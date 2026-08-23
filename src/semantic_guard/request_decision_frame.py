from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation
from itertools import pairwise
from typing import Any

from semantic_guard.decision_frame_scales import (
    SCALE_SPECS,
    OrderAxisSpec,
    ScaleSpec,
    all_comparison_terms,
    all_measure_terms,
    axis_for_measure,
    match_directional_axis,
    normalize_unit,
    numeric_projection_for_scale,
    numeric_unit_pattern,
)
from semantic_guard.direction_binding_core import resolve_direction_binding

DECISION_FRAME_SCHEMA_VERSION = "decision-frame-summary/v3"
PRECONDITION_ORDER_DIRECTION_RULE_ID = "req.precondition.order_direction_unspecified"
# Retained as a compatibility identifier only.  v3 never evaluates or emits it;
# numeric counterfactuals live under ``impact_evidence`` instead.
PRECONDITION_OUTCOME_RULE_ID = "req.precondition.outcome_not_invariant"

_SCOPE = "bounded_japanese_registered_scalar_direction_binding"
_MAX_TOKENS = 4096
_MAX_OBSERVATIONS = 64
_MAX_PATTERNS = 8
_MAX_REFERENCE_TOKENS = 8
_CLAUSE_BOUNDARIES = "。！？!?\n\r"
_REFERENCE_SURFACE_RE = re.compile(
    r"(?P<reference>[^\s、，,;；:：=＝。！？!?「」『』（）()]{1,32})\s*$"
)
_TARGET_RE = r"[A-Za-z0-9_\-一-龥々〆ヵヶぁ-んァ-ヴー]{1,16}?"
_ROW_LABEL_RE = r"[^\s:：=＝,，、;；。！？!?]{1,32}"
_ROW_SEGMENT_RE = re.compile(
    rf"(?:^|[\n\r,，、;；])\s*(?:[-*+・•]\s*)?"
    rf"(?P<label>{_ROW_LABEL_RE})\s*[:：=＝]\s*"
    r"(?P<raw>[^\n\r,，、;；。！？!?]{1,160})",
    re.MULTILINE,
)
_ROW_LINE_RE = re.compile(
    rf"^\s*(?:[-*+・•]\s*)?(?P<label>{_ROW_LABEL_RE})\s*[:：=＝]\s*.+$"
)
_NUMERIC_VALUE_RE = r"[+-]?(?:\d+(?:\.\d+)?|\.\d+)"
_NUMERICISH_RE = re.compile(
    rf"^(?:(?:約|およそ|概ね|ほぼ|推定)\s*)?{_NUMERIC_VALUE_RE}"
)
_DECLARED_CANDIDATE_COUNT_RE = re.compile(
    r"この\s*(?P<count>[0-9０-９〇零一二三四五六七八九十百]+)\s*"
    r"(?P<kind>[A-Za-z一-龥々ぁ-んァ-ヶー]{1,12})\s*の\s*中\s*で"
    r"(?!\s*(?:は\s*)?な(?:い|く))\s*[,、，]"
)
_COUNT_SURFACE = r"[0-9０-９〇零一二三四五六七八九十百]+"
_KIND_SURFACE = r"[A-Za-z一-龥々ぁ-んァ-ヶー]{1,12}"
_DIRECT_ORDER_PREFIX_RE = re.compile(
    rf"^[ \t]*(?:この[ \t]*(?P<count>{_COUNT_SURFACE})[ \t]*"
    rf"(?P<kind>{_KIND_SURFACE})"
    r"[ \t]*(?:を|の[ \t]*中[ \t]*で[ \t]*[,、，]))?[ \t]*$"
)
_DIRECT_ORDER_GAP_RE = re.compile(
    rf"^[ \t]*[,、，][ \t]*(?:この[ \t]*(?P<count>{_COUNT_SURFACE})[ \t]*"
    rf"(?P<kind>{_KIND_SURFACE})[ \t]*の[ \t]*中[ \t]*で[ \t]*"
    r"[,、，][ \t]*)?$"
)
_CANDIDATE_MEMBERSHIP_HEADER_RE = re.compile(
    r"^[ \t]*(?:候補種別[ \t]*[:：=＝][ \t]*(?P<declared_kind>"
    r"[A-Za-z一-龥々ぁ-んァ-ヶー]{1,12})|"
    r"候補(?:集合|一覧)[ \t]*[（(][ \t]*(?P<parenthesized_kind>"
    r"[A-Za-z一-龥々ぁ-んァ-ヶー]{1,12})[ \t]*[）)][ \t]*[:：]?)[ \t]*$",
    re.MULTILINE,
)
_OPAQUE_CANDIDATE_LABEL_RE = re.compile(r"[A-Z]")
_MORPHOLOGY_FIELDS = (
    "status",
    "authority",
    "provider_id",
    "provider_version",
    "resource_version",
    "split_mode",
)
_NON_ENTITY_LABELS = {
    "平均",
    "平均値",
    "標準偏差",
    "分散",
    "合計",
    "合計値",
    "小計",
    "総計",
    "中央値",
    "最大",
    "最大値",
    "最小",
    "最小値",
    "average",
    "average_value",
    "avg",
    "mean",
    "median",
    "sum",
    "total",
    "standard_deviation",
    "variance",
}
_QUESTION_WORD_RE = re.compile(
    r"(?:誰|どれ|どこ|どの\s*[A-Za-z一-龥々ぁ-んァ-ヶー]+|何\s*(?:人|件|個)|"
    r"いつ|なぜ|どうして|どちら)"
)
_QUESTION_SEPARATOR_RE = re.compile(r"か\s*[,、，;；]")
_QUESTION_END_RE = re.compile(
    r"(?:(?:です|ます|でしょう|だろう|なの|の)\s*)?か\s*(?:[。！？!?]|$)"
)
_METALINGUISTIC_RE = re.compile(
    r"(?:という|との)(?:表現|例文|問題文|文|文言|語|問い)|"
    r"(?:表現|例文|問題文|文言)\s*(?:を|の)\s*(?:検出|解析|監査|説明)"
)
_BLOCK_QUOTED_CANDIDATE_RE = re.compile(r"(?:^|[\n\r])\s*>")
_NONBINDING_CANDIDATE_PREFIX_RE = re.compile(
    r"^\s*(?:(?:例えば|たとえば|例として|一例として|一例では|例題|例文|"
    r"見本|参考例)\s*[:：、，,]?|例\s*[:：]|"
    r"(?:旧版|旧仕様|旧問題)(?:\s*の\s*(?:問題|問い|例|問題文|文言|表現))?"
    r"\s*(?:では|として)?\s*[:：、，,]?|"
    r"(?:以前|過去|かつて)\s*の\s*(?:問題|問い|例|問題文|文言|表現)"
    r"\s*(?:として)?\s*[:：、，,]?|"
    r"(?:仮に|もし)\s*(?:[、，,]|(?:問|選)う?\s*(?:なら|場合))|"
    r"仮定\s*(?:すると|して)\s*[:：、，,]?|引用\s*[:：、，,]|"
    r"(?:説明対象|解析対象)\s*[:：、，,])"
)
_NONBINDING_CANDIDATE_DISPOSITION_RE = re.compile(
    r"^\s*(?:(?:なお|また|ただし|そして)[、，,]?\s*)?"
    r"(?:(?:(?:これ|この(?:案|問題|問い|質問|表現|文言|選択)|"
    r"当該(?:案|問題|問い|質問|表現|文言|選択)|本案|上記の(?:案|問題|問い|質問))"
    r"\s*(?:(?:は|を)\s*(?:不採用(?:とする|にする)?|却下(?:する)?|撤回(?:する)?|"
    r"採用しない|使用しない|使わない|廃止(?:する)?)|"
    r"の\s*採用\s*は\s*(?:見送る|取りやめる|中止する)))|"
    r"(?:不採用とする|採用は見送る|現行では使わない|現在は使わない))"
    r"\s*[。！？!?]?\s*$"
)
_UNSAFE_ORDER_DISCOURSE_RE = re.compile(
    r"(?:旧版|旧仕様|旧問題|一例では|以前\s*の\s*(?:問題|問い|例)|"
    r"過去\s*の\s*(?:問題|問い|例)|かつて\s*の\s*(?:問題|問い|例)|"
    r"未決|未定|未確定|保留|判断待ち|"
    r"とは\s*限らない|かも\s*しれない|という\s*(?:案|候補|仮説|想定)|"
    r"という\s*(?:文言|表現|説明)|(?:文言|表現)\s*(?:を|の)\s*(?:説明|検出|解析))"
)
_UNSAFE_ORDER_HEADER_CONTEXT_RE = re.compile(
    r"(?:旧版|旧仕様|以前|過去|かつて|未決|未定|保留|判断待ち|"
    r"候補案|参考案|参考例|見本|引用|説明用|(?:^|\n)[^\n]{0,12}案\s*[:：])"
)
_ARRANGEMENT_SUFFIX = (
    r"\s*(?:で|に)?\s*(?:並べ|整列|ソート)(?:た|る|した|する)?"
    r"\s*(?:とき|時|場合|と|なら)"
)
_ALL_ORDER_TERMS = tuple(
    sorted({*all_comparison_terms(), "昇", "降"}, key=lambda value: (-len(value), value))
)
_ORDER_TERM_PATTERN = "(?:" + "|".join(
    re.escape(term) for term in _ALL_ORDER_TERMS
) + ")"
_COMPARISON_TERM_PATTERN = "(?:" + "|".join(
    re.escape(term) for term in all_comparison_terms()
) + ")"
_CLASSIC_ORDER_SURFACE_PATTERN = _ORDER_TERM_PATTERN + r"\s*順"
_POLE_ORIGIN_ORDER_SURFACE_PATTERN = (
    _COMPARISON_TERM_PATTERN
    + r"\s*(?:もの\s*から\s*順|方\s*から(?:\s*順)?)"
)
_ANY_ORDER_RE = re.compile(
    rf"(?:{_CLASSIC_ORDER_SURFACE_PATTERN}|{_POLE_ORIGIN_ORDER_SURFACE_PATTERN})"
)
_CLASSIC_ORDER_VALUE_RE = re.compile(
    rf"(?P<term>{_ORDER_TERM_PATTERN})\s*順"
)
_POLE_ORIGIN_ORDER_VALUE_RE = re.compile(
    rf"(?P<term>{_COMPARISON_TERM_PATTERN})"
    r"\s*(?:もの\s*から\s*順|方\s*から(?:\s*順)?)"
)
_ORDINAL_ORDER_DIRECTIONS = {
    "昇": "scale_low_pole_first",
    "降": "scale_high_pole_first",
}
_NEGATED_ORDER_RE = re.compile(
    _ANY_ORDER_RE.pattern + r"\s*(?:で\s*は)?\s*な(?:い|く)"
)
_NEGATED_ARRANGEMENT_RE = re.compile(
    _ANY_ORDER_RE.pattern
    + r"[^。！？!?\n\r]{0,32}(?:とき|時|場合)\s*"
    + r"(?:(?:で\s*は)?\s*な(?:い|く)|(?:で\s*は)?\s*ありませ(?:ん|ず)|"
    + r"を\s*除(?:き|く|外)|以外(?:で\s*は|なら|の)?)"
)
_ORDER_HEADER_RE = re.compile(
    r"^[ \t]{0,3}(?:(?P<measure>[^\n\r:：=＝]{1,24}?)[ \t]*(?:の[ \t]*)?)?"
    r"並び順[ \t]*[:：=＝][ \t]*(?P<value>[^\n\r]+?)[ \t]*$",
    re.MULTILINE,
)
_LIMITS = [
    "登録済み尺度と極性語を使う、日本語の固定された後続選択構文だけを検査する。",
    "形態素解析は候補範囲の信号であり、方向拘束の結合、候補所属、数値、又は結果を単独では確定しない。",
    "一次監査は、方向を一意にしない固定構文と、同じ判断枠・同じ順序軸へ結び付く方向拘束との関係だけを判定する。",
    "近傍の他尺度、引用、例示、旧版、仮定、否定、又は非現行の方向表現は拘束とせず、拒否証拠として記録する。",
    "数値投影は任意の影響証拠であり、一次規則の発火、状態、適合度、又は確信度を変更しない。",
    "数値影響証拠は登録済みの同一単位だけを扱い、単位換算、同値順位、範囲、概数、順位尺度、日時、尺度省略、照応を扱わない。",
    "方向を一意にしない表現自体が引用、例示、旧版、仮定、破棄対象、複数操作、又はコード塊に属する場合は棄権又は非適用にする。",
]


def audit_precondition_sufficiency(semantic_ir: object) -> dict[str, object]:
    """Audit a bounded scalar-successor family from a shared semantic IR."""

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
        token_errors.extend(f"provider_diagnostic:{str(item)[:160]}" for item in diagnostics)
    if token_errors:
        base.update(
            {
                "status": "indeterminate",
                "derivation_status": "blocked_by_unknown",
                "unknown_reasons": sorted(set(token_errors)),
            }
        )
        return base

    patterns = _find_patterns(source_text, tokens, context_start=context_start)
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

    frame = _evaluate_pattern(
        source_text,
        patterns[0],
        context_start=context_start,
    )
    base["frames"] = [frame]
    base["status"] = frame["status"]
    base["derivation_status"] = frame["derivation_status"]
    return base


def _base_summary(morphology: dict[str, object]) -> dict[str, object]:
    return {
        "schema_version": DECISION_FRAME_SCHEMA_VERSION,
        "scope": _SCOPE,
        "status": "not_applicable",
        "derivation_status": "not_applicable",
        "authority_policy": (
            "morphology is signal_only; fixed source grammar and bounded attachment rules derive "
            "direction binding; numeric projections are auxiliary impact evidence only"
        ),
        "morphology": morphology,
        "checked_scope": {
            "language": "ja",
            "pattern_families": [
                "reference_next_registered_scalar",
                "explicit_registered_scalar_order_successor",
            ],
            "selection_operation": "successor_in_scalar_order",
            "registered_scale_ids": [scale.scale_id for scale in SCALE_SPECS],
            "registered_order_axis_ids": [
                axis.axis_id for scale in SCALE_SPECS for axis in scale.axes
            ],
            "comparison_terms": list(all_comparison_terms()),
            "direction_binding_sites": [
                "same_clause_arrangement",
                "current_candidate_table_header",
            ],
            "same_scale_required_for_direction_binding": True,
            "same_order_axis_required_for_direction_binding": True,
            "postposed_header_binding_allowed": False,
            "optional_impact_scope": {
                "emitted_only_when_closed_witness_exists": True,
                "affects_primary_finding": False,
            },
        },
        "frames": [],
        "limits": list(_LIMITS),
    }


def _morphology_attempt(semantic_ir: object) -> object | None:
    for attempt in _sequence(_value(semantic_ir, "attempts", ())):
        if str(_value(attempt, "stage", "")) == "morphology":
            return attempt
    return None


def _morphology_receipt(attempt: object | None) -> dict[str, object]:
    if attempt is None:
        return {"status": "not_configured", "authority": "signal_only"}
    receipt = {
        field: _value(attempt, field, "")
        for field in _MORPHOLOGY_FIELDS
        if _value(attempt, field, "") not in (None, "")
    }
    receipt.setdefault("status", "not_configured")
    receipt.setdefault("authority", "signal_only")
    return receipt


def _morphology_tokens(semantic_ir: object) -> list[object]:
    for support in _sequence(_value(semantic_ir, "supports", ())):
        if str(_value(support, "tier", "")) != "morphology":
            continue
        if str(_value(support, "authority", "")) != "signal_only":
            continue
        metadata = _value(support, "metadata", {})
        return list(_sequence(_value(metadata, "tokens", ())))
    return []


def _validated_tokens(
    raw_tokens: list[object], source_text: str
) -> tuple[list[dict[str, object]], list[str]]:
    if len(raw_tokens) > _MAX_TOKENS:
        return [], ["morphology_token_limit_exceeded"]
    valid: list[dict[str, object]] = []
    errors: list[str] = []
    previous_end = 0
    for index, raw in enumerate(raw_tokens):
        if not isinstance(raw, Mapping):
            errors.append(f"invalid_token_mapping:{index}")
            continue
        start = raw.get("start")
        end = raw.get("end")
        surface = raw.get("surface")
        if (
            not isinstance(start, int)
            or isinstance(start, bool)
            or not isinstance(end, int)
            or isinstance(end, bool)
            or start < 0
            or end <= start
            or end > len(source_text)
        ):
            errors.append(f"invalid_token_span:{index}")
            continue
        if start < previous_end:
            errors.append(f"non_monotonic_or_overlapping_token:{index}")
            continue
        if not isinstance(surface, str) or source_text[start:end] != surface:
            errors.append(f"token_surface_mismatch:{index}")
            continue
        token = dict(raw)
        token.update({"start": start, "end": end, "surface": surface})
        valid.append(token)
        previous_end = end
    if not valid and not errors:
        errors.append("morphology_tokens_missing")
    return valid, errors


def _find_patterns(
    source_text: str,
    tokens: list[dict[str, object]],
    *,
    context_start: int,
) -> list[dict[str, object]]:
    significant = [token for token in tokens if not _space_token(token)]
    fenced_ranges = _fenced_code_ranges(source_text)
    patterns: list[dict[str, object]] = []
    measure_pattern = "|".join(re.escape(value) for value in all_measure_terms())
    comparison_pattern = "|".join(re.escape(value) for value in all_comparison_terms())
    scalar_tail_re = re.compile(
        rf"^\s*に\s*(?P<measure>{measure_pattern})\s*(?:が|の)\s*"
        rf"(?P<comparator>{comparison_pattern})\s*(?P<target>{_TARGET_RE})"
        r"(?P<selection>\s*(?:は|を).*)$"
    )
    explicit_tail_re = re.compile(
        rf"^\s*の\s*(?P<target>{_TARGET_RE})(?P<selection>\s*(?:は|を).*)$"
    )

    for index, token in enumerate(significant):
        if _token_surface(token) != "次" or _token_lemma(token) != "次":
            continue
        previous = _previous_non_ignorable(significant, index)
        if previous is None or _token_surface(previous) != "の":
            continue
        if _position_in_ranges(int(token["start"]), fenced_ranges):
            continue
        start, end = _clause_span(source_text, int(previous["start"]), int(token["end"]))
        clause = source_text[start:end]
        reference = _reference_before(source_text, tokens, start, int(previous["start"]))
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
        scalar_match = scalar_tail_re.fullmatch(tail_text)
        pattern: dict[str, object] | None = None
        if scalar_match is not None:
            measure = scalar_match.group("measure")
            comparator = scalar_match.group("comparator")
            resolved_scale = match_directional_axis(measure, comparator)
            target = scalar_match.group("target")
            selection = scalar_match.group("selection")
            if resolved_scale is None or not _selection_tail(selection, target):
                continue
            scale, order_axis, pole = resolved_scale
            comparison_span = (
                int(token["end"]) + scalar_match.start("comparator"),
                int(token["end"]) + scalar_match.end("comparator"),
            )
            comparison_signal = _comparison_evidence(tokens, comparison_span, comparator)
            if comparison_signal is None:
                continue
            order = _order_for_scale(
                source_text,
                clause,
                start,
                scale,
                order_axis,
                reference_start=int(reference["start"]),
                reference_id=str(reference["surface"]),
                target=target,
                question_start=start,
                question_end=end,
                context_start=context_start,
            )
            pattern = {
                "pattern_family": "reference_next_registered_scalar",
                "reference": reference["surface"],
                "reference_evidence": reference,
                "scale": scale,
                "order_axis": order_axis,
                "measure": measure,
                "comparison_term": comparator,
                "comparison_pole": pole,
                "target": target,
                "selection_tail": selection,
                "source_span": _span(start, end, clause),
                "morphology_signal": {
                    "reference": reference,
                    "next": _token_evidence(token),
                    "comparison": comparison_signal,
                },
                "direction_binding": order,
            }
        else:
            explicit_match = explicit_tail_re.fullmatch(tail_text)
            if explicit_match is not None:
                target = explicit_match.group("target")
                selection = explicit_match.group("selection")
                if not _selection_tail(selection, target):
                    continue
                discovered = _discover_explicit_order(
                    source_text,
                    clause,
                    start,
                    reference_start=int(reference["start"]),
                    reference_id=str(reference["surface"]),
                    target=target,
                    question_start=start,
                    question_end=end,
                    context_start=context_start,
                )
                scale = discovered.get("scale")
                order_axis = discovered.get("order_axis")
                if not isinstance(scale, ScaleSpec) or not isinstance(
                    order_axis, OrderAxisSpec
                ):
                    continue
                order = dict(discovered)
                order.pop("scale", None)
                order.pop("order_axis", None)
                pattern = {
                    "pattern_family": "explicit_registered_scalar_order_successor",
                    "reference": reference["surface"],
                    "reference_evidence": reference,
                    "scale": scale,
                    "order_axis": order_axis,
                    "measure": order_axis.measure_terms[0],
                    "comparison_term": (
                        scale.canonical_high_term
                        if order.get("direction") == "scale_high_pole_first"
                        else scale.canonical_low_term
                    ),
                    "comparison_pole": (
                        "high"
                        if order.get("direction") == "scale_high_pole_first"
                        else "low"
                    ),
                    "target": target,
                    "selection_tail": selection,
                    "source_span": _span(start, end, clause),
                    "morphology_signal": {
                        "reference": reference,
                        "next": _token_evidence(token),
                    },
                    "direction_binding": order,
                }
        if pattern is not None:
            patterns.append(pattern)
            if len(patterns) >= _MAX_PATTERNS:
                break
    return patterns


def _evaluate_pattern(
    source_text: str,
    pattern: dict[str, object],
    *,
    context_start: int,
) -> dict[str, object]:
    reference = str(pattern["reference"])
    scale = pattern["scale"]
    order_axis = pattern["order_axis"]
    direction_binding = pattern["direction_binding"]
    assert isinstance(scale, ScaleSpec)
    assert isinstance(order_axis, OrderAxisSpec)
    assert isinstance(direction_binding, dict)
    binding = dict(direction_binding)
    binding.setdefault(
        "required_constraint",
        {
            "scale_id": scale.scale_id,
            "order_axis_id": order_axis.axis_id,
            "allowed_directions": [
                "scale_high_pole_first",
                "scale_low_pole_first",
            ],
            "same_scale_required": True,
            "same_order_axis_required": True,
        },
    )
    pattern_span = pattern["source_span"]
    reference_evidence = pattern["reference_evidence"]
    assert isinstance(pattern_span, Mapping)
    assert isinstance(reference_evidence, Mapping)
    expression_start = int(reference_evidence["start"])
    expression_end = int(pattern_span["end"])
    frame: dict[str, object] = {
        "frame_id": f"decision-frame:{pattern['source_span']['start']}:{pattern['source_span']['end']}",
        "pattern_family": pattern["pattern_family"],
        "status": "direction_unbound",
        "derivation_status": "derived",
        "source_span": pattern["source_span"],
        "direction_open_expression": {
            "kind": "successor_in_scalar_order",
            "source_span": _span(
                expression_start,
                expression_end,
                source_text[expression_start:expression_end],
            ),
            "scale_id": scale.scale_id,
            "order_axis_id": order_axis.axis_id,
            "surface_comparison_pole": pattern["comparison_pole"],
            "direction_options": [
                "scale_high_pole_first",
                "scale_low_pole_first",
            ],
        },
        "direction_binding": binding,
        "operation": {
            "family": "successor_in_scalar_order",
            "reference_id": reference,
            "scale_id": scale.scale_id,
            "order_axis_id": order_axis.axis_id,
            "measure": pattern["measure"],
            "comparison_pole": pattern["comparison_pole"],
            "target": pattern["target"],
            "offset": 1,
        },
        "morphology_signal": pattern["morphology_signal"],
        "required_conditions": ["order_direction"],
        "conditional_conditions": [],
        "missing_conditions": [],
        "interpretation_candidates": [],
        "repair_candidates": [],
        "unknown_reasons": [],
        "evaluations": [],
    }
    impact_evidence = _impact_evidence(
        source_text,
        pattern,
        binding=binding,
        context_start=context_start,
    )
    if impact_evidence.get("status") != "not_available":
        frame["impact_evidence"] = impact_evidence

    binding_status = str(binding.get("status", "missing"))
    if binding_status == "bound":
        frame["status"] = "direction_bound"
        frame["derivation_status"] = "satisfied"
        frame["evaluations"] = _evaluations(binding_status)
        return frame

    if binding_status == "conflict":
        frame["status"] = "direction_conflict"
        frame["derivation_status"] = "conflict"
        frame["missing_conditions"] = ["unambiguous_order_direction"]
        frame["unknown_reasons"] = [
            str(binding.get("reason", "multiple_order_directions"))
        ]
    else:
        frame["status"] = "direction_unbound"
        frame["missing_conditions"] = ["order_direction"]
    frame["interpretation_candidates"] = _interpretation_candidates(pattern, None)
    frame["repair_candidates"] = [
        {
            "condition": item["condition"],
            "rewrite": item["rewrite"],
            "outcome_status": "not_evaluated",
        }
        for item in frame["interpretation_candidates"]
    ]
    frame["evaluations"] = _evaluations(binding_status)
    return frame


def _evaluations(binding_status: str) -> list[dict[str, object]]:
    eligible = binding_status in {"missing", "conflict"}
    return [
        {
            "rule_id": PRECONDITION_ORDER_DIRECTION_RULE_ID,
            "status": "derived" if eligible else "satisfied",
            "claim_level": "direction_binding_gap",
            "finding_eligible": eligible,
            "match_status": "matched",
            "confidence": "medium",
            "binding_status": binding_status,
            "candidate_conditions": [
                "scale_high_pole_first",
                "scale_low_pole_first",
            ],
        }
    ]


def _impact_evidence(
    source_text: str,
    pattern: Mapping[str, object],
    *,
    binding: Mapping[str, object],
    context_start: int,
) -> dict[str, object]:
    """Build optional numeric evidence without affecting the primary audit."""

    scale = pattern["scale"]
    assert isinstance(scale, ScaleSpec)
    projection = numeric_projection_for_scale(scale)
    base: dict[str, object] = {
        "status": "not_available",
        "authority": "auxiliary_only",
        "affects_primary_finding": False,
        "candidate_frames": [],
        "outcome_invariant": None,
        "unknown_reasons": [],
    }
    if projection is None:
        base["unknown_reasons"] = ["scale_numeric_projection_not_supported"]
        return base

    pattern_span = pattern["source_span"]
    assert isinstance(pattern_span, Mapping)
    observations, errors, meta = _observations(
        source_text,
        count_span=(int(pattern_span["start"]), int(pattern_span["end"])),
        scale=scale,
        reference=str(pattern["reference"]),
        target=str(pattern["target"]),
        context_start=context_start,
    )
    membership = meta.get("membership_evidence")
    if isinstance(membership, Mapping):
        base["candidate_membership_evidence"] = dict(membership)
    if errors:
        base["unknown_reasons"] = errors
        return base

    if binding.get("status") == "bound":
        outcome = _outcome_witness(
            observations,
            str(pattern["reference"]),
            str(binding["direction"]),
            scale,
        )
        if outcome is None:
            base["unknown_reasons"] = ["successor_not_defined_for_bound_direction"]
            return base
        base.update({"status": "observed_outcome", "candidate_frames": [outcome]})
        return base

    high = _outcome_witness(
        observations,
        str(pattern["reference"]),
        "scale_high_pole_first",
        scale,
    )
    low = _outcome_witness(
        observations,
        str(pattern["reference"]),
        "scale_low_pole_first",
        scale,
    )
    if high is None or low is None:
        base["unknown_reasons"] = [
            "successor_not_defined_in_both_direction_hypotheses"
        ]
        return base
    invariant = high["outcome"]["entity_id"] == low["outcome"]["entity_id"]
    base.update(
        {
            "status": "outcome_invariant" if invariant else "outcome_divergent",
            "candidate_frames": [high, low],
            "outcome_invariant": invariant,
        }
    )
    return base


def _interpretation_candidates(
    pattern: Mapping[str, object], observation_meta: Mapping[str, object] | None
) -> list[dict[str, object]]:
    scale = pattern["scale"]
    order_axis = pattern["order_axis"]
    assert isinstance(scale, ScaleSpec)
    assert isinstance(order_axis, OrderAxisSpec)
    measure = str(pattern["measure"])
    reference = str(pattern["reference"])
    target = str(pattern["target"])
    tail = str(pattern["selection_tail"])
    prefix = ""
    if observation_meta:
        count = observation_meta.get("declared_count")
        kind = observation_meta.get("declared_kind")
        if isinstance(count, int) and isinstance(kind, str):
            prefix = f"この{count}{kind}の中で、"
    candidates: list[dict[str, object]] = []
    for direction, term in (
        ("scale_high_pole_first", scale.canonical_high_term),
        ("scale_low_pole_first", scale.canonical_low_term),
    ):
        rewrite = f"{prefix}{measure}が{term}順に並べたとき、{reference}の次の{target}{tail}"
        candidates.append(
            {
                "condition": {
                    "order_direction": direction,
                    "scale_id": scale.scale_id,
                    "order_axis_id": order_axis.axis_id,
                    "order_term": term,
                },
                "rewrite": rewrite,
                "outcome_status": "not_evaluated",
            }
        )
    return candidates


def _observations(
    source_text: str,
    *,
    count_span: tuple[int, int],
    scale: ScaleSpec,
    reference: str,
    target: str,
    context_start: int,
) -> tuple[list[dict[str, object]], list[str], dict[str, object]]:
    declared, count_errors = _declared_candidate_counts(
        source_text, required_span=count_span, target=target
    )
    if count_errors:
        return [], count_errors, {}
    if not declared:
        return [], ["candidate_set_count_not_declared"], {}
    if len(declared) > 1:
        return [], ["conflicting_candidate_count_declarations"], {}
    declared_count, declared_kind = next(iter(declared))

    unit_re = numeric_unit_pattern(scale)
    exact_re = re.compile(
        rf"^(?P<value>{_NUMERIC_VALUE_RE})\s*(?P<unit>{unit_re})$",
        re.IGNORECASE,
    )
    unit_search_re = re.compile(unit_re, re.IGNORECASE)
    fenced_ranges = _fenced_code_ranges(source_text)
    row_candidates: list[dict[str, object]] = []
    for match in _ROW_SEGMENT_RE.finditer(source_text):
        if _position_in_ranges(match.start("label"), fenced_ranges):
            continue
        raw = match.group("raw").strip()
        if not (_NUMERICISH_RE.search(raw) or unit_search_re.search(raw)):
            continue
        row: dict[str, object] = {
            "label": match.group("label"),
            "raw": raw,
            "start": match.start("label"),
            "end": match.end("raw"),
            "status": "invalid",
            "errors": [],
        }
        exact = exact_re.fullmatch(raw)
        if exact is None:
            row["errors"] = ["unsupported_value_or_unit"]
        else:
            value_text = exact.group("value")
            try:
                value = Decimal(value_text)
            except InvalidOperation:
                row["errors"] = ["invalid_numeric_value"]
            else:
                unit = normalize_unit(scale, exact.group("unit"))
                if unit is None:
                    row["errors"] = ["unsupported_value_or_unit"]
                else:
                    row.update(
                        {
                            "status": "exact",
                            "value": value_text,
                            "unit": unit,
                            "_numeric_value": value,
                        }
                    )
        row_candidates.append(row)
        if len(row_candidates) > _MAX_OBSERVATIONS:
            return [], ["candidate_set_limit_exceeded"], {}

    groups = _row_groups(source_text, row_candidates)
    matching_groups = [
        group
        for group in groups
        if any(str(row["label"]) == reference for row in group)
    ]
    if not matching_groups:
        if not groups:
            return [], ["candidate_set_not_closed"], {}
        return [], ["reference_entity_not_in_candidate_set"], {}
    if len(matching_groups) > 1:
        return [], ["multiple_candidate_regions_match_reference"], {}
    rows = matching_groups[0]
    errors: list[str] = []
    observations: list[dict[str, object]] = []
    seen_exact: dict[str, dict[str, object]] = {}
    seen_folded: dict[str, str] = {}
    for row in rows:
        errors.extend(str(item) for item in _sequence(row.get("errors", [])))
        label = str(row["label"])
        folded = unicodedata.normalize("NFKC", label).casefold()
        if label.casefold() in _NON_ENTITY_LABELS or folded in _NON_ENTITY_LABELS:
            errors.append("aggregate_row_in_candidate_set")
        previous_surface = seen_folded.setdefault(folded, label)
        if previous_surface != label:
            errors.append("confusable_candidate_labels")
        if label in seen_exact:
            previous = seen_exact[label]
            if previous.get("_numeric_value") != row.get("_numeric_value"):
                errors.append("duplicate_identifier_conflict")
            else:
                errors.append("duplicate_identifier_repeated")
            continue
        seen_exact[label] = row
        if row.get("status") != "exact":
            continue
        observation = {
            "entity_id": label,
            "value": str(row["value"]),
            "unit": str(row["unit"]),
            "evidence_span": _span(
                int(row["start"]),
                int(row["end"]),
                source_text[int(row["start"]) : int(row["end"])],
            ),
            "_numeric_value": row["_numeric_value"],
        }
        observations.append(observation)

    if len(rows) != declared_count:
        errors.append("declared_candidate_count_mismatch")
    membership_evidence = _candidate_membership_evidence(
        source_text,
        rows=rows,
        count_span=count_span,
        declared_count=declared_count,
        declared_kind=declared_kind,
        reference=reference,
        target=target,
        context_start=context_start,
    )
    if membership_evidence is None:
        errors.append("candidate_membership_not_established")
    if len(observations) < 3:
        errors.append("candidate_set_not_closed")
    units = {str(item["unit"]) for item in observations}
    if len(units) != 1:
        errors.append("unit_normalization_not_established")
    values = [item["_numeric_value"] for item in observations]
    if len(values) != len(set(values)):
        errors.append("tie_policy_not_established")
    if errors:
        return [], sorted(set(errors)), {
            "declared_count": declared_count,
            "declared_kind": declared_kind,
            "membership_evidence": membership_evidence,
        }
    return observations, [], {
        "declared_count": declared_count,
        "declared_kind": declared_kind,
        "membership_evidence": membership_evidence,
    }


def _row_groups(
    source_text: str, rows: list[dict[str, object]]
) -> list[list[dict[str, object]]]:
    groups: list[list[dict[str, object]]] = []
    for row in rows:
        if not groups:
            groups.append([row])
            continue
        previous = groups[-1][-1]
        gap = source_text[int(previous["end"]) : int(row["start"])]
        if _candidate_rows_are_contiguous(gap):
            groups[-1].append(row)
        else:
            groups.append([row])
    return groups


def _candidate_membership_evidence(
    source_text: str,
    *,
    rows: list[dict[str, object]],
    count_span: tuple[int, int],
    declared_count: int,
    declared_kind: str,
    reference: str,
    target: str,
    context_start: int,
) -> dict[str, object] | None:
    """Return source evidence that binds one row group to the declared set.

    This deliberately does not infer real-world entity types from names or
    morphology.  General labels require a directly adjacent candidate-kind
    header.  The legacy single-uppercase identifier form remains accepted as
    an explicit opaque identifier convention, not as the only public form.
    """

    if not rows or len(rows) != declared_count:
        return None
    declarations = [
        match
        for match in _DECLARED_CANDIDATE_COUNT_RE.finditer(source_text)
        if count_span[0] <= match.start()
        and match.end() <= count_span[1]
        and _parse_candidate_count(match.group("count")) == declared_count
        and match.group("kind") == declared_kind
    ]
    if len(declarations) != 1:
        return None
    declaration = declarations[0]
    row_start = int(rows[0]["start"])
    row_end = int(rows[-1]["end"])

    labels = [str(row["label"]) for row in rows]
    membership_form = ""
    header_span: dict[str, object] | None = None
    header_start: int | None = None
    if all(_OPAQUE_CANDIDATE_LABEL_RE.fullmatch(label) for label in labels):
        membership_form = "opaque_identifier_table"
    else:
        headers: list[re.Match[str]] = []
        for match in _CANDIDATE_MEMBERSHIP_HEADER_RE.finditer(source_text, 0, row_start):
            header_kind = match.group("declared_kind") or match.group(
                "parenthesized_kind"
            )
            if not _candidate_kinds_equivalent(header_kind, declared_kind, target):
                continue
            if _single_line_gap(source_text[match.end() : row_start]):
                headers.append(match)
        if len(headers) != 1:
            return None
        header = headers[0]
        membership_form = "typed_candidate_header"
        header_start = header.start()
        header_span = _span(
            header.start(),
            header.end(),
            source_text[header.start() : header.end()],
        )

    table_start = header_start if header_start is not None else row_start
    if row_end <= count_span[0] and _single_line_gap(
        source_text[row_end : count_span[0]]
    ):
        binding_method = f"adjacent_{membership_form}"
    elif (
        count_span[1] <= context_start <= table_start
        and _complete_context_table_prefix(source_text[context_start:table_start])
        and not source_text[row_end:].strip()
    ):
        binding_method = f"complete_context_{membership_form}"
    else:
        return None

    evidence: dict[str, object] = {
        "membership_status": "source_declared",
        "binding_method": binding_method,
        "declared_count": declared_count,
        "declared_kind": declared_kind,
        "selection_target": target,
        "member_ids": labels,
        "reference_id": reference,
        "declaration_span": _span(
            declaration.start(),
            declaration.end(),
            source_text[declaration.start() : declaration.end()],
        ),
        "row_group_span": _span(
            row_start,
            row_end,
            source_text[row_start:row_end],
        ),
    }
    if header_span is not None:
        evidence["header_span"] = header_span
    return evidence


def _single_line_gap(value: str) -> bool:
    return re.fullmatch(r"[ \t]*(?:\r?\n)?[ \t]*", value) is not None


def _complete_context_table_prefix(value: str) -> bool:
    if not value.strip():
        return True
    matches = list(_ORDER_HEADER_RE.finditer(value))
    return (
        len(matches) == 1
        and not value[: matches[0].start()].strip()
        and not value[matches[0].end() :].strip()
    )


def _outcome_witness(
    observations: list[dict[str, object]],
    reference: str,
    direction: str,
    scale: ScaleSpec,
) -> dict[str, object] | None:
    projection = numeric_projection_for_scale(scale)
    if projection is None:
        return None
    high_descending = projection.high_pole_numeric_order == "descending"
    reverse = high_descending if direction == "scale_high_pole_first" else not high_descending
    ordered = sorted(observations, key=lambda item: item["_numeric_value"], reverse=reverse)
    index = next(
        (index for index, item in enumerate(ordered) if str(item["entity_id"]) == reference),
        None,
    )
    if index is None or index + 1 >= len(ordered):
        return None
    outcome = ordered[index + 1]
    return {
        "frame_id": direction,
        "hypothesis": {
            "order_direction": direction,
            "scale_id": scale.scale_id,
        },
        "numeric_projection": {
            "order": "descending" if reverse else "ascending",
            "unit": str(ordered[0]["unit"]),
        },
        "ordered_entity_ids": [str(item["entity_id"]) for item in ordered],
        "outcome": {"kind": "entity", "entity_id": str(outcome["entity_id"])},
        "evidence_spans": [item["evidence_span"] for item in ordered],
    }


def _order_for_scale(
    source_text: str,
    clause: str,
    offset: int,
    scale: ScaleSpec,
    order_axis: OrderAxisSpec,
    *,
    reference_start: int,
    reference_id: str,
    target: str,
    question_start: int,
    question_end: int,
    context_start: int,
) -> dict[str, object]:
    local = _explicit_order(
        clause,
        offset,
        scale,
        order_axis,
        reference_start=reference_start,
    )
    header = _explicit_order_headers(
        source_text,
        scale=scale,
        order_axis=order_axis,
        reference_id=reference_id,
        target=target,
        question_start=question_start,
        question_end=question_end,
        context_start=context_start,
    )
    accepted = [
        *list(_sequence(local.get("accepted_evidence", []))),
        *list(_sequence(header.get("accepted_evidence", []))),
    ]
    rejected = [
        *list(_sequence(local.get("rejected_evidence", []))),
        *list(_sequence(header.get("rejected_evidence", []))),
    ]
    resolution = resolve_direction_binding(
        [item for item in accepted if isinstance(item, Mapping)],
        conflict_reason="multiple_order_directions",
    )
    result: dict[str, object] = {
        "status": resolution.status,
        "search_scope": _direction_search_scope(
            source_text,
            clause=clause,
            offset=offset,
            context_start=context_start,
        ),
        "accepted_evidence": accepted,
        "rejected_evidence": rejected,
        "unknown_reasons": [],
    }
    if resolution.status == "conflict":
        result.update(
            {
                "reason": resolution.reason,
            }
        )
    elif resolution.status == "bound":
        result["direction"] = resolution.selected_direction
    return result


def _explicit_order(
    clause: str,
    offset: int,
    scale: ScaleSpec,
    order_axis: OrderAxisSpec,
    *,
    reference_start: int,
) -> dict[str, object]:
    matches: list[tuple[str, re.Match[str]]] = []

    def add_explicit_matches(
        measure: str,
        order_surface_pattern: str,
        direction: str,
    ) -> None:
        bound_re = re.compile(
            rf"(?P<order>{re.escape(measure)}\s*(?:が|の|を)?\s*"
            rf"{order_surface_pattern}){_ARRANGEMENT_SUFFIX}"
        )
        for item in bound_re.finditer(clause):
            order_surface = _ANY_ORDER_RE.search(
                clause,
                item.start("order"),
                item.end("order"),
            )
            resolved = (
                _resolve_order_candidate(clause, order_surface)
                if order_surface is not None
                else None
            )
            if (
                resolved is not None
                and resolved[1] is not None
                and resolved[1].axis_id != order_axis.axis_id
            ):
                continue
            matches.append((direction, item))

    for direction, terms in (
        ("scale_high_pole_first", scale.high_terms),
        ("scale_low_pole_first", scale.low_terms),
    ):
        for measure in order_axis.measure_terms:
            for term in terms:
                add_explicit_matches(
                    measure,
                    rf"{re.escape(term)}\s*順",
                    direction,
                )
                add_explicit_matches(
                    measure,
                    rf"{re.escape(term)}\s*"
                    r"(?:もの\s*から\s*順|方\s*から(?:\s*順)?)",
                    direction,
                )
        for term in terms:
            if _term_uniquely_identifies_scale(term, scale):
                bare_re = re.compile(
                    rf"(?P<order>{re.escape(term)}\s*順)"
                    rf"{_ARRANGEMENT_SUFFIX}"
                )
                matches.extend(
                    (direction, item)
                    for item in bare_re.finditer(clause)
                    if _bare_order_can_inherit_axis(clause, item)
                )

    for term, direction in _ORDINAL_ORDER_DIRECTIONS.items():
        for measure in order_axis.measure_terms:
            add_explicit_matches(
                measure,
                rf"{re.escape(term)}\s*順",
                direction,
            )

    unique_matches: list[tuple[str, re.Match[str]]] = []
    for direction, item in sorted(
        matches,
        key=lambda pair: (
            -(pair[1].end() - pair[1].start()),
            pair[1].start(),
            pair[0],
        ),
    ):
        if any(
            existing_direction == direction
            and existing.start() <= item.start()
            and item.end() <= existing.end()
            for existing_direction, existing in unique_matches
        ):
            continue
        unique_matches.append((direction, item))
    matches = sorted(unique_matches, key=lambda pair: (pair[1].start(), pair[1].end()))

    accepted: list[dict[str, object]] = []
    rejected: list[dict[str, object]] = []
    raw_order_spans = [
        (item.start("order"), item.end("order")) for _direction, item in matches
    ]
    negated_spans = [
        (item.start(), item.end())
        for regex in (_NEGATED_ORDER_RE, _NEGATED_ARRANGEMENT_RE)
        for item in regex.finditer(clause)
    ]
    unsafe_discourse = _UNSAFE_ORDER_DISCOURSE_RE.search(clause) is not None
    local_reference_start = reference_start - offset
    for direction, match in matches:
        reason = ""
        order_span = (match.start("order"), match.end("order"))
        if any(_ranges_overlap(order_span, span) for span in negated_spans):
            reason = "negated"
        elif _position_in_inline_quote(clause, match.start("order")):
            reason = "quoted_or_code_example"
        elif unsafe_discourse:
            reason = "historical_hypothetical_or_tentative"
        else:
            attachment_rejection = _direct_order_attachment_rejection_reason(
                clause,
                match,
                reference_start=local_reference_start,
            )
            if attachment_rejection:
                reason = attachment_rejection
        evidence = _direction_binding_evidence(
            binding_site="same_clause_arrangement",
            scale_id=scale.scale_id,
            order_axis_id=order_axis.axis_id,
            value=direction,
            source_span=_span(
                offset + match.start("order"),
                offset + match.end("order"),
                match.group("order"),
            ),
            relation_span=_span(
                offset + match.start(),
                offset + match.end(),
                match.group(0),
            ),
            rejection_reason=reason,
            axis_resolution=(
                "explicit_measure"
                if any(
                    measure in match.group("order")
                    for measure in order_axis.measure_terms
                )
                else "inherited_from_target_frame"
            ),
        )
        (rejected if reason else accepted).append(evidence)

    for item in _ANY_ORDER_RE.finditer(clause):
        if any(start <= item.start() and item.end() <= end for start, end in raw_order_spans):
            continue
        resolved = _resolve_order_candidate(clause, item)
        observed_scale = resolved[0].scale_id if resolved is not None else ""
        observed_axis = (
            resolved[1].axis_id
            if resolved is not None and resolved[1] is not None
            else ""
        )
        observed_direction = resolved[2] if resolved is not None else ""
        rejected.append(
            _direction_binding_evidence(
                binding_site="target_clause",
                scale_id=observed_scale or "unresolved",
                order_axis_id=observed_axis or "unresolved",
                value=observed_direction,
                source_span=_span(
                    offset + item.start(),
                    offset + item.end(),
                    item.group(0),
                ),
                rejection_reason=(
                    "quoted_or_code_example"
                    if _position_in_inline_quote(clause, item.start())
                    else (
                        "different_scale"
                        if observed_scale and observed_scale != scale.scale_id
                        else (
                            "different_order_axis"
                            if observed_axis and observed_axis != order_axis.axis_id
                            else "unsupported_binding_form"
                        )
                    )
                ),
            )
        )

    resolution = resolve_direction_binding(
        accepted,
        conflict_reason="multiple_order_directions",
    )
    status = resolution.status
    result: dict[str, object] = {
        "status": status,
        "accepted_evidence": accepted,
        "rejected_evidence": rejected,
    }
    if status == "bound":
        result["direction"] = resolution.selected_direction
    elif status == "conflict":
        result["reason"] = resolution.reason
    return result


def _discover_explicit_order(
    source_text: str,
    clause: str,
    offset: int,
    *,
    reference_start: int,
    reference_id: str,
    target: str,
    question_start: int,
    question_end: int,
    context_start: int,
) -> dict[str, object]:
    resolved: list[tuple[ScaleSpec, OrderAxisSpec, dict[str, object]]] = []
    conflicts: list[tuple[ScaleSpec, OrderAxisSpec, dict[str, object]]] = []
    for scale in SCALE_SPECS:
        for order_axis in scale.axes:
            order = _order_for_scale(
                source_text,
                clause,
                offset,
                scale,
                order_axis,
                reference_start=reference_start,
                reference_id=reference_id,
                target=target,
                question_start=question_start,
                question_end=question_end,
                context_start=context_start,
            )
            if order.get("status") == "bound":
                resolved.append((scale, order_axis, order))
            elif order.get("status") == "conflict" and _axis_terms_present(
                clause, scale, order_axis
            ):
                conflicts.append((scale, order_axis, order))
    if len(resolved) == 1:
        scale, order_axis, order = resolved[0]
        return {**order, "scale": scale, "order_axis": order_axis}
    if len(resolved) > 1:
        return {"status": "conflict", "reason": "multiple_order_scales"}
    if len(conflicts) == 1:
        scale, order_axis, order = conflicts[0]
        return {**order, "scale": scale, "order_axis": order_axis}
    return {"status": "missing"}


def _explicit_order_headers(
    source_text: str,
    *,
    scale: ScaleSpec,
    order_axis: OrderAxisSpec,
    reference_id: str,
    target: str,
    question_start: int,
    question_end: int,
    context_start: int,
) -> dict[str, object]:
    fenced_ranges = _fenced_code_ranges(source_text)
    accepted: list[dict[str, object]] = []
    rejected: list[dict[str, object]] = []
    for match in _ORDER_HEADER_RE.finditer(source_text):
        if _position_in_ranges(match.start(), fenced_ranges):
            if _header_mentions_scale(match, scale):
                rejected.append(
                    _direction_binding_evidence(
                        binding_site="candidate_table_header",
                        scale_id=scale.scale_id,
                        order_axis_id="unresolved",
                        value="",
                        source_span=_span(
                            match.start("value"),
                            match.end("value"),
                            match.group("value"),
                        ),
                        rejection_reason="quoted_or_code_example",
                        axis_resolution="unresolved",
                    )
                )
            continue
        current_rejection_reason = _order_header_binding_rejection_reason(
            source_text,
            match,
            reference_id=reference_id,
            target=target,
            question_start=question_start,
            question_end=question_end,
            context_start=context_start,
        )
        resolved = _resolve_header(match)
        if resolved is None:
            if _header_mentions_scale(match, scale):
                rejected.append(
                    _direction_binding_evidence(
                        binding_site="candidate_table_header",
                        scale_id=scale.scale_id,
                        order_axis_id="unresolved",
                        value="",
                        source_span=_span(
                            match.start("value"),
                            match.end("value"),
                            match.group("value"),
                        ),
                        rejection_reason="unsupported_binding_form",
                        axis_resolution="unresolved",
                    )
                )
            continue
        resolved_scale, resolved_axis, direction = resolved
        reason = ""
        if resolved_scale.scale_id != scale.scale_id:
            reason = "different_scale"
        elif resolved_axis is not None and resolved_axis.axis_id != order_axis.axis_id:
            reason = "different_order_axis"
        elif resolved_axis is None and not _term_uniquely_identifies_scale(
            re.sub(r"[ \t]*順[ \t]*$", "", match.group("value")).strip(),
            scale,
        ):
            reason = "order_axis_not_established"
        elif current_rejection_reason:
            reason = current_rejection_reason
        evidence = _direction_binding_evidence(
            binding_site="current_candidate_table_header",
            scale_id=resolved_scale.scale_id,
            order_axis_id=(
                resolved_axis.axis_id
                if resolved_axis is not None
                else order_axis.axis_id
            ),
            value=direction,
            source_span=_span(
                match.start("value"),
                match.end("value"),
                match.group("value"),
            ),
            relation_span=_span(
                match.start(),
                match.end(),
                match.group(0),
            ),
            rejection_reason=reason,
            axis_resolution=(
                "explicit_measure"
                if resolved_axis is not None
                else "inherited_from_target_frame"
            ),
        )
        (rejected if reason else accepted).append(evidence)
    resolution = resolve_direction_binding(
        accepted,
        conflict_reason="multiple_order_directions",
    )
    status = resolution.status
    result: dict[str, object] = {
        "status": status,
        "accepted_evidence": accepted,
        "rejected_evidence": rejected,
    }
    if status == "bound":
        result["direction"] = resolution.selected_direction
    elif status == "conflict":
        result["reason"] = resolution.reason
    return result


def _order_term_from_surface(value: str) -> str | None:
    for regex in (_CLASSIC_ORDER_VALUE_RE, _POLE_ORIGIN_ORDER_VALUE_RE):
        match = regex.fullmatch(value.strip())
        if match is not None:
            return match.group("term").strip()
    return None


def _direction_for_order_term(scale: ScaleSpec, term: str) -> str:
    ordinal_direction = _ORDINAL_ORDER_DIRECTIONS.get(term)
    if ordinal_direction is not None:
        return ordinal_direction
    if term in scale.high_terms:
        return "scale_high_pole_first"
    if term in scale.low_terms:
        return "scale_low_pole_first"
    return ""


def _scale_axis_for_measure(measure: str) -> tuple[ScaleSpec, OrderAxisSpec] | None:
    order_axis = axis_for_measure(measure)
    if order_axis is None:
        return None
    owners = [scale for scale in SCALE_SPECS if order_axis in scale.axes]
    if len(owners) != 1:
        return None
    return owners[0], order_axis


def _resolve_header(
    match: re.Match[str],
) -> tuple[ScaleSpec, OrderAxisSpec | None, str] | None:
    raw_measure = (match.group("measure") or "").strip()
    raw_value = match.group("value").strip()
    term = _order_term_from_surface(raw_value)
    if term is None or _POLE_ORIGIN_ORDER_VALUE_RE.fullmatch(raw_value) is not None:
        return None
    if raw_measure:
        ordinal_direction = _ORDINAL_ORDER_DIRECTIONS.get(term)
        if ordinal_direction is not None:
            resolved_axis = _scale_axis_for_measure(raw_measure)
            if resolved_axis is None:
                return None
            scale, order_axis = resolved_axis
            return scale, order_axis, ordinal_direction
        matched = match_directional_axis(raw_measure, term)
        if matched is None:
            return None
        scale, order_axis, pole = matched
        direction = (
            "scale_high_pole_first" if pole == "high" else "scale_low_pole_first"
        )
        return scale, order_axis, direction
    return _resolve_order_surface(raw_value)


def _header_mentions_scale(match: re.Match[str], scale: ScaleSpec) -> bool:
    text = f"{match.group('measure') or ''}{match.group('value')}"
    return any(term in text for term in (*scale.measure_terms, *scale.high_terms, *scale.low_terms))


def _direction_binding_evidence(
    *,
    binding_site: str,
    scale_id: str,
    order_axis_id: str,
    value: str,
    source_span: Mapping[str, object],
    relation_span: Mapping[str, object] | None = None,
    rejection_reason: str = "",
    axis_resolution: str = "explicit_measure",
) -> dict[str, object]:
    evidence: dict[str, object] = {
        "relation": "nonbinding" if rejection_reason else "bound",
        "binding_site": binding_site,
        "scale_id": scale_id,
        "order_axis_id": order_axis_id,
        "axis_resolution": axis_resolution,
        "value": value,
        "source_span": dict(source_span),
        "authority": "deterministic_source_grammar",
    }
    if relation_span is not None:
        evidence["relation_span"] = dict(relation_span)
    if rejection_reason:
        evidence["rejection_reasons"] = [rejection_reason]
    return evidence


def _direction_search_scope(
    source_text: str,
    *,
    clause: str,
    offset: int,
    context_start: int,
) -> dict[str, object]:
    scope: dict[str, object] = {
        "target_clause_span": _span(offset, offset + len(clause), clause),
        "checked_binding_sites": [
            "same_clause_arrangement",
            "current_candidate_table_header",
        ],
        "same_scale_required": True,
        "same_order_axis_required": True,
        "direct_attachment_required": True,
        "postposed_text_header_allowed": False,
    }
    text_end = context_start - 1 if context_start < len(source_text) else len(source_text)
    scope["text_region"] = {"start": 0, "end": max(0, text_end)}
    if context_start < len(source_text):
        scope["context_region"] = {"start": context_start, "end": len(source_text)}
    return scope


def _direct_order_attachment_rejection_reason(
    clause: str,
    match: re.Match[str],
    *,
    reference_start: int,
) -> str:
    if reference_start < match.end():
        return "postposed"
    prefix = clause[: match.start()]
    gap = clause[match.end() : reference_start]
    prefix_match = _DIRECT_ORDER_PREFIX_RE.fullmatch(prefix)
    gap_match = _DIRECT_ORDER_GAP_RE.fullmatch(gap)
    if prefix_match is None or gap_match is None:
        return "not_directly_attached_to_direction_open_expression"
    prefix_count = prefix_match.group("count")
    gap_count = gap_match.group("count")
    prefix_kind = prefix_match.group("kind")
    gap_kind = gap_match.group("kind")
    if prefix_count and gap_count:
        if _parse_candidate_count(prefix_count) != _parse_candidate_count(gap_count):
            return "different_candidate_set"
        if unicodedata.normalize("NFKC", prefix_kind) != unicodedata.normalize(
            "NFKC", gap_kind
        ):
            return "different_candidate_set"
    return ""


def _resolve_order_surface(
    value: str,
) -> tuple[ScaleSpec, OrderAxisSpec | None, str] | None:
    term = _order_term_from_surface(value)
    if term is None or term in _ORDINAL_ORDER_DIRECTIONS:
        return None
    candidates: list[tuple[ScaleSpec, OrderAxisSpec | None, str]] = []
    for scale in SCALE_SPECS:
        direction = _direction_for_order_term(scale, term)
        if direction:
            candidates.append((scale, None, direction))
    return candidates[0] if len(candidates) == 1 else None


def _resolve_order_candidate(
    clause: str, match: re.Match[str]
) -> tuple[ScaleSpec, OrderAxisSpec | None, str] | None:
    term = _order_term_from_surface(match.group(0))
    if term is None:
        return None
    prefix = clause[: match.start()]
    candidates: list[tuple[int, ScaleSpec, OrderAxisSpec, str]] = []
    for scale in SCALE_SPECS:
        for order_axis in scale.axes:
            direction = _direction_for_order_term(scale, term)
            if not direction:
                continue
            for measure in order_axis.measure_terms:
                if re.search(
                    rf"{re.escape(measure)}[ \t]*(?:が|の|を)?[ \t]*$",
                    prefix,
                ):
                    candidates.append((len(measure), scale, order_axis, direction))
    if candidates:
        longest = max(length for length, *_rest in candidates)
        owners = {
            (scale.scale_id, order_axis.axis_id, direction): (
                scale,
                order_axis,
                direction,
            )
            for length, scale, order_axis, direction in candidates
            if length == longest
        }
        if len(owners) == 1:
            return next(iter(owners.values()))
    return _resolve_order_surface(match.group(0))


def _bare_order_can_inherit_axis(clause: str, match: re.Match[str]) -> bool:
    order = _ANY_ORDER_RE.match(clause, match.start("order"))
    if order is None:
        return False
    resolved = _resolve_order_candidate(clause, order)
    return resolved is None or resolved[1] is None


def _ranges_overlap(left: tuple[int, int], right: tuple[int, int]) -> bool:
    return left[0] < right[1] and right[0] < left[1]


def _order_header_binding_rejection_reason(
    source_text: str,
    match: re.Match[str],
    *,
    reference_id: str,
    target: str,
    question_start: int,
    question_end: int,
    context_start: int,
) -> str:
    has_context = context_start < len(source_text)
    in_context = has_context and match.start() >= context_start
    segment_start = context_start if in_context else 0
    segment_end = len(source_text) if in_context else (
        max(0, context_start - 1) if has_context else len(source_text)
    )
    segment = source_text[segment_start:segment_end]
    if _UNSAFE_ORDER_HEADER_CONTEXT_RE.search(segment):
        return "outside_current_binding_scope"
    if source_text[segment_start : match.start()].strip():
        return "outside_current_binding_scope"
    if in_context:
        if not question_start < context_start:
            return "outside_current_binding_scope"
        table_region = source_text[match.end() : segment_end]
    else:
        if match.end() > question_start:
            return "outside_current_binding_scope"
        table_region = source_text[match.end() : question_start]
    if table_region.startswith("\r\n"):
        table_region = table_region[2:]
    elif table_region.startswith(("\n", "\r")):
        table_region = table_region[1:]
    lines = table_region.splitlines()
    if not lines or any(not line.strip() for line in lines):
        return "outside_current_binding_scope"
    membership_kind = ""
    membership_header = _CANDIDATE_MEMBERSHIP_HEADER_RE.fullmatch(lines[0].strip())
    if membership_header is not None:
        membership_kind = membership_header.group(
            "declared_kind"
        ) or membership_header.group("parenthesized_kind")
        lines = lines[1:]
        if not lines:
            return "candidate_set_not_established"
    rows = [_ROW_LINE_RE.fullmatch(line.strip()) for line in lines]
    if any(row is None for row in rows):
        return "outside_current_binding_scope"
    labels = [str(row.group("label")) for row in rows if row is not None]
    if reference_id not in labels:
        return "different_candidate_set"
    declared, declaration_errors = _declared_candidate_counts(
        source_text,
        required_span=(question_start, question_end),
        target=target,
    )
    if declaration_errors or len(declared) > 1:
        return "candidate_set_not_established"
    if declared:
        declared_count, declared_kind = next(iter(declared))
        if membership_kind and not _candidate_kinds_equivalent(
            membership_kind,
            declared_kind,
            target,
        ):
            return "different_candidate_set"
        if declared_count != len(labels):
            return "different_candidate_set"
    elif membership_kind and not _candidate_kind_compatible(membership_kind, target):
        return "different_candidate_set"
    return ""


def _candidate_is_nonbinding(
    source_text: str,
    start: int,
    end: int,
    clause: str,
    *,
    reference_start: int,
) -> bool:
    local_reference_start = reference_start - start
    if _BLOCK_QUOTED_CANDIDATE_RE.search(clause) or _position_in_inline_quote(
        clause, local_reference_start
    ):
        return True
    if _METALINGUISTIC_RE.search(_following_clause_window(source_text, end, end)):
        return True
    prefix = source_text[start:reference_start]
    if _NONBINDING_CANDIDATE_PREFIX_RE.search(prefix):
        return True
    return _NONBINDING_CANDIDATE_DISPOSITION_RE.fullmatch(
        _next_clause(source_text, end)
    ) is not None


def _position_in_inline_quote(value: str, position: int) -> bool:
    if position < 0 or position >= len(value):
        return False
    for opening, closing in (("「", "」"), ("『", "』"), ("“", "”"), ("‘", "’")):
        cursor = 0
        while (left := value.find(opening, cursor)) >= 0:
            right = value.find(closing, left + len(opening))
            if right < 0:
                return left <= position
            if left <= position < right + len(closing):
                return True
            cursor = right + len(closing)
    for marker in ('"', "'", "`"):
        quoted = False
        for index, character in enumerate(value):
            if character != marker or (index > 0 and value[index - 1] == "\\"):
                continue
            if index > position:
                break
            quoted = not quoted
        if quoted:
            return True
    return False


def _following_clause_window(source_text: str, start: int, end: int) -> str:
    right = len(source_text)
    for mark in "。！？!?\n\r":
        position = source_text.find(mark, end)
        if position >= 0:
            right = min(right, position + 1)
    return source_text[start:right]


def _next_clause(source_text: str, end: int) -> str:
    if end >= len(source_text):
        return ""
    start = end
    while start < len(source_text) and source_text[start].isspace():
        start += 1
    if start >= len(source_text):
        return ""
    right = len(source_text)
    for mark in "。！？!?\n\r":
        position = source_text.find(mark, start)
        if position >= 0:
            right = min(right, position + 1)
    return source_text[start:right]


def _reference_before(
    source_text: str,
    tokens: list[dict[str, object]],
    clause_start: int,
    reference_end: int,
) -> dict[str, object] | None:
    match = _REFERENCE_SURFACE_RE.search(source_text[clause_start:reference_end])
    if match is None:
        return None
    start = clause_start + match.start("reference")
    surface = match.group("reference")
    evidence_tokens = [
        token
        for token in tokens
        if start <= int(token["start"]) and int(token["end"]) <= reference_end
    ]
    if not evidence_tokens or len(evidence_tokens) > _MAX_REFERENCE_TOKENS:
        return None
    if int(evidence_tokens[0]["start"]) != start or int(evidence_tokens[-1]["end"]) != reference_end:
        return None
    if any(
        source_text[int(left["end"]) : int(right["start"])]
        for left, right in pairwise(evidence_tokens)
    ):
        return None
    noun_seen = False
    for token in evidence_tokens:
        pos = _token_pos(token)
        primary = pos[0] if pos else ""
        if primary in {"名詞", "代名詞", "接尾辞"}:
            noun_seen = True
            continue
        if primary == "補助記号" and _token_surface(token) in {"・", "･", "-", "_", "/"}:
            continue
        if primary == "記号" and re.fullmatch(r"[A-Za-z0-9α-ωΑ-Ω]", _token_surface(token)):
            continue
        return None
    if not noun_seen:
        return None
    return {
        "surface": surface,
        "start": start,
        "end": reference_end,
        "tokens": [_token_evidence(token) for token in evidence_tokens],
        "identity_status": "source_surface_only",
    }


def _comparison_evidence(
    tokens: list[dict[str, object]], span: tuple[int, int], comparator: str
) -> dict[str, object] | None:
    matches = [
        token
        for token in tokens
        if int(token["start"]) == span[0] and int(token["end"]) == span[1]
    ]
    if len(matches) != 1:
        return None
    token = matches[0]
    if _token_surface(token) != comparator:
        return None
    pos = _token_pos(token)
    if not pos or pos[0] not in {"形容詞", "名詞", "接尾辞"}:
        return None
    return _token_evidence(token)


def _selection_tail(value: str, target: str) -> bool:
    query = re.compile(
        rf"^\s*は\s*(?:誰|どれ|どこ|どの\s*{re.escape(target)})\s*"
        r"(?:(?:です|でしょう|なの)\s*)?か?\s*[?？。]?\s*$"
    )
    directive = re.compile(
        r"^\s*を\s*(?:選ぶ|選んで(?:ください|下さい)|選択(?:する|してください)|"
        r"返す|表示する|抽出する|特定する|取得する|採用する|指定する|"
        r"割り当てる)\s*[。]?\s*$"
    )
    return query.fullmatch(value) is not None or directive.fullmatch(value) is not None


def _declared_candidate_counts(
    source_text: str,
    *,
    required_span: tuple[int, int],
    target: str,
) -> tuple[set[tuple[int, str]], list[str]]:
    counts: set[tuple[int, str]] = set()
    fenced_ranges = _fenced_code_ranges(source_text)
    for match in _DECLARED_CANDIDATE_COUNT_RE.finditer(source_text):
        if _position_in_ranges(match.start(), fenced_ranges):
            continue
        if not (required_span[0] <= match.start() and match.end() <= required_span[1]):
            continue
        raw = match.group("count")
        if len(raw) > 8:
            return set(), ["declared_candidate_count_limit_exceeded"]
        value = _parse_candidate_count(raw)
        if value is None or value <= 0:
            return set(), ["declared_candidate_count_invalid"]
        if value > _MAX_OBSERVATIONS:
            return set(), ["declared_candidate_count_limit_exceeded"]
        kind = match.group("kind")
        if not _candidate_kind_compatible(kind, target):
            return set(), ["declared_candidate_kind_mismatch"]
        counts.add((value, kind))
    return counts, []


def _candidate_kind_compatible(kind: str, target: str) -> bool:
    if kind == target:
        return True
    families = (
        ({"人", "名"}, {"人", "者"}),
        ({"件"}, {"案件", "項目", "候補"}),
        ({"個"}, {"商品", "製品", "項目", "対象", "もの", "物"}),
    )
    return any(kind in counters and target in targets for counters, targets in families)


def _candidate_kinds_equivalent(
    header_kind: str, declared_kind: str, target: str
) -> bool:
    normalized_header = unicodedata.normalize("NFKC", header_kind)
    normalized_declared = unicodedata.normalize("NFKC", declared_kind)
    return (
        normalized_header == normalized_declared
        and _candidate_kind_compatible(normalized_declared, target)
    )


def _parse_candidate_count(value: str) -> int | None:
    ascii_value = value.translate(str.maketrans("０１２３４５６７８９", "0123456789"))
    if ascii_value.isascii() and ascii_value.isdigit():
        try:
            return int(ascii_value)
        except ValueError:
            return None
    digits = {
        "〇": 0,
        "零": 0,
        "一": 1,
        "二": 2,
        "三": 3,
        "四": 4,
        "五": 5,
        "六": 6,
        "七": 7,
        "八": 8,
        "九": 9,
    }
    units = {"十": 10, "百": 100}
    total = 0
    current: int | None = None
    for character in value:
        if character in digits:
            current = digits[character]
            continue
        unit = units.get(character)
        if unit is None:
            return None
        total += (1 if current is None else current) * unit
        current = None
    return total + (0 if current is None else current)


def _term_uniquely_identifies_scale(term: str, expected: ScaleSpec) -> bool:
    owners = [
        scale
        for scale in SCALE_SPECS
        if term in (*scale.high_terms, *scale.low_terms)
    ]
    return len(owners) == 1 and owners[0].scale_id == expected.scale_id


def _axis_terms_present(
    clause: str,
    scale: ScaleSpec,
    order_axis: OrderAxisSpec,
) -> bool:
    return any(
        term in clause
        for term in (*order_axis.measure_terms, *scale.high_terms, *scale.low_terms)
    )


def _previous_non_ignorable(
    tokens: list[dict[str, object]], index: int
) -> dict[str, object] | None:
    for candidate in reversed(tokens[:index]):
        if _ignorable(candidate):
            continue
        return candidate
    return None


def _question_clause_count(source_text: str) -> int:
    evidence_text = _mask_fenced_code(source_text)
    clauses = re.findall(r"[^。！？!?\n\r]+[。！？!?]?", evidence_text)
    count = 0
    for clause in clauses:
        word_count = len(_QUESTION_WORD_RE.findall(clause))
        marker_count = clause.count("?") + clause.count("？")
        separator_count = len(_QUESTION_SEPARATOR_RE.findall(clause))
        end_count = len(_QUESTION_END_RE.findall(clause))
        if word_count or marker_count or separator_count or end_count:
            count += max(1, word_count, marker_count, separator_count + 1, end_count)
    return count


def _context_start(semantic_ir: object, source_text: str) -> int:
    text = str(_value(semantic_ir, "text", ""))
    context = str(_value(semantic_ir, "context", ""))
    separator = "\n" if text and context else ""
    candidate = len(text) + len(separator)
    return candidate if f"{text}{separator}{context}" == source_text else len(source_text)


def _fenced_code_ranges(source_text: str) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    active_character = ""
    active_length = 0
    active_start = 0
    offset = 0
    for line in source_text.splitlines(keepends=True):
        line_end = offset + len(line)
        marker_match = re.match(
            r"^[ \t]{0,3}(?P<marker>`{3,}|~{3,})(?P<tail>.*)$",
            line.rstrip("\r\n"),
        )
        if marker_match is not None:
            marker = marker_match.group("marker")
            if not active_character:
                active_character = marker[0]
                active_length = len(marker)
                active_start = offset
            elif (
                marker[0] == active_character
                and len(marker) >= active_length
                and not marker_match.group("tail").strip()
            ):
                ranges.append((active_start, line_end))
                active_character = ""
                active_length = 0
        offset = line_end
    if active_character:
        ranges.append((active_start, len(source_text)))
    return ranges


def _position_in_ranges(position: int, ranges: Sequence[tuple[int, int]]) -> bool:
    return any(start <= position < end for start, end in ranges)


def _mask_fenced_code(source_text: str) -> str:
    ranges = _fenced_code_ranges(source_text)
    if not ranges:
        return source_text
    pieces: list[str] = []
    cursor = 0
    for start, end in ranges:
        pieces.append(source_text[cursor:start])
        pieces.append(re.sub(r"[^\r\n]", " ", source_text[start:end]))
        cursor = end
    pieces.append(source_text[cursor:])
    return "".join(pieces)


def _candidate_rows_are_contiguous(gap: str) -> bool:
    if re.search(r"\n\s*\n", gap):
        return False
    return not re.sub(r"[\s,，、;；*+・•-]", "", gap)


def _clause_span(source_text: str, start: int, minimum_end: int) -> tuple[int, int]:
    left = max(
        (source_text.rfind(mark, 0, start) for mark in _CLAUSE_BOUNDARIES),
        default=-1,
    ) + 1
    right_candidates = [
        position + 1
        for mark in _CLAUSE_BOUNDARIES
        if (position := source_text.find(mark, minimum_end)) >= 0
    ]
    right = min(right_candidates) if right_candidates else len(source_text)
    return left, right


def _space_token(token: Mapping[str, object]) -> bool:
    pos = _token_pos(token)
    return (pos and pos[0] == "空白") or _token_surface(token).isspace()


def _ignorable(token: Mapping[str, object]) -> bool:
    pos = _token_pos(token)
    if pos and pos[0] in {"空白", "補助記号"}:
        return True
    return _token_surface(token).isspace() or _token_surface(token) in {"、", "，", ","}


def _token_pos(token: Mapping[str, object]) -> list[str]:
    return [str(item) for item in _sequence(token.get("pos", ()))]


def _token_surface(token: Mapping[str, object]) -> str:
    return str(token.get("surface", ""))


def _token_lemma(token: Mapping[str, object]) -> str:
    return str(token.get("lemma", "") or token.get("normalized", "") or token.get("surface", ""))


def _token_evidence(token: Mapping[str, object]) -> dict[str, object]:
    return {
        "surface": _token_surface(token),
        "lemma": _token_lemma(token),
        "start": int(token["start"]),
        "end": int(token["end"]),
    }


def _span(start: int, end: int, excerpt: str) -> dict[str, object]:
    return {"start": start, "end": end, "excerpt": excerpt[:240]}


def _sequence(value: object) -> list[object]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return list(value)
    return []


def _value(item: object, key: str, default: Any = None) -> Any:
    if isinstance(item, Mapping):
        return item.get(key, default)
    return getattr(item, key, default)


__all__ = [
    "DECISION_FRAME_SCHEMA_VERSION",
    "PRECONDITION_ORDER_DIRECTION_RULE_ID",
    "PRECONDITION_OUTCOME_RULE_ID",
    "audit_precondition_sufficiency",
]
