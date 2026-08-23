"""Closed public audit for bounded scalar and non-scalar direction binding.

This module deliberately remains independent from the functional-requirement
obligation profile.  It shares one source-aligned morphology attempt between
two deterministic detectors, projects one primary rule evaluation, and never
grants the morphology provider assertion or acceptance authority.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from functools import lru_cache
import hashlib
import json
import re
from typing import Any, Iterable, Mapping

from jsonschema import Draft202012Validator, FormatChecker, ValidationError

from ._version import __version__
from .legacy_runner import validate_requirement_input_size
from .providers import (
    AnalysisAttempt,
    AnalysisProvider,
    AnalysisSpan,
    ProviderAuthority,
    ProviderRequest,
    run_provider,
)
from .public_contract import load_public_schema
from .decision_frame_scales import all_comparison_terms
from .request_decision_frame import (
    PRECONDITION_ORDER_DIRECTION_RULE_ID,
    audit_precondition_sufficiency,
)
from .request_direction_binding import audit_direction_binding_sufficiency
from .request_direction_binding import direction_binding_contract_violations


SCHEMA_VERSION = "semantic-guard-direction-binding-audit/v1"
PUBLIC_SLICE_ENTITY_ID = "245dad95-accf-581c-8b0a-ae1c1f557de4"
_REQUESTED_CAPABILITIES = ("tokenization", "lemma", "part_of_speech")
_LIMITATIONS = (
    "Only registered Japanese scalar and explicit direction-space successor forms are checked.",
    "Morphology is source-aligned signal_only material and cannot assert a direction.",
    "Provider identity, token lemmas, and parts of speech are declared receipt material, not authenticated or re-executed by validation.",
    "Numeric projections are auxiliary evidence and never alter the primary rule evaluation.",
    "Quoted, historical, hypothetical, negated, cross-axis, and indirect expressions are bounded out.",
    "Workflow pass is not human acceptance and does not establish unrestricted language coverage.",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _source_text(text: str, context: str) -> tuple[str, int]:
    if not isinstance(text, str) or not isinstance(context, str):
        raise TypeError("text and context must be strings")
    separator = "\n" if text and context else ""
    combined = f"{text}{separator}{context}"
    validate_requirement_input_size(combined)
    return combined, len(text) + len(separator)


def _split_mode(provider: AnalysisProvider | None, attempt: AnalysisAttempt) -> str:
    declared = str(getattr(provider, "split_mode", "") or "")
    token_modes = {
        str(token.features.get("split_mode", ""))
        for token in attempt.tokens
        if token.features.get("split_mode")
    }
    if len(token_modes) > 1:
        return ""
    observed = next(iter(token_modes), "")
    if declared and observed and declared != observed:
        return ""
    selected = declared or observed
    return selected if selected in {"A", "B", "C"} else ""


def _full_coverage(attempt: AnalysisAttempt, source_length: int) -> bool:
    if any(
        (span.role or "document") != "document"
        or span.start < 0
        or span.end < span.start
        or span.end > source_length
        for span in attempt.covered_spans
    ):
        return False
    if source_length == 0:
        return True
    intervals = sorted(
        (span.start, span.end)
        for span in attempt.covered_spans
        if span.start < span.end
    )
    cursor = 0
    for start, end in intervals:
        if start > cursor:
            return False
        cursor = max(cursor, end)
    return cursor >= source_length


def _execution_status(
    attempt: AnalysisAttempt,
    *,
    source_length: int,
    split_mode: str,
) -> str:
    if attempt.status == "not_configured":
        return "not_configured"
    if attempt.status == "partial":
        return "partial"
    if attempt.status != "ok":
        return "failed"
    if (
        not all(
            str(value).strip()
            for value in (
                attempt.provider_id,
                attempt.provider_version,
                attempt.resource_version,
            )
        )
        or
        set(attempt.fulfilled_capabilities) != set(_REQUESTED_CAPABILITIES)
        or not _full_coverage(attempt, source_length)
        or split_mode not in {"A", "B", "C"}
    ):
        return "invalid"
    return "executed"


def _semantic_ir(
    text: str,
    context: str,
    source_text: str,
    attempt: AnalysisAttempt,
    *,
    execution_status: str,
    split_mode: str,
) -> dict[str, Any]:
    detector_status = {
        "executed": "executed",
        "not_configured": "not_configured",
        "partial": "failed",
        "failed": "failed",
        "invalid": "failed",
    }[execution_status]
    diagnostics = list(attempt.diagnostics)
    if execution_status == "partial":
        diagnostics.append("provider_partial_result_not_actionable")
    elif execution_status == "invalid":
        diagnostics.append("provider_execution_contract_invalid")
    receipt = {
        "stage": "morphology",
        "status": detector_status,
        "authority": "signal_only",
        "provider_id": attempt.provider_id,
        "provider_version": attempt.provider_version,
        "resource_version": attempt.resource_version,
        "split_mode": split_mode,
        "diagnostics": diagnostics,
    }
    tokens = [
        {
            "surface": token.surface,
            "lemma": token.lemma,
            "normalized": token.normalized,
            "pos": list(token.part_of_speech),
            "start": token.start,
            "end": token.end,
        }
        for token in attempt.tokens
    ]
    return {
        "text": text,
        "context": context,
        "source_text": source_text,
        "attempts": [receipt],
        "supports": [
            {
                "tier": "morphology",
                "authority": "signal_only",
                "metadata": {"tokens": tokens},
            }
        ],
    }


def _surface_probe_tokens(source_text: str) -> list[dict[str, Any]]:
    """Build bounded lexical signals used only to detect morphology vetoes.

    The probe never establishes a direction.  It asks whether fixed source
    grammar would have produced a candidate if a provider had not changed a
    registered ``次`` lemma or comparison-term part of speech.
    """

    separators = {
        "次",
        "の",
        "、",
        "，",
        ",",
        "。",
        "！",
        "？",
        "!",
        "?",
        ";",
        "；",
        ":",
        "：",
        "(",
        ")",
        "（",
        "）",
        "「",
        "」",
        "『",
        "』",
    }
    comparison_terms = set(all_comparison_terms())
    alternatives = sorted(comparison_terms | separators, key=len, reverse=True)
    matcher = re.compile(
        "(" + "|".join(re.escape(item) for item in alternatives) + r"|\s+)"
    )
    pieces: list[tuple[int, int, str]] = []
    cursor = 0
    for match in matcher.finditer(source_text):
        if cursor < match.start():
            pieces.append((cursor, match.start(), source_text[cursor : match.start()]))
        pieces.append((match.start(), match.end(), match.group(0)))
        cursor = match.end()
    if cursor < len(source_text):
        pieces.append((cursor, len(source_text), source_text[cursor:]))
    if len(pieces) > 4096:
        return []

    tokens: list[dict[str, Any]] = []
    for start, end, surface in pieces:
        if surface.isspace():
            pos = ["空白"]
        elif surface in separators - {"次", "の"}:
            pos = ["補助記号"]
        elif surface == "の":
            pos = ["助詞"]
        elif surface in comparison_terms:
            pos = ["形容詞"]
        else:
            pos = ["名詞"]
        tokens.append(
            {
                "surface": surface,
                "lemma": surface,
                "normalized": surface,
                "pos": pos,
                "start": start,
                "end": end,
            }
        )
    return tokens


def _surface_probe_summaries(
    text: str,
    context: str,
    source_text: str,
    attempt: AnalysisAttempt,
    *,
    split_mode: str,
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    tokens = _surface_probe_tokens(source_text)
    if source_text and not tokens:
        return None
    receipt = {
        "stage": "morphology",
        "status": "executed",
        "authority": "signal_only",
        "provider_id": attempt.provider_id,
        "provider_version": attempt.provider_version,
        "resource_version": attempt.resource_version,
        "split_mode": split_mode,
        "diagnostics": [],
    }
    ir = {
        "text": text,
        "context": context,
        "source_text": source_text,
        "attempts": [receipt],
        "supports": [
            {
                "tier": "morphology",
                "authority": "signal_only",
                "metadata": {"tokens": tokens},
            }
        ],
    }
    scalar = _normalize_unsafe_source_scope(
        _normalize_unknown_scalar_direction(
            audit_precondition_sufficiency(ir),
            source_text,
        ),
        source_text,
    )
    non_scalar = _normalize_unsafe_source_scope(
        audit_direction_binding_sufficiency(ir),
        source_text,
    )
    return scalar, non_scalar


def _frames(summary: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    value = summary.get("frames", [])
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _normalize_unknown_scalar_direction(
    summary: dict[str, Any], source_text: str
) -> dict[str, Any]:
    """Do not mislabel an unsupported attached order phrase as mere absence."""

    frames = _frames(summary)
    if len(frames) != 1:
        return summary
    frame = frames[0]
    binding = frame.get("direction_binding", {})
    span = frame.get("source_span", {})
    if not isinstance(binding, Mapping) or not isinstance(span, Mapping):
        return summary
    if binding.get("status") != "missing" or binding.get("accepted_evidence"):
        return summary
    start = span.get("start")
    end = span.get("end")
    if not isinstance(start, int) or not isinstance(end, int):
        return summary
    clause = source_text[start:end]
    if re.search(
        r"[^、，,。！？!?\n\r]{1,48}順[^、，,。！？!?\n\r]{0,24}"
        r"(?:並べ|整列|ソート)(?:た|る|した|する)?\s*"
        r"(?:とき|時|場合|と|なら)",
        clause,
    ) is None:
        return summary
    normalized = deepcopy(summary)
    normalized["status"] = "indeterminate"
    normalized["derivation_status"] = "blocked_by_unknown"
    normalized["frames"] = []
    normalized["unknown_reasons"] = ["unsupported_scalar_direction_expression"]
    normalized["candidate_operation_count"] = 1
    return normalized


def _frame_has_unsafe_source_scope(
    frame: Mapping[str, Any], source_text: str
) -> bool:
    span = frame.get("source_span", {})
    if not isinstance(span, Mapping):
        return True
    start = span.get("start")
    end = span.get("end")
    if not isinstance(start, int) or not isinstance(end, int) or not 0 <= start <= end <= len(source_text):
        return True

    line_start = source_text.rfind("\n", 0, start) + 1
    if re.match(r"^[ \t]{0,3}>", source_text[line_start:start]):
        return True

    asymmetric_quotes = (("「", "」"), ("『", "』"), ("“", "”"), ("‘", "’"))
    for opening, closing in asymmetric_quotes:
        depth = 0
        for index, character in enumerate(source_text):
            if character == opening:
                depth += 1
                if start <= index < end:
                    return True
            if depth and start <= index < end:
                return True
            if character == closing:
                if depth == 0 and start <= index < end:
                    return True
                depth = max(0, depth - 1)

    for marker in ('"', "'", "`"):
        inside = False
        escaped = False
        for index, character in enumerate(source_text):
            if character == "\\" and not escaped:
                escaped = True
                continue
            if character == marker and not escaped:
                inside = not inside
                if start <= index < end:
                    return True
            if inside and start <= index < end:
                return True
            escaped = False
    return False


def _indeterminate_summary(
    summary: Mapping[str, Any],
    *,
    reasons: Iterable[str],
    candidate_count: int | None = None,
) -> dict[str, Any]:
    normalized = deepcopy(dict(summary))
    normalized["status"] = "indeterminate"
    normalized["derivation_status"] = "blocked_by_unknown"
    normalized["frames"] = []
    existing = normalized.get("unknown_reasons", [])
    existing_reasons = (
        [str(item) for item in existing if str(item)]
        if isinstance(existing, list)
        else []
    )
    normalized["unknown_reasons"] = list(
        dict.fromkeys(
            [
                *existing_reasons,
                *(str(item) for item in reasons if str(item)),
            ]
        )
    )
    if candidate_count is not None:
        normalized["candidate_operation_count"] = candidate_count
    return normalized


def _normalize_unsafe_source_scope(
    summary: dict[str, Any], source_text: str
) -> dict[str, Any]:
    frames = _frames(summary)
    if not frames or not any(
        _frame_has_unsafe_source_scope(frame, source_text) for frame in frames
    ):
        return summary
    return _indeterminate_summary(
        summary,
        reasons=("quoted_block_or_unbalanced_source_scope",),
        candidate_count=len(frames),
    )


def _not_applicable_summary(summary: Mapping[str, Any]) -> dict[str, Any]:
    normalized = deepcopy(dict(summary))
    normalized["status"] = "not_applicable"
    normalized["derivation_status"] = "not_applicable"
    normalized["frames"] = []
    normalized.pop("candidate_operation_count", None)
    if normalized.get("schema_version") == "direction-binding-summary/v1":
        normalized["unknown_reasons"] = []
    else:
        normalized.pop("unknown_reasons", None)
    return normalized


def _canonical_uncertain_summary(
    probe: Mapping[str, Any],
    *,
    diagnostics: Iterable[str] = (),
    morphology_veto: bool = False,
) -> dict[str, Any]:
    if probe.get("status") == "indeterminate" and not _frames(probe):
        base = deepcopy(dict(probe))
    else:
        base = _not_applicable_summary(probe)
    reasons = [f"provider_diagnostic:{str(item)[:160]}" for item in diagnostics]
    if morphology_veto:
        reasons.append("morphology_signal_surface_candidate_unresolved")
    count = len(_frames(probe)) or (
        probe.get("candidate_operation_count")
        if isinstance(probe.get("candidate_operation_count"), int)
        else None
    )
    return _indeterminate_summary(base, reasons=reasons, candidate_count=count)


def _normalize_executed_summaries(
    scalar: dict[str, Any],
    non_scalar: dict[str, Any],
    probe: tuple[Mapping[str, Any], Mapping[str, Any]] | None,
    *,
    diagnostics: Iterable[str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    if probe is None:
        return scalar, non_scalar
    diagnostics_tuple = tuple(str(item) for item in diagnostics)
    normalized: list[dict[str, Any]] = []
    for actual, candidate in ((scalar, probe[0]), (non_scalar, probe[1])):
        veto = bool(_frames(candidate)) and not bool(_frames(actual))
        if diagnostics_tuple or veto:
            normalized.append(
                _canonical_uncertain_summary(
                    candidate,
                    diagnostics=diagnostics_tuple,
                    morphology_veto=veto,
                )
            )
        elif (
            candidate.get("status") == "indeterminate"
            and actual.get("status") == "not_applicable"
        ):
            normalized.append(deepcopy(dict(candidate)))
        else:
            normalized.append(actual)
    return normalized[0], normalized[1]


def _binding_status(frame: Mapping[str, Any]) -> str:
    binding = frame.get("direction_binding", {})
    return str(binding.get("status", "indeterminate")) if isinstance(binding, Mapping) else "indeterminate"


def _unknown_reasons(*summaries: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    for summary in summaries:
        values = summary.get("unknown_reasons", [])
        if isinstance(values, list):
            reasons.extend(str(item) for item in values if str(item))
        for frame in _frames(summary):
            values = frame.get("unknown_reasons", [])
            if isinstance(values, list):
                reasons.extend(str(item) for item in values if str(item))
    return list(dict.fromkeys(reasons))


def _reason_code(value: str) -> str:
    candidate = str(value)
    if candidate and len(candidate) <= 256 and all(
        (character.isascii() and character.isalnum()) or character in "._:/-"
        for character in candidate
    ):
        return candidate
    digest = hashlib.sha256(candidate.encode("utf-8")).hexdigest()[:24]
    return f"direction_binding_reason.{digest}"


def _stable_id(value: str, prefix: str) -> str:
    candidate = str(value)
    if candidate and len(candidate) <= 256 and all(
        (character.isascii() and character.isalnum()) or character in "._:/-"
        for character in candidate
    ):
        return candidate
    digest = hashlib.sha256(candidate.encode("utf-8")).hexdigest()[:24]
    return f"{prefix}.{digest}"


def _primary_evaluation(
    scalar: Mapping[str, Any],
    non_scalar: Mapping[str, Any],
    *,
    execution_status: str,
    source_region_end: int | None = None,
    surface_probe: tuple[Mapping[str, Any], Mapping[str, Any]] | None = None,
) -> tuple[dict[str, Any], str]:
    scalar_frames = _frames(scalar)
    non_scalar_frames = _frames(non_scalar)
    reasons = _unknown_reasons(scalar, non_scalar)

    source_region_violation = False
    if source_region_end is not None:
        frames_to_check = [*scalar_frames, *non_scalar_frames]
        if surface_probe is not None:
            frames_to_check.extend(
                [*_frames(surface_probe[0]), *_frames(surface_probe[1])]
            )
        for frame in frames_to_check:
            span = frame.get("source_span", {})
            if not isinstance(span, Mapping):
                source_region_violation = True
                break
            start = span.get("start")
            end = span.get("end")
            if (
                not isinstance(start, int)
                or isinstance(start, bool)
                or not isinstance(end, int)
                or isinstance(end, bool)
                or start < 0
                or end < start
                or end > source_region_end
            ):
                source_region_violation = True
                break

    summary_indeterminate = (
        scalar.get("status") == "indeterminate"
        or non_scalar.get("status") == "indeterminate"
    )
    morphology_veto = False
    if surface_probe is not None:
        probe_scalar, probe_non_scalar = surface_probe
        morphology_veto = any(
            (
                bool(_frames(probe)) and not bool(_frames(actual))
            )
            or (
                probe.get("status") == "indeterminate"
                and actual.get("status") == "not_applicable"
            )
            for probe, actual in (
                (probe_scalar, scalar),
                (probe_non_scalar, non_scalar),
            )
        )

    if execution_status == "invalid":
        state, emitter, workflow = "invalid", "none", "block"
        reasons = [*reasons, "provider_execution_contract_invalid"]
    elif execution_status != "executed":
        state, emitter, workflow = "indeterminate", "none", "warn"
        reasons = [*reasons, f"morphology_{execution_status}"]
    elif source_region_violation:
        state, emitter, workflow = "invalid", "none", "block"
        reasons = [*reasons, "primary_frame_outside_source_region"]
    elif scalar_frames and non_scalar_frames:
        state, emitter, workflow = "invalid", "none", "block"
        reasons = [*reasons, "multiple_primary_emitters"]
    elif summary_indeterminate and (scalar_frames or non_scalar_frames):
        state, emitter, workflow = "invalid", "none", "block"
        reasons = [*reasons, "detector_emission_indeterminate_conflict"]
    elif morphology_veto and (scalar_frames or non_scalar_frames):
        state, emitter, workflow = "invalid", "none", "block"
        reasons = [*reasons, "morphology_signal_suppressed_competing_candidate"]
    elif morphology_veto:
        state, emitter, workflow = "indeterminate", "none", "warn"
        reasons = [*reasons, "morphology_signal_surface_candidate_unresolved"]
    elif scalar_frames or non_scalar_frames:
        emitter = "scalar" if scalar_frames else "non_scalar"
        frame = (scalar_frames or non_scalar_frames)[0]
        binding_status = _binding_status(frame)
        state = {
            "bound": "satisfied",
            "missing": "gap",
            "conflict": "conflict",
            "indeterminate": "indeterminate",
        }.get(binding_status, "invalid")
        workflow = "pass" if state == "satisfied" else ("block" if state == "invalid" else "warn")
        if state in {"indeterminate", "invalid"} and not reasons:
            reasons.append(f"direction_binding_{binding_status}")
    elif summary_indeterminate:
        state, emitter, workflow = "indeterminate", "none", "warn"
        if not reasons:
            reasons.append("detector_summary_indeterminate")
    else:
        state, emitter, workflow = "not_applicable", "none", "pass"

    evaluation = {
        "state": state,
        "emitter": emitter,
        "needs_human_decision": state in {"gap", "conflict", "indeterminate", "invalid"},
        "authority": "deterministic_source_grammar",
        "basis_frame_ids": [
            str(frame.get("frame_id"))
            for frame in [*scalar_frames, *non_scalar_frames]
            if frame.get("frame_id")
        ]
        if emitter != "none"
        else [],
        "reason_codes": list(
            dict.fromkeys(_reason_code(item) for item in reasons)
        ),
        "numeric_evidence_role": "auxiliary_only_non_decisional",
    }
    return evaluation, workflow


def _execution_payload(
    attempt: AnalysisAttempt,
    *,
    status: str,
    split_mode: str,
    additional_diagnostics: Iterable[str] = (),
) -> dict[str, Any]:
    provider_ref = {
        "reference_kind": "ref",
        "entity_id": _stable_id(attempt.provider_id, "provider"),
        "label_hint": attempt.provider_id,
    }
    if attempt.provider_version:
        provider_ref["entity_version"] = attempt.provider_version
    return {
        "status": status,
        "authority": "signal_only",
        "provider_ref": provider_ref,
        "resource_version": attempt.resource_version,
        "split_mode": split_mode,
        "requested_capabilities": list(_REQUESTED_CAPABILITIES),
        "fulfilled_capabilities": list(attempt.fulfilled_capabilities),
        "covered_regions": [
            {
                "role": span.role or "document",
                "start": span.start,
                "end_exclusive": span.end,
            }
            for span in attempt.covered_spans
        ],
        "diagnostics": list(
            dict.fromkeys([*attempt.diagnostics, *additional_diagnostics])
        ),
    }


def _input_regions(text: str, context: str, context_start: int) -> list[dict[str, Any]]:
    regions = [
        {
            "region_id": "region.source_text",
            "role": "source_text",
            "coordinate_unit": "unicode_code_point",
            "start": 0,
            "end_exclusive": len(text),
        }
    ]
    if context:
        regions.append(
            {
                "region_id": "region.context",
                "role": "context",
                "coordinate_unit": "unicode_code_point",
                "start": context_start,
                "end_exclusive": context_start + len(context),
            }
        )
    return regions


def _audit_id(payload: Mapping[str, Any]) -> str:
    material = {key: value for key, value in payload.items() if key != "audit_id"}
    encoded = json.dumps(
        material,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "audit.direction-binding." + hashlib.sha256(encoded).hexdigest()


def audit_direction_binding(
    text: str,
    *,
    context: str = "",
    morphology_provider: AnalysisProvider | None = None,
    recorded_at: str | None = None,
) -> dict[str, Any]:
    """Audit one bounded direction-open expression under the v1 sidecar contract."""

    source_text, context_start = _source_text(text, context)
    targets = (AnalysisSpan(0, len(source_text), "document"),) if source_text else ()
    request = ProviderRequest(
        text=source_text,
        target_spans=targets,
        reason_codes=(PRECONDITION_ORDER_DIRECTION_RULE_ID,),
        requested_capabilities=_REQUESTED_CAPABILITIES,
    )
    attempt = run_provider(morphology_provider, request, stage="morphology")
    split_mode = _split_mode(morphology_provider, attempt)
    execution_status = _execution_status(
        attempt,
        source_length=len(source_text),
        split_mode=split_mode,
    )
    ir = _semantic_ir(
        text,
        context,
        source_text,
        attempt,
        execution_status=execution_status,
        split_mode=split_mode,
    )
    scalar = _normalize_unsafe_source_scope(
        _normalize_unknown_scalar_direction(
            audit_precondition_sufficiency(ir),
            source_text,
        ),
        source_text,
    )
    non_scalar = _normalize_unsafe_source_scope(
        audit_direction_binding_sufficiency(ir),
        source_text,
    )
    surface_probe = (
        _surface_probe_summaries(
            text,
            context,
            source_text,
            attempt,
            split_mode=split_mode,
        )
        if execution_status == "executed"
        else None
    )
    if execution_status == "executed":
        scalar, non_scalar = _normalize_executed_summaries(
            scalar,
            non_scalar,
            surface_probe,
            diagnostics=attempt.diagnostics,
        )
    evaluation, workflow = _primary_evaluation(
        scalar,
        non_scalar,
        execution_status=execution_status,
        source_region_end=len(text),
        surface_probe=surface_probe,
    )
    public_execution_status = execution_status
    execution_diagnostics: list[str] = []
    if evaluation["state"] == "invalid" and execution_status == "executed":
        public_execution_status = "invalid"
        execution_diagnostics.extend(evaluation["reason_codes"])
    digest = hashlib.sha256(source_text.encode("utf-8")).hexdigest()
    timestamp = _now() if recorded_at is None else recorded_at
    if not isinstance(timestamp, str):
        raise TypeError("recorded_at must be an RFC 3339 date-time string")
    try:
        FormatChecker().check(timestamp, "date-time")
    except Exception as exc:
        raise ValueError("recorded_at must be an RFC 3339 date-time string") from exc
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "audit_id": "",
        "recorded_at": timestamp,
        "subject_ref": {
            "reference_kind": "ref",
            "entity_id": f"direction-binding-input.{digest[:24]}",
            "label_hint": "direction-binding audit input",
        },
        "source_digest": {"algorithm": "sha256", "value": digest},
        "input_regions": _input_regions(text, context, context_start),
        "producer_ref": {
            "reference_kind": "ref",
            "entity_id": PUBLIC_SLICE_ENTITY_ID,
            "label_hint": "direction-binding public slice",
            "entity_version": SCHEMA_VERSION,
        },
        "producer_version": __version__,
        "rule_id": PRECONDITION_ORDER_DIRECTION_RULE_ID,
        "execution": _execution_payload(
            attempt,
            status=public_execution_status,
            split_mode=split_mode,
            additional_diagnostics=execution_diagnostics,
        ),
        "decision_frame_summary": scalar,
        "direction_binding_summary": non_scalar,
        "primary_rule_evaluation": evaluation,
        "workflow_disposition": {
            "status": workflow,
            "reason_codes": list(evaluation["reason_codes"]),
            "semantics": "workflow_disposition_not_human_acceptance",
            "acceptance_effect": "none",
        },
        "limitations": list(_LIMITATIONS),
        "acceptance_owner": {
            "authority_boundary": "human_external_to_criterion_loom",
            "acceptance_status": "pending",
            "accepted": False,
        },
    }
    payload["audit_id"] = _audit_id(payload)
    validate_direction_binding_audit(payload, text=text, context=context)
    return payload


@lru_cache(maxsize=1)
def _validator() -> Draft202012Validator:
    schema = load_public_schema("direction-binding-audit")
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _walk(value: Any) -> Iterable[Any]:
    yield value
    if isinstance(value, Mapping):
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _reconstruct_input(
    payload: Mapping[str, Any], source_text: str
) -> tuple[str, str, int]:
    regions = payload.get("input_regions", [])
    if not isinstance(regions, list):
        raise ValidationError("input_regions must be a list")
    source_regions = [
        item for item in regions if isinstance(item, Mapping) and item.get("role") == "source_text"
    ]
    context_regions = [
        item for item in regions if isinstance(item, Mapping) and item.get("role") == "context"
    ]
    if len(source_regions) != 1 or len(context_regions) > 1:
        raise ValidationError("input regions must identify one source and at most one context")
    source_region = source_regions[0]
    source_end = source_region.get("end_exclusive")
    if (
        source_region.get("region_id") != "region.source_text"
        or source_region.get("start") != 0
        or not isinstance(source_end, int)
        or isinstance(source_end, bool)
        or not 0 <= source_end <= len(source_text)
    ):
        raise ValidationError("source_text input region is not canonical")
    text = source_text[:source_end]
    context = ""
    context_start = source_end
    if context_regions:
        context_region = context_regions[0]
        context_start = context_region.get("start")
        context_end = context_region.get("end_exclusive")
        expected_start = source_end + 1 if source_end else 0
        if (
            context_region.get("region_id") != "region.context"
            or context_start != expected_start
            or context_end != len(source_text)
            or (source_end and source_text[source_end:context_start] != "\n")
        ):
            raise ValidationError("context input region is not canonical")
        context = source_text[context_start:]
        if not context:
            raise ValidationError("empty context must not have an input region")
    elif source_end != len(source_text):
        raise ValidationError("source input region does not cover the supplied text")
    if regions != _input_regions(text, context, context_start):
        raise ValidationError("input regions are not the canonical text/context projection")
    return text, context, source_end


def _validate_source_local_coordinates(value: Any, source_text: str) -> None:
    for item in _walk(value):
        if not isinstance(item, Mapping) or "start" not in item:
            continue
        end_key = "end" if "end" in item else "end_exclusive" if "end_exclusive" in item else ""
        if not end_key:
            continue
        start = item.get("start")
        end = item.get(end_key)
        if (
            not isinstance(start, int)
            or isinstance(start, bool)
            or not isinstance(end, int)
            or isinstance(end, bool)
            or start < 0
            or end < start
            or end > len(source_text)
        ):
            raise ValidationError("source-local coordinate is outside the supplied text")
        if "excerpt" in item:
            excerpt = item.get("excerpt")
            if not isinstance(excerpt, str) or excerpt != source_text[start:end][:240]:
                raise ValidationError("source excerpt does not match its coordinates")
        if "surface" in item:
            surface = item.get("surface")
            if not isinstance(surface, str) or surface != source_text[start:end]:
                raise ValidationError("source surface does not match its coordinates")


def _semantic_scalar_projection(summary: Mapping[str, Any]) -> dict[str, Any]:
    projected = deepcopy(dict(summary))
    projected.pop("morphology", None)
    for frame in projected.get("frames", []):
        if isinstance(frame, dict):
            frame.pop("morphology_signal", None)
    return projected


def _probe_for_validation(
    text: str,
    context: str,
    source_text: str,
    execution: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    provider_ref = execution.get("provider_ref", {})
    if not isinstance(provider_ref, Mapping):
        return None
    attempt = AnalysisAttempt(
        stage="morphology",
        provider_id=str(provider_ref.get("label_hint", "")),
        provider_version=str(provider_ref.get("entity_version", "")),
        resource_version=str(execution.get("resource_version", "")),
        status="ok",
        authority=ProviderAuthority(),
        requested_capabilities=_REQUESTED_CAPABILITIES,
        fulfilled_capabilities=_REQUESTED_CAPABILITIES,
    )
    return _surface_probe_summaries(
        text,
        context,
        source_text,
        attempt,
        split_mode=str(execution.get("split_mode", "")),
    )


def validate_direction_binding_audit(
    payload: dict[str, Any],
    *,
    source_text: str | None = None,
    text: str | None = None,
    context: str | None = None,
) -> None:
    """Validate shape, source claims, declared provenance, and projection."""

    expected_text_context: tuple[str, str] | None = None
    if text is not None or context is not None:
        strict_text = "" if text is None else text
        strict_context = "" if context is None else context
        combined, _ = _source_text(strict_text, strict_context)
        if source_text is not None and source_text != combined:
            raise ValidationError("supplied source_text differs from text/context")
        source_text = combined
        expected_text_context = (strict_text, strict_context)

    _validator().validate(payload)
    if payload["audit_id"] != _audit_id(payload):
        raise ValidationError("audit_id does not bind the complete audit projection")
    if payload["producer_ref"] != {
        "reference_kind": "ref",
        "entity_id": PUBLIC_SLICE_ENTITY_ID,
        "label_hint": "direction-binding public slice",
        "entity_version": SCHEMA_VERSION,
    } or payload["producer_version"] != __version__:
        raise ValidationError("producer identity does not match this public slice")
    if payload["limitations"] != list(_LIMITATIONS):
        raise ValidationError("limitations are not the canonical public-slice limitations")
    if payload["acceptance_owner"] != {
        "authority_boundary": "human_external_to_criterion_loom",
        "acceptance_status": "pending",
        "accepted": False,
    }:
        raise ValidationError("machine output cannot alter the human acceptance boundary")

    evaluation = payload["primary_rule_evaluation"]
    scalar = payload["decision_frame_summary"]
    non_scalar = payload["direction_binding_summary"]
    scalar_frames = _frames(scalar)
    non_scalar_frames = _frames(non_scalar)
    emitter = evaluation["emitter"]
    if scalar_frames and non_scalar_frames:
        if evaluation["state"] != "invalid" or emitter != "none":
            raise ValidationError("multiple primary emitters must fail closed")
    elif emitter == "scalar" and (not scalar_frames or non_scalar_frames):
        raise ValidationError("scalar emitter does not match summary frames")
    elif emitter == "non_scalar" and (not non_scalar_frames or scalar_frames):
        raise ValidationError("non-scalar emitter does not match summary frames")
    elif emitter == "none" and (scalar_frames or non_scalar_frames) and evaluation["state"] != "invalid":
        raise ValidationError("an applicable summary must identify its sole emitter")

    expected_workflow_status = (
        "block"
        if evaluation["state"] == "invalid"
        else "pass"
        if evaluation["state"] in {"satisfied", "not_applicable"}
        else "warn"
    )
    expected_workflow = {
        "status": expected_workflow_status,
        "reason_codes": list(evaluation["reason_codes"]),
        "semantics": "workflow_disposition_not_human_acceptance",
        "acceptance_effect": "none",
    }
    if payload["workflow_disposition"] != expected_workflow:
        raise ValidationError("workflow disposition does not match the primary evaluation")

    for item in _walk(payload):
        if isinstance(item, Mapping) and "affects_primary_finding" in item:
            if item["affects_primary_finding"] is not False:
                raise ValidationError("numeric impact evidence cannot affect the primary finding")
    execution = payload["execution"]
    if execution["authority"] != "signal_only":
        raise ValidationError("morphology authority must remain signal_only")
    if execution["requested_capabilities"] != list(_REQUESTED_CAPABILITIES):
        raise ValidationError("requested morphology capabilities are not canonical")

    scalar_morphology = scalar["morphology"]
    non_scalar_morphology = non_scalar["morphology"]
    if scalar_morphology != non_scalar_morphology:
        raise ValidationError("both detectors must share one morphology receipt")
    provider_ref = execution["provider_ref"]
    provider_label = str(provider_ref["label_hint"])
    provider_version = str(provider_ref.get("entity_version", ""))
    expected_provider_ref = {
        "reference_kind": "ref",
        "entity_id": _stable_id(provider_label, "provider"),
        "label_hint": provider_label,
    }
    if provider_version:
        expected_provider_ref["entity_version"] = provider_version
    if provider_ref != expected_provider_ref:
        raise ValidationError("execution provider reference is not canonical")
    if scalar_morphology.get("provider_id", "") != provider_label:
        raise ValidationError("summary provider identity differs from execution")
    if scalar_morphology.get("provider_version", "") != provider_version:
        raise ValidationError("summary provider version differs from execution")
    if scalar_morphology.get("resource_version", "") != execution["resource_version"]:
        raise ValidationError("summary resource version differs from execution")
    if scalar_morphology.get("split_mode", "") != execution["split_mode"]:
        raise ValidationError("summary split mode differs from execution")

    if source_text is None:
        return

    digest = hashlib.sha256(source_text.encode("utf-8")).hexdigest()
    if payload["source_digest"] != {"algorithm": "sha256", "value": digest}:
        raise ValidationError("source_digest does not match the supplied source text")
    if payload["subject_ref"] != {
        "reference_kind": "ref",
        "entity_id": f"direction-binding-input.{digest[:24]}",
        "label_hint": "direction-binding audit input",
    }:
        raise ValidationError("subject identity does not match the supplied source")
    text, context, source_region_end = _reconstruct_input(payload, source_text)
    if expected_text_context is not None and (text, context) != expected_text_context:
        raise ValidationError("input region roles differ from supplied text/context")
    _validate_source_local_coordinates(payload, source_text)

    summary_morphology_status = str(scalar_morphology.get("status", ""))
    public_execution_status = str(execution["status"])
    raw_execution_status = (
        "executed"
        if public_execution_status == "invalid" and summary_morphology_status == "executed"
        else public_execution_status
    )
    expected_morphology_status = {
        "executed": "executed",
        "not_configured": "not_configured",
        "partial": "failed",
        "failed": "failed",
        "invalid": "failed",
    }[raw_execution_status]
    if summary_morphology_status != expected_morphology_status:
        raise ValidationError("summary morphology status differs from execution")

    shape_probe = _probe_for_validation(text, context, source_text, execution)
    surface_probe = shape_probe if raw_execution_status == "executed" else None
    preliminary_evaluation, _ = _primary_evaluation(
        scalar,
        non_scalar,
        execution_status=raw_execution_status,
        source_region_end=source_region_end,
        surface_probe=surface_probe,
    )
    projected_execution_diagnostics = (
        set(preliminary_evaluation["reason_codes"])
        if raw_execution_status == "executed"
        and preliminary_evaluation["state"] == "invalid"
        else set()
    )
    provider_diagnostics = [
        item
        for item in execution["diagnostics"]
        if item not in projected_execution_diagnostics
    ]
    if shape_probe is not None:
        for actual, candidate in ((scalar, shape_probe[0]), (non_scalar, shape_probe[1])):
            if _frames(actual):
                continue
            if raw_execution_status == "executed":
                veto = bool(_frames(candidate))
                expected_summary = (
                    _canonical_uncertain_summary(
                        candidate,
                        diagnostics=provider_diagnostics,
                        morphology_veto=veto,
                    )
                    if provider_diagnostics or veto
                    else deepcopy(dict(candidate))
                )
            else:
                expected_summary = _not_applicable_summary(candidate)
                expected_summary["morphology"] = deepcopy(dict(actual["morphology"]))
                if raw_execution_status != "not_configured":
                    expected_summary = _indeterminate_summary(
                        expected_summary,
                        reasons=("morphology_failed",),
                    )
            if actual != expected_summary:
                raise ValidationError("no-frame summary is not the canonical execution projection")
    if scalar_frames:
        if surface_probe is None or not _frames(surface_probe[0]):
            raise ValidationError("scalar frame is not reproducible from source grammar")
        if _semantic_scalar_projection(scalar) != _semantic_scalar_projection(surface_probe[0]):
            raise ValidationError("scalar summary is not reproducible from source grammar")
    if non_scalar_frames:
        context_start = (
            source_region_end + (1 if text and context else 0)
            if context
            else len(source_text)
        )
        violations = direction_binding_contract_violations(
            non_scalar,
            source_text,
            context_start=context_start,
        )
        if violations:
            raise ValidationError(
                "non-scalar summary is not source-reproducible: " + ",".join(violations)
            )

    expected_evaluation, expected_status = _primary_evaluation(
        scalar,
        non_scalar,
        execution_status=raw_execution_status,
        source_region_end=source_region_end,
        surface_probe=surface_probe,
    )
    if evaluation != expected_evaluation:
        raise ValidationError("primary evaluation is not reproducible from summaries")
    if expected_evaluation["state"] == "invalid" and raw_execution_status == "executed":
        expected_public_execution_status = "invalid"
    else:
        expected_public_execution_status = raw_execution_status
    if public_execution_status != expected_public_execution_status:
        raise ValidationError("public execution status does not match the replayed result")
    if payload["workflow_disposition"]["status"] != expected_status:
        raise ValidationError("workflow status does not match the replayed result")

    if raw_execution_status == "executed":
        if (
            not provider_label.strip()
            or not provider_version.strip()
            or not str(execution["resource_version"]).strip()
            or execution["split_mode"] not in {"A", "B", "C"}
            or set(execution["fulfilled_capabilities"]) != set(_REQUESTED_CAPABILITIES)
        ):
            raise ValidationError("executed morphology identity or capabilities are incomplete")
        covered = [
            AnalysisSpan(item["start"], item["end_exclusive"], item["role"])
            for item in execution["covered_regions"]
        ]
        if not _full_coverage(
            AnalysisAttempt(
                stage="morphology",
                provider_id=provider_label,
                provider_version=provider_version,
                resource_version=str(execution["resource_version"]),
                status="ok",
                authority=ProviderAuthority(),
                requested_capabilities=_REQUESTED_CAPABILITIES,
                fulfilled_capabilities=_REQUESTED_CAPABILITIES,
                covered_spans=tuple(covered),
            ),
            len(source_text),
        ):
            raise ValidationError("executed morphology does not cover the supplied source")


__all__ = [
    "PUBLIC_SLICE_ENTITY_ID",
    "SCHEMA_VERSION",
    "audit_direction_binding",
    "validate_direction_binding_audit",
]
