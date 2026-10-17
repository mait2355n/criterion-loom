"""Reviewer backends: how an isolated LLM reviewer process is invoked and read.

The reviewer contract is agent-neutral: the prompt goes to standard input, the
process must answer with one JSON object, and that object is validated against
the same schema that was sent. Only the command line and the output envelope
differ between agent CLIs.

``codex`` and ``claude`` are fixed presets whose argument vectors are owned by
this module. ``command`` runs an operator-supplied argument template and is
therefore never reachable from MCP, where the caller is not the operator.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

BACKEND_CODEX = "codex"
BACKEND_CLAUDE = "claude"
BACKEND_COMMAND = "command"

PRESET_BACKENDS: tuple[str, ...] = (BACKEND_CODEX, BACKEND_CLAUDE)
BACKENDS: tuple[str, ...] = (*PRESET_BACKENDS, BACKEND_COMMAND)

DEFAULT_CODEX_MODEL = "gpt-5.4-mini"
DEFAULT_CLAUDE_MODEL = "sonnet"

_DEFAULT_MODELS = {
    BACKEND_CODEX: DEFAULT_CODEX_MODEL,
    BACKEND_CLAUDE: DEFAULT_CLAUDE_MODEL,
    BACKEND_COMMAND: "",
}
_DEFAULT_BINARIES = {
    BACKEND_CODEX: "codex",
    BACKEND_CLAUDE: "claude",
    BACKEND_COMMAND: "",
}

COMMAND_PLACEHOLDERS = ("{model}", "{schema_path}", "{schema_json}", "{working_directory}")

_FENCE = re.compile(r"\A\s*```[A-Za-z0-9_-]*[ \t]*\r?\n(?P<body>.*?)\r?\n```\s*\Z", re.DOTALL)


def validate_backend(backend: str, agent_command: Sequence[str] = ()) -> None:
    """Raise ``ValueError`` when the backend selection cannot be executed."""
    if backend not in BACKENDS:
        raise ValueError(f"unknown backend {backend!r}; expected one of {', '.join(BACKENDS)}")
    if backend == BACKEND_COMMAND and not agent_command:
        raise ValueError("backend 'command' requires a non-empty agent command template")
    if backend != BACKEND_COMMAND and agent_command:
        raise ValueError(f"an agent command template is only valid with backend 'command', not {backend!r}")


def validate_mcp_backend(backend: str) -> None:
    """Raise ``ValueError`` unless an MCP caller may select this backend.

    MCP callers choose among fixed presets only. An operator-supplied command
    template would let a remote caller start an arbitrary process.
    """
    if backend not in PRESET_BACKENDS:
        raise ValueError(
            f"backend {backend!r} is not available over MCP; expected one of {', '.join(PRESET_BACKENDS)}"
        )


def default_binary(backend: str) -> str:
    return _DEFAULT_BINARIES.get(backend, "")


def resolve_model(backend: str, model: str) -> str:
    """Map an unset model, or another backend's default, to this backend's default.

    ``DEFAULT_CODEX_MODEL`` is the historical signature default everywhere a
    model is accepted, so it also means "unset" for every backend but codex.
    """
    if not model or (backend != BACKEND_CODEX and model == DEFAULT_CODEX_MODEL):
        return _DEFAULT_MODELS.get(backend, "")
    return model


def build_agent_command(
    *,
    backend: str,
    binary: str,
    schema_path: str | Path,
    model: str,
    working_directory: str | Path | None,
    agent_command: Sequence[str] = (),
) -> list[str]:
    """Return the argument vector for one reviewer process (prompt via stdin)."""
    validate_backend(backend, agent_command)
    model = resolve_model(backend, model)
    if backend == BACKEND_CODEX:
        return _codex_command(binary or "codex", schema_path, model, working_directory)
    if backend == BACKEND_CLAUDE:
        return _claude_command(binary or "claude", schema_path, model)
    return _template_command(agent_command, schema_path, model, working_directory)


def request_binary(request: Any) -> str:
    """Executable for a request: ``agent_binary``, else the backend default.

    ``codex_binary`` is the historical field name and only applies to codex.
    """
    explicit = getattr(request, "agent_binary", "")
    if explicit:
        return explicit
    if request.backend == BACKEND_CODEX:
        return getattr(request, "codex_binary", "") or default_binary(BACKEND_CODEX)
    return default_binary(request.backend)


def build_request_command(request: Any) -> list[str]:
    """Argument vector for a review or exploration request."""
    return build_agent_command(
        backend=request.backend,
        binary=request_binary(request),
        schema_path=request.schema_path,
        model=request.model,
        working_directory=request.working_directory,
        agent_command=request.agent_command,
    )


def extract_agent_output(backend: str, stdout: str) -> tuple[str, list[str], str | None]:
    """Return ``(json_text, errors, failure_kind)`` for the reviewer payload.

    ``json_text`` is what the caller parses as the reviewer's JSON object. For
    ``codex`` it is standard output unchanged. ``claude`` wraps the answer in a
    result envelope; ``command`` tolerates a Markdown fence and the same
    envelope, because generic agent CLIs cannot be assumed to enforce a schema.
    """
    if backend == BACKEND_CODEX:
        return stdout, [], None
    if backend == BACKEND_CLAUDE:
        return _unwrap_claude_envelope(stdout)
    text = _strip_fence(stdout)
    envelope = _load_envelope(text)
    if envelope is not None and ("structured_output" in envelope or "is_error" in envelope):
        return _unwrap_claude_envelope(text)
    return text, [], None


def process_label(backend: str) -> str:
    return "codex exec" if backend == BACKEND_CODEX else f"{backend} agent"


def _codex_command(binary: str, schema_path: str | Path, model: str, working_directory: str | Path | None) -> list[str]:
    command = [
        binary,
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


def _claude_command(binary: str, schema_path: str | Path, model: str) -> list[str]:
    # Isolation mirrors the codex preset: no tools (so no file or shell access),
    # no persisted session, no user/project settings, no MCP servers, no skills.
    # The working directory is the process cwd; ``claude`` has no ``--cd``.
    return [
        binary,
        "-p",
        "--output-format",
        "json",
        "--json-schema",
        _schema_json(schema_path),
        "--model",
        model,
        "--tools",
        "",
        "--no-session-persistence",
        "--setting-sources",
        "",
        "--strict-mcp-config",
        "--disable-slash-commands",
    ]


def _template_command(
    template: Sequence[str],
    schema_path: str | Path,
    model: str,
    working_directory: str | Path | None,
) -> list[str]:
    needs_schema_json = any("{schema_json}" in part for part in template)
    values = {
        "{model}": model,
        "{schema_path}": str(schema_path),
        "{schema_json}": _schema_json(schema_path) if needs_schema_json else "",
        "{working_directory}": str(Path(working_directory)) if working_directory is not None else "",
    }
    command: list[str] = []
    for part in template:
        for placeholder, value in values.items():
            part = part.replace(placeholder, value)
        command.append(part)
    return command


def _schema_json(schema_path: str | Path) -> str:
    """Compact schema for inline use on a command line.

    ``$schema`` and ``$id`` are dropped: agent CLIs that take the schema inline
    do not resolve the meta-schema reference (Claude Code rejects it), and they
    add nothing to validation.
    """
    schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
    if isinstance(schema, dict):
        schema = {key: value for key, value in schema.items() if key not in ("$schema", "$id")}
    return json.dumps(schema, ensure_ascii=False, separators=(",", ":"))


def _strip_fence(stdout: str) -> str:
    match = _FENCE.match(stdout)
    return match.group("body") if match else stdout


def _load_envelope(text: str) -> Mapping[str, Any] | None:
    try:
        loaded = json.loads(text)
    except json.JSONDecodeError:
        return None
    return loaded if isinstance(loaded, dict) else None


def _unwrap_claude_envelope(stdout: str) -> tuple[str, list[str], str | None]:
    stripped = stdout.strip()
    if not stripped:
        return stdout, [], None
    envelope = _load_envelope(stripped)
    if envelope is None:
        return stdout, [], None
    if envelope.get("is_error") is True:
        detail = envelope.get("result")
        message = detail if isinstance(detail, str) and detail.strip() else "agent reported an error"
        return stdout, [f"agent reported an error: {message}"], "agent_error"
    structured = envelope.get("structured_output")
    if isinstance(structured, dict):
        return json.dumps(structured, ensure_ascii=False), [], None
    result = envelope.get("result")
    if isinstance(result, str) and result.strip():
        return _strip_fence(result), [], None
    return stdout, ["agent envelope has neither structured_output nor a result string"], "invalid_json"
