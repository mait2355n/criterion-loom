from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest

from semantic_guard_workflow.core import finish_check
from semantic_guard_workflow.mcp_server import finish_check_tool


SUMMARY = "CLI出力を実装した。残リスク: 実機未確認。"
OTHER_EVIDENCE = "検証証拠: pytest 8 passed。受入証拠: 要求と結果の対応表を確認済み。"
BEHAVIOR_RULE = "finish.implementation.behavior_evidence_missing"


class BehaviorEvidenceTests(unittest.TestCase):
    def assert_behavior(self, text: str, *, present: bool) -> dict[str, object]:
        result = finish_check(SUMMARY, evidence=OTHER_EVIDENCE + text)
        self.assertEqual("behavior_evidence" not in result["missing"], present, text)
        rules = {item["rule_id"] for item in result["findings"] if "rule_id" in item}
        self.assertEqual(BEHAVIOR_RULE not in rules, present, text)
        self.assertEqual(result["status"], "pass" if present else "warn", text)
        return result

    def test_reported_packaged_cli_mcp_receipt_is_recognized(self) -> None:
        self.assert_behavior("隔離wheel CLI/MCP stdio各7入力成功。", present=True)

    def test_reported_non_execution_does_not_count_as_a_receipt(self) -> None:
        self.assert_behavior("代表実行は未実施。", present=False)

    def test_completed_execution_receipts_in_japanese_and_english(self) -> None:
        for receipt in (
            "代表 CLI 実行済み。",
            "CLIを実行しJSON出力を確認済み。",
            "MCP stdio: 7入力成功。",
            "API request returned HTTP 200 with JSON output.",
            "representative execution returned JSON output.",
            "semantic-guard audit-request returned JSON.",
            "smoke test passed.",
            "手動の出力確認を実施した。",
            "returncode: 0。",
            'stdout: {"status": "pass"}。',
        ):
            with self.subTest(receipt=receipt):
                self.assert_behavior(receipt, present=True)

    def test_failed_execution_is_still_execution_evidence(self) -> None:
        for receipt in (
            "CLI実行は失敗した。",
            "MCP stdio各7入力失敗。",
            "representative execution failed with returncode 1.",
            "API request returned HTTP 500.",
            "CLI returned no JSON output.",
        ):
            with self.subTest(receipt=receipt):
                self.assert_behavior(receipt, present=True)

    def test_explicit_absence_and_non_execution_stay_missing(self) -> None:
        for receipt in (
            "代表実行証拠は存在しない。",
            "代表実行はしていない。",
            "代表実行済みではない。",
            "手動確認: 実施済みではない。",
            "手動確認は未確認。",
            "smoke test was not executed.",
            "representative execution has not been performed.",
            "No representative execution evidence.",
            "We did not run the representative execution.",
            "CLI failed to execute.",
        ):
            with self.subTest(receipt=receipt):
                self.assert_behavior(receipt, present=False)

    def test_empty_or_unresolved_behavior_fields_stay_missing(self) -> None:
        for heading in ("代表実行", "smoke test", "stdout", "returncode", "CLI"):
            for value in ("", "-", "なし", "未定", "未実施", "保留", "TBD", "pending", "not run"):
                with self.subTest(heading=heading, value=value):
                    self.assert_behavior(f"{heading}: {value}。", present=False)

    def test_future_or_requested_execution_is_not_a_receipt(self) -> None:
        for receipt in (
            "代表実行は後日実施予定。",
            "代表実行: 実行済みにする予定。",
            "代表実行を実施してstdoutを確認する。",
            "CLIの終了値returncode: 0を確認してください。",
            "代表実行: 成功させる予定。",
            "representative execution will be performed.",
            "The smoke test should have passed.",
            'Run representative execution and check stdout: {"ok": true}.',
            "semantic-guard audit-request --text example を実行する。",
        ):
            with self.subTest(receipt=receipt):
                self.assert_behavior(receipt, present=False)

    def test_terms_and_descriptions_are_not_execution_receipts(self) -> None:
        for receipt in (
            "代表実行、手動、stdout、returncode。",
            "代表実行とはCLIの出力確認である。",
            "CLI API MCP JSON stdout returncode smoke e2e manual.",
            "representative execution means checking the command output.",
            "semantic-guard audit-request --text example",
        ):
            with self.subTest(receipt=receipt):
                self.assert_behavior(receipt, present=False)

    def test_unit_fixture_output_terms_are_not_public_execution(self) -> None:
        for receipt in (
            "単体試験: stdout fixture 8件を確認済み。",
            "単体試験: returncode fixture 8件を確認済み。",
            "Unit tests: screenshot fixtures passed.",
        ):
            with self.subTest(receipt=receipt):
                self.assert_behavior(receipt, present=False)

    def test_a_unit_test_label_does_not_discard_actual_cli_execution(self) -> None:
        self.assert_behavior("単体試験: CLIを実行しstdoutを確認済み。", present=True)

    def test_implementation_success_is_distinct_from_execution_success(self) -> None:
        for receipt in (
            "CLI実装に成功。", "CLIの実装は失敗した。", "MCPの改修に成功した。",
            "CLI implementation completed.", "CLI build passed.", "MCP build failed.",
        ):
            with self.subTest(receipt=receipt):
                self.assert_behavior(receipt, present=False)
        self.assert_behavior("CLI実行に成功した。", present=True)
        self.assert_behavior("MCP実行は失敗した。", present=True)
        self.assert_behavior(
            "CLI implementation completed; representative CLI execution returned JSON.", present=True,
        )
        self.assert_behavior("CLI build passed and CLI smoke test returned JSON.", present=True)

    def test_other_evidence_cannot_complete_an_absent_behavior_field(self) -> None:
        for receipt in (
            "代表実行は未実施、検証証拠: pytest 8 passed。",
            "代表実行:\n受入証拠: 要求と結果の対応表を確認済み。",
            "代表実行:\n検証証拠: pytest 8 passed。",
        ):
            with self.subTest(receipt=receipt):
                self.assert_behavior(receipt, present=False)

    def test_completed_receipts_survive_independent_non_execution(self) -> None:
        absent = "代表実行は未実施"
        present = "隔離wheel CLI/MCP stdio各7入力成功"
        for separator in ("。", "; ", "\n"):
            for first, second in ((absent, present), (present, absent)):
                with self.subTest(separator=separator, first=first):
                    self.assert_behavior(first + separator + second + "。", present=True)

    def test_behavior_headings_after_commas_keep_independent_receipts(self) -> None:
        for separator in ("、", "，", ", ", "、\u3000", ",\u00a0", "，\t"):
            for first, second in (
                ("代表実行: 未実施", "代表実行: CLI実行済み"),
                ("CLI: 未実施", "MCP: 7入力成功"),
                ("MCP: 7入力成功", "CLI: 未実施"),
            ):
                with self.subTest(separator=separator, first=first):
                    self.assert_behavior(first + separator + second + "。", present=True)

    def test_multiline_behavior_values_keep_receipt_colons(self) -> None:
        for receipt in ("returncode: 0", 'stdout: {"status": "pass"}', "check-log: CLI 7入力成功"):
            with self.subTest(receipt=receipt):
                self.assert_behavior(f"代表実行:\n{receipt}\n", present=True)

    def test_risk_and_criteria_cannot_supply_execution_evidence(self) -> None:
        for receipt in (
            "残リスク: 代表実行は未実施。",
            "受入基準: representative execution returned JSON output.",
            "完了条件: CLI 7入力成功。",
        ):
            with self.subTest(receipt=receipt):
                self.assert_behavior(receipt, present=False)

    def test_valid_not_run_reason_keeps_existing_escape(self) -> None:
        for reason in (
            "代表実行は未実施。未実行理由: 実機を利用できないため。",
            "Tests were not run because hardware is unavailable.",
        ):
            with self.subTest(reason=reason):
                self.assert_behavior(reason, present=True)

    def test_missing_behavior_keeps_strict_and_non_strict_severity(self) -> None:
        for strict, severity in ((True, "major"), (False, "minor")):
            with self.subTest(strict=strict):
                result = finish_check(SUMMARY, evidence=OTHER_EVIDENCE + "代表実行は未実施。", strict=strict)
                finding = next(item for item in result["findings"] if item.get("rule_id") == BEHAVIOR_RULE)
                self.assertEqual(finding["severity"], severity)

    def test_public_cli_preserves_both_reported_outcomes(self) -> None:
        for receipt, status in (("隔離wheel CLI/MCP stdio各7入力成功。", "pass"), ("代表実行は未実施。", "warn")):
            with self.subTest(receipt=receipt):
                completed = subprocess.run(
                    [sys.executable, "-m", "semantic_guard_workflow.cli", "finish-check", "--text", SUMMARY,
                     "--evidence", OTHER_EVIDENCE + receipt],
                    capture_output=True, text=True, check=False,
                    env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertEqual(completed.stderr, "")
                result = json.loads(completed.stdout)
                self.assertEqual(result["status"], status)
                self.assertEqual("behavior_evidence" in result["missing"], status == "warn")

    def test_mcp_service_preserves_both_reported_outcomes(self) -> None:
        for receipt, status in (("隔離wheel CLI/MCP stdio各7入力成功。", "pass"), ("代表実行は未実施。", "warn")):
            with self.subTest(receipt=receipt):
                result = finish_check_tool(summary=SUMMARY, evidence=OTHER_EVIDENCE + receipt)
                self.assertEqual(result["status"], status)
                self.assertEqual("behavior_evidence" in result["missing"], status == "warn")


if __name__ == "__main__":
    unittest.main()
