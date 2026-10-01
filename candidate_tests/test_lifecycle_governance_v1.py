from __future__ import annotations

import copy
import unittest

from semantic_guard_vnext.assurance_roles import (
    AssuranceRoleError,
    build_review_record,
    build_role_binding,
    validate_review_record,
)
from semantic_guard_vnext.lifecycle_governance import (
    AUTHORITY_BOUNDARY,
    CORE_STAGES,
    LifecycleGovernanceError,
    _digest,
    assess_candidate_lifecycle_runtime,
    build_applicability_record,
    build_extension_applicability_record,
    build_runtime_rule_binding,
    build_stage_profile,
    build_stage_registry,
    build_tailoring,
    lifecycle_governance_schema,
    resolve_lifecycle_runtime,
    validate_runtime_resolution,
)
from semantic_guard_vnext.lifecycle_occurrences import (
    LifecycleOccurrenceError,
    build_artifact_manifest,
    build_completion_claim,
    build_handoff,
    build_occurrence_evidence,
    build_stage_occurrence,
    build_subject_entity,
    build_subject_snapshot,
    entity_ref,
    snapshot_ref,
    validate_artifact_manifest_closed,
    validate_completion_claim,
    validate_handoff_closed,
    validate_occurrence_evidence,
    validate_stage_occurrence_closed,
    validate_subject_entity,
)
from semantic_guard_vnext.lifecycle_requalification import (
    LifecycleRequalificationError,
    build_impact_closure,
    build_occurrence_relation,
    validate_impact_closure,
)


NOW = "2026-07-18T12:00:00+09:00"
LATER = "2026-07-18T12:01:00+09:00"


def digest(label: str) -> dict[str, str]:
    return _digest({"label": label})


def identity(label: str, version: str = "1") -> dict[str, object]:
    return {
        "entity_id": label,
        "entity_version": version,
        "content_digest": digest(f"identity:{label}:{version}"),
    }


def record(label: str, content: str | None = None) -> dict[str, object]:
    return {
        "record_id": label,
        "locator": f"urn:test:{label}",
        "content_digest": digest(content or label),
    }


def decision(
    *,
    decision_id: str,
    kind: str,
    target_id: str,
    target_version: str,
    basis_digest: dict[str, str],
    status: str = "accept",
    resolved: bool = True,
) -> dict[str, object]:
    return {
        "decision_id": decision_id,
        "decision_kind": kind,
        "status": status,
        "target_id": target_id,
        "target_version": target_version,
        "target_basis_digest": copy.deepcopy(basis_digest),
        "decision_maker_ref": identity("human-owner"),
        "trusted_entry_ref": record(f"entry-{decision_id}"),
        "entry_resolution_state": "resolved" if resolved else "unresolved",
        "decided_at": NOW,
    }


def trusted_decision_verifier(value) -> bool:
    """Test stand-in for a trust-domain decision service, not JSON self-claim."""

    return bool(
        value.get("trusted_entry_ref", {}).get("record_id", "").startswith("entry-")
        and value.get("decision_maker_ref", {}).get("entity_id") == "human-owner"
    )


trusted_decision_verifier.verifier_ref = record("trusted-decision-verifier")


def trusted_identity_verifier(context) -> bool:
    return bool(
        context.get("reviewer_kind") == "human"
        and context.get("reviewer_ref", {}).get("entity_id") == "human-reviewer"
        and context.get("subject_executor_ref", {}).get("entity_id") == "agent"
        and context.get("target_ref", {}).get("record_id") == "target"
    )


trusted_identity_verifier.verifier_ref = record("trusted-identity-verifier")


def rejecting_identity_verifier(context) -> bool:
    return False


rejecting_identity_verifier.verifier_ref = record("rejecting-identity-verifier")


def failing_identity_verifier(context) -> bool:
    raise RuntimeError("identity service unavailable")


failing_identity_verifier.verifier_ref = record("failing-identity-verifier")


def unbound_identity_verifier(context) -> bool:
    return True


def unbound_true_verifier(context) -> bool:
    return True


def trusted_harness_verifier(context) -> bool:
    return bool(
        context.get("reported_observation_method") == "claimed_execution_harness"
        and context.get("environment_ref", {}).get("entity_id") == "environment"
        and [item["record_id"] for item in context.get("raw_result_refs", [])]
        == ["raw-result"]
        and context.get("observer_role_binding_ref", {}).get("record_id")
        == "harness-binding"
        and context.get("observer_authority_ref", {}).get("record_id")
        == "harness-authority"
    )


trusted_harness_verifier.verifier_ref = record("trusted-harness-verifier")


def trusted_completion_verifier(context) -> bool:
    return bool(
        context.get("reported_technical_completion_state") == "completed"
        and [item["record_id"] for item in context.get("obligation_result_refs", [])]
        == ["obligation-results"]
        and [
            item["record_id"] for item in context.get("verification_evidence_refs", [])
        ]
        == ["verification-results"]
        and not context.get("unresolved_refs")
    )


trusted_completion_verifier.verifier_ref = record("trusted-completion-verifier")


def trusted_graph_verifier(context) -> bool:
    return bool(
        context.get("reported_graph_completeness") == "complete"
        and context.get("graph_manifest_ref", {}).get("record_id")
        == "dependency-graph-manifest"
        and context.get("known_denominator_refs")
        and context.get("dependency_edges")
    )


trusted_graph_verifier.verifier_ref = record("trusted-graph-verifier")


def adopted_rule_requirement() -> dict[str, object]:
    basis = digest("rule-basis")
    return {
        "rule_id": "RULE-001",
        "rule_version": "1",
        "content_digest": digest("rule-content"),
        "basis_digest": basis,
        "reported_adoption_status": "adopted",
        "human_adoption_ref": decision(
            decision_id="adopt-rule",
            kind="adopt_engineering_rule",
            target_id="RULE-001",
            target_version="1",
            basis_digest=basis,
        ),
        "applicability": "all lifecycle stage candidate analyses",
        "required_authorities": ["candidate_finding", "unresolved_escalation"],
    }


def make_profile(
    stage: str,
    *,
    adopted: bool = True,
    profile_id: str | None = None,
) -> dict[str, object]:
    resolved_profile_id = profile_id or f"profile-{stage}"
    args = {
        "profile_id": resolved_profile_id,
        "profile_version": "1",
        "stage_id": stage,
        "purpose": f"purpose for {stage}",
        "entry_conditions": [f"{stage} entry is identified"],
        "exit_conditions": [f"{stage} exit is evidenced"],
        "applicability_policy": "use the adopted tailoring record",
        "input_manifest_contract": record(f"input-contract-{stage}"),
        "output_manifest_contract": record(f"output-contract-{stage}"),
        "obligations": [f"preserve {stage} obligations"],
        "engineering_basis_refs": [adopted_rule_requirement()],
        "validation_obligations": [f"validate {stage} manifest"],
        "requalification_triggers": [f"{stage} subject changes"],
        "implementation_digest": digest(f"implementation-{stage}"),
        "trusted_decision_verifier": trusted_decision_verifier,
    }
    candidate = build_stage_profile(**args)
    if not adopted:
        return candidate
    return build_stage_profile(
        **args,
        reported_adoption_status="adopted",
        human_adoption_ref=decision(
            decision_id=f"adopt-{resolved_profile_id}",
            kind="adopt_stage_profile",
            target_id=resolved_profile_id,
            target_version="1",
            basis_digest=candidate["basis_digest"],
        ),
    )


def make_profiles(*, adopted: bool = True) -> dict[str, dict[str, object]]:
    return {stage: make_profile(stage, adopted=adopted) for stage in CORE_STAGES}


def make_registry(
    profiles: dict[str, dict[str, object]],
    *,
    adopted: bool = True,
    extension_profiles=(),
):
    candidate = build_stage_registry(
        registry_id="core-lifecycle",
        registry_version="1",
        core_profiles=profiles,
        extension_profiles=extension_profiles,
        trusted_decision_verifier=trusted_decision_verifier,
    )
    if not adopted:
        return candidate
    return build_stage_registry(
        registry_id="core-lifecycle",
        registry_version="1",
        core_profiles=profiles,
        extension_profiles=extension_profiles,
        reported_adoption_status="adopted",
        human_adoption_ref=decision(
            decision_id="adopt-registry",
            kind="adopt_stage_registry",
            target_id="core-lifecycle",
            target_version="1",
            basis_digest=candidate["basis_digest"],
        ),
        trusted_decision_verifier=trusted_decision_verifier,
    )


def required_applicability(stage: str):
    return build_applicability_record(
        stage_id=stage, reported_applicability_state="required"
    )


def make_tailoring(
    scope: dict[str, object],
    *,
    adopted: bool = True,
    records=None,
    extension_stage_applicability=(),
):
    applicability = records or [required_applicability(stage) for stage in CORE_STAGES]
    args = {
        "tailoring_id": "tailoring-case-1",
        "tailoring_version": "1",
        "subject_scope_ref": scope,
        "risk_class": "medium",
        "core_stage_applicability": applicability,
        "basis_refs": [record("tailoring-basis")],
        "decision_owner_ref": identity("human-owner"),
        "reactivation_triggers": ["subject or risk class changes"],
        "extension_stage_applicability": extension_stage_applicability,
        "trusted_decision_verifier": trusted_decision_verifier,
    }
    candidate = build_tailoring(**args)
    if not adopted:
        return candidate
    return build_tailoring(
        **args,
        reported_adoption_status="adopted",
        human_adoption_ref=decision(
            decision_id="adopt-tailoring",
            kind="adopt_lifecycle_tailoring",
            target_id="tailoring-case-1",
            target_version="1",
            basis_digest=candidate["basis_digest"],
        ),
    )


def make_rule_binding(*, adopted: bool = True, wrong_content: bool = False):
    requirement = adopted_rule_requirement()
    return build_runtime_rule_binding(
        rule_id="RULE-001",
        rule_version="1",
        content_digest=(
            digest("wrong") if wrong_content else requirement["content_digest"]
        ),
        basis_digest=requirement["basis_digest"],
        implementation_digest=digest("rule-implementation"),
        reported_adoption_status="adopted" if adopted else "candidate",
        human_adoption_ref=(requirement["human_adoption_ref"] if adopted else None),
        authority={
            "candidate_finding": True,
            "unresolved_escalation": True,
            "nonconformance": False,
            "satisfaction": False,
            "final_verdict": False,
        },
        trusted_decision_verifier=trusted_decision_verifier,
    )


def axes(
    *,
    execution: str = "completed",
    evidence: str = "assessed",
    decision_requirement: str = "none",
    human_decision: str = "none",
    human_decision_ref=None,
    disposition: str = "none",
    disposition_ref=None,
):
    return {
        "applicability_state": "required",
        "execution_state": execution,
        "evidence_state": evidence,
        "currency_state": "current",
        "decision_requirement": decision_requirement,
        "human_decision": human_decision,
        "human_decision_ref": human_decision_ref,
        "human_disposition": disposition,
        "human_disposition_ref": disposition_ref,
    }


class TestAssuranceRoles(unittest.TestCase):
    def test_role_capability_ceiling_blocks_cross_surface_power(self):
        with self.assertRaises(AssuranceRoleError):
            build_role_binding(
                binding_id="audit-overreach",
                actor_ref=identity("audit"),
                role_surface="audit_system",
                granted_capabilities=["adopt"],
                authority_ref=record("claimed-authority"),
            )
        with self.assertRaises(AssuranceRoleError):
            build_role_binding(
                binding_id="harness-overreach",
                actor_ref=identity("harness"),
                role_surface="execution_harness",
                granted_capabilities=["evaluate_under_adopted_rules"],
                authority_ref=record("claimed-authority"),
            )

    def test_capability_claim_requires_external_authority(self):
        with self.assertRaises(AssuranceRoleError):
            build_role_binding(
                binding_id="agent-no-authority",
                actor_ref=identity("agent"),
                role_surface="ai_agent",
                granted_capabilities=["execute_authorized"],
            )

    def test_review_independence_is_derived_and_old_review_is_not_promoted(self):
        same = identity("reviewer")
        review = build_review_record(
            review_id="self-review",
            reviewer_ref=same,
            reviewer_kind="human",
            subject_executor_ref=same,
            reviewer_implementation_ref=identity("impl-a"),
            subject_implementation_ref=identity("impl-b"),
            reviewer_runtime_ref=identity("runtime-a"),
            subject_runtime_ref=identity("runtime-b"),
            target_ref=record("target"),
            identity_resolution_state="resolved",
            identity_resolver_ref=record("identity-resolver"),
            independence_evidence_refs=[record("independence-evidence")],
        )
        self.assertEqual(review["review_independence"], "self_review")
        self.assertEqual(review["identity_trust_state"], "unresolved")
        self.assertEqual(review["identity_verifier_claim"], "not_supplied")
        self.assertIsNone(review["identity_verifier_ref"])
        with self.assertRaises(AssuranceRoleError):
            validate_review_record(
                {
                    "schema_version": "repair-independent-review/v1",
                    "review_independence": "independent",
                }
            )

    def test_self_claimed_human_identity_never_establishes_independence(self):
        review = build_review_record(
            review_id="self-claimed-human",
            reviewer_ref=identity("human-reviewer"),
            reviewer_kind="human",
            subject_executor_ref=identity("agent"),
            reviewer_implementation_ref=identity("impl"),
            subject_implementation_ref=identity("impl"),
            reviewer_runtime_ref=identity("runtime"),
            subject_runtime_ref=identity("runtime"),
            target_ref=record("target"),
            identity_resolution_state="resolved",
            identity_resolver_ref=record("caller-selected-identity-resolver"),
            independence_evidence_refs=[record("caller-selected-independence")],
        )
        self.assertEqual(review["review_independence"], "isolated_context_review")
        self.assertEqual(review["identity_trust_state"], "unresolved")
        self.assertEqual(review["identity_verifier_claim"], "not_supplied")
        self.assertIsNone(review["identity_verifier_ref"])
        self.assertEqual(review["formal_adoption_authority"], "none")

        forged = copy.deepcopy(review)
        forged["review_independence"] = "independent_human_review"
        forged["review_digest"] = _digest(
            {key: value for key, value in forged.items() if key != "review_digest"}
        )
        with self.assertRaises(AssuranceRoleError):
            validate_review_record(forged)

    def test_content_addressed_true_callback_cannot_create_independent_human_review(
        self,
    ):
        review = build_review_record(
            review_id="externally-verified-human",
            reviewer_ref=identity("human-reviewer"),
            reviewer_kind="human",
            subject_executor_ref=identity("agent"),
            reviewer_implementation_ref=identity("human-review-process"),
            subject_implementation_ref=identity("agent-implementation"),
            reviewer_runtime_ref=identity("human-review-runtime"),
            subject_runtime_ref=identity("agent-runtime"),
            target_ref=record("target"),
            identity_resolution_state="resolved",
            identity_resolver_ref=record("identity-resolver"),
            independence_evidence_refs=[record("independence-evidence")],
            trusted_identity_verifier=trusted_identity_verifier,
        )
        self.assertEqual(review["review_independence"], "separate_runtime_review")
        self.assertEqual(review["identity_trust_state"], "unresolved")
        self.assertEqual(review["identity_verifier_claim"], "verifier_claim_accepted")
        self.assertEqual(
            review["identity_verifier_ref"],
            trusted_identity_verifier.verifier_ref,
        )
        self.assertEqual(review["trust_root_resolution_state"], "not_integrated")
        self.assertIsNone(review["trust_root_ref"])
        self.assertEqual(review["formal_adoption_authority"], "none")
        with self.assertRaises(AssuranceRoleError):
            validate_review_record(review)
        self.assertEqual(
            validate_review_record(
                review, trusted_identity_verifier=trusted_identity_verifier
            ),
            review,
        )

    def test_false_exception_and_unbound_identity_verifiers_fail_closed(self):
        common = {
            "reviewer_ref": identity("human-reviewer"),
            "reviewer_kind": "human",
            "subject_executor_ref": identity("agent"),
            "reviewer_implementation_ref": identity("human-review-process"),
            "subject_implementation_ref": identity("agent-implementation"),
            "reviewer_runtime_ref": identity("runtime"),
            "subject_runtime_ref": identity("runtime"),
            "target_ref": record("target"),
            "identity_resolution_state": "resolved",
            "identity_resolver_ref": record("identity-resolver"),
            "independence_evidence_refs": [record("independence-evidence")],
        }
        for label, verifier, expected_claim in (
            (
                "rejecting",
                rejecting_identity_verifier,
                "verifier_claim_rejected",
            ),
            ("failing", failing_identity_verifier, "verifier_unavailable"),
            ("unbound", unbound_identity_verifier, "verifier_ref_invalid"),
        ):
            with self.subTest(verifier=label):
                review = build_review_record(
                    review_id=f"{label}-identity-verifier",
                    **common,
                    trusted_identity_verifier=verifier,
                )
                self.assertEqual(
                    review["review_independence"], "isolated_context_review"
                )
                self.assertEqual(
                    review["identity_trust_state"],
                    "unresolved",
                )
                self.assertEqual(review["identity_verifier_claim"], expected_claim)
                self.assertEqual(review["formal_adoption_authority"], "none")


class TestGovernance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profiles = make_profiles()
        cls.registry = make_registry(cls.profiles)
        cls.scope = record("case-scope")
        cls.tailoring = make_tailoring(cls.scope)

    def test_schema_is_valid_and_registry_has_exact_ten_stage_denominator(self):
        self.assertIn("stageRegistry", lifecycle_governance_schema()["$defs"])
        self.assertEqual(tuple(self.registry["core_stage_order"]), CORE_STAGES)
        with self.assertRaises(LifecycleGovernanceError):
            build_stage_registry(
                registry_id="bad-registry",
                registry_version="1",
                core_profiles={
                    k: v for k, v in self.profiles.items() if k != "completion"
                },
            )

    def test_registry_rejects_stage_profile_substitution(self):
        substituted = dict(self.profiles)
        substituted["request"] = self.profiles["action"]
        with self.assertRaises(LifecycleGovernanceError):
            build_stage_registry(
                registry_id="substituted-registry",
                registry_version="1",
                core_profiles=substituted,
                trusted_decision_verifier=trusted_decision_verifier,
            )

    def test_authority_boundary_is_candidate_only(self):
        self.assertEqual(self.registry["authority_boundary"], AUTHORITY_BOUNDARY)
        self.assertEqual(self.registry["reported_adoption_status"], "adopted")
        self.assertNotIn("adoption_status", self.registry)
        self.assertEqual(
            self.registry["authority_boundary"]["direct_command_authority"],
            "prohibited",
        )

    def test_conditional_applicability_fails_closed_when_incomplete(self):
        with self.assertRaises(LifecycleGovernanceError):
            build_applicability_record(
                stage_id="verification",
                reported_applicability_state="conditional",
                activation_conditions=["risk is high"],
            )

    def test_not_applicable_requires_exact_human_decision(self):
        denominator = record("core-denominator")
        with self.assertRaises(LifecycleGovernanceError):
            build_applicability_record(
                stage_id="exploration",
                reported_applicability_state="not_applicable",
                denominator_ref=denominator,
                rationale="no unknown domain remains",
                decision_owner_ref=identity("human-owner"),
                authority_ref=record("human-authority"),
                decision_evidence_refs=[record("na-evidence")],
                reactivation_triggers=["domain changes"],
                review_at=LATER,
            )
        valid = build_applicability_record(
            stage_id="exploration",
            reported_applicability_state="not_applicable",
            denominator_ref=denominator,
            rationale="no unknown domain remains",
            decision_owner_ref=identity("human-owner"),
            authority_ref=record("human-authority"),
            decision_record_ref=decision(
                decision_id="na-exploration",
                kind="stage_not_applicable",
                target_id="exploration",
                target_version="1",
                basis_digest=denominator["content_digest"],
            ),
            decision_evidence_refs=[record("na-evidence")],
            reactivation_triggers=["domain changes"],
            review_at=LATER,
            trusted_decision_verifier=trusted_decision_verifier,
        )
        self.assertEqual(valid["reported_applicability_state"], "not_applicable")
        self.assertNotIn("applicability_state", valid)
        records = [
            valid if stage == "exploration" else required_applicability(stage)
            for stage in CORE_STAGES
        ]
        resolution = resolve_lifecycle_runtime(
            registry=self.registry,
            tailoring=make_tailoring(self.scope, records=records),
            subject_scope_ref=self.scope,
            profiles=list(self.profiles.values()),
            rule_bindings=[make_rule_binding()],
            trusted_decision_verifier=trusted_decision_verifier,
        )
        self.assertIn("exploration", resolution["required_stage_denominator"])
        self.assertTrue(
            any(
                item["item_id"] == "applicability:exploration"
                and item["state"] == "unresolved"
                and "not_applicable_decision_trust_root_unresolved" in item["reasons"]
                for item in resolution["resolution_items"]
            )
        )

    def test_waiver_is_not_stage_satisfaction(self):
        denominator = record("waiver-basis")
        waived = build_applicability_record(
            stage_id="diff",
            reported_applicability_state="required",
            denominator_ref=denominator,
            reported_human_disposition="waived",
            human_disposition_ref=decision(
                decision_id="waive-diff",
                kind="waive_stage",
                target_id="diff",
                target_version="1",
                basis_digest=denominator["content_digest"],
                status="waive",
            ),
            trusted_decision_verifier=trusted_decision_verifier,
        )
        self.assertEqual(waived["reported_human_disposition"], "waived")
        self.assertNotIn("human_disposition", waived)
        records = [
            waived if stage == "diff" else required_applicability(stage)
            for stage in CORE_STAGES
        ]
        tailoring = make_tailoring(self.scope, records=records)
        resolution = resolve_lifecycle_runtime(
            registry=self.registry,
            tailoring=tailoring,
            subject_scope_ref=self.scope,
            profiles=list(self.profiles.values()),
            rule_bindings=[make_rule_binding()],
            trusted_decision_verifier=trusted_decision_verifier,
        )
        self.assertEqual(resolution["resolution_state"], "unresolved")
        self.assertTrue(
            any(
                "waiver_does_not_establish_stage_satisfaction" in item["reasons"]
                for item in resolution["resolution_items"]
            )
        )

    def test_true_decision_callback_never_resolves_runtime_or_grants_authority(self):
        resolution = resolve_lifecycle_runtime(
            registry=self.registry,
            tailoring=self.tailoring,
            subject_scope_ref=self.scope,
            profiles=list(self.profiles.values()),
            rule_bindings=[make_rule_binding()],
            trusted_decision_verifier=trusted_decision_verifier,
        )
        self.assertEqual(resolution["resolution_state"], "unresolved")
        self.assertEqual(resolution["formal_authority"], "none")
        self.assertEqual(resolution["allowed_use"], "candidate_and_unresolved_only")
        self.assertEqual(
            resolution["decision_verifier_claim"],
            "callback_supplied_not_trust_root",
        )
        self.assertEqual(resolution["trust_root_resolution_state"], "not_integrated")
        self.assertTrue(
            any(
                item["item_kind"] == "trust_root" and item["state"] == "unresolved"
                for item in resolution["resolution_items"]
            )
        )

    def test_historical_runtime_name_is_only_a_candidate_assessment_alias(self):
        arguments = {
            "registry": self.registry,
            "tailoring": self.tailoring,
            "subject_scope_ref": self.scope,
            "profiles": list(self.profiles.values()),
            "rule_bindings": [make_rule_binding()],
        }
        preferred = assess_candidate_lifecycle_runtime(**arguments)
        compatibility = resolve_lifecycle_runtime(**arguments)

        self.assertEqual(compatibility, preferred)
        self.assertEqual(preferred["resolution_state"], "unresolved")
        self.assertEqual(preferred["formal_authority"], "none")

    def test_embedded_resolved_flag_is_not_trusted_without_external_verifier(self):
        resolution = resolve_lifecycle_runtime(
            registry=self.registry,
            tailoring=self.tailoring,
            subject_scope_ref=self.scope,
            profiles=list(self.profiles.values()),
            rule_bindings=[make_rule_binding()],
        )
        self.assertEqual(resolution["resolution_state"], "unresolved")
        reasons = {
            reason
            for item in resolution["resolution_items"]
            for reason in item["reasons"]
        }
        self.assertIn("registry_adoption_trust_root_unresolved", reasons)
        self.assertIn("tailoring_adoption_trust_root_unresolved", reasons)
        self.assertIn("profile_adoption_trust_root_unresolved", reasons)
        self.assertIn("rule_adoption_trust_root_unresolved", reasons)

    def test_adopted_binding_is_only_a_reported_claim_without_trust_root(self):
        requirement = adopted_rule_requirement()
        binding = build_runtime_rule_binding(
            rule_id="RULE-001",
            rule_version="1",
            content_digest=requirement["content_digest"],
            basis_digest=requirement["basis_digest"],
            implementation_digest=digest("rule-implementation"),
            reported_adoption_status="adopted",
            human_adoption_ref=requirement["human_adoption_ref"],
            authority={
                "candidate_finding": True,
                "unresolved_escalation": True,
                "nonconformance": False,
                "satisfaction": False,
                "final_verdict": False,
            },
        )
        self.assertEqual(binding["reported_adoption_status"], "adopted")
        self.assertNotIn("adoption_status", binding)
        resolution = resolve_lifecycle_runtime(
            registry=self.registry,
            tailoring=self.tailoring,
            subject_scope_ref=self.scope,
            profiles=list(self.profiles.values()),
            rule_bindings=[binding],
            trusted_decision_verifier=trusted_decision_verifier,
        )
        self.assertEqual(resolution["resolution_state"], "unresolved")

    def test_runtime_resolver_refuses_missing_or_nonexact_rule(self):
        missing = resolve_lifecycle_runtime(
            registry=self.registry,
            tailoring=self.tailoring,
            subject_scope_ref=self.scope,
            profiles=list(self.profiles.values()),
            rule_bindings=[],
            trusted_decision_verifier=trusted_decision_verifier,
        )
        self.assertEqual(missing["resolution_state"], "unresolved")
        wrong = resolve_lifecycle_runtime(
            registry=self.registry,
            tailoring=self.tailoring,
            subject_scope_ref=self.scope,
            profiles=list(self.profiles.values()),
            rule_bindings=[make_rule_binding(wrong_content=True)],
            trusted_decision_verifier=trusted_decision_verifier,
        )
        self.assertEqual(wrong["resolution_state"], "unresolved")
        self.assertGreater(wrong["blocking_unresolved_count"], 0)

    def test_runtime_resolver_marks_supplied_rule_outside_required_denominator(self):
        extra = build_runtime_rule_binding(
            rule_id="RULE-EXTRA",
            rule_version="1",
            content_digest=digest("extra-rule-content"),
            basis_digest=digest("extra-rule-basis"),
            implementation_digest=digest("extra-rule-implementation"),
            authority={
                "candidate_finding": True,
                "unresolved_escalation": True,
                "nonconformance": False,
                "satisfaction": False,
                "final_verdict": False,
            },
        )
        resolution = resolve_lifecycle_runtime(
            registry=self.registry,
            tailoring=self.tailoring,
            subject_scope_ref=self.scope,
            profiles=list(self.profiles.values()),
            rule_bindings=[make_rule_binding(), extra],
            trusted_decision_verifier=trusted_decision_verifier,
        )

        self.assertEqual(
            resolution["required_rule_denominator"],
            [{"rule_id": "RULE-001", "rule_version": "1"}],
        )
        self.assertEqual(
            {
                (item["rule_id"], item["rule_version"])
                for item in resolution["supplied_rule_bindings"]
            },
            {("RULE-001", "1"), ("RULE-EXTRA", "1")},
        )
        extra_item = next(
            item
            for item in resolution["resolution_items"]
            if item["item_id"] == "rule:unrequired:RULE-EXTRA:1"
        )
        self.assertEqual(extra_item["state"], "unresolved")
        self.assertEqual(extra_item["reasons"], ["runtime_rule_not_required"])

        omitted = copy.deepcopy(resolution)
        omitted["resolution_items"].remove(extra_item)
        omitted["blocking_unresolved_count"] -= 1
        omitted["resolution_digest"] = _digest(
            {key: value for key, value in omitted.items() if key != "resolution_digest"}
        )
        with self.assertRaisesRegex(
            LifecycleGovernanceError, "unrequired rule findings"
        ):
            validate_runtime_resolution(omitted)

    def test_runtime_resolver_refuses_candidate_registry_and_scope_substitution(self):
        candidate_registry = make_registry(self.profiles, adopted=False)
        substituted_scope = record("case-scope-copy", content="case-scope")
        resolution = resolve_lifecycle_runtime(
            registry=candidate_registry,
            tailoring=self.tailoring,
            subject_scope_ref=substituted_scope,
            profiles=list(self.profiles.values()),
            rule_bindings=[make_rule_binding()],
            trusted_decision_verifier=trusted_decision_verifier,
        )
        self.assertEqual(resolution["resolution_state"], "unresolved")
        reasons = {
            reason
            for item in resolution["resolution_items"]
            for reason in item["reasons"]
        }
        self.assertIn("registry_not_adopted", reasons)
        self.assertIn("subject_scope_not_exact", reasons)

    def test_adopted_extension_is_part_of_runtime_stage_denominator(self):
        extension = make_profile("architecture")
        extension_applicability = build_extension_applicability_record(
            profile=extension,
            applicability=required_applicability("architecture"),
            trusted_decision_verifier=trusted_decision_verifier,
        )
        registry = make_registry(self.profiles, extension_profiles=[extension])
        tailoring = make_tailoring(
            self.scope,
            extension_stage_applicability=[extension_applicability],
        )
        resolution = resolve_lifecycle_runtime(
            registry=registry,
            tailoring=tailoring,
            subject_scope_ref=self.scope,
            profiles=[*self.profiles.values(), extension],
            rule_bindings=[make_rule_binding()],
            trusted_decision_verifier=trusted_decision_verifier,
        )
        self.assertEqual(resolution["resolution_state"], "unresolved")
        self.assertIn("architecture", resolution["required_stage_denominator"])

    def test_missing_or_extra_extension_enumeration_is_unresolved(self):
        extension = make_profile("architecture")
        extension_applicability = build_extension_applicability_record(
            profile=extension,
            applicability=required_applicability("architecture"),
            trusted_decision_verifier=trusted_decision_verifier,
        )
        missing = resolve_lifecycle_runtime(
            registry=make_registry(self.profiles, extension_profiles=[extension]),
            tailoring=self.tailoring,
            subject_scope_ref=self.scope,
            profiles=[*self.profiles.values(), extension],
            rule_bindings=[make_rule_binding()],
            trusted_decision_verifier=trusted_decision_verifier,
        )
        extra = resolve_lifecycle_runtime(
            registry=self.registry,
            tailoring=make_tailoring(
                self.scope,
                extension_stage_applicability=[extension_applicability],
            ),
            subject_scope_ref=self.scope,
            profiles=[*self.profiles.values(), extension],
            rule_bindings=[make_rule_binding()],
            trusted_decision_verifier=trusted_decision_verifier,
        )
        self.assertEqual(missing["resolution_state"], "unresolved")
        self.assertEqual(extra["resolution_state"], "unresolved")
        missing_reasons = {
            reason for item in missing["resolution_items"] for reason in item["reasons"]
        }
        extra_reasons = {
            reason for item in extra["resolution_items"] for reason in item["reasons"]
        }
        self.assertIn("extension_applicability_not_enumerated", missing_reasons)
        self.assertIn("extension_profile_not_registered", extra_reasons)
        self.assertIn("runtime_profile_not_registered", extra_reasons)

    def test_extension_profile_reference_mismatch_is_unresolved(self):
        registered = make_profile("architecture")
        substituted = make_profile(
            "architecture",
            profile_id="profile-architecture-substituted",
        )
        substituted_applicability = build_extension_applicability_record(
            profile=substituted,
            applicability=required_applicability("architecture"),
            trusted_decision_verifier=trusted_decision_verifier,
        )
        resolution = resolve_lifecycle_runtime(
            registry=make_registry(
                self.profiles,
                extension_profiles=[registered],
            ),
            tailoring=make_tailoring(
                self.scope,
                extension_stage_applicability=[substituted_applicability],
            ),
            subject_scope_ref=self.scope,
            profiles=[*self.profiles.values(), registered, substituted],
            rule_bindings=[make_rule_binding()],
            trusted_decision_verifier=trusted_decision_verifier,
        )
        reasons = {
            reason
            for item in resolution["resolution_items"]
            for reason in item["reasons"]
        }
        self.assertEqual(resolution["resolution_state"], "unresolved")
        self.assertIn("extension_profile_ref_not_exact", reasons)


class TestOccurrences(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.subject = build_subject_entity(
            entity_id="subject-A",
            entity_kind="software-system",
            label="same-label",
            created_at=NOW,
        )
        cls.snapshot = build_subject_snapshot(
            snapshot_id="snapshot-A1",
            subject_entity_id="subject-A",
            snapshot_version="1",
            content_digest=digest("snapshot-content"),
            captured_at=NOW,
        )
        cls.scope = record("occurrence-scope")
        cls.manifest = build_artifact_manifest(
            manifest_id="manifest-A",
            manifest_version="1",
            subject_entity_ref=entity_ref(cls.subject),
            subject_snapshot_ref=snapshot_ref(cls.snapshot),
            scope_ref=cls.scope,
            items=[
                {
                    "item_id": "requirement-1",
                    "artifact_ref": record("requirement-1-artifact"),
                    "role": "requirement",
                    "state": "open",
                    "authority_ref": None,
                    "obligation_refs": ["OBL-1"],
                }
            ],
        )

    def make_occurrence(
        self,
        stage="action",
        state_axes=None,
        authority=True,
        input_manifest=None,
        output_manifest=None,
        occurrence_id=None,
    ):
        return build_stage_occurrence(
            stage_occurrence_id=occurrence_id or f"occurrence-{stage}",
            stage_id=stage,
            profile=make_profile(stage, adopted=False),
            configuration_snapshot_ref=record("configuration"),
            subject_entity=self.subject,
            subject_snapshot=self.snapshot,
            applicability_ref=record(f"applicability-{stage}"),
            observed_at=LATER,
            actor_ref=identity("agent"),
            role="ai_agent",
            authority_ref=record("execution-authority") if authority else None,
            input_manifest=input_manifest or self.manifest,
            output_manifest=output_manifest or self.manifest,
            started_at=NOW if stage in {"action", "verification"} else None,
            finished_at=LATER if stage in {"action", "verification"} else None,
            state_axes=state_axes or axes(),
            trusted_decision_verifier=trusted_decision_verifier,
        )

    def test_entity_identity_is_not_label_or_content_equality(self):
        other = build_subject_entity(
            entity_id="subject-B",
            entity_kind="software-system",
            label="same-label",
            created_at=NOW,
        )
        self.assertNotEqual(
            entity_ref(self.subject)["entity_id"], entity_ref(other)["entity_id"]
        )
        tampered = copy.deepcopy(self.subject)
        tampered["derived_from_ref"] = entity_ref(self.subject)
        tampered["entity_digest"] = _digest(
            {k: v for k, v in tampered.items() if k != "entity_digest"}
        )
        with self.assertRaises(LifecycleOccurrenceError):
            validate_subject_entity(tampered)

    def test_snapshot_predecessor_must_preserve_entity_identity(self):
        with self.assertRaises(LifecycleOccurrenceError):
            build_subject_snapshot(
                snapshot_id="snapshot-A2",
                subject_entity_id="subject-A",
                snapshot_version="2",
                content_digest=digest("next"),
                captured_at=LATER,
                previous_snapshot_ref={
                    "snapshot_id": "snapshot-B1",
                    "subject_entity_id": "subject-B",
                    "content_digest": digest("other"),
                    "snapshot_digest": digest("other-snapshot"),
                },
            )

    def test_action_occurrence_needs_observed_time_and_authority(self):
        with self.assertRaises(LifecycleOccurrenceError):
            self.make_occurrence(authority=False)
        observed = self.make_occurrence()
        self.assertNotIn("stage_satisfaction", observed)
        self.assertEqual(observed["formal_authority"], "none")
        self.assertEqual(observed["state_axes_semantics"], "reported_claim")
        self.assertEqual(observed["occurrence_resolution_state"], "unresolved")

    def test_stage_occurrence_rejects_profile_substitution(self):
        with self.assertRaises(LifecycleOccurrenceError):
            build_stage_occurrence(
                stage_occurrence_id="occurrence-action-with-completion-profile",
                stage_id="action",
                profile=make_profile("completion", adopted=False),
                configuration_snapshot_ref=record("configuration"),
                subject_entity=self.subject,
                subject_snapshot=self.snapshot,
                applicability_ref=record("applicability-action"),
                observed_at=LATER,
                actor_ref=identity("agent"),
                role="ai_agent",
                authority_ref=record("execution-authority"),
                input_manifest=self.manifest,
                output_manifest=self.manifest,
                started_at=NOW,
                finished_at=LATER,
                state_axes=axes(),
                trusted_decision_verifier=trusted_decision_verifier,
            )

    def test_non_human_gate_cannot_generate_pending_decision(self):
        with self.assertRaises(LifecycleOccurrenceError):
            self.make_occurrence(
                state_axes=axes(decision_requirement="none", human_decision="pending")
            )

    def test_technical_completion_and_human_pending_are_distinct_axes(self):
        completion = self.make_occurrence(
            stage="completion",
            state_axes=axes(
                decision_requirement="human",
                human_decision="pending",
            ),
        )
        self.assertEqual(completion["state_axes"]["execution_state"], "completed")
        self.assertEqual(completion["state_axes"]["human_decision"], "pending")
        self.assertEqual(completion["formal_authority"], "none")
        self.assertNotIn("stage_satisfaction", completion)

    def test_skipped_or_waived_occurrence_never_satisfies_candidate_predicate(self):
        skipped = self.make_occurrence(state_axes=axes(execution="skipped"))
        self.assertEqual(skipped["state_axes"]["execution_state"], "skipped")
        self.assertEqual(skipped["formal_authority"], "none")
        self.assertNotIn("stage_satisfaction", skipped)

    def test_occurrence_evidence_rejects_actor_self_report_and_requires_verification_method(
        self,
    ):
        occurrence = self.make_occurrence(stage="verification")
        harness_binding = build_role_binding(
            binding_id="harness-binding",
            actor_ref=identity("harness"),
            role_surface="execution_harness",
            granted_capabilities=["observe_occurrence", "collect_raw_evidence"],
            authority_ref=record("harness-authority"),
        )
        actor_binding = build_role_binding(
            binding_id="actor-as-harness-binding",
            actor_ref=identity("agent"),
            role_surface="execution_harness",
            granted_capabilities=["observe_occurrence", "collect_raw_evidence"],
            authority_ref=record("harness-authority"),
        )
        common = {
            "occurrence_evidence_id": "verification-evidence",
            "occurrence_kind": "verification",
            "stage_occurrence": occurrence,
            "actor_ref": identity("agent"),
            "authority_ref": occurrence["authority_ref"],
            "target_snapshot_ref": snapshot_ref(self.snapshot),
            "environment_ref": identity("environment"),
            "tool_refs": [identity("tool")],
            "started_at": NOW,
            "finished_at": LATER,
            "input_refs": [record("verify-input")],
            "raw_result_refs": [record("raw-result")],
            "output_refs": [record("verify-output")],
            "reported_outcome": "succeeded",
        }
        with self.assertRaises(LifecycleOccurrenceError):
            build_occurrence_evidence(
                **common,
                observer_ref=identity("agent"),
                observer_role_binding=actor_binding,
                verification_method_ref=record("method"),
            )
        with self.assertRaises(LifecycleOccurrenceError):
            build_occurrence_evidence(
                **common,
                observer_ref=identity("harness"),
                observer_role_binding=harness_binding,
            )
        valid = build_occurrence_evidence(
            **common,
            observer_ref=identity("harness"),
            observer_role_binding=harness_binding,
            verification_method_ref=record("method"),
        )
        self.assertEqual(valid["formal_authority"], "none")
        self.assertEqual(valid["reported_outcome"], "succeeded")
        self.assertEqual(valid["external_harness_state"], "unresolved")
        self.assertEqual(valid["harness_verifier_claim"], "not_supplied")
        self.assertNotIn("verified_observation_method", valid)
        self.assertNotIn("verified_outcome", valid)
        self.assertNotIn("observation_method", valid)
        self.assertNotIn("observed_outcome", valid)

        verifier_accepted = build_occurrence_evidence(
            **common,
            observer_ref=identity("harness"),
            observer_role_binding=harness_binding,
            verification_method_ref=record("method"),
            trusted_harness_verifier=trusted_harness_verifier,
        )
        self.assertEqual(
            verifier_accepted["external_harness_state"],
            "unresolved",
        )
        self.assertEqual(
            verifier_accepted["harness_verifier_claim"],
            "verifier_claim_accepted",
        )
        self.assertNotIn("verified_observation_method", verifier_accepted)
        self.assertNotIn("verified_outcome", verifier_accepted)
        self.assertEqual(
            verifier_accepted["trust_root_resolution_state"], "not_integrated"
        )
        self.assertEqual(
            verifier_accepted["observer_authority_ref"],
            record("harness-authority"),
        )
        with self.assertRaises(LifecycleOccurrenceError):
            validate_occurrence_evidence(
                verifier_accepted,
                stage_occurrence=occurrence,
                observer_role_binding=harness_binding,
            )

        substituted_raw = {**common, "raw_result_refs": [record("forged-raw-result")]}
        rejected = build_occurrence_evidence(
            **substituted_raw,
            observer_ref=identity("harness"),
            observer_role_binding=harness_binding,
            verification_method_ref=record("method"),
            trusted_harness_verifier=trusted_harness_verifier,
        )
        self.assertEqual(rejected["external_harness_state"], "unresolved")
        self.assertEqual(rejected["harness_verifier_claim"], "verifier_claim_rejected")

        substituted_environment = {**common, "environment_ref": identity("forged")}
        rejected_environment = build_occurrence_evidence(
            **substituted_environment,
            observer_ref=identity("harness"),
            observer_role_binding=harness_binding,
            verification_method_ref=record("method"),
            trusted_harness_verifier=trusted_harness_verifier,
        )
        self.assertEqual(rejected_environment["external_harness_state"], "unresolved")

        unbound = build_occurrence_evidence(
            **common,
            observer_ref=identity("harness"),
            observer_role_binding=harness_binding,
            verification_method_ref=record("method"),
            trusted_harness_verifier=unbound_true_verifier,
        )
        self.assertEqual(unbound["external_harness_state"], "unresolved")
        self.assertIn(
            "trusted_harness_verifier_ref_invalid",
            unbound["external_harness_unresolved_reasons"],
        )

        substituted_authority_binding = build_role_binding(
            binding_id="harness-binding",
            actor_ref=identity("harness"),
            role_surface="execution_harness",
            granted_capabilities=["observe_occurrence", "collect_raw_evidence"],
            authority_ref=record("substituted-harness-authority"),
        )
        rejected_authority = build_occurrence_evidence(
            **common,
            observer_ref=identity("harness"),
            observer_role_binding=substituted_authority_binding,
            verification_method_ref=record("method"),
            trusted_harness_verifier=trusted_harness_verifier,
        )
        self.assertEqual(rejected_authority["external_harness_state"], "unresolved")

    def test_closed_handoff_rejects_unaccounted_addition(self):
        target = build_artifact_manifest(
            manifest_id="manifest-B",
            manifest_version="1",
            subject_entity_ref=entity_ref(self.subject),
            subject_snapshot_ref=snapshot_ref(self.snapshot),
            scope_ref=self.scope,
            items=[
                *self.manifest["items"],
                {
                    "item_id": "invented",
                    "artifact_ref": record("invented-artifact"),
                    "role": "claim",
                    "state": "new",
                    "authority_ref": None,
                    "obligation_refs": [],
                },
            ],
        )
        target_occurrence = self.make_occurrence(
            input_manifest=target,
            output_manifest=target,
            occurrence_id="occurrence-target-handoff",
        )
        with self.assertRaises(LifecycleOccurrenceError):
            build_handoff(
                handoff_id="handoff-unaccounted",
                source_manifest=self.manifest,
                target_manifest=target,
                target_stage_occurrence=target_occurrence,
                target_stage_output_manifest=target,
                subject_entity=self.subject,
                subject_snapshot=self.snapshot,
            )
        valid = build_handoff(
            handoff_id="handoff-accounted",
            source_manifest=self.manifest,
            target_manifest=target,
            target_stage_occurrence=target_occurrence,
            target_stage_output_manifest=target,
            subject_entity=self.subject,
            subject_snapshot=self.snapshot,
            introduced_items=[
                {
                    "output_item_id": "invented",
                    "origin_ref": record("origin"),
                    "reason": "new observation",
                    "basis_refs": [record("introduction-basis")],
                    "actor_ref": identity("agent"),
                    "authority_ref": record("introduction-authority"),
                }
            ],
        )
        self.assertEqual(valid["formal_authority"], "none")

    def test_closed_stage_occurrence_rejects_manifest_and_subject_substitution(self):
        occurrence = self.make_occurrence()
        substituted_manifest = build_artifact_manifest(
            manifest_id="manifest-substituted",
            manifest_version="1",
            subject_entity_ref=entity_ref(self.subject),
            subject_snapshot_ref=snapshot_ref(self.snapshot),
            scope_ref=self.scope,
            items=self.manifest["items"],
        )
        with self.assertRaisesRegex(
            LifecycleOccurrenceError, "input manifest reference is not exact"
        ):
            validate_stage_occurrence_closed(
                occurrence,
                subject_entity=self.subject,
                subject_snapshot=self.snapshot,
                input_manifest=substituted_manifest,
                output_manifest=self.manifest,
            )
        with self.assertRaisesRegex(
            LifecycleOccurrenceError, "output manifest reference is not exact"
        ):
            validate_stage_occurrence_closed(
                occurrence,
                subject_entity=self.subject,
                subject_snapshot=self.snapshot,
                input_manifest=self.manifest,
                output_manifest=substituted_manifest,
            )

        other_subject = build_subject_entity(
            entity_id="subject-B",
            entity_kind="software-system",
            label=self.subject["label"],
            created_at=NOW,
        )
        other_snapshot = build_subject_snapshot(
            snapshot_id="snapshot-B1",
            subject_entity_id="subject-B",
            snapshot_version="1",
            content_digest=self.snapshot["content_digest"],
            captured_at=NOW,
        )
        other_manifest = build_artifact_manifest(
            manifest_id="manifest-subject-B",
            manifest_version="1",
            subject_entity_ref=entity_ref(other_subject),
            subject_snapshot_ref=snapshot_ref(other_snapshot),
            scope_ref=self.scope,
            items=self.manifest["items"],
        )
        validate_artifact_manifest_closed(
            other_manifest,
            subject_entity=other_subject,
            subject_snapshot=other_snapshot,
        )
        with self.assertRaisesRegex(
            LifecycleOccurrenceError, "subject entity reference is not exact"
        ):
            validate_stage_occurrence_closed(
                occurrence,
                subject_entity=other_subject,
                subject_snapshot=other_snapshot,
                input_manifest=other_manifest,
                output_manifest=other_manifest,
            )

    def test_closed_handoff_rejects_occurrence_and_input_manifest_substitution(self):
        occurrence = self.make_occurrence(occurrence_id="occurrence-handoff-target")
        handoff = build_handoff(
            handoff_id="handoff-exact-target",
            source_manifest=self.manifest,
            target_manifest=self.manifest,
            target_stage_occurrence=occurrence,
            target_stage_output_manifest=self.manifest,
            subject_entity=self.subject,
            subject_snapshot=self.snapshot,
        )
        other_occurrence = self.make_occurrence(
            occurrence_id="occurrence-handoff-substituted"
        )
        with self.assertRaisesRegex(
            LifecycleOccurrenceError, "occurrence reference is not exact"
        ):
            validate_handoff_closed(
                handoff,
                source_manifest=self.manifest,
                target_manifest=self.manifest,
                target_stage_occurrence=other_occurrence,
                target_stage_output_manifest=self.manifest,
                subject_entity=self.subject,
                subject_snapshot=self.snapshot,
            )

        substituted_manifest = build_artifact_manifest(
            manifest_id="manifest-handoff-substituted",
            manifest_version="1",
            subject_entity_ref=entity_ref(self.subject),
            subject_snapshot_ref=snapshot_ref(self.snapshot),
            scope_ref=self.scope,
            items=self.manifest["items"],
        )
        with self.assertRaisesRegex(
            LifecycleOccurrenceError, "target manifest reference is not exact"
        ):
            validate_handoff_closed(
                handoff,
                source_manifest=self.manifest,
                target_manifest=substituted_manifest,
                target_stage_occurrence=occurrence,
                target_stage_output_manifest=self.manifest,
                subject_entity=self.subject,
                subject_snapshot=self.snapshot,
            )

    def test_completion_claim_does_not_synthesize_human_acceptance(self):
        claim = build_completion_claim(
            completion_claim_id="completion-1",
            subject_snapshot_ref=snapshot_ref(self.snapshot),
            reported_technical_completion_state="completed",
            obligation_result_refs=[record("obligation-results")],
            verification_evidence_refs=[record("verification-results")],
        )
        self.assertEqual(claim["reported_technical_completion_state"], "completed")
        self.assertEqual(claim["completion_resolution_state"], "unresolved")
        self.assertEqual(claim["completion_verifier_claim"], "not_supplied")
        self.assertNotIn("externally_verified_technical_completion_state", claim)
        self.assertNotIn("technical_completion_state", claim)
        self.assertEqual(claim["human_decision"], "pending")
        self.assertIsNone(claim["human_decision_ref"])

        verifier_accepted = build_completion_claim(
            completion_claim_id="completion-verified",
            subject_snapshot_ref=snapshot_ref(self.snapshot),
            reported_technical_completion_state="completed",
            obligation_result_refs=[record("obligation-results")],
            verification_evidence_refs=[record("verification-results")],
            trusted_completion_verifier=trusted_completion_verifier,
        )
        self.assertEqual(
            verifier_accepted["completion_resolution_state"],
            "unresolved",
        )
        self.assertEqual(
            verifier_accepted["completion_verifier_claim"],
            "verifier_claim_accepted",
        )
        self.assertNotIn(
            "externally_verified_technical_completion_state", verifier_accepted
        )
        with self.assertRaises(LifecycleOccurrenceError):
            validate_completion_claim(verifier_accepted)

        rejected = build_completion_claim(
            completion_claim_id="completion-substituted",
            subject_snapshot_ref=snapshot_ref(self.snapshot),
            reported_technical_completion_state="completed",
            obligation_result_refs=[record("substituted-obligation-results")],
            verification_evidence_refs=[record("verification-results")],
            trusted_completion_verifier=trusted_completion_verifier,
        )
        self.assertEqual(rejected["completion_resolution_state"], "unresolved")
        self.assertEqual(
            rejected["completion_verifier_claim"], "verifier_claim_rejected"
        )
        unbound = build_completion_claim(
            completion_claim_id="completion-unbound-verifier",
            subject_snapshot_ref=snapshot_ref(self.snapshot),
            reported_technical_completion_state="completed",
            obligation_result_refs=[record("obligation-results")],
            verification_evidence_refs=[record("verification-results")],
            trusted_completion_verifier=unbound_true_verifier,
        )
        self.assertEqual(unbound["completion_resolution_state"], "unresolved")
        self.assertIn(
            "trusted_completion_verifier_ref_invalid",
            unbound["completion_unresolved_reasons"],
        )
        with self.assertRaises(LifecycleOccurrenceError):
            build_completion_claim(
                completion_claim_id="completion-fake-accept",
                subject_snapshot_ref=snapshot_ref(self.snapshot),
                reported_technical_completion_state="completed",
                obligation_result_refs=[record("obligation-results")],
                verification_evidence_refs=[record("verification-results")],
                human_decision="accept",
            )


class TestRequalification(unittest.TestCase):
    def test_reopen_relation_can_cross_stage_order_but_needs_authority(self):
        source = {
            "stage_occurrence_id": "action-2",
            "occurrence_digest": digest("action-2"),
        }
        target = {
            "stage_occurrence_id": "requirement-1",
            "occurrence_digest": digest("requirement-1"),
        }
        relation = build_occurrence_relation(
            relation_id="reopen-requirement",
            relation_kind="reopens",
            source_occurrence_ref=source,
            target_occurrence_ref=target,
            basis_refs=[record("reopen-basis")],
            actor_ref=identity("agent"),
            authority_ref=record("reopen-authority"),
            recorded_at=NOW,
        )
        self.assertEqual(relation["relation_kind"], "reopens")
        with self.assertRaises(LifecycleRequalificationError):
            build_occurrence_relation(
                relation_id="unauthorized-reopen",
                relation_kind="reopens",
                source_occurrence_ref=source,
                target_occurrence_ref=target,
                basis_refs=[record("reopen-basis")],
                actor_ref=identity("agent"),
                recorded_at=NOW,
            )

    def test_relation_rejects_self_relation(self):
        same = {"stage_occurrence_id": "same", "occurrence_digest": digest("same")}
        with self.assertRaises(LifecycleRequalificationError):
            build_occurrence_relation(
                relation_id="self-relation",
                relation_kind="derived_from",
                source_occurrence_ref=same,
                target_occurrence_ref=same,
                basis_refs=[record("basis")],
                actor_ref=identity("agent"),
                recorded_at=NOW,
            )

    def test_true_graph_callback_cannot_create_exact_impact_closure(self):
        requirement = record("requirement")
        plan = record("plan")
        realization = record("realization")
        unrelated = record("unrelated")
        closure = build_impact_closure(
            impact_id="impact-exact",
            changed_refs=[requirement],
            known_denominator_refs=[requirement, plan, realization, unrelated],
            dependency_edges=[
                {
                    "source_ref": requirement,
                    "dependent_ref": plan,
                    "dependency_kind": "derived_from",
                    "basis_refs": [record("edge-1")],
                },
                {
                    "source_ref": plan,
                    "dependent_ref": realization,
                    "dependency_kind": "implements",
                    "basis_refs": [record("edge-2")],
                },
            ],
            reported_graph_completeness="complete",
            graph_manifest_ref=record("dependency-graph-manifest"),
            trusted_graph_verifier=trusted_graph_verifier,
        )
        self.assertEqual(
            closure["scope_status"],
            "safe_expanded_to_known_denominator",
        )
        self.assertEqual(closure["graph_trust_state"], "unresolved")
        self.assertEqual(closure["graph_verifier_claim"], "verifier_claim_accepted")
        self.assertEqual(
            {item["record_id"] for item in closure["impacted_refs"]},
            {"requirement", "plan", "realization", "unrelated"},
        )
        with self.assertRaises(LifecycleRequalificationError):
            validate_impact_closure(closure)

    def test_unknown_dependency_graph_expands_safely(self):
        first = record("first")
        second = record("second")
        closure = build_impact_closure(
            impact_id="impact-expanded",
            changed_refs=[first],
            known_denominator_refs=[first, second],
            dependency_edges=[],
            reported_graph_completeness="unknown",
        )
        self.assertEqual(closure["scope_status"], "safe_expanded_to_known_denominator")
        self.assertEqual(len(closure["impacted_refs"]), 2)
        self.assertEqual(closure["formal_authority"], "none")

    def test_reported_complete_graph_without_trusted_verifier_expands_safely(self):
        first = record("first")
        second = record("second")
        closure = build_impact_closure(
            impact_id="impact-unverified-complete",
            changed_refs=[first],
            known_denominator_refs=[first, second],
            dependency_edges=[],
            reported_graph_completeness="complete",
            graph_manifest_ref=record("dependency-graph-manifest"),
        )
        self.assertEqual(closure["graph_trust_state"], "unresolved")
        self.assertEqual(closure["scope_status"], "safe_expanded_to_known_denominator")
        self.assertEqual(
            {item["record_id"] for item in closure["impacted_refs"]},
            {"first", "second"},
        )
        self.assertIn(
            "trusted_graph_verifier_missing",
            closure["reasons"],
        )

        unbound = build_impact_closure(
            impact_id="impact-unbound-verifier",
            changed_refs=[first],
            known_denominator_refs=[first, second],
            dependency_edges=[],
            reported_graph_completeness="complete",
            graph_manifest_ref=record("dependency-graph-manifest"),
            trusted_graph_verifier=unbound_true_verifier,
        )
        self.assertEqual(unbound["graph_trust_state"], "unresolved")
        self.assertIn("trusted_graph_verifier_ref_invalid", unbound["reasons"])


if __name__ == "__main__":
    unittest.main()
