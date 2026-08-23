from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class DirectionBindingResolution:
    """Domain-neutral result of classifying explicit direction evidence."""

    status: str
    selected_direction: str = ""
    reason: str = ""


def resolve_direction_binding(
    accepted_evidence: Sequence[Mapping[str, object]],
    *,
    unresolved_evidence: Sequence[Mapping[str, object]] = (),
    value_field: str = "value",
    conflict_reason: str = "multiple_directions",
) -> DirectionBindingResolution:
    """Resolve 0/1/many explicit direction values without domain inference.

    Rejected evidence is deliberately absent from this interface: an adapter
    must decide whether evidence is binding before the common kernel sees it.
    Any conclusion-changing unresolved evidence takes precedence over a gap or
    a seemingly unique binding.
    """

    if unresolved_evidence:
        return DirectionBindingResolution(
            status="indeterminate",
            reason="direction_evidence_unresolved",
        )

    directions = {
        str(item.get(value_field, ""))
        for item in accepted_evidence
        if str(item.get(value_field, ""))
    }
    if len(directions) > 1:
        return DirectionBindingResolution(
            status="conflict",
            reason=conflict_reason,
        )
    if len(directions) == 1:
        return DirectionBindingResolution(
            status="bound",
            selected_direction=next(iter(directions)),
        )
    return DirectionBindingResolution(status="missing")


__all__ = ["DirectionBindingResolution", "resolve_direction_binding"]
