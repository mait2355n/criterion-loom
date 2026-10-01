import json
import subprocess
import unittest
from typing import Any

from semantic_guard_workflow.codex_exec_exploration import (
    CodexExecExplorationRequest,
    build_codex_exec_exploration_command,
    command_display,
    run_codex_exec_exploration,
)
from semantic_guard_workflow.request_exploration_review import RequestExplorationInput
from workflow_tests.test_request_exploration_review import VALID_EXPLORATION


def _request(**overrides: Any) -> CodexExecExplorationRequest:
    return CodexExecExplorationRequest(
        RequestExplorationInput(text="割り勘アプリを作りたい"),
        **overrides,
    )


class CodexExecExplorationTests(unittest.TestCase):
    def test_build_command_uses_fixed_safe_options(self) -> None:
        request = _request(model="gpt-test", timeout_seconds=30, working_directory="/tmp/project")

        command = build_codex_exec_exploration_command(request)

        self.assertEqual(
            command,
            [
                "codex",
                "exec",
                "--ephemeral",
                "--ignore-user-config",
                "--ignore-rules",
                "--skip-git-repo-check",
                "--sandbox",
                "read-only",
                "-c",
                'approval_policy="never"',
                "--output-schema",
                str(request.schema_path),
                "-m",
                "gpt-test",
                "--cd",
                "/tmp/project",
                "-",
            ],
        )

    def test_dry_run_does_not_call_runner(self) -> None:
        request = _request()

        def runner(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
            raise AssertionError("runner should not be called")

        result = run_codex_exec_exploration(request, execute=False, runner=runner)

        self.assertFalse(result.executed)
        self.assertEqual(result.execution_status, "dry_run")
        self.assertIn("codex", result.command)
        self.assertIn("request_exploration_interviewer", result.prompt)

    def test_execute_accepts_valid_exploration(self) -> None:
        request = _request(timeout_seconds=42, working_directory="/tmp/project")
        calls: list[dict[str, object]] = []

        def runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            calls.append({"command": command, **kwargs})
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps(VALID_EXPLORATION), stderr="")

        result = run_codex_exec_exploration(request, execute=True, runner=runner)

        self.assertTrue(result.executed)
        self.assertTrue(result.valid)
        self.assertEqual(result.execution_status, "valid_exploration")
        self.assertIsNone(result.failure_kind)
        self.assertEqual(result.exploration["schema_version"], "request-exploration-review/v1")
        self.assertEqual(
            list(result.as_dict()),
            [
                "executed",
                "execution_status",
                "command",
                "schema_path",
                "prompt",
                "returncode",
                "stdout",
                "stderr",
                "timed_out",
                "valid",
                "errors",
                "exploration",
                "failure_kind",
            ],
        )
        self.assertEqual(calls[0]["timeout"], 42)
        self.assertEqual(calls[0]["text"], True)
        self.assertEqual(calls[0]["capture_output"], True)
        self.assertEqual(calls[0]["check"], False)
        self.assertEqual(calls[0]["cwd"], "/tmp/project")
        self.assertIn("request_exploration_interviewer", str(calls[0]["input"]))

    def test_execute_reports_non_zero_exit(self) -> None:
        def runner(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(command, 2, stdout="partial", stderr="failed")

        result = run_codex_exec_exploration(_request(), execute=True, runner=runner)

        self.assertFalse(result.valid)
        self.assertEqual(result.execution_status, "command_failed")
        self.assertEqual(result.failure_kind, "non_zero_exit")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.errors, ["codex exec exited with status 2"])

    def test_execute_reports_invalid_json(self) -> None:
        def runner(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(command, 0, stdout="not json", stderr="")

        result = run_codex_exec_exploration(_request(), execute=True, runner=runner)

        self.assertFalse(result.valid)
        self.assertEqual(result.execution_status, "invalid_exploration")
        self.assertEqual(result.failure_kind, "invalid_json")
        self.assertTrue(any("invalid JSON" in error for error in result.errors))

    def test_execute_reports_missing_output(self) -> None:
        def runner(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

        result = run_codex_exec_exploration(_request(), execute=True, runner=runner)

        self.assertEqual(result.execution_status, "invalid_exploration")
        self.assertEqual(result.failure_kind, "invalid_json")
        self.assertEqual(result.errors, ["missing exploration output"])

    def test_execute_reports_non_object_output(self) -> None:
        def runner(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(command, 0, stdout="[]", stderr="")

        result = run_codex_exec_exploration(_request(), execute=True, runner=runner)

        self.assertEqual(result.execution_status, "invalid_exploration")
        self.assertEqual(result.failure_kind, "invalid_json")
        self.assertEqual(result.errors, ["exploration output must be a JSON object"])

    def test_execute_reports_schema_mismatch(self) -> None:
        payload = dict(VALID_EXPLORATION)
        payload.pop("questions")

        def runner(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps(payload), stderr="")

        result = run_codex_exec_exploration(_request(), execute=True, runner=runner)

        self.assertFalse(result.valid)
        self.assertEqual(result.execution_status, "invalid_exploration")
        self.assertEqual(result.failure_kind, "schema_mismatch")
        self.assertIn("missing required field: questions", result.errors)

    def test_execute_reports_timeout(self) -> None:
        def runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            raise subprocess.TimeoutExpired(
                cmd=command,
                timeout=kwargs["timeout"],
                output="partial",
                stderr="late",
            )

        result = run_codex_exec_exploration(_request(timeout_seconds=1), execute=True, runner=runner)

        self.assertTrue(result.executed)
        self.assertTrue(result.timed_out)
        self.assertFalse(result.valid)
        self.assertEqual(result.execution_status, "timeout")
        self.assertEqual(result.failure_kind, "timeout")
        self.assertEqual(result.stdout, "partial")
        self.assertEqual(result.stderr, "late")
        self.assertEqual(result.errors, ["codex exec timed out after 1 seconds"])

    def test_execute_reports_execution_error(self) -> None:
        def runner(_command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            raise OSError("codex unavailable")

        result = run_codex_exec_exploration(_request(), execute=True, runner=runner)

        self.assertTrue(result.executed)
        self.assertFalse(result.valid)
        self.assertEqual(result.execution_status, "execution_error")
        self.assertEqual(result.failure_kind, "execution_error")
        self.assertEqual(result.stderr, "codex unavailable")
        self.assertEqual(result.errors, ["codex unavailable"])

    def test_command_display_quotes_prompt_marker_safely(self) -> None:
        display = command_display(["codex", "exec", "--cd", "/tmp/has space", "-"])

        self.assertEqual(display, "codex exec --cd '/tmp/has space' -")


if __name__ == "__main__":
    unittest.main()
