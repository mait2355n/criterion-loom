from __future__ import annotations

from dataclasses import dataclass, fields
from enum import Enum
from typing import Any


class Outcome(str, Enum):
    SATISFIED = "satisfied"
    REFUTED = "refuted"
    UNDETERMINED = "undetermined"
    NOT_APPLICABLE = "not_applicable"
    INVALID = "invalid"


class Finality(str, Enum):
    PROVISIONAL = "provisional"
    TERMINAL = "terminal"
    INVALID = "invalid"


class Challenge(str, Enum):
    NONE = "none"
    OPEN = "open"
    CONFLICT = "conflict"


class Coverage(str, Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    NOT_EVALUATED = "not_evaluated"
    FAILED = "failed"


class Workflow(str, Enum):
    """Audit workflow disposition, never a human acceptance decision."""

    PASS = "pass"
    WARN = "warn"
    BLOCK = "block"


class EvidenceRole(str, Enum):
    SUPPORT = "support"
    CHALLENGE = "challenge"
    SIGNAL = "signal"


def _wire(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, WireModel):
        return value.as_dict()
    if isinstance(value, tuple):
        return [_wire(item) for item in value]
    return value


class WireModel:
    """Small internal serialization aid; it is not the public schema contract."""

    def as_dict(self) -> dict[str, Any]:
        return {item.name: _wire(getattr(self, item.name)) for item in fields(self)}


def _require_identifier(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")


def _require_unique(values: tuple[str, ...], field_name: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{field_name} must not contain duplicate values")


@dataclass(frozen=True)
class SourceSpan(WireModel):
    source_id: str
    start: int
    end: int
    text: str = ""

    def __post_init__(self) -> None:
        _require_identifier(self.source_id, "source_id")
        if not isinstance(self.start, int) or not isinstance(self.end, int):
            raise TypeError("source offsets must be integers")
        if self.start < 0 or self.end <= self.start:
            raise ValueError("source span must satisfy 0 <= start < end")


@dataclass(frozen=True)
class StageAuthority(WireModel):
    """Four independent powers held by an analysis stage.

    Complexity and confidence do not grant authority.  A dependency parser or
    LLM candidate should normally use ``candidate_only``: it may contribute a
    challenge candidate, but it may neither establish support nor mutate hold
    state.  A versioned policy consumes candidate evidence and uses the
    separate ``policy_authority`` capability when a hold is warranted.
    """

    stage_id: str
    support: bool = False
    challenge: bool = False
    hold_apply: bool = False
    hold_release: bool = False

    def __post_init__(self) -> None:
        _require_identifier(self.stage_id, "stage_id")

    @classmethod
    def assertion_capable(cls, stage_id: str) -> StageAuthority:
        return cls(
            stage_id=stage_id,
            support=True,
            challenge=True,
        )

    @classmethod
    def candidate_only(cls, stage_id: str) -> StageAuthority:
        return cls(
            stage_id=stage_id,
            challenge=True,
        )

    @classmethod
    def signal_only(cls, stage_id: str) -> StageAuthority:
        return cls(stage_id=stage_id)

    @classmethod
    def policy_authority(
        cls,
        stage_id: str,
        *,
        challenge: bool = True,
        hold_apply: bool = True,
        hold_release: bool = False,
    ) -> StageAuthority:
        return cls(
            stage_id=stage_id,
            challenge=challenge,
            hold_apply=hold_apply,
            hold_release=hold_release,
        )


@dataclass(frozen=True)
class EvidenceRef(WireModel):
    evidence_id: str
    role: EvidenceRole
    authority: StageAuthority
    source_ref: str
    source_span: SourceSpan | None = None
    summary: str = ""

    def __post_init__(self) -> None:
        _require_identifier(self.evidence_id, "evidence_id")
        _require_identifier(self.source_ref, "source_ref")
        if not isinstance(self.role, EvidenceRole):
            object.__setattr__(self, "role", EvidenceRole(self.role))


@dataclass(frozen=True)
class Hold(WireModel):
    hold_id: str
    scope: tuple[str, ...]
    reason: str
    applied_by: EvidenceRef
    release_conditions: tuple[str, ...]
    released_by: EvidenceRef | None = None

    def __post_init__(self) -> None:
        _require_identifier(self.hold_id, "hold_id")
        _require_identifier(self.reason, "reason")
        object.__setattr__(self, "scope", tuple(self.scope))
        object.__setattr__(self, "release_conditions", tuple(self.release_conditions))
        if not self.scope:
            raise ValueError("hold scope must identify at least one obligation or '*'")
        if not self.release_conditions:
            raise ValueError("a hold must state its release conditions")
        _require_unique(self.scope, "scope")
        if not self.applied_by.authority.hold_apply:
            raise ValueError("hold was not applied by a stage with hold_apply authority")
        if self.released_by is not None and not self.released_by.authority.hold_release:
            raise ValueError("hold was not released by a stage with hold_release authority")

    @property
    def is_open(self) -> bool:
        return self.released_by is None


@dataclass(frozen=True)
class GuardCoverage(WireModel):
    status: Coverage
    required_checks: tuple[str, ...] = ()
    completed_checks: tuple[str, ...] = ()
    unresolved_reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.status, Coverage):
            object.__setattr__(self, "status", Coverage(self.status))
        object.__setattr__(self, "required_checks", tuple(self.required_checks))
        object.__setattr__(self, "completed_checks", tuple(self.completed_checks))
        object.__setattr__(self, "unresolved_reasons", tuple(self.unresolved_reasons))
        _require_unique(self.required_checks, "required_checks")
        _require_unique(self.completed_checks, "completed_checks")
        unexpected = set(self.completed_checks) - set(self.required_checks)
        if unexpected:
            raise ValueError(
                "completed_checks contains checks outside required_checks: "
                + ", ".join(sorted(unexpected))
            )
        if self.status is Coverage.COMPLETE:
            missing = set(self.required_checks) - set(self.completed_checks)
            if missing:
                raise ValueError(
                    "complete coverage is missing required checks: "
                    + ", ".join(sorted(missing))
                )
            if self.unresolved_reasons:
                raise ValueError("complete coverage cannot retain unresolved reasons")


@dataclass(frozen=True)
class ObligationResult(WireModel):
    obligation_id: str
    outcome: Outcome
    finality: Finality
    challenge: Challenge
    coverage: GuardCoverage
    active: bool = True
    required: bool = True
    interpretations: tuple[str, ...] = ()
    source_spans: tuple[SourceSpan, ...] = ()
    provenance: tuple[EvidenceRef, ...] = ()
    holds: tuple[Hold, ...] = ()
    unknown_reasons: tuple[str, ...] = ()
    residual_risks: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_identifier(self.obligation_id, "obligation_id")
        for field_name, enum_type in (
            ("outcome", Outcome),
            ("finality", Finality),
            ("challenge", Challenge),
        ):
            value = getattr(self, field_name)
            if not isinstance(value, enum_type):
                object.__setattr__(self, field_name, enum_type(value))
        for field_name in (
            "interpretations",
            "source_spans",
            "provenance",
            "holds",
            "unknown_reasons",
            "residual_risks",
        ):
            object.__setattr__(self, field_name, tuple(getattr(self, field_name)))
        if self.finality is Finality.INVALID and self.outcome is not Outcome.INVALID:
            raise ValueError("invalid finality requires invalid outcome")
        if self.outcome is Outcome.INVALID and self.finality is not Finality.INVALID:
            raise ValueError("invalid outcome requires invalid finality")
        if self.outcome is Outcome.UNDETERMINED and self.finality is Finality.TERMINAL:
            raise ValueError("an undetermined outcome cannot be terminal")
        if self.outcome is Outcome.NOT_APPLICABLE:
            if self.active or self.required:
                raise ValueError(
                    "not_applicable requires an inactive, non-required obligation"
                )
            if self.finality is not Finality.TERMINAL:
                raise ValueError("not_applicable must be terminal")
        if self.finality is Finality.TERMINAL and self.outcome in {
            Outcome.SATISFIED,
            Outcome.NOT_APPLICABLE,
        }:
            if self.coverage.status is not Coverage.COMPLETE:
                raise ValueError("terminal satisfaction requires complete obligation coverage")
            if self.challenge is not Challenge.NONE:
                raise ValueError("a challenged obligation cannot be terminally satisfied")
            if any(hold.is_open for hold in self.holds):
                raise ValueError("an open hold prevents terminal satisfaction")
            if not any(
                evidence.role is EvidenceRole.SUPPORT and evidence.authority.support
                for evidence in self.provenance
            ):
                raise ValueError(
                    "terminal satisfaction requires support evidence from an assertion-capable stage"
                )
        if self.finality is Finality.TERMINAL and self.outcome is Outcome.REFUTED:
            if not any(
                evidence.role is EvidenceRole.CHALLENGE and evidence.authority.challenge
                for evidence in self.provenance
            ):
                raise ValueError(
                    "terminal refutation requires challenge evidence from a challenge-capable stage"
                )
        for hold in self.holds:
            if "*" not in hold.scope and self.obligation_id not in hold.scope:
                raise ValueError(
                    f"hold {hold.hold_id!r} does not include obligation {self.obligation_id!r}"
                )

    @property
    def open_holds(self) -> tuple[Hold, ...]:
        return tuple(hold for hold in self.holds if hold.is_open)


@dataclass(frozen=True)
class AuditExecution(WireModel):
    execution_id: str
    coverage: GuardCoverage
    holds: tuple[Hold, ...] = ()
    provider_failures: tuple[str, ...] = ()
    integrity_failures: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_identifier(self.execution_id, "execution_id")
        for field_name in ("holds", "provider_failures", "integrity_failures"):
            object.__setattr__(self, field_name, tuple(getattr(self, field_name)))
        hold_ids = tuple(hold.hold_id for hold in self.holds)
        _require_unique(hold_ids, "hold ids")
        for field_name in ("provider_failures", "integrity_failures"):
            for value in getattr(self, field_name):
                _require_identifier(value, field_name)

    @property
    def open_holds(self) -> tuple[Hold, ...]:
        return tuple(hold for hold in self.holds if hold.is_open)


@dataclass(frozen=True)
class DecisionRequest(WireModel):
    request_id: str
    subject_ref: str
    issue_class: str
    epistemic_state: str
    detected_by: tuple[EvidenceRef, ...]
    required_authority: str
    affected_obligation_ids: tuple[str, ...]
    resolution_conditions: tuple[str, ...]
    agent_work_candidates: tuple[str, ...] = ()
    question_material: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for field_name in (
            "request_id",
            "subject_ref",
            "issue_class",
            "epistemic_state",
            "required_authority",
        ):
            _require_identifier(getattr(self, field_name), field_name)
        for field_name in (
            "detected_by",
            "affected_obligation_ids",
            "resolution_conditions",
            "agent_work_candidates",
            "question_material",
        ):
            object.__setattr__(self, field_name, tuple(getattr(self, field_name)))
        if not self.affected_obligation_ids:
            raise ValueError("a decision request must identify affected obligations")
        if not self.resolution_conditions:
            raise ValueError("a decision request must state resolution conditions")


@dataclass(frozen=True)
class AuditResult(WireModel):
    execution: AuditExecution
    obligations: tuple[ObligationResult, ...]
    outcome: Outcome
    finality: Finality
    challenge: Challenge
    coverage: Coverage
    workflow: Workflow
    decision_requests: tuple[DecisionRequest, ...] = ()
    residual_risks: tuple[str, ...] = ()
    reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for field_name, enum_type in (
            ("outcome", Outcome),
            ("finality", Finality),
            ("challenge", Challenge),
            ("coverage", Coverage),
            ("workflow", Workflow),
        ):
            value = getattr(self, field_name)
            if not isinstance(value, enum_type):
                object.__setattr__(self, field_name, enum_type(value))
        for field_name in ("obligations", "decision_requests", "residual_risks", "reasons"):
            object.__setattr__(self, field_name, tuple(getattr(self, field_name)))
        obligation_ids = tuple(item.obligation_id for item in self.obligations)
        _require_unique(obligation_ids, "obligation ids")
        expected_coverage = combined_coverage(self.execution, self.obligations)
        if self.coverage is not expected_coverage:
            raise ValueError(
                f"aggregate coverage must be {expected_coverage.value}, got {self.coverage.value}"
            )
        expected_challenge = combined_challenge(self.execution, self.obligations)
        if self.challenge is not expected_challenge:
            raise ValueError(
                f"aggregate challenge must be {expected_challenge.value}, got {self.challenge.value}"
            )
        if self.finality is Finality.INVALID and self.outcome is not Outcome.INVALID:
            raise ValueError("invalid finality requires invalid outcome")
        if self.outcome is Outcome.INVALID and self.finality is not Finality.INVALID:
            raise ValueError("invalid outcome requires invalid finality")
        if self.outcome is Outcome.UNDETERMINED and self.finality is Finality.TERMINAL:
            raise ValueError("an undetermined aggregate outcome cannot be terminal")
        if self.outcome is Outcome.INVALID and self.workflow is not Workflow.BLOCK:
            raise ValueError("an invalid audit must block")
        if self.challenge is Challenge.CONFLICT and self.workflow is not Workflow.BLOCK:
            raise ValueError("an aggregate conflict must block")
        if self.workflow is Workflow.PASS and not pass_invariants_hold(
            self.execution, self.obligations
        ):
            raise ValueError("pass violates fail-closed aggregation invariants")
        if self.workflow is Workflow.PASS:
            active_required = tuple(
                item for item in self.obligations if item.active and item.required
            )
            expected_outcome = Outcome.SATISFIED if active_required else Outcome.NOT_APPLICABLE
            if (
                self.outcome is not expected_outcome
                or self.finality is not Finality.TERMINAL
                or self.challenge is not Challenge.NONE
                or self.coverage is not Coverage.COMPLETE
            ):
                raise ValueError("pass dimensions are internally inconsistent")

    @property
    def is_pass(self) -> bool:
        return self.workflow is Workflow.PASS

    def obligation_ids_by_outcome(self) -> dict[str, list[str]]:
        grouped = {item.value: [] for item in Outcome}
        for obligation in self.obligations:
            grouped[obligation.outcome.value].append(obligation.obligation_id)
        return grouped


def pass_invariants_hold(
    execution: AuditExecution,
    obligations: tuple[ObligationResult, ...],
) -> bool:
    """Return whether a pass is structurally allowed.

    This does not determine human acceptance.  It only checks that the audit
    has no internal state that a legacy finding-only aggregation could hide.
    """

    obligations = tuple(obligations)
    if not obligations:
        return False
    if execution.coverage.status is not Coverage.COMPLETE:
        return False
    if execution.provider_failures or execution.integrity_failures or execution.open_holds:
        return False
    if any(
        obligation.active
        and (
            obligation.challenge is not Challenge.NONE
            or bool(obligation.open_holds)
            or obligation.outcome is Outcome.INVALID
        )
        for obligation in obligations
    ):
        return False

    active_required = tuple(
        obligation for obligation in obligations if obligation.active and obligation.required
    )
    if active_required:
        return all(
            obligation.finality is Finality.TERMINAL
            and obligation.outcome is Outcome.SATISFIED
            and obligation.coverage.status is Coverage.COMPLETE
            for obligation in active_required
        )

    # Avoid a vacuous pass.  An audit without active required obligations must
    # carry an explicit, terminal not-applicable result for every obligation.
    return all(
        obligation.outcome is Outcome.NOT_APPLICABLE
        and obligation.finality is Finality.TERMINAL
        and obligation.coverage.status is Coverage.COMPLETE
        for obligation in obligations
    )


def combined_coverage(
    execution: AuditExecution,
    obligations: tuple[ObligationResult, ...],
) -> Coverage:
    states = [execution.coverage.status]
    states.extend(
        item.coverage.status for item in obligations if item.active and item.required
    )
    if Coverage.FAILED in states:
        return Coverage.FAILED
    if Coverage.NOT_EVALUATED in states:
        return Coverage.NOT_EVALUATED
    if Coverage.PARTIAL in states:
        return Coverage.PARTIAL
    return Coverage.COMPLETE


def combined_challenge(
    execution: AuditExecution,
    obligations: tuple[ObligationResult, ...],
) -> Challenge:
    if any(item.challenge is Challenge.CONFLICT for item in obligations if item.active):
        return Challenge.CONFLICT
    if execution.open_holds or any(
        item.challenge is Challenge.OPEN or bool(item.open_holds)
        for item in obligations
        if item.active
    ):
        return Challenge.OPEN
    return Challenge.NONE
