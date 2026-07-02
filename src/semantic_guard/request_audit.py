from __future__ import annotations

from semantic_guard.audit_common import (
    BASIS,
    SCOPE_BOUNDARY_TERMS,
    _add_ambiguity_findings,
    _blocker,
    _classify_requirements,
    _has_solution_bias,
    _is_bounded_work_package_request,
    _looks_multi_requirement,
    _normalize_input_kind,
    _result,
    _suppression_trace,
)
from semantic_guard.diff_audit import audit_diff
from semantic_guard.document_audit import audit_document as _audit_document
from semantic_guard.field_detection import missing_field_finding as _missing_field_finding
from semantic_guard.logic import (
    ACCEPTANCE_MISSING_RULE_ID,
    ACCEPTANCE_MISSING_VERIFICATION_TERMS,
    ACHIEVEMENT_CRITERIA_RULE_ID,
    EVIDENCE_ARTIFACT_RULE_ID,
    METHOD_DETAIL_RULE_ID,
    OBSERVABLE_BEHAVIOR_RULE_ID,
    REJECTION_CONDITION_RULE_ID,
    SCENARIO_CONTEXT_RULE_ID,
    build_request_verification_trace,
    derivation_for_rule,
)
from semantic_guard.models import Finding
from semantic_guard.plan_audit import audit_plan
from semantic_guard.request_findings import _add_requirement_quality_findings
from semantic_guard.request_profiles import (
    _requirement_achievement_profile,
    _requirement_quality_signals,
    _requirement_structure_profile,
)
from semantic_guard.result_builder import next_actions as _next_actions, score_from_findings as _score_from_findings
from semantic_guard.text_utils import combine as _combine, first_match as _first_match, has_any as _has_any

def audit_request(text: str, context: str = "", strict: bool = True, input_kind: str = "requirement") -> dict[str, object]:
    input_kind = _normalize_input_kind(input_kind)
    if input_kind == "document":
        return _audit_document(text=text, context=context, strict=strict, input_kind=input_kind)
    if input_kind == "plan":
        return audit_plan(plan=text, context=context, strict=strict, input_kind=input_kind)
    if input_kind == "diff-summary":
        return audit_diff(diff=text, intent=context, strict=strict, input_kind=input_kind)

    combined = _combine(text, context)
    findings: list[Finding] = []
    missing: list[str] = []
    classifications = _classify_requirements(combined)
    requirement_profile = _requirement_achievement_profile(combined)
    structure_profile = _requirement_structure_profile(combined)
    requirement_signals = _requirement_quality_signals(text, combined, requirement_profile, structure_profile)
    logical_trace = build_request_verification_trace(
        text=text,
        context=context,
        input_kind=input_kind,
        requirement_profile=requirement_profile,
        requirement_structure=structure_profile,
    )
    acceptance_missing_derivation = derivation_for_rule(logical_trace, ACCEPTANCE_MISSING_RULE_ID)
    achievement_criteria_derivation = derivation_for_rule(logical_trace, ACHIEVEMENT_CRITERIA_RULE_ID)
    method_detail_derivation = derivation_for_rule(logical_trace, METHOD_DETAIL_RULE_ID)
    evidence_artifact_derivation = derivation_for_rule(logical_trace, EVIDENCE_ARTIFACT_RULE_ID)
    rejection_condition_derivation = derivation_for_rule(logical_trace, REJECTION_CONDITION_RULE_ID)
    scenario_context_derivation = derivation_for_rule(logical_trace, SCENARIO_CONTEXT_RULE_ID)
    observable_behavior_derivation = derivation_for_rule(logical_trace, OBSERVABLE_BEHAVIOR_RULE_ID)
    non_emitted_rules: list[dict[str, object]] = []

    if not text.strip():
        findings.append(_blocker("clarity", "要求本文が空。", "要求本文を渡す。", BASIS["requirements"]))
        missing.append("request_text")

    bounded_work_package = _is_bounded_work_package_request(text, combined)
    if _looks_multi_requirement(text) and not bounded_work_package:
        findings.append(
            Finding(
                severity="minor",
                category="atomicity",
                basis=BASIS["requirements"],
                finding="複数の要求が一つに束ねられている可能性がある。",
                evidence=_first_match(text, [" and ", " or ", "かつ", "または", "及び", "および", "、"]),
                suggested_fix="一要求一意味へ分け、優先度と依存を別に書く。",
            )
        )

    _add_ambiguity_findings(text, findings)

    verification_terms = list(ACCEPTANCE_MISSING_VERIFICATION_TERMS)
    if not _has_any(combined, verification_terms):
        severity = "blocker" if strict else "major"
        finding = _missing_field_finding(
            field="verification_or_acceptance",
            patterns=verification_terms,
            text=combined,
            severity=severity,
            category="verifiability",
            basis=BASIS["requirements"],
            finding="要求の達成確認方法が見えない。",
            suggested_fix="試験、解析、検査、実演、受入条件のいずれかを明示する。",
        )
        finding.rule_id = ACCEPTANCE_MISSING_RULE_ID
        finding.derivation = acceptance_missing_derivation
        findings.append(finding)
        missing.append("verification_or_acceptance")

    purpose_terms = ["目的", "狙い", "意図", "価値", "意義", "理由", "why", "purpose", "value", "benefit"]
    if not _has_any(combined, purpose_terms):
        findings.append(
            _missing_field_finding(
                field="purpose_trace",
                patterns=purpose_terms,
                text=combined,
                severity="major",
                category="necessity",
                basis=BASIS["requirements"],
                finding="要求が上位目的や価値へ追跡できない。",
                suggested_fix="この要求が何を叶えるために必要かを足す。",
            )
        )
        missing.append("purpose_trace")

    if _has_solution_bias(text):
        findings.append(
            Finding(
                severity="minor",
                category="solution_bias",
                basis=BASIS["requirements"],
                finding="要求が実装方式を固定している可能性がある。",
                evidence=_first_match(text, ["SQLite", "PostgreSQL", "React", "Swift", "Python", "CLI", "MCP", "API", "JSON"]),
                suggested_fix="方式が意味上必要なら根拠を書く。単なる案なら仕様案へ分離する。",
            )
        )

    if not _has_any(combined, SCOPE_BOUNDARY_TERMS):
        findings.append(
            _missing_field_finding(
                field="non_requirements",
                patterns=SCOPE_BOUNDARY_TERMS,
                text=combined,
                severity="minor",
                category="scope",
                basis=BASIS["requirements"],
                finding="非要求または対象外が明示されていない。",
                suggested_fix="今回やらないこと、誤って含めてはいけないことを追加する。",
            )
        )
        missing.append("non_requirements")
    else:
        non_emitted_rules.append(
            _suppression_trace(
                phase="audit_request",
                rule_id="req.scope.non_goals_missing",
                emission_status="satisfied",
                reason="explicit_scope_boundary_satisfies_rule",
                evidence=_first_match(combined, SCOPE_BOUNDARY_TERMS),
                source="required_field.non_requirements",
            )
        )

    unknown_terms = ["未確定", "未決", "不明", "判断待ち", "仮説", "保留", "unknown", "tbd", "pending"]
    if not _has_any(combined, unknown_terms):
        findings.append(
            _missing_field_finding(
                field="unknowns",
                patterns=unknown_terms,
                text=combined,
                severity="info",
                category="unknowns",
                basis=BASIS["requirements"] + BASIS["meaning"],
                finding="未確定事項が明示されていない。無いなら無いと書く方がよい。",
                suggested_fix="未確定、仮説、判断待ち、片側観測、時点差を分ける。",
            )
        )

    _add_requirement_quality_findings(
        requirement_signals,
        findings,
        missing,
        strict,
        achievement_criteria_derivation=achievement_criteria_derivation,
        method_detail_derivation=method_detail_derivation,
        evidence_artifact_derivation=evidence_artifact_derivation,
        rejection_condition_derivation=rejection_condition_derivation,
        scenario_context_derivation=scenario_context_derivation,
        observable_behavior_derivation=observable_behavior_derivation,
    )

    return _result(
        phase="audit_request",
        findings=findings,
        missing=sorted(set(missing)),
        score=_score_from_findings(findings),
        details={
            "classifications": classifications,
            "input_kind": input_kind,
            "requirement_signals": requirement_signals,
            "requirement_profile": requirement_profile,
            "requirement_structure": structure_profile,
            "logical_trace": logical_trace.as_dict(),
            "non_emitted_rules": non_emitted_rules,
            "suppressed_rules": non_emitted_rules,
        },
        next_actions=_next_actions(findings, "要求を目的、非要求、検証方法へ分解する。"),
    )
