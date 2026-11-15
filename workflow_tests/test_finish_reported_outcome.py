"""A completion report is read for what it says happened, not for which words it contains.

Three boundaries are held here:

* a denied or unresolved verification is not verification evidence;
* a verification reported as failed blocks the completion claim;
* a statement that verification happened, with nothing another person could
  check, is a declaration and not a receipt.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest

from semantic_guard_workflow.core import finish_check
from semantic_guard_workflow.mcp_server import finish_check_tool


FAILURE_RULE = "finish.evidence.failure_reported"
RECEIPT_RULE = "finish.evidence.receipt_missing"
TESTS_RULE = "finish.evidence.tests_missing"
RECEIPTS = "検証証拠: pytest 12 passed。受入証拠: 要求と結果の対応表を確認済み。"
CLOSED_SUMMARY = "完了。残リスク: なし。"


def _rules(result: dict[str, object]) -> set[str]:
    return {item["rule_id"] for item in result["findings"] if "rule_id" in item}


class DeniedVerificationTests(unittest.TestCase):
    def test_negated_predicate_after_the_action_noun_is_not_evidence(self) -> None:
        for statement in (
            "テストは実行していません。",
            "テストは実行していない。",
            "検証はしていません。",
            "動作確認はできていません。",
            "テストは行っていません。",
            "検証はまだ実施していない。",
            "テストは省略しました。",
            "テストをスキップした。",
            "Tests were skipped.",
            "Verification was skipped.",
            "I skipped the tests.",
            "We were unable to run the tests.",
        ):
            with self.subTest(statement=statement):
                result = finish_check(f"実装した。{statement} 受入証拠: なし。残リスク: 未検証。")
                self.assertIn("tests_ran_or_reason", result["missing"])
                self.assertEqual(result["status"], "block")
                self.assertNotIn(RECEIPT_RULE, _rules(result))

    def test_a_copula_does_not_turn_an_unresolved_value_into_evidence(self) -> None:
        for statement, missing in (
            ("テストは未実行です。", "tests_ran_or_reason"),
            ("テストは未実行である。", "tests_ran_or_reason"),
            ("テストはまだです。", "tests_ran_or_reason"),
            ("テストはこれからです。", "tests_ran_or_reason"),
            ("受入基準は未確認です。", "acceptance_evidence"),
            ("受入証拠は未確認でした。", "acceptance_evidence"),
        ):
            with self.subTest(statement=statement):
                result = finish_check(f"実装した。{statement} 残リスク: 未検証。")
                self.assertIn(missing, result["missing"])
                self.assertNotEqual(result["status"], "pass")

    def test_a_denied_check_does_not_hide_an_independent_receipt_in_the_same_clause(self) -> None:
        result = finish_check(
            "完了。残リスク: 実機未確認。",
            evidence="統合テストは実行していないが、pytest は 8 passed。受入証拠: REQ-1 の8件の結果が基準と一致。",
        )
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["missing"], [])

    def test_residual_risk_synonyms_are_recognized_as_a_risk_statement(self) -> None:
        for label in ("残余リスク", "残存リスク"):
            with self.subTest(label=label):
                result = finish_check(f"完了。{label}: なし。", evidence=RECEIPTS)
                self.assertEqual(result["findings"], [])


class ReportedFailureTests(unittest.TestCase):
    def assert_failure(self, summary: str, evidence: str = "", *, reported: bool, context: str = "") -> dict[str, object]:
        result = finish_check(summary, evidence=evidence, context=context)
        self.assertEqual(FAILURE_RULE in _rules(result), reported, summary + " | " + evidence)
        self.assertEqual("failure_resolution" in result["missing"], reported)
        if reported:
            self.assertEqual(result["status"], "block")
        return result

    def test_reported_failures_block_the_completion_claim(self) -> None:
        for evidence in (
            "検証証拠: テストが3件失敗しました。",
            "検証証拠: 3件失敗。",
            "検証証拠: 失敗3件。",
            "検証証拠: 3件のテストが失敗しました。",
            "検証証拠: pytestで3件失敗。",
            "検証証拠: テストは失敗しています。",
            "検証証拠: CIが落ちています。",
            "検証証拠: テストが通りません。",
            "検証証拠: pytest: 3 failed, 117 passed。",
            "検証証拠: 117 passed, 3 failed in 2.1s。",
            "検証証拠: passed 6 failed 2。",
            "検証証拠: pytest: 1 error, 9 passed。",
            "Verification evidence: 2 tests failed.",
            "Verification evidence: the build is failing.",
            "Verification evidence: tests did not pass.",
            "FAILED tests/test_core.py::test_total",
            "受入基準を満たしていません。",
            "Acceptance criteria are not met.",
        ):
            with self.subTest(evidence=evidence):
                self.assert_failure(CLOSED_SUMMARY, evidence + " 受入証拠: 対応表を確認済み。", reported=True)

    def test_a_success_claim_does_not_override_failing_evidence(self) -> None:
        result = self.assert_failure(
            "実装は完了しました。受入基準は満たしました。検証済み。残リスクなし。",
            "pytest: 3 failed, 117 passed",
            reported=True,
        )
        finding = next(item for item in result["findings"] if item["rule_id"] == FAILURE_RULE)
        self.assertIn("3 failed", finding["evidence"])

    def test_zero_counts_and_absence_of_failures_are_not_failures(self) -> None:
        for evidence in (
            "検証証拠: pytest 120 passed, 0 failed。",
            "検証証拠: total 6 passed 6 failed 0 pass_rate 1.0。",
            "検証証拠: 0 failed 117 passed。",
            "検証証拠: pytest 12 passed、失敗0件。",
            "検証証拠: pytest 12 passed、失敗なし。",
            "検証証拠: pytest 12 passed、失敗はありません。",
            "Verification evidence: pytest 12 passed, no tests failed.",
        ):
            with self.subTest(evidence=evidence):
                result = self.assert_failure(CLOSED_SUMMARY, evidence + " 受入証拠: 対応表を確認済み。", reported=False)
                self.assertEqual(result["status"], "pass")

    def test_descriptions_of_failure_are_not_reported_results(self) -> None:
        for summary in (
            "失敗時は退避済み状態へ戻す処理を追加した。",
            "テストが失敗する場合の出力を改善した。",
            "テストが失敗したら通知する処理を追加した。",
            "失敗したテストを修正した。",
            "テストが3件失敗していた問題を修正した。",
            "ログイン失敗3件でロックする機能を実装した。",
            "ログイン失敗3回でロックする機能を実装した。",
            "The account is locked after 3 failed attempts.",
            "The validator returns 3 errors for the invalid bundle.",
            "The build was failing before the pin; the pin was added.",
            "execution.status=failed is returned for a provider failure.",
            "failed 3 times to connect, then succeeded.",
        ):
            with self.subTest(summary=summary):
                self.assert_failure(summary + " 残リスク: なし。", RECEIPTS, reported=False)

    def test_a_later_recorded_reverification_closes_an_earlier_failure(self) -> None:
        for evidence in (
            "検証証拠: pytest 3 failed。原因を修正し再実行して pytest 120 passed。",
            "検証証拠: テスト3件失敗、修正して再実行し全件成功、pytest 120 passed。",
            "Verification evidence: pytest 3 failed. After the fix, pytest 120 passed.",
        ):
            with self.subTest(evidence=evidence):
                result = self.assert_failure(CLOSED_SUMMARY, evidence + " 受入証拠: 対応表を確認済み。", reported=False)
                self.assertEqual(result["status"], "pass")

    def test_a_failure_after_the_claimed_success_stays_open(self) -> None:
        for summary, evidence in (
            ("再実行して全件成功しました。残リスク: なし。", "pytest: 3 failed, 117 passed。受入証拠: 対応表を確認済み。"),
            (CLOSED_SUMMARY, "検証証拠: 修正後は 117 passed, 3 failed。受入証拠: 対応表を確認済み。"),
            (CLOSED_SUMMARY, "検証証拠: 再実行でも3件失敗。受入証拠: 対応表を確認済み。"),
        ):
            with self.subTest(evidence=evidence):
                self.assert_failure(summary, evidence, reported=True)

    def test_failures_described_only_in_the_request_context_are_not_the_report(self) -> None:
        result = self.assert_failure(
            "修正した。残リスク: なし。",
            RECEIPTS,
            context="依頼: テストが3件失敗しているので直してほしい。pytest: 3 failed。",
            reported=False,
        )
        self.assertEqual(result["status"], "pass")

    def test_relaxed_mode_downgrades_the_failure_to_major(self) -> None:
        result = finish_check(CLOSED_SUMMARY, evidence="pytest: 3 failed, 117 passed。受入証拠: 対応表を確認済み。", strict=False)
        finding = next(item for item in result["findings"] if item["rule_id"] == FAILURE_RULE)
        self.assertEqual(finding["severity"], "major")
        self.assertEqual(result["status"], "warn")


class DeclarationWithoutReceiptTests(unittest.TestCase):
    def test_bare_declarations_warn_instead_of_passing(self) -> None:
        for summary in (
            "完了。受入基準は満たしました。検証済み。残リスクなし。",
            "完了。受入条件と証拠の対応あり。テスト済みです。残リスクなし。",
            "完了。受入条件と証拠の対応あり。動作確認しました。残リスクなし。",
            "完了。受入条件と証拠の対応あり。すべてのテストが通っています。残リスクなし。",
            "完了。受入条件と証拠の対応あり。検証証拠: 手動で確認済み。残リスクなし。",
        ):
            with self.subTest(summary=summary):
                result = finish_check(summary)
                self.assertIn(RECEIPT_RULE, _rules(result))
                self.assertNotIn(TESTS_RULE, _rules(result))
                self.assertIn("verification_receipt", result["missing"])
                self.assertEqual(result["status"], "warn")

    def test_a_named_command_count_or_output_location_is_a_receipt(self) -> None:
        for receipt in (
            "検証証拠: pytest 8 passed。",
            "検証証拠: uv run pytest を実行して成功。",
            "検証証拠: pytestを実行して成功。",
            "検証証拠: テスト 686 件成功を確認。",
            "検証証拠: `make test` を実行して確認。",
            "検証証拠: 確認ログは out/run.log。",
            "検証証拠: 手動確認で 3 回ログイン成功を確認。",
            "検証証拠: CI run 39009453507 で検証済み。",
            "unittest を実行して成功した。",
        ):
            with self.subTest(receipt=receipt):
                result = finish_check(CLOSED_SUMMARY, evidence=receipt + " 受入証拠: 対応表を確認済み。")
                self.assertNotIn(RECEIPT_RULE, _rules(result))
                self.assertEqual(result["status"], "pass")

    def test_a_recorded_not_run_reason_is_not_asked_for_a_receipt(self) -> None:
        result = finish_check(
            "CLI command の JSON output を実装した。残リスク: 実機未確認。",
            evidence="Tests were not run because hardware is unavailable. Acceptance evidence: none.",
        )
        self.assertNotIn(RECEIPT_RULE, _rules(result))
        self.assertEqual(result["missing"], ["acceptance_evidence"])

    def test_a_reported_failure_is_not_additionally_asked_for_a_receipt(self) -> None:
        result = finish_check("完了。検証済み。受入基準は満たしました。残リスクなし。", evidence="テストは失敗しています。")
        self.assertIn(FAILURE_RULE, _rules(result))
        self.assertNotIn(RECEIPT_RULE, _rules(result))

    def test_relaxed_mode_downgrades_the_missing_receipt_to_minor(self) -> None:
        result = finish_check("完了。受入基準は満たしました。検証済み。残リスクなし。", strict=False)
        finding = next(item for item in result["findings"] if item["rule_id"] == RECEIPT_RULE)
        self.assertEqual(finding["severity"], "minor")


class PublicSurfaceTests(unittest.TestCase):
    SUMMARY = "実装は完了しました。受入基準は満たしました。検証済み。残リスクなし。"
    EVIDENCE = "pytest: 3 failed, 117 passed"

    def test_cli_reports_the_failure_as_audit_json(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-m", "semantic_guard_workflow.cli", "finish-check",
             "--text", self.SUMMARY, "--evidence", self.EVIDENCE],
            capture_output=True, text=True, check=False,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "block")
        self.assertIn(FAILURE_RULE, _rules(result))

    def test_mcp_service_uses_the_same_boundary(self) -> None:
        result = finish_check_tool(summary=self.SUMMARY, evidence=self.EVIDENCE)
        self.assertEqual(result["status"], "block")
        self.assertIn(FAILURE_RULE, _rules(result))


if __name__ == "__main__":
    unittest.main()
