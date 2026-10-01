from __future__ import annotations

from copy import deepcopy
import unittest

from semantic_guard_vnext.engine import audit_requirement_relations_vnext
from semantic_guard_vnext.governed_audit import (
    GovernedAuditValidationError,
    _candidate_finding_values,
    _governed_audit_id,
    digest_value,
    project_governed_audit,
    validate_governed_audit,
    validate_legacy_output,
    wrap_legacy_output,
)
from semantic_guard_vnext.public_contract import public_audit_payload


COMPLETE = """Purpose: 検索APIが検索結果を p95 500ms以内で返す
User: 検索API
Scenario: 検索APIが検索要求を処理して検索結果を返す
Expected result: 検索結果を p95 500ms以内で返す
Acceptance criteria: 検索応答時間 p95 500ms 以下
Verification method: 検索結果の検索応答時間を benchmark で測定する
Evidence: 検索結果の検索応答時間 benchmark report"""

RECORDED_AT = "2026-07-18T00:00:00Z"


def _payload() -> dict:
    report = audit_requirement_relations_vnext(
        COMPLETE,
        analysis_mode="conditional",
    )
    return project_governed_audit(report, recorded_at=RECORDED_AT)


def _reseal(payload: dict, *, analysis_material_changed: bool = False) -> None:
    if analysis_material_changed:
        material = payload["legacy_analysis_material"]
        digest_material = deepcopy(material)
        digest_material.pop("material_digest")
        material["material_digest"] = digest_value(digest_material)
    payload["audit_id"] = _governed_audit_id(payload)
    record = deepcopy(payload)
    record.pop("record_digest")
    payload["record_digest"] = digest_value(record)


class GovernedAuditTests(unittest.TestCase):
    def test_legacy_direct_pass_is_only_an_observation_without_h1(self) -> None:
        payload = validate_governed_audit(_payload())

        self.assertEqual(
            payload["legacy_analysis_observation"]["observed_workflow_disposition"],
            "pass",
        )
        self.assertEqual(
            payload["legacy_analysis_observation"]["authority_status"],
            "legacy_ungoverned_observation_only",
        )
        self.assertEqual(payload["assurance_assessment"]["status"], "unresolved")
        self.assertEqual(
            payload["assurance_assessment"]["workflow_disposition"], "block"
        )
        self.assertEqual(
            payload["assurance_assessment"]["formal_verdict_authority"], "none"
        )
        self.assertEqual(
            payload["governance_resolution"]["h1_human_decision"], "pending"
        )

    def test_direct_findings_remain_candidate_only(self) -> None:
        payload = _payload()

        self.assertTrue(payload["candidate_findings"])
        self.assertTrue(
            all(
                finding["allowed_use"] == "candidate_finding"
                and finding["formal_authority"] == "none"
                for finding in payload["candidate_findings"]
            )
        )
        self.assertTrue(
            payload["governance_resolution"]["required_authority_source_ids"]
        )
        self.assertEqual(payload["subject"]["source_text"], COMPLETE)
        self.assertTrue(
            {
                "structured_record_observation",
                "direct_rule_assessment",
            }
            <= {item["finding_kind"] for item in payload["candidate_findings"]}
        )

    def test_governed_trace_retains_every_analysis_layer_as_candidate_material(
        self,
    ) -> None:
        report = audit_requirement_relations_vnext(COMPLETE, analysis_mode="assurance")
        payload = project_governed_audit(report, recorded_at=RECORDED_AT)
        material = payload["legacy_analysis_material"]

        self.assertEqual(
            [item["stage"] for item in material["analysis_attempts"]],
            [
                "structured_parse",
                "direct_rules",
                "morphology",
                "dependency_parse",
                "llm_candidate",
            ],
        )
        self.assertTrue(
            all(
                item["allowed_use"] == "candidate_finding"
                and item["formal_authority"] == "none"
                for item in material["analysis_attempts"]
            )
        )
        internal = material["legacy_internal_trace"]
        self.assertEqual(
            material["provider_execution_receipts"],
            internal["provider_execution_receipts"],
        )
        self.assertEqual(
            material["obligation_reassessments"],
            internal["obligation_reassessments"],
        )
        self.assertEqual(
            material["unresolved_observations"]["remaining"],
            internal["remaining_unresolved_obligations"],
        )
        self.assertEqual(
            material["provenance"],
            material["legacy_public_payload"]["provenance"],
        )
        self.assertIn(
            "provider_analysis_attempt",
            {item["finding_kind"] for item in payload["candidate_findings"]},
        )

    def test_analysis_attempt_omission_is_detected_even_after_outer_reseal(
        self,
    ) -> None:
        report = audit_requirement_relations_vnext(COMPLETE, analysis_mode="assurance")
        payload = project_governed_audit(report, recorded_at=RECORDED_AT)
        payload["legacy_analysis_material"]["analysis_attempts"].pop()
        payload["record_digest"] = digest_value(
            {
                key: deepcopy(value)
                for key, value in payload.items()
                if key != "record_digest"
            }
        )

        with self.assertRaises(GovernedAuditValidationError) as caught:
            validate_governed_audit(payload)
        self.assertIn("analysis_attempt_denominator_mismatch", caught.exception.codes)
        self.assertIn("audit_id_mismatch", caught.exception.codes)

    def test_explicit_audit_id_tampering_is_rejected(self) -> None:
        payload = _payload()
        payload["audit_id"] = "governed-audit." + ("0" * 64)
        payload["record_digest"] = digest_value(
            {
                key: deepcopy(value)
                for key, value in payload.items()
                if key != "record_digest"
            }
        )

        with self.assertRaises(GovernedAuditValidationError) as caught:
            validate_governed_audit(payload)
        self.assertIn("audit_id_mismatch", caught.exception.codes)

    def test_legacy_envelope_remains_self_describing_after_format_context_loss(
        self,
    ) -> None:
        stored = deepcopy(
            wrap_legacy_output(
                "legacy-internal-debug-v0",
                audit_requirement_relations_vnext(
                    COMPLETE, analysis_mode="conditional"
                ).as_dict(),
            )
        )
        payload = validate_legacy_output(stored)

        self.assertEqual(payload["governance_status"], "legacy_ungoverned")
        self.assertEqual(payload["authority_scope"], "observation_only")
        self.assertEqual(payload["formal_authority"], "none")
        self.assertFalse(payload["positive_assurance"])
        self.assertEqual(payload["legacy_payload"]["result"]["workflow"], "pass")

    def test_legacy_nested_payload_tampering_is_rejected(self) -> None:
        legacy = public_audit_payload(
            audit_requirement_relations_vnext(COMPLETE, analysis_mode="conditional"),
            recorded_at=RECORDED_AT,
        )
        payload = wrap_legacy_output("legacy-public-v0", legacy)
        payload["legacy_payload"]["workflow_disposition"]["status"] = "block"

        with self.assertRaises(GovernedAuditValidationError) as caught:
            validate_legacy_output(payload)
        self.assertIn("record_digest_mismatch", caught.exception.codes)
        self.assertIn("envelope_id_mismatch", caught.exception.codes)

    def test_missing_governance_has_closed_unresolved_record(self) -> None:
        payload = _payload()
        unresolved = payload["unresolved_records"][0]

        for field in (
            "owner",
            "next_action",
            "resolution_condition",
            "review_at",
            "fallback",
            "retirement_condition",
        ):
            self.assertTrue(unresolved[field])
        self.assertEqual(unresolved["blocking_status"], "blocking_positive_assurance")
        self.assertEqual(
            {item["uncertainty_kind"] for item in payload["unresolved_records"]},
            {
                "engineering_rule_authority",
                "lifecycle_profile_authority",
                "execution_environment_evidence",
                "field_performance_qualification",
            },
        )
        self.assertEqual(
            payload["assurance_assessment"]["blocking_unresolved_count"], 4
        )

    def test_resealed_authority_laundering_is_rejected(self) -> None:
        payload = _payload()
        payload["assurance_assessment"].update(
            {
                "status": "formally_resolved_for_declared_scope",
                "workflow_disposition": "pass",
                "formal_verdict_authority": "bounded",
            }
        )
        payload["unresolved_records"] = []
        payload["record_digest"] = digest_value(
            {
                key: deepcopy(value)
                for key, value in payload.items()
                if key != "record_digest"
            }
        )

        with self.assertRaises(GovernedAuditValidationError) as caught:
            validate_governed_audit(payload)
        self.assertIn("unresolved_authority_laundering", caught.exception.codes)

    def test_resealed_allowed_use_escalation_is_rejected(self) -> None:
        payload = _payload()
        payload["assurance_assessment"]["allowed_use"].append(
            "bounded_formal_audit_disposition"
        )
        payload["record_digest"] = digest_value(
            {
                key: deepcopy(value)
                for key, value in payload.items()
                if key != "record_digest"
            }
        )

        with self.assertRaises(GovernedAuditValidationError) as caught:
            validate_governed_audit(payload)
        self.assertIn("unresolved_authority_laundering", caught.exception.codes)

    def test_unverified_h1_disposition_cannot_be_projected(self) -> None:
        payload = _payload()
        payload["governance_resolution"].update(
            {"h1_human_decision": "accept", "h1_verdict_authority": "formal"}
        )
        payload["record_digest"] = digest_value(
            {
                key: deepcopy(value)
                for key, value in payload.items()
                if key != "record_digest"
            }
        )

        with self.assertRaises(GovernedAuditValidationError):
            validate_governed_audit(payload)

    def test_resealed_removal_of_a_required_governance_axis_is_rejected(self) -> None:
        payload = _payload()
        payload["unresolved_records"] = [
            item
            for item in payload["unresolved_records"]
            if item["uncertainty_kind"] != "field_performance_qualification"
        ]
        payload["assurance_assessment"]["blocking_unresolved_count"] = len(
            payload["unresolved_records"]
        )
        payload["record_digest"] = digest_value(
            {
                key: deepcopy(value)
                for key, value in payload.items()
                if key != "record_digest"
            }
        )

        with self.assertRaises(GovernedAuditValidationError) as caught:
            validate_governed_audit(payload)
        self.assertIn("unresolved_denominator_mismatch", caught.exception.codes)

    def test_resealed_subject_and_audit_identity_substitution_is_rejected(self) -> None:
        payload = _payload()
        payload["subject"]["content_digest"] = digest_value("another subject")
        payload["record_digest"] = digest_value(
            {
                key: deepcopy(value)
                for key, value in payload.items()
                if key != "record_digest"
            }
        )

        with self.assertRaises(GovernedAuditValidationError) as caught:
            validate_governed_audit(payload)
        self.assertIn("subject_digest_mismatch", caught.exception.codes)

        payload = _payload()
        payload["governance_resolution"]["reason_codes"].append("substituted")
        payload["record_digest"] = digest_value(
            {
                key: deepcopy(value)
                for key, value in payload.items()
                if key != "record_digest"
            }
        )
        with self.assertRaises(GovernedAuditValidationError) as caught:
            validate_governed_audit(payload)
        self.assertIn("audit_id_mismatch", caught.exception.codes)

    def test_resealed_limitation_or_finding_identity_replacement_is_rejected(
        self,
    ) -> None:
        for mutate, expected in (
            (
                lambda payload: payload.update(
                    {"limitations": ["replacement limitation"]}
                ),
                "limitations_mismatch",
            ),
            (
                lambda payload: payload["candidate_findings"][0].update(
                    {"finding_id": "candidate-finding.replaced"}
                ),
                "candidate_finding_denominator_mismatch",
            ),
        ):
            with self.subTest(expected=expected):
                payload = _payload()
                mutate(payload)
                payload["record_digest"] = digest_value(
                    {
                        key: deepcopy(value)
                        for key, value in payload.items()
                        if key != "record_digest"
                    }
                )
                with self.assertRaises(GovernedAuditValidationError) as caught:
                    validate_governed_audit(payload)
                self.assertIn(expected, caught.exception.codes)

    def test_audit_identity_binds_every_semantic_output_field(self) -> None:
        mutations = (
            lambda payload: payload["candidate_findings"][0].update(
                {"observed_outcome": "unresolved"}
            ),
            lambda payload: payload["candidate_findings"][0]["reason_codes"].append(
                "replacement basis"
            ),
            lambda payload: payload["legacy_analysis_observation"].update(
                {"analysis_reasons": ["replacement summary"]}
            ),
            lambda payload: payload["unresolved_records"][0].update(
                {"next_action": "replacement action"}
            ),
        )
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                payload = _payload()
                original_audit_id = payload["audit_id"]
                mutate(payload)
                payload["record_digest"] = digest_value(
                    {
                        key: deepcopy(value)
                        for key, value in payload.items()
                        if key != "record_digest"
                    }
                )
                self.assertEqual(payload["audit_id"], original_audit_id)
                with self.assertRaises(GovernedAuditValidationError) as caught:
                    validate_governed_audit(payload)
                self.assertIn("audit_id_mismatch", caught.exception.codes)

    def test_authority_denominator_tracks_exercised_capabilities(self) -> None:
        payload = _payload()

        self.assertTrue(
            all(
                "#" in source_id
                for source_id in payload["governance_resolution"][
                    "required_authority_source_ids"
                ]
            )
        )
        self.assertEqual(
            payload["governance_resolution"]["resolved_authority_source_ids"], []
        )

    def test_unembedded_governance_bundle_is_rejected(self) -> None:
        report = audit_requirement_relations_vnext(
            COMPLETE, analysis_mode="conditional"
        )
        with self.assertRaisesRegex(ValueError, "cannot be replayed"):
            project_governed_audit(
                report,
                governance_bundle={"schema_version": "forged"},
                recorded_at=RECORDED_AT,
            )

    def test_source_text_and_content_unresolved_denominator_are_closed(self) -> None:
        report = audit_requirement_relations_vnext(
            "Purpose: 利用者が検索する",
            analysis_mode="assurance",
        )
        payload = project_governed_audit(report, recorded_at=RECORDED_AT)
        unresolved_required = payload["legacy_analysis_material"][
            "legacy_public_payload"
        ]["unresolved_required_obligation_ids"]
        projected = [
            item
            for item in payload["unresolved_records"]
            if item["uncertainty_kind"] == "requirement_obligation_evidence"
        ]
        self.assertEqual(len(projected), len(unresolved_required))
        self.assertTrue(projected)
        self.assertIn(
            "obligation_reassessment",
            {item["finding_kind"] for item in payload["candidate_findings"]},
        )
        self.assertEqual(
            payload["assurance_assessment"]["workflow_disposition"], "block"
        )

        payload["subject"]["source_text"] += " tampered"
        payload["record_digest"] = digest_value(
            {
                key: deepcopy(value)
                for key, value in payload.items()
                if key != "record_digest"
            }
        )
        with self.assertRaises(GovernedAuditValidationError) as caught:
            validate_governed_audit(payload)
        self.assertIn("subject_source_text_digest_mismatch", caught.exception.codes)

    def test_content_unresolved_omission_is_rejected_after_reseal(self) -> None:
        report = audit_requirement_relations_vnext(
            "Purpose: 利用者が検索する",
            analysis_mode="assurance",
        )
        payload = project_governed_audit(report, recorded_at=RECORDED_AT)
        payload["unresolved_records"] = [
            item
            for item in payload["unresolved_records"]
            if item["uncertainty_kind"] != "requirement_obligation_evidence"
        ]
        payload["assurance_assessment"]["blocking_unresolved_count"] = len(
            payload["unresolved_records"]
        )
        payload["record_digest"] = digest_value(
            {
                key: deepcopy(value)
                for key, value in payload.items()
                if key != "record_digest"
            }
        )
        with self.assertRaises(GovernedAuditValidationError) as caught:
            validate_governed_audit(payload)
        self.assertIn(
            "requirement_unresolved_denominator_mismatch", caught.exception.codes
        )

    def test_resealed_route_trace_omission_cannot_erase_content_unresolved(
        self,
    ) -> None:
        payload = project_governed_audit(
            audit_requirement_relations_vnext(
                "Purpose: 利用者が検索する", analysis_mode="assurance"
            ),
            recorded_at=RECORDED_AT,
        )
        material = payload["legacy_analysis_material"]
        internal = material["legacy_internal_trace"]
        internal["remaining_unresolved_obligations"] = []
        internal["unresolved_obligations"] = []
        material["unresolved_observations"]["remaining"] = []
        material["unresolved_observations"]["effective"] = []
        material["trace_inventory"]["remaining_unresolved_count"] = 0
        payload["unresolved_records"] = [
            item
            for item in payload["unresolved_records"]
            if item["uncertainty_kind"] != "requirement_obligation_evidence"
        ]
        payload["assurance_assessment"]["blocking_unresolved_count"] = len(
            payload["unresolved_records"]
        )
        _reseal(payload, analysis_material_changed=True)

        with self.assertRaises(GovernedAuditValidationError) as caught:
            validate_governed_audit(payload)
        self.assertIn(
            "requirement_unresolved_denominator_mismatch", caught.exception.codes
        )

    def test_resealed_legacy_summary_cannot_disagree_with_internal_result(self) -> None:
        payload = _payload()
        payload["legacy_analysis_observation"]["observed_workflow_disposition"] = (
            "block"
        )
        _reseal(payload)

        with self.assertRaises(GovernedAuditValidationError) as caught:
            validate_governed_audit(payload)
        self.assertIn(
            "legacy_observation_internal_trace_mismatch", caught.exception.codes
        )

    def test_resealed_governance_summary_must_replay_from_embedded_material(
        self,
    ) -> None:
        payload = _payload()
        payload["governance_resolution"]["observation_binding_status"] = "matched"
        _reseal(payload)

        with self.assertRaises(GovernedAuditValidationError) as caught:
            validate_governed_audit(payload)
        self.assertIn("governance_resolution_material_mismatch", caught.exception.codes)

    def test_resealed_direct_result_chain_mismatch_is_rejected(self) -> None:
        payload = _payload()
        material = payload["legacy_analysis_material"]
        internal = material["legacy_internal_trace"]
        original = internal["direct_assessments"][0]["outcome"]
        internal["direct_assessments"][0]["outcome"] = (
            "unresolved" if original != "unresolved" else "supported"
        )
        material["analysis_attempts"][1]["observed_material"] = deepcopy(
            internal["direct_assessments"]
        )
        payload["candidate_findings"] = _candidate_finding_values(internal)
        _reseal(payload, analysis_material_changed=True)

        with self.assertRaises(GovernedAuditValidationError) as caught:
            validate_governed_audit(payload)
        self.assertIn("direct_reassessment_result_mismatch", caught.exception.codes)

    def test_malformed_internal_trace_returns_closed_validation_error(self) -> None:
        payload = _payload()
        payload["legacy_analysis_material"]["legacy_internal_trace"] = {}
        _reseal(payload, analysis_material_changed=True)

        with self.assertRaises(GovernedAuditValidationError) as caught:
            validate_governed_audit(payload)
        self.assertIn("schema_error", caught.exception.codes)

    def test_governance_material_schema_requires_every_axis(self) -> None:
        payload = _payload()
        assessment = payload["governance_material_assessment"]
        del assessment["field_performance_evidence"]
        assessment_material = deepcopy(assessment)
        assessment_material.pop("assessment_digest")
        assessment["assessment_digest"] = digest_value(assessment_material)
        _reseal(payload)

        with self.assertRaises(GovernedAuditValidationError) as caught:
            validate_governed_audit(payload)
        self.assertIn("schema_error", caught.exception.codes)

    def test_same_observation_time_is_deterministic(self) -> None:
        self.assertEqual(_payload(), _payload())


if __name__ == "__main__":
    unittest.main()
