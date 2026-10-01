"""Fail-closed public envelope for governance-aware requirement auditing.

The existing v0 engine remains a historical analysis implementation.  This
module records its output as an observation and prevents its internally
assertion-capable stages from becoming engineering assurance.  The v1 public
envelope is permanently candidate-only; a later contract with an external
trust root would be required before any formal authority could be represented.
"""

from __future__ import annotations

import copy
from datetime import datetime, timezone
from functools import lru_cache
import hashlib
import json
from typing import Any, Mapping, Sequence

from jsonschema import Draft202012Validator, FormatChecker, ValidationError

from .assurance_graph import validate_assurance_claim_v1
from .audit.report import RequirementAuditReport
from .engineering_rule_governance import (
    EngineeringRuleGovernanceError,
    validate_governance_bundle,
)
from .governance_materials import (
    GovernanceMaterialAssessmentError,
    assess_governance_materials,
    validate_governance_material_assessment,
)
from .public_contract import public_audit_payload, validate_public_audit
from .schema_access import schema_path


SCHEMA_VERSION = "governed-requirement-audit/v1"
LEGACY_OUTPUT_ENVELOPE_SCHEMA_VERSION = "legacy-ungoverned-output-envelope/v0"
_SCHEMA_PATH = schema_path("governed-audit-result.schema.json")
_LEGACY_OUTPUT_SCHEMA_PATH = schema_path("legacy-output-envelope.schema.json")
_LEGACY_OUTPUT_FORMATS = {
    "legacy-compat",
    "legacy-public-v0",
    "legacy-assurance-v1",
    "legacy-internal-debug-v0",
}
_LEGACY_COMPAT_KEYS = {
    "phase",
    "status",
    "score",
    "findings",
    "missing",
    "next_actions",
    "details",
}
_LEGACY_INTERNAL_REQUIRED_KEYS = {
    "schema_version",
    "source_id",
    "profile_id",
    "profile_version",
    "record",
    "direct_assessments",
    "analysis_attempts",
    "obligation_reassessments",
    "remaining_unresolved_obligations",
    "result",
    "analysis_mode",
}
_AUTHORITY_BOUNDARY = {
    "legacy_analysis_authority": "observation_only",
    "candidate_finding_authority": "candidate_only",
    "unresolved_escalation": True,
    "direct_command_authority": False,
    "human_decision_authority": False,
    "formal_verdict_requires_exact_h1_resolution": True,
    "formal_verdict_requires_complete_governance_resolution": True,
    "final_acceptance_owner": "human",
}
_LIMITATIONS = (
    "The legacy v0 workflow disposition is preserved only as an analysis observation and has no governed verdict authority by itself.",
    "A candidate finding cannot establish satisfaction, nonconformance, not-applicability, hold release, or a final verdict.",
    "A structurally valid H1 bundle is insufficient unless it binds this exact observation and every authority-producing stage.",
    "Public v1 can embed and replay candidate H1, H2, ENV-PATH, and D7 material, but none can establish formal assurance without its external trust and qualification prerequisites.",
    "The record digest supports deterministic replay but not origin authentication or resistance to deliberate resealing; trusted transport or an external signature is required for that claim.",
    "No governed audit result performs control-plane routing, grants authority, proves action occurrence, or establishes final human acceptance.",
)
_REQUIRED_UNRESOLVED_KINDS = {
    "unresolved.engineering-rule-governance.H1": "engineering_rule_authority",
    "unresolved.lifecycle-profile-governance.H2": "lifecycle_profile_authority",
    "unresolved.execution-environment.ENV-PATH-001": "execution_environment_evidence",
    "unresolved.field-performance.D7": "field_performance_qualification",
}


class GovernedAuditValidationError(ValueError):
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


def digest_value(value: Any) -> dict[str, str]:
    return {
        "algorithm": "sha256",
        "value": hashlib.sha256(_canonical(value)).hexdigest(),
    }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _observation_ref(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "ref_id": str(payload["audit_id"]),
        "schema_version": str(payload["schema_version"]),
        "digest": digest_value(payload),
    }


def _semantic_identity(prefix: str, payload: Mapping[str, Any]) -> str:
    meaning = copy.deepcopy(dict(payload))
    meaning.pop("envelope_id", None)
    meaning.pop("record_digest", None)
    return prefix + hashlib.sha256(_canonical(meaning)).hexdigest()


def _governed_audit_id(payload: Mapping[str, Any]) -> str:
    """Derive identity from the entire semantic record, excluding identities.

    ``record_digest`` makes resealing detectable only when the signer or
    transport is trusted.  ``audit_id`` additionally provides stable semantic
    identity: changing any finding, legacy summary, unresolved closure action,
    authority boundary, or limitation necessarily changes the identifier.
    """

    meaning = copy.deepcopy(dict(payload))
    meaning.pop("audit_id", None)
    meaning.pop("record_digest", None)
    return "governed-audit." + hashlib.sha256(_canonical(meaning)).hexdigest()


def wrap_legacy_output(
    output_format: str,
    legacy_payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Isolate a historical payload in a self-describing ungoverned envelope.

    Selecting a legacy format is transport compatibility only.  The authority
    ceiling is carried inside the returned value so that persisting the value
    without the CLI or MCP format-selection context cannot turn it into a
    contemporary assurance result.
    """

    if output_format not in _LEGACY_OUTPUT_FORMATS:
        raise ValueError(f"unsupported legacy output format: {output_format}")
    material = {
        "schema_version": LEGACY_OUTPUT_ENVELOPE_SCHEMA_VERSION,
        "envelope_id": "pending-semantic-identity",
        "output_format": output_format,
        "governance_status": "legacy_ungoverned",
        "authority_scope": "observation_only",
        "formal_authority": "none",
        "positive_assurance": False,
        "allowed_use": ["historical_observation", "compatibility_analysis"],
        "forbidden_use": [
            "formal_satisfaction",
            "formal_nonconformance",
            "hold_release",
            "human_acceptance",
        ],
        "limitations": [
            "The nested legacy payload is historical analysis material and is not a governed verdict.",
            "Removing the outer envelope destroys the public authority context and is not a supported projection.",
            "The digest is replay evidence, not origin authentication; trusted transport or an external signature is required against deliberate resealing.",
        ],
        "legacy_payload": copy.deepcopy(dict(legacy_payload)),
    }
    material["envelope_id"] = _semantic_identity("legacy-output.", material)
    result = {**material, "record_digest": digest_value(material)}
    validate_legacy_output(result)
    return result


def _analysis_material(
    report: RequirementAuditReport,
    legacy_public_payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Retain the complete legacy observation plus a closed trace inventory."""

    internal = report.as_dict()
    provider_attempts = copy.deepcopy(internal["analysis_attempts"])
    indexed_attempts = [
        {
            "stage": "structured_parse",
            "source_kind": "structured_record_observation",
            "observed_material": copy.deepcopy(internal["record"]),
            "allowed_use": "candidate_finding",
            "formal_authority": "none",
        },
        {
            "stage": "direct_rules",
            "source_kind": "direct_rule_observations",
            "observed_material": copy.deepcopy(internal["direct_assessments"]),
            "allowed_use": "candidate_finding",
            "formal_authority": "none",
        },
    ]
    indexed_attempts.extend(
        {
            "stage": str(attempt["stage"]),
            "source_kind": "provider_analysis_attempt",
            "observed_material": copy.deepcopy(attempt),
            "allowed_use": "candidate_finding",
            "formal_authority": "none",
        }
        for attempt in provider_attempts
    )
    unresolved = {
        "initial": copy.deepcopy(internal["initial_unresolved_obligations"]),
        "remaining": copy.deepcopy(internal["remaining_unresolved_obligations"]),
        "effective": copy.deepcopy(internal["unresolved_obligations"]),
        "public_required_obligation_ids": copy.deepcopy(
            legacy_public_payload["unresolved_required_obligation_ids"]
        ),
    }
    limitations = {
        "report": copy.deepcopy(internal["limitations"]),
        "public_audit_conclusion": copy.deepcopy(
            legacy_public_payload["audit_conclusion"]["limitations"]
        ),
        "residual_signals": [
            copy.deepcopy(item.get("limitations", []))
            for item in internal["residual_signals"]
        ],
        "shadow_signals": [
            copy.deepcopy(item.get("limitations", []))
            for item in internal["shadow_signals"]
        ],
    }
    inventory = {
        "structured_attempt_count": 1,
        "direct_attempt_count": 1,
        "provider_attempt_count": len(provider_attempts),
        "reassessment_count": len(internal["obligation_reassessments"]),
        "provider_receipt_count": len(internal["provider_execution_receipts"]),
        "initial_unresolved_count": len(unresolved["initial"]),
        "remaining_unresolved_count": len(unresolved["remaining"]),
        "provenance_count": len(legacy_public_payload["provenance"]),
    }
    material = {
        "authority_status": "legacy_ungoverned_observation_only",
        "allowed_use": ["candidate_finding", "unresolved_escalation"],
        "formal_authority": "none",
        "trace_inventory": inventory,
        "analysis_attempts": indexed_attempts,
        "provider_execution_receipts": copy.deepcopy(
            internal["provider_execution_receipts"]
        ),
        "obligation_reassessments": copy.deepcopy(internal["obligation_reassessments"]),
        "dependency_projections": copy.deepcopy(internal["dependency_projections"]),
        "analyzer_qualifications": copy.deepcopy(internal["analyzer_qualifications"]),
        "lifting_resolutions": copy.deepcopy(internal["lifting_resolutions"]),
        "unresolved_observations": unresolved,
        "limitations_by_source": limitations,
        "provenance": copy.deepcopy(legacy_public_payload["provenance"]),
        # These full payloads prevent the stage index from becoming a lossy
        # replacement for historical material.  They remain nested below the
        # fixed observation-only authority ceiling above.
        "legacy_public_payload": copy.deepcopy(dict(legacy_public_payload)),
        "legacy_internal_trace": internal,
    }
    material["material_digest"] = digest_value(material)
    return material


def _candidate_finding_id(kind: str, material: Mapping[str, Any]) -> str:
    return (
        f"candidate-finding.{kind}."
        f"{hashlib.sha256(_canonical(material)).hexdigest()[:32]}"
    )


def _candidate_finding_values(
    internal_trace: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Normalize every analysis route into one candidate-only finding type."""

    findings: list[dict[str, Any]] = []
    structured = copy.deepcopy(dict(internal_trace["record"]))
    structured_material = {
        "finding_kind": "structured_record_observation",
        "stage": "structured_parse",
        "obligation_ids": [],
        "origin_refs": ["structured-functional-requirement-parser/v0"],
        "observed_outcome": (
            "incomplete"
            if structured["missing_fields"]
            or structured["duplicate_fields"]
            or structured["diagnostics"]
            else "observed"
        ),
        "evidence_spans": [],
        "reason_codes": sorted(
            set(
                [
                    *[f"missing_field:{item}" for item in structured["missing_fields"]],
                    *[
                        f"duplicate_field:{item}"
                        for item in structured["duplicate_fields"]
                    ],
                    *[str(item) for item in structured["diagnostics"]],
                ]
            )
        ),
        "observed_material_digest": digest_value(structured),
        "allowed_use": "candidate_finding",
        "formal_authority": "none",
    }
    findings.append(
        {
            "finding_id": _candidate_finding_id("structured", structured_material),
            **structured_material,
        }
    )

    for assessment in internal_trace["direct_assessments"]:
        material = {
            "finding_kind": "direct_rule_assessment",
            "stage": "direct_rules",
            "obligation_ids": [str(assessment["obligation_id"])],
            "origin_refs": [str(assessment["rule_id"])],
            "observed_outcome": str(assessment["outcome"]),
            "evidence_spans": [
                {"start": int(start), "end_exclusive": int(end)}
                for start, end in assessment["evidence_spans"]
            ],
            "reason_codes": sorted(
                set(
                    [
                        *[str(item) for item in assessment["basis"]],
                        *[str(item) for item in assessment["unknown_reasons"]],
                    ]
                )
            ),
            "observed_material_digest": digest_value(assessment),
            "allowed_use": "candidate_finding",
            "formal_authority": "none",
        }
        findings.append(
            {
                "finding_id": _candidate_finding_id("direct", material),
                **material,
            }
        )

    for attempt in internal_trace["analysis_attempts"]:
        stage = str(attempt["stage"])
        provider_id = str(attempt["provider_id"])
        material = {
            "finding_kind": "provider_analysis_attempt",
            "stage": stage,
            "obligation_ids": [],
            "origin_refs": sorted(
                set(
                    [
                        provider_id,
                        *[str(item) for item in attempt["upstream_usage"]],
                    ]
                )
            ),
            "observed_outcome": str(attempt["status"]),
            "evidence_spans": [],
            "reason_codes": sorted(set(str(item) for item in attempt["diagnostics"])),
            "observed_material_digest": digest_value(attempt),
            "allowed_use": "candidate_finding",
            "formal_authority": "none",
        }
        findings.append(
            {
                "finding_id": _candidate_finding_id(f"provider-{stage}", material),
                **material,
            }
        )

    for reassessment in internal_trace["obligation_reassessments"]:
        material = {
            "finding_kind": "obligation_reassessment",
            "stage": "obligation_reassessment",
            "obligation_ids": [str(reassessment["obligation_id"])],
            "origin_refs": sorted(
                set(
                    [
                        str(reassessment["original_rule_id"]),
                        str(reassessment["policy_rule_id"]),
                        *[str(item) for item in reassessment["receipt_ids"]],
                        *[str(item) for item in reassessment["qualification_ids"]],
                        *[str(item) for item in reassessment["projection_ids"]],
                    ]
                )
            ),
            "observed_outcome": str(reassessment["effective_outcome"]),
            "evidence_spans": [
                {"start": int(start), "end_exclusive": int(end)}
                for start, end in reassessment["evidence_spans"]
            ],
            "reason_codes": sorted(
                set(
                    [
                        f"reassessment_decision:{reassessment['decision']}",
                        *[str(item) for item in reassessment["reasons"]],
                    ]
                )
            ),
            "observed_material_digest": digest_value(reassessment),
            "allowed_use": "candidate_finding",
            "formal_authority": "none",
        }
        findings.append(
            {
                "finding_id": _candidate_finding_id("reassessment", material),
                **material,
            }
        )
    return findings


def _obligation_is_closed(obligation: Mapping[str, Any]) -> bool:
    return (
        obligation["finality"] == "terminal"
        and obligation["outcome"] in {"satisfied", "not_applicable"}
        and obligation["challenge"] == "none"
    )


def _requirement_unresolved_records(
    internal_trace: Mapping[str, Any],
    *,
    observation_ref_id: str,
) -> list[dict[str, Any]]:
    remaining = internal_trace["remaining_unresolved_obligations"]
    routes_by_obligation: dict[str, list[Mapping[str, Any]]] = {}
    for unresolved in remaining:
        routes_by_obligation.setdefault(str(unresolved["obligation_id"]), []).append(
            unresolved
        )
    records: list[dict[str, Any]] = []
    for obligation in internal_trace["result"]["obligations"]:
        if (
            not obligation["active"]
            or not obligation["required"]
            or _obligation_is_closed(obligation)
        ):
            continue
        obligation_id = str(obligation["obligation_id"])
        route_materials = routes_by_obligation.get(obligation_id, [])
        routes = sorted(
            {
                str(item["requested_route"])
                for unresolved in route_materials
                for item in unresolved["reason_routing"]
            }
        )
        unresolved_material = {
            "obligation_id": obligation_id,
            "outcome": obligation["outcome"],
            "finality": obligation["finality"],
            "challenge": obligation["challenge"],
            "coverage": copy.deepcopy(obligation["coverage"]),
            "unknown_reasons": copy.deepcopy(obligation["unknown_reasons"]),
            "route_unresolved_refs": [
                str(item["unresolved_id"]) for item in route_materials
            ],
        }
        item_digest = digest_value(unresolved_material)["value"]
        records.append(
            {
                "unresolved_id": (
                    "unresolved.requirement-obligation." + item_digest[:32]
                ),
                "uncertainty_kind": "requirement_obligation_evidence",
                "owner": "audit_requesting_agent_then_human_if_authority_required",
                "needed_for": f"obligation_assurance:{obligation_id}",
                "blocking_status": "blocking_positive_assurance",
                "next_action": (
                    "Run and assess the candidate routes: " + ", ".join(routes)
                    if routes
                    else "Provide additional source-aligned evidence and reassess the obligation."
                ),
                "resolution_condition": (
                    "A new digest-bound obligation assessment resolves the exact "
                    "unresolved item without authority escalation or lost guards."
                ),
                "review_at": "after_candidate_route_or_source_revision",
                "fallback": "retain_the_obligation_as_unresolved",
                "retirement_condition": (
                    "superseded_by_a_new_source_and_obligation_assessment_digest"
                ),
                "evidence_refs": [
                    observation_ref_id,
                    f"obligation:{obligation_id}",
                    *[
                        str(unresolved["unresolved_id"])
                        for unresolved in route_materials
                    ],
                ],
            }
        )
    return records


def _authority_source_ids(report: RequirementAuditReport) -> list[str]:
    values: set[str] = set()
    for obligation in report.result.obligations:
        for evidence in obligation.provenance:
            authority = evidence.authority
            for capability, exercised in (
                ("support", authority.support),
                ("challenge", authority.challenge),
                ("hold_apply", authority.hold_apply),
                ("hold_release", authority.hold_release),
            ):
                if exercised:
                    values.add(f"{authority.stage_id}#{capability}")
        for hold in obligation.holds:
            values.add(f"{hold.applied_by.authority.stage_id}#hold_apply")
            if hold.released_by is not None:
                values.add(f"{hold.released_by.authority.stage_id}#hold_release")
    for hold in report.result.execution.holds:
        values.add(f"{hold.applied_by.authority.stage_id}#hold_apply")
        if hold.released_by is not None:
            values.add(f"{hold.released_by.authority.stage_id}#hold_release")
    return sorted(values)


def _governance_summary(
    governance_bundle: Mapping[str, Any] | None,
    *,
    observation_digest: Mapping[str, str],
    authority_source_ids: Sequence[str],
) -> dict[str, Any]:
    if governance_bundle is None:
        return {
            "h1_human_decision": "pending",
            "h1_verdict_authority": "none",
            "runtime_resolution_status": "unresolved",
            "observation_binding_status": "not_bound",
            "required_authority_source_ids": list(authority_source_ids),
            "resolved_authority_source_ids": [],
            "reason_codes": [
                "engineering_rule_governance_bundle_missing",
                "H1_human_decision_pending",
            ],
        }
    try:
        validate_governance_bundle(governance_bundle)
    except EngineeringRuleGovernanceError as exc:
        replay_context_missing = "runtime resolution replay mismatch" in str(exc)
        return {
            "h1_human_decision": "pending",
            "h1_verdict_authority": "none",
            "runtime_resolution_status": "unresolved",
            "observation_binding_status": (
                "unsupported_proof_context"
                if replay_context_missing
                else "invalid_governance_bundle"
            ),
            "required_authority_source_ids": list(authority_source_ids),
            "resolved_authority_source_ids": [],
            "reason_codes": [
                (
                    "engineering_rule_governance_runtime_verifier_context_not_embedded"
                    if replay_context_missing
                    else "engineering_rule_governance_bundle_invalid"
                )
            ],
        }
    except (KeyError, TypeError, ValueError):
        return {
            "h1_human_decision": "pending",
            "h1_verdict_authority": "none",
            "runtime_resolution_status": "unresolved",
            "observation_binding_status": "invalid_governance_bundle",
            "required_authority_source_ids": list(authority_source_ids),
            "resolved_authority_source_ids": [],
            "reason_codes": ["engineering_rule_governance_bundle_invalid"],
        }

    resolution = governance_bundle["runtime_resolution"]
    request = resolution["runtime_request"]
    bound = request["obligation_assessment_digest"] == observation_digest
    reasons: list[str] = []
    if not bound:
        reasons.append("governance_observation_digest_mismatch")
    reasons.extend(
        f"authority_capability_unresolved:{item}" for item in authority_source_ids
    )
    # Public v1 intentionally does not embed the complete H1 bundle, trusted
    # reviewer-verifier result, or trusted decision-verifier result.  It may
    # report that supplied material matched, but it can never replay a formal
    # resolution from this envelope alone.  A later formal contract requires a
    # new schema that carries and revalidates that proof closure.
    reasons.append("formal_governance_proof_not_embedded_in_public_v1")
    return {
        # The bundle does not carry portable verifier receipts.  Consequently
        # neither a reported human disposition nor a locally resolved rule may
        # be projected as a verified public fact.
        "h1_human_decision": "pending",
        "h1_verdict_authority": "none",
        "runtime_resolution_status": "unresolved",
        "observation_binding_status": "matched" if bound else "mismatched",
        "required_authority_source_ids": list(authority_source_ids),
        "resolved_authority_source_ids": [],
        "reason_codes": sorted(set(reasons)),
    }


def project_governed_audit(
    report: RequirementAuditReport,
    *,
    governance_bundle: Mapping[str, Any] | None = None,
    governance_materials: Mapping[str, Any] | None = None,
    recorded_at: str | None = None,
) -> dict[str, Any]:
    """Project a v0 analysis into the governed public v1 authority ceiling."""

    if governance_bundle is not None:
        raise ValueError(
            "governance_bundle is not accepted by governed public v1 because the "
            "complete input cannot be replayed from the result; supply an "
            "engineering_rule_pack_candidate through governance_materials"
        )
    timestamp = recorded_at or _now()
    legacy = public_audit_payload(report, recorded_at=timestamp)
    validate_public_audit(legacy)
    observation = _observation_ref(legacy)
    authority_sources = _authority_source_ids(report)
    subject_scope_ref = {
        "record_id": report.source_id,
        "locator": f"urn:semantic-guard:embedded-source:{report.source_id}",
        "content_digest": {
            "algorithm": "sha256",
            "value": report.source_id.removeprefix("sha256:"),
        },
    }
    material_assessment = assess_governance_materials(
        governance_materials,
        observation_digest=observation["digest"],
        authority_source_ids=authority_sources,
        subject_scope_ref=subject_scope_ref,
    )
    adapted_h1 = material_assessment["engineering_rule_governance"]["validated_record"]
    effective_h1_bundle = (
        adapted_h1["governance_bundle"] if isinstance(adapted_h1, Mapping) else None
    )
    governance = _governance_summary(
        effective_h1_bundle,
        observation_digest=observation["digest"],
        authority_source_ids=authority_sources,
    )
    analysis_material = _analysis_material(report, legacy)
    formal = False
    workflow = "block"
    result_status = "unresolved"
    unresolved_records = []
    if not formal:
        unresolved_records.extend(
            [
                {
                    "unresolved_id": "unresolved.engineering-rule-governance.H1",
                    "uncertainty_kind": "engineering_rule_authority",
                    "owner": "external_engineering_governance_owner",
                    "needed_for": "formal_requirement_audit_verdict",
                    "blocking_status": "blocking_positive_assurance",
                    "next_action": "Resolve H1, every authority-producing rule, the exact implementation, scope, profile, evidence currency, and this observation digest through a trusted external decision entrypoint.",
                    "resolution_condition": "The exact required authority-source denominator resolves formally with no blocking unresolved item and binds this observation digest.",
                    "review_at": "pending_external_schedule",
                    "fallback": "retain_candidate_findings_and_unresolved_status",
                    "retirement_condition": "superseded_by_a_new_digest_bound_governed_audit",
                    "evidence_refs": [observation["ref_id"]],
                },
                {
                    "unresolved_id": "unresolved.lifecycle-profile-governance.H2",
                    "uncertainty_kind": "lifecycle_profile_authority",
                    "owner": "external_lifecycle_governance_owner",
                    "needed_for": "formal_requirement_stage_assurance",
                    "blocking_status": "blocking_positive_assurance",
                    "next_action": "Resolve the requirement-stage profile, tailoring, applicability, rule bindings, implementation, and external adoption through the H2 runtime resolver.",
                    "resolution_condition": "The exact requirement-stage occurrence and profile denominator resolve under an externally verified adopted H2 record.",
                    "review_at": "pending_external_schedule",
                    "fallback": "retain_profile_observation_as_unresolved",
                    "retirement_condition": "superseded_by_a_digest_bound_lifecycle_resolution",
                    "evidence_refs": [observation["ref_id"]],
                },
                {
                    "unresolved_id": "unresolved.execution-environment.ENV-PATH-001",
                    "uncertainty_kind": "execution_environment_evidence",
                    "owner": "external_execution_harness_owner",
                    "needed_for": "replayable_audit_occurrence_evidence",
                    "blocking_status": "blocking_positive_assurance",
                    "next_action": "Execute under an externally adopted logical-tool profile with managed PATH, pre/post observations, and child-process executable evidence.",
                    "resolution_condition": "The exact audit occurrence is bound to a current environment profile and complete executable trace with no requalification trigger.",
                    "review_at": "pending_external_schedule",
                    "fallback": "treat_the_computation_as_an_unqualified_local_observation",
                    "retirement_condition": "superseded_by_a_digest_bound_environment_snapshot",
                    "evidence_refs": [observation["ref_id"]],
                },
                {
                    "unresolved_id": "unresolved.field-performance.D7",
                    "uncertainty_kind": "field_performance_qualification",
                    "owner": "external_field_evaluation_owner",
                    "needed_for": "practical_population_bounded_assurance",
                    "blocking_status": "blocking_positive_assurance",
                    "next_action": "Complete independent holdout evaluation, resolve all seven metrics and provenance, then obtain externally authenticated human threshold adoption.",
                    "resolution_condition": "A current field-performance bundle for the exact implementation and population meets adopted risk-class thresholds without leakage, authority violation, traceability loss, or blocking unresolved items.",
                    "review_at": "pending_external_schedule",
                    "fallback": "make_no_field_qualification_claim",
                    "retirement_condition": "superseded_by_a_new_implementation_bound_field_evaluation",
                    "evidence_refs": [observation["ref_id"]],
                },
            ]
        )
        unresolved_records.extend(
            _requirement_unresolved_records(
                report.as_dict(),
                observation_ref_id=observation["ref_id"],
            )
        )
    material = {
        "schema_version": SCHEMA_VERSION,
        "audit_id": "pending-semantic-identity",
        "recorded_at": timestamp,
        "subject": {
            "source_id": report.source_id,
            "source_text": report.record.source_text,
            "content_digest": {
                "algorithm": "sha256",
                "value": report.source_id.removeprefix("sha256:"),
            },
        },
        "profile_observation": {
            "profile_id": report.profile_id,
            "profile_version": report.profile_version,
            "adoption_resolution": "unresolved",
            "formal_authority": "none",
        },
        "legacy_analysis_observation": {
            "analysis_ref": observation,
            "analysis_mode": report.analysis_mode,
            "observed_workflow_disposition": report.result.workflow.value,
            "observed_outcome": report.result.outcome.value,
            "analysis_reasons": list(report.result.reasons),
            "required_provider_failure_ids": list(
                report.result.execution.provider_failures
            ),
            "authority_status": "legacy_ungoverned_observation_only",
            "formal_authority": "none",
        },
        "legacy_analysis_material": analysis_material,
        "candidate_findings": _candidate_finding_values(
            analysis_material["legacy_internal_trace"]
        ),
        "governance_material_assessment": material_assessment,
        "governance_resolution": governance,
        "assurance_assessment": {
            "status": result_status,
            "workflow_disposition": workflow,
            "formal_verdict_authority": "none",
            "blocking_unresolved_count": len(unresolved_records),
            "allowed_use": ["candidate_finding", "unresolved_escalation"],
            "forbidden_use": [
                "direct_ai_command",
                "human_decision_inference",
                "action_occurrence_inference",
                "final_human_acceptance",
            ],
        },
        "unresolved_records": unresolved_records,
        "authority_boundary": copy.deepcopy(_AUTHORITY_BOUNDARY),
        "limitations": list(_LIMITATIONS),
    }
    material["audit_id"] = _governed_audit_id(material)
    result = {**material, "record_digest": digest_value(material)}
    validate_governed_audit(result)
    return result


@lru_cache(maxsize=1)
def _validator() -> Draft202012Validator:
    with _SCHEMA_PATH.open("r", encoding="utf-8") as handle:
        schema = json.load(handle)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


@lru_cache(maxsize=1)
def _legacy_output_validator() -> Draft202012Validator:
    with _LEGACY_OUTPUT_SCHEMA_PATH.open("r", encoding="utf-8") as handle:
        schema = json.load(handle)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def legacy_output_errors(payload: Mapping[str, Any]) -> tuple[dict[str, str], ...]:
    errors: list[dict[str, str]] = []
    schema_errors: list[dict[str, str]] = []
    for error in sorted(
        _legacy_output_validator().iter_errors(payload),
        key=lambda item: list(item.path),
    ):
        location = "$" + "".join(
            f"[{item}]" if isinstance(item, int) else f".{item}" for item in error.path
        )
        schema_errors.append(
            {"code": "schema_error", "location": location, "message": error.message}
        )
    errors.extend(schema_errors)
    if schema_errors:
        return tuple(errors)
    material = copy.deepcopy(dict(payload))
    observed_digest = material.pop("record_digest")
    if observed_digest != digest_value(material):
        errors.append(
            {
                "code": "record_digest_mismatch",
                "location": "$.record_digest",
                "message": "legacy output envelope digest does not replay",
            }
        )
    if payload["envelope_id"] != _semantic_identity("legacy-output.", payload):
        errors.append(
            {
                "code": "envelope_id_mismatch",
                "location": "$.envelope_id",
                "message": "legacy output envelope identity does not replay",
            }
        )
    output_format = payload["output_format"]
    legacy_payload = payload["legacy_payload"]
    try:
        if output_format == "legacy-public-v0":
            validate_public_audit(legacy_payload)
        elif output_format == "legacy-assurance-v1":
            validate_assurance_claim_v1(copy.deepcopy(dict(legacy_payload)))
        elif output_format == "legacy-internal-debug-v0":
            if (
                legacy_payload.get("schema_version")
                != "semantic-guard-vnext-requirement-audit/v0"
                or not _LEGACY_INTERNAL_REQUIRED_KEYS <= set(legacy_payload)
            ):
                raise ValueError(
                    "nested payload is not an internal requirement-audit v0 report"
                )
        elif output_format == "legacy-compat":
            if set(legacy_payload) != _LEGACY_COMPAT_KEYS:
                raise ValueError(
                    "nested payload is not the closed seven-field compatibility projection"
                )
        else:  # The schema currently prevents this branch.
            raise ValueError(f"unsupported legacy output format: {output_format}")
    except (ValidationError, KeyError, TypeError, ValueError, IndexError) as exc:
        errors.append(
            {
                "code": "legacy_payload_format_mismatch",
                "location": "$.legacy_payload",
                "message": f"output_format does not match the nested legacy contract: {exc}",
            }
        )
    return tuple(errors)


def validate_legacy_output(payload: Mapping[str, Any]) -> dict[str, Any]:
    errors = legacy_output_errors(payload)
    if errors:
        raise GovernedAuditValidationError(errors)
    return copy.deepcopy(dict(payload))


def _analysis_material_errors(payload: Mapping[str, Any]) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    material = payload["legacy_analysis_material"]
    observed_material_digest = material["material_digest"]
    digest_material = copy.deepcopy(dict(material))
    digest_material.pop("material_digest")
    if observed_material_digest != digest_value(digest_material):
        errors.append(
            {
                "code": "analysis_material_digest_mismatch",
                "location": "$.legacy_analysis_material.material_digest",
                "message": "legacy analysis material digest does not replay",
            }
        )

    public_payload = material["legacy_public_payload"]
    try:
        validate_public_audit(public_payload)
    except Exception as exc:
        errors.append(
            {
                "code": "legacy_public_payload_invalid",
                "location": "$.legacy_analysis_material.legacy_public_payload",
                "message": str(exc),
            }
        )
        return errors
    analysis_ref = payload["legacy_analysis_observation"]["analysis_ref"]
    if (
        public_payload["audit_id"] != analysis_ref["ref_id"]
        or public_payload["schema_version"] != analysis_ref["schema_version"]
        or digest_value(public_payload) != analysis_ref["digest"]
    ):
        errors.append(
            {
                "code": "legacy_public_observation_binding_mismatch",
                "location": "$.legacy_analysis_material.legacy_public_payload",
                "message": "embedded legacy public observation does not match its bound analysis reference",
            }
        )

    internal = material["legacy_internal_trace"]
    attempts = material["analysis_attempts"]
    provider_attempts = internal["analysis_attempts"]
    expected_attempts = [
        ("structured_parse", "structured_record_observation", internal["record"]),
        ("direct_rules", "direct_rule_observations", internal["direct_assessments"]),
        *[
            (item["stage"], "provider_analysis_attempt", item)
            for item in provider_attempts
        ],
    ]
    if len(attempts) != len(expected_attempts) or any(
        attempt["stage"] != stage
        or attempt["source_kind"] != source_kind
        or attempt["observed_material"] != observed_material
        for attempt, (stage, source_kind, observed_material) in zip(
            attempts, expected_attempts, strict=False
        )
    ):
        errors.append(
            {
                "code": "analysis_attempt_denominator_mismatch",
                "location": "$.legacy_analysis_material.analysis_attempts",
                "message": "structured, direct, and every provider analysis attempt must remain indexed without omission",
            }
        )

    unresolved = material["unresolved_observations"]
    inventory = material["trace_inventory"]
    expected_counts = {
        "structured_attempt_count": 1,
        "direct_attempt_count": 1,
        "provider_attempt_count": len(provider_attempts),
        "reassessment_count": len(internal["obligation_reassessments"]),
        "provider_receipt_count": len(internal["provider_execution_receipts"]),
        "initial_unresolved_count": len(internal["initial_unresolved_obligations"]),
        "remaining_unresolved_count": len(internal["remaining_unresolved_obligations"]),
        "provenance_count": len(public_payload["provenance"]),
    }
    if inventory != expected_counts:
        errors.append(
            {
                "code": "analysis_trace_inventory_mismatch",
                "location": "$.legacy_analysis_material.trace_inventory",
                "message": "analysis trace inventory does not match embedded trace material",
            }
        )
    expected_mirrors = (
        (
            material["provider_execution_receipts"],
            internal["provider_execution_receipts"],
        ),
        (material["obligation_reassessments"], internal["obligation_reassessments"]),
        (material["dependency_projections"], internal["dependency_projections"]),
        (material["analyzer_qualifications"], internal["analyzer_qualifications"]),
        (material["lifting_resolutions"], internal["lifting_resolutions"]),
        (unresolved["initial"], internal["initial_unresolved_obligations"]),
        (unresolved["remaining"], internal["remaining_unresolved_obligations"]),
        (unresolved["effective"], internal["unresolved_obligations"]),
        (
            unresolved["public_required_obligation_ids"],
            public_payload["unresolved_required_obligation_ids"],
        ),
        (material["provenance"], public_payload["provenance"]),
    )
    if any(observed != expected for observed, expected in expected_mirrors):
        errors.append(
            {
                "code": "analysis_trace_mirror_mismatch",
                "location": "$.legacy_analysis_material",
                "message": "indexed receipts, reassessments, unresolved items, or provenance differ from the embedded complete observations",
            }
        )
    expected_limitations = {
        "report": internal["limitations"],
        "public_audit_conclusion": public_payload["audit_conclusion"]["limitations"],
        "residual_signals": [
            item.get("limitations", []) for item in internal["residual_signals"]
        ],
        "shadow_signals": [
            item.get("limitations", []) for item in internal["shadow_signals"]
        ],
    }
    if material["limitations_by_source"] != expected_limitations:
        errors.append(
            {
                "code": "analysis_limitation_denominator_mismatch",
                "location": "$.legacy_analysis_material.limitations_by_source",
                "message": "per-source limitations must match the embedded complete traces",
            }
        )
    errors.extend(_analysis_cross_view_errors(payload, public_payload, internal))
    return errors


def _analysis_cross_view_errors(
    payload: Mapping[str, Any],
    public_payload: Mapping[str, Any],
    internal: Mapping[str, Any],
) -> list[dict[str, str]]:
    """Reject independently resealed views that no longer describe one audit."""

    errors: list[dict[str, str]] = []
    result = internal["result"]
    observation = payload["legacy_analysis_observation"]
    expected_observation = {
        "analysis_ref": copy.deepcopy(observation["analysis_ref"]),
        "analysis_mode": internal["analysis_mode"],
        "observed_workflow_disposition": result["workflow"],
        "observed_outcome": result["outcome"],
        "analysis_reasons": copy.deepcopy(result["reasons"]),
        "required_provider_failure_ids": copy.deepcopy(
            result["execution"]["provider_failures"]
        ),
        "authority_status": "legacy_ungoverned_observation_only",
        "formal_authority": "none",
    }
    if observation != expected_observation:
        errors.append(
            {
                "code": "legacy_observation_internal_trace_mismatch",
                "location": "$.legacy_analysis_observation",
                "message": "legacy observation summary must replay from the embedded internal result",
            }
        )

    profile_refs = public_payload["profile_refs"]
    public_obligations = public_payload["obligation_results"]
    internal_obligations = result["obligations"]
    public_core = [
        {
            "obligation_id": item["obligation_id"],
            "active": item["active"],
            "required": item["required"],
            "outcome": item["outcome"],
            "finality": item["finality"],
            "challenge": item["challenge"],
            "coverage_status": item["coverage"]["status"],
        }
        for item in public_obligations
    ]
    internal_core = [
        {
            "obligation_id": item["obligation_id"],
            "active": item["active"],
            "required": item["required"],
            "outcome": item["outcome"],
            "finality": item["finality"],
            "challenge": item["challenge"],
            "coverage_status": item["coverage"]["status"],
        }
        for item in internal_obligations
    ]
    if (
        public_payload["subject_ref"]["entity_id"] != internal["source_id"]
        or len(profile_refs) != 1
        or profile_refs[0]["entity_id"] != internal["profile_id"]
        or profile_refs[0]["entity_version"] != internal["profile_version"]
        or public_payload["analysis_mode"] != internal["analysis_mode"]
        or public_payload["audit_conclusion"]["outcome"] != result["outcome"]
        or public_payload["audit_conclusion"]["finality"] != result["finality"]
        or public_payload["audit_conclusion"]["challenge"] != result["challenge"]
        or public_payload["workflow_disposition"]["status"] != result["workflow"]
        or public_core != internal_core
    ):
        errors.append(
            {
                "code": "legacy_public_internal_trace_mismatch",
                "location": "$.legacy_analysis_material",
                "message": "legacy public subject, profile, conclusion, workflow, and obligation states must replay from one internal result",
            }
        )

    direct = internal["direct_assessments"]
    reassessments = internal["obligation_reassessments"]
    direct_by_id = {str(item["obligation_id"]): item for item in direct}
    reassessment_by_id = {str(item["obligation_id"]): item for item in reassessments}
    result_by_id = {str(item["obligation_id"]): item for item in internal_obligations}
    denominator = set(result_by_id)
    trace_denominator_valid = (
        len(direct_by_id) == len(direct)
        and len(reassessment_by_id) == len(reassessments)
        and len(result_by_id) == len(internal_obligations)
        and set(direct_by_id) == denominator
        and set(reassessment_by_id) == denominator
    )
    trace_values_valid = trace_denominator_valid
    effective_outcome_map = {
        "supported": "satisfied",
        "refuted": "refuted",
        "unresolved": "undetermined",
        "not_applicable": "not_applicable",
        "invalid": "invalid",
    }
    if trace_denominator_valid:
        for obligation_id in sorted(denominator):
            direct_item = direct_by_id[obligation_id]
            reassessment = reassessment_by_id[obligation_id]
            obligation = result_by_id[obligation_id]
            expected_outcome = effective_outcome_map.get(
                str(reassessment["effective_outcome"])
            )
            open_hold = any(
                hold.get("released_by") is None for hold in obligation["holds"]
            )
            if expected_outcome == "not_applicable" and (
                open_hold or obligation["coverage"]["status"] != "complete"
            ):
                expected_outcome = "undetermined"
            expected_finality = (
                "invalid"
                if expected_outcome == "invalid"
                else (
                    "provisional"
                    if expected_outcome == "undetermined"
                    or open_hold
                    or obligation["coverage"]["status"] != "complete"
                    else "terminal"
                )
            )
            if (
                reassessment["original_rule_id"] != direct_item["rule_id"]
                or reassessment["original_outcome"] != direct_item["outcome"]
                or expected_outcome is None
                or obligation["outcome"] != expected_outcome
                or obligation["finality"] != expected_finality
            ):
                trace_values_valid = False
                break
    if not trace_values_valid:
        errors.append(
            {
                "code": "direct_reassessment_result_mismatch",
                "location": "$.legacy_analysis_material.legacy_internal_trace",
                "message": "direct assessments, reassessments, and final obligation states must share one exact denominator and outcome chain",
            }
        )

    expected_public_unresolved = [
        item["obligation_id"]
        for item in internal_obligations
        if item["active"] and item["required"] and not _obligation_is_closed(item)
    ]
    if (
        public_payload["unresolved_required_obligation_ids"]
        != expected_public_unresolved
    ):
        errors.append(
            {
                "code": "public_internal_unresolved_denominator_mismatch",
                "location": "$.legacy_analysis_material.legacy_public_payload.unresolved_required_obligation_ids",
                "message": "public unresolved required obligations must replay from the embedded final obligation denominator",
            }
        )
    return errors


def governed_audit_errors(payload: Mapping[str, Any]) -> tuple[dict[str, str], ...]:
    errors: list[dict[str, str]] = []
    assessment = payload.get("assurance_assessment")
    unresolved = payload.get("unresolved_records")
    if isinstance(assessment, Mapping) and (
        assessment.get("status") != "unresolved"
        or assessment.get("formal_verdict_authority") != "none"
        or assessment.get("workflow_disposition") != "block"
        or assessment.get("allowed_use")
        != ["candidate_finding", "unresolved_escalation"]
        or not isinstance(unresolved, list)
        or not unresolved
    ):
        # Keep the semantic security diagnosis even when the forged values also
        # violate the intentionally unresolved-only public schema.  Otherwise a
        # resealed authority escalation is reported merely as malformed JSON.
        errors.append(
            {
                "code": "unresolved_authority_laundering",
                "location": "$.assurance_assessment",
                "message": "public v1 cannot project a formal, passing, or unresolved-free disposition",
            }
        )
    candidate_findings = payload.get("candidate_findings")
    if isinstance(candidate_findings, list) and any(
        isinstance(finding, Mapping)
        and (
            finding.get("formal_authority") != "none"
            or finding.get("allowed_use") != "candidate_finding"
        )
        for finding in candidate_findings
    ):
        errors.append(
            {
                "code": "candidate_finding_authority_laundering",
                "location": "$.candidate_findings",
                "message": "candidate findings cannot acquire formal authority",
            }
        )

    schema_errors: list[dict[str, str]] = []
    for error in sorted(
        _validator().iter_errors(payload), key=lambda item: list(item.path)
    ):
        location = "$" + "".join(
            f"[{item}]" if isinstance(item, int) else f".{item}" for item in error.path
        )
        schema_errors.append(
            {"code": "schema_error", "location": location, "message": error.message}
        )
    errors.extend(schema_errors)
    if schema_errors:
        return tuple(errors)
    try:
        material_assessment = validate_governance_material_assessment(
            payload["governance_material_assessment"]
        )
    except GovernanceMaterialAssessmentError as exc:
        errors.append(
            {
                "code": "governance_material_assessment_invalid",
                "location": "$.governance_material_assessment",
                "message": str(exc),
            }
        )
        material_assessment = None
    try:
        errors.extend(_analysis_material_errors(payload))
    except (KeyError, TypeError, ValueError, IndexError) as exc:
        errors.append(
            {
                "code": "legacy_analysis_material_not_replayable",
                "location": "$.legacy_analysis_material",
                "message": f"embedded legacy analysis material is not closed: {exc}",
            }
        )
    material = copy.deepcopy(dict(payload))
    observed = material.pop("record_digest")
    if observed != digest_value(material):
        errors.append(
            {
                "code": "record_digest_mismatch",
                "location": "$.record_digest",
                "message": "governed audit digest does not replay",
            }
        )
    subject = payload["subject"]
    if subject["source_id"] != f"sha256:{subject['content_digest']['value']}":
        errors.append(
            {
                "code": "subject_digest_mismatch",
                "location": "$.subject",
                "message": "subject source identity must equal its declared content digest",
            }
        )
    observed_source_digest = {
        "algorithm": "sha256",
        "value": hashlib.sha256(subject["source_text"].encode("utf-8")).hexdigest(),
    }
    if observed_source_digest != subject["content_digest"]:
        errors.append(
            {
                "code": "subject_source_text_digest_mismatch",
                "location": "$.subject.source_text",
                "message": "embedded source text does not match the subject content digest",
            }
        )
    expected_audit_id = _governed_audit_id(payload)
    if payload["audit_id"] != expected_audit_id:
        errors.append(
            {
                "code": "audit_id_mismatch",
                "location": "$.audit_id",
                "message": "audit identity does not replay from the complete semantic record",
            }
        )
    if assessment["blocking_unresolved_count"] != len(unresolved):
        errors.append(
            {
                "code": "blocking_unresolved_count_mismatch",
                "location": "$.assurance_assessment.blocking_unresolved_count",
                "message": "blocking unresolved count must equal the closed unresolved-record denominator",
            }
        )
    try:
        expected_findings = _candidate_finding_values(
            payload["legacy_analysis_material"]["legacy_internal_trace"]
        )
    except (KeyError, TypeError, ValueError, IndexError) as exc:
        expected_findings = None
        errors.append(
            {
                "code": "candidate_finding_source_not_replayable",
                "location": "$.legacy_analysis_material.legacy_internal_trace",
                "message": f"candidate finding sources are not closed: {exc}",
            }
        )
    if (
        expected_findings is not None
        and payload["candidate_findings"] != expected_findings
    ):
        errors.append(
            {
                "code": "candidate_finding_denominator_mismatch",
                "location": "$.candidate_findings",
                "message": "structured, direct, provider, and reassessment findings must replay without omission",
            }
        )
    unresolved_by_id = {
        item["unresolved_id"]: item for item in unresolved if isinstance(item, Mapping)
    }
    observation_ref_id = payload["legacy_analysis_observation"]["analysis_ref"][
        "ref_id"
    ]
    if material_assessment is not None:
        analysis_ref = payload["legacy_analysis_observation"]["analysis_ref"]
        expected_subject_scope_ref = {
            "record_id": subject["source_id"],
            "locator": f"urn:semantic-guard:embedded-source:{subject['source_id']}",
            "content_digest": copy.deepcopy(subject["content_digest"]),
        }
        if (
            material_assessment["observation_digest"] != analysis_ref["digest"]
            or material_assessment["authority_source_ids"]
            != payload["governance_resolution"]["required_authority_source_ids"]
            or material_assessment["subject_scope_ref"] != expected_subject_scope_ref
        ):
            errors.append(
                {
                    "code": "governance_material_subject_binding_mismatch",
                    "location": "$.governance_material_assessment",
                    "message": "governance material must bind the exact observation, authority denominator, and embedded subject",
                }
            )
        adapted_h1 = material_assessment["engineering_rule_governance"][
            "validated_record"
        ]
        expected_governance = _governance_summary(
            (
                adapted_h1["governance_bundle"]
                if isinstance(adapted_h1, Mapping)
                else None
            ),
            observation_digest=analysis_ref["digest"],
            authority_source_ids=material_assessment["authority_source_ids"],
        )
        if payload["governance_resolution"] != expected_governance:
            errors.append(
                {
                    "code": "governance_resolution_material_mismatch",
                    "location": "$.governance_resolution",
                    "message": "governance resolution must replay from the embedded governance material assessment",
                }
            )
    if (
        len(unresolved_by_id) != len(unresolved)
        or not set(_REQUIRED_UNRESOLVED_KINDS) <= set(unresolved_by_id)
        or any(
            unresolved_by_id[unresolved_id]["uncertainty_kind"] != uncertainty_kind
            or unresolved_by_id[unresolved_id]["blocking_status"]
            != "blocking_positive_assurance"
            or unresolved_by_id[unresolved_id]["evidence_refs"] != [observation_ref_id]
            for unresolved_id, uncertainty_kind in _REQUIRED_UNRESOLVED_KINDS.items()
            if unresolved_id in unresolved_by_id
        )
    ):
        errors.append(
            {
                "code": "unresolved_denominator_mismatch",
                "location": "$.unresolved_records",
                "message": "public v1 must retain the closed H1, H2, ENV-PATH, and D7 blocking denominator",
            }
        )
    try:
        expected_requirement_unresolved = _requirement_unresolved_records(
            payload["legacy_analysis_material"]["legacy_internal_trace"],
            observation_ref_id=observation_ref_id,
        )
    except (KeyError, TypeError, ValueError, IndexError):
        expected_requirement_unresolved = []
    observed_requirement_unresolved = [
        item
        for item in unresolved
        if item["unresolved_id"].startswith("unresolved.requirement-obligation.")
    ]
    expected_all_ids = {
        *_REQUIRED_UNRESOLVED_KINDS,
        *[item["unresolved_id"] for item in expected_requirement_unresolved],
    }
    if (
        observed_requirement_unresolved != expected_requirement_unresolved
        or set(unresolved_by_id) != expected_all_ids
    ):
        errors.append(
            {
                "code": "requirement_unresolved_denominator_mismatch",
                "location": "$.unresolved_records",
                "message": "every remaining requirement obligation must retain one closed unresolved record",
            }
        )
    if payload["authority_boundary"] != _AUTHORITY_BOUNDARY:
        errors.append(
            {
                "code": "authority_boundary_mismatch",
                "location": "$.authority_boundary",
                "message": "governed audit authority boundary is fixed",
            }
        )
    if payload["limitations"] != list(_LIMITATIONS):
        errors.append(
            {
                "code": "limitations_mismatch",
                "location": "$.limitations",
                "message": "public v1 limitations are fixed and cannot be replaced or removed",
            }
        )
    return tuple(errors)


def validate_governed_audit(payload: Mapping[str, Any]) -> dict[str, Any]:
    errors = governed_audit_errors(payload)
    if errors:
        raise GovernedAuditValidationError(errors)
    return copy.deepcopy(dict(payload))


__all__ = [
    "SCHEMA_VERSION",
    "LEGACY_OUTPUT_ENVELOPE_SCHEMA_VERSION",
    "GovernedAuditValidationError",
    "digest_value",
    "governed_audit_errors",
    "legacy_output_errors",
    "project_governed_audit",
    "validate_governed_audit",
    "validate_legacy_output",
    "wrap_legacy_output",
]
