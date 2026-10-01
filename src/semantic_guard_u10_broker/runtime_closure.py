"""Runtime-closure verification for the U-10 broker."""

from __future__ import annotations

from collections.abc import Mapping
import ctypes
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
from typing import Any

from .darwin_acl import assert_no_extended_acl
from .protected_io import (
    U10_ROOT,
    BrokerBoundaryError,
    digest_bytes,
    read_protected_file,
    strict_json_loads,
    validate_directory_chain,
)


_RUNTIME_CLOSURE_PROFILE = "darwin-executed-image-common-root-closure/v1"
_RUNTIME_OS_EXCLUSION_PROFILE = "darwin-dyld-system-library-roots-os-build-bound/v1"
_RUNTIME_OS_ASSET_ROOTS = (Path("/System/Library"), Path("/usr/lib"))
_RUNTIME_PROBE_ENVIRONMENT = {
    "PATH": "",
    "LC_ALL": "C",
    "PYTHONDONTWRITEBYTECODE": "1",
}
_RUNTIME_PROBE = r"""
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
    matched = re.fullmatch(r"0x([0-9A-Fa-f]+):0x[0-9A-Fa-f]+:0x[0-9A-Fa-f]+", str(injected))
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
    state = "present" if path.exists() or path.is_symlink() else "absent"
    return {"locator": locator, "resolved_locator": str(path.resolve(strict=False)), "state": state}
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
    matching_roots = [root for root in OS_ROOTS if under(item["locator"], root) and under(item["resolved_locator"], root)]
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
site_values = [("site.getsitepackages", item) for item in site.getsitepackages()]
for name in ("purelib", "platlib"):
    site_values.append(("sysconfig.%s" % name, sysconfig.get_path(name)))
active_sys_path = {item["resolved_locator"] for item in sys_path}
site_roots = []
for source, value in site_values:
    item = record(value)
    item["source"] = source
    item["active"] = item["resolved_locator"] in active_sys_path
    item["disposition"] = "runtime_tree" if item["active"] else "suppressed_by_isolated_no_site"
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
    "probe_execution_identity": {"effective_uid": os.geteuid(), "effective_gid": os.getegid()},
    "process_image": {"sys_executable": record(sys.executable), "ns_get_executable_path": record(os.fsdecode(buffer.value))},
    "python_prefixes": {"prefix": record(sys.prefix), "base_prefix": record(sys.base_prefix)},
    "sys_path": sys_path,
    "stdlib_roots": stdlib_roots,
    "site_roots": site_roots,
    "site_policy": "isolated_no_site_only_active_paths_enter_runtime_closure/v1",
    "imported_module_origins": module_origins,
    "dyld_images": dyld,
    "os_asset_exclusion": {"profile": "darwin-dyld-system-library-roots-os-build-bound/v1", "allowed_roots": list(OS_ROOTS), "scope": "dyld_images_only", "binding": "exact_platform_binding_and_os_build_artifact"},
}
print(json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False))
"""


def _ref_artifact_digest(reference: Mapping[str, Any]) -> dict[str, str]:
    return dict(reference["artifact_digest"])


def _verify_root_artifact(reference: Mapping[str, Any]) -> bytes:
    path = Path(str(reference["locator"]))
    raw = read_protected_file(path, protected_root=U10_ROOT)
    observed = path.lstat()
    if (
        observed.st_uid != int(reference.get("owner_uid", 0))
        or observed.st_gid != int(reference.get("owner_gid", 0))
        or observed.st_nlink != 1
        or observed.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
        or digest_bytes(raw) != _ref_artifact_digest(reference)
    ):
        raise BrokerBoundaryError("u10_root_artifact_digest_mismatch", str(path))
    return raw


def _verify_host_runtime_artifact(reference: Mapping[str, Any]) -> bytes:
    path = Path(str(reference["locator"]))
    resolved = Path(os.path.realpath(path))
    if (
        not path.is_absolute()
        or path != Path(os.path.normpath(str(path)))
        or resolved != Path(str(reference["resolved_locator"]))
    ):
        raise BrokerBoundaryError("u10_host_runtime_path_mismatch", str(path))
    current = Path(path.anchor)
    for part in (None, *path.parent.parts[1:]):
        if part is not None:
            current /= part
        observed = current.lstat()
        try:
            assert_no_extended_acl(current)
        except (OSError, PermissionError) as exc:
            raise BrokerBoundaryError(
                "u10_host_runtime_acl_untrusted", str(current)
            ) from exc
        if (
            stat.S_ISLNK(observed.st_mode)
            or not stat.S_ISDIR(observed.st_mode)
            or observed.st_uid != 0
            or observed.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
        ):
            raise BrokerBoundaryError(
                "u10_host_runtime_ancestor_untrusted", str(current)
            )
    before = path.lstat()
    try:
        assert_no_extended_acl(path)
    except (OSError, PermissionError) as exc:
        raise BrokerBoundaryError("u10_host_runtime_acl_untrusted", str(path)) from exc
    if (
        stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_uid != 0
        or before.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
        or before.st_nlink < 1
    ):
        raise BrokerBoundaryError("u10_host_runtime_artifact_untrusted", str(path))
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
            raise BrokerBoundaryError("u10_host_runtime_changed", str(path))
        chunks: list[bytes] = []
        while block := os.read(descriptor, 1024 * 1024):
            chunks.append(block)
        raw = b"".join(chunks)
    finally:
        os.close(descriptor)
    if (
        reference["owner_uid"] != 0
        or reference["write_protection"]
        != "absolute_ancestor_chain_not_group_or_world_writable"
        or reference["artifact_digest"] != digest_bytes(raw)
    ):
        raise BrokerBoundaryError("u10_host_runtime_artifact_mismatch", str(path))
    return raw


def _validate_absolute_root_owned_chain_v1(path: Path) -> None:
    if not path.is_absolute() or path != Path(os.path.normpath(str(path))):
        raise BrokerBoundaryError("u10_host_runtime_path_mismatch", str(path))
    current = Path(path.anchor)
    for part in (None, *path.parts[1:]):
        if part is not None:
            current /= part
        observed = current.lstat()
        try:
            assert_no_extended_acl(current)
        except (OSError, PermissionError) as exc:
            raise BrokerBoundaryError(
                "u10_host_runtime_acl_untrusted", str(current)
            ) from exc
        if (
            stat.S_ISLNK(observed.st_mode)
            or not stat.S_ISDIR(observed.st_mode)
            or observed.st_uid != 0
            or observed.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
        ):
            raise BrokerBoundaryError(
                "u10_host_runtime_ancestor_untrusted", str(current)
            )


def _runtime_path_is_under_v1(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _runtime_inclusion_paths_v1(observation: Mapping[str, Any]) -> list[Path]:
    try:
        records = [
            observation["process_image"]["sys_executable"],
            observation["process_image"]["ns_get_executable_path"],
            observation["python_prefixes"]["prefix"],
            observation["python_prefixes"]["base_prefix"],
        ]
        records.extend(observation["sys_path"])
        records.extend(observation["stdlib_roots"])
        records.extend(
            item for item in observation["site_roots"] if item["active"] is True
        )
        records.extend(observation["imported_module_origins"])
        records.extend(
            item
            for item in observation["dyld_images"]
            if item["classification"] == "runtime_tree"
        )
        paths = [
            Path(item[field])
            for item in records
            for field in ("locator", "resolved_locator")
        ]
    except (KeyError, TypeError, ValueError) as exc:
        raise BrokerBoundaryError(
            "u10_bootstrap_runtime_closure_malformed", repr(exc)
        ) from exc
    return paths


def _derive_runtime_root_v1(observation: Mapping[str, Any]) -> Path:
    expected_exclusion = {
        "profile": _RUNTIME_OS_EXCLUSION_PROFILE,
        "allowed_roots": [str(path) for path in _RUNTIME_OS_ASSET_ROOTS],
        "scope": "dyld_images_only",
        "binding": "exact_platform_binding_and_os_build_artifact",
    }
    if (
        observation.get("probe_profile") != _RUNTIME_CLOSURE_PROFILE
        or observation.get("probe_execution_identity")
        != {"effective_uid": 0, "effective_gid": 0}
        or observation.get("os_asset_exclusion") != expected_exclusion
    ):
        raise BrokerBoundaryError(
            "u10_bootstrap_runtime_closure_contract_mismatch", "profile"
        )
    dyld = observation.get("dyld_images")
    if not isinstance(dyld, list) or not dyld:
        raise BrokerBoundaryError(
            "u10_bootstrap_runtime_closure_contract_mismatch", "dyld"
        )
    for item in dyld:
        locator = Path(str(item.get("locator", "")))
        resolved = Path(str(item.get("resolved_locator", "")))
        if item.get("classification") == "excluded_os_asset":
            root = Path(str(item.get("os_asset_root", "")))
            if root not in _RUNTIME_OS_ASSET_ROOTS or not (
                _runtime_path_is_under_v1(locator, root)
                and _runtime_path_is_under_v1(resolved, root)
            ):
                raise BrokerBoundaryError(
                    "u10_bootstrap_runtime_os_exclusion_mismatch", str(locator)
                )
        elif (
            item.get("classification") != "runtime_tree"
            or item.get("os_asset_root") is not None
        ):
            raise BrokerBoundaryError(
                "u10_bootstrap_runtime_os_exclusion_mismatch", str(locator)
            )
    paths = _runtime_inclusion_paths_v1(observation)
    if not paths or any(not path.is_absolute() for path in paths):
        raise BrokerBoundaryError(
            "u10_bootstrap_runtime_closure_path_mismatch", repr(paths)
        )
    try:
        root = Path(os.path.commonpath([str(path) for path in paths]))
    except ValueError as exc:
        raise BrokerBoundaryError(
            "u10_bootstrap_runtime_closure_path_mismatch", "commonpath"
        ) from exc
    if (
        not root.is_dir()
        or Path(os.path.realpath(root)) != root
        or any(not _runtime_path_is_under_v1(path, root) for path in paths)
    ):
        raise BrokerBoundaryError(
            "u10_bootstrap_runtime_derived_root_mismatch", str(root)
        )
    prefix = Path(observation["python_prefixes"]["prefix"]["resolved_locator"])
    base_prefix = Path(
        observation["python_prefixes"]["base_prefix"]["resolved_locator"]
    )
    if prefix != base_prefix or root != base_prefix:
        raise BrokerBoundaryError(
            "u10_bootstrap_runtime_base_prefix_mismatch", str(base_prefix)
        )
    return root


def _probe_bootstrap_runtime_v1(interpreter: Path) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            [str(interpreter), "-I", "-S", "-B", "-c", _RUNTIME_PROBE],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
            env=_RUNTIME_PROBE_ENVIRONMENT,
            text=True,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise BrokerBoundaryError(
            "u10_bootstrap_runtime_probe_failed", str(interpreter)
        ) from exc
    if completed.returncode != 0:
        raise BrokerBoundaryError(
            "u10_bootstrap_runtime_probe_failed", completed.stderr[:1000]
        )
    try:
        observation = strict_json_loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise BrokerBoundaryError(
            "u10_bootstrap_runtime_probe_unreadable", str(interpreter)
        ) from exc
    if not isinstance(observation, dict):
        raise BrokerBoundaryError(
            "u10_bootstrap_runtime_probe_unreadable", str(interpreter)
        )
    _derive_runtime_root_v1(observation)
    return observation


def _validate_current_process_runtime_closure_v1(
    observation: Mapping[str, Any], root: Path, interpreter: Path
) -> None:
    if Path(os.path.realpath(sys.executable)) != interpreter:
        raise BrokerBoundaryError(
            "u10_bootstrap_runtime_running_interpreter_mismatch",
            str(sys.executable),
        )
    libc = ctypes.CDLL(None, use_errno=True)
    ns_get_executable_path = libc._NSGetExecutablePath
    ns_get_executable_path.argtypes = [
        ctypes.c_char_p,
        ctypes.POINTER(ctypes.c_uint32),
    ]
    ns_get_executable_path.restype = ctypes.c_int
    size = ctypes.c_uint32(0)
    ns_get_executable_path(None, ctypes.byref(size))
    if size.value <= 1 or size.value > 1024 * 1024:
        raise BrokerBoundaryError(
            "u10_bootstrap_runtime_process_image_mismatch", "size"
        )
    buffer = ctypes.create_string_buffer(size.value)
    if ns_get_executable_path(buffer, ctypes.byref(size)) != 0:
        raise BrokerBoundaryError(
            "u10_bootstrap_runtime_process_image_mismatch", "read"
        )
    running_image = Path(os.path.realpath(os.fsdecode(buffer.value)))
    expected_image = Path(
        observation["process_image"]["ns_get_executable_path"]["resolved_locator"]
    )
    if running_image != expected_image or not _runtime_path_is_under_v1(
        running_image, root
    ):
        raise BrokerBoundaryError(
            "u10_bootstrap_runtime_process_image_mismatch", str(running_image)
        )
    # The broker package and its third-party verifier dependencies are closed
    # by the candidate/snapshot denominator, not by this stdlib bootstrap
    # denominator.  Requiring the already-running core process's complete
    # sys.path or dyld set here would silently merge those two trust domains.


def _host_runtime_tree_entries_v1(root: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    validate_directory_chain(root, root, required_uid=0)
    for raw_directory, directory_names, file_names in os.walk(
        root, topdown=True, followlinks=False
    ):
        base = Path(raw_directory)
        directory_names.sort()
        file_names.sort()
        for name in (*directory_names, *file_names):
            path = base / name
            observed = path.lstat()
            try:
                assert_no_extended_acl(path)
            except (OSError, PermissionError) as exc:
                raise BrokerBoundaryError(
                    "u10_bootstrap_runtime_acl_untrusted", str(path)
                ) from exc
            common = {
                "path": path.relative_to(root).as_posix(),
                "mode": stat.S_IMODE(observed.st_mode),
                "uid": observed.st_uid,
                "gid": observed.st_gid,
            }
            if observed.st_uid != 0:
                raise BrokerBoundaryError(
                    "u10_bootstrap_runtime_owner_mismatch", str(path)
                )
            if stat.S_ISLNK(observed.st_mode):
                target = os.readlink(path)
                resolved = Path(os.path.realpath(path))
                try:
                    resolved.relative_to(root)
                except ValueError as exc:
                    raise BrokerBoundaryError(
                        "u10_bootstrap_runtime_symlink_escape", str(path)
                    ) from exc
                entries.append({**common, "kind": "symlink", "target": target})
            elif stat.S_ISDIR(observed.st_mode):
                if observed.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
                    raise BrokerBoundaryError(
                        "u10_bootstrap_runtime_mutable", str(path)
                    )
                entries.append({**common, "kind": "directory"})
            elif stat.S_ISREG(observed.st_mode):
                raw = read_protected_file(
                    path,
                    protected_root=root,
                    required_uid=0,
                    maximum_bytes=256 * 1024 * 1024,
                )
                if observed.st_nlink != 1:
                    raise BrokerBoundaryError(
                        "u10_bootstrap_runtime_hardlink", str(path)
                    )
                entries.append(
                    {
                        **common,
                        "kind": "file",
                        "size": observed.st_size,
                        "artifact_digest": digest_bytes(raw),
                    }
                )
            else:
                raise BrokerBoundaryError(
                    "u10_bootstrap_runtime_special_entry", str(path)
                )
    entries.sort(key=lambda item: str(item["path"]))
    return entries
