from __future__ import annotations

import re
from collections.abc import Mapping

from semantic_guard.direction_binding_core import resolve_direction_binding
from semantic_guard.direction_spaces import (
    DIRECTION_SPACE_SPECS,
    DirectionOptionSpec,
    DirectionSpaceSpec,
    direction_axis_ids,
    direction_option_ids,
)
from semantic_guard.request_decision_frame import (
    PRECONDITION_ORDER_DIRECTION_RULE_ID,
    _candidate_is_nonbinding,
    _clause_span,
    _context_start,
    _fenced_code_ranges,
    _morphology_attempt,
    _morphology_receipt,
    _morphology_tokens,
    _position_in_inline_quote,
    _position_in_ranges,
    _previous_non_ignorable,
    _question_clause_count,
    _reference_before,
    _selection_tail,
    _sequence,
    _space_token,
    _span,
    _token_evidence,
    _token_lemma,
    _token_surface,
    _validated_tokens,
    _value,
)

DIRECTION_BINDING_SCHEMA_VERSION = "direction-binding-summary/v1"

_SCOPE = "bounded_japanese_explicit_direction_space_successor_binding"
_MAX_PATTERNS = 8
_TARGET_RE = r"[A-Za-z0-9_\-一-龥々〆ヵヶぁ-んァ-ヴー]{1,16}?"
_EXPLICIT_TAIL_RE = re.compile(
    rf"^\s*の\s*(?P<target>{_TARGET_RE})(?P<selection>\s*(?:は|を).*)$"
)
_SOURCE_SUCCESSOR_RE = re.compile(
    r"(?P<reference>[^\s、，,;；:：=＝。！？!?「」『』（）()]{1,32})"
    r"\s*の\s*(?P<next>次)"
)
_TRAVERSAL_VERB_RE = r"(?:辿る|たどる|進む|走査する|読む|見る)"
_CONDITION_RE = r"(?:とき|時|場合|なら)"
_UNSAFE_DIRECTION_DISCOURSE_RE = re.compile(
    r"(?:旧版|旧仕様|旧問題|以前|過去の(?:問題|問い|例)|"
    r"未決|未定|未確定|保留|判断待ち|かも\s*しれない|"
    r"という(?:案|候補|仮説|想定)|不採用|却下|撤回|採用しない)"
)
_NEGATED_DIRECTION_RE = re.compile(
    r"^\s*[、，,]?\s*(?:(?:で\s*)?は\s*|で\s*)?な(?:い|く)"
)
_RESIDUE_CONNECTOR_RE = re.compile(
    r"(?:\s+|[、，,・/「」『』\"'`“”‘’]|又は|または|若しくは|もしくは|かつ|及び|および|"
    r"ではなく|でなく|ではない|でない|に|へ)+"
)
_LIMITS = [
    "明示された方向領域と二方向の後続選択構文だけを検査する。",
    "形態素解析は候補範囲の信号であり、方向領域又は方向拘束を単独では確定しない。",
    "同一節で方向基準へ直接付随する固定原文文法だけを拘束として受理する。",
    "慣習的な既定順、世界知識、画面座標、日付計算、行順、又は結果から方向を補わない。",
    "未知の方向らしい表現が直接位置にある場合は欠落と断定せず判定不能にする。",
    "引用、例示、旧版、仮定、否定、破棄対象、別領域、又は別軸の方向表現は拘束としない。",
    "候補結果、端点、循環時の巻戻し、一般グラフ、部分順序、又は複数操作を扱わない。",
]


def audit_direction_binding_sufficiency(semantic_ir: object) -> dict[str, object]:
    """Audit explicit non-scalar direction-space successor expressions."""

    source_text = str(_value(semantic_ir, "source_text", ""))
    context_start = _context_start(semantic_ir, source_text)
    attempt = _morphology_attempt(semantic_ir)
    morphology = _morphology_receipt(attempt)
    base = _base_summary(morphology)

    attempt_status = str(morphology.get("status", "not_configured"))
    if attempt_status != "executed":
        base["status"] = (
            "indeterminate"
            if attempt_status in {"failed", "unavailable"}
            else "not_applicable"
        )
        base["derivation_status"] = (
            "blocked_by_unknown"
            if attempt_status in {"failed", "unavailable"}
            else "not_applicable"
        )
        if attempt_status in {"failed", "unavailable"}:
            base["unknown_reasons"] = [f"morphology_{attempt_status}"]
        return base

    raw_tokens = _morphology_tokens(semantic_ir)
    tokens, token_errors = _validated_tokens(raw_tokens, source_text)
    diagnostics = _sequence(_value(attempt, "diagnostics", ()))
    if diagnostics:
        token_errors.extend(
            f"provider_diagnostic:{str(item)[:160]}" for item in diagnostics
        )
    if token_errors:
        base.update(
            {
                "status": "indeterminate",
                "derivation_status": "blocked_by_unknown",
                "unknown_reasons": sorted(set(token_errors)),
            }
        )
        return base

    patterns = _find_direction_patterns(
        source_text, tokens, context_start=context_start
    )
    if not patterns:
        return base
    if _question_clause_count(source_text) > 1:
        base.update(
            {
                "status": "indeterminate",
                "derivation_status": "blocked_by_unknown",
                "unknown_reasons": ["multiple_questions"],
                "candidate_operation_count": len(patterns),
            }
        )
        return base
    if len(patterns) > 1:
        base.update(
            {
                "status": "indeterminate",
                "derivation_status": "blocked_by_unknown",
                "unknown_reasons": ["multiple_candidate_operations"],
                "candidate_operation_count": len(patterns),
            }
        )
        return base

    frame = _evaluate_direction_pattern(source_text, patterns[0])
    base["frames"] = [frame]
    base["status"] = frame["status"]
    base["derivation_status"] = frame["derivation_status"]
    violations = direction_binding_contract_violations(
        base,
        source_text,
        context_start=context_start,
    )
    if violations:
        failed = _base_summary(morphology)
        failed.update(
            {
                "status": "indeterminate",
                "derivation_status": "blocked_by_unknown",
                "unknown_reasons": [
                    f"internal_direction_binding_contract:{item}" for item in violations
                ],
            }
        )
        return failed
    return base


def _base_summary(morphology: dict[str, object]) -> dict[str, object]:
    return {
        "schema_version": DIRECTION_BINDING_SCHEMA_VERSION,
        "scope": _SCOPE,
        "status": "not_applicable",
        "derivation_status": "not_applicable",
        "authority_policy": (
            "morphology is signal_only; an explicit direction-space basis and fixed "
            "source grammar establish binding; convention and outcome do not"
        ),
        "emission_authority": "primary_non_scalar_only",
        "morphology": morphology,
        "checked_scope": {
            "language": "ja",
            "pattern_families": ["explicit_direction_space_successor"],
            "selection_operation": "successor_in_explicit_direction_space",
            "registered_direction_domain_ids": sorted(
                {spec.direction_domain_id for spec in DIRECTION_SPACE_SPECS}
            ),
            "registered_direction_axis_ids": list(direction_axis_ids()),
            "registered_direction_option_ids": list(direction_option_ids()),
            "direction_binding_sites": ["same_clause_traversal"],
            "same_direction_domain_required": True,
            "same_direction_axis_required": True,
            "same_direction_basis_required": True,
            "direct_attachment_required": True,
            "candidate_result_required_for_binding": False,
        },
        "frames": [],
        "unknown_reasons": [],
        "limits": list(_LIMITS),
    }


def _find_direction_patterns(
    source_text: str,
    tokens: list[dict[str, object]],
    *,
    context_start: int,
) -> list[dict[str, object]]:
    significant = [token for token in tokens if not _space_token(token)]
    fenced_ranges = _fenced_code_ranges(source_text)
    patterns: list[dict[str, object]] = []
    for index, token in enumerate(significant):
        if _token_surface(token) != "次" or _token_lemma(token) != "次":
            continue
        previous = _previous_non_ignorable(significant, index)
        if previous is None or _token_surface(previous) != "の":
            continue
        if _position_in_ranges(int(token["start"]), fenced_ranges):
            continue
        start, end = _clause_span(
            source_text, int(previous["start"]), int(token["end"])
        )
        clause = source_text[start:end]
        reference = _reference_before(
            source_text, tokens, start, int(previous["start"])
        )
        if reference is None:
            continue
        if _candidate_is_nonbinding(
            source_text,
            start,
            end,
            clause,
            reference_start=int(reference["start"]),
        ):
            continue
        tail_text = source_text[int(token["end"]) : end]
        tail_match = _EXPLICIT_TAIL_RE.fullmatch(tail_text)
        if tail_match is None:
            continue
        target = tail_match.group("target")
        selection = tail_match.group("selection")
        if not _selection_tail(selection, target):
            continue
        prefix = source_text[start : int(reference["start"])]
        parsed = _parse_direction_prefix(
            source_text,
            prefix,
            offset=start,
            clause=clause,
            context_start=context_start,
        )
        if parsed is None:
            continue
        public_reference = _public_reference_evidence(reference)
        patterns.append(
            {
                "pattern_family": "explicit_direction_space_successor",
                "reference": reference["surface"],
                "reference_evidence": public_reference,
                "target": target,
                "selection_tail": selection,
                "source_span": _span(start, end, clause),
                "morphology_signal": {
                    "reference": public_reference,
                    "next": _token_evidence(token),
                },
                **parsed,
            }
        )
        if len(patterns) >= _MAX_PATTERNS:
            break
    return patterns


def _public_reference_evidence(
    reference: Mapping[str, object],
) -> dict[str, object]:
    """Keep only source-reproducible reference identity in the public frame."""

    public_tokens: list[dict[str, object]] = []
    for token in _sequence(reference.get("tokens", ())):
        if not isinstance(token, Mapping):
            continue
        public_tokens.append(
            {
                "surface": str(token.get("surface", "")),
                "start": token.get("start"),
                "end": token.get("end"),
            }
        )
    return {
        "surface": str(reference.get("surface", "")),
        "start": reference.get("start"),
        "end": reference.get("end"),
        "tokens": public_tokens,
        "identity_status": "source_surface_only",
    }


def _parse_direction_prefix(
    source_text: str,
    prefix: str,
    *,
    offset: int,
    clause: str,
    context_start: int,
) -> dict[str, object] | None:
    basis_matches = _basis_matches(prefix)
    if not basis_matches:
        return None
    spec, basis_match = basis_matches[0]
    basis_id = (
        f"direction-basis:{offset + basis_match.start()}:{offset + basis_match.end()}"
    )
    basis_span = _span(
        offset + basis_match.start(),
        offset + basis_match.end(),
        basis_match.group(0),
    )
    search_scope = {
        "target_clause_span": _span(offset, offset + len(clause), clause),
        "checked_binding_sites": ["same_clause_traversal"],
        "same_direction_domain_required": True,
        "same_direction_axis_required": True,
        "same_direction_basis_required": True,
        "direct_attachment_required": True,
        "postposed_binding_allowed": False,
    }
    text_end = (
        context_start - 1 if context_start < len(source_text) else len(source_text)
    )
    search_scope["text_region"] = {"start": 0, "end": max(0, text_end)}
    if context_start < len(source_text):
        search_scope["context_region"] = {
            "start": context_start,
            "end": len(source_text),
        }

    if len(basis_matches) > 1:
        unresolved = [
            _unresolved_evidence(
                spec=spec,
                basis_id=basis_id,
                source_span=_span(offset, offset + len(prefix), prefix),
                reason="multiple_direction_bases",
            )
        ]
        return {
            "direction_space": spec,
            "direction_basis_id": basis_id,
            "direction_basis_span": basis_span,
            "direction_binding": _binding_payload(
                spec,
                basis_id,
                accepted=[],
                rejected=[],
                unresolved=unresolved,
                search_scope=search_scope,
            ),
        }

    basis_pattern = _basis_pattern(spec)
    open_re = re.compile(rf"^\s*(?P<basis>{basis_pattern})\s*(?:で|では)\s*[,、，]\s*$")
    if open_re.fullmatch(prefix):
        return {
            "direction_space": spec,
            "direction_basis_id": basis_id,
            "direction_basis_span": basis_span,
            "direction_binding": _binding_payload(
                spec,
                basis_id,
                accepted=[],
                rejected=[],
                unresolved=[],
                search_scope=search_scope,
            ),
        }

    traversal_re = re.compile(
        rf"^\s*(?P<basis>{basis_pattern})\s*(?:を|で)\s*"
        rf"(?P<body>.+?)\s*{_TRAVERSAL_VERB_RE}{_CONDITION_RE}\s*[,、，]\s*$"
    )
    traversal = traversal_re.fullmatch(prefix)
    if traversal is None:
        unresolved = [
            _unresolved_evidence(
                spec=spec,
                basis_id=basis_id,
                source_span=_span(offset, offset + len(prefix), prefix),
                reason="direction_attachment_form_unresolved",
            )
        ]
        return {
            "direction_space": spec,
            "direction_basis_id": basis_id,
            "direction_basis_span": basis_span,
            "direction_binding": _binding_payload(
                spec,
                basis_id,
                accepted=[],
                rejected=[],
                unresolved=unresolved,
                search_scope=search_scope,
            ),
        }

    body = traversal.group("body")
    body_start = offset + traversal.start("body")
    accepted: list[dict[str, object]] = []
    rejected: list[dict[str, object]] = []
    unresolved: list[dict[str, object]] = []
    direction_matches = _direction_matches(body)
    unsafe_discourse = _UNSAFE_DIRECTION_DISCOURSE_RE.search(prefix) is not None
    for owner, option, match in direction_matches:
        reason = ""
        if _NEGATED_DIRECTION_RE.search(body[match.end() :]):
            reason = "negated"
        elif _position_in_inline_quote(body, match.start()):
            reason = "quoted_or_code_example"
        elif unsafe_discourse:
            reason = "historical_hypothetical_tentative_or_rejected"
        elif owner.direction_domain_id != spec.direction_domain_id:
            reason = "different_direction_domain"
        elif owner.direction_axis_id != spec.direction_axis_id:
            reason = "different_direction_axis"
        evidence = _direction_evidence(
            spec=owner,
            basis_id=basis_id,
            option=option,
            source_span=_span(
                body_start + match.start(),
                body_start + match.end(),
                match.group(0),
            ),
            relation_span=_span(
                offset + traversal.start(),
                offset + traversal.end(),
                traversal.group(0),
            ),
            rejection_reason=reason,
        )
        (rejected if reason else accepted).append(evidence)

    residue = _direction_residue(body, direction_matches)
    if not direction_matches or residue:
        unresolved.append(
            _unresolved_evidence(
                spec=spec,
                basis_id=basis_id,
                source_span=_span(body_start, body_start + len(body), body),
                reason=(
                    "unsupported_direction_expression"
                    if not direction_matches
                    else "direction_expression_contains_unresolved_material"
                ),
            )
        )
    return {
        "direction_space": spec,
        "direction_basis_id": basis_id,
        "direction_basis_span": basis_span,
        "direction_binding": _binding_payload(
            spec,
            basis_id,
            accepted=accepted,
            rejected=rejected,
            unresolved=unresolved,
            search_scope=search_scope,
        ),
    }


def _basis_matches(prefix: str) -> list[tuple[DirectionSpaceSpec, re.Match[str]]]:
    candidates: list[tuple[DirectionSpaceSpec, re.Match[str]]] = []
    for spec in DIRECTION_SPACE_SPECS:
        regex = re.compile(_basis_pattern(spec))
        candidates.extend((spec, match) for match in regex.finditer(prefix))
    return sorted(
        candidates,
        key=lambda item: (item[1].start(), -(item[1].end() - item[1].start())),
    )


def _basis_pattern(spec: DirectionSpaceSpec) -> str:
    return (
        "(?:"
        + "|".join(
            re.escape(term) for term in sorted(spec.basis_terms, key=len, reverse=True)
        )
        + ")"
    )


def _direction_matches(
    body: str,
) -> list[tuple[DirectionSpaceSpec, DirectionOptionSpec, re.Match[str]]]:
    raw: list[tuple[DirectionSpaceSpec, DirectionOptionSpec, re.Match[str]]] = []
    for spec in DIRECTION_SPACE_SPECS:
        for option in spec.options:
            for surface_pattern in option.surface_patterns:
                raw.extend(
                    (spec, option, match)
                    for match in re.finditer(surface_pattern, body)
                )
    ordered = sorted(
        raw,
        key=lambda item: (
            item[2].start(),
            -(item[2].end() - item[2].start()),
            item[1].option_id,
        ),
    )
    selected: list[tuple[DirectionSpaceSpec, DirectionOptionSpec, re.Match[str]]] = []
    for candidate in ordered:
        match = candidate[2]
        if any(
            existing[2].start() <= match.start() and match.end() <= existing[2].end()
            for existing in selected
        ):
            continue
        selected.append(candidate)
    return sorted(selected, key=lambda item: (item[2].start(), item[2].end()))


def _direction_residue(
    body: str,
    matches: list[tuple[DirectionSpaceSpec, DirectionOptionSpec, re.Match[str]]],
) -> str:
    characters = list(body)
    for _spec, _option, match in matches:
        characters[match.start() : match.end()] = " " * (match.end() - match.start())
    residue = "".join(characters)
    return _RESIDUE_CONNECTOR_RE.sub("", residue)


def _binding_payload(
    spec: DirectionSpaceSpec,
    basis_id: str,
    *,
    accepted: list[dict[str, object]],
    rejected: list[dict[str, object]],
    unresolved: list[dict[str, object]],
    search_scope: Mapping[str, object],
) -> dict[str, object]:
    resolution = resolve_direction_binding(
        accepted,
        unresolved_evidence=unresolved,
        conflict_reason="multiple_traversal_directions",
    )
    payload: dict[str, object] = {
        "status": resolution.status,
        "search_scope": dict(search_scope),
        "accepted_evidence": accepted,
        "rejected_evidence": rejected,
        "unresolved_evidence": unresolved,
        "unknown_reasons": (
            [resolution.reason] if resolution.status == "indeterminate" else []
        ),
        "required_constraint": {
            "direction_domain_id": spec.direction_domain_id,
            "direction_axis_id": spec.direction_axis_id,
            "direction_basis_id": basis_id,
            "allowed_directions": [option.option_id for option in spec.options],
            "same_direction_domain_required": True,
            "same_direction_axis_required": True,
            "same_direction_basis_required": True,
        },
    }
    if resolution.status == "bound":
        payload["direction"] = resolution.selected_direction
    elif resolution.status == "conflict":
        payload["reason"] = resolution.reason
    return payload


def _direction_evidence(
    *,
    spec: DirectionSpaceSpec,
    basis_id: str,
    option: DirectionOptionSpec,
    source_span: Mapping[str, object],
    relation_span: Mapping[str, object],
    rejection_reason: str,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "relation": "nonbinding" if rejection_reason else "bound",
        "binding_site": "same_clause_traversal",
        "direction_domain_id": spec.direction_domain_id,
        "direction_axis_id": spec.direction_axis_id,
        "direction_basis_id": basis_id,
        "basis_relation": "same_source_basis",
        "value": option.option_id,
        "source_span": dict(source_span),
        "relation_span": dict(relation_span),
        "authority": "deterministic_source_grammar",
    }
    if rejection_reason:
        payload["rejection_reasons"] = [rejection_reason]
    return payload


def _unresolved_evidence(
    *,
    spec: DirectionSpaceSpec,
    basis_id: str,
    source_span: Mapping[str, object],
    reason: str,
) -> dict[str, object]:
    return {
        "relation": "unresolved",
        "binding_site": "same_clause_traversal",
        "direction_domain_id": spec.direction_domain_id,
        "direction_axis_id": spec.direction_axis_id,
        "direction_basis_id": basis_id,
        "basis_relation": "same_source_basis",
        "value": "",
        "source_span": dict(source_span),
        "authority": "deterministic_source_grammar",
        "unknown_reasons": [reason],
    }


def _evaluate_direction_pattern(
    source_text: str,
    pattern: dict[str, object],
) -> dict[str, object]:
    spec = pattern["direction_space"]
    binding = pattern["direction_binding"]
    reference_evidence = pattern["reference_evidence"]
    pattern_span = pattern["source_span"]
    assert isinstance(spec, DirectionSpaceSpec)
    assert isinstance(binding, dict)
    assert isinstance(reference_evidence, Mapping)
    assert isinstance(pattern_span, Mapping)
    options = [option.option_id for option in spec.options]
    reference = str(pattern["reference"])
    target = str(pattern["target"])
    expression_start = int(reference_evidence["start"])
    expression_end = int(pattern_span["end"])
    basis_id = str(pattern["direction_basis_id"])
    binding_status = str(binding.get("status", "missing"))

    frame_status = {
        "missing": "direction_unbound",
        "bound": "direction_bound",
        "conflict": "direction_conflict",
        "indeterminate": "direction_indeterminate",
    }[binding_status]
    derivation_status = {
        "missing": "derived",
        "bound": "satisfied",
        "conflict": "conflict",
        "indeterminate": "blocked_by_unknown",
    }[binding_status]
    frame: dict[str, object] = {
        "frame_id": f"direction-binding:{pattern_span['start']}:{pattern_span['end']}",
        "pattern_family": pattern["pattern_family"],
        "status": frame_status,
        "derivation_status": derivation_status,
        "source_span": dict(pattern_span),
        "direction_open_expression": {
            "kind": "successor_in_explicit_direction_space",
            "source_span": _span(
                expression_start,
                expression_end,
                source_text[expression_start:expression_end],
            ),
            "direction_domain_id": spec.direction_domain_id,
            "direction_axis_id": spec.direction_axis_id,
            "direction_basis_id": basis_id,
            "direction_basis_span": dict(pattern["direction_basis_span"]),
            "direction_options": options,
        },
        "candidate_set_binding": {
            "status": "not_required",
            "reason": (
                "primary binding audits direct source attachment and does not compute an outcome"
            ),
        },
        "direction_binding": binding,
        "operation": {
            "family": "successor_in_explicit_direction_space",
            "reference_member_key": (
                f"source-member:{reference_evidence['start']}:{reference_evidence['end']}"
            ),
            "reference_label": reference,
            "direction_domain_id": spec.direction_domain_id,
            "direction_axis_id": spec.direction_axis_id,
            "direction_basis_id": basis_id,
            "target": target,
            "offset": 1,
        },
        "morphology_signal": pattern["morphology_signal"],
        "required_conditions": ["traversal_direction"],
        "missing_conditions": [],
        "interpretation_candidates": [],
        "repair_candidates": [],
        "unknown_reasons": list(binding.get("unknown_reasons", [])),
        "evaluations": [
            _direction_evaluation(binding_status=binding_status, options=options)
        ],
    }
    if binding_status in {"missing", "conflict"}:
        frame["missing_conditions"] = [
            "traversal_direction"
            if binding_status == "missing"
            else "unambiguous_traversal_direction"
        ]
        candidates = _interpretation_candidates(pattern, spec)
        frame["interpretation_candidates"] = candidates
        frame["repair_candidates"] = [
            {
                "condition": dict(item["condition"]),
                "rewrite": item["rewrite"],
                "outcome_status": "not_evaluated",
            }
            for item in candidates
        ]
    return frame


def _direction_evaluation(
    *,
    binding_status: str,
    options: list[str],
) -> dict[str, object]:
    finding_eligible = binding_status in {"missing", "conflict"}
    return {
        "rule_id": PRECONDITION_ORDER_DIRECTION_RULE_ID,
        "status": (
            "derived"
            if finding_eligible
            else "satisfied"
            if binding_status == "bound"
            else "unknown"
        ),
        "claim_level": "direction_binding_gap",
        "finding_eligible": finding_eligible,
        "match_status": "unknown" if binding_status == "indeterminate" else "matched",
        "confidence": "low" if binding_status == "indeterminate" else "medium",
        "binding_status": binding_status,
        "candidate_conditions": options,
        "emission_authority": "primary",
    }


def _interpretation_candidates(
    pattern: Mapping[str, object],
    spec: DirectionSpaceSpec,
) -> list[dict[str, object]]:
    basis = spec.basis_terms[0]
    reference = str(pattern["reference"])
    target = str(pattern["target"])
    tail = str(pattern["selection_tail"])
    return [
        {
            "condition": {
                "traversal_direction": option.option_id,
                "direction_domain_id": spec.direction_domain_id,
                "direction_axis_id": spec.direction_axis_id,
            },
            "rewrite": (
                f"{basis}を{option.canonical_surface}辿るとき、"
                f"{reference}の次の{target}{tail}"
            ),
            "outcome_status": "not_evaluated",
        }
        for option in spec.options
    ]


def direction_binding_contract_violations(
    summary: Mapping[str, object],
    source_text: str,
    *,
    context_start: int | None = None,
) -> list[str]:
    """Return internal cross-field and source-span contract violations.

    JSON Schema constrains the public shape. This runtime check covers the
    source-local equalities that JSON Schema cannot express, so an internal
    drift fails closed before it can become an actionable finding.

    ``context_start`` is a trusted text/context boundary derived from the same
    semantic IR as ``source_text``. A detached caller that invents both the
    boundary and matching scope metadata is outside this validator's contract.
    """

    violations: list[str] = []
    frames = summary.get("frames", [])
    if not isinstance(frames, list) or len(frames) != 1:
        return ["expected_one_frame"]
    frame = frames[0]
    if not isinstance(frame, Mapping):
        return ["frame_not_mapping"]
    expression = frame.get("direction_open_expression", {})
    operation = frame.get("operation", {})
    binding = frame.get("direction_binding", {})
    if not all(isinstance(item, Mapping) for item in (expression, operation, binding)):
        return ["frame_contract_component_not_mapping"]
    assert isinstance(expression, Mapping)
    assert isinstance(operation, Mapping)
    assert isinstance(binding, Mapping)
    required = binding.get("required_constraint", {})
    if not isinstance(required, Mapping):
        return ["required_constraint_not_mapping"]

    identity_fields = (
        "direction_domain_id",
        "direction_axis_id",
        "direction_basis_id",
    )
    for field in identity_fields:
        values = {
            str(item.get(field, "")) for item in (expression, operation, required)
        }
        if "" in values or len(values) != 1:
            violations.append(f"{field}_mismatch")

    options = expression.get("direction_options", [])
    allowed = required.get("allowed_directions", [])
    if (
        not isinstance(options, list)
        or not isinstance(allowed, list)
        or len(options) != 2
        or len(set(map(str, options))) != 2
        or set(map(str, options)) != set(map(str, allowed))
    ):
        violations.append("direction_options_mismatch")
    option_ids = set(map(str, options)) if isinstance(options, list) else set()

    accepted = binding.get("accepted_evidence", [])
    rejected = binding.get("rejected_evidence", [])
    unresolved = binding.get("unresolved_evidence", [])
    if not all(isinstance(item, list) for item in (accepted, rejected, unresolved)):
        violations.append("evidence_collection_not_list")
        return sorted(set(violations))
    assert isinstance(accepted, list)
    assert isinstance(rejected, list)
    assert isinstance(unresolved, list)

    expected_domain = str(expression.get("direction_domain_id", ""))
    expected_axis = str(expression.get("direction_axis_id", ""))
    expected_basis = str(expression.get("direction_basis_id", ""))
    for index, evidence in enumerate(accepted):
        if not isinstance(evidence, Mapping):
            violations.append(f"accepted_evidence_not_mapping:{index}")
            continue
        if evidence.get("relation") != "bound":
            violations.append(f"accepted_evidence_relation:{index}")
        if str(evidence.get("value", "")) not in option_ids:
            violations.append(f"accepted_evidence_option:{index}")
        for field, expected in (
            ("direction_domain_id", expected_domain),
            ("direction_axis_id", expected_axis),
            ("direction_basis_id", expected_basis),
        ):
            if str(evidence.get(field, "")) != expected:
                violations.append(f"accepted_evidence_{field}:{index}")

    for index, evidence in enumerate(unresolved):
        if not isinstance(evidence, Mapping):
            violations.append(f"unresolved_evidence_not_mapping:{index}")
            continue
        if evidence.get("relation") != "unresolved" or evidence.get("value") != "":
            violations.append(f"unresolved_evidence_relation:{index}")
        for field, expected in (
            ("direction_domain_id", expected_domain),
            ("direction_axis_id", expected_axis),
            ("direction_basis_id", expected_basis),
        ):
            if str(evidence.get(field, "")) != expected:
                violations.append(f"unresolved_evidence_{field}:{index}")

    for index, evidence in enumerate(rejected):
        if not isinstance(evidence, Mapping):
            violations.append(f"rejected_evidence_not_mapping:{index}")
            continue
        if evidence.get("relation") != "nonbinding" or not evidence.get(
            "rejection_reasons"
        ):
            violations.append(f"rejected_evidence_relation:{index}")
        if str(evidence.get("direction_basis_id", "")) != expected_basis:
            violations.append(f"rejected_evidence_direction_basis_id:{index}")

    recomputed = resolve_direction_binding(
        [item for item in accepted if isinstance(item, Mapping)],
        unresolved_evidence=[item for item in unresolved if isinstance(item, Mapping)],
        conflict_reason="multiple_traversal_directions",
    )
    binding_status = str(binding.get("status", ""))
    if binding_status != recomputed.status:
        violations.append("binding_status_not_reproducible")
    if recomputed.status == "bound" and str(binding.get("direction", "")) != (
        recomputed.selected_direction
    ):
        violations.append("selected_direction_mismatch")

    expected_frame_status = {
        "missing": "direction_unbound",
        "bound": "direction_bound",
        "conflict": "direction_conflict",
        "indeterminate": "direction_indeterminate",
    }.get(recomputed.status, "")
    if str(frame.get("status", "")) != expected_frame_status:
        violations.append("frame_status_mismatch")
    if str(summary.get("status", "")) != expected_frame_status:
        violations.append("summary_status_mismatch")

    basis_span = expression.get("direction_basis_span", {})
    if isinstance(basis_span, Mapping):
        basis_start = basis_span.get("start")
        basis_end = basis_span.get("end")
        if expected_basis != f"direction-basis:{basis_start}:{basis_end}":
            violations.append("direction_basis_id_span_mismatch")
    else:
        violations.append("direction_basis_span_not_mapping")

    morphology = frame.get("morphology_signal", {})
    reference = (
        morphology.get("reference", {}) if isinstance(morphology, Mapping) else {}
    )
    if isinstance(reference, Mapping):
        expected_member_key = (
            f"source-member:{reference.get('start')}:{reference.get('end')}"
        )
        if operation.get("reference_member_key") != expected_member_key:
            violations.append("reference_member_key_span_mismatch")
    else:
        violations.append("reference_signal_not_mapping")

    spans: list[tuple[str, object]] = [
        ("frame", frame.get("source_span")),
        ("open_expression", expression.get("source_span")),
        ("direction_basis", expression.get("direction_basis_span")),
    ]
    for collection_name, collection in (
        ("accepted", accepted),
        ("rejected", rejected),
        ("unresolved", unresolved),
    ):
        for index, evidence in enumerate(collection):
            if not isinstance(evidence, Mapping):
                continue
            spans.append(
                (f"{collection_name}:{index}:source", evidence.get("source_span"))
            )
            if "relation_span" in evidence:
                spans.append(
                    (
                        f"{collection_name}:{index}:relation",
                        evidence.get("relation_span"),
                    )
                )
    for label, candidate in spans:
        if not _source_span_is_aligned(candidate, source_text):
            violations.append(f"source_span_mismatch:{label}")

    canonical, canonical_errors = _canonical_direction_binding_summary(
        summary,
        source_text,
        context_start=len(source_text) if context_start is None else context_start,
    )
    violations.extend(canonical_errors)
    if canonical is not None:
        canonical_frame = canonical["frames"][0]
        if binding != canonical_frame["direction_binding"]:
            violations.append("direction_binding_not_source_reproducible")
        if dict(frame) != canonical_frame:
            violations.append("direction_frame_not_source_reproducible")
        if dict(summary) != canonical:
            violations.append("direction_summary_not_source_reproducible")
    return sorted(set(violations))


def _canonical_direction_binding_summary(
    summary: Mapping[str, object],
    source_text: str,
    *,
    context_start: int,
) -> tuple[dict[str, object] | None, list[str]]:
    """Rebuild the one-frame payload from source grammar, not supplied claims."""

    errors: list[str] = []
    frames = summary.get("frames")
    if not isinstance(frames, list) or len(frames) != 1:
        return None, ["canonical_expected_one_frame"]
    frame = frames[0]
    if not isinstance(frame, Mapping):
        return None, ["canonical_frame_not_mapping"]

    frame_span = frame.get("source_span")
    if not _source_span_is_aligned(frame_span, source_text):
        return None, ["canonical_frame_span_unaligned"]
    assert isinstance(frame_span, Mapping)
    frame_start = frame_span.get("start")
    frame_end = frame_span.get("end")
    if not isinstance(frame_start, int) or not isinstance(frame_end, int):
        return None, ["canonical_frame_span_invalid"]

    morphology_signal = frame.get("morphology_signal")
    if not isinstance(morphology_signal, Mapping):
        return None, ["canonical_morphology_signal_not_mapping"]
    reference = morphology_signal.get("reference")
    next_signal = morphology_signal.get("next")
    if not isinstance(reference, Mapping) or not isinstance(next_signal, Mapping):
        return None, ["canonical_token_signal_not_mapping"]
    expected_reference_keys = {
        "surface",
        "start",
        "end",
        "tokens",
        "identity_status",
    }
    expected_next_keys = {"surface", "lemma", "start", "end"}
    if set(reference) != expected_reference_keys:
        errors.append("canonical_reference_signal_shape")
    if set(next_signal) != expected_next_keys:
        errors.append("canonical_next_signal_shape")

    reference_start = reference.get("start")
    reference_end = reference.get("end")
    next_start = next_signal.get("start")
    next_end = next_signal.get("end")
    positions = (reference_start, reference_end, next_start, next_end)
    if not all(
        isinstance(item, int) and not isinstance(item, bool) for item in positions
    ):
        return None, errors + ["canonical_token_signal_position"]
    assert isinstance(reference_start, int)
    assert isinstance(reference_end, int)
    assert isinstance(next_start, int)
    assert isinstance(next_end, int)
    if not (
        frame_start
        <= reference_start
        < reference_end
        < next_start
        < next_end
        <= frame_end
    ):
        return None, errors + ["canonical_token_signal_order"]

    reference_surface = source_text[reference_start:reference_end]
    next_surface = source_text[next_start:next_end]
    if str(reference.get("surface", "")) != reference_surface:
        errors.append("canonical_reference_surface_mismatch")
    if reference.get("identity_status") != "source_surface_only":
        errors.append("canonical_reference_identity_status")
    reference_tokens = reference.get("tokens")
    if not _reference_tokens_align(
        reference_tokens,
        source_text,
        start=reference_start,
        end=reference_end,
    ):
        errors.append("canonical_reference_tokens_mismatch")
    if (
        next_surface != "次"
        or str(next_signal.get("surface", "")) != "次"
        or str(next_signal.get("lemma", "")) != "次"
    ):
        errors.append("canonical_next_signal_mismatch")
    if re.sub(r"\s+", "", source_text[reference_end:next_start]) != "の":
        errors.append("canonical_reference_next_relation")

    if _question_clause_count(source_text) > 1:
        errors.append("canonical_multiple_questions")
    fenced_ranges = _fenced_code_ranges(source_text)
    if _position_in_ranges(next_start, fenced_ranges):
        errors.append("canonical_fenced_source_frame")

    expected_clause_start, expected_clause_end = _clause_span(
        source_text,
        next_start,
        next_end,
    )
    if (frame_start, frame_end) != (expected_clause_start, expected_clause_end):
        errors.append("canonical_frame_clause_mismatch")

    tail_text = source_text[next_end:frame_end]
    tail_match = _EXPLICIT_TAIL_RE.fullmatch(tail_text)
    if tail_match is None:
        return None, errors + ["canonical_selection_tail_unparseable"]
    target = tail_match.group("target")
    selection = tail_match.group("selection")
    if not _selection_tail(selection, target):
        return None, errors + ["canonical_selection_tail_invalid"]

    clause = source_text[frame_start:frame_end]
    if _candidate_is_nonbinding(
        source_text,
        frame_start,
        frame_end,
        clause,
        reference_start=reference_start,
    ):
        errors.append("canonical_nonbinding_source_frame")

    canonical_operations = _canonical_source_operations(
        source_text,
        context_start=context_start,
    )
    if len(canonical_operations) != 1:
        errors.append("canonical_candidate_operation_count")
    elif canonical_operations[0] != (
        frame_start,
        frame_end,
        reference_start,
        reference_end,
        next_start,
        next_end,
    ):
        errors.append("canonical_candidate_operation_identity")
    prefix = source_text[frame_start:reference_start]
    parsed = _parse_direction_prefix(
        source_text,
        prefix,
        offset=frame_start,
        clause=clause,
        context_start=context_start,
    )
    if parsed is None:
        return None, errors + ["canonical_direction_prefix_unparseable"]

    canonical_reference = dict(reference)
    canonical_next = {
        "surface": "次",
        "lemma": "次",
        "start": next_start,
        "end": next_end,
    }
    pattern = {
        "pattern_family": "explicit_direction_space_successor",
        "reference": reference_surface,
        "reference_evidence": canonical_reference,
        "target": target,
        "selection_tail": selection,
        "source_span": _span(frame_start, frame_end, clause),
        "morphology_signal": {
            "reference": canonical_reference,
            "next": canonical_next,
        },
        **parsed,
    }
    expected_frame = _evaluate_direction_pattern(source_text, pattern)

    morphology = summary.get("morphology")
    if not isinstance(morphology, Mapping):
        return None, errors + ["canonical_morphology_not_mapping"]
    errors.extend(_executed_morphology_receipt_errors(morphology))
    expected_summary = _base_summary(dict(morphology))
    expected_summary["frames"] = [expected_frame]
    expected_summary["status"] = expected_frame["status"]
    expected_summary["derivation_status"] = expected_frame["derivation_status"]
    return expected_summary, errors


def _reference_tokens_align(
    candidate: object,
    source_text: str,
    *,
    start: int,
    end: int,
) -> bool:
    if not isinstance(candidate, list) or not candidate:
        return False
    cursor = start
    for token in candidate:
        if not isinstance(token, Mapping) or set(token) != {
            "surface",
            "start",
            "end",
        }:
            return False
        token_start = token.get("start")
        token_end = token.get("end")
        if (
            not isinstance(token_start, int)
            or isinstance(token_start, bool)
            or not isinstance(token_end, int)
            or isinstance(token_end, bool)
            or token_start != cursor
            or token_end <= token_start
            or token_end > end
            or str(token.get("surface", "")) != source_text[token_start:token_end]
        ):
            return False
        cursor = token_end
    return cursor == end


def _canonical_source_operations(
    source_text: str,
    *,
    context_start: int,
) -> list[tuple[int, int, int, int, int, int]]:
    """Locate every registered live operation from fixed source grammar alone."""

    operations: list[tuple[int, int, int, int, int, int]] = []
    fenced_ranges = _fenced_code_ranges(source_text)
    for match in _SOURCE_SUCCESSOR_RE.finditer(source_text):
        next_start = match.start("next")
        next_end = match.end("next")
        if _position_in_ranges(next_start, fenced_ranges):
            continue
        frame_start, frame_end = _clause_span(source_text, next_start, next_end)
        reference_start = match.start("reference")
        reference_end = match.end("reference")
        clause = source_text[frame_start:frame_end]
        if _candidate_is_nonbinding(
            source_text,
            frame_start,
            frame_end,
            clause,
            reference_start=reference_start,
        ):
            continue
        tail_match = _EXPLICIT_TAIL_RE.fullmatch(source_text[next_end:frame_end])
        if tail_match is None:
            continue
        target = tail_match.group("target")
        if not _selection_tail(tail_match.group("selection"), target):
            continue
        if (
            _parse_direction_prefix(
                source_text,
                source_text[frame_start:reference_start],
                offset=frame_start,
                clause=clause,
                context_start=context_start,
            )
            is None
        ):
            continue
        operations.append(
            (
                frame_start,
                frame_end,
                reference_start,
                reference_end,
                next_start,
                next_end,
            )
        )
    return operations


def _executed_morphology_receipt_errors(
    morphology: Mapping[str, object],
) -> list[str]:
    expected_keys = {
        "status",
        "authority",
        "provider_id",
        "provider_version",
        "resource_version",
        "split_mode",
    }
    errors: list[str] = []
    if set(morphology) != expected_keys:
        errors.append("canonical_morphology_receipt_shape")
    if morphology.get("status") != "executed":
        errors.append("canonical_morphology_not_executed")
    if morphology.get("authority") != "signal_only":
        errors.append("canonical_morphology_authority")
    for field in ("provider_id", "provider_version", "resource_version"):
        if not isinstance(morphology.get(field), str) or not morphology.get(field):
            errors.append(f"canonical_morphology_{field}")
    if morphology.get("split_mode") not in {"A", "B", "C"}:
        errors.append("canonical_morphology_split_mode")
    return errors


def _source_span_is_aligned(candidate: object, source_text: str) -> bool:
    if not isinstance(candidate, Mapping):
        return False
    start = candidate.get("start")
    end = candidate.get("end")
    excerpt = candidate.get("excerpt")
    if (
        not isinstance(start, int)
        or isinstance(start, bool)
        or not isinstance(end, int)
        or isinstance(end, bool)
        or start < 0
        or end < start
        or end > len(source_text)
        or not isinstance(excerpt, str)
    ):
        return False
    return excerpt == source_text[start:end][:240]


__all__ = [
    "DIRECTION_BINDING_SCHEMA_VERSION",
    "audit_direction_binding_sufficiency",
    "direction_binding_contract_violations",
]
