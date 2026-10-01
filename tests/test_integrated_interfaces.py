"""User-facing routing checks; each engine retains its own result contract."""
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from semantic_guard.cli import main


REQUIREMENT = """Purpose: 検索APIが検索結果を p95 500ms以内で返す
User: 検索API
Scenario: 検索APIが検索要求を処理して検索結果を返す
Expected result: 検索結果を p95 500ms以内で返す
Acceptance criteria: 検索応答時間 p95 500ms 以下
Verification method: 検索結果の検索応答時間を benchmark で測定する
Evidence: 検索結果の検索応答時間 benchmark report"""
OBSERVED_AT = "2026-10-01T00:00:00Z"


class IntegratedInterfaceTests(unittest.TestCase):
    def invoke(self, *args):
        output = StringIO()
        with redirect_stdout(output):
            status = main(args)
        return status, json.loads(output.getvalue())

    def test_canonical_workflow_candidate_remain_distinct_in_one_process(self):
        canonical_status, canonical = self.invoke(
            "audit-requirement", "--text", REQUIREMENT,
            "--recorded-at", OBSERVED_AT,
        )
        workflow_status, workflow = self.invoke(
            "workflow", "audit-request", "--text", REQUIREMENT,
        )
        candidate_status, candidate = self.invoke(
            "candidate", "audit-requirement", "--text", REQUIREMENT,
            "--recorded-at", OBSERVED_AT,
        )
        self.assertEqual(canonical_status, 0)
        self.assertEqual(canonical["schema_version"], "semantic-guard-audit-result/v0")
        self.assertEqual(workflow_status, 0)
        self.assertEqual(workflow["phase"], "audit_request")
        self.assertNotIn("schema_version", workflow)
        self.assertEqual(candidate_status, 3)
        self.assertEqual(candidate["schema_version"], "governed-requirement-audit/v1")
        self.assertEqual(candidate["assurance_assessment"]["workflow_disposition"], "block")
        self.assertEqual(candidate["assurance_assessment"]["formal_verdict_authority"], "none")
        # Loading the old engine and candidate must not replace canonical imports.
        after_status, after = self.invoke(
            "audit-requirement", "--text", REQUIREMENT,
            "--recorded-at", OBSERVED_AT,
        )
        self.assertEqual((after_status, after), (canonical_status, canonical))

    def test_workflow_plan_diff_finish_are_reachable_without_argument_rewriting(self):
        original_argv = list(sys.argv)
        for command, phase in (
            ("audit-plan", "audit_plan"),
            ("audit-diff", "audit_diff"),
            ("finish-check", "finish_check"),
        ):
            with self.subTest(command=command):
                status, result = self.invoke(
                    "workflow", command, "--text", "対象: 保存処理。未検証。",
                )
                self.assertEqual(status, 0)
                self.assertEqual(result["phase"], phase)
                self.assertIn(result["status"], {"pass", "warn", "block"})
        self.assertEqual(sys.argv, original_argv)

    def test_help_and_invalid_arguments_are_owned_by_selected_interface(self):
        for route in ("workflow", "candidate"):
            with self.subTest(route=route):
                help_output = StringIO()
                with redirect_stdout(help_output), self.assertRaises(SystemExit) as exc:
                    main((route, "--help"))
                self.assertEqual(exc.exception.code, 0)
                self.assertIn("audit-", help_output.getvalue())
                with redirect_stderr(StringIO()), self.assertRaises(SystemExit) as exc:
                    main((route, "not-a-command"))
                self.assertEqual(exc.exception.code, 2)

    def test_canonical_launch_does_not_import_or_start_other_engines(self):
        program = """
import contextlib, io, sys
from semantic_guard.cli import main
with contextlib.redirect_stdout(io.StringIO()):
    assert main(['schema', 'audit-result']) == 0
assert not any(n.startswith(('semantic_guard_workflow', 'semantic_guard_vnext',
                             'semantic_guard_u10_broker')) for n in sys.modules)
"""
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, "-I", "-c", program], cwd=directory,
                capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_cli_file_input_runs_from_unrelated_working_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "plan.txt"
            path.write_text("目的: 保存する。未検証。", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "-I", "-m", "semantic_guard.cli", "workflow",
                 "audit-plan", "--file", str(path)],
                cwd=directory, capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["phase"], "audit_plan")
