"""Shared reviewer process execution mechanics.

The module keeps its historical ``codex_exec`` name because existing callers
import it; the mechanics are shared by every backend in
:mod:`semantic_guard_workflow.runtime.backends`.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .backends import (
    BACKEND_CODEX,
    DEFAULT_CODEX_MODEL as DEFAULT_CODEX_MODEL,
    build_agent_command,
    extract_agent_output,
    process_label,
)

DEFAULT_TIMEOUT_SECONDS = 180

Runner = Callable[..., subprocess.CompletedProcess[str]]
Validator = Callable[[Mapping[str, Any]], list[str]]


@dataclass
class CodexExecRuntimeResult:
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
    payload: dict[str, Any] | None = None
    failure_kind: str | None = None
    backend: str = BACKEND_CODEX

    def domain_result_fields(self) -> dict[str, Any]:
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
            "failure_kind": self.failure_kind,
            "backend": self.backend,
        }


def build_codex_exec_runtime_command(
    *,
    codex_binary: str,
    schema_path: str | Path,
    model: str,
    working_directory: str | Path | None,
) -> list[str]:
    return build_agent_command(
        backend=BACKEND_CODEX,
        binary=codex_binary,
        schema_path=schema_path,
        model=model,
        working_directory=working_directory,
    )


def run_codex_exec_runtime(
    *,
    command: list[str],
    schema_path: str | Path,
    prompt: str,
    timeout_seconds: int,
    working_directory: str | Path | None,
    execute: bool,
    valid_execution_status: str,
    invalid_execution_status: str,
    output_name: str,
    validator: Validator,
    runner: Runner = subprocess.run,
    backend: str = BACKEND_CODEX,
) -> CodexExecRuntimeResult:
    label = process_label(backend)
    base = {
        "command": command,
        "schema_path": str(schema_path),
        "prompt": prompt,
        "backend": backend,
    }
    if not execute:
        return CodexExecRuntimeResult(
            executed=False,
            execution_status="dry_run",
            **base,
        )

    try:
        completed = runner(
            command,
            input=prompt,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=timeout_seconds,
            cwd=str(Path(working_directory)) if working_directory is not None else None,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return CodexExecRuntimeResult(
            executed=True,
            execution_status="timeout",
            returncode=None,
            stdout=_string_or_empty(exc.stdout or exc.output),
            stderr=_string_or_empty(exc.stderr),
            timed_out=True,
            errors=[f"{label} timed out after {timeout_seconds} seconds"],
            failure_kind="timeout",
            **base,
        )
    except (OSError, ValueError) as exc:
        # UnicodeError is a ValueError; NUL bytes in an argument raise ValueError too.
        return CodexExecRuntimeResult(
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
        return CodexExecRuntimeResult(
            executed=True,
            execution_status="command_failed",
            returncode=completed.returncode,
            stdout=stdout,
            stderr=stderr,
            errors=[f"{label} exited with status {completed.returncode}"],
            failure_kind="non_zero_exit",
            **base,
        )

    json_text, envelope_errors, envelope_failure = extract_agent_output(backend, stdout)
    if envelope_errors:
        return CodexExecRuntimeResult(
            executed=True,
            execution_status=invalid_execution_status,
            returncode=completed.returncode,
            stdout=stdout,
            stderr=stderr,
            errors=envelope_errors,
            failure_kind=envelope_failure or "invalid_json",
            **base,
        )

    payload, parse_errors = parse_json_object(json_text, output_name=output_name)
    if parse_errors:
        return CodexExecRuntimeResult(
            executed=True,
            execution_status=invalid_execution_status,
            returncode=completed.returncode,
            stdout=stdout,
            stderr=stderr,
            errors=parse_errors,
            failure_kind="invalid_json",
            **base,
        )

    validation_errors = validator(payload)
    if validation_errors:
        return CodexExecRuntimeResult(
            executed=True,
            execution_status=invalid_execution_status,
            returncode=completed.returncode,
            stdout=stdout,
            stderr=stderr,
            errors=validation_errors,
            failure_kind="schema_mismatch",
            **base,
        )

    return CodexExecRuntimeResult(
        executed=True,
        execution_status=valid_execution_status,
        returncode=completed.returncode,
        stdout=stdout,
        stderr=stderr,
        valid=True,
        payload=dict(payload),
        **base,
    )


def parse_json_object(stdout: str, *, output_name: str) -> tuple[dict[str, Any], list[str]]:
    stripped = stdout.strip()
    if not stripped:
        return {}, [f"missing {output_name} output"]
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError as exc:
        return {}, [f"invalid JSON output: {exc}"]
    if not isinstance(payload, dict):
        return {}, [f"{output_name} output must be a JSON object"]
    return payload, []


def command_display(command: Sequence[str]) -> str:
    return " ".join(_quote_arg(arg) for arg in command)


def _string_or_empty(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _quote_arg(arg: str) -> str:
    if not arg or any(char.isspace() or char in "\"'\\$`" for char in arg):
        return "'" + arg.replace("'", "'\"'\"'") + "'"
    return arg
