"""One definition of "a decision" for every field a detector looks for.

A label is not a decision. The value behind it is classified into a state:

``decided``         a concrete value, or an unlabelled lexical mention
``not_applicable``  the author states the field does not apply (``該当なし``, ``n/a``)
``declared_none``   the author states there is nothing (``なし``, ``none``)
``deferred``        the decision is postponed (``未定``, ``後で決める``, ``TBD``, ``検討中``)
``negated``         the thing is refused (``実施しない``, ``未実施``)
``empty``           nothing was written

Only ``decided`` satisfies an obligation. A field for which "nothing" is a real
answer (non-goals, open questions) opts in with ``accept_none``, which also lets
``not_applicable`` and ``declared_none`` satisfy it. Vocabulary and spelling
(emphasis, table cells, trailing remarks, qualifiers) are absorbed here so that
no detector keeps its own list of placeholder words.
"""

from __future__ import annotations

import re
from bisect import bisect_left
from dataclasses import dataclass, replace
from typing import Iterable, Literal

from semantic_guard_workflow.text_normalization import normalize_audit_text
from semantic_guard_workflow.text_utils import excerpt_around

AssertionStatus = Literal["present", "rejected"]
AssertionState = Literal["decided", "not_applicable", "declared_none", "deferred", "negated", "empty"]

_REASON_STATE: dict[str, AssertionState] = {
    "asserted_field_value": "decided",
    "lexical_assertion": "decided",
    "decided_not_applicable": "not_applicable",
    "explicit_absence": "declared_none",
    "deferred_placeholder": "deferred",
    "explicit_negation": "negated",
    "empty_or_placeholder_value": "empty",
}
# Reasons that an obligation which accepts "nothing" as an answer still counts.
_NONE_REASONS = frozenset({"decided_not_applicable", "explicit_absence"})


@dataclass(frozen=True)
class AssertionMatch:
    term: str
    start: int
    end: int
    excerpt: str
    status: AssertionStatus
    reason: str

    @property
    def state(self) -> AssertionState:
        return _REASON_STATE.get(self.reason, "decided")


_QUALIFIER = (
    r"(?:現在(?:は)?|現時点(?:では)?|現段階(?:では)?|現状(?:では)?|この段階(?:では)?|今のところ(?:は)?|いまのところ(?:は)?"
    r"|目下(?:は)?|当面(?:は)?|今回は|今は|いまは|ここでは|まだ|いまだ(?:に)?|依然(?:として)?|引き続き|一旦|いったん"
    r"|ひとまず|とりあえず|暫定的に(?:は)?|基本的に(?:は)?|なお|やはり)"
)
_QUALIFIERS = rf"(?:{_QUALIFIER}\s*)*"
_DEFERRAL_MARKER = (
    r"(?:未定|未決定|未確定|未策定|未設定|未定義|未記載|未検討|未選定|未指定|未整理|未合意|未承認"
    r"|保留(?:中)?|検討(?:中|予定)|要(?:検討|確認|調整|協議|相談)|(?:調整|確認|協議|選定|準備|作成|策定|設計|相談)中"
    r"|不明|不詳|分からない|わからない|分かりません|わかりません|tbd|tbc|tba|todo|to-do|fixme|wip)"
)
_DEFERRAL_BARE_ADVERB = r"(?:別途|追って|後日|後ほど|のちほど|あとで|後で|いずれ|そのうち)"
_DEFERRAL_NOUN = rf"(?:{_DEFERRAL_MARKER}|{_DEFERRAL_BARE_ADVERB})"
_DEFERRAL_ADVERB = r"(?:後で|あとで|後ほど|のちほど|後日|今後|別途|追って|いずれ|改めて|あらためて|そのうち)"
_DEFERRAL_SURU = (
    r"(?:決定|設定|策定|検討|確認|記載|記入|追記|追加|調整|相談|整理|判断|選定|指定|定義|用意|作成|計画|協議|合意|確定"
    r"|具体化|明確化|設計|実施|実行|対応|連絡|共有|報告|通知|記述|補足|補完|追補|見積)"
)
_DEFERRAL_VERB = (
    r"(?:決め|定め|詰め|考え|見積もり|見積り|選び|書き|書く|決める|定める|詰める|考える|見積もる|選ぶ)"
)
_DEFERRAL_ENDING = (
    r"(?:る|ます|します|する|しておく|しておきます|していく|していきます|したい|したいと思います|いたします|致します"
    r"|し直す|し直します|行う|行います|おく|おきます|いく|いきます)"
    r"(?:予定|つもり|方針|見込み|こととする|ことにする|ことにします)?(?:です|でございます|である)?"
)
# ``後で決める``, ``別途定める予定``, ``今後決定する予定``, ``追って連絡する``.
_DEFERRAL_PHRASE = (
    rf"{_DEFERRAL_ADVERB}\s*(?:{_DEFERRAL_SURU}(?:{_DEFERRAL_ENDING}|予定|する)|{_DEFERRAL_VERB}(?:{_DEFERRAL_ENDING}|予定)?)"
)
_DEFERRAL_TAIL = (
    r"(?:の(?:まま|状態|予定)(?:と(?:する|します))?|です|でございます|である|だ|とする|とします|となっている|になっている"
    r"|となります|になります|の予定|予定|見込み|状態|段階|中|扱い)*"
)
_DEFERRED_VALUE = re.compile(
    rf"^{_QUALIFIERS}(?:{_DEFERRAL_PHRASE}|{_DEFERRAL_NOUN}){_DEFERRAL_TAIL}$",
    re.IGNORECASE,
)
# ``未定のまま進める``, ``未定、担当者が決める``, ``TODO: 追記``: a leading deferral marker
# followed by a clause boundary or a linking form is still a postponement.
_DEFERRED_LEAD = re.compile(
    rf"^{_QUALIFIERS}(?:{_DEFERRAL_PHRASE}|{_DEFERRAL_MARKER})(?:のまま|で(?:あるが|すが)|だが|ですが|でして"
    r"|[、,，:：\-—–])",
    re.IGNORECASE,
)
_ENGLISH_DEFERRED_VALUE = re.compile(
    r"^(?:(?:currently|presently|still|for now|as of now|at this time|at the moment)\s+)?(?:"
    r"tbd|tbc|tba|todo|to-do|fixme|wip|pending|undecided|unresolved|unspecified|undefined|unknown|unclear|later|separately"
    r"|to follow|coming soon|tbd later"
    r"|not (?:yet )?(?:decided|specified|defined|determined|set|confirmed|available|known|clear|settled|finali[sz]ed|planned|started)"
    r"|to be (?:decided|defined|determined|specified|set|confirmed|announced|discussed|added|filled in|written|provided|agreed|selected|chosen|planned)"
    r"|(?:will|shall|to|we will|we'll)\s+(?:be\s+)?(?:decide|decided|define|defined|determine|determined|specify|specified|confirm|confirmed"
    r"|discuss|discussed|add|added|fill|write|written|plan|planned)\s+(?:later|afterwards?|separately|soon)"
    r"|(?:decide|define|determine|specify|confirm|discuss|add|fill in|write|plan)\s+(?:later|afterwards?|separately)"
    r"|(?:under|in)\s+(?:discussion|review|consideration|progress|development|preparation|investigation)"
    r"|needs?\s+(?:to be\s+)?(?:decided|defined|determined|specified|confirmed|discussion|review|investigation|investigating|considering)"
    r"|(?:decision|owner decision|human decision)\s+(?:pending|needed|required)"
    r"|pending\s+(?:owner|human|stakeholder|team|management)?\s*(?:decision|input|review|approval|confirmation)?"
    r"|awaiting\s+(?:decision|input|review|approval|confirmation)"
    r")\.?$",
    re.IGNORECASE,
)
_EMPTY_WORDS = frozenset({"未記入", "空欄", "空白", "空", "記入なし", "blank", "empty", "null", "nil", "undefined value"})
_NOT_APPLICABLE_VALUE = re.compile(
    rf"^{_QUALIFIERS}(?:該当(?:事項|項目|箇所)?(?:は)?(?:なし|無し|ありません|ない|しない|せず)|非該当|対象外|対象なし|対象無し|適用外"
    r"|適用(?:なし|無し|しない)|n\s*/\s*a|n\.\s*a\.?|not\s+applicable|inapplicable|not\s+relevant)"
    r"(?:です|である|だ|とする|とします)?$",
    re.IGNORECASE,
)
_JAPANESE_ABSENCE_VALUE = re.compile(
    rf"^{_QUALIFIERS}(?:特に\s*)?(?:なし|無し|無|不要|必要(?:なし|無し|ありません|ない)|存在しない|ありません|ございません|ない)"
    r"(?:です|である|だ|とする|とします)?$"
)
_ENGLISH_ABSENCE_VALUE = re.compile(
    r"^(?:none|nothing|nil|no|not required|no need|not needed|absent|missing|not available|not defined)\.?$",
    re.IGNORECASE,
)
_JAPANESE_NEGATED_STATE = re.compile(
    rf"^{_QUALIFIERS}(?:未実施|未実行|未対応|未確認|未検証|未試験|未取得|不実施|実施見送り|見送り|見送る|見送ります|省略|省略する|省略します"
    r"|スキップ(?:する|します|済み)?|対応しない|対応しません|検証しない|確認しない|試験しない|行わず|実施せず|実行せず)"
    r"(?:です|である|だ|とする|とします)?$"
)
_ENGLISH_NEGATED_STATE = re.compile(
    r"^(?:skipped|skipping|skip|not run|not done|not executed|not performed|not tested|not verified|won't do|wont fix|will not fix|no action)\.?$",
    re.IGNORECASE,
)
_JAPANESE_NEGATED_FIELD_VALUE = re.compile(
    r"^(?:(?:現在(?:は)?|現時点(?:では)?|今のところ(?:は)?|まだ|当面(?:は)?|今回は)\s*)?"
    r"(?:"
    r"(?:定め|設け)(?:ない|ません|ず|ぬ)"
    r"|(?:設定|規定|定義|記載|用意|策定|明示|実施|実行|使用|採用|保持|保存|記録|作成|生成|提出|取得)"
    r"(?:しない|しません|せず|していない|していません|されていない|されていません)"
    r"|残(?:さない|しません|さず|していない|していません)"
    r"|行(?:わ(?:ない|ず)|いません)"
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
    r"|行(?:わ(?:ない|ず)|いません)"
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


def find_field_assertion(text: str, terms: Iterable[str], *, accept_none: bool = False) -> AssertionMatch | None:
    """Return the strongest deterministic assertion for the supplied field terms.

    A concrete asserted value wins over an absence, a deferral or a negation
    elsewhere in the supplied text. Empty labels, placeholders, negations and
    statements of "nothing" never satisfy an obligation by lexical presence
    alone. ``accept_none`` is for fields where "nothing" is itself an answer
    (non-goals, open questions): ``なし`` and ``該当なし`` then count as a
    decision, while a deferral, a negation and an empty value still do not.
    """

    matches = _term_matches(text, terms)
    if not matches:
        return None

    # Classify in reading order and stop at the first decision: only the chosen
    # match needs an excerpt, and a text with many mentions stays linear.
    first: tuple[str, int, int, AssertionStatus, str] | None = None
    for term, start, end in matches:
        status, reason = _classify(text, term, start, end)
        if accept_none and reason in _NONE_REASONS:
            status = "present"
        if status == "present":
            return _match(text, term, start, end, status, reason)
        if first is None:
            first = (term, start, end, status, reason)
    return _match(text, *first) if first is not None else None


def asserted_excerpt(text: str, terms: Iterable[str], *, accept_none: bool = False) -> str:
    match = find_field_assertion(text, terms, accept_none=accept_none)
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

    # Longest match first; a shorter one that overlaps a kept match is dropped.
    # Kept matches are disjoint, so only the neighbours of the insertion point
    # can overlap.
    found.sort(key=lambda item: (-(item[2] - item[1]), item[1], item[0].casefold()))
    selected: list[tuple[str, int, int]] = []
    starts: list[int] = []
    for item in found:
        position = bisect_left(starts, item[1])
        if position > 0 and selected[position - 1][2] > item[1]:
            continue
        if position < len(selected) and selected[position][1] < item[2]:
            continue
        starts.insert(position, item[1])
        selected.insert(position, item)
    return selected


def _term_pattern(term: str) -> str:
    escaped = re.escape(term)
    if re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_ ./+-]*", term):
        return rf"(?<![A-Za-z0-9_]){escaped}(?![A-Za-z0-9_])"
    return escaped


_WINDOW_BEFORE = 120
_WINDOW_AFTER = 320
_FOLLOWING_LINES = 40
_DECORATION = r"[\s*_`~=]*"
_LABEL_SEPARATOR = re.compile(rf"^{_DECORATION}[:：＝=]\s*(?P<value>.*)$")
# The term is the beginning of a longer label: ``検証`` in ``検証結果: 未定``.
_COMPOUND_LABEL = re.compile(r"^[^\s:：＝=。、,，.|*`]{1,10}" + _DECORATION + r"[:：＝=]\s*(?P<value>.*)$")
_TABLE_CELL = re.compile(r"^[^\s|:：]{0,10}\s*\|(?P<value>[^|]*)(?:\||$)")
_COPULA = re.compile(r"^\s*(?:については|には|では|は|が|も|を)\s*[、,，]?\s*(?P<value>[^。！？!?；;\n]{1,80})")
_ENGLISH_COPULA = re.compile(
    r"^\s*(?:is|are|was|were|remains?|stays?|will be|shall be|status(?:\s+is)?|currently|for now)\s+(?P<value>[^.;!?\n]{1,80})",
    re.IGNORECASE,
)


# ``未定`` opens ``未定義の挙動`` and ``なし`` opens ``なしとする``: a negation word only
# counts when the word ends there.
_NEGATION_COMPLETE = re.compile(
    r"^(?:$|[\s、,，。.！!？?；;]|が|けれど|けど|ため|ので|から|です|ます|ませ|のため|のまま|とする|と考える|方針|こと|ものとする|である|だ)"
)


def _classify(text: str, term: str, start: int, end: int) -> tuple[AssertionStatus, str]:
    structured = _structured_value(text, term, start, end)
    if structured is not None:
        value, reason = structured
        return ("rejected" if reason else "present"), (reason or "asserted_field_value")

    before = text[max(0, start - 48):start]
    after = text[end:min(len(text), end + 96)]
    english_action_prefix = _ENGLISH_NEGATED_ACTION_PREFIX.search(before)
    if _ENGLISH_NEGATED_PREFIX.search(before) or _ENGLISH_NEGATED_DETERMINER_PREFIX.search(before):
        return "rejected", "explicit_negation"
    if english_action_prefix:
        return "rejected", "explicit_negation"
    for copula in (_COPULA, _ENGLISH_COPULA):
        stated = copula.match(after)
        if stated is not None:
            reason = _placeholder_reason(stated.group("value"), term)
            if reason:
                return "rejected", reason
    japanese_negation = _JAPANESE_NEGATED_RELATION.search(after)
    if (
        japanese_negation
        and _NEGATION_COMPLETE.match(after[japanese_negation.end():])
        and _japanese_relation_applies(term, japanese_negation.group(0))
        and not _looks_like_japanese_field_content(after[japanese_negation.end():], term)
    ):
        return "rejected", "explicit_negation"
    if _ENGLISH_NEGATED_RELATION.search(after):
        return "rejected", "explicit_negation"
    return "present", "lexical_assertion"


def _structured_value(text: str, term: str, start: int, end: int) -> tuple[str, str] | None:
    # Look at a bounded window around the mention so that a very long line with
    # many mentions costs the same per mention as a short one.
    window_start = max(0, start - _WINDOW_BEFORE)
    newline = text.rfind("\n", window_start, start)
    line_start = newline + 1 if newline >= 0 else window_start
    window_end = min(len(text), end + _WINDOW_AFTER)
    line_end = text.find("\n", end, window_end)
    cut_short = line_end < 0 and window_end < len(text)
    if line_end < 0:
        line_end = window_end
    line = text[line_start:line_end]
    relative_start = start - line_start
    relative_end = end - line_start

    tail = line[relative_end:]
    prefix = line[:relative_start]
    label = _LABEL_SEPARATOR.match(tail) or _COMPOUND_LABEL.match(tail)
    if label is not None:
        value = _first_sentence_value(label.group("value"))
        if not _has_content(value) and not cut_short:
            value = _following_structured_value(text, line_end)
        return value, _placeholder_reason(value, term)

    # Table row: ``| 検証 | 未定 |``. The term must open its cell.
    if "|" in prefix:
        cell = _TABLE_CELL.match(tail)
        if cell is not None and prefix.strip().strip("|").strip("*_` ") == "":
            value = cell.group("value")
            return value, _placeholder_reason(value, term)

    markdown_heading = bool(re.match(r"^\s*#{1,6}\s+", prefix))
    normalized_line = re.sub(r"^\s*(?:>\s*)*(?:#{1,6}\s+|[-*]\s+|\d+[.)]\s+)", "", line).strip().strip("*_`~ ")
    if markdown_heading and normalized_line.casefold() == term.casefold() and not cut_short:
        value = _following_structured_value(text, line_end)
        return value, _placeholder_reason(value, term)

    if normalized_line.casefold() == term.casefold():
        return "", "empty_or_placeholder_value"
    return None


def _has_content(value: str) -> bool:
    return bool(re.search(r"\w", re.sub(r"[*_`~=|]", "", value)))


def _first_sentence_value(value: str) -> str:
    boundary = re.search(r"[。！？；;]|[!?](?:\s|$)|\.(?=\s|$)", value)
    if boundary:
        return value[:boundary.start()].strip()
    return value.strip()


def _following_structured_value(text: str, line_end: int) -> str:
    position = line_end + 1
    for _ in range(_FOLLOWING_LINES):
        if position >= len(text):
            return ""
        newline = text.find("\n", position, position + _WINDOW_AFTER)
        end = newline if newline >= 0 else min(len(text), position + _WINDOW_AFTER)
        stripped = text[position:end].strip()
        position = end + 1
        if not stripped:
            continue
        if stripped.startswith("#"):
            return ""
        if re.match(r"^[^:：]{1,48}[:：]\s*$", stripped):
            return ""
        return re.sub(r"^(?:>\s*)*(?:[-*]\s+|\d+[.)]\s+)", "", stripped).strip()
    return ""


_EMPHASIS = re.compile(r"\*+|~~|`+|==|__")
_TRAILING_REMARK = re.compile(r"[（(\[【][^（()）\[\]【】]*[）)\]】]$")
_WRAPPING_BRACKETS = re.compile(r"^[（(\[【「『](?P<inner>[^（()）\[\]【】「」『』]*)[）)\]】」』]$")
_VALUE_SEPARATOR = re.compile(r"\s*[/／、,，・&＆]\s*|\s+(?:or|and)\s+|\s*(?:または|又は|及び|かつ)\s*", re.IGNORECASE)


def _clean_value(value: str) -> str:
    # Collapse whitespace first: every pattern below can then rescan a run of
    # spaces at most once, so the cost stays linear in the length of the value.
    cleaned = re.sub(r"\s+", " ", normalize_audit_text(value))
    cleaned = re.sub(r"<[^<>\n]{1,20}>", "", cleaned)
    cleaned = re.sub(r"^\s*(?:>\s*)+", "", cleaned)
    cleaned = re.sub(r"^\s*(?:[-*+]\s+|\d+[.)]\s+|#{1,6}\s+)", "", cleaned)
    cleaned = _EMPHASIS.sub("", cleaned).strip().strip("_").strip().strip("|").strip()
    for _ in range(3):
        wrapped = _WRAPPING_BRACKETS.match(cleaned)
        if wrapped is not None:
            cleaned = wrapped.group("inner").strip()
            continue
        remark = _TRAILING_REMARK.search(cleaned)
        if remark is not None and cleaned[:remark.start()].strip():
            cleaned = cleaned[:remark.start()].strip()
            continue
        break
    return cleaned.strip().strip("。.!?！？；;、,，…・:：-—–~ \t")


def _placeholder_reason(value: str, term: str) -> str:
    """The reason ``value`` is not a decision, or ``""`` when it is one."""
    cleaned = _clean_value(value)
    if not re.search(r"\w", cleaned):
        return "empty_or_placeholder_value"
    parts = [part for part in _VALUE_SEPARATOR.split(cleaned) if part.strip()]
    if len(parts) > 1:
        reasons = [_single_placeholder_reason(part.strip(), term) for part in parts]
        if all(reasons):
            return reasons[0]
    return _single_placeholder_reason(cleaned, term)


def _single_placeholder_reason(cleaned: str, term: str) -> str:
    folded = cleaned.casefold()
    if folded in _EMPTY_WORDS:
        return "empty_or_placeholder_value"
    if (
        _DEFERRED_VALUE.fullmatch(cleaned)
        or _ENGLISH_DEFERRED_VALUE.fullmatch(cleaned)
        or _DEFERRED_LEAD.match(cleaned)
    ):
        return "deferred_placeholder"
    if _NOT_APPLICABLE_VALUE.fullmatch(cleaned):
        return "decided_not_applicable"
    if _JAPANESE_ABSENCE_VALUE.fullmatch(cleaned) or _ENGLISH_ABSENCE_VALUE.fullmatch(cleaned):
        return "explicit_absence"
    if _JAPANESE_NEGATED_STATE.fullmatch(cleaned) or _ENGLISH_NEGATED_STATE.fullmatch(cleaned):
        return "explicit_negation"
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


__all__ = ["AssertionMatch", "AssertionState", "AssertionStatus", "asserted_excerpt", "find_field_assertion"]
