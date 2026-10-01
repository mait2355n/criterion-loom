"""Public CLI input failures are diagnostics, not Python crashes."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class CLIInputErrorTests(unittest.TestCase):
    def run_cli(self, *args: str, input: str | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "semantic_guard_workflow.cli", *args],
            input=input, capture_output=True, text=True, check=False,
        )

    def assert_input_error(self, result: subprocess.CompletedProcess[str], message: str) -> None:
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertIn(message, result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_unreadable_files_are_input_errors_for_text_and_json_commands(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            malformed = root / "malformed.txt"
            malformed.write_bytes(b"\xff\xfe")
            for command in ("explore-request", "audit-plan", "trace-report"):
                for path in (root / "missing", root, malformed):
                    with self.subTest(command=command, path=path.name):
                        self.assert_input_error(self.run_cli(command, "--file", str(path)), "cannot read input")

    def test_malformed_json_and_non_object_are_input_errors(self) -> None:
        for raw, message in (("{", "invalid JSON input"), ("[]", "JSON input must be an object")):
            with self.subTest(raw=raw):
                self.assert_input_error(self.run_cli("trace-report", input=raw), message)

    def test_nonpositive_review_timeout_is_input_error(self) -> None:
        self.assert_input_error(
            self.run_cli("llm-review-command", "--text", '{"candidate":"review this"}', "--timeout-seconds", "0"),
            "--timeout-seconds must be positive",
        )

    def test_invalid_review_request_is_input_error_before_execution(self) -> None:
        for command in ("llm-review-command", "llm-review-run", "llm-review-prompt"):
            with self.subTest(command=command):
                self.assert_input_error(self.run_cli(command, "--text", "{}"), "`candidate` must be a non-empty string")

    def test_valid_review_request_stays_dry_run(self) -> None:
        result = self.run_cli("llm-review-run", "--text", '{"candidate":"review this"}')
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["executed"])
        self.assertEqual(payload["execution_status"], "dry_run")

    def test_unknown_review_rule_is_input_error(self) -> None:
        for command in ("llm-review-command", "llm-review-prompt"):
            with self.subTest(command=command):
                self.assert_input_error(
                    self.run_cli(command, "--text", '{"candidate":"review this","rule_ids":["not-a-rule"]}'),
                    "not-a-rule",
                )

    def test_invalid_template_field_is_input_error(self) -> None:
        self.assert_input_error(
            self.run_cli("acceptance-bundle-template", "--text", '{"original_request":42}'),
            "expected string value",
        )

    def test_valid_unicode_file_stdin_and_text_keep_audit_output(self) -> None:
        text = "対象: 入力。目的: 日本語の監査。"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "入力.txt"
            path.write_text(text, encoding="utf-8")
            variants = [
                self.run_cli("audit-request", "--file", str(path)),
                self.run_cli("audit-request", input=text),
                self.run_cli("audit-request", "--text", text),
            ]
        for result in variants:
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, "")
            self.assertEqual(json.loads(result.stdout)["phase"], "audit_request")
        self.assertEqual([json.loads(r.stdout) for r in variants], [json.loads(variants[0].stdout)] * 3)
