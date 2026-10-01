#!/usr/bin/python3
"""Stdlib-only preflight for the fixed U-10 production control route.

The public wrapper reaches this file with the qualified no-site broker Python.
This verifier resolves the historical initial-bootstrap chain, checks every
fixed control artifact named by that chain, requalifies both runtime closures,
then replaces itself with the dedicated site-enabled control Python.  It never
accepts a caller path, raw JSON value, or inline authority record.
"""

from __future__ import annotations

import ctypes
import errno
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import plistlib
import re
import stat
import subprocess
import sys
from typing import Any


U10_ROOT = Path("/Library/Application Support/semantic-guard/u10")
BOOTSTRAP_ROOT = U10_ROOT / "bootstrap"
PREBOOT_LEDGER_ROOT = Path(
    "/Library/Application Support/semantic-guard/u10-bootstrap-ledger"
)
CONTROL_ENTRYPOINT = BOOTSTRAP_ROOT / "u10_root_control_entrypoint.sh"
CONTROL_OUTER = BOOTSTRAP_ROOT / "u10_root_control_outer_launcher.py"
CONTROL_DISPATCHER = BOOTSTRAP_ROOT / "u10_root_control_dispatcher.py"
SNAPSHOT_STORE_PRODUCER = (
    BOOTSTRAP_ROOT / "u10_snapshot_store_production.py"
)
PROVISIONER = BOOTSTRAP_ROOT / "u10_initial_trust_provisioner.py"
BROKER_OUTER = BOOTSTRAP_ROOT / "u10_root_broker_outer_launcher.py"
PROVENANCE_BINDING = (
    BOOTSTRAP_ROOT / "initial-bootstrap-provenance-binding.json"
)
BROKER_EFFECTIVE_PATH = BOOTSTRAP_ROOT / "effective-python.path"
BROKER_RUNTIME_MANIFEST = (
    BOOTSTRAP_ROOT / "effective-python-runtime-manifest.json"
)
CONTROL_EFFECTIVE_PATH = BOOTSTRAP_ROOT / "control-effective-python.path"
CONTROL_RUNTIME_MANIFEST = (
    BOOTSTRAP_ROOT / "control-python-runtime-manifest.json"
)
SYSTEM_VERSION_PATH = Path(
    "/System/Library/CoreServices/SystemVersion.plist"
)
EXPECTED_ENVIRONMENT = {
    "PATH": "",
    "LC_ALL": "C",
    "PYTHONDONTWRITEBYTECODE": "1",
    "SEMANTIC_GUARD_U10_CONTROL_LAUNCH": (
        "fixed-root-control-wrapper-v1"
    ),
}
FORBIDDEN_ENVIRONMENT_PREFIXES = ("DYLD_", "LD_", "PYTHONHOME", "PYTHONPATH")
ALLOWED_OPERATIONS = frozenset(
    {
        "activate-snapshot",
        "activate-store",
        "key",
        "project-snapshot",
        "revoke-store",
    }
)
IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,255}$")
CONTROL_PROBE_ENVIRONMENT = {
    "PATH": "",
    "LC_ALL": "C",
    "PYTHONDONTWRITEBYTECODE": "1",
}

CONTROL_PROBE = r'''
import ctypes
import importlib.metadata
import json
import os
import pathlib
import re
import site
import sys

EXPECTED_ENV = {"PATH": "", "LC_ALL": "C", "PYTHONDONTWRITEBYTECODE": "1"}
observed = dict(os.environ)
injected = observed.pop("__CF_USER_TEXT_ENCODING", None)
if injected is not None:
    matched = re.fullmatch(r"0x([0-9A-Fa-f]+):0x[0-9A-Fa-f]+:0x[0-9A-Fa-f]+", str(injected))
    if matched is None or int(matched.group(1), 16) != os.geteuid():
        raise RuntimeError("unexpected Darwin environment injection")
if observed != EXPECTED_ENV:
    raise RuntimeError("control probe environment is not closed")
if not (sys.flags.isolated and not sys.flags.no_site and sys.flags.dont_write_bytecode and sys.flags.safe_path):
    raise RuntimeError("control runtime requires -I -B with site enabled")

import cryptography
import jsonschema
import semantic_guard_u10_broker

OS_ROOTS = ("/System/Library", "/usr/lib")
def canonical(raw):
    path = pathlib.Path(str(raw))
    if not path.is_absolute() or path != pathlib.Path(os.path.normpath(str(path))):
        raise RuntimeError("non-canonical path: %r" % (raw,))
    return str(path)
def record(raw):
    locator = canonical(raw)
    path = pathlib.Path(locator)
    return {"locator": locator, "resolved_locator": str(path.resolve(strict=False)), "state": "present" if path.exists() or path.is_symlink() else "absent"}
def under(path, root):
    try:
        pathlib.Path(path).relative_to(root); return True
    except ValueError:
        return False

libc = ctypes.CDLL(None, use_errno=True)
ns = libc._NSGetExecutablePath
ns.argtypes = [ctypes.c_char_p, ctypes.POINTER(ctypes.c_uint32)]
ns.restype = ctypes.c_int
size = ctypes.c_uint32(0); ns(None, ctypes.byref(size))
if size.value <= 1 or size.value > 1024 * 1024: raise RuntimeError("bad executable path size")
buffer = ctypes.create_string_buffer(size.value)
if ns(buffer, ctypes.byref(size)) != 0: raise RuntimeError("_NSGetExecutablePath failed")
count = libc._dyld_image_count; count.argtypes = []; count.restype = ctypes.c_uint32
name = libc._dyld_get_image_name; name.argtypes = [ctypes.c_uint32]; name.restype = ctypes.c_char_p
dyld = []
for index in range(count()):
    raw = name(index)
    if not raw: raise RuntimeError("dyld image without name")
    item = record(os.fsdecode(raw))
    roots = [root for root in OS_ROOTS if under(item["locator"], root) and under(item["resolved_locator"], root)]
    item["classification"] = "excluded_os_asset" if len(roots) == 1 else "runtime_tree"
    item["os_asset_root"] = roots[0] if len(roots) == 1 else None
    dyld.append(item)
dyld.sort(key=lambda item: (item["resolved_locator"], item["locator"]))

sys_path = [record(item) for item in sys.path if item]
if len({item["resolved_locator"] for item in sys_path}) != len(sys_path): raise RuntimeError("duplicate sys.path")
origins = []
for module_name, module in sorted(sys.modules.items()):
    origin = getattr(module, "__file__", None)
    if origin:
        item = record(origin); item["module"] = module_name; origins.append(item)
required = []
for distribution, module_name in (("cryptography", "cryptography"), ("jsonschema", "jsonschema"), ("semantic-guard-vnext", "semantic_guard_u10_broker")):
    module = sys.modules[module_name]
    required.append({"distribution": distribution, "module": module_name, "version": importlib.metadata.version(distribution), "origin": record(module.__file__)})
required.sort(key=lambda item: item["distribution"])
print(json.dumps({
    "probe_profile": "darwin-control-runtime-site-closure/v1",
    "runtime_version": ".".join(map(str, sys.version_info[:3])),
    "probe_execution_identity": {"effective_uid": os.geteuid(), "effective_gid": os.getegid()},
    "process_image": {"sys_executable": record(sys.executable), "ns_get_executable_path": record(os.fsdecode(buffer.value))},
    "python_prefixes": {"prefix": record(sys.prefix), "base_prefix": record(sys.base_prefix)},
    "sys_path": sys_path,
    "site_roots": [record(item) for item in site.getsitepackages()],
    "required_modules": required,
    "imported_module_origins": origins,
    "dyld_images": dyld,
    "os_asset_exclusion": {"profile": "darwin-dyld-system-library-roots-os-build-bound/v1", "allowed_roots": list(OS_ROOTS), "scope": "dyld_images_only", "binding": "exact_platform_binding_and_os_build_artifact"},
}, sort_keys=True, separators=(",", ":"), allow_nan=False))
'''


class ControlOuterError(RuntimeError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _strict_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise json.JSONDecodeError(
                f"duplicate object key: {key!r}", key, 0
            )
        value[key] = item
    return value


def _reject_nonfinite_json_constant(value: str) -> Any:
    raise json.JSONDecodeError(f"non-finite JSON number: {value}", value, 0)


def _strict_json_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise json.JSONDecodeError(
            f"non-finite JSON number: {value}", value, 0
        )
    return parsed


def strict_json_loads(raw: str | bytes | bytearray) -> Any:
    return json.loads(
        raw,
        object_pairs_hook=_strict_json_object,
        parse_constant=_reject_nonfinite_json_constant,
        parse_float=_strict_json_float,
    )


def _digest(raw: bytes) -> dict[str, str]:
    return {"algorithm": "sha256", "value": hashlib.sha256(raw).hexdigest()}


def _sealed(value: dict[str, Any], field: str) -> dict[str, str]:
    material = dict(value)
    material.pop(field, None)
    return _digest(_canonical(material))


def _assert_no_acl(path: Path) -> None:
    if sys.platform != "darwin":
        return
    libc = ctypes.CDLL(None, use_errno=True)
    getter = libc.acl_get_link_np
    getter.argtypes = [ctypes.c_char_p, ctypes.c_int]
    getter.restype = ctypes.c_void_p
    freer = libc.acl_free
    freer.argtypes = [ctypes.c_void_p]
    freer.restype = ctypes.c_int
    ctypes.set_errno(0)
    acl = getter(os.fsencode(path), 0x00000100)
    if acl:
        freer(acl)
        raise ControlOuterError(f"extended ACL prohibited: {path}")
    if ctypes.get_errno() != errno.ENOENT:
        raise ControlOuterError(f"ACL observation failed: {path}")


def _validate_root_chain(path: Path) -> None:
    if not path.is_absolute() or path != Path(os.path.normpath(str(path))):
        raise ControlOuterError(f"non-canonical protected path: {path}")
    current = Path(path.anchor)
    for part in (None, *path.parts[1:-1]):
        if part is not None:
            current /= part
        observed = current.lstat()
        _assert_no_acl(current)
        if (
            stat.S_ISLNK(observed.st_mode)
            or not stat.S_ISDIR(observed.st_mode)
            or observed.st_uid != 0
            or observed.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
        ):
            raise ControlOuterError(f"untrusted protected ancestor: {current}")


def _read_root_file(path: Path, *, exact_mode: int | None = None) -> bytes:
    _validate_root_chain(path)
    before = path.lstat()
    _assert_no_acl(path)
    if (
        stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_uid != 0
        or before.st_gid != 0
        or before.st_nlink != 1
        or before.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
        or (
            exact_mode is not None
            and stat.S_IMODE(before.st_mode) != exact_mode
        )
    ):
        raise ControlOuterError(f"untrusted root file: {path}")
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
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
            raise ControlOuterError(f"root file changed before read: {path}")
        chunks: list[bytes] = []
        while True:
            block = os.read(descriptor, 1024 * 1024)
            if not block:
                break
            chunks.append(block)
        after = os.fstat(descriptor)
        if (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        ) != identity:
            raise ControlOuterError(f"root file changed during read: {path}")
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _json(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = strict_json_loads(raw)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ControlOuterError(f"{label} is unreadable") from exc
    if not isinstance(value, dict):
        raise ControlOuterError(f"{label} is not an object")
    return value


def _one_line_path(path: Path, *, exact_mode: int = 0o400) -> Path:
    raw = _read_root_file(path, exact_mode=exact_mode)
    try:
        text = raw.decode("utf-8")
    except UnicodeError as exc:
        raise ControlOuterError(f"path record is not UTF-8: {path}") from exc
    if not text.endswith("\n") or text.count("\n") != 1 or "\x00" in text:
        raise ControlOuterError(f"path record is not one sealed line: {path}")
    result = Path(text[:-1])
    if (
        not result.is_absolute()
        or result != Path(os.path.normpath(str(result)))
        or Path(os.path.realpath(result)) != result
    ):
        raise ControlOuterError(f"path record is not canonical: {path}")
    return result


def _consume_os_injected_environment() -> None:
    observed = dict(os.environ)
    injected = observed.pop("__CF_USER_TEXT_ENCODING", None)
    if injected is not None:
        matched = re.fullmatch(
            r"0x([0-9A-Fa-f]+):0x[0-9A-Fa-f]+:0x[0-9A-Fa-f]+",
            str(injected),
        )
        if matched is None or int(matched.group(1), 16) != os.geteuid():
            raise ControlOuterError("invalid Darwin environment injection")
        os.environ.pop("__CF_USER_TEXT_ENCODING", None)
    if observed != EXPECTED_ENVIRONMENT:
        raise ControlOuterError("control outer environment denominator mismatch")


def _request(arguments: list[str]) -> tuple[str, str]:
    if len(arguments) != 2:
        raise ControlOuterError("OPERATION IDENTIFIER required")
    operation, identifier = arguments
    if operation not in ALLOWED_OPERATIONS:
        raise ControlOuterError("control operation is not allowed")
    if IDENTIFIER.fullmatch(identifier) is None:
        raise ControlOuterError("control identifier is invalid")
    return operation, identifier


def _validate_startup() -> None:
    if os.geteuid() != 0 or os.getegid() != 0:
        raise ControlOuterError("control outer requires euid/egid 0")
    if not (
        sys.flags.isolated
        and sys.flags.no_site
        and sys.flags.dont_write_bytecode
    ):
        raise ControlOuterError("control outer requires -I -S -B")
    if Path(__file__).absolute() != CONTROL_OUTER or Path(__file__).is_symlink():
        raise ControlOuterError("control outer path is not fixed")
    _consume_os_injected_environment()
    if any(
        name.startswith(FORBIDDEN_ENVIRONMENT_PREFIXES)
        and name != "PYTHONDONTWRITEBYTECODE"
        for name in os.environ
    ):
        raise ControlOuterError("loader or Python environment injection detected")


def _target_file_entry(
    plan: dict[str, Any], relative_path: str, *, expected_role: str | None
) -> dict[str, Any]:
    entries = plan.get("target_denominator", {}).get("entries", [])
    matches = [
        item
        for item in entries
        if item.get("kind") == "file"
        and item.get("relative_path") == relative_path
    ]
    if (
        len(matches) != 1
        or (
            expected_role is not None
            and matches[0].get("role") != expected_role
        )
    ):
        raise ControlOuterError(f"bootstrap target entry missing: {relative_path}")
    return matches[0]


def _verify_target_file(
    plan: dict[str, Any],
    path: Path,
    *,
    role: str | None,
) -> bytes:
    try:
        relative = path.relative_to(U10_ROOT).as_posix()
    except ValueError as exc:
        raise ControlOuterError(f"fixed target escaped U-10 root: {path}") from exc
    entry = _target_file_entry(plan, relative, expected_role=role)
    raw = _read_root_file(path, exact_mode=int(entry["mode"]))
    if (
        entry.get("uid") != 0
        or entry.get("gid") != 0
        or entry.get("artifact_digest") != _digest(raw)
    ):
        raise ControlOuterError(f"bootstrap target artifact mismatch: {path}")
    return raw


def _load_verified_provisioner() -> tuple[Any, dict[str, Any]]:
    binding_raw = _read_root_file(PROVENANCE_BINDING, exact_mode=0o400)
    binding = _json(binding_raw, "bootstrap provenance binding")
    if (
        binding.get("schema_version")
        != "semantic-guard-u10-bootstrap-provenance-binding/v1"
        or binding.get("record_kind")
        != "initial_bootstrap_external_chain_selector"
        or binding.get("preboot_ledger_root") != str(PREBOOT_LEDGER_ROOT)
        or binding.get("binding_digest") != _sealed(binding, "binding_digest")
    ):
        raise ControlOuterError("bootstrap provenance binding mismatch")
    authorization_id = str(binding.get("authorization_id", ""))
    if IDENTIFIER.fullmatch(authorization_id) is None:
        raise ControlOuterError("bootstrap authorization id mismatch")
    expected_names = {
        "authorization_record": f"{authorization_id}.authorization.json",
        "plan_record": f"{authorization_id}.plan.json",
        "consumption_record": f"{authorization_id}.consumption.json",
        "receipt_record": f"{authorization_id}.receipt.json",
    }
    if any(binding.get(field) != name for field, name in expected_names.items()):
        raise ControlOuterError("bootstrap provenance record selection mismatch")
    plan_raw = _read_root_file(
        PREBOOT_LEDGER_ROOT / expected_names["plan_record"], exact_mode=0o400
    )
    authorization_raw = _read_root_file(
        PREBOOT_LEDGER_ROOT / expected_names["authorization_record"],
        exact_mode=0o400,
    )
    plan = _json(plan_raw, "bootstrap plan")
    authorization = _json(authorization_raw, "bootstrap authorization")
    plan_ref = authorization.get("plan_ref", {})
    if (
        plan.get("schema_version")
        != "semantic-guard-u10-bootstrap-provisioning-plan/v1"
        or plan.get("target_root") != str(U10_ROOT)
        or plan.get("plan_digest") != _sealed(plan, "plan_digest")
        or plan.get("plan_id") != binding.get("plan_id")
        or authorization.get("schema_version")
        != "semantic-guard-u10-bootstrap-provisioning-authorization/v1"
        or authorization.get("authorization_id") != authorization_id
        or authorization.get("human_decision") != "accept"
        or authorization.get("decision_owner") != "human"
        or authorization.get("target_root") != str(U10_ROOT)
        or authorization.get("authorization_digest")
        != _sealed(authorization, "authorization_digest")
        or plan_ref.get("artifact_digest") != _digest(plan_raw)
        or plan_ref.get("semantic_digest") != plan.get("plan_digest")
        or plan_ref.get("plan_id") != plan.get("plan_id")
    ):
        raise ControlOuterError("bootstrap authorization/plan chain mismatch")
    provisioner_raw = _verify_target_file(
        plan, PROVISIONER, role="initial_capsule_provisioner"
    )
    specification = importlib.util.spec_from_file_location(
        "_u10_fixed_initial_provisioner", PROVISIONER
    )
    if specification is None or specification.loader is None:
        raise ControlOuterError("fixed provisioner loader unavailable")
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    try:
        specification.loader.exec_module(module)
    except Exception:
        sys.modules.pop(specification.name, None)
        raise
    if _digest(provisioner_raw) != _digest(_read_root_file(PROVISIONER)):
        raise ControlOuterError("fixed provisioner changed during load")
    try:
        chain = module.validate_bootstrap_provenance_chain()
    except Exception as exc:
        raise ControlOuterError(f"bootstrap provenance validation failed: {exc}") from exc
    if chain.get("binding") != binding:
        raise ControlOuterError("bootstrap provenance binding changed")
    return module, chain


def _validate_fixed_control_artifacts(
    chain: dict[str, Any],
) -> dict[str, bytes]:
    plan = chain["plan"]
    expected = {
        "root_control_entrypoint": CONTROL_ENTRYPOINT,
        "root_control_outer": CONTROL_OUTER,
        "root_control_dispatcher": CONTROL_DISPATCHER,
        "snapshot_store_producer": SNAPSHOT_STORE_PRODUCER,
    }
    result = {
        role: _verify_target_file(plan, path, role=role)
        for role, path in expected.items()
    }
    result["initial_capsule_provisioner"] = _verify_target_file(
        plan, PROVISIONER, role="initial_capsule_provisioner"
    )
    result["broker_outer_launcher"] = _verify_target_file(
        plan, BROKER_OUTER, role=None
    )
    return result


def _load_module(path: Path, name: str) -> Any:
    specification = importlib.util.spec_from_file_location(name, path)
    if specification is None or specification.loader is None:
        raise ControlOuterError(f"module loader unavailable: {path}")
    module = importlib.util.module_from_spec(specification)
    sys.modules[name] = module
    try:
        specification.loader.exec_module(module)
    except Exception:
        sys.modules.pop(name, None)
        raise
    return module


def _validate_broker_runtime(
    chain: dict[str, Any], fixed_artifacts: dict[str, bytes]
) -> None:
    helper = _load_module(BROKER_OUTER, "_u10_broker_runtime_validator")
    if _digest(fixed_artifacts["broker_outer_launcher"]) != _digest(
        _read_root_file(BROKER_OUTER)
    ):
        raise ControlOuterError("broker outer changed during load")
    interpreter = _one_line_path(BROKER_EFFECTIVE_PATH)
    if Path(os.path.realpath(sys.executable)) != interpreter:
        raise ControlOuterError("control outer broker interpreter mismatch")
    raw = _read_root_file(BROKER_RUNTIME_MANIFEST, exact_mode=0o400)
    manifest = _json(raw, "broker runtime manifest")
    runtime_ref = chain["plan"]["runtime_bindings"]["broker"]
    receipt = chain["receipt"]
    if (
        manifest.get("schema_version")
        != "semantic-guard-u10-bootstrap-runtime-manifest/v1"
        or manifest.get("manifest_digest") != _sealed(manifest, "manifest_digest")
        or manifest.get("manifest_digest")
        != runtime_ref.get("expected_manifest_digest")
        or manifest.get("manifest_digest")
        != receipt.get("broker_runtime_manifest_digest")
        or manifest.get("effective_interpreter_locator") != str(interpreter)
        or manifest.get("effective_interpreter_artifact_digest")
        != _digest(_read_root_file(interpreter))
        or runtime_ref.get("effective_interpreter_locator") != str(interpreter)
        or runtime_ref.get("effective_interpreter_artifact_digest")
        != manifest.get("effective_interpreter_artifact_digest")
    ):
        raise ControlOuterError("broker runtime binding mismatch")
    observed_closure = helper._probe_bootstrap_runtime(interpreter)
    if observed_closure != manifest.get("runtime_closure"):
        raise ControlOuterError("broker runtime closure changed")
    root = helper._derive_runtime_root(observed_closure)
    entries = helper._host_runtime_tree_entries(root)
    denominator = manifest.get("tree_denominator", {})
    if (
        root != Path(str(manifest.get("runtime_root", "")))
        or denominator.get("status") != "closed"
        or denominator.get("entry_count") != len(entries)
        or denominator.get("entries") != entries
        or denominator.get("tree_digest")
        != _digest(_canonical({"entries": entries}))
    ):
        raise ControlOuterError("broker runtime denominator changed")
    if [str(Path(item)) for item in sys.path] != [
        item["locator"] for item in observed_closure["sys_path"]
    ]:
        raise ControlOuterError("running broker sys.path changed")
    allowed_external = {CONTROL_OUTER, PROVISIONER, BROKER_OUTER}
    for name, module in sys.modules.items():
        origin = getattr(module, "__file__", None)
        if origin is None or name == "__main__":
            continue
        resolved = Path(os.path.realpath(origin))
        try:
            resolved.relative_to(root)
        except ValueError:
            if resolved not in allowed_external:
                raise ControlOuterError(
                    f"running broker module escaped closure: {name}: {resolved}"
                )


def _control_tree_entries(root: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for raw_root, directories, files in os.walk(
        root, topdown=True, followlinks=False
    ):
        directories.sort()
        files.sort()
        base = Path(raw_root)
        for name in (*directories, *files):
            path = base / name
            observed = path.lstat()
            _assert_no_acl(path)
            if (
                stat.S_ISLNK(observed.st_mode)
                or observed.st_uid != 0
                or observed.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
            ):
                raise ControlOuterError(f"untrusted control runtime entry: {path}")
            common = {
                "path": path.relative_to(root).as_posix(),
                "mode": stat.S_IMODE(observed.st_mode),
                "uid": observed.st_uid,
                "gid": observed.st_gid,
            }
            if stat.S_ISDIR(observed.st_mode):
                entries.append({**common, "kind": "directory"})
            elif stat.S_ISREG(observed.st_mode):
                if observed.st_nlink != 1:
                    raise ControlOuterError(f"hard-linked control file: {path}")
                raw = _read_root_file(path)
                entries.append(
                    {
                        **common,
                        "kind": "file",
                        "size": len(raw),
                        "artifact_digest": _digest(raw),
                    }
                )
            else:
                raise ControlOuterError(f"special control runtime entry: {path}")
    return entries


def _probe_control_runtime(interpreter: Path) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            [str(interpreter), "-I", "-B", "-c", CONTROL_PROBE],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=CONTROL_PROBE_ENVIRONMENT,
            check=False,
            timeout=60,
            text=True,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ControlOuterError("control runtime probe failed") from exc
    if completed.returncode != 0:
        raise ControlOuterError(
            "control runtime probe failed: " + completed.stderr[:1000]
        )
    try:
        value = strict_json_loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise ControlOuterError("control runtime probe unreadable") from exc
    if not isinstance(value, dict):
        raise ControlOuterError("control runtime probe malformed")
    return value


def _validate_control_runtime(chain: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    interpreter = _one_line_path(CONTROL_EFFECTIVE_PATH)
    raw = _read_root_file(CONTROL_RUNTIME_MANIFEST, exact_mode=0o400)
    manifest = _json(raw, "control runtime manifest")
    runtime_ref = chain["plan"]["runtime_bindings"]["control"]
    receipt = chain["receipt"]
    if (
        set(manifest)
        != {
            "schema_version", "runtime_id", "runtime_version", "runtime_root",
            "runtime_root_uid", "runtime_root_gid", "runtime_root_mode",
            "effective_interpreter_locator", "effective_interpreter_artifact_digest",
            "invocation_contract", "runtime_closure", "platform_binding",
            "tree_denominator", "trust_boundary", "formal_authority",
            "positive_assurance_allowed", "manifest_digest",
        }
        or manifest.get("schema_version")
        != "semantic-guard-u10-control-runtime-manifest/v1"
        or manifest.get("manifest_digest") != _sealed(manifest, "manifest_digest")
        or manifest.get("manifest_digest")
        != runtime_ref.get("expected_manifest_digest")
        or manifest.get("manifest_digest")
        != receipt.get("control_runtime_manifest_digest")
        or manifest.get("effective_interpreter_locator") != str(interpreter)
        or runtime_ref.get("effective_interpreter_locator") != str(interpreter)
        or manifest.get("invocation_contract")
        != {
            "python_flags": ["-I", "-B"],
            "site_policy": "qualified_closed_site_only_no_fallback/v1",
            "required_modules": [
                "cryptography", "jsonschema", "semantic_guard_u10_broker"
            ],
        }
        or manifest.get("formal_authority") != "none"
        or manifest.get("positive_assurance_allowed") is not False
    ):
        raise ControlOuterError("control runtime manifest contract mismatch")
    interpreter_raw = _read_root_file(interpreter)
    if (
        manifest.get("effective_interpreter_artifact_digest")
        != _digest(interpreter_raw)
        or runtime_ref.get("effective_interpreter_artifact_digest")
        != _digest(interpreter_raw)
    ):
        raise ControlOuterError("control interpreter digest mismatch")
    observed = _probe_control_runtime(interpreter)
    if observed != manifest.get("runtime_closure"):
        raise ControlOuterError("control runtime closure changed")
    root = Path(str(manifest.get("runtime_root", "")))
    paths: list[Path] = []
    for section in (
        observed["process_image"].values(),
        observed["python_prefixes"].values(),
        observed["sys_path"],
        observed["site_roots"],
        observed["imported_module_origins"],
    ):
        for item in section:
            if item.get("state") == "present":
                paths.append(Path(item["resolved_locator"]))
    paths.extend(
        Path(item["resolved_locator"])
        for item in observed["dyld_images"]
        if item.get("classification") == "runtime_tree"
        and item.get("state") == "present"
    )
    try:
        derived_root = Path(os.path.commonpath([str(path) for path in paths]))
    except (TypeError, ValueError) as exc:
        raise ControlOuterError("control runtime has no closed root") from exc
    if (
        not paths
        or root != derived_root
        or root != Path(observed["python_prefixes"]["base_prefix"]["resolved_locator"])
        or any(not path.is_relative_to(root) for path in paths)
    ):
        raise ControlOuterError("control runtime escaped one root")
    _validate_root_chain(root / ".runtime-root-sentinel")
    root_observed = root.lstat()
    if (
        root_observed.st_uid != manifest.get("runtime_root_uid")
        or root_observed.st_gid != manifest.get("runtime_root_gid")
        or stat.S_IMODE(root_observed.st_mode)
        != manifest.get("runtime_root_mode")
    ):
        raise ControlOuterError("control runtime root binding changed")
    entries = _control_tree_entries(root)
    denominator = manifest.get("tree_denominator", {})
    if (
        denominator.get("status") != "closed"
        or denominator.get("entry_count") != len(entries)
        or denominator.get("entries") != entries
        or denominator.get("tree_digest")
        != _digest(_canonical({"entries": entries}))
    ):
        raise ControlOuterError("control runtime denominator changed")
    system_raw = _read_root_file(SYSTEM_VERSION_PATH)
    try:
        system_version = plistlib.loads(system_raw)
    except plistlib.InvalidFileException as exc:
        raise ControlOuterError("SystemVersion.plist unreadable") from exc
    uname = os.uname()
    expected_platform = {
        "system": uname.sysname,
        "release": uname.release,
        "kernel_version": uname.version,
        "machine": uname.machine,
        "os_build_artifact": {
            "locator": str(SYSTEM_VERSION_PATH),
            "product_build_version": system_version.get("ProductBuildVersion"),
            "artifact_digest": _digest(system_raw),
        },
        "binding_profile": "uname_kernel_and_system_version_artifact_exact/v2",
    }
    if manifest.get("platform_binding") != expected_platform:
        raise ControlOuterError("control runtime platform changed")
    return interpreter, manifest


def main(argv: list[str] | None = None) -> int:
    _validate_startup()
    request = list(sys.argv[1:] if argv is None else argv)
    _request(request)
    _provisioner, chain = _load_verified_provisioner()
    fixed = _validate_fixed_control_artifacts(chain)
    _validate_broker_runtime(chain, fixed)
    control_python, control_manifest = _validate_control_runtime(chain)
    os.umask(0o077)
    environment = {
        "PATH": "",
        "LC_ALL": "C",
        "PYTHONDONTWRITEBYTECODE": "1",
        "SEMANTIC_GUARD_U10_CONTROL_VERIFIED": "fixed-control-outer-v1",
        "SEMANTIC_GUARD_U10_BOOTSTRAP_BINDING_DIGEST": chain["binding"][
            "binding_digest"
        ]["value"],
        "SEMANTIC_GUARD_U10_CONTROL_RUNTIME_MANIFEST_DIGEST": control_manifest[
            "manifest_digest"
        ]["value"],
    }
    os.execve(
        str(control_python),
        [
            str(control_python),
            "-I",
            "-B",
            str(CONTROL_DISPATCHER),
            *request,
        ],
        environment,
    )
    raise ControlOuterError("control execve returned unexpectedly")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ControlOuterError, OSError, KeyError, TypeError, ValueError) as exc:
        print(f"U-10 root control outer failed: {exc}", file=sys.stderr)
        raise SystemExit(70)
