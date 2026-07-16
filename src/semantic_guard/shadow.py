from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .engine import RequirementAuditReport
from .legacy_runner import LegacyObservation


KNOWN_SCOPE_DEFEATERS = frozenset(
    {
        "reported_speech_present",
        "metalinguistic_or_quotation_present",
        "non_adoption_or_proposal_present",
        "historical_or_retired_scope_present",
        "negation_scope_present",
        "conditional_or_exception_scope_present",
        "modal_uncertainty_present",
        "multiple_propositions_present",
        "unconsumed_relevant_span",
        "record_boundary_not_single",
    }
)


@dataclass(frozen=True, slots=True)
class ShadowDifference:
    subject: str
    observation_delta: str
    direction: str
    assessment: str
    basis_kind: str
    legacy_value: Any
    canonical_value: Any
    rationale: str


@dataclass(frozen=True, slots=True)
class ShadowComparison:
    source_id: str
    legacy_execution_status: str
    legacy_baseline_status: str
    canonical_workflow: str
    canonical_outcome: str
    differences: tuple[ShadowDifference, ...]
    unresolved_requires_review_count: int
    schema_version: str = "semantic-guard-shadow-comparison/v0"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _legacy_obligation_state(check: dict[str, Any]) -> str:
    derivation = str(check.get("derivation_status", "")).casefold()
    status = str(check.get("status", "")).casefold()
    if derivation in {"satisfied", "derived"} or status == "aligned":
        return "satisfied"
    if derivation in {"refuted", "mismatch"} or status == "mismatch":
        return "refuted"
    if derivation == "conflict" or status == "conflict":
        return "conflict"
    return "undetermined"


def _known_defect_basis(report: RequirementAuditReport) -> tuple[bool, tuple[str, ...]]:
    reasons = tuple(
        sorted(
            {
                item.reason_code
                for item in report.residual_signals
                if item.reason_code in KNOWN_SCOPE_DEFEATERS
            }
        )
    )
    return bool(reasons), reasons


def _known_defect_basis_for_obligation(obligation: Any) -> tuple[bool, tuple[str, ...]]:
    """Limit a known-defect classification to holds on the compared obligation."""

    reasons = tuple(
        sorted(
            {
                hold.reason
                for hold in obligation.open_holds
                if hold.reason in KNOWN_SCOPE_DEFEATERS
            }
        )
    )
    return bool(reasons), reasons


def compare_with_legacy(
    report: RequirementAuditReport,
    legacy: LegacyObservation,
) -> ShadowComparison:
    """Classify observations without treating either implementation as truth.

    The constitution and adjudicated conformance cases, not output agreement,
    decide whether a delta is acceptable.  Unjustified differences remain
    explicit review work.
    """

    differences: list[ShadowDifference] = []
    normalized = legacy.normalized_legacy_observation
    known_defect, defect_reasons = _known_defect_basis(report)

    if legacy.execution.status != "completed" or normalized is None:
        differences.append(
            ShadowDifference(
                subject="legacy_execution",
                observation_delta="execution_availability_change",
                direction="canonical_only",
                assessment="provider_environment_drift"
                if legacy.execution.status in {"unavailable", "execution_error"}
                else "unresolved_requires_review",
                basis_kind="operational_evidence",
                legacy_value=legacy.execution.status,
                canonical_value="completed",
                rationale="The legacy observation was unavailable; semantic equivalence was not inferred.",
            )
        )
    else:
        legacy_status = normalized.get("top_level", {}).get("legacy_status")
        canonical_status = report.result.workflow.value
        if legacy_status != canonical_status:
            if legacy_status == "pass" and not report.result.is_pass and known_defect:
                assessment = "legacy_known_defect"
                basis = "constitution_invariant"
                rationale = (
                    "Canonical v1 preserved a scope defeater forbidden from affirmative promotion by "
                    f"INV-VN-006: {', '.join(defect_reasons)}"
                )
            else:
                assessment = "unresolved_requires_review"
                basis = "none"
                rationale = "A disposition delta is not self-justifying and requires an adjudicated case."
            differences.append(
                ShadowDifference(
                    subject="workflow_disposition",
                    observation_delta="disposition_change",
                    direction="conflicting",
                    assessment=assessment,
                    basis_kind=basis,
                    legacy_value=legacy_status,
                    canonical_value=canonical_status,
                    rationale=rationale,
                )
            )

        legacy_checks = normalized.get("relation", {}).get("obligation_checks", [])
        canonical_by_id = {item.obligation_id: item for item in report.result.obligations}
        for check in legacy_checks if isinstance(legacy_checks, list) else []:
            if not isinstance(check, dict):
                continue
            obligation_id = str(check.get("obligation_id", ""))
            if not obligation_id or obligation_id not in canonical_by_id:
                continue
            legacy_state = _legacy_obligation_state(check)
            current = canonical_by_id[obligation_id]
            canonical_state = current.outcome.value
            equivalent = (
                legacy_state == canonical_state
                and not (legacy_state == "satisfied" and current.finality.value != "terminal")
            )
            if equivalent:
                continue
            scoped_known_defect, scoped_reasons = _known_defect_basis_for_obligation(
                current
            )
            if legacy_state == "satisfied" and scoped_known_defect:
                assessment = "legacy_known_defect"
                basis = "constitution_invariant"
                rationale = (
                    "Legacy affirmative promotion is challenged by an independently detected scope defeater: "
                    + ", ".join(scoped_reasons)
                )
            else:
                assessment = "unresolved_requires_review"
                basis = "none"
                rationale = "The obligation delta has no adjudicated reference in this comparison."
            differences.append(
                ShadowDifference(
                    subject=obligation_id,
                    observation_delta="obligation_state_change",
                    direction="conflicting",
                    assessment=assessment,
                    basis_kind=basis,
                    legacy_value={
                        "state": legacy_state,
                        "status": check.get("status"),
                        "derivation_status": check.get("derivation_status"),
                    },
                    canonical_value={
                        "outcome": current.outcome.value,
                        "finality": current.finality.value,
                        "challenge": current.challenge.value,
                    },
                    rationale=rationale,
                )
            )

        legacy_record_mode = normalized.get("relation", {}).get("coverage", {}).get("record_mode")
        if legacy_record_mode and legacy_record_mode != report.record.record_mode:
            differences.append(
                ShadowDifference(
                    subject="input_record_boundary",
                    observation_delta="coverage_change",
                    direction="conflicting",
                    assessment="intentional_constitutional_change"
                    if report.record.record_mode == "open_text"
                    else "unresolved_requires_review",
                    basis_kind="constitution_invariant"
                    if report.record.record_mode == "open_text"
                    else "none",
                    legacy_value=legacy_record_mode,
                    canonical_value=report.record.record_mode,
                    rationale=(
                        "Canonical v1 does not infer a closed assertion boundary from unconsumed prose."
                        if report.record.record_mode == "open_text"
                        else "The record-boundary delta requires an adjudicated case."
                    ),
                )
            )

    if not differences:
        differences.append(
            ShadowDifference(
                subject="normalized_observation",
                observation_delta="equivalent",
                direction="equivalent_after_normalization",
                assessment="coverage_expansion" if report.shadow_signals else "intentional_constitutional_change",
                basis_kind="operational_evidence",
                legacy_value="no classified semantic delta",
                canonical_value="no classified semantic delta",
                rationale="No delta was found in the currently normalized comparison surface.",
            )
        )

    unresolved = sum(
        item.assessment == "unresolved_requires_review" for item in differences
    )
    return ShadowComparison(
        source_id=report.source_id,
        legacy_execution_status=legacy.execution.status,
        legacy_baseline_status=legacy.execution.baseline.status,
        canonical_workflow=report.result.workflow.value,
        canonical_outcome=report.result.outcome.value,
        differences=tuple(differences),
        unresolved_requires_review_count=unresolved,
    )
