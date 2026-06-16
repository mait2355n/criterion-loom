import json
import subprocess
import unittest

from semantic_guard.codex_exec_exploration import CodexExecExplorationRequest, run_codex_exec_exploration
from semantic_guard.request_exploration_review import RequestExplorationInput
from tests.test_request_exploration_review import VALID_EXPLORATION


class CodexExecExplorationTests(unittest.TestCase):
    def test_dry_run_does_not_call_runner(self) -> None:
        request = CodexExecExplorationRequest(RequestExplorationInput(text="割り勘アプリを作りたい"))

        def runner(*args, **kwargs):  # pragma: no cover - should not be called
            raise AssertionError("runner should not be called")

        result = run_codex_exec_exploration(request, execute=False, runner=runner)

        self.assertFalse(result.executed)
        self.assertEqual(result.execution_status, "dry_run")
        self.assertIn("codex", result.command)
        self.assertIn("request_exploration_interviewer", result.prompt)

    def test_execute_accepts_valid_exploration(self) -> None:
        request = CodexExecExplorationRequest(RequestExplorationInput(text="割り勘アプリを作りたい"))

        def runner(*args, **kwargs):
            return subprocess.CompletedProcess(args=args[0], returncode=0, stdout=json.dumps(VALID_EXPLORATION), stderr="")

        result = run_codex_exec_exploration(request, execute=True, runner=runner)

        self.assertTrue(result.executed)
        self.assertTrue(result.valid)
        self.assertEqual(result.execution_status, "valid_exploration")
        self.assertEqual(result.exploration["schema_version"], "request-exploration-review/v1")

    def test_execute_rejects_schema_mismatch(self) -> None:
        request = CodexExecExplorationRequest(RequestExplorationInput(text="割り勘アプリを作りたい"))
        payload = dict(VALID_EXPLORATION)
        payload.pop("questions")

        def runner(*args, **kwargs):
            return subprocess.CompletedProcess(args=args[0], returncode=0, stdout=json.dumps(payload), stderr="")

        result = run_codex_exec_exploration(request, execute=True, runner=runner)

        self.assertFalse(result.valid)
        self.assertEqual(result.execution_status, "invalid_exploration")
        self.assertEqual(result.failure_kind, "schema_mismatch")
        self.assertIn("missing required field: questions", result.errors)


if __name__ == "__main__":
    unittest.main()
