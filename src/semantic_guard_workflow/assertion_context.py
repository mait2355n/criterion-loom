from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Literal

from semantic_guard_workflow.text_utils import excerpt_around

AssertionStatus = Literal["present", "rejected"]


@dataclass(frozen=True)
class AssertionMatch:
    term: str
    start: int
    end: int
    excerpt: str
    status: AssertionStatus
    reason: str


_JAPANESE_EMPTY_VALUES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("empty_or_placeholder_value", ("", "-", "—", "―", "未記入")),
    ("deferred_placeholder", ("未定", "未策定", "未設定", "未定義", "未記載", "保留", "後日")),
    ("explicit_absence", ("なし", "無し", "無", "不要", "不明", "存在しない")),
)
_ENGLISH_EMPTY_VALUE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("empty_or_placeholder_value", re.compile(r"^(?:|[-—])$", re.IGNORECASE)),
    (
        "deferred_placeholder",
        re.compile(
            r"^(?:tbd|pending(?:\s+(?:owner|human|stakeholder)\s+decision)?"
            r"|not (?:yet )?(?:decided|specified|defined|set|determined)"
            r"|to be (?:decided|defined|determined|specified|set))\.?$",
            re.IGNORECASE,
        ),
    ),
    (
        "explicit_absence",
        re.compile(
            r"^(?:none|n\s*/?\s*a|not applicable|not (?:yet )?available|undefined|absent|missing|not defined)\.?$",
            re.IGNORECASE,
        ),
    ),
)
_JAPANESE_DEFERRED_VALUE = re.compile(
    r"^(?:(?:現在(?:は)?|現時点(?:では)?|今のところ(?:は)?|まだ|当面(?:は)?|今回は)\s*)?"
    r"(?:未定|未策定|未設定|未定義|未記載|保留)(?:です|である)?$"
    r"|^(?:後で|後ほど|今後|別途)\s*(?:決める|決定する|定める|設定する|策定する|記載する)(?:予定)?$"
)
_JAPANESE_ABSENCE_VALUE = re.compile(
    r"^(?:(?:現在(?:は)?|現時点(?:では)?|今のところ(?:は)?|まだ|当面(?:は)?|今回は)\s*)?"
    r"(?:なし|無し|不要|不明|存在しない|ありません|ございません)(?:です|である)?$"
)
_JAPANESE_NEGATED_FIELD_VALUE = re.compile(
    r"^(?:(?:現在(?:は)?|現時点(?:では)?|今のところ(?:は)?|まだ|当面(?:は)?|今回は)\s*)?"
    r"(?:"
    r"(?:定め|設け)(?:ない|ません|ず|ぬ)"
    r"|(?:設定|規定|定義|記載|用意|策定|明示|実施|実行|使用|採用|保持|保存|記録|作成|生成|提出|取得)"
    r"(?:しない|しません|せず|していない|していません|されていない|されていません)"
    r"|残(?:さない|しません|さず|していない|していません)"
    r"|行わ(?:ない|ず)"
    r")(?:です|方針です|こと(?:と|に)する)?$"
)
_ENGLISH_NEGATED_FIELD_VALUE = re.compile(
    r"^(?:"
    r"(?:currently\s+|presently\s+|for now\s+)?(?:not|never)\s+"
    r"(?:defined|specified|provided|available|retained|recorded|kept|created|set|established|decided|used|required|run|executed|performed|done)"
    r"|(?:will|shall|would|do|does|did|can|could)\s+not\s+(?:be\s+)?"
    r"(?:defined|specified|provided|retained|recorded|kept|created|set|established|used|required|run|executed|performed|done)"
    r"|(?:isn't|aren't|wasn't|weren't|won't|doesn't|don't|cannot|can't)\s+"
    r"(?:be\s+)?(?:defined|specified|provided|available|retained|recorded|kept|created|set|established|used|required|run|executed|performed|done)"
    r")\.?$",
    re.IGNORECASE,
)
_JAPANESE_NEGATED_RELATION = re.compile(
    r"^\s*(?:は|が|を|も|については)?\s*"
    r"(?:(?:今回は|現時点では?|現在は|現状では?|当面は?|今は|まだ|この段階では?)\s*)?"
    r"(?:"
    r"(?:ない|なし|無し|不要|不明|未定|未策定|未設定|未定義|未記載|ありません|ございません)"
    r"|(?:定め|設け)(?:ない|ません|ず|ぬ)"
    r"|(?:設定|規定|定義|記載|用意|策定|明示|保持|保存|記録|実施|実行|使用|採用|作成|生成|提出|取得)"
    r"(?:しない|しません|せず|していない|していません|されていない|されていません)"
    r"|残(?:さない|しません|さず|していない|していません)"
    r"|行わ(?:ない|ず)"
    r"|存在(?:し)?(?:ない|しません)"
    r")"
)
_ENGLISH_NEGATED_RELATION = re.compile(
    r"^\s*(?:"
    r"(?:is|are|was|were|has been|have been)\s+(?:(?:currently|presently|now|still)\s+)?not\s+(?:yet\s+)?"
    r"(?:defined|specified|provided|available|retained|recorded|kept|created|set|established|decided|present)"
    r"|(?:has|have|had)\s+not\s+been\s+"
    r"(?:defined|specified|provided|available|retained|recorded|kept|created|set|established|decided|present)"
    r"|(?:has|have)\s+yet\s+to\s+be\s+"
    r"(?:defined|specified|provided|made available|retained|recorded|created|set|established|decided)"
    r"|(?:is|are|remains?|remained)\s+(?:unavailable|undefined|absent|missing)"
    r"|(?:will|shall|do|does|did|can|could|would)\s+not\s+(?:be\s+)?"
    r"(?:defined|specified|provided|retained|recorded|kept|created|used|required|run|executed|performed|done|set|established|exist)"
    r"|(?:isn't|aren't|wasn't|weren't|won't|doesn't|don't|cannot|can't)\s+"
    r"(?:be\s+)?(?:defined|specified|provided|available|retained|recorded|kept|created|used|required|run|executed|performed|done|set|established|present|exist)"
    r")",
    re.IGNORECASE,
)
_ENGLISH_NEGATED_PREFIX = re.compile(r"(?:\bno|\bwithout)\s+$", re.IGNORECASE)
_ENGLISH_NEGATED_DETERMINER_PREFIX = re.compile(
    r"(?:\bthere\s+(?:isn't|aren't|wasn't|weren't)|\b(?:isn't|aren't|wasn't|weren't))\s+(?:any|an?|the)\s+$",
    re.IGNORECASE,
)
_ENGLISH_NEGATED_ACTION_PREFIX = re.compile(
    r"(?:"
    r"(?:"
    r"\b(?:do|does|did|will|shall|would|can|could)\s+not"
    r"|\b(?:don't|doesn't|didn't|won't|wouldn't|can't|cannot|couldn't)"
    r")\s+(?:define|specify|provide|retain|record|keep|create|set|establish|use|require|run|execute|perform)"
    r"|(?:"
    r"\b(?:have|has|had)\s+not"
    r"|\b(?:haven't|hasn't|hadn't)"
    r")\s+(?:defined|specified|provided|retained|recorded|kept|created|set|established|used|required|run|executed|performed)"
    r")\s+"
    r"(?:an?\s+|the\s+)?$",
    re.IGNORECASE,
)

_FIELD_KIND_MARKERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "evidence",
        (
            "evidence",
            "test result",
            "command output",
            "json output",
            "screenshot",
            "artifact",
            "report",
            "log",
            "record",
            "証拠",
            "証跡",
            "根拠",
            "結果",
            "ログ",
            "記録",
            "成果物",
            "報告",
        ),
    ),
    (
        "acceptance",
        (
            "acceptance",
            "success criteria",
            "definition of done",
            "done when",
            "accepted when",
            "pass condition",
            "pass if",
            "threshold",
            "metric",
            "受入",
            "合格",
            "完了",
            "成功",
            "達成",
            "基準",
            "条件",
            "閾値",
            "指標",
            "以内",
            "以下",
            "以上",
        ),
    ),
    (
        "method",
        (
            "verification",
            "verify",
            "test method",
            "test",
            "pytest",
            "unittest",
            "benchmark",
            "inspection",
            "review",
            "demonstration",
            "analysis",
            "measurement",
            "smoke",
            "e2e",
            "検証",
            "確認",
            "試験",
            "テスト",
            "検査",
            "解析",
            "測定",
            "計測",
            "実演",
            "レビュー",
            "ベンチ",
            "スモーク",
            "コマンド",
        ),
    ),
)
_JAPANESE_COMMON_FIELD_ACTIONS = ("定め", "設け", "設定", "規定", "定義", "記載", "用意", "策定", "明示")
_JAPANESE_METHOD_FIELD_ACTIONS = ("実施", "実行", "使用", "採用", "行わ")
_JAPANESE_EVIDENCE_FIELD_ACTIONS = ("保持", "保存", "記録", "作成", "生成", "提出", "取得", "残")
_ENGLISH_COMMON_FIELD_ACTIONS = {
    "available",
    "decide",
    "decided",
    "define",
    "defined",
    "establish",
    "established",
    "exist",
    "present",
    "provide",
    "provided",
    "require",
    "required",
    "set",
    "specify",
    "specified",
}
_ENGLISH_METHOD_FIELD_ACTIONS = {
    "done",
    "execute",
    "executed",
    "perform",
    "performed",
    "run",
    "use",
    "used",
}
_ENGLISH_EVIDENCE_FIELD_ACTIONS = {
    "create",
    "created",
    "keep",
    "kept",
    "record",
    "recorded",
    "retain",
    "retained",
}


def find_field_assertion(text: str, terms: Iterable[str]) -> AssertionMatch | None:
    """Return the strongest deterministic assertion for the supplied field terms.

    A concrete asserted value wins over an explicit absence elsewhere in the
    supplied text. This keeps a later/current specification usable while still
    preventing absence statements, empty labels, and placeholders from
    satisfying an obligation by lexical presence alone.
    """

    matches = _term_matches(text, terms)
    if not matches:
        return None

    classified = [_classify_match(text, term, start, end) for term, start, end in matches]
    for item in classified:
        if item.status == "present":
            return item
    return classified[0]


def asserted_excerpt(text: str, terms: Iterable[str]) -> str:
    match = find_field_assertion(text, terms)
    if match is None or match.status != "present":
        return ""
    return match.excerpt


def _term_matches(text: str, terms: Iterable[str]) -> list[tuple[str, int, int]]:
    found: list[tuple[str, int, int]] = []
    seen_terms: set[str] = set()
    for term in terms:
        normalized = term.strip()
        key = normalized.casefold()
        if not normalized or key in seen_terms:
            continue
        seen_terms.add(key)
        for match in re.finditer(_term_pattern(normalized), text, flags=re.IGNORECASE):
            found.append((normalized, match.start(), match.end()))

    found.sort(key=lambda item: (-(item[2] - item[1]), item[1], item[0].casefold()))
    selected: list[tuple[str, int, int]] = []
    for item in found:
        if any(item[1] < existing[2] and existing[1] < item[2] for existing in selected):
            continue
        selected.append(item)
    return sorted(selected, key=lambda item: (item[1], item[2]))


def _term_pattern(term: str) -> str:
    escaped = re.escape(term)
    if re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_ ./+-]*", term):
        return rf"(?<![A-Za-z0-9_]){escaped}(?![A-Za-z0-9_])"
    return escaped


def _classify_match(text: str, term: str, start: int, end: int) -> AssertionMatch:
    structured = _structured_value(text, term, start, end)
    if structured is not None:
        value, reason = structured
        status: AssertionStatus = "rejected" if reason else "present"
        return _match(text, term, start, end, status, reason or "asserted_field_value")

    before = text[max(0, start - 48):start]
    after = text[end:min(len(text), end + 96)]
    english_action_prefix = _ENGLISH_NEGATED_ACTION_PREFIX.search(before)
    if _ENGLISH_NEGATED_PREFIX.search(before) or _ENGLISH_NEGATED_DETERMINER_PREFIX.search(before):
        return _match(text, term, start, end, "rejected", "explicit_negation")
    if english_action_prefix:
        return _match(text, term, start, end, "rejected", "explicit_negation")
    japanese_negation = _JAPANESE_NEGATED_RELATION.search(after)
    if (
        japanese_negation
        and _japanese_relation_applies(term, japanese_negation.group(0))
        and not _looks_like_japanese_field_content(after[japanese_negation.end():], term)
    ):
        return _match(text, term, start, end, "rejected", "explicit_negation")
    if _ENGLISH_NEGATED_RELATION.search(after):
        return _match(text, term, start, end, "rejected", "explicit_negation")
    return _match(text, term, start, end, "present", "lexical_assertion")


def _structured_value(text: str, term: str, start: int, end: int) -> tuple[str, str] | None:
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", end)
    if line_end < 0:
        line_end = len(text)
    line = text[line_start:line_end]
    relative_start = start - line_start
    relative_end = end - line_start

    tail = line[relative_end:]
    label_separator = re.match(r"^\s*[:：]\s*(.*)$", tail)
    if label_separator:
        value = _first_sentence_value(label_separator.group(1))
        if not value:
            value = _following_structured_value(text, line_end)
        return value, _placeholder_reason(value, term)

    prefix = line[:relative_start]
    markdown_heading = bool(re.match(r"^\s*#{1,6}\s+", prefix))
    normalized_line = re.sub(r"^\s*(?:#{1,6}\s+|[-*]\s+|\d+[.)]\s+)", "", line).strip()
    if markdown_heading and normalized_line.casefold() == term.casefold():
        value = _following_structured_value(text, line_end)
        return value, _placeholder_reason(value, term)

    if normalized_line.casefold() == term.casefold():
        return "", "empty_or_placeholder_value"
    return None


def _first_sentence_value(value: str) -> str:
    boundary = re.search(r"[。！？；;]|[!?](?:\s|$)|\.(?=\s|$)", value)
    if boundary:
        return value[:boundary.start()].strip()
    return value.strip()


def _following_structured_value(text: str, line_end: int) -> str:
    if line_end >= len(text):
        return ""
    for line in text[line_end + 1:].splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            return ""
        if re.match(r"^[^:：]{1,48}[:：]\s*$", stripped):
            return ""
        return re.sub(r"^(?:[-*]\s+|\d+[.)]\s+)", "", stripped).strip()
    return ""


def _placeholder_reason(value: str, term: str) -> str:
    cleaned = value.strip().strip("。.!?！？；;").strip()
    for reason, values in _JAPANESE_EMPTY_VALUES:
        if cleaned in values:
            return reason
    for reason, pattern in _ENGLISH_EMPTY_VALUE_PATTERNS:
        if pattern.fullmatch(cleaned):
            return reason
    if _JAPANESE_DEFERRED_VALUE.fullmatch(cleaned):
        return "deferred_placeholder"
    if _JAPANESE_ABSENCE_VALUE.fullmatch(cleaned):
        return "explicit_absence"
    japanese_negation = _JAPANESE_NEGATED_FIELD_VALUE.fullmatch(cleaned)
    if japanese_negation and _japanese_relation_applies(term, japanese_negation.group(0)):
        return "explicit_negation"
    english_negation = _ENGLISH_NEGATED_FIELD_VALUE.fullmatch(cleaned)
    if english_negation and _english_relation_applies(term, english_negation.group(0)):
        return "explicit_negation"
    return ""


def _looks_like_japanese_field_content(remainder: str, term: str) -> bool:
    cleaned = remainder.strip()
    if not cleaned:
        return False
    if re.match(r"^こと(?:(?:と|に)する)?(?:[。！？!?；;]|$)", cleaned):
        return False
    if re.match(
        r"^[^。！？!?\n；;]{1,48}(?:とする|と定める|を用いる|である)(?:[。！？!?]|$)",
        cleaned,
    ):
        return True

    clause = re.split(r"[。！？!?\n；;]", cleaned, maxsplit=1)[0].strip()
    if not clause or re.search(r"(?:こと|方針|予定|扱い|もの)$", clause):
        return False

    kind = _field_kind(term)
    markers_by_kind = {
        "method": ("試験", "テスト", "検査", "解析", "測定", "計測", "実演", "レビュー", "ベンチ", "コマンド"),
        "evidence": ("証跡", "結果", "ログ", "記録", "成果物", "報告", "一覧", "出力", "画像", "ファイル"),
        "acceptance": ("受入", "合格", "完了", "成功", "達成", "基準", "条件", "閾値", "指標"),
    }
    return any(marker in clause for marker in markers_by_kind.get(kind, ()))


def _field_kind(term: str) -> str:
    normalized = term.casefold()
    for kind, markers in _FIELD_KIND_MARKERS:
        if any(marker.casefold() in normalized for marker in markers):
            return kind
    return "generic"


def _japanese_relation_applies(term: str, phrase: str) -> bool:
    action_stems = _japanese_action_stems(phrase)
    if not action_stems:
        return True
    kind = _field_kind(term)
    allowed = set(_JAPANESE_COMMON_FIELD_ACTIONS)
    if kind in {"method", "generic"}:
        allowed.update(_JAPANESE_METHOD_FIELD_ACTIONS)
    if kind in {"evidence", "generic"}:
        allowed.update(_JAPANESE_EVIDENCE_FIELD_ACTIONS)
    return bool(action_stems & allowed)


def _japanese_action_stems(phrase: str) -> set[str]:
    known = (
        _JAPANESE_COMMON_FIELD_ACTIONS
        + _JAPANESE_METHOD_FIELD_ACTIONS
        + _JAPANESE_EVIDENCE_FIELD_ACTIONS
    )
    return {stem for stem in known if stem in phrase}


def _english_relation_applies(term: str, phrase: str) -> bool:
    normalized = phrase.casefold()
    if re.search(r"\b(?:unavailable|undefined|absent|missing)\b", normalized):
        return True
    actions = {
        action
        for action in _all_english_field_actions()
        if re.search(rf"\b{re.escape(action)}\b", normalized)
    }
    if not actions:
        return True
    allowed = set(_ENGLISH_COMMON_FIELD_ACTIONS)
    kind = _field_kind(term)
    if kind in {"method", "generic"}:
        allowed.update(_ENGLISH_METHOD_FIELD_ACTIONS)
    if kind in {"evidence", "generic"}:
        allowed.update(_ENGLISH_EVIDENCE_FIELD_ACTIONS)
    return bool(actions & allowed)


def _all_english_field_actions() -> set[str]:
    return _ENGLISH_COMMON_FIELD_ACTIONS | _ENGLISH_METHOD_FIELD_ACTIONS | _ENGLISH_EVIDENCE_FIELD_ACTIONS


def _match(
    text: str,
    term: str,
    start: int,
    end: int,
    status: AssertionStatus,
    reason: str,
) -> AssertionMatch:
    return AssertionMatch(
        term=term,
        start=start,
        end=end,
        excerpt=excerpt_around(text, start, end),
        status=status,
        reason=reason,
    )


__all__ = ["AssertionMatch", "AssertionStatus", "asserted_excerpt", "find_field_assertion"]
