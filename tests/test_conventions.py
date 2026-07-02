from __future__ import annotations

import unittest

from semantic_guard.conventions import audit_conventions, load_conventions_catalog


class ConventionTests(unittest.TestCase):
    def test_catalog_loads_base_contract(self) -> None:
        catalog = load_conventions_catalog()

        self.assertEqual(catalog["schema_version"], "semantic-guard-conventions/v1")
        self.assertEqual(catalog["id"], "base-contract")
        self.assertTrue(catalog["rules"])

    def test_audit_conventions_detects_mcp_output_contract_gap(self) -> None:
        result = audit_conventions("MCP tool を実装し JSON result を返す。")

        self.assertEqual(result["phase"], "audit_conventions")
        self.assertEqual(result["status"], "warn")
        self.assertIn("conv.structure.versioned_shape", result["missing"])
        self.assertIn("conv.output.envelope", result["missing"])
        self.assertTrue(result["details"]["surfaces"]["mcp"])

    def test_audit_conventions_passes_non_public_note(self) -> None:
        result = audit_conventions("内部メモ: 実装方針を考える。")

        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["missing"], [])

    def test_audit_conventions_detects_record_surface_gap(self) -> None:
        result = audit_conventions("JSONL 台帳に監査記録を保存する。schema_version と evidence を持つ。")

        self.assertEqual(result["status"], "warn")
        self.assertIn("conv.record.shallow_context_surface", result["missing"])

    def test_audit_conventions_accepts_shallow_record_surface(self) -> None:
        result = audit_conventions(
            "JSONL 台帳に監査記録を保存する。schema_version を持ち、fields は record_surface, evidence, "
            "inference_status, pending_decision。type は string, object, array, boolean。"
            "record_surface は context, current_state, next_action, detail_refs を持つ。"
            "timestamp は ISO 8601 timezone 付き。evidence source を記録し、inference と pending を分ける。"
        )

        self.assertNotIn("conv.record.shallow_context_surface", result["missing"])

    def test_expression_precision_detects_blurred_sentence(self) -> None:
        result = audit_conventions("怪しい場所を試験できる内容として外に出す。", input_kind="document")

        self.assertEqual(result["status"], "warn")
        self.assertIn("doc.expression.target_blurred", result["missing"])
        self.assertIn("doc.expression.operation_blurred", result["missing"])
        self.assertIn("doc.expression.output_form_missing", result["missing"])
        expression_details = result["details"]["expression_precision"]
        self.assertIn("怪しい場所", expression_details["matched_phrases"])
        self.assertIn("doc.expression.output_form_missing", expression_details["emitted_rule_ids"])

    def test_expression_precision_accepts_operational_sentence(self) -> None:
        result = audit_conventions("不明点を抽出し、外部での判断に使える一覧として返す。", input_kind="document")

        self.assertEqual(result["status"], "pass")
        self.assertNotIn("doc.expression.output_form_missing", result["missing"])
        self.assertEqual(result["next_actions"], [])
        expression_details = result["details"]["expression_precision"]
        self.assertTrue(expression_details["surface_detected"])
        self.assertIn("一覧", expression_details["support_terms"])

    def test_expression_precision_detects_unclear_demonstrative_reference(self) -> None:
        result = audit_conventions("それを外部へ出す。", input_kind="document")

        self.assertEqual(result["status"], "warn")
        self.assertIn("doc.expression.demonstrative_reference_blurred", result["missing"])
        expression_details = result["details"]["expression_precision"]
        self.assertIn("それ", expression_details["matched_phrases"])
        self.assertEqual(expression_details["referent_resolutions"][0]["status"], "no_candidate")

    def test_expression_precision_detects_demonstrative_with_vague_head(self) -> None:
        result = audit_conventions("この内容を判断できる形にする。", input_kind="document")

        self.assertEqual(result["status"], "warn")
        self.assertIn("doc.expression.demonstrative_reference_blurred", result["missing"])
        expression_details = result["details"]["expression_precision"]
        self.assertEqual(expression_details["referent_resolutions"][0]["status"], "no_candidate")

    def test_expression_precision_accepts_demonstrative_with_named_antecedent(self) -> None:
        result = audit_conventions("未決定事項を抽出し、その一覧を JSON の findings として返す。", input_kind="document")

        expression_missing = [rule_id for rule_id in result["missing"] if rule_id.startswith("doc.expression.")]
        self.assertEqual(expression_missing, [])
        expression_details = result["details"]["expression_precision"]
        self.assertEqual(expression_details["referent_resolutions"][0]["status"], "supported")

    def test_expression_precision_accepts_demonstrative_value_with_fields(self) -> None:
        result = audit_conventions(
            "schema_version と status を読み、その値を diagnostics.result に保存する。",
            input_kind="document",
        )

        expression_missing = [rule_id for rule_id in result["missing"] if rule_id.startswith("doc.expression.")]
        self.assertEqual(expression_missing, [])
        expression_details = result["details"]["expression_precision"]
        candidates = expression_details["referent_resolutions"][0]["candidates"]
        self.assertTrue(any(candidate["strength"] == "strong" for candidate in candidates))

    def test_expression_precision_accepts_demonstrative_with_previous_line_referent(self) -> None:
        result = audit_conventions(
            "要求文を受け取る。\nその文書から未決定事項を抽出する。",
            input_kind="document",
        )

        expression_missing = [rule_id for rule_id in result["missing"] if rule_id.startswith("doc.expression.")]
        self.assertEqual(expression_missing, [])
        expression_details = result["details"]["expression_precision"]
        self.assertEqual(expression_details["referent_resolutions"][0]["status"], "supported")

    def test_expression_precision_warns_on_ambiguous_medium_referents(self) -> None:
        result = audit_conventions(
            "要求と計画を比較する。\nそれを一覧として返す。",
            input_kind="document",
        )

        self.assertIn("doc.expression.demonstrative_reference_blurred", result["missing"])
        expression_details = result["details"]["expression_precision"]
        self.assertEqual(expression_details["referent_resolutions"][0]["status"], "ambiguous")

    def test_expression_precision_detects_weak_visualization(self) -> None:
        result = audit_conventions("問題点を見える化する。", input_kind="document")

        self.assertEqual(result["status"], "warn")
        self.assertIn("doc.expression.operation_blurred", result["missing"])

    def test_expression_precision_accepts_classified_findings(self) -> None:
        result = audit_conventions("問題点を分類し、指摘一覧として返す。", input_kind="document")

        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["missing"], [])

    def test_expression_precision_suppresses_negative_examples(self) -> None:
        result = audit_conventions("悪い例: 怪しい場所を試験できる内容として外に出す。", input_kind="document")

        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["missing"], [])
        expression_details = result["details"]["expression_precision"]
        self.assertTrue(expression_details["suppressed_contexts"])

    def test_expression_precision_suppresses_demonstrative_negative_examples(self) -> None:
        result = audit_conventions("悪い例: それを外部へ出す。", input_kind="document")

        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["missing"], [])
        expression_details = result["details"]["expression_precision"]
        self.assertTrue(expression_details["suppressed_contexts"])

    def test_expression_precision_suppresses_seed_example_table(self) -> None:
        result = audit_conventions(
            "Observed wording changes used as seed examples:\n\n"
            "| Before Pattern | After Pattern | Reason |\n"
            "| --- | --- | --- |\n"
            "| `試験できる材料として外へ出す` | `退行検査できる材料として抽出する` | Ties the claim to regression checking. |\n"
            "| `修正できる` | `指定された弱点に基づいて修正する` | Names the revision basis. |\n",
            input_kind="document",
        )

        expression_missing = [rule_id for rule_id in result["missing"] if rule_id.startswith("doc.expression.")]
        self.assertEqual(expression_missing, [])
        expression_details = result["details"]["expression_precision"]
        self.assertTrue(any("seed_example_table_context" in item for item in expression_details["suppressed_contexts"]))

    def test_expression_precision_does_not_flag_normal_support_material(self) -> None:
        result = audit_conventions(
            "長い作業や公開差分で、fresh-eyes 査読を補助材料として挟むかを確認する。",
            input_kind="document",
        )

        expression_missing = [rule_id for rule_id in result["missing"] if rule_id.startswith("doc.expression.")]
        self.assertEqual(expression_missing, [])

    def test_expression_precision_does_not_match_inside_exposure_word(self) -> None:
        result = audit_conventions("未決定、不明、仮説、推測、価値判断、根拠不足を分けて露出する。", input_kind="document")

        expression_missing = [rule_id for rule_id in result["missing"] if rule_id.startswith("doc.expression.")]
        self.assertEqual(expression_missing, [])

    def test_expression_precision_challenge_set_catches_survivorship_bias(self) -> None:
        cases = [
            ("warn", "気になるところをレビューできる形で共有する。"),
            ("warn", "不確かな点を検討できる形にする。"),
            ("warn", "問題を対応できるようにする。"),
            ("warn", "弱いところを外部に共有する。"),
            ("warn", "これを判断できる形にする。"),
            ("pass", "判断が必要な箇所を一覧として返す。"),
            ("pass", "修正対象を検出し、該当規則ごとの指摘一覧として返す。"),
            ("pass", "要求文を受け取り、その文書から未決定事項を抽出する。"),
        ]

        for expected, text in cases:
            with self.subTest(text=text):
                result = audit_conventions(text, input_kind="document")
                expression_missing = [rule_id for rule_id in result["missing"] if rule_id.startswith("doc.expression.")]
                actual = "warn" if expression_missing else "pass"
                self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
