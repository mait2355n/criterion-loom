from __future__ import annotations

import re
from collections.abc import Iterable

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
from semantic_guard.matching import FieldMatchDiagnostic, diagnose_field_match
from semantic_guard.models import AuditResult, Finding
from semantic_guard.rule_mapping import infer_rule_id, repair_for_finding

BASIS = {
    "requirements": ["ISO/IEC/IEEE 29148", "BABOK", "NASA SEH"],
    "planning": ["PMBOK", "PMI WBS", "ISO 21502", "ISO 21511", "NASA SEH", "NASA SEMP"],
    "implementation": ["ISO/IEC 25010", "ISO/IEC/IEEE 12207", "SWEBOK"],
    "security": ["OWASP", "NIST SSDF", "CWE"],
    "minimality": ["Value Engineering", "Lean Engineering", "SWEBOK", "ISO/IEC 25010"],
    "meaning": ["semantic-implementation"],
}
LOGICAL_TRACE_SUMMARY_SCHEMA_VERSION = "logical-trace-summary/v1"
LOGICAL_TRACE_OUTPUT_MODES = ("summary", "full", "none")
DECISION_STATE_AUDIT_SCHEMA_VERSION = "decision-state-audit/v1"
DEFAULT_SNIPPET_LIMIT = 220

AMBIGUOUS_TERMS = [
    "適切",
    "十分",
    "なるべく",
    "できるだけ",
    "柔軟",
    "簡単",
    "速い",
    "安全",
    "いい感じ",
    "必要に応じて",
    "適宜",
    "appropriate",
    "enough",
    "fast",
    "easy",
    "simple",
    "flexible",
    "secure",
    "safe",
    "as needed",
]

SCOPE_BOUNDARY_TERMS = ["対象外", "非対象", "しない", "やらない", "非要求", "非目標", "out of scope", "non-goal", "not"]

CHANGE_CONTROL_TERMS = [
    "変更統制",
    "change control",
    "scope change",
    "範囲変更",
    "追加要求",
    "逸脱",
    "後続",
    "保留",
    "判断待ち",
    "決定点",
    "再計画",
]

MINIMALITY_EXPANSION_TERMS = [
    "新規依存",
    "依存追加",
    "追加依存",
    "new dependency",
    "add dependency",
    "pip install",
    "npm install",
    "external package",
    "third-party package",
    "npm package",
    "python package",
    "pip package",
    "library",
    "framework",
    "middleware",
    "wrapper",
    "factory",
    "interface",
    "adapter",
    "plugin",
    "抽象",
    "抽象化",
    "ラッパ",
    "ラッパー",
    "ファクトリ",
    "インターフェース",
    "アダプタ",
    "アダプター",
    "プラグイン",
    "層",
    "レイヤ",
    "schema",
    "スキーマ",
]

MINIMALITY_JUSTIFICATION_TERMS = [
    "既存",
    "標準",
    "stdlib",
    "standard library",
    "native",
    "platform",
    "平台",
    "再利用",
    "reuse",
    "追加依存なし",
    "no new dependency",
    "不要",
    "作らない",
    "置かない",
    "足さない",
    "増やさない",
    "追加しない",
    "導入しない",
    "使わない",
    "対象外",
    "最小",
    "最小限",
    "minimal",
    "YAGNI",
    "KISS",
    "削る",
    "削除",
    "代替",
    "選定理由",
    "採用理由",
    "必要理由",
    "tradeoff",
    "trade-off",
    "トレードオフ",
]

MINIMALITY_SAFETY_EXEMPTION_TERMS = [
    "入力検証",
    "権限",
    "認証",
    "認可",
    "秘密",
    "証拠",
    "証跡",
    "再現",
    "復旧",
    "rollback",
    "security",
    "accessibility",
    "traceability",
]

UNDERSTANDING_FIELDS: dict[str, list[str]] = {
    "subject_identity": ["対象", "target", "subject", "module", "feature", "document", "機能", "実体", "識別子", "何を扱う"],
    "stakeholders": ["ユーザー", "利用者", "保守", "運用", "作者", "読者", "stakeholder", "user", "maintainer"],
    "current_state": ["現在", "現状", "いま", "current", "as-is", "before", "既存"],
    "desired_state": ["したい", "できる", "なる", "完了", "desired", "to-be", "goal", "実現", "叶える"],
    "purpose": ["なぜ", "目的", "狙い", "why", "intent", "意図", "必要", "解決"],
    "value": ["価値", "意義", "benefit", "value", "効用", "何が変わる"],
    "domain_terms": ["用語", "語彙", "term", "禁則", "alias", "domain"],
    "constraints": ["制約", "条件", "must", "shall", "必要", "禁止", "constraint", "権限", "期限", "守る"],
    "non_goals": ["しない", "対象外", "非対象", "非目標", "非要求", "除外", "not", "non-goal", "out of scope", "やらない"],
    "assumptions": ["前提", "仮定", "assume", "assumption", "推測"],
    "unknowns": ["未確定", "未決", "不明", "判断待ち", "unknown", "tbd", "tbr", "保留", "仮説", "片側", "時点差"],
    "conflicts": ["矛盾", "競合", "衝突", "tradeoff", "conflict"],
    "validation_route": ["確認", "検証", "妥当", "validation", "受入", "受入基準", "acceptance", "証拠", "証跡", "evidence", "テスト"],
}

CRITICAL_UNDERSTANDING = ["purpose", "desired_state", "non_goals", "unknowns", "validation_route"]
INPUT_KINDS = {"requirement", "plan", "document", "diff-summary"}

DECISION_STATE_TERMS: dict[str, list[str]] = {
    "pending_decision": [
        "未決",
        "未決定",
        "未確定",
        "判断待ち",
        "決定待ち",
        "保留",
        "pending decision",
        "to be decided",
        "tbd",
        "tbr",
    ],
    "unknown": ["不明", "未確認", "わからない", "unknown", "unconfirmed", "not confirmed"],
    "hypothesis": ["仮説", "仮定", "assumption", "hypothesis"],
    "inference": ["推測", "推定", "推論", "おそらく", "たぶん", "inference", "inferred", "probably"],
    "one_sided_observation": ["片側観測", "片側", "一方だけ", "one-sided", "single-sided"],
    "time_dependent": ["現時点", "時点差", "最新", "current", "latest", "today", "as of"],
    "value_judgment": ["価値判断", "優先", "重視", "許容", "妥協", "tradeoff", "trade-off", "risk tolerance"],
    "evidence_gap": ["証拠なし", "根拠なし", "証跡なし", "未検証", "裏取りなし", "no evidence", "not verified", "evidence gap"],
}

DECISION_STATE_CONTROL_TERMS: dict[str, list[str]] = {
    "owner": ["owner", "担当", "判断者", "決定者", "decision_owner", "human", "人間"],
    "needed_for": ["needed_for", "必要理由", "何のため", "目的", "goal", "connects_to"],
    "blocking_status": ["blocking", "block", "塞ぐ", "止める", "遮断", "依存"],
    "next_action": ["next_action", "次行動", "次に", "確認", "調査", "検証"],
    "review_at": ["review_at", "再確認", "見直し", "期限", "by ", "until"],
    "evidence_reference": ["evidence", "source", "証拠", "証跡", "根拠", "出典", "ログ"],
}


def understand_target(text: str, context: str = "", strict: bool = True) -> dict[str, object]:
    combined = _combine(text, context)
    field_scores = {field: _score_field(combined, patterns) for field, patterns in UNDERSTANDING_FIELDS.items()}
    findings: list[Finding] = []
    missing: list[str] = []

    for field, score in field_scores.items():
        if score == 0:
            missing.append(field)
        if strict and field in CRITICAL_UNDERSTANDING and score < 2:
            findings.append(
                _missing_field_finding(
                    field=field,
                    patterns=UNDERSTANDING_FIELDS[field],
                    text=combined,
                    severity="blocker",
                    category="understanding",
                    basis=BASIS["requirements"] + BASIS["meaning"],
                    finding=f"対象理解の必須項目 `{field}` が不足している。",
                    suggested_fix=f"`{field}` を明示し、推測なら推測として分ける。",
                    needs_human_decision=field in {"unknowns", "validation_route"},
                )
            )
        elif field in CRITICAL_UNDERSTANDING and score < 2:
            findings.append(
                _missing_field_finding(
                    field=field,
                    patterns=UNDERSTANDING_FIELDS[field],
                    text=combined,
                    severity="major",
                    category="understanding",
                    basis=BASIS["requirements"] + BASIS["meaning"],
                    finding=f"対象理解の重要項目 `{field}` が薄い。",
                    suggested_fix=f"`{field}` を要求または計画に足す。",
                )
            )
        elif score == 0:
            findings.append(
                _missing_field_finding(
                    field=field,
                    patterns=UNDERSTANDING_FIELDS[field],
                    text=combined,
                    severity="info",
                    category="understanding",
                    basis=BASIS["requirements"] + BASIS["meaning"],
                    finding=f"対象理解の補助項目 `{field}` が未記述。",
                    suggested_fix=f"必要なら `{field}` を補足する。不要なら省略してよい。",
                )
            )

    _add_ambiguity_findings(combined, findings)
    return _result(
        phase="understand_target",
        findings=findings,
        missing=missing,
        score=sum(field_scores.values()) / (4 * len(field_scores)),
        details={"field_scores": field_scores},
        next_actions=_next_actions(findings, "対象理解を補完してから要求監査へ進む。"),
    )


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


def audit_decision_state(text: str, context: str = "", strict: bool = True, input_kind: str = "document") -> dict[str, object]:
    """Expose decided, undecided, inferred, hypothetical, and evidence-gap states without resolving them."""
    input_kind = _normalize_input_kind(input_kind)
    combined = _combine(text, context)
    findings: list[Finding] = []
    missing: list[str] = []
    report = _decision_state_report(combined)
    counts = report["counts"]
    control_fields = report["control_fields"]

    if not text.strip():
        findings.append(_blocker("clarity", "監査対象本文が空。", "決定状態を含む本文を渡す。", BASIS["meaning"]))
        missing.append("text")

    if not report["has_explicit_decision_state"]:
        findings.append(
            Finding(
                severity="minor" if strict else "info",
                category="decision_state",
                basis=BASIS["meaning"] + BASIS["planning"],
                finding="決定済み、未決定、仮説、推測、不明、根拠不足の区別が明示されていない。",
                suggested_fix="決定状態を decided / undecided / hypothesis / inferred / unknown / needs_evidence のいずれかで明示する。",
                needs_human_decision=True,
                warning_class="possible false positive",
            )
        )
        missing.append("decision_state_markers")

    unresolved_count = int(report["unresolved_item_count"])
    if unresolved_count:
        findings.append(
            Finding(
                severity="major" if strict else "minor",
                category="decision_state",
                basis=BASIS["meaning"] + BASIS["planning"],
                finding="未決定または不確実な項目がある。監査は露出までで、解決管理は管制面へ渡す必要がある。",
                evidence=str(report["first_unresolved_evidence"]),
                suggested_fix="owner, needed_for, blocking_status, next_action, review_at を付けて管理対象へ移す。",
                needs_human_decision=True,
            )
        )
        missing.append("unresolved_decision_management")
        for field in ("owner", "needed_for", "blocking_status", "next_action", "review_at"):
            if not control_fields[field]:
                missing.append(f"unresolved_{field}")

    if int(counts["value_judgment"]):
        findings.append(
            Finding(
                severity="minor",
                category="value_judgment",
                basis=BASIS["meaning"] + BASIS["planning"],
                finding="価値判断が含まれている。これは監査で自動決定せず、判断主体と判断基準を分ける必要がある。",
                evidence=str(report["first_value_judgment_evidence"]),
                suggested_fix="何を優先し、何を犠牲にする判断なのかを人間の判断点として記録する。",
                needs_human_decision=True,
            )
        )

    if int(counts["evidence_gap"]):
        findings.append(
            Finding(
                severity="major" if strict else "minor",
                category="evidence",
                basis=BASIS["requirements"] + BASIS["meaning"],
                finding="根拠不足または未検証の項目がある。",
                evidence=str(report["first_evidence_gap_evidence"]),
                suggested_fix="根拠、証跡、確認方法、または未検証のまま扱う範囲を明示する。",
            )
        )
        missing.append("decision_evidence")

    if int(counts["hypothesis"]) or int(counts["inference"]):
        findings.append(
            Finding(
                severity="minor",
                category="uncertainty",
                basis=BASIS["meaning"],
                finding="仮説または推測が含まれている。事実と同格に扱わないための境界が必要。",
                evidence=str(report["first_inferential_evidence"]),
                suggested_fix="仮説、推測、確認済み事実を分け、仮説が崩れた時の影響先を書く。",
            )
        )

    return _result(
        phase="audit_decision_state",
        findings=findings,
        missing=sorted(set(missing)),
        score=_score_from_findings(findings),
        details={
            "schema_version": DECISION_STATE_AUDIT_SCHEMA_VERSION,
            "input_kind": input_kind,
            "decision_authority": {
                "audit_scope": "expose decision and uncertainty state",
                "does_not_decide": True,
                "final_decision_owner": "human_or_control_plane",
            },
            "decision_state_report": report,
        },
        next_actions=_next_actions(findings, "決定状態を明示し、未決定項目を管制面の管理対象へ渡す。"),
    )


def apply_logical_trace_mode(result: dict[str, object], mode: str = "summary") -> dict[str, object]:
    normalized = (mode or "summary").strip().lower().replace("_", "-")
    if normalized not in LOGICAL_TRACE_OUTPUT_MODES:
        normalized = "summary"

    details = result.get("details", {})
    if not isinstance(details, dict):
        return dict(result)

    payload = dict(result)
    filtered_details = dict(details)
    if normalized == "summary":
        filtered_details.pop("logical_trace", None)
    elif normalized == "none":
        filtered_details.pop("logical_trace", None)
        filtered_details.pop("logical_trace_summary", None)
        diagnostics = filtered_details.get("diagnostics")
        if isinstance(diagnostics, dict):
            diagnostics = dict(diagnostics)
            diagnostics.pop("logical_trace", None)
            filtered_details["diagnostics"] = diagnostics

    payload["details"] = filtered_details
    return payload


def audit_plan(plan: str, request: str = "", context: str = "", strict: bool = True, input_kind: str = "plan") -> dict[str, object]:
    input_kind = _normalize_input_kind(input_kind)
    combined = _combine(plan, request, context)
    findings: list[Finding] = []
    missing: list[str] = []
    required = {
        "objective": ["目的", "目標", "狙い", "意図", "objective", "goal", "成果", "何を達成"],
        "non_goals": ["対象外", "非対象", "非目標", "非要求", "しない", "やらない", "含めない", "non-goal", "out of scope"],
        "deliverables": ["成果物", "納品物", "出力", "変更物", "deliverable", "ファイル", "artifact"],
        "work_breakdown": ["手順", "段取り", "作業分解", "作業項目", "実施手順", "step", "作業", "実装", "検証", "文書"],
        "dependencies": ["依存", "前提", "順序", "先行", "先に", "dependency", "prerequisite"],
        "risks": ["危険", "リスク", "懸念", "失敗条件", "risk", "失敗", "障害", "副作用"],
        "verification_plan": ["検証", "試験", "テスト", "確認", "検査", "verify", "test", "check"],
        "validation_plan": ["妥当", "受入", "受け入れ", "受入基準", "目的に合う", "validation", "acceptance"],
        "rollback_or_recovery": ["戻", "復旧", "切戻し", "切り戻し", "戻し方", "rollback", "revert", "退避", "backup"],
        "completion_evidence": ["証拠", "証跡", "根拠", "結果", "command", "コマンド", "diff", "スクリーンショット", "evidence"],
        "unknowns_or_decisions": ["未確定", "未決", "不明", "判断待ち", "保留", "決定点", "decision", "unknown", "pending", "tbd"],
    }
    critical = {"objective", "non_goals", "verification_plan", "validation_plan", "completion_evidence"}
    advisory = {"unknowns_or_decisions"}
    planning_structure = _planning_structure_profile(combined)
    planning_signals: dict[str, str] = {}
    non_emitted_rules: list[dict[str, object]] = []

    for field, patterns in required.items():
        diagnostic = _field_match_diagnostic(combined, field, patterns)
        if not _has_any(combined, patterns) and diagnostic.match_status != "matched":
            missing.append(field)
            severity = "blocker" if strict and field in critical else "minor" if field in advisory else "major"
            finding_text = f"計画に `{field}` が見えない。"
            category = "planning"
            rule_id = ""
            suggested_fix = f"`{field}` を計画へ足す。該当なしなら、該当なしと明示する。"
            if field == "rollback_or_recovery":
                rule_id = "plan.risk.rollback_missing"
                finding_text = "計画に復旧またはrollback経路が見えない。"
                category = "risk"
                suggested_fix = "戻し方、退避、fallback、または失敗時の containment を明示する。"
            elif field == "validation_plan":
                rule_id = "plan.validation.problem_fit_missing"
                finding_text = "計画に妥当性確認が見えない。"
                category = "validation"
                suggested_fix = "成果物が目的に合うことを誰が何で確認するか明示する。"
            finding = _missing_field_finding(
                field=field,
                patterns=patterns,
                text=combined,
                severity=severity,
                category=category,
                basis=BASIS["planning"],
                finding=finding_text,
                suggested_fix=suggested_fix,
                diagnostic=diagnostic,
            )
            finding.rule_id = rule_id
            findings.append(finding)

    planning_signals = _planning_quality_signals(plan, combined, planning_structure)
    non_emitted_rules.extend(_planning_suppression_traces(plan, combined))
    _add_planning_quality_findings(planning_signals, findings, missing, strict)

    if request and not _has_overlap(_tokens(request), _tokens(plan), minimum=3):
        findings.append(
            Finding(
                severity="major",
                category="traceability",
                basis=BASIS["planning"] + BASIS["requirements"],
                finding="要求と計画の語彙接続が弱い。計画が要求を覆っていない可能性がある。",
                suggested_fix="要求項目ごとに対応する作業と検証を紐付ける。",
            )
        )

    if _has_any(plan, ["全部", "全体", "全面", "まとめて", "rewrite all", "refactor all"]):
        broad_scope_evidence = _first_match(plan, ["全部", "全体", "全面", "まとめて", "rewrite all", "refactor all"])
        if _has_bounded_broad_scope_controls(plan, combined):
            non_emitted_rules.append(
                _suppression_trace(
                    phase="audit_plan",
                    rule_id="plan.scope.broad_scope_unbounded",
                    emission_status="satisfied",
                    reason="broad_scope_has_work_package_controls",
                    evidence=broad_scope_evidence,
                    source="planning_scope_guardrail",
                )
            )
        else:
            findings.append(
                Finding(
                    severity="major",
                    category="scope",
                    basis=BASIS["planning"],
                    finding="範囲が広がりすぎている可能性がある。",
                    evidence=broad_scope_evidence,
                    suggested_fix="成果物単位に分割し、変更禁止領域と段階境界を置く。",
                )
            )

    return _result(
        phase="audit_plan",
        findings=findings,
        missing=sorted(set(missing)),
        score=_score_from_findings(findings),
        details={
            "required_fields": sorted(required),
            "input_kind": input_kind,
            "planning_signals": planning_signals,
            "planning_structure": planning_structure,
            "non_emitted_rules": non_emitted_rules,
            "suppressed_rules": non_emitted_rules,
        },
        next_actions=_next_actions(findings, "計画に欠けた欄を補完し、必要なら再監査する。"),
    )


def audit_diff(diff: str, intent: str = "", context: str = "", strict: bool = True, input_kind: str = "diff-summary") -> dict[str, object]:
    input_kind = _normalize_input_kind(input_kind)
    combined = _combine(diff, intent, context)
    findings: list[Finding] = []
    missing: list[str] = []
    changed_files = _changed_files(diff)

    if not diff.strip():
        findings.append(_blocker("evidence", "差分が空。", "unified diff または変更要約を渡す。", BASIS["implementation"]))
        missing.append("diff")

    if not intent.strip():
        findings.append(
            Finding(
                severity="major",
                category="traceability",
                basis=BASIS["implementation"] + BASIS["requirements"],
                finding="変更意図が渡されていない。",
                suggested_fix="要求または計画を `intent` として渡し、差分との対応を見る。",
            )
        )
        missing.append("intent")

    security_evidence = _security_signal(diff)
    if security_evidence:
        findings.append(
            Finding(
                severity="major",
                category="security",
                basis=BASIS["security"],
                finding="安全性に関わる差分の可能性がある。",
                evidence=security_evidence,
                suggested_fix="入力、出力、認証、認可、秘密、ログ、依存、構成の確認証拠を残す。",
            )
        )

    implementation_signals = _implementation_change_signals(diff, changed_files)
    _add_implementation_findings(implementation_signals, findings, missing, strict)

    source_changed = any(_is_source_file(path) for path in changed_files)
    test_changed = any(_is_test_file(path) for path in changed_files)
    if source_changed and not test_changed:
        findings.append(
            Finding(
                severity="major" if strict else "minor",
                category="quality",
                basis=BASIS["implementation"],
                finding="ソース変更に対する試験差分または確認証拠が見えない。",
                evidence=", ".join(changed_files[:5]),
                suggested_fix="試験を追加・更新するか、不要な理由と実行した確認を finish_check に残す。",
                rule_id="diff.test_obligation.source_without_tests",
            )
        )
        missing.append("test_obligation")

    semantic_boundaries = _semantic_boundaries(diff)
    document_only_boundaries: list[dict[str, object]] = []
    reportable_boundaries: list[dict[str, str]] = []
    if semantic_boundaries:
        for boundary in semantic_boundaries:
            if _is_document_only_boundary(boundary, changed_files):
                document_only_boundaries.append(
                    {
                        **boundary,
                        "emission_status": "document_only",
                        "reason": "docs_only_evidence_language",
                    }
                )
            else:
                reportable_boundaries.append(boundary)

    if reportable_boundaries:
        boundary_names = [boundary["boundary"] for boundary in reportable_boundaries]
        boundary_evidence = _unique_nonempty([str(boundary["evidence"]) for boundary in reportable_boundaries])
        findings.append(
            Finding(
                severity="minor",
                category="meaning",
                basis=BASIS["meaning"],
                finding="名前、表示、識別子、保管、所属、正典に関わる差分の可能性がある。",
                evidence="; ".join(boundary_evidence[:3]),
                suggested_fix=_semantic_boundary_fix(boundary_names),
                warning_class="generic caution",
                semantic_boundaries=boundary_names,
                rule_id="diff.meaning.identity_boundary_change",
            )
        )

    complexity_growth = _complexity_growth_signal(diff)
    if complexity_growth:
        finding = (
            Finding(
                severity="minor",
                category="minimality",
                basis=BASIS["implementation"] + BASIS["minimality"],
                finding="差分で複雑性が増えている可能性がある。",
                evidence=complexity_growth,
                suggested_fix="必要な安全・証跡・失敗処理を残したまま、不要な抽象、分岐、将来対応、新規依存、標準機能の手製実装を削れないか確認する。",
                warning_class="generic caution",
            )
        )
        finding.rule_id = "diff.implementation.complexity_growth"
        findings.append(finding)

    if changed_files and not any(_is_doc_file(path) for path in changed_files) and _has_any(intent + context, ["仕様", "README", "docs", "運用", "設定", "migration", "移行"]):
        findings.append(
            Finding(
                severity="minor",
                category="documentation",
                basis=BASIS["implementation"],
                finding="文書更新が必要そうな意図に対して文書差分が見えない。",
                suggested_fix="仕様、README、設定例、移行手順の更新要否を finish_check で明記する。",
            )
        )

    return _result(
        phase="audit_diff",
        findings=findings,
        missing=sorted(set(missing)),
        score=_score_from_findings(findings),
        details={
            "changed_files": changed_files[:50],
            "changed_file_count": len(changed_files),
            "input_kind": input_kind,
            "semantic_boundaries": semantic_boundaries,
            "document_only_boundaries": document_only_boundaries,
            "implementation_signals": implementation_signals,
            "complexity_growth": complexity_growth,
        },
        next_actions=_next_actions(findings, "差分の根拠、試験、文書、安全確認を補完する。"),
    )


def finish_check(summary: str, evidence: str = "", context: str = "", strict: bool = True) -> dict[str, object]:
    combined = _combine(summary, evidence, context)
    findings: list[Finding] = []
    missing: list[str] = []

    if not summary.strip():
        findings.append(_blocker("evidence", "完了要約が空。", "変更内容と完了範囲を書く。", BASIS["implementation"]))
        missing.append("summary")

    if not _has_any(combined, ["test", "pytest", "swift test", "npm test", "uv run", "検証", "確認", "コマンド", "実行"]):
        findings.append(
            Finding(
                severity="blocker" if strict else "major",
                category="evidence",
                basis=BASIS["implementation"],
                finding="検証証拠が見えない。",
                suggested_fix="実行したコマンド、結果、または未実行理由を記録する。",
                rule_id="finish.evidence.tests_missing",
            )
        )
        missing.append("tests_ran_or_reason")

    if not _has_any(combined, ["受入", "acceptance", "完了条件", "criteria", "evidence", "証拠", "結果"]):
        findings.append(
            Finding(
                severity="major",
                category="validation",
                basis=BASIS["requirements"] + BASIS["planning"],
                finding="受入条件と証拠の対応が薄い。",
                suggested_fix="要求または目的に対して、何をもって完了としたかを明記する。",
            )
        )
        missing.append("acceptance_evidence")

    if _security_signal(combined) and not _has_any(combined, ["secret scan", "dependency", "owasp", "nist", "安全", "セキュリティ", "手動確認"]):
        findings.append(
            Finding(
                severity="major",
                category="security",
                basis=BASIS["security"],
                finding="安全性に関わる変更の証拠が不足している。",
                suggested_fix="秘密情報、依存、認証認可、入力出力、ログの確認結果を記録する。",
            )
        )
        missing.append("security_evidence")

    if _implemented_public_behavior(combined) and not _has_behavior_evidence(combined):
        findings.append(
            Finding(
                severity="major" if strict else "minor",
                category="behavior",
                basis=BASIS["implementation"],
                finding="実装した公開挙動に対する代表実行証拠が見えない。",
                suggested_fix="単体試験だけでなく、代表 CLI/API/MCP 実行、smoke test、出力契約確認、または未実行理由を記録する。",
                warning_class="generic caution",
                rule_id="finish.implementation.behavior_evidence_missing",
            )
        )
        missing.append("behavior_evidence")

    if not _has_any(combined, ["残リスク", "未実行", "未確認", "できなかった", "not run", "residual", "risk", "none"]):
        findings.append(
            Finding(
                severity="info",
                category="risk",
                basis=BASIS["planning"],
                finding="残リスクまたは未実行事項の有無が明示されていない。",
                suggested_fix="残リスクが無い場合も `残リスクなし` と書く。",
            )
        )

    return _result(
        phase="finish_check",
        findings=findings,
        missing=sorted(set(missing)),
        score=_score_from_findings(findings),
        details={},
        next_actions=_next_actions(findings, "証拠と残リスクを補完してから完了報告する。"),
    )


def _decision_state_report(text: str) -> dict[str, object]:
    units = _decision_state_units(text)
    control_values = _decision_control_values(text)
    items: list[dict[str, object]] = []
    explicit_categories: list[str] = []
    none_categories: list[str] = []

    for category, terms in DECISION_STATE_TERMS.items():
        category_explicit = False
        for unit in units:
            if not _has_any(unit, terms):
                continue
            category_explicit = True
            if _decision_state_unit_declares_none(unit, terms):
                none_categories.append(category)
                continue
            items.append(_decision_state_item(category, unit, control_values))
        if category_explicit:
            explicit_categories.append(category)

    items = _unique_decision_state_items(items)
    counts = {category: sum(1 for item in items if item["uncertainty_kind"] == category) for category in DECISION_STATE_TERMS}
    unresolved_categories = {
        "pending_decision",
        "unknown",
        "hypothesis",
        "inference",
        "one_sided_observation",
        "time_dependent",
        "value_judgment",
        "evidence_gap",
    }
    unresolved_items = [item for item in items if str(item["uncertainty_kind"]) in unresolved_categories]
    first_by_category = {category: _first_item_evidence(items, category) for category in DECISION_STATE_TERMS}

    return {
        "has_explicit_decision_state": bool(explicit_categories),
        "explicit_categories": sorted(set(explicit_categories)),
        "none_categories": sorted(set(none_categories)),
        "counts": counts,
        "unresolved_item_count": len(unresolved_items),
        "first_unresolved_evidence": _first_item_evidence(unresolved_items, ""),
        "first_value_judgment_evidence": first_by_category["value_judgment"],
        "first_evidence_gap_evidence": first_by_category["evidence_gap"],
        "first_inferential_evidence": _first_item_evidence(
            [item for item in items if item["uncertainty_kind"] in {"hypothesis", "inference"}],
            "",
        ),
        "control_fields": _decision_control_coverage(text),
        "control_values": control_values,
        "management_handoff_items": items,
    }


def _decision_state_units(text: str) -> list[str]:
    units: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        fragments = [fragment.strip(" \t-・*") for fragment in re.split(r"[。！？!?]\s*", stripped)]
        units.extend(fragment for fragment in fragments if fragment)
    if not units and text.strip():
        return [_compact_snippet(text)]
    return units


def _decision_state_unit_declares_none(unit: str, terms: list[str]) -> bool:
    lower = unit.lower()
    none_terms = ("なし", "無し", "ない", "該当なし", "none", "n/a", "not applicable")
    for term in terms:
        pattern = rf"{re.escape(term.lower())}[^。\n]{{0,24}}[:：=\\-]\s*({'|'.join(re.escape(item) for item in none_terms)})"
        if re.search(pattern, lower):
            return True
    return False


def _decision_state_item(category: str, unit: str, control_values: dict[str, object] | None = None) -> dict[str, object]:
    kind, state = _decision_state_kind_and_state(category)
    excerpt = _compact_snippet(unit)
    controls = control_values or {}
    suggested_owner = _extract_labeled_value(unit, DECISION_STATE_CONTROL_TERMS["owner"]) or str(controls.get("owner", ""))
    needed_for = _extract_labeled_values(unit, DECISION_STATE_CONTROL_TERMS["needed_for"]) or list(controls.get("needed_for", []))
    blocking_status = _decision_blocking_status(unit)
    if blocking_status == "unknown":
        blocking_status = str(controls.get("blocking_status", "unknown"))
    review_at = _extract_labeled_value(unit, DECISION_STATE_CONTROL_TERMS["review_at"]) or str(controls.get("review_at", ""))
    return {
        "kind": kind,
        "uncertainty_kind": category,
        "decision_state": state,
        "source_excerpt": excerpt,
        "suggested_owner": suggested_owner,
        "needed_for": needed_for,
        "blocking_status": blocking_status,
        "next_action": _decision_next_action(category, unit, str(controls.get("next_action", ""))),
        "review_at": review_at,
    }


def _decision_state_kind_and_state(category: str) -> tuple[str, str]:
    mapping = {
        "pending_decision": ("unresolved_decision", "undecided"),
        "unknown": ("unknown", "unknown"),
        "hypothesis": ("hypothesis", "hypothesis"),
        "inference": ("inference", "inferred"),
        "one_sided_observation": ("one_sided_observation", "unknown"),
        "time_dependent": ("time_dependent_item", "pending"),
        "value_judgment": ("value_judgment", "pending"),
        "evidence_gap": ("evidence_gap", "needs_evidence"),
    }
    return mapping.get(category, ("uncertainty", "unknown"))


def _decision_blocking_status(unit: str) -> str:
    lower = unit.lower()
    if any(term in lower for term in ["not blocking", "non-blocking", "塞がない", "止めない", "遮断しない"]):
        return "not_blocking"
    if _has_any(unit, DECISION_STATE_CONTROL_TERMS["blocking_status"]):
        return "blocking"
    return "unknown"


def _decision_next_action(category: str, unit: str, fallback_explicit: str = "") -> str:
    explicit = _extract_labeled_value(unit, DECISION_STATE_CONTROL_TERMS["next_action"]) or fallback_explicit
    if explicit:
        return explicit
    defaults = {
        "pending_decision": "決定者、判断条件、期限を置く。",
        "unknown": "確認先と証拠取得方法を決める。",
        "hypothesis": "検証方法を定め、仮説のまま使う範囲を制限する。",
        "inference": "推測の根拠と反証条件を残す。",
        "one_sided_observation": "反対側または欠けた観測元を確認する。",
        "time_dependent": "再確認時点を置き、時点依存の根拠を更新する。",
        "value_judgment": "人間の判断点として判断基準を明示する。",
        "evidence_gap": "根拠となる一次証跡を取得する。",
    }
    return defaults.get(category, "管理対象として次行動を決める。")


def _extract_labeled_value(text: str, labels: Iterable[str]) -> str:
    for label in labels:
        match = re.search(rf"{re.escape(label)}\s*[:：=]\s*([^、。\n;；]+)", text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ""


def _extract_labeled_values(text: str, labels: Iterable[str]) -> list[str]:
    value = _extract_labeled_value(text, labels)
    if not value:
        return []
    return [item.strip() for item in re.split(r"[,，、/]+", value) if item.strip()]


def _decision_control_coverage(text: str) -> dict[str, bool]:
    return {field: _has_any(text, terms) for field, terms in DECISION_STATE_CONTROL_TERMS.items()}


def _decision_control_values(text: str) -> dict[str, object]:
    return {
        "owner": _extract_labeled_value(text, DECISION_STATE_CONTROL_TERMS["owner"]),
        "needed_for": _extract_labeled_values(text, DECISION_STATE_CONTROL_TERMS["needed_for"]),
        "blocking_status": _decision_blocking_status(text),
        "next_action": _extract_labeled_value(text, DECISION_STATE_CONTROL_TERMS["next_action"]),
        "review_at": _extract_labeled_value(text, DECISION_STATE_CONTROL_TERMS["review_at"]),
    }


def _unique_decision_state_items(items: list[dict[str, object]]) -> list[dict[str, object]]:
    unique: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()
    for item in items:
        key = (str(item["uncertainty_kind"]), str(item["source_excerpt"]))
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def _first_item_evidence(items: list[dict[str, object]], category: str) -> str:
    for item in items:
        if category and item.get("uncertainty_kind") != category:
            continue
        evidence = str(item.get("source_excerpt", ""))
        if evidence:
            return evidence
    return ""


def _combine(*parts: str) -> str:
    return "\n".join(part for part in parts if part)


def _normalize_input_kind(input_kind: str) -> str:
    normalized = (input_kind or "requirement").strip().lower().replace("_", "-")
    if normalized not in INPUT_KINDS:
        return "requirement"
    return normalized


def _audit_document(text: str, context: str = "", strict: bool = True, input_kind: str = "document") -> dict[str, object]:
    combined = _combine(text, context)
    findings: list[Finding] = []
    missing: list[str] = []
    fields = {
        "purpose_or_overview": ["purpose", "overview", "what", "目的", "概要", "要旨", "何", "狙い", "位置づけ"],
        "audience_or_use": ["when to use", "use when", "audience", "reader", "読者", "利用者", "使いどころ", "用途", "誰"],
        "status_or_scope": ["status", "scope", "prototype", "alpha", "状態", "範囲", "試作", "現状", "適用範囲"],
        "usage_or_examples": ["usage", "example", "cli", "mcp", "使い方", "使用法", "例", "実行例", "設定"],
        "output_or_contract": ["output", "json", "schema", "contract", "出力", "契約", "構造", "返却", "項目"],
        "limitations_or_non_goals": ["limitations", "do not", "not ", "non-goal", "out of scope", "制限", "限界", "対象外", "しない", "非目標"],
    }
    critical = {"purpose_or_overview", "usage_or_examples", "limitations_or_non_goals"}
    field_scores = {field: _score_field(combined, patterns) for field, patterns in fields.items()}

    if not text.strip():
        findings.append(_blocker("clarity", "文書本文が空。", "文書本文を渡す。", BASIS["requirements"]))
        missing.append("document_text")

    for field, score in field_scores.items():
        patterns = fields[field]
        if score == 0:
            missing.append(field)
            findings.append(
                _missing_field_finding(
                    field=field,
                    patterns=patterns,
                    text=combined,
                    severity="major" if strict and field in critical else "info",
                    category="documentation",
                    basis=BASIS["requirements"] + BASIS["meaning"],
                    finding=f"文書監査項目 `{field}` が見えない。",
                    suggested_fix=f"`{field}` に相当する節や説明を足す。",
                )
            )

    document_checks = _document_validity_checks(combined, findings, missing)
    claim_triples = _document_claim_triples(combined, findings)
    document_claim_summary = _document_claim_summary(claim_triples)
    coverage_score = sum(field_scores.values()) / (4 * len(field_scores)) if field_scores else 0.0
    return _result(
        phase="audit_request",
        findings=findings,
        missing=sorted(set(missing)),
        score=min(coverage_score, _score_from_findings(findings)),
        details={
            "input_kind": input_kind,
            "document_field_scores": field_scores,
            "document_checks": document_checks,
            "claim_triples": claim_triples,
            "document_claim_summary": document_claim_summary,
        },
        next_actions=_next_actions(findings, "文書の目的、使い方、制限、出力契約を補う。"),
    )


def _has_any(text: str, needles: Iterable[str]) -> bool:
    lower = text.lower()
    return any(needle.lower() in lower for needle in needles)


def _first_match(text: str, needles: Iterable[str]) -> str:
    lower = text.lower()
    for needle in needles:
        index = lower.find(needle.lower())
        if index >= 0:
            return _excerpt_around(text, index, index + len(needle))
    return ""


def _excerpt_around(text: str, start: int, end: int, limit: int = DEFAULT_SNIPPET_LIMIT) -> str:
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", end)
    if line_end < 0:
        line_end = len(text)
    line = text[line_start:line_end].strip()
    if line:
        relative_start = max(0, start - line_start)
        relative_end = max(relative_start, end - line_start)
        if len(line) > limit and relative_start >= limit // 2:
            return _compact_snippet_around(line, relative_start, relative_end, limit)
        return _compact_snippet(line, limit)

    before = max(text.rfind(mark, 0, start) for mark in ("\n", "。", ".", "!", "?"))
    after_candidates = [text.find(mark, end) for mark in ("\n", "。", ".", "!", "?")]
    after_candidates = [candidate for candidate in after_candidates if candidate >= 0]
    snippet_start = before + 1 if before >= 0 else 0
    snippet_end = min(after_candidates) + 1 if after_candidates else len(text)
    return _compact_snippet(text[snippet_start:snippet_end].strip(), limit)


def _compact_snippet(text: str, limit: int = DEFAULT_SNIPPET_LIMIT) -> str:
    cleaned = "\n".join(line.rstrip() for line in text.strip().splitlines())
    if len(cleaned) <= limit:
        return cleaned

    boundary_chars = ".!?。！？、，,;；:：)]}」』"
    cut = -1
    for index in range(limit - 1, max(0, limit // 2), -1):
        if cleaned[index] in boundary_chars or cleaned[index].isspace():
            cut = index + 1
            break
    if cut < 0:
        cut = limit

    return cleaned[:cut].rstrip() + "..."


def _compact_snippet_around(text: str, start: int, end: int, limit: int = DEFAULT_SNIPPET_LIMIT) -> str:
    cleaned = text.strip()
    if len(cleaned) <= limit:
        return cleaned

    content_limit = max(32, limit - 6)
    window_start = max(0, start - content_limit // 2)
    window_end = min(len(cleaned), window_start + content_limit)
    if end > window_end:
        window_end = min(len(cleaned), end + content_limit // 2)
        window_start = max(0, window_end - content_limit)

    if window_start > 0:
        whitespace = cleaned.find(" ", window_start, min(len(cleaned), window_start + 24))
        punctuation = min(
            [idx for idx in (cleaned.find(mark, window_start, min(len(cleaned), window_start + 24)) for mark in "、，,;；:：") if idx >= 0],
            default=-1,
        )
        boundary = whitespace if whitespace >= 0 else punctuation
        if boundary >= 0 and boundary < start:
            window_start = boundary + 1

    if window_end < len(cleaned):
        for idx in range(window_end, max(window_start, window_end - 40), -1):
            if cleaned[idx - 1].isspace() or cleaned[idx - 1] in ".!?。！？、，,;；:：)]}」』":
                window_end = idx
                break

    prefix = "..." if window_start > 0 else ""
    suffix = "..." if window_end < len(cleaned) else ""
    return prefix + cleaned[window_start:window_end].strip() + suffix


def _compact_code_snippet(text: str, limit: int = DEFAULT_SNIPPET_LIMIT) -> str:
    cleaned = "\n".join(line.rstrip() for line in text.strip().splitlines())
    if len(cleaned) <= limit:
        return cleaned

    lines = cleaned.splitlines()
    selected: list[str] = []
    total = 0
    for line in lines:
        next_total = total + len(line) + (1 if selected else 0)
        if selected and next_total > max(16, limit - 8):
            break
        selected.append(line)
        total = next_total
        if total >= max(16, limit - 8):
            break

    if not selected:
        return _compact_snippet(cleaned, limit)

    if selected[0].startswith("```") and not selected[-1].startswith("```"):
        selected.append("...")
        selected.append("```")
    else:
        selected[-1] = selected[-1].rstrip() + "..."
    return "\n".join(selected)


def _suppression_trace(
    *,
    phase: str,
    rule_id: str,
    emission_status: str = "not_applicable",
    reason: str,
    evidence: str,
    source: str,
    confidence: str = "high",
    match_status: str = "",
) -> dict[str, object]:
    if not match_status:
        match_status = "matched" if emission_status == "satisfied" else "not_applicable"
    trace: dict[str, object] = {
        "phase": phase,
        "rule_id": rule_id,
        "emission_status": emission_status,
        "match_status": match_status,
        "confidence": confidence,
        "reason": reason,
        "source": source,
    }
    if evidence:
        trace["evidence"] = evidence
    return trace


FIELD_CANDIDATE_HINTS: dict[str, list[str]] = {
    "objective": ["背景", "狙い", "到達点", "期待結果", "何をする"],
    "purpose_trace": ["背景", "理由", "狙い", "課題", "困りごと"],
    "non_goals": ["除外", "非対象", "範囲外", "今回は", "やらないこと"],
    "non_requirements": ["除外", "範囲外", "今回は", "やらないこと"],
    "stakeholder_source": ["利用者", "受入者", "依頼元", "関係者", "誰のため"],
    "quality_constraint": ["指標", "閾値", "測定", "許容", "性能条件"],
    "priority": ["優先", "重要度", "順序", "先に", "後で"],
    "uncertainty_classification": ["未確定", "仮説", "判断待ち", "保留", "片側観測"],
    "deliverables": ["納品", "作るもの", "更新対象", "変更対象"],
    "work_breakdown": ["進め方", "工程", "作業列", "段階", "着手順", "work package decomposition", "work package"],
    "dependencies": ["必要条件", "先行条件", "前提条件", "依存先"],
    "risks": ["懸念", "注意", "怖い点", "失敗時"],
    "verification_plan": ["検査", "点検", "動作確認", "試す", "見る"],
    "verification_or_acceptance": ["検査", "点検", "動作確認", "試す", "見る"],
    "validation_plan": ["受入基準", "合格条件", "目的適合", "人間確認"],
    "rollback_or_recovery": ["切戻し", "戻し方", "退避先", "復元"],
    "completion_evidence": ["証跡", "根拠", "ログ", "実行結果", "確認結果"],
    "unknowns_or_decisions": ["未決", "判断点", "確認待ち", "決めること", "不明点"],
    "unknowns": ["未決", "判断点", "確認待ち", "決めること", "不明点"],
    "validation_owner": ["判断主体", "受入者", "承認者", "誰が", "人間確認"],
    "progress_control": ["進捗", "確認点", "中間", "節目", "状態報告"],
    "change_control": ["変更統制", "範囲変更", "追加要求", "逸脱", "判断点"],
    "work_package_decomposition": ["作業分解", "作業パッケージ", "成果物分解", "WBS", "担当別", "ファイル別"],
    "dependency_sequence": ["順序", "先行", "後続", "前後関係", "依存関係", "critical path"],
    "estimation_or_resource_basis": ["見積", "工数", "所要時間", "資源", "担当", "capacity", "duration"],
    "risk_response": ["対策", "緩和", "回避", "代替", "退避", "contingency", "fallback"],
    "control_baseline": ["基準線", "基準", "指標", "閾値", "milestone", "baseline", "判定基準"],
    "decision_gate": ["決定点", "判断ゲート", "承認", "停止条件", "go/no-go", "継続判断"],
}


def _missing_field_finding(
    *,
    field: str,
    patterns: list[str],
    text: str,
    severity: str,
    category: str,
    basis: list[str],
    finding: str,
    suggested_fix: str,
    needs_human_decision: bool = False,
    diagnostic: FieldMatchDiagnostic | None = None,
) -> Finding:
    direct_evidence = _excerpt_for_field(text, patterns)
    diagnostic = diagnostic or _field_match_diagnostic(text, field, patterns)
    candidates = diagnostic.nearest_candidates
    ambiguity_reasons = diagnostic.ambiguity_reasons
    return Finding(
        severity=severity,  # type: ignore[arg-type]
        category=category,
        basis=basis,
        finding=finding,
        evidence=direct_evidence or (candidates[0] if candidates else ""),
        suggested_fix=suggested_fix,
        needs_human_decision=needs_human_decision,
        warning_class="possible false positive" if candidates else "actionable",
        nearest_candidates=candidates,
        match_status=diagnostic.match_status,
        confidence=diagnostic.confidence,
        ambiguity_reasons=ambiguity_reasons,
        candidate_matches=diagnostic.candidate_matches,
    )


def _field_match_diagnostic(text: str, field: str, patterns: list[str]) -> FieldMatchDiagnostic:
    return diagnose_field_match(
        text,
        field,
        patterns,
        weak_hints=FIELD_CANDIDATE_HINTS.get(field, []),
    )


def _nearest_candidates(text: str, field: str, patterns: list[str], limit: int = 2) -> list[str]:
    lines = _candidate_lines(text)
    if not lines:
        return []

    field_tokens = _tokens(field.replace("_", " "))
    hints = FIELD_CANDIDATE_HINTS.get(field, []) + patterns
    scored: list[tuple[int, str]] = []
    for line in lines:
        lower = line.lower()
        tokens = _tokens(line)
        score = len((tokens & field_tokens) - {"or", "and"})
        for hint in hints:
            if hint.lower() in lower:
                score += 3
        if re.match(r"^\s*(#{1,4}|\d+[.)]|[-*])?\s*[^:：]{1,24}[:：]", line):
            score += 1
        if score > 0:
            scored.append((score, line.strip()[:220]))

    if scored:
        scored.sort(key=lambda item: (-item[0], len(item[1])))
        return _unique_nonempty([line for _, line in scored[:limit]])

    heading_like = [
        line.strip()[:220]
        for line in lines
        if re.match(r"^\s*(#{1,4}\s+|[-*]\s+|\d+[.)]\s+)?[^:：]{1,28}[:：]", line)
    ]
    return _unique_nonempty(heading_like[:limit])


def _candidate_lines(text: str) -> list[str]:
    stripped = _strip_code_blocks(text)
    raw_lines = [line.strip() for line in stripped.splitlines()]
    lines = [line for line in raw_lines if line and not line.startswith("|")]
    structured = [
        line
        for line in lines
        if re.match(r"^\s*(#{1,4}\s+|[-*]\s+|\d+[.)]\s+)?\S", line)
        and (":" in line or "：" in line or line.startswith(("#", "-", "*")) or len(line) <= 90)
    ]
    if structured:
        return structured[:80]
    return [sentence.strip() for sentence in re.split(r"(?<=[.!?。])\s+|\n+", stripped) if sentence.strip()][:80]


def _security_signal(text: str) -> str:
    japanese_terms = ["認証", "認可", "権限", "秘密", "暗号", "資格情報"]
    match = _first_match(text, japanese_terms)
    if match:
        return match

    patterns = [
        r"\bauth(?:entication|orization)?\b",
        r"\bpasswords?\b",
        r"\btokens?\b",
        r"\bsecrets?\b",
        r"\bcredentials?\b",
        r"\bpermissions?\b",
        r"\buser roles?\b",
        r"\badmin roles?\b",
        r"\brbac\b",
        r"\bencrypt(?:ion|ed|s)?\b",
        r"\bdecrypt(?:ion|ed|s)?\b",
        r"\bsql\b",
        r"\bshell\b",
        r"\bcommand injection\b",
        r"\bsubprocess\b",
        r"\bpath traversal\b",
        r"\buploads?\b",
        r"\bcookies?\b",
        r"\bsessions?\b",
    ]
    for pattern in patterns:
        match_obj = re.search(pattern, text, re.IGNORECASE)
        if match_obj:
            start, end = match_obj.span()
            return text[max(0, start - 40): min(len(text), end + 40)].strip()
    return ""


def _has_implementation_evidence(text: str) -> bool:
    return _has_any(
        text,
        [
            "unittest",
            "pytest",
            "npm test",
            "swift test",
            "uv run",
            "passed",
            "ok",
            "実行済み",
            "確認済み",
            "試験済み",
            "テスト済み",
            "結果:",
            "結果：",
            "検証結果",
        ],
    )


def _requirement_achievement_profile(text: str) -> dict[str, str]:
    if not text.strip():
        return {
            "acceptance_criteria": "",
            "verification_method": "",
            "evidence_artifact": "",
            "acceptance_owner": "",
            "rejection_condition": "",
            "scenario_context": "",
        }

    return {
        "acceptance_criteria": _acceptance_criteria_signal(text),
        "verification_method": _verification_method_signal(text),
        "evidence_artifact": _evidence_artifact_signal(text),
        "acceptance_owner": _stakeholder_source_signal(text),
        "rejection_condition": _rejection_condition_signal(text),
        "scenario_context": _scenario_context_signal(text),
    }


def _requirement_structure_profile(text: str) -> dict[str, str]:
    if not text.strip():
        return {
            "observable_behavior": "",
            "precondition_or_trigger": "",
            "expected_result": "",
            "interface_contract": "",
        }

    return {
        "observable_behavior": _observable_behavior_signal(text),
        "precondition_or_trigger": _precondition_or_trigger_signal(text),
        "expected_result": _expected_result_signal(text),
        "interface_contract": _interface_contract_signal(text),
    }


def _requirement_quality_signals(
    text: str,
    combined: str,
    profile: dict[str, str],
    structure: dict[str, str],
) -> dict[str, str]:
    if not text.strip():
        return {}

    signals: dict[str, str] = {}
    stakeholder_source = _stakeholder_source_signal(combined)
    if not stakeholder_source:
        signals["stakeholder_source"] = ""

    quality_claim = _quality_requirement_signal(combined)
    if quality_claim and not _has_quality_constraint_evidence(combined):
        signals["quality_constraint"] = quality_claim

    if _looks_multi_requirement(text) and not _has_priority_evidence(combined) and not _is_bounded_work_package_request(text, combined):
        signals["priority"] = _first_match(text, [" and ", " or ", "かつ", "または", "及び", "および", "、"])

    uncertainty = _unclassified_uncertainty_signal(combined)
    if uncertainty:
        signals["uncertainty_classification"] = uncertainty

    problem_mechanism_gap = _problem_mechanism_fit_signal(combined)
    if problem_mechanism_gap:
        signals["problem_mechanism_fit"] = problem_mechanism_gap

    symptom_only_success = _symptom_only_success_signal(combined)
    if symptom_only_success:
        signals["symptom_only_success"] = symptom_only_success

    if _has_verification_or_acceptance_language(combined) and not profile["acceptance_criteria"]:
        signals["achievement_criteria"] = _first_match(
            combined,
            ["検証", "確認", "受入", "acceptance", "verify", "test", "evidence"],
        )

    if _has_verification_or_acceptance_language(combined) and not profile["verification_method"]:
        signals["verification_method_detail"] = _first_match(
            combined,
            ["検証", "確認", "試験", "テスト", "acceptance", "verify", "test"],
        )

    if (
        profile["acceptance_criteria"]
        or profile["verification_method"]
        or _has_verification_or_acceptance_language(combined)
    ) and not profile["evidence_artifact"]:
        signals["evidence_artifact"] = profile["acceptance_criteria"] or profile["verification_method"]

    if _requires_rejection_condition(combined) and not profile["rejection_condition"]:
        signals["rejection_condition"] = _first_match(
            combined,
            ["安全", "権限", "削除", "移行", "公開", "運用", "認証", "認可", "security", "permission", "delete", "migration"],
        )

    if _requires_scenario_context(combined) and not profile["scenario_context"]:
        signals["scenario_context"] = _first_match(
            combined,
            ["画面", "ユーザー", "利用者", "入力", "操作", "通知", "表示", "検索", "UI", "user", "screen", "input"],
        )

    vague_behavior = _vague_behavior_signal(combined)
    if vague_behavior and not structure["observable_behavior"]:
        signals["observable_behavior"] = vague_behavior

    if _requires_precondition_or_trigger(combined) and not structure["precondition_or_trigger"]:
        signals["precondition_or_trigger"] = _first_match(
            combined,
            ["画面", "UI", "ユーザー", "利用者", "入力", "操作", "検索", "通知", "API", "CLI", "JSON", "user", "input"],
        )

    if _requires_expected_result(combined) and not structure["expected_result"]:
        signals["expected_result"] = _first_match(
            combined,
            ["入力", "操作", "検索", "表示", "通知", "API", "CLI", "JSON", "output", "return", "screen"],
        )

    interface_surface = _interface_surface_signal(combined)
    if interface_surface and not structure["interface_contract"]:
        signals["interface_contract"] = interface_surface

    return signals


def _add_requirement_quality_findings(
    signals: dict[str, str],
    findings: list[Finding],
    missing: list[str],
    strict: bool,
    *,
    achievement_criteria_derivation: dict[str, object],
    method_detail_derivation: dict[str, object],
    evidence_artifact_derivation: dict[str, object],
    rejection_condition_derivation: dict[str, object],
    scenario_context_derivation: dict[str, object],
    observable_behavior_derivation: dict[str, object],
) -> None:
    if "stakeholder_source" in signals:
        findings.append(
            _missing_field_finding(
                field="stakeholder_source",
                patterns=STAKEHOLDER_SOURCE_TERMS,
                text="",
                severity="major" if strict else "minor",
                category="stakeholder",
                basis=BASIS["requirements"],
                finding="要求の利害関係者または出所が見えない。",
                suggested_fix="誰の要求か、誰が使うか、誰が受け入れるか、または出所が不要な理由を明示する。",
            )
        )
        missing.append("stakeholder_source")

    if "quality_constraint" in signals:
        findings.append(
            Finding(
                severity="major" if strict else "minor",
                category="quality",
                basis=BASIS["requirements"] + BASIS["implementation"],
                finding="品質要求らしき記述があるが、測定条件や受入基準が薄い。",
                evidence=signals["quality_constraint"],
                suggested_fix="性能、信頼性、安全性、使いやすさなどを、閾値、測定方法、受入基準、判断主体へ落とす。",
                warning_class="generic caution",
            )
        )
        missing.append("quality_constraint")

    if "priority" in signals:
        findings.append(
            Finding(
                severity="minor",
                category="priority",
                basis=BASIS["requirements"] + BASIS["planning"],
                finding="複数要求らしき入力に優先度または実施順序が見えない。",
                evidence=signals["priority"],
                suggested_fix="必須/任意、先にやる/後でやる、採用/保留などの優先度を分ける。",
            )
        )
        missing.append("priority")

    if "uncertainty_classification" in signals:
        findings.append(
            Finding(
                severity="minor",
                category="unknowns",
                basis=BASIS["requirements"] + BASIS["meaning"],
                finding="不確実な表現があるが、未確定、仮説、判断待ちなどの扱いが分かれていない。",
                evidence=signals["uncertainty_classification"],
                suggested_fix="推測を要求に混ぜず、未確定、仮説、判断待ち、片側観測、時点差のいずれかへ分類する。",
            )
        )
        missing.append("uncertainty_classification")

    if "problem_mechanism_fit" in signals:
        finding = Finding(
            severity="major" if strict else "minor",
            category="solution_fit",
            basis=BASIS["requirements"] + BASIS["meaning"],
            finding="解決策が問題の原因構造または発生機構へどう作用するかが見えない。",
            evidence=signals["problem_mechanism_fit"],
            suggested_fix="観測症状、原因仮説、発生条件、制約、解決策が効く理由、または調査で確かめる項目を分けて明示する。",
            warning_class="generic caution",
            needs_human_decision=True,
        )
        finding.rule_id = "req.solution.problem_mechanism_fit_missing"
        findings.append(finding)
        missing.append("problem_mechanism_fit")

    if "symptom_only_success" in signals:
        finding = Finding(
            severity="major" if strict else "minor",
            category="acceptance",
            basis=BASIS["requirements"] + BASIS["meaning"],
            finding="受入条件が観測症状の消失だけに寄っている。",
            evidence=signals["symptom_only_success"],
            suggested_fix="症状が出ないことだけでなく、原因または制約が解けた証拠、目的達成、異常時挙動、差し戻し条件を足す。",
            warning_class="generic caution",
            needs_human_decision=True,
        )
        finding.rule_id = "req.acceptance.symptom_only_success_criteria"
        findings.append(finding)
        missing.append("symptom_only_success_criteria")

    if "achievement_criteria" in signals:
        finding = Finding(
            severity="major" if strict else "minor",
            category="acceptance",
            basis=BASIS["requirements"],
            finding="要求が何を以て達成されたと言えるかが薄い。",
            evidence=signals["achievement_criteria"],
            suggested_fix="受入基準、合格条件、完了条件、成功状態、または Definition of Done を明示する。",
        )
        finding.rule_id = ACHIEVEMENT_CRITERIA_RULE_ID
        finding.derivation = achievement_criteria_derivation
        findings.append(finding)
        missing.append("achievement_criteria")

    if "verification_method_detail" in signals:
        finding = Finding(
            severity="major" if strict else "minor",
            category="verification",
            basis=BASIS["requirements"],
            finding="検証または確認の方法が具体化されていない。",
            evidence=signals["verification_method_detail"],
            suggested_fix="試験、解析、検査、実演、測定、レビュー、代表 CLI 実行など、どの方法で確かめるかを明示する。",
        )
        finding.rule_id = METHOD_DETAIL_RULE_ID
        finding.derivation = method_detail_derivation
        findings.append(finding)
        missing.append("verification_method_detail")

    if "evidence_artifact" in signals:
        finding = Finding(
            severity="minor",
            category="evidence",
            basis=BASIS["requirements"],
            finding="達成確認に使う証拠成果物が見えない。",
            evidence=signals["evidence_artifact"],
            suggested_fix="コマンド結果、試験結果、ログ、スクリーンショット、出力 JSON、レビュー記録など、残す証拠を明示する。",
        )
        finding.rule_id = EVIDENCE_ARTIFACT_RULE_ID
        finding.derivation = evidence_artifact_derivation
        findings.append(finding)
        missing.append("evidence_artifact")

    if "rejection_condition" in signals:
        finding = Finding(
            severity="minor",
            category="acceptance",
            basis=BASIS["requirements"] + BASIS["planning"],
            finding="不合格、棄却、戻しが必要になる条件が見えない。",
            evidence=signals["rejection_condition"],
            suggested_fix="どの結果なら未達、差し戻し、保留、または rollback とするかを明示する。",
            warning_class="generic caution",
        )
        finding.rule_id = REJECTION_CONDITION_RULE_ID
        finding.derivation = rejection_condition_derivation
        findings.append(finding)
        missing.append("rejection_condition")

    if "scenario_context" in signals:
        finding = Finding(
            severity="minor",
            category="scenario",
            basis=BASIS["requirements"] + BASIS["meaning"],
            finding="利用場面、入力条件、操作文脈が見えない。",
            evidence=signals["scenario_context"],
            suggested_fix="誰が、どの状態で、何を入力または操作し、何が返ればよいかを短いシナリオで明示する。",
        )
        finding.rule_id = SCENARIO_CONTEXT_RULE_ID
        finding.derivation = scenario_context_derivation
        findings.append(finding)
        missing.append("scenario_context")

    if "observable_behavior" in signals:
        finding = Finding(
            severity="major" if strict else "minor",
            category="behavior",
            basis=BASIS["requirements"],
            finding="要求が観測可能な振る舞いへ落ちていない。",
            evidence=signals["observable_behavior"],
            suggested_fix="誰または何が、どの操作や入力に対して、何を返す、保存する、表示する、拒否する、通知するのかを明示する。",
        )
        finding.rule_id = OBSERVABLE_BEHAVIOR_RULE_ID
        finding.derivation = observable_behavior_derivation
        findings.append(finding)
        missing.append("observable_behavior")

    if "precondition_or_trigger" in signals:
        findings.append(
            Finding(
                severity="minor",
                category="scenario",
                basis=BASIS["requirements"] + BASIS["meaning"],
                finding="要求が満たされる前提条件または発火条件が見えない。",
                evidence=signals["precondition_or_trigger"],
                suggested_fix="Given/When、前提状態、入力条件、操作、発火条件、対象データを明示する。",
            )
        )
        missing.append("precondition_or_trigger")

    if "expected_result" in signals:
        findings.append(
            Finding(
                severity="minor",
                category="acceptance",
                basis=BASIS["requirements"],
                finding="操作や入力に対する期待結果が見えない。",
                evidence=signals["expected_result"],
                suggested_fix="期待する出力、表示、状態変化、エラー、拒否、通知、保存結果を明示する。",
            )
        )
        missing.append("expected_result")

    if "interface_contract" in signals:
        findings.append(
            Finding(
                severity="minor",
                category="interface",
                basis=BASIS["requirements"] + BASIS["implementation"],
                finding="入出力または公開面に触れているが、契約の項目が薄い。",
                evidence=signals["interface_contract"],
                suggested_fix="入力項目、出力項目、形式、状態コード、エラー、既定値、例、schema のいずれかを明示する。",
                warning_class="generic caution",
            )
        )
        missing.append("interface_contract")


STAKEHOLDER_SOURCE_TERMS = [
    "stakeholder",
    "user",
    "customer",
    "owner",
    "operator",
    "maintainer",
    "reviewer",
    "requester",
    "利用者",
    "ユーザー",
    "顧客",
    "依頼元",
    "受入者",
    "判断主体",
    "運用者",
    "保守者",
    "読者",
    "作者",
    "誰が",
    "誰のため",
]


def _stakeholder_source_signal(text: str) -> str:
    return _first_match(text, STAKEHOLDER_SOURCE_TERMS)


def _quality_requirement_signal(text: str) -> str:
    terms = [
        "performance",
        "latency",
        "throughput",
        "availability",
        "reliability",
        "maintainability",
        "usability",
        "security",
        "secure",
        "safe",
        "fast",
        "品質",
        "性能",
        "速度",
        "速く",
        "高速",
        "安全",
        "可用",
        "信頼",
        "保守",
        "使いやす",
        "分かりやす",
        "安定",
    ]
    return _first_match(text, terms)


def _has_quality_constraint_evidence(text: str) -> bool:
    if re.search(r"(\d+(\.\d+)?\s*(ms|s|sec|秒|分|件|回|%|kb|mb|gb)|p9[059]|[<>]=?|以内|以上|以下|未満)", text, re.IGNORECASE):
        return True
    return _has_any(
        text,
        [
            "threshold",
            "metric",
            "measure",
            "measurement",
            "acceptance",
            "criteria",
            "benchmark",
            "slo",
            "sla",
            "閾値",
            "指標",
            "測定",
            "計測",
            "受入",
            "受入基準",
            "許容",
            "基準",
            "ベンチ",
        ],
    )


def _has_priority_evidence(text: str) -> bool:
    return _has_any(
        text,
        [
            "priority",
            "must",
            "should",
            "could",
            "p0",
            "p1",
            "p2",
            "critical",
            "optional",
            "優先",
            "必須",
            "任意",
            "重要度",
            "先に",
            "後で",
            "保留",
            "採用",
        ],
    )


def _unclassified_uncertainty_signal(text: str) -> str:
    uncertainty = _first_match(
        text,
        ["たぶん", "おそらく", "かもしれない", "っぽい", "と思う", "maybe", "probably", "likely", "seems"],
    )
    if not uncertainty:
        return ""
    if _has_any(
        text,
        [
            "未確定",
            "未決",
            "仮説",
            "判断待ち",
            "保留",
            "片側観測",
            "時点差",
            "unknown",
            "hypothesis",
            "pending",
            "tbd",
        ],
    ):
        return ""
    return uncertainty


def _problem_mechanism_fit_signal(text: str) -> str:
    if not _problem_or_symptom_signal(text) or not _solution_action_signal(text):
        return ""
    if _problem_mechanism_evidence_signal(text) or _investigation_only_signal(text):
        return ""
    return _problem_or_symptom_signal(text) or _solution_action_signal(text)


def _symptom_only_success_signal(text: str) -> str:
    if not _problem_or_symptom_signal(text):
        return ""
    symptom_success = _symptom_disappearance_success_signal(text)
    if not symptom_success:
        return ""
    if _problem_mechanism_evidence_signal(text) or _side_effect_transfer_evidence_signal(text) or _rejection_condition_signal(text):
        return ""
    return symptom_success


def _problem_or_symptom_signal(text: str) -> str:
    return _first_match(
        text,
        [
            "problem",
            "issue",
            "failure",
            "error",
            "incident",
            "symptom",
            "does not work",
            "broken",
            "slow",
            "blocked",
            "stuck",
            "rejected",
            "warning",
            "問題",
            "課題",
            "症状",
            "障害",
            "不具合",
            "失敗",
            "エラー",
            "警告",
            "止まる",
            "落ちる",
            "切れる",
            "詰まる",
            "遅い",
            "重い",
            "拒否",
            "通らない",
            "できない",
            "うまくいかない",
        ],
    )


def _solution_action_signal(text: str) -> str:
    return _first_match(
        text,
        [
            "solution",
            "fix",
            "workaround",
            "mitigation",
            "対応",
            "解決策",
            "解決案",
            "修正",
            "改善",
            "変更",
            "置換",
            "交換",
            "導入",
            "追加",
            "削除",
            "緩和",
            "回避",
            "抑止",
            "無効化",
            "上げる",
            "下げる",
            "増やす",
            "減らす",
            "伸ばす",
            "短くする",
            "広げる",
            "狭める",
            "止める",
            "消す",
        ],
    )


def _intervention_action_signal(text: str) -> str:
    return _first_match(
        text,
        [
            "bypass",
            "disable",
            "ignore",
            "suppress",
            "mute",
            "increase",
            "decrease",
            "raise",
            "lower",
            "retry",
            "timeout",
            "limit",
            "threshold",
            "quota",
            "capacity",
            "fallback",
            "workaround",
            "無効化",
            "握り潰す",
            "握りつぶす",
            "抑止",
            "抑制",
            "回避",
            "緩和",
            "無視",
            "消す",
            "出さない",
            "上げる",
            "下げる",
            "増やす",
            "減らす",
            "伸ばす",
            "短くする",
            "広げる",
            "狭める",
            "リトライ",
            "タイムアウト",
            "上限",
            "下限",
            "閾値",
            "容量",
            "制限",
            "検証を外す",
            "認可を外す",
        ],
    )


def _problem_mechanism_evidence_signal(text: str) -> str:
    return _first_match(
        text,
        [
            "root cause",
            "cause",
            "mechanism",
            "reproduction",
            "precondition",
            "constraint",
            "rationale",
            "why",
            "because",
            "caused by",
            "原因",
            "根本原因",
            "発生原因",
            "発生機構",
            "機構",
            "仕組み",
            "再現条件",
            "発生条件",
            "前提条件",
            "制約",
            "根拠",
            "理由",
            "なぜ",
            "作用",
            "効く",
            "仮説",
            "切り分け",
            "調査で確かめる",
        ],
    )


def _side_effect_transfer_evidence_signal(text: str) -> str:
    return _first_match(
        text,
        [
            "side effect",
            "impact",
            "risk transfer",
            "tradeoff",
            "downstream",
            "upstream",
            "load",
            "capacity",
            "cost",
            "regression",
            "compatibility",
            "failure mode",
            "副作用",
            "影響",
            "危険移転",
            "負荷移転",
            "リスク移転",
            "トレードオフ",
            "上流",
            "下流",
            "隣接",
            "負荷",
            "容量",
            "定格",
            "費用",
            "責任",
            "故障様式",
            "失敗様式",
            "互換",
            "回帰",
            "波及",
        ],
    )


def _symptom_disappearance_success_signal(text: str) -> str:
    return _first_match(
        text,
        [
            "does not happen",
            "does not fail",
            "does not stop",
            "no error",
            "no warning",
            "not blocked",
            "not rejected",
            "起きない",
            "発生しない",
            "再発しない",
            "失敗しない",
            "エラーが出ない",
            "警告が出ない",
            "止まらない",
            "落ちない",
            "切れない",
            "詰まらない",
            "拒否されない",
            "通る",
            "消える",
            "出ない",
        ],
    )


def _investigation_only_signal(text: str) -> str:
    return _has_any(
        text,
        [
            "調査のみ",
            "原因調査",
            "切り分けのみ",
            "まだ実施しない",
            "解決策を決めない",
            "investigation only",
            "diagnosis only",
            "do not implement",
        ],
    )


def _acceptance_criteria_signal(text: str) -> str:
    terms = [
        "acceptance criteria",
        "success criteria",
        "definition of done",
        "done when",
        "pass if",
        "accepted when",
        "受入基準",
        "合格条件",
        "完了条件",
        "達成条件",
        "成功条件",
        "達成されたと言える",
        "完了とする",
        "合格とする",
        "ことを確認",
        "ことを検証",
    ]
    match = _first_match(text, terms)
    if match:
        return match
    if _has_quality_constraint_evidence(text):
        return _first_match(text, ["threshold", "metric", "受入", "閾値", "指標", "測定", "基準", "p95", "以内", "以下", "以上"])
    return ""


def _verification_method_signal(text: str) -> str:
    return _first_match(
        text,
        [
            "unittest",
            "pytest",
            "npm test",
            "swift test",
            "uv run",
            "benchmark",
            "inspection",
            "review",
            "demonstration",
            "analysis",
            "measurement",
            "schema validation",
            "smoke",
            "e2e",
            "cli",
            "command",
            "試験",
            "テスト",
            "検査",
            "実演",
            "解析",
            "測定",
            "計測",
            "レビュー",
            "ベンチ",
            "代表 CLI",
            "コマンド",
            "スモーク",
        ],
    )


def _evidence_artifact_signal(text: str) -> str:
    return _first_match(
        text,
        [
            "evidence",
            "test result",
            "command output",
            "log",
            "screenshot",
            "report",
            "record",
            "json output",
            "artifact",
            "証拠",
            "証跡",
            "根拠",
            "試験結果",
            "検証結果",
            "コマンド結果",
            "実行結果",
            "ログ",
            "スクリーンショット",
            "出力 JSON",
            "記録",
            "報告",
            "成果物",
        ],
    )


def _rejection_condition_signal(text: str) -> str:
    return _first_match(
        text,
        [
            "fail if",
            "reject",
            "rejection",
            "not accepted",
            "rollback if",
            "error if",
            "不合格",
            "棄却",
            "差し戻し",
            "未達",
            "失敗条件",
            "失敗時",
            "戻す",
            "保留",
            "rollback",
        ],
    )


def _scenario_context_signal(text: str) -> str:
    return _first_match(
        text,
        [
            "scenario",
            "use case",
            "given",
            "when",
            "then",
            "input",
            "output",
            "operation",
            "workflow",
            "context",
            "シナリオ",
            "利用場面",
            "ユースケース",
            "入力",
            "出力",
            "手順",
            "前提条件",
            "場合",
        ],
    )


def _has_verification_or_acceptance_language(text: str) -> bool:
    return _has_any(
        text,
        ["検証", "確認", "試験", "テスト", "受入", "受入基準", "acceptance", "verify", "test", "evidence"],
    )


def _requires_rejection_condition(text: str) -> bool:
    return _has_any(
        text,
        [
            "安全",
            "security",
            "secure",
            "権限",
            "permission",
            "認証",
            "認可",
            "削除",
            "delete",
            "移行",
            "migration",
            "公開",
            "release",
            "運用",
            "operation",
            "永続",
            "保存",
            "支払",
            "payment",
        ],
    )


def _requires_scenario_context(text: str) -> bool:
    return _has_any(
        text,
        [
            "画面",
            "UI",
            "ユーザー",
            "利用者",
            "操作",
            "入力",
            "表示",
            "検索",
            "通知",
            "workflow",
            "screen",
            "user",
            "input",
            "display",
            "search",
            "notification",
        ],
    )


def _observable_behavior_signal(text: str) -> str:
    return _first_match(
        text,
        [
            "return",
            "returns",
            "display",
            "show",
            "save",
            "create",
            "update",
            "delete",
            "reject",
            "allow",
            "deny",
            "notify",
            "record",
            "validate",
            "search",
            "filter",
            "返す",
            "返る",
            "表示",
            "保存",
            "作成",
            "更新",
            "削除",
            "拒否",
            "許可",
            "通知",
            "検索",
            "絞り込",
            "出力",
            "入力",
        ],
    )


def _vague_behavior_signal(text: str) -> str:
    return _first_match(
        text,
        [
            "改善",
            "対応",
            "サポート",
            "整える",
            "最適化",
            "いい感じ",
            "使いやす",
            "分かりやす",
            "強化",
            "improve",
            "support",
            "optimize",
            "enhance",
            "better",
        ],
    )


def _precondition_or_trigger_signal(text: str) -> str:
    return _first_match(
        text,
        [
            "given",
            "when",
            "if",
            "on ",
            "after",
            "before",
            "trigger",
            "precondition",
            "前提",
            "前提条件",
            "場合",
            "とき",
            "時",
            "入力した場合",
            "クリック",
            "操作した場合",
            "起動時",
            "保存時",
            "受信時",
            "発火",
            "条件",
        ],
    )


def _expected_result_signal(text: str) -> str:
    return _first_match(
        text,
        [
            "then",
            "expected",
            "result",
            "output",
            "returns",
            "status",
            "error",
            "state",
            "期待結果",
            "期待状態",
            "返る",
            "返す",
            "表示される",
            "出力される",
            "保存される",
            "更新される",
            "作成される",
            "記録される",
            "残る",
            "拒否される",
            "通知される",
            "エラー",
            "状態",
            "一覧",
        ],
    )


def _interface_surface_signal(text: str) -> str:
    return _first_match(
        text,
        [
            "api",
            "cli",
            "mcp",
            "json",
            "yaml",
            "csv",
            "webhook",
            "http",
            "endpoint",
            "schema",
            "config",
            "env",
            "file format",
            "API",
            "CLI",
            "MCP",
            "JSON",
            "YAML",
            "CSV",
            "Webhook",
            "エンドポイント",
            "スキーマ",
            "構成",
            "設定",
            "環境変数",
            "ファイル形式",
        ],
    )


def _interface_contract_signal(text: str) -> str:
    if not _interface_surface_signal(text):
        return ""
    return _first_match(
        text,
        [
            "schema",
            "field",
            "property",
            "status",
            "status code",
            "error",
            "format",
            "example",
            "default",
            "option",
            "flag",
            "argument",
            "request",
            "response",
            "スキーマ",
            "項目",
            "フィールド",
            "状態コード",
            "エラー",
            "形式",
            "例",
            "既定",
            "オプション",
            "フラグ",
            "引数",
            "リクエスト",
            "レスポンス",
        ],
    )


def _requires_precondition_or_trigger(text: str) -> bool:
    if _has_quality_constraint_evidence(text) and not _has_any(text, ["画面", "UI", "入力", "操作", "API", "CLI", "JSON"]):
        return False
    return _has_any(
        text,
        [
            "画面",
            "UI",
            "ユーザー",
            "利用者",
            "操作",
            "入力",
            "検索",
            "通知",
            "API",
            "CLI",
            "JSON",
            "workflow",
            "screen",
            "user",
            "input",
            "search",
            "notification",
        ],
    )


def _requires_expected_result(text: str) -> bool:
    if _has_quality_constraint_evidence(text) and not _has_any(text, ["画面", "UI", "入力", "操作", "API", "CLI", "JSON"]):
        return False
    return _has_any(
        text,
        [
            "入力",
            "操作",
            "検索",
            "通知",
            "画面",
            "UI",
            "API",
            "CLI",
            "JSON",
            "output",
            "return",
            "screen",
            "input",
            "search",
            "notification",
        ],
    )


def _planning_structure_profile(text: str) -> dict[str, str]:
    return {
        "work_package_decomposition": _work_package_decomposition_signal(text),
        "dependency_sequence": _dependency_sequence_signal(text),
        "estimation_or_resource_basis": _estimation_or_resource_signal(text),
        "risk_response": _risk_response_signal(text),
        "control_baseline": _control_baseline_signal(text),
        "decision_gate": _decision_gate_signal(text),
    }


def _planning_quality_signals(plan: str, combined: str, structure: dict[str, str]) -> dict[str, str]:
    if not plan.strip():
        return {}

    signals: dict[str, str] = {}
    if _has_any(combined, ["妥当", "受入", "受け入れ", "validation", "acceptance"]) and not _has_validation_owner(combined):
        signals["validation_owner"] = ""

    if _requires_work_package_decomposition(plan) and not structure["work_package_decomposition"]:
        signals["work_package_decomposition"] = _work_decomposition_scope_signal(plan)

    if _requires_dependency_sequence(plan) and not structure["dependency_sequence"]:
        signals["dependency_sequence"] = _first_match(plan, ["手順", "段取り", "工程", "step", "作業", "実装", "検証"])

    if _requires_estimation_or_resource_basis(plan) and not structure["estimation_or_resource_basis"]:
        signals["estimation_or_resource_basis"] = _first_match(
            plan,
            ["手順", "工程", "実装", "移行", "公開", "運用", "設定", "複数", "全体"],
        )

    risk_scope = _risk_statement_signal(plan)
    if risk_scope and not structure["risk_response"]:
        signals["risk_response"] = risk_scope

    hazard_transfer = _hazard_transfer_analysis_signal(plan, combined)
    if hazard_transfer:
        signals["hazard_transfer_analysis"] = hazard_transfer

    if _plan_has_multiple_steps(plan) and not _has_progress_control(combined):
        signals["progress_control"] = _first_match(plan, ["手順", "段取り", "工程", "step", "作業", "実装", "検証"])

    if _requires_control_baseline(plan) and not structure["control_baseline"]:
        signals["control_baseline"] = _first_match(plan, ["確認点", "進捗", "工程", "手順", "検証", "証拠"])

    change_scope = _change_control_scope_signal(plan)
    if change_scope and not _has_change_control(combined):
        signals["change_control"] = change_scope

    if _requires_decision_gate(plan) and not structure["decision_gate"]:
        signals["decision_gate"] = _first_match(
            plan,
            ["移行", "公開", "release", "運用", "設定", "権限", "安全", "削除", "本番"],
        )

    minimality_gap = _minimality_justification_gap_signal(plan, combined)
    if minimality_gap:
        signals["minimality_justification"] = minimality_gap

    return signals


def _planning_suppression_traces(plan: str, combined: str) -> list[dict[str, object]]:
    traces: list[dict[str, object]] = []
    if _change_control_scope_signal(plan) and _has_change_control(combined):
        traces.append(
            _suppression_trace(
                phase="audit_plan",
                rule_id="plan.control.change_control_missing",
                emission_status="satisfied",
                reason="explicit_change_control_boundary_satisfies_rule",
                evidence=_first_match(combined, CHANGE_CONTROL_TERMS),
                source="planning_structure.change_control",
            )
        )
    return traces


def _minimality_justification_gap_signal(plan: str, combined: str) -> str:
    expansion = _first_match(plan, MINIMALITY_EXPANSION_TERMS)
    if not expansion:
        return ""
    if _has_any(expansion, MINIMALITY_JUSTIFICATION_TERMS):
        return ""
    if _has_any(expansion, MINIMALITY_SAFETY_EXEMPTION_TERMS):
        return ""
    return expansion


def _add_planning_quality_findings(
    signals: dict[str, str],
    findings: list[Finding],
    missing: list[str],
    strict: bool,
) -> None:
    if "validation_owner" in signals:
        findings.append(
            _missing_field_finding(
                field="validation_owner",
                patterns=VALIDATION_OWNER_TERMS,
                text="",
                severity="major" if strict else "minor",
                category="validation",
                basis=BASIS["planning"] + BASIS["requirements"],
                finding="妥当性確認または受入判断の主体が見えない。",
                suggested_fix="誰が、何を見て、受け入れまたは修正要求を判断するか明示する。",
                needs_human_decision=True,
            )
        )
        missing.append("validation_owner")

    if "work_package_decomposition" in signals:
        findings.append(
            Finding(
                severity="minor",
                category="planning",
                basis=BASIS["planning"],
                finding="成果物や作業が、管理可能な作業パッケージへ分解されていない。",
                evidence=signals["work_package_decomposition"],
                suggested_fix="WBS、成果物分解、ファイル別/機能別/担当別の作業パッケージを明示する。",
                warning_class="generic caution",
            )
        )
        missing.append("work_package_decomposition")

    if "dependency_sequence" in signals:
        findings.append(
            Finding(
                severity="minor",
                category="schedule",
                basis=BASIS["planning"],
                finding="複数作業の先行関係、依存順序、並行可否が見えない。",
                evidence=signals["dependency_sequence"],
                suggested_fix="先に終える作業、後続作業、並行できる作業、ブロッカーを明示する。",
                warning_class="generic caution",
            )
        )
        missing.append("dependency_sequence")

    if "estimation_or_resource_basis" in signals:
        findings.append(
            Finding(
                severity="minor",
                category="resource",
                basis=BASIS["planning"],
                finding="作業量、所要時間、担当、資源、容量の前提が見えない。",
                evidence=signals["estimation_or_resource_basis"],
                suggested_fix="工数、所要時間、担当、追加依存なし、容量制約、または見積不要な理由を明示する。",
                warning_class="generic caution",
            )
        )
        missing.append("estimation_or_resource_basis")

    if "risk_response" in signals:
        findings.append(
            Finding(
                severity="major" if strict else "minor",
                category="risk",
                basis=BASIS["planning"],
                finding="リスクは挙がっているが、対応方針が見えない。",
                evidence=signals["risk_response"],
                suggested_fix="リスク事象ごとに、回避、低減、検知、代替、退避、再試行、保留、責任者のいずれかを明示する。",
                warning_class="generic caution",
            )
        )
        missing.append("risk_response")

    if "hazard_transfer_analysis" in signals:
        finding = Finding(
            severity="major" if strict else "minor",
            category="risk",
            basis=BASIS["planning"] + BASIS["meaning"],
            finding="解決策が危険、負荷、費用、責任、故障様式をどこへ移すかが見えない。",
            evidence=signals["hazard_transfer_analysis"],
            suggested_fix="副作用、危険移転、負荷移転、上流下流影響、制約確認、または対象外理由を計画へ足す。",
            warning_class="generic caution",
            needs_human_decision=True,
        )
        finding.rule_id = "plan.risk.hazard_transfer_analysis_missing"
        findings.append(finding)
        missing.append("hazard_transfer_analysis")

    if "progress_control" in signals:
        findings.append(
            Finding(
                severity="minor",
                category="control",
                basis=BASIS["planning"],
                finding="複数段階の計画だが、進捗確認点または状態報告の方法が見えない。",
                evidence=signals["progress_control"],
                suggested_fix="中間確認、進捗報告、状態更新、停止条件、または不要理由を足す。",
            )
        )
        missing.append("progress_control")

    if "control_baseline" in signals:
        findings.append(
            Finding(
                severity="minor",
                category="control",
                basis=BASIS["planning"],
                finding="進捗や完了を測る基準線、指標、節目条件が見えない。",
                evidence=signals["control_baseline"],
                suggested_fix="scope/schedule baseline、節目、完了基準、測定指標、判定基準、または不要理由を足す。",
                warning_class="generic caution",
            )
        )
        missing.append("control_baseline")

    if "change_control" in signals:
        findings.append(
            Finding(
                severity="minor",
                category="control",
                basis=BASIS["planning"] + BASIS["requirements"],
                finding="範囲変更や追加要求が起きやすい計画だが、変更統制が見えない。",
                evidence=signals["change_control"],
                suggested_fix="追加要求、範囲変更、逸脱、後続化、判断待ちの扱いを決める。",
                warning_class="generic caution",
            )
        )
        missing.append("change_control")

    if "decision_gate" in signals:
        findings.append(
            Finding(
                severity="minor",
                category="governance",
                basis=BASIS["planning"],
                finding="移行、公開、運用、設定変更などの高影響作業に対する判断ゲートが見えない。",
                evidence=signals["decision_gate"],
                suggested_fix="go/no-go、承認、停止条件、保留条件、または人間判断へ回す条件を明示する。",
                warning_class="generic caution",
                needs_human_decision=True,
            )
        )
        missing.append("decision_gate")

    if "minimality_justification" in signals:
        finding = Finding(
            severity="minor",
            category="minimality",
            basis=BASIS["planning"] + BASIS["implementation"] + BASIS["minimality"],
            finding="新規依存、抽象、層、wrapper、schema などを足す計画だが、既存機能や最小案で足りない理由が見えない。",
            evidence=signals["minimality_justification"],
            suggested_fix="既存機能、標準機能、平台機能、既存依存で足りるかを確認し、新規要素が必要な根拠、後続化できる範囲、削減してはいけない安全・証跡境界を明示する。",
            warning_class="generic caution",
        )
        finding.rule_id = "plan.minimality.justification_missing"
        findings.append(finding)
        missing.append("minimality_justification")


def _work_package_decomposition_signal(text: str) -> str:
    return _first_match(
        text,
        [
            "WBS",
            "PBS",
            "work breakdown",
            "work package",
            "product breakdown",
            "作業分解構成",
            "作業分解",
            "作業パッケージ",
            "成果物分解",
            "機能別",
            "ファイル別",
            "モジュール別",
            "担当別",
            "component",
        ],
    )


def _dependency_sequence_signal(text: str) -> str:
    return _first_match(
        text,
        [
            "dependency sequence",
            "predecessor",
            "successor",
            "critical path",
            "after",
            "before",
            "parallel",
            "blocked by",
            "順序",
            "先行",
            "後続",
            "前後関係",
            "依存関係",
            "並行",
            "直列",
            "ブロッカー",
        ],
    )


def _estimation_or_resource_signal(text: str) -> str:
    return _first_match(
        text,
        [
            "estimate",
            "duration",
            "effort",
            "cost",
            "budget",
            "resource",
            "capacity",
            "owner",
            "assignee",
            "見積",
            "工数",
            "所要時間",
            "期間",
            "期限",
            "予算",
            "費用",
            "資源",
            "容量",
            "担当",
            "担当者",
            "追加依存なし",
            "一作業単位",
        ],
    )


def _risk_response_signal(text: str) -> str:
    return _first_match(
        text,
        [
            "mitigation",
            "contingency",
            "fallback",
            "workaround",
            "response",
            "risk owner",
            "probability",
            "impact",
            "対策",
            "対応",
            "緩和",
            "低減",
            "回避",
            "代替",
            "退避",
            "再検証",
            "再試行",
            "検知",
            "保留",
            "影響度",
            "発生確率",
            "責任者",
            "抑える",
        ],
    )


def _control_baseline_signal(text: str) -> str:
    return _first_match(
        text,
        [
            "baseline",
            "scope baseline",
            "schedule baseline",
            "cost baseline",
            "earned value",
            "EVM",
            "metric",
            "measure",
            "milestone",
            "基準線",
            "scope 基準",
            "schedule 基準",
            "測定",
            "計測",
            "指標",
            "閾値",
            "判定基準",
            "完了基準",
            "進捗基準",
            "節目条件",
        ],
    )


def _decision_gate_signal(text: str) -> str:
    return _first_match(
        text,
        [
            "go/no-go",
            "gate",
            "approval",
            "hold point",
            "stop condition",
            "release gate",
            "決定点",
            "判断点",
            "判断ゲート",
            "承認",
            "停止条件",
            "中止条件",
            "保留条件",
            "継続判断",
            "公開判定",
            "移行判定",
        ],
    )


def _requires_work_package_decomposition(plan: str) -> bool:
    return _has_any(plan, ["複数", "全体", "全面", "移行", "公開", "運用", "設定", "API", "MCP", "CLI"]) or (
        _has_any(plan, ["実装", "文書", "検証"]) and _deliverable_item_count(plan) >= 3
    )


def _requires_dependency_sequence(plan: str) -> bool:
    return _plan_has_multiple_steps(plan) and (
        _deliverable_item_count(plan) >= 2 or _has_any(plan, ["実装", "移行", "公開", "設定", "運用", "複数"])
    )


def _requires_estimation_or_resource_basis(plan: str) -> bool:
    return _plan_has_multiple_steps(plan) and _has_any(
        plan,
        ["実装", "移行", "公開", "運用", "設定", "検証", "文書", "複数", "全体", "API", "CLI", "MCP"],
    )


def _risk_statement_signal(plan: str) -> str:
    return _first_match(plan, ["リスク", "危険", "懸念", "失敗条件", "risk", "failure", "hazard"])


def _hazard_transfer_analysis_signal(plan: str, combined: str) -> str:
    if _investigation_only_signal(combined):
        return ""
    if not (_problem_or_symptom_signal(plan) and _intervention_action_signal(plan)):
        return ""
    if _side_effect_transfer_evidence_signal(combined):
        return ""
    if _has_any(
        combined,
        [
            "副作用なし",
            "影響なし",
            "危険移転なし",
            "負荷移転なし",
            "対象外理由",
            "不要理由",
            "no side effect",
            "no impact",
            "not applicable",
        ],
    ):
        return ""
    return _intervention_action_signal(plan) or _problem_or_symptom_signal(plan)


def _requires_control_baseline(plan: str) -> bool:
    return _plan_has_multiple_steps(plan) and _has_any(plan, ["確認点", "進捗", "状態", "報告", "検証", "証拠", "工程"])


def _requires_decision_gate(plan: str) -> bool:
    return _has_any(
        plan,
        [
            "移行",
            "migration",
            "公開",
            "release",
            "本番",
            "production",
            "運用",
            "設定",
            "権限",
            "安全",
            "削除",
            "認証",
            "認可",
        ],
    )


def _work_decomposition_scope_signal(plan: str) -> str:
    return _first_match(plan, ["成果物", "納品物", "出力", "変更物", "実装", "文書", "検証", "複数", "全体"])


def _deliverable_item_count(plan: str) -> int:
    deliverable_line = _first_match(plan, ["成果物", "納品物", "出力", "変更物", "deliverable", "artifact"])
    if not deliverable_line:
        return 0
    return len([part for part in re.split(r"[、,，/／]+|\s+and\s+|\s+と\s+", deliverable_line) if part.strip()])


VALIDATION_OWNER_TERMS = [
    "validation owner",
    "acceptance owner",
    "reviewer",
    "approver",
    "stakeholder",
    "user",
    "owner",
    "判断主体",
    "受入者",
    "承認者",
    "査読者",
    "利用者",
    "ユーザー",
    "人間",
    "誰が",
]


def _has_validation_owner(text: str) -> bool:
    return _has_any(text, VALIDATION_OWNER_TERMS)


def _plan_has_multiple_steps(plan: str) -> bool:
    lowered = plan.lower()
    if any(term in lowered for term in ["手順", "段取り", "工程", "step", "phase", "作業分解"]):
        return True
    return len(re.findall(r"(?m)^\s*(?:[-*]|\d+[.)])\s+\S+", plan)) >= 3


def _has_progress_control(text: str) -> bool:
    return _has_any(
        text,
        [
            "checkpoint",
            "milestone",
            "status",
            "progress",
            "monitor",
            "report",
            "review",
            "確認点",
            "節目",
            "中間",
            "進捗",
            "状態",
            "報告",
            "レビュー",
            "監視",
            "停止条件",
        ],
    )


def _change_control_scope_signal(plan: str) -> str:
    return _first_match(
        plan,
        [
            "移行",
            "migration",
            "公開",
            "release",
            "運用",
            "設定",
            "複数",
            "全体",
            "全面",
            "rewrite all",
            "refactor all",
        ],
    )


def _has_change_control(text: str) -> bool:
    return _has_any(text, CHANGE_CONTROL_TERMS)


def _implementation_change_signals(diff: str, changed_files: list[str]) -> dict[str, str]:
    change_text = _change_text(diff)
    source_changed = any(_is_source_file(path) for path in changed_files)
    signals: dict[str, str] = {}

    public_contract = _public_contract_signal(change_text, changed_files)
    if public_contract:
        signals["public_contract"] = public_contract

    failure_prone = _failure_prone_operation_signal(change_text)
    if source_changed and failure_prone and not _has_failure_handling_evidence(change_text):
        signals["failure_prone_operation"] = failure_prone

    operational = _operational_change_signal(change_text)
    if source_changed and operational and not _has_observability_evidence(change_text):
        signals["operational_observability"] = operational

    dependency = _dependency_runtime_signal(change_text, changed_files)
    if dependency:
        signals["dependency_runtime"] = dependency

    return signals


def _add_implementation_findings(
    signals: dict[str, str],
    findings: list[Finding],
    missing: list[str],
    strict: bool,
) -> None:
    if "public_contract" in signals:
        findings.append(
            Finding(
                severity="minor",
                category="compatibility",
                basis=BASIS["implementation"],
                finding="CLI/API/MCP/出力契約など公開面の変更の可能性がある。",
                evidence=signals["public_contract"],
                suggested_fix="互換性、既定値、移行要否、文書、代表実行、出力契約確認を finish_check に残す。",
                warning_class="generic caution",
            )
        )
        missing.append("public_contract_evidence")

    if "failure_prone_operation" in signals:
        findings.append(
            Finding(
                severity="major" if strict else "minor",
                category="reliability",
                basis=BASIS["implementation"],
                finding="失敗しやすい実行・入出力・解析処理に対する失敗処理の証拠が薄い。",
                evidence=signals["failure_prone_operation"],
                suggested_fix="timeout、例外処理、戻り値確認、入力不正時の扱い、fallback、または意図的に不要な理由を明示する。",
                warning_class="generic caution",
            )
        )
        missing.append("failure_handling")

    if "operational_observability" in signals:
        findings.append(
            Finding(
                severity="minor",
                category="operations",
                basis=BASIS["implementation"],
                finding="運用中に失敗し得る処理に対する状態報告や観測性の証拠が薄い。",
                evidence=signals["operational_observability"],
                suggested_fix="log、status、returncode、通知、監視、retry 記録、または不要理由を残す。",
                warning_class="generic caution",
            )
        )
        missing.append("observability_evidence")

    if "dependency_runtime" in signals:
        findings.append(
            Finding(
                severity="minor",
                category="dependency",
                basis=BASIS["implementation"] + BASIS["security"],
                finding="依存、実行環境、構成、CI に関わる変更の可能性がある。",
                evidence=signals["dependency_runtime"],
                suggested_fix="依存更新、実行環境、互換性、安全性、lockfile、CI 影響の確認結果を残す。",
                warning_class="generic caution",
            )
        )
        missing.append("dependency_runtime_evidence")


PUBLIC_CONTRACT_FILES = (
    "cli.py",
    "mcp_server.py",
    "__init__.py",
    ".schema.json",
    "openapi",
    "api/",
    "schemas/",
)

DEPENDENCY_RUNTIME_FILES = (
    "pyproject.toml",
    "uv.lock",
    "requirements.txt",
    "requirements-dev.txt",
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "Dockerfile",
    "docker-compose",
    ".github/workflows/",
)


def _change_text(diff: str) -> str:
    added = [line[1:] for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++")]
    return "\n".join(added) if added else diff


def _public_contract_signal(text: str, changed_files: list[str]) -> str:
    public_file = next((path for path in changed_files if _matches_suffix_or_part(path, PUBLIC_CONTRACT_FILES)), "")
    public_terms = [
        "--",
        "command",
        "option",
        "flag",
        "argument",
        "api",
        "mcp",
        "tool",
        "schema",
        "json",
        "output",
        "contract",
        "default",
        "互換",
        "移行",
        "出力",
        "契約",
        "既定",
    ]
    if public_file and _has_any(text, public_terms):
        return public_file
    if _has_any(text, ["breaking", "public api", "output schema", "出力契約", "公開 API", "公開面"]):
        return _first_match(text, public_terms)
    return ""


def _failure_prone_operation_signal(text: str) -> str:
    patterns = [
        r"\bsubprocess\.",
        r"\bshell=True\b",
        r"\bjson\.loads\b",
        r"\bjson\.load\b",
        r"\bopen\(",
        r"\bread_text\(",
        r"\bwrite_text\(",
        r"\brequests\.",
        r"\bhttpx\.",
        r"\burllib\.",
        r"\bsocket\.",
        r"\bexec\(",
        r"\beval\(",
        r"\bPath\(",
        r"\bos\.environ\b",
        r"\bdatabase\b",
        r"(?:database|data|schema)[_\s]+migration\b",
        r"\bmigration[_\s]+(?:script|command|runner|job|step|tool|operation)\b",
        r"\bmigrate[_\s]+(?:database|data|schema)\b",
        r"外部実行",
        r"入出力",
        r"ファイル",
        r"(?:DB|データ|スキーマ)移行",
        r"移行(?:処理|スクリプト|ジョブ|実行)",
        r"解析",
    ]
    return _first_regex_match(text, patterns)


def _has_failure_handling_evidence(text: str) -> bool:
    return _has_any(
        text,
        [
            "timeout",
            "try",
            "except",
            "catch",
            "fallback",
            "returncode",
            "check=True",
            "raise_for_status",
            "validate",
            "validation",
            "schema",
            "FileNotFoundError",
            "JSONDecodeError",
            "失敗",
            "例外",
            "タイムアウト",
            "検証",
            "戻り値",
            "異常",
        ],
    )


def _operational_change_signal(text: str) -> str:
    terms = [
        "daemon",
        "scheduler",
        "cron",
        "launchd",
        "background",
        "webhook",
        "notification",
        "discord",
        "monitor",
        "watchdog",
        "retry",
        "codex exec",
        "subprocess",
        "常駐",
        "定期実行",
        "通知",
        "監視",
        "再試行",
        "外部実行",
    ]
    return _first_match(text, terms)


def _has_observability_evidence(text: str) -> bool:
    return _has_any(
        text,
        [
            "log",
            "logger",
            "logging",
            "status",
            "returncode",
            "stderr",
            "stdout",
            "metric",
            "monitor",
            "alert",
            "report",
            "record",
            "ログ",
            "状態",
            "通知",
            "記録",
            "報告",
            "監視",
        ],
    )


def _dependency_runtime_signal(text: str, changed_files: list[str]) -> str:
    file_match = next((path for path in changed_files if _matches_suffix_or_part(path, DEPENDENCY_RUNTIME_FILES)), "")
    if file_match:
        return file_match
    return _first_word_or_phrase_match(
        text,
        ["dependency", "dependencies", "runtime", "lockfile", "container", "ci"],
        ["依存", "実行環境", "構成"],
    )


def _matches_suffix_or_part(path: str, needles: tuple[str, ...]) -> bool:
    lowered = path.lower()
    return any(lowered.endswith(needle.lower()) or needle.lower() in lowered for needle in needles)


def _first_regex_match(text: str, patterns: list[str]) -> str:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            start, end = match.span()
            return text[max(0, start - 45): min(len(text), end + 45)].strip()
    return ""


def _first_word_or_phrase_match(text: str, english_terms: list[str], other_terms: list[str]) -> str:
    for term in english_terms:
        escaped = re.escape(term)
        pattern = rf"(?<![A-Za-z0-9_]){escaped}(?![A-Za-z0-9_])"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            start, end = match.span()
            return text[max(0, start - 45): min(len(text), end + 45)].strip()
    return _first_match(text, other_terms)


def _implemented_public_behavior(text: str) -> bool:
    implementation_terms = ["実装", "implemented", "added", "changed", "更新", "追加"]
    public_terms = ["cli", "api", "mcp", "command", "tool", "schema", "json", "出力", "コマンド", "公開"]
    return _has_any(text, implementation_terms) and _has_any(text, public_terms)


def _has_behavior_evidence(text: str) -> bool:
    if _has_any(
        text,
        [
            "smoke",
            "manual",
            "representative",
            "end-to-end",
            "e2e",
            "stdout",
            "returncode",
            "screenshot",
            "実地",
            "手動",
            "代表",
            "出力確認",
            "実行例",
            "挙動確認",
        ],
    ):
        return True
    return bool(re.search(r"\bsemantic-guard\s+(audit|review|finish|understand|llm|acceptance|validate)", text))


SEMANTIC_BOUNDARY_TERMS: dict[str, list[str]] = {
    "identity": ["identity", "identifier", "uuid", "primary key", "識別子", "同一性", "実体", "ID"],
    "display_identifier": ["display", "label", "title", "rename", "表示名", "表示", "ラベル", "名称", "名前"],
    "persistence": ["file path", "storage path", "save path", "directory", "folder", "永続化", "保存先", "保管", "格納", "配置"],
    "membership": ["membership", "belongs", "collection", "group", "所属", "分類", "包含", "メンバー"],
    "source_of_truth": ["source of truth", "canonical", "canon", "正本", "正典", "唯一の正", "参照元"],
    "permission": ["permission", "authorization", "authz", "role", "権限", "認可", "ロール"],
    "evidence": ["evidence", "proof", "acceptance", "verification", "証拠", "証跡", "根拠", "受入", "検証"],
}


def _semantic_boundaries(diff: str) -> list[dict[str, str]]:
    boundaries: list[dict[str, str]] = []
    for boundary, terms in SEMANTIC_BOUNDARY_TERMS.items():
        evidence = _semantic_boundary_evidence(diff, terms)
        if evidence:
            boundaries.append({"boundary": boundary, "evidence": evidence})
    return boundaries


def _semantic_boundary_evidence(text: str, terms: list[str]) -> str:
    lowered = text.lower()
    ignored_phrases = ["audit path", "document audit path", "code path", "path through"]
    for term in terms:
        term_lower = term.lower()
        if term_lower == "id":
            pattern = r"\b(id|ids)\b"
            match = re.search(pattern, text, re.IGNORECASE)
            if not match:
                continue
            start, end = match.span()
        else:
            index = lowered.find(term_lower)
            if index < 0:
                continue
            start, end = index, index + len(term)
        excerpt = _excerpt_around(text, start, end)
        if any(ignored in excerpt.lower() for ignored in ignored_phrases):
            continue
        return excerpt
    return ""


def _semantic_boundary_fix(boundaries: list[str]) -> str:
    guidance = {
        "identity": "名前変更と実体識別子変更を分け、移行や参照解決の証拠を残す。",
        "display_identifier": "表示名、ラベル、識別子のどれを変えたのか明示する。",
        "persistence": "物理保存先、永続化形式、意味上の所属を混同していないか確認する。",
        "membership": "所属、分類、包含関係が変わるなら影響する参照と移行を確認する。",
        "source_of_truth": "正本、正典、参照元が変わるなら旧正本との関係を明示する。",
        "permission": "権限、認可、役割への影響と確認証拠を残す。",
        "evidence": "証拠、受入、検証の主張が成果物と対応しているか確認する。",
    }
    return " ".join(guidance.get(boundary, "") for boundary in boundaries).strip()


def _document_validity_checks(text: str, findings: list[Finding], missing: list[str]) -> dict[str, object]:
    checks = {
        "has_headings": bool(re.search(r"(?m)^\s*#{1,3}\s+\S+", text)),
        "has_code_examples": "```" in text,
        "has_output_contract_terms": _has_any(text, ["status", "score", "findings", "missing", "next_actions", "details"]),
        "has_limitations": _has_any(text, ["limitations", "制限", "does not", "do not", "not ", "対象外", "しない"]),
        "has_implementation_evidence": _has_implementation_evidence(text),
        "no_implementation_evidence_available": False,
        "overclaim_count": 0,
    }
    checks["no_implementation_evidence_available"] = not checks["has_implementation_evidence"]

    if not checks["has_headings"]:
        findings.append(
            Finding(
                severity="minor",
                category="documentation",
                basis=BASIS["requirements"] + BASIS["meaning"],
                finding="文書に見出し構造が見えない。",
                suggested_fix="読み手が走査できるように、目的、使い方、制限などを見出しで分ける。",
            )
        )

    if _has_any(text, ["cli", "mcp", "command", "run", "usage", "使い方"]) and not checks["has_code_examples"]:
        findings.append(
            Finding(
                severity="minor",
                category="documentation",
                basis=BASIS["requirements"],
                finding="使い方を述べているが、実行例やコードブロックが見えない。",
                suggested_fix="少なくとも一つ、再現可能なコマンド例または設定例を追加する。",
            )
        )
        missing.append("executable_example")

    if _has_any(text, ["json", "output", "schema", "contract", "出力", "契約"]) and not checks["has_output_contract_terms"]:
        findings.append(
            Finding(
                severity="minor",
                category="documentation",
                basis=BASIS["requirements"],
                finding="出力契約に触れているが、返却項目の説明が薄い。",
                suggested_fix="`status`, `score`, `findings`, `missing`, `next_actions`, `details` などの主要項目を明示する。",
            )
        )
        missing.append("output_contract_terms")

    overclaims = _document_overclaim_sentences(text)
    checks["overclaim_count"] = len(overclaims)
    for sentence in overclaims[:3]:
        document_only = not checks["has_implementation_evidence"]
        findings.append(
            Finding(
                severity="major",
                category="evidence",
                basis=BASIS["requirements"] + BASIS["meaning"],
                finding=(
                    "文書が強い完成度・安全性・正確性を主張しているが、文書内の実装証拠では支えられていない可能性がある。"
                    if document_only
                    else "文書が強い完成度・安全性・正確性を主張しているが、制限や証拠で支えられていない可能性がある。"
                ),
                evidence=sentence,
                suggested_fix=(
                    "文書だけでは実行時正しさを証明できないため、検証範囲、未証明範囲、または実装証拠が無い状態を明示する。"
                    if document_only
                    else "試作、制限、検証範囲、残リスク、根拠を明示するか、主張を弱める。"
                ),
                warning_class="generic caution" if document_only else "actionable",
            )
        )

    return checks


def _document_claim_triples(text: str, findings: list[Finding]) -> list[dict[str, object]]:
    blocks = _document_blocks(text)
    triples: list[dict[str, object]] = []
    for heading, block_text in blocks:
        evidence = _evidence_snippets(block_text)
        limitations = _limitation_snippets(block_text)
        for claim in _claim_sentences(block_text):
            strong = _is_strong_claim(claim)
            triple = {
                "section": heading,
                "claim": claim,
                "evidence": evidence[:2],
                "limitations": limitations[:2],
                "support": "supported" if evidence else "limited" if limitations else "unsupported",
                "strong": strong,
            }
            triples.append(triple)
            if strong and not evidence and not limitations and not _is_negated_or_scoped_claim(claim):
                findings.append(
                    Finding(
                        severity="major",
                        category="evidence",
                        basis=BASIS["requirements"] + BASIS["meaning"],
                        finding="文書内の強い主張に対応する証拠または制限が見えない。文書だけでは実行時正しさまでは証明できない。",
                        evidence=claim,
                        suggested_fix="同じ節に、実行例、検証結果、制限、未証明範囲、または主張を弱める説明を足す。",
                        warning_class="generic caution",
                    )
                )
    return triples[:20]


def _document_claim_summary(claim_triples: list[dict[str, object]]) -> dict[str, object]:
    support_counts = {"supported": 0, "limited": 0, "unsupported": 0}
    strong_counts = {"supported": 0, "limited": 0, "unsupported": 0}
    for triple in claim_triples:
        support = str(triple.get("support", "unsupported"))
        if support not in support_counts:
            support = "unsupported"
        support_counts[support] += 1
        if triple.get("strong"):
            strong_counts[support] += 1
    return {
        "claim_count": len(claim_triples),
        "support_counts": support_counts,
        "strong_support_counts": strong_counts,
        "unsupported_count": support_counts["unsupported"],
        "strong_unsupported_count": strong_counts["unsupported"],
    }


def _document_blocks(text: str) -> list[tuple[str, str]]:
    blocks: list[tuple[str, list[str]]] = [("preamble", [])]
    for line in text.splitlines():
        heading = re.match(r"^\s*#{1,3}\s+(.+?)\s*$", line)
        if heading:
            blocks.append((heading.group(1), []))
        else:
            blocks[-1][1].append(line)
    return [(heading, "\n".join(lines).strip()) for heading, lines in blocks if "\n".join(lines).strip()]


def _claim_sentences(text: str) -> list[str]:
    stripped = _strip_code_blocks(text)
    sentences = [sentence.strip(" -\t") for sentence in re.split(r"(?<=[.!?。])\s+|\n+", stripped)]
    claims: list[str] = []
    for sentence in sentences:
        if len(sentence) < 24 or sentence.startswith("|"):
            continue
        if sentence.lower().startswith(("whether ", "does ", "is there ", "what ", "when ", "where ", "how ")):
            continue
        if _has_any(sentence, [" is ", " are ", " can ", " will ", " should ", " provides ", " exposes ", " returns ", " checks ", " detects ", "useful", "helps", "は", "できる", "する", "返す"]):
            claims.append(sentence[:260])
    return claims[:6]


def _evidence_snippets(text: str) -> list[str]:
    snippets: list[str] = []
    for block in re.findall(r"```.*?```", text, re.DOTALL):
        snippets.append(_compact_code_snippet(block))
    for sentence in re.split(r"(?<=[.!?。])\s+|\n+", _strip_code_blocks(text)):
        cleaned = sentence.strip(" -\t")
        if _has_any(cleaned, ["verified", "tested", "passed", "ok", "example", "run ", "command", "evidence", "result", "検証", "確認", "実行", "結果", "証拠", "例"]):
            snippets.append(_compact_snippet(cleaned))
    return _unique_nonempty(snippets)


def _limitation_snippets(text: str) -> list[str]:
    snippets: list[str] = []
    for sentence in re.split(r"(?<=[.!?。])\s+|\n+", _strip_code_blocks(text)):
        cleaned = sentence.strip(" -\t")
        if _is_negated_or_scoped_claim(cleaned) or _has_any(cleaned, ["limitation", "heuristic", "rough", "residual risk", "prototype", "制限", "試作", "残リスク"]):
            snippets.append(_compact_snippet(cleaned))
    return _unique_nonempty(snippets)


def _strip_code_blocks(text: str) -> str:
    return re.sub(r"```.*?```", " ", text, flags=re.DOTALL)


def _unique_nonempty(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        cleaned = item.strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            result.append(cleaned)
    return result


def _is_strong_claim(sentence: str) -> bool:
    return bool(
        re.search(
            r"\b(production[- ]ready|authoritative|guarantee(?:d|s)?|complete|fully|always|never fails?|correct|safe|secure)\b|完成品|完全|保証|安全|正確",
            sentence,
            re.IGNORECASE,
        )
    )


def _document_overclaim_sentences(text: str) -> list[str]:
    terms = [
        r"\bproduction[- ]ready\b",
        r"\bauthoritative\b",
        r"\bguarantee(?:d|s)?\b",
        r"\bcomplete\b",
        r"\bfully\b",
        r"\balways\b",
        r"\bnever fails?\b",
        r"\bcorrect\b",
        r"\bsafe\b",
        r"\bsecure\b",
        r"完成品",
        r"完全",
        r"保証",
        r"安全",
        r"正確",
    ]
    sentences = re.split(r"(?<=[.!?。])\s+|\n+", text)
    flagged: list[str] = []
    for sentence in sentences:
        cleaned = sentence.strip()
        if not cleaned or _is_negated_or_scoped_claim(cleaned):
            continue
        for term in terms:
            if re.search(term, cleaned, re.IGNORECASE):
                flagged.append(cleaned[:240])
                break
    return flagged


def _is_negated_or_scoped_claim(sentence: str) -> bool:
    lowered = sentence.lower()
    scoped_phrases = [
        "not ",
        "does not",
        "do not",
        "should not",
        "cannot",
        "can't",
        "prototype",
        "research",
        "limitation",
        "limited",
        "over-warn",
        "under-warn",
        "influenced by",
        "guidance",
        "review",
        "試作",
        "制限",
        "対象外",
        "ではない",
        "しない",
    ]
    return any(phrase in lowered for phrase in scoped_phrases)


def _score_field(text: str, patterns: list[str]) -> int:
    if not text.strip():
        return 0
    hits = sum(1 for pattern in patterns if pattern.lower() in text.lower())
    if hits == 0:
        return 0
    if _has_heading_hit(text, patterns):
        return 4
    if hits == 1:
        return 2
    if re.search(r"(/Users/|[\w.-]+:\d+|`[^`]+`|https?://|実行|確認済み|verified)", text, re.I):
        return 4
    return 3


def _has_heading_hit(text: str, patterns: list[str]) -> bool:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        heading_like = bool(re.match(r"^(#{1,4}\s+|[-*]\s+|\d+[.)]\s+)?[^:：]{1,32}[:：]", stripped))
        markdown_heading = stripped.startswith("#")
        if not (heading_like or markdown_heading):
            continue
        prefix = stripped.split(":", 1)[0].split("：", 1)[0]
        if any(pattern.lower() in prefix.lower() for pattern in patterns):
            return True
    return False


def _excerpt_for_field(text: str, patterns: list[str]) -> str:
    return _first_match(text, patterns)


def _add_ambiguity_findings(text: str, findings: list[Finding]) -> None:
    matches = sorted({term for term in AMBIGUOUS_TERMS if term.lower() in text.lower()})
    for term in matches[:5]:
        findings.append(
            Finding(
                severity="minor",
                category="clarity",
                basis=BASIS["requirements"],
                finding=f"曖昧語 `{term}` が含まれている。",
                evidence=_first_match(text, [term]),
                suggested_fix="測定可能な条件、閾値、受入基準、または判断主体を足す。",
            )
        )


def _looks_multi_requirement(text: str) -> bool:
    separators = [" and ", " or ", "かつ", "または", "及び", "および"]
    return sum(text.lower().count(separator) for separator in separators) > 0 or text.count("、") >= 2


def _is_bounded_work_package_request(text: str, combined: str) -> bool:
    if not _looks_multi_requirement(text):
        return False
    has_package_language = _has_any(
        combined,
        [
            "作業パッケージ",
            "work package",
            "段階",
            "stage",
            "修正計画",
            "実装計画",
            "順位",
            "優先",
            "依存",
            "順序",
        ],
    )
    has_scope_control = _has_any(combined, SCOPE_BOUNDARY_TERMS)
    has_validation = _has_any(combined, ["検証", "確認", "受入", "完了条件", "証拠", "test", "acceptance", "evidence"])
    return has_package_language and has_scope_control and has_validation


def _has_bounded_broad_scope_controls(plan: str, combined: str) -> bool:
    return (
        _has_any(combined, ["作業分解", "作業パッケージ", "成果物", "ファイル別", "段階", "stage", "work package"])
        and _has_any(combined, ["対象外", "非対象", "しない", "non-goal", "out of scope"])
        and _has_any(combined, ["順序", "依存", "先に", "後で", "dependency", "sequence"])
        and _has_any(combined, ["検証", "試験", "確認", "証拠", "受入", "test", "evidence"])
        and not _has_any(plan, ["無制限", "全部書き換え", "unbounded"])
    )


def _classify_requirements(text: str) -> list[str]:
    classifications = []
    checks = {
        "purpose": ["目的", "価値", "意義", "goal", "purpose", "value"],
        "stakeholder": ["ユーザー", "利用者", "運用者", "stakeholder", "user"],
        "solution": ["機能", "表示", "保存", "検索", "API", "function", "capability"],
        "transition": ["移行", "変換", "導入", "migration", "transition"],
        "quality": ["性能", "安全", "保守", "可用", "速", "security", "performance", "maintain"],
        "operation": ["運用", "通知", "実行", "ログ", "監視", "backup", "schedule"],
        "non_requirement": ["対象外", "しない", "非要求", "non-goal", "out of scope"],
    }
    for label, needles in checks.items():
        if _has_any(text, needles):
            classifications.append(label)
    return classifications or ["unclassified"]


def _has_solution_bias(text: str) -> bool:
    tools = ["SQLite", "PostgreSQL", "React", "Swift", "Python", "CLI", "MCP", "API", "JSON", "YAML"]
    return _has_any(text, tools) and not _has_any(text, ["なぜ", "理由", "because", "根拠", "必要", "原因"])


def _tokens(text: str) -> set[str]:
    return {token.lower() for token in re.findall(r"[A-Za-z0-9_一-龯ぁ-んァ-ヶー]{2,}", text)}


def _has_overlap(left: set[str], right: set[str], minimum: int) -> bool:
    ignored = {"する", "ある", "こと", "ため", "これ", "それ", "with", "that", "this", "from"}
    return len((left & right) - ignored) >= minimum


SUMMARY_FILE_CONTEXT_TERMS = (
    "changed",
    "changes",
    "updated",
    "modified",
    "added",
    "removed",
    "deleted",
    "touched",
    "files",
    "file",
    "変更",
    "更新",
    "修正",
    "追加",
    "削除",
    "変更ファイル",
    "変更対象",
)

SUMMARY_FILE_PATH_PATTERN = re.compile(
    r"""
    (?<![\w./-])
    (?:
        (?:[A-Za-z0-9_.@()+-]+/)+[A-Za-z0-9_.@()+-]+\.
            (?:py|js|ts|tsx|jsx|swift|go|rs|java|kt|c|cc|cpp|h|sh|css|html|sql|md|rst|txt|adoc|json|ya?ml|toml|lock)
        |
        (?:README|CHANGELOG|CONTRIBUTING|LICENSE)\.(?:md|txt)
        |
        pyproject\.toml
        |
        uv\.lock
        |
        requirements(?:-dev)?\.txt
        |
        package(?:-lock)?\.json
        |
        pnpm-lock\.yaml
        |
        yarn\.lock
        |
        Dockerfile
    )
    (?![\w./-])
    """,
    re.VERBOSE,
)


def _changed_files(diff: str) -> list[str]:
    files: list[str] = []
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            files.append(line[6:])
        elif line.startswith("diff --git "):
            match = re.search(r"\sb/(\S+)$", line)
            if match:
                files.append(match.group(1))
        elif line.startswith("rename to "):
            files.append(line.removeprefix("rename to ").strip())
        elif line.startswith("*** Update File: "):
            files.append(line.removeprefix("*** Update File: ").strip())
        elif line.startswith("*** Add File: "):
            files.append(line.removeprefix("*** Add File: ").strip())
        elif line.startswith("*** Delete File: "):
            files.append(line.removeprefix("*** Delete File: ").strip())
    header_files = _unique_nonempty([_clean_changed_file_candidate(path) for path in files])
    if header_files:
        return header_files
    return _summary_changed_files(diff)


def _summary_changed_files(text: str) -> list[str]:
    files: list[str] = []
    for line in text.splitlines():
        if not _line_can_list_changed_files(line):
            continue
        for match in SUMMARY_FILE_PATH_PATTERN.finditer(line):
            files.append(_clean_changed_file_candidate(match.group(0)))
    return _unique_nonempty(files)


def _line_can_list_changed_files(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if re.match(r"^(?:uv|python|pytest|git|semantic-guard|codex)\b", stripped):
        return False
    if _has_any(stripped, SUMMARY_FILE_CONTEXT_TERMS):
        return True
    return bool(re.match(r"^[-*]?\s*" + SUMMARY_FILE_PATH_PATTERN.pattern, stripped, re.VERBOSE))


def _clean_changed_file_candidate(path: str) -> str:
    cleaned = path.strip().strip("'\"`<>()[]{}")
    return cleaned.removeprefix("a/").removeprefix("b/")


def _is_source_file(path: str) -> bool:
    return path.endswith((".py", ".js", ".ts", ".tsx", ".jsx", ".swift", ".go", ".rs", ".java", ".kt", ".c", ".cc", ".cpp", ".h"))


def _is_test_file(path: str) -> bool:
    lowered = path.lower()
    return "/test" in lowered or "test_" in lowered or lowered.endswith((".spec.ts", ".test.ts", ".spec.js", ".test.js"))


def _is_doc_file(path: str) -> bool:
    return path.endswith((".md", ".rst", ".txt", ".adoc"))


def _is_document_only_boundary(boundary: dict[str, str], changed_files: list[str]) -> bool:
    return (
        boundary.get("boundary") == "evidence"
        and bool(changed_files)
        and all(_is_doc_file(path) for path in changed_files)
    )


def _complexity_signal(diff: str) -> int:
    added = [line for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++")]
    patterns = [" if ", " for ", " while ", " try", " except", " catch", " class ", " enum ", " switch ", " async ", " await "]
    return sum(sum(pattern in line for pattern in patterns) for line in added)


def _complexity_growth_signal(diff: str) -> str:
    if _complexity_signal(diff) < 8:
        return ""
    added = [line for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++")]
    return _compact_snippet("\n".join(added[:8]))


def _blocker(category: str, finding: str, suggested_fix: str, basis: list[str]) -> Finding:
    return Finding(
        severity="blocker",
        category=category,
        basis=basis,
        finding=finding,
        suggested_fix=suggested_fix,
    )


def _score_from_findings(findings: list[Finding]) -> float:
    score = 1.0
    for finding in findings:
        if finding.severity == "blocker":
            score -= 0.35
        elif finding.severity == "major":
            score -= 0.18
        elif finding.severity == "minor":
            score -= 0.07
    return max(0.0, score)


def _result(
    *,
    phase: str,
    findings: list[Finding],
    missing: list[str],
    score: float,
    details: dict[str, object],
    next_actions: list[str],
) -> dict[str, object]:
    _enrich_findings(phase, findings)
    if any(finding.severity == "blocker" for finding in findings):
        status = "block"
    elif any(finding.severity in {"major", "minor"} for finding in findings):
        status = "warn"
    elif findings and score < 0.75:
        status = "warn"
    else:
        status = "pass"
    enriched_details = dict(details)
    non_emitted_rules = _normalized_non_emitted_rules(
        enriched_details.get("non_emitted_rules") or enriched_details.get("suppressed_rules")
    )
    warning_class_counts = _warning_class_counts(findings)
    match_status_counts = _match_status_counts(findings)
    confidence_counts = _confidence_counts(findings)
    ambiguity_reason_counts = _ambiguity_reason_counts(findings)
    enriched_details["non_emitted_rules"] = non_emitted_rules
    enriched_details["suppressed_rules"] = non_emitted_rules
    enriched_details["suppressed_rule_counts"] = _suppressed_rule_counts(non_emitted_rules)
    enriched_details["non_emitted_rule_counts"] = _non_emitted_rule_counts(non_emitted_rules)
    enriched_details["warning_class_counts"] = warning_class_counts
    enriched_details["match_status_counts"] = match_status_counts
    enriched_details["confidence_counts"] = confidence_counts
    enriched_details["ambiguity_reason_counts"] = ambiguity_reason_counts
    enriched_details["diagnostics"] = _diagnostic_envelope(
        findings=findings,
        non_emitted_rules=non_emitted_rules,
        warning_class_counts=warning_class_counts,
        match_status_counts=match_status_counts,
        confidence_counts=confidence_counts,
        ambiguity_reason_counts=ambiguity_reason_counts,
    )
    logical_trace = enriched_details.get("logical_trace")
    if isinstance(logical_trace, dict):
        rules_evaluated = logical_trace.get("rules_evaluated", [])
        facts = logical_trace.get("facts", [])
        logical_trace_summary = _logical_trace_summary(logical_trace)
        enriched_details["logical_trace_summary"] = logical_trace_summary
        enriched_details["diagnostics"]["logical_trace"] = {
            "schema_version": logical_trace.get("schema_version", ""),
            "scope": logical_trace.get("scope", ""),
            "derivation_scope": logical_trace.get("derivation_scope", ""),
            "rule_count": len(rules_evaluated) if isinstance(rules_evaluated, list) else 0,
            "fact_count": len(facts) if isinstance(facts, list) else 0,
            "summary_schema_version": logical_trace_summary.get("schema_version", ""),
        }
    return AuditResult(
        phase=phase,
        status=status,
        score=score,
        findings=findings,
        missing=missing,
        next_actions=next_actions,
        details=enriched_details,
    ).as_dict()


def _logical_trace_summary(logical_trace: dict[str, object]) -> dict[str, object]:
    raw_rules = logical_trace.get("rules_evaluated", [])
    raw_obligations = logical_trace.get("obligations", [])
    raw_unknowns = logical_trace.get("unknowns", [])
    raw_conflicts = logical_trace.get("conflicts", [])
    raw_facts = logical_trace.get("facts", [])
    rules = [rule for rule in raw_rules if isinstance(rule, dict)] if isinstance(raw_rules, list) else []
    obligations = [item for item in raw_obligations if isinstance(item, dict)] if isinstance(raw_obligations, list) else []
    unknowns = [item for item in raw_unknowns if isinstance(item, str)] if isinstance(raw_unknowns, list) else []
    conflicts = [item for item in raw_conflicts if isinstance(item, str)] if isinstance(raw_conflicts, list) else []
    facts = raw_facts if isinstance(raw_facts, list) else []
    fact_count = len(facts) if isinstance(facts, list) else 0

    return {
        "schema_version": LOGICAL_TRACE_SUMMARY_SCHEMA_VERSION,
        "source_schema_version": str(logical_trace.get("schema_version", "")),
        "scope": str(logical_trace.get("scope", "")),
        "derivation_scope": str(logical_trace.get("derivation_scope", "")),
        "rule_count": len(rules),
        "fact_count": fact_count,
        "unknown_count": len(unknowns),
        "conflict_count": len(conflicts),
        "rules": [_logical_trace_rule_summary(rule, obligations) for rule in rules],
    }


def _logical_trace_rule_summary(rule: dict[str, object], obligations: list[dict[str, object]]) -> dict[str, object]:
    rule_id = str(rule.get("rule_id", ""))
    rule_obligations = [item for item in obligations if str(item.get("rule_id", "")) == rule_id]
    raw_finding_ids = rule.get("finding_ids", [])
    raw_derivation_steps = rule.get("derivation_steps", [])
    raw_counterconditions = rule.get("counterconditions_checked", [])
    finding_ids = [str(item) for item in raw_finding_ids if isinstance(item, str)] if isinstance(raw_finding_ids, list) else []
    derivation_steps = [str(item) for item in raw_derivation_steps if isinstance(item, str)] if isinstance(raw_derivation_steps, list) else []
    counterconditions = [str(item) for item in raw_counterconditions if isinstance(item, str)] if isinstance(raw_counterconditions, list) else []

    return {
        "rule_id": rule_id,
        "status": str(rule.get("status", "")),
        "finding_ids": finding_ids,
        "finding_count": len(finding_ids),
        "missing_obligation_count": sum(1 for item in rule_obligations if item.get("status") == "missing"),
        "unknown_obligation_count": sum(1 for item in rule_obligations if item.get("status") == "unknown"),
        "conflict_obligation_count": sum(1 for item in rule_obligations if item.get("status") == "conflict"),
        "countercondition_count": len(counterconditions),
        "derivation_step_count": len(derivation_steps),
    }


def _enrich_findings(phase: str, findings: list[Finding]) -> None:
    for finding in findings:
        if not finding.rule_id:
            finding.rule_id = infer_rule_id(phase, finding)
        if not finding.repair:
            finding.repair = repair_for_finding(finding.rule_id, finding)


def _warning_class_counts(findings: list[Finding]) -> dict[str, int]:
    counts = {"actionable": 0, "generic caution": 0, "possible false positive": 0}
    for finding in findings:
        counts[finding.warning_class] = counts.get(finding.warning_class, 0) + 1
    return counts


def _match_status_counts(findings: list[Finding]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for finding in findings:
        if finding.match_status:
            counts[finding.match_status] = counts.get(finding.match_status, 0) + 1
    return dict(sorted(counts.items()))


def _confidence_counts(findings: list[Finding]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for finding in findings:
        if finding.confidence:
            counts[finding.confidence] = counts.get(finding.confidence, 0) + 1
    return dict(sorted(counts.items()))


def _ambiguity_reason_counts(findings: list[Finding]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for finding in findings:
        for reason in finding.ambiguity_reasons:
            counts[reason] = counts.get(reason, 0) + 1
    return dict(sorted(counts.items()))


def _normalized_suppressed_rules(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _normalized_non_emitted_rules(value: object) -> list[dict[str, object]]:
    normalized = _normalized_suppressed_rules(value)
    for item in normalized:
        if "emission_status" not in item:
            item["emission_status"] = "not_applicable"
        if "match_status" not in item:
            item["match_status"] = "not_applicable" if item["emission_status"] == "not_applicable" else "matched"
    return normalized


def _suppressed_rule_counts(suppressed_rules: list[dict[str, object]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in suppressed_rules:
        rule_id = item.get("rule_id")
        if isinstance(rule_id, str) and rule_id:
            counts[rule_id] = counts.get(rule_id, 0) + 1
    return dict(sorted(counts.items()))


def _non_emitted_rule_counts(non_emitted_rules: list[dict[str, object]]) -> dict[str, object]:
    by_rule_id: dict[str, int] = {}
    by_emission_status: dict[str, int] = {}
    for item in non_emitted_rules:
        rule_id = str(item.get("rule_id", ""))
        emission_status = str(item.get("emission_status", "unknown"))
        if rule_id:
            by_rule_id[rule_id] = by_rule_id.get(rule_id, 0) + 1
        by_emission_status[emission_status] = by_emission_status.get(emission_status, 0) + 1
    return {
        "by_rule_id": dict(sorted(by_rule_id.items())),
        "by_emission_status": dict(sorted(by_emission_status.items())),
    }


def _diagnostic_envelope(
    *,
    findings: list[Finding],
    non_emitted_rules: list[dict[str, object]],
    warning_class_counts: dict[str, int],
    match_status_counts: dict[str, int],
    confidence_counts: dict[str, int],
    ambiguity_reason_counts: dict[str, int],
) -> dict[str, object]:
    return {
        "emitted_findings": {
            "count": len(findings),
            "by_category": _finding_category_counts(findings),
            "by_rule_id": _finding_rule_counts(findings),
            "warning_class_counts": warning_class_counts,
        },
        "non_emitted_rules": {
            "count": len(non_emitted_rules),
            **_non_emitted_rule_counts(non_emitted_rules),
        },
        "field_match_diagnostics": {
            "match_status_counts": match_status_counts,
            "confidence_counts": confidence_counts,
            "ambiguity_reason_counts": ambiguity_reason_counts,
        },
    }


def _finding_category_counts(findings: list[Finding]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for finding in findings:
        counts[finding.category] = counts.get(finding.category, 0) + 1
    return dict(sorted(counts.items()))


def _finding_rule_counts(findings: list[Finding]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for finding in findings:
        if finding.rule_id:
            counts[finding.rule_id] = counts.get(finding.rule_id, 0) + 1
    return dict(sorted(counts.items()))


def _next_actions(findings: list[Finding], fallback: str) -> list[str]:
    if not findings:
        return []
    blockers = [finding for finding in findings if finding.severity == "blocker"]
    if blockers:
        return [blockers[0].suggested_fix or fallback]
    majors = [finding for finding in findings if finding.severity == "major"]
    if majors:
        return [majors[0].suggested_fix or fallback]
    return [fallback]
