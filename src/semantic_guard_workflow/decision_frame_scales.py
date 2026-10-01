from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Literal

WitnessPolicy = Literal["numeric", "structural_only"]
NumericOrder = Literal["descending", "ascending"]
ScalePole = Literal["high", "low"]


@dataclass(frozen=True)
class OrderAxisSpec:
    """One explicitly agreed identity boundary for ordering measures."""

    axis_id: str
    measure_terms: tuple[str, ...]


@dataclass(frozen=True)
class DirectionalScaleSpec:
    """One coarse vocabulary family whose measures keep explicit axis identity."""

    scale_id: str
    axes: tuple[OrderAxisSpec, ...]
    high_terms: tuple[str, ...]
    low_terms: tuple[str, ...]
    canonical_high_term: str
    canonical_low_term: str

    @property
    def measure_terms(self) -> tuple[str, ...]:
        """Expose the legacy flattened vocabulary without collapsing its axes."""

        return tuple(term for axis in self.axes for term in axis.measure_terms)


# Compatibility name for consumers that only need the directional scale type.
ScaleSpec = DirectionalScaleSpec


@dataclass(frozen=True)
class NumericProjectionSpec:
    """Optional numeric witness projection for one directional scale.

    Unit aliases only normalize spellings of the same unit. Canonical units
    remain distinct, so this registry never implies conversion between, for
    example, kilograms and grams or centimetres and metres.
    """

    scale_id: str
    unit_aliases: tuple[tuple[str, str], ...]
    witness_policy: WitnessPolicy
    high_pole_numeric_order: NumericOrder


_MASS_UNITS = (
    ("mg", "mg"),
    ("ｍｇ", "mg"),
    ("ミリグラム", "mg"),
    ("g", "g"),
    ("ｇ", "g"),
    ("グラム", "g"),
    ("kg", "kg"),
    ("ｋｇ", "kg"),
    ("㎏", "kg"),
    ("キログラム", "kg"),
    ("t", "t"),
    ("ｔ", "t"),
    ("トン", "t"),
)

_LENGTH_UNITS = (
    ("mm", "mm"),
    ("ｍｍ", "mm"),
    ("ミリメートル", "mm"),
    ("cm", "cm"),
    ("ｃｍ", "cm"),
    ("センチメートル", "cm"),
    ("m", "m"),
    ("ｍ", "m"),
    ("メートル", "m"),
    ("km", "km"),
    ("ｋｍ", "km"),
    ("キロメートル", "km"),
)

_DURATION_UNITS = (
    ("ms", "ms"),
    ("ｍｓ", "ms"),
    ("ミリ秒", "ms"),
    ("s", "s"),
    ("sec", "s"),
    ("秒", "s"),
    ("min", "min"),
    ("分", "min"),
    ("h", "h"),
    ("hr", "h"),
    ("時間", "h"),
    ("日", "day"),
    ("日間", "day"),
)

_SPEED_UNITS = (
    ("m/s", "m/s"),
    ("m／s", "m/s"),
    ("m毎秒", "m/s"),
    ("メートル毎秒", "m/s"),
    ("km/h", "km/h"),
    ("km／h", "km/h"),
    ("km毎時", "km/h"),
    ("キロメートル毎時", "km/h"),
    ("mph", "mph"),
)

_PRICE_UNITS = (
    ("円", "JPY"),
    ("JPY", "JPY"),
    ("￥", "JPY"),
    ("¥", "JPY"),
    ("ドル", "USD"),
    ("米ドル", "USD"),
    ("USD", "USD"),
    ("$", "USD"),
    ("＄", "USD"),
    ("ユーロ", "EUR"),
    ("EUR", "EUR"),
    ("€", "EUR"),
)

_COUNT_UNITS = tuple(
    (unit, unit)
    for unit in ("人", "名", "件", "個", "票", "回", "台", "本", "枚")
)

_SCORE_UNITS = (
    ("点", "point"),
    ("pt", "point"),
    ("pts", "point"),
    ("ポイント", "point"),
    ("%", "percent"),
    ("％", "percent"),
    ("パーセント", "percent"),
)

_AGE_UNITS = (
    ("歳", "歳"),
    ("才", "歳"),
)

_TEMPERATURE_UNITS = (
    ("℃", "degree_celsius"),
    ("°C", "degree_celsius"),
    ("度", "degree_celsius"),
    ("K", "kelvin"),
    ("ケルビン", "kelvin"),
    ("℉", "degree_fahrenheit"),
    ("°F", "degree_fahrenheit"),
)

_SIZE_UNITS = (
    ("mL", "mL"),
    ("ml", "mL"),
    ("ｍＬ", "mL"),
    ("ミリリットル", "mL"),
    ("L", "L"),
    ("l", "L"),
    ("Ｌ", "L"),
    ("リットル", "L"),
    ("cm3", "cm3"),
    ("cm³", "cm3"),
    ("㎤", "cm3"),
    ("立方センチメートル", "cm3"),
    ("m3", "m3"),
    ("m³", "m3"),
    ("㎥", "m3"),
    ("立方メートル", "m3"),
    ("KB", "KB"),
    ("MB", "MB"),
    ("GB", "GB"),
    ("TB", "TB"),
)

_AREA_UNITS = (
    ("mm2", "mm2"),
    ("mm²", "mm2"),
    ("平方ミリメートル", "mm2"),
    ("cm2", "cm2"),
    ("cm²", "cm2"),
    ("平方センチメートル", "cm2"),
    ("m2", "m2"),
    ("m²", "m2"),
    ("㎡", "m2"),
    ("平方メートル", "m2"),
    ("km2", "km2"),
    ("km²", "km2"),
    ("平方キロメートル", "km2"),
    ("ha", "ha"),
    ("ヘクタール", "ha"),
)

_STRENGTH_UNITS = (
    ("Pa", "Pa"),
    ("kPa", "kPa"),
    ("MPa", "MPa"),
    ("N", "N"),
    ("kN", "kN"),
    ("ニュートン", "N"),
)


SCALE_SPECS: tuple[DirectionalScaleSpec, ...] = (
    DirectionalScaleSpec(
        scale_id="body_mass",
        axes=(
            OrderAxisSpec(axis_id="body_weight", measure_terms=("体重",)),
            OrderAxisSpec(axis_id="weight", measure_terms=("重量", "重さ")),
            OrderAxisSpec(axis_id="mass", measure_terms=("質量",)),
        ),
        high_terms=("重い",),
        low_terms=("軽い",),
        canonical_high_term="重い",
        canonical_low_term="軽い",
    ),
    DirectionalScaleSpec(
        scale_id="height",
        axes=(
            OrderAxisSpec(axis_id="stature", measure_terms=("身長",)),
            OrderAxisSpec(axis_id="generic_height", measure_terms=("高さ",)),
            OrderAxisSpec(axis_id="elevation", measure_terms=("標高",)),
        ),
        high_terms=("高い",),
        low_terms=("低い",),
        canonical_high_term="高い",
        canonical_low_term="低い",
    ),
    DirectionalScaleSpec(
        scale_id="score",
        axes=(
            OrderAxisSpec(
                axis_id="score",
                measure_terms=("点数", "得点", "スコア"),
            ),
            OrderAxisSpec(axis_id="academic_performance", measure_terms=("成績",)),
        ),
        high_terms=("高い",),
        low_terms=("低い",),
        canonical_high_term="高い",
        canonical_low_term="低い",
    ),
    DirectionalScaleSpec(
        scale_id="price",
        axes=(
            OrderAxisSpec(axis_id="price", measure_terms=("価格", "値段")),
            OrderAxisSpec(axis_id="fee", measure_terms=("料金",)),
            OrderAxisSpec(axis_id="cost", measure_terms=("費用", "コスト")),
        ),
        high_terms=("高い",),
        low_terms=("安い", "低い"),
        canonical_high_term="高い",
        canonical_low_term="安い",
    ),
    DirectionalScaleSpec(
        scale_id="count",
        axes=(
            OrderAxisSpec(axis_id="population", measure_terms=("人口",)),
            OrderAxisSpec(axis_id="people_count", measure_terms=("人数",)),
            OrderAxisSpec(axis_id="case_count", measure_terms=("件数",)),
            OrderAxisSpec(axis_id="item_count", measure_terms=("個数",)),
            OrderAxisSpec(axis_id="quantity", measure_terms=("数量",)),
            OrderAxisSpec(axis_id="vote_count", measure_terms=("票数",)),
            OrderAxisSpec(axis_id="occurrence_count", measure_terms=("回数",)),
            OrderAxisSpec(axis_id="inventory_count", measure_terms=("在庫数",)),
        ),
        high_terms=("多い",),
        low_terms=("少ない",),
        canonical_high_term="多い",
        canonical_low_term="少ない",
    ),
    DirectionalScaleSpec(
        scale_id="distance",
        axes=(OrderAxisSpec(axis_id="distance", measure_terms=("距離",)),),
        high_terms=("遠い", "長い"),
        low_terms=("近い", "短い"),
        canonical_high_term="遠い",
        canonical_low_term="近い",
    ),
    DirectionalScaleSpec(
        scale_id="duration",
        axes=(
            OrderAxisSpec(axis_id="elapsed_time", measure_terms=("所要時間",)),
            OrderAxisSpec(axis_id="processing_time", measure_terms=("処理時間",)),
            OrderAxisSpec(axis_id="response_time", measure_terms=("応答時間",)),
            OrderAxisSpec(axis_id="wait_time", measure_terms=("待ち時間",)),
            OrderAxisSpec(axis_id="period", measure_terms=("期間",)),
            OrderAxisSpec(axis_id="generic_time", measure_terms=("時間",)),
        ),
        high_terms=("長い",),
        low_terms=("短い",),
        canonical_high_term="長い",
        canonical_low_term="短い",
    ),
    DirectionalScaleSpec(
        scale_id="speed",
        axes=(OrderAxisSpec(axis_id="speed", measure_terms=("速度", "速さ")),),
        high_terms=("速い",),
        low_terms=("遅い",),
        canonical_high_term="速い",
        canonical_low_term="遅い",
    ),
    DirectionalScaleSpec(
        scale_id="age",
        axes=(OrderAxisSpec(axis_id="age", measure_terms=("年齢",)),),
        high_terms=("高い", "年上", "年長"),
        low_terms=("低い", "若い", "年下"),
        canonical_high_term="高い",
        canonical_low_term="低い",
    ),
    DirectionalScaleSpec(
        scale_id="temperature",
        axes=(
            OrderAxisSpec(axis_id="temperature", measure_terms=("温度",)),
            OrderAxisSpec(axis_id="air_temperature", measure_terms=("気温",)),
            OrderAxisSpec(axis_id="water_temperature", measure_terms=("水温",)),
            OrderAxisSpec(axis_id="body_temperature", measure_terms=("体温",)),
        ),
        high_terms=("高い",),
        low_terms=("低い",),
        canonical_high_term="高い",
        canonical_low_term="低い",
    ),
    DirectionalScaleSpec(
        scale_id="size",
        axes=(
            OrderAxisSpec(axis_id="generic_size", measure_terms=("大きさ",)),
            OrderAxisSpec(axis_id="capacity", measure_terms=("容量",)),
            OrderAxisSpec(axis_id="volume", measure_terms=("体積",)),
        ),
        high_terms=("大きい",),
        low_terms=("小さい",),
        canonical_high_term="大きい",
        canonical_low_term="小さい",
    ),
    DirectionalScaleSpec(
        scale_id="area",
        axes=(
            OrderAxisSpec(axis_id="area", measure_terms=("面積",)),
            OrderAxisSpec(axis_id="spaciousness", measure_terms=("広さ",)),
        ),
        high_terms=("広い", "大きい"),
        low_terms=("狭い", "小さい"),
        canonical_high_term="広い",
        canonical_low_term="狭い",
    ),
    DirectionalScaleSpec(
        scale_id="rating",
        axes=(
            OrderAxisSpec(axis_id="evaluation", measure_terms=("評価",)),
            OrderAxisSpec(axis_id="evaluation_value", measure_terms=("評価値",)),
            OrderAxisSpec(axis_id="evaluation_score", measure_terms=("評価点",)),
            OrderAxisSpec(axis_id="rating", measure_terms=("レーティング",)),
            OrderAxisSpec(axis_id="satisfaction", measure_terms=("満足度",)),
            OrderAxisSpec(axis_id="priority", measure_terms=("優先度",)),
            OrderAxisSpec(axis_id="importance", measure_terms=("重要度",)),
            OrderAxisSpec(axis_id="difficulty", measure_terms=("難易度",)),
            OrderAxisSpec(axis_id="risk", measure_terms=("危険度",)),
            OrderAxisSpec(axis_id="urgency", measure_terms=("緊急度",)),
            OrderAxisSpec(axis_id="confidence", measure_terms=("信頼度",)),
        ),
        high_terms=("高い",),
        low_terms=("低い",),
        canonical_high_term="高い",
        canonical_low_term="低い",
    ),
    DirectionalScaleSpec(
        scale_id="strength",
        axes=(OrderAxisSpec(axis_id="strength", measure_terms=("強度", "強さ")),),
        high_terms=("高い", "強い"),
        low_terms=("低い", "弱い"),
        canonical_high_term="高い",
        canonical_low_term="低い",
    ),
)


NUMERIC_PROJECTION_SPECS: tuple[NumericProjectionSpec, ...] = (
    NumericProjectionSpec("body_mass", _MASS_UNITS, "numeric", "descending"),
    NumericProjectionSpec("height", _LENGTH_UNITS, "numeric", "descending"),
    NumericProjectionSpec("score", _SCORE_UNITS, "numeric", "descending"),
    NumericProjectionSpec("price", _PRICE_UNITS, "numeric", "descending"),
    NumericProjectionSpec("count", _COUNT_UNITS, "numeric", "descending"),
    NumericProjectionSpec("distance", _LENGTH_UNITS, "numeric", "descending"),
    NumericProjectionSpec("duration", _DURATION_UNITS, "numeric", "descending"),
    NumericProjectionSpec("speed", _SPEED_UNITS, "numeric", "descending"),
    NumericProjectionSpec("age", _AGE_UNITS, "numeric", "descending"),
    NumericProjectionSpec(
        "temperature", _TEMPERATURE_UNITS, "numeric", "descending"
    ),
    NumericProjectionSpec("size", _SIZE_UNITS, "numeric", "descending"),
    NumericProjectionSpec("area", _AREA_UNITS, "numeric", "descending"),
    NumericProjectionSpec("strength", _STRENGTH_UNITS, "numeric", "descending"),
)


def _normalize_term(value: str) -> str:
    return "".join(unicodedata.normalize("NFKC", value).split())


def _normalized_terms(values: tuple[str, ...]) -> frozenset[str]:
    return frozenset(_normalize_term(value) for value in values)


_STABLE_ID_RE = re.compile(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*")
_SCALES_WITHOUT_NUMERIC_PROJECTION = frozenset({"rating"})


def _unit_alias_map(projection: NumericProjectionSpec) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for alias, canonical in projection.unit_aliases:
        normalized = _normalize_term(alias)
        previous = mapping.setdefault(normalized, canonical)
        if previous != canonical:
            raise ValueError(
                "normalized unit aliases conflict: "
                f"{projection.scale_id}:{alias}"
            )
    return mapping


def _validate_registry() -> None:
    scale_ids: set[str] = set()
    axis_ids: set[str] = set()
    owner_by_measure: dict[str, tuple[str, str]] = {}
    for scale in SCALE_SPECS:
        if not _STABLE_ID_RE.fullmatch(scale.scale_id):
            raise ValueError(
                f"decision-frame scale id is not stable ASCII: {scale.scale_id}"
            )
        if scale.scale_id in scale_ids:
            raise ValueError(f"decision-frame scale id is not unique: {scale.scale_id}")
        scale_ids.add(scale.scale_id)
        if not scale.axes or not scale.high_terms or not scale.low_terms:
            raise ValueError(
                f"decision-frame scale vocabulary is incomplete: {scale.scale_id}"
            )
        high_terms = _normalized_terms(scale.high_terms)
        low_terms = _normalized_terms(scale.low_terms)
        if len(high_terms) != len(scale.high_terms):
            raise ValueError(
                f"decision-frame high terms are not unique: {scale.scale_id}"
            )
        if len(low_terms) != len(scale.low_terms):
            raise ValueError(
                f"decision-frame low terms are not unique: {scale.scale_id}"
            )
        if high_terms & low_terms:
            raise ValueError(f"decision-frame scale poles overlap: {scale.scale_id}")
        if _normalize_term(scale.canonical_high_term) not in high_terms:
            raise ValueError(f"canonical high term is not registered: {scale.scale_id}")
        if _normalize_term(scale.canonical_low_term) not in low_terms:
            raise ValueError(f"canonical low term is not registered: {scale.scale_id}")
        for axis in scale.axes:
            if not _STABLE_ID_RE.fullmatch(axis.axis_id):
                raise ValueError(
                    f"decision-frame axis id is not stable ASCII: {axis.axis_id}"
                )
            if axis.axis_id in axis_ids:
                raise ValueError(
                    f"decision-frame axis id is not unique: {axis.axis_id}"
                )
            axis_ids.add(axis.axis_id)
            if not axis.measure_terms:
                raise ValueError(f"decision-frame axis has no measures: {axis.axis_id}")
            measures = tuple(_normalize_term(term) for term in axis.measure_terms)
            if any(not measure for measure in measures):
                raise ValueError(
                    f"decision-frame axis has an empty measure: {axis.axis_id}"
                )
            if len(set(measures)) != len(measures):
                raise ValueError(
                    f"decision-frame axis measures are not unique: {axis.axis_id}"
                )
            for measure in measures:
                owner = (scale.scale_id, axis.axis_id)
                previous_owner = owner_by_measure.setdefault(measure, owner)
                if previous_owner == owner:
                    continue
                raise ValueError(
                    "decision-frame measure belongs to multiple axes: "
                    f"{measure}:{previous_owner[1]}:{axis.axis_id}"
                )

    projection_scale_ids: set[str] = set()
    for projection in NUMERIC_PROJECTION_SPECS:
        if projection.scale_id in projection_scale_ids:
            raise ValueError(
                "numeric projection scale reference is not unique: "
                f"{projection.scale_id}"
            )
        projection_scale_ids.add(projection.scale_id)
        if projection.scale_id not in scale_ids:
            raise ValueError(
                f"numeric projection references an unknown scale: {projection.scale_id}"
            )
        if projection.witness_policy != "numeric":
            raise ValueError(
                f"numeric projection has a non-numeric policy: {projection.scale_id}"
            )
        if projection.high_pole_numeric_order not in {"ascending", "descending"}:
            raise ValueError(
                "numeric projection has an invalid pole order: "
                f"{projection.scale_id}"
            )
        if not projection.unit_aliases:
            raise ValueError(
                f"numeric projection has no registered units: {projection.scale_id}"
            )
        _unit_alias_map(projection)

    if projection_scale_ids & _SCALES_WITHOUT_NUMERIC_PROJECTION:
        raise ValueError("a projection-free scale has a numeric projection")
    covered_scale_ids = projection_scale_ids | _SCALES_WITHOUT_NUMERIC_PROJECTION
    if covered_scale_ids != scale_ids:
        missing = sorted(scale_ids - covered_scale_ids)
        unknown = sorted(covered_scale_ids - scale_ids)
        raise ValueError(
            "numeric projection decisions do not close over scales: "
            f"{missing}:{unknown}"
        )


_validate_registry()


_SCALES_BY_ID = {scale.scale_id: scale for scale in SCALE_SPECS}
_HIGH_TERMS = {
    scale.scale_id: _normalized_terms(scale.high_terms) for scale in SCALE_SPECS
}
_LOW_TERMS = {
    scale.scale_id: _normalized_terms(scale.low_terms) for scale in SCALE_SPECS
}
_AXIS_OWNER_BY_MEASURE = {
    _normalize_term(measure): (scale, axis)
    for scale in SCALE_SPECS
    for axis in scale.axes
    for measure in axis.measure_terms
}
_NUMERIC_PROJECTIONS_BY_SCALE_ID = {
    projection.scale_id: projection for projection in NUMERIC_PROJECTION_SPECS
}
_UNIT_ALIASES = {
    projection.scale_id: _unit_alias_map(projection)
    for projection in NUMERIC_PROJECTION_SPECS
}


def scale_by_id(scale_id: str) -> ScaleSpec | None:
    """Return the exact registered scale id, or ``None`` when it is unknown."""

    return _SCALES_BY_ID.get(scale_id.strip()) if isinstance(scale_id, str) else None


def axis_for_measure(measure: str) -> OrderAxisSpec | None:
    """Resolve one exact registered measure to its agreed ordering axis."""

    if not isinstance(measure, str):
        return None
    owner = _AXIS_OWNER_BY_MEASURE.get(_normalize_term(measure))
    return owner[1] if owner is not None else None


def match_directional_axis(
    measure: str,
    comparator: str,
) -> tuple[DirectionalScaleSpec, OrderAxisSpec, ScalePole] | None:
    """Resolve an exact measure/comparator pair without collapsing axis identity."""

    if not isinstance(measure, str) or not isinstance(comparator, str):
        return None
    owner = _AXIS_OWNER_BY_MEASURE.get(_normalize_term(measure))
    if owner is None:
        return None
    scale, axis = owner
    normalized_comparator = _normalize_term(comparator)
    if normalized_comparator in _HIGH_TERMS[scale.scale_id]:
        return scale, axis, "high"
    if normalized_comparator in _LOW_TERMS[scale.scale_id]:
        return scale, axis, "low"
    return None


def match_scale(measure: str, comparator: str) -> tuple[ScaleSpec, ScalePole] | None:
    """Compatibility view of :func:`match_directional_axis` without the axis."""

    matched = match_directional_axis(measure, comparator)
    if matched is None:
        return None
    scale, _axis, pole = matched
    return scale, pole


def all_measure_terms() -> tuple[str, ...]:
    """Return unique source vocabulary, longest first for stable matching."""

    return tuple(
        sorted(
            {term for scale in SCALE_SPECS for term in scale.measure_terms},
            key=lambda term: (-len(term), term),
        )
    )


def all_comparison_terms() -> tuple[str, ...]:
    """Return unique comparison vocabulary, longest first for stable matching."""

    return tuple(
        sorted(
            {
                term
                for scale in SCALE_SPECS
                for term in (*scale.high_terms, *scale.low_terms)
            },
            key=lambda term: (-len(term), term),
        )
    )


def _coerce_scale(scale: DirectionalScaleSpec | str) -> DirectionalScaleSpec | None:
    if isinstance(scale, ScaleSpec):
        return _SCALES_BY_ID.get(scale.scale_id)
    return scale_by_id(scale)


def numeric_projection_for_scale(
    scale: DirectionalScaleSpec | NumericProjectionSpec | str,
) -> NumericProjectionSpec | None:
    """Return the optional numeric witness projection for a registered scale."""

    if isinstance(scale, NumericProjectionSpec):
        return _NUMERIC_PROJECTIONS_BY_SCALE_ID.get(scale.scale_id)
    resolved = _coerce_scale(scale)
    if resolved is None:
        return None
    return _NUMERIC_PROJECTIONS_BY_SCALE_ID.get(resolved.scale_id)


def numeric_unit_pattern(
    scale: DirectionalScaleSpec | NumericProjectionSpec | str,
) -> str:
    """Return a regex alternation for raw unit spellings without conversion."""

    projection = numeric_projection_for_scale(scale)
    if projection is None or not projection.unit_aliases:
        return r"(?!)"
    aliases = sorted(
        {alias for alias, _canonical in projection.unit_aliases},
        key=lambda alias: (-len(alias), alias),
    )
    return "(?:" + "|".join(re.escape(alias) for alias in aliases) + ")"


def normalize_unit(
    scale: DirectionalScaleSpec | NumericProjectionSpec | str,
    raw: str,
) -> str | None:
    """Normalize one unit spelling while preserving distinct canonical units."""

    projection = numeric_projection_for_scale(scale)
    if projection is None or not isinstance(raw, str):
        return None
    return _UNIT_ALIASES[projection.scale_id].get(_normalize_term(raw))


__all__ = [
    "NUMERIC_PROJECTION_SPECS",
    "SCALE_SPECS",
    "DirectionalScaleSpec",
    "NumericProjectionSpec",
    "OrderAxisSpec",
    "ScaleSpec",
    "all_comparison_terms",
    "all_measure_terms",
    "axis_for_measure",
    "match_directional_axis",
    "match_scale",
    "normalize_unit",
    "numeric_projection_for_scale",
    "numeric_unit_pattern",
    "scale_by_id",
]
