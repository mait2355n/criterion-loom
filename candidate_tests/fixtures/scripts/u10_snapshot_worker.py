#!/usr/bin/env python3
"""Non-root U-10 worker launched only by the fixed root supervisor.

The worker receives one root-generated context path.  It never reads a caller
profile, source, output path, UID/GID, argv, or trust-store override.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import importlib
import importlib.machinery
import json
import math
import os
from pathlib import Path
import sys
import types


WORKER_VERSION = "3.0.0-candidate"
_CONTEXT_FIELDS = {
    "schema_version",
    "run_id",
    "receipt_id",
    "entry_id",
    "command_id",
    "request_nonce",
    "snapshot_root",
    "evidence_store_root",
    "output_directory",
    "source_ref",
    "profile_ref",
    "environment_ref",
    "environment_adoption_ref",
    "environment_adoption",
    "worker_identity",
    "worker_launch",
    "dependency_import_roots",
    "subject_source_root",
    "phase_budget",
}

_ENVIRONMENT_ADOPTION_ROOT = Path(
    "/Library/Application Support/semantic-guard/u10/authorizations"
)


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


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _digest(raw: bytes) -> dict[str, str]:
    return {"algorithm": "sha256", "value": hashlib.sha256(raw).hexdigest()}


def _canonical_digest(value: dict) -> dict[str, str]:
    return _digest(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    )


def _canonical_json_record_bytes(value: dict) -> bytes:
    """Encode one root record exactly as compact canonical JSON plus newline."""

    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _validate_environment_adoption_binding(context: dict) -> dict:
    """Validate the exact root-projected adoption before trust resolution."""

    reference = context.get("environment_adoption_ref")
    adoption = context.get("environment_adoption")
    if (
        not isinstance(reference, dict)
        or set(reference)
        != {"record_id", "locator", "artifact_digest", "semantic_digest"}
        or not isinstance(adoption, dict)
    ):
        raise RuntimeError("root environment adoption binding malformed")
    adoption_id = adoption.get("adoption_id")
    adoption_version = adoption.get("adoption_version")
    adoption_digest = adoption.get("adoption_digest")
    if (
        not isinstance(adoption_id, str)
        or not adoption_id
        or not isinstance(adoption_version, str)
        or not adoption_version
        or reference.get("record_id") != adoption_id
        or Path(str(reference.get("locator", "")))
        != _ENVIRONMENT_ADOPTION_ROOT / f"{adoption_id}.json"
        or reference.get("artifact_digest")
        != _digest(_canonical_json_record_bytes(adoption))
        or reference.get("semantic_digest") != adoption_digest
    ):
        raise RuntimeError("root environment adoption binding mismatch")
    material = dict(adoption)
    material.pop("adoption_digest", None)
    if adoption_digest != _canonical_digest(material):
        raise RuntimeError("root environment adoption seal mismatch")
    return adoption


def _build_environment_eligibility_service(
    qualified: object,
    source: dict,
    context: dict,
    snapshot_root: Path,
) -> object:
    adoption = _validate_environment_adoption_binding(context)
    service_type = getattr(qualified, "EnvironmentEligibilityService")
    return service_type(
        source,
        expected_source_digest=context["source_ref"]["source_digest"],
        repository_root=snapshot_root,
        external_adoption=adoption,
    )


def _load_object(path: Path) -> tuple[dict, bytes]:
    raw = path.read_bytes()
    value = strict_json_loads(raw)
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON root is not an object: {path}")
    return value, raw


def _inside(root: Path, candidate: Path) -> Path:
    resolved = candidate.resolve(strict=True)
    resolved.relative_to(root)
    return resolved


def _load_bound_json(root: Path, reference: dict, semantic_field: str) -> dict:
    path = _inside(root, Path(str(reference["locator"])))
    value, raw = _load_object(path)
    if _digest(raw) != reference["artifact_digest"]:
        raise RuntimeError(f"snapshot artifact digest mismatch: {path}")
    observed_semantic = (
        _canonical_digest(value)
        if semantic_field == "content_digest"
        else value.get(semantic_field)
    )
    if observed_semantic != reference[semantic_field]:
        raise RuntimeError(f"snapshot semantic digest mismatch: {path}")
    return value


def _write_exclusive(path: Path, value: dict) -> None:
    encoded = (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.fchmod(descriptor, 0o600)
        offset = 0
        while offset < len(encoded):
            offset += os.write(descriptor, encoded[offset:])
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    parent_fd = os.open(
        path.parent,
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
    )
    try:
        os.fsync(parent_fd)
    finally:
        os.close(parent_fd)


def _install_snapshot_runtime(
    snapshot_root: Path,
    subject_source_root: Path,
    dependency_roots: list[Path],
) -> None:
    exact_roots: list[Path] = []
    for dependency in dependency_roots:
        for child in dependency.iterdir():
            if child.name == "semantic_guard_vnext" or child.name.startswith(
                "semantic_guard_vnext."
            ):
                raise RuntimeError("dependency subject namespace collision")
    for root in [subject_source_root, *dependency_roots]:
        exact = _inside(snapshot_root, root)
        if not exact.is_dir():
            raise RuntimeError(f"snapshot import root is not a directory: {exact}")
        exact_roots.append(exact)
    sys.path[:] = [str(root) for root in exact_roots]
    # Do not execute semantic_guard_vnext/__init__.py.  The worker needs only
    # the three exact environment/execution modules in the root-owned snapshot.
    package_root = _inside(
        subject_source_root, subject_source_root / "semantic_guard_vnext"
    )
    package = types.ModuleType("semantic_guard_vnext")
    package.__path__ = [str(package_root)]
    package.__package__ = "semantic_guard_vnext"
    package_specification = importlib.machinery.ModuleSpec(
        "semantic_guard_vnext", loader=None, is_package=True
    )
    package_specification.submodule_search_locations = [str(package_root)]
    package.__spec__ = package_specification
    sys.modules["semantic_guard_vnext"] = package


def _validate_module_origin(snapshot_root: Path, name: str, module: object) -> None:
    origin = getattr(module, "__file__", None)
    if origin:
        path = Path(str(origin))
        if path.suffix in {".pyc", ".pyo"} and not path.exists():
            path = Path(str(origin)[:-1])
        if not path.is_absolute() or not path.exists() or not path.is_file():
            raise RuntimeError(
                f"loaded module origin is not one existing file: {name}={path}"
            )
        resolved = Path(os.path.realpath(path))
        try:
            resolved.relative_to(snapshot_root)
        except ValueError as exc:
            raise RuntimeError(
                f"loaded module outside snapshot: {name}={resolved}"
            ) from exc
        return

    specification = getattr(module, "__spec__", None)
    specification_origin = getattr(specification, "origin", None)
    if specification_origin in {"built-in", "frozen"}:
        return
    namespace_locations = getattr(specification, "submodule_search_locations", None)
    if specification_origin not in {None, "namespace"} or namespace_locations is None:
        raise RuntimeError(
            f"loaded module origin is unverified: {name}={specification_origin!r}"
        )
    locations = tuple(namespace_locations)
    if not locations:
        raise RuntimeError(f"loaded namespace module has no locations: {name}")
    for location in locations:
        path = Path(str(location))
        if not path.is_absolute() or not path.exists() or not path.is_dir():
            raise RuntimeError(
                f"loaded namespace location is unavailable: {name}={path}"
            )
        resolved = Path(os.path.realpath(path))
        try:
            resolved.relative_to(snapshot_root)
        except ValueError as exc:
            raise RuntimeError(
                f"loaded namespace outside snapshot: {name}={resolved}"
            ) from exc


def _validate_module_origins(snapshot_root: Path) -> None:
    for name, module in tuple(sys.modules.items()):
        _validate_module_origin(snapshot_root, name, module)


def run(context_path: Path) -> int:
    started_at = _utc_now()
    if not (
        sys.flags.isolated
        and sys.flags.no_site
        and sys.flags.dont_write_bytecode
        and sys.flags.safe_path
    ):
        raise RuntimeError("snapshot worker requires Python flags -I -S -B")
    context, _raw = _load_object(context_path)
    if set(context) != _CONTEXT_FIELDS:
        raise RuntimeError("root worker context field denominator mismatch")
    if context["schema_version"] != "semantic-guard-u10-worker-context/v2":
        raise RuntimeError("root worker context version mismatch")
    phase_budget = context["phase_budget"]
    required_phase_fields = {
        "profile",
        "pre_environment_reobservation_seconds",
        "post_environment_reobservation_seconds",
        "evidence_finalization_seconds",
        "process_reap_seconds",
        "governed_command_timeout_seconds",
        "whole_run_timeout_seconds",
    }
    if set(phase_budget) != required_phase_fields or phase_budget["profile"] != (
        "u10-compositional-worker-budget/v1"
    ):
        raise RuntimeError("worker phase budget field denominator mismatch")
    phase_values = [
        phase_budget["pre_environment_reobservation_seconds"],
        phase_budget["governed_command_timeout_seconds"],
        phase_budget["post_environment_reobservation_seconds"],
        phase_budget["evidence_finalization_seconds"],
        phase_budget["process_reap_seconds"],
    ]
    if any(
        isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0
        for value in phase_values
    ) or phase_budget["whole_run_timeout_seconds"] != sum(phase_values):
        raise RuntimeError("worker phase budget composition mismatch")
    expected_identity = context["worker_identity"]
    if set(expected_identity) != {"uid", "gid", "supplementary_gids", "umask"}:
        raise RuntimeError("worker identity field denominator mismatch")
    expected_uid = int(expected_identity["uid"])
    expected_gid = int(expected_identity["gid"])
    expected_umask = int(expected_identity["umask"])
    observed_umask = os.umask(expected_umask)
    os.umask(observed_umask)
    if (
        os.geteuid() == 0
        or os.geteuid() != expected_uid
        or os.getegid() != expected_gid
        or sorted(os.getgroups()) != expected_identity["supplementary_gids"]
        or observed_umask != expected_umask
    ):
        raise RuntimeError(
            "worker principal mismatch: "
            f"{os.geteuid()}:{os.getegid()} groups={sorted(os.getgroups())} "
            f"umask={observed_umask:o}"
        )
    launch = context["worker_launch"]
    if set(launch) != {
        "worker_version",
        "interpreter_ref",
        "entrypoint_ref",
        "python_flags",
        "working_directory",
        "environment",
        "process_group_policy",
    }:
        raise RuntimeError("worker launch field denominator mismatch")
    expected_environment = {
        "PATH": "",
        "LC_ALL": "C",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    if (
        launch["worker_version"] != WORKER_VERSION
        or launch["python_flags"] != ["-I", "-S", "-B"]
        or launch["working_directory"] != os.getcwd()
        or launch["environment"] != expected_environment
        or dict(os.environ) != expected_environment
        or launch["process_group_policy"]
        != "worker_and_inner_runner_share_root_reaped_group/v1"
    ):
        raise RuntimeError("worker launch contract mismatch")
    snapshot_root = Path(str(context["snapshot_root"]))
    evidence_root = Path(str(context["evidence_store_root"]))
    output_directory = Path(str(context["output_directory"]))
    subject_source_root = Path(str(context["subject_source_root"]))
    dependency_roots = [Path(str(item)) for item in context["dependency_import_roots"]]
    snapshot_root = snapshot_root.resolve(strict=True)
    evidence_root = evidence_root.resolve(strict=True)
    output_directory.parent.resolve(strict=True).relative_to(evidence_root)
    Path(os.path.realpath(sys.executable)).relative_to(snapshot_root)
    if Path(os.path.realpath(sys.executable)) != Path(
        str(launch["interpreter_ref"]["locator"])
    ):
        raise RuntimeError("worker interpreter launch mismatch")
    if Path(__file__).resolve(strict=True) != Path(
        str(launch["entrypoint_ref"]["locator"])
    ):
        raise RuntimeError("worker entrypoint launch mismatch")
    for value in sys.path:
        if value and Path(value).exists():
            Path(os.path.realpath(value)).relative_to(snapshot_root)
    _validate_module_origins(snapshot_root)
    _install_snapshot_runtime(snapshot_root, subject_source_root, dependency_roots)
    qualified = importlib.import_module("semantic_guard_vnext.qualified_environment")
    governed = importlib.import_module(
        "semantic_guard_vnext.governed_environment_execution"
    )
    _validate_module_origins(snapshot_root)
    source = _load_bound_json(snapshot_root, context["source_ref"], "source_digest")
    profile = _load_bound_json(snapshot_root, context["profile_ref"], "content_digest")
    environment = _load_bound_json(
        snapshot_root, context["environment_ref"], "basis_digest"
    )
    profile_commands = [
        item
        for item in profile["commands"]
        if item["command_id"] == context["command_id"]
    ]
    if (
        len(profile_commands) != 1
        or profile_commands[0]["timeout_seconds"]
        != phase_budget["governed_command_timeout_seconds"]
    ):
        raise RuntimeError("worker command timeout budget mismatch")
    service = _build_environment_eligibility_service(
        qualified,
        source,
        context,
        snapshot_root,
    )
    receipt = governed._execute_governed_command_with_service_v1(
        str(context["command_id"]),
        profile,
        environment,
        eligibility_service=service,
        output_directory=output_directory,
        receipt_id=str(context["receipt_id"]),
        evidence_store_root=evidence_root,
        execution_uid=None,
        execution_gid=None,
        extra_groups=None,
        umask=0o077,
        child_start_new_session=False,
        parent_environment={},
    )
    receipt_path = output_directory / "receipt.json"
    receipt_raw = receipt_path.read_bytes()
    outcome = {
        "schema_version": "semantic-guard-u10-worker-outcome/v1",
        "worker_version": WORKER_VERSION,
        "run_id": context["run_id"],
        "entry_id": context["entry_id"],
        "command_id": context["command_id"],
        "request_nonce": context["request_nonce"],
        "worker_identity": {
            "uid": os.geteuid(),
            "gid": os.getegid(),
            "supplementary_gids": sorted(os.getgroups()),
            "umask": observed_umask,
        },
        "launch_observation": {
            "pid": os.getpid(),
            "parent_pid": os.getppid(),
            "process_group_id": os.getpgrp(),
            "session_id": os.getsid(0),
        },
        "receipt_locator": str(receipt_path),
        "receipt_artifact_digest": _digest(receipt_raw),
        "receipt_semantic_digest": receipt["receipt_digest"],
        "execution_nonce": receipt["execution_nonce"],
        "execution_status": receipt["execution_status"],
        "started_at": started_at,
        "finished_at": _utc_now(),
        "formal_authority": "none",
        "positive_assurance_allowed": False,
    }
    _write_exclusive(evidence_root / "worker-outcome.json", outcome)
    return 0


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) != 2 or arguments[0] != "--broker-context":
        raise SystemExit("usage: u10_snapshot_worker.py --broker-context ABSOLUTE_PATH")
    context_path = Path(arguments[1])
    if not context_path.is_absolute():
        raise SystemExit("broker context path must be absolute")
    try:
        return run(context_path)
    except Exception as exc:
        print(f"u10 worker failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 70


if __name__ == "__main__":
    raise SystemExit(main())
