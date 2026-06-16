from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from semantic_guard.codex_exec_review import (
    DEFAULT_CODEX_MODEL,
    DEFAULT_TIMEOUT_SECONDS,
    CodexExecReviewRequest,
    Runner,
    run_codex_exec_review,
)
from semantic_guard.core import (
    _problem_mechanism_evidence_signal,
    _problem_or_symptom_signal,
    _side_effect_transfer_evidence_signal,
    _solution_action_signal,
    _symptom_disappearance_success_signal,
)

ESCALATION_TARGET = "candidate_gap_reviewer"
DEFAULT_ROUTING_POLICY = "default"
REVIEW_PRESSURE_SCORE_SEMANTICS = "review routing pressure; not correctness probability"
HIGH_IMPACT_CATEGORIES = {"security", "meaning", "evidence"}
HIGH_IMPACT_BOUNDARIES = {"identity", "persistence", "source_of_truth", "permission"}
ESCALATION_AMBIGUITY_REASONS = {
    "negated_context",
    "quoted_or_historical",
    "trace_vocabulary_gap",
    "high_impact_low_specificity",
}
NON_DECISIONS = [
    "does_not_score_correctness_probability",
    "does_not_accept_or_reject_candidate",
    "does_not_clear_deterministic_findings",
    "does_not_change_status_or_score",
    "does_not_change_final_human_decision",
]


@dataclass(frozen=True)
class EscalationSignal:
    id: str
    dimension: str
    weight: int
    source: str
    evidence: str
    finding_index: int | None = None
    rule_id: str = ""
    severity: str = ""
    category: str = ""

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": self.id,
            "dimension": self.dimension,
            "weight": self.weight,
            "source": self.source,
            "evidence": self.evidence,
        }
        if self.finding_index is not None:
            payload["finding_index"] = self.finding_index
        if self.rule_id:
            payload["rule_id"] = self.rule_id
        if self.severity:
            payload["severity"] = self.severity
        if self.category:
            payload["category"] = self.category
        return payload


@dataclass
class EscalationDecision:
    needed: bool
    mode: str = "dry_run"
    target: str = ESCALATION_TARGET
    routing_policy: str = DEFAULT_ROUTING_POLICY
    reasons: list[str] = field(default_factory=list)
    rationale: list[str] = field(default_factory=list)
    pressure: dict[str, Any] = field(default_factory=dict)
    dimensions: dict[str, str] = field(default_factory=dict)
    signals: list[dict[str, Any]] = field(default_factory=list)
    non_decisions: list[str] = field(default_factory=lambda: list(NON_DECISIONS))
    payload: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "needed": self.needed,
            "mode": self.mode,
            "target": self.target,
            "routing_policy": self.routing_policy,
            "reasons": self.reasons,
            "rationale": self.rationale,
            "pressure": self.pressure,
            "dimensions": self.dimensions,
            "signals": self.signals,
            "non_decisions": self.non_decisions,
            "payload": self.payload,
        }


def decide_escalation(
    *,
    candidate: str,
    phase: str,
    deterministic_audit: Mapping[str, Any],
    request: str = "",
    constraints: str = "",
    non_goals: str = "",
    unknowns: str = "",
    context: str = "",
    review_context: Mapping[str, Any] | None = None,
    mode: str = "dry_run",
) -> dict[str, Any]:
    audit = dict(deterministic_audit or {})
    normalized_phase = phase or str(audit.get("phase", ""))
    normalized_review_context = _mapping(review_context)
    signals = _escalation_signals(audit, normalized_review_context)
    _add_candidate_mechanism_fit_signals(signals, candidate, request, context, normalized_phase)
    assessment = _routing_assessment(signals)
    return EscalationDecision(
        needed=bool(signals),
        mode="execute" if mode == "execute" else "dry_run",
        reasons=_signal_reasons(signals),
        rationale=_signal_rationale(signals),
        pressure=assessment["pressure"],
        dimensions=assessment["dimensions"],
        signals=assessment["signals"],
        non_decisions=assessment["non_decisions"],
        payload={
            "candidate": candidate,
            "request": request,
            "deterministic_audit": audit,
            "review_context": normalized_review_context,
            "routing_assessment": assessment,
            "constraints": constraints,
            "non_goals": non_goals,
            "unknowns": unknowns,
            "context": context,
            "phase": normalized_phase,
        },
    ).as_dict()


def review_if_needed(
    payload: Mapping[str, Any],
    *,
    execute: bool = False,
    model: str = DEFAULT_CODEX_MODEL,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    working_directory: str = "",
    include_schema: bool = False,
    runner: Runner | None = None,
) -> dict[str, Any]:
    audit = _mapping(payload.get("deterministic_audit") or payload.get("audit_result"))
    phase = _string(payload.get("phase")) or _string(audit.get("phase"))
    candidate = _string(payload.get("candidate"))
    review_context = _mapping(payload.get("review_context") or payload.get("routing_context"))
    decision = decide_escalation(
        candidate=candidate,
        phase=phase,
        deterministic_audit=audit,
        request=_string(payload.get("request")),
        constraints=_string(payload.get("constraints")),
        non_goals=_string(payload.get("non_goals")),
        unknowns=_string(payload.get("unknowns")),
        context=_string(payload.get("context")),
        review_context=review_context,
        mode="execute" if execute else "dry_run",
    )
    if not decision["needed"]:
        return {"escalation": decision, "review_result": None}

    try:
        request = CodexExecReviewRequest.from_mapping(
            decision["payload"],
            model=model,
            timeout_seconds=timeout_seconds,
            working_directory=working_directory or None,
            codex_binary="codex",
            include_schema_in_prompt=include_schema,
        )
    except ValueError as exc:
        return {
            "escalation": decision,
            "review_result": {
                "executed": False,
                "execution_status": "input_error",
                "valid": False,
                "errors": [str(exc)],
            },
        }

    if runner is None:
        review = run_codex_exec_review(request, execute=execute)
    else:
        review = run_codex_exec_review(request, execute=execute, runner=runner)
    return {"escalation": decision, "review_result": review.as_dict()}


def _escalation_reasons(audit: Mapping[str, Any]) -> tuple[list[str], list[str]]:
    signals = _escalation_signals(audit, {})
    return _signal_reasons(signals), _signal_rationale(signals)


def _escalation_signals(audit: Mapping[str, Any], review_context: Mapping[str, Any]) -> list[EscalationSignal]:
    findings = _findings(audit)
    details = _mapping(audit.get("details"))
    signals: list[EscalationSignal] = []

    for index, finding in enumerate(findings):
        if finding.get("warning_class") == "possible false positive":
            _add_signal(
                signals,
                "possible_false_positive",
                "countercondition_plausibility",
                25,
                "finding.warning_class",
                "deterministic audit found a warning with nearby rejected candidate text",
                index,
                finding,
            )

        if finding.get("match_status") == "unknown":
            _add_signal(
                signals,
                "unknown_match_status",
                "uncertainty",
                30,
                "finding.match_status",
                "field matching produced an explicit unknown match status",
                index,
                finding,
            )

        if finding.get("match_status") == "partial" and finding.get("severity") in {"blocker", "major"}:
            _add_signal(
                signals,
                "high_severity_partial_match",
                "uncertainty",
                24,
                "finding.match_status",
                "a high-severity finding has only a partial deterministic match",
                index,
                finding,
            )

        if finding.get("confidence") == "low" and (
            finding.get("category") in HIGH_IMPACT_CATEGORIES or bool(finding.get("semantic_boundaries"))
        ):
            _add_signal(
                signals,
                "high_impact_low_confidence",
                "uncertainty",
                30,
                "finding.confidence",
                "a high-impact finding has low deterministic confidence",
                index,
                finding,
            )

    structured_reasons = sorted(
        {
            reason
            for finding in findings
            for reason in finding.get("ambiguity_reasons", [])
            if isinstance(reason, str) and reason in ESCALATION_AMBIGUITY_REASONS
        }
    )
    if structured_reasons:
        _add_signal(
            signals,
            "structured_ambiguity_reason",
            "ambiguity",
            22,
            "finding.ambiguity_reasons",
            f"structured ambiguity reasons require review: {', '.join(structured_reasons)}",
        )

    for index, finding in enumerate(findings):
        if finding.get("severity") in {"blocker", "major"} and finding.get("nearest_candidates"):
            _add_signal(
                signals,
                "major_or_blocking_gap_has_candidate",
                "countercondition_plausibility",
                20,
                "finding.nearest_candidates",
                "a high-severity missing field has nearby candidate text and may be a parser miss",
                index,
                finding,
            )

        if finding.get("warning_class") == "generic caution" and (
            finding.get("category") in HIGH_IMPACT_CATEGORIES or bool(finding.get("semantic_boundaries"))
        ):
            _add_signal(
                signals,
                "high_impact_generic_caution",
                "impact",
                18,
                "finding.warning_class",
                "a broad caution touches evidence, security, meaning, or named semantic boundaries",
                index,
                finding,
            )

        if finding.get("rule_id") in {
            "req.solution.problem_mechanism_fit_missing",
            "req.acceptance.symptom_only_success_criteria",
            "plan.risk.hazard_transfer_analysis_missing",
        }:
            _add_signal(
                signals,
                "problem_mechanism_fit_gap",
                "mechanism_fit_uncertainty",
                26,
                "finding.rule_id",
                "deterministic audit found a problem-solution fit or symptom-suppression gap that benefits from context-isolated review",
                index,
                finding,
            )

    document_checks = _mapping(details.get("document_checks"))
    if document_checks.get("no_implementation_evidence_available") and any(
        finding.get("category") == "evidence" for finding in findings
    ):
        _add_signal(
            signals,
            "document_runtime_evidence_gap",
            "uncertainty",
            24,
            "details.document_checks",
            "document-only audit cannot determine whether strong runtime claims are supported elsewhere",
        )

    boundaries = _semantic_boundaries_from_audit(audit)
    risky_boundaries = sorted(boundaries & HIGH_IMPACT_BOUNDARIES)
    if risky_boundaries:
        _add_signal(
            signals,
            "semantic_boundary_review",
            "impact",
            28,
            "details.semantic_boundaries",
            f"diff touches high-impact semantic boundaries: {', '.join(risky_boundaries)}",
        )

    score = audit.get("score")
    has_blocker = any(finding.get("severity") == "blocker" for finding in findings)
    if isinstance(score, (float, int)) and float(score) < 0.8 and audit.get("status") == "warn" and not has_blocker:
        _add_signal(
            signals,
            "low_confidence_warn",
            "review_value",
            12,
            "audit.score",
            "audit score is low without a deterministic blocker, so a supplement review may clarify the gap",
        )

    _add_review_context_signals(signals, review_context)
    return signals


def _add_signal(
    signals: list[EscalationSignal],
    signal_id: str,
    dimension: str,
    weight: int,
    source: str,
    evidence: str,
    finding_index: int | None = None,
    finding: Mapping[str, Any] | None = None,
) -> None:
    if any(signal.id == signal_id and signal.finding_index == finding_index for signal in signals):
        return
    item = _mapping(finding)
    signals.append(
        EscalationSignal(
            id=signal_id,
            dimension=dimension,
            weight=weight,
            source=source,
            evidence=evidence,
            finding_index=finding_index,
            rule_id=_string(item.get("rule_id")),
            severity=_string(item.get("severity")),
            category=_string(item.get("category")),
        )
    )


def _add_review_context_signals(signals: list[EscalationSignal], review_context: Mapping[str, Any]) -> None:
    if not review_context:
        return
    if _truthy(review_context.get("independent_review_requested")) or _truthy(
        review_context.get("fresh_eyes_requested")
    ):
        _add_signal(
            signals,
            "independent_review_requested",
            "independent_review_value",
            32,
            "review_context.independent_review_requested",
            "caller requested context-isolated fresh-eyes review",
        )
    if _truthy(review_context.get("self_reviewed")) or _truthy(
        review_context.get("same_agent_planned_and_implemented")
    ):
        _add_signal(
            signals,
            "context_contamination_risk",
            "context_contamination_risk",
            18,
            "review_context.self_reviewed",
            "same working context may have planned, implemented, and reviewed the change",
        )
    if _truthy(review_context.get("long_running_work")):
        _add_signal(
            signals,
            "long_running_work_context",
            "context_contamination_risk",
            12,
            "review_context.long_running_work",
            "long-running work increases the value of an independent second pass",
        )
    if _truthy(review_context.get("public_release")) or _truthy(review_context.get("external_publication")):
        _add_signal(
            signals,
            "public_or_external_surface",
            "impact",
            18,
            "review_context.public_release",
            "public or external-facing material benefits from independent review",
        )
    changed_files_count = review_context.get("changed_files_count")
    if isinstance(changed_files_count, int) and changed_files_count >= 10:
        _add_signal(
            signals,
            "wide_change_surface",
            "review_value",
            12,
            "review_context.changed_files_count",
            f"wide change surface with {changed_files_count} changed files benefits from a fresh pass",
        )


def _add_candidate_mechanism_fit_signals(
    signals: list[EscalationSignal],
    candidate: str,
    request: str,
    context: str,
    phase: str,
) -> None:
    if phase not in {"audit_request", "audit_plan"}:
        return
    combined = "\n".join(part for part in [candidate, request, context] if part)
    if not combined.strip():
        return
    has_problem = bool(_problem_or_symptom_signal(combined))
    has_solution = bool(_solution_action_signal(combined))
    has_mechanism = bool(_problem_mechanism_evidence_signal(combined))
    has_symptom_only_success = bool(_symptom_disappearance_success_signal(combined))
    has_transfer_evidence = bool(_side_effect_transfer_evidence_signal(combined))

    if has_problem and has_solution and not has_mechanism:
        _add_signal(
            signals,
            "candidate_mechanism_fit_unclear",
            "mechanism_fit_uncertainty",
            24,
            "candidate.structure",
            "candidate states a problem and solution, but cause, mechanism, constraint, or solution-fit evidence is thin",
        )

    if has_problem and has_solution and has_symptom_only_success and not (has_mechanism or has_transfer_evidence):
        _add_signal(
            signals,
            "candidate_symptom_suppression_risk",
            "mechanism_fit_uncertainty",
            18,
            "candidate.acceptance_structure",
            "candidate success criteria appear to rely on symptom disappearance without mechanism or transfer evidence",
        )


def _routing_assessment(signals: list[EscalationSignal]) -> dict[str, Any]:
    score = min(100, sum(max(0, signal.weight) for signal in signals))
    return {
        "routing_policy": DEFAULT_ROUTING_POLICY,
        "pressure": {
            "score": score,
            "level": _pressure_level(score),
            "score_semantics": REVIEW_PRESSURE_SCORE_SEMANTICS,
        },
        "dimensions": _dimension_levels(signals),
        "signals": [signal.as_dict() for signal in signals],
        "non_decisions": list(NON_DECISIONS),
    }


def _pressure_level(score: int) -> str:
    if score <= 0:
        return "none"
    if score < 40:
        return "dry_run_recommended"
    if score < 70:
        return "review_recommended"
    return "high_review_pressure"


def _dimension_levels(signals: list[EscalationSignal]) -> dict[str, str]:
    totals: dict[str, int] = {}
    for signal in signals:
        totals[signal.dimension] = totals.get(signal.dimension, 0) + max(0, signal.weight)
    return {dimension: _dimension_level(weight) for dimension, weight in sorted(totals.items())}


def _dimension_level(weight: int) -> str:
    if weight <= 0:
        return "none"
    if weight < 20:
        return "low"
    if weight < 40:
        return "medium"
    return "high"


def _signal_reasons(signals: list[EscalationSignal]) -> list[str]:
    reasons: list[str] = []
    for signal in signals:
        if signal.id not in reasons:
            reasons.append(signal.id)
    return reasons


def _signal_rationale(signals: list[EscalationSignal]) -> list[str]:
    rationale: list[str] = []
    for signal in signals:
        if signal.evidence not in rationale:
            rationale.append(signal.evidence)
    return rationale


def _semantic_boundaries_from_audit(audit: Mapping[str, Any]) -> set[str]:
    boundaries: set[str] = set()
    details = _mapping(audit.get("details"))
    for item in details.get("semantic_boundaries", []) if isinstance(details.get("semantic_boundaries"), list) else []:
        if isinstance(item, Mapping):
            boundary = item.get("boundary")
            if isinstance(boundary, str):
                boundaries.add(boundary)
    for finding in _findings(audit):
        value = finding.get("semantic_boundaries")
        if isinstance(value, list):
            boundaries.update(item for item in value if isinstance(item, str))
    return boundaries


def _findings(audit: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    findings = audit.get("findings", [])
    if not isinstance(findings, list):
        return []
    return [finding for finding in findings if isinstance(finding, Mapping)]


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _string(value: object) -> str:
    return value if isinstance(value, str) else ""


def _truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return bool(value)
