from __future__ import annotations

import unittest

from semantic_guard.records import parse_requirement_record
from semantic_guard.residual_risk import scan_residual_risks


TEMPLATE = """Purpose: 検索結果を返す
User: 検索API
Scenario: 検索APIが検索要求を処理した場合、検索結果を返す
Expected result: 検索結果を p95 500ms以内で返す
Acceptance criteria: {criterion}
Verification method: {method}
Evidence: 検索 benchmark report"""


class ResidualRiskTests(unittest.TestCase):
    def reason_codes(self, *, criterion: str, method: str) -> set[str]:
        record = parse_requirement_record(TEMPLATE.format(criterion=criterion, method=method))
        return {item.reason_code for item in scan_residual_risks(record)}

    def test_reported_speech_is_challenged(self) -> None:
        reasons = self.reason_codes(
            criterion="検索応答時間 p95 500ms 以下",
            method="担当者によれば検索応答時間を benchmark で測定する",
        )
        self.assertIn("reported_speech_present", reasons)

    def test_unadopted_quotation_is_challenged(self) -> None:
        reasons = self.reason_codes(
            criterion="検索応答時間 p95 500ms 以下",
            method="「検索応答時間を benchmark で測定する」と書かれているだけで、採用していない",
        )
        self.assertIn("metalinguistic_or_quotation_present", reasons)
        self.assertIn("non_adoption_or_proposal_present", reasons)

    def test_negation_is_scope_signal_not_defect_assertion(self) -> None:
        record = parse_requirement_record(
            TEMPLATE.format(
                criterion="検索応答時間 p95 500ms 以下とは定めない",
                method="検索応答時間を benchmark で測定する",
            )
        )
        signals = scan_residual_risks(record)
        negation = next(item for item in signals if item.reason_code == "negation_scope_present")

        self.assertEqual(negation.next_route, "morphology")
        self.assertTrue(negation.limitations)

    def test_unlabelled_text_is_preserved_as_source_aligned_signal(self) -> None:
        text = TEMPLATE.format(
            criterion="検索応答時間 p95 500ms 以下",
            method="検索応答時間を benchmark で測定する",
        ) + "\n採用状態は別文書にある。"
        record = parse_requirement_record(text)
        signal = next(
            item for item in scan_residual_risks(record) if item.reason_code == "unconsumed_relevant_span"
        )

        self.assertEqual(text[signal.start : signal.end], "採用状態は別文書にある。")

    def test_hostile_inflections_and_brackets_are_not_a_lexical_bypass(self) -> None:
        reasons = self.reason_codes(
            criterion="担当者曰く【障害時だけ検索応答時間 p95 500ms 以下を認めない】は草案の文言にすぎぬ",
            method="検索応答時間を benchmark で測定する",
        )

        self.assertTrue(
            {
                "reported_speech_present",
                "metalinguistic_or_quotation_present",
                "non_adoption_or_proposal_present",
                "negation_scope_present",
                "conditional_or_exception_scope_present",
            }
            <= reasons
        )

    def test_coordination_requests_proposition_segmentation(self) -> None:
        record = parse_requirement_record(
            TEMPLATE.format(
                criterion="検索応答時間 p95 500ms 以下",
                method="検索応答時間を測定しかつ顧客記録を削除する",
            )
        )

        self.assertIn(
            "multiple_propositions_present",
            {item.reason_code for item in scan_residual_risks(record)},
        )


if __name__ == "__main__":
    unittest.main()
