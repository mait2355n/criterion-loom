#!/usr/bin/env python3
"""Provision the U-10 initial root and Ed25519 keys without trusting repo paths.

The initial operation is entered only through the OS-protected, digest-pinned
capsule loader emitted by ``prepare_u10_initial_bootstrap_capsule.py``.  Normal
key operations are entered through the fixed root wrapper and accept one
authorization identifier; neither route accepts a caller-selected filesystem
path or inline authorization payload.

This module intentionally imports only the standard library at module load.
The key route imports ``cryptography`` only after the qualified control-runtime
outer launcher has established the closed runtime boundary.
"""

from __future__ import annotations

import base64
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import ctypes
import errno
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
from typing import Any, Callable, Iterator, Mapping


U10_ROOT = Path("/Library/Application Support/semantic-guard/u10")
PREBOOT_LEDGER_ROOT = Path(
    "/Library/Application Support/semantic-guard/u10-bootstrap-ledger"
)
KEY_AUTHORIZATION_ROOT = U10_ROOT / "authorizations" / "key"
KEY_LEDGER_ROOT = U10_ROOT / "activations" / "key-transitions"
KEY_ROOT = U10_ROOT / "keys"
KEY_GENERATION_ROOT = KEY_ROOT / "generations"
KEY_REVOCATION_ROOT = KEY_ROOT / "revocations"
KEY_SELECTOR_HISTORY_ROOT = KEY_ROOT / "selector-history" / "sha256"
KEY_CURRENT_SELECTOR = KEY_ROOT / "current.json"
TRUST_STORE_LOCK_PATH = U10_ROOT / "trust-store.lock"
KEY_LOCK_PATH = KEY_ROOT / "key-transition.lock"

BROKER_EFFECTIVE_PATH = U10_ROOT / "bootstrap" / "effective-python.path"
BROKER_RUNTIME_MANIFEST = (
    U10_ROOT / "bootstrap" / "effective-python-runtime-manifest.json"
)
CONTROL_EFFECTIVE_PATH = U10_ROOT / "bootstrap" / "control-effective-python.path"
CONTROL_RUNTIME_MANIFEST = (
    U10_ROOT / "bootstrap" / "control-python-runtime-manifest.json"
)
INITIAL_BOOTSTRAP_PROVENANCE_BINDING = (
    U10_ROOT / "bootstrap" / "initial-bootstrap-provenance-binding.json"
)

CONTROL_PUBLISHER_BINDING_SCHEMA = (
    "semantic-guard-u10-control-publisher-contract-binding/v1"
)
CONTROL_PUBLISHER_CONTRACT_ID = "semantic-guard.u10.fixed-root-control-publisher.v1"
CONTROL_PUBLISHER_ARTIFACTS = {
    "broker_outer_launcher": (
        U10_ROOT / "bootstrap" / "u10_root_broker_outer_launcher.py"
    ),
    "initial_trust_provisioner": (
        U10_ROOT / "bootstrap" / "u10_initial_trust_provisioner.py"
    ),
    "root_control_dispatcher": (
        U10_ROOT / "bootstrap" / "u10_root_control_dispatcher.py"
    ),
    "root_control_entrypoint": (
        U10_ROOT / "bootstrap" / "u10_root_control_entrypoint.sh"
    ),
    "root_control_outer_launcher": (
        U10_ROOT / "bootstrap" / "u10_root_control_outer_launcher.py"
    ),
    "snapshot_store_producer": (
        U10_ROOT / "bootstrap" / "u10_snapshot_store_production.py"
    ),
}

BOOTSTRAP_PLAN_SCHEMA = "semantic-guard-u10-bootstrap-provisioning-plan/v1"
BOOTSTRAP_AUTH_SCHEMA = "semantic-guard-u10-bootstrap-provisioning-authorization/v1"
BOOTSTRAP_CONSUMPTION_SCHEMA = (
    "semantic-guard-u10-bootstrap-provisioning-consumption/v1"
)
BOOTSTRAP_RECEIPT_SCHEMA = "semantic-guard-u10-bootstrap-provisioning-receipt/v1"
BOOTSTRAP_PROVENANCE_BINDING_SCHEMA = (
    "semantic-guard-u10-bootstrap-provenance-binding/v1"
)
CAPSULE_SCHEMA = "semantic-guard-u10-initial-bootstrap-capsule/v1"
RUNTIME_OBSERVATION_REQUEST_SCHEMA = (
    "semantic-guard-u10-bootstrap-runtime-observation-request/v1"
)
RUNTIME_OBSERVATION_RECEIPT_SCHEMA = (
    "semantic-guard-u10-bootstrap-runtime-observation-receipt/v1"
)
KEY_AUTH_SCHEMA_V1 = "semantic-guard-u10-key-operation-authorization/v1"
KEY_CONSUMPTION_SCHEMA_V1 = (
    "semantic-guard-u10-key-operation-authorization-consumption/v1"
)
KEY_METADATA_SCHEMA_V1 = "semantic-guard-u10-signing-key-metadata/v1"
KEY_REVOCATION_SCHEMA_V1 = "semantic-guard-u10-signing-key-revocation/v1"
KEY_SELECTOR_SCHEMA_V1 = "semantic-guard-u10-signing-key-selector/v1"
KEY_RECEIPT_SCHEMA_V1 = "semantic-guard-u10-key-operation-receipt/v1"

# v1 records remain readable through the legacy validators below.  All new key
# transitions are produced with the v2 contracts; callers cannot select v1.
KEY_AUTH_SCHEMA = "semantic-guard-u10-key-operation-authorization/v2"
KEY_CONSUMPTION_SCHEMA = "semantic-guard-u10-key-operation-authorization-consumption/v2"
KEY_METADATA_SCHEMA = "semantic-guard-u10-signing-key-metadata/v2"
KEY_REVOCATION_SCHEMA = "semantic-guard-u10-signing-key-revocation/v2"
KEY_SELECTOR_SCHEMA = "semantic-guard-u10-signing-key-selector/v2"
KEY_RECEIPT_SCHEMA = "semantic-guard-u10-key-operation-receipt/v2"
KEY_EMERGENCY_CLOSURE_SCHEMA = "semantic-guard-u10-key-transition-emergency-closure/v1"

_KEY_LEDGER_LAYOUT_V2 = {
    ".authorization.json": (
        "authorization",
        0o400,
        KEY_AUTH_SCHEMA,
        KEY_AUTH_SCHEMA_V1,
    ),
    ".consumption.json": (
        "consumption",
        0o400,
        KEY_CONSUMPTION_SCHEMA,
        KEY_CONSUMPTION_SCHEMA_V1,
    ),
    ".receipt.json": (
        "receipt",
        0o444,
        KEY_RECEIPT_SCHEMA,
        KEY_RECEIPT_SCHEMA_V1,
    ),
    ".emergency-closure.json": (
        "emergency_closure",
        0o444,
        KEY_EMERGENCY_CLOSURE_SCHEMA,
        None,
    ),
}

_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,199}$")
_MEMBER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,1023}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_UUID = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-"
    r"[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)
_ENTITY_REF = re.compile(
    r"^.{1,200}・[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-"
    r"[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)


class U10ProvisioningError(RuntimeError):
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
    """Decode one strict JSON value before any contract validation or write."""

    return json.loads(
        raw,
        object_pairs_hook=_strict_json_object,
        parse_constant=_reject_nonfinite_json_constant,
        parse_float=_strict_json_float,
    )


@dataclass(frozen=True)
class BootstrapPaths:
    target_root: Path = U10_ROOT
    ledger_root: Path = PREBOOT_LEDGER_ROOT


@dataclass(frozen=True)
class KeyPaths:
    u10_root: Path = U10_ROOT
    authorization_root: Path = KEY_AUTHORIZATION_ROOT
    ledger_root: Path = KEY_LEDGER_ROOT
    key_root: Path = KEY_ROOT
    generation_root: Path = KEY_GENERATION_ROOT
    revocation_root: Path = KEY_REVOCATION_ROOT
    selector_history_root: Path = KEY_SELECTOR_HISTORY_ROOT
    selector_path: Path = KEY_CURRENT_SELECTOR
    trust_store_lock_path: Path = TRUST_STORE_LOCK_PATH
    lock_path: Path = KEY_LOCK_PATH


def _assert_fixed_key_paths_v2(paths: KeyPaths) -> None:
    if paths != KeyPaths():
        raise U10ProvisioningError("u10_key_paths_not_fixed", repr(paths))


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def json_record_bytes(value: Mapping[str, Any]) -> bytes:
    return canonical_json_bytes(value) + b"\n"


def digest_bytes(raw: bytes) -> dict[str, str]:
    return {"algorithm": "sha256", "value": hashlib.sha256(raw).hexdigest()}


def sealed_digest(value: Mapping[str, Any], field: str) -> dict[str, str]:
    material = dict(value)
    material.pop(field, None)
    return digest_bytes(canonical_json_bytes(material))


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_time(value: Any, *, code: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise U10ProvisioningError(code, str(value))
    try:
        result = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise U10ProvisioningError(code, value) from exc
    if result.tzinfo is None:
        raise U10ProvisioningError(code, value)
    return result


def _require_exact_keys(value: Any, expected: set[str], *, code: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        actual = sorted(value) if isinstance(value, dict) else type(value).__name__
        raise U10ProvisioningError(
            code, f"expected={sorted(expected)!r}; actual={actual!r}"
        )
    return value


def _require_id(value: Any, *, code: str) -> str:
    if not isinstance(value, str) or _ID.fullmatch(value) is None:
        raise U10ProvisioningError(code, str(value))
    return value


def _require_member(value: Any, *, code: str) -> str:
    if (
        not isinstance(value, str)
        or _MEMBER.fullmatch(value) is None
        or value.startswith("/")
        or ".." in Path(value).parts
        or Path(value).as_posix() != value
    ):
        raise U10ProvisioningError(code, str(value))
    return value


def _require_digest(value: Any, *, code: str) -> dict[str, str]:
    item = _require_exact_keys(value, {"algorithm", "value"}, code=code)
    if item["algorithm"] != "sha256" or not isinstance(item["value"], str):
        raise U10ProvisioningError(code, str(value))
    if _HEX64.fullmatch(item["value"]) is None:
        raise U10ProvisioningError(code, str(value))
    return item


def _require_canonical_absolute(value: Any, *, code: str) -> Path:
    path = Path(str(value))
    if not path.is_absolute() or path != Path(os.path.normpath(str(path))):
        raise U10ProvisioningError(code, str(value))
    return path


def _require_entity_ref(value: Any, *, code: str) -> str:
    if not isinstance(value, str) or _ENTITY_REF.fullmatch(value) is None:
        raise U10ProvisioningError(code, str(value))
    return value


def _assert_no_acl(path: Path) -> None:
    if sys.platform != "darwin":
        return
    libc = ctypes.CDLL(None, use_errno=True)
    acl_get_link = libc.acl_get_link_np
    acl_get_link.argtypes = [ctypes.c_char_p, ctypes.c_int]
    acl_get_link.restype = ctypes.c_void_p
    acl_free = libc.acl_free
    acl_free.argtypes = [ctypes.c_void_p]
    acl_free.restype = ctypes.c_int
    ctypes.set_errno(0)
    acl = acl_get_link(os.fsencode(path), 0x00000100)
    if acl:
        acl_free(acl)
        raise U10ProvisioningError("u10_extended_acl_prohibited", str(path))
    observed_errno = ctypes.get_errno()
    if observed_errno != errno.ENOENT:
        raise U10ProvisioningError(
            "u10_acl_observation_failed", f"{path}: errno={observed_errno}"
        )


def _assert_directory(
    path: Path,
    *,
    uid: int,
    exact_mode: int | None = None,
    allow_mutable: bool = False,
) -> os.stat_result:
    try:
        observed = path.lstat()
    except OSError as exc:
        raise U10ProvisioningError("u10_directory_unavailable", str(path)) from exc
    _assert_no_acl(path)
    if stat.S_ISLNK(observed.st_mode) or not stat.S_ISDIR(observed.st_mode):
        raise U10ProvisioningError("u10_directory_untrusted", str(path))
    if observed.st_uid != uid:
        raise U10ProvisioningError("u10_owner_mismatch", str(path))
    if not allow_mutable and observed.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
        raise U10ProvisioningError("u10_mutable_ancestor", str(path))
    if exact_mode is not None and stat.S_IMODE(observed.st_mode) != exact_mode:
        raise U10ProvisioningError("u10_mode_mismatch", str(path))
    return observed


def validate_directory_chain(
    root: Path, path: Path, *, uid: int, strict_from_filesystem_root: bool = False
) -> None:
    root = _require_canonical_absolute(root, code="u10_root_not_canonical")
    path = _require_canonical_absolute(path, code="u10_path_not_canonical")
    try:
        relative = path.relative_to(root)
    except ValueError as exc:
        raise U10ProvisioningError("u10_path_outside_root", str(path)) from exc
    if strict_from_filesystem_root:
        current = Path(root.anchor)
        parts = (*root.parts[1:], *relative.parts)
    else:
        current = root
        parts = relative.parts
    _assert_directory(current, uid=0 if strict_from_filesystem_root else uid)
    for part in parts:
        current /= part
        _assert_directory(current, uid=uid)


def read_protected_file(
    path: Path,
    *,
    root: Path,
    uid: int,
    exact_mode: int | None = None,
    maximum_bytes: int = 64 * 1024 * 1024,
) -> bytes:
    path = _require_canonical_absolute(path, code="u10_file_not_canonical")
    validate_directory_chain(root, path.parent, uid=uid)
    try:
        before = path.lstat()
    except OSError as exc:
        raise U10ProvisioningError("u10_file_unavailable", str(path)) from exc
    _assert_no_acl(path)
    if (
        stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_uid != uid
        or before.st_nlink != 1
        or before.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
        or (exact_mode is not None and stat.S_IMODE(before.st_mode) != exact_mode)
    ):
        raise U10ProvisioningError("u10_file_untrusted", str(path))
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise U10ProvisioningError("u10_file_open_failed", str(path)) from exc
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
            raise U10ProvisioningError("u10_file_changed_before_read", str(path))
        chunks: list[bytes] = []
        size = 0
        while True:
            block = os.read(descriptor, min(1024 * 1024, maximum_bytes + 1 - size))
            if not block:
                break
            chunks.append(block)
            size += len(block)
            if size > maximum_bytes:
                raise U10ProvisioningError("u10_file_too_large", str(path))
        after = os.fstat(descriptor)
        if (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        ) != identity:
            raise U10ProvisioningError("u10_file_changed_during_read", str(path))
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _write_all(descriptor: int, raw: bytes) -> None:
    offset = 0
    while offset < len(raw):
        written = os.write(descriptor, raw[offset:])
        if written <= 0:
            raise U10ProvisioningError("u10_short_write", str(descriptor))
        offset += written


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _atomic_append_only(path: Path, record: Mapping[str, Any], *, mode: int) -> bytes:
    raw = json_record_bytes(record)
    if path.exists() or path.is_symlink():
        existing = read_protected_file(
            path, root=path.parent, uid=os.geteuid(), exact_mode=mode
        )
        if existing != raw:
            raise U10ProvisioningError("u10_append_only_collision", str(path))
        return raw
    token = hashlib.sha256(raw).hexdigest()[:24]
    temporary = path.parent / f".{path.name}.tmp.{token}"
    if temporary.exists() or temporary.is_symlink():
        try:
            observed = temporary.lstat()
            if (
                stat.S_ISREG(observed.st_mode)
                and observed.st_uid == os.geteuid()
                and observed.st_nlink in {1, 2}
            ):
                temporary.unlink()
            else:
                raise U10ProvisioningError(
                    "u10_append_only_temp_untrusted", str(temporary)
                )
        except FileNotFoundError:
            pass
    descriptor = os.open(
        temporary,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
        mode,
    )
    try:
        _write_all(descriptor, raw)
        os.fchmod(descriptor, mode)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    try:
        os.link(temporary, path, follow_symlinks=False)
    except FileExistsError:
        existing = read_protected_file(
            path, root=path.parent, uid=os.geteuid(), exact_mode=mode
        )
        if existing != raw:
            raise U10ProvisioningError("u10_append_only_collision", str(path))
    finally:
        if temporary.exists() or temporary.is_symlink():
            temporary.unlink()
    _fsync_directory(path.parent)
    return raw


def _atomic_replace(path: Path, raw: bytes, *, mode: int) -> None:
    token = hashlib.sha256(raw).hexdigest()[:24]
    temporary = path.parent / f".{path.name}.replace.{token}"
    if temporary.exists() or temporary.is_symlink():
        temporary.unlink()
    descriptor = os.open(
        temporary,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
        mode,
    )
    try:
        _write_all(descriptor, raw)
        os.fchmod(descriptor, mode)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    os.replace(temporary, path)
    _fsync_directory(path.parent)


def _rename_directory_no_replace(source: Path, target: Path) -> None:
    if sys.platform == "darwin":
        libc = ctypes.CDLL(None, use_errno=True)
        renameatx = libc.renameatx_np
        renameatx.argtypes = [
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        ]
        renameatx.restype = ctypes.c_int
        at_fdcwd = -2
        rename_excl = 0x00000004
        if (
            renameatx(
                at_fdcwd,
                os.fsencode(source),
                at_fdcwd,
                os.fsencode(target),
                rename_excl,
            )
            != 0
        ):
            observed_errno = ctypes.get_errno()
            if observed_errno in {errno.EEXIST, errno.ENOTEMPTY}:
                raise U10ProvisioningError("u10_publish_collision", str(target))
            raise U10ProvisioningError(
                "u10_atomic_publish_failed", f"{target}: errno={observed_errno}"
            )
        return
    if target.exists() or target.is_symlink():
        raise U10ProvisioningError("u10_publish_collision", str(target))
    os.rename(source, target)


def _safe_remove_tree(path: Path, *, uid: int) -> None:
    if not path.exists() and not path.is_symlink():
        return
    root_stat = path.lstat()
    if stat.S_ISLNK(root_stat.st_mode) or not stat.S_ISDIR(root_stat.st_mode):
        raise U10ProvisioningError("u10_stale_stage_untrusted", str(path))
    for raw_root, directories, files in os.walk(path, topdown=False, followlinks=False):
        base = Path(raw_root)
        for name in files:
            item = base / name
            observed = item.lstat()
            if (
                stat.S_ISLNK(observed.st_mode)
                or not stat.S_ISREG(observed.st_mode)
                or observed.st_uid != uid
                or observed.st_nlink != 1
            ):
                raise U10ProvisioningError("u10_stale_stage_untrusted", str(item))
            item.unlink()
        for name in directories:
            item = base / name
            observed = item.lstat()
            if stat.S_ISLNK(observed.st_mode) or observed.st_uid != uid:
                raise U10ProvisioningError("u10_stale_stage_untrusted", str(item))
            item.rmdir()
    path.rmdir()


@contextmanager
def _exclusive_lock(path: Path, *, uid: int) -> Iterator[bool]:
    validate_directory_chain(path.parent, path.parent, uid=uid)
    created = False
    try:
        descriptor = os.open(
            path,
            os.O_RDWR | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
            0o600,
        )
        created = True
        if uid == 0:
            os.fchown(descriptor, 0, 0)
        os.fchmod(descriptor, 0o600)
        os.fsync(descriptor)
        _fsync_directory(path.parent)
    except FileExistsError:
        descriptor = os.open(path, os.O_RDWR | getattr(os, "O_NOFOLLOW", 0))
    try:
        _assert_no_acl(path)
        observed = os.fstat(descriptor)
        if (
            not stat.S_ISREG(observed.st_mode)
            or observed.st_uid != uid
            or observed.st_nlink != 1
            or stat.S_IMODE(observed.st_mode) != 0o600
        ):
            raise U10ProvisioningError("u10_lock_untrusted", str(path))
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield created
    finally:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)


@contextmanager
def _existing_exclusive_lock_v2(path: Path, *, uid: int) -> Iterator[None]:
    """Lock one pre-provisioned regular file without ever creating it.

    Key-transition locking is part of the installed trust denominator.  A
    missing lock is therefore an incomplete installation, not something a
    transition is allowed to repair implicitly.
    """

    if not path.exists() and not path.is_symlink():
        raise U10ProvisioningError("u10_key_lock_missing", str(path))
    _assert_directory(path.parent, uid=uid)
    descriptor = os.open(
        path,
        os.O_RDWR | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        _assert_no_acl(path)
        observed = os.fstat(descriptor)
        if (
            not stat.S_ISREG(observed.st_mode)
            or observed.st_uid != uid
            or observed.st_nlink != 1
            or stat.S_IMODE(observed.st_mode) != 0o600
        ):
            raise U10ProvisioningError("u10_key_lock_untrusted", str(path))
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)


@contextmanager
def _key_transition_locks_v2(paths: KeyPaths, *, uid: int) -> Iterator[None]:
    """Acquire the fixed U-10 lock hierarchy in its only permitted order."""

    with _existing_exclusive_lock_v2(paths.trust_store_lock_path, uid=uid):
        with _existing_exclusive_lock_v2(paths.lock_path, uid=uid):
            yield


def ensure_preboot_ledger(
    *, ledger_root: Path = PREBOOT_LEDGER_ROOT, required_uid: int = 0
) -> str:
    """Create only the fixed preboot ledger, or verify its exact prior state."""

    if required_uid == 0:
        if ledger_root != PREBOOT_LEDGER_ROOT:
            raise U10ProvisioningError("u10_preboot_ledger_not_fixed", str(ledger_root))
        application_support = Path("/Library/Application Support")
        validate_directory_chain(
            Path("/"),
            application_support,
            uid=0,
            strict_from_filesystem_root=True,
        )
        semantic_guard_parent = application_support / "semantic-guard"
        if (
            not semantic_guard_parent.exists()
            and not semantic_guard_parent.is_symlink()
        ):
            os.mkdir(semantic_guard_parent, 0o755)
            os.chown(semantic_guard_parent, 0, 0)
            os.chmod(semantic_guard_parent, 0o755)
            _fsync_directory(application_support)
        _assert_directory(semantic_guard_parent, uid=0, exact_mode=0o755)
    else:
        semantic_guard_parent = ledger_root.parent
        _assert_directory(semantic_guard_parent, uid=required_uid)
    if ledger_root.exists() or ledger_root.is_symlink():
        _assert_directory(ledger_root, uid=required_uid, exact_mode=0o700)
        return "existing_exact"
    os.mkdir(ledger_root, 0o700)
    if required_uid == 0:
        os.chown(ledger_root, 0, 0)
    os.chmod(ledger_root, 0o700)
    _fsync_directory(semantic_guard_parent)
    _assert_directory(ledger_root, uid=required_uid, exact_mode=0o700)
    return "created_by_observation_loader"


def _decode_capsule(raw: bytes) -> tuple[dict[str, Any], dict[str, bytes]]:
    if not 2 <= len(raw) <= 512 * 1024 * 1024:
        raise U10ProvisioningError("u10_capsule_size_invalid", str(len(raw)))
    try:
        capsule = strict_json_loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise U10ProvisioningError("u10_capsule_unreadable", "invalid JSON") from exc
    capsule = _require_exact_keys(
        capsule,
        {
            "schema_version",
            "capsule_kind",
            "invocation_id",
            "members",
            "formal_authority",
            "positive_assurance_allowed",
        },
        code="u10_capsule_shape_invalid",
    )
    if capsule["schema_version"] != CAPSULE_SCHEMA:
        raise U10ProvisioningError(
            "u10_capsule_schema_invalid", str(capsule.get("schema_version"))
        )
    if capsule["capsule_kind"] not in {
        "root_runtime_observation",
        "bootstrap_publication",
    }:
        raise U10ProvisioningError(
            "u10_capsule_kind_invalid", str(capsule["capsule_kind"])
        )
    _require_id(capsule["invocation_id"], code="u10_capsule_invocation_id_invalid")
    if (
        capsule["formal_authority"] != "none"
        or capsule["positive_assurance_allowed"] is not False
    ):
        raise U10ProvisioningError(
            "u10_capsule_authority_invalid", "capsule grants authority"
        )
    members_raw = capsule["members"]
    if not isinstance(members_raw, list) or not 1 <= len(members_raw) <= 20000:
        raise U10ProvisioningError("u10_capsule_members_invalid", "empty")
    members: dict[str, bytes] = {}
    decoded_total = 0
    previous = ""
    for item in members_raw:
        item = _require_exact_keys(
            item,
            {"name", "encoding", "content", "artifact_digest"},
            code="u10_capsule_member_shape_invalid",
        )
        name = _require_member(item["name"], code="u10_capsule_member_name_invalid")
        if name <= previous or name in members:
            raise U10ProvisioningError("u10_capsule_member_order_invalid", name)
        previous = name
        if item["encoding"] != "base64":
            raise U10ProvisioningError("u10_capsule_member_encoding_invalid", name)
        try:
            content = base64.b64decode(item["content"], validate=True)
        except (ValueError, TypeError) as exc:
            raise U10ProvisioningError(
                "u10_capsule_member_content_invalid", name
            ) from exc
        if len(content) > 64 * 1024 * 1024:
            raise U10ProvisioningError("u10_capsule_member_too_large", name)
        decoded_total += len(content)
        if decoded_total > 384 * 1024 * 1024:
            raise U10ProvisioningError(
                "u10_capsule_denominator_too_large", str(decoded_total)
            )
        if digest_bytes(content) != _require_digest(
            item["artifact_digest"], code="u10_capsule_member_digest_invalid"
        ):
            raise U10ProvisioningError("u10_capsule_member_digest_mismatch", name)
        members[name] = content
    return capsule, members


def _load_json_member(
    members: Mapping[str, bytes], name: str, *, code: str
) -> tuple[dict[str, Any], bytes]:
    try:
        raw = members[name]
    except KeyError as exc:
        raise U10ProvisioningError(code, name) from exc
    try:
        value = strict_json_loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise U10ProvisioningError(code, name) from exc
    if not isinstance(value, dict):
        raise U10ProvisioningError(code, name)
    return value, raw


def validate_bootstrap_authorization(
    authorization: Mapping[str, Any],
    *,
    plan: Mapping[str, Any],
    plan_raw: bytes,
    effective_at: datetime | None = None,
) -> None:
    item = _require_exact_keys(
        authorization,
        {
            "schema_version",
            "authorization_id",
            "authorization_version",
            "record_kind",
            "plan_ref",
            "target_root",
            "authorized_operation",
            "human_decision",
            "decision_owner",
            "recorded_at",
            "not_before",
            "expires_at",
            "authority_scope",
            "u4_principal_authenticity",
            "formal_authority",
            "positive_assurance_allowed",
            "authorization_digest",
        },
        code="u10_bootstrap_authorization_shape_invalid",
    )
    if (
        item["schema_version"] != BOOTSTRAP_AUTH_SCHEMA
        or item["authorization_version"] != "1.0.0"
        or item["record_kind"] != "bootstrap_provisioning_authorization"
        or item["target_root"] != str(U10_ROOT)
        or item["authorized_operation"] != "publish_exact_initial_u10_root"
        or item["human_decision"] != "accept"
        or item["decision_owner"] != "human"
        or item["authority_scope"] != "initial_u10_root_publication_only"
        or item["u4_principal_authenticity"] != "unresolved"
        or item["formal_authority"] != "human_bootstrap_publication_decision_only"
        or item["positive_assurance_allowed"] is not False
    ):
        raise U10ProvisioningError(
            "u10_bootstrap_authorization_invalid", "fixed fields"
        )
    _require_id(item["authorization_id"], code="u10_bootstrap_authorization_id_invalid")
    if item["authorization_id"] != plan.get("expected_authorization_id"):
        raise U10ProvisioningError(
            "u10_bootstrap_expected_authorization_mismatch",
            str(item["authorization_id"]),
        )
    if sealed_digest(item, "authorization_digest") != _require_digest(
        item["authorization_digest"], code="u10_bootstrap_authorization_digest_invalid"
    ):
        raise U10ProvisioningError(
            "u10_bootstrap_authorization_seal_mismatch", item["authorization_id"]
        )
    plan_ref = _require_exact_keys(
        item["plan_ref"],
        {
            "plan_id",
            "plan_version",
            "record_member",
            "artifact_digest",
            "semantic_digest",
        },
        code="u10_bootstrap_plan_ref_invalid",
    )
    if (
        plan_ref["plan_id"] != plan.get("plan_id")
        or plan_ref["plan_version"] != plan.get("plan_version")
        or plan_ref["record_member"]
        != f"records/bootstrap-plans/{plan['plan_id']}.json"
        or plan_ref["artifact_digest"] != digest_bytes(plan_raw)
        or plan_ref["semantic_digest"] != plan.get("plan_digest")
    ):
        raise U10ProvisioningError("u10_bootstrap_plan_binding_mismatch", str(plan_ref))
    recorded = _parse_time(
        item["recorded_at"], code="u10_bootstrap_authorization_time_invalid"
    )
    not_before = _parse_time(
        item["not_before"], code="u10_bootstrap_authorization_time_invalid"
    )
    expires = _parse_time(
        item["expires_at"], code="u10_bootstrap_authorization_time_invalid"
    )
    evaluated = datetime.now(timezone.utc) if effective_at is None else effective_at
    if not (recorded <= not_before <= evaluated <= expires):
        raise U10ProvisioningError(
            "u10_bootstrap_authorization_time_invalid", str(evaluated)
        )


def validate_bootstrap_plan(
    plan: Mapping[str, Any], members: Mapping[str, bytes]
) -> list[dict[str, Any]]:
    item = _require_exact_keys(
        plan,
        {
            "schema_version",
            "plan_id",
            "plan_version",
            "record_kind",
            "target_root",
            "target_root_mode",
            "expected_authorization_id",
            "preboot_ledger_binding",
            "runtime_bindings",
            "bootstrap_kit_denominator",
            "root_observation_ref",
            "target_denominator",
            "trust_boundary",
            "formal_authority",
            "positive_assurance_allowed",
            "plan_digest",
        },
        code="u10_bootstrap_plan_shape_invalid",
    )
    if (
        item["schema_version"] != BOOTSTRAP_PLAN_SCHEMA
        or item["plan_version"] != "1.0.0"
        or item["record_kind"] != "initial_u10_root_provisioning_plan"
        or item["target_root"] != str(U10_ROOT)
        or item["target_root_mode"] != 0o755
        or item["trust_boundary"]
        != {
            "covered": "exact_capsule_bytes_root_observation_and_atomic_initial_publication",
            "not_claimed": "root_os_or_hardware_compromise_resistance",
        }
        or item["formal_authority"] != "none"
        or item["positive_assurance_allowed"] is not False
    ):
        raise U10ProvisioningError("u10_bootstrap_plan_invalid", "fixed fields")
    _require_id(item["plan_id"], code="u10_bootstrap_plan_id_invalid")
    _require_id(
        item["expected_authorization_id"],
        code="u10_bootstrap_expected_authorization_id_invalid",
    )
    ledger_binding = _require_exact_keys(
        item["preboot_ledger_binding"],
        {
            "root",
            "policy",
            "authorization_record",
            "plan_record",
            "consumption_record",
            "receipt_record",
        },
        code="u10_preboot_ledger_binding_invalid",
    )
    expected_authorization = item["expected_authorization_id"]
    if (
        ledger_binding["root"] != str(PREBOOT_LEDGER_ROOT)
        or ledger_binding["policy"]
        != "append_only_exact_id_resolution_outside_target/v1"
        or ledger_binding["authorization_record"]
        != f"{expected_authorization}.authorization.json"
        or ledger_binding["plan_record"] != f"{expected_authorization}.plan.json"
        or ledger_binding["consumption_record"]
        != f"{expected_authorization}.consumption.json"
        or ledger_binding["receipt_record"] != f"{expected_authorization}.receipt.json"
    ):
        raise U10ProvisioningError(
            "u10_preboot_ledger_binding_invalid", expected_authorization
        )
    if sealed_digest(item, "plan_digest") != _require_digest(
        item["plan_digest"], code="u10_bootstrap_plan_digest_invalid"
    ):
        raise U10ProvisioningError("u10_bootstrap_plan_seal_mismatch", item["plan_id"])
    kit = _require_exact_keys(
        item["bootstrap_kit_denominator"],
        {"status", "entry_count", "entries", "denominator_digest"},
        code="u10_bootstrap_kit_denominator_invalid",
    )
    if (
        kit["status"] != "closed"
        or not isinstance(kit["entries"], list)
        or kit["entry_count"] != len(kit["entries"])
    ):
        raise U10ProvisioningError("u10_bootstrap_kit_denominator_invalid", "count")
    kit_material: list[dict[str, Any]] = []
    kit_roles: set[str] = set()
    kit_members: set[str] = set()
    for entry in kit["entries"]:
        entry = _require_exact_keys(
            entry,
            {"role", "member", "artifact_digest"},
            code="u10_bootstrap_kit_entry_invalid",
        )
        role = _require_id(entry["role"], code="u10_bootstrap_kit_role_invalid")
        member = _require_member(
            entry["member"], code="u10_bootstrap_kit_member_invalid"
        )
        if role in kit_roles or member in kit_members or member not in members:
            raise U10ProvisioningError("u10_bootstrap_kit_denominator_invalid", member)
        if digest_bytes(members[member]) != _require_digest(
            entry["artifact_digest"], code="u10_bootstrap_kit_digest_invalid"
        ):
            raise U10ProvisioningError("u10_bootstrap_kit_digest_mismatch", member)
        kit_roles.add(role)
        kit_members.add(member)
        kit_material.append(dict(entry))
    required_kit_roles = {
        "initial_capsule_provisioner",
        "broker_runtime_manifest_generator",
        "control_runtime_manifest_generator",
        "initial_fixed_entrypoint",
    }
    if not required_kit_roles.issubset(kit_roles):
        raise U10ProvisioningError(
            "u10_bootstrap_kit_role_missing",
            str(sorted(required_kit_roles - kit_roles)),
        )
    if digest_bytes(canonical_json_bytes({"entries": kit_material})) != _require_digest(
        kit["denominator_digest"], code="u10_bootstrap_kit_denominator_digest_invalid"
    ):
        raise U10ProvisioningError(
            "u10_bootstrap_kit_denominator_digest_mismatch", item["plan_id"]
        )
    runtimes = _require_exact_keys(
        item["runtime_bindings"],
        {"broker", "control"},
        code="u10_runtime_bindings_invalid",
    )
    for name, flags, effective_target, manifest_target, generator_role in (
        (
            "broker",
            ["-I", "-S", "-B"],
            BROKER_EFFECTIVE_PATH,
            BROKER_RUNTIME_MANIFEST,
            "broker_runtime_manifest_generator",
        ),
        (
            "control",
            ["-I", "-B"],
            CONTROL_EFFECTIVE_PATH,
            CONTROL_RUNTIME_MANIFEST,
            "control_runtime_manifest_generator",
        ),
    ):
        runtime = _require_exact_keys(
            runtimes[name],
            {
                "effective_interpreter_locator",
                "effective_interpreter_artifact_digest",
                "python_flags",
                "effective_path_target",
                "manifest_target",
                "manifest_generator_role",
                "expected_manifest_digest",
            },
            code="u10_runtime_binding_invalid",
        )
        _require_canonical_absolute(
            runtime["effective_interpreter_locator"],
            code="u10_runtime_interpreter_invalid",
        )
        _require_digest(
            runtime["effective_interpreter_artifact_digest"],
            code="u10_runtime_interpreter_digest_invalid",
        )
        _require_digest(
            runtime["expected_manifest_digest"],
            code="u10_runtime_manifest_digest_invalid",
        )
        if (
            runtime["python_flags"] != flags
            or runtime["effective_path_target"] != str(effective_target)
            or runtime["manifest_target"] != str(manifest_target)
            or runtime["manifest_generator_role"] != generator_role
        ):
            raise U10ProvisioningError("u10_runtime_binding_invalid", name)
    observation_ref = _require_exact_keys(
        item["root_observation_ref"],
        {
            "request_id",
            "receipt_id",
            "receipt_member",
            "receipt_artifact_digest",
            "receipt_digest",
            "broker_manifest_member",
            "broker_manifest_artifact_digest",
            "broker_manifest_digest",
            "control_manifest_member",
            "control_manifest_artifact_digest",
            "control_manifest_digest",
        },
        code="u10_root_observation_ref_invalid",
    )
    _require_id(
        observation_ref["request_id"], code="u10_root_observation_request_id_invalid"
    )
    _require_id(
        observation_ref["receipt_id"], code="u10_root_observation_receipt_id_invalid"
    )
    for field in (
        "receipt_member",
        "broker_manifest_member",
        "control_manifest_member",
    ):
        member = _require_member(
            observation_ref[field], code="u10_root_observation_member_invalid"
        )
        if member not in members:
            raise U10ProvisioningError("u10_root_observation_member_missing", member)
    for member_field, digest_field in (
        ("receipt_member", "receipt_artifact_digest"),
        ("broker_manifest_member", "broker_manifest_artifact_digest"),
        ("control_manifest_member", "control_manifest_artifact_digest"),
    ):
        if digest_bytes(members[observation_ref[member_field]]) != _require_digest(
            observation_ref[digest_field],
            code="u10_root_observation_artifact_digest_invalid",
        ):
            raise U10ProvisioningError(
                "u10_root_observation_artifact_digest_mismatch",
                observation_ref[member_field],
            )
    receipt_value, _ = _load_json_member(
        members,
        observation_ref["receipt_member"],
        code="u10_root_observation_receipt_invalid",
    )
    broker_value, _ = _load_json_member(
        members,
        observation_ref["broker_manifest_member"],
        code="u10_root_observation_manifest_invalid",
    )
    control_value, _ = _load_json_member(
        members,
        observation_ref["control_manifest_member"],
        code="u10_root_observation_manifest_invalid",
    )
    if (
        receipt_value.get("schema_version") != RUNTIME_OBSERVATION_RECEIPT_SCHEMA
        or receipt_value.get("request_id") != observation_ref["request_id"]
        or receipt_value.get("receipt_id") != observation_ref["receipt_id"]
        or sealed_digest(receipt_value, "receipt_digest")
        != observation_ref["receipt_digest"]
        or broker_value.get("manifest_digest")
        != observation_ref["broker_manifest_digest"]
        or control_value.get("manifest_digest")
        != observation_ref["control_manifest_digest"]
        or receipt_value.get("broker_manifest_ref", {}).get("manifest_digest")
        != observation_ref["broker_manifest_digest"]
        or receipt_value.get("control_manifest_ref", {}).get("manifest_digest")
        != observation_ref["control_manifest_digest"]
        or runtimes["broker"]["expected_manifest_digest"]
        != observation_ref["broker_manifest_digest"]
        or runtimes["control"]["expected_manifest_digest"]
        != observation_ref["control_manifest_digest"]
    ):
        raise U10ProvisioningError(
            "u10_root_observation_semantic_binding_mismatch", item["plan_id"]
        )
    denominator = _require_exact_keys(
        item["target_denominator"],
        {"status", "entry_count", "entries", "tree_digest"},
        code="u10_target_denominator_invalid",
    )
    entries = denominator["entries"]
    if (
        denominator["status"] != "closed"
        or not isinstance(entries, list)
        or denominator["entry_count"] != len(entries)
    ):
        raise U10ProvisioningError("u10_target_denominator_invalid", "count")
    prior_path = ""
    roles: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for entry in entries:
        common = {"relative_path", "kind", "mode", "uid", "gid", "role"}
        if not isinstance(entry, dict) or not common.issubset(entry):
            raise U10ProvisioningError("u10_target_entry_invalid", str(entry))
        relative = _require_member(
            entry["relative_path"], code="u10_target_relative_path_invalid"
        )
        role = _require_id(entry["role"], code="u10_target_role_invalid")
        if (
            relative <= prior_path
            or role in roles
            or entry["uid"] != 0
            or entry["gid"] != 0
        ):
            raise U10ProvisioningError("u10_target_denominator_invalid", relative)
        prior_path = relative
        roles.add(role)
        if entry["kind"] == "directory":
            _require_exact_keys(
                entry, common, code="u10_target_directory_entry_invalid"
            )
        elif entry["kind"] == "file":
            _require_exact_keys(
                entry,
                common | {"artifact_digest", "source"},
                code="u10_target_file_entry_invalid",
            )
            _require_digest(
                entry["artifact_digest"], code="u10_target_file_digest_invalid"
            )
            source = entry["source"]
            if source in {
                "generated_broker_effective_path",
                "generated_broker_runtime_manifest",
                "generated_control_effective_path",
                "generated_control_runtime_manifest",
                "generated_bootstrap_provenance_binding",
                "generated_empty_lock_file",
            }:
                pass
            else:
                source = _require_member(source, code="u10_target_source_invalid")
                if (
                    source not in members
                    or digest_bytes(members[source]) != entry["artifact_digest"]
                ):
                    raise U10ProvisioningError(
                        "u10_target_source_digest_mismatch", source
                    )
        else:
            raise U10ProvisioningError("u10_target_kind_invalid", relative)
        if not isinstance(entry["mode"], int) or not 0 <= entry["mode"] <= 0o7777:
            raise U10ProvisioningError("u10_target_mode_invalid", relative)
        normalized.append(dict(entry))
    required_generated = {
        "broker_effective_python_path",
        "broker_runtime_manifest",
        "control_effective_python_path",
        "control_runtime_manifest",
        "bootstrap_provenance_binding",
    }
    if not required_generated.issubset(roles):
        raise U10ProvisioningError(
            "u10_generated_target_role_missing", str(sorted(required_generated - roles))
        )
    required_role_paths = {
        "broker_effective_python_path": (
            "bootstrap/effective-python.path",
            "file",
        ),
        "broker_runtime_manifest": (
            "bootstrap/effective-python-runtime-manifest.json",
            "file",
        ),
        "control_effective_python_path": (
            "bootstrap/control-effective-python.path",
            "file",
        ),
        "control_runtime_manifest": (
            "bootstrap/control-python-runtime-manifest.json",
            "file",
        ),
        "bootstrap_provenance_binding": (
            "bootstrap/initial-bootstrap-provenance-binding.json",
            "file",
        ),
        "root_execution_entrypoint": (
            "bootstrap/u10_root_broker_entrypoint.sh",
            "file",
        ),
        "root_execution_outer": (
            "bootstrap/u10_root_broker_outer_launcher.py",
            "file",
        ),
        "root_candidate_installer_entrypoint": (
            "bootstrap/u10_root_candidate_installer_entrypoint.sh",
            "file",
        ),
        "root_candidate_installer": (
            "bootstrap/prepare_u10_root_candidate.py",
            "file",
        ),
        "root_control_entrypoint": (
            "bootstrap/u10_root_control_entrypoint.sh",
            "file",
        ),
        "root_control_outer": (
            "bootstrap/u10_root_control_outer_launcher.py",
            "file",
        ),
        "root_control_dispatcher": (
            "bootstrap/u10_root_control_dispatcher.py",
            "file",
        ),
        "broker_runtime_manifest_generator": (
            "bootstrap/prepare_u10_bootstrap_runtime_manifest.py",
            "file",
        ),
        "control_runtime_manifest_generator": (
            "bootstrap/prepare_u10_control_runtime_manifest.py",
            "file",
        ),
        "snapshot_store_producer": (
            "bootstrap/u10_snapshot_store_production.py",
            "file",
        ),
        "initial_fixed_entrypoint": (
            "bootstrap/u10_initial_trust_entrypoint.sh",
            "file",
        ),
        "initial_capsule_provisioner": (
            "bootstrap/u10_initial_trust_provisioner.py",
            "file",
        ),
        "broker_package_closure": (
            "bootstrap/semantic_guard_u10_broker",
            "directory",
        ),
        "bootstrap_directory": ("bootstrap", "directory"),
        "authorizations_directory": ("authorizations", "directory"),
        "key_authorizations_directory": ("authorizations/key", "directory"),
        "activations_directory": ("activations", "directory"),
        "store_transition_directory": (
            "activations/store-transitions",
            "directory",
        ),
        "store_revocation_transition_directory": (
            "activations/store-revocations",
            "directory",
        ),
        "snapshot_projection_ledger_directory": (
            "activations/snapshot-projections",
            "directory",
        ),
        "snapshot_activation_ledger_directory": (
            "activations/snapshot-activations",
            "directory",
        ),
        "snapshot_activation_record_directory": (
            "activations/snapshots",
            "directory",
        ),
        "store_activation_basis_directory": (
            "store-activation-bases",
            "directory",
        ),
        "key_transition_directory": (
            "activations/key-transitions",
            "directory",
        ),
        "keys_directory": ("keys", "directory"),
        "key_generations_directory": ("keys/generations", "directory"),
        "key_revocations_directory": ("keys/revocations", "directory"),
        "key_selector_history_directory": (
            "keys/selector-history",
            "directory",
        ),
        "key_selector_digest_directory": (
            "keys/selector-history/sha256",
            "directory",
        ),
        "snapshots_directory": ("snapshots", "directory"),
        "evidence_spool_directory": ("spool", "directory"),
        "nonce_ledger_directory": ("nonce-ledger", "directory"),
        "trust_store_history_directory": (
            "trust-store-history",
            "directory",
        ),
        "trust_store_history_digest_directory": (
            "trust-store-history/sha256",
            "directory",
        ),
        "revocations_directory": ("revocations", "directory"),
        "revocation_digest_directory": ("revocations/sha256", "directory"),
        "root_trust_store_lock": ("trust-store.lock", "file"),
        "root_key_transition_lock": ("keys/key-transition.lock", "file"),
        "snapshot_projection_lock": (
            "activations/snapshot-projections/snapshot-projection.lock",
            "file",
        ),
        "snapshot_activation_lock": (
            "activations/snapshot-activations/snapshot-activation.lock",
            "file",
        ),
    }
    entries_by_role = {entry["role"]: entry for entry in normalized}
    for role, (relative_path, kind) in required_role_paths.items():
        entry = entries_by_role.get(role)
        if (
            entry is None
            or entry.get("relative_path") != relative_path
            or entry.get("kind") != kind
        ):
            raise U10ProvisioningError("u10_required_target_role_invalid", role)
    for role in (
        "root_trust_store_lock",
        "root_key_transition_lock",
        "snapshot_projection_lock",
        "snapshot_activation_lock",
    ):
        entry = entries_by_role[role]
        if (
            entry.get("mode") != 0o600
            or entry.get("source") != "generated_empty_lock_file"
            or entry.get("artifact_digest") != digest_bytes(b"")
        ):
            raise U10ProvisioningError("u10_required_lock_contract_invalid", role)
    for role, mode in {
        "snapshot_store_producer": 0o400,
        "snapshot_projection_ledger_directory": 0o700,
        "snapshot_activation_ledger_directory": 0o700,
        "snapshot_activation_record_directory": 0o700,
        "store_activation_basis_directory": 0o700,
    }.items():
        if entries_by_role[role].get("mode") != mode:
            raise U10ProvisioningError("u10_required_target_mode_invalid", role)
    required_generated_sources = {
        "broker_effective_python_path": "generated_broker_effective_path",
        "broker_runtime_manifest": "generated_broker_runtime_manifest",
        "control_effective_python_path": "generated_control_effective_path",
        "control_runtime_manifest": "generated_control_runtime_manifest",
        "bootstrap_provenance_binding": ("generated_bootstrap_provenance_binding"),
    }
    for role, source in required_generated_sources.items():
        if entries_by_role[role].get("source") != source:
            raise U10ProvisioningError("u10_required_generated_source_invalid", role)
    by_source = {
        entry.get("source"): entry
        for entry in normalized
        if entry.get("kind") == "file"
    }
    if (
        by_source.get("generated_broker_runtime_manifest", {}).get("artifact_digest")
        != observation_ref["broker_manifest_artifact_digest"]
        or by_source.get("generated_control_runtime_manifest", {}).get(
            "artifact_digest"
        )
        != observation_ref["control_manifest_artifact_digest"]
    ):
        raise U10ProvisioningError(
            "u10_root_observation_target_digest_mismatch", item["plan_id"]
        )
    binding_entry = by_source.get("generated_bootstrap_provenance_binding", {})
    binding_raw = json_record_bytes(build_bootstrap_provenance_binding(item))
    if binding_entry.get("artifact_digest") != digest_bytes(binding_raw):
        raise U10ProvisioningError(
            "u10_bootstrap_provenance_binding_digest_mismatch", item["plan_id"]
        )
    if digest_bytes(canonical_json_bytes({"entries": normalized})) != _require_digest(
        denominator["tree_digest"], code="u10_target_tree_digest_invalid"
    ):
        raise U10ProvisioningError("u10_target_tree_digest_mismatch", item["plan_id"])
    return normalized


def build_bootstrap_provenance_binding(plan: Mapping[str, Any]) -> dict[str, Any]:
    authorization_id = str(plan["expected_authorization_id"])
    ledger = plan["preboot_ledger_binding"]
    observation = plan["root_observation_ref"]
    value: dict[str, Any] = {
        "schema_version": BOOTSTRAP_PROVENANCE_BINDING_SCHEMA,
        "binding_id": f"binding.{authorization_id}",
        "record_kind": "initial_bootstrap_external_chain_selector",
        "authorization_id": authorization_id,
        "plan_id": plan["plan_id"],
        "root_observation_request_id": observation["request_id"],
        "root_observation_receipt_id": observation["receipt_id"],
        "preboot_ledger_root": ledger["root"],
        "authorization_record": ledger["authorization_record"],
        "plan_record": ledger["plan_record"],
        "consumption_record": ledger["consumption_record"],
        "receipt_record": ledger["receipt_record"],
        "resolution_policy": (
            "resolve_exact_external_chain_then_reverse_validate_target_denominator/v1"
        ),
        "human_adoption_status": "pending",
        "formal_authority": "none",
        "positive_assurance_allowed": False,
    }
    value["binding_digest"] = sealed_digest(value, "binding_digest")
    return value


def validate_bootstrap_provenance_chain(
    *,
    binding_path: Path = U10_ROOT
    / "bootstrap"
    / "initial-bootstrap-provenance-binding.json",
    target_root: Path = U10_ROOT,
    ledger_root: Path = PREBOOT_LEDGER_ROOT,
    required_uid: int = 0,
) -> dict[str, Any]:
    """Resolve the target selector into the exact external bootstrap chain.

    This is a deterministic verification API for the control outer launcher.
    It grants no activation, adoption, or positive-assurance authority.
    """

    binding_raw = read_protected_file(
        binding_path,
        root=target_root,
        uid=required_uid,
        exact_mode=0o400,
    )
    try:
        binding = strict_json_loads(binding_raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise U10ProvisioningError(
            "u10_bootstrap_provenance_binding_unreadable", str(binding_path)
        ) from exc
    binding = _require_exact_keys(
        binding,
        {
            "schema_version",
            "binding_id",
            "record_kind",
            "authorization_id",
            "plan_id",
            "root_observation_request_id",
            "root_observation_receipt_id",
            "preboot_ledger_root",
            "authorization_record",
            "plan_record",
            "consumption_record",
            "receipt_record",
            "resolution_policy",
            "human_adoption_status",
            "formal_authority",
            "positive_assurance_allowed",
            "binding_digest",
        },
        code="u10_bootstrap_provenance_binding_invalid",
    )
    authorization_id = _require_id(
        binding["authorization_id"],
        code="u10_bootstrap_provenance_authorization_id_invalid",
    )
    if (
        binding["schema_version"] != BOOTSTRAP_PROVENANCE_BINDING_SCHEMA
        or binding["record_kind"] != "initial_bootstrap_external_chain_selector"
        or binding["preboot_ledger_root"] != str(PREBOOT_LEDGER_ROOT)
        or binding["authorization_record"] != f"{authorization_id}.authorization.json"
        or binding["plan_record"] != f"{authorization_id}.plan.json"
        or binding["consumption_record"] != f"{authorization_id}.consumption.json"
        or binding["receipt_record"] != f"{authorization_id}.receipt.json"
        or binding["resolution_policy"]
        != "resolve_exact_external_chain_then_reverse_validate_target_denominator/v1"
        or binding["human_adoption_status"] != "pending"
        or binding["formal_authority"] != "none"
        or binding["positive_assurance_allowed"] is not False
        or sealed_digest(binding, "binding_digest")
        != _require_digest(
            binding["binding_digest"],
            code="u10_bootstrap_provenance_binding_digest_invalid",
        )
    ):
        raise U10ProvisioningError(
            "u10_bootstrap_provenance_binding_invalid", authorization_id
        )
    if ledger_root != PREBOOT_LEDGER_ROOT and required_uid == 0:
        raise U10ProvisioningError(
            "u10_bootstrap_provenance_ledger_not_fixed", str(ledger_root)
        )
    records: dict[str, tuple[dict[str, Any], bytes]] = {}
    for key, name in (
        ("authorization", binding["authorization_record"]),
        ("plan", binding["plan_record"]),
        ("consumption", binding["consumption_record"]),
        ("receipt", binding["receipt_record"]),
    ):
        raw = read_protected_file(
            ledger_root / name,
            root=ledger_root,
            uid=required_uid,
            exact_mode=0o400,
        )
        try:
            value = strict_json_loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise U10ProvisioningError(
                "u10_bootstrap_provenance_record_unreadable", key
            ) from exc
        if not isinstance(value, dict):
            raise U10ProvisioningError(
                "u10_bootstrap_provenance_record_unreadable", key
            )
        records[key] = (value, raw)
    authorization, authorization_raw = records["authorization"]
    plan, plan_raw = records["plan"]
    consumption, consumption_raw = records["consumption"]
    receipt, receipt_raw = records["receipt"]
    authorization_consumed_at = _parse_time(
        consumption.get("reserved_at"),
        code="u10_bootstrap_provenance_chronology_invalid",
    )
    validate_bootstrap_authorization(
        authorization,
        plan=plan,
        plan_raw=plan_raw,
        effective_at=authorization_consumed_at,
    )
    if (
        authorization.get("authorization_id") != authorization_id
        or plan.get("plan_id") != binding["plan_id"]
        or plan.get("expected_authorization_id") != authorization_id
        or sealed_digest(plan, "plan_digest") != plan.get("plan_digest")
    ):
        raise U10ProvisioningError(
            "u10_bootstrap_provenance_plan_mismatch", authorization_id
        )
    matching_binding_entries = [
        entry
        for entry in plan.get("target_denominator", {}).get("entries", [])
        if entry.get("role") == "bootstrap_provenance_binding"
        and entry.get("relative_path")
        == "bootstrap/initial-bootstrap-provenance-binding.json"
        and entry.get("source") == "generated_bootstrap_provenance_binding"
    ]
    if len(matching_binding_entries) != 1 or matching_binding_entries[0].get(
        "artifact_digest"
    ) != digest_bytes(binding_raw):
        raise U10ProvisioningError(
            "u10_bootstrap_provenance_reverse_binding_mismatch", authorization_id
        )
    if (
        consumption.get("schema_version") != BOOTSTRAP_CONSUMPTION_SCHEMA
        or sealed_digest(consumption, "consumption_digest")
        != consumption.get("consumption_digest")
        or consumption.get("authorization_ref", {}).get("authorization_id")
        != authorization_id
        or consumption.get("authorization_ref", {}).get("authorization_digest")
        != authorization.get("authorization_digest")
        or consumption.get("authorization_ref", {}).get("artifact_digest")
        != digest_bytes(authorization_raw)
        or consumption.get("plan_ref", {}).get("plan_id") != plan.get("plan_id")
        or consumption.get("plan_ref", {}).get("plan_digest") != plan.get("plan_digest")
        or consumption.get("target_root") != str(target_root)
        or consumption.get("publication_occurred") is not False
    ):
        raise U10ProvisioningError(
            "u10_bootstrap_provenance_consumption_mismatch", authorization_id
        )
    if (
        receipt.get("schema_version") != BOOTSTRAP_RECEIPT_SCHEMA
        or sealed_digest(receipt, "receipt_digest") != receipt.get("receipt_digest")
        or receipt.get("authorization_ref", {}).get("authorization_id")
        != authorization_id
        or receipt.get("authorization_ref", {}).get("authorization_digest")
        != authorization.get("authorization_digest")
        or receipt.get("consumption_ref", {}).get("consumption_id")
        != consumption.get("consumption_id")
        or receipt.get("consumption_ref", {}).get("consumption_digest")
        != consumption.get("consumption_digest")
        or receipt.get("plan_ref", {}).get("plan_id") != plan.get("plan_id")
        or receipt.get("plan_ref", {}).get("plan_digest") != plan.get("plan_digest")
        or receipt.get("capsule_digest") != consumption.get("capsule_digest")
        or receipt.get("target_root") != str(target_root)
        or receipt.get("target_tree_digest")
        != plan.get("target_denominator", {}).get("tree_digest")
        or receipt.get("publication_occurred") is not True
    ):
        raise U10ProvisioningError(
            "u10_bootstrap_provenance_receipt_mismatch", authorization_id
        )
    reserved = authorization_consumed_at
    observed = _parse_time(
        receipt.get("publication_observed_at"),
        code="u10_bootstrap_provenance_chronology_invalid",
    )
    recorded = _parse_time(
        receipt.get("receipt_recorded_at"),
        code="u10_bootstrap_provenance_chronology_invalid",
    )
    if (
        receipt.get("publication_not_before") != consumption.get("reserved_at")
        or not reserved <= observed <= recorded
    ):
        raise U10ProvisioningError(
            "u10_bootstrap_provenance_chronology_invalid", authorization_id
        )
    return {
        "binding": binding,
        "authorization": authorization,
        "plan": plan,
        "consumption": consumption,
        "receipt": receipt,
        "artifact_digests": {
            "binding": digest_bytes(binding_raw),
            "authorization": digest_bytes(authorization_raw),
            "plan": digest_bytes(plan_raw),
            "consumption": digest_bytes(consumption_raw),
            "receipt": digest_bytes(receipt_raw),
        },
        "formal_authority": "none",
        "positive_assurance_allowed": False,
    }


def _runtime_generator_member(
    plan: Mapping[str, Any], members: Mapping[str, bytes], role: str
) -> tuple[str, bytes]:
    for entry in plan["bootstrap_kit_denominator"]["entries"]:
        if entry["role"] == role:
            return entry["member"], members[entry["member"]]
    raise U10ProvisioningError("u10_runtime_generator_missing", role)


def _default_runtime_manifest_builder(
    *, runtime_name: str, runtime: Mapping[str, Any], generator_raw: bytes, output: Path
) -> dict[str, Any]:
    generator_path = output.parent / f".{runtime_name}-manifest-generator.py"
    descriptor = os.open(
        generator_path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
        0o500,
    )
    try:
        _write_all(descriptor, generator_raw)
        os.fchmod(descriptor, 0o500)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    interpreter = str(runtime["effective_interpreter_locator"])
    command = [
        interpreter,
        *runtime["python_flags"],
        str(generator_path),
        "--interpreter",
        interpreter,
        "--output",
        str(output),
    ]
    completed = subprocess.run(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={"PATH": "", "LC_ALL": "C", "PYTHONDONTWRITEBYTECODE": "1"},
        check=False,
        timeout=120,
        text=True,
    )
    generator_path.unlink()
    if completed.returncode != 0:
        raise U10ProvisioningError(
            "u10_runtime_manifest_generation_failed",
            f"{runtime_name}: {completed.stderr[:1000]}",
        )
    raw = output.read_bytes()
    try:
        value = strict_json_loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise U10ProvisioningError(
            "u10_runtime_manifest_unreadable", runtime_name
        ) from exc
    if not isinstance(value, dict):
        raise U10ProvisioningError("u10_runtime_manifest_unreadable", runtime_name)
    return value


def _write_stage_file(path: Path, raw: bytes, *, mode: int) -> None:
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), mode
    )
    try:
        _write_all(descriptor, raw)
        os.fchmod(descriptor, mode)
        if os.geteuid() == 0:
            os.fchown(descriptor, 0, 0)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _observe_target_tree(
    root: Path, entries: list[dict[str, Any]], *, uid: int
) -> None:
    declared = {entry["relative_path"] for entry in entries}
    observed_paths: set[str] = set()
    for raw_root, directories, files in os.walk(root, topdown=True, followlinks=False):
        directories.sort()
        files.sort()
        base = Path(raw_root)
        for name in (*directories, *files):
            relative = (base / name).relative_to(root).as_posix()
            observed_paths.add(relative)
    if observed_paths != declared:
        raise U10ProvisioningError(
            "u10_target_denominator_not_closed",
            f"missing={sorted(declared - observed_paths)!r}; extra={sorted(observed_paths - declared)!r}",
        )
    for entry in entries:
        path = root / entry["relative_path"]
        observed = path.lstat()
        _assert_no_acl(path)
        expected_gid = 0 if uid == 0 else os.getegid()
        if (
            observed.st_uid != uid
            or observed.st_gid != expected_gid
            or stat.S_IMODE(observed.st_mode) != entry["mode"]
        ):
            raise U10ProvisioningError(
                "u10_target_observation_mismatch", entry["relative_path"]
            )
        if entry["kind"] == "directory":
            if stat.S_ISLNK(observed.st_mode) or not stat.S_ISDIR(observed.st_mode):
                raise U10ProvisioningError(
                    "u10_target_observation_mismatch", entry["relative_path"]
                )
        else:
            if (
                stat.S_ISLNK(observed.st_mode)
                or not stat.S_ISREG(observed.st_mode)
                or observed.st_nlink != 1
            ):
                raise U10ProvisioningError(
                    "u10_target_observation_mismatch", entry["relative_path"]
                )
            raw = read_protected_file(
                path, root=root, uid=uid, exact_mode=entry["mode"]
            )
            if digest_bytes(raw) != entry["artifact_digest"]:
                raise U10ProvisioningError(
                    "u10_target_observation_digest_mismatch", entry["relative_path"]
                )


def _bootstrap_record_paths(
    authorization_id: str, ledger_root: Path
) -> tuple[Path, Path, Path, Path, Path]:
    return (
        ledger_root / f"{authorization_id}.authorization.json",
        ledger_root / f"{authorization_id}.plan.json",
        ledger_root / f"{authorization_id}.consumption.json",
        ledger_root / f"{authorization_id}.receipt.json",
        ledger_root / "bootstrap.lock",
    )


def _assert_no_other_unresolved_consumption(
    *,
    ledger_root: Path,
    selected_id: str,
    suffix: str,
    uid: int,
    receipt_suffix: str,
    receipt_mode: int,
) -> None:
    for path in sorted(ledger_root.glob(f"*.{suffix}.json")):
        raw = read_protected_file(path, root=ledger_root, uid=uid, exact_mode=0o400)
        try:
            value = strict_json_loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise U10ProvisioningError(
                "u10_consumption_ledger_unreadable", str(path)
            ) from exc
        authorization_id = value.get("authorization_ref", {}).get("authorization_id")
        if authorization_id == selected_id:
            continue
        receipt = ledger_root / f"{authorization_id}.{receipt_suffix}.json"
        if not receipt.exists() and not receipt.is_symlink():
            raise U10ProvisioningError(
                "u10_unresolved_prior_consumption", str(authorization_id)
            )
        receipt_raw = read_protected_file(
            receipt,
            root=ledger_root,
            uid=uid,
            exact_mode=receipt_mode,
        )
        try:
            receipt_value = strict_json_loads(receipt_raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise U10ProvisioningError(
                "u10_consumption_receipt_unreadable", str(receipt)
            ) from exc
        if receipt_value.get("authorization_ref", {}).get(
            "authorization_id"
        ) != authorization_id or sealed_digest(
            receipt_value, "receipt_digest"
        ) != receipt_value.get("receipt_digest"):
            raise U10ProvisioningError("u10_consumption_receipt_invalid", str(receipt))


def validate_runtime_observation_request(
    request: Mapping[str, Any], members: Mapping[str, bytes]
) -> dict[str, Any]:
    item = _require_exact_keys(
        request,
        {
            "schema_version",
            "request_id",
            "request_version",
            "record_kind",
            "runtime_bindings",
            "bootstrap_kit_denominator",
            "authorized_operation",
            "human_decision",
            "decision_owner",
            "recorded_at",
            "not_before",
            "expires_at",
            "authority_scope",
            "formal_authority",
            "positive_assurance_allowed",
            "request_digest",
        },
        code="u10_runtime_observation_request_shape_invalid",
    )
    if (
        item["schema_version"] != RUNTIME_OBSERVATION_REQUEST_SCHEMA
        or item["request_version"] != "1.0.0"
        or item["record_kind"] != "bootstrap_runtime_root_observation_request"
        or item["authorized_operation"] != "observe_exact_root_runtimes_only"
        or item["human_decision"] != "accept"
        or item["decision_owner"] != "human"
        or item["authority_scope"] != "root_runtime_observation_no_target_publication"
        or item["formal_authority"] != "human_root_observation_decision_only"
        or item["positive_assurance_allowed"] is not False
    ):
        raise U10ProvisioningError(
            "u10_runtime_observation_request_invalid", "fixed fields"
        )
    _require_id(item["request_id"], code="u10_runtime_observation_request_id_invalid")
    if sealed_digest(item, "request_digest") != _require_digest(
        item["request_digest"], code="u10_runtime_observation_request_digest_invalid"
    ):
        raise U10ProvisioningError(
            "u10_runtime_observation_request_seal_mismatch", item["request_id"]
        )
    recorded = _parse_time(
        item["recorded_at"], code="u10_runtime_observation_request_time_invalid"
    )
    not_before = _parse_time(
        item["not_before"], code="u10_runtime_observation_request_time_invalid"
    )
    expires = _parse_time(
        item["expires_at"], code="u10_runtime_observation_request_time_invalid"
    )
    now = datetime.now(timezone.utc)
    if not (recorded <= not_before <= now <= expires):
        raise U10ProvisioningError(
            "u10_runtime_observation_request_time_invalid", str(now)
        )
    kit = _require_exact_keys(
        item["bootstrap_kit_denominator"],
        {"status", "entry_count", "entries", "denominator_digest"},
        code="u10_runtime_observation_kit_invalid",
    )
    if (
        kit["status"] != "closed"
        or not isinstance(kit["entries"], list)
        or kit["entry_count"] != len(kit["entries"])
    ):
        raise U10ProvisioningError("u10_runtime_observation_kit_invalid", "count")
    roles: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for entry in kit["entries"]:
        entry = _require_exact_keys(
            entry,
            {"role", "member", "artifact_digest"},
            code="u10_runtime_observation_kit_entry_invalid",
        )
        role = _require_id(entry["role"], code="u10_runtime_observation_role_invalid")
        member = _require_member(
            entry["member"], code="u10_runtime_observation_member_invalid"
        )
        if role in roles or member not in members:
            raise U10ProvisioningError("u10_runtime_observation_kit_invalid", member)
        if digest_bytes(members[member]) != _require_digest(
            entry["artifact_digest"], code="u10_runtime_observation_kit_digest_invalid"
        ):
            raise U10ProvisioningError(
                "u10_runtime_observation_kit_digest_mismatch", member
            )
        roles.add(role)
        normalized.append(dict(entry))
    required = {
        "initial_capsule_provisioner",
        "broker_runtime_manifest_generator",
        "control_runtime_manifest_generator",
    }
    if not required.issubset(roles):
        raise U10ProvisioningError(
            "u10_runtime_observation_role_missing", str(sorted(required - roles))
        )
    if digest_bytes(canonical_json_bytes({"entries": normalized})) != _require_digest(
        kit["denominator_digest"], code="u10_runtime_observation_kit_digest_invalid"
    ):
        raise U10ProvisioningError(
            "u10_runtime_observation_kit_denominator_mismatch", item["request_id"]
        )
    runtimes = _require_exact_keys(
        item["runtime_bindings"],
        {"broker", "control"},
        code="u10_runtime_observation_bindings_invalid",
    )
    for name, flags, generator_role in (
        ("broker", ["-I", "-S", "-B"], "broker_runtime_manifest_generator"),
        ("control", ["-I", "-B"], "control_runtime_manifest_generator"),
    ):
        runtime = _require_exact_keys(
            runtimes[name],
            {
                "effective_interpreter_locator",
                "effective_interpreter_artifact_digest",
                "python_flags",
                "manifest_generator_role",
            },
            code="u10_runtime_observation_binding_invalid",
        )
        _require_canonical_absolute(
            runtime["effective_interpreter_locator"],
            code="u10_runtime_observation_interpreter_invalid",
        )
        _require_digest(
            runtime["effective_interpreter_artifact_digest"],
            code="u10_runtime_observation_interpreter_digest_invalid",
        )
        if (
            runtime["python_flags"] != flags
            or runtime["manifest_generator_role"] != generator_role
        ):
            raise U10ProvisioningError("u10_runtime_observation_binding_invalid", name)
    return item


def execute_runtime_observation_from_capsule(
    capsule_raw: bytes,
    request_id: str,
    *,
    ledger_root: Path = PREBOOT_LEDGER_ROOT,
    runtime_manifest_builder: Callable[
        ..., dict[str, Any]
    ] = _default_runtime_manifest_builder,
    required_uid: int = 0,
) -> dict[str, Any]:
    capsule, members = _decode_capsule(capsule_raw)
    request_id = _require_id(
        request_id, code="u10_runtime_observation_request_id_invalid"
    )
    if (
        capsule["capsule_kind"] != "root_runtime_observation"
        or capsule["invocation_id"] != request_id
    ):
        raise U10ProvisioningError(
            "u10_runtime_observation_capsule_mismatch", request_id
        )
    request_member = f"records/bootstrap-runtime-observation-requests/{request_id}.json"
    request, request_raw = _load_json_member(
        members, request_member, code="u10_runtime_observation_request_missing"
    )
    request = validate_runtime_observation_request(request, members)
    if request["request_id"] != request_id:
        raise U10ProvisioningError(
            "u10_runtime_observation_request_mismatch", request_id
        )
    if required_uid == 0 and os.geteuid() != 0:
        raise U10ProvisioningError(
            "u10_runtime_observation_requires_root", str(os.geteuid())
        )
    ledger_initialization_state = ensure_preboot_ledger(
        ledger_root=ledger_root, required_uid=required_uid
    )
    request_path = ledger_root / f"{request_id}.observation-request.json"
    broker_path = ledger_root / f"{request_id}.broker-runtime-manifest.json"
    control_path = ledger_root / f"{request_id}.control-runtime-manifest.json"
    receipt_path = ledger_root / f"{request_id}.observation-receipt.json"
    lock_path = ledger_root / "runtime-observation.lock"
    with _exclusive_lock(lock_path, uid=required_uid) as lock_created:
        _atomic_append_only(request_path, request, mode=0o400)
        if receipt_path.exists():
            receipt = strict_json_loads(
                read_protected_file(
                    receipt_path,
                    root=ledger_root,
                    uid=required_uid,
                    exact_mode=0o400,
                )
            )
            if receipt.get("request_digest") != request["request_digest"]:
                raise U10ProvisioningError(
                    "u10_runtime_observation_receipt_collision", request_id
                )
            return receipt
        observed: dict[str, tuple[dict[str, Any], bytes, Path]] = {}
        started_at = utc_now()
        for name, final_path, generator_role in (
            ("broker", broker_path, "broker_runtime_manifest_generator"),
            ("control", control_path, "control_runtime_manifest_generator"),
        ):
            runtime = request["runtime_bindings"][name]
            interpreter = Path(runtime["effective_interpreter_locator"])
            if required_uid == 0:
                validate_directory_chain(
                    Path("/"),
                    interpreter.parent,
                    uid=0,
                    strict_from_filesystem_root=True,
                )
            interpreter_raw = read_protected_file(
                interpreter,
                root=interpreter.parent,
                uid=0 if required_uid == 0 else required_uid,
            )
            if (
                digest_bytes(interpreter_raw)
                != runtime["effective_interpreter_artifact_digest"]
            ):
                raise U10ProvisioningError(
                    "u10_runtime_observation_interpreter_digest_mismatch", name
                )
            _, generator_raw = _runtime_generator_member(
                {"bootstrap_kit_denominator": request["bootstrap_kit_denominator"]},
                members,
                generator_role,
            )
            temporary = ledger_root / f".{request_id}.{name}.manifest.tmp"
            if temporary.exists() or temporary.is_symlink():
                temporary.unlink()
            manifest = runtime_manifest_builder(
                runtime_name=name,
                runtime=runtime,
                generator_raw=generator_raw,
                output=temporary,
            )
            raw = json_record_bytes(manifest)
            if temporary.exists():
                if temporary.read_bytes() != raw:
                    raise U10ProvisioningError(
                        "u10_runtime_observation_manifest_encoding_mismatch", name
                    )
                temporary.unlink()
            _atomic_append_only(final_path, manifest, mode=0o400)
            observed[name] = (manifest, raw, final_path)
        observed_at = utc_now()
        receipt = {
            "schema_version": RUNTIME_OBSERVATION_RECEIPT_SCHEMA,
            "receipt_id": f"receipt.{request_id}",
            "record_kind": "bootstrap_runtime_root_observation_occurrence",
            "request_id": request_id,
            "request_digest": request["request_digest"],
            "request_artifact_digest": digest_bytes(request_raw),
            "capsule_digest": digest_bytes(capsule_raw),
            "broker_manifest_ref": {
                "locator": str(broker_path),
                "artifact_digest": digest_bytes(observed["broker"][1]),
                "manifest_digest": observed["broker"][0]["manifest_digest"],
            },
            "control_manifest_ref": {
                "locator": str(control_path),
                "artifact_digest": digest_bytes(observed["control"][1]),
                "manifest_digest": observed["control"][0]["manifest_digest"],
            },
            "preboot_ledger_initialization": {
                "root": str(ledger_root),
                "root_state": ledger_initialization_state,
                "root_mode": 448,
                "lock_locator": str(lock_path),
                "lock_state": (
                    "created_by_observation_loader"
                    if lock_created
                    else "existing_exact"
                ),
                "lock_mode": 384,
            },
            "observation_started_at": started_at,
            "observation_observed_at": observed_at,
            "receipt_recorded_at": utc_now(),
            "target_publication_occurred": False,
            "key_generation_occurred": False,
            "human_bootstrap_authorization_status": "pending",
            "formal_authority": "none",
            "positive_assurance_allowed": False,
        }
        receipt["receipt_digest"] = sealed_digest(receipt, "receipt_digest")
        _atomic_append_only(receipt_path, receipt, mode=0o400)
        return receipt


def execute_initial_bootstrap_from_capsule(
    capsule_raw: bytes,
    authorization_id: str,
    *,
    paths: BootstrapPaths = BootstrapPaths(),
    runtime_manifest_builder: Callable[
        ..., dict[str, Any]
    ] = _default_runtime_manifest_builder,
    required_uid: int = 0,
) -> dict[str, Any]:
    capsule, members = _decode_capsule(capsule_raw)
    authorization_id = _require_id(
        authorization_id, code="u10_bootstrap_authorization_id_invalid"
    )
    if (
        capsule["capsule_kind"] != "bootstrap_publication"
        or capsule["invocation_id"] != authorization_id
    ):
        raise U10ProvisioningError(
            "u10_capsule_authorization_mismatch", authorization_id
        )
    auth_member = f"records/bootstrap-authorizations/{authorization_id}.json"
    authorization, authorization_raw = _load_json_member(
        members, auth_member, code="u10_bootstrap_authorization_missing"
    )
    plan_id = authorization.get("plan_ref", {}).get("plan_id")
    _require_id(plan_id, code="u10_bootstrap_plan_id_invalid")
    plan_member = f"records/bootstrap-plans/{plan_id}.json"
    plan, plan_raw = _load_json_member(
        members, plan_member, code="u10_bootstrap_plan_missing"
    )
    entries = validate_bootstrap_plan(plan, members)
    validate_bootstrap_authorization(authorization, plan=plan, plan_raw=plan_raw)
    if authorization["authorization_id"] != authorization_id:
        raise U10ProvisioningError(
            "u10_bootstrap_authorization_mismatch", authorization_id
        )
    if paths.target_root != Path(plan["target_root"]) and paths.target_root == U10_ROOT:
        raise U10ProvisioningError(
            "u10_bootstrap_target_mismatch", str(paths.target_root)
        )
    if required_uid == 0 and os.geteuid() != 0:
        raise U10ProvisioningError("u10_bootstrap_requires_root", str(os.geteuid()))
    validate_directory_chain(paths.ledger_root, paths.ledger_root, uid=required_uid)
    auth_path, plan_path, consumption_path, receipt_path, lock_path = (
        _bootstrap_record_paths(authorization_id, paths.ledger_root)
    )
    with _exclusive_lock(lock_path, uid=required_uid):
        _atomic_append_only(auth_path, authorization, mode=0o400)
        _atomic_append_only(plan_path, plan, mode=0o400)
        _assert_no_other_unresolved_consumption(
            ledger_root=paths.ledger_root,
            selected_id=authorization_id,
            suffix="consumption",
            uid=required_uid,
            receipt_suffix="receipt",
            receipt_mode=0o400,
        )
        if receipt_path.exists():
            receipt_raw = read_protected_file(
                receipt_path, root=paths.ledger_root, uid=required_uid, exact_mode=0o400
            )
            receipt = strict_json_loads(receipt_raw)
            if (
                receipt.get("authorization_ref", {}).get("authorization_digest")
                != authorization["authorization_digest"]
            ):
                raise U10ProvisioningError(
                    "u10_bootstrap_receipt_collision", authorization_id
                )
            _observe_target_tree(paths.target_root, entries, uid=required_uid)
            return receipt
        consumption: dict[str, Any]
        if consumption_path.exists():
            consumption = strict_json_loads(
                read_protected_file(
                    consumption_path,
                    root=paths.ledger_root,
                    uid=required_uid,
                    exact_mode=0o400,
                )
            )
            if (
                consumption.get("authorization_ref", {}).get("authorization_digest")
                != authorization["authorization_digest"]
            ):
                raise U10ProvisioningError(
                    "u10_bootstrap_consumption_collision", authorization_id
                )
        else:
            consumption = {
                "schema_version": BOOTSTRAP_CONSUMPTION_SCHEMA,
                "consumption_id": f"consumption.{authorization_id}",
                "record_kind": "bootstrap_provisioning_authorization_consumption",
                "authorization_ref": {
                    "authorization_id": authorization_id,
                    "authorization_digest": authorization["authorization_digest"],
                    "artifact_digest": digest_bytes(authorization_raw),
                },
                "plan_ref": {
                    "plan_id": plan["plan_id"],
                    "plan_digest": plan["plan_digest"],
                },
                "capsule_digest": digest_bytes(capsule_raw),
                "target_root": str(paths.target_root),
                "occurrence_id": (
                    "bootstrap." + authorization["authorization_digest"]["value"]
                ),
                "reserved_at": utc_now(),
                "publication_occurred": False,
                "formal_authority": "none",
                "positive_assurance_allowed": False,
            }
            consumption["consumption_digest"] = sealed_digest(
                consumption, "consumption_digest"
            )
            _atomic_append_only(consumption_path, consumption, mode=0o400)
        if paths.target_root.exists() or paths.target_root.is_symlink():
            raise U10ProvisioningError(
                "u10_bootstrap_target_collision", str(paths.target_root)
            )
        stage = (
            paths.target_root.parent
            / f".{paths.target_root.name}.stage.{authorization['authorization_digest']['value'][:24]}"
        )
        _safe_remove_tree(stage, uid=required_uid)
        stage.mkdir(mode=0o700)
        if required_uid == 0:
            os.chown(stage, 0, 0)
        try:
            for entry in entries:
                if entry["kind"] != "directory":
                    continue
                target = stage / entry["relative_path"]
                target.mkdir(parents=False, mode=entry["mode"])
                os.chmod(target, entry["mode"])
                if required_uid == 0:
                    os.chown(target, 0, 0)
            runtimes = plan["runtime_bindings"]
            generated: dict[str, bytes] = {
                "generated_bootstrap_provenance_binding": json_record_bytes(
                    build_bootstrap_provenance_binding(plan)
                ),
                "generated_empty_lock_file": b"",
            }
            for name, effective_source, manifest_source, generator_role in (
                (
                    "broker",
                    "generated_broker_effective_path",
                    "generated_broker_runtime_manifest",
                    "broker_runtime_manifest_generator",
                ),
                (
                    "control",
                    "generated_control_effective_path",
                    "generated_control_runtime_manifest",
                    "control_runtime_manifest_generator",
                ),
            ):
                runtime = runtimes[name]
                interpreter = Path(runtime["effective_interpreter_locator"])
                interpreter_raw = read_protected_file(
                    interpreter,
                    root=interpreter.parent,
                    uid=0 if required_uid == 0 else required_uid,
                )
                if (
                    digest_bytes(interpreter_raw)
                    != runtime["effective_interpreter_artifact_digest"]
                ):
                    raise U10ProvisioningError(
                        "u10_runtime_interpreter_digest_mismatch", name
                    )
                generated[effective_source] = (str(interpreter) + "\n").encode("utf-8")
                _, generator_raw = _runtime_generator_member(
                    plan, members, generator_role
                )
                manifest_entry = next(
                    entry for entry in entries if entry.get("source") == manifest_source
                )
                manifest_output = stage / manifest_entry["relative_path"]
                manifest = runtime_manifest_builder(
                    runtime_name=name,
                    runtime=runtime,
                    generator_raw=generator_raw,
                    output=manifest_output,
                )
                manifest_raw = json_record_bytes(manifest)
                if manifest_output.exists():
                    actual = manifest_output.read_bytes()
                    if actual != manifest_raw:
                        raise U10ProvisioningError(
                            "u10_runtime_manifest_encoding_mismatch", name
                        )
                else:
                    _write_stage_file(
                        manifest_output, manifest_raw, mode=manifest_entry["mode"]
                    )
                generated[manifest_source] = manifest_raw
                if (
                    manifest.get("manifest_digest")
                    != runtime["expected_manifest_digest"]
                ):
                    raise U10ProvisioningError(
                        "u10_runtime_manifest_semantic_mismatch", name
                    )
            for entry in entries:
                if entry["kind"] != "file":
                    continue
                target = stage / entry["relative_path"]
                if target.exists():
                    raw = target.read_bytes()
                    os.chmod(target, entry["mode"])
                    if required_uid == 0:
                        os.chown(target, 0, 0)
                else:
                    raw = generated.get(entry["source"], members.get(entry["source"]))
                    if raw is None:
                        raise U10ProvisioningError(
                            "u10_target_source_missing", entry["source"]
                        )
                    _write_stage_file(target, raw, mode=entry["mode"])
                if digest_bytes(raw) != entry["artifact_digest"]:
                    raise U10ProvisioningError(
                        "u10_target_generated_digest_mismatch", entry["relative_path"]
                    )
            os.chmod(stage, plan["target_root_mode"])
            if required_uid == 0:
                os.chown(stage, 0, 0)
            for raw_root, _directories, _files in os.walk(stage, topdown=False):
                _fsync_directory(Path(raw_root))
            _observe_target_tree(stage, entries, uid=required_uid)
            _rename_directory_no_replace(stage, paths.target_root)
            _fsync_directory(paths.target_root.parent)
        except BaseException:
            if stage.exists() or stage.is_symlink():
                _safe_remove_tree(stage, uid=required_uid)
            raise
        _observe_target_tree(paths.target_root, entries, uid=required_uid)
        publication_observed_at = utc_now()
        receipt = {
            "schema_version": BOOTSTRAP_RECEIPT_SCHEMA,
            "receipt_id": f"receipt.{authorization_id}",
            "record_kind": "initial_u10_root_publication_occurrence",
            "occurrence_id": consumption["occurrence_id"],
            "authorization_ref": {
                "authorization_id": authorization_id,
                "authorization_digest": authorization["authorization_digest"],
            },
            "consumption_ref": {
                "consumption_id": consumption["consumption_id"],
                "consumption_digest": consumption["consumption_digest"],
            },
            "plan_ref": {
                "plan_id": plan["plan_id"],
                "plan_digest": plan["plan_digest"],
            },
            "capsule_digest": digest_bytes(capsule_raw),
            "target_root": str(paths.target_root),
            "target_tree_digest": plan["target_denominator"]["tree_digest"],
            "broker_runtime_manifest_digest": plan["runtime_bindings"]["broker"][
                "expected_manifest_digest"
            ],
            "control_runtime_manifest_digest": plan["runtime_bindings"]["control"][
                "expected_manifest_digest"
            ],
            "publication_not_before": consumption["reserved_at"],
            "publication_observed_at": publication_observed_at,
            "receipt_recorded_at": utc_now(),
            "publication_occurred": True,
            "installation_state": "initial_root_published_not_activated",
            "key_state": "not_generated",
            "human_adoption_status": "pending",
            "u4_principal_authenticity": "unresolved",
            "formal_authority": "none",
            "positive_assurance_allowed": False,
        }
        receipt["receipt_digest"] = sealed_digest(receipt, "receipt_digest")
        _atomic_append_only(receipt_path, receipt, mode=0o400)
        return receipt


def _key_record_paths(
    authorization_id: str, ledger_root: Path
) -> tuple[Path, Path, Path]:
    return (
        ledger_root / f"{authorization_id}.authorization.json",
        ledger_root / f"{authorization_id}.consumption.json",
        ledger_root / f"{authorization_id}.receipt.json",
    )


def _validate_publisher_contract_binding(
    value: Any,
) -> dict[str, Any]:
    """Validate the static fixed-control publication contract.

    Current-runtime re-observation belongs to the fixed dispatcher and broker
    core.  This provisioner nevertheless rejects malformed, caller-shaped, or
    unsealed bindings before reserving a key authorization.
    """

    item = _require_exact_keys(
        value,
        {
            "allowed_operations",
            "artifacts",
            "binding_digest",
            "bootstrap_provenance_ref",
            "broker_runtime_ref",
            "caller_environment_injection_allowed",
            "caller_supplied_inline_authority_allowed",
            "caller_supplied_paths_allowed",
            "caller_supplied_raw_payloads_allowed",
            "contract_id",
            "control_runtime_ref",
            "formal_authority",
            "launch_profile",
            "positive_assurance_allowed",
            "public_argument_denominator",
            "schema_version",
        },
        code="u10_publisher_contract_binding_invalid",
    )
    if (
        item["schema_version"] != CONTROL_PUBLISHER_BINDING_SCHEMA
        or item["contract_id"] != CONTROL_PUBLISHER_CONTRACT_ID
        or item["launch_profile"]
        != "fixed-root-wrapper-broker-outer-control-runtime-dispatcher/v1"
        or item["public_argument_denominator"] != ["operation", "identifier"]
        or item["allowed_operations"]
        != [
            "activate-snapshot",
            "activate-store",
            "key",
            "project-snapshot",
            "revoke-store",
        ]
        or any(
            item[field] is not False
            for field in (
                "caller_environment_injection_allowed",
                "caller_supplied_inline_authority_allowed",
                "caller_supplied_paths_allowed",
                "caller_supplied_raw_payloads_allowed",
                "positive_assurance_allowed",
            )
        )
        or item["formal_authority"] != "none"
        or sealed_digest(item, "binding_digest")
        != _require_digest(
            item["binding_digest"],
            code="u10_publisher_contract_binding_digest_invalid",
        )
    ):
        raise U10ProvisioningError(
            "u10_publisher_contract_binding_invalid", "fixed fields or seal"
        )
    artifacts = _require_exact_keys(
        item["artifacts"],
        set(CONTROL_PUBLISHER_ARTIFACTS),
        code="u10_publisher_contract_binding_artifacts_invalid",
    )
    for name, expected_path in CONTROL_PUBLISHER_ARTIFACTS.items():
        reference = _require_exact_keys(
            artifacts[name],
            {"locator", "artifact_digest"},
            code="u10_publisher_contract_binding_artifact_invalid",
        )
        if reference["locator"] != str(expected_path):
            raise U10ProvisioningError(
                "u10_publisher_contract_binding_artifact_invalid", name
            )
        _require_digest(
            reference["artifact_digest"],
            code="u10_publisher_contract_binding_artifact_invalid",
        )
    for field, effective_path, manifest_path in (
        (
            "broker_runtime_ref",
            BROKER_EFFECTIVE_PATH,
            BROKER_RUNTIME_MANIFEST,
        ),
        (
            "control_runtime_ref",
            CONTROL_EFFECTIVE_PATH,
            CONTROL_RUNTIME_MANIFEST,
        ),
    ):
        expected_fields = {
            "effective_python_path",
            "effective_python_path_artifact_digest",
            "runtime_manifest_artifact_digest",
            "runtime_manifest_digest",
            "runtime_manifest_locator",
            "runtime_tree_digest",
        }
        if field == "control_runtime_ref":
            expected_fields.add("broker_package_binding")
        reference = _require_exact_keys(
            item[field],
            expected_fields,
            code="u10_publisher_contract_binding_runtime_invalid",
        )
        if reference["effective_python_path"] != str(effective_path) or reference[
            "runtime_manifest_locator"
        ] != str(manifest_path):
            raise U10ProvisioningError(
                "u10_publisher_contract_binding_runtime_invalid", field
            )
        for digest_field in (
            "effective_python_path_artifact_digest",
            "runtime_manifest_artifact_digest",
            "runtime_manifest_digest",
            "runtime_tree_digest",
        ):
            _require_digest(
                reference[digest_field],
                code="u10_publisher_contract_binding_runtime_invalid",
            )
    package = _require_exact_keys(
        item["control_runtime_ref"]["broker_package_binding"],
        {"entry_count", "package_root", "tree_digest"},
        code="u10_publisher_contract_binding_package_invalid",
    )
    if not isinstance(package["entry_count"], int) or package["entry_count"] < 1:
        raise U10ProvisioningError(
            "u10_publisher_contract_binding_package_invalid", "entry_count"
        )
    _require_canonical_absolute(
        package["package_root"],
        code="u10_publisher_contract_binding_package_invalid",
    )
    _require_digest(
        package["tree_digest"],
        code="u10_publisher_contract_binding_package_invalid",
    )
    provenance = _require_exact_keys(
        item["bootstrap_provenance_ref"],
        {
            "authorization_id",
            "binding_artifact_digest",
            "binding_digest",
            "binding_id",
            "chain_artifact_digests",
            "locator",
            "plan_id",
        },
        code="u10_publisher_contract_binding_provenance_invalid",
    )
    if provenance["locator"] != str(INITIAL_BOOTSTRAP_PROVENANCE_BINDING):
        raise U10ProvisioningError(
            "u10_publisher_contract_binding_provenance_invalid", "locator"
        )
    for field in ("authorization_id", "binding_id", "plan_id"):
        _require_id(
            provenance[field],
            code="u10_publisher_contract_binding_provenance_invalid",
        )
    for field in ("binding_artifact_digest", "binding_digest"):
        _require_digest(
            provenance[field],
            code="u10_publisher_contract_binding_provenance_invalid",
        )
    chain = _require_exact_keys(
        provenance["chain_artifact_digests"],
        {"authorization", "plan", "consumption", "receipt"},
        code="u10_publisher_contract_binding_provenance_invalid",
    )
    for digest in chain.values():
        _require_digest(
            digest,
            code="u10_publisher_contract_binding_provenance_invalid",
        )
    return strict_json_loads(json.dumps(item, ensure_ascii=False, allow_nan=False))


def _generation_evidence_selector(
    authorization_id: str, paths: KeyPaths
) -> dict[str, Any]:
    return {
        "ledger_root": str(paths.ledger_root),
        "authorization_record": f"{authorization_id}.authorization.json",
        "consumption_record": f"{authorization_id}.consumption.json",
        "receipt_record": f"{authorization_id}.receipt.json",
        "resolution_policy": (
            "resolve_exact_generation_authorization_consumption_receipt/v1"
        ),
    }


def _generation_receipt_selector(
    authorization_id: str, paths: KeyPaths
) -> dict[str, Any]:
    return {
        "ledger_root": str(paths.ledger_root),
        "receipt_record": f"{authorization_id}.receipt.json",
        "resolution_policy": "resolve_exact_generation_receipt/v1",
    }


def validate_key_public_metadata(
    value: Mapping[str, Any], *, paths: KeyPaths = KeyPaths()
) -> dict[str, Any]:
    item = _require_exact_keys(
        value,
        {
            "algorithm",
            "authorization_ref",
            "created_at",
            "formal_authority",
            "generation_evidence_selector",
            "key_entity_ref",
            "key_id",
            "metadata_digest",
            "positive_assurance_allowed",
            "private_material",
            "public_key",
            "record_kind",
            "schema_version",
        },
        code="u10_key_metadata_shape_invalid",
    )
    key_id = str(item["key_id"])
    entity_ref = _require_entity_ref(
        item["key_entity_ref"], code="u10_key_metadata_entity_ref_invalid"
    )
    authorization_ref = _require_exact_keys(
        item["authorization_ref"],
        {"authorization_id", "authorization_digest"},
        code="u10_key_metadata_authorization_ref_invalid",
    )
    authorization_id = _require_id(
        authorization_ref["authorization_id"],
        code="u10_key_metadata_authorization_ref_invalid",
    )
    _require_digest(
        authorization_ref["authorization_digest"],
        code="u10_key_metadata_authorization_ref_invalid",
    )
    public_key = _require_exact_keys(
        item["public_key"],
        {"encoding", "value"},
        code="u10_key_public_material_invalid",
    )
    try:
        public_raw = base64.b64decode(public_key["value"], validate=True)
    except (TypeError, ValueError) as exc:
        raise U10ProvisioningError("u10_key_public_material_invalid", "base64") from exc
    private = _require_exact_keys(
        item["private_material"],
        {"locator", "storage_state"},
        code="u10_key_private_material_ref_invalid",
    )
    if (
        item["schema_version"] != KEY_METADATA_SCHEMA_V1
        or item["record_kind"] != "signing_key_public_metadata"
        or item["algorithm"] != "Ed25519"
        or _UUID.fullmatch(key_id) is None
        or entity_ref.rsplit("・", 1)[-1] != key_id
        or public_key["encoding"] != "raw_base64"
        or len(public_raw) != 32
        or private["locator"] != str(paths.generation_root / key_id / "private.ed25519")
        or private["storage_state"] != "root_only_0600_not_exported"
        or item["generation_evidence_selector"]
        != _generation_evidence_selector(authorization_id, paths)
        or item["formal_authority"] != "none"
        or item["positive_assurance_allowed"] is not False
        or sealed_digest(item, "metadata_digest")
        != _require_digest(
            item["metadata_digest"], code="u10_key_metadata_digest_invalid"
        )
    ):
        raise U10ProvisioningError("u10_key_metadata_invalid", "fixed fields or seal")
    _parse_time(item["created_at"], code="u10_key_metadata_time_invalid")
    return item


def _validate_public_metadata_ref(
    value: Any,
    *,
    metadata: Mapping[str, Any] | None,
    paths: KeyPaths,
) -> dict[str, Any]:
    item = _require_exact_keys(
        value,
        {
            "generation_authorization_ref",
            "generation_receipt_selector",
            "key_entity_ref",
            "key_id",
            "metadata_artifact_digest",
            "metadata_digest",
            "metadata_locator",
        },
        code="u10_key_public_metadata_ref_invalid",
    )
    key_id = str(item["key_id"])
    _require_entity_ref(
        item["key_entity_ref"], code="u10_key_public_metadata_ref_invalid"
    )
    authorization_ref = _require_exact_keys(
        item["generation_authorization_ref"],
        {"authorization_id", "authorization_digest"},
        code="u10_key_public_metadata_ref_invalid",
    )
    authorization_id = _require_id(
        authorization_ref["authorization_id"],
        code="u10_key_public_metadata_ref_invalid",
    )
    _require_digest(
        authorization_ref["authorization_digest"],
        code="u10_key_public_metadata_ref_invalid",
    )
    if (
        _UUID.fullmatch(key_id) is None
        or item["key_entity_ref"].rsplit("・", 1)[-1] != key_id
        or item["metadata_locator"]
        != str(paths.generation_root / key_id / "public-metadata.json")
        or item["generation_receipt_selector"]
        != _generation_receipt_selector(authorization_id, paths)
    ):
        raise U10ProvisioningError(
            "u10_key_public_metadata_ref_invalid", "fixed fields"
        )
    for field in ("metadata_artifact_digest", "metadata_digest"):
        _require_digest(item[field], code="u10_key_public_metadata_ref_invalid")
    if metadata is not None:
        metadata_raw = json_record_bytes(metadata)
        if (
            item["key_id"] != metadata["key_id"]
            or item["key_entity_ref"] != metadata["key_entity_ref"]
            or item["metadata_artifact_digest"] != digest_bytes(metadata_raw)
            or item["metadata_digest"] != metadata["metadata_digest"]
            or item["generation_authorization_ref"] != metadata["authorization_ref"]
        ):
            raise U10ProvisioningError("u10_key_public_metadata_ref_mismatch", key_id)
    return item


def validate_key_revocation(value: Mapping[str, Any]) -> dict[str, Any]:
    item = _require_exact_keys(
        value,
        {
            "authorization_ref",
            "formal_authority",
            "key_entity_ref",
            "key_id",
            "positive_assurance_allowed",
            "private_material_disposition",
            "record_kind",
            "revocation_digest",
            "revocation_id",
            "revoked_at",
            "schema_version",
        },
        code="u10_key_revocation_shape_invalid",
    )
    authorization_ref = _require_exact_keys(
        item["authorization_ref"],
        {"authorization_digest", "authorization_id"},
        code="u10_key_revocation_authorization_ref_invalid",
    )
    authorization_id = _require_id(
        authorization_ref["authorization_id"],
        code="u10_key_revocation_authorization_ref_invalid",
    )
    _require_digest(
        authorization_ref["authorization_digest"],
        code="u10_key_revocation_authorization_ref_invalid",
    )
    key_id = str(item["key_id"])
    entity_ref = _require_entity_ref(
        item["key_entity_ref"], code="u10_key_revocation_entity_ref_invalid"
    )
    if (
        item["schema_version"] != KEY_REVOCATION_SCHEMA_V1
        or item["revocation_id"] != f"revocation.{authorization_id}"
        or item["record_kind"] != "signing_key_revocation_occurrence"
        or _UUID.fullmatch(key_id) is None
        or entity_ref.rsplit("・", 1)[-1] != key_id
        or item["private_material_disposition"]
        != "retained_root_only_not_exported_pending_retention_policy"
        or item["formal_authority"] != "none"
        or item["positive_assurance_allowed"] is not False
        or sealed_digest(item, "revocation_digest")
        != _require_digest(
            item["revocation_digest"],
            code="u10_key_revocation_digest_invalid",
        )
    ):
        raise U10ProvisioningError("u10_key_revocation_invalid", authorization_id)
    _parse_time(item["revoked_at"], code="u10_key_revocation_time_invalid")
    return item


def validate_key_selector(
    value: Mapping[str, Any], *, paths: KeyPaths = KeyPaths()
) -> dict[str, Any]:
    item = _require_exact_keys(
        value,
        {
            "formal_authority",
            "key_entity_ref",
            "key_id",
            "positive_assurance_allowed",
            "public_metadata_ref",
            "record_kind",
            "schema_version",
            "selected_at",
            "selector_digest",
            "selector_id",
            "state",
            "transition_authorization_ref",
        },
        code="u10_key_selector_shape_invalid",
    )
    authorization_ref = _require_exact_keys(
        item["transition_authorization_ref"],
        {"authorization_id", "authorization_digest"},
        code="u10_key_selector_authorization_ref_invalid",
    )
    authorization_id = _require_id(
        authorization_ref["authorization_id"],
        code="u10_key_selector_authorization_ref_invalid",
    )
    _require_digest(
        authorization_ref["authorization_digest"],
        code="u10_key_selector_authorization_ref_invalid",
    )
    if (
        item["schema_version"] != KEY_SELECTOR_SCHEMA_V1
        or item["selector_id"] != f"selector.{authorization_id}"
        or item["record_kind"] != "current_signing_key_selector"
        or item["state"] not in {"active", "no_active_key"}
        or item["formal_authority"] != "none"
        or item["positive_assurance_allowed"] is not False
        or sealed_digest(item, "selector_digest")
        != _require_digest(
            item["selector_digest"], code="u10_key_selector_digest_invalid"
        )
    ):
        raise U10ProvisioningError("u10_key_selector_invalid", "fixed fields or seal")
    _parse_time(item["selected_at"], code="u10_key_selector_time_invalid")
    if item["state"] == "active":
        public_ref = _validate_public_metadata_ref(
            item["public_metadata_ref"], metadata=None, paths=paths
        )
        if (
            item["key_id"] != public_ref["key_id"]
            or item["key_entity_ref"] != public_ref["key_entity_ref"]
        ):
            raise U10ProvisioningError(
                "u10_key_selector_context_mismatch", authorization_id
            )
    elif any(
        item[field] is not None
        for field in ("key_id", "key_entity_ref", "public_metadata_ref")
    ):
        raise U10ProvisioningError(
            "u10_key_selector_context_mismatch", authorization_id
        )
    return item


def validate_key_authorization(
    value: Mapping[str, Any],
    *,
    paths: KeyPaths = KeyPaths(),
    effective_at: datetime | None = None,
) -> dict[str, Any]:
    item = _require_exact_keys(
        value,
        {
            "schema_version",
            "authorization_id",
            "authorization_version",
            "record_kind",
            "key_operation",
            "key_id",
            "key_entity_ref",
            "expected_current_key_id",
            "target_generation_path",
            "target_public_metadata_path",
            "target_private_key_path",
            "authorized_algorithm",
            "authorized_operation",
            "human_decision",
            "decision_owner",
            "recorded_at",
            "not_before",
            "expires_at",
            "u4_principal_authenticity",
            "authority_scope",
            "formal_authority",
            "positive_assurance_allowed",
            "authorization_digest",
        },
        code="u10_key_authorization_shape_invalid",
    )
    key_id = str(item["key_id"])
    if (
        item["schema_version"] != KEY_AUTH_SCHEMA_V1
        or item["authorization_version"] != "1.0.0"
        or item["record_kind"] != "signing_key_operation_authorization"
        or item["key_operation"] not in {"generate", "rotate", "revoke"}
        or _UUID.fullmatch(key_id) is None
        or item["key_entity_ref"].rsplit("・", 1)[-1] != key_id
        or item["target_generation_path"] != str(paths.generation_root / key_id)
        or item["target_public_metadata_path"]
        != str(paths.generation_root / key_id / "public-metadata.json")
        or item["target_private_key_path"]
        != str(paths.generation_root / key_id / "private.ed25519")
        or item["authorized_algorithm"] != "Ed25519"
        or item["authorized_operation"] != "apply_exact_key_lifecycle_transition"
        or item["human_decision"] != "accept"
        or item["decision_owner"] != "human"
        or item["u4_principal_authenticity"] != "unresolved"
        or item["authority_scope"] != "u10_signing_key_transition_only"
        or item["formal_authority"] != "human_key_transition_decision_only"
        or item["positive_assurance_allowed"] is not False
    ):
        raise U10ProvisioningError("u10_key_authorization_invalid", "fixed fields")
    _require_id(item["authorization_id"], code="u10_key_authorization_id_invalid")
    _require_entity_ref(item["key_entity_ref"], code="u10_key_entity_ref_invalid")
    previous = item["expected_current_key_id"]
    if item["key_operation"] == "generate" and previous is not None:
        raise U10ProvisioningError("u10_key_authorization_invalid", "generate previous")
    if item["key_operation"] in {"rotate", "revoke"} and (
        not isinstance(previous, str) or _UUID.fullmatch(previous) is None
    ):
        raise U10ProvisioningError("u10_key_authorization_invalid", "previous key")
    if item["key_operation"] == "revoke" and previous != key_id:
        raise U10ProvisioningError(
            "u10_key_authorization_invalid", "revoke must target current"
        )
    if sealed_digest(item, "authorization_digest") != _require_digest(
        item["authorization_digest"], code="u10_key_authorization_digest_invalid"
    ):
        raise U10ProvisioningError(
            "u10_key_authorization_seal_mismatch", item["authorization_id"]
        )
    recorded = _parse_time(
        item["recorded_at"], code="u10_key_authorization_time_invalid"
    )
    not_before = _parse_time(
        item["not_before"], code="u10_key_authorization_time_invalid"
    )
    expires = _parse_time(item["expires_at"], code="u10_key_authorization_time_invalid")
    decision_time = effective_at or datetime.now(timezone.utc)
    if not (recorded <= not_before <= decision_time <= expires):
        raise U10ProvisioningError(
            "u10_key_authorization_time_invalid", str(decision_time)
        )
    return item


def validate_key_consumption(
    value: Mapping[str, Any],
    *,
    authorization: Mapping[str, Any],
) -> dict[str, Any]:
    item = _require_exact_keys(
        value,
        {
            "authorization_ref",
            "consumption_digest",
            "consumption_id",
            "formal_authority",
            "key_id",
            "key_operation",
            "occurrence_id",
            "positive_assurance_allowed",
            "publication_occurred",
            "publisher_contract_binding",
            "record_kind",
            "reserved_at",
            "schema_version",
        },
        code="u10_key_consumption_shape_invalid",
    )
    authorization_id = str(authorization["authorization_id"])
    authorization_ref = _require_exact_keys(
        item["authorization_ref"],
        {"artifact_digest", "authorization_digest", "authorization_id"},
        code="u10_key_consumption_authorization_ref_invalid",
    )
    _require_digest(
        authorization_ref["artifact_digest"],
        code="u10_key_consumption_authorization_ref_invalid",
    )
    _validate_publisher_contract_binding(item["publisher_contract_binding"])
    reserved_at = _parse_time(
        item["reserved_at"], code="u10_key_consumption_time_invalid"
    )
    if (
        item["schema_version"] != KEY_CONSUMPTION_SCHEMA_V1
        or item["consumption_id"] != f"consumption.{authorization_id}"
        or item["record_kind"] != "key_operation_authorization_consumption"
        or authorization_ref["authorization_id"] != authorization_id
        or authorization_ref["authorization_digest"]
        != authorization["authorization_digest"]
        or item["key_operation"] != authorization["key_operation"]
        or item["key_id"] != authorization["key_id"]
        or item["occurrence_id"]
        != f"key.{authorization['authorization_digest']['value']}"
        or reserved_at
        < _parse_time(
            authorization["recorded_at"],
            code="u10_key_authorization_time_invalid",
        )
        or item["publication_occurred"] is not False
        or item["formal_authority"] != "none"
        or item["positive_assurance_allowed"] is not False
        or sealed_digest(item, "consumption_digest")
        != _require_digest(
            item["consumption_digest"],
            code="u10_key_consumption_digest_invalid",
        )
    ):
        raise U10ProvisioningError("u10_key_consumption_invalid", authorization_id)
    return item


def validate_key_receipt(
    value: Mapping[str, Any], *, paths: KeyPaths = KeyPaths()
) -> dict[str, Any]:
    item = _require_exact_keys(
        value,
        {
            "authorization_ref",
            "consumption_ref",
            "formal_authority",
            "generation_evidence_selector",
            "human_adoption_status",
            "key_id",
            "key_operation",
            "key_state",
            "occurrence_id",
            "positive_assurance_allowed",
            "private_material_evidence",
            "publication_not_before",
            "publication_observed_at",
            "publication_occurred",
            "public_metadata_ref",
            "publisher_contract_binding",
            "receipt_digest",
            "receipt_id",
            "receipt_recorded_at",
            "record_kind",
            "schema_version",
            "u4_principal_authenticity",
        },
        code="u10_key_receipt_shape_invalid",
    )
    authorization_ref = _require_exact_keys(
        item["authorization_ref"],
        {"authorization_digest", "authorization_id"},
        code="u10_key_receipt_authorization_ref_invalid",
    )
    authorization_id = _require_id(
        authorization_ref["authorization_id"],
        code="u10_key_receipt_authorization_ref_invalid",
    )
    _require_digest(
        authorization_ref["authorization_digest"],
        code="u10_key_receipt_authorization_ref_invalid",
    )
    consumption_ref = _require_exact_keys(
        item["consumption_ref"],
        {"consumption_digest", "consumption_id"},
        code="u10_key_receipt_consumption_ref_invalid",
    )
    _require_digest(
        consumption_ref["consumption_digest"],
        code="u10_key_receipt_consumption_ref_invalid",
    )
    _validate_publisher_contract_binding(item["publisher_contract_binding"])
    publication_not_before = _parse_time(
        item["publication_not_before"], code="u10_key_receipt_time_invalid"
    )
    publication_observed_at = _parse_time(
        item["publication_observed_at"], code="u10_key_receipt_time_invalid"
    )
    receipt_recorded_at = _parse_time(
        item["receipt_recorded_at"], code="u10_key_receipt_time_invalid"
    )
    if (
        item["schema_version"] != KEY_RECEIPT_SCHEMA_V1
        or item["receipt_id"] != f"receipt.{authorization_id}"
        or item["record_kind"] != "signing_key_operation_occurrence"
        or item["occurrence_id"]
        != f"key.{authorization_ref['authorization_digest']['value']}"
        or consumption_ref["consumption_id"] != f"consumption.{authorization_id}"
        or item["key_operation"] not in {"generate", "rotate", "revoke"}
        or _UUID.fullmatch(str(item["key_id"])) is None
        or not (
            publication_not_before <= publication_observed_at <= receipt_recorded_at
        )
        or item["publication_occurred"] is not True
        or item["human_adoption_status"] != "pending"
        or item["u4_principal_authenticity"] != "unresolved"
        or item["formal_authority"] != "none"
        or item["positive_assurance_allowed"] is not False
        or sealed_digest(item, "receipt_digest")
        != _require_digest(
            item["receipt_digest"], code="u10_key_receipt_digest_invalid"
        )
    ):
        raise U10ProvisioningError("u10_key_receipt_invalid", authorization_id)
    if item["key_operation"] in {"generate", "rotate"}:
        public_ref = _validate_public_metadata_ref(
            item["public_metadata_ref"], metadata=None, paths=paths
        )
        if (
            item["generation_evidence_selector"]
            != _generation_evidence_selector(authorization_id, paths)
            or public_ref["key_id"] != item["key_id"]
            or public_ref["generation_authorization_ref"] != authorization_ref
            or item["private_material_evidence"]
            != "root_owned_0600_present_not_disclosed"
            or item["key_state"] != "active"
        ):
            raise U10ProvisioningError(
                "u10_key_receipt_context_mismatch", authorization_id
            )
    elif (
        item["public_metadata_ref"] is not None
        or item["generation_evidence_selector"] is not None
        or item["private_material_evidence"] != "unchanged_not_disclosed"
        or item["key_state"] != "revoked_no_active_key"
    ):
        raise U10ProvisioningError("u10_key_receipt_context_mismatch", authorization_id)
    return item


def _validate_authorization_ref_v2(
    value: Any, *, paths: KeyPaths, code: str
) -> dict[str, Any]:
    item = _require_exact_keys(
        value,
        {
            "artifact_digest",
            "authorization_digest",
            "authorization_id",
            "locator",
        },
        code=code,
    )
    authorization_id = _require_id(item["authorization_id"], code=code)
    if item["locator"] != str(
        paths.ledger_root / f"{authorization_id}.authorization.json"
    ):
        raise U10ProvisioningError(code, "authorization locator")
    _require_digest(item["artifact_digest"], code=code)
    _require_digest(item["authorization_digest"], code=code)
    return item


def _validate_consumption_ref_v2(
    value: Any, *, paths: KeyPaths, code: str
) -> dict[str, Any]:
    item = _require_exact_keys(
        value,
        {
            "artifact_digest",
            "consumption_digest",
            "consumption_id",
            "locator",
        },
        code=code,
    )
    consumption_id = _require_id(item["consumption_id"], code=code)
    if not consumption_id.startswith("consumption."):
        raise U10ProvisioningError(code, "consumption id")
    authorization_id = consumption_id.removeprefix("consumption.")
    if item["locator"] != str(
        paths.ledger_root / f"{authorization_id}.consumption.json"
    ):
        raise U10ProvisioningError(code, "consumption locator")
    _require_digest(item["artifact_digest"], code=code)
    _require_digest(item["consumption_digest"], code=code)
    return item


def _authorization_ref_v2(
    authorization: Mapping[str, Any], raw: bytes, *, paths: KeyPaths
) -> dict[str, Any]:
    authorization_id = str(authorization["authorization_id"])
    return {
        "authorization_id": authorization_id,
        "locator": str(paths.ledger_root / f"{authorization_id}.authorization.json"),
        "artifact_digest": digest_bytes(raw),
        "authorization_digest": authorization["authorization_digest"],
    }


def _consumption_ref_v2(
    consumption: Mapping[str, Any], raw: bytes, *, paths: KeyPaths
) -> dict[str, Any]:
    authorization_id = str(consumption["authorization_ref"]["authorization_id"])
    return {
        "consumption_id": consumption["consumption_id"],
        "locator": str(paths.ledger_root / f"{authorization_id}.consumption.json"),
        "artifact_digest": digest_bytes(raw),
        "consumption_digest": consumption["consumption_digest"],
    }


def _validate_selector_ref_v2(
    value: Any,
    *,
    paths: KeyPaths,
    code: str,
) -> dict[str, Any]:
    item = _require_exact_keys(
        value,
        {"artifact_digest", "locator", "selector_digest", "selector_id"},
        code=code,
    )
    _require_id(item["selector_id"], code=code)
    artifact_digest = _require_digest(item["artifact_digest"], code=code)
    _require_digest(item["selector_digest"], code=code)
    expected = paths.selector_history_root / (f"{artifact_digest['value']}.json")
    if item["locator"] != str(expected):
        raise U10ProvisioningError(code, "selector history locator")
    return item


def _validate_optional_selector_ref_v2(
    value: Any, *, paths: KeyPaths, code: str
) -> dict[str, Any] | None:
    if value is None:
        return None
    return _validate_selector_ref_v2(value, paths=paths, code=code)


def _validate_transition_evidence_selector_v2(
    value: Any, *, paths: KeyPaths, code: str
) -> dict[str, Any]:
    item = _require_exact_keys(
        value,
        {
            "authorization_ref",
            "consumption_ref",
            "ledger_root",
            "prior_selector_ref",
            "receipt_locator",
            "resolution_policy",
        },
        code=code,
    )
    authorization_ref = _validate_authorization_ref_v2(
        item["authorization_ref"], paths=paths, code=code
    )
    consumption_ref = _validate_consumption_ref_v2(
        item["consumption_ref"], paths=paths, code=code
    )
    _validate_optional_selector_ref_v2(
        item["prior_selector_ref"], paths=paths, code=code
    )
    authorization_id = authorization_ref["authorization_id"]
    if (
        item["ledger_root"] != str(paths.ledger_root)
        or consumption_ref["consumption_id"] != f"consumption.{authorization_id}"
        or item["receipt_locator"]
        != str(paths.ledger_root / f"{authorization_id}.receipt.json")
        or item["resolution_policy"] != "resolve_exact_key_transition_chain/v2"
    ):
        raise U10ProvisioningError(code, "transition evidence selector")
    return item


def validate_key_authorization_v2(
    value: Mapping[str, Any],
    *,
    paths: KeyPaths = KeyPaths(),
    effective_at: datetime | None = None,
) -> dict[str, Any]:
    item = _require_exact_keys(
        value,
        {
            "authorization_digest",
            "authorization_id",
            "authorization_version",
            "authorized_algorithm",
            "authorized_operation",
            "authority_scope",
            "decision_owner",
            "expected_current_key_id",
            "expires_at",
            "formal_authority",
            "human_decision",
            "key_entity_ref",
            "key_id",
            "key_operation",
            "not_before",
            "positive_assurance_allowed",
            "prior_selector_ref",
            "record_kind",
            "recorded_at",
            "schema_version",
            "target_generation_path",
            "target_private_key_path",
            "target_public_metadata_path",
            "transition_mode",
            "u4_principal_authenticity",
        },
        code="u10_key_authorization_v2_shape_invalid",
    )
    authorization_id = _require_id(
        item["authorization_id"], code="u10_key_authorization_id_invalid"
    )
    key_id = str(item["key_id"])
    entity_ref = _require_entity_ref(
        item["key_entity_ref"], code="u10_key_entity_ref_invalid"
    )
    prior_ref = _validate_optional_selector_ref_v2(
        item["prior_selector_ref"],
        paths=paths,
        code="u10_key_authorization_prior_selector_invalid",
    )
    operation = item["key_operation"]
    mode = item["transition_mode"]
    allowed_mode = {
        "rotate": "rotate_active_key",
        "revoke": "revoke_active_key",
    }.get(operation)
    if operation == "generate":
        allowed_modes = (
            {"initialize_empty_store"}
            if prior_ref is None
            else {"generate_from_no_active_key"}
        )
    else:
        allowed_modes = {allowed_mode}
    previous = item["expected_current_key_id"]
    if (
        item["schema_version"] != KEY_AUTH_SCHEMA
        or item["authorization_version"] != "2.0.0"
        or item["record_kind"] != "signing_key_operation_authorization"
        or operation not in {"generate", "rotate", "revoke"}
        or mode not in allowed_modes
        or _UUID.fullmatch(key_id) is None
        or entity_ref.rsplit("・", 1)[-1] != key_id
        or item["target_generation_path"] != str(paths.generation_root / key_id)
        or item["target_public_metadata_path"]
        != str(paths.generation_root / key_id / "public-metadata.json")
        or item["target_private_key_path"]
        != str(paths.generation_root / key_id / "private.ed25519")
        or item["authorized_algorithm"] != "Ed25519"
        or item["authorized_operation"] != "apply_exact_key_lifecycle_transition_v2"
        or item["human_decision"] != "accept"
        or item["decision_owner"] != "human"
        or item["u4_principal_authenticity"] != "unresolved"
        or item["authority_scope"] != "u10_signing_key_transition_only"
        or item["formal_authority"] != "human_key_transition_decision_only"
        or item["positive_assurance_allowed"] is not False
    ):
        raise U10ProvisioningError("u10_key_authorization_v2_invalid", "fixed fields")
    if operation == "generate" and previous is not None:
        raise U10ProvisioningError(
            "u10_key_authorization_v2_invalid", "generate previous key"
        )
    if operation in {"rotate", "revoke"} and (
        not isinstance(previous, str) or _UUID.fullmatch(previous) is None
    ):
        raise U10ProvisioningError(
            "u10_key_authorization_v2_invalid", "active previous key"
        )
    if operation == "revoke" and previous != key_id:
        raise U10ProvisioningError("u10_key_authorization_v2_invalid", "revoke target")
    if operation == "rotate" and previous == key_id:
        raise U10ProvisioningError(
            "u10_key_authorization_v2_invalid", "rotation must change key"
        )
    if sealed_digest(item, "authorization_digest") != _require_digest(
        item["authorization_digest"],
        code="u10_key_authorization_digest_invalid",
    ):
        raise U10ProvisioningError(
            "u10_key_authorization_seal_mismatch", authorization_id
        )
    recorded = _parse_time(
        item["recorded_at"], code="u10_key_authorization_time_invalid"
    )
    not_before = _parse_time(
        item["not_before"], code="u10_key_authorization_time_invalid"
    )
    expires = _parse_time(item["expires_at"], code="u10_key_authorization_time_invalid")
    decision_time = effective_at or datetime.now(timezone.utc)
    if not (recorded <= not_before <= decision_time <= expires):
        raise U10ProvisioningError(
            "u10_key_authorization_time_invalid", str(decision_time)
        )
    return item


def validate_key_consumption_v2(
    value: Mapping[str, Any],
    *,
    authorization: Mapping[str, Any],
    authorization_raw: bytes,
    paths: KeyPaths = KeyPaths(),
) -> dict[str, Any]:
    item = _require_exact_keys(
        value,
        {
            "authorization_ref",
            "consumption_digest",
            "consumption_id",
            "formal_authority",
            "key_id",
            "key_operation",
            "occurrence_id",
            "positive_assurance_allowed",
            "prior_selector_ref",
            "publication_occurred",
            "publisher_contract_binding",
            "record_kind",
            "reserved_at",
            "schema_version",
            "transition_mode",
        },
        code="u10_key_consumption_v2_shape_invalid",
    )
    authorization_id = str(authorization["authorization_id"])
    auth_ref = _validate_authorization_ref_v2(
        item["authorization_ref"],
        paths=paths,
        code="u10_key_consumption_authorization_ref_invalid",
    )
    prior_ref = _validate_optional_selector_ref_v2(
        item["prior_selector_ref"],
        paths=paths,
        code="u10_key_consumption_prior_selector_invalid",
    )
    _validate_publisher_contract_binding(item["publisher_contract_binding"])
    reserved = _parse_time(item["reserved_at"], code="u10_key_consumption_time_invalid")
    if (
        item["schema_version"] != KEY_CONSUMPTION_SCHEMA
        or item["consumption_id"] != f"consumption.{authorization_id}"
        or item["record_kind"] != "key_operation_authorization_consumption"
        or auth_ref["authorization_id"] != authorization_id
        or auth_ref["authorization_digest"] != authorization["authorization_digest"]
        or auth_ref["artifact_digest"] != digest_bytes(authorization_raw)
        or item["key_operation"] != authorization["key_operation"]
        or item["transition_mode"] != authorization["transition_mode"]
        or item["key_id"] != authorization["key_id"]
        or item["occurrence_id"]
        != f"key.{authorization['authorization_digest']['value']}"
        or prior_ref != authorization["prior_selector_ref"]
        or reserved
        < _parse_time(
            authorization["recorded_at"],
            code="u10_key_authorization_time_invalid",
        )
        or item["publication_occurred"] is not False
        or item["formal_authority"] != "none"
        or item["positive_assurance_allowed"] is not False
        or sealed_digest(item, "consumption_digest")
        != _require_digest(
            item["consumption_digest"],
            code="u10_key_consumption_digest_invalid",
        )
    ):
        raise U10ProvisioningError("u10_key_consumption_v2_invalid", authorization_id)
    return item


def _transition_evidence_selector_v2(
    *,
    authorization_ref: Mapping[str, Any],
    consumption_ref: Mapping[str, Any],
    prior_selector_ref: Mapping[str, Any] | None,
    paths: KeyPaths,
) -> dict[str, Any]:
    authorization_id = str(authorization_ref["authorization_id"])
    return {
        "ledger_root": str(paths.ledger_root),
        "authorization_ref": dict(authorization_ref),
        "consumption_ref": dict(consumption_ref),
        "prior_selector_ref": (
            None if prior_selector_ref is None else dict(prior_selector_ref)
        ),
        "receipt_locator": str(paths.ledger_root / f"{authorization_id}.receipt.json"),
        "resolution_policy": "resolve_exact_key_transition_chain/v2",
    }


def validate_key_public_metadata_v2(
    value: Mapping[str, Any], *, paths: KeyPaths = KeyPaths()
) -> dict[str, Any]:
    item = _require_exact_keys(
        value,
        {
            "algorithm",
            "authorization_ref",
            "consumption_ref",
            "created_at",
            "formal_authority",
            "key_entity_ref",
            "key_id",
            "metadata_digest",
            "positive_assurance_allowed",
            "prior_selector_ref",
            "private_material",
            "public_key",
            "record_kind",
            "schema_version",
            "transition_evidence_selector",
        },
        code="u10_key_metadata_v2_shape_invalid",
    )
    key_id = str(item["key_id"])
    entity_ref = _require_entity_ref(
        item["key_entity_ref"], code="u10_key_metadata_entity_ref_invalid"
    )
    auth_ref = _validate_authorization_ref_v2(
        item["authorization_ref"],
        paths=paths,
        code="u10_key_metadata_authorization_ref_invalid",
    )
    consumption_ref = _validate_consumption_ref_v2(
        item["consumption_ref"],
        paths=paths,
        code="u10_key_metadata_consumption_ref_invalid",
    )
    prior_ref = _validate_optional_selector_ref_v2(
        item["prior_selector_ref"],
        paths=paths,
        code="u10_key_metadata_prior_selector_invalid",
    )
    evidence = _validate_transition_evidence_selector_v2(
        item["transition_evidence_selector"],
        paths=paths,
        code="u10_key_metadata_evidence_selector_invalid",
    )
    public_key = _require_exact_keys(
        item["public_key"],
        {"encoding", "value"},
        code="u10_key_public_material_invalid",
    )
    try:
        public_raw = base64.b64decode(public_key["value"], validate=True)
    except (TypeError, ValueError) as exc:
        raise U10ProvisioningError("u10_key_public_material_invalid", "base64") from exc
    private = _require_exact_keys(
        item["private_material"],
        {"locator", "storage_state"},
        code="u10_key_private_material_ref_invalid",
    )
    if (
        item["schema_version"] != KEY_METADATA_SCHEMA
        or item["record_kind"] != "signing_key_public_metadata"
        or item["algorithm"] != "Ed25519"
        or _UUID.fullmatch(key_id) is None
        or entity_ref.rsplit("・", 1)[-1] != key_id
        or public_key["encoding"] != "raw_base64"
        or len(public_raw) != 32
        or private["locator"] != str(paths.generation_root / key_id / "private.ed25519")
        or private["storage_state"] != "root_only_0600_not_exported"
        or consumption_ref["consumption_id"]
        != f"consumption.{auth_ref['authorization_id']}"
        or evidence["authorization_ref"] != auth_ref
        or evidence["consumption_ref"] != consumption_ref
        or evidence["prior_selector_ref"] != prior_ref
        or item["formal_authority"] != "none"
        or item["positive_assurance_allowed"] is not False
        or sealed_digest(item, "metadata_digest")
        != _require_digest(
            item["metadata_digest"], code="u10_key_metadata_digest_invalid"
        )
    ):
        raise U10ProvisioningError(
            "u10_key_metadata_v2_invalid", "fixed fields or seal"
        )
    _parse_time(item["created_at"], code="u10_key_metadata_time_invalid")
    return item


def _public_metadata_ref_v2(
    metadata: Mapping[str, Any], raw: bytes, *, paths: KeyPaths
) -> dict[str, Any]:
    return {
        "key_id": metadata["key_id"],
        "key_entity_ref": metadata["key_entity_ref"],
        "locator": str(
            paths.generation_root / str(metadata["key_id"]) / "public-metadata.json"
        ),
        "artifact_digest": digest_bytes(raw),
        "metadata_digest": metadata["metadata_digest"],
        "generation_authorization_ref": metadata["authorization_ref"],
        "generation_consumption_ref": metadata["consumption_ref"],
    }


def _validate_public_metadata_ref_v2(
    value: Any,
    *,
    metadata: Mapping[str, Any] | None,
    metadata_raw: bytes | None,
    paths: KeyPaths,
) -> dict[str, Any]:
    item = _require_exact_keys(
        value,
        {
            "artifact_digest",
            "generation_authorization_ref",
            "generation_consumption_ref",
            "key_entity_ref",
            "key_id",
            "locator",
            "metadata_digest",
        },
        code="u10_key_public_metadata_ref_v2_invalid",
    )
    key_id = str(item["key_id"])
    _require_entity_ref(
        item["key_entity_ref"], code="u10_key_public_metadata_ref_v2_invalid"
    )
    _validate_authorization_ref_v2(
        item["generation_authorization_ref"],
        paths=paths,
        code="u10_key_public_metadata_ref_v2_invalid",
    )
    _validate_consumption_ref_v2(
        item["generation_consumption_ref"],
        paths=paths,
        code="u10_key_public_metadata_ref_v2_invalid",
    )
    _require_digest(
        item["artifact_digest"], code="u10_key_public_metadata_ref_v2_invalid"
    )
    _require_digest(
        item["metadata_digest"], code="u10_key_public_metadata_ref_v2_invalid"
    )
    if (
        _UUID.fullmatch(key_id) is None
        or item["key_entity_ref"].rsplit("・", 1)[-1] != key_id
        or item["locator"]
        != str(paths.generation_root / key_id / "public-metadata.json")
    ):
        raise U10ProvisioningError(
            "u10_key_public_metadata_ref_v2_invalid", "fixed fields"
        )
    if metadata is not None:
        if metadata_raw is None or item != _public_metadata_ref_v2(
            metadata, metadata_raw, paths=paths
        ):
            raise U10ProvisioningError(
                "u10_key_public_metadata_ref_v2_mismatch", key_id
            )
    return item


def validate_key_revocation_v2(
    value: Mapping[str, Any], *, paths: KeyPaths = KeyPaths()
) -> dict[str, Any]:
    item = _require_exact_keys(
        value,
        {
            "authorization_ref",
            "consumption_ref",
            "formal_authority",
            "key_entity_ref",
            "key_id",
            "positive_assurance_allowed",
            "prior_selector_ref",
            "private_material_disposition",
            "record_kind",
            "revocation_digest",
            "revocation_id",
            "revoked_at",
            "schema_version",
            "transition_evidence_selector",
        },
        code="u10_key_revocation_v2_shape_invalid",
    )
    auth_ref = _validate_authorization_ref_v2(
        item["authorization_ref"],
        paths=paths,
        code="u10_key_revocation_authorization_ref_invalid",
    )
    consumption_ref = _validate_consumption_ref_v2(
        item["consumption_ref"],
        paths=paths,
        code="u10_key_revocation_consumption_ref_invalid",
    )
    prior_ref = _validate_optional_selector_ref_v2(
        item["prior_selector_ref"],
        paths=paths,
        code="u10_key_revocation_prior_selector_invalid",
    )
    evidence = _validate_transition_evidence_selector_v2(
        item["transition_evidence_selector"],
        paths=paths,
        code="u10_key_revocation_evidence_selector_invalid",
    )
    authorization_id = auth_ref["authorization_id"]
    key_id = str(item["key_id"])
    entity_ref = _require_entity_ref(
        item["key_entity_ref"], code="u10_key_revocation_entity_ref_invalid"
    )
    if (
        item["schema_version"] != KEY_REVOCATION_SCHEMA
        or item["revocation_id"] != f"revocation.{authorization_id}"
        or item["record_kind"] != "signing_key_revocation_occurrence"
        or _UUID.fullmatch(key_id) is None
        or entity_ref.rsplit("・", 1)[-1] != key_id
        or consumption_ref["consumption_id"] != f"consumption.{authorization_id}"
        or evidence["authorization_ref"] != auth_ref
        or evidence["consumption_ref"] != consumption_ref
        or evidence["prior_selector_ref"] != prior_ref
        or item["private_material_disposition"]
        != "retained_root_only_not_exported_pending_retention_policy"
        or item["formal_authority"] != "none"
        or item["positive_assurance_allowed"] is not False
        or sealed_digest(item, "revocation_digest")
        != _require_digest(
            item["revocation_digest"],
            code="u10_key_revocation_digest_invalid",
        )
    ):
        raise U10ProvisioningError("u10_key_revocation_v2_invalid", authorization_id)
    _parse_time(item["revoked_at"], code="u10_key_revocation_time_invalid")
    return item


def _revocation_ref_v2(
    revocation: Mapping[str, Any], raw: bytes, *, paths: KeyPaths
) -> dict[str, Any]:
    authorization_id = revocation["authorization_ref"]["authorization_id"]
    key_id = str(revocation["key_id"])
    return {
        "revocation_id": revocation["revocation_id"],
        "key_id": key_id,
        "locator": str(paths.revocation_root / key_id / f"{authorization_id}.json"),
        "artifact_digest": digest_bytes(raw),
        "revocation_digest": revocation["revocation_digest"],
    }


def _validate_revocation_ref_v2(
    value: Any,
    *,
    revocation: Mapping[str, Any] | None,
    revocation_raw: bytes | None,
    paths: KeyPaths,
) -> dict[str, Any]:
    item = _require_exact_keys(
        value,
        {
            "artifact_digest",
            "key_id",
            "locator",
            "revocation_digest",
            "revocation_id",
        },
        code="u10_key_revocation_ref_v2_invalid",
    )
    revocation_id = _require_id(
        item["revocation_id"], code="u10_key_revocation_ref_v2_invalid"
    )
    key_id = str(item["key_id"])
    if not revocation_id.startswith("revocation."):
        raise U10ProvisioningError("u10_key_revocation_ref_v2_invalid", "revocation id")
    authorization_id = revocation_id.removeprefix("revocation.")
    if _UUID.fullmatch(key_id) is None or item["locator"] != str(
        paths.revocation_root / key_id / f"{authorization_id}.json"
    ):
        raise U10ProvisioningError(
            "u10_key_revocation_ref_v2_invalid", "key id or locator"
        )
    _require_digest(item["artifact_digest"], code="u10_key_revocation_ref_v2_invalid")
    _require_digest(item["revocation_digest"], code="u10_key_revocation_ref_v2_invalid")
    if revocation is not None:
        if revocation_raw is None or item != _revocation_ref_v2(
            revocation, revocation_raw, paths=paths
        ):
            raise U10ProvisioningError("u10_key_revocation_ref_v2_mismatch", key_id)
    return item


def validate_key_selector_v2(
    value: Mapping[str, Any], *, paths: KeyPaths = KeyPaths()
) -> dict[str, Any]:
    item = _require_exact_keys(
        value,
        {
            "formal_authority",
            "key_entity_ref",
            "key_id",
            "positive_assurance_allowed",
            "previous_selector_ref",
            "public_metadata_ref",
            "record_kind",
            "revocation_ref",
            "schema_version",
            "selected_at",
            "selector_digest",
            "selector_id",
            "state",
            "transition_evidence_selector",
            "transition_mode",
        },
        code="u10_key_selector_v2_shape_invalid",
    )
    previous_ref = _validate_optional_selector_ref_v2(
        item["previous_selector_ref"],
        paths=paths,
        code="u10_key_selector_previous_ref_invalid",
    )
    evidence = _validate_transition_evidence_selector_v2(
        item["transition_evidence_selector"],
        paths=paths,
        code="u10_key_selector_evidence_invalid",
    )
    authorization_id = evidence["authorization_ref"]["authorization_id"]
    if (
        item["schema_version"] != KEY_SELECTOR_SCHEMA
        or item["selector_id"] != f"selector.{authorization_id}"
        or item["record_kind"] != "current_signing_key_selector"
        or item["state"] not in {"active", "no_active_key"}
        or item["transition_mode"]
        not in {
            "initialize_empty_store",
            "generate_from_no_active_key",
            "rotate_active_key",
            "revoke_active_key",
        }
        or (
            item["transition_mode"] == "initialize_empty_store"
            and previous_ref is not None
        )
        or (
            item["transition_mode"] != "initialize_empty_store" and previous_ref is None
        )
        or evidence["prior_selector_ref"] != previous_ref
        or item["formal_authority"] != "none"
        or item["positive_assurance_allowed"] is not False
        or sealed_digest(item, "selector_digest")
        != _require_digest(
            item["selector_digest"], code="u10_key_selector_digest_invalid"
        )
    ):
        raise U10ProvisioningError(
            "u10_key_selector_v2_invalid", "fixed fields or seal"
        )
    _parse_time(item["selected_at"], code="u10_key_selector_time_invalid")
    if item["state"] == "active":
        public_ref = _validate_public_metadata_ref_v2(
            item["public_metadata_ref"],
            metadata=None,
            metadata_raw=None,
            paths=paths,
        )
        if (
            item["key_id"] != public_ref["key_id"]
            or item["key_entity_ref"] != public_ref["key_entity_ref"]
            or item["revocation_ref"] is not None
            or item["transition_mode"] == "revoke_active_key"
        ):
            raise U10ProvisioningError(
                "u10_key_selector_v2_context_mismatch", authorization_id
            )
    else:
        revocation_ref = _validate_revocation_ref_v2(
            item["revocation_ref"],
            revocation=None,
            revocation_raw=None,
            paths=paths,
        )
        if (
            any(
                item[field] is not None
                for field in ("key_id", "key_entity_ref", "public_metadata_ref")
            )
            or item["transition_mode"] != "revoke_active_key"
            or revocation_ref["revocation_id"] != f"revocation.{authorization_id}"
        ):
            raise U10ProvisioningError(
                "u10_key_selector_v2_context_mismatch", authorization_id
            )
    return item


def _selector_ref_v2(
    selector: Mapping[str, Any], raw: bytes, *, paths: KeyPaths
) -> dict[str, Any]:
    artifact_digest = digest_bytes(raw)
    return {
        "selector_id": selector["selector_id"],
        "locator": str(
            paths.selector_history_root / f"{artifact_digest['value']}.json"
        ),
        "artifact_digest": artifact_digest,
        "selector_digest": selector["selector_digest"],
    }


def validate_key_receipt_v2(
    value: Mapping[str, Any], *, paths: KeyPaths = KeyPaths()
) -> dict[str, Any]:
    item = _require_exact_keys(
        value,
        {
            "authorization_ref",
            "consumption_ref",
            "formal_authority",
            "human_adoption_status",
            "key_id",
            "key_operation",
            "key_state",
            "occurrence_id",
            "positive_assurance_allowed",
            "prior_selector_ref",
            "private_material_evidence",
            "publication_not_before",
            "publication_observed_at",
            "publication_occurred",
            "public_metadata_ref",
            "published_selector_ref",
            "publisher_contract_binding",
            "receipt_digest",
            "receipt_id",
            "receipt_recorded_at",
            "record_kind",
            "revocation_ref",
            "schema_version",
            "transition_mode",
            "u4_principal_authenticity",
        },
        code="u10_key_receipt_v2_shape_invalid",
    )
    auth_ref = _validate_authorization_ref_v2(
        item["authorization_ref"],
        paths=paths,
        code="u10_key_receipt_authorization_ref_invalid",
    )
    consumption_ref = _validate_consumption_ref_v2(
        item["consumption_ref"],
        paths=paths,
        code="u10_key_receipt_consumption_ref_invalid",
    )
    prior_ref = _validate_optional_selector_ref_v2(
        item["prior_selector_ref"],
        paths=paths,
        code="u10_key_receipt_prior_selector_ref_invalid",
    )
    _validate_selector_ref_v2(
        item["published_selector_ref"],
        paths=paths,
        code="u10_key_receipt_published_selector_ref_invalid",
    )
    _validate_publisher_contract_binding(item["publisher_contract_binding"])
    authorization_id = auth_ref["authorization_id"]
    not_before = _parse_time(
        item["publication_not_before"], code="u10_key_receipt_time_invalid"
    )
    observed = _parse_time(
        item["publication_observed_at"], code="u10_key_receipt_time_invalid"
    )
    recorded = _parse_time(
        item["receipt_recorded_at"], code="u10_key_receipt_time_invalid"
    )
    if (
        item["schema_version"] != KEY_RECEIPT_SCHEMA
        or item["receipt_id"] != f"receipt.{authorization_id}"
        or item["record_kind"] != "signing_key_operation_occurrence"
        or item["occurrence_id"] != f"key.{auth_ref['authorization_digest']['value']}"
        or consumption_ref["consumption_id"] != f"consumption.{authorization_id}"
        or item["key_operation"] not in {"generate", "rotate", "revoke"}
        or item["transition_mode"]
        not in {
            "initialize_empty_store",
            "generate_from_no_active_key",
            "rotate_active_key",
            "revoke_active_key",
        }
        or (
            item["transition_mode"] == "initialize_empty_store"
            and prior_ref is not None
        )
        or (item["transition_mode"] != "initialize_empty_store" and prior_ref is None)
        or (
            item["transition_mode"]
            in {"initialize_empty_store", "generate_from_no_active_key"}
            and item["key_operation"] != "generate"
        )
        or (
            item["transition_mode"] == "rotate_active_key"
            and item["key_operation"] != "rotate"
        )
        or (
            item["transition_mode"] == "revoke_active_key"
            and item["key_operation"] != "revoke"
        )
        or _UUID.fullmatch(str(item["key_id"])) is None
        or not (not_before <= observed <= recorded)
        or item["publication_occurred"] is not True
        or item["human_adoption_status"] != "pending"
        or item["u4_principal_authenticity"] != "unresolved"
        or item["formal_authority"] != "none"
        or item["positive_assurance_allowed"] is not False
        or sealed_digest(item, "receipt_digest")
        != _require_digest(
            item["receipt_digest"], code="u10_key_receipt_digest_invalid"
        )
    ):
        raise U10ProvisioningError("u10_key_receipt_v2_invalid", authorization_id)
    if item["key_operation"] in {"generate", "rotate"}:
        public_ref = _validate_public_metadata_ref_v2(
            item["public_metadata_ref"],
            metadata=None,
            metadata_raw=None,
            paths=paths,
        )
        if (
            item["revocation_ref"] is not None
            or public_ref["key_id"] != item["key_id"]
            or public_ref["generation_authorization_ref"] != auth_ref
            or public_ref["generation_consumption_ref"] != consumption_ref
            or item["private_material_evidence"]
            != "root_owned_0600_present_not_disclosed"
            or item["key_state"] != "active"
        ):
            raise U10ProvisioningError(
                "u10_key_receipt_v2_context_mismatch", authorization_id
            )
    else:
        revocation_ref = _validate_revocation_ref_v2(
            item["revocation_ref"],
            revocation=None,
            revocation_raw=None,
            paths=paths,
        )
        if (
            item["public_metadata_ref"] is not None
            or revocation_ref["key_id"] != item["key_id"]
            or revocation_ref["revocation_id"] != f"revocation.{authorization_id}"
            or item["private_material_evidence"] != "unchanged_not_disclosed"
            or item["key_state"] != "revoked_no_active_key"
        ):
            raise U10ProvisioningError(
                "u10_key_receipt_v2_context_mismatch", authorization_id
            )
    return item


def validate_key_emergency_closure_v1(
    value: Mapping[str, Any], *, paths: KeyPaths = KeyPaths()
) -> dict[str, Any]:
    """Validate a human-authored closure; this function never creates one."""

    item = _require_exact_keys(
        value,
        {
            "authorization_ref",
            "closure_digest",
            "closure_disposition",
            "closure_id",
            "closure_reason",
            "consumption_ref",
            "decision_owner",
            "formal_authority",
            "human_decision",
            "positive_assurance_allowed",
            "prior_selector_ref",
            "published_selector_ref",
            "record_kind",
            "recorded_at",
            "schema_version",
            "transition_success_claimed",
            "u4_principal_authenticity",
        },
        code="u10_key_emergency_closure_shape_invalid",
    )
    auth_ref = _validate_authorization_ref_v2(
        item["authorization_ref"],
        paths=paths,
        code="u10_key_emergency_closure_authorization_ref_invalid",
    )
    consumption_ref = _validate_consumption_ref_v2(
        item["consumption_ref"],
        paths=paths,
        code="u10_key_emergency_closure_consumption_ref_invalid",
    )
    _validate_optional_selector_ref_v2(
        item["prior_selector_ref"],
        paths=paths,
        code="u10_key_emergency_closure_prior_ref_invalid",
    )
    if item["published_selector_ref"] is not None:
        _validate_selector_ref_v2(
            item["published_selector_ref"],
            paths=paths,
            code="u10_key_emergency_closure_published_ref_invalid",
        )
    authorization_id = auth_ref["authorization_id"]
    if (
        item["schema_version"] != KEY_EMERGENCY_CLOSURE_SCHEMA
        or item["closure_id"] != f"emergency-closure.{authorization_id}"
        or item["record_kind"] != "key_transition_emergency_closure"
        or consumption_ref["consumption_id"] != f"consumption.{authorization_id}"
        or item["closure_disposition"]
        not in {"abandoned_before_publication", "quarantined_after_publication"}
        or not isinstance(item["closure_reason"], str)
        or not item["closure_reason"].strip()
        or item["human_decision"] != "accept_emergency_closure"
        or item["decision_owner"] != "human"
        or item["u4_principal_authenticity"] != "unresolved"
        or item["formal_authority"] != "human_emergency_closure_decision_only"
        or item["positive_assurance_allowed"] is not False
        or item["transition_success_claimed"] is not False
        or sealed_digest(item, "closure_digest")
        != _require_digest(
            item["closure_digest"],
            code="u10_key_emergency_closure_digest_invalid",
        )
    ):
        raise U10ProvisioningError(
            "u10_key_emergency_closure_invalid", authorization_id
        )
    _parse_time(item["recorded_at"], code="u10_key_emergency_closure_time_invalid")
    if (
        item["closure_disposition"] == "abandoned_before_publication"
        and item["published_selector_ref"] is not None
    ) or (
        item["closure_disposition"] == "quarantined_after_publication"
        and item["published_selector_ref"] is None
    ):
        raise U10ProvisioningError(
            "u10_key_emergency_closure_context_invalid", authorization_id
        )
    return item


def _load_current_selector(paths: KeyPaths, *, uid: int) -> dict[str, Any] | None:
    if not paths.selector_path.exists() and not paths.selector_path.is_symlink():
        return None
    raw = read_protected_file(
        paths.selector_path, root=paths.key_root, uid=uid, exact_mode=0o444
    )
    try:
        value = strict_json_loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise U10ProvisioningError(
            "u10_key_selector_unreadable", str(paths.selector_path)
        ) from exc
    if not isinstance(value, dict):
        raise U10ProvisioningError("u10_key_selector_invalid", str(paths.selector_path))
    return validate_key_selector(value, paths=paths)


def _reobserve_active_selector(
    selector: Mapping[str, Any],
    *,
    paths: KeyPaths,
    uid: int,
    pending_authorization_id: str | None = None,
) -> None:
    if selector["state"] != "active":
        return
    public_ref = selector["public_metadata_ref"]
    metadata_path = Path(public_ref["metadata_locator"])
    metadata_raw = read_protected_file(
        metadata_path,
        root=paths.key_root,
        uid=uid,
        exact_mode=0o444,
    )
    try:
        metadata = validate_key_public_metadata(
            strict_json_loads(metadata_raw), paths=paths
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise U10ProvisioningError(
            "u10_key_metadata_unreadable", str(metadata_path)
        ) from exc
    _validate_public_metadata_ref(public_ref, metadata=metadata, paths=paths)
    if public_ref["metadata_artifact_digest"] != digest_bytes(metadata_raw):
        raise U10ProvisioningError(
            "u10_key_selector_metadata_mismatch", str(metadata_path)
        )
    receipt_selector = public_ref["generation_receipt_selector"]
    receipt_path = (
        Path(receipt_selector["ledger_root"]) / receipt_selector["receipt_record"]
    )
    if not receipt_path.exists() and not receipt_path.is_symlink():
        if (
            pending_authorization_id is not None
            and selector["transition_authorization_ref"]["authorization_id"]
            == pending_authorization_id
            and public_ref["generation_authorization_ref"]["authorization_id"]
            == pending_authorization_id
        ):
            _reobserve_private_matches_metadata(metadata, paths=paths, uid=uid)
            return
        raise U10ProvisioningError(
            "u10_key_generation_receipt_missing", str(receipt_path)
        )
    try:
        receipt = validate_key_receipt(
            strict_json_loads(
                read_protected_file(
                    receipt_path,
                    root=paths.ledger_root,
                    uid=uid,
                    exact_mode=0o444,
                )
            ),
            paths=paths,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise U10ProvisioningError(
            "u10_key_receipt_unreadable", str(receipt_path)
        ) from exc
    if receipt["public_metadata_ref"] != public_ref:
        raise U10ProvisioningError(
            "u10_key_selector_receipt_mismatch", str(receipt_path)
        )
    _reobserve_key_receipt(receipt, paths=paths, uid=uid)


def _publish_selector(paths: KeyPaths, selector: dict[str, Any]) -> None:
    validate_key_selector(selector, paths=paths)
    raw = json_record_bytes(selector)
    digest = digest_bytes(raw)
    history_path = paths.selector_history_root / f"{digest['value']}.json"
    _atomic_append_only(history_path, selector, mode=0o444)
    _atomic_replace(paths.selector_path, raw, mode=0o444)


def _load_cryptography() -> tuple[Any, Any, Any, Any]:
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    except ImportError as exc:
        raise U10ProvisioningError("u10_control_crypto_unavailable", str(exc)) from exc
    return (
        Ed25519PrivateKey,
        serialization.Encoding,
        serialization.PrivateFormat,
        serialization.PublicFormat,
    )


def _reobserve_private_matches_metadata(
    metadata: Mapping[str, Any], *, paths: KeyPaths, uid: int
) -> None:
    key_id = str(metadata["key_id"])
    private_raw = read_protected_file(
        paths.generation_root / key_id / "private.ed25519",
        root=paths.key_root,
        uid=uid,
        exact_mode=0o600,
    )
    if len(private_raw) != 32:
        raise U10ProvisioningError("u10_private_key_material_invalid", key_id)
    private_type, encoding, _private_format, public_format = _load_cryptography()
    derived_public_raw = (
        private_type.from_private_bytes(private_raw)
        .public_key()
        .public_bytes(encoding.Raw, public_format.Raw)
    )
    if metadata["public_key"]["value"] != base64.b64encode(derived_public_raw).decode(
        "ascii"
    ):
        raise U10ProvisioningError("u10_private_public_key_mismatch", key_id)


def _reobserve_key_receipt(
    receipt: Mapping[str, Any], *, paths: KeyPaths, uid: int
) -> None:
    validate_key_receipt(receipt, paths=paths)
    operation = receipt.get("key_operation")
    key_id = str(receipt.get("key_id", ""))
    if operation in {"generate", "rotate"}:
        generation = paths.generation_root / key_id
        _assert_directory(generation, uid=uid, exact_mode=0o555)
        metadata_raw = read_protected_file(
            generation / "public-metadata.json",
            root=paths.key_root,
            uid=uid,
            exact_mode=0o444,
        )
        try:
            metadata = strict_json_loads(metadata_raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise U10ProvisioningError("u10_key_metadata_unreadable", key_id) from exc
        metadata = validate_key_public_metadata(metadata, paths=paths)
        _reobserve_private_matches_metadata(metadata, paths=paths, uid=uid)
        public_ref = receipt["public_metadata_ref"]
        _validate_public_metadata_ref(public_ref, metadata=metadata, paths=paths)
        if public_ref["metadata_artifact_digest"] != digest_bytes(metadata_raw):
            raise U10ProvisioningError("u10_key_metadata_receipt_mismatch", key_id)
    elif operation == "revoke":
        revocation = (
            paths.revocation_root
            / key_id
            / (
                str(receipt.get("authorization_ref", {}).get("authorization_id"))
                + ".json"
            )
        )
        raw = read_protected_file(
            revocation,
            root=paths.key_root,
            uid=uid,
            exact_mode=0o444,
        )
        try:
            value = strict_json_loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise U10ProvisioningError("u10_key_revocation_unreadable", key_id) from exc
        if value["key_id"] != key_id:
            raise U10ProvisioningError("u10_key_revocation_invalid", key_id)
    else:
        raise U10ProvisioningError("u10_key_receipt_operation_invalid", str(operation))


def _read_json_record_v2(
    path: Path,
    *,
    root: Path,
    uid: int,
    mode: int,
    code: str,
) -> tuple[dict[str, Any], bytes]:
    raw = read_protected_file(path, root=root, uid=uid, exact_mode=mode)
    try:
        value = strict_json_loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise U10ProvisioningError(code, str(path)) from exc
    if not isinstance(value, dict) or raw != json_record_bytes(value):
        raise U10ProvisioningError(code, f"non-canonical: {path}")
    return value, raw


def _read_selector_ref_v2(
    reference: Mapping[str, Any],
    *,
    paths: KeyPaths,
    uid: int,
) -> tuple[dict[str, Any], bytes, dict[str, Any]]:
    ref = _validate_selector_ref_v2(
        reference, paths=paths, code="u10_key_selector_ref_invalid"
    )
    value, raw = _read_json_record_v2(
        Path(ref["locator"]),
        root=paths.key_root,
        uid=uid,
        mode=0o444,
        code="u10_key_selector_history_unreadable",
    )
    selector = validate_key_selector_v2(value, paths=paths)
    observed_ref = _selector_ref_v2(selector, raw, paths=paths)
    if observed_ref != ref:
        raise U10ProvisioningError(
            "u10_key_selector_history_ref_mismatch", str(ref["locator"])
        )
    return selector, raw, observed_ref


def _load_current_selector_v2(
    paths: KeyPaths, *, uid: int
) -> tuple[dict[str, Any], bytes, dict[str, Any]] | None:
    if not paths.selector_path.exists() and not paths.selector_path.is_symlink():
        return None
    value, raw = _read_json_record_v2(
        paths.selector_path,
        root=paths.key_root,
        uid=uid,
        mode=0o444,
        code="u10_key_selector_unreadable",
    )
    if value.get("schema_version") != KEY_SELECTOR_SCHEMA:
        raise U10ProvisioningError(
            "u10_key_legacy_selector_requires_explicit_migration",
            str(value.get("schema_version")),
        )
    selector = validate_key_selector_v2(value, paths=paths)
    reference = _selector_ref_v2(selector, raw, paths=paths)
    _history_selector, history_raw, _history_ref = _read_selector_ref_v2(
        reference, paths=paths, uid=uid
    )
    if history_raw != raw:
        raise U10ProvisioningError(
            "u10_key_current_selector_history_mismatch",
            str(paths.selector_path),
        )
    return selector, raw, reference


def _scan_selector_history_denominator_v2(
    paths: KeyPaths, *, uid: int
) -> tuple[
    dict[str, tuple[dict[str, Any], bytes, dict[str, Any]]],
    dict[str, tuple[dict[str, Any], bytes, Path]],
]:
    """Classify and validate every selector-history record.

    A genuine v1 selector remains read-only evidence.  Merely claiming the v1
    schema is not enough to leave the current denominator: its shape, seal,
    references, identifier, and content-addressed filename are all checked.
    """

    result: dict[str, tuple[dict[str, Any], bytes, dict[str, Any]]] = {}
    legacy: dict[str, tuple[dict[str, Any], bytes, Path]] = {}
    for path in sorted(paths.selector_history_root.iterdir()):
        if path.name.startswith(".") or path.suffix != ".json":
            raise U10ProvisioningError(
                "u10_key_selector_history_entry_unexpected", str(path)
            )
        raw = read_protected_file(
            path,
            root=paths.key_root,
            uid=uid,
            exact_mode=0o444,
        )
        try:
            value = strict_json_loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise U10ProvisioningError(
                "u10_key_selector_history_unreadable", str(path)
            ) from exc
        if not isinstance(value, dict):
            raise U10ProvisioningError("u10_key_selector_history_unreadable", str(path))
        schema_version = value.get("schema_version")
        if schema_version == KEY_SELECTOR_SCHEMA_V1:
            selector = validate_key_selector(value, paths=paths)
            artifact_digest = digest_bytes(raw)["value"]
            if path != paths.selector_history_root / f"{artifact_digest}.json":
                raise U10ProvisioningError(
                    "u10_key_selector_history_filename_mismatch", str(path)
                )
            if artifact_digest in legacy:
                raise U10ProvisioningError(
                    "u10_key_selector_history_duplicate", artifact_digest
                )
            legacy[artifact_digest] = (selector, raw, path)
            continue
        if schema_version != KEY_SELECTOR_SCHEMA:
            raise U10ProvisioningError(
                "u10_key_selector_history_schema_unknown",
                f"{path}: {schema_version!r}",
            )
        if raw != json_record_bytes(value):
            raise U10ProvisioningError(
                "u10_key_selector_history_unreadable",
                f"non-canonical: {path}",
            )
        selector = validate_key_selector_v2(value, paths=paths)
        reference = _selector_ref_v2(selector, raw, paths=paths)
        if Path(reference["locator"]) != path:
            raise U10ProvisioningError(
                "u10_key_selector_history_filename_mismatch", str(path)
            )
        digest = reference["artifact_digest"]["value"]
        if digest in result:
            raise U10ProvisioningError("u10_key_selector_history_duplicate", digest)
        result[digest] = (selector, raw, reference)
    return result, legacy


def _scan_selector_history_v2(
    paths: KeyPaths, *, uid: int
) -> dict[str, tuple[dict[str, Any], bytes, dict[str, Any]]]:
    current, _legacy = _scan_selector_history_denominator_v2(paths, uid=uid)
    return current


def _read_transition_records_v2(
    selector: Mapping[str, Any],
    selector_ref: Mapping[str, Any],
    *,
    paths: KeyPaths,
    uid: int,
    allow_missing_receipt: bool,
) -> dict[str, Any] | None:
    evidence = selector["transition_evidence_selector"]
    auth_ref = evidence["authorization_ref"]
    consumption_ref = evidence["consumption_ref"]
    authorization, authorization_raw = _read_json_record_v2(
        Path(auth_ref["locator"]),
        root=paths.ledger_root,
        uid=uid,
        mode=0o400,
        code="u10_key_authorization_archive_unreadable",
    )
    consumption, consumption_raw = _read_json_record_v2(
        Path(consumption_ref["locator"]),
        root=paths.ledger_root,
        uid=uid,
        mode=0o400,
        code="u10_key_consumption_unreadable",
    )
    authorization = validate_key_authorization_v2(
        authorization,
        paths=paths,
        effective_at=_parse_time(
            consumption.get("reserved_at"),
            code="u10_key_consumption_time_invalid",
        ),
    )
    consumption = validate_key_consumption_v2(
        consumption,
        authorization=authorization,
        authorization_raw=authorization_raw,
        paths=paths,
    )
    observed_auth_ref = _authorization_ref_v2(
        authorization, authorization_raw, paths=paths
    )
    observed_consumption_ref = _consumption_ref_v2(
        consumption, consumption_raw, paths=paths
    )
    if (
        auth_ref != observed_auth_ref
        or consumption_ref != observed_consumption_ref
        or selector["previous_selector_ref"] != authorization["prior_selector_ref"]
        or evidence["prior_selector_ref"] != authorization["prior_selector_ref"]
        or selector["transition_mode"] != authorization["transition_mode"]
    ):
        raise U10ProvisioningError(
            "u10_key_transition_chain_mismatch",
            auth_ref["authorization_id"],
        )
    if selector["state"] == "active":
        public_ref = selector["public_metadata_ref"]
        metadata, metadata_raw = _read_json_record_v2(
            Path(public_ref["locator"]),
            root=paths.key_root,
            uid=uid,
            mode=0o444,
            code="u10_key_metadata_unreadable",
        )
        metadata = validate_key_public_metadata_v2(metadata, paths=paths)
        _validate_public_metadata_ref_v2(
            public_ref,
            metadata=metadata,
            metadata_raw=metadata_raw,
            paths=paths,
        )
        _reobserve_private_matches_metadata_v2(metadata, paths=paths, uid=uid)
        if (
            metadata["authorization_ref"] != auth_ref
            or metadata["consumption_ref"] != consumption_ref
            or metadata["prior_selector_ref"] != selector["previous_selector_ref"]
            or metadata["transition_evidence_selector"] != evidence
            or metadata["key_id"] != authorization["key_id"]
        ):
            raise U10ProvisioningError(
                "u10_key_metadata_transition_mismatch",
                auth_ref["authorization_id"],
            )
    else:
        revocation_ref = selector["revocation_ref"]
        revocation, revocation_raw = _read_json_record_v2(
            Path(revocation_ref["locator"]),
            root=paths.key_root,
            uid=uid,
            mode=0o444,
            code="u10_key_revocation_unreadable",
        )
        revocation = validate_key_revocation_v2(revocation, paths=paths)
        _validate_revocation_ref_v2(
            revocation_ref,
            revocation=revocation,
            revocation_raw=revocation_raw,
            paths=paths,
        )
        if (
            revocation["authorization_ref"] != auth_ref
            or revocation["consumption_ref"] != consumption_ref
            or revocation["prior_selector_ref"] != selector["previous_selector_ref"]
            or revocation["transition_evidence_selector"] != evidence
            or revocation["key_id"] != authorization["key_id"]
        ):
            raise U10ProvisioningError(
                "u10_key_revocation_transition_mismatch",
                auth_ref["authorization_id"],
            )
    receipt_path = Path(evidence["receipt_locator"])
    if not receipt_path.exists() and not receipt_path.is_symlink():
        if allow_missing_receipt:
            return None
        raise U10ProvisioningError(
            "u10_key_transition_receipt_missing", str(receipt_path)
        )
    receipt, receipt_raw = _read_json_record_v2(
        receipt_path,
        root=paths.ledger_root,
        uid=uid,
        mode=0o444,
        code="u10_key_receipt_unreadable",
    )
    receipt = validate_key_receipt_v2(receipt, paths=paths)
    if (
        receipt["authorization_ref"] != auth_ref
        or receipt["consumption_ref"] != consumption_ref
        or receipt["prior_selector_ref"] != selector["previous_selector_ref"]
        or receipt["published_selector_ref"] != selector_ref
        or receipt["transition_mode"] != selector["transition_mode"]
        or receipt["key_operation"] != authorization["key_operation"]
        or receipt["key_id"] != authorization["key_id"]
        or receipt["publisher_contract_binding"]
        != consumption["publisher_contract_binding"]
        or receipt["publication_not_before"] != consumption["reserved_at"]
        or receipt["publication_observed_at"] != selector["selected_at"]
        or receipt_raw != json_record_bytes(receipt)
        or (
            selector["state"] == "active"
            and receipt["public_metadata_ref"] != selector["public_metadata_ref"]
        )
        or (
            selector["state"] == "no_active_key"
            and receipt["revocation_ref"] != selector["revocation_ref"]
        )
    ):
        raise U10ProvisioningError(
            "u10_key_transition_receipt_chain_mismatch",
            auth_ref["authorization_id"],
        )
    return receipt


def _resolve_selector_chain_v2(
    paths: KeyPaths,
    *,
    uid: int,
    pending_authorization_id: str | None = None,
) -> tuple[
    tuple[dict[str, Any], bytes, dict[str, Any]] | None,
    tuple[dict[str, Any], bytes, dict[str, Any]] | None,
]:
    """Reread the complete v2 selector chain and reject forks or rollback."""

    history = _scan_selector_history_v2(paths, uid=uid)
    current = _load_current_selector_v2(paths, uid=uid)
    chain_digests: set[str] = set()
    current_item = current
    while current_item is not None:
        selector, _raw, reference = current_item
        digest = reference["artifact_digest"]["value"]
        if digest in chain_digests:
            raise U10ProvisioningError("u10_key_selector_cycle", digest)
        chain_digests.add(digest)
        stored = history.get(digest)
        if stored is None or stored[1] != current_item[1]:
            raise U10ProvisioningError("u10_key_selector_history_mismatch", digest)
        previous_ref = selector["previous_selector_ref"]
        current_item = (
            None
            if previous_ref is None
            else _read_selector_ref_v2(previous_ref, paths=paths, uid=uid)
        )
    extras = [item for digest, item in history.items() if digest not in chain_digests]
    pending: tuple[dict[str, Any], bytes, dict[str, Any]] | None = None
    if extras:
        candidates = [
            item
            for item in extras
            if pending_authorization_id is not None
            and item[0]["transition_evidence_selector"]["authorization_ref"][
                "authorization_id"
            ]
            == pending_authorization_id
        ]
        if len(extras) != 1 or len(candidates) != 1:
            raise U10ProvisioningError(
                "u10_key_selector_branch_or_rollback",
                ",".join(sorted(item[2]["selector_id"] for item in extras)),
            )
        pending = candidates[0]
        expected_previous = None if current is None else current[2]
        if pending[0]["previous_selector_ref"] != expected_previous:
            raise U10ProvisioningError(
                "u10_key_selector_pending_branch",
                pending_authorization_id,
            )
    # Re-observe every committed transition, oldest references included.  Only
    # the currently selected transition may lack a receipt during recovery.
    current_item = current
    while current_item is not None:
        selector, _raw, reference = current_item
        transition_id = selector["transition_evidence_selector"]["authorization_ref"][
            "authorization_id"
        ]
        allow_missing = (
            pending_authorization_id is not None
            and transition_id == pending_authorization_id
            and current_item == current
        )
        _read_transition_records_v2(
            selector,
            reference,
            paths=paths,
            uid=uid,
            allow_missing_receipt=allow_missing,
        )
        previous_ref = selector["previous_selector_ref"]
        current_item = (
            None
            if previous_ref is None
            else _read_selector_ref_v2(previous_ref, paths=paths, uid=uid)
        )
    if pending is not None:
        _read_transition_records_v2(
            pending[0],
            pending[2],
            paths=paths,
            uid=uid,
            allow_missing_receipt=True,
        )
    return current, pending


def replay_key_transition_chain_v2(
    *,
    paths: KeyPaths = KeyPaths(),
    required_uid: int = 0,
) -> dict[str, Any]:
    """Read-only, lock-stable replay of the complete committed v2 chain.

    Private material is re-observed by the resolver but never returned.  The
    result exposes only the sealed locator/state reference needed by downstream
    store-basis construction.
    """

    if required_uid == 0:
        if os.geteuid() != 0:
            raise U10ProvisioningError(
                "u10_key_replay_requires_root", str(os.geteuid())
            )
        _assert_fixed_key_paths_v2(paths)
    with _key_transition_locks_v2(paths, uid=required_uid):
        current, pending = _resolve_selector_chain_v2(paths, uid=required_uid)
        if pending is not None:
            raise U10ProvisioningError(
                "u10_key_transition_replay_incomplete",
                pending[2]["selector_id"],
            )
        reverse_sequence: list[dict[str, Any]] = []
        item = current
        while item is not None:
            selector, _selector_raw, selector_ref = item
            evidence = selector["transition_evidence_selector"]
            receipt, receipt_raw = _read_json_record_v2(
                Path(evidence["receipt_locator"]),
                root=paths.ledger_root,
                uid=required_uid,
                mode=0o444,
                code="u10_key_receipt_unreadable",
            )
            receipt = validate_key_receipt_v2(receipt, paths=paths)
            reverse_sequence.append(
                {
                    "selector_ref": selector_ref,
                    "previous_selector_ref": selector["previous_selector_ref"],
                    "transition_mode": selector["transition_mode"],
                    "authorization_ref": evidence["authorization_ref"],
                    "consumption_ref": evidence["consumption_ref"],
                    "receipt_ref": {
                        "receipt_id": receipt["receipt_id"],
                        "locator": evidence["receipt_locator"],
                        "artifact_digest": digest_bytes(receipt_raw),
                        "receipt_digest": receipt["receipt_digest"],
                    },
                    "public_metadata_ref": selector["public_metadata_ref"],
                    "revocation_ref": selector["revocation_ref"],
                }
            )
            previous_ref = selector["previous_selector_ref"]
            item = (
                None
                if previous_ref is None
                else _read_selector_ref_v2(previous_ref, paths=paths, uid=required_uid)
            )
        transition_sequence = list(reversed(reverse_sequence))
        active_key: dict[str, Any] | None = None
        if current is not None and current[0]["state"] == "active":
            public_ref = current[0]["public_metadata_ref"]
            metadata, _metadata_raw = _read_json_record_v2(
                Path(public_ref["locator"]),
                root=paths.key_root,
                uid=required_uid,
                mode=0o444,
                code="u10_key_metadata_unreadable",
            )
            metadata = validate_key_public_metadata_v2(metadata, paths=paths)
            active_key = {
                "key_id": metadata["key_id"],
                "key_entity_ref": metadata["key_entity_ref"],
                "public_metadata_ref": public_ref,
                "private_material_ref": metadata["private_material"],
            }
        return {
            "schema_version": "semantic-guard-u10-key-chain-replay/v1",
            "replay_status": "complete",
            "current_selector": None if current is None else current[0],
            "current_selector_ref": None if current is None else current[2],
            "active_key": active_key,
            "transition_sequence": transition_sequence,
            "transition_count": len(transition_sequence),
            "formal_authority": "none",
            "positive_assurance_allowed": False,
        }


def _reobserve_private_matches_metadata_v2(
    metadata: Mapping[str, Any], *, paths: KeyPaths, uid: int
) -> None:
    key_id = str(metadata["key_id"])
    private_raw = read_protected_file(
        paths.generation_root / key_id / "private.ed25519",
        root=paths.key_root,
        uid=uid,
        exact_mode=0o600,
    )
    if len(private_raw) != 32:
        raise U10ProvisioningError("u10_private_key_material_invalid", key_id)
    private_type, encoding, _private_format, public_format = _load_cryptography()
    try:
        private = private_type.from_private_bytes(private_raw)
    except ValueError as exc:
        raise U10ProvisioningError("u10_private_key_material_invalid", key_id) from exc
    derived = private.public_key().public_bytes(encoding.Raw, public_format.Raw)
    if len(derived) != 32 or metadata["public_key"]["value"] != base64.b64encode(
        derived
    ).decode("ascii"):
        raise U10ProvisioningError("u10_private_public_key_mismatch", key_id)


def _read_denominator_record_v2(
    path: Path,
    *,
    root: Path,
    uid: int,
    mode: int,
    code: str,
) -> tuple[dict[str, Any], bytes]:
    """Read strict JSON while leaving legacy byte serialization untouched."""

    raw = read_protected_file(
        path,
        root=root,
        uid=uid,
        exact_mode=mode,
    )
    try:
        value = strict_json_loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise U10ProvisioningError(code, str(path)) from exc
    if not isinstance(value, dict):
        raise U10ProvisioningError(code, str(path))
    return value, raw


def _scan_key_transition_ledger_denominator_v2(
    paths: KeyPaths, *, uid: int
) -> tuple[
    dict[str, dict[str, tuple[dict[str, Any], bytes, Path]]],
    dict[str, dict[str, tuple[dict[str, Any], bytes, Path]]],
]:
    """Classify every ledger entry without trusting its schema declaration."""

    kinds = {definition[0] for definition in _KEY_LEDGER_LAYOUT_V2.values()}
    records: dict[str, dict[str, tuple[dict[str, Any], bytes, Path]]] = {
        kind: {} for kind in kinds
    }
    legacy: dict[str, dict[str, tuple[dict[str, Any], bytes, Path]]] = {
        kind: {} for kind in kinds
    }
    for path in sorted(paths.ledger_root.iterdir()):
        matches = [
            (suffix, *definition)
            for suffix, definition in _KEY_LEDGER_LAYOUT_V2.items()
            if path.name.endswith(suffix)
        ]
        if len(matches) != 1:
            raise U10ProvisioningError(
                "u10_key_transition_ledger_entry_unexpected", str(path)
            )
        suffix, kind, mode, current_schema, legacy_schema = matches[0]
        authorization_id = path.name.removesuffix(suffix)
        _require_id(
            authorization_id,
            code="u10_key_transition_ledger_identifier_invalid",
        )
        value, raw = _read_denominator_record_v2(
            path,
            root=paths.ledger_root,
            uid=uid,
            mode=mode,
            code="u10_key_transition_ledger_record_unreadable",
        )
        schema_version = value.get("schema_version")
        if legacy_schema is not None and schema_version == legacy_schema:
            target = legacy
        elif schema_version == current_schema:
            if raw != json_record_bytes(value):
                raise U10ProvisioningError(
                    "u10_key_transition_ledger_record_unreadable",
                    f"non-canonical: {path}",
                )
            target = records
        else:
            raise U10ProvisioningError(
                "u10_key_transition_ledger_schema_unknown",
                f"{path}: {schema_version!r}",
            )
        if authorization_id in target[kind]:
            raise U10ProvisioningError("u10_key_transition_ledger_duplicate", str(path))
        target[kind][authorization_id] = (value, raw, path)
    return records, legacy


def _validate_closed_legacy_key_ledger_v1(
    records: Mapping[str, Mapping[str, tuple[dict[str, Any], bytes, Path]]],
    *,
    paths: KeyPaths,
) -> dict[str, dict[str, Any]]:
    """Validate genuine completed v1 chains before read-only exclusion."""

    all_ids = set().union(*(set(items) for items in records.values()))
    result: dict[str, dict[str, Any]] = {}
    for authorization_id in sorted(all_ids):
        kinds = {kind for kind, items in records.items() if authorization_id in items}
        if kinds != {"authorization", "consumption", "receipt"}:
            raise U10ProvisioningError(
                "u10_key_legacy_transition_unclosed_or_orphaned",
                authorization_id,
            )
        authorization_value, authorization_raw, authorization_path = records[
            "authorization"
        ][authorization_id]
        consumption_value, consumption_raw, consumption_path = records["consumption"][
            authorization_id
        ]
        receipt_value, _receipt_raw, receipt_path = records["receipt"][authorization_id]
        (
            expected_authorization_path,
            expected_consumption_path,
            expected_receipt_path,
        ) = _key_record_paths(authorization_id, paths.ledger_root)
        if (
            authorization_path != expected_authorization_path
            or consumption_path != expected_consumption_path
            or receipt_path != expected_receipt_path
        ):
            raise U10ProvisioningError(
                "u10_key_legacy_transition_identifier_mismatch",
                authorization_id,
            )
        reserved_at = _parse_time(
            consumption_value.get("reserved_at"),
            code="u10_key_consumption_time_invalid",
        )
        authorization = validate_key_authorization(
            authorization_value,
            paths=paths,
            effective_at=reserved_at,
        )
        if authorization["authorization_id"] != authorization_id:
            raise U10ProvisioningError(
                "u10_key_legacy_transition_identifier_mismatch",
                authorization_id,
            )
        consumption = validate_key_consumption(
            consumption_value,
            authorization=authorization,
        )
        receipt = validate_key_receipt(receipt_value, paths=paths)
        authorization_ref = {
            "authorization_id": authorization_id,
            "authorization_digest": authorization["authorization_digest"],
        }
        consumption_ref = {
            "consumption_id": consumption["consumption_id"],
            "consumption_digest": consumption["consumption_digest"],
        }
        if (
            consumption["authorization_ref"]
            != {
                **authorization_ref,
                "artifact_digest": digest_bytes(authorization_raw),
            }
            or receipt["authorization_ref"] != authorization_ref
            or receipt["consumption_ref"] != consumption_ref
            or receipt["publisher_contract_binding"]
            != consumption["publisher_contract_binding"]
            or receipt["key_operation"] != authorization["key_operation"]
            or receipt["key_id"] != authorization["key_id"]
            or receipt["occurrence_id"] != consumption["occurrence_id"]
            or receipt["publication_not_before"] != consumption["reserved_at"]
        ):
            raise U10ProvisioningError(
                "u10_key_legacy_transition_chain_mismatch",
                authorization_id,
            )
        result[authorization_id] = {
            "authorization": authorization,
            "authorization_raw": authorization_raw,
            "authorization_ref": authorization_ref,
            "consumption": consumption,
            "consumption_raw": consumption_raw,
            "consumption_ref": consumption_ref,
            "receipt": receipt,
        }
    return result


def _validate_closed_legacy_selector_history_v1(
    history: Mapping[str, tuple[dict[str, Any], bytes, Path]],
    *,
    chains: Mapping[str, Mapping[str, Any]],
) -> None:
    """Bind each validated v1 selector to one completed v1 ledger chain."""

    selector_ids: set[str] = set()
    for selector, _raw, path in history.values():
        authorization_ref = selector["transition_authorization_ref"]
        authorization_id = str(authorization_ref["authorization_id"])
        if authorization_id in selector_ids:
            raise U10ProvisioningError(
                "u10_key_legacy_selector_duplicate_transition",
                authorization_id,
            )
        selector_ids.add(authorization_id)
        chain = chains.get(authorization_id)
        if chain is None:
            raise U10ProvisioningError("u10_key_legacy_selector_orphaned", str(path))
        receipt = chain["receipt"]
        if (
            authorization_ref != chain["authorization_ref"]
            or selector["selected_at"] != receipt["publication_observed_at"]
            or (
                selector["state"] == "active"
                and (
                    receipt["key_state"] != "active"
                    or selector["key_id"] != receipt["key_id"]
                    or selector["public_metadata_ref"] != receipt["public_metadata_ref"]
                )
            )
            or (
                selector["state"] == "no_active_key"
                and receipt["key_state"] != "revoked_no_active_key"
            )
        ):
            raise U10ProvisioningError(
                "u10_key_legacy_selector_chain_mismatch",
                authorization_id,
            )
    if selector_ids != set(chains):
        missing = sorted(set(chains) - selector_ids)
        raise U10ProvisioningError("u10_key_legacy_selector_missing", ",".join(missing))


def _validate_ledger_pair_v2(
    records: Mapping[str, Mapping[str, tuple[dict[str, Any], bytes, Path]]],
    authorization_id: str,
    *,
    paths: KeyPaths,
) -> dict[str, Any]:
    authorization_item = records["authorization"].get(authorization_id)
    consumption_item = records["consumption"].get(authorization_id)
    if authorization_item is None:
        raise U10ProvisioningError(
            "u10_key_transition_unclosed_or_orphaned",
            f"{authorization_id}: authorization",
        )
    authorization_value, authorization_raw, authorization_path = authorization_item
    effective_at = (
        None
        if consumption_item is None
        else _parse_time(
            consumption_item[0].get("reserved_at"),
            code="u10_key_consumption_time_invalid",
        )
    )
    authorization = validate_key_authorization_v2(
        authorization_value,
        paths=paths,
        effective_at=effective_at,
    )
    expected_authorization_path, expected_consumption_path, _receipt_path = (
        _key_record_paths(authorization_id, paths.ledger_root)
    )
    if (
        authorization["authorization_id"] != authorization_id
        or authorization_path != expected_authorization_path
    ):
        raise U10ProvisioningError(
            "u10_key_transition_ledger_identifier_mismatch",
            authorization_id,
        )
    authorization_ref = {
        "authorization_id": authorization_id,
        "locator": str(authorization_path),
        "artifact_digest": digest_bytes(authorization_raw),
        "authorization_digest": authorization["authorization_digest"],
    }
    if consumption_item is None:
        return {
            "authorization": authorization,
            "authorization_ref": authorization_ref,
            "consumption": None,
            "consumption_ref": None,
        }
    consumption_value, consumption_raw, consumption_path = consumption_item
    consumption = validate_key_consumption_v2(
        consumption_value,
        authorization=authorization,
        authorization_raw=authorization_raw,
        paths=paths,
    )
    consumption_ref = {
        "consumption_id": consumption["consumption_id"],
        "locator": str(consumption_path),
        "artifact_digest": digest_bytes(consumption_raw),
        "consumption_digest": consumption["consumption_digest"],
    }
    if (
        consumption_path != expected_consumption_path
        or consumption["authorization_ref"] != authorization_ref
        or consumption_ref["consumption_id"] != f"consumption.{authorization_id}"
    ):
        raise U10ProvisioningError(
            "u10_key_transition_ledger_identifier_mismatch",
            authorization_id,
        )
    return {
        "authorization": authorization,
        "authorization_ref": authorization_ref,
        "consumption": consumption,
        "consumption_ref": consumption_ref,
    }


def _legacy_public_metadata_ref_v1(
    metadata: Mapping[str, Any],
    metadata_raw: bytes,
    *,
    paths: KeyPaths,
) -> dict[str, Any]:
    authorization_ref = metadata["authorization_ref"]
    authorization_id = str(authorization_ref["authorization_id"])
    return {
        "key_id": metadata["key_id"],
        "key_entity_ref": metadata["key_entity_ref"],
        "metadata_locator": str(
            paths.generation_root / str(metadata["key_id"]) / "public-metadata.json"
        ),
        "metadata_artifact_digest": digest_bytes(metadata_raw),
        "metadata_digest": metadata["metadata_digest"],
        "generation_authorization_ref": authorization_ref,
        "generation_receipt_selector": _generation_receipt_selector(
            authorization_id, paths
        ),
    }


def _validate_recoverable_closed_stage_v2(
    stage: Path,
    *,
    authorization: Mapping[str, Any],
    uid: int,
) -> None:
    """Validate the exact abandoned stage before closure-authorized removal."""

    observed = _assert_directory(stage, uid=uid, allow_mutable=True)
    if stat.S_IMODE(observed.st_mode) not in {0o700, 0o555}:
        raise U10ProvisioningError("u10_closed_key_stage_mode_invalid", str(stage))
    operation = authorization["key_operation"]
    authorization_id = str(authorization["authorization_id"])
    allowed = (
        {"private.ed25519", "public-metadata.json"}
        if operation in {"generate", "rotate"}
        else {f"{authorization_id}.json"}
    )
    for item in stage.iterdir():
        item_stat = item.lstat()
        if (
            item.name not in allowed
            or stat.S_ISLNK(item_stat.st_mode)
            or not stat.S_ISREG(item_stat.st_mode)
            or item_stat.st_uid != uid
            or item_stat.st_nlink != 1
        ):
            raise U10ProvisioningError(
                "u10_closed_key_stage_denominator_invalid", str(item)
            )
        expected_mode = 0o600 if item.name == "private.ed25519" else 0o444
        if stat.S_IMODE(item_stat.st_mode) != expected_mode:
            raise U10ProvisioningError("u10_closed_key_stage_mode_invalid", str(item))


def _scan_key_material_denominator_before_mutation_v2(
    *,
    paths: KeyPaths,
    uid: int,
    selector_history: Mapping[str, tuple[dict[str, Any], bytes, dict[str, Any]]],
    selected_pending_pair: Mapping[str, Any] | None,
    legacy_chains: Mapping[str, Mapping[str, Any]],
    recoverable_closed_stages: Mapping[Path, Mapping[str, Any]],
) -> tuple[Path, ...]:
    referenced_metadata: dict[str, Mapping[str, Any]] = {}
    referenced_revocations: dict[str, Mapping[str, Any]] = {}
    for selector, _raw, _selector_ref in selector_history.values():
        public_ref = selector["public_metadata_ref"]
        revocation_ref = selector["revocation_ref"]
        if isinstance(public_ref, Mapping):
            referenced_metadata[str(public_ref["locator"])] = public_ref
        if isinstance(revocation_ref, Mapping):
            referenced_revocations[str(revocation_ref["locator"])] = revocation_ref

    legacy_metadata: dict[str, tuple[Mapping[str, Any], Mapping[str, Any]]] = {}
    legacy_revocations: dict[str, Mapping[str, Any]] = {}
    for authorization_id, chain in legacy_chains.items():
        receipt = chain["receipt"]
        authorization = chain["authorization"]
        if authorization["key_operation"] in {"generate", "rotate"}:
            public_ref = receipt["public_metadata_ref"]
            locator = str(public_ref["metadata_locator"])
            if locator in legacy_metadata:
                raise U10ProvisioningError(
                    "u10_key_legacy_metadata_ref_duplicate", locator
                )
            legacy_metadata[locator] = (public_ref, chain)
        else:
            locator = str(
                paths.revocation_root
                / str(authorization["key_id"])
                / f"{authorization_id}.json"
            )
            legacy_revocations[locator] = chain

    pending_authorization = (
        None
        if selected_pending_pair is None
        else selected_pending_pair["authorization"]
    )
    pending_authorization_ref = (
        None
        if selected_pending_pair is None
        else selected_pending_pair["authorization_ref"]
    )
    pending_consumption = (
        None if selected_pending_pair is None else selected_pending_pair["consumption"]
    )
    pending_consumption_ref = (
        None
        if selected_pending_pair is None
        else selected_pending_pair["consumption_ref"]
    )
    pending_stage_name: str | None = None
    if pending_authorization is not None and pending_consumption is not None:
        pending_stage_name = (
            f".{pending_authorization['key_id']}.stage."
            f"{pending_authorization['authorization_digest']['value'][:24]}"
        )

    cleanup_stages: list[Path] = []
    observed_legacy_metadata: set[str] = set()
    observed_legacy_revocations: set[str] = set()

    for generation in sorted(paths.generation_root.iterdir()):
        if generation.name.startswith("."):
            if (
                pending_authorization is not None
                and generation.name == pending_stage_name
                and pending_authorization["key_operation"] in {"generate", "rotate"}
            ):
                continue
            closed_authorization = recoverable_closed_stages.get(generation)
            if closed_authorization is not None and closed_authorization[
                "key_operation"
            ] in {"generate", "rotate"}:
                _validate_recoverable_closed_stage_v2(
                    generation,
                    authorization=closed_authorization,
                    uid=uid,
                )
                cleanup_stages.append(generation)
                continue
            raise U10ProvisioningError(
                "u10_key_generation_stage_orphaned", str(generation)
            )
        _assert_directory(generation, uid=uid, exact_mode=0o555)
        if {item.name for item in generation.iterdir()} != {
            "private.ed25519",
            "public-metadata.json",
        }:
            raise U10ProvisioningError(
                "u10_key_generation_denominator_mismatch", str(generation)
            )
        metadata_path = generation / "public-metadata.json"
        metadata_value, metadata_raw = _read_denominator_record_v2(
            metadata_path,
            root=paths.key_root,
            uid=uid,
            mode=0o444,
            code="u10_key_metadata_unreadable",
        )
        schema_version = metadata_value.get("schema_version")
        if schema_version == KEY_METADATA_SCHEMA_V1:
            metadata = validate_key_public_metadata(metadata_value, paths=paths)
            if generation.name != metadata["key_id"]:
                raise U10ProvisioningError(
                    "u10_key_legacy_generation_identifier_mismatch",
                    str(generation),
                )
            _reobserve_private_matches_metadata(metadata, paths=paths, uid=uid)
            expected = legacy_metadata.get(str(metadata_path))
            observed_ref = _legacy_public_metadata_ref_v1(
                metadata, metadata_raw, paths=paths
            )
            if (
                expected is None
                or observed_ref != expected[0]
                or metadata["authorization_ref"] != expected[1]["authorization_ref"]
                or metadata["key_id"] != expected[1]["authorization"]["key_id"]
            ):
                raise U10ProvisioningError(
                    "u10_key_legacy_generation_orphaned", str(metadata_path)
                )
            observed_legacy_metadata.add(str(metadata_path))
            continue
        if schema_version != KEY_METADATA_SCHEMA:
            raise U10ProvisioningError(
                "u10_key_generation_schema_unknown",
                f"{metadata_path}: {schema_version!r}",
            )
        if metadata_raw != json_record_bytes(metadata_value):
            raise U10ProvisioningError(
                "u10_key_metadata_unreadable",
                f"non-canonical: {metadata_path}",
            )
        metadata = validate_key_public_metadata_v2(metadata_value, paths=paths)
        if generation.name != metadata["key_id"]:
            raise U10ProvisioningError(
                "u10_key_generation_identifier_mismatch", str(generation)
            )
        _reobserve_private_matches_metadata_v2(metadata, paths=paths, uid=uid)
        observed_ref = _public_metadata_ref_v2(metadata, metadata_raw, paths=paths)
        referenced_ref = referenced_metadata.get(str(metadata_path))
        if referenced_ref == observed_ref:
            continue
        if (
            pending_authorization is not None
            and pending_consumption is not None
            and metadata["authorization_ref"] == pending_authorization_ref
            and metadata["consumption_ref"] == pending_consumption_ref
            and metadata["key_id"] == pending_authorization["key_id"]
            and pending_authorization["key_operation"] in {"generate", "rotate"}
        ):
            continue
        raise U10ProvisioningError("u10_key_generation_orphaned", str(metadata_path))

    for key_directory in sorted(paths.revocation_root.iterdir()):
        if key_directory.name.startswith("."):
            if (
                pending_authorization is not None
                and key_directory.name == pending_stage_name
                and pending_authorization["key_operation"] == "revoke"
            ):
                continue
            closed_authorization = recoverable_closed_stages.get(key_directory)
            if (
                closed_authorization is not None
                and closed_authorization["key_operation"] == "revoke"
            ):
                _validate_recoverable_closed_stage_v2(
                    key_directory,
                    authorization=closed_authorization,
                    uid=uid,
                )
                cleanup_stages.append(key_directory)
                continue
            raise U10ProvisioningError(
                "u10_key_revocation_stage_orphaned", str(key_directory)
            )
        _assert_directory(key_directory, uid=uid, exact_mode=0o555)
        if _UUID.fullmatch(key_directory.name) is None:
            raise U10ProvisioningError(
                "u10_key_revocation_directory_identifier_invalid",
                str(key_directory),
            )
        observed_entries = 0
        for path in sorted(key_directory.iterdir()):
            if path.name.startswith(".") or path.suffix != ".json":
                raise U10ProvisioningError(
                    "u10_key_revocation_entry_unexpected", str(path)
                )
            revocation_value, revocation_raw = _read_denominator_record_v2(
                path,
                root=paths.key_root,
                uid=uid,
                mode=0o444,
                code="u10_key_revocation_unreadable",
            )
            schema_version = revocation_value.get("schema_version")
            if schema_version == KEY_REVOCATION_SCHEMA_V1:
                revocation = validate_key_revocation(revocation_value)
                authorization_id = str(
                    revocation["authorization_ref"]["authorization_id"]
                )
                expected = legacy_revocations.get(str(path))
                if (
                    path.name != f"{authorization_id}.json"
                    or key_directory.name != revocation["key_id"]
                    or expected is None
                    or expected["authorization_ref"] != revocation["authorization_ref"]
                    or expected["authorization"]["key_id"] != revocation["key_id"]
                    or expected["authorization"]["key_operation"] != "revoke"
                ):
                    raise U10ProvisioningError(
                        "u10_key_legacy_revocation_orphaned", str(path)
                    )
                observed_legacy_revocations.add(str(path))
                observed_entries += 1
                continue
            if schema_version != KEY_REVOCATION_SCHEMA:
                raise U10ProvisioningError(
                    "u10_key_revocation_schema_unknown",
                    f"{path}: {schema_version!r}",
                )
            if revocation_raw != json_record_bytes(revocation_value):
                raise U10ProvisioningError(
                    "u10_key_revocation_unreadable",
                    f"non-canonical: {path}",
                )
            revocation = validate_key_revocation_v2(revocation_value, paths=paths)
            observed_ref = _revocation_ref_v2(revocation, revocation_raw, paths=paths)
            referenced_ref = referenced_revocations.get(str(path))
            if referenced_ref == observed_ref:
                observed_entries += 1
                continue
            if (
                pending_authorization is not None
                and pending_consumption is not None
                and revocation["authorization_ref"] == pending_authorization_ref
                and revocation["consumption_ref"] == pending_consumption_ref
                and revocation["key_id"] == pending_authorization["key_id"]
                and pending_authorization["key_operation"] == "revoke"
            ):
                observed_entries += 1
                continue
            raise U10ProvisioningError("u10_key_revocation_orphaned", str(path))
        if observed_entries == 0:
            raise U10ProvisioningError(
                "u10_key_revocation_directory_orphaned", str(key_directory)
            )
    if observed_legacy_metadata != set(legacy_metadata):
        raise U10ProvisioningError(
            "u10_key_legacy_generation_missing",
            ",".join(sorted(set(legacy_metadata) - observed_legacy_metadata)),
        )
    if observed_legacy_revocations != set(legacy_revocations):
        raise U10ProvisioningError(
            "u10_key_legacy_revocation_missing",
            ",".join(sorted(set(legacy_revocations) - observed_legacy_revocations)),
        )
    return tuple(cleanup_stages)


def _validate_closed_key_denominator_before_mutation_v2(
    *, paths: KeyPaths, uid: int, selected_id: str
) -> tuple[Path, ...]:
    """Reject every unexplained v2 record or material before the first write."""

    current, pending = _resolve_selector_chain_v2(
        paths,
        uid=uid,
        pending_authorization_id=selected_id,
    )
    selector_history, legacy_selector_history = _scan_selector_history_denominator_v2(
        paths, uid=uid
    )
    records, legacy_records = _scan_key_transition_ledger_denominator_v2(paths, uid=uid)
    legacy_chains = _validate_closed_legacy_key_ledger_v1(legacy_records, paths=paths)
    _validate_closed_legacy_selector_history_v1(
        legacy_selector_history,
        chains=legacy_chains,
    )
    selector_ids = {
        str(
            selector["transition_evidence_selector"]["authorization_ref"][
                "authorization_id"
            ]
        )
        for selector, _raw, _reference in selector_history.values()
    }
    pending_id = (
        None
        if pending is None
        else str(
            pending[0]["transition_evidence_selector"]["authorization_ref"][
                "authorization_id"
            ]
        )
    )
    current_head_id = (
        None
        if current is None
        else str(
            current[0]["transition_evidence_selector"]["authorization_ref"][
                "authorization_id"
            ]
        )
    )
    all_ids = set().union(*(set(items) for items in records.values()))
    selected_pending_pair: dict[str, Any] | None = None
    recoverable_closed_stages: dict[Path, Mapping[str, Any]] = {}
    for authorization_id in sorted(all_ids):
        kinds = {kind for kind, items in records.items() if authorization_id in items}
        if authorization_id in selector_ids:
            if not {"authorization", "consumption"}.issubset(kinds):
                raise U10ProvisioningError(
                    "u10_key_transition_unclosed_or_orphaned",
                    authorization_id,
                )
            if "emergency_closure" in kinds:
                raise U10ProvisioningError(
                    "u10_key_committed_transition_has_emergency_closure",
                    authorization_id,
                )
            if "receipt" not in kinds and authorization_id != selected_id:
                raise U10ProvisioningError(
                    "u10_key_transition_unclosed_or_orphaned",
                    authorization_id,
                )
            if "receipt" in kinds and authorization_id == pending_id:
                raise U10ProvisioningError(
                    "u10_key_receipt_without_selected_transition",
                    authorization_id,
                )
            _validate_ledger_pair_v2(records, authorization_id, paths=paths)
            continue
        if authorization_id == selected_id:
            if kinds not in (
                {"authorization"},
                {"authorization", "consumption"},
            ):
                raise U10ProvisioningError(
                    "u10_key_transition_quarantined", authorization_id
                )
            selected_pending_pair = _validate_ledger_pair_v2(
                records, authorization_id, paths=paths
            )
            continue
        if kinds != {
            "authorization",
            "consumption",
            "emergency_closure",
        }:
            raise U10ProvisioningError(
                "u10_key_transition_unclosed_or_orphaned",
                authorization_id,
            )
        pair = _validate_ledger_pair_v2(records, authorization_id, paths=paths)
        closure = validate_key_emergency_closure_v1(
            records["emergency_closure"][authorization_id][0],
            paths=paths,
        )
        if (
            closure["authorization_ref"] != pair["authorization_ref"]
            or closure["consumption_ref"] != pair["consumption_ref"]
            or closure["prior_selector_ref"]
            != pair["consumption"]["prior_selector_ref"]
            or closure["closure_disposition"] != "abandoned_before_publication"
            or closure["published_selector_ref"] is not None
        ):
            raise U10ProvisioningError(
                "u10_key_emergency_closure_chain_mismatch",
                authorization_id,
            )
        authorization = pair["authorization"]
        stage_root = (
            paths.generation_root
            if authorization["key_operation"] in {"generate", "rotate"}
            else paths.revocation_root
        )
        stage = stage_root / (
            f".{authorization['key_id']}.stage."
            f"{authorization['authorization_digest']['value'][:24]}"
        )
        recoverable_closed_stages[stage] = authorization
    if selected_id in selector_ids and (
        selected_id == pending_id or selected_id == current_head_id
    ):
        selected_pending_pair = _validate_ledger_pair_v2(
            records, selected_id, paths=paths
        )
    return _scan_key_material_denominator_before_mutation_v2(
        paths=paths,
        uid=uid,
        selector_history=selector_history,
        selected_pending_pair=selected_pending_pair,
        legacy_chains=legacy_chains,
        recoverable_closed_stages=recoverable_closed_stages,
    )


def _publish_selector_v2(
    paths: KeyPaths, selector: Mapping[str, Any]
) -> tuple[bytes, dict[str, Any]]:
    selector = validate_key_selector_v2(selector, paths=paths)
    raw = json_record_bytes(selector)
    reference = _selector_ref_v2(selector, raw, paths=paths)
    history_path = Path(reference["locator"])
    _atomic_append_only(history_path, selector, mode=0o444)
    history_raw = read_protected_file(
        history_path, root=paths.key_root, uid=os.geteuid(), exact_mode=0o444
    )
    if history_raw != raw:
        raise U10ProvisioningError(
            "u10_key_selector_history_write_mismatch", str(history_path)
        )
    _atomic_replace(paths.selector_path, raw, mode=0o444)
    return raw, reference


def _read_emergency_closure_v1(
    authorization_id: str,
    *,
    paths: KeyPaths,
    uid: int,
) -> dict[str, Any] | None:
    path = paths.ledger_root / f"{authorization_id}.emergency-closure.json"
    if not path.exists() and not path.is_symlink():
        return None
    closure, _raw = _read_json_record_v2(
        path,
        root=paths.ledger_root,
        uid=uid,
        mode=0o444,
        code="u10_key_emergency_closure_unreadable",
    )
    return validate_key_emergency_closure_v1(closure, paths=paths)


def _assert_no_other_unresolved_key_consumption_v2(
    *,
    paths: KeyPaths,
    selected_id: str,
    uid: int,
) -> None:
    history = _scan_selector_history_v2(paths, uid=uid)
    for path in sorted(paths.ledger_root.glob("*.consumption.json")):
        consumption, consumption_raw = _read_denominator_record_v2(
            path,
            root=paths.ledger_root,
            uid=uid,
            mode=0o400,
            code="u10_key_consumption_unreadable",
        )
        schema_version = consumption.get("schema_version")
        if schema_version == KEY_CONSUMPTION_SCHEMA_V1:
            continue
        if schema_version != KEY_CONSUMPTION_SCHEMA:
            raise U10ProvisioningError(
                "u10_key_transition_ledger_schema_unknown",
                f"{path}: {schema_version!r}",
            )
        if consumption_raw != json_record_bytes(consumption):
            raise U10ProvisioningError(
                "u10_key_consumption_unreadable",
                f"non-canonical: {path}",
            )
        authorization_id = consumption.get("authorization_ref", {}).get(
            "authorization_id"
        )
        if authorization_id == selected_id:
            continue
        auth_ref = _validate_authorization_ref_v2(
            consumption.get("authorization_ref"),
            paths=paths,
            code="u10_key_consumption_authorization_ref_invalid",
        )
        authorization, authorization_raw = _read_json_record_v2(
            Path(auth_ref["locator"]),
            root=paths.ledger_root,
            uid=uid,
            mode=0o400,
            code="u10_key_authorization_archive_unreadable",
        )
        authorization = validate_key_authorization_v2(
            authorization,
            paths=paths,
            effective_at=_parse_time(
                consumption.get("reserved_at"),
                code="u10_key_consumption_time_invalid",
            ),
        )
        consumption = validate_key_consumption_v2(
            consumption,
            authorization=authorization,
            authorization_raw=authorization_raw,
            paths=paths,
        )
        receipt_path = paths.ledger_root / f"{authorization_id}.receipt.json"
        if receipt_path.exists() or receipt_path.is_symlink():
            receipt, _receipt_raw = _read_json_record_v2(
                receipt_path,
                root=paths.ledger_root,
                uid=uid,
                mode=0o444,
                code="u10_key_receipt_unreadable",
            )
            receipt = validate_key_receipt_v2(receipt, paths=paths)
            published_ref = receipt["published_selector_ref"]
            published = history.get(published_ref["artifact_digest"]["value"])
            if published is None or published[2] != published_ref:
                raise U10ProvisioningError(
                    "u10_key_resolved_consumption_selector_missing",
                    str(authorization_id),
                )
            observed_receipt = _read_transition_records_v2(
                published[0],
                published[2],
                paths=paths,
                uid=uid,
                allow_missing_receipt=False,
            )
            if (
                observed_receipt != receipt
                or receipt["authorization_ref"] != auth_ref
                or receipt["consumption_ref"]
                != {
                    "consumption_id": consumption["consumption_id"],
                    "locator": str(path),
                    "artifact_digest": digest_bytes(consumption_raw),
                    "consumption_digest": consumption["consumption_digest"],
                }
            ):
                raise U10ProvisioningError(
                    "u10_key_resolved_consumption_chain_mismatch",
                    str(authorization_id),
                )
            continue
        closure = _read_emergency_closure_v1(
            str(authorization_id), paths=paths, uid=uid
        )
        if closure is None:
            raise U10ProvisioningError(
                "u10_unresolved_prior_key_consumption", str(authorization_id)
            )
        expected_consumption_ref = {
            "consumption_id": consumption["consumption_id"],
            "locator": str(path),
            "artifact_digest": digest_bytes(consumption_raw),
            "consumption_digest": consumption["consumption_digest"],
        }
        if closure["consumption_ref"] != expected_consumption_ref:
            raise U10ProvisioningError(
                "u10_key_emergency_closure_consumption_mismatch",
                str(authorization_id),
            )
        if (
            closure["authorization_ref"] != consumption["authorization_ref"]
            or closure["prior_selector_ref"] != consumption["prior_selector_ref"]
        ):
            raise U10ProvisioningError(
                "u10_key_emergency_closure_chain_mismatch",
                str(authorization_id),
            )
        published = [
            item
            for item in history.values()
            if item[0]["transition_evidence_selector"]["authorization_ref"][
                "authorization_id"
            ]
            == authorization_id
        ]
        if (
            closure["closure_disposition"] != "abandoned_before_publication"
            or published
        ):
            raise U10ProvisioningError(
                "u10_key_transition_quarantined", str(authorization_id)
            )


def execute_key_authorization(
    authorization_id: str,
    *,
    publisher_contract_binding: Mapping[str, Any],
    paths: KeyPaths = KeyPaths(),
    required_uid: int = 0,
) -> dict[str, Any]:
    """Execute one v2 key transition from a fixed identifier only.

    v1 records remain inspectable through their validators, but this mutating
    route never emits or resumes v1 state.
    """

    publisher_binding = _validate_publisher_contract_binding(publisher_contract_binding)
    authorization_id = _require_id(
        authorization_id, code="u10_key_authorization_id_invalid"
    )
    if required_uid == 0:
        expected = U10_ROOT / "bootstrap" / "u10_initial_trust_provisioner.py"
        if os.geteuid() != 0:
            raise U10ProvisioningError(
                "u10_key_operation_requires_root", str(os.geteuid())
            )
        if Path(__file__) != expected:
            raise U10ProvisioningError(
                "u10_key_provisioner_not_fixed", str(Path(__file__))
            )
        _assert_fixed_key_paths_v2(paths)
        if (
            os.environ.get("SEMANTIC_GUARD_U10_CONTROL_VERIFIED")
            != "fixed-control-outer-v1"
            or not sys.flags.isolated
            or sys.flags.no_site
            or not sys.flags.dont_write_bytecode
        ):
            raise U10ProvisioningError(
                "u10_control_outer_verification_missing", "key route"
            )
    authorization_path = paths.authorization_root / f"{authorization_id}.json"
    auth_archive, consumption_path, receipt_path = _key_record_paths(
        authorization_id, paths.ledger_root
    )
    with _key_transition_locks_v2(paths, uid=required_uid):
        authorization_candidate, authorization_raw = _read_json_record_v2(
            authorization_path,
            root=paths.u10_root,
            uid=required_uid,
            mode=0o400,
            code="u10_key_authorization_unreadable",
        )
        if authorization_candidate.get("schema_version") != KEY_AUTH_SCHEMA:
            raise U10ProvisioningError(
                "u10_key_legacy_authorization_read_only",
                str(authorization_candidate.get("schema_version")),
            )
        existing_consumption: dict[str, Any] | None = None
        existing_consumption_raw: bytes | None = None
        if consumption_path.exists() or consumption_path.is_symlink():
            existing_consumption, existing_consumption_raw = _read_json_record_v2(
                consumption_path,
                root=paths.ledger_root,
                uid=required_uid,
                mode=0o400,
                code="u10_key_consumption_unreadable",
            )
        effective_at = (
            None
            if existing_consumption is None
            else _parse_time(
                existing_consumption.get("reserved_at"),
                code="u10_key_consumption_time_invalid",
            )
        )
        authorization = validate_key_authorization_v2(
            authorization_candidate,
            paths=paths,
            effective_at=effective_at,
        )
        if authorization["authorization_id"] != authorization_id:
            raise U10ProvisioningError(
                "u10_key_authorization_binding_invalid", authorization_id
            )
        if auth_archive.exists() or auth_archive.is_symlink():
            archived_raw = read_protected_file(
                auth_archive,
                root=paths.ledger_root,
                uid=required_uid,
                exact_mode=0o400,
            )
            if archived_raw != authorization_raw:
                raise U10ProvisioningError(
                    "u10_key_authorization_archive_mismatch",
                    authorization_id,
                )
        recoverable_closed_stages = _validate_closed_key_denominator_before_mutation_v2(
            paths=paths,
            uid=required_uid,
            selected_id=authorization_id,
        )
        for stage in recoverable_closed_stages:
            _safe_remove_tree(stage, uid=required_uid)
            _fsync_directory(stage.parent)
        _atomic_append_only(auth_archive, authorization, mode=0o400)
        archived_raw = read_protected_file(
            auth_archive,
            root=paths.ledger_root,
            uid=required_uid,
            exact_mode=0o400,
        )
        if archived_raw != authorization_raw:
            raise U10ProvisioningError(
                "u10_key_authorization_archive_mismatch", authorization_id
            )
        authorization_ref = {
            "authorization_id": authorization_id,
            "locator": str(auth_archive),
            "artifact_digest": digest_bytes(authorization_raw),
            "authorization_digest": authorization["authorization_digest"],
        }
        current, pending_history = _resolve_selector_chain_v2(
            paths,
            uid=required_uid,
            pending_authorization_id=authorization_id,
        )
        _assert_no_other_unresolved_key_consumption_v2(
            paths=paths, selected_id=authorization_id, uid=required_uid
        )
        consumption: dict[str, Any] | None = None
        consumption_raw: bytes | None = existing_consumption_raw
        if existing_consumption is not None:
            consumption = validate_key_consumption_v2(
                existing_consumption,
                authorization=authorization,
                authorization_raw=authorization_raw,
                paths=paths,
            )
        current_is_transition = bool(
            current is not None
            and current[0]["transition_evidence_selector"]["authorization_ref"][
                "authorization_id"
            ]
            == authorization_id
        )
        if receipt_path.exists() or receipt_path.is_symlink():
            if consumption is None or not current_is_transition:
                raise U10ProvisioningError(
                    "u10_key_receipt_without_selected_transition",
                    authorization_id,
                )
            receipt, _receipt_raw = _read_json_record_v2(
                receipt_path,
                root=paths.ledger_root,
                uid=required_uid,
                mode=0o444,
                code="u10_key_receipt_unreadable",
            )
            receipt = validate_key_receipt_v2(receipt, paths=paths)
            if (
                receipt["authorization_ref"] != authorization_ref
                or receipt["consumption_ref"]["consumption_digest"]
                != consumption["consumption_digest"]
                or receipt["published_selector_ref"] != current[2]
                or receipt["publisher_contract_binding"]
                != consumption["publisher_contract_binding"]
            ):
                raise U10ProvisioningError(
                    "u10_key_receipt_collision", authorization_id
                )
            # Completed replay deliberately ignores a newly supplied publisher;
            # the occurrence remains bound to its original immutable publisher.
            _resolve_selector_chain_v2(paths, uid=required_uid)
            return receipt
        if consumption is not None and (
            consumption["publisher_contract_binding"] != publisher_binding
        ):
            raise U10ProvisioningError(
                "u10_key_recovery_publisher_contract_changed",
                authorization_id,
            )
        if current_is_transition:
            assert current is not None
            actual_prior_ref = current[0]["previous_selector_ref"]
            base = (
                None
                if actual_prior_ref is None
                else _read_selector_ref_v2(
                    actual_prior_ref, paths=paths, uid=required_uid
                )
            )
        else:
            actual_prior_ref = None if current is None else current[2]
            base = current
        if actual_prior_ref != authorization["prior_selector_ref"]:
            raise U10ProvisioningError(
                "u10_key_prior_selector_mismatch",
                f"authorization={authorization['prior_selector_ref']!r}; "
                f"observed={actual_prior_ref!r}",
            )
        base_key = (
            None
            if base is None or base[0]["state"] == "no_active_key"
            else base[0]["key_id"]
        )
        if base_key != authorization["expected_current_key_id"]:
            raise U10ProvisioningError(
                "u10_key_current_mismatch",
                f"expected={authorization['expected_current_key_id']}; "
                f"actual={base_key}",
            )
        mode = authorization["transition_mode"]
        if (
            (mode == "initialize_empty_store" and base is not None)
            or (
                mode == "generate_from_no_active_key"
                and (base is None or base[0]["state"] != "no_active_key")
            )
            or (
                mode in {"rotate_active_key", "revoke_active_key"}
                and (base is None or base[0]["state"] != "active")
            )
        ):
            raise U10ProvisioningError("u10_key_transition_mode_state_mismatch", mode)
        if consumption is None:
            consumption = {
                "schema_version": KEY_CONSUMPTION_SCHEMA,
                "consumption_id": f"consumption.{authorization_id}",
                "record_kind": "key_operation_authorization_consumption",
                "authorization_ref": authorization_ref,
                "prior_selector_ref": authorization["prior_selector_ref"],
                "key_operation": authorization["key_operation"],
                "transition_mode": mode,
                "key_id": authorization["key_id"],
                "occurrence_id": (
                    f"key.{authorization['authorization_digest']['value']}"
                ),
                "publisher_contract_binding": publisher_binding,
                "reserved_at": utc_now(),
                "publication_occurred": False,
                "formal_authority": "none",
                "positive_assurance_allowed": False,
            }
            consumption["consumption_digest"] = sealed_digest(
                consumption, "consumption_digest"
            )
            validate_key_consumption_v2(
                consumption,
                authorization=authorization,
                authorization_raw=authorization_raw,
                paths=paths,
            )
            consumption_raw = _atomic_append_only(
                consumption_path, consumption, mode=0o400
            )
        assert consumption_raw is not None
        consumption_ref = {
            "consumption_id": consumption["consumption_id"],
            "locator": str(consumption_path),
            "artifact_digest": digest_bytes(consumption_raw),
            "consumption_digest": consumption["consumption_digest"],
        }
        evidence_selector = _transition_evidence_selector_v2(
            authorization_ref=authorization_ref,
            consumption_ref=consumption_ref,
            prior_selector_ref=authorization["prior_selector_ref"],
            paths=paths,
        )
        operation = authorization["key_operation"]
        key_id = str(authorization["key_id"])
        public_ref: dict[str, Any] | None = None
        revocation_ref: dict[str, Any] | None = None
        if operation in {"generate", "rotate"}:
            generation_path = paths.generation_root / key_id
            if generation_path.exists() or generation_path.is_symlink():
                _assert_directory(generation_path, uid=required_uid, exact_mode=0o555)
                metadata, metadata_raw = _read_json_record_v2(
                    generation_path / "public-metadata.json",
                    root=paths.key_root,
                    uid=required_uid,
                    mode=0o444,
                    code="u10_key_metadata_unreadable",
                )
                metadata = validate_key_public_metadata_v2(metadata, paths=paths)
                if (
                    metadata["authorization_ref"] != authorization_ref
                    or metadata["consumption_ref"] != consumption_ref
                    or metadata["prior_selector_ref"]
                    != authorization["prior_selector_ref"]
                ):
                    raise U10ProvisioningError("u10_key_generation_collision", key_id)
                _reobserve_private_matches_metadata_v2(
                    metadata, paths=paths, uid=required_uid
                )
            else:
                stage = paths.generation_root / (
                    f".{key_id}.stage."
                    f"{authorization['authorization_digest']['value'][:24]}"
                )
                _safe_remove_tree(stage, uid=required_uid)
                stage.mkdir(mode=0o700)
                if required_uid == 0:
                    os.chown(stage, 0, 0)
                private_type, encoding, private_format, public_format = (
                    _load_cryptography()
                )
                private = private_type.generate()
                no_encryption = __import__(
                    "cryptography.hazmat.primitives.serialization",
                    fromlist=["NoEncryption"],
                ).NoEncryption()
                private_raw = private.private_bytes(
                    encoding.Raw, private_format.Raw, no_encryption
                )
                public_raw = private.public_key().public_bytes(
                    encoding.Raw, public_format.Raw
                )
                if len(private_raw) != 32 or len(public_raw) != 32:
                    raise U10ProvisioningError(
                        "u10_key_raw32_generation_failed", key_id
                    )
                _write_stage_file(stage / "private.ed25519", private_raw, mode=0o600)
                metadata = {
                    "schema_version": KEY_METADATA_SCHEMA,
                    "key_id": key_id,
                    "key_entity_ref": authorization["key_entity_ref"],
                    "record_kind": "signing_key_public_metadata",
                    "algorithm": "Ed25519",
                    "public_key": {
                        "encoding": "raw_base64",
                        "value": base64.b64encode(public_raw).decode("ascii"),
                    },
                    "private_material": {
                        "locator": str(
                            paths.generation_root / key_id / "private.ed25519"
                        ),
                        "storage_state": "root_only_0600_not_exported",
                    },
                    "authorization_ref": authorization_ref,
                    "consumption_ref": consumption_ref,
                    "prior_selector_ref": authorization["prior_selector_ref"],
                    "transition_evidence_selector": evidence_selector,
                    "created_at": utc_now(),
                    "formal_authority": "none",
                    "positive_assurance_allowed": False,
                }
                metadata["metadata_digest"] = sealed_digest(metadata, "metadata_digest")
                validate_key_public_metadata_v2(metadata, paths=paths)
                metadata_raw = json_record_bytes(metadata)
                _write_stage_file(
                    stage / "public-metadata.json", metadata_raw, mode=0o444
                )
                os.chmod(stage, 0o555)
                if required_uid == 0:
                    os.chown(stage, 0, 0)
                _fsync_directory(stage)
                _rename_directory_no_replace(stage, generation_path)
                _fsync_directory(paths.generation_root)
            public_ref = _public_metadata_ref_v2(metadata, metadata_raw, paths=paths)
            _validate_public_metadata_ref_v2(
                public_ref,
                metadata=metadata,
                metadata_raw=metadata_raw,
                paths=paths,
            )
        else:
            revocation_dir = paths.revocation_root / key_id
            revocation_path = revocation_dir / f"{authorization_id}.json"
            if revocation_path.exists() or revocation_path.is_symlink():
                revocation, revocation_raw = _read_json_record_v2(
                    revocation_path,
                    root=paths.key_root,
                    uid=required_uid,
                    mode=0o444,
                    code="u10_key_revocation_unreadable",
                )
                revocation = validate_key_revocation_v2(revocation, paths=paths)
                if (
                    revocation["authorization_ref"] != authorization_ref
                    or revocation["consumption_ref"] != consumption_ref
                    or revocation["prior_selector_ref"]
                    != authorization["prior_selector_ref"]
                ):
                    raise U10ProvisioningError(
                        "u10_key_revocation_collision", authorization_id
                    )
            else:
                revocation = {
                    "schema_version": KEY_REVOCATION_SCHEMA,
                    "revocation_id": f"revocation.{authorization_id}",
                    "record_kind": "signing_key_revocation_occurrence",
                    "key_id": key_id,
                    "key_entity_ref": authorization["key_entity_ref"],
                    "authorization_ref": authorization_ref,
                    "consumption_ref": consumption_ref,
                    "prior_selector_ref": authorization["prior_selector_ref"],
                    "transition_evidence_selector": evidence_selector,
                    "revoked_at": utc_now(),
                    "private_material_disposition": (
                        "retained_root_only_not_exported_pending_retention_policy"
                    ),
                    "formal_authority": "none",
                    "positive_assurance_allowed": False,
                }
                revocation["revocation_digest"] = sealed_digest(
                    revocation, "revocation_digest"
                )
                validate_key_revocation_v2(revocation, paths=paths)
                revocation_raw = json_record_bytes(revocation)
                if not revocation_dir.exists() and not revocation_dir.is_symlink():
                    stage = paths.revocation_root / (
                        f".{key_id}.stage."
                        f"{authorization['authorization_digest']['value'][:24]}"
                    )
                    _safe_remove_tree(stage, uid=required_uid)
                    stage.mkdir(mode=0o700)
                    if required_uid == 0:
                        os.chown(stage, 0, 0)
                    _atomic_append_only(
                        stage / f"{authorization_id}.json",
                        revocation,
                        mode=0o444,
                    )
                    os.chmod(stage, 0o555)
                    _fsync_directory(stage)
                    _rename_directory_no_replace(stage, revocation_dir)
                    _fsync_directory(paths.revocation_root)
                else:
                    _assert_directory(
                        revocation_dir, uid=required_uid, exact_mode=0o555
                    )
                    _atomic_append_only(revocation_path, revocation, mode=0o444)
            revocation_ref = _revocation_ref_v2(revocation, revocation_raw, paths=paths)
            _validate_revocation_ref_v2(
                revocation_ref,
                revocation=revocation,
                revocation_raw=revocation_raw,
                paths=paths,
            )
        existing_pending = current if current_is_transition else pending_history
        selected_at = (
            existing_pending[0]["selected_at"]
            if existing_pending is not None
            else utc_now()
        )
        selector_value = {
            "schema_version": KEY_SELECTOR_SCHEMA,
            "selector_id": f"selector.{authorization_id}",
            "record_kind": "current_signing_key_selector",
            "transition_mode": mode,
            "previous_selector_ref": authorization["prior_selector_ref"],
            "transition_evidence_selector": evidence_selector,
            "state": (
                "active" if operation in {"generate", "rotate"} else "no_active_key"
            ),
            "key_id": key_id if operation in {"generate", "rotate"} else None,
            "key_entity_ref": (
                authorization["key_entity_ref"]
                if operation in {"generate", "rotate"}
                else None
            ),
            "public_metadata_ref": public_ref,
            "revocation_ref": revocation_ref,
            "selected_at": selected_at,
            "formal_authority": "none",
            "positive_assurance_allowed": False,
        }
        selector_value["selector_digest"] = sealed_digest(
            selector_value, "selector_digest"
        )
        validate_key_selector_v2(selector_value, paths=paths)
        if existing_pending is not None:
            if selector_value != existing_pending[0]:
                raise U10ProvisioningError(
                    "u10_key_published_selector_mismatch", authorization_id
                )
            selector_raw = existing_pending[1]
            selector_ref = existing_pending[2]
            if not current_is_transition:
                _atomic_replace(paths.selector_path, selector_raw, mode=0o444)
        else:
            selector_raw, selector_ref = _publish_selector_v2(paths, selector_value)
        observed_current = _load_current_selector_v2(paths, uid=required_uid)
        if (
            observed_current is None
            or observed_current[1] != selector_raw
            or observed_current[2] != selector_ref
        ):
            raise U10ProvisioningError(
                "u10_key_selector_publication_unobserved", authorization_id
            )
        receipt = {
            "schema_version": KEY_RECEIPT_SCHEMA,
            "receipt_id": f"receipt.{authorization_id}",
            "record_kind": "signing_key_operation_occurrence",
            "occurrence_id": consumption["occurrence_id"],
            "authorization_ref": authorization_ref,
            "consumption_ref": consumption_ref,
            "prior_selector_ref": authorization["prior_selector_ref"],
            "published_selector_ref": selector_ref,
            "key_operation": operation,
            "transition_mode": mode,
            "key_id": key_id,
            "public_metadata_ref": public_ref,
            "revocation_ref": revocation_ref,
            "publisher_contract_binding": consumption["publisher_contract_binding"],
            "private_material_evidence": (
                "root_owned_0600_present_not_disclosed"
                if operation in {"generate", "rotate"}
                else "unchanged_not_disclosed"
            ),
            "publication_not_before": consumption["reserved_at"],
            "publication_observed_at": selector_value["selected_at"],
            "receipt_recorded_at": utc_now(),
            "publication_occurred": True,
            "key_state": (
                "active"
                if operation in {"generate", "rotate"}
                else "revoked_no_active_key"
            ),
            "human_adoption_status": "pending",
            "u4_principal_authenticity": "unresolved",
            "formal_authority": "none",
            "positive_assurance_allowed": False,
        }
        receipt["receipt_digest"] = sealed_digest(receipt, "receipt_digest")
        validate_key_receipt_v2(receipt, paths=paths)
        _atomic_append_only(receipt_path, receipt, mode=0o444)
        final_current, final_pending = _resolve_selector_chain_v2(
            paths, uid=required_uid
        )
        if (
            final_pending is not None
            or final_current is None
            or final_current[2] != selector_ref
        ):
            raise U10ProvisioningError(
                "u10_key_transition_final_reread_failed", authorization_id
            )
        return receipt


def _capsule_from_loader() -> bytes:
    raw = globals().get("_U10_INITIAL_CAPSULE_RAW")
    if not isinstance(raw, bytes):
        raise U10ProvisioningError(
            "u10_initial_loader_required", "capsule bytes absent"
        )
    return raw


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) != 2 or arguments[0] not in {
        "observe-runtime-capsule",
        "bootstrap-capsule",
    }:
        raise U10ProvisioningError(
            "u10_provisioner_usage_invalid",
            "expected observe-runtime-capsule|bootstrap-capsule IDENTIFIER; "
            "key operations require fixed dispatcher import",
        )
    operation, authorization_id = arguments
    _require_id(authorization_id, code="u10_authorization_id_invalid")
    if operation == "observe-runtime-capsule":
        execute_runtime_observation_from_capsule(
            _capsule_from_loader(), authorization_id
        )
    else:
        execute_initial_bootstrap_from_capsule(_capsule_from_loader(), authorization_id)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except U10ProvisioningError as exc:
        print(
            json.dumps(
                {"status": "error", "error": {"code": exc.code, "detail": exc.detail}},
                sort_keys=True,
                allow_nan=False,
            ),
            file=sys.stderr,
        )
        raise SystemExit(70) from exc
