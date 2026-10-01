"""Managed execution-environment construction for ENV-PATH-001.

The helpers here prepare bounded execution material and pre/post observations.
They do not execute commands, observe descendants, or authorize a positive
assurance claim.
"""

from __future__ import annotations

from collections.abc import Mapping
import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from .environment_governance import (
    DecisionEvidenceVerifier,
    HostIdentityVerifier,
    resolve_candidate_environment_material,
    validate_adoption_record,
    validate_candidate_environment_resolution,
)
from .environment_resolution import (
    EnvironmentResolutionError,
    canonical_digest,
    environment_schema_directory,
    observe_resolved_environment,
    validate_resolved_environment_profile,
    validate_verification_profile,
)


SNAPSHOT_VERSION = "semantic-guard-local-environment-snapshot/v1"
_SNAPSHOT_SCHEMA = (
    environment_schema_directory() / "local-environment-snapshot-v1.schema.json"
)


def _validate_snapshot_schema(value: Mapping[str, Any]) -> None:
    try:
        schema = json.loads(_SNAPSHOT_SCHEMA.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise EnvironmentResolutionError(
            "schema_unavailable", f"{_SNAPSHOT_SCHEMA}: {exc}"
        ) from exc
    issues = sorted(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(value),
        key=lambda issue: tuple(str(part) for part in issue.absolute_path),
    )
    if issues:
        issue = issues[0]
        location = "/".join(str(part) for part in issue.absolute_path) or "$"
        raise EnvironmentResolutionError(
            "environment_snapshot_v1_schema_invalid",
            f"{location}: {issue.message}",
        )


def _replay_candidate_resolution(
    supplied_resolution: Mapping[str, Any],
    *,
    candidate_profile: Mapping[str, Any],
    adoption_record: Mapping[str, Any],
    current_host_identity_ref: Mapping[str, Any],
    trusted_decision_evidence_verifier: DecisionEvidenceVerifier | None,
    trusted_host_identity_verifier: HostIdentityVerifier | None,
) -> dict[str, Any]:
    """Re-establish context and reject self-authored candidate dictionaries."""

    validate_candidate_environment_resolution(supplied_resolution)
    replayed = resolve_candidate_environment_material(
        candidate_profile,
        adoption_record=adoption_record,
        current_host_identity_ref=current_host_identity_ref,
        trusted_decision_evidence_verifier=trusted_decision_evidence_verifier,
        trusted_host_identity_verifier=trusted_host_identity_verifier,
    )
    if replayed.get("resolution_status") != "candidate_execution_material":
        raise EnvironmentResolutionError(
            "environment_resolution_replay_not_candidate",
            repr(replayed.get("reason_codes", [])),
        )
    validate_candidate_environment_resolution(replayed)
    if dict(replayed) != dict(supplied_resolution):
        raise EnvironmentResolutionError(
            "environment_resolution_replay_mismatch",
            str(supplied_resolution.get("environment_profile_ref")),
        )
    return replayed


def _bound_environment_contract(
    verification_profile: Mapping[str, Any],
    candidate_profile: Mapping[str, Any],
) -> dict[str, Any]:
    """Return only the contract whose digest is sealed into the candidate.

    A caller cannot widen inheritance or replace fixed values at execution
    time: the portable profile is first validated and then matched against the
    digest recorded by the adopted environment candidate.
    """

    validate_verification_profile(verification_profile)
    validate_resolved_environment_profile(candidate_profile)
    portable_basis = {
        "profile_id": verification_profile["profile_id"],
        "profile_version": verification_profile["profile_version"],
        "environment_contract": verification_profile["environment_contract"],
    }
    observed_digest = canonical_digest(portable_basis)
    if observed_digest != candidate_profile["verification_profile_basis_digest"]:
        raise EnvironmentResolutionError(
            "verification_profile_basis_mismatch",
            str(verification_profile.get("profile_id")),
        )
    contract = dict(verification_profile["environment_contract"])
    inherited = {str(name) for name in contract["inherited_environment_allowlist"]}
    fixed = {str(name) for name in contract["fixed_environment"]}
    overlap = sorted(inherited & fixed)
    if overlap:
        raise EnvironmentResolutionError(
            "environment_contract_variable_conflict", repr(overlap)
        )
    return contract


def build_managed_environment(
    resolution: Mapping[str, Any],
    *,
    verification_profile: Mapping[str, Any],
    candidate_profile: Mapping[str, Any],
    adoption_record: Mapping[str, Any],
    current_host_identity_ref: Mapping[str, Any],
    trusted_decision_evidence_verifier: DecisionEvidenceVerifier | None,
    trusted_host_identity_verifier: HostIdentityVerifier | None,
    parent_environment: Mapping[str, str],
) -> dict[str, str]:
    """Derive candidate environment material from the digest-bound contract.

    Returning this mapping is not execution permission.
    """

    verified_resolution = _replay_candidate_resolution(
        resolution,
        candidate_profile=candidate_profile,
        adoption_record=adoption_record,
        current_host_identity_ref=current_host_identity_ref,
        trusted_decision_evidence_verifier=trusted_decision_evidence_verifier,
        trusted_host_identity_verifier=trusted_host_identity_verifier,
    )
    contract = _bound_environment_contract(verification_profile, candidate_profile)
    normalized_names = [
        str(name) for name in contract["inherited_environment_allowlist"]
    ]
    fixed_values = {
        str(key): str(value) for key, value in contract["fixed_environment"].items()
    }
    environment = {
        name: str(parent_environment[name])
        for name in normalized_names
        if name in parent_environment
    }
    environment.update(fixed_values)
    environment["PATH"] = str(verified_resolution["effective_path"]["rendered_value"])
    return dict(sorted(environment.items()))


def render_absolute_command(
    command: Mapping[str, Any],
    *,
    resolution: Mapping[str, Any],
    verification_profile: Mapping[str, Any],
    candidate_profile: Mapping[str, Any],
    adoption_record: Mapping[str, Any],
    current_host_identity_ref: Mapping[str, Any],
    trusted_decision_evidence_verifier: DecisionEvidenceVerifier | None,
    trusted_host_identity_verifier: HostIdentityVerifier | None,
) -> list[str]:
    """Render a candidate v3 command with a digest-bound absolute executable.

    Returning the argument vector is not execution permission.
    """

    verified_resolution = _replay_candidate_resolution(
        resolution,
        candidate_profile=candidate_profile,
        adoption_record=adoption_record,
        current_host_identity_ref=current_host_identity_ref,
        trusted_decision_evidence_verifier=trusted_decision_evidence_verifier,
        trusted_host_identity_verifier=trusted_host_identity_verifier,
    )
    _bound_environment_contract(verification_profile, candidate_profile)
    tool_id = str(command["tool_id"])
    matches = [
        tool
        for tool in verified_resolution["resolved_tools"]
        if tool["tool_id"] == tool_id
    ]
    if len(matches) != 1:
        raise EnvironmentResolutionError("command_tool_resolution_not_unique", tool_id)
    resolved = Path(str(matches[0]["resolved_path"]))
    if not resolved.is_absolute():
        raise EnvironmentResolutionError(
            "command_executable_not_absolute", str(resolved)
        )
    return [str(resolved), *[str(item) for item in command["arguments"]]]


def capture_tool_observation(
    candidate_profile: Mapping[str, Any],
    *,
    host_identity_ref: Mapping[str, Any],
    observed_platform: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Capture a path-independent observation using candidate-bound paths."""

    return observe_resolved_environment(
        candidate_profile,
        host_identity_ref=host_identity_ref,
        observed_platform=observed_platform,
    )


def compare_pre_post_observations(
    before: Mapping[str, Any], after: Mapping[str, Any]
) -> dict[str, Any]:
    reasons: list[str] = []
    for field, code in (
        ("host_identity_ref", "host_identity_changed_during_execution"),
        ("platform", "platform_changed_during_execution"),
        ("resolved_tools", "tool_changed_during_execution"),
        ("effective_path", "effective_path_changed_during_execution"),
    ):
        if before.get(field) != after.get(field):
            reasons.append(code)
    status = "stable" if not reasons else "requalification_required"
    return {
        "observation_status": status,
        "reason_codes": reasons,
        "positive_assurance_allowed": False,
        "formal_authority": "none",
    }


def _observation_binding_reasons(
    observation: Mapping[str, Any],
    expected: Mapping[str, Any],
    *,
    phase: str,
) -> list[str]:
    reasons: list[str] = []
    for field, suffix in (
        ("host_identity_ref", "host_not_bound_to_candidate_resolution"),
        ("platform", "platform_not_bound_to_candidate_resolution"),
        ("resolved_tools", "tools_not_bound_to_candidate_resolution"),
        ("effective_path", "effective_path_not_bound_to_candidate_resolution"),
    ):
        if observation.get(field) != expected.get(field):
            reasons.append(f"{phase}_{suffix}")
    return reasons


def _validate_snapshot_subject_binding(
    *,
    verification_profile: Mapping[str, Any],
    candidate_profile: Mapping[str, Any],
    adoption_record: Mapping[str, Any],
    resolution: Mapping[str, Any],
    trusted_decision_evidence_verifier: DecisionEvidenceVerifier | None,
    trusted_host_identity_verifier: HostIdentityVerifier | None,
) -> dict[str, Any]:
    """Validate the closed profile/candidate/adoption/resolution chain."""

    _bound_environment_contract(verification_profile, candidate_profile)
    validate_adoption_record(adoption_record)
    validate_candidate_environment_resolution(resolution)
    candidate_ref = {
        "environment_profile_id": candidate_profile["environment_profile_id"],
        "environment_profile_version": candidate_profile["environment_profile_version"],
        "basis_digest": candidate_profile["basis_digest"],
    }
    if adoption_record["environment_profile_ref"] != candidate_ref:
        raise EnvironmentResolutionError(
            "snapshot_adoption_candidate_mismatch", str(candidate_ref)
        )
    if resolution["environment_profile_ref"] != candidate_ref:
        raise EnvironmentResolutionError(
            "snapshot_resolution_candidate_mismatch", str(candidate_ref)
        )
    adoption_ref = {
        "adoption_id": adoption_record["adoption_id"],
        "adoption_version": adoption_record["adoption_version"],
        "adoption_digest": adoption_record["adoption_digest"],
    }
    if resolution["adoption_ref"] != adoption_ref:
        raise EnvironmentResolutionError(
            "snapshot_resolution_adoption_mismatch", str(adoption_ref)
        )
    expected = resolution["current_observation"]
    if expected.get("host_identity_ref") != candidate_profile["host_identity_ref"]:
        raise EnvironmentResolutionError(
            "snapshot_resolution_host_candidate_mismatch", str(candidate_ref)
        )
    if expected.get("platform") != candidate_profile["platform"]:
        raise EnvironmentResolutionError(
            "snapshot_resolution_platform_candidate_mismatch", str(candidate_ref)
        )
    if expected.get("resolved_tools") != candidate_profile["resolved_tools"]:
        raise EnvironmentResolutionError(
            "snapshot_resolution_tools_candidate_mismatch", str(candidate_ref)
        )
    if expected.get("effective_path") != candidate_profile["effective_path"]:
        raise EnvironmentResolutionError(
            "snapshot_resolution_path_candidate_mismatch", str(candidate_ref)
        )
    verifier_cases = (
        (
            "decision_evidence",
            trusted_decision_evidence_verifier,
            adoption_record,
        ),
        (
            "host_identity",
            trusted_host_identity_verifier,
            {
                "environment_profile_ref": candidate_ref,
                "candidate_host_identity_ref": candidate_profile["host_identity_ref"],
                "current_host_identity_ref": expected["host_identity_ref"],
            },
        ),
    )
    for verifier_name, verifier, material in verifier_cases:
        if verifier is None:
            raise EnvironmentResolutionError(
                f"snapshot_{verifier_name}_verifier_missing", verifier_name
            )
        verifier_ref = getattr(verifier, "verifier_ref", None)
        expected_ref = resolution["trust_verifier_refs"][verifier_name]
        if not isinstance(verifier_ref, Mapping) or dict(verifier_ref) != expected_ref:
            raise EnvironmentResolutionError(
                f"snapshot_{verifier_name}_verifier_mismatch", verifier_name
            )
        try:
            verified = bool(verifier(copy.deepcopy(dict(material))))
        except Exception as exc:
            raise EnvironmentResolutionError(
                f"snapshot_{verifier_name}_verifier_failed", verifier_name
            ) from exc
        if not verified:
            raise EnvironmentResolutionError(
                f"snapshot_{verifier_name}_unverified", verifier_name
            )
    return {
        "candidate_ref": candidate_ref,
        "adoption_ref": adoption_ref,
        "expected_observation": expected,
    }


def build_environment_snapshot(
    candidate_profile: Mapping[str, Any],
    *,
    verification_profile: Mapping[str, Any],
    adoption_record: Mapping[str, Any],
    resolution: Mapping[str, Any],
    trusted_decision_evidence_verifier: DecisionEvidenceVerifier | None,
    trusted_host_identity_verifier: HostIdentityVerifier | None,
    managed_environment: Mapping[str, str],
    pre_observation: Mapping[str, Any],
    post_observation: Mapping[str, Any],
) -> dict[str, Any]:
    binding = _validate_snapshot_subject_binding(
        verification_profile=verification_profile,
        candidate_profile=candidate_profile,
        adoption_record=adoption_record,
        resolution=resolution,
        trusted_decision_evidence_verifier=trusted_decision_evidence_verifier,
        trusted_host_identity_verifier=trusted_host_identity_verifier,
    )
    comparison = compare_pre_post_observations(pre_observation, post_observation)
    binding_reasons = [
        *_observation_binding_reasons(
            pre_observation,
            binding["expected_observation"],
            phase="pre",
        ),
        *_observation_binding_reasons(
            post_observation,
            binding["expected_observation"],
            phase="post",
        ),
    ]
    if binding_reasons:
        comparison = {
            "observation_status": "requalification_required",
            "reason_codes": sorted(
                set([*comparison["reason_codes"], *binding_reasons])
            ),
            "positive_assurance_allowed": False,
            "formal_authority": "none",
        }
    path_value = str(managed_environment.get("PATH", ""))
    if path_value != candidate_profile["effective_path"]["rendered_value"]:
        comparison = {
            "observation_status": "requalification_required",
            "reason_codes": sorted(
                set([*comparison["reason_codes"], "effective_path_not_adopted_value"])
            ),
            "positive_assurance_allowed": False,
            "formal_authority": "none",
        }
    snapshot: dict[str, Any] = {
        "schema_version": SNAPSHOT_VERSION,
        "environment_profile_ref": binding["candidate_ref"],
        "verification_profile_basis_digest": candidate_profile[
            "verification_profile_basis_digest"
        ],
        "adoption_ref": binding["adoption_ref"],
        "candidate_environment_resolution_ref": {
            "schema_version": resolution["schema_version"],
            "environment_profile_ref": dict(resolution["environment_profile_ref"]),
            "adoption_ref": dict(resolution["adoption_ref"]),
            "trust_verifier_refs": dict(resolution["trust_verifier_refs"]),
            "trust_claim_states": dict(resolution["trust_claim_states"]),
            "resolution_digest": resolution["resolution_digest"],
        },
        "effective_path": dict(candidate_profile["effective_path"]),
        "effective_path_observation": {
            "rendered_value": path_value,
            "content_digest": {
                "algorithm": "sha256",
                "value": hashlib.sha256(path_value.encode("utf-8")).hexdigest(),
            },
        },
        "pre_observation": dict(pre_observation),
        "post_observation": dict(post_observation),
        "observation_status": comparison["observation_status"],
        "reason_codes": comparison["reason_codes"],
        "child_process_observation": "not_implemented",
        "formal_authority": "none",
        "positive_assurance_allowed": False,
        "limitations": [
            "No child-process executable observer is attached.",
            "Verifier callback success is a supplied claim, not externally rooted authenticity.",
            "The snapshot cannot establish positive assurance or human acceptance.",
        ],
    }
    snapshot["snapshot_digest"] = canonical_digest(snapshot)
    validate_environment_snapshot(snapshot)
    return snapshot


def validate_environment_snapshot(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """Replay a serialized candidate snapshot without granting trust.

    This validates closure and the hard authority ceiling.  It cannot replace
    re-observation of the host, tools, descendants, or an external harness.
    """

    _validate_snapshot_schema(snapshot)
    material = copy.deepcopy(dict(snapshot))
    observed_digest = material.pop("snapshot_digest")
    if observed_digest != canonical_digest(material):
        raise EnvironmentResolutionError(
            "environment_snapshot_digest_mismatch",
            str(snapshot.get("environment_profile_ref")),
        )
    if (
        snapshot["formal_authority"] != "none"
        or snapshot["positive_assurance_allowed"] is not False
        or snapshot["child_process_observation"] != "not_implemented"
    ):
        raise EnvironmentResolutionError(
            "environment_snapshot_authority_ceiling_mismatch",
            str(snapshot.get("environment_profile_ref")),
        )
    observed_path = str(snapshot["effective_path_observation"]["rendered_value"])
    expected_path = str(snapshot["effective_path"]["rendered_value"])
    observed_path_digest = {
        "algorithm": "sha256",
        "value": hashlib.sha256(observed_path.encode("utf-8")).hexdigest(),
    }
    if (
        observed_path != expected_path
        or snapshot["effective_path_observation"]["content_digest"]
        != observed_path_digest
    ):
        raise EnvironmentResolutionError(
            "environment_snapshot_effective_path_mismatch",
            observed_path,
        )
    replayed = compare_pre_post_observations(
        snapshot["pre_observation"], snapshot["post_observation"]
    )
    if snapshot["observation_status"] == "stable" and (
        replayed["observation_status"] != "stable" or snapshot["reason_codes"]
    ):
        raise EnvironmentResolutionError(
            "environment_snapshot_observation_status_mismatch",
            str(snapshot["reason_codes"]),
        )
    if (
        snapshot["observation_status"] == "requalification_required"
        and not snapshot["reason_codes"]
    ):
        raise EnvironmentResolutionError(
            "environment_snapshot_requalification_reason_missing",
            str(snapshot.get("environment_profile_ref")),
        )
    return copy.deepcopy(dict(snapshot))


__all__ = [
    "SNAPSHOT_VERSION",
    "build_environment_snapshot",
    "build_managed_environment",
    "capture_tool_observation",
    "compare_pre_post_observations",
    "render_absolute_command",
    "validate_environment_snapshot",
]
