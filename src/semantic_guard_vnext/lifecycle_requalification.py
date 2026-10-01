"""Occurrence relations and conservative reverse-dependency requalification.

Relations never overwrite prior occurrences.  Impact closure is derived from
content-addressed dependency evidence; incomplete or dangling graphs expand to
the entire known denominator instead of claiming a precise boundary.
"""

from __future__ import annotations

from typing import Any, Callable, Mapping, Sequence

from .lifecycle_governance import (
    LifecycleGovernanceError,
    _copy,
    _digest,
    _record_key,
    _schema_validate,
    _validate_digest,
)


OCCURRENCE_RELATION_VERSION = "lifecycle-occurrence-relation/v1"
IMPACT_CLOSURE_VERSION = "lifecycle-impact-closure/v1"
GraphVerifier = Callable[[Mapping[str, Any]], bool]

_TRUST_ROOT_UNRESOLVED = "control_plane_trust_registry_not_integrated"
_CALLBACK_LIMITATION = (
    "A supplied graph-verifier callback and verifier_ref can record a verifier "
    "claim only; they are not a control-plane trust registry or signature trust root."
)


class LifecycleRequalificationError(LifecycleGovernanceError):
    """Raised when a relation or impact boundary cannot be replayed."""


def _occurrence_key(value: Mapping[str, Any]) -> tuple[str, str]:
    return (
        str(value["stage_occurrence_id"]),
        str(value["occurrence_digest"]["value"]),
    )


def build_occurrence_relation(
    *,
    relation_id: str,
    relation_kind: str,
    source_occurrence_ref: Mapping[str, Any],
    target_occurrence_ref: Mapping[str, Any],
    basis_refs: Sequence[Mapping[str, Any]],
    actor_ref: Mapping[str, Any],
    recorded_at: str,
    authority_ref: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    material = {
        "schema_version": OCCURRENCE_RELATION_VERSION,
        "relation_id": relation_id,
        "relation_kind": relation_kind,
        "source_occurrence_ref": _copy(source_occurrence_ref),
        "target_occurrence_ref": _copy(target_occurrence_ref),
        "basis_refs": sorted((_copy(item) for item in basis_refs), key=_record_key),
        "actor_ref": _copy(actor_ref),
        "authority_ref": _copy(authority_ref) if authority_ref else None,
        "recorded_at": recorded_at,
        "formal_authority": "none",
    }
    result = {**material, "relation_digest": _digest(material)}
    validate_occurrence_relation(result)
    return result


def validate_occurrence_relation(relation: Mapping[str, Any]) -> dict[str, Any]:
    _schema_validate(relation, "occurrenceRelation", "lifecycle occurrence relation")
    if _occurrence_key(relation["source_occurrence_ref"]) == _occurrence_key(
        relation["target_occurrence_ref"]
    ):
        raise LifecycleRequalificationError("an occurrence cannot relate to itself")
    if (
        relation["relation_kind"]
        in {"supersedes", "reopens", "repair_of", "invalidates"}
        and relation["authority_ref"] is None
    ):
        raise LifecycleRequalificationError(
            f"{relation['relation_kind']} relation requires authority evidence"
        )
    if relation["formal_authority"] != "none":
        raise LifecycleRequalificationError(
            "relation record cannot hold formal authority"
        )
    _validate_digest(relation, "relation_digest", "occurrence relation")
    return _copy(relation)


def _unique_records(
    refs: Sequence[Mapping[str, Any]], *, label: str
) -> dict[tuple[str, str, str], dict[str, Any]]:
    result: dict[tuple[str, str, str], dict[str, Any]] = {}
    for value in refs:
        key = _record_key(value)
        if key in result:
            raise LifecycleRequalificationError(f"duplicate {label} reference: {key!r}")
        result[key] = _copy(value)
    return result


def _graph_verification_context(
    *,
    changed_refs: Sequence[Mapping[str, Any]],
    denominator_refs: Sequence[Mapping[str, Any]],
    dependency_edges: Sequence[Mapping[str, Any]],
    reported_graph_completeness: str,
    graph_manifest_ref: Mapping[str, Any] | None,
) -> dict[str, Any]:
    return {
        "changed_refs": sorted((_copy(item) for item in changed_refs), key=_record_key),
        "known_denominator_refs": sorted(
            (_copy(item) for item in denominator_refs), key=_record_key
        ),
        "dependency_edges": sorted(
            (_copy(item) for item in dependency_edges),
            key=lambda edge: (
                _record_key(edge["source_ref"]),
                _record_key(edge["dependent_ref"]),
                edge["dependency_kind"],
            ),
        ),
        "reported_graph_completeness": reported_graph_completeness,
        "graph_manifest_ref": (
            _copy(graph_manifest_ref) if graph_manifest_ref is not None else None
        ),
    }


def _graph_verifier_ref(
    trusted_graph_verifier: GraphVerifier | None,
) -> dict[str, Any] | None:
    if trusted_graph_verifier is None:
        return None
    verifier_ref = getattr(trusted_graph_verifier, "verifier_ref", None)
    if not isinstance(verifier_ref, Mapping):
        return None
    try:
        _schema_validate(verifier_ref, "recordRef", "trusted graph verifier")
    except LifecycleGovernanceError:
        return None
    return _copy(verifier_ref)


def _evaluate_graph_trust(
    context: Mapping[str, Any],
    trusted_graph_verifier: GraphVerifier | None,
) -> tuple[str, dict[str, Any] | None, str, list[str]]:
    denominator = _unique_records(
        context["known_denominator_refs"], label="denominator"
    )
    changed = _unique_records(context["changed_refs"], label="changed")
    structural_reasons: list[str] = []
    if context["reported_graph_completeness"] != "complete":
        structural_reasons.append("reported_graph_completeness_unknown")
    if context["graph_manifest_ref"] is None:
        structural_reasons.append("graph_manifest_missing")
    if set(changed) - set(denominator):
        structural_reasons.append("changed_reference_outside_known_denominator")
    for edge in context["dependency_edges"]:
        if (
            _record_key(edge["source_ref"]) not in denominator
            or _record_key(edge["dependent_ref"]) not in denominator
        ):
            structural_reasons.append("dependency_edge_outside_known_denominator")
    if structural_reasons:
        return (
            "unresolved",
            None,
            "not_evaluated",
            sorted(set([*structural_reasons, _TRUST_ROOT_UNRESOLVED])),
        )
    if trusted_graph_verifier is None:
        return (
            "unresolved",
            None,
            "not_supplied",
            [_TRUST_ROOT_UNRESOLVED, "trusted_graph_verifier_missing"],
        )
    verifier_ref = _graph_verifier_ref(trusted_graph_verifier)
    if verifier_ref is None:
        return (
            "unresolved",
            None,
            "verifier_ref_invalid",
            [_TRUST_ROOT_UNRESOLVED, "trusted_graph_verifier_ref_invalid"],
        )
    try:
        verified = bool(trusted_graph_verifier(_copy(context)))
    except Exception:
        return (
            "unresolved",
            verifier_ref,
            "verifier_unavailable",
            [_TRUST_ROOT_UNRESOLVED, "trusted_graph_verifier_unavailable"],
        )
    if not verified:
        return (
            "unresolved",
            verifier_ref,
            "verifier_claim_rejected",
            [_TRUST_ROOT_UNRESOLVED, "trusted_graph_verifier_rejected_manifest"],
        )
    return (
        "unresolved",
        verifier_ref,
        "verifier_claim_accepted",
        [_TRUST_ROOT_UNRESOLVED, "verifier_claim_accepted_without_trust_root"],
    )


def _derive_impact(
    *,
    context: Mapping[str, Any],
    graph_trust_reasons: Sequence[str],
) -> tuple[list[dict[str, Any]], str, list[str], list[str]]:
    denominator_refs = context["known_denominator_refs"]
    denominator = _unique_records(denominator_refs, label="denominator")
    reasons = list(graph_trust_reasons)
    limitations = [
        "Impact closure is candidate requalification evidence and does not itself invalidate, waive, or accept any record.",
        "Reverse indexes and caches are reproducible aids, not evidence originals.",
        _CALLBACK_LIMITATION,
    ]

    impacted_keys = set(denominator)
    reasons.append("safe_scope_expansion_required")
    limitations.append(
        "The exact impact boundary was not provable; all known denominator records require requalification."
    )
    scope_status = "safe_expanded_to_known_denominator"

    impacted = [denominator[key] for key in sorted(impacted_keys)]
    return impacted, scope_status, sorted(set(reasons)), sorted(set(limitations))


def build_impact_closure(
    *,
    impact_id: str,
    changed_refs: Sequence[Mapping[str, Any]],
    known_denominator_refs: Sequence[Mapping[str, Any]],
    dependency_edges: Sequence[Mapping[str, Any]],
    reported_graph_completeness: str,
    graph_manifest_ref: Mapping[str, Any] | None = None,
    trusted_graph_verifier: GraphVerifier | None = None,
) -> dict[str, Any]:
    context = _graph_verification_context(
        changed_refs=changed_refs,
        denominator_refs=known_denominator_refs,
        dependency_edges=dependency_edges,
        reported_graph_completeness=reported_graph_completeness,
        graph_manifest_ref=graph_manifest_ref,
    )
    (
        graph_trust_state,
        graph_verifier_ref,
        graph_verifier_claim,
        graph_trust_reasons,
    ) = _evaluate_graph_trust(context, trusted_graph_verifier)
    impacted, scope_status, reasons, limitations = _derive_impact(
        context=context,
        graph_trust_reasons=graph_trust_reasons,
    )
    material = {
        "schema_version": IMPACT_CLOSURE_VERSION,
        "impact_id": impact_id,
        "changed_refs": context["changed_refs"],
        "known_denominator_refs": context["known_denominator_refs"],
        "dependency_edges": context["dependency_edges"],
        "reported_graph_completeness": reported_graph_completeness,
        "graph_manifest_ref": context["graph_manifest_ref"],
        "graph_trust_state": graph_trust_state,
        "graph_verifier_claim": graph_verifier_claim,
        "graph_verifier_ref": graph_verifier_ref,
        "graph_verification_input_digest": _digest(context),
        "trust_root_resolution_state": "not_integrated",
        "trust_root_ref": None,
        "impacted_refs": impacted,
        "scope_status": scope_status,
        "requalification_required": True,
        "reasons": reasons,
        "formal_authority": "none",
        "limitations": limitations,
    }
    result = {**material, "impact_digest": _digest(material)}
    validate_impact_closure(result, trusted_graph_verifier=trusted_graph_verifier)
    return result


def validate_impact_closure(
    impact: Mapping[str, Any],
    *,
    trusted_graph_verifier: GraphVerifier | None = None,
) -> dict[str, Any]:
    _schema_validate(impact, "impactClosure", "lifecycle impact closure")
    context = _graph_verification_context(
        changed_refs=impact["changed_refs"],
        denominator_refs=impact["known_denominator_refs"],
        dependency_edges=impact["dependency_edges"],
        reported_graph_completeness=str(impact["reported_graph_completeness"]),
        graph_manifest_ref=impact["graph_manifest_ref"],
    )
    if impact["graph_verification_input_digest"] != _digest(context):
        raise LifecycleRequalificationError(
            "graph verification input digest does not replay"
        )
    (
        graph_trust_state,
        graph_verifier_ref,
        graph_verifier_claim,
        graph_trust_reasons,
    ) = _evaluate_graph_trust(context, trusted_graph_verifier)
    if (
        impact["graph_trust_state"] != graph_trust_state
        or impact["graph_verifier_claim"] != graph_verifier_claim
        or impact["graph_verifier_ref"] != graph_verifier_ref
    ):
        raise LifecycleRequalificationError(
            "graph trust state does not replay through its trusted verifier"
        )
    derived, scope_status, reasons, limitations = _derive_impact(
        context=context,
        graph_trust_reasons=graph_trust_reasons,
    )
    if impact["impacted_refs"] != derived:
        raise LifecycleRequalificationError(
            "impact set does not replay from dependency evidence"
        )
    if impact["scope_status"] != scope_status or impact["reasons"] != reasons:
        raise LifecycleRequalificationError(
            "impact scope status or reasons do not replay"
        )
    if impact["limitations"] != limitations:
        raise LifecycleRequalificationError("impact limitations do not replay")
    if (
        impact["trust_root_resolution_state"] != "not_integrated"
        or impact["trust_root_ref"] is not None
    ):
        raise LifecycleRequalificationError(
            "impact closure cannot self-establish an external trust root"
        )
    if impact["formal_authority"] != "none":
        raise LifecycleRequalificationError(
            "impact closure cannot hold formal authority"
        )
    _validate_digest(impact, "impact_digest", "impact closure")
    return _copy(impact)
