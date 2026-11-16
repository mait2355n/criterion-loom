"""``--fail-on`` lets a script or CI job gate on the workflow audit status.

Without it a completed audit exits 0 whatever it found, so the status had to be
read from the JSON. The exit code is 3, the same value the canonical CLI uses.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import unittest

from semantic_guard.cli import main as canonical_main
from semantic_guard_workflow.cli import EXIT_AUDIT_DISPOSITION, main as workflow_main


PASS_ARGS = (
    "finish-check", "--text", "完了。残リスク: なし。",
    "--evidence", "検証証拠: pytest 8 passed。受入証拠: 対応表を確認済み。",
)
WARN_ARGS = ("finish-check", "--text", "完了。受入基準は満たしました。検証済み。残リスクなし。")
BLOCK_ARGS = ("finish-check", "--text", "実装した")


def _run(*args: str) -> tuple[int, dict[str, object]]:
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        code = workflow_main(list(args))
    return code or 0, json.loads(output.getvalue())


class FailOnTests(unittest.TestCase):
    def test_exit_code_three_matches_the_canonical_cli(self) -> None:
        self.assertEqual(EXIT_AUDIT_DISPOSITION, 3)

    def test_default_exit_code_does_not_depend_on_the_status(self) -> None:
        for args, status in ((PASS_ARGS, "pass"), (WARN_ARGS, "warn"), (BLOCK_ARGS, "block")):
            for explicit in ((), ("--fail-on", "never")):
                with self.subTest(status=status, explicit=explicit):
                    code, result = _run(*args, *explicit)
                    self.assertEqual(result["status"], status)
                    self.assertEqual(code, 0)

    def test_threshold_is_applied_after_the_json_is_written(self) -> None:
        expected = {
            ("warn", "pass"): 0, ("warn", "warn"): 3, ("warn", "block"): 3,
            ("block", "pass"): 0, ("block", "warn"): 0, ("block", "block"): 3,
        }
        for args, status in ((PASS_ARGS, "pass"), (WARN_ARGS, "warn"), (BLOCK_ARGS, "block")):
            for threshold in ("warn", "block"):
                with self.subTest(status=status, threshold=threshold):
                    code, result = _run(*args, "--fail-on", threshold)
                    self.assertEqual(result["status"], status)
                    self.assertEqual(code, expected[(threshold, status)])

    def test_every_status_bearing_audit_command_accepts_the_option(self) -> None:
        for command in (
            "explore-request", "understand-target", "audit-request", "audit-decision-state",
            "audit-plan", "audit-diff", "finish-check", "audit-conventions",
        ):
            with self.subTest(command=command):
                code, result = _run(command, "--text", "対象: 保存処理。未検証。", "--fail-on", "never")
                self.assertEqual(code, 0)
                self.assertIsInstance(result, dict)
        code, result = _run("audit-artifact-membership", "--text", "本文。", "--fail-on", "never")
        self.assertEqual(code, 0)
        self.assertIn(result["status"], {"pass", "warn", "block"})

    def test_canonical_route_propagates_the_exit_code(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = canonical_main(["workflow", *BLOCK_ARGS, "--fail-on", "block"])
        self.assertEqual(code, 3)
        self.assertEqual(json.loads(output.getvalue())["status"], "block")

    def test_process_exit_status_and_stdout_contract(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-m", "semantic_guard_workflow.cli", *BLOCK_ARGS, "--fail-on", "block"],
            capture_output=True, text=True, check=False,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        self.assertEqual(completed.returncode, 3, completed.stderr)
        self.assertEqual(completed.stderr, "")
        self.assertEqual(json.loads(completed.stdout)["status"], "block")


if __name__ == "__main__":
    unittest.main()
