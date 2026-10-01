"""Governed D7 field-performance evidence supplementary to field-evaluation/v0.

This module computes the seven required performance rates, checks tuning versus
holdout separation, records holdout access, and exposes temporal deterioration
material.  It deliberately cannot adopt thresholds, qualify field use, change
runtime routing, or make a final acceptance decision.
"""

from __future__ import annotations

import copy
from datetime import datetime, timedelta
from functools import lru_cache
import hashlib
import json
import math
from typing import Any, Iterable, Mapping, Sequence

from jsonschema import Draft202012Validator, FormatChecker

from .field_evaluation import wilson_interval
from .schema_access import schema_path


SCHEMA_VERSION = "field-performance-governance/v1"
REFERENCE_OUTCOMES = ("satisfied", "nonconforming", "unresolved")
OBSERVED_DISPOSITIONS = ("pass", "nonconformance", "unresolved", "abstain")
METRIC_NAMES = (
    "false_pass_rate",
    "false_nonconformance_rate",
    "unresolved_rate",
    "abstention_rate",
    "coverage",
    "authority_violation_rate",
    "traceability_loss_rate",
)
_THRESHOLD_DIRECTIONS = {
    "false_pass_rate": "max",
    "false_nonconformance_rate": "max",
    "unresolved_rate": "max",
    "abstention_rate": "max",
    "coverage": "min",
    "authority_violation_rate": "max",
    "traceability_loss_rate": "max",
}
_SCHEMA_PATH = schema_path("field-performance-governance.schema.json")
_AUTHORITY_BOUNDARY = {
    "semantic_guard_role": "compute_and_validate_audit_material_only",
    "threshold_adoption": False,
    "field_qualification": False,
    "runtime_cutover": False,
    "final_acceptance": False,
    "threshold_owner": "human",
    "cutover_owner": "external_control_plane_and_human",
    "final_acceptance_owner": "human",
}
_LIMITATIONS = (
    "The result is bounded to the declared population, risk classes, sealed holdout, access record coverage, temporal cohorts, and referenced route implementation.",
    "Content digests do not prove participant identity, access-log completeness, reviewer independence, clock integrity, or source authenticity.",
    "Supplied access records can show observed leakage but cannot prove the absence of unrecorded access without an external trusted access-log verifier.",
    "Cross-route output access is not classified as label leakage by this contract and requires a separately declared route-independence design.",
    "No metric, threshold result, or local validation grants field qualification, runtime cutover, or final human acceptance.",
)


class FieldPerformanceGovernanceError(ValueError):
    """A closed D7 evidence bundle failed schema or semantic replay."""

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


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def digest_value(value: Any) -> dict[str, str]:
    return {"algorithm": "sha256", "value": canonical_sha256(value)}


def digest_ref(ref_id: str, material: Any | None = None) -> dict[str, Any]:
    basis = {"ref_id": ref_id} if material is None else material
    return {"ref_id": ref_id, "digest": digest_value(basis)}


def versioned_ref(
    ref_id: str,
    version: str,
    material: Any | None = None,
) -> dict[str, Any]:
    basis = {"ref_id": ref_id, "version": version} if material is None else material
    return {"ref_id": ref_id, "version": version, "digest": digest_value(basis)}


def _without(value: Mapping[str, Any], *fields: str) -> dict[str, Any]:
    result = copy.deepcopy(dict(value))
    for field in fields:
        result.pop(field, None)
    return result


def _record_digest(value: Mapping[str, Any], field: str) -> dict[str, str]:
    return digest_value(_without(value, field))


def _sorted(values: Iterable[Mapping[str, Any]], *keys: str) -> list[dict[str, Any]]:
    return sorted(
        (copy.deepcopy(dict(item)) for item in values),
        key=lambda item: tuple(str(item.get(key, "")) for key in keys),
    )


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


@lru_cache(maxsize=1)
def _metric_definition_profile() -> dict[str, Any]:
    """Return the fixed candidate meanings used by this implementation."""

    definitions = [
        {
            "metric": "false_pass_rate",
            "direction": "lower_is_better",
            "numerator_definition": "observed pass where the reference outcome is nonconforming or unresolved",
            "denominator_definition": "all cases whose reference outcome is nonconforming or unresolved",
            "reference_unresolved_treatment": "included as unsafe to pass; this is a candidate safety convention, not an adopted universal definition",
            "observed_unresolved_treatment": "excluded from the numerator and counted by unresolved_rate",
            "abstention_treatment": "excluded from the numerator and counted by abstention_rate",
        },
        {
            "metric": "false_nonconformance_rate",
            "direction": "lower_is_better",
            "numerator_definition": "observed nonconformance where the reference outcome is satisfied",
            "denominator_definition": "all cases whose reference outcome is satisfied",
            "reference_unresolved_treatment": "excluded from the denominator",
            "observed_unresolved_treatment": "excluded from the numerator and counted by unresolved_rate",
            "abstention_treatment": "excluded from the numerator and counted by abstention_rate",
        },
        {
            "metric": "unresolved_rate",
            "direction": "lower_is_better",
            "numerator_definition": "all cases with observed disposition unresolved",
            "denominator_definition": "all evaluated cases",
            "reference_unresolved_treatment": "included in the denominator",
            "observed_unresolved_treatment": "included in the numerator",
            "abstention_treatment": "excluded from the numerator and counted by abstention_rate",
        },
        {
            "metric": "abstention_rate",
            "direction": "lower_is_better",
            "numerator_definition": "all cases with observed disposition abstain",
            "denominator_definition": "all evaluated cases",
            "reference_unresolved_treatment": "included in the denominator",
            "observed_unresolved_treatment": "excluded from the numerator and counted by unresolved_rate",
            "abstention_treatment": "included in the numerator",
        },
        {
            "metric": "coverage",
            "direction": "higher_is_better",
            "numerator_definition": "all cases whose observed disposition is not abstain",
            "denominator_definition": "all evaluated cases",
            "reference_unresolved_treatment": "included in the denominator",
            "observed_unresolved_treatment": "included as attempted coverage; coverage does not imply conclusive resolution",
            "abstention_treatment": "excluded from the numerator",
        },
        {
            "metric": "authority_violation_rate",
            "direction": "lower_is_better",
            "numerator_definition": "all cases whose supplied authority status is violation or unknown",
            "denominator_definition": "all evaluated cases",
            "reference_unresolved_treatment": "included in the denominator",
            "observed_unresolved_treatment": "included in the denominator",
            "abstention_treatment": "included in the denominator",
        },
        {
            "metric": "traceability_loss_rate",
            "direction": "lower_is_better",
            "numerator_definition": "all cases whose supplied traceability status is partial, lost, or unknown",
            "denominator_definition": "all evaluated cases",
            "reference_unresolved_treatment": "included in the denominator",
            "observed_unresolved_treatment": "included in the denominator",
            "abstention_treatment": "included in the denominator",
        },
    ]
    material = {
        "profile_id": "field-performance-metric-definitions",
        "profile_version": "candidate.v1",
        "adoption_status": "candidate",
        "formal_authority": "none",
        "definitions": definitions,
    }
    return {**material, "profile_digest": digest_value(material)}


def _metric_definition_ref() -> dict[str, Any]:
    profile = _metric_definition_profile()
    return {
        "ref_id": profile["profile_id"],
        "version": profile["profile_version"],
        "digest": copy.deepcopy(profile["profile_digest"]),
    }


def build_performance_policy(
    *,
    policy_id: str,
    version: str,
    reported_status: str,
    threshold_decision_ref: str | None,
    target_population: Mapping[str, Any],
    risk_classes: Iterable[Mapping[str, Any]],
    confidence_level: float,
    minimum_overall_sample: int,
    minimum_per_risk_class: int,
    review_period_days: int,
    reevaluation_triggers: Iterable[str],
) -> dict[str, Any]:
    """Build a human-owned policy without manufacturing a human decision."""

    if not math.isfinite(confidence_level) or not 0 < confidence_level < 1:
        raise ValueError("confidence_level must be finite and between zero and one")

    normalized_risks: list[dict[str, Any]] = []
    for risk_class in risk_classes:
        item = copy.deepcopy(dict(risk_class))
        numeric_values = [*item["costs"].values(), *item["thresholds"].values()]
        if any(
            value is not None
            and (not isinstance(value, (int, float)) or not math.isfinite(value))
            for value in numeric_values
        ):
            raise ValueError("risk costs and thresholds must be finite numbers or null")
        item["thresholds"] = {
            metric: item["thresholds"].get(metric) for metric in METRIC_NAMES
        }
        normalized_risks.append(item)
    material = {
        "policy_id": policy_id,
        "version": version,
        "owner_kind": "human",
        # This field records an externally supplied claim.  It is deliberately
        # not named ``status`` and never says ``adopted`` because this module
        # has no trusted decision resolver.
        "reported_status": reported_status,
        "threshold_decision_ref": threshold_decision_ref,
        "metric_definition_profile_ref": _metric_definition_ref(),
        "target_population": copy.deepcopy(dict(target_population)),
        "risk_classes": _sorted(normalized_risks, "risk_class_id"),
        "confidence_level": confidence_level,
        "minimum_overall_sample": minimum_overall_sample,
        "minimum_per_risk_class": minimum_per_risk_class,
        "review_period_days": review_period_days,
        "reevaluation_triggers": sorted(set(reevaluation_triggers)),
    }
    return {**material, "policy_digest": digest_value(material)}


def build_performance_case(
    *,
    case_id: str,
    subject_ref: str,
    subject_digest: Mapping[str, Any],
    risk_class_id: str,
    cohort_id: str,
    source_class: str,
    reference_outcome: str,
    observed_disposition: str,
    authority_status: str,
    traceability_status: str,
    evidence_refs: Iterable[str],
) -> dict[str, Any]:
    material = {
        "case_id": case_id,
        "subject_ref": subject_ref,
        "subject_digest": copy.deepcopy(dict(subject_digest)),
        "risk_class_id": risk_class_id,
        "cohort_id": cohort_id,
        "source_class": source_class,
        "reference_outcome": reference_outcome,
        "observed_disposition": observed_disposition,
        "authority_status": authority_status,
        "traceability_status": traceability_status,
        "evidence_refs": sorted(set(evidence_refs)),
    }
    return {**material, "case_digest": digest_value(material)}


def build_access_record(
    *,
    access_id: str,
    actor_ref: str,
    actor_role: str,
    material_ref: str,
    material_partition: str,
    material_kind: str,
    purpose: str,
    accessed_at: str,
    authorized: bool,
) -> dict[str, Any]:
    material = {
        "access_id": access_id,
        "actor_ref": actor_ref,
        "actor_role": actor_role,
        "material_ref": material_ref,
        "material_partition": material_partition,
        "material_kind": material_kind,
        "purpose": purpose,
        "accessed_at": accessed_at,
        "authorized": authorized,
    }
    return {**material, "access_digest": digest_value(material)}


def _rate(numerator: int, denominator: int, confidence: float) -> dict[str, Any]:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "value": None if denominator == 0 else round(numerator / denominator, 12),
        "wilson_interval": wilson_interval(numerator, denominator, confidence),
    }


def _metric_set(
    cases: Sequence[Mapping[str, Any]],
    confidence: float,
) -> dict[str, Any]:
    false_pass_denominator = sum(
        case["reference_outcome"] in {"nonconforming", "unresolved"} for case in cases
    )
    false_pass = sum(
        case["reference_outcome"] in {"nonconforming", "unresolved"}
        and case["observed_disposition"] == "pass"
        for case in cases
    )
    false_nonconformance_denominator = sum(
        case["reference_outcome"] == "satisfied" for case in cases
    )
    false_nonconformance = sum(
        case["reference_outcome"] == "satisfied"
        and case["observed_disposition"] == "nonconformance"
        for case in cases
    )
    unresolved = sum(case["observed_disposition"] == "unresolved" for case in cases)
    abstention = sum(case["observed_disposition"] == "abstain" for case in cases)
    coverage = len(cases) - abstention
    authority_violation = sum(
        case["authority_status"] != "within_authority" for case in cases
    )
    traceability_loss = sum(case["traceability_status"] != "complete" for case in cases)
    return {
        "case_count": len(cases),
        "rates": {
            "false_pass_rate": _rate(false_pass, false_pass_denominator, confidence),
            "false_nonconformance_rate": _rate(
                false_nonconformance,
                false_nonconformance_denominator,
                confidence,
            ),
            "unresolved_rate": _rate(unresolved, len(cases), confidence),
            "abstention_rate": _rate(abstention, len(cases), confidence),
            "coverage": _rate(coverage, len(cases), confidence),
            "authority_violation_rate": _rate(
                authority_violation, len(cases), confidence
            ),
            "traceability_loss_rate": _rate(traceability_loss, len(cases), confidence),
        },
    }


def _leaked_accesses(
    records: Sequence[Mapping[str, Any]],
    *,
    predictions_sealed_at: str,
) -> list[str]:
    sealed = _time(predictions_sealed_at)
    leaked: list[str] = []
    for record in records:
        prohibited_kind = record["material_kind"] in {
            "reference_label",
            "adjudication",
        }
        prohibited_role = record["actor_role"] in {
            "model_or_rule_developer",
            "evaluation_runtime",
        }
        prohibited_purpose = record["purpose"] in {"implementation", "tuning"}
        holdout = record["material_partition"] == "holdout"
        unauthorized = holdout and not bool(record["authorized"])
        premature_sensitive_access = (
            holdout
            and _time(str(record["accessed_at"])) < sealed
            and prohibited_kind
            and (prohibited_role or prohibited_purpose)
        )
        if unauthorized or premature_sensitive_access:
            leaked.append(str(record["access_id"]))
    return sorted(leaked)


def _threshold_results(
    *,
    policy: Mapping[str, Any],
    risk_metrics: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    policy_by_risk = {
        str(item["risk_class_id"]): item for item in policy["risk_classes"]
    }
    results: list[dict[str, Any]] = []
    for metric_group in risk_metrics:
        risk_id = str(metric_group["risk_class_id"])
        thresholds = policy_by_risk[risk_id]["thresholds"]
        for metric in METRIC_NAMES:
            threshold = thresholds[metric]
            rate = metric_group["metric_set"]["rates"][metric]
            direction = _THRESHOLD_DIRECTIONS[metric]
            comparison_basis = "wilson_lower" if direction == "min" else "wilson_upper"
            comparison_value = rate["wilson_interval"][
                "lower" if direction == "min" else "upper"
            ]
            candidate_comparison_outcome = "not_computable"
            if threshold is not None and comparison_value is not None:
                within_claimed_threshold = (
                    comparison_value >= threshold
                    if direction == "min"
                    else comparison_value <= threshold
                )
                candidate_comparison_outcome = (
                    "within_claimed_threshold"
                    if within_claimed_threshold
                    else "outside_claimed_threshold"
                )
            results.append(
                {
                    "risk_class_id": risk_id,
                    "metric": metric,
                    "operator": ">=" if direction == "min" else "<=",
                    "point_estimate": rate["value"],
                    "comparison_value": comparison_value,
                    "comparison_basis": comparison_basis,
                    "threshold": threshold,
                    "candidate_comparison_outcome": candidate_comparison_outcome,
                }
            )
    return results


def _temporal_assessment(
    *,
    cases: Sequence[Mapping[str, Any]],
    cohorts: Sequence[Mapping[str, Any]],
    risk_ids: Sequence[str],
    confidence: float,
) -> dict[str, Any]:
    ordered = sorted(cohorts, key=lambda item: _time(str(item["observed_from"])))
    comparisons: list[dict[str, Any]] = []
    for left, right in zip(ordered, ordered[1:]):
        for risk_id in sorted(risk_ids):
            left_set = _metric_set(
                [
                    case
                    for case in cases
                    if case["cohort_id"] == left["cohort_id"]
                    and case["risk_class_id"] == risk_id
                ],
                confidence,
            )
            right_set = _metric_set(
                [
                    case
                    for case in cases
                    if case["cohort_id"] == right["cohort_id"]
                    and case["risk_class_id"] == risk_id
                ],
                confidence,
            )
            for metric in METRIC_NAMES:
                left_rate = left_set["rates"][metric]
                right_rate = right_set["rates"][metric]
                from_value = left_rate["value"]
                to_value = right_rate["value"]
                comparable = from_value is not None and to_value is not None
                direction = (
                    "decrease_is_degradation"
                    if _THRESHOLD_DIRECTIONS[metric] == "min"
                    else "increase_is_degradation"
                )
                degraded = False
                if comparable:
                    degraded = bool(
                        to_value < from_value
                        if direction == "decrease_is_degradation"
                        else to_value > from_value
                    )
                comparison_id = (
                    f"temporal.{left['cohort_id']}.{right['cohort_id']}."
                    f"{risk_id}.{metric}"
                )
                comparisons.append(
                    {
                        "comparison_id": comparison_id,
                        "from_cohort_id": left["cohort_id"],
                        "to_cohort_id": right["cohort_id"],
                        "risk_class_id": risk_id,
                        "metric": metric,
                        "direction": direction,
                        "comparison_basis": "point_estimate_candidate_direction_only",
                        "from_case_count": left_set["case_count"],
                        "to_case_count": right_set["case_count"],
                        "from_denominator": left_rate["denominator"],
                        "to_denominator": right_rate["denominator"],
                        "from_value": from_value,
                        "to_value": to_value,
                        "from_interval": copy.deepcopy(left_rate["wilson_interval"]),
                        "to_interval": copy.deepcopy(right_rate["wilson_interval"]),
                        "comparable": comparable,
                        "degradation_observed": degraded,
                    }
                )
    if not comparisons:
        status = "not_assessed"
    elif all(item["comparable"] for item in comparisons):
        status = "assessed"
    else:
        status = "partially_assessed"
    degraded_refs = sorted(
        str(item["comparison_id"])
        for item in comparisons
        if item["degradation_observed"]
    )
    return {
        "status": status,
        "comparison_scope": "adjacent_cohort_by_risk_class_all_seven_metrics",
        "comparisons": comparisons,
        "directional_degradation_observed": bool(degraded_refs),
        "degraded_comparison_refs": degraded_refs,
        "reevaluation_required": status != "assessed" or bool(degraded_refs),
        "thresholded_degradation_claim": "not_established_candidate_direction_only",
    }


def _metrics(
    *,
    policy: Mapping[str, Any],
    cases: Sequence[Mapping[str, Any]],
    cohorts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    confidence = float(policy["confidence_level"])
    risk_ids = [str(item["risk_class_id"]) for item in policy["risk_classes"]]
    overall = _metric_set(cases, confidence)
    risk_metrics = [
        {
            "risk_class_id": risk_id,
            "metric_set": _metric_set(
                [case for case in cases if case["risk_class_id"] == risk_id],
                confidence,
            ),
        }
        for risk_id in sorted(risk_ids)
    ]
    ordered_cohorts = sorted(
        cohorts,
        key=lambda item: _time(str(item["observed_from"])),
    )
    cohort_metrics = [
        {
            "cohort_id": cohort["cohort_id"],
            "observed_from": cohort["observed_from"],
            "observed_until": cohort["observed_until"],
            "metric_set": _metric_set(
                [case for case in cases if case["cohort_id"] == cohort["cohort_id"]],
                confidence,
            ),
        }
        for cohort in ordered_cohorts
    ]
    material = {
        "overall": overall,
        "by_risk_class": risk_metrics,
        "by_temporal_cohort": cohort_metrics,
        "threshold_results": _threshold_results(
            policy=policy,
            risk_metrics=risk_metrics,
        ),
        "temporal_assessment": _temporal_assessment(
            cases=cases,
            cohorts=ordered_cohorts,
            risk_ids=risk_ids,
            confidence=confidence,
        ),
    }
    return {**material, "metrics_digest": digest_value(material)}


def _evaluation_material_digest(
    *,
    evaluation_id: str,
    base_field_evaluation_ref: Mapping[str, Any],
    route_implementation_ref: Mapping[str, Any],
    metric_definition_profile: Mapping[str, Any],
    dataset_partition: Mapping[str, Any],
    access_records: Sequence[Mapping[str, Any]],
    cohorts: Sequence[Mapping[str, Any]],
    cases: Sequence[Mapping[str, Any]],
    metrics: Mapping[str, Any],
    evaluation_as_of: str,
) -> dict[str, str]:
    observations = {
        key: copy.deepcopy(metrics[key])
        for key in (
            "overall",
            "by_risk_class",
            "by_temporal_cohort",
            "temporal_assessment",
        )
    }
    return digest_value(
        {
            "evaluation_id": evaluation_id,
            "base_field_evaluation_ref": copy.deepcopy(dict(base_field_evaluation_ref)),
            "route_implementation_ref": copy.deepcopy(dict(route_implementation_ref)),
            "metric_definition_profile": copy.deepcopy(dict(metric_definition_profile)),
            "dataset_partition": copy.deepcopy(dict(dataset_partition)),
            "access_records": copy.deepcopy(list(access_records)),
            "cohorts": copy.deepcopy(list(cohorts)),
            "cases": copy.deepcopy(list(cases)),
            "metric_observations": observations,
            "evaluation_as_of": evaluation_as_of,
        }
    )


def _matching_threshold_decision_record(
    policy: Mapping[str, Any],
    decisions: Sequence[Mapping[str, Any]],
) -> Mapping[str, Any] | None:
    decision_ref = policy["threshold_decision_ref"]
    if not decision_ref:
        return None
    matching = [item for item in decisions if item["decision_id"] == decision_ref]
    if not (
        len(matching) == 1
        and matching[0]["decision_type"] == "adopt_thresholds"
        and matching[0]["policy_id"] == policy["policy_id"]
        and matching[0]["policy_version"] == policy["version"]
        and matching[0]["policy_digest"] == policy["policy_digest"]
        and matching[0]["trusted_entry_ref"]
        and matching[0]["authenticity_evidence_ref"]
    ):
        return None
    return matching[0]


def _matching_threshold_decision(
    policy: Mapping[str, Any],
    decisions: Sequence[Mapping[str, Any]],
) -> bool:
    return _matching_threshold_decision_record(policy, decisions) is not None


def _threshold_evaluation_binding_matches(
    *,
    decision: Mapping[str, Any],
    evaluation_id: str,
    evaluation_material_digest: Mapping[str, Any],
    metric_definition_profile_ref: Mapping[str, Any],
    route_implementation_ref: Mapping[str, Any],
    evaluation_as_of: str,
) -> bool:
    binding = decision.get("evaluation_binding")
    if not isinstance(binding, Mapping):
        return False
    expected = {
        "evaluation_id": evaluation_id,
        "evaluation_material_digest": copy.deepcopy(dict(evaluation_material_digest)),
        "metric_definition_profile_ref": copy.deepcopy(
            dict(metric_definition_profile_ref)
        ),
        "route_implementation_ref": copy.deepcopy(dict(route_implementation_ref)),
        "evaluation_completed_at": evaluation_as_of,
    }
    if dict(binding) != expected:
        return False
    return _time(str(decision["recorded_at"])) >= _time(evaluation_as_of)


def _unresolved_record(
    *,
    unresolved_id: str,
    uncertainty_kind: str,
    owner: str,
    next_action: str,
    resolution_condition: str,
    review_at: str,
    retirement_condition: str,
    evidence_refs: Iterable[str],
) -> dict[str, Any]:
    return {
        "unresolved_id": unresolved_id,
        "uncertainty_kind": uncertainty_kind,
        "owner": owner,
        "needed_for": "field_qualification",
        "blocking_status": "blocking_field_qualification",
        "next_action": next_action,
        "resolution_condition": resolution_condition,
        "review_at": review_at,
        "fallback": "retain_candidate_only_and_formal_authority_none",
        "retirement_condition": retirement_condition,
        "evidence_refs": sorted(set(evidence_refs)),
    }


def _assessment(
    *,
    evaluation_id: str,
    policy: Mapping[str, Any],
    decisions: Sequence[Mapping[str, Any]],
    base_field_evaluation_ref: Mapping[str, Any],
    route_implementation_ref: Mapping[str, Any],
    evaluation_material_digest: Mapping[str, Any],
    cases: Sequence[Mapping[str, Any]],
    access_log_coverage: str,
    leaked_access_refs: Sequence[str],
    metrics: Mapping[str, Any],
    evaluation_as_of: str,
    review_due_at: str,
) -> dict[str, Any]:
    unresolved: list[dict[str, Any]] = []

    def add(
        unresolved_id: str,
        uncertainty_kind: str,
        owner: str,
        next_action: str,
        resolution_condition: str,
        *,
        evidence_refs: Iterable[str] = (),
        review_at: str = review_due_at,
        retirement_condition: str = "superseded by a resolved field-performance evaluation",
    ) -> None:
        unresolved.append(
            _unresolved_record(
                unresolved_id=unresolved_id,
                uncertainty_kind=uncertainty_kind,
                owner=owner,
                next_action=next_action,
                resolution_condition=resolution_condition,
                review_at=review_at,
                retirement_condition=retirement_condition,
                evidence_refs=evidence_refs,
            )
        )

    add(
        "input_references_not_runtime_resolved",
        "external_reference_resolution",
        "external_control_plane",
        "resolve the base field evaluation and route implementation by exact version and digest",
        "both references resolve to validated current artifacts and their governed provenance",
        evidence_refs=(
            str(base_field_evaluation_ref["ref_id"]),
            str(route_implementation_ref["ref_id"]),
        ),
    )
    add(
        "case_assertions_not_governed_source_derived",
        "case_evidence_provenance",
        "evaluation_owner",
        "derive labels, source class, risk class, authority, and traceability from governed source records",
        "every case assertion is replayed from content-addressed H1, H2, label, and occurrence evidence",
        evidence_refs=(evaluation_id,),
    )
    add(
        "runtime_currency_not_evaluated",
        "evaluation_currency",
        "external_control_plane",
        "compare review_due_at with a trusted runtime clock and reevaluation triggers",
        "a trusted current-time observation establishes current or overdue state",
        evidence_refs=(evaluation_id,),
    )

    policy_status = str(policy["reported_status"])
    if policy_status == "pending":
        threshold_adoption_state = "pending_human_decision"
        add(
            "thresholds_pending_human_decision",
            "threshold_adoption",
            "human",
            "review the completed evaluation material and decide whether to adopt numeric thresholds",
            "an externally authenticated human decision binds the policy and completed evaluation material",
            evidence_refs=(str(policy["policy_id"]),),
        )
    elif policy_status == "retired":
        threshold_adoption_state = "claimed_retired_unverified"
        add(
            "threshold_policy_retired_claim_unverified",
            "threshold_retirement",
            "external_control_plane",
            "resolve the retirement decision and its effective scope",
            "an externally authenticated retirement record matches the policy version and digest",
            evidence_refs=(str(policy["policy_id"]),),
        )
    else:  # adoption_claimed
        threshold_adoption_state = "claimed_adopted_unverified"
        decision = _matching_threshold_decision_record(policy, decisions)
        if decision is None:
            add(
                "threshold_decision_missing_or_mismatched",
                "threshold_adoption",
                "human",
                "provide an exact external threshold-adoption decision",
                "one decision matches the policy identifier, version, and digest",
                evidence_refs=(str(policy["policy_id"]),),
            )
        else:
            add(
                "threshold_decision_external_authenticity_unverified",
                "decision_authenticity",
                "external_control_plane",
                "authenticate the human actor, trusted entrypoint, and decision evidence",
                "the external trust domain verifies the decision and its current validity",
                evidence_refs=(str(decision["decision_id"]),),
            )
        if decision is None or not _threshold_evaluation_binding_matches(
            decision=decision,
            evaluation_id=evaluation_id,
            evaluation_material_digest=evaluation_material_digest,
            metric_definition_profile_ref=policy["metric_definition_profile_ref"],
            route_implementation_ref=route_implementation_ref,
            evaluation_as_of=evaluation_as_of,
        ):
            add(
                "threshold_decision_evaluation_binding_unverified",
                "decision_subject_binding",
                "human",
                "bind the decision to the completed evaluation material, candidate metric definition, route implementation, and completion time",
                "the external decision contains an exact evaluation binding and is recorded no earlier than evaluation completion",
                evidence_refs=(evaluation_id, str(policy["policy_id"])),
            )

    if len(cases) < int(policy["minimum_overall_sample"]):
        add(
            "overall_sample_insufficient",
            "sample_sufficiency",
            "evaluation_owner",
            "collect additional independent field cases",
            "the independent overall sample reaches the human-owned minimum",
            evidence_refs=(evaluation_id,),
        )
    for risk_class in policy["risk_classes"]:
        risk_id = risk_class["risk_class_id"]
        if sum(case["risk_class_id"] == risk_id for case in cases) < int(
            policy["minimum_per_risk_class"]
        ):
            add(
                f"risk_class_sample_insufficient:{risk_id}",
                "risk_class_sample_sufficiency",
                "evaluation_owner",
                f"collect additional independent field cases for {risk_id}",
                "the risk-class sample reaches the human-owned minimum",
                evidence_refs=(str(risk_id),),
            )
    if access_log_coverage != "claimed_complete":
        add(
            "access_log_coverage_not_complete",
            "access_log_coverage",
            "data_custodian",
            "complete the declared access-event inventory",
            "the supplied inventory declares complete coverage for its sealed scope",
            evidence_refs=(evaluation_id,),
        )
    else:
        add(
            "access_log_completeness_externally_unverified",
            "access_log_authenticity",
            "external_control_plane",
            "verify the access-log collector, scope, interval, and source authenticity",
            "an external trusted verifier confirms access-log completeness",
            evidence_refs=(evaluation_id,),
        )
    if leaked_access_refs:
        add(
            "holdout_leakage_detected",
            "holdout_leakage",
            "evaluation_owner",
            "retire the contaminated holdout and create a new independent sealed holdout",
            "a new evaluation uses uncontaminated material with no detected prohibited access",
            evidence_refs=leaked_access_refs,
            review_at=evaluation_as_of,
        )
    if any(case["source_class"] != "field_sample" for case in cases):
        add(
            "non_field_material_present",
            "population_material_class",
            "evaluation_owner",
            "remove non-field material from the field-performance denominator",
            "every measured case has externally verified field provenance",
            evidence_refs=(evaluation_id,),
        )
    temporal = metrics["temporal_assessment"]
    if temporal["status"] == "not_assessed":
        add(
            "temporal_degradation_not_assessed",
            "temporal_performance",
            "evaluation_owner",
            "collect at least two comparable temporal cohorts for every required risk class and metric",
            "adjacent risk-class comparisons cover all seven metrics",
            evidence_refs=(evaluation_id,),
        )
    elif temporal["status"] == "partially_assessed":
        noncomparable = [
            str(item["comparison_id"])
            for item in temporal["comparisons"]
            if not item["comparable"]
        ]
        add(
            "temporal_degradation_partially_assessed",
            "temporal_performance",
            "evaluation_owner",
            "supply sufficient denominators for every adjacent risk-class metric comparison",
            "all required temporal comparisons have non-zero applicable denominators",
            evidence_refs=noncomparable,
        )
    if temporal["directional_degradation_observed"]:
        add(
            "temporal_degradation_observed",
            "temporal_deterioration",
            "evaluation_owner",
            "investigate the degraded metrics and run a newly sealed evaluation",
            "a subsequent evaluation resolves or bounds each degraded comparison",
            evidence_refs=temporal["degraded_comparison_refs"],
            review_at=evaluation_as_of,
        )
    threshold_results = metrics["threshold_results"]
    if policy_status != "retired" and any(
        item["candidate_comparison_outcome"] == "outside_claimed_threshold"
        for item in threshold_results
    ):
        add(
            "claimed_threshold_outside_bound",
            "threshold_nonconformance",
            "evaluation_owner",
            "investigate comparisons outside claimed thresholds and produce a new evaluation",
            "every claimed threshold comparison is within the required confidence bound",
            evidence_refs=(evaluation_id,),
        )
    if policy_status != "retired" and any(
        item["candidate_comparison_outcome"] == "not_computable"
        for item in threshold_results
    ):
        add(
            "threshold_assessment_pending",
            "threshold_assessment",
            "human",
            "adopt thresholds only after reviewing the completed evaluation material",
            "every required metric has a claimed threshold and an applicable denominator",
            evidence_refs=(str(policy["policy_id"]),),
        )
    unresolved = sorted(unresolved, key=lambda item: str(item["unresolved_id"]))
    return {
        "calculation_replay_state": "replayed",
        "input_resolution_state": "unresolved_external_bindings",
        "evidence_sufficiency_state": "insufficient",
        "currency_state": "review_schedule_bound_runtime_clock_unresolved",
        "threshold_adoption_state": threshold_adoption_state,
        "qualification_state": "not_established",
        "formal_authority": "none",
        "reasons": [str(item["unresolved_id"]) for item in unresolved],
        "unresolved_records": unresolved,
        "not_inferred": [
            "runtime_cutover",
            "engineering_correctness",
            "operational_qualification",
            "human_acceptance",
        ],
    }


def build_field_performance_bundle(
    *,
    evaluation_id: str,
    policy: Mapping[str, Any],
    human_decision_records: Iterable[Mapping[str, Any]],
    base_field_evaluation_ref: Mapping[str, Any],
    route_implementation_ref: Mapping[str, Any],
    tuning_refs: Iterable[Mapping[str, Any]],
    holdout_refs: Iterable[Mapping[str, Any]],
    holdout_sealed_at: str,
    predictions_sealed_at: str,
    labels_released_at: str,
    access_log_coverage: str,
    access_records: Iterable[Mapping[str, Any]],
    cohorts: Iterable[Mapping[str, Any]],
    cases: Iterable[Mapping[str, Any]],
    evaluation_as_of: str,
    review_due_at: str,
    limitations: Iterable[str] = (),
) -> dict[str, Any]:
    normalized_cases = _sorted(cases, "case_id")
    normalized_cohorts = _sorted(cohorts, "observed_from", "cohort_id")
    normalized_access = _sorted(access_records, "accessed_at", "access_id")
    normalized_decisions = _sorted(human_decision_records, "decision_id")
    tuning = _sorted(tuning_refs, "ref_id")
    holdout = _sorted(holdout_refs, "ref_id")
    partition_material = {
        "tuning_refs": tuning,
        "holdout_refs": holdout,
        "holdout_sealed_at": holdout_sealed_at,
        "predictions_sealed_at": predictions_sealed_at,
        "labels_released_at": labels_released_at,
        "access_log_coverage": access_log_coverage,
    }
    dataset_partition = {
        **partition_material,
        "partition_digest": digest_value(partition_material),
    }
    leaked_access_refs = _leaked_accesses(
        normalized_access,
        predictions_sealed_at=predictions_sealed_at,
    )
    tuning_ids = {str(item["ref_id"]) for item in tuning}
    holdout_ids = {str(item["ref_id"]) for item in holdout}
    tuning_digests = {str(item["digest"]["value"]) for item in tuning}
    holdout_digests = {str(item["digest"]["value"]) for item in holdout}
    split_overlap_refs = sorted(tuning_ids & holdout_ids) + [
        f"sha256:{value}" for value in sorted(tuning_digests & holdout_digests)
    ]
    metrics = _metrics(
        policy=policy,
        cases=normalized_cases,
        cohorts=normalized_cohorts,
    )
    metric_definition_profile = _metric_definition_profile()
    evaluation_material_digest = _evaluation_material_digest(
        evaluation_id=evaluation_id,
        base_field_evaluation_ref=base_field_evaluation_ref,
        route_implementation_ref=route_implementation_ref,
        metric_definition_profile=metric_definition_profile,
        dataset_partition=dataset_partition,
        access_records=normalized_access,
        cohorts=normalized_cohorts,
        cases=normalized_cases,
        metrics=metrics,
        evaluation_as_of=evaluation_as_of,
    )
    assessment = _assessment(
        evaluation_id=evaluation_id,
        policy=policy,
        decisions=normalized_decisions,
        base_field_evaluation_ref=base_field_evaluation_ref,
        route_implementation_ref=route_implementation_ref,
        evaluation_material_digest=evaluation_material_digest,
        cases=normalized_cases,
        access_log_coverage=access_log_coverage,
        leaked_access_refs=leaked_access_refs,
        metrics=metrics,
        evaluation_as_of=evaluation_as_of,
        review_due_at=review_due_at,
    )
    material = {
        "schema_version": SCHEMA_VERSION,
        "evaluation_id": evaluation_id,
        "policy": copy.deepcopy(dict(policy)),
        "human_decision_records": normalized_decisions,
        "base_field_evaluation_ref": copy.deepcopy(dict(base_field_evaluation_ref)),
        "route_implementation_ref": copy.deepcopy(dict(route_implementation_ref)),
        "metric_definition_profile": copy.deepcopy(metric_definition_profile),
        "evaluation_material_digest": evaluation_material_digest,
        "dataset_partition": dataset_partition,
        "access_records": normalized_access,
        "dataset_diagnostics": {
            "split_overlap_refs": split_overlap_refs,
            "leakage_status": (
                "unknown"
                if access_log_coverage != "claimed_complete"
                else "detected"
                if leaked_access_refs
                else "not_observed_in_supplied_records"
            ),
            "leaked_access_refs": leaked_access_refs,
        },
        "cohorts": normalized_cohorts,
        "cases": normalized_cases,
        "metrics": metrics,
        "evaluation_as_of": evaluation_as_of,
        "review_due_at": review_due_at,
        "assessment": assessment,
        "authority_boundary": copy.deepcopy(_AUTHORITY_BOUNDARY),
        "limitations": sorted(set((*_LIMITATIONS, *limitations))),
    }
    bundle = {**material, "bundle_digest": digest_value(material)}
    # Builders must not emit a known-invalid sealed record and leave callers
    # to discover that only if they remember a second API call.
    return validate_field_performance(bundle)


@lru_cache(maxsize=1)
def _validator() -> Draft202012Validator:
    with _SCHEMA_PATH.open("r", encoding="utf-8") as handle:
        schema = json.load(handle)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _add(
    errors: list[dict[str, str]],
    code: str,
    location: str,
    message: str,
) -> None:
    errors.append({"code": code, "location": location, "message": message})


def _non_finite_locations(value: Any, location: str = "$") -> list[str]:
    if isinstance(value, float) and not math.isfinite(value):
        return [location]
    if isinstance(value, Mapping):
        result: list[str] = []
        for key, item in value.items():
            result.extend(_non_finite_locations(item, f"{location}.{key}"))
        return result
    if isinstance(value, (list, tuple)):
        result = []
        for index, item in enumerate(value):
            result.extend(_non_finite_locations(item, f"{location}[{index}]"))
        return result
    return []


def field_performance_errors(bundle: Mapping[str, Any]) -> tuple[dict[str, str], ...]:
    errors: list[dict[str, str]] = []
    for location in _non_finite_locations(bundle):
        _add(
            errors,
            "non_finite_number",
            location,
            "NaN and infinity are not valid canonical JSON numbers",
        )
    if errors:
        return tuple(errors)
    for error in sorted(
        _validator().iter_errors(bundle), key=lambda item: list(item.path)
    ):
        location = "$" + "".join(
            f"[{item}]" if isinstance(item, int) else f".{item}" for item in error.path
        )
        _add(errors, "schema_error", location, error.message)
    if errors:
        return tuple(errors)

    policy = bundle["policy"]
    expected_metric_profile = _metric_definition_profile()
    if bundle["metric_definition_profile"] != expected_metric_profile:
        _add(
            errors,
            "metric_definition_profile_mismatch",
            "$.metric_definition_profile",
            "candidate metric definitions do not match this implementation version",
        )
    if policy["metric_definition_profile_ref"] != _metric_definition_ref():
        _add(
            errors,
            "policy_metric_definition_ref_mismatch",
            "$.policy.metric_definition_profile_ref",
            "policy does not bind the candidate metric-definition profile",
        )
    if policy["policy_digest"] != _record_digest(policy, "policy_digest"):
        _add(
            errors,
            "policy_digest_mismatch",
            "$.policy.policy_digest",
            "policy digest does not replay",
        )
    population = policy["target_population"]
    if population["population_digest"] != _record_digest(
        population, "population_digest"
    ):
        _add(
            errors,
            "population_digest_mismatch",
            "$.policy.target_population.population_digest",
            "population digest does not replay",
        )
    decisions = bundle["human_decision_records"]
    for index, decision in enumerate(decisions):
        if decision["decision_digest"] != _record_digest(decision, "decision_digest"):
            _add(
                errors,
                "decision_digest_mismatch",
                f"$.human_decision_records[{index}]",
                "decision digest does not replay",
            )
    for index, case in enumerate(bundle["cases"]):
        if case["case_digest"] != _record_digest(case, "case_digest"):
            _add(
                errors,
                "case_digest_mismatch",
                f"$.cases[{index}]",
                "case digest does not replay",
            )
    for index, access in enumerate(bundle["access_records"]):
        if access["access_digest"] != _record_digest(access, "access_digest"):
            _add(
                errors,
                "access_digest_mismatch",
                f"$.access_records[{index}]",
                "access digest does not replay",
            )
    access_ids = [str(item["access_id"]) for item in bundle["access_records"]]
    if len(access_ids) != len(set(access_ids)):
        _add(
            errors,
            "duplicate_access_record",
            "$.access_records",
            "access identifiers must be unique",
        )
    partition = bundle["dataset_partition"]
    if partition["partition_digest"] != _record_digest(partition, "partition_digest"):
        _add(
            errors,
            "partition_digest_mismatch",
            "$.dataset_partition",
            "partition digest does not replay",
        )

    risk_ids = [str(item["risk_class_id"]) for item in policy["risk_classes"]]
    if len(risk_ids) != len(set(risk_ids)):
        _add(
            errors,
            "duplicate_risk_class",
            "$.policy.risk_classes",
            "risk class identifiers must be unique",
        )
    for risk in policy["risk_classes"]:
        costs = risk["costs"]
        false_pass_cost = costs["false_pass_cost"]
        other_costs = [
            value for key, value in costs.items() if key != "false_pass_cost"
        ]
        if not all(false_pass_cost > value for value in other_costs):
            _add(
                errors,
                "false_pass_not_most_costly",
                "$.policy.risk_classes",
                "false-pass cost must exceed every other declared cost",
            )
        thresholds = risk["thresholds"]
        if policy["reported_status"] == "pending" and any(
            value is not None for value in thresholds.values()
        ):
            _add(
                errors,
                "pending_policy_has_threshold",
                "$.policy.risk_classes",
                "pending policy thresholds must remain null",
            )
        if policy["reported_status"] == "adoption_claimed" and any(
            value is None for value in thresholds.values()
        ):
            _add(
                errors,
                "adoption_claim_missing_threshold",
                "$.policy.risk_classes",
                "an adoption claim requires every threshold",
            )
    if (
        policy["reported_status"] == "pending"
        and policy["threshold_decision_ref"] is not None
    ):
        _add(
            errors,
            "pending_policy_has_decision_ref",
            "$.policy.threshold_decision_ref",
            "pending policy cannot bind an adoption decision",
        )
    if policy[
        "reported_status"
    ] == "adoption_claimed" and not _matching_threshold_decision(policy, decisions):
        _add(
            errors,
            "threshold_decision_mismatch",
            "$.human_decision_records",
            "claimed threshold adoption requires an exact human decision binding",
        )

    tuning_ids = {str(item["ref_id"]) for item in partition["tuning_refs"]}
    holdout_ids = {str(item["ref_id"]) for item in partition["holdout_refs"]}
    tuning_digests = {str(item["digest"]["value"]) for item in partition["tuning_refs"]}
    holdout_digests = {
        str(item["digest"]["value"]) for item in partition["holdout_refs"]
    }
    overlap = sorted(tuning_ids & holdout_ids) + [
        f"sha256:{value}" for value in sorted(tuning_digests & holdout_digests)
    ]
    if overlap:
        _add(
            errors,
            "tuning_holdout_overlap",
            "$.dataset_partition",
            f"tuning and holdout overlap: {overlap}",
        )
    if not (
        _time(partition["holdout_sealed_at"])
        <= _time(partition["predictions_sealed_at"])
        <= _time(partition["labels_released_at"])
    ):
        _add(
            errors,
            "holdout_temporal_order_invalid",
            "$.dataset_partition",
            "expected sealed <= predictions <= labels released",
        )
    if _time(partition["labels_released_at"]) > _time(bundle["evaluation_as_of"]):
        _add(
            errors,
            "evaluation_before_label_release",
            "$.evaluation_as_of",
            "evaluation_as_of cannot precede release of the sealed reference labels",
        )
    if _time(bundle["evaluation_as_of"]) > _time(bundle["review_due_at"]):
        _add(
            errors,
            "review_due_before_evaluation",
            "$.review_due_at",
            "review_due_at cannot precede evaluation_as_of",
        )
    expected_review_due = _time(bundle["evaluation_as_of"]) + timedelta(
        days=int(policy["review_period_days"])
    )
    if _time(bundle["review_due_at"]) != expected_review_due:
        _add(
            errors,
            "review_due_policy_mismatch",
            "$.review_due_at",
            "review_due_at must equal evaluation_as_of plus policy.review_period_days",
        )

    case_ids = [str(item["case_id"]) for item in bundle["cases"]]
    if len(case_ids) != len(set(case_ids)):
        _add(errors, "duplicate_case", "$.cases", "case identifiers must be unique")
    sampling_units = [
        (str(item["subject_ref"]), str(item["subject_digest"]["value"]))
        for item in bundle["cases"]
    ]
    if len(sampling_units) != len(set(sampling_units)):
        _add(
            errors,
            "duplicate_sampling_unit",
            "$.cases",
            "one subject snapshot cannot be counted as more than one field case",
        )
    if set(case_ids) != holdout_ids:
        _add(
            errors,
            "holdout_case_coverage_mismatch",
            "$.cases",
            "case identifiers must exactly match holdout references",
        )
    holdout_by_id = {str(item["ref_id"]): item for item in partition["holdout_refs"]}
    for case in bundle["cases"]:
        holdout_ref = holdout_by_id.get(str(case["case_id"]))
        if holdout_ref is not None and holdout_ref["digest"] != case["subject_digest"]:
            _add(
                errors,
                "holdout_case_digest_mismatch",
                "$.dataset_partition.holdout_refs",
                f"holdout digest does not bind subject snapshot for {case['case_id']}",
            )
    cohort_ids = [str(item["cohort_id"]) for item in bundle["cohorts"]]
    if len(cohort_ids) != len(set(cohort_ids)):
        _add(
            errors, "duplicate_cohort", "$.cohorts", "cohort identifiers must be unique"
        )
    observed_case_refs: list[str] = []
    ordered_cohorts = sorted(
        bundle["cohorts"], key=lambda item: _time(str(item["observed_from"]))
    )
    for index, cohort in enumerate(ordered_cohorts):
        if cohort["cohort_digest"] != _record_digest(cohort, "cohort_digest"):
            _add(
                errors,
                "cohort_digest_mismatch",
                f"$.cohorts[{index}]",
                "cohort digest does not replay",
            )
        if _time(cohort["observed_from"]) >= _time(cohort["observed_until"]):
            _add(
                errors,
                "cohort_interval_invalid",
                "$.cohorts",
                "cohort start must precede its end",
            )
        if _time(cohort["observed_until"]) > _time(bundle["evaluation_as_of"]):
            _add(
                errors,
                "future_cohort",
                "$.cohorts",
                "cohort cannot end after evaluation_as_of",
            )
        observed_case_refs.extend(str(item) for item in cohort["case_refs"])
    for left, right in zip(ordered_cohorts, ordered_cohorts[1:]):
        if _time(left["observed_until"]) > _time(right["observed_from"]):
            _add(
                errors,
                "cohort_intervals_overlap",
                "$.cohorts",
                "temporal cohorts must not overlap",
            )
    if sorted(observed_case_refs) != sorted(case_ids) or len(observed_case_refs) != len(
        set(observed_case_refs)
    ):
        _add(
            errors,
            "cohort_case_coverage_mismatch",
            "$.cohorts",
            "cohorts must partition every case exactly once",
        )
    cases_by_id = {str(item["case_id"]): item for item in bundle["cases"]}
    for cohort in bundle["cohorts"]:
        for case_ref in cohort["case_refs"]:
            if (
                str(case_ref) in cases_by_id
                and cases_by_id[str(case_ref)]["cohort_id"] != cohort["cohort_id"]
            ):
                _add(
                    errors,
                    "case_cohort_binding_mismatch",
                    "$.cohorts",
                    f"case {case_ref} binds another cohort",
                )
    if any(case["risk_class_id"] not in risk_ids for case in bundle["cases"]):
        _add(
            errors,
            "unknown_risk_class",
            "$.cases",
            "every case must bind a declared risk class",
        )

    leaked = _leaked_accesses(
        bundle["access_records"],
        predictions_sealed_at=partition["predictions_sealed_at"],
    )
    expected_diagnostics = {
        "split_overlap_refs": overlap,
        "leakage_status": (
            "unknown"
            if partition["access_log_coverage"] != "claimed_complete"
            else "detected"
            if leaked
            else "not_observed_in_supplied_records"
        ),
        "leaked_access_refs": leaked,
    }
    if bundle["dataset_diagnostics"] != expected_diagnostics:
        _add(
            errors,
            "dataset_diagnostics_mismatch",
            "$.dataset_diagnostics",
            "dataset diagnostics do not replay",
        )

    expected_metrics = _metrics(
        policy=policy,
        cases=bundle["cases"],
        cohorts=bundle["cohorts"],
    )
    if bundle["metrics"] != expected_metrics:
        _add(
            errors,
            "metrics_replay_mismatch",
            "$.metrics",
            "metrics do not replay from cases",
        )
    expected_evaluation_material_digest = _evaluation_material_digest(
        evaluation_id=bundle["evaluation_id"],
        base_field_evaluation_ref=bundle["base_field_evaluation_ref"],
        route_implementation_ref=bundle["route_implementation_ref"],
        metric_definition_profile=expected_metric_profile,
        dataset_partition=bundle["dataset_partition"],
        access_records=bundle["access_records"],
        cohorts=bundle["cohorts"],
        cases=bundle["cases"],
        metrics=expected_metrics,
        evaluation_as_of=bundle["evaluation_as_of"],
    )
    if bundle["evaluation_material_digest"] != expected_evaluation_material_digest:
        _add(
            errors,
            "evaluation_material_digest_mismatch",
            "$.evaluation_material_digest",
            "completed evaluation material does not replay",
        )
    expected_assessment = _assessment(
        evaluation_id=bundle["evaluation_id"],
        policy=policy,
        decisions=decisions,
        base_field_evaluation_ref=bundle["base_field_evaluation_ref"],
        route_implementation_ref=bundle["route_implementation_ref"],
        evaluation_material_digest=expected_evaluation_material_digest,
        cases=bundle["cases"],
        access_log_coverage=partition["access_log_coverage"],
        leaked_access_refs=leaked,
        metrics=expected_metrics,
        evaluation_as_of=bundle["evaluation_as_of"],
        review_due_at=bundle["review_due_at"],
    )
    if bundle["assessment"] != expected_assessment:
        _add(
            errors,
            "assessment_replay_mismatch",
            "$.assessment",
            "assessment does not replay",
        )
    if bundle["authority_boundary"] != _AUTHORITY_BOUNDARY:
        _add(
            errors,
            "authority_boundary_mismatch",
            "$.authority_boundary",
            "authority boundary must remain fixed",
        )
    if not set(_LIMITATIONS).issubset(set(bundle["limitations"])):
        _add(
            errors,
            "required_limitation_missing",
            "$.limitations",
            "required field-performance limitations cannot be removed",
        )
    if bundle["bundle_digest"] != _record_digest(bundle, "bundle_digest"):
        _add(
            errors,
            "bundle_digest_mismatch",
            "$.bundle_digest",
            "bundle digest does not replay",
        )
    return tuple(errors)


def validate_field_performance(bundle: Mapping[str, Any]) -> dict[str, Any]:
    errors = field_performance_errors(bundle)
    if errors:
        raise FieldPerformanceGovernanceError(errors)
    return copy.deepcopy(dict(bundle))


__all__ = [
    "METRIC_NAMES",
    "SCHEMA_VERSION",
    "FieldPerformanceGovernanceError",
    "build_access_record",
    "build_field_performance_bundle",
    "build_performance_case",
    "build_performance_policy",
    "canonical_sha256",
    "digest_ref",
    "digest_value",
    "field_performance_errors",
    "validate_field_performance",
    "versioned_ref",
]
