from __future__ import annotations

from copy import deepcopy
import hashlib
import unittest

from semantic_guard.action_evidence import (
    ActionEvidenceError,
    build_action_assurance_profile,
    build_action_event,
    build_action_evidence_assessment,
    build_action_observation,
    build_authority_grant,
    build_causal_observation,
    build_signature_attestation,
    validate_action_assurance_profile,
    validate_action_event,
    validate_action_evidence_assessment,
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


def locator(record_id: str, label: str) -> dict:
    return {
        "record_id": record_id,
        "locator": f"evidence/{record_id}.json",
        "content_digest": digest(label),
    }


def artifact(artifact_id: str, role: str, label: str) -> dict:
    return {
        "artifact_id": artifact_id,
        "role": role,
        "locator": f"artifacts/{artifact_id}",
        "content_digest": digest(label),
    }


class ActionEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.actor = binding("agent.worker", "1", "actor")
        self.other_actor = binding("agent.other", "1", "other-actor")
        self.observer = binding("observer.independent", "1", "observer")
        self.verifier = binding("verifier.signature", "1", "verifier")
        self.grantor = binding("human.owner", "1", "grantor")
        self.environment = binding("environment.local", "1", "environment")
        self.target = binding("target.repository", "1", "target")
        self.clock = binding("clock.rfc3161", "1", "clock")
        self.trust_root = {
            "root_id": "trust-root.operations",
            "root_version": "1",
            "locator": "trust/operations.pem",
            "content_digest": digest("trust-root"),
        }
        self.trusted_time = {
            "time_trust": "trusted",
            "clock_identity": self.clock,
            "trust_root_ref": self.trust_root,
        }
        self.untrusted_time = {
            "time_trust": "untrusted",
            "clock_identity": None,
            "trust_root_ref": None,
        }
        self.action_spec = {
            "action_type": "action.patch",
            "target_ref": self.target,
            "intent_digest": digest("accepted-intent"),
            "parameters_digest": digest("patch-parameters"),
        }
        self.input_artifact = artifact("artifact.source.before", "input", "before")
        self.output_artifact = artifact(
            "artifact.source.after", "patched_source", "after"
        )
        self.stages = [
            {
                "stage_id": "stage.prepare",
                "status": "completed",
                "observed_at": "2026-07-16T00:01:00Z",
                "evidence_digest": digest("stage-prepare"),
            },
            {
                "stage_id": "stage.execute",
                "status": "completed",
                "observed_at": "2026-07-16T00:02:00Z",
                "evidence_digest": digest("stage-execute"),
            },
            {
                "stage_id": "stage.verify",
                "status": "completed",
                "observed_at": "2026-07-16T00:03:00Z",
                "evidence_digest": digest("stage-verify"),
            },
        ]
        self.stops = [
            {
                "condition_id": "condition.abort_on_test_failure",
                "triggered": False,
                "response": "continued",
                "evidence_digest": digest("stop-condition"),
            }
        ]
        self.profile = self._profile("adopted")
        self.event = self._event()
        self.observation = self._observation(self.event)
        self.event_signature = self._signature(
            self.event["event_digest"], self.actor, "event-signature"
        )
        self.grant = self._grant()
        self.causal = self._causal(self.event, self.observation)

    def _profile(self, state: str, *, reverse: bool = False) -> dict:
        decision = None
        if state == "adopted":
            pending = self._profile("pending", reverse=reverse)
            decision = {
                "decision_id": "decision.action-profile-adoption",
                "decision_kind": "adopt_action_assurance_profile",
                "target_id": pending["profile_id"],
                "target_version": pending["profile_version"],
                "target_basis_digest": deepcopy(pending["profile_basis_digest"]),
                "status": "accepted",
                "locator": "decisions/action-profile.json",
                "content_digest": digest("profile-adoption"),
                "decided_by": "human.owner",
                "decision_maker_identity": self.grantor,
                "decision_maker_kind": "human",
                "external_to_semantic_guard": True,
                "decided_at": "2026-07-15T00:00:00Z",
            }
        claims = [
            "occurrence",
            "identity",
            "authority",
            "procedure",
            "artifact_provenance",
            "authenticity",
            "causality",
        ]
        occurrence_kinds = [
            "observer_attestation",
            "trusted_execution_log",
            "signed_event",
        ]
        accepted_trust = [
            "independently_observed",
            "signed",
            "tool_reported",
        ]
        independence = [
            "occurrence",
            "identity",
            "procedure",
            "artifact_provenance",
            "causality",
        ]
        if reverse:
            claims.reverse()
            occurrence_kinds.reverse()
            accepted_trust.reverse()
            independence.reverse()
        return build_action_assurance_profile(
            profile_id="profile.action-evidence",
            profile_version="1.0.0",
            adoption_state=state,
            human_decision_ref=decision,
            required_claim_classes=claims,
            occurrence_capable_evidence_kinds=occurrence_kinds,
            observer_policy={
                "accepted_trust_classes": accepted_trust,
                "allowed_observers": [self.observer],
                "independence_required_for": independence,
                "self_observation_max_trust": "self_reported",
            },
            time_policy={
                "trusted_time_required_for": claims,
                "max_event_age_seconds": 3600,
                "untrusted_time_result": "unproved",
                "allowed_clock_identities": [self.clock],
                "allowed_trust_roots": [self.trust_root],
            },
            authority_policy={
                "explicit_grant_required": True,
                "grant_record_digest_required": True,
                "signed_grant_required": True,
                "allowed_grantors": [self.grantor],
            },
            procedure_policy={
                "required_stages": [
                    {
                        "stage_id": "stage.prepare",
                        "order": 0,
                        "description": "Prepare the bounded action.",
                    },
                    {
                        "stage_id": "stage.execute",
                        "order": 1,
                        "description": "Execute the bounded action.",
                    },
                    {
                        "stage_id": "stage.verify",
                        "order": 2,
                        "description": "Verify the bounded result.",
                    },
                ],
                "stop_conditions": [
                    {
                        "condition_id": "condition.abort_on_test_failure",
                        "description": "Stop when verification fails.",
                        "required_response": "stop",
                    }
                ],
            },
            artifact_policy={
                "required_input_roles": ["input"],
                "required_output_roles": ["patched_source"],
                "allowed_digest_algorithms": ["sha256"],
            },
            authenticity_policy={
                "signature_required": True,
                "verified_signature_required": True,
                "external_trust_root_required": True,
                "external_clock_required": True,
                "allowed_signers": [self.actor],
                "allowed_verifiers": [self.verifier],
                "allowed_signature_algorithms": ["ed25519"],
            },
            causality_policy={
                "explicit_observation_required": True,
                "accepted_methods": ["trace_link"],
                "independent_observer_required": True,
            },
            threat_assumptions=[
                "Supplied records may be replayed, substituted, or self-asserted."
            ],
            limitations=[
                "External cryptographic and clock mechanisms remain external."
            ],
        )

    def _event(
        self,
        *,
        action_spec: dict | None = None,
        time_attestation: dict | None = None,
        output_artifacts: list[dict] | None = None,
        stages: list[dict] | None = None,
        stops: list[dict] | None = None,
    ) -> dict:
        return build_action_event(
            action_spec=action_spec or self.action_spec,
            actor_identity=self.actor,
            environment_identity=self.environment,
            occurred_at="2026-07-16T00:00:00Z",
            time_attestation=time_attestation or self.trusted_time,
            execution_status="succeeded",
            input_artifacts=[self.input_artifact],
            output_artifacts=(
                [self.output_artifact]
                if output_artifacts is None
                else output_artifacts
            ),
            procedure_stages=self.stages if stages is None else stages,
            stop_conditions=self.stops if stops is None else stops,
        )

    def _observation(self, event: dict, **overrides: object) -> dict:
        values: dict[str, object] = {
            "event": event,
            "evidence_kind": "trusted_execution_log",
            "observer_identity": self.observer,
            "relationship_to_actor": "independent",
            "trust_class": "independently_observed",
            "observed_at": "2026-07-16T00:05:00Z",
            "time_attestation": self.trusted_time,
            "observed_stage_ids": [
                "stage.prepare",
                "stage.execute",
                "stage.verify",
            ],
            "observed_stop_condition_ids": [
                "condition.abort_on_test_failure"
            ],
            "evidence_record_ref": locator(
                "observation.execution-log", "execution-log-record"
            ),
            "limitations": ["Observer trust is bounded by the selected profile."],
        }
        values.update(overrides)
        return build_action_observation(**values)  # type: ignore[arg-type]

    def _signature(
        self,
        signed_digest: dict,
        signer: dict,
        label: str,
        *,
        verified_at: str = "2026-07-16T00:06:00Z",
        time_attestation: dict | None = None,
        verification_status: str = "verified",
    ) -> dict:
        return build_signature_attestation(
            algorithm="ed25519",
            signer_identity=signer,
            signed_content_digest=signed_digest,
            signature_value_digest=digest(f"{label}-value"),
            trust_root_ref=self.trust_root,
            verification_status=verification_status,
            verifier_identity=self.verifier,
            verified_at=verified_at,
            time_attestation=time_attestation or self.trusted_time,
            verification_record_ref=locator(
                f"verification.{label}", f"{label}-record"
            ),
        )

    def _grant(
        self,
        *,
        grantee: dict | None = None,
        expires_at: str = "2026-07-17T00:00:00Z",
        grantor: dict | None = None,
        signer: dict | None = None,
        signed: bool = True,
    ) -> dict:
        grantee = grantee or self.actor
        grantor = grantor or self.grantor
        unsigned = build_authority_grant(
            grantor_identity=grantor,
            grantee_identity=grantee,
            action_types=["action.patch"],
            target_ids=[self.target["entity_id"]],
            environment_ids=[self.environment["entity_id"]],
            issued_at="2026-07-15T00:00:00Z",
            expires_at=expires_at,
            time_attestation=self.trusted_time,
            status="active",
            grant_record_ref=locator("grant.patch", "grant-record"),
        )
        if not signed:
            return unsigned
        signature = self._signature(
            unsigned["grant_material_digest"],
            signer or grantor,
            "grant-signature",
            verified_at="2026-07-15T00:01:00Z",
        )
        return build_authority_grant(
            grantor_identity=grantor,
            grantee_identity=grantee,
            action_types=["action.patch"],
            target_ids=[self.target["entity_id"]],
            environment_ids=[self.environment["entity_id"]],
            issued_at="2026-07-15T00:00:00Z",
            expires_at=expires_at,
            time_attestation=self.trusted_time,
            status="active",
            grant_record_ref=locator("grant.patch", "grant-record"),
            grant_signature=signature,
        )

    def _causal(self, event: dict, observation: dict) -> dict:
        return build_causal_observation(
            event=event,
            effect_artifact_ref=event["output_artifacts"][0],
            observer_observation_id=observation["observation_id"],
            method="trace_link",
            outcome="supports",
            observed_at="2026-07-16T00:07:00Z",
            time_attestation=self.trusted_time,
            evidence_digest=digest("causal-trace"),
        )

    def _assessment(
        self,
        *,
        profile: dict | None = None,
        expected_action_spec: dict | None = None,
        event: dict | None = None,
        observations: list[dict] | None = None,
        grants: list[dict] | None = None,
        signatures: list[dict] | None = None,
        causal: list[dict] | None = None,
        evaluated_at: str = "2026-07-16T00:10:00Z",
    ) -> dict:
        return build_action_evidence_assessment(
            profile=profile or self.profile,
            expected_action_spec=expected_action_spec or self.action_spec,
            event=event or self.event,
            observations=(
                [self.observation] if observations is None else observations
            ),
            authority_grants=[self.grant] if grants is None else grants,
            signature_attestations=(
                [self.event_signature] if signatures is None else signatures
            ),
            causal_observations=[self.causal] if causal is None else causal,
            evaluated_at=evaluated_at,
        )

    @staticmethod
    def _claims(assessment: dict) -> dict[str, dict]:
        return {item["claim_class"]: item for item in assessment["claim_results"]}

    def test_complete_bundle_proves_each_independent_claim(self) -> None:
        assessment = self._assessment()
        claims = self._claims(assessment)
        self.assertEqual(set(claims), {
            "occurrence",
            "identity",
            "authority",
            "procedure",
            "artifact_provenance",
            "authenticity",
            "causality",
        })
        self.assertTrue(all(item["state"] == "proved" for item in claims.values()))
        self.assertTrue(assessment["summary"]["all_required_claims_proved"])
        self.assertEqual(assessment["summary"]["human_acceptance"], "pending")
        self.assertEqual(
            assessment["summary"]["semantic_guard_role"],
            "audit_only_no_dispatch_or_authority_grant",
        )

    def test_prose_tool_request_and_self_report_never_prove_occurrence(self) -> None:
        cases = [
            ("prose_description", self.observer, "independent", "tool_reported"),
            ("tool_request", self.observer, "independent", "tool_reported"),
            ("self_report", self.actor, "self", "self_reported"),
        ]
        for kind, observer, relationship, trust in cases:
            with self.subTest(kind=kind):
                observation = self._observation(
                    self.event,
                    evidence_kind=kind,
                    observer_identity=observer,
                    relationship_to_actor=relationship,
                    trust_class=trust,
                )
                assessment = self._assessment(
                    observations=[observation], grants=[], signatures=[], causal=[]
                )
                self.assertEqual(
                    self._claims(assessment)["occurrence"]["state"], "unproved"
                )

    def test_execution_success_never_implies_authority(self) -> None:
        assessment = self._assessment(grants=[])
        authority = self._claims(assessment)["authority"]
        self.assertEqual(authority["state"], "unproved")
        self.assertIn("explicit_authority_grant_missing", authority["reasons"])

    def test_independence_is_enforced_only_when_profile_requires_it(self) -> None:
        same_operator = self._observation(
            self.event,
            relationship_to_actor="same_operator",
            trust_class="tool_reported",
        )
        strict = self._assessment(
            observations=[same_operator], grants=[], signatures=[], causal=[]
        )
        self.assertEqual(self._claims(strict)["occurrence"]["state"], "unproved")

        profile = self._profile("adopted")
        profile_input = {
            **profile["observer_policy"],
            "independence_required_for": [],
        }
        def build_relaxed(state: str, decision: dict | None = None) -> dict:
            return build_action_assurance_profile(
                profile_id="profile.action-evidence.relaxed",
                profile_version="1.0.0",
                adoption_state=state,
                human_decision_ref=decision,
                required_claim_classes=profile["required_claim_classes"],
                occurrence_capable_evidence_kinds=profile[
                    "occurrence_capable_evidence_kinds"
                ],
                observer_policy=profile_input,
                time_policy=profile["time_policy"],
                authority_policy=profile["authority_policy"],
                procedure_policy=profile["procedure_policy"],
                artifact_policy=profile["artifact_policy"],
                authenticity_policy=profile["authenticity_policy"],
                causality_policy={
                    **profile["causality_policy"],
                    "independent_observer_required": False,
                },
                threat_assumptions=profile["threat_assumptions"],
                limitations=profile["limitations"],
            )

        relaxed_pending = build_relaxed("pending")
        relaxed_decision = {
            **profile["human_decision_ref"],
            "target_id": relaxed_pending["profile_id"],
            "target_version": relaxed_pending["profile_version"],
            "target_basis_digest": deepcopy(
                relaxed_pending["profile_basis_digest"]
            ),
        }
        relaxed = build_relaxed("adopted", relaxed_decision)
        relaxed_assessment = self._assessment(
            profile=relaxed,
            observations=[same_operator],
            grants=[],
            signatures=[],
            causal=[],
        )
        self.assertEqual(
            self._claims(relaxed_assessment)["occurrence"]["state"], "proved"
        )

    def test_self_observation_cannot_inflate_trust(self) -> None:
        with self.assertRaisesRegex(ActionEvidenceError, "self observation"):
            self._observation(
                self.event,
                evidence_kind="observer_attestation",
                observer_identity=self.actor,
                relationship_to_actor="self",
                trust_class="independently_observed",
            )

    def test_event_digest_tamper_is_rejected(self) -> None:
        tampered = deepcopy(self.event)
        tampered["output_artifacts"][0]["content_digest"] = digest("tampered")
        with self.assertRaises(ActionEvidenceError):
            validate_action_event(tampered)

    def test_event_substitution_refutes_occurrence(self) -> None:
        other_spec = {**self.action_spec, "parameters_digest": digest("other")}
        other_event = self._event(action_spec=other_spec)
        assessment = self._assessment(
            expected_action_spec=other_spec,
            event=other_event,
            observations=[self.observation],
            grants=[],
            signatures=[],
            causal=[],
        )
        occurrence = self._claims(assessment)["occurrence"]
        self.assertEqual(occurrence["state"], "refuted")
        self.assertIn("observation_event_substitution", occurrence["reasons"])

    def test_pending_and_retired_profiles_gate_positive_results(self) -> None:
        for state in ("pending", "retired"):
            with self.subTest(state=state):
                assessment = self._assessment(profile=self._profile(state))
                claims = self._claims(assessment)
                self.assertTrue(all(item["state"] == "unproved" for item in claims.values()))
                self.assertFalse(assessment["summary"]["all_required_claims_proved"])

    def test_adopted_profile_requires_external_human_decision(self) -> None:
        with self.assertRaises(ActionEvidenceError):
            build_action_assurance_profile(
                profile_id="profile.invalid",
                profile_version="1",
                adoption_state="adopted",
                human_decision_ref=None,
                required_claim_classes=self.profile["required_claim_classes"],
                occurrence_capable_evidence_kinds=self.profile[
                    "occurrence_capable_evidence_kinds"
                ],
                observer_policy=self.profile["observer_policy"],
                time_policy=self.profile["time_policy"],
                authority_policy=self.profile["authority_policy"],
                procedure_policy=self.profile["procedure_policy"],
                artifact_policy=self.profile["artifact_policy"],
                authenticity_policy=self.profile["authenticity_policy"],
                causality_policy=self.profile["causality_policy"],
                threat_assumptions=self.profile["threat_assumptions"],
                limitations=self.profile["limitations"],
            )

    def test_profile_mismatch_is_rejected_by_exact_replay_validator(self) -> None:
        assessment = self._assessment()
        with self.assertRaisesRegex(ActionEvidenceError, "profile reference mismatch"):
            validate_action_evidence_assessment(
                assessment, profile=self._profile("pending")
            )

    def test_authority_actor_mismatch_is_refuted_and_expiry_is_unproved(self) -> None:
        mismatched = self._assessment(grants=[self._grant(grantee=self.other_actor)])
        self.assertEqual(self._claims(mismatched)["authority"]["state"], "refuted")

        expired = self._assessment(
            grants=[self._grant(expires_at="2026-07-15T12:00:00Z")]
        )
        claim = self._claims(expired)["authority"]
        self.assertEqual(claim["state"], "unproved")
        self.assertIn("authority_grant_expired", claim["reasons"])

    def test_untrusted_time_blocks_time_bound_claims(self) -> None:
        event = self._event(time_attestation=self.untrusted_time)
        observation = self._observation(
            event, time_attestation=self.untrusted_time
        )
        signature = self._signature(
            event["event_digest"],
            self.actor,
            "untrusted-time-event",
            time_attestation=self.untrusted_time,
        )
        assessment = self._assessment(
            event=event,
            observations=[observation],
            signatures=[signature],
            causal=[],
        )
        claims = self._claims(assessment)
        self.assertEqual(claims["occurrence"]["state"], "unproved")
        self.assertEqual(claims["authority"]["state"], "unproved")
        self.assertEqual(claims["authenticity"]["state"], "unproved")

    def test_artifact_digest_mismatch_refutes_provenance(self) -> None:
        mismatched_output = deepcopy(self.output_artifact)
        mismatched_output["content_digest"] = digest("different-output")
        observation = self._observation(
            self.event, observed_output_artifacts=[mismatched_output]
        )
        assessment = self._assessment(observations=[observation], causal=[])
        self.assertEqual(
            self._claims(assessment)["artifact_provenance"]["state"], "refuted"
        )

    def test_input_digest_mismatch_also_refutes_provenance(self) -> None:
        mismatched_input = deepcopy(self.input_artifact)
        mismatched_input["content_digest"] = digest("different-input")
        observation = self._observation(
            self.event, observed_input_artifacts=[mismatched_input]
        )
        assessment = self._assessment(observations=[observation], causal=[])
        self.assertEqual(
            self._claims(assessment)["artifact_provenance"]["state"], "refuted"
        )

    def test_unobserved_stage_is_unproved(self) -> None:
        observation = self._observation(
            self.event,
            observed_stage_ids=["stage.prepare", "stage.execute"],
        )
        assessment = self._assessment(observations=[observation], causal=[])
        self.assertEqual(self._claims(assessment)["procedure"]["state"], "unproved")

    def test_stop_condition_violation_refutes_procedure(self) -> None:
        violating_stops = deepcopy(self.stops)
        violating_stops[0]["triggered"] = True
        event = self._event(stops=violating_stops)
        observation = self._observation(event)
        assessment = self._assessment(
            event=event,
            expected_action_spec=event["action_spec"],
            observations=[observation],
            grants=[],
            signatures=[],
            causal=[],
        )
        procedure = self._claims(assessment)["procedure"]
        self.assertEqual(procedure["state"], "refuted")
        self.assertIn("stop_condition_violated", procedure["reasons"])

    def test_future_procedure_stage_refutes_procedure_timeline(self) -> None:
        future_stages = deepcopy(self.stages)
        future_stages[-1]["observed_at"] = "2026-07-16T00:20:00Z"
        event = self._event(stages=future_stages)
        observation = self._observation(event)
        assessment = self._assessment(
            event=event,
            observations=[observation],
            grants=[],
            signatures=[],
            causal=[],
        )
        procedure = self._claims(assessment)["procedure"]
        self.assertEqual(procedure["state"], "refuted")
        self.assertIn(
            "procedure_stage_time_outside_event_evaluation_window",
            procedure["reasons"],
        )

    def test_signed_semantic_substitution_refutes_occurrence_and_authenticity(self) -> None:
        expected = {**self.action_spec, "intent_digest": digest("substituted-intent")}
        assessment = self._assessment(expected_action_spec=expected)
        claims = self._claims(assessment)
        self.assertEqual(claims["occurrence"]["state"], "refuted")
        self.assertEqual(claims["authenticity"]["state"], "refuted")
        self.assertIn(
            "signature_does_not_cure_semantic_substitution",
            claims["authenticity"]["reasons"],
        )

    def test_missing_external_signature_clock_and_root_leave_authenticity_unproved(self) -> None:
        event = self._event(time_attestation=self.untrusted_time)
        observation = self._observation(event, time_attestation=self.untrusted_time)
        assessment = self._assessment(
            event=event,
            observations=[observation],
            grants=[],
            signatures=[],
            causal=[],
        )
        authenticity = self._claims(assessment)["authenticity"]
        self.assertEqual(authenticity["state"], "unproved")
        self.assertIn("external_signature_missing", authenticity["reasons"])
        self.assertIn(
            "external_clock_or_clock_trust_root_missing", authenticity["reasons"]
        )

    def test_disallowed_signer_does_not_prove_authenticity(self) -> None:
        signature = self._signature(
            self.event["event_digest"], self.other_actor, "wrong-signer"
        )
        assessment = self._assessment(signatures=[signature])
        authenticity = self._claims(assessment)["authenticity"]
        self.assertEqual(authenticity["state"], "unproved")
        self.assertIn(
            "event_signature_signer_not_allowed_by_profile",
            authenticity["reasons"],
        )

    def test_same_signer_label_with_wrong_identity_digest_is_not_allowed(self) -> None:
        lookalike = binding(self.actor["entity_id"], "1", "lookalike-key")
        signature = self._signature(
            self.event["event_digest"], lookalike, "lookalike-signer"
        )
        assessment = self._assessment(signatures=[signature])
        self.assertEqual(
            self._claims(assessment)["authenticity"]["state"], "unproved"
        )

    def test_future_signature_verification_does_not_prove_authenticity(self) -> None:
        signature = self._signature(
            self.event["event_digest"],
            self.actor,
            "future-signature",
            verified_at="2026-07-16T00:20:00Z",
        )
        assessment = self._assessment(signatures=[signature])
        self.assertEqual(
            self._claims(assessment)["authenticity"]["state"], "unproved"
        )

    def test_trusted_failed_event_signature_refutes_authenticity(self) -> None:
        signature = self._signature(
            self.event["event_digest"],
            self.actor,
            "failed-event-signature",
            verification_status="failed",
        )
        assessment = self._assessment(signatures=[signature])
        authenticity = self._claims(assessment)["authenticity"]
        self.assertEqual(authenticity["state"], "refuted")
        self.assertIn(
            "event_signature_verification_failed", authenticity["reasons"]
        )

    def test_profile_and_event_identifiers_are_order_deterministic(self) -> None:
        self.assertEqual(self.profile, self._profile("adopted", reverse=True))
        extra = artifact("artifact.log", "execution_log", "log")
        event_a = self._event(output_artifacts=[self.output_artifact, extra])
        event_b = self._event(
            output_artifacts=[extra, self.output_artifact],
            stages=list(reversed(self.stages)),
        )
        self.assertEqual(event_a, event_b)

    def test_duplicate_observation_is_rejected(self) -> None:
        with self.assertRaisesRegex(ActionEvidenceError, "duplicate observation_id"):
            self._assessment(
                observations=[self.observation, self.observation], causal=[]
            )

    def test_exact_replay_rejects_claim_result_tamper(self) -> None:
        assessment = self._assessment()
        tampered = deepcopy(assessment)
        tampered["claim_results"][0]["state"] = "unproved"
        with self.assertRaisesRegex(ActionEvidenceError, "do not replay exactly"):
            validate_action_evidence_assessment(tampered, profile=self.profile)

    def test_missing_causal_observation_is_unproved(self) -> None:
        assessment = self._assessment(causal=[])
        self.assertEqual(self._claims(assessment)["causality"]["state"], "unproved")

    def test_causal_observer_must_have_observed_the_effect_artifact(self) -> None:
        log_output = artifact("artifact.execution.log", "execution_log", "log")
        event = self._event(
            output_artifacts=[self.output_artifact, log_output]
        )
        observation = self._observation(
            event, observed_output_artifacts=[self.output_artifact]
        )
        causal = build_causal_observation(
            event=event,
            effect_artifact_ref=log_output,
            observer_observation_id=observation["observation_id"],
            method="trace_link",
            outcome="supports",
            observed_at="2026-07-16T00:07:00Z",
            time_attestation=self.trusted_time,
            evidence_digest=digest("unseen-effect-trace"),
        )
        assessment = self._assessment(
            event=event,
            observations=[observation],
            grants=[],
            signatures=[],
            causal=[causal],
        )
        self.assertEqual(self._claims(assessment)["causality"]["state"], "unproved")

    def test_causal_record_cannot_predate_its_observer_record(self) -> None:
        causal = build_causal_observation(
            event=self.event,
            effect_artifact_ref=self.output_artifact,
            observer_observation_id=self.observation["observation_id"],
            method="trace_link",
            outcome="supports",
            observed_at="2026-07-16T00:04:00Z",
            time_attestation=self.trusted_time,
            evidence_digest=digest("premature-causal-trace"),
        )
        assessment = self._assessment(causal=[causal])
        self.assertEqual(self._claims(assessment)["causality"]["state"], "unproved")

    def test_causal_event_substitution_refutes_causality(self) -> None:
        other_spec = {**self.action_spec, "parameters_digest": digest("causal-other")}
        other_event = self._event(action_spec=other_spec)
        substituted = build_causal_observation(
            event=other_event,
            effect_artifact_ref=other_event["output_artifacts"][0],
            observer_observation_id=self.observation["observation_id"],
            method="trace_link",
            outcome="supports",
            observed_at="2026-07-16T00:07:00Z",
            time_attestation=self.trusted_time,
            evidence_digest=digest("substituted-causal-trace"),
        )
        assessment = self._assessment(causal=[substituted])
        self.assertEqual(self._claims(assessment)["causality"]["state"], "refuted")

    def test_grant_signature_by_non_grantor_is_rejected(self) -> None:
        with self.assertRaisesRegex(ActionEvidenceError, "signer is not the grantor"):
            self._grant(signer=self.other_actor)

    def test_unsigned_exact_grant_is_unproved_not_refuted(self) -> None:
        assessment = self._assessment(grants=[self._grant(signed=False)])
        authority = self._claims(assessment)["authority"]
        self.assertEqual(authority["state"], "unproved")
        self.assertIn("authority_grant_assurance_incomplete", authority["reasons"])

    def test_grant_from_unapproved_grantor_is_refuted(self) -> None:
        assessment = self._assessment(
            grants=[self._grant(grantor=self.other_actor)]
        )
        self.assertEqual(self._claims(assessment)["authority"]["state"], "refuted")

    def test_unapproved_observer_cannot_prove_occurrence(self) -> None:
        observation = self._observation(
            self.event,
            observer_identity=self.other_actor,
            relationship_to_actor="independent",
        )
        assessment = self._assessment(
            observations=[observation], grants=[], signatures=[], causal=[]
        )
        self.assertEqual(self._claims(assessment)["occurrence"]["state"], "unproved")

    def test_unapproved_clock_and_trust_root_cannot_prove_timed_claims(self) -> None:
        foreign_root = {
            "root_id": "trust-root.foreign",
            "root_version": "1",
            "locator": "trust/foreign.pem",
            "content_digest": digest("foreign-root"),
        }
        foreign_time = {
            "time_trust": "trusted",
            "clock_identity": binding("clock.foreign", "1", "foreign-clock"),
            "trust_root_ref": foreign_root,
        }
        event = self._event(time_attestation=foreign_time)
        observation = self._observation(event, time_attestation=foreign_time)
        assessment = self._assessment(
            event=event,
            observations=[observation],
            grants=[],
            signatures=[],
            causal=[],
        )
        claims = self._claims(assessment)
        self.assertEqual(claims["occurrence"]["state"], "unproved")
        self.assertEqual(claims["authenticity"]["state"], "unproved")

    def test_observation_semantic_binding_mismatch_refutes_occurrence(self) -> None:
        observation = self._observation(
            self.event, observed_action_spec_digest=digest("other-action-spec")
        )
        assessment = self._assessment(observations=[observation], causal=[])
        occurrence = self._claims(assessment)["occurrence"]
        self.assertEqual(occurrence["state"], "refuted")
        self.assertIn(
            "observation_action_or_environment_binding_mismatch",
            occurrence["reasons"],
        )

    def test_observation_cannot_name_stage_absent_from_event(self) -> None:
        observation = self._observation(
            self.event,
            observed_stage_ids=[
                "stage.prepare",
                "stage.execute",
                "stage.verify",
                "stage.unbound",
            ],
        )
        with self.assertRaisesRegex(ActionEvidenceError, "stages absent"):
            self._assessment(observations=[observation], causal=[])

    def test_profile_rejects_noncontiguous_procedure_denominator(self) -> None:
        tampered = deepcopy(self.profile)
        tampered["procedure_policy"]["required_stages"][1]["order"] = 4
        with self.assertRaises(ActionEvidenceError):
            validate_action_assurance_profile(tampered)

    def test_human_adoption_decision_cannot_be_reused_for_changed_profile(self) -> None:
        with self.assertRaisesRegex(ActionEvidenceError, "target_basis_digest"):
            build_action_assurance_profile(
                profile_id=self.profile["profile_id"],
                profile_version=self.profile["profile_version"],
                adoption_state="adopted",
                human_decision_ref=self.profile["human_decision_ref"],
                required_claim_classes=["occurrence"],
                occurrence_capable_evidence_kinds=self.profile[
                    "occurrence_capable_evidence_kinds"
                ],
                observer_policy=self.profile["observer_policy"],
                time_policy=self.profile["time_policy"],
                authority_policy=self.profile["authority_policy"],
                procedure_policy=self.profile["procedure_policy"],
                artifact_policy=self.profile["artifact_policy"],
                authenticity_policy=self.profile["authenticity_policy"],
                causality_policy=self.profile["causality_policy"],
                threat_assumptions=self.profile["threat_assumptions"],
                limitations=self.profile["limitations"],
            )

    def test_v0_action_profile_is_not_implicitly_accepted(self) -> None:
        profile = deepcopy(self.profile)
        profile["schema_version"] = "action-assurance-profile/v0"
        with self.assertRaisesRegex(ActionEvidenceError, "schema violation"):
            validate_action_assurance_profile(profile)


if __name__ == "__main__":
    unittest.main()
