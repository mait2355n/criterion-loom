from __future__ import annotations

"""Conservative relation-profile audit for functional requirement records.

This module deliberately separates *extraction* from *satisfaction*.  Relations
proposed by morphology, a dependency parser, or an LLM remain candidates even
when those providers report high confidence.  Only current, binding, asserted
relations may satisfy a profile obligation.
"""

from dataclasses import dataclass, field
import re
from typing import Any, Literal, Mapping, Sequence

from semantic_guard_workflow.semantic_assertions import (
    SemanticAssertionIR,
    SemanticEntity,
    SemanticRelation,
    SourceSegment,
    extract_semantic_assertions,
)


RELATION_PROFILE_SCHEMA_VERSION = "requirement-relation-profile/v0"
RELATION_DELTA_SCHEMA_VERSION = "relation-delta/v0"
RELATION_AUDIT_SCHEMA_VERSION = "requirement-relation-audit/v0"
RELATION_SUMMARY_SCHEMA_VERSION = "requirement-relation-summary/v1"
FUNCTIONAL_REQUIREMENT_PROFILE_ID = "functional-requirement-record/v0"
VERIFICATION_TARGET_MISMATCH_RULE_ID = "req.relation.verification_target_mismatch"

Necessity = Literal["required", "conditional"]
DeltaKind = Literal[
    "missing_node",
    "missing_relation",
    "wrong_attachment",
    "ambiguous_scope",
    "contradiction",
    "verification_mismatch",
    "evidence_disconnect",
    "unknown_applicability",
    "unmapped_expression",
]
DeltaStatus = Literal[
    "derived",
    "candidate",
    "blocked_by_unknown",
    "conflict",
    "not_applicable",
]


@dataclass(frozen=True)
class RelationObligation:
    id: str
    relation_kind: str
    from_kind: str
    to_kind: str
    necessity: Necessity = "required"
    description: str = ""

    def as_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "id": self.id,
            "relation_kind": self.relation_kind,
            "from_kind": self.from_kind,
            "to_kind": self.to_kind,
            "necessity": self.necessity,
        }
        if self.description:
            payload["description"] = self.description
        return payload


@dataclass(frozen=True)
class RequirementRelationProfile:
    profile_id: str
    requirement_kind: str
    obligations: tuple[RelationObligation, ...]
    schema_version: str = RELATION_PROFILE_SCHEMA_VERSION
    satisfying_state: str = "asserted"
    discourse_scope: str = "binding"
    temporal_scope: str = "current"

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "profile_id": self.profile_id,
            "requirement_kind": self.requirement_kind,
            "match_policy": {
                "satisfying_state": self.satisfying_state,
                "discourse_scope": self.discourse_scope,
                "temporal_scope": self.temporal_scope,
                "confidence_does_not_grant_authority": True,
            },
            "relation_obligations": [item.as_dict() for item in self.obligations],
        }


FUNCTIONAL_REQUIREMENT_PROFILE = RequirementRelationProfile(
    profile_id=FUNCTIONAL_REQUIREMENT_PROFILE_ID,
    requirement_kind="functional",
    obligations=(
        RelationObligation("func.applies_to", "applies_to", "requirement", "scenario_actor"),
        RelationObligation("func.performs", "performs", "scenario_actor", "behavior"),
        RelationObligation("func.acts_on", "acts_on", "behavior", "object", "conditional"),
        RelationObligation("func.triggered_by", "triggered_by", "behavior", "condition", "conditional"),
        RelationObligation("func.produces", "produces", "behavior", "observable_result"),
        RelationObligation("func.constrained_by", "constrained_by", "observable_result", "acceptance_criterion"),
        RelationObligation("func.uses_metric", "uses_metric", "acceptance_criterion", "metric", "conditional"),
        RelationObligation("func.verified_by", "verified_by", "requirement", "verification_method"),
        RelationObligation("func.verifies", "verifies", "verification_method", "acceptance_criterion"),
        RelationObligation("func.measures", "measures", "verification_method", "metric", "conditional"),
        RelationObligation("func.produces_evidence", "produces_evidence", "verification_method", "evidence_artifact"),
    ),
)


@dataclass(frozen=True)
class RelationDelta:
    id: str
    profile_id: str
    obligation_id: str
    kind: DeltaKind
    status: DeltaStatus
    expected: Mapping[str, object]
    observed: Mapping[str, object] = field(default_factory=dict)
    basis: Mapping[str, object] = field(default_factory=dict)
    unknown_reasons: tuple[str, ...] = ()
    rule_id: str = ""
    schema_version: str = RELATION_DELTA_SCHEMA_VERSION

    def as_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_version": self.schema_version,
            "id": self.id,
            "profile_id": self.profile_id,
            "obligation_id": self.obligation_id,
            "kind": self.kind,
            "status": self.status,
            "expected": dict(self.expected),
            "observed": dict(self.observed),
            "basis": dict(self.basis),
            "unknown_reasons": list(self.unknown_reasons),
        }
        if self.rule_id:
            payload["rule_id"] = self.rule_id
        return payload


@dataclass
class RequirementRelationAudit:
    ir: SemanticAssertionIR
    profile: RequirementRelationProfile
    satisfied_obligation_ids: list[str] = field(default_factory=list)
    deltas: list[RelationDelta] = field(default_factory=list)
    applicability_status: str = "unknown"
    applicability_reasons: list[str] = field(default_factory=list)
    schema_version: str = RELATION_AUDIT_SCHEMA_VERSION

    @property
    def summary(self) -> dict[str, object]:
        by_kind: dict[str, int] = {}
        by_status: dict[str, int] = {}
        for delta in self.deltas:
            by_kind[delta.kind] = by_kind.get(delta.kind, 0) + 1
            by_status[delta.status] = by_status.get(delta.status, 0) + 1
        return {
            "profile_id": self.profile.profile_id,
            "obligation_count": len(self.profile.obligations),
            "satisfied_count": len(self.satisfied_obligation_ids),
            "delta_count": len(self.deltas),
            "satisfied_obligation_ids": sorted(self.satisfied_obligation_ids),
            "delta_counts_by_kind": dict(sorted(by_kind.items())),
            "delta_counts_by_status": dict(sorted(by_status.items())),
            "has_derived_delta": any(item.status == "derived" for item in self.deltas),
            "applicability_status": self.applicability_status,
            "applicability_reasons": list(self.applicability_reasons),
        }

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "scope": "relation-profile comparison only; not natural-language truth or final acceptance",
            "profile": self.profile.as_dict(),
            "semantic_assertion_ir": self.ir.as_dict(),
            "satisfied_obligation_ids": sorted(self.satisfied_obligation_ids),
            "deltas": [item.as_dict() for item in self.deltas],
            "applicability_status": self.applicability_status,
            "applicability_reasons": list(self.applicability_reasons),
            "summary": self.summary,
        }

    def public_summary(self) -> dict[str, object]:
        """Return a bounded, evidence-carrying summary for public audit details."""

        attempts: list[dict[str, object]] = []
        extractor_stages: list[str] = []
        for attempt in _items(self.ir, "attempts")[:16]:
            stage = str(
                _value(attempt, "stage", "")
                or _value(attempt, "kind", "")
                or _value(attempt, "provider", "")
            )
            if stage == "structured_direct":
                stage = "structured_field"
            if stage and stage not in extractor_stages:
                extractor_stages.append(stage)
            bounded = {
                key: _value(attempt, key)
                for key in (
                    "stage",
                    "kind",
                    "provider",
                    "provider_id",
                    "provider_version",
                    "resource_version",
                    "split_mode",
                    "executed",
                    "status",
                    "authority",
                    "candidate_count",
                    "reason",
                    "diagnostic",
                    "diagnostics",
                )
                if _value(attempt, key, None) not in (None, "", [])
            }
            if bounded.get("stage") == "structured_direct":
                bounded["stage"] = "structured_field"
            produced_ids = _value(attempt, "produced_ids", ())
            if isinstance(produced_ids, Sequence) and not isinstance(produced_ids, (str, bytes)):
                bounded["produced_count"] = len(produced_ids)
            diagnostics = bounded.get("diagnostics")
            if isinstance(diagnostics, Sequence) and not isinstance(diagnostics, (str, bytes)):
                bounded["diagnostics"] = [str(item)[:240] for item in diagnostics[:4]]
            for key in ("reason", "diagnostic"):
                if isinstance(bounded.get(key), str):
                    bounded[key] = bounded[key][:240]
                elif key in bounded:
                    bounded[key] = str(bounded[key])[:240]
            if bounded:
                attempts.append(bounded)

        coverage_value = _value(self.ir, "coverage", {})
        if hasattr(coverage_value, "as_dict"):
            coverage_value = coverage_value.as_dict()
        raw_coverage = dict(coverage_value) if isinstance(coverage_value, Mapping) else {}
        raw_fields = raw_coverage.get("fields", [])
        if isinstance(raw_fields, Mapping):
            all_field_names = sorted(str(key) for key in raw_fields)
        elif isinstance(raw_fields, Sequence) and not isinstance(raw_fields, (str, bytes)):
            all_field_names = sorted(str(item) for item in raw_fields)
        else:
            all_field_names = []
        public_field_names = [name for name in all_field_names if not name.startswith("_")]
        field_names = public_field_names[:24]
        unresolved = raw_coverage.get("unresolved_spans")
        unresolved_count = (
            len(unresolved)
            if isinstance(unresolved, Sequence) and not isinstance(unresolved, (str, bytes))
            else int(raw_coverage.get("unresolved_count", 0) or 0)
        )
        candidate_conflicts = raw_coverage.get("candidate_conflicts", [])
        candidate_conflict_count = (
            len(candidate_conflicts)
            if isinstance(candidate_conflicts, Sequence)
            and not isinstance(candidate_conflicts, (str, bytes))
            else 0
        )
        metadata = _value(self.ir, "metadata", {})
        coverage = {
            "record_mode": str(
                raw_coverage.get("record_mode", "")
                or raw_coverage.get("kind", "")
                or _value(metadata, "record_mode", "")
                or "unknown"
            ),
            "field_names": field_names,
            "field_count": len(public_field_names),
            "unresolved_span_count": unresolved_count,
            "candidate_conflict_count": candidate_conflict_count,
        }

        entities = _items(self.ir, "entities")
        criterion, method, _, _ = _select_verification_pair(
            self.ir,
            entities,
            _items(self.ir, "relations"),
        )
        mismatch = next(
            (
                item
                for item in self.deltas
                if item.kind == "verification_mismatch" and item.status == "derived"
            ),
            None,
        )
        mismatch_candidate = next(
            (
                item
                for item in self.deltas
                if item.kind == "verification_mismatch" and item.status != "derived"
            ),
            None,
        )
        verifies_delta = next(
            (item for item in self.deltas if item.obligation_id == "func.verifies"),
            None,
        )
        verification_check: dict[str, object] = {
            "check_id": "verification_verifies_acceptance",
            "profile_id": self.profile.profile_id,
            "obligation_id": "func.verifies",
            "expected": {
                "relation": {
                    "kind": "verifies",
                    "from_kind": "verification_method",
                    "to_kind": "acceptance_criterion",
                }
            },
            "observed": {
                "criterion_entity_id": _entity_id(criterion) if criterion is not None else "",
                "method_entity_id": _entity_id(method) if method is not None else "",
            },
        }
        if self.applicability_status == "not_applicable":
            verification_check.update(
                {"status": "not_applicable", "derivation_status": "not_applicable"}
            )
        elif self.applicability_status in {"unknown", "conflict"}:
            verification_check.update(
                {
                    "status": "unknown",
                    "derivation_status": (
                        "conflict" if self.applicability_status == "conflict" else "blocked_by_unknown"
                    ),
                    "unknown_reasons": list(self.applicability_reasons),
                }
            )
        elif mismatch is not None:
            verification_check.update(
                {
                    "status": "mismatch",
                    "derivation_status": "derived",
                    "rule_id": VERIFICATION_TARGET_MISMATCH_RULE_ID,
                    "evidence_spans": list(mismatch.basis.get("evidence_spans", [])),
                }
            )
        elif mismatch_candidate is not None:
            verification_check.update(
                {
                    "status": "unknown",
                    "derivation_status": mismatch_candidate.status,
                    "unknown_reasons": list(mismatch_candidate.unknown_reasons),
                    "evidence_spans": list(
                        mismatch_candidate.basis.get("evidence_spans", [])
                    ),
                }
            )
        elif verifies_delta is not None:
            verification_check.update(
                {
                    "status": "unknown",
                    "derivation_status": verifies_delta.status,
                    "unknown_reasons": list(verifies_delta.unknown_reasons),
                }
            )
        elif "func.verifies" in self.satisfied_obligation_ids and criterion is not None and method is not None:
            verification_check.update(
                {
                    "status": "aligned",
                    "derivation_status": "satisfied",
                    "evidence_spans": [
                        _entity_evidence(self.ir, criterion),
                        _entity_evidence(self.ir, method),
                    ],
                }
            )
        else:
            verification_check.update(
                {"status": "not_applicable", "derivation_status": "not_applicable"}
            )

        checks: list[dict[str, object]] = [verification_check]
        for delta in self.deltas:
            if delta.kind == "verification_mismatch":
                continue
            check: dict[str, object] = {
                "check_id": f"delta:{delta.id}",
                "obligation_id": delta.obligation_id,
                "kind": delta.kind,
                "status": delta.status,
                "expected": {
                    "relation": dict(delta.expected.get("relation", {}))
                    if isinstance(delta.expected.get("relation"), Mapping)
                    else {}
                },
                "observed": {
                    "from_entity_count": len(delta.observed.get("from_entity_ids", [])),
                    "to_entity_count": len(delta.observed.get("to_entity_ids", [])),
                    "asserted_relation_count": len(delta.observed.get("asserted_relation_ids", [])),
                    "candidate_relation_count": len(delta.observed.get("candidate_relation_ids", [])),
                },
            }
            if delta.rule_id:
                check["rule_id"] = delta.rule_id
            evidence_spans = delta.basis.get("evidence_spans")
            if isinstance(evidence_spans, Sequence) and not isinstance(evidence_spans, (str, bytes)):
                check["evidence_spans"] = list(evidence_spans)
            if delta.unknown_reasons:
                check["unknown_reasons"] = list(delta.unknown_reasons)
            checks.append(check)

        return {
            "schema_version": RELATION_SUMMARY_SCHEMA_VERSION,
            "scope": "bounded relation-profile audit summary; not full IR, natural-language truth, or final acceptance",
            "profile_ids": [self.profile.profile_id],
            "extractor_stages": extractor_stages,
            "attempts": attempts,
            "coverage": coverage,
            "applicability": {
                "status": self.applicability_status,
                "reasons": list(self.applicability_reasons),
            },
            "checks": checks,
            "delta_counts_by_kind": self.summary["delta_counts_by_kind"],
            "delta_counts_by_status": self.summary["delta_counts_by_status"],
        }


_CANDIDATE_ONLY_SOURCES = frozenset(
    {
        "morphology",
        "morphological",
        "dependency",
        "dependency_parse",
        "dependency_parser",
        "llm",
        "llm_candidate",
        "llm_reviewer",
    }
)
_MULTI_TARGET_CONJUNCTION_RE = re.compile(
    r"(?:かつ|及び|および|ならびに|または|又は|\band\b|\bor\b)",
    re.IGNORECASE,
)
_DIMENSION_TERMS: dict[str, str] = {
    "response_latency": r"(?:search|検索|応答|response|latency)",
    "authentication": r"(?:login|authentication|authn|ログイン|認証)",
    "static_security": r"(?:sast|security|static\s+analysis|静的解析|脆弱性)",
    "error_rate": r"(?:error\s*rate|failure\s*rate|エラー率|失敗率)",
    "throughput": r"(?:throughput|rps|スループット|件/秒)",
}


def _value(item: object, name: str, default: Any = None) -> Any:
    if isinstance(item, Mapping):
        return item.get(name, default)
    return getattr(item, name, default)


def _items(ir: SemanticAssertionIR, name: str) -> list[Any]:
    value = _value(ir, name, ())
    return list(value or ())


def _entity_id(entity: object) -> str:
    return str(_value(entity, "id", ""))


def _entity_kind(entity: object) -> str:
    return str(_value(entity, "kind", "unknown"))


def _entity_state(entity: object) -> str:
    return str(_value(entity, "state", "unknown"))


def _entity_text(entity: object) -> str:
    return str(
        _value(entity, "canonical", "")
        or _value(entity, "normalized", "")
        or _value(entity, "text", "")
        or _value(entity, "label", "")
        or ""
    )


def _entity_attributes(entity: object) -> Mapping[str, object]:
    value = _value(entity, "attributes", {})
    return value if isinstance(value, Mapping) else {}


def _segment_map(ir: SemanticAssertionIR) -> dict[str, SourceSegment]:
    return {str(_value(item, "id", "")): item for item in _items(ir, "source_segments")}


def _assertion_map(ir: SemanticAssertionIR) -> dict[str, object]:
    return {str(_value(item, "id", "")): item for item in _items(ir, "assertions")}


def _support_ids(item: object) -> list[str]:
    value = _value(item, "support_ids", ())
    if isinstance(value, str):
        return [value]
    return [str(part) for part in (value or ())]


def _assertion_capable_supports(ir: SemanticAssertionIR, item: object) -> list[object]:
    support_map = {
        str(_value(support, "id", "")): support for support in _items(ir, "supports")
    }
    support_ids = _support_ids(item)
    if not support_ids:
        return []
    capable: list[object] = []
    for support_id in support_ids:
        support = support_map.get(support_id)
        if support is None:
            continue
        tier = str(
            _value(support, "tier", "")
            or _value(support, "source_kind", "")
            or _value(support, "kind", "")
        ).lower()
        authority = str(_value(support, "authority", "")).lower()
        if tier not in _CANDIDATE_ONLY_SOURCES and authority == "assertion_capable":
            capable.append(support)
    return capable


def _support_source_is_candidate_only(ir: SemanticAssertionIR, item: object) -> bool:
    direct_source = str(
        _value(item, "source_kind", "") or _value(item, "source", "")
    ).lower()
    direct_authority = str(_value(item, "authority", "")).lower()
    return (
        direct_source in _CANDIDATE_ONLY_SOURCES
        or direct_authority != "assertion_capable"
        or not _assertion_capable_supports(ir, item)
    )


def _current_binding(
    ir: SemanticAssertionIR,
    item: object,
    profile: RequirementRelationProfile = FUNCTIONAL_REQUIREMENT_PROFILE,
) -> bool:
    capable_supports = _assertion_capable_supports(ir, item)
    if not capable_supports:
        return False
    support_has_current_binding_scope = False
    for support in capable_supports:
        support_segment_id = str(_value(support, "source_segment_id", ""))
        if not support_segment_id:
            continue
        support_segment = _segment_map(ir).get(support_segment_id)
        if support_segment is None:
            continue
        support_discourse = str(_value(support_segment, "discourse_scope", ""))
        support_temporal = str(_value(support_segment, "temporal_scope", ""))
        if (
            support_discourse == profile.discourse_scope
            and support_temporal == profile.temporal_scope
        ):
            support_has_current_binding_scope = True
    if not support_has_current_binding_scope:
        return False

    discourse = str(_value(item, "discourse_scope", ""))
    temporal = str(_value(item, "temporal_scope", ""))
    if discourse or temporal:
        if discourse != profile.discourse_scope or temporal != profile.temporal_scope:
            return False
    segment_id = str(_value(item, "source_segment_id", ""))
    if segment_id:
        segment = _segment_map(ir).get(segment_id)
        if segment is None:
            return False
        discourse = str(_value(segment, "discourse_scope", ""))
        temporal = str(_value(segment, "temporal_scope", ""))
        if discourse != profile.discourse_scope or temporal != profile.temporal_scope:
            return False
    assertion = _assertion_map(ir).get(str(_value(item, "assertion_id", "")))
    if assertion is not None:
        assertion_discourse = str(_value(assertion, "discourse_scope", ""))
        assertion_temporal = str(_value(assertion, "temporal_scope", ""))
        if assertion_discourse:
            discourse = assertion_discourse
        if assertion_temporal:
            temporal = assertion_temporal
        if str(_value(assertion, "state", "")) != profile.satisfying_state:
            return False
        if _support_source_is_candidate_only(ir, assertion):
            return False
        if discourse != profile.discourse_scope or temporal != profile.temporal_scope:
            return False
    return True


def _entity_is_satisfying(
    ir: SemanticAssertionIR,
    entity: object,
    profile: RequirementRelationProfile = FUNCTIONAL_REQUIREMENT_PROFILE,
) -> bool:
    return (
        _entity_state(entity) == profile.satisfying_state
        and _current_binding(ir, entity, profile)
        and not _support_source_is_candidate_only(ir, entity)
    )


def _relation_is_coexistence_only(relation: object) -> bool:
    relation_kind = str(_value(relation, "kind", ""))
    attributes = _value(relation, "attributes", {})
    return (
        relation_kind in {"verifies", "produces_evidence"}
        and isinstance(attributes, Mapping)
        and attributes.get("cooccurrence_only") is True
    )


def _relation_is_satisfying(
    ir: SemanticAssertionIR,
    relation: object,
    profile: RequirementRelationProfile = FUNCTIONAL_REQUIREMENT_PROFILE,
) -> bool:
    return (
        not _relation_is_coexistence_only(relation)
        and str(_value(relation, "state", "unknown")) == profile.satisfying_state
        and _current_binding(ir, relation, profile)
        and not _support_source_is_candidate_only(ir, relation)
    )


def _relation_endpoints(relation: object) -> tuple[str, str]:
    return (
        str(_value(relation, "from_id", "") or _value(relation, "source_id", "")),
        str(_value(relation, "to_id", "") or _value(relation, "target_id", "")),
    )


def _coverage_is_closed(ir: SemanticAssertionIR) -> bool:
    coverage = str(
        _value(ir, "input_coverage", "")
        or _value(_value(ir, "coverage", {}), "input_coverage", "")
        or _value(_value(ir, "coverage", {}), "record_mode", "")
        or _value(_value(ir, "coverage", {}), "kind", "")
        or _value(_value(ir, "coverage", {}), "mode", "")
        or _value(_value(ir, "scope", {}), "input_coverage", "")
        or _value(_value(ir, "metadata", {}), "input_coverage", "")
        or _value(_value(ir, "metadata", {}), "record_mode", "")
    )
    return coverage in {"closed", "closed_record", "bounded_fields"}


def _profile_applicability(
    ir: SemanticAssertionIR,
    entities: Sequence[object],
) -> tuple[str, list[str]]:
    metadata = _value(ir, "metadata", {})
    requirement_kind = str(_value(metadata, "requirement_kind", ""))
    if requirement_kind not in {"", "unknown", "functional"}:
        return "not_applicable", [f"requirement_kind is {requirement_kind}, not functional"]
    reasons: list[str] = []
    if requirement_kind in {"", "unknown"}:
        reasons.append("requirement_kind is not explicitly established")
    if not _coverage_is_closed(ir):
        reasons.append("input is not a closed requirement record")
    role_span_kinds: dict[tuple[object, object], set[str]] = {}
    for entity in entities:
        kind = _entity_kind(entity)
        if kind not in {
            "scenario_actor",
            "behavior",
            "observable_result",
            "acceptance_criterion",
            "verification_method",
            "evidence_artifact",
        } or not _entity_is_satisfying(ir, entity):
            continue
        span = (_value(entity, "start", None), _value(entity, "end", None))
        if not all(isinstance(value, int) for value in span):
            continue
        role_span_kinds.setdefault(span, set()).add(kind)
    if any(len(kinds) > 1 for kinds in role_span_kinds.values()):
        reasons.append(
            "multiple requirement roles share one undifferentiated source span"
        )
    record_count_value = _value(metadata, "record_count", None)
    single_record_value = _value(metadata, "single_record", None)
    if isinstance(record_count_value, int):
        record_count = record_count_value
    else:
        record_count = len(
            [item for item in entities if _entity_kind(item) == "requirement"]
        )
    if single_record_value is False or record_count != 1:
        reasons.append(f"single-record scope is not established (record_count={record_count})")
    requirement_entities = [
        item
        for item in entities
        if _entity_kind(item) == "requirement" and _entity_is_satisfying(ir, item)
    ]
    if len(requirement_entities) != 1:
        reasons.append(
            "exactly one current binding asserted requirement root is required"
        )
    if reasons:
        if record_count > 1:
            return "conflict", reasons
        return "unknown", reasons
    return "applicable", []


def _expected(obligation: RelationObligation) -> dict[str, object]:
    return {
        "relation": {
            "kind": obligation.relation_kind,
            "from_kind": obligation.from_kind,
            "to_kind": obligation.to_kind,
        },
        "necessity": obligation.necessity,
    }


def _observed(
    obligation: RelationObligation,
    from_entities: Sequence[object],
    to_entities: Sequence[object],
    relations: Sequence[object],
) -> dict[str, object]:
    return {
        "from_entity_ids": sorted(_entity_id(item) for item in from_entities),
        "to_entity_ids": sorted(_entity_id(item) for item in to_entities),
        "asserted_relation_ids": sorted(
            str(_value(item, "id", ""))
            for item in relations
            if str(_value(item, "state", "")) == "asserted"
        ),
        "candidate_relation_ids": sorted(
            str(_value(item, "id", ""))
            for item in relations
            if str(_value(item, "state", "")) == "candidate"
        ),
        "rejected_entity_ids": sorted(
            _entity_id(item)
            for item in (*from_entities, *to_entities)
            if _entity_state(item) == "rejected"
        ),
    }


def _delta(
    sequence: int,
    obligation: RelationObligation,
    kind: DeltaKind,
    status: DeltaStatus,
    *,
    observed: Mapping[str, object] | None = None,
    basis: Mapping[str, object] | None = None,
    unknown_reasons: Sequence[str] = (),
    rule_id: str = "",
) -> RelationDelta:
    return RelationDelta(
        id=f"delta-{sequence:03d}",
        profile_id=FUNCTIONAL_REQUIREMENT_PROFILE_ID,
        obligation_id=obligation.id,
        kind=kind,
        status=status,
        expected=_expected(obligation),
        observed=observed or {},
        basis=basis or {},
        unknown_reasons=tuple(unknown_reasons),
        rule_id=rule_id,
    )


def _dimensions(entity: object, role: str) -> set[str]:
    attributes = _entity_attributes(entity)
    dimensions: set[str] = set()
    for key in ("dimension", "metric_dimension", "target_dimension", "domain"):
        value = attributes.get(key)
        if isinstance(value, str) and value.strip():
            dimensions.add(value.strip().lower())

    text = _entity_text(entity).lower()
    if re.search(r"(?:p\d{2}|latency|response\s*time|応答(?:時間)?|レスポンス|\bms\b|ミリ秒)", text):
        dimensions.add("response_latency")
    if re.search(r"(?:login|authentication|authn|ログイン|認証)", text):
        dimensions.add("authentication")
    if re.search(r"(?:sast|vulnerab|security|静的(?:解析|検査)|脆弱性|安全性)", text):
        dimensions.add("static_security")
    if role in {"method", "evidence"} and re.search(
        r"(?:search|検索).*(?:bench|performance|負荷|性能)|(?:bench|performance|負荷|性能).*(?:search|検索)",
        text,
    ):
        dimensions.add("response_latency")
    if re.search(r"(?:error\s*rate|failure\s*rate|エラー率|失敗率)", text):
        dimensions.add("error_rate")
    if re.search(r"(?:throughput|requests?/s|rps|スループット|件/秒)", text):
        dimensions.add("throughput")
    return dimensions


def _dimension_is_explicit(entity: object, role: str, dimension: str) -> bool:
    if str(_value(entity, "confidence", "")) != "high":
        return False
    text = _entity_text(entity).lower()
    if _MULTI_TARGET_CONJUNCTION_RE.search(text):
        return False
    if re.search(
        r"(?:準備のみ|の準備(?:を)?する|を検討(?:する)?|の名称|の呼称|記載のみ|"
        r"setup\s+only|consider(?:ing)?\s+(?:the\s+)?|name\s+only)",
        text,
        re.IGNORECASE,
    ):
        return False
    dimension_terms = _DIMENSION_TERMS.get(dimension)
    if dimension_terms and re.search(
        rf"(?:{dimension_terms}).{{0,16}}(?:除外|ではなく|以外|準備(?:後)?|前処理|テストデータ|"
        rf"excluded?|rather\s+than|instead\s+of|setup|prepar(?:e|ation)|test\s+data)",
        text,
        re.IGNORECASE,
    ):
        return False
    if dimension_terms and re.search(
        rf"(?:除外|以外|excluded?|rather\s+than|instead\s+of).{{0,12}}(?:{dimension_terms})",
        text,
        re.IGNORECASE,
    ):
        return False
    if re.search(r"(?:予定|候補|準備中|未定|proposal|proposed|planned|will\s+decide|if\b|場合)", text):
        return False
    if re.search(
        r"(?:測定|検証|試験|test|measure|verify).{0,12}(?:しない|行わない|not\s+|without)"
        r"|(?:does\s+not|will\s+not|without).{0,12}(?:test|measure|verify)",
        text,
    ):
        return False
    attributes = _entity_attributes(entity)
    explicit_attribute = any(
        str(attributes.get(key, "")).strip().lower() == dimension
        for key in ("dimension", "metric_dimension", "target_dimension", "domain")
    )
    if explicit_attribute:
        return True
    if role == "criterion":
        patterns = {
            "response_latency": r"(?=.*(?:p\d{2}|応答時間|response\s*time|latency))(?=.*\d+\s*(?:ms|s|秒|ミリ秒))",
            "authentication": r"(?=.*(?:login|authentication|認証))(?=.*(?:成功率|failure|success|%|合格))",
            "static_security": r"(?:sast|脆弱性|security).*(?:0件|zero|なし|検出)",
            "error_rate": r"(?:error\s*rate|failure\s*rate|エラー率|失敗率).*(?:\d|%|以下|以内)",
            "throughput": r"(?:throughput|rps|スループット|件/秒).*(?:\d|以上)",
        }
    elif role == "method":
        patterns = {
            "response_latency": (
                r"(?:search|検索|応答|response|latency).{0,40}"
                r"(?:測定する|計測する|試験する|検証する|(?:benchmark|ベンチマーク).{0,16}(?:実施する|実行する|測定する|計測する)|"
                r"\b(?:measure|test|verify|benchmark)(?:s|ed|ing)?\b)"
                r"|\b(?:measure|test|verify|benchmark)(?:s|ed|ing)?\b.{0,40}(?:search|検索|応答|response|latency)"
            ),
            "authentication": (
                r"(?:login|authentication|authn|ログイン|認証).{0,40}"
                r"(?:試験する|検証する|検査する|pytest.{0,16}(?:実施する|実行する|試験する)|"
                r"\b(?:test|verify|inspect)(?:s|ed|ing)?\b)"
                r"|\b(?:test|verify|inspect)(?:s|ed|ing)?\b.{0,40}(?:login|authentication|authn|ログイン|認証)"
            ),
            "static_security": (
                r"(?:sast|static\s+analysis|静的解析|脆弱性検査).{0,32}"
                r"(?:実施する|実行する|試験する|検査する|\b(?:run|execute|test|inspect)(?:s|ed|ing)?\b)"
            ),
            "error_rate": (
                r"(?:error\s*rate|failure\s*rate|エラー率|失敗率).{0,32}"
                r"(?:試験する|測定する|計測する|\b(?:test|measure)(?:s|ed|ing)?\b)"
            ),
            "throughput": (
                r"(?:throughput|rps|スループット|件/秒).{0,32}"
                r"(?:負荷試験する|測定する|計測する|\b(?:benchmark|measure|test)(?:s|ed|ing)?\b)"
            ),
        }
    else:
        patterns = {
            "response_latency": r"(?=.*(?:search|検索|応答|response|latency))(?=.*(?:bench|performance|負荷|性能|report|結果))",
            "authentication": r"(?=.*(?:login|authentication|ログイン|認証))(?=.*(?:log|report|result|ログ|結果))",
            "static_security": r"(?=.*(?:sast|security|静的解析|脆弱性))(?=.*(?:log|report|result|ログ|結果))",
            "error_rate": r"(?:error\s*rate|failure\s*rate|エラー率|失敗率).*(?:log|report|結果)",
            "throughput": r"(?:throughput|rps|スループット|件/秒).*(?:log|report|結果)",
        }
    pattern = patterns.get(dimension)
    return bool(pattern and re.search(pattern, text))


def _metric_target(entity: object) -> str:
    attributes = _entity_attributes(entity)
    for key in ("target", "metric_target", "threshold"):
        value = attributes.get(key)
        if value not in (None, ""):
            return str(value).strip().lower()
    text = _entity_text(entity).lower()
    match = re.search(r"(?:p\d{2}\s*)?\d+(?:\.\d+)?\s*(?:ms|s|秒|ミリ秒|%|rps|requests?/s)", text)
    return match.group(0).replace(" ", "") if match else ""


def _entity_evidence(ir: SemanticAssertionIR, entity: object) -> dict[str, object]:
    segment_id = str(_value(entity, "source_segment_id", ""))
    segment = _segment_map(ir).get(segment_id)
    excerpt = _entity_text(entity)
    field_name = ""
    if segment is not None:
        excerpt = str(_value(segment, "text", "") or excerpt)
        field_name = str(_value(segment, "field", ""))
    payload: dict[str, object] = {
        "entity_id": _entity_id(entity),
        "source_segment_id": segment_id,
        "excerpt": excerpt[:240],
    }
    if field_name:
        payload["field"] = field_name
    start = _value(entity, "start", None)
    end = _value(entity, "end", None)
    if isinstance(start, int):
        payload["start"] = start
    if isinstance(end, int):
        payload["end"] = end
    metadata = _value(ir, "metadata", {})
    source_layout = _value(metadata, "source_layout", {})
    coordinate_space = str(_value(source_layout, "coordinate_space", ""))
    if coordinate_space:
        payload["coordinate_space"] = coordinate_space
    if isinstance(start, int) and isinstance(end, int):
        for source_part in ("text", "context"):
            bounds = _value(source_layout, source_part, {})
            part_start = _value(bounds, "start", None)
            part_end = _value(bounds, "end", None)
            if (
                isinstance(part_start, int)
                and isinstance(part_end, int)
                and part_start <= start
                and end <= part_end
            ):
                payload["source_part"] = source_part
                break
    return payload


def _select_verification_pair(
    ir: SemanticAssertionIR,
    entities: Sequence[object],
    relations: Sequence[object],
) -> tuple[object | None, object | None, str, str]:
    criteria = [
        item
        for item in entities
        if _entity_kind(item) == "acceptance_criterion" and _entity_is_satisfying(ir, item)
    ]
    methods = [
        item
        for item in entities
        if _entity_kind(item) == "verification_method" and _entity_is_satisfying(ir, item)
    ]
    entity_by_id = {_entity_id(item): item for item in entities}
    verifies_pairs = {
        _relation_endpoints(item)
        for item in relations
        if str(_value(item, "kind", "")) == "verifies"
        and _relation_is_satisfying(ir, item)
        and _relation_endpoints(item)[0] in {_entity_id(method) for method in methods}
        and _relation_endpoints(item)[1] in {_entity_id(criterion) for criterion in criteria}
    }
    if len(verifies_pairs) == 1:
        method_id, criterion_id = next(iter(verifies_pairs))
        return entity_by_id.get(criterion_id), entity_by_id.get(method_id), "", ""
    if len(criteria) == 1 and len(methods) == 1:
        return criteria[0], methods[0], "", ""
    if criteria and methods:
        status = "conflict" if len(verifies_pairs) > 1 else "candidate"
        return None, None, "verification method to criterion pairing is not unique", status
    return None, None, "required verification pair is not asserted", "blocked_by_unknown"


def _verification_is_explicitly_aligned(
    ir: SemanticAssertionIR,
    entities: Sequence[object],
    relations: Sequence[object],
) -> bool:
    criterion, method, _, _ = _select_verification_pair(ir, entities, relations)
    if criterion is None or method is None:
        return False
    criterion_dimensions = _dimensions(criterion, "criterion")
    method_dimensions = _dimensions(method, "method")
    if len(criterion_dimensions) != 1 or criterion_dimensions != method_dimensions:
        return False
    dimension = next(iter(criterion_dimensions))
    return _dimension_is_explicit(criterion, "criterion", dimension) and _dimension_is_explicit(
        method, "method", dimension
    )


def _evidence_is_explicitly_aligned(
    ir: SemanticAssertionIR,
    entities: Sequence[object],
    relations: Sequence[object],
) -> bool:
    _, method, _, _ = _select_verification_pair(ir, entities, relations)
    if method is None:
        return False
    evidences = [
        item
        for item in entities
        if _entity_kind(item) == "evidence_artifact" and _entity_is_satisfying(ir, item)
    ]
    evidence_by_id = {_entity_id(item): item for item in evidences}
    pairs = {
        _relation_endpoints(item)
        for item in relations
        if str(_value(item, "kind", "")) == "produces_evidence"
        and _relation_is_satisfying(ir, item)
        and _relation_endpoints(item)[0] == _entity_id(method)
        and _relation_endpoints(item)[1] in evidence_by_id
    }
    if len(pairs) == 1:
        _, evidence_id = next(iter(pairs))
        evidence = evidence_by_id.get(evidence_id)
    elif len(evidences) == 1:
        evidence = evidences[0]
    else:
        return False
    if evidence is None:
        return False
    method_dimensions = _dimensions(method, "method")
    evidence_dimensions = _dimensions(evidence, "evidence")
    if len(method_dimensions) != 1 or method_dimensions != evidence_dimensions:
        return False
    dimension = next(iter(method_dimensions))
    return _dimension_is_explicit(method, "method", dimension) and _dimension_is_explicit(
        evidence, "evidence", dimension
    )


def _specialized_deltas(
    ir: SemanticAssertionIR,
    entities: Sequence[object],
    relations: Sequence[object],
    start_sequence: int,
) -> list[RelationDelta]:
    deltas: list[RelationDelta] = []
    criteria = [
        item
        for item in entities
        if _entity_kind(item) == "acceptance_criterion" and _entity_is_satisfying(ir, item)
    ]
    methods = [
        item
        for item in entities
        if _entity_kind(item) == "verification_method" and _entity_is_satisfying(ir, item)
    ]
    evidences = [
        item
        for item in entities
        if _entity_kind(item) == "evidence_artifact" and _entity_is_satisfying(ir, item)
    ]
    entity_by_id = {_entity_id(item): item for item in entities}
    criterion, method, pair_reason, pair_status = _select_verification_pair(
        ir, entities, relations
    )
    if criterion is None and method is None and criteria and methods:
        obligation = next(item for item in FUNCTIONAL_REQUIREMENT_PROFILE.obligations if item.id == "func.verifies")
        deltas.append(
            _delta(
                start_sequence + len(deltas),
                obligation,
                "ambiguous_scope",
                "conflict" if pair_status == "conflict" else "candidate",
                observed={
                    "criterion_entity_ids": sorted(_entity_id(item) for item in criteria),
                    "method_entity_ids": sorted(_entity_id(item) for item in methods),
                },
                basis={
                    "evidence_spans": [
                        _entity_evidence(ir, item) for item in (*criteria[:2], *methods[:2])
                    ]
                },
                unknown_reasons=(pair_reason,),
            )
        )

    if criterion is not None and method is not None:
        criterion_dimensions = _dimensions(criterion, "criterion")
        method_dimensions = _dimensions(method, "method")
        criterion_target = _metric_target(criterion)
        criterion_explicit = (
            len(criterion_dimensions) == 1
            and _dimension_is_explicit(
                criterion, "criterion", next(iter(criterion_dimensions))
            )
        )
        method_explicit = (
            len(method_dimensions) == 1
            and _dimension_is_explicit(method, "method", next(iter(method_dimensions)))
        )
        if (
            len(criterion_dimensions) == 1
            and len(method_dimensions) == 1
            and criterion_dimensions != method_dimensions
            and criterion_explicit
            and method_explicit
        ):
            criterion_dimension = next(iter(criterion_dimensions))
            method_dimension = next(iter(method_dimensions))
            obligation = next(item for item in FUNCTIONAL_REQUIREMENT_PROFILE.obligations if item.id == "func.verifies")
            deltas.append(
                _delta(
                    start_sequence + len(deltas),
                    obligation,
                    "verification_mismatch",
                    "derived",
                    observed={
                        "criterion_entity_id": _entity_id(criterion),
                        "criterion_dimension": criterion_dimension,
                        "criterion_target": criterion_target,
                        "method_entity_id": _entity_id(method),
                        "method_dimension": method_dimension,
                    },
                    basis={
                        "asserted_entity_ids": [_entity_id(criterion), _entity_id(method)],
                        "evidence_spans": [
                            _entity_evidence(ir, criterion),
                            _entity_evidence(ir, method),
                        ],
                    },
                    rule_id=VERIFICATION_TARGET_MISMATCH_RULE_ID,
                )
            )
        elif (
            len(criterion_dimensions) > 1
            or len(method_dimensions) > 1
            or (
                criterion_dimensions
                and method_dimensions
                and not (criterion_explicit and method_explicit)
            )
        ):
            obligation = next(item for item in FUNCTIONAL_REQUIREMENT_PROFILE.obligations if item.id == "func.verifies")
            deltas.append(
                _delta(
                    start_sequence + len(deltas),
                    obligation,
                    "verification_mismatch",
                    "candidate",
                    observed={
                        "criterion_entity_id": _entity_id(criterion),
                        "criterion_dimensions": sorted(criterion_dimensions),
                        "method_entity_id": _entity_id(method),
                        "method_dimensions": sorted(method_dimensions),
                    },
                    basis={
                        "asserted_entity_ids": [_entity_id(criterion), _entity_id(method)],
                        "evidence_spans": [
                            _entity_evidence(ir, criterion),
                            _entity_evidence(ir, method),
                        ],
                    },
                    unknown_reasons=(
                        "criterion or method target dimension is multiple, implicit, or low-confidence",
                    ),
                )
            )

    evidence: object | None = None
    if method is not None:
        evidence_pairs = {
            _relation_endpoints(item)
            for item in relations
            if str(_value(item, "kind", "")) == "produces_evidence"
            and _relation_is_satisfying(ir, item)
            and _relation_endpoints(item)[0] == _entity_id(method)
            and _relation_endpoints(item)[1] in {_entity_id(candidate) for candidate in evidences}
        }
        if len(evidence_pairs) == 1:
            _, evidence_id = next(iter(evidence_pairs))
            evidence = entity_by_id.get(evidence_id)
        elif len(evidences) == 1:
            evidence = evidences[0]
        elif evidences:
            obligation = next(
                item for item in FUNCTIONAL_REQUIREMENT_PROFILE.obligations if item.id == "func.produces_evidence"
            )
            deltas.append(
                _delta(
                    start_sequence + len(deltas),
                    obligation,
                    "ambiguous_scope",
                    "conflict" if len(evidence_pairs) > 1 else "candidate",
                    observed={
                        "method_entity_id": _entity_id(method),
                        "evidence_entity_ids": sorted(_entity_id(item) for item in evidences),
                        "pair_count": len(evidence_pairs),
                    },
                    basis={
                        "evidence_spans": [
                            _entity_evidence(ir, method),
                            *[_entity_evidence(ir, item) for item in evidences[:2]],
                        ]
                    },
                    unknown_reasons=("verification method to evidence pairing is not unique",),
                )
            )

    if method is not None and evidence is not None:
        method_dimensions = _dimensions(method, "method")
        evidence_dimensions = _dimensions(evidence, "evidence")
        if (
            len(method_dimensions) == 1
            and len(evidence_dimensions) == 1
            and method_dimensions != evidence_dimensions
            and _dimension_is_explicit(method, "method", next(iter(method_dimensions)))
            and _dimension_is_explicit(evidence, "evidence", next(iter(evidence_dimensions)))
        ):
            method_dimension = next(iter(method_dimensions))
            evidence_dimension = next(iter(evidence_dimensions))
            obligation = next(
                item for item in FUNCTIONAL_REQUIREMENT_PROFILE.obligations if item.id == "func.produces_evidence"
            )
            deltas.append(
                _delta(
                    start_sequence + len(deltas),
                    obligation,
                    "evidence_disconnect",
                    "derived",
                    observed={
                        "method_entity_id": _entity_id(method),
                        "method_dimension": method_dimension,
                        "evidence_entity_id": _entity_id(evidence),
                        "evidence_dimension": evidence_dimension,
                    },
                    basis={
                        "asserted_entity_ids": [_entity_id(method), _entity_id(evidence)],
                        "evidence_spans": [
                            _entity_evidence(ir, method),
                            _entity_evidence(ir, evidence),
                        ],
                    },
                )
            )
    return deltas


def audit_requirement_relations(
    text: str,
    context: str = "",
    *,
    morphology_provider: object | None = None,
    dependency_provider: object | None = None,
    llm_candidates: object | None = None,
) -> RequirementRelationAudit:
    """Extract and compare a functional requirement record conservatively.

    Providers are passed through to the extractor.  Their output may enlarge
    candidate coverage but cannot, by itself, satisfy an obligation here.
    """

    ir = extract_semantic_assertions(
        text,
        context=context,
        morphology_provider=morphology_provider,
        dependency_provider=dependency_provider,
        llm_candidates=llm_candidates,
    )
    profile = FUNCTIONAL_REQUIREMENT_PROFILE
    entities = _items(ir, "entities")
    relations = _items(ir, "relations")
    applicability_status, applicability_reasons = _profile_applicability(ir, entities)
    if applicability_status != "applicable":
        obligation = profile.obligations[0]
        if applicability_status == "not_applicable":
            kind: DeltaKind = "unknown_applicability"
            status: DeltaStatus = "not_applicable"
        elif applicability_status == "conflict":
            kind = "unknown_applicability"
            status = "conflict"
        else:
            kind = (
                "unmapped_expression"
                if not _coverage_is_closed(ir)
                or any("undifferentiated source span" in reason for reason in applicability_reasons)
                else "unknown_applicability"
            )
            status = "blocked_by_unknown"
        return RequirementRelationAudit(
            ir=ir,
            profile=profile,
            satisfied_obligation_ids=[],
            deltas=[
                _delta(
                    1,
                    obligation,
                    kind,
                    status,
                    unknown_reasons=applicability_reasons,
                )
            ],
            applicability_status=applicability_status,
            applicability_reasons=applicability_reasons,
        )
    satisfying_entities = [item for item in entities if _entity_is_satisfying(ir, item)]
    satisfying_entity_ids = {_entity_id(item) for item in satisfying_entities}
    satisfying_relations = [item for item in relations if _relation_is_satisfying(ir, item)]
    closed = _coverage_is_closed(ir)

    satisfied: list[str] = []
    deltas: list[RelationDelta] = []
    for obligation in profile.obligations:
        from_all = [item for item in entities if _entity_kind(item) == obligation.from_kind]
        to_all = [item for item in entities if _entity_kind(item) == obligation.to_kind]
        from_asserted = [item for item in from_all if _entity_id(item) in satisfying_entity_ids]
        to_asserted = [item for item in to_all if _entity_id(item) in satisfying_entity_ids]

        applicable: bool | None
        if obligation.necessity == "required":
            applicable = True
        elif to_asserted:
            applicable = True
        elif any(_entity_state(item) in {"candidate", "unknown", "conflict"} for item in to_all):
            applicable = None
        else:
            applicable = False

        if applicable is False:
            continue
        if applicable is None:
            deltas.append(
                _delta(
                    len(deltas) + 1,
                    obligation,
                    "unknown_applicability",
                    "blocked_by_unknown",
                    observed=_observed(obligation, from_all, to_all, relations),
                    unknown_reasons=("conditional target is not asserted",),
                )
            )
            continue

        if not from_asserted or not to_asserted:
            rejected = any(_entity_state(item) == "rejected" for item in (*from_all, *to_all))
            if closed or rejected:
                kind: DeltaKind = "missing_node"
                status: DeltaStatus = "derived"
                reasons = ("required endpoint is explicitly absent or rejected",) if rejected else ()
            else:
                kind = "unmapped_expression"
                status = "blocked_by_unknown"
                reasons = ("open text does not establish the required endpoint",)
            deltas.append(
                _delta(
                    len(deltas) + 1,
                    obligation,
                    kind,
                    status,
                    observed=_observed(obligation, from_all, to_all, relations),
                    unknown_reasons=reasons,
                )
            )
            continue

        matching_relations: list[object] = []
        wrong_attachment: list[object] = []
        for relation in satisfying_relations:
            if str(_value(relation, "kind", "")) != obligation.relation_kind:
                continue
            from_id, to_id = _relation_endpoints(relation)
            if from_id in {_entity_id(item) for item in from_asserted} and to_id in {
                _entity_id(item) for item in to_asserted
            }:
                matching_relations.append(relation)
            elif from_id in {_entity_id(item) for item in from_asserted} or to_id in {
                _entity_id(item) for item in to_asserted
            }:
                wrong_attachment.append(relation)

        if matching_relations:
            satisfied.append(obligation.id)
            continue

        relevant_relations = [
            item for item in relations if str(_value(item, "kind", "")) == obligation.relation_kind
        ]
        candidate_relations = [
            item
            for item in relevant_relations
            if str(_value(item, "state", "")) in {"candidate", "unknown", "conflict"}
            or _relation_is_coexistence_only(item)
            or _support_source_is_candidate_only(ir, item)
            or not _current_binding(ir, item)
        ]
        if wrong_attachment:
            kind = "wrong_attachment"
            status = "derived"
            reasons = ()
        elif candidate_relations:
            has_conflict = any(str(_value(item, "state", "")) == "conflict" for item in candidate_relations)
            kind = "ambiguous_scope"
            status = "conflict" if has_conflict else "candidate"
            reasons = ("only candidate or non-current relation interpretations exist",)
        elif closed:
            kind = "missing_relation"
            status = "derived"
            reasons = ()
        else:
            kind = "unmapped_expression"
            status = "blocked_by_unknown"
            reasons = ("open text does not establish the required relation",)
        deltas.append(
            _delta(
                len(deltas) + 1,
                obligation,
                kind,
                status,
                observed=_observed(obligation, from_all, to_all, relevant_relations),
                unknown_reasons=reasons,
            )
        )

    specialized = _specialized_deltas(ir, entities, relations, len(deltas) + 1)
    if _verification_is_explicitly_aligned(ir, entities, relations):
        deltas = [item for item in deltas if item.obligation_id != "func.verifies"]
        if "func.verifies" not in satisfied:
            satisfied.append("func.verifies")
    elif any(item.obligation_id == "func.verifies" for item in specialized):
        deltas = [item for item in deltas if item.obligation_id != "func.verifies"]
        satisfied = [item for item in satisfied if item != "func.verifies"]
    if _evidence_is_explicitly_aligned(ir, entities, relations):
        deltas = [item for item in deltas if item.obligation_id != "func.produces_evidence"]
        if "func.produces_evidence" not in satisfied:
            satisfied.append("func.produces_evidence")
    elif any(item.obligation_id == "func.produces_evidence" for item in specialized):
        deltas = [item for item in deltas if item.obligation_id != "func.produces_evidence"]
        satisfied = [item for item in satisfied if item != "func.produces_evidence"]
    deltas.extend(specialized)
    return RequirementRelationAudit(
        ir=ir,
        profile=profile,
        satisfied_obligation_ids=sorted(satisfied),
        deltas=deltas,
        applicability_status="applicable",
        applicability_reasons=[],
    )


__all__ = [
    "FUNCTIONAL_REQUIREMENT_PROFILE",
    "FUNCTIONAL_REQUIREMENT_PROFILE_ID",
    "RELATION_AUDIT_SCHEMA_VERSION",
    "RELATION_DELTA_SCHEMA_VERSION",
    "RELATION_PROFILE_SCHEMA_VERSION",
    "RELATION_SUMMARY_SCHEMA_VERSION",
    "VERIFICATION_TARGET_MISMATCH_RULE_ID",
    "RelationDelta",
    "RelationObligation",
    "RequirementRelationAudit",
    "RequirementRelationProfile",
    "audit_requirement_relations",
]
