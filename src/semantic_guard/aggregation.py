from __future__ import annotations

from semantic_guard.models import (
    AuditExecution,
    Challenge,
    Coverage,
    DecisionRequest,
    Finality,
    ObligationResult,
    Outcome,
    AuditResult,
    Workflow,
    combined_challenge,
    combined_coverage,
    pass_invariants_hold,
)


def aggregate_audit_result(
    *,
    execution: AuditExecution,
    obligations: tuple[ObligationResult, ...],
    decision_requests: tuple[DecisionRequest, ...] = (),
    residual_risks: tuple[str, ...] = (),
) -> AuditResult:
    """Aggregate independent audit dimensions without score-based promotion."""

    obligations = tuple(obligations)
    decision_requests = tuple(decision_requests)
    residual_risks = tuple(residual_risks)
    coverage = combined_coverage(execution, obligations)
    challenge = combined_challenge(execution, obligations)
    reasons = _collect_reasons(execution, obligations)

    invalid = bool(execution.integrity_failures) or any(
        item.outcome is Outcome.INVALID or item.finality is Finality.INVALID
        for item in obligations
        if item.active
    )
    active_required = tuple(
        item for item in obligations if item.active and item.required
    )
    terminal_refutation = any(
        item.outcome is Outcome.REFUTED and item.finality is Finality.TERMINAL
        for item in active_required
    )

    if invalid:
        outcome = Outcome.INVALID
        finality = Finality.INVALID
        workflow = Workflow.BLOCK
    elif challenge is Challenge.CONFLICT:
        outcome = Outcome.UNDETERMINED
        finality = Finality.PROVISIONAL
        workflow = Workflow.BLOCK
    elif terminal_refutation:
        outcome = Outcome.REFUTED
        finality = Finality.TERMINAL
        workflow = Workflow.BLOCK
    elif pass_invariants_hold(execution, obligations):
        outcome = Outcome.SATISFIED if active_required else Outcome.NOT_APPLICABLE
        finality = Finality.TERMINAL
        workflow = Workflow.PASS
    else:
        outcome = Outcome.UNDETERMINED
        finality = Finality.PROVISIONAL
        workflow = Workflow.WARN

    return AuditResult(
        execution=execution,
        obligations=obligations,
        outcome=outcome,
        finality=finality,
        challenge=challenge,
        coverage=coverage,
        workflow=workflow,
        decision_requests=decision_requests,
        residual_risks=residual_risks,
        reasons=reasons,
    )


def _collect_reasons(
    execution: AuditExecution,
    obligations: tuple[ObligationResult, ...],
) -> tuple[str, ...]:
    reasons: list[str] = []
    reasons.extend(f"integrity_failure:{item}" for item in execution.integrity_failures)
    reasons.extend(f"provider_failure:{item}" for item in execution.provider_failures)
    reasons.extend(f"open_hold:{item.hold_id}" for item in execution.open_holds)
    if execution.coverage.status is not Coverage.COMPLETE:
        reasons.append(f"execution_coverage:{execution.coverage.status.value}")
    for obligation in obligations:
        if not obligation.active:
            continue
        if obligation.coverage.status is not Coverage.COMPLETE:
            reasons.append(
                f"obligation_coverage:{obligation.obligation_id}:{obligation.coverage.status.value}"
            )
        if obligation.challenge is not Challenge.NONE:
            reasons.append(
                f"challenge:{obligation.obligation_id}:{obligation.challenge.value}"
            )
        reasons.extend(
            f"unknown:{obligation.obligation_id}:{item}"
            for item in obligation.unknown_reasons
        )
        reasons.extend(
            f"open_hold:{item.hold_id}" for item in obligation.open_holds
        )
    return tuple(dict.fromkeys(reasons))
