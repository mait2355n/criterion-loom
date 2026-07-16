"""Deterministic, bounded audit of action evidence.

This module keeps occurrence, actor identity, authority, procedure, artifact
provenance, authenticity, and causality as independent claim classes.  It
never dispatches an action, grants authority, or performs human acceptance.

The validators establish record-internal identity, digest, reference, and
policy closure.  They do not themselves verify a cryptographic signature,
authenticate a clock or trust root, or prove that an external record exists.
"""

from __future__ import annotations

import copy
from datetime import datetime, timedelta
from functools import lru_cache
import hashlib
import json
from typing import Any, Iterable, Mapping, Sequence

from jsonschema import Draft202012Validator, FormatChecker

from .schema_access import schema_directory


PROFILE_VERSION = "action-assurance-profile/v1"
EVENT_VERSION = "action-event/v0"
OBSERVATION_VERSION = "action-observation/v0"
GRANT_VERSION = "authority-grant/v0"
ASSESSMENT_VERSION = "action-evidence-assessment/v0"

CLAIM_CLASSES = (
    "occurrence",
    "identity",
    "authority",
    "procedure",
    "artifact_provenance",
    "authenticity",
    "causality",
)
NON_OCCURRENCE_EVIDENCE_KINDS = {
    "prose_description",
    "tool_request",
    "self_report",
}

_SCHEMA_DIR = schema_directory()
_AUDIT_LIMITATION = (
    "semantic-guard audits supplied records only; it does not dispatch the "
    "action, grant authority, release a stop condition, or accept the result."
)
_TRUST_LIMITATION = (
    "Signature, clock, and trust-root records are structurally bound but their "
    "external existence, cryptographic validity, and authority are not "
    "established by this deterministic validator."
)
_CAUSAL_LIMITATION = (
    "An exact trace link is bounded causal evidence under the adopted profile, "
    "not universal proof that no omitted cause exists."
)


class ActionEvidenceError(ValueError):
    """Raised when an action-evidence contract fails closed."""


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _digest(value: Any) -> dict[str, str]:
    return {"algorithm": "sha256", "value": _sha256(value)}


def _without(value: Mapping[str, Any], *fields: str) -> dict[str, Any]:
    result = copy.deepcopy(dict(value))
    for field in fields:
        result.pop(field, None)
    return result


def _parse_time(value: str, location: str) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith(("Z", "z")) else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ActionEvidenceError(f"invalid timestamp at {location}: {value}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ActionEvidenceError(f"timestamp lacks timezone at {location}: {value}")
    return parsed


def _format_path(parts: Iterable[Any]) -> str:
    return "/".join(str(part) for part in parts) or "/"


@lru_cache(maxsize=None)
def _schema(name: str) -> dict[str, Any]:
    return json.loads((_SCHEMA_DIR / name).read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def _validator(name: str) -> Draft202012Validator:
    schema = _schema(name)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


@lru_cache(maxsize=None)
def _subschema_validator(definition: str) -> Draft202012Validator:
    root = _schema("action-evidence.schema.json")
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$defs": root["$defs"],
        "$ref": f"#/$defs/{definition}",
    }
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _validate_schema(
    value: Mapping[str, Any],
    validator: Draft202012Validator,
    contract: str,
) -> None:
    issues = sorted(
        validator.iter_errors(value),
        key=lambda issue: tuple(str(part) for part in issue.absolute_path),
    )
    if issues:
        issue = issues[0]
        raise ActionEvidenceError(
            f"{contract} schema violation at {_format_path(issue.absolute_path)}: "
            f"{issue.message}"
        )


def _require_unique(
    values: Sequence[Mapping[str, Any]],
    field: str,
    location: str,
) -> None:
    identities = [str(value[field]) for value in values]
    duplicates = sorted(
        {identity for identity in identities if identities.count(identity) > 1}
    )
    if duplicates:
        raise ActionEvidenceError(
            f"duplicate {field} at {location}: {duplicates!r}"
        )


def _identity_key(value: Mapping[str, Any]) -> tuple[str, str, str]:
    return (
        str(value["entity_id"]),
        str(value["entity_version"]),
        str(value["content_digest"]["value"]),
    )


def _sort_identities(values: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        (copy.deepcopy(dict(value)) for value in values),
        key=_identity_key,
    )


def _trust_root_key(value: Mapping[str, Any]) -> tuple[str, str, str]:
    return (
        str(value["root_id"]),
        str(value["root_version"]),
        str(value["content_digest"]["value"]),
    )


def _sort_trust_roots(
    values: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    return sorted(
        (copy.deepcopy(dict(value)) for value in values),
        key=_trust_root_key,
    )


def _identity_allowed(
    value: Mapping[str, Any], allowed: Sequence[Mapping[str, Any]]
) -> bool:
    return _identity_key(value) in {_identity_key(item) for item in allowed}


def _trust_root_allowed(
    value: Mapping[str, Any] | None,
    allowed: Sequence[Mapping[str, Any]],
) -> bool:
    return value is not None and _trust_root_key(value) in {
        _trust_root_key(item) for item in allowed
    }


def _artifact_key(value: Mapping[str, Any]) -> tuple[str, str, str]:
    return (
        str(value["artifact_id"]),
        str(value["role"]),
        str(value["content_digest"]["value"]),
    )


def _sort_artifacts(values: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        (copy.deepcopy(dict(value)) for value in values),
        key=_artifact_key,
    )


def _event_ref(event: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "event_id": event["event_id"],
        "event_digest": copy.deepcopy(event["event_digest"]),
    }


def _profile_ref(profile: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "profile_id": profile["profile_id"],
        "profile_version": profile["profile_version"],
        "profile_digest": copy.deepcopy(profile["profile_digest"]),
    }


def _profile_basis_material(profile: Mapping[str, Any]) -> dict[str, Any]:
    """Return the non-cyclic content a human adoption decision must target."""

    return _without(
        profile,
        "adoption_state",
        "human_decision_ref",
        "profile_basis_digest",
        "profile_digest",
    )


def build_action_assurance_profile(
    *,
    profile_id: str,
    profile_version: str,
    adoption_state: str,
    required_claim_classes: Sequence[str],
    occurrence_capable_evidence_kinds: Sequence[str],
    observer_policy: Mapping[str, Any],
    time_policy: Mapping[str, Any],
    authority_policy: Mapping[str, Any],
    procedure_policy: Mapping[str, Any],
    artifact_policy: Mapping[str, Any],
    authenticity_policy: Mapping[str, Any],
    causality_policy: Mapping[str, Any],
    threat_assumptions: Sequence[str],
    limitations: Sequence[str],
    human_decision_ref: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    profile: dict[str, Any] = {
        "schema_version": PROFILE_VERSION,
        "profile_id": profile_id,
        "profile_version": profile_version,
        "adoption_state": adoption_state,
        "human_decision_ref": (
            copy.deepcopy(dict(human_decision_ref))
            if human_decision_ref is not None
            else None
        ),
        "required_claim_classes": sorted(set(required_claim_classes)),
        "occurrence_capable_evidence_kinds": sorted(
            set(occurrence_capable_evidence_kinds)
        ),
        "observer_policy": {
            "accepted_trust_classes": sorted(
                set(observer_policy["accepted_trust_classes"])
            ),
            "allowed_observers": _sort_identities(
                observer_policy["allowed_observers"]
            ),
            "independence_required_for": sorted(
                set(observer_policy["independence_required_for"])
            ),
            "self_observation_max_trust": observer_policy[
                "self_observation_max_trust"
            ],
        },
        "time_policy": {
            "trusted_time_required_for": sorted(
                set(time_policy["trusted_time_required_for"])
            ),
            "max_event_age_seconds": time_policy["max_event_age_seconds"],
            "untrusted_time_result": time_policy["untrusted_time_result"],
            "allowed_clock_identities": _sort_identities(
                time_policy["allowed_clock_identities"]
            ),
            "allowed_trust_roots": _sort_trust_roots(
                time_policy["allowed_trust_roots"]
            ),
        },
        "authority_policy": {
            "explicit_grant_required": authority_policy[
                "explicit_grant_required"
            ],
            "grant_record_digest_required": authority_policy[
                "grant_record_digest_required"
            ],
            "signed_grant_required": authority_policy[
                "signed_grant_required"
            ],
            "allowed_grantors": _sort_identities(
                authority_policy["allowed_grantors"]
            ),
        },
        "procedure_policy": {
            "required_stages": sorted(
                (
                    copy.deepcopy(dict(item))
                    for item in procedure_policy["required_stages"]
                ),
                key=lambda item: (item["order"], item["stage_id"]),
            ),
            "stop_conditions": sorted(
                (
                    copy.deepcopy(dict(item))
                    for item in procedure_policy["stop_conditions"]
                ),
                key=lambda item: item["condition_id"],
            ),
        },
        "artifact_policy": {
            "required_input_roles": sorted(
                set(artifact_policy["required_input_roles"])
            ),
            "required_output_roles": sorted(
                set(artifact_policy["required_output_roles"])
            ),
            "allowed_digest_algorithms": sorted(
                set(artifact_policy["allowed_digest_algorithms"])
            ),
        },
        "authenticity_policy": {
            "signature_required": authenticity_policy["signature_required"],
            "verified_signature_required": authenticity_policy[
                "verified_signature_required"
            ],
            "external_trust_root_required": authenticity_policy[
                "external_trust_root_required"
            ],
            "external_clock_required": authenticity_policy[
                "external_clock_required"
            ],
            "allowed_signers": _sort_identities(
                authenticity_policy["allowed_signers"]
            ),
            "allowed_verifiers": _sort_identities(
                authenticity_policy["allowed_verifiers"]
            ),
            "allowed_signature_algorithms": sorted(
                set(authenticity_policy["allowed_signature_algorithms"])
            ),
        },
        "causality_policy": {
            "explicit_observation_required": causality_policy[
                "explicit_observation_required"
            ],
            "accepted_methods": sorted(
                set(causality_policy["accepted_methods"])
            ),
            "independent_observer_required": causality_policy[
                "independent_observer_required"
            ],
        },
        "threat_assumptions": sorted(set(threat_assumptions)),
        "limitations": sorted(set(limitations)),
    }
    profile["profile_basis_digest"] = _digest(_profile_basis_material(profile))
    profile["profile_digest"] = _digest(profile)
    validate_action_assurance_profile(profile)
    return profile


def validate_action_assurance_profile(profile: Mapping[str, Any]) -> None:
    _validate_schema(
        profile,
        _validator("action-assurance-profile.schema.json"),
        "action assurance profile",
    )
    stages = list(profile["procedure_policy"]["required_stages"])
    _require_unique(stages, "stage_id", "procedure_policy.required_stages")
    _require_unique(stages, "order", "procedure_policy.required_stages")
    if sorted(int(item["order"]) for item in stages) != list(range(len(stages))):
        raise ActionEvidenceError(
            "procedure stage order must be contiguous and start at zero"
        )
    conditions = list(profile["procedure_policy"]["stop_conditions"])
    _require_unique(
        conditions,
        "condition_id",
        "procedure_policy.stop_conditions",
    )
    identity_lists = (
        ("observer_policy.allowed_observers", profile["observer_policy"]["allowed_observers"]),
        ("time_policy.allowed_clock_identities", profile["time_policy"]["allowed_clock_identities"]),
        ("authority_policy.allowed_grantors", profile["authority_policy"]["allowed_grantors"]),
        ("authenticity_policy.allowed_signers", profile["authenticity_policy"]["allowed_signers"]),
        ("authenticity_policy.allowed_verifiers", profile["authenticity_policy"]["allowed_verifiers"]),
    )
    for location, values in identity_lists:
        _require_unique(list(values), "entity_id", location)
    _require_unique(
        list(profile["time_policy"]["allowed_trust_roots"]),
        "root_id",
        "time_policy.allowed_trust_roots",
    )
    expected_basis = _digest(_profile_basis_material(profile))
    if profile["profile_basis_digest"] != expected_basis:
        raise ActionEvidenceError("action assurance profile basis digest mismatch")
    if profile["adoption_state"] == "adopted":
        decision = profile["human_decision_ref"]
        if decision["decided_by"] != decision["decision_maker_identity"][
            "entity_id"
        ]:
            raise ActionEvidenceError(
                "human decision identity does not match decided_by"
            )
        expected_target = {
            "decision_kind": "adopt_action_assurance_profile",
            "target_id": profile["profile_id"],
            "target_version": profile["profile_version"],
            "target_basis_digest": profile["profile_basis_digest"],
        }
        for field, expected_value in expected_target.items():
            if decision[field] != expected_value:
                raise ActionEvidenceError(
                    f"human adoption decision {field} does not target this profile basis"
                )
    authenticity = profile["authenticity_policy"]
    if authenticity["verified_signature_required"] and not authenticity[
        "signature_required"
    ]:
        raise ActionEvidenceError(
            "verified_signature_required cannot be true when signature_required is false"
        )
    expected = _digest(_without(profile, "profile_digest"))
    if profile["profile_digest"] != expected:
        raise ActionEvidenceError("action assurance profile digest mismatch")


def build_action_event(
    *,
    action_spec: Mapping[str, Any],
    actor_identity: Mapping[str, Any],
    environment_identity: Mapping[str, Any],
    occurred_at: str,
    time_attestation: Mapping[str, Any],
    execution_status: str,
    input_artifacts: Sequence[Mapping[str, Any]],
    output_artifacts: Sequence[Mapping[str, Any]],
    procedure_stages: Sequence[Mapping[str, Any]],
    stop_conditions: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    material = {
        "schema_version": EVENT_VERSION,
        "action_spec": copy.deepcopy(dict(action_spec)),
        "action_spec_digest": _digest(action_spec),
        "actor_identity": copy.deepcopy(dict(actor_identity)),
        "environment_identity": copy.deepcopy(dict(environment_identity)),
        "occurred_at": occurred_at,
        "time_attestation": copy.deepcopy(dict(time_attestation)),
        "execution_status": execution_status,
        "input_artifacts": _sort_artifacts(input_artifacts),
        "output_artifacts": _sort_artifacts(output_artifacts),
        "procedure_stages": sorted(
            (copy.deepcopy(dict(item)) for item in procedure_stages),
            key=lambda item: (item["observed_at"], item["stage_id"]),
        ),
        "stop_conditions": sorted(
            (copy.deepcopy(dict(item)) for item in stop_conditions),
            key=lambda item: item["condition_id"],
        ),
    }
    event_id = f"action-event.sha256.{_sha256(material)}"
    event: dict[str, Any] = {
        "schema_version": EVENT_VERSION,
        "event_id": event_id,
        **{key: value for key, value in material.items() if key != "schema_version"},
    }
    event["event_digest"] = _digest(event)
    validate_action_event(event)
    return event


def _validate_time_attestation(value: Mapping[str, Any], location: str) -> None:
    if value["time_trust"] == "trusted":
        if value["clock_identity"] is None:
            raise ActionEvidenceError(
                f"trusted time requires a bound clock identity at {location}"
            )
        if value["trust_root_ref"] is None:
            raise ActionEvidenceError(
                f"trusted time requires a bound trust root at {location}"
            )


def validate_action_event(event: Mapping[str, Any]) -> None:
    _validate_schema(event, _subschema_validator("action_event"), "action event")
    _parse_time(str(event["occurred_at"]), "event.occurred_at")
    _validate_time_attestation(event["time_attestation"], "event.time_attestation")
    for field in ("input_artifacts", "output_artifacts"):
        values = list(event[field])
        _require_unique(values, "artifact_id", f"event.{field}")
    stages = list(event["procedure_stages"])
    _require_unique(stages, "stage_id", "event.procedure_stages")
    for stage in stages:
        _parse_time(
            str(stage["observed_at"]),
            f"event.procedure_stages[{stage['stage_id']}].observed_at",
        )
    conditions = list(event["stop_conditions"])
    _require_unique(conditions, "condition_id", "event.stop_conditions")
    expected_spec_digest = _digest(event["action_spec"])
    if event["action_spec_digest"] != expected_spec_digest:
        raise ActionEvidenceError("event action-spec digest mismatch")
    material = _without(event, "event_id", "event_digest")
    expected_id = f"action-event.sha256.{_sha256(material)}"
    if event["event_id"] != expected_id:
        raise ActionEvidenceError("action event deterministic identity mismatch")
    if event["event_digest"] != _digest(_without(event, "event_digest")):
        raise ActionEvidenceError("action event digest mismatch")


def build_action_observation(
    *,
    event: Mapping[str, Any],
    evidence_kind: str,
    observer_identity: Mapping[str, Any],
    relationship_to_actor: str,
    trust_class: str,
    observed_at: str,
    time_attestation: Mapping[str, Any],
    observed_action_spec_digest: Mapping[str, Any] | None = None,
    observed_actor_identity: Mapping[str, Any] | None = None,
    observed_environment_identity: Mapping[str, Any] | None = None,
    observed_input_artifacts: Sequence[Mapping[str, Any]] | None = None,
    observed_output_artifacts: Sequence[Mapping[str, Any]] | None = None,
    observed_stage_ids: Sequence[str] = (),
    observed_stop_condition_ids: Sequence[str] = (),
    evidence_record_ref: Mapping[str, Any],
    limitations: Sequence[str] = (),
) -> dict[str, Any]:
    validate_action_event(event)
    material = {
        "schema_version": OBSERVATION_VERSION,
        "evidence_kind": evidence_kind,
        "event_ref": _event_ref(event),
        "observer_identity": copy.deepcopy(dict(observer_identity)),
        "relationship_to_actor": relationship_to_actor,
        "trust_class": trust_class,
        "observed_action_spec_digest": copy.deepcopy(
            dict(observed_action_spec_digest or event["action_spec_digest"])
        ),
        "observed_actor_identity": copy.deepcopy(
            dict(observed_actor_identity or event["actor_identity"])
        ),
        "observed_environment_identity": copy.deepcopy(
            dict(observed_environment_identity or event["environment_identity"])
        ),
        "observed_at": observed_at,
        "time_attestation": copy.deepcopy(dict(time_attestation)),
        "observed_input_artifacts": _sort_artifacts(
            event["input_artifacts"]
            if observed_input_artifacts is None
            else observed_input_artifacts
        ),
        "observed_output_artifacts": _sort_artifacts(
            event["output_artifacts"]
            if observed_output_artifacts is None
            else observed_output_artifacts
        ),
        "observed_stage_ids": sorted(set(observed_stage_ids)),
        "observed_stop_condition_ids": sorted(
            set(observed_stop_condition_ids)
        ),
        "evidence_record_ref": copy.deepcopy(dict(evidence_record_ref)),
        "limitations": sorted(set(limitations)),
    }
    observation_id = f"action-observation.sha256.{_sha256(material)}"
    observation: dict[str, Any] = {
        "schema_version": OBSERVATION_VERSION,
        "observation_id": observation_id,
        **{key: value for key, value in material.items() if key != "schema_version"},
    }
    observation["observation_digest"] = _digest(observation)
    validate_action_observation(observation)
    return observation


def validate_action_observation(observation: Mapping[str, Any]) -> None:
    _validate_schema(
        observation,
        _subschema_validator("action_observation"),
        "action observation",
    )
    _parse_time(str(observation["observed_at"]), "observation.observed_at")
    _validate_time_attestation(
        observation["time_attestation"], "observation.time_attestation"
    )
    if observation["relationship_to_actor"] == "self" and observation[
        "trust_class"
    ] != "self_reported":
        raise ActionEvidenceError(
            "self observation cannot exceed self_reported trust"
        )
    if observation["evidence_kind"] == "self_report" and observation[
        "relationship_to_actor"
    ] != "self":
        raise ActionEvidenceError("self_report must identify a self relationship")
    for field in ("observed_input_artifacts", "observed_output_artifacts"):
        _require_unique(list(observation[field]), "artifact_id", field)
    material = _without(observation, "observation_id", "observation_digest")
    expected_id = f"action-observation.sha256.{_sha256(material)}"
    if observation["observation_id"] != expected_id:
        raise ActionEvidenceError("action observation deterministic identity mismatch")
    expected_digest = _digest(_without(observation, "observation_digest"))
    if observation["observation_digest"] != expected_digest:
        raise ActionEvidenceError("action observation digest mismatch")


def build_signature_attestation(
    *,
    algorithm: str,
    signer_identity: Mapping[str, Any],
    signed_content_digest: Mapping[str, Any],
    signature_value_digest: Mapping[str, Any],
    trust_root_ref: Mapping[str, Any] | None,
    verification_status: str,
    verifier_identity: Mapping[str, Any],
    verified_at: str,
    time_attestation: Mapping[str, Any],
    verification_record_ref: Mapping[str, Any],
) -> dict[str, Any]:
    material = {
        "algorithm": algorithm,
        "signer_identity": copy.deepcopy(dict(signer_identity)),
        "signed_content_digest": copy.deepcopy(dict(signed_content_digest)),
        "signature_value_digest": copy.deepcopy(dict(signature_value_digest)),
        "trust_root_ref": (
            copy.deepcopy(dict(trust_root_ref)) if trust_root_ref is not None else None
        ),
        "verification_status": verification_status,
        "verifier_identity": copy.deepcopy(dict(verifier_identity)),
        "verified_at": verified_at,
        "time_attestation": copy.deepcopy(dict(time_attestation)),
        "verification_record_ref": copy.deepcopy(dict(verification_record_ref)),
    }
    attestation: dict[str, Any] = {
        "signature_id": f"signature-attestation.sha256.{_sha256(material)}",
        **material,
    }
    attestation["attestation_digest"] = _digest(attestation)
    validate_signature_attestation(attestation)
    return attestation


def validate_signature_attestation(attestation: Mapping[str, Any]) -> None:
    _validate_schema(
        attestation,
        _subschema_validator("signature_attestation"),
        "signature attestation",
    )
    _parse_time(str(attestation["verified_at"]), "signature.verified_at")
    _validate_time_attestation(
        attestation["time_attestation"], "signature.time_attestation"
    )
    material = _without(attestation, "signature_id", "attestation_digest")
    expected_id = f"signature-attestation.sha256.{_sha256(material)}"
    if attestation["signature_id"] != expected_id:
        raise ActionEvidenceError("signature attestation identity mismatch")
    expected_digest = _digest(_without(attestation, "attestation_digest"))
    if attestation["attestation_digest"] != expected_digest:
        raise ActionEvidenceError("signature attestation digest mismatch")


def build_authority_grant(
    *,
    grantor_identity: Mapping[str, Any],
    grantee_identity: Mapping[str, Any],
    action_types: Sequence[str],
    target_ids: Sequence[str],
    environment_ids: Sequence[str],
    issued_at: str,
    expires_at: str,
    time_attestation: Mapping[str, Any],
    status: str,
    grant_record_ref: Mapping[str, Any],
    grant_signature: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    core = {
        "schema_version": GRANT_VERSION,
        "grantor_identity": copy.deepcopy(dict(grantor_identity)),
        "grantee_identity": copy.deepcopy(dict(grantee_identity)),
        "action_types": sorted(set(action_types)),
        "target_ids": sorted(set(target_ids)),
        "environment_ids": sorted(set(environment_ids)),
        "issued_at": issued_at,
        "expires_at": expires_at,
        "time_attestation": copy.deepcopy(dict(time_attestation)),
        "status": status,
        "grant_record_ref": copy.deepcopy(dict(grant_record_ref)),
    }
    material_digest = _digest(core)
    grant: dict[str, Any] = {
        "schema_version": GRANT_VERSION,
        "grant_id": f"authority-grant.sha256.{_sha256(core)}",
        **{key: value for key, value in core.items() if key != "schema_version"},
        "grant_material_digest": material_digest,
        "grant_signature": (
            copy.deepcopy(dict(grant_signature))
            if grant_signature is not None
            else None
        ),
    }
    grant["grant_digest"] = _digest(grant)
    validate_authority_grant(grant)
    return grant


def validate_authority_grant(grant: Mapping[str, Any]) -> None:
    _validate_schema(
        grant,
        _subschema_validator("authority_grant"),
        "authority grant",
    )
    issued = _parse_time(str(grant["issued_at"]), "grant.issued_at")
    expires = _parse_time(str(grant["expires_at"]), "grant.expires_at")
    _validate_time_attestation(grant["time_attestation"], "grant.time_attestation")
    if expires <= issued:
        raise ActionEvidenceError("authority grant expires_at must follow issued_at")
    core = {
        key: copy.deepcopy(value)
        for key, value in grant.items()
        if key
        not in {
            "grant_id",
            "grant_material_digest",
            "grant_signature",
            "grant_digest",
        }
    }
    expected_material_digest = _digest(core)
    if grant["grant_material_digest"] != expected_material_digest:
        raise ActionEvidenceError("authority grant material digest mismatch")
    expected_id = f"authority-grant.sha256.{_sha256(core)}"
    if grant["grant_id"] != expected_id:
        raise ActionEvidenceError("authority grant deterministic identity mismatch")
    signature = grant["grant_signature"]
    if signature is not None:
        validate_signature_attestation(signature)
        if signature["signed_content_digest"] != grant["grant_material_digest"]:
            raise ActionEvidenceError("grant signature binds another grant material")
        if _identity_key(signature["signer_identity"]) != _identity_key(
            grant["grantor_identity"]
        ):
            raise ActionEvidenceError("grant signature signer is not the grantor")
    if grant["grant_digest"] != _digest(_without(grant, "grant_digest")):
        raise ActionEvidenceError("authority grant digest mismatch")


def build_causal_observation(
    *,
    event: Mapping[str, Any],
    effect_artifact_ref: Mapping[str, Any],
    observer_observation_id: str,
    method: str,
    outcome: str,
    observed_at: str,
    time_attestation: Mapping[str, Any],
    evidence_digest: Mapping[str, Any],
) -> dict[str, Any]:
    validate_action_event(event)
    material = {
        "event_ref": _event_ref(event),
        "effect_artifact_ref": copy.deepcopy(dict(effect_artifact_ref)),
        "observer_observation_id": observer_observation_id,
        "method": method,
        "outcome": outcome,
        "observed_at": observed_at,
        "time_attestation": copy.deepcopy(dict(time_attestation)),
        "evidence_digest": copy.deepcopy(dict(evidence_digest)),
    }
    observation: dict[str, Any] = {
        "causal_id": f"causal-observation.sha256.{_sha256(material)}",
        **material,
    }
    observation["observation_digest"] = _digest(observation)
    validate_causal_observation(observation)
    return observation


def validate_causal_observation(observation: Mapping[str, Any]) -> None:
    _validate_schema(
        observation,
        _subschema_validator("causal_observation"),
        "causal observation",
    )
    _parse_time(str(observation["observed_at"]), "causal.observed_at")
    _validate_time_attestation(
        observation["time_attestation"], "causal.time_attestation"
    )
    material = _without(observation, "causal_id", "observation_digest")
    expected_id = f"causal-observation.sha256.{_sha256(material)}"
    if observation["causal_id"] != expected_id:
        raise ActionEvidenceError("causal observation identity mismatch")
    if observation["observation_digest"] != _digest(
        _without(observation, "observation_digest")
    ):
        raise ActionEvidenceError("causal observation digest mismatch")


def _claim(
    claim_class: str,
    state: str,
    *,
    basis: Iterable[str] = (),
    counter: Iterable[str] = (),
    reasons: Iterable[str],
    limitations: Iterable[str],
) -> dict[str, Any]:
    return {
        "claim_class": claim_class,
        "state": state,
        "basis_refs": sorted(set(basis)),
        "counterevidence_refs": sorted(set(counter)),
        "reasons": sorted(set(reasons)),
        "limitations": sorted(set(limitations)),
    }


def _profile_active(profile: Mapping[str, Any], evaluated_at: str) -> tuple[bool, str]:
    if profile["adoption_state"] != "adopted":
        return False, "profile_not_adopted"
    decision_at = _parse_time(
        str(profile["human_decision_ref"]["decided_at"]),
        "profile.human_decision_ref.decided_at",
    )
    if _parse_time(evaluated_at, "evaluated_at") < decision_at:
        return False, "profile_not_adopted_at_evaluation"
    return True, "profile_adopted"


def _trusted_time_attestation_eligible(
    value: Mapping[str, Any], profile: Mapping[str, Any]
) -> bool:
    return bool(
        value["time_trust"] == "trusted"
        and value["clock_identity"] is not None
        and _identity_allowed(
            value["clock_identity"],
            profile["time_policy"]["allowed_clock_identities"],
        )
        and _trust_root_allowed(
            value["trust_root_ref"],
            profile["time_policy"]["allowed_trust_roots"],
        )
    )


def _time_eligible(
    claim_class: str,
    event: Mapping[str, Any],
    observation: Mapping[str, Any],
    profile: Mapping[str, Any],
    evaluated_at: str,
) -> bool:
    required = claim_class in profile["time_policy"]["trusted_time_required_for"]
    if required and (
        not _trusted_time_attestation_eligible(event["time_attestation"], profile)
        or not _trusted_time_attestation_eligible(
            observation["time_attestation"], profile
        )
    ):
        return False
    event_at = _parse_time(str(event["occurred_at"]), "event.occurred_at")
    observation_at = _parse_time(
        str(observation["observed_at"]), "observation.observed_at"
    )
    evaluation_at = _parse_time(evaluated_at, "evaluated_at")
    if observation_at < event_at or evaluation_at < observation_at:
        return False
    return evaluation_at < event_at + timedelta(
        seconds=int(profile["time_policy"]["max_event_age_seconds"])
    )


def _event_time_eligible(
    claim_class: str,
    event: Mapping[str, Any],
    profile: Mapping[str, Any],
    evaluated_at: str,
) -> bool:
    if (
        claim_class in profile["time_policy"]["trusted_time_required_for"]
        and not _trusted_time_attestation_eligible(
            event["time_attestation"], profile
        )
    ):
        return False
    event_at = _parse_time(str(event["occurred_at"]), "event.occurred_at")
    evaluation_at = _parse_time(evaluated_at, "evaluated_at")
    return event_at <= evaluation_at < event_at + timedelta(
        seconds=int(profile["time_policy"]["max_event_age_seconds"])
    )


def _observation_eligible(
    observation: Mapping[str, Any],
    claim_class: str,
    event: Mapping[str, Any],
    profile: Mapping[str, Any],
    evaluated_at: str,
) -> bool:
    if observation["evidence_kind"] in NON_OCCURRENCE_EVIDENCE_KINDS:
        return False
    if observation["evidence_kind"] not in profile[
        "occurrence_capable_evidence_kinds"
    ]:
        return False
    if observation["trust_class"] not in profile["observer_policy"][
        "accepted_trust_classes"
    ]:
        return False
    if not _identity_allowed(
        observation["observer_identity"],
        profile["observer_policy"]["allowed_observers"],
    ):
        return False
    if (
        claim_class in profile["observer_policy"]["independence_required_for"]
        and observation["relationship_to_actor"] != "independent"
    ):
        return False
    if observation["event_ref"] != _event_ref(event):
        return False
    if observation["observed_action_spec_digest"] != event["action_spec_digest"]:
        return False
    if _identity_key(observation["observed_environment_identity"]) != _identity_key(
        event["environment_identity"]
    ):
        return False
    return _time_eligible(claim_class, event, observation, profile, evaluated_at)


def _signature_context_eligible(
    signature: Mapping[str, Any], profile: Mapping[str, Any]
) -> bool:
    policy = profile["authenticity_policy"]
    return bool(
        signature["algorithm"] in policy["allowed_signature_algorithms"]
        and _identity_allowed(
            signature["verifier_identity"], policy["allowed_verifiers"]
        )
        and _trust_root_allowed(
            signature["trust_root_ref"],
            profile["time_policy"]["allowed_trust_roots"],
        )
        and _trusted_time_attestation_eligible(
            signature["time_attestation"], profile
        )
    )


def _signature_assurance_eligible(
    signature: Mapping[str, Any], profile: Mapping[str, Any]
) -> bool:
    return bool(
        signature["verification_status"] == "verified"
        and _signature_context_eligible(signature, profile)
    )


def _event_signature_result(
    event: Mapping[str, Any],
    signatures: Sequence[Mapping[str, Any]],
    profile: Mapping[str, Any],
    evaluated_at: str,
) -> tuple[str, list[str], list[str], list[str]]:
    policy = profile["authenticity_policy"]
    exact = [
        signature
        for signature in signatures
        if signature["signed_content_digest"] == event["event_digest"]
        and _identity_allowed(
            signature["signer_identity"], policy["allowed_signers"]
        )
    ]
    disallowed_signers = [
        signature["signature_id"]
        for signature in signatures
        if signature["signed_content_digest"] == event["event_digest"]
        and not _identity_allowed(
            signature["signer_identity"], policy["allowed_signers"]
        )
    ]
    mismatched = [
        signature["signature_id"]
        for signature in signatures
        if signature["signed_content_digest"] != event["event_digest"]
        and _identity_allowed(
            signature["signer_identity"], policy["allowed_signers"]
        )
        and _signature_assurance_eligible(signature, profile)
        and _parse_time(str(signature["verified_at"]), "signature.verified_at")
        <= _parse_time(evaluated_at, "evaluated_at")
    ]
    if not exact:
        if mismatched:
            return (
                "refuted",
                [],
                mismatched,
                ["signature_binds_other_content"],
            )
        if disallowed_signers:
            return (
                "unproved",
                disallowed_signers,
                [],
                ["event_signature_signer_not_allowed_by_profile"],
            )
        return "unproved", [], [], ["external_signature_missing"]
    for signature in exact:
        verified_at = _parse_time(
            str(signature["verified_at"]), "signature.verified_at"
        )
        if not (
            _parse_time(str(event["occurred_at"]), "event.occurred_at")
            <= verified_at
            <= _parse_time(evaluated_at, "evaluated_at")
        ):
            continue
        if not _signature_assurance_eligible(signature, profile):
            continue
        return "proved", [signature["signature_id"]], [], [
            "event_digest_has_profile_conformant_signature_attestation"
        ]
    failed = [
        signature["signature_id"]
        for signature in exact
        if signature["verification_status"] == "failed"
        and _signature_context_eligible(signature, profile)
        and _parse_time(str(event["occurred_at"]), "event.occurred_at")
        <= _parse_time(str(signature["verified_at"]), "signature.verified_at")
        <= _parse_time(evaluated_at, "evaluated_at")
    ]
    if failed:
        return "refuted", [], failed, ["event_signature_verification_failed"]
    return "unproved", [item["signature_id"] for item in exact], [], [
        "signature_attestation_does_not_meet_profile"
    ]


def _derive_claims(
    *,
    profile: Mapping[str, Any],
    expected_action_spec: Mapping[str, Any],
    event: Mapping[str, Any],
    observations: Sequence[Mapping[str, Any]],
    authority_grants: Sequence[Mapping[str, Any]],
    signatures: Sequence[Mapping[str, Any]],
    causal_observations: Sequence[Mapping[str, Any]],
    evaluated_at: str,
) -> list[dict[str, Any]]:
    spec_matches = (
        event["action_spec"] == expected_action_spec
        and event["action_spec_digest"] == _digest(expected_action_spec)
    )
    active, inactive_reason = _profile_active(profile, evaluated_at)

    eligible_by_claim = {
        claim_class: [
            observation
            for observation in observations
            if _observation_eligible(
                observation, claim_class, event, profile, evaluated_at
            )
        ]
        for claim_class in CLAIM_CLASSES
    }
    event_ref_mismatches = [
        observation["observation_id"]
        for observation in observations
        if observation["event_ref"] != _event_ref(event)
        and observation["evidence_kind"]
        in profile["occurrence_capable_evidence_kinds"]
        and observation["trust_class"]
        in profile["observer_policy"]["accepted_trust_classes"]
        and _identity_allowed(
            observation["observer_identity"],
            profile["observer_policy"]["allowed_observers"],
        )
        and (
            "occurrence"
            not in profile["observer_policy"]["independence_required_for"]
            or observation["relationship_to_actor"] == "independent"
        )
        and _time_eligible(
            "occurrence", event, observation, profile, evaluated_at
        )
    ]
    semantic_observation_mismatches = [
        observation["observation_id"]
        for observation in observations
        if observation["event_ref"] == _event_ref(event)
        and observation["evidence_kind"]
        in profile["occurrence_capable_evidence_kinds"]
        and observation["trust_class"]
        in profile["observer_policy"]["accepted_trust_classes"]
        and _identity_allowed(
            observation["observer_identity"],
            profile["observer_policy"]["allowed_observers"],
        )
        and (
            "occurrence"
            not in profile["observer_policy"]["independence_required_for"]
            or observation["relationship_to_actor"] == "independent"
        )
        and _time_eligible(
            "occurrence", event, observation, profile, evaluated_at
        )
        and (
            observation["observed_action_spec_digest"]
            != event["action_spec_digest"]
            or _identity_key(observation["observed_environment_identity"])
            != _identity_key(event["environment_identity"])
        )
    ]

    if not spec_matches:
        occurrence = _claim(
            "occurrence",
            "refuted",
            counter=[event["event_id"]],
            reasons=["expected_action_semantic_substitution"],
            limitations=["A signed event for another action does not prove this action."],
        )
    elif event_ref_mismatches:
        occurrence = _claim(
            "occurrence",
            "refuted",
            counter=event_ref_mismatches,
            reasons=["observation_event_substitution"],
            limitations=["Conflicting event identity prevents occurrence proof."],
        )
    elif semantic_observation_mismatches:
        occurrence = _claim(
            "occurrence",
            "refuted",
            counter=semantic_observation_mismatches,
            reasons=["observation_action_or_environment_binding_mismatch"],
            limitations=[
                "An observation bound to another action or environment cannot prove this event."
            ],
        )
    elif eligible_by_claim["occurrence"]:
        occurrence = _claim(
            "occurrence",
            "proved",
            basis=[item["observation_id"] for item in eligible_by_claim["occurrence"]],
            reasons=["occurrence_capable_observation_matches_event"],
            limitations=["Occurrence proof is bounded to the supplied observer records."],
        )
    else:
        non_occurrence = [
            item["observation_id"]
            for item in observations
            if item["evidence_kind"] in NON_OCCURRENCE_EVIDENCE_KINDS
        ]
        occurrence = _claim(
            "occurrence",
            "unproved",
            basis=non_occurrence,
            reasons=[
                "non_occurrence_evidence_only"
                if non_occurrence
                else "qualifying_occurrence_observation_missing"
            ],
            limitations=[
                "Prose, tool requests, and self-reports are not occurrence evidence."
            ],
        )

    identity_observations = eligible_by_claim["identity"]
    conflicting_identity = [
        item["observation_id"]
        for item in identity_observations
        if _identity_key(item["observed_actor_identity"])
        != _identity_key(event["actor_identity"])
    ]
    matching_identity = [
        item
        for item in identity_observations
        if _identity_key(item["observed_actor_identity"])
        == _identity_key(event["actor_identity"])
    ]
    if not spec_matches:
        identity = _claim(
            "identity",
            "unproved",
            reasons=["expected_action_mismatch_prevents_actor_binding"],
            limitations=["Actor identity remains independent from event authenticity."],
        )
    elif conflicting_identity:
        identity = _claim(
            "identity",
            "refuted",
            counter=conflicting_identity,
            reasons=["observed_actor_identity_mismatch"],
            limitations=["Conflicting actor observations require external resolution."],
        )
    elif matching_identity:
        identity = _claim(
            "identity",
            "proved",
            basis=[item["observation_id"] for item in matching_identity],
            reasons=["observer_bound_actor_identity_matches_event"],
            limitations=["Identity proof is bounded to supplied identity digests."],
        )
    else:
        identity = _claim(
            "identity",
            "unproved",
            reasons=["qualifying_actor_identity_observation_missing"],
            limitations=["Event self-attribution does not prove actor identity."],
        )

    exact_grants: list[Mapping[str, Any]] = []
    mismatched_grants: list[str] = []
    expired_grants: list[str] = []
    time_ineligible_grants: list[str] = []
    insufficient_grants: list[str] = []
    failed_signature_grants: list[str] = []
    event_at = _parse_time(str(event["occurred_at"]), "event.occurred_at")
    evaluation_at = _parse_time(evaluated_at, "evaluated_at")
    for grant in authority_grants:
        exact_scope = (
            _identity_key(grant["grantee_identity"])
            == _identity_key(event["actor_identity"])
            and _identity_allowed(
                grant["grantor_identity"],
                profile["authority_policy"]["allowed_grantors"],
            )
            and event["action_spec"]["action_type"] in grant["action_types"]
            and event["action_spec"]["target_ref"]["entity_id"]
            in grant["target_ids"]
            and event["environment_identity"]["entity_id"]
            in grant["environment_ids"]
        )
        valid_time = (
            _parse_time(str(grant["issued_at"]), "grant.issued_at")
            <= event_at
            < _parse_time(str(grant["expires_at"]), "grant.expires_at")
        )
        grant_time_ok = _event_time_eligible(
            "authority", event, profile, evaluated_at
        ) and (
            "authority" not in profile["time_policy"]["trusted_time_required_for"]
            or _trusted_time_attestation_eligible(
                grant["time_attestation"], profile
            )
        )
        if not exact_scope or grant["status"] != "active":
            mismatched_grants.append(grant["grant_id"])
            continue
        if not valid_time:
            expired_grants.append(grant["grant_id"])
            continue
        if not grant_time_ok:
            time_ineligible_grants.append(grant["grant_id"])
            continue
        if profile["authority_policy"]["signed_grant_required"]:
            signature = grant["grant_signature"]
            if signature is None:
                insufficient_grants.append(grant["grant_id"])
                continue
            if (
                signature["verification_status"] == "failed"
                and _signature_context_eligible(signature, profile)
            ):
                failed_signature_grants.append(grant["grant_id"])
                continue
            verified_at = _parse_time(
                str(signature["verified_at"]), "grant.signature.verified_at"
            )
            issued_at = _parse_time(str(grant["issued_at"]), "grant.issued_at")
            if not (
                issued_at <= verified_at <= evaluation_at
                and _signature_assurance_eligible(signature, profile)
            ):
                insufficient_grants.append(grant["grant_id"])
                continue
        exact_grants.append(grant)
    if exact_grants:
        authority = _claim(
            "authority",
            "proved",
            basis=[item["grant_id"] for item in exact_grants],
            reasons=["explicit_scope_and_time_bound_authority_grant"],
            limitations=[
                "Action success was not used to infer authority; the result depends on the external grant record."
            ],
        )
    elif mismatched_grants or failed_signature_grants:
        authority = _claim(
            "authority",
            "refuted",
            counter=[*mismatched_grants, *failed_signature_grants],
            reasons=[
                *(
                    ["authority_grant_scope_identity_or_status_mismatch"]
                    if mismatched_grants
                    else []
                ),
                *(
                    ["authority_grant_signature_verification_failed"]
                    if failed_signature_grants
                    else []
                ),
            ],
            limitations=["A grant for another actor or scope is counterevidence, not authority."],
        )
    else:
        authority = _claim(
            "authority",
            "unproved",
            basis=[
                *expired_grants,
                *time_ineligible_grants,
                *insufficient_grants,
            ],
            reasons=[
                *(
                    ["authority_grant_time_not_profile_eligible"]
                    if time_ineligible_grants
                    else []
                ),
                *(
                    ["authority_grant_expired"]
                    if expired_grants
                    else []
                ),
                *(
                    ["authority_grant_assurance_incomplete"]
                    if insufficient_grants
                    else []
                ),
                *(
                    ["explicit_authority_grant_missing"]
                    if not expired_grants
                    and not time_ineligible_grants
                    and not insufficient_grants
                    else []
                ),
            ],
            limitations=["Successful execution cannot create or retroactively grant authority."],
        )

    stages_by_id = {item["stage_id"]: item for item in event["procedure_stages"]}
    required_stages = profile["procedure_policy"]["required_stages"]
    required_stage_ids = [item["stage_id"] for item in required_stages]
    failed_stages = [
        stage_id
        for stage_id in required_stage_ids
        if stage_id in stages_by_id
        and stages_by_id[stage_id]["status"] in {"failed", "skipped"}
    ]
    missing_stages = [
        stage_id
        for stage_id in required_stage_ids
        if stage_id not in stages_by_id
        or stages_by_id[stage_id]["status"] == "not_observed"
    ]
    completed_times = [
        _parse_time(
            str(stages_by_id[item["stage_id"]]["observed_at"]),
            f"stage.{item['stage_id']}.observed_at",
        )
        for item in required_stages
        if item["stage_id"] in stages_by_id
    ]
    order_violation = completed_times != sorted(completed_times)
    stage_time_violations = [
        item["stage_id"]
        for item in required_stages
        if item["stage_id"] in stages_by_id
        and not (
            event_at
            <= _parse_time(
                str(stages_by_id[item["stage_id"]]["observed_at"]),
                f"stage.{item['stage_id']}.observed_at",
            )
            <= evaluation_at
        )
    ]
    stops_by_id = {item["condition_id"]: item for item in event["stop_conditions"]}
    required_stop_ids = [
        item["condition_id"]
        for item in profile["procedure_policy"]["stop_conditions"]
    ]
    stop_violations = [
        condition_id
        for condition_id in required_stop_ids
        if condition_id in stops_by_id
        and stops_by_id[condition_id]["triggered"]
        and stops_by_id[condition_id]["response"] != "stopped"
    ]
    missing_stops = [
        condition_id
        for condition_id in required_stop_ids
        if condition_id not in stops_by_id
        or stops_by_id[condition_id]["response"] == "not_observed"
    ]
    procedure_observers = eligible_by_claim["procedure"]
    observer_stage_time_violations = [
        observer["observation_id"]
        for observer in procedure_observers
        if any(
            stage_id in stages_by_id
            and _parse_time(
                str(stages_by_id[stage_id]["observed_at"]),
                f"stage.{stage_id}.observed_at",
            )
            > _parse_time(
                str(observer["observed_at"]), "procedure_observer.observed_at"
            )
            for stage_id in observer["observed_stage_ids"]
        )
    ]
    observed_stage_ids = {
        stage_id for item in procedure_observers for stage_id in item["observed_stage_ids"]
    }
    observed_stop_ids = {
        condition_id
        for item in procedure_observers
        for condition_id in item["observed_stop_condition_ids"]
    }
    missing_observer_stage = sorted(set(required_stage_ids) - observed_stage_ids)
    missing_observer_stop = sorted(set(required_stop_ids) - observed_stop_ids)
    if (
        failed_stages
        or stop_violations
        or order_violation
        or stage_time_violations
        or observer_stage_time_violations
    ):
        procedure = _claim(
            "procedure",
            "refuted",
            counter=[
                *failed_stages,
                *stop_violations,
                *stage_time_violations,
                *observer_stage_time_violations,
            ],
            reasons=[
                *(["required_stage_failed_or_skipped"] if failed_stages else []),
                *(["stop_condition_violated"] if stop_violations else []),
                *(["procedure_stage_order_violated"] if order_violation else []),
                *(
                    ["procedure_stage_time_outside_event_evaluation_window"]
                    if stage_time_violations
                    else []
                ),
                *(
                    ["procedure_observer_predates_observed_stage"]
                    if observer_stage_time_violations
                    else []
                ),
            ],
            limitations=["Procedure proof is independent from occurrence and authority."],
        )
    elif missing_stages or missing_stops or missing_observer_stage or missing_observer_stop:
        procedure = _claim(
            "procedure",
            "unproved",
            basis=[item["observation_id"] for item in procedure_observers],
            reasons=["required_procedure_or_stop_observation_missing"],
            limitations=["Unobserved stages cannot be inferred from a success status."],
        )
    else:
        procedure = _claim(
            "procedure",
            "proved",
            basis=[item["observation_id"] for item in procedure_observers],
            reasons=["required_stages_and_stop_conditions_observed"],
            limitations=["Only the profile-declared procedure denominator was checked."],
        )

    required_input_roles = set(
        profile["artifact_policy"]["required_input_roles"]
    )
    required_output_roles = set(
        profile["artifact_policy"]["required_output_roles"]
    )
    event_inputs = {
        (item["artifact_id"], item["role"]): item
        for item in event["input_artifacts"]
    }
    event_outputs = {
        (item["artifact_id"], item["role"]): item for item in event["output_artifacts"]
    }
    missing_input_roles = required_input_roles - {
        item["role"] for item in event["input_artifacts"]
    }
    missing_output_roles = required_output_roles - {
        item["role"] for item in event["output_artifacts"]
    }
    artifact_observers = eligible_by_claim["artifact_provenance"]
    artifact_mismatch: list[str] = []
    artifact_exact_basis: list[str] = []
    for observation in artifact_observers:
        observed_inputs = {
            (item["artifact_id"], item["role"]): item
            for item in observation["observed_input_artifacts"]
        }
        observed_outputs = {
            (item["artifact_id"], item["role"]): item
            for item in observation["observed_output_artifacts"]
        }
        input_mismatches = [
            artifact_id
            for (artifact_id, role), item in event_inputs.items()
            if role in required_input_roles
            and (
                (artifact_id, role) not in observed_inputs
                or observed_inputs[(artifact_id, role)]["content_digest"]
                != item["content_digest"]
            )
        ]
        output_mismatches = [
            artifact_id
            for (artifact_id, role), item in event_outputs.items()
            if role in required_output_roles
            and (
                (artifact_id, role) not in observed_outputs
                or observed_outputs[(artifact_id, role)]["content_digest"]
                != item["content_digest"]
            )
        ]
        mismatches = [*input_mismatches, *output_mismatches]
        if mismatches:
            artifact_mismatch.extend(mismatches)
        elif not missing_input_roles and not missing_output_roles:
            artifact_exact_basis.append(observation["observation_id"])
    if artifact_mismatch:
        artifact_provenance = _claim(
            "artifact_provenance",
            "refuted",
            counter=artifact_mismatch,
            reasons=["observed_artifact_digest_mismatch"],
            limitations=["A digest mismatch identifies inconsistency, not its cause."],
        )
    elif missing_input_roles or missing_output_roles or not artifact_exact_basis:
        artifact_provenance = _claim(
            "artifact_provenance",
            "unproved",
            reasons=[
                *(
                    ["required_input_role_missing"]
                    if missing_input_roles
                    else []
                ),
                *(
                    ["required_output_role_missing"]
                    if missing_output_roles
                    else []
                ),
                *(
                    ["independent_artifact_digest_observation_missing"]
                    if not missing_input_roles
                    and not missing_output_roles
                    and not artifact_exact_basis
                    else []
                ),
            ],
            limitations=["Event-declared output digests are not self-authenticating."],
        )
    else:
        artifact_provenance = _claim(
            "artifact_provenance",
            "proved",
            basis=artifact_exact_basis,
            reasons=["observer_input_and_output_digests_match_event_artifacts"],
            limitations=["Content digests do not establish authorship or semantic correctness."],
        )

    authenticity_state, authenticity_basis, authenticity_counter, authenticity_reasons = (
        _event_signature_result(event, signatures, profile, evaluated_at)
    )
    clock_required = profile["authenticity_policy"]["external_clock_required"]
    if clock_required and not _trusted_time_attestation_eligible(
        event["time_attestation"], profile
    ):
        authenticity_state = "unproved"
        authenticity_reasons.append("external_clock_or_clock_trust_root_missing")
    if not _event_time_eligible("authenticity", event, profile, evaluated_at):
        authenticity_state = "unproved"
        authenticity_reasons.append("event_time_not_profile_eligible")
    if not spec_matches:
        authenticity_state = "refuted"
        authenticity_counter.append(event["event_id"])
        authenticity_reasons.append("signature_does_not_cure_semantic_substitution")
    authenticity = _claim(
        "authenticity",
        authenticity_state,
        basis=authenticity_basis,
        counter=authenticity_counter,
        reasons=authenticity_reasons,
        limitations=[_TRUST_LIMITATION],
    )

    observation_by_id = {item["observation_id"]: item for item in observations}
    output_by_key = {_artifact_key(item): item for item in event["output_artifacts"]}
    causal_basis: list[str] = []
    causal_counter: list[str] = []
    causal_binding_mismatch: list[str] = []
    for causal in causal_observations:
        observer = observation_by_id.get(causal["observer_observation_id"])
        exact_event = causal["event_ref"] == _event_ref(event)
        exact_output = _artifact_key(causal["effect_artifact_ref"]) in output_by_key
        method_ok = causal["method"] in profile["causality_policy"]["accepted_methods"]
        observer_ok = bool(
            observer is not None
            and _observation_eligible(
                observer, "causality", event, profile, evaluated_at
            )
        )
        observer_saw_effect = bool(
            observer is not None
            and _artifact_key(causal["effect_artifact_ref"])
            in {
                _artifact_key(item)
                for item in observer["observed_output_artifacts"]
            }
        )
        if profile["causality_policy"]["independent_observer_required"]:
            observer_ok = bool(
                observer_ok and observer["relationship_to_actor"] == "independent"
            )
        causal_at = _parse_time(str(causal["observed_at"]), "causal.observed_at")
        causal_time_ok = bool(
            event_at <= causal_at <= evaluation_at
            and _event_time_eligible("causality", event, profile, evaluated_at)
            and (
                "causality"
                not in profile["time_policy"]["trusted_time_required_for"]
                or _trusted_time_attestation_eligible(
                    causal["time_attestation"], profile
                )
            )
            and observer is not None
            and _parse_time(
                str(observer["observed_at"]), "causal.observer.observed_at"
            )
            <= causal_at
        )
        if (
            (not exact_event or not exact_output)
            and method_ok
            and observer_ok
            and causal_time_ok
        ):
            causal_binding_mismatch.append(causal["causal_id"])
            continue
        if method_ok and observer_ok and observer_saw_effect and causal_time_ok:
            if causal["outcome"] == "refutes":
                causal_counter.append(causal["causal_id"])
            else:
                causal_basis.append(causal["causal_id"])
    if not spec_matches:
        causality = _claim(
            "causality",
            "unproved",
            reasons=["expected_action_mismatch_prevents_causal_binding"],
            limitations=[_CAUSAL_LIMITATION],
        )
    elif causal_counter:
        causality = _claim(
            "causality",
            "refuted",
            counter=causal_counter,
            reasons=["explicit_causal_observation_refutes_link"],
            limitations=[_CAUSAL_LIMITATION],
        )
    elif causal_binding_mismatch:
        causality = _claim(
            "causality",
            "refuted",
            counter=causal_binding_mismatch,
            reasons=["causal_event_or_effect_artifact_binding_mismatch"],
            limitations=[_CAUSAL_LIMITATION],
        )
    elif causal_basis:
        causality = _claim(
            "causality",
            "proved",
            basis=causal_basis,
            reasons=["profile_conformant_explicit_causal_observation"],
            limitations=[_CAUSAL_LIMITATION],
        )
    else:
        causality = _claim(
            "causality",
            "unproved",
            reasons=["qualifying_explicit_causal_observation_missing"],
            limitations=[_CAUSAL_LIMITATION],
        )

    results = [
        occurrence,
        identity,
        authority,
        procedure,
        artifact_provenance,
        authenticity,
        causality,
    ]
    if not active:
        for result in results:
            if result["state"] == "proved":
                result["state"] = "unproved"
                result["reasons"] = sorted(
                    set(result["reasons"]) | {inactive_reason}
                )
    return results


def _summary(
    results: Sequence[Mapping[str, Any]], profile: Mapping[str, Any]
) -> dict[str, Any]:
    by_class = {str(item["claim_class"]): item for item in results}
    required = sorted(profile["required_claim_classes"])
    return {
        "required_claim_classes": required,
        "unproved_claim_classes": sorted(
            claim for claim, item in by_class.items() if item["state"] == "unproved"
        ),
        "refuted_claim_classes": sorted(
            claim for claim, item in by_class.items() if item["state"] == "refuted"
        ),
        "all_required_claims_proved": all(
            by_class[claim]["state"] == "proved" for claim in required
        ),
        "human_acceptance": "pending",
        "semantic_guard_role": "audit_only_no_dispatch_or_authority_grant",
    }


def _assessment_material(
    *,
    profile: Mapping[str, Any],
    expected_action_spec: Mapping[str, Any],
    event: Mapping[str, Any],
    observations: Sequence[Mapping[str, Any]],
    authority_grants: Sequence[Mapping[str, Any]],
    signatures: Sequence[Mapping[str, Any]],
    causal_observations: Sequence[Mapping[str, Any]],
    evaluated_at: str,
) -> dict[str, Any]:
    return {
        "profile_ref": _profile_ref(profile),
        "expected_action_spec": copy.deepcopy(dict(expected_action_spec)),
        "expected_action_spec_digest": _digest(expected_action_spec),
        "event": copy.deepcopy(dict(event)),
        "observations": sorted(
            (copy.deepcopy(dict(item)) for item in observations),
            key=lambda item: item["observation_id"],
        ),
        "authority_grants": sorted(
            (copy.deepcopy(dict(item)) for item in authority_grants),
            key=lambda item: item["grant_id"],
        ),
        "signature_attestations": sorted(
            (copy.deepcopy(dict(item)) for item in signatures),
            key=lambda item: item["signature_id"],
        ),
        "causal_observations": sorted(
            (copy.deepcopy(dict(item)) for item in causal_observations),
            key=lambda item: item["causal_id"],
        ),
        "evaluated_at": evaluated_at,
    }


def _validate_bundle_bindings(
    event: Mapping[str, Any],
    observations: Sequence[Mapping[str, Any]],
    causal_observations: Sequence[Mapping[str, Any]],
) -> None:
    event_stage_ids = {item["stage_id"] for item in event["procedure_stages"]}
    event_stop_ids = {item["condition_id"] for item in event["stop_conditions"]}
    observation_ids = {item["observation_id"] for item in observations}
    for observation in observations:
        unknown_stages = sorted(
            set(observation["observed_stage_ids"]) - event_stage_ids
        )
        if unknown_stages:
            raise ActionEvidenceError(
                "observation names stages absent from the event: "
                f"{unknown_stages!r}"
            )
        unknown_stops = sorted(
            set(observation["observed_stop_condition_ids"]) - event_stop_ids
        )
        if unknown_stops:
            raise ActionEvidenceError(
                "observation names stop conditions absent from the event: "
                f"{unknown_stops!r}"
            )
    dangling_observers = sorted(
        {
            item["observer_observation_id"]
            for item in causal_observations
            if item["observer_observation_id"] not in observation_ids
        }
    )
    if dangling_observers:
        raise ActionEvidenceError(
            "causal observations reference absent observer records: "
            f"{dangling_observers!r}"
        )


def build_action_evidence_assessment(
    *,
    profile: Mapping[str, Any],
    expected_action_spec: Mapping[str, Any],
    event: Mapping[str, Any],
    observations: Sequence[Mapping[str, Any]],
    authority_grants: Sequence[Mapping[str, Any]] = (),
    signature_attestations: Sequence[Mapping[str, Any]] = (),
    causal_observations: Sequence[Mapping[str, Any]] = (),
    evaluated_at: str,
) -> dict[str, Any]:
    validate_action_assurance_profile(profile)
    validate_action_event(event)
    for item in observations:
        validate_action_observation(item)
    for item in authority_grants:
        validate_authority_grant(item)
    for item in signature_attestations:
        validate_signature_attestation(item)
    for item in causal_observations:
        validate_causal_observation(item)
    _parse_time(evaluated_at, "evaluated_at")

    material = _assessment_material(
        profile=profile,
        expected_action_spec=expected_action_spec,
        event=event,
        observations=observations,
        authority_grants=authority_grants,
        signatures=signature_attestations,
        causal_observations=causal_observations,
        evaluated_at=evaluated_at,
    )
    _require_unique(material["observations"], "observation_id", "observations")
    _require_unique(material["authority_grants"], "grant_id", "authority_grants")
    _require_unique(
        material["signature_attestations"],
        "signature_id",
        "signature_attestations",
    )
    _require_unique(
        material["causal_observations"], "causal_id", "causal_observations"
    )
    _validate_bundle_bindings(
        event,
        material["observations"],
        material["causal_observations"],
    )
    results = _derive_claims(
        profile=profile,
        expected_action_spec=expected_action_spec,
        event=event,
        observations=material["observations"],
        authority_grants=material["authority_grants"],
        signatures=material["signature_attestations"],
        causal_observations=material["causal_observations"],
        evaluated_at=evaluated_at,
    )
    assessment_id = f"action-assessment.sha256.{_sha256(material)}"
    assessment: dict[str, Any] = {
        "schema_version": ASSESSMENT_VERSION,
        "assessment_id": assessment_id,
        **material,
        "claim_results": results,
        "summary": _summary(results, profile),
        "limitations": [_AUDIT_LIMITATION, _TRUST_LIMITATION],
    }
    assessment["assessment_digest"] = _digest(assessment)
    validate_action_evidence_assessment(assessment, profile=profile)
    return assessment


def validate_action_evidence_assessment(
    assessment: Mapping[str, Any],
    *,
    profile: Mapping[str, Any],
) -> None:
    validate_action_assurance_profile(profile)
    _validate_schema(
        assessment,
        _validator("action-evidence.schema.json"),
        "action evidence assessment",
    )
    validate_action_event(assessment["event"])
    observations = list(assessment["observations"])
    grants = list(assessment["authority_grants"])
    signatures = list(assessment["signature_attestations"])
    causal = list(assessment["causal_observations"])
    for item in observations:
        validate_action_observation(item)
    for item in grants:
        validate_authority_grant(item)
    for item in signatures:
        validate_signature_attestation(item)
    for item in causal:
        validate_causal_observation(item)
    _require_unique(observations, "observation_id", "observations")
    _require_unique(grants, "grant_id", "authority_grants")
    _require_unique(signatures, "signature_id", "signature_attestations")
    _require_unique(causal, "causal_id", "causal_observations")
    _validate_bundle_bindings(assessment["event"], observations, causal)
    if assessment["profile_ref"] != _profile_ref(profile):
        raise ActionEvidenceError("assessment profile reference mismatch")
    if assessment["expected_action_spec_digest"] != _digest(
        assessment["expected_action_spec"]
    ):
        raise ActionEvidenceError("expected action-spec digest mismatch")

    material = _assessment_material(
        profile=profile,
        expected_action_spec=assessment["expected_action_spec"],
        event=assessment["event"],
        observations=observations,
        authority_grants=grants,
        signatures=signatures,
        causal_observations=causal,
        evaluated_at=str(assessment["evaluated_at"]),
    )
    expected_id = f"action-assessment.sha256.{_sha256(material)}"
    if assessment["assessment_id"] != expected_id:
        raise ActionEvidenceError("action assessment deterministic identity mismatch")
    replayed_results = _derive_claims(
        profile=profile,
        expected_action_spec=assessment["expected_action_spec"],
        event=assessment["event"],
        observations=observations,
        authority_grants=grants,
        signatures=signatures,
        causal_observations=causal,
        evaluated_at=str(assessment["evaluated_at"]),
    )
    if assessment["claim_results"] != replayed_results:
        raise ActionEvidenceError("action claim results do not replay exactly")
    expected_summary = _summary(replayed_results, profile)
    if assessment["summary"] != expected_summary:
        raise ActionEvidenceError("action evidence summary does not replay exactly")
    claim_classes = [item["claim_class"] for item in replayed_results]
    if set(claim_classes) != set(CLAIM_CLASSES) or len(claim_classes) != len(
        CLAIM_CLASSES
    ):
        raise ActionEvidenceError("claim result denominator is not exactly closed")
    expected_digest = _digest(_without(assessment, "assessment_digest"))
    if assessment["assessment_digest"] != expected_digest:
        raise ActionEvidenceError("action assessment digest mismatch")
