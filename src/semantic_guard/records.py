from __future__ import annotations

from dataclasses import dataclass
import re


FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "purpose": ("purpose", "目的"),
    "user": ("user", "stakeholder", "利用者", "ユーザー", "主体"),
    "scenario": ("scenario", "シナリオ", "利用場面", "場面"),
    "expected_result": ("expected result", "expected_result", "期待結果", "期待する結果"),
    "acceptance_criteria": (
        "acceptance criteria",
        "acceptance criterion",
        "acceptance_criteria",
        "受入基準",
        "受け入れ基準",
    ),
    "verification_method": (
        "verification method",
        "verification_method",
        "検証方法",
        "確認方法",
    ),
    "evidence": ("evidence", "evidence artifact", "証拠", "証拠成果物"),
}

REQUIRED_FIELDS = tuple(FIELD_ALIASES)


def _alias_pattern() -> re.Pattern[str]:
    aliases = sorted(
        (alias for values in FIELD_ALIASES.values() for alias in values),
        key=len,
        reverse=True,
    )
    joined = "|".join(re.escape(alias) for alias in aliases)
    return re.compile(rf"^(?P<indent>[ \t]*)(?P<label>{joined})[ \t]*[:：][ \t]*(?P<value>.*)$", re.IGNORECASE)


FIELD_LINE = _alias_pattern()
RECORD_SEPARATOR = re.compile(r"^[ \t]*(?:---+|===+)[ \t]*$")


@dataclass(frozen=True, slots=True)
class ParsedField:
    name: str
    label: str
    value: str
    start: int
    end: int
    value_start: int
    value_end: int
    line: int

    def source_excerpt(self, source: str) -> str:
        return source[self.value_start : self.value_end]


@dataclass(frozen=True, slots=True)
class ParsedRequirementRecord:
    source_text: str
    fields: dict[str, tuple[ParsedField, ...]]
    record_mode: str
    record_count: int
    unconsumed_spans: tuple[tuple[int, int], ...] = ()
    diagnostics: tuple[str, ...] = ()

    def one(self, name: str) -> ParsedField | None:
        values = self.fields.get(name, ())
        return values[0] if len(values) == 1 else None

    @property
    def missing_fields(self) -> tuple[str, ...]:
        return tuple(name for name in REQUIRED_FIELDS if not self.fields.get(name))

    @property
    def duplicate_fields(self) -> tuple[str, ...]:
        return tuple(name for name in REQUIRED_FIELDS if len(self.fields.get(name, ())) > 1)


def _canonical_field(label: str) -> str:
    normalized = label.casefold().strip()
    for name, aliases in FIELD_ALIASES.items():
        if normalized in {alias.casefold() for alias in aliases}:
            return name
    raise KeyError(label)


def parse_requirement_record(text: str) -> ParsedRequirementRecord:
    """Parse one labelled record without treating open prose as a closed record.

    Only explicit `label: value` lines are assertion-capable. Continuation lines,
    headings, comments, and additional records are deliberately left unconsumed
    so a later residual-risk policy can hold the affected obligations.
    """

    fields: dict[str, list[ParsedField]] = {name: [] for name in REQUIRED_FIELDS}
    unconsumed: list[tuple[int, int]] = []
    diagnostics: list[str] = []
    separators = 0
    offset = 0

    for line_number, line_with_ending in enumerate(text.splitlines(keepends=True), start=1):
        line = line_with_ending.rstrip("\r\n")
        line_end = offset + len(line)
        if not line.strip():
            offset += len(line_with_ending)
            continue
        if RECORD_SEPARATOR.match(line):
            separators += 1
            offset += len(line_with_ending)
            continue
        match = FIELD_LINE.match(line)
        if match is None:
            unconsumed.append((offset, line_end))
            offset += len(line_with_ending)
            continue

        name = _canonical_field(match.group("label"))
        raw_value = match.group("value")
        leading = len(raw_value) - len(raw_value.lstrip())
        trailing = len(raw_value.rstrip())
        value = raw_value.strip()
        value_start = offset + match.start("value") + leading
        value_end = offset + match.start("value") + trailing
        fields[name].append(
            ParsedField(
                name=name,
                label=match.group("label"),
                value=value,
                start=offset,
                end=line_end,
                value_start=value_start,
                value_end=value_end,
                line=line_number,
            )
        )
        if not value:
            diagnostics.append(f"empty_field:{name}:line={line_number}")
        offset += len(line_with_ending)

    if text and not text.endswith(("\n", "\r")) and offset < len(text):
        offset = len(text)

    record_count = separators + 1 if text.strip() else 0
    duplicate_fields = [name for name, values in fields.items() if len(values) > 1]
    missing_fields = [name for name, values in fields.items() if len(values) != 1 or not values[0].value]
    if record_count > 1:
        diagnostics.append(f"multiple_records:{record_count}")
    diagnostics.extend(f"duplicate_field:{name}" for name in duplicate_fields)
    diagnostics.extend(f"missing_or_empty_field:{name}" for name in missing_fields)
    if unconsumed:
        diagnostics.append(f"unconsumed_span_count:{len(unconsumed)}")

    closed = (
        record_count == 1
        and not unconsumed
        and not duplicate_fields
        and not missing_fields
    )
    return ParsedRequirementRecord(
        source_text=text,
        fields={name: tuple(values) for name, values in fields.items()},
        record_mode="closed_record" if closed else "open_text",
        record_count=record_count,
        unconsumed_spans=tuple(unconsumed),
        diagnostics=tuple(diagnostics),
    )
