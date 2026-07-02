from __future__ import annotations

from semantic_guard.audit_common import BASIS, _add_ambiguity_findings, _result
from semantic_guard.field_detection import missing_field_finding as _missing_field_finding, score_field as _score_field
from semantic_guard.models import Finding
from semantic_guard.result_builder import next_actions as _next_actions
from semantic_guard.text_utils import combine as _combine

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
