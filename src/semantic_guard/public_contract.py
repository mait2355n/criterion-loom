"""Explicit projection from internal audit state to the closed public contract.

The engine models are intentionally smaller than the public evidence contract.
This module is the only place where the missing envelope material is made
explicit.  It never upgrades analyzer candidates to support, never releases a
hold, and never presents workflow ``pass`` as human acceptance.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from functools import lru_cache
from pathlib import Path
import re
from typing import Any, Iterable

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

from ._version import __version__
from .engine import RequirementAuditReport
from .models import (
    Challenge,
    Coverage,
    DecisionRequest,
    EvidenceRef,
    EvidenceRole,
    GuardCoverage,
    Hold,
    ObligationResult,
    SourceSpan,
)
from .reassessment import validate_reassessment_trace
from .providers import AnalysisAttempt
from .schema_access import schema_directory as _shared_schema_directory


SCHEMA_VERSION = "semantic-guard-audit-result/v0"
KNOWN_SCHEMA_NAMES = frozenset(
    {
        "action-assurance-profile",
        "action-evidence",
        "analysis-provider",
        "assurance-claim",
        "assurance-claim-v1",
        "audit-result",
        "common",
        "decision-request",
        "direction-binding-audit",
        "evidence-validity-policy",
        "field-evaluation",
        "field-sample-intake",
        "lifecycle-profile-registry",
        "lifecycle-trace",
        "llm-candidate-input",
        "obligation-result",
        "operational-outcome-evaluation",
        "operational-qualification",
        "repair-cycle",
        "responsibility-material",
        "responsibility-policy",
        "secure-operation",
        "state-assessment",
        "subject-manifest",
        "transition-plan",
    }
)
_STABLE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}$")
_ASSURANCE_V1_RUNTIME_TOKEN = object()
_REASSESSMENT_POLICY_ID = "obligation-reassessment-policy/v0"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _ref(
    entity_id: str,
    label: str,
    *,
    version: str | None = None,
    role: str | None = None,
    kind: str = "ref",
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "reference_kind": kind,
        "entity_id": _stable_id(entity_id, "entity"),
        "label_hint": label or entity_id,
    }
    if version:
        value["entity_version"] = version
    if role:
        value["role"] = role
    return value


def _stable_id(value: str, prefix: str) -> str:
    candidate = str(value)
    if _STABLE_ID.fullmatch(candidate):
        return candidate
    digest = hashlib.sha256(candidate.encode("utf-8")).hexdigest()[:24]
    return f"{prefix}.{digest}"


def _digest_value(report: RequirementAuditReport) -> str:
    prefix = "sha256:"
    if report.source_id.startswith(prefix):
        value = report.source_id[len(prefix) :]
        if len(value) == 64:
            return value
    return hashlib.sha256(report.record.source_text.encode("utf-8")).hexdigest()


def _source_ref(report: RequirementAuditReport) -> dict[str, Any]:
    return _ref(report.source_id, "audited requirement source", role="audit_subject")


def _profile_ref(report: RequirementAuditReport) -> dict[str, Any]:
    return _ref(
        report.profile_id,
        "functional requirement relation profile",
        version=report.profile_version,
        role="normative_profile",
    )


def _obligation_ref(obligation_id: str) -> dict[str, Any]:
    return _ref(obligation_id, obligation_id, role="profile_obligation")


def _scope_ref(scope_id: str) -> dict[str, Any]:
    if scope_id == "*":
        return _ref(
            "audit.all-obligations",
            "all obligations in this audit",
            role="audit_scope",
        )
    return _ref(scope_id, scope_id, role="audit_scope")


def _span_id(span: SourceSpan, digest: str) -> str:
    seed = f"{span.source_id}:{span.start}:{span.end}:{digest}"
    return "span." + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]


def _public_span(
    span: SourceSpan,
    *,
    report: RequirementAuditReport,
) -> dict[str, Any]:
    digest = _digest_value(report)
    return {
        "span_id": _span_id(span, digest),
        "source_ref": _source_ref(report),
        "coordinate_unit": "unicode_code_point",
        "start": span.start,
        "end_exclusive": span.end,
        "excerpt": span.text or report.record.source_text[span.start : span.end],
        # The projector has the invocation text and emits the matching excerpt,
        # but the standalone public validator receives only this envelope.  It
        # can check digest/reference consistency and duplicate-span agreement;
        # it must not pretend to recompute the excerpt without the source text.
        "excerpt_verification": "not_reverified_without_source_text",
        "source_digest": {"algorithm": "sha256", "value": digest},
    }


def _audit_observation_id(
    report: RequirementAuditReport,
    *,
    recorded_at: str,
) -> str:
    """Identify one observed audit projection, not merely its source text.

    The subject keeps its content-derived identity.  The audit identity binds
    the observation time, analysis/profile configuration visible in the
    report, provider and resource versions, candidate material, and resulting
    decision state.  Replaying the exact same recorded observation is stable;
    changing the mode, provider/resource, result, or timestamp is not.
    """

    material = {
        "producer": {
            "entity_id": "semantic-guard",
            "version": __version__,
        },
        "recorded_at": recorded_at,
        "subject_id": report.source_id,
        "profile": {
            "id": report.profile_id,
            "version": report.profile_version,
        },
        "analysis_mode": report.analysis_mode,
        "direct_rules": [
            {
                "obligation_id": item.obligation_id,
                "rule_id": item.rule_id,
                "outcome": item.outcome,
                "evidence_spans": item.evidence_spans,
                "basis": item.basis,
                "unknown_reasons": item.unknown_reasons,
            }
            for item in report.direct_assessments
        ],
        "analysis_attempts": [
            {
                "stage": item.stage,
                "provider_id": item.provider_id,
                "provider_version": item.provider_version,
                "resource_version": item.resource_version,
                "status": item.status,
                "requested_capabilities": item.requested_capabilities,
                "fulfilled_capabilities": item.fulfilled_capabilities,
                "covered_spans": [
                    (span.start, span.end, span.role) for span in item.covered_spans
                ],
                "tokens": [
                    (
                        token.surface,
                        token.lemma,
                        token.normalized,
                        token.part_of_speech,
                        token.start,
                        token.end,
                        token.features,
                    )
                    for token in item.tokens
                ],
                "relations": [
                    (
                        relation.relation_kind,
                        relation.from_span.start,
                        relation.from_span.end,
                        relation.to_span.start,
                        relation.to_span.end,
                        relation.confidence,
                        relation.interpretation_id,
                        relation.rationale,
                    )
                    for relation in item.relations
                ],
                "scopes": [
                    (
                        scope.scope_kind,
                        scope.cue_span.start,
                        scope.cue_span.end,
                        scope.target_span.start if scope.target_span else None,
                        scope.target_span.end if scope.target_span else None,
                        scope.confidence,
                    )
                    for scope in item.scopes
                ],
                "diagnostics": item.diagnostics,
            }
            for item in report.analysis_attempts
        ],
        "provider_execution_receipts": [
            item.as_dict() for item in report.provider_execution_receipts
        ],
        "obligation_reassessments": [
            item.as_dict() for item in report.obligation_reassessments
        ],
        "analyzer_qualifications": [
            item.as_dict() for item in report.analyzer_qualifications
        ],
        "initial_unresolved_obligations": [
            item.as_dict() for item in report.initial_unresolved_obligations
        ],
        "remaining_unresolved_obligations": [
            item.as_dict() for item in report.remaining_unresolved_obligations
        ],
        "result": {
            "outcome": report.result.outcome.value,
            "finality": report.result.finality.value,
            "challenge": report.result.challenge.value,
            "coverage": report.result.coverage.value,
            "workflow": report.result.workflow.value,
            "obligations": [
                (
                    item.obligation_id,
                    item.active,
                    item.required,
                    item.outcome.value,
                    item.finality.value,
                    item.challenge.value,
                    item.coverage.status.value,
                    tuple(hold.hold_id for hold in item.open_holds),
                )
                for item in report.result.obligations
            ],
            "provider_failures": report.result.execution.provider_failures,
            "integrity_failures": report.result.execution.integrity_failures,
            "decision_request_ids": tuple(
                item.request_id for item in report.result.decision_requests
            ),
        },
    }
    canonical = json.dumps(
        material,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "audit." + hashlib.sha256(canonical).hexdigest()


def _input_provenance(report: RequirementAuditReport, recorded_at: str) -> dict[str, Any]:
    return {
        "provenance_id": f"provenance.input.{_digest_value(report)[:20]}",
        "kind": "input",
        "source_ref": _source_ref(report),
        "recorded_at": recorded_at,
        "trust_class": "locally_observed",
        "trust_assumptions": [
            "Offsets and digest describe the exact text supplied to this audit invocation."
        ],
        "content_digest": {"algorithm": "sha256", "value": _digest_value(report)},
    }


def _producer_provenance(recorded_at: str) -> dict[str, Any]:
    """Identify the software release that emitted this closed audit envelope."""

    return {
        "provenance_id": f"provenance.producer.semantic-guard.{__version__}",
        "kind": "tool_output",
        "source_ref": _ref(
            "semantic-guard",
            "semantic-guard audit producer",
            version=__version__,
            role="audit_producer",
        ),
        "recorded_at": recorded_at,
        "trust_class": "tool_reported",
        "trust_assumptions": [
            "The producer version is self-reported by the installed semantic-guard package."
        ],
    }


def _evidence_ref(evidence: EvidenceRef) -> dict[str, Any]:
    return _ref(evidence.evidence_id, evidence.summary or evidence.evidence_id, role="audit_evidence")


def _evidence_provenance(
    evidence: EvidenceRef,
    *,
    recorded_at: str,
) -> dict[str, Any]:
    return {
        "provenance_id": _stable_id(
            f"provenance.{evidence.evidence_id}",
            "provenance",
        ),
        "kind": "rule_derivation",
        "source_ref": _ref(
            evidence.authority.stage_id,
            evidence.authority.stage_id,
            role="derivation_stage",
        ),
        "recorded_at": recorded_at,
        "trust_class": "tool_reported",
        "trust_assumptions": [
            "This record reports a version-bounded engine derivation, not independent corroboration."
        ],
    }


def _derivation_provenance(
    provenance_id: str,
    stage_id: str,
    *,
    recorded_at: str,
) -> dict[str, Any]:
    return {
        "provenance_id": _stable_id(provenance_id, "provenance"),
        "kind": "rule_derivation",
        "source_ref": _ref(stage_id, stage_id, role="derivation_stage"),
        "recorded_at": recorded_at,
        "trust_class": "tool_reported",
        "trust_assumptions": [
            "The derivation is valid only under the declared profile, rules, and observed input boundary."
        ],
    }


def _rights(evidence: EvidenceRef) -> dict[str, bool]:
    authority = evidence.authority
    return {
        "support": authority.support,
        "challenge": authority.challenge,
        "hold_apply": authority.hold_apply,
        "hold_release": authority.hold_release,
    }


def _effect(
    evidence: EvidenceRef,
    kind: str,
    scope_refs: list[dict[str, Any]],
    *,
    suffix: str = "",
) -> dict[str, Any]:
    basis = [evidence.evidence_id]
    if evidence.summary:
        basis.append(evidence.summary)
    scope_identity = ",".join(
        sorted(str(item["entity_id"]) for item in scope_refs)
    )
    scope_digest = hashlib.sha256(scope_identity.encode("utf-8")).hexdigest()[:12]
    return {
        "effect_id": _stable_id(
            f"effect.{kind}.{evidence.evidence_id}{suffix}.{scope_digest}",
            "effect",
        ),
        "kind": kind,
        "actor_ref": _ref(
            evidence.authority.stage_id,
            evidence.authority.stage_id,
            role="audit_stage",
        ),
        "authority_snapshot": _rights(evidence),
        "scope_refs": scope_refs,
        "basis": basis,
    }


def _evidence_effects(
    obligation: ObligationResult,
) -> list[dict[str, Any]]:
    scope = [_obligation_ref(obligation.obligation_id)]
    effects: list[dict[str, Any]] = []
    for evidence in obligation.provenance:
        if evidence.role is EvidenceRole.SUPPORT and evidence.authority.support:
            effects.append(_effect(evidence, "support", scope))
        elif (
            evidence.role in {EvidenceRole.CHALLENGE, EvidenceRole.SIGNAL}
            and (
                obligation.challenge is not Challenge.NONE
                or obligation.outcome.value == "refuted"
            )
            and evidence.authority.challenge
        ):
            effects.append(_effect(evidence, "challenge", scope))
    return effects


def _hold_effect(hold: Hold, *, suffix: str = "") -> dict[str, Any]:
    scope_refs = [_scope_ref(item) for item in hold.scope]
    return _effect(hold.applied_by, "hold_apply", scope_refs, suffix=suffix)


def _hold_effects(hold: Hold, *, suffix: str = "") -> list[dict[str, Any]]:
    effects = [_hold_effect(hold, suffix=suffix)]
    if hold.released_by is not None:
        effects.append(
            _effect(
                hold.released_by,
                "hold_release",
                [_scope_ref(item) for item in hold.scope],
                suffix=suffix,
            )
        )
    return effects


def _public_hold(hold: Hold, *, suffix: str = "") -> dict[str, Any]:
    payload: dict[str, Any] = {
        "hold_id": _stable_id(hold.hold_id, "hold"),
        "status": "open" if hold.is_open else "released",
        "effect_scope": "satisfaction_claim",
        "affected_refs": [_scope_ref(item) for item in hold.scope],
        "reason": hold.reason,
        "applied_by": _hold_effect(hold, suffix=suffix),
        "release_conditions": list(hold.release_conditions),
        "release_evidence_refs": [],
    }
    if hold.released_by is not None:
        payload["released_by"] = _effect(
            hold.released_by,
            "hold_release",
            payload["affected_refs"],
            suffix=suffix,
        )
        payload["release_evidence_refs"] = [_evidence_ref(hold.released_by)]
    return payload


def _guard_ref(name: str) -> dict[str, Any]:
    return _ref(f"guard.{name}", name, role="required_guard")


def _coverage(
    coverage: GuardCoverage,
    *,
    scope_refs: list[dict[str, Any]],
) -> dict[str, Any]:
    required = list(coverage.required_checks)
    completed = list(coverage.completed_checks)
    missing = [item for item in required if item not in set(completed)]
    return {
        "status": coverage.status.value,
        "scope_refs": scope_refs,
        "evaluated_item_refs": [_guard_ref(item) for item in completed],
        "not_evaluated_item_refs": [_guard_ref(item) for item in missing],
        "unobserved_ranges": [
            {
                "range_id": f"unobserved.guard.{item}",
                "description": f"Required guard was not closed: {item}",
                "reason": next(
                    (
                        reason
                        for reason in coverage.unresolved_reasons
                        if item in reason
                    ),
                    "No assertion-capable result closed this required guard.",
                ),
                "source_spans": [],
            }
            for item in missing
        ],
        "required_analyzer_refs": [_guard_ref(item) for item in required],
        "completed_analyzer_refs": [_guard_ref(item) for item in completed],
        "failed_analyzer_refs": (
            [_guard_ref(item) for item in missing]
            if coverage.status is Coverage.FAILED
            else []
        ),
    }


def _unknown_reason(reason: str) -> str:
    lowered = reason.casefold()
    if "applicab" in lowered or "profile" in lowered:
        return "applicability_unknown"
    if "record_boundary" in lowered or "multiple_record" in lowered:
        return "record_boundary_unknown"
    if "input_boundary" in lowered or "unconsumed" in lowered:
        return "input_boundary_open"
    if "provider_contract" in lowered:
        return "provider_contract_invalid"
    if "provider" in lowered and ("failed" in lowered or "unavailable" in lowered):
        return "analyzer_failed"
    if "not_configured" in lowered or "not_run" in lowered:
        return "analyzer_unavailable"
    if "conflict" in lowered:
        return "conflicting_evidence"
    if "authority" in lowered:
        return "authority_insufficient"
    if "integrity" in lowered or "invalid" in lowered:
        return "integrity_failure"
    if "missing" in lowered or "required_endpoint" in lowered:
        return "required_evidence_missing"
    if "interpret" in lowered or "ambiguous" in lowered or "scope" in lowered:
        return "multiple_interpretations"
    if "guard_not_closed" in lowered or "unobserved" in lowered:
        return "unobserved_range"
    return "other"


def _rule(
    report: RequirementAuditReport,
    obligation: ObligationResult,
) -> dict[str, Any]:
    assessment = next(
        item for item in report.direct_assessments if item.obligation_id == obligation.obligation_id
    )
    if assessment.outcome == "not_applicable":
        applicability = "not_applicable"
    elif assessment.outcome == "invalid":
        applicability = "conflict"
    elif assessment.outcome == "unresolved":
        applicability = "unknown"
    else:
        applicability = "applicable"
    proof_effect = {
        "supported": "support",
        "refuted": "refute",
        "not_applicable": "support",
        "unresolved": "none",
        "invalid": "challenge",
    }[assessment.outcome]
    evidence_refs = [_evidence_ref(item) for item in obligation.provenance]
    return {
        "rule_ref": _ref(assessment.rule_id, assessment.rule_id, role="audit_rule"),
        "rule_version": "v0",
        "applicability": applicability,
        "counterconditions": list(assessment.unknown_reasons),
        "required_evidence_refs": evidence_refs,
        "proof_effect": proof_effect,
    }


def _interpretation(
    report: RequirementAuditReport,
    obligation: ObligationResult,
) -> dict[str, Any]:
    supporting = [
        _evidence_ref(item)
        for item in obligation.provenance
        if item.role is EvidenceRole.SUPPORT and item.authority.support
    ]
    challenging = [
        _evidence_ref(item)
        for item in obligation.provenance
        if item.role in {EvidenceRole.CHALLENGE, EvidenceRole.SIGNAL}
    ]
    status = "adopted" if obligation.finality.value == "terminal" else "undetermined"
    return {
        "interpretation_id": f"interpretation.{obligation.obligation_id}",
        "proposition": (
            f"Under profile {report.profile_id}/{report.profile_version}, obligation "
            f"{obligation.obligation_id} has audit outcome {obligation.outcome.value}."
        ),
        "status": status,
        "source_spans": [
            _public_span(item, report=report) for item in obligation.source_spans
        ],
        "supporting_evidence_refs": supporting,
        "challenging_evidence_refs": challenging,
        "derived_from": [_profile_ref(report), _source_ref(report)],
    }


def _provider_candidate_interpretations(
    report: RequirementAuditReport,
    obligation: ObligationResult,
) -> list[dict[str, Any]]:
    """Preserve provider candidates named by the engine without adopting them.

    ``ObligationResult.interpretations`` contains candidate identities, while
    the provider attempts contain the candidate proposition and source spans.
    Joining them here keeps the public contract lossless at that boundary.  A
    candidate never receives supporting evidence merely because it survived
    the join.
    """

    requested_ids = tuple(dict.fromkeys(obligation.interpretations))
    if not requested_ids:
        return []

    by_id: dict[
        str,
        tuple[Any, str, str, list[dict[str, Any]]],
    ] = {}
    for attempt in report.analysis_attempts:
        for relation in attempt.relations:
            if relation.interpretation_id:
                provider_label = attempt.provider_id or "unknown-provider"
                provider_ref = _ref(
                    _stable_id(provider_label, "provider"),
                    provider_label,
                    version=attempt.provider_version or "unknown",
                    role="analysis_provider",
                )
                by_id.setdefault(
                    relation.interpretation_id,
                    (
                        relation,
                        provider_label,
                        attempt.provider_version or "unknown",
                        [provider_ref, _source_ref(report)],
                    ),
                )
    for projection in report.dependency_projections:
        relation = projection.candidate
        if not relation.interpretation_id:
            continue
        provider_label = projection.provider_id or "unknown-provider"
        provider_ref = _ref(
            _stable_id(provider_label, "provider"),
            provider_label,
            version=projection.provider_version or "unknown",
            role="analysis_provider",
        )
        by_id[relation.interpretation_id] = (
            relation,
            provider_label,
            projection.provider_version or "unknown",
            [
                _ref(
                    projection.projection_id,
                    projection.projection_id,
                    role="dependency_projection",
                    kind="derived_from",
                ),
                _ref(
                    projection.rule_id,
                    projection.rule_id,
                    role="projection_rule",
                ),
                provider_ref,
                _source_ref(report),
            ],
        )

    interpretations: list[dict[str, Any]] = []
    for candidate_id in requested_ids:
        found = by_id.get(candidate_id)
        if found is None:
            # Preserve the engine's identity even if a future candidate source
            # is not an AnalysisAttempt relation.  The absence of a provider
            # join remains visible and grants no evidentiary authority.
            interpretations.append(
                {
                    "interpretation_id": _stable_id(candidate_id, "interpretation"),
                    "proposition": (
                        f"Candidate interpretation {candidate_id} was retained for "
                        f"obligation {obligation.obligation_id}, but its provider "
                        "material was not available to this public projection."
                    ),
                    "status": "candidate",
                    "source_spans": [
                        _public_span(item, report=report)
                        for item in obligation.source_spans
                    ],
                    "supporting_evidence_refs": [],
                    "challenging_evidence_refs": [],
                    "derived_from": [_source_ref(report), _profile_ref(report)],
                }
            )
            continue

        relation, _provider_label, _provider_version, derived_from = found
        candidate_spans = [
            item
            for span in (relation.from_span, relation.to_span)
            if (item := _analysis_span(report, span.start, span.end)) is not None
        ]
        interpretations.append(
            {
                "interpretation_id": _stable_id(candidate_id, "interpretation"),
                "proposition": relation.rationale
                or (
                    f"Provider candidate relation {relation.relation_kind} was "
                    f"retained for obligation {obligation.obligation_id}; it was not adopted."
                ),
                "status": "candidate",
                "source_spans": _dedupe(candidate_spans, "span_id"),
                "supporting_evidence_refs": [],
                "challenging_evidence_refs": [],
                "derived_from": derived_from,
            }
        )
    return interpretations


def _risk(
    risk_id: str,
    description: str,
    affected_refs: list[dict[str, Any]],
    *,
    category: str = "semantic_audit_limitation",
    evidence_refs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "risk_id": _stable_id(risk_id, "risk"),
        "category": category,
        "severity": "unknown",
        "description": description or "Unspecified residual audit risk.",
        "affected_refs": affected_refs,
        "basis_evidence_refs": evidence_refs or [],
        "disposition": "open",
    }


def _obligation_risks(obligation: ObligationResult) -> list[dict[str, Any]]:
    affected = [_obligation_ref(obligation.obligation_id)]
    evidence = [_evidence_ref(item) for item in obligation.provenance]
    return [
        _risk(
            f"risk.{obligation.obligation_id}.{index}",
            description,
            affected,
            evidence_refs=evidence,
        )
        for index, description in enumerate(obligation.residual_risks, start=1)
    ]


def _obligation_payload(
    report: RequirementAuditReport,
    obligation: ObligationResult,
    *,
    recorded_at: str,
) -> dict[str, Any]:
    interpretation = _interpretation(report, obligation)
    candidate_interpretations = _provider_candidate_interpretations(report, obligation)
    supporting = [
        _evidence_ref(item)
        for item in obligation.provenance
        if item.role is EvidenceRole.SUPPORT and item.authority.support
    ]
    challenges = [
        _evidence_ref(item)
        for item in obligation.provenance
        if item.role in {EvidenceRole.CHALLENGE, EvidenceRole.SIGNAL}
        and item.authority.challenge
    ]
    refuting = challenges if obligation.outcome.value == "refuted" else []
    if obligation.challenge is not Challenge.NONE and not challenges:
        challenges = [
            _ref(
                f"evidence.unresolved.{obligation.obligation_id}",
                "Unresolved obligation state emitted by fail-closed aggregation",
                role="audit_evidence",
            )
        ]
    effects = _evidence_effects(obligation)
    if obligation.challenge is not Challenge.NONE and not any(
        item["kind"] == "challenge" for item in effects
    ):
        # This records the aggregation policy's challenge effect.  It does not
        # attribute authority to a morphology/dependency/LLM provider.
        evidence = EvidenceRef(
            evidence_id=f"evidence.unresolved.{obligation.obligation_id}",
            role=EvidenceRole.CHALLENGE,
            authority=next(
                (
                    item.authority
                    for item in obligation.provenance
                    if item.authority.challenge
                ),
                obligation.holds[0].applied_by.authority if obligation.holds else None,
            )
            or _projection_policy_authority(),
            source_ref=report.source_id,
            summary="Fail-closed aggregation retained an unresolved challenge.",
        )
        effects.append(_effect(evidence, "challenge", [_obligation_ref(obligation.obligation_id)]))
    effects.extend(
        effect
        for hold in obligation.holds
        for effect in _hold_effects(hold)
    )
    provenance = [_input_provenance(report, recorded_at)]
    provenance.extend(
        _evidence_provenance(item, recorded_at=recorded_at)
        for item in obligation.provenance
    )
    provenance.append(
        _derivation_provenance(
            f"provenance.obligation.{obligation.obligation_id}",
            "public-contract-projection/v0",
            recorded_at=recorded_at,
        )
    )
    unknown_reasons = list(dict.fromkeys(_unknown_reason(item) for item in obligation.unknown_reasons))
    if obligation.outcome.value == "undetermined" and not unknown_reasons:
        unknown_reasons = ["other"]
    return {
        "schema_version": "obligation-result/v0",
        "obligation_id": obligation.obligation_id,
        "profile_ref": _profile_ref(report),
        "subject_ref": _source_ref(report),
        "active": obligation.active,
        "required": obligation.required,
        "outcome": obligation.outcome.value,
        "finality": obligation.finality.value,
        "challenge": obligation.challenge.value,
        "interpretations": [interpretation, *candidate_interpretations],
        "supporting_evidence_refs": supporting,
        "refuting_evidence_refs": refuting,
        "challenging_evidence_refs": challenges,
        "rules": [_rule(report, obligation)],
        "unknown_reasons": unknown_reasons,
        "coverage": _coverage(
            obligation.coverage,
            scope_refs=[_obligation_ref(obligation.obligation_id)],
        ),
        "residual_risks": _obligation_risks(obligation),
        "holds": [_public_hold(item) for item in obligation.holds],
        "open_hold_ids": [
            _stable_id(item.hold_id, "hold") for item in obligation.open_holds
        ],
        "source_spans": [
            _public_span(item, report=report) for item in obligation.source_spans
        ],
        "provenance": _dedupe(provenance, "provenance_id"),
        "authority_effects": _dedupe(effects, "effect_id"),
    }


def _projection_policy_authority():
    # Local import avoids broadening the public module's model surface.
    from .models import StageAuthority

    return StageAuthority.policy_authority("public-contract-projection/v0")


def _projection_hold(
    report: RequirementAuditReport,
    request: DecisionRequest,
) -> Hold:
    evidence = EvidenceRef(
        evidence_id=f"evidence.decision-hold.{request.request_id}",
        role=EvidenceRole.CHALLENGE,
        authority=_projection_policy_authority(),
        source_ref=report.source_id,
        summary="The internal unresolved decision state implies a satisfaction-claim hold.",
    )
    return Hold(
        hold_id=f"hold.decision.{request.request_id}",
        scope=request.affected_obligation_ids,
        reason="unresolved_decision_request",
        applied_by=evidence,
        release_conditions=request.resolution_conditions,
    )


def _decision_payload(
    report: RequirementAuditReport,
    request: DecisionRequest,
    obligation_payloads: dict[str, dict[str, Any]],
    *,
    audit_id: str,
    recorded_at: str,
) -> tuple[dict[str, Any], list[Hold]]:
    affected_internal = [
        item
        for item in report.result.obligations
        if item.obligation_id in set(request.affected_obligation_ids)
    ]
    holds = [item for obligation in affected_internal for item in obligation.holds]
    projection_holds: list[Hold] = []
    if not holds:
        generated = _projection_hold(report, request)
        holds = [generated]
        projection_holds.append(generated)

    evidence = request.detected_by[0] if request.detected_by else holds[0].applied_by
    provider_ref: dict[str, Any] | None = None
    if evidence.authority.stage_id.startswith("provider:"):
        provider_ref = _ref(
            evidence.authority.stage_id,
            evidence.authority.stage_id,
            role="analysis_provider",
        )
    issue_class = "conflicting_evidence" if request.epistemic_state == "conflict" else "missing_evidence"
    if any(item in report.result.execution.provider_failures for item in request.question_material):
        issue_class = "provider_failure"
    if any("record_boundary" in item or "input_boundary" in item for item in request.question_material):
        issue_class = "record_boundary_unknown"
    owner_resolution = request.required_authority == "requirement_owner_interpretation"
    required_authority = "source_owner" if owner_resolution else "bounded_technical_interpretation"
    resolution_kind = "select_interpretation" if owner_resolution else "acquire_evidence"

    affected_payloads = [obligation_payloads[item] for item in request.affected_obligation_ids]
    interpretations = _dedupe(
        [
            interpretation
            for item in affected_payloads
            for interpretation in item["interpretations"]
        ],
        "interpretation_id",
    )
    source_spans = _dedupe(
        [span for item in affected_payloads for span in item["source_spans"]],
        "span_id",
    )
    provenance = _dedupe(
        [record for item in affected_payloads for record in item["provenance"]],
        "provenance_id",
    )
    authority_effects = _dedupe(
        [effect for item in affected_payloads for effect in item["authority_effects"]]
        + [
            effect
            for item in holds
            for effect in _hold_effects(item, suffix=".decision")
        ],
        "effect_id",
    )
    risks = _dedupe(
        [risk for item in affected_payloads for risk in item["residual_risks"]],
        "risk_id",
    )
    unknowns = list(request.question_material) or [
        "The affected obligation remains unresolved under the current evidence and authority boundary."
    ]
    return (
        {
            "schema_version": "decision-request/v0",
            "decision_request_id": request.request_id,
            "audit_ref": _ref(audit_id, audit_id, role="originating_audit"),
            "subject_ref": _source_ref(report),
            "affected_obligation_refs": [
                _obligation_ref(item) for item in request.affected_obligation_ids
            ],
            "issue_class": issue_class,
            "epistemic_state": "conflict" if request.epistemic_state == "conflict" else "unknown",
            "detected_by": {
                "stage_ref": _ref(
                    evidence.authority.stage_id,
                    evidence.authority.stage_id,
                    role="detection_stage",
                ),
                "provider_ref": provider_ref,
                "result": (
                    "conflict"
                    if request.epistemic_state == "conflict"
                    else "hold" if holds else "unknown"
                ),
                "authority_rights": _rights(evidence),
            },
            "decision_need": {
                "resolution_kind": resolution_kind,
                "proposition": (
                    "Determine whether the available source-aligned evidence and adopted "
                    f"interpretation close: {', '.join(request.affected_obligation_ids)}."
                ),
                "required_authority": required_authority,
            },
            "resolution_conditions": list(request.resolution_conditions),
            "agent_work_candidates": [
                {
                    "candidate_id": f"candidate.{request.request_id}.{index}",
                    "action": action,
                    "required_authority": "read_only",
                    "side_effect_class": "none",
                    "reaudit_required": True,
                }
                for index, action in enumerate(request.agent_work_candidates, start=1)
            ],
            "audit_holds": [_public_hold(item, suffix=".decision") for item in holds],
            "question_material": {
                "facts": [
                    f"The audit emitted {request.epistemic_state} for the affected obligation set."
                ],
                "unknowns": unknowns,
                "options": list(request.agent_work_candidates),
                "tradeoffs": [
                    "Proceeding without closure preserves speed but cannot justify a satisfaction claim.",
                    "Acquiring source-aligned evidence costs work but may close the audit hold."
                ],
                "recommended_question": None,
            },
            "interpretations": interpretations,
            "coverage": _coverage(
                affected_internal[0].coverage,
                scope_refs=[_obligation_ref(item) for item in request.affected_obligation_ids],
            ),
            "residual_risks": risks,
            "source_spans": source_spans,
            "provenance": provenance or [_input_provenance(report, recorded_at)],
            "authority_effects": authority_effects,
            "routing_boundary": {
                "semantic_guard_role": "emit_audit_material_only",
                "routing_owner": "external_caller_or_control_plane",
                "is_control_decision": False,
                "is_authority_grant": False,
                "is_human_question": False,
            },
        },
        projection_holds,
    )


def _analysis_span(
    report: RequirementAuditReport,
    start: int,
    end: int,
) -> dict[str, Any] | None:
    if end <= start:
        return None
    return _public_span(
        SourceSpan(
            source_id=report.source_id,
            start=start,
            end=end,
            text=report.record.source_text[start:end],
        ),
        report=report,
    )


def _analysis_payload(
    report: RequirementAuditReport,
    attempt: AnalysisAttempt,
    *,
    index: int,
    recorded_at: str,
) -> dict[str, Any]:
    provider_kind = {
        "morphology": "morphology",
        "dependency_parse": "dependency",
        "llm_candidate": "llm",
    }[attempt.stage]
    status = {
        "ok": "complete",
        "partial": "partial",
        "failed": "failed",
        "not_configured": "unavailable",
    }[attempt.status]
    provider_label = attempt.provider_id or "unknown-provider"
    provider_id = _stable_id(provider_label, "provider")
    provider_ref = _ref(provider_id, provider_label, role="analysis_provider")
    stage_ref = _ref(f"stage.{attempt.stage}", attempt.stage, role="analysis_stage")
    source_spans = [
        item
        for span in attempt.covered_spans
        if (item := _analysis_span(report, span.start, span.end)) is not None
    ]
    interpretations = []
    for relation_index, relation in enumerate(attempt.relations, start=1):
        relation_spans = [
            item
            for candidate_span in (relation.from_span, relation.to_span)
            if (
                item := _analysis_span(
                    report,
                    candidate_span.start,
                    candidate_span.end,
                )
            )
            is not None
        ]
        interpretations.append(
            {
                "interpretation_id": _stable_id(
                    relation.interpretation_id
                    or f"interpretation.provider.{index}.{relation_index}",
                    "interpretation",
                ),
                "proposition": relation.rationale
                or f"Candidate relation {relation.relation_kind} was emitted by {provider_id}.",
                "status": "candidate",
                "source_spans": relation_spans,
                "supporting_evidence_refs": [],
                "challenging_evidence_refs": [],
                "derived_from": [provider_ref, _source_ref(report)],
            }
        )
    rights = {
        "support": False,
        "challenge": attempt.authority.challenge_signal,
        "hold_apply": False,
        "hold_release": False,
    }
    coverage_status = {
        "ok": "complete",
        "partial": "partial",
        "failed": "failed",
        "not_configured": "not_evaluated",
    }[attempt.status]
    provider_risks = []
    if attempt.status != "ok":
        provider_risks.append(
            _risk(
                f"risk.provider.{index}.{attempt.status}",
                "; ".join(attempt.diagnostics)
                or f"Provider execution ended with status {attempt.status}.",
                [provider_ref],
                category="analysis_provider_execution",
            )
        )
    provenance_kind = "model_output" if provider_kind == "llm" else "tool_output"
    provenance = {
        "provenance_id": f"provenance.provider.{index}.{provider_id}",
        "kind": provenance_kind,
        "source_ref": provider_ref,
        "recorded_at": recorded_at,
        "trust_class": "tool_reported",
        "trust_assumptions": [
            "Provider output is retained as a candidate or signal and has no implicit support or hold authority."
        ],
    }
    return {
        "schema_version": "analysis-provider/v0",
        "decision_influence": (
            "shadow_observation"
            if report.analysis_mode == "shadow_all"
            else "effective"
        ),
        "provider_id": provider_id,
        "provider_kind": provider_kind,
        "provider_version": attempt.provider_version or "unknown",
        "resource_version": attempt.resource_version or "unknown",
        "implementation_ref": _ref(
            f"implementation.{provider_id}",
            provider_id,
            version=attempt.provider_version or "unknown",
            role="provider_implementation",
        ),
        "determinism": "model_backed" if provider_kind == "llm" else "unknown",
        "maximum_evidentiary_authority": (
            "signal_only" if provider_kind == "morphology" else "candidate_only"
        ),
        "authority_rights": rights,
        "input_contract": {
            "accepted_media_types": ["text/plain; charset=utf-8"],
            "requires_closed_record": False,
            "requires_source_digest": True,
        },
        "output_contract": {
            "requires_source_spans": True,
            "requires_provenance": True,
            "preserves_multiple_interpretations": True,
            "may_emit_relation_candidates": provider_kind != "morphology",
            "raw_output_may_satisfy_obligation": False,
            "lifting_rule_required_for_support": True,
        },
        "failure_policy": {
            "on_not_run": "emit_unknown_and_hold_when_required",
            "on_unavailable": "emit_unknown_and_hold_when_required",
            "on_failure": "emit_unknown_and_hold_when_required",
            "on_invalid_output": "invalidate_provider_result_and_hold",
        },
        "execution": {
            "execution_id": f"provider-execution.{index}.{provider_id}",
            "status": status,
            "started_at": None,
            "finished_at": None,
            "input_digest": {"algorithm": "sha256", "value": _digest_value(report)},
            "requested_capabilities": list(attempt.requested_capabilities),
            "fulfilled_capabilities": list(attempt.fulfilled_capabilities),
            "missing_capabilities": list(attempt.missing_capabilities),
            "diagnostics": [item for item in attempt.diagnostics if item],
            "unknown_effect": (
                "none"
                if status == "complete"
                else "emit_unknown_and_hold_when_required"
            ),
        },
        "interpretations": interpretations,
        "coverage": {
            "status": coverage_status,
            "scope_refs": [_source_ref(report)],
            "evaluated_item_refs": [stage_ref] if attempt.status in {"ok", "partial"} else [],
            "not_evaluated_item_refs": [stage_ref] if attempt.status == "not_configured" else [],
            "unobserved_ranges": [],
            "required_analyzer_refs": [provider_ref],
            "completed_analyzer_refs": [provider_ref] if attempt.status == "ok" else [],
            "failed_analyzer_refs": [provider_ref] if attempt.status in {"failed", "not_configured"} else [],
        },
        "residual_risks": provider_risks,
        "source_spans": _dedupe(source_spans, "span_id"),
        "provenance": [provenance],
        "authority_effects": [],
    }


def _shadow_observation(
    report: RequirementAuditReport,
    signal: Any,
) -> dict[str, Any]:
    source_spans = []
    if signal.end > signal.start:
        source_spans.append(
            _public_span(
                SourceSpan(
                    source_id=report.source_id,
                    start=signal.start,
                    end=signal.end,
                    text=signal.excerpt,
                ),
                report=report,
            )
        )
    return {
        "observation_id": _stable_id(signal.signal_id, "shadow-observation"),
        "reason_code": _stable_id(signal.reason_code, "reason"),
        "category": signal.category,
        "detected_by_ref": _ref(
            signal.detected_by,
            signal.detected_by,
            role="observation_source",
        ),
        "next_route": signal.next_route,
        "source_spans": source_spans,
        "limitations": list(signal.limitations),
        "decision_influence": "none",
    }


def _aggregate_interpretation(
    report: RequirementAuditReport,
    obligation_payloads: list[dict[str, Any]],
    *,
    audit_id: str,
) -> dict[str, Any]:
    support = _dedupe(
        [item for payload in obligation_payloads for item in payload["supporting_evidence_refs"]],
        "entity_id",
    )
    challenge = _dedupe(
        [item for payload in obligation_payloads for item in payload["challenging_evidence_refs"]],
        "entity_id",
    )
    return {
        "interpretation_id": f"interpretation.{audit_id}",
        "proposition": (
            f"Under {report.profile_id}/{report.profile_version}, this bounded audit concluded "
            f"{report.result.outcome.value}; workflow disposition is {report.result.workflow.value}, "
            "which is not human acceptance."
        ),
        "status": (
            "adopted" if report.result.finality.value == "terminal" else "undetermined"
        ),
        "source_spans": _dedupe(
            [span for payload in obligation_payloads for span in payload["source_spans"]],
            "span_id",
        ),
        "supporting_evidence_refs": support,
        "challenging_evidence_refs": challenge,
        "derived_from": [_profile_ref(report), _source_ref(report)],
    }


def _assurance_claim(
    report: RequirementAuditReport,
    obligation_payloads: list[dict[str, Any]],
    aggregate_interpretation: dict[str, Any],
    coverage: dict[str, Any],
    risks: list[dict[str, Any]],
    holds: list[dict[str, Any]],
    provenance: list[dict[str, Any]],
    authority_effects: list[dict[str, Any]],
    *,
    audit_id: str,
    recorded_at: str,
) -> dict[str, Any]:
    support = _dedupe(
        [item for payload in obligation_payloads for item in payload["supporting_evidence_refs"]],
        "entity_id",
    )
    challenge = _dedupe(
        [item for payload in obligation_payloads for item in payload["challenging_evidence_refs"]],
        "entity_id",
    )
    unproven = []
    if report.result.outcome.value == "undetermined":
        unproven.append(
            {
                "range_id": f"unproven.{audit_id}",
                "description": "Required obligation scope not closed by the current audit.",
                "reason": "; ".join(report.result.reasons)
                or "At least one required obligation, guard, or provider stage remains unresolved.",
                "source_spans": aggregate_interpretation["source_spans"],
            }
        )
    return {
        "schema_version": "assurance-claim/v0",
        "claim_id": f"claim.{audit_id}",
        "subject_ref": _source_ref(report),
        "claim_kind": "requirement_conformance",
        "proposition": aggregate_interpretation["proposition"],
        "scope": {
            "included_refs": [_source_ref(report), _profile_ref(report)],
            "excluded_refs": [],
            "time_boundary": f"single audit projection recorded at {recorded_at}",
            "environment_boundary": (
                "semantic-guard v1 process; no implementation, action-occurrence, external-state, "
                "or human-acceptance observation"
            ),
        },
        "outcome": report.result.outcome.value,
        "finality": report.result.finality.value,
        "challenge": report.result.challenge.value,
        "assurance_level": "derived_under_profile",
        "interpretations": [aggregate_interpretation],
        "rules": [rule for payload in obligation_payloads for rule in payload["rules"]],
        "supporting_evidence_refs": support,
        "challenging_evidence_refs": challenge,
        "trust_assumptions": [
            "Input digest and source offsets identify the audited text.",
            "Direct rules and the profile versions named in this envelope are the decision basis.",
            "Analyzer candidates do not independently establish satisfaction or release holds."
        ],
        "counterconditions": list(report.limitations),
        "coverage": coverage,
        "unproven_scope": unproven,
        "residual_risks": risks,
        "holds": holds,
        "open_hold_ids": [item["hold_id"] for item in holds if item["status"] == "open"],
        "source_spans": aggregate_interpretation["source_spans"],
        "provenance": provenance,
        "authority_effects": authority_effects,
    }


def _dedupe(values: Iterable[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for value in values:
        identity = str(value[key])
        if identity in seen:
            continue
        seen.add(identity)
        result.append(value)
    return result


def public_audit_payload(
    report: RequirementAuditReport,
    *,
    recorded_at: str | None = None,
    _runtime_derivation_token: object | None = None,
) -> dict[str, Any]:
    """Project an internal report into the versioned, closed public envelope.

    ``recorded_at`` is injectable so replay tests and durable audit records can
    control their observation timestamp.  The adapter creates a bounded
    assurance claim about this audit only; it emits no implementation or human
    acceptance claim.
    """

    if any(item.is_promotion for item in report.obligation_reassessments) and (
        _runtime_derivation_token is not _ASSURANCE_V1_RUNTIME_TOKEN
    ):
        raise ValueError(
            "audit-result/v0 cannot replay qualified reassessment support; "
            "request assurance-claim/v1 runtime derivation instead"
        )
    timestamp = recorded_at or _now()
    direct_by_id = {
        item.obligation_id: item for item in report.direct_assessments
    }
    initial_unresolved_by_id = {
        item.obligation_id: item for item in report.initial_unresolved_obligations
    }
    receipt_ids = {
        item.receipt_id for item in report.provider_execution_receipts
    }
    qualification_ids = {
        item.qualification_id for item in report.analyzer_qualifications
    }
    projection_ids = {
        item.projection_id for item in report.dependency_projections
    }
    if any(
        item.receipt_id not in receipt_ids
        for item in report.dependency_projections
    ):
        raise ValueError("dependency projection refers to an absent provider receipt")
    if report.unresolved_obligations != report.remaining_unresolved_obligations:
        raise ValueError("unresolved_obligations must equal the remaining route trace")
    for reassessment in report.obligation_reassessments:
        validate_reassessment_trace(
            reassessment,
            source_id=report.source_id,
            profile_id=report.profile_id,
            profile_version=report.profile_version,
            prior_assessment=direct_by_id[reassessment.obligation_id],
            initial_unresolved=initial_unresolved_by_id.get(
                reassessment.obligation_id
            ),
        )
        if not set(reassessment.receipt_ids).issubset(receipt_ids):
            raise ValueError("reassessment refers to an absent provider receipt")
        if not set(reassessment.qualification_ids).issubset(qualification_ids):
            raise ValueError("reassessment refers to an absent analyzer qualification")
        if not set(reassessment.projection_ids).issubset(projection_ids):
            raise ValueError("reassessment refers to an absent dependency projection")
    audit_id = _audit_observation_id(report, recorded_at=timestamp)
    obligation_payloads = [
        _obligation_payload(report, item, recorded_at=timestamp)
        for item in report.result.obligations
    ]
    by_obligation = {item["obligation_id"]: item for item in obligation_payloads}

    decision_payloads: list[dict[str, Any]] = []
    projection_holds: list[Hold] = []
    for request in report.result.decision_requests:
        payload, generated = _decision_payload(
            report,
            request,
            by_obligation,
            audit_id=audit_id,
            recorded_at=timestamp,
        )
        decision_payloads.append(payload)
        projection_holds.extend(generated)

    analysis_runs = [
        _analysis_payload(report, item, index=index, recorded_at=timestamp)
        for index, item in enumerate(report.analysis_attempts, start=1)
    ]
    shadow_observations = [
        _shadow_observation(report, item) for item in report.shadow_signals
    ]

    signal_spans = [
        _public_span(
            SourceSpan(
                source_id=report.source_id,
                start=item.start,
                end=item.end,
                text=item.excerpt,
            ),
            report=report,
        )
        for item in report.residual_signals
        if item.end > item.start
    ]
    shadow_spans = [
        span
        for observation in shadow_observations
        for span in observation["source_spans"]
    ]
    source_spans = _dedupe(
        [span for item in obligation_payloads for span in item["source_spans"]]
        + [span for item in analysis_runs for span in item["source_spans"]]
        + signal_spans
        + shadow_spans,
        "span_id",
    )
    execution_hold_provenance = [
        _evidence_provenance(item.applied_by, recorded_at=timestamp)
        for item in report.result.execution.holds
    ] + [
        _evidence_provenance(item.released_by, recorded_at=timestamp)
        for item in report.result.execution.holds
        if item.released_by is not None
    ]
    provenance = _dedupe(
        [_input_provenance(report, timestamp), _producer_provenance(timestamp)]
        + [record for item in obligation_payloads for record in item["provenance"]]
        + [record for item in analysis_runs for record in item["provenance"]]
        + execution_hold_provenance,
        "provenance_id",
    )
    shadow_provenance_ids = {
        record["provenance_id"]
        for item in analysis_runs
        if item["decision_influence"] == "shadow_observation"
        for record in item["provenance"]
    }
    assurance_provenance = [
        item
        for item in provenance
        if item["provenance_id"] not in shadow_provenance_ids
    ]
    authority_effects = _dedupe(
        [effect for item in obligation_payloads for effect in item["authority_effects"]]
        + [
            effect
            for item in report.result.execution.holds
            for effect in _hold_effects(item, suffix=".execution")
        ]
        + [
            effect
            for item in projection_holds
            for effect in _hold_effects(item, suffix=".projection")
        ],
        "effect_id",
    )

    effective_holds = _dedupe(
        [
            _public_hold(item, suffix=".execution")
            for item in report.result.execution.holds
        ]
        + [hold for item in obligation_payloads for hold in item["holds"]]
        + [_public_hold(item, suffix=".projection") for item in projection_holds],
        "hold_id",
    )
    open_hold_ids = [item["hold_id"] for item in effective_holds if item["status"] == "open"]

    risks = _dedupe(
        [risk for item in obligation_payloads for risk in item["residual_risks"]]
        + [
            _risk(
                item.signal_id,
                "; ".join((item.reason_code, *item.limitations)),
                [
                    _obligation_ref(obligation_id)
                    for obligation_id in sorted(
                        {
                            obligation.obligation_id
                            for obligation in report.result.obligations
                            if any(hold.reason == item.reason_code for hold in obligation.holds)
                        }
                    )
                ]
                or [_source_ref(report)],
                category=item.category,
                evidence_refs=[
                    _ref(
                        f"evidence.{item.signal_id}",
                        item.reason_code,
                        role="audit_evidence",
                    )
                ],
            )
            for item in report.residual_signals
        ]
        + [
            _risk(
                f"risk.aggregate.{index}",
                description,
                [_source_ref(report)],
            )
            for index, description in enumerate(report.result.residual_risks, start=1)
        ],
        "risk_id",
    )
    blocking_risk_ids = [
        item["risk_id"]
        for item in risks
        if open_hold_ids or report.result.challenge is not Challenge.NONE
    ]

    execution_coverage = _coverage(
        report.result.execution.coverage,
        scope_refs=[_source_ref(report), _profile_ref(report)],
    )
    top_coverage = dict(execution_coverage)
    top_coverage["status"] = report.result.coverage.value
    incomplete_required = [
        item
        for item in obligation_payloads
        if item["active"]
        and item["required"]
        and item["coverage"]["status"] != "complete"
    ]
    top_coverage["not_evaluated_item_refs"] = _dedupe(
        [*top_coverage["not_evaluated_item_refs"]]
        + [_obligation_ref(item["obligation_id"]) for item in incomplete_required],
        "entity_id",
    )
    top_coverage["unobserved_ranges"] = _dedupe(
        [*top_coverage["unobserved_ranges"]]
        + [
            unobserved
            for item in incomplete_required
            for unobserved in item["coverage"]["unobserved_ranges"]
        ],
        "range_id",
    )
    aggregate_interpretation = _aggregate_interpretation(
        report,
        obligation_payloads,
        audit_id=audit_id,
    )
    assurance_claim = _assurance_claim(
        report,
        obligation_payloads,
        aggregate_interpretation,
        top_coverage,
        risks,
        effective_holds,
        assurance_provenance,
        authority_effects,
        audit_id=audit_id,
        recorded_at=timestamp,
    )

    effective_attempts = (
        () if report.analysis_mode == "shadow_all" else report.analysis_attempts
    )
    attempted_refs = [
        _ref(f"stage.{item.stage}", item.stage, role="analysis_stage")
        for item in effective_attempts
    ]
    completed_refs = [
        _ref(f"stage.{item.stage}", item.stage, role="analysis_stage")
        for item in effective_attempts
        if item.status == "ok"
    ]
    not_evaluated_refs = [
        _ref(f"stage.{item.stage}", item.stage, role="analysis_stage")
        for item in effective_attempts
        if item.status == "not_configured"
    ]
    unresolved_required = [
        item.obligation_id
        for item in report.result.obligations
        if item.active
        and item.required
        and not (
            item.finality.value == "terminal"
            and item.outcome.value in {"satisfied", "not_applicable"}
            and item.challenge.value == "none"
        )
    ]
    reason_codes = [
        "reason." + hashlib.sha256(item.encode("utf-8")).hexdigest()[:20]
        for item in report.result.reasons
    ]
    presentation = {
        "met": [item.obligation_id for item in report.result.obligations if item.outcome.value == "satisfied"],
        "not_met": [item.obligation_id for item in report.result.obligations if item.outcome.value == "refuted"],
        "undetermined": [item.obligation_id for item in report.result.obligations if item.outcome.value == "undetermined"],
        "contested": [item.obligation_id for item in report.result.obligations if item.challenge.value != "none"],
        "not_applicable": [item.obligation_id for item in report.result.obligations if item.outcome.value == "not_applicable"],
        "not_evaluated": [
            item.obligation_id
            for item in report.result.obligations
            if item.coverage.status in {Coverage.NOT_EVALUATED, Coverage.FAILED}
        ],
    }
    limitations = list(report.limitations)
    limitations.extend(f"aggregation_reason:{item}" for item in report.result.reasons)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "audit_id": audit_id,
        "phase": "requirements_engineering",
        "analysis_mode": report.analysis_mode,
        "subject_ref": _source_ref(report),
        "profile_refs": [_profile_ref(report)],
        "audit_conclusion": {
            "outcome": report.result.outcome.value,
            "finality": report.result.finality.value,
            "challenge": report.result.challenge.value,
            "basis_refs": [
                _obligation_ref(item.obligation_id) for item in report.result.obligations
            ],
            "limitations": limitations,
        },
        "execution": {
            "started_at": timestamp,
            "finished_at": timestamp,
            "coverage": execution_coverage,
            "integrity_failure_ids": list(report.result.execution.integrity_failures),
            "required_provider_failure_ids": list(report.result.execution.provider_failures),
            "attempted_stage_refs": attempted_refs,
            "completed_stage_refs": completed_refs,
            "not_evaluated_stage_refs": not_evaluated_refs,
        },
        "workflow_disposition": {
            "status": report.result.workflow.value,
            "reason_codes": reason_codes,
            "semantics": "audit_rules_do_not_currently_stop_work_not_human_acceptance",
            "acceptance_owner": "human_external_to_semantic_guard",
        },
        "obligation_results": obligation_payloads,
        "assurance_claims": [assurance_claim],
        "analysis_runs": analysis_runs,
        "shadow_observations": shadow_observations,
        "decision_requests": decision_payloads,
        "interpretations": _dedupe(
            [aggregate_interpretation]
            + [
                interpretation
                for item in obligation_payloads
                for interpretation in item["interpretations"]
                if interpretation["status"] == "candidate"
            ],
            "interpretation_id",
        ),
        "coverage": top_coverage,
        "unresolved_required_obligation_ids": unresolved_required,
        "open_hold_ids": open_hold_ids,
        "blocking_residual_risk_ids": blocking_risk_ids,
        "residual_risks": risks,
        "source_spans": source_spans,
        "provenance": provenance,
        "authority_effects": authority_effects,
        "presentation": presentation,
    }
    return payload


def _public_audit_payload_for_assurance_v1(
    report: RequirementAuditReport,
    *,
    recorded_at: str | None = None,
) -> dict[str, Any]:
    return public_audit_payload(
        report,
        recorded_at=recorded_at,
        _runtime_derivation_token=_ASSURANCE_V1_RUNTIME_TOKEN,
    )


def _schema_directory() -> Path:
    return _shared_schema_directory(sentinel="audit-result.schema.json")


def load_public_schema(name: str = "audit-result") -> dict[str, Any]:
    if name not in KNOWN_SCHEMA_NAMES:
        raise ValueError(f"unknown schema name: {name}")
    path = _schema_directory() / f"{name}.schema.json"
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _validator() -> Draft202012Validator:
    resources: list[tuple[str, Resource[Any]]] = []
    root: dict[str, Any] | None = None
    for path in sorted(_schema_directory().glob("*.schema.json")):
        schema = json.loads(path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        resources.append((schema["$id"], Resource.from_contents(schema)))
        if path.name == "audit-result.schema.json":
            root = schema
    if root is None:
        raise FileNotFoundError("audit-result.schema.json is missing")
    registry = Registry().with_resources(resources)
    return Draft202012Validator(
        root,
        registry=registry,
        format_checker=FormatChecker(),
    )


def _walk(value: Any) -> Iterable[Any]:
    yield value
    if isinstance(value, dict):
        for item in value.values():
            yield from _walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk(item)


def _has_reassessment_support(payload: dict[str, Any]) -> bool:
    return any(
        effect.get("kind") == "support"
        and effect.get("actor_ref", {}).get("entity_id")
        == _REASSESSMENT_POLICY_ID
        for effect in payload.get("authority_effects", [])
    )


def _validate_public_audit(
    payload: dict[str, Any],
    *,
    allow_runtime_derivation: bool,
) -> None:
    """Validate schema, source spans, authority ceilings, and effect references.

    ``jsonschema.ValidationError`` is raised for contract violations.  Span
    ordering is a declared cross-field constraint that JSON Schema cannot
    express without an extension, so it is checked here and reported as a
    validation error as well.
    """

    from jsonschema import ValidationError

    _validator().validate(payload)
    if _has_reassessment_support(payload) and not allow_runtime_derivation:
        raise ValidationError(
            "audit-result/v0 cannot replay qualified reassessment support"
        )
    for item in _walk(payload):
        if (
            isinstance(item, dict)
            and item.get("coordinate_unit") in {
                "unicode_code_point",
                "utf8_byte",
                "token_index",
                "record_index",
            }
            and "start" in item
            and "end_exclusive" in item
            and item["end_exclusive"] < item["start"]
        ):
            raise ValidationError("source span end_exclusive must be >= start")

    _validate_source_span_consistency(payload, ValidationError)
    _validate_audit_state_consistency(payload, ValidationError)
    _validate_provider_capabilities(payload, ValidationError)
    _validate_analysis_authority(payload, ValidationError)
    _validate_hold_effect_references(payload, ValidationError)
    _validate_shadow_isolation(payload, ValidationError)


def validate_public_audit(payload: dict[str, Any]) -> None:
    """Validate a standalone v0 audit; hidden reassessment support is rejected."""

    _validate_public_audit(payload, allow_runtime_derivation=False)


def _validate_public_audit_for_assurance_v1(payload: dict[str, Any]) -> None:
    _validate_public_audit(payload, allow_runtime_derivation=True)


_COVERAGE_PRECEDENCE = {
    "complete": 0,
    "partial": 1,
    "not_evaluated": 2,
    "failed": 3,
}


def _validate_source_span_consistency(
    payload: dict[str, Any],
    error_type: type[Exception],
) -> None:
    subject_id = payload["subject_ref"]["entity_id"]
    input_provenance = [
        item
        for item in payload.get("provenance", [])
        if item.get("kind") == "input"
    ]
    if len(input_provenance) != 1:
        raise error_type("audit envelope must contain exactly one input provenance record")
    provenance = input_provenance[0]
    if provenance["source_ref"]["entity_id"] != subject_id:
        raise error_type("input provenance source_ref disagrees with audit subject_ref")
    digest = provenance.get("content_digest")
    if not isinstance(digest, dict) or digest.get("algorithm") != "sha256":
        raise error_type("input provenance must contain one sha256 content digest")
    digest_value = str(digest.get("value", "")).lower()
    if subject_id != f"sha256:{digest_value}":
        raise error_type("audit subject_ref does not match input provenance digest")

    spans_by_id: dict[str, dict[str, Any]] = {}
    for item in _walk(payload):
        if not isinstance(item, dict) or not {
            "span_id",
            "source_ref",
            "source_digest",
            "coordinate_unit",
            "start",
            "end_exclusive",
            "excerpt_verification",
        }.issubset(item):
            continue
        if item["source_ref"]["entity_id"] != subject_id:
            raise error_type(
                f"source span {item['span_id']} source_ref disagrees with audit subject_ref"
            )
        span_digest = item["source_digest"]
        if (
            span_digest.get("algorithm") != "sha256"
            or str(span_digest.get("value", "")).lower() != digest_value
        ):
            raise error_type(
                f"source span {item['span_id']} digest disagrees with input provenance"
            )
        expected_span_id = "span." + hashlib.sha256(
            (
                f"{subject_id}:{item['start']}:{item['end_exclusive']}:"
                f"{digest_value}"
            ).encode("utf-8")
        ).hexdigest()[:24]
        if item["span_id"] != expected_span_id:
            raise error_type(
                f"source span {item['span_id']} identity disagrees with its coordinates and digest"
            )
        prior = spans_by_id.setdefault(item["span_id"], item)
        if prior != item:
            raise error_type(
                f"source span {item['span_id']} has inconsistent duplicate material"
            )


def _open_hold_ids(container: dict[str, Any], field_name: str) -> list[str]:
    return [
        item["hold_id"]
        for item in container.get(field_name, [])
        if item["status"] == "open"
    ]


def _validate_audit_state_consistency(
    payload: dict[str, Any],
    error_type: type[Exception],
) -> None:
    obligations = payload["obligation_results"]
    obligation_ids = [item["obligation_id"] for item in obligations]
    if len(obligation_ids) != len(set(obligation_ids)):
        raise error_type("obligation_results contains duplicate obligation_id values")

    basis_ids = [item["entity_id"] for item in payload["audit_conclusion"]["basis_refs"]]
    if basis_ids != obligation_ids:
        raise error_type("audit conclusion basis_refs disagree with obligation_results")

    subject_id = payload["subject_ref"]["entity_id"]
    profile_ids = {item["entity_id"] for item in payload["profile_refs"]}
    for obligation in obligations:
        if obligation["subject_ref"]["entity_id"] != subject_id:
            raise error_type(
                f"obligation {obligation['obligation_id']} subject_ref disagrees with audit subject"
            )
        if obligation["profile_ref"]["entity_id"] not in profile_ids:
            raise error_type(
                f"obligation {obligation['obligation_id']} profile_ref is absent from profile_refs"
            )
        expected_local_holds = _open_hold_ids(obligation, "holds")
        if obligation["open_hold_ids"] != expected_local_holds:
            raise error_type(
                f"obligation {obligation['obligation_id']} open_hold_ids disagree with holds"
            )

    expected_unresolved = [
        item["obligation_id"]
        for item in obligations
        if item["active"]
        and item["required"]
        and not (
            item["outcome"] == "satisfied"
            and item["finality"] == "terminal"
            and item["challenge"] == "none"
            and item["coverage"]["status"] == "complete"
            and not item["open_hold_ids"]
        )
    ]
    if payload["unresolved_required_obligation_ids"] != expected_unresolved:
        raise error_type(
            "unresolved_required_obligation_ids disagree with active required obligations"
        )

    hold_statuses: dict[str, set[str]] = {}
    for item in _walk(payload):
        if not isinstance(item, dict):
            continue
        for field_name in ("holds", "audit_holds"):
            for hold in item.get(field_name, []):
                hold_statuses.setdefault(hold["hold_id"], set()).add(hold["status"])
    conflicting_holds = [
        hold_id for hold_id, statuses in hold_statuses.items() if len(statuses) > 1
    ]
    if conflicting_holds:
        raise error_type(
            "hold status disagrees across public projections: "
            + ", ".join(sorted(conflicting_holds))
        )
    expected_open_holds = [
        hold_id
        for hold_id, statuses in hold_statuses.items()
        if statuses == {"open"}
    ]
    if set(payload["open_hold_ids"]) != set(expected_open_holds):
        raise error_type("top-level open_hold_ids disagree with projected holds")
    for claim in payload["assurance_claims"]:
        if set(claim["open_hold_ids"]) != set(_open_hold_ids(claim, "holds")):
            raise error_type(
                f"assurance claim {claim['claim_id']} open_hold_ids disagree with holds"
            )
    active = [item for item in obligations if item["active"]]
    if any(item["challenge"] == "conflict" for item in active):
        expected_challenge = "conflict"
    elif expected_open_holds or any(item["challenge"] == "open" for item in active):
        expected_challenge = "open"
    else:
        expected_challenge = "none"
    if payload["audit_conclusion"]["challenge"] != expected_challenge:
        raise error_type("audit conclusion challenge disagrees with obligations and holds")

    execution_coverage = payload["execution"]["coverage"]["status"]
    coverage_states = [execution_coverage]
    coverage_states.extend(
        item["coverage"]["status"]
        for item in obligations
        if item["active"] and item["required"]
    )
    expected_coverage = max(
        coverage_states,
        key=lambda item: _COVERAGE_PRECEDENCE[item],
    )
    if payload["coverage"]["status"] != expected_coverage:
        raise error_type("top-level coverage disagrees with execution and obligations")
    incomplete_required_ids = {
        item["obligation_id"]
        for item in obligations
        if item["active"]
        and item["required"]
        and item["coverage"]["status"] != "complete"
    }
    projected_incomplete_ids = {
        item["entity_id"] for item in payload["coverage"]["not_evaluated_item_refs"]
    }
    if not incomplete_required_ids.issubset(projected_incomplete_ids):
        raise error_type("top-level coverage omits incomplete required obligations")

    execution = payload["execution"]
    active_required = [
        item for item in obligations if item["active"] and item["required"]
    ]
    invalid = bool(execution["integrity_failure_ids"]) or any(
        item["outcome"] == "invalid" or item["finality"] == "invalid"
        for item in active
    )
    terminal_refutation = any(
        item["outcome"] == "refuted" and item["finality"] == "terminal"
        for item in active_required
    )
    pass_allowed = (
        bool(obligations)
        and expected_coverage == "complete"
        and expected_challenge == "none"
        and not execution["integrity_failure_ids"]
        and not execution["required_provider_failure_ids"]
        and not execution["not_evaluated_stage_refs"]
        and not expected_open_holds
        and not payload["blocking_residual_risk_ids"]
        and not payload["decision_requests"]
        and (
            all(
                item["outcome"] == "satisfied"
                and item["finality"] == "terminal"
                and item["challenge"] == "none"
                and item["coverage"]["status"] == "complete"
                and not item["open_hold_ids"]
                for item in active_required
            )
            if active_required
            else all(
                not item["active"]
                and not item["required"]
                and item["outcome"] == "not_applicable"
                and item["finality"] == "terminal"
                and item["challenge"] == "none"
                and item["coverage"]["status"] == "complete"
                and not item["open_hold_ids"]
                for item in obligations
            )
        )
    )
    if invalid:
        expected_dimensions = ("invalid", "invalid", "block")
    elif expected_challenge == "conflict":
        expected_dimensions = ("undetermined", "provisional", "block")
    elif terminal_refutation:
        expected_dimensions = ("refuted", "terminal", "block")
    elif pass_allowed:
        expected_dimensions = (
            "satisfied" if active_required else "not_applicable",
            "terminal",
            "pass",
        )
    else:
        expected_dimensions = ("undetermined", "provisional", "warn")
    observed_dimensions = (
        payload["audit_conclusion"]["outcome"],
        payload["audit_conclusion"]["finality"],
        payload["workflow_disposition"]["status"],
    )
    if observed_dimensions != expected_dimensions:
        raise error_type(
            "workflow and audit conclusion disagree with re-aggregated public state"
        )

    # Re-aggregate the enclosing state before checking its claim and decision
    # projections.  Otherwise a top-level coverage or challenge defect is
    # reported first as a downstream claim mismatch, obscuring the source.
    _validate_assurance_claim_consistency(payload, error_type)
    _validate_decision_request_consistency(payload, error_type)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _deduped_projection(
    values: Iterable[dict[str, Any]],
    identity_key: str,
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for value in values:
        identity = str(value[identity_key])
        if identity in seen:
            continue
        seen.add(identity)
        result.append(value)
    return result


def _require_exact_projection(
    observed: Any,
    expected: Any,
    message: str,
    error_type: type[Exception],
) -> None:
    if _canonical_json(observed) != _canonical_json(expected):
        raise error_type(message)


def _validate_assurance_claim_consistency(
    payload: dict[str, Any],
    error_type: type[Exception],
) -> None:
    """Bind aggregate assurance claims to their public audit basis.

    The v0 JSON Schema validates each local shape, but a bounded assurance
    claim is meaningful only when its subject, proposition, rules, evidence,
    state, and provenance are the exact projection of the enclosing audit.
    These checks deliberately reject semantically valid-looking substitution.
    """

    claims = payload["assurance_claims"]
    if len(claims) != 1:
        raise error_type("audit envelope must contain exactly one aggregate assurance claim")
    claim = claims[0]
    if claim["claim_id"] != f"claim.{payload['audit_id']}":
        raise error_type("assurance claim identity disagrees with audit identity")
    if claim["subject_ref"] != payload["subject_ref"]:
        raise error_type("assurance claim subject_ref disagrees with audit subject")

    expected_scope_refs = [payload["subject_ref"], *payload["profile_refs"]]
    _require_exact_projection(
        claim["scope"]["included_refs"],
        expected_scope_refs,
        "assurance claim scope disagrees with audit subject and profiles",
        error_type,
    )

    expected_dimensions = {
        key: payload["audit_conclusion"][key]
        for key in ("outcome", "finality", "challenge")
    }
    observed_dimensions = {key: claim[key] for key in expected_dimensions}
    if observed_dimensions != expected_dimensions:
        raise error_type("assurance claim state disagrees with audit conclusion")
    if claim["coverage"] != payload["coverage"]:
        raise error_type("assurance claim coverage disagrees with audit coverage")

    aggregate_id = f"interpretation.{payload['audit_id']}"
    aggregate = [
        item for item in payload["interpretations"] if item["interpretation_id"] == aggregate_id
    ]
    if len(aggregate) != 1:
        raise error_type("audit envelope must contain one aggregate interpretation")
    if claim["proposition"] != aggregate[0]["proposition"]:
        raise error_type("assurance claim proposition disagrees with aggregate interpretation")
    _require_exact_projection(
        claim["interpretations"],
        aggregate,
        "assurance claim interpretations disagree with aggregate interpretation",
        error_type,
    )

    obligations = payload["obligation_results"]
    expected_rules = [rule for item in obligations for rule in item["rules"]]
    _require_exact_projection(
        claim["rules"],
        expected_rules,
        "assurance claim rules disagree with obligation results",
        error_type,
    )
    expected_support = _deduped_projection(
        [ref for item in obligations for ref in item["supporting_evidence_refs"]],
        "entity_id",
    )
    expected_challenge = _deduped_projection(
        [ref for item in obligations for ref in item["challenging_evidence_refs"]],
        "entity_id",
    )
    _require_exact_projection(
        claim["supporting_evidence_refs"],
        expected_support,
        "assurance claim supporting evidence disagrees with obligation results",
        error_type,
    )
    _require_exact_projection(
        claim["challenging_evidence_refs"],
        expected_challenge,
        "assurance claim challenging evidence disagrees with obligation results",
        error_type,
    )

    top_provenance = {
        item["provenance_id"]: _canonical_json(item) for item in payload["provenance"]
    }
    for record in claim["provenance"]:
        if top_provenance.get(record["provenance_id"]) != _canonical_json(record):
            raise error_type("assurance claim provenance is absent or changed in audit provenance")
    top_effects = {
        item["effect_id"]: _canonical_json(item) for item in payload["authority_effects"]
    }
    for effect in claim["authority_effects"]:
        if top_effects.get(effect["effect_id"]) != _canonical_json(effect):
            raise error_type(
                "assurance claim authority effect is absent or changed in audit effects"
            )
    _require_exact_projection(
        claim["residual_risks"],
        payload["residual_risks"],
        "assurance claim residual risks disagree with audit residual risks",
        error_type,
    )


_RESOLUTION_AUTHORITY = {
    "change_intent_or_scope": "requester_intent",
    "accept_residual_risk": "risk_acceptance",
    "grant_or_expand_authority": "authority_grant",
    "authorize_external_effect": "external_effect_authorization",
    "final_acceptance": "final_acceptance",
}


def _validate_decision_request_consistency(
    payload: dict[str, Any],
    error_type: type[Exception],
) -> None:
    obligation_ids = {item["obligation_id"] for item in payload["obligation_results"]}
    seen: set[str] = set()
    for request in payload["decision_requests"]:
        request_id = request["decision_request_id"]
        if request_id in seen:
            raise error_type("decision_requests contains duplicate decision_request_id values")
        seen.add(request_id)
        if request["audit_ref"]["entity_id"] != payload["audit_id"]:
            raise error_type(f"decision request {request_id} audit_ref disagrees with audit")
        if request["subject_ref"] != payload["subject_ref"]:
            raise error_type(f"decision request {request_id} subject_ref disagrees with audit")
        affected = {item["entity_id"] for item in request["affected_obligation_refs"]}
        if not affected or not affected.issubset(obligation_ids):
            raise error_type(
                f"decision request {request_id} references an unknown affected obligation"
            )
        need = request["decision_need"]
        expected_authority = _RESOLUTION_AUTHORITY.get(need["resolution_kind"])
        if expected_authority and need["required_authority"] != expected_authority:
            raise error_type(
                f"decision request {request_id} resolution kind requires {expected_authority}"
            )
        if request["issue_class"] == "final_acceptance" and (
            need["resolution_kind"] != "final_acceptance"
            or need["required_authority"] != "final_acceptance"
        ):
            raise error_type(
                f"decision request {request_id} final acceptance requires human final authority"
            )


def _validate_provider_capabilities(
    payload: dict[str, Any],
    error_type: type[Exception],
) -> None:
    """Recheck the capability contract represented by every public run.

    Provider-boundary validation happens before projection, but the public
    envelope must remain independently auditable after serialization.  These
    checks prevent a mutated or hand-built run from claiming completeness
    while omitting a requested analysis capability.
    """

    for run in payload.get("analysis_runs", []):
        execution = run["execution"]
        requested = execution["requested_capabilities"]
        fulfilled = execution["fulfilled_capabilities"]
        missing = execution["missing_capabilities"]
        requested_set = set(requested)
        fulfilled_set = set(fulfilled)
        if not fulfilled_set.issubset(requested_set):
            raise error_type(
                f"analysis run {run['provider_id']} fulfilled capabilities "
                "outside its requested capabilities"
            )
        expected_missing = [
            capability
            for capability in requested
            if capability not in fulfilled_set
        ]
        if missing != expected_missing:
            raise error_type(
                f"analysis run {run['provider_id']} missing_capabilities "
                "disagree with requested minus fulfilled"
            )
        if execution["status"] == "complete" and missing:
            raise error_type(
                f"analysis run {run['provider_id']} claims complete with "
                "missing capabilities"
            )


_EFFECT_RIGHT = {
    "support": "support",
    "challenge": "challenge",
    "hold_apply": "hold_apply",
    "hold_release": "hold_release",
}
_ANALYSIS_STAGE_CEILINGS: dict[str, dict[str, bool]] = {
    "stage.morphology": {
        "support": False,
        "challenge": False,
        "hold_apply": False,
        "hold_release": False,
    },
    "stage.dependency_parse": {
        "support": False,
        "challenge": True,
        "hold_apply": False,
        "hold_release": False,
    },
    "stage.llm_candidate": {
        "support": False,
        "challenge": True,
        "hold_apply": False,
        "hold_release": False,
    },
}


def _rights_within_ceiling(
    claimed: dict[str, Any],
    ceiling: dict[str, Any],
) -> bool:
    return all(
        not bool(claimed.get(name)) or bool(ceiling.get(name))
        for name in _EFFECT_RIGHT.values()
    )


def _validate_analysis_authority(payload: dict[str, Any], error_type: type[Exception]) -> None:
    provider_ceilings: dict[str, dict[str, Any]] = {}
    for run in payload.get("analysis_runs", []):
        provider_id = run["provider_id"]
        rights = run["authority_rights"]
        maximum = run["maximum_evidentiary_authority"]
        forbidden_rights = (
            ("support", "challenge", "hold_apply", "hold_release")
            if maximum == "signal_only"
            else ("support", "hold_apply", "hold_release")
        )
        if maximum in {"signal_only", "candidate_only"} and any(
            rights[name] for name in forbidden_rights
        ):
            raise error_type(
                f"analysis provider {provider_id} exceeds {maximum} authority"
            )
        provider_ceilings[provider_id] = rights

    ceilings = {**_ANALYSIS_STAGE_CEILINGS, **provider_ceilings}
    for item in _walk(payload):
        if not isinstance(item, dict) or not {
            "effect_id",
            "kind",
            "actor_ref",
            "authority_snapshot",
        }.issubset(item):
            continue
        actor_id = item["actor_ref"]["entity_id"]
        ceiling = ceilings.get(actor_id)
        if ceiling is None:
            continue
        snapshot = item["authority_snapshot"]
        if not _rights_within_ceiling(snapshot, ceiling):
            raise error_type(
                f"authority effect {item['effect_id']} exceeds actor ceiling for {actor_id}"
            )
        required_right = _EFFECT_RIGHT[item["kind"]]
        if not bool(ceiling.get(required_right)):
            raise error_type(
                f"authority effect {item['effect_id']} is forbidden for actor {actor_id}"
            )


def _validate_hold_effect_references(
    payload: dict[str, Any],
    error_type: type[Exception],
) -> None:
    for item in _walk(payload):
        if not isinstance(item, dict) or "authority_effects" not in item:
            continue
        holds = [*item.get("holds", []), *item.get("audit_holds", [])]
        if not holds:
            continue
        effects = {effect["effect_id"]: effect for effect in item["authority_effects"]}
        for hold in holds:
            for field_name in ("applied_by", "released_by"):
                embedded = hold.get(field_name)
                if embedded is None:
                    continue
                effect_id = embedded["effect_id"]
                registered = effects.get(effect_id)
                if registered is None:
                    raise error_type(
                        f"hold {hold['hold_id']} references absent authority effect {effect_id}"
                    )
                if registered != embedded:
                    raise error_type(
                        f"hold {hold['hold_id']} authority effect {effect_id} disagrees with its registry entry"
                    )


def _contains_identity(value: Any, identities: set[str]) -> bool:
    if isinstance(value, str):
        return value in identities
    if isinstance(value, dict):
        return any(_contains_identity(item, identities) for item in value.values())
    if isinstance(value, list):
        return any(_contains_identity(item, identities) for item in value)
    return False


def _validate_shadow_isolation(
    payload: dict[str, Any],
    error_type: type[Exception],
) -> None:
    if payload.get("analysis_mode") != "shadow_all":
        return

    shadow_observation_ids = {
        item["observation_id"] for item in payload.get("shadow_observations", [])
    }
    shadow_candidate_ids = {
        interpretation["interpretation_id"]
        for run in payload.get("analysis_runs", [])
        if run["decision_influence"] == "shadow_observation"
        for interpretation in run["interpretations"]
    }
    shadow_provenance_ids = {
        record["provenance_id"]
        for run in payload.get("analysis_runs", [])
        if run["decision_influence"] == "shadow_observation"
        for record in run["provenance"]
    }
    effective_material = {
        "obligation_results": payload.get("obligation_results", []),
        "assurance_claims": payload.get("assurance_claims", []),
        "decision_requests": payload.get("decision_requests", []),
        "interpretations": payload.get("interpretations", []),
        "blocking_residual_risk_ids": payload.get("blocking_residual_risk_ids", []),
        "residual_risks": payload.get("residual_risks", []),
        "authority_effects": payload.get("authority_effects", []),
    }
    forbidden_identities = shadow_observation_ids | shadow_candidate_ids
    if forbidden_identities and _contains_identity(effective_material, forbidden_identities):
        raise error_type(
            "shadow observation or candidate identity appears in effective audit material"
        )
    for claim in payload.get("assurance_claims", []):
        if _contains_identity(claim.get("provenance", []), shadow_provenance_ids):
            raise error_type(
                "shadow analysis provenance appears in an assurance claim"
            )


__all__ = [
    "KNOWN_SCHEMA_NAMES",
    "SCHEMA_VERSION",
    "load_public_schema",
    "public_audit_payload",
    "validate_public_audit",
]
