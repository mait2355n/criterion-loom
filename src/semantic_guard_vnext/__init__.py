"""Fail-closed semantic-guard vNext audit kernel."""

from importlib import import_module

__all__ = [
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
    "VNextAuditResult",
    "Workflow",
    "aggregate_audit_result",
    "audit_requirement_relations_vnext",
    "combined_challenge",
    "combined_coverage",
    "pass_invariants_hold",
    "load_public_schema",
    "public_audit_payload",
    "validate_public_audit",
]

_LAZY_ATTRS = {
    "AuditExecution": ("semantic_guard_vnext.models", "AuditExecution"),
    "Challenge": ("semantic_guard_vnext.models", "Challenge"),
    "Coverage": ("semantic_guard_vnext.models", "Coverage"),
    "DecisionRequest": ("semantic_guard_vnext.models", "DecisionRequest"),
    "EvidenceRef": ("semantic_guard_vnext.models", "EvidenceRef"),
    "EvidenceRole": ("semantic_guard_vnext.models", "EvidenceRole"),
    "Finality": ("semantic_guard_vnext.models", "Finality"),
    "GuardCoverage": ("semantic_guard_vnext.models", "GuardCoverage"),
    "Hold": ("semantic_guard_vnext.models", "Hold"),
    "ObligationResult": ("semantic_guard_vnext.models", "ObligationResult"),
    "Outcome": ("semantic_guard_vnext.models", "Outcome"),
    "RequirementAuditReport": (
        "semantic_guard_vnext.audit.report",
        "RequirementAuditReport",
    ),
    "SourceSpan": ("semantic_guard_vnext.models", "SourceSpan"),
    "StageAuthority": ("semantic_guard_vnext.models", "StageAuthority"),
    "VNextAuditResult": ("semantic_guard_vnext.models", "VNextAuditResult"),
    "Workflow": ("semantic_guard_vnext.models", "Workflow"),
    "aggregate_audit_result": (
        "semantic_guard_vnext.audit.aggregation",
        "aggregate_audit_result",
    ),
    "audit_requirement_relations_vnext": (
        "semantic_guard_vnext.audit.engine",
        "audit_requirement_relations_vnext",
    ),
    "combined_challenge": ("semantic_guard_vnext.models", "combined_challenge"),
    "combined_coverage": ("semantic_guard_vnext.models", "combined_coverage"),
    "pass_invariants_hold": ("semantic_guard_vnext.models", "pass_invariants_hold"),
    "load_public_schema": (
        "semantic_guard_vnext.public_contract",
        "load_public_schema",
    ),
    "public_audit_payload": (
        "semantic_guard_vnext.public_contract",
        "public_audit_payload",
    ),
    "validate_public_audit": (
        "semantic_guard_vnext.public_contract",
        "validate_public_audit",
    ),
}


def __getattr__(name: str) -> object:
    try:
        module_name, attribute_name = _LAZY_ATTRS[name]
    except KeyError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None
    value = getattr(import_module(module_name), attribute_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
