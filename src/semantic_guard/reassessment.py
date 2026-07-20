from __future__ import annotations

from dataclasses import dataclass, field
import re
import unicodedata
from typing import Literal

from .dependency_projection import DependencyRelationProjection
from .direct_rules import DirectRelationAssessment
from .provider_receipts import (
    AnalyzerQualification,
    ProviderExecutionReceipt,
    QualifiedAnalyzerRegistry,
    attempt_output_digest,
    canonical_digest,
    source_digest,
)
from .providers import AnalysisAttempt, AnalysisSpan
from .records import ParsedRequirementRecord
from .residual_risk import ResidualRiskSignal
from .routing import UnresolvedObligation


REASSESSMENT_POLICY_VERSION = "obligation-reassessment-policy/v0"
SUPPORTED_OBLIGATIONS = frozenset({"func.performs", "func.acts_on"})
REQUIRED_CAPABILITIES = ("coordination", "dependency", "predicate_argument")
DIRECT_REASON_ALLOWLIST: dict[str, tuple[str, ...]] = {
    "func.performs": ("scenario_actor_role_not_assertion_capable",),
    "func.acts_on": ("object_applicability_not_established",),
}

_SOURCE_VOICE_BARRIER = re.compile(
    r"(?:され(?:る|た|て|ない|ます)?|させ(?:られ)?(?:る|た|て|ない|ます)?|"
    r"られ(?:る|た|て|ない|ます)?)"
    r"|\b(?:is|are|was|were|be|been|being)\s+[A-Za-z]+(?:ed|en)\b"
    r"|\b(?:causes?|makes?)\s+",
    re.IGNORECASE,
)

ReassessmentDecision = Literal[
    "preserved",
    "supported",
    "abstain",
    "challenged_by_policy",
    "shadow_observation",
]


def policy_scope(obligation_id: str) -> str:
    return f"{REASSESSMENT_POLICY_VERSION}:{obligation_id}"


@dataclass(frozen=True, slots=True)
class ObligationReassessment:
    source_id: str
    profile_id: str
    profile_version: str
    obligation_id: str
    unresolved_id: str | None
    unresolved_digest: str | None
    prior_assessment_digest: str
    original_rule_id: str
    original_outcome: str
    decision: ReassessmentDecision
    effective_outcome: str
    policy_rule_id: str
    receipt_ids: tuple[str, ...]
    qualification_ids: tuple[str, ...]
    projection_ids: tuple[str, ...]
    evidence_spans: tuple[tuple[int, int], ...]
    reasons: tuple[str, ...]
    reassessment_id: str = field(init=False)

    def __post_init__(self) -> None:
        if self.original_outcome == "unresolved" and (
            not self.unresolved_id or not self.unresolved_digest
        ):
            raise ValueError(
                "an unresolved reassessment must bind an initial unresolved_id and digest"
            )
        material = {
            "source_id": self.source_id,
            "profile_id": self.profile_id,
            "profile_version": self.profile_version,
            "obligation_id": self.obligation_id,
            "unresolved_id": self.unresolved_id,
            "unresolved_digest": self.unresolved_digest,
            "prior_assessment_digest": self.prior_assessment_digest,
            "original_rule_id": self.original_rule_id,
            "original_outcome": self.original_outcome,
            "decision": self.decision,
            "effective_outcome": self.effective_outcome,
            "policy_rule_id": self.policy_rule_id,
            "receipt_ids": self.receipt_ids,
            "qualification_ids": self.qualification_ids,
            "projection_ids": self.projection_ids,
            "evidence_spans": self.evidence_spans,
            "reasons": self.reasons,
        }
        object.__setattr__(
            self,
            "reassessment_id",
            "reassessment." + canonical_digest(material)[7:],
        )

    @property
    def is_promotion(self) -> bool:
        return self.decision == "supported" and self.effective_outcome == "supported"

    @property
    def is_challenge(self) -> bool:
        return self.decision == "challenged_by_policy"

    def as_dict(self) -> dict[str, object]:
        return {
            "reassessment_id": self.reassessment_id,
            "source_id": self.source_id,
            "profile_id": self.profile_id,
            "profile_version": self.profile_version,
            "obligation_id": self.obligation_id,
            "unresolved_id": self.unresolved_id,
            "unresolved_digest": self.unresolved_digest,
            "prior_assessment_digest": self.prior_assessment_digest,
            "original_rule_id": self.original_rule_id,
            "original_outcome": self.original_outcome,
            "decision": self.decision,
            "effective_outcome": self.effective_outcome,
            "policy_rule_id": self.policy_rule_id,
            "receipt_ids": list(self.receipt_ids),
            "qualification_ids": list(self.qualification_ids),
            "projection_ids": list(self.projection_ids),
            "evidence_spans": [
                {"start": start, "end": end} for start, end in self.evidence_spans
            ],
            "reasons": list(self.reasons),
            "route_status": (
                "resolved_by_reassessment"
                if self.is_promotion
                else (
                    "shadow_observation"
                    if self.decision == "shadow_observation"
                    else (
                        "remaining_unresolved"
                        if self.unresolved_id is not None
                        else "not_routed"
                    )
                )
            ),
            "resolved_by": self.policy_rule_id if self.is_promotion else None,
        }


@dataclass(frozen=True, slots=True)
class _TraceBinding:
    source_id: str
    profile_id: str
    profile_version: str
    unresolved_id: str | None
    unresolved_digest: str | None
    prior_assessment_digest: str


def _normalized(value: str) -> str:
    # Identity matching is deliberately narrower than search normalization.
    # Compatibility folding and internal-whitespace deletion can collapse two
    # differently declared actors and create a false satisfaction.
    return unicodedata.normalize("NFC", value).strip().casefold()


def _covered(start: int, end: int, spans: tuple[AnalysisSpan, ...]) -> bool:
    intervals = sorted(
        (max(start, span.start), min(end, span.end))
        for span in spans
        if span.start < end and start < span.end
    )
    cursor = start
    for left, right in intervals:
        if left > cursor:
            return False
        cursor = max(cursor, right)
        if cursor >= end:
            return True
    return cursor >= end


def _barrier_reasons(
    attempt: AnalysisAttempt,
    signals: tuple[ResidualRiskSignal, ...],
    record: ParsedRequirementRecord,
) -> tuple[str, ...]:
    reasons: list[str] = []
    scenario = record.one("scenario")
    if scenario is not None and _SOURCE_VOICE_BARRIER.search(scenario.value):
        reasons.append("source_voice_or_causative_not_excluded")
    blocking_signal_markers = (
        "reported_speech",
        "quotation",
        "non_adoption",
        "negation",
        "modal",
        "multiple_propositions",
    )
    for signal in signals:
        if signal.field_name not in {"scenario", "record"}:
            continue
        if any(marker in signal.reason_code for marker in blocking_signal_markers):
            reasons.append(f"unresolved_signal:{signal.reason_code}")

    for relation in attempt.relations:
        label = relation.relation_kind.casefold()
        if any(
            marker in label
            for marker in (
                "nsubj:pass",
                "aux:pass",
                "passive",
                "caus",
                "dependency:conj",
                "dependency:cc",
            )
        ):
            reasons.append(f"unresolved_dependency:{relation.relation_kind}")
    for scope in attempt.scopes:
        if scope.scope_kind.casefold() in {
            "negation",
            "modality",
            "quotation",
            "reporting",
            "coordination",
        }:
            reasons.append(f"unresolved_scope:{scope.scope_kind}")
    for token in attempt.tokens:
        material = " ".join(
            (
                token.surface,
                token.lemma,
                token.normalized,
                *token.part_of_speech,
                *(f"{key}={value}" for key, value in token.features.items()),
            )
        ).casefold()
        if "voice=pass" in material or "passive" in material:
            reasons.append("unresolved_token_voice:passive")
        if "voice=caus" in material or "causative" in material:
            reasons.append("unresolved_token_voice:causative")
    return tuple(dict.fromkeys(reasons))


def _attempt_for_receipt(
    receipt: ProviderExecutionReceipt,
    attempts: tuple[AnalysisAttempt, ...],
) -> AnalysisAttempt | None:
    matches = tuple(
        attempt
        for attempt in attempts
        if attempt.stage == receipt.stage
        and attempt.provider_id == receipt.provider_id
        and attempt.provider_version == receipt.provider_version
        and attempt.resource_version == receipt.resource_version
        and attempt.status == receipt.status
        and attempt_output_digest(attempt) == receipt.output_digest
    )
    return matches[0] if len(matches) == 1 else None


def _base(
    assessment: DirectRelationAssessment,
    *,
    binding: _TraceBinding,
    decision: ReassessmentDecision,
    effective_outcome: str | None = None,
    receipts: tuple[ProviderExecutionReceipt, ...] = (),
    qualification: AnalyzerQualification | None = None,
    projections: tuple[DependencyRelationProjection, ...] = (),
    evidence_spans: tuple[tuple[int, int], ...] = (),
    reasons: tuple[str, ...] = (),
) -> ObligationReassessment:
    return ObligationReassessment(
        source_id=binding.source_id,
        profile_id=binding.profile_id,
        profile_version=binding.profile_version,
        obligation_id=assessment.obligation_id,
        unresolved_id=binding.unresolved_id,
        unresolved_digest=binding.unresolved_digest,
        prior_assessment_digest=binding.prior_assessment_digest,
        original_rule_id=assessment.rule_id,
        original_outcome=assessment.outcome,
        decision=decision,
        effective_outcome=effective_outcome or assessment.outcome,
        policy_rule_id=REASSESSMENT_POLICY_VERSION,
        receipt_ids=tuple(item.receipt_id for item in receipts),
        qualification_ids=(qualification.qualification_id,) if qualification else (),
        projection_ids=tuple(item.projection_id for item in projections),
        evidence_spans=evidence_spans,
        reasons=reasons,
    )


def _candidate_material(
    assessment: DirectRelationAssessment,
    *,
    record: ParsedRequirementRecord,
    projections: tuple[DependencyRelationProjection, ...],
    receipts: tuple[ProviderExecutionReceipt, ...],
    attempts: tuple[AnalysisAttempt, ...],
    registry: QualifiedAnalyzerRegistry,
    signals: tuple[ResidualRiskSignal, ...],
) -> tuple[
    tuple[DependencyRelationProjection, ...],
    ProviderExecutionReceipt | None,
    AnalysisAttempt | None,
    AnalyzerQualification | None,
    tuple[str, ...],
    bool,
]:
    relevant = tuple(
        item
        for item in projections
        if item.candidate.relation_kind in {"performs", "acts_on"}
    )
    if not relevant:
        return (), None, None, None, ("no_dependency_projection",), False
    if record.record_mode != "closed_record" or record.record_count != 1:
        return relevant, None, None, None, ("record_boundary_not_closed_single",), False
    receipt_ids = {item.receipt_id for item in relevant}
    if len(receipt_ids) != 1:
        return relevant, None, None, None, ("competing_provider_receipts",), True
    receipt = next((item for item in receipts if item.receipt_id in receipt_ids), None)
    if receipt is None:
        return relevant, None, None, None, ("receipt_not_found",), False
    if receipt.stage != "dependency_parse":
        return relevant, receipt, None, None, ("non_dependency_receipt",), False
    if receipt.source_digest != source_digest(record.source_text):
        return relevant, receipt, None, None, ("receipt_source_digest_mismatch",), True
    if receipt.status != "ok":
        return relevant, receipt, None, None, (f"receipt_status:{receipt.status}",), False
    scenario = record.one("scenario")
    if scenario is None or not _covered(
        scenario.value_start, scenario.value_end, receipt.target_spans
    ) or not _covered(scenario.value_start, scenario.value_end, receipt.covered_spans):
        return relevant, receipt, None, None, ("scenario_coverage_incomplete",), False
    required = set(REQUIRED_CAPABILITIES)
    if not required.issubset(receipt.requested_capabilities) or not required.issubset(
        receipt.fulfilled_capabilities
    ):
        return relevant, receipt, None, None, ("required_capability_missing",), False
    attempt = _attempt_for_receipt(receipt, attempts)
    if attempt is None:
        return relevant, receipt, None, None, ("receipt_output_not_bound_to_attempt",), True
    barriers = _barrier_reasons(attempt, signals, record)
    if barriers:
        return relevant, receipt, attempt, None, barriers, False
    qualification = registry.match(
        receipt,
        required_capabilities=REQUIRED_CAPABILITIES,
        policy_scope=policy_scope(assessment.obligation_id),
    )
    if qualification is None:
        return relevant, receipt, attempt, None, ("analyzer_not_qualified_for_scope",), False
    return relevant, receipt, attempt, qualification, (), False


def _reassess_performs(
    assessment: DirectRelationAssessment,
    *,
    binding: _TraceBinding,
    record: ParsedRequirementRecord,
    projections: tuple[DependencyRelationProjection, ...],
    receipt: ProviderExecutionReceipt,
    qualification: AnalyzerQualification,
) -> ObligationReassessment:
    user = record.one("user")
    scenario = record.one("scenario")
    candidates = tuple(item for item in projections if item.candidate.relation_kind == "performs")
    if user is None or scenario is None or len(candidates) != 1:
        return _base(
            assessment,
            binding=binding,
            decision="challenged_by_policy" if len(candidates) > 1 else "abstain",
            receipts=(receipt,),
            qualification=qualification,
            projections=candidates,
            reasons=("subject_candidate_not_unique",),
        )
    candidate = candidates[0]
    actor_span = candidate.candidate.from_span
    predicate_span = candidate.candidate.to_span
    actor = record.source_text[actor_span.start : actor_span.end]
    evidence = (
        (user.value_start, user.value_end),
        (scenario.value_start, scenario.value_end),
    )
    if not (
        scenario.value_start <= actor_span.start < actor_span.end <= scenario.value_end
        and scenario.value_start
        <= predicate_span.start
        < predicate_span.end
        <= scenario.value_end
    ):
        return _base(
            assessment,
            binding=binding,
            decision="challenged_by_policy",
            receipts=(receipt,),
            qualification=qualification,
            projections=candidates,
            evidence_spans=evidence,
            reasons=("subject_or_predicate_outside_scenario",),
        )
    if _normalized(actor) != _normalized(user.value):
        return _base(
            assessment,
            binding=binding,
            decision="challenged_by_policy",
            receipts=(receipt,),
            qualification=qualification,
            projections=candidates,
            evidence_spans=evidence,
            reasons=("declared_user_differs_from_plain_nsubj",),
        )
    if candidate.source_relation_kinds != ("dependency:nsubj",):
        return _base(
            assessment,
            binding=binding,
            decision="abstain",
            receipts=(receipt,),
            qualification=qualification,
            projections=candidates,
            evidence_spans=evidence,
            reasons=("subject_dependency_not_plain_nsubj",),
        )
    return _base(
        assessment,
        binding=binding,
        decision="supported",
        effective_outcome="supported",
        receipts=(receipt,),
        qualification=qualification,
        projections=candidates,
        evidence_spans=evidence,
        reasons=("qualified_exact_user_plain_nsubj",),
    )


def _reassess_acts_on(
    assessment: DirectRelationAssessment,
    *,
    binding: _TraceBinding,
    record: ParsedRequirementRecord,
    projections: tuple[DependencyRelationProjection, ...],
    receipt: ProviderExecutionReceipt,
    qualification: AnalyzerQualification,
) -> ObligationReassessment:
    user = record.one("user")
    scenario = record.one("scenario")
    subjects = tuple(item for item in projections if item.candidate.relation_kind == "performs")
    objects = tuple(item for item in projections if item.candidate.relation_kind == "acts_on")
    evidence = (
        (((user.value_start, user.value_end),) if user else ())
        + (((scenario.value_start, scenario.value_end),) if scenario else ())
    )
    if user is None or scenario is None:
        return _base(
            assessment,
            binding=binding,
            decision="abstain",
            receipts=(receipt,),
            qualification=qualification,
            projections=tuple((*subjects, *objects)),
            reasons=("closed_user_scenario_pair_missing",),
        )
    if len(subjects) != 1 or len(objects) != 1:
        return _base(
            assessment,
            binding=binding,
            decision="challenged_by_policy" if len(subjects) > 1 or len(objects) > 1 else "abstain",
            receipts=(receipt,),
            qualification=qualification,
            projections=tuple((*subjects, *objects)),
            evidence_spans=evidence,
            reasons=("subject_object_candidate_not_unique",),
        )
    subject = subjects[0]
    obj = objects[0]
    if subject.source_relation_kinds != ("dependency:nsubj",) or obj.source_relation_kinds not in {
        ("dependency:obj",),
        ("dependency:dobj",),
    }:
        return _base(
            assessment,
            binding=binding,
            decision="abstain",
            receipts=(receipt,),
            qualification=qualification,
            projections=(subject, obj),
            evidence_spans=evidence,
            reasons=("triad_requires_plain_nsubj_and_obj_or_dobj",),
        )
    actor_span = subject.candidate.from_span
    actor = record.source_text[actor_span.start : actor_span.end]
    if _normalized(actor) != _normalized(user.value):
        return _base(
            assessment,
            binding=binding,
            decision="challenged_by_policy",
            receipts=(receipt,),
            qualification=qualification,
            projections=(subject, obj),
            evidence_spans=evidence,
            reasons=("declared_user_differs_from_plain_nsubj",),
        )
    if subject.candidate.to_span != obj.candidate.from_span:
        return _base(
            assessment,
            binding=binding,
            decision="challenged_by_policy",
            receipts=(receipt,),
            qualification=qualification,
            projections=(subject, obj),
            evidence_spans=evidence,
            reasons=("subject_and_object_do_not_share_predicate",),
        )
    object_span = obj.candidate.to_span
    if not (
        scenario.value_start <= object_span.start < object_span.end <= scenario.value_end
    ):
        return _base(
            assessment,
            binding=binding,
            decision="challenged_by_policy",
            receipts=(receipt,),
            qualification=qualification,
            projections=(subject, obj),
            evidence_spans=evidence,
            reasons=("object_outside_scenario",),
        )
    return _base(
        assessment,
        binding=binding,
        decision="supported",
        effective_outcome="supported",
        receipts=(receipt,),
        qualification=qualification,
        projections=(subject, obj),
        evidence_spans=evidence,
        reasons=("qualified_exact_subject_predicate_object_triad",),
    )


def reassess_obligations(
    *,
    source_id: str,
    profile_id: str,
    profile_version: str,
    record: ParsedRequirementRecord,
    direct_assessments: tuple[DirectRelationAssessment, ...],
    initial_unresolved_obligations: tuple[UnresolvedObligation, ...],
    projections: tuple[DependencyRelationProjection, ...],
    attempts: tuple[AnalysisAttempt, ...],
    receipts: tuple[ProviderExecutionReceipt, ...],
    registry: QualifiedAnalyzerRegistry,
    residual_signals: tuple[ResidualRiskSignal, ...] = (),
    shadow: bool = False,
) -> tuple[ObligationReassessment, ...]:
    """Apply the narrow v0 assertion-capable policy as a pure derivation."""

    if source_id != source_digest(record.source_text):
        raise ValueError("reassessment source_id does not bind the supplied record")
    if not profile_id.strip() or not profile_version.strip():
        raise ValueError("reassessment profile identity must be non-empty")
    assessments_by_id = {item.obligation_id: item for item in direct_assessments}
    if len(assessments_by_id) != len(direct_assessments):
        raise ValueError("direct assessment identities must be unique")
    unresolved_by_id = {
        item.obligation_id: item for item in initial_unresolved_obligations
    }
    if len(unresolved_by_id) != len(initial_unresolved_obligations):
        raise ValueError("initial unresolved identities must be unique by obligation")
    for obligation_id, unresolved in unresolved_by_id.items():
        assessment = assessments_by_id.get(obligation_id)
        if assessment is None:
            raise ValueError("initial unresolved entry has no prior direct assessment")
        if (
            unresolved.source_id != source_id
            or unresolved.profile_id != profile_id
            or unresolved.profile_version != profile_version
            or unresolved.direct_rule_id != assessment.rule_id
            or unresolved.direct_outcome != assessment.outcome
            or unresolved.direct_unknown_reasons != assessment.unknown_reasons
            or unresolved.direct_reasons
            != tuple((*assessment.basis, *assessment.unknown_reasons))
        ):
            raise ValueError(
                f"initial unresolved entry is not bound to prior assessment:{obligation_id}"
            )

    results: list[ObligationReassessment] = []
    for assessment in direct_assessments:
        unresolved = unresolved_by_id.get(assessment.obligation_id)
        if assessment.outcome == "unresolved" and unresolved is None:
            raise ValueError(
                f"unresolved direct assessment lacks initial route identity:{assessment.obligation_id}"
            )
        binding = _TraceBinding(
            source_id=source_id,
            profile_id=profile_id,
            profile_version=profile_version,
            unresolved_id=unresolved.unresolved_id if unresolved else None,
            unresolved_digest=(
                canonical_digest(unresolved.as_dict()) if unresolved else None
            ),
            prior_assessment_digest=canonical_digest(assessment),
        )
        if assessment.obligation_id not in SUPPORTED_OBLIGATIONS or assessment.outcome != "unresolved":
            results.append(
                _base(assessment, binding=binding, decision="preserved")
            )
            continue
        allowed_reasons = DIRECT_REASON_ALLOWLIST[assessment.obligation_id]
        if tuple(assessment.unknown_reasons) != allowed_reasons:
            observed = ",".join(assessment.unknown_reasons) or "none"
            results.append(
                _base(
                    assessment,
                    binding=binding,
                    decision="abstain",
                    reasons=(f"direct_reason_not_reassessment_eligible:{observed}",),
                )
            )
            continue
        relevant, receipt, attempt, qualification, reasons, challenge = _candidate_material(
            assessment,
            record=record,
            projections=projections,
            receipts=receipts,
            attempts=attempts,
            registry=registry,
            signals=residual_signals,
        )
        if shadow:
            results.append(
                _base(
                    assessment,
                    binding=binding,
                    decision="shadow_observation",
                    receipts=(receipt,) if receipt else (),
                    qualification=qualification,
                    projections=relevant,
                    reasons=reasons or ("shadow_mode_cannot_change_result",),
                )
            )
            continue
        if reasons:
            results.append(
                _base(
                    assessment,
                    binding=binding,
                    decision="challenged_by_policy" if challenge else "abstain",
                    receipts=(receipt,) if receipt else (),
                    qualification=qualification,
                    projections=relevant,
                    reasons=reasons,
                )
            )
            continue
        assert receipt is not None and attempt is not None and qualification is not None
        if assessment.obligation_id == "func.performs":
            result = _reassess_performs(
                assessment,
                binding=binding,
                record=record,
                projections=relevant,
                receipt=receipt,
                qualification=qualification,
            )
        else:
            result = _reassess_acts_on(
                assessment,
                binding=binding,
                record=record,
                projections=relevant,
                receipt=receipt,
                qualification=qualification,
            )
        results.append(result)
    return tuple(results)


def used_qualifications(
    reassessments: tuple[ObligationReassessment, ...],
    registry: QualifiedAnalyzerRegistry,
) -> tuple[AnalyzerQualification, ...]:
    ids = {item for result in reassessments for item in result.qualification_ids}
    return tuple(item for item in registry.records if item.qualification_id in ids)


def validate_reassessment_trace(
    reassessment: ObligationReassessment,
    *,
    source_id: str,
    profile_id: str,
    profile_version: str,
    prior_assessment: DirectRelationAssessment,
    initial_unresolved: UnresolvedObligation | None,
) -> None:
    """Reject replay of a reassessment under a different route context."""

    expected_unresolved_id = (
        initial_unresolved.unresolved_id if initial_unresolved is not None else None
    )
    expected_unresolved_digest = (
        canonical_digest(initial_unresolved.as_dict())
        if initial_unresolved is not None
        else None
    )
    if (
        reassessment.source_id != source_id
        or reassessment.profile_id != profile_id
        or reassessment.profile_version != profile_version
        or reassessment.obligation_id != prior_assessment.obligation_id
        or reassessment.original_rule_id != prior_assessment.rule_id
        or reassessment.original_outcome != prior_assessment.outcome
        or reassessment.prior_assessment_digest
        != canonical_digest(prior_assessment)
        or reassessment.unresolved_id != expected_unresolved_id
        or reassessment.unresolved_digest != expected_unresolved_digest
    ):
        raise ValueError("reassessment trace binding mismatch")


__all__ = [
    "ObligationReassessment",
    "REASSESSMENT_POLICY_VERSION",
    "REQUIRED_CAPABILITIES",
    "policy_scope",
    "reassess_obligations",
    "used_qualifications",
    "validate_reassessment_trace",
]
