from __future__ import annotations

from dataclasses import dataclass

from .provider_receipts import ProviderExecutionReceipt
from .providers import AnalysisAttempt, AnalysisSpan, RelationCandidate
from .records import ParsedRequirementRecord


@dataclass(frozen=True, slots=True)
class DependencyRelationProjection:
    """A versioned, non-assertive projection from syntax to a profile relation.

    The projection is deliberately candidate-only.  It records enough source
    identity to audit the transformation, but it has no support or hold-release
    authority and therefore cannot make an obligation pass.
    """

    projection_id: str
    rule_id: str
    provider_id: str
    provider_version: str
    resource_version: str
    receipt_id: str
    source_relation_kinds: tuple[str, ...]
    candidate: RelationCandidate


# Passive and clausal grammatical subjects are not actors.  v0 projects only
# a plain nominal subject; voice remains a reassessment-policy obligation.
_SUBJECT_DEPENDENCIES = frozenset({"nsubj"})
_OBJECT_DEPENDENCIES = frozenset({"obj", "dobj", "iobj"})


def _overlaps(left: AnalysisSpan, right: AnalysisSpan) -> bool:
    return left.start < right.end and right.start < left.end


def _within(span: AnalysisSpan, start: int, end: int) -> bool:
    return start <= span.start < span.end <= end


def _dependency_label(relation_kind: str) -> str | None:
    prefix = "dependency:"
    if not relation_kind.startswith(prefix):
        return None
    value = relation_kind[len(prefix) :].strip().lower()
    return value or None


def _connected(
    relation: RelationCandidate,
    left: AnalysisSpan,
    right: AnalysisSpan,
) -> bool:
    return (
        _overlaps(relation.from_span, left) and _overlaps(relation.to_span, right)
    ) or (
        _overlaps(relation.from_span, right) and _overlaps(relation.to_span, left)
    )


def _projection(
    attempt: AnalysisAttempt,
    receipt: ProviderExecutionReceipt,
    *,
    rule_id: str,
    relation_kind: str,
    from_span: AnalysisSpan,
    to_span: AnalysisSpan,
    source_relation_kinds: tuple[str, ...],
) -> DependencyRelationProjection:
    identity = (
        f"{attempt.provider_id}.{attempt.provider_version}.{attempt.resource_version}."
        f"{receipt.receipt_id}.{relation_kind}."
        f"{from_span.start}.{from_span.end}.{to_span.start}.{to_span.end}"
    )
    candidate = RelationCandidate(
        relation_kind=relation_kind,
        from_span=from_span,
        to_span=to_span,
        confidence=None,
        interpretation_id=f"interpretation.projection.{identity}",
        rationale=(
            f"candidate_only; rule={rule_id}; source_dependencies="
            + ",".join(source_relation_kinds)
        ),
    )
    return DependencyRelationProjection(
        projection_id=f"projection.{identity}",
        rule_id=rule_id,
        provider_id=attempt.provider_id,
        provider_version=attempt.provider_version,
        resource_version=attempt.resource_version,
        receipt_id=receipt.receipt_id,
        source_relation_kinds=source_relation_kinds,
        candidate=candidate,
    )


def project_dependency_relations(
    record: ParsedRequirementRecord,
    attempts: tuple[AnalysisAttempt, ...],
    receipts: tuple[ProviderExecutionReceipt, ...] = (),
) -> tuple[DependencyRelationProjection, ...]:
    """Project a narrow subset of source-aligned UD edges into candidates.

    v0 covers only actor→predicate, predicate→object, and an explicitly
    emitted condition scope attached by a dependency edge.  Cross-field
    relations such as ``verifies`` and ``produces_evidence`` remain outside
    this rule; pretending they follow from sentence syntax would be an
    evidentiary escalation.
    """

    scenario = record.one("scenario")
    if scenario is None:
        return ()
    start, end = scenario.value_start, scenario.value_end
    projections: list[DependencyRelationProjection] = []
    for attempt in attempts:
        if (
            attempt.stage != "dependency_parse"
            or attempt.status not in {"ok", "partial"}
            or "dependency" not in attempt.fulfilled_capabilities
        ):
            continue
        matching_receipts = tuple(
            receipt
            for receipt in receipts
            if receipt.stage == attempt.stage
            and receipt.provider_id == attempt.provider_id
            and receipt.provider_version == attempt.provider_version
            and receipt.resource_version == attempt.resource_version
            and receipt.status == attempt.status
        )
        if len(matching_receipts) != 1:
            # A projection without an unambiguous engine receipt is not usable
            # as reassessment material.
            continue
        receipt = matching_receipts[0]
        dependency_relations = tuple(
            relation
            for relation in attempt.relations
            if _dependency_label(relation.relation_kind) is not None
            and _within(relation.from_span, start, end)
            and _within(relation.to_span, start, end)
        )
        for relation in dependency_relations:
            label = _dependency_label(relation.relation_kind)
            if label in _SUBJECT_DEPENDENCIES:
                projections.append(
                    _projection(
                        attempt,
                        receipt,
                        rule_id="projection.ud-subject-performs/v0",
                        relation_kind="performs",
                        from_span=relation.from_span,
                        to_span=relation.to_span,
                        source_relation_kinds=(relation.relation_kind,),
                    )
                )
            elif label in _OBJECT_DEPENDENCIES:
                projections.append(
                    _projection(
                        attempt,
                        receipt,
                        rule_id="projection.ud-object-acts-on/v0",
                        relation_kind="acts_on",
                        from_span=relation.to_span,
                        to_span=relation.from_span,
                        source_relation_kinds=(relation.relation_kind,),
                    )
                )

        if "scope" not in attempt.fulfilled_capabilities:
            continue
        for scope in attempt.scopes:
            if (
                scope.scope_kind not in {"condition", "conditional", "conditional_scope"}
                or scope.target_span is None
                or not _within(scope.cue_span, start, end)
                or not _within(scope.target_span, start, end)
            ):
                continue
            source_edges = tuple(
                relation.relation_kind
                for relation in dependency_relations
                if _connected(relation, scope.cue_span, scope.target_span)
            )
            if not source_edges:
                continue
            projections.append(
                _projection(
                    attempt,
                    receipt,
                    rule_id="projection.condition-trigger/v0",
                    relation_kind="triggered_by",
                    from_span=scope.target_span,
                    to_span=scope.cue_span,
                    source_relation_kinds=tuple(sorted(set(source_edges))),
                )
            )

    unique: dict[
        tuple[str, int, int, int, int, str, str, str, str],
        DependencyRelationProjection,
    ] = {}
    for item in projections:
        candidate = item.candidate
        unique[
            (
                candidate.relation_kind,
                candidate.from_span.start,
                candidate.from_span.end,
                candidate.to_span.start,
                candidate.to_span.end,
                item.provider_id,
                item.provider_version,
                item.resource_version,
                item.receipt_id,
            )
        ] = item
    return tuple(
        sorted(
            unique.values(),
            key=lambda item: (
                item.candidate.from_span.start,
                item.candidate.to_span.start,
                item.candidate.relation_kind,
                item.provider_id,
            ),
        )
    )


__all__ = ["DependencyRelationProjection", "project_dependency_relations"]
