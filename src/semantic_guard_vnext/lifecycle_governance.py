"""Candidate-only lifecycle governance records and exact runtime resolution.

This module is a sidecar for the H2/D1-D3 revision principles.  It describes
profiles, tailoring, and resolution evidence.  It deliberately cannot adopt a
profile, operate a control plane, or grant lifecycle satisfaction.
"""

from __future__ import annotations

import copy
from functools import lru_cache
import hashlib
import json
from typing import Any, Callable, Iterable, Mapping, Sequence

from jsonschema import Draft202012Validator, FormatChecker

from .schema_access import schema_path


CORE_STAGES = (
    "request",
    "exploration",
    "requirement",
    "decision",
    "plan",
    "action",
    "realization",
    "diff",
    "verification",
    "completion",
)

STAGE_PROFILE_VERSION = "lifecycle-stage-profile/v1"
STAGE_REGISTRY_VERSION = "lifecycle-stage-registry/v1"
TAILORING_VERSION = "lifecycle-tailoring/v1"
RUNTIME_RULE_BINDING_VERSION = "lifecycle-runtime-rule-binding/v1"
RUNTIME_RESOLUTION_VERSION = "lifecycle-runtime-resolution/v1"

AUTHORITY_BOUNDARY = {
    "finding_authority": "candidate_only",
    "routing_authority": "may_escalate_unresolved",
    "nonconformance_authority": "prohibited",
    "satisfaction_authority": "prohibited",
    "final_verdict_authority": "prohibited",
    "direct_command_authority": "prohibited",
}

_SCHEMA_PATH = schema_path("lifecycle-governance-v1.schema.json")
_LIMITATION = (
    "This lifecycle resolution is candidate audit material and has no formal "
    "satisfaction, command, waiver, adoption, or final-verdict authority."
)
_TRUST_ROOT_LIMITATION = (
    "A supplied decision-verifier callback and verifier_ref are not a "
    "control-plane trust registry or signature trust root; reported adoption, "
    "non-applicability, and waiver remain unresolved."
)


class LifecycleGovernanceError(ValueError):
    """Raised when lifecycle governance input cannot be proven exact."""


DecisionVerifier = Callable[[Mapping[str, Any]], bool]


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
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


def _copy(value: Mapping[str, Any]) -> dict[str, Any]:
    return copy.deepcopy(dict(value))


def _record_key(value: Mapping[str, Any]) -> tuple[str, str, str]:
    return (
        str(value["record_id"]),
        str(value["locator"]),
        str(value["content_digest"]["value"]),
    )


def _profile_key(value: Mapping[str, Any]) -> tuple[str, str]:
    return str(value["profile_id"]), str(value["profile_version"])


@lru_cache(maxsize=1)
def lifecycle_governance_schema() -> dict[str, Any]:
    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return schema


@lru_cache(maxsize=None)
def _validator(definition: str) -> Draft202012Validator:
    root = lifecycle_governance_schema()
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
        raise LifecycleGovernanceError(
            f"{contract} schema violation at {location}: {issue.message}"
        )


def _validate_digest(record: Mapping[str, Any], field: str, contract: str) -> None:
    if record[field] != _digest(_without(record, field)):
        raise LifecycleGovernanceError(f"{contract} {field} mismatch")


def _decision_binding_matches(
    decision: Mapping[str, Any] | None,
    *,
    kind: str,
    target_id: str,
    target_version: str,
    basis_digest: Mapping[str, Any],
    accepted_statuses: frozenset[str] = frozenset({"accept"}),
) -> bool:
    return bool(
        decision is not None
        and decision.get("decision_kind") == kind
        and decision.get("status") in accepted_statuses
        and decision.get("target_id") == target_id
        and decision.get("target_version") == target_version
        and decision.get("target_basis_digest") == basis_digest
        and decision.get("entry_resolution_state") == "resolved"
    )


def _decision_matches(
    decision: Mapping[str, Any] | None,
    *,
    kind: str,
    target_id: str,
    target_version: str,
    basis_digest: Mapping[str, Any],
    trusted_decision_verifier: DecisionVerifier | None,
    accepted_statuses: frozenset[str] = frozenset({"accept"}),
) -> bool:
    """Never promote a supplied callback to an external trust-root decision."""

    del (
        decision,
        kind,
        target_id,
        target_version,
        basis_digest,
        trusted_decision_verifier,
        accepted_statuses,
    )
    return False


def _decision_verifier_claim(
    trusted_decision_verifier: DecisionVerifier | None,
) -> tuple[str, dict[str, Any] | None]:
    """Describe the supplied callback without executing or trusting it."""

    if trusted_decision_verifier is None:
        return "not_supplied", None
    verifier_ref = getattr(trusted_decision_verifier, "verifier_ref", None)
    if not isinstance(verifier_ref, Mapping):
        return "verifier_ref_invalid", None
    try:
        _schema_validate(verifier_ref, "recordRef", "decision verifier claim")
    except LifecycleGovernanceError:
        return "verifier_ref_invalid", None
    return "callback_supplied_not_trust_root", _copy(verifier_ref)


def _validate_adoption(
    *,
    adoption_status: str,
    decision: Mapping[str, Any] | None,
    kind: str,
    target_id: str,
    target_version: str,
    basis_digest: Mapping[str, Any],
    trusted_decision_verifier: DecisionVerifier | None,
    require_trusted_decisions: bool,
) -> None:
    del trusted_decision_verifier, require_trusted_decisions
    if adoption_status == "adopted":
        if not _decision_binding_matches(
            decision,
            kind=kind,
            target_id=target_id,
            target_version=target_version,
            basis_digest=basis_digest,
        ):
            raise LifecycleGovernanceError(
                f"adopted {target_id} lacks an exact resolved human adoption record"
            )
    elif decision is not None:
        raise LifecycleGovernanceError(
            f"non-adopted {target_id} cannot carry a human adoption reference"
        )


def profile_ref(
    profile: Mapping[str, Any],
    *,
    trusted_decision_verifier: DecisionVerifier | None = None,
    require_trusted_decisions: bool = True,
) -> dict[str, Any]:
    validate_stage_profile(
        profile,
        trusted_decision_verifier=trusted_decision_verifier,
        require_trusted_decisions=require_trusted_decisions,
    )
    return {
        "profile_id": profile["profile_id"],
        "profile_version": profile["profile_version"],
        "stage_id": profile["stage_id"],
        "content_digest": copy.deepcopy(profile["content_digest"]),
        "basis_digest": copy.deepcopy(profile["basis_digest"]),
        "artifact_digest": copy.deepcopy(profile["artifact_digest"]),
        "implementation_digest": copy.deepcopy(profile["implementation_digest"]),
    }


def _stage_profile_ref(
    stage_id: str,
    profile: Mapping[str, Any],
    *,
    trusted_decision_verifier: DecisionVerifier | None,
) -> dict[str, Any]:
    return {
        "stage_id": stage_id,
        "profile_ref": profile_ref(
            profile, trusted_decision_verifier=trusted_decision_verifier
        ),
    }


def registry_record_ref(
    registry: Mapping[str, Any],
    *,
    locator: str | None = None,
    trusted_decision_verifier: DecisionVerifier | None = None,
    require_trusted_decisions: bool = True,
) -> dict[str, Any]:
    validate_stage_registry(
        registry,
        trusted_decision_verifier=trusted_decision_verifier,
        require_trusted_decisions=require_trusted_decisions,
    )
    return {
        "record_id": registry["registry_id"],
        "locator": locator or f"urn:lifecycle-registry:{registry['registry_id']}",
        "content_digest": copy.deepcopy(registry["artifact_digest"]),
    }


def tailoring_record_ref(
    tailoring: Mapping[str, Any],
    *,
    locator: str | None = None,
    trusted_decision_verifier: DecisionVerifier | None = None,
    require_trusted_decisions: bool = True,
) -> dict[str, Any]:
    validate_tailoring(
        tailoring,
        trusted_decision_verifier=trusted_decision_verifier,
        require_trusted_decisions=require_trusted_decisions,
    )
    return {
        "record_id": tailoring["tailoring_id"],
        "locator": locator or f"urn:lifecycle-tailoring:{tailoring['tailoring_id']}",
        "content_digest": copy.deepcopy(tailoring["artifact_digest"]),
    }


def build_stage_profile(
    *,
    profile_id: str,
    profile_version: str,
    stage_id: str,
    purpose: str,
    entry_conditions: Sequence[str],
    exit_conditions: Sequence[str],
    applicability_policy: str,
    input_manifest_contract: Mapping[str, Any],
    output_manifest_contract: Mapping[str, Any],
    obligations: Sequence[str],
    engineering_basis_refs: Sequence[Mapping[str, Any]],
    validation_obligations: Sequence[str],
    requalification_triggers: Sequence[str],
    implementation_digest: Mapping[str, Any],
    reported_adoption_status: str = "candidate",
    human_adoption_ref: Mapping[str, Any] | None = None,
    trusted_decision_verifier: DecisionVerifier | None = None,
) -> dict[str, Any]:
    """Build one independently adoptable lifecycle stage profile."""

    content_material = {
        "schema_version": STAGE_PROFILE_VERSION,
        "profile_id": profile_id,
        "profile_version": profile_version,
        "stage_id": stage_id,
        "purpose": purpose,
        "entry_conditions": sorted(set(entry_conditions)),
        "exit_conditions": sorted(set(exit_conditions)),
        "applicability_policy": applicability_policy,
        "input_manifest_contract": _copy(input_manifest_contract),
        "output_manifest_contract": _copy(output_manifest_contract),
        "obligations": sorted(set(obligations)),
        "validation_obligations": sorted(set(validation_obligations)),
        "requalification_triggers": sorted(set(requalification_triggers)),
    }
    content_digest = _digest(content_material)
    basis_material = {
        "content_digest": content_digest,
        "engineering_basis_refs": sorted(
            (_copy(item) for item in engineering_basis_refs),
            key=lambda item: (item["rule_id"], item["rule_version"]),
        ),
        "authority_boundary": copy.deepcopy(AUTHORITY_BOUNDARY),
        "requalification_triggers": content_material["requalification_triggers"],
    }
    basis_digest = _digest(basis_material)
    material = {
        **content_material,
        "engineering_basis_refs": basis_material["engineering_basis_refs"],
        "authority_boundary": copy.deepcopy(AUTHORITY_BOUNDARY),
        "reported_adoption_status": reported_adoption_status,
        "human_adoption_ref": (
            _copy(human_adoption_ref) if human_adoption_ref is not None else None
        ),
        "implementation_digest": _copy(implementation_digest),
        "content_digest": content_digest,
        "basis_digest": basis_digest,
    }
    result = {**material, "artifact_digest": _digest(material)}
    validate_stage_profile(result, trusted_decision_verifier=trusted_decision_verifier)
    return result


def validate_stage_profile(
    profile: Mapping[str, Any],
    *,
    trusted_decision_verifier: DecisionVerifier | None = None,
    require_trusted_decisions: bool = True,
) -> dict[str, Any]:
    _schema_validate(profile, "stageProfile", "lifecycle stage profile")
    content_material = {
        key: copy.deepcopy(profile[key])
        for key in (
            "schema_version",
            "profile_id",
            "profile_version",
            "stage_id",
            "purpose",
            "entry_conditions",
            "exit_conditions",
            "applicability_policy",
            "input_manifest_contract",
            "output_manifest_contract",
            "obligations",
            "validation_obligations",
            "requalification_triggers",
        )
    }
    if profile["content_digest"] != _digest(content_material):
        raise LifecycleGovernanceError("stage profile content digest mismatch")
    basis_material = {
        "content_digest": copy.deepcopy(profile["content_digest"]),
        "engineering_basis_refs": copy.deepcopy(profile["engineering_basis_refs"]),
        "authority_boundary": copy.deepcopy(profile["authority_boundary"]),
        "requalification_triggers": copy.deepcopy(profile["requalification_triggers"]),
    }
    if profile["basis_digest"] != _digest(basis_material):
        raise LifecycleGovernanceError("stage profile basis digest mismatch")
    if profile["authority_boundary"] != AUTHORITY_BOUNDARY:
        raise LifecycleGovernanceError(
            "stage profile authority exceeds candidate-only policy"
        )
    keys = [
        (str(item["rule_id"]), str(item["rule_version"]))
        for item in profile["engineering_basis_refs"]
    ]
    if len(keys) != len(set(keys)):
        raise LifecycleGovernanceError("stage profile repeats an engineering rule")
    for requirement in profile["engineering_basis_refs"]:
        decision = requirement["human_adoption_ref"]
        if requirement["reported_adoption_status"] == "adopted":
            if not _decision_binding_matches(
                decision,
                kind="adopt_engineering_rule",
                target_id=requirement["rule_id"],
                target_version=requirement["rule_version"],
                basis_digest=requirement["basis_digest"],
            ):
                raise LifecycleGovernanceError(
                    f"engineering rule {requirement['rule_id']} lacks exact adoption"
                )
        elif decision is not None:
            raise LifecycleGovernanceError(
                f"non-adopted engineering rule {requirement['rule_id']} carries adoption"
            )
    _validate_adoption(
        adoption_status=str(profile["reported_adoption_status"]),
        decision=profile["human_adoption_ref"],
        kind="adopt_stage_profile",
        target_id=str(profile["profile_id"]),
        target_version=str(profile["profile_version"]),
        basis_digest=profile["basis_digest"],
        trusted_decision_verifier=trusted_decision_verifier,
        require_trusted_decisions=require_trusted_decisions,
    )
    _validate_digest(profile, "artifact_digest", "stage profile")
    return _copy(profile)


def build_stage_registry(
    *,
    registry_id: str,
    registry_version: str,
    core_profiles: Mapping[str, Mapping[str, Any]],
    extension_profiles: Sequence[Mapping[str, Any]] = (),
    reported_adoption_status: str = "candidate",
    human_adoption_ref: Mapping[str, Any] | None = None,
    trusted_decision_verifier: DecisionVerifier | None = None,
) -> dict[str, Any]:
    if set(core_profiles) != set(CORE_STAGES):
        missing = sorted(set(CORE_STAGES) - set(core_profiles))
        extra = sorted(set(core_profiles) - set(CORE_STAGES))
        raise LifecycleGovernanceError(
            f"registry core denominator mismatch; missing={missing!r}, extra={extra!r}"
        )
    core_refs = [
        _stage_profile_ref(
            stage,
            core_profiles[stage],
            trusted_decision_verifier=trusted_decision_verifier,
        )
        for stage in CORE_STAGES
    ]
    extension_refs = sorted(
        (
            _stage_profile_ref(
                str(profile["stage_id"]),
                profile,
                trusted_decision_verifier=trusted_decision_verifier,
            )
            for profile in extension_profiles
        ),
        key=lambda item: item["stage_id"],
    )
    material_without_digests = {
        "schema_version": STAGE_REGISTRY_VERSION,
        "registry_id": registry_id,
        "registry_version": registry_version,
        "core_stage_order": list(CORE_STAGES),
        "core_profile_refs": core_refs,
        "extension_profile_refs": extension_refs,
        "reported_adoption_status": reported_adoption_status,
        "human_adoption_ref": (
            _copy(human_adoption_ref) if human_adoption_ref is not None else None
        ),
        "authority_boundary": copy.deepcopy(AUTHORITY_BOUNDARY),
    }
    basis_digest = _digest(
        _without(
            material_without_digests,
            "reported_adoption_status",
            "human_adoption_ref",
        )
    )
    material = {**material_without_digests, "basis_digest": basis_digest}
    result = {**material, "artifact_digest": _digest(material)}
    validate_stage_registry(result, trusted_decision_verifier=trusted_decision_verifier)
    return result


def validate_stage_registry(
    registry: Mapping[str, Any],
    *,
    trusted_decision_verifier: DecisionVerifier | None = None,
    require_trusted_decisions: bool = True,
) -> dict[str, Any]:
    _schema_validate(registry, "stageRegistry", "lifecycle stage registry")
    if tuple(registry["core_stage_order"]) != CORE_STAGES:
        raise LifecycleGovernanceError(
            "registry core stage order is not core lifecycle v1"
        )
    core_ids = [str(item["stage_id"]) for item in registry["core_profile_refs"]]
    if tuple(core_ids) != CORE_STAGES or len(set(core_ids)) != len(CORE_STAGES):
        raise LifecycleGovernanceError(
            "registry must bind each core stage exactly once"
        )
    if any(
        item["stage_id"] != item["profile_ref"]["stage_id"]
        for item in registry["core_profile_refs"]
    ):
        raise LifecycleGovernanceError(
            "registry stage and profile stage bindings differ"
        )
    extension_ids = [
        str(item["stage_id"]) for item in registry["extension_profile_refs"]
    ]
    if set(extension_ids) & set(CORE_STAGES) or len(extension_ids) != len(
        set(extension_ids)
    ):
        raise LifecycleGovernanceError(
            "extension profiles collide with the core denominator"
        )
    if any(
        item["stage_id"] != item["profile_ref"]["stage_id"]
        for item in registry["extension_profile_refs"]
    ):
        raise LifecycleGovernanceError(
            "extension stage and profile stage bindings differ"
        )
    all_profile_keys = [
        (
            str(item["profile_ref"]["profile_id"]),
            str(item["profile_ref"]["profile_version"]),
        )
        for item in [
            *registry["core_profile_refs"],
            *registry["extension_profile_refs"],
        ]
    ]
    if len(all_profile_keys) != len(set(all_profile_keys)):
        raise LifecycleGovernanceError(
            "registry cannot bind one profile identity to multiple stages"
        )
    if registry["authority_boundary"] != AUTHORITY_BOUNDARY:
        raise LifecycleGovernanceError(
            "registry authority exceeds candidate-only policy"
        )
    basis_material = _without(
        registry,
        "reported_adoption_status",
        "human_adoption_ref",
        "basis_digest",
        "artifact_digest",
    )
    if registry["basis_digest"] != _digest(basis_material):
        raise LifecycleGovernanceError("stage registry basis digest mismatch")
    _validate_adoption(
        adoption_status=str(registry["reported_adoption_status"]),
        decision=registry["human_adoption_ref"],
        kind="adopt_stage_registry",
        target_id=str(registry["registry_id"]),
        target_version=str(registry["registry_version"]),
        basis_digest=registry["basis_digest"],
        trusted_decision_verifier=trusted_decision_verifier,
        require_trusted_decisions=require_trusted_decisions,
    )
    _validate_digest(registry, "artifact_digest", "stage registry")
    return _copy(registry)


def build_applicability_record(
    *,
    stage_id: str,
    reported_applicability_state: str,
    activation_conditions: Sequence[str] = (),
    non_activation_conditions: Sequence[str] = (),
    decision_evidence_refs: Sequence[Mapping[str, Any]] = (),
    denominator_ref: Mapping[str, Any] | None = None,
    rationale: str | None = None,
    decision_owner_ref: Mapping[str, Any] | None = None,
    authority_ref: Mapping[str, Any] | None = None,
    decision_record_ref: Mapping[str, Any] | None = None,
    reactivation_triggers: Sequence[str] = (),
    review_at: str | None = None,
    reported_human_disposition: str = "none",
    human_disposition_ref: Mapping[str, Any] | None = None,
    unresolved_ref: Mapping[str, Any] | None = None,
    trusted_decision_verifier: DecisionVerifier | None = None,
) -> dict[str, Any]:
    result = {
        "stage_id": stage_id,
        "reported_applicability_state": reported_applicability_state,
        "activation_conditions": sorted(set(activation_conditions)),
        "non_activation_conditions": sorted(set(non_activation_conditions)),
        "decision_evidence_refs": sorted(
            (_copy(item) for item in decision_evidence_refs), key=_record_key
        ),
        "denominator_ref": _copy(denominator_ref) if denominator_ref else None,
        "rationale": rationale,
        "decision_owner_ref": _copy(decision_owner_ref) if decision_owner_ref else None,
        "authority_ref": _copy(authority_ref) if authority_ref else None,
        "decision_record_ref": _copy(decision_record_ref)
        if decision_record_ref
        else None,
        "reactivation_triggers": sorted(set(reactivation_triggers)),
        "review_at": review_at,
        "reported_human_disposition": reported_human_disposition,
        "human_disposition_ref": (
            _copy(human_disposition_ref) if human_disposition_ref else None
        ),
        "unresolved_ref": _copy(unresolved_ref) if unresolved_ref else None,
    }
    _validate_applicability(result, trusted_decision_verifier=trusted_decision_verifier)
    return result


def _validate_applicability(
    record: Mapping[str, Any],
    *,
    trusted_decision_verifier: DecisionVerifier | None,
    require_trusted_decisions: bool = True,
) -> None:
    del trusted_decision_verifier, require_trusted_decisions
    _schema_validate(record, "applicabilityRecord", "stage applicability")
    state = record["reported_applicability_state"]
    stage = str(record["stage_id"])
    if state == "conditional" and (
        not record["activation_conditions"]
        or not record["non_activation_conditions"]
        or not record["decision_evidence_refs"]
    ):
        raise LifecycleGovernanceError(
            f"conditional stage {stage} lacks activation, non-activation, or evidence"
        )
    if state == "not_applicable":
        required = (
            record["denominator_ref"],
            record["rationale"],
            record["decision_owner_ref"],
            record["authority_ref"],
            record["decision_record_ref"],
            record["reactivation_triggers"],
            record["review_at"],
            record["decision_evidence_refs"],
        )
        if not all(required):
            raise LifecycleGovernanceError(
                f"not-applicable stage {stage} lacks its complete decision basis"
            )
        decision = record["decision_record_ref"]
        if not _decision_binding_matches(
            decision,
            kind="stage_not_applicable",
            target_id=stage,
            target_version="1",
            basis_digest=record["denominator_ref"]["content_digest"],
        ):
            raise LifecycleGovernanceError(
                f"not-applicable stage {stage} lacks an exact resolved human decision"
            )
    elif record["decision_record_ref"] is not None:
        raise LifecycleGovernanceError(
            "stage applicability decision reference is reserved for not_applicable"
        )
    if state == "unresolved" and record["unresolved_ref"] is None:
        raise LifecycleGovernanceError(f"unresolved stage {stage} lacks unresolved_ref")
    if state != "unresolved" and record["unresolved_ref"] is not None:
        raise LifecycleGovernanceError(
            "resolved applicability cannot retain unresolved_ref"
        )
    if record["reported_human_disposition"] == "waived":
        decision = record["human_disposition_ref"]
        basis = record["denominator_ref"]
        if basis is None or not _decision_binding_matches(
            decision,
            kind="waive_stage",
            target_id=stage,
            target_version="1",
            basis_digest=basis["content_digest"],
            accepted_statuses=frozenset({"waive"}),
        ):
            raise LifecycleGovernanceError(
                f"waived stage {stage} lacks an exact resolved human waiver"
            )
        if state == "not_applicable":
            raise LifecycleGovernanceError("waiver and non-applicability are distinct")
    elif record["human_disposition_ref"] is not None:
        raise LifecycleGovernanceError(
            "non-waived stage cannot carry a waiver reference"
        )


def build_extension_applicability_record(
    *,
    profile: Mapping[str, Any],
    applicability: Mapping[str, Any],
    trusted_decision_verifier: DecisionVerifier | None = None,
) -> dict[str, Any]:
    result = {
        "stage_id": profile["stage_id"],
        "profile_ref": profile_ref(
            profile, trusted_decision_verifier=trusted_decision_verifier
        ),
        "applicability": _copy(applicability),
    }
    _validate_extension_applicability(
        result, trusted_decision_verifier=trusted_decision_verifier
    )
    return result


def _validate_extension_applicability(
    record: Mapping[str, Any],
    *,
    trusted_decision_verifier: DecisionVerifier | None,
    require_trusted_decisions: bool = True,
) -> None:
    _schema_validate(
        record, "extensionApplicabilityRecord", "extension stage applicability"
    )
    stage = str(record["stage_id"])
    if stage in CORE_STAGES:
        raise LifecycleGovernanceError(
            "extension applicability cannot redefine a core stage"
        )
    if (
        record["profile_ref"]["stage_id"] != stage
        or record["applicability"]["stage_id"] != stage
    ):
        raise LifecycleGovernanceError(
            "extension profile and applicability stage identities differ"
        )
    _validate_applicability(
        record["applicability"],
        trusted_decision_verifier=trusted_decision_verifier,
        require_trusted_decisions=require_trusted_decisions,
    )


def build_tailoring(
    *,
    tailoring_id: str,
    tailoring_version: str,
    subject_scope_ref: Mapping[str, Any],
    risk_class: str,
    core_stage_applicability: Sequence[Mapping[str, Any]],
    basis_refs: Sequence[Mapping[str, Any]],
    decision_owner_ref: Mapping[str, Any],
    reactivation_triggers: Sequence[str],
    extension_stage_applicability: Sequence[Mapping[str, Any]] = (),
    reported_adoption_status: str = "candidate",
    human_adoption_ref: Mapping[str, Any] | None = None,
    trusted_decision_verifier: DecisionVerifier | None = None,
) -> dict[str, Any]:
    material_without_digests = {
        "schema_version": TAILORING_VERSION,
        "tailoring_id": tailoring_id,
        "tailoring_version": tailoring_version,
        "subject_scope_ref": _copy(subject_scope_ref),
        "risk_class": risk_class,
        "core_stage_applicability": [_copy(item) for item in core_stage_applicability],
        "extension_stage_applicability": sorted(
            (_copy(item) for item in extension_stage_applicability),
            key=lambda x: x["stage_id"],
        ),
        "basis_refs": sorted((_copy(item) for item in basis_refs), key=_record_key),
        "decision_owner_ref": _copy(decision_owner_ref),
        "reactivation_triggers": sorted(set(reactivation_triggers)),
        "reported_adoption_status": reported_adoption_status,
        "human_adoption_ref": (
            _copy(human_adoption_ref) if human_adoption_ref is not None else None
        ),
    }
    basis_digest = _digest(
        _without(
            material_without_digests,
            "reported_adoption_status",
            "human_adoption_ref",
        )
    )
    material = {**material_without_digests, "basis_digest": basis_digest}
    result = {**material, "artifact_digest": _digest(material)}
    validate_tailoring(result, trusted_decision_verifier=trusted_decision_verifier)
    return result


def validate_tailoring(
    tailoring: Mapping[str, Any],
    *,
    trusted_decision_verifier: DecisionVerifier | None = None,
    require_trusted_decisions: bool = True,
) -> dict[str, Any]:
    _schema_validate(tailoring, "tailoring", "lifecycle tailoring")
    stages = [str(item["stage_id"]) for item in tailoring["core_stage_applicability"]]
    if tuple(stages) != CORE_STAGES or len(set(stages)) != len(CORE_STAGES):
        raise LifecycleGovernanceError(
            "tailoring must decide each core stage exactly once"
        )
    for item in tailoring["core_stage_applicability"]:
        _validate_applicability(
            item,
            trusted_decision_verifier=trusted_decision_verifier,
            require_trusted_decisions=require_trusted_decisions,
        )
    extension_stages = [
        str(item["stage_id"]) for item in tailoring["extension_stage_applicability"]
    ]
    if len(extension_stages) != len(set(extension_stages)):
        raise LifecycleGovernanceError(
            "tailoring repeats an extension stage applicability decision"
        )
    for item in tailoring["extension_stage_applicability"]:
        _validate_extension_applicability(
            item,
            trusted_decision_verifier=trusted_decision_verifier,
            require_trusted_decisions=require_trusted_decisions,
        )
    basis_material = _without(
        tailoring,
        "reported_adoption_status",
        "human_adoption_ref",
        "basis_digest",
        "artifact_digest",
    )
    if tailoring["basis_digest"] != _digest(basis_material):
        raise LifecycleGovernanceError("tailoring basis digest mismatch")
    _validate_adoption(
        adoption_status=str(tailoring["reported_adoption_status"]),
        decision=tailoring["human_adoption_ref"],
        kind="adopt_lifecycle_tailoring",
        target_id=str(tailoring["tailoring_id"]),
        target_version=str(tailoring["tailoring_version"]),
        basis_digest=tailoring["basis_digest"],
        trusted_decision_verifier=trusted_decision_verifier,
        require_trusted_decisions=require_trusted_decisions,
    )
    _validate_digest(tailoring, "artifact_digest", "tailoring")
    return _copy(tailoring)


def build_runtime_rule_binding(
    *,
    rule_id: str,
    rule_version: str,
    content_digest: Mapping[str, Any],
    basis_digest: Mapping[str, Any],
    implementation_digest: Mapping[str, Any],
    authority: Mapping[str, bool],
    reported_adoption_status: str = "candidate",
    human_adoption_ref: Mapping[str, Any] | None = None,
    trusted_decision_verifier: DecisionVerifier | None = None,
) -> dict[str, Any]:
    material = {
        "schema_version": RUNTIME_RULE_BINDING_VERSION,
        "rule_id": rule_id,
        "rule_version": rule_version,
        "content_digest": _copy(content_digest),
        "basis_digest": _copy(basis_digest),
        "implementation_digest": _copy(implementation_digest),
        "reported_adoption_status": reported_adoption_status,
        "human_adoption_ref": (
            _copy(human_adoption_ref) if human_adoption_ref is not None else None
        ),
        "authority": copy.deepcopy(dict(authority)),
    }
    result = {**material, "binding_digest": _digest(material)}
    validate_runtime_rule_binding(
        result, trusted_decision_verifier=trusted_decision_verifier
    )
    return result


def validate_runtime_rule_binding(
    binding: Mapping[str, Any],
    *,
    trusted_decision_verifier: DecisionVerifier | None = None,
    require_trusted_decisions: bool = True,
) -> dict[str, Any]:
    _schema_validate(binding, "runtimeRuleBinding", "runtime rule binding")
    _validate_adoption(
        adoption_status=str(binding["reported_adoption_status"]),
        decision=binding["human_adoption_ref"],
        kind="adopt_engineering_rule",
        target_id=str(binding["rule_id"]),
        target_version=str(binding["rule_version"]),
        basis_digest=binding["basis_digest"],
        trusted_decision_verifier=trusted_decision_verifier,
        require_trusted_decisions=require_trusted_decisions,
    )
    _validate_digest(binding, "binding_digest", "runtime rule binding")
    return _copy(binding)


def _resolution_item(kind: str, item_id: str, reasons: Iterable[str]) -> dict[str, Any]:
    unique = sorted(set(reasons))
    return {
        "item_kind": kind,
        "item_id": item_id,
        "state": "resolved" if not unique else "unresolved",
        "reasons": unique,
    }


def assess_candidate_lifecycle_runtime(
    *,
    registry: Mapping[str, Any],
    tailoring: Mapping[str, Any],
    subject_scope_ref: Mapping[str, Any],
    profiles: Sequence[Mapping[str, Any]],
    rule_bindings: Sequence[Mapping[str, Any]],
    trusted_decision_verifier: DecisionVerifier | None = None,
) -> dict[str, Any]:
    """Assess supplied lifecycle material under the v1 candidate-only ceiling."""

    validate_stage_registry(registry, require_trusted_decisions=False)
    validate_tailoring(tailoring, require_trusted_decisions=False)
    profile_map: dict[tuple[str, str], Mapping[str, Any]] = {}
    for profile in profiles:
        validate_stage_profile(profile, require_trusted_decisions=False)
        key = _profile_key(profile)
        if key in profile_map:
            raise LifecycleGovernanceError(f"duplicate runtime profile: {key!r}")
        profile_map[key] = profile
    rule_map: dict[tuple[str, str], Mapping[str, Any]] = {}
    for binding in rule_bindings:
        validate_runtime_rule_binding(binding, require_trusted_decisions=False)
        key = (str(binding["rule_id"]), str(binding["rule_version"]))
        if key in rule_map:
            raise LifecycleGovernanceError(f"duplicate runtime rule: {key!r}")
        rule_map[key] = binding
    supplied_rule_bindings = [
        {
            "rule_id": key[0],
            "rule_version": key[1],
            "binding_digest": copy.deepcopy(rule_map[key]["binding_digest"]),
        }
        for key in sorted(rule_map)
    ]
    required_rule_keys: set[tuple[str, str]] = set()

    decision_verifier_claim, decision_verifier_ref = _decision_verifier_claim(
        trusted_decision_verifier
    )
    items: list[dict[str, Any]] = [
        _resolution_item(
            "trust_root",
            "decision-trust-root",
            ["control_plane_trust_registry_not_integrated"],
        )
    ]
    registry_reasons: list[str] = []
    if registry["reported_adoption_status"] != "adopted":
        registry_reasons.append("registry_not_adopted")
    elif not _decision_matches(
        registry["human_adoption_ref"],
        kind="adopt_stage_registry",
        target_id=str(registry["registry_id"]),
        target_version=str(registry["registry_version"]),
        basis_digest=registry["basis_digest"],
        trusted_decision_verifier=trusted_decision_verifier,
    ):
        registry_reasons.append("registry_adoption_trust_root_unresolved")
    items.append(
        _resolution_item("registry", str(registry["registry_id"]), registry_reasons)
    )

    tailoring_reasons: list[str] = []
    if tailoring["reported_adoption_status"] != "adopted":
        tailoring_reasons.append("tailoring_not_adopted")
    elif not _decision_matches(
        tailoring["human_adoption_ref"],
        kind="adopt_lifecycle_tailoring",
        target_id=str(tailoring["tailoring_id"]),
        target_version=str(tailoring["tailoring_version"]),
        basis_digest=tailoring["basis_digest"],
        trusted_decision_verifier=trusted_decision_verifier,
    ):
        tailoring_reasons.append("tailoring_adoption_trust_root_unresolved")
    if tailoring["subject_scope_ref"] != subject_scope_ref:
        tailoring_reasons.append("subject_scope_not_exact")
    items.append(
        _resolution_item("tailoring", str(tailoring["tailoring_id"]), tailoring_reasons)
    )
    items.append(
        _resolution_item(
            "subject",
            str(subject_scope_ref["record_id"]),
            []
            if tailoring["subject_scope_ref"] == subject_scope_ref
            else ["subject_scope_unresolved"],
        )
    )

    applicability_by_stage = {
        str(item["stage_id"]): item for item in tailoring["core_stage_applicability"]
    }
    registry_by_stage = {
        str(item["stage_id"]): item["profile_ref"]
        for item in registry["core_profile_refs"]
    }
    denominator: list[str] = []
    for stage in CORE_STAGES:
        applicability = applicability_by_stage[stage]
        state = applicability["reported_applicability_state"]
        applicability_reasons: list[str] = []
        if state == "unresolved":
            applicability_reasons.append("stage_applicability_unresolved")
        if applicability["reported_human_disposition"] == "waived":
            applicability_reasons.append("waiver_does_not_establish_stage_satisfaction")
            waiver_basis = applicability["denominator_ref"]
            if waiver_basis is None or not _decision_matches(
                applicability["human_disposition_ref"],
                kind="waive_stage",
                target_id=stage,
                target_version="1",
                basis_digest=waiver_basis["content_digest"] if waiver_basis else {},
                accepted_statuses=frozenset({"waive"}),
                trusted_decision_verifier=trusted_decision_verifier,
            ):
                applicability_reasons.append("waiver_trust_root_unresolved")
        app_item = _resolution_item(
            "applicability", f"applicability:{stage}", applicability_reasons
        )
        if state == "not_applicable":
            denominator_ref = applicability["denominator_ref"]
            trust_root_resolved = denominator_ref is not None and _decision_matches(
                applicability["decision_record_ref"],
                kind="stage_not_applicable",
                target_id=stage,
                target_version="1",
                basis_digest=denominator_ref["content_digest"],
                trusted_decision_verifier=trusted_decision_verifier,
            )
            if trust_root_resolved:
                app_item["state"] = "not_applicable"
                app_item["reasons"] = []
                items.append(app_item)
                continue
            app_item["state"] = "unresolved"
            app_item["reasons"] = ["not_applicable_decision_trust_root_unresolved"]
        items.append(app_item)
        denominator.append(stage)

        expected = registry_by_stage[stage]
        key = (str(expected["profile_id"]), str(expected["profile_version"]))
        actual = profile_map.get(key)
        profile_reasons: list[str] = []
        if actual is None:
            profile_reasons.append("profile_missing")
        else:
            actual_ref = profile_ref(actual, require_trusted_decisions=False)
            if actual_ref != expected:
                profile_reasons.append("profile_digest_or_implementation_not_exact")
            if actual["stage_id"] != stage:
                profile_reasons.append("profile_stage_mismatch")
            if actual["reported_adoption_status"] != "adopted":
                profile_reasons.append("profile_not_adopted")
            elif not _decision_matches(
                actual["human_adoption_ref"],
                kind="adopt_stage_profile",
                target_id=str(actual["profile_id"]),
                target_version=str(actual["profile_version"]),
                basis_digest=actual["basis_digest"],
                trusted_decision_verifier=trusted_decision_verifier,
            ):
                profile_reasons.append("profile_adoption_trust_root_unresolved")
        items.append(_resolution_item("profile", f"profile:{stage}", profile_reasons))
        if actual is None:
            continue
        items.append(
            _resolution_item(
                "implementation",
                f"implementation:{stage}",
                []
                if actual["implementation_digest"] == expected["implementation_digest"]
                else ["implementation_not_exact"],
            )
        )
        for requirement in actual["engineering_basis_refs"]:
            rule_key = (str(requirement["rule_id"]), str(requirement["rule_version"]))
            required_rule_keys.add(rule_key)
            binding = rule_map.get(rule_key)
            rule_reasons: list[str] = []
            if binding is None:
                rule_reasons.append("rule_binding_missing")
            else:
                for field in (
                    "content_digest",
                    "basis_digest",
                    "reported_adoption_status",
                ):
                    if binding[field] != requirement[field]:
                        rule_reasons.append(f"rule_{field}_not_exact")
                if binding["reported_adoption_status"] != "adopted":
                    rule_reasons.append("rule_not_adopted")
                elif not _decision_matches(
                    binding["human_adoption_ref"],
                    kind="adopt_engineering_rule",
                    target_id=str(binding["rule_id"]),
                    target_version=str(binding["rule_version"]),
                    basis_digest=binding["basis_digest"],
                    trusted_decision_verifier=trusted_decision_verifier,
                ):
                    rule_reasons.append("rule_adoption_trust_root_unresolved")
                if requirement[
                    "reported_adoption_status"
                ] == "adopted" and not _decision_matches(
                    requirement["human_adoption_ref"],
                    kind="adopt_engineering_rule",
                    target_id=str(requirement["rule_id"]),
                    target_version=str(requirement["rule_version"]),
                    basis_digest=requirement["basis_digest"],
                    trusted_decision_verifier=trusted_decision_verifier,
                ):
                    rule_reasons.append("profile_rule_adoption_trust_root_unresolved")
                for authority in requirement["required_authorities"]:
                    if not binding["authority"].get(authority, False):
                        rule_reasons.append(f"rule_authority_missing:{authority}")
            items.append(
                _resolution_item(
                    "rule", f"rule:{rule_key[0]}:{rule_key[1]}:{stage}", rule_reasons
                )
            )

    registry_extensions = {
        str(item["stage_id"]): item["profile_ref"]
        for item in registry["extension_profile_refs"]
    }
    tailoring_extensions = {
        str(item["stage_id"]): item
        for item in tailoring["extension_stage_applicability"]
    }
    for stage in sorted(set(registry_extensions) | set(tailoring_extensions)):
        expected = registry_extensions.get(stage)
        tailoring_extension = tailoring_extensions.get(stage)
        extension_reasons: list[str] = []
        if expected is None:
            extension_reasons.append("extension_profile_not_registered")
        if tailoring_extension is None:
            extension_reasons.append("extension_applicability_not_enumerated")
            applicability = None
        else:
            applicability = tailoring_extension["applicability"]
            if expected is not None and tailoring_extension["profile_ref"] != expected:
                extension_reasons.append("extension_profile_ref_not_exact")

        applicability_reasons = list(extension_reasons)
        if applicability is None:
            applicability_reasons.append("extension_applicability_unresolved")
            state = "unresolved"
        else:
            state = str(applicability["reported_applicability_state"])
            if state == "unresolved":
                applicability_reasons.append("stage_applicability_unresolved")
            if applicability["reported_human_disposition"] == "waived":
                applicability_reasons.append(
                    "waiver_does_not_establish_stage_satisfaction"
                )
                waiver_basis = applicability["denominator_ref"]
                if waiver_basis is None or not _decision_matches(
                    applicability["human_disposition_ref"],
                    kind="waive_stage",
                    target_id=stage,
                    target_version="1",
                    basis_digest=(
                        waiver_basis["content_digest"] if waiver_basis else {}
                    ),
                    accepted_statuses=frozenset({"waive"}),
                    trusted_decision_verifier=trusted_decision_verifier,
                ):
                    applicability_reasons.append("waiver_trust_root_unresolved")

        app_item = _resolution_item(
            "applicability", f"applicability:{stage}", applicability_reasons
        )
        if applicability is not None and state == "not_applicable":
            denominator_ref = applicability["denominator_ref"]
            trust_root_resolved = denominator_ref is not None and _decision_matches(
                applicability["decision_record_ref"],
                kind="stage_not_applicable",
                target_id=stage,
                target_version="1",
                basis_digest=denominator_ref["content_digest"],
                trusted_decision_verifier=trusted_decision_verifier,
            )
            if trust_root_resolved and not extension_reasons:
                app_item["state"] = "not_applicable"
                app_item["reasons"] = []
                items.append(app_item)
                continue
            app_item["state"] = "unresolved"
            app_item["reasons"] = sorted(
                set(
                    [
                        *extension_reasons,
                        "not_applicable_decision_trust_root_unresolved"
                        if not trust_root_resolved
                        else "extension_registration_unresolved",
                    ]
                )
            )
        items.append(app_item)
        denominator.append(stage)

        if expected is None:
            items.append(
                _resolution_item(
                    "profile",
                    f"profile:{stage}",
                    ["extension_profile_not_registered"],
                )
            )
            continue
        key = (str(expected["profile_id"]), str(expected["profile_version"]))
        actual = profile_map.get(key)
        profile_reasons = list(extension_reasons)
        if actual is None:
            profile_reasons.append("profile_missing")
        else:
            actual_ref = profile_ref(actual, require_trusted_decisions=False)
            if actual_ref != expected:
                profile_reasons.append("profile_digest_or_implementation_not_exact")
            if actual["stage_id"] != stage:
                profile_reasons.append("profile_stage_mismatch")
            if actual["reported_adoption_status"] != "adopted":
                profile_reasons.append("profile_not_adopted")
            elif not _decision_matches(
                actual["human_adoption_ref"],
                kind="adopt_stage_profile",
                target_id=str(actual["profile_id"]),
                target_version=str(actual["profile_version"]),
                basis_digest=actual["basis_digest"],
                trusted_decision_verifier=trusted_decision_verifier,
            ):
                profile_reasons.append("profile_adoption_trust_root_unresolved")
        items.append(_resolution_item("profile", f"profile:{stage}", profile_reasons))
        if actual is None:
            continue
        items.append(
            _resolution_item(
                "implementation",
                f"implementation:{stage}",
                []
                if actual["implementation_digest"] == expected["implementation_digest"]
                else ["implementation_not_exact"],
            )
        )
        for requirement in actual["engineering_basis_refs"]:
            rule_key = (
                str(requirement["rule_id"]),
                str(requirement["rule_version"]),
            )
            required_rule_keys.add(rule_key)
            binding = rule_map.get(rule_key)
            rule_reasons: list[str] = []
            if binding is None:
                rule_reasons.append("rule_binding_missing")
            else:
                for field in (
                    "content_digest",
                    "basis_digest",
                    "reported_adoption_status",
                ):
                    if binding[field] != requirement[field]:
                        rule_reasons.append(f"rule_{field}_not_exact")
                if binding["reported_adoption_status"] != "adopted":
                    rule_reasons.append("rule_not_adopted")
                elif not _decision_matches(
                    binding["human_adoption_ref"],
                    kind="adopt_engineering_rule",
                    target_id=str(binding["rule_id"]),
                    target_version=str(binding["rule_version"]),
                    basis_digest=binding["basis_digest"],
                    trusted_decision_verifier=trusted_decision_verifier,
                ):
                    rule_reasons.append("rule_adoption_trust_root_unresolved")
                if requirement[
                    "reported_adoption_status"
                ] == "adopted" and not _decision_matches(
                    requirement["human_adoption_ref"],
                    kind="adopt_engineering_rule",
                    target_id=str(requirement["rule_id"]),
                    target_version=str(requirement["rule_version"]),
                    basis_digest=requirement["basis_digest"],
                    trusted_decision_verifier=trusted_decision_verifier,
                ):
                    rule_reasons.append("profile_rule_adoption_trust_root_unresolved")
                for authority in requirement["required_authorities"]:
                    if not binding["authority"].get(authority, False):
                        rule_reasons.append(f"rule_authority_missing:{authority}")
            items.append(
                _resolution_item(
                    "rule",
                    f"rule:{rule_key[0]}:{rule_key[1]}:{stage}",
                    rule_reasons,
                )
            )

    registered_profile_keys = {
        (
            str(item["profile_ref"]["profile_id"]),
            str(item["profile_ref"]["profile_version"]),
        )
        for item in [
            *registry["core_profile_refs"],
            *registry["extension_profile_refs"],
        ]
    }
    for profile_key in sorted(set(profile_map) - registered_profile_keys):
        items.append(
            _resolution_item(
                "profile",
                f"profile:unregistered:{profile_key[0]}:{profile_key[1]}",
                ["runtime_profile_not_registered"],
            )
        )

    for rule_key in sorted(set(rule_map) - required_rule_keys):
        items.append(
            _resolution_item(
                "rule",
                f"rule:unrequired:{rule_key[0]}:{rule_key[1]}",
                ["runtime_rule_not_required"],
            )
        )

    unresolved_count = sum(item["state"] == "unresolved" for item in items)
    registry_ref_value = registry_record_ref(registry, require_trusted_decisions=False)
    tailoring_ref_value = tailoring_record_ref(
        tailoring, require_trusted_decisions=False
    )
    stable_material = {
        "registry_ref": registry_ref_value,
        "tailoring_ref": tailoring_ref_value,
        "subject_scope_ref": _copy(subject_scope_ref),
        "decision_verifier_claim": decision_verifier_claim,
        "trusted_decision_verifier_ref": decision_verifier_ref,
        "trust_root_resolution_state": "not_integrated",
        "trust_root_ref": None,
        "required_stage_denominator": denominator,
        "required_rule_denominator": [
            {"rule_id": rule_id, "rule_version": rule_version}
            for rule_id, rule_version in sorted(required_rule_keys)
        ],
        "supplied_rule_bindings": supplied_rule_bindings,
        "resolution_items": items,
    }
    resolution_id = f"runtime:{_digest(stable_material)['value'][:24]}"
    material = {
        "schema_version": RUNTIME_RESOLUTION_VERSION,
        "resolution_id": resolution_id,
        **stable_material,
        "resolution_state": "unresolved",
        "blocking_unresolved_count": unresolved_count,
        "allowed_use": "candidate_and_unresolved_only",
        "formal_authority": "none",
        "limitations": [_LIMITATION, _TRUST_ROOT_LIMITATION],
    }
    result = {**material, "resolution_digest": _digest(material)}
    validate_runtime_resolution(result)
    return result


def resolve_lifecycle_runtime(
    *,
    registry: Mapping[str, Any],
    tailoring: Mapping[str, Any],
    subject_scope_ref: Mapping[str, Any],
    profiles: Sequence[Mapping[str, Any]],
    rule_bindings: Sequence[Mapping[str, Any]],
    trusted_decision_verifier: DecisionVerifier | None = None,
) -> dict[str, Any]:
    """Compatibility alias for :func:`assess_candidate_lifecycle_runtime`.

    The historical name must not be read as formal runtime resolution.  This
    v1 contract always returns ``formal_authority: none`` and an unresolved
    trust root, even when a supplied callback reports that it accepted a
    decision.
    """

    return assess_candidate_lifecycle_runtime(
        registry=registry,
        tailoring=tailoring,
        subject_scope_ref=subject_scope_ref,
        profiles=profiles,
        rule_bindings=rule_bindings,
        trusted_decision_verifier=trusted_decision_verifier,
    )


def validate_runtime_resolution(resolution: Mapping[str, Any]) -> dict[str, Any]:
    _schema_validate(resolution, "runtimeResolution", "lifecycle runtime resolution")
    required_rules = {
        (str(item["rule_id"]), str(item["rule_version"]))
        for item in resolution["required_rule_denominator"]
    }
    supplied_rules = {
        (str(item["rule_id"]), str(item["rule_version"]))
        for item in resolution["supplied_rule_bindings"]
    }
    if len(required_rules) != len(resolution["required_rule_denominator"]):
        raise LifecycleGovernanceError(
            "runtime required rule denominator repeats a rule"
        )
    if len(supplied_rules) != len(resolution["supplied_rule_bindings"]):
        raise LifecycleGovernanceError("runtime supplied rule bindings repeat a rule")
    expected_unrequired_items = {
        f"rule:unrequired:{rule_id}:{rule_version}"
        for rule_id, rule_version in supplied_rules - required_rules
    }
    observed_unrequired_items = {
        str(item["item_id"])
        for item in resolution["resolution_items"]
        if "runtime_rule_not_required" in item["reasons"]
        and item["item_kind"] == "rule"
        and item["state"] == "unresolved"
    }
    if observed_unrequired_items != expected_unrequired_items:
        raise LifecycleGovernanceError(
            "runtime unrequired rule findings do not match the supplied rule denominator"
        )
    unresolved = sum(
        item["state"] == "unresolved" for item in resolution["resolution_items"]
    )
    if resolution["blocking_unresolved_count"] != unresolved:
        raise LifecycleGovernanceError("runtime unresolved count does not replay")
    if unresolved < 1 or resolution["resolution_state"] != "unresolved":
        raise LifecycleGovernanceError("runtime resolution state does not replay")
    if resolution["allowed_use"] != "candidate_and_unresolved_only":
        raise LifecycleGovernanceError("runtime allowed-use ceiling does not replay")
    if (
        resolution["trust_root_resolution_state"] != "not_integrated"
        or resolution["trust_root_ref"] is not None
    ):
        raise LifecycleGovernanceError(
            "runtime resolution cannot self-establish a decision trust root"
        )
    if _TRUST_ROOT_LIMITATION not in resolution["limitations"]:
        raise LifecycleGovernanceError("decision trust-root limitation is missing")
    if resolution["formal_authority"] != "none":
        raise LifecycleGovernanceError(
            "runtime resolution cannot hold formal authority"
        )
    _validate_digest(resolution, "resolution_digest", "runtime resolution")
    return _copy(resolution)
