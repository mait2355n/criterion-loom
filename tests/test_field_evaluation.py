from __future__ import annotations

from copy import deepcopy
import unittest

from semantic_guard.field_evaluation import (
    ROUTES,
    FieldEvaluationValidationError,
    build_adjudication,
    build_blind_label,
    build_evaluation_policy,
    build_field_case,
    build_field_evaluation,
    build_human_policy_decision,
    digest_value,
    field_evaluation_errors,
    validate_field_evaluation,
    versioned_ref,
    wilson_interval,
)


SEALED_AT = "2026-07-16T09:00:00Z"
PREDICTED_AT = "2026-07-16T11:00:00Z"
LABELS_RELEASED_AT = "2026-07-16T12:00:00Z"
LABEL_RECORDED_AT = "2026-07-16T10:00:00Z"

TRUTH = {
    "field-case.01": "satisfied",
    "field-case.02": "refuted",
    "field-case.03": "satisfied",
    "field-case.04": "refuted",
    "field-case.05": "satisfied",
    "field-case.06": "refuted",
}

PREDICTIONS = {
    "direct_only": {
        "field-case.01": "abstain",
        "field-case.02": "satisfied",
        "field-case.03": "satisfied",
        "field-case.04": "abstain",
        "field-case.05": "refuted",
        "field-case.06": "refuted",
    },
    "morphology": {
        "field-case.01": "satisfied",
        "field-case.02": "abstain",
        "field-case.03": "satisfied",
        "field-case.04": "abstain",
        "field-case.05": "refuted",
        "field-case.06": "refuted",
    },
    "dependency": {
        "field-case.01": "satisfied",
        "field-case.02": "refuted",
        "field-case.03": "satisfied",
        "field-case.04": "abstain",
        "field-case.05": "satisfied",
        "field-case.06": "refuted",
    },
    "llm": dict(TRUTH),
}


def _reviewers(*, independent: bool = True) -> list[dict]:
    second_group = "independent-b" if independent else "independent-a"
    return [
        {
            "reviewer_id": "reviewer.a",
            "reviewer_kind": "human",
            "role": "label_reviewer",
            "independence_group": "independent-a",
            "relationship_to_system": "independent",
            "blind_to_route_outputs": True,
            "blind_to_other_labels": True,
            "conflict_statement": "No implementation or evaluation ownership.",
        },
        {
            "reviewer_id": "reviewer.b",
            "reviewer_kind": "human",
            "role": "label_reviewer",
            "independence_group": second_group,
            "relationship_to_system": "independent",
            "blind_to_route_outputs": True,
            "blind_to_other_labels": True,
            "conflict_statement": "No implementation or evaluation ownership.",
        },
        {
            "reviewer_id": "reviewer.adjudicator",
            "reviewer_kind": "human",
            "role": "adjudicator",
            "independence_group": "independent-adjudication",
            "relationship_to_system": "independent",
            "blind_to_route_outputs": True,
            "blind_to_other_labels": False,
            "conflict_statement": "Independent adjudicator; labels are revealed only for adjudication.",
        },
    ]


def _policy(
    *,
    status: str = "adopted",
    evidence_class: str = "field_evaluation",
    minimum_overall: int = 6,
    thresholds: dict[str, float] | None = None,
) -> dict:
    decision_ref = "human-decision.field-policy-v1" if status != "pending" else None
    return build_evaluation_policy(
        policy_id="field-policy.functional-relations",
        version="v1",
        status=status,
        decision_record_ref=decision_ref,
        target_population={
            "population_id": "population.requirement-statements",
            "description": "Requirement statements sampled from the declared operational intake.",
            "intended_use_id": "use.audit-functional-relations",
            "intended_use": "Audit whether required functional relations are explicitly recoverable.",
            "unit_of_analysis": "one immutable requirement statement",
            "sampling_frame": "the declared production intake ledger during the evaluation window",
            "inclusion_criteria": ["Statement is within the declared audit profile."],
            "exclusion_criteria": ["Statement is a duplicate or outside the evaluation window."],
        },
        stratification=[
            {
                "dimension_id": "risk",
                "required": True,
                "strata": [
                    {
                        "stratum_id": "risk.high",
                        "label": "high",
                        "definition": "A false satisfaction can authorize a high-impact action.",
                    },
                    {
                        "stratum_id": "risk.normal",
                        "label": "normal",
                        "definition": "The declared use has ordinary impact.",
                    },
                ],
            }
        ],
        cost_model={
            "false_satisfaction_cost": 100,
            "false_refutation_cost": 10,
            "abstention_cost": 2,
            "catastrophic_false_satisfaction": True,
            "currency_or_unit": "human-adopted relative harm units",
            "rationale": "A false claim of satisfaction destroys the value of later passage decisions.",
        },
        thresholds=thresholds
        or {
            "max_false_satisfaction_rate": 0.57,
            "max_false_refutation_rate": 0.57,
            "max_abstention_rate": 0.4,
            "min_coverage": 0.6,
            "max_cost_weighted_loss": 0,
        },
        minimum_sample={
            "overall": minimum_overall,
            "reference_satisfied": 3,
            "reference_refuted": 3,
            "per_required_stratum": 3,
        },
        confidence_level=0.95,
        primary_metric="cost_weighted_loss",
        candidate_route="llm",
        evidence_class=evidence_class,
        review_triggers=[
            "population change",
            "route or rule version change",
            "threshold or cost change",
        ],
    )


def _cases(*, source_kind: str = "field_sample") -> list[dict]:
    values = []
    for index, case_id in enumerate(TRUTH, start=1):
        stratum = "risk.high" if index <= 3 else "risk.normal"
        values.append(
            build_field_case(
                case_id=case_id,
                subject_ref=f"artifact://requirement/{index}",
                subject_digest=digest_value({"immutable requirement": index}),
                population_id="population.requirement-statements",
                intended_use_id="use.audit-functional-relations",
                stratum_refs=[stratum],
                source_kind=source_kind,
            )
        )
    return values


def _run_specs(predictions: dict[str, dict[str, str]] | None = None) -> list[dict]:
    values = predictions or PREDICTIONS
    return [
        {
            "run_id": f"field-run.{route.replace('_', '-')}.v1",
            "route": route,
            "route_config": versioned_ref(f"route.{route}", "v1"),
            "predictions_recorded_at": PREDICTED_AT,
            "label_access_prohibited": True,
            "training_case_refs": [],
            "case_results": [
                {
                    "case_id": case_id,
                    "prediction": values[route][case_id],
                    "reason_codes": [f"fixture.{route}"],
                }
                for case_id in TRUTH
            ],
        }
        for route in ROUTES
    ]


def _bundle(
    *,
    policy: dict | None = None,
    reviewers: list[dict] | None = None,
    source_kind: str = "field_sample",
    predictions: dict[str, dict[str, str]] | None = None,
    disagree: bool = False,
    policy_decision_recorded_at: str = "2026-07-15T10:00:00Z",
) -> dict:
    policy_value = deepcopy(policy or _policy())
    decisions = []
    if policy_value["status"] != "pending":
        decisions = [
            build_human_policy_decision(
                decision_id=policy_value["decision_record_ref"],
                decision_type=(
                    "adopt_policy"
                    if policy_value["status"] == "adopted"
                    else "retire_policy"
                ),
                human_actor_ref="human.evaluation-owner",
                policy=policy_value,
                rationale="External human adoption of declared costs, thresholds, and use.",
                evidence_refs=["evidence.human-review-minutes"],
                recorded_at=policy_decision_recorded_at,
            )
        ]
    case_values = _cases(source_kind=source_kind)
    guide = versioned_ref(
        "label-guide.functional-relations",
        "v1",
        {"guide": "Independent binary functional-relation labeling guide v1."},
    )
    labels = []
    for case in case_values:
        case_id = case["case_id"]
        labels.append(
            build_blind_label(
                label_id=f"label.a.{case_id.rsplit('.', 1)[1]}",
                case=case,
                reviewer_id="reviewer.a",
                reference_label=TRUTH[case_id],
                label_guide=guide,
                recorded_at=LABEL_RECORDED_AT,
            )
        )
        second_label = TRUTH[case_id]
        if disagree and case_id == "field-case.01":
            second_label = "refuted"
        labels.append(
            build_blind_label(
                label_id=f"label.b.{case_id.rsplit('.', 1)[1]}",
                case=case,
                reviewer_id="reviewer.b",
                reference_label=second_label,
                label_guide=guide,
                recorded_at=LABEL_RECORDED_AT,
            )
        )
    adjudications = []
    if disagree:
        case = case_values[0]
        adjudications.append(
            build_adjudication(
                adjudication_id="adjudication.field-case-01",
                case=case,
                adjudicator_id="reviewer.adjudicator",
                basis_label_refs=["label.a.01", "label.b.01"],
                final_label=TRUTH[case["case_id"]],
                label_guide=guide,
                recorded_at="2026-07-16T14:00:00Z",
            )
        )
    return build_field_evaluation(
        evaluation_id="field-evaluation.functional-relations.v1",
        policy=policy_value,
        human_decision_records=decisions,
        label_guide=guide,
        reviewers=reviewers or _reviewers(),
        cases=case_values,
        labels=labels,
        adjudications=adjudications,
        holdout_id="holdout.functional-relations.v1",
        sealed_at=SEALED_AT,
        labels_released_at=LABELS_RELEASED_AT,
        run_specs=_run_specs(predictions),
    )


def _codes(bundle: dict) -> set[str]:
    return {item["code"] for item in field_evaluation_errors(bundle)}


class FieldEvaluationTests(unittest.TestCase):
    def test_adopted_field_bundle_establishes_only_declared_population(self) -> None:
        bundle = _bundle()
        self.assertEqual(validate_field_evaluation(bundle), bundle)
        self.assertEqual(
            bundle["field_validity"]["status"],
            "established_for_declared_population",
        )
        self.assertEqual(bundle["field_validity"]["reasons"], [])
        self.assertEqual(
            set(bundle["outcome_axes"]),
            {"repair_effect", "human_operational_use", "operational_qualification"},
        )
        self.assertEqual(
            {axis["status"] for axis in bundle["outcome_axes"].values()},
            {"not_evaluated"},
        )
        self.assertEqual(bundle["authority_boundary"]["cost_owner"], "human")
        self.assertEqual(
            bundle["authority_boundary"]["cutover_owner"],
            "external_human_or_control_plane",
        )

    def test_same_case_route_metrics_and_incremental_value_are_deterministic(self) -> None:
        left = _bundle()
        right = _bundle()
        self.assertEqual(left, right)
        metrics = {item["route"]: item for item in left["metrics"]["route_metrics"]}
        self.assertEqual(metrics["direct_only"]["counts"]["false_satisfaction"], 1)
        self.assertEqual(metrics["direct_only"]["counts"]["false_refutation"], 1)
        self.assertEqual(metrics["direct_only"]["counts"]["abstain"], 2)
        self.assertEqual(metrics["direct_only"]["cost_weighted_loss"], 19)
        self.assertEqual(metrics["llm"]["counts"]["correct"], 6)
        self.assertEqual(metrics["llm"]["cost_weighted_loss"], 0)
        increments = left["metrics"]["incremental_values"]
        self.assertEqual(
            [(item["baseline_route"], item["target_route"]) for item in increments],
            [
                ("direct_only", "morphology"),
                ("morphology", "dependency"),
                ("dependency", "llm"),
            ],
        )
        self.assertEqual(increments[0]["loss_reduction"], 16.666666666667)
        self.assertEqual(increments[0]["resolved_abstentions"], 1)
        self.assertEqual(increments[2]["coverage_delta"], 0.166666666667)
        self.assertEqual(
            metrics["direct_only"]["rates"]["false_satisfaction"]["wilson_interval"],
            wilson_interval(1, 3, 0.95),
        )
        criteria = {
            item["metric"]: item
            for item in left["metrics"]["threshold_assessment"]["criteria"]
        }
        self.assertEqual(
            criteria["false_satisfaction_rate"]["comparison_basis"],
            "wilson_upper",
        )
        self.assertEqual(criteria["coverage"]["comparison_basis"], "wilson_lower")
        self.assertEqual(
            criteria["cost_weighted_loss"]["comparison_basis"],
            "point_estimate",
        )

    def test_point_estimate_cannot_pass_when_conservative_bound_fails(self) -> None:
        policy = _policy(
            thresholds={
                "max_false_satisfaction_rate": 0.3,
                "max_false_refutation_rate": 1,
                "max_abstention_rate": 1,
                "min_coverage": 0,
                "max_cost_weighted_loss": 1,
            }
        )
        bundle = _bundle(policy=policy)
        criterion = next(
            item
            for item in bundle["metrics"]["threshold_assessment"]["criteria"]
            if item["metric"] == "false_satisfaction_rate"
        )
        self.assertEqual(criterion["point_estimate"], 0)
        self.assertGreater(criterion["comparison_value"], 0.3)
        self.assertFalse(criterion["passed"])
        self.assertEqual(bundle["field_validity"]["status"], "not_established")

    def test_valid_disagreement_requires_and_accepts_independent_adjudication(self) -> None:
        bundle = _bundle(disagree=True)
        self.assertEqual(validate_field_evaluation(bundle), bundle)
        self.assertEqual(len(bundle["adjudications"]), 1)
        self.assertEqual(bundle["field_validity"]["status"], "established_for_declared_population")

    def test_pending_policy_is_validly_recorded_but_cannot_establish_validity(self) -> None:
        bundle = _bundle(policy=_policy(status="pending"))
        self.assertEqual(validate_field_evaluation(bundle), bundle)
        self.assertEqual(bundle["field_validity"]["status"], "not_established")
        self.assertIn("policy_not_adopted", bundle["field_validity"]["reasons"])

    def test_retired_policy_is_bound_to_human_retirement_but_not_valid(self) -> None:
        bundle = _bundle(policy=_policy(status="retired"))
        self.assertEqual(validate_field_evaluation(bundle), bundle)
        self.assertEqual(bundle["human_decision_records"][0]["decision"], "retire")
        self.assertEqual(bundle["field_validity"]["status"], "not_established")
        self.assertIn("policy_not_adopted", bundle["field_validity"]["reasons"])

    def test_reviewer_independence_shortfall_is_not_established(self) -> None:
        bundle = _bundle(reviewers=_reviewers(independent=False))
        self.assertEqual(validate_field_evaluation(bundle), bundle)
        self.assertEqual(bundle["field_validity"]["status"], "not_established")
        self.assertIn(
            "reviewer_independence_insufficient",
            bundle["field_validity"]["reasons"],
        )

    def test_each_case_must_actually_use_two_independent_groups(self) -> None:
        reviewers = _reviewers()
        reviewers[1]["relationship_to_system"] = "developer"
        reviewers.append(
            {
                "reviewer_id": "reviewer.unused-independent",
                "reviewer_kind": "human",
                "role": "label_reviewer",
                "independence_group": "independent-unused",
                "relationship_to_system": "independent",
                "blind_to_route_outputs": True,
                "blind_to_other_labels": True,
                "conflict_statement": "Independent, but assigned no cases in this run.",
            }
        )
        bundle = _bundle(reviewers=reviewers)
        self.assertEqual(validate_field_evaluation(bundle), bundle)
        self.assertEqual(bundle["field_validity"]["status"], "not_established")
        self.assertIn(
            "case_reviewer_independence_insufficient",
            bundle["field_validity"]["reasons"],
        )

    def test_blindness_shortfall_is_not_established(self) -> None:
        reviewers = _reviewers()
        reviewers[0]["blind_to_other_labels"] = False
        bundle = _bundle(reviewers=reviewers)
        self.assertEqual(validate_field_evaluation(bundle), bundle)
        self.assertEqual(bundle["field_validity"]["status"], "not_established")
        self.assertIn("blindness_not_established", bundle["field_validity"]["reasons"])

    def test_sample_shortfall_is_not_established(self) -> None:
        bundle = _bundle(policy=_policy(minimum_overall=7))
        self.assertEqual(validate_field_evaluation(bundle), bundle)
        self.assertEqual(bundle["field_validity"]["status"], "not_established")
        self.assertIn("sample_size_insufficient", bundle["field_validity"]["reasons"])

    def test_threshold_failure_is_not_established(self) -> None:
        changed = deepcopy(PREDICTIONS)
        changed["llm"]["field-case.01"] = "abstain"
        bundle = _bundle(predictions=changed)
        self.assertEqual(validate_field_evaluation(bundle), bundle)
        self.assertEqual(bundle["metrics"]["threshold_assessment"]["status"], "failed")
        self.assertIn("thresholds_not_met", bundle["field_validity"]["reasons"])

    def test_fixture_or_smoke_evidence_cannot_be_generalized(self) -> None:
        bundle = _bundle(
            policy=_policy(evidence_class="local_fixture"),
            source_kind="local_fixture",
        )
        self.assertEqual(validate_field_evaluation(bundle), bundle)
        self.assertEqual(bundle["field_validity"]["status"], "not_established")
        self.assertIn(
            "non_field_evidence_cannot_establish_validity",
            bundle["field_validity"]["reasons"],
        )

    def test_missing_or_substituted_case_is_rejected(self) -> None:
        missing = _bundle()
        llm = next(item for item in missing["runs"] if item["route"] == "llm")
        llm["case_results"].pop()
        self.assertIn("run_case_population_mismatch", _codes(missing))

        substituted = _bundle()
        substituted["cases"][0]["subject_digest"] = digest_value({"substituted": True})
        self.assertIn("case_digest_mismatch", _codes(substituted))

    def test_missing_population_label_and_route_run_are_rejected(self) -> None:
        population = _bundle()
        del population["policy"]["target_population"]["description"]
        self.assertIn("schema_validation_failed", _codes(population))

        label = _bundle()
        label["labels"] = [
            item for item in label["labels"] if item["label_id"] != "label.a.01"
        ]
        self.assertIn("case_label_count_insufficient", _codes(label))

        run = _bundle()
        run["runs"] = [item for item in run["runs"] if item["route"] != "llm"]
        self.assertIn("schema_validation_failed", _codes(run))

    def test_population_label_and_run_substitution_are_rejected(self) -> None:
        population = _bundle()
        population["policy"]["target_population"]["description"] = "substituted population"
        self.assertIn("population_digest_mismatch", _codes(population))

        label = _bundle()
        label["labels"][0]["reference_label"] = "refuted"
        label_codes = _codes(label)
        self.assertIn("label_digest_mismatch", label_codes)
        self.assertIn("adjudication_missing", label_codes)

        run = _bundle()
        run["runs"][0]["case_results"][0]["prediction"] = "refuted"
        run_codes = _codes(run)
        self.assertIn("run_digest_mismatch", run_codes)
        self.assertIn("metrics_replay_mismatch", run_codes)

    def test_duplicate_case_label_and_run_are_rejected(self) -> None:
        case = _bundle()
        case["cases"].append(deepcopy(case["cases"][0]))
        self.assertIn("duplicate_case", _codes(case))

        label = _bundle()
        label["labels"].append(deepcopy(label["labels"][0]))
        self.assertIn("duplicate_label", _codes(label))

        run = _bundle()
        run["runs"].append(deepcopy(run["runs"][0]))
        run_codes = _codes(run)
        self.assertIn("duplicate_run", run_codes)
        self.assertIn("duplicate_route_run", run_codes)

    def test_holdout_training_label_access_and_release_contamination_are_rejected(self) -> None:
        training = _bundle()
        training["runs"][0]["training_case_refs"] = ["field-case.01"]
        self.assertIn("holdout_training_contamination", _codes(training))

        access = _bundle()
        access["runs"][0]["label_access_prohibited"] = False
        self.assertIn("holdout_label_access_violation", _codes(access))

        released = _bundle()
        released["runs"][0]["predictions_recorded_at"] = LABELS_RELEASED_AT
        self.assertIn("holdout_prediction_after_label_release", _codes(released))

        before_seal = _bundle()
        before_seal["runs"][0]["predictions_recorded_at"] = "2026-07-16T08:59:59Z"
        self.assertIn("holdout_prediction_before_seal", _codes(before_seal))

        late_label = _bundle()
        late_label["labels"][0]["recorded_at"] = "2026-07-16T12:00:01Z"
        self.assertIn("holdout_label_time_invalid", _codes(late_label))

    def test_policy_must_be_adopted_before_holdout_is_sealed(self) -> None:
        bundle = _bundle(policy_decision_recorded_at="2026-07-16T09:00:01Z")
        self.assertEqual(bundle["field_validity"]["status"], "not_established")
        self.assertIn(
            "policy_not_frozen_before_holdout",
            bundle["field_validity"]["reasons"],
        )
        self.assertIn("policy_adoption_after_holdout_seal", _codes(bundle))

    def test_missing_adjudication_is_rejected(self) -> None:
        bundle = _bundle()
        second = next(item for item in bundle["labels"] if item["label_id"] == "label.b.01")
        second["reference_label"] = "refuted"
        self.assertIn("adjudication_missing", _codes(bundle))

    def test_cost_threshold_and_policy_decision_changes_are_rejected(self) -> None:
        cost = _bundle()
        cost["policy"]["cost_model"]["false_satisfaction_cost"] = 50
        self.assertIn("policy_digest_mismatch", _codes(cost))

        invalid_order = _bundle()
        invalid_order["policy"]["cost_model"]["false_satisfaction_cost"] = 5
        self.assertIn("catastrophic_cost_order_invalid", _codes(invalid_order))

        threshold = _bundle()
        threshold["policy"]["thresholds"]["min_coverage"] = 0.9
        self.assertIn("policy_digest_mismatch", _codes(threshold))

        decision = _bundle()
        decision["human_decision_records"] = []
        decision_codes = _codes(decision)
        self.assertIn("policy_human_decision_missing_or_mismatched", decision_codes)

    def test_llm_cannot_use_a_different_case_set(self) -> None:
        bundle = _bundle()
        llm = next(item for item in bundle["runs"] if item["route"] == "llm")
        llm["case_results"][-1] = deepcopy(llm["case_results"][0])
        codes = _codes(bundle)
        self.assertIn("duplicate_run_case", codes)
        self.assertIn("run_case_population_mismatch", codes)

    def test_false_established_status_cannot_be_written_over_recomputation(self) -> None:
        bundle = _bundle(policy=_policy(status="pending"))
        bundle["field_validity"]["status"] = "established_for_declared_population"
        bundle["field_validity"]["reasons"] = []
        codes = _codes(bundle)
        self.assertIn("field_validity_replay_mismatch", codes)

    def test_validation_exception_exposes_stable_error_codes(self) -> None:
        bundle = _bundle()
        bundle["runs"][0]["label_access_prohibited"] = False
        with self.assertRaises(FieldEvaluationValidationError) as caught:
            validate_field_evaluation(bundle)
        self.assertIn("holdout_label_access_violation", caught.exception.codes)


if __name__ == "__main__":
    unittest.main()
