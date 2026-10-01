#!/usr/bin/env python3
"""Root-observe the closed U-10 control runtime used with ``-I -B``.

Unlike the broker bootstrap runtime, this runtime intentionally enables its
qualified site packages.  The probe must import the exact control dependencies
and binds every active path and non-OS dyld image to one root-owned runtime
tree.  It never falls back to an unsealed site directory.
"""

from __future__ import annotations

import argparse
import ctypes
import errno
import hashlib
import json
import math
import os
from pathlib import Path
import plistlib
import stat
import subprocess
import sys
from typing import Any


SCHEMA_VERSION = "semantic-guard-u10-control-runtime-manifest/v1"
PROBE_PROFILE = "darwin-control-runtime-site-closure/v1"
SYSTEM_VERSION_PATH = Path("/System/Library/CoreServices/SystemVersion.plist")
OS_ROOTS = (Path("/System/Library"), Path("/usr/lib"))
PROBE_ENV = {"PATH": "", "LC_ALL": "C", "PYTHONDONTWRITEBYTECODE": "1"}

CONTROL_PROBE = r'''
import ctypes
import hashlib
import importlib.metadata
import json
import os
import pathlib
import re
import site
import stat
import sys
import sysconfig

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
        pathlib.Path(path).relative_to(pathlib.Path(root)); return True
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


class ControlRuntimeManifestError(RuntimeError):
    pass


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
    return json.loads(
        raw,
        object_pairs_hook=_strict_json_object,
        parse_constant=_reject_nonfinite_json_constant,
        parse_float=_strict_json_float,
    )


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _digest(raw: bytes) -> dict[str, str]:
    return {"algorithm": "sha256", "value": hashlib.sha256(raw).hexdigest()}


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
        raise ControlRuntimeManifestError(f"extended ACL prohibited: {path}")
    if ctypes.get_errno() != errno.ENOENT:
        raise ControlRuntimeManifestError(f"ACL observation failed: {path}")


def _assert_root_chain(path: Path) -> None:
    current = Path(path.anchor)
    for part in (None, *path.parts[1:]):
        if part is not None:
            current /= part
        observed = current.lstat()
        _assert_no_acl(current)
        if stat.S_ISLNK(observed.st_mode) or observed.st_uid != 0 or observed.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
            raise ControlRuntimeManifestError(f"untrusted runtime path: {current}")


def _read_regular(path: Path) -> bytes:
    before = path.lstat()
    _assert_no_acl(path)
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode) or before.st_uid != 0 or before.st_nlink != 1 or before.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
        raise ControlRuntimeManifestError(f"untrusted runtime file: {path}")
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        opened = os.fstat(descriptor)
        identity = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
        if (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns, opened.st_ctime_ns) != identity:
            raise ControlRuntimeManifestError(f"runtime file changed: {path}")
        chunks = []
        while True:
            block = os.read(descriptor, 1024 * 1024)
            if not block:
                break
            chunks.append(block)
        after = os.fstat(descriptor)
        if (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns) != identity:
            raise ControlRuntimeManifestError(f"runtime file changed: {path}")
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _under(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _probe(interpreter: Path) -> dict[str, Any]:
    completed = subprocess.run(
        [str(interpreter), "-I", "-B", "-c", CONTROL_PROBE],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=PROBE_ENV,
        check=False,
        timeout=60,
        text=True,
    )
    if completed.returncode != 0:
        raise ControlRuntimeManifestError(f"control runtime probe failed: {completed.stderr[:1000]}")
    try:
        value = strict_json_loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise ControlRuntimeManifestError("control runtime probe unreadable") from exc
    if not isinstance(value, dict) or value.get("probe_profile") != PROBE_PROFILE:
        raise ControlRuntimeManifestError("control runtime probe malformed")
    if value.get("probe_execution_identity") != {"effective_uid": 0, "effective_gid": 0}:
        raise ControlRuntimeManifestError("control runtime was not root-observed")
    return value


def _runtime_paths(observation: dict[str, Any]) -> list[Path]:
    paths: list[Path] = []
    for section in (observation["process_image"].values(), observation["python_prefixes"].values(), observation["sys_path"], observation["site_roots"], observation["imported_module_origins"]):
        for item in section:
            if item.get("state") == "present":
                paths.append(Path(item["resolved_locator"]))
    for item in observation["dyld_images"]:
        if item["classification"] == "runtime_tree" and item.get("state") == "present":
            paths.append(Path(item["resolved_locator"]))
    return paths


def _tree_entries(root: Path) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for raw_root, directories, files in os.walk(root, topdown=True, followlinks=False):
        directories.sort()
        files.sort()
        base = Path(raw_root)
        for name in (*directories, *files):
            path = base / name
            observed = path.lstat()
            _assert_no_acl(path)
            relative = path.relative_to(root).as_posix()
            if stat.S_ISLNK(observed.st_mode) or observed.st_uid != 0 or observed.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
                raise ControlRuntimeManifestError(f"untrusted runtime tree entry: {path}")
            if stat.S_ISDIR(observed.st_mode):
                result.append({"path": relative, "kind": "directory", "mode": stat.S_IMODE(observed.st_mode), "uid": observed.st_uid, "gid": observed.st_gid})
            elif stat.S_ISREG(observed.st_mode):
                if observed.st_nlink != 1:
                    raise ControlRuntimeManifestError(
                        f"hard-linked runtime file: {path}"
                    )
                raw = _read_regular(path)
                result.append({"path": relative, "kind": "file", "mode": stat.S_IMODE(observed.st_mode), "uid": observed.st_uid, "gid": observed.st_gid, "size": len(raw), "artifact_digest": _digest(raw)})
            else:
                raise ControlRuntimeManifestError(f"special runtime entry: {path}")
    return result


def build_manifest(interpreter: Path) -> dict[str, Any]:
    interpreter = interpreter.resolve(strict=True)
    observation = _probe(interpreter)
    paths = _runtime_paths(observation)
    if not paths or any(not path.is_absolute() for path in paths):
        raise ControlRuntimeManifestError("control runtime denominator is not absolute")
    runtime_root = Path(os.path.commonpath([str(path) for path in paths]))
    base_prefix = Path(observation["python_prefixes"]["base_prefix"]["resolved_locator"])
    if runtime_root != base_prefix or any(not _under(path, runtime_root) for path in paths):
        raise ControlRuntimeManifestError(f"control runtime escaped one base prefix: {runtime_root}")
    if Path(observation["process_image"]["sys_executable"]["resolved_locator"]) != interpreter:
        raise ControlRuntimeManifestError("control interpreter identity mismatch")
    _assert_root_chain(runtime_root)
    interpreter_raw = _read_regular(interpreter)
    entries = _tree_entries(runtime_root)
    system_raw = _read_regular(SYSTEM_VERSION_PATH)
    system_version = plistlib.loads(system_raw)
    uname = os.uname()
    manifest: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "runtime_id": f"runtime.u10.control.{_digest(_canonical({'entries': entries}))['value']}",
        "runtime_version": observation["runtime_version"],
        "runtime_root": str(runtime_root),
        "runtime_root_uid": 0,
        "runtime_root_gid": runtime_root.lstat().st_gid,
        "runtime_root_mode": stat.S_IMODE(runtime_root.lstat().st_mode),
        "effective_interpreter_locator": str(interpreter),
        "effective_interpreter_artifact_digest": _digest(interpreter_raw),
        "invocation_contract": {"python_flags": ["-I", "-B"], "site_policy": "qualified_closed_site_only_no_fallback/v1", "required_modules": ["cryptography", "jsonschema", "semantic_guard_u10_broker"]},
        "runtime_closure": observation,
        "platform_binding": {"system": uname.sysname, "release": uname.release, "kernel_version": uname.version, "machine": uname.machine, "os_build_artifact": {"locator": str(SYSTEM_VERSION_PATH), "product_build_version": system_version["ProductBuildVersion"], "artifact_digest": _digest(system_raw)}, "binding_profile": "uname_kernel_and_system_version_artifact_exact/v2"},
        "tree_denominator": {"status": "closed", "entry_count": len(entries), "entries": entries, "tree_digest": _digest(_canonical({"entries": entries}))},
        "trust_boundary": {"covered": "root_owned_control_runtime_and_exact_site_dependency_tree", "not_claimed": "root_os_or_hardware_compromise_resistance"},
        "formal_authority": "none",
        "positive_assurance_allowed": False,
    }
    manifest["manifest_digest"] = _digest(_canonical(manifest))
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interpreter", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    manifest = build_manifest(args.interpreter)
    raw = _canonical(manifest) + b"\n"
    descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o400)
    try:
        offset = 0
        while offset < len(raw):
            offset += os.write(descriptor, raw[offset:])
        os.fchmod(descriptor, 0o400)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
