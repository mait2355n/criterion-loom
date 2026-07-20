"""Deterministic field evaluation and route ablation support.

The module binds a human-owned evaluation policy, population, blind labels,
holdout, and four route runs before computing metrics.  It never chooses error
costs, thresholds, or deployment cutover, and it never generalizes local
fixtures or smoke checks into field validity.
"""

from __future__ import annotations

import copy
from datetime import datetime
from functools import lru_cache
import hashlib
import json
from statistics import NormalDist
from typing import Any, Iterable, Mapping, Sequence

from jsonschema import Draft202012Validator, FormatChecker

from .schema_access import schema_path


SCHEMA_VERSION = "field-evaluation/v0"
ROUTES = ("direct_only", "morphology", "dependency", "llm")
ROUTE_PAIRS = tuple(zip(ROUTES[:-1], ROUTES[1:], strict=True))
REFERENCE_LABELS = ("satisfied", "refuted")
PREDICTIONS = (*REFERENCE_LABELS, "abstain")

_SCHEMA_PATH = schema_path("field-evaluation.schema.json")
_DEFAULT_LIMITATIONS = (
    "Validity is bounded to the declared population, intended use, strata, label guide, policy, holdout, and route versions.",
    "Detection metrics do not establish repair effect, human operational use, operational qualification, or cutover readiness.",
    "semantic-guard computes and validates declared policy consequences; humans own costs, thresholds, policy adoption, and final decisions.",
)
_FIELD_VALIDITY_LIMITATIONS = (
    "Established status applies only to the declared field population and intended use.",
    "Wilson intervals quantify sampling uncertainty under the observed denominator, not label correctness or population representativeness.",
    "A future policy, rule, analyzer, model, prompt, population, label guide, or route change requires a new evaluation binding.",
)
_NOT_EVALUATED_AXES = {
    "repair_effect": {
        "status": "not_evaluated",
        "evidence_refs": [],
        "reason": "Detection-route comparison does not measure whether audit findings cause successful repair.",
    },
    "human_operational_use": {
        "status": "not_evaluated",
        "evidence_refs": [],
        "reason": "No human workflow, comprehension, decision quality, or workload outcome is measured here.",
    },
    "operational_qualification": {
        "status": "not_evaluated",
        "evidence_refs": [],
        "reason": "No secure operation, reliability, incident, capacity, or cutover qualification is measured here.",
    },
}
_AUTHORITY_BOUNDARY = {
    "semantic_guard_role": "compute_and_validate_declared_evaluation",
    "cost_owner": "human",
    "threshold_owner": "human",
    "cutover_owner": "external_human_or_control_plane",
    "final_acceptance_owner": "human",
}


class FieldEvaluationValidationError(ValueError):
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
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def digest_value(value: Any) -> dict[str, str]:
    return {"algorithm": "sha256", "value": canonical_sha256(value)}


def versioned_ref(ref_id: str, version: str, material: Any | None = None) -> dict[str, Any]:
    basis = {"ref_id": ref_id, "version": version} if material is None else material
    return {"ref_id": ref_id, "version": version, "digest": digest_value(basis)}


def _sorted_dicts(values: Iterable[Mapping[str, Any]], *keys: str) -> list[dict[str, Any]]:
    return sorted(
        [copy.deepcopy(dict(item)) for item in values],
        key=lambda item: tuple(str(item.get(key, "")) for key in keys),
    )


def _without_digest(value: Mapping[str, Any], field: str) -> dict[str, Any]:
    return {key: copy.deepcopy(item) for key, item in value.items() if key != field}


def _normalize_stratification(values: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for value in values:
        item = copy.deepcopy(dict(value))
        item["strata"] = _sorted_dicts(item["strata"], "stratum_id")
        result.append(item)
    return sorted(result, key=lambda item: str(item["dimension_id"]))


def build_evaluation_policy(
    *,
    policy_id: str,
    version: str,
    status: str,
    decision_record_ref: str | None,
    target_population: Mapping[str, Any],
    stratification: Iterable[Mapping[str, Any]],
    cost_model: Mapping[str, Any],
    thresholds: Mapping[str, Any],
    minimum_sample: Mapping[str, Any],
    confidence_level: float,
    primary_metric: str,
    candidate_route: str,
    evidence_class: str,
    review_triggers: Iterable[str],
) -> dict[str, Any]:
    """Build a content-addressed policy whose choices remain human-owned."""

    population_material = {
        key: copy.deepcopy(value)
        for key, value in target_population.items()
        if key != "population_digest"
    }
    population = {
        **population_material,
        "inclusion_criteria": sorted(set(population_material["inclusion_criteria"])),
        "exclusion_criteria": sorted(set(population_material["exclusion_criteria"])),
    }
    population["population_digest"] = digest_value(population)
    material = {
        "policy_id": policy_id,
        "version": version,
        "owner_kind": "human",
        "status": status,
        "decision_record_ref": decision_record_ref,
        "target_population": population,
        "stratification": _normalize_stratification(stratification),
        "cost_model": copy.deepcopy(dict(cost_model)),
        "thresholds": copy.deepcopy(dict(thresholds)),
        "minimum_sample": copy.deepcopy(dict(minimum_sample)),
        "confidence_level": confidence_level,
        "primary_metric": primary_metric,
        "candidate_route": candidate_route,
        "evidence_class": evidence_class,
        "review_triggers": sorted(set(review_triggers)),
    }
    return {**material, "policy_digest": digest_value(material)}


def build_human_policy_decision(
    *,
    decision_id: str,
    decision_type: str,
    human_actor_ref: str,
    policy: Mapping[str, Any],
    rationale: str,
    evidence_refs: Iterable[str],
    recorded_at: str,
) -> dict[str, Any]:
    decision = "adopt" if decision_type == "adopt_policy" else "retire"
    return {
        "decision_id": decision_id,
        "decision_type": decision_type,
        "issuer_kind": "human",
        "human_actor_ref": human_actor_ref,
        "policy_id": policy["policy_id"],
        "policy_version": policy["version"],
        "policy_digest": copy.deepcopy(policy["policy_digest"]),
        "decision": decision,
        "rationale": rationale,
        "evidence_refs": sorted(set(evidence_refs)),
        "recorded_at": recorded_at,
    }


def build_field_case(
    *,
    case_id: str,
    subject_ref: str,
    subject_digest: Mapping[str, Any],
    population_id: str,
    intended_use_id: str,
    stratum_refs: Iterable[str],
    source_kind: str = "field_sample",
) -> dict[str, Any]:
    material = {
        "case_id": case_id,
        "subject_ref": subject_ref,
        "subject_digest": copy.deepcopy(dict(subject_digest)),
        "population_id": population_id,
        "intended_use_id": intended_use_id,
        "stratum_refs": sorted(set(stratum_refs)),
        "source_kind": source_kind,
        "split": "holdout",
    }
    return {**material, "case_digest": digest_value(material)}


def build_blind_label(
    *,
    label_id: str,
    case: Mapping[str, Any],
    reviewer_id: str,
    reference_label: str,
    label_guide: Mapping[str, Any],
    recorded_at: str,
    blind_to_route_outputs: bool = True,
    blind_to_other_labels: bool = True,
) -> dict[str, Any]:
    material = {
        "label_id": label_id,
        "case_id": case["case_id"],
        "case_digest": copy.deepcopy(case["case_digest"]),
        "reviewer_id": reviewer_id,
        "reference_label": reference_label,
        "label_guide_ref": label_guide["ref_id"],
        "label_guide_digest": copy.deepcopy(label_guide["digest"]),
        "blind_to_route_outputs": blind_to_route_outputs,
        "blind_to_other_labels": blind_to_other_labels,
        "recorded_at": recorded_at,
    }
    return {**material, "label_digest": digest_value(material)}


def build_adjudication(
    *,
    adjudication_id: str,
    case: Mapping[str, Any],
    adjudicator_id: str,
    basis_label_refs: Iterable[str],
    final_label: str,
    label_guide: Mapping[str, Any],
    recorded_at: str,
) -> dict[str, Any]:
    material = {
        "adjudication_id": adjudication_id,
        "case_id": case["case_id"],
        "case_digest": copy.deepcopy(case["case_digest"]),
        "adjudicator_id": adjudicator_id,
        "basis_label_refs": sorted(set(basis_label_refs)),
        "final_label": final_label,
        "label_guide_ref": label_guide["ref_id"],
        "label_guide_digest": copy.deepcopy(label_guide["digest"]),
        "recorded_at": recorded_at,
    }
    return {**material, "adjudication_digest": digest_value(material)}


def _case_set_digest(cases: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    return digest_value(_sorted_dicts(cases, "case_id"))


def _label_bundle_digest(
    label_guide: Mapping[str, Any],
    labels: Sequence[Mapping[str, Any]],
    adjudications: Sequence[Mapping[str, Any]],
) -> dict[str, str]:
    return digest_value(
        {
            "label_guide": copy.deepcopy(dict(label_guide)),
            "labels": _sorted_dicts(labels, "label_id"),
            "adjudications": _sorted_dicts(adjudications, "adjudication_id"),
        }
    )


def _build_holdout(
    *,
    holdout_id: str,
    cases: Sequence[Mapping[str, Any]],
    sealed_at: str,
    labels_released_at: str,
) -> dict[str, Any]:
    case_digest = _case_set_digest(cases)
    material = {
        "holdout_id": holdout_id,
        "case_refs": [
            {
                "case_id": item["case_id"],
                "case_digest": copy.deepcopy(item["case_digest"]),
            }
            for item in _sorted_dicts(cases, "case_id")
        ],
        "case_set_digest": case_digest,
        "sealed_at": sealed_at,
        "labels_released_at": labels_released_at,
    }
    return {**material, "holdout_digest": digest_value(material)}


def _build_runs(
    *,
    run_specs: Sequence[Mapping[str, Any]],
    cases: Sequence[Mapping[str, Any]],
    policy: Mapping[str, Any],
    holdout: Mapping[str, Any],
    label_bundle_digest: Mapping[str, Any],
) -> list[dict[str, Any]]:
    cases_by_id = {str(item["case_id"]): item for item in cases}
    runs: list[dict[str, Any]] = []
    for spec in run_specs:
        case_results: list[dict[str, Any]] = []
        for result in spec["case_results"]:
            case_id = str(result["case_id"])
            if case_id not in cases_by_id:
                raise ValueError(f"run spec references unknown case: {case_id}")
            case_results.append(
                {
                    "case_id": case_id,
                    "case_digest": copy.deepcopy(cases_by_id[case_id]["case_digest"]),
                    "prediction": result["prediction"],
                    "reason_codes": sorted(set(result["reason_codes"])),
                }
            )
        material = {
            "run_id": spec["run_id"],
            "route": spec["route"],
            "route_config": copy.deepcopy(dict(spec["route_config"])),
            "policy_id": policy["policy_id"],
            "policy_version": policy["version"],
            "policy_digest": copy.deepcopy(policy["policy_digest"]),
            "population_digest": copy.deepcopy(
                policy["target_population"]["population_digest"]
            ),
            "holdout_id": holdout["holdout_id"],
            "holdout_digest": copy.deepcopy(holdout["holdout_digest"]),
            "case_set_digest": copy.deepcopy(holdout["case_set_digest"]),
            "label_bundle_digest": copy.deepcopy(dict(label_bundle_digest)),
            "predictions_recorded_at": spec["predictions_recorded_at"],
            "label_access_prohibited": spec.get("label_access_prohibited", True),
            "training_case_refs": sorted(set(spec.get("training_case_refs", []))),
            "case_results": _sorted_dicts(case_results, "case_id"),
        }
        runs.append({**material, "run_digest": digest_value(material)})
    return _sorted_dicts(runs, "route", "run_id")


def wilson_interval(
    successes: int,
    total: int,
    confidence_level: float,
) -> dict[str, float | None]:
    """Return a deterministic two-sided Wilson score interval."""

    if total == 0:
        return {
            "confidence_level": confidence_level,
            "lower": None,
            "upper": None,
        }
    z = NormalDist().inv_cdf(0.5 + confidence_level / 2.0)
    proportion = successes / total
    z2 = z * z
    denominator = 1.0 + z2 / total
    center = (proportion + z2 / (2.0 * total)) / denominator
    margin = (
        z
        * ((proportion * (1.0 - proportion) / total + z2 / (4.0 * total * total)) ** 0.5)
        / denominator
    )
    return {
        "confidence_level": confidence_level,
        "lower": round(max(0.0, center - margin), 12),
        "upper": round(min(1.0, center + margin), 12),
    }


def _rate(numerator: int, denominator: int, confidence: float) -> dict[str, Any]:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "value": None if denominator == 0 else round(numerator / denominator, 12),
        "wilson_interval": wilson_interval(numerator, denominator, confidence),
    }


def _reference_labels(
    cases: Sequence[Mapping[str, Any]],
    labels: Sequence[Mapping[str, Any]],
    adjudications: Sequence[Mapping[str, Any]],
) -> dict[str, str]:
    labels_by_case: dict[str, list[Mapping[str, Any]]] = {}
    for label in labels:
        labels_by_case.setdefault(str(label["case_id"]), []).append(label)
    adjudications_by_case = {
        str(item["case_id"]): item for item in adjudications
    }
    result: dict[str, str] = {}
    for case in cases:
        case_id = str(case["case_id"])
        observed = {
            str(label["reference_label"])
            for label in labels_by_case.get(case_id, [])
        }
        if not observed:
            raise ValueError(f"case has no reference label: {case_id}")
        if len(observed) == 1:
            result[case_id] = next(iter(observed))
            continue
        if case_id not in adjudications_by_case:
            raise ValueError(f"disagreement requires adjudication: {case_id}")
        result[case_id] = str(adjudications_by_case[case_id]["final_label"])
    return result


def _metric_for_cases(
    *,
    case_ids: Sequence[str],
    truth: Mapping[str, str],
    predictions: Mapping[str, str],
    policy: Mapping[str, Any],
) -> dict[str, Any]:
    reference_satisfied = sum(truth[item] == "satisfied" for item in case_ids)
    reference_refuted = sum(truth[item] == "refuted" for item in case_ids)
    false_satisfaction = sum(
        truth[item] == "refuted" and predictions[item] == "satisfied"
        for item in case_ids
    )
    false_refutation = sum(
        truth[item] == "satisfied" and predictions[item] == "refuted"
        for item in case_ids
    )
    abstain = sum(predictions[item] == "abstain" for item in case_ids)
    covered = len(case_ids) - abstain
    correct = sum(predictions[item] == truth[item] for item in case_ids)
    confidence = float(policy["confidence_level"])
    costs = policy["cost_model"]
    loss = (
        false_satisfaction * costs["false_satisfaction_cost"]
        + false_refutation * costs["false_refutation_cost"]
        + abstain * costs["abstention_cost"]
    ) / len(case_ids) if case_ids else 0.0
    return {
        "counts": {
            "total": len(case_ids),
            "reference_satisfied": reference_satisfied,
            "reference_refuted": reference_refuted,
            "false_satisfaction": false_satisfaction,
            "false_refutation": false_refutation,
            "abstain": abstain,
            "covered": covered,
            "correct": correct,
        },
        "rates": {
            "false_satisfaction": _rate(
                false_satisfaction, reference_refuted, confidence
            ),
            "false_refutation": _rate(
                false_refutation, reference_satisfied, confidence
            ),
            "abstention": _rate(abstain, len(case_ids), confidence),
            "coverage": _rate(covered, len(case_ids), confidence),
        },
        "cost_weighted_loss": round(loss, 12),
    }


def _delta(left: float | None, right: float | None) -> float | None:
    if left is None or right is None:
        return None
    return round(right - left, 12)


def _compute_metrics(
    *,
    policy: Mapping[str, Any],
    cases: Sequence[Mapping[str, Any]],
    labels: Sequence[Mapping[str, Any]],
    adjudications: Sequence[Mapping[str, Any]],
    runs: Sequence[Mapping[str, Any]],
    case_set_digest: Mapping[str, Any],
    label_bundle_digest: Mapping[str, Any],
) -> dict[str, Any]:
    truth = _reference_labels(cases, labels, adjudications)
    cases_by_id = {str(item["case_id"]): item for item in cases}
    all_case_ids = sorted(cases_by_id)
    runs_by_route = {str(item["route"]): item for item in runs}
    predictions_by_route = {
        route: {
            str(item["case_id"]): str(item["prediction"])
            for item in run["case_results"]
        }
        for route, run in runs_by_route.items()
    }
    stratum_refs = sorted(
        {
            str(stratum_ref)
            for case in cases
            for stratum_ref in case["stratum_refs"]
        }
    )
    route_metrics: list[dict[str, Any]] = []
    metric_by_route: dict[str, dict[str, Any]] = {}
    for route in ROUTES:
        run = runs_by_route[route]
        predictions = predictions_by_route[route]
        base = _metric_for_cases(
            case_ids=all_case_ids,
            truth=truth,
            predictions=predictions,
            policy=policy,
        )
        strata = []
        for stratum_ref in stratum_refs:
            selected = [
                case_id
                for case_id, case in cases_by_id.items()
                if stratum_ref in case["stratum_refs"]
            ]
            strata.append(
                {
                    "stratum_ref": stratum_ref,
                    **_metric_for_cases(
                        case_ids=sorted(selected),
                        truth=truth,
                        predictions=predictions,
                        policy=policy,
                    ),
                }
            )
        metric = {
            "route": route,
            "run_ref": run["run_id"],
            "run_digest": copy.deepcopy(run["run_digest"]),
            **base,
            "strata": strata,
        }
        route_metrics.append(metric)
        metric_by_route[route] = metric

    incremental_values: list[dict[str, Any]] = []
    for baseline_route, target_route in ROUTE_PAIRS:
        baseline = metric_by_route[baseline_route]
        target = metric_by_route[target_route]
        baseline_predictions = predictions_by_route[baseline_route]
        target_predictions = predictions_by_route[target_route]
        resolved_abstentions = sum(
            baseline_predictions[case_id] == "abstain"
            and target_predictions[case_id] == truth[case_id]
            for case_id in all_case_ids
        )
        introduced_errors = sum(
            baseline_predictions[case_id] in {truth[case_id], "abstain"}
            and target_predictions[case_id] not in {truth[case_id], "abstain"}
            for case_id in all_case_ids
        )
        incremental_values.append(
            {
                "baseline_route": baseline_route,
                "target_route": target_route,
                "case_set_digest": copy.deepcopy(dict(case_set_digest)),
                "loss_reduction": round(
                    baseline["cost_weighted_loss"] - target["cost_weighted_loss"],
                    12,
                ),
                "coverage_delta": round(
                    target["rates"]["coverage"]["value"]
                    - baseline["rates"]["coverage"]["value"],
                    12,
                ),
                "false_satisfaction_rate_delta": _delta(
                    baseline["rates"]["false_satisfaction"]["value"],
                    target["rates"]["false_satisfaction"]["value"],
                ),
                "false_refutation_rate_delta": _delta(
                    baseline["rates"]["false_refutation"]["value"],
                    target["rates"]["false_refutation"]["value"],
                ),
                "resolved_abstentions": resolved_abstentions,
                "introduced_errors": introduced_errors,
            }
        )

    candidate = metric_by_route[str(policy["candidate_route"])]
    point_estimates = {
        "false_satisfaction_rate": candidate["rates"]["false_satisfaction"]["value"],
        "false_refutation_rate": candidate["rates"]["false_refutation"]["value"],
        "abstention_rate": candidate["rates"]["abstention"]["value"],
        "coverage": candidate["rates"]["coverage"]["value"],
        "cost_weighted_loss": candidate["cost_weighted_loss"],
    }
    comparison_values = {
        "false_satisfaction_rate": candidate["rates"]["false_satisfaction"]
        ["wilson_interval"]["upper"],
        "false_refutation_rate": candidate["rates"]["false_refutation"]
        ["wilson_interval"]["upper"],
        "abstention_rate": candidate["rates"]["abstention"]["wilson_interval"]
        ["upper"],
        "coverage": candidate["rates"]["coverage"]["wilson_interval"]["lower"],
        "cost_weighted_loss": candidate["cost_weighted_loss"],
    }
    comparison_bases = {
        "false_satisfaction_rate": "wilson_upper",
        "false_refutation_rate": "wilson_upper",
        "abstention_rate": "wilson_upper",
        "coverage": "wilson_lower",
        "cost_weighted_loss": "point_estimate",
    }
    threshold_pairs = (
        (
            "false_satisfaction_rate",
            "<=",
            policy["thresholds"]["max_false_satisfaction_rate"],
        ),
        (
            "false_refutation_rate",
            "<=",
            policy["thresholds"]["max_false_refutation_rate"],
        ),
        ("abstention_rate", "<=", policy["thresholds"]["max_abstention_rate"]),
        ("coverage", ">=", policy["thresholds"]["min_coverage"]),
        (
            "cost_weighted_loss",
            "<=",
            policy["thresholds"]["max_cost_weighted_loss"],
        ),
    )
    criteria: list[dict[str, Any]] = []
    for metric_name, operator, threshold in threshold_pairs:
        value = comparison_values[metric_name]
        passed = value is not None and (
            value <= threshold if operator == "<=" else value >= threshold
        )
        criteria.append(
            {
                "metric": metric_name,
                "operator": operator,
                "point_estimate": point_estimates[metric_name],
                "comparison_value": value,
                "comparison_basis": comparison_bases[metric_name],
                "confidence_level": (
                    None
                    if comparison_bases[metric_name] == "point_estimate"
                    else policy["confidence_level"]
                ),
                "threshold": threshold,
                "passed": passed,
            }
        )
    material = {
        "case_set_digest": copy.deepcopy(dict(case_set_digest)),
        "label_bundle_digest": copy.deepcopy(dict(label_bundle_digest)),
        "population_digest": copy.deepcopy(
            policy["target_population"]["population_digest"]
        ),
        "route_metrics": route_metrics,
        "incremental_values": incremental_values,
        "threshold_assessment": {
            "route": policy["candidate_route"],
            "status": "passed" if all(item["passed"] for item in criteria) else "failed",
            "criteria": criteria,
        },
    }
    return {**material, "metrics_digest": digest_value(material)}


def _matching_policy_decision(
    policy: Mapping[str, Any], decisions: Sequence[Mapping[str, Any]]
) -> bool:
    reference = policy["decision_record_ref"]
    if not reference:
        return False
    matches = [item for item in decisions if item["decision_id"] == reference]
    if len(matches) != 1:
        return False
    decision = matches[0]
    expected_type = "adopt_policy" if policy["status"] == "adopted" else "retire_policy"
    expected_decision = "adopt" if policy["status"] == "adopted" else "retire"
    return (
        decision["decision_type"] == expected_type
        and decision["decision"] == expected_decision
        and decision["policy_id"] == policy["policy_id"]
        and decision["policy_version"] == policy["version"]
        and decision["policy_digest"] == policy["policy_digest"]
    )


def _compute_field_validity(
    *,
    policy: Mapping[str, Any],
    decisions: Sequence[Mapping[str, Any]],
    reviewers: Sequence[Mapping[str, Any]],
    labels: Sequence[Mapping[str, Any]],
    cases: Sequence[Mapping[str, Any]],
    truth: Mapping[str, str],
    metrics: Mapping[str, Any],
    holdout: Mapping[str, Any],
) -> dict[str, Any]:
    reasons: list[str] = []
    if policy["status"] != "adopted":
        reasons.append("policy_not_adopted")
    if policy["status"] == "adopted" and not _matching_policy_decision(policy, decisions):
        reasons.append("policy_decision_missing_or_mismatched")
    if policy["status"] == "adopted" and policy["decision_record_ref"]:
        matching_decisions = [
            item
            for item in decisions
            if item["decision_id"] == policy["decision_record_ref"]
            and item["decision_type"] == "adopt_policy"
            and item["decision"] == "adopt"
        ]
        if matching_decisions and _parse_time(
            matching_decisions[0]["recorded_at"]
        ) > _parse_time(holdout["sealed_at"]):
            reasons.append("policy_not_frozen_before_holdout")

    label_reviewers = [item for item in reviewers if item["role"] == "label_reviewer"]
    reviewers_by_id = {str(item["reviewer_id"]): item for item in reviewers}
    independent_groups = {
        item["independence_group"]
        for item in label_reviewers
        if item["relationship_to_system"] == "independent"
    }
    if len(label_reviewers) < 2 or len(independent_groups) < 2:
        reasons.append("reviewer_independence_insufficient")
    if any(
        not item["blind_to_route_outputs"] or not item["blind_to_other_labels"]
        for item in label_reviewers
    ) or any(
        not item["blind_to_route_outputs"] or not item["blind_to_other_labels"]
        for item in labels
    ):
        reasons.append("blindness_not_established")
    labels_by_case: dict[str, list[Mapping[str, Any]]] = {}
    for label in labels:
        labels_by_case.setdefault(str(label["case_id"]), []).append(label)
    for case in cases:
        actual_independent_groups = {
            str(reviewers_by_id[reviewer_id]["independence_group"])
            for label in labels_by_case.get(str(case["case_id"]), [])
            if (reviewer_id := str(label["reviewer_id"])) in reviewers_by_id
            and reviewers_by_id[reviewer_id]["role"] == "label_reviewer"
            and reviewers_by_id[reviewer_id]["relationship_to_system"]
            == "independent"
        }
        if len(actual_independent_groups) < 2:
            reasons.append("case_reviewer_independence_insufficient")
            break

    minimum = policy["minimum_sample"]
    satisfied_count = sum(value == "satisfied" for value in truth.values())
    refuted_count = sum(value == "refuted" for value in truth.values())
    if (
        len(cases) < minimum["overall"]
        or satisfied_count < minimum["reference_satisfied"]
        or refuted_count < minimum["reference_refuted"]
    ):
        reasons.append("sample_size_insufficient")
    required_strata = {
        str(stratum["stratum_id"])
        for dimension in policy["stratification"]
        if dimension["required"]
        for stratum in dimension["strata"]
    }
    for stratum_ref in required_strata:
        if sum(stratum_ref in case["stratum_refs"] for case in cases) < minimum[
            "per_required_stratum"
        ]:
            reasons.append("required_stratum_sample_insufficient")
            break
    if metrics["threshold_assessment"]["status"] != "passed":
        reasons.append("thresholds_not_met")
    if policy["evidence_class"] != "field_evaluation" or any(
        item["source_kind"] != "field_sample" for item in cases
    ):
        reasons.append("non_field_evidence_cannot_establish_validity")

    reasons = sorted(set(reasons))
    return {
        "status": (
            "established_for_declared_population" if not reasons else "not_established"
        ),
        "reasons": reasons,
        "policy_id": policy["policy_id"],
        "policy_version": policy["version"],
        "policy_digest": copy.deepcopy(policy["policy_digest"]),
        "population_digest": copy.deepcopy(
            policy["target_population"]["population_digest"]
        ),
        "holdout_digest": copy.deepcopy(holdout["holdout_digest"]),
        "evaluated_route": policy["candidate_route"],
        "limitations": list(_FIELD_VALIDITY_LIMITATIONS),
    }


def build_field_evaluation(
    *,
    evaluation_id: str,
    policy: Mapping[str, Any],
    human_decision_records: Iterable[Mapping[str, Any]],
    label_guide: Mapping[str, Any],
    reviewers: Iterable[Mapping[str, Any]],
    cases: Iterable[Mapping[str, Any]],
    labels: Iterable[Mapping[str, Any]],
    adjudications: Iterable[Mapping[str, Any]],
    holdout_id: str,
    sealed_at: str,
    labels_released_at: str,
    run_specs: Iterable[Mapping[str, Any]],
    limitations: Iterable[str] = _DEFAULT_LIMITATIONS,
) -> dict[str, Any]:
    """Build metrics and validity from one bound, same-case four-route bundle."""

    policy_value = copy.deepcopy(dict(policy))
    decisions = _sorted_dicts(human_decision_records, "decision_id")
    guide = copy.deepcopy(dict(label_guide))
    reviewer_values = _sorted_dicts(reviewers, "reviewer_id")
    case_values = _sorted_dicts(cases, "case_id")
    label_values = _sorted_dicts(labels, "label_id")
    adjudication_values = _sorted_dicts(adjudications, "adjudication_id")
    holdout = _build_holdout(
        holdout_id=holdout_id,
        cases=case_values,
        sealed_at=sealed_at,
        labels_released_at=labels_released_at,
    )
    label_digest = _label_bundle_digest(guide, label_values, adjudication_values)
    runs = _build_runs(
        run_specs=list(run_specs),
        cases=case_values,
        policy=policy_value,
        holdout=holdout,
        label_bundle_digest=label_digest,
    )
    metrics = _compute_metrics(
        policy=policy_value,
        cases=case_values,
        labels=label_values,
        adjudications=adjudication_values,
        runs=runs,
        case_set_digest=holdout["case_set_digest"],
        label_bundle_digest=label_digest,
    )
    truth = _reference_labels(case_values, label_values, adjudication_values)
    field_validity = _compute_field_validity(
        policy=policy_value,
        decisions=decisions,
        reviewers=reviewer_values,
        labels=label_values,
        cases=case_values,
        truth=truth,
        metrics=metrics,
        holdout=holdout,
    )
    material = {
        "schema_version": SCHEMA_VERSION,
        "evaluation_id": evaluation_id,
        "policy": policy_value,
        "human_decision_records": decisions,
        "label_guide": guide,
        "reviewers": reviewer_values,
        "cases": case_values,
        "labels": label_values,
        "adjudications": adjudication_values,
        "holdout": holdout,
        "runs": runs,
        "metrics": metrics,
        "field_validity": field_validity,
        "outcome_axes": copy.deepcopy(_NOT_EVALUATED_AXES),
        "authority_boundary": copy.deepcopy(_AUTHORITY_BOUNDARY),
        "limitations": sorted(set(limitations)),
    }
    return {**material, "bundle_digest": digest_value(material)}


@lru_cache(maxsize=1)
def _schema_validator() -> Draft202012Validator:
    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _add(
    errors: list[dict[str, str]],
    code: str,
    location: str,
    message: str,
) -> None:
    errors.append({"code": code, "location": location, "message": message})


def _schema_location(path: Any) -> str:
    values = [str(item) for item in path]
    return "$" if not values else "$." + ".".join(values)


def _duplicates(values: Iterable[str]) -> set[str]:
    seen: set[str] = set()
    duplicate: set[str] = set()
    for value in values:
        if value in seen:
            duplicate.add(value)
        seen.add(value)
    return duplicate


def _parse_time(value: str) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    return datetime.fromisoformat(normalized)


def field_evaluation_errors(bundle: Mapping[str, Any]) -> tuple[dict[str, str], ...]:
    """Return fail-closed integrity errors and validity-recomputation errors."""

    errors: list[dict[str, str]] = []
    schema_failures = sorted(
        _schema_validator().iter_errors(bundle), key=lambda item: list(item.path)
    )
    for failure in schema_failures:
        _add(
            errors,
            "schema_validation_failed",
            _schema_location(failure.path),
            failure.message,
        )
    if schema_failures:
        return tuple(errors)

    material = _without_digest(bundle, "bundle_digest")
    if bundle["bundle_digest"] != digest_value(material):
        _add(errors, "bundle_digest_mismatch", "$.bundle_digest", "bundle digest does not replay")

    policy = bundle["policy"]
    population = policy["target_population"]
    population_material = _without_digest(population, "population_digest")
    if population["population_digest"] != digest_value(population_material):
        _add(
            errors,
            "population_digest_mismatch",
            "$.policy.target_population.population_digest",
            "target population changed after binding",
        )
    policy_material = _without_digest(policy, "policy_digest")
    if policy["policy_digest"] != digest_value(policy_material):
        _add(errors, "policy_digest_mismatch", "$.policy.policy_digest", "policy changed after binding")
    costs = policy["cost_model"]
    if not (
        costs["false_satisfaction_cost"] > costs["false_refutation_cost"]
        and costs["false_satisfaction_cost"] > costs["abstention_cost"]
    ):
        _add(
            errors,
            "catastrophic_cost_order_invalid",
            "$.policy.cost_model",
            "catastrophic false-satisfaction cost must exceed false-refutation and abstention costs",
        )

    decisions = bundle["human_decision_records"]
    decision_ids = [str(item["decision_id"]) for item in decisions]
    for duplicate in sorted(_duplicates(decision_ids)):
        _add(errors, "duplicate_human_decision", "$.human_decision_records", duplicate)
    if policy["status"] == "pending":
        if policy["decision_record_ref"] is not None:
            _add(
                errors,
                "pending_policy_has_decision",
                "$.policy.decision_record_ref",
                "pending policy cannot imply adoption or retirement",
            )
    elif not _matching_policy_decision(policy, decisions):
        _add(
            errors,
            "policy_human_decision_missing_or_mismatched",
            "$.policy.decision_record_ref",
            "adopted or retired policy requires its exact external human decision",
        )

    reviewers = bundle["reviewers"]
    reviewer_ids = [str(item["reviewer_id"]) for item in reviewers]
    for duplicate in sorted(_duplicates(reviewer_ids)):
        _add(errors, "duplicate_reviewer", "$.reviewers", duplicate)
    reviewers_by_id = {str(item["reviewer_id"]): item for item in reviewers}

    cases = bundle["cases"]
    case_ids = [str(item["case_id"]) for item in cases]
    for duplicate in sorted(_duplicates(case_ids)):
        _add(errors, "duplicate_case", "$.cases", duplicate)
    cases_by_id = {str(item["case_id"]): item for item in cases}
    declared_strata: dict[str, str] = {}
    required_dimensions: dict[str, set[str]] = {}
    for dimension in policy["stratification"]:
        strata = {str(item["stratum_id"]) for item in dimension["strata"]}
        for stratum_ref in strata:
            if stratum_ref in declared_strata:
                _add(errors, "duplicate_stratum_id", "$.policy.stratification", stratum_ref)
            declared_strata[stratum_ref] = str(dimension["dimension_id"])
        if dimension["required"]:
            required_dimensions[str(dimension["dimension_id"])] = strata
    for index, case in enumerate(cases):
        location = f"$.cases.{index}"
        if case["case_digest"] != digest_value(_without_digest(case, "case_digest")):
            _add(errors, "case_digest_mismatch", f"{location}.case_digest", case["case_id"])
        if (
            case["population_id"] != population["population_id"]
            or case["intended_use_id"] != population["intended_use_id"]
        ):
            _add(errors, "case_population_mismatch", location, case["case_id"])
        for stratum_ref in case["stratum_refs"]:
            if stratum_ref not in declared_strata:
                _add(errors, "case_dangling_stratum", location, stratum_ref)
        for dimension_id, stratum_set in required_dimensions.items():
            count = len(set(case["stratum_refs"]) & stratum_set)
            if count != 1:
                _add(
                    errors,
                    "case_required_stratum_cardinality",
                    location,
                    f"case must have exactly one stratum for {dimension_id}, found {count}",
                )

    expected_case_set_digest = _case_set_digest(cases)
    holdout = bundle["holdout"]
    if holdout["case_set_digest"] != expected_case_set_digest:
        _add(errors, "holdout_case_set_digest_mismatch", "$.holdout.case_set_digest", "case set changed")
    expected_case_refs = [
        {"case_id": item["case_id"], "case_digest": item["case_digest"]}
        for item in _sorted_dicts(cases, "case_id")
    ]
    if holdout["case_refs"] != expected_case_refs:
        _add(errors, "holdout_case_coverage_mismatch", "$.holdout.case_refs", "holdout must bind every case exactly once")
    if holdout["holdout_digest"] != digest_value(
        _without_digest(holdout, "holdout_digest")
    ):
        _add(errors, "holdout_digest_mismatch", "$.holdout.holdout_digest", "holdout changed")
    if _parse_time(holdout["sealed_at"]) >= _parse_time(holdout["labels_released_at"]):
        _add(errors, "holdout_time_order_invalid", "$.holdout", "seal must precede label release")
    if policy["status"] == "adopted" and policy["decision_record_ref"]:
        matching_decisions = [
            item
            for item in decisions
            if item["decision_id"] == policy["decision_record_ref"]
            and item["decision_type"] == "adopt_policy"
            and item["decision"] == "adopt"
        ]
        if matching_decisions and _parse_time(
            matching_decisions[0]["recorded_at"]
        ) > _parse_time(holdout["sealed_at"]):
            _add(
                errors,
                "policy_adoption_after_holdout_seal",
                "$.policy.decision_record_ref",
                "costs and thresholds must be adopted before the holdout is sealed",
            )

    labels = bundle["labels"]
    label_ids = [str(item["label_id"]) for item in labels]
    for duplicate in sorted(_duplicates(label_ids)):
        _add(errors, "duplicate_label", "$.labels", duplicate)
    labels_by_id = {str(item["label_id"]): item for item in labels}
    labels_by_case: dict[str, list[Mapping[str, Any]]] = {}
    for index, label in enumerate(labels):
        location = f"$.labels.{index}"
        if label["label_digest"] != digest_value(_without_digest(label, "label_digest")):
            _add(errors, "label_digest_mismatch", f"{location}.label_digest", label["label_id"])
        case_id = str(label["case_id"])
        labels_by_case.setdefault(case_id, []).append(label)
        if case_id not in cases_by_id or label["case_digest"] != cases_by_id.get(case_id, {}).get("case_digest"):
            _add(errors, "label_case_binding_mismatch", location, case_id)
        reviewer_id = str(label["reviewer_id"])
        if (
            reviewer_id not in reviewers_by_id
            or reviewers_by_id[reviewer_id]["role"] != "label_reviewer"
        ):
            _add(errors, "label_reviewer_invalid", location, reviewer_id)
        if (
            label["label_guide_ref"] != bundle["label_guide"]["ref_id"]
            or label["label_guide_digest"] != bundle["label_guide"]["digest"]
        ):
            _add(errors, "label_guide_binding_mismatch", location, label["label_id"])
        if not (
            _parse_time(holdout["sealed_at"])
            <= _parse_time(label["recorded_at"])
            <= _parse_time(holdout["labels_released_at"])
        ):
            _add(
                errors,
                "holdout_label_time_invalid",
                location,
                "blind labels must be recorded after sealing and no later than label release",
            )
    for case_id in case_ids:
        case_labels = labels_by_case.get(case_id, [])
        reviewer_refs = [str(item["reviewer_id"]) for item in case_labels]
        if len(case_labels) < 2:
            _add(errors, "case_label_count_insufficient", "$.labels", case_id)
        if _duplicates(reviewer_refs):
            _add(errors, "duplicate_reviewer_label_for_case", "$.labels", case_id)

    adjudications = bundle["adjudications"]
    adjudication_ids = [str(item["adjudication_id"]) for item in adjudications]
    adjudication_case_ids = [str(item["case_id"]) for item in adjudications]
    for duplicate in sorted(_duplicates(adjudication_ids)):
        _add(errors, "duplicate_adjudication", "$.adjudications", duplicate)
    for duplicate in sorted(_duplicates(adjudication_case_ids)):
        _add(errors, "duplicate_case_adjudication", "$.adjudications", duplicate)
    adjudications_by_case = {
        str(item["case_id"]): item for item in adjudications
    }
    for index, adjudication in enumerate(adjudications):
        location = f"$.adjudications.{index}"
        if adjudication["adjudication_digest"] != digest_value(
            _without_digest(adjudication, "adjudication_digest")
        ):
            _add(errors, "adjudication_digest_mismatch", location, adjudication["adjudication_id"])
        case_id = str(adjudication["case_id"])
        if case_id not in cases_by_id or adjudication["case_digest"] != cases_by_id.get(case_id, {}).get("case_digest"):
            _add(errors, "adjudication_case_binding_mismatch", location, case_id)
        if (
            adjudication["label_guide_ref"] != bundle["label_guide"]["ref_id"]
            or adjudication["label_guide_digest"] != bundle["label_guide"]["digest"]
        ):
            _add(errors, "adjudication_guide_binding_mismatch", location, case_id)
        adjudicator_id = str(adjudication["adjudicator_id"])
        if (
            adjudicator_id not in reviewers_by_id
            or reviewers_by_id[adjudicator_id]["role"] != "adjudicator"
        ):
            _add(errors, "adjudicator_invalid", location, adjudicator_id)
        basis = set(adjudication["basis_label_refs"])
        expected_basis = {
            str(item["label_id"]) for item in labels_by_case.get(case_id, [])
        }
        if basis != expected_basis or not basis.issubset(labels_by_id):
            _add(errors, "adjudication_basis_incomplete", location, case_id)
        if adjudicator_id in {
            str(item["reviewer_id"]) for item in labels_by_case.get(case_id, [])
        }:
            _add(errors, "adjudicator_not_independent", location, case_id)
    for case_id, case_labels in labels_by_case.items():
        observed = {str(item["reference_label"]) for item in case_labels}
        if len(observed) > 1 and case_id not in adjudications_by_case:
            _add(errors, "adjudication_missing", "$.adjudications", case_id)

    expected_label_bundle_digest = _label_bundle_digest(
        bundle["label_guide"], labels, adjudications
    )

    runs = bundle["runs"]
    run_ids = [str(item["run_id"]) for item in runs]
    routes = [str(item["route"]) for item in runs]
    for duplicate in sorted(_duplicates(run_ids)):
        _add(errors, "duplicate_run", "$.runs", duplicate)
    for duplicate in sorted(_duplicates(routes)):
        _add(errors, "duplicate_route_run", "$.runs", duplicate)
    if set(routes) != set(ROUTES):
        _add(errors, "route_coverage_mismatch", "$.runs", f"expected {list(ROUTES)}, found {sorted(set(routes))}")
    holdout_case_ids = set(case_ids)
    for index, run in enumerate(runs):
        location = f"$.runs.{index}"
        if run["run_digest"] != digest_value(_without_digest(run, "run_digest")):
            _add(errors, "run_digest_mismatch", f"{location}.run_digest", run["run_id"])
        expected_bindings = (
            run["policy_id"] == policy["policy_id"]
            and run["policy_version"] == policy["version"]
            and run["policy_digest"] == policy["policy_digest"]
            and run["population_digest"] == population["population_digest"]
            and run["holdout_id"] == holdout["holdout_id"]
            and run["holdout_digest"] == holdout["holdout_digest"]
            and run["case_set_digest"] == expected_case_set_digest
            and run["label_bundle_digest"] == expected_label_bundle_digest
        )
        if not expected_bindings:
            _add(errors, "run_evaluation_binding_mismatch", location, run["run_id"])
        result_ids = [str(item["case_id"]) for item in run["case_results"]]
        for duplicate in sorted(_duplicates(result_ids)):
            _add(errors, "duplicate_run_case", location, duplicate)
        if set(result_ids) != holdout_case_ids:
            _add(
                errors,
                "run_case_population_mismatch",
                location,
                f"route {run['route']} does not use the exact holdout case set",
            )
        for result in run["case_results"]:
            case_id = str(result["case_id"])
            if case_id not in cases_by_id or result["case_digest"] != cases_by_id.get(case_id, {}).get("case_digest"):
                _add(errors, "run_case_digest_mismatch", location, case_id)
        if not run["label_access_prohibited"]:
            _add(errors, "holdout_label_access_violation", location, run["run_id"])
        contamination = set(run["training_case_refs"]) & holdout_case_ids
        if contamination:
            _add(
                errors,
                "holdout_training_contamination",
                location,
                f"holdout cases used for training/tuning: {sorted(contamination)}",
            )
        if _parse_time(run["predictions_recorded_at"]) >= _parse_time(
            holdout["labels_released_at"]
        ):
            _add(
                errors,
                "holdout_prediction_after_label_release",
                location,
                run["run_id"],
            )
        if _parse_time(run["predictions_recorded_at"]) < _parse_time(
            holdout["sealed_at"]
        ):
            _add(
                errors,
                "holdout_prediction_before_seal",
                location,
                run["run_id"],
            )

    # Recompute metrics and validity only when reference and route denominators are usable.
    critical_codes = {
        "adjudication_missing",
        "case_label_count_insufficient",
        "duplicate_reviewer_label_for_case",
        "route_coverage_mismatch",
        "duplicate_route_run",
        "run_case_population_mismatch",
        "run_case_digest_mismatch",
    }
    if not critical_codes & {item["code"] for item in errors}:
        try:
            expected_metrics = _compute_metrics(
                policy=policy,
                cases=cases,
                labels=labels,
                adjudications=adjudications,
                runs=runs,
                case_set_digest=expected_case_set_digest,
                label_bundle_digest=expected_label_bundle_digest,
            )
            if bundle["metrics"] != expected_metrics:
                _add(
                    errors,
                    "metrics_replay_mismatch",
                    "$.metrics",
                    "stored metrics do not equal deterministic same-case recomputation",
                )
            truth = _reference_labels(cases, labels, adjudications)
            expected_validity = _compute_field_validity(
                policy=policy,
                decisions=decisions,
                reviewers=reviewers,
                labels=labels,
                cases=cases,
                truth=truth,
                metrics=expected_metrics,
                holdout=holdout,
            )
            if bundle["field_validity"] != expected_validity:
                _add(
                    errors,
                    "field_validity_replay_mismatch",
                    "$.field_validity",
                    "field validity does not equal deterministic policy evaluation",
                )
        except (KeyError, ValueError) as exc:
            _add(errors, "evaluation_replay_failed", "$.metrics", str(exc))

    return tuple(errors)


def validate_field_evaluation(bundle: Mapping[str, Any]) -> dict[str, Any]:
    errors = field_evaluation_errors(bundle)
    if errors:
        raise FieldEvaluationValidationError(errors)
    return copy.deepcopy(dict(bundle))
