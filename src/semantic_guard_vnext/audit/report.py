"""Typed report returned by the canonical vNext audit engine."""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
from typing import Any, Literal

from ..dependency_projection import DependencyRelationProjection
from ..direct_rules import DirectRelationAssessment
from ..lifting import LiftingResolution
from ..models import VNextAuditResult
from ..provider_receipts import AnalyzerQualification, ProviderExecutionReceipt
from ..providers import AnalysisAttempt
from ..reassessment import ObligationReassessment
from ..records import ParsedRequirementRecord
from ..residual_risk import ResidualRiskSignal
from ..routing import StagePlan, UnresolvedObligation


AnalysisMode = Literal["assurance", "conditional", "shadow_all"]


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
    result: VNextAuditResult
    analysis_mode: AnalysisMode
    limitations: tuple[str, ...]
    schema_version: str = "semantic-guard-vnext-requirement-audit/v0"

    def as_dict(self) -> dict[str, Any]:
        payload = _wire(self)
        assert isinstance(payload, dict)
        payload["summary"] = self.result.obligation_ids_by_outcome()
        payload["record"] = {
            "record_mode": self.record.record_mode,
            "record_count": self.record.record_count,
            "field_names": sorted(
                name for name, values in self.record.fields.items() if values
            ),
            "missing_fields": list(self.record.missing_fields),
            "duplicate_fields": list(self.record.duplicate_fields),
            "unconsumed_spans": [
                {
                    "start": start,
                    "end": end,
                    "text": self.record.source_text[start:end],
                }
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


__all__ = ["AnalysisMode", "RequirementAuditReport"]
