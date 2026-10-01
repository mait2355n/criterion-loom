"""Shared Codex process execution mechanics."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_CODEX_MODEL = "gpt-5.4-mini"
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
        }


def build_codex_exec_runtime_command(
    *,
    codex_binary: str,
    schema_path: str | Path,
    model: str,
    working_directory: str | Path | None,
) -> list[str]:
    command = [
        codex_binary,
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
        str(schema_path),
        "-m",
        model,
    ]
    if working_directory is not None:
        command.extend(["--cd", str(Path(working_directory))])
    command.append("-")
    return command


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
) -> CodexExecRuntimeResult:
    base = {
        "command": command,
        "schema_path": str(schema_path),
        "prompt": prompt,
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
            errors=[f"codex exec timed out after {timeout_seconds} seconds"],
            failure_kind="timeout",
            **base,
        )
    except OSError as exc:
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
            errors=[f"codex exec exited with status {completed.returncode}"],
            failure_kind="non_zero_exit",
            **base,
        )

    payload, parse_errors = parse_json_object(stdout, output_name=output_name)
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
