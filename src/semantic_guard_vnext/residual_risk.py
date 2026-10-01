from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable

from .records import ParsedField, ParsedRequirementRecord


@dataclass(frozen=True, slots=True)
class ResidualRiskSignal:
    signal_id: str
    reason_code: str
    category: str
    field_name: str
    start: int
    end: int
    excerpt: str
    detected_by: str
    next_route: str
    limitations: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class _SignalRule:
    reason_code: str
    category: str
    pattern: re.Pattern[str]
    next_route: str
    limitations: tuple[str, ...] = ()


def _compiled(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern, re.IGNORECASE)


RULES: tuple[_SignalRule, ...] = (
    _SignalRule(
        "reported_speech_present",
        "discourse_scope",
        _compiled(
            r"(?:担当者|利用者|文書|仕様書).{0,16}(?:によれば|によると|と述べ|と報告|曰く)"
            r"|(?:曰く|とのこと(?:だ|である)?|とされる|と聞く)"
            r"|according\s+to|reportedly"
        ),
        "morphology",
    ),
    _SignalRule(
        "metalinguistic_or_quotation_present",
        "discourse_scope",
        _compiled(
            r"[「『“\"【〔〈《]|(?:と書かれている|という記載|と記載され|文言(?:である|だ|にすぎ)|wording|quoted)"
        ),
        "morphology",
        ("A quotation cue does not by itself prove that the content is non-binding.",),
    ),
    _SignalRule(
        "non_adoption_or_proposal_present",
        "modality_scope",
        _compiled(
            r"(?:採用していない|未採用|採用案|提案に留まる|検討中|予定である|推奨する"
            r"|草案|案文|たたき台|文言にすぎ(?:ない|ぬ)|暫定(?:案|的)?|仮(?:案|置き|定)"
            r"|should\s+consider|proposal|not\s+adopted)"
        ),
        "morphology",
    ),
    _SignalRule(
        "historical_or_retired_scope_present",
        "temporal_scope",
        _compiled(r"(?:旧版|以前は|過去には|廃止済み|削除済み|retired|deprecated|previous(?:ly)?)"),
        "morphology",
    ),
    _SignalRule(
        "negation_scope_present",
        "polarity_scope",
        _compiled(
            r"(?:しない|ではない|定めない|存在しない|できない|禁止する"
            r"|認め(?:ない|ぬ|ず|ません|まい)|(?:ない|ぬ|ず|ません|まい)(?=[\s。、，,；;）」』】〕〉》]|$)"
            r"|not\b|never\b|without\b)"
        ),
        "morphology",
        (
            "A negative requirement may be valid; this signal requests scope analysis and is not a defect assertion.",
        ),
    ),
    _SignalRule(
        "conditional_or_exception_scope_present",
        "conditional_scope",
        _compiled(
            r"(?:場合(?:に限り|だけ|のみ|は|に|、|，|$)|"
            r"(?:[一-龥ぁ-んァ-ヶA-Za-z0-9_]+)?(?:時|際)(?:だけ|のみ|は|に|、|，|$)"
            r"|なら(?:ば)?|たら|れば|を除き|ただし|に限り|だけ"
            r"|unless\b|except\b|only\s+if\b|when\b|if\b)"
        ),
        "dependency_parse",
        ("Conditions are often legitimate and require attachment analysis rather than automatic rejection.",),
    ),
    _SignalRule(
        "modal_uncertainty_present",
        "modality_scope",
        _compiled(r"(?:かもしれない|可能性がある|できれば|望ましい|may\b|might\b|possibly\b|preferably\b)"),
        "morphology",
    ),
    _SignalRule(
        "multiple_propositions_present",
        "record_boundary",
        _compiled(r"[。；;].+|(?:かつ|且つ|ならびに|並びに|および|及び|または|又は)"),
        "dependency_parse",
        ("Multiple propositions can be valid but must not be silently merged into one relation.",),
    ),
)


def _field_signals(field: ParsedField) -> Iterable[ResidualRiskSignal]:
    for rule in RULES:
        for match_index, match in enumerate(rule.pattern.finditer(field.value), start=1):
            absolute_start = field.value_start + match.start()
            absolute_end = field.value_start + match.end()
            yield ResidualRiskSignal(
                signal_id=f"signal.{field.name}.{rule.reason_code}.{absolute_start}.{match_index}",
                reason_code=rule.reason_code,
                category=rule.category,
                field_name=field.name,
                start=absolute_start,
                end=absolute_end,
                excerpt=field.value[match.start() : match.end()],
                detected_by=f"residual-risk.{rule.reason_code}/v0",
                next_route=rule.next_route,
                limitations=rule.limitations,
            )


def scan_residual_risks(record: ParsedRequirementRecord) -> tuple[ResidualRiskSignal, ...]:
    """Run an independent challenge-oriented scan over every parsed field.

    The result may request a hold, but it cannot establish obligation support
    and cannot release a prior hold.
    """

    signals: list[ResidualRiskSignal] = []
    for values in record.fields.values():
        for field in values:
            signals.extend(_field_signals(field))

    for index, (start, end) in enumerate(record.unconsumed_spans, start=1):
        signals.append(
            ResidualRiskSignal(
                signal_id=f"signal.record.unconsumed_span.{start}.{index}",
                reason_code="unconsumed_relevant_span",
                category="record_boundary",
                field_name="record",
                start=start,
                end=end,
                excerpt=record.source_text[start:end],
                detected_by="residual-risk.unconsumed-span/v0",
                next_route="record_segmentation",
                limitations=("Relevance has not yet been semantically classified.",),
            )
        )

    if record.record_count != 1:
        signals.append(
            ResidualRiskSignal(
                signal_id="signal.record.multiple_records",
                reason_code="record_boundary_not_single",
                category="record_boundary",
                field_name="record",
                start=0,
                end=len(record.source_text),
                excerpt=record.source_text[:160],
                detected_by="residual-risk.record-count/v0",
                next_route="record_segmentation",
            )
        )

    unique: dict[tuple[str, str, int, int], ResidualRiskSignal] = {}
    for signal in signals:
        unique[(signal.reason_code, signal.field_name, signal.start, signal.end)] = signal
    return tuple(sorted(unique.values(), key=lambda item: (item.start, item.end, item.reason_code)))
