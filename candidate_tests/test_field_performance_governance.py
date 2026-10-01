from __future__ import annotations

from copy import deepcopy
import unittest

from semantic_guard_vnext.field_performance_governance import (
    METRIC_NAMES,
    FieldPerformanceGovernanceError,
    build_access_record,
    build_field_performance_bundle,
    build_performance_case,
    build_performance_policy,
    digest_ref,
    digest_value,
    validate_field_performance,
    versioned_ref,
)


def _population() -> dict:
    material = {
        "population_id": "population.requirements.jp",
        "description": "Japanese field requirement records in the declared use.",
        "sampling_frame": "Sealed operational sample registry.",
        "unit_of_analysis": "One requirement record and its governed audit result.",
        "inclusion_criteria": ["field source", "declared intended use"],
        "exclusion_criteria": ["training fixture", "smoke-only record"],
    }
    return {**material, "population_digest": digest_value(material)}


def _risk(*, adopted: bool = False) -> dict:
    return {
        "risk_class_id": "risk.high",
        "description": "A false pass can invalidate downstream assurance.",
        "costs": {
            "false_pass_cost": 100,
            "false_nonconformance_cost": 10,
            "unresolved_cost": 4,
            "abstention_cost": 3,
            "authority_violation_cost": 20,
            "traceability_loss_cost": 15,
        },
        "thresholds": {
            metric: (
                0.01 if adopted and metric != "coverage" else 0.8 if adopted else None
            )
            for metric in METRIC_NAMES
        },
        "rationale": "False passage receives the greatest declared cost.",
    }


def _policy(*, adopted: bool = False, reported_status: str | None = None) -> dict:
    policy_status = reported_status or ("adoption_claimed" if adopted else "pending")
    thresholds_adopted = policy_status == "adoption_claimed"
    return build_performance_policy(
        policy_id="field-performance-policy.requirements",
        version="v1",
        reported_status=policy_status,
        threshold_decision_ref=(
            "human-decision.thresholds.v1" if thresholds_adopted else None
        ),
        target_population=_population(),
        risk_classes=[_risk(adopted=thresholds_adopted)],
        confidence_level=0.95,
        minimum_overall_sample=4,
        minimum_per_risk_class=4,
        review_period_days=90,
        reevaluation_triggers=[
            "route implementation changed",
            "population changed",
            "temporal degradation observed",
        ],
    )


def _case(
    number: int,
    *,
    cohort: str,
    reference: str,
    observed: str,
    authority: str = "within_authority",
    traceability: str = "complete",
) -> dict:
    return build_performance_case(
        case_id=f"field-case.{number:02d}",
        subject_ref=f"requirement.{number:02d}",
        subject_digest=digest_value({"requirement": number}),
        risk_class_id="risk.high",
        cohort_id=cohort,
        source_class="field_sample",
        reference_outcome=reference,
        observed_disposition=observed,
        authority_status=authority,
        traceability_status=traceability,
        evidence_refs=[f"evidence.case.{number:02d}"],
    )


def _cohort(cohort_id: str, start: str, end: str, case_refs: list[str]) -> dict:
    material = {
        "cohort_id": cohort_id,
        "observed_from": start,
        "observed_until": end,
        "case_refs": sorted(case_refs),
    }
    return {**material, "cohort_digest": digest_value(material)}


def _bundle(
    *,
    adopted: bool = False,
    leaked: bool = False,
    access_coverage: str = "claimed_complete",
) -> dict:
    policy = _policy(adopted=adopted)
    decision_material = {
        "decision_id": "human-decision.thresholds.v1",
        "decision_type": "adopt_thresholds",
        "issuer_kind": "human",
        "human_actor_ref": "human.performance-owner",
        "trusted_entry_ref": "decision-entry.external.v1",
        "authenticity_evidence_ref": "auth-evidence.external.v1",
        "policy_id": policy["policy_id"],
        "policy_version": policy["version"],
        "policy_digest": deepcopy(policy["policy_digest"]),
        "rationale": "Externally supplied fixture; this test does not prove a human act.",
        "recorded_at": "2026-06-01T00:00:00Z",
    }
    decisions = (
        [{**decision_material, "decision_digest": digest_value(decision_material)}]
        if adopted
        else []
    )
    cases = [
        _case(1, cohort="cohort.early", reference="satisfied", observed="pass"),
        _case(2, cohort="cohort.early", reference="nonconforming", observed="pass"),
        _case(
            3,
            cohort="cohort.late",
            reference="satisfied",
            observed="nonconformance",
            authority="violation",
        ),
        _case(
            4,
            cohort="cohort.late",
            reference="unresolved",
            observed="unresolved",
            traceability="partial",
        ),
    ]
    cohorts = [
        _cohort(
            "cohort.early",
            "2026-01-01T00:00:00Z",
            "2026-02-01T00:00:00Z",
            ["field-case.01", "field-case.02"],
        ),
        _cohort(
            "cohort.late",
            "2026-02-01T00:00:00Z",
            "2026-03-01T00:00:00Z",
            ["field-case.03", "field-case.04"],
        ),
    ]
    access_records = [
        build_access_record(
            access_id="access.custody.01",
            actor_ref="custodian.01",
            actor_role="data_custodian",
            material_ref="holdout.bundle",
            material_partition="holdout",
            material_kind="subject",
            purpose="custody",
            accessed_at="2026-03-10T00:00:00Z",
            authorized=True,
        )
    ]
    if leaked:
        access_records.append(
            build_access_record(
                access_id="access.leak.01",
                actor_ref="developer.01",
                actor_role="model_or_rule_developer",
                material_ref="label.field-case.02",
                material_partition="holdout",
                material_kind="reference_label",
                purpose="tuning",
                accessed_at="2026-03-02T00:00:00Z",
                authorized=False,
            )
        )
    return build_field_performance_bundle(
        evaluation_id="field-performance-evaluation.v1",
        policy=policy,
        human_decision_records=decisions,
        base_field_evaluation_ref=versioned_ref(
            "field-evaluation.base", "field-evaluation/v0"
        ),
        route_implementation_ref=versioned_ref(
            "semantic-guard-route", "implementation.v1"
        ),
        tuning_refs=[digest_ref("tuning-case.01")],
        holdout_refs=[
            {"ref_id": case["case_id"], "digest": deepcopy(case["subject_digest"])}
            for case in cases
        ],
        holdout_sealed_at="2026-03-01T00:00:00Z",
        predictions_sealed_at="2026-03-05T00:00:00Z",
        labels_released_at="2026-03-06T00:00:00Z",
        access_log_coverage=access_coverage,
        access_records=access_records,
        cohorts=cohorts,
        cases=cases,
        evaluation_as_of="2026-03-10T00:00:00Z",
        review_due_at="2026-06-08T00:00:00Z",
    )


def _rebuild(bundle: dict, **overrides) -> dict:
    partition = bundle["dataset_partition"]
    values = {
        "evaluation_id": bundle["evaluation_id"],
        "policy": bundle["policy"],
        "human_decision_records": bundle["human_decision_records"],
        "base_field_evaluation_ref": bundle["base_field_evaluation_ref"],
        "route_implementation_ref": bundle["route_implementation_ref"],
        "tuning_refs": partition["tuning_refs"],
        "holdout_refs": partition["holdout_refs"],
        "holdout_sealed_at": partition["holdout_sealed_at"],
        "predictions_sealed_at": partition["predictions_sealed_at"],
        "labels_released_at": partition["labels_released_at"],
        "access_log_coverage": partition["access_log_coverage"],
        "access_records": bundle["access_records"],
        "cohorts": bundle["cohorts"],
        "cases": bundle["cases"],
        "evaluation_as_of": bundle["evaluation_as_of"],
        "review_due_at": bundle["review_due_at"],
    }
    values.update(overrides)
    return build_field_performance_bundle(**values)


class FieldPerformanceGovernanceTests(unittest.TestCase):
    def test_pending_thresholds_compute_all_metrics_without_qualification(self) -> None:
        bundle = validate_field_performance(_bundle())
        rates = bundle["metrics"]["overall"]["rates"]
        self.assertEqual(set(rates), set(METRIC_NAMES))
        self.assertEqual(rates["false_pass_rate"]["value"], 0.5)
        self.assertEqual(rates["false_nonconformance_rate"]["value"], 0.5)
        self.assertEqual(rates["unresolved_rate"]["value"], 0.25)
        self.assertEqual(rates["abstention_rate"]["value"], 0.0)
        self.assertEqual(rates["coverage"]["value"], 1.0)
        self.assertEqual(rates["authority_violation_rate"]["value"], 0.25)
        self.assertEqual(rates["traceability_loss_rate"]["value"], 0.25)
        self.assertEqual(bundle["assessment"]["formal_authority"], "none")
        self.assertIn(
            "thresholds_pending_human_decision",
            bundle["assessment"]["reasons"],
        )

    def test_assurance_state_axes_are_separate_and_fail_closed(self) -> None:
        assessment = validate_field_performance(_bundle())["assessment"]
        self.assertEqual(assessment["calculation_replay_state"], "replayed")
        self.assertEqual(
            assessment["input_resolution_state"],
            "unresolved_external_bindings",
        )
        self.assertEqual(assessment["evidence_sufficiency_state"], "insufficient")
        self.assertEqual(
            assessment["currency_state"],
            "review_schedule_bound_runtime_clock_unresolved",
        )
        self.assertEqual(
            assessment["threshold_adoption_state"], "pending_human_decision"
        )
        self.assertEqual(assessment["qualification_state"], "not_established")
        self.assertEqual(assessment["formal_authority"], "none")
        self.assertEqual(
            assessment["reasons"],
            [item["unresolved_id"] for item in assessment["unresolved_records"]],
        )

    def test_unresolved_records_are_typed_and_closable(self) -> None:
        records = validate_field_performance(_bundle())["assessment"][
            "unresolved_records"
        ]
        required = {
            "owner",
            "next_action",
            "resolution_condition",
            "review_at",
            "fallback",
            "retirement_condition",
            "evidence_refs",
        }
        self.assertTrue(records)
        self.assertTrue(all(required <= set(item) for item in records))
        self.assertTrue(
            all(
                item["blocking_status"] == "blocking_field_qualification"
                for item in records
            )
        )

    def test_candidate_metric_definitions_cover_all_seven_metrics(self) -> None:
        bundle = validate_field_performance(_bundle())
        profile = bundle["metric_definition_profile"]
        self.assertEqual(profile["profile_version"], "candidate.v1")
        self.assertEqual(profile["adoption_status"], "candidate")
        self.assertEqual(profile["formal_authority"], "none")
        self.assertEqual(
            {item["metric"] for item in profile["definitions"]},
            set(METRIC_NAMES),
        )
        false_pass = next(
            item
            for item in profile["definitions"]
            if item["metric"] == "false_pass_rate"
        )
        self.assertIn("unsafe to pass", false_pass["reference_unresolved_treatment"])
        coverage = next(
            item for item in profile["definitions"] if item["metric"] == "coverage"
        )
        self.assertIn("does not imply", coverage["observed_unresolved_treatment"])

    def test_temporal_assessment_covers_all_metrics_by_risk_and_triggers_recheck(
        self,
    ) -> None:
        bundle = validate_field_performance(_bundle())
        temporal = bundle["metrics"]["temporal_assessment"]
        self.assertEqual(temporal["status"], "assessed")
        self.assertEqual(len(temporal["comparisons"]), len(METRIC_NAMES))
        self.assertEqual(
            {item["metric"] for item in temporal["comparisons"]},
            set(METRIC_NAMES),
        )
        self.assertEqual(
            {item["risk_class_id"] for item in temporal["comparisons"]},
            {"risk.high"},
        )
        self.assertTrue(temporal["directional_degradation_observed"])
        self.assertTrue(temporal["reevaluation_required"])
        self.assertIn(
            "temporal_degradation_observed",
            bundle["assessment"]["reasons"],
        )
        degraded_metrics = {
            item["metric"]
            for item in temporal["comparisons"]
            if item["degradation_observed"]
        }
        self.assertEqual(
            degraded_metrics,
            {
                "false_nonconformance_rate",
                "unresolved_rate",
                "authority_violation_rate",
                "traceability_loss_rate",
            },
        )

    def test_holdout_leakage_is_visible_and_blocks_assessment(self) -> None:
        bundle = validate_field_performance(_bundle(leaked=True))
        self.assertEqual(bundle["dataset_diagnostics"]["leakage_status"], "detected")
        self.assertEqual(
            bundle["dataset_diagnostics"]["leaked_access_refs"],
            ["access.leak.01"],
        )
        self.assertIn("holdout_leakage_detected", bundle["assessment"]["reasons"])

    def test_partial_access_log_cannot_claim_no_leakage(self) -> None:
        bundle = validate_field_performance(_bundle(access_coverage="partial"))
        self.assertEqual(bundle["dataset_diagnostics"]["leakage_status"], "unknown")
        self.assertIn(
            "access_log_coverage_not_complete",
            bundle["assessment"]["reasons"],
        )

    def test_tuning_holdout_overlap_is_rejected(self) -> None:
        bundle = _bundle()
        bundle["dataset_partition"]["tuning_refs"][0] = deepcopy(
            bundle["dataset_partition"]["holdout_refs"][0]
        )
        bundle["dataset_partition"]["partition_digest"] = digest_value(
            {
                key: deepcopy(value)
                for key, value in bundle["dataset_partition"].items()
                if key != "partition_digest"
            }
        )
        bundle["bundle_digest"] = digest_value(
            {
                key: deepcopy(value)
                for key, value in bundle.items()
                if key != "bundle_digest"
            }
        )
        with self.assertRaises(FieldPerformanceGovernanceError) as caught:
            validate_field_performance(bundle)
        self.assertIn("tuning_holdout_overlap", caught.exception.codes)

    def test_same_holdout_content_under_an_alias_is_rejected(self) -> None:
        bundle = _bundle()
        aliased_tuning = [
            {
                "ref_id": "tuning-case.alias",
                "digest": deepcopy(
                    bundle["dataset_partition"]["holdout_refs"][0]["digest"]
                ),
            }
        ]

        with self.assertRaises(FieldPerformanceGovernanceError) as caught:
            validate_field_performance(_rebuild(bundle, tuning_refs=aliased_tuning))
        self.assertIn("tuning_holdout_overlap", caught.exception.codes)

    def test_one_subject_snapshot_cannot_inflate_the_sample(self) -> None:
        bundle = _bundle()
        first, second = bundle["cases"][:2]
        second["subject_ref"] = first["subject_ref"]
        second["subject_digest"] = deepcopy(first["subject_digest"])
        second["case_digest"] = digest_value(
            {
                key: deepcopy(value)
                for key, value in second.items()
                if key != "case_digest"
            }
        )
        holdout = deepcopy(bundle["dataset_partition"]["holdout_refs"])
        for reference in holdout:
            if reference["ref_id"] == second["case_id"]:
                reference["digest"] = deepcopy(second["subject_digest"])

        with self.assertRaises(FieldPerformanceGovernanceError) as caught:
            validate_field_performance(_rebuild(bundle, holdout_refs=holdout))
        self.assertIn("duplicate_sampling_unit", caught.exception.codes)

    def test_empty_access_records_cannot_claim_complete_coverage(self) -> None:
        bundle = _bundle()
        with self.assertRaises(FieldPerformanceGovernanceError) as caught:
            validate_field_performance(_rebuild(bundle, access_records=[]))
        self.assertIn("schema_error", caught.exception.codes)

    def test_no_observed_leakage_is_not_absence_proof(self) -> None:
        bundle = validate_field_performance(_bundle())
        self.assertEqual(
            bundle["dataset_diagnostics"]["leakage_status"],
            "not_observed_in_supplied_records",
        )
        self.assertIn(
            "access_log_completeness_externally_unverified",
            bundle["assessment"]["reasons"],
        )

    def test_evaluation_cannot_complete_before_label_release(self) -> None:
        bundle = _bundle()
        with self.assertRaises(FieldPerformanceGovernanceError) as caught:
            validate_field_performance(
                _rebuild(bundle, evaluation_as_of="2026-03-05T12:00:00Z")
            )
        self.assertIn("evaluation_before_label_release", caught.exception.codes)

    def test_required_limitations_cannot_be_resealed_away(self) -> None:
        bundle = _bundle()
        bundle["limitations"] = ["all good"]
        bundle["bundle_digest"] = digest_value(
            {
                key: deepcopy(value)
                for key, value in bundle.items()
                if key != "bundle_digest"
            }
        )
        with self.assertRaises(FieldPerformanceGovernanceError) as caught:
            validate_field_performance(bundle)
        self.assertIn("required_limitation_missing", caught.exception.codes)

    def test_own_route_result_recording_is_not_label_leakage(self) -> None:
        bundle = _bundle()
        access = [
            *bundle["access_records"],
            build_access_record(
                access_id="access.route-output.01",
                actor_ref="runtime.01",
                actor_role="evaluation_runtime",
                material_ref="route-output.01",
                material_partition="holdout",
                material_kind="route_result",
                purpose="evaluation",
                accessed_at="2026-03-04T00:00:00Z",
                authorized=True,
            ),
        ]
        rebuilt = validate_field_performance(_rebuild(bundle, access_records=access))
        self.assertEqual(
            rebuilt["dataset_diagnostics"]["leakage_status"],
            "not_observed_in_supplied_records",
        )

    def test_metric_tampering_is_rejected_even_with_resealed_bundle(self) -> None:
        bundle = _bundle()
        bundle["metrics"]["overall"]["rates"]["coverage"]["value"] = 0.5
        bundle["metrics"]["metrics_digest"] = digest_value(
            {
                key: deepcopy(value)
                for key, value in bundle["metrics"].items()
                if key != "metrics_digest"
            }
        )
        bundle["bundle_digest"] = digest_value(
            {
                key: deepcopy(value)
                for key, value in bundle.items()
                if key != "bundle_digest"
            }
        )
        with self.assertRaises(FieldPerformanceGovernanceError) as caught:
            validate_field_performance(bundle)
        self.assertIn("metrics_replay_mismatch", caught.exception.codes)

    def test_false_pass_must_be_most_costly(self) -> None:
        bundle = _bundle()
        bundle["policy"]["risk_classes"][0]["costs"]["false_pass_cost"] = 10
        bundle["policy"]["policy_digest"] = digest_value(
            {
                key: deepcopy(value)
                for key, value in bundle["policy"].items()
                if key != "policy_digest"
            }
        )
        bundle["bundle_digest"] = digest_value(
            {
                key: deepcopy(value)
                for key, value in bundle.items()
                if key != "bundle_digest"
            }
        )
        with self.assertRaises(FieldPerformanceGovernanceError) as caught:
            validate_field_performance(bundle)
        self.assertIn("false_pass_not_most_costly", caught.exception.codes)

    def test_adoption_claim_shape_still_has_no_formal_authority(self) -> None:
        bundle = validate_field_performance(_bundle(adopted=True))
        self.assertEqual(bundle["assessment"]["formal_authority"], "none")
        self.assertIn(
            "claimed_threshold_outside_bound", bundle["assessment"]["reasons"]
        )
        self.assertEqual(bundle["policy"]["reported_status"], "adoption_claimed")
        self.assertNotIn("status", bundle["policy"])
        self.assertTrue(
            all("passed" not in item for item in bundle["metrics"]["threshold_results"])
        )
        self.assertNotIn(
            "threshold_decision_missing_or_mismatched",
            bundle["assessment"]["reasons"],
        )
        self.assertIn(
            "threshold_decision_external_authenticity_unverified",
            bundle["assessment"]["reasons"],
        )
        self.assertIn(
            "threshold_decision_evaluation_binding_unverified",
            bundle["assessment"]["reasons"],
        )

    def test_structural_evaluation_binding_remains_non_authoritative(self) -> None:
        bundle = _bundle(adopted=True)
        decision = deepcopy(bundle["human_decision_records"][0])
        decision["evaluation_binding"] = {
            "evaluation_id": bundle["evaluation_id"],
            "evaluation_material_digest": deepcopy(
                bundle["evaluation_material_digest"]
            ),
            "metric_definition_profile_ref": deepcopy(
                bundle["policy"]["metric_definition_profile_ref"]
            ),
            "route_implementation_ref": deepcopy(bundle["route_implementation_ref"]),
            "evaluation_completed_at": bundle["evaluation_as_of"],
        }
        decision["decision_digest"] = digest_value(
            {
                key: deepcopy(value)
                for key, value in decision.items()
                if key != "decision_digest"
            }
        )
        rebuilt = validate_field_performance(
            _rebuild(bundle, human_decision_records=[decision])
        )
        self.assertNotIn(
            "threshold_decision_evaluation_binding_unverified",
            rebuilt["assessment"]["reasons"],
        )
        self.assertIn(
            "threshold_decision_external_authenticity_unverified",
            rebuilt["assessment"]["reasons"],
        )
        self.assertEqual(rebuilt["assessment"]["formal_authority"], "none")

    def test_retired_policy_is_not_reported_as_pending_adoption(self) -> None:
        bundle = _bundle()
        rebuilt = validate_field_performance(
            _rebuild(bundle, policy=_policy(reported_status="retired"))
        )
        self.assertEqual(
            rebuilt["assessment"]["threshold_adoption_state"],
            "claimed_retired_unverified",
        )
        self.assertIn(
            "threshold_policy_retired_claim_unverified",
            rebuilt["assessment"]["reasons"],
        )
        self.assertNotIn(
            "thresholds_pending_human_decision",
            rebuilt["assessment"]["reasons"],
        )

    def test_review_due_must_follow_policy_period(self) -> None:
        bundle = _bundle()
        with self.assertRaises(FieldPerformanceGovernanceError) as caught:
            validate_field_performance(
                _rebuild(bundle, review_due_at="2026-06-09T00:00:00Z")
            )
        self.assertIn("review_due_policy_mismatch", caught.exception.codes)

    def test_non_finite_numbers_are_rejected_before_digest_replay(self) -> None:
        for invalid in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(invalid=invalid):
                bundle = _bundle()
                bundle["policy"]["confidence_level"] = invalid
                with self.assertRaises(FieldPerformanceGovernanceError) as caught:
                    validate_field_performance(bundle)
                self.assertIn("non_finite_number", caught.exception.codes)

    def test_unknown_authority_and_partial_trace_count_against_rates(self) -> None:
        bundle = _bundle()
        first = bundle["cases"][0]
        first["authority_status"] = "unknown"
        first["traceability_status"] = "unknown"
        first["case_digest"] = digest_value(
            {
                key: deepcopy(value)
                for key, value in first.items()
                if key != "case_digest"
            }
        )
        for ref in bundle["dataset_partition"]["holdout_refs"]:
            if ref["ref_id"] == first["case_id"]:
                ref["digest"] = deepcopy(first["subject_digest"])
        bundle["dataset_partition"]["partition_digest"] = digest_value(
            {
                key: deepcopy(value)
                for key, value in bundle["dataset_partition"].items()
                if key != "partition_digest"
            }
        )
        rebuilt = _rebuild(bundle)
        rates = validate_field_performance(rebuilt)["metrics"]["overall"]["rates"]
        self.assertEqual(rates["authority_violation_rate"]["value"], 0.5)
        self.assertEqual(rates["traceability_loss_rate"]["value"], 0.5)


if __name__ == "__main__":
    unittest.main()
