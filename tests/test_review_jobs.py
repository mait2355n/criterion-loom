from __future__ import annotations

import json
import subprocess
import threading
import time
import unittest
from typing import Any

from semantic_guard.codex_exec_review import CodexExecReviewRequest
from semantic_guard.llm_review import SCHEMA_VERSION
from semantic_guard.review_jobs import ReviewJobStore, start_review_if_needed_job


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
        "supplement_proposals": [],
        "rule_item_reviews": [],
        "human_decision_needed": [],
    }


def _wait_for_done(store: ReviewJobStore, job_id: str) -> dict[str, Any]:
    deadline = time.monotonic() + 2
    snapshot: dict[str, Any] = {}
    while time.monotonic() < deadline:
        snapshot = store.get(job_id)
        if snapshot["done"]:
            return snapshot
        time.sleep(0.01)
    raise AssertionError(f"job did not finish: {snapshot}")


class ReviewJobStoreTests(unittest.TestCase):
    def test_job_reports_running_then_completed(self) -> None:
        store = ReviewJobStore()
        started = threading.Event()
        release = threading.Event()

        def runner(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            started.set()
            release.wait(1)
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps(_valid_review()), stderr="")

        initial = store.start(_request(), runner=runner)
        self.assertIn(initial["state"], {"queued", "running"})
        self.assertTrue(initial["running"])

        self.assertTrue(started.wait(1))
        running = store.get(initial["job_id"])
        self.assertEqual(running["state"], "running")
        self.assertFalse(running["done"])
        self.assertEqual(running["response_state"], "pending")

        release.set()
        done = _wait_for_done(store, initial["job_id"])
        self.assertEqual(done["state"], "completed")
        self.assertFalse(done["running"])
        self.assertTrue(done["process_finished"])
        self.assertTrue(done["review_received"])
        self.assertEqual(done["response_state"], "valid_review")
        self.assertTrue(done["valid"])
        self.assertEqual(done["review_result"]["execution_status"], "valid_review")
        self.assertNotIn("prompt", done["review_result"])

    def test_job_maps_timeout_to_timed_out(self) -> None:
        store = ReviewJobStore()

        def runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            raise subprocess.TimeoutExpired(cmd=command, timeout=kwargs["timeout"], output="partial", stderr="late")

        initial = store.start(_request(timeout_seconds=1), runner=runner)
        done = _wait_for_done(store, initial["job_id"])

        self.assertEqual(done["state"], "timed_out")
        self.assertTrue(done["timed_out"])
        self.assertEqual(done["response_state"], "timed_out")
        self.assertEqual(done["failure_kind"], "timeout")

    def test_job_maps_invalid_review_to_failed(self) -> None:
        store = ReviewJobStore()

        def runner(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(command, 0, stdout="not json", stderr="")

        initial = store.start(_request(), runner=runner)
        done = _wait_for_done(store, initial["job_id"])

        self.assertEqual(done["state"], "failed")
        self.assertEqual(done["response_state"], "invalid_review")
        self.assertEqual(done["failure_kind"], "invalid_json")
        self.assertFalse(done["valid"])

    def test_missing_job_reports_not_found(self) -> None:
        store = ReviewJobStore()

        result = store.get("missing")

        self.assertEqual(result["state"], "not_found")
        self.assertTrue(result["done"])
        self.assertEqual(result["errors"], ["review job not found"])

    def test_review_if_needed_start_returns_not_needed_without_job(self) -> None:
        store = ReviewJobStore()

        result = start_review_if_needed_job(
            store,
            {
                "candidate": "要求: 利用者: 保守者。目的: 設定を保存する。受入基準: 設定が保存される。",
                "phase": "audit_request",
                "deterministic_audit": {"phase": "audit_request", "status": "pass", "score": 1.0, "findings": []},
            },
        )

        self.assertEqual(result["state"], "not_needed")
        self.assertIsNone(result["job_id"])
        self.assertFalse(result["escalation"]["needed"])

    def test_review_if_needed_start_creates_job_when_needed(self) -> None:
        store = ReviewJobStore()

        def runner(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps(_valid_review()), stderr="")

        result = start_review_if_needed_job(
            store,
            {
                "candidate": "計画本文",
                "phase": "audit_plan",
                "deterministic_audit": {
                    "phase": "audit_plan",
                    "status": "warn",
                    "score": 0.82,
                    "findings": [
                        {
                            "severity": "major",
                            "category": "planning",
                            "finding": "計画に verification_plan が見えない。",
                            "warning_class": "possible false positive",
                            "nearest_candidates": ["点検方針: 人間が画面を見る。"],
                        }
                    ],
                },
            },
            runner=runner,
        )

        self.assertTrue(result["escalation"]["needed"])
        self.assertIsNotNone(result["job_id"])
        done = _wait_for_done(store, result["job_id"])
        self.assertEqual(done["state"], "completed")
        self.assertTrue(done["metadata"]["escalation"]["needed"])


if __name__ == "__main__":
    unittest.main()
