from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

from semantic_guard.field_evaluation import (
    ROUTES,
    build_blind_label,
    build_evaluation_policy,
    build_field_evaluation,
    build_human_policy_decision,
    digest_value,
    versioned_ref,
)
from semantic_guard.field_sample_intake import (
    REQUIRED_DUPLICATE_METHODS,
    REQUIRED_EXPOSURE_CONTEXTS,
    FieldSampleIntakeValidationError,
    build_duplicate_cluster,
    build_evaluation_permission,
    build_exposure_declaration,
    build_field_sample_intake,
    build_function_unit_assessment,
    build_intake_candidate,
    build_privacy_review,
    field_sample_intake_errors,
    field_sample_intake_evaluation_errors,
    project_holdout_field_cases,
    validate_field_sample_intake,
    validate_field_sample_intake_evaluation,
)


POLICY_DECIDED_AT = "2026-08-27T23:00:00Z"
COLLECTION_OPENED_AT = "2026-08-28T00:00:00Z"
COLLECTION_CLOSED_AT = "2026-08-28T03:00:00Z"
DUPLICATE_REVIEWED_AT = "2026-08-28T04:00:00Z"
ASSIGNED_AT = "2026-08-28T05:00:00Z"
ASSIGNMENT_FROZEN_AT = "2026-08-28T06:00:00Z"
HOLDOUT_SEALED_AT = "2026-08-28T07:00:00Z"
LABEL_RECORDED_AT = "2026-08-28T08:00:00Z"
PREDICTED_AT = "2026-08-28T08:30:00Z"
LABELS_RELEASED_AT = "2026-08-28T09:00:00Z"


def _policy(*, status: str = "adopted") -> dict:
    return build_evaluation_policy(
        policy_id="field-policy.single-function-operational-requests",
        version="v1",
        status=status,
        decision_record_ref=(
            "human-decision.single-function-policy-v1"
            if status != "pending"
            else None
        ),
        target_population={
            "population_id": "population.single-function-operational-requests",
            "description": "Prospectively received operational requests with one functional outcome.",
            "intended_use_id": "use.audit-functional-relations",
            "intended_use": "Compare bounded requirement-relation audit routes.",
            "unit_of_analysis": "One human-confirmed single-function request.",
            "sampling_frame": "Consecutive eligible requests in the declared collection window.",
            "inclusion_criteria": ["newly acquired", "single functional outcome"],
            "exclusion_criteria": ["known development exposure", "permission absent"],
        },
        stratification=[
            {
                "dimension_id": "risk",
                "required": True,
                "strata": [
                    {"stratum_id": "risk.normal", "label": "normal", "definition": "ordinary consequence"},
                    {"stratum_id": "risk.high", "label": "high", "definition": "high consequence"},
                ],
            }
        ],
        cost_model={
            "false_satisfaction_cost": 10,
            "false_refutation_cost": 2,
            "abstention_cost": 1,
            "catastrophic_false_satisfaction": True,
            "currency_or_unit": "human-adopted relative harm units",
            "rationale": "False satisfaction has the highest declared consequence.",
        },
        thresholds={
            "max_false_satisfaction_rate": 1,
            "max_false_refutation_rate": 1,
            "max_abstention_rate": 1,
            "min_coverage": 0,
            "max_cost_weighted_loss": 10,
        },
        minimum_sample={
            "overall": 2,
            "reference_satisfied": 1,
            "reference_refuted": 1,
            "per_required_stratum": 1,
        },
        confidence_level=0.95,
        primary_metric="cost_weighted_loss",
        candidate_route="llm",
        evidence_class="field_evaluation",
        review_triggers=["population change", "route change"],
    )


def _decision(policy: dict, *, recorded_at: str = POLICY_DECIDED_AT) -> dict | None:
    if policy["status"] == "pending":
        return None
    return build_human_policy_decision(
        decision_id=policy["decision_record_ref"],
        decision_type=(
            "adopt_policy" if policy["status"] == "adopted" else "retire_policy"
        ),
        human_actor_ref="human.evaluation-owner",
        policy=policy,
        rationale="Human adoption of the declared population, costs, and thresholds.",
        evidence_refs=["record.evaluation-policy-review"],
        recorded_at=recorded_at,
    )


def _normalization_profile() -> dict:
    return versioned_ref(
        "normalization.requirement-text",
        "v1",
        {"operations": ["utf8", "unicode-nfc", "lf-line-endings"]},
    )


def _assignment_protocol() -> dict:
    return versioned_ref(
        "assignment.semantic-cluster",
        "v1",
        {"unit": "closed semantic duplicate cluster", "splits": ["calibration", "holdout", "excluded"]},
    )


def _collection(*, acquisition_mode: str = "prospective_consecutive") -> dict:
    return {
        "collection_id": "collection.single-function-requests.2026-08",
        "source_register_ref": versioned_ref(
            "register.private-operational-requests",
            "snapshot-v1",
            {"entry_digests": ["external-private-register-snapshot"]},
        ),
        "acquisition_mode": acquisition_mode,
        "opened_at": COLLECTION_OPENED_AT,
        "closed_at": COLLECTION_CLOSED_AT,
        "assignment_frozen_at": ASSIGNMENT_FROZEN_AT,
    }


def _comparison_scope() -> dict:
    return {
        role: versioned_ref(
            f"registry.{role.replace('_', '-')}",
            "snapshot-v1",
            {"entries": [], "role": role},
        )
        for role in (
            "calibration_corpus",
            "test_fixtures",
            "documentation_examples",
            "prior_intakes",
            "rule_and_route_design",
        )
    }


def _precomputed_digest(text: str) -> dict[str, str]:
    return {"algorithm": "sha256", "value": hashlib.sha256(text.encode("utf-8")).hexdigest()}


def _candidate(
    index: int,
    *,
    original_text: str | None = None,
    normalized_text: str | None = None,
    evaluation_text: str | None = None,
    acquired_at: str | None = None,
    permission_status: str = "granted",
    allowed_uses: tuple[str, ...] = (
        "calibration",
        "holdout_evaluation",
        "derived_metrics",
    ),
    permission_valid_through: str | None = None,
    privacy_status: str = "approved",
    unit_status: str = "single_function",
    exposure_status: str = "no_known_exposure",
    checked_contexts: set[str] | None = None,
    exposure_records: list[dict] | None = None,
    derived_from_refs: tuple[str, ...] = (),
    source_occurrence_id: str | None = None,
    stratum_refs: tuple[str, ...] | None = None,
    record_times: dict[str, str] | None = None,
) -> dict:
    original = original_text or f"raw requirement {index}"
    normalized = normalized_text or f"normalized requirement {index}"
    evaluated = evaluation_text or f"redacted requirement {index}"
    acquired = acquired_at or f"2026-08-28T0{index}:00:00Z"
    times = record_times or {}
    evaluation_digest = _precomputed_digest(evaluated)
    permission = build_evaluation_permission(
        status=permission_status,
        owner_ref=f"owner.project-{index}",
        allowed_uses=allowed_uses,
        decision_record_ref=(f"permission.project-{index}" if permission_status != "unknown" else None),
        recorded_at=(
            times.get("permission", acquired)
            if permission_status != "unknown"
            else None
        ),
        valid_through=permission_valid_through,
    )
    privacy = build_privacy_review(
        classification="internal",
        handling="redacted",
        release_status=privacy_status,
        reviewer_ref="privacy.reviewer",
        decision_record_ref=(f"privacy.project-{index}" if privacy_status != "pending" else None),
        recorded_at=(
            times.get("privacy_review", acquired)
            if privacy_status != "pending"
            else None
        ),
        approved_subject_digest=(evaluation_digest if privacy_status == "approved" else None),
    )
    unit = build_function_unit_assessment(
        status=unit_status,
        assessor_ref="reviewer.functional-unit",
        assessment_record_ref=f"unit-assessment.project-{index}",
        recorded_at=times.get("unit_assessment", acquired),
    )
    records = exposure_records or []
    exposure = build_exposure_declaration(
        status=exposure_status,
        checked_contexts=(
            REQUIRED_EXPOSURE_CONTEXTS
            if checked_contexts is None
            else checked_contexts
        ),
        records=records,
        declared_by="reviewer.exposure-register",
        recorded_at=times.get("exposure_declaration", acquired),
    )
    return build_intake_candidate(
        candidate_id=f"field-candidate.{index:02d}",
        field_case_id=f"field-case.{index:02d}",
        subject_ref=f"private-artifact.requirement-{index}",
        source_occurrence_id=source_occurrence_id or f"source-occurrence.requirement-{index}",
        origin_ref=f"project.operational-source-{index}",
        source_revision="revision.1",
        source_kind="operational_request",
        acquired_at=acquired,
        collector_ref="collector.field-intake",
        original_digest=_precomputed_digest(original),
        normalized_digest=_precomputed_digest(normalized),
        evaluation_subject_digest=evaluation_digest,
        normalization_profile=_normalization_profile(),
        population_id="population.single-function-operational-requests",
        intended_use_id="use.audit-functional-relations",
        stratum_refs=(
            stratum_refs
            if stratum_refs is not None
            else ("risk.normal" if index == 1 else "risk.high",)
        ),
        derived_from_refs=derived_from_refs,
        permission=permission,
        privacy_review=privacy,
        unit_assessment=unit,
        exposure_declaration=exposure,
    )


def _cluster(
    index: int,
    *,
    members: tuple[str, ...] | None = None,
    representative: str | None = None,
    split: str = "holdout",
    assigned_at: str = ASSIGNED_AT,
) -> dict:
    member_values = members or (f"field-candidate.{index:02d}",)
    return build_duplicate_cluster(
        cluster_id=f"duplicate-cluster.{index:02d}",
        member_refs=member_values,
        representative_ref=representative or member_values[0],
        assigned_split=split,
        assignment_protocol=_assignment_protocol(),
        assignment_record_ref=f"assignment.cluster-{index}",
        assigned_at=assigned_at,
    )


def _intake(
    *,
    policy: dict | None = None,
    decision: dict | None | object = ...,
    collection: dict | None = None,
    candidates: list[dict] | None = None,
    clusters: list[dict] | None = None,
    review_status: str = "complete",
    review_methods: set[str] | None = None,
) -> dict:
    policy_value = policy or _policy()
    decision_value = _decision(policy_value) if decision is ... else decision
    candidate_values = candidates or [_candidate(1), _candidate(2)]
    cluster_values = clusters or [_cluster(1), _cluster(2)]
    return build_field_sample_intake(
        intake_id="field-intake.single-function-requests.v1",
        policy=policy_value,
        human_policy_decision=decision_value,
        collection=collection or _collection(),
        normalization_profile=_normalization_profile(),
        assignment_protocol=_assignment_protocol(),
        candidates=candidate_values,
        duplicate_clusters=cluster_values,
        duplicate_review_spec={
            "review_id": "duplicate-review.single-function-requests.v1",
            "status": review_status,
            "reviewer_ref": "reviewer.semantic-duplicates",
            "review_record_ref": "record.semantic-duplicate-review",
            "methods": review_methods if review_methods is not None else REQUIRED_DUPLICATE_METHODS,
            "comparison_scope": _comparison_scope(),
            "completed_at": DUPLICATE_REVIEWED_AT,
        },
    )


def _codes(bundle: dict) -> set[str]:
    return {item["code"] for item in field_sample_intake_errors(bundle)}


def _reviewers() -> list[dict]:
    return [
        {
            "reviewer_id": f"reviewer.{suffix}",
            "reviewer_kind": "human",
            "role": "label_reviewer",
            "independence_group": f"independent-{suffix}",
            "relationship_to_system": "independent",
            "blind_to_route_outputs": True,
            "blind_to_other_labels": True,
            "conflict_statement": "No known relationship to the evaluated implementation.",
        }
        for suffix in ("a", "b")
    ]


def _evaluation(policy: dict, cases: list[dict]) -> dict:
    guide = versioned_ref(
        "label-guide.functional-relations",
        "v1",
        {"guide": "Independent binary functional-relation labeling guide."},
    )
    truth = {cases[0]["case_id"]: "satisfied", cases[1]["case_id"]: "refuted"}
    labels = [
        build_blind_label(
            label_id=f"label.{reviewer[-1]}.{case['case_id'].rsplit('.', 1)[1]}",
            case=case,
            reviewer_id=reviewer,
            reference_label=truth[case["case_id"]],
            label_guide=guide,
            recorded_at=LABEL_RECORDED_AT,
        )
        for case in cases
        for reviewer in ("reviewer.a", "reviewer.b")
    ]
    run_specs = [
        {
            "run_id": f"field-run.{route.replace('_', '-')}.v1",
            "route": route,
            "route_config": versioned_ref(f"route.{route}", "v1"),
            "predictions_recorded_at": PREDICTED_AT,
            "label_access_prohibited": True,
            "training_case_refs": [],
            "case_results": [
                {"case_id": case["case_id"], "prediction": truth[case["case_id"]], "reason_codes": [f"test.{route}"]}
                for case in cases
            ],
        }
        for route in ROUTES
    ]
    return build_field_evaluation(
        evaluation_id="field-evaluation.single-function-requests.v1",
        policy=policy,
        human_decision_records=[_decision(policy)],
        label_guide=guide,
        reviewers=_reviewers(),
        cases=cases,
        labels=labels,
        adjudications=[],
        holdout_id="holdout.single-function-requests.v1",
        sealed_at=HOLDOUT_SEALED_AT,
        labels_released_at=LABELS_RELEASED_AT,
        run_specs=run_specs,
    )


class FieldSampleIntakeTests(unittest.TestCase):
    def test_schema_is_closed_valid_and_resolves_field_case_reference(self) -> None:
        root = Path(__file__).resolve().parents[1] / "schemas"
        schemas = [
            json.loads((root / name).read_text(encoding="utf-8"))
            for name in ("field-sample-intake.schema.json", "field-evaluation.schema.json")
        ]
        for schema in schemas:
            Draft202012Validator.check_schema(schema)
        registry = Registry().with_resources(
            [(schema["$id"], Resource.from_contents(schema)) for schema in schemas]
        )
        validator = Draft202012Validator(
            schemas[0], registry=registry, format_checker=FormatChecker()
        )
        self.assertFalse(list(validator.iter_errors(_intake())))
        schema = schemas[0]
        self.assertEqual(schema["properties"]["candidates"]["maxItems"], 4096)
        self.assertEqual(schema["$defs"]["stableRef"]["maxLength"], 512)

    def test_valid_intake_is_deterministic_and_projects_only_representatives(self) -> None:
        left = _intake(candidates=[_candidate(2), _candidate(1)], clusters=[_cluster(2), _cluster(1)])
        right = _intake()
        self.assertEqual(left, right)
        self.assertEqual(validate_field_sample_intake(left), left)
        self.assertEqual(left["holdout_projection"]["status"], "ready")
        cases = project_holdout_field_cases(left, policy=_policy())
        self.assertEqual([item["case_id"] for item in cases], ["field-case.01", "field-case.02"])
        self.assertTrue(all(item["source_kind"] == "field_sample" for item in cases))
        self.assertTrue(all(item["split"] == "holdout" for item in cases))

    def test_raw_material_cannot_be_added_to_closed_candidate(self) -> None:
        bundle = _intake()
        bundle["candidates"][0]["raw_text"] = "private source material"
        self.assertIn("schema_validation_failed", _codes(bundle))

    def test_pending_or_late_policy_blocks_holdout_without_faking_integrity(self) -> None:
        pending_policy = _policy(status="pending")
        pending = _intake(policy=pending_policy, decision=None)
        self.assertEqual(validate_field_sample_intake(pending), pending)
        self.assertEqual(pending["holdout_projection"]["status"], "blocked")
        self.assertIn("policy_not_adopted", pending["holdout_projection"]["reason_codes"])

        policy = _policy()
        late = _intake(
            policy=policy,
            decision=_decision(policy, recorded_at=COLLECTION_OPENED_AT),
        )
        self.assertEqual(validate_field_sample_intake(late), late)
        self.assertIn("policy_adopted_after_collection_open", late["holdout_projection"]["reason_codes"])
        with self.assertRaises(FieldSampleIntakeValidationError) as caught:
            project_holdout_field_cases(late, policy=policy)
        self.assertIn("holdout_projection_not_ready", caught.exception.codes)

    def test_permission_privacy_and_single_function_fail_closed(self) -> None:
        candidates = [
            _candidate(1, permission_status="unknown", allowed_uses=()),
            _candidate(2),
        ]
        permission = _intake(candidates=candidates)
        self.assertEqual(permission["candidate_assessments"][0]["status"], "excluded")
        self.assertIn("evaluation_permission_not_granted", permission["holdout_projection"]["reason_codes"])

        privacy = _intake(candidates=[_candidate(1, privacy_status="pending"), _candidate(2)])
        self.assertIn("privacy_release_not_approved", privacy["holdout_projection"]["reason_codes"])

        multiple = _intake(candidates=[_candidate(1, unit_status="multiple_functions"), _candidate(2)])
        self.assertIn("not_single_function", multiple["holdout_projection"]["reason_codes"])

    def test_known_unknown_or_incompletely_checked_exposure_blocks_holdout(self) -> None:
        record = {
            "exposure_id": "exposure.prior-test",
            "kind": "test_fixture",
            "subject_digest": _precomputed_digest("raw requirement 1"),
            "actor_ref": "semantic-guard.test-suite",
            "actor_version": "v1",
            "artifact_ref": "fixture.requirement-one",
            "occurred_at": "2026-08-27T12:00:00Z",
        }
        known = _intake(candidates=[_candidate(1, exposure_status="known_exposure", exposure_records=[record]), _candidate(2)])
        self.assertIn("known_prior_exposure", known["holdout_projection"]["reason_codes"])

        unknown = _intake(candidates=[_candidate(1, exposure_status="unknown"), _candidate(2)])
        self.assertIn("exposure_status_unknown", unknown["holdout_projection"]["reason_codes"])

        incomplete = _intake(
            candidates=[
                _candidate(1, checked_contexts={"training_corpus"}),
                _candidate(2),
            ]
        )
        self.assertIn("exposure_scope_incomplete", incomplete["holdout_projection"]["reason_codes"])

    def test_calibration_accepts_known_exposure_but_requires_calibration_permission(self) -> None:
        record = {
            "exposure_id": "exposure.prior-doc",
            "kind": "documentation_example",
            "subject_digest": _precomputed_digest("raw requirement 1"),
            "actor_ref": "documentation.author",
            "actor_version": "v1",
            "artifact_ref": "docs.example-one",
            "occurred_at": "2026-08-27T12:00:00Z",
        }
        candidates = [
            _candidate(1, exposure_status="known_exposure", exposure_records=[record]),
            _candidate(2),
        ]
        calibration = _intake(
            candidates=candidates,
            clusters=[_cluster(1, split="calibration"), _cluster(2, split="excluded")],
        )
        self.assertEqual(validate_field_sample_intake(calibration), calibration)
        self.assertEqual(calibration["holdout_projection"]["status"], "not_requested")

        no_permission_candidates = [
            _candidate(1, allowed_uses=("holdout_evaluation", "derived_metrics")),
            _candidate(2),
        ]
        not_permitted = _intake(
            candidates=no_permission_candidates,
            clusters=[_cluster(1, split="calibration"), _cluster(2, split="excluded")],
        )
        self.assertIn("calibration_assignment_not_permitted", _codes(not_permitted))

    def test_exact_and_normalized_duplicates_cannot_cross_clusters(self) -> None:
        exact = _intake(
            candidates=[
                _candidate(1, original_text="same raw"),
                _candidate(2, original_text="same raw"),
            ]
        )
        self.assertIn("exact_duplicate_cluster_mismatch", _codes(exact))

        normalized = _intake(
            candidates=[
                _candidate(1, normalized_text="same normalized"),
                _candidate(2, normalized_text="same normalized"),
            ]
        )
        self.assertIn("normalized_duplicate_cluster_mismatch", _codes(normalized))

    def test_duplicate_cluster_projects_one_representative(self) -> None:
        candidates = [
            _candidate(1, normalized_text="same normalized"),
            _candidate(2, normalized_text="same normalized"),
        ]
        intake = _intake(
            candidates=candidates,
            clusters=[
                _cluster(
                    1,
                    members=("field-candidate.01", "field-candidate.02"),
                    representative="field-candidate.01",
                )
            ],
        )
        self.assertEqual(validate_field_sample_intake(intake), intake)
        self.assertEqual(len(intake["holdout_projection"]["cases"]), 1)

    def test_lineage_must_be_known_acyclic_and_in_one_duplicate_cluster(self) -> None:
        cross = _intake(
            candidates=[
                _candidate(1),
                _candidate(2, derived_from_refs=("field-candidate.01",)),
            ]
        )
        self.assertIn("lineage_cluster_mismatch", _codes(cross))

        cyclic = _intake(
            candidates=[
                _candidate(1, derived_from_refs=("field-candidate.02",)),
                _candidate(2, derived_from_refs=("field-candidate.01",)),
            ],
            clusters=[
                _cluster(1, members=("field-candidate.01", "field-candidate.02"))
            ],
        )
        self.assertIn("lineage_cycle", _codes(cyclic))

    def test_derived_chain_inherits_cluster_exposure_block(self) -> None:
        record = {
            "exposure_id": "exposure.ancestor-training",
            "kind": "training",
            "subject_digest": _precomputed_digest("raw requirement 1"),
            "actor_ref": "model.training-pipeline",
            "actor_version": "v1",
            "artifact_ref": "corpus.training-snapshot",
            "occurred_at": "2026-08-27T12:00:00Z",
        }
        bundle = _intake(
            candidates=[
                _candidate(1, exposure_status="known_exposure", exposure_records=[record]),
                _candidate(2, derived_from_refs=("field-candidate.01",)),
                _candidate(3, derived_from_refs=("field-candidate.02",)),
            ],
            clusters=[
                _cluster(
                    1,
                    members=(
                        "field-candidate.01",
                        "field-candidate.02",
                        "field-candidate.03",
                    ),
                )
            ],
        )
        self.assertEqual(validate_field_sample_intake(bundle), bundle)
        self.assertEqual(bundle["holdout_projection"]["status"], "blocked")
        self.assertIn("known_prior_exposure", bundle["holdout_projection"]["reason_codes"])

    def test_same_source_occurrence_cannot_bind_different_original_content(self) -> None:
        bundle = _intake(
            candidates=[
                _candidate(1, original_text="one", source_occurrence_id="occurrence.shared"),
                _candidate(2, original_text="two", source_occurrence_id="occurrence.shared"),
            ]
        )
        self.assertIn("source_occurrence_content_conflict", _codes(bundle))

    def test_duplicate_review_must_cover_closed_sets_and_all_three_methods(self) -> None:
        incomplete = _intake(review_status="incomplete")
        self.assertEqual(validate_field_sample_intake(incomplete), incomplete)
        self.assertIn("duplicate_review_incomplete", incomplete["holdout_projection"]["reason_codes"])

        methods = _intake(review_methods={"exact_digest", "normalized_digest"})
        self.assertEqual(validate_field_sample_intake(methods), methods)
        self.assertIn("duplicate_review_methods_incomplete", methods["holdout_projection"]["reason_codes"])

        changed = _intake()
        changed["duplicate_review"]["candidate_set_digest"] = digest_value([])
        changed["duplicate_review"]["review_digest"] = digest_value(
            {
                key: value
                for key, value in changed["duplicate_review"].items()
                if key != "review_digest"
            }
        )
        changed["bundle_digest"] = digest_value(
            {key: value for key, value in changed.items() if key != "bundle_digest"}
        )
        self.assertIn("duplicate_review_candidate_set_mismatch", _codes(changed))

    def test_semantic_review_cannot_be_delegated_to_the_evaluated_model(self) -> None:
        bundle = _intake()
        bundle["duplicate_review"]["reviewer_kind"] = "model"
        self.assertIn("schema_validation_failed", _codes(bundle))

        missing_scope = _intake()
        del missing_scope["duplicate_review"]["comparison_scope"]["prior_intakes"]
        self.assertIn("schema_validation_failed", _codes(missing_scope))

    def test_acquisition_review_assignment_and_expiry_times_are_checked(self) -> None:
        outside = _intake(candidates=[_candidate(1, acquired_at="2026-08-27T22:00:00Z"), _candidate(2)])
        self.assertIn("candidate_acquisition_time_invalid", _codes(outside))

        expired = _intake(
            candidates=[
                _candidate(1, permission_valid_through="2026-08-28T05:59:59Z"),
                _candidate(2),
            ]
        )
        self.assertIn("permission_expired_before_freeze", expired["holdout_projection"]["reason_codes"])

        assigned = _intake(
            clusters=[
                _cluster(1, assigned_at="2026-08-28T03:59:59Z"),
                _cluster(2),
            ]
        )
        self.assertIn("cluster_assignment_time_invalid", _codes(assigned))

        for record_name in (
            "permission",
            "privacy_review",
            "unit_assessment",
            "exposure_declaration",
        ):
            with self.subTest(record_name=record_name):
                late_record = _intake(
                    candidates=[
                        _candidate(
                            1,
                            record_times={
                                record_name: "2026-08-28T05:30:00Z"
                            },
                        ),
                        _candidate(2),
                    ]
                )
                failures = field_sample_intake_errors(late_record)
                self.assertIn(
                    "candidate_record_after_assignment",
                    {item["code"] for item in failures},
                )
                self.assertTrue(
                    any(
                        item["location"].endswith(
                            f".{record_name}.recorded_at"
                        )
                        for item in failures
                    )
                )

    def test_undeclared_or_ambiguous_strata_cannot_reach_projection(self) -> None:
        for refs, expected_codes in (
            (
                ("risk.unknown",),
                {
                    "candidate_dangling_stratum",
                    "candidate_required_stratum_cardinality",
                },
            ),
            (("risk.normal", "risk.high"), {"candidate_required_stratum_cardinality"}),
        ):
            with self.subTest(stratum_refs=refs):
                bundle = _intake(
                    candidates=[
                        _candidate(1, stratum_refs=refs),
                        _candidate(2),
                    ]
                )
                self.assertEqual(bundle["holdout_projection"]["status"], "blocked")
                self.assertTrue(expected_codes.issubset(_codes(bundle)))
                with self.assertRaises(FieldSampleIntakeValidationError) as caught:
                    project_holdout_field_cases(bundle, policy=_policy())
                self.assertTrue(expected_codes.issubset(set(caught.exception.codes)))

    def test_privacy_approval_is_bound_to_the_evaluated_digest(self) -> None:
        candidate = _candidate(1)
        candidate["privacy_review"] = build_privacy_review(
            classification="internal",
            handling="redacted",
            release_status="approved",
            reviewer_ref="privacy.reviewer",
            decision_record_ref="privacy.project-1",
            recorded_at="2026-08-28T01:00:00Z",
            approved_subject_digest=_precomputed_digest("different subject"),
        )
        candidate["candidate_digest"] = digest_value(
            {key: value for key, value in candidate.items() if key != "candidate_digest"}
        )
        bundle = _intake(candidates=[candidate, _candidate(2)])
        self.assertIn("privacy_subject_binding_mismatch", _codes(bundle))

    def test_false_eligibility_write_over_is_rejected_by_replay(self) -> None:
        bundle = _intake(policy=_policy(status="pending"), decision=None)
        assessment = bundle["candidate_assessments"][0]
        assessment["status"] = "eligible_for_holdout"
        assessment["reason_codes"] = []
        assessment["assessment_digest"] = digest_value(
            {key: value for key, value in assessment.items() if key != "assessment_digest"}
        )
        bundle["bundle_digest"] = digest_value(
            {key: value for key, value in bundle.items() if key != "bundle_digest"}
        )
        self.assertIn("candidate_assessment_replay_mismatch", _codes(bundle))

    def test_policy_substitution_is_rejected_at_projection(self) -> None:
        intake = _intake()
        changed = _policy()
        changed["target_population"]["description"] = "substituted population"
        changed["target_population"]["population_digest"] = digest_value(
            {
                key: value
                for key, value in changed["target_population"].items()
                if key != "population_digest"
            }
        )
        changed["policy_digest"] = digest_value(
            {key: value for key, value in changed.items() if key != "policy_digest"}
        )
        with self.assertRaises(FieldSampleIntakeValidationError) as caught:
            project_holdout_field_cases(intake, policy=changed)
        self.assertIn("projection_policy_binding_mismatch", caught.exception.codes)

    def test_malformed_projection_policy_returns_stable_validation_error(self) -> None:
        intake = _intake()
        for malformed in ({}, {"policy_id": "field-policy.partial"}):
            with self.subTest(policy=malformed):
                with self.assertRaises(FieldSampleIntakeValidationError) as caught:
                    project_holdout_field_cases(intake, policy=malformed)
                self.assertEqual(
                    set(caught.exception.codes),
                    {"projection_policy_schema_invalid"},
                )

    def test_intake_and_field_evaluation_bind_on_policy_population_and_case_set(self) -> None:
        policy = _policy()
        intake = _intake(policy=policy)
        cases = project_holdout_field_cases(intake, policy=policy)
        evaluation = _evaluation(policy, cases)
        self.assertEqual(
            validate_field_sample_intake_evaluation(intake, evaluation),
            evaluation,
        )
        self.assertEqual(field_sample_intake_evaluation_errors(intake, evaluation), ())

        other_intake = _intake(
            policy=policy,
            candidates=[
                _candidate(1, evaluation_text="different evaluated requirement"),
                _candidate(2),
            ],
        )
        other_cases = project_holdout_field_cases(other_intake, policy=policy)
        other_evaluation = _evaluation(policy, other_cases)
        codes = {
            item["code"]
            for item in field_sample_intake_evaluation_errors(intake, other_evaluation)
        }
        self.assertIn("intake_evaluation_case_set_mismatch", codes)
        self.assertIn("intake_evaluation_case_set_digest_mismatch", codes)

    def test_evaluation_binding_rechecks_permission_through_label_release(self) -> None:
        policy = _policy()
        expired_intake = _intake(
            policy=policy,
            candidates=[
                _candidate(
                    1,
                    permission_valid_through="2026-08-28T06:30:00Z",
                ),
                _candidate(2),
            ],
        )
        self.assertEqual(expired_intake["holdout_projection"]["status"], "ready")
        expired_cases = project_holdout_field_cases(
            expired_intake, policy=policy
        )
        expired_evaluation = _evaluation(policy, expired_cases)
        self.assertIn(
            "permission_expired_before_evaluation_completion",
            {
                item["code"]
                for item in field_sample_intake_evaluation_errors(
                    expired_intake, expired_evaluation
                )
            },
        )

        boundary_intake = _intake(
            policy=policy,
            candidates=[
                _candidate(
                    1,
                    permission_valid_through=LABELS_RELEASED_AT,
                ),
                _candidate(2),
            ],
        )
        boundary_cases = project_holdout_field_cases(
            boundary_intake, policy=policy
        )
        boundary_evaluation = _evaluation(policy, boundary_cases)
        self.assertEqual(
            field_sample_intake_evaluation_errors(
                boundary_intake, boundary_evaluation
            ),
            (),
        )

    def test_old_field_case_contract_is_not_extended(self) -> None:
        case = project_holdout_field_cases(_intake(), policy=_policy())[0]
        self.assertEqual(
            set(case),
            {
                "case_id",
                "subject_ref",
                "subject_digest",
                "population_id",
                "intended_use_id",
                "stratum_refs",
                "source_kind",
                "split",
                "case_digest",
            },
        )
        self.assertNotIn("intake_id", case)

    def test_validation_exception_exposes_stable_error_codes(self) -> None:
        bundle = _intake()
        bundle["candidates"][0]["candidate_digest"] = digest_value({"changed": True})
        with self.assertRaises(FieldSampleIntakeValidationError) as caught:
            validate_field_sample_intake(bundle)
        self.assertIn("candidate_digest_mismatch", caught.exception.codes)


if __name__ == "__main__":
    unittest.main()
