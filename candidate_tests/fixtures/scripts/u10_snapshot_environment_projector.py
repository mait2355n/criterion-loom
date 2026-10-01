#!/usr/bin/env python3
"""Non-root final-path environment projection for a U-10 snapshot.

The root producer supplies one closed JSON context over stdin.  This helper
loads code and contracts only from the already projected snapshot, reobserves
the exact final-path tools/host/containment boundary, and returns candidate
material over stdout.  It never records a human decision and never writes the
snapshot.
"""

from __future__ import annotations

import base64
import importlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import sys
import types
from typing import Any


_SCHEMA_VERSION = "semantic-guard-u10-snapshot-environment-projection-context/v1"
_RESULT_VERSION = "semantic-guard-u10-snapshot-environment-projection-result/v1"
_CONTEXT_FIELDS = {
    "schema_version",
    "snapshot_root",
    "subject_source_root",
    "dependency_import_roots",
    "verification_profile_locator",
    "environment_profile_id",
    "environment_profile_version",
    "environment_output_locators",
    "adoption_id",
    "adoption_version",
    "source_id",
    "source_version",
    "decision_owner_ref",
    "worker_identity",
}
_OUTPUT_LOCATOR_FIELDS = {
    "host_identity_evidence",
    "containment_probe_evidence",
    "containment_trace",
    "resolved_environment_profile",
    "environment_adoption_request",
    "eligibility_source",
}


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


def _canonical_relative(value: Any) -> str:
    if not isinstance(value, str):
        raise RuntimeError("snapshot locator is not a string")
    parsed = PurePosixPath(value)
    if (
        not value
        or value != parsed.as_posix()
        or parsed.is_absolute()
        or any(part in {"", ".", ".."} for part in value.split("/"))
        or "\\" in value
        or "\x00" in value
    ):
        raise RuntimeError(f"snapshot locator is not canonical: {value!r}")
    return value


def _inside(root: Path, value: Any, *, directory: bool | None = None) -> Path:
    relative = _canonical_relative(value)
    path = root / relative
    resolved = path.resolve(strict=True)
    resolved.relative_to(root)
    if directory is True and not resolved.is_dir():
        raise RuntimeError(f"snapshot directory required: {relative}")
    if directory is False and not resolved.is_file():
        raise RuntimeError(f"snapshot file required: {relative}")
    return resolved


def _load_context() -> dict[str, Any]:
    raw = sys.stdin.buffer.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise RuntimeError("projection context exceeds byte limit")
    try:
        value = strict_json_loads(raw)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("projection context is unreadable") from exc
    if not isinstance(value, dict) or set(value) != _CONTEXT_FIELDS:
        raise RuntimeError("projection context field denominator mismatch")
    if value["schema_version"] != _SCHEMA_VERSION:
        raise RuntimeError("projection context schema mismatch")
    return value


def _install_snapshot_runtime(
    snapshot: Path, subject_root: Path, dependency_roots: list[Path]
) -> None:
    for dependency in dependency_roots:
        for child in dependency.iterdir():
            if child.name == "semantic_guard_vnext" or child.name.startswith(
                "semantic_guard_vnext."
            ):
                raise RuntimeError("dependency subject namespace collision")
    sys.path[:] = [str(subject_root), *(str(item) for item in dependency_roots)]
    package_root = subject_root / "semantic_guard_vnext"
    package_root.resolve(strict=True).relative_to(snapshot)
    package = types.ModuleType("semantic_guard_vnext")
    package.__path__ = [str(package_root)]
    package.__package__ = "semantic_guard_vnext"
    sys.modules["semantic_guard_vnext"] = package


def _load_object(path: Path) -> dict[str, Any]:
    try:
        value = strict_json_loads(path.read_bytes())
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"projection input is unreadable: {path}") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"projection input is not an object: {path}")
    return value


def _assert_identity(context: dict[str, Any]) -> None:
    expected = context["worker_identity"]
    if set(expected) != {"uid", "gid", "supplementary_gids", "umask"}:
        raise RuntimeError("projection worker identity contract mismatch")
    expected_umask = int(expected["umask"])
    observed_umask = os.umask(expected_umask)
    os.umask(observed_umask)
    if (
        os.geteuid() == 0
        or os.geteuid() != int(expected["uid"])
        or os.getegid() != int(expected["gid"])
        or sorted(os.getgroups()) != list(expected["supplementary_gids"])
        or observed_umask != expected_umask
    ):
        raise RuntimeError("projection worker principal mismatch")


def run() -> dict[str, Any]:
    if not (
        sys.flags.isolated
        and sys.flags.no_site
        and sys.flags.dont_write_bytecode
        and getattr(sys.flags, "safe_path", True)
    ):
        raise RuntimeError("projection helper requires Python -I -S -B")
    if dict(os.environ) != {
        "PATH": "",
        "LC_ALL": "C",
        "PYTHONDONTWRITEBYTECODE": "1",
    }:
        raise RuntimeError("projection environment denominator mismatch")
    context = _load_context()
    _assert_identity(context)
    snapshot = Path(str(context["snapshot_root"])).resolve(strict=True)
    Path(os.path.realpath(sys.executable)).relative_to(snapshot)
    subject = Path(str(context["subject_source_root"])).resolve(strict=True)
    subject.relative_to(snapshot)
    dependencies = [
        Path(str(item)).resolve(strict=True)
        for item in context["dependency_import_roots"]
    ]
    for dependency in dependencies:
        dependency.relative_to(snapshot)
    outputs = context["environment_output_locators"]
    if not isinstance(outputs, dict) or set(outputs) != _OUTPUT_LOCATOR_FIELDS:
        raise RuntimeError("projection output locator denominator mismatch")
    for locator in outputs.values():
        _canonical_relative(locator)
    if len(set(outputs.values())) != len(outputs):
        raise RuntimeError("projection output locator collision")
    profile_path = _inside(
        snapshot, context["verification_profile_locator"], directory=False
    )
    _install_snapshot_runtime(snapshot, subject, dependencies)
    qualified = importlib.import_module("semantic_guard_vnext.qualified_environment")
    profile = _load_object(profile_path)
    qualified.validate_verification_profile_v4(profile)
    material = qualified.build_environment_candidate_material(
        profile,
        repository_root=snapshot,
        environment_profile_id=str(context["environment_profile_id"]),
        environment_profile_version=str(context["environment_profile_version"]),
        host_evidence_locator=str(outputs["host_identity_evidence"]),
        containment_evidence_locator=str(outputs["containment_probe_evidence"]),
        containment_trace_locator=str(outputs["containment_trace"]),
    )
    adoption_request = qualified.build_adoption_request_v1(
        material["resolved_environment_profile"],
        profile,
        adoption_id=str(context["adoption_id"]),
        adoption_version=str(context["adoption_version"]),
        decision_owner_ref=context["decision_owner_ref"],
    )
    source = qualified.build_candidate_eligibility_source(
        adoption_request,
        repository_root=snapshot,
        source_id=str(context["source_id"]),
        source_version=str(context["source_version"]),
    )
    return {
        "schema_version": _RESULT_VERSION,
        "host_identity_evidence": material["host_identity_evidence"],
        "containment_probe_evidence": material["containment_probe_evidence"],
        "containment_trace_base64": base64.b64encode(
            material["containment_trace_bytes"]
        ).decode("ascii"),
        "resolved_environment_profile": material[
            "resolved_environment_profile"
        ],
        "environment_adoption_request": adoption_request,
        "eligibility_source": source,
        "formal_authority": "none",
        "positive_assurance_allowed": False,
    }


def main() -> int:
    result = run()
    encoded = json.dumps(
        result,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    if len(encoded) > 16 * 1024 * 1024:
        raise RuntimeError("projection result exceeds byte limit")
    sys.stdout.buffer.write(encoded)
    sys.stdout.buffer.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
