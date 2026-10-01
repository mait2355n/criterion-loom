from __future__ import annotations

import re

from semantic_guard_workflow.audit_common import (
    BASIS,
    _BEHAVIOR_DECLARATIONS,
    _blocker,
    _has_behavior_evidence,
    _implemented_public_behavior,
    _result,
    _security_signal,
)
from semantic_guard_workflow.assertion_context import find_field_assertion
from semantic_guard_workflow.models import Finding
from semantic_guard_workflow.result_builder import next_actions as _next_actions, score_from_findings as _score_from_findings
from semantic_guard_workflow.text_utils import combine as _combine, has_any as _has_any


_VERIFICATION_TERMS = (
    "検証証拠", "試験証拠", "テスト証拠", "検証結果", "試験結果", "テスト結果",
    "verification evidence", "test evidence", "test results", "test result",
    "verification", "testing", "tests", "test", "pytest", "unittest",
    "swift test", "npm test", "uv run", "command", "execution",
    "検証", "確認", "試験", "テスト", "コマンド", "実行",
)
_ACCEPTANCE_TERMS = (
    "受入条件と証拠の対応", "受入基準と証拠の対応", "受入証拠", "受入条件",
    "受入基準", "受入", "完了条件", "acceptance evidence", "acceptance criteria",
    "verification evidence", "test evidence", "test results", "test result",
    "acceptance", "criteria", "evidence", "証拠", "結果",
)
_VERIFICATION_DECLARATIONS = (
    "検証証拠", "試験証拠", "テスト証拠", "検証結果", "試験結果", "テスト結果",
    "verification evidence", "test evidence", "test results", "test result",
    "verification", "testing", "tests", "test", "検証", "確認", "試験", "テスト",
)
_ACCEPTANCE_DECLARATIONS = (
    "受入条件と証拠の対応", "受入基準と証拠の対応", "受入証拠", "acceptance evidence",
)
_COMPLETION_HEADINGS = {
    "verification": _VERIFICATION_DECLARATIONS,
    "acceptance": _ACCEPTANCE_DECLARATIONS,
    "criterion": ("受入基準", "受入条件", "完了条件", "acceptance criteria", "criteria"),
    "risk": ("残リスク", "未確認事項", "未実行事項", "residual risk", "residual risks", "risk", "risks", "unknown", "unknowns"),
    "not_run_reason": ("未実行理由", "未実施理由", "未検証理由"),
    "behavior": _BEHAVIOR_DECLARATIONS,
}


def _heading_pattern(*kinds: str) -> str:
    terms = {term for kind in kinds for term in _COMPLETION_HEADINGS[kind]}
    patterns = [
        re.escape(term).replace(r"\ ", r"\s+")
        for term in sorted(terms, key=lambda term: (-len(term), term))
    ]
    return "(?:" + "|".join(patterns) + ")"


_COMPLETION_HEADING = re.compile(
    _heading_pattern(*(kind for kind in _COMPLETION_HEADINGS if kind != "behavior")) + r"\s*[:：]",
    re.IGNORECASE,
)
_COMPLETION_COMMA_BOUNDARY = re.compile(
    r"[,、，][^\S\r\n]*(?=" + _COMPLETION_HEADING.pattern + r")",
    re.IGNORECASE,
)
_BEHAVIOR_COMPLETION_HEADING = re.compile(
    _heading_pattern(*_COMPLETION_HEADINGS) + r"\s*[:：]", re.IGNORECASE,
)
_BEHAVIOR_COMMA_BOUNDARY = re.compile(
    r"[,、，][^\S\r\n]*(?=" + _BEHAVIOR_COMPLETION_HEADING.pattern + r")", re.IGNORECASE,
)
_RISK_LABEL = re.compile(
    "^" + _heading_pattern("risk") + r"\s*[:：は]",
    re.IGNORECASE,
)
_ACCEPTANCE_CRITERION_LABEL = re.compile(
    "^" + _heading_pattern("criterion") + r"\s*[:：]",
    re.IGNORECASE,
)
_NOT_RUN_REASON = re.compile(
    r"(?:未(?:実行|実施|検証)理由\s*[:：]\s*"
    r"|(?:tests?|verification)\s+(?:(?:were|was|are|is|have|has|had)\s+)?"
    r"not\s+(?:yet\s+)?(?:been\s+)?(?:run|executed|performed)\s*"
    r"(?:because\s+(?:of\s+)?|[:：]\s*))"
    r"(?P<reason>.*)$",
    re.IGNORECASE,
)
_UNRESOLVED_COMPLETION_VALUE = re.compile(
    r"^(?:[:：はがもを]\s*)?(?:(?:is|are|was|were|has been|have been|has|have|had)\s+)?"
    r"(?:未実行|未実施|未検証|未確認|未試験|unknown|not\s+(?:yet\s+)?"
    r"(?:been\s+)?(?:run|executed|performed|verified|checked))$",
    re.IGNORECASE,
)


def _completion_evidence_presence(text: str) -> tuple[bool, bool, bool]:
    """Check bounded completion clauses, not evidence authenticity or sufficiency.

    Reuse the shared assertion-context rules for absence and placeholders. Risk
    labels and criterion wording cannot supply an execution receipt. A concrete
    not-run reason accounts for execution only, never for acceptance evidence.
    Explicit evidence kinds take precedence over generic mentions elsewhere.
    Other independently stated receipts remain usable when one check is absent.
    This is not a general quotation, temporal-scope, or contradiction parser.
    """
    verification = acceptance = not_run_reason = False
    declared_verification = declared_acceptance = None
    for clause in _completion_clauses(text):
        if not clause or _RISK_LABEL.match(clause):
            continue
        reason_match = _NOT_RUN_REASON.search(clause)
        if reason_match:
            reason = reason_match.group("reason").strip().rstrip(".")
            reason_assertion = find_field_assertion(f"未実行理由: {reason}", ["未実行理由"])
            if (
                reason_assertion is not None
                and reason_assertion.status == "present"
                and not _UNRESOLVED_COMPLETION_VALUE.fullmatch(reason)
            ):
                not_run_reason = True
            continue
        if "未実行理由" in clause:
            # An empty reason heading must not be rescued by its 実行 substring.
            continue
        verification_state = _declared_completion_presence(clause, _VERIFICATION_DECLARATIONS)
        acceptance_state = _declared_completion_presence(clause, _ACCEPTANCE_DECLARATIONS)
        if verification_state is not None:
            declared_verification = bool(declared_verification) or verification_state
        if acceptance_state is not None:
            declared_acceptance = bool(declared_acceptance) or acceptance_state
        if not _ACCEPTANCE_CRITERION_LABEL.match(clause):
            verification |= _present_completion_assertion(clause, _VERIFICATION_TERMS)
        acceptance |= _present_completion_assertion(clause, _ACCEPTANCE_TERMS)
    return (
        verification if declared_verification is None else declared_verification,
        acceptance if declared_acceptance is None else declared_acceptance,
        not_run_reason,
    )


def _completion_clauses(text: str, *, behavior: bool = False) -> list[str]:
    """Keep registered field boundaries distinct from colons inside receipts.

    Behavior headings are opt-in so command-like values retain the existing
    verification/acceptance association in the default completion check.
    """
    heading = _BEHAVIOR_COMPLETION_HEADING if behavior else _COMPLETION_HEADING
    comma_boundary = _BEHAVIOR_COMMA_BOUNDARY if behavior else _COMPLETION_COMMA_BOUNDARY
    clauses: list[str] = []
    pending_label = ""
    for line in comma_boundary.sub("\n", text).splitlines():
        fragments = [
            re.sub(r"^\s*(?:#{1,6}\s+|[-*]\s+|\d+[.)]\s+)", "", part).strip()
            for part in re.split(r"[。！？；;]+|(?<=[.!?])\s+", line)
            if part.strip()
        ]
        if not fragments:
            continue
        if pending_label:
            if not heading.match(fragments[0]) and not _RISK_LABEL.match(fragments[0]):
                fragments[0] = f"{pending_label} {fragments[0]}"
            else:
                clauses.append(pending_label)
            pending_label = ""
        if line.rstrip().endswith((":", "：")) and heading.fullmatch(fragments[-1]):
            pending_label = fragments.pop()
        clauses.extend(fragments)
    if pending_label:
        clauses.append(pending_label)
    return clauses


def _declared_completion_presence(clause: str, terms: tuple[str, ...]) -> bool | None:
    match = find_field_assertion(clause, terms)
    if match is None or clause[:match.start].strip().lower() not in {"", "no", "without"}:
        return None
    return _present_completion_assertion(clause, terms)


def _present_completion_assertion(clause: str, terms: tuple[str, ...]) -> bool:
    match = find_field_assertion(clause, terms)
    if match is None or match.status != "present":
        return False
    if match.start > 0 and clause[match.start - 1] == "未":
        return False
    tail = clause[match.end:].strip().rstrip(".")
    return not _UNRESOLVED_COMPLETION_VALUE.fullmatch(tail)


def finish_check(summary: str, evidence: str = "", context: str = "", strict: bool = True) -> dict[str, object]:
    combined = _combine(summary, evidence, context)
    verification_present, acceptance_present, not_run_reason = _completion_evidence_presence(combined)
    findings: list[Finding] = []
    missing: list[str] = []

    if not summary.strip():
        findings.append(_blocker("evidence", "完了要約が空。", "変更内容と完了範囲を書く。", BASIS["implementation"]))
        missing.append("summary")

    if not (verification_present or not_run_reason):
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

    if not acceptance_present:
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

    behavior_present = any(
        _has_behavior_evidence(clause)
        for clause in _completion_clauses(combined, behavior=True)
        if not _RISK_LABEL.match(clause) and not _ACCEPTANCE_CRITERION_LABEL.match(clause)
    )
    if _implemented_public_behavior(combined) and not (behavior_present or not_run_reason):
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
