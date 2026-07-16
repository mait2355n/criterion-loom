from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Literal, Protocol, Sequence, runtime_checkable


ProviderStage = Literal["morphology", "dependency_parse", "llm_candidate"]
ProviderStatus = Literal["ok", "partial", "failed", "not_configured"]


@dataclass(frozen=True, slots=True)
class AnalysisSpan:
    start: int
    end: int
    role: str = ""

    def __post_init__(self) -> None:
        if self.start < 0 or self.end < self.start:
            raise ValueError("analysis span must satisfy 0 <= start <= end")


@dataclass(frozen=True, slots=True)
class ProviderRequest:
    text: str
    target_spans: tuple[AnalysisSpan, ...]
    reason_codes: tuple[str, ...]
    requested_capabilities: tuple[str, ...]
    upstream_tokens: tuple[TokenCandidate, ...] = ()
    upstream_relations: tuple[RelationCandidate, ...] = ()
    upstream_scopes: tuple[ScopeCandidate, ...] = ()


@dataclass(frozen=True, slots=True)
class TokenCandidate:
    surface: str
    lemma: str
    normalized: str
    part_of_speech: tuple[str, ...]
    start: int
    end: int
    features: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RelationCandidate:
    relation_kind: str
    from_span: AnalysisSpan
    to_span: AnalysisSpan
    confidence: float | None = None
    interpretation_id: str = ""
    rationale: str = ""


@dataclass(frozen=True, slots=True)
class ScopeCandidate:
    scope_kind: str
    cue_span: AnalysisSpan
    target_span: AnalysisSpan | None = None
    confidence: float | None = None


@dataclass(frozen=True, slots=True)
class ProviderAuthority:
    support: bool = False
    challenge_signal: bool = True
    apply_hold: bool = False
    release_hold: bool = False


@dataclass(frozen=True, slots=True)
class AnalysisAttempt:
    stage: ProviderStage
    provider_id: str
    provider_version: str
    resource_version: str
    status: ProviderStatus
    authority: ProviderAuthority
    requested_capabilities: tuple[str, ...]
    fulfilled_capabilities: tuple[str, ...]
    covered_spans: tuple[AnalysisSpan, ...] = ()
    tokens: tuple[TokenCandidate, ...] = ()
    relations: tuple[RelationCandidate, ...] = ()
    scopes: tuple[ScopeCandidate, ...] = ()
    upstream_usage: tuple[str, ...] = ()
    diagnostics: tuple[str, ...] = ()

    @property
    def missing_capabilities(self) -> tuple[str, ...]:
        fulfilled = set(self.fulfilled_capabilities)
        return tuple(
            capability
            for capability in self.requested_capabilities
            if capability not in fulfilled
        )


@runtime_checkable
class AnalysisProvider(Protocol):
    provider_id: str
    provider_version: str
    resource_version: str
    stage: ProviderStage

    def analyze(self, request: ProviderRequest) -> AnalysisAttempt: ...


def _span_within_text(span: AnalysisSpan, text: str) -> bool:
    return (
        isinstance(span, AnalysisSpan)
        and isinstance(span.start, int)
        and isinstance(span.end, int)
        and 0 <= span.start <= span.end <= len(text)
    )


def _valid_candidate(candidate: RelationCandidate, text: str) -> bool:
    return (
        isinstance(candidate, RelationCandidate)
        and isinstance(candidate.relation_kind, str)
        and bool(candidate.relation_kind.strip())
        and _span_within_text(candidate.from_span, text)
        and _span_within_text(candidate.to_span, text)
        and (
            candidate.confidence is None
            or (
                isinstance(candidate.confidence, (int, float))
                and not isinstance(candidate.confidence, bool)
                and 0.0 <= float(candidate.confidence) <= 1.0
            )
        )
    )


def _failed_attempt(
    *,
    stage: ProviderStage,
    provider_id: str,
    provider_version: str,
    resource_version: str,
    requested_capabilities: tuple[str, ...],
    diagnostics: tuple[str, ...],
) -> AnalysisAttempt:
    return AnalysisAttempt(
        stage=stage,
        provider_id=provider_id or "unknown",
        provider_version=provider_version,
        resource_version=resource_version,
        status="failed",
        authority=ProviderAuthority(challenge_signal=stage != "morphology"),
        requested_capabilities=requested_capabilities,
        fulfilled_capabilities=(),
        diagnostics=diagnostics,
    )


def _provider_identity(provider: object) -> tuple[str, str, str, object]:
    return (
        str(getattr(provider, "provider_id", "") or "unknown"),
        str(getattr(provider, "provider_version", "") or ""),
        str(getattr(provider, "resource_version", "") or ""),
        getattr(provider, "stage", None),
    )


def _capability_tuple(value: object) -> tuple[str, ...] | None:
    if not isinstance(value, (tuple, list)):
        return None
    capabilities = tuple(value)
    if (
        any(not isinstance(item, str) or not item.strip() for item in capabilities)
        or len(set(capabilities)) != len(capabilities)
    ):
        return None
    return capabilities


def _merged_intervals(spans: Sequence[AnalysisSpan]) -> tuple[tuple[int, int], ...]:
    intervals = sorted(
        (span.start, span.end)
        for span in spans
        if isinstance(span, AnalysisSpan) and span.start < span.end
    )
    merged: list[tuple[int, int]] = []
    for start, end in intervals:
        if not merged or start > merged[-1][1]:
            merged.append((start, end))
            continue
        previous_start, previous_end = merged[-1]
        merged[-1] = (previous_start, max(previous_end, end))
    return tuple(merged)


def _uncovered_target_spans(
    targets: Sequence[AnalysisSpan],
    covered: Sequence[AnalysisSpan],
) -> tuple[AnalysisSpan, ...]:
    """Return every positive-length target fragment outside the covered union."""

    coverage = _merged_intervals(covered)
    uncovered: list[AnalysisSpan] = []
    for target in targets:
        if target.start >= target.end:
            continue
        cursor = target.start
        for start, end in coverage:
            if end <= cursor:
                continue
            if start >= target.end:
                break
            if start > cursor:
                uncovered.append(
                    AnalysisSpan(cursor, min(start, target.end), target.role)
                )
            cursor = max(cursor, end)
            if cursor >= target.end:
                break
        if cursor < target.end:
            uncovered.append(AnalysisSpan(cursor, target.end, target.role))
    return tuple(uncovered)


def run_provider(
    provider: AnalysisProvider | None,
    request: ProviderRequest,
    *,
    stage: ProviderStage,
) -> AnalysisAttempt:
    """Run a provider behind a fail-closed, non-escalating boundary."""

    requested_capabilities = _capability_tuple(request.requested_capabilities)
    if requested_capabilities is None:
        return _failed_attempt(
            stage=stage,
            provider_id="unknown",
            provider_version="",
            resource_version="",
            requested_capabilities=(),
            diagnostics=("provider_request_invalid:requested_capabilities",),
        )
    target_spans = tuple(request.target_spans)
    if any(
        not _span_within_text(span, request.text)
        for span in target_spans
    ):
        return _failed_attempt(
            stage=stage,
            provider_id="unknown",
            provider_version="",
            resource_version="",
            requested_capabilities=requested_capabilities,
            diagnostics=("provider_request_invalid:target_spans",),
        )

    if provider is None:
        return AnalysisAttempt(
            stage=stage,
            provider_id="not-configured",
            provider_version="",
            resource_version="",
            status="not_configured",
            authority=ProviderAuthority(challenge_signal=stage != "morphology"),
            requested_capabilities=requested_capabilities,
            fulfilled_capabilities=(),
            diagnostics=("provider_not_configured",),
        )
    try:
        provider_id, provider_version, resource_version, declared_stage = _provider_identity(
            provider
        )
    except Exception as exc:
        return _failed_attempt(
            stage=stage,
            provider_id="unknown",
            provider_version="",
            resource_version="",
            requested_capabilities=requested_capabilities,
            diagnostics=(f"provider_identity_error:{type(exc).__name__}:{exc}",),
        )
    if declared_stage != stage:
        return AnalysisAttempt(
            stage=stage,
            provider_id=provider_id,
            provider_version=provider_version,
            resource_version=resource_version,
            status="failed",
            authority=ProviderAuthority(challenge_signal=stage != "morphology"),
            requested_capabilities=requested_capabilities,
            fulfilled_capabilities=(),
            diagnostics=(f"provider_stage_mismatch:{declared_stage}",),
        )

    try:
        attempt = provider.analyze(request)
    except Exception as exc:  # provider boundary deliberately converts failure to evidence
        return _failed_attempt(
            stage=stage,
            provider_id=provider_id,
            provider_version=provider_version,
            resource_version=resource_version,
            requested_capabilities=requested_capabilities,
            diagnostics=(f"provider_exception:{type(exc).__name__}:{exc}",),
        )

    if not isinstance(attempt, AnalysisAttempt):
        return _failed_attempt(
            stage=stage,
            provider_id=provider_id,
            provider_version=provider_version,
            resource_version=resource_version,
            requested_capabilities=requested_capabilities,
            diagnostics=(
                f"provider_contract_invalid:return_type:{type(attempt).__name__}",
            ),
        )

    try:
        provider_id, provider_version, resource_version, declared_stage = _provider_identity(
            provider
        )
        diagnostics = [str(item) for item in tuple(attempt.diagnostics)]
        contract_invalid = False
        reported_requested = _capability_tuple(attempt.requested_capabilities)
        reported_fulfilled = _capability_tuple(attempt.fulfilled_capabilities)
        if reported_requested is None:
            diagnostics.append("provider_contract_invalid:requested_capabilities")
            reported_requested = ()
            contract_invalid = True
        elif reported_requested != requested_capabilities:
            diagnostics.append("provider_requested_capabilities_mismatch")
            contract_invalid = True
        if reported_fulfilled is None:
            diagnostics.append("provider_contract_invalid:fulfilled_capabilities")
            reported_fulfilled = ()
            contract_invalid = True
        elif not set(reported_fulfilled).issubset(requested_capabilities):
            diagnostics.append("provider_fulfilled_unrequested_capability")
            contract_invalid = True
        if declared_stage != stage:
            diagnostics.append(f"provider_stage_changed:{declared_stage}")
            contract_invalid = True
        if attempt.stage != stage:
            diagnostics.append(f"attempt_stage_mismatch:{attempt.stage}")
            contract_invalid = True
        if attempt.provider_id != provider_id:
            diagnostics.append(
                f"provider_id_mismatch:{attempt.provider_id}:{provider_id}"
            )
            contract_invalid = True
        if attempt.provider_version != provider_version:
            diagnostics.append(
                f"provider_version_mismatch:{attempt.provider_version}:{provider_version}"
            )
            contract_invalid = True
        if attempt.resource_version != resource_version:
            diagnostics.append(
                f"resource_version_mismatch:{attempt.resource_version}:{resource_version}"
            )
            contract_invalid = True
        if attempt.status not in {"ok", "partial", "failed", "not_configured"}:
            diagnostics.append(f"provider_status_invalid:{attempt.status}")
            contract_invalid = True

        raw_covered = tuple(attempt.covered_spans)
        covered = tuple(
            span for span in raw_covered if _span_within_text(span, request.text)
        )
        if len(covered) != len(raw_covered):
            diagnostics.append("invalid_covered_span_dropped")
            contract_invalid = True

        uncovered_targets = _uncovered_target_spans(target_spans, covered)
        coverage_partial = bool(uncovered_targets) and attempt.status in {"ok", "partial"}
        if coverage_partial:
            diagnostics.append(
                "provider_target_coverage_partial:"
                + ",".join(
                    f"{span.start}:{span.end}" for span in uncovered_targets
                )
            )

        raw_tokens = tuple(attempt.tokens)
        tokens = tuple(
            token
            for token in raw_tokens
            if isinstance(token, TokenCandidate)
            and isinstance(token.start, int)
            and isinstance(token.end, int)
            and 0 <= token.start < token.end <= len(request.text)
            and request.text[token.start : token.end] == token.surface
        )
        if len(tokens) != len(raw_tokens):
            diagnostics.append("invalid_token_span_or_surface_dropped")
            contract_invalid = True

        raw_relations = tuple(attempt.relations)
        relations = tuple(
            candidate
            for candidate in raw_relations
            if _valid_candidate(candidate, request.text)
        )
        if len(relations) != len(raw_relations):
            diagnostics.append("invalid_relation_span_dropped")
            contract_invalid = True

        if stage == "morphology" and raw_relations:
            diagnostics.append("stage_output_not_permitted:morphology:relations")
            relations = ()
            contract_invalid = True

        raw_scopes = tuple(attempt.scopes)
        scopes = tuple(
            candidate
            for candidate in raw_scopes
            if isinstance(candidate, ScopeCandidate)
            and isinstance(candidate.scope_kind, str)
            and bool(candidate.scope_kind.strip())
            and _span_within_text(candidate.cue_span, request.text)
            and candidate.cue_span.start < candidate.cue_span.end
            and (
                candidate.target_span is None
                or (
                    _span_within_text(candidate.target_span, request.text)
                    and candidate.target_span.start < candidate.target_span.end
                )
            )
            and (
                candidate.confidence is None
                or (
                    isinstance(candidate.confidence, (int, float))
                    and not isinstance(candidate.confidence, bool)
                    and 0.0 <= float(candidate.confidence) <= 1.0
                )
            )
        )
        if len(scopes) != len(raw_scopes):
            diagnostics.append("invalid_scope_span_dropped")
            contract_invalid = True
        if stage == "morphology" and raw_scopes:
            diagnostics.append("stage_output_not_permitted:morphology:scopes")
            scopes = ()
            contract_invalid = True

        raw_upstream_usage = tuple(attempt.upstream_usage)
        upstream_usage = tuple(
            item
            for item in raw_upstream_usage
            if isinstance(item, str) and item.strip()
        )
        if len(upstream_usage) != len(raw_upstream_usage) or len(set(upstream_usage)) != len(
            upstream_usage
        ):
            diagnostics.append("provider_contract_invalid:upstream_usage")
            upstream_usage = ()
            contract_invalid = True

        nonempty_request = bool(request.text) and any(
            span.start < span.end for span in request.target_spans
        )
        if (
            nonempty_request
            and attempt.status == "ok"
            and stage == "morphology"
            and not tokens
        ):
            diagnostics.append("provider_coverage_invalid:morphology:no_tokens")
            contract_invalid = True
        if (
            nonempty_request
            and attempt.status == "ok"
            and stage == "dependency_parse"
            and not tokens
            and not relations
            and not scopes
        ):
            diagnostics.append(
                "provider_coverage_invalid:dependency_parse:no_candidate_material"
            )
            contract_invalid = True

        fulfilled = tuple(reported_fulfilled)
        if coverage_partial:
            # Capabilities are requested over the target union.  A provider that
            # did not cover that union cannot report any of them as wholly met.
            fulfilled = ()
        missing_capabilities = tuple(
            capability
            for capability in requested_capabilities
            if capability not in set(fulfilled)
        )
        capability_partial = (
            bool(missing_capabilities) and attempt.status in {"ok", "partial"}
        )
        if capability_partial:
            diagnostics.append(
                "provider_capabilities_unfulfilled:"
                + ",".join(missing_capabilities)
            )
        if attempt.status in {"failed", "not_configured"} and fulfilled:
            diagnostics.append(
                f"provider_capabilities_invalid_for_status:{attempt.status}"
            )
            fulfilled = ()
            contract_invalid = True
    except Exception as exc:
        return _failed_attempt(
            stage=stage,
            provider_id=provider_id,
            provider_version=provider_version,
            resource_version=resource_version,
            requested_capabilities=requested_capabilities,
            diagnostics=(
                f"provider_contract_invalid:{type(exc).__name__}:{exc}",
            ),
        )

    # Providers may supply candidates and challenge signals. They never acquire
    # support, hold-application, or hold-release authority by self-declaration.
    normalized_status = attempt.status
    if normalized_status == "ok" and (coverage_partial or capability_partial):
        normalized_status = "partial"
    if contract_invalid:
        normalized_status = "failed"
        fulfilled = ()
    return replace(
        attempt,
        stage=stage,
        provider_id=provider_id,
        provider_version=provider_version,
        resource_version=resource_version,
        status=normalized_status,
        authority=ProviderAuthority(
            support=False,
            challenge_signal=stage != "morphology",
            apply_hold=False,
            release_hold=False,
        ),
        requested_capabilities=requested_capabilities,
        fulfilled_capabilities=fulfilled,
        covered_spans=covered,
        tokens=tokens,
        relations=relations,
        scopes=scopes,
        upstream_usage=upstream_usage,
        diagnostics=tuple(diagnostics),
    )


def target_spans_for_reasons(
    text: str,
    spans: Sequence[AnalysisSpan],
) -> tuple[AnalysisSpan, ...]:
    valid = [span for span in spans if _span_within_text(span, text) and span.start < span.end]
    return tuple(sorted(set(valid), key=lambda item: (item.start, item.end, item.role)))
