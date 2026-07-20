from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import unittest

from semantic_guard.state_assessment import (
    StateAssessmentError,
    build_evidence_observation,
    build_state_assessment,
    build_subject_manifest,
    build_validity_policy,
    validate_evidence_observation,
    validate_state_assessment,
    validate_subject_manifest,
    validate_validity_policy,
)


def digest(label: str) -> dict[str, str]:
    return {
        "algorithm": "sha256",
        "value": hashlib.sha256(label.encode("utf-8")).hexdigest(),
    }


def binding(entity_id: str, version: str, label: str) -> dict:
    return {
        "entity_id": entity_id,
        "entity_version": version,
        "content_digest": digest(label),
    }


def refresh_digest(value: dict, field: str) -> None:
    material = deepcopy(value)
    material.pop(field, None)
    encoded = json.dumps(
        material,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    value[field] = {
        "algorithm": "sha256",
        "value": hashlib.sha256(encoded).hexdigest(),
    }


class StateAssessmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.environment = binding("environment.local", "1", "environment-a")
        self.profile = binding("profile.audit", "1", "profile-a")
        self.tool = binding("tool.parser", "1", "tool-a")
        self.rule = binding("rule.subject-binding", "1", "rule-a")
        self.human_owner = binding("human.owner", "1", "human-owner")
        self.manifest = build_subject_manifest(
            manifest_id="manifest.service-a",
            manifest_version="1",
            root="workspace",
            inclusion_rule="All files named by the accepted audit subject are included.",
            subject_entries=[
                {
                    "entry_id": "subject.service-a",
                    "path": "src/service.py",
                    "role": "primary_subject",
                    "content_digest": digest("service-a"),
                },
                {
                    "entry_id": "subject.service-config",
                    "path": "config/service.json",
                    "role": "configuration",
                    "content_digest": digest("config-a"),
                },
            ],
            environment_bindings=[self.environment],
            profile_bindings=[self.profile],
            exclusions=[
                {"path": "tmp/cache.bin", "reason": "Generated cache is excluded."}
            ],
        )
        self.change_rules = {
            "subject_digest_change": {
                "invalidates": True,
                "freshness_after_change": "unbound",
                "requalification_evidence_kinds": ["test_execution"],
            },
            "environment_digest_change": {
                "invalidates": True,
                "freshness_after_change": "stale",
                "requalification_evidence_kinds": ["test_execution"],
            },
            "tool_digest_change": {
                "invalidates": True,
                "freshness_after_change": "stale",
                "requalification_evidence_kinds": ["test_execution"],
            },
            "profile_digest_change": {
                "invalidates": True,
                "freshness_after_change": "stale",
                "requalification_evidence_kinds": ["independent_review"],
            },
            "rule_digest_change": {
                "invalidates": True,
                "freshness_after_change": "stale",
                "requalification_evidence_kinds": ["independent_review"],
            },
        }
        self.kind_rules = [
            {
                "evidence_kind": "test_execution",
                "max_age_seconds": 3600,
                "accepted_trust_classes": ["tool_reported"],
                "requalification_evidence_kinds": [
                    "test_execution",
                    "independent_review",
                ],
                "claim_ceiling": [
                    {
                        "axis": "implementation",
                        "allowed_values": ["missing", "partial", "implemented"],
                    },
                    {
                        "axis": "verification",
                        "allowed_values": ["not_run", "passed", "failed", "invalid"],
                    },
                ],
            }
        ]
        self.policy = self._policy("adopted")
        self.evidence = self._evidence()

    def _human_decision_actor(self) -> dict:
        return {
            "decision_maker_identity": deepcopy(self.human_owner),
            "decision_maker_kind": "human",
            "external_to_semantic_guard": True,
        }

    def _policy(self, state: str) -> dict:
        decision = None
        if state == "adopted":
            pending = self._policy("pending")
            decision = {
                "decision_id": "decision.validity-policy-adoption",
                "decision_kind": "adopt_evidence_validity_policy",
                "target_id": pending["policy_id"],
                "target_version": pending["policy_version"],
                "target_basis_digest": deepcopy(pending["policy_basis_digest"]),
                "status": "accepted",
                "locator": "decisions/validity-policy.json",
                "content_digest": digest("policy-decision"),
                "decided_by": "human.owner",
                **self._human_decision_actor(),
                "decided_at": "2026-07-16T00:00:00Z",
            }
        return build_validity_policy(
            policy_id="policy.evidence-validity",
            policy_version="1",
            adoption_state=state,
            human_decision_ref=decision,
            evidence_kind_rules=self.kind_rules,
            change_invalidation=self.change_rules,
            untrusted_time_result="stale",
        )

    def _evidence(
        self,
        *,
        evidence_id: str = "evidence.service-test",
        manifest: dict | None = None,
        observed_at: str = "2026-07-16T00:10:00Z",
        expires_at: str = "2026-07-16T01:10:00Z",
        time_trust: str = "trusted",
        claim_effects: list[dict] | None = None,
    ) -> dict:
        effects = claim_effects or [
            {
                "axis": "implementation",
                "effect": "supports_axis_value",
                "value": "implemented",
                "rule_id": self.rule["entity_id"],
            },
            {
                "axis": "verification",
                "effect": "supports_axis_value",
                "value": "passed",
                "rule_id": self.rule["entity_id"],
            },
        ]
        return build_evidence_observation(
            evidence_id=evidence_id,
            evidence_kind="test_execution",
            content_digest=digest("test-log-a"),
            subject_manifest=manifest or self.manifest,
            observed_at=observed_at,
            expires_at=expires_at,
            time_trust=time_trust,
            environment_identity=self.environment,
            tool_identity=self.tool,
            profile_identity=self.profile,
            rule_identities=[self.rule],
            covered_claim_dimensions=[item["axis"] for item in effects],
            claim_effects=effects,
            trust_class="tool_reported",
            limitations=["Local test execution is not field validation."],
        )

    def _assessment(
        self,
        *,
        manifest: dict | None = None,
        policy: dict | None = None,
        evidence: list[dict] | None = None,
        assessed_at: str = "2026-07-16T00:30:00Z",
        time_trust: str = "trusted",
        tool: dict | None = None,
        environment: list[dict] | None = None,
        profile: list[dict] | None = None,
        rules: list[dict] | None = None,
        axis_values: dict | None = None,
        axis_basis: dict | None = None,
        human_acceptance_record: dict | None = None,
        supporting_ids: list[str] | None = None,
        counter_ids: list[str] | None = None,
    ) -> dict:
        used_evidence = [self.evidence] if evidence is None else evidence
        evidence_ids = [item["evidence_id"] for item in used_evidence]
        return build_state_assessment(
            assessment_id="assessment.service-a",
            proposition="The declared service satisfies the bounded audit claim.",
            subject_manifest=manifest or self.manifest,
            validity_policy=policy or self.policy,
            assessed_at=assessed_at,
            time_trust=time_trust,
            evidence_observations=used_evidence,
            current_environment_bindings=environment or [self.environment],
            current_tool_identity=tool or self.tool,
            current_profile_bindings=profile or [self.profile],
            applied_rules=rules or [self.rule],
            axis_values=axis_values
            or {
                "implementation": "implemented",
                "verification": "passed",
            },
            axis_basis=axis_basis
            or {
                "implementation": {
                    "evidence_ids": evidence_ids,
                    "rule_ids": [self.rule["entity_id"]],
                    "rationale": "The implementation and rule were explicitly checked.",
                },
                "verification": {
                    "evidence_ids": evidence_ids,
                    "rule_ids": [self.rule["entity_id"]],
                    "rationale": "The declared verification procedure passed.",
                },
            },
            supporting_evidence_ids=(
                evidence_ids if supporting_ids is None else supporting_ids
            ),
            counterevidence_ids=([] if counter_ids is None else counter_ids),
            unproven_scope=["Field validation and independent observation remain open."],
            human_acceptance_record=human_acceptance_record,
        )

    def test_closed_manifest_adopted_policy_and_current_evidence_are_current(self) -> None:
        assessment = self._assessment()
        self.assertEqual(assessment["axes"]["freshness"], "current")
        self.assertEqual(assessment["axes"]["human_acceptance"], "pending")
        self.assertFalse(assessment["requalification_plan"]["required"])
        self.assertEqual(assessment["axes"]["validation"], "not_assessed")
        self.assertEqual(assessment["axes"]["assurance"], "not_assessed")
        validate_state_assessment(
            assessment,
            subject_manifest=self.manifest,
            validity_policy=self.policy,
        )

    def test_subject_substitution_becomes_unbound_and_requires_requalification(self) -> None:
        substituted = build_subject_manifest(
            manifest_id="manifest.service-b",
            manifest_version="1",
            root="workspace",
            inclusion_rule="The substituted service is the entire subject.",
            subject_entries=[
                {
                    "entry_id": "subject.service-b",
                    "path": "src/service_b.py",
                    "role": "primary_subject",
                    "content_digest": digest("service-b"),
                }
            ],
            environment_bindings=[self.environment],
            profile_bindings=[self.profile],
        )
        assessment = self._assessment(manifest=substituted)
        self.assertEqual(assessment["axes"]["freshness"], "unbound")
        evaluation = assessment["evidence_evaluations"][0]
        self.assertEqual(evaluation["subject_binding"], "unbound")
        self.assertIn("subject_manifest_mismatch", evaluation["reasons"])
        self.assertTrue(assessment["requalification_plan"]["required"])

    def test_manifest_digest_mutation_is_rejected(self) -> None:
        manifest = deepcopy(self.manifest)
        manifest["manifest_digest"]["value"] = "0" * 64
        with self.assertRaisesRegex(StateAssessmentError, "manifest digest mismatch"):
            validate_subject_manifest(manifest)

    def test_self_evidence_only_manifest_and_path_traversal_are_rejected(self) -> None:
        with self.assertRaises(StateAssessmentError):
            build_subject_manifest(
                manifest_id="manifest.evidence-only",
                manifest_version="1",
                root="workspace",
                inclusion_rule="Only the audit output selected by itself.",
                subject_entries=[
                    {
                        "entry_id": "evidence.self",
                        "path": "reports/audit.json",
                        "role": "evidence",
                        "content_digest": digest("audit"),
                    }
                ],
                environment_bindings=[self.environment],
                profile_bindings=[self.profile],
            )
        with self.assertRaises(StateAssessmentError):
            build_subject_manifest(
                manifest_id="manifest.traversal",
                manifest_version="1",
                root="workspace",
                inclusion_rule="Invalid traversal.",
                subject_entries=[
                    {
                        "entry_id": "subject.escape",
                        "path": "../outside.txt",
                        "role": "primary_subject",
                        "content_digest": digest("outside"),
                    }
                ],
                environment_bindings=[self.environment],
                profile_bindings=[self.profile],
            )

    def test_duplicate_manifest_path_is_rejected(self) -> None:
        entries = deepcopy(self.manifest["subject_entries"])
        entries[1]["path"] = entries[0]["path"]
        with self.assertRaisesRegex(StateAssessmentError, "duplicate path"):
            build_subject_manifest(
                manifest_id="manifest.duplicate",
                manifest_version="1",
                root="workspace",
                inclusion_rule="Duplicate paths are invalid.",
                subject_entries=entries,
                environment_bindings=[self.environment],
                profile_bindings=[self.profile],
            )

    def test_expired_evidence_is_stale_with_concrete_requalification(self) -> None:
        assessment = self._assessment(assessed_at="2026-07-16T01:30:00Z")
        self.assertEqual(assessment["axes"]["freshness"], "stale")
        self.assertEqual(assessment["axes"]["implementation"], "not_assessed")
        self.assertEqual(
            assessment["axis_derivations"]["implementation"]["mode"],
            "asserted_input_unproved",
        )
        self.assertIn(
            "evidence_expired", assessment["requalification_plan"]["reasons"]
        )
        self.assertIn(
            "test_execution",
            assessment["requalification_plan"]["required_evidence_kinds"],
        )

    def test_policy_maximum_age_overrides_later_declared_expiry(self) -> None:
        evidence = self._evidence(expires_at="2026-07-16T10:10:00Z")
        assessment = self._assessment(
            evidence=[evidence], assessed_at="2026-07-16T01:30:00Z"
        )
        self.assertEqual(assessment["axes"]["freshness"], "stale")
        self.assertIn(
            "evidence_age_exceeds_policy",
            assessment["evidence_evaluations"][0]["reasons"],
        )

    def test_pending_policy_never_produces_current_freshness(self) -> None:
        pending = self._policy("pending")
        assessment = self._assessment(policy=pending)
        self.assertEqual(assessment["axes"]["freshness"], "unbound")
        self.assertIn(
            "policy_not_adopted",
            assessment["evidence_evaluations"][0]["reasons"],
        )

    def test_future_policy_adoption_cannot_validate_earlier_assessment(self) -> None:
        future_pending = build_validity_policy(
            policy_id="policy.future-adoption",
            policy_version="1",
            adoption_state="pending",
            human_decision_ref=None,
            evidence_kind_rules=self.kind_rules,
            change_invalidation=self.change_rules,
        )
        future_policy = build_validity_policy(
            policy_id="policy.future-adoption",
            policy_version="1",
            adoption_state="adopted",
            human_decision_ref={
                "decision_id": "decision.future-adoption",
                "decision_kind": "adopt_evidence_validity_policy",
                "target_id": future_pending["policy_id"],
                "target_version": future_pending["policy_version"],
                "target_basis_digest": deepcopy(
                    future_pending["policy_basis_digest"]
                ),
                "status": "accepted",
                "locator": "decisions/future-policy.json",
                "content_digest": digest("future-policy"),
                "decided_by": "human.owner",
                **self._human_decision_actor(),
                "decided_at": "2026-07-16T02:00:00Z",
            },
            evidence_kind_rules=self.kind_rules,
            change_invalidation=self.change_rules,
        )
        assessment = self._assessment(policy=future_policy)
        self.assertEqual(assessment["axes"]["freshness"], "unbound")
        self.assertIn(
            "policy_not_adopted_at_assessment",
            assessment["evidence_evaluations"][0]["reasons"],
        )

    def test_nonadopted_policy_cannot_carry_human_adoption_decision(self) -> None:
        with self.assertRaises(StateAssessmentError):
            build_validity_policy(
                policy_id="policy.invalid-pending",
                policy_version="1",
                adoption_state="pending",
                human_decision_ref={
                    "decision_id": "decision.fake",
                    "status": "accepted",
                    "locator": "decisions/fake.json",
                    "content_digest": digest("fake"),
                    "decided_by": "human.fake",
                    "decided_at": "2026-07-16T00:00:00Z",
                },
                evidence_kind_rules=self.kind_rules,
                change_invalidation=self.change_rules,
            )

    def test_axes_do_not_leak_into_unassessed_axes(self) -> None:
        implementation_only = self._evidence(
            claim_effects=[
                {
                    "axis": "implementation",
                    "effect": "supports_axis_value",
                    "value": "implemented",
                    "rule_id": self.rule["entity_id"],
                }
            ]
        )
        assessment = self._assessment(
            evidence=[implementation_only],
            axis_values={"implementation": "implemented"},
            axis_basis={
                "implementation": {
                    "evidence_ids": [implementation_only["evidence_id"]],
                    "rule_ids": [self.rule["entity_id"]],
                    "rationale": "Only implementation was explicitly assessed.",
                }
            },
        )
        self.assertEqual(assessment["axes"]["verification"], "not_assessed")
        self.assertEqual(assessment["axes"]["validation"], "not_assessed")
        self.assertEqual(assessment["axes"]["assurance"], "not_assessed")

        forged = deepcopy(assessment)
        forged["axes"]["verification"] = "passed"
        refresh_digest(forged, "assessment_digest")
        with self.assertRaisesRegex(
            StateAssessmentError, "acceptance basis|do not replay"
        ):
            validate_state_assessment(
                forged,
                subject_manifest=self.manifest,
                validity_policy=self.policy,
            )

    def test_environment_tool_profile_and_rule_changes_invalidate(self) -> None:
        changes = (
            ("environment", {"environment": [binding("environment.local", "2", "environment-b")]}),
            ("tool", {"tool": binding("tool.parser", "2", "tool-b")}),
            ("profile", {"profile": [binding("profile.audit", "2", "profile-b")]}),
            ("rule", {"rules": [binding("rule.subject-binding", "2", "rule-b")]}),
        )
        expected = {
            "environment": "environment_digest_change",
            "tool": "tool_digest_change",
            "profile": "profile_digest_change",
            "rule": "rule_digest_change",
        }
        for label, arguments in changes:
            with self.subTest(change=label):
                assessment = self._assessment(**arguments)
                self.assertEqual(assessment["axes"]["freshness"], "stale")
                self.assertIn(
                    expected[label],
                    assessment["evidence_evaluations"][0][
                        "invalidating_changes"
                    ],
                )

    def test_new_environment_evidence_cannot_reuse_old_manifest_binding(self) -> None:
        environment_b = binding("environment.local", "2", "environment-b")
        evidence = build_evidence_observation(
            evidence_id="evidence.new-environment",
            evidence_kind="test_execution",
            content_digest=digest("new-environment-log"),
            subject_manifest=self.manifest,
            observed_at="2026-07-16T00:10:00Z",
            expires_at="2026-07-16T01:10:00Z",
            time_trust="trusted",
            environment_identity=environment_b,
            tool_identity=self.tool,
            profile_identity=self.profile,
            rule_identities=[self.rule],
            covered_claim_dimensions=["implementation", "verification"],
            claim_effects=[
                {
                    "axis": "implementation",
                    "effect": "supports_axis_value",
                    "value": "implemented",
                    "rule_id": self.rule["entity_id"],
                },
                {
                    "axis": "verification",
                    "effect": "supports_axis_value",
                    "value": "passed",
                    "rule_id": self.rule["entity_id"],
                },
            ],
            trust_class="tool_reported",
        )
        assessment = self._assessment(
            evidence=[evidence], environment=[environment_b]
        )
        self.assertEqual(assessment["axes"]["freshness"], "stale")
        self.assertIn(
            "environment_digest_change",
            assessment["evidence_evaluations"][0]["invalidating_changes"],
        )

    def test_untrusted_time_is_stale_and_does_not_claim_authenticity(self) -> None:
        evidence = self._evidence(time_trust="untrusted")
        assessment = self._assessment(evidence=[evidence])
        self.assertEqual(assessment["axes"]["freshness"], "stale")
        self.assertIn("untrusted_time", assessment["requalification_plan"]["reasons"])
        self.assertTrue(
            any("trusted-time authenticity" in item for item in assessment["limitations"])
        )

    def test_fake_human_acceptance_without_external_record_is_rejected(self) -> None:
        assessment = self._assessment()
        forged = deepcopy(assessment)
        forged["axes"]["human_acceptance"] = "accept"
        refresh_digest(forged, "assessment_digest")
        with self.assertRaisesRegex(StateAssessmentError, "must remain pending"):
            validate_state_assessment(
                forged,
                subject_manifest=self.manifest,
                validity_policy=self.policy,
            )

    def test_explicit_external_human_record_can_be_projected_but_not_created(self) -> None:
        pending = self._assessment()
        record = {
            "decision_id": "decision.accept-assessment",
            "decision_kind": "accept_state_assessment",
            "status": "accept",
            "assessment_id": "assessment.service-a",
            "subject_manifest_ref": {
                "manifest_id": self.manifest["manifest_id"],
                "manifest_version": self.manifest["manifest_version"],
                "manifest_digest": deepcopy(self.manifest["manifest_digest"]),
            },
            "target_basis_digest": deepcopy(pending["acceptance_basis_digest"]),
            "decided_by": "human.owner",
            **self._human_decision_actor(),
            "decided_at": "2026-07-16T00:40:00Z",
            "record_ref": {
                "record_id": "record.accept-assessment",
                "locator": "decisions/accept-assessment.json",
                "content_digest": digest("accept-assessment"),
            },
        }
        assessment = self._assessment(human_acceptance_record=record)
        self.assertEqual(assessment["axes"]["human_acceptance"], "accept")
        self.assertEqual(
            assessment["axis_derivations"]["human_acceptance"]["mode"],
            "external_human_record",
        )

    def test_human_record_cannot_predate_assessment(self) -> None:
        pending = self._assessment()
        record = {
            "decision_id": "decision.before-assessment",
            "decision_kind": "accept_state_assessment",
            "status": "accept",
            "assessment_id": "assessment.service-a",
            "subject_manifest_ref": {
                "manifest_id": self.manifest["manifest_id"],
                "manifest_version": self.manifest["manifest_version"],
                "manifest_digest": deepcopy(self.manifest["manifest_digest"]),
            },
            "target_basis_digest": deepcopy(pending["acceptance_basis_digest"]),
            "decided_by": "human.owner",
            **self._human_decision_actor(),
            "decided_at": "2026-07-16T00:20:00Z",
            "record_ref": {
                "record_id": "record.before-assessment",
                "locator": "decisions/before-assessment.json",
                "content_digest": digest("before-assessment"),
            },
        }
        with self.assertRaisesRegex(StateAssessmentError, "predates"):
            self._assessment(human_acceptance_record=record)

    def test_duplicate_evidence_is_rejected(self) -> None:
        with self.assertRaisesRegex(StateAssessmentError, "duplicate evidence_id"):
            self._assessment(evidence=[self.evidence, deepcopy(self.evidence)])

    def test_missing_requalification_plan_is_rejected(self) -> None:
        assessment = self._assessment(assessed_at="2026-07-16T01:30:00Z")
        assessment.pop("requalification_plan")
        refresh_digest(assessment, "assessment_digest")
        with self.assertRaisesRegex(StateAssessmentError, "schema violation"):
            validate_state_assessment(
                assessment,
                subject_manifest=self.manifest,
                validity_policy=self.policy,
            )

    def test_observation_and_policy_digest_mutations_are_rejected(self) -> None:
        evidence = deepcopy(self.evidence)
        evidence["observation_digest"]["value"] = "0" * 64
        with self.assertRaisesRegex(StateAssessmentError, "observation digest mismatch"):
            validate_evidence_observation(evidence)

        policy = deepcopy(self.policy)
        policy["policy_digest"]["value"] = "0" * 64
        with self.assertRaisesRegex(StateAssessmentError, "policy digest mismatch"):
            validate_validity_policy(policy)

    def test_validity_policy_decision_cannot_be_reused_after_policy_change(self) -> None:
        changed_rules = deepcopy(self.kind_rules)
        changed_rules[0]["max_age_seconds"] = 7200
        with self.assertRaisesRegex(StateAssessmentError, "target_basis_digest"):
            build_validity_policy(
                policy_id=self.policy["policy_id"],
                policy_version=self.policy["policy_version"],
                adoption_state="adopted",
                human_decision_ref=self.policy["human_decision_ref"],
                evidence_kind_rules=changed_rules,
                change_invalidation=self.change_rules,
            )

    def test_test_execution_cannot_claim_validation_above_policy_ceiling(self) -> None:
        evidence = self._evidence(
            claim_effects=[
                {
                    "axis": "validation",
                    "effect": "supports_axis_value",
                    "value": "supported_in_context",
                    "rule_id": self.rule["entity_id"],
                }
            ]
        )
        with self.assertRaisesRegex(StateAssessmentError, "claim ceiling"):
            self._assessment(
                evidence=[evidence],
                axis_values={"validation": "supported_in_context"},
                axis_basis={
                    "validation": {
                        "evidence_ids": [evidence["evidence_id"]],
                        "rule_ids": [self.rule["entity_id"]],
                        "rationale": "A test result was incorrectly offered as validation.",
                    }
                },
            )

    def test_counterevidence_cannot_be_reused_as_positive_axis_basis(self) -> None:
        with self.assertRaisesRegex(StateAssessmentError, "counterevidence"):
            self._assessment(
                supporting_ids=[],
                counter_ids=[self.evidence["evidence_id"]],
                axis_values={"implementation": "implemented"},
                axis_basis={
                    "implementation": {
                        "evidence_ids": [self.evidence["evidence_id"]],
                        "rule_ids": [self.rule["entity_id"]],
                        "rationale": "Counterevidence cannot become positive support.",
                    }
                },
            )

    def test_conflicting_typed_effects_are_rejected(self) -> None:
        conflicting = self._evidence(
            evidence_id="evidence.service-test-conflict",
            claim_effects=[
                {
                    "axis": "implementation",
                    "effect": "supports_axis_value",
                    "value": "partial",
                    "rule_id": self.rule["entity_id"],
                }
            ],
        )
        with self.assertRaisesRegex(StateAssessmentError, "conflicting typed"):
            self._assessment(evidence=[self.evidence, conflicting])

    def test_generic_rule_assertion_is_recorded_but_remains_unproved(self) -> None:
        assessment = self._assessment(
            evidence=[],
            axis_values={"validation": "supported_in_context"},
            axis_basis={
                "validation": {
                    "evidence_ids": [],
                    "rule_ids": [self.rule["entity_id"]],
                    "rationale": "This is an interpretation assertion, not typed evidence.",
                }
            },
            supporting_ids=[],
            counter_ids=[],
        )
        self.assertEqual(assessment["axes"]["validation"], "not_assessed")
        derivation = assessment["axis_derivations"]["validation"]
        self.assertEqual(derivation["mode"], "asserted_input_unproved")
        self.assertEqual(derivation["asserted_value"], "supported_in_context")

    def test_human_acceptance_decision_cannot_be_reused_for_changed_basis(self) -> None:
        pending = self._assessment()
        record = {
            "decision_id": "decision.accept-once",
            "decision_kind": "accept_state_assessment",
            "status": "accept",
            "assessment_id": pending["assessment_id"],
            "subject_manifest_ref": deepcopy(pending["subject_manifest_ref"]),
            "target_basis_digest": deepcopy(pending["acceptance_basis_digest"]),
            "decided_by": "human.owner",
            **self._human_decision_actor(),
            "decided_at": "2026-07-16T00:40:00Z",
            "record_ref": {
                "record_id": "record.accept-once",
                "locator": "decisions/accept-once.json",
                "content_digest": digest("accept-once"),
            },
        }
        accepted = self._assessment(human_acceptance_record=record)
        self.assertEqual(accepted["axes"]["human_acceptance"], "accept")
        with self.assertRaisesRegex(StateAssessmentError, "target_basis_digest"):
            self._assessment(
                assessed_at="2026-07-16T00:31:00Z",
                human_acceptance_record=record,
            )

    def test_agent_identity_cannot_adopt_validity_policy(self) -> None:
        pending = self._policy("pending")
        decision = deepcopy(self.policy["human_decision_ref"])
        decision["decided_by"] = "agent.worker"
        decision["decision_maker_identity"] = binding(
            "agent.worker", "1", "agent-worker"
        )
        decision["decision_maker_kind"] = "coding_agent"
        with self.assertRaisesRegex(StateAssessmentError, "schema violation"):
            build_validity_policy(
                policy_id=pending["policy_id"],
                policy_version=pending["policy_version"],
                adoption_state="adopted",
                human_decision_ref=decision,
                evidence_kind_rules=self.kind_rules,
                change_invalidation=self.change_rules,
            )

        mismatched = deepcopy(self.policy["human_decision_ref"])
        mismatched["decided_by"] = "agent.worker"
        with self.assertRaisesRegex(StateAssessmentError, "identity does not match"):
            build_validity_policy(
                policy_id=pending["policy_id"],
                policy_version=pending["policy_version"],
                adoption_state="adopted",
                human_decision_ref=mismatched,
                evidence_kind_rules=self.kind_rules,
                change_invalidation=self.change_rules,
            )

    def test_agent_identity_cannot_accept_state_assessment(self) -> None:
        pending = self._assessment()
        record = {
            "decision_id": "decision.agent-accept",
            "decision_kind": "accept_state_assessment",
            "status": "accept",
            "assessment_id": pending["assessment_id"],
            "subject_manifest_ref": deepcopy(pending["subject_manifest_ref"]),
            "target_basis_digest": deepcopy(pending["acceptance_basis_digest"]),
            "decided_by": "agent.worker",
            "decision_maker_identity": binding(
                "agent.worker", "1", "agent-worker"
            ),
            "decision_maker_kind": "coding_agent",
            "external_to_semantic_guard": True,
            "decided_at": "2026-07-16T00:40:00Z",
            "record_ref": {
                "record_id": "record.agent-accept",
                "locator": "decisions/agent-accept.json",
                "content_digest": digest("agent-accept"),
            },
        }
        with self.assertRaisesRegex(StateAssessmentError, "schema violation"):
            self._assessment(human_acceptance_record=record)

    def test_legacy_state_assessment_is_not_implicitly_accepted(self) -> None:
        assessment = self._assessment()
        for version in ("state-assessment/v0", "state-assessment/v1"):
            with self.subTest(version=version):
                broken = deepcopy(assessment)
                broken["schema_version"] = version
                with self.assertRaisesRegex(StateAssessmentError, "schema violation"):
                    validate_state_assessment(
                        broken,
                        subject_manifest=self.manifest,
                        validity_policy=self.policy,
                    )

    def test_legacy_validity_policy_is_not_implicitly_accepted(self) -> None:
        for version in (
            "evidence-validity-policy/v0",
            "evidence-validity-policy/v1",
        ):
            with self.subTest(version=version):
                policy = deepcopy(self.policy)
                policy["schema_version"] = version
                with self.assertRaisesRegex(StateAssessmentError, "schema violation"):
                    validate_validity_policy(policy)


if __name__ == "__main__":
    unittest.main()
