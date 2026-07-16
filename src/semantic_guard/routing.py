from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from typing import Any, Literal

from .direct_rules import DirectRelationAssessment
from .profiles import FUNCTIONAL_REQUIREMENT_PROFILE, NormativeProfile
from .providers import AnalysisAttempt, AnalysisSpan, ProviderStage
from .residual_risk import ResidualRiskSignal


ROUTING_CONTRACT_VERSION = "semantic-guard-unresolved-routing/v0"
DIRECT_UNKNOWN_ROUTE_POLICY_VERSION = "direct-unknown-route-policy/v0"

MORPHOLOGY_CAPABILITIES = ("tokenization", "lemma", "part_of_speech")
DEPENDENCY_CAPABILITIES = (
    "dependency",
    "scope",
    "predicate_argument",
    "polarity_scope",
    "modality_scope",
    "coordination",
    "coreference_candidate",
)
LLM_CAPABILITIES = (
    "interpretation_candidates",
    "countercondition_candidates",
)

# Capability requests are reason driven in conditional mode.  Unknown reason
# codes deliberately fall back to the complete stage capability set: a newly
# introduced reason must not silently under-request analysis.  Assurance and
# shadow-all modes always request the full set because their denominator is the
# whole declared profile rather than one known gap.
_DEPENDENCY_REASON_CAPABILITIES: dict[str, tuple[str, ...]] = {
    "scenario_actor_role_not_assertion_capable": (
        "dependency",
        "predicate_argument",
        "coordination",
    ),
    "scenario_actor_active_predicate_not_established": (
        "dependency",
        "predicate_argument",
        "coordination",
    ),
    "scenario_actor_voice_not_agentive": (
        "dependency",
        "predicate_argument",
        "scope",
        "coordination",
    ),
    "scenario_actor_passive_or_nominal_clause": (
        "dependency",
        "predicate_argument",
        "scope",
        "coordination",
    ),
    "scenario_actor_causative_or_reported_clause": (
        "dependency",
        "predicate_argument",
        "scope",
        "coordination",
    ),
    "object_applicability_not_established": (
        "dependency",
        "predicate_argument",
        "coordination",
    ),
    "conditional_or_exception_scope_present": (
        "dependency",
        "scope",
        "predicate_argument",
        "coordination",
    ),
    "multiple_propositions_present": (
        "dependency",
        "scope",
        "predicate_argument",
        "coordination",
    ),
    "negation_scope_present": (
        "dependency",
        "scope",
        "polarity_scope",
    ),
    "morphology_negation_candidate": (
        "dependency",
        "scope",
        "polarity_scope",
    ),
    "modal_uncertainty_present": (
        "dependency",
        "scope",
        "modality_scope",
    ),
    "non_adoption_or_proposal_present": (
        "dependency",
        "scope",
        "modality_scope",
    ),
    "reported_speech_present": (
        "dependency",
        "scope",
        "predicate_argument",
    ),
    "metalinguistic_or_quotation_present": (
        "dependency",
        "scope",
        "predicate_argument",
    ),
    "candidate_relation_conflict": (
        "dependency",
        "predicate_argument",
        "coordination",
    ),
}

_LLM_REASON_CAPABILITIES: dict[str, tuple[str, ...]] = {
    "llm_countercondition_candidate": ("countercondition_candidates",),
    "conditional_or_exception_scope_present": ("countercondition_candidates",),
    "llm_alternative_scope_candidate": ("interpretation_candidates",),
    "candidate_relation_conflict": ("interpretation_candidates",),
    "shared_dimension_is_candidate_not_relation_proof": (
        "interpretation_candidates",
    ),
    "no_assertion_capable_target_alignment": ("interpretation_candidates",),
}

RouteDecision = Literal["run", "skipped_not_needed"]
StageObservation = Literal[
    "skipped_not_needed",
    "not_configured",
    "attempted_ok",
    "attempted_partial",
    "attempted_failed",
]
StageAvailability = Literal[
    "not_needed",
    "not_configured",
    "available",
    "unavailable",
]


FIELD_OBLIGATIONS: dict[str, frozenset[str]] = {
    "purpose": frozenset({"func.applies_to", "func.verified_by"}),
    "user": frozenset({"func.applies_to", "func.performs"}),
    "scenario": frozenset(
        {"func.performs", "func.acts_on", "func.triggered_by", "func.produces"}
    ),
    "expected_result": frozenset({"func.produces", "func.constrained_by"}),
    "acceptance_criteria": frozenset(
        {"func.constrained_by", "func.uses_metric", "func.verifies", "func.measures"}
    ),
    "verification_method": frozenset(
        {
            "func.verified_by",
            "func.verifies",
            "func.measures",
            "func.produces_evidence",
        }
    ),
    "evidence": frozenset({"func.produces_evidence"}),
    "record": frozenset(
        item.obligation_id for item in FUNCTIONAL_REQUIREMENT_PROFILE.obligations
    ),
}


def affected_obligation_ids(signal: ResidualRiskSignal) -> frozenset[str]:
    """Return the bounded obligation family challenged by a residual signal."""

    return FIELD_OBLIGATIONS.get(signal.field_name, FIELD_OBLIGATIONS["record"])


def capabilities_for_stage(
    stage: ProviderStage,
    reason_codes: tuple[str, ...] = (),
    *,
    full_coverage: bool = False,
) -> tuple[str, ...]:
    """Return the bounded capabilities justified by the current route.

    Morphology's three outputs form one indivisible lexical observation.  For
    dependency and LLM stages, every known reason contributes a smaller
    capability family.  One unknown reason closes the optimization and
    requests the full stage set so capability accounting cannot reduce recall
    merely because the reason vocabulary changed.
    """

    complete = {
        "morphology": MORPHOLOGY_CAPABILITIES,
        "dependency_parse": DEPENDENCY_CAPABILITIES,
        "llm_candidate": LLM_CAPABILITIES,
    }[stage]
    reasons = tuple(dict.fromkeys(reason_codes))
    if full_coverage or not reasons or stage == "morphology":
        return complete

    mapping = (
        _DEPENDENCY_REASON_CAPABILITIES
        if stage == "dependency_parse"
        else _LLM_REASON_CAPABILITIES
    )
    if any(reason not in mapping for reason in reasons):
        return complete
    required = {
        capability
        for reason in reasons
        for capability in mapping[reason]
    }
    return tuple(capability for capability in complete if capability in required)


def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


def _canonical_id(prefix: str, payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"{prefix}." + hashlib.sha256(encoded).hexdigest()[:24]


def _rule_version(rule_id: str) -> str:
    _, separator, version = rule_id.rpartition("/")
    return version if separator and version else "unversioned"


def _span_dict(span: AnalysisSpan) -> dict[str, Any]:
    return {"start": span.start, "end": span.end, "role": span.role}


@dataclass(frozen=True, slots=True)
class UnresolvedObligation:
    """Versioned route material for one obligation needing further analysis.

    An entry can be created because the direct assessment is unresolved or
    because a residual signal keeps one of the obligation guards open.  It is
    routing evidence only and cannot reclassify the direct assessment.
    """

    source_id: str
    profile_id: str
    profile_version: str
    obligation_id: str
    relation_kind: str | None
    direct_rule_id: str
    direct_rule_version: str
    direct_outcome: str
    direct_reasons: tuple[str, ...]
    direct_unknown_reasons: tuple[str, ...]
    required_guards: tuple[str, ...]
    signal_ids: tuple[str, ...]
    reason_routes: tuple[tuple[str, str], ...]
    target_spans: tuple[AnalysisSpan, ...]
    unresolved_id: str = field(init=False)
    schema_version: str = field(
        init=False,
        default=ROUTING_CONTRACT_VERSION,
    )

    def __post_init__(self) -> None:
        for name in (
            "source_id",
            "profile_id",
            "profile_version",
            "obligation_id",
            "direct_rule_id",
            "direct_rule_version",
            "direct_outcome",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")
        if self.relation_kind is not None and not self.relation_kind.strip():
            raise ValueError("relation_kind must be non-empty when supplied")

        object.__setattr__(self, "direct_reasons", _dedupe(tuple(self.direct_reasons)))
        object.__setattr__(
            self,
            "direct_unknown_reasons",
            _dedupe(tuple(self.direct_unknown_reasons)),
        )
        object.__setattr__(self, "required_guards", _dedupe(tuple(self.required_guards)))
        object.__setattr__(self, "signal_ids", tuple(sorted(set(self.signal_ids))))

        reason_routes = tuple(sorted(set(tuple(item) for item in self.reason_routes)))
        if any(
            len(item) != 2 or not item[0].strip() or not item[1].strip()
            for item in reason_routes
        ):
            raise ValueError("reason_routes must contain non-empty reason/route pairs")
        object.__setattr__(self, "reason_routes", reason_routes)

        spans = tuple(
            sorted(
                set(self.target_spans),
                key=lambda item: (item.start, item.end, item.role),
            )
        )
        if any(not isinstance(item, AnalysisSpan) for item in spans):
            raise TypeError("target_spans must contain AnalysisSpan values")
        object.__setattr__(self, "target_spans", spans)

        object.__setattr__(
            self,
            "unresolved_id",
            _canonical_id(
                "unresolved-obligation",
                {
                    "schema_version": self.schema_version,
                    "source_id": self.source_id,
                    "profile_id": self.profile_id,
                    "profile_version": self.profile_version,
                    "obligation_id": self.obligation_id,
                    "relation_kind": self.relation_kind,
                },
            ),
        )

    @property
    def reason_codes(self) -> tuple[str, ...]:
        return tuple(reason for reason, _ in self.reason_routes)

    @property
    def requested_routes(self) -> tuple[str, ...]:
        return tuple(sorted({route for _, route in self.reason_routes}))

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "unresolved_id": self.unresolved_id,
            "source_id": self.source_id,
            "profile_id": self.profile_id,
            "profile_version": self.profile_version,
            "obligation_id": self.obligation_id,
            "relation_kind": self.relation_kind,
            "direct_rule_id": self.direct_rule_id,
            "direct_rule_version": self.direct_rule_version,
            "direct_outcome": self.direct_outcome,
            "direct_reasons": list(self.direct_reasons),
            "direct_unknown_reasons": list(self.direct_unknown_reasons),
            "required_guards": list(self.required_guards),
            "signal_ids": list(self.signal_ids),
            "reason_routing": [
                {"reason_code": reason, "requested_route": route}
                for reason, route in self.reason_routes
            ],
            "target_spans": [_span_dict(span) for span in self.target_spans],
        }


@dataclass(frozen=True, slots=True)
class StagePlan:
    """Immutable plan plus its non-authoritative execution observation."""

    source_id: str
    profile_id: str
    profile_version: str
    stage: ProviderStage
    route_decision: RouteDecision
    run_causes: tuple[str, ...]
    driver_unresolved_ids: tuple[str, ...]
    driver_obligation_ids: tuple[str, ...]
    driver_relation_kinds: tuple[str, ...]
    reason_routes: tuple[tuple[str, str], ...]
    required_guards: tuple[str, ...]
    required_capabilities: tuple[str, ...]
    target_obligation_ids: tuple[str, ...]
    target_relation_kinds: tuple[str, ...]
    target_spans: tuple[AnalysisSpan, ...]
    provider_configured: bool
    execution_state: StageObservation
    availability: StageAvailability
    attempt_status: str | None = None
    provider_id: str | None = None
    provider_version: str | None = None
    resource_version: str | None = None
    diagnostics: tuple[str, ...] = ()
    stage_plan_id: str = field(init=False)
    schema_version: str = field(
        init=False,
        default=ROUTING_CONTRACT_VERSION,
    )

    def __post_init__(self) -> None:
        if self.stage not in {"morphology", "dependency_parse", "llm_candidate"}:
            raise ValueError(f"unsupported stage: {self.stage}")
        if self.route_decision not in {"run", "skipped_not_needed"}:
            raise ValueError(f"unsupported route decision: {self.route_decision}")
        if not self.run_causes:
            raise ValueError("a stage plan must state at least one run or skip cause")

        for name in (
            "run_causes",
            "driver_unresolved_ids",
            "driver_obligation_ids",
            "driver_relation_kinds",
            "required_guards",
            "required_capabilities",
            "target_obligation_ids",
            "target_relation_kinds",
            "diagnostics",
        ):
            values = _dedupe(tuple(getattr(self, name)))
            if any(not isinstance(item, str) or not item.strip() for item in values):
                raise ValueError(f"{name} must contain non-empty strings")
            object.__setattr__(self, name, values)

        reason_routes = tuple(sorted(set(tuple(item) for item in self.reason_routes)))
        if any(
            len(item) != 2 or not item[0].strip() or not item[1].strip()
            for item in reason_routes
        ):
            raise ValueError("reason_routes must contain non-empty reason/route pairs")
        object.__setattr__(self, "reason_routes", reason_routes)

        spans = tuple(
            sorted(
                set(self.target_spans),
                key=lambda item: (item.start, item.end, item.role),
            )
        )
        if any(not isinstance(item, AnalysisSpan) for item in spans):
            raise TypeError("target_spans must contain AnalysisSpan values")
        object.__setattr__(self, "target_spans", spans)

        if self.route_decision == "skipped_not_needed":
            if self.execution_state != "skipped_not_needed":
                raise ValueError("a skipped plan must have skipped_not_needed state")
            if self.availability != "not_needed" or self.attempt_status is not None:
                raise ValueError("a skipped plan cannot carry an attempt observation")
        elif self.execution_state == "skipped_not_needed":
            raise ValueError("a run decision cannot have a skipped observation")

        expected_availability = {
            "skipped_not_needed": "not_needed",
            "not_configured": "not_configured",
            "attempted_ok": "available",
            "attempted_partial": "available",
            "attempted_failed": "unavailable",
        }[self.execution_state]
        if self.availability != expected_availability:
            raise ValueError("availability does not match the execution state")

        expected_attempt = {
            "skipped_not_needed": None,
            "not_configured": "not_configured",
            "attempted_ok": "ok",
            "attempted_partial": "partial",
            "attempted_failed": "failed",
        }[self.execution_state]
        if self.attempt_status != expected_attempt:
            raise ValueError("attempt_status does not match the execution state")

        object.__setattr__(
            self,
            "stage_plan_id",
            _canonical_id(
                "stage-plan",
                {
                    "schema_version": self.schema_version,
                    "source_id": self.source_id,
                    "profile_id": self.profile_id,
                    "profile_version": self.profile_version,
                    "stage": self.stage,
                    "route_decision": self.route_decision,
                    "run_causes": self.run_causes,
                    "driver_unresolved_ids": self.driver_unresolved_ids,
                    "reason_routes": self.reason_routes,
                    "required_capabilities": self.required_capabilities,
                    "target_obligation_ids": self.target_obligation_ids,
                    "target_spans": tuple(
                        (span.start, span.end, span.role) for span in self.target_spans
                    ),
                },
            ),
        )

    @property
    def reason_codes(self) -> tuple[str, ...]:
        return tuple(reason for reason, _ in self.reason_routes)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "stage_plan_id": self.stage_plan_id,
            "source_id": self.source_id,
            "profile_id": self.profile_id,
            "profile_version": self.profile_version,
            "stage": self.stage,
            "route_decision": self.route_decision,
            "run_causes": list(self.run_causes),
            "driver_unresolved_ids": list(self.driver_unresolved_ids),
            "driver_obligation_ids": list(self.driver_obligation_ids),
            "driver_relation_kinds": list(self.driver_relation_kinds),
            "reason_routing": [
                {
                    "reason_code": reason,
                    "requested_route": route,
                    "planned_stage": self.stage,
                }
                for reason, route in self.reason_routes
            ],
            "required_guards": list(self.required_guards),
            "required_capabilities": list(self.required_capabilities),
            "target_denominator": {
                "obligation_count": len(self.target_obligation_ids),
                "obligation_ids": list(self.target_obligation_ids),
                "relation_kinds": list(self.target_relation_kinds),
                "span_count": len(self.target_spans),
                "spans": [_span_dict(span) for span in self.target_spans],
            },
            "execution_observation": {
                "state": self.execution_state,
                "availability": self.availability,
                "provider_configured": self.provider_configured,
                "attempt_status": self.attempt_status,
                "provider_id": self.provider_id,
                "provider_version": self.provider_version,
                "resource_version": self.resource_version,
                "diagnostics": list(self.diagnostics),
            },
        }


def build_unresolved_obligations(
    *,
    source_id: str,
    profile: NormativeProfile,
    direct_assessments: tuple[DirectRelationAssessment, ...],
    residual_signals: tuple[ResidualRiskSignal, ...],
) -> tuple[UnresolvedObligation, ...]:
    """Project direct unknowns and residual signals into route material."""

    assessments = {item.obligation_id: item for item in direct_assessments}
    results: list[UnresolvedObligation] = []
    for specification in profile.obligations:
        assessment = assessments[specification.obligation_id]
        relevant_signals = tuple(
            signal
            for signal in residual_signals
            if specification.obligation_id in affected_obligation_ids(signal)
        )
        if assessment.outcome != "unresolved" and not relevant_signals:
            continue

        reason_routes = [
            (reason, "dependency_parse")
            for reason in assessment.unknown_reasons
        ]
        reason_routes.extend(
            (signal.reason_code, signal.next_route) for signal in relevant_signals
        )
        if assessment.outcome == "unresolved" and not reason_routes:
            reason_routes.append(("direct_outcome_unresolved", "dependency_parse"))

        spans = [
            AnalysisSpan(start, end, specification.obligation_id)
            for start, end in assessment.evidence_spans
            if end > start
        ]
        spans.extend(
            AnalysisSpan(signal.start, signal.end, signal.field_name)
            for signal in relevant_signals
            if signal.end > signal.start
        )
        results.append(
            UnresolvedObligation(
                source_id=source_id,
                profile_id=profile.profile_id,
                profile_version=profile.version,
                obligation_id=specification.obligation_id,
                relation_kind=specification.relation_kind or None,
                direct_rule_id=assessment.rule_id,
                direct_rule_version=_rule_version(assessment.rule_id),
                direct_outcome=assessment.outcome,
                direct_reasons=tuple((*assessment.basis, *assessment.unknown_reasons)),
                direct_unknown_reasons=assessment.unknown_reasons,
                required_guards=specification.required_guards,
                signal_ids=tuple(signal.signal_id for signal in relevant_signals),
                reason_routes=tuple(reason_routes),
                target_spans=tuple(spans),
            )
        )
    return tuple(results)


def reason_codes_for(
    unresolved: tuple[UnresolvedObligation, ...],
) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                reason
                for obligation in unresolved
                for reason, _ in obligation.reason_routes
            }
        )
    )


def make_stage_plan(
    *,
    source_id: str,
    profile: NormativeProfile,
    stage: ProviderStage,
    route_decision: RouteDecision,
    run_causes: tuple[str, ...],
    drivers: tuple[UnresolvedObligation, ...],
    target_obligation_ids: tuple[str, ...],
    target_spans: tuple[AnalysisSpan, ...],
    provider_configured: bool,
    attempt: AnalysisAttempt | None = None,
    required_capabilities: tuple[str, ...] | None = None,
) -> StagePlan:
    specifications = {item.obligation_id: item for item in profile.obligations}
    target_ids = tuple(dict.fromkeys(target_obligation_ids))
    unknown_targets = set(target_ids) - set(specifications)
    if unknown_targets:
        raise ValueError(
            "target obligations are outside the profile: "
            + ", ".join(sorted(unknown_targets))
        )

    if route_decision == "skipped_not_needed":
        if attempt is not None:
            raise ValueError("a skipped stage cannot carry an analysis attempt")
        execution_state: StageObservation = "skipped_not_needed"
        availability: StageAvailability = "not_needed"
        attempt_status = None
    elif attempt is None:
        if provider_configured:
            raise ValueError("a configured run must carry its analysis attempt")
        execution_state = "not_configured"
        availability = "not_configured"
        attempt_status = "not_configured"
    else:
        if attempt.stage != stage:
            raise ValueError("analysis attempt stage does not match the stage plan")
        execution_state = {
            "ok": "attempted_ok",
            "partial": "attempted_partial",
            "failed": "attempted_failed",
            "not_configured": "not_configured",
        }[attempt.status]
        availability = {
            "ok": "available",
            "partial": "available",
            "failed": "unavailable",
            "not_configured": "not_configured",
        }[attempt.status]
        attempt_status = attempt.status

    reason_routes = tuple(
        sorted(
            {
                pair
                for obligation in drivers
                for pair in obligation.reason_routes
            }
        )
    )
    guards = tuple(
        dict.fromkeys(
            guard
            for obligation_id in target_ids
            for guard in specifications[obligation_id].required_guards
        )
    )
    return StagePlan(
        source_id=source_id,
        profile_id=profile.profile_id,
        profile_version=profile.version,
        stage=stage,
        route_decision=route_decision,
        run_causes=run_causes,
        driver_unresolved_ids=tuple(item.unresolved_id for item in drivers),
        driver_obligation_ids=tuple(
            dict.fromkeys(item.obligation_id for item in drivers)
        ),
        driver_relation_kinds=tuple(
            dict.fromkeys(
                item.relation_kind
                for item in drivers
                if item.relation_kind is not None
            )
        ),
        reason_routes=reason_routes,
        required_guards=guards,
        required_capabilities=(
            required_capabilities
            if required_capabilities is not None
            else capabilities_for_stage(stage, reason_codes_for(drivers))
        ),
        target_obligation_ids=target_ids,
        target_relation_kinds=tuple(
            specifications[item].relation_kind for item in target_ids
        ),
        target_spans=target_spans,
        provider_configured=provider_configured,
        execution_state=execution_state,
        availability=availability,
        attempt_status=attempt_status,
        provider_id=(attempt.provider_id if attempt is not None else "not-configured")
        if route_decision == "run"
        else None,
        provider_version=attempt.provider_version if attempt is not None else None,
        resource_version=attempt.resource_version if attempt is not None else None,
        diagnostics=attempt.diagnostics if attempt is not None else (),
    )
