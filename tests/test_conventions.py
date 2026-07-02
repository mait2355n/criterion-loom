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

    def test_expression_precision_detects_as_view_operation_blurred(self) -> None:
        result = audit_conventions("曖昧な箇所を判断材料として見る。", input_kind="document")

        self.assertEqual(result["status"], "warn")
        self.assertIn("doc.expression.as_view_operation_blurred", result["missing"])
        expression_details = result["details"]["expression_precision"]
        self.assertTrue(expression_details["operation_contracts"])
        operation_finding = next(
            finding for finding in result["findings"] if finding["rule_id"] == "doc.expression.as_view_operation_blurred"
        )
        repair = operation_finding["repair"]
        self.assertTrue(repair["needs_human_decision"])
        self.assertIn("rewrite_candidates", repair)

    def test_expression_precision_detects_inspection_contract_missing(self) -> None:
        result = audit_conventions("対象を検査する。", input_kind="document")

        self.assertEqual(result["status"], "warn")
        self.assertIn("doc.expression.inspection_contract_missing", result["missing"])
        expression_details = result["details"]["expression_precision"]
        contract = next(
            item
            for item in expression_details["operation_contracts"]
            if item["rule_id"] == "doc.expression.inspection_contract_missing"
        )
        self.assertEqual(contract["status"], "under_specified")
        self.assertIn("criterion", contract["missing_slots"])

    def test_expression_precision_accepts_inspection_with_contract(self) -> None:
        result = audit_conventions("差分を基準に照らして検査し、違反箇所を findings として返す。", input_kind="document")

        expression_missing = [rule_id for rule_id in result["missing"] if rule_id.startswith("doc.expression.")]
        self.assertEqual(expression_missing, [])
        expression_details = result["details"]["expression_precision"]
        contract = next(
            item
            for item in expression_details["operation_contracts"]
            if item["rule_id"] == "doc.expression.inspection_contract_missing"
        )
        self.assertEqual(contract["status"], "supported")

    def test_expression_precision_detects_capability_contract_missing(self) -> None:
        result = audit_conventions("資源全体を見渡し、次に何を扱うべきかを決める。", input_kind="document")

        self.assertIn("doc.expression.capability_contract_missing", result["missing"])
        expression_details = result["details"]["expression_precision"]
        contract = next(
            item
            for item in expression_details["operation_contracts"]
            if item["rule_id"] == "doc.expression.capability_contract_missing"
        )
        self.assertEqual(contract["status"], "under_specified")
        self.assertIn("input_boundary", contract["missing_slots"])
        self.assertIn("limit_or_non_guarantee", contract["missing_slots"])

    def test_expression_precision_detects_all_information_overclaim(self) -> None:
        result = audit_conventions("入力から取れる情報をすべて拾わせる。", input_kind="document")

        self.assertIn("doc.expression.capability_contract_missing", result["missing"])
        expression_details = result["details"]["expression_precision"]
        contract = next(
            item
            for item in expression_details["operation_contracts"]
            if item["rule_id"] == "doc.expression.capability_contract_missing"
        )
        self.assertEqual(contract["status"], "under_specified")
        self.assertIn("limit_or_non_guarantee", contract["missing_slots"])

    def test_expression_precision_accepts_bounded_capability_contract(self) -> None:
        result = audit_conventions(
            "指定された入力から現在の規則で検出できた候補を JSON findings として返し、網羅性は保証しない。",
            input_kind="document",
        )

        expression_missing = [rule_id for rule_id in result["missing"] if rule_id.startswith("doc.expression.")]
        self.assertEqual(expression_missing, [])
        expression_details = result["details"]["expression_precision"]
        contract = next(
            item
            for item in expression_details["operation_contracts"]
            if item["rule_id"] == "doc.expression.capability_contract_missing"
        )
        self.assertEqual(contract["status"], "supported")

    def test_expression_precision_does_not_flag_plain_english_every(self) -> None:
        result = audit_conventions(
            "Do not use it to force one internal architecture onto every repository.",
            input_kind="document",
        )

        expression_missing = [rule_id for rule_id in result["missing"] if rule_id.startswith("doc.expression.")]
        self.assertEqual(expression_missing, [])

    def test_expression_precision_does_not_flag_capability_compound_or_negated_scope(self) -> None:
        cases = [
            "形式手法や網羅的な要求検証は担当しない。",
            "全体図は有用だが、図だけでは管理できない。",
            "現在の状態。履歴全体ではない。",
        ]

        for text in cases:
            with self.subTest(text=text):
                result = audit_conventions(text, input_kind="document")
                expression_missing = [
                    rule_id
                    for rule_id in result["missing"]
                    if rule_id == "doc.expression.capability_contract_missing"
                ]
                self.assertEqual(expression_missing, [])

    def test_expression_precision_detects_mapping_contract_missing(self) -> None:
        result = audit_conventions("監査結果を資源状態、危険、次行動へ写像する。", input_kind="document")

        self.assertIn("doc.expression.mapping_contract_missing", result["missing"])
        expression_details = result["details"]["expression_precision"]
        contract = next(
            item
            for item in expression_details["operation_contracts"]
            if item["rule_id"] == "doc.expression.mapping_contract_missing"
        )
        self.assertEqual(contract["status"], "under_specified")
        self.assertIn("rule_or_condition", contract["missing_slots"])
        self.assertIn("evidence_preservation", contract["missing_slots"])

    def test_expression_precision_detects_handoff_enrichment_contract_missing(self) -> None:
        result = audit_conventions(
            "handoff item に owner と next_action を補って管理対象へ昇格させる。",
            input_kind="document",
        )

        self.assertIn("doc.expression.mapping_contract_missing", result["missing"])
        expression_details = result["details"]["expression_precision"]
        contract = next(
            item
            for item in expression_details["operation_contracts"]
            if item["rule_id"] == "doc.expression.mapping_contract_missing"
        )
        self.assertEqual(contract["status"], "under_specified")
        self.assertIn("rule_or_condition", contract["missing_slots"])

    def test_expression_precision_accepts_field_mapping_contract(self) -> None:
        result = audit_conventions(
            "findings と evidence を audit_record.fields に写し、source_audit_id を保持する。",
            input_kind="document",
        )

        expression_missing = [rule_id for rule_id in result["missing"] if rule_id.startswith("doc.expression.")]
        self.assertEqual(expression_missing, [])
        expression_details = result["details"]["expression_precision"]
        contract = next(
            item
            for item in expression_details["operation_contracts"]
            if item["rule_id"] == "doc.expression.mapping_contract_missing"
        )
        self.assertEqual(contract["status"], "supported")

    def test_expression_precision_does_not_treat_closed_loop_as_mapping(self) -> None:
        result = audit_conventions(
            "観測、監査、判断、行動を閉じた制御環として扱う。",
            input_kind="document",
        )

        expression_missing = [
            rule_id for rule_id in result["missing"] if rule_id == "doc.expression.mapping_contract_missing"
        ]
        self.assertEqual(expression_missing, [])

    def test_expression_precision_accepts_classified_findings(self) -> None:
        result = audit_conventions("問題点を分類し、指摘一覧として返す。", input_kind="document")

        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["missing"], [])

    def test_expression_precision_does_not_treat_compound_material_as_target(self) -> None:
        result = audit_conventions("未決定事項を判断材料として提示する。", input_kind="document")

        expression_missing = [rule_id for rule_id in result["missing"] if rule_id.startswith("doc.expression.")]
        self.assertEqual(expression_missing, [])

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
            ("warn", "曖昧な箇所を判断材料として見る。"),
            ("warn", "対象を検査する。"),
            ("warn", "資源全体を見渡し、次に何を扱うべきかを決める。"),
            ("warn", "入力から取れる情報をすべて拾わせる。"),
            ("warn", "監査結果を資源状態、危険、次行動へ写像する。"),
            ("warn", "handoff item に owner と next_action を補って管理対象へ昇格させる。"),
            ("pass", "判断が必要な箇所を一覧として返す。"),
            ("pass", "修正対象を検出し、該当規則ごとの指摘一覧として返す。"),
            ("pass", "要求文を受け取り、その文書から未決定事項を抽出する。"),
            ("pass", "差分を基準に照らして検査し、違反箇所を findings として返す。"),
            ("pass", "指定された入力から現在の規則で検出できた候補を JSON findings として返し、網羅性は保証しない。"),
            ("pass", "findings と evidence を audit_record.fields に写し、source_audit_id を保持する。"),
            ("pass", "形式手法や網羅的な要求検証は担当しない。"),
            ("pass", "全体図は有用だが、図だけでは管理できない。"),
        ]

        for expected, text in cases:
            with self.subTest(text=text):
                result = audit_conventions(text, input_kind="document")
                expression_missing = [rule_id for rule_id in result["missing"] if rule_id.startswith("doc.expression.")]
                actual = "warn" if expression_missing else "pass"
                self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
