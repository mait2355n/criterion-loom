"""Closed information-handling and verified-nonapplicability audit material.

The module has two deliberately exclusive paths:

* ``adopted_profile`` checks a profile declared to have an external human
  decision against a declared information-flow inventory and control evidence.
* ``verified_nonapplicability`` checks the internal consistency of a declared
  local synthetic boundary whose six conditions are derived from subject,
  configuration, runtime-path, and restart material.

All builders and validators are local and deterministic. Digests bind supplied
content but do not authenticate a clock, actor, classification, observer,
inventory, or external record. Version 1 therefore emits weak declared internal
consistency only and lists every stronger claim as unproved. This module never
adopts a policy, issues a credential, transmits data, declares an incident,
accepts risk, or makes final acceptance.
"""

from __future__ import annotations

import copy
from collections import deque
from datetime import datetime
from functools import lru_cache
import hashlib
import json
from typing import Any, Iterable, Mapping, Sequence

from jsonschema import Draft202012Validator, FormatChecker

from .schema_access import schema_path


SCHEMA_VERSION = "secure-operation/v1"
SCOPE_MANIFEST_VERSION = "secure-operation-scope-manifest/v1"
EVIDENCE_VERSION = "secure-operation-evidence/v1"
SECURE_PROFILE_VERSION = "secure-operation-profile/v0"
NONAPPLICABILITY_PROFILE_VERSION = (
    "secure-operation-nonapplicability-profile/v0"
)
REVIEW_VERSION = "secure-operation-independent-review/v1"

MAX_SCOPE_ENTRIES = 2048
MAX_COMPONENTS = 2048
MAX_FLOWS = 4096
MAX_EVIDENCE = 4096

DATA_CLASSES = (
    "synthetic",
    "public",
    "internal",
    "confidential",
    "personal",
    "secret",
)
SENSITIVE_CLASSES = frozenset({"internal", "confidential", "personal", "secret"})
DATA_CLASS_RANK = {value: index for index, value in enumerate(DATA_CLASSES)}
MANIFEST_KINDS = ("subject", "configuration", "runtime_path")
CONTROL_KINDS = (
    "encryption",
    "credential",
    "least_privilege",
    "dependency",
    "resource_limit",
    "denial_of_service",
    "incident_response",
    "notification",
)
REQUALIFICATION_DIMENSIONS = (
    "subject",
    "classification",
    "provider",
    "configuration",
    "runtime_path",
    "dependency",
    "credential",
    "incident",
)
NONAPPLICABILITY_CONDITIONS = (
    "synthetic",
    "local",
    "nonprivileged",
    "nondurable",
    "no_external",
    "no_sensitive",
)
REACTIVATION_TRIGGERS = (
    "external_provider_observed",
    "real_material_observed",
    "durable_output_observed",
    "sensitive_data_observed",
    "privilege_observed",
    "production_scope_requested",
    "restart_binding_mismatch",
)
ALLOWED_FLOW_PAIRS = frozenset(
    {
        ("source", "processor"),
        ("source", "provider"),
        ("processor", "processor"),
        ("processor", "provider"),
        ("processor", "log"),
        ("processor", "artifact"),
        ("processor", "retention"),
        ("provider", "processor"),
        ("provider", "log"),
        ("provider", "artifact"),
        ("provider", "retention"),
        ("log", "retention"),
        ("artifact", "retention"),
    }
)
POSITIVE_EVIDENCE_TRUST = frozenset(
    {"tool_observed", "independently_observed", "signed"}
)
CONDITION_EVIDENCE_KINDS = {
    "synthetic": frozenset({"scope_inventory"}),
    "local": frozenset({"runtime_observation"}),
    "nonprivileged": frozenset(
        {"configuration_observation", "runtime_observation"}
    ),
    "nondurable": frozenset({"runtime_observation"}),
    "no_external": frozenset({"runtime_observation"}),
    "no_sensitive": frozenset({"scope_inventory"}),
}
CONTROL_EVIDENCE_KINDS = {
    "encryption": frozenset({"control_test"}),
    "credential": frozenset({"control_test"}),
    "least_privilege": frozenset({"control_test"}),
    "dependency": frozenset({"dependency_scan"}),
    "resource_limit": frozenset({"resource_test"}),
    "denial_of_service": frozenset({"dos_test"}),
    "incident_response": frozenset({"incident_rehearsal"}),
    "notification": frozenset({"notification_rehearsal"}),
}
UNPROVED_CLAIM_CODES = (
    "external_human_decision_authenticity_unproved",
    "independent_review_authenticity_unproved",
    "operational_evidence_authenticity_unproved",
    "scope_denominator_authenticity_unproved",
    "scope_version_continuity_unproved",
    "trusted_time_authenticity_unproved",
)

_SCHEMA_PATH = schema_path("secure-operation.schema.json")
_DEFAULT_LIMITATIONS = (
    "Digest closure binds supplied content but does not authenticate clocks, actors, classifications, observers, evidence locators, or external records.",
    "Closed manifests cover only the declared denominator and do not prove that every real information path was discovered.",
    "Declared profile consistency and declared local nonapplicability do not establish external authenticity, field validity, human acceptance, incident disposition, or risk acceptance.",
    "semantic-guard audits supplied material only and performs no credential, transmission, notification, incident, or policy-adoption action.",
)
_AUTHORITY_BOUNDARY = {
    "semantic_guard_role": "audit_declared_information_handling_only",
    "adopt_policy": False,
    "verify_external_authenticity": False,
    "strong_positive_claims_enabled": False,
    "determine_classification_truth": False,
    "issue_credentials": False,
    "transmit_external_data": False,
    "declare_incident": False,
    "accept_risk": False,
    "final_acceptance_owner": "human",
}
_OPEN_DIMENSIONS = {
    "classification_truth": "open",
    "credential_authority": "open",
    "incident_decision": "open",
    "risk_acceptance": "open",
    "human_acceptance": "open",
    "field_validity": "open",
}


class SecureOperationValidationError(ValueError):
    """Raised with stable typed codes when a bundle fails closed."""

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
    return hashlib.sha256(_canonical(value)).hexdigest()


def digest_value(value: Any) -> dict[str, str]:
    return {"algorithm": "sha256", "value": canonical_sha256(value)}


def versioned_ref(
    ref_id: str,
    version: str,
    material: Any | None = None,
) -> dict[str, Any]:
    basis = {"ref_id": ref_id, "version": version} if material is None else material
    return {"ref_id": ref_id, "version": version, "digest": digest_value(basis)}


def _without(value: Mapping[str, Any], *fields: str) -> dict[str, Any]:
    result = copy.deepcopy(dict(value))
    for field in fields:
        result.pop(field, None)
    return result


def _sorted_dicts(
    values: Iterable[Mapping[str, Any]],
    *fields: str,
) -> list[dict[str, Any]]:
    return sorted(
        [copy.deepcopy(dict(value)) for value in values],
        key=lambda value: tuple(str(value.get(field, "")) for field in fields),
    )


def _parse_time(value: str) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith(("Z", "z")) else value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"timestamp lacks timezone: {value}")
    return parsed


def _duplicates(values: Iterable[str]) -> set[str]:
    observed: set[str] = set()
    duplicate: set[str] = set()
    for value in values:
        if value in observed:
            duplicate.add(value)
        observed.add(value)
    return duplicate


def _add(
    errors: list[dict[str, str]],
    code: str,
    location: str,
    message: str,
) -> None:
    errors.append({"code": code, "location": location, "message": message})


def _schema_location(path: Iterable[Any]) -> str:
    parts = [str(item) for item in path]
    return "$" if not parts else "$." + ".".join(parts)


@lru_cache(maxsize=1)
def _validator() -> Draft202012Validator:
    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def build_scope_entry(
    *,
    entry_id: str,
    entry_kind: str,
    locator: str,
    content_digest: Mapping[str, Any],
    attributes: Mapping[str, Any],
    evidence_refs: Iterable[str] = (),
) -> dict[str, Any]:
    normalized_attributes = copy.deepcopy(dict(attributes))
    normalized_attributes["data_classes"] = sorted(
        set(normalized_attributes["data_classes"])
    )
    material = {
        "entry_id": entry_id,
        "entry_kind": entry_kind,
        "locator": locator,
        "content_digest": copy.deepcopy(dict(content_digest)),
        "attributes": normalized_attributes,
        "evidence_refs": sorted(set(evidence_refs)),
    }
    return {**material, "entry_digest": digest_value(material)}


def build_scope_manifest(
    *,
    manifest_id: str,
    manifest_version: str,
    manifest_kind: str,
    closure_rule: str,
    inventory_authority_ref: Mapping[str, Any],
    inventory_evidence_refs: Iterable[str],
    entries: Iterable[Mapping[str, Any]],
    previous_manifest_digest: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    material = {
        "schema_version": SCOPE_MANIFEST_VERSION,
        "manifest_id": manifest_id,
        "manifest_version": manifest_version,
        "manifest_kind": manifest_kind,
        "closure_rule": closure_rule,
        "inventory_status": "declared_complete_unverified",
        "inventory_authority_ref": copy.deepcopy(dict(inventory_authority_ref)),
        "inventory_evidence_refs": sorted(set(inventory_evidence_refs)),
        "previous_manifest_digest": (
            None
            if previous_manifest_digest is None
            else copy.deepcopy(dict(previous_manifest_digest))
        ),
        "entries": _sorted_dicts(entries, "entry_id"),
    }
    return {**material, "manifest_digest": digest_value(material)}


def scope_digest(manifests: Iterable[Mapping[str, Any]]) -> dict[str, str]:
    return digest_value(_sorted_dicts(manifests, "manifest_kind", "manifest_id"))


def build_evidence_observation(
    *,
    evidence_id: str,
    evidence_kind: str,
    locator: str,
    content_digest: Mapping[str, Any],
    scope_digest_value: Mapping[str, Any],
    claim_refs: Iterable[str],
    observer: Mapping[str, Any],
    trust_class: str,
    observed_at: str,
    expires_at: str,
    time_trust: str,
    limitations: Iterable[str],
) -> dict[str, Any]:
    material = {
        "schema_version": EVIDENCE_VERSION,
        "evidence_id": evidence_id,
        "evidence_kind": evidence_kind,
        "locator": locator,
        "content_digest": copy.deepcopy(dict(content_digest)),
        "scope_digest": copy.deepcopy(dict(scope_digest_value)),
        "claim_refs": sorted(set(claim_refs)),
        "observer": copy.deepcopy(dict(observer)),
        "trust_class": trust_class,
        "observed_at": observed_at,
        "expires_at": expires_at,
        "time_trust": time_trust,
        "authenticity_status": "unverified",
        "limitations": sorted(set(limitations)),
    }
    return {**material, "evidence_digest": digest_value(material)}


def build_external_human_decision(
    *,
    decision_id: str,
    decision_sequence: int,
    decision_kind: str,
    decided_by: str,
    decided_at: str,
    target_id: str,
    target_version: str,
    target_digest: Mapping[str, Any],
    target_scope_digest: Mapping[str, Any],
    trust_class: str,
    record_ref: Mapping[str, Any],
    rationale: str,
) -> dict[str, Any]:
    material = {
        "decision_id": decision_id,
        "decision_sequence": decision_sequence,
        "decision_kind": decision_kind,
        "decision_source": "external_human_record",
        "actor_kind": "human",
        "decided_by": decided_by,
        "decided_at": decided_at,
        "status": "accepted",
        "target_id": target_id,
        "target_version": target_version,
        "target_digest": copy.deepcopy(dict(target_digest)),
        "target_scope_digest": copy.deepcopy(dict(target_scope_digest)),
        "trust_class": trust_class,
        "authenticity_status": "unverified",
        "record_ref": copy.deepcopy(dict(record_ref)),
        "rationale": rationale,
    }
    return {**material, "decision_digest": digest_value(material)}


def build_purpose(
    *,
    purpose_id: str,
    version: str,
    description: str,
    allowed_data_classes: Iterable[str],
) -> dict[str, Any]:
    material = {
        "purpose_id": purpose_id,
        "version": version,
        "description": description,
        "allowed_data_classes": sorted(set(allowed_data_classes)),
    }
    return {**material, "purpose_digest": digest_value(material)}


def build_destination(
    *,
    destination_id: str,
    version: str,
    component_kind: str,
    external: bool,
    allowed_data_classes: Iterable[str],
    allowed_purpose_refs: Iterable[str],
) -> dict[str, Any]:
    material = {
        "destination_id": destination_id,
        "version": version,
        "component_kind": component_kind,
        "external": external,
        "allowed_data_classes": sorted(set(allowed_data_classes)),
        "allowed_purpose_refs": sorted(set(allowed_purpose_refs)),
    }
    return {**material, "destination_digest": digest_value(material)}


def build_retention_rule(
    *,
    retention_id: str,
    version: str,
    data_classes: Iterable[str],
    maximum_seconds: int,
    deletion_evidence_required: bool,
) -> dict[str, Any]:
    material = {
        "retention_id": retention_id,
        "version": version,
        "data_classes": sorted(set(data_classes)),
        "maximum_seconds": maximum_seconds,
        "deletion_evidence_required": deletion_evidence_required,
    }
    return {**material, "retention_digest": digest_value(material)}


def build_retention_observation(
    *,
    observation_id: str,
    component_ref: str,
    retention_rule: Mapping[str, Any],
    configured_maximum_seconds: int,
    deletion_evidence_present: bool,
    evidence_refs: Iterable[str],
) -> dict[str, Any]:
    material = {
        "observation_id": observation_id,
        "component_ref": component_ref,
        "retention_rule_ref": retention_rule["retention_id"],
        "retention_rule_digest": copy.deepcopy(retention_rule["retention_digest"]),
        "configured_maximum_seconds": configured_maximum_seconds,
        "deletion_evidence_present": deletion_evidence_present,
        "evidence_refs": sorted(set(evidence_refs)),
    }
    return {**material, "observation_digest": digest_value(material)}


def build_control_profile(
    *,
    control_id: str,
    version: str,
    control_kind: str,
    requirements: Iterable[str],
) -> dict[str, Any]:
    material = {
        "control_id": control_id,
        "version": version,
        "control_kind": control_kind,
        "requirements": sorted(set(requirements)),
    }
    return {**material, "control_digest": digest_value(material)}


def build_requalification_trigger(
    *,
    trigger_id: str,
    version: str,
    dimension: str,
    condition: str,
    required_evidence_kinds: Iterable[str],
) -> dict[str, Any]:
    material = {
        "trigger_id": trigger_id,
        "version": version,
        "dimension": dimension,
        "condition": condition,
        "invalidates": True,
        "required_evidence_kinds": sorted(set(required_evidence_kinds)),
    }
    return {**material, "trigger_digest": digest_value(material)}


def build_secure_operation_profile(
    *,
    profile_id: str,
    profile_version: str,
    status: str,
    decision_record_ref: str | None,
    purposes: Iterable[Mapping[str, Any]],
    destination_allowlist: Iterable[Mapping[str, Any]],
    retention_rules: Iterable[Mapping[str, Any]],
    classification_policy: Mapping[str, Any],
    control_profiles: Iterable[Mapping[str, Any]],
    requalification_triggers: Iterable[Mapping[str, Any]],
    max_evidence_age_seconds: int,
) -> dict[str, Any]:
    classification = copy.deepcopy(dict(classification_policy))
    for field in (
        "redaction_required_classes",
        "encryption_in_transit_required_classes",
        "encryption_at_rest_required_classes",
        "external_transmission_allowed_classes",
        "prohibited_log_classes",
    ):
        classification[field] = sorted(set(classification[field]))
    basis = {
        "schema_version": SECURE_PROFILE_VERSION,
        "profile_id": profile_id,
        "profile_version": profile_version,
        "purposes": _sorted_dicts(purposes, "purpose_id"),
        "destination_allowlist": _sorted_dicts(
            destination_allowlist, "destination_id"
        ),
        "retention_rules": _sorted_dicts(retention_rules, "retention_id"),
        "classification_policy": classification,
        "control_profiles": _sorted_dicts(control_profiles, "control_kind"),
        "requalification_triggers": _sorted_dicts(
            requalification_triggers, "dimension"
        ),
        "max_evidence_age_seconds": max_evidence_age_seconds,
    }
    material = {
        **basis,
        "profile_basis_digest": digest_value(basis),
        "status": status,
        "decision_record_ref": decision_record_ref,
    }
    return {**material, "profile_digest": digest_value(material)}


def build_nonapplicability_profile(
    *,
    profile_id: str,
    profile_version: str,
    status: str,
    decision_record_ref: str | None,
    max_evidence_age_seconds: int,
) -> dict[str, Any]:
    basis = {
        "schema_version": NONAPPLICABILITY_PROFILE_VERSION,
        "profile_id": profile_id,
        "profile_version": profile_version,
        "required_conditions": list(NONAPPLICABILITY_CONDITIONS),
        "reactivation_triggers": list(REACTIVATION_TRIGGERS),
        "scope_limit": "local_fixture_only",
        "max_evidence_age_seconds": max_evidence_age_seconds,
    }
    material = {
        **basis,
        "profile_basis_digest": digest_value(basis),
        "status": status,
        "decision_record_ref": decision_record_ref,
    }
    return {**material, "profile_digest": digest_value(material)}


def build_data_item(
    *,
    data_id: str,
    data_class: str,
    subject_entry_ref: str,
    source_component_ref: str,
    allowed_purpose_refs: Iterable[str],
    field_names: Iterable[str],
) -> dict[str, Any]:
    material = {
        "data_id": data_id,
        "data_class": data_class,
        "subject_entry_ref": subject_entry_ref,
        "source_component_ref": source_component_ref,
        "allowed_purpose_refs": sorted(set(allowed_purpose_refs)),
        "field_names": sorted(set(field_names)),
    }
    return {**material, "data_digest": digest_value(material)}


def build_flow_component(
    *,
    component_id: str,
    component_kind: str,
    runtime_entry_ref: str,
    destination_ref: str | None,
    external: bool,
    persistent: bool,
    privileged: bool,
    retention_rule_ref: str | None,
    encryption_at_rest: str,
    least_privilege_scopes: Iterable[str],
    credential_binding_ref: Mapping[str, Any] | None,
) -> dict[str, Any]:
    material = {
        "component_id": component_id,
        "component_kind": component_kind,
        "runtime_entry_ref": runtime_entry_ref,
        "destination_ref": destination_ref,
        "external": external,
        "persistent": persistent,
        "privileged": privileged,
        "retention_rule_ref": retention_rule_ref,
        "encryption_at_rest": encryption_at_rest,
        "least_privilege_scopes": sorted(set(least_privilege_scopes)),
        "credential_binding_ref": (
            None
            if credential_binding_ref is None
            else copy.deepcopy(dict(credential_binding_ref))
        ),
    }
    return {**material, "component_digest": digest_value(material)}


def build_information_flow(
    *,
    flow_id: str,
    data_ref: str,
    from_component_ref: str,
    to_component_ref: str,
    purpose_ref: str,
    transmitted_fields: Iterable[str],
    minimization: str,
    redaction: str,
    encryption_in_transit: str,
    credential_binding_ref: Mapping[str, Any] | None,
    evidence_refs: Iterable[str],
) -> dict[str, Any]:
    material = {
        "flow_id": flow_id,
        "data_ref": data_ref,
        "from_component_ref": from_component_ref,
        "to_component_ref": to_component_ref,
        "purpose_ref": purpose_ref,
        "transmitted_fields": sorted(set(transmitted_fields)),
        "minimization": minimization,
        "redaction": redaction,
        "encryption_in_transit": encryption_in_transit,
        "credential_binding_ref": (
            None
            if credential_binding_ref is None
            else copy.deepcopy(dict(credential_binding_ref))
        ),
        "evidence_refs": sorted(set(evidence_refs)),
    }
    return {**material, "flow_digest": digest_value(material)}


def build_flow_observation(
    *,
    observation_id: str,
    flow: Mapping[str, Any],
    evidence_refs: Iterable[str],
) -> dict[str, Any]:
    material = {
        "observation_id": observation_id,
        "flow_ref": flow["flow_id"],
        "flow_digest": copy.deepcopy(flow["flow_digest"]),
        "evidence_refs": sorted(set(evidence_refs)),
    }
    return {**material, "observation_digest": digest_value(material)}


def build_control_result(
    *,
    control: Mapping[str, Any],
    status: str,
    evidence_refs: Iterable[str],
) -> dict[str, Any]:
    material = {
        "control_ref": control["control_id"],
        "control_digest": copy.deepcopy(control["control_digest"]),
        "control_kind": control["control_kind"],
        "status": status,
        "evidence_refs": sorted(set(evidence_refs)),
    }
    return {**material, "result_digest": digest_value(material)}


def build_trigger_assessment(
    *,
    trigger: Mapping[str, Any],
    status: str,
    evidence_refs: Iterable[str],
) -> dict[str, Any]:
    material = {
        "trigger_ref": trigger["trigger_id"],
        "trigger_digest": copy.deepcopy(trigger["trigger_digest"]),
        "dimension": trigger["dimension"],
        "status": status,
        "evidence_refs": sorted(set(evidence_refs)),
    }
    return {**material, "assessment_digest": digest_value(material)}


def build_condition_result(
    *,
    condition_id: str,
    status: str,
    scope_digest_value: Mapping[str, Any],
    evidence_refs: Iterable[str],
) -> dict[str, Any]:
    material = {
        "condition_id": condition_id,
        "status": status,
        "scope_digest": copy.deepcopy(dict(scope_digest_value)),
        "evidence_refs": sorted(set(evidence_refs)),
    }
    return {**material, "result_digest": digest_value(material)}


def build_restart_test(
    *,
    test_id: str,
    before_configuration_digest: Mapping[str, Any],
    before_runtime_path_digest: Mapping[str, Any],
    after_configuration_digest: Mapping[str, Any],
    after_runtime_path_digest: Mapping[str, Any],
    status: str,
    observed_at: str,
    expires_at: str,
    time_trust: str,
    evidence_refs: Iterable[str],
) -> dict[str, Any]:
    material = {
        "test_id": test_id,
        "before_configuration_digest": copy.deepcopy(
            dict(before_configuration_digest)
        ),
        "before_runtime_path_digest": copy.deepcopy(
            dict(before_runtime_path_digest)
        ),
        "after_configuration_digest": copy.deepcopy(
            dict(after_configuration_digest)
        ),
        "after_runtime_path_digest": copy.deepcopy(dict(after_runtime_path_digest)),
        "status": status,
        "observed_at": observed_at,
        "expires_at": expires_at,
        "time_trust": time_trust,
        "authenticity_status": "unverified",
        "evidence_refs": sorted(set(evidence_refs)),
    }
    return {**material, "test_digest": digest_value(material)}


def build_independent_review(
    *,
    review_id: str,
    reviewer_ref: Mapping[str, Any],
    target_assessment_id: str,
    target_assessment_version: str,
    target_basis_digest: Mapping[str, Any],
    status: str,
    reviewed_at: str,
    expires_at: str,
    time_trust: str,
    evidence_refs: Iterable[str],
) -> dict[str, Any]:
    material = {
        "schema_version": REVIEW_VERSION,
        "review_id": review_id,
        "review_source": "external_independent_record",
        "reviewer_ref": copy.deepcopy(dict(reviewer_ref)),
        "relationship_to_subject": "independent",
        "target_assessment_id": target_assessment_id,
        "target_assessment_version": target_assessment_version,
        "target_basis_digest": copy.deepcopy(dict(target_basis_digest)),
        "status": status,
        "reviewed_at": reviewed_at,
        "expires_at": expires_at,
        "time_trust": time_trust,
        "authenticity_status": "unverified",
        "evidence_refs": sorted(set(evidence_refs)),
    }
    return {**material, "review_digest": digest_value(material)}


def _profile_ref(profile: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "profile_id": profile["profile_id"],
        "profile_version": profile["profile_version"],
        "profile_digest": copy.deepcopy(profile["profile_digest"]),
        "status": profile["status"],
    }


def _basis_material(bundle: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: copy.deepcopy(value)
        for key, value in bundle.items()
        if key
        not in {
            "review_basis_digest",
            "independent_review_record",
            "result",
            "assessment_digest",
        }
    }


def _matching_policy_decision(
    profile: Mapping[str, Any],
    decisions: Sequence[Mapping[str, Any]],
    *,
    path: str,
    expected_scope_digest: Mapping[str, Any],
) -> bool:
    reference = profile["decision_record_ref"]
    if not reference:
        return False
    relevant = [
        item
        for item in decisions
        if item["target_id"] == profile["profile_id"]
        and item["target_version"] == profile["profile_version"]
        and item["target_digest"] == profile["profile_basis_digest"]
        and item["target_scope_digest"] == expected_scope_digest
    ]
    if not relevant:
        return False
    highest_sequence = max(int(item["decision_sequence"]) for item in relevant)
    effective = [
        item for item in relevant if int(item["decision_sequence"]) == highest_sequence
    ]
    if len(effective) != 1 or effective[0]["decision_id"] != reference:
        return False
    decision = effective[0]
    if path == "adopted_profile":
        expected = (
            "adopt_secure_operation_profile"
            if profile["status"] == "adopted"
            else "retire_secure_operation_profile"
        )
    else:
        expected = (
            "select_nonapplicability_boundary"
            if profile["status"] == "adopted"
            else "retire_nonapplicability_boundary"
        )
    return (
        decision["decision_kind"] == expected
        and decision["target_id"] == profile["profile_id"]
        and decision["target_version"] == profile["profile_version"]
        and decision["target_digest"] == profile["profile_basis_digest"]
        and decision["target_scope_digest"] == expected_scope_digest
    )


def _evidence_trust_tuple_valid(evidence: Mapping[str, Any]) -> bool:
    observer = evidence["observer"]
    trust = evidence["trust_class"]
    kind = observer["observer_kind"]
    relationship = observer["relationship_to_subject"]
    if trust == "self_reported":
        return relationship == "self"
    if trust == "tool_observed":
        return kind == "tool" and relationship == "tool_observer"
    if trust == "independently_observed":
        return relationship == "independent"
    if trust == "signed":
        return kind in {"human", "external_system"} and relationship == "independent"
    return False


def _evidence_usable(
    evidence: Mapping[str, Any],
    *,
    assessed_at: str,
    max_age_seconds: int,
    expected_scope_digest: Mapping[str, Any],
) -> bool:
    try:
        observed = _parse_time(str(evidence["observed_at"]))
        expires = _parse_time(str(evidence["expires_at"]))
        assessed = _parse_time(assessed_at)
    except (KeyError, TypeError, ValueError):
        return False
    return (
        evidence["scope_digest"] == expected_scope_digest
        and evidence["time_trust"] == "trusted"
        and evidence["trust_class"] in POSITIVE_EVIDENCE_TRUST
        and _evidence_trust_tuple_valid(evidence)
        and observed <= assessed <= expires
        and (assessed - observed).total_seconds() <= max_age_seconds
    )


def _refs_usable(
    parent_ref: str,
    evidence_refs: Sequence[str],
    evidence_by_id: Mapping[str, Mapping[str, Any]],
    *,
    assessed_at: str,
    max_age_seconds: int,
    expected_scope_digest: Mapping[str, Any],
    allowed_evidence_kinds: frozenset[str] | None = None,
    expected_observer_ref: Mapping[str, Any] | None = None,
) -> bool:
    return bool(evidence_refs) and all(
        evidence_ref in evidence_by_id
        and parent_ref in evidence_by_id[evidence_ref]["claim_refs"]
        and (
            allowed_evidence_kinds is None
            or evidence_by_id[evidence_ref]["evidence_kind"]
            in allowed_evidence_kinds
        )
        and (
            expected_observer_ref is None
            or evidence_by_id[evidence_ref]["observer"]["observer_ref"]
            == expected_observer_ref
        )
        and _evidence_usable(
            evidence_by_id[evidence_ref],
            assessed_at=assessed_at,
            max_age_seconds=max_age_seconds,
            expected_scope_digest=expected_scope_digest,
        )
        for evidence_ref in evidence_refs
    )


def _review_usable(
    review: Mapping[str, Any] | None,
    *,
    assessment_id: str,
    assessment_version: str,
    basis_digest: Mapping[str, Any],
    assessed_at: str,
    evidence_by_id: Mapping[str, Mapping[str, Any]],
    max_age_seconds: int,
    expected_scope_digest: Mapping[str, Any],
) -> bool:
    if review is None:
        return False
    try:
        reviewed = _parse_time(str(review["reviewed_at"]))
        expires = _parse_time(str(review["expires_at"]))
        assessed = _parse_time(assessed_at)
    except (KeyError, TypeError, ValueError):
        return False
    if not (
        review["review_source"] == "external_independent_record"
        and review["relationship_to_subject"] == "independent"
        and review["status"] == "accepted"
        and review["time_trust"] == "trusted"
        and review["target_assessment_id"] == assessment_id
        and review["target_assessment_version"] == assessment_version
        and review["target_basis_digest"] == basis_digest
        and reviewed <= assessed <= expires
        and (assessed - reviewed).total_seconds() <= max_age_seconds
    ):
        return False
    return _refs_usable(
        str(review["review_id"]),
        list(review["evidence_refs"]),
        evidence_by_id,
        assessed_at=assessed_at,
        max_age_seconds=max_age_seconds,
        expected_scope_digest=expected_scope_digest,
        allowed_evidence_kinds=frozenset({"independent_review"}),
        expected_observer_ref=review["reviewer_ref"],
    ) and all(
        evidence_by_id[ref]["trust_class"]
        in {"independently_observed", "signed"}
        and evidence_by_id[ref]["observer"]["relationship_to_subject"]
        == "independent"
        for ref in review["evidence_refs"]
        if ref in evidence_by_id
    )


def _manifest_by_kind(
    manifests: Sequence[Mapping[str, Any]],
) -> dict[str, Mapping[str, Any]]:
    return {str(item["manifest_kind"]): item for item in manifests}


def _all_entries(
    manifests: Sequence[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    return [entry for manifest in manifests for entry in manifest["entries"]]


def _derived_nonapplicability_conditions(
    manifests: Sequence[Mapping[str, Any]],
) -> dict[str, bool]:
    attributes = [item["attributes"] for item in _all_entries(manifests)]
    return {
        "synthetic": bool(attributes)
        and all(
            set(value["data_classes"]) <= {"synthetic"}
            and not value["real_material"]
            and value["source_kind"]
            in {"synthetic", "local_fixture", "not_applicable"}
            for value in attributes
        ),
        "local": bool(attributes)
        and all(value["execution_location"] == "local" for value in attributes),
        "nonprivileged": bool(attributes)
        and all(
            not value["privileged"] and not value["credential_present"]
            for value in attributes
        ),
        "nondurable": bool(attributes)
        and all(
            not value["durable"]
            and not value["persistent_log"]
            and not value["persistent_artifact"]
            for value in attributes
        ),
        "no_external": bool(attributes)
        and all(
            not value["external_provider"]
            and value["execution_location"] == "local"
            for value in attributes
        ),
        "no_sensitive": bool(attributes)
        and all(
            not (set(value["data_classes"]) & SENSITIVE_CLASSES)
            for value in attributes
        ),
    }


def _reactivation_from_scope(
    *,
    manifests: Sequence[Mapping[str, Any]],
    claimed_environment: str,
    restart_test: Mapping[str, Any],
) -> list[str]:
    entries = _all_entries(manifests)
    attributes = [item["attributes"] for item in entries]
    triggers: set[str] = set()
    if any(
        value["external_provider"] or value["execution_location"] == "external"
        for value in attributes
    ):
        triggers.add("external_provider_observed")
    if any(value["real_material"] for value in attributes):
        triggers.add("real_material_observed")
    if any(
        value["source_kind"]
        not in {"synthetic", "local_fixture", "not_applicable"}
        for value in attributes
    ):
        triggers.add("real_material_observed")
    if any(
        value["durable"]
        or value["persistent_log"]
        or value["persistent_artifact"]
        for value in attributes
    ):
        triggers.add("durable_output_observed")
    if any(
        set(value["data_classes"]) & SENSITIVE_CLASSES for value in attributes
    ):
        triggers.add("sensitive_data_observed")
    if any(value["privileged"] or value["credential_present"] for value in attributes):
        triggers.add("privilege_observed")
    if claimed_environment == "production":
        triggers.add("production_scope_requested")

    by_kind = _manifest_by_kind(manifests)
    configuration = by_kind.get("configuration")
    runtime_path = by_kind.get("runtime_path")
    if (
        configuration is None
        or runtime_path is None
        or restart_test["before_configuration_digest"]
        != configuration["manifest_digest"]
        or restart_test["before_runtime_path_digest"]
        != runtime_path["manifest_digest"]
        or restart_test["after_configuration_digest"]
        != configuration["manifest_digest"]
        or restart_test["after_runtime_path_digest"]
        != runtime_path["manifest_digest"]
        or restart_test["status"] != "passed"
    ):
        triggers.add("restart_binding_mismatch")
    return sorted(triggers)


def _graph_reaches_retention(
    data_id: str,
    source: str,
    flows: Sequence[Mapping[str, Any]],
    components: Mapping[str, Mapping[str, Any]],
) -> bool:
    relevant = [item for item in flows if item["data_ref"] == data_id]
    adjacency: dict[str, set[str]] = {}
    for flow in relevant:
        adjacency.setdefault(str(flow["from_component_ref"]), set()).add(
            str(flow["to_component_ref"])
        )
    reachable: set[str] = set()
    pending = [source]
    while pending:
        node = pending.pop()
        if node in reachable:
            continue
        if node not in components or len(reachable) >= MAX_COMPONENTS:
            return False
        reachable.add(node)
        pending.extend(adjacency.get(node, set()) - reachable)

    indegree = {node: 0 for node in reachable}
    for node in reachable:
        for target in adjacency.get(node, set()):
            if target not in reachable:
                return False
            indegree[target] += 1
    ready = deque(sorted(node for node, degree in indegree.items() if degree == 0))
    order: list[str] = []
    while ready:
        node = ready.popleft()
        order.append(node)
        for target in sorted(adjacency.get(node, set())):
            indegree[target] -= 1
            if indegree[target] == 0:
                ready.append(target)
    if len(order) != len(reachable):
        return False

    closes: dict[str, bool] = {}
    for node in reversed(order):
        component = components[node]
        targets = adjacency.get(node, set())
        if component["component_kind"] == "retention":
            closes[node] = not targets
        else:
            closes[node] = bool(targets) and all(closes[target] for target in targets)
    return closes.get(source, False)


def _adopted_profile_reasons(
    bundle: Mapping[str, Any],
    *,
    basis_digest: Mapping[str, Any],
) -> list[str]:
    contract = bundle["path_contract"]
    profile = contract["profile"]
    evidence_by_id = {
        str(item["evidence_id"]): item for item in bundle["evidence_observations"]
    }
    reasons: set[str] = set()
    for manifest in bundle["scope_manifests"]:
        if not _refs_usable(
            str(manifest["manifest_id"]),
            list(manifest["inventory_evidence_refs"]),
            evidence_by_id,
            assessed_at=str(bundle["assessed_at"]),
            max_age_seconds=int(profile["max_evidence_age_seconds"]),
            expected_scope_digest=bundle["scope_digest"],
            allowed_evidence_kinds=frozenset({"scope_inventory"}),
            expected_observer_ref=manifest["inventory_authority_ref"],
        ):
            reasons.add("scope_denominator_evidence_not_current_or_trusted")
    if profile["status"] != "adopted":
        reasons.add("profile_not_adopted")
    elif not _matching_policy_decision(
        profile,
        bundle["human_decision_records"],
        path="adopted_profile",
        expected_scope_digest=bundle["scope_digest"],
    ):
        reasons.add("effective_policy_decision_mismatch")
    if bundle["time_trust"] != "trusted":
        reasons.add("assessment_time_untrusted")
    if any(item["blocking"] for item in bundle["unresolved_scope"]):
        reasons.add("blocking_unresolved_scope")
    if not _review_usable(
        bundle["independent_review_record"],
        assessment_id=str(bundle["assessment_id"]),
        assessment_version=str(bundle["assessment_version"]),
        basis_digest=basis_digest,
        assessed_at=str(bundle["assessed_at"]),
        evidence_by_id=evidence_by_id,
        max_age_seconds=int(profile["max_evidence_age_seconds"]),
        expected_scope_digest=bundle["scope_digest"],
    ):
        reasons.add("independent_review_not_established")

    purposes = {str(item["purpose_id"]): item for item in profile["purposes"]}
    destinations = {
        str(item["destination_id"]): item
        for item in profile["destination_allowlist"]
    }
    retention_rules = {
        str(item["retention_id"]): item for item in profile["retention_rules"]
    }
    retention_observations = {
        str(item["component_ref"]): item
        for item in contract["retention_observations"]
    }
    data_items = {str(item["data_id"]): item for item in contract["data_items"]}
    components = {
        str(item["component_id"]): item for item in contract["components"]
    }
    classification = profile["classification_policy"]

    if "secret" not in classification["prohibited_log_classes"]:
        reasons.add("profile_secret_log_prohibition_missing")

    for data in data_items.values():
        if not _graph_reaches_retention(
            str(data["data_id"]),
            str(data["source_component_ref"]),
            contract["declared_flows"],
            components,
        ):
            reasons.add("information_path_does_not_close_at_retention")

    for component in components.values():
        kind = str(component["component_kind"])
        if component["destination_ref"] is not None:
            destination = destinations.get(str(component["destination_ref"]))
            if destination is None:
                reasons.add("destination_not_allowlisted")
            elif (
                destination["component_kind"] != kind
                or destination["external"] != component["external"]
            ):
                reasons.add("destination_allowlist_binding_mismatch")
        elif kind != "source":
            reasons.add("destination_not_allowlisted")
        if component["persistent"] and not component["retention_rule_ref"]:
            reasons.add("retention_rule_missing")
        if (
            component["retention_rule_ref"] is not None
            and component["retention_rule_ref"] not in retention_rules
        ):
            reasons.add("retention_rule_missing")
        if component["privileged"] and not component["least_privilege_scopes"]:
            reasons.add("least_privilege_scope_missing")
        if kind == "provider" and component["credential_binding_ref"] is None:
            reasons.add("provider_credential_binding_missing")
        if component["persistent"] and component["retention_rule_ref"]:
            observation = retention_observations.get(str(component["component_id"]))
            rule = retention_rules.get(str(component["retention_rule_ref"]))
            if observation is None or rule is None:
                reasons.add("retention_effect_unproved")
            else:
                if (
                    observation["retention_rule_ref"] != rule["retention_id"]
                    or observation["retention_rule_digest"]
                    != rule["retention_digest"]
                    or int(observation["configured_maximum_seconds"])
                    > int(rule["maximum_seconds"])
                ):
                    reasons.add("retention_effect_unproved")
                observed_kinds = {
                    str(evidence_by_id[ref]["evidence_kind"])
                    for ref in observation["evidence_refs"]
                    if ref in evidence_by_id
                }
                required_kinds = {"retention_test"}
                if rule["deletion_evidence_required"]:
                    required_kinds.add("deletion_test")
                    if not observation["deletion_evidence_present"]:
                        reasons.add("deletion_evidence_missing")
                if not required_kinds.issubset(observed_kinds) or not _refs_usable(
                    str(observation["observation_id"]),
                    list(observation["evidence_refs"]),
                    evidence_by_id,
                    assessed_at=str(bundle["assessed_at"]),
                    max_age_seconds=int(profile["max_evidence_age_seconds"]),
                    expected_scope_digest=bundle["scope_digest"],
                    allowed_evidence_kinds=frozenset(
                        {"retention_test", "deletion_test"}
                    ),
                ):
                    reasons.add("retention_effect_unproved")

    for flow in contract["declared_flows"]:
        data = data_items.get(str(flow["data_ref"]))
        source = components.get(str(flow["from_component_ref"]))
        target = components.get(str(flow["to_component_ref"]))
        if data is None or source is None or target is None:
            continue
        data_class = str(data["data_class"])
        pair = (str(source["component_kind"]), str(target["component_kind"]))
        if pair not in ALLOWED_FLOW_PAIRS:
            reasons.add("information_flow_stage_invalid")
        purpose = purposes.get(str(flow["purpose_ref"]))
        if (
            purpose is None
            or flow["purpose_ref"] not in data["allowed_purpose_refs"]
            or data_class not in purpose["allowed_data_classes"]
        ):
            reasons.add("purpose_not_allowed")
        if not set(flow["transmitted_fields"]).issubset(set(data["field_names"])):
            reasons.add("transmitted_field_outside_inventory")
        if flow["minimization"] != "applied":
            reasons.add("minimization_not_established")
        if (
            data_class in classification["redaction_required_classes"]
            and flow["redaction"] != "applied"
        ):
            reasons.add("redaction_not_established")
        if (
            data_class in classification["encryption_in_transit_required_classes"]
            and flow["encryption_in_transit"] != "applied"
        ):
            reasons.add("transport_encryption_not_established")
        if (
            target["persistent"]
            and data_class
            in classification["encryption_at_rest_required_classes"]
            and target["encryption_at_rest"] != "applied"
        ):
            reasons.add("at_rest_encryption_not_established")
        if (
            target["component_kind"] == "log"
            and data_class in classification["prohibited_log_classes"]
        ):
            reasons.add("prohibited_data_class_logged")
        if target["external"]:
            destination = destinations.get(str(target["destination_ref"]))
            if data_class not in classification["external_transmission_allowed_classes"]:
                reasons.add("external_data_class_not_allowed")
            if (
                destination is None
                or data_class not in destination["allowed_data_classes"]
                or flow["purpose_ref"] not in destination["allowed_purpose_refs"]
            ):
                reasons.add("external_destination_scope_not_allowed")
        destination = (
            None
            if target["destination_ref"] is None
            else destinations.get(str(target["destination_ref"]))
        )
        if (
            destination is None
            or data_class not in destination["allowed_data_classes"]
            or flow["purpose_ref"] not in destination["allowed_purpose_refs"]
        ):
            reasons.add("destination_scope_not_allowed")
        if target["component_kind"] == "provider" and (
            flow["credential_binding_ref"] is None
            or flow["credential_binding_ref"] != target["credential_binding_ref"]
        ):
            reasons.add("provider_credential_binding_missing")
        if target["retention_rule_ref"]:
            rule = retention_rules.get(str(target["retention_rule_ref"]))
            if rule is None or data_class not in rule["data_classes"]:
                reasons.add("retention_rule_scope_mismatch")
        if not _refs_usable(
            str(flow["flow_id"]),
            list(flow["evidence_refs"]),
            evidence_by_id,
            assessed_at=str(bundle["assessed_at"]),
            max_age_seconds=int(profile["max_evidence_age_seconds"]),
            expected_scope_digest=bundle["scope_digest"],
            allowed_evidence_kinds=frozenset(
                {"information_flow_observation"}
            ),
        ):
            reasons.add("flow_evidence_not_current_or_trusted")

    for observation in contract["flow_observations"]:
        if not _refs_usable(
            str(observation["observation_id"]),
            list(observation["evidence_refs"]),
            evidence_by_id,
            assessed_at=str(bundle["assessed_at"]),
            max_age_seconds=int(profile["max_evidence_age_seconds"]),
            expected_scope_digest=bundle["scope_digest"],
            allowed_evidence_kinds=frozenset(
                {"information_flow_observation"}
            ),
        ):
            reasons.add("flow_inventory_evidence_not_current_or_trusted")
    for result in contract["control_results"]:
        if result["status"] != "satisfied":
            reasons.add(f"control_{result['control_kind']}_not_satisfied")
        if not _refs_usable(
            str(result["control_ref"]),
            list(result["evidence_refs"]),
            evidence_by_id,
            assessed_at=str(bundle["assessed_at"]),
            max_age_seconds=int(profile["max_evidence_age_seconds"]),
            expected_scope_digest=bundle["scope_digest"],
            allowed_evidence_kinds=CONTROL_EVIDENCE_KINDS[
                str(result["control_kind"])
            ],
        ):
            reasons.add("control_evidence_not_current_or_trusted")
    for assessment in contract["trigger_assessments"]:
        if assessment["status"] != "not_observed":
            reasons.add("requalification_trigger_observed_or_unresolved")
        trigger = next(
            (
                item
                for item in profile["requalification_triggers"]
                if item["trigger_id"] == assessment["trigger_ref"]
            ),
            None,
        )
        required_evidence_kinds = (
            frozenset()
            if trigger is None
            else frozenset(str(item) for item in trigger["required_evidence_kinds"])
        )
        observed_evidence_kinds = {
            str(evidence_by_id[ref]["evidence_kind"])
            for ref in assessment["evidence_refs"]
            if ref in evidence_by_id
        }
        if (
            not required_evidence_kinds.issubset(observed_evidence_kinds)
            or not _refs_usable(
                str(assessment["trigger_ref"]),
                list(assessment["evidence_refs"]),
                evidence_by_id,
                assessed_at=str(bundle["assessed_at"]),
                max_age_seconds=int(profile["max_evidence_age_seconds"]),
                expected_scope_digest=bundle["scope_digest"],
                allowed_evidence_kinds=required_evidence_kinds,
            )
        ):
            reasons.add("trigger_evidence_not_current_or_trusted")
    return sorted(reasons)


def _nonapplicability_reasons_and_triggers(
    bundle: Mapping[str, Any],
    *,
    basis_digest: Mapping[str, Any],
) -> tuple[list[str], list[str]]:
    contract = bundle["path_contract"]
    profile = contract["profile"]
    evidence_by_id = {
        str(item["evidence_id"]): item for item in bundle["evidence_observations"]
    }
    reasons: set[str] = set()
    for manifest in bundle["scope_manifests"]:
        if not _refs_usable(
            str(manifest["manifest_id"]),
            list(manifest["inventory_evidence_refs"]),
            evidence_by_id,
            assessed_at=str(bundle["assessed_at"]),
            max_age_seconds=int(profile["max_evidence_age_seconds"]),
            expected_scope_digest=bundle["scope_digest"],
            allowed_evidence_kinds=frozenset({"scope_inventory"}),
            expected_observer_ref=manifest["inventory_authority_ref"],
        ):
            reasons.add("scope_denominator_evidence_not_current_or_trusted")
    if profile["status"] != "adopted":
        reasons.add("profile_not_adopted")
    elif not _matching_policy_decision(
        profile,
        bundle["human_decision_records"],
        path="verified_nonapplicability",
        expected_scope_digest=bundle["scope_digest"],
    ):
        reasons.add("effective_policy_decision_mismatch")
    if bundle["time_trust"] != "trusted":
        reasons.add("assessment_time_untrusted")
    if bundle["unresolved_scope"]:
        reasons.add("unresolved_scope_prevents_nonapplicability")
    if bundle["claimed_environment"] != "local_fixture":
        reasons.add("scope_outside_local_fixture")
    if not _review_usable(
        bundle["independent_review_record"],
        assessment_id=str(bundle["assessment_id"]),
        assessment_version=str(bundle["assessment_version"]),
        basis_digest=basis_digest,
        assessed_at=str(bundle["assessed_at"]),
        evidence_by_id=evidence_by_id,
        max_age_seconds=int(profile["max_evidence_age_seconds"]),
        expected_scope_digest=bundle["scope_digest"],
    ):
        reasons.add("independent_review_not_established")
    derived_conditions = _derived_nonapplicability_conditions(
        bundle["scope_manifests"]
    )
    for result in contract["condition_results"]:
        if result["status"] != "confirmed":
            reasons.add(f"condition_{result['condition_id']}_not_confirmed")
        if not derived_conditions[str(result["condition_id"])]:
            reasons.add(f"condition_{result['condition_id']}_contradicted_by_scope")
        if result["scope_digest"] != bundle["scope_digest"]:
            reasons.add("condition_scope_binding_mismatch")
        if not _refs_usable(
            str(result["condition_id"]),
            list(result["evidence_refs"]),
            evidence_by_id,
            assessed_at=str(bundle["assessed_at"]),
            max_age_seconds=int(profile["max_evidence_age_seconds"]),
            expected_scope_digest=bundle["scope_digest"],
            allowed_evidence_kinds=CONDITION_EVIDENCE_KINDS[
                str(result["condition_id"])
            ],
        ):
            reasons.add("condition_evidence_not_current_or_trusted")
    restart = contract["restart_test"]
    if not _refs_usable(
        str(restart["test_id"]),
        list(restart["evidence_refs"]),
        evidence_by_id,
        assessed_at=str(bundle["assessed_at"]),
        max_age_seconds=int(profile["max_evidence_age_seconds"]),
        expected_scope_digest=bundle["scope_digest"],
        allowed_evidence_kinds=frozenset({"restart_test"}),
    ):
        reasons.add("restart_evidence_not_current_or_trusted")
    try:
        if not (
            restart["time_trust"] == "trusted"
            and _parse_time(str(restart["observed_at"]))
            <= _parse_time(str(bundle["assessed_at"]))
            <= _parse_time(str(restart["expires_at"]))
            and (
                _parse_time(str(bundle["assessed_at"]))
                - _parse_time(str(restart["observed_at"]))
            ).total_seconds()
            <= int(profile["max_evidence_age_seconds"])
        ):
            reasons.add("restart_test_not_current_or_trusted")
    except (TypeError, ValueError):
        reasons.add("restart_test_not_current_or_trusted")
    triggers = _reactivation_from_scope(
        manifests=bundle["scope_manifests"],
        claimed_environment=str(bundle["claimed_environment"]),
        restart_test=restart,
    )
    return sorted(reasons), triggers


def _compute_result(
    bundle: Mapping[str, Any],
    *,
    basis_digest: Mapping[str, Any],
) -> dict[str, Any]:
    contract = bundle["path_contract"]
    profile = contract["profile"]
    if bundle["path"] == "adopted_profile":
        reasons = _adopted_profile_reasons(bundle, basis_digest=basis_digest)
        triggers: list[str] = []
        status = (
            "declared_profile_internally_consistent"
            if not reasons
            else "not_established"
        )
    else:
        reasons, triggers = _nonapplicability_reasons_and_triggers(
            bundle, basis_digest=basis_digest
        )
        if triggers:
            status = "reactivated"
        elif reasons:
            status = "not_established"
        else:
            status = "declared_nonapplicability_internally_consistent"
    material = {
        "path": bundle["path"],
        "status": status,
        "reason_codes": sorted(set(reasons)),
        "unproved_claim_codes": list(UNPROVED_CLAIM_CODES),
        "reactivation_triggers": sorted(set(triggers)),
        "profile_ref": _profile_ref(profile),
        "scope_digest": copy.deepcopy(bundle["scope_digest"]),
        "review_basis_digest": copy.deepcopy(dict(basis_digest)),
        "unresolved_scope_refs": sorted(
            str(item["scope_id"]) for item in bundle["unresolved_scope"]
        ),
    }
    return {**material, "result_digest": digest_value(material)}


def build_secure_operation_assessment(
    *,
    assessment_id: str,
    assessment_version: str,
    path: str,
    assessed_at: str,
    time_trust: str,
    claimed_environment: str,
    scope_manifests: Iterable[Mapping[str, Any]],
    evidence_observations: Iterable[Mapping[str, Any]],
    human_decision_records: Iterable[Mapping[str, Any]],
    unresolved_scope: Iterable[Mapping[str, Any]],
    path_contract: Mapping[str, Any],
    independent_review_record: Mapping[str, Any] | None = None,
    limitations: Iterable[str] = _DEFAULT_LIMITATIONS,
) -> dict[str, Any]:
    manifests = _sorted_dicts(scope_manifests, "manifest_kind", "manifest_id")
    base = {
        "schema_version": SCHEMA_VERSION,
        "assessment_id": assessment_id,
        "assessment_version": assessment_version,
        "path": path,
        "assessed_at": assessed_at,
        "time_trust": time_trust,
        "claimed_environment": claimed_environment,
        "scope_manifests": manifests,
        "scope_digest": scope_digest(manifests),
        "evidence_observations": _sorted_dicts(
            evidence_observations, "evidence_id"
        ),
        "human_decision_records": _sorted_dicts(
            human_decision_records, "decision_id"
        ),
        "unresolved_scope": _sorted_dicts(unresolved_scope, "scope_id"),
        "path_contract": copy.deepcopy(dict(path_contract)),
        "independent_open_dimensions": copy.deepcopy(_OPEN_DIMENSIONS),
        "authority_boundary": copy.deepcopy(_AUTHORITY_BOUNDARY),
        "limitations": sorted(set(limitations)),
    }
    contract = base["path_contract"]
    if (
        len(base["evidence_observations"]) > MAX_EVIDENCE
        or sum(len(item["entries"]) for item in manifests) > MAX_SCOPE_ENTRIES
        or len(contract.get("components", [])) > MAX_COMPONENTS
        or len(contract.get("declared_flows", [])) > MAX_FLOWS
    ):
        raise SecureOperationValidationError(
            [
                {
                    "code": "input_resource_limit_exceeded",
                    "location": "$",
                    "message": "secure-operation collection limit exceeded",
                }
            ]
        )
    basis_digest = digest_value(base)
    with_review = {
        **base,
        "review_basis_digest": basis_digest,
        "independent_review_record": (
            None
            if independent_review_record is None
            else copy.deepcopy(dict(independent_review_record))
        ),
    }
    result = _compute_result(with_review, basis_digest=basis_digest)
    material = {**with_review, "result": result}
    return {**material, "assessment_digest": digest_value(material)}


def _check_nested_digest(
    errors: list[dict[str, str]],
    value: Mapping[str, Any],
    *,
    digest_field: str,
    code: str,
    location: str,
) -> None:
    if value[digest_field] != digest_value(_without(value, digest_field)):
        _add(errors, code, location, f"{digest_field} does not replay")


def _profile_digest_errors(
    profile: Mapping[str, Any],
    errors: list[dict[str, str]],
    location: str,
) -> None:
    basis = _without(
        profile,
        "profile_basis_digest",
        "status",
        "decision_record_ref",
        "profile_digest",
    )
    if profile["profile_basis_digest"] != digest_value(basis):
        _add(
            errors,
            "profile_basis_digest_mismatch",
            f"{location}.profile_basis_digest",
            "profile basis changed after human-decision binding",
        )
    if profile["profile_digest"] != digest_value(
        _without(profile, "profile_digest")
    ):
        _add(
            errors,
            "profile_digest_mismatch",
            f"{location}.profile_digest",
            "profile changed after binding",
        )


def _decision_integrity_errors(
    bundle: Mapping[str, Any],
    profile: Mapping[str, Any],
    errors: list[dict[str, str]],
) -> None:
    decisions = bundle["human_decision_records"]
    ids = [str(item["decision_id"]) for item in decisions]
    for duplicate in sorted(_duplicates(ids)):
        _add(errors, "duplicate_human_decision", "$.human_decision_records", duplicate)
    for index, decision in enumerate(decisions):
        _check_nested_digest(
            errors,
            decision,
            digest_field="decision_digest",
            code="human_decision_digest_mismatch",
            location=f"$.human_decision_records.{index}.decision_digest",
        )
        if _parse_time(str(decision["decided_at"])) > _parse_time(
            str(bundle["assessed_at"])
        ):
            _add(
                errors,
                "human_decision_after_assessment",
                f"$.human_decision_records.{index}.decided_at",
                decision["decision_id"],
            )
    relevant = [
        item
        for item in decisions
        if item["target_id"] == profile["profile_id"]
        and item["target_version"] == profile["profile_version"]
        and item["target_digest"] == profile["profile_basis_digest"]
        and item["target_scope_digest"] == bundle["scope_digest"]
    ]
    sequence_counts: dict[int, int] = {}
    for decision in relevant:
        sequence = int(decision["decision_sequence"])
        sequence_counts[sequence] = sequence_counts.get(sequence, 0) + 1
    if any(count > 1 for count in sequence_counts.values()):
        _add(
            errors,
            "conflicting_policy_decisions",
            "$.human_decision_records",
            "effective decision sequence is not unique for the same profile basis and scope",
        )
    ordered = sorted(relevant, key=lambda item: int(item["decision_sequence"]))
    if any(
        _parse_time(str(later["decided_at"]))
        < _parse_time(str(earlier["decided_at"]))
        for earlier, later in zip(ordered, ordered[1:])
    ):
        _add(
            errors,
            "policy_decision_order_mismatch",
            "$.human_decision_records",
            "decision sequence and decision time disagree",
        )
    if profile["status"] == "pending":
        if profile["decision_record_ref"] is not None:
            _add(
                errors,
                "pending_profile_has_decision",
                "$.path_contract.profile.decision_record_ref",
                "pending profile cannot imply adoption or retirement",
            )
    elif not _matching_policy_decision(
        profile,
        decisions,
        path=str(bundle["path"]),
        expected_scope_digest=bundle["scope_digest"],
    ):
        _add(
            errors,
            "effective_policy_decision_mismatch",
            "$.path_contract.profile.decision_record_ref",
            "profile status must follow the latest unique decision for the exact basis and scope",
        )


def _claim_binding(
    errors: list[dict[str, str]],
    *,
    parent_id: str,
    evidence_refs: Sequence[str],
    evidence_by_id: Mapping[str, Mapping[str, Any]],
    location: str,
    allowed_evidence_kinds: frozenset[str] | None = None,
    expected_observer_ref: Mapping[str, Any] | None = None,
    wrong_kind_code: str = "evidence_kind_not_allowed_for_claim",
    observer_mismatch_code: str = "reviewer_evidence_identity_mismatch",
) -> None:
    for evidence_ref in evidence_refs:
        evidence = evidence_by_id.get(str(evidence_ref))
        if evidence is None:
            _add(errors, "dangling_evidence_ref", location, str(evidence_ref))
            continue
        if parent_id not in evidence["claim_refs"]:
            _add(
                errors,
                "evidence_claim_binding_mismatch",
                location,
                f"{evidence_ref} does not claim {parent_id}",
            )
        if (
            allowed_evidence_kinds is not None
            and evidence["evidence_kind"] not in allowed_evidence_kinds
        ):
            _add(
                errors,
                wrong_kind_code,
                location,
                f"{evidence_ref} has kind {evidence['evidence_kind']}",
            )
        if (
            expected_observer_ref is not None
            and evidence["observer"]["observer_ref"] != expected_observer_ref
        ):
            _add(
                errors,
                observer_mismatch_code,
                location,
                f"{evidence_ref} observer does not match the review identity",
            )


def secure_operation_errors(
    bundle: Mapping[str, Any],
) -> tuple[dict[str, str], ...]:
    """Return schema, integrity, closure, and deterministic replay failures."""

    errors: list[dict[str, str]] = []
    evidence_candidate = bundle.get("evidence_observations", [])
    manifests_candidate = bundle.get("scope_manifests", [])
    contract_candidate = bundle.get("path_contract", {})
    entry_count = (
        sum(
            len(item.get("entries", []))
            for item in manifests_candidate
            if isinstance(item, Mapping)
        )
        if isinstance(manifests_candidate, Sequence)
        else 0
    )
    component_count = (
        len(contract_candidate.get("components", []))
        if isinstance(contract_candidate, Mapping)
        else 0
    )
    flow_count = (
        len(contract_candidate.get("declared_flows", []))
        if isinstance(contract_candidate, Mapping)
        else 0
    )
    if (
        isinstance(evidence_candidate, Sequence)
        and len(evidence_candidate) > MAX_EVIDENCE
        or entry_count > MAX_SCOPE_ENTRIES
        or component_count > MAX_COMPONENTS
        or flow_count > MAX_FLOWS
    ):
        _add(
            errors,
            "input_resource_limit_exceeded",
            "$",
            "secure-operation collection limit exceeded",
        )
        return tuple(errors)
    schema_failures = sorted(
        _validator().iter_errors(bundle), key=lambda item: list(item.absolute_path)
    )
    for failure in schema_failures:
        _add(
            errors,
            "schema_validation_failed",
            _schema_location(failure.absolute_path),
            failure.message,
        )
    if schema_failures:
        return tuple(errors)

    try:
        if bundle["assessment_digest"] != digest_value(
            _without(bundle, "assessment_digest")
        ):
            _add(
                errors,
                "assessment_digest_mismatch",
                "$.assessment_digest",
                "assessment changed after binding",
            )
        if bundle["path"] != bundle["path_contract"]["kind"]:
            _add(
                errors,
                "path_contract_mismatch",
                "$.path_contract.kind",
                "root path and typed path contract differ",
            )
        _parse_time(str(bundle["assessed_at"]))

        manifests = bundle["scope_manifests"]
        manifest_kinds = [str(item["manifest_kind"]) for item in manifests]
        for duplicate in sorted(_duplicates(manifest_kinds)):
            _add(errors, "duplicate_manifest_kind", "$.scope_manifests", duplicate)
        if set(manifest_kinds) != set(MANIFEST_KINDS):
            _add(
                errors,
                "scope_manifest_coverage_mismatch",
                "$.scope_manifests",
                f"expected {list(MANIFEST_KINDS)}, found {sorted(set(manifest_kinds))}",
            )
        entry_ids: list[str] = []
        entry_by_id: dict[str, Mapping[str, Any]] = {}
        for manifest_index, manifest in enumerate(manifests):
            location = f"$.scope_manifests.{manifest_index}"
            _check_nested_digest(
                errors,
                manifest,
                digest_field="manifest_digest",
                code="manifest_digest_mismatch",
                location=f"{location}.manifest_digest",
            )
            local_ids = [str(item["entry_id"]) for item in manifest["entries"]]
            for duplicate in sorted(_duplicates(local_ids)):
                _add(errors, "duplicate_scope_entry", location, duplicate)
            for entry_index, entry in enumerate(manifest["entries"]):
                entry_location = f"{location}.entries.{entry_index}"
                entry_id = str(entry["entry_id"])
                entry_ids.append(entry_id)
                entry_by_id[entry_id] = entry
                _check_nested_digest(
                    errors,
                    entry,
                    digest_field="entry_digest",
                    code="scope_entry_digest_mismatch",
                    location=f"{entry_location}.entry_digest",
                )
                if entry["entry_kind"] != manifest["manifest_kind"]:
                    _add(
                        errors,
                        "scope_entry_kind_mismatch",
                        entry_location,
                        entry_id,
                    )
        for duplicate in sorted(_duplicates(entry_ids)):
            _add(errors, "duplicate_scope_entry", "$.scope_manifests", duplicate)
        expected_scope_digest = scope_digest(manifests)
        if bundle["scope_digest"] != expected_scope_digest:
            _add(
                errors,
                "scope_digest_mismatch",
                "$.scope_digest",
                "scope manifests changed after binding",
            )

        evidence = bundle["evidence_observations"]
        evidence_ids = [str(item["evidence_id"]) for item in evidence]
        for duplicate in sorted(_duplicates(evidence_ids)):
            _add(errors, "duplicate_evidence", "$.evidence_observations", duplicate)
        evidence_by_id = {str(item["evidence_id"]): item for item in evidence}
        claim_universe: set[str] = set(entry_ids)
        used_evidence_refs: set[str] = set()
        for index, item in enumerate(evidence):
            location = f"$.evidence_observations.{index}"
            _check_nested_digest(
                errors,
                item,
                digest_field="evidence_digest",
                code="evidence_digest_mismatch",
                location=f"{location}.evidence_digest",
            )
            if item["scope_digest"] != expected_scope_digest:
                _add(errors, "evidence_scope_mismatch", location, item["evidence_id"])
            if _parse_time(str(item["observed_at"])) > _parse_time(
                str(item["expires_at"])
            ):
                _add(errors, "evidence_time_order_invalid", location, item["evidence_id"])
            if not _evidence_trust_tuple_valid(item):
                _add(
                    errors,
                    "evidence_trust_relationship_mismatch",
                    f"{location}.observer",
                    item["evidence_id"],
                )

        unresolved_ids = [str(item["scope_id"]) for item in bundle["unresolved_scope"]]
        for duplicate in sorted(_duplicates(unresolved_ids)):
            _add(errors, "duplicate_unresolved_scope", "$.unresolved_scope", duplicate)
        claim_universe.update(unresolved_ids)
        for index, item in enumerate(bundle["unresolved_scope"]):
            refs = [str(value) for value in item["evidence_refs"]]
            used_evidence_refs.update(refs)
            _claim_binding(
                errors,
                parent_id=str(item["scope_id"]),
                evidence_refs=refs,
                evidence_by_id=evidence_by_id,
                location=f"$.unresolved_scope.{index}.evidence_refs",
            )

        contract = bundle["path_contract"]
        profile = contract["profile"]
        _profile_digest_errors(profile, errors, "$.path_contract.profile")
        _decision_integrity_errors(bundle, profile, errors)

        if bundle["path"] == "adopted_profile":
            for collection, id_field, digest_field, code in (
                (profile["purposes"], "purpose_id", "purpose_digest", "purpose_digest_mismatch"),
                (profile["destination_allowlist"], "destination_id", "destination_digest", "destination_digest_mismatch"),
                (profile["retention_rules"], "retention_id", "retention_digest", "retention_digest_mismatch"),
                (profile["control_profiles"], "control_id", "control_digest", "control_profile_digest_mismatch"),
                (profile["requalification_triggers"], "trigger_id", "trigger_digest", "trigger_digest_mismatch"),
                (contract["data_items"], "data_id", "data_digest", "data_digest_mismatch"),
                (contract["components"], "component_id", "component_digest", "component_digest_mismatch"),
                (contract["declared_flows"], "flow_id", "flow_digest", "flow_digest_mismatch"),
                (contract["flow_observations"], "observation_id", "observation_digest", "flow_observation_digest_mismatch"),
                (contract["retention_observations"], "observation_id", "observation_digest", "retention_observation_digest_mismatch"),
                (contract["control_results"], "control_ref", "result_digest", "control_result_digest_mismatch"),
                (contract["trigger_assessments"], "trigger_ref", "assessment_digest", "trigger_assessment_digest_mismatch"),
            ):
                ids = [str(item[id_field]) for item in collection]
                for duplicate in sorted(_duplicates(ids)):
                    _add(errors, f"duplicate_{id_field}", "$.path_contract", duplicate)
                for index, item in enumerate(collection):
                    _check_nested_digest(
                        errors,
                        item,
                        digest_field=digest_field,
                        code=code,
                        location=f"$.path_contract.{id_field}.{index}.{digest_field}",
                    )

            purpose_ids = {str(item["purpose_id"]) for item in profile["purposes"]}
            for destination in profile["destination_allowlist"]:
                if not set(destination["allowed_purpose_refs"]).issubset(purpose_ids):
                    _add(
                        errors,
                        "destination_dangling_purpose",
                        "$.path_contract.profile.destination_allowlist",
                        destination["destination_id"],
                    )
            control_by_id = {
                str(item["control_id"]): item for item in profile["control_profiles"]
            }
            control_kinds = {str(item["control_kind"]) for item in profile["control_profiles"]}
            if control_kinds != set(CONTROL_KINDS):
                _add(errors, "control_profile_coverage_mismatch", "$.path_contract.profile.control_profiles", str(sorted(control_kinds)))
            trigger_by_id = {
                str(item["trigger_id"]): item
                for item in profile["requalification_triggers"]
            }
            trigger_dimensions = {
                str(item["dimension"]) for item in profile["requalification_triggers"]
            }
            if trigger_dimensions != set(REQUALIFICATION_DIMENSIONS):
                _add(errors, "requalification_trigger_coverage_mismatch", "$.path_contract.profile.requalification_triggers", str(sorted(trigger_dimensions)))
            if "secret" not in profile["classification_policy"]["prohibited_log_classes"]:
                _add(errors, "profile_secret_log_prohibition_missing", "$.path_contract.profile.classification_policy.prohibited_log_classes", "secret must remain prohibited from logs")

            data_by_id = {str(item["data_id"]): item for item in contract["data_items"]}
            component_by_id = {
                str(item["component_id"]): item for item in contract["components"]
            }
            runtime_entries = {
                entry_id: entry
                for entry_id, entry in entry_by_id.items()
                if entry["entry_kind"] == "runtime_path"
            }
            subject_entries = {
                entry_id: entry
                for entry_id, entry in entry_by_id.items()
                if entry["entry_kind"] == "subject"
            }
            for data in contract["data_items"]:
                subject = subject_entries.get(str(data["subject_entry_ref"]))
                if subject is None:
                    _add(errors, "data_subject_binding_missing", "$.path_contract.data_items", data["data_id"])
                else:
                    observed_rank = max(
                        DATA_CLASS_RANK[str(value)]
                        for value in subject["attributes"]["data_classes"]
                    )
                    if DATA_CLASS_RANK[str(data["data_class"])] < observed_rank:
                        _add(errors, "classification_laundering", "$.path_contract.data_items", data["data_id"])
                source = component_by_id.get(str(data["source_component_ref"]))
                if source is None or source["component_kind"] != "source":
                    _add(errors, "data_source_component_invalid", "$.path_contract.data_items", data["data_id"])
                if not set(data["allowed_purpose_refs"]).issubset(purpose_ids):
                    _add(errors, "data_dangling_purpose", "$.path_contract.data_items", data["data_id"])
            for component in contract["components"]:
                entry = runtime_entries.get(str(component["runtime_entry_ref"]))
                if entry is None:
                    _add(errors, "component_runtime_binding_missing", "$.path_contract.components", component["component_id"])
                    continue
                attributes = entry["attributes"]
                expected_external = attributes["external_provider"] or attributes["execution_location"] == "external"
                expected_persistent = attributes["durable"] or attributes["persistent_log"] or attributes["persistent_artifact"]
                expected_credential = component["credential_binding_ref"] is not None
                if (
                    component["external"] != expected_external
                    or component["persistent"] != expected_persistent
                    or component["privileged"] != attributes["privileged"]
                    or expected_credential != attributes["credential_present"]
                ):
                    _add(errors, "component_runtime_binding_mismatch", "$.path_contract.components", component["component_id"])

            runtime_component_refs = [
                str(item["runtime_entry_ref"]) for item in contract["components"]
            ]
            if (
                set(runtime_component_refs) != set(runtime_entries)
                or _duplicates(runtime_component_refs)
            ):
                _add(
                    errors,
                    "runtime_component_exact_coverage_mismatch",
                    "$.path_contract.components",
                    "every runtime-path entry must bind to exactly one flow component",
                )
            subject_data_refs = [
                str(item["subject_entry_ref"]) for item in contract["data_items"]
            ]
            if set(subject_data_refs) != set(subject_entries):
                _add(
                    errors,
                    "subject_data_coverage_mismatch",
                    "$.path_contract.data_items",
                    "every subject entry must be represented by at least one data item",
                )

            retention_observation_components = [
                str(item["component_ref"])
                for item in contract["retention_observations"]
            ]
            for duplicate in sorted(_duplicates(retention_observation_components)):
                _add(
                    errors,
                    "duplicate_retention_observation",
                    "$.path_contract.retention_observations",
                    duplicate,
                )
            retention_by_id = {
                str(item["retention_id"]): item
                for item in profile["retention_rules"]
            }
            for observation in contract["retention_observations"]:
                component = component_by_id.get(str(observation["component_ref"]))
                rule = retention_by_id.get(str(observation["retention_rule_ref"]))
                if (
                    component is None
                    or not component["persistent"]
                    or component["retention_rule_ref"]
                    != observation["retention_rule_ref"]
                    or rule is None
                    or observation["retention_rule_digest"]
                    != rule["retention_digest"]
                ):
                    _add(
                        errors,
                        "retention_observation_binding_mismatch",
                        "$.path_contract.retention_observations",
                        observation["observation_id"],
                    )
                refs = [str(value) for value in observation["evidence_refs"]]
                used_evidence_refs.update(refs)
                claim_universe.add(str(observation["observation_id"]))
                _claim_binding(
                    errors,
                    parent_id=str(observation["observation_id"]),
                    evidence_refs=refs,
                    evidence_by_id=evidence_by_id,
                    location="$.path_contract.retention_observations.evidence_refs",
                    allowed_evidence_kinds=frozenset(
                        {"retention_test", "deletion_test"}
                    ),
                )
                observed_kinds = {
                    str(evidence_by_id[ref]["evidence_kind"])
                    for ref in refs
                    if ref in evidence_by_id
                }
                required_kinds = {"retention_test"}
                if rule is not None and rule["deletion_evidence_required"]:
                    required_kinds.add("deletion_test")
                if not required_kinds.issubset(observed_kinds):
                    _add(
                        errors,
                        "retention_required_evidence_kind_missing",
                        "$.path_contract.retention_observations.evidence_refs",
                        observation["observation_id"],
                    )

            flow_by_id = {str(item["flow_id"]): item for item in contract["declared_flows"]}
            observation_refs = [str(item["flow_ref"]) for item in contract["flow_observations"]]
            for duplicate in sorted(_duplicates(observation_refs)):
                _add(errors, "duplicate_flow_observation", "$.path_contract.flow_observations", duplicate)
            if set(observation_refs) != set(flow_by_id):
                _add(errors, "flow_exact_coverage_mismatch", "$.path_contract.flow_observations", "every declared flow must have exactly one observation")
            source_component_refs = {
                str(item["source_component_ref"]) for item in contract["data_items"]
            }
            component_ids = set(component_by_id)
            from_refs = {
                str(item["from_component_ref"])
                for item in contract["declared_flows"]
            }
            to_refs = {
                str(item["to_component_ref"])
                for item in contract["declared_flows"]
            }
            retention_component_refs = {
                str(item["component_id"])
                for item in contract["components"]
                if item["component_kind"] == "retention"
            }
            if (
                not source_component_refs.issubset(from_refs)
                or not (component_ids - source_component_refs).issubset(to_refs)
                or not (component_ids - retention_component_refs).issubset(from_refs)
            ):
                _add(
                    errors,
                    "component_flow_coverage_mismatch",
                    "$.path_contract.declared_flows",
                    "every component must participate in a source-to-retention flow",
                )
            for flow in contract["declared_flows"]:
                if (
                    flow["data_ref"] not in data_by_id
                    or flow["from_component_ref"] not in component_by_id
                    or flow["to_component_ref"] not in component_by_id
                ):
                    _add(errors, "flow_reference_not_closed", "$.path_contract.declared_flows", flow["flow_id"])
                refs = [str(value) for value in flow["evidence_refs"]]
                used_evidence_refs.update(refs)
                claim_universe.add(str(flow["flow_id"]))
                _claim_binding(
                    errors,
                    parent_id=str(flow["flow_id"]),
                    evidence_refs=refs,
                    evidence_by_id=evidence_by_id,
                    location="$.path_contract.declared_flows.evidence_refs",
                    allowed_evidence_kinds=frozenset(
                        {"information_flow_observation"}
                    ),
                )
            for observation in contract["flow_observations"]:
                flow = flow_by_id.get(str(observation["flow_ref"]))
                if flow is None or observation["flow_digest"] != flow["flow_digest"]:
                    _add(errors, "flow_observation_substitution", "$.path_contract.flow_observations", observation["observation_id"])
                refs = [str(value) for value in observation["evidence_refs"]]
                used_evidence_refs.update(refs)
                claim_universe.add(str(observation["observation_id"]))
                _claim_binding(
                    errors,
                    parent_id=str(observation["observation_id"]),
                    evidence_refs=refs,
                    evidence_by_id=evidence_by_id,
                    location="$.path_contract.flow_observations.evidence_refs",
                    allowed_evidence_kinds=frozenset(
                        {"information_flow_observation"}
                    ),
                )
            result_kinds = {str(item["control_kind"]) for item in contract["control_results"]}
            if result_kinds != set(CONTROL_KINDS):
                _add(errors, "control_result_coverage_mismatch", "$.path_contract.control_results", str(sorted(result_kinds)))
            for result in contract["control_results"]:
                control = control_by_id.get(str(result["control_ref"]))
                if control is None or result["control_digest"] != control["control_digest"] or result["control_kind"] != control["control_kind"]:
                    _add(errors, "control_result_binding_mismatch", "$.path_contract.control_results", result["control_ref"])
                refs = [str(value) for value in result["evidence_refs"]]
                used_evidence_refs.update(refs)
                claim_universe.add(str(result["control_ref"]))
                _claim_binding(
                    errors,
                    parent_id=str(result["control_ref"]),
                    evidence_refs=refs,
                    evidence_by_id=evidence_by_id,
                    location="$.path_contract.control_results.evidence_refs",
                    allowed_evidence_kinds=CONTROL_EVIDENCE_KINDS[
                        str(result["control_kind"])
                    ],
                )
            assessment_dimensions = {str(item["dimension"]) for item in contract["trigger_assessments"]}
            if assessment_dimensions != set(REQUALIFICATION_DIMENSIONS):
                _add(errors, "trigger_assessment_coverage_mismatch", "$.path_contract.trigger_assessments", str(sorted(assessment_dimensions)))
            for assessment in contract["trigger_assessments"]:
                trigger = trigger_by_id.get(str(assessment["trigger_ref"]))
                if trigger is None or assessment["trigger_digest"] != trigger["trigger_digest"] or assessment["dimension"] != trigger["dimension"]:
                    _add(errors, "trigger_assessment_binding_mismatch", "$.path_contract.trigger_assessments", assessment["trigger_ref"])
                refs = [str(value) for value in assessment["evidence_refs"]]
                used_evidence_refs.update(refs)
                claim_universe.add(str(assessment["trigger_ref"]))
                required_kinds = (
                    frozenset()
                    if trigger is None
                    else frozenset(
                        str(value) for value in trigger["required_evidence_kinds"]
                    )
                )
                _claim_binding(
                    errors,
                    parent_id=str(assessment["trigger_ref"]),
                    evidence_refs=refs,
                    evidence_by_id=evidence_by_id,
                    location="$.path_contract.trigger_assessments.evidence_refs",
                    allowed_evidence_kinds=required_kinds,
                )
                observed_kinds = {
                    str(evidence_by_id[ref]["evidence_kind"])
                    for ref in refs
                    if ref in evidence_by_id
                }
                if not required_kinds.issubset(observed_kinds):
                    _add(
                        errors,
                        "trigger_required_evidence_kind_missing",
                        "$.path_contract.trigger_assessments.evidence_refs",
                        assessment["trigger_ref"],
                    )
        else:
            if set(profile["required_conditions"]) != set(NONAPPLICABILITY_CONDITIONS):
                _add(errors, "nonapplicability_condition_profile_mismatch", "$.path_contract.profile.required_conditions", "six fixed conditions are required")
            if set(profile["reactivation_triggers"]) != set(REACTIVATION_TRIGGERS):
                _add(errors, "reactivation_trigger_profile_mismatch", "$.path_contract.profile.reactivation_triggers", "all automatic reactivation triggers are required")
            condition_ids = [str(item["condition_id"]) for item in contract["condition_results"]]
            for duplicate in sorted(_duplicates(condition_ids)):
                _add(errors, "duplicate_condition_result", "$.path_contract.condition_results", duplicate)
            if set(condition_ids) != set(NONAPPLICABILITY_CONDITIONS):
                _add(errors, "condition_exact_coverage_mismatch", "$.path_contract.condition_results", "all six boundary conditions require observations")
            derived_conditions = _derived_nonapplicability_conditions(manifests)
            for index, result in enumerate(contract["condition_results"]):
                _check_nested_digest(errors, result, digest_field="result_digest", code="condition_result_digest_mismatch", location=f"$.path_contract.condition_results.{index}.result_digest")
                refs = [str(value) for value in result["evidence_refs"]]
                used_evidence_refs.update(refs)
                claim_universe.add(str(result["condition_id"]))
                condition_id = str(result["condition_id"])
                _claim_binding(
                    errors,
                    parent_id=condition_id,
                    evidence_refs=refs,
                    evidence_by_id=evidence_by_id,
                    location=f"$.path_contract.condition_results.{index}.evidence_refs",
                    allowed_evidence_kinds=CONDITION_EVIDENCE_KINDS[condition_id],
                )
                if result["status"] == "confirmed" and not derived_conditions[
                    condition_id
                ]:
                    _add(
                        errors,
                        "nonapplicability_condition_scope_contradiction",
                        f"$.path_contract.condition_results.{index}.status",
                        condition_id,
                    )
            restart = contract["restart_test"]
            _check_nested_digest(errors, restart, digest_field="test_digest", code="restart_test_digest_mismatch", location="$.path_contract.restart_test.test_digest")
            refs = [str(value) for value in restart["evidence_refs"]]
            used_evidence_refs.update(refs)
            claim_universe.add(str(restart["test_id"]))
            _claim_binding(
                errors,
                parent_id=str(restart["test_id"]),
                evidence_refs=refs,
                evidence_by_id=evidence_by_id,
                location="$.path_contract.restart_test.evidence_refs",
                allowed_evidence_kinds=frozenset({"restart_test"}),
            )

        for manifest in manifests:
            claim_universe.add(str(manifest["manifest_id"]))
            inventory_refs = [
                str(value) for value in manifest["inventory_evidence_refs"]
            ]
            used_evidence_refs.update(inventory_refs)
            _claim_binding(
                errors,
                parent_id=str(manifest["manifest_id"]),
                evidence_refs=inventory_refs,
                evidence_by_id=evidence_by_id,
                location="$.scope_manifests.inventory_evidence_refs",
                allowed_evidence_kinds=frozenset({"scope_inventory"}),
                expected_observer_ref=manifest["inventory_authority_ref"],
                observer_mismatch_code="inventory_evidence_authority_mismatch",
            )
            for entry in manifest["entries"]:
                refs = [str(value) for value in entry["evidence_refs"]]
                used_evidence_refs.update(refs)
                _claim_binding(errors, parent_id=str(entry["entry_id"]), evidence_refs=refs, evidence_by_id=evidence_by_id, location="$.scope_manifests.entries.evidence_refs")

        review_basis = digest_value(_basis_material(bundle))
        if bundle["review_basis_digest"] != review_basis:
            _add(errors, "review_basis_digest_mismatch", "$.review_basis_digest", "review basis changed")
        review = bundle["independent_review_record"]
        if review is not None:
            _check_nested_digest(errors, review, digest_field="review_digest", code="independent_review_digest_mismatch", location="$.independent_review_record.review_digest")
            claim_universe.add(str(review["review_id"]))
            refs = [str(value) for value in review["evidence_refs"]]
            used_evidence_refs.update(refs)
            _claim_binding(
                errors,
                parent_id=str(review["review_id"]),
                evidence_refs=refs,
                evidence_by_id=evidence_by_id,
                location="$.independent_review_record.evidence_refs",
                allowed_evidence_kinds=frozenset({"independent_review"}),
                expected_observer_ref=review["reviewer_ref"],
                wrong_kind_code="independent_review_evidence_kind_mismatch",
            )
            if (
                review["target_assessment_id"] != bundle["assessment_id"]
                or review["target_assessment_version"] != bundle["assessment_version"]
                or review["target_basis_digest"] != review_basis
            ):
                _add(errors, "independent_review_binding_mismatch", "$.independent_review_record", review["review_id"])

        for item in evidence:
            unknown_claims = set(item["claim_refs"]) - claim_universe
            if unknown_claims:
                _add(errors, "evidence_unknown_claim_ref", "$.evidence_observations", f"{item['evidence_id']}: {sorted(unknown_claims)}")
        unused = set(evidence_ids) - used_evidence_refs
        if unused:
            _add(errors, "unused_evidence", "$.evidence_observations", str(sorted(unused)))

        expected_result = _compute_result(bundle, basis_digest=review_basis)
        if bundle["result"] != expected_result:
            _add(errors, "result_replay_mismatch", "$.result", "stored result does not equal deterministic recomputation")
    except (KeyError, TypeError, ValueError) as exc:
        _add(errors, "secure_operation_replay_failed", "$", str(exc))

    return tuple(errors)


def validate_secure_operation(bundle: Mapping[str, Any]) -> dict[str, Any]:
    errors = secure_operation_errors(bundle)
    if errors:
        raise SecureOperationValidationError(errors)
    return copy.deepcopy(dict(bundle))
