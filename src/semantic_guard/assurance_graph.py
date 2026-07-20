"""Opt-in proof-obligation closure for bounded assurance claims.

The existing ``assurance-claim/v0`` remains the default public shape.  This
module wraps one validated v0 audit snapshot in ``assurance-claim/v1`` and
builds a deterministic graph whose nodes and edges are regenerated during
validation.  A successful validation means that the bounded material is
internally replayable; it does not establish action occurrence, authenticity,
operational fitness, or human acceptance.
"""

from __future__ import annotations

import copy
import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator, FormatChecker, ValidationError
from referencing import Registry, Resource

from .engine import RequirementAuditReport, audit_requirement_relations
from .schema_access import schema_directory as _shared_schema_directory
from .profiles import FUNCTIONAL_REQUIREMENT_PROFILE
from .provider_receipts import (
    AnalyzerQualification,
    QualifiedAnalyzerRegistry,
    attempt_output_digest,
)
from .providers import (
    AnalysisAttempt,
    AnalysisSpan,
    ProviderAuthority,
    ProviderRequest,
    RelationCandidate,
    ScopeCandidate,
    TokenCandidate,
)
from .public_contract import (
    _has_reassessment_support,
    _public_audit_payload_for_assurance_v1,
    _validate_public_audit_for_assurance_v1,
)


SCHEMA_VERSION = "assurance-claim/v1"
PROFILE_ID = "profile.assurance-proof-closure"
PROFILE_VERSION = "1.0.0"

_OBLIGATIONS = (
    ("proof.subject-binding", "subject_binding", "/basis_snapshot/public_audit/subject_ref"),
    ("proof.proposition-derivation", "proposition_derivation", "/base_claim/proposition"),
    ("proof.rule-closure", "rule_closure", "/base_claim/rules"),
    ("proof.evidence-closure", "evidence_closure", "/base_claim/supporting_evidence_refs"),
    ("proof.authority-closure", "authority_closure", "/base_claim/authority_effects"),
    ("proof.aggregation-closure", "aggregation_closure", "/base_claim/outcome"),
    ("proof.unresolved-preservation", "unresolved_preservation", "/base_claim/unproven_scope"),
    ("proof.runtime-derivation-closure", "runtime_derivation_closure", "/runtime_derivation"),
    ("proof.graph-closure", "graph_closure", "/derivation_graph"),
)

_RUNTIME_SCHEMA_VERSION = "assurance-runtime-derivation/v1"
_REASSESSMENT_BASIS_VERSION = "reassessment-basis/v1"
_REASSESSMENT_POLICY_ID = "obligation-reassessment-policy/v0"
_REQUIRED_REASSESSMENT_CAPABILITIES = (
    "coordination",
    "dependency",
    "predicate_argument",
)

_LIMITATIONS = [
    "Graph closure establishes internal replayability only.",
    "The embedded v0 audit does not prove action occurrence, actor identity, authority, artifact authenticity, causality, or human acceptance.",
    "Qualified reassessment replay embeds the source text and sanitized provider attempts; this improves deterministic replay but increases disclosure and is not cryptographic authenticity or field-validity certification.",
    "Replacing the whole snapshot and regenerating every digest creates a different claim identity; authenticity still requires an adopted trust mechanism outside this prototype.",
]

_AUTHORITY_BOUNDARY = {
    "semantic_guard_role": "validate_bounded_assurance_material",
    "execution_owner": "external_caller_or_control_plane",
    "final_acceptance_owner": "human",
}


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _digest(value: Any) -> dict[str, str]:
    return {"algorithm": "sha256", "value": _sha256(value)}


def _prefixed_digest(value: Any) -> str:
    return "sha256:" + _sha256(value)


def _direct_assessment_payload(item: Any) -> dict[str, Any]:
    return {
        "obligation_id": item.obligation_id,
        "outcome": item.outcome,
        "rule_id": item.rule_id,
        "from_field": item.from_field,
        "to_field": item.to_field,
        "evidence_spans": [list(span) for span in item.evidence_spans],
        "basis": list(item.basis),
        "unknown_reasons": list(item.unknown_reasons),
    }


def _projection_payload(item: Any) -> dict[str, Any]:
    candidate = item.candidate
    return {
        "projection_id": item.projection_id,
        "rule_id": item.rule_id,
        "provider_id": item.provider_id,
        "provider_version": item.provider_version,
        "resource_version": item.resource_version,
        "receipt_id": item.receipt_id,
        "source_relation_kinds": list(item.source_relation_kinds),
        "candidate": {
            "relation_kind": candidate.relation_kind,
            "from_span": {
                "start": candidate.from_span.start,
                "end": candidate.from_span.end,
                "role": candidate.from_span.role,
            },
            "to_span": {
                "start": candidate.to_span.start,
                "end": candidate.to_span.end,
                "role": candidate.to_span.role,
            },
            "confidence": candidate.confidence,
            "interpretation_id": candidate.interpretation_id,
            "rationale": candidate.rationale,
        },
    }


def _span_payload(span: AnalysisSpan) -> dict[str, Any]:
    return {"start": span.start, "end": span.end, "role": span.role}


def _attempt_output_material(item: AnalysisAttempt) -> dict[str, Any]:
    return {
        "stage": item.stage,
        "provider_id": item.provider_id,
        "provider_version": item.provider_version,
        "resource_version": item.resource_version,
        "status": item.status,
        "authority": {
            "support": item.authority.support,
            "challenge_signal": item.authority.challenge_signal,
            "apply_hold": item.authority.apply_hold,
            "release_hold": item.authority.release_hold,
        },
        "requested_capabilities": list(item.requested_capabilities),
        "fulfilled_capabilities": list(item.fulfilled_capabilities),
        "covered_spans": [_span_payload(span) for span in item.covered_spans],
        "tokens": [
            {
                "surface": token.surface,
                "lemma": token.lemma,
                "normalized": token.normalized,
                "part_of_speech": list(token.part_of_speech),
                "start": token.start,
                "end": token.end,
                "features": dict(token.features),
            }
            for token in item.tokens
        ],
        "relations": [
            {
                "relation_kind": relation.relation_kind,
                "from_span": _span_payload(relation.from_span),
                "to_span": _span_payload(relation.to_span),
                "confidence": relation.confidence,
                "interpretation_id": relation.interpretation_id,
                "rationale": relation.rationale,
            }
            for relation in item.relations
        ],
        "scopes": [
            {
                "scope_kind": scope.scope_kind,
                "cue_span": _span_payload(scope.cue_span),
                "target_span": (
                    _span_payload(scope.target_span)
                    if scope.target_span is not None
                    else None
                ),
                "confidence": scope.confidence,
            }
            for scope in item.scopes
        ],
        "upstream_usage": list(item.upstream_usage),
        "diagnostics": list(item.diagnostics),
    }


def _attempt_payload(item: AnalysisAttempt) -> dict[str, Any]:
    material = _attempt_output_material(item)
    output_digest = attempt_output_digest(item)
    return {
        "schema_version": "provider-analysis-attempt/v0",
        "attempt_id": "analysis-attempt." + output_digest[7:],
        "output_digest": output_digest,
        **material,
    }


def _span_from_payload(value: dict[str, Any]) -> AnalysisSpan:
    return AnalysisSpan(value["start"], value["end"], value["role"])


def _attempt_from_payload(value: dict[str, Any]) -> AnalysisAttempt:
    return AnalysisAttempt(
        stage=value["stage"],
        provider_id=value["provider_id"],
        provider_version=value["provider_version"],
        resource_version=value["resource_version"],
        status=value["status"],
        authority=ProviderAuthority(
            support=value["authority"]["support"],
            challenge_signal=value["authority"]["challenge_signal"],
            apply_hold=value["authority"]["apply_hold"],
            release_hold=value["authority"]["release_hold"],
        ),
        requested_capabilities=tuple(value["requested_capabilities"]),
        fulfilled_capabilities=tuple(value["fulfilled_capabilities"]),
        covered_spans=tuple(_span_from_payload(item) for item in value["covered_spans"]),
        tokens=tuple(
            TokenCandidate(
                surface=item["surface"],
                lemma=item["lemma"],
                normalized=item["normalized"],
                part_of_speech=tuple(item["part_of_speech"]),
                start=item["start"],
                end=item["end"],
                features=dict(item["features"]),
            )
            for item in value["tokens"]
        ),
        relations=tuple(
            RelationCandidate(
                relation_kind=item["relation_kind"],
                from_span=_span_from_payload(item["from_span"]),
                to_span=_span_from_payload(item["to_span"]),
                confidence=item["confidence"],
                interpretation_id=item["interpretation_id"],
                rationale=item["rationale"],
            )
            for item in value["relations"]
        ),
        scopes=tuple(
            ScopeCandidate(
                scope_kind=item["scope_kind"],
                cue_span=_span_from_payload(item["cue_span"]),
                target_span=(
                    _span_from_payload(item["target_span"])
                    if item["target_span"] is not None
                    else None
                ),
                confidence=item["confidence"],
            )
            for item in value["scopes"]
        ),
        upstream_usage=tuple(value["upstream_usage"]),
        diagnostics=tuple(value["diagnostics"]),
    )


class _ReplayProvider:
    def __init__(self, attempt: AnalysisAttempt) -> None:
        self.provider_id = attempt.provider_id
        self.provider_version = attempt.provider_version
        self.resource_version = attempt.resource_version
        self.stage = attempt.stage
        self._attempt = attempt

    def analyze(self, request: ProviderRequest) -> AnalysisAttempt:
        return self._attempt


def _finish_runtime_derivation(basis_material: dict[str, Any]) -> dict[str, Any]:
    basis = {**basis_material, "basis_digest": _digest(basis_material)}
    runtime_material = {
        "schema_version": _RUNTIME_SCHEMA_VERSION,
        "reassessment_basis": basis,
    }
    return {
        **runtime_material,
        "runtime_derivation_digest": _digest(runtime_material),
    }


def _empty_runtime_derivation(public_audit: dict[str, Any]) -> dict[str, Any]:
    profile = public_audit["profile_refs"][0]
    return _finish_runtime_derivation(
        {
            "schema_version": _REASSESSMENT_BASIS_VERSION,
            "source_id": public_audit["subject_ref"]["entity_id"],
            "source_text": None,
            "analysis_mode": None,
            "profile_id": profile["entity_id"],
            "profile_version": profile["entity_version"],
            "analysis_attempts": [],
            "provider_receipts": [],
            "analyzer_qualifications": [],
            "dependency_projections": [],
            "prior_assessments": [],
            "initial_unresolved_obligations": [],
            "obligation_reassessments": [],
        }
    )


def _runtime_derivation_from_report(
    report: RequirementAuditReport,
    public_audit: dict[str, Any],
) -> dict[str, Any]:
    promotions = tuple(
        item for item in report.obligation_reassessments if item.is_promotion
    )
    if not promotions:
        return _empty_runtime_derivation(public_audit)
    if (
        report.profile_id != FUNCTIONAL_REQUIREMENT_PROFILE.profile_id
        or report.profile_version != FUNCTIONAL_REQUIREMENT_PROFILE.version
    ):
        raise ValidationError(
            "qualified reassessment replay currently requires the functional-requirement-record/v1 profile"
        )
    receipt_ids = {value for item in promotions for value in item.receipt_ids}
    qualification_ids = {
        value for item in promotions for value in item.qualification_ids
    }
    projection_ids = {value for item in promotions for value in item.projection_ids}
    obligation_ids = {item.obligation_id for item in promotions}
    unresolved_ids = {
        item.unresolved_id for item in promotions if item.unresolved_id is not None
    }
    return _finish_runtime_derivation(
        {
            "schema_version": _REASSESSMENT_BASIS_VERSION,
            "source_id": report.source_id,
            "source_text": report.record.source_text,
            "analysis_mode": report.analysis_mode,
            "profile_id": report.profile_id,
            "profile_version": report.profile_version,
            "analysis_attempts": [
                _attempt_payload(item) for item in report.analysis_attempts
            ],
            "provider_receipts": [
                item.as_dict()
                for item in report.provider_execution_receipts
                if item.receipt_id in receipt_ids
            ],
            "analyzer_qualifications": [
                item.as_dict()
                for item in report.analyzer_qualifications
                if item.qualification_id in qualification_ids
            ],
            "dependency_projections": [
                _projection_payload(item)
                for item in report.dependency_projections
                if item.projection_id in projection_ids
            ],
            "prior_assessments": [
                _direct_assessment_payload(item)
                for item in report.direct_assessments
                if item.obligation_id in obligation_ids
            ],
            "initial_unresolved_obligations": [
                item.as_dict()
                for item in report.initial_unresolved_obligations
                if item.unresolved_id in unresolved_ids
            ],
            "obligation_reassessments": [item.as_dict() for item in promotions],
        }
    )


def _ref(entity_id: str, label: str, *, role: str | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "reference_kind": "ref",
        "entity_id": entity_id,
        "label_hint": label,
    }
    if role:
        result["role"] = role
    return result


def _node(kind: str, label: str, payload: Any) -> dict[str, Any]:
    digest = _sha256(payload)
    return {
        "node_id": f"derivation-node.{kind}.{digest[:24]}",
        "node_kind": kind,
        "label": label,
        "payload_digest": {"algorithm": "sha256", "value": digest},
    }


def _node_ref(node: dict[str, Any]) -> dict[str, Any]:
    return _ref(node["node_id"], node["label"], role="derivation_node")


def _proof_ref(obligation_id: str) -> dict[str, Any]:
    return _ref(obligation_id, obligation_id, role="proof_obligation")


def _claim_profile_ref() -> dict[str, Any]:
    return {
        **_ref(
            PROFILE_ID,
            "proof obligation and assurance graph profile",
            role="claim_profile",
        ),
        "entity_version": PROFILE_VERSION,
    }


def _edge(
    kind: str,
    source: dict[str, Any],
    target: dict[str, Any],
    proof_obligation_id: str,
) -> dict[str, Any]:
    material = {
        "kind": kind,
        "source": source["node_id"],
        "target": target["node_id"],
        "proof": proof_obligation_id,
    }
    return {
        "edge_id": f"derivation-edge.{_sha256(material)[:24]}",
        "edge_kind": kind,
        "from_node_ref": _node_ref(source),
        "to_node_ref": _node_ref(target),
        "proof_obligation_ref": _proof_ref(proof_obligation_id),
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


def _rule_identity(rule: dict[str, Any]) -> str:
    return f"{rule['rule_ref']['entity_id']}@{rule['rule_version']}"


def _unique_by(values: list[dict[str, Any]], key: str, label: str) -> dict[str, dict[str, Any]]:
    mapped = {str(item[key]): item for item in values}
    if len(mapped) != len(values):
        raise ValidationError(f"runtime reassessment basis contains duplicate {label}")
    return mapped


def _receipt_identity(receipt: dict[str, Any]) -> str:
    material = {
        "schema_version": receipt["schema_version"],
        "source_digest": receipt["source_digest"],
        "request_digest": receipt["request_digest"],
        "output_digest": receipt["output_digest"],
        "provider": [
            receipt["provider_id"],
            receipt["provider_version"],
            receipt["resource_version"],
        ],
        "stage": receipt["stage"],
        "status": receipt["status"],
        "target_spans": [
            [item["start"], item["end"], item["role"]]
            for item in receipt["target_spans"]
        ],
        "covered_spans": [
            [item["start"], item["end"], item["role"]]
            for item in receipt["covered_spans"]
        ],
        "requested_capabilities": receipt["requested_capabilities"],
        "fulfilled_capabilities": receipt["fulfilled_capabilities"],
        "upstream_digest": receipt["upstream_digest"],
        "upstream_usage": receipt["upstream_usage"],
    }
    return "receipt." + _sha256(material)


def _qualification_identity(qualification: dict[str, Any]) -> str:
    material = {
        "schema_version": qualification["schema_version"],
        "provider_id": qualification["provider_id"],
        "provider_version": qualification["provider_version"],
        "resource_version": qualification["resource_version"],
        "capabilities": qualification["capabilities"],
        "policy_scope": qualification["policy_scope"],
        "qualification_basis": qualification["qualification_basis"],
    }
    return "qualification." + _sha256(material)


def _reassessment_identity(reassessment: dict[str, Any]) -> str:
    material = {
        "source_id": reassessment["source_id"],
        "profile_id": reassessment["profile_id"],
        "profile_version": reassessment["profile_version"],
        "obligation_id": reassessment["obligation_id"],
        "unresolved_id": reassessment["unresolved_id"],
        "unresolved_digest": reassessment["unresolved_digest"],
        "prior_assessment_digest": reassessment["prior_assessment_digest"],
        "original_rule_id": reassessment["original_rule_id"],
        "original_outcome": reassessment["original_outcome"],
        "decision": reassessment["decision"],
        "effective_outcome": reassessment["effective_outcome"],
        "policy_rule_id": reassessment["policy_rule_id"],
        "receipt_ids": reassessment["receipt_ids"],
        "qualification_ids": reassessment["qualification_ids"],
        "projection_ids": reassessment["projection_ids"],
        "evidence_spans": [
            [item["start"], item["end"]]
            for item in reassessment["evidence_spans"]
        ],
        "reasons": reassessment["reasons"],
    }
    return "reassessment." + _sha256(material)


def _reassessment_support_obligations(public_audit: dict[str, Any]) -> set[str]:
    return {
        scope["entity_id"]
        for effect in public_audit["authority_effects"]
        if effect["kind"] == "support"
        and effect["actor_ref"]["entity_id"] == _REASSESSMENT_POLICY_ID
        for scope in effect["scope_refs"]
    }


def _validate_attempt_payload(value: dict[str, Any]) -> AnalysisAttempt:
    attempt = _attempt_from_payload(value)
    expected_digest = attempt_output_digest(attempt)
    if value["output_digest"] != expected_digest:
        raise ValidationError("analysis attempt output digest mismatch")
    if value["attempt_id"] != "analysis-attempt." + expected_digest[7:]:
        raise ValidationError("analysis attempt identity mismatch")
    return attempt


def _replay_runtime_reassessment(
    basis: dict[str, Any],
    public_audit: dict[str, Any],
) -> None:
    """Re-run the bounded engine path from embedded text and provider output.

    This is deterministic implementation replay, not proof that the embedded
    text or provider output was authentically observed in the outside world.
    """

    attempts = {
        item["attempt_id"]: _validate_attempt_payload(item)
        for item in basis["analysis_attempts"]
    }
    if len(attempts) != len(basis["analysis_attempts"]):
        raise ValidationError("runtime replay contains duplicate analysis attempt identities")
    by_stage: dict[str, AnalysisAttempt] = {}
    for attempt in attempts.values():
        if attempt.stage in by_stage:
            raise ValidationError("runtime replay contains more than one attempt for a stage")
        by_stage[attempt.stage] = attempt

    qualifications = tuple(
        AnalyzerQualification(
            provider_id=item["provider_id"],
            provider_version=item["provider_version"],
            resource_version=item["resource_version"],
            capabilities=tuple(item["capabilities"]),
            policy_scope=item["policy_scope"],
            qualification_basis=item["qualification_basis"],
        )
        for item in basis["analyzer_qualifications"]
    )
    if any(
        generated.qualification_id != embedded["qualification_id"]
        for generated, embedded in zip(
            qualifications,
            basis["analyzer_qualifications"],
            strict=True,
        )
    ):
        raise ValidationError("runtime replay qualification identity mismatch")
    registry = QualifiedAnalyzerRegistry(qualifications)

    def provider(stage: str) -> _ReplayProvider | None:
        attempt = by_stage.get(stage)
        if attempt is None or attempt.status == "not_configured":
            return None
        return _ReplayProvider(attempt)

    report = audit_requirement_relations(
        basis["source_text"],
        profile=FUNCTIONAL_REQUIREMENT_PROFILE,
        morphology_provider=provider("morphology"),
        dependency_provider=provider("dependency_parse"),
        llm_provider=provider("llm_candidate"),
        analysis_mode=basis["analysis_mode"],
        analyzer_registry=registry,
    )
    if (
        report.source_id != basis["source_id"]
        or report.profile_id != basis["profile_id"]
        or report.profile_version != basis["profile_version"]
    ):
        raise ValidationError("runtime engine replay source or profile mismatch")

    replay_attempts = {
        item["attempt_id"]: item
        for item in (_attempt_payload(attempt) for attempt in report.analysis_attempts)
    }
    embedded_attempts = {
        item["attempt_id"]: item for item in basis["analysis_attempts"]
    }
    if replay_attempts != embedded_attempts:
        raise ValidationError("embedded provider attempts disagree with engine replay")

    replay_receipts = {
        item.receipt_id: item.as_dict() for item in report.provider_execution_receipts
    }
    if any(
        replay_receipts.get(item["receipt_id"]) != item
        for item in basis["provider_receipts"]
    ):
        raise ValidationError("embedded provider receipt disagrees with engine replay")
    replay_projections = {
        item.projection_id: _projection_payload(item)
        for item in report.dependency_projections
    }
    if any(
        replay_projections.get(item["projection_id"]) != item
        for item in basis["dependency_projections"]
    ):
        raise ValidationError("embedded dependency projection disagrees with engine replay")
    replay_priors = {
        item.obligation_id: _direct_assessment_payload(item)
        for item in report.direct_assessments
    }
    if any(
        replay_priors.get(item["obligation_id"]) != item
        for item in basis["prior_assessments"]
    ):
        raise ValidationError("embedded prior assessment disagrees with engine replay")
    replay_unresolved = {
        item.unresolved_id: item.as_dict()
        for item in report.initial_unresolved_obligations
    }
    if any(
        replay_unresolved.get(item["unresolved_id"]) != item
        for item in basis["initial_unresolved_obligations"]
    ):
        raise ValidationError("embedded unresolved route disagrees with engine replay")
    replay_reassessments = {
        item.reassessment_id: item.as_dict()
        for item in report.obligation_reassessments
        if item.is_promotion
    }
    embedded_reassessments = {
        item["reassessment_id"]: item
        for item in basis["obligation_reassessments"]
    }
    if replay_reassessments != embedded_reassessments:
        raise ValidationError("embedded obligation reassessment disagrees with engine replay")
    if {
        item.qualification_id: item.as_dict()
        for item in report.analyzer_qualifications
    } != {
        item["qualification_id"]: item
        for item in basis["analyzer_qualifications"]
    }:
        raise ValidationError("embedded analyzer qualifications disagree with engine replay")

    replay_support = _reassessment_support_obligations(public_audit)
    if replay_support != {
        item.obligation_id
        for item in report.obligation_reassessments
        if item.is_promotion
    }:
        raise ValidationError("public reassessment support disagrees with engine replay")


def _validate_runtime_derivation(
    runtime: dict[str, Any],
    public_audit: dict[str, Any],
) -> None:
    if runtime["schema_version"] != _RUNTIME_SCHEMA_VERSION:
        raise ValidationError("runtime derivation schema version mismatch")
    runtime_material = {
        "schema_version": runtime["schema_version"],
        "reassessment_basis": runtime["reassessment_basis"],
    }
    if runtime["runtime_derivation_digest"] != _digest(runtime_material):
        raise ValidationError("runtime derivation digest mismatch")
    basis = runtime["reassessment_basis"]
    if basis["schema_version"] != _REASSESSMENT_BASIS_VERSION:
        raise ValidationError("reassessment basis schema version mismatch")
    basis_material = {
        key: value for key, value in basis.items() if key != "basis_digest"
    }
    if basis["basis_digest"] != _digest(basis_material):
        raise ValidationError("reassessment basis digest mismatch")
    profile = public_audit["profile_refs"][0]
    if (
        basis["source_id"] != public_audit["subject_ref"]["entity_id"]
        or basis["profile_id"] != profile["entity_id"]
        or basis["profile_version"] != profile["entity_version"]
    ):
        raise ValidationError("runtime reassessment source or profile binding mismatch")

    collection_names = (
        "analysis_attempts",
        "provider_receipts",
        "analyzer_qualifications",
        "dependency_projections",
        "prior_assessments",
        "initial_unresolved_obligations",
        "obligation_reassessments",
    )
    support_obligation_ids = _reassessment_support_obligations(public_audit)
    if not support_obligation_ids:
        if (
            basis["source_text"] is not None
            or basis["analysis_mode"] is not None
            or any(basis[name] for name in collection_names)
        ):
            raise ValidationError(
                "runtime reassessment basis must be empty without reassessment-derived support"
            )
        return
    if (
        not isinstance(basis["source_text"], str)
        or not basis["source_text"]
        or basis["analysis_mode"] not in {"assurance", "conditional", "shadow_all"}
        or any(not basis[name] for name in collection_names)
    ):
        raise ValidationError(
            "reassessment-derived support requires a closed non-empty runtime basis"
        )
    if (
        "sha256:" + hashlib.sha256(basis["source_text"].encode("utf-8")).hexdigest()
        != basis["source_id"]
    ):
        raise ValidationError("runtime source text digest mismatch")
    if (
        basis["profile_id"] != FUNCTIONAL_REQUIREMENT_PROFILE.profile_id
        or basis["profile_version"] != FUNCTIONAL_REQUIREMENT_PROFILE.version
    ):
        raise ValidationError(
            "runtime reassessment replay profile is not implemented"
        )

    attempts = _unique_by(
        basis["analysis_attempts"], "attempt_id", "analysis attempt identity"
    )
    replay_attempts = {
        identity: _validate_attempt_payload(item)
        for identity, item in attempts.items()
    }
    if len({item.stage for item in replay_attempts.values()}) != len(replay_attempts):
        raise ValidationError("runtime reassessment basis has duplicate provider stages")

    receipts = _unique_by(basis["provider_receipts"], "receipt_id", "receipt identity")
    qualifications = _unique_by(
        basis["analyzer_qualifications"],
        "qualification_id",
        "qualification identity",
    )
    projections = _unique_by(
        basis["dependency_projections"], "projection_id", "projection identity"
    )
    priors = _unique_by(basis["prior_assessments"], "obligation_id", "prior assessment")
    unresolved = _unique_by(
        basis["initial_unresolved_obligations"],
        "unresolved_id",
        "unresolved route identity",
    )
    reassessments = _unique_by(
        basis["obligation_reassessments"],
        "reassessment_id",
        "reassessment identity",
    )
    if {
        item["obligation_id"] for item in reassessments.values()
    } != support_obligation_ids:
        raise ValidationError(
            "runtime reassessment obligations disagree with public support effects"
        )
    if set(receipts) != {
        identity
        for item in reassessments.values()
        for identity in item["receipt_ids"]
    }:
        raise ValidationError("runtime receipt denominator disagrees with reassessments")
    if set(qualifications) != {
        identity
        for item in reassessments.values()
        for identity in item["qualification_ids"]
    }:
        raise ValidationError(
            "runtime qualification denominator disagrees with reassessments"
        )
    if set(projections) != {
        identity
        for item in reassessments.values()
        for identity in item["projection_ids"]
    }:
        raise ValidationError("runtime projection denominator disagrees with reassessments")
    if set(priors) != support_obligation_ids:
        raise ValidationError("runtime prior assessment denominator is not closed")
    if set(unresolved) != {
        item["unresolved_id"] for item in reassessments.values()
    }:
        raise ValidationError("runtime unresolved route denominator is not closed")

    for receipt_id, receipt in receipts.items():
        if receipt_id != _receipt_identity(receipt):
            raise ValidationError("provider receipt identity mismatch")
        if (
            receipt["source_digest"] != basis["source_id"]
            or receipt["stage"] != "dependency_parse"
            or receipt["status"] != "ok"
        ):
            raise ValidationError(
                "reassessment support requires an ok dependency receipt for the same source"
            )
        matching_attempts = [
            item
            for item in replay_attempts.values()
            if item.stage == receipt["stage"]
            and item.provider_id == receipt["provider_id"]
            and item.provider_version == receipt["provider_version"]
            and item.resource_version == receipt["resource_version"]
            and item.status == receipt["status"]
            and attempt_output_digest(item) == receipt["output_digest"]
        ]
        if len(matching_attempts) != 1:
            raise ValidationError(
                "provider receipt output is not bound to one embedded analysis attempt"
            )
    for qualification_id, qualification in qualifications.items():
        if qualification_id != _qualification_identity(qualification):
            raise ValidationError("analyzer qualification identity mismatch")
        if tuple(qualification["capabilities"]) != _REQUIRED_REASSESSMENT_CAPABILITIES:
            raise ValidationError("analyzer qualification capability scope mismatch")
    for projection in projections.values():
        receipt = receipts.get(projection["receipt_id"])
        if receipt is None:
            raise ValidationError("dependency projection has no runtime receipt")
        if (
            projection["provider_id"] != receipt["provider_id"]
            or projection["provider_version"] != receipt["provider_version"]
            or projection["resource_version"] != receipt["resource_version"]
        ):
            raise ValidationError("dependency projection provider binding mismatch")
        if projection["candidate"]["relation_kind"] not in {"performs", "acts_on"}:
            raise ValidationError("unsupported runtime projection relation")

    for reassessment in reassessments.values():
        obligation_id = reassessment["obligation_id"]
        if (
            reassessment["reassessment_id"] != _reassessment_identity(reassessment)
            or reassessment["source_id"] != basis["source_id"]
            or reassessment["profile_id"] != basis["profile_id"]
            or reassessment["profile_version"] != basis["profile_version"]
            or reassessment["policy_rule_id"] != _REASSESSMENT_POLICY_ID
            or reassessment["decision"] != "supported"
            or reassessment["effective_outcome"] != "supported"
            or reassessment["original_outcome"] != "unresolved"
            or reassessment["route_status"] != "resolved_by_reassessment"
            or reassessment["resolved_by"] != _REASSESSMENT_POLICY_ID
        ):
            raise ValidationError("obligation reassessment policy or identity mismatch")
        prior = priors.get(obligation_id)
        if prior is None or reassessment["prior_assessment_digest"] != _prefixed_digest(prior):
            raise ValidationError("reassessment prior assessment binding mismatch")
        unresolved_item = unresolved.get(reassessment["unresolved_id"])
        if (
            unresolved_item is None
            or reassessment["unresolved_digest"]
            != _prefixed_digest(unresolved_item)
            or unresolved_item["obligation_id"] != obligation_id
        ):
            raise ValidationError("reassessment unresolved route binding mismatch")
        selected_receipts = [receipts.get(item) for item in reassessment["receipt_ids"]]
        selected_qualifications = [
            qualifications.get(item) for item in reassessment["qualification_ids"]
        ]
        selected_projections = [
            projections.get(item) for item in reassessment["projection_ids"]
        ]
        if (
            not selected_receipts
            or any(item is None for item in selected_receipts)
            or not selected_qualifications
            or any(item is None for item in selected_qualifications)
            or not selected_projections
            or any(item is None for item in selected_projections)
        ):
            raise ValidationError("reassessment runtime reference closure is incomplete")
        public_effect_basis = "\n".join(
            str(value)
            for effect in public_audit["authority_effects"]
            if effect["kind"] == "support"
            and effect["actor_ref"]["entity_id"] == _REASSESSMENT_POLICY_ID
            and any(
                scope["entity_id"] == obligation_id
                for scope in effect["scope_refs"]
            )
            for value in effect["basis"]
        )
        if any(
            identity not in public_effect_basis
            for identity in (
                *reassessment["receipt_ids"],
                *reassessment["qualification_ids"],
            )
        ):
            raise ValidationError(
                "runtime receipt or qualification is absent from public support basis"
            )
        for qualification in selected_qualifications:
            assert qualification is not None
            if qualification["policy_scope"] != f"{_REASSESSMENT_POLICY_ID}:{obligation_id}":
                raise ValidationError("qualification policy scope mismatch")
            if not any(
                receipt is not None
                and qualification["provider_id"] == receipt["provider_id"]
                and qualification["provider_version"] == receipt["provider_version"]
                and qualification["resource_version"] == receipt["resource_version"]
                for receipt in selected_receipts
            ):
                raise ValidationError("qualification provider binding mismatch")

    _replay_runtime_reassessment(basis, public_audit)


def _build_graph(
    public_audit: dict[str, Any],
    base_claim: dict[str, Any],
    runtime_derivation: dict[str, Any],
) -> dict[str, Any]:
    subject_material = {
        "subject_ref": public_audit["subject_ref"],
        "input_provenance": [
            item for item in public_audit["provenance"] if item["kind"] == "input"
        ],
    }
    subject_node = _node("subject_snapshot", "audited subject snapshot", subject_material)
    profile_nodes = [
        _node("claim_profile", item["label_hint"], item)
        for item in public_audit["profile_refs"]
    ]
    proposition_node = _node("proposition", "bounded claim proposition", base_claim["proposition"])

    rules_by_identity: dict[str, dict[str, Any]] = {}
    for obligation in public_audit["obligation_results"]:
        for rule in obligation["rules"]:
            rules_by_identity.setdefault(_rule_identity(rule), rule)
    rule_nodes = {
        identity: _node("rule", identity, rule)
        for identity, rule in rules_by_identity.items()
    }

    evidence_by_id: dict[str, dict[str, Any]] = {}
    for obligation in public_audit["obligation_results"]:
        for field in (
            "supporting_evidence_refs",
            "refuting_evidence_refs",
            "challenging_evidence_refs",
        ):
            for reference in obligation[field]:
                evidence_by_id.setdefault(reference["entity_id"], reference)
    evidence_nodes = {
        identity: _node("evidence", reference["label_hint"], reference)
        for identity, reference in evidence_by_id.items()
    }

    obligation_nodes = {
        item["obligation_id"]: _node(
            "obligation_result",
            item["obligation_id"],
            item,
        )
        for item in public_audit["obligation_results"]
    }
    coverage_node = _node("coverage", "aggregate coverage", public_audit["coverage"])
    hold_values = _dedupe(base_claim["holds"], "hold_id")
    hold_nodes = {
        item["hold_id"]: _node("hold", item["hold_id"], item) for item in hold_values
    }
    provenance_nodes = {
        item["provenance_id"]: _node("provenance", item["provenance_id"], item)
        for item in base_claim["provenance"]
    }
    effect_nodes = {
        item["effect_id"]: _node("authority_effect", item["effect_id"], item)
        for item in base_claim["authority_effects"]
    }
    reassessment_basis = runtime_derivation["reassessment_basis"]
    runtime_node = _node(
        "runtime_derivation",
        "closed runtime reassessment derivation",
        runtime_derivation,
    )
    runtime_source_node = (
        _node(
            "runtime_source",
            "embedded replay source text",
            {
                "source_id": reassessment_basis["source_id"],
                "source_text": reassessment_basis["source_text"],
            },
        )
        if reassessment_basis["source_text"] is not None
        else None
    )
    attempt_nodes = {
        item["attempt_id"]: _node(
            "analysis_attempt", item["attempt_id"], item
        )
        for item in reassessment_basis["analysis_attempts"]
    }
    receipt_nodes = {
        item["receipt_id"]: _node(
            "provider_receipt", item["receipt_id"], item
        )
        for item in reassessment_basis["provider_receipts"]
    }
    qualification_nodes = {
        item["qualification_id"]: _node(
            "analyzer_qualification", item["qualification_id"], item
        )
        for item in reassessment_basis["analyzer_qualifications"]
    }
    projection_nodes = {
        item["projection_id"]: _node(
            "dependency_projection", item["projection_id"], item
        )
        for item in reassessment_basis["dependency_projections"]
    }
    prior_nodes = {
        item["obligation_id"]: _node(
            "prior_assessment", item["obligation_id"], item
        )
        for item in reassessment_basis["prior_assessments"]
    }
    unresolved_nodes = {
        item["unresolved_id"]: _node(
            "unresolved_route", item["unresolved_id"], item
        )
        for item in reassessment_basis["initial_unresolved_obligations"]
    }
    reassessment_nodes = {
        item["reassessment_id"]: _node(
            "obligation_reassessment", item["reassessment_id"], item
        )
        for item in reassessment_basis["obligation_reassessments"]
    }
    aggregation_material = {
        "audit_conclusion": public_audit["audit_conclusion"],
        "workflow_disposition": public_audit["workflow_disposition"],
        "coverage": public_audit["coverage"],
        "unresolved_required_obligation_ids": public_audit[
            "unresolved_required_obligation_ids"
        ],
        "open_hold_ids": public_audit["open_hold_ids"],
        "blocking_residual_risk_ids": public_audit["blocking_residual_risk_ids"],
    }
    aggregation_node = _node("aggregation", "public audit aggregation", aggregation_material)
    claim_node = _node("bounded_claim", "bounded assurance claim v0 basis", base_claim)

    nodes = [
        subject_node,
        *profile_nodes,
        proposition_node,
        *rule_nodes.values(),
        *evidence_nodes.values(),
        *obligation_nodes.values(),
        coverage_node,
        *hold_nodes.values(),
        *provenance_nodes.values(),
        *effect_nodes.values(),
        runtime_node,
        *([runtime_source_node] if runtime_source_node is not None else []),
        *attempt_nodes.values(),
        *receipt_nodes.values(),
        *qualification_nodes.values(),
        *projection_nodes.values(),
        *prior_nodes.values(),
        *unresolved_nodes.values(),
        *reassessment_nodes.values(),
        aggregation_node,
        claim_node,
    ]

    edges: list[dict[str, Any]] = []
    for obligation in public_audit["obligation_results"]:
        target = obligation_nodes[obligation["obligation_id"]]
        edges.append(_edge("binds_subject", subject_node, target, "proof.subject-binding"))
        profile = next(
            node
            for ref, node in zip(public_audit["profile_refs"], profile_nodes, strict=True)
            if ref["entity_id"] == obligation["profile_ref"]["entity_id"]
        )
        edges.append(_edge("interprets_under", profile, target, "proof.rule-closure"))
        for rule in obligation["rules"]:
            edges.append(
                _edge(
                    "applies_rule",
                    rule_nodes[_rule_identity(rule)],
                    target,
                    "proof.rule-closure",
                )
            )
        for field, kind in (
            ("supporting_evidence_refs", "supports"),
            ("refuting_evidence_refs", "refutes"),
            ("challenging_evidence_refs", "challenges"),
        ):
            for reference in obligation[field]:
                edges.append(
                    _edge(
                        kind,
                        evidence_nodes[reference["entity_id"]],
                        target,
                        "proof.evidence-closure",
                    )
                )
        edges.append(_edge("aggregates", target, aggregation_node, "proof.aggregation-closure"))

    edges.append(_edge("aggregates", coverage_node, aggregation_node, "proof.aggregation-closure"))
    for node in hold_nodes.values():
        edges.append(_edge("preserves_hold", node, aggregation_node, "proof.unresolved-preservation"))
    for node in provenance_nodes.values():
        edges.append(_edge("records_provenance", node, claim_node, "proof.evidence-closure"))
    for node in effect_nodes.values():
        edges.append(_edge("constrains_authority", node, claim_node, "proof.authority-closure"))
    if runtime_source_node is not None:
        for attempt_node in attempt_nodes.values():
            edges.append(
                _edge(
                    "observes_runtime_source",
                    runtime_source_node,
                    attempt_node,
                    "proof.runtime-derivation-closure",
                )
            )
    for attempt_id, attempt_node in attempt_nodes.items():
        attempt = next(
            item
            for item in reassessment_basis["analysis_attempts"]
            if item["attempt_id"] == attempt_id
        )
        for receipt_id, receipt_node in receipt_nodes.items():
            receipt = next(
                item
                for item in reassessment_basis["provider_receipts"]
                if item["receipt_id"] == receipt_id
            )
            if (
                attempt["stage"] == receipt["stage"]
                and attempt["provider_id"] == receipt["provider_id"]
                and attempt["provider_version"] == receipt["provider_version"]
                and attempt["resource_version"] == receipt["resource_version"]
                and attempt["output_digest"] == receipt["output_digest"]
            ):
                edges.append(
                    _edge(
                        "materializes_receipt",
                        attempt_node,
                        receipt_node,
                        "proof.runtime-derivation-closure",
                    )
                )
    for qualification_id, qualification_node in qualification_nodes.items():
        qualification = next(
            item
            for item in reassessment_basis["analyzer_qualifications"]
            if item["qualification_id"] == qualification_id
        )
        for receipt_id, receipt_node in receipt_nodes.items():
            receipt = next(
                item
                for item in reassessment_basis["provider_receipts"]
                if item["receipt_id"] == receipt_id
            )
            if (
                qualification["provider_id"] == receipt["provider_id"]
                and qualification["provider_version"] == receipt["provider_version"]
                and qualification["resource_version"] == receipt["resource_version"]
            ):
                edges.append(
                    _edge(
                        "qualifies_execution",
                        qualification_node,
                        receipt_node,
                        "proof.runtime-derivation-closure",
                    )
                )
    for reassessment in reassessment_basis["obligation_reassessments"]:
        node = reassessment_nodes[reassessment["reassessment_id"]]
        for receipt_id in reassessment["receipt_ids"]:
            edges.append(
                _edge(
                    "records_execution",
                    receipt_nodes[receipt_id],
                    node,
                    "proof.runtime-derivation-closure",
                )
            )
        for projection_id in reassessment["projection_ids"]:
            edges.append(
                _edge(
                    "projects_dependency",
                    projection_nodes[projection_id],
                    node,
                    "proof.runtime-derivation-closure",
                )
            )
        edges.append(
            _edge(
                "reassesses_prior",
                prior_nodes[reassessment["obligation_id"]],
                node,
                "proof.runtime-derivation-closure",
            )
        )
        edges.append(
            _edge(
                "resolves_unresolved",
                unresolved_nodes[reassessment["unresolved_id"]],
                node,
                "proof.runtime-derivation-closure",
            )
        )
        edges.append(
            _edge(
                "derives_support",
                node,
                obligation_nodes[reassessment["obligation_id"]],
                "proof.runtime-derivation-closure",
            )
        )
        edges.append(
            _edge(
                "records_runtime_derivation",
                node,
                runtime_node,
                "proof.runtime-derivation-closure",
            )
        )
    edges.append(
        _edge(
            "binds_runtime_derivation",
            runtime_node,
            claim_node,
            "proof.runtime-derivation-closure",
        )
    )
    edges.append(_edge("defines_proposition", proposition_node, claim_node, "proof.proposition-derivation"))
    edges.append(_edge("derives", aggregation_node, claim_node, "proof.aggregation-closure"))

    graph_material = {
        "schema_version": "assurance-derivation-graph/v1",
        "nodes": nodes,
        "edges": edges,
        "root_node_ref": _node_ref(claim_node),
    }
    return {**graph_material, "graph_digest": _digest(graph_material)}


def _proof_obligations(graph: dict[str, Any]) -> list[dict[str, Any]]:
    nodes = graph["nodes"]
    by_kind: dict[str, list[dict[str, Any]]] = {}
    for node in nodes:
        by_kind.setdefault(node["node_kind"], []).append(node)
    basis_kinds = {
        "subject_binding": ("subject_snapshot", "obligation_result"),
        "proposition_derivation": ("proposition", "bounded_claim"),
        "rule_closure": ("claim_profile", "rule", "obligation_result"),
        "evidence_closure": ("evidence", "provenance", "obligation_result"),
        "authority_closure": ("authority_effect", "bounded_claim"),
        "aggregation_closure": ("obligation_result", "coverage", "aggregation"),
        "unresolved_preservation": ("coverage", "hold", "aggregation"),
        "runtime_derivation_closure": (
            "runtime_derivation",
            "runtime_source",
            "analysis_attempt",
            "provider_receipt",
            "analyzer_qualification",
            "dependency_projection",
            "prior_assessment",
            "unresolved_route",
            "obligation_reassessment",
        ),
        "graph_closure": ("aggregation", "bounded_claim"),
    }
    result: list[dict[str, Any]] = []
    for obligation_id, kind, locator in _OBLIGATIONS:
        selected = [
            node for node_kind in basis_kinds[kind] for node in by_kind.get(node_kind, [])
        ]
        if not selected:
            selected = by_kind["bounded_claim"]
        result.append(
            {
                "obligation_id": obligation_id,
                "obligation_kind": kind,
                "required": True,
                "status": "satisfied",
                "basis_node_refs": [_node_ref(node) for node in selected],
                "result_locator": locator,
                "limitations": [
                    "Satisfaction means internal replay closure under the embedded audit snapshot, not external truth or human acceptance."
                ],
            }
        )
    return result


def build_assurance_claim_v1(
    public_audit: dict[str, Any],
    *,
    runtime_derivation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one deterministic v1 claim from a validated public v0 audit."""

    _validate_public_audit_for_assurance_v1(public_audit)
    basis = copy.deepcopy(public_audit)
    if runtime_derivation is None:
        if _has_reassessment_support(basis):
            raise ValidationError(
                "qualified reassessment support requires runtime derivation material"
            )
        runtime = _empty_runtime_derivation(basis)
    else:
        runtime = copy.deepcopy(runtime_derivation)
    _validate_runtime_derivation(runtime, basis)
    base_claim = copy.deepcopy(basis["assurance_claims"][0])
    graph = _build_graph(basis, base_claim, runtime)
    snapshot_digest = _digest(basis)
    identity_material = {
        "basis": snapshot_digest,
        "graph": graph["graph_digest"],
        "runtime_derivation": runtime["runtime_derivation_digest"],
        "base_claim_id": base_claim["claim_id"],
        "profile": f"{PROFILE_ID}/{PROFILE_VERSION}",
    }
    result = {
        "schema_version": SCHEMA_VERSION,
        "claim_id": f"claim.v1.{_sha256(identity_material)}",
        "basis_snapshot": {
            "schema_version": "assurance-basis-snapshot/v1",
            "public_audit": basis,
            "snapshot_digest": snapshot_digest,
        },
        "base_claim": base_claim,
        "runtime_derivation": runtime,
        "claim_profile_ref": _claim_profile_ref(),
        "proof_obligations": _proof_obligations(graph),
        "derivation_graph": graph,
        "limitations": list(_LIMITATIONS),
        "authority_boundary": dict(_AUTHORITY_BOUNDARY),
    }
    validate_assurance_claim_v1(result)
    return result


def public_assurance_claim_v1(
    report: RequirementAuditReport,
    *,
    recorded_at: str | None = None,
) -> dict[str, Any]:
    public_audit = _public_audit_payload_for_assurance_v1(
        report,
        recorded_at=recorded_at,
    )
    return build_assurance_claim_v1(
        public_audit,
        runtime_derivation=_runtime_derivation_from_report(report, public_audit),
    )


def _schema_directory() -> Path:
    return _shared_schema_directory(sentinel="assurance-claim-v1.schema.json")


@lru_cache(maxsize=1)
def _validator() -> Draft202012Validator:
    resources: list[tuple[str, Resource[Any]]] = []
    root: dict[str, Any] | None = None
    for path in sorted(_schema_directory().glob("*.schema.json")):
        schema = json.loads(path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        resources.append((schema["$id"], Resource.from_contents(schema)))
        if path.name == "assurance-claim-v1.schema.json":
            root = schema
    if root is None:
        raise FileNotFoundError("assurance-claim-v1.schema.json is missing")
    return Draft202012Validator(
        root,
        registry=Registry().with_resources(resources),
        format_checker=FormatChecker(),
    )


def _validate_graph_structure(graph: dict[str, Any]) -> None:
    nodes = graph["nodes"]
    node_ids = [item["node_id"] for item in nodes]
    if len(node_ids) != len(set(node_ids)):
        raise ValidationError("derivation graph contains duplicate node identities")
    edge_ids = [item["edge_id"] for item in graph["edges"]]
    if len(edge_ids) != len(set(edge_ids)):
        raise ValidationError("derivation graph contains duplicate edge identities")
    known_nodes = set(node_ids)
    known_proofs = {item[0] for item in _OBLIGATIONS}
    adjacency: dict[str, set[str]] = {item: set() for item in known_nodes}
    for edge in graph["edges"]:
        source = edge["from_node_ref"]["entity_id"]
        target = edge["to_node_ref"]["entity_id"]
        if source not in known_nodes or target not in known_nodes:
            raise ValidationError("derivation edge has an unresolved node endpoint")
        if edge["proof_obligation_ref"]["entity_id"] not in known_proofs:
            raise ValidationError("derivation edge has an unknown proof obligation")
        adjacency[source].add(target)
    if graph["root_node_ref"]["entity_id"] not in known_nodes:
        raise ValidationError("derivation graph root does not resolve")

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node_id: str) -> None:
        if node_id in visiting:
            raise ValidationError("derivation graph contains a cycle")
        if node_id in visited:
            return
        visiting.add(node_id)
        for target in adjacency[node_id]:
            visit(target)
        visiting.remove(node_id)
        visited.add(node_id)

    for node_id in node_ids:
        visit(node_id)
    graph_material = {key: graph[key] for key in ("schema_version", "nodes", "edges", "root_node_ref")}
    if graph["graph_digest"] != _digest(graph_material):
        raise ValidationError("derivation graph digest disagrees with graph material")


def validate_assurance_claim_v1(claim: dict[str, Any]) -> None:
    """Validate schema, graph closure, and deterministic replay material."""

    _validator().validate(claim)
    audit = claim["basis_snapshot"]["public_audit"]
    _validate_public_audit_for_assurance_v1(audit)
    if claim["basis_snapshot"]["snapshot_digest"] != _digest(audit):
        raise ValidationError("assurance basis snapshot digest disagrees with public audit")
    if claim["base_claim"] != audit["assurance_claims"][0]:
        raise ValidationError("v1 base claim disagrees with its embedded public audit")
    _validate_runtime_derivation(claim["runtime_derivation"], audit)
    _validate_graph_structure(claim["derivation_graph"])
    proof_ids = [item["obligation_id"] for item in claim["proof_obligations"]]
    if proof_ids != [item[0] for item in _OBLIGATIONS]:
        raise ValidationError("proof obligation set or order disagrees with the v1 profile")
    if any(item["required"] and item["status"] != "satisfied" for item in claim["proof_obligations"]):
        raise ValidationError("required proof obligation is not satisfied")

    # Regenerate without recursively calling this validator.
    base_claim = copy.deepcopy(audit["assurance_claims"][0])
    runtime = copy.deepcopy(claim["runtime_derivation"])
    graph = _build_graph(audit, base_claim, runtime)
    expected_snapshot = _digest(audit)
    expected_identity = {
        "basis": expected_snapshot,
        "graph": graph["graph_digest"],
        "runtime_derivation": runtime["runtime_derivation_digest"],
        "base_claim_id": base_claim["claim_id"],
        "profile": f"{PROFILE_ID}/{PROFILE_VERSION}",
    }
    if claim["claim_id"] != f"claim.v1.{_sha256(expected_identity)}":
        raise ValidationError("v1 claim identity disagrees with its basis and graph")
    if claim["claim_profile_ref"] != _claim_profile_ref():
        raise ValidationError("v1 claim profile disagrees with the adopted prototype profile")
    if claim["limitations"] != _LIMITATIONS:
        raise ValidationError("v1 limitations disagree with the bounded prototype contract")
    if claim["authority_boundary"] != _AUTHORITY_BOUNDARY:
        raise ValidationError("v1 authority boundary disagrees with the prototype contract")
    if claim["derivation_graph"] != graph:
        raise ValidationError("v1 derivation graph disagrees with regenerated audit basis")
    if claim["proof_obligations"] != _proof_obligations(graph):
        raise ValidationError("v1 proof obligations disagree with regenerated graph")
