#!/usr/bin/env python3
"""Stdlib-only root bootstrap for the U-10 execution broker.

The bootstrap proves that its interpreter, import roots, broker entrypoint and
complete execution tree are inside one root-owned snapshot before importing
jsonschema, cryptography, or any semantic-guard implementation module.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import stat
import sys


SNAPSHOT_ROOT = Path("/Library/Application Support/semantic-guard/u10/snapshots")
MANIFEST_NAME = "u10-execution-snapshot-manifest-v1.json"


class BootstrapError(RuntimeError):
    pass


def _strict_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise json.JSONDecodeError(f"duplicate object key: {key!r}", key, 0)
        value[key] = item
    return value


def _reject_nonfinite_json_constant(value: str) -> object:
    raise json.JSONDecodeError(f"non-finite JSON number: {value}", value, 0)


def _strict_json_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise json.JSONDecodeError(f"non-finite JSON number: {value}", value, 0)
    return parsed


def strict_json_loads(raw: str | bytes | bytearray) -> object:
    return json.loads(
        raw,
        object_pairs_hook=_strict_json_object,
        parse_constant=_reject_nonfinite_json_constant,
        parse_float=_strict_json_float,
    )


def _canonical(value: dict) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _digest(raw: bytes) -> dict[str, str]:
    return {"algorithm": "sha256", "value": hashlib.sha256(raw).hexdigest()}


def _read_regular(path: Path) -> bytes:
    before = path.lstat()
    if (
        not stat.S_ISREG(before.st_mode)
        or stat.S_ISLNK(before.st_mode)
        or before.st_uid != 0
        or before.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
        or before.st_nlink != 1
    ):
        raise BootstrapError(f"untrusted root artifact: {path}")
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
            raise BootstrapError(f"artifact changed before read: {path}")
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
            raise BootstrapError(f"artifact changed during read: {path}")
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _validate_absolute_directory_chain(path: Path, *, exact_leaf_mode: int | None = None) -> None:
    if not path.is_absolute() or path != Path(os.path.normpath(str(path))):
        raise BootstrapError(f"non-canonical absolute directory: {path}")
    current = Path(path.anchor)
    chain = [current]
    for part in path.parts[1:]:
        current /= part
        chain.append(current)
    for index, item in enumerate(chain):
        observed = item.lstat()
        if (
            stat.S_ISLNK(observed.st_mode)
            or not stat.S_ISDIR(observed.st_mode)
            or observed.st_uid != 0
            or observed.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
            or (
                exact_leaf_mode is not None
                and index == len(chain) - 1
                and stat.S_IMODE(observed.st_mode) != exact_leaf_mode
            )
        ):
            raise BootstrapError(f"untrusted snapshot ancestor: {item}")


def _snapshot_root(script: Path) -> Path:
    if script != Path(os.path.normpath(str(script))) or not script.is_absolute():
        raise BootstrapError("bootstrap path is not canonical and absolute")
    for parent in script.parents:
        if parent.parent == SNAPSHOT_ROOT:
            return parent
    raise BootstrapError("bootstrap is outside the fixed U-10 snapshot root")


def _tree_digest(root: Path, excluded: Path) -> dict[str, str]:
    records: list[dict] = []
    for raw_directory, directories, files in os.walk(
        root, topdown=True, followlinks=False
    ):
        base = Path(raw_directory)
        directories.sort()
        files.sort()
        for name in (*directories, *files):
            path = base / name
            if path == excluded:
                continue
            observed = path.lstat()
            if (
                stat.S_ISLNK(observed.st_mode)
                or observed.st_uid != 0
                or observed.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
            ):
                raise BootstrapError(f"mutable or non-root snapshot path: {path}")
            relative = path.relative_to(root).as_posix()
            if stat.S_ISDIR(observed.st_mode):
                records.append(
                    {
                        "path": relative,
                        "kind": "directory",
                        "mode": stat.S_IMODE(observed.st_mode),
                        "uid": observed.st_uid,
                        "gid": observed.st_gid,
                    }
                )
            elif stat.S_ISREG(observed.st_mode):
                if observed.st_nlink != 1:
                    raise BootstrapError(f"hard-linked snapshot file: {path}")
                raw = _read_regular(path)
                records.append(
                    {
                        "path": relative,
                        "kind": "file",
                        "mode": stat.S_IMODE(observed.st_mode),
                        "uid": observed.st_uid,
                        "gid": observed.st_gid,
                        "size": observed.st_size,
                        "digest": _digest(raw),
                    }
                )
            else:
                raise BootstrapError(f"special snapshot path: {path}")
    return _digest(_canonical({"entries": records}))


def _inside(root: Path, value: object) -> Path:
    path = Path(str(value))
    if not path.is_absolute() or path != Path(os.path.normpath(str(path))):
        raise BootstrapError(f"non-canonical snapshot path: {path}")
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise BootstrapError(f"snapshot path escaped: {path}") from exc
    return path


def _validate_loaded_module_origin(
    snapshot: Path, name: str, module: object
) -> None:
    origin = getattr(module, "__file__", None)
    if origin:
        path = Path(str(origin))
        if path.suffix in {".pyc", ".pyo"} and not path.exists():
            path = Path(str(origin)[:-1])
        if not path.is_absolute() or not path.exists() or not path.is_file():
            raise BootstrapError(
                f"pre-bootstrap module origin is not one existing file: "
                f"{name}={path}"
            )
        resolved = Path(os.path.realpath(path))
        try:
            resolved.relative_to(snapshot)
        except ValueError as exc:
            raise BootstrapError(
                f"pre-bootstrap module outside snapshot: {name}={resolved}"
            ) from exc
        return

    specification = getattr(module, "__spec__", None)
    specification_origin = getattr(specification, "origin", None)
    if specification_origin in {"built-in", "frozen"}:
        return
    namespace_locations = getattr(
        specification, "submodule_search_locations", None
    )
    if (
        specification_origin not in {None, "namespace"}
        or namespace_locations is None
    ):
        raise BootstrapError(
            f"pre-bootstrap module origin is unverified: "
            f"{name}={specification_origin!r}"
        )
    locations = tuple(namespace_locations)
    if not locations:
        raise BootstrapError(
            f"pre-bootstrap namespace module has no locations: {name}"
        )
    for location in locations:
        path = Path(str(location))
        if not path.is_absolute() or not path.exists() or not path.is_dir():
            raise BootstrapError(
                f"pre-bootstrap namespace location is unavailable: "
                f"{name}={path}"
            )
        resolved = Path(os.path.realpath(path))
        try:
            resolved.relative_to(snapshot)
        except ValueError as exc:
            raise BootstrapError(
                f"pre-bootstrap namespace outside snapshot: {name}={resolved}"
            ) from exc


def _validate_loaded_origins(snapshot: Path) -> None:
    for name, module in tuple(sys.modules.items()):
        _validate_loaded_module_origin(snapshot, name, module)


def _validate_runtime(manifest: dict, snapshot: Path, script: Path) -> None:
    if not (
        sys.flags.isolated
        and sys.flags.no_site
        and sys.flags.dont_write_bytecode
        and sys.flags.safe_path
    ):
        raise BootstrapError("broker requires Python flags -I -S -B")
    material = dict(manifest)
    observed_manifest_digest = material.pop("manifest_digest", None)
    if observed_manifest_digest != _digest(_canonical(material)):
        raise BootstrapError("snapshot manifest digest mismatch")
    if manifest.get("lifecycle_state") != "active":
        raise BootstrapError("snapshot is not active")
    expected_environment = {
        "PATH": "",
        "LC_ALL": "C",
        "PYTHONDONTWRITEBYTECODE": "1",
        "SEMANTIC_GUARD_U10_OUTER_VERIFICATION": manifest["manifest_digest"][
            "value"
        ],
    }
    if dict(os.environ) != expected_environment:
        raise BootstrapError("snapshot process did not come from the outer verifier")
    if manifest["root_storage"]["snapshot_path"] != str(snapshot):
        raise BootstrapError("snapshot root binding mismatch")
    _validate_absolute_directory_chain(snapshot, exact_leaf_mode=0o555)
    manifest_path = snapshot / MANIFEST_NAME
    if _tree_digest(snapshot, manifest_path) != manifest["root_storage"]["tree_digest"]:
        raise BootstrapError("snapshot tree digest mismatch")
    runtime_ref = manifest["broker_runtime_ref"]
    if _inside(snapshot, runtime_ref["locator"]) != script:
        raise BootstrapError("broker bootstrap locator mismatch")
    script_raw = _read_regular(script)
    if (
        runtime_ref["artifact_digest"] != _digest(script_raw)
        or runtime_ref["semantic_digest"] != _digest(script_raw)
    ):
        raise BootstrapError("broker bootstrap digest mismatch")
    launch = manifest["broker_launch_contract"]
    if (
        launch["invocation_mode"]
        != "fixed_root_wrapper_outer_verifier_then_snapshot_execve/v2"
        or launch["python_flags"] != ["-I", "-S", "-B"]
        or launch["environment_policy"]
        != "env_i_direct_qualified_python_then_exact_snapshot_execve/v3"
    ):
        raise BootstrapError("outer launch contract mismatch")
    interpreter_ref = manifest["worker_runtime"]["interpreter_snapshot_ref"]
    interpreter = _inside(snapshot, interpreter_ref["locator"])
    if Path(os.path.realpath(sys.executable)) != interpreter:
        raise BootstrapError("interpreter is not the snapshot interpreter")
    if _digest(_read_regular(interpreter)) != interpreter_ref["artifact_digest"]:
        raise BootstrapError("snapshot interpreter digest mismatch")
    for value in sys.path:
        if not value:
            continue
        path = Path(value)
        if not path.is_absolute():
            raise BootstrapError(f"relative pre-bootstrap sys.path: {value}")
        if path.exists():
            _inside(snapshot, Path(os.path.realpath(path)))
    _validate_loaded_origins(snapshot)
    entries = manifest["artifact_denominator"]["entries"]
    declared = {
        _inside(snapshot, artifact["snapshot_ref"]["locator"])
        for artifact in entries.values()
    }
    observed = {
        path
        for path in snapshot.rglob("*")
        if path != manifest_path and path.is_file() and not path.is_symlink()
    }
    if declared != observed or len(declared) != len(entries):
        raise BootstrapError("snapshot regular-file denominator is not closed")


def _request(arguments: list[str]) -> dict[str, str]:
    if len(arguments) != 6 or arguments[0::2] != [
        "--entry-id",
        "--command-id",
        "--request-nonce",
    ]:
        raise BootstrapError(
            "usage: u10_root_broker_bootstrap.py --entry-id ID "
            "--command-id ID --request-nonce HEX64"
        )
    return {
        "entry_id": arguments[1],
        "command_id": arguments[3],
        "request_nonce": arguments[5],
    }


def main(argv: list[str] | None = None) -> int:
    if os.geteuid() != 0:
        raise BootstrapError("U-10 root broker bootstrap requires euid 0")
    script = Path(__file__)
    if stat.S_ISLNK(script.lstat().st_mode):
        raise BootstrapError("bootstrap symlink is prohibited")
    script = script.resolve(strict=True)
    snapshot = _snapshot_root(script)
    manifest_path = snapshot / MANIFEST_NAME
    try:
        manifest = strict_json_loads(_read_regular(manifest_path))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BootstrapError("snapshot manifest is not strict JSON") from exc
    if not isinstance(manifest, dict):
        raise BootstrapError("snapshot manifest root is not an object")
    _validate_runtime(manifest, snapshot, script)
    runtime = manifest["worker_runtime"]
    subject_root = _inside(snapshot, runtime["subject_source_root"]["locator"])
    dependency_roots = [
        _inside(snapshot, item["locator"])
        for item in runtime["dependency_import_roots"]
    ]
    for dependency in dependency_roots:
        for child in dependency.iterdir():
            if child.name == "semantic_guard_u10_broker" or child.name.startswith(
                "semantic_guard_u10_broker."
            ):
                raise BootstrapError("dependency broker namespace collision")
    import_roots = [subject_root, *dependency_roots]
    sys.path[:] = [str(path) for path in import_roots]
    os.environ.clear()
    os.environ.update(
        {"PATH": "", "LC_ALL": "C", "PYTHONDONTWRITEBYTECODE": "1"}
    )
    from semantic_guard_u10_broker.supervisor import (  # noqa: PLC0415
        execute_root_broker_request_v3,
    )

    envelope = execute_root_broker_request_v3(
        _request(list(sys.argv[1:] if argv is None else argv))
    )
    sys.stdout.write(
        json.dumps(
            envelope,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        + "\n"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BootstrapError as exc:
        print(f"U-10 broker bootstrap failed: {exc}", file=sys.stderr)
        raise SystemExit(70)
