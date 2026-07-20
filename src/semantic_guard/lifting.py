from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Literal

from .providers import AnalysisAttempt, AnalysisSpan, RelationCandidate, ScopeCandidate
from .records import ParsedRequirementRecord
from .residual_risk import ResidualRiskSignal


LiftingStatus = Literal["resolved", "unresolved", "not_applicable"]


@dataclass(frozen=True, slots=True)
class LiftingResolution:
    signal_id: str
    status: LiftingStatus
    rule_id: str
    provider_ref: str
    cue_span: AnalysisSpan | None
    target_span: AnalysisSpan | None
    reasons: tuple[str, ...]


ACTION_HEAD = re.compile(
    r"(?:する|した|される|された|返す|返した|返る|記録する|処理する|処理した|保存する|表示する|生成する|更新する|削除する|送信する|測定する|検証する|実行する|処理|記録|返却|保存|表示|生成|更新|削除|送信|測定|検証|実行)$"
)


def _overlaps(left: AnalysisSpan, right: AnalysisSpan) -> bool:
    return left.start < right.end and right.start < left.end


def _signal_span(signal: ResidualRiskSignal) -> AnalysisSpan:
    return AnalysisSpan(signal.start, signal.end, signal.category)


def _within_field(
    span: AnalysisSpan,
    signal: ResidualRiskSignal,
    record: ParsedRequirementRecord,
) -> bool:
    values = record.fields.get(signal.field_name, ())
    return any(item.value_start <= span.start < span.end <= item.value_end for item in values)


def _edge_connects(
    relation: RelationCandidate,
    cue: AnalysisSpan,
    target: AnalysisSpan,
) -> bool:
    if not relation.relation_kind.startswith("dependency:"):
        return False
    return (
        _overlaps(relation.from_span, cue) and _overlaps(relation.to_span, target)
    ) or (
        _overlaps(relation.to_span, cue) and _overlaps(relation.from_span, target)
    )


def _condition_candidates(
    signal: ResidualRiskSignal,
    record: ParsedRequirementRecord,
    attempts: tuple[AnalysisAttempt, ...],
) -> list[tuple[AnalysisAttempt, ScopeCandidate]]:
    cue = _signal_span(signal)
    candidates: list[tuple[AnalysisAttempt, ScopeCandidate]] = []
    for attempt in attempts:
        if (
            attempt.stage != "dependency_parse"
            or attempt.status not in {"ok", "partial"}
            or not {"dependency", "scope"}.issubset(
                attempt.fulfilled_capabilities
            )
        ):
            continue
        if not any(_overlaps(item, cue) for item in attempt.covered_spans):
            continue
        for scope in attempt.scopes:
            if scope.scope_kind not in {"condition", "conditional", "conditional_scope"}:
                continue
            if not _overlaps(scope.cue_span, cue) or scope.target_span is None:
                continue
            if not _within_field(scope.target_span, signal, record):
                continue
            target_text = record.source_text[scope.target_span.start : scope.target_span.end]
            if not ACTION_HEAD.search(target_text):
                continue
            if not any(
                _edge_connects(relation, scope.cue_span, scope.target_span)
                for relation in attempt.relations
            ):
                continue
            candidates.append((attempt, scope))
    return candidates


def evaluate_lifting_resolutions(
    signals: tuple[ResidualRiskSignal, ...],
    record: ParsedRequirementRecord,
    attempts: tuple[AnalysisAttempt, ...],
) -> tuple[LiftingResolution, ...]:
    """Apply narrowly versioned rules to provider candidates.

    Provider output alone never releases a hold.  The only v0 release rule is
    for an explicitly marked condition with one source-aligned dependency
    attachment to an action head in the same declared field.  Every other
    semantic scope remains unresolved.
    """

    resolutions: list[LiftingResolution] = []
    for signal in signals:
        if signal.reason_code != "conditional_or_exception_scope_present":
            resolutions.append(
                LiftingResolution(
                    signal_id=signal.signal_id,
                    status="not_applicable",
                    rule_id="lifting.condition-attachment/v0",
                    provider_ref="",
                    cue_span=None,
                    target_span=None,
                    reasons=("no_lifting_rule_for_signal_kind",),
                )
            )
            continue
        candidates = _condition_candidates(signal, record, attempts)
        unique = {
            (
                scope.cue_span.start,
                scope.cue_span.end,
                scope.target_span.start if scope.target_span else -1,
                scope.target_span.end if scope.target_span else -1,
            )
            for _, scope in candidates
        }
        if len(unique) != 1:
            resolutions.append(
                LiftingResolution(
                    signal_id=signal.signal_id,
                    status="unresolved",
                    rule_id="lifting.condition-attachment/v0",
                    provider_ref="",
                    cue_span=_signal_span(signal),
                    target_span=None,
                    reasons=(
                        "no_source_aligned_condition_attachment"
                        if not unique
                        else "multiple_condition_attachments",
                    ),
                )
            )
            continue
        attempt, scope = candidates[0]
        resolutions.append(
            LiftingResolution(
                signal_id=signal.signal_id,
                status="resolved",
                rule_id="lifting.condition-attachment/v0",
                provider_ref=f"{attempt.provider_id}:{attempt.provider_version}:{attempt.resource_version}",
                cue_span=scope.cue_span,
                target_span=scope.target_span,
                reasons=(
                    "single_source_aligned_dependency_attachment",
                    "condition_preserved_as_requirement_semantics",
                ),
            )
        )
    return tuple(resolutions)
