from __future__ import annotations

from copy import deepcopy
import unittest

from semantic_guard.transition_control import (
    DEFAULT_RETIRE_GATES,
    STAGES,
    STAGE_GATE_REQUIREMENTS,
    TransitionControlError,
    build_abort_criterion,
    build_abort_observation,
    build_compatibility_window,
    build_gate_evidence,
    build_stage_completion,
    build_transition_plan,
    validate_transition_plan,
)
from tests import test_operational_qualification as _operational_tests


digest = _operational_tests.digest
identity = _operational_tests.identity
refresh_digest = _operational_tests.refresh_digest


def artifact(name: str, *, version: str = "1") -> dict:
    return {
        "artifact_id": f"artifact.{name}",
        "artifact_version": version,
        "locator": f"artifacts/{name}.json",
        "content_digest": digest(f"artifact-{name}-{version}"),
    }


def transition_decision(
    kind: str,
    target_id: str,
    target_version: str,
    target_stage: str | None,
    target_digest: dict,
    label: str,
    *,
    irreversible: bool = False,
) -> dict:
    return {
        "decision_id": f"decision.{label}",
        "decision_kind": kind,
        "decision_source": "external_human_record",
        "actor_kind": "human",
        "decided_by": "human.owner",
        "decided_at": "2026-07-16T01:20:00Z",
        "status": "accepted",
        "target_id": target_id,
        "target_version": target_version,
        "target_stage": target_stage,
        "target_digest": deepcopy(target_digest),
        "trust_class": "signed",
        "record_ref": {
            "record_id": f"record.{label}",
            "locator": f"decisions/{label}.json",
            "content_digest": digest(f"decision-{label}"),
        },
        "acknowledgements": {
            "rollback_unavailable": irreversible,
            "predecessor_recovery_unavailable": irreversible,
        },
    }


class TransitionControlTests(unittest.TestCase):
    def setUp(self) -> None:
        operational_fixture = _operational_tests.OperationalQualificationTests(
            "test_all_scenarios_independent_review_and_human_authorization_are_separate"
        )
        operational_fixture.setUp()
        self.operational_fixture = operational_fixture
        self.profile = operational_fixture.profile
        self.envelope = operational_fixture.envelope
        self.qualification = operational_fixture._qualification()
        self.scope_digest = self.qualification["scope_digest"]
        self.predecessor = identity("predecessor")
        self.successor = identity("successor")
        self.abort_criterion = build_abort_criterion(
            criterion_id="abort.error-rate",
            criterion_version="1",
            metric="error_rate",
            comparator="gte",
            threshold_value=0.05,
            unit="ratio",
        )
        self.compatibility_window = build_compatibility_window(
            window_id="window.transition",
            window_version="1",
            starts_at="2026-07-16T00:00:00Z",
            ends_at="2026-07-16T03:00:00Z",
            predecessor_ref=self.predecessor,
            successor_ref=self.successor,
            compatibility_evidence_ref=artifact("compatibility-window"),
        )
        self.migration_refs = {
            "configuration_migration_ref": artifact("migration-config"),
            "data_migration_ref": artifact("migration-data"),
            "interface_migration_ref": artifact("migration-interface"),
            "evidence_migration_ref": artifact("migration-evidence"),
            "register_update_ref": artifact("register-update"),
        }
        self.rollback_ref = artifact("rollback-recovery")
        self.disposal_ref = artifact("disposal-retirement")

    def _history(self, target_stage: str) -> list[dict]:
        return [
            build_stage_completion(
                stage=stage,
                completed_at=f"2026-07-16T00:{10 + index:02d}:00Z",
                scope_digest=self.scope_digest,
                completion_ref=artifact(f"completion-{stage}"),
                evidence_origin="controlled_execution",
            )
            for index, stage in enumerate(STAGES[: STAGES.index(target_stage)])
        ]

    def _gates(
        self,
        target_stage: str,
        *,
        qualification: dict | None = None,
    ) -> list[dict]:
        used_qualification = qualification or self.qualification
        result: list[dict] = []
        for index, gate_kind in enumerate(STAGE_GATE_REQUIREMENTS[target_stage]):
            if gate_kind == "operational_qualification":
                gate_artifact = {
                    "artifact_id": used_qualification["qualification_id"],
                    "artifact_version": used_qualification["qualification_version"],
                    "locator": "qualifications/current.json",
                    "content_digest": deepcopy(
                        used_qualification["qualification_digest"]
                    ),
                }
                status = (
                    "passed"
                    if used_qualification["outcome"]
                    in {"eligible", "human_authorized"}
                    else "failed"
                )
            elif gate_kind == "register_readiness":
                gate_artifact = self.migration_refs["register_update_ref"]
                status = "passed"
            elif gate_kind == "compatibility_migration":
                gate_artifact = self.migration_refs["evidence_migration_ref"]
                status = "passed"
            elif gate_kind == "rollback_recovery_rehearsal":
                gate_artifact = self.rollback_ref
                status = "passed"
            else:
                gate_artifact = artifact(f"gate-{gate_kind}")
                status = "passed"
            independent = gate_kind in {
                "field_validity",
                "human_use_validation",
                "security_assessment",
                "independent_observation",
            }
            result.append(
                build_gate_evidence(
                    gate_id=f"gate.{target_stage}.{gate_kind}",
                    gate_kind=gate_kind,
                    target_stage=target_stage,
                    artifact_ref=gate_artifact,
                    scope_digest=self.scope_digest,
                    execution_id=f"gate-execution.{target_stage}.{index}",
                    status=status,
                    observed_at="2026-07-16T00:40:00Z",
                    expires_at="2026-07-16T02:40:00Z",
                    time_trust="trusted",
                    trust_class=(
                        "independently_observed" if independent else "tool_reported"
                    ),
                    evidence_origin=(
                        "operational_observation"
                        if gate_kind in {"shadow_observation", "independent_observation"}
                        else "controlled_execution"
                    ),
                    before_state_digest=(
                        digest("rollback-before")
                        if gate_kind == "rollback_recovery_rehearsal"
                        else None
                    ),
                    after_state_digest=(
                        digest("rollback-after")
                        if gate_kind == "rollback_recovery_rehearsal"
                        else None
                    ),
                )
            )
        return result

    def _abort_observations(self, target_stage: str) -> list[dict]:
        return [
            build_abort_observation(
                observation_id=f"abort-observation.{target_stage}",
                criterion=self.abort_criterion,
                target_stage=target_stage,
                scope_digest=self.scope_digest,
                execution_id=f"abort-execution.{target_stage}",
                observed_at="2026-07-16T00:50:00Z",
                triggered=False,
                response="not_triggered",
                evidence_origin="controlled_execution",
                evidence_ref=artifact(f"abort-observation-{target_stage}"),
            )
        ]

    def _build(
        self,
        *,
        target_stage: str = "default",
        adoption_state: str = "pending",
        adoption_decision_ref: dict | None = None,
        retirement_decision_ref: dict | None = None,
        cutover_decision_ref: dict | None = None,
        irreversibility_decision_ref: dict | None = None,
        stage_history: list[dict] | None = None,
        gate_evidence: list[dict] | None = None,
        abort_observations: list[dict] | None = None,
        assessed_at: str = "2026-07-16T01:30:00Z",
        compatibility_window: dict | None = None,
        qualification: dict | None = None,
        predecessor: dict | None = None,
        successor: dict | None = None,
    ) -> dict:
        used_qualification = qualification or self.qualification
        return build_transition_plan(
            plan_id="transition.service",
            plan_version="1",
            adoption_state=adoption_state,
            predecessor_ref=predecessor or self.predecessor,
            successor_ref=successor or self.successor,
            operational_profile=self.profile,
            deployment_envelope=self.envelope,
            operational_qualification=used_qualification,
            abort_criteria=[self.abort_criterion],
            compatibility_window=compatibility_window or self.compatibility_window,
            migration_plan_refs=self.migration_refs,
            rollback_recovery_plan_ref=self.rollback_ref,
            disposal_retirement_plan_ref=self.disposal_ref,
            target_stage=target_stage,
            stage_history=(
                self._history(target_stage)
                if stage_history is None
                else stage_history
            ),
            gate_evidence=(
                self._gates(target_stage, qualification=used_qualification)
                if gate_evidence is None
                else gate_evidence
            ),
            abort_observations=(
                self._abort_observations(target_stage)
                if abort_observations is None
                else abort_observations
            ),
            assessed_at=assessed_at,
            time_trust="trusted",
            adoption_decision_ref=adoption_decision_ref,
            retirement_decision_ref=retirement_decision_ref,
            cutover_decision_ref=cutover_decision_ref,
            irreversibility_decision_ref=irreversibility_decision_ref,
        )

    def _eligible(self, target_stage: str = "default", **kwargs) -> dict:
        pending = self._build(target_stage=target_stage, **kwargs)
        adoption = transition_decision(
            "adopt_transition_plan",
            "transition.service",
            "1",
            None,
            pending["plan_configuration_digest"],
            f"plan-adoption-{target_stage}",
        )
        return self._build(
            target_stage=target_stage,
            adoption_state="adopted",
            adoption_decision_ref=adoption,
            **kwargs,
        )

    def test_default_requires_full_gate_set_and_separate_cutover_decision(self) -> None:
        eligible = self._eligible()
        self.assertEqual(eligible["outcome"], "eligible")
        self.assertEqual(
            tuple(item["gate_kind"] for item in eligible["gate_evidence"]),
            DEFAULT_RETIRE_GATES,
        )
        self.assertEqual(
            tuple(item["stage"] for item in eligible["stage_sequence"]),
            STAGES,
        )
        cutover = transition_decision(
            "authorize_cutover_stage",
            "transition.service",
            "1",
            "default",
            eligible["gate_set_digest"],
            "default-cutover",
        )
        authorized = self._build(
            adoption_state="adopted",
            adoption_decision_ref=eligible["adoption_decision_ref"],
            cutover_decision_ref=cutover,
        )
        self.assertEqual(authorized["outcome"], "human_authorized")
        self.assertFalse(authorized["authority_boundary"]["change_default"])
        validate_transition_plan(
            authorized,
            operational_profile=self.profile,
            deployment_envelope=self.envelope,
            operational_qualification=self.qualification,
        )

    def test_missing_gate_or_stage_history_is_contract_invalid(self) -> None:
        with self.assertRaisesRegex(
            TransitionControlError,
            "every target-stage entry requirement exactly once",
        ):
            self._eligible(gate_evidence=self._gates("default")[:-1])
        with self.assertRaisesRegex(
            TransitionControlError,
            "exact completed prefix",
        ):
            self._eligible(stage_history=self._history("default")[:-1])

    def test_bound_register_or_migration_ref_substitution_is_rejected(self) -> None:
        substitutions = {
            "register_readiness": "register gate",
            "compatibility_migration": "compatibility/migration gate",
        }
        for gate_kind, message in substitutions.items():
            with self.subTest(gate_kind=gate_kind):
                gates = self._gates("default")
                target = next(
                    item for item in gates if item["gate_kind"] == gate_kind
                )
                target["artifact_ref"] = artifact(f"substituted-{gate_kind}")
                refresh_digest(target, "evidence_digest")
                with self.assertRaisesRegex(TransitionControlError, message):
                    self._eligible(gate_evidence=gates)

    def test_unknown_target_or_gate_kind_fails_closed(self) -> None:
        with self.assertRaisesRegex(
            TransitionControlError,
            "unknown transition target stage",
        ):
            self._build(
                target_stage="unbounded",
                stage_history=[],
                gate_evidence=[],
                abort_observations=[],
            )
        gates = self._gates("default")
        gates[0]["gate_kind"] = "unbound_gate"
        refresh_digest(gates[0], "evidence_digest")
        with self.assertRaisesRegex(TransitionControlError, "unknown gate kinds"):
            self._eligible(gate_evidence=gates)

    def test_failed_not_run_out_of_scope_or_synthetic_gate_is_not_eligible(self) -> None:
        mutations = {
            "failed": lambda gate: gate.__setitem__("status", "failed"),
            "not_run": lambda gate: gate.__setitem__("status", "not_run"),
            "out_of_scope": lambda gate: gate.__setitem__("status", "out_of_scope"),
            "synthetic": lambda gate: gate.__setitem__(
                "evidence_origin", "synthetic_fixture"
            ),
        }
        for label, mutation in mutations.items():
            with self.subTest(label=label):
                gates = self._gates("default")
                target = next(
                    item for item in gates if item["gate_kind"] == "field_validity"
                )
                mutation(target)
                refresh_digest(target, "evidence_digest")
                plan = self._eligible(gate_evidence=gates)
                self.assertEqual(plan["outcome"], "not_eligible")

    def test_stale_operational_qualification_cannot_authorize_cutover(self) -> None:
        later_window = build_compatibility_window(
            window_id="window.transition-later",
            window_version="1",
            starts_at="2026-07-16T00:00:00Z",
            ends_at="2026-07-16T05:00:00Z",
            predecessor_ref=self.predecessor,
            successor_ref=self.successor,
            compatibility_evidence_ref=artifact("compatibility-window-later"),
        )
        gates = self._gates("default")
        for gate in gates:
            gate["expires_at"] = "2026-07-16T04:00:00Z"
            refresh_digest(gate, "evidence_digest")
        plan = self._eligible(
            assessed_at="2026-07-16T03:00:00Z",
            compatibility_window=later_window,
            gate_evidence=gates,
        )
        self.assertEqual(plan["outcome"], "not_eligible")
        cutover = transition_decision(
            "authorize_cutover_stage",
            "transition.service",
            "1",
            "default",
            plan["gate_set_digest"],
            "stale-cutover",
        )
        with self.assertRaisesRegex(
            TransitionControlError,
            "cannot override failed, stale",
        ):
            self._build(
                adoption_state="adopted",
                adoption_decision_ref=plan["adoption_decision_ref"],
                cutover_decision_ref=cutover,
                assessed_at="2026-07-16T03:00:00Z",
                compatibility_window=later_window,
                gate_evidence=gates,
            )

    def test_replayed_rehearsal_and_identical_before_after_are_rejected(self) -> None:
        gates = self._gates("default")
        gates[1]["execution_id"] = gates[0]["execution_id"]
        refresh_digest(gates[1], "evidence_digest")
        with self.assertRaisesRegex(
            TransitionControlError,
            "duplicate execution_id|replayed under multiple claims",
        ):
            self._eligible(gate_evidence=gates)

        gates = self._gates("default")
        rollback = next(
            item
            for item in gates
            if item["gate_kind"] == "rollback_recovery_rehearsal"
        )
        rollback["after_state_digest"] = deepcopy(rollback["before_state_digest"])
        refresh_digest(rollback, "evidence_digest")
        with self.assertRaisesRegex(
            TransitionControlError,
            "before and after states are identical",
        ):
            self._eligible(gate_evidence=gates)

    def test_abort_violation_is_rejected_and_triggered_abort_stops_eligibility(self) -> None:
        with self.assertRaisesRegex(
            TransitionControlError,
            "execution continued",
        ):
            build_abort_observation(
                observation_id="abort-observation.violation",
                criterion=self.abort_criterion,
                target_stage="default",
                scope_digest=self.scope_digest,
                execution_id="abort-execution.violation",
                observed_at="2026-07-16T00:50:00Z",
                triggered=True,
                response="continued",
                evidence_origin="controlled_execution",
                evidence_ref=artifact("abort-violation"),
            )
        triggered = build_abort_observation(
            observation_id="abort-observation.triggered",
            criterion=self.abort_criterion,
            target_stage="default",
            scope_digest=self.scope_digest,
            execution_id="abort-execution.triggered",
            observed_at="2026-07-16T00:50:00Z",
            triggered=True,
            response="aborted_and_rollback_started",
            evidence_origin="controlled_execution",
            evidence_ref=artifact("abort-triggered"),
        )
        plan = self._eligible(abort_observations=[triggered])
        self.assertEqual(plan["outcome"], "not_eligible")

    def test_predecessor_retirement_requires_two_separate_human_decisions(self) -> None:
        eligible = self._eligible("predecessor_retired")
        cutover = transition_decision(
            "authorize_cutover_stage",
            "transition.service",
            "1",
            "predecessor_retired",
            eligible["gate_set_digest"],
            "retirement-cutover",
        )
        cutover_only = self._build(
            target_stage="predecessor_retired",
            adoption_state="adopted",
            adoption_decision_ref=eligible["adoption_decision_ref"],
            cutover_decision_ref=cutover,
        )
        self.assertEqual(cutover_only["outcome"], "eligible")
        irreversible = transition_decision(
            "authorize_irreversible_predecessor_retirement",
            "transition.service",
            "1",
            "predecessor_retired",
            eligible["retirement_basis_digest"],
            "retirement-irreversible",
            irreversible=True,
        )
        authorized = self._build(
            target_stage="predecessor_retired",
            adoption_state="adopted",
            adoption_decision_ref=eligible["adoption_decision_ref"],
            cutover_decision_ref=cutover,
            irreversibility_decision_ref=irreversible,
        )
        self.assertEqual(authorized["outcome"], "human_authorized")
        self.assertFalse(authorized["authority_boundary"]["retire"])

    def test_same_predecessor_successor_and_forged_human_target_are_rejected(self) -> None:
        with self.assertRaisesRegex(
            TransitionControlError,
            "cannot be the same identity",
        ):
            self._build(successor=self.predecessor)
        eligible = self._eligible()
        forged = transition_decision(
            "authorize_cutover_stage",
            "transition.other",
            "1",
            "default",
            eligible["gate_set_digest"],
            "forged-cutover",
        )
        with self.assertRaisesRegex(
            TransitionControlError,
            "target or decision kind mismatch",
        ):
            self._build(
                adoption_state="adopted",
                adoption_decision_ref=eligible["adoption_decision_ref"],
                cutover_decision_ref=forged,
            )

    def test_local_unit_only_operational_material_cannot_open_transition_gate(self) -> None:
        observations = deepcopy(self.operational_fixture.observations)
        for observation in observations:
            observation["execution_kind"] = "unit_test"
            refresh_digest(observation, "observation_digest")
        local_only = self.operational_fixture._qualification(
            observations=observations
        )
        self.assertEqual(local_only["outcome"], "not_eligible")
        gates = self._gates("default", qualification=local_only)
        plan = self._eligible(
            gate_evidence=gates,
            qualification=local_only,
        )
        self.assertEqual(plan["outcome"], "not_eligible")


if __name__ == "__main__":
    unittest.main()
