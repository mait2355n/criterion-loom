"""Typed lifecycle trace and composition validation.

This module checks whether meaning and audit material are carried across ten
development stages.  A valid graph proves only internal, content-addressed
composition under the declared rules.  It does not grant authority, establish
evidence authenticity, or perform human final acceptance.
"""

from __future__ import annotations

import copy
from functools import lru_cache
import hashlib
import json
from typing import Any, Iterable, Mapping, Sequence

from jsonschema import Draft202012Validator, FormatChecker

from .schema_access import schema_path


SCHEMA_VERSION = "lifecycle-trace/v0"
COMPOSITION_PROFILE_ID = "profile.lifecycle-trace-composition"
COMPOSITION_PROFILE_VERSION = "0.1.0"

STAGES = (
    "request",
    "exploration_question",
    "requirement",
    "decision",
    "plan",
    "action",
    "realization",
    "diff",
    "verification",
    "completion_claim",
)
STAGE_RANK = {stage: index for index, stage in enumerate(STAGES)}

EDGE_KINDS = (
    "refines",
    "transforms",
    "derives",
    "verifies",
    "supersedes",
    "branches",
    "merges",
    "cancels",
    "completes",
)

TRUST_RANK = {
    "unverified": 0,
    "self_reported": 1,
    "tool_observed": 2,
    "independently_observed": 3,
    "signed": 4,
    "formally_verified": 5,
}
FRESHNESS_RANK = {"unknown": 0, "stale": 1, "current": 2}

_SCHEMA_PATH = schema_path("lifecycle-trace.schema.json")

_DEFAULT_LIMITATIONS = (
    "Graph validity establishes declared composition and preservation only, not external truth.",
    "Evidence trust and freshness labels remain bounded by their declared observation and authority records.",
    "semantic-guard validates human authority records but does not create, approve, or replace human decisions.",
)


class LifecycleTraceValidationError(ValueError):
    """Raised when a lifecycle trace fails schema or semantic validation."""

    def __init__(self, errors: Sequence[Mapping[str, str]]) -> None:
        self.errors = tuple(dict(item) for item in errors)
        self.codes = tuple(str(item["code"]) for item in self.errors)
        summary = "; ".join(
            f"{item['code']}@{item['location']}: {item['message']}"
            for item in self.errors[:8]
        )
        if len(self.errors) > 8:
            summary += f"; ... {len(self.errors) - 8} more"
        super().__init__(summary)


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    """Return the deterministic SHA-256 of canonical JSON material."""

    return hashlib.sha256(_canonical(value)).hexdigest()


def digest_value(value: Any) -> dict[str, str]:
    return {"algorithm": "sha256", "value": canonical_sha256(value)}


def versioned_ref(ref_id: str, version: str, material: Any | None = None) -> dict[str, Any]:
    basis = {"ref_id": ref_id, "version": version} if material is None else material
    return {"ref_id": ref_id, "version": version, "digest": digest_value(basis)}


def _sorted_dicts(values: Iterable[Mapping[str, Any]], *keys: str) -> list[dict[str, Any]]:
    copied = [copy.deepcopy(dict(item)) for item in values]
    return sorted(copied, key=lambda item: tuple(str(item.get(key, "")) for key in keys))


def _normalize_completion(value: Mapping[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(dict(value))
    result["verification_node_refs"] = sorted(set(result["verification_node_refs"]))
    result["obligation_trace"] = _sorted_dicts(
        result["obligation_trace"], "obligation_id", "verification_node_ref"
    )
    result["residual_unproven_scope"] = _sorted_dicts(
        result["residual_unproven_scope"], "unresolved_ref", "source_node_ref"
    )
    return result


def build_lifecycle_node(
    *,
    stage: str,
    subject: Mapping[str, Any],
    proposition: Mapping[str, Any],
    obligation_states: Iterable[Mapping[str, Any]],
    unresolved_refs: Iterable[str],
    evidence_refs: Iterable[Mapping[str, Any]],
    authority_rights: Iterable[str],
    profile_refs: Iterable[Mapping[str, Any]],
    rule_refs: Iterable[Mapping[str, Any]],
    actor: Mapping[str, Any],
    observer: Mapping[str, Any],
    recorded_at: str,
    completion: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one content-addressed lifecycle node without external effects."""

    if stage not in STAGE_RANK:
        raise ValueError(f"unknown lifecycle stage: {stage}")
    material: dict[str, Any] = {
        "stage": stage,
        "subject": copy.deepcopy(dict(subject)),
        "proposition": copy.deepcopy(dict(proposition)),
        "obligation_states": _sorted_dicts(obligation_states, "obligation_id"),
        "unresolved_refs": sorted(set(unresolved_refs)),
        "evidence_refs": _sorted_dicts(evidence_refs, "evidence_id"),
        "authority_rights": sorted(set(authority_rights)),
        "profile_refs": _sorted_dicts(profile_refs, "ref_id", "version"),
        "rule_refs": _sorted_dicts(rule_refs, "ref_id", "version"),
        "actor": copy.deepcopy(dict(actor)),
        "observer": copy.deepcopy(dict(observer)),
        "recorded_at": recorded_at,
    }
    if completion is not None:
        material["completion"] = _normalize_completion(completion)
    node_hash = canonical_sha256(material)
    return {
        "node_id": f"lifecycle-node.{stage}.{node_hash[:24]}",
        **material,
        "node_digest": {"algorithm": "sha256", "value": node_hash},
    }


def build_pair_preservation(
    input_node: Mapping[str, Any],
    output_node: Mapping[str, Any],
    *,
    obligation_transitions: Mapping[str, Mapping[str, Any]] | None = None,
    unresolved_transitions: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Build a conservative one-input/one-output preservation map.

    New output obligations, unresolved items, evidence, or rights are not
    silently justified here.  The validator separately checks any authority
    escalation and every input item must have one disposition.
    """

    input_ref = str(input_node["node_id"])
    output_ref = str(output_node["node_id"])
    obligation_overrides = obligation_transitions or {}
    unresolved_overrides = unresolved_transitions or {}
    obligations: list[dict[str, Any]] = []
    for obligation in input_node["obligation_states"]:
        obligation_id = str(obligation["obligation_id"])
        override = dict(obligation_overrides.get(obligation_id, {}))
        obligations.append(
            {
                "input_node_ref": input_ref,
                "output_node_ref": output_ref,
                "input_obligation_id": obligation_id,
                "output_obligation_id": override.get("output_obligation_id", obligation_id),
                "transition": override.get("transition", "carried"),
                "resolution_record_ref": override.get("resolution_record_ref"),
                "authority_record_ref": override.get("authority_record_ref"),
            }
        )
    unresolved: list[dict[str, Any]] = []
    for unresolved_ref in input_node["unresolved_refs"]:
        override = dict(unresolved_overrides.get(str(unresolved_ref), {}))
        unresolved.append(
            {
                "input_node_ref": input_ref,
                "output_node_ref": output_ref,
                "unresolved_ref": unresolved_ref,
                "status": override.get("status", "carried"),
                "resolution_record_ref": override.get("resolution_record_ref"),
                "authority_record_ref": override.get("authority_record_ref"),
            }
        )
    return {
        "subjects": [
            {
                "input_node_ref": input_ref,
                "output_node_ref": output_ref,
                "status": "preserved",
                "authority_record_ref": None,
            }
        ],
        "propositions": [
            {
                "input_node_ref": input_ref,
                "output_node_ref": output_ref,
                "status": "preserved",
                "authority_record_ref": None,
            }
        ],
        "obligations": obligations,
        "unresolved": unresolved,
        "evidence": [
            {
                "input_node_ref": input_ref,
                "output_node_ref": output_ref,
                "evidence_id": item["evidence_id"],
                "status": "preserved",
                "authority_record_ref": None,
            }
            for item in input_node["evidence_refs"]
        ],
        "authority": [
            {
                "input_node_ref": input_ref,
                "output_node_ref": output_ref,
                "right": right,
                "status": "preserved",
                "authority_record_ref": None,
            }
            for right in input_node["authority_rights"]
        ],
    }


def _normalize_preservation(value: Mapping[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(dict(value))
    sort_keys = {
        "subjects": ("input_node_ref", "output_node_ref", "status"),
        "propositions": ("input_node_ref", "output_node_ref", "status"),
        "obligations": (
            "input_node_ref",
            "output_node_ref",
            "input_obligation_id",
            "transition",
        ),
        "unresolved": (
            "input_node_ref",
            "output_node_ref",
            "unresolved_ref",
            "status",
        ),
        "evidence": (
            "input_node_ref",
            "output_node_ref",
            "evidence_id",
            "status",
        ),
        "authority": ("input_node_ref", "output_node_ref", "right", "status"),
    }
    for field, keys in sort_keys.items():
        result[field] = _sorted_dicts(result.get(field, []), *keys)
    return result


def build_composition_edge(
    *,
    edge_kind: str,
    composition_rule_id: str,
    composition_rule_version: str,
    input_node_refs: Iterable[str],
    output_node_refs: Iterable[str],
    preservation: Mapping[str, Any],
    allowed_changes: Iterable[str] = (),
    decision_refs: Iterable[str] = (),
    evidence_refs: Iterable[str] = (),
) -> dict[str, Any]:
    """Build one deterministic typed composition edge."""

    if edge_kind not in EDGE_KINDS:
        raise ValueError(f"unknown lifecycle edge kind: {edge_kind}")
    rule_material = {
        "rule_id": composition_rule_id,
        "version": composition_rule_version,
    }
    material = {
        "edge_kind": edge_kind,
        "composition_rule": {
            **rule_material,
            "digest": digest_value(rule_material),
        },
        "input_node_refs": sorted(set(input_node_refs)),
        "output_node_refs": sorted(set(output_node_refs)),
        "preservation": _normalize_preservation(preservation),
        "allowed_changes": sorted(set(allowed_changes)),
        "decision_refs": sorted(set(decision_refs)),
        "evidence_refs": sorted(set(evidence_refs)),
    }
    edge_hash = canonical_sha256(material)
    return {
        "edge_id": f"lifecycle-edge.{edge_kind}.{edge_hash[:24]}",
        **material,
        "edge_digest": {"algorithm": "sha256", "value": edge_hash},
    }


def build_lifecycle_trace(
    *,
    trace_id: str,
    nodes: Iterable[Mapping[str, Any]],
    edges: Iterable[Mapping[str, Any]],
    authority_records: Iterable[Mapping[str, Any]] = (),
    resolution_records: Iterable[Mapping[str, Any]] = (),
    limitations: Iterable[str] = _DEFAULT_LIMITATIONS,
    origin_trace: Iterable[str] = ("OR-01", "OR-02", "OR-03"),
) -> dict[str, Any]:
    """Build a deterministic lifecycle trace.  It does not auto-accept it."""

    material = {
        "schema_version": SCHEMA_VERSION,
        "trace_id": trace_id,
        "origin_trace": sorted(set(origin_trace)),
        "composition_profile": versioned_ref(
            COMPOSITION_PROFILE_ID,
            COMPOSITION_PROFILE_VERSION,
        ),
        "nodes": _sorted_dicts(nodes, "node_id"),
        "edges": _sorted_dicts(edges, "edge_id"),
        "authority_records": _sorted_dicts(authority_records, "record_id"),
        "resolution_records": _sorted_dicts(resolution_records, "resolution_id"),
        "limitations": sorted(set(limitations)),
    }
    return {**material, "graph_digest": digest_value(material)}


@lru_cache(maxsize=1)
def _schema_validator() -> Draft202012Validator:
    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _add(
    errors: list[dict[str, str]],
    code: str,
    location: str,
    message: str,
) -> None:
    errors.append({"code": code, "location": location, "message": message})


def _schema_location(path: Any) -> str:
    values = [str(item) for item in path]
    return "$" if not values else "$." + ".".join(values)


def _duplicates(values: Iterable[str]) -> set[str]:
    seen: set[str] = set()
    duplicate: set[str] = set()
    for value in values:
        if value in seen:
            duplicate.add(value)
        seen.add(value)
    return duplicate


def _node_material(node: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: copy.deepcopy(value)
        for key, value in node.items()
        if key not in {"node_id", "node_digest"}
    }


def _edge_material(edge: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: copy.deepcopy(value)
        for key, value in edge.items()
        if key not in {"edge_id", "edge_digest"}
    }


def _trace_material(trace: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: copy.deepcopy(value)
        for key, value in trace.items()
        if key != "graph_digest"
    }


def _obligations(node: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {str(item["obligation_id"]): item for item in node["obligation_states"]}


def _evidence(node: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {str(item["evidence_id"]): item for item in node["evidence_refs"]}


def _version_identity(value: Mapping[str, Any]) -> tuple[str, str]:
    return str(value["ref_id"]), str(value["version"])


def _pair_items(
    values: Iterable[Mapping[str, Any]], input_ref: str, output_ref: str
) -> list[Mapping[str, Any]]:
    return [
        item
        for item in values
        if item["input_node_ref"] == input_ref
        and item["output_node_ref"] == output_ref
    ]


def _authority_for_change(
    *,
    reference: str | None,
    expected_types: set[str],
    edge: Mapping[str, Any],
    input_ref: str,
    output_ref: str,
    authority_records: Mapping[str, Mapping[str, Any]],
    errors: list[dict[str, str]],
    location: str,
    code: str,
    right: str | None = None,
    obligation_id: str | None = None,
) -> Mapping[str, Any] | None:
    if not reference or reference not in authority_records:
        _add(errors, code, location, "required human authority record is missing")
        return None
    record = authority_records[reference]
    if record["record_type"] not in expected_types:
        _add(
            errors,
            code,
            location,
            f"authority record type {record['record_type']} is not one of {sorted(expected_types)}",
        )
    if reference not in edge["decision_refs"]:
        _add(errors, code, location, "authority record is not cited by edge decision_refs")
    if input_ref not in record["node_refs"] or output_ref not in record["node_refs"]:
        _add(errors, code, location, "authority record does not scope both endpoint nodes")
    if right is not None and right not in record["rights"]:
        _add(errors, code, location, f"authority record does not scope right: {right}")
    if obligation_id is not None and obligation_id not in record["obligation_refs"]:
        _add(
            errors,
            code,
            location,
            f"authority record does not scope obligation: {obligation_id}",
        )
    return record


def _resolution_for_transition(
    *,
    reference: str | None,
    transition: str,
    obligation_id: str,
    unresolved_ref: str | None,
    input_ref: str,
    output_ref: str,
    edge: Mapping[str, Any],
    resolution_records: Mapping[str, Mapping[str, Any]],
    authority_records: Mapping[str, Mapping[str, Any]],
    nodes: Mapping[str, Mapping[str, Any]],
    errors: list[dict[str, str]],
    location: str,
) -> Mapping[str, Any] | None:
    if not reference or reference not in resolution_records:
        _add(errors, "resolution_record_missing", location, "located resolution record is missing")
        return None
    record = resolution_records[reference]
    if record["status"] != transition:
        _add(
            errors,
            "resolution_status_mismatch",
            location,
            f"resolution status {record['status']} does not match {transition}",
        )
    if (
        record["obligation_id"] != obligation_id
        or record["input_node_ref"] != input_ref
        or record["output_node_ref"] != output_ref
    ):
        _add(
            errors,
            "resolution_scope_mismatch",
            location,
            "resolution record is not bound to the mapped obligation and endpoints",
        )
    if unresolved_ref is not None and unresolved_ref not in record["unresolved_refs"]:
        _add(
            errors,
            "resolution_unresolved_mismatch",
            location,
            f"resolution record does not name unresolved item: {unresolved_ref}",
        )
    output = nodes[output_ref]
    output_evidence = _evidence(output)
    for evidence_ref in record["evidence_refs"]:
        if evidence_ref not in output_evidence:
            _add(
                errors,
                "resolution_evidence_missing",
                location,
                f"resolution evidence is not located in output node: {evidence_ref}",
            )
        if evidence_ref not in edge["evidence_refs"]:
            _add(
                errors,
                "resolution_evidence_not_cited",
                location,
                f"edge does not cite resolution evidence: {evidence_ref}",
            )
    output_rules = {_version_identity(item): item for item in output["rule_refs"]}
    if _version_identity(record["rule_ref"]) not in output_rules:
        _add(
            errors,
            "resolution_rule_missing",
            location,
            "resolution rule is not present in output node rule_refs",
        )
    if transition == "not_applicable":
        _authority_for_change(
            reference=record["human_authority_record_ref"],
            expected_types={"not_applicable", "scope_change"},
            edge=edge,
            input_ref=input_ref,
            output_ref=output_ref,
            authority_records=authority_records,
            errors=errors,
            location=location,
            code="not_applicable_authority_missing",
            obligation_id=obligation_id,
        )
    return record


def _validate_pair(
    *,
    edge: Mapping[str, Any],
    input_node: Mapping[str, Any],
    output_node: Mapping[str, Any],
    authority_records: Mapping[str, Mapping[str, Any]],
    resolution_records: Mapping[str, Mapping[str, Any]],
    nodes: Mapping[str, Mapping[str, Any]],
    errors: list[dict[str, str]],
    edge_location: str,
) -> bool:
    input_ref = str(input_node["node_id"])
    output_ref = str(output_node["node_id"])
    preservation = edge["preservation"]
    incomplete = False

    subject_maps = _pair_items(preservation["subjects"], input_ref, output_ref)
    if len(subject_maps) != 1:
        _add(
            errors,
            "subject_map_incomplete",
            edge_location,
            f"expected one subject map for {input_ref}->{output_ref}, found {len(subject_maps)}",
        )
        incomplete = True
    else:
        mapping = subject_maps[0]
        same = input_node["subject"] == output_node["subject"]
        if mapping["status"] == "preserved":
            if not same:
                _add(
                    errors,
                    "subject_substitution_without_authority",
                    edge_location,
                    "subject snapshot changed on a preserved mapping",
                )
            if mapping["authority_record_ref"] is not None:
                _add(errors, "spurious_authority_ref", edge_location, "preserved subject has authority ref")
        else:
            if "subject_change" not in edge["allowed_changes"]:
                _add(errors, "subject_change_not_allowed", edge_location, "edge does not allow subject change")
            record = _authority_for_change(
                reference=mapping["authority_record_ref"],
                expected_types={"subject_change"},
                edge=edge,
                input_ref=input_ref,
                output_ref=output_ref,
                authority_records=authority_records,
                errors=errors,
                location=edge_location,
                code="subject_change_authority_missing",
            )
            if record is not None:
                expected_subjects = {
                    input_node["subject"]["snapshot_ref"],
                    output_node["subject"]["snapshot_ref"],
                }
                if not expected_subjects.issubset(set(record["subject_refs"])):
                    _add(
                        errors,
                        "subject_change_authority_scope_mismatch",
                        edge_location,
                        "authority record does not name old and new subjects",
                    )

    proposition_maps = _pair_items(preservation["propositions"], input_ref, output_ref)
    if len(proposition_maps) != 1:
        _add(
            errors,
            "proposition_map_incomplete",
            edge_location,
            f"expected one proposition map for {input_ref}->{output_ref}, found {len(proposition_maps)}",
        )
        incomplete = True
    else:
        mapping = proposition_maps[0]
        same = input_node["proposition"] == output_node["proposition"]
        if mapping["status"] == "preserved":
            if not same:
                _add(
                    errors,
                    "proposition_substitution_without_authority",
                    edge_location,
                    "proposition changed on a preserved mapping",
                )
        else:
            if "intent_change" not in edge["allowed_changes"]:
                _add(errors, "intent_change_not_allowed", edge_location, "edge does not allow intent change")
            record = _authority_for_change(
                reference=mapping["authority_record_ref"],
                expected_types={"intent_change"},
                edge=edge,
                input_ref=input_ref,
                output_ref=output_ref,
                authority_records=authority_records,
                errors=errors,
                location=edge_location,
                code="intent_change_authority_missing",
            )
            if record is not None:
                expected_ids = {
                    input_node["proposition"]["proposition_id"],
                    output_node["proposition"]["proposition_id"],
                }
                if not expected_ids.issubset(set(record["proposition_ids"])):
                    _add(
                        errors,
                        "intent_change_authority_scope_mismatch",
                        edge_location,
                        "authority record does not name old and new propositions",
                    )

    input_obligations = _obligations(input_node)
    output_obligations = _obligations(output_node)
    obligation_maps = _pair_items(preservation["obligations"], input_ref, output_ref)
    for obligation_id, input_value in input_obligations.items():
        matches = [
            item for item in obligation_maps if item["input_obligation_id"] == obligation_id
        ]
        if len(matches) != 1:
            _add(
                errors,
                "obligation_map_incomplete",
                edge_location,
                f"obligation {obligation_id} has {len(matches)} dispositions for {input_ref}->{output_ref}",
            )
            incomplete = True
            continue
        mapping = matches[0]
        transition = mapping["transition"]
        output_id = mapping["output_obligation_id"]
        if transition == "carried":
            if output_id != obligation_id or output_id not in output_obligations:
                _add(
                    errors,
                    "obligation_dropped_without_authority",
                    edge_location,
                    f"carried obligation is absent or renamed: {obligation_id}",
                )
                continue
            output_value = output_obligations[output_id]
            if output_value["required"] != input_value["required"]:
                _add(
                    errors,
                    "obligation_requiredness_changed",
                    edge_location,
                    f"requiredness changed without scope authority: {obligation_id}",
                )
            if input_value["state"] in {"resolved", "refuted", "not_applicable"}:
                if output_value["state"] != input_value["state"]:
                    _add(
                        errors,
                        "terminal_obligation_state_laundered",
                        edge_location,
                        f"terminal state changed for {obligation_id}",
                    )
            elif output_value["state"] not in {"active", "carried"}:
                _add(
                    errors,
                    "obligation_resolution_without_record",
                    edge_location,
                    f"obligation changed to {output_value['state']} without typed resolution",
                )
            if not set(input_value["basis_evidence_refs"]).issubset(
                set(output_value["basis_evidence_refs"])
            ):
                _add(
                    errors,
                    "obligation_basis_evidence_dropped",
                    edge_location,
                    f"carried obligation lost evidence basis: {obligation_id}",
                )
            if not set(input_value["rule_refs"]).issubset(
                set(output_value["rule_refs"])
            ):
                _add(
                    errors,
                    "obligation_rule_basis_dropped",
                    edge_location,
                    f"carried obligation lost rule basis: {obligation_id}",
                )
        elif transition in {"resolved", "refuted", "not_applicable"}:
            expected_state = transition
            if output_id != obligation_id or output_id not in output_obligations:
                _add(
                    errors,
                    "resolved_obligation_missing",
                    edge_location,
                    f"resolved obligation is absent from output: {obligation_id}",
                )
            elif output_obligations[output_id]["state"] != expected_state:
                _add(
                    errors,
                    "obligation_resolution_state_mismatch",
                    edge_location,
                    f"output state does not match {transition}: {obligation_id}",
                )
            allowed = "not_applicable" if transition == "not_applicable" else "resolution"
            if allowed not in edge["allowed_changes"]:
                _add(
                    errors,
                    "resolution_not_allowed",
                    edge_location,
                    f"edge does not declare allowed change {allowed}",
                )
            _resolution_for_transition(
                reference=mapping["resolution_record_ref"],
                transition=transition,
                obligation_id=obligation_id,
                unresolved_ref=None,
                input_ref=input_ref,
                output_ref=output_ref,
                edge=edge,
                resolution_records=resolution_records,
                authority_records=authority_records,
                nodes=nodes,
                errors=errors,
                location=edge_location,
            )
        else:
            if "scope_change" not in edge["allowed_changes"]:
                _add(errors, "scope_change_not_allowed", edge_location, "edge does not allow scope change")
            _authority_for_change(
                reference=mapping["authority_record_ref"],
                expected_types={"scope_change"},
                edge=edge,
                input_ref=input_ref,
                output_ref=output_ref,
                authority_records=authority_records,
                errors=errors,
                location=edge_location,
                code="obligation_scope_change_authority_missing",
                obligation_id=obligation_id,
            )

    unresolved_maps = _pair_items(preservation["unresolved"], input_ref, output_ref)
    for unresolved_ref in input_node["unresolved_refs"]:
        matches = [item for item in unresolved_maps if item["unresolved_ref"] == unresolved_ref]
        if len(matches) != 1:
            _add(
                errors,
                "unresolved_map_incomplete",
                edge_location,
                f"unresolved item {unresolved_ref} has {len(matches)} dispositions",
            )
            incomplete = True
            continue
        mapping = matches[0]
        if mapping["status"] == "carried":
            if unresolved_ref not in output_node["unresolved_refs"]:
                _add(
                    errors,
                    "unresolved_dropped_without_resolution",
                    edge_location,
                    f"unresolved item disappeared: {unresolved_ref}",
                )
        elif mapping["status"] == "resolved":
            if "resolution" not in edge["allowed_changes"]:
                _add(errors, "resolution_not_allowed", edge_location, "edge does not allow resolution")
            matching_obligation = next(
                (
                    item
                    for item in obligation_maps
                    if item["resolution_record_ref"] == mapping["resolution_record_ref"]
                ),
                None,
            )
            obligation_id = (
                str(matching_obligation["input_obligation_id"])
                if matching_obligation is not None
                else "__unbound__"
            )
            _resolution_for_transition(
                reference=mapping["resolution_record_ref"],
                transition=(
                    str(matching_obligation["transition"])
                    if matching_obligation is not None
                    and matching_obligation["transition"] in {"resolved", "refuted"}
                    else "resolved"
                ),
                obligation_id=obligation_id,
                unresolved_ref=str(unresolved_ref),
                input_ref=input_ref,
                output_ref=output_ref,
                edge=edge,
                resolution_records=resolution_records,
                authority_records=authority_records,
                nodes=nodes,
                errors=errors,
                location=edge_location,
            )
            if unresolved_ref in output_node["unresolved_refs"]:
                _add(
                    errors,
                    "resolved_unresolved_still_active",
                    edge_location,
                    f"resolved item remains active: {unresolved_ref}",
                )
        else:
            if "scope_change" not in edge["allowed_changes"]:
                _add(errors, "scope_change_not_allowed", edge_location, "edge does not allow scope change")
            _authority_for_change(
                reference=mapping["authority_record_ref"],
                expected_types={"scope_change"},
                edge=edge,
                input_ref=input_ref,
                output_ref=output_ref,
                authority_records=authority_records,
                errors=errors,
                location=edge_location,
                code="unresolved_scope_change_authority_missing",
            )

    input_evidence = _evidence(input_node)
    output_evidence = _evidence(output_node)
    evidence_maps = _pair_items(preservation["evidence"], input_ref, output_ref)
    for evidence_id, input_value in input_evidence.items():
        matches = [item for item in evidence_maps if item["evidence_id"] == evidence_id]
        if len(matches) != 1:
            _add(
                errors,
                "evidence_map_incomplete",
                edge_location,
                f"evidence {evidence_id} has {len(matches)} dispositions",
            )
            incomplete = True
            continue
        mapping = matches[0]
        if evidence_id not in output_evidence:
            _add(
                errors,
                "evidence_dropped",
                edge_location,
                f"evidence disappeared without a typed replacement: {evidence_id}",
            )
            continue
        output_value = output_evidence[evidence_id]
        if (
            input_value["digest"] != output_value["digest"]
            or input_value["locator"] != output_value["locator"]
        ):
            _add(
                errors,
                "evidence_identity_substitution",
                edge_location,
                f"evidence locator or digest changed under the same ID: {evidence_id}",
            )
        trust_delta = TRUST_RANK[output_value["trust_level"]] - TRUST_RANK[input_value["trust_level"]]
        freshness_delta = (
            FRESHNESS_RANK[output_value["freshness"]["status"]]
            - FRESHNESS_RANK[input_value["freshness"]["status"]]
        )
        if mapping["status"] == "preserved":
            if trust_delta > 0:
                _add(
                    errors,
                    "evidence_trust_promotion_without_authority",
                    edge_location,
                    f"trust increased on preserved evidence: {evidence_id}",
                )
            elif trust_delta != 0:
                _add(
                    errors,
                    "evidence_trust_changed_without_typed_transition",
                    edge_location,
                    f"trust changed on preserved evidence: {evidence_id}",
                )
            if freshness_delta > 0:
                _add(
                    errors,
                    "evidence_freshness_promotion_without_authority",
                    edge_location,
                    f"freshness increased on preserved evidence: {evidence_id}",
                )
            elif input_value["freshness"] != output_value["freshness"]:
                _add(
                    errors,
                    "evidence_freshness_changed_without_typed_transition",
                    edge_location,
                    f"freshness metadata changed on preserved evidence: {evidence_id}",
                )
        elif mapping["status"] == "trust_promoted":
            if trust_delta <= 0 or input_value["freshness"] != output_value["freshness"]:
                _add(
                    errors,
                    "invalid_trust_promotion",
                    edge_location,
                    f"trust promotion must increase trust only: {evidence_id}",
                )
            if "evidence_trust_override" not in edge["allowed_changes"]:
                _add(errors, "trust_override_not_allowed", edge_location, "edge does not allow trust override")
            _authority_for_change(
                reference=mapping["authority_record_ref"],
                expected_types={"evidence_trust_override"},
                edge=edge,
                input_ref=input_ref,
                output_ref=output_ref,
                authority_records=authority_records,
                errors=errors,
                location=edge_location,
                code="evidence_trust_authority_missing",
            )
        else:
            if freshness_delta <= 0 or trust_delta != 0:
                _add(
                    errors,
                    "invalid_freshness_promotion",
                    edge_location,
                    f"freshness promotion must increase freshness only: {evidence_id}",
                )
            if "evidence_freshness_override" not in edge["allowed_changes"]:
                _add(errors, "freshness_override_not_allowed", edge_location, "edge does not allow freshness override")
            _authority_for_change(
                reference=mapping["authority_record_ref"],
                expected_types={"evidence_freshness_override"},
                edge=edge,
                input_ref=input_ref,
                output_ref=output_ref,
                authority_records=authority_records,
                errors=errors,
                location=edge_location,
                code="evidence_freshness_authority_missing",
            )

    authority_maps = _pair_items(preservation["authority"], input_ref, output_ref)
    input_rights = set(input_node["authority_rights"])
    output_rights = set(output_node["authority_rights"])
    for right in sorted(input_rights):
        matches = [item for item in authority_maps if item["right"] == right]
        if len(matches) != 1:
            _add(
                errors,
                "authority_map_incomplete",
                edge_location,
                f"right {right} has {len(matches)} dispositions",
            )
            incomplete = True
            continue
        mapping = matches[0]
        if mapping["status"] == "preserved" and right not in output_rights:
            _add(errors, "authority_right_dropped", edge_location, f"preserved right is absent: {right}")
        elif mapping["status"] == "revoked" and right in output_rights:
            _add(errors, "authority_revocation_ineffective", edge_location, f"revoked right remains: {right}")
        elif mapping["status"] == "granted":
            _add(errors, "authority_grant_not_new", edge_location, f"grant mapping used for existing right: {right}")
    for right in sorted(output_rights - input_rights):
        matches = [
            item
            for item in authority_maps
            if item["right"] == right and item["status"] == "granted"
        ]
        if len(matches) != 1:
            _add(
                errors,
                "authority_escalation_unmapped",
                edge_location,
                f"new right lacks exactly one grant mapping: {right}",
            )
            incomplete = True
            continue
        mapping = matches[0]
        if "authority_grant" not in edge["allowed_changes"]:
            _add(errors, "authority_grant_not_allowed", edge_location, "edge does not allow authority grant")
        _authority_for_change(
            reference=mapping["authority_record_ref"],
            expected_types={"authority_grant"},
            edge=edge,
            input_ref=input_ref,
            output_ref=output_ref,
            authority_records=authority_records,
            errors=errors,
            location=edge_location,
            code="authority_grant_record_missing",
            right=right,
        )

    return incomplete


def _reachable(start: str, adjacency: Mapping[str, set[str]]) -> set[str]:
    seen: set[str] = set()
    pending = [start]
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        seen.add(current)
        pending.extend(adjacency.get(current, set()) - seen)
    return seen


def _validate_completion(
    *,
    node: Mapping[str, Any],
    nodes: Mapping[str, Mapping[str, Any]],
    adjacency: Mapping[str, set[str]],
    incoming_edges: Mapping[str, list[Mapping[str, Any]]],
    authority_records: Mapping[str, Mapping[str, Any]],
    errors: list[dict[str, str]],
    location: str,
) -> None:
    completion = node["completion"]
    verification_refs = set(completion["verification_node_refs"])
    for verification_ref in sorted(verification_refs):
        if (
            verification_ref not in nodes
            or nodes[verification_ref]["stage"] != "verification"
            or node["node_id"] not in _reachable(verification_ref, adjacency)
        ):
            _add(
                errors,
                "completion_verification_invalid",
                location,
                f"verification node is missing, mistyped, or not connected: {verification_ref}",
            )

    completion_obligations = _obligations(node)
    active_required = {
        obligation_id
        for obligation_id, value in completion_obligations.items()
        if value["required"] and value["state"] != "not_applicable"
    }
    traces = completion["obligation_trace"]
    trace_ids = [str(item["obligation_id"]) for item in traces]
    for duplicate in sorted(_duplicates(trace_ids)):
        _add(errors, "duplicate_completion_obligation_trace", location, duplicate)
    if set(trace_ids) != active_required:
        _add(
            errors,
            "completion_obligation_coverage_incomplete",
            location,
            f"completion trace {sorted(set(trace_ids))} does not equal active required obligations {sorted(active_required)}",
        )
    for trace in traces:
        obligation_id = str(trace["obligation_id"])
        source_ref = str(trace["source_node_ref"])
        verification_ref = str(trace["verification_node_ref"])
        if obligation_id in completion_obligations and trace["state"] != completion_obligations[obligation_id]["state"]:
            _add(
                errors,
                "completion_obligation_state_mismatch",
                location,
                f"trace state differs from completion node: {obligation_id}",
            )
        if source_ref not in nodes or obligation_id not in _obligations(nodes[source_ref]):
            _add(
                errors,
                "completion_obligation_source_missing",
                location,
                f"source node does not carry obligation: {obligation_id}",
            )
        if (
            verification_ref not in verification_refs
            or verification_ref not in nodes
            or obligation_id not in _obligations(nodes[verification_ref])
        ):
            _add(
                errors,
                "completion_obligation_verification_missing",
                location,
                f"verification node does not carry obligation: {obligation_id}",
            )

    residuals = completion["residual_unproven_scope"]
    residual_ids = [str(item["unresolved_ref"]) for item in residuals]
    if set(residual_ids) != set(node["unresolved_refs"]):
        _add(
            errors,
            "completion_residual_scope_mismatch",
            location,
            "residual trace must exactly cover completion unresolved refs",
        )
    for residual in residuals:
        source_ref = str(residual["source_node_ref"])
        unresolved_ref = str(residual["unresolved_ref"])
        if source_ref not in nodes or unresolved_ref not in nodes[source_ref]["unresolved_refs"]:
            _add(
                errors,
                "completion_residual_source_missing",
                location,
                f"residual source does not carry unresolved item: {unresolved_ref}",
            )

    acceptance = completion["human_acceptance"]
    authority_ref = acceptance["authority_record_ref"]
    if acceptance["status"] == "pending":
        if authority_ref is not None:
            _add(
                errors,
                "pending_acceptance_has_authority_record",
                location,
                "pending acceptance must not imply a completed human decision",
            )
        return
    if not authority_ref or authority_ref not in authority_records:
        _add(
            errors,
            "final_acceptance_authority_missing",
            location,
            "non-pending human acceptance requires a located human authority record",
        )
        return
    record = authority_records[authority_ref]
    expected_decision = {
        "accepted": "accept",
        "request_revision": "request_revision",
        "deferred": "defer",
    }[acceptance["status"]]
    if (
        record["record_type"] != "final_acceptance"
        or record["decision"] != expected_decision
        or node["node_id"] not in record["node_refs"]
    ):
        _add(
            errors,
            "final_acceptance_authority_mismatch",
            location,
            "human decision type, disposition, or completion scope does not match",
        )
    cited = any(
        authority_ref in edge["decision_refs"]
        and "final_acceptance" in edge["allowed_changes"]
        for edge in incoming_edges.get(str(node["node_id"]), [])
    )
    if not cited:
        _add(
            errors,
            "final_acceptance_not_cited_by_completion_edge",
            location,
            "completion edge does not cite the final human authority record",
        )


def lifecycle_trace_errors(trace: Mapping[str, Any]) -> tuple[dict[str, str], ...]:
    """Return deterministic validation errors without mutating the trace."""

    errors: list[dict[str, str]] = []
    schema_failures = sorted(
        _schema_validator().iter_errors(trace), key=lambda item: list(item.path)
    )
    for failure in schema_failures:
        _add(
            errors,
            "schema_validation_failed",
            _schema_location(failure.path),
            failure.message,
        )
    if schema_failures:
        return tuple(errors)

    if trace["graph_digest"] != digest_value(_trace_material(trace)):
        _add(errors, "graph_digest_mismatch", "$.graph_digest", "graph digest does not replay")
    expected_profile_digest = digest_value(
        {
            "ref_id": trace["composition_profile"]["ref_id"],
            "version": trace["composition_profile"]["version"],
        }
    )
    if trace["composition_profile"]["digest"] != expected_profile_digest:
        _add(
            errors,
            "composition_profile_digest_mismatch",
            "$.composition_profile.digest",
            "composition profile digest does not replay",
        )

    node_list = trace["nodes"]
    node_ids = [str(node["node_id"]) for node in node_list]
    for duplicate in sorted(_duplicates(node_ids)):
        _add(errors, "duplicate_node_id", "$.nodes", duplicate)
    nodes = {str(node["node_id"]): node for node in node_list}
    for index, node in enumerate(node_list):
        location = f"$.nodes.{index}"
        material = _node_material(node)
        node_hash = canonical_sha256(material)
        if node["node_digest"] != {"algorithm": "sha256", "value": node_hash}:
            _add(errors, "node_digest_mismatch", f"{location}.node_digest", node["node_id"])
        expected_id = f"lifecycle-node.{node['stage']}.{node_hash[:24]}"
        if node["node_id"] != expected_id:
            _add(errors, "node_id_mismatch", f"{location}.node_id", f"expected {expected_id}")
        for field, identity_field in (
            ("obligation_states", "obligation_id"),
            ("evidence_refs", "evidence_id"),
        ):
            identities = [str(item[identity_field]) for item in node[field]]
            for duplicate in sorted(_duplicates(identities)):
                _add(errors, f"duplicate_{identity_field}", f"{location}.{field}", duplicate)
        for field in ("profile_refs", "rule_refs"):
            identities = ["@".join(_version_identity(item)) for item in node[field]]
            for duplicate in sorted(_duplicates(identities)):
                _add(errors, f"duplicate_{field}", f"{location}.{field}", duplicate)

    observed_stages = {str(node["stage"]) for node in node_list}
    for stage in sorted(set(STAGES) - observed_stages):
        _add(errors, "lifecycle_stage_missing", "$.nodes", stage)

    authority_list = trace["authority_records"]
    authority_ids = [str(item["record_id"]) for item in authority_list]
    for duplicate in sorted(_duplicates(authority_ids)):
        _add(errors, "duplicate_authority_record", "$.authority_records", duplicate)
    authority_records = {str(item["record_id"]): item for item in authority_list}

    resolution_list = trace["resolution_records"]
    resolution_ids = [str(item["resolution_id"]) for item in resolution_list]
    for duplicate in sorted(_duplicates(resolution_ids)):
        _add(errors, "duplicate_resolution_record", "$.resolution_records", duplicate)
    resolution_records = {str(item["resolution_id"]): item for item in resolution_list}

    all_evidence_ids = {
        str(item["evidence_id"])
        for node in node_list
        for item in node["evidence_refs"]
    }
    for index, record in enumerate(authority_list):
        location = f"$.authority_records.{index}"
        for node_ref in record["node_refs"]:
            if node_ref not in nodes:
                _add(errors, "authority_record_dangling_node", location, node_ref)
        for evidence_ref in record["evidence_refs"]:
            if evidence_ref not in all_evidence_ids:
                _add(errors, "authority_record_dangling_evidence", location, evidence_ref)
        if record["record_type"] == "final_acceptance":
            if record["decision"] not in {"accept", "request_revision", "defer"}:
                _add(errors, "final_acceptance_decision_invalid", location, record["decision"])
        elif record["decision"] != "authorize_change":
            _add(errors, "change_authority_decision_invalid", location, record["decision"])

    for index, record in enumerate(resolution_list):
        location = f"$.resolution_records.{index}"
        if record["input_node_ref"] not in nodes or record["output_node_ref"] not in nodes:
            _add(errors, "resolution_dangling_endpoint", location, record["resolution_id"])
            continue
        input_node = nodes[record["input_node_ref"]]
        if record["obligation_id"] not in _obligations(input_node):
            _add(errors, "resolution_obligation_missing_at_input", location, record["obligation_id"])
        for unresolved_ref in record["unresolved_refs"]:
            if unresolved_ref not in input_node["unresolved_refs"]:
                _add(errors, "resolution_unresolved_missing_at_input", location, unresolved_ref)

    edge_list = trace["edges"]
    edge_ids = [str(edge["edge_id"]) for edge in edge_list]
    for duplicate in sorted(_duplicates(edge_ids)):
        _add(errors, "duplicate_edge_id", "$.edges", duplicate)

    adjacency: dict[str, set[str]] = {node_id: set() for node_id in nodes}
    reverse: dict[str, set[str]] = {node_id: set() for node_id in nodes}
    incoming_edges: dict[str, list[Mapping[str, Any]]] = {node_id: [] for node_id in nodes}
    outgoing_edges: dict[str, list[Mapping[str, Any]]] = {node_id: [] for node_id in nodes}

    for index, edge in enumerate(edge_list):
        location = f"$.edges.{index}"
        material = _edge_material(edge)
        edge_hash = canonical_sha256(material)
        if edge["edge_digest"] != {"algorithm": "sha256", "value": edge_hash}:
            _add(errors, "edge_digest_mismatch", f"{location}.edge_digest", edge["edge_id"])
        expected_id = f"lifecycle-edge.{edge['edge_kind']}.{edge_hash[:24]}"
        if edge["edge_id"] != expected_id:
            _add(errors, "edge_id_mismatch", f"{location}.edge_id", f"expected {expected_id}")
        rule_material = {
            "rule_id": edge["composition_rule"]["rule_id"],
            "version": edge["composition_rule"]["version"],
        }
        if edge["composition_rule"]["digest"] != digest_value(rule_material):
            _add(
                errors,
                "composition_rule_digest_mismatch",
                f"{location}.composition_rule.digest",
                edge["composition_rule"]["rule_id"],
            )
        dangling = [
            node_ref
            for node_ref in (*edge["input_node_refs"], *edge["output_node_refs"])
            if node_ref not in nodes
        ]
        for node_ref in dangling:
            _add(errors, "edge_dangling_endpoint", location, node_ref)
        for decision_ref in edge["decision_refs"]:
            if decision_ref not in authority_records:
                _add(errors, "edge_dangling_decision_ref", location, decision_ref)
        for evidence_ref in edge["evidence_refs"]:
            if evidence_ref not in all_evidence_ids:
                _add(errors, "edge_dangling_evidence_ref", location, evidence_ref)
        if dangling:
            continue

        if edge["edge_kind"] == "branches" and (
            len(edge["input_node_refs"]) != 1 or len(edge["output_node_refs"]) < 2
        ):
            _add(errors, "branch_cardinality_invalid", location, "branches requires 1 input and at least 2 outputs")
        if edge["edge_kind"] == "merges" and (
            len(edge["input_node_refs"]) < 2 or len(edge["output_node_refs"]) != 1
        ):
            _add(errors, "merge_cardinality_invalid", location, "merges requires at least 2 inputs and 1 output")
        if edge["edge_kind"] == "verifies":
            if any(nodes[item]["stage"] != "verification" for item in edge["output_node_refs"]):
                _add(errors, "verification_edge_target_invalid", location, "verifies must target verification stage")
        if edge["edge_kind"] == "completes":
            if any(nodes[item]["stage"] != "completion_claim" for item in edge["output_node_refs"]):
                _add(errors, "completion_edge_target_invalid", location, "completes must target completion_claim")
            if not any(nodes[item]["stage"] == "verification" for item in edge["input_node_refs"]):
                _add(errors, "completion_without_verification_input", location, "completes requires verification input")

        same_stage_allowed = {"refines", "supersedes", "branches", "merges", "cancels"}
        for input_ref in edge["input_node_refs"]:
            for output_ref in edge["output_node_refs"]:
                input_rank = STAGE_RANK[nodes[input_ref]["stage"]]
                output_rank = STAGE_RANK[nodes[output_ref]["stage"]]
                if output_rank < input_rank:
                    _add(
                        errors,
                        "lifecycle_stage_regression",
                        location,
                        f"{nodes[input_ref]['stage']}->{nodes[output_ref]['stage']}",
                    )
                if output_rank == input_rank and edge["edge_kind"] not in same_stage_allowed:
                    _add(
                        errors,
                        "same_stage_edge_kind_invalid",
                        location,
                        "same-stage composition requires an explicit refinement/supersession/branch/merge/cancel kind",
                    )
                adjacency[input_ref].add(output_ref)
                reverse[output_ref].add(input_ref)
                outgoing_edges[input_ref].append(edge)
                incoming_edges[output_ref].append(edge)
                incomplete = _validate_pair(
                    edge=edge,
                    input_node=nodes[input_ref],
                    output_node=nodes[output_ref],
                    authority_records=authority_records,
                    resolution_records=resolution_records,
                    nodes=nodes,
                    errors=errors,
                    edge_location=location,
                )
                if incomplete and edge["edge_kind"] == "merges":
                    _add(
                        errors,
                        "incomplete_merge_preservation",
                        location,
                        f"merge input {input_ref} is not completely composed into {output_ref}",
                    )

        allowed_endpoint_pairs = {
            (input_ref, output_ref)
            for input_ref in edge["input_node_refs"]
            for output_ref in edge["output_node_refs"]
        }
        for field, mappings in edge["preservation"].items():
            for mapping in mappings:
                pair = (mapping["input_node_ref"], mapping["output_node_ref"])
                if pair not in allowed_endpoint_pairs:
                    _add(
                        errors,
                        "preservation_map_outside_edge",
                        f"{location}.preservation.{field}",
                        f"mapping pair is not an edge endpoint pair: {pair}",
                    )

    # Kahn cycle detection.
    indegree = {node_id: len(reverse[node_id]) for node_id in nodes}
    pending = [node_id for node_id, count in indegree.items() if count == 0]
    visited = 0
    while pending:
        current = pending.pop()
        visited += 1
        for target in adjacency[current]:
            indegree[target] -= 1
            if indegree[target] == 0:
                pending.append(target)
    if visited != len(nodes):
        _add(errors, "lifecycle_cycle_detected", "$.edges", "composition graph must be acyclic")

    request_nodes = [node_id for node_id, node in nodes.items() if node["stage"] == "request"]
    completion_nodes = [
        node_id for node_id, node in nodes.items() if node["stage"] == "completion_claim"
    ]
    reachable_from_requests: set[str] = set()
    for node_id in request_nodes:
        reachable_from_requests |= _reachable(node_id, adjacency)
    can_reach_completion: set[str] = set()
    for node_id in completion_nodes:
        can_reach_completion |= _reachable(node_id, reverse)
    for node_id, node in nodes.items():
        if node_id not in reachable_from_requests:
            _add(errors, "node_not_composed_from_request", "$.nodes", node_id)
        if node_id not in can_reach_completion:
            _add(errors, "node_not_composed_to_completion", "$.nodes", node_id)
        if node["stage"] != "request" and not incoming_edges[node_id]:
            _add(errors, "non_request_node_without_input", "$.nodes", node_id)
        if node["stage"] != "completion_claim" and not outgoing_edges[node_id]:
            _add(errors, "non_completion_node_without_output", "$.nodes", node_id)

    merge_inputs = {
        node_ref
        for edge in edge_list
        if edge["edge_kind"] == "merges"
        for node_ref in edge["input_node_refs"]
    }
    cancel_inputs = {
        node_ref
        for edge in edge_list
        if edge["edge_kind"] == "cancels"
        for node_ref in edge["input_node_refs"]
    }
    for index, edge in enumerate(edge_list):
        if edge["edge_kind"] != "branches":
            continue
        for output_ref in edge["output_node_refs"]:
            reachable = _reachable(output_ref, adjacency)
            if not reachable & (merge_inputs | cancel_inputs):
                _add(
                    errors,
                    "branch_output_unclosed",
                    f"$.edges.{index}",
                    f"branch output reaches neither merge nor cancellation: {output_ref}",
                )

    for index, node in enumerate(node_list):
        if node["stage"] == "completion_claim":
            _validate_completion(
                node=node,
                nodes=nodes,
                adjacency=adjacency,
                incoming_edges=incoming_edges,
                authority_records=authority_records,
                errors=errors,
                location=f"$.nodes.{index}.completion",
            )

    return tuple(errors)


def validate_lifecycle_trace(trace: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and return a deep copy, or raise with typed error codes."""

    errors = lifecycle_trace_errors(trace)
    if errors:
        raise LifecycleTraceValidationError(errors)
    return copy.deepcopy(dict(trace))
