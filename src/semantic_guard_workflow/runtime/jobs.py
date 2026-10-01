from __future__ import annotations

import subprocess
import threading
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from .codex_exec import Runner


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
    def __init__(self, config: JobRuntimeConfig, *, max_jobs: int = 64) -> None:
        self._config = config
        self._max_jobs = max_jobs
        self._jobs: dict[str, Any] = {}
        self._lock = threading.Lock()

    def start(
        self,
        request: Any,
        *,
        metadata: Mapping[str, Any] | None = None,
        runner: Runner = subprocess.run,
        include_prompt: bool = False,
    ) -> dict[str, Any]:
        job = self._config.job_factory(
            uuid.uuid4().hex,
            request,
            dict(metadata or {}),
        )
        thread = threading.Thread(target=self._run, args=(job.job_id, runner), daemon=True)
        with self._lock:
            self._jobs[job.job_id] = job
            self._prune_locked()
        thread.start()
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

    def _prune_locked(self) -> None:
        overflow = len(self._jobs) - self._max_jobs
        if overflow <= 0:
            return
        removable = [job_id for job_id, job in self._jobs.items() if job.state in self._config.done_states]
        for job_id in removable[:overflow]:
            self._jobs.pop(job_id, None)

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
            "metadata": dict(job.metadata),
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


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _state_from_result(result: Any) -> str:
    if result.valid:
        return "completed"
    if result.timed_out or result.execution_status == "timeout":
        return "timed_out"
    return "failed"
