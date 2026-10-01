"""Bind real candidate governance material to one audit observation.

This is an audit-side bridge, not a control-plane trust root.  It converts the
saved H1/H2 candidates through their current resolvers, validates serialized
ENV and D7 evidence when supplied, and preserves every result below formal
authority.  Missing or rejected material stays explicit rather than becoming
an implicit default.
"""

from __future__ import annotations

import copy
from functools import lru_cache
import hashlib
import json
from typing import Any, Mapping, Sequence

from jsonschema import Draft202012Validator, FormatChecker

from .candidate_governance_adapters import (
    CandidateGovernanceAdapterError,
    adapt_engineering_rule_pack_document,
    adapt_lifecycle_profile_registry_document,
    load_default_engineering_rule_pack_candidate,
    load_default_lifecycle_profile_registry_candidate,
)
from .environment_resolution import EnvironmentResolutionError
from .execution_environment import validate_environment_snapshot
from .field_performance_governance import (
    FieldPerformanceGovernanceError,
    validate_field_performance,
)
from .schema_access import schema_path


SCHEMA_VERSION = "governance-material-assessment/v1"
_SCHEMA_PATH = schema_path("governance-material-assessment.schema.json")
_INPUT_KEYS = {
    "engineering_rule_pack_candidate",
    "lifecycle_profile_registry_candidate",
    "environment_snapshot",
    "field_performance_bundle",
}
_LIMITATIONS = (
    "Candidate adaptation and structural replay do not establish rule correctness, adoption, external authenticity, or field qualification.",
    "ENV evidence remains unbound to this audit occurrence until an external harness supplies a digest-bound occurrence receipt and child-process trace.",
    "No material in this v1 assessment can grant formal authority, execution permission, control-plane disposition, or human acceptance.",
)


class GovernanceMaterialAssessmentError(ValueError):
    """Raised when a serialized assessment cannot be replayed."""


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _digest(value: Any) -> dict[str, str]:
    return {
        "algorithm": "sha256",
        "value": hashlib.sha256(_canonical(value)).hexdigest(),
    }


def _copy(value: Any) -> Any:
    return copy.deepcopy(value)


@lru_cache(maxsize=1)
def _validator() -> Draft202012Validator:
    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _axis(
    *,
    input_material: Any,
    validated_record: Any = None,
    binding_status: str,
    reason_codes: Sequence[str],
    rejected: bool = False,
) -> dict[str, Any]:
    present = input_material is not None
    return {
        "input_status": (
            "rejected" if rejected else "candidate_assessed" if present else "missing"
        ),
        "binding_status": binding_status,
        "input_material": _copy(input_material),
        "input_material_digest": _digest(input_material) if present else None,
        "validated_record": _copy(validated_record),
        "validated_record_digest": (
            _digest(validated_record) if validated_record is not None else None
        ),
        "reason_codes": sorted(set(str(item) for item in reason_codes)),
        "formal_authority": "none",
        "positive_assurance": False,
    }


def _missing(code: str) -> dict[str, Any]:
    return _axis(
        input_material=None,
        binding_status="not_bound",
        reason_codes=[code],
    )


def _candidate_document_input(
    value: Any, label: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(value, Mapping) or set(value) != {"document", "source_ref"}:
        raise GovernanceMaterialAssessmentError(
            f"{label} must contain exactly document and source_ref"
        )
    document = value["document"]
    source_ref = value["source_ref"]
    if not isinstance(document, Mapping) or not isinstance(source_ref, Mapping):
        raise GovernanceMaterialAssessmentError(
            f"{label} document and source_ref must be objects"
        )
    return copy.deepcopy(dict(document)), copy.deepcopy(dict(source_ref))


def _canonical_source_ref(
    document: Mapping[str, Any], raw_source_ref: Mapping[str, Any]
) -> dict[str, Any]:
    return {
        "record_id": f"{raw_source_ref['record_id']}.canonical",
        "locator": f"{raw_source_ref['locator']}#canonical-json",
        "content_digest": {
            "algorithm": "sha256",
            "value": hashlib.sha256(_canonical(document)).hexdigest(),
        },
    }


def default_candidate_governance_materials() -> dict[str, Any]:
    """Load the two pinned real candidates as explicitly untrusted inputs."""

    h1_document, _h1_bytes, h1_raw_ref = load_default_engineering_rule_pack_candidate()
    h2_document, _h2_bytes, h2_raw_ref = (
        load_default_lifecycle_profile_registry_candidate()
    )
    return {
        "engineering_rule_pack_candidate": {
            "document": h1_document,
            "source_ref": _canonical_source_ref(h1_document, h1_raw_ref),
        },
        "lifecycle_profile_registry_candidate": {
            "document": h2_document,
            "source_ref": _canonical_source_ref(h2_document, h2_raw_ref),
        },
    }


def _build_assessment(
    materials: Mapping[str, Any] | None,
    *,
    observation_digest: Mapping[str, Any],
    authority_source_ids: Sequence[str],
    subject_scope_ref: Mapping[str, Any],
) -> dict[str, Any]:
    supplied = {} if materials is None else copy.deepcopy(dict(materials))
    unknown = sorted(set(supplied) - _INPUT_KEYS)
    if unknown:
        raise GovernanceMaterialAssessmentError(
            f"unknown governance material keys: {unknown!r}"
        )
    authority_ids = sorted(set(str(item) for item in authority_source_ids))
    if len(authority_ids) != len(tuple(authority_source_ids)):
        raise GovernanceMaterialAssessmentError("authority_source_ids must be unique")

    h1_input = supplied.get("engineering_rule_pack_candidate")
    if h1_input is None:
        h1 = _missing("engineering_rule_pack_candidate_missing")
    else:
        try:
            document, source_ref = _candidate_document_input(h1_input, "H1 candidate")
            record = adapt_engineering_rule_pack_document(
                document,
                source_ref=source_ref,
                obligation_assessment_digest=observation_digest,
                authority_source_ids=authority_ids,
            )
            h1 = _axis(
                input_material=h1_input,
                validated_record=record,
                binding_status="matched_candidate",
                reason_codes=record["unresolved_codes"],
            )
        except (CandidateGovernanceAdapterError, GovernanceMaterialAssessmentError):
            h1 = _axis(
                input_material=h1_input,
                binding_status="invalid",
                reason_codes=["engineering_rule_pack_candidate_rejected"],
                rejected=True,
            )

    h2_input = supplied.get("lifecycle_profile_registry_candidate")
    if h2_input is None:
        h2 = _missing("lifecycle_profile_registry_candidate_missing")
    else:
        try:
            document, source_ref = _candidate_document_input(h2_input, "H2 candidate")
            record = adapt_lifecycle_profile_registry_document(
                document,
                source_ref=source_ref,
                subject_scope_ref=subject_scope_ref,
            )
            h2 = _axis(
                input_material=h2_input,
                validated_record=record,
                binding_status="matched_candidate",
                reason_codes=record["unresolved_codes"],
            )
        except (CandidateGovernanceAdapterError, GovernanceMaterialAssessmentError):
            h2 = _axis(
                input_material=h2_input,
                binding_status="invalid",
                reason_codes=["lifecycle_profile_registry_candidate_rejected"],
                rejected=True,
            )

    environment_input = supplied.get("environment_snapshot")
    if environment_input is None:
        environment = _missing("environment_snapshot_missing")
    else:
        try:
            if not isinstance(environment_input, Mapping):
                raise EnvironmentResolutionError(
                    "environment_snapshot_not_object", type(environment_input).__name__
                )
            record = validate_environment_snapshot(environment_input)
            environment = _axis(
                input_material=environment_input,
                validated_record=record,
                binding_status="not_bound",
                reason_codes=[
                    "environment_snapshot_not_bound_to_audit_occurrence",
                    "child_process_executable_trace_not_integrated",
                ],
            )
        except EnvironmentResolutionError:
            environment = _axis(
                input_material=environment_input,
                binding_status="invalid",
                reason_codes=["environment_snapshot_rejected"],
                rejected=True,
            )

    field_input = supplied.get("field_performance_bundle")
    if field_input is None:
        field = _missing("field_performance_bundle_missing")
    else:
        try:
            if not isinstance(field_input, Mapping):
                raise FieldPerformanceGovernanceError(
                    [
                        {
                            "code": "schema_error",
                            "location": "$",
                            "message": "field performance bundle must be an object",
                        }
                    ]
                )
            record = validate_field_performance(field_input)
            field = _axis(
                input_material=field_input,
                validated_record=record,
                binding_status="not_bound",
                reason_codes=[
                    "field_performance_bundle_not_bound_to_audit_implementation",
                    "field_qualification_not_established",
                ],
            )
        except FieldPerformanceGovernanceError:
            field = _axis(
                input_material=field_input,
                binding_status="invalid",
                reason_codes=["field_performance_bundle_rejected"],
                rejected=True,
            )

    material = {
        "schema_version": SCHEMA_VERSION,
        "observation_digest": _copy(observation_digest),
        "authority_source_ids": authority_ids,
        "subject_scope_ref": _copy(subject_scope_ref),
        "engineering_rule_governance": h1,
        "lifecycle_profile_governance": h2,
        "execution_environment_evidence": environment,
        "field_performance_evidence": field,
        "formal_authority": "none",
        "positive_assurance": False,
        "limitations": list(_LIMITATIONS),
    }
    return {**material, "assessment_digest": _digest(material)}


def assess_governance_materials(
    materials: Mapping[str, Any] | None,
    *,
    observation_digest: Mapping[str, Any],
    authority_source_ids: Sequence[str],
    subject_scope_ref: Mapping[str, Any],
) -> dict[str, Any]:
    result = _build_assessment(
        materials,
        observation_digest=observation_digest,
        authority_source_ids=authority_source_ids,
        subject_scope_ref=subject_scope_ref,
    )
    return validate_governance_material_assessment(result)


def validate_governance_material_assessment(
    assessment: Mapping[str, Any],
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(assessment))
    failures = sorted(
        _validator().iter_errors(copied),
        key=lambda item: tuple(str(part) for part in item.absolute_path),
    )
    if failures:
        failure = failures[0]
        location = "/".join(str(item) for item in failure.absolute_path) or "/"
        raise GovernanceMaterialAssessmentError(
            f"governance material assessment schema violation at {location}: {failure.message}"
        )
    inputs = {}
    for input_key, axis in (
        ("engineering_rule_pack_candidate", "engineering_rule_governance"),
        ("lifecycle_profile_registry_candidate", "lifecycle_profile_governance"),
        ("environment_snapshot", "execution_environment_evidence"),
        ("field_performance_bundle", "field_performance_evidence"),
    ):
        value = copied[axis]["input_material"]
        if value is not None:
            inputs[input_key] = value
    expected = _build_assessment(
        inputs,
        observation_digest=copied["observation_digest"],
        authority_source_ids=copied["authority_source_ids"],
        subject_scope_ref=copied["subject_scope_ref"],
    )
    if copied != expected:
        raise GovernanceMaterialAssessmentError(
            "governance material assessment does not replay from embedded inputs"
        )
    return copied


__all__ = [
    "SCHEMA_VERSION",
    "GovernanceMaterialAssessmentError",
    "assess_governance_materials",
    "default_candidate_governance_materials",
    "validate_governance_material_assessment",
]
