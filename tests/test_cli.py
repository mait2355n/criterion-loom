import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from semantic_guard.cli import main


class CLITests(unittest.TestCase):
    def test_explore_request_command_prints_questions(self) -> None:
        result = self._run_cli(["semantic-guard", "explore-request", "--text", "割り勘アプリを作りたい"], "")

        self.assertEqual(result["phase"], "explore_request")
        self.assertEqual(result["status"], "warn")
        self.assertIn("questions", result["details"])
        self.assertIn("target_audience", result["missing"])

    def test_llm_explore_request_command_defaults_to_dry_run(self) -> None:
        result = self._run_cli(["semantic-guard", "llm-explore-request", "--text", "割り勘アプリを作りたい"], "")

        self.assertFalse(result["executed"])
        self.assertEqual(result["execution_status"], "dry_run")
        self.assertIn("codex", result["command"])
        self.assertIn("request_exploration_interviewer", result["prompt"])
        self.assertIn("request-exploration-review.schema.json", result["schema_path"])

    def test_request_exploration_review_schema_command_prints_schema(self) -> None:
        result = self._run_cli(["semantic-guard", "request-exploration-review-schema"], "")

        self.assertEqual(result["title"], "semantic-guard request exploration review")
        self.assertIn("questions", result["required"])

    def test_audit_diff_reads_top_stdin_intent_metadata(self) -> None:
        result = self._run_cli(
            ["semantic-guard", "audit-diff"],
            "Intent: docs に検証証拠を追記する。\n"
            "*** Update File: docs/example.md\n"
            "+ 検証証拠: audit-request --kind document を実行し、status pass を確認。\n",
        )

        self.assertEqual(result["status"], "pass")
        self.assertNotIn("intent", result["missing"])
        self.assertEqual(result["details"]["changed_files"], ["docs/example.md"])

    def test_audit_decision_state_command_reports_handoff_items(self) -> None:
        result = self._run_cli(
            [
                "semantic-guard",
                "audit-decision-state",
                "--text",
                "未決定: 採用基準。owner: 人間。needed_for: goal design。next_action: 判断条件を書く。",
            ],
            "",
        )

        self.assertEqual(result["phase"], "audit_decision_state")
        self.assertEqual(result["details"]["schema_version"], "decision-state-audit/v1")
        self.assertGreaterEqual(len(result["details"]["decision_state_report"]["management_handoff_items"]), 1)

    def test_audit_diff_explicit_intent_wins_over_stdin_metadata(self) -> None:
        result = self._run_cli(
            ["semantic-guard", "audit-diff", "--intent", "内部処理を修正する。"],
            "Intent: README を更新する。\n"
            "*** Update File: src/semantic_guard/core.py\n"
            "+ result = process()\n",
        )

        categories = {finding["category"] for finding in result["findings"]}
        self.assertNotIn("intent", result["missing"])
        self.assertNotIn("documentation", categories)

    def test_audit_diff_does_not_extract_hunk_intent_line(self) -> None:
        result = self._run_cli(
            ["semantic-guard", "audit-diff"],
            "*** Update File: docs/example.md\n"
            "+Intent: docs に検証証拠を追記する。\n"
            "+ 検証証拠: audit-request --kind document を実行し、status pass を確認。\n",
        )

        self.assertIn("intent", result["missing"])

    def test_audit_diff_text_argument_does_not_use_intent_metadata(self) -> None:
        result = self._run_cli(
            [
                "semantic-guard",
                "audit-diff",
                "--text",
                "Intent: docs に検証証拠を追記する。\n"
                "*** Update File: docs/example.md\n"
                "+ 検証証拠: audit-request --kind document を実行し、status pass を確認。\n",
            ],
            "",
        )

        self.assertIn("intent", result["missing"])

    def test_audit_result_schema_command_prints_schema(self) -> None:
        result = self._run_cli(["semantic-guard", "audit-result-schema"], "")

        self.assertEqual(result["title"], "semantic-guard audit result")
        self.assertIn("phase", result["required"])
        self.assertIn("findings", result["properties"])

    def test_rule_detector_map_command_covers_rules(self) -> None:
        result = self._run_cli(["semantic-guard", "rule-detector-map"], "")

        self.assertEqual(result["rule_count"], result["mapping_count"])
        self.assertEqual(result["unmapped_rule_ids"], [])
        self.assertGreater(len(result["mappings"]), 0)
        first = result["mappings"][0]
        self.assertIn("rule_id", first)
        self.assertIn("detector_id", first)
        self.assertIn("source_functions", first)

    def test_conventions_catalog_command_prints_catalog(self) -> None:
        result = self._run_cli(["semantic-guard", "conventions-catalog"], "")

        self.assertEqual(result["schema_version"], "semantic-guard-conventions/v1")
        self.assertEqual(result["id"], "base-contract")
        self.assertGreater(len(result["rules"]), 0)

    def test_audit_conventions_warns_on_public_output_without_contract(self) -> None:
        result = self._run_cli(
            [
                "semantic-guard",
                "audit-conventions",
                "--text",
                "MCP tool を追加して JSON result を返す。エラー時も返す。",
            ],
            "",
        )

        self.assertEqual(result["phase"], "audit_conventions")
        self.assertEqual(result["status"], "warn")
        self.assertIn("conv.structure.versioned_shape", result["missing"])
        self.assertIn("conv.output.envelope", result["missing"])
        self.assertIn("conv.error.shape", result["missing"])

    def test_audit_conventions_passes_explicit_cli_contract(self) -> None:
        result = self._run_cli(
            [
                "semantic-guard",
                "audit-conventions",
                "--text",
                "CLI command returns JSON output to stdout. Human diagnostics go to stderr. "
                "The schema_version is tool-result/v1 and fields are typed strings, booleans, numbers, and enum status values. "
                "Exit code 0 means success, exit code 1 means audited-material failure, "
                "exit code 2 means usage error, and exit code 3 means dependency failure. "
                "Failure output includes error code, message, details, and hint fields. "
                "The output status, result, error, and details fields are verified by representative unittest output-contract tests.",
            ],
            "",
        )

        self.assertEqual(result["phase"], "audit_conventions")
        self.assertEqual(result["status"], "pass")

    def test_doctor_command_reports_environment(self) -> None:
        result = self._run_cli(["semantic-guard", "doctor", "--no-fixtures"], "")

        self.assertEqual(result["phase"], "doctor")
        self.assertIn(result["status"], {"pass", "warn"})
        self.assertTrue(any(check["name"] == "schemas" for check in result["checks"]))

    def _run_cli(self, argv: list[str], stdin: str) -> dict[str, object]:
        stdout = io.StringIO()
        with patch.object(sys, "argv", argv), patch("sys.stdin", io.StringIO(stdin)), redirect_stdout(stdout):
            main()
        return json.loads(stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
