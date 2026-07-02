from __future__ import annotations

import re

from semantic_guard.audit_common import (
    BASIS,
    CHANGE_CONTROL_TERMS,
    SCOPE_BOUNDARY_TERMS,
    _has_any,
    _has_bounded_broad_scope_controls,
    _has_overlap,
    _normalize_input_kind,
    _result,
    _suppression_trace,
    _tokens,
)
from semantic_guard.field_detection import field_match_diagnostic as _field_match_diagnostic, missing_field_finding as _missing_field_finding
from semantic_guard.models import Finding
from semantic_guard.problem_signals import (
    _intervention_action_signal,
    _investigation_only_signal,
    _problem_or_symptom_signal,
    _side_effect_transfer_evidence_signal,
)
from semantic_guard.result_builder import next_actions as _next_actions, score_from_findings as _score_from_findings
from semantic_guard.text_utils import combine as _combine, first_match as _first_match

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

IDEMPOTENCY_REPEAT_TERMS = [
    "再実行",
    "再試行",
    "リトライ",
    "再送",
    "同じ処理",
    "同期処理",
    "定期実行",
    "キュー",
    "ジョブ",
    "retry",
    "rerun",
    "re-run",
    "resend",
    "sync job",
    "background job",
    "scheduled job",
    "queue",
    "cron",
]

IDEMPOTENCY_EFFECT_TERMS = [
    "作成",
    "登録",
    "送信",
    "通知",
    "保存",
    "更新",
    "同期",
    "公開",
    "配布",
    "削除",
    "書き込み",
    "create",
    "insert",
    "register",
    "send",
    "notify",
    "save",
    "update",
    "sync",
    "publish",
    "delete",
    "write",
]

IDEMPOTENCY_DUPLICATE_CONCERN_TERMS = [
    "二重作成",
    "二重登録",
    "二重送信",
    "重複作成",
    "重複登録",
    "重複送信",
    "重複通知",
    "duplicate",
    "duplication",
]

IDEMPOTENCY_STRONG_EVIDENCE_TERMS = [
    "冪等",
    "idempotent",
    "idempotency",
    "重複防止",
    "二重作成を防止",
    "二重登録を防止",
    "二重送信を防止",
    "重複送信を防止",
    "一度だけ",
    "一意制約",
    "一意キー",
    "unique constraint",
    "unique key",
    "idempotency key",
    "upsert",
    "deduplicate",
    "dedup",
    "exactly-once",
    "at-most-once",
    "排他",
    "ロック",
    "transaction",
    "atomic",
]

IDEMPOTENCY_DEFERRED_TERMS = [
    "あとで",
    "後で",
    "後続",
    "未定",
    "保留",
    "TODO",
    "TBD",
    "later",
]

READ_ONLY_PLAN_TERMS = [
    "読み取り専用",
    "調査のみ",
    "調査だけ",
    "確認のみ",
    "dry-run",
    "dry run",
    "書き込みなし",
    "副作用なし",
    "read-only",
    "no side effect",
    "no write",
]

RELEASE_TRIGGER_TERMS = [
    "公開する",
    "公開前",
    "公開後",
    "公開物",
    "公開版",
    "配布",
    "リリース",
    "release",
    "publish",
    "wheel",
    "sdist",
    "PyPI",
    "npm",
    "GitHub に上げる",
    "GitHubへ上げる",
]

RELEASE_NOT_APPLICABLE_TERMS = [
    "公開しない",
    "配布しない",
    "リリースしない",
    "非公開",
    "private only",
    "no release",
    "do not publish",
]

RELEASE_PROVENANCE_EVIDENCE_TERMS = [
    "版",
    "バージョン",
    "version",
    "tag",
    "タグ",
    "commit",
    "SHA",
    "checksum",
    "hash",
    "変更履歴",
    "changelog",
    "release note",
    "リリースノート",
    "生成物由来",
    "生成元",
    "出所",
    "由来",
    "provenance",
    "再現手順",
    "build command",
    "build 手順",
    "ビルド手順",
    "署名",
    "SBOM",
]

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

    idempotency_gap = _idempotency_gap_signal(plan, combined)
    if idempotency_gap:
        signals["idempotency"] = idempotency_gap

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

    release_provenance_gap = _release_provenance_gap_signal(plan, combined)
    if release_provenance_gap:
        signals["release_provenance"] = release_provenance_gap

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

    if "idempotency" in signals:
        finding = Finding(
            severity="major" if strict else "minor",
            category="reliability",
            basis=BASIS["planning"] + BASIS["implementation"],
            finding="再実行、再試行、同期、定期実行などの反復処理だが、冪等性や重複副作用の扱いが見えない。",
            evidence=signals["idempotency"],
            suggested_fix="再実行時の二重作成、重複送信、重複更新をどう防ぐか、冪等キー、一意制約、upsert、排他、重複検知、または対象外理由を明示する。",
            warning_class="generic caution",
            needs_human_decision=True,
        )
        finding.rule_id = "plan.system.idempotency_missing"
        findings.append(finding)
        missing.append("idempotency")

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

    if "release_provenance" in signals:
        finding = Finding(
            severity="minor",
            category="release",
            basis=BASIS["planning"] + BASIS["implementation"],
            finding="公開または配布を扱う計画だが、版、変更履歴、生成物の由来、または再現手順が見えない。",
            evidence=signals["release_provenance"],
            suggested_fix="公開物の版、tag/commit、変更履歴、生成物の出所、build/release 手順、照合方法、または不要理由を明示する。",
            warning_class="generic caution",
            needs_human_decision=True,
        )
        finding.rule_id = "plan.release.provenance_missing"
        findings.append(finding)
        missing.append("release_provenance")

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


def _idempotency_gap_signal(plan: str, combined: str) -> str:
    trigger = _first_match(plan, IDEMPOTENCY_REPEAT_TERMS)
    if not trigger:
        return ""
    if _has_any(combined, READ_ONLY_PLAN_TERMS):
        return ""

    duplicate_concern = _first_match(plan, IDEMPOTENCY_DUPLICATE_CONCERN_TERMS)
    if duplicate_concern and _has_any(duplicate_concern, IDEMPOTENCY_DEFERRED_TERMS):
        return duplicate_concern

    if _has_any(combined, IDEMPOTENCY_STRONG_EVIDENCE_TERMS):
        return ""
    if not (duplicate_concern or _has_any(plan, IDEMPOTENCY_EFFECT_TERMS)):
        return ""
    return duplicate_concern or trigger


def _release_provenance_gap_signal(plan: str, combined: str) -> str:
    trigger = _first_match(plan, RELEASE_TRIGGER_TERMS)
    if not trigger:
        return ""
    if _has_any(combined, RELEASE_NOT_APPLICABLE_TERMS):
        return ""
    if _has_any(combined, RELEASE_PROVENANCE_EVIDENCE_TERMS):
        return ""
    return trigger


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
