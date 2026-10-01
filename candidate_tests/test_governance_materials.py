from __future__ import annotations

from copy import deepcopy
import unittest

from semantic_guard_vnext.engine import audit_requirement_relations_vnext
from semantic_guard_vnext.governed_audit import (
    digest_value,
    project_governed_audit,
    validate_governed_audit,
)
from semantic_guard_vnext.governance_materials import (
    GovernanceMaterialAssessmentError,
    assess_governance_materials,
    default_candidate_governance_materials,
    validate_governance_material_assessment,
)


TEXT = """Purpose: 利用者が検索結果を得る
User: 検索利用者
Scenario: 利用者が語を入力したときシステムは文書を検索する
Expected result: システムは検索結果を表示する
Acceptance criteria: 検索結果を一秒以内に表示する
Verification method: 統合試験で応答時間を測定する"""
RECORDED_AT = "2026-07-18T00:00:00Z"


class GovernanceMaterialTests(unittest.TestCase):
    def setUp(self) -> None:
        self.report = audit_requirement_relations_vnext(
            TEXT,
            analysis_mode="assurance",
        )

    def test_real_candidate_pack_and_registry_reach_public_resolvers(self) -> None:
        payload = project_governed_audit(
            self.report,
            governance_materials=default_candidate_governance_materials(),
            recorded_at=RECORDED_AT,
        )
        validate_governed_audit(payload)
        assessment = payload["governance_material_assessment"]
        h1 = assessment["engineering_rule_governance"]
        h2 = assessment["lifecycle_profile_governance"]

        self.assertEqual(h1["input_status"], "candidate_assessed")
        self.assertEqual(h1["binding_status"], "matched_candidate")
        self.assertEqual(len(h1["validated_record"]["rule_mappings"]), 11)
        self.assertEqual(h2["input_status"], "candidate_assessed")
        self.assertEqual(h2["binding_status"], "matched_candidate")
        self.assertEqual(len(h2["validated_record"]["profile_mappings"]), 10)
        self.assertEqual(
            payload["governance_resolution"]["observation_binding_status"],
            "matched",
        )
        self.assertEqual(
            payload["governance_resolution"]["h1_verdict_authority"], "none"
        )
        self.assertEqual(
            h2["validated_record"]["runtime_resolution"]["resolution_state"],
            "unresolved",
        )
        self.assertEqual(
            payload["assurance_assessment"]["workflow_disposition"], "block"
        )

    def test_candidate_content_substitution_is_reported_as_rejected(self) -> None:
        materials = default_candidate_governance_materials()
        materials["engineering_rule_pack_candidate"]["document"]["rules"][0][
            "engineering_proposition"
        ] = "substituted"
        payload = project_governed_audit(
            self.report,
            governance_materials=materials,
            recorded_at=RECORDED_AT,
        )
        axis = payload["governance_material_assessment"]["engineering_rule_governance"]
        self.assertEqual(axis["input_status"], "rejected")
        self.assertEqual(axis["binding_status"], "invalid")
        self.assertIsNone(axis["validated_record"])
        self.assertEqual(
            payload["governance_resolution"]["observation_binding_status"],
            "not_bound",
        )
        self.assertEqual(
            payload["assurance_assessment"]["workflow_disposition"], "block"
        )

    def test_material_assessment_rejects_resealed_authority_escalation(self) -> None:
        payload = project_governed_audit(
            self.report,
            governance_materials=default_candidate_governance_materials(),
            recorded_at=RECORDED_AT,
        )
        assessment = deepcopy(payload["governance_material_assessment"])
        assessment["engineering_rule_governance"]["formal_authority"] = "formal"
        assessment["assessment_digest"] = digest_value(
            {
                key: deepcopy(value)
                for key, value in assessment.items()
                if key != "assessment_digest"
            }
        )
        with self.assertRaises(GovernanceMaterialAssessmentError):
            validate_governance_material_assessment(assessment)

    def test_unknown_material_axis_is_rejected(self) -> None:
        base = project_governed_audit(self.report, recorded_at=RECORDED_AT)
        assessment = base["governance_material_assessment"]
        with self.assertRaisesRegex(
            GovernanceMaterialAssessmentError, "unknown governance material keys"
        ):
            assess_governance_materials(
                {"unknown_axis": {}},
                observation_digest=assessment["observation_digest"],
                authority_source_ids=assessment["authority_source_ids"],
                subject_scope_ref=assessment["subject_scope_ref"],
            )


if __name__ == "__main__":
    unittest.main()
