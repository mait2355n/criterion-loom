"""Deterministic repair-effect and human-use evaluation contracts.

This module evaluates two operational outcome axes without joining them:
``repair_effect`` and ``human_operational_use``.  It binds a human-owned
policy, one immutable task set, baseline/candidate observations, independent
blind grading, disagreement adjudication, and conservative uncertainty bounds.

It is audit material only.  It does not recruit or assign participants, route
work, execute repairs, grant authority, send questions, cut over a system, or
make a final human acceptance decision.
"""

from __future__ import annotations

import copy
from datetime import datetime
from functools import lru_cache
import hashlib
import json
import math
from numbers import Number
from statistics import NormalDist
from typing import Any, Iterable, Mapping, Sequence

from jsonschema import Draft202012Validator, FormatChecker

from .schema_access import schema_path


SCHEMA_VERSION = "operational-outcome-evaluation/v1"
AXES = ("repair_effect", "human_operational_use")
ARMS = ("baseline", "candidate")
REPAIR_METRICS = (
    "correct_repair",
    "regression_free",
    "finding_integrity_preserved",
    "correct_escalation",
    "unresolved_preserved",
    "responsibility_boundary_preserved",
)
HUMAN_USE_METRICS = (
    "correct_routing",
    "proposition_understood",
    "evidence_understood",
    "limitations_understood",
    "unresolved_understood",
    "actionable",
    "correct_escalation",
    "authority_safe",
    "technical_pass_not_converted_to_acceptance",
)
METRICS_BY_AXIS = {
    "repair_effect": REPAIR_METRICS,
    "human_operational_use": HUMAN_USE_METRICS,
}
EVIDENCE_CLASSES = (
    "operational_participant",
    "synthetic",
    "local_fixture",
    "smoke",
)
HUMAN_ONLY_DECISIONS = frozenset(
    {
        "change_intent_or_scope",
        "accept_residual_risk",
        "grant_or_expand_authority",
        "authorize_external_effect",
        "final_acceptance",
    }
)
REPAIR_SHORTCUTS = frozenset(
    {"finding_suppression", "rule_weakening", "verification_bypass"}
)
MAX_TASKS = 256
MAX_PARTICIPANTS = 2048
MAX_SESSIONS = 4096
MAX_OBSERVATIONS = 65536
MAX_GRADERS = 128
MAX_SCORES = 262144
MAX_ADJUDICATIONS = 65536
MAX_DECISIONS = 64
MAX_LIMITATIONS = 256
MAX_TEXT_LENGTH = 4096
MAX_INPUT_DEPTH = 128
MAX_INPUT_CONTAINER_ITEMS = MAX_SCORES
MAX_PRE_SCHEMA_ERRORS = 64

_SCHEMA_PATH = schema_path("operational-outcome-evaluation.schema.json")
_AXIS_LIMITATIONS = {
    "repair_effect": (
        "Repair effect is bounded to the declared population, use, roles, task set, policy, arms, rubrics, and recorded session intervals.",
        "A local re-audit, changed artifact, or participant self-report is not repair-effect evidence by itself.",
        "Repair-effect results do not establish human operational use, field validity, operational qualification, security, cutover, or final acceptance.",
    ),
    "human_operational_use": (
        "Human-use effect is bounded to the declared population, use, roles, task set, policy, arms, rubrics, and recorded session intervals.",
        "Schema validity, technical passage, reviewer agreement, or participant self-report is not comprehension or correct authority use by itself.",
        "Human-use results do not establish repair effect, field validity, operational qualification, security, cutover, or final acceptance.",
    ),
}
_NON_INFERENCE = {
    "field_validity": {
        "status": "not_evaluated",
        "reason": "The operational outcome contract does not evaluate detection validity for a field population.",
    },
    "operational_qualification": {
        "status": "not_evaluated",
        "reason": "Participant outcomes do not qualify reliability, capacity, incident handling, or deployment operation.",
    },
    "security": {
        "status": "not_evaluated",
        "reason": "The contract does not establish secure processing, privacy control effectiveness, or threat resistance.",
    },
    "cutover": {
        "status": "not_evaluated",
        "reason": "No baseline/candidate outcome authorizes a default-route transition or predecessor retirement.",
    },
    "final_acceptance": {
        "status": "not_evaluated",
        "reason": "Final acceptance remains an external human decision and is never inferred from a technical or evaluation result.",
    },
}
_AUTHORITY_BOUNDARY = {
    "semantic_guard_role": "compute_and_validate_audit_material_only",
    "participant_assignment": False,
    "work_routing": False,
    "repair_execution": False,
    "authority_grant": False,
    "question_sending": False,
    "policy_adoption": False,
    "cutover_decision": False,
    "final_acceptance": False,
    "external_owners": {
        "study_operation": "external_research_or_operations_owner",
        "control": "external_caller_or_resource_control_plane",
        "policy_and_thresholds": "human",
        "final_acceptance": "human",
    },
}
_DEFAULT_LIMITATIONS = (
    "Participant identity, consent authenticity, reviewer identity, independence, blindness, timestamps, and source-artifact authenticity require external evidence; content digests alone do not prove them.",
    "The bundle is an audit record and never performs participant allocation, routing, repair, authority grant, question delivery, adoption, cutover, or acceptance.",
    "A result on either outcome axis cannot be projected onto the other axis or onto field validity, operational qualification, security, cutover, or final acceptance.",
)


class OperationalOutcomeValidationError(ValueError):
    """A closed operational-outcome contract failed validation."""

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


def digest_ref(ref_id: str, material: Any | None = None) -> dict[str, Any]:
    basis = {"ref_id": ref_id} if material is None else material
    return {"ref_id": ref_id, "digest": digest_value(basis)}


def _without(value: Mapping[str, Any], *fields: str) -> dict[str, Any]:
    result = copy.deepcopy(dict(value))
    for field in fields:
        result.pop(field, None)
    return result


def _sorted_dicts(values: Iterable[Mapping[str, Any]], *keys: str) -> list[dict[str, Any]]:
    return sorted(
        (copy.deepcopy(dict(item)) for item in values),
        key=lambda item: tuple(str(item.get(key, "")) for key in keys),
    )


def _policy_ref(policy: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "ref_id": policy["policy_id"],
        "version": policy["version"],
        "digest": copy.deepcopy(policy["policy_digest"]),
    }


def _record_digest(value: Mapping[str, Any], field: str) -> dict[str, str]:
    return digest_value(_without(value, field))


def _decision_ref(decision: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if decision is None:
        return None
    return {
        "decision_id": decision["decision_id"],
        "decision_digest": copy.deepcopy(decision["decision_digest"]),
    }


def _enrollment_material(participant: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: copy.deepcopy(value)
        for key, value in participant.items()
        if key not in {"disposition", "participant_digest", "enrollment_digest"}
    }


def _parse_time(value: str) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith(("Z", "z")) else value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"timestamp lacks timezone: {value}")
    return parsed


def _duplicates(values: Iterable[str]) -> set[str]:
    seen: set[str] = set()
    duplicate: set[str] = set()
    for value in values:
        if value in seen:
            duplicate.add(value)
        seen.add(value)
    return duplicate


def build_outcome_policy(
    *,
    policy_id: str,
    version: str,
    status: str,
    decision_record_ref: str | None,
    evidence_class: str,
    target_population: Mapping[str, Any],
    intended_use: Mapping[str, Any],
    roles: Iterable[Mapping[str, Any]],
    task_strata: Iterable[Mapping[str, Any]],
    baseline_ref: Mapping[str, Any],
    candidate_ref: Mapping[str, Any],
    axis_policies: Iterable[Mapping[str, Any]],
    confidence_level: float,
    minimum_sample: Mapping[str, int],
    privacy_consent: Mapping[str, Any],
    stop_conditions: Iterable[str],
) -> dict[str, Any]:
    """Build but do not adopt a human-owned outcome evaluation policy."""

    population = copy.deepcopy(dict(target_population))
    population["inclusion_criteria"] = sorted(set(population["inclusion_criteria"]))
    population["exclusion_criteria"] = sorted(set(population["exclusion_criteria"]))
    population["population_digest"] = digest_value(population)
    material = {
        "policy_id": policy_id,
        "version": version,
        "owner_kind": "human",
        "status": status,
        "decision_record_ref": decision_record_ref,
        "evidence_class": evidence_class,
        "target_population": population,
        "intended_use": copy.deepcopy(dict(intended_use)),
        "roles": _sorted_dicts(roles, "role_id"),
        "task_strata": _sorted_dicts(task_strata, "axis", "stratum_id"),
        "arm_contract": {
            "baseline": copy.deepcopy(dict(baseline_ref)),
            "candidate": copy.deepcopy(dict(candidate_ref)),
            "same_task_set_required": True,
            "cross_arm_participant_reuse_prohibited": True,
        },
        "axis_policies": _sorted_dicts(axis_policies, "axis"),
        "confidence_level": confidence_level,
        "minimum_sample": copy.deepcopy(dict(minimum_sample)),
        "privacy_consent": copy.deepcopy(dict(privacy_consent)),
        "stop_conditions": sorted(set(stop_conditions)),
    }
    return {**material, "policy_digest": digest_value(material)}


def build_human_policy_decision(
    *,
    decision_id: str,
    decision_type: str,
    human_actor_ref: str,
    policy: Mapping[str, Any],
    rationale: str,
    evidence_refs: Iterable[Mapping[str, Any]],
    recorded_at: str,
) -> dict[str, Any]:
    decision = "adopt" if decision_type == "adopt_policy" else "retire"
    material = {
        "decision_id": decision_id,
        "decision_type": decision_type,
        "issuer_kind": "human",
        "human_actor_ref": human_actor_ref,
        "policy_ref": _policy_ref(policy),
        "decision": decision,
        "rationale": rationale,
        "evidence_refs": _sorted_dicts(evidence_refs, "ref_id"),
        "recorded_at": recorded_at,
    }
    return {**material, "decision_digest": digest_value(material)}


def build_outcome_task(
    *,
    task_id: str,
    axis: str,
    target_role_id: str,
    stratum_id: str,
    correct_answer_ref: Mapping[str, Any],
    rubric_ref: Mapping[str, Any],
    baseline_material_ref: Mapping[str, Any],
    candidate_material_ref: Mapping[str, Any],
    baseline_arm_ref: Mapping[str, Any],
    candidate_arm_ref: Mapping[str, Any],
    prohibited_decisions: Iterable[str],
    required_escalation: bool,
    unresolved_must_be_preserved: bool,
    prohibited_repair_shortcuts: Iterable[str],
    sealed_at: str,
) -> dict[str, Any]:
    material = {
        "task_id": task_id,
        "axis": axis,
        "target_role_id": target_role_id,
        "stratum_id": stratum_id,
        "correct_answer_ref": copy.deepcopy(dict(correct_answer_ref)),
        "rubric_ref": copy.deepcopy(dict(rubric_ref)),
        "arm_materials": {
            "baseline": {
                "material_ref": copy.deepcopy(dict(baseline_material_ref)),
                "derived_from_arm_ref": copy.deepcopy(dict(baseline_arm_ref)),
            },
            "candidate": {
                "material_ref": copy.deepcopy(dict(candidate_material_ref)),
                "derived_from_arm_ref": copy.deepcopy(dict(candidate_arm_ref)),
            },
        },
        "prohibited_decisions": sorted(set(prohibited_decisions)),
        "required_escalation": required_escalation,
        "unresolved_must_be_preserved": unresolved_must_be_preserved,
        "prohibited_repair_shortcuts": sorted(set(prohibited_repair_shortcuts)),
        "sealed_at": sealed_at,
    }
    return {**material, "task_digest": digest_value(material)}


def build_outcome_task_set(
    *,
    policy: Mapping[str, Any],
    adoption_decision: Mapping[str, Any] | None,
    task_set_id: str,
    sealed_at: str,
    tasks: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Bind the exact task denominator before sessions are recorded."""

    task_values = _sorted_dicts(tasks, "axis", "task_id")
    material = {
        "task_set_id": task_set_id,
        "policy_ref": _policy_ref(policy),
        "adoption_decision_ref": _decision_ref(adoption_decision),
        "sealed_at": sealed_at,
        "task_refs": [
            {
                "task_id": item["task_id"],
                "task_digest": copy.deepcopy(item["task_digest"]),
            }
            for item in task_values
        ],
    }
    return {**material, "task_set_digest": digest_value(material)}


def build_participant(
    *,
    participant_id: str,
    role_id: str,
    population_id: str,
    assigned_arm: str,
    cluster_id: str,
    source_kind: str,
    consent_status: str,
    consent_evidence_ref: Mapping[str, Any],
    consent_scope_ref: Mapping[str, Any],
    consent_recorded_at: str,
    enrolled_at: str,
    disposition_status: str = "completed",
    disposition_reason: str = "completed_protocol",
    disposition_evidence_ref: Mapping[str, Any] | None = None,
    disposition_recorded_at: str | None = None,
) -> dict[str, Any]:
    enrollment = {
        "participant_id": participant_id,
        "pseudonymized": True,
        "raw_identifiers_present": False,
        "role_id": role_id,
        "population_id": population_id,
        "assigned_arm": assigned_arm,
        "cluster_id": cluster_id,
        "source_kind": source_kind,
        "enrolled_at": enrolled_at,
        "consent": {
            "status": consent_status,
            "evidence_ref": copy.deepcopy(dict(consent_evidence_ref)),
            "scope_ref": copy.deepcopy(dict(consent_scope_ref)),
            "recorded_at": consent_recorded_at,
        },
    }
    material = {
        **enrollment,
        "enrollment_digest": digest_value(enrollment),
        "disposition": {
            "status": disposition_status,
            "reason": disposition_reason,
            "evidence_ref": (
                copy.deepcopy(dict(disposition_evidence_ref))
                if disposition_evidence_ref
                else None
            ),
            "recorded_at": disposition_recorded_at or consent_recorded_at,
        },
    }
    return {**material, "participant_digest": digest_value(material)}


def build_enrollment_manifest(
    *,
    manifest_id: str,
    policy: Mapping[str, Any],
    task_set_digest: Mapping[str, Any],
    sealed_at: str,
    participants: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    participant_values = _sorted_dicts(participants, "participant_id")
    material = {
        "manifest_id": manifest_id,
        "policy_ref": _policy_ref(policy),
        "task_set_digest": copy.deepcopy(dict(task_set_digest)),
        "sealed_at": sealed_at,
        "participant_refs": [
            {
                "participant_id": item["participant_id"],
                "enrollment_digest": copy.deepcopy(item["enrollment_digest"]),
                "role_id": item["role_id"],
                "arm": item["assigned_arm"],
                "cluster_id": item["cluster_id"],
            }
            for item in participant_values
        ],
    }
    return {**material, "manifest_digest": digest_value(material)}


def build_outcome_session(
    *,
    session_id: str,
    participant: Mapping[str, Any],
    policy: Mapping[str, Any],
    task_set_digest: Mapping[str, Any],
    started_at: str,
    completed_at: str,
    prior_task_exposure: bool = False,
    training_task_refs: Iterable[str] = (),
) -> dict[str, Any]:
    material = {
        "session_id": session_id,
        "participant_id": participant["participant_id"],
        "participant_digest": copy.deepcopy(participant["participant_digest"]),
        "role_id": participant["role_id"],
        "arm": participant["assigned_arm"],
        "policy_ref": _policy_ref(policy),
        "task_set_digest": copy.deepcopy(dict(task_set_digest)),
        "started_at": started_at,
        "completed_at": completed_at,
        "prior_task_exposure": prior_task_exposure,
        "training_task_refs": sorted(set(training_task_refs)),
    }
    return {**material, "session_digest": digest_value(material)}


def build_outcome_observation(
    *,
    observation_id: str,
    session: Mapping[str, Any],
    task: Mapping[str, Any],
    response_ref: Mapping[str, Any] | None,
    repair_artifact_ref: Mapping[str, Any] | None,
    repair_verification_refs: Iterable[Mapping[str, Any]],
    repair_shortcuts_used: Iterable[str],
    regression_status: str,
    unresolved_preserved: bool,
    routing_destination: str,
    escalation_chosen: bool,
    decision_claim: str,
    authority_claims: Iterable[str],
    self_reported_success: bool,
    self_report_ref: Mapping[str, Any] | None,
    started_at: str,
    completed_at: str,
    elapsed_seconds: float,
    effort_units: float,
    interruptions: int = 0,
) -> dict[str, Any]:
    arm = str(session["arm"])
    material = {
        "observation_id": observation_id,
        "session_id": session["session_id"],
        "session_digest": copy.deepcopy(session["session_digest"]),
        "participant_id": session["participant_id"],
        "role_id": session["role_id"],
        "arm": arm,
        "axis": task["axis"],
        "task_id": task["task_id"],
        "task_digest": copy.deepcopy(task["task_digest"]),
        "material_ref": copy.deepcopy(task["arm_materials"][arm]["material_ref"]),
        "response_ref": copy.deepcopy(dict(response_ref)) if response_ref else None,
        "repair_artifact_ref": (
            copy.deepcopy(dict(repair_artifact_ref)) if repair_artifact_ref else None
        ),
        "repair_verification_refs": _sorted_dicts(
            repair_verification_refs, "ref_id"
        ),
        "repair_shortcuts_used": sorted(set(repair_shortcuts_used)),
        "regression_status": regression_status,
        "unresolved_preserved": unresolved_preserved,
        "response_projection": {
            "routing_destination": routing_destination,
            "escalation_chosen": escalation_chosen,
            "decision_claim": decision_claim,
            "authority_claims": sorted(set(authority_claims)),
        },
        "participant_self_report": {
            "claimed_success": self_reported_success,
            "note_ref": copy.deepcopy(dict(self_report_ref)) if self_report_ref else None,
        },
        "started_at": started_at,
        "completed_at": completed_at,
        "effort": {
            "elapsed_seconds": elapsed_seconds,
            "effort_units": effort_units,
            "interruptions": interruptions,
        },
    }
    return {**material, "observation_digest": digest_value(material)}


def build_grader(
    *,
    grader_id: str,
    role: str,
    independence_group: str,
    relationship_to_artifact: str,
    blind_to_arm: bool,
    blind_to_participant_identity: bool,
    conflict_statement: str,
) -> dict[str, Any]:
    material = {
        "grader_id": grader_id,
        "grader_kind": "human",
        "role": role,
        "independence_group": independence_group,
        "relationship_to_artifact": relationship_to_artifact,
        "blind_to_arm": blind_to_arm,
        "blind_to_participant_identity": blind_to_participant_identity,
        "conflict_statement": conflict_statement,
    }
    return {**material, "grader_digest": digest_value(material)}


def build_outcome_score(
    *,
    score_id: str,
    observation: Mapping[str, Any],
    grader: Mapping[str, Any],
    rubric_ref: Mapping[str, Any],
    criteria: Mapping[str, bool],
    recorded_at: str,
    blind_to_arm: bool = True,
    participant_self_report_used: bool = False,
) -> dict[str, Any]:
    material = {
        "score_id": score_id,
        "observation_id": observation["observation_id"],
        "observation_digest": copy.deepcopy(observation["observation_digest"]),
        "grader_id": grader["grader_id"],
        "grader_digest": copy.deepcopy(grader["grader_digest"]),
        "rubric_ref": copy.deepcopy(dict(rubric_ref)),
        "blind_to_arm": blind_to_arm,
        "participant_self_report_used": participant_self_report_used,
        "criteria": [
            {"metric_id": metric_id, "result": bool(result)}
            for metric_id, result in sorted(criteria.items())
        ],
        "recorded_at": recorded_at,
    }
    return {**material, "score_digest": digest_value(material)}


def build_outcome_adjudication(
    *,
    adjudication_id: str,
    observation: Mapping[str, Any],
    metric_id: str,
    basis_score_refs: Iterable[str],
    adjudicator: Mapping[str, Any],
    resolved_result: bool,
    rationale: str,
    recorded_at: str,
    blind_to_arm: bool = True,
) -> dict[str, Any]:
    material = {
        "adjudication_id": adjudication_id,
        "observation_id": observation["observation_id"],
        "observation_digest": copy.deepcopy(observation["observation_digest"]),
        "metric_id": metric_id,
        "basis_score_refs": sorted(set(basis_score_refs)),
        "adjudicator_id": adjudicator["grader_id"],
        "adjudicator_digest": copy.deepcopy(adjudicator["grader_digest"]),
        "blind_to_arm": blind_to_arm,
        "resolved_result": resolved_result,
        "rationale": rationale,
        "recorded_at": recorded_at,
    }
    return {**material, "adjudication_digest": digest_value(material)}


def wilson_interval(successes: int, total: int, confidence: float) -> dict[str, Any]:
    if total <= 0:
        return {"point": None, "lower": None, "upper": None, "confidence": confidence}
    z = NormalDist().inv_cdf(0.5 + confidence / 2.0)
    p = successes / total
    denominator = 1.0 + (z * z / total)
    center = (p + (z * z / (2.0 * total))) / denominator
    radius = (
        z
        * math.sqrt((p * (1.0 - p) / total) + (z * z / (4.0 * total * total)))
        / denominator
    )
    return {
        "point": p,
        "lower": max(0.0, center - radius),
        "upper": min(1.0, center + radius),
        "confidence": confidence,
    }


def _bounded_mean(values: Sequence[float], cap: float, confidence: float) -> dict[str, Any]:
    if not values:
        return {
            "count": 0,
            "mean": None,
            "lower": None,
            "upper": None,
            "cap": cap,
            "confidence": confidence,
            "basis": "two_sided_hoeffding_bound",
        }
    mean = sum(values) / len(values)
    alpha = 1.0 - confidence
    radius = cap * math.sqrt(math.log(2.0 / alpha) / (2.0 * len(values)))
    return {
        "count": len(values),
        "mean": mean,
        "lower": max(0.0, mean - radius),
        "upper": min(cap, mean + radius),
        "cap": cap,
        "confidence": confidence,
        "basis": "two_sided_hoeffding_bound",
    }


def _matching_policy_decision(
    policy: Mapping[str, Any], decisions: Sequence[Mapping[str, Any]]
) -> bool:
    matched, _ = _policy_decision_resolution(policy, decisions)
    return matched


def _policy_decision_resolution(
    policy: Mapping[str, Any], decisions: Sequence[Mapping[str, Any]]
) -> tuple[bool, str | None]:
    decision_ref = policy["decision_record_ref"]
    if not decision_ref:
        return False, "policy_decision_missing_or_mismatched"
    policy_ref = _policy_ref(policy)
    relevant = [item for item in decisions if item["policy_ref"] == policy_ref]
    matches = [item for item in relevant if item["decision_id"] == decision_ref]
    if len(matches) != 1 or not relevant:
        return False, "policy_decision_missing_or_mismatched"
    by_time: dict[datetime, list[Mapping[str, Any]]] = {}
    for decision in relevant:
        by_time.setdefault(_parse_time(str(decision["recorded_at"])), []).append(
            decision
        )
    if any(len(values) != 1 for values in by_time.values()):
        return False, "policy_decision_conflict"
    latest = max(relevant, key=lambda item: _parse_time(str(item["recorded_at"])))
    expected_type = "adopt_policy" if policy["status"] == "adopted" else "retire_policy"
    expected_value = "adopt" if policy["status"] == "adopted" else "retire"
    if latest["decision_id"] != decision_ref:
        return False, "policy_decision_superseded"
    decision = latest
    matched = (
        decision["decision_type"] == expected_type
        and decision["decision"] == expected_value
        and decision["policy_ref"] == policy_ref
    )
    return (
        (True, None)
        if matched
        else (False, "policy_decision_missing_or_mismatched")
    )


def _criteria_map(score: Mapping[str, Any]) -> dict[str, bool]:
    return {str(item["metric_id"]): bool(item["result"]) for item in score["criteria"]}


def _resolved_outcomes(
    *,
    observations: Sequence[Mapping[str, Any]],
    scores: Sequence[Mapping[str, Any]],
    adjudications: Sequence[Mapping[str, Any]],
) -> tuple[dict[tuple[str, str], bool], list[dict[str, Any]]]:
    scores_by_observation: dict[str, list[Mapping[str, Any]]] = {}
    for score in scores:
        scores_by_observation.setdefault(str(score["observation_id"]), []).append(score)
    adjudication_by_key = {
        (str(item["observation_id"]), str(item["metric_id"])): item
        for item in adjudications
    }
    resolved: dict[tuple[str, str], bool] = {}
    disagreements: list[dict[str, Any]] = []
    for observation in observations:
        observation_id = str(observation["observation_id"])
        observation_scores = scores_by_observation.get(observation_id, [])
        for metric_id in METRICS_BY_AXIS[str(observation["axis"])]:
            values = {
                _criteria_map(score)[metric_id]
                for score in observation_scores
                if metric_id in _criteria_map(score)
            }
            key = (observation_id, metric_id)
            if len(values) == 1:
                resolved[key] = values.pop()
            else:
                adjudication = adjudication_by_key.get(key)
                resolved[key] = (
                    bool(adjudication["resolved_result"])
                    if adjudication is not None
                    else False
                )
                disagreements.append(
                    {
                        "observation_id": observation_id,
                        "metric_id": metric_id,
                        "score_refs": sorted(
                            str(score["score_id"]) for score in observation_scores
                        ),
                        "adjudication_ref": (
                            adjudication["adjudication_id"]
                            if adjudication is not None
                            else "missing-adjudication"
                        ),
                        "resolved_result": resolved[key],
                    }
                )
    return resolved, sorted(
        disagreements, key=lambda item: (item["observation_id"], item["metric_id"])
    )


def _metric_policy(policy: Mapping[str, Any], axis: str) -> Mapping[str, Any]:
    return next(item for item in policy["axis_policies"] if item["axis"] == axis)


def _compute_axis_result(
    *,
    axis: str,
    policy: Mapping[str, Any],
    decisions: Sequence[Mapping[str, Any]],
    tasks: Sequence[Mapping[str, Any]],
    participants: Sequence[Mapping[str, Any]],
    observations: Sequence[Mapping[str, Any]],
    scores: Sequence[Mapping[str, Any]],
    adjudications: Sequence[Mapping[str, Any]],
    task_set_digest: Mapping[str, Any],
) -> dict[str, Any]:
    confidence = float(policy["confidence_level"])
    axis_policy = _metric_policy(policy, axis)
    task_values = [item for item in tasks if item["axis"] == axis]
    observation_values = [item for item in observations if item["axis"] == axis]
    resolved, all_disagreements = _resolved_outcomes(
        observations=observations,
        scores=scores,
        adjudications=adjudications,
    )
    disagreements = [
        item
        for item in all_disagreements
        if any(
            observation["observation_id"] == item["observation_id"]
            for observation in observation_values
        )
    ]
    threshold_by_metric = {
        str(item["metric_id"]): item for item in axis_policy["metric_thresholds"]
    }
    arm_metrics: dict[str, Any] = {}
    axis_role_ids = {str(item["target_role_id"]) for item in task_values}
    participants_by_id = {str(item["participant_id"]): item for item in participants}
    for arm in ARMS:
        arm_observations = [item for item in observation_values if item["arm"] == arm]
        enrolled_participants = [
            item
            for item in participants
            if item["assigned_arm"] == arm and item["role_id"] in axis_role_ids
        ]
        observed_participant_ids = {
            str(item["participant_id"]) for item in arm_observations
        }
        observed_cluster_ids = sorted(
            {
                str(participants_by_id[participant_id]["cluster_id"])
                for participant_id in observed_participant_ids
            }
        )
        metric_rates: list[dict[str, Any]] = []
        cluster_losses: list[float] = []
        cluster_effort_seconds: list[float] = []
        cluster_effort_units: list[float] = []
        cluster_observations: dict[str, list[Mapping[str, Any]]] = {}
        for observation in arm_observations:
            cluster_id = str(
                participants_by_id[str(observation["participant_id"])]["cluster_id"]
            )
            cluster_observations.setdefault(cluster_id, []).append(observation)
        for cluster_id in observed_cluster_ids:
            values = cluster_observations[cluster_id]
            cluster_losses.append(
                max(
                    sum(
                        float(threshold_by_metric[metric_id]["error_cost"])
                        for metric_id in METRICS_BY_AXIS[axis]
                        if not resolved[(str(observation["observation_id"]), metric_id)]
                    )
                    for observation in values
                )
            )
            cluster_effort_seconds.append(
                sum(float(item["effort"]["elapsed_seconds"]) for item in values)
                / len(values)
            )
            cluster_effort_units.append(
                sum(float(item["effort"]["effort_units"]) for item in values)
                / len(values)
            )
        for metric_id in METRICS_BY_AXIS[axis]:
            successes = sum(
                all(
                    resolved[(str(observation["observation_id"]), metric_id)]
                    for observation in cluster_observations[cluster_id]
                )
                for cluster_id in observed_cluster_ids
            )
            denominator = len(observed_cluster_ids)
            errors = denominator - successes
            metric_rates.append(
                {
                    "metric_id": metric_id,
                    "success_count": successes,
                    "error_count": errors,
                    "denominator": denominator,
                    "success_rate": wilson_interval(successes, denominator, confidence),
                    "error_rate": wilson_interval(errors, denominator, confidence),
                }
            )
        maximum_loss = sum(
            float(item["error_cost"])
            for item in axis_policy["metric_thresholds"]
        )
        disposition_counts = {
            status: sum(
                item["disposition"]["status"] == status
                for item in enrolled_participants
            )
            for status in (
                "completed",
                "withdrawn",
                "protocol_violation",
                "missing",
                "excluded",
            )
        }
        dropout_count = len(enrolled_participants) - disposition_counts["completed"]
        arm_metrics[arm] = {
            "observation_count": len(arm_observations),
            "participant_count": len(observed_participant_ids),
            "cluster_count": len(observed_cluster_ids),
            "analysis_unit": "participant_cluster",
            "metric_rates": metric_rates,
            "weighted_error_loss": _bounded_mean(
                cluster_losses, maximum_loss, confidence
            ),
            "effort_seconds": _bounded_mean(
                cluster_effort_seconds,
                float(axis_policy["effort_cap_seconds"]),
                confidence,
            ),
            "effort_units": _bounded_mean(
                cluster_effort_units,
                float(axis_policy["effort_cap_units"]),
                confidence,
            ),
            "enrollment": {
                "enrolled_participant_count": len(enrolled_participants),
                "completed_participant_count": disposition_counts["completed"],
                "dropout_count": dropout_count,
                "dropout_rate": wilson_interval(
                    dropout_count, len(enrolled_participants), confidence
                ),
                "disposition_counts": [
                    {"status": status, "count": count}
                    for status, count in sorted(disposition_counts.items())
                ],
            },
            "stratum_counts": [
                {
                    "stratum_id": stratum["stratum_id"],
                    "observation_count": len(
                        [
                            observation
                            for observation in arm_observations
                            if next(
                                task
                                for task in task_values
                                if task["task_id"] == observation["task_id"]
                            )["stratum_id"]
                            == stratum["stratum_id"]
                        ]
                    ),
                    "participant_count": len(
                        {
                            str(observation["participant_id"])
                            for observation in arm_observations
                            if next(
                                task
                                for task in task_values
                                if task["task_id"] == observation["task_id"]
                            )["stratum_id"]
                            == stratum["stratum_id"]
                        }
                    ),
                    "cluster_count": len(
                        {
                            str(
                                participants_by_id[str(observation["participant_id"])][
                                    "cluster_id"
                                ]
                            )
                            for observation in arm_observations
                            if next(
                                task
                                for task in task_values
                                if task["task_id"] == observation["task_id"]
                            )["stratum_id"]
                            == stratum["stratum_id"]
                        }
                    ),
                }
                for stratum in policy["task_strata"]
                if stratum["axis"] == axis and stratum["required"]
            ],
        }

    criteria: list[dict[str, Any]] = []
    candidate_by_metric = {
        item["metric_id"]: item for item in arm_metrics["candidate"]["metric_rates"]
    }
    for metric_id in METRICS_BY_AXIS[axis]:
        threshold = threshold_by_metric[metric_id]
        metric = candidate_by_metric[metric_id]
        criteria.extend(
            [
                {
                    "criterion": "error_rate_wilson_upper",
                    "metric_id": metric_id,
                    "observed": metric["error_rate"]["upper"],
                    "threshold": threshold["max_error_rate"],
                    "comparison": "less_than_or_equal",
                    "basis": "wilson_upper_bound",
                    "passed": metric["error_rate"]["upper"]
                    <= threshold["max_error_rate"],
                },
                {
                    "criterion": "success_rate_wilson_lower",
                    "metric_id": metric_id,
                    "observed": metric["success_rate"]["lower"],
                    "threshold": threshold["min_success_rate"],
                    "comparison": "greater_than_or_equal",
                    "basis": "wilson_lower_bound",
                    "passed": metric["success_rate"]["lower"]
                    >= threshold["min_success_rate"],
                },
            ]
        )
    candidate_loss = arm_metrics["candidate"]["weighted_error_loss"]
    baseline_loss = arm_metrics["baseline"]["weighted_error_loss"]
    improvement_lower = baseline_loss["lower"] - candidate_loss["upper"]
    criteria.extend(
        [
            {
                "criterion": "weighted_error_loss_upper",
                "metric_id": None,
                "observed": candidate_loss["upper"],
                "threshold": axis_policy["max_weighted_error_loss"],
                "comparison": "less_than_or_equal",
                "basis": "hoeffding_upper_bound",
                "passed": candidate_loss["upper"]
                <= axis_policy["max_weighted_error_loss"],
            },
            {
                "criterion": "weighted_loss_improvement_lower",
                "metric_id": None,
                "observed": improvement_lower,
                "threshold": axis_policy["min_weighted_loss_improvement"],
                "comparison": "greater_than_or_equal",
                "basis": "baseline_hoeffding_lower_minus_candidate_hoeffding_upper",
                "passed": improvement_lower
                >= axis_policy["min_weighted_loss_improvement"],
            },
            {
                "criterion": "effort_seconds_upper",
                "metric_id": None,
                "observed": arm_metrics["candidate"]["effort_seconds"]["upper"],
                "threshold": axis_policy["max_effort_seconds"],
                "comparison": "less_than_or_equal",
                "basis": "hoeffding_upper_bound",
                "passed": arm_metrics["candidate"]["effort_seconds"]["upper"]
                <= axis_policy["max_effort_seconds"],
            },
            {
                "criterion": "effort_units_upper",
                "metric_id": None,
                "observed": arm_metrics["candidate"]["effort_units"]["upper"],
                "threshold": axis_policy["max_effort_units"],
                "comparison": "less_than_or_equal",
                "basis": "hoeffding_upper_bound",
                "passed": arm_metrics["candidate"]["effort_units"]["upper"]
                <= axis_policy["max_effort_units"],
            },
            {
                "criterion": "baseline_dropout_rate_wilson_upper",
                "metric_id": None,
                "observed": arm_metrics["baseline"]["enrollment"][
                    "dropout_rate"
                ]["upper"],
                "threshold": axis_policy["max_dropout_rate"],
                "comparison": "less_than_or_equal",
                "basis": "wilson_upper_bound",
                "passed": arm_metrics["baseline"]["enrollment"][
                    "dropout_rate"
                ]["upper"]
                <= axis_policy["max_dropout_rate"],
            },
            {
                "criterion": "candidate_dropout_rate_wilson_upper",
                "metric_id": None,
                "observed": arm_metrics["candidate"]["enrollment"][
                    "dropout_rate"
                ]["upper"],
                "threshold": axis_policy["max_dropout_rate"],
                "comparison": "less_than_or_equal",
                "basis": "wilson_upper_bound",
                "passed": arm_metrics["candidate"]["enrollment"][
                    "dropout_rate"
                ]["upper"]
                <= axis_policy["max_dropout_rate"],
            },
        ]
    )
    reasons: list[str] = []
    if policy["status"] != "adopted":
        reasons.append("policy_not_adopted")
    elif not _matching_policy_decision(policy, decisions):
        reasons.append("policy_decision_missing_or_mismatched")
    if not all(item["passed"] for item in criteria):
        reasons.append("conservative_thresholds_not_met")
    minimum = policy["minimum_sample"]
    for arm in ARMS:
        if (
            arm_metrics[arm]["observation_count"]
            < minimum["per_axis_arm_observations"]
        ):
            reasons.append("minimum_sample_not_met")
        if (
            arm_metrics[arm]["participant_count"]
            < minimum["per_axis_arm_participants"]
        ):
            reasons.append("minimum_participant_sample_not_met")
        if arm_metrics[arm]["cluster_count"] < minimum["per_axis_arm_clusters"]:
            reasons.append("independent_cluster_sample_not_met")
        if any(
            item["participant_count"]
            < minimum["per_required_stratum_participants"]
            for item in arm_metrics[arm]["stratum_counts"]
        ):
            reasons.append("required_stratum_participant_sample_not_met")
    axis_participants = {
        str(item["participant_id"])
        for item in observation_values
    }
    if policy["evidence_class"] != "operational_participant" or any(
        participants_by_id[participant_id]["source_kind"]
        != "operational_participant"
        for participant_id in axis_participants
    ):
        reasons.append("declared_synthetic_protocol_only")
    reasons = sorted(set(reasons))
    claim_scope = (
        "declared_records_only"
        if not reasons
        else (
            "declared_synthetic_protocol_only"
            if "declared_synthetic_protocol_only" in reasons
            else "declared_protocol_not_established"
        )
    )
    material = {
        "axis": axis,
        "status": "meets_policy_for_declared_records" if not reasons else "not_established",
        "claim_scope": claim_scope,
        "task_set_digest": copy.deepcopy(dict(task_set_digest)),
        "arm_metrics": arm_metrics,
        "unpaired_arm_comparison": {
            "baseline_weighted_loss_lower": baseline_loss["lower"],
            "candidate_weighted_loss_upper": candidate_loss["upper"],
            "improvement_lower": improvement_lower,
            "minimum_required_improvement": axis_policy[
                "min_weighted_loss_improvement"
            ],
            "basis": "baseline_hoeffding_lower_minus_candidate_hoeffding_upper",
            "passed": improvement_lower
            >= axis_policy["min_weighted_loss_improvement"],
        },
        "threshold_assessment": {
            "status": "passed" if all(item["passed"] for item in criteria) else "failed",
            "criteria": criteria,
            "confidence_level": confidence,
        },
        "disagreements": disagreements,
        "reasons": reasons,
        "limitations": list(_AXIS_LIMITATIONS[axis]),
        "cross_axis_inference_prohibited": True,
    }
    return {**material, "result_digest": digest_value(material)}


def _compute_results(
    *,
    policy: Mapping[str, Any],
    decisions: Sequence[Mapping[str, Any]],
    tasks: Sequence[Mapping[str, Any]],
    participants: Sequence[Mapping[str, Any]],
    observations: Sequence[Mapping[str, Any]],
    scores: Sequence[Mapping[str, Any]],
    adjudications: Sequence[Mapping[str, Any]],
    task_set_digest: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        axis: _compute_axis_result(
            axis=axis,
            policy=policy,
            decisions=decisions,
            tasks=tasks,
            participants=participants,
            observations=observations,
            scores=scores,
            adjudications=adjudications,
            task_set_digest=task_set_digest,
        )
        for axis in AXES
    }


def _bounded_input_values(
    values: Iterable[Any], *, maximum: int, location: str
) -> list[Any]:
    """Materialize at most the public contract's declared denominator."""

    result: list[Any] = []
    for item in values:
        if len(result) >= maximum:
            raise OperationalOutcomeValidationError(
                (
                    {
                        "code": "input_container_width_exceeded",
                        "location": location,
                        "message": f"input container cannot exceed {maximum} items",
                    },
                )
            )
        result.append(item)
    return result


def _precompute_coverage_errors(
    *, tasks: Sequence[Mapping[str, Any]], observations: Sequence[Mapping[str, Any]]
) -> list[dict[str, str]]:
    """Reject empty axis/cell denominators before interval arithmetic."""

    errors: list[dict[str, str]] = []
    for axis in AXES:
        if not any(item.get("axis") == axis for item in tasks):
            _add(
                errors,
                "axis_task_coverage_missing",
                "$.tasks",
                f"at least one task is required for {axis}",
            )
        for arm in ARMS:
            if not any(
                item.get("axis") == axis and item.get("arm") == arm
                for item in observations
            ):
                _add(
                    errors,
                    "axis_arm_observation_coverage_missing",
                    "$.observations",
                    f"at least one observation is required for {axis}/{arm}",
                )
    return errors


def build_operational_outcome_evaluation(
    *,
    policy: Mapping[str, Any],
    human_decision_records: Iterable[Mapping[str, Any]],
    task_set: Mapping[str, Any],
    enrollment_manifest: Mapping[str, Any],
    tasks: Iterable[Mapping[str, Any]],
    participants: Iterable[Mapping[str, Any]],
    sessions: Iterable[Mapping[str, Any]],
    observations: Iterable[Mapping[str, Any]],
    graders: Iterable[Mapping[str, Any]],
    scores: Iterable[Mapping[str, Any]],
    adjudications: Iterable[Mapping[str, Any]],
    limitations: Iterable[str] = _DEFAULT_LIMITATIONS,
) -> dict[str, Any]:
    """Build and validate a fully replayable two-axis evaluation bundle."""

    raw_values = {
        "policy": policy,
        "human_decision_records": _bounded_input_values(
            human_decision_records,
            maximum=MAX_DECISIONS,
            location="$.human_decision_records",
        ),
        "task_set": task_set,
        "enrollment_manifest": enrollment_manifest,
        "tasks": _bounded_input_values(
            tasks, maximum=MAX_TASKS, location="$.tasks"
        ),
        "participants": _bounded_input_values(
            participants, maximum=MAX_PARTICIPANTS, location="$.participants"
        ),
        "sessions": _bounded_input_values(
            sessions, maximum=MAX_SESSIONS, location="$.sessions"
        ),
        "observations": _bounded_input_values(
            observations, maximum=MAX_OBSERVATIONS, location="$.observations"
        ),
        "graders": _bounded_input_values(
            graders, maximum=MAX_GRADERS, location="$.graders"
        ),
        "scores": _bounded_input_values(
            scores, maximum=MAX_SCORES, location="$.scores"
        ),
        "adjudications": _bounded_input_values(
            adjudications,
            maximum=MAX_ADJUDICATIONS,
            location="$.adjudications",
        ),
        "limitations": _bounded_input_values(
            limitations, maximum=MAX_LIMITATIONS, location="$.limitations"
        ),
    }
    structure_errors = _pre_schema_structure_errors(raw_values)
    if structure_errors:
        raise OperationalOutcomeValidationError(structure_errors)
    coverage_errors = _precompute_coverage_errors(
        tasks=raw_values["tasks"], observations=raw_values["observations"]
    )
    if coverage_errors:
        raise OperationalOutcomeValidationError(coverage_errors)

    policy_value = copy.deepcopy(dict(policy))
    task_values = _sorted_dicts(raw_values["tasks"], "axis", "task_id")
    participant_values = _sorted_dicts(raw_values["participants"], "participant_id")
    session_values = _sorted_dicts(raw_values["sessions"], "session_id")
    observation_values = _sorted_dicts(raw_values["observations"], "observation_id")
    grader_values = _sorted_dicts(raw_values["graders"], "grader_id")
    score_values = _sorted_dicts(raw_values["scores"], "score_id")
    adjudication_values = _sorted_dicts(
        raw_values["adjudications"], "adjudication_id"
    )
    decision_values = _sorted_dicts(
        raw_values["human_decision_records"], "decision_id"
    )
    task_set_value = copy.deepcopy(dict(task_set))
    enrollment_manifest_value = copy.deepcopy(dict(enrollment_manifest))
    results = _compute_results(
        policy=policy_value,
        decisions=decision_values,
        tasks=task_values,
        participants=participant_values,
        observations=observation_values,
        scores=score_values,
        adjudications=adjudication_values,
        task_set_digest=task_set_value["task_set_digest"],
    )
    body = {
        "schema_version": SCHEMA_VERSION,
        "policy": policy_value,
        "human_decision_records": decision_values,
        "task_set": task_set_value,
        "enrollment_manifest": enrollment_manifest_value,
        "tasks": task_values,
        "participants": participant_values,
        "sessions": session_values,
        "observations": observation_values,
        "graders": grader_values,
        "scores": score_values,
        "adjudications": adjudication_values,
        "axis_results": results,
        "non_inference_axes": copy.deepcopy(_NON_INFERENCE),
        "authority_boundary": copy.deepcopy(_AUTHORITY_BOUNDARY),
        "limitations": sorted(
            set(_DEFAULT_LIMITATIONS) | set(raw_values["limitations"])
        ),
    }
    evaluation_id = "operational-outcome-evaluation." + canonical_sha256(body)
    material = {"evaluation_id": evaluation_id, **body}
    bundle = {**material, "bundle_digest": digest_value(material)}
    validate_operational_outcome_evaluation(bundle)
    return bundle


@lru_cache(maxsize=1)
def _schema_validator() -> Draft202012Validator:
    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _add(errors: list[dict[str, str]], code: str, location: str, message: str) -> None:
    errors.append({"code": code, "location": location, "message": message})


def _schema_location(path: Any) -> str:
    values = [str(item) for item in path]
    return "$" if not values else "$." + ".".join(values)


def _pre_schema_structure_errors(value: Any) -> list[dict[str, str]]:
    """Inspect hostile Python structures without recursion or breadth copies."""

    errors: list[dict[str, str]] = []
    stack: list[tuple[Any, ...]] = [("value", value, "$", 0)]
    while stack:
        frame = stack.pop()
        if frame[0] == "children":
            _, iterator, parent_path, depth, mapping_children = frame
            try:
                key, nested = next(iterator)
            except StopIteration:
                continue
            stack.append(frame)
            if mapping_children:
                if not isinstance(key, str):
                    _add(
                        errors,
                        "non_string_object_key",
                        parent_path,
                        "JSON object keys must be strings",
                    )
                    child_path = f"{parent_path}.<non-string-key>"
                else:
                    if len(key) > MAX_TEXT_LENGTH:
                        _add(
                            errors,
                            "input_string_length_exceeded",
                            parent_path,
                            f"object keys cannot exceed {MAX_TEXT_LENGTH} characters",
                        )
                    child_path = f"{parent_path}.{key}"
            else:
                child_path = f"{parent_path}.{key}"
            stack.append(("value", nested, child_path, depth))
            if len(errors) >= MAX_PRE_SCHEMA_ERRORS:
                break
            continue

        _, item, path, depth = frame
        if isinstance(item, str) and len(item) > MAX_TEXT_LENGTH:
            _add(
                errors,
                "input_string_length_exceeded",
                path,
                f"strings cannot exceed {MAX_TEXT_LENGTH} characters",
            )
            if len(errors) >= MAX_PRE_SCHEMA_ERRORS:
                break
        if isinstance(item, float) and not math.isfinite(item):
            _add(
                errors,
                "non_finite_number",
                path,
                "numbers must be finite JSON values",
            )
            continue
        if isinstance(item, Number) and not isinstance(item, (bool, int, float)):
            finite: bool | None = None
            is_finite = getattr(item, "is_finite", None)
            if callable(is_finite):
                try:
                    finite = bool(is_finite())
                except (ArithmeticError, TypeError, ValueError):
                    finite = None
            else:
                try:
                    finite = math.isfinite(float(item))
                except (ArithmeticError, OverflowError, TypeError, ValueError):
                    finite = None
            if finite is False:
                _add(
                    errors,
                    "non_finite_number",
                    path,
                    "numbers must be finite JSON values",
                )
            else:
                _add(
                    errors,
                    "unsupported_number_type",
                    path,
                    "numbers must use JSON-compatible int or float values",
                )
            continue
        is_mapping = isinstance(item, Mapping)
        is_sequence = isinstance(item, Sequence) and not isinstance(
            item, (str, bytes, bytearray)
        )
        if not is_mapping and not is_sequence:
            continue
        if depth >= MAX_INPUT_DEPTH:
            _add(
                errors,
                "input_structure_depth_exceeded",
                path,
                f"input nesting exceeds the maximum depth of {MAX_INPUT_DEPTH}",
            )
            continue
        try:
            width = len(item)
        except (ArithmeticError, OverflowError, TypeError, ValueError):
            _add(
                errors,
                "input_container_invalid",
                path,
                "input containers must expose a finite length",
            )
            continue
        if width > MAX_INPUT_CONTAINER_ITEMS:
            _add(
                errors,
                "input_container_width_exceeded",
                path,
                f"input containers cannot exceed {MAX_INPUT_CONTAINER_ITEMS} items",
            )
            continue
        if is_mapping:
            stack.append(
                ("children", iter(item.items()), path, depth + 1, True)
            )
        else:
            stack.append(
                ("children", enumerate(item), path, depth + 1, False)
            )
    return errors


def operational_outcome_errors(
    bundle: Mapping[str, Any],
) -> tuple[dict[str, str], ...]:
    """Return stable fail-closed error records for the complete bundle."""

    errors: list[dict[str, str]] = []
    structure_errors = _pre_schema_structure_errors(bundle)
    errors.extend(structure_errors)
    if structure_errors:
        return tuple(errors)
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

    material = _without(bundle, "bundle_digest")
    if bundle["bundle_digest"] != digest_value(material):
        _add(errors, "bundle_digest_mismatch", "$.bundle_digest", "bundle digest does not replay")
    body = _without(material, "evaluation_id")
    expected_id = "operational-outcome-evaluation." + canonical_sha256(body)
    if bundle["evaluation_id"] != expected_id:
        _add(errors, "evaluation_id_mismatch", "$.evaluation_id", "content-addressed evaluation id does not replay")

    policy = bundle["policy"]
    population = policy["target_population"]
    if population["population_digest"] != digest_value(_without(population, "population_digest")):
        _add(errors, "population_digest_mismatch", "$.policy.target_population", "population changed after binding")
    if policy["policy_digest"] != digest_value(_without(policy, "policy_digest")):
        _add(errors, "policy_digest_mismatch", "$.policy.policy_digest", "policy changed after binding")
    if (
        policy["arm_contract"]["baseline"] == policy["arm_contract"]["candidate"]
        or policy["arm_contract"]["baseline"]["digest"]
        == policy["arm_contract"]["candidate"]["digest"]
    ):
        _add(
            errors,
            "policy_arms_not_distinct",
            "$.policy.arm_contract",
            "baseline and candidate must be distinct outside an explicit A/A contract",
        )
    axis_policies = {str(item["axis"]): item for item in policy["axis_policies"]}
    if set(axis_policies) != set(AXES):
        _add(errors, "axis_policy_coverage_mismatch", "$.policy.axis_policies", "both outcome axes require one policy")
    for axis in AXES:
        if axis not in axis_policies:
            continue
        metric_ids = [str(item["metric_id"]) for item in axis_policies[axis]["metric_thresholds"]]
        if set(metric_ids) != set(METRICS_BY_AXIS[axis]) or _duplicates(metric_ids):
            _add(errors, "metric_policy_coverage_mismatch", "$.policy.axis_policies", axis)
        if axis_policies[axis]["max_effort_seconds"] > axis_policies[axis]["effort_cap_seconds"]:
            _add(errors, "effort_threshold_exceeds_cap", "$.policy.axis_policies", axis)
        if axis_policies[axis]["max_effort_units"] > axis_policies[axis]["effort_cap_units"]:
            _add(errors, "effort_threshold_exceeds_cap", "$.policy.axis_policies", axis)
    roles = {str(item["role_id"]): item for item in policy["roles"]}
    if len(roles) != len(policy["roles"]):
        _add(errors, "duplicate_role", "$.policy.roles", "role ids must be unique")
    strata = {(str(item["axis"]), str(item["stratum_id"])): item for item in policy["task_strata"]}
    if len(strata) != len(policy["task_strata"]):
        _add(errors, "duplicate_task_stratum", "$.policy.task_strata", "axis/stratum pairs must be unique")

    decisions = bundle["human_decision_records"]
    for duplicate in sorted(_duplicates(str(item["decision_id"]) for item in decisions)):
        _add(errors, "duplicate_human_decision", "$.human_decision_records", duplicate)
    for index, decision in enumerate(decisions):
        if decision["decision_digest"] != _record_digest(decision, "decision_digest"):
            _add(errors, "decision_digest_mismatch", f"$.human_decision_records.{index}", decision["decision_id"])
    if policy["status"] == "pending":
        if policy["decision_record_ref"] is not None:
            _add(errors, "pending_policy_has_decision_ref", "$.policy.decision_record_ref", "pending policy cannot imply adoption")
    else:
        decision_matches, decision_error = _policy_decision_resolution(
            policy, decisions
        )
        if not decision_matches:
            _add(
                errors,
                decision_error or "policy_decision_missing_or_mismatched",
                "$.policy.decision_record_ref",
                "the latest unambiguous decision over this exact policy must match its declared state",
            )

    task_set = bundle["task_set"]
    if task_set["policy_ref"] != _policy_ref(policy):
        _add(errors, "task_set_policy_mismatch", "$.task_set.policy_ref", "task set is not bound to current policy")
    if task_set["task_set_digest"] != _record_digest(task_set, "task_set_digest"):
        _add(errors, "task_set_digest_mismatch", "$.task_set.task_set_digest", "task set changed after sealing")
    if policy["status"] == "adopted" and _matching_policy_decision(policy, decisions):
        decision = next(item for item in decisions if item["decision_id"] == policy["decision_record_ref"])
        if task_set["adoption_decision_ref"] != _decision_ref(decision):
            _add(
                errors,
                "task_set_adoption_decision_mismatch",
                "$.task_set.adoption_decision_ref",
                "task-set sealing must cite the exact adoption decision digest",
            )
        if _parse_time(decision["recorded_at"]) >= _parse_time(task_set["sealed_at"]):
            _add(errors, "policy_adopted_after_task_seal", "$.task_set.sealed_at", "policy, costs, and thresholds must be adopted before sealing")
    elif task_set["adoption_decision_ref"] is not None:
        _add(
            errors,
            "task_set_has_invalid_adoption_ref",
            "$.task_set.adoption_decision_ref",
            "only an adopted policy may bind an adoption decision to the task set",
        )

    tasks = bundle["tasks"]
    task_ids = [str(item["task_id"]) for item in tasks]
    for duplicate in sorted(_duplicates(task_ids)):
        _add(errors, "duplicate_task", "$.tasks", duplicate)
    task_by_id = {str(item["task_id"]): item for item in tasks}
    for index, task in enumerate(tasks):
        location = f"$.tasks.{index}"
        if task["task_digest"] != _record_digest(task, "task_digest"):
            _add(errors, "task_digest_mismatch", location, task["task_id"])
        if task["target_role_id"] not in roles:
            _add(errors, "task_role_dangling", location, task["target_role_id"])
        if (task["axis"], task["stratum_id"]) not in strata:
            _add(errors, "task_stratum_dangling", location, task["stratum_id"])
        if _parse_time(task["sealed_at"]) != _parse_time(task_set["sealed_at"]):
            _add(errors, "task_seal_mismatch", location, task["task_id"])
        if task["axis"] == "repair_effect" and not REPAIR_SHORTCUTS.issubset(set(task["prohibited_repair_shortcuts"])):
            _add(errors, "repair_shortcut_barrier_missing", location, task["task_id"])
        if set(task["prohibited_decisions"]) != set(HUMAN_ONLY_DECISIONS):
            _add(
                errors,
                "human_only_decision_barrier_incomplete",
                location,
                task["task_id"],
            )
        for arm in ARMS:
            if (
                task["arm_materials"][arm]["derived_from_arm_ref"]
                != policy["arm_contract"][arm]
            ):
                _add(
                    errors,
                    "task_arm_derivation_mismatch",
                    f"{location}.arm_materials.{arm}",
                    task["task_id"],
                )
        if (
            task["arm_materials"]["baseline"]["material_ref"]
            == task["arm_materials"]["candidate"]["material_ref"]
            or task["arm_materials"]["baseline"]["material_ref"]["digest"]
            == task["arm_materials"]["candidate"]["material_ref"]["digest"]
        ):
            _add(
                errors,
                "task_arm_materials_not_distinct",
                f"{location}.arm_materials",
                task["task_id"],
            )
    uncovered_roles = sorted(
        set(roles) - {str(item["target_role_id"]) for item in tasks}
    )
    for role_id in uncovered_roles:
        _add(
            errors,
            "policy_role_task_coverage_missing",
            "$.policy.roles",
            f"declared policy role has no evaluation task: {role_id}",
        )
    expected_task_refs = [
        {"task_id": item["task_id"], "task_digest": item["task_digest"]}
        for item in _sorted_dicts(tasks, "axis", "task_id")
    ]
    if task_set["task_refs"] != expected_task_refs:
        _add(errors, "task_set_reference_closure_mismatch", "$.task_set.task_refs", "task references are incomplete or substituted")
    for axis in AXES:
        if not any(task["axis"] == axis for task in tasks):
            _add(errors, "axis_task_coverage_missing", "$.tasks", axis)

    enrollment_manifest = bundle["enrollment_manifest"]
    if enrollment_manifest["manifest_digest"] != _record_digest(
        enrollment_manifest, "manifest_digest"
    ):
        _add(
            errors,
            "enrollment_manifest_digest_mismatch",
            "$.enrollment_manifest.manifest_digest",
            "enrollment manifest changed after sealing",
        )
    if (
        enrollment_manifest["policy_ref"] != _policy_ref(policy)
        or enrollment_manifest["task_set_digest"] != task_set["task_set_digest"]
    ):
        _add(
            errors,
            "enrollment_study_binding_mismatch",
            "$.enrollment_manifest",
            "enrollment must bind the current policy and task set",
        )
    if _parse_time(enrollment_manifest["sealed_at"]) <= _parse_time(
        task_set["sealed_at"]
    ):
        _add(
            errors,
            "enrollment_sealed_before_task_set",
            "$.enrollment_manifest.sealed_at",
            "enrollment cannot precede task-set sealing",
        )

    participants = bundle["participants"]
    participant_ids = [str(item["participant_id"]) for item in participants]
    for duplicate in sorted(_duplicates(participant_ids)):
        _add(errors, "duplicate_participant", "$.participants", duplicate)
    participant_by_id = {str(item["participant_id"]): item for item in participants}
    for index, participant in enumerate(participants):
        location = f"$.participants.{index}"
        if participant["participant_digest"] != _record_digest(participant, "participant_digest"):
            _add(errors, "participant_digest_mismatch", location, participant["participant_id"])
        if participant["enrollment_digest"] != digest_value(
            _enrollment_material(participant)
        ):
            _add(errors, "participant_enrollment_digest_mismatch", location, participant["participant_id"])
        if not participant["pseudonymized"] or participant["raw_identifiers_present"]:
            _add(errors, "participant_pseudonymization_violation", location, participant["participant_id"])
        if participant["role_id"] not in roles:
            _add(errors, "participant_role_dangling", location, participant["role_id"])
        if participant["population_id"] != population["population_id"]:
            _add(errors, "participant_population_mismatch", location, participant["participant_id"])
        consent_withdrawn = (
            participant["consent"]["status"] == "withdrawn"
            and participant["disposition"]["status"] == "withdrawn"
        )
        if participant["consent"]["status"] != "obtained" and not consent_withdrawn:
            _add(errors, "participant_consent_missing", location, participant["participant_id"])
        if participant["consent"]["scope_ref"] != policy["privacy_consent"]["consent_scope_ref"]:
            _add(errors, "participant_consent_scope_mismatch", location, participant["participant_id"])
        if participant["source_kind"] != policy["evidence_class"]:
            _add(errors, "participant_evidence_class_mismatch", location, participant["participant_id"])
        if _parse_time(participant["enrolled_at"]) > _parse_time(
            enrollment_manifest["sealed_at"]
        ):
            _add(errors, "participant_enrolled_after_manifest_seal", location, participant["participant_id"])
        if _parse_time(participant["disposition"]["recorded_at"]) < _parse_time(
            participant["enrolled_at"]
        ):
            _add(errors, "participant_disposition_time_invalid", location, participant["participant_id"])

    expected_enrollment_refs = [
        {
            "participant_id": item["participant_id"],
            "enrollment_digest": item["enrollment_digest"],
            "role_id": item["role_id"],
            "arm": item["assigned_arm"],
            "cluster_id": item["cluster_id"],
        }
        for item in _sorted_dicts(participants, "participant_id")
    ]
    if enrollment_manifest["participant_refs"] != expected_enrollment_refs:
        _add(
            errors,
            "enrollment_participant_closure_mismatch",
            "$.enrollment_manifest.participant_refs",
            "all and only enrolled participants must remain in the denominator",
        )

    sessions = bundle["sessions"]
    session_ids = [str(item["session_id"]) for item in sessions]
    for duplicate in sorted(_duplicates(session_ids)):
        _add(errors, "duplicate_session", "$.sessions", duplicate)
    session_by_id = {str(item["session_id"]): item for item in sessions}
    participant_arms: dict[str, set[str]] = {}
    cluster_arms: dict[str, set[str]] = {}
    for index, session in enumerate(sessions):
        location = f"$.sessions.{index}"
        if session["session_digest"] != _record_digest(session, "session_digest"):
            _add(errors, "session_digest_mismatch", location, session["session_id"])
        participant = participant_by_id.get(str(session["participant_id"]))
        if participant is None or session["participant_digest"] != participant.get("participant_digest"):
            _add(errors, "session_participant_binding_mismatch", location, session["participant_id"])
        else:
            if session["role_id"] != participant["role_id"] or session["arm"] != participant["assigned_arm"]:
                _add(errors, "session_assignment_mismatch", location, session["session_id"])
        if session["policy_ref"] != _policy_ref(policy) or session["task_set_digest"] != task_set["task_set_digest"]:
            _add(errors, "session_study_binding_mismatch", location, session["session_id"])
        if _parse_time(session["started_at"]) < _parse_time(task_set["sealed_at"]) or _parse_time(session["started_at"]) >= _parse_time(session["completed_at"]):
            _add(errors, "session_time_order_invalid", location, session["session_id"])
        if _parse_time(session["started_at"]) <= _parse_time(
            enrollment_manifest["sealed_at"]
        ):
            _add(errors, "session_before_enrollment_seal", location, session["session_id"])
        if participant is not None and _parse_time(participant["consent"]["recorded_at"]) >= _parse_time(session["started_at"]):
            _add(errors, "consent_recorded_after_session_start", location, session["session_id"])
        if session["prior_task_exposure"] or set(session["training_task_refs"]) & set(task_ids):
            _add(errors, "learning_contamination", location, session["session_id"])
        participant_arms.setdefault(str(session["participant_id"]), set()).add(str(session["arm"]))
        if participant is not None:
            cluster_arms.setdefault(str(participant["cluster_id"]), set()).add(
                str(session["arm"])
            )
    if any(len(arms) > 1 for arms in participant_arms.values()):
        _add(errors, "cross_arm_participant_reuse", "$.sessions", "participants cannot observe both arms")
    if any(len(arms) > 1 for arms in cluster_arms.values()):
        _add(
            errors,
            "cross_arm_cluster_reuse",
            "$.sessions",
            "dependent participant clusters cannot cross arms",
        )

    observations = bundle["observations"]
    observation_ids = [str(item["observation_id"]) for item in observations]
    for duplicate in sorted(_duplicates(observation_ids)):
        _add(errors, "duplicate_observation", "$.observations", duplicate)
    observation_by_id = {str(item["observation_id"]): item for item in observations}
    participant_task_pairs: list[tuple[str, str]] = []
    coverage: dict[tuple[str, str], int] = {}
    for index, observation in enumerate(observations):
        location = f"$.observations.{index}"
        if observation["observation_digest"] != _record_digest(observation, "observation_digest"):
            _add(errors, "observation_digest_mismatch", location, observation["observation_id"])
        session = session_by_id.get(str(observation["session_id"]))
        task = task_by_id.get(str(observation["task_id"]))
        if session is None or observation["session_digest"] != session.get("session_digest"):
            _add(errors, "observation_session_binding_mismatch", location, observation["session_id"])
        elif any(observation[field] != session[field] for field in ("participant_id", "role_id", "arm")):
            _add(errors, "observation_session_projection_mismatch", location, observation["observation_id"])
        if task is None or observation["task_digest"] != task.get("task_digest"):
            _add(errors, "observation_task_binding_mismatch", location, observation["task_id"])
        else:
            if observation["axis"] != task["axis"] or observation["role_id"] != task["target_role_id"]:
                _add(errors, "observation_task_projection_mismatch", location, observation["observation_id"])
            if (
                observation["material_ref"]
                != task["arm_materials"][observation["arm"]]["material_ref"]
            ):
                _add(errors, "arm_material_substitution", location, observation["observation_id"])
        if session is not None and not (
            _parse_time(session["started_at"])
            <= _parse_time(observation["started_at"])
            < _parse_time(observation["completed_at"])
            <= _parse_time(session["completed_at"])
        ):
            _add(errors, "observation_time_order_invalid", location, observation["observation_id"])
        elapsed_from_interval = (
            _parse_time(observation["completed_at"])
            - _parse_time(observation["started_at"])
        ).total_seconds()
        if float(observation["effort"]["elapsed_seconds"]) != elapsed_from_interval:
            _add(
                errors,
                "elapsed_seconds_interval_mismatch",
                location,
                "elapsed_seconds must equal the observation wall-clock interval",
            )
        if observation["axis"] == "repair_effect":
            if observation["repair_artifact_ref"] is None or observation["response_ref"] is not None:
                _add(errors, "repair_observation_shape_invalid", location, observation["observation_id"])
        elif observation["response_ref"] is None or observation["repair_artifact_ref"] is not None:
            _add(errors, "human_use_observation_shape_invalid", location, observation["observation_id"])
        projection = observation["response_projection"]
        if projection["escalation_chosen"] and projection["routing_destination"] == "no_action":
            _add(
                errors,
                "escalation_destination_missing",
                location,
                "a chosen escalation must name a non-no_action routing destination",
            )
        if observation["axis"] == "repair_effect":
            verification_refs = observation["repair_verification_refs"]
            verification_ids = [str(item["ref_id"]) for item in verification_refs]
            verification_digests = [str(item["digest"]["value"]) for item in verification_refs]
            if _duplicates(verification_ids) or _duplicates(verification_digests):
                _add(
                    errors,
                    "repair_verification_reference_reused",
                    location,
                    "repair verification references must be mutually distinct by id and digest",
                )
            prohibited_refs = [
                item
                for item in (
                    observation["repair_artifact_ref"],
                    observation["participant_self_report"]["note_ref"],
                )
                if item is not None
            ]
            prohibited_ids = {str(item["ref_id"]) for item in prohibited_refs}
            prohibited_digests = {
                str(item["digest"]["value"]) for item in prohibited_refs
            }
            if set(verification_ids) & prohibited_ids or set(verification_digests) & prohibited_digests:
                _add(
                    errors,
                    "repair_verification_not_independent_reference",
                    location,
                    "repair verification cannot reuse the repair artifact or self-report id/digest",
                )
        axis_policy = axis_policies.get(str(observation["axis"]))
        if axis_policy and (
            observation["effort"]["elapsed_seconds"] > axis_policy["effort_cap_seconds"]
            or observation["effort"]["effort_units"] > axis_policy["effort_cap_units"]
        ):
            _add(errors, "effort_cap_exceeded", location, observation["observation_id"])
        participant_task_pairs.append((str(observation["participant_id"]), str(observation["task_id"])))
        coverage[(str(observation["arm"]), str(observation["task_id"]))] = coverage.get((str(observation["arm"]), str(observation["task_id"])), 0) + 1
    for duplicate in sorted(_duplicates(f"{a}|{b}" for a, b in participant_task_pairs)):
        _add(errors, "duplicate_participant_task_observation", "$.observations", duplicate)
    for task_id in task_ids:
        counts = [coverage.get((arm, task_id), 0) for arm in ARMS]
        if 0 in counts or len(set(counts)) != 1:
            _add(errors, "same_task_arm_coverage_mismatch", "$.observations", f"{task_id}: {counts}")
    session_counts = {
        participant_id: sum(
            str(session["participant_id"]) == participant_id for session in sessions
        )
        for participant_id in participant_ids
    }
    observation_counts = {
        participant_id: sum(
            str(observation["participant_id"]) == participant_id
            for observation in observations
        )
        for participant_id in participant_ids
    }
    for participant in participants:
        participant_id = str(participant["participant_id"])
        completed = participant["disposition"]["status"] == "completed"
        if completed and (
            session_counts[participant_id] != 1
            or observation_counts[participant_id] == 0
        ):
            _add(
                errors,
                "completed_participant_evidence_incomplete",
                "$.participants",
                participant_id,
            )
        if not completed and observation_counts[participant_id] != 0:
            _add(
                errors,
                "noncompleted_participant_observation_present",
                "$.observations",
                participant_id,
            )

    graders = bundle["graders"]
    grader_ids = [str(item["grader_id"]) for item in graders]
    for duplicate in sorted(_duplicates(grader_ids)):
        _add(errors, "duplicate_grader", "$.graders", duplicate)
    grader_by_id = {str(item["grader_id"]): item for item in graders}
    for index, grader in enumerate(graders):
        if grader["grader_digest"] != _record_digest(grader, "grader_digest"):
            _add(errors, "grader_digest_mismatch", f"$.graders.{index}", grader["grader_id"])

    scores = bundle["scores"]
    score_ids = [str(item["score_id"]) for item in scores]
    for duplicate in sorted(_duplicates(score_ids)):
        _add(errors, "duplicate_score", "$.scores", duplicate)
    score_by_id = {str(item["score_id"]): item for item in scores}
    scores_by_observation: dict[str, list[Mapping[str, Any]]] = {}
    for index, score in enumerate(scores):
        location = f"$.scores.{index}"
        if score["score_digest"] != _record_digest(score, "score_digest"):
            _add(errors, "score_digest_mismatch", location, score["score_id"])
        observation = observation_by_id.get(str(score["observation_id"]))
        grader = grader_by_id.get(str(score["grader_id"]))
        if observation is None or score["observation_digest"] != observation.get("observation_digest"):
            _add(errors, "score_observation_binding_mismatch", location, score["score_id"])
        if grader is None or score["grader_digest"] != grader.get("grader_digest") or grader.get("role") != "score_grader":
            _add(errors, "score_grader_binding_mismatch", location, score["score_id"])
        elif grader["relationship_to_artifact"] != "independent":
            _add(errors, "author_or_participant_self_scoring", location, score["grader_id"])
        if not score["blind_to_arm"] or not grader or not grader["blind_to_arm"] or not grader["blind_to_participant_identity"]:
            _add(errors, "score_blinding_broken", location, score["score_id"])
        if score["participant_self_report_used"]:
            _add(errors, "participant_self_report_used_as_score", location, score["score_id"])
        if observation is not None:
            task = task_by_id.get(str(observation["task_id"]))
            metric_ids = [str(item["metric_id"]) for item in score["criteria"]]
            if set(metric_ids) != set(METRICS_BY_AXIS[str(observation["axis"])]) or _duplicates(metric_ids):
                _add(errors, "score_metric_coverage_mismatch", location, score["score_id"])
            if task is not None and score["rubric_ref"] != task["rubric_ref"]:
                _add(errors, "score_rubric_substitution", location, score["score_id"])
            if _parse_time(score["recorded_at"]) < _parse_time(observation["completed_at"]):
                _add(errors, "score_before_observation_completion", location, score["score_id"])
        scores_by_observation.setdefault(str(score["observation_id"]), []).append(score)

    adjudications = bundle["adjudications"]
    adjudication_ids = [str(item["adjudication_id"]) for item in adjudications]
    for duplicate in sorted(_duplicates(adjudication_ids)):
        _add(errors, "duplicate_adjudication", "$.adjudications", duplicate)
    adjudication_by_key: dict[tuple[str, str], Mapping[str, Any]] = {}
    for index, adjudication in enumerate(adjudications):
        location = f"$.adjudications.{index}"
        if adjudication["adjudication_digest"] != _record_digest(adjudication, "adjudication_digest"):
            _add(errors, "adjudication_digest_mismatch", location, adjudication["adjudication_id"])
        key = (str(adjudication["observation_id"]), str(adjudication["metric_id"]))
        if key in adjudication_by_key:
            _add(errors, "duplicate_metric_adjudication", location, str(key))
        adjudication_by_key[key] = adjudication
        observation = observation_by_id.get(key[0])
        adjudicator = grader_by_id.get(str(adjudication["adjudicator_id"]))
        basis = set(str(item) for item in adjudication["basis_score_refs"])
        expected_basis = {str(item["score_id"]) for item in scores_by_observation.get(key[0], [])}
        if observation is None or adjudication["observation_digest"] != observation.get("observation_digest"):
            _add(errors, "adjudication_observation_binding_mismatch", location, key[0])
        elif adjudication["metric_id"] not in METRICS_BY_AXIS[str(observation["axis"])]:
            _add(
                errors,
                "adjudication_metric_axis_mismatch",
                location,
                adjudication["metric_id"],
            )
        if adjudicator is None or adjudication["adjudicator_digest"] != adjudicator.get("grader_digest") or adjudicator.get("role") != "adjudicator" or adjudicator.get("relationship_to_artifact") != "independent":
            _add(errors, "adjudicator_binding_or_independence_invalid", location, adjudication["adjudicator_id"])
        if (
            not adjudication["blind_to_arm"]
            or not adjudicator
            or not adjudicator["blind_to_arm"]
            or not adjudicator["blind_to_participant_identity"]
        ):
            _add(errors, "adjudication_blinding_broken", location, adjudication["adjudication_id"])
        if basis != expected_basis or not basis.issubset(score_by_id):
            _add(errors, "adjudication_basis_incomplete", location, adjudication["adjudication_id"])
        basis_times = [
            _parse_time(score_by_id[score_id]["recorded_at"])
            for score_id in basis
            if score_id in score_by_id
        ]
        if basis_times and _parse_time(adjudication["recorded_at"]) < max(basis_times):
            _add(
                errors,
                "adjudication_before_basis_scores",
                location,
                adjudication["adjudication_id"],
            )
        score_groups = {
            grader_by_id[str(score_by_id[score_id]["grader_id"])]["independence_group"]
            for score_id in basis
            if score_id in score_by_id and str(score_by_id[score_id]["grader_id"]) in grader_by_id
        }
        if adjudicator and adjudicator["independence_group"] in score_groups:
            _add(errors, "adjudicator_group_not_independent", location, adjudication["adjudication_id"])

    for observation in observations:
        observation_id = str(observation["observation_id"])
        observation_scores = scores_by_observation.get(observation_id, [])
        score_grader_ids = [str(item["grader_id"]) for item in observation_scores]
        groups = {
            grader_by_id[grader_id]["independence_group"]
            for grader_id in score_grader_ids
            if grader_id in grader_by_id
            and grader_by_id[grader_id]["relationship_to_artifact"] == "independent"
        }
        if len(observation_scores) < 2 or len(groups) < 2 or _duplicates(score_grader_ids):
            _add(errors, "independent_score_groups_insufficient", "$.scores", observation_id)
            continue
        task = task_by_id[str(observation["task_id"])]
        for metric_id in METRICS_BY_AXIS[str(observation["axis"])]:
            values = {_criteria_map(item).get(metric_id) for item in observation_scores}
            key = (observation_id, metric_id)
            if len(values) > 1 and key not in adjudication_by_key:
                _add(errors, "score_disagreement_unadjudicated", "$.adjudications", str(key))
            if len(values) == 1 and key in adjudication_by_key:
                _add(errors, "unnecessary_adjudication", "$.adjudications", str(key))
        resolved_candidate: dict[str, bool] = {}
        for metric_id in METRICS_BY_AXIS[str(observation["axis"])]:
            values = {_criteria_map(item)[metric_id] for item in observation_scores}
            key = (observation_id, metric_id)
            resolved_candidate[metric_id] = (
                next(iter(values)) if len(values) == 1 else bool(adjudication_by_key.get(key, {}).get("resolved_result", False))
            )
        projection = observation["response_projection"]
        authority_violation = bool(set(projection["authority_claims"]) & set(task["prohibited_decisions"])) or (
            projection["decision_claim"] == "accept"
            and "final_acceptance" in task["prohibited_decisions"]
        )
        if observation["axis"] == "human_operational_use":
            boundary_metric = "authority_safe"
        else:
            boundary_metric = "responsibility_boundary_preserved"
        if authority_violation and resolved_candidate.get(boundary_metric, True):
            _add(
                errors,
                "authority_error_concealed",
                "$.scores",
                observation_id,
            )
        if observation["axis"] == "human_operational_use":
            if projection["decision_claim"] == "accept" and resolved_candidate.get("technical_pass_not_converted_to_acceptance", True):
                _add(errors, "technical_pass_acceptance_conversion_concealed", "$.scores", observation_id)
            if task["unresolved_must_be_preserved"] and not observation["unresolved_preserved"] and resolved_candidate.get("unresolved_understood", True):
                _add(errors, "unresolved_loss_concealed", "$.scores", observation_id)
        else:
            shortcuts = set(observation["repair_shortcuts_used"])
            if shortcuts and (resolved_candidate.get("correct_repair", True) or resolved_candidate.get("finding_integrity_preserved", True)):
                _add(errors, "finding_suppression_concealed", "$.scores", observation_id)
            if observation["regression_status"] != "passed" and resolved_candidate.get("regression_free", True):
                _add(errors, "regression_concealed", "$.scores", observation_id)
            if not observation["repair_verification_refs"] and resolved_candidate.get("correct_repair", True):
                _add(errors, "self_report_only_repair_concealed", "$.scores", observation_id)
            if task["unresolved_must_be_preserved"] and not observation["unresolved_preserved"] and resolved_candidate.get("unresolved_preserved", True):
                _add(errors, "unresolved_loss_concealed", "$.scores", observation_id)
        if task["required_escalation"] and not projection["escalation_chosen"] and resolved_candidate.get("correct_escalation", True):
            _add(errors, "escalation_error_concealed", "$.scores", observation_id)

    critical_codes = {
        "schema_validation_failed",
        "duplicate_task",
        "duplicate_observation",
        "same_task_arm_coverage_mismatch",
        "axis_task_coverage_missing",
        "axis_arm_observation_coverage_missing",
        "independent_score_groups_insufficient",
        "score_disagreement_unadjudicated",
        "score_metric_coverage_mismatch",
    }
    if not critical_codes & {item["code"] for item in errors}:
        try:
            expected_results = _compute_results(
                policy=policy,
                decisions=decisions,
                tasks=tasks,
                participants=participants,
                observations=observations,
                scores=scores,
                adjudications=adjudications,
                task_set_digest=task_set["task_set_digest"],
            )
            if bundle["axis_results"] != expected_results:
                _add(errors, "axis_results_replay_mismatch", "$.axis_results", "stored results differ from complete deterministic replay")
        except (ArithmeticError, KeyError, TypeError, ValueError, StopIteration) as exc:
            _add(errors, "outcome_replay_failed", "$.axis_results", str(exc))
    if bundle["non_inference_axes"] != _NON_INFERENCE:
        _add(errors, "non_inference_boundary_mismatch", "$.non_inference_axes", "unrelated readiness axes must remain not_evaluated")
    if bundle["authority_boundary"] != _AUTHORITY_BOUNDARY:
        _add(errors, "authority_boundary_mismatch", "$.authority_boundary", "audit material cannot acquire control or acceptance authority")
    if not set(_DEFAULT_LIMITATIONS).issubset(set(bundle["limitations"])):
        _add(
            errors,
            "mandatory_limitations_missing",
            "$.limitations",
            "caller limitations may supplement but never replace mandatory limits",
        )
    return tuple(errors)


def validate_operational_outcome_evaluation(
    bundle: Mapping[str, Any],
) -> dict[str, Any]:
    errors = operational_outcome_errors(bundle)
    if errors:
        raise OperationalOutcomeValidationError(errors)
    return copy.deepcopy(dict(bundle))
