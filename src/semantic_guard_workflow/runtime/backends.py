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
import math
import os
import re
from collections.abc import Iterable, Mapping, Sequence
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

MAX_TIMEOUT_SECONDS = 3600
WORKDIR_ROOTS_ENV = "SEMANTIC_GUARD_WORKDIR_ROOTS"

_PLACEHOLDER = re.compile(r"\{(model|schema_path|schema_json|working_directory)\}")
_FENCE = re.compile(r"\A\s*```[A-Za-z0-9_-]*[ \t]*\r?\n(?P<body>.*?)\r?\n```\s*\Z", re.DOTALL)


def validate_backend(backend: str, agent_command: Sequence[str] = (), agent_binary: str = "") -> None:
    """Raise ``ValueError`` when the backend selection cannot be executed."""
    if backend not in BACKENDS:
        raise ValueError(f"unknown backend {backend!r}; expected one of {', '.join(BACKENDS)}")
    if backend == BACKEND_COMMAND and not agent_command:
        raise ValueError("backend 'command' requires a non-empty agent command template")
    if backend != BACKEND_COMMAND and agent_command:
        raise ValueError(f"an agent command template is only valid with backend 'command', not {backend!r}")
    if backend == BACKEND_COMMAND and agent_binary:
        raise ValueError("agent_binary has no effect with backend 'command'; the executable is the first template argument")


def validate_timeout_seconds(value: object, *, name: str = "timeout_seconds") -> None:
    """Raise ``ValueError`` unless ``value`` is a positive finite number of seconds, at most ``MAX_TIMEOUT_SECONDS``."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number of seconds")
    if math.isnan(value):
        raise ValueError(f"{name} must be a finite number of seconds")
    if value <= 0:
        raise ValueError(f"{name} must be positive")
    if value > MAX_TIMEOUT_SECONDS:
        raise ValueError(f"{name} must be at most {MAX_TIMEOUT_SECONDS}")


def validate_argument_value(name: str, value: object) -> None:
    """Raise ``ValueError`` unless ``value`` can be passed as one process argument."""
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    if "\x00" in value:
        raise ValueError(f"{name} must not contain a NUL character")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        raise ValueError(f"{name} must be valid Unicode text") from None


def validate_model(value: object, *, name: str = "model") -> None:
    """Raise ``ValueError`` unless ``value`` is a plain model name that cannot be read as an option."""
    validate_argument_value(name, value)
    assert isinstance(value, str)
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ValueError(f"{name} must not contain control characters")
    if value.startswith("-"):
        raise ValueError(f"{name} must not start with '-'")


def validate_reviewer_options(model: object, timeout_seconds: object, working_directory: object) -> None:
    """Raise ``ValueError`` unless a call that has not been built into a request yet could still run.

    Callers that decide *whether* to start a reviewer (escalation) use this first, so
    a call that could never run is reported as such instead of as "not needed".
    """
    validate_timeout_seconds(timeout_seconds)
    validate_model(model)
    normalize_working_directory(working_directory)  # type: ignore[arg-type]


def normalize_working_directory(value: str | os.PathLike[str] | None) -> str | None:
    """Return ``value`` as an absolute path string without touching the filesystem.

    ``None`` and the empty string mean "no working directory". A relative path is
    made absolute here so that codex ``--cd`` and the process ``cwd`` cannot each
    apply it again.
    """
    if value is None:
        return None
    try:
        text = os.fspath(value)
    except TypeError:
        raise ValueError("working_directory must be a path string") from None
    if not text:
        return None
    validate_argument_value("working_directory", text)
    return str(Path(text)) if os.path.isabs(text) else os.path.abspath(text)


def resolve_working_directory(
    value: str | os.PathLike[str] | None,
    *,
    allowed_roots: Iterable[str | os.PathLike[str]] | None = None,
    name: str = "working_directory",
    hint: str = "",
) -> str | None:
    """Return the real path of an existing directory, or ``None`` when none was given.

    ``allowed_roots`` limits the result to those directories and everything below
    them (``None`` allows any). Containment is judged on the real path, so a
    symlink inside a root cannot lead outside it, and it is checked before
    existence so a path outside the roots says nothing about what exists there.
    """
    text = normalize_working_directory(value)
    if text is None:
        return None
    real = os.path.realpath(text)
    if allowed_roots is not None and not any(
        Path(real).is_relative_to(os.path.realpath(root)) for root in allowed_roots
    ):
        raise ValueError(f"{name} is outside the allowed directories{hint}: {text}")
    if not os.path.exists(real):
        raise ValueError(f"{name} does not exist: {text}")
    if not os.path.isdir(real):
        raise ValueError(f"{name} is not a directory: {text}")
    return real


def mcp_working_directory_roots(environ: Mapping[str, str] | None = None) -> list[Path]:
    """Directories an MCP caller may name: the server's current directory and ``WORKDIR_ROOTS_ENV``."""
    environ = os.environ if environ is None else environ
    roots: list[Path] = []
    try:
        roots.append(Path.cwd().resolve())
    except OSError:
        pass
    for entry in environ.get(WORKDIR_ROOTS_ENV, "").split(os.pathsep):
        if not entry.strip():
            continue
        root = Path(entry).resolve()
        if root.is_dir() and root not in roots:
            roots.append(root)
    return roots


def resolve_mcp_working_directory(value: str | None, environ: Mapping[str, str] | None = None) -> str | None:
    """``resolve_working_directory`` limited to what an MCP caller may name."""
    if not value:
        return None
    return resolve_working_directory(
        value,
        allowed_roots=mcp_working_directory_roots(environ),
        hint=f" (the server's current directory and {WORKDIR_ROOTS_ENV})",
    )


def normalize_request(request: Any) -> None:
    """Validate the reviewer options of a frozen request dataclass and normalise them in place."""
    validate_backend(request.backend, request.agent_command, request.agent_binary)
    validate_timeout_seconds(request.timeout_seconds)
    validate_model(request.model)
    validate_argument_value("codex_binary", request.codex_binary)
    validate_argument_value("agent_binary", request.agent_binary)
    for part in request.agent_command:
        validate_argument_value("agent_command", part)
    object.__setattr__(request, "model", resolve_model(request.backend, request.model))
    object.__setattr__(request, "working_directory", normalize_working_directory(request.working_directory))


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
        # A generic agent need not report every claude status field, but one it does report must be a success.
        return _unwrap_claude_envelope(text, require_status=False)
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
    if (directory := normalize_working_directory(working_directory)) is not None:
        command.extend(["--cd", directory])
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
    """Expand the operator's argument template in one pass over its placeholders.

    A substituted value is never scanned again, so a model or path that contains
    ``{working_directory}`` stays literal. An argument whose placeholder has no
    value (no model, no working directory) is left out, together with the bare
    option right before it when the argument is only that placeholder
    (``--model {model}``); an empty string written in the template is kept.
    """
    values = {
        "model": model,
        "schema_path": str(schema_path),
        "working_directory": normalize_working_directory(working_directory) or "",
    }
    if any("{schema_json}" in part for part in template):
        values["schema_json"] = _schema_json(schema_path)
    command: list[str] = []
    after_bare_option = False
    for index, part in enumerate(template):
        unset = False

        def expand(match: re.Match[str]) -> str:
            nonlocal unset
            value = values[match.group(1)]
            unset = unset or not value
            return value

        expanded = _PLACEHOLDER.sub(expand, part)
        if unset and index > 0:
            if after_bare_option and _PLACEHOLDER.fullmatch(part):
                command.pop()
            after_bare_option = False
            continue
        command.append(expanded)
        after_bare_option = index > 0 and _is_bare_option(part)
    return command


def _is_bare_option(part: str) -> bool:
    return part.startswith("-") and len(part) > 1 and "=" not in part and not _PLACEHOLDER.search(part)


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


def _unwrap_claude_envelope(stdout: str, *, require_status: bool = True) -> tuple[str, list[str], str | None]:
    stripped = stdout.strip()
    if not stripped:
        return stdout, [], None
    envelope = _load_envelope(stripped)
    if envelope is None:
        return stdout, [], None
    failures = _envelope_failures(envelope, require_status=require_status)
    if failures:
        return stdout, failures, "agent_error"
    structured = envelope.get("structured_output")
    if isinstance(structured, dict):
        return json.dumps(structured, ensure_ascii=False), [], None
    result = envelope.get("result")
    if isinstance(result, str) and result.strip():
        return _strip_fence(result), [], None
    return stdout, ["agent envelope has neither structured_output nor a result string"], "invalid_json"


def _envelope_failures(envelope: Mapping[str, Any], *, require_status: bool) -> list[str]:
    """Reasons the envelope does not report success; empty when it does.

    Success is ``subtype == "success"``, ``is_error is False`` (the JSON boolean,
    not a truthy-looking string or integer) and no permission denials. With
    ``require_status`` unset only the status fields that are present are checked.
    """
    failures: list[str] = []
    if "is_error" in envelope or require_status:
        is_error = envelope.get("is_error")
        if is_error is True:
            detail = envelope.get("result")
            message = detail if isinstance(detail, str) and detail.strip() else "agent reported an error"
            failures.append(f"agent reported an error: {message}")
        elif is_error is not False:
            failures.append(f"agent envelope is_error must be the boolean false, got {is_error!r}")
    if "subtype" in envelope or require_status:
        subtype = envelope.get("subtype")
        if subtype != "success":
            failures.append(f"agent envelope subtype must be 'success', got {subtype!r}")
    denials = envelope.get("permission_denials")
    if denials is not None and denials != []:
        failures.append(f"agent reported permission denials: {_denial_summary(denials)}")
    return failures


def _denial_summary(denials: object) -> str:
    if not isinstance(denials, list):
        return "permission_denials must be an empty list"
    names = [str(item.get("tool_name")) for item in denials if isinstance(item, Mapping) and item.get("tool_name")]
    return ", ".join(names) if names else f"{len(denials)} denied"
