from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal, Mapping, Protocol, Sequence, runtime_checkable

from semantic_guard_workflow.assertion_context import find_field_assertion


SEMANTIC_ASSERTION_IR_VERSION = "semantic-assertion-ir/v0"

EntityKind = Literal[
    "requirement",
    "scenario_actor",
    "behavior",
    "object",
    "condition",
    "observable_result",
    "acceptance_criterion",
    "metric",
    "verification_method",
    "evidence_artifact",
    "unknown",
]
SemanticState = Literal["asserted", "candidate", "rejected", "unknown", "conflict"]
DiscourseScope = Literal["binding", "quoted", "example", "reported", "metalinguistic", "unknown"]
TemporalScope = Literal["current", "future", "historical", "unknown"]
SemanticAuthority = Literal["assertion_capable", "candidate_only", "signal_only"]
SupportTier = Literal[
    "caller_structure",
    "structured_field",
    "direct_rule",
    "dependency_parse",
    "morphology",
    "llm",
]


@runtime_checkable
class MorphologyProvider(Protocol):
    def analyze(self, text: str) -> Mapping[str, Any]: ...


@runtime_checkable
class DependencyProvider(Protocol):
    def analyze(self, text: str) -> Mapping[str, Any] | Sequence[Mapping[str, Any]]: ...


@dataclass(frozen=True)
class SourceSegment:
    id: str
    field: str
    text: str
    start: int
    end: int
    structure: str
    discourse_scope: DiscourseScope
    temporal_scope: TemporalScope
    state: SemanticState
    confidence: str
    authority: SemanticAuthority

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "field": self.field,
            "text": self.text,
            "start": self.start,
            "end": self.end,
            "structure": self.structure,
            "discourse_scope": self.discourse_scope,
            "temporal_scope": self.temporal_scope,
            "state": self.state,
            "confidence": self.confidence,
            "authority": self.authority,
        }


@dataclass(frozen=True)
class SemanticSupport:
    id: str
    tier: SupportTier
    source_segment_id: str
    start: int
    end: int
    authority: SemanticAuthority
    detail: str = ""
    metadata: Mapping[str, object] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "tier": self.tier,
            "source_segment_id": self.source_segment_id,
            "start": self.start,
            "end": self.end,
            "authority": self.authority,
            "detail": self.detail,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class SemanticEntity:
    id: str
    kind: EntityKind
    text: str
    normalized: str
    source_segment_id: str
    start: int
    end: int
    state: SemanticState
    discourse_scope: DiscourseScope
    temporal_scope: TemporalScope
    authority: SemanticAuthority
    support_ids: tuple[str, ...]
    attributes: Mapping[str, object] = field(default_factory=dict)
    confidence: str = "unknown"

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "kind": self.kind,
            "text": self.text,
            "normalized": self.normalized,
            "source_segment_id": self.source_segment_id,
            "start": self.start,
            "end": self.end,
            "state": self.state,
            "discourse_scope": self.discourse_scope,
            "temporal_scope": self.temporal_scope,
            "authority": self.authority,
            "support_ids": list(self.support_ids),
            "attributes": dict(self.attributes),
            "confidence": self.confidence,
        }


@dataclass(frozen=True)
class SemanticAssertion:
    id: str
    kind: str
    subject_id: str
    object_id: str
    text: str
    polarity: Literal["positive", "negative", "unknown"]
    state: SemanticState
    discourse_scope: DiscourseScope
    temporal_scope: TemporalScope
    authority: SemanticAuthority
    source_segment_id: str
    start: int
    end: int
    support_ids: tuple[str, ...]
    attributes: Mapping[str, object] = field(default_factory=dict)
    confidence: str = "unknown"

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "kind": self.kind,
            "subject_id": self.subject_id,
            "object_id": self.object_id,
            "text": self.text,
            "polarity": self.polarity,
            "state": self.state,
            "discourse_scope": self.discourse_scope,
            "temporal_scope": self.temporal_scope,
            "authority": self.authority,
            "source_segment_id": self.source_segment_id,
            "start": self.start,
            "end": self.end,
            "support_ids": list(self.support_ids),
            "attributes": dict(self.attributes),
            "confidence": self.confidence,
        }


@dataclass(frozen=True)
class SemanticRelation:
    id: str
    kind: str
    from_id: str
    to_id: str
    state: SemanticState
    discourse_scope: DiscourseScope
    temporal_scope: TemporalScope
    authority: SemanticAuthority
    support_ids: tuple[str, ...]
    attributes: Mapping[str, object] = field(default_factory=dict)
    confidence: str = "unknown"

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "kind": self.kind,
            "from_id": self.from_id,
            "to_id": self.to_id,
            "state": self.state,
            "discourse_scope": self.discourse_scope,
            "temporal_scope": self.temporal_scope,
            "authority": self.authority,
            "support_ids": list(self.support_ids),
            "attributes": dict(self.attributes),
            "confidence": self.confidence,
        }


@dataclass(frozen=True)
class ExtractionAttempt:
    stage: str
    status: Literal["executed", "unavailable", "not_configured", "failed", "skipped"]
    authority: SemanticAuthority
    provider_id: str = ""
    provider_version: str = ""
    resource_version: str = ""
    split_mode: str = ""
    produced_ids: tuple[str, ...] = ()
    diagnostics: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {
            "stage": self.stage,
            "status": self.status,
            "authority": self.authority,
            "provider_id": self.provider_id,
            "provider_version": self.provider_version,
            "resource_version": self.resource_version,
            "split_mode": self.split_mode,
            "produced_ids": list(self.produced_ids),
            "diagnostics": list(self.diagnostics),
        }


@dataclass(frozen=True)
class SemanticAssertionIR:
    text: str
    context: str
    source_text: str
    source_segments: tuple[SourceSegment, ...]
    entities: tuple[SemanticEntity, ...]
    assertions: tuple[SemanticAssertion, ...]
    relations: tuple[SemanticRelation, ...]
    supports: tuple[SemanticSupport, ...]
    attempts: tuple[ExtractionAttempt, ...]
    diagnostics: tuple[str, ...]
    coverage: Mapping[str, object]
    metadata: Mapping[str, object]
    schema_version: str = SEMANTIC_ASSERTION_IR_VERSION

    @property
    def segments(self) -> tuple[SourceSegment, ...]:
        return self.source_segments

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "text": self.text,
            "context": self.context,
            "source_text": self.source_text,
            "source_segments": [item.as_dict() for item in self.source_segments],
            "entities": [item.as_dict() for item in self.entities],
            "assertions": [item.as_dict() for item in self.assertions],
            "relations": [item.as_dict() for item in self.relations],
            "supports": [item.as_dict() for item in self.supports],
            "attempts": [item.as_dict() for item in self.attempts],
            "diagnostics": list(self.diagnostics),
            "coverage": dict(self.coverage),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class _FieldSpec:
    field: str
    entity_kind: EntityKind
    assertion_kind: str
    labels: tuple[str, ...]


_FIELD_SPECS = (
    _FieldSpec("purpose", "behavior", "purpose", ("Purpose", "目的")),
    _FieldSpec("user", "scenario_actor", "scenario_actor", ("User", "利用者")),
    _FieldSpec("scenario", "condition", "scenario", ("Scenario", "シナリオ", "前提")),
    _FieldSpec("expected_result", "observable_result", "expected_result", ("Expected result", "期待結果")),
    _FieldSpec("acceptance_criteria", "acceptance_criterion", "acceptance_criterion", ("Acceptance criteria", "受入基準")),
    _FieldSpec("verification_method", "verification_method", "verification_method", ("Verification method", "検証方法")),
    _FieldSpec("evidence", "evidence_artifact", "evidence_artifact", ("Evidence", "証拠")),
)
_LABEL_TO_SPEC = {label.casefold(): spec for spec in _FIELD_SPECS for label in spec.labels}
_LABELS = tuple(sorted((label for spec in _FIELD_SPECS for label in spec.labels), key=len, reverse=True))
_LABEL_PATTERN = "|".join(re.escape(label) for label in _LABELS)
_STRUCTURED_FIELD_RE = re.compile(
    rf"(?<![0-9A-Za-z_一-龥ぁ-んァ-ヶ])(?P<label>{_LABEL_PATTERN})(?:\s*\*\*)?\s*[:：]\s*",
    re.IGNORECASE,
)
_BOUNDARY_FIELD_RE = re.compile(
    rf"(?<![0-9A-Za-z_一-龥ぁ-んァ-ヶ])(?:{_LABEL_PATTERN}|不合格条件|対象外|未確定|"
    r"利害関係者|優先度|入力条件|問題|原因|解決策|成果物|非目標|非要求)"
    r"(?:\s*\*\*)?\s*[:：]\s*",
    re.IGNORECASE,
)
_DIRECT_LABEL_RE = re.compile(
    rf"(?<![0-9A-Za-z_一-龥ぁ-んァ-ヶ])(?P<label>{_LABEL_PATTERN})(?![0-9A-Za-z_])",
    re.IGNORECASE,
)
_DIRECT_LINE_RE = re.compile(
    rf"^\s*(?:[-*+]\s*)?[「\"]?(?P<label>{_LABEL_PATTERN})(?![0-9A-Za-z_])",
    re.IGNORECASE,
)
_META_RE = re.compile(r"という(?:語|単語|表現)|と(?:いう|呼ぶ)\s*(?:term|word)|\b(?:term|word)\b", re.IGNORECASE)
_EXAMPLE_RE = re.compile(
    r"(?:例\s*(?:[:：]|として)|例示|一例|サンプル|\bexample\b|\be\.g\.)",
    re.IGNORECASE,
)
_HISTORICAL_RE = re.compile(r"(?:旧版|旧バージョン|以前|過去|従来|かつて|\bprevious(?: version)?\b|\bformer(?:ly)?\b|\bhistorical\b)", re.IGNORECASE)
_CONDITIONAL_RE = re.compile(
    r"(?:採用する場合|採用した場合|採用案|提案(?:では|として|:|：)|候補(?:では|として|:|：)|"
    r"\bif\b.{0,48}\badopt(?:ed)?\b|\bproposed\b|\bcandidate\b)",
    re.IGNORECASE,
)
_NEGATIVE_RE = re.compile(
    r"(?:しない|さない|れない|られない|できない|行わない|存在しない|しません|せず|さず|"
    r"禁止(?:する|される|とする)|除外(?:する|される|とする)|無し|なし|"
    r"\bnot\b|\bno\b|\bwithout\b|n't\b)",
    re.IGNORECASE,
)
_RETIRED_FIELD_VALUE_RE = re.compile(
    r"(?:削除|中止|廃止|撤回|停止)(?:する|した|済み|されている|された|中である)|"
    r"\b(?:remove|delete|cancel|retire|withdraw|stop|deprecat)(?:d|s|ed|ing)?\b",
    re.IGNORECASE,
)
_PROPOSED_FIELD_VALUE_RE = re.compile(
    r"(?:推奨|提案|検討|候補|予定)(?:する|した|中|である|とする)?|"
    r"\b(?:recommend|propos|consider|candidate|planned)(?:s|ed|ing)?\b",
    re.IGNORECASE,
)
_REQ_ID_RE = re.compile(r"(?:^|\n)\s*(?:#{1,6}\s*)?(?:REQ-[A-Za-z0-9_.-]+|要求\s*ID\s*[:：]\s*\S+)", re.IGNORECASE)
_SENTENCE_END_RE = re.compile(r"。|(?<!e\.g)(?<!i\.e)\.(?=\s|$)", re.IGNORECASE)


def _scope_for(line: str, label_start: int) -> tuple[DiscourseScope, TemporalScope, SemanticAuthority]:
    if _META_RE.search(line):
        return "metalinguistic", "current", "candidate_only"
    if _EXAMPLE_RE.search(line):
        return "example", "unknown", "candidate_only"
    if _HISTORICAL_RE.search(line):
        return "reported", "historical", "candidate_only"
    if _CONDITIONAL_RE.search(line):
        return "binding", "future", "candidate_only"
    before = line[:label_start]
    if before.rfind("「") > before.rfind("」") or before.count('"') % 2 == 1:
        return "quoted", "unknown", "candidate_only"
    return "binding", "current", "assertion_capable"


def _direct_has_predicate(line: str, match: re.Match[str]) -> bool:
    """Require more than a bag of field names before a direct rule can assert."""

    residue = _DIRECT_LABEL_RE.sub("", line)
    if not re.search(r"[0-9A-Za-z一-龥ぁ-んァ-ヶ]", residue):
        return False
    after = line[match.end("label") :]
    before = line[: match.start("label")]
    if re.match(r"^\s*(?:は|が|を|も|については|には|では)", after):
        return True
    if re.match(
        r"^\s*(?:is|are|was|were|has|have|had|will|shall|must|should|can|could|does|do|did|remains?)\b",
        after,
        re.IGNORECASE,
    ):
        return True
    return bool(
        re.search(
            r"(?:定め|設定|定義|記載|用意|実施|実行|保存|記録|残さ|define|specify|provide|retain|record)\S*\s*$",
            before,
            re.IGNORECASE,
        )
    )


def _trim_value(text: str, start: int, end: int, *, quoted: bool) -> tuple[int, int]:
    if quoted:
        close_positions = [position for mark in ("」", '"') if (position := text.find(mark, start, end)) >= 0]
        if close_positions:
            end = min(close_positions)
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return start, end


def _classify_value(label: str, value: str, discourse: DiscourseScope, temporal: TemporalScope) -> tuple[SemanticState, SemanticAuthority, str]:
    if discourse != "binding" or temporal != "current":
        return "candidate", "candidate_only", "medium"
    if _RETIRED_FIELD_VALUE_RE.search(value):
        return "rejected", "signal_only", "high"
    if _PROPOSED_FIELD_VALUE_RE.search(value):
        return "candidate", "candidate_only", "medium"
    match = find_field_assertion(f"{label}: {value}", [label])
    if match is None or match.status == "rejected":
        return "rejected", "signal_only", "high"
    return "asserted", "assertion_capable", "high"


def _combine_state(*states: SemanticState) -> SemanticState:
    if "conflict" in states:
        return "conflict"
    if "rejected" in states:
        return "rejected"
    if "unknown" in states:
        return "unknown"
    if "candidate" in states:
        return "candidate"
    return "asserted"


def _authority_for_state(state: SemanticState) -> SemanticAuthority:
    if state == "asserted":
        return "assertion_capable"
    if state in {"candidate", "conflict"}:
        return "candidate_only"
    return "signal_only"


class _Builder:
    def __init__(self, text: str, context: str) -> None:
        self.text = text
        self.context = context
        self.segments: list[SourceSegment] = []
        self.entities: list[SemanticEntity] = []
        self.assertions: list[SemanticAssertion] = []
        self.relations: list[SemanticRelation] = []
        self.supports: list[SemanticSupport] = []
        self.attempts: list[ExtractionAttempt] = []
        self.diagnostics: list[str] = []
        self.unresolved_spans: list[dict[str, object]] = []
        self._counts: dict[str, int] = {}

    def new_id(self, prefix: str) -> str:
        self._counts[prefix] = self._counts.get(prefix, 0) + 1
        return f"{prefix}:{self._counts[prefix]}"

    def add_segment(
        self,
        *,
        field_name: str,
        start: int,
        end: int,
        structure: str,
        discourse: DiscourseScope,
        temporal: TemporalScope,
        state: SemanticState,
        confidence: str,
        authority: SemanticAuthority,
    ) -> SourceSegment:
        segment = SourceSegment(
            id=self.new_id("segment"),
            field=field_name,
            text=self.text[start:end],
            start=start,
            end=end,
            structure=structure,
            discourse_scope=discourse,
            temporal_scope=temporal,
            state=state,
            confidence=confidence,
            authority=authority,
        )
        self.segments.append(segment)
        return segment

    def add_support(
        self,
        tier: SupportTier,
        segment: SourceSegment,
        authority: SemanticAuthority,
        detail: str,
        metadata: Mapping[str, object] | None = None,
    ) -> SemanticSupport:
        support = SemanticSupport(
            id=self.new_id("support"),
            tier=tier,
            source_segment_id=segment.id,
            start=segment.start,
            end=segment.end,
            authority=authority,
            detail=detail,
            metadata=metadata or {},
        )
        self.supports.append(support)
        return support

    def add_field_entity(
        self,
        spec: _FieldSpec,
        segment: SourceSegment,
        support: SemanticSupport,
        state: SemanticState,
        authority: SemanticAuthority,
        confidence: str,
        *,
        source: str,
        extra_attributes: Mapping[str, object] | None = None,
    ) -> SemanticEntity:
        attributes = {"field": spec.field, "source": source, **dict(extra_attributes or {})}
        entity = SemanticEntity(
            id=self.new_id("entity"),
            kind=spec.entity_kind,
            text=segment.text,
            normalized=segment.text.strip().casefold(),
            source_segment_id=segment.id,
            start=segment.start,
            end=segment.end,
            state=state,
            discourse_scope=segment.discourse_scope,
            temporal_scope=segment.temporal_scope,
            authority=authority,
            support_ids=(support.id,),
            attributes=attributes,
            confidence=confidence,
        )
        self.entities.append(entity)
        assertion = SemanticAssertion(
            id=self.new_id("assertion"),
            kind=spec.assertion_kind,
            subject_id="entity:root",
            object_id=entity.id,
            text=segment.text,
            polarity="negative" if state == "asserted" and _NEGATIVE_RE.search(segment.text) else "positive",
            state=state,
            discourse_scope=segment.discourse_scope,
            temporal_scope=segment.temporal_scope,
            authority=authority,
            source_segment_id=segment.id,
            start=segment.start,
            end=segment.end,
            support_ids=(support.id,),
            attributes=attributes,
            confidence=confidence,
        )
        self.assertions.append(assertion)
        return entity


_SCENARIO_SUBJECT_SPEC = _FieldSpec("_scenario_subject", "scenario_actor", "scenario_subject", ())
_SCENARIO_BEHAVIOR_SPEC = _FieldSpec("_scenario_behavior", "behavior", "scenario_behavior", ())
_SCENARIO_RESULT_SPEC = _FieldSpec("_scenario_result", "observable_result", "scenario_result", ())
_JAPANESE_SCENARIO_RE = re.compile(
    r"(?P<subject>[^\s、,。]{1,32}?)(?:が|は)(?P<behavior>[^、,。]{1,96}?)(?:場合(?:は)?)"
    r"(?:[、,]\s*(?P<result>[^。]+))?"
)
_JAPANESE_SIMPLE_SCENARIO_RE = re.compile(
    r"(?P<subject>[^\s、,。]{1,32}?)(?:が|は)(?P<behavior>[^、,。]{2,96}?)(?:[。]|$)"
)
_ENGLISH_SCENARIO_RE = re.compile(
    r"\b(?:when|if)\s+(?P<subject>[A-Za-z][A-Za-z0-9 _-]{0,40}?)\s+"
    r"(?P<behavior>[^,.;]{2,96})(?:[,;]\s*(?P<result>[^.]+))?",
    re.IGNORECASE,
)


def _add_scenario_components(
    builder: _Builder,
    scenario: SemanticEntity,
    by_field: dict[str, list[SemanticEntity]],
) -> None:
    match = _JAPANESE_SCENARIO_RE.search(scenario.text)
    if match is None:
        match = _ENGLISH_SCENARIO_RE.search(scenario.text)
    if match is None:
        match = _JAPANESE_SIMPLE_SCENARIO_RE.search(scenario.text)
    if match is None:
        return
    for group_name, spec in (
        ("subject", _SCENARIO_SUBJECT_SPEC),
        ("behavior", _SCENARIO_BEHAVIOR_SPEC),
        ("result", _SCENARIO_RESULT_SPEC),
    ):
        if group_name not in match.re.groupindex or match.group(group_name) is None:
            continue
        relative_start, relative_end = match.span(group_name)
        start = scenario.start + relative_start
        end = scenario.start + relative_end
        segment = builder.add_segment(
            field_name=spec.field,
            start=start,
            end=end,
            structure="direct_rule",
            discourse=scenario.discourse_scope,
            temporal=scenario.temporal_scope,
            state=scenario.state,
            confidence="medium" if scenario.state == "asserted" else "low",
            authority=scenario.authority,
        )
        support = builder.add_support(
            "direct_rule",
            segment,
            scenario.authority,
            f"scenario_component:{group_name}",
        )
        entity = builder.add_field_entity(
            spec,
            segment,
            support,
            scenario.state,
            scenario.authority,
            "medium" if scenario.state == "asserted" else "low",
            source="scenario_direct_rule",
            extra_attributes={
                "derived_from_entity_id": scenario.id,
                "component_role": group_name,
                "typed_derivation": "scenario_clause/v0",
            },
        )
        by_field.setdefault(spec.field, []).append(entity)


def _line_ranges(text: str) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    offset = 0
    for line in text.splitlines(keepends=True):
        end = offset + len(line.rstrip("\r\n"))
        ranges.append((offset, end))
        offset += len(line)
    if not ranges and text == "":
        ranges.append((0, 0))
    elif offset < len(text):
        ranges.append((offset, len(text)))
    return ranges


def _sentence_ranges(line: str) -> list[tuple[int, int]]:
    """Return bounded sentence ranges without splitting paths or decimals."""

    ranges: list[tuple[int, int]] = []
    start = 0
    for match in _SENTENCE_END_RE.finditer(line):
        end = match.end()
        ranges.append((start, end))
        start = end
    if start < len(line) or not ranges:
        ranges.append((start, len(line)))
    return ranges


def _extract_deterministic(builder: _Builder) -> dict[str, list[SemanticEntity]]:
    by_field: dict[str, list[SemanticEntity]] = {}
    for line_start, line_end in _line_ranges(builder.text):
        line = builder.text[line_start:line_end]
        structured_matches = list(_STRUCTURED_FIELD_RE.finditer(line))
        boundary_matches = list(_BOUNDARY_FIELD_RE.finditer(line))
        for match_index, match in enumerate(structured_matches):
            label = match.group("label")
            spec = _LABEL_TO_SPEC[label.casefold()]
            absolute_label_start = line_start + match.start("label")
            value_start = line_start + match.end()
            following_boundaries = [
                item for item in boundary_matches if item.start() > match.start()
            ]
            raw_value_end = (
                line_start + following_boundaries[0].start()
                if following_boundaries
                else line_end
            )
            value_end = raw_value_end
            sentence_boundary = _SENTENCE_END_RE.search(
                builder.text,
                value_start,
                raw_value_end,
            )
            if sentence_boundary is not None:
                value_end = sentence_boundary.end()
                trailing_start = value_end
                trailing = builder.text[trailing_start:raw_value_end]
                for relative_start, relative_end in _sentence_ranges(trailing):
                    clause = trailing[relative_start:relative_end]
                    stripped = clause.strip()
                    if not stripped:
                        continue
                    direct_match = _DIRECT_LINE_RE.search(clause)
                    if direct_match is not None and _direct_has_predicate(clause, direct_match):
                        continue
                    start = trailing_start + relative_start
                    end = trailing_start + relative_end
                    while start < end and builder.text[start].isspace():
                        start += 1
                    while end > start and builder.text[end - 1].isspace():
                        end -= 1
                    if start < end:
                        builder.unresolved_spans.append(
                            {
                                "start": start,
                                "end": end,
                                "reason": "unlabelled_trailing_structured_field_clause",
                                "field": spec.field,
                            }
                        )
                        builder.diagnostics.append(
                            f"structured_field.unresolved_trailing_clause:{spec.field}:{start}:{end}"
                        )
            local_context_start = (
                match.start()
                if match_index > 0
                else max(
                    (line.rfind(mark, 0, match.start("label")) + 1 for mark in ("。", ";", "；")),
                    default=0,
                )
            )
            local_end = value_end - line_start
            local_clause = line[local_context_start:local_end]
            local_label_start = match.start("label") - local_context_start
            discourse, temporal, scope_authority = _scope_for(local_clause, local_label_start)
            value_start, value_end = _trim_value(
                builder.text,
                value_start,
                value_end,
                quoted=discourse == "quoted" or "「" in line[: match.start("label") + 1],
            )
            value = builder.text[value_start:value_end]
            state, authority, confidence = _classify_value(label, value, discourse, temporal)
            if scope_authority != "assertion_capable" and state == "asserted":
                state, authority, confidence = "candidate", "candidate_only", "medium"
            segment_start = value_start if value_start < value_end else absolute_label_start
            segment_end = value_end if value_start < value_end else line_start + match.end()
            segment = builder.add_segment(
                field_name=spec.field,
                start=segment_start,
                end=segment_end,
                structure="structured_field",
                discourse=discourse,
                temporal=temporal,
                state=state,
                confidence=confidence,
                authority=authority,
            )
            support = builder.add_support("structured_field", segment, authority, f"label:{label}")
            entity = builder.add_field_entity(spec, segment, support, state, authority, confidence, source="structured_field")
            by_field.setdefault(spec.field, []).append(entity)
            if spec.field == "scenario":
                _add_scenario_components(builder, entity, by_field)

        # Direct fields are evaluated per sentence. This permits a structured
        # field followed by a direct field on the same physical line, while a
        # word inside a structured value (for example `未認証利用者`) is never
        # reinterpreted as a second field.
        for clause_start, clause_end in _sentence_ranges(line):
            clause = line[clause_start:clause_end]
            match = _DIRECT_LINE_RE.search(clause)
            if match is None:
                continue
            if any(clause_start <= item.start("label") < clause_end for item in structured_matches):
                continue
            label = match.group("label")
            spec = _LABEL_TO_SPEC[label.casefold()]
            discourse, temporal, scope_authority = _scope_for(clause, match.start("label"))
            direct = find_field_assertion(clause, [label])
            if direct is None and scope_authority == "assertion_capable":
                continue
            if scope_authority != "assertion_capable":
                state, authority, confidence = "candidate", "candidate_only", "medium"
            elif not _direct_has_predicate(clause, match):
                state, authority, confidence = "candidate", "candidate_only", "low"
            elif direct is not None and direct.status == "rejected":
                state, authority, confidence = "rejected", "signal_only", "high"
            else:
                state, authority, confidence = "asserted", "assertion_capable", "medium"
            start = line_start + clause_start
            end = line_start + clause_end
            segment = builder.add_segment(
                field_name=spec.field,
                start=start,
                end=end,
                structure="direct_rule",
                discourse=discourse,
                temporal=temporal,
                state=state,
                confidence=confidence,
                authority=authority,
            )
            support = builder.add_support("direct_rule", segment, authority, f"term:{label}")
            entity = builder.add_field_entity(spec, segment, support, state, authority, confidence, source="direct_rule")
            by_field.setdefault(spec.field, []).append(entity)
            if spec.field == "scenario":
                _add_scenario_components(builder, entity, by_field)
    return by_field


def _add_root(builder: _Builder) -> SemanticEntity:
    segment = builder.add_segment(
        field_name="requirement",
        start=0,
        end=len(builder.text),
        structure="caller_structure",
        discourse="binding",
        temporal="current",
        state="asserted",
        confidence="high",
        authority="assertion_capable",
    )
    support = builder.add_support(
        "caller_structure",
        segment,
        "assertion_capable",
        "implicit requirement record container; not proof of field completeness",
    )
    root = SemanticEntity(
        id="entity:root",
        kind="requirement",
        text=builder.text,
        normalized="requirement_record",
        source_segment_id=segment.id,
        start=0,
        end=len(builder.text),
        state="asserted",
        discourse_scope="binding",
        temporal_scope="current",
        authority="assertion_capable",
        support_ids=(support.id,),
        attributes={"implicit_container": True},
        confidence="high",
    )
    builder.entities.insert(0, root)
    return root


def _preferred_current(by_field: Mapping[str, list[SemanticEntity]], field_name: str) -> SemanticEntity | None:
    entities = by_field.get(field_name, [])
    order = {"asserted": 0, "rejected": 1, "conflict": 2, "unknown": 3, "candidate": 4}
    current = [item for item in entities if item.discourse_scope == "binding" and item.temporal_scope == "current"]
    pool = current or list(entities)
    return min(pool, key=lambda item: order[item.state]) if pool else None


def _add_relation(
    builder: _Builder,
    kind: str,
    source: SemanticEntity | None,
    target: SemanticEntity | None,
    *,
    cooccurrence_only: bool = False,
) -> None:
    if source is None or target is None:
        return
    state = _combine_state(source.state, target.state)
    discourse: DiscourseScope = "binding" if source.discourse_scope == target.discourse_scope == "binding" else "unknown"
    temporal: TemporalScope = "current" if source.temporal_scope == target.temporal_scope == "current" else "unknown"
    if discourse != "binding" or temporal != "current":
        state = "candidate" if state == "asserted" else state
    if cooccurrence_only and state == "asserted":
        state = "candidate"
    authority = _authority_for_state(state)
    builder.relations.append(
        SemanticRelation(
            id=builder.new_id("relation"),
            kind=kind,
            from_id=source.id,
            to_id=target.id,
            state=state,
            discourse_scope=discourse,
            temporal_scope=temporal,
            authority=authority,
            support_ids=tuple(dict.fromkeys((*source.support_ids, *target.support_ids))),
            attributes={
                "derivation": "same_requirement_record",
                "cooccurrence_only": cooccurrence_only,
                "non_decision": "field co-occurrence does not prove target alignment" if cooccurrence_only else "",
            },
            confidence="high" if state == "asserted" else "medium",
        )
    )


def _link_record(builder: _Builder, root: SemanticEntity, by_field: Mapping[str, list[SemanticEntity]]) -> None:
    actor = _preferred_current(by_field, "_scenario_subject") or _preferred_current(by_field, "user")
    behavior = _preferred_current(by_field, "_scenario_behavior") or _preferred_current(by_field, "purpose")
    condition = _preferred_current(by_field, "scenario")
    result = _preferred_current(by_field, "_scenario_result") or _preferred_current(by_field, "expected_result")
    criterion = _preferred_current(by_field, "acceptance_criteria")
    method = _preferred_current(by_field, "verification_method")
    evidence = _preferred_current(by_field, "evidence")
    _add_relation(builder, "applies_to", root, actor)
    _add_relation(builder, "performs", actor, behavior)
    _add_relation(builder, "triggered_by", behavior, condition)
    _add_relation(builder, "produces", behavior, result)
    _add_relation(builder, "constrained_by", result, criterion)
    _add_relation(builder, "verified_by", root, method)
    _add_relation(builder, "verifies", method, criterion, cooccurrence_only=True)
    _add_relation(builder, "produces_evidence", method, evidence, cooccurrence_only=True)


def _provider_call(provider: object, text: str) -> object:
    analyze = getattr(provider, "analyze", None)
    if callable(analyze):
        return analyze(text)
    if callable(provider):
        return provider(text)
    raise TypeError("provider must be callable or expose analyze(text)")


def _valid_span(value: Mapping[str, Any], text: str) -> tuple[int, int] | None:
    start = value.get("start")
    end = value.get("end")
    if not isinstance(start, int) or isinstance(start, bool) or not isinstance(end, int) or isinstance(end, bool):
        return None
    if start < 0 or end <= start or end > len(text):
        return None
    return start, end


def _run_morphology(builder: _Builder, provider: object | None, unresolved: bool) -> None:
    if provider is None:
        status = "not_configured" if unresolved else "skipped"
        builder.attempts.append(ExtractionAttempt("morphology", status, "signal_only"))
        return
    try:
        raw = _provider_call(provider, builder.text)
        if not isinstance(raw, Mapping):
            raise TypeError("morphology result must be a mapping")
        valid_tokens: list[dict[str, object]] = []
        diagnostics: list[str] = []
        for index, token in enumerate(raw.get("tokens", [])):
            if not isinstance(token, Mapping) or _valid_span(token, builder.text) is None:
                diagnostics.append(f"morphology.invalid_span:{index}")
                continue
            valid_tokens.append(dict(token))
        segment = builder.add_segment(
            field_name="unknown",
            start=0,
            end=len(builder.text),
            structure="morphology",
            discourse="unknown",
            temporal="unknown",
            state="unknown",
            confidence="unknown",
            authority="signal_only",
        )
        support = builder.add_support(
            "morphology",
            segment,
            "signal_only",
            "tokenization/POS signal only; cannot assert a relation",
            {"tokens": valid_tokens},
        )
        builder.diagnostics.extend(diagnostics)
        builder.attempts.append(
            ExtractionAttempt(
                "morphology",
                "executed",
                "signal_only",
                provider_id=str(raw.get("provider_id", "")),
                provider_version=str(raw.get("provider_version", "")),
                resource_version=str(raw.get("resource_version", "")),
                split_mode=str(raw.get("split_mode", "")),
                produced_ids=(support.id,),
                diagnostics=tuple(diagnostics),
            )
        )
    except Exception as exc:  # provider boundary
        unavailable = "unavailable" in type(exc).__name__.casefold()
        diagnostic = f"morphology.{('unavailable' if unavailable else 'failed')}:{type(exc).__name__}:{exc}"
        builder.diagnostics.append(diagnostic)
        builder.attempts.append(
            ExtractionAttempt("morphology", "unavailable" if unavailable else "failed", "signal_only", diagnostics=(diagnostic,))
        )


def _candidate_items(raw: object) -> tuple[list[Mapping[str, Any]], Mapping[str, Any]]:
    metadata: Mapping[str, Any] = raw if isinstance(raw, Mapping) else {}
    if isinstance(raw, Mapping):
        candidates = raw.get("candidates")
        if candidates is None:
            candidates = [*raw.get("entities", []), *raw.get("assertions", []), *raw.get("relations", [])]
    else:
        candidates = raw
    if not isinstance(candidates, Sequence) or isinstance(candidates, (str, bytes)):
        raise TypeError("candidate result must contain a sequence")
    return [item for item in candidates if isinstance(item, Mapping)], metadata


def _add_candidate(builder: _Builder, item: Mapping[str, Any], tier: Literal["dependency_parse", "llm"], index: int) -> str | None:
    span = _valid_span(item, builder.text)
    if span is None:
        builder.diagnostics.append(f"{tier}.invalid_span:{index}")
        return None
    start, end = span
    segment = builder.add_segment(
        field_name=str(item.get("field", "unknown")),
        start=start,
        end=end,
        structure=tier,
        discourse="unknown",
        temporal="unknown",
        state="candidate",
        confidence="low",
        authority="candidate_only",
    )
    support = builder.add_support(
        tier,
        segment,
        "candidate_only",
        "untrusted candidate; provider authority and asserted state were discarded",
        {"provider_claimed_state": item.get("state"), "provider_claimed_authority": item.get("authority")},
    )
    candidate_type = str(item.get("type", item.get("candidate_type", "entity")))
    if candidate_type == "relation" or ("from_id" in item and "to_id" in item):
        relation = SemanticRelation(
            id=builder.new_id("relation"),
            kind=str(item.get("kind", "unknown")),
            from_id=str(item.get("from_id", "")),
            to_id=str(item.get("to_id", "")),
            state="candidate",
            discourse_scope="unknown",
            temporal_scope="unknown",
            authority="candidate_only",
            support_ids=(support.id,),
            attributes={"source": tier, "provider_payload": dict(item)},
            confidence="low",
        )
        builder.relations.append(relation)
        return relation.id
    if candidate_type == "assertion" or "subject_id" in item:
        assertion = SemanticAssertion(
            id=builder.new_id("assertion"),
            kind=str(item.get("kind", "unknown")),
            subject_id=str(item.get("subject_id", "")),
            object_id=str(item.get("object_id", "")),
            text=builder.text[start:end],
            polarity=str(item.get("polarity", "unknown")) if item.get("polarity") in {"positive", "negative"} else "unknown",
            state="candidate",
            discourse_scope="unknown",
            temporal_scope="unknown",
            authority="candidate_only",
            source_segment_id=segment.id,
            start=start,
            end=end,
            support_ids=(support.id,),
            attributes={"source": tier, "provider_payload": dict(item)},
            confidence="low",
        )
        builder.assertions.append(assertion)
        return assertion.id
    raw_kind = str(item.get("kind", "unknown"))
    kind: EntityKind = raw_kind if raw_kind in {
        "requirement", "scenario_actor", "behavior", "object", "condition", "observable_result",
        "acceptance_criterion", "metric", "verification_method", "evidence_artifact", "unknown",
    } else "unknown"
    entity = SemanticEntity(
        id=builder.new_id("entity"),
        kind=kind,
        text=builder.text[start:end],
        normalized=str(item.get("normalized", builder.text[start:end].casefold())),
        source_segment_id=segment.id,
        start=start,
        end=end,
        state="candidate",
        discourse_scope="unknown",
        temporal_scope="unknown",
        authority="candidate_only",
        support_ids=(support.id,),
        attributes={"source": tier, "provider_payload": dict(item)},
        confidence="low",
    )
    builder.entities.append(entity)
    return entity.id


def _run_candidates(builder: _Builder, stage: Literal["dependency_parse", "llm"], raw_or_provider: object | None, unresolved: bool) -> None:
    if not unresolved:
        builder.attempts.append(ExtractionAttempt(stage, "skipped", "candidate_only"))
        return
    if raw_or_provider is None:
        builder.attempts.append(ExtractionAttempt(stage, "not_configured", "candidate_only"))
        return
    try:
        raw = _provider_call(raw_or_provider, builder.text) if stage == "dependency_parse" else raw_or_provider
        items, metadata = _candidate_items(raw)
        produced = tuple(
            result
            for index, item in enumerate(items)
            if (result := _add_candidate(builder, item, stage, index)) is not None
        )
        diagnostics = tuple(item for item in builder.diagnostics if item.startswith(f"{stage}.invalid_span:"))
        builder.attempts.append(
            ExtractionAttempt(
                stage,
                "executed",
                "candidate_only",
                provider_id=str(metadata.get("provider_id", "")),
                provider_version=str(metadata.get("provider_version", "")),
                resource_version=str(metadata.get("resource_version", "")),
                split_mode=str(metadata.get("split_mode", "")),
                produced_ids=produced,
                diagnostics=diagnostics,
            )
        )
    except Exception as exc:  # provider/candidate boundary
        unavailable = "unavailable" in type(exc).__name__.casefold()
        diagnostic = f"{stage}.{('unavailable' if unavailable else 'failed')}:{type(exc).__name__}:{exc}"
        builder.diagnostics.append(diagnostic)
        builder.attempts.append(
            ExtractionAttempt(stage, "unavailable" if unavailable else "failed", "candidate_only", diagnostics=(diagnostic,))
        )


def _record_metadata(text: str, by_field: Mapping[str, list[SemanticEntity]]) -> tuple[dict[str, object], dict[str, object]]:
    current_asserted = {
        name
        for name, values in by_field.items()
        if any(item.state == "asserted" and item.discourse_scope == "binding" and item.temporal_scope == "current" for item in values)
    }
    core_fields = {spec.field for spec in _FIELD_SPECS}
    label_counts = {
        name: sum(
            item.discourse_scope == "binding" and item.temporal_scope == "current"
            for item in values
        )
        for name, values in by_field.items()
        if name in core_fields
    }
    repeated_core = any(count > 1 for count in label_counts.values())
    req_ids = len(_REQ_ID_RE.findall(text))
    record_count = max(1, req_ids, 2 if repeated_core else 1)
    functional_basis = (
        "scenario" in current_asserted
        and "_scenario_behavior" in current_asserted
        and bool({"_scenario_result", "expected_result"} & current_asserted)
    )
    requirement_kind = "functional" if functional_basis else "unknown"
    kind_state = "asserted" if functional_basis else "unknown"
    single_record = record_count == 1
    closed = functional_basis and single_record
    mode = "closed_record" if closed else "open_text"
    coverage = {
        "fields": {name: [item.state for item in values] for name, values in by_field.items()},
        "field_states": {
            name: (preferred.state if (preferred := _preferred_current(by_field, name)) is not None else "unknown")
            for name in by_field
        },
        "record_mode": mode,
        "record_count": record_count,
        "single_record": single_record,
        "unresolved": not closed,
    }
    metadata = {
        "requirement_kind": requirement_kind,
        "requirement_kind_state": kind_state,
        "requirement_kind_basis": [
            name
            for name in ("scenario", "_scenario_behavior", "_scenario_result", "expected_result")
            if name in current_asserted
        ],
        "record_mode": mode,
        "record_count": record_count,
        "single_record": single_record,
        "closed_record_basis": "current binding scenario with extracted behavior and observable result; no repeated core labels or requirement IDs" if closed else "not established",
        "authority_policy": "only current binding deterministic structure may assert; morphology is signal-only; dependency and LLM are candidate-only",
    }
    return coverage, metadata


def _candidate_conflicts(builder: _Builder) -> list[dict[str, object]]:
    grouped: dict[tuple[int, int, str], list[SemanticAssertion]] = {}
    for assertion in builder.assertions:
        if assertion.authority != "candidate_only":
            continue
        grouped.setdefault((assertion.start, assertion.end, assertion.kind), []).append(assertion)
    conflicts: list[dict[str, object]] = []
    for (start, end, kind), assertions in grouped.items():
        polarities = {item.polarity for item in assertions if item.polarity != "unknown"}
        if polarities != {"positive", "negative"}:
            continue
        record = {
            "start": start,
            "end": end,
            "kind": kind,
            "assertion_ids": [item.id for item in assertions],
            "resolution": "unresolved",
        }
        conflicts.append(record)
        builder.diagnostics.append(f"candidate_conflict:{kind}:{start}:{end}")
    return conflicts


def extract_semantic_assertions(
    text: str,
    context: str = "",
    *,
    morphology_provider: object | None = None,
    dependency_provider: object | None = None,
    llm_candidates: object | None = None,
) -> SemanticAssertionIR:
    """Extract a bounded, evidence-linked semantic assertion graph.

    Deterministic current/binding fields can assert. Morphology only contributes
    token/POS signals. Dependency parsers and LLMs only contribute candidates,
    irrespective of provider-claimed state, confidence, or authority.
    """

    if not isinstance(text, str) or not isinstance(context, str):
        raise TypeError("text and context must be strings")
    separator = "\n" if text and context else ""
    source_text = f"{text}{separator}{context}"
    context_start = len(text) + len(separator)
    builder = _Builder(source_text, context)
    root = _add_root(builder)
    builder.attempts.append(
        ExtractionAttempt("caller_structure", "executed", "assertion_capable", produced_ids=(root.id,))
    )
    by_field = _extract_deterministic(builder)
    builder.attempts.append(
        ExtractionAttempt(
            "structured_field",
            "executed",
            "assertion_capable",
            produced_ids=tuple(item.id for items in by_field.values() for item in items if item.attributes.get("source") == "structured_field"),
        )
    )
    builder.attempts.append(
        ExtractionAttempt(
            "direct_rule",
            "executed",
            "assertion_capable",
            produced_ids=tuple(item.id for items in by_field.values() for item in items if item.attributes.get("source") == "direct_rule"),
        )
    )
    _link_record(builder, root, by_field)
    coverage, metadata = _record_metadata(source_text, by_field)
    if builder.unresolved_spans:
        coverage["unresolved"] = True
        coverage["unresolved_spans"] = list(builder.unresolved_spans)
        coverage["record_mode"] = "open_text"
        metadata["record_mode"] = "open_text"
        metadata["closed_record_basis"] = "unlabelled trailing structured-field clause remains unresolved"
    metadata["source_layout"] = {
        "coordinate_space": "combined_input/v1",
        "text": {"start": 0, "end": len(text)},
        "separator": {"start": len(text), "end": context_start, "text": separator},
        "context": {"start": context_start, "end": len(source_text)},
    }
    required_first_slice_fields = {
        "purpose",
        "user",
        "scenario",
        "expected_result",
        "acceptance_criteria",
        "verification_method",
        "evidence",
    }
    asserted_fields = {
        name
        for name, state in dict(coverage["field_states"]).items()
        if state == "asserted"
    }
    unresolved_relation_kinds = {
        relation.kind
        for relation in builder.relations
        if relation.state != "asserted"
    }
    unresolved = (
        bool(coverage["unresolved"])
        or not required_first_slice_fields.issubset(asserted_fields)
        or bool({"verifies", "produces_evidence"} & unresolved_relation_kinds)
    )
    coverage["unresolved"] = unresolved
    coverage["unresolved_relation_kinds"] = sorted(unresolved_relation_kinds)
    _run_morphology(builder, morphology_provider, unresolved)
    _run_candidates(builder, "dependency_parse", dependency_provider, unresolved)
    _run_candidates(builder, "llm", llm_candidates, unresolved)
    coverage["candidate_conflicts"] = _candidate_conflicts(builder)
    return SemanticAssertionIR(
        text=text,
        context=context,
        source_text=source_text,
        source_segments=tuple(builder.segments),
        entities=tuple(builder.entities),
        assertions=tuple(builder.assertions),
        relations=tuple(builder.relations),
        supports=tuple(builder.supports),
        attempts=tuple(builder.attempts),
        diagnostics=tuple(builder.diagnostics),
        coverage=coverage,
        metadata=metadata,
    )
