from __future__ import annotations

import unittest

from semantic_guard_workflow.assertion_context import find_field_assertion


class AssertionContextTests(unittest.TestCase):
    def test_rejects_japanese_field_absence_without_rejecting_negative_outcome(self) -> None:
        absent = find_field_assertion("受入基準は定めない。", ["受入基準"])
        criterion = find_field_assertion("受入基準: 未認証利用者には機密情報を表示しない。", ["受入基準"])

        self.assertIsNotNone(absent)
        self.assertEqual(absent.status, "rejected")
        self.assertEqual(absent.reason, "explicit_negation")
        self.assertIsNotNone(criterion)
        self.assertEqual(criterion.status, "present")
        self.assertEqual(criterion.reason, "asserted_field_value")

    def test_rejects_english_field_absence_without_rejecting_bounded_evidence(self) -> None:
        absent = find_field_assertion("Evidence will not be retained.", ["evidence"])
        evidence = find_field_assertion("Evidence: retain logs without personal data.", ["evidence", "log"])

        self.assertIsNotNone(absent)
        self.assertEqual(absent.status, "rejected")
        self.assertIsNotNone(evidence)
        self.assertEqual(evidence.status, "present")

    def test_rejects_placeholders_and_empty_labels(self) -> None:
        for text in ["受入基準: 未定。", "受入基準: なし。", "受入基準:", "Acceptance criteria: TBD."]:
            with self.subTest(text=text):
                match = find_field_assertion(text, ["受入基準", "acceptance criteria"])
                self.assertIsNotNone(match)
                self.assertEqual(match.status, "rejected")

    def test_markdown_heading_uses_immediate_body_as_field_content(self) -> None:
        asserted = find_field_assertion("## 受入基準\n- p95 500ms 以下", ["受入基準"])
        empty = find_field_assertion("## 受入基準\n## 検証方法", ["受入基準"])

        self.assertIsNotNone(asserted)
        self.assertEqual(asserted.status, "present")
        self.assertIsNotNone(empty)
        self.assertEqual(empty.status, "rejected")

    def test_concrete_assertion_wins_over_rejected_proposal(self) -> None:
        match = find_field_assertion(
            "証拠は残さない案は棄却する。証拠: pytest 結果を保存する。",
            ["証拠"],
        )

        self.assertIsNotNone(match)
        self.assertEqual(match.status, "present")

    def test_rejects_negated_structured_values(self) -> None:
        cases = [
            ("受入基準: 定めない。", ["受入基準"]),
            ("検証方法: 実施しない。", ["検証方法"]),
            ("証拠: 残さない。", ["証拠"]),
            ("Evidence: will not be retained.", ["evidence"]),
        ]
        for text, terms in cases:
            with self.subTest(text=text):
                match = find_field_assertion(text, terms)
                self.assertIsNotNone(match)
                self.assertEqual(match.status, "rejected")
                self.assertEqual(match.reason, "explicit_negation")

    def test_rejects_polite_completed_and_modified_absence(self) -> None:
        cases = [
            ("受入基準はありません。", ["受入基準"]),
            ("受入基準: 現在未定です。", ["受入基準"]),
            ("検証方法: 後で決める。", ["検証方法"]),
            ("証拠: 今のところ無し。", ["証拠"]),
            ("受入基準: 設定しません。", ["受入基準"]),
            ("検証方法: 実施しません。", ["検証方法"]),
            ("証拠: 保存しません。", ["証拠"]),
            ("Acceptance criteria have not been defined.", ["acceptance criteria"]),
            ("Verification method is absent.", ["verification method"]),
            ("There isn't any evidence.", ["evidence"]),
            ("Acceptance criteria: to be determined.", ["acceptance criteria"]),
            ("Verification method: not yet available.", ["verification method"]),
            ("Evidence: pending owner decision.", ["evidence"]),
        ]
        for text, terms in cases:
            with self.subTest(text=text):
                match = find_field_assertion(text, terms)
                self.assertIsNotNone(match)
                self.assertEqual(match.status, "rejected")

    def test_unlabelled_negative_outcome_content_is_not_field_absence(self) -> None:
        cases = [
            ("受入基準は設定を保存しないこと。", ["受入基準"]),
            ("受入基準は保存しないこと。", ["受入基準"]),
            ("受入基準: 保存しない。", ["受入基準"]),
            ("検証方法は実行しない静的解析とする。", ["検証方法"]),
            ("検証方法は実行しない静的解析。", ["検証方法"]),
            ("証拠は保存しない機密データの検出一覧とする。", ["証拠"]),
            ("証拠は保存しない機密情報の検出一覧。", ["証拠"]),
            ("Acceptance criteria: will not retain personal data.", ["acceptance criteria"]),
        ]
        for text, terms in cases:
            with self.subTest(text=text):
                match = find_field_assertion(text, terms)
                self.assertIsNotNone(match)
                self.assertEqual(match.status, "present")

    def test_field_specific_japanese_actions_distinguish_absence_from_negative_outcome(self) -> None:
        cases = [
            ("受入基準は設定しないこととする。", ["受入基準"]),
            ("検証方法は実施しないこととする。", ["検証方法"]),
            ("検証方法は実施しない方針。", ["検証方法"]),
            ("証拠は保存しないこととする。", ["証拠"]),
        ]
        for text, terms in cases:
            with self.subTest(text=text):
                match = find_field_assertion(text, terms)
                self.assertIsNotNone(match)
                self.assertEqual(match.status, "rejected")
                self.assertEqual(match.reason, "explicit_negation")

    def test_rejects_english_negated_action_before_field(self) -> None:
        for text, terms in [
            ("We do not define acceptance criteria.", ["acceptance criteria"]),
            ("We will not retain acceptance criteria.", ["acceptance criteria"]),
            ("Acceptance criteria will not be retained.", ["acceptance criteria"]),
            ("We will not retain evidence.", ["evidence"]),
        ]:
            with self.subTest(text=text):
                match = find_field_assertion(text, terms)
                self.assertIsNotNone(match)
                self.assertEqual(match.status, "rejected")


if __name__ == "__main__":
    unittest.main()
