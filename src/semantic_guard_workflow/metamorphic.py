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

from semantic_guard_workflow.core import audit_plan, audit_request
from semantic_guard_workflow.evaluation import DEFAULT_FIXTURE_ROOT, _fixture_text, _load_spec, _run_fixture
from semantic_guard_workflow.rule_mapping import enrich_finding_mapping

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


def _crlf(text: str) -> str:
    return text.replace("\n", "\r\n")


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
    RewriteSpec("crlf", "CRLF line endings", _crlf, diff_safe=True),
    RewriteSpec("trailing_whitespace", "two trailing spaces on every line", _trailing_whitespace, diff_safe=True),
    RewriteSpec("bold_label", "Markdown bold around field labels", _bold_label),
    RewriteSpec("bullet_markers", "'- ' list markers", _prefix("- ")),
    RewriteSpec("numbered_markers", "'n. ' list markers", _numbered),
    RewriteSpec("heading_markers", "'## ' heading markers", _prefix("## "), prose_only=True),
    RewriteSpec("blockquote_markers", "'> ' quote markers", _prefix("> ")),
    RewriteSpec("rotated_lines", "first line moved to the end", _rotate_lines, prose_only=True),
    RewriteSpec("sentence_newlines", "a line break after every sentence", _sentence_newlines, prose_only=True),
)

# (rewrite, fixture label) -> why the verdict is allowed to move. An entry that
# no longer drifts is reported as stale so the table shrinks as detectors improve.
KNOWN_DRIFT: dict[tuple[str, str], str] = {
    (
        "fullwidth_ascii",
        "requests/verification-target-mismatch.expected.json",
    ): "the relation audit receives the caller's text unchanged because its spans and morphology binding refer to that text",
    (
        "decomposed_kana",
        "requests/verification-target-mismatch.expected.json",
    ): "the relation audit receives the caller's text unchanged because its spans and morphology binding refer to that text",
    (
        "halfwidth_katakana",
        "requests/verification-target-mismatch.expected.json",
    ): "the relation audit receives the caller's text unchanged because its spans and morphology binding refer to that text",
}


def _applicable(spec: RewriteSpec, fixture: dict[str, Any]) -> bool:
    phase = fixture.get("phase")
    if phase == "audit_diff":
        return spec.diff_safe
    if phase not in _PROSE_PHASES:
        return False
    if spec.prose_only and fixture.get("kind") == "document":
        return False
    return True


def _signature(result: dict[str, Any], phase: str) -> tuple[str, frozenset[str]]:
    identifiers: set[str] = set()
    for finding in result.get("findings", []):
        if isinstance(finding, dict):
            enriched = enrich_finding_mapping(phase, finding)
            identifiers.add(str(enriched.get("rule_id") or enriched.get("category") or ""))
    return str(result.get("status", "")), frozenset(identifiers)


def _rerun(spec: dict[str, Any], expected_path: Path, text: str) -> dict[str, Any]:
    variant = {key: value for key, value in spec.items() if key != "input"}
    variant["text"] = text
    return _run_fixture(variant, expected_path)


def evaluate_invariance(root: str | Path = DEFAULT_FIXTURE_ROOT) -> dict[str, Any]:
    """Replay every fixture under every applicable rewrite and report verdict drift."""
    fixture_root = Path(root)
    per_rewrite = {spec.name: {"checked": 0, "stable": 0, "drifted": 0} for spec in REWRITES}
    unexpected: list[dict[str, Any]] = []
    known: list[dict[str, Any]] = []
    seen_known: set[tuple[str, str]] = set()

    for expected_path in sorted(fixture_root.rglob("*.expected.json")):
        spec = _load_spec(expected_path)
        if spec.get("morphology") is not None:
            continue  # the recorded analysis is bound to the exact input text
        label = expected_path.relative_to(fixture_root).as_posix()
        phase = str(spec.get("phase", ""))
        text = _fixture_text(spec, expected_path)
        baseline = _signature(_run_fixture(spec, expected_path), phase)
        for rewrite in REWRITES:
            if not _applicable(rewrite, spec):
                continue
            per_rewrite[rewrite.name]["checked"] += 1
            variant = _signature(_rerun(spec, expected_path, rewrite.apply(text)), phase)
            if variant == baseline:
                per_rewrite[rewrite.name]["stable"] += 1
                continue
            per_rewrite[rewrite.name]["drifted"] += 1
            record = {
                "rewrite": rewrite.name,
                "fixture": label,
                "status": {"before": baseline[0], "after": variant[0]},
                "lost": sorted(baseline[1] - variant[1]),
                "gained": sorted(variant[1] - baseline[1]),
            }
            reason = KNOWN_DRIFT.get((rewrite.name, label))
            if reason is None:
                unexpected.append(record)
            else:
                seen_known.add((rewrite.name, label))
                known.append({**record, "reason": reason})

    stale = [
        {"rewrite": name, "fixture": label, "reason": reason}
        for (name, label), reason in sorted(KNOWN_DRIFT.items())
        if (name, label) not in seen_known
    ]
    checked = sum(row["checked"] for row in per_rewrite.values())
    drifted = sum(row["drifted"] for row in per_rewrite.values())
    return {
        "checked": checked,
        "stable": checked - drifted,
        "drifted": drifted,
        "stability_rate": round((checked - drifted) / checked, 4) if checked else 0.0,
        "rewrites": per_rewrite,
        "unexpected_drift": unexpected,
        "known_drift": known,
        "stale_known_drift": stale,
        "passed": not unexpected and not stale,
    }


# --- field-deletion sensitivity -----------------------------------------------------


@dataclass(frozen=True)
class AblationDocument:
    """A known-good document whose labelled fields are deleted one at a time.

    ``expectations`` maps a field label to either the rule ids that must newly
    appear when that field is removed, or a reason string. A reason string
    records that the deletion currently raises nothing, typically because
    another field's wording also satisfies the obligation. Such an entry fails
    as soon as the deletion starts raising a finding, so the table is updated
    deliberately when a detector improves.
    """

    document_id: str
    phase: str
    fixture: str
    expectations: dict[str, tuple[str, ...] | str]
    sentence_split: bool = False


def _fields(text: str, sentence_split: bool) -> list[str]:
    if not sentence_split:
        return [line for line in text.split("\n") if line.strip()]
    return [part for part in re.split(r"(?<=。)", text) if part.strip()]


def _label(field: str) -> str:
    match = re.match(r"\s*([^:：]{1,16})[:：]", field)
    return match.group(1).strip() if match else ""


def _audit_for(phase: str, spec: dict[str, Any], text: str) -> dict[str, Any]:
    if phase == "audit_plan":
        return audit_plan(text, strict=bool(spec.get("strict", True)))
    return audit_request(text, strict=bool(spec.get("strict", True)))


def _ids(result: dict[str, Any], phase: str) -> set[str]:
    return set(_signature(result, phase)[1])


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
        if path.suffix == ".json":
            spec = _load_spec(path)
            text = _fixture_text(spec, path)
        else:
            spec = {"strict": True}
            text = path.read_text(encoding="utf-8")
        base = _audit_for(document.phase, spec, text)
        base_ids = _ids(base, document.phase)
        fields = _fields(text, document.sentence_split)
        joiner = "" if document.sentence_split else "\n"
        rows: list[dict[str, Any]] = []
        for index, field in enumerate(fields):
            label = _label(field)
            if not label:
                continue
            reduced = joiner.join(part for position, part in enumerate(fields) if position != index)
            result = _audit_for(document.phase, spec, reduced)
            raised = sorted(_ids(result, document.phase) - base_ids)
            expected = document.expectations.get(label)
            silent_because = ""
            if expected is None:
                ok, note = False, "no expectation recorded for this field"
            elif isinstance(expected, str):
                silent_because = expected
                ok, note = not raised, ("deletion now raises findings; record them" if raised else "")
            else:
                missing = sorted(set(expected) - set(raised))
                ok, note = not missing, (f"expected rules not raised: {missing}" if missing else "")
            row = {
                "field": label,
                "status": result.get("status"),
                "raised": raised,
                "expected": [] if isinstance(expected, str) or expected is None else list(expected),
                "ok": ok,
            }
            if silent_because:
                row["silent_because"] = silent_because
            if note:
                row["note"] = note
                mismatches.append({"document": document.document_id, **row})
            rows.append(row)
        unlisted = sorted(set(document.expectations) - {row["field"] for row in rows})
        for label in unlisted:
            mismatches.append({"document": document.document_id, "field": label, "ok": False, "note": "field not found in document"})
        reports.append(
            {
                "document": document.document_id,
                "base_status": base.get("status"),
                "base_findings": sorted(base_ids),
                "fields": rows,
            }
        )
        if base_ids:
            mismatches.append(
                {"document": document.document_id, "field": "", "ok": False, "note": f"baseline is not clean: {sorted(base_ids)}"}
            )

    return {"documents": reports, "mismatches": mismatches, "passed": not mismatches}


_COVERED_BY_OTHER_FIELDS = "the obligation is also satisfied by wording in another field; the detector matches terms, not field labels"

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
            "手順": _COVERED_BY_OTHER_FIELDS,
            "順序": ("plan.schedule.dependency_sequence_missing",),
            "依存": _COVERED_BY_OTHER_FIELDS,
            "資源": ("plan.resource.estimate_or_capacity_missing",),
            "リスク": ("plan.structure.required_field_missing",),
            "検証": _COVERED_BY_OTHER_FIELDS,
            "妥当性": _COVERED_BY_OTHER_FIELDS,
            "判断主体": ("plan.validation.owner_missing",),
            "確認点": _COVERED_BY_OTHER_FIELDS,
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
        sentence_split=True,
        expectations={
            "利用者": _COVERED_BY_OTHER_FIELDS,
            "問題": _COVERED_BY_OTHER_FIELDS,
            "原因": ("req.solution.problem_mechanism_fit_missing",),
            "解決策": _COVERED_BY_OTHER_FIELDS,
            "目的": ("req.necessity.purpose_trace_missing",),
            "シナリオ": _COVERED_BY_OTHER_FIELDS,
            "期待結果": _COVERED_BY_OTHER_FIELDS,
            "受入基準": ("req.quality.measurable_constraint_missing",),
            "検証方法": _COVERED_BY_OTHER_FIELDS,
            "証拠": _COVERED_BY_OTHER_FIELDS,
            "不合格条件": ("req.acceptance.rejection_condition_missing",),
            "対象外": ("req.scope.non_goals_missing",),
            "未確定": ("req.uncertainty.unknowns_unstated",),
            "優先度": ("req.priority.multiple_requirements_unprioritized",),
        },
    ),
)


def evaluate_metamorphic(root: str | Path = DEFAULT_FIXTURE_ROOT) -> dict[str, Any]:
    invariance = evaluate_invariance(root)
    sensitivity = evaluate_sensitivity(root=root)
    return {
        "calibration_scope": "repository fixtures only; not field accuracy and not acceptance",
        "invariance": invariance,
        "sensitivity": sensitivity,
        "passed": invariance["passed"] and sensitivity["passed"],
    }
