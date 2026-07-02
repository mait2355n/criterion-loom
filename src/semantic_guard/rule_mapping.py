from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from semantic_guard.rules import RULES, RULES_BY_ID, Rule


@dataclass(frozen=True)
class RuleDetectorMapping:
    rule_id: str
    detector_id: str
    source_module: str
    source_functions: tuple[str, ...]
    predicate_id: str = ""
    notes: str = ""

    def as_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "rule_id": self.rule_id,
            "detector_id": self.detector_id,
            "source_module": self.source_module,
            "source_functions": list(self.source_functions),
        }
        if self.predicate_id:
            payload["predicate_id"] = self.predicate_id
        if self.notes:
            payload["notes"] = self.notes
        return payload


_LOGICAL_PREDICATES = {
    "req.verifiability.acceptance_missing": "req.verifiability.acceptance_missing/v1",
    "req.achievement.criteria_missing": "req.achievement.criteria_missing/v1",
    "req.verification.method_detail_missing": "req.verification.method_detail_missing/v1",
    "req.evidence.artifact_missing": "req.evidence.artifact_missing/v1",
    "req.acceptance.rejection_condition_missing": "req.acceptance.rejection_condition_missing/v1",
    "req.context.scenario_missing": "req.context.scenario_missing/v1",
    "req.structure.observable_behavior_missing": "req.structure.observable_behavior_missing/v1",
}

_DETECTOR_SOURCES: dict[str, tuple[str, tuple[str, ...], str]] = {
    "req.verifiability.acceptance_missing": ("request.logical_verification.acceptance", ("audit_request", "build_request_verification_trace"), "logical trace plus lexical verification terms"),
    "req.scope.non_goals_missing": ("request.required_field.non_requirements", ("audit_request", "_missing_field_finding"), "required-field detector with satisfied non-emission support"),
    "req.achievement.criteria_missing": ("request.logical_verification.achievement_criteria", ("audit_request", "_requirement_achievement_profile", "build_request_verification_trace"), "logical trace over extracted achievement facts"),
    "req.verification.method_detail_missing": ("request.logical_verification.method_detail", ("audit_request", "_requirement_achievement_profile", "build_request_verification_trace"), "logical trace over verification-method facts"),
    "req.evidence.artifact_missing": ("request.logical_verification.evidence_artifact", ("audit_request", "_requirement_achievement_profile", "build_request_verification_trace"), "logical trace over retained-evidence facts"),
    "req.acceptance.rejection_condition_missing": ("request.logical_verification.rejection_condition", ("audit_request", "_requirement_achievement_profile", "build_request_verification_trace"), "logical trace over high-impact rejection-condition facts"),
    "req.context.scenario_missing": ("request.logical_verification.scenario_context", ("audit_request", "_requirement_achievement_profile", "build_request_verification_trace"), "logical trace over scenario-context facts"),
    "req.structure.observable_behavior_missing": ("request.logical_verification.observable_behavior", ("audit_request", "_requirement_structure_profile", "build_request_verification_trace"), "logical trace over observable-behavior facts"),
    "req.context.precondition_trigger_missing": ("request.structure.precondition_or_trigger", ("_requirement_structure_profile", "_add_requirement_quality_findings"), "lexical structure profile detector"),
    "req.result.expected_result_missing": ("request.structure.expected_result", ("_requirement_structure_profile", "_add_requirement_quality_findings"), "lexical structure profile detector"),
    "req.interface.contract_missing": ("request.structure.interface_contract", ("_requirement_structure_profile", "_add_requirement_quality_findings"), "lexical interface-contract detector"),
    "req.stakeholder.source_missing": ("request.quality.stakeholder_source", ("_requirement_quality_signals", "_add_requirement_quality_findings"), "requirements-quality signal detector"),
    "req.quality.measurable_constraint_missing": ("request.quality.measurable_constraint", ("_requirement_quality_signals", "_add_requirement_quality_findings"), "requirements-quality signal detector"),
    "req.priority.multiple_requirements_unprioritized": ("request.quality.priority", ("_looks_multi_requirement", "_requirement_quality_signals", "_add_requirement_quality_findings"), "multi-requirement and priority detector"),
    "req.uncertainty.unclassified_uncertainty": ("request.quality.uncertainty_classification", ("_add_ambiguity_findings", "_requirement_quality_signals", "_add_requirement_quality_findings"), "uncertainty lexical detector"),
    "req.solution.problem_mechanism_fit_missing": ("request.solution.problem_mechanism_fit", ("_requirement_quality_signals", "_problem_mechanism_fit_signal", "_add_requirement_quality_findings"), "structural problem-solution fit detector"),
    "req.acceptance.symptom_only_success_criteria": ("request.acceptance.symptom_only_success", ("_requirement_quality_signals", "_symptom_only_success_signal", "_add_requirement_quality_findings"), "symptom-only acceptance detector"),
    "plan.risk.rollback_missing": ("plan.required_field.rollback_or_recovery", ("audit_plan", "_missing_field_finding"), "required-field planning detector"),
    "plan.validation.problem_fit_missing": ("plan.required_field.validation_plan", ("audit_plan", "_missing_field_finding"), "required-field planning detector"),
    "plan.validation.owner_missing": ("plan.structure.validation_owner", ("audit_plan", "_missing_field_finding"), "required-field planning detector"),
    "plan.control.progress_control_missing": ("plan.quality.progress_control", ("_planning_quality_signals", "_add_planning_quality_findings"), "planning-quality signal detector"),
    "plan.control.change_control_missing": ("plan.quality.change_control", ("_planning_quality_signals", "_planning_suppression_traces", "_add_planning_quality_findings"), "planning signal with satisfied non-emission support"),
    "plan.structure.work_package_decomposition_missing": ("plan.structure.work_package_decomposition", ("_planning_structure_profile", "_planning_quality_signals", "_add_planning_quality_findings"), "planning-structure signal detector"),
    "plan.schedule.dependency_sequence_missing": ("plan.structure.dependency_sequence", ("_planning_structure_profile", "_planning_quality_signals", "_add_planning_quality_findings"), "planning-structure signal detector"),
    "plan.resource.estimate_or_capacity_missing": ("plan.structure.estimate_or_resource_basis", ("_planning_structure_profile", "_planning_quality_signals", "_add_planning_quality_findings"), "planning-structure signal detector"),
    "plan.risk.response_missing": ("plan.structure.risk_response", ("_planning_structure_profile", "_planning_quality_signals", "_add_planning_quality_findings"), "planning-structure signal detector"),
    "plan.risk.hazard_transfer_analysis_missing": ("plan.risk.hazard_transfer_analysis", ("_planning_quality_signals", "_hazard_transfer_analysis_signal", "_add_planning_quality_findings"), "solution side-effect and transfer detector"),
    "plan.system.idempotency_missing": ("plan.system.idempotency", ("_planning_quality_signals", "_idempotency_gap_signal", "_add_planning_quality_findings"), "retry and repeated side-effect safety detector"),
    "plan.control.baseline_or_metric_missing": ("plan.structure.control_baseline", ("_planning_structure_profile", "_planning_quality_signals", "_add_planning_quality_findings"), "planning-structure signal detector"),
    "plan.governance.decision_gate_missing": ("plan.structure.decision_gate", ("_planning_structure_profile", "_planning_quality_signals", "_add_planning_quality_findings"), "planning-structure signal detector"),
    "plan.release.provenance_missing": ("plan.release.provenance", ("_planning_quality_signals", "_release_provenance_gap_signal", "_add_planning_quality_findings"), "release artifact provenance detector"),
    "plan.minimality.justification_missing": ("plan.minimality.expansion_without_basis", ("_planning_quality_signals", "_minimality_justification_gap_signal", "_add_planning_quality_findings"), "negative requirements and minimality detector"),
    "diff.test_obligation.source_without_tests": ("diff.changed_files.source_without_tests", ("audit_diff", "_changed_files", "_is_source_file", "_is_test_file"), "changed-file detector"),
    "diff.security.sensitive_surface_change": ("diff.signal.security_surface", ("audit_diff", "_security_signal"), "security lexical signal detector"),
    "diff.implementation.public_contract_change": ("diff.signal.public_contract", ("_implementation_change_signals", "_public_contract_signal"), "implementation-change signal detector"),
    "diff.implementation.failure_handling_gap": ("diff.signal.failure_handling", ("_implementation_change_signals", "_failure_prone_operation_signal"), "implementation-change signal detector"),
    "diff.implementation.operational_observability_gap": ("diff.signal.operational_observability", ("_implementation_change_signals", "_operational_change_signal"), "implementation-change signal detector"),
    "diff.implementation.dependency_runtime_change": ("diff.signal.dependency_runtime", ("_implementation_change_signals", "_dependency_runtime_signal"), "implementation-change signal detector"),
    "diff.implementation.complexity_growth": ("diff.signal.complexity_growth", ("audit_diff", "_complexity_signal", "_complexity_growth_signal"), "minimality signal over structural additions"),
    "diff.implementation.filename_content_overbreadth": ("diff.signal.filename_content_scope", ("audit_diff", "_filename_content_scope_signals", "_responsibility_domain_hits"), "filename-to-content responsibility overbreadth detector"),
    "diff.implementation.filename_scope_underspecified": ("diff.signal.filename_naming_scope", ("audit_diff", "_filename_naming_scope_signals", "_changed_file_actions", "_filename_scope_risk_tokens"), "new-file filename scope-management detector"),
    "diff.meaning.identity_boundary_change": ("diff.semantic_boundaries.identity", ("audit_diff", "_semantic_boundaries", "_is_document_only_boundary"), "semantic-boundary lexical detector"),
    "finish.evidence.tests_missing": ("finish.evidence.tests_ran_or_reason", ("finish_check", "_has_any"), "finish evidence lexical detector"),
    "finish.implementation.behavior_evidence_missing": ("finish.evidence.public_behavior", ("finish_check", "_implemented_public_behavior", "_has_behavior_evidence"), "finish public-behavior evidence detector"),
    "finish.validation.acceptance_evidence_missing": ("finish.evidence.acceptance", ("finish_check", "_has_any"), "finish acceptance-evidence lexical detector"),
}


def rule_detector_mappings() -> list[dict[str, object]]:
    return [rule_detector_mapping(rule.id).as_dict() for rule in RULES]


def rule_detector_mapping(rule_id: str) -> RuleDetectorMapping:
    if rule_id not in RULES_BY_ID:
        raise KeyError(rule_id)
    detector_id, source_functions, notes = _DETECTOR_SOURCES[rule_id]
    return RuleDetectorMapping(
        rule_id=rule_id,
        detector_id=detector_id,
        source_module="semantic_guard.core",
        source_functions=source_functions,
        predicate_id=_LOGICAL_PREDICATES.get(rule_id, ""),
        notes=notes,
    )


def unmapped_rule_ids() -> list[str]:
    return sorted(rule.id for rule in RULES if rule.id not in _DETECTOR_SOURCES)


def infer_rule_id(phase: str, finding: dict[str, Any] | Any) -> str:
    text = _field(finding, "finding")
    if not text:
        return ""

    phase_rules = [rule for rule in RULES if rule.phase == phase]
    for rule in phase_rules:
        if text == rule.finding:
            return rule.id

    for rule in phase_rules:
        if rule.finding and (rule.finding in text or text in rule.finding):
            return rule.id

    return ""


def repair_for_finding(rule_id: str, finding: dict[str, Any] | Any) -> dict[str, object]:
    rule = RULES_BY_ID.get(rule_id)
    suggested_fix = _field(finding, "suggested_fix")
    needs_human_decision = _bool_field(finding, "needs_human_decision")
    if rule is None:
        return _generic_repair(finding, suggested_fix, needs_human_decision)

    target = _repair_target(rule, finding)
    kind = _repair_kind(rule, finding)
    return {
        "kind": kind,
        "target": target,
        "minimal_example": _minimal_example(kind, target),
        "needs_human_decision": needs_human_decision,
        "source": "rule_catalog",
        "rule_id": rule.id,
        "remediation": rule.remediation or suggested_fix,
    }


def enrich_finding_mapping(phase: str, finding: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(finding)
    rule_id = str(enriched.get("rule_id") or infer_rule_id(phase, enriched))
    if rule_id:
        enriched["rule_id"] = rule_id
    if "repair" not in enriched:
        repair = repair_for_finding(rule_id, enriched)
        if repair:
            enriched["repair"] = repair
    return enriched


def _generic_repair(finding: dict[str, Any] | Any, suggested_fix: str, needs_human_decision: bool) -> dict[str, object]:
    if not suggested_fix:
        return {}
    target = _field(finding, "category") or "audit_gap"
    return {
        "kind": "review_or_add_evidence",
        "target": target,
        "minimal_example": f"{target}: ...",
        "needs_human_decision": needs_human_decision,
        "source": "finding",
        "remediation": suggested_fix,
    }


def _repair_target(rule: Rule, finding: dict[str, Any] | Any) -> str:
    if rule.evidence_required:
        return rule.evidence_required[0]
    category = _field(finding, "category")
    return category or "audit_gap"


def _repair_kind(rule: Rule, finding: dict[str, Any] | Any) -> str:
    text = " ".join([rule.remediation, _field(finding, "suggested_fix"), rule.concern]).lower()
    if any(term in text for term in ["証拠", "evidence", "結果", "log", "実行"]):
        return "add_evidence"
    if any(term in text for term in ["判断", "受け入れ", "承認", "human"]):
        return "add_decision_point"
    if any(term in text for term in ["戻", "rollback", "復旧", "退避"]):
        return "add_recovery_condition"
    return "add_field"


def _minimal_example(kind: str, target: str) -> str:
    if kind == "add_evidence":
        return f"{target}: 実行コマンド、結果、保存先を記録する。"
    if kind == "add_decision_point":
        return f"{target}: 誰が、何を見て、受入または保留を判断する。"
    if kind == "add_recovery_condition":
        return f"{target}: 失敗時は退避済み状態へ戻す。"
    return f"{target}: ..."


def _field(item: dict[str, Any] | Any, key: str) -> str:
    if isinstance(item, dict):
        return str(item.get(key, ""))
    return str(getattr(item, key, ""))


def _bool_field(item: dict[str, Any] | Any, key: str) -> bool:
    if isinstance(item, dict):
        return bool(item.get(key, False))
    return bool(getattr(item, key, False))
