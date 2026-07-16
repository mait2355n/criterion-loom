from __future__ import annotations

import re
from collections.abc import Iterable

from semantic_guard.models import AuditResult, Finding

EXPLORATION_SCHEMA_VERSION = "request-exploration/v1"
ELICITATION_BASIS = ["semantic-implementation", "requirements elicitation", "ISO/IEC/IEEE 29148", "BABOK"]

AUDIENCE_TERMS = [
    "利用者",
    "対象者",
    "読者",
    "作者",
    "保守者",
    "運用者",
    "管理者",
    "連携先",
    "audience",
    "user",
    "stakeholder",
    "operator",
    "maintainer",
]
PROBLEM_TERMS = ["問題", "課題", "目的", "狙い", "意図", "価値", "なぜ", "problem", "purpose", "intent", "why", "value"]
NON_GOAL_TERMS = ["対象外", "非目標", "非要求", "しない", "やらない", "out of scope", "non-goal", "not doing"]
WORKFLOW_TERMS = ["導線", "手順", "流れ", "ワークフロー", "シナリオ", "ユースケース", "workflow", "flow", "scenario", "use case"]
ACCEPTANCE_TERMS = ["受入", "受入基準", "検証", "証拠", "証跡", "不合格", "acceptance", "verify", "evidence", "test"]
UNCERTAINTY_TERMS = ["未確定", "未決", "仮説", "判断待ち", "保留", "不明", "unknown", "hypothesis", "pending", "tbd"]
DATA_TERMS = [
    "保存",
    "資料",
    "データ",
    "状態",
    "履歴",
    "記録",
    "json",
    "yaml",
    "csv",
    "api",
    "cli",
    "mcp",
    "database",
    "db",
    "data",
    "state",
    "record",
]
IDENTITY_PRIVACY_TERMS = [
    "アカウント",
    "ログイン",
    "共有",
    "リンク",
    "秘匿",
    "権限",
    "個人",
    "認証",
    "決済",
    "支払い",
    "口座",
    "account",
    "login",
    "auth",
    "permission",
    "privacy",
    "private",
    "share",
    "link",
    "payment",
]
PRODUCT_TERMS = ["アプリ", "サービス", "画面", "web", "app", "product", "site", "tool"]
BILL_SPLIT_TERMS = ["割り勘", "精算", "立替", "支払い", "会計", "bill", "split", "expense", "settle"]
SOFTWARE_SURFACE_TERMS = ["api", "cli", "mcp", "json", "schema", "設定", "出力", "command", "tool"]
CREATIVE_TERMS = ["創作", "本文", "人物", "読者", "設定", "canon", "story", "character"]


def explore_request(text: str, context: str = "", strict: bool = True) -> dict[str, object]:
    """Expose material ambiguities before turning an open-ended idea into a spec."""
    combined = _combine(text, context)
    signals = _signals(combined)
    findings: list[Finding] = []
    missing: list[str] = []

    if not text.strip():
        findings.append(
            Finding(
                severity="blocker",
                category="exploration",
                basis=ELICITATION_BASIS,
                finding="探索対象の本文が空。",
                suggested_fix="初期案、変更したい対象、または実現したい状態を一文でも渡す。",
                needs_human_decision=True,
            )
        )
        missing.append("request_text")

    ambiguities = _material_ambiguities(combined, signals)
    for ambiguity in ambiguities:
        missing.append(str(ambiguity["id"]))
        findings.append(
            Finding(
                severity=str(ambiguity["severity"]),
                category=str(ambiguity["category"]),
                basis=ELICITATION_BASIS,
                evidence=str(ambiguity["evidence"]),
                finding=str(ambiguity["finding"]),
                suggested_fix=str(ambiguity["suggested_fix"]),
                needs_human_decision=True,
                semantic_boundaries=[
                    "This is an elicitation prompt, not a final requirement or implementation decision.",
                    "Ask only when the answer changes scope, data shape, privacy, external authority, risk, or acceptance.",
                ],
                match_status="missing",
                confidence=str(ambiguity["confidence"]),
                ambiguity_reasons=[str(ambiguity["reason"])],
            )
        )

    questions = [_question_from_ambiguity(item) for item in ambiguities]
    score = _score(signals, findings)
    return AuditResult(
        phase="explore_request",
        status=_status(findings),
        score=score,
        findings=findings,
        missing=_dedupe(missing),
        next_actions=_next_actions(questions),
        details={
            "schema_version": EXPLORATION_SCHEMA_VERSION,
            "purpose": "pre-spec ambiguity elicitation before audit-request or implementation planning",
            "signals": signals,
            "audience_hypotheses": _audience_hypotheses(combined),
            "material_ambiguities": ambiguities,
            "questions": questions,
            "question_policy": {
                "ask_when": [
                    "the answer changes product or implementation scope",
                    "the answer changes data model, identity, privacy, payment, permissions, or external authority",
                    "the answer changes acceptance evidence or rejection conditions",
                    "the answer separates fact, hypothesis, pending decision, and non-goal",
                ],
                "avoid_when": [
                    "the question only asks for taste or wording preference",
                    "a conservative assumption can be stated and verified later without material risk",
                ],
            },
            "spec_outline": _spec_outline(signals),
            "non_decisions": [
                "does not approve the idea",
                "does not choose the final audience",
                "does not turn hypotheses into requirements",
                "does not start implementation",
                "does not change final human acceptance",
            ],
            "score_semantics": "score is exploration coverage before a spec exists, not implementation quality or product value.",
        },
    ).as_dict()


def _material_ambiguities(text: str, signals: dict[str, bool]) -> list[dict[str, object]]:
    ambiguities: list[dict[str, object]] = []
    if not signals["has_audience"]:
        ambiguities.append(
            _ambiguity(
                "target_audience",
                "audience",
                "対象利用者または判断主体が見えない。",
                "誰のためのものかを一種類に絞るか、複数なら優先順位を付ける。",
                "対象利用者が変わると、導線、資料模型、権限、成功条件が変わる。",
                "誰が最初に使い、誰が成否を判断する？",
                "primary audience; secondary audience; acceptance owner",
                text,
                severity="major",
                reason="audience_absent",
            )
        )
    if not signals["has_problem"]:
        ambiguities.append(
            _ambiguity(
                "core_problem",
                "problem",
                "解く問題または上位目的が見えない。",
                "症状、原因仮説、目的を分けて書く。",
                "問題が曖昧なまま実装すると、手段だけが仕様化される。",
                "何が困っていて、なぜ今それを解く必要がある？",
                "problem; current pain; desired change; value if solved",
                text,
                severity="major",
                reason="problem_absent",
            )
        )
    if not signals["has_non_goals"]:
        ambiguities.append(
            _ambiguity(
                "scope_boundary",
                "scope",
                "非目標または対象外が見えない。",
                "今回やらないこと、混ぜると危険なことを明示する。",
                "境界が無いと、探索がそのまま実装範囲の膨張へ変わる。",
                "今回は何をあえてやらない？",
                "non-goals; excluded workflows; deferred decisions",
                text,
                severity="minor",
                reason="non_goals_absent",
            )
        )
    if signals["needs_workflow"] and not signals["has_workflow"]:
        ambiguities.append(
            _ambiguity(
                "primary_workflow",
                "workflow",
                "主要導線または利用場面が見えない。",
                "最初の利用開始から完了判定までの一連の流れを書く。",
                "導線が違うと必要な画面、コマンド、状態遷移、失敗処理が変わる。",
                "最も重要な一回の利用は、どこから始まり何で終わる？",
                "entry point; steps; completion state; failure state",
                text,
                severity="major",
                reason="workflow_absent",
            )
        )
    if signals["needs_data_model"] and not signals["has_data_model"]:
        ambiguities.append(
            _ambiguity(
                "data_or_state_model",
                "data_model",
                "扱う資料、状態、識別子、保存対象の境界が見えない。",
                "最低限の実体、関係、保存するもの、保存しないものを書く。",
                "資料模型が曖昧だと、後続の UI、API、永続化、監査証跡が噛み合わない。",
                "何を記録し、何を識別し、何を保存しない？",
                "entities; identifiers; relationships; stored fields; excluded data",
                text,
                severity="major",
                reason="data_model_absent",
            )
        )
    if signals["needs_identity_privacy"] and not signals["has_identity_privacy"]:
        ambiguities.append(
            _ambiguity(
                "identity_privacy_or_authority",
                "privacy",
                "本人性、秘匿性、権限、外部権威の前提が見えない。",
                "ログイン有無、共有範囲、支払い/権限/外部連携の扱いを明示する。",
                "ここを曖昧にすると、後から安全境界と資料模型を作り直す羽目になる。",
                "誰が何を見られて、誰が変更できて、外部の決済・権限へ触る？",
                "identity model; visibility; edit authority; external authority; privacy boundary",
                text,
                severity="major",
                reason="identity_privacy_absent",
            )
        )
    if not signals["has_acceptance"]:
        ambiguities.append(
            _ambiguity(
                "acceptance_evidence",
                "acceptance",
                "受入基準または検証証拠が見えない。",
                "何を見れば成功、何なら差し戻し、どんな証拠を残すかを書く。",
                "成功条件が無いと、後続監査が実装完了の顔をした好み判断になる。",
                "何が観測できれば十分で、何が起きたら失敗扱いにする？",
                "acceptance criteria; rejection condition; evidence artifact; owner",
                text,
                severity="major" if signals["needs_workflow"] else "minor",
                reason="acceptance_absent",
            )
        )
    if not signals["has_uncertainty"]:
        ambiguities.append(
            _ambiguity(
                "unresolved_decisions",
                "uncertainty",
                "未確定、仮説、判断待ちの扱いが見えない。",
                "確定事項、仮説、後で人間が決める点を分ける。",
                "不明点を確定扱いにすると、監査が価値判断を隠す。",
                "まだ決めていないこと、仮置きで進めることは何？",
                "known facts; hypotheses; pending decisions; decision owner",
                text,
                severity="minor",
                reason="uncertainty_absent",
                confidence="medium",
            )
        )
    return ambiguities


def _ambiguity(
    ambiguity_id: str,
    category: str,
    finding: str,
    suggested_fix: str,
    why_material: str,
    question: str,
    answer_shape: str,
    text: str,
    *,
    severity: str,
    reason: str,
    confidence: str = "high",
) -> dict[str, object]:
    return {
        "id": ambiguity_id,
        "category": category,
        "severity": severity,
        "finding": finding,
        "suggested_fix": suggested_fix,
        "question": question,
        "answer_shape": answer_shape,
        "affects": _affects_for(category),
        "why_material": why_material,
        "evidence": _excerpt(text),
        "reason": reason,
        "confidence": confidence,
        "needs_human_decision": True,
    }


def _question_from_ambiguity(ambiguity: dict[str, object]) -> dict[str, object]:
    return {
        "id": ambiguity["id"],
        "question": ambiguity["question"],
        "why": ambiguity["why_material"],
        "affects": ambiguity["affects"],
        "answer_shape": ambiguity["answer_shape"],
    }


def _audience_hypotheses(text: str) -> list[dict[str, object]]:
    if _has_any(text, BILL_SPLIT_TERMS):
        return [
            {
                "id": "link_participant",
                "label": "会員登録せずリンクから参加する支払参加者",
                "scope_implications": ["no-account identity", "shared bill visibility", "low-friction mobile flow"],
            },
            {
                "id": "organizer_or_payer",
                "label": "幹事または立替者",
                "scope_implications": ["expense entry speed", "settlement summary", "correction and audit trail"],
            },
            {
                "id": "recurring_group",
                "label": "同居、旅行、部活動など反復精算する小集団",
                "scope_implications": ["history", "member reuse", "recurring balances"],
            },
            {
                "id": "privacy_sensitive_participant",
                "label": "金額や支払先の見え方を気にする参加者",
                "scope_implications": ["visibility rules", "share boundary", "no payment credential storage by default"],
            },
        ]
    if _has_any(text, SOFTWARE_SURFACE_TERMS):
        return [
            {
                "id": "direct_user",
                "label": "その道具を直接操作する利用者",
                "scope_implications": ["command or UI ergonomics", "error messages", "observable behavior"],
            },
            {
                "id": "maintainer",
                "label": "実装を保守し、壊れ方を調べる保守者",
                "scope_implications": ["stable contracts", "tests", "diagnostics and rollback"],
            },
            {
                "id": "integrator",
                "label": "API、CLI、MCP、出力を呼び出す連携先",
                "scope_implications": ["versioned schema", "typed fields", "failure shape"],
            },
            {
                "id": "acceptance_owner",
                "label": "最終受入を判断する人間",
                "scope_implications": ["evidence bundle", "non-decisions", "residual risk notes"],
            },
        ]
    if _has_any(text, CREATIVE_TERMS):
        return [
            {
                "id": "reader",
                "label": "作品を読む読者",
                "scope_implications": ["first impression", "emotional payoff", "reading order"],
            },
            {
                "id": "author",
                "label": "本文や設定を更新する作者",
                "scope_implications": ["canon boundary", "unresolved facts", "revision path"],
            },
            {
                "id": "canon_maintainer",
                "label": "設定の整合と未確定事項を管理する保守者",
                "scope_implications": ["fact status", "source trace", "conflict handling"],
            },
        ]
    return [
        {
            "id": "primary_user",
            "label": "成果物を直接使う主利用者",
            "scope_implications": ["primary workflow", "success criteria", "error tolerance"],
        },
        {
            "id": "maintainer_or_operator",
            "label": "保守または運用する人",
            "scope_implications": ["diagnostics", "rollback", "support evidence"],
        },
        {
            "id": "decision_owner",
            "label": "受入、差し戻し、保留を決める人間",
            "scope_implications": ["acceptance criteria", "human review points", "residual risk"],
        },
    ]


def _spec_outline(signals: dict[str, bool]) -> list[dict[str, object]]:
    sections = [
        ("target_audience", "対象利用者と受入判断主体", True),
        ("core_problem", "解く問題、現状、目的", True),
        ("non_goals", "非目標と対象外", True),
        ("primary_workflows", "主要導線と失敗導線", True),
        ("data_model", "実体、識別子、状態、保存しない資料", signals["needs_data_model"]),
        ("identity_privacy_authority", "本人性、秘匿性、権限、外部権威", signals["needs_identity_privacy"]),
        ("acceptance_criteria", "受入基準、不合格条件、証拠", True),
        ("unresolved_decisions", "未確定、仮説、判断待ち", True),
        ("next_design_phase", "次の設計探索または実装計画への渡し方", True),
    ]
    return [{"id": section_id, "title": title, "required": required} for section_id, title, required in sections]


def _signals(text: str) -> dict[str, bool]:
    needs_workflow = _has_any(text, PRODUCT_TERMS + SOFTWARE_SURFACE_TERMS + CREATIVE_TERMS + BILL_SPLIT_TERMS)
    needs_data_model = _has_any(text, PRODUCT_TERMS + DATA_TERMS + BILL_SPLIT_TERMS + SOFTWARE_SURFACE_TERMS)
    needs_identity_privacy = _has_any(text, IDENTITY_PRIVACY_TERMS + BILL_SPLIT_TERMS)
    return {
        "has_text": bool(text.strip()),
        "has_audience": _has_any(text, AUDIENCE_TERMS),
        "has_problem": _has_any(text, PROBLEM_TERMS),
        "has_non_goals": _has_any(text, NON_GOAL_TERMS),
        "has_workflow": _has_any(text, WORKFLOW_TERMS),
        "has_data_model": _has_any(text, DATA_TERMS + ["実体", "識別子", "関係", "保存対象", "entities", "identifier"]),
        "has_identity_privacy": _has_any(text, IDENTITY_PRIVACY_TERMS),
        "has_acceptance": _has_any(text, ACCEPTANCE_TERMS),
        "has_uncertainty": _has_any(text, UNCERTAINTY_TERMS),
        "needs_workflow": needs_workflow,
        "needs_data_model": needs_data_model,
        "needs_identity_privacy": needs_identity_privacy,
    }


def _affects_for(category: str) -> list[str]:
    mapping = {
        "audience": ["scope", "workflow", "acceptance_owner", "risk_tolerance"],
        "problem": ["requirements", "priority", "non_goals", "acceptance"],
        "scope": ["implementation_boundary", "delivery_size", "deferred_work"],
        "workflow": ["screens_or_commands", "state_transitions", "failure_handling"],
        "data_model": ["storage", "interface_contract", "traceability", "migration"],
        "privacy": ["permissions", "identity", "external_authority", "security_review"],
        "acceptance": ["verification", "evidence", "human_review"],
        "uncertainty": ["decision_points", "hypotheses", "human_judgment_boundary"],
    }
    return mapping.get(category, ["scope", "verification"])


def _next_actions(questions: list[dict[str, object]]) -> list[str]:
    if not questions:
        return [
            "Write the spec using `details.spec_outline`.",
            "Run `audit-request` on the resulting spec before planning implementation.",
        ]
    return [
        "Answer only the questions in `details.questions` that would materially change scope or evidence.",
        "Convert answered material into a spec with `details.spec_outline`.",
        "Run `audit-request` on the spec before `audit-plan`.",
    ]


def _score(signals: dict[str, bool], findings: list[Finding]) -> float:
    if not signals["has_text"]:
        return 0.0
    required = ["has_audience", "has_problem", "has_non_goals", "has_acceptance", "has_uncertainty"]
    if signals["needs_workflow"]:
        required.append("has_workflow")
    if signals["needs_data_model"]:
        required.append("has_data_model")
    if signals["needs_identity_privacy"]:
        required.append("has_identity_privacy")
    present = sum(1 for item in required if signals[item])
    base = present / len(required)
    penalty = 0.08 * sum(1 for finding in findings if finding.severity == "major")
    penalty += 0.03 * sum(1 for finding in findings if finding.severity == "minor")
    return max(0.0, round(min(base, 1.0) - penalty, 3))


def _status(findings: list[Finding]) -> str:
    if any(finding.severity == "blocker" for finding in findings):
        return "block"
    if any(finding.severity in {"major", "minor"} for finding in findings):
        return "warn"
    return "pass"


def _combine(text: str, context: str = "") -> str:
    return "\n".join(part for part in [context, text] if part)


def _has_any(text: str, terms: Iterable[str]) -> bool:
    lowered = text.lower()
    for term in terms:
        normalized = term.lower()
        if _is_ascii_word(normalized):
            if re.search(rf"(?<![a-z0-9_]){re.escape(normalized)}(?![a-z0-9_])", lowered):
                return True
        elif normalized in lowered:
            return True
    return False


def _is_ascii_word(term: str) -> bool:
    return bool(re.fullmatch(r"[a-z0-9_ -]+", term))


def _excerpt(text: str) -> str:
    stripped = " ".join(line.strip() for line in text.splitlines() if line.strip())
    return (stripped or "No text supplied.")[:240]


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result
