import json
import subprocess
import time
import unittest

from semantic_guard.codex_exec_exploration import CodexExecExplorationRequest
from semantic_guard.exploration_jobs import ExplorationJobStore
from semantic_guard.request_exploration_review import RequestExplorationInput
from tests.test_request_exploration_review import VALID_EXPLORATION


class ExplorationJobStoreTests(unittest.TestCase):
    def test_missing_job_reports_not_found(self) -> None:
        store = ExplorationJobStore()

        result = store.get("missing")

        self.assertEqual(result["state"], "not_found")
        self.assertTrue(result["done"])
        self.assertFalse(result["exploration_received"])

    def test_job_reports_running_then_completed(self) -> None:
        store = ExplorationJobStore()
        request = CodexExecExplorationRequest(RequestExplorationInput(text="割り勘アプリを作りたい"))

        def runner(*args, **kwargs):
            time.sleep(0.02)
            return subprocess.CompletedProcess(args=args[0], returncode=0, stdout=json.dumps(VALID_EXPLORATION), stderr="")

        first = store.start(request, runner=runner)
        self.assertIn(first["state"], {"queued", "running"})

        final = first
        for _ in range(20):
            final = store.get(first["job_id"])
            if final["done"]:
                break
            time.sleep(0.01)

        self.assertEqual(final["state"], "completed")
        self.assertTrue(final["exploration_received"])
        self.assertEqual(final["response_state"], "valid_exploration")
        self.assertTrue(final["valid"])


if __name__ == "__main__":
    unittest.main()
