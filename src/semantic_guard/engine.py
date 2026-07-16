from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
import hashlib
from typing import Any, Literal

from .aggregation import aggregate_audit_result
from .dependency_projection import (
    DependencyRelationProjection,
    project_dependency_relations,
)
from .direct_rules import DirectRelationAssessment, evaluate_direct_relations
from .lifting import LiftingResolution, evaluate_lifting_resolutions
from .models import (
    AuditExecution,
    Challenge,
    Coverage,
    DecisionRequest,
    EvidenceRef,
    EvidenceRole,
    Finality,
    GuardCoverage,
    Hold,
    ObligationResult,
    Outcome,
    SourceSpan,
    StageAuthority,
    AuditResult,
)
from .profiles import FUNCTIONAL_REQUIREMENT_PROFILE, NormativeProfile
from .provider_receipts import (
    AnalyzerQualification,
    EMPTY_QUALIFIED_ANALYZER_REGISTRY,
    ProviderExecutionReceipt,
    QualifiedAnalyzerRegistry,
    build_provider_execution_receipt,
)
from .providers import (
    AnalysisAttempt,
    AnalysisProvider,
    AnalysisSpan,
    ProviderRequest,
    ProviderStage,
    RelationCandidate,
    TokenCandidate,
    run_provider,
)
from .reassessment import (
    ObligationReassessment,
    REASSESSMENT_POLICY_VERSION,
    reassess_obligations,
    used_qualifications,
)
from .records import ParsedRequirementRecord, parse_requirement_record
from .residual_risk import ResidualRiskSignal, scan_residual_risks
from .routing import (
    FIELD_OBLIGATIONS,
    StagePlan,
    UnresolvedObligation,
    affected_obligation_ids,
    build_unresolved_obligations,
    capabilities_for_stage,
    make_stage_plan,
    reason_codes_for,
)


AnalysisMode = Literal["assurance", "conditional", "shadow_all"]


CATEGORY_GUARD = {
    "record_boundary": "record_boundary",
    "discourse_scope": "discourse_scope",
    "temporal_scope": "temporal_scope",
    "polarity_scope": "polarity_scope",
    "modality_scope": "modality_scope",
    "conditional_scope": "attachment",
    "attachment": "attachment",
}


@dataclass(frozen=True, slots=True)
class RequirementAuditReport:
    source_id: str
    profile_id: str
    profile_version: str
    applicability: str
    record: ParsedRequirementRecord
    direct_assessments: tuple[DirectRelationAssessment, ...]
    residual_signals: tuple[ResidualRiskSignal, ...]
    shadow_signals: tuple[ResidualRiskSignal, ...]
    analysis_attempts: tuple[AnalysisAttempt, ...]
    provider_execution_receipts: tuple[ProviderExecutionReceipt, ...]
    dependency_projections: tuple[DependencyRelationProjection, ...]
    obligation_reassessments: tuple[ObligationReassessment, ...]
    analyzer_qualifications: tuple[AnalyzerQualification, ...]
    lifting_resolutions: tuple[LiftingResolution, ...]
    initial_unresolved_obligations: tuple[UnresolvedObligation, ...]
    remaining_unresolved_obligations: tuple[UnresolvedObligation, ...]
    unresolved_obligations: tuple[UnresolvedObligation, ...]
    stage_plans: tuple[StagePlan, ...]
    result: AuditResult
    analysis_mode: AnalysisMode
    limitations: tuple[str, ...]
    schema_version: str = "semantic-guard-requirement-audit/v0"

    def as_dict(self) -> dict[str, Any]:
        payload = _wire(self)
        assert isinstance(payload, dict)
        payload["summary"] = self.result.obligation_ids_by_outcome()
        payload["record"] = {
            "record_mode": self.record.record_mode,
            "record_count": self.record.record_count,
            "field_names": sorted(name for name, values in self.record.fields.items() if values),
            "missing_fields": list(self.record.missing_fields),
            "duplicate_fields": list(self.record.duplicate_fields),
            "unconsumed_spans": [
                {"start": start, "end": end, "text": self.record.source_text[start:end]}
                for start, end in self.record.unconsumed_spans
            ],
            "diagnostics": list(self.record.diagnostics),
        }
        return payload


def _wire(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (UnresolvedObligation, StagePlan)):
        return value.as_dict()
    if isinstance(value, dict):
        return {str(key): _wire(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_wire(item) for item in value]
    if is_dataclass(value):
        return {item.name: _wire(getattr(value, item.name)) for item in fields(value)}
    return value


def _source_id(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _applicability(record: ParsedRequirementRecord) -> str:
    functional_fields = {
        "scenario",
        "expected_result",
        "acceptance_criteria",
        "verification_method",
    }
    observed = {name for name, values in record.fields.items() if values}
    if functional_fields & observed:
        return "applicable"
    return "unknown"


def _source_span(source_id: str, text: str, start: int, end: int) -> SourceSpan:
    return SourceSpan(source_id=source_id, start=start, end=end, text=text[start:end])


def _direct_evidence(
    source_id: str,
    text: str,
    assessment: DirectRelationAssessment,
) -> tuple[EvidenceRef, ...]:
    if assessment.outcome in {"supported", "not_applicable"}:
        role = EvidenceRole.SUPPORT
    elif assessment.outcome == "refuted":
        role = EvidenceRole.CHALLENGE
    else:
        role = EvidenceRole.SIGNAL
    authority = StageAuthority.assertion_capable(assessment.rule_id)
    spans = assessment.evidence_spans or ((0, len(text)),)
    return tuple(
        EvidenceRef(
            evidence_id=f"evidence.{assessment.obligation_id}.{index}.{start}.{end}",
            role=role,
            authority=authority,
            source_ref=source_id,
            source_span=_source_span(source_id, text, start, end),
            summary="; ".join(assessment.basis or assessment.unknown_reasons),
        )
        for index, (start, end) in enumerate(spans, start=1)
        if end > start
    )


def _signal_evidence(
    source_id: str,
    text: str,
    signal: ResidualRiskSignal,
    *,
    authority: StageAuthority,
) -> EvidenceRef:
    return EvidenceRef(
        evidence_id=f"evidence.{signal.signal_id}",
        role=EvidenceRole.CHALLENGE,
        authority=authority,
        source_ref=source_id,
        source_span=(
            _source_span(source_id, text, signal.start, signal.end)
            if signal.end > signal.start
            else None
        ),
        summary=f"{signal.reason_code}; route={signal.next_route}",
    )


def _affected_obligations(signal: ResidualRiskSignal) -> frozenset[str]:
    return affected_obligation_ids(signal)


def _provider_target_spans(
    record: ParsedRequirementRecord,
    signals: tuple[ResidualRiskSignal, ...],
    direct: tuple[DirectRelationAssessment, ...],
    *,
    shadow_all: bool,
) -> tuple[AnalysisSpan, ...]:
    spans: list[AnalysisSpan] = []
    if shadow_all:
        for name, values in record.fields.items():
            spans.extend(AnalysisSpan(item.value_start, item.value_end, name) for item in values if item.value)
    else:
        for signal in signals:
            if signal.end > signal.start:
                spans.append(AnalysisSpan(signal.start, signal.end, signal.field_name))
            for field in record.fields.get(signal.field_name, ()):
                if field.value:
                    spans.append(
                        AnalysisSpan(field.value_start, field.value_end, signal.field_name)
                    )
        unresolved = {item.obligation_id for item in direct if item.outcome == "unresolved"}
        for field_name, obligation_ids in FIELD_OBLIGATIONS.items():
            if field_name == "record" or not (unresolved & obligation_ids):
                continue
            spans.extend(
                AnalysisSpan(item.value_start, item.value_end, field_name)
                for item in record.fields.get(field_name, ())
                if item.value
            )
    return tuple(sorted(set(spans), key=lambda item: (item.start, item.end, item.role)))


def _route_target_obligation_ids(
    profile: NormativeProfile,
    drivers: tuple[UnresolvedObligation, ...],
    *,
    full_coverage: bool,
) -> tuple[str, ...]:
    if full_coverage:
        return tuple(item.obligation_id for item in profile.obligations)
    driver_ids = {item.obligation_id for item in drivers}
    return tuple(
        item.obligation_id
        for item in profile.obligations
        if item.obligation_id in driver_ids
    )


def _stage_plan_causes(
    *,
    analysis_mode: AnalysisMode,
    stage: ProviderStage,
    should_run: bool,
    drivers: tuple[UnresolvedObligation, ...],
) -> tuple[str, ...]:
    if not should_run:
        return ("no_unresolved_material",)

    causes: list[str] = []
    if analysis_mode in {"assurance", "shadow_all"}:
        causes.append(f"analysis_mode:{analysis_mode}")
    if any(item.direct_outcome == "unresolved" for item in drivers):
        causes.append("direct_assessment_unresolved")
    if any(item.signal_ids for item in drivers):
        causes.append("residual_signal_present")

    requested_routes = {
        route
        for item in drivers
        for _, route in item.reason_routes
    }
    if stage in requested_routes:
        causes.append(f"requested_route:{stage}")
    elif stage == "morphology" and requested_routes:
        causes.append("pipeline_prerequisite:downstream_analysis")
    elif stage == "dependency_parse" and requested_routes:
        causes.append("unresolved_after:morphology_or_direct_rules")
    elif stage == "llm_candidate" and drivers:
        causes.append("unresolved_after:dependency_parse")
    if not causes:
        causes.append("versioned_pipeline_policy")
    return tuple(dict.fromkeys(causes))


def _morphology_signals(attempt: AnalysisAttempt) -> tuple[ResidualRiskSignal, ...]:
    negation_lemmas = {"ない", "ぬ", "ず", "無い", "not", "never"}
    signals: list[ResidualRiskSignal] = []
    for index, token in enumerate(attempt.tokens, start=1):
        if token.lemma.casefold() not in {item.casefold() for item in negation_lemmas} and token.normalized.casefold() not in {
            item.casefold() for item in negation_lemmas
        }:
            continue
        signals.append(
            ResidualRiskSignal(
                signal_id=f"signal.morphology.negation.{token.start}.{index}",
                reason_code="morphology_negation_candidate",
                category="polarity_scope",
                field_name="record",
                start=token.start,
                end=token.end,
                excerpt=token.surface,
                detected_by=f"provider:{attempt.provider_id}:{attempt.provider_version}",
                next_route="dependency_parse",
                limitations=("Token identity does not determine the scope or meaning of negation.",),
            )
        )
    return tuple(signals)


def _field_name_for_span(
    record: ParsedRequirementRecord,
    span: AnalysisSpan,
) -> str:
    for name, values in record.fields.items():
        if any(item.value_start <= span.start < span.end <= item.value_end for item in values):
            return name
    return "record"


def _provider_scope_signals(
    attempt: AnalysisAttempt,
    record: ParsedRequirementRecord,
) -> tuple[ResidualRiskSignal, ...]:
    mapping = {
        "condition": (
            "conditional_or_exception_scope_present",
            "conditional_scope",
            "deterministic_lifting",
        ),
        "conditional": (
            "conditional_or_exception_scope_present",
            "conditional_scope",
            "deterministic_lifting",
        ),
        "conditional_scope": (
            "conditional_or_exception_scope_present",
            "conditional_scope",
            "deterministic_lifting",
        ),
        "negation": (
            "dependency_negation_scope_candidate",
            "polarity_scope",
            "llm_candidate",
        ),
        "modality": (
            "dependency_modality_scope_candidate",
            "modality_scope",
            "llm_candidate",
        ),
        "quotation": (
            "dependency_quotation_scope_candidate",
            "discourse_scope",
            "llm_candidate",
        ),
        "reporting": (
            "dependency_reporting_scope_candidate",
            "discourse_scope",
            "llm_candidate",
        ),
        "countercondition": (
            "llm_countercondition_candidate",
            "conditional_scope",
            "assertion_capable_recomparison",
        ),
        "countercondition_candidate": (
            "llm_countercondition_candidate",
            "conditional_scope",
            "assertion_capable_recomparison",
        ),
        "exception": (
            "llm_countercondition_candidate",
            "conditional_scope",
            "assertion_capable_recomparison",
        ),
        "alternative_interpretation": (
            "llm_alternative_scope_candidate",
            "attachment",
            "requirement_owner_interpretation",
        ),
    }
    signals: list[ResidualRiskSignal] = []
    for index, scope in enumerate(attempt.scopes, start=1):
        values = mapping.get(scope.scope_kind)
        if values is None:
            if attempt.stage != "llm_candidate":
                continue
            values = (
                "llm_unmapped_scope_candidate",
                "attachment",
                "requirement_owner_interpretation",
            )
        reason_code, category, route = values
        cue = scope.cue_span
        signals.append(
            ResidualRiskSignal(
                signal_id=f"signal.dependency.{reason_code}.{cue.start}.{index}",
                reason_code=reason_code,
                category=category,
                field_name=_field_name_for_span(record, cue),
                start=cue.start,
                end=cue.end,
                excerpt=record.source_text[cue.start : cue.end],
                detected_by=f"provider:{attempt.provider_id}:{attempt.provider_version}",
                next_route=route,
                limitations=(
                    "A provider scope is candidate material; its meaning and attachment require a versioned assertion-capable rule or bounded human adjudication.",
                ),
            )
        )
    return tuple(signals)


def _new_scope_signals(
    candidates: tuple[ResidualRiskSignal, ...],
    existing: tuple[ResidualRiskSignal, ...],
) -> tuple[ResidualRiskSignal, ...]:
    return tuple(
        candidate
        for candidate in candidates
        if not any(
            item.category == candidate.category
            and item.field_name == candidate.field_name
            and item.start < candidate.end
            and candidate.start < item.end
            for item in existing
        )
    )


def _candidate_conflicts(
    candidates: tuple[RelationCandidate, ...],
    direct: tuple[DirectRelationAssessment, ...],
    profile: NormativeProfile,
    record: ParsedRequirementRecord,
) -> dict[str, tuple[RelationCandidate, ...]]:
    relation_to_obligation = {item.relation_kind: item.obligation_id for item in profile.obligations}
    expected = {item.obligation_id: item.evidence_spans for item in direct}
    assessments = {item.obligation_id: item for item in direct}
    conflicts: dict[str, list[RelationCandidate]] = {}
    grouped: dict[str, list[RelationCandidate]] = {}
    for candidate in candidates:
        obligation_id = relation_to_obligation.get(candidate.relation_kind)
        if obligation_id is None:
            continue
        grouped.setdefault(obligation_id, []).append(candidate)
        assessment = assessments[obligation_id]
        if assessment.outcome in {"refuted", "not_applicable", "invalid"}:
            conflicts.setdefault(obligation_id, []).append(candidate)
            continue
        expected_spans = expected.get(obligation_id, ())
        if expected_spans and not all(
            any(span_start <= endpoint.start and endpoint.end <= span_end for span_start, span_end in expected_spans)
            for endpoint in (candidate.from_span, candidate.to_span)
        ):
            conflicts.setdefault(obligation_id, []).append(candidate)
            continue
        if assessment.outcome != "supported":
            continue
        if candidate.relation_kind == "performs":
            actor = record.one("user")
            actor_occurrences: list[tuple[int, int]] = []
            if actor is not None:
                search_from = 0
                while True:
                    start = record.source_text.casefold().find(
                        actor.value.casefold(), search_from
                    )
                    if start < 0:
                        break
                    actor_occurrences.append((start, start + len(actor.value)))
                    search_from = start + max(1, len(actor.value))
            if actor is not None and not any(
                start <= candidate.from_span.start
                and candidate.from_span.end <= end
                for start, end in actor_occurrences
            ):
                conflicts.setdefault(obligation_id, []).append(candidate)
        elif candidate.relation_kind == "acts_on":
            expected_objects = {
                item.split(":", 1)[1]
                for item in assessment.basis
                if item.startswith("object_marker:")
            }
            candidate_object = record.source_text[
                candidate.to_span.start : candidate.to_span.end
            ]
            if expected_objects and not any(
                item.casefold() in candidate_object.casefold()
                or candidate_object.casefold() in item.casefold()
                for item in expected_objects
            ):
                conflicts.setdefault(obligation_id, []).append(candidate)
    for obligation_id, candidates in grouped.items():
        endpoints = {
            (item.from_span.start, item.from_span.end, item.to_span.start, item.to_span.end)
            for item in candidates
        }
        if len(endpoints) > 1:
            conflicts.setdefault(obligation_id, []).extend(candidates)
    return {key: tuple(dict.fromkeys(values)) for key, values in conflicts.items()}


def audit_requirement_relations(
    text: str,
    *,
    profile: NormativeProfile = FUNCTIONAL_REQUIREMENT_PROFILE,
    morphology_provider: AnalysisProvider | None = None,
    dependency_provider: AnalysisProvider | None = None,
    llm_provider: AnalysisProvider | None = None,
    analysis_mode: AnalysisMode = "assurance",
    analyzer_registry: QualifiedAnalyzerRegistry | None = None,
) -> RequirementAuditReport:
    if analysis_mode not in {"assurance", "conditional", "shadow_all"}:
        raise ValueError("analysis_mode must be assurance, conditional, or shadow_all")
    source_id = _source_id(text)
    record = parse_requirement_record(text)
    applicability = _applicability(record)
    direct = evaluate_direct_relations(record, profile)
    signals = list(scan_residual_risks(record))
    shadow_signals: list[ResidualRiskSignal] = []
    routing_signals = list(signals)
    initial_unresolved = build_unresolved_obligations(
        source_id=source_id,
        profile=profile,
        direct_assessments=direct,
        residual_signals=tuple(routing_signals),
    )
    full_coverage_analysis = analysis_mode in {"assurance", "shadow_all"}
    target_spans = _provider_target_spans(
        record,
        tuple(signals),
        direct,
        shadow_all=full_coverage_analysis,
    )
    unresolved_before_providers = bool(signals) or any(item.outcome == "unresolved" for item in direct)
    run_analysis = full_coverage_analysis or unresolved_before_providers
    attempts: list[AnalysisAttempt] = []
    receipts: list[ProviderExecutionReceipt] = []
    stage_plans: list[StagePlan] = []
    required_stage_failures: list[str] = []

    upstream_tokens: tuple[TokenCandidate, ...] = ()
    morphology: AnalysisAttempt | None = None
    morphology_reason_codes = reason_codes_for(initial_unresolved)
    morphology_capabilities = capabilities_for_stage(
        "morphology",
        morphology_reason_codes,
        full_coverage=full_coverage_analysis,
    )
    if run_analysis:
        morphology_request = ProviderRequest(
            text=text,
            target_spans=target_spans,
            reason_codes=morphology_reason_codes,
            requested_capabilities=morphology_capabilities,
        )
        morphology = run_provider(morphology_provider, morphology_request, stage="morphology")
        attempts.append(morphology)
        receipts.append(build_provider_execution_receipt(morphology_request, morphology))
        upstream_tokens = morphology.tokens
        if analysis_mode != "shadow_all" and morphology.status in {"failed", "not_configured", "partial"}:
            required_stage_failures.append(f"morphology:{morphology.status}")
        if morphology.status in {"ok", "partial"}:
            existing = {
                (item.reason_code, item.start, item.end)
                for item in (*signals, *shadow_signals)
            }
            morphology_signals = [
                item
                for item in _morphology_signals(morphology)
                if (item.reason_code, item.start, item.end) not in existing
            ]
            routing_signals.extend(morphology_signals)
            if analysis_mode == "shadow_all":
                shadow_signals.extend(morphology_signals)
            else:
                signals.extend(morphology_signals)

    morphology_target_ids = _route_target_obligation_ids(
        profile,
        initial_unresolved,
        full_coverage=full_coverage_analysis,
    )
    stage_plans.append(
        make_stage_plan(
            source_id=source_id,
            profile=profile,
            stage="morphology",
            route_decision="run" if run_analysis else "skipped_not_needed",
            run_causes=_stage_plan_causes(
                analysis_mode=analysis_mode,
                stage="morphology",
                should_run=run_analysis,
                drivers=initial_unresolved,
            ),
            drivers=initial_unresolved,
            target_obligation_ids=morphology_target_ids,
            target_spans=target_spans if run_analysis else (),
            provider_configured=morphology_provider is not None,
            attempt=morphology,
            required_capabilities=morphology_capabilities,
        )
    )

    dependency_needed = run_analysis and (
        full_coverage_analysis
        or bool(routing_signals)
        or any(item.outcome == "unresolved" for item in direct)
    )
    dependency_drivers = build_unresolved_obligations(
        source_id=source_id,
        profile=profile,
        direct_assessments=direct,
        residual_signals=tuple(routing_signals),
    )
    dependency_reason_codes = reason_codes_for(dependency_drivers)
    dependency_capabilities = capabilities_for_stage(
        "dependency_parse",
        dependency_reason_codes,
        full_coverage=full_coverage_analysis,
    )
    dependency: AnalysisAttempt | None = None
    if dependency_needed:
        dependency_request = ProviderRequest(
            text=text,
            target_spans=target_spans,
            reason_codes=dependency_reason_codes,
            requested_capabilities=dependency_capabilities,
            upstream_tokens=upstream_tokens,
        )
        dependency = run_provider(dependency_provider, dependency_request, stage="dependency_parse")
        attempts.append(dependency)
        receipts.append(build_provider_execution_receipt(dependency_request, dependency))
        if analysis_mode != "shadow_all" and dependency.status in {"failed", "not_configured", "partial"}:
            required_stage_failures.append(f"dependency_parse:{dependency.status}")
        if dependency.status in {"ok", "partial"}:
            dependency_signals = _new_scope_signals(
                _provider_scope_signals(dependency, record),
                tuple((*signals, *shadow_signals)),
            )
            routing_signals.extend(dependency_signals)
            if analysis_mode == "shadow_all":
                shadow_signals.extend(dependency_signals)
            else:
                signals.extend(dependency_signals)

    dependency_target_ids = _route_target_obligation_ids(
        profile,
        dependency_drivers,
        full_coverage=full_coverage_analysis,
    )
    stage_plans.append(
        make_stage_plan(
            source_id=source_id,
            profile=profile,
            stage="dependency_parse",
            route_decision="run" if dependency_needed else "skipped_not_needed",
            run_causes=_stage_plan_causes(
                analysis_mode=analysis_mode,
                stage="dependency_parse",
                should_run=dependency_needed,
                drivers=dependency_drivers,
            ),
            drivers=dependency_drivers,
            target_obligation_ids=dependency_target_ids,
            target_spans=target_spans if dependency_needed else (),
            provider_configured=dependency_provider is not None,
            attempt=dependency,
            required_capabilities=dependency_capabilities,
        )
    )

    # Materialize the bounded semantic projection before any LLM candidate
    # stage.  This preserves the constitutional pipeline order and gives a
    # future LLM adapter explicit upstream candidate context without granting
    # those candidates assertion authority.
    dependency_projections = project_dependency_relations(
        record,
        tuple(attempts),
        tuple(receipts),
    )
    registry = analyzer_registry or EMPTY_QUALIFIED_ANALYZER_REGISTRY
    obligation_reassessments = reassess_obligations(
        source_id=source_id,
        profile_id=profile.profile_id,
        profile_version=profile.version,
        record=record,
        direct_assessments=direct,
        initial_unresolved_obligations=initial_unresolved,
        projections=dependency_projections,
        attempts=tuple(attempts),
        receipts=tuple(receipts),
        registry=registry,
        residual_signals=tuple(routing_signals),
        shadow=analysis_mode == "shadow_all",
    )
    effective_direct_outcomes = {
        item.obligation_id: item.effective_outcome
        for item in obligation_reassessments
    }
    analyzer_qualifications = used_qualifications(
        obligation_reassessments,
        registry,
    )
    dependency_scopes = tuple(
        scope
        for attempt in attempts
        if attempt.stage == "dependency_parse" and attempt.status in {"ok", "partial"}
        for scope in attempt.scopes
    )

    lifting_resolutions = evaluate_lifting_resolutions(
        tuple(routing_signals),
        record,
        tuple(attempts),
    )
    effectively_resolved_signal_ids = (
        {
            item.signal_id
            for item in lifting_resolutions
            if item.status == "resolved"
        }
        if analysis_mode != "shadow_all"
        else set()
    )
    unresolved_after_dependency = (
        any(
            effective_direct_outcomes.get(item.obligation_id, item.outcome)
            == "unresolved"
            for item in direct
        )
        or any(item.signal_id not in effectively_resolved_signal_ids for item in signals)
        or (
            analysis_mode == "shadow_all"
            and bool(routing_signals)
        )
    )
    llm_active_signals = (
        tuple(routing_signals)
        if analysis_mode == "shadow_all"
        else tuple(
            item
            for item in signals
            if item.signal_id not in effectively_resolved_signal_ids
        )
    )
    llm_drivers = build_unresolved_obligations(
        source_id=source_id,
        profile=profile,
        direct_assessments=direct,
        residual_signals=llm_active_signals,
    )
    llm_needed = unresolved_after_dependency or full_coverage_analysis
    llm_reason_codes = reason_codes_for(llm_drivers)
    llm_capabilities = capabilities_for_stage(
        "llm_candidate",
        llm_reason_codes,
        full_coverage=full_coverage_analysis,
    )
    llm_attempt: AnalysisAttempt | None = None
    if llm_needed:
        llm_request_drivers = build_unresolved_obligations(
            source_id=source_id,
            profile=profile,
            direct_assessments=direct,
            residual_signals=tuple(routing_signals),
        )
        llm_reason_codes = reason_codes_for(llm_request_drivers)
        llm_capabilities = capabilities_for_stage(
            "llm_candidate",
            llm_reason_codes,
            full_coverage=full_coverage_analysis,
        )
        llm_request = ProviderRequest(
            text=text,
            target_spans=target_spans,
            reason_codes=llm_reason_codes,
            requested_capabilities=llm_capabilities,
            upstream_tokens=upstream_tokens,
            upstream_relations=tuple(
                projection.candidate for projection in dependency_projections
            ),
            upstream_scopes=dependency_scopes,
        )
        llm_attempt = run_provider(llm_provider, llm_request, stage="llm_candidate")
        attempts.append(llm_attempt)
        receipts.append(build_provider_execution_receipt(llm_request, llm_attempt))
        if analysis_mode != "shadow_all" and llm_attempt.status in {
            "failed",
            "not_configured",
            "partial",
        }:
            required_stage_failures.append(f"llm_candidate:{llm_attempt.status}")
        if llm_attempt.status in {"ok", "partial"}:
            llm_scope_signals = _new_scope_signals(
                _provider_scope_signals(llm_attempt, record),
                tuple((*signals, *shadow_signals)),
            )
            routing_signals.extend(llm_scope_signals)
            if analysis_mode == "shadow_all":
                shadow_signals.extend(llm_scope_signals)
            else:
                signals.extend(llm_scope_signals)

    llm_target_ids = _route_target_obligation_ids(
        profile,
        llm_drivers,
        full_coverage=full_coverage_analysis,
    )
    stage_plans.append(
        make_stage_plan(
            source_id=source_id,
            profile=profile,
            stage="llm_candidate",
            route_decision="run" if llm_needed else "skipped_not_needed",
            run_causes=_stage_plan_causes(
                analysis_mode=analysis_mode,
                stage="llm_candidate",
                should_run=llm_needed,
                drivers=llm_drivers,
            ),
            drivers=llm_drivers,
            target_obligation_ids=llm_target_ids,
            target_spans=target_spans if llm_needed else (),
            provider_configured=llm_provider is not None,
            attempt=llm_attempt,
            required_capabilities=llm_capabilities,
        )
    )

    candidate_entries: list[tuple[RelationCandidate, str, str, str]] = [
        (
            candidate,
            attempt.stage,
            attempt.provider_id,
            attempt.provider_version,
        )
        for attempt in attempts
        if attempt.status in {"ok", "partial"}
        for candidate in attempt.relations
    ]
    candidate_entries.extend(
        (
            projection.candidate,
            "dependency_projection",
            projection.provider_id,
            projection.provider_version,
        )
        for projection in dependency_projections
    )
    candidate_pool = tuple(item[0] for item in candidate_entries)

    policy_authority = StageAuthority.policy_authority("residual-risk-policy/v0")
    lifting_release_evidence: dict[str, EvidenceRef] = {}
    if analysis_mode != "shadow_all":
        for resolution in lifting_resolutions:
            if resolution.status != "resolved" or resolution.target_span is None:
                continue
            target = resolution.target_span
            lifting_release_evidence[resolution.signal_id] = EvidenceRef(
                evidence_id=f"evidence.{resolution.rule_id}.{resolution.signal_id}",
                role=EvidenceRole.SUPPORT,
                authority=StageAuthority(
                    stage_id=resolution.rule_id,
                    support=True,
                    challenge=True,
                    hold_release=True,
                ),
                source_ref=source_id,
                source_span=_source_span(source_id, text, target.start, target.end),
                summary=(
                    f"provider={resolution.provider_ref}; "
                    + "; ".join(resolution.reasons)
                ),
            )
    global_holds: list[Hold] = []
    holds_by_obligation: dict[str, list[Hold]] = {item.obligation_id: [] for item in profile.obligations}
    signal_evidence_by_obligation: dict[str, list[EvidenceRef]] = {
        item.obligation_id: [] for item in profile.obligations
    }
    signal_categories_by_obligation: dict[str, set[str]] = {
        item.obligation_id: set() for item in profile.obligations
    }
    reassessment_evidence_by_obligation: dict[str, list[EvidenceRef]] = {
        item.obligation_id: [] for item in profile.obligations
    }
    reassessment_by_obligation = {
        item.obligation_id: item for item in obligation_reassessments
    }

    for reassessment in obligation_reassessments:
        if reassessment.decision in {"preserved", "shadow_observation"}:
            continue
        if reassessment.is_promotion:
            role = EvidenceRole.SUPPORT
            authority = StageAuthority.assertion_capable(REASSESSMENT_POLICY_VERSION)
        elif reassessment.is_challenge:
            role = EvidenceRole.CHALLENGE
            authority = StageAuthority.policy_authority(REASSESSMENT_POLICY_VERSION)
        else:
            role = EvidenceRole.SIGNAL
            authority = StageAuthority.signal_only(REASSESSMENT_POLICY_VERSION)
        receipt_material = ",".join(reassessment.receipt_ids) or "none"
        qualification_material = ",".join(reassessment.qualification_ids) or "none"
        span_material: tuple[tuple[int, int] | None, ...] = (
            tuple(reassessment.evidence_spans)
            if reassessment.evidence_spans
            else (None,)
        )
        for index, span in enumerate(span_material, start=1):
            evidence = EvidenceRef(
                evidence_id=(
                    f"evidence.reassessment.{reassessment.obligation_id}."
                    f"{reassessment.decision}.{index}."
                    f"{hashlib.sha256((receipt_material + qualification_material).encode('utf-8')).hexdigest()[:16]}"
                ),
                role=role,
                authority=authority,
                source_ref=source_id,
                source_span=(
                    _source_span(source_id, text, *span) if span is not None else None
                ),
                summary=(
                    f"policy={reassessment.policy_rule_id}; "
                    f"decision={reassessment.decision}; "
                    f"receipts={receipt_material}; "
                    f"qualifications={qualification_material}; "
                    + "; ".join(reassessment.reasons)
                ),
            )
            reassessment_evidence_by_obligation[reassessment.obligation_id].append(
                evidence
            )

    for signal in signals:
        evidence = _signal_evidence(source_id, text, signal, authority=policy_authority)
        released_by = lifting_release_evidence.get(signal.signal_id)
        affected = _affected_obligations(signal)
        for obligation_id in affected:
            if obligation_id not in holds_by_obligation:
                continue
            signal_evidence_by_obligation[obligation_id].append(evidence)
            if released_by is not None:
                signal_evidence_by_obligation[obligation_id].append(released_by)
            else:
                signal_categories_by_obligation[obligation_id].add(signal.category)
            hold = Hold(
                hold_id=f"hold.{obligation_id}.{signal.signal_id}",
                scope=(obligation_id,),
                reason=signal.reason_code,
                applied_by=evidence,
                release_conditions=(
                    f"run:{signal.next_route}",
                    "apply an assertion-capable, source-aligned re-evaluation rule",
                    "preserve alternative interpretations and counterconditions",
                ),
                released_by=released_by,
            )
            holds_by_obligation[obligation_id].append(hold)
        if signal.field_name == "record":
            global_holds.append(
                Hold(
                    hold_id=f"hold.execution.{signal.signal_id}",
                    scope=("*",),
                    reason=signal.reason_code,
                    applied_by=evidence,
                    release_conditions=(
                        f"run:{signal.next_route}",
                        "close the input boundary with source-aligned evidence",
                    ),
                    released_by=released_by,
                )
            )

    conflict_obligations: set[str] = {
        item.obligation_id for item in obligation_reassessments if item.is_challenge
    }
    for obligation_id in conflict_obligations:
        evidence = reassessment_evidence_by_obligation[obligation_id][0]
        holds_by_obligation[obligation_id].append(
            Hold(
                hold_id=f"hold.{obligation_id}.reassessment-policy-conflict",
                scope=(obligation_id,),
                reason="reassessment_candidate_conflict",
                applied_by=evidence,
                release_conditions=(
                    "obtain a single qualified source-aligned dependency observation",
                    "resolve or preserve the competing subject/object interpretation",
                ),
            )
        )
    candidate_conflicts = _candidate_conflicts(candidate_pool, direct, profile, record)
    for obligation_id, candidates in candidate_conflicts.items():
        candidate = candidates[0]
        span = candidate.from_span
        source = next(
            (
                (stage, provider_id, provider_version)
                for item, stage, provider_id, provider_version in candidate_entries
                if item == candidate
            ),
            ("unknown", "unknown", "unknown"),
        )
        stage, provider_id, provider_version = source
        synthetic = ResidualRiskSignal(
            signal_id=f"signal.{stage}.relation-conflict.{obligation_id}.{span.start}",
            reason_code="candidate_relation_conflict",
            category="attachment",
            field_name="record",
            start=span.start,
            end=span.end,
            excerpt=text[span.start : span.end],
            detected_by=f"provider:{provider_id}:{provider_version}",
            next_route="assertion_capable_recomparison",
            limitations=(
                "A candidate relation disagrees with the direct assessment; neither candidate nor syntax projection can choose the adopted meaning.",
            ),
        )
        if analysis_mode == "shadow_all":
            shadow_signals.append(synthetic)
            continue
        conflict_obligations.add(obligation_id)
        signals.append(synthetic)
        evidence = _signal_evidence(source_id, text, synthetic, authority=policy_authority)
        signal_evidence_by_obligation[obligation_id].append(evidence)
        signal_categories_by_obligation[obligation_id].add("attachment")
        holds_by_obligation[obligation_id].append(
            Hold(
                hold_id=f"hold.{obligation_id}.{synthetic.signal_id}",
                scope=(obligation_id,),
                reason=synthetic.reason_code,
                applied_by=evidence,
                release_conditions=(
                    "assertion-capable source-aligned re-evaluation",
                    "resolve or preserve the competing interpretation",
                ),
            )
        )

    assessments = {item.obligation_id: item for item in direct}
    obligations: list[ObligationResult] = []
    for specification in profile.obligations:
        assessment = assessments[specification.obligation_id]
        reassessment = reassessment_by_obligation[specification.obligation_id]
        effective_outcome = reassessment.effective_outcome
        holds = tuple(holds_by_obligation[specification.obligation_id])
        open_holds = tuple(item for item in holds if item.is_open)
        categories = signal_categories_by_obligation[specification.obligation_id]
        required_checks = specification.required_guards
        completed_checks: list[str] = []
        for guard in required_checks:
            if guard == "record_boundary":
                if record.record_mode == "closed_record":
                    completed_checks.append(guard)
                continue
            if guard == "target_alignment":
                if effective_outcome in {"supported", "refuted", "not_applicable"}:
                    completed_checks.append(guard)
                continue
            if guard == "attachment":
                if "conditional_scope" not in categories and "attachment" not in categories:
                    completed_checks.append(guard)
                continue
            if guard not in {CATEGORY_GUARD.get(item) for item in categories}:
                completed_checks.append(guard)

        unknown_reasons = (
            []
            if reassessment.is_promotion
            else list(assessment.unknown_reasons)
        )
        if reassessment.decision in {"abstain", "challenged_by_policy"}:
            unknown_reasons.extend(reassessment.reasons)
        unknown_reasons.extend(hold.reason for hold in open_holds)
        missing_checks = [item for item in required_checks if item not in completed_checks]
        unknown_reasons.extend(f"guard_not_closed:{item}" for item in missing_checks)
        coverage_status = Coverage.COMPLETE if not missing_checks else Coverage.PARTIAL
        coverage = GuardCoverage(
            status=coverage_status,
            required_checks=required_checks,
            completed_checks=tuple(completed_checks),
            unresolved_reasons=tuple(dict.fromkeys(unknown_reasons)) if missing_checks else (),
        )

        outcome = {
            "supported": Outcome.SATISFIED,
            "refuted": Outcome.REFUTED,
            "unresolved": Outcome.UNDETERMINED,
            "not_applicable": Outcome.NOT_APPLICABLE,
            "invalid": Outcome.INVALID,
        }[effective_outcome]
        active = effective_outcome != "not_applicable"
        required = specification.necessity == "required"
        if outcome is Outcome.NOT_APPLICABLE and (
            open_holds or coverage_status is not Coverage.COMPLETE
        ):
            # Applicability itself is unresolved.  A provisional
            # not-applicable state would be contractually incoherent because
            # not-applicable is a terminal assertion, not an escape hatch.
            outcome = Outcome.UNDETERMINED
            active = True
        if outcome is Outcome.INVALID:
            finality = Finality.INVALID
        elif (
            outcome is Outcome.UNDETERMINED
            or open_holds
            or coverage_status is not Coverage.COMPLETE
        ):
            finality = Finality.PROVISIONAL
        else:
            finality = Finality.TERMINAL
        if specification.obligation_id in conflict_obligations:
            challenge = Challenge.CONFLICT
        elif open_holds or outcome is Outcome.UNDETERMINED:
            challenge = Challenge.OPEN
        else:
            challenge = Challenge.NONE

        provenance = (
            _direct_evidence(source_id, text, assessment)
            + tuple(reassessment_evidence_by_obligation[specification.obligation_id])
            + tuple(
            signal_evidence_by_obligation[specification.obligation_id]
            )
        )
        effective_evidence_spans = (
            reassessment.evidence_spans
            if reassessment.is_promotion
            else assessment.evidence_spans
        )
        source_spans = tuple(
            _source_span(source_id, text, start, end)
            for start, end in effective_evidence_spans
            if end > start
        )
        obligations.append(
            ObligationResult(
                obligation_id=specification.obligation_id,
                outcome=outcome,
                finality=finality,
                challenge=challenge,
                coverage=coverage,
                active=active,
                required=required if active else False,
                interpretations=tuple(
                    candidate.interpretation_id
                    for candidate in candidate_pool
                    if analysis_mode != "shadow_all"
                    if candidate.relation_kind == specification.relation_kind
                    and candidate.interpretation_id
                ),
                source_spans=source_spans,
                provenance=provenance,
                holds=holds,
                unknown_reasons=tuple(dict.fromkeys(unknown_reasons)),
                residual_risks=tuple(
                    limitation
                    for signal in signals
                    if specification.obligation_id in _affected_obligations(signal)
                    for limitation in signal.limitations
                ),
            )
        )

    execution_required = (
        "record_segmentation",
        "profile_applicability",
        "direct_obligation_projection",
        "residual_risk_gate",
        "provider_accounting",
    )
    execution_completed = [
        "record_segmentation",
        "direct_obligation_projection",
        "residual_risk_gate",
    ]
    if applicability == "applicable":
        execution_completed.append("profile_applicability")
    if not required_stage_failures:
        execution_completed.append("provider_accounting")
    execution_coverage_status = (
        Coverage.COMPLETE
        if len(execution_completed) == len(execution_required)
        else Coverage.PARTIAL
    )
    execution = AuditExecution(
        execution_id=f"execution.{source_id.split(':', 1)[1][:16]}",
        coverage=GuardCoverage(
            status=execution_coverage_status,
            required_checks=execution_required,
            completed_checks=tuple(execution_completed),
            unresolved_reasons=tuple(
                ["profile_applicability_unknown"] if applicability != "applicable" else []
            )
            + tuple(f"required_provider_stage:{item}" for item in required_stage_failures),
        ),
        holds=tuple(global_holds),
        provider_failures=tuple(required_stage_failures),
        integrity_failures=(),
    )

    decision_requests: list[DecisionRequest] = []
    for obligation in obligations:
        if obligation.finality is Finality.TERMINAL and obligation.challenge is Challenge.NONE:
            continue
        detected_by = tuple(
            item for item in obligation.provenance if item.role in {EvidenceRole.CHALLENGE, EvidenceRole.SIGNAL}
        ) or obligation.provenance[:1]
        reasons = tuple(dict.fromkeys(obligation.unknown_reasons))
        human_semantics = any(
            marker in reason
            for reason in reasons
            for marker in ("non_adoption", "reported_speech", "metalinguistic", "modal")
        )
        required_authority = (
            "requirement_owner_interpretation" if human_semantics else "evidence_or_technical_interpretation"
        )
        decision_requests.append(
            DecisionRequest(
                request_id=f"decision.{obligation.obligation_id}.{source_id[-12:]}",
                subject_ref=f"{source_id}#{obligation.obligation_id}",
                issue_class="semantic_conflict" if obligation.challenge is Challenge.CONFLICT else "audit_unresolved",
                epistemic_state="conflict" if obligation.challenge is Challenge.CONFLICT else "unresolved",
                detected_by=detected_by,
                required_authority=required_authority,
                affected_obligation_ids=(obligation.obligation_id,),
                resolution_conditions=(
                    "provide source-aligned evidence or an authority-bounded interpretation",
                    "rerun the audit under the same or explicitly revised profile",
                    "do not erase alternative interpretations or residual risk",
                ),
                agent_work_candidates=(
                    "inspect the source record and referenced artifacts",
                    "run configured morphology and dependency analysis",
                    "re-audit after evidence is added",
                ),
                question_material=reasons,
            )
        )

    result = aggregate_audit_result(
        execution=execution,
        obligations=tuple(obligations),
        decision_requests=tuple(decision_requests),
        residual_risks=tuple(
            dict.fromkeys(
                limitation
                for signal in signals
                for limitation in signal.limitations
            )
        ),
    )
    routed_unresolved_obligations = build_unresolved_obligations(
        source_id=source_id,
        profile=profile,
        direct_assessments=direct,
        residual_signals=tuple(routing_signals),
    )
    closed_obligation_ids = {
        item.obligation_id
        for item in result.obligations
        if item.finality is Finality.TERMINAL and item.challenge is Challenge.NONE
    }
    remaining_unresolved_obligations = tuple(
        item
        for item in routed_unresolved_obligations
        if item.obligation_id not in closed_obligation_ids
    )
    return RequirementAuditReport(
        source_id=source_id,
        profile_id=profile.profile_id,
        profile_version=profile.version,
        applicability=applicability,
        record=record,
        direct_assessments=direct,
        residual_signals=tuple(signals),
        shadow_signals=tuple(shadow_signals),
        analysis_attempts=tuple(attempts),
        provider_execution_receipts=tuple(receipts),
        dependency_projections=dependency_projections,
        obligation_reassessments=obligation_reassessments,
        analyzer_qualifications=analyzer_qualifications,
        lifting_resolutions=tuple(lifting_resolutions),
        initial_unresolved_obligations=initial_unresolved,
        remaining_unresolved_obligations=remaining_unresolved_obligations,
        unresolved_obligations=remaining_unresolved_obligations,
        stage_plans=tuple(stage_plans),
        result=result,
        analysis_mode=analysis_mode,
        limitations=(
            "The result is a bounded engineering audit under a versioned profile, not natural-language truth.",
            "Provider candidates cannot establish support or release holds.",
            "Only obligation-reassessment-policy/v0 may promote originally unresolved performs/acts_on relations, and only from exact qualified receipt-bound dependency material.",
            "Dependency-to-semantic projection v0 covers only subject/performs, object/acts_on, and attached condition/triggered_by candidates.",
            "Workflow pass is not human acceptance or proof of action occurrence.",
        ),
    )
