from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DirectionOptionSpec:
    option_id: str
    surface_patterns: tuple[str, ...]
    canonical_surface: str


@dataclass(frozen=True)
class DirectionSpaceSpec:
    direction_domain_id: str
    direction_axis_id: str
    basis_terms: tuple[str, ...]
    options: tuple[DirectionOptionSpec, DirectionOptionSpec]


DIRECTION_SPACE_SPECS: tuple[DirectionSpaceSpec, ...] = (
    DirectionSpaceSpec(
        direction_domain_id="spatial_line",
        direction_axis_id="horizontal_left_right",
        basis_terms=("横一列", "横並び", "水平方向の列"),
        options=(
            DirectionOptionSpec(
                option_id="left_to_right",
                surface_patterns=(r"左\s*から\s*右\s*(?:へ|に)",),
                canonical_surface="左から右へ",
            ),
            DirectionOptionSpec(
                option_id="right_to_left",
                surface_patterns=(r"右\s*から\s*左\s*(?:へ|に)",),
                canonical_surface="右から左へ",
            ),
        ),
    ),
    DirectionSpaceSpec(
        direction_domain_id="spatial_line",
        direction_axis_id="vertical_top_bottom",
        basis_terms=("縦一列", "縦並び", "垂直方向の列"),
        options=(
            DirectionOptionSpec(
                option_id="top_to_bottom",
                surface_patterns=(r"上\s*から\s*下\s*(?:へ|に)",),
                canonical_surface="上から下へ",
            ),
            DirectionOptionSpec(
                option_id="bottom_to_top",
                surface_patterns=(r"下\s*から\s*上\s*(?:へ|に)",),
                canonical_surface="下から上へ",
            ),
        ),
    ),
    DirectionSpaceSpec(
        direction_domain_id="spatial_depth",
        direction_axis_id="front_back",
        basis_terms=("奥行き方向", "前後一列", "前後方向の列"),
        options=(
            DirectionOptionSpec(
                option_id="front_to_back",
                surface_patterns=(
                    r"手前\s*から\s*奥\s*(?:へ|に)",
                    r"前\s*から\s*後(?:ろ)?\s*(?:へ|に)",
                ),
                canonical_surface="手前から奥へ",
            ),
            DirectionOptionSpec(
                option_id="back_to_front",
                surface_patterns=(
                    r"奥\s*から\s*手前\s*(?:へ|に)",
                    r"後(?:ろ)?\s*から\s*前\s*(?:へ|に)",
                ),
                canonical_surface="奥から手前へ",
            ),
        ),
    ),
    DirectionSpaceSpec(
        direction_domain_id="temporal_sequence",
        direction_axis_id="past_future",
        basis_terms=("時系列", "時間順序", "年代列"),
        options=(
            DirectionOptionSpec(
                option_id="past_to_future",
                surface_patterns=(
                    r"過去\s*から\s*未来\s*(?:へ|に)",
                    r"古い\s*時点\s*から\s*新しい\s*時点\s*(?:へ|に)",
                ),
                canonical_surface="過去から未来へ",
            ),
            DirectionOptionSpec(
                option_id="future_to_past",
                surface_patterns=(
                    r"未来\s*から\s*過去\s*(?:へ|に)",
                    r"新しい\s*時点\s*から\s*古い\s*時点\s*(?:へ|に)",
                ),
                canonical_surface="未来から過去へ",
            ),
        ),
    ),
    DirectionSpaceSpec(
        direction_domain_id="circular_sequence",
        direction_axis_id="clockwise_counterclockwise",
        basis_terms=("円周上", "環状配置", "円環"),
        options=(
            DirectionOptionSpec(
                option_id="clockwise",
                surface_patterns=(r"(?<!反)時計\s*回り\s*に?",),
                canonical_surface="時計回りに",
            ),
            DirectionOptionSpec(
                option_id="counterclockwise",
                surface_patterns=(r"反\s*時計\s*回り\s*に?",),
                canonical_surface="反時計回りに",
            ),
        ),
    ),
    DirectionSpaceSpec(
        direction_domain_id="path_traversal",
        direction_axis_id="origin_destination",
        basis_terms=("経路上", "走査経路", "経路"),
        options=(
            DirectionOptionSpec(
                option_id="origin_to_destination",
                surface_patterns=(
                    r"起点\s*から\s*終点\s*(?:へ|に)",
                    r"始点\s*から\s*終点\s*(?:へ|に)",
                ),
                canonical_surface="起点から終点へ",
            ),
            DirectionOptionSpec(
                option_id="destination_to_origin",
                surface_patterns=(
                    r"終点\s*から\s*起点\s*(?:へ|に)",
                    r"終点\s*から\s*始点\s*(?:へ|に)",
                ),
                canonical_surface="終点から起点へ",
            ),
        ),
    ),
)


def direction_option_ids() -> tuple[str, ...]:
    return tuple(
        option.option_id for spec in DIRECTION_SPACE_SPECS for option in spec.options
    )


def direction_axis_ids() -> tuple[str, ...]:
    return tuple(spec.direction_axis_id for spec in DIRECTION_SPACE_SPECS)


def _validate_registry() -> None:
    axes: set[str] = set()
    bases: set[str] = set()
    options: set[str] = set()
    for spec in DIRECTION_SPACE_SPECS:
        if spec.direction_axis_id in axes:
            raise ValueError(f"duplicate direction axis: {spec.direction_axis_id}")
        axes.add(spec.direction_axis_id)
        if len(spec.options) != 2:
            raise ValueError(
                f"direction axis must have exactly two options: {spec.direction_axis_id}"
            )
        for basis in spec.basis_terms:
            if basis in bases:
                raise ValueError(f"duplicate direction basis term: {basis}")
            bases.add(basis)
        for option in spec.options:
            if option.option_id in options:
                raise ValueError(f"duplicate direction option: {option.option_id}")
            options.add(option.option_id)
            if not option.surface_patterns or not option.canonical_surface:
                raise ValueError(f"incomplete direction option: {option.option_id}")


_validate_registry()


__all__ = [
    "DIRECTION_SPACE_SPECS",
    "DirectionOptionSpec",
    "DirectionSpaceSpec",
    "direction_axis_ids",
    "direction_option_ids",
]
