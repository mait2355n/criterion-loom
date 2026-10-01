from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest

from semantic_guard_workflow.core import finish_check
from semantic_guard_workflow.mcp_server import finish_check_tool


ABSENT_EVIDENCE = (
    "完了。検証証拠は存在しない。受入条件と証拠の対応もない。残リスクは未確認。"
)
MISSING_EVIDENCE = {"tests_ran_or_reason", "acceptance_evidence"}


class FinishEvidenceTests(unittest.TestCase):
    def test_explicit_absence_does_not_count_as_completion_evidence(self) -> None:
        cases = (
            ABSENT_EVIDENCE,
            "完了。テスト: なし。受入証拠: なし。残リスク: 未確認。",
            "完了。検証結果: 未定。受入証拠: 不明。残リスク: なし。",
            "Done. Tests: none. Acceptance evidence: none. Residual risks: unknown.",
            "Done. Tests were not run. Acceptance evidence does not exist. Residual risks: unknown.",
            "Done. No test evidence. No acceptance evidence. Residual risks: unknown.",
            "Done. Verification: TBD. Acceptance evidence: pending. Residual risks: none.",
        )
        for text in cases:
            with self.subTest(text=text):
                result = finish_check(text)
                self.assertEqual(result["status"], "block")
                self.assertTrue(MISSING_EVIDENCE <= set(result["missing"]))

    def test_empty_or_unresolved_evidence_labels_stay_missing(self) -> None:
        for value in ("", "-", "未定", "未実行", "未確認", "未検証", "TBD", "not run"):
            with self.subTest(value=value):
                text = f"完了。\n検証証拠: {value}\n受入証拠: {value}\n残リスク: 未確認。"
                result = finish_check(text)
                self.assertTrue(MISSING_EVIDENCE <= set(result["missing"]))

    def test_explicit_evidence_kinds_cannot_satisfy_each_other(self) -> None:
        cases = (
            ("検証証拠: pytest 8 passed。受入証拠: なし。", "acceptance_evidence"),
            ("検証証拠: なし。受入証拠: 要求と結果の対応表を確認済み。", "tests_ran_or_reason"),
            ("Verification evidence: pytest 8 passed. Acceptance evidence: none.", "acceptance_evidence"),
            ("Verification evidence: none. Acceptance evidence: checked the requirement mapping.", "tests_ran_or_reason"),
            ("検証証拠: pytest 8 passed。受入証拠: 未定。受入基準: JSON が出る。", "acceptance_evidence"),
        )
        for evidence, missing in cases:
            with self.subTest(evidence=evidence):
                result = finish_check("完了。残リスク: 未確認。", evidence=evidence)
                self.assertIn(missing, result["missing"])
                self.assertNotEqual(result["status"], "pass")

    def test_known_evidence_headings_separate_kinds_after_commas(self) -> None:
        cases = (
            ("検証証拠: pytest 8 passed", "受入証拠: なし", "acceptance_evidence"),
            ("検証証拠: なし", "受入証拠: 要求と結果の対応表を確認済み", "tests_ran_or_reason"),
            ("Verification evidence: pytest 8 passed", "Acceptance evidence: none", "acceptance_evidence"),
            ("Verification evidence: none", "Acceptance evidence: checked the requirement mapping", "tests_ran_or_reason"),
        )
        for first, second, missing in cases:
            for separator in ("、", "，", ", ", "、\u3000", ",\u00a0", "，\t"):
                with self.subTest(first=first, second=second, separator=separator):
                    result = finish_check(
                        "完了。残リスク: 未確認。", evidence=f"{first}{separator}{second}。"
                    )
                    self.assertEqual(set(result["missing"]), {missing})

    def test_known_heading_boundary_preserves_multiple_same_kind_receipts(self) -> None:
        result = finish_check(
            "完了。残リスク: 未確認。",
            evidence=(
                "検証証拠: なし、検証証拠: pytest 8 passed、"
                "受入証拠: 未定、受入証拠: REQ-1 の8件の結果が基準と一致。"
            ),
        )
        self.assertEqual(result["status"], "pass")
        self.assertFalse(MISSING_EVIDENCE & set(result["missing"]))

    def test_independent_receipts_of_the_same_declared_kind_are_preserved(self) -> None:
        result = finish_check(
            "完了。残リスク: 実機未確認。",
            evidence=(
                "検証証拠: なし。検証証拠: pytest 8 passed。"
                "受入証拠: 未定。受入証拠: REQ-1 の8件の結果が基準と一致。"
            ),
        )
        self.assertEqual(result["status"], "pass")
        self.assertFalse(MISSING_EVIDENCE & set(result["missing"]))

    def test_present_perfect_non_execution_stays_missing(self) -> None:
        result = finish_check(
            "Done. Tests have not been run. Acceptance evidence: none. Residual risks: unknown."
        )
        self.assertTrue(MISSING_EVIDENCE <= set(result["missing"]))

    def test_multiline_evidence_values_keep_their_declared_kind(self) -> None:
        result = finish_check(
            "完了。残リスク: 実機未確認。",
            evidence="検証証拠:\npytest 8 passed\n受入証拠:\nREQ-1 の8件の結果が基準と一致。",
        )
        self.assertEqual(result["status"], "pass")
        self.assertFalse(MISSING_EVIDENCE & set(result["missing"]))

    def test_command_and_requirement_colons_remain_multiline_values(self) -> None:
        for receipt in ("pytest: 8 passed", "unittest: 8 passed", "check-log: 8 tests passed"):
            with self.subTest(receipt=receipt):
                result = finish_check(
                    "完了。残リスク: 実機未確認。",
                    evidence=f"検証証拠:\n{receipt}\n受入証拠:\nREQ-1: 8件の結果が基準と一致。",
                )
                self.assertEqual(result["status"], "pass")
                self.assertFalse(MISSING_EVIDENCE & set(result["missing"]))

    def test_next_known_evidence_heading_cannot_fill_an_empty_previous_kind(self) -> None:
        result = finish_check(
            "完了。残リスク: 未確認。",
            evidence="検証証拠:\n受入証拠: 要求と結果の対応表を確認済み。",
        )
        self.assertEqual(result["missing"], ["tests_ran_or_reason"])

    def test_public_behavior_can_record_a_reason_for_not_running(self) -> None:
        result = finish_check(
            "CLI command の JSON output を実装した。残リスク: 実機未確認。",
            evidence="Tests were not run because hardware is unavailable. Acceptance evidence: none.",
        )
        self.assertEqual(result["missing"], ["acceptance_evidence"])
        self.assertEqual(result["status"], "warn")

    def test_negative_acceptance_condition_with_actual_tests_is_preserved(self) -> None:
        result = finish_check(
            "認証処理を改修した。受入基準: 未認証利用者には機密情報を表示しない。",
            evidence="検証証拠: pytest 8 passed。受入証拠: セキュリティ試験で機密情報の表示が0件と確認。残リスクなし。",
        )
        self.assertEqual(result["status"], "pass")
        self.assertFalse(MISSING_EVIDENCE & set(result["missing"]))

    def test_independent_test_receipt_survives_an_absent_other_test(self) -> None:
        result = finish_check(
            "完了。統合テスト: 未実行。",
            evidence="検証証拠: pytest 8 passed。受入証拠: REQ-1 の期待値と8件の試験結果が一致。残リスク: 実機未確認。",
        )
        self.assertEqual(result["status"], "pass")
        self.assertFalse(MISSING_EVIDENCE & set(result["missing"]))

    def test_documented_not_run_reason_counts_only_for_execution_accounting(self) -> None:
        for reason in (
            "未実行理由: 実機を利用できないため。",
            "Tests were not run because the test device is unavailable.",
            "Tests not run: hardware is unavailable.",
        ):
            with self.subTest(reason=reason):
                result = finish_check(
                    "完了。受入証拠: なし。残リスク: 実機未確認。",
                    evidence=reason,
                )
                self.assertNotIn("tests_ran_or_reason", result["missing"])
                self.assertIn("acceptance_evidence", result["missing"])
                self.assertEqual(result["status"], "warn")

    def test_empty_or_placeholder_not_run_reason_is_not_evidence(self) -> None:
        for reason in ("未実行理由:", "未実行理由: なし。", "未実行理由: 未定。", "Tests not run because TBD."):
            with self.subTest(reason=reason):
                result = finish_check(
                    "完了。受入証拠: なし。残リスク: 未確認。",
                    evidence=reason,
                )
                self.assertTrue(MISSING_EVIDENCE <= set(result["missing"]))

    def test_risk_or_acceptance_wording_does_not_supply_a_test_receipt(self) -> None:
        for text in (
            "完了。受入証拠: なし。残リスク: 動作確認は未実行。",
            "完了。受入基準: 試験で機密情報を表示しない。残リスク: 未確認。",
        ):
            with self.subTest(text=text):
                result = finish_check(text)
                self.assertIn("tests_ran_or_reason", result["missing"])

    def test_non_strict_mode_preserves_missing_evidence_but_downgrades_blocker(self) -> None:
        result = finish_check(ABSENT_EVIDENCE, strict=False)
        self.assertEqual(result["status"], "warn")
        self.assertTrue(MISSING_EVIDENCE <= set(result["missing"]))
        finding = next(item for item in result["findings"] if item["rule_id"] == "finish.evidence.tests_missing")
        self.assertEqual(finding["severity"], "major")

    def test_public_cli_reports_absence_as_audit_json(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-m", "semantic_guard_workflow.cli", "finish-check", "--text", ABSENT_EVIDENCE],
            capture_output=True,
            text=True,
            check=False,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stderr, "")
        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "block")
        self.assertTrue(MISSING_EVIDENCE <= set(result["missing"]))

    def test_mcp_service_uses_the_same_evidence_boundary(self) -> None:
        result = finish_check_tool(summary=ABSENT_EVIDENCE)
        self.assertEqual(result["status"], "block")
        self.assertTrue(MISSING_EVIDENCE <= set(result["missing"]))


if __name__ == "__main__":
    unittest.main()
