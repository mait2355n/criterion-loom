from __future__ import annotations

import subprocess
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .codex_exec import (
    DEFAULT_CODEX_MODEL,
    DEFAULT_TIMEOUT_SECONDS,
    Runner,
    build_codex_exec_runtime_command,
    command_display,  # noqa: F401 - preserved adapter-level import
    parse_json_object,
    run_codex_exec_runtime,
)
from semantic_guard_workflow.llm_review import (
    CandidateGapReviewInput,
    build_candidate_gap_review_prompt,
    candidate_gap_review_schema_path,
    validate_candidate_gap_review,
)


@dataclass(frozen=True)
class CodexExecReviewRequest:
    review_input: CandidateGapReviewInput
    model: str = DEFAULT_CODEX_MODEL
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
    working_directory: str | Path | None = None
    codex_binary: str = "codex"
    include_schema_in_prompt: bool = False

    @classmethod
    def from_mapping(
        cls,
        payload: Mapping[str, Any],
        *,
        model: str = DEFAULT_CODEX_MODEL,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        working_directory: str | Path | None = None,
        codex_binary: str = "codex",
        include_schema_in_prompt: bool = False,
    ) -> CodexExecReviewRequest:
        return cls(
            review_input=CandidateGapReviewInput.from_mapping(payload),
            model=model,
            timeout_seconds=timeout_seconds,
            working_directory=working_directory,
            codex_binary=codex_binary,
            include_schema_in_prompt=include_schema_in_prompt,
        )

    @property
    def prompt(self) -> str:
        return build_candidate_gap_review_prompt(self.review_input, include_schema=self.include_schema_in_prompt)

    @property
    def schema_path(self) -> Path:
        return candidate_gap_review_schema_path()


@dataclass
class CodexExecReviewResult:
    executed: bool
    execution_status: str
    command: list[str]
    schema_path: str
    prompt: str
    returncode: int | None = None
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False
    valid: bool = False
    errors: list[str] = field(default_factory=list)
    review: dict[str, Any] | None = None
    failure_kind: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "executed": self.executed,
            "execution_status": self.execution_status,
            "command": self.command,
            "schema_path": self.schema_path,
            "prompt": self.prompt,
            "returncode": self.returncode,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "timed_out": self.timed_out,
            "valid": self.valid,
            "errors": self.errors,
            "review": self.review,
            "failure_kind": self.failure_kind,
        }


def build_codex_exec_command(request: CodexExecReviewRequest) -> list[str]:
    return build_codex_exec_runtime_command(
        codex_binary=request.codex_binary,
        schema_path=request.schema_path,
        model=request.model,
        working_directory=request.working_directory,
    )


def run_codex_exec_review(
    request: CodexExecReviewRequest,
    *,
    execute: bool = False,
    runner: Runner = subprocess.run,
) -> CodexExecReviewResult:
    command = build_codex_exec_command(request)
    runtime_result = run_codex_exec_runtime(
        command=command,
        schema_path=request.schema_path,
        prompt=request.prompt,
        timeout_seconds=request.timeout_seconds,
        working_directory=request.working_directory,
        execute=execute,
        valid_execution_status="valid_review",
        invalid_execution_status="invalid_review",
        output_name="reviewer",
        validator=validate_candidate_gap_review,
        runner=runner,
    )
    return CodexExecReviewResult(
        review=runtime_result.payload,
        **runtime_result.domain_result_fields(),
    )


def _parse_review_output(stdout: str) -> tuple[dict[str, Any], list[str]]:
    return parse_json_object(stdout, output_name="reviewer")
