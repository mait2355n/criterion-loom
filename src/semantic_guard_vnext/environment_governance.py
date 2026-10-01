"""Candidate/adoption separation for ENV-PATH-001.

An adoption document and caller-supplied verifier are only candidate material.
Until a control-plane trust registry or signature root is integrated, this
module may construct bounded execution material but cannot authorize its use.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
import copy
import json
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from .environment_resolution import (
    EnvironmentResolutionError,
    canonical_digest,
    effective_path_from_resolved_tools,
    environment_schema_directory,
    observe_resolved_environment,
    validate_content_addressed_ref,
    validate_host_identity_ref,
    validate_resolved_environment_profile,
)


ADOPTION_VERSION = "semantic-guard-local-environment-adoption/v0"
CANDIDATE_RESOLUTION_VERSION = (
    "semantic-guard-adopted-environment-candidate-resolution/v1"
)
_SCHEMA_PATH = environment_schema_directory() / "local-environment-adoption.schema.json"
_CANDIDATE_RESOLUTION_SCHEMA_PATH = (
    environment_schema_directory() / "resolved-local-environment-profile.schema.json"
)


DecisionEvidenceVerifier = Callable[[Mapping[str, Any]], bool]
HostIdentityVerifier = Callable[[Mapping[str, Any]], bool]


def _validate_schema(value: Mapping[str, Any]) -> None:
    try:
        schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise EnvironmentResolutionError(
            "schema_unavailable", f"{_SCHEMA_PATH}: {exc}"
        ) from exc
    issues = sorted(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(value),
        key=lambda issue: tuple(str(part) for part in issue.absolute_path),
    )
    if issues:
        issue = issues[0]
        location = "/".join(str(part) for part in issue.absolute_path) or "$"
        raise EnvironmentResolutionError(
            "environment_adoption_schema_invalid",
            f"{location}: {issue.message}",
        )


def validate_adoption_record(record: Mapping[str, Any]) -> None:
    _validate_schema(record)
    material = dict(record)
    observed = material.pop("adoption_digest")
    if canonical_digest(material) != observed:
        raise EnvironmentResolutionError(
            "environment_adoption_digest_mismatch", str(record.get("adoption_id"))
        )


def validate_candidate_environment_resolution(resolution: Mapping[str, Any]) -> None:
    """Validate closed candidate execution material with no use authority."""

    try:
        schema_document = json.loads(
            _CANDIDATE_RESOLUTION_SCHEMA_PATH.read_text(encoding="utf-8")
        )
        schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$defs": schema_document["$defs"],
            "$ref": "#/$defs/candidate_environment_resolution",
        }
        Draft202012Validator.check_schema(schema)
    except (KeyError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise EnvironmentResolutionError(
            "schema_unavailable", f"{_CANDIDATE_RESOLUTION_SCHEMA_PATH}: {exc}"
        ) from exc
    issues = sorted(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(
            resolution
        ),
        key=lambda issue: tuple(str(part) for part in issue.absolute_path),
    )
    if issues:
        issue = issues[0]
        location = "/".join(str(part) for part in issue.absolute_path) or "$"
        raise EnvironmentResolutionError(
            "candidate_environment_resolution_schema_invalid",
            f"{location}: {issue.message}",
        )
    material = dict(resolution)
    observed_digest = material.pop("resolution_digest")
    if canonical_digest(material) != observed_digest:
        raise EnvironmentResolutionError(
            "candidate_environment_resolution_digest_mismatch",
            str(resolution.get("environment_profile_ref")),
        )
    observation = resolution["current_observation"]
    if observation["resolved_tools"] != resolution["resolved_tools"]:
        raise EnvironmentResolutionError(
            "candidate_environment_resolution_tool_projection_mismatch",
            str(resolution.get("environment_profile_ref")),
        )
    if observation["effective_path"] != resolution["effective_path"]:
        raise EnvironmentResolutionError(
            "candidate_environment_resolution_path_projection_mismatch",
            str(resolution.get("environment_profile_ref")),
        )
    derived_path = effective_path_from_resolved_tools(resolution["resolved_tools"])
    if derived_path != resolution["effective_path"]:
        raise EnvironmentResolutionError(
            "candidate_environment_resolution_path_derivation_mismatch",
            str(resolution.get("environment_profile_ref")),
        )


def build_adoption_request(
    candidate_profile: Mapping[str, Any],
    *,
    adoption_id: str,
    adoption_version: str,
    decision_owner_ref: Mapping[str, Any],
) -> dict[str, Any]:
    """Build a pending request without generating a human decision."""

    validate_resolved_environment_profile(candidate_profile)
    record: dict[str, Any] = {
        "schema_version": ADOPTION_VERSION,
        "record_kind": "adoption_request",
        "adoption_id": adoption_id,
        "adoption_version": adoption_version,
        "human_decision": "pending",
        "environment_profile_ref": {
            "environment_profile_id": candidate_profile["environment_profile_id"],
            "environment_profile_version": candidate_profile[
                "environment_profile_version"
            ],
            "basis_digest": candidate_profile["basis_digest"],
        },
        "decision_owner_ref": dict(decision_owner_ref),
        "decision_evidence_ref": None,
        "trusted_entrypoint_ref": None,
        "formal_authority": "none",
        "positive_assurance_allowed": False,
        "limitations": [
            "This request is not a human decision and cannot be used as environment adoption.",
            "Environment adoption does not grant engineering-verdict or final-acceptance authority.",
        ],
    }
    record["adoption_digest"] = canonical_digest(record)
    validate_adoption_record(record)
    return record


def _unresolved(code: str) -> dict[str, Any]:
    return {
        "resolution_status": "unresolved",
        "reason_codes": [code],
        "environment_use_allowed": False,
        "formal_authority": "none",
        "positive_assurance_allowed": False,
    }


def _requalification(*codes: str) -> dict[str, Any]:
    return {
        "resolution_status": "requalification_required",
        "reason_codes": sorted(set(codes)),
        "environment_use_allowed": False,
        "formal_authority": "none",
        "positive_assurance_allowed": False,
    }


def _trusted_verifier_ref(
    verifier: Callable[[Mapping[str, Any]], bool] | None,
) -> dict[str, Any] | None:
    if verifier is None:
        return None
    verifier_ref = getattr(verifier, "verifier_ref", None)
    if not isinstance(verifier_ref, Mapping):
        return None
    try:
        validate_content_addressed_ref(verifier_ref)
    except EnvironmentResolutionError:
        return None
    return copy.deepcopy(dict(verifier_ref))


def _verify_external(
    verifier: Callable[[Mapping[str, Any]], bool],
    material: Mapping[str, Any],
) -> str:
    try:
        supplied = copy.deepcopy(dict(material))
        return "verifier_claim_accepted" if bool(verifier(supplied)) else "rejected"
    except Exception:  # Trust-adapter failures must never permit execution.
        return "failed"


def resolve_candidate_environment_material(
    candidate_profile: Mapping[str, Any],
    *,
    adoption_record: Mapping[str, Any] | None,
    current_host_identity_ref: Mapping[str, Any],
    trusted_decision_evidence_verifier: DecisionEvidenceVerifier | None,
    trusted_host_identity_verifier: HostIdentityVerifier | None,
    current_observation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Construct candidate material from fresh local observations and claims.

    ``current_observation`` is accepted only as deprecated, untrusted input and
    is deliberately ignored.  Ready state is derived from a fresh observation
    of the absolute paths sealed in ``candidate_profile``.
    """

    validate_resolved_environment_profile(candidate_profile)
    if adoption_record is None:
        return _unresolved("environment_adoption_missing")
    try:
        validate_adoption_record(adoption_record)
    except EnvironmentResolutionError as exc:
        return _unresolved(exc.code)
    expected_ref = {
        "environment_profile_id": candidate_profile["environment_profile_id"],
        "environment_profile_version": candidate_profile["environment_profile_version"],
        "basis_digest": candidate_profile["basis_digest"],
    }
    if adoption_record["environment_profile_ref"] != expected_ref:
        return _unresolved("environment_adoption_basis_mismatch")
    if adoption_record["human_decision"] != "accept":
        return _unresolved("environment_not_accepted")
    if adoption_record["record_kind"] != "adoption_decision":
        return _unresolved("environment_adoption_decision_missing")
    if trusted_decision_evidence_verifier is None:
        return _unresolved("decision_evidence_verifier_missing")
    decision_verifier_ref = _trusted_verifier_ref(trusted_decision_evidence_verifier)
    if decision_verifier_ref is None:
        return _unresolved("decision_evidence_verifier_ref_invalid")
    decision_status = _verify_external(
        trusted_decision_evidence_verifier, adoption_record
    )
    if decision_status == "failed":
        return _unresolved("decision_evidence_verifier_failed")
    if decision_status != "verifier_claim_accepted":
        return _unresolved("decision_evidence_unverified")

    try:
        validate_host_identity_ref(current_host_identity_ref)
    except EnvironmentResolutionError:
        return _unresolved("current_host_identity_ref_invalid")
    if trusted_host_identity_verifier is None:
        return _unresolved("host_identity_verifier_missing")
    host_verifier_ref = _trusted_verifier_ref(trusted_host_identity_verifier)
    if host_verifier_ref is None:
        return _unresolved("host_identity_verifier_ref_invalid")

    host_verification_material = {
        "environment_profile_ref": expected_ref,
        "candidate_host_identity_ref": candidate_profile["host_identity_ref"],
        "current_host_identity_ref": dict(current_host_identity_ref),
    }
    host_status = _verify_external(
        trusted_host_identity_verifier, host_verification_material
    )
    if host_status == "failed":
        return _unresolved("host_identity_verifier_failed")
    if host_status != "verifier_claim_accepted":
        return _unresolved("host_identity_unverified")

    # Never use a caller-authored observation to establish readiness.  The
    # path, real target, version, and file digest are observed again here.
    del current_observation
    try:
        observed_environment = observe_resolved_environment(
            candidate_profile,
            host_identity_ref=current_host_identity_ref,
        )
    except EnvironmentResolutionError as exc:
        return _requalification("environment_reobservation_failed", exc.code)

    drift: list[str] = []
    if (
        observed_environment.get("host_identity_ref")
        != candidate_profile["host_identity_ref"]
    ):
        drift.append("host_identity_drift")
    if observed_environment.get("platform") != candidate_profile["platform"]:
        drift.append("platform_drift")
    if (
        observed_environment.get("resolved_tools")
        != candidate_profile["resolved_tools"]
    ):
        drift.append("resolved_tool_drift")
    if (
        observed_environment.get("effective_path")
        != candidate_profile["effective_path"]
    ):
        drift.append("effective_path_drift")
    if drift:
        return _requalification(*drift)

    result: dict[str, Any] = {
        "schema_version": CANDIDATE_RESOLUTION_VERSION,
        "resolution_status": "candidate_execution_material",
        "reason_codes": ["external_trust_control_not_integrated"],
        "environment_use_allowed": False,
        "formal_authority": "none",
        "positive_assurance_allowed": False,
        "environment_profile_ref": expected_ref,
        "adoption_ref": {
            "adoption_id": adoption_record["adoption_id"],
            "adoption_version": adoption_record["adoption_version"],
            "adoption_digest": adoption_record["adoption_digest"],
        },
        "trust_verifier_refs": {
            "decision_evidence": decision_verifier_ref,
            "host_identity": host_verifier_ref,
        },
        "trust_claim_states": {
            "decision_evidence": decision_status,
            "host_identity": host_status,
        },
        "current_observation": observed_environment,
        "observation_source": "internal_reobservation",
        "resolved_tools": copy.deepcopy(observed_environment["resolved_tools"]),
        "effective_path": copy.deepcopy(observed_environment["effective_path"]),
        "child_process_observation": "not_implemented",
        "limitations": [
            "Child-process executable observation is not implemented.",
            "Caller-supplied verifier success is only a claim until a control-plane trust registry or signature root resolves it.",
            "This record constructs candidate execution material but does not permit execution or support positive assurance.",
        ],
    }
    result["resolution_digest"] = canonical_digest(result)
    validate_candidate_environment_resolution(result)
    return result


def resolve_adopted_environment(
    candidate_profile: Mapping[str, Any],
    *,
    adoption_record: Mapping[str, Any] | None,
    current_host_identity_ref: Mapping[str, Any],
    trusted_decision_evidence_verifier: DecisionEvidenceVerifier | None,
    trusted_host_identity_verifier: HostIdentityVerifier | None,
    current_observation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Compatibility alias for the pre-hard-cap API name.

    No adopted environment is resolved by v1.  New callers must use
    :func:`resolve_candidate_environment_material` and treat its result as
    non-executable candidate material.
    """

    return resolve_candidate_environment_material(
        candidate_profile,
        adoption_record=adoption_record,
        current_host_identity_ref=current_host_identity_ref,
        trusted_decision_evidence_verifier=trusted_decision_evidence_verifier,
        trusted_host_identity_verifier=trusted_host_identity_verifier,
        current_observation=current_observation,
    )


__all__ = [
    "ADOPTION_VERSION",
    "CANDIDATE_RESOLUTION_VERSION",
    "DecisionEvidenceVerifier",
    "HostIdentityVerifier",
    "build_adoption_request",
    "resolve_candidate_environment_material",
    "resolve_adopted_environment",
    "validate_adoption_record",
    "validate_candidate_environment_resolution",
]
