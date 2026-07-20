from __future__ import annotations

import unittest

from semantic_guard.engine import audit_requirement_relations
from semantic_guard.legacy_runner import (
    BaselineCheck,
    LegacyExecution,
    LegacyObservation,
)
from semantic_guard.shadow import compare_with_legacy


COMPLETE = """Purpose: 検索APIが検索結果を p95 500ms以内で返す
User: 検索API
Scenario: 検索APIが検索要求を処理して検索結果を返す
Expected result: 検索結果を p95 500ms以内で返す
Acceptance criteria: 検索応答時間 p95 500ms 以下
Verification method: 検索結果の検索応答時間を benchmark で測定する
Evidence: 検索結果の検索応答時間 benchmark report"""


def observation(
    *,
    status: str,
    obligation_state: str = "satisfied",
    obligation_id: str = "func.verifies",
) -> LegacyObservation:
    return LegacyObservation(
        schema_version="semantic-guard-legacy-observation/v0",
        execution=LegacyExecution(
            status="completed",
            command=("legacy",),
            exit_code=0,
            stdout_valid_json=True,
            stderr="",
            baseline=BaselineCheck(status="matched", checked_files=1, mismatches=()),
        ),
        raw_legacy_result={},
        normalized_legacy_observation={
            "top_level": {"legacy_status": status, "legacy_score": 1.0},
            "relation": {
                "coverage": {"record_mode": "closed_record"},
                "obligation_checks": [
                    {
                        "obligation_id": obligation_id,
                        "status": "aligned",
                        "derivation_status": obligation_state,
                    }
                ],
            },
        },
    )


class ShadowComparisonTests(unittest.TestCase):
    def test_scope_defeater_classifies_legacy_false_satisfaction(self) -> None:
        text = COMPLETE.replace(
            "検索応答時間 p95 500ms 以下",
            "担当者によれば検索応答時間 p95 500ms 以下",
        )
        report = audit_requirement_relations(
            text, analysis_mode="conditional"
        )
        comparison = compare_with_legacy(report, observation(status="pass"))

        self.assertIn(
            "legacy_known_defect",
            {item.assessment for item in comparison.differences},
        )
        self.assertTrue(
            all(
                item.basis_kind == "constitution_invariant"
                for item in comparison.differences
                if item.assessment == "legacy_known_defect"
            )
        )

    def test_unjustified_delta_stays_unresolved(self) -> None:
        report = audit_requirement_relations(
            COMPLETE, analysis_mode="conditional"
        )
        comparison = compare_with_legacy(report, observation(status="warn"))

        self.assertGreater(comparison.unresolved_requires_review_count, 0)

    def test_unavailable_legacy_is_not_treated_as_equivalence(self) -> None:
        report = audit_requirement_relations(
            COMPLETE, analysis_mode="conditional"
        )
        unavailable = LegacyObservation(
            schema_version="semantic-guard-legacy-observation/v0",
            execution=LegacyExecution(
                status="unavailable",
                command=("legacy",),
                exit_code=None,
                stdout_valid_json=False,
                stderr="missing",
                baseline=BaselineCheck(status="matched", checked_files=1, mismatches=()),
            ),
            raw_legacy_result=None,
            normalized_legacy_observation=None,
        )

        comparison = compare_with_legacy(report, unavailable)

        self.assertEqual(comparison.differences[0].observation_delta, "execution_availability_change")
        self.assertNotEqual(comparison.differences[0].observation_delta, "equivalent")

    def test_scope_defeater_does_not_excuse_an_unaffected_obligation_delta(self) -> None:
        text = COMPLETE.replace(
            "検索応答時間 p95 500ms 以下",
            "担当者によれば検索応答時間 p95 500ms 以下",
        ).replace("User: 検索API", "User: 利用者")
        report = audit_requirement_relations(
            text, analysis_mode="conditional"
        )
        comparison = compare_with_legacy(
            report,
            observation(status="warn", obligation_id="func.performs"),
        )
        performs = next(
            item for item in comparison.differences if item.subject == "func.performs"
        )

        self.assertEqual(performs.assessment, "unresolved_requires_review")
        self.assertEqual(performs.basis_kind, "none")


if __name__ == "__main__":
    unittest.main()
