"""Mechanical accuracy checks that need no human labels.

Two properties of a detector can be tested without ground truth beyond the
fixtures the repository already holds:

* **Invariance.** A semantics-preserving rewrite of an input (full-width
  characters, decomposed kana, bullet markers, a different line order, ...)
  must not change the verdict. The recorded fixtures supply the inputs; the
  rewrite supplies the second view. A verdict that moves is a detector that
  reads the spelling rather than the meaning.
* **Sensitivity.** Deleting one required field from a known-good document must
  raise the finding that field is responsible for. A deletion that raises
  nothing is a rule that cannot see its own obligation.

Both are ratchets. Every accepted exception is listed with its reason, and an
exception that stops occurring is reported as stale, so the table can only
shrink as the detectors improve.

This is calibration against the repository's own fixtures. It does not measure
field accuracy and does not grant any acceptance.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from semantic_guard_workflow.core import audit_plan, audit_request, finish_check
from semantic_guard_workflow.evaluation import DEFAULT_FIXTURE_ROOT, _fixture_text, _load_spec, _run_fixture
from semantic_guard_workflow.rule_mapping import enrich_finding_mapping
from semantic_guard_workflow.rules import RULES

Transform = Callable[[str], str]

_PROSE_PHASES = frozenset({"audit_request", "audit_plan", "finish_check"})


# --- semantics-preserving rewrites ---------------------------------------------------


def _outside_fences(text: str, line_fn: Callable[[str], str]) -> str:
    """Apply ``line_fn`` to every line that is not inside a fenced code block."""
    lines: list[str] = []
    in_fence = False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            lines.append(line)
        else:
            lines.append(line if in_fence else line_fn(line))
    return "\n".join(lines)


def _fullwidth_ascii(text: str) -> str:
    def convert(line: str) -> str:
        return "".join(chr(ord(ch) + 0xFEE0) if 0x21 <= ord(ch) <= 0x7E else ch for ch in line)

    return _outside_fences(text, convert)


def _decomposed(text: str) -> str:
    return _outside_fences(text, lambda line: unicodedata.normalize("NFD", line))


def _build_halfwidth_katakana() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for code in range(0xFF61, 0xFFA0):
        mapping.setdefault(unicodedata.normalize("NFKC", chr(code)), chr(code))
    marks = {"\u3099": "\uff9e", "\u309a": "\uff9f"}
    for code in range(0x30A1, 0x30FB):
        decomposed = unicodedata.normalize("NFD", chr(code))
        if len(decomposed) == 2 and decomposed[1] in marks and decomposed[0] in mapping:
            mapping[chr(code)] = mapping[decomposed[0]] + marks[decomposed[1]]
    return mapping


_HALFWIDTH_KATAKANA = _build_halfwidth_katakana()


def _halfwidth_katakana(text: str) -> str:
    return _outside_fences(text, lambda line: "".join(_HALFWIDTH_KATAKANA.get(ch, ch) for ch in line))


def _ideographic_space(text: str) -> str:
    return _outside_fences(text, lambda line: line.replace(" ", "\u3000"))


def _invisible_characters(text: str) -> str:
    def convert(line: str) -> str:
        return re.sub(r"([ :：])", "\\1\u200b", line)

    return "\ufeff" + _outside_fences(text, convert)


# Format characters that render as nothing: ZWNJ, ZWJ, soft hyphen, the bidirectional
# marks and embeddings, invisible operators, the Arabic letter mark, a variation
# selector, a tag character, and the combining grapheme joiner.
_FORMAT_CHARACTERS = (
    "\u200c", "\u200d", "\u00ad", "\u200e", "\u200f", "\u202a", "\u202b", "\u202c", "\u202d", "\u202e",
    "\u2060", "\u2062", "\u2063", "\u061c", "\ufe0f", "\U000e0020", "\u034f", "\u180e",
)


def _invisible_inside_words(text: str) -> str:
    """Put a format character inside every word and label, not only beside them."""
    counter = 0

    def convert(line: str) -> str:
        def insert(match: re.Match[str]) -> str:
            nonlocal counter
            word = match.group(0)
            character = _FORMAT_CHARACTERS[counter % len(_FORMAT_CHARACTERS)]
            counter += 1
            return word[0] + character + word[1:]

        return re.sub(r"[A-Za-z0-9_\u3040-\u30ff\u4e00-\u9fff]{2,}", insert, line)

    return _outside_fences(text, convert)


def _crlf(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\n", "\r\n")


def _line_break(character: str) -> Transform:
    def convert(text: str) -> str:
        return text.replace("\r\n", "\n").replace("\n", character)

    return convert


def _trailing_whitespace(text: str) -> str:
    return "\n".join(line + "  " for line in text.split("\n"))


def _bold_label(text: str) -> str:
    return _outside_fences(text, lambda line: re.sub(r"^([^:：\n*]{1,12})([:：])", r"**\1**\2", line))


def _prefix(prefix: str) -> Transform:
    def convert(text: str) -> str:
        return _outside_fences(text, lambda line: prefix + line if line.strip() else line)

    return convert


def _numbered(text: str) -> str:
    counter = 0

    def convert(line: str) -> str:
        nonlocal counter
        if not line.strip():
            return line
        counter += 1
        return f"{counter}. {line}"

    return _outside_fences(text, convert)


def _rotate_lines(text: str) -> str:
    lines = text.split("\n")
    content = [index for index, line in enumerate(lines) if line.strip()]
    if len(content) < 2:
        return text
    first = lines[content[0]]
    rest = [lines[index] for index in content[1:]]
    return "\n".join([*rest, first])


def _sentence_newlines(text: str) -> str:
    return text.replace("。", "。\n")


@dataclass(frozen=True)
class RewriteSpec:
    name: str
    description: str
    apply: Transform
    # True when the rewrite is also safe on diff bodies, which are code.
    diff_safe: bool = False
    # True when the rewrite changes what Markdown structure means (it reorders
    # lines or adds heading syntax) and so is only semantics-preserving for
    # plain requirement, plan, and completion text, not for documents.
    prose_only: bool = False


REWRITES: tuple[RewriteSpec, ...] = (
    RewriteSpec("fullwidth_ascii", "ASCII letters, digits, and punctuation as full-width forms", _fullwidth_ascii),
    RewriteSpec("decomposed_kana", "NFD: dakuten and handakuten as separate combining marks", _decomposed),
    RewriteSpec("halfwidth_katakana", "katakana as half-width forms", _halfwidth_katakana),
    RewriteSpec("ideographic_space", "ASCII spaces as U+3000", _ideographic_space),
    RewriteSpec("invisible_characters", "BOM and zero-width spaces after spaces and colons", _invisible_characters),
    RewriteSpec("invisible_inside_words", "format characters inside every word and label", _invisible_inside_words),
    RewriteSpec("crlf", "CRLF line endings", _crlf, diff_safe=True),
    RewriteSpec("cr_line_breaks", "lone CR line endings", _line_break("\r")),
    RewriteSpec("line_separators", "U+2028 line separators", _line_break("\u2028")),
    RewriteSpec("paragraph_separators", "U+2029 paragraph separators", _line_break("\u2029")),
    RewriteSpec("next_line_breaks", "U+0085 next-line characters", _line_break("\x85")),
    RewriteSpec("trailing_whitespace", "two trailing spaces on every line", _trailing_whitespace, diff_safe=True),
    RewriteSpec("bold_label", "Markdown bold around field labels", _bold_label),
    RewriteSpec("bullet_markers", "'- ' list markers", _prefix("- "), prose_only=True),
    RewriteSpec("numbered_markers", "'n. ' list markers", _numbered, prose_only=True),
    RewriteSpec("heading_markers", "'## ' heading markers", _prefix("## "), prose_only=True),
    RewriteSpec("blockquote_markers", "'> ' quote markers", _prefix("> "), prose_only=True),
    RewriteSpec("rotated_lines", "first line moved to the end", _rotate_lines, prose_only=True),
    RewriteSpec("sentence_newlines", "a line break after every sentence", _sentence_newlines, prose_only=True),
)

# A known pair permits only this exact status and rule delta. Other regressions
# in the same fixture must remain unexpected; a reason alone is not a waiver.
# No rewrite currently drifts: the relation audit reads the normalized text, so
# spelling and invisible characters no longer change a verdict. An entry that
# stops occurring is reported as stale, which keeps this table from rotting.
KNOWN_DRIFT: dict[tuple[str, str], dict[str, Any]] = {}


def _applicable(spec: RewriteSpec, fixture: dict[str, Any]) -> bool:
    phase = fixture.get("phase")
    if phase == "audit_diff":
        return spec.diff_safe
    if phase not in _PROSE_PHASES:
        return False
    if spec.prose_only and fixture.get("kind") == "document":
        return False
    return True


def _structural_rewrite_skip_reason(spec: RewriteSpec, text: str) -> str:
    if spec.name not in {"rotated_lines", "sentence_newlines"}:
        return ""
    if re.search(r"(?m)^[ \t]*(?:`{3,}|~{3,})", text):
        return "fenced code may contain literal sentence marks or order-sensitive lines"
    if "`" in text or re.search(r"(?m)^(?: {4}|\t)\S", text):
        return "code literals are outside the flat-prose rewrite scope"
    if re.search(r"(?m)^[ \t]*(?:#{1,6}\s|>|[-*+]\s|\d+[.)]\s|\|)", text):
        return "Markdown containers and ordered steps require structure-aware rewriting"
    if spec.name == "rotated_lines" and any(
        not re.match(r"^[^:：]{1,32}[:：]\s*\S", line)
        for line in text.splitlines() if line.strip()
    ):
        return "line rotation is limited to self-contained labelled field records"
    return ""


@dataclass(frozen=True)
class Verdict:
    """What a rewrite must not change: status, score, each finding's rule and severity, and gaps."""

    status: str
    score: float
    rules: tuple[tuple[str, str, int], ...]
    missing: tuple[str, ...]

    @property
    def rule_ids(self) -> frozenset[str]:
        return frozenset(rule for rule, _, _ in self.rules)


def _signature(result: dict[str, Any], phase: str) -> Verdict:
    counts: dict[tuple[str, str], int] = {}
    for finding in result.get("findings", []):
        if isinstance(finding, dict):
            enriched = enrich_finding_mapping(phase, finding)
            key = (str(enriched.get("rule_id") or enriched.get("category") or ""), str(finding.get("severity", "")))
            counts[key] = counts.get(key, 0) + 1
    missing = result.get("missing", [])
    return Verdict(
        status=str(result.get("status", "")),
        score=float(result.get("score", 0.0) or 0.0),
        rules=tuple(sorted((rule, severity, count) for (rule, severity), count in counts.items())),
        missing=tuple(sorted(str(item) for item in missing)) if isinstance(missing, list) else (),
    )


def _drift_record(rewrite: str, label: str, before: Verdict, after: Verdict) -> dict[str, Any]:
    record: dict[str, Any] = {
        "rewrite": rewrite,
        "fixture": label,
        "status": {"before": before.status, "after": after.status},
        "lost": sorted(before.rule_ids - after.rule_ids),
        "gained": sorted(after.rule_ids - before.rule_ids),
    }
    other: dict[str, Any] = {}
    if before.score != after.score:
        other["score"] = {"before": before.score, "after": after.score}
    if before.rules != after.rules and before.rule_ids == after.rule_ids:
        other["findings"] = {"before": [list(item) for item in before.rules], "after": [list(item) for item in after.rules]}
    if before.missing != after.missing:
        other["missing"] = {"before": list(before.missing), "after": list(after.missing)}
    if other:
        record["other"] = other
    return record


def _span_errors(result: dict[str, Any], text: str, context: str) -> list[str]:
    """Evidence spans that do not index the text the variant was audited on."""
    bodies = {"request": text, "context": context}
    combined = len(text) + (1 + len(context) if text and context else 0)
    errors: list[str] = []
    details = result.get("details")
    if not isinstance(details, dict):
        return errors
    trace = details.get("logical_trace")
    for fact in trace.get("facts", []) if isinstance(trace, dict) else []:
        for span in fact.get("evidence", []) if isinstance(fact, dict) else []:
            start, end, source = span.get("start"), span.get("end"), span.get("source")
            if isinstance(start, int) and isinstance(end, int):
                limit = len(bodies.get(str(source), ""))
                if not 0 <= start < end <= limit:
                    errors.append(f"fact {fact.get('name')}: span {start}-{end} outside {source} (length {limit})")
    relation = details.get("requirement_relation_summary")
    for check in relation.get("checks", []) if isinstance(relation, dict) else []:
        for span in check.get("evidence_spans", []) if isinstance(check, dict) else []:
            start, end = span.get("start"), span.get("end")
            if isinstance(start, int) and isinstance(end, int) and not 0 <= start < end <= combined:
                errors.append(f"relation {check.get('check_id')}: span {start}-{end} outside the input (length {combined})")
    return errors


def _rerun(spec: dict[str, Any], expected_path: Path, text: str) -> dict[str, Any]:
    variant = {key: value for key, value in spec.items() if key != "input"}
    variant["text"] = text
    return _run_fixture(variant, expected_path)


# The fewest rewrite-versus-fixture comparisons the repository's own tree must
# yield. A tree that silently stops being replayed (an empty directory, a skipped
# phase) lowers the count and fails the check instead of reporting a vacuous pass.
MINIMUM_CHECKED_COMPARISONS = 800


def _is_default_root(root: Path) -> bool:
    try:
        return root.resolve() == Path(DEFAULT_FIXTURE_ROOT).resolve()
    except OSError:
        return False


def evaluate_invariance(root: str | Path = DEFAULT_FIXTURE_ROOT, *, minimum_checked: int | None = None) -> dict[str, Any]:
    """Replay every fixture under every applicable rewrite and report verdict drift.

    A rewrite that leaves the text unchanged proves nothing, so it is counted as
    ``identity`` and excluded from ``checked``.
    """
    fixture_root = Path(root)
    if not fixture_root.is_dir():
        return {"passed": False, "error": f"fixture root is not a directory: {fixture_root}"}
    per_rewrite = {spec.name: {"checked": 0, "stable": 0, "drifted": 0, "identity": 0} for spec in REWRITES}
    unexpected: list[dict[str, Any]] = []
    known: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    seen_known: set[tuple[str, str]] = set()
    fixtures = 0

    for expected_path in sorted(fixture_root.rglob("*.expected.json")):
        spec = _load_spec(expected_path)
        label = expected_path.relative_to(fixture_root).as_posix()
        if spec.get("morphology") is not None:
            skipped.append(
                {"rewrite": "*", "fixture": label, "reason": "the recorded morphology analysis is bound to the exact input text"}
            )
            continue
        fixtures += 1
        phase = str(spec.get("phase", ""))
        text = _fixture_text(spec, expected_path)
        context = str(spec.get("context", "") or "")
        baseline = _signature(_run_fixture(spec, expected_path), phase)
        for rewrite in REWRITES:
            if not _applicable(rewrite, spec):
                continue
            skip_reason = _structural_rewrite_skip_reason(rewrite, text)
            if skip_reason:
                skipped.append({"rewrite": rewrite.name, "fixture": label, "reason": skip_reason})
                continue
            rewritten = rewrite.apply(text)
            if rewritten == text:
                per_rewrite[rewrite.name]["identity"] += 1
                continue
            per_rewrite[rewrite.name]["checked"] += 1
            result = _rerun(spec, expected_path, rewritten)
            span_errors = _span_errors(result, rewritten, context)
            if span_errors:
                unexpected.append({"rewrite": rewrite.name, "fixture": label, "span_errors": span_errors})
            variant = _signature(result, phase)
            if variant == baseline:
                per_rewrite[rewrite.name]["stable"] += 1
                continue
            per_rewrite[rewrite.name]["drifted"] += 1
            record = _drift_record(rewrite.name, label, baseline, variant)
            expected = KNOWN_DRIFT.get((rewrite.name, label))
            if expected is None:
                unexpected.append(record)
            elif any(record[key] != expected[key] for key in ("status", "lost", "gained")) or record.get("other", {}) != expected.get("other", {}):
                unexpected.append({**record, "known_expectation_mismatch": expected})
            else:
                seen_known.add((rewrite.name, label))
                known.append({**record, "reason": expected["reason"]})

    stale = [
        {"rewrite": name, "fixture": label, "reason": expected["reason"]}
        for (name, label), expected in sorted(KNOWN_DRIFT.items())
        if (name, label) not in seen_known
    ]
    # An exception may excuse a changed finding, never a finding that vanished into a pass.
    hiding = [entry for entry in known if entry["status"]["after"] == "pass" and entry["status"]["before"] != "pass"]
    checked = sum(row["checked"] for row in per_rewrite.values())
    drifted = sum(row["drifted"] for row in per_rewrite.values())
    identity = sum(row["identity"] for row in per_rewrite.values())
    if minimum_checked is None:
        minimum_checked = MINIMUM_CHECKED_COMPARISONS if _is_default_root(fixture_root) else 1
    too_few = checked < minimum_checked
    return {
        "checked": checked,
        "stable": checked - drifted,
        "drifted": drifted,
        "identity": identity,
        "fixtures": fixtures,
        "minimum_checked": minimum_checked,
        "stability_rate": round((checked - drifted) / checked, 4) if checked else 0.0,
        "rewrites": per_rewrite,
        "unexpected_drift": unexpected,
        "known_drift": known,
        "known_drift_hiding_findings": hiding,
        "stale_known_drift": stale,
        "skipped": skipped,
        "too_few_comparisons": too_few,
        "passed": not unexpected and not stale and not hiding and not too_few,
    }


# --- field-deletion sensitivity -----------------------------------------------------


@dataclass(frozen=True)
class Silent:
    """A deletion that raises nothing by itself, and the evidence that explains why.

    The detectors match terms, so another field's wording can satisfy the
    obligation of the field that was deleted. That is a blind spot, not a pass,
    and a bare reason string would let it rot. Each entry is therefore checked
    twice: the single deletion must still raise nothing, and deleting the field
    *together with* ``also_remove`` must raise ``expected_rules`` (and leave
    ``expected_missing`` among the gaps). ``still_present`` names a term that
    must survive in the reduced text, for a field covered by wording that cannot
    be removed without removing the document itself.
    """

    reason: str
    also_remove: tuple[str, ...] = ()
    expected_rules: tuple[str, ...] = ()
    expected_missing: tuple[str, ...] = ()
    still_present: str = ""


@dataclass(frozen=True)
class AblationDocument:
    """A known-good document whose labelled fields are deleted one at a time.

    ``expectations`` maps a field label to the rule ids that must newly appear
    when that field is removed, or to a :class:`Silent` entry. ``split`` says how
    the document is cut into fields: ``lines``, ``sentences``, ``sections``
    (Markdown ``##`` blocks), or ``finish`` (sentences of the summary and of the
    evidence). ``unit_labels`` names an unlabelled sentence by its prefix.
    """

    document_id: str
    phase: str
    fixture: str
    expectations: dict[str, tuple[str, ...] | Silent | str]
    split: str = "lines"
    unit_labels: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class _Unit:
    label: str
    text: str
    part: str = "body"


def _sentences(text: str) -> list[str]:
    return [part for part in re.split(r"(?<=。)", text) if part.strip()]


def _label(field: str) -> str:
    match = re.match(r"\s*([^:：]{1,16})[:：]", field)
    return match.group(1).strip() if match else ""


def _units(document: AblationDocument, spec: dict[str, Any], text: str) -> list[_Unit]:
    def named(field: str) -> str:
        return _label(field) or next((label for prefix, label in document.unit_labels if field.strip().startswith(prefix)), "")

    if document.split == "sections":
        blocks = re.split(r"(?m)^(?=## )", text)
        units = [_Unit("", blocks[0])]
        units.extend(_Unit(block.split("\n", 1)[0].lstrip("# ").strip(), block) for block in blocks[1:])
        return units
    if document.split == "finish":
        evidence = str(spec.get("evidence", "") or "")
        return [_Unit(named(part), part, "body") for part in _sentences(text)] + [
            _Unit(named(part), part, "evidence") for part in _sentences(evidence)
        ]
    if document.split == "sentences":
        return [_Unit(named(part), part) for part in _sentences(text)]
    return [_Unit(named(line), line) for line in text.split("\n") if line.strip()]


def _reduced(document: AblationDocument, units: list[_Unit], removed: set[str]) -> tuple[str, str]:
    kept = [unit for unit in units if not (unit.label and unit.label in removed)]
    if document.split == "finish":
        return "".join(u.text for u in kept if u.part == "body"), "".join(u.text for u in kept if u.part == "evidence")
    joiner = "\n" if document.split == "lines" else ""
    return joiner.join(u.text for u in kept), ""


def _audit_for(document: AblationDocument, spec: dict[str, Any], reduced: tuple[str, str]) -> dict[str, Any]:
    text, evidence = reduced
    strict = bool(spec.get("strict", True))
    if document.phase == "audit_plan":
        return audit_plan(text, strict=strict)
    if document.phase == "finish_check":
        return finish_check(text, evidence=evidence, strict=strict)
    kind = "document" if spec.get("kind") == "document" else "requirement"
    return audit_request(text, strict=strict, input_kind=kind)


def _ids(result: dict[str, Any], phase: str) -> set[str]:
    return set(_signature(result, phase).rule_ids)


def _asserted_rules(documents: tuple[AblationDocument, ...]) -> set[str]:
    rules: set[str] = set()
    for document in documents:
        for expected in document.expectations.values():
            if isinstance(expected, Silent):
                rules.update(expected.expected_rules)
            elif isinstance(expected, tuple):
                rules.update(expected)
    return rules


def evaluate_sensitivity(
    documents: tuple[AblationDocument, ...] | None = None,
    root: str | Path = DEFAULT_FIXTURE_ROOT,
) -> dict[str, Any]:
    fixture_root = Path(root)
    selected = ABLATION_DOCUMENTS if documents is None else documents
    reports: list[dict[str, Any]] = []
    mismatches: list[dict[str, Any]] = []

    for document in selected:
        path = fixture_root / document.fixture
        if not path.is_file():
            mismatches.append({"document": document.document_id, "field": "", "ok": False, "note": f"fixture not found: {document.fixture}"})
            continue
        if path.suffix == ".json":
            spec = _load_spec(path)
            text = _fixture_text(spec, path)
        else:
            spec = {"strict": True}
            text = path.read_text(encoding="utf-8")
        units = _units(document, spec, text)
        base = _audit_for(document, spec, _reduced(document, units, set()))
        base_ids = _ids(base, document.phase)
        base_missing = set(base.get("missing", []))
        rows: list[dict[str, Any]] = []
        for label in dict.fromkeys(unit.label for unit in units if unit.label):
            result = _audit_for(document, spec, _reduced(document, units, {label}))
            raised = sorted(_ids(result, document.phase) - base_ids)
            expected = document.expectations.get(label)
            row: dict[str, Any] = {"field": label, "status": result.get("status"), "raised": raised, "expected": [], "ok": True}
            note = ""
            if expected is None:
                note = "no expectation recorded for this field"
            elif isinstance(expected, str):
                note = "a silent deletion needs a Silent entry with the fields to remove together and the rule it then raises"
            elif isinstance(expected, Silent):
                row["silent_because"] = expected.reason
                row["expected"] = list(expected.expected_rules)
                if raised:
                    note = "deletion now raises findings; record them"
                else:
                    note = _verify_silent(document, spec, units, label, expected, base_ids, base_missing)
            else:
                row["expected"] = list(expected)
                unraised = sorted(set(expected) - set(raised))
                if unraised:
                    note = f"expected rules not raised: {unraised}"
            if note:
                row["ok"] = False
                row["note"] = note
                mismatches.append({"document": document.document_id, **row})
            rows.append(row)
        unlisted = sorted(set(document.expectations) - {row["field"] for row in rows})
        for label in unlisted:
            mismatches.append({"document": document.document_id, "field": label, "ok": False, "note": "field not found in document"})
        reports.append(
            {
                "document": document.document_id,
                "phase": document.phase,
                "base_status": base.get("status"),
                "base_findings": sorted(base_ids),
                "fields": rows,
            }
        )
        if base_ids:
            mismatches.append(
                {"document": document.document_id, "field": "", "ok": False, "note": f"baseline is not clean: {sorted(base_ids)}"}
            )

    asserted = _asserted_rules(selected)
    catalog = len(RULES)
    minimum = MINIMUM_ASSERTED_RULES if documents is None else 0
    if len(asserted) < minimum:
        mismatches.append(
            {"document": "", "field": "", "ok": False, "note": f"only {len(asserted)} rules are asserted; at least {minimum} are required"}
        )
    return {
        "documents": reports,
        "asserted_rules": sorted(asserted),
        "asserted_rule_count": len(asserted),
        "catalog_rule_count": catalog,
        "minimum_asserted_rules": minimum,
        "mismatches": mismatches,
        "passed": not mismatches,
    }


def _verify_silent(
    document: AblationDocument,
    spec: dict[str, Any],
    units: list[_Unit],
    label: str,
    silent: Silent,
    base_ids: set[str],
    base_missing: set[str],
) -> str:
    known = {unit.label for unit in units if unit.label}
    unknown = sorted(set(silent.also_remove) - known)
    if unknown:
        return f"also_remove names fields that do not exist: {unknown}"
    reduced = _reduced(document, units, {label, *silent.also_remove})
    result = _audit_for(document, spec, reduced)
    problems: list[str] = []
    raised = _ids(result, document.phase) - base_ids
    missing_rules = sorted(set(silent.expected_rules) - raised)
    if missing_rules:
        problems.append(f"removing it together with {list(silent.also_remove)} did not raise {missing_rules}")
    missing_gaps = sorted(set(silent.expected_missing) - set(result.get("missing", [])))
    if missing_gaps:
        problems.append(f"removing it together with {list(silent.also_remove)} did not leave {missing_gaps} missing")
    if silent.still_present and silent.still_present not in "".join(reduced):
        problems.append(f"{silent.still_present!r} is no longer in the reduced text, so the stated cover is gone")
    if not (silent.expected_rules or silent.expected_missing or silent.still_present):
        problems.append("a silent entry must state what removing it together with other fields raises")
    return "; ".join(problems)


# The fewest distinct rules the ablation documents must assert. A field whose
# deletion is tested protects its rule; this keeps the table from shrinking quietly.
MINIMUM_ASSERTED_RULES = 30

_REST_OF_THE_PLAN = (
    "対象外", "成果物", "作業分解", "順序", "依存", "資源", "リスク", "検証", "妥当性", "判断主体", "確認点",
    "基準線", "戻し方", "証拠", "未確定",
)

ABLATION_DOCUMENTS: tuple[AblationDocument, ...] = (
    AblationDocument(
        document_id="plans/good",
        phase="audit_plan",
        fixture="plans/good.md",
        expectations={
            "目的": ("plan.objective.purpose_missing",),
            "対象外": ("plan.scope.non_goals_missing",),
            "成果物": ("plan.structure.required_field_missing",),
            "作業分解": ("plan.structure.work_package_decomposition_missing",),
            "手順": Silent(
                "the objective line itself contains 実装, a work-breakdown term",
                also_remove=_REST_OF_THE_PLAN,
                still_present="実装",
            ),
            "順序": ("plan.schedule.dependency_sequence_missing",),
            "依存": Silent("the sequence line also names a dependency", also_remove=("順序",), expected_missing=("dependencies",)),
            "資源": ("plan.resource.estimate_or_capacity_missing",),
            "リスク": ("plan.structure.required_field_missing",),
            "検証": Silent(
                "the steps, sequence, validation and check points also name a verification",
                also_remove=("妥当性", "手順", "確認点", "順序"),
                expected_rules=("plan.verification.plan_missing",),
            ),
            "妥当性": Silent(
                "the decision-maker line also names acceptance",
                also_remove=("判断主体",),
                expected_rules=("plan.validation.problem_fit_missing",),
            ),
            "判断主体": ("plan.validation.owner_missing",),
            "確認点": Silent(
                "the evidence line also names a progress check",
                also_remove=("証拠",),
                expected_missing=("progress_control",),
            ),
            "基準線": ("plan.control.baseline_or_metric_missing",),
            "戻し方": ("plan.risk.rollback_missing",),
            "証拠": ("plan.completion.evidence_missing",),
            "未確定": ("plan.uncertainty.unknowns_unstated",),
        },
    ),
    AblationDocument(
        document_id="requests/problem-mechanism-fit-good",
        phase="audit_request",
        fixture="requests/problem-mechanism-fit-good.expected.json",
        split="sentences",
        expectations={
            "利用者": Silent(
                "the scenario also names the stakeholder",
                also_remove=("シナリオ",),
                expected_rules=("req.stakeholder.source_missing",),
            ),
            "問題": Silent(
                "the stakeholder is named in the scenario and the user field",
                also_remove=("シナリオ", "利用者"),
                expected_rules=("req.stakeholder.source_missing",),
            ),
            "原因": ("req.solution.problem_mechanism_fit_missing",),
            "解決策": Silent(
                "the stakeholder is named in the scenario and the user field",
                also_remove=("シナリオ", "利用者"),
                expected_rules=("req.stakeholder.source_missing",),
            ),
            "目的": ("req.necessity.purpose_trace_missing",),
            "シナリオ": Silent(
                "the user field also names the stakeholder",
                also_remove=("利用者",),
                expected_rules=("req.stakeholder.source_missing",),
            ),
            "期待結果": Silent(
                "the stakeholder is named in the scenario and the user field",
                also_remove=("シナリオ", "利用者"),
                expected_rules=("req.stakeholder.source_missing",),
            ),
            "受入基準": ("req.quality.measurable_constraint_missing",),
            "検証方法": Silent(
                "the evidence line also describes the method",
                also_remove=("証拠",),
                expected_rules=("req.verification.method_detail_missing",),
            ),
            "証拠": Silent(
                "the verification-method line also describes the method",
                also_remove=("検証方法",),
                expected_rules=("req.verification.method_detail_missing",),
            ),
            "不合格条件": ("req.acceptance.rejection_condition_missing",),
            "対象外": ("req.scope.non_goals_missing",),
            "未確定": ("req.uncertainty.unknowns_unstated",),
            "優先度": ("req.priority.multiple_requirements_unprioritized",),
        },
    ),
    AblationDocument(
        document_id="finish/public-behavior-good",
        phase="finish_check",
        fixture="finish/public-behavior-good.expected.json",
        split="finish",
        unit_labels=(("代表 CLI 実行済み", "代表実行"),),
        expectations={
            "完了要約": Silent(
                "the acceptance receipt and criterion carry the completion claim",
                also_remove=("受入証拠", "完了条件"),
                expected_rules=("finish.validation.acceptance_evidence_missing",),
            ),
            "完了条件": Silent(
                "the acceptance receipt also states what was achieved",
                also_remove=("受入証拠",),
                expected_rules=("finish.validation.acceptance_evidence_missing",),
            ),
            "公開挙動": Silent(
                "the acceptance receipt describes the public behavior",
                also_remove=("受入証拠", "完了条件"),
                expected_rules=("finish.validation.acceptance_evidence_missing",),
            ),
            "残リスク": ("finish.risk.residual_risk_missing",),
            "受入証拠": Silent(
                "the completion criterion also reads as acceptance",
                also_remove=("完了条件",),
                expected_rules=("finish.validation.acceptance_evidence_missing",),
            ),
            "代表実行": Silent(
                "the acceptance receipt also records the command run",
                also_remove=("受入証拠",),
                expected_rules=("finish.evidence.tests_missing", "finish.implementation.behavior_evidence_missing"),
            ),
        },
    ),
    AblationDocument(
        document_id="documents/readme-good",
        phase="audit_request",
        fixture="documents/readme-good.expected.json",
        split="sections",
        expectations={
            "Overview": ("doc.structure.required_section_missing",),
            "Status": Silent(
                "the output section also describes the contract",
                also_remove=("Output Shape",),
                expected_rules=("doc.contract.output_fields_thin", "doc.structure.optional_section_missing"),
            ),
            "When To Use": ("doc.structure.optional_section_missing",),
            "CLI": ("doc.usage.example_missing",),
            "Output Shape": Silent(
                "the status section also describes the output",
                also_remove=("Status",),
                expected_rules=("doc.contract.output_fields_thin", "doc.structure.optional_section_missing"),
            ),
            "Limitations": Silent(
                "the status section also states the limits",
                also_remove=("Status",),
                expected_rules=("doc.structure.required_section_missing",),
            ),
        },
    ),
)


def evaluate_metamorphic(root: str | Path = DEFAULT_FIXTURE_ROOT) -> dict[str, Any]:
    invariance = evaluate_invariance(root)
    if "error" in invariance:
        return {
            "calibration_scope": "repository fixtures only; not field accuracy and not acceptance",
            "error": invariance["error"],
            "passed": False,
        }
    sensitivity = evaluate_sensitivity(root=root)
    return {
        "calibration_scope": "repository fixtures only; not field accuracy and not acceptance",
        "invariance": invariance,
        "sensitivity": sensitivity,
        "passed": invariance["passed"] and sensitivity["passed"],
    }
