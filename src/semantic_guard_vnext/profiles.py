from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


Necessity = Literal["required", "conditional"]


@dataclass(frozen=True, slots=True)
class RelationObligationSpec:
    obligation_id: str
    relation_kind: str
    from_role: str
    to_role: str
    necessity: Necessity = "required"
    critical: bool = False
    required_guards: tuple[str, ...] = (
        "record_boundary",
        "discourse_scope",
        "temporal_scope",
        "polarity_scope",
        "modality_scope",
        "attachment",
    )


@dataclass(frozen=True, slots=True)
class NormativeProfile:
    profile_id: str
    version: str
    requirement_kind: str
    obligations: tuple[RelationObligationSpec, ...]
    purpose: str
    limitations: tuple[str, ...]


FUNCTIONAL_REQUIREMENT_PROFILE = NormativeProfile(
    profile_id="functional-requirement-record",
    version="v1",
    requirement_kind="functional",
    purpose="Audit whether a structured functional requirement exposes the relations needed for bounded verification.",
    limitations=(
        "The profile is an adopted engineering criterion, not natural-language truth.",
        "A satisfied relation does not prove implementation, action occurrence, or human acceptance.",
        "Open text cannot establish absence without a closed record contract.",
    ),
    obligations=(
        RelationObligationSpec("func.applies_to", "applies_to", "requirement", "scenario_actor"),
        RelationObligationSpec("func.performs", "performs", "scenario_actor", "behavior"),
        RelationObligationSpec(
            "func.acts_on", "acts_on", "behavior", "object", necessity="conditional"
        ),
        RelationObligationSpec(
            "func.triggered_by", "triggered_by", "behavior", "condition", necessity="conditional"
        ),
        RelationObligationSpec("func.produces", "produces", "behavior", "observable_result"),
        RelationObligationSpec(
            "func.constrained_by",
            "constrained_by",
            "observable_result",
            "acceptance_criterion",
            critical=True,
        ),
        RelationObligationSpec(
            "func.uses_metric",
            "uses_metric",
            "acceptance_criterion",
            "metric",
            necessity="conditional",
        ),
        RelationObligationSpec(
            "func.verified_by",
            "verified_by",
            "requirement",
            "verification_method",
            critical=True,
        ),
        RelationObligationSpec(
            "func.verifies",
            "verifies",
            "verification_method",
            "acceptance_criterion",
            critical=True,
            required_guards=(
                "record_boundary",
                "discourse_scope",
                "temporal_scope",
                "polarity_scope",
                "modality_scope",
                "attachment",
                "target_alignment",
            ),
        ),
        RelationObligationSpec(
            "func.measures",
            "measures",
            "verification_method",
            "metric",
            necessity="conditional",
        ),
        RelationObligationSpec(
            "func.produces_evidence",
            "produces_evidence",
            "verification_method",
            "evidence_artifact",
            critical=True,
        ),
    ),
)


def obligation_by_id(obligation_id: str) -> RelationObligationSpec:
    for obligation in FUNCTIONAL_REQUIREMENT_PROFILE.obligations:
        if obligation.obligation_id == obligation_id:
            return obligation
    raise KeyError(obligation_id)
