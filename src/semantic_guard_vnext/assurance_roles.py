"""Candidate-only responsibility and review-independence contracts.

The records in this module describe capability ceilings and review context.
They do not dispatch work, grant authority, authenticate a person, or adopt a
review.  Every returned record therefore keeps ``formal_authority`` at
``none`` or its review equivalent.
"""

from __future__ import annotations

import copy
from functools import lru_cache
import hashlib
import json
from typing import Any, Callable, Iterable, Mapping, Sequence

from jsonschema import Draft202012Validator, FormatChecker

from .schema_access import schema_path


ROLE_BINDING_VERSION = "assurance-role-binding/v1"
REVIEW_VERSION = "assurance-review/v1"

CAPABILITIES = frozenset(
    {
        "set_objective",
        "adopt",
        "waive",
        "accept_risk",
        "final_acceptance",
        "grant_authority",
        "record_external_decision",
        "apply_adopted_policy",
        "manage_hold",
        "manage_unresolved",
        "route_next_action",
        "plan",
        "technical_decision",
        "execute_authorized",
        "request_audit",
        "observe_occurrence",
        "collect_raw_evidence",
        "evaluate_under_adopted_rules",
        "emit_finding",
        "escalate_unresolved",
        "emit_non_binding_recommendation",
        "emit_candidate_review",
    }
)

ROLE_CAPABILITY_CEILINGS: dict[str, frozenset[str]] = {
    "human_decision": frozenset(
        {
            "set_objective",
            "adopt",
            "waive",
            "accept_risk",
            "final_acceptance",
            "grant_authority",
        }
    ),
    "control_plane": frozenset(
        {
            "record_external_decision",
            "apply_adopted_policy",
            "manage_hold",
            "manage_unresolved",
            "route_next_action",
        }
    ),
    "ai_agent": frozenset(
        {"plan", "technical_decision", "execute_authorized", "request_audit"}
    ),
    "execution_harness": frozenset({"observe_occurrence", "collect_raw_evidence"}),
    "audit_system": frozenset(
        {
            "evaluate_under_adopted_rules",
            "emit_finding",
            "escalate_unresolved",
            "emit_non_binding_recommendation",
        }
    ),
    "llm_reviewer": frozenset({"emit_candidate_review"}),
}

_ROLE_LIMITATION = (
    "This binding is candidate audit material; an external authority resolver "
    "must establish any effective permission."
)
_REVIEW_LIMITATION = (
    "Review output is candidate-only and cannot adopt, waive, accept risk, "
    "release a hold, or perform final acceptance."
)
_IDENTITY_LIMITATION = (
    "Reviewer identity and human independence remain unresolved; a supplied "
    "callback, including one with a content-addressed verifier reference, is "
    "not a control-plane trust registry or signature trust root."
)
_TRUST_ROOT_LIMITATION = (
    "A future contract must bind identity verification to a control-plane "
    "trust registry or signature trust root before independent human review "
    "can be established."
)
_SCHEMA_PATH = schema_path("assurance-role-binding.schema.json")


class AssuranceRoleError(ValueError):
    """Raised when responsibility or review context fails closed."""


IdentityVerifier = Callable[[Mapping[str, Any]], bool]


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _digest(value: Any) -> dict[str, str]:
    return {
        "algorithm": "sha256",
        "value": hashlib.sha256(_canonical(value)).hexdigest(),
    }


def _without(value: Mapping[str, Any], *fields: str) -> dict[str, Any]:
    result = copy.deepcopy(dict(value))
    for field in fields:
        result.pop(field, None)
    return result


def _identity_key(value: Mapping[str, Any]) -> tuple[str, str, str]:
    return (
        str(value["entity_id"]),
        str(value["entity_version"]),
        str(value["content_digest"]["value"]),
    )


@lru_cache(maxsize=1)
def assurance_role_schema() -> dict[str, Any]:
    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return schema


@lru_cache(maxsize=None)
def _validator(definition: str) -> Draft202012Validator:
    root = assurance_role_schema()
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$defs": root["$defs"],
        "$ref": f"#/$defs/{definition}",
    }
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _schema_validate(value: Mapping[str, Any], definition: str, contract: str) -> None:
    issues = sorted(
        _validator(definition).iter_errors(value),
        key=lambda item: tuple(str(part) for part in item.absolute_path),
    )
    if issues:
        issue = issues[0]
        location = "/".join(str(part) for part in issue.absolute_path) or "/"
        raise AssuranceRoleError(
            f"{contract} schema violation at {location}: {issue.message}"
        )


def role_capability_ceiling(role_surface: str) -> tuple[str, ...]:
    """Return the immutable capability ceiling for one responsibility surface."""

    try:
        return tuple(sorted(ROLE_CAPABILITY_CEILINGS[role_surface]))
    except KeyError as exc:
        raise AssuranceRoleError(f"unknown role surface: {role_surface}") from exc


def build_role_binding(
    *,
    binding_id: str,
    actor_ref: Mapping[str, Any],
    role_surface: str,
    granted_capabilities: Iterable[str] = (),
    authority_ref: Mapping[str, Any] | None = None,
    limitations: Sequence[str] = (),
) -> dict[str, Any]:
    """Build a capability-bounded record without granting formal authority."""

    ceiling = set(role_capability_ceiling(role_surface))
    granted = set(str(item) for item in granted_capabilities)
    unknown = granted - CAPABILITIES
    if unknown:
        raise AssuranceRoleError(f"unknown capabilities: {sorted(unknown)!r}")
    if not granted <= ceiling:
        raise AssuranceRoleError(
            f"role {role_surface} exceeds its capability ceiling: "
            f"{sorted(granted - ceiling)!r}"
        )
    if granted and authority_ref is None:
        raise AssuranceRoleError(
            "granted capabilities require an external authority record reference"
        )
    material: dict[str, Any] = {
        "schema_version": ROLE_BINDING_VERSION,
        "binding_id": binding_id,
        "actor_ref": copy.deepcopy(dict(actor_ref)),
        "role_surface": role_surface,
        "authority_ref": (
            copy.deepcopy(dict(authority_ref)) if authority_ref is not None else None
        ),
        "granted_capabilities": sorted(granted),
        "capability_ceiling": sorted(ceiling),
        "prohibited_capabilities": sorted(CAPABILITIES - ceiling),
        "formal_authority": "none",
        "limitations": sorted(set([*limitations, _ROLE_LIMITATION])),
    }
    result = {**material, "binding_digest": _digest(material)}
    validate_role_binding(result)
    return result


def validate_role_binding(binding: Mapping[str, Any]) -> dict[str, Any]:
    _schema_validate(binding, "roleBinding", "assurance role binding")
    role = str(binding["role_surface"])
    ceiling = set(role_capability_ceiling(role))
    if set(binding["capability_ceiling"]) != ceiling:
        raise AssuranceRoleError("role capability ceiling differs from policy")
    if set(binding["prohibited_capabilities"]) != CAPABILITIES - ceiling:
        raise AssuranceRoleError("prohibited capabilities differ from policy")
    granted = set(str(item) for item in binding["granted_capabilities"])
    if not granted <= ceiling:
        raise AssuranceRoleError("granted capabilities exceed the role ceiling")
    if granted and binding["authority_ref"] is None:
        raise AssuranceRoleError("effective capability claim lacks authority reference")
    if binding["formal_authority"] != "none":
        raise AssuranceRoleError("candidate role binding cannot hold formal authority")
    expected = _digest(_without(binding, "binding_digest"))
    if binding["binding_digest"] != expected:
        raise AssuranceRoleError("assurance role binding digest mismatch")
    return copy.deepcopy(dict(binding))


def _identity_verification_context(
    *,
    reviewer_ref: Mapping[str, Any],
    reviewer_kind: str,
    subject_executor_ref: Mapping[str, Any],
    reviewer_implementation_ref: Mapping[str, Any],
    subject_implementation_ref: Mapping[str, Any],
    reviewer_runtime_ref: Mapping[str, Any],
    subject_runtime_ref: Mapping[str, Any],
    target_ref: Mapping[str, Any],
    identity_resolution_state: str,
    identity_resolver_ref: Mapping[str, Any] | None,
    independence_evidence_refs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "reviewer_ref": copy.deepcopy(dict(reviewer_ref)),
        "reviewer_kind": reviewer_kind,
        "subject_executor_ref": copy.deepcopy(dict(subject_executor_ref)),
        "reviewer_implementation_ref": copy.deepcopy(dict(reviewer_implementation_ref)),
        "subject_implementation_ref": copy.deepcopy(dict(subject_implementation_ref)),
        "reviewer_runtime_ref": copy.deepcopy(dict(reviewer_runtime_ref)),
        "subject_runtime_ref": copy.deepcopy(dict(subject_runtime_ref)),
        "target_ref": copy.deepcopy(dict(target_ref)),
        "identity_resolution_state": identity_resolution_state,
        "identity_resolver_ref": (
            copy.deepcopy(dict(identity_resolver_ref))
            if identity_resolver_ref is not None
            else None
        ),
        "independence_evidence_refs": sorted(
            (copy.deepcopy(dict(item)) for item in independence_evidence_refs),
            key=lambda item: (
                item["record_id"],
                item["locator"],
                item["content_digest"]["value"],
            ),
        ),
    }


def _evaluate_identity_verifier_claim(
    context: Mapping[str, Any],
    trusted_identity_verifier: IdentityVerifier | None,
) -> tuple[str, dict[str, Any] | None]:
    eligible = bool(
        context["reviewer_kind"] == "human"
        and context["identity_resolution_state"] == "resolved"
        and context["identity_resolver_ref"] is not None
        and context["independence_evidence_refs"]
    )
    if not eligible:
        return "not_eligible", None
    if trusted_identity_verifier is None:
        return "not_supplied", None
    verifier_ref = getattr(trusted_identity_verifier, "verifier_ref", None)
    if not isinstance(verifier_ref, Mapping):
        return "verifier_ref_invalid", None
    try:
        _schema_validate(verifier_ref, "recordRef", "trusted identity verifier")
    except AssuranceRoleError:
        return "verifier_ref_invalid", None
    copied_ref = copy.deepcopy(dict(verifier_ref))
    try:
        verified = bool(trusted_identity_verifier(copy.deepcopy(dict(context))))
    except Exception:
        return "verifier_unavailable", copied_ref
    if not verified:
        return "verifier_claim_rejected", copied_ref
    return "verifier_claim_accepted", copied_ref


def _derive_review_independence(
    *,
    reviewer_ref: Mapping[str, Any],
    subject_executor_ref: Mapping[str, Any],
    reviewer_runtime_ref: Mapping[str, Any],
    subject_runtime_ref: Mapping[str, Any],
) -> str:
    if _identity_key(reviewer_ref) == _identity_key(subject_executor_ref):
        return "self_review"
    if _identity_key(reviewer_runtime_ref) != _identity_key(subject_runtime_ref):
        return "separate_runtime_review"
    return "isolated_context_review"


def build_review_record(
    *,
    review_id: str,
    reviewer_ref: Mapping[str, Any],
    reviewer_kind: str,
    subject_executor_ref: Mapping[str, Any],
    reviewer_implementation_ref: Mapping[str, Any],
    subject_implementation_ref: Mapping[str, Any],
    reviewer_runtime_ref: Mapping[str, Any],
    subject_runtime_ref: Mapping[str, Any],
    target_ref: Mapping[str, Any],
    identity_resolution_state: str = "unresolved",
    identity_resolver_ref: Mapping[str, Any] | None = None,
    independence_evidence_refs: Sequence[Mapping[str, Any]] = (),
    limitations: Sequence[str] = (),
    trusted_identity_verifier: IdentityVerifier | None = None,
) -> dict[str, Any]:
    """Classify review independence from explicit context; never accept a label."""

    context = _identity_verification_context(
        reviewer_ref=reviewer_ref,
        reviewer_kind=reviewer_kind,
        subject_executor_ref=subject_executor_ref,
        reviewer_implementation_ref=reviewer_implementation_ref,
        subject_implementation_ref=subject_implementation_ref,
        reviewer_runtime_ref=reviewer_runtime_ref,
        subject_runtime_ref=subject_runtime_ref,
        target_ref=target_ref,
        identity_resolution_state=identity_resolution_state,
        identity_resolver_ref=identity_resolver_ref,
        independence_evidence_refs=independence_evidence_refs,
    )
    identity_verifier_claim, identity_verifier_ref = _evaluate_identity_verifier_claim(
        context, trusted_identity_verifier
    )
    independence = _derive_review_independence(
        reviewer_ref=reviewer_ref,
        subject_executor_ref=subject_executor_ref,
        reviewer_runtime_ref=reviewer_runtime_ref,
        subject_runtime_ref=subject_runtime_ref,
    )
    effective_limitations = [
        *limitations,
        _REVIEW_LIMITATION,
        _IDENTITY_LIMITATION,
        _TRUST_ROOT_LIMITATION,
    ]
    material: dict[str, Any] = {
        "schema_version": REVIEW_VERSION,
        "review_id": review_id,
        "reviewer_ref": copy.deepcopy(dict(reviewer_ref)),
        "reviewer_kind": reviewer_kind,
        "subject_executor_ref": copy.deepcopy(dict(subject_executor_ref)),
        "reviewer_implementation_ref": copy.deepcopy(dict(reviewer_implementation_ref)),
        "subject_implementation_ref": copy.deepcopy(dict(subject_implementation_ref)),
        "reviewer_runtime_ref": copy.deepcopy(dict(reviewer_runtime_ref)),
        "subject_runtime_ref": copy.deepcopy(dict(subject_runtime_ref)),
        "target_ref": copy.deepcopy(dict(target_ref)),
        "identity_resolution_state": identity_resolution_state,
        "identity_resolver_ref": context["identity_resolver_ref"],
        "identity_trust_state": "unresolved",
        "identity_verifier_claim": identity_verifier_claim,
        "identity_verifier_ref": identity_verifier_ref,
        "identity_verification_input_digest": _digest(context),
        "trust_root_resolution_state": "not_integrated",
        "trust_root_ref": None,
        "independence_evidence_refs": context["independence_evidence_refs"],
        "review_independence": independence,
        "finding_authority": "candidate_only",
        "formal_adoption_authority": "none",
        "limitations": sorted(set(effective_limitations)),
    }
    result = {**material, "review_digest": _digest(material)}
    validate_review_record(result, trusted_identity_verifier=trusted_identity_verifier)
    return result


def validate_review_record(
    review: Mapping[str, Any],
    *,
    trusted_identity_verifier: IdentityVerifier | None = None,
) -> dict[str, Any]:
    _schema_validate(review, "reviewRecord", "assurance review")
    context = _identity_verification_context(
        reviewer_ref=review["reviewer_ref"],
        reviewer_kind=str(review["reviewer_kind"]),
        subject_executor_ref=review["subject_executor_ref"],
        reviewer_implementation_ref=review["reviewer_implementation_ref"],
        subject_implementation_ref=review["subject_implementation_ref"],
        reviewer_runtime_ref=review["reviewer_runtime_ref"],
        subject_runtime_ref=review["subject_runtime_ref"],
        target_ref=review["target_ref"],
        identity_resolution_state=str(review["identity_resolution_state"]),
        identity_resolver_ref=review["identity_resolver_ref"],
        independence_evidence_refs=list(review["independence_evidence_refs"]),
    )
    identity_verifier_claim, identity_verifier_ref = _evaluate_identity_verifier_claim(
        context, trusted_identity_verifier
    )
    if review["identity_verification_input_digest"] != _digest(context):
        raise AssuranceRoleError(
            "identity verification input digest does not replay from review context"
        )
    if review["identity_trust_state"] != "unresolved":
        raise AssuranceRoleError(
            "supplied verifier callback cannot resolve identity trust"
        )
    if review["identity_verifier_claim"] != identity_verifier_claim:
        raise AssuranceRoleError("identity verifier claim does not replay")
    if review["identity_verifier_ref"] != identity_verifier_ref:
        raise AssuranceRoleError(
            "identity verifier reference does not match the injected verifier"
        )
    derived = _derive_review_independence(
        reviewer_ref=review["reviewer_ref"],
        subject_executor_ref=review["subject_executor_ref"],
        reviewer_runtime_ref=review["reviewer_runtime_ref"],
        subject_runtime_ref=review["subject_runtime_ref"],
    )
    if review["review_independence"] != derived:
        raise AssuranceRoleError(
            "review independence label does not replay from its context"
        )
    if review["review_independence"] == "independent_human_review":
        raise AssuranceRoleError(
            "independent human review requires a future control-plane trust-root contract"
        )
    if (
        review["trust_root_resolution_state"] != "not_integrated"
        or review["trust_root_ref"] is not None
    ):
        raise AssuranceRoleError(
            "review cannot self-establish a control-plane or signature trust root"
        )
    if _REVIEW_LIMITATION not in review["limitations"]:
        raise AssuranceRoleError("review authority limitation is missing")
    if _IDENTITY_LIMITATION not in review["limitations"]:
        raise AssuranceRoleError("unverified identity limitation is missing")
    if _TRUST_ROOT_LIMITATION not in review["limitations"]:
        raise AssuranceRoleError("future trust-root integration limitation is missing")
    if review["finding_authority"] != "candidate_only":
        raise AssuranceRoleError("review findings cannot hold formal verdict authority")
    if review["formal_adoption_authority"] != "none":
        raise AssuranceRoleError("review cannot adopt its own result")
    expected = _digest(_without(review, "review_digest"))
    if review["review_digest"] != expected:
        raise AssuranceRoleError("assurance review digest mismatch")
    return copy.deepcopy(dict(review))


__all__ = [
    "AssuranceRoleError",
    "CAPABILITIES",
    "IdentityVerifier",
    "ROLE_CAPABILITY_CEILINGS",
    "assurance_role_schema",
    "build_review_record",
    "build_role_binding",
    "role_capability_ceiling",
    "validate_review_record",
    "validate_role_binding",
]
