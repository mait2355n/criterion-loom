from __future__ import annotations

import re

from semantic_guard.models import Finding
from semantic_guard.result_builder import build_result
from semantic_guard.text_utils import (
    first_match as _first_match,
    has_any as _has_any,
)

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
DEFAULT_SNIPPET_LIMIT = 220
INPUT_KINDS = {"requirement", "plan", "document", "diff-summary"}

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


def _normalize_input_kind(input_kind: str) -> str:
    normalized = (input_kind or "requirement").strip().lower().replace("_", "-")
    if normalized not in INPUT_KINDS:
        return "requirement"
    return normalized


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


def _blocker(category: str, finding: str, suggested_fix: str, basis: list[str]) -> Finding:
    return Finding(
        severity="blocker",
        category=category,
        basis=basis,
        finding=finding,
        suggested_fix=suggested_fix,
    )


def _result(
    *,
    phase: str,
    findings: list[Finding],
    missing: list[str],
    score: float,
    details: dict[str, object],
    next_actions: list[str],
) -> dict[str, object]:
    return build_result(
        phase=phase,
        findings=findings,
        missing=missing,
        score=score,
        details=details,
        next_actions=next_actions,
        logical_trace_summary_builder=_logical_trace_summary,
    )


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
