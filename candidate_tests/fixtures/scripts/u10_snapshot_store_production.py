#!/usr/bin/env python3
"""Fixed-ID U-10 snapshot projection and activation transactions.

The public root entry accepts only an authorization identifier.  Filesystem
paths and JSON payloads are resolved from root-held authorization records.
Projection and activation are deliberately separate: projection performs the
final-path non-root lock check and seals the tree, while activation consumes a
later human snapshot-adoption authorization and publishes the manifest last.
"""

from __future__ import annotations

import argparse
import base64
from contextlib import nullcontext
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import selectors
import signal
import stat
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Sequence

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from semantic_guard_u10_broker.core import (
    BROKER_VERSION,
    KeyChainPaths,
    resolve_current_signing_key_chain_v2_under_trust_store_lock,
    snapshot_basis_digest_v1,
    store_activation_content_v1,
    store_activation_transition_digest_v2,
)
from semantic_guard_u10_broker.darwin_acl import assert_no_extended_acl
from semantic_guard_u10_broker.internal_contracts import (
    STORE_ACTIVATION_LEDGER_POLICY_V3,
    STORE_LEDGER_RETENTION_POLICY_V1,
    STORE_REVOCATION_LEDGER_POLICY_V2,
)
from semantic_guard_u10_broker.internal_operations import (
    load_current_store_activation_context_v1 as _load_current_store_activation_context_v1,
    revocation_transition_ref_v1 as _revocation_transition_ref_v1,
    store_transition_ref_v1 as _store_transition_ref_v1,
    validate_publisher_contract_binding_v1 as _validate_publisher_contract_binding_v1,
)
from semantic_guard_u10_broker.protected_io import (
    BrokerBoundaryError,
    U10_ROOT,
    read_protected_file,
    strict_json_loads,
    trust_store_coordination_lock,
    validate_directory_chain,
)
from semantic_guard_vnext.environment_resolution import environment_schema_directory


MANIFEST_NAME = "u10-execution-snapshot-manifest-v1.json"
_SCHEMA_ROOT = environment_schema_directory()
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,199}$")
_ENTITY_REF = re.compile(
    r"^.{1,200}・(?P<id>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$"
)
_PROJECTION_POLICY = "authorization_consumption_projection_receipt_append_only/v1"
_ACTIVATION_POLICY = "authorization_consumption_manifest_receipt_append_only/v1"
_PROJECTION_LOCK_NAME = "snapshot-projection.lock"
_ACTIVATION_LOCK_NAME = "snapshot-activation.lock"
_PROJECTOR_RELATIVE_PATH = "vnext/scripts/u10_snapshot_environment_projector.py"


class U10SnapshotProductionError(RuntimeError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class SnapshotPaths:
    u10_root: Path = U10_ROOT
    candidate_root: Path = U10_ROOT / "candidates"
    snapshot_root: Path = U10_ROOT / "snapshots"
    authorization_root: Path = U10_ROOT / "authorizations"
    projection_ledger_root: Path = U10_ROOT / "activations" / "snapshot-projections"
    activation_ledger_root: Path = U10_ROOT / "activations" / "snapshot-activations"
    activation_root: Path = U10_ROOT / "activations" / "snapshots"
    store_activation_basis_root: Path = U10_ROOT / "store-activation-bases"


def canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise U10SnapshotProductionError(
            "u10_canonical_json_invalid", type(exc).__name__
        ) from exc


def json_record_bytes(value: Any) -> bytes:
    try:
        return (
            json.dumps(
                value,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise U10SnapshotProductionError(
            "u10_json_record_invalid", type(exc).__name__
        ) from exc


def _strict_json_clone(value: Any) -> Any:
    """Clone through the finite JSON boundary used for protected records."""

    return strict_json_loads(canonical_json_bytes(value))


def digest_bytes(raw: bytes) -> dict[str, str]:
    return {"algorithm": "sha256", "value": hashlib.sha256(raw).hexdigest()}


def sealed_digest(value: Mapping[str, Any], field: str) -> dict[str, str]:
    material = dict(value)
    material.pop(field, None)
    return digest_bytes(canonical_json_bytes(material))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _time(value: Any, *, code: str) -> datetime:
    if not isinstance(value, str):
        raise U10SnapshotProductionError(code, repr(value))
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise U10SnapshotProductionError(code, value) from exc
    if parsed.tzinfo is None:
        raise U10SnapshotProductionError(code, value)
    return parsed.astimezone(timezone.utc)


def _ed25519_private_key_from_root_raw(
    raw: bytes, *, path: Path
) -> Ed25519PrivateKey:
    if len(raw) != 32:
        raise U10SnapshotProductionError(
            "u10_private_key_raw_length_invalid", str(path)
        )
    try:
        return Ed25519PrivateKey.from_private_bytes(raw)
    except ValueError as exc:
        raise U10SnapshotProductionError(
            "u10_private_key_unreadable", str(path)
        ) from exc


def _validate_schema(value: Mapping[str, Any], name: str, code: str) -> None:
    try:
        schema = strict_json_loads((_SCHEMA_ROOT / name).read_bytes())
        if not isinstance(schema, dict):
            raise U10SnapshotProductionError(code, f"schema {name}: not object")
        registry = Registry()
        for candidate_path in sorted(_SCHEMA_ROOT.glob("*.schema.json")):
            candidate = strict_json_loads(candidate_path.read_bytes())
            if not isinstance(candidate, dict):
                raise U10SnapshotProductionError(
                    code, f"schema {candidate_path.name}: not object"
                )
            resource_id = candidate.get("$id")
            if isinstance(resource_id, str):
                registry = registry.with_resource(
                    resource_id, Resource.from_contents(candidate)
                )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise U10SnapshotProductionError(code, f"schema {name}: {exc}") from exc
    issues = sorted(
        Draft202012Validator(
            schema, registry=registry, format_checker=FormatChecker()
        ).iter_errors(value),
        key=lambda item: tuple(map(str, item.absolute_path)),
    )
    if issues:
        issue = issues[0]
        where = "/".join(map(str, issue.absolute_path)) or "$"
        raise U10SnapshotProductionError(code, f"{where}: {issue.message}")


def _id(value: Any, *, code: str) -> str:
    if not isinstance(value, str) or _ID.fullmatch(value) is None:
        raise U10SnapshotProductionError(code, repr(value))
    return value


def _entity_id(value: Any, *, code: str) -> str:
    if not isinstance(value, str):
        raise U10SnapshotProductionError(code, repr(value))
    matched = _ENTITY_REF.fullmatch(value)
    if matched is None:
        raise U10SnapshotProductionError(code, value)
    return matched.group("id")


def _canonical_relative(value: Any, *, code: str) -> PurePosixPath:
    if not isinstance(value, str):
        raise U10SnapshotProductionError(code, repr(value))
    parsed = PurePosixPath(value)
    if (
        not value
        or value != parsed.as_posix()
        or parsed.is_absolute()
        or any(part in {"", ".", ".."} for part in value.split("/"))
        or "\\" in value
        or "\x00" in value
    ):
        raise U10SnapshotProductionError(code, value)
    return parsed


def _inside(root: Path, path: Path) -> Path:
    if not path.is_absolute() or path != Path(os.path.normpath(str(path))):
        raise U10SnapshotProductionError("u10_noncanonical_path", str(path))
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise U10SnapshotProductionError("u10_path_escape", str(path)) from exc
    return path


def _root_owner(root: Path) -> int:
    try:
        observed = root.lstat()
    except OSError as exc:
        raise U10SnapshotProductionError("u10_protected_root_unavailable", str(root)) from exc
    if stat.S_ISLNK(observed.st_mode) or not stat.S_ISDIR(observed.st_mode):
        raise U10SnapshotProductionError("u10_protected_root_untrusted", str(root))
    return observed.st_uid


def _assert_acl_absent(path: Path) -> None:
    try:
        assert_no_extended_acl(path)
    except PermissionError as exc:
        raise U10SnapshotProductionError("u10_extended_acl_prohibited", str(path)) from exc
    except OSError as exc:
        raise U10SnapshotProductionError("u10_acl_observation_failed", str(path)) from exc


def _assert_directory(
    path: Path,
    *,
    root: Path,
    uid: int,
    exact_mode: int | None = None,
) -> os.stat_result:
    _inside(root, path)
    try:
        validate_directory_chain(root, path, required_uid=uid)
        observed = path.lstat()
    except BrokerBoundaryError as exc:
        raise U10SnapshotProductionError(exc.code, exc.detail) from exc
    except OSError as exc:
        raise U10SnapshotProductionError("u10_directory_unavailable", str(path)) from exc
    _assert_acl_absent(path)
    if (
        stat.S_ISLNK(observed.st_mode)
        or not stat.S_ISDIR(observed.st_mode)
        or observed.st_uid != uid
        or observed.st_gid != (0 if uid == 0 else os.getgid())
        or observed.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
        or (exact_mode is not None and stat.S_IMODE(observed.st_mode) != exact_mode)
    ):
        raise U10SnapshotProductionError("u10_directory_untrusted", str(path))
    return observed


def _read_regular(
    path: Path,
    *,
    root: Path,
    private: bool = False,
    allowed_modes: set[int] | None = None,
    allowed_nlinks: set[int] = frozenset({1}),
    maximum_bytes: int = 256 * 1024 * 1024,
) -> tuple[bytes, os.stat_result]:
    _inside(root, path)
    uid = _root_owner(root)
    try:
        raw = read_protected_file(
            path,
            protected_root=root,
            required_uid=uid,
            private=private,
            maximum_bytes=maximum_bytes,
        )
        observed = path.lstat()
    except BrokerBoundaryError as exc:
        raise U10SnapshotProductionError(exc.code, exc.detail) from exc
    except OSError as exc:
        raise U10SnapshotProductionError("u10_artifact_unreadable", str(path)) from exc
    if observed.st_nlink not in allowed_nlinks or (
        allowed_modes is not None
        and stat.S_IMODE(observed.st_mode) not in allowed_modes
    ):
        raise U10SnapshotProductionError("u10_artifact_mode_or_link_untrusted", str(path))
    return raw, observed


def _json(raw: bytes, *, code: str) -> dict[str, Any]:
    try:
        value = strict_json_loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise U10SnapshotProductionError(code, str(exc)) from exc
    if not isinstance(value, dict):
        raise U10SnapshotProductionError(code, "root is not object")
    return value


def _write_exclusive(path: Path, value: Mapping[str, Any], *, mode: int) -> bytes:
    raw = json_record_bytes(value)
    uid = _root_owner(path.parent)
    _assert_directory(path.parent, root=path.parent, uid=uid)
    descriptor = os.open(
        path,
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_NOFOLLOW", 0),
        mode,
    )
    try:
        os.fchmod(descriptor, mode)
        if os.geteuid() == 0:
            os.fchown(descriptor, 0, 0)
        offset = 0
        while offset < len(raw):
            offset += os.write(descriptor, raw[offset:])
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    parent = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(parent)
    finally:
        os.close(parent)
    return raw


def _load_record(path: Path, *, root: Path) -> tuple[dict[str, Any], bytes]:
    raw, _observed = _read_regular(path, root=root, allowed_modes={0o400, 0o444})
    return _json(raw, code="u10_record_unreadable"), raw


def _load_optional_record(
    path: Path, *, root: Path
) -> tuple[dict[str, Any], bytes] | None:
    if not path.exists() and not path.is_symlink():
        return None
    return _load_record(path, root=root)


def _fsync_directory(path: Path) -> None:
    try:
        descriptor = os.open(
            path,
            os.O_RDONLY
            | getattr(os, "O_DIRECTORY", 0)
            | getattr(os, "O_NOFOLLOW", 0),
        )
    except OSError as exc:
        raise U10SnapshotProductionError("u10_directory_fsync_open_failed", str(path)) from exc
    try:
        os.fsync(descriptor)
    except OSError as exc:
        raise U10SnapshotProductionError("u10_directory_fsync_failed", str(path)) from exc
    finally:
        os.close(descriptor)


def _write_all_bytes(path: Path, raw: bytes, *, mode: int) -> None:
    descriptor = os.open(
        path,
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_NOFOLLOW", 0),
        mode,
    )
    try:
        os.fchmod(descriptor, mode)
        if os.geteuid() == 0:
            os.fchown(descriptor, 0, 0)
        offset = 0
        while offset < len(raw):
            written = os.write(descriptor, raw[offset:])
            if written <= 0:
                raise U10SnapshotProductionError("u10_short_write", str(path))
            offset += written
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _publish_append_only_record(
    path: Path,
    value: Mapping[str, Any],
    *,
    ledger_root: Path,
    mode: int = 0o400,
) -> bytes:
    """Atomically publish complete bytes without replacing an existing record."""

    raw = json_record_bytes(value)
    pending = ledger_root / f".{path.name}.pending"
    if path.exists() or path.is_symlink():
        observed_raw, observed_state = _read_regular(
            path,
            root=ledger_root,
            allowed_modes={mode},
            allowed_nlinks={1, 2},
        )
        if observed_raw != raw:
            raise U10SnapshotProductionError("u10_append_only_record_collision", str(path))
        if observed_state.st_nlink == 2:
            pending_raw, pending_state = _read_regular(
                pending,
                root=ledger_root,
                private=not bool(mode & (stat.S_IRGRP | stat.S_IROTH)),
                allowed_modes={mode},
                allowed_nlinks={2},
            )
            if (
                pending_raw != raw
                or pending_state.st_dev != observed_state.st_dev
                or pending_state.st_ino != observed_state.st_ino
            ):
                raise U10SnapshotProductionError(
                    "u10_append_only_link_recovery_mismatch", str(path)
                )
            pending.unlink()
            _fsync_directory(ledger_root)
            observed_raw, observed_state = _read_regular(
                path, root=ledger_root, allowed_modes={mode}
            )
        elif pending.exists() or pending.is_symlink():
            raise U10SnapshotProductionError(
                "u10_append_only_orphan_pending", str(pending)
            )
        return observed_raw
    if pending.exists() or pending.is_symlink():
        pending_raw, _ = _read_regular(
            pending,
            root=ledger_root,
            private=not bool(mode & (stat.S_IRGRP | stat.S_IROTH)),
            allowed_modes={mode},
            allowed_nlinks={1},
        )
        if pending_raw != raw:
            raise U10SnapshotProductionError("u10_append_only_pending_collision", str(pending))
    else:
        _write_all_bytes(pending, raw, mode=mode)
    try:
        os.link(pending, path, follow_symlinks=False)
    except FileExistsError:
        observed, _ = _read_regular(
            path,
            root=ledger_root,
            allowed_modes={mode},
            allowed_nlinks={1, 2},
        )
        if observed != raw:
            raise U10SnapshotProductionError("u10_append_only_record_collision", str(path))
    except OSError as exc:
        raise U10SnapshotProductionError("u10_append_only_publish_failed", str(path)) from exc
    _fsync_directory(ledger_root)
    try:
        pending.unlink()
    except FileNotFoundError:
        pass
    _fsync_directory(ledger_root)
    observed, state = _read_regular(path, root=ledger_root, allowed_modes={mode})
    if observed != raw or state.st_nlink != 1:
        raise U10SnapshotProductionError("u10_append_only_post_publish_mismatch", str(path))
    return observed


def _validate_publisher_contract_binding(
    value: Mapping[str, Any], *, operation: str
) -> dict[str, Any]:
    normalized = _strict_json_clone(value)
    if not isinstance(normalized, dict):
        raise U10SnapshotProductionError("u10_publisher_contract_binding_invalid", "not object")
    try:
        normalized = _validate_publisher_contract_binding_v1(
            normalized, enforce_current=True
        )
    except BrokerBoundaryError as exc:
        raise U10SnapshotProductionError(exc.code, exc.detail) from exc
    if operation not in normalized["allowed_operations"]:
        raise U10SnapshotProductionError(
            "u10_publisher_operation_not_allowed", operation
        )
    producer = normalized["artifacts"]["snapshot_store_producer"]
    if producer["locator"] != str(U10_ROOT / "bootstrap" / Path(__file__).name):
        raise U10SnapshotProductionError(
            "u10_publisher_contract_producer_path_mismatch", str(producer["locator"])
        )
    return normalized


def _validate_fixed_roots(paths: SnapshotPaths, *, required_uid: int) -> None:
    if required_uid != 0:
        raise U10SnapshotProductionError("u10_production_uid_contract_invalid", str(required_uid))
    expected = SnapshotPaths()
    if paths != expected:
        raise U10SnapshotProductionError("u10_production_path_override", repr(paths))
    modes = {
        paths.u10_root: 0o700,
        paths.candidate_root: 0o700,
        paths.snapshot_root: 0o700,
        paths.authorization_root: 0o700,
        paths.projection_ledger_root: 0o700,
        paths.activation_ledger_root: 0o700,
        paths.activation_root: 0o700,
        paths.store_activation_basis_root: 0o700,
    }
    for path, mode in modes.items():
        _assert_directory(path, root=paths.u10_root, uid=0, exact_mode=mode)


def _lock(root: Path, name: str):
    path = root / name
    uid = _root_owner(root)
    _assert_directory(root, root=root, uid=uid, exact_mode=0o700)
    try:
        before = path.lstat()
    except OSError as exc:
        raise U10SnapshotProductionError("u10_transaction_lock_unavailable", str(path)) from exc
    _assert_acl_absent(path)
    if (
        stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_uid != uid
        or before.st_gid != (0 if uid == 0 else os.getgid())
        or stat.S_IMODE(before.st_mode) != 0o600
        or before.st_nlink != 1
    ):
        raise U10SnapshotProductionError("u10_transaction_lock_untrusted", str(path))
    descriptor = os.open(
        path, os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
    )
    opened = os.fstat(descriptor)
    if (
        opened.st_dev,
        opened.st_ino,
        opened.st_mode,
        opened.st_uid,
        opened.st_gid,
        opened.st_nlink,
    ) != (
        before.st_dev,
        before.st_ino,
        before.st_mode,
        before.st_uid,
        before.st_gid,
        before.st_nlink,
    ):
        os.close(descriptor)
        raise U10SnapshotProductionError("u10_transaction_lock_changed", str(path))

    class _Lock:
        def __enter__(self) -> None:
            fcntl.flock(descriptor, fcntl.LOCK_EX)

        def __exit__(self, *_args: Any) -> None:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)

    return _Lock()


def _verify_seal(value: Mapping[str, Any], field: str, *, code: str) -> None:
    if value.get(field) != sealed_digest(value, field):
        raise U10SnapshotProductionError(code, str(value.get(field)))


def _load_projection_authorization(
    authorization_id: str,
    *,
    paths: SnapshotPaths,
    enforce_fixed_paths: bool,
) -> tuple[dict[str, Any], bytes]:
    authorization_id = _id(authorization_id, code="u10_projection_authorization_id_invalid")
    value, raw = _load_record(
        paths.authorization_root / f"{authorization_id}.json",
        root=paths.authorization_root,
    )
    _validate_schema(
        value,
        "u10-snapshot-projection-authorization-v1.schema.json",
        "u10_projection_authorization_invalid",
    )
    _verify_seal(value, "authorization_digest", code="u10_projection_authorization_digest_mismatch")
    target = value["target_snapshot"]
    bundle = value["bundle_ref"]
    expected_policy_digest = digest_bytes(canonical_json_bytes(_PROJECTION_POLICY))
    if (
        value["authorization_id"] != authorization_id
        or value["projection_ledger"]
        != {
            "root": str(paths.projection_ledger_root),
            "policy": _PROJECTION_POLICY,
            "policy_digest": expected_policy_digest,
        }
        or (enforce_fixed_paths and Path(target["snapshot_path"]).parent != paths.snapshot_root)
        or (enforce_fixed_paths and Path(bundle["candidate_path"]).parent != paths.candidate_root)
        or Path(bundle["candidate_path"]).name != bundle["bundle_id"]
        or Path(target["snapshot_path"]).name != target["snapshot_id"]
    ):
        raise U10SnapshotProductionError("u10_projection_authorization_context_mismatch", authorization_id)
    _time(value["recorded_at"], code="u10_projection_authorization_time_invalid")
    return value, raw


def _verify_installed_candidate(
    authorization: Mapping[str, Any], *, paths: SnapshotPaths
) -> tuple[dict[str, Any], bytes, dict[str, Any], bytes]:
    bundle = authorization["bundle_ref"]
    candidate = Path(bundle["candidate_path"])
    manifest, manifest_raw = _load_record(
        candidate / "bundle-manifest.json", root=candidate
    )
    _validate_schema(
        manifest,
        "u10-root-candidate-bundle-v1.schema.json",
        "u10_candidate_bundle_invalid",
    )
    _verify_seal(manifest, "bundle_digest", code="u10_candidate_bundle_digest_mismatch")
    projection, projection_raw = _load_record(
        candidate / "install-projection.json", root=candidate
    )
    _validate_schema(
        projection,
        "u10-candidate-install-projection-v1.schema.json",
        "u10_candidate_install_projection_invalid",
    )
    _verify_seal(projection, "projection_digest", code="u10_candidate_install_projection_digest_mismatch")
    projection_ref = bundle["install_projection_ref"]
    if (
        manifest["bundle_id"] != bundle["bundle_id"]
        or manifest["bundle_version"] != bundle["bundle_version"]
        or digest_bytes(manifest_raw) != bundle["manifest_artifact_digest"]
        or manifest["bundle_digest"] != bundle["bundle_digest"]
        or projection_ref
        != {
            "record_id": projection["projection_id"],
            "locator": str(candidate / "install-projection.json"),
            "artifact_digest": digest_bytes(projection_raw),
            "semantic_digest": projection["projection_digest"],
        }
        or projection["bundle_ref"]
        != {"bundle_id": manifest["bundle_id"], "bundle_digest": manifest["bundle_digest"]}
        or projection["projected_candidate_path"] != str(candidate)
    ):
        raise U10SnapshotProductionError("u10_installed_candidate_binding_mismatch", str(candidate))
    declared = {
        _canonical_relative(
            item["path"], code="u10_candidate_payload_path_invalid"
        ).as_posix(): item
        for item in projection["installed_denominator"]["entries"]
    }
    if len(declared) != len(projection["installed_denominator"]["entries"]):
        raise U10SnapshotProductionError(
            "u10_candidate_payload_path_collision", str(candidate)
        )
    declared_directories = {
        _canonical_relative(
            item, code="u10_candidate_payload_directory_invalid"
        ).as_posix()
        for item in projection["installed_denominator"]["directories"]
    }
    if len(declared_directories) != len(
        projection["installed_denominator"]["directories"]
    ):
        raise U10SnapshotProductionError(
            "u10_candidate_payload_directory_collision", str(candidate)
        )
    observed: set[str] = set()
    observed_directories: set[str] = set()
    payload = candidate / "payload"
    for base, directories, files in os.walk(payload, topdown=True, followlinks=False):
        directories.sort()
        files.sort()
        base_path = Path(base)
        base_state = base_path.lstat()
        _assert_acl_absent(base_path)
        if (
            stat.S_ISLNK(base_state.st_mode)
            or not stat.S_ISDIR(base_state.st_mode)
            or base_state.st_uid != _root_owner(candidate)
            or base_state.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
        ):
            raise U10SnapshotProductionError(
                "u10_candidate_payload_directory_untrusted", str(base_path)
            )
        for name in directories:
            path = base_path / name
            state = path.lstat()
            _assert_acl_absent(path)
            if stat.S_ISLNK(state.st_mode) or not stat.S_ISDIR(state.st_mode):
                raise U10SnapshotProductionError(
                    "u10_candidate_payload_special_entry", str(path)
                )
            observed_directories.add(path.relative_to(payload).as_posix())
        for name in files:
            path = base_path / name
            relative = path.relative_to(payload).as_posix()
            raw, observed_state = _read_regular(
                path, root=payload, allowed_modes={0o400, 0o500}
            )
            expected = declared.get(relative)
            if (
                expected is None
                or digest_bytes(raw) != expected["artifact_digest"]
                or stat.S_IMODE(observed_state.st_mode)
                != int(str(expected["installed_mode"]), 8)
            ):
                raise U10SnapshotProductionError("u10_candidate_payload_denominator_mismatch", relative)
            observed.add(relative)
    if observed != set(declared) or observed_directories != declared_directories:
        raise U10SnapshotProductionError(
            "u10_candidate_payload_denominator_mismatch",
            repr(
                {
                    "file_missing": sorted(set(declared) - observed),
                    "file_extra": sorted(observed - set(declared)),
                    "directory_missing": sorted(
                        declared_directories - observed_directories
                    ),
                    "directory_extra": sorted(
                        observed_directories - declared_directories
                    ),
                }
            ),
        )
    return manifest, manifest_raw, projection, projection_raw


def _semantic_digest(raw: bytes) -> tuple[dict[str, str], dict[str, Any] | None]:
    try:
        value = strict_json_loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return digest_bytes(raw), None
    if not isinstance(value, dict):
        return digest_bytes(raw), None
    for field in (
        "source_digest",
        "basis_digest",
        "adoption_digest",
        "manifest_digest",
        "evidence_digest",
        "decision_digest",
        "observation_digest",
        "resolution_digest",
        "bundle_digest",
        "projection_digest",
    ):
        candidate = value.get(field)
        if isinstance(candidate, dict) and set(candidate) == {"algorithm", "value"}:
            return dict(candidate), value
    return digest_bytes(canonical_json_bytes(value)), value


def _artifact_role(
    path: str,
    candidate_role: str,
    value: Mapping[str, Any] | None,
    *,
    environment_projection: Mapping[str, Any],
) -> str:
    outputs = environment_projection["output_locators"]
    exact_generated_roles = {
        outputs["host_identity_evidence"]: "host_identity_evidence",
        outputs["containment_probe_evidence"]: "containment_probe_evidence",
        outputs["containment_trace"]: "containment_trace",
        outputs["resolved_environment_profile"]: "environment_profile",
        outputs["environment_adoption_request"]: "environment_adoption_request",
        outputs["eligibility_source"]: "eligibility_source",
    }
    if path in exact_generated_roles:
        return exact_generated_roles[path]
    if path == environment_projection["profile_locator"]:
        return "verification_profile"
    schema = value.get("schema_version") if isinstance(value, Mapping) else None
    known = {
        "semantic-guard-closed-verification-test-manifest/v1": "closed_test_manifest",
    }
    if schema in known:
        return known[str(schema)]
    if candidate_role in {
        "u10_preactivation_decision_record",
        "u10_worker_account_observation",
        "u10_worker_principal_resolution",
    }:
        return candidate_role
    if path == "vnext/.venv/bin/python":
        return "python_interpreter"
    if path == "vnext/scripts/u10_snapshot_worker.py":
        return "worker_entrypoint"
    if path == _PROJECTOR_RELATIVE_PATH:
        return "environment_projector"
    if path == "vnext/scripts/u10_root_broker_bootstrap.py" or path.startswith(
        "vnext/src/semantic_guard_u10_broker/"
    ):
        return "broker_runtime"
    if path.startswith("vnext/src/semantic_guard_vnext/"):
        return "subject"
    if path.startswith("vnext/.venv/lib/") and "/site-packages/" in path:
        return "dependency"
    if path.startswith("vnext/.venv/lib/"):
        return "python_runtime"
    if path.endswith(".schema.json"):
        return "contract_schema"
    if path in {"vnext/uv.lock", "vnext/pyproject.toml"}:
        return "dependency_lock"
    if path.startswith("vnext/scripts/"):
        return "runner"
    return "test_source"


def _walk_refs(value: Any, result: dict[tuple[str, str], str]) -> None:
    if isinstance(value, Mapping):
        if set(("record_id", "locator", "content_digest")).issubset(value):
            digest = value.get("content_digest")
            if isinstance(digest, Mapping) and isinstance(digest.get("value"), str):
                result[(str(value["locator"]), str(digest["value"]))] = str(value["record_id"])
        for child in value.values():
            _walk_refs(child, result)
    elif isinstance(value, list):
        for child in value:
            _walk_refs(child, result)


def _copy_candidate_to_snapshot(
    *,
    manifest: Mapping[str, Any],
    manifest_raw: bytes,
    projection: Mapping[str, Any],
    projection_raw: bytes,
    snapshot: Path,
    marker: Mapping[str, Any],
) -> None:
    try:
        snapshot.mkdir(mode=0o700)
    except FileExistsError as exc:
        raise U10SnapshotProductionError("u10_projection_collision", str(snapshot)) from exc
    _write_exclusive(snapshot / ".projection-owner.json", marker, mode=0o400)
    candidate = Path(str(projection["projected_candidate_path"]))
    payload = candidate / "payload"
    observed_targets: set[str] = set()
    for item in projection["installed_denominator"]["entries"]:
        relative = _canonical_relative(
            item["path"], code="u10_projection_payload_path_invalid"
        )
        if relative.as_posix() in observed_targets:
            raise U10SnapshotProductionError(
                "u10_projection_payload_path_collision", relative.as_posix()
            )
        observed_targets.add(relative.as_posix())
        target = snapshot / Path(*relative.parts)
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if target.is_symlink() or target.exists():
            raise U10SnapshotProductionError(
                "u10_projection_payload_collision", relative.as_posix()
            )
        raw, _observed = _read_regular(
            payload / Path(*relative.parts),
            root=payload,
            allowed_modes={0o400, 0o500},
        )
        if digest_bytes(raw) != item["artifact_digest"]:
            raise U10SnapshotProductionError("u10_projection_source_changed", relative.as_posix())
        installed_mode = int(str(item["installed_mode"]), 8)
        _write_all_bytes(target, raw, mode=0o700 if installed_mode & 0o100 else 0o600)
    metadata = snapshot / "vnext" / "governance"
    metadata.mkdir(parents=True, exist_ok=True, mode=0o700)
    for name, raw in (
        ("u10-root-candidate-bundle.json", manifest_raw),
        ("u10-candidate-install-projection.json", projection_raw),
    ):
        _write_all_bytes(metadata / name, raw, mode=0o400)
    _fsync_directory(metadata)
    _fsync_directory(snapshot)


def _remove_owned_partial(
    snapshot: Path,
    marker: Mapping[str, Any],
    *,
    allow_missing_marker: bool = False,
) -> None:
    marker_path = snapshot / ".projection-owner.json"
    if marker_path.exists() or marker_path.is_symlink():
        value, _raw = _load_record(marker_path, root=snapshot)
        if value != marker:
            raise U10SnapshotProductionError("u10_projection_collision", str(snapshot))
    elif not allow_missing_marker:
        raise U10SnapshotProductionError("u10_projection_collision", str(snapshot))
    if (snapshot / MANIFEST_NAME).exists() or (snapshot / MANIFEST_NAME).is_symlink():
        raise U10SnapshotProductionError("u10_projection_collision", str(snapshot))
    owner = _root_owner(snapshot)
    for base, directories, files in os.walk(snapshot, topdown=False, followlinks=False):
        for name in files:
            path = Path(base) / name
            observed = path.lstat()
            _assert_acl_absent(path)
            if (
                stat.S_ISLNK(observed.st_mode)
                or not stat.S_ISREG(observed.st_mode)
                or observed.st_uid != owner
            ):
                raise U10SnapshotProductionError("u10_projection_partial_symlink", str(path))
            path.unlink()
        for name in directories:
            path = Path(base) / name
            observed = path.lstat()
            _assert_acl_absent(path)
            if (
                stat.S_ISLNK(observed.st_mode)
                or not stat.S_ISDIR(observed.st_mode)
                or observed.st_uid != owner
            ):
                raise U10SnapshotProductionError("u10_projection_partial_symlink", str(path))
            path.rmdir()
    snapshot.rmdir()


def _set_projection_modes(snapshot: Path) -> None:
    for base, directories, files in os.walk(snapshot, topdown=False, followlinks=False):
        for name in files:
            path = Path(base) / name
            executable = path.name in {"python", "uv"} or path.suffix in {".sh"}
            os.chmod(path, 0o555 if executable else 0o444)
        for name in directories:
            os.chmod(Path(base) / name, 0o555)
    os.chmod(snapshot, 0o555)


def _kill_process_group_and_confirm(process: subprocess.Popen[bytes], *, code: str) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired as exc:
        raise U10SnapshotProductionError(code, "process leader did not terminate") from exc
    deadline = time.monotonic() + 2.0
    while True:
        try:
            os.killpg(process.pid, 0)
        except ProcessLookupError:
            return
        except PermissionError as exc:
            raise U10SnapshotProductionError(code, "process group ownership changed") from exc
        if time.monotonic() >= deadline:
            raise U10SnapshotProductionError(code, "residual process group remains")
        time.sleep(0.02)


def _bounded_worker_run(
    argv: list[str],
    *,
    cwd: Path,
    environment: dict[str, str],
    uid: int,
    gid: int,
    stdin_bytes: bytes | None = None,
    timeout_seconds: int = 1800,
    stdout_limit: int = 16 * 1024 * 1024,
    stderr_limit: int = 1024 * 1024,
) -> subprocess.CompletedProcess[bytes]:
    if timeout_seconds <= 0 or stdout_limit <= 0 or stderr_limit <= 0:
        raise U10SnapshotProductionError("u10_worker_budget_invalid", repr(argv))
    popen_kwargs: dict[str, Any] = {
        "cwd": cwd,
        "env": environment,
        "stdin": subprocess.PIPE if stdin_bytes is not None else subprocess.DEVNULL,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "start_new_session": True,
    }
    if os.geteuid() == 0:
        popen_kwargs.update(
            {"user": uid, "group": gid, "extra_groups": [], "umask": 0o77}
        )
    elif (
        os.geteuid() != uid
        or os.getegid() != gid
        or os.getgroups()
    ):
        raise U10SnapshotProductionError(
            "u10_worker_identity_unavailable", f"{uid}:{gid}:[]"
        )
    process = subprocess.Popen(argv, **popen_kwargs)
    assert process.stdout is not None and process.stderr is not None
    selector = selectors.DefaultSelector()
    streams = {
        process.stdout.fileno(): ("stdout", process.stdout, stdout_limit),
        process.stderr.fileno(): ("stderr", process.stderr, stderr_limit),
    }
    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    for descriptor, (_name, stream, _limit) in streams.items():
        os.set_blocking(descriptor, False)
        selector.register(stream, selectors.EVENT_READ)
    pending_stdin = memoryview(stdin_bytes or b"")
    stdin_offset = 0
    if stdin_bytes is not None:
        assert process.stdin is not None
        os.set_blocking(process.stdin.fileno(), False)
        selector.register(process.stdin, selectors.EVENT_WRITE)
    deadline = time.monotonic() + timeout_seconds
    failure_code: str | None = None
    try:
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                failure_code = "u10_worker_timeout"
                break
            for key, mask in selector.select(min(0.25, remaining)):
                stream = key.fileobj
                if process.stdin is not None and stream is process.stdin:
                    if stdin_offset >= len(pending_stdin):
                        selector.unregister(stream)
                        stream.close()
                        continue
                    try:
                        written = os.write(
                            stream.fileno(), pending_stdin[stdin_offset : stdin_offset + 65536]
                        )
                    except BlockingIOError:
                        continue
                    stdin_offset += written
                    continue
                name, _known_stream, limit = streams[stream.fileno()]
                try:
                    chunk = os.read(stream.fileno(), 65536)
                except BlockingIOError:
                    continue
                if not chunk:
                    selector.unregister(stream)
                    stream.close()
                    continue
                buffer = buffers[name]
                if len(buffer) + len(chunk) > limit:
                    failure_code = f"u10_worker_{name}_limit_exceeded"
                    break
                buffer.extend(chunk)
            if failure_code is not None:
                break
    finally:
        selector.close()
    if failure_code is not None:
        _kill_process_group_and_confirm(process, code=failure_code)
        raise U10SnapshotProductionError(failure_code, repr(argv))
    try:
        return_code = process.wait(timeout=max(0.1, deadline - time.monotonic()))
    except subprocess.TimeoutExpired:
        _kill_process_group_and_confirm(process, code="u10_worker_timeout")
        raise U10SnapshotProductionError("u10_worker_timeout", repr(argv)) from None
    try:
        os.killpg(process.pid, 0)
    except ProcessLookupError:
        pass
    else:
        _kill_process_group_and_confirm(process, code="u10_worker_residual_process_group")
        raise U10SnapshotProductionError(
            "u10_worker_residual_process_group", repr(argv)
        )
    return subprocess.CompletedProcess(
        argv, return_code, bytes(buffers["stdout"]), bytes(buffers["stderr"])
    )


def _default_dependency_runner(
    argv: list[str],
    *,
    cwd: Path,
    environment: dict[str, str],
    uid: int,
    gid: int,
) -> subprocess.CompletedProcess[bytes]:
    return _bounded_worker_run(
        argv,
        cwd=cwd,
        environment=environment,
        uid=uid,
        gid=gid,
    )


def _run_dependency_check(
    *,
    manifest: Mapping[str, Any],
    snapshot: Path,
    runner: Callable[..., subprocess.CompletedProcess[bytes]],
) -> dict[str, Any]:
    check = manifest["dependency_environment_policy"]["lock_validation"]
    uv = snapshot / str(check["uv_executable"])
    expected_arguments = [
        str(argument).format(candidate_payload=str(snapshot))
        for argument in check["arguments"]
    ]
    argv = [str(uv), *expected_arguments]
    environment = {
        "PATH": str(uv.parent),
        "LC_ALL": "C",
        "NO_COLOR": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "UV_NO_PROGRESS": "1",
        "UV_OFFLINE": "1",
        "UV_PYTHON_DOWNLOADS": "never",
    }
    identity = manifest["worker_identity"]
    started = _utc_now()
    completed = runner(
        argv,
        cwd=snapshot / str(check["working_directory"]),
        environment=environment,
        uid=int(identity["uid"]),
        gid=int(identity["gid"]),
    )
    finished = _utc_now()
    if completed.returncode != 0:
        raise U10SnapshotProductionError("u10_snapshot_dependency_check_failed", str(completed.returncode))
    return {
        "profile": "uv-sync-check-offline-frozen-final-path/v1",
        "argv": argv,
        "effective_environment": environment,
        "worker_identity": {
            "uid": identity["uid"],
            "gid": identity["gid"],
            "effective_supplementary_gids": [],
            "umask": 63,
        },
        "started_at": started,
        "finished_at": finished,
        "exit_code": 0,
        "stdout_digest": digest_bytes(completed.stdout),
        "stderr_digest": digest_bytes(completed.stderr),
    }


def _validate_repository_ref_in_snapshot(
    reference: Mapping[str, Any], *, snapshot: Path, code: str
) -> None:
    relative = _canonical_relative(reference.get("locator"), code=code)
    raw, _ = _read_regular(
        snapshot / Path(*relative.parts),
        root=snapshot,
        allowed_modes={0o444, 0o555},
    )
    if digest_bytes(raw) != reference.get("content_digest"):
        raise U10SnapshotProductionError(code, relative.as_posix())


def _run_environment_projection(
    *,
    authorization: Mapping[str, Any],
    candidate: Mapping[str, Any],
    snapshot: Path,
    runner: Callable[..., subprocess.CompletedProcess[bytes]] = _bounded_worker_run,
) -> tuple[dict[str, Any], dict[str, Any]]:
    projection = authorization["environment_projection"]
    _validate_repository_ref_in_snapshot(
        projection["decision_owner_ref"],
        snapshot=snapshot,
        code="u10_environment_decision_owner_ref_mismatch",
    )
    identity = candidate["worker_identity"]
    interpreter = snapshot / "vnext/.venv/bin/python"
    projector = snapshot / _PROJECTOR_RELATIVE_PATH
    subject = snapshot / candidate["dependency_environment_policy"]["snapshot_source_root"]
    dependencies = [
        snapshot / candidate["dependency_environment_policy"]["dependency_import_root"]
    ]
    context = {
        "schema_version": "semantic-guard-u10-snapshot-environment-projection-context/v1",
        "snapshot_root": str(snapshot),
        "subject_source_root": str(subject),
        "dependency_import_roots": [str(item) for item in dependencies],
        "verification_profile_locator": projection["profile_locator"],
        "environment_profile_id": projection["environment_profile_id"],
        "environment_profile_version": projection["environment_profile_version"],
        "environment_output_locators": projection["output_locators"],
        "adoption_id": projection["adoption_id"],
        "adoption_version": projection["adoption_version"],
        "source_id": projection["source_id"],
        "source_version": projection["source_version"],
        "decision_owner_ref": projection["decision_owner_ref"],
        "worker_identity": {
            "uid": identity["uid"],
            "gid": identity["gid"],
            "supplementary_gids": [],
            "umask": 0o77,
        },
    }
    context_raw = canonical_json_bytes(context)
    argv = [
        str(interpreter),
        "-I",
        "-S",
        "-B",
        str(projector),
        "--closed-context-stdin",
    ]
    environment = {
        "PATH": "",
        "LC_ALL": "C",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    started = _utc_now()
    completed = runner(
        argv,
        cwd=snapshot,
        environment=environment,
        uid=int(identity["uid"]),
        gid=int(identity["gid"]),
        stdin_bytes=context_raw,
        timeout_seconds=1800,
        stdout_limit=16 * 1024 * 1024,
        stderr_limit=1024 * 1024,
    )
    finished = _utc_now()
    if completed.returncode != 0:
        raise U10SnapshotProductionError(
            "u10_snapshot_environment_projection_failed",
            f"exit={completed.returncode}; stderr_digest={digest_bytes(completed.stderr)}",
        )
    try:
        result = strict_json_loads(completed.stdout)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise U10SnapshotProductionError(
            "u10_snapshot_environment_projection_unreadable", str(exc)
        ) from exc
    required_fields = {
        "schema_version",
        "host_identity_evidence",
        "containment_probe_evidence",
        "containment_trace_base64",
        "resolved_environment_profile",
        "environment_adoption_request",
        "eligibility_source",
        "formal_authority",
        "positive_assurance_allowed",
    }
    if (
        not isinstance(result, dict)
        or set(result) != required_fields
        or result.get("schema_version")
        != "semantic-guard-u10-snapshot-environment-projection-result/v1"
        or result.get("formal_authority") != "none"
        or result.get("positive_assurance_allowed") is not False
    ):
        raise U10SnapshotProductionError(
            "u10_snapshot_environment_projection_contract_mismatch", repr(result)
        )
    validations = (
        ("host_identity_evidence", "local-host-identity-evidence-v1.schema.json", "evidence_digest"),
        ("containment_probe_evidence", "process-containment-probe-v1.schema.json", "evidence_digest"),
        ("resolved_environment_profile", "resolved-local-environment-profile-v1.schema.json", "basis_digest"),
        ("environment_adoption_request", "local-environment-adoption-v1.schema.json", "adoption_digest"),
        ("eligibility_source", "environment-eligibility-source-v1.schema.json", "source_digest"),
    )
    for field, schema_name, seal_field in validations:
        value = result[field]
        if not isinstance(value, Mapping):
            raise U10SnapshotProductionError(
                "u10_snapshot_environment_projection_contract_mismatch", field
            )
        _validate_schema(
            value, schema_name, "u10_snapshot_environment_projection_contract_mismatch"
        )
        _verify_seal(
            value,
            seal_field,
            code="u10_snapshot_environment_projection_digest_mismatch",
        )
    try:
        trace_raw = base64.b64decode(
            result["containment_trace_base64"], validate=True
        )
    except (TypeError, ValueError) as exc:
        raise U10SnapshotProductionError(
            "u10_snapshot_containment_trace_unreadable", str(exc)
        ) from exc
    if len(trace_raw) > 16 * 1024 * 1024:
        raise U10SnapshotProductionError(
            "u10_snapshot_containment_trace_oversized", str(len(trace_raw))
        )
    evidence = result["containment_probe_evidence"]
    if (
        digest_bytes(trace_raw) != evidence["trace_ref"]["content_digest"]
        or evidence["trace_ref"]["locator"]
        != projection["output_locators"]["containment_trace"]
    ):
        raise U10SnapshotProductionError(
            "u10_snapshot_containment_trace_binding_mismatch",
            str(evidence.get("evidence_id")),
        )
    outputs: dict[str, bytes] = {
        projection["output_locators"]["host_identity_evidence"]: json_record_bytes(
            result["host_identity_evidence"]
        ),
        projection["output_locators"]["containment_probe_evidence"]: json_record_bytes(
            result["containment_probe_evidence"]
        ),
        projection["output_locators"]["containment_trace"]: trace_raw,
        projection["output_locators"]["resolved_environment_profile"]: json_record_bytes(
            result["resolved_environment_profile"]
        ),
        projection["output_locators"]["environment_adoption_request"]: json_record_bytes(
            result["environment_adoption_request"]
        ),
        projection["output_locators"]["eligibility_source"]: json_record_bytes(
            result["eligibility_source"]
        ),
    }
    if len(outputs) != len(projection["output_locators"]):
        raise U10SnapshotProductionError(
            "u10_snapshot_environment_output_collision", str(snapshot)
        )
    for relative, raw in sorted(outputs.items()):
        target = snapshot / Path(*_canonical_relative(
            relative, code="u10_snapshot_environment_output_path_invalid"
        ).parts)
        if target.exists() or target.is_symlink():
            raise U10SnapshotProductionError(
                "u10_snapshot_environment_output_preexists", relative
            )
        _write_all_bytes(target, raw, mode=0o444)
    _fsync_directory(snapshot / "vnext/validation/env-path-contracts")
    check = {
        "profile": "non-root-final-path-environment-projection/v1",
        "argv": argv,
        "effective_environment": environment,
        "worker_identity": context["worker_identity"],
        "started_at": started,
        "finished_at": finished,
        "exit_code": 0,
        "stdout_digest": digest_bytes(completed.stdout),
        "stderr_digest": digest_bytes(completed.stderr),
    }
    return result, check


def _tree_records(root: Path, *, exclude_manifest: bool = True) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for base, directories, files in os.walk(root, topdown=True, followlinks=False):
        directories.sort()
        files.sort()
        for name in [*directories, *files]:
            path = Path(base) / name
            if exclude_manifest and path == root / MANIFEST_NAME:
                continue
            observed = path.lstat()
            relative = path.relative_to(root).as_posix()
            if stat.S_ISDIR(observed.st_mode):
                records.append({"path": relative, "kind": "directory", "mode": stat.S_IMODE(observed.st_mode), "uid": observed.st_uid, "gid": observed.st_gid})
            elif stat.S_ISREG(observed.st_mode) and not stat.S_ISLNK(observed.st_mode):
                raw, _ = _read_regular(path, root=root)
                records.append({"path": relative, "kind": "file", "mode": stat.S_IMODE(observed.st_mode), "uid": observed.st_uid, "gid": observed.st_gid, "size": len(raw), "digest": digest_bytes(raw)})
            else:
                raise U10SnapshotProductionError("u10_snapshot_special_file", str(path))
    return records


def _subtree_digest(root: Path) -> dict[str, str]:
    return digest_bytes(canonical_json_bytes({"entries": _tree_records(root, exclude_manifest=False)}))


def _build_manifest_basis(
    *,
    authorization: Mapping[str, Any],
    candidate: Mapping[str, Any],
    projection: Mapping[str, Any],
    snapshot: Path,
    verified_at: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, dict[str, Any]]]:
    environment_projection = authorization["environment_projection"]
    candidate_entries = {
        _canonical_relative(
            item["path"], code="u10_snapshot_candidate_path_invalid"
        ).as_posix(): item
        for item in candidate["payload_denominator"]["entries"]
    }
    values: dict[str, dict[str, Any]] = {}
    raw_by_path: dict[str, bytes] = {}
    for base, directories, files in os.walk(snapshot, topdown=True, followlinks=False):
        directories.sort()
        files.sort()
        for name in files:
            path = Path(base) / name
            relative = path.relative_to(snapshot).as_posix()
            if relative in {MANIFEST_NAME, ".projection-owner.json"}:
                continue
            raw, _ = _read_regular(
                path, root=snapshot, allowed_modes={0o444, 0o555}
            )
            raw_by_path[relative] = raw
            try:
                value = strict_json_loads(raw)
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
            if isinstance(value, dict):
                values[relative] = value
    candidate_manifest_path = "vnext/governance/u10-root-candidate-bundle.json"
    candidate_projection_path = "vnext/governance/u10-candidate-install-projection.json"
    if candidate_manifest_path not in values or candidate_projection_path not in values:
        raise U10SnapshotProductionError(
            "u10_snapshot_candidate_metadata_missing", str(snapshot)
        )

    ref_index: dict[tuple[str, str], str] = {}
    for value in values.values():
        _walk_refs(value, ref_index)
    boundary = candidate["preactivation_boundary_refs"]
    special_records = {
        boundary["decision_record_ref"]["bundled_locator"]: ("decision_record_ref", "u10_preactivation_decision_record"),
        boundary["worker_account_observation_ref"]["bundled_locator"]: ("worker_account_observation_ref", "u10_worker_account_observation"),
        boundary["worker_principal_resolution_ref"]["bundled_locator"]: ("worker_principal_resolution_ref", "u10_worker_principal_resolution"),
    }
    artifacts: dict[str, dict[str, Any]] = {}
    by_role: dict[str, list[tuple[str, dict[str, Any], dict[str, Any] | None]]] = {}
    boundary_refs: dict[str, Any] = {}
    for relative, raw in sorted(raw_by_path.items()):
        semantic, value = _semantic_digest(raw)
        artifact_id = f"artifact.snapshot.{hashlib.sha256(relative.encode('utf-8')).hexdigest()}"
        if relative == candidate_manifest_path:
            role = "u10_candidate_bundle_manifest"
            source_ref = {
                "record_id": candidate["bundle_id"],
                "locator": str(Path(projection["projected_candidate_path"]) / "bundle-manifest.json"),
                "artifact_digest": digest_bytes(raw),
                "semantic_digest": candidate["bundle_digest"],
            }
        elif relative == candidate_projection_path:
            role = "u10_candidate_install_projection"
            source_ref = {
                "record_id": projection["projection_id"],
                "locator": str(Path(projection["projected_candidate_path"]) / "install-projection.json"),
                "artifact_digest": digest_bytes(raw),
                "semantic_digest": projection["projection_digest"],
            }
        else:
            candidate_entry = candidate_entries.get(relative)
            candidate_role = str(candidate_entry["role"]) if candidate_entry else "root_generated"
            role = _artifact_role(
                relative,
                candidate_role,
                value,
                environment_projection=environment_projection,
            )
            original = candidate_entry.get("source_ref") if candidate_entry else None
            locator = (
                str(original["locator"])
                if isinstance(original, Mapping)
                else relative
            )
            raw_digest = digest_bytes(raw)
            source_record_id = ref_index.get((locator, raw_digest["value"]))
            if relative == environment_projection["output_locators"]["eligibility_source"]:
                source_record_id = str(value.get("source_id")) if value else None
            elif relative == environment_projection["output_locators"]["resolved_environment_profile"]:
                source_record_id = str(value.get("environment_profile_id")) if value else None
            elif relative == environment_projection["output_locators"]["host_identity_evidence"]:
                source_record_id = str(value.get("evidence_id")) if value else None
            elif relative == environment_projection["output_locators"]["containment_probe_evidence"]:
                source_record_id = str(value.get("evidence_id")) if value else None
            elif relative == environment_projection["output_locators"]["environment_adoption_request"]:
                source_record_id = str(value.get("adoption_id")) if value else None
            if not source_record_id:
                source_record_id = f"source.snapshot.{hashlib.sha256(relative.encode('utf-8')).hexdigest()}"
            source_ref = {
                "record_id": source_record_id,
                "locator": locator,
                "artifact_digest": raw_digest,
                "semantic_digest": semantic,
            }
            if relative in special_records:
                field, role = special_records[relative]
                record = boundary[field]
                source_ref = {
                    "record_id": record["record_id"],
                    "locator": str(Path(projection["projected_candidate_path"]) / "payload" / relative),
                    "artifact_digest": digest_bytes(raw),
                    "semantic_digest": record["semantic_digest"],
                }
        if artifact_id in artifacts:
            raise U10SnapshotProductionError(
                "u10_snapshot_artifact_identity_collision", relative
            )
        snapshot_ref = {"record_id": artifact_id, "locator": str(snapshot / relative), "artifact_digest": digest_bytes(raw), "semantic_digest": semantic}
        artifact = {"role": role, "source_ref": source_ref, "snapshot_ref": snapshot_ref}
        artifacts[artifact_id] = artifact
        by_role.setdefault(role, []).append((artifact_id, artifact, value))
        if relative in special_records:
            field, _role = special_records[relative]
            record = boundary[field]
            boundary_refs[field] = {
                "record_id": record["record_id"],
                "source_locator": record["source_locator"],
                "source_artifact_digest": record["source_artifact_digest"],
                "candidate_relative_locator": record["bundled_locator"],
                "candidate_artifact_digest": record["bundled_artifact_digest"],
                "semantic_digest": record["semantic_digest"],
                "snapshot_artifact_ref": snapshot_ref,
            }

    def one(role: str) -> tuple[str, dict[str, Any], dict[str, Any]]:
        matches = by_role.get(role, [])
        if len(matches) != 1 or not isinstance(matches[0][2], dict):
            raise U10SnapshotProductionError("u10_snapshot_role_denominator_mismatch", role)
        return matches[0][0], matches[0][1], matches[0][2]

    _source_id, source_artifact, source = one("eligibility_source")
    _profile_id, profile_artifact, profile = one("verification_profile")
    _environment_id, environment_artifact, environment = one("environment_profile")
    _host_id, host_artifact, host = one("host_identity_evidence")
    _request_id, request_artifact, adoption_request = one(
        "environment_adoption_request"
    )
    if (
        source.get("lifecycle_state") != "candidate"
        or source.get("adoption_record") != adoption_request
        or adoption_request.get("record_kind") != "adoption_request"
        or adoption_request.get("human_decision") != "pending"
        or adoption_request.get("recorded_at") is not None
        or adoption_request.get("decision_owner_ref")
        != environment_projection["decision_owner_ref"]
        or environment.get("host_identity_ref", {}).get("identity_digest") != host.get("identity_digest")
    ):
        raise U10SnapshotProductionError(
            "u10_snapshot_projected_environment_binding_mismatch",
            str(source.get("source_id")),
        )
    decision = one("u10_preactivation_decision_record")[2]
    resolution = one("u10_worker_principal_resolution")[2]
    candidate_manifest_artifact = one("u10_candidate_bundle_manifest")[1]
    candidate_ref = {
        "bundle_id": candidate["bundle_id"],
        "bundle_version": candidate["bundle_version"],
        "candidate_locator": str(Path(projection["projected_candidate_path"]) / "bundle-manifest.json"),
        "artifact_digest": digest_bytes(raw_by_path[candidate_manifest_path]),
        "bundle_digest": candidate["bundle_digest"],
        "snapshot_artifact_ref": candidate_manifest_artifact["snapshot_ref"],
    }
    preactivation = {
        "profile": boundary["profile"],
        "candidate_bundle_ref": candidate_ref,
        "boundary_binding_digest": boundary["binding_digest"],
        **boundary_refs,
        "subject_entity_id": _entity_id(decision["subject_entity_ref"], code="u10_subject_entity_ref_invalid"),
        "worker_principal_entity_id": _entity_id(resolution["principal_entity_ref"], code="u10_principal_entity_ref_invalid"),
        "threat_boundary": boundary["threat_boundary"],
        "worker_identity_policy": boundary["worker_identity_policy"],
        "qualification_scope": boundary["qualification_scope"],
        "hostile_code_assurance": boundary["hostile_code_assurance"],
        "requalification_triggers": boundary["requalification_triggers"],
        "effective_worker_identity": {"uid": resolution["uid"], "gid": resolution["gid"], "effective_supplementary_gids": resolution["effective_supplementary_gids"], "umask": resolution["umask"]},
    }

    def source_ref(artifact: Mapping[str, Any]) -> dict[str, Any]:
        return dict(artifact["source_ref"])

    projected_environment_basis: dict[str, Any] = {
        "eligibility_source_ref": {
            "source_id": source["source_id"],
            "source_version": source["source_version"],
            "lifecycle_state": "candidate",
            "snapshot_artifact_ref": source_artifact["snapshot_ref"],
            "source_digest": source["source_digest"],
        },
        "verification_profile_ref": {
            "profile_id": profile["profile_id"],
            "profile_version": profile["profile_version"],
            "snapshot_artifact_ref": profile_artifact["snapshot_ref"],
            "content_digest": environment["verification_profile_ref"]["content_digest"],
        },
        "environment_profile_ref": {
            "environment_profile_id": environment["environment_profile_id"],
            "environment_profile_version": environment["environment_profile_version"],
            "lifecycle_state": "candidate",
            "snapshot_artifact_ref": environment_artifact["snapshot_ref"],
            "basis_digest": environment["basis_digest"],
        },
        "host_identity_evidence_ref": {
            "evidence_id": host["evidence_id"],
            "snapshot_artifact_ref": host_artifact["snapshot_ref"],
            "identity_digest": host["identity_digest"],
            "evidence_digest": host["evidence_digest"],
        },
        "decision_owner_ref": environment_projection["decision_owner_ref"],
    }
    projected_environment_basis["basis_digest"] = digest_bytes(
        canonical_json_bytes(projected_environment_basis)
    )

    command_bindings: dict[str, Any] = {}
    for command in profile["commands"]:
        closed_ref = command["closed_test_manifest_ref"]
        closed_matches = [item for item in by_role.get("closed_test_manifest", []) if item[2] and item[2].get("manifest_id") == closed_ref["record_id"]]
        if len(closed_matches) != 1:
            raise U10SnapshotProductionError("u10_closed_manifest_missing", str(command["command_id"]))
        _closed_id, closed_artifact, closed = closed_matches[0]
        command_bindings[command["command_id"]] = {
            "command_definition_digest": digest_bytes(canonical_json_bytes(command)),
            "closed_test_manifest_ref": {
                "manifest_id": closed["manifest_id"],
                "manifest_version": closed["manifest_version"],
                "source_artifact_ref": source_ref(closed_artifact),
                "snapshot_artifact_ref": closed_artifact["snapshot_ref"],
                "manifest_digest": closed["manifest_digest"],
            },
            "governed_command_timeout_seconds": command["timeout_seconds"],
            "required_snapshot_artifact_ids": sorted(artifacts),
        }
    worker_bootstrap = [item for item in by_role.get("broker_runtime", []) if item[1]["snapshot_ref"]["locator"].endswith("/vnext/scripts/u10_root_broker_bootstrap.py")]
    worker_entry = by_role.get("worker_entrypoint", [])
    interpreter = by_role.get("python_interpreter", [])
    if len(worker_bootstrap) != 1 or len(worker_entry) != 1 or len(interpreter) != 1:
        raise U10SnapshotProductionError("u10_snapshot_runtime_denominator_mismatch", "bootstrap/worker/python")
    subject_root = snapshot / candidate["dependency_environment_policy"]["snapshot_source_root"]
    dependency_root = snapshot / candidate["dependency_environment_policy"]["dependency_import_root"]
    subject_ids = sorted(artifact_id for artifact_id, artifact in artifacts.items() if Path(artifact["snapshot_ref"]["locator"]).is_relative_to(subject_root))
    dependency_ids = sorted(artifact_id for artifact_id, artifact in artifacts.items() if Path(artifact["snapshot_ref"]["locator"]).is_relative_to(dependency_root))
    tree_digest = digest_bytes(canonical_json_bytes({"entries": _tree_records(snapshot)}))
    target = authorization["target_snapshot"]
    manifest: dict[str, Any] = {
        "schema_version": "semantic-guard-u10-execution-snapshot-manifest/v1",
        "snapshot_id": target["snapshot_id"],
        "snapshot_version": target["snapshot_version"],
        "lifecycle_state": "candidate",
        "prepared_for_entry_id": target["entry_id"],
        "source_repository_binding": candidate["source_repository_binding"],
        "preactivation_boundary_binding": preactivation,
        "root_storage": {"snapshot_root": str(snapshot.parent), "snapshot_path": str(snapshot), "storage_state": "candidate", "owner_uid": 0, "owner_gid": 0, "directory_mode": "0555", "mutation_policy": "no_mutation_after_manifest_seal/v1", "tree_digest": tree_digest},
        "broker_runtime_ref": worker_bootstrap[0][1]["snapshot_ref"],
        "broker_launch_contract": {"invocation_mode": "fixed_root_wrapper_outer_verifier_then_snapshot_execve/v2", "entrypoint_ref": authorization["broker_entrypoint_ref"], "outer_launcher_ref": authorization["broker_outer_launcher_ref"], "platform_binding_digest": digest_bytes(canonical_json_bytes(authorization["broker_launch_platform"])), "python_flags": ["-I", "-S", "-B"], "caller_fields": ["entry_id", "command_id", "request_nonce"], "environment_policy": "env_i_direct_qualified_python_then_exact_snapshot_execve/v3"},
        "eligibility_source_ref": {"source_id": source["source_id"], "source_version": source["source_version"], "lifecycle_state": source["lifecycle_state"], "source_artifact_ref": source_ref(source_artifact), "snapshot_artifact_ref": source_artifact["snapshot_ref"], "source_digest": source["source_digest"]},
        "verification_profile_ref": {"profile_id": profile["profile_id"], "profile_version": profile["profile_version"], "source_artifact_ref": source_ref(profile_artifact), "snapshot_artifact_ref": profile_artifact["snapshot_ref"], "content_digest": environment["verification_profile_ref"]["content_digest"]},
        "environment_profile_ref": {"environment_profile_id": environment["environment_profile_id"], "environment_profile_version": environment["environment_profile_version"], "source_artifact_ref": source_ref(environment_artifact), "snapshot_artifact_ref": environment_artifact["snapshot_ref"], "basis_digest": environment["basis_digest"]},
        "environment_adoption_ref": None,
        "worker_identity": {"uid": resolution["uid"], "gid": resolution["gid"], "account_supplementary_gids": resolution["account_supplementary_gids"], "effective_supplementary_gids": resolution["effective_supplementary_gids"], "umask": resolution["umask"], "login_shell": resolution["login_shell"], "non_login": resolution["non_login"], "root_prohibited": True, "principal_entity_id": _entity_id(resolution["principal_entity_ref"], code="u10_principal_entity_ref_invalid"), "principal_resolution_digest": resolution["resolution_digest"]},
        "worker_runtime": {"worker_version": "3.0.0-candidate", "interpreter_snapshot_ref": interpreter[0][1]["snapshot_ref"], "worker_entrypoint_snapshot_ref": worker_entry[0][1]["snapshot_ref"], "subject_source_root": {"tree_id": "tree.u10.subject", "locator": str(subject_root), "tree_digest": _subtree_digest(subject_root), "required_artifact_ids": subject_ids}, "dependency_import_roots": [{"tree_id": "tree.u10.dependencies", "locator": str(dependency_root), "tree_digest": _subtree_digest(dependency_root), "required_artifact_ids": dependency_ids}], "phase_budget": {"profile": "u10-compositional-worker-budget/v1", "pre_environment_reobservation_seconds": 240, "post_environment_reobservation_seconds": 240, "evidence_finalization_seconds": 30, "process_reap_seconds": 10}, "launch_contract": {"invocation_mode": "root_supervisor_exact_snapshot_worker/v1", "python_flags": ["-I", "-S", "-B"], "caller_supplied_argv_allowed": False, "working_directory_policy": "snapshot_root_exact", "process_group_policy": "worker_and_inner_runner_share_root_reaped_group/v1"}},
        "artifact_denominator": {"status": "closed", "entries": artifacts},
        "command_bindings": command_bindings,
        "immutability_verification": {"status": "pending", "verified_at": None, "verifier_runtime_ref": None, "checks": ["root_ownership_exact", "directory_not_writable_by_worker", "artifact_denominator_digest_exact", "tree_digest_exact", "command_manifest_bindings_exact", "broker_runtime_digest_exact"]},
        "snapshot_adoption_authorization_ref": None,
        "activation_ref": None,
        "revocation_ref": None,
        "u4_authority_resolution": {"requirement_id": "U-4", "status": "unresolved", "consequence": "does_not_establish_principal_identity_delegation_or_revocation_authority", "resolution_ref": None},
        "formal_authority": "none",
        "positive_assurance_allowed": False,
        "limitations": ["Snapshot activation does not establish engineering correctness.", "U-4 principal authenticity remains unresolved.", "Environment use requires a separate root-held exact snapshot-environment adoption decision.", "Qualification is limited to the externally adopted closed local verification suite."],
    }
    manifest["snapshot_basis_digest"] = snapshot_basis_digest_v1(manifest)
    manifest["manifest_digest"] = sealed_digest(manifest, "manifest_digest")
    _validate_schema(
        manifest,
        "u10-execution-snapshot-manifest-v1.schema.json",
        "u10_snapshot_candidate_manifest_basis_invalid",
    )
    return (
        manifest,
        {
            "adoption_request": adoption_request,
            "adoption_request_artifact": request_artifact,
            "projected_environment_basis": projected_environment_basis,
            "verified_at": verified_at,
        },
        artifacts,
    )


def project_snapshot_by_authorization_id(
    authorization_id: str,
    *,
    publisher_contract_binding: Mapping[str, Any],
    paths: SnapshotPaths = SnapshotPaths(),
    required_uid: int = 0,
    enforce_fixed_paths: bool = True,
    dependency_runner: Callable[..., subprocess.CompletedProcess[bytes]] = _default_dependency_runner,
    projector_runner: Callable[..., subprocess.CompletedProcess[bytes]] = _bounded_worker_run,
) -> dict[str, Any]:
    if required_uid == 0 and os.geteuid() != 0:
        raise U10SnapshotProductionError("u10_snapshot_projection_requires_root", str(os.geteuid()))
    if enforce_fixed_paths:
        _validate_fixed_roots(paths, required_uid=required_uid)
    publisher = _validate_publisher_contract_binding(
        publisher_contract_binding, operation="project-snapshot"
    )
    authorization, authorization_raw = _load_projection_authorization(authorization_id, paths=paths, enforce_fixed_paths=enforce_fixed_paths)
    candidate, candidate_raw, projection, projection_raw = _verify_installed_candidate(authorization, paths=paths)
    ledger = paths.projection_ledger_root
    auth_path = ledger / f"{authorization_id}.authorization.json"
    consumption_path = ledger / f"{authorization_id}.consumption.json"
    receipt_path = ledger / f"{authorization_id}.receipt.json"
    target = Path(authorization["target_snapshot"]["snapshot_path"])
    occurrence = f"snapshot-projection.{authorization['authorization_digest']['value']}"
    marker = {"schema_version": "semantic-guard-u10-snapshot-projection-owner/v1", "authorization_id": authorization_id, "occurrence_id": occurrence, "authorization_digest": authorization["authorization_digest"]}
    with _lock(ledger, _PROJECTION_LOCK_NAME):
        existing_receipt = _load_optional_record(receipt_path, root=ledger)
        if existing_receipt is not None:
            receipt = existing_receipt[0]
            _validate_schema(receipt, "u10-snapshot-projection-receipt-v1.schema.json", "u10_projection_receipt_invalid")
            _verify_seal(receipt, "receipt_digest", code="u10_projection_receipt_digest_mismatch")
            if (
                receipt["authorization_ref"]["authorization_digest"]
                != authorization["authorization_digest"]
                or receipt["public_identifier"] != authorization_id
                or receipt["publisher_contract_binding"] != publisher
                or receipt["snapshot_ref"] != authorization["target_snapshot"]
                or not target.is_dir()
                or (target / MANIFEST_NAME).exists()
                or digest_bytes(
                    canonical_json_bytes({"entries": _tree_records(target)})
                )
                != receipt["tree_digest"]
            ):
                raise U10SnapshotProductionError("u10_projection_receipt_collision", authorization_id)
            rebuilt, context, artifacts = _build_manifest_basis(
                authorization=authorization,
                candidate=candidate,
                projection=projection,
                snapshot=target,
                verified_at=receipt["immutability_verified_at"],
            )
            if (
                rebuilt["snapshot_basis_digest"] != receipt["snapshot_basis_digest"]
                or context["projected_environment_basis"]
                != receipt["projected_environment_basis"]
                or digest_bytes(canonical_json_bytes(artifacts))
                != receipt["artifact_denominator"]["denominator_digest"]
            ):
                raise U10SnapshotProductionError(
                    "u10_projection_receipt_reconciliation_failed", authorization_id
                )
            return receipt
        _publish_append_only_record(
            auth_path, authorization, ledger_root=ledger, mode=0o400
        )
        archived, archived_raw = _load_record(auth_path, root=ledger)
        if archived != authorization or archived_raw != authorization_raw:
            raise U10SnapshotProductionError(
                "u10_projection_authorization_archive_collision", authorization_id
            )
        existing_consumption = _load_optional_record(consumption_path, root=ledger)
        if existing_consumption is None:
            if target.exists() or target.is_symlink():
                raise U10SnapshotProductionError(
                    "u10_projection_unowned_target_collision", str(target)
                )
            consumption = {"schema_version": "semantic-guard-u10-snapshot-projection-authorization-consumption/v1", "consumption_id": f"consumption.{authorization_id}", "record_kind": "snapshot_projection_authorization_consumption", "public_operation": "project-snapshot", "public_identifier": authorization_id, "authorization_ref": {"authorization_id": authorization_id, "artifact_digest": digest_bytes(authorization_raw), "authorization_digest": authorization["authorization_digest"]}, "bundle_ref": authorization["bundle_ref"], "target_snapshot": authorization["target_snapshot"], "occurrence_id": occurrence, "reserved_at": _utc_now(), "publisher_contract_binding": publisher, "projection_occurred": False, "formal_authority": "none", "positive_assurance_allowed": False}
            consumption["consumption_digest"] = sealed_digest(consumption, "consumption_digest")
            _validate_schema(consumption, "u10-snapshot-projection-authorization-consumption-v1.schema.json", "u10_projection_consumption_invalid")
            _publish_append_only_record(
                consumption_path, consumption, ledger_root=ledger, mode=0o400
            )
        else:
            consumption = existing_consumption[0]
            _validate_schema(consumption, "u10-snapshot-projection-authorization-consumption-v1.schema.json", "u10_projection_consumption_invalid")
            _verify_seal(consumption, "consumption_digest", code="u10_projection_consumption_digest_mismatch")
            if (
                consumption["authorization_ref"]["authorization_digest"]
                != authorization["authorization_digest"]
                or consumption["public_identifier"] != authorization_id
                or consumption["publisher_contract_binding"] != publisher
                or consumption["target_snapshot"] != authorization["target_snapshot"]
            ):
                raise U10SnapshotProductionError("u10_projection_consumption_collision", authorization_id)
        if target.exists() or target.is_symlink():
            _remove_owned_partial(target, marker, allow_missing_marker=True)
        _copy_candidate_to_snapshot(manifest=candidate, manifest_raw=candidate_raw, projection=projection, projection_raw=projection_raw, snapshot=target, marker=marker)
        _set_projection_modes(target)
        dependency_check = _run_dependency_check(manifest=candidate, snapshot=target, runner=dependency_runner)
        _projection_result, environment_projection_check = _run_environment_projection(
            authorization=authorization,
            candidate=candidate,
            snapshot=target,
            runner=projector_runner,
        )
        _set_projection_modes(target)
        (target / ".projection-owner.json").unlink()
        _fsync_directory(target)
        verified_at = _utc_now()
        manifest_basis, context, artifacts = _build_manifest_basis(authorization=authorization, candidate=candidate, projection=projection, snapshot=target, verified_at=verified_at)
        projection_observed_at = _utc_now()
        receipt: dict[str, Any] = {"schema_version": "semantic-guard-u10-snapshot-projection-receipt/v1", "receipt_id": f"receipt.{authorization_id}", "record_kind": "inactive_snapshot_projection_occurrence", "public_operation": "project-snapshot", "public_identifier": authorization_id, "occurrence_id": occurrence, "authorization_ref": consumption["authorization_ref"], "consumption_ref": {"consumption_id": consumption["consumption_id"], "consumption_digest": consumption["consumption_digest"]}, "bundle_ref": authorization["bundle_ref"], "snapshot_ref": authorization["target_snapshot"], "dependency_lock_check": dependency_check, "environment_projection_check": environment_projection_check, "projected_environment_basis": context["projected_environment_basis"], "artifact_denominator": {"status": "closed", "entry_count": len(artifacts), "denominator_digest": digest_bytes(canonical_json_bytes(artifacts))}, "tree_digest": manifest_basis["root_storage"]["tree_digest"], "snapshot_basis_digest": manifest_basis["snapshot_basis_digest"], "immutability_verified_at": verified_at, "publication_not_before": consumption["reserved_at"], "projection_observed_at": projection_observed_at, "receipt_recorded_at": _utc_now(), "publisher_contract_binding": publisher, "projection_occurred": True, "snapshot_manifest_published": False, "snapshot_adoption_status": "pending_human_decision", "formal_authority": "none", "positive_assurance_allowed": False}
        receipt["receipt_digest"] = sealed_digest(receipt, "receipt_digest")
        _validate_schema(receipt, "u10-snapshot-projection-receipt-v1.schema.json", "u10_projection_receipt_invalid")
        if not (_time(consumption["reserved_at"], code="u10_projection_time_invalid") <= _time(dependency_check["started_at"], code="u10_projection_time_invalid") <= _time(dependency_check["finished_at"], code="u10_projection_time_invalid") <= _time(environment_projection_check["started_at"], code="u10_projection_time_invalid") <= _time(environment_projection_check["finished_at"], code="u10_projection_time_invalid") <= _time(verified_at, code="u10_projection_time_invalid") <= _time(projection_observed_at, code="u10_projection_time_invalid") <= _time(receipt["receipt_recorded_at"], code="u10_projection_time_invalid")):
            raise U10SnapshotProductionError("u10_projection_time_order_invalid", authorization_id)
        _publish_append_only_record(
            receipt_path, receipt, ledger_root=ledger, mode=0o400
        )
        return receipt


def _root_ref(record_id: str, path: Path, raw: bytes, semantic: Mapping[str, Any]) -> dict[str, Any]:
    return {"record_id": record_id, "locator": str(path), "artifact_digest": digest_bytes(raw), "semantic_digest": dict(semantic)}


def _verify_root_artifact_ref(
    reference: Mapping[str, Any], *, paths: SnapshotPaths, code: str
) -> bytes:
    path = Path(str(reference.get("locator", "")))
    raw, _ = _read_regular(
        path,
        root=paths.u10_root,
        allowed_modes={0o400, 0o444, 0o500, 0o555},
    )
    semantic, _value = _semantic_digest(raw)
    if (
        digest_bytes(raw) != reference.get("artifact_digest")
        or semantic != reference.get("semantic_digest")
    ):
        raise U10SnapshotProductionError(code, str(path))
    return raw


def _load_snapshot_environment_adoption(
    reference: Mapping[str, Any],
    *,
    paths: SnapshotPaths,
    projection: Mapping[str, Any],
    projection_path: Path,
    projection_raw: bytes,
) -> tuple[dict[str, Any], bytes]:
    raw = _verify_root_artifact_ref(
        reference, paths=paths, code="u10_snapshot_environment_adoption_ref_mismatch"
    )
    adoption = _json(raw, code="u10_snapshot_environment_adoption_unreadable")
    _validate_schema(
        adoption,
        "u10-snapshot-environment-adoption-v1.schema.json",
        "u10_snapshot_environment_adoption_invalid",
    )
    _verify_seal(
        adoption,
        "adoption_digest",
        code="u10_snapshot_environment_adoption_digest_mismatch",
    )
    if raw != canonical_json_bytes(adoption) + b"\n":
        raise U10SnapshotProductionError(
            "u10_snapshot_environment_adoption_noncanonical",
            str(reference.get("locator", "")),
        )
    exact_ref = _root_ref(
        adoption["adoption_id"],
        Path(str(reference["locator"])),
        raw,
        adoption["adoption_digest"],
    )
    projection_ref = _root_ref(
        projection["receipt_id"],
        projection_path,
        projection_raw,
        projection["receipt_digest"],
    )
    expected_snapshot_ref = {
        "snapshot_id": projection["snapshot_ref"]["snapshot_id"],
        "snapshot_version": projection["snapshot_ref"]["snapshot_version"],
        "snapshot_path": projection["snapshot_ref"]["snapshot_path"],
        "tree_digest": projection["tree_digest"],
        "snapshot_basis_digest": projection["snapshot_basis_digest"],
    }
    basis = projection["projected_environment_basis"]
    if (
        dict(reference) != exact_ref
        or adoption["projection_receipt_ref"] != projection_ref
        or adoption["snapshot_ref"] != expected_snapshot_ref
        or adoption["eligibility_source_ref"] != basis["eligibility_source_ref"]
        or adoption["verification_profile_ref"] != basis["verification_profile_ref"]
        or adoption["environment_profile_ref"] != basis["environment_profile_ref"]
        or adoption["host_identity_evidence_ref"]
        != basis["host_identity_evidence_ref"]
        or adoption["decision_owner_ref"] != basis["decision_owner_ref"]
        or adoption["formal_authority"] != "none"
        or adoption["positive_assurance_allowed"] is not False
    ):
        raise U10SnapshotProductionError(
            "u10_snapshot_environment_adoption_binding_mismatch",
            str(adoption.get("adoption_id")),
        )
    for field in (
        "decision_owner_authority_evidence_ref",
        "decision_evidence_ref",
        "trusted_entrypoint_ref",
    ):
        _verify_root_artifact_ref(
            adoption[field],
            paths=paths,
            code=f"u10_snapshot_environment_{field}_mismatch",
        )
    return adoption, raw


def _active_signing_key_context(
    *, paths: SnapshotPaths
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Project a fully replayed v2 key head into the root-store contract."""

    key_root = paths.u10_root / "keys"
    key_paths = KeyChainPaths(
        u10_root=paths.u10_root,
        ledger_root=paths.u10_root / "activations" / "key-transitions",
        key_root=key_root,
        generation_root=key_root / "generations",
        revocation_root=key_root / "revocations",
        selector_history_root=key_root / "selector-history" / "sha256",
        selector_path=key_root / "current.json",
        lock_path=key_root / "key-transition.lock",
    )
    try:
        replay = resolve_current_signing_key_chain_v2_under_trust_store_lock(
            paths=key_paths,
            required_uid=0 if paths == SnapshotPaths() else os.geteuid(),
        )
    except BrokerBoundaryError as exc:
        raise U10SnapshotProductionError(exc.code, exc.detail) from exc
    active_key = replay.get("active_key")
    selector_ref = replay.get("current_selector_ref")
    if not isinstance(active_key, Mapping) or not isinstance(
        selector_ref, Mapping
    ):
        raise U10SnapshotProductionError(
            "u10_active_signing_key_required",
            str(replay.get("current_selector", {}).get("state")),
        )
    metadata = active_key["public_metadata"]
    metadata_ref = active_key["public_metadata_ref"]
    private_ref = active_key["private_material_ref"]
    private_path = Path(str(private_ref["locator"]))
    binding = {
        "key_id": metadata["key_id"],
        "key_state": "active",
        "algorithm": "ed25519",
        "public_key_base64": metadata["public_key"]["value"],
        "private_key_path": str(private_path),
        "private_key_owner_uid": 0,
        "private_key_owner_gid": 0,
        "private_key_mode": "0600",
        "key_usage": "u10_broker_execution_attestation_only",
    }
    return (
        binding,
        _strict_json_clone(metadata_ref),
        _strict_json_clone(selector_ref),
    )


def _active_signing_key_binding(*, paths: SnapshotPaths) -> dict[str, Any]:
    """Compatibility helper for callers needing only the store projection."""

    return _active_signing_key_context(paths=paths)[0]


def _store_entry_from_active_snapshot(
    *, manifest: Mapping[str, Any], manifest_ref: Mapping[str, Any]
) -> dict[str, Any]:
    def source_binding(
        reference: Mapping[str, Any],
        *,
        identity_fields: Sequence[str],
        digest_field: str,
        lifecycle: bool = False,
    ) -> dict[str, Any]:
        source = reference["source_artifact_ref"]
        value = {field: reference[field] for field in identity_fields}
        if lifecycle:
            value["lifecycle_state"] = reference["lifecycle_state"]
        value.update(
            {
                "locator": source["locator"],
                "artifact_digest": source["artifact_digest"],
                digest_field: reference[digest_field],
            }
        )
        return value

    commands: dict[str, Any] = {}
    for command_id, command in manifest["command_bindings"].items():
        closed = command["closed_test_manifest_ref"]
        source = closed["source_artifact_ref"]
        snapshot = closed["snapshot_artifact_ref"]
        common = {
            "manifest_id": closed["manifest_id"],
            "manifest_version": closed["manifest_version"],
            "artifact_digest": source["artifact_digest"],
            "manifest_digest": closed["manifest_digest"],
        }
        commands[str(command_id)] = {
            "command_definition_digest": command["command_definition_digest"],
            "closed_test_manifest_binding": {
                **common,
                "locator": source["locator"],
            },
            "snapshot_closed_test_manifest_ref": {
                **common,
                "locator": snapshot["locator"],
                "artifact_digest": snapshot["artifact_digest"],
            },
        }
    entry: dict[str, Any] = {
        "entry_state": "active",
        "repository_binding": {
            field: manifest["source_repository_binding"][field]
            for field in ("canonical_path", "device_id", "inode")
        },
        "snapshot_manifest_binding": {
            "snapshot_id": manifest["snapshot_id"],
            "snapshot_version": manifest["snapshot_version"],
            "lifecycle_state": "active",
            "locator": manifest_ref["locator"],
            "artifact_digest": manifest_ref["artifact_digest"],
            "manifest_digest": manifest["manifest_digest"],
        },
        "preactivation_boundary_binding": manifest[
            "preactivation_boundary_binding"
        ],
        "eligibility_source_binding": source_binding(
            manifest["eligibility_source_ref"],
            identity_fields=("source_id", "source_version"),
            digest_field="source_digest",
            lifecycle=True,
        ),
        "verification_profile_binding": source_binding(
            manifest["verification_profile_ref"],
            identity_fields=("profile_id", "profile_version"),
            digest_field="content_digest",
        ),
        "environment_profile_binding": source_binding(
            manifest["environment_profile_ref"],
            identity_fields=(
                "environment_profile_id",
                "environment_profile_version",
            ),
            digest_field="basis_digest",
        ),
        "environment_adoption_binding": manifest["environment_adoption_ref"],
        "commands": commands,
        "execution_uid": manifest["worker_identity"]["uid"],
        "execution_gid": manifest["worker_identity"]["gid"],
        "execution_supplementary_gids": manifest["worker_identity"][
            "effective_supplementary_gids"
        ],
        "execution_umask": manifest["worker_identity"]["umask"],
        "granted_capability": "verification_process_launch",
        "formal_authority": "none",
        "positive_assurance_allowed": False,
    }
    entry["entry_digest"] = sealed_digest(entry, "entry_digest")
    return entry


def _initial_store_content(
    *,
    manifest: Mapping[str, Any],
    manifest_ref: Mapping[str, Any],
    projection_authorization: Mapping[str, Any],
    signing_key: Mapping[str, Any],
    store_revision_id: str,
    prior_store: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if prior_store is None:
        content: dict[str, Any] = {
            "schema_version": "semantic-guard-u10-root-trust-store/v2",
            "store_id": "store.u10.semantic-guard",
            "store_version": "2.0.0",
            "current_selector": {
                "path": str(U10_ROOT / "trust-store-current.json"),
                "owner_uid": 0, "owner_gid": 0, "mode": "0444",
                "publication_policy": "history_fsync_before_atomic_current_replace/v1",
                "activation_ledger_path": str(U10_ROOT / "activations/store-transitions"),
                "activation_ledger_policy": STORE_ACTIVATION_LEDGER_POLICY_V3,
                "activation_ledger_retention_policy": STORE_LEDGER_RETENTION_POLICY_V1,
                "revocation_selector_path": str(U10_ROOT / "trust-store-current-revocation.json"),
                "revocation_history_path": str(U10_ROOT / "revocations/sha256"),
                "revocation_ledger_path": str(U10_ROOT / "activations/store-revocations"),
                "revocation_ledger_policy": STORE_REVOCATION_LEDGER_POLICY_V2,
                "revocation_ledger_retention_policy": STORE_LEDGER_RETENTION_POLICY_V1,
                "revocation_decision_root_path": str(U10_ROOT / "authorizations"),
                "revocation_decision_entry_policy": "fixed_root_record_id_resolution_no_caller_raw/v1",
                "revocation_publication_policy": "decision_consumption_history_selector_interval_receipt_recovery/v4",
            },
            "trust_store_history": {"path": str(U10_ROOT / "trust-store-history/sha256"), "owner_uid": 0, "owner_gid": 0, "directory_mode": "0755", "artifact_mode": "0444", "address_profile": "sha256_raw_artifact_filename/v1", "write_policy": "root_o_excl_create_once_no_replace/v1", "retention_policy": "no_automatic_deletion_while_referenced/v1"},
            "coordination_lock": {"path": str(U10_ROOT / "trust-store.lock"), "owner_uid": 0, "owner_gid": 0, "mode": "0600", "protocol": "shared_execution_exclusive_activation_flock/v1"},
            "snapshot_root": {"path": str(U10_ROOT / "snapshots"), "resource_state": "active", "owner_uid": 0, "owner_gid": 0, "mode": "0755", "write_policy": "root_broker_content_addressed_snapshot_only/v1"},
            "nonce_ledger": {"ledger_root": str(U10_ROOT / "nonce-ledger"), "resource_state": "active", "owner_uid": 0, "owner_gid": 0, "directory_mode": "0700", "record_format": "semantic-guard-u10-request-nonce-record/v1", "record_locator_scheme": "sha256(entry_id_nul_request_nonce).json", "write_policy": "one_record_per_nonce_o_excl_create_once/v1", "replay_policy": "reject_if_nonce_record_already_exists"},
            "result_spool": {"path": str(U10_ROOT / "spool"), "resource_state": "active", "owner_uid": 0, "owner_gid": 0, "mode": "0755", "write_policy": "root_broker_create_once_content_addressed_results/v1"},
            "entries": {},
            "u4_authority_resolution": {"requirement_id": "U-4", "status": "unresolved", "consequence": "does_not_establish_principal_identity_delegation_or_revocation_authority", "resolution_ref": None},
            "formal_authority": "none", "positive_assurance_allowed": False,
        }
    else:
        content = store_activation_content_v1(prior_store)
    content.update(
        {
            "store_revision_id": (
                store_revision_id
            ),
            "broker_runtime_version": BROKER_VERSION,
            "broker_entrypoint_ref": projection_authorization[
                "broker_entrypoint_ref"
            ],
            "broker_outer_launcher_ref": projection_authorization[
                "broker_outer_launcher_ref"
            ],
            "broker_launch_platform": projection_authorization[
                "broker_launch_platform"
            ],
            "broker_runtime_ref": manifest["broker_runtime_ref"],
            "signing_key": dict(signing_key),
        }
    )
    content["entries"] = _strict_json_clone(content.get("entries", {}))
    content["entries"][manifest["prepared_for_entry_id"]] = (
        _store_entry_from_active_snapshot(
            manifest=manifest,
            manifest_ref=manifest_ref,
        )
    )
    return content


def _prepare_store_activation_basis_candidate(
    *,
    manifest: Mapping[str, Any],
    manifest_raw: bytes,
    snapshot_activation_authorization_ref: Mapping[str, Any],
    projection_authorization: Mapping[str, Any],
    publisher_contract_binding: Mapping[str, Any],
    paths: SnapshotPaths,
    enforce_fixed_paths: bool,
    create_if_missing: bool = True,
) -> dict[str, Any]:
    publisher = _validate_publisher_contract_binding(
        publisher_contract_binding,
        operation="activate-snapshot",
    )
    manifest_path = (
        Path(str(manifest["root_storage"]["snapshot_path"])) / MANIFEST_NAME
    )
    manifest_ref = _root_ref(
        str(manifest["snapshot_id"]),
        manifest_path,
        manifest_raw,
        manifest["manifest_digest"],
    )
    if (
        manifest_ref.get("artifact_digest") != digest_bytes(manifest_raw)
        or manifest_ref.get("semantic_digest") != manifest.get("manifest_digest")
    ):
        raise U10SnapshotProductionError(
            "u10_store_activation_snapshot_manifest_binding_mismatch",
            str(manifest.get("snapshot_id")),
        )
    snapshot_authorization_id = str(
        snapshot_activation_authorization_ref.get("record_id", "")
    )
    reservation_path = (
        paths.store_activation_basis_root
        / f"{snapshot_authorization_id}.store-basis.json"
    )

    def load_reserved() -> dict[str, Any] | None:
        existing = _load_optional_record(
            reservation_path, root=paths.store_activation_basis_root
        )
        if existing is None:
            return None
        basis, basis_raw = existing
        _validate_schema(
            basis,
            "u10-store-activation-basis-v2.schema.json",
            "u10_store_activation_basis_invalid",
        )
        _verify_seal(
            basis,
            "basis_digest",
            code="u10_store_activation_basis_digest_mismatch",
        )
        transition_digest = store_activation_transition_digest_v2(
            snapshot_manifest_ref=basis["snapshot_manifest_ref"],
            entry_id=str(basis["entry_id"]),
            prior_store_ref=basis["prior_store_ref"],
            prior_revocation_ref=basis["prior_revocation_ref"],
            signing_key_ref=basis["signing_key_ref"],
            signing_key_selector_ref=basis["signing_key_selector_ref"],
        )
        content = basis["store_content"]
        if basis["publisher_contract_binding"] != publisher:
            raise U10SnapshotProductionError(
                "u10_store_activation_basis_publisher_contract_changed",
                snapshot_authorization_id,
            )
        if (
            basis["snapshot_activation_authorization_ref"]
            != snapshot_activation_authorization_ref
            or basis["snapshot_manifest_ref"] != manifest_ref
            or basis["store_transition_digest"] != transition_digest
            or basis["basis_id"]
            != f"store-basis.{transition_digest['value']}"
            or content.get("store_revision_id")
            != f"revision.u10.{transition_digest['value']}"
            or basis["store_activation_basis_digest"]
            != digest_bytes(canonical_json_bytes(content))
        ):
            raise U10SnapshotProductionError(
                "u10_store_activation_basis_reservation_mismatch",
                snapshot_authorization_id,
            )
        return _root_ref(
            str(basis["basis_id"]),
            reservation_path,
            basis_raw,
            basis["basis_digest"],
        )

    reserved = load_reserved()
    if reserved is not None:
        return reserved
    if not create_if_missing:
        raise U10SnapshotProductionError(
            "u10_store_activation_basis_missing_after_receipt",
            snapshot_authorization_id,
        )
    lock = (
        trust_store_coordination_lock(exclusive=False)
        if enforce_fixed_paths
        else nullcontext()
    )
    with lock:
        reserved = load_reserved()
        if reserved is not None:
            return reserved
        current = (
            _load_current_store_activation_context_v1()
            if enforce_fixed_paths
            else None
        )
        prior_store = current[0] if current is not None else None
        prior_store_raw = current[1] if current is not None else None
        prior_revocation = current[5] if current is not None else None
        prior_store_ref = (
            None
            if prior_store is None or prior_store_raw is None
            else _store_transition_ref_v1(prior_store, prior_store_raw)
        )
        prior_revocation_ref = (
            None
            if prior_revocation is None
            else _revocation_transition_ref_v1(*prior_revocation)
        )
        signing_key, signing_key_ref, signing_key_selector_ref = (
            _active_signing_key_context(paths=paths)
        )
        entry_id = str(manifest["prepared_for_entry_id"])
        transition_digest = store_activation_transition_digest_v2(
            snapshot_manifest_ref=manifest_ref,
            entry_id=entry_id,
            prior_store_ref=prior_store_ref,
            prior_revocation_ref=prior_revocation_ref,
            signing_key_ref=signing_key_ref,
            signing_key_selector_ref=signing_key_selector_ref,
        )
        store_revision_id = f"revision.u10.{transition_digest['value']}"
        basis_id = f"store-basis.{transition_digest['value']}"
        content = _initial_store_content(
            manifest=manifest,
            manifest_ref=manifest_ref,
            projection_authorization=projection_authorization,
            signing_key=signing_key,
            store_revision_id=store_revision_id,
            prior_store=prior_store,
        )
        store_basis_digest = digest_bytes(canonical_json_bytes(content))
        basis: dict[str, Any] = {
            "schema_version": "semantic-guard-u10-store-activation-basis/v2",
            "basis_id": basis_id,
            "basis_version": "2.0.0",
            "record_kind": "exact_store_activation_basis_candidate",
            "store_content": content,
            "store_activation_basis_digest": store_basis_digest,
            "store_transition_digest": transition_digest,
            "entry_id": entry_id,
            "snapshot_manifest_ref": manifest_ref,
            "snapshot_activation_authorization_ref": _strict_json_clone(
                snapshot_activation_authorization_ref
            ),
            "signing_key_ref": signing_key_ref,
            "signing_key_selector_ref": signing_key_selector_ref,
            "prior_store_ref": prior_store_ref,
            "prior_revocation_ref": prior_revocation_ref,
            "publisher_contract_binding": publisher,
            "prepared_at": _utc_now(),
            "publication_state": "not_published",
            "formal_authority": "none",
            "positive_assurance_allowed": False,
        }
        basis["basis_digest"] = sealed_digest(basis, "basis_digest")
        _validate_schema(
            basis,
            "u10-store-activation-basis-v2.schema.json",
            "u10_store_activation_basis_invalid",
        )
        raw = _publish_append_only_record(
            reservation_path,
            basis,
            ledger_root=paths.store_activation_basis_root,
            mode=0o444,
        )
        return _root_ref(
            basis_id,
            reservation_path,
            raw,
            basis["basis_digest"],
        )


def _publish_snapshot_manifest_last(
    *,
    manifest_path: Path,
    manifest: Mapping[str, Any],
    ledger: Path,
    pending_name: str,
    snapshot: Path,
) -> bytes:
    raw = json_record_bytes(manifest)
    pending = ledger / pending_name
    if manifest_path.exists() or manifest_path.is_symlink():
        observed_raw, observed_state = _read_regular(
            manifest_path,
            root=snapshot,
            allowed_modes={0o444},
            allowed_nlinks={1, 2},
        )
        if observed_raw != raw:
            raise U10SnapshotProductionError(
                "u10_snapshot_manifest_collision", str(manifest_path)
            )
        if observed_state.st_nlink == 2:
            pending_raw, pending_state = _read_regular(
                pending,
                root=ledger,
                allowed_modes={0o444},
                allowed_nlinks={2},
            )
            if (
                pending_raw != raw
                or pending_state.st_dev != observed_state.st_dev
                or pending_state.st_ino != observed_state.st_ino
            ):
                raise U10SnapshotProductionError(
                    "u10_snapshot_manifest_link_recovery_mismatch", str(manifest_path)
                )
            pending.unlink()
            _fsync_directory(ledger)
            observed_raw, _ = _read_regular(
                manifest_path, root=snapshot, allowed_modes={0o444}
            )
        elif pending.exists() or pending.is_symlink():
            raise U10SnapshotProductionError(
                "u10_snapshot_manifest_orphan_pending", str(pending)
            )
        return observed_raw
    if pending.exists() or pending.is_symlink():
        pending_raw, _ = _read_regular(
            pending, root=ledger, allowed_modes={0o444}
        )
        if pending_raw != raw:
            raise U10SnapshotProductionError(
                "u10_snapshot_manifest_pending_collision", str(pending)
            )
    else:
        _write_all_bytes(pending, raw, mode=0o444)
        _fsync_directory(ledger)
    try:
        os.link(pending, manifest_path, follow_symlinks=False)
    except FileExistsError:
        observed_raw, _ = _read_regular(
            manifest_path,
            root=snapshot,
            allowed_modes={0o444},
            allowed_nlinks={1, 2},
        )
        if observed_raw != raw:
            raise U10SnapshotProductionError(
                "u10_snapshot_manifest_collision", str(manifest_path)
            )
    except OSError as exc:
        raise U10SnapshotProductionError(
            "u10_snapshot_manifest_publication_failed", str(exc)
        ) from exc
    _fsync_directory(snapshot)
    try:
        pending.unlink()
    except FileNotFoundError:
        pass
    _fsync_directory(ledger)
    observed_raw, observed_state = _read_regular(
        manifest_path, root=snapshot, allowed_modes={0o444}
    )
    if observed_raw != raw or observed_state.st_nlink != 1:
        raise U10SnapshotProductionError(
            "u10_snapshot_manifest_post_publish_mismatch", str(manifest_path)
        )
    return observed_raw


def activate_snapshot_by_authorization_id(
    authorization_id: str,
    *,
    publisher_contract_binding: Mapping[str, Any],
    paths: SnapshotPaths = SnapshotPaths(),
    required_uid: int = 0,
    enforce_fixed_paths: bool = True,
) -> dict[str, Any]:
    if required_uid == 0 and os.geteuid() != 0:
        raise U10SnapshotProductionError("u10_snapshot_activation_requires_root", str(os.geteuid()))
    if enforce_fixed_paths:
        _validate_fixed_roots(paths, required_uid=required_uid)
    publisher = _validate_publisher_contract_binding(
        publisher_contract_binding, operation="activate-snapshot"
    )
    authorization_id = _id(authorization_id, code="u10_snapshot_adoption_authorization_id_invalid")
    authorization_path = paths.authorization_root / f"{authorization_id}.json"
    authorization, authorization_raw = _load_record(authorization_path, root=paths.authorization_root)
    _validate_schema(authorization, "u10-snapshot-adoption-authorization-v1.schema.json", "u10_snapshot_adoption_authorization_invalid")
    _verify_seal(authorization, "authorization_digest", code="u10_snapshot_adoption_authorization_digest_mismatch")
    if authorization["authorization_id"] != authorization_id:
        raise U10SnapshotProductionError("u10_snapshot_adoption_authorization_context_mismatch", authorization_id)
    projection_ref = authorization["projection_receipt_ref"]
    projection_path = Path(projection_ref["locator"])
    projection, projection_raw = _load_record(projection_path, root=paths.projection_ledger_root)
    _validate_schema(projection, "u10-snapshot-projection-receipt-v1.schema.json", "u10_projection_receipt_invalid")
    _verify_seal(projection, "receipt_digest", code="u10_projection_receipt_digest_mismatch")
    if projection_ref != _root_ref(projection["receipt_id"], projection_path, projection_raw, projection["receipt_digest"]):
        raise U10SnapshotProductionError("u10_projection_receipt_binding_mismatch", authorization_id)
    environment_adoption_ref = authorization["environment_adoption_ref"]
    environment_adoption, _environment_adoption_raw = (
        _load_snapshot_environment_adoption(
            environment_adoption_ref,
            paths=paths,
            projection=projection,
            projection_path=projection_path,
            projection_raw=projection_raw,
        )
    )
    snapshot = Path(projection["snapshot_ref"]["snapshot_path"])
    if enforce_fixed_paths and snapshot.parent != paths.snapshot_root:
        raise U10SnapshotProductionError("u10_snapshot_target_mismatch", str(snapshot))
    candidate_manifest, _ = _load_record(snapshot / "vnext/governance/u10-root-candidate-bundle.json", root=snapshot)
    candidate_projection, _ = _load_record(snapshot / "vnext/governance/u10-candidate-install-projection.json", root=snapshot)
    projection_authorization_id = projection["authorization_ref"]["authorization_id"]
    projection_authorization, _ = _load_projection_authorization(projection_authorization_id, paths=paths, enforce_fixed_paths=enforce_fixed_paths)
    manifest, context, artifacts = _build_manifest_basis(authorization=projection_authorization, candidate=candidate_manifest, projection=candidate_projection, snapshot=snapshot, verified_at=projection["immutability_verified_at"])
    if (
        manifest["snapshot_id"] != authorization["snapshot_id"]
        or manifest["snapshot_version"] != authorization["snapshot_version"]
        or manifest["prepared_for_entry_id"] != authorization["entry_id"]
        or manifest["snapshot_basis_digest"] != authorization["snapshot_basis_digest"]
        or manifest["snapshot_basis_digest"] != projection["snapshot_basis_digest"]
        or manifest["root_storage"]["tree_digest"] != projection["tree_digest"]
        or digest_bytes(canonical_json_bytes(artifacts)) != projection["artifact_denominator"]["denominator_digest"]
        or context["projected_environment_basis"]
        != projection["projected_environment_basis"]
    ):
        raise U10SnapshotProductionError("u10_snapshot_adoption_basis_mismatch", authorization_id)
    if not (
        _time(
            projection["immutability_verified_at"],
            code="u10_snapshot_activation_time_invalid",
        )
        <= _time(
            environment_adoption["recorded_at"],
            code="u10_snapshot_activation_time_invalid",
        )
        <= _time(
            authorization["recorded_at"],
            code="u10_snapshot_activation_time_invalid",
        )
    ):
        raise U10SnapshotProductionError("u10_snapshot_activation_time_order_invalid", authorization_id)
    ledger = paths.activation_ledger_root
    consumption_path = ledger / f"{authorization_id}.consumption.json"
    receipt_path = ledger / f"{authorization_id}.receipt.json"
    occurrence = f"snapshot-activation.{authorization['authorization_digest']['value']}"
    authorization_ref = _root_ref(
        authorization_id,
        authorization_path,
        authorization_raw,
        authorization["authorization_digest"],
    )
    with _lock(ledger, _ACTIVATION_LOCK_NAME):
        existing_receipt = _load_optional_record(receipt_path, root=ledger)
        if existing_receipt is not None:
            receipt = existing_receipt[0]
            _validate_schema(receipt, "u10-snapshot-activation-publication-receipt-v1.schema.json", "u10_snapshot_activation_receipt_invalid")
            _verify_seal(receipt, "receipt_digest", code="u10_snapshot_activation_receipt_digest_mismatch")
            manifest_path = snapshot / MANIFEST_NAME
            manifest_raw, _ = _read_regular(
                manifest_path, root=snapshot, allowed_modes={0o444}
            )
            store_basis_ref = _prepare_store_activation_basis_candidate(
                manifest=_json(
                    manifest_raw,
                    code="u10_snapshot_active_manifest_unreadable",
                ),
                manifest_raw=manifest_raw,
                snapshot_activation_authorization_ref=authorization_ref,
                projection_authorization=projection_authorization,
                publisher_contract_binding=publisher,
                paths=paths,
                enforce_fixed_paths=enforce_fixed_paths,
                create_if_missing=False,
            )
            if (
                receipt["authorization_ref"]["semantic_digest"]
                != authorization["authorization_digest"]
                or receipt["public_identifier"] != authorization_id
                or receipt["environment_adoption_ref"] != environment_adoption_ref
                or receipt["projection_receipt_ref"] != projection_ref
                or receipt["publisher_contract_binding"] != publisher
                or receipt["snapshot_manifest_ref"]["artifact_digest"]
                != digest_bytes(manifest_raw)
                or receipt["store_activation_basis_ref"] != store_basis_ref
                or receipt["completion_scope"]
                != "snapshot_manifest_and_exact_store_basis_candidate_published"
            ):
                raise U10SnapshotProductionError("u10_snapshot_activation_receipt_collision", authorization_id)
            return receipt
        existing_consumption = _load_optional_record(consumption_path, root=ledger)
        if existing_consumption is None:
            reserved_at = _utc_now()
            activation_prepared_at = _utc_now()
            consumption = {"schema_version": "semantic-guard-u10-snapshot-activation-authorization-consumption/v1", "consumption_id": f"consumption.{authorization_id}", "record_kind": "snapshot_adoption_authorization_consumption", "public_operation": "activate-snapshot", "public_identifier": authorization_id, "authorization_ref": authorization_ref, "projection_receipt_ref": projection_ref, "environment_adoption_ref": environment_adoption_ref, "snapshot_id": authorization["snapshot_id"], "snapshot_basis_digest": authorization["snapshot_basis_digest"], "occurrence_id": occurrence, "reserved_at": reserved_at, "activation_prepared_at": activation_prepared_at, "publisher_contract_binding": publisher, "manifest_publication_occurred": False, "formal_authority": "none", "positive_assurance_allowed": False}
            consumption["consumption_digest"] = sealed_digest(consumption, "consumption_digest")
            _validate_schema(consumption, "u10-snapshot-activation-authorization-consumption-v1.schema.json", "u10_snapshot_activation_consumption_invalid")
            _publish_append_only_record(
                consumption_path, consumption, ledger_root=ledger, mode=0o400
            )
        else:
            consumption = existing_consumption[0]
            _validate_schema(consumption, "u10-snapshot-activation-authorization-consumption-v1.schema.json", "u10_snapshot_activation_consumption_invalid")
            _verify_seal(consumption, "consumption_digest", code="u10_snapshot_activation_consumption_digest_mismatch")
            if (
                consumption["authorization_ref"] != authorization_ref
                or consumption["public_identifier"] != authorization_id
                or consumption["projection_receipt_ref"] != projection_ref
                or consumption["environment_adoption_ref"] != environment_adoption_ref
                or consumption["publisher_contract_binding"] != publisher
            ):
                raise U10SnapshotProductionError("u10_snapshot_activation_consumption_collision", authorization_id)
        activation_prepared_at = consumption["activation_prepared_at"]
        if not (
            _time(
                authorization["recorded_at"],
                code="u10_snapshot_activation_time_invalid",
            )
            <= _time(
                consumption["reserved_at"],
                code="u10_snapshot_activation_time_invalid",
            )
            <= _time(
                activation_prepared_at,
                code="u10_snapshot_activation_time_invalid",
            )
        ):
            raise U10SnapshotProductionError(
                "u10_snapshot_activation_time_order_invalid", authorization_id
            )
        activation_basis_id = (
            "activation-basis."
            f"{authorization['authorization_digest']['value']}"
        )
        activation_basis_path = (
            paths.activation_root / f"{activation_basis_id}.json"
        )
        activation_basis: dict[str, Any] = {"schema_version": "semantic-guard-u10-snapshot-activation-basis/v1", "activation_basis_id": activation_basis_id, "snapshot_id": authorization["snapshot_id"], "snapshot_version": authorization["snapshot_version"], "snapshot_basis_digest": authorization["snapshot_basis_digest"], "entry_id": authorization["entry_id"], "adoption_id": environment_adoption["adoption_id"], "adoption_version": environment_adoption["adoption_version"], "adoption_digest": environment_adoption["adoption_digest"], "environment_adoption_ref": environment_adoption_ref, "projection_receipt_ref": projection_ref, "snapshot_adoption_authorization_ref": authorization_ref, "immutability_verified_at": projection["immutability_verified_at"], "activation_prepared_at": activation_prepared_at, "preparation_status": "prepared_for_manifest_publication", "formal_authority": "none", "positive_assurance_allowed": False}
        activation_basis["activation_basis_digest"] = sealed_digest(
            activation_basis,
            "activation_basis_digest",
        )
        _validate_schema(
            activation_basis,
            "u10-snapshot-activation-basis-v1.schema.json",
            "u10_snapshot_activation_basis_invalid",
        )
        activation_basis_raw = _publish_append_only_record(
            activation_basis_path,
            activation_basis,
            ledger_root=paths.activation_root,
            mode=0o400,
        )
        activation_ref = _root_ref(
            activation_basis_id,
            activation_basis_path,
            activation_basis_raw,
            activation_basis["activation_basis_digest"],
        )
        manifest["lifecycle_state"] = "active"
        manifest["root_storage"]["storage_state"] = "immutable_active"
        manifest["immutability_verification"] = {"status": "verified", "verified_at": projection["immutability_verified_at"], "verifier_runtime_ref": manifest["broker_runtime_ref"], "checks": manifest["immutability_verification"]["checks"]}
        manifest["environment_adoption_ref"] = environment_adoption_ref
        manifest["snapshot_adoption_authorization_ref"] = authorization_ref
        manifest["activation_ref"] = activation_ref
        manifest["snapshot_basis_digest"] = snapshot_basis_digest_v1(manifest)
        manifest["manifest_digest"] = sealed_digest(manifest, "manifest_digest")
        _validate_schema(
            manifest,
            "u10-execution-snapshot-manifest-v1.schema.json",
            "u10_snapshot_active_manifest_invalid",
        )
        if manifest["snapshot_basis_digest"] != authorization["snapshot_basis_digest"]:
            raise U10SnapshotProductionError(
                "u10_snapshot_basis_changed_during_activation", authorization_id
            )
        manifest_path = snapshot / MANIFEST_NAME
        predicted_manifest_raw = json_record_bytes(manifest)
        store_basis_ref = _prepare_store_activation_basis_candidate(
            manifest=manifest,
            manifest_raw=predicted_manifest_raw,
            snapshot_activation_authorization_ref=authorization_ref,
            projection_authorization=projection_authorization,
            publisher_contract_binding=publisher,
            paths=paths,
            enforce_fixed_paths=enforce_fixed_paths,
        )
        store_basis_path = Path(str(store_basis_ref["locator"]))
        store_basis, _store_basis_raw = _load_record(
            store_basis_path, root=paths.store_activation_basis_root
        )
        manifest_raw = _publish_snapshot_manifest_last(
            manifest_path=manifest_path,
            manifest=manifest,
            ledger=ledger,
            pending_name=f".{authorization_id}.manifest.pending",
            snapshot=snapshot,
        )
        if manifest_raw != predicted_manifest_raw:
            raise U10SnapshotProductionError(
                "u10_snapshot_manifest_publication_bytes_changed",
                authorization_id,
            )
        publication_observed_at = _utc_now()
        receipt: dict[str, Any] = {"schema_version": "semantic-guard-u10-snapshot-activation-publication-receipt/v1", "receipt_id": f"receipt.{authorization_id}", "record_kind": "active_snapshot_manifest_publication_occurrence", "public_operation": "activate-snapshot", "public_identifier": authorization_id, "occurrence_id": occurrence, "authorization_ref": authorization_ref, "consumption_ref": {"consumption_id": consumption["consumption_id"], "consumption_digest": consumption["consumption_digest"]}, "projection_receipt_ref": projection_ref, "environment_adoption_ref": environment_adoption_ref, "activation_ref": activation_ref, "snapshot_manifest_ref": _root_ref(manifest["snapshot_id"], manifest_path, manifest_raw, manifest["manifest_digest"]), "store_activation_basis_ref": store_basis_ref, "completion_scope": "snapshot_manifest_and_exact_store_basis_candidate_published", "publication_not_before": consumption["reserved_at"], "publication_observed_at": publication_observed_at, "receipt_recorded_at": _utc_now(), "publisher_contract_binding": publisher, "publication_occurred": True, "formal_authority": "none", "positive_assurance_allowed": False}
        receipt["receipt_digest"] = sealed_digest(receipt, "receipt_digest")
        _validate_schema(receipt, "u10-snapshot-activation-publication-receipt-v1.schema.json", "u10_snapshot_activation_receipt_invalid")
        if not (_time(consumption["reserved_at"], code="u10_snapshot_activation_time_invalid") <= _time(activation_prepared_at, code="u10_snapshot_activation_time_invalid") <= _time(store_basis["prepared_at"], code="u10_snapshot_activation_time_invalid") <= _time(publication_observed_at, code="u10_snapshot_activation_time_invalid") <= _time(receipt["receipt_recorded_at"], code="u10_snapshot_activation_time_invalid")):
            raise U10SnapshotProductionError("u10_snapshot_activation_time_order_invalid", authorization_id)
        _publish_append_only_record(
            receipt_path, receipt, ledger_root=ledger, mode=0o400
        )
        return receipt


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    project = sub.add_parser("project")
    project.add_argument("--authorization-id", required=True)
    activate = sub.add_parser("activate")
    activate.add_argument("--authorization-id", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        raise U10SnapshotProductionError(
            "u10_snapshot_producer_direct_invocation_prohibited",
            (
                f"{args.command}:{args.authorization_id}; use the fixed U-10 "
                "control entry so the root-sealed publisher contract is supplied"
            ),
        )
    except U10SnapshotProductionError as exc:
        print(
            json.dumps(
                {
                    "status": "error",
                    "error": {"code": exc.code, "detail": exc.detail},
                    "formal_authority": "none",
                },
                ensure_ascii=False,
                sort_keys=True,
                allow_nan=False,
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
