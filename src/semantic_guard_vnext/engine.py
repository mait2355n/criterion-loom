"""Compatibility imports for the canonical vNext audit engine."""

from .audit.engine import CATEGORY_GUARD, audit_requirement_relations_vnext
from .audit.report import AnalysisMode, RequirementAuditReport


__all__ = [
    "AnalysisMode",
    "CATEGORY_GUARD",
    "RequirementAuditReport",
    "audit_requirement_relations_vnext",
]
