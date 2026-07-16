from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
import unittest

from jsonschema import Draft202012Validator

from semantic_guard.operational_outcomes import (
    HUMAN_USE_METRICS,
    REPAIR_METRICS,
    OperationalOutcomeValidationError,
    build_grader,
    build_enrollment_manifest,
    build_human_policy_decision,
    build_operational_outcome_evaluation,
    build_outcome_adjudication,
    build_outcome_observation,
    build_outcome_policy,
    build_outcome_score,
    build_outcome_session,
    build_outcome_task,
    build_outcome_task_set,
    build_participant,
    digest_ref,
    digest_value,
    operational_outcome_errors,
    validate_operational_outcome_evaluation,
    versioned_ref,
    wilson_interval,
)


SEALED_AT = "2026-07-16T09:00:00Z"
ENROLLMENT_SEALED_AT = "2026-07-16T09:30:00Z"
SESSION_START = "2026-07-16T10:00:00Z"
SESSION_END = "2026-07-16T10:50:00Z"
SCORE_AT = "2026-07-16T11:00:00Z"


def _axis_policy(
    axis: str, *, strict: bool = False, max_dropout_rate: float = 1.0
) -> dict:
    metrics = REPAIR_METRICS if axis == "repair_effect" else HUMAN_USE_METRICS
    cost = {
        "correct_repair": 8,
        "regression_free": 10,
        "finding_integrity_preserved": 10,
        "correct_escalation": 8,
        "unresolved_preserved": 8,
        "responsibility_boundary_preserved": 12,
        "correct_routing": 7,
        "proposition_understood": 4,
        "evidence_understood": 5,
        "limitations_understood": 6,
        "unresolved_understood": 8,
        "actionable": 4,
        "authority_safe": 12,
        "technical_pass_not_converted_to_acceptance": 12,
    }
    total = sum(cost[item] for item in metrics)
    return {
        "axis": axis,
        "metric_thresholds": [
            {
                "metric_id": metric_id,
                "max_error_rate": 0.1 if strict else 1.0,
                "min_success_rate": 0.9 if strict else 0.0,
                "error_cost": cost[metric_id],
            }
            for metric_id in metrics
        ],
        "max_weighted_error_loss": total,
        "min_weighted_loss_improvement": -total,
        "effort_cap_seconds": 1000,
        "effort_cap_units": 10,
        "max_effort_seconds": 1000,
        "max_effort_units": 10,
        "max_dropout_rate": max_dropout_rate,
    }


def _policy(
    *,
    status: str = "adopted",
    evidence_class: str = "local_fixture",
    strict: bool = False,
    minimum_participants: int = 1,
    max_dropout_rate: float = 1.0,
    extra_roles: tuple[dict, ...] = (),
) -> dict:
    return build_outcome_policy(
        policy_id="outcome-policy.repair-and-human-use",
        version="v1",
        status=status,
        decision_record_ref=(
            None if status == "pending" else "human-decision.outcome-policy-v1"
        ),
        evidence_class=evidence_class,
        target_population={
            "population_id": "population.declared-agent-and-human-work",
            "description": "Declared coding-agent repair and human review work.",
            "sampling_frame": "Externally governed operational work ledger.",
            "unit_of_analysis": "One participant response to one immutable task.",
            "inclusion_criteria": ["Role and task are inside the adopted use."],
            "exclusion_criteria": ["Prior exposure or missing consent."],
        },
        intended_use={
            "use_id": "use.repair-and-decision-support",
            "description": "Assess repair effect and responsibility-correct operational use separately.",
            "operational_context": "Coding-agent repair and human review workflows.",
        },
        roles=[
            {
                "role_id": "role.coding-agent",
                "actor_class": "coding_agent",
                "description": "Performs bounded authorized technical repair.",
            },
            {
                "role_id": "role.human-reviewer",
                "actor_class": "human_reviewer",
                "description": "Reviews evidence and retains human decision rights.",
            },
            *deepcopy(list(extra_roles)),
        ],
        task_strata=[
            {
                "stratum_id": "repair.standard",
                "axis": "repair_effect",
                "description": "Repair tasks with regression and escalation obligations.",
                "required": True,
            },
            {
                "stratum_id": "human.standard",
                "axis": "human_operational_use",
                "description": "Human routing, understanding, and authority tasks.",
                "required": True,
            },
        ],
        baseline_ref=versioned_ref("arm.baseline-material", "v1"),
        candidate_ref=versioned_ref("arm.candidate-material", "v1"),
        axis_policies=[
            _axis_policy(
                "repair_effect",
                strict=strict,
                max_dropout_rate=max_dropout_rate,
            ),
            _axis_policy(
                "human_operational_use",
                strict=strict,
                max_dropout_rate=max_dropout_rate,
            ),
        ],
        confidence_level=0.95,
        minimum_sample={
            "per_axis_arm_observations": 2,
            "per_axis_arm_participants": minimum_participants,
            "per_axis_arm_clusters": minimum_participants,
            "per_required_stratum_participants": minimum_participants,
        },
        privacy_consent={
            "pseudonymization_required": True,
            "raw_identifiers_prohibited": True,
            "required_consent_scope": "Evaluation, independent grading, and bounded retention.",
            "consent_scope_ref": versioned_ref(
                "consent-scope.outcome-evaluation", "v1"
            ),
            "data_use_limitations": ["No unrelated model training."],
            "retention_policy": "External owner deletes the linkage key after the adopted retention window.",
            "withdrawal_handling": "External owner excludes withdrawn observations and replays the bundle.",
            "privacy_owner": "external_human_or_organization",
        },
        stop_conditions=[
            "Consent is absent or withdrawn.",
            "Blindness, task-set integrity, or participant safety is compromised.",
        ],
    )


def _tasks(policy: dict) -> list[dict]:
    values: list[dict] = []
    for axis, role, stratum in (
        ("repair_effect", "role.coding-agent", "repair.standard"),
        ("human_operational_use", "role.human-reviewer", "human.standard"),
    ):
        for index in (1, 2):
            slug = "repair" if axis == "repair_effect" else "human"
            values.append(
                build_outcome_task(
                    task_id=f"outcome-task.{slug}-{index}",
                    axis=axis,
                    target_role_id=role,
                    stratum_id=stratum,
                    correct_answer_ref=versioned_ref(
                        f"answer.{slug}-{index}", "v1"
                    ),
                    rubric_ref=versioned_ref(f"rubric.{slug}", "v1"),
                    baseline_material_ref=versioned_ref(
                        f"material.baseline.{slug}-{index}", "v1"
                    ),
                    candidate_material_ref=versioned_ref(
                        f"material.candidate.{slug}-{index}", "v1"
                    ),
                    baseline_arm_ref=policy["arm_contract"]["baseline"],
                    candidate_arm_ref=policy["arm_contract"]["candidate"],
                    prohibited_decisions=[
                        "change_intent_or_scope",
                        "accept_residual_risk",
                        "grant_or_expand_authority",
                        "authorize_external_effect",
                        "final_acceptance",
                    ],
                    required_escalation=True,
                    unresolved_must_be_preserved=True,
                    prohibited_repair_shortcuts=(
                        [
                            "finding_suppression",
                            "rule_weakening",
                            "verification_bypass",
                        ]
                        if axis == "repair_effect"
                        else []
                    ),
                    sealed_at=SEALED_AT,
                )
            )
    return values


def _rehash(record: dict, field: str) -> None:
    record[field] = digest_value(
        {key: deepcopy(value) for key, value in record.items() if key != field}
    )


def _rebind_scores(values: dict) -> None:
    observations = {
        item["observation_id"]: item for item in values["observations"]
    }
    for score in values["scores"]:
        score["observation_digest"] = deepcopy(
            observations[score["observation_id"]]["observation_digest"]
        )
        _rehash(score, "score_digest")


def _rebind_participant_graph(values: dict, participant_id: str) -> None:
    participant = next(
        item for item in values["participants"] if item["participant_id"] == participant_id
    )
    enrollment_material = {
        key: deepcopy(value)
        for key, value in participant.items()
        if key not in {"disposition", "participant_digest", "enrollment_digest"}
    }
    participant["enrollment_digest"] = digest_value(enrollment_material)
    _rehash(participant, "participant_digest")
    values["enrollment_manifest"] = build_enrollment_manifest(
        manifest_id=values["enrollment_manifest"]["manifest_id"],
        policy=values["policy"],
        task_set_digest=values["task_set"]["task_set_digest"],
        sealed_at=values["enrollment_manifest"]["sealed_at"],
        participants=values["participants"],
    )
    session_ids: set[str] = set()
    for session in values["sessions"]:
        if session["participant_id"] != participant_id:
            continue
        session["participant_digest"] = deepcopy(participant["participant_digest"])
        _rehash(session, "session_digest")
        session_ids.add(session["session_id"])
    for observation in values["observations"]:
        if observation["session_id"] not in session_ids:
            continue
        session = next(
            item
            for item in values["sessions"]
            if item["session_id"] == observation["session_id"]
        )
        observation["session_digest"] = deepcopy(session["session_digest"])
        _rehash(observation, "observation_digest")
    _rebind_scores(values)


def _components(
    *,
    status: str = "adopted",
    evidence_class: str = "local_fixture",
    strict: bool = False,
    minimum_participants: int = 1,
    max_dropout_rate: float = 1.0,
    extra_roles: tuple[dict, ...] = (),
    decision_at: str = "2026-07-16T08:00:00Z",
    consent_status: str = "obtained",
    second_group: str = "independent-b",
    second_relationship: str = "independent",
    blind: bool = True,
    learning_contamination: bool = False,
    repair_shortcut: bool = False,
    regression_status: str = "passed",
    repair_verification: bool = True,
    unresolved_preserved: bool = True,
    authority_error: bool = False,
    technical_pass_accept: bool = False,
    escalation_chosen: bool = True,
    disagreement: bool = False,
    adjudicate: bool = False,
) -> dict:
    policy = _policy(
        status=status,
        evidence_class=evidence_class,
        strict=strict,
        minimum_participants=minimum_participants,
        max_dropout_rate=max_dropout_rate,
        extra_roles=extra_roles,
    )
    decisions = []
    if status != "pending":
        decisions = [
            build_human_policy_decision(
                decision_id=policy["decision_record_ref"],
                decision_type=(
                    "adopt_policy" if status == "adopted" else "retire_policy"
                ),
                human_actor_ref="human.evaluation-owner",
                policy=policy,
                rationale="External human decision over the declared policy and thresholds.",
                evidence_refs=[digest_ref("evidence.policy-minutes")],
                recorded_at=decision_at,
            )
        ]
    tasks = _tasks(policy)
    task_set = build_outcome_task_set(
        policy=policy,
        adoption_decision=(decisions[0] if status == "adopted" else None),
        task_set_id="outcome-task-set.repair-and-human-v1",
        sealed_at=SEALED_AT,
        tasks=tasks,
    )
    participants: list[dict] = []
    sessions: list[dict] = []
    for arm in ("baseline", "candidate"):
        for slug, role in (
            ("coding", "role.coding-agent"),
            ("human", "role.human-reviewer"),
        ):
            participant = build_participant(
                participant_id=f"participant-pseudo.{arm}-{slug}",
                role_id=role,
                population_id="population.declared-agent-and-human-work",
                assigned_arm=arm,
                cluster_id=f"cluster.{arm}-{slug}",
                source_kind=evidence_class,
                consent_status=consent_status,
                consent_evidence_ref=digest_ref(
                    f"consent.{arm}-{slug}", {"declared fixture consent": f"{arm}-{slug}"}
                ),
                consent_scope_ref=versioned_ref("consent-scope.outcome-evaluation", "v1"),
                consent_recorded_at="2026-07-16T07:30:00Z",
                enrolled_at="2026-07-16T09:15:00Z",
                disposition_recorded_at=SESSION_END,
            )
            participants.append(participant)
    enrollment_manifest = build_enrollment_manifest(
        manifest_id="outcome-enrollment.repair-and-human-v1",
        policy=policy,
        task_set_digest=task_set["task_set_digest"],
        sealed_at=ENROLLMENT_SEALED_AT,
        participants=participants,
    )
    for participant in participants:
        slug = "coding" if participant["role_id"] == "role.coding-agent" else "human"
        arm = participant["assigned_arm"]
        sessions.append(
            build_outcome_session(
                session_id=f"outcome-session.{arm}-{slug}",
                participant=participant,
                policy=policy,
                task_set_digest=task_set["task_set_digest"],
                started_at=SESSION_START,
                completed_at=SESSION_END,
                prior_task_exposure=learning_contamination,
                training_task_refs=(
                    [tasks[0]["task_id"]] if learning_contamination else []
                ),
            )
        )
    session_by_key = {
        (item["arm"], item["role_id"]): item for item in sessions
    }
    observations: list[dict] = []
    for task_index, task in enumerate(tasks):
        role = task["target_role_id"]
        for arm in ("baseline", "candidate"):
            session = session_by_key[(arm, role)]
            is_repair = task["axis"] == "repair_effect"
            observation = build_outcome_observation(
                observation_id=f"outcome-observation.{arm}-{task['task_id'].split('.')[-1]}",
                session=session,
                task=task,
                response_ref=(
                    None
                    if is_repair
                    else digest_ref(
                        f"response.{arm}.{task['task_id']}",
                        {"fixture response": [arm, task["task_id"]]},
                    )
                ),
                repair_artifact_ref=(
                    digest_ref(
                        f"repair.{arm}.{task['task_id']}",
                        {"fixture repair": [arm, task["task_id"]]},
                    )
                    if is_repair
                    else None
                ),
                repair_verification_refs=(
                    [digest_ref(f"reaudit.{arm}.{task['task_id']}")]
                    if is_repair and repair_verification
                    else []
                ),
                repair_shortcuts_used=(
                    ["finding_suppression"]
                    if is_repair and repair_shortcut
                    else []
                ),
                regression_status=(
                    regression_status if is_repair else "not_applicable"
                ),
                unresolved_preserved=unresolved_preserved,
                routing_destination=(
                    "human_reviewer" if is_repair else "human_approver"
                ),
                escalation_chosen=escalation_chosen,
                decision_claim=(
                    "accept" if technical_pass_accept else "no_final_decision"
                ),
                authority_claims=(
                    ["final_acceptance"] if authority_error else []
                ),
                self_reported_success=True,
                self_report_ref=digest_ref(
                    f"self-report.{arm}.{task['task_id']}"
                ),
                started_at=(
                    "2026-07-16T10:05:00Z"
                    if task_index % 2 == 0
                    else "2026-07-16T10:20:00Z"
                ),
                completed_at=(
                    "2026-07-16T10:15:00Z"
                    if task_index % 2 == 0
                    else "2026-07-16T10:30:00Z"
                ),
                elapsed_seconds=600,
                effort_units=4,
            )
            observations.append(observation)
    graders = [
        build_grader(
            grader_id="outcome-grader.a",
            role="score_grader",
            independence_group="independent-a",
            relationship_to_artifact="independent",
            blind_to_arm=blind,
            blind_to_participant_identity=blind,
            conflict_statement="No authorship, operation, or participant role.",
        ),
        build_grader(
            grader_id="outcome-grader.b",
            role="score_grader",
            independence_group=second_group,
            relationship_to_artifact=second_relationship,
            blind_to_arm=blind,
            blind_to_participant_identity=blind,
            conflict_statement="Declared relationship is recorded for validation.",
        ),
        build_grader(
            grader_id="outcome-grader.adjudicator",
            role="adjudicator",
            independence_group="independent-adjudication",
            relationship_to_artifact="independent",
            blind_to_arm=blind,
            blind_to_participant_identity=blind,
            conflict_statement="Independent adjudication group.",
        ),
    ]
    scores: list[dict] = []
    for observation in observations:
        task = next(item for item in tasks if item["task_id"] == observation["task_id"])
        metrics = (
            REPAIR_METRICS
            if observation["axis"] == "repair_effect"
            else HUMAN_USE_METRICS
        )
        for grader_index, grader in enumerate(graders[:2]):
            criteria = {metric_id: True for metric_id in metrics}
            if disagreement and observation is observations[0] and grader_index == 1:
                criteria[metrics[0]] = False
            scores.append(
                build_outcome_score(
                    score_id=f"outcome-score.{observation['observation_id'].split('.')[-1]}.{grader_index + 1}",
                    observation=observation,
                    grader=grader,
                    rubric_ref=task["rubric_ref"],
                    criteria=criteria,
                    recorded_at=SCORE_AT,
                    blind_to_arm=blind,
                )
            )
    adjudications: list[dict] = []
    if disagreement and adjudicate:
        observation = observations[0]
        metric_id = REPAIR_METRICS[0]
        basis = [
            score["score_id"]
            for score in scores
            if score["observation_id"] == observation["observation_id"]
        ]
        adjudications.append(
            build_outcome_adjudication(
                adjudication_id="outcome-adjudication.first-repair",
                observation=observation,
                metric_id=metric_id,
                basis_score_refs=basis,
                adjudicator=graders[2],
                resolved_result=True,
                rationale="The sealed rubric and correct-answer reference support the resolved result.",
                recorded_at="2026-07-16T11:30:00Z",
                blind_to_arm=blind,
            )
        )
    return {
        "policy": policy,
        "decisions": decisions,
        "tasks": tasks,
        "task_set": task_set,
        "enrollment_manifest": enrollment_manifest,
        "participants": participants,
        "sessions": sessions,
        "observations": observations,
        "graders": graders,
        "scores": scores,
        "adjudications": adjudications,
    }


def _assemble(values: dict, *, limitations: tuple[str, ...] = ()) -> dict:
    return build_operational_outcome_evaluation(
        policy=values["policy"],
        human_decision_records=values["decisions"],
        task_set=values["task_set"],
        enrollment_manifest=values["enrollment_manifest"],
        tasks=values["tasks"],
        participants=values["participants"],
        sessions=values["sessions"],
        observations=values["observations"],
        graders=values["graders"],
        scores=values["scores"],
        adjudications=values["adjudications"],
        limitations=limitations,
    )


class OperationalOutcomeEvaluationTests(unittest.TestCase):
    def assert_contract_error(self, code: str, values: dict) -> None:
        with self.assertRaises(OperationalOutcomeValidationError) as caught:
            _assemble(values)
        self.assertIn(code, caught.exception.codes)

    def test_schema_is_draft_2020_12_valid(self) -> None:
        from semantic_guard import operational_outcomes

        Draft202012Validator.check_schema(
            operational_outcomes._schema_validator().schema
        )

    def test_fixture_replays_but_cannot_establish_operational_effect(self) -> None:
        bundle = _assemble(_components())
        validate_operational_outcome_evaluation(bundle)
        for axis in ("repair_effect", "human_operational_use"):
            result = bundle["axis_results"][axis]
            self.assertEqual(result["status"], "not_established")
            self.assertEqual(result["claim_scope"], "declared_synthetic_protocol_only")
            self.assertIn("declared_synthetic_protocol_only", result["reasons"])

    def test_positive_branch_is_only_a_declared_record_result(self) -> None:
        # These are still artificial unit-test records.  The positive branch
        # deliberately does not claim participant identity, genuine consent,
        # field representativeness, or practical operational effectiveness.
        bundle = _assemble(
            _components(evidence_class="operational_participant")
        )
        for axis in ("repair_effect", "human_operational_use"):
            result = bundle["axis_results"][axis]
            self.assertEqual(result["status"], "meets_policy_for_declared_records")
            self.assertEqual(result["claim_scope"], "declared_records_only")
        self.assertEqual(
            bundle["non_inference_axes"]["field_validity"]["status"],
            "not_evaluated",
        )
        self.assertTrue(
            any(
                "Participant identity, consent authenticity" in limitation
                for limitation in bundle["limitations"]
            )
        )

    def test_axes_remain_separate_and_other_readiness_is_not_evaluated(self) -> None:
        bundle = _assemble(_components())
        self.assertNotEqual(
            bundle["axis_results"]["repair_effect"]["result_digest"],
            bundle["axis_results"]["human_operational_use"]["result_digest"],
        )
        self.assertTrue(
            all(
                item["status"] == "not_evaluated"
                for item in bundle["non_inference_axes"].values()
            )
        )
        self.assertFalse(bundle["authority_boundary"]["final_acceptance"])

    def test_pending_and_retired_policy_cannot_establish(self) -> None:
        for status in ("pending", "retired"):
            with self.subTest(status=status):
                bundle = _assemble(_components(status=status))
                self.assertEqual(
                    bundle["axis_results"]["repair_effect"]["status"],
                    "not_established",
                )
                self.assertIn(
                    "policy_not_adopted",
                    bundle["axis_results"]["repair_effect"]["reasons"],
                )

    def test_policy_must_be_adopted_before_task_set_is_sealed(self) -> None:
        self.assert_contract_error(
            "policy_adopted_after_task_seal",
            _components(decision_at="2026-07-16T09:30:00Z"),
        )

    def test_same_task_set_is_required_in_both_arms(self) -> None:
        values = _components()
        removed = next(
            item
            for item in values["observations"]
            if item["arm"] == "candidate"
        )
        values["observations"].remove(removed)
        values["scores"] = [
            item
            for item in values["scores"]
            if item["observation_id"] != removed["observation_id"]
        ]
        self.assert_contract_error("same_task_arm_coverage_mismatch", values)

    def test_learning_contamination_is_rejected(self) -> None:
        self.assert_contract_error(
            "learning_contamination", _components(learning_contamination=True)
        )

    def test_missing_consent_is_rejected(self) -> None:
        self.assert_contract_error(
            "participant_consent_missing", _components(consent_status="not_obtained")
        )

    def test_author_or_participant_self_scoring_is_rejected(self) -> None:
        self.assert_contract_error(
            "author_or_participant_self_scoring",
            _components(second_relationship="material_author"),
        )

    def test_two_people_in_one_group_are_not_independent(self) -> None:
        self.assert_contract_error(
            "independent_score_groups_insufficient",
            _components(second_group="independent-a"),
        )

    def test_blinding_break_is_rejected(self) -> None:
        self.assert_contract_error("score_blinding_broken", _components(blind=False))

    def test_disagreement_is_preserved_and_requires_adjudication(self) -> None:
        self.assert_contract_error(
            "score_disagreement_unadjudicated",
            _components(disagreement=True, adjudicate=False),
        )
        bundle = _assemble(_components(disagreement=True, adjudicate=True))
        disagreements = bundle["axis_results"]["repair_effect"]["disagreements"]
        self.assertEqual(len(disagreements), 1)
        self.assertEqual(
            disagreements[0]["adjudication_ref"],
            "outcome-adjudication.first-repair",
        )

    def test_self_report_alone_cannot_prove_repair(self) -> None:
        self.assert_contract_error(
            "self_report_only_repair_concealed",
            _components(repair_verification=False),
        )

    def test_finding_suppression_or_rule_weakening_cannot_be_hidden(self) -> None:
        self.assert_contract_error(
            "finding_suppression_concealed", _components(repair_shortcut=True)
        )

    def test_regression_cannot_be_hidden(self) -> None:
        self.assert_contract_error(
            "regression_concealed", _components(regression_status="failed")
        )

    def test_missing_escalation_cannot_be_hidden(self) -> None:
        self.assert_contract_error(
            "escalation_error_concealed", _components(escalation_chosen=False)
        )

    def test_unresolved_obligation_cannot_disappear(self) -> None:
        self.assert_contract_error(
            "unresolved_loss_concealed", _components(unresolved_preserved=False)
        )

    def test_authority_error_cannot_be_hidden(self) -> None:
        self.assert_contract_error(
            "authority_error_concealed", _components(authority_error=True)
        )

    def test_disclosed_authority_error_is_measured_not_deleted(self) -> None:
        values = _components(authority_error=True)
        observation_axes = {
            item["observation_id"]: item["axis"]
            for item in values["observations"]
        }
        for score in values["scores"]:
            axis = observation_axes[score["observation_id"]]
            disclosed_metric = (
                "authority_safe"
                if axis == "human_operational_use"
                else "responsibility_boundary_preserved"
            )
            for criterion in score["criteria"]:
                if criterion["metric_id"] == disclosed_metric:
                    criterion["result"] = False
            _rehash(score, "score_digest")
        bundle = _assemble(values)
        authority_rate = next(
            item
            for item in bundle["axis_results"]["human_operational_use"][
                "arm_metrics"
            ]["candidate"]["metric_rates"]
            if item["metric_id"] == "authority_safe"
        )
        self.assertEqual(authority_rate["error_count"], 1)
        self.assertEqual(authority_rate["error_rate"]["point"], 1.0)

    def test_technical_pass_cannot_be_converted_to_acceptance(self) -> None:
        self.assert_contract_error(
            "technical_pass_acceptance_conversion_concealed",
            _components(technical_pass_accept=True),
        )

    def test_small_perfect_sample_fails_conservative_rate_bounds(self) -> None:
        bundle = _assemble(_components(strict=True))
        assessment = bundle["axis_results"]["repair_effect"][
            "threshold_assessment"
        ]
        self.assertEqual(assessment["status"], "failed")
        error = next(
            item
            for item in assessment["criteria"]
            if item["criterion"] == "error_rate_wilson_upper"
            and item["metric_id"] == "correct_repair"
        )
        rate = bundle["axis_results"]["repair_effect"]["arm_metrics"][
            "candidate"
        ]["metric_rates"][0]["error_rate"]
        self.assertEqual(rate["point"], 0.0)
        self.assertGreater(error["observed"], error["threshold"])
        self.assertEqual(error["basis"], "wilson_upper_bound")

    def test_wilson_interval_is_deterministic_and_not_point_only(self) -> None:
        interval = wilson_interval(0, 2, 0.95)
        self.assertEqual(interval["point"], 0.0)
        self.assertGreater(interval["upper"], 0.0)
        self.assertEqual(interval, wilson_interval(0, 2, 0.95))

    def test_policy_threshold_change_after_binding_is_rejected(self) -> None:
        bundle = _assemble(_components())
        bundle["policy"]["axis_policies"][0]["max_weighted_error_loss"] = 0
        errors = operational_outcome_errors(bundle)
        self.assertIn("policy_digest_mismatch", {item["code"] for item in errors})

    def test_saved_result_and_digest_tampering_are_rejected(self) -> None:
        bundle = _assemble(_components())
        bundle["axis_results"]["repair_effect"]["status"] = (
            "meets_policy_for_declared_records"
        )
        errors = operational_outcome_errors(bundle)
        codes = {item["code"] for item in errors}
        self.assertIn("bundle_digest_mismatch", codes)
        self.assertIn("axis_results_replay_mismatch", codes)

    def test_task_digest_substitution_is_rejected(self) -> None:
        values = _components()
        values["tasks"][0]["correct_answer_ref"] = versioned_ref(
            "answer.substituted", "v1"
        )
        self.assert_contract_error("task_digest_mismatch", values)

    def test_result_uses_wilson_and_hoeffding_not_point_only_cost_claims(self) -> None:
        bundle = _assemble(_components())
        result = bundle["axis_results"]["human_operational_use"]
        weighted = result["arm_metrics"]["candidate"]["weighted_error_loss"]
        self.assertEqual(weighted["basis"], "two_sided_hoeffding_bound")
        criterion = next(
            item
            for item in result["threshold_assessment"]["criteria"]
            if item["criterion"] == "weighted_error_loss_upper"
        )
        self.assertEqual(criterion["basis"], "hoeffding_upper_bound")

    def test_v1_requires_complete_human_only_decision_barrier(self) -> None:
        values = _components()
        values["tasks"][0]["prohibited_decisions"].remove(
            "grant_or_expand_authority"
        )
        _rehash(values["tasks"][0], "task_digest")
        self.assert_contract_error(
            "human_only_decision_barrier_incomplete", values
        )

    def test_repair_axis_authority_violation_cannot_hide(self) -> None:
        values = _components(authority_error=True)
        for observation in values["observations"]:
            if observation["axis"] == "human_operational_use":
                observation["response_projection"]["authority_claims"] = []
                _rehash(observation, "observation_digest")
        _rebind_scores(values)
        self.assert_contract_error("authority_error_concealed", values)

    def test_policy_and_task_arm_identity_is_closed(self) -> None:
        values = _components()
        values["policy"]["arm_contract"]["candidate"] = deepcopy(
            values["policy"]["arm_contract"]["baseline"]
        )
        _rehash(values["policy"], "policy_digest")
        self.assert_contract_error("policy_arms_not_distinct", values)

        values = _components()
        values["policy"]["arm_contract"]["candidate"]["digest"] = deepcopy(
            values["policy"]["arm_contract"]["baseline"]["digest"]
        )
        _rehash(values["policy"], "policy_digest")
        self.assert_contract_error("policy_arms_not_distinct", values)

        values = _components()
        task = values["tasks"][0]
        task["arm_materials"]["candidate"]["material_ref"] = deepcopy(
            task["arm_materials"]["baseline"]["material_ref"]
        )
        _rehash(task, "task_digest")
        self.assert_contract_error("task_arm_materials_not_distinct", values)

        values = _components()
        task = values["tasks"][0]
        task["arm_materials"]["candidate"]["derived_from_arm_ref"] = deepcopy(
            values["policy"]["arm_contract"]["baseline"]
        )
        _rehash(task, "task_digest")
        self.assert_contract_error("task_arm_derivation_mismatch", values)

    def test_policy_adoption_is_strictly_before_task_seal(self) -> None:
        self.assert_contract_error(
            "policy_adopted_after_task_seal",
            _components(decision_at=SEALED_AT),
        )

    def test_task_set_binds_exact_adoption_decision_digest(self) -> None:
        bundle = _assemble(_components())
        bundle["task_set"]["adoption_decision_ref"]["decision_digest"] = (
            digest_value({"substituted": True})
        )
        _rehash(bundle["task_set"], "task_set_digest")
        codes = {item["code"] for item in operational_outcome_errors(bundle)}
        self.assertIn("task_set_adoption_decision_mismatch", codes)

    def test_completed_participant_cannot_disappear_from_denominator(self) -> None:
        values = _components()
        values["participants"].append(
            build_participant(
                participant_id="participant-pseudo.unobserved-candidate",
                role_id="role.coding-agent",
                population_id="population.declared-agent-and-human-work",
                assigned_arm="candidate",
                cluster_id="cluster.unobserved-candidate",
                source_kind="local_fixture",
                consent_status="obtained",
                consent_evidence_ref=digest_ref("consent.unobserved"),
                consent_scope_ref=versioned_ref(
                    "consent-scope.outcome-evaluation", "v1"
                ),
                consent_recorded_at="2026-07-16T07:30:00Z",
                enrolled_at="2026-07-16T09:15:00Z",
                disposition_recorded_at=SESSION_END,
            )
        )
        self.assert_contract_error(
            "completed_participant_evidence_incomplete", values
        )

    def test_noncompleted_participant_remains_in_dropout_denominator(self) -> None:
        values = _components()
        values["participants"].append(
            build_participant(
                participant_id="participant-pseudo.missing-candidate",
                role_id="role.coding-agent",
                population_id="population.declared-agent-and-human-work",
                assigned_arm="candidate",
                cluster_id="cluster.missing-candidate",
                source_kind="local_fixture",
                consent_status="obtained",
                consent_evidence_ref=digest_ref("consent.missing"),
                consent_scope_ref=versioned_ref(
                    "consent-scope.outcome-evaluation", "v1"
                ),
                consent_recorded_at="2026-07-16T07:30:00Z",
                enrolled_at="2026-07-16T09:15:00Z",
                disposition_status="missing",
                disposition_reason="no_completed_session",
                disposition_recorded_at=SESSION_END,
            )
        )
        values["enrollment_manifest"] = build_enrollment_manifest(
            manifest_id=values["enrollment_manifest"]["manifest_id"],
            policy=values["policy"],
            task_set_digest=values["task_set"]["task_set_digest"],
            sealed_at=values["enrollment_manifest"]["sealed_at"],
            participants=values["participants"],
        )
        bundle = _assemble(values)
        enrollment = bundle["axis_results"]["repair_effect"]["arm_metrics"][
            "candidate"
        ]["enrollment"]
        self.assertEqual(enrollment["enrolled_participant_count"], 2)
        self.assertEqual(enrollment["completed_participant_count"], 1)
        self.assertEqual(enrollment["dropout_count"], 1)

    def test_dropout_threshold_is_enforced_independently_for_each_arm(self) -> None:
        values = _components(
            evidence_class="operational_participant",
            max_dropout_rate=0.9,
        )
        values["participants"].append(
            build_participant(
                participant_id="participant-pseudo.missing-baseline",
                role_id="role.coding-agent",
                population_id="population.declared-agent-and-human-work",
                assigned_arm="baseline",
                cluster_id="cluster.missing-baseline",
                source_kind="operational_participant",
                consent_status="obtained",
                consent_evidence_ref=digest_ref("consent.missing-baseline"),
                consent_scope_ref=versioned_ref(
                    "consent-scope.outcome-evaluation", "v1"
                ),
                consent_recorded_at="2026-07-16T07:30:00Z",
                enrolled_at="2026-07-16T09:15:00Z",
                disposition_status="missing",
                disposition_reason="no_completed_session",
                disposition_recorded_at=SESSION_END,
            )
        )
        values["enrollment_manifest"] = build_enrollment_manifest(
            manifest_id=values["enrollment_manifest"]["manifest_id"],
            policy=values["policy"],
            task_set_digest=values["task_set"]["task_set_digest"],
            sealed_at=values["enrollment_manifest"]["sealed_at"],
            participants=values["participants"],
        )

        result = _assemble(values)["axis_results"]["repair_effect"]
        criteria = {
            item["criterion"]: item
            for item in result["threshold_assessment"]["criteria"]
            if item["criterion"].endswith("dropout_rate_wilson_upper")
        }
        self.assertEqual(result["status"], "not_established")
        self.assertIn("conservative_thresholds_not_met", result["reasons"])
        self.assertFalse(
            criteria["baseline_dropout_rate_wilson_upper"]["passed"]
        )
        self.assertGreater(
            criteria["baseline_dropout_rate_wilson_upper"]["observed"], 0.9
        )
        self.assertTrue(
            criteria["candidate_dropout_rate_wilson_upper"]["passed"]
        )
        self.assertLess(
            criteria["candidate_dropout_rate_wilson_upper"]["observed"], 0.9
        )

    def test_consent_withdrawal_is_retained_without_observation(self) -> None:
        values = _components()
        values["participants"].append(
            build_participant(
                participant_id="participant-pseudo.withdrawn-candidate",
                role_id="role.coding-agent",
                population_id="population.declared-agent-and-human-work",
                assigned_arm="candidate",
                cluster_id="cluster.withdrawn-candidate",
                source_kind="local_fixture",
                consent_status="withdrawn",
                consent_evidence_ref=digest_ref("consent.withdrawn"),
                consent_scope_ref=versioned_ref(
                    "consent-scope.outcome-evaluation", "v1"
                ),
                consent_recorded_at="2026-07-16T07:30:00Z",
                enrolled_at="2026-07-16T09:15:00Z",
                disposition_status="withdrawn",
                disposition_reason="participant_withdrew",
                disposition_evidence_ref=digest_ref("withdrawal.notice"),
                disposition_recorded_at=SESSION_END,
            )
        )
        values["enrollment_manifest"] = build_enrollment_manifest(
            manifest_id=values["enrollment_manifest"]["manifest_id"],
            policy=values["policy"],
            task_set_digest=values["task_set"]["task_set_digest"],
            sealed_at=values["enrollment_manifest"]["sealed_at"],
            participants=values["participants"],
        )
        bundle = _assemble(values)
        dispositions = {
            item["status"]: item["count"]
            for item in bundle["axis_results"]["repair_effect"]["arm_metrics"][
                "candidate"
            ]["enrollment"]["disposition_counts"]
        }
        self.assertEqual(dispositions["withdrawn"], 1)

    def test_distinct_participant_and_cluster_minima_are_not_observation_counts(self) -> None:
        bundle = _assemble(_components(minimum_participants=2))
        result = bundle["axis_results"]["repair_effect"]
        self.assertEqual(result["arm_metrics"]["candidate"]["observation_count"], 2)
        self.assertEqual(result["arm_metrics"]["candidate"]["participant_count"], 1)
        self.assertEqual(result["arm_metrics"]["candidate"]["cluster_count"], 1)
        self.assertIn("minimum_participant_sample_not_met", result["reasons"])
        self.assertIn("independent_cluster_sample_not_met", result["reasons"])

    def test_dependent_cluster_cannot_cross_arms(self) -> None:
        values = _components()
        baseline = next(
            item
            for item in values["participants"]
            if item["assigned_arm"] == "baseline"
            and item["role_id"] == "role.coding-agent"
        )
        candidate = next(
            item
            for item in values["participants"]
            if item["assigned_arm"] == "candidate"
            and item["role_id"] == "role.coding-agent"
        )
        candidate["cluster_id"] = baseline["cluster_id"]
        _rehash(candidate, "participant_digest")
        self.assert_contract_error("cross_arm_cluster_reuse", values)

    def test_adjudication_axis_time_and_identity_blindness_are_closed(self) -> None:
        values = _components(disagreement=True, adjudicate=True)
        values["adjudications"][0]["metric_id"] = "authority_safe"
        _rehash(values["adjudications"][0], "adjudication_digest")
        self.assert_contract_error("adjudication_metric_axis_mismatch", values)

        values = _components(disagreement=True, adjudicate=True)
        values["adjudications"][0]["recorded_at"] = "2026-07-16T06:00:00Z"
        _rehash(values["adjudications"][0], "adjudication_digest")
        self.assert_contract_error("adjudication_before_basis_scores", values)

        values = _components(disagreement=True, adjudicate=True)
        adjudicator = next(
            item for item in values["graders"] if item["role"] == "adjudicator"
        )
        adjudicator["blind_to_participant_identity"] = False
        _rehash(adjudicator, "grader_digest")
        values["adjudications"][0]["adjudicator_digest"] = deepcopy(
            adjudicator["grader_digest"]
        )
        _rehash(values["adjudications"][0], "adjudication_digest")
        self.assert_contract_error("adjudication_blinding_broken", values)

    def test_mandatory_limitations_cannot_be_replaced(self) -> None:
        bundle = _assemble(
            _components(), limitations=("Caller supplement only.",)
        )
        self.assertIn("Caller supplement only.", bundle["limitations"])
        self.assertTrue(
            any(
                "Participant identity, consent authenticity" in item
                for item in bundle["limitations"]
            )
        )

    def test_non_finite_numbers_fail_closed(self) -> None:
        values = _components()
        values["observations"][0]["effort"]["elapsed_seconds"] = float("nan")
        _rehash(values["observations"][0], "observation_digest")
        _rebind_scores(values)
        self.assert_contract_error("non_finite_number", values)

    def test_schema_declares_resource_caps(self) -> None:
        from semantic_guard import operational_outcomes

        schema = operational_outcomes._schema_validator().schema
        self.assertEqual(schema["properties"]["tasks"]["maxItems"], 256)
        self.assertEqual(schema["properties"]["observations"]["maxItems"], 65536)
        self.assertEqual(schema["$defs"]["nonEmptyString"]["maxLength"], 4096)
        self.assertEqual(schema["$defs"]["policy"]["properties"]["roles"]["maxItems"], 256)
        self.assertEqual(schema["$defs"]["policy"]["properties"]["task_strata"]["maxItems"], 256)
        self.assertEqual(schema["$defs"]["humanDecision"]["properties"]["recorded_at"]["maxLength"], 64)
        self.assertEqual(schema["$defs"]["adjudication"]["properties"]["basis_score_refs"]["maxItems"], 128)

    def test_consent_and_enrollment_seal_must_precede_session(self) -> None:
        values = _components()
        participant = values["participants"][0]
        participant["consent"]["recorded_at"] = SESSION_START
        _rebind_participant_graph(values, participant["participant_id"])
        self.assert_contract_error("consent_recorded_after_session_start", values)

        values = _components()
        values["enrollment_manifest"] = build_enrollment_manifest(
            manifest_id=values["enrollment_manifest"]["manifest_id"],
            policy=values["policy"],
            task_set_digest=values["task_set"]["task_set_digest"],
            sealed_at=SESSION_START,
            participants=values["participants"],
        )
        self.assert_contract_error("session_before_enrollment_seal", values)

    def test_task_set_seal_must_precede_enrollment_seal(self) -> None:
        values = _components()
        values["enrollment_manifest"] = build_enrollment_manifest(
            manifest_id=values["enrollment_manifest"]["manifest_id"],
            policy=values["policy"],
            task_set_digest=values["task_set"]["task_set_digest"],
            sealed_at=SEALED_AT,
            participants=values["participants"],
        )
        self.assert_contract_error("enrollment_sealed_before_task_set", values)

    def test_non_json_and_non_finite_decimal_numbers_fail_closed(self) -> None:
        for value, code in (
            (Decimal("NaN"), "non_finite_number"),
            (Decimal("1"), "unsupported_number_type"),
            (True, "schema_validation_failed"),
        ):
            with self.subTest(value=value, code=code):
                values = _components()
                values["observations"][0]["effort"]["elapsed_seconds"] = value
                self.assert_contract_error(code, values)

    def test_unknown_wide_container_fails_before_schema_copy(self) -> None:
        bundle = _assemble(_components())
        bundle["unknown_wide_container"] = [None] * 262145
        codes = {item["code"] for item in operational_outcome_errors(bundle)}
        self.assertIn("input_container_width_exceeded", codes)

    def test_every_declared_policy_role_requires_task_coverage(self) -> None:
        values = _components(
            extra_roles=(
                {
                    "role_id": "role.unobserved-operator",
                    "actor_class": "operator",
                    "description": "A declared role with no task cell.",
                },
            )
        )
        self.assert_contract_error("policy_role_task_coverage_missing", values)

    def test_chosen_escalation_cannot_route_to_no_action(self) -> None:
        values = _components()
        for observation in values["observations"]:
            observation["response_projection"]["routing_destination"] = "no_action"
            _rehash(observation, "observation_digest")
        _rebind_scores(values)
        self.assert_contract_error("escalation_destination_missing", values)

    def test_repair_artifact_cannot_serve_as_its_own_verification(self) -> None:
        values = _components()
        for observation in values["observations"]:
            if observation["axis"] != "repair_effect":
                continue
            observation["repair_verification_refs"] = [
                deepcopy(observation["repair_artifact_ref"])
            ]
            _rehash(observation, "observation_digest")
        _rebind_scores(values)
        self.assert_contract_error(
            "repair_verification_not_independent_reference", values
        )

    def test_elapsed_seconds_must_equal_observation_interval(self) -> None:
        values = _components()
        for observation in values["observations"]:
            observation["effort"]["elapsed_seconds"] = 0
            _rehash(observation, "observation_digest")
        _rebind_scores(values)
        self.assert_contract_error("elapsed_seconds_interval_mismatch", values)

    def test_missing_axis_fails_closed_before_result_arithmetic(self) -> None:
        values = _components()
        values["tasks"] = [
            item for item in values["tasks"] if item["axis"] == "repair_effect"
        ]
        removed_observation_ids = {
            item["observation_id"]
            for item in values["observations"]
            if item["axis"] == "human_operational_use"
        }
        values["observations"] = [
            item
            for item in values["observations"]
            if item["observation_id"] not in removed_observation_ids
        ]
        values["scores"] = [
            item
            for item in values["scores"]
            if item["observation_id"] not in removed_observation_ids
        ]
        self.assert_contract_error("axis_task_coverage_missing", values)

    def test_later_retirement_supersedes_adoption(self) -> None:
        values = _components(evidence_class="operational_participant")
        values["decisions"].append(
            build_human_policy_decision(
                decision_id="human-decision.outcome-policy-v1-retired",
                decision_type="retire_policy",
                human_actor_ref="human.evaluation-owner",
                policy=values["policy"],
                rationale="The exact adopted policy was subsequently retired.",
                evidence_refs=[digest_ref("evidence.retirement-minutes")],
                recorded_at="2026-07-16T12:00:00Z",
            )
        )
        self.assert_contract_error("policy_decision_superseded", values)

    def test_same_time_policy_decisions_fail_closed(self) -> None:
        values = _components(evidence_class="operational_participant")
        values["decisions"].append(
            build_human_policy_decision(
                decision_id="human-decision.outcome-policy-v1-conflict",
                decision_type="retire_policy",
                human_actor_ref="human.evaluation-owner",
                policy=values["policy"],
                rationale="Conflicting decision at the adoption timestamp.",
                evidence_refs=[digest_ref("evidence.conflicting-minutes")],
                recorded_at=values["decisions"][0]["recorded_at"],
            )
        )
        self.assert_contract_error("policy_decision_conflict", values)

    def test_deep_unknown_object_fails_closed_without_recursion(self) -> None:
        bundle = _assemble(_components())
        nested: dict = {}
        cursor = nested
        for _ in range(1200):
            child: dict = {}
            cursor["next"] = child
            cursor = child
        bundle["unknown_deep_object"] = nested
        codes = {item["code"] for item in operational_outcome_errors(bundle)}
        self.assertIn("input_structure_depth_exceeded", codes)


if __name__ == "__main__":
    unittest.main()
