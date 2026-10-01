"""Pure construction stages used by the vNext audit engine."""

from __future__ import annotations

from ..models import AuditExecution, Coverage, GuardCoverage, Hold


_EXECUTION_REQUIRED_CHECKS = (
    "record_segmentation",
    "profile_applicability",
    "direct_obligation_projection",
    "residual_risk_gate",
    "provider_accounting",
)
_EXECUTION_BASE_COMPLETED_CHECKS = (
    "record_segmentation",
    "direct_obligation_projection",
    "residual_risk_gate",
)


def build_audit_execution(
    *,
    source_id: str,
    applicability: str,
    holds: tuple[Hold, ...],
    provider_failures: tuple[str, ...],
) -> AuditExecution:
    """Assemble execution coverage without mutating engine stage state."""

    completed_checks = list(_EXECUTION_BASE_COMPLETED_CHECKS)
    if applicability == "applicable":
        completed_checks.append("profile_applicability")
    if not provider_failures:
        completed_checks.append("provider_accounting")
    coverage_status = (
        Coverage.COMPLETE
        if len(completed_checks) == len(_EXECUTION_REQUIRED_CHECKS)
        else Coverage.PARTIAL
    )
    return AuditExecution(
        execution_id=f"execution.{source_id.split(':', 1)[1][:16]}",
        coverage=GuardCoverage(
            status=coverage_status,
            required_checks=_EXECUTION_REQUIRED_CHECKS,
            completed_checks=tuple(completed_checks),
            unresolved_reasons=tuple(
                ["profile_applicability_unknown"]
                if applicability != "applicable"
                else []
            )
            + tuple(
                f"required_provider_stage:{item}" for item in provider_failures
            ),
        ),
        holds=holds,
        provider_failures=provider_failures,
        integrity_failures=(),
    )


__all__ = ["build_audit_execution"]
