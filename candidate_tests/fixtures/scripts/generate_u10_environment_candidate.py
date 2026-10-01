#!/usr/bin/env python3
"""Generate U-10 candidate evidence without creating a human decision."""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import tempfile

from semantic_guard_vnext.environment_resolution import file_digest
from semantic_guard_vnext.qualified_environment import (
    build_adoption_request_v1,
    build_candidate_eligibility_source,
    build_environment_candidate_material,
    validate_adoption_record_v1,
    validate_eligibility_source,
    validate_resolved_environment_profile_v1,
    validate_verification_profile_v4,
)


PROFILE_LOCATOR = (
    "vnext/validation/env-path-contracts/"
    "local-verification-profile-v4.candidate.json"
)
HOST_LOCATOR = (
    "vnext/validation/env-path-contracts/u10-host-identity.candidate.json"
)
CONTAINMENT_LOCATOR = (
    "vnext/validation/env-path-contracts/u10-containment-probe.candidate.json"
)
TRACE_LOCATOR = (
    "vnext/validation/env-path-contracts/"
    "u10-containment-probe-trace.candidate.jsonl"
)
ENVIRONMENT_LOCATOR = (
    "vnext/validation/env-path-contracts/"
    "u10-resolved-environment-profile.candidate.json"
)
ADOPTION_LOCATOR = (
    "vnext/validation/env-path-contracts/u10-environment-adoption-request.candidate.json"
)
SOURCE_LOCATOR = (
    "vnext/validation/env-path-contracts/u10-eligibility-source.candidate.json"
)
OWNER_EVIDENCE_LOCATOR = (
    "vnext/docs/governance-revision/"
    "public-operation-assurance-and-invocation-directive-2026-07-19.md"
)
CANDIDATE_VERSION = "1.2.0-candidate"


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


def _load_object(path: Path) -> dict:
    value = strict_json_loads(path.read_bytes())
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON root is not an object: {path}")
    return value


def _artifact_bytes(value: dict) -> bytes:
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


def _validate_strict_json_lines(raw: bytes) -> None:
    lines = raw.splitlines()
    if not lines:
        raise RuntimeError("candidate JSONL output is empty")
    for line_number, line in enumerate(lines, 1):
        try:
            value = strict_json_loads(line)
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise RuntimeError(
                f"candidate JSONL output is not strict at line {line_number}"
            ) from exc
        if not isinstance(value, dict):
            raise RuntimeError(
                f"candidate JSONL record is not an object at line {line_number}"
            )


def _write_candidate(path: Path, value: bytes, *, replace: bool) -> None:
    if path.exists() and not replace:
        raise RuntimeError(f"candidate already exists; use --replace-candidate: {path}")
    if ".candidate." not in path.name:
        raise RuntimeError(f"refusing to write a non-candidate artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def generate(repository_root: Path, *, replace: bool) -> dict:
    root = repository_root.resolve(strict=True)
    profile = _load_object(root / PROFILE_LOCATOR)
    validate_verification_profile_v4(profile)
    material = build_environment_candidate_material(
        profile,
        repository_root=root,
        environment_profile_id="environment.public-operation.u10.local-darwin-arm64",
        environment_profile_version=CANDIDATE_VERSION,
        host_evidence_locator=HOST_LOCATOR,
        containment_evidence_locator=CONTAINMENT_LOCATOR,
        containment_trace_locator=TRACE_LOCATOR,
    )
    owner_evidence = root / OWNER_EVIDENCE_LOCATOR
    decision_owner_ref = {
        "record_id": "role.human.environment_owner.public-operation.u10",
        "locator": OWNER_EVIDENCE_LOCATOR,
        "content_digest": file_digest(owner_evidence),
    }
    adoption_request = build_adoption_request_v1(
        material["resolved_environment_profile"],
        profile,
        adoption_id="adoption.environment.public-operation.u10.local-darwin-arm64",
        adoption_version=CANDIDATE_VERSION,
        decision_owner_ref=decision_owner_ref,
    )
    source = build_candidate_eligibility_source(
        adoption_request,
        repository_root=root,
        source_id="eligibility-source.environment.public-operation.u10.local-darwin-arm64",
        source_version=CANDIDATE_VERSION,
    )
    _validate_strict_json_lines(material["containment_trace_bytes"])
    outputs = {
        HOST_LOCATOR: _artifact_bytes(material["host_identity_evidence"]),
        TRACE_LOCATOR: material["containment_trace_bytes"],
        CONTAINMENT_LOCATOR: _artifact_bytes(material["containment_probe_evidence"]),
        ENVIRONMENT_LOCATOR: _artifact_bytes(material["resolved_environment_profile"]),
        ADOPTION_LOCATOR: _artifact_bytes(adoption_request),
        SOURCE_LOCATOR: _artifact_bytes(source),
    }
    for locator, encoded in outputs.items():
        _write_candidate(root / locator, encoded, replace=replace)
    validate_resolved_environment_profile_v1(
        _load_object(root / ENVIRONMENT_LOCATOR), verification_profile=profile
    )
    validate_adoption_record_v1(_load_object(root / ADOPTION_LOCATOR))
    validate_eligibility_source(_load_object(root / SOURCE_LOCATOR))
    return {
        "generation_status": "candidate_material_generated",
        "human_decision": "pending",
        "environment_use_allowed": False,
        "formal_authority": "none",
        "positive_assurance_allowed": False,
        "profile_locator": PROFILE_LOCATOR,
        "output_locators": sorted(outputs),
        "environment_basis_digest": material["resolved_environment_profile"][
            "basis_digest"
        ],
        "adoption_digest": adoption_request["adoption_digest"],
        "eligibility_source_digest": source["source_digest"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repository-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
    )
    parser.add_argument("--replace-candidate", action="store_true")
    arguments = parser.parse_args()
    print(
        json.dumps(
            generate(
                arguments.repository_root,
                replace=arguments.replace_candidate,
            ),
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
