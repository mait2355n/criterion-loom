from __future__ import annotations

import hashlib
import json
import unicodedata
import unittest

from jsonschema import validate

from semantic_guard_workflow import audit_artifact_membership
from semantic_guard_workflow.artifact_membership import _compact_folded_projection
from semantic_guard_workflow.models import load_audit_result_schema


def _reference_compact_folded(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    compact = "".join(character for character in decomposed if not character.isspace())
    reordered = unicodedata.normalize("NFD", compact)
    folded = reordered.casefold()
    redecomposed = unicodedata.normalize("NFKD", folded)
    recompact = "".join(character for character in redecomposed if not character.isspace())
    return unicodedata.normalize("NFD", recompact)


class ArtifactMembershipAuditTests(unittest.TestCase):
    def test_six_dispositions_keep_membership_action_and_truth_separate(self) -> None:
        cases = [
            (
                "retain_direct",
                "安全要件: 秘密鍵とアクセストークンを成果物へ含めない。",
                ["秘密鍵とアクセストークンを成果物へ含めない。"],
                "belongs",
            ),
            (
                "retain_transformed",
                "アナタがさっき言った通り、秘密鍵とアクセストークンを成果物へ含めない。",
                ["秘密鍵とアクセストークンを成果物へ含めない。"],
                "mixed",
            ),
            (
                "relocate_to_appendix",
                "補足資料: 旧形式からの移行対応表",
                [],
                "belongs",
            ),
            (
                "relocate_to_audit_bundle",
                "監査証拠: unittest 6件 passed",
                [],
                "does_not_belong",
            ),
            (
                "exclude_from_artifact",
                "アナタの指摘に合わせて以下を直した。",
                [],
                "does_not_belong",
            ),
            (
                "hold_for_human_review",
                "これは後で残すか決める。",
                [],
                "unknown",
            ),
        ]

        for disposition, text, required, membership_status in cases:
            with self.subTest(disposition=disposition):
                result = self._audit(text, required_elements=required)
                assessment = self._only_assessment(result)

                self.assertEqual(assessment["membership_status"], membership_status)
                self.assertEqual(assessment["recommended_disposition"], disposition)
                self.assertEqual(assessment["performed_action"], "none")
                self.assertEqual(assessment["acceptance_status"], "not_assessed")
                self.assertEqual(assessment["truth_assessment"]["status"], "not_performed")
                self.assertTrue(assessment["reason_codes"])
                self.assertTrue(assessment["loss_if_applied"])
                self.assertEqual(assessment["unit_ref"]["source_range"]["start_line"], 1)

    def test_common_audit_result_schema_accepts_membership_result(self) -> None:
        result = self._audit(
            "安全要件: 秘密鍵を成果物へ含めない。",
            required_elements=["秘密鍵を成果物へ含めない。"],
        )

        validate(instance=result, schema=load_audit_result_schema())

    def test_context_excision_requires_a_complete_contract_and_direct_units(self) -> None:
        direct = self._audit(
            "安全要件: 秘密鍵を成果物へ含めない。",
            required_elements=["秘密鍵を成果物へ含めない。"],
        )
        mixed = self._audit(
            "アナタがさっき言った通り、秘密鍵を成果物へ含めない。",
            required_elements=["秘密鍵を成果物へ含めない。"],
        )

        direct_check = direct["details"]["context_excision_assessment"]
        mixed_check = mixed["details"]["context_excision_assessment"]
        self.assertEqual(direct_check["status"], "supported_under_declared_contract")
        self.assertTrue(direct_check["excision_ready"])
        self.assertFalse(direct_check["counterfactual_regeneration_performed"])
        self.assertEqual(mixed_check["status"], "not_supported")
        self.assertFalse(mixed_check["excision_ready"])
        self.assertTrue(mixed_check["context_dependency_candidates"])

    def test_runtime_delivery_context_exact_regression_is_not_retained_direct(self) -> None:
        text = (
            "指定出力先への保存は実行環境の書き込み制約により未実施。"
            "本文はこの応答へ保持する。"
        )
        result = self._audit(text, required_elements=[text])
        assessment = self._only_assessment(result)

        self.assertEqual(assessment["membership_status"], "mixed")
        self.assertEqual(assessment["recommended_disposition"], "retain_transformed")
        self.assertIn("runtime_delivery_context", assessment["reason_codes"])
        self.assertEqual(
            result["details"]["context_excision_assessment"]["context_dependency_candidates"],
            [assessment["unit_ref"]],
        )

    def test_saved_runtime_delivery_regressions_are_not_retained_direct(self) -> None:
        cases = (
            "災害・警報が多く、AI独立項目の過半配分より人命・避難を優先した。指定出力先への保存は読み取り専用制約に拒否され、未保存である。",
            "保存状態: 指定先への書込みは、実行環境が読取専用のため拒否され、未保存。",
            "出力: 指定先は実行環境の読取専用制約により書込不能。本文はこの応答へ保持する。",
            "指定出力先への上書きは実行環境の読取専用制約で拒否され、既存の素材一覧だけの仮本文が残った。この応答のMarkdown本文が生成成果である。",
        )

        for text in cases:
            with self.subTest(text=text):
                result = self._audit(text, required_elements=[text])
                assessment = self._only_assessment(result)

                self.assertEqual(assessment["membership_status"], "mixed")
                self.assertEqual(assessment["recommended_disposition"], "retain_transformed")
                self.assertIn("runtime_delivery_context", assessment["reason_codes"])
                self.assertNotEqual(assessment["recommended_disposition"], "retain_direct")

    def test_runtime_delivery_context_paraphrases_share_the_same_invariant(self) -> None:
        cases = (
            (
                "実行環境ではファイルに保存できなかったため、"
                "本文はこの回答に記載する。"
            ),
            (
                "出力先への書き込みは権限制約により行えなかった。"
                "成果物はチャット上で提示する。"
            ),
            "保存処理は未完了だったため、この応答に内容を載せる。",
        )

        for text in cases:
            with self.subTest(text=text):
                result = self._audit(text, required_elements=[text])
                assessment = self._only_assessment(result)

                self.assertEqual(assessment["membership_status"], "mixed")
                self.assertEqual(assessment["recommended_disposition"], "retain_transformed")
                self.assertIn("runtime_delivery_context", assessment["reason_codes"])

    def test_conversation_dependency_paraphrases_are_not_retained_direct(self) -> None:
        cases = (
            "そうだね。公開前に機密情報を除く。",
            "そうですね、公開前に機密情報を除く。",
            "前に話したとおり、公開前に機密情報を除く。",
            "以前話していた通り、公開前に機密情報を除く。",
            "その方針で進める。",
            "この進め方で進めていきます。",
            "こちらで確認したところ、出力は妥当だった。",
            "こっちで確認した感じ、出力は妥当だった。",
        )

        for text in cases:
            with self.subTest(text=text):
                result = self._audit(text, required_elements=[text])
                assessment = self._only_assessment(result)

                self.assertEqual(assessment["membership_status"], "mixed")
                self.assertEqual(assessment["recommended_disposition"], "retain_transformed")
                self.assertIn("conversation_dependency", assessment["reason_codes"])

    def test_quotation_and_example_counterevidence_prevents_automatic_exclusion(self) -> None:
        cases = (
            "「そうだね。公開前に機密情報を除く。」",
            "例示: その方針で進める。",
            "悪い例: こちらで確認したところ、とだけ書く。",
        )

        for text in cases:
            with self.subTest(text=text):
                assessment = self._only_assessment(self._audit(text))

                self.assertEqual(assessment["membership_status"], "unknown")
                self.assertEqual(assessment["recommended_disposition"], "hold_for_human_review")
                self.assertIn("quotation_or_example", assessment["reason_codes"])

    def test_persistent_storage_contracts_and_storage_facts_remain_direct(self) -> None:
        cases = (
            "保存に失敗した場合はエラーを返す。",
            "読み取り専用の保存先への書き込みが拒否された場合は、エラーを返す。",
            "成果物の保存先は /var/lib/semantic-guard/report.md である。",
            "本文は指定された保存先へ保存される。",
        )

        for text in cases:
            with self.subTest(text=text):
                assessment = self._only_assessment(
                    self._audit(text, required_elements=[text])
                )

                self.assertEqual(assessment["membership_status"], "belongs")
                self.assertEqual(assessment["recommended_disposition"], "retain_direct")
                self.assertNotIn("runtime_delivery_context", assessment["reason_codes"])
                self.assertNotIn("conversation_dependency", assessment["reason_codes"])

    def test_evaluation_context_does_not_authorize_publication(self) -> None:
        result = self._audit(
            "内部比較では旧版より短い。",
            evaluation_context=["内部比較では旧版より短い。"],
        )
        assessment = self._only_assessment(result)

        self.assertEqual(assessment["membership_status"], "unknown")
        self.assertEqual(assessment["recommended_disposition"], "hold_for_human_review")
        self.assertIn("evaluation_context_is_not_publication_authority", assessment["ambiguity_reasons"])

    def test_evaluation_context_overrides_heuristic_appendix_routing(self) -> None:
        value = "補足資料: 内部比較結果"
        result = self._audit(value, evaluation_context=[value])
        assessment = self._only_assessment(result)

        self.assertEqual(assessment["recommended_disposition"], "hold_for_human_review")
        self.assertIn("evaluation_context_is_not_publication_authority", assessment["ambiguity_reasons"])

    def test_audit_only_role_can_coexist_with_body_prohibition(self) -> None:
        value = "監査証拠: unittest 6件 passed"
        result = self._audit(
            value,
            prohibited_elements=[value],
            audit_only_context=[value],
        )
        assessment = self._only_assessment(result)

        self.assertEqual(result["details"]["artifact_contract"]["contract_status"], "complete")
        self.assertEqual(assessment["target_role"], "audit_bundle")
        self.assertEqual(assessment["recommended_disposition"], "relocate_to_audit_bundle")

    def test_non_exportable_values_are_not_echoed_into_audit_output(self) -> None:
        sensitive = "API token: top-secret-value"
        result = self._audit(sensitive, non_exportable_context=[sensitive])
        serialized = json.dumps(result, ensure_ascii=False)
        assessment = self._only_assessment(result)

        self.assertNotIn(sensitive, serialized)
        self.assertEqual(assessment["recommended_disposition"], "exclude_from_artifact")
        self.assertEqual(assessment["excerpt"], "[non-exportable matched content omitted]")
        self.assertIsNone(assessment["unit_ref"]["content_hash"])
        self.assertEqual(assessment["unit_ref"]["content_hash_status"], "withheld_non_exportable")
        projection = result["details"]["artifact_contract"]["context_projection"]
        self.assertEqual(
            projection["non_exportable_context"][0]["value_exposure"],
            "redacted_non_exportable",
        )
        self.assertNotIn("value_length", projection["non_exportable_context"][0])

    def test_short_non_exportable_values_use_length_unrestricted_matching(self) -> None:
        for sensitive in ("PIN", "OTP", "鍵"):
            with self.subTest(sensitive=sensitive):
                result = self._audit(sensitive, non_exportable_context=[sensitive])
                serialized = json.dumps(result, ensure_ascii=False)
                assessment = self._only_assessment(result)

                self.assertNotIn(sensitive, serialized)
                self.assertEqual(assessment["recommended_disposition"], "exclude_from_artifact")
                self.assertEqual(assessment["excerpt"], "[non-exportable matched content omitted]")
                self.assertIsNone(assessment["unit_ref"]["content_hash"])

    def test_unicode_equivalent_non_exportable_value_is_withheld(self) -> None:
        sensitive_nfc = "café"
        sensitive_nfd = unicodedata.normalize("NFD", sensitive_nfc)
        result = self._audit(
            sensitive_nfd,
            purpose=f"Explain {sensitive_nfd}",
            non_exportable_context=[sensitive_nfc],
        )
        serialized = json.dumps(result, ensure_ascii=False)
        assessment = self._only_assessment(result)

        self.assertNotIn(sensitive_nfc, unicodedata.normalize("NFC", serialized))
        self.assertNotIn(sensitive_nfd, serialized)
        self.assertEqual(assessment["recommended_disposition"], "exclude_from_artifact")
        self.assertEqual(assessment["unit_ref"]["content_hash_status"], "withheld_non_exportable")
        self.assertEqual(
            result["details"]["artifact_contract"]["purpose"]["value_exposure"],
            "redacted_non_exportable",
        )

    def test_unicode_combining_sequence_split_by_whitespace_is_withheld(self) -> None:
        sensitive = "é"
        result = self._audit("e \u0301", non_exportable_context=[sensitive])
        serialized = json.dumps(result, ensure_ascii=False)
        assessment = self._only_assessment(result)

        self.assertNotIn(sensitive, unicodedata.normalize("NFC", serialized))
        self.assertIsNone(assessment["unit_ref"]["content_hash"])
        self.assertIn("non_exportable_split_variant_match", assessment["reason_codes"])
        self.assertFalse(result["details"]["context_excision_assessment"]["excision_ready"])

    def test_unicode_compatibility_ligature_is_withheld(self) -> None:
        sensitive = "office"
        result = self._audit("oﬃce", non_exportable_context=[sensitive])
        serialized = json.dumps(result, ensure_ascii=False)
        assessment = self._only_assessment(result)

        self.assertNotIn(sensitive, serialized.casefold())
        self.assertNotIn("oﬃce", serialized)
        self.assertEqual(assessment["excerpt"], "[non-exportable matched content omitted]")
        self.assertIsNone(assessment["unit_ref"]["content_hash"])
        self.assertEqual(assessment["recommended_disposition"], "exclude_from_artifact")
        self.assertFalse(result["details"]["context_excision_assessment"]["excision_ready"])

    def test_unicode_combining_sequence_split_across_contract_and_body_is_withheld(self) -> None:
        sensitive = "é"
        result = self._audit(
            "\u0301",
            intended_use="e",
            non_exportable_context=[sensitive],
        )
        serialized = json.dumps(result, ensure_ascii=False)
        assessment = self._only_assessment(result)

        self.assertNotIn(sensitive, unicodedata.normalize("NFC", serialized))
        self.assertEqual(
            result["details"]["artifact_contract"]["intended_use"]["value_exposure"],
            "redacted_non_exportable",
        )
        self.assertIsNone(assessment["unit_ref"]["content_hash"])
        self.assertIn("non_exportable_split_variant_match", assessment["reason_codes"])

    def test_unicode_combining_marks_reorder_across_source_records(self) -> None:
        sensitive = unicodedata.normalize("NFC", "e\u0323\u0301")
        result = self._audit(
            "\u0323",
            intended_use="e\u0301",
            non_exportable_context=[sensitive],
        )
        serialized = json.dumps(result, ensure_ascii=False)
        assessment = self._only_assessment(result)

        self.assertNotIn(
            unicodedata.normalize("NFD", sensitive),
            unicodedata.normalize("NFD", serialized),
        )
        self.assertIsNone(assessment["unit_ref"]["content_hash"])
        self.assertFalse(result["details"]["context_excision_assessment"]["excision_ready"])

    def test_unicode_casefold_expansion_reorders_across_source_records(self) -> None:
        for trailing_mark in ("\u0300", "\u0301", "\u0315", "\u0323"):
            with self.subTest(trailing_mark=hex(ord(trailing_mark))):
                sensitive = f"\u0345{trailing_mark}"
                result = self._audit(
                    trailing_mark,
                    intended_use="\u0345",
                    non_exportable_context=[sensitive],
                )
                assessment = self._only_assessment(result)
                intended_use = result["details"]["artifact_contract"]["intended_use"]

                self.assertEqual(intended_use["value_exposure"], "redacted_non_exportable")
                self.assertEqual(assessment["excerpt"], "[non-exportable matched content omitted]")
                self.assertIsNone(assessment["unit_ref"]["content_hash"])
                self.assertIn("non_exportable_split_variant_match", assessment["reason_codes"])
                self.assertFalse(result["details"]["context_excision_assessment"]["excision_ready"])

    def test_projection_fold_is_split_invariant_for_ypogegrammeni_family(self) -> None:
        family = ["\u0345"] + [
            chr(codepoint)
            for codepoint in range(0x1F00, 0x2000)
            if "\u0345" in unicodedata.normalize("NFD", chr(codepoint))
        ]
        self.assertGreater(len(family), 1)

        for family_character in family:
            for trailing_mark in ("\u0300", "\u0301", "\u0315", "\u0323"):
                sensitive = f"x{family_character}{trailing_mark}y"
                expected = _reference_compact_folded(sensitive)
                for split_at in range(1, len(sensitive)):
                    source_ids = ["left"] * split_at + ["right"] * (len(sensitive) - split_at)
                    actual_characters, actual_source_ids = _compact_folded_projection(
                        list(sensitive),
                        source_ids,
                    )
                    with self.subTest(
                        family_character=hex(ord(family_character)),
                        trailing_mark=hex(ord(trailing_mark)),
                        split_at=split_at,
                    ):
                        self.assertEqual("".join(actual_characters), expected)
                        self.assertEqual(
                            "".join(
                                character
                                for character, source_id in zip(
                                    actual_characters,
                                    actual_source_ids,
                                    strict=True,
                                )
                                if source_id == "left"
                            ),
                            _reference_compact_folded(sensitive[:split_at]),
                        )
                        self.assertEqual(
                            "".join(
                                character
                                for character, source_id in zip(
                                    actual_characters,
                                    actual_source_ids,
                                    strict=True,
                                )
                                if source_id == "right"
                            ),
                            _reference_compact_folded(sensitive[split_at:]),
                        )

    def test_non_exportable_value_matching_derived_content_hash_is_withheld(self) -> None:
        body = "Required operational body."
        sensitive = f"sha256:{hashlib.sha256(body.encode('utf-8')).hexdigest()}"
        result = self._audit(
            body,
            required_elements=[body],
            non_exportable_context=[sensitive],
        )
        serialized = json.dumps(result, ensure_ascii=False)
        assessment = self._only_assessment(result)

        self.assertNotIn(sensitive, serialized)
        self.assertEqual(assessment["excerpt"], "[non-exportable matched content omitted]")
        self.assertIsNone(assessment["unit_ref"]["content_hash"])
        self.assertEqual(assessment["unit_ref"]["content_hash_status"], "withheld_non_exportable")
        self.assertIn("non_exportable_derived_output_match", assessment["reason_codes"])
        self.assertEqual(assessment["recommended_disposition"], "hold_for_human_review")
        self.assertFalse(result["details"]["context_excision_assessment"]["excision_ready"])

    def test_non_exportable_value_spanning_body_to_content_hash_is_withheld(self) -> None:
        body = "Body-to-hash boundary tail."
        content_hash = f"sha256:{hashlib.sha256(body.encode('utf-8')).hexdigest()}"
        sensitive = f"{body[-6:]}{content_hash[:12]}"
        result = self._audit(body, non_exportable_context=[sensitive])
        serialized = json.dumps(result, ensure_ascii=False)
        assessment = self._only_assessment(result)

        self.assertNotIn(sensitive, serialized)
        self.assertEqual(assessment["excerpt"], "[non-exportable matched content omitted]")
        self.assertIsNone(assessment["unit_ref"]["content_hash"])
        self.assertEqual(assessment["unit_ref"]["content_hash_status"], "withheld_non_exportable")
        self.assertIn("non_exportable_split_variant_match", assessment["reason_codes"])
        self.assertFalse(result["details"]["context_excision_assessment"]["excision_ready"])

    def test_non_exportable_value_spanning_adjacent_content_hashes_is_withheld(self) -> None:
        left = "First hash-boundary body."
        right = "Second hash-boundary body."
        left_hash = f"sha256:{hashlib.sha256(left.encode('utf-8')).hexdigest()}"
        right_hash = f"sha256:{hashlib.sha256(right.encode('utf-8')).hexdigest()}"
        sensitive = f"{left_hash[-12:]}{right_hash[:12]}"
        result = self._audit(
            f"{left}\n\n{right}",
            non_exportable_context=[sensitive],
        )
        serialized = json.dumps(result, ensure_ascii=False)
        assessments = result["details"]["assessments"]

        self.assertNotIn(sensitive, serialized)
        self.assertEqual(len(assessments), 2)
        self.assertTrue(
            all(item["excerpt"] == "[non-exportable matched content omitted]" for item in assessments)
        )
        self.assertTrue(all(item["unit_ref"]["content_hash"] is None for item in assessments))
        self.assertTrue(
            all("non_exportable_split_variant_match" in item["reason_codes"] for item in assessments)
        )
        self.assertFalse(result["details"]["context_excision_assessment"]["excision_ready"])

    def test_non_exportable_phrase_spanning_units_taints_every_intersection(self) -> None:
        left = "alpha-sensitive-fragment"
        right = "beta-sensitive-fragment"
        sensitive = f"{left}\n\n{right}"
        result = self._audit(sensitive, non_exportable_context=[sensitive])
        serialized = json.dumps(result, ensure_ascii=False)
        assessments = result["details"]["assessments"]

        self.assertEqual(len(assessments), 2)
        self.assertNotIn(left, serialized)
        self.assertNotIn(right, serialized)
        self.assertTrue(
            all(item["excerpt"] == "[non-exportable matched content omitted]" for item in assessments)
        )
        self.assertTrue(all(item["unit_ref"]["content_hash"] is None for item in assessments))
        self.assertTrue(
            all("non_exportable_split_variant_match" in item["reason_codes"] for item in assessments)
        )

    def test_non_exportable_value_split_without_declared_whitespace_is_withheld(self) -> None:
        left = "alpha-sensitive"
        right = "beta-sensitive"
        sensitive = f"{left}{right}"
        result = self._audit(
            f"{left}\n\n{right}",
            purpose=left,
            audience=right,
            non_exportable_context=[sensitive],
        )
        serialized = json.dumps(result, ensure_ascii=False)
        assessments = result["details"]["assessments"]

        self.assertNotIn(left, serialized)
        self.assertNotIn(right, serialized)
        self.assertTrue(all(item["unit_ref"]["content_hash"] is None for item in assessments))
        self.assertTrue(
            all("non_exportable_split_variant_match" in item["reason_codes"] for item in assessments)
        )
        self.assertFalse(result["details"]["context_excision_assessment"]["excision_ready"])
        contract = result["details"]["artifact_contract"]
        self.assertEqual(contract["purpose"]["value_exposure"], "redacted_non_exportable")
        self.assertEqual(contract["audience"]["value_exposure"], "redacted_non_exportable")

    def test_non_exportable_value_split_across_contract_and_body_is_withheld(self) -> None:
        left = "contract-sensitive-fragment"
        right = "body-sensitive-fragment"
        result = self._audit(
            right,
            intended_use=left,
            non_exportable_context=[f"{left}{right}"],
        )
        serialized = json.dumps(result, ensure_ascii=False)
        assessment = self._only_assessment(result)

        self.assertNotIn(left, serialized)
        self.assertNotIn(right, serialized)
        self.assertEqual(
            result["details"]["artifact_contract"]["intended_use"]["value_exposure"],
            "redacted_non_exportable",
        )
        self.assertIsNone(assessment["unit_ref"]["content_hash"])
        self.assertIn("non_exportable_split_variant_match", assessment["reason_codes"])
        self.assertFalse(result["details"]["context_excision_assessment"]["excision_ready"])

    def test_non_exportable_value_split_inside_one_unit_is_withheld(self) -> None:
        sensitive = "alphabeta"
        result = self._audit("alpha beta", non_exportable_context=[sensitive])
        serialized = json.dumps(result, ensure_ascii=False)
        assessment = self._only_assessment(result)

        self.assertNotIn("alpha beta", serialized)
        self.assertIsNone(assessment["unit_ref"]["content_hash"])
        self.assertIn("non_exportable_split_variant_match", assessment["reason_codes"])

    def test_non_exportable_split_uses_the_same_line_break_family_as_segmentation(self) -> None:
        sensitive = "alphabeta"
        for separator in ("\r", "\v", "\f", "\x1c", "\x1d", "\x1e", "\x85", "\u2028", "\u2029"):
            with self.subTest(separator=repr(separator)):
                result = self._audit(f"alpha{separator}beta", non_exportable_context=[sensitive])
                serialized = json.dumps(result, ensure_ascii=False)

                self.assertNotIn("alpha", serialized)
                self.assertNotIn("beta", serialized)
                self.assertTrue(
                    all(
                        item["unit_ref"]["content_hash_status"] == "withheld_non_exportable"
                        for item in result["details"]["assessments"]
                    )
                )

    def test_non_exportable_value_mixed_with_material_is_transformed_not_discarded(self) -> None:
        result = self._audit(
            "Use alpha-secret only in staging.",
            non_exportable_context=["alpha-secret"],
        )
        assessment = self._only_assessment(result)

        self.assertEqual(assessment["membership_status"], "mixed")
        self.assertEqual(assessment["recommended_disposition"], "retain_transformed")
        self.assertIn(
            "non_exportable_value_mixed_with_potentially_retainable_content",
            assessment["ambiguity_reasons"],
        )

    def test_non_exportable_identifier_is_replaced_and_blocks_contract(self) -> None:
        sensitive = "marker-secret-id"
        result = audit_artifact_membership(
            "通常の本文。",
            artifact_id=sensitive,
            artifact_kind="guide",
            purpose="案内を渡す",
            audience="運用担当者",
            intended_use="公開可否を判断する",
            non_exportable_context=[sensitive],
        )
        serialized = json.dumps(result, ensure_ascii=False)

        self.assertNotIn(sensitive, serialized)
        self.assertEqual(result["status"], "block")
        self.assertEqual(result["details"]["artifact_contract"]["contract_status"], "conflicted")
        self.assertEqual(
            result["details"]["artifact_contract"]["artifact_ref"]["entity_id"],
            f"{result['details']['unit_identity_policy']['audit_snapshot_id']}.artifact.non-exportable-id",
        )
        self.assertTrue(
            all(
                assessment["recommended_disposition"] == "hold_for_human_review"
                for assessment in result["details"]["assessments"]
            )
        )
        repeated = audit_artifact_membership(
            "通常の本文。",
            artifact_id=sensitive,
            artifact_kind="guide",
            purpose="案内を渡す",
            audience="運用担当者",
            intended_use="公開可否を判断する",
            non_exportable_context=[sensitive],
        )
        self.assertNotEqual(
            result["details"]["artifact_contract"]["artifact_ref"]["entity_id"],
            repeated["details"]["artifact_contract"]["artifact_ref"]["entity_id"],
        )
        self.assertEqual(
            result["details"]["artifact_contract"]["artifact_ref"]["identity_stability"],
            "withheld_non_exportable",
        )
        identifier_conflict = next(
            item
            for item in result["details"]["artifact_contract"]["context_projection"]["conflicts"]
            if item["kind"] == "public_identifier_vs_non_exportable"
        )
        snapshot_id = result["details"]["unit_identity_policy"]["audit_snapshot_id"]
        self.assertTrue(identifier_conflict["left_ref"].startswith(snapshot_id))
        self.assertTrue(identifier_conflict["right_ref"].startswith(snapshot_id))
        self.assertEqual(identifier_conflict["left_path"], "artifact_contract.artifact_id")
        self.assertEqual(identifier_conflict["right_zone"], "non_exportable_context")

        multi_value_result = audit_artifact_membership(
            "通常の本文。",
            artifact_id=sensitive,
            artifact_kind="guide",
            purpose="案内を渡す",
            audience="運用担当者",
            intended_use="公開可否を判断する",
            non_exportable_context=["first-unrelated-value", sensitive],
        )
        multi_value_conflict = next(
            item
            for item in multi_value_result["details"]["artifact_contract"]["context_projection"]["conflicts"]
            if item["kind"] == "public_identifier_vs_non_exportable"
            and item["left_path"] == "artifact_contract.artifact_id"
        )
        multi_value_snapshot_id = multi_value_result["details"]["unit_identity_policy"]["audit_snapshot_id"]
        self.assertEqual(
            multi_value_conflict["right_ref"],
            f"{multi_value_snapshot_id}.contract.non-exportable.002",
        )

        kind_result = audit_artifact_membership(
            "通常の本文。",
            artifact_id="artifact.guide",
            artifact_kind=sensitive,
            purpose="案内を渡す",
            audience="運用担当者",
            intended_use="公開可否を判断する",
            non_exportable_context=[sensitive],
        )
        kind_serialized = json.dumps(kind_result, ensure_ascii=False)
        self.assertNotIn(sensitive, kind_serialized)
        self.assertEqual(kind_result["status"], "block")
        self.assertEqual(kind_result["details"]["artifact_contract"]["artifact_kind"], "non-exportable-kind")

    def test_required_and_non_exportable_conflict_blocks_disposition(self) -> None:
        value = "内部接続文字列を掲載する"
        result = self._audit(
            value,
            required_elements=[value],
            non_exportable_context=[value],
        )
        assessment = self._only_assessment(result)

        self.assertEqual(result["status"], "block")
        self.assertEqual(result["details"]["artifact_contract"]["contract_status"], "conflicted")
        self.assertEqual(assessment["membership_status"], "unknown")
        self.assertEqual(assessment["recommended_disposition"], "hold_for_human_review")

    def test_context_zone_conflicts_block_even_when_value_is_absent_from_body(self) -> None:
        value = "内部比較結果"
        cases = [
            {"publishable_context": [value], "non_exportable_context": [value]},
            {"publishable_context": [value], "audit_only_context": [value]},
            {"publishable_context": [value], "prohibited_elements": [value]},
            {"audit_only_context": [value], "non_exportable_context": [value]},
        ]

        for contract in cases:
            with self.subTest(contract=contract):
                result = self._audit("安全な運用案内を渡す。", **contract)
                assessment = self._only_assessment(result)

                self.assertEqual(result["status"], "block")
                self.assertEqual(result["details"]["artifact_contract"]["contract_status"], "conflicted")
                self.assertEqual(assessment["recommended_disposition"], "hold_for_human_review")
                self.assertFalse(result["details"]["context_excision_assessment"]["excision_ready"])

    def test_non_exportable_safety_meaning_is_held_instead_of_discarded(self) -> None:
        warning = "Safety warning: token alpha-secret must never be published."
        result = self._audit(warning, non_exportable_context=[warning])
        assessment = self._only_assessment(result)

        self.assertEqual(assessment["membership_status"], "unknown")
        self.assertEqual(assessment["recommended_disposition"], "hold_for_human_review")
        self.assertIn(
            "non_exportable_content_has_retention_countercondition",
            assessment["ambiguity_reasons"],
        )

    def test_weak_single_term_overlap_never_authorizes_exclusion_or_standalone_support(self) -> None:
        production = self._audit(
            "Production deployment guide.",
            non_exportable_context=["production database password xyz"],
        )
        short = self._audit(
            "安全",
            purpose="安全な運用案内を渡す",
        )

        production_assessment = self._only_assessment(production)
        short_assessment = self._only_assessment(short)
        self.assertEqual(production_assessment["recommended_disposition"], "hold_for_human_review")
        self.assertNotIn("non_exportable_context_match", production_assessment["reason_codes"])
        self.assertEqual(short_assessment["recommended_disposition"], "hold_for_human_review")
        self.assertFalse(short["details"]["context_excision_assessment"]["excision_ready"])

    def test_boundary_fields_do_not_authorize_body_membership(self) -> None:
        cases = (
            {"purpose": "Operational objective"},
            {"audience": "Operations team"},
            {"intended_use": "Publication review"},
        )
        for override in cases:
            with self.subTest(override=override):
                value = next(iter(override.values()))
                result = self._audit(value, **override)
                assessment = self._only_assessment(result)

                self.assertEqual(assessment["membership_status"], "unknown")
                self.assertEqual(assessment["recommended_disposition"], "hold_for_human_review")
                self.assertFalse(result["details"]["context_excision_assessment"]["excision_ready"])

    def test_bare_string_contract_collection_is_rejected(self) -> None:
        with self.assertRaisesRegex(TypeError, "sequences of strings"):
            self._audit("本文", non_exportable_context="secret")

    def test_missing_contract_holds_every_unit_and_never_authorizes_exclusion(self) -> None:
        result = audit_artifact_membership("アナタの指摘に合わせて直した。")
        assessment = self._only_assessment(result)

        self.assertEqual(result["status"], "block")
        self.assertEqual(assessment["recommended_disposition"], "hold_for_human_review")
        self.assertFalse(result["details"]["execution_policy"]["automatic_changes_authorized"])
        review_point = result["details"]["human_review_points"][0]
        self.assertIn("disposition_options", review_point)
        self.assertIn("target_role_options", review_point)
        self.assertIn("hold_for_human_review", review_point["disposition_options"])
        self.assertNotIn("defer", review_point["disposition_options"])
        allowed_pairs = {
            (item["disposition"], tuple(item["target_roles"]))
            for item in review_point["allowed_outcomes"]
        }
        self.assertEqual(
            allowed_pairs,
            {
                ("retain_direct", ("body",)),
                ("retain_transformed", ("body",)),
                ("relocate_to_appendix", ("appendix",)),
                ("relocate_to_audit_bundle", ("audit_bundle",)),
                ("exclude_from_artifact", ("none",)),
                ("hold_for_human_review", ("undecided",)),
            },
        )

    def test_content_identity_and_placement_identity_are_separate(self) -> None:
        result = self._audit("同じ断片。\n\n同じ断片。")
        first, second = result["details"]["assessments"]

        self.assertNotEqual(first["unit_ref"]["entity_id"], second["unit_ref"]["entity_id"])
        self.assertNotEqual(
            first["unit_ref"]["placement"]["placement_id"],
            second["unit_ref"]["placement"]["placement_id"],
        )
        self.assertEqual(first["unit_ref"]["content_hash"], second["unit_ref"]["content_hash"])
        self.assertEqual(first["unit_ref"]["identity_scope"], "current_audit_snapshot_only")
        self.assertFalse(result["details"]["unit_identity_policy"]["durable_unit_identity_assigned"])
        self.assertEqual(result["details"]["unit_identity_policy"]["reuse_across_runs"], "forbidden")

    def test_snapshot_namespace_prevents_cross_result_local_id_collisions(self) -> None:
        first = self._audit("同じ断片。", required_elements=["別の必須要素。"])
        second = self._audit("同じ断片。", required_elements=["別の必須要素。"])

        first_policy = first["details"]["unit_identity_policy"]
        second_policy = second["details"]["unit_identity_policy"]
        first_unit = self._only_assessment(first)
        second_unit = self._only_assessment(second)
        self.assertNotEqual(first_policy["audit_snapshot_id"], second_policy["audit_snapshot_id"])
        self.assertTrue(first_policy["caller_artifact_identity_is_separate"])
        self.assertEqual(
            first_policy["namespaced_local_reference_kinds"],
            ["contract_record", "unit_placement", "human_review_point"],
        )
        self.assertNotEqual(first_unit["unit_ref"]["entity_id"], second_unit["unit_ref"]["entity_id"])
        self.assertTrue(
            first_unit["unit_ref"]["entity_id"].startswith(first_policy["audit_snapshot_id"])
        )
        self.assertNotEqual(
            first_unit["human_review_point_ref"],
            second_unit["human_review_point_ref"],
        )
        self.assertNotEqual(
            first["details"]["artifact_contract"]["required_elements"][0]["entity_id"],
            second["details"]["artifact_contract"]["required_elements"][0]["entity_id"],
        )
        self.assertNotEqual(
            first["details"]["artifact_contract"]["purpose"]["entity_id"],
            second["details"]["artifact_contract"]["purpose"]["entity_id"],
        )

    def test_structural_units_preserve_actual_ranges_and_kinds(self) -> None:
        result = self._audit(
            "# 表\n\n| 列 | 値 |\n| --- | --- |\n| A | B |\n\n[^note]: 監査注記"
        )
        table, footnote = result["details"]["assessments"]

        self.assertEqual(table["unit_ref"]["unit_kind"], "table")
        self.assertEqual(table["unit_ref"]["source_range"], {"start_line": 1, "end_line": 5})
        snapshot_id = result["details"]["unit_identity_policy"]["audit_snapshot_id"]
        self.assertEqual(
            table["unit_ref"]["placement"]["parent_ref"],
            f"{snapshot_id}.section.line-1",
        )
        self.assertEqual(footnote["unit_ref"]["unit_kind"], "footnote")
        self.assertEqual(footnote["unit_ref"]["source_range"], {"start_line": 7, "end_line": 7})

    def _audit(self, text: str, **overrides: object) -> dict[str, object]:
        arguments: dict[str, object] = {
            "artifact_id": "artifact.guide",
            "artifact_kind": "guide",
            "purpose": "安全な運用案内を渡す",
            "audience": "運用担当者",
            "intended_use": "公開可否と運用手順を判断する",
        }
        arguments.update(overrides)
        return audit_artifact_membership(text, **arguments)

    def _only_assessment(self, result: dict[str, object]) -> dict[str, object]:
        assessments = result["details"]["assessments"]
        self.assertEqual(len(assessments), 1)
        return assessments[0]


if __name__ == "__main__":
    unittest.main()
