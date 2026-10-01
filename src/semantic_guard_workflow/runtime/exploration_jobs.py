from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .exploration import (
    CodexExecExplorationRequest,
    CodexExecExplorationResult,
    Runner,
    build_codex_exec_exploration_command,
    run_codex_exec_exploration,
)
from .jobs import BackgroundJobStore, JobRuntimeConfig, utc_now

_DONE_STATES = {"completed", "failed", "timed_out", "input_error", "not_found"}


@dataclass
class ExplorationJob:
    job_id: str
    request: CodexExecExplorationRequest
    metadata: dict[str, Any] = field(default_factory=dict)
    state: str = "queued"
    created_at: str = field(default_factory=utc_now)
    started_at: str | None = None
    finished_at: str | None = None
    result: CodexExecExplorationResult | None = None
    errors: list[str] = field(default_factory=list)


class ExplorationJobStore(BackgroundJobStore):
    """In-process background jobs for LLM exploration calls."""

    def __init__(self, max_jobs: int = 64) -> None:
        super().__init__(
            JobRuntimeConfig(
                job_factory=ExplorationJob,
                run_request=_run_request,
                build_command=build_codex_exec_exploration_command,
                exception_result=_exception_result,
                response_state=_response_state,
                done_states=frozenset(_DONE_STATES),
                response_received_key="exploration_received",
                result_key="exploration_result",
                not_found_error="exploration job not found",
            ),
            max_jobs=max_jobs,
        )


def _response_state(job: ExplorationJob) -> str:
    result = job.result
    if result is None:
        return "pending"
    if result.valid:
        return "valid_exploration"
    if result.execution_status == "invalid_exploration":
        return "invalid_exploration"
    if result.execution_status == "timeout":
        return "timed_out"
    return "no_valid_exploration"


def _run_request(request: CodexExecExplorationRequest, runner: Runner) -> CodexExecExplorationResult:
    return run_codex_exec_exploration(request, execute=True, runner=runner)


def _exception_result(request: CodexExecExplorationRequest, exc: Exception) -> CodexExecExplorationResult:
    return CodexExecExplorationResult(
        executed=True,
        execution_status="job_failed",
        command=build_codex_exec_exploration_command(request),
        schema_path=str(request.schema_path),
        prompt=request.prompt,
        valid=False,
        errors=[str(exc)],
        failure_kind="job_exception",
    )
