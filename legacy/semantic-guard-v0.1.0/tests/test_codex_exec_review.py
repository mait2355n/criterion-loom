from __future__ import annotations

import json
import subprocess
import unittest
from typing import Any

from semantic_guard.codex_exec_review import (
    CodexExecReviewRequest,
    build_codex_exec_command,
    command_display,
    run_codex_exec_review,
)
from semantic_guard.llm_review import SCHEMA_VERSION


def _request(**overrides: Any) -> CodexExecReviewRequest:
    payload = {
        "candidate": "要求: 画面をいい感じに速くする。",
        "phase": "audit_request",
    }
    payload.update(overrides.pop("payload", {}))
    return CodexExecReviewRequest.from_mapping(payload, **overrides)


def _valid_review() -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "review_status": "needs_supplement",
        "missing_aspects": [
            {
                "kind": "acceptance_criteria",
                "severity": "major",
                "why_it_matters": "速いという要求を検証できない。",
                "supplement": "対象画面、計測条件、しきい値を明記する。",
            }
        ],
        "questionable_assumptions": [],
        "possible_counter_conditions": [],
        "supplement_proposals": [
            {
                "target": "request",
                "proposal": "初期表示を2秒未満にする、などの受入基準を置く。",
                "reason": "検証可能な速度要求へ変えるため。",
            }
        ],
        "rule_item_reviews": [
            {
                "rule_id": "req.verifiability.acceptance_missing",
                "inspected_items": ["concern", "applies_when", "evidence_required"],
                "missing_items": ["acceptance criteria"],
                "counter_condition_candidates": [],
                "supplement": "速度要求の受入条件を要求へ足す。",
                "notes": "追加注記なし。",
            }
        ],
        "human_decision_needed": [],
    }


class CodexExecReviewTests(unittest.TestCase):
    def test_build_command_uses_fixed_safe_options(self) -> None:
        request = _request(model="gpt-test", timeout_seconds=30, working_directory="/tmp/project")

        command = build_codex_exec_command(request)

        self.assertEqual(command[:2], ["codex", "exec"])
        self.assertIn("--ephemeral", command)
        self.assertIn("--ignore-user-config", command)
        self.assertIn("--ignore-rules", command)
        self.assertIn("--skip-git-repo-check", command)
        self.assertIn("--sandbox", command)
        self.assertIn("read-only", command)
        self.assertIn('approval_policy="never"', command)
        self.assertIn("--output-schema", command)
        self.assertIn("-m", command)
        self.assertIn("gpt-test", command)
        self.assertIn("--cd", command)
        self.assertIn("/tmp/project", command)
        self.assertNotIn("--ask-for-approval", command)
        self.assertEqual(command[-1], "-")

    def test_dry_run_does_not_call_runner(self) -> None:
        called = False

        def runner(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
            nonlocal called
            called = True
            return subprocess.CompletedProcess([], 0, stdout="", stderr="")

        result = run_codex_exec_review(_request(), execute=False, runner=runner)

        self.assertFalse(called)
        self.assertFalse(result.executed)
        self.assertEqual(result.execution_status, "dry_run")
        self.assertIn("candidate_gap_reviewer", result.prompt)
        self.assertFalse(result.valid)

    def test_execute_accepts_valid_review(self) -> None:
        calls: list[dict[str, object]] = []

        def runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            calls.append({"command": command, **kwargs})
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps(_valid_review()), stderr="")

        result = run_codex_exec_review(_request(timeout_seconds=42), execute=True, runner=runner)

        self.assertTrue(result.executed)
        self.assertTrue(result.valid)
        self.assertEqual(result.execution_status, "valid_review")
        self.assertEqual(result.failure_kind, None)
        self.assertEqual(result.review, _valid_review())
        self.assertEqual(calls[0]["timeout"], 42)
        self.assertEqual(calls[0]["text"], True)
        self.assertEqual(calls[0]["capture_output"], True)
        self.assertEqual(calls[0]["check"], False)
        self.assertIn("candidate_gap_reviewer", str(calls[0]["input"]))

    def test_execute_reports_non_zero_exit(self) -> None:
        def runner(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(command, 2, stdout="partial", stderr="failed")

        result = run_codex_exec_review(_request(), execute=True, runner=runner)

        self.assertFalse(result.valid)
        self.assertEqual(result.execution_status, "command_failed")
        self.assertEqual(result.failure_kind, "non_zero_exit")
        self.assertEqual(result.returncode, 2)
        self.assertIn("status 2", result.errors[0])

    def test_execute_reports_invalid_json(self) -> None:
        def runner(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(command, 0, stdout="not json", stderr="")

        result = run_codex_exec_review(_request(), execute=True, runner=runner)

        self.assertFalse(result.valid)
        self.assertEqual(result.execution_status, "invalid_review")
        self.assertEqual(result.failure_kind, "invalid_json")
        self.assertTrue(any("invalid JSON" in error for error in result.errors))

    def test_execute_reports_schema_mismatch(self) -> None:
        invalid = _valid_review()
        invalid.pop("rule_item_reviews")

        def runner(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps(invalid), stderr="")

        result = run_codex_exec_review(_request(), execute=True, runner=runner)

        self.assertFalse(result.valid)
        self.assertEqual(result.execution_status, "invalid_review")
        self.assertEqual(result.failure_kind, "schema_mismatch")
        self.assertTrue(any("rule_item_reviews" in error for error in result.errors))

    def test_execute_reports_timeout(self) -> None:
        def runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            raise subprocess.TimeoutExpired(
                cmd=command,
                timeout=kwargs["timeout"],
                output="partial",
                stderr="late",
            )

        result = run_codex_exec_review(_request(timeout_seconds=1), execute=True, runner=runner)

        self.assertTrue(result.executed)
        self.assertTrue(result.timed_out)
        self.assertFalse(result.valid)
        self.assertEqual(result.execution_status, "timeout")
        self.assertEqual(result.failure_kind, "timeout")
        self.assertEqual(result.stdout, "partial")
        self.assertEqual(result.stderr, "late")

    def test_command_display_quotes_prompt_marker_safely(self) -> None:
        display = command_display(["codex", "exec", "--cd", "/tmp/has space", "-"])

        self.assertEqual(display, "codex exec --cd '/tmp/has space' -")


if __name__ == "__main__":
    unittest.main()
