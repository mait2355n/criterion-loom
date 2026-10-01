#!/usr/bin/env python3
"""Generate a candidate-only closed manifest for the U-10 bootstrap Python.

The result describes current root-owned host material.  It does not install,
adopt, or activate that material.  A separately authorized privileged
provisioning step must place and re-observe the exact manifest and bootstrap
artifacts under the fixed U-10 root.
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


SCHEMA_VERSION = "semantic-guard-u10-bootstrap-runtime-manifest/v1"
SYSTEM_VERSION_PATH = Path("/System/Library/CoreServices/SystemVersion.plist")
RUNTIME_CLOSURE_PROFILE = "darwin-executed-image-common-root-closure/v1"
OS_ASSET_EXCLUSION_PROFILE = (
    "darwin-dyld-system-library-roots-os-build-bound/v1"
)
OS_ASSET_ROOTS = (Path("/System/Library"), Path("/usr/lib"))
PROBE_ENVIRONMENT = {"PATH": "", "LC_ALL": "C", "PYTHONDONTWRITEBYTECODE": "1"}

# This probe is deliberately self-contained and Python 3.9 compatible.  The
# generator and both runtime verifiers execute the same profile under the
# selected interpreter.  The result, rather than a caller-provided directory,
# determines the only permissible runtime root.
RUNTIME_PROBE = r'''
import ctypes
import datetime
import errno
import hashlib
import json
import os
import pathlib
import plistlib
import re
import site
import stat
import sys
import sysconfig
import typing

OS_ROOTS = ("/System/Library", "/usr/lib")
EXPECTED_ENVIRONMENT = {"PATH": "", "LC_ALL": "C", "PYTHONDONTWRITEBYTECODE": "1"}

observed_environment = dict(os.environ)
injected = observed_environment.pop("__CF_USER_TEXT_ENCODING", None)
if injected is not None:
    matched = re.fullmatch(
        r"0x([0-9A-Fa-f]+):0x[0-9A-Fa-f]+:0x[0-9A-Fa-f]+", str(injected)
    )
    if matched is None or int(matched.group(1), 16) != os.geteuid():
        raise RuntimeError("unexpected Darwin environment injection")
if observed_environment != EXPECTED_ENVIRONMENT:
    raise RuntimeError("runtime probe environment is not closed")

def canonical(raw):
    path = pathlib.Path(str(raw))
    if not path.is_absolute() or path != pathlib.Path(os.path.normpath(str(path))):
        raise RuntimeError("non-canonical probe path: %r" % (raw,))
    return str(path)

def record(raw):
    locator = canonical(raw)
    path = pathlib.Path(locator)
    if path.exists() or path.is_symlink():
        state = "present"
    else:
        state = "absent"
    return {
        "locator": locator,
        "resolved_locator": str(path.resolve(strict=False)),
        "state": state,
    }

def under(path, root):
    try:
        pathlib.Path(path).relative_to(pathlib.Path(root))
        return True
    except ValueError:
        return False

libc = ctypes.CDLL(None, use_errno=True)
ns_get_executable_path = libc._NSGetExecutablePath
ns_get_executable_path.argtypes = [ctypes.c_char_p, ctypes.POINTER(ctypes.c_uint32)]
ns_get_executable_path.restype = ctypes.c_int
size = ctypes.c_uint32(0)
ns_get_executable_path(None, ctypes.byref(size))
if size.value <= 1 or size.value > 1024 * 1024:
    raise RuntimeError("invalid _NSGetExecutablePath size")
buffer = ctypes.create_string_buffer(size.value)
if ns_get_executable_path(buffer, ctypes.byref(size)) != 0:
    raise RuntimeError("_NSGetExecutablePath failed")

dyld_image_count = libc._dyld_image_count
dyld_image_count.argtypes = []
dyld_image_count.restype = ctypes.c_uint32
dyld_get_image_name = libc._dyld_get_image_name
dyld_get_image_name.argtypes = [ctypes.c_uint32]
dyld_get_image_name.restype = ctypes.c_char_p
dyld = []
for index in range(dyld_image_count()):
    raw_name = dyld_get_image_name(index)
    if not raw_name:
        raise RuntimeError("dyld image without a name")
    item = record(os.fsdecode(raw_name))
    matching_roots = [
        root for root in OS_ROOTS
        if under(item["locator"], root) and under(item["resolved_locator"], root)
    ]
    if len(matching_roots) == 1:
        item["classification"] = "excluded_os_asset"
        item["os_asset_root"] = matching_roots[0]
    else:
        item["classification"] = "runtime_tree"
        item["os_asset_root"] = None
    dyld.append(item)
dyld.sort(key=lambda item: (item["resolved_locator"], item["locator"]))
if len({(item["locator"], item["resolved_locator"]) for item in dyld}) != len(dyld):
    raise RuntimeError("duplicate dyld image")

sys_path = [record(item) for item in sys.path]
if len({item["locator"] for item in sys_path}) != len(sys_path):
    raise RuntimeError("duplicate sys.path entry")

stdlib_roots = []
for name in ("stdlib", "platstdlib"):
    item = record(sysconfig.get_path(name))
    item["kind"] = name
    stdlib_roots.append(item)
stdlib_roots.sort(key=lambda item: item["kind"])

site_values = []
for source, value in (
    ("site.getsitepackages", item) for item in site.getsitepackages()
):
    site_values.append((source, value))
for name in ("purelib", "platlib"):
    site_values.append(("sysconfig.%s" % name, sysconfig.get_path(name)))
active_sys_path = {item["resolved_locator"] for item in sys_path}
site_roots = []
for source, value in site_values:
    item = record(value)
    item["source"] = source
    item["active"] = item["resolved_locator"] in active_sys_path
    item["disposition"] = (
        "runtime_tree" if item["active"] else "suppressed_by_isolated_no_site"
    )
    site_roots.append(item)
site_roots.sort(key=lambda item: (item["resolved_locator"], item["source"]))

module_origins = []
for name, module in sorted(sys.modules.items()):
    if name == "__main__":
        continue
    origin = getattr(module, "__file__", None)
    if origin is None:
        continue
    item = record(origin)
    item["module"] = name
    module_origins.append(item)

result = {
    "probe_profile": "darwin-executed-image-common-root-closure/v1",
    "runtime_version": ".".join(map(str, sys.version_info[:3])),
    "probe_execution_identity": {
        "effective_uid": os.geteuid(),
        "effective_gid": os.getegid(),
    },
    "process_image": {
        "sys_executable": record(sys.executable),
        "ns_get_executable_path": record(os.fsdecode(buffer.value)),
    },
    "python_prefixes": {
        "prefix": record(sys.prefix),
        "base_prefix": record(sys.base_prefix),
    },
    "sys_path": sys_path,
    "stdlib_roots": stdlib_roots,
    "site_roots": site_roots,
    "site_policy": "isolated_no_site_only_active_paths_enter_runtime_closure/v1",
    "imported_module_origins": module_origins,
    "dyld_images": dyld,
    "os_asset_exclusion": {
        "profile": "darwin-dyld-system-library-roots-os-build-bound/v1",
        "allowed_roots": list(OS_ROOTS),
        "scope": "dyld_images_only",
        "binding": "exact_platform_binding_and_os_build_artifact",
    },
}
print(json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False))
'''


class BootstrapManifestError(RuntimeError):
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
        raise BootstrapManifestError(f"extended ACL is prohibited: {path}")
    observed_errno = ctypes.get_errno()
    if observed_errno != errno.ENOENT:
        raise BootstrapManifestError(
            f"extended ACL could not be observed: {path}: errno={observed_errno}"
        )


def _assert_root_chain(path: Path) -> None:
    if not path.is_absolute() or path != Path(os.path.normpath(str(path))):
        raise BootstrapManifestError(f"non-canonical absolute path: {path}")
    current = Path(path.anchor)
    for part in (None, *path.parts[1:]):
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
            raise BootstrapManifestError(f"untrusted runtime ancestor: {current}")


def _read_regular(path: Path) -> tuple[bytes, os.stat_result]:
    before = path.lstat()
    _assert_no_acl(path)
    if (
        stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_uid != 0
        or before.st_nlink != 1
        or before.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
    ):
        raise BootstrapManifestError(f"untrusted runtime file: {path}")
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
            raise BootstrapManifestError(f"runtime file changed: {path}")
        chunks: list[bytes] = []
        while block := os.read(descriptor, 1024 * 1024):
            chunks.append(block)
        after = os.fstat(descriptor)
        if (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        ) != identity:
            raise BootstrapManifestError(f"runtime file changed: {path}")
    finally:
        os.close(descriptor)
    return b"".join(chunks), before


def _tree_entries(root: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for raw_directory, directory_names, file_names in os.walk(
        root, topdown=True, followlinks=False
    ):
        base = Path(raw_directory)
        directory_names.sort()
        file_names.sort()
        for name in (*directory_names, *file_names):
            path = base / name
            observed = path.lstat()
            _assert_no_acl(path)
            relative = path.relative_to(root).as_posix()
            common = {
                "path": relative,
                "mode": stat.S_IMODE(observed.st_mode),
                "uid": observed.st_uid,
                "gid": observed.st_gid,
            }
            if observed.st_uid != 0:
                raise BootstrapManifestError(f"non-root runtime entry: {path}")
            if stat.S_ISLNK(observed.st_mode):
                target = os.readlink(path)
                resolved = Path(os.path.realpath(path))
                try:
                    resolved.relative_to(root)
                except ValueError as exc:
                    raise BootstrapManifestError(
                        f"runtime symlink escapes denominator: {path} -> {target}"
                    ) from exc
                entries.append({**common, "kind": "symlink", "target": target})
            elif stat.S_ISDIR(observed.st_mode):
                if observed.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
                    raise BootstrapManifestError(f"mutable runtime directory: {path}")
                entries.append({**common, "kind": "directory"})
            elif stat.S_ISREG(observed.st_mode):
                raw, stable = _read_regular(path)
                entries.append(
                    {
                        **common,
                        "kind": "file",
                        "size": stable.st_size,
                        "artifact_digest": _digest(raw),
                    }
                )
            else:
                raise BootstrapManifestError(f"special runtime entry: {path}")
    entries.sort(key=lambda item: str(item["path"]))
    paths = [str(item["path"]) for item in entries]
    if len(paths) != len(set(paths)):
        raise BootstrapManifestError("duplicate runtime paths")
    return entries


def _is_under(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _runtime_inclusion_paths(observation: dict[str, Any]) -> list[Path]:
    records = [
        observation["process_image"]["sys_executable"],
        observation["process_image"]["ns_get_executable_path"],
        observation["python_prefixes"]["prefix"],
        observation["python_prefixes"]["base_prefix"],
    ]
    records.extend(observation["sys_path"])
    records.extend(observation["stdlib_roots"])
    records.extend(
        item
        for item in observation["site_roots"]
        if item["active"] is True
    )
    records.extend(observation["imported_module_origins"])
    records.extend(
        item
        for item in observation["dyld_images"]
        if item["classification"] == "runtime_tree"
    )
    return [
        Path(item[field])
        for item in records
        for field in ("locator", "resolved_locator")
    ]


def _derive_runtime_root(observation: dict[str, Any]) -> Path:
    if observation.get("probe_profile") != RUNTIME_CLOSURE_PROFILE:
        raise BootstrapManifestError("runtime closure probe profile mismatch")
    if observation.get("probe_execution_identity") != {
        "effective_uid": 0,
        "effective_gid": 0,
    }:
        raise BootstrapManifestError(
            "bootstrap runtime closure must be observed as effective uid/gid 0"
        )
    exclusion = observation.get("os_asset_exclusion")
    expected_exclusion = {
        "profile": OS_ASSET_EXCLUSION_PROFILE,
        "allowed_roots": [str(path) for path in OS_ASSET_ROOTS],
        "scope": "dyld_images_only",
        "binding": "exact_platform_binding_and_os_build_artifact",
    }
    if exclusion != expected_exclusion:
        raise BootstrapManifestError("runtime OS exclusion policy mismatch")
    dyld = observation.get("dyld_images")
    if not isinstance(dyld, list) or not dyld:
        raise BootstrapManifestError("runtime dyld denominator is empty")
    for item in dyld:
        locator = Path(str(item.get("locator", "")))
        resolved = Path(str(item.get("resolved_locator", "")))
        classification = item.get("classification")
        if classification == "excluded_os_asset":
            root = Path(str(item.get("os_asset_root", "")))
            if root not in OS_ASSET_ROOTS or not (
                _is_under(locator, root) and _is_under(resolved, root)
            ):
                raise BootstrapManifestError("invalid excluded OS dyld image")
        elif classification == "runtime_tree":
            if item.get("os_asset_root") is not None:
                raise BootstrapManifestError("non-OS dyld image has OS root")
        else:
            raise BootstrapManifestError("unknown dyld image classification")
    inclusion_paths = _runtime_inclusion_paths(observation)
    if not inclusion_paths or any(not path.is_absolute() for path in inclusion_paths):
        raise BootstrapManifestError("runtime closure contains a non-absolute path")
    try:
        derived = Path(os.path.commonpath([str(path) for path in inclusion_paths]))
    except ValueError as exc:
        raise BootstrapManifestError("runtime closure has no common root") from exc
    if not derived.is_dir() or Path(os.path.realpath(derived)) != derived:
        raise BootstrapManifestError(
            f"derived runtime root is not a canonical directory: {derived}"
        )
    if any(not _is_under(path, derived) for path in inclusion_paths):
        raise BootstrapManifestError("runtime closure escaped derived root")
    prefix = Path(observation["python_prefixes"]["prefix"]["resolved_locator"])
    base_prefix = Path(
        observation["python_prefixes"]["base_prefix"]["resolved_locator"]
    )
    if prefix != base_prefix or derived != base_prefix:
        raise BootstrapManifestError(
            "execution-derived common root is not the isolated base_prefix: "
            f"derived={derived}; prefix={prefix}; base_prefix={base_prefix}"
        )
    return derived


def _probe_interpreter(interpreter: Path) -> tuple[str, Path, dict[str, Any]]:
    try:
        completed = subprocess.run(
            [str(interpreter), "-I", "-S", "-B", "-c", RUNTIME_PROBE],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
            env=PROBE_ENVIRONMENT,
            text=True,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise BootstrapManifestError("effective interpreter probe failed") from exc
    if completed.returncode != 0:
        raise BootstrapManifestError(
            f"effective interpreter probe failed: {completed.stderr[:1000]}"
        )
    try:
        value = strict_json_loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise BootstrapManifestError("effective interpreter probe unreadable") from exc
    if not isinstance(value, dict):
        raise BootstrapManifestError("effective interpreter probe malformed")
    process_image = value.get("process_image")
    if not isinstance(process_image, dict):
        raise BootstrapManifestError("effective interpreter process image missing")
    probed = Path(
        str(process_image.get("sys_executable", {}).get("resolved_locator", ""))
    )
    runtime_version = value.get("runtime_version")
    if not isinstance(runtime_version, str) or not runtime_version:
        raise BootstrapManifestError("runtime version probe missing")
    return runtime_version, probed, value


def build_manifest(
    interpreter: Path, *, expected_runtime_root: Path | None = None
) -> dict[str, Any]:
    interpreter = interpreter.resolve(strict=True)
    runtime_version, probed_interpreter, runtime_closure = _probe_interpreter(
        interpreter
    )
    runtime_root = _derive_runtime_root(runtime_closure)
    if expected_runtime_root is not None:
        expected = expected_runtime_root.resolve(strict=True)
        if expected != runtime_root:
            raise BootstrapManifestError(
                "caller runtime root is not the execution-derived runtime root: "
                f"expected={expected}; derived={runtime_root}"
            )
    _assert_root_chain(runtime_root)
    try:
        interpreter.relative_to(runtime_root)
    except ValueError as exc:
        raise BootstrapManifestError("interpreter is outside runtime root") from exc
    interpreter_raw, _interpreter_stat = _read_regular(interpreter)
    if probed_interpreter != interpreter:
        raise BootstrapManifestError("effective interpreter probe identity mismatch")
    root_stat = runtime_root.lstat()
    entries = _tree_entries(runtime_root)
    tree_digest = _digest(_canonical({"entries": entries}))
    uname = os.uname()
    _assert_root_chain(SYSTEM_VERSION_PATH.parent)
    system_version_raw, _system_version_stat = _read_regular(SYSTEM_VERSION_PATH)
    try:
        system_version = plistlib.loads(system_version_raw)
    except plistlib.InvalidFileException as exc:
        raise BootstrapManifestError("SystemVersion.plist is unreadable") from exc
    product_build_version = system_version.get("ProductBuildVersion")
    if not isinstance(product_build_version, str) or not product_build_version:
        raise BootstrapManifestError("ProductBuildVersion is unavailable")
    manifest: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "runtime_id": f"runtime.u10.bootstrap.{tree_digest['value']}",
        "runtime_version": runtime_version,
        "runtime_root": str(runtime_root),
        "runtime_root_mode": stat.S_IMODE(root_stat.st_mode),
        "runtime_root_uid": root_stat.st_uid,
        "runtime_root_gid": root_stat.st_gid,
        "effective_interpreter_locator": str(interpreter),
        "runtime_closure": runtime_closure,
        "platform_binding": {
            "system": uname.sysname,
            "release": uname.release,
            "kernel_version": uname.version,
            "machine": uname.machine,
            "os_build_artifact": {
                "locator": str(SYSTEM_VERSION_PATH),
                "product_build_version": product_build_version,
                "artifact_digest": _digest(system_version_raw),
            },
            "binding_profile": (
                "uname_kernel_and_system_version_artifact_exact/v2"
            ),
        },
        "tree_denominator": {
            "status": "closed",
            "entry_count": len(entries),
            "entries": entries,
            "tree_digest": tree_digest,
        },
        "trust_boundary": {
            "covered": "root_owned_runtime_tree_resistant_to_non_root_tampering",
            "not_claimed": "root_or_os_compromise_resistance",
        },
        "formal_authority": "none",
        "positive_assurance_allowed": False,
        "effective_interpreter_artifact_digest": _digest(interpreter_raw),
    }
    # Redundant with the tree entry, but useful for reviewing the exact image
    # selected by the fixed path file.
    manifest["manifest_digest"] = _digest(_canonical(manifest))
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--runtime-root",
        type=Path,
        help=(
            "optional expected root; it is checked against, and never overrides, "
            "the root derived from the executed interpreter"
        ),
    )
    parser.add_argument("--interpreter", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    manifest = build_manifest(
        arguments.interpreter, expected_runtime_root=arguments.runtime_root
    )
    raw = _canonical(manifest) + b"\n"
    if arguments.output.exists() or arguments.output.is_symlink():
        raise BootstrapManifestError(f"output exists: {arguments.output}")
    descriptor = os.open(
        arguments.output,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
        0o400,
    )
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
