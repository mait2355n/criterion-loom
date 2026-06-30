from __future__ import annotations

import subprocess
import threading
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Mapping

from semantic_guard.codex_exec_review import (
    DEFAULT_CODEX_MODEL,
    DEFAULT_TIMEOUT_SECONDS,
    CodexExecReviewRequest,
    CodexExecReviewResult,
    Runner,
    build_codex_exec_command,
    run_codex_exec_review,
)
from semantic_guard.escalation import decide_escalation


_DONE_STATES = {"completed", "failed", "timed_out", "input_error", "not_needed", "not_found"}


@dataclass
class ReviewJob:
    job_id: str
    request: CodexExecReviewRequest
    metadata: dict[str, Any] = field(default_factory=dict)
    state: str = "queued"
    created_at: str = field(default_factory=lambda: _now())
    started_at: str | None = None
    finished_at: str | None = None
    result: CodexExecReviewResult | None = None
    errors: list[str] = field(default_factory=list)


class ReviewJobStore:
    """In-process background jobs for MCP callers that need pollable review state."""

    def __init__(self, max_jobs: int = 64) -> None:
        self._max_jobs = max_jobs
        self._jobs: dict[str, ReviewJob] = {}
        self._lock = threading.Lock()

    def start(
        self,
        request: CodexExecReviewRequest,
        *,
        metadata: Mapping[str, Any] | None = None,
        runner: Runner = subprocess.run,
        include_prompt: bool = False,
    ) -> dict[str, Any]:
        job = ReviewJob(
            job_id=uuid.uuid4().hex,
            request=request,
            metadata=dict(metadata or {}),
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
                    "review_received": False,
                    "response_state": "not_found",
                    "valid": False,
                    "errors": ["review job not found"],
                }
            return _snapshot(job, include_result=include_result, include_prompt=include_prompt)

    def _run(self, job_id: str, runner: Runner) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.state = "running"
            job.started_at = _now()
        try:
            result = run_codex_exec_review(job.request, execute=True, runner=runner)
        except Exception as exc:  # pragma: no cover - defensive boundary for injected runners.
            result = _exception_result(job.request, exc)

        with self._lock:
            job = self._jobs[job_id]
            job.result = result
            job.state = _state_from_result(result)
            job.finished_at = _now()
            job.errors = list(result.errors)

    def _prune_locked(self) -> None:
        overflow = len(self._jobs) - self._max_jobs
        if overflow <= 0:
            return
        removable = [job_id for job_id, job in self._jobs.items() if job.state in _DONE_STATES]
        for job_id in removable[:overflow]:
            self._jobs.pop(job_id, None)


def start_review_if_needed_job(
    store: ReviewJobStore,
    payload: Mapping[str, Any],
    *,
    model: str = DEFAULT_CODEX_MODEL,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    working_directory: str = "",
    include_schema: bool = False,
    runner: Runner = subprocess.run,
) -> dict[str, Any]:
    audit = _mapping(payload.get("deterministic_audit") or payload.get("audit_result"))
    phase = _string(payload.get("phase")) or _string(audit.get("phase"))
    decision = decide_escalation(
        candidate=_string(payload.get("candidate")),
        phase=phase,
        deterministic_audit=audit,
        request=_string(payload.get("request")),
        constraints=_string(payload.get("constraints")),
        non_goals=_string(payload.get("non_goals")),
        unknowns=_string(payload.get("unknowns")),
        context=_string(payload.get("context")),
        review_context=_mapping(payload.get("review_context") or payload.get("routing_context")),
        mode="execute",
    )
    if not decision["needed"]:
        return {
            "job_id": None,
            "state": "not_needed",
            "done": True,
            "running": False,
            "process_finished": False,
            "review_received": False,
            "response_state": "not_needed",
            "valid": True,
            "errors": [],
            "escalation": decision,
            "review_result": None,
        }

    try:
        request = CodexExecReviewRequest.from_mapping(
            decision["payload"],
            model=model,
            timeout_seconds=timeout_seconds,
            working_directory=working_directory or None,
            codex_binary="codex",
            include_schema_in_prompt=include_schema,
        )
    except ValueError as exc:
        return {
            "job_id": None,
            "state": "input_error",
            "done": True,
            "running": False,
            "process_finished": False,
            "review_received": False,
            "response_state": "input_error",
            "valid": False,
            "errors": [str(exc)],
            "escalation": decision,
            "review_result": {
                "executed": False,
                "execution_status": "input_error",
                "valid": False,
                "errors": [str(exc)],
            },
        }

    snapshot = store.start(
        request,
        metadata={"kind": "review_if_needed", "escalation": decision},
        runner=runner,
    )
    snapshot["escalation"] = decision
    return snapshot


def _snapshot(job: ReviewJob, *, include_result: bool, include_prompt: bool) -> dict[str, Any]:
    result = job.result
    command = build_codex_exec_command(job.request)
    payload: dict[str, Any] = {
        "job_id": job.job_id,
        "state": job.state,
        "done": job.state in _DONE_STATES,
        "running": job.state in {"queued", "running"},
        "process_finished": result is not None,
        "review_received": bool(result and result.valid),
        "response_state": _response_state(job),
        "created_at": job.created_at,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
        "execution_status": result.execution_status if result is not None else None,
        "failure_kind": result.failure_kind if result is not None else None,
        "valid": bool(result and result.valid),
        "timed_out": bool(result and result.timed_out),
        "errors": list(result.errors if result is not None else job.errors),
        "command": command,
        "schema_path": str(job.request.schema_path),
        "metadata": dict(job.metadata),
    }
    if include_result and result is not None:
        result_payload = result.as_dict()
        if not include_prompt:
            result_payload = dict(result_payload)
            result_payload.pop("prompt", None)
        payload["review_result"] = result_payload
    else:
        payload["review_result"] = None
    return payload


def _response_state(job: ReviewJob) -> str:
    result = job.result
    if result is None:
        return "pending"
    if result.valid:
        return "valid_review"
    if result.execution_status == "invalid_review":
        return "invalid_review"
    if result.execution_status == "timeout":
        return "timed_out"
    return "no_valid_review"


def _state_from_result(result: CodexExecReviewResult) -> str:
    if result.valid:
        return "completed"
    if result.timed_out or result.execution_status == "timeout":
        return "timed_out"
    return "failed"


def _exception_result(request: CodexExecReviewRequest, exc: Exception) -> CodexExecReviewResult:
    return CodexExecReviewResult(
        executed=True,
        execution_status="job_failed",
        command=build_codex_exec_command(request),
        schema_path=str(request.schema_path),
        prompt=request.prompt,
        valid=False,
        errors=[str(exc)],
        failure_kind="job_exception",
    )


def _mapping(value: object) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _string(value: object) -> str:
    if isinstance(value, str):
        return value
    return ""


def _now() -> str:
    return datetime.now(UTC).isoformat()
