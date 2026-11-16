from __future__ import annotations

import re

from semantic_guard_workflow.audit_common import (
    BASIS,
    _BEHAVIOR_DECLARATIONS,
    _blocker,
    _has_asserted_any,
    _has_behavior_evidence,
    _implemented_public_behavior,
    _result,
    _security_signal,
)
from semantic_guard_workflow.assertion_context import (
    AssertionMatch,
    find_field_assertion,
    find_field_assertions,
)
from semantic_guard_workflow.models import Finding
from semantic_guard_workflow.result_builder import next_actions as _next_actions, score_from_findings as _score_from_findings
from semantic_guard_workflow.text_utils import (
    combine as _combine,
    compact_snippet as _compact_snippet,
    has_any as _has_any,
)
from semantic_guard_workflow.text_normalization import normalize_audit_text


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
    "risk": (
        "残リスク", "残余リスク", "残存リスク", "未確認事項", "未実行事項",
        "residual risk", "residual risks", "risk", "risks", "unknown", "unknowns",
    ),
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
# A trailing copula does not turn an unresolved value into a receipt:
# 「未確認です」 is as unresolved as 「未確認」.
_COMPLETION_COPULA = r"(?:です|だ|である|でした|だった|のまま(?:です|だ|である)?)?"
_UNRESOLVED_COMPLETION_VALUE = re.compile(
    r"^(?:[:：はがもを]\s*)?(?:(?:is|are|was|were|has been|have been|has|have|had)\s+)?"
    r"(?:(?:まだ|現時点では?|今回は)\s*)?"
    r"(?:(?:未実行|未実施|未検証|未確認|未試験|未着手|未了|まだ|これから|スキップ|省略|見送り)"
    + _COMPLETION_COPULA
    + r"|unknown|skipped|omitted|deferred|not\s+done"
    r"|not\s+(?:yet\s+)?(?:been\s+)?(?:run|executed|performed|verified|checked))$",
    re.IGNORECASE,
)
# The matched term is itself the action noun (検証, 確認, 実行, テスト ...), so a
# negated する-form directly after it denies the action instead of reporting it.
_NEGATED_COMPLETION_PREDICATE = re.compile(
    r"^(?:[はがもを]\s*)?(?:(?:まだ|現時点では?|今回は|一切|全く|何も)\s*)?"
    r"(?:"
    r"して(?:い)?(?:ない|ません|なかった|ませんでした)"
    r"|し(?:ない|ません|なかった|ませんでした)"
    r"|せず"
    r"|されて(?:い)?(?:ない|ません)"
    r"|でき(?:て(?:い)?)?(?:ない|ません|なかった|ませんでした)"
    r"|行って(?:い)?(?:ない|ません)|行わ(?:ない|なかった|ず)|行えて(?:い)?(?:ない|ません)"
    r"|(?:省略|スキップ|見送[りっ]|割愛)"
    r")"
)
# ASCII word edges. Japanese text does not separate words with spaces, and to
# ``\b`` a kana or kanji neighbour is a word character: 「CIが」 has no boundary
# after ``CI``. These treat any non-ASCII neighbour as an edge.
_W0 = r"(?<![A-Za-z0-9_])"
_W1 = r"(?![A-Za-z0-9_])"
_SKIPPED_ACTION_PREFIX = re.compile(
    rf"(?:{_W0}(?:skipped|omitted|deferred)|{_W0}unable\s+to\s+(?:run|execute|perform))\s+"
    r"(?:(?:all\s+)?(?:of\s+)?the\s+|all\s+|any\s+)?$",
    re.IGNORECASE,
)

# --- reported failure -------------------------------------------------------
# A completion claim cannot rest on a verification that is reported as failed.
# Only result statements are read: a count above zero, or a perfective/ongoing
# failure of a named verification activity. Conditionals (失敗した場合), failure
# handling descriptions, attributive uses (失敗したテストを修正) and past states
# (失敗していた) are not results and stay outside.
_FAILURE_SUBJECT = re.compile(
    r"テスト|試験|検証|確認|ビルド|受入|実行|スモーク|チェック|型検査|リント"
    rf"|{_W0}(?:pytest|unittest|tests?|checks?|build|ci|lint|typecheck|type\s+check(?:ing)?|pipeline|suite"
    rf"|smoke|execution|run|verification|validation){_W1}",
    re.IGNORECASE,
)
_JA_FAILURE_UNIT = r"(?:件|個|本|ケース|項目|入力|テスト|試験)"
_JA_FAILURE_WORD = r"(?:失敗|不合格|NG)"
_JA_FAILURE_NOT_A_RESULT = r"(?!\s*(?:して(?:い)?た|で|の場合|以上|以下|まで|ごと|毎|を超))"
# 「失敗3件でロックする」 is a threshold in a requirement, and 「失敗3回」 a retry
# count; neither is a verification result. The unit is matched without
# backtracking so the exclusion cannot be dodged by dropping it.
_JA_COUNT_NOT_A_RESULT = r"(?!\s*(?:で|の場合|以上|以下|まで|ごと|毎|を超|回|秒|分|時間|日|%|％))"
_JA_FAILURE_COUNT = re.compile(
    rf"(?<!\d)(?P<before>\d+)\s*{_JA_FAILURE_UNIT}\s*"
    rf"(?:の\s*(?:テスト|試験|ケース|項目)\s*)?(?:が|は|も)?\s*{_JA_FAILURE_WORD}{_JA_FAILURE_NOT_A_RESULT}"
    rf"|{_JA_FAILURE_WORD}\s*(?:[:：=]|は|が)?\s*(?P<after>\d+)(?!\d)\s*"
    rf"(?:{_JA_FAILURE_UNIT}{_JA_COUNT_NOT_A_RESULT}|(?!{_JA_FAILURE_UNIT}){_JA_COUNT_NOT_A_RESULT})"
)
_JA_FAILURE_RESULT = re.compile(
    r"失敗(?:した|しました|して(?:い)?(?:る|ます)|しており|中)"
    r"(?!\s*(?:場合|とき|時|際|ら|テスト|試験|ケース|項目|箇所|原因|理由|もの|こと|の))"
    r"|(?:テスト|試験|検証|CI|ビルド|チェック)\s*(?:が|は|も|に)\s*(?:まだ\s*|一部\s*)?"
    r"(?:通ら(?:ない|なかった|ず)|通って(?:い)?(?:ない|ません)|通りません(?:でした)?"
    r"|落ち(?:た|ました|て(?:い)?(?:る|ます)))"
)
_UNMET_ACCEPTANCE = re.compile(
    r"(?:受入(?:基準|条件)|完了条件)[^。.!?\n]{0,24}?"
    r"(?:満た(?:して(?:い)?(?:ない|ません)|さない|しません|せて(?:い)?(?:ない|ません)|せなかった|せず)"
    r"|未達|未充足)"
    rf"|{_W0}acceptance\s+criteri(?:a|on)\s+(?:(?:is|are|was|were)\s+)?"
    rf"(?:not\s+(?:yet\s+)?(?:met|satisfied)|unmet){_W1}",
    re.IGNORECASE,
)
_EN_FAILURE_RESULT = re.compile(
    rf"{_W0}(?:tests?|checks?|build|ci|pipeline|suite|lint|type\s*check(?:ing)?|verification|validation"
    r"|execution|run|smoke(?:\s+test)?)\s+"
    rf"(?:(?:has|have|is|are|still|also)\s+)*(?:failed|failing|fails){_W1}"
    rf"|{_W0}(?:did|does|do)\s+not\s+pass{_W1}|{_W0}(?:is|are)\s+not\s+passing{_W1}",
    re.IGNORECASE,
)
_EN_FAILURE_NEGATED_PREFIX = re.compile(
    rf"{_W0}(?:no|none\s+of\s+the|zero|without\s+any)\s+$", re.IGNORECASE
)
# Runner output: an upper-case verdict at line start or in front of a test id.
_RUNNER_FAILED_VERDICT = re.compile(
    rf"(?:^|\n)\s*FAILED{_W1}|{_W0}FAILED\s+[\w./-]+(?:::|\.py{_W1}|\.js{_W1}|\.ts{_W1})"
)
_EN_COUNT_LABELS = r"(?:total|passed|failed|failures|errors|skipped)"
_EN_NOT_A_TEST_COUNT = (
    r"(?!\s*(?:attempts?|logins?|requests?|retries|tries|times?|payments?|jobs?|transactions?|messages?"
    r"|ms|s|%)(?![A-Za-z]))"
)
_EN_LABEL_THEN_COUNT = re.compile(
    rf"{_W0}(?P<label>{_EN_COUNT_LABELS})\s*[:=]?\s*(?P<count>\d+){_W1}{_EN_NOT_A_TEST_COUNT}",
    re.IGNORECASE,
)
_EN_COUNT_THEN_LABEL = re.compile(
    rf"(?<![A-Za-z0-9_.])(?P<count>\d+)\s+(?:(?:tests?|cases?|checks?|assertions?)\s+)?"
    rf"(?P<label>{_EN_COUNT_LABELS}|failing|failure|error|errored){_W1}{_EN_NOT_A_TEST_COUNT}",
    re.IGNORECASE,
)
_EN_FAILURE_LABELS = frozenset({"failed", "failing", "failure", "failures"})
_EN_ERROR_LABELS = frozenset({"error", "errors", "errored"})
# "3 errors" is a failure count only inside a runner summary; a validator that
# returns three errors for an invalid input is the expected behaviour.
_RUNNER_SUMMARY_CONTEXT = re.compile(rf"{_W0}(?:pytest|unittest|passed|failed){_W1}", re.IGNORECASE)
_REVERIFIED_SUCCESS = re.compile(
    r"(?:再実行|再試験|再検証|再テスト|再度の?(?:実行|試験|検証|テスト)|もう一度(?:実行|試験|検証))"
    r"[^。.\n]{0,40}(?:成功|通過|合格|通っ|全件|passed|pass|green|OK)"
    r"|(?:その後|現在は|今は|修正後(?:は|に)?)[^。.\n]{0,40}"
    r"(?:成功|通過|合格|通っ(?:た|ている|ています)|passed|green)"
    rf"|{_W0}(?:re-?ran|re-?run|rerun|after\s+(?:the\s+)?fix(?:es|ing)?|now){_W1}[^.\n]{{0,60}}"
    rf"{_W0}(?:pass(?:ed|es|ing)?|green|succeed(?:ed|s)?){_W1}",
    re.IGNORECASE,
)

# --- inspectable receipt ----------------------------------------------------
# 「検証済み」 states that something was done. A receipt additionally names
# what was run or what came out, so that someone else could check it.
_VERIFICATION_RECEIPT = re.compile(
    rf"{_W0}(?:pytest|unittest|tox|nox|jest|vitest|mocha|rspec|phpunit|ctest|junit|gtest|doctest"
    rf"|playwright|cypress|semantic-guard){_W1}"
    rf"|{_W0}(?:uv|npm|pnpm|yarn|go|cargo|swift|gradle|gradlew|mvn|make|dotnet|bazel|python3?|node|deno|bun"
    r"|bundle|rake|pip|ruff|mypy|pyright|eslint|tsc|curl|git|docker|kubectl)\s+[A-Za-z0-9_./:-]"
    r"|`[^`\n]+`"
    r"|(?:^|\s)\$\s+\S+"
    rf"|\d+\s*(?:passed|failed|tests?|cases?|assertions?|checks?|files?){_W1}"
    r"|\d+\s*(?:件|項目|ケース|入力|回|個|本|ファイル|テスト|試験)"
    rf"|{_W0}\d+\s*/\s*\d+{_W1}"
    rf"|{_W0}(?:pass_rate|exit\s+(?:code|status)|returncode|stdout|stderr){_W1}|終了コード"
    rf"|{_W0}(?:run|job|build)\s*#?\s*\d{{3,}}{_W1}"
    rf"|[\w./-]+\.(?:log|json|jsonl|txt|xml|html|png|jpe?g|csv|md|ya?ml|out){_W1}"
    r"|https?://\S+"
    r"|ログ|スクリーンショット|実行結果|出力結果",
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
    """One asserted occurrence is enough; a denied one cannot hide another."""
    return any(_occurrence_is_asserted(clause, match) for match in find_field_assertions(clause, terms))


def _occurrence_is_asserted(clause: str, match: AssertionMatch) -> bool:
    if match.status != "present":
        return False
    if match.start > 0 and clause[match.start - 1] == "未":
        return False
    if _SKIPPED_ACTION_PREFIX.search(clause[:match.start]):
        return False
    tail = clause[match.end:].strip().rstrip(".")
    if _UNRESOLVED_COMPLETION_VALUE.fullmatch(tail):
        return False
    return not _NEGATED_COMPLETION_PREDICATE.match(tail)


def _reported_failure(text: str) -> str:
    """Return the clause that reports a verification failure left unresolved.

    Reads result statements in the summary and evidence only; the caller keeps
    request context out, because the task itself may be "the tests fail".
    A later clause that records a successful re-verification closes an earlier
    failure. This is a bounded lexical reading, not a contradiction parser.
    """
    open_failure = ""
    for clause in _completion_clauses(text):
        failure_end = _last_failure_end(clause)
        reverified = [match.start() for match in _REVERIFIED_SUCCESS.finditer(clause)]
        if failure_end < 0:
            if reverified:
                open_failure = ""
            continue
        # 「3件失敗、修正して再実行し全件成功」 closes itself; the reverse order does not.
        if any(start >= failure_end for start in reverified):
            open_failure = ""
            continue
        open_failure = open_failure or clause
    return open_failure


def _last_failure_end(clause: str) -> int:
    """Offset just past the last failure result in the clause, or -1."""
    ends = [
        match.end()
        for match in _JA_FAILURE_COUNT.finditer(clause)
        if int(match.group("before") or match.group("after")) > 0
    ]
    ends.extend(_english_failure_count_ends(clause))
    ends.extend(match.end() for match in _RUNNER_FAILED_VERDICT.finditer(clause))
    ends.extend(match.end() for match in _UNMET_ACCEPTANCE.finditer(clause))
    if _FAILURE_SUBJECT.search(clause):
        ends.extend(match.end() for match in _JA_FAILURE_RESULT.finditer(clause))
        ends.extend(
            match.end()
            for match in _EN_FAILURE_RESULT.finditer(clause)
            if not _EN_FAILURE_NEGATED_PREFIX.search(clause[:match.start()])
        )
    return max(ends, default=-1)


def _english_failure_count_ends(clause: str) -> list[int]:
    """Read a runner summary in whichever order it pairs counts with labels.

    ``3 failed, 117 passed`` puts the count first; ``passed 6 failed 0`` puts
    the label first. The order with more complete pairs decides which number
    belongs to ``failed``.
    """
    label_first = list(_EN_LABEL_THEN_COUNT.finditer(clause))
    count_first = list(_EN_COUNT_THEN_LABEL.finditer(clause))
    pairs = label_first if len(label_first) > len(count_first) else count_first
    in_runner_summary = bool(_RUNNER_SUMMARY_CONTEXT.search(clause))
    ends: list[int] = []
    for pair in pairs:
        label = pair.group("label").lower()
        counts_as_failure = label in _EN_FAILURE_LABELS or (label in _EN_ERROR_LABELS and in_runner_summary)
        if counts_as_failure and int(pair.group("count")) > 0:
            ends.append(pair.end())
    return ends


def _has_verification_receipt(text: str) -> bool:
    """Is any verification statement backed by something another person could check?

    A command or tool name, a count, an exit state, or the location of an
    output qualifies. This checks that a receipt is named, not that it is true.
    """
    for clause in _completion_clauses(text):
        if not clause or _RISK_LABEL.match(clause) or _ACCEPTANCE_CRITERION_LABEL.match(clause):
            continue
        if _NOT_RUN_REASON.search(clause) or not _VERIFICATION_RECEIPT.search(clause):
            continue
        if _present_completion_assertion(clause, _VERIFICATION_TERMS) or _has_behavior_evidence(clause):
            return True
    return False


# Names of a security check, and the surfaces such a check is about. A surface word
# counts only in a clause that also states a result, so "認証処理を変更した" is not evidence.
_SECURITY_EVIDENCE_TERMS = [
    "secret scan", "dependency", "owasp", "nist", "安全", "セキュリティ", "手動確認",
    "認可", "認証", "権限", "秘密情報", "機密", "脆弱性", "入力検証", "authz", "authn", "injection", "csrf", "xss",
]
# A statement of what was confirmed. A security word alone ("安全。", "dependency")
# names a topic and reports nothing; "未実施" and "していない" report the opposite.
_SECURITY_RESULT_STATEMENT = re.compile(
    r"(?:確認|実施|実行|検証|検査|検討|レビュー|テスト|試験|点検|監査)(?:した|しました|済み|済)"
    r"|スキャン(?:した|しました|済み|を実施)|問題(?:なし|はない|は見つからなかった|は検出されなかった)"
    r"|(?:検出|指摘|脆弱性)(?:なし|0件|はなかった|は見つからなかった|されなかった)|0\s*件|と(?:確認|判断|判定)\s*$|通過|合格"
    r"|\b(?:passed|clean|checked|verified|reviewed|scanned|audited|confirmed|ran)\b"
    r"|\bno\s+(?:findings|issues|vulnerabilit(?:y|ies))\b|\b0\s+(?:findings|issues|vulnerabilities)\b",
    re.IGNORECASE,
)
_SECURITY_CLAUSE_BOUNDARY = re.compile(r"[。\n；;]|(?<=[.!?])\s")


_RESIDUAL_RISK_TERMS = [
    "残リスク", "残余リスク", "残存リスク", "残る危険", "残る懸念", "残る問題", "リスクなし", "懸念なし", "未解決", "未実行", "未確認",
    "できなかった", "not run", "residual", "risk", "none",
]


def _has_security_evidence(text: str) -> bool:
    for clause in _SECURITY_CLAUSE_BOUNDARY.split(text):
        clause = clause.strip()
        if not clause:
            continue
        match = find_field_assertion(clause, _SECURITY_EVIDENCE_TERMS)
        if match is None or match.status != "present":
            continue
        if match.labelled or _SECURITY_RESULT_STATEMENT.search(clause):
            return True
    return False


def finish_check(summary: str, evidence: str = "", context: str = "", strict: bool = True) -> dict[str, object]:
    summary = normalize_audit_text(summary)
    evidence = normalize_audit_text(evidence)
    context = normalize_audit_text(context)
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

    # The request context may itself describe failing tests; only what the
    # completion report and its evidence state as a result is read here.
    reported_failure = _reported_failure(_combine(summary, evidence))
    if reported_failure:
        findings.append(
            Finding(
                severity="blocker" if strict else "major",
                category="evidence",
                basis=BASIS["implementation"],
                finding="検証の失敗または受入基準の未達が報告されている。",
                evidence=_compact_snippet(reported_failure),
                suggested_fix="失敗を解消して再実行した結果を記録するか、完了主張を取り下げ、未解消の失敗を人間判断へ渡す。",
                rule_id="finish.evidence.failure_reported",
            )
        )
        missing.append("failure_resolution")
    elif verification_present and not not_run_reason and not _has_verification_receipt(combined):
        findings.append(
            Finding(
                severity="major" if strict else "minor",
                category="evidence",
                basis=BASIS["implementation"],
                finding="検証の宣言はあるが、確かめられる実行記録が見えない。",
                suggested_fix="実行したコマンド、件数、出力、保存先など、後から確かめられる記録を足す。",
                rule_id="finish.evidence.receipt_missing",
            )
        )
        missing.append("verification_receipt")

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

    if _security_signal(combined) and not _has_security_evidence(combined):
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

    if not _has_asserted_any(combined, _RESIDUAL_RISK_TERMS, accept_none=True):
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
