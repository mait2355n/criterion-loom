"""Governed engineering-rule sidecar contracts.

This module deliberately does not alter or authorize the legacy v0 rule pack
or the existing audit engine.  It builds and replays a closed v1 governance
bundle around six logical records: immutable rule basis, review, external
human decision, implementation binding, pack manifest, and runtime
resolution.  The H1 gate is a derived view, never a decision maker.

Digest closure proves only consistency of supplied records.  It does not
prove engineering correctness, source validity, reviewer competence, human
identity, external evidence existence, implementation behaviour, or final
human acceptance.
"""

from __future__ import annotations

import copy
from functools import lru_cache
import hashlib
import json
from typing import Any, Callable, Mapping, Sequence

from jsonschema import Draft202012Validator, FormatChecker

from .schema_access import schema_path


BUNDLE_VERSION = "engineering-rule-governance-bundle/v1"
BASIS_VERSION = "engineering-rule-basis/v1"
REVIEW_VERSION = "engineering-rule-review/v1"
DECISION_VERSION = "engineering-rule-human-decision/v1"
IMPLEMENTATION_VERSION = "engineering-rule-implementation-binding/v1"
PACK_VERSION = "engineering-rule-pack-manifest/v1"
RESOLUTION_VERSION = "engineering-rule-runtime-resolution/v1"
RUNTIME_RECEIPT_VERSION = "engineering-rule-runtime-receipt/v1"
GATE_VERSION = "engineering-rule-governance-gate-view/v1"
NORMALIZATION_PROFILE = "semantic-guard-canonical-json/v1"

_SCHEMA_PATH = schema_path("engineering-rule-governance-v1.schema.json")

_LIMITATIONS = (
    "Schema and digest replay establish supplied-record closure only, not engineering correctness.",
    "A human marker, verified flag, or evidence locator is not identity proof; every completed decision also requires a successful externally injected trusted verifier.",
    "A human reviewer marker, qualification locator, or evidence locator cannot become adoption material without a separate externally injected trusted reviewer verifier.",
    "Runtime resolution does not execute a rule, validate an obligation assessment, or grant authority outside this bundle.",
    "Explicit runtime artifact and implementation digests are supplied observations, not proof that the corresponding bytes were independently observed.",
    "Sealed runtime receipts are portable records, but their external authenticity is not portable by digest alone; an injected verifier result and content-addressed verifier_ref remain supplied verification claims.",
    "Injected verifier callbacks and their content-addressed references are supplied claims until a control-plane trust registry or signature root is integrated; this candidate implementation therefore grants no formal runtime authority.",
    "Rule artifact bytes are bound into the adoption basis because no trusted versioned semantic normalizer currently proves formatting-only equivalence.",
    "Legacy v0 records and similarly named identifiers cannot receive formal authority through this contract.",
)

_AUTHORITY_FIELDS = (
    "finding_authority",
    "routing_authority",
    "nonconformance_authority",
    "satisfaction_authority",
    "not_applicable_authority",
    "hold_apply_authority",
    "hold_release_authority",
    "final_verdict_authority",
)

CANDIDATE_AUTHORITY: dict[str, str] = {
    "finding_authority": "candidate_only",
    "routing_authority": "may_escalate_unresolved",
    "nonconformance_authority": "prohibited",
    "satisfaction_authority": "prohibited",
    "not_applicable_authority": "prohibited",
    "hold_apply_authority": "prohibited",
    "hold_release_authority": "prohibited",
    "final_verdict_authority": "prohibited",
}


class EngineeringRuleGovernanceError(ValueError):
    """Raised when the v1 governance contract fails closed."""


DecisionVerifier = Callable[[Mapping[str, Any]], bool]
ReviewerVerifier = Callable[[Mapping[str, Any]], bool]
RuntimeVerifier = Callable[[Mapping[str, Any]], bool]


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha256_digest(value: Any) -> dict[str, str]:
    return {
        "algorithm": "sha256",
        "value": hashlib.sha256(_canonical(value)).hexdigest(),
    }


def sha256_bytes(value: bytes) -> dict[str, str]:
    if not isinstance(value, bytes):
        raise TypeError("artifact content must be bytes")
    return {"algorithm": "sha256", "value": hashlib.sha256(value).hexdigest()}


def _without(value: Mapping[str, Any], *fields: str) -> dict[str, Any]:
    material = copy.deepcopy(dict(value))
    for field in fields:
        material.pop(field, None)
    return material


@lru_cache(maxsize=1)
def _root_schema() -> dict[str, Any]:
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def _subvalidator(definition: str) -> Draft202012Validator:
    root = _root_schema()
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$defs": root["$defs"],
        "$ref": f"#/$defs/{definition}",
    }
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


@lru_cache(maxsize=1)
def _bundle_validator() -> Draft202012Validator:
    schema = _root_schema()
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _validate_schema(
    value: Mapping[str, Any],
    validator: Draft202012Validator,
    label: str,
) -> None:
    failures = sorted(
        validator.iter_errors(value),
        key=lambda failure: tuple(str(item) for item in failure.absolute_path),
    )
    if failures:
        failure = failures[0]
        location = "/".join(str(item) for item in failure.absolute_path) or "/"
        raise EngineeringRuleGovernanceError(
            f"{label} schema violation at {location}: {failure.message}"
        )


def _verifier_ref(
    verifier: Callable[[Mapping[str, Any]], bool] | None,
) -> dict[str, Any] | None:
    """Return a closed content-addressed verifier identity or fail closed.

    A callable, function name, or process-local object identity is not a trust
    anchor.  The injected verifier must expose an immutable record reference so
    the exact trust provider used by resolution is bound into the result.
    """

    if verifier is None:
        return None
    verifier_ref = getattr(verifier, "verifier_ref", None)
    if not isinstance(verifier_ref, Mapping):
        return None
    copied = copy.deepcopy(dict(verifier_ref))
    try:
        _validate_schema(copied, _subvalidator("record_ref"), "trusted verifier")
    except EngineeringRuleGovernanceError:
        return None
    return copied


def _unique(
    values: Sequence[Mapping[str, Any]], fields: tuple[str, ...], label: str
) -> None:
    observed = [tuple(str(item[field]) for field in fields) for item in values]
    duplicates = sorted({item for item in observed if observed.count(item) > 1})
    if duplicates:
        raise EngineeringRuleGovernanceError(f"duplicate {label}: {duplicates!r}")


def _authority(value: Mapping[str, Any]) -> dict[str, str]:
    result = {field: str(value[field]) for field in _AUTHORITY_FIELDS}
    _validate_schema(result, _subvalidator("authority"), "authority")
    return result


def _candidate_authority() -> dict[str, str]:
    return copy.deepcopy(CANDIDATE_AUTHORITY)


def _authority_within(granted: Mapping[str, Any], requested: Mapping[str, Any]) -> bool:
    if (
        granted["finding_authority"] == "formal_finding"
        and requested["finding_authority"] != "formal_finding"
    ):
        return False
    if (
        granted["routing_authority"] == "may_escalate_unresolved"
        and requested["routing_authority"] != "may_escalate_unresolved"
    ):
        return False
    return all(
        granted[field] != "permitted" or requested[field] == "permitted"
        for field in _AUTHORITY_FIELDS[2:]
    )


def _rule_key(value: Mapping[str, Any]) -> tuple[str, str]:
    return str(value["rule_id"]), str(value["rule_version"])


def _rule_ref(basis: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "rule_id": basis["rule_id"],
        "rule_version": basis["rule_version"],
        "basis_digest": copy.deepcopy(basis["basis_digest"]),
    }


def _basis_material(basis: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": basis["schema_version"],
        "rule_id": basis["rule_id"],
        "rule_version": basis["rule_version"],
        "normalization_profile": basis["normalization_profile"],
        "artifact_digest": copy.deepcopy(basis["artifact_digest"]),
        "content_digest": copy.deepcopy(basis["content_digest"]),
        "source_bindings": copy.deepcopy(basis["source_bindings"]),
        "applicability": copy.deepcopy(basis["applicability"]),
        "exceptions": copy.deepcopy(basis["exceptions"]),
        "requested_authority": copy.deepcopy(basis["requested_authority"]),
    }


def build_rule_basis(
    *,
    rule_id: str,
    rule_version: str,
    artifact_locator: str,
    artifact_content: bytes,
    engineering_proposition: str,
    interpretation: str,
    required_evidence: Sequence[str],
    limitations: Sequence[str],
    source_bindings: Sequence[Mapping[str, Any]],
    applicability_scope_ids: Sequence[str],
    applicability_conditions: Sequence[str],
    exceptions: Sequence[Mapping[str, Any]],
    requested_authority: Mapping[str, Any],
) -> dict[str, Any]:
    semantic_content = {
        "engineering_proposition": engineering_proposition,
        "interpretation": interpretation,
        "required_evidence": sorted(set(required_evidence)),
        "limitations": sorted(set(limitations)),
    }
    basis: dict[str, Any] = {
        "schema_version": BASIS_VERSION,
        "rule_id": rule_id,
        "rule_version": rule_version,
        "normalization_profile": NORMALIZATION_PROFILE,
        "artifact_locator": artifact_locator,
        "artifact_digest": sha256_bytes(artifact_content),
        "semantic_content": semantic_content,
        "content_digest": sha256_digest(semantic_content),
        "source_bindings": sorted(
            (copy.deepcopy(dict(item)) for item in source_bindings),
            key=lambda item: (
                item["source_id"],
                item["source_version"],
                item["section_locator"],
            ),
        ),
        "applicability": {
            "scope_ids": sorted(set(applicability_scope_ids)),
            "conditions": sorted(set(applicability_conditions)),
        },
        "exceptions": sorted(
            (copy.deepcopy(dict(item)) for item in exceptions),
            key=lambda item: item["exception_id"],
        ),
        "requested_authority": _authority(requested_authority),
    }
    basis["basis_digest"] = sha256_digest(_basis_material(basis))
    basis["record_digest"] = sha256_digest(basis)
    validate_rule_basis(basis)
    return basis


def validate_rule_basis(basis: Mapping[str, Any]) -> None:
    _validate_schema(basis, _subvalidator("rule_basis"), "rule basis")
    _unique(
        list(basis["source_bindings"]),
        ("source_id", "source_version", "section_locator"),
        "source binding",
    )
    _unique(list(basis["exceptions"]), ("exception_id",), "exception")
    if basis["content_digest"] != sha256_digest(basis["semantic_content"]):
        raise EngineeringRuleGovernanceError("rule content digest mismatch")
    if basis["basis_digest"] != sha256_digest(_basis_material(basis)):
        raise EngineeringRuleGovernanceError("rule basis digest mismatch")
    if basis["record_digest"] != sha256_digest(_without(basis, "record_digest")):
        raise EngineeringRuleGovernanceError("rule basis record digest mismatch")


def build_candidate_review(
    *,
    review_id: str,
    basis: Mapping[str, Any],
    reviewer_ref: str,
    reviewer_kind: str,
    review_independence: str,
    reviewer_qualification_refs: Sequence[str],
    audit_assessment: str,
    finding_refs: Sequence[str],
    evidence_status: str,
    non_binding_recommendation: str,
    recommendation_rationale: str,
    review_evidence_refs: Sequence[str],
) -> dict[str, Any]:
    """Build a non-authoritative audit, AI, or tool review candidate."""

    validate_rule_basis(basis)
    if reviewer_kind not in {"ai", "tool"}:
        raise EngineeringRuleGovernanceError(
            "audit-side review builder cannot construct a human review"
        )
    review: dict[str, Any] = {
        "schema_version": REVIEW_VERSION,
        "review_id": review_id,
        "rule_ref": _rule_ref(basis),
        "review_source": "audit_generated_candidate",
        "reviewer_ref": reviewer_ref,
        "reviewer_kind": reviewer_kind,
        "review_independence": review_independence,
        "review_authority": "candidate_only",
        "reviewer_qualification_refs": sorted(set(reviewer_qualification_refs)),
        "audit_assessment": audit_assessment,
        "finding_refs": sorted(set(finding_refs)),
        "evidence_status": evidence_status,
        "non_binding_recommendation": non_binding_recommendation,
        "recommendation_rationale": recommendation_rationale,
        "review_evidence_refs": sorted(set(review_evidence_refs)),
    }
    review["review_digest"] = sha256_digest(review)
    validate_review(review)
    return review


def bind_external_human_review(
    review: Mapping[str, Any],
    *,
    basis: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate and exactly bind an externally supplied human review."""

    validate_rule_basis(basis)
    bound = copy.deepcopy(dict(review))
    validate_review(bound)
    if bound["review_source"] != "external_human_record":
        raise EngineeringRuleGovernanceError(
            "external human review binding requires an external human record"
        )
    if bound["rule_ref"] != _rule_ref(basis):
        raise EngineeringRuleGovernanceError(
            "external human review target binding mismatch"
        )
    return bound


def validate_review(review: Mapping[str, Any]) -> None:
    _validate_schema(review, _subvalidator("review"), "engineering rule review")
    source = review["review_source"]
    if review["reviewer_kind"] == "ai" and review["review_independence"] in {
        "separate_runtime_review",
        "independent_human_review",
    }:
        raise EngineeringRuleGovernanceError(
            "AI review cannot be represented as independent review"
        )
    if source == "audit_generated_candidate" and review["reviewer_kind"] == "human":
        raise EngineeringRuleGovernanceError(
            "audit-generated review cannot claim a human reviewer"
        )
    if source == "external_human_record" and review["reviewer_kind"] != "human":
        raise EngineeringRuleGovernanceError(
            "external human review requires a human reviewer"
        )
    eligible = (
        source == "external_human_record"
        and review["reviewer_kind"] == "human"
        and review["review_independence"] == "independent_human_review"
        and bool(review["reviewer_qualification_refs"])
        and bool(review["review_evidence_refs"])
    )
    expected_authority = "adoption_material" if eligible else "candidate_only"
    if review["review_authority"] != expected_authority:
        raise EngineeringRuleGovernanceError(
            "review authority exceeds review identity or independence"
        )
    if (
        review["audit_assessment"] in {"adoption_not_ready", "conflicting"}
        and not review["finding_refs"]
    ):
        raise EngineeringRuleGovernanceError("non-ready review requires finding_refs")
    if review["review_digest"] != sha256_digest(_without(review, "review_digest")):
        raise EngineeringRuleGovernanceError("review digest mismatch")


def build_implementation_binding(
    *,
    binding_id: str,
    basis: Mapping[str, Any],
    implementation_id: str,
    implementation_version: str,
    entry_point: str,
    artifacts: Sequence[Mapping[str, Any]],
    implementation_status: str,
    verification_evidence_refs: Sequence[str],
) -> dict[str, Any]:
    validate_rule_basis(basis)
    normalized_artifacts = sorted(
        (copy.deepcopy(dict(item)) for item in artifacts),
        key=lambda item: item["locator"],
    )
    material = {
        "schema_version": IMPLEMENTATION_VERSION,
        "binding_id": binding_id,
        "rule_ref": _rule_ref(basis),
        "implementation_id": implementation_id,
        "implementation_version": implementation_version,
        "entry_point": entry_point,
        "artifacts": normalized_artifacts,
    }
    binding: dict[str, Any] = {
        **material,
        "implementation_digest": sha256_digest(material),
        "implementation_status": implementation_status,
        "verification_evidence_refs": sorted(set(verification_evidence_refs)),
    }
    binding["binding_digest"] = sha256_digest(binding)
    validate_implementation_binding(binding)
    return binding


def validate_implementation_binding(binding: Mapping[str, Any]) -> None:
    _validate_schema(
        binding,
        _subvalidator("implementation_binding"),
        "implementation binding",
    )
    _unique(list(binding["artifacts"]), ("locator",), "implementation artifact")
    material = {
        key: copy.deepcopy(binding[key])
        for key in (
            "schema_version",
            "binding_id",
            "rule_ref",
            "implementation_id",
            "implementation_version",
            "entry_point",
            "artifacts",
        )
    }
    if binding["implementation_digest"] != sha256_digest(material):
        raise EngineeringRuleGovernanceError("implementation digest mismatch")
    if (
        binding["implementation_status"] == "verified"
        and not binding["verification_evidence_refs"]
    ):
        raise EngineeringRuleGovernanceError(
            "verified implementation requires verification evidence"
        )
    if binding["binding_digest"] != sha256_digest(_without(binding, "binding_digest")):
        raise EngineeringRuleGovernanceError("implementation binding digest mismatch")


def build_pack_manifest(
    *,
    pack_id: str,
    pack_version: str,
    subject_scope_ids: Sequence[str],
    required_bases: Sequence[Mapping[str, Any]],
    optional_bases: Sequence[Mapping[str, Any]] = (),
    excluded_bases: Sequence[tuple[Mapping[str, Any], str]] = (),
) -> dict[str, Any]:
    for basis in (
        tuple(required_bases)
        + tuple(optional_bases)
        + tuple(item[0] for item in excluded_bases)
    ):
        validate_rule_basis(basis)
    manifest: dict[str, Any] = {
        "schema_version": PACK_VERSION,
        "pack_id": pack_id,
        "pack_version": pack_version,
        "subject_scope_ids": sorted(set(subject_scope_ids)),
        "required_rule_denominator": sorted(
            (_rule_ref(item) for item in required_bases), key=_rule_key
        ),
        "optional_rule_denominator": sorted(
            (_rule_ref(item) for item in optional_bases), key=_rule_key
        ),
        "excluded_rules": sorted(
            (
                {"rule_ref": _rule_ref(basis), "reason": reason}
                for basis, reason in excluded_bases
            ),
            key=lambda item: _rule_key(item["rule_ref"]),
        ),
        "aggregation_conditions": [
            "all_required_obligations_satisfied",
            "all_required_rules_grant_final_verdict",
            "blocking_unresolved_count_zero",
            "resolved_required_rules_equal_denominator",
        ],
    }
    manifest["manifest_digest"] = sha256_digest(manifest)
    validate_pack_manifest(manifest)
    return manifest


def validate_pack_manifest(manifest: Mapping[str, Any]) -> None:
    _validate_schema(manifest, _subvalidator("pack_manifest"), "pack manifest")
    partitions = [
        list(manifest["required_rule_denominator"]),
        list(manifest["optional_rule_denominator"]),
        [item["rule_ref"] for item in manifest["excluded_rules"]],
    ]
    for label, values in zip(("required", "optional", "excluded"), partitions):
        _unique(values, ("rule_id", "rule_version"), f"{label} pack rule")
    identities = [{_rule_key(item) for item in values} for values in partitions]
    if (
        identities[0] & identities[1]
        or identities[0] & identities[2]
        or identities[1] & identities[2]
    ):
        raise EngineeringRuleGovernanceError("pack rule partitions overlap")
    if manifest["manifest_digest"] != sha256_digest(
        _without(manifest, "manifest_digest")
    ):
        raise EngineeringRuleGovernanceError("pack manifest digest mismatch")


def build_pending_human_decision(
    *,
    decision_id: str,
    target_kind: str,
    target_id: str,
    target_version: str,
    target_digest: Mapping[str, Any],
    pack_manifest: Mapping[str, Any],
    decision_owner_ref: str,
    rationale: str,
) -> dict[str, Any]:
    """Build only an unanswered request for an external human decision.

    The audit side may identify the target and owner of a required decision,
    but it cannot manufacture a completed human disposition or grant runtime
    authority.  Completed decisions enter through
    :func:`bind_external_human_decision` as already sealed external records.
    """

    validate_pack_manifest(pack_manifest)
    decision: dict[str, Any] = {
        "schema_version": DECISION_VERSION,
        "decision_id": decision_id,
        "target_kind": target_kind,
        "target_id": target_id,
        "target_version": target_version,
        "target_digest": copy.deepcopy(dict(target_digest)),
        "target_pack_manifest_digest": copy.deepcopy(pack_manifest["manifest_digest"]),
        "human_decision": "pending",
        "decision_source": "pending_gate_request",
        "decision_owner_ref": decision_owner_ref,
        "decision_actor_kind": "human",
        "decision_authenticity": {
            "status": "unproved",
            "evidence_ref": None,
        },
        "decided_at": None,
        "record_ref": None,
        "rationale": rationale,
        "granted_authority": _candidate_authority(),
        "revision": None,
    }
    decision["decision_digest"] = sha256_digest(decision)
    validate_human_decision(decision)
    return decision


def bind_external_human_decision(
    decision: Mapping[str, Any],
    *,
    pack_manifest: Mapping[str, Any],
    expected_target_kind: str,
    expected_target_id: str,
    expected_target_version: str,
    expected_target_digest: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate and bind an externally supplied, already sealed decision.

    This function deliberately neither fills fields nor computes a decision
    digest.  A non-pending disposition must pre-exist in the external record;
    this sidecar can only reject it or bind it to the exact governed target.
    """

    validate_pack_manifest(pack_manifest)
    bound = copy.deepcopy(dict(decision))
    validate_human_decision(bound)
    if bound["human_decision"] == "pending":
        raise EngineeringRuleGovernanceError(
            "external human decision binding requires a non-pending disposition"
        )
    if bound["decision_source"] != "external_human_record":
        raise EngineeringRuleGovernanceError(
            "completed human decision must originate from an external human record"
        )
    if (
        bound["target_kind"] != expected_target_kind
        or bound["target_id"] != expected_target_id
        or bound["target_version"] != expected_target_version
        or bound["target_digest"] != expected_target_digest
        or bound["target_pack_manifest_digest"] != pack_manifest["manifest_digest"]
    ):
        raise EngineeringRuleGovernanceError(
            "external human decision target binding mismatch"
        )
    return bound


def validate_human_decision(decision: Mapping[str, Any]) -> None:
    _validate_schema(decision, _subvalidator("human_decision"), "human decision")
    disposition = decision["human_decision"]
    source = decision["decision_source"]
    authenticity = decision["decision_authenticity"]
    if authenticity["status"] == "verified" and not authenticity["evidence_ref"]:
        raise EngineeringRuleGovernanceError(
            "verified human authenticity requires a non-empty evidence reference"
        )
    if disposition == "pending":
        if source != "pending_gate_request":
            raise EngineeringRuleGovernanceError(
                "pending human decision must be a pending gate request"
            )
        if decision["decided_at"] is not None or decision["record_ref"] is not None:
            raise EngineeringRuleGovernanceError(
                "pending human decision cannot carry a completed decision record"
            )
        if authenticity != {"status": "unproved", "evidence_ref": None}:
            raise EngineeringRuleGovernanceError(
                "pending human decision must retain unproved authenticity"
            )
        if decision["revision"] is not None:
            raise EngineeringRuleGovernanceError(
                "pending decision cannot carry revision disposition"
            )
    else:
        if source != "external_human_record":
            raise EngineeringRuleGovernanceError(
                "non-pending human decision requires an external human record"
            )
        if decision["decided_at"] is None or decision["record_ref"] is None:
            raise EngineeringRuleGovernanceError(
                "completed human decision requires timestamp and external record reference"
            )
    if disposition == "request_revision":
        if decision["revision"] is None:
            raise EngineeringRuleGovernanceError(
                "request_revision requires complete revision material"
            )
        _validate_schema(decision["revision"], _subvalidator("revision"), "revision")
    elif decision["revision"] is not None:
        raise EngineeringRuleGovernanceError(
            "revision material is valid only for request_revision"
        )
    if disposition != "accept" and decision["granted_authority"] != CANDIDATE_AUTHORITY:
        raise EngineeringRuleGovernanceError(
            "non-accept decision cannot grant authority"
        )
    if decision["decision_digest"] != sha256_digest(
        _without(decision, "decision_digest")
    ):
        raise EngineeringRuleGovernanceError("human decision digest mismatch")


def build_runtime_rule_request(
    *,
    basis: Mapping[str, Any],
    implementation_binding: Mapping[str, Any],
    requested_authority: Mapping[str, Any],
    observed_artifact_digest: Mapping[str, Any],
    observed_implementation_digest: Mapping[str, Any],
) -> dict[str, Any]:
    validate_rule_basis(basis)
    validate_implementation_binding(implementation_binding)
    return {
        "rule_id": basis["rule_id"],
        "rule_version": basis["rule_version"],
        "basis_digest": copy.deepcopy(basis["basis_digest"]),
        "artifact_digest": copy.deepcopy(dict(observed_artifact_digest)),
        "implementation_digest": copy.deepcopy(dict(observed_implementation_digest)),
        "requested_authority": _authority(requested_authority),
    }


def validate_runtime_receipt(receipt: Mapping[str, Any]) -> None:
    _validate_schema(receipt, _subvalidator("runtime_receipt"), "runtime receipt")
    if receipt["receipt_digest"] != sha256_digest(_without(receipt, "receipt_digest")):
        raise EngineeringRuleGovernanceError("runtime receipt digest mismatch")


def build_runtime_request(
    *,
    request_id: str,
    subject_scope_id: str,
    profile_id: str,
    profile_version: str,
    profile_basis_digest: Mapping[str, Any],
    profile_resolution_status: str,
    evidence_currency: str,
    all_required_obligations_satisfied: bool,
    obligation_assessment_digest: Mapping[str, Any],
    rule_requests: Sequence[Mapping[str, Any]],
    active_exception_ids: Sequence[str] = (),
    runtime_receipts: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    request = {
        "request_id": request_id,
        "subject_scope_id": subject_scope_id,
        "profile_resolution": {
            "profile_id": profile_id,
            "profile_version": profile_version,
            "basis_digest": copy.deepcopy(dict(profile_basis_digest)),
            "resolution_status": profile_resolution_status,
        },
        "evidence_currency": evidence_currency,
        "all_required_obligations_satisfied": all_required_obligations_satisfied,
        "obligation_assessment_digest": copy.deepcopy(
            dict(obligation_assessment_digest)
        ),
        # Do not silently normalize duplicates: ambiguity in the active
        # exception denominator must be rejected by the closed schema.
        "active_exception_ids": sorted(active_exception_ids),
        "runtime_receipts": sorted(
            (copy.deepcopy(dict(item)) for item in runtime_receipts),
            key=lambda item: item["receipt_id"],
        ),
        "rule_requests": sorted(
            (copy.deepcopy(dict(item)) for item in rule_requests), key=_rule_key
        ),
    }
    _validate_schema(request, _subvalidator("runtime_request"), "runtime request")
    _unique(
        list(request["rule_requests"]),
        ("rule_id", "rule_version"),
        "runtime rule request",
    )
    for receipt in request["runtime_receipts"]:
        validate_runtime_receipt(receipt)
    _unique(list(request["runtime_receipts"]), ("receipt_id",), "runtime receipt")
    _unique(
        list(request["runtime_receipts"]),
        ("claim_kind", "target_ref"),
        "runtime receipt claim",
    )
    return request


def _decision_adoption_status(
    decision: Mapping[str, Any] | None,
    decision_trust_status: str,
) -> str:
    if decision is None:
        return "candidate"
    disposition = decision["human_decision"]
    if disposition == "accept":
        return (
            "adopted"
            if decision["decision_authenticity"]["status"] == "verified"
            and decision["decision_authenticity"]["evidence_ref"]
            and decision_trust_status == "externally_verified"
            else "candidate"
        )
    if disposition == "defer":
        return "deferred"
    if disposition == "reject":
        return "rejected"
    return "candidate"


def _decision_trust_status(
    decision: Mapping[str, Any] | None,
    verifier: DecisionVerifier | None,
) -> str:
    if decision is None or decision["human_decision"] == "pending":
        return "not_applicable"
    if (
        decision["decision_authenticity"]["status"] != "verified"
        or not decision["decision_authenticity"]["evidence_ref"]
    ):
        return "verification_failed"
    if _verifier_ref(verifier) is None:
        return "missing_verifier"
    assert verifier is not None
    try:
        verified = verifier(copy.deepcopy(dict(decision)))
    except Exception:  # A trust-provider failure must fail closed.
        return "verification_failed"
    # A caller-supplied callback is not itself an external trust root.  Its
    # successful claim remains candidate material until a separate control-
    # plane registry or signature verifier is integrated.
    return "verifier_claim_accepted" if verified is True else "verification_failed"


def _review_trust_status(
    review: Mapping[str, Any] | None,
    verifier: ReviewerVerifier | None,
) -> str:
    if review is None or review["review_source"] != "external_human_record":
        return "not_applicable"
    if _verifier_ref(verifier) is None:
        return "missing_verifier"
    assert verifier is not None
    try:
        verified = verifier(copy.deepcopy(dict(review)))
    except Exception:  # A trust-provider failure must fail closed.
        return "verification_failed"
    return "verifier_claim_accepted" if verified is True else "verification_failed"


def _runtime_verifier_ref(verifier: RuntimeVerifier | None) -> dict[str, Any] | None:
    return _verifier_ref(verifier)


def _build_trust_context(
    *,
    reviews: Sequence[Mapping[str, Any]],
    decisions: Sequence[Mapping[str, Any]],
    runtime_receipts: Sequence[Mapping[str, Any]],
    review_trust_by_id: Mapping[str, str],
    decision_trust_by_id: Mapping[str, str],
    trusted_reviewer_verifier: ReviewerVerifier | None,
    trusted_decision_verifier: DecisionVerifier | None,
    trusted_runtime_verifier: RuntimeVerifier | None,
) -> dict[str, Any]:
    """Bind verifier identities, exact inputs, and observed outcomes.

    This is a deterministic resolution receipt, not proof that an injected
    verifier itself is trustworthy.  That trust anchor remains external.
    """

    context: dict[str, Any] = {
        "reviewer_verifier_ref": _verifier_ref(trusted_reviewer_verifier),
        "decision_verifier_ref": _verifier_ref(trusted_decision_verifier),
        "runtime_verifier_ref": _runtime_verifier_ref(trusted_runtime_verifier),
        "review_inputs": sorted(
            (
                {
                    "target_id": str(item["review_id"]),
                    "target_record_digest": copy.deepcopy(item["review_digest"]),
                    "trust_status": str(review_trust_by_id[item["review_id"]]),
                }
                for item in reviews
            ),
            key=lambda item: item["target_id"],
        ),
        "decision_inputs": sorted(
            (
                {
                    "target_id": str(item["decision_id"]),
                    "target_record_digest": copy.deepcopy(item["decision_digest"]),
                    "trust_status": str(decision_trust_by_id[item["decision_id"]]),
                }
                for item in decisions
            ),
            key=lambda item: item["target_id"],
        ),
        "runtime_receipt_inputs": sorted(
            (
                {
                    "target_id": str(item["receipt_id"]),
                    "target_record_digest": copy.deepcopy(item["receipt_digest"]),
                }
                for item in runtime_receipts
            ),
            key=lambda item: item["target_id"],
        ),
    }
    context["context_digest"] = sha256_digest(context)
    _validate_schema(context, _subvalidator("trust_context"), "trust context")
    return context


def _source_receipt_target(
    basis: Mapping[str, Any], source_binding: Mapping[str, Any]
) -> str:
    return "/".join(
        (
            str(basis["rule_id"]),
            str(basis["rule_version"]),
            str(source_binding["source_id"]),
            str(source_binding["source_version"]),
            str(source_binding["section_locator"]),
        )
    )


def _source_receipt_claim(
    basis: Mapping[str, Any], source_binding: Mapping[str, Any]
) -> dict[str, str]:
    return sha256_digest(
        {
            "rule_ref": _rule_ref(basis),
            "source_binding": copy.deepcopy(dict(source_binding)),
        }
    )


def _implementation_receipt_claim(
    basis: Mapping[str, Any], implementation: Mapping[str, Any]
) -> dict[str, str]:
    return sha256_digest(
        {
            "rule_ref": _rule_ref(basis),
            "binding_digest": copy.deepcopy(implementation["binding_digest"]),
            "implementation_digest": copy.deepcopy(
                implementation["implementation_digest"]
            ),
            "implementation_status": implementation["implementation_status"],
            "verification_evidence_refs": copy.deepcopy(
                implementation["verification_evidence_refs"]
            ),
        }
    )


def _profile_receipt_claim(runtime_request: Mapping[str, Any]) -> dict[str, str]:
    return sha256_digest(runtime_request["profile_resolution"])


def _currency_receipt_claim(runtime_request: Mapping[str, Any]) -> dict[str, str]:
    return sha256_digest(
        {
            "subject_scope_id": runtime_request["subject_scope_id"],
            "evidence_currency": runtime_request["evidence_currency"],
            "obligation_assessment_digest": copy.deepcopy(
                runtime_request["obligation_assessment_digest"]
            ),
        }
    )


def _obligation_receipt_claim(runtime_request: Mapping[str, Any]) -> dict[str, str]:
    return sha256_digest(
        {
            "subject_scope_id": runtime_request["subject_scope_id"],
            "all_required_obligations_satisfied": runtime_request[
                "all_required_obligations_satisfied"
            ],
            "obligation_assessment_digest": copy.deepcopy(
                runtime_request["obligation_assessment_digest"]
            ),
        }
    )


def _check_runtime_receipt(
    *,
    claim_kind: str,
    target_ref: str,
    expected_claim_digest: Mapping[str, Any],
    receipts: Mapping[tuple[str, str], Mapping[str, Any]],
    trusted_runtime_verifier: RuntimeVerifier | None,
) -> tuple[list[str], list[str]]:
    hard: list[str] = []
    candidate: list[str] = []
    prefix = claim_kind
    receipt = receipts.get((claim_kind, target_ref))
    if receipt is None:
        candidate.append(f"{prefix}_receipt_missing")
        return hard, candidate
    if receipt["claim_digest"] != expected_claim_digest:
        hard.append(f"{prefix}_receipt_claim_mismatch")
        return hard, candidate
    if trusted_runtime_verifier is None:
        candidate.append(f"{prefix}_trusted_runtime_verifier_missing")
        return hard, candidate
    if _runtime_verifier_ref(trusted_runtime_verifier) is None:
        candidate.append(f"{prefix}_runtime_verifier_ref_missing")
        return hard, candidate
    try:
        verified = trusted_runtime_verifier(copy.deepcopy(dict(receipt)))
    except Exception:
        verified = False
    if verified is not True:
        candidate.append(f"{prefix}_receipt_verification_failed")
    else:
        candidate.append(f"{prefix}_verifier_claim_accepted_untrusted")
    return hard, candidate


def _trace(
    *,
    basis: Mapping[str, Any] | None,
    review: Mapping[str, Any] | None,
    decision: Mapping[str, Any] | None,
    implementation: Mapping[str, Any] | None,
    manifest: Mapping[str, Any],
    runtime_request: Mapping[str, Any],
) -> dict[str, Any] | None:
    if None in (basis, review, decision, implementation):
        return None
    assert (
        basis is not None
        and review is not None
        and decision is not None
        and implementation is not None
    )
    return {
        "rule_ref": _rule_ref(basis),
        "source_bindings": copy.deepcopy(basis["source_bindings"]),
        "subject_scope_id": runtime_request["subject_scope_id"],
        "finding_refs": copy.deepcopy(review["finding_refs"]),
        "basis_record_digest": copy.deepcopy(basis["record_digest"]),
        "review_digest": copy.deepcopy(review["review_digest"]),
        "human_decision_digest": copy.deepcopy(decision["decision_digest"]),
        "implementation_binding_digest": copy.deepcopy(
            implementation["binding_digest"]
        ),
        "pack_manifest_digest": copy.deepcopy(manifest["manifest_digest"]),
        "profile_basis_digest": copy.deepcopy(
            runtime_request["profile_resolution"]["basis_digest"]
        ),
    }


def _rule_resolution(
    *,
    requested: Mapping[str, Any],
    required_ref: Mapping[str, Any] | None,
    basis: Mapping[str, Any] | None,
    review: Mapping[str, Any] | None,
    decision: Mapping[str, Any] | None,
    implementation: Mapping[str, Any] | None,
    h1_decision: Mapping[str, Any] | None,
    review_trust_status: str,
    decision_trust_status: str,
    h1_decision_trust_status: str,
    manifest: Mapping[str, Any],
    runtime_request: Mapping[str, Any],
    runtime_receipts: Mapping[tuple[str, str], Mapping[str, Any]],
    trusted_runtime_verifier: RuntimeVerifier | None,
    exception_denominator_reasons: Sequence[str],
) -> dict[str, Any]:
    hard: list[str] = list(exception_denominator_reasons)
    candidate: list[str] = ["external_trust_control_not_integrated"]
    for claim_kind, target_ref, expected_digest in (
        (
            "profile_resolution",
            str(runtime_request["profile_resolution"]["profile_id"]),
            _profile_receipt_claim(runtime_request),
        ),
        (
            "evidence_currency",
            str(runtime_request["request_id"]),
            _currency_receipt_claim(runtime_request),
        ),
        (
            "obligation_assessment",
            str(runtime_request["request_id"]),
            _obligation_receipt_claim(runtime_request),
        ),
    ):
        receipt_hard, receipt_candidate = _check_runtime_receipt(
            claim_kind=claim_kind,
            target_ref=target_ref,
            expected_claim_digest=expected_digest,
            receipts=runtime_receipts,
            trusted_runtime_verifier=trusted_runtime_verifier,
        )
        hard.extend(receipt_hard)
        candidate.extend(receipt_candidate)
    if runtime_request["subject_scope_id"] not in manifest["subject_scope_ids"]:
        hard.append("pack_subject_scope_mismatch")
    if required_ref is None:
        hard.append("rule_not_in_required_denominator")
    if basis is None:
        hard.append("unknown_or_unsupported_rule_identity")
    else:
        if requested["rule_version"] != basis["rule_version"]:
            hard.append("rule_version_mismatch")
        if requested["basis_digest"] != basis["basis_digest"]:
            hard.append("rule_basis_digest_mismatch")
        if requested["artifact_digest"] != basis["artifact_digest"]:
            hard.append("rule_artifact_digest_mismatch")
        if (
            required_ref is not None
            and required_ref["basis_digest"] != basis["basis_digest"]
        ):
            hard.append("pack_rule_basis_mismatch")
        if (
            runtime_request["subject_scope_id"]
            not in basis["applicability"]["scope_ids"]
        ):
            hard.append("rule_scope_mismatch")
        active = set(runtime_request["active_exception_ids"])
        if active & {item["exception_id"] for item in basis["exceptions"]}:
            hard.append("active_exception_requires_disposition")
        for source_binding in basis["source_bindings"]:
            if source_binding["binding_status"] != "verified":
                candidate.append("source_binding_not_verified")
                continue
            receipt_hard, receipt_candidate = _check_runtime_receipt(
                claim_kind="source_binding",
                target_ref=_source_receipt_target(basis, source_binding),
                expected_claim_digest=_source_receipt_claim(basis, source_binding),
                receipts=runtime_receipts,
                trusted_runtime_verifier=trusted_runtime_verifier,
            )
            hard.extend(receipt_hard)
            candidate.extend(receipt_candidate)
    if review is None:
        candidate.append("review_missing")
        evidence_status = "unverified"
    else:
        evidence_status = review["evidence_status"]
        if basis is not None and review["rule_ref"] != _rule_ref(basis):
            hard.append("review_target_mismatch")
        if review["review_authority"] != "adoption_material":
            candidate.append("review_candidate_only")
        elif review_trust_status != "externally_verified":
            candidate.append(f"review_{review_trust_status}")
        if review["evidence_status"] != "sufficient":
            candidate.append("rule_evidence_not_sufficient")
        if review["audit_assessment"] != "adoption_ready":
            candidate.append("rule_adoption_not_ready")
    if decision is None:
        candidate.append("human_decision_missing")
    else:
        if basis is not None and (
            decision["target_kind"] != "rule"
            or decision["target_id"] != basis["rule_id"]
            or decision["target_version"] != basis["rule_version"]
            or decision["target_digest"] != basis["basis_digest"]
            or decision["target_pack_manifest_digest"] != manifest["manifest_digest"]
        ):
            hard.append("human_decision_target_mismatch")
        disposition = decision["human_decision"]
        if disposition != "accept":
            candidate.append(f"human_decision_{disposition}")
        if (
            decision["decision_authenticity"]["status"] != "verified"
            or not decision["decision_authenticity"]["evidence_ref"]
        ):
            candidate.append("human_decision_authenticity_unproved")
        if disposition != "pending" and decision_trust_status != "externally_verified":
            candidate.append(f"human_decision_{decision_trust_status}")
        if basis is not None and not _authority_within(
            decision["granted_authority"], basis["requested_authority"]
        ):
            hard.append("granted_authority_exceeds_rule_basis")
        if requested["requested_authority"] != decision["granted_authority"]:
            hard.append("runtime_authority_request_mismatch")
    if implementation is None:
        candidate.append("implementation_binding_missing")
        implementation_status = "unknown"
    else:
        implementation_status = implementation["implementation_status"]
        if basis is not None and implementation["rule_ref"] != _rule_ref(basis):
            hard.append("implementation_rule_target_mismatch")
        if (
            requested["implementation_digest"]
            != implementation["implementation_digest"]
        ):
            hard.append("implementation_digest_mismatch")
        if implementation["implementation_status"] != "verified":
            candidate.append("implementation_not_verified")
        elif basis is not None:
            receipt_hard, receipt_candidate = _check_runtime_receipt(
                claim_kind="implementation_verification",
                target_ref=str(implementation["binding_id"]),
                expected_claim_digest=_implementation_receipt_claim(
                    basis, implementation
                ),
                receipts=runtime_receipts,
                trusted_runtime_verifier=trusted_runtime_verifier,
            )
            hard.extend(receipt_hard)
            candidate.extend(receipt_candidate)
    profile = runtime_request["profile_resolution"]
    if profile["resolution_status"] == "unresolved":
        hard.append("profile_resolution_unresolved")
    elif profile["resolution_status"] != "resolved_formal":
        candidate.append("profile_candidate_only")
    if runtime_request["evidence_currency"] != "current":
        hard.append("evidence_not_current")
    if h1_decision is None:
        candidate.append("h1_human_decision_missing")
    else:
        if (
            h1_decision["target_kind"] != "h1_gate"
            or h1_decision["target_id"] != "H1"
            or h1_decision["target_version"] != manifest["pack_version"]
            or h1_decision["target_digest"] != manifest["manifest_digest"]
            or h1_decision["target_pack_manifest_digest"] != manifest["manifest_digest"]
        ):
            hard.append("h1_human_decision_target_mismatch")
        if h1_decision["human_decision"] != "accept":
            candidate.append(f"h1_human_decision_{h1_decision['human_decision']}")
        if (
            h1_decision["decision_authenticity"]["status"] != "verified"
            or not h1_decision["decision_authenticity"]["evidence_ref"]
        ):
            candidate.append("h1_human_decision_authenticity_unproved")
        if (
            h1_decision["human_decision"] != "pending"
            and h1_decision_trust_status != "externally_verified"
        ):
            candidate.append(f"h1_human_decision_{h1_decision_trust_status}")

    if hard:
        status = "unresolved"
        authority = _candidate_authority()
        reasons = sorted(set(hard + candidate))
    elif candidate:
        status = "candidate_only"
        authority = _candidate_authority()
        reasons = sorted(set(candidate))
    else:
        status = "resolved_formal"
        assert decision is not None
        authority = copy.deepcopy(decision["granted_authority"])
        reasons = ["exact_runtime_resolution"]
    resolution: dict[str, Any] = {
        "rule_id": requested["rule_id"],
        "rule_version": requested["rule_version"],
        "resolution_status": status,
        "governance_states": {
            "evidence_status": evidence_status,
            "adoption_status": _decision_adoption_status(
                decision, decision_trust_status
            ),
            "implementation_status": implementation_status,
            "review_trust_status": review_trust_status,
            "decision_trust_status": decision_trust_status,
        },
        "effective_authority": authority,
        "reason_codes": reasons,
        "trace": _trace(
            basis=basis,
            review=review,
            decision=decision,
            implementation=implementation,
            manifest=manifest,
            runtime_request=runtime_request,
        ),
    }
    resolution["resolution_digest"] = sha256_digest(resolution)
    return resolution


def resolve_runtime(
    *,
    resolution_id: str,
    rule_bases: Sequence[Mapping[str, Any]],
    reviews: Sequence[Mapping[str, Any]],
    human_decisions: Sequence[Mapping[str, Any]],
    implementation_bindings: Sequence[Mapping[str, Any]],
    pack_manifest: Mapping[str, Any],
    runtime_request: Mapping[str, Any],
    trusted_reviewer_verifier: ReviewerVerifier | None = None,
    trusted_decision_verifier: DecisionVerifier | None = None,
    trusted_runtime_verifier: RuntimeVerifier | None = None,
) -> dict[str, Any]:
    validate_pack_manifest(pack_manifest)
    _validate_schema(
        runtime_request, _subvalidator("runtime_request"), "runtime request"
    )
    for basis in rule_bases:
        validate_rule_basis(basis)
    for review in reviews:
        validate_review(review)
    for decision in human_decisions:
        validate_human_decision(decision)
    for implementation in implementation_bindings:
        validate_implementation_binding(implementation)
    for receipt in runtime_request["runtime_receipts"]:
        validate_runtime_receipt(receipt)
    _unique(list(rule_bases), ("rule_id", "rule_version"), "runtime rule basis")
    _unique(list(reviews), ("review_id",), "runtime review")
    _unique(list(human_decisions), ("decision_id",), "runtime human decision")
    _unique(
        list(implementation_bindings),
        ("binding_id",),
        "runtime implementation binding",
    )
    _unique(
        list(runtime_request["rule_requests"]),
        ("rule_id", "rule_version"),
        "runtime rule request",
    )
    _unique(
        list(runtime_request["runtime_receipts"]),
        ("receipt_id",),
        "runtime receipt",
    )
    _unique(
        list(runtime_request["runtime_receipts"]),
        ("claim_kind", "target_ref"),
        "runtime receipt claim",
    )
    bases = {_rule_key(item): item for item in rule_bases}
    review_by_key = {_rule_key(item["rule_ref"]): item for item in reviews}
    decision_by_key = {
        (item["target_id"], item["target_version"]): item
        for item in human_decisions
        if item["target_kind"] == "rule"
    }
    implementation_by_key = {
        _rule_key(item["rule_ref"]): item for item in implementation_bindings
    }
    h1_decisions = [
        item for item in human_decisions if item["target_kind"] == "h1_gate"
    ]
    rule_decisions = [item for item in human_decisions if item["target_kind"] == "rule"]
    if len({_rule_key(item["rule_ref"]) for item in reviews}) != len(reviews):
        raise EngineeringRuleGovernanceError(
            "runtime requires at most one review per rule"
        )
    if len(
        {(item["target_id"], item["target_version"]) for item in rule_decisions}
    ) != len(rule_decisions):
        raise EngineeringRuleGovernanceError(
            "runtime requires at most one active human decision per rule"
        )
    if len({_rule_key(item["rule_ref"]) for item in implementation_bindings}) != len(
        implementation_bindings
    ):
        raise EngineeringRuleGovernanceError(
            "runtime requires at most one implementation binding per rule"
        )
    if len(h1_decisions) != 1:
        raise EngineeringRuleGovernanceError(
            "runtime requires exactly one H1 human decision record"
        )
    h1_decision = h1_decisions[0] if len(h1_decisions) == 1 else None
    decision_trust_by_id = {
        item["decision_id"]: _decision_trust_status(item, trusted_decision_verifier)
        for item in human_decisions
    }
    h1_decision_trust_status = (
        decision_trust_by_id[h1_decision["decision_id"]]
        if h1_decision is not None
        else "not_applicable"
    )
    review_trust_by_id = {
        item["review_id"]: _review_trust_status(item, trusted_reviewer_verifier)
        for item in reviews
    }
    trust_context = _build_trust_context(
        reviews=reviews,
        decisions=human_decisions,
        runtime_receipts=runtime_request["runtime_receipts"],
        review_trust_by_id=review_trust_by_id,
        decision_trust_by_id=decision_trust_by_id,
        trusted_reviewer_verifier=trusted_reviewer_verifier,
        trusted_decision_verifier=trusted_decision_verifier,
        trusted_runtime_verifier=trusted_runtime_verifier,
    )
    required = {
        _rule_key(item): item for item in pack_manifest["required_rule_denominator"]
    }
    requested = {_rule_key(item): item for item in runtime_request["rule_requests"]}
    exception_owners: dict[str, set[tuple[str, str]]] = {}
    for basis in rule_bases:
        for exception in basis["exceptions"]:
            exception_owners.setdefault(str(exception["exception_id"]), set()).add(
                _rule_key(basis)
            )
    duplicate_exception_ids = {
        exception_id
        for exception_id, owners in exception_owners.items()
        if len(owners) != 1
    }
    unknown_active_exception_ids = set(runtime_request["active_exception_ids"]) - set(
        exception_owners
    )
    exception_denominator_reasons: list[str] = []
    if duplicate_exception_ids:
        exception_denominator_reasons.append("duplicate_exception_identifier")
    if unknown_active_exception_ids:
        exception_denominator_reasons.append("unknown_active_exception_identifier")
    runtime_receipts = {
        (str(item["claim_kind"]), str(item["target_ref"])): item
        for item in runtime_request["runtime_receipts"]
    }
    resolutions: list[dict[str, Any]] = []
    for key in sorted(set(required) | set(requested)):
        request = requested.get(key)
        if request is None:
            required_ref = required[key]
            request = {
                "rule_id": required_ref["rule_id"],
                "rule_version": required_ref["rule_version"],
                "basis_digest": copy.deepcopy(required_ref["basis_digest"]),
                "artifact_digest": sha256_digest("missing-artifact"),
                "implementation_digest": sha256_digest("missing-implementation"),
                "requested_authority": _candidate_authority(),
            }
        resolutions.append(
            _rule_resolution(
                requested=request,
                required_ref=required.get(key),
                basis=bases.get(key),
                review=review_by_key.get(key),
                decision=decision_by_key.get(key),
                implementation=implementation_by_key.get(key),
                h1_decision=h1_decision,
                review_trust_status=(
                    review_trust_by_id[review_by_key[key]["review_id"]]
                    if key in review_by_key
                    else "not_applicable"
                ),
                decision_trust_status=(
                    decision_trust_by_id[decision_by_key[key]["decision_id"]]
                    if key in decision_by_key
                    else "not_applicable"
                ),
                h1_decision_trust_status=h1_decision_trust_status,
                manifest=pack_manifest,
                runtime_request=runtime_request,
                runtime_receipts=runtime_receipts,
                trusted_runtime_verifier=trusted_runtime_verifier,
                exception_denominator_reasons=exception_denominator_reasons,
            )
        )
    required_resolutions = [item for item in resolutions if _rule_key(item) in required]
    formal_count = sum(
        item["resolution_status"] == "resolved_formal" for item in required_resolutions
    )
    candidate_count = sum(
        item["resolution_status"] == "candidate_only" for item in required_resolutions
    )
    unresolved_count = sum(
        item["resolution_status"] == "unresolved" for item in required_resolutions
    )
    pack_reasons: list[str] = []
    pack_reasons.append("external_trust_control_not_integrated")
    if exception_denominator_reasons:
        pack_reasons.extend(exception_denominator_reasons)
        pack_reasons.append("exception_denominator_unresolved")
    runtime_scope_in_pack = (
        runtime_request["subject_scope_id"] in pack_manifest["subject_scope_ids"]
    )
    if not runtime_scope_in_pack:
        pack_reasons.append("pack_subject_scope_mismatch")
    if set(requested) != set(required):
        pack_reasons.append("runtime_rule_denominator_mismatch")
    if not runtime_request["all_required_obligations_satisfied"]:
        pack_reasons.append("required_obligations_not_satisfied")
    if unresolved_count:
        pack_reasons.append("required_rule_resolution_unresolved")
    if candidate_count:
        pack_reasons.append("required_rule_resolution_candidate_only")
    all_final = all(
        item["effective_authority"]["final_verdict_authority"] == "permitted"
        for item in required_resolutions
    )
    if not all_final:
        pack_reasons.append("final_verdict_authority_incomplete")
    formal_pack = (
        runtime_scope_in_pack
        and set(requested) == set(required)
        and not exception_denominator_reasons
        and formal_count == len(required)
        and not candidate_count
        and not unresolved_count
        and runtime_request["all_required_obligations_satisfied"]
        and all_final
    )
    if formal_pack:
        pack_status = "resolved_formal"
        formal_verdict = "permitted"
    elif (
        not runtime_scope_in_pack
        or unresolved_count
        or set(requested) != set(required)
        or bool(exception_denominator_reasons)
    ):
        pack_status = "unresolved"
        formal_verdict = "none"
    else:
        pack_status = "candidate_only"
        formal_verdict = "none"
    resolution: dict[str, Any] = {
        "schema_version": RESOLUTION_VERSION,
        "resolution_id": resolution_id,
        "pack_ref": {
            "pack_id": pack_manifest["pack_id"],
            "pack_version": pack_manifest["pack_version"],
            "manifest_digest": copy.deepcopy(pack_manifest["manifest_digest"]),
        },
        "runtime_request": copy.deepcopy(dict(runtime_request)),
        "trust_context": trust_context,
        "rule_resolutions": resolutions,
        "pack_resolution": {
            "status": pack_status,
            "required_rule_count": len(required),
            "resolved_formal_count": formal_count,
            "candidate_count": candidate_count,
            "unresolved_count": unresolved_count,
            "blocking_unresolved_count": len(required) - formal_count,
            "formal_verdict_authority": formal_verdict,
            "h1_decision_trust_status": h1_decision_trust_status,
            "reviewer_verifier_ref": _verifier_ref(trusted_reviewer_verifier),
            "decision_verifier_ref": _verifier_ref(trusted_decision_verifier),
            "runtime_verifier_ref": _runtime_verifier_ref(trusted_runtime_verifier),
            "reason_codes": sorted(set(pack_reasons)),
        },
    }
    resolution["resolution_digest"] = sha256_digest(resolution)
    _validate_schema(
        resolution, _subvalidator("runtime_resolution"), "runtime resolution"
    )
    return resolution


def build_h1_gate_view(
    *,
    reviews: Sequence[Mapping[str, Any]],
    pack_manifest: Mapping[str, Any],
    h1_decision: Mapping[str, Any],
    runtime_resolution: Mapping[str, Any],
    trusted_decision_verifier: DecisionVerifier | None = None,
) -> dict[str, Any]:
    validate_pack_manifest(pack_manifest)
    required_keys = {
        _rule_key(item) for item in pack_manifest["required_rule_denominator"]
    }
    required_reviews = [
        item for item in reviews if _rule_key(item["rule_ref"]) in required_keys
    ]
    non_required_reviews = [
        item for item in reviews if _rule_key(item["rule_ref"]) not in required_keys
    ]
    assessments = {str(item["audit_assessment"]) for item in required_reviews}
    if "conflicting" in assessments:
        assessment = "conflicting"
    elif "adoption_not_ready" in assessments:
        assessment = "adoption_not_ready"
    elif "not_assessed" in assessments:
        assessment = "not_assessed"
    else:
        assessment = "adoption_ready_for_human_decision"
    recommendations = {
        str(item["non_binding_recommendation"]) for item in required_reviews
    }
    recommendation = next(
        (
            item
            for item in ("reject", "request_revision", "defer", "accept")
            if item in recommendations
        ),
        "none",
    )
    reported_disposition = str(h1_decision["human_decision"])
    decision_trust_status = str(
        runtime_resolution["pack_resolution"]["h1_decision_trust_status"]
    )
    expected_decision_trust_status = _decision_trust_status(
        h1_decision, trusted_decision_verifier
    )
    if decision_trust_status != expected_decision_trust_status:
        raise EngineeringRuleGovernanceError(
            "H1 decision trust status does not match the injected verifier"
        )
    disposition = (
        reported_disposition
        if reported_disposition == "pending"
        or decision_trust_status == "externally_verified"
        else "pending"
    )
    pack_formal = runtime_resolution["pack_resolution"]["status"] == "resolved_formal"
    if disposition == "request_revision":
        revision = h1_decision["revision"]
        next_action = str(revision["next_action"])
        resolution_condition = "; ".join(revision["resolution_conditions"])
    elif disposition == "pending":
        next_action = "Obtain an explicit external human H1 decision without converting audit material into that decision."
        resolution_condition = "A digest-bound H1 decision and all required rule-level governance records are resolved."
    elif disposition == "accept" and not pack_formal:
        next_action = "Resolve remaining rule, implementation, profile, scope, currency, and authority bindings."
        resolution_condition = "The exact required denominator resolves formally with no blocking unresolved item."
    elif disposition == "accept":
        next_action = "Preserve the resolved bundle and monitor invalidation triggers."
        resolution_condition = (
            "No current invalidation or supersession trigger is present."
        )
    elif disposition == "defer":
        next_action = "Retain candidate-only authority until the recorded review point."
        resolution_condition = "A later external human decision reopens H1."
    else:
        next_action = "Keep the pack outside formal runtime authority."
        resolution_condition = (
            "A new version and new external human decision replace the rejected target."
        )
    gate: dict[str, Any] = {
        "schema_version": GATE_VERSION,
        "gate_id": "H1",
        "subject": "engineering_rule_pack",
        "assessment_scope": "required_rule_denominator",
        "non_required_review_count": len(non_required_reviews),
        "non_required_review_assessments": sorted(
            {str(item["audit_assessment"]) for item in non_required_reviews}
        ),
        "audit_assessment": assessment,
        "non_binding_recommendation": recommendation,
        "human_decision": disposition,
        "reported_human_decision": reported_disposition,
        "decision_trust_status": decision_trust_status,
        "human_decision_ref": h1_decision["decision_id"],
        "decision_owner": "human",
        "blocking_status": "not_blocking"
        if pack_formal
        else "blocking_positive_assurance",
        "next_action": next_action,
        "resolution_condition": resolution_condition,
        "verdict_authority": "formal" if pack_formal else "none",
    }
    gate["gate_digest"] = sha256_digest(gate)
    _validate_schema(gate, _subvalidator("h1_gate_view"), "H1 gate view")
    return gate


def build_governance_bundle(
    *,
    bundle_id: str,
    bundle_version: str,
    rule_bases: Sequence[Mapping[str, Any]],
    reviews: Sequence[Mapping[str, Any]],
    human_decisions: Sequence[Mapping[str, Any]],
    implementation_bindings: Sequence[Mapping[str, Any]],
    pack_manifest: Mapping[str, Any],
    runtime_request: Mapping[str, Any],
    resolution_id: str,
    trusted_reviewer_verifier: ReviewerVerifier | None = None,
    trusted_decision_verifier: DecisionVerifier | None = None,
    trusted_runtime_verifier: RuntimeVerifier | None = None,
    limitations: Sequence[str] = _LIMITATIONS,
) -> dict[str, Any]:
    if not set(_LIMITATIONS).issubset(set(limitations)):
        raise EngineeringRuleGovernanceError(
            "governance bundle cannot remove required limitations"
        )
    bases = sorted((copy.deepcopy(dict(item)) for item in rule_bases), key=_rule_key)
    review_values = sorted(
        (copy.deepcopy(dict(item)) for item in reviews),
        key=lambda item: item["review_id"],
    )
    decision_values = sorted(
        (copy.deepcopy(dict(item)) for item in human_decisions),
        key=lambda item: item["decision_id"],
    )
    implementation_values = sorted(
        (copy.deepcopy(dict(item)) for item in implementation_bindings),
        key=lambda item: item["binding_id"],
    )
    resolution = resolve_runtime(
        resolution_id=resolution_id,
        rule_bases=bases,
        reviews=review_values,
        human_decisions=decision_values,
        implementation_bindings=implementation_values,
        pack_manifest=pack_manifest,
        runtime_request=runtime_request,
        trusted_reviewer_verifier=trusted_reviewer_verifier,
        trusted_decision_verifier=trusted_decision_verifier,
        trusted_runtime_verifier=trusted_runtime_verifier,
    )
    h1_values = [item for item in decision_values if item["target_kind"] == "h1_gate"]
    if len(h1_values) != 1:
        raise EngineeringRuleGovernanceError(
            "bundle requires exactly one H1 human decision record"
        )
    gate = build_h1_gate_view(
        reviews=review_values,
        pack_manifest=pack_manifest,
        h1_decision=h1_values[0],
        runtime_resolution=resolution,
        trusted_decision_verifier=trusted_decision_verifier,
    )
    bundle: dict[str, Any] = {
        "schema_version": BUNDLE_VERSION,
        "bundle_id": bundle_id,
        "bundle_version": bundle_version,
        "normalization_profile": NORMALIZATION_PROFILE,
        "rule_bases": bases,
        "reviews": review_values,
        "human_decisions": decision_values,
        "implementation_bindings": implementation_values,
        "pack_manifest": copy.deepcopy(dict(pack_manifest)),
        "runtime_resolution": resolution,
        "h1_gate_view": gate,
        "limitations": sorted(set(limitations)),
    }
    bundle["bundle_digest"] = sha256_digest(bundle)
    validate_governance_bundle(
        bundle,
        trusted_reviewer_verifier=trusted_reviewer_verifier,
        trusted_decision_verifier=trusted_decision_verifier,
        trusted_runtime_verifier=trusted_runtime_verifier,
    )
    return bundle


def validate_governance_bundle(
    bundle: Mapping[str, Any],
    *,
    trusted_reviewer_verifier: ReviewerVerifier | None = None,
    trusted_decision_verifier: DecisionVerifier | None = None,
    trusted_runtime_verifier: RuntimeVerifier | None = None,
) -> None:
    _validate_schema(bundle, _bundle_validator(), "engineering rule governance bundle")
    if not set(_LIMITATIONS).issubset(set(bundle["limitations"])):
        raise EngineeringRuleGovernanceError(
            "governance bundle is missing required limitations"
        )
    bases = list(bundle["rule_bases"])
    reviews = list(bundle["reviews"])
    decisions = list(bundle["human_decisions"])
    implementations = list(bundle["implementation_bindings"])
    manifest = bundle["pack_manifest"]
    for basis in bases:
        validate_rule_basis(basis)
    for review in reviews:
        validate_review(review)
    for decision in decisions:
        validate_human_decision(decision)
    for implementation in implementations:
        validate_implementation_binding(implementation)
    validate_pack_manifest(manifest)
    _unique(bases, ("rule_id", "rule_version"), "rule basis")
    _unique(reviews, ("review_id",), "review")
    _unique(decisions, ("decision_id",), "human decision")
    _unique(implementations, ("binding_id",), "implementation binding")
    basis_by_key = {_rule_key(item): item for item in bases}
    partitions = (
        list(manifest["required_rule_denominator"])
        + list(manifest["optional_rule_denominator"])
        + [item["rule_ref"] for item in manifest["excluded_rules"]]
    )
    if {_rule_key(item) for item in partitions} != set(basis_by_key):
        raise EngineeringRuleGovernanceError(
            "pack partitions must close exactly over the rule basis denominator"
        )
    for reference in partitions:
        basis = basis_by_key[_rule_key(reference)]
        if reference != _rule_ref(basis):
            raise EngineeringRuleGovernanceError(
                "pack reference does not match rule basis"
            )
    review_keys = [_rule_key(item["rule_ref"]) for item in reviews]
    implementation_keys = [_rule_key(item["rule_ref"]) for item in implementations]
    rule_decisions = [item for item in decisions if item["target_kind"] == "rule"]
    decision_keys = [
        (item["target_id"], item["target_version"]) for item in rule_decisions
    ]
    for label, values in (
        ("review", review_keys),
        ("implementation", implementation_keys),
        ("rule decision", decision_keys),
    ):
        if len(values) != len(set(values)) or set(values) != set(basis_by_key):
            raise EngineeringRuleGovernanceError(
                f"bundle requires exactly one {label} per rule basis"
            )
    for review in reviews:
        if review["rule_ref"] != _rule_ref(basis_by_key[_rule_key(review["rule_ref"])]):
            raise EngineeringRuleGovernanceError("review reference mismatch")
    for implementation in implementations:
        if implementation["rule_ref"] != _rule_ref(
            basis_by_key[_rule_key(implementation["rule_ref"])]
        ):
            raise EngineeringRuleGovernanceError("implementation reference mismatch")
    for decision in rule_decisions:
        basis = basis_by_key[(decision["target_id"], decision["target_version"])]
        if (
            decision["target_digest"] != basis["basis_digest"]
            or decision["target_pack_manifest_digest"] != manifest["manifest_digest"]
        ):
            raise EngineeringRuleGovernanceError("rule decision target mismatch")
        if not _authority_within(
            decision["granted_authority"], basis["requested_authority"]
        ):
            raise EngineeringRuleGovernanceError(
                "decision authority exceeds rule basis"
            )
    h1 = [item for item in decisions if item["target_kind"] == "h1_gate"]
    if len(h1) != 1:
        raise EngineeringRuleGovernanceError("bundle requires exactly one H1 decision")
    if (
        h1[0]["target_id"] != "H1"
        or h1[0]["target_version"] != manifest["pack_version"]
        or h1[0]["target_digest"] != manifest["manifest_digest"]
        or h1[0]["target_pack_manifest_digest"] != manifest["manifest_digest"]
    ):
        raise EngineeringRuleGovernanceError("H1 decision target mismatch")
    expected_resolution = resolve_runtime(
        resolution_id=bundle["runtime_resolution"]["resolution_id"],
        rule_bases=bases,
        reviews=reviews,
        human_decisions=decisions,
        implementation_bindings=implementations,
        pack_manifest=manifest,
        runtime_request=bundle["runtime_resolution"]["runtime_request"],
        trusted_reviewer_verifier=trusted_reviewer_verifier,
        trusted_decision_verifier=trusted_decision_verifier,
        trusted_runtime_verifier=trusted_runtime_verifier,
    )
    if bundle["runtime_resolution"] != expected_resolution:
        raise EngineeringRuleGovernanceError("runtime resolution replay mismatch")
    expected_gate = build_h1_gate_view(
        reviews=reviews,
        pack_manifest=manifest,
        h1_decision=h1[0],
        runtime_resolution=expected_resolution,
        trusted_decision_verifier=trusted_decision_verifier,
    )
    if bundle["h1_gate_view"] != expected_gate:
        raise EngineeringRuleGovernanceError("H1 gate view replay mismatch")
    if bundle["bundle_digest"] != sha256_digest(_without(bundle, "bundle_digest")):
        raise EngineeringRuleGovernanceError("governance bundle digest mismatch")


__all__ = [
    "BUNDLE_VERSION",
    "CANDIDATE_AUTHORITY",
    "EngineeringRuleGovernanceError",
    "bind_external_human_decision",
    "bind_external_human_review",
    "build_candidate_review",
    "build_governance_bundle",
    "build_h1_gate_view",
    "build_implementation_binding",
    "build_pack_manifest",
    "build_pending_human_decision",
    "build_rule_basis",
    "build_runtime_request",
    "build_runtime_rule_request",
    "resolve_runtime",
    "sha256_bytes",
    "sha256_digest",
    "validate_governance_bundle",
    "validate_runtime_receipt",
]
