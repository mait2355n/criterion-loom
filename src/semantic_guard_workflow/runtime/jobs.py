from __future__ import annotations

import threading
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from .codex_exec import Runner
from .process import run_agent_process

DEFAULT_MAX_JOBS = 64
DEFAULT_MAX_RUNNING_JOBS = 4


@dataclass(frozen=True)
class JobRuntimeConfig:
    job_factory: Callable[[str, Any, dict[str, Any]], Any]
    run_request: Callable[[Any, Runner], Any]
    build_command: Callable[[Any], list[str]]
    exception_result: Callable[[Any, Exception], Any]
    response_state: Callable[[Any], str]
    done_states: frozenset[str]
    response_received_key: str
    result_key: str
    not_found_error: str


class BackgroundJobStore:
    """Pollable jobs, bounded in both running processes and retained results.

    At most ``max_running`` jobs run at once and at most ``max_jobs`` are kept.
    Finished jobs whose result was already returned by :meth:`get` are dropped
    oldest first to make room; a result nobody has read yet is never dropped, so
    a start that would need that room is rejected with the reason instead.
    """

    def __init__(
        self,
        config: JobRuntimeConfig,
        *,
        max_jobs: int = DEFAULT_MAX_JOBS,
        max_running: int = DEFAULT_MAX_RUNNING_JOBS,
    ) -> None:
        self._config = config
        self._max_jobs = max_jobs
        self._max_running = max_running
        self._jobs: dict[str, Any] = {}
        self._delivered: set[str] = set()
        self._lock = threading.Lock()

    def start(
        self,
        request: Any,
        *,
        metadata: Mapping[str, Any] | None = None,
        runner: Runner = run_agent_process,
        include_prompt: bool = False,
    ) -> dict[str, Any]:
        job = self._config.job_factory(
            uuid.uuid4().hex,
            request,
            dict(metadata or {}),
        )
        thread = threading.Thread(target=self._run, args=(job.job_id, runner), daemon=True)
        with self._lock:
            refusal = self._admission_refusal_locked()
            if refusal is not None:
                return self._rejected(refusal)
            self._jobs[job.job_id] = job
        try:
            thread.start()
        except RuntimeError as exc:  # no thread could be created; do not leave a job that never runs
            with self._lock:
                self._jobs.pop(job.job_id, None)
            return self._rejected(f"cannot start a background thread: {exc}")
        return self.get(job.job_id, include_result=False, include_prompt=include_prompt)

    def get(self, job_id: str, *, include_result: bool = True, include_prompt: bool = False) -> dict[str, Any]:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return {
                    "job_id": job_id,
                    "state": "not_found",
                    "done": True,
                    "running": False,
                    "process_finished": False,
                    self._config.response_received_key: False,
                    "response_state": "not_found",
                    "valid": False,
                    "errors": [self._config.not_found_error],
                }
            if include_result and job.state in self._config.done_states:
                self._delivered.add(job_id)
            return self._snapshot(job, include_result=include_result, include_prompt=include_prompt)

    def _run(self, job_id: str, runner: Runner) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.state = "running"
            job.started_at = utc_now()
        try:
            result = self._config.run_request(job.request, runner)
        except Exception as exc:  # noqa: BLE001  # pragma: no cover - defensive boundary for injected runners.
            result = self._config.exception_result(job.request, exc)

        with self._lock:
            job = self._jobs[job_id]
            job.result = result
            job.state = _state_from_result(result)
            job.finished_at = utc_now()
            job.errors = list(result.errors)

    def _admission_refusal_locked(self) -> str | None:
        running = sum(1 for job in self._jobs.values() if job.state not in self._config.done_states)
        if running >= self._max_running:
            return f"{running} background jobs are already running (limit {self._max_running}); wait for one to finish and start again"
        while len(self._jobs) >= self._max_jobs:
            delivered = next((job_id for job_id in self._jobs if job_id in self._delivered), None)
            if delivered is None:
                kept = sum(1 for job in self._jobs.values() if job.state in self._config.done_states)
                return (
                    f"{len(self._jobs)} background jobs are retained (limit {self._max_jobs}) and {kept} finished "
                    "results have not been read yet; read them with the status tool and start again"
                )
            self._jobs.pop(delivered)
            self._delivered.discard(delivered)
        return None

    def _rejected(self, reason: str) -> dict[str, Any]:
        return {
            "job_id": None,
            "state": "rejected",
            "done": True,
            "running": False,
            "process_finished": False,
            self._config.response_received_key: False,
            "response_state": "rejected",
            "valid": False,
            "errors": [reason],
        }

    def _snapshot(self, job: Any, *, include_result: bool, include_prompt: bool) -> dict[str, Any]:
        result = job.result
        payload: dict[str, Any] = {
            "job_id": job.job_id,
            "state": job.state,
            "done": job.state in self._config.done_states,
            "running": job.state in {"queued", "running"},
            "process_finished": result is not None,
            self._config.response_received_key: bool(result and result.valid),
            "response_state": self._config.response_state(job),
            "created_at": job.created_at,
            "started_at": job.started_at,
            "finished_at": job.finished_at,
            "execution_status": result.execution_status if result is not None else None,
            "failure_kind": result.failure_kind if result is not None else None,
            "valid": bool(result and result.valid),
            "timed_out": bool(result and result.timed_out),
            "errors": list(result.errors if result is not None else job.errors),
            "command": self._config.build_command(job.request),
            "schema_path": str(job.request.schema_path),
            "metadata": dict(job.metadata) if include_prompt else without_payload(job.metadata),
        }
        if include_result and result is not None:
            result_payload = result.as_dict()
            if not include_prompt:
                result_payload = dict(result_payload)
                result_payload.pop("prompt", None)
            payload[self._config.result_key] = result_payload
        else:
            payload[self._config.result_key] = None
        return payload


def without_payload(values: Mapping[str, Any]) -> dict[str, Any]:
    """Copy ``values`` leaving out the ``payload`` of any nested mapping (the full text under review)."""
    return {
        key: {inner: item for inner, item in value.items() if inner != "payload"} if isinstance(value, Mapping) else value
        for key, value in values.items()
    }


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _state_from_result(result: Any) -> str:
    if result.valid:
        return "completed"
    if result.timed_out or result.execution_status == "timeout":
        return "timed_out"
    return "failed"
