"""Keep normalization and decision-state rules across the two audit repairs."""
from __future__ import annotations

import unittest

from semantic_guard_workflow.assertion_context import find_field_assertion, find_field_assertions
from semantic_guard_workflow.core import audit_diff, finish_check
from workflow_tests.test_diff_test_preservation import INTENT, SOURCE, _test_file_change


def _rules(result: dict[str, object]) -> set[str]:
    return {item["rule_id"] for item in result["findings"] if "rule_id" in item}


class MergedAuditContractsTests(unittest.TestCase):
    def test_test_reduction_reads_normalized_hunks_without_changing_paths(self) -> None:
        path = "tests/test_カ\u3099.py"
        for marker in ('@unittest.skip("flaky")', '＠ｕｎｉｔｔｅｓｔ．ｓｋｉｐ("flaky")'):
            with self.subTest(marker=marker):
                diff = SOURCE + _test_file_change("    " + marker).replace("tests/test_core.py", path)
                result = audit_diff(diff, intent=INTENT)
                self.assertIn("diff.test_obligation.tests_removed_or_disabled", _rules(result))
                self.assertEqual(result["status"], "block")
                self.assertIn(path, result["details"]["changed_files"])

    def test_reported_failures_are_detected_after_normalization(self) -> None:
        for receipt in ("pytest 3 failed", "ｐｙｔｅｓｔ ３ ｆａｉｌｅｄ", "py\u200btest 3 fail\u200bed"):
            with self.subTest(receipt=receipt):
                result = finish_check(
                    "完了。残余リスク: なし。",
                    evidence=f"検証証拠: {receipt}。受入証拠: 対応表を確認済み。",
                )
                self.assertIn("finish.evidence.failure_reported", _rules(result))
                self.assertEqual(result["status"], "block")

    def test_enumerating_receipts_preserves_labelled_value_precedence(self) -> None:
        text = "検証: 後で決める。補足として検証に触れる。"
        chosen = find_field_assertion(text, ["検証"])
        self.assertIsNotNone(chosen)
        self.assertNotEqual(chosen.status, "present")
        self.assertEqual(len(find_field_assertions(text, ["検証"])), 2)
        self.assertEqual(find_field_assertion("残余リスク: なし。", ["残余リスク"], accept_none=True).status, "present")

    def test_independent_receipt_survives_a_denied_check(self) -> None:
        result = finish_check(
            "完了。残る危険: 実機未確認。",
            evidence="統合テストは実行していないが、pytest は 8 passed。受入証拠: REQ-1 の8件が基準と一致。",
        )
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["missing"], [])
