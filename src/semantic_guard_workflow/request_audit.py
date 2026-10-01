from __future__ import annotations

from semantic_guard_workflow.audit_common import (
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
from semantic_guard_workflow.diff_audit import audit_diff
from semantic_guard_workflow.document_audit import audit_document as _audit_document
from semantic_guard_workflow.field_detection import (
    missing_field_finding as _missing_field_finding,
)
from semantic_guard_workflow.logic import (
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
from semantic_guard_workflow.models import Finding
from semantic_guard_workflow.plan_audit import audit_plan
from semantic_guard_workflow.request_decision_frame import (
    PRECONDITION_ORDER_DIRECTION_RULE_ID,
    audit_precondition_sufficiency,
)
from semantic_guard_workflow.request_direction_binding import (
    audit_direction_binding_sufficiency,
)
from semantic_guard_workflow.request_findings import _add_requirement_quality_findings
from semantic_guard_workflow.request_profiles import (
    _requirement_achievement_profile,
    _requirement_quality_signals,
    _requirement_structure_profile,
)
from semantic_guard_workflow.requirement_relations import (
    VERIFICATION_TARGET_MISMATCH_RULE_ID,
    audit_requirement_relations,
)
from semantic_guard_workflow.result_builder import next_actions as _next_actions
from semantic_guard_workflow.result_builder import score_from_findings as _score_from_findings
from semantic_guard_workflow.text_utils import combine as _combine
from semantic_guard_workflow.text_utils import first_match as _first_match
from semantic_guard_workflow.text_utils import has_any as _has_any


def _relation_evidence_excerpt(check: dict[str, object], role: str) -> str:
    spans = check.get("evidence_spans", [])
    if not isinstance(spans, list):
        return ""
    role_fields = {
        "criterion": {"acceptance", "acceptance_criteria", "criterion"},
        "method": {"verification", "verification_method", "method"},
    }
    for span in spans:
        if not isinstance(span, dict):
            continue
        if str(span.get("field", "")) not in role_fields[role]:
            continue
        excerpt = span.get("excerpt")
        if isinstance(excerpt, str) and excerpt.strip():
            return excerpt.strip()
    return ""


def _add_requirement_relation_result(
    summary: dict[str, object],
    findings: list[Finding],
    non_emitted_rules: list[dict[str, object]],
    *,
    strict: bool,
) -> None:
    checks = summary.get("checks", [])
    if not isinstance(checks, list):
        return
    check = next(
        (
            item
            for item in checks
            if isinstance(item, dict)
            and item.get("check_id") == "verification_verifies_acceptance"
        ),
        None,
    )
    if check is None:
        return

    status = str(check.get("status", "unknown"))
    derivation_status = str(check.get("derivation_status", "blocked_by_unknown"))
    criterion_excerpt = _relation_evidence_excerpt(check, "criterion")
    method_excerpt = _relation_evidence_excerpt(check, "method")
    if status == "mismatch" and derivation_status == "derived" and criterion_excerpt and method_excerpt:
        findings.append(
            Finding(
                severity="major" if strict else "minor",
                category="verification",
                basis=BASIS["requirements"],
                finding="受入基準と検証方法が同じ対象または測定特性を扱っていない。",
                evidence=f"受入基準: {criterion_excerpt} | 検証方法: {method_excerpt}",
                suggested_fix=(
                    "受入基準が定める対象、測定特性、条件を検証方法へ結び、"
                    "同じ量または挙動を測る方法と証拠を明示する。"
                ),
                rule_id=VERIFICATION_TARGET_MISMATCH_RULE_ID,
                match_status="matched",
                confidence="high",
                derivation={
                    "schema_version": "requirement-relation-finding-derivation/v1",
                    "derivation_scope": (
                        "bounded single-record relation comparison; not natural-language truth or final acceptance"
                    ),
                    "rule_id": VERIFICATION_TARGET_MISMATCH_RULE_ID,
                    "status": "derived",
                    "profile_id": check.get("profile_id", ""),
                    "check_id": check.get("check_id", ""),
                    "obligation_id": check.get("obligation_id", ""),
                    "evidence_spans": list(check.get("evidence_spans", [])),
                },
            )
        )
        return

    if status == "aligned":
        emission_status = "satisfied"
        match_status = "matched"
        reason = "asserted_verification_target_alignment_satisfies_rule"
        evidence = f"受入基準: {criterion_excerpt} | 検証方法: {method_excerpt}".strip(" |")
    elif status == "not_applicable":
        emission_status = "not_applicable"
        match_status = "not_applicable"
        reason = "requirement_relation_profile_not_applicable"
        evidence = ""
    else:
        emission_status = "conflict" if derivation_status == "conflict" else "unknown"
        match_status = "unknown"
        reasons = check.get("unknown_reasons", [])
        reason = ", ".join(str(item) for item in reasons) if isinstance(reasons, list) else ""
        reason = reason or "verification_target_relation_not_asserted"
        evidence = ""
    non_emitted_rules.append(
        _suppression_trace(
            phase="audit_request",
            rule_id=VERIFICATION_TARGET_MISMATCH_RULE_ID,
            emission_status=emission_status,
            match_status=match_status,
            reason=reason,
            evidence=evidence,
            source="requirement_relation_summary",
            confidence="high" if status in {"aligned", "not_applicable"} else "low",
        )
    )


def _add_precondition_sufficiency_result(
    summary: dict[str, object],
    findings: list[Finding],
    missing: list[str],
    non_emitted_rules: list[dict[str, object]],
    *,
    strict: bool,
) -> None:
    status = str(summary.get("status", "not_applicable"))
    frames = summary.get("frames", [])
    frame = frames[0] if isinstance(frames, list) and frames and isinstance(frames[0], dict) else None
    if frame is None:
        return

    source_span = frame.get("source_span", {})
    source_excerpt = str(source_span.get("excerpt", "")) if isinstance(source_span, dict) else ""
    evaluations = frame.get("evaluations", [])
    evaluation = next(
        (
            item
            for item in evaluations
            if isinstance(item, dict)
            and item.get("rule_id") == PRECONDITION_ORDER_DIRECTION_RULE_ID
        ),
        {},
    ) if isinstance(evaluations, list) else {}
    finding_eligible = bool(evaluation.get("finding_eligible"))

    if finding_eligible:
        interpretations = frame.get("interpretation_candidates", [])
        rewrite_candidates = [
            str(item.get("rewrite", ""))
            for item in interpretations
            if isinstance(item, dict) and str(item.get("rewrite", ""))
        ] if isinstance(interpretations, list) else []
        candidate_matches = [
            {
                "candidate_id": str(item.get("condition", {}).get("order_direction", ""))
                if isinstance(item.get("condition"), dict)
                else "",
                "condition": dict(item.get("condition", {}))
                if isinstance(item.get("condition"), dict)
                else {},
                "rewrite": str(item.get("rewrite", "")),
                "outcome_status": "not_evaluated",
            }
            for item in interpretations
            if isinstance(item, dict)
        ] if isinstance(interpretations, list) else []
        operation = frame.get("operation", {})
        scale_id = str(operation.get("scale_id", "")) if isinstance(operation, dict) else ""
        order_axis_id = (
            str(operation.get("order_axis_id", ""))
            if isinstance(operation, dict)
            else ""
        )
        measure = str(operation.get("measure", "")) if isinstance(operation, dict) else ""
        direction_binding = frame.get("direction_binding", {})
        binding = direction_binding if isinstance(direction_binding, dict) else {}
        binding_status = str(binding.get("status", "missing"))
        accepted = binding.get("accepted_evidence", [])
        rejected = binding.get("rejected_evidence", [])
        accepted_count = len(accepted) if isinstance(accepted, list) else 0
        rejected_count = len(rejected) if isinstance(rejected, list) else 0
        is_conflict = binding_status == "conflict"
        findings.append(
            Finding(
                severity="minor" if strict else "info",
                category="decision_frame",
                basis=BASIS["requirements"] + BASIS["meaning"],
                finding=(
                    "方向を一意にしない後続選択表現に、相反する方向拘束が結び付いている。"
                    if is_conflict
                    else "方向を一意にしない後続選択表現に、有効な方向拘束が結び付いていない。"
                ),
                evidence=(
                    f"{source_excerpt} | scale={scale_id} axis={order_axis_id} "
                    f"measure={measure} "
                    f"direction_binding={binding_status} accepted={accepted_count} "
                    f"rejected={rejected_count}"
                ).strip(" |"),
                suggested_fix=(
                    "相反する方向指定を一つへ確定する。"
                    if is_conflict
                    else "同じ判断枠・同じ順序軸へ、高極側先行又は低極側先行の方向条件を明示的に結び付ける。"
                ),
                needs_human_decision=True,
                warning_class="actionable",
                semantic_boundaries=[
                    "比較形容詞の極性から意図した並び方向を自動決定しない。",
                    "同じ高低語を使えても、順序軸が異なる条件は方向拘束として受理しない。",
                    "数値、候補所属、又は結果差は方向拘束の成否、適合度、確信度を変更しない。",
                    "登録尺度の固定表層と、列挙された結合位置の範囲だけを監査する。",
                ],
                rule_id=PRECONDITION_ORDER_DIRECTION_RULE_ID,
                repair={
                    "schema_version": "decision-frame-repair/v3",
                    "kind": "resolve_precondition" if is_conflict else "add_precondition",
                    "target": "order_direction",
                    "rewrite_candidates": rewrite_candidates,
                    "needs_human_decision": True,
                },
                match_status=str(evaluation.get("match_status", "matched")),
                confidence=str(evaluation.get("confidence", "medium")),
                ambiguity_reasons=[
                    (
                        "conflicting_condition:order_direction"
                        if is_conflict
                        else "missing_condition:order_direction"
                    )
                ],
                candidate_matches=candidate_matches,
                derivation={
                    "schema_version": "decision-frame-finding-derivation/v3",
                    "derivation_scope": (
                        "bounded Japanese registered scalar direction-open expression and "
                        "attachment sites; not unrestricted natural-language truth, intended "
                        "direction, or final acceptance"
                    ),
                    "rule_id": PRECONDITION_ORDER_DIRECTION_RULE_ID,
                    "status": "derived",
                    "frame_id": frame.get("frame_id", ""),
                    "source_span": source_span,
                    "direction_open_expression": dict(
                        frame.get("direction_open_expression", {})
                    )
                    if isinstance(frame.get("direction_open_expression"), dict)
                    else {},
                    "direction_binding": dict(binding),
                    "operation": dict(operation) if isinstance(operation, dict) else {},
                    "unresolved_unknowns": list(frame.get("unknown_reasons", [])),
                    "morphology": dict(summary.get("morphology", {}))
                    if isinstance(summary.get("morphology"), dict)
                    else {},
                },
            )
        )
        missing.append("order_direction")
        return

    if status == "direction_bound":
        direction_binding = frame.get("direction_binding", {})
        evidence = ""
        if isinstance(direction_binding, dict):
            accepted = direction_binding.get("accepted_evidence", [])
            if isinstance(accepted, list) and accepted and isinstance(accepted[0], dict):
                span = accepted[0].get("source_span", {})
                if isinstance(span, dict):
                    evidence = str(span.get("excerpt", ""))
        non_emitted_rules.append(
            _suppression_trace(
                phase="audit_request",
                rule_id=PRECONDITION_ORDER_DIRECTION_RULE_ID,
                emission_status="satisfied",
                match_status="matched",
                reason="direction_constraint_bound_to_direction_open_expression",
                evidence=evidence,
                source="decision_frame_summary",
            )
        )
        return

    if status == "indeterminate":
        reasons = frame.get("unknown_reasons", [])
        reason = ", ".join(str(item) for item in reasons) if isinstance(reasons, list) else ""
        non_emitted_rules.append(
            _suppression_trace(
                phase="audit_request",
                rule_id=PRECONDITION_ORDER_DIRECTION_RULE_ID,
                emission_status="unknown",
                match_status="unknown",
                reason=reason or "direction_binding_not_derived",
                evidence=source_excerpt,
                source="decision_frame_summary",
                confidence="low",
            )
        )


def _add_direction_binding_result(
    summary: dict[str, object],
    findings: list[Finding],
    missing: list[str],
    non_emitted_rules: list[dict[str, object]],
    *,
    strict: bool,
) -> None:
    frames = summary.get("frames", [])
    frame = (
        frames[0]
        if isinstance(frames, list) and frames and isinstance(frames[0], dict)
        else None
    )
    if frame is None:
        return

    source_span = frame.get("source_span", {})
    source_excerpt = (
        str(source_span.get("excerpt", ""))
        if isinstance(source_span, dict)
        else ""
    )
    evaluations = frame.get("evaluations", [])
    evaluation = (
        next(
            (
                item
                for item in evaluations
                if isinstance(item, dict)
                and item.get("rule_id") == PRECONDITION_ORDER_DIRECTION_RULE_ID
            ),
            {},
        )
        if isinstance(evaluations, list)
        else {}
    )
    direction_binding = frame.get("direction_binding", {})
    binding = direction_binding if isinstance(direction_binding, dict) else {}
    binding_status = str(binding.get("status", "indeterminate"))
    finding_eligible = bool(evaluation.get("finding_eligible"))

    if finding_eligible:
        interpretations = frame.get("interpretation_candidates", [])
        interpretations = interpretations if isinstance(interpretations, list) else []
        rewrite_candidates = [
            str(item.get("rewrite", ""))
            for item in interpretations
            if isinstance(item, dict) and str(item.get("rewrite", ""))
        ]
        candidate_matches = [
            {
                "candidate_id": str(
                    item.get("condition", {}).get("traversal_direction", "")
                )
                if isinstance(item.get("condition"), dict)
                else "",
                "condition": dict(item.get("condition", {}))
                if isinstance(item.get("condition"), dict)
                else {},
                "rewrite": str(item.get("rewrite", "")),
                "outcome_status": "not_evaluated",
            }
            for item in interpretations
            if isinstance(item, dict)
        ]
        operation = frame.get("operation", {})
        operation = operation if isinstance(operation, dict) else {}
        domain_id = str(operation.get("direction_domain_id", ""))
        axis_id = str(operation.get("direction_axis_id", ""))
        basis_id = str(operation.get("direction_basis_id", ""))
        accepted = binding.get("accepted_evidence", [])
        rejected = binding.get("rejected_evidence", [])
        unresolved = binding.get("unresolved_evidence", [])
        accepted_count = len(accepted) if isinstance(accepted, list) else 0
        rejected_count = len(rejected) if isinstance(rejected, list) else 0
        unresolved_count = len(unresolved) if isinstance(unresolved, list) else 0
        is_conflict = binding_status == "conflict"
        findings.append(
            Finding(
                severity="minor" if strict else "info",
                category="decision_frame",
                basis=BASIS["requirements"] + BASIS["meaning"],
                finding=(
                    "方向を一意にしない後続選択表現に、相反する方向拘束が結び付いている。"
                    if is_conflict
                    else "方向を一意にしない後続選択表現に、有効な方向拘束が結び付いていない。"
                ),
                evidence=(
                    f"{source_excerpt} | domain={domain_id} axis={axis_id} "
                    f"basis={basis_id} direction_binding={binding_status} "
                    f"accepted={accepted_count} rejected={rejected_count} "
                    f"unresolved={unresolved_count}"
                ).strip(" |"),
                suggested_fix=(
                    "同じ方向基準へ結び付いた相反指定を、一方向へ確定する。"
                    if is_conflict
                    else "同じ判断枠・同じ方向基準へ、走査又は辿り方の方向条件を明示的に結び付ける。"
                ),
                needs_human_decision=True,
                warning_class="actionable",
                semantic_boundaries=[
                    "「次」又は近傍表現だけから意図した走査方向を自動決定しない。",
                    "方向領域又は方向軸が異なる条件は拘束として受理しない。",
                    "慣習的な既定順、世界知識、候補結果、又は行順は方向拘束を補完しない。",
                    "明示方向領域の固定表層と、列挙された直接結合位置だけを監査する。",
                ],
                rule_id=PRECONDITION_ORDER_DIRECTION_RULE_ID,
                repair={
                    "schema_version": "direction-binding-repair/v1",
                    "kind": (
                        "resolve_precondition" if is_conflict else "add_precondition"
                    ),
                    "target": "traversal_direction",
                    "rewrite_candidates": rewrite_candidates,
                    "needs_human_decision": True,
                },
                match_status=str(evaluation.get("match_status", "matched")),
                confidence=str(evaluation.get("confidence", "medium")),
                ambiguity_reasons=[
                    (
                        "conflicting_condition:traversal_direction"
                        if is_conflict
                        else "missing_condition:traversal_direction"
                    )
                ],
                candidate_matches=candidate_matches,
                derivation={
                    "schema_version": "direction-binding-finding-derivation/v1",
                    "derivation_scope": (
                        "bounded Japanese explicit direction-space successor expression "
                        "and direct attachment sites; not unrestricted natural-language "
                        "truth, conventional direction, outcome, or final acceptance"
                    ),
                    "rule_id": PRECONDITION_ORDER_DIRECTION_RULE_ID,
                    "status": "derived",
                    "frame_id": frame.get("frame_id", ""),
                    "source_span": source_span,
                    "direction_open_expression": dict(
                        frame.get("direction_open_expression", {})
                    )
                    if isinstance(frame.get("direction_open_expression"), dict)
                    else {},
                    "direction_binding": dict(binding),
                    "operation": dict(operation),
                    "unresolved_unknowns": list(frame.get("unknown_reasons", [])),
                    "morphology": dict(summary.get("morphology", {}))
                    if isinstance(summary.get("morphology"), dict)
                    else {},
                },
            )
        )
        missing.append("order_direction")
        return

    if binding_status == "bound":
        accepted = binding.get("accepted_evidence", [])
        evidence = ""
        if isinstance(accepted, list) and accepted and isinstance(accepted[0], dict):
            span = accepted[0].get("source_span", {})
            if isinstance(span, dict):
                evidence = str(span.get("excerpt", ""))
        non_emitted_rules.append(
            _suppression_trace(
                phase="audit_request",
                rule_id=PRECONDITION_ORDER_DIRECTION_RULE_ID,
                emission_status="satisfied",
                match_status="matched",
                reason="direction_constraint_bound_to_explicit_direction_space",
                evidence=evidence,
                source="direction_binding_summary",
            )
        )
        return

    if binding_status == "indeterminate":
        reasons = frame.get("unknown_reasons", [])
        reason = (
            ", ".join(str(item) for item in reasons)
            if isinstance(reasons, list)
            else ""
        )
        non_emitted_rules.append(
            _suppression_trace(
                phase="audit_request",
                rule_id=PRECONDITION_ORDER_DIRECTION_RULE_ID,
                emission_status="unknown",
                match_status="unknown",
                reason=reason or "direction_binding_not_derived",
                evidence=source_excerpt,
                source="direction_binding_summary",
                confidence="low",
            )
        )


def audit_request(
    text: str,
    context: str = "",
    strict: bool = True,
    input_kind: str = "requirement",
    *,
    morphology_provider: object | None = None,
) -> dict[str, object]:
    input_kind = _normalize_input_kind(input_kind)
    if morphology_provider is not None and input_kind != "requirement":
        raise ValueError("morphology_provider is supported only for requirement input")
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
    relation_audit = audit_requirement_relations(
        text,
        context=context,
        morphology_provider=morphology_provider,
    )
    relation_summary = relation_audit.public_summary()
    decision_frame_summary = (
        audit_precondition_sufficiency(relation_audit.ir)
        if morphology_provider is not None
        else None
    )
    direction_binding_summary = (
        audit_direction_binding_sufficiency(relation_audit.ir)
        if morphology_provider is not None
        else None
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
    if acceptance_missing_derivation.get("status") == "derived":
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
        rejected_route_facts = [
            fact
            for fact in acceptance_missing_derivation.get("facts_used", [])
            if isinstance(fact, dict)
            and fact.get("name")
            in {
                "text.has_verification_language",
                "text.has_acceptance_criteria",
                "text.has_verification_method",
            }
            and fact.get("status") == "rejected"
        ]
        if rejected_route_facts:
            finding.warning_class = "actionable"
            finding.match_status = "rejected"
            finding.confidence = "high"
            finding.ambiguity_reasons = ["explicitly_rejected_field_assertion"]
            finding.nearest_candidates = []
            finding.candidate_matches = []
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

    _add_requirement_relation_result(
        relation_summary,
        findings,
        non_emitted_rules,
        strict=strict,
    )

    if decision_frame_summary is not None:
        _add_precondition_sufficiency_result(
            decision_frame_summary,
            findings,
            missing,
            non_emitted_rules,
            strict=strict,
        )
    if direction_binding_summary is not None:
        _add_direction_binding_result(
            direction_binding_summary,
            findings,
            missing,
            non_emitted_rules,
            strict=strict,
        )

    details: dict[str, object] = {
        "classifications": classifications,
        "input_kind": input_kind,
        "requirement_signals": requirement_signals,
        "requirement_profile": requirement_profile,
        "requirement_structure": structure_profile,
        "requirement_relation_summary": relation_summary,
        "logical_trace": logical_trace.as_dict(),
        "non_emitted_rules": non_emitted_rules,
        "suppressed_rules": non_emitted_rules,
    }
    if decision_frame_summary is not None:
        details["decision_frame_summary"] = decision_frame_summary
    if direction_binding_summary is not None:
        details["direction_binding_summary"] = direction_binding_summary

    return _result(
        phase="audit_request",
        findings=findings,
        missing=sorted(set(missing)),
        score=_score_from_findings(findings),
        details=details,
        next_actions=_next_actions(findings, "要求を目的、非要求、検証方法へ分解する。"),
    )
