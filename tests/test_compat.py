from __future__ import annotations

import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator

from semantic_guard.compat import project_legacy_result
from semantic_guard.engine import audit_requirement_relations


COMPLETE = """Purpose: 検索APIが検索結果を p95 500ms以内で返す
User: 検索API
Scenario: 検索APIが検索要求を処理して検索結果を返す
Expected result: 検索結果を p95 500ms以内で返す
Acceptance criteria: 検索応答時間 p95 500ms 以下
Verification method: 検索結果の検索応答時間を benchmark で測定する
Evidence: 検索結果の検索応答時間 benchmark report"""


class LegacyProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        path = (
            Path(__file__).resolve().parents[1]
            / "legacy"
            / "semantic-guard-v0.1.0"
            / "schemas"
            / "audit-result.schema.json"
        )
        cls.validator = Draft202012Validator(json.loads(path.read_text(encoding="utf-8")))

    def test_projection_has_exact_legacy_top_level_and_validates(self) -> None:
        projection = project_legacy_result(
            audit_requirement_relations(
                COMPLETE, analysis_mode="conditional"
            )
        )

        self.assertEqual(
            set(projection),
            {"phase", "status", "score", "findings", "missing", "next_actions", "details"},
        )
        self.validator.validate(projection)
        self.assertEqual(
            projection["details"]["score_semantics"],
            "compatibility_ordinal_not_correctness_probability",
        )
        self.assertEqual(projection["details"]["canonical_producer_version"], "1.0.0")

    def test_projection_does_not_hide_canonical_uncertainty(self) -> None:
        text = COMPLETE.replace(
            "検索応答時間 p95 500ms 以下",
            "検索応答時間 p95 500ms 以下とは定めない",
        )
        projection = project_legacy_result(
            audit_requirement_relations(
                text, analysis_mode="conditional"
            )
        )

        self.assertNotEqual(projection["status"], "pass")
        self.assertTrue(projection["missing"])
        self.validator.validate(projection)


if __name__ == "__main__":
    unittest.main()
