from __future__ import annotations

from typing import Any

from ._version import __version__
from .engine import RequirementAuditReport
from .models import Challenge, Outcome, Workflow


def _excerpt(report: RequirementAuditReport, obligation_id: str) -> str:
    obligation = next(
        item for item in report.result.obligations if item.obligation_id == obligation_id
    )
    excerpts = [span.text for span in obligation.source_spans if span.text]
    return " | ".join(excerpts[:3])


def project_legacy_result(report: RequirementAuditReport) -> dict[str, Any]:
    """Project v1 into the old seven-field envelope.

    This is an explicitly lossy transport adapter.  Its score is only a fixed
    compatibility ordinal and is never a probability or the v1 decision
    basis.
    """

    findings: list[dict[str, Any]] = []
    missing: list[str] = []
    for obligation in report.result.obligations:
        if not obligation.active:
            continue
        if (
            obligation.outcome is Outcome.UNDETERMINED
            or obligation.finality.value != "terminal"
            or obligation.challenge is not Challenge.NONE
            or bool(obligation.open_holds)
        ):
            missing.extend(
                f"{obligation.obligation_id}: {reason}"
                for reason in obligation.unknown_reasons
            )
            if not obligation.unknown_reasons:
                missing.append(
                    f"{obligation.obligation_id}: unresolved {obligation.finality.value}/{obligation.challenge.value}"
                )
        if obligation.outcome is Outcome.REFUTED or obligation.challenge is Challenge.CONFLICT:
            findings.append(
                {
                    "severity": "blocker"
                    if obligation.challenge is Challenge.CONFLICT
                    else "major",
                    "category": "requirement_relation",
                    "basis": list(obligation.unknown_reasons)
                    or [f"outcome:{obligation.outcome.value}"],
                    "evidence": _excerpt(report, obligation.obligation_id),
                    "finding": (
                        f"{obligation.obligation_id} is {obligation.outcome.value} "
                        f"with challenge={obligation.challenge.value}."
                    ),
                    "suggested_fix": "Inspect the source-aligned evidence and satisfy the emitted resolution conditions.",
                    "needs_human_decision": bool(
                        any(
                            obligation.obligation_id in request.affected_obligation_ids
                            and request.required_authority == "requirement_owner_interpretation"
                            for request in report.result.decision_requests
                        )
                    ),
                    "warning_class": "actionable",
                    "rule_id": f"v1.{obligation.obligation_id}",
                    "match_status": "rejected"
                    if obligation.outcome is Outcome.REFUTED
                    else "unknown",
                    "confidence": "high"
                    if obligation.finality.value == "terminal"
                    else "low",
                }
            )

    actions = tuple(
        dict.fromkeys(
            action
            for request in report.result.decision_requests
            for action in (*request.agent_work_candidates, *request.resolution_conditions)
        )
    )
    score = {
        Workflow.PASS: 1.0,
        Workflow.WARN: 0.5,
        Workflow.BLOCK: 0.0,
    }[report.result.workflow]
    return {
        "phase": "audit_request",
        "status": report.result.workflow.value,
        "score": score,
        "findings": findings,
        "missing": list(dict.fromkeys(missing)),
        "next_actions": list(actions),
        "details": {
            "projection_contract": "semantic-guard-to-legacy-seven-field/v0",
            "score_semantics": "compatibility_ordinal_not_correctness_probability",
            "canonical_producer_version": __version__,
            "canonical_source_id": report.source_id,
            "canonical_outcome": report.result.outcome.value,
            "canonical_finality": report.result.finality.value,
            "canonical_challenge": report.result.challenge.value,
            "canonical_coverage": report.result.coverage.value,
            "limitations": [
                "This projection is lossy and is not the canonical v1 result.",
                "Legacy consumers cannot observe every hold, authority, interpretation, or provenance record.",
            ],
        },
    }
