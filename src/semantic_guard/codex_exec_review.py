from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from semantic_guard.llm_review import (
    CandidateGapReviewInput,
    build_candidate_gap_review_prompt,
    candidate_gap_review_schema_path,
    validate_candidate_gap_review,
)

DEFAULT_CODEX_MODEL = "gpt-5.4-mini"
DEFAULT_TIMEOUT_SECONDS = 180

Runner = Callable[..., subprocess.CompletedProcess[str]]


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
    ) -> "CodexExecReviewRequest":
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
    command = [
        request.codex_binary,
        "exec",
        "--ephemeral",
        "--ignore-user-config",
        "--ignore-rules",
        "--skip-git-repo-check",
        "--sandbox",
        "read-only",
        "-c",
        'approval_policy="never"',
        "--output-schema",
        str(request.schema_path),
        "-m",
        request.model,
    ]
    if request.working_directory is not None:
        command.extend(["--cd", str(Path(request.working_directory))])
    command.append("-")
    return command


def run_codex_exec_review(
    request: CodexExecReviewRequest,
    *,
    execute: bool = False,
    runner: Runner = subprocess.run,
) -> CodexExecReviewResult:
    command = build_codex_exec_command(request)
    prompt = request.prompt
    base = {
        "command": command,
        "schema_path": str(request.schema_path),
        "prompt": prompt,
    }
    if not execute:
        return CodexExecReviewResult(
            executed=False,
            execution_status="dry_run",
            **base,
        )

    try:
        completed = runner(
            command,
            input=prompt,
            text=True,
            capture_output=True,
            timeout=request.timeout_seconds,
            cwd=str(Path(request.working_directory)) if request.working_directory is not None else None,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return CodexExecReviewResult(
            executed=True,
            execution_status="timeout",
            returncode=None,
            stdout=_string_or_empty(exc.stdout or exc.output),
            stderr=_string_or_empty(exc.stderr),
            timed_out=True,
            errors=[f"codex exec timed out after {request.timeout_seconds} seconds"],
            failure_kind="timeout",
            **base,
        )
    except OSError as exc:
        return CodexExecReviewResult(
            executed=True,
            execution_status="execution_error",
            returncode=None,
            stderr=str(exc),
            errors=[str(exc)],
            failure_kind="execution_error",
            **base,
        )

    stdout = completed.stdout or ""
    stderr = completed.stderr or ""
    if completed.returncode != 0:
        return CodexExecReviewResult(
            executed=True,
            execution_status="command_failed",
            returncode=completed.returncode,
            stdout=stdout,
            stderr=stderr,
            errors=[f"codex exec exited with status {completed.returncode}"],
            failure_kind="non_zero_exit",
            **base,
        )

    review, parse_errors = _parse_review_output(stdout)
    if parse_errors:
        return CodexExecReviewResult(
            executed=True,
            execution_status="invalid_review",
            returncode=completed.returncode,
            stdout=stdout,
            stderr=stderr,
            errors=parse_errors,
            failure_kind="invalid_json",
            **base,
        )

    validation_errors = validate_candidate_gap_review(review)
    if validation_errors:
        return CodexExecReviewResult(
            executed=True,
            execution_status="invalid_review",
            returncode=completed.returncode,
            stdout=stdout,
            stderr=stderr,
            errors=validation_errors,
            failure_kind="schema_mismatch",
            **base,
        )

    return CodexExecReviewResult(
        executed=True,
        execution_status="valid_review",
        returncode=completed.returncode,
        stdout=stdout,
        stderr=stderr,
        valid=True,
        review=dict(review),
        **base,
    )


def _parse_review_output(stdout: str) -> tuple[dict[str, Any], list[str]]:
    stripped = stdout.strip()
    if not stripped:
        return {}, ["missing reviewer output"]
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError as exc:
        return {}, [f"invalid JSON output: {exc}"]
    if not isinstance(payload, dict):
        return {}, ["reviewer output must be a JSON object"]
    return payload, []


def _string_or_empty(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def command_display(command: Sequence[str]) -> str:
    return " ".join(_quote_arg(arg) for arg in command)


def _quote_arg(arg: str) -> str:
    if not arg or any(char.isspace() or char in "\"'\\$`" for char in arg):
        return "'" + arg.replace("'", "'\"'\"'") + "'"
    return arg
