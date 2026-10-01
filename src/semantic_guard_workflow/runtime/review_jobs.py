from __future__ import annotations

import subprocess
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from .review import (
    DEFAULT_CODEX_MODEL,
    DEFAULT_TIMEOUT_SECONDS,
    CodexExecReviewRequest,
    CodexExecReviewResult,
    Runner,
    build_codex_exec_command,
    run_codex_exec_review,
)
from semantic_guard_workflow.escalation import decide_escalation
from .jobs import BackgroundJobStore, JobRuntimeConfig, utc_now

_DONE_STATES = {"completed", "failed", "timed_out", "input_error", "not_needed", "not_found"}


@dataclass
class ReviewJob:
    job_id: str
    request: CodexExecReviewRequest
    metadata: dict[str, Any] = field(default_factory=dict)
    state: str = "queued"
    created_at: str = field(default_factory=utc_now)
    started_at: str | None = None
    finished_at: str | None = None
    result: CodexExecReviewResult | None = None
    errors: list[str] = field(default_factory=list)


class ReviewJobStore(BackgroundJobStore):
    """In-process background jobs for MCP callers that need pollable review state."""

    def __init__(self, max_jobs: int = 64) -> None:
        super().__init__(
            JobRuntimeConfig(
                job_factory=ReviewJob,
                run_request=_run_request,
                build_command=build_codex_exec_command,
                exception_result=_exception_result,
                response_state=_response_state,
                done_states=frozenset(_DONE_STATES),
                response_received_key="review_received",
                result_key="review_result",
                not_found_error="review job not found",
            ),
            max_jobs=max_jobs,
        )


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


def _run_request(request: CodexExecReviewRequest, runner: Runner) -> CodexExecReviewResult:
    return run_codex_exec_review(request, execute=True, runner=runner)


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
