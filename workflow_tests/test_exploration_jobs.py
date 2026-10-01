import json
import subprocess
import threading
import time
import unittest
from typing import Any

from semantic_guard_workflow.codex_exec_exploration import CodexExecExplorationRequest
from semantic_guard_workflow.exploration_jobs import ExplorationJobStore
from semantic_guard_workflow.request_exploration_review import RequestExplorationInput
from workflow_tests.test_request_exploration_review import VALID_EXPLORATION


def _request(**overrides: Any) -> CodexExecExplorationRequest:
    return CodexExecExplorationRequest(
        RequestExplorationInput(text="割り勘アプリを作りたい"),
        **overrides,
    )


def _wait_for_done(store: ExplorationJobStore, job_id: str) -> dict[str, Any]:
    deadline = time.monotonic() + 2
    snapshot: dict[str, Any] = {}
    while time.monotonic() < deadline:
        snapshot = store.get(job_id)
        if snapshot["done"]:
            return snapshot
        time.sleep(0.01)
    raise AssertionError(f"job did not finish: {snapshot}")


class ExplorationJobStoreTests(unittest.TestCase):
    def test_missing_job_reports_not_found(self) -> None:
        store = ExplorationJobStore()

        result = store.get("missing")

        self.assertEqual(result["state"], "not_found")
        self.assertTrue(result["done"])
        self.assertFalse(result["exploration_received"])
        self.assertEqual(result["errors"], ["exploration job not found"])

    def test_job_reports_running_then_completed(self) -> None:
        store = ExplorationJobStore()
        started = threading.Event()
        release = threading.Event()

        def runner(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            started.set()
            release.wait(1)
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps(VALID_EXPLORATION), stderr="")

        first = store.start(_request(), runner=runner)
        self.assertIn(first["state"], {"queued", "running"})
        self.assertTrue(first["running"])

        self.assertTrue(started.wait(1))
        running = store.get(first["job_id"])
        self.assertEqual(running["state"], "running")
        self.assertFalse(running["done"])
        self.assertEqual(running["response_state"], "pending")

        release.set()
        final = _wait_for_done(store, first["job_id"])
        self.assertEqual(final["state"], "completed")
        self.assertFalse(final["running"])
        self.assertTrue(final["process_finished"])
        self.assertTrue(final["exploration_received"])
        self.assertEqual(final["response_state"], "valid_exploration")
        self.assertTrue(final["valid"])
        self.assertEqual(final["exploration_result"]["execution_status"], "valid_exploration")
        self.assertNotIn("prompt", final["exploration_result"])
        self.assertEqual(
            set(final),
            {
                "job_id",
                "state",
                "done",
                "running",
                "process_finished",
                "exploration_received",
                "response_state",
                "created_at",
                "started_at",
                "finished_at",
                "execution_status",
                "failure_kind",
                "valid",
                "timed_out",
                "errors",
                "command",
                "schema_path",
                "metadata",
                "exploration_result",
            },
        )

    def test_job_maps_timeout_to_timed_out(self) -> None:
        store = ExplorationJobStore()

        def runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            raise subprocess.TimeoutExpired(cmd=command, timeout=kwargs["timeout"], output="partial", stderr="late")

        initial = store.start(_request(timeout_seconds=1), runner=runner)
        done = _wait_for_done(store, initial["job_id"])

        self.assertEqual(done["state"], "timed_out")
        self.assertTrue(done["timed_out"])
        self.assertEqual(done["response_state"], "timed_out")
        self.assertEqual(done["failure_kind"], "timeout")

    def test_job_maps_invalid_exploration_to_failed(self) -> None:
        store = ExplorationJobStore()

        def runner(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(command, 0, stdout="not json", stderr="")

        initial = store.start(_request(), runner=runner)
        done = _wait_for_done(store, initial["job_id"])

        self.assertEqual(done["state"], "failed")
        self.assertEqual(done["response_state"], "invalid_exploration")
        self.assertEqual(done["failure_kind"], "invalid_json")
        self.assertFalse(done["valid"])

    def test_job_maps_unexpected_runner_exception_to_failed(self) -> None:
        store = ExplorationJobStore()

        def runner(_command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            raise ValueError("runner broke")

        initial = store.start(_request(), runner=runner)
        done = _wait_for_done(store, initial["job_id"])

        self.assertEqual(done["state"], "failed")
        self.assertEqual(done["response_state"], "no_valid_exploration")
        self.assertEqual(done["execution_status"], "job_failed")
        self.assertEqual(done["failure_kind"], "job_exception")
        self.assertEqual(done["errors"], ["runner broke"])

    def test_start_prunes_oldest_completed_job_over_capacity(self) -> None:
        store = ExplorationJobStore(max_jobs=1)

        def runner(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps(VALID_EXPLORATION), stderr="")

        first = store.start(_request(), runner=runner)
        _wait_for_done(store, first["job_id"])

        second = store.start(_request(), runner=runner)

        self.assertEqual(store.get(first["job_id"])["state"], "not_found")
        self.assertEqual(_wait_for_done(store, second["job_id"])["state"], "completed")


if __name__ == "__main__":
    unittest.main()
