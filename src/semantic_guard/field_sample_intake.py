"""Prospective intake gate for ``field-evaluation/v0`` holdout cases.

The gate binds declared provenance, permission, privacy review, single-function
assessment, exposure history, duplicate closure, and split assignment before
projecting eligible representatives into the existing field-case contract.  It
does not authenticate those declarations or establish field validity.
"""

from __future__ import annotations

import copy
from datetime import datetime
from functools import lru_cache
import json
from typing import Any, Iterable, Mapping, Sequence

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

from .field_evaluation import (
    build_field_case,
    digest_value,
    field_evaluation_errors,
)
from .schema_access import schema_path


SCHEMA_VERSION = "field-sample-intake/v0"
PROSPECTIVE_MODES = frozenset(
    {"prospective_consecutive", "prospective_stratified"}
)
REQUIRED_EXPOSURE_CONTEXTS = frozenset(
    {
        "training_corpus",
        "tuning_history",
        "test_fixtures",
        "documentation_examples",
        "rule_and_route_design",
        "prior_model_inputs",
        "prior_intake_manifests",
    }
)
REQUIRED_DUPLICATE_METHODS = frozenset(
    {"exact_digest", "normalized_digest", "semantic_human_review"}
)
_EXCLUDED_REASONS = frozenset(
    {
        "evaluation_permission_not_granted",
        "calibration_use_not_permitted",
        "permission_expired_before_freeze",
        "privacy_release_not_approved",
        "not_single_function",
    }
)
_SCHEMA_PATH = schema_path("field-sample-intake.schema.json")
_FIELD_SCHEMA_PATH = schema_path("field-evaluation.schema.json")
_AUTHORITY_BOUNDARY = {
    "semantic_guard_role": (
        "validate_declared_intake_and_project_eligible_holdout_cases"
    ),
    "policy_owner": "human",
    "permission_owner": "external_human_or_organization",
    "privacy_owner": "external_human_or_organization",
    "single_function_owner": "human",
    "semantic_duplicate_owner": "human",
    "split_owner": "external_human_or_control_plane",
    "final_acceptance_owner": "human",
}
_DEFAULT_LIMITATIONS = (
    "The bundle validates declared records and deterministic bindings; it does not authenticate people, source occurrences, permissions, privacy decisions, or timestamps.",
    "SHA-256 detects changes to bound material but does not prove source authenticity, lawful use, or meaning-preserving normalization.",
    "Human semantic-duplicate and single-function assessments may be incomplete or wrong; undisclosed historical or provider-side exposure remains unknown.",
    "A valid intake bundle does not establish sampling-frame coverage, population representativeness, route accuracy, repair effect, operational value, or human acceptance.",
    "field-evaluation/v0 does not embed this intake digest; the two artifacts must remain together and be checked with the explicit binding validator.",
    "Evaluation binding rechecks declared permission expiry only through labels_released_at; undeclared revocation and later use remain outside this artifact.",
)


class FieldSampleIntakeValidationError(ValueError):
    """Expose stable codes for intake integrity or projection failures."""

    def __init__(self, errors: Sequence[Mapping[str, str]]) -> None:
        self.errors = tuple(dict(item) for item in errors)
        self.codes = tuple(str(item["code"]) for item in self.errors)
        summary = "; ".join(
            f"{item['code']}@{item['location']}: {item['message']}"
            for item in self.errors[:8]
        )
        if len(self.errors) > 8:
            summary += f"; ... {len(self.errors) - 8} more"
        super().__init__(summary)


def _sorted_dicts(
    values: Iterable[Mapping[str, Any]], *keys: str
) -> list[dict[str, Any]]:
    return sorted(
        [copy.deepcopy(dict(item)) for item in values],
        key=lambda item: tuple(str(item.get(key, "")) for key in keys),
    )


def _without_digest(value: Mapping[str, Any], field: str) -> dict[str, Any]:
    return {
        key: copy.deepcopy(item)
        for key, item in value.items()
        if key != field
    }


def _bound(material: Mapping[str, Any], field: str) -> dict[str, Any]:
    value = copy.deepcopy(dict(material))
    return {**value, field: digest_value(value)}


def _parse_time(value: str) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    return datetime.fromisoformat(normalized)


def _add(
    errors: list[dict[str, str]],
    code: str,
    location: str,
    message: str,
) -> None:
    errors.append({"code": code, "location": location, "message": message})


def _duplicates(values: Iterable[str]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return duplicates


def _schema_location(path: Any) -> str:
    values = [str(item) for item in path]
    return "$" if not values else "$." + ".".join(values)


def build_evaluation_permission(
    *,
    status: str,
    owner_ref: str,
    allowed_uses: Iterable[str],
    decision_record_ref: str | None,
    recorded_at: str | None,
    valid_through: str | None = None,
) -> dict[str, Any]:
    """Bind an external permission decision without storing source text."""

    material = {
        "status": status,
        "owner_ref": owner_ref,
        "allowed_uses": sorted(set(allowed_uses)),
        "decision_record_ref": decision_record_ref,
        "recorded_at": recorded_at,
        "valid_through": valid_through,
    }
    return _bound(material, "permission_digest")


def build_privacy_review(
    *,
    classification: str,
    handling: str,
    release_status: str,
    reviewer_ref: str,
    decision_record_ref: str | None,
    recorded_at: str | None,
    approved_subject_digest: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Bind the human/organizational release decision for the evaluated form."""

    material = {
        "classification": classification,
        "handling": handling,
        "release_status": release_status,
        "reviewer_ref": reviewer_ref,
        "decision_record_ref": decision_record_ref,
        "recorded_at": recorded_at,
        "approved_subject_digest": (
            None
            if approved_subject_digest is None
            else copy.deepcopy(dict(approved_subject_digest))
        ),
    }
    return _bound(material, "privacy_digest")


def build_function_unit_assessment(
    *,
    status: str,
    assessor_ref: str,
    assessment_record_ref: str,
    recorded_at: str,
) -> dict[str, Any]:
    """Bind a human assessment of the one-functional-unit boundary."""

    material = {
        "status": status,
        "assessor_kind": "human",
        "assessor_ref": assessor_ref,
        "assessment_record_ref": assessment_record_ref,
        "recorded_at": recorded_at,
    }
    return _bound(material, "assessment_digest")


def build_exposure_declaration(
    *,
    status: str,
    checked_contexts: Iterable[str],
    records: Iterable[Mapping[str, Any]],
    declared_by: str,
    recorded_at: str,
) -> dict[str, Any]:
    """Bind a scoped exposure search and its known records."""

    material = {
        "status": status,
        "checked_contexts": sorted(set(checked_contexts)),
        "records": _sorted_dicts(records, "exposure_id"),
        "declared_by": declared_by,
        "recorded_at": recorded_at,
    }
    return _bound(material, "exposure_digest")


def build_intake_candidate(
    *,
    candidate_id: str,
    field_case_id: str,
    subject_ref: str,
    source_occurrence_id: str,
    origin_ref: str,
    source_revision: str,
    source_kind: str,
    acquired_at: str,
    collector_ref: str,
    original_digest: Mapping[str, Any],
    normalized_digest: Mapping[str, Any],
    evaluation_subject_digest: Mapping[str, Any],
    normalization_profile: Mapping[str, Any],
    population_id: str,
    intended_use_id: str,
    stratum_refs: Iterable[str],
    derived_from_refs: Iterable[str],
    permission: Mapping[str, Any],
    privacy_review: Mapping[str, Any],
    unit_assessment: Mapping[str, Any],
    exposure_declaration: Mapping[str, Any],
) -> dict[str, Any]:
    """Build one content-addressed candidate without embedding raw material."""

    material = {
        "candidate_id": candidate_id,
        "field_case_id": field_case_id,
        "subject_ref": subject_ref,
        "source_occurrence_id": source_occurrence_id,
        "origin_ref": origin_ref,
        "source_revision": source_revision,
        "source_kind": source_kind,
        "acquired_at": acquired_at,
        "collector_ref": collector_ref,
        "original_digest": copy.deepcopy(dict(original_digest)),
        "normalized_digest": copy.deepcopy(dict(normalized_digest)),
        "evaluation_subject_digest": copy.deepcopy(
            dict(evaluation_subject_digest)
        ),
        "normalization_profile_ref": normalization_profile["ref_id"],
        "normalization_profile_digest": copy.deepcopy(
            dict(normalization_profile["digest"])
        ),
        "population_id": population_id,
        "intended_use_id": intended_use_id,
        "stratum_refs": sorted(set(stratum_refs)),
        "derived_from_refs": sorted(set(derived_from_refs)),
        "permission": copy.deepcopy(dict(permission)),
        "privacy_review": copy.deepcopy(dict(privacy_review)),
        "unit_assessment": copy.deepcopy(dict(unit_assessment)),
        "exposure_declaration": copy.deepcopy(dict(exposure_declaration)),
    }
    return _bound(material, "candidate_digest")


def build_duplicate_cluster(
    *,
    cluster_id: str,
    member_refs: Iterable[str],
    representative_ref: str,
    assigned_split: str,
    assignment_protocol: Mapping[str, Any],
    assignment_record_ref: str,
    assigned_at: str,
) -> dict[str, Any]:
    """Assign a closed duplicate unit to exactly one split."""

    material = {
        "cluster_id": cluster_id,
        "member_refs": sorted(set(member_refs)),
        "representative_ref": representative_ref,
        "assigned_split": assigned_split,
        "assignment_protocol_ref": assignment_protocol["ref_id"],
        "assignment_protocol_digest": copy.deepcopy(
            dict(assignment_protocol["digest"])
        ),
        "assignment_record_ref": assignment_record_ref,
        "assigned_at": assigned_at,
    }
    return _bound(material, "cluster_digest")


def _bind_policy(
    policy: Mapping[str, Any],
    human_policy_decision: Mapping[str, Any] | None,
) -> dict[str, Any]:
    target = policy["target_population"]
    decision: dict[str, Any] | None = None
    if human_policy_decision is not None:
        source = human_policy_decision
        decision_material = {
            "decision_id": source["decision_id"],
            "decision_type": source["decision_type"],
            "issuer_kind": source["issuer_kind"],
            "human_actor_ref": source["human_actor_ref"],
            "policy_id": source["policy_id"],
            "policy_version": source["policy_version"],
            "policy_digest": copy.deepcopy(dict(source["policy_digest"])),
            "decision": source["decision"],
            "rationale_digest": digest_value(source["rationale"]),
            "evidence_refs": sorted(set(source["evidence_refs"])),
            "recorded_at": source["recorded_at"],
        }
        decision = _bound(decision_material, "decision_digest")
    material = {
        "policy_id": policy["policy_id"],
        "policy_version": policy["version"],
        "policy_digest": copy.deepcopy(dict(policy["policy_digest"])),
        "policy_status": policy["status"],
        "evidence_class": policy["evidence_class"],
        "population_id": target["population_id"],
        "intended_use_id": target["intended_use_id"],
        "population_digest": copy.deepcopy(dict(target["population_digest"])),
        "stratification": _stratification_binding(policy),
        "human_decision": decision,
    }
    return _bound(material, "policy_binding_digest")


def _stratification_binding(
    policy: Mapping[str, Any],
) -> list[dict[str, Any]]:
    return sorted(
        [
            {
                "dimension_id": str(dimension["dimension_id"]),
                "required": bool(dimension["required"]),
                "stratum_refs": sorted(
                    str(stratum["stratum_id"])
                    for stratum in dimension["strata"]
                ),
            }
            for dimension in policy["stratification"]
        ],
        key=lambda dimension: dimension["dimension_id"],
    )


def _candidate_stratum_reasons(
    candidate: Mapping[str, Any],
    policy_binding: Mapping[str, Any],
) -> set[str]:
    declared: set[str] = set()
    required_dimensions: list[set[str]] = []
    for dimension in policy_binding["stratification"]:
        refs = {str(item) for item in dimension["stratum_refs"]}
        declared.update(refs)
        if dimension["required"]:
            required_dimensions.append(refs)
    candidate_refs = {str(item) for item in candidate["stratum_refs"]}
    reasons: set[str] = set()
    if not candidate_refs.issubset(declared):
        reasons.add("stratum_not_declared")
    if any(len(candidate_refs & refs) != 1 for refs in required_dimensions):
        reasons.add("required_stratum_cardinality_invalid")
    return reasons


def _bind_collection(collection: Mapping[str, Any]) -> dict[str, Any]:
    material = {
        key: copy.deepcopy(value)
        for key, value in collection.items()
        if key != "collection_digest"
    }
    return _bound(material, "collection_digest")


def _policy_decision_matches(binding: Mapping[str, Any]) -> bool:
    status = binding["policy_status"]
    decision = binding["human_decision"]
    if status == "pending":
        return decision is None
    if decision is None:
        return False
    expected_type = "adopt_policy" if status == "adopted" else "retire_policy"
    expected_value = "adopt" if status == "adopted" else "retire"
    return bool(
        decision["decision_type"] == expected_type
        and decision["decision"] == expected_value
        and decision["issuer_kind"] == "human"
        and decision["policy_id"] == binding["policy_id"]
        and decision["policy_version"] == binding["policy_version"]
        and decision["policy_digest"] == binding["policy_digest"]
    )


def _candidate_assessment(
    candidate: Mapping[str, Any],
    *,
    policy_binding: Mapping[str, Any],
    collection: Mapping[str, Any],
) -> dict[str, Any]:
    reasons: set[str] = set()
    permission = candidate["permission"]
    allowed_uses = set(permission["allowed_uses"])
    can_calibrate = "calibration" in allowed_uses
    can_holdout = {
        "holdout_evaluation",
        "derived_metrics",
    }.issubset(allowed_uses)

    if permission["status"] != "granted":
        reasons.add("evaluation_permission_not_granted")
    elif not can_holdout:
        reasons.add(
            "holdout_use_not_permitted"
            if can_calibrate
            else "calibration_use_not_permitted"
        )
    valid_through = permission["valid_through"]
    if valid_through is not None and _parse_time(valid_through) < _parse_time(
        collection["assignment_frozen_at"]
    ):
        reasons.add("permission_expired_before_freeze")

    if candidate["privacy_review"]["release_status"] != "approved":
        reasons.add("privacy_release_not_approved")
    if candidate["unit_assessment"]["status"] != "single_function":
        reasons.add("not_single_function")
    reasons.update(_candidate_stratum_reasons(candidate, policy_binding))

    if not _EXCLUDED_REASONS.isdisjoint(reasons):
        status = "excluded"
    else:
        if policy_binding["policy_status"] != "adopted":
            reasons.add("policy_not_adopted")
        if not _policy_decision_matches(policy_binding):
            reasons.add("policy_decision_missing_or_mismatched")
        else:
            decision = policy_binding["human_decision"]
            if (
                decision is not None
                and _parse_time(decision["recorded_at"])
                >= _parse_time(collection["opened_at"])
            ):
                reasons.add("policy_adopted_after_collection_open")
        if policy_binding["evidence_class"] != "field_evaluation":
            reasons.add("policy_evidence_class_not_field")
        if collection["acquisition_mode"] not in PROSPECTIVE_MODES:
            reasons.add("collection_not_prospective")

        exposure = candidate["exposure_declaration"]
        if exposure["status"] == "known_exposure":
            reasons.add("known_prior_exposure")
        elif exposure["status"] == "unknown":
            reasons.add("exposure_status_unknown")
        if set(exposure["checked_contexts"]) != REQUIRED_EXPOSURE_CONTEXTS:
            reasons.add("exposure_scope_incomplete")
        status = "calibration_only" if reasons else "eligible_for_holdout"

    material = {
        "candidate_id": candidate["candidate_id"],
        "candidate_digest": copy.deepcopy(dict(candidate["candidate_digest"])),
        "status": status,
        "reason_codes": sorted(reasons),
    }
    return _bound(material, "assessment_digest")


def _cluster_assessment(
    cluster: Mapping[str, Any],
    *,
    candidate_assessments: Mapping[str, Mapping[str, Any]],
    duplicate_review: Mapping[str, Any],
) -> dict[str, Any]:
    reasons: set[str] = set()
    statuses: set[str] = set()
    for candidate_id in cluster["member_refs"]:
        assessment = candidate_assessments.get(candidate_id)
        if assessment is None:
            continue
        statuses.add(str(assessment["status"]))
        reasons.update(str(item) for item in assessment["reason_codes"])

    if duplicate_review["status"] != "complete":
        reasons.add("duplicate_review_incomplete")
    if set(duplicate_review["methods"]) != REQUIRED_DUPLICATE_METHODS:
        reasons.add("duplicate_review_methods_incomplete")

    if "excluded" in statuses or not _EXCLUDED_REASONS.isdisjoint(reasons):
        status = "excluded"
    elif (
        "calibration_only" in statuses
        or "duplicate_review_incomplete" in reasons
        or "duplicate_review_methods_incomplete" in reasons
    ):
        status = "calibration_only"
    else:
        status = "eligible_for_holdout"
    material = {
        "cluster_id": cluster["cluster_id"],
        "cluster_digest": copy.deepcopy(dict(cluster["cluster_digest"])),
        "status": status,
        "reason_codes": sorted(reasons),
    }
    return _bound(material, "assessment_digest")


def _build_duplicate_review(
    *,
    spec: Mapping[str, Any],
    candidates: Sequence[Mapping[str, Any]],
    clusters: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    material = {
        "review_id": spec["review_id"],
        "status": spec["status"],
        "reviewer_kind": "human",
        "reviewer_ref": spec["reviewer_ref"],
        "review_record_ref": spec["review_record_ref"],
        "methods": sorted(set(spec["methods"])),
        "comparison_scope": copy.deepcopy(dict(spec["comparison_scope"])),
        "candidate_set_digest": digest_value(_sorted_dicts(candidates, "candidate_id")),
        "cluster_set_digest": digest_value(_sorted_dicts(clusters, "cluster_id")),
        "completed_at": spec["completed_at"],
    }
    return _bound(material, "review_digest")


def _projection_cases(
    *,
    clusters: Sequence[Mapping[str, Any]],
    candidates_by_id: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for cluster in clusters:
        if cluster["assigned_split"] != "holdout":
            continue
        candidate = candidates_by_id.get(str(cluster["representative_ref"]))
        if candidate is None:
            continue
        cases.append(
            build_field_case(
                case_id=str(candidate["field_case_id"]),
                subject_ref=str(candidate["subject_ref"]),
                subject_digest=candidate["evaluation_subject_digest"],
                population_id=str(candidate["population_id"]),
                intended_use_id=str(candidate["intended_use_id"]),
                stratum_refs=candidate["stratum_refs"],
                source_kind="field_sample",
            )
        )
    return _sorted_dicts(cases, "case_id")


def _build_holdout_projection(
    *,
    policy_binding: Mapping[str, Any],
    clusters: Sequence[Mapping[str, Any]],
    candidates_by_id: Mapping[str, Mapping[str, Any]],
    cluster_assessments: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    holdout_clusters = [
        cluster for cluster in clusters if cluster["assigned_split"] == "holdout"
    ]
    reasons: set[str] = set()
    for cluster in holdout_clusters:
        assessment = cluster_assessments.get(str(cluster["cluster_id"]))
        if assessment is not None and assessment["status"] != "eligible_for_holdout":
            reasons.update(str(item) for item in assessment["reason_codes"])

    if not holdout_clusters:
        status = "not_requested"
        cases: list[dict[str, Any]] = []
    elif reasons:
        status = "blocked"
        cases = []
    else:
        status = "ready"
        cases = _projection_cases(
            clusters=clusters,
            candidates_by_id=candidates_by_id,
        )
    material = {
        "status": status,
        "reason_codes": sorted(reasons),
        "policy_id": policy_binding["policy_id"],
        "policy_version": policy_binding["policy_version"],
        "policy_digest": copy.deepcopy(dict(policy_binding["policy_digest"])),
        "population_digest": copy.deepcopy(
            dict(policy_binding["population_digest"])
        ),
        "cases": cases,
        "case_set_digest": digest_value(cases) if cases else None,
    }
    return _bound(material, "projection_digest")


def _count_status(values: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    return {
        status: sum(item["status"] == status for item in values)
        for status in ("eligible_for_holdout", "calibration_only", "excluded")
    }


def _build_summary(
    *,
    candidates: Sequence[Mapping[str, Any]],
    clusters: Sequence[Mapping[str, Any]],
    candidate_assessments: Sequence[Mapping[str, Any]],
    cluster_assessments: Sequence[Mapping[str, Any]],
    holdout_projection: Mapping[str, Any],
) -> dict[str, Any]:
    material = {
        "candidate_count": len(candidates),
        "cluster_count": len(clusters),
        "candidate_status_counts": _count_status(candidate_assessments),
        "cluster_status_counts": _count_status(cluster_assessments),
        "split_counts": {
            split: sum(item["assigned_split"] == split for item in clusters)
            for split in ("calibration", "holdout", "excluded")
        },
        "projected_holdout_case_count": len(holdout_projection["cases"]),
    }
    return _bound(material, "summary_digest")


def build_field_sample_intake(
    *,
    intake_id: str,
    policy: Mapping[str, Any],
    human_policy_decision: Mapping[str, Any] | None,
    collection: Mapping[str, Any],
    normalization_profile: Mapping[str, Any],
    assignment_protocol: Mapping[str, Any],
    candidates: Iterable[Mapping[str, Any]],
    duplicate_clusters: Iterable[Mapping[str, Any]],
    duplicate_review_spec: Mapping[str, Any],
    limitations: Iterable[str] = _DEFAULT_LIMITATIONS,
) -> dict[str, Any]:
    """Build a deterministic intake ledger and prospective holdout projection."""

    policy_binding = _bind_policy(policy, human_policy_decision)
    collection_value = _bind_collection(collection)
    candidate_values = _sorted_dicts(candidates, "candidate_id")
    cluster_values = _sorted_dicts(duplicate_clusters, "cluster_id")
    duplicate_review = _build_duplicate_review(
        spec=duplicate_review_spec,
        candidates=candidate_values,
        clusters=cluster_values,
    )
    candidate_assessments = [
        _candidate_assessment(
            candidate,
            policy_binding=policy_binding,
            collection=collection_value,
        )
        for candidate in candidate_values
    ]
    candidate_assessments = _sorted_dicts(
        candidate_assessments, "candidate_id"
    )
    candidate_assessments_by_id = {
        str(item["candidate_id"]): item for item in candidate_assessments
    }
    cluster_assessments = [
        _cluster_assessment(
            cluster,
            candidate_assessments=candidate_assessments_by_id,
            duplicate_review=duplicate_review,
        )
        for cluster in cluster_values
    ]
    cluster_assessments = _sorted_dicts(cluster_assessments, "cluster_id")
    cluster_assessments_by_id = {
        str(item["cluster_id"]): item for item in cluster_assessments
    }
    candidates_by_id = {
        str(item["candidate_id"]): item for item in candidate_values
    }
    holdout_projection = _build_holdout_projection(
        policy_binding=policy_binding,
        clusters=cluster_values,
        candidates_by_id=candidates_by_id,
        cluster_assessments=cluster_assessments_by_id,
    )
    summary = _build_summary(
        candidates=candidate_values,
        clusters=cluster_values,
        candidate_assessments=candidate_assessments,
        cluster_assessments=cluster_assessments,
        holdout_projection=holdout_projection,
    )
    material = {
        "schema_version": SCHEMA_VERSION,
        "intake_id": intake_id,
        "policy_binding": policy_binding,
        "collection": collection_value,
        "normalization_profile": copy.deepcopy(dict(normalization_profile)),
        "assignment_protocol": copy.deepcopy(dict(assignment_protocol)),
        "candidates": candidate_values,
        "duplicate_clusters": cluster_values,
        "duplicate_review": duplicate_review,
        "candidate_assessments": candidate_assessments,
        "cluster_assessments": cluster_assessments,
        "holdout_projection": holdout_projection,
        "summary": summary,
        "authority_boundary": copy.deepcopy(_AUTHORITY_BOUNDARY),
        "limitations": sorted(set(limitations)),
    }
    return _bound(material, "bundle_digest")


@lru_cache(maxsize=1)
def _schema_validator() -> Draft202012Validator:
    schemas = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in (_SCHEMA_PATH, _FIELD_SCHEMA_PATH)
    ]
    for schema in schemas:
        Draft202012Validator.check_schema(schema)
    registry = Registry().with_resources(
        [(schema["$id"], Resource.from_contents(schema)) for schema in schemas]
    )
    return Draft202012Validator(
        schemas[0], registry=registry, format_checker=FormatChecker()
    )


@lru_cache(maxsize=1)
def _policy_schema_validator() -> Draft202012Validator:
    field_schema = json.loads(_FIELD_SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(field_schema)
    registry = Registry().with_resource(
        field_schema["$id"], Resource.from_contents(field_schema)
    )
    return Draft202012Validator(
        {"$ref": f"{field_schema['$id']}#/$defs/policy"},
        registry=registry,
        format_checker=FormatChecker(),
    )


def _check_record_digest(
    errors: list[dict[str, str]],
    value: Mapping[str, Any],
    field: str,
    location: str,
    code: str,
) -> None:
    if value[field] != digest_value(_without_digest(value, field)):
        _add(errors, code, f"{location}.{field}", "content digest does not replay")


def _check_record_time(
    errors: list[dict[str, str]],
    value: str | None,
    *,
    acquired_at: str,
    frozen_at: str,
    location: str,
) -> None:
    if value is None:
        return
    if not (
        _parse_time(acquired_at)
        <= _parse_time(value)
        <= _parse_time(frozen_at)
    ):
        _add(
            errors,
            "candidate_record_time_invalid",
            location,
            "candidate review/declaration must be recorded from acquisition through assignment freeze",
        )


def _lineage_cycle(candidate_by_id: Mapping[str, Mapping[str, Any]]) -> bool:
    indegree = {candidate_id: 0 for candidate_id in candidate_by_id}
    children = {candidate_id: [] for candidate_id in candidate_by_id}
    for child_id, candidate in candidate_by_id.items():
        for parent in candidate["derived_from_refs"]:
            parent_id = str(parent)
            if parent_id not in candidate_by_id:
                continue
            indegree[child_id] += 1
            children[parent_id].append(child_id)
    ready = sorted(
        candidate_id for candidate_id, degree in indegree.items() if degree == 0
    )
    visited = 0
    while ready:
        candidate_id = ready.pop()
        visited += 1
        for child_id in children[candidate_id]:
            indegree[child_id] -= 1
            if indegree[child_id] == 0:
                ready.append(child_id)
    return visited != len(candidate_by_id)


def field_sample_intake_errors(
    bundle: Mapping[str, Any],
) -> tuple[dict[str, str], ...]:
    """Return deterministic, fail-closed intake integrity errors."""

    errors: list[dict[str, str]] = []
    schema_failures = sorted(
        _schema_validator().iter_errors(bundle), key=lambda issue: list(issue.path)
    )
    for failure in schema_failures:
        _add(
            errors,
            "schema_validation_failed",
            _schema_location(failure.path),
            failure.message,
        )
    if schema_failures:
        return tuple(
            sorted(errors, key=lambda item: (item["location"], item["code"], item["message"]))
        )

    _check_record_digest(
        errors, bundle, "bundle_digest", "$", "bundle_digest_mismatch"
    )
    policy_binding = bundle["policy_binding"]
    _check_record_digest(
        errors,
        policy_binding,
        "policy_binding_digest",
        "$.policy_binding",
        "policy_binding_digest_mismatch",
    )
    decision = policy_binding["human_decision"]
    if decision is not None:
        _check_record_digest(
            errors,
            decision,
            "decision_digest",
            "$.policy_binding.human_decision",
            "policy_decision_digest_mismatch",
        )
    if not _policy_decision_matches(policy_binding):
        _add(
            errors,
            "policy_decision_missing_or_mismatched",
            "$.policy_binding.human_decision",
            "policy state is not bound to the matching external human decision",
        )

    collection = bundle["collection"]
    _check_record_digest(
        errors,
        collection,
        "collection_digest",
        "$.collection",
        "collection_digest_mismatch",
    )
    opened_at = collection["opened_at"]
    closed_at = collection["closed_at"]
    frozen_at = collection["assignment_frozen_at"]
    if not (
        _parse_time(opened_at)
        < _parse_time(closed_at)
        <= _parse_time(frozen_at)
    ):
        _add(
            errors,
            "collection_time_order_invalid",
            "$.collection",
            "collection open must precede close, and close must not follow assignment freeze",
        )

    candidates = bundle["candidates"]
    candidate_ids = [str(item["candidate_id"]) for item in candidates]
    field_case_ids = [str(item["field_case_id"]) for item in candidates]
    if candidate_ids != sorted(candidate_ids):
        _add(
            errors,
            "candidate_order_noncanonical",
            "$.candidates",
            "candidates must be ordered by candidate_id",
        )
    for duplicate in sorted(_duplicates(candidate_ids)):
        _add(errors, "duplicate_candidate", "$.candidates", duplicate)
    for duplicate in sorted(_duplicates(field_case_ids)):
        _add(errors, "duplicate_field_case_id", "$.candidates", duplicate)
    candidates_by_id = {
        str(item["candidate_id"]): item for item in candidates
    }
    candidate_index_by_id = {
        str(item["candidate_id"]): index for index, item in enumerate(candidates)
    }
    declared_strata: dict[str, str] = {}
    required_dimensions: dict[str, set[str]] = {}
    for dimension in policy_binding["stratification"]:
        dimension_id = str(dimension["dimension_id"])
        refs = {str(item) for item in dimension["stratum_refs"]}
        for stratum_ref in refs:
            if stratum_ref in declared_strata:
                _add(
                    errors,
                    "duplicate_policy_stratum_id",
                    "$.policy_binding.stratification",
                    stratum_ref,
                )
            declared_strata[stratum_ref] = dimension_id
        if dimension["required"]:
            required_dimensions[dimension_id] = refs
    occurrence_digests: dict[str, Mapping[str, Any]] = {}
    exposure_ids: list[str] = []
    for index, candidate in enumerate(candidates):
        location = f"$.candidates.{index}"
        _check_record_digest(
            errors,
            candidate,
            "candidate_digest",
            location,
            "candidate_digest_mismatch",
        )
        for field, code in (
            ("permission", "permission_digest_mismatch"),
            ("privacy_review", "privacy_digest_mismatch"),
            ("unit_assessment", "unit_assessment_digest_mismatch"),
            ("exposure_declaration", "exposure_digest_mismatch"),
        ):
            record = candidate[field]
            digest_field = {
                "permission": "permission_digest",
                "privacy_review": "privacy_digest",
                "unit_assessment": "assessment_digest",
                "exposure_declaration": "exposure_digest",
            }[field]
            _check_record_digest(
                errors, record, digest_field, f"{location}.{field}", code
            )

        if (
            candidate["normalization_profile_ref"]
            != bundle["normalization_profile"]["ref_id"]
            or candidate["normalization_profile_digest"]
            != bundle["normalization_profile"]["digest"]
        ):
            _add(
                errors,
                "normalization_profile_binding_mismatch",
                location,
                candidate["candidate_id"],
            )
        if (
            candidate["population_id"] != policy_binding["population_id"]
            or candidate["intended_use_id"] != policy_binding["intended_use_id"]
        ):
            _add(
                errors,
                "candidate_population_mismatch",
                location,
                candidate["candidate_id"],
            )
        candidate_strata = {str(item) for item in candidate["stratum_refs"]}
        for stratum_ref in sorted(candidate_strata - set(declared_strata)):
            _add(
                errors,
                "candidate_dangling_stratum",
                f"{location}.stratum_refs",
                stratum_ref,
            )
        for dimension_id, stratum_refs in required_dimensions.items():
            count = len(candidate_strata & stratum_refs)
            if count != 1:
                _add(
                    errors,
                    "candidate_required_stratum_cardinality",
                    f"{location}.stratum_refs",
                    f"{dimension_id}: {count}",
                )
        acquired_at = candidate["acquired_at"]
        if not (
            _parse_time(opened_at)
            <= _parse_time(acquired_at)
            <= _parse_time(closed_at)
        ):
            _add(
                errors,
                "candidate_acquisition_time_invalid",
                f"{location}.acquired_at",
                candidate["candidate_id"],
            )
        occurrence = str(candidate["source_occurrence_id"])
        prior_digest = occurrence_digests.get(occurrence)
        if prior_digest is not None and prior_digest != candidate["original_digest"]:
            _add(
                errors,
                "source_occurrence_content_conflict",
                f"{location}.source_occurrence_id",
                occurrence,
            )
        occurrence_digests[occurrence] = candidate["original_digest"]

        permission = candidate["permission"]
        if permission["status"] == "granted" and (
            permission["decision_record_ref"] is None
            or permission["recorded_at"] is None
            or not permission["allowed_uses"]
        ):
            _add(
                errors,
                "granted_permission_record_incomplete",
                f"{location}.permission",
                candidate["candidate_id"],
            )
        if (
            permission["recorded_at"] is not None
            and _parse_time(permission["recorded_at"]) > _parse_time(frozen_at)
        ):
            _add(
                errors,
                "permission_record_after_freeze",
                f"{location}.permission.recorded_at",
                candidate["candidate_id"],
            )
        _check_record_time(
            errors,
            permission["recorded_at"],
            acquired_at=acquired_at,
            frozen_at=frozen_at,
            location=f"{location}.permission.recorded_at",
        )
        if (
            permission["valid_through"] is not None
            and permission["recorded_at"] is not None
            and _parse_time(permission["valid_through"])
            < _parse_time(permission["recorded_at"])
        ):
            _add(
                errors,
                "permission_time_order_invalid",
                f"{location}.permission.valid_through",
                candidate["candidate_id"],
            )

        privacy = candidate["privacy_review"]
        if privacy["release_status"] == "approved":
            if (
                privacy["decision_record_ref"] is None
                or privacy["recorded_at"] is None
                or privacy["approved_subject_digest"]
                != candidate["evaluation_subject_digest"]
            ):
                _add(
                    errors,
                    "privacy_subject_binding_mismatch",
                    f"{location}.privacy_review",
                    candidate["candidate_id"],
                )
        if (
            privacy["classification"] in {"confidential", "restricted"}
            and privacy["handling"] == "not_required"
        ):
            _add(
                errors,
                "sensitive_handling_not_established",
                f"{location}.privacy_review.handling",
                candidate["candidate_id"],
            )
        _check_record_time(
            errors,
            privacy["recorded_at"],
            acquired_at=acquired_at,
            frozen_at=frozen_at,
            location=f"{location}.privacy_review.recorded_at",
        )
        _check_record_time(
            errors,
            candidate["unit_assessment"]["recorded_at"],
            acquired_at=acquired_at,
            frozen_at=frozen_at,
            location=f"{location}.unit_assessment.recorded_at",
        )
        exposure = candidate["exposure_declaration"]
        _check_record_time(
            errors,
            exposure["recorded_at"],
            acquired_at=acquired_at,
            frozen_at=frozen_at,
            location=f"{location}.exposure_declaration.recorded_at",
        )
        if exposure["status"] == "known_exposure" and not exposure["records"]:
            _add(
                errors,
                "known_exposure_record_missing",
                f"{location}.exposure_declaration.records",
                candidate["candidate_id"],
            )
        if exposure["status"] != "known_exposure" and exposure["records"]:
            _add(
                errors,
                "exposure_status_records_mismatch",
                f"{location}.exposure_declaration",
                candidate["candidate_id"],
            )
        exposure_ids.extend(str(item["exposure_id"]) for item in exposure["records"])
        for parent in candidate["derived_from_refs"]:
            if parent == candidate["candidate_id"]:
                _add(
                    errors,
                    "lineage_self_reference",
                    f"{location}.derived_from_refs",
                    str(parent),
                )
            elif parent not in candidates_by_id:
                _add(
                    errors,
                    "lineage_parent_unknown",
                    f"{location}.derived_from_refs",
                    str(parent),
                )
    for duplicate in sorted(_duplicates(exposure_ids)):
        _add(errors, "duplicate_exposure_record", "$.candidates", duplicate)
    if _lineage_cycle(candidates_by_id):
        _add(
            errors,
            "lineage_cycle",
            "$.candidates",
            "derived_from_refs must form an acyclic graph",
        )

    clusters = bundle["duplicate_clusters"]
    cluster_ids = [str(item["cluster_id"]) for item in clusters]
    if cluster_ids != sorted(cluster_ids):
        _add(
            errors,
            "cluster_order_noncanonical",
            "$.duplicate_clusters",
            "clusters must be ordered by cluster_id",
        )
    for duplicate in sorted(_duplicates(cluster_ids)):
        _add(errors, "duplicate_cluster", "$.duplicate_clusters", duplicate)
    member_to_clusters: dict[str, list[str]] = {}
    clusters_by_id = {str(item["cluster_id"]): item for item in clusters}
    candidate_to_cluster: dict[str, str] = {}
    for index, cluster in enumerate(clusters):
        location = f"$.duplicate_clusters.{index}"
        _check_record_digest(
            errors,
            cluster,
            "cluster_digest",
            location,
            "cluster_digest_mismatch",
        )
        if (
            cluster["assignment_protocol_ref"]
            != bundle["assignment_protocol"]["ref_id"]
            or cluster["assignment_protocol_digest"]
            != bundle["assignment_protocol"]["digest"]
        ):
            _add(
                errors,
                "assignment_protocol_binding_mismatch",
                location,
                cluster["cluster_id"],
            )
        if cluster["representative_ref"] not in cluster["member_refs"]:
            _add(
                errors,
                "cluster_representative_not_member",
                f"{location}.representative_ref",
                cluster["cluster_id"],
            )
        for member in cluster["member_refs"]:
            member_to_clusters.setdefault(str(member), []).append(
                str(cluster["cluster_id"])
            )
            if member not in candidates_by_id:
                _add(
                    errors,
                    "cluster_member_unknown",
                    f"{location}.member_refs",
                    str(member),
                )
            else:
                candidate_to_cluster[str(member)] = str(cluster["cluster_id"])
                candidate = candidates_by_id[str(member)]
                candidate_location = (
                    f"$.candidates.{candidate_index_by_id[str(member)]}"
                )
                for record_name, recorded_at in (
                    ("permission", candidate["permission"]["recorded_at"]),
                    (
                        "privacy_review",
                        candidate["privacy_review"]["recorded_at"],
                    ),
                    (
                        "unit_assessment",
                        candidate["unit_assessment"]["recorded_at"],
                    ),
                    (
                        "exposure_declaration",
                        candidate["exposure_declaration"]["recorded_at"],
                    ),
                ):
                    if (
                        recorded_at is not None
                        and _parse_time(recorded_at)
                        > _parse_time(cluster["assigned_at"])
                    ):
                        _add(
                            errors,
                            "candidate_record_after_assignment",
                            f"{candidate_location}.{record_name}.recorded_at",
                            str(member),
                        )
        if not (
            _parse_time(bundle["duplicate_review"]["completed_at"])
            <= _parse_time(cluster["assigned_at"])
            <= _parse_time(frozen_at)
        ):
            _add(
                errors,
                "cluster_assignment_time_invalid",
                f"{location}.assigned_at",
                cluster["cluster_id"],
            )
        if cluster["assigned_split"] == "calibration":
            missing_permission = [
                member
                for member in cluster["member_refs"]
                if member in candidates_by_id
                and "calibration"
                not in candidates_by_id[str(member)]["permission"]["allowed_uses"]
            ]
            if missing_permission:
                _add(
                    errors,
                    "calibration_assignment_not_permitted",
                    f"{location}.assigned_split",
                    str(sorted(missing_permission)),
                )
    for candidate_id in candidate_ids:
        memberships = member_to_clusters.get(candidate_id, [])
        if not memberships:
            _add(
                errors,
                "candidate_cluster_missing",
                "$.duplicate_clusters",
                candidate_id,
            )
        elif len(memberships) > 1:
            _add(
                errors,
                "candidate_cluster_membership_conflict",
                "$.duplicate_clusters",
                candidate_id,
            )

    for digest_field, code in (
        ("original_digest", "exact_duplicate_cluster_mismatch"),
        ("normalized_digest", "normalized_duplicate_cluster_mismatch"),
    ):
        digest_clusters: dict[str, set[str]] = {}
        for candidate in candidates:
            cluster_id = candidate_to_cluster.get(str(candidate["candidate_id"]))
            if cluster_id is None:
                continue
            value = str(candidate[digest_field]["value"])
            digest_clusters.setdefault(value, set()).add(cluster_id)
        for value, cluster_refs in sorted(digest_clusters.items()):
            if len(cluster_refs) > 1:
                _add(
                    errors,
                    code,
                    "$.duplicate_clusters",
                    f"{value}: {sorted(cluster_refs)}",
                )
    for candidate in candidates:
        child_cluster = candidate_to_cluster.get(str(candidate["candidate_id"]))
        for parent in candidate["derived_from_refs"]:
            parent_cluster = candidate_to_cluster.get(str(parent))
            if (
                child_cluster is not None
                and parent_cluster is not None
                and child_cluster != parent_cluster
            ):
                _add(
                    errors,
                    "lineage_cluster_mismatch",
                    "$.duplicate_clusters",
                    f"{parent} -> {candidate['candidate_id']}",
                )

    review = bundle["duplicate_review"]
    _check_record_digest(
        errors,
        review,
        "review_digest",
        "$.duplicate_review",
        "duplicate_review_digest_mismatch",
    )
    expected_candidate_set_digest = digest_value(
        _sorted_dicts(candidates, "candidate_id")
    )
    expected_cluster_set_digest = digest_value(_sorted_dicts(clusters, "cluster_id"))
    if review["candidate_set_digest"] != expected_candidate_set_digest:
        _add(
            errors,
            "duplicate_review_candidate_set_mismatch",
            "$.duplicate_review.candidate_set_digest",
            "review does not cover the exact candidate set",
        )
    if review["cluster_set_digest"] != expected_cluster_set_digest:
        _add(
            errors,
            "duplicate_review_cluster_set_mismatch",
            "$.duplicate_review.cluster_set_digest",
            "review does not cover the exact cluster set",
        )
    if not (
        _parse_time(closed_at)
        <= _parse_time(review["completed_at"])
        <= _parse_time(frozen_at)
    ):
        _add(
            errors,
            "duplicate_review_time_invalid",
            "$.duplicate_review.completed_at",
            "duplicate review must cover the closed collection before assignment freeze",
        )

    expected_candidate_assessments = _sorted_dicts(
        [
            _candidate_assessment(
                candidate,
                policy_binding=policy_binding,
                collection=collection,
            )
            for candidate in candidates
        ],
        "candidate_id",
    )
    if bundle["candidate_assessments"] != expected_candidate_assessments:
        _add(
            errors,
            "candidate_assessment_replay_mismatch",
            "$.candidate_assessments",
            "stored candidate eligibility does not equal deterministic recomputation",
        )
    candidate_assessments_by_id = {
        str(item["candidate_id"]): item for item in expected_candidate_assessments
    }
    expected_cluster_assessments = _sorted_dicts(
        [
            _cluster_assessment(
                cluster,
                candidate_assessments=candidate_assessments_by_id,
                duplicate_review=review,
            )
            for cluster in clusters
        ],
        "cluster_id",
    )
    if bundle["cluster_assessments"] != expected_cluster_assessments:
        _add(
            errors,
            "cluster_assessment_replay_mismatch",
            "$.cluster_assessments",
            "stored cluster eligibility does not equal deterministic recomputation",
        )
    cluster_assessments_by_id = {
        str(item["cluster_id"]): item for item in expected_cluster_assessments
    }
    expected_projection = _build_holdout_projection(
        policy_binding=policy_binding,
        clusters=clusters,
        candidates_by_id=candidates_by_id,
        cluster_assessments=cluster_assessments_by_id,
    )
    if bundle["holdout_projection"] != expected_projection:
        _add(
            errors,
            "holdout_projection_replay_mismatch",
            "$.holdout_projection",
            "stored projection does not equal eligible representative recomputation",
        )
    expected_summary = _build_summary(
        candidates=candidates,
        clusters=clusters,
        candidate_assessments=expected_candidate_assessments,
        cluster_assessments=expected_cluster_assessments,
        holdout_projection=expected_projection,
    )
    if bundle["summary"] != expected_summary:
        _add(
            errors,
            "summary_replay_mismatch",
            "$.summary",
            "stored summary does not equal deterministic recomputation",
        )

    return tuple(
        sorted(errors, key=lambda item: (item["location"], item["code"], item["message"]))
    )


def validate_field_sample_intake(bundle: Mapping[str, Any]) -> dict[str, Any]:
    errors = field_sample_intake_errors(bundle)
    if errors:
        raise FieldSampleIntakeValidationError(errors)
    return copy.deepcopy(dict(bundle))


def _projection_policy_errors(
    bundle: Mapping[str, Any], policy: Mapping[str, Any]
) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    schema_failures = sorted(
        _policy_schema_validator().iter_errors(policy),
        key=lambda issue: list(issue.path),
    )
    for failure in schema_failures:
        location = _schema_location(failure.path)
        _add(
            errors,
            "projection_policy_schema_invalid",
            "$.policy" if location == "$" else f"$.policy{location[1:]}",
            failure.message,
        )
    if schema_failures:
        return errors
    policy_material = _without_digest(policy, "policy_digest")
    if policy["policy_digest"] != digest_value(policy_material):
        _add(
            errors,
            "projection_policy_digest_invalid",
            "$.policy.policy_digest",
            "provided field policy digest does not replay",
        )
    population = policy["target_population"]
    if population["population_digest"] != digest_value(
        _without_digest(population, "population_digest")
    ):
        _add(
            errors,
            "projection_population_digest_invalid",
            "$.policy.target_population.population_digest",
            "provided population digest does not replay",
        )
    binding = bundle["policy_binding"]
    expected = {
        "policy_id": policy["policy_id"],
        "policy_version": policy["version"],
        "policy_digest": policy["policy_digest"],
        "policy_status": policy["status"],
        "evidence_class": policy["evidence_class"],
        "population_id": population["population_id"],
        "intended_use_id": population["intended_use_id"],
        "population_digest": population["population_digest"],
        "stratification": _stratification_binding(policy),
    }
    for field, value in expected.items():
        if binding[field] != value:
            _add(
                errors,
                "projection_policy_binding_mismatch",
                f"$.policy_binding.{field}",
                field,
            )
    if bundle["holdout_projection"]["status"] != "ready":
        _add(
            errors,
            "holdout_projection_not_ready",
            "$.holdout_projection.status",
            bundle["holdout_projection"]["status"],
        )
    return errors


def project_holdout_field_cases(
    bundle: Mapping[str, Any],
    *,
    policy: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Return only ready cases after revalidating intake and exact policy binding."""

    errors = list(field_sample_intake_errors(bundle))
    if not errors:
        errors.extend(_projection_policy_errors(bundle, policy))
    if errors:
        raise FieldSampleIntakeValidationError(errors)
    return copy.deepcopy(list(bundle["holdout_projection"]["cases"]))


def field_sample_intake_evaluation_errors(
    intake: Mapping[str, Any],
    evaluation: Mapping[str, Any],
) -> tuple[dict[str, str], ...]:
    """Check that an existing field-evaluation/v0 bundle uses this projection."""

    errors = list(field_sample_intake_errors(intake))
    if errors:
        return tuple(errors)
    evaluation_failures = field_evaluation_errors(evaluation)
    if evaluation_failures:
        first = evaluation_failures[0]
        _add(
            errors,
            "field_evaluation_bundle_invalid",
            "$.evaluation",
            f"{first['code']} at {first['location']}",
        )
        return tuple(errors)
    projection = intake["holdout_projection"]
    if projection["status"] != "ready":
        _add(
            errors,
            "holdout_projection_not_ready",
            "$.intake.holdout_projection.status",
            projection["status"],
        )
        return tuple(errors)
    policy = evaluation["policy"]
    binding = intake["policy_binding"]
    for field, actual in (
        ("policy_id", policy["policy_id"]),
        ("policy_version", policy["version"]),
        ("policy_digest", policy["policy_digest"]),
        (
            "population_digest",
            policy["target_population"]["population_digest"],
        ),
    ):
        if binding[field] != actual:
            _add(
                errors,
                "intake_evaluation_policy_mismatch",
                f"$.evaluation.policy.{field}",
                field,
            )
    if evaluation["cases"] != projection["cases"]:
        _add(
            errors,
            "intake_evaluation_case_set_mismatch",
            "$.evaluation.cases",
            "evaluation cases differ from the intake projection",
        )
    projected_case_ids = {
        str(case["case_id"]) for case in projection["cases"]
    }
    evaluation_use_through = evaluation["holdout"]["labels_released_at"]
    for index, candidate in enumerate(intake["candidates"]):
        if str(candidate["field_case_id"]) not in projected_case_ids:
            continue
        valid_through = candidate["permission"]["valid_through"]
        if (
            valid_through is not None
            and _parse_time(valid_through) < _parse_time(evaluation_use_through)
        ):
            _add(
                errors,
                "permission_expired_before_evaluation_completion",
                f"$.intake.candidates.{index}.permission.valid_through",
                str(candidate["candidate_id"]),
            )
    if evaluation["holdout"]["case_set_digest"] != projection["case_set_digest"]:
        _add(
            errors,
            "intake_evaluation_case_set_digest_mismatch",
            "$.evaluation.holdout.case_set_digest",
            "evaluation holdout digest differs from the intake projection",
        )
    return tuple(
        sorted(errors, key=lambda item: (item["location"], item["code"], item["message"]))
    )


def validate_field_sample_intake_evaluation(
    intake: Mapping[str, Any],
    evaluation: Mapping[str, Any],
) -> dict[str, Any]:
    errors = field_sample_intake_evaluation_errors(intake, evaluation)
    if errors:
        raise FieldSampleIntakeValidationError(errors)
    return copy.deepcopy(dict(evaluation))


__all__ = [
    "PROSPECTIVE_MODES",
    "REQUIRED_DUPLICATE_METHODS",
    "REQUIRED_EXPOSURE_CONTEXTS",
    "SCHEMA_VERSION",
    "FieldSampleIntakeValidationError",
    "build_duplicate_cluster",
    "build_evaluation_permission",
    "build_exposure_declaration",
    "build_field_sample_intake",
    "build_function_unit_assessment",
    "build_intake_candidate",
    "build_privacy_review",
    "field_sample_intake_errors",
    "field_sample_intake_evaluation_errors",
    "project_holdout_field_cases",
    "validate_field_sample_intake",
    "validate_field_sample_intake_evaluation",
]
