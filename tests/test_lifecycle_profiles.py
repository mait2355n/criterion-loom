from __future__ import annotations

import copy
import unittest

from jsonschema import Draft202012Validator

from semantic_guard.lifecycle_profiles import (
    ORIGIN_REQUIREMENTS,
    STAGES,
    TRACE_STAGE_BY_PROFILE_STAGE,
    LifecycleProfileRegistryValidationError,
    build_registry_summary,
    lifecycle_profile_registry_errors,
    lifecycle_profile_registry_schema,
    load_candidate_registry,
    seal_lifecycle_profile_registry,
    validate_lifecycle_profile_registry,
)


class LifecycleProfileRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = load_candidate_registry()

    def _codes(self, registry: dict) -> set[str]:
        return {item["code"] for item in lifecycle_profile_registry_errors(registry)}

    def _profile(self, registry: dict, stage: str) -> dict:
        return next(item for item in registry["profiles"] if item["stage"] == stage)

    def test_schema_is_valid_draft_2020_12(self) -> None:
        Draft202012Validator.check_schema(lifecycle_profile_registry_schema())

    def test_repository_candidate_is_valid_and_closed(self) -> None:
        validated = validate_lifecycle_profile_registry(self.registry)
        self.assertEqual(tuple(validated["stage_order"]), STAGES)
        self.assertEqual(
            tuple(profile["stage"] for profile in validated["profiles"]), STAGES
        )
        self.assertEqual(
            {profile["status"] for profile in validated["profiles"]},
            {"pending_human_adoption"},
        )
        for profile in validated["profiles"]:
            self.assertEqual(
                set(profile["upstream_trace"]["origin_requirements"]),
                ORIGIN_REQUIREMENTS,
            )
            self.assertIn(
                "artifact_presence_only",
                {
                    item["condition_kind"]
                    for item in profile["hollow_success_conditions"]
                },
            )

    def test_sealing_is_deterministic_and_cannot_adopt(self) -> None:
        raw = copy.deepcopy(self.registry)
        raw.pop("registry_digest")
        raw.pop("summary")
        for profile in raw["profiles"]:
            profile.pop("profile_digest")
        first = seal_lifecycle_profile_registry(raw)
        second = seal_lifecycle_profile_registry(raw)
        self.assertEqual(first, second)
        self.assertEqual(first["status"], "candidate")
        self.assertEqual(first["summary"]["adoption_counts"]["adopted"], 0)
        self.assertEqual(first, self.registry)

    def test_saved_summary_replays_exactly(self) -> None:
        self.assertEqual(self.registry["summary"], build_registry_summary(self.registry))

    def test_missing_stage_is_rejected(self) -> None:
        registry = copy.deepcopy(self.registry)
        registry["profiles"] = registry["profiles"][:-1]
        self.assertIn("stage_denominator_incomplete", self._codes(registry))

    def test_declared_stage_order_change_is_rejected(self) -> None:
        registry = copy.deepcopy(self.registry)
        registry["stage_order"][3], registry["stage_order"][4] = (
            registry["stage_order"][4],
            registry["stage_order"][3],
        )
        self.assertIn("stage_order_invalid", self._codes(registry))

    def test_profile_order_change_is_rejected(self) -> None:
        registry = copy.deepcopy(self.registry)
        registry["profiles"][0], registry["profiles"][1] = (
            registry["profiles"][1],
            registry["profiles"][0],
        )
        self.assertIn("profile_order_invalid", self._codes(registry))

    def test_profile_digest_tamper_is_rejected(self) -> None:
        registry = copy.deepcopy(self.registry)
        self._profile(registry, "requirement")["purpose"] += " tampered"
        self.assertIn("profile_digest_mismatch", self._codes(registry))

    def test_registry_digest_tamper_is_rejected(self) -> None:
        registry = copy.deepcopy(self.registry)
        registry["registry_digest"]["value"] = "0" * 64
        self.assertIn("registry_digest_mismatch", self._codes(registry))

    def test_unknown_stage_reference_is_rejected(self) -> None:
        registry = copy.deepcopy(self.registry)
        self._profile(registry, "plan")["upstream_trace"]["stage_refs"] = [
            "imaginary_stage"
        ]
        self.assertIn("unknown_stage_reference", self._codes(registry))

    def test_empty_required_semantic_denominator_is_rejected(self) -> None:
        registry = copy.deepcopy(self.registry)
        self._profile(registry, "requirement")["required_semantic_fields"] = []
        self.assertIn("empty_required_denominator", self._codes(registry))

    def test_schema_invalid_null_does_not_crash_fail_closed_validation(self) -> None:
        registry = copy.deepcopy(self.registry)
        profile = self._profile(registry, "action")
        profile["hollow_success_conditions"] = None
        profile["authority_boundary"]["prohibited_promotions"] = None
        codes = self._codes(registry)
        self.assertIn("schema_validation_failed", codes)
        self.assertIn("hollow_success_coverage_missing", codes)
        self.assertIn("action_authority_violation", codes)

    def test_artifact_existence_cannot_be_the_only_success_basis(self) -> None:
        registry = copy.deepcopy(self.registry)
        self._profile(registry, "realization")["required_relationships"] = []
        self.assertIn("empty_required_denominator", self._codes(registry))

    def test_adoption_claim_is_rejected(self) -> None:
        registry = copy.deepcopy(self.registry)
        self._profile(registry, "plan")["status"] = "adopted"
        self.assertIn("adoption_authority_violation", self._codes(registry))

    def test_semantic_guard_adoption_authority_is_rejected(self) -> None:
        registry = copy.deepcopy(self.registry)
        registry["authority_boundary"]["semantic_guard_adoption_authority"] = (
            "audit_decision"
        )
        self.assertIn("adoption_authority_violation", self._codes(registry))

    def test_origin_requirement_omission_is_rejected(self) -> None:
        registry = copy.deepcopy(self.registry)
        self._profile(registry, "diff")["upstream_trace"]["origin_requirements"] = [
            "OR-01",
            "OR-02",
        ]
        self.assertIn("origin_trace_incomplete", self._codes(registry))

    def test_obligation_templates_must_cover_all_origin_requirements(self) -> None:
        registry = copy.deepcopy(self.registry)
        profile = self._profile(registry, "verification")
        profile["obligation_templates"][-1]["origin_trace"] = ["OR-02"]
        self.assertIn("obligation_origin_trace_incomplete", self._codes(registry))

    def test_artifact_presence_hollow_condition_cannot_be_removed(self) -> None:
        registry = copy.deepcopy(self.registry)
        profile = self._profile(registry, "request")
        profile["hollow_success_conditions"] = [
            item
            for item in profile["hollow_success_conditions"]
            if item["condition_kind"] != "artifact_presence_only"
        ]
        self.assertIn("hollow_success_coverage_missing", self._codes(registry))

    def test_decision_cannot_be_owned_by_an_agent(self) -> None:
        registry = copy.deepcopy(self.registry)
        profile = self._profile(registry, "decision")
        profile["authority_boundary"]["claim_owner"] = "explicitly_authorized_actor"
        self.assertIn("decision_authority_violation", self._codes(registry))

    def test_decision_cannot_drop_audit_promotion_prohibition(self) -> None:
        registry = copy.deepcopy(self.registry)
        profile = self._profile(registry, "decision")
        profile["authority_boundary"]["prohibited_promotions"].remove(
            "audit_result_implies_decision"
        )
        self.assertIn("decision_authority_violation", self._codes(registry))

    def test_action_requires_separate_occurrence_evidence(self) -> None:
        registry = copy.deepcopy(self.registry)
        profile = self._profile(registry, "action")
        profile["authority_boundary"]["occurrence_evidence_required"] = False
        self.assertIn("action_authority_violation", self._codes(registry))

    def test_action_audit_cannot_grant_execution_authority(self) -> None:
        registry = copy.deepcopy(self.registry)
        profile = self._profile(registry, "action")
        profile["authority_boundary"]["execution_authority"] = "not_applicable"
        self.assertIn("action_authority_violation", self._codes(registry))

    def test_completion_claim_cannot_be_human_acceptance(self) -> None:
        registry = copy.deepcopy(self.registry)
        profile = self._profile(registry, "completion")
        profile["authority_boundary"]["claim_owner"] = "human"
        self.assertIn("completion_authority_violation", self._codes(registry))

    def test_completion_cannot_drop_final_acceptance_prohibition(self) -> None:
        registry = copy.deepcopy(self.registry)
        profile = self._profile(registry, "completion")
        profile["authority_boundary"]["prohibited_promotions"].remove(
            "audit_result_implies_final_acceptance"
        )
        self.assertIn("completion_authority_violation", self._codes(registry))

    def test_lifecycle_trace_stage_mapping_is_closed(self) -> None:
        registry = copy.deepcopy(self.registry)
        profile = self._profile(registry, "exploration")
        profile["lifecycle_trace_stage"] = "request"
        self.assertIn("lifecycle_trace_stage_mismatch", self._codes(registry))
        self.assertEqual(
            TRACE_STAGE_BY_PROFILE_STAGE["completion"], "completion_claim"
        )

    def test_adjacent_trace_cannot_skip_a_stage(self) -> None:
        registry = copy.deepcopy(self.registry)
        self._profile(registry, "diff")["upstream_trace"]["stage_refs"] = [
            "requirement"
        ]
        self.assertIn("adjacent_upstream_trace_invalid", self._codes(registry))

    def test_duplicate_nested_identity_is_rejected(self) -> None:
        registry = copy.deepcopy(self.registry)
        fields = self._profile(registry, "requirement")["required_semantic_fields"]
        fields[1]["field_id"] = fields[0]["field_id"]
        self.assertIn("duplicate_profile_member_id", self._codes(registry))

    def test_saved_summary_tamper_is_rejected(self) -> None:
        registry = copy.deepcopy(self.registry)
        registry["summary"]["authority_statement"] += " tampered"
        self.assertIn("summary_replay_mismatch", self._codes(registry))

    def test_exception_exposes_typed_codes(self) -> None:
        registry = copy.deepcopy(self.registry)
        self._profile(registry, "action")["required_relationships"] = []
        with self.assertRaises(LifecycleProfileRegistryValidationError) as caught:
            validate_lifecycle_profile_registry(registry)
        self.assertIn("empty_required_denominator", caught.exception.codes)


if __name__ == "__main__":
    unittest.main()
