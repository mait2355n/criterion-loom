"""Root-owned I/O primitives used by the U-10 broker supervisor."""

from __future__ import annotations

from collections.abc import Mapping
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import stat
from typing import Any

from .darwin_acl import assert_no_extended_acl


U10_ROOT = Path("/Library/Application Support/semantic-guard/u10")
TRUST_STORE_PATH = U10_ROOT / "trust-store-current.json"
TRUST_STORE_HISTORY_ROOT = U10_ROOT / "trust-store-history" / "sha256"
TRUST_STORE_LOCK_PATH = U10_ROOT / "trust-store.lock"
NONCE_LEDGER_ROOT = U10_ROOT / "nonce-ledger"
EVIDENCE_SPOOL_ROOT = U10_ROOT / "spool"
SNAPSHOT_ROOT = U10_ROOT / "snapshots"
TRUST_STORE_CANDIDATE_ROOT = U10_ROOT / "trust-store-candidates"
STORE_ACTIVATION_BASIS_ROOT = U10_ROOT / "store-activation-bases"
KEY_ROOT = U10_ROOT / "keys"
ACTIVATION_ROOT = U10_ROOT / "activations"
SNAPSHOT_PROJECTION_LEDGER_ROOT = ACTIVATION_ROOT / "snapshot-projections"
SNAPSHOT_ACTIVATION_LEDGER_ROOT = ACTIVATION_ROOT / "snapshot-activations"
SNAPSHOT_ACTIVATION_ROOT = ACTIVATION_ROOT / "snapshots"
STORE_ACTIVATION_LEDGER_ROOT = ACTIVATION_ROOT / "store-transitions"
AUTHORIZATION_ROOT = U10_ROOT / "authorizations"
REVOCATION_ROOT = U10_ROOT / "revocations" / "sha256"
REVOCATION_LEDGER_ROOT = ACTIVATION_ROOT / "store-revocations"
REVOCATION_SELECTOR_PATH = U10_ROOT / "trust-store-current-revocation.json"
BROKER_ENTRYPOINT_PATH = U10_ROOT / "bootstrap" / "u10_root_broker_entrypoint.sh"
BROKER_OUTER_LAUNCHER_PATH = (
    U10_ROOT / "bootstrap" / "u10_root_broker_outer_launcher.py"
)
BROKER_EFFECTIVE_PYTHON_PATH = U10_ROOT / "bootstrap" / "effective-python.path"
BROKER_EFFECTIVE_RUNTIME_MANIFEST_PATH = (
    U10_ROOT / "bootstrap" / "effective-python-runtime-manifest.json"
)
ROOT_CONTROL_ENTRYPOINT_PATH = (
    U10_ROOT / "bootstrap" / "u10_root_control_entrypoint.sh"
)
ROOT_CONTROL_OUTER_LAUNCHER_PATH = (
    U10_ROOT / "bootstrap" / "u10_root_control_outer_launcher.py"
)
ROOT_CONTROL_DISPATCHER_PATH = (
    U10_ROOT / "bootstrap" / "u10_root_control_dispatcher.py"
)
SNAPSHOT_STORE_PRODUCER_PATH = (
    U10_ROOT / "bootstrap" / "u10_snapshot_store_production.py"
)
CONTROL_EFFECTIVE_PYTHON_PATH = (
    U10_ROOT / "bootstrap" / "control-effective-python.path"
)
CONTROL_RUNTIME_MANIFEST_PATH = (
    U10_ROOT / "bootstrap" / "control-python-runtime-manifest.json"
)
INITIAL_TRUST_PROVISIONER_PATH = (
    U10_ROOT / "bootstrap" / "u10_initial_trust_provisioner.py"
)
INITIAL_BOOTSTRAP_PROVENANCE_BINDING_PATH = (
    U10_ROOT / "bootstrap" / "initial-bootstrap-provenance-binding.json"
)


class BrokerBoundaryError(RuntimeError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


def _strict_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise json.JSONDecodeError(f"duplicate object key: {key!r}", key, 0)
        value[key] = item
    return value


def _reject_nonfinite_json_constant(value: str) -> Any:
    raise json.JSONDecodeError(f"non-finite JSON number: {value}", value, 0)


def _strict_json_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise json.JSONDecodeError(f"non-finite JSON number: {value}", value, 0)
    return parsed


def strict_json_loads(raw: str | bytes | bytearray) -> Any:
    """Decode JSON while rejecting ambiguous keys and non-finite numbers."""

    return json.loads(
        raw,
        object_pairs_hook=_strict_json_object,
        parse_constant=_reject_nonfinite_json_constant,
        parse_float=_strict_json_float,
    )


@contextmanager
def trust_store_coordination_lock(*, exclusive: bool):
    """Hold the fixed root-owned store lock across execution or activation.

    Execution/signing uses a shared lock.  Activation and current-store
    replacement must use the exclusive form, preventing a mixed-generation
    occurrence from being signed.
    """

    if os.geteuid() != 0:
        raise BrokerBoundaryError("u10_root_broker_requires_root", str(os.geteuid()))
    validate_directory_chain(U10_ROOT, U10_ROOT)
    try:
        before = TRUST_STORE_LOCK_PATH.lstat()
    except OSError as exc:
        raise BrokerBoundaryError(
            "u10_trust_store_lock_unavailable", str(TRUST_STORE_LOCK_PATH)
        ) from exc
    try:
        assert_no_extended_acl(TRUST_STORE_LOCK_PATH)
    except PermissionError as exc:
        raise BrokerBoundaryError(
            "u10_trust_store_lock_extended_acl", str(TRUST_STORE_LOCK_PATH)
        ) from exc
    except OSError as exc:
        raise BrokerBoundaryError(
            "u10_trust_store_lock_acl_unavailable", str(TRUST_STORE_LOCK_PATH)
        ) from exc
    if (
        stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_uid != 0
        or before.st_gid != 0
        or stat.S_IMODE(before.st_mode) != 0o600
        or before.st_nlink != 1
    ):
        raise BrokerBoundaryError(
            "u10_trust_store_lock_untrusted", str(TRUST_STORE_LOCK_PATH)
        )
    flags = os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(TRUST_STORE_LOCK_PATH, flags)
    except OSError as exc:
        raise BrokerBoundaryError(
            "u10_trust_store_lock_open_failed", str(TRUST_STORE_LOCK_PATH)
        ) from exc
    try:
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
            raise BrokerBoundaryError(
                "u10_trust_store_lock_changed", str(TRUST_STORE_LOCK_PATH)
            )
        fcntl.flock(descriptor, fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
        yield
    finally:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)


def canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def digest_bytes(value: bytes) -> dict[str, str]:
    return {"algorithm": "sha256", "value": hashlib.sha256(value).hexdigest()}


def digest_file(path: Path) -> dict[str, str]:
    return digest_bytes(
        read_protected_file(path, protected_root=U10_ROOT, private=False)
    )


def _relative_parts(root: Path, path: Path) -> tuple[Path, tuple[str, ...]]:
    if not root.is_absolute() or not path.is_absolute():
        raise BrokerBoundaryError("protected_path_not_absolute", str(path))
    normalized_root = Path(os.path.normpath(str(root)))
    normalized_path = Path(os.path.normpath(str(path)))
    if normalized_root != root or normalized_path != path:
        raise BrokerBoundaryError("protected_path_not_canonical", str(path))
    try:
        return root, normalized_path.relative_to(root).parts
    except ValueError as exc:
        raise BrokerBoundaryError("protected_path_outside_root", str(path)) from exc


def _assert_stat(
    observed: os.stat_result,
    *,
    path: Path,
    uid: int,
    directory: bool,
    private: bool = False,
) -> None:
    try:
        assert_no_extended_acl(path)
    except PermissionError as exc:
        raise BrokerBoundaryError("protected_path_extended_acl", str(path)) from exc
    except OSError as exc:
        raise BrokerBoundaryError(
            "protected_path_acl_unavailable", str(path)
        ) from exc
    if directory and not stat.S_ISDIR(observed.st_mode):
        raise BrokerBoundaryError("protected_path_not_directory", str(path))
    if not directory and not stat.S_ISREG(observed.st_mode):
        raise BrokerBoundaryError("protected_path_not_regular", str(path))
    if observed.st_uid != uid:
        raise BrokerBoundaryError("protected_path_owner_mismatch", str(path))
    if observed.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
        raise BrokerBoundaryError("protected_path_mutable", str(path))
    if private and observed.st_mode & (stat.S_IRGRP | stat.S_IROTH):
        raise BrokerBoundaryError("protected_private_file_exposed", str(path))


def validate_directory_chain(
    root: Path, path: Path, *, required_uid: int = 0
) -> None:
    root, parts = _relative_parts(root, path)
    try:
        root.relative_to(U10_ROOT)
    except ValueError:
        fixed_u10_root = False
    else:
        fixed_u10_root = True
    if fixed_u10_root:
        current = Path(root.anchor)
        chain = (None, *root.parts[1:], *parts)
    else:
        current = root
        chain = (None, *parts)
    for part in chain:
        if part is not None:
            current /= part
        try:
            observed = current.lstat()
        except OSError as exc:
            raise BrokerBoundaryError(
                "protected_directory_unavailable", str(current)
            ) from exc
        if stat.S_ISLNK(observed.st_mode):
            raise BrokerBoundaryError("protected_symlink_prohibited", str(current))
        _assert_stat(
            observed,
            path=current,
            uid=required_uid,
            directory=True,
        )


def read_protected_file(
    path: Path,
    *,
    protected_root: Path = U10_ROOT,
    required_uid: int = 0,
    private: bool = False,
    maximum_bytes: int = 32 * 1024 * 1024,
) -> bytes:
    root, parts = _relative_parts(protected_root, path)
    if not parts:
        raise BrokerBoundaryError("protected_file_is_root", str(path))
    validate_directory_chain(root, path.parent, required_uid=required_uid)
    try:
        before = path.lstat()
    except OSError as exc:
        raise BrokerBoundaryError("protected_file_unavailable", str(path)) from exc
    if stat.S_ISLNK(before.st_mode):
        raise BrokerBoundaryError("protected_symlink_prohibited", str(path))
    _assert_stat(
        before,
        path=path,
        uid=required_uid,
        directory=False,
        private=private,
    )
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise BrokerBoundaryError("protected_file_open_failed", str(path)) from exc
    try:
        opened = os.fstat(descriptor)
        identity = (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
        )
        if (
            opened.st_dev,
            opened.st_ino,
            opened.st_size,
            opened.st_mtime_ns,
            opened.st_ctime_ns,
        ) != identity:
            raise BrokerBoundaryError("protected_file_changed_before_read", str(path))
        chunks: list[bytes] = []
        size = 0
        while True:
            block = os.read(descriptor, min(1024 * 1024, maximum_bytes + 1 - size))
            if not block:
                break
            size += len(block)
            if size > maximum_bytes:
                raise BrokerBoundaryError("protected_file_too_large", str(path))
            chunks.append(block)
        after = os.fstat(descriptor)
        if (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        ) != identity:
            raise BrokerBoundaryError("protected_file_changed_during_read", str(path))
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def reserve_nonce_once(
    request: Mapping[str, Any],
    *,
    ledger_root: Path = NONCE_LEDGER_ROOT,
    required_uid: int = 0,
) -> tuple[Path, dict[str, Any]]:
    entry_id = str(request.get("entry_id", ""))
    nonce = str(request.get("request_nonce", ""))
    if len(nonce) != 64 or any(item not in "0123456789abcdef" for item in nonce):
        raise BrokerBoundaryError("request_nonce_invalid", nonce)
    validate_directory_chain(ledger_root, ledger_root, required_uid=required_uid)
    name = hashlib.sha256(f"{entry_id}\0{nonce}".encode()).hexdigest() + ".json"
    path = ledger_root / name
    record = {
        "schema_version": "semantic-guard-u10-request-nonce-record/v1",
        "entry_id": entry_id,
        "command_id": str(request.get("command_id", "")),
        "request_nonce": nonce,
        "recorded_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "state": "consumed_before_launch",
    }
    encoded = canonical_json_bytes(record) + b"\n"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags, 0o600)
    except FileExistsError as exc:
        raise BrokerBoundaryError("request_nonce_replay", nonce) from exc
    except OSError as exc:
        raise BrokerBoundaryError("request_nonce_reservation_failed", nonce) from exc
    try:
        offset = 0
        while offset < len(encoded):
            offset += os.write(descriptor, encoded[offset:])
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    directory_fd = os.open(
        ledger_root,
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
    )
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
    return path, record


def validate_protected_tree(root: Path, *, required_uid: int = 0) -> None:
    validate_directory_chain(root, root, required_uid=required_uid)
    for raw_directory, directories, files in os.walk(
        root, topdown=True, followlinks=False
    ):
        base = Path(raw_directory)
        for name in (*directories, *files):
            path = base / name
            observed = path.lstat()
            if stat.S_ISLNK(observed.st_mode):
                raise BrokerBoundaryError("protected_tree_symlink", str(path))
            directory = stat.S_ISDIR(observed.st_mode)
            if not directory and not stat.S_ISREG(observed.st_mode):
                raise BrokerBoundaryError("protected_tree_special_file", str(path))
            _assert_stat(
                observed,
                path=path,
                uid=required_uid,
                directory=directory,
            )
            if stat.S_ISREG(observed.st_mode) and observed.st_nlink != 1:
                raise BrokerBoundaryError("protected_tree_hardlink", str(path))
