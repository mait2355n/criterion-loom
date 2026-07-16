"""Fail-closed semantic-guard v1 audit kernel."""

from semantic_guard._version import __version__
from semantic_guard.aggregation import aggregate_audit_result
from semantic_guard.engine import RequirementAuditReport, audit_requirement_relations
from semantic_guard.models import (
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
    Workflow,
    combined_challenge,
    combined_coverage,
    pass_invariants_hold,
)
from semantic_guard.public_contract import (
    load_public_schema,
    public_audit_payload,
    validate_public_audit,
)

__all__ = [
    "__version__",
    "AuditExecution",
    "Challenge",
    "Coverage",
    "DecisionRequest",
    "EvidenceRef",
    "EvidenceRole",
    "Finality",
    "GuardCoverage",
    "Hold",
    "ObligationResult",
    "Outcome",
    "RequirementAuditReport",
    "SourceSpan",
    "StageAuthority",
    "AuditResult",
    "Workflow",
    "aggregate_audit_result",
    "audit_requirement_relations",
    "combined_challenge",
    "combined_coverage",
    "pass_invariants_hold",
    "load_public_schema",
    "public_audit_payload",
    "validate_public_audit",
]
