"""Closed subject capture and append-only local verification execution.

This module is repository-internal evidence infrastructure.  It deliberately
executes only commands present in a versioned profile, never a caller-supplied
shell string, and keeps run outputs outside the captured subject denominator.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import platform
import re
import secrets
import selectors
import shutil
import signal
import stat
import subprocess
import time
from typing import Any, Mapping, Sequence

from jsonschema import Draft202012Validator, FormatChecker

from .state_assessment import build_subject_manifest, validate_subject_manifest


PROFILE_VERSION_V0 = "semantic-guard-local-verification-profile/v0"
PROFILE_VERSION_V1 = "semantic-guard-local-verification-profile/v1"
PROFILE_VERSION = "semantic-guard-local-verification-profile/v2"
RUN_VERSION_V0 = "semantic-guard-local-verification-run/v0"
RUN_VERSION_V1 = "semantic-guard-local-verification-run/v1"
RUN_VERSION = "semantic-guard-local-verification-run/v2"
_VALIDATION_DIRECTORY = Path(__file__).resolve().parent / "validation"
_PROFILE_SCHEMA_PATH = _VALIDATION_DIRECTORY / "local-verification-profile.schema.json"
_PROFILE_SCHEMA_V1_PATH = (
    _VALIDATION_DIRECTORY / "local-verification-profile-v1.schema.json"
)
_PROFILE_SCHEMA_V2_PATH = (
    _VALIDATION_DIRECTORY / "local-verification-profile-v2.schema.json"
)
_RUN_SCHEMA_PATH = _VALIDATION_DIRECTORY / "local-verification-run.schema.json"
_RUN_SCHEMA_V1_PATH = _VALIDATION_DIRECTORY / "local-verification-run-v1.schema.json"
_RUN_SCHEMA_V2_PATH = _VALIDATION_DIRECTORY / "local-verification-run-v2.schema.json"
_ENVIRONMENT_SCHEMA_PATH = (
    _VALIDATION_DIRECTORY / "local-environment-snapshot.schema.json"
)
_ENVIRONMENT_VERSION = "semantic-guard-local-environment-snapshot/v0"
_ENVIRONMENT_LIMITATIONS = (
    "Package names and versions are captured separately from both command interpreters; package file bytes and host libraries are not fully attested.",
    "Environment-variable values are retained only as SHA-256 digests to avoid copying secrets into evidence.",
)
_DURATION_BASE_TOLERANCE_SECONDS = 0.5
_DURATION_RELATIVE_TOLERANCE = 0.02
_PLACEHOLDER = re.compile(r"\{([a-z_]+)\}")
_ALLOWED_PLACEHOLDERS = frozenset(
    {
        "artifact_dir",
        "legacy_python",
        "manifest_path",
        "repo_root",
        "run_dir",
        "uv",
        "vnext_python",
        "wheel_path",
    }
)


class LocalVerificationError(RuntimeError):
    """Fail-closed local verification error with a stable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _digest_value(value: str) -> dict[str, str]:
    return {"algorithm": "sha256", "value": value}


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def canonical_digest(value: Any) -> dict[str, str]:
    return _digest_value(hashlib.sha256(_canonical_json_bytes(value)).hexdigest())


def file_digest(path: Path) -> dict[str, str]:
    digest = hashlib.sha256()
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise LocalVerificationError("file_digest_open_failed", f"{path}: {exc}") from exc
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise LocalVerificationError("file_digest_not_regular", str(path))
        while block := os.read(descriptor, 1024 * 1024):
            digest.update(block)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    identity_before = (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
    )
    identity_after = (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    )
    if identity_before != identity_after:
        raise LocalVerificationError("file_changed_during_digest", str(path))
    return _digest_value(digest.hexdigest())


def _object_without_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    counts = Counter(key for key, _ in pairs)
    duplicates = sorted(key for key, count in counts.items() if count > 1)
    if duplicates:
        raise LocalVerificationError(
            "duplicate_json_key",
            f"duplicate JSON object keys: {duplicates!r}",
        )
    return dict(pairs)


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_object_without_duplicate_keys,
        )
    except LocalVerificationError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise LocalVerificationError("json_load_failed", f"{path}: {exc}") from exc
    if not isinstance(value, dict):
        raise LocalVerificationError("json_root_not_object", str(path))
    return value


def _schema_validator(path: Path) -> Draft202012Validator:
    schema = load_json(path)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _validate_with_schema(
    value: Mapping[str, Any],
    *,
    schema_path: Path,
    contract: str,
) -> None:
    issues = sorted(
        _schema_validator(schema_path).iter_errors(value),
        key=lambda issue: tuple(str(part) for part in issue.absolute_path),
    )
    if issues:
        issue = issues[0]
        location = "/".join(str(part) for part in issue.absolute_path) or "$"
        raise LocalVerificationError(
            f"{contract}_schema_invalid",
            f"{location}: {issue.message}",
        )


def _canonical_repository_path(value: str, *, allow_root: bool = False) -> bool:
    if value == ".":
        return allow_root
    return bool(
        value
        and not value.startswith(("/", "./"))
        and "\\" not in value
        and "\x00" not in value
        and re.match(r"^[A-Za-z]:", value) is None
        and all(part not in {"", ".", ".."} for part in value.split("/"))
    )


def validate_profile(profile: Mapping[str, Any]) -> None:
    version = profile.get("schema_version")
    if version == PROFILE_VERSION:
        schema_path = _PROFILE_SCHEMA_V2_PATH
    elif version == PROFILE_VERSION_V1:
        schema_path = _PROFILE_SCHEMA_V1_PATH
    elif version == PROFILE_VERSION_V0:
        schema_path = _PROFILE_SCHEMA_PATH
    else:
        raise LocalVerificationError("profile_version_mismatch", repr(version))
    _validate_with_schema(
        profile,
        schema_path=schema_path,
        contract="local_verification_profile",
    )
    commands = list(profile["commands"])
    command_ids = [str(item["command_id"]) for item in commands]
    if len(command_ids) != len(set(command_ids)):
        raise LocalVerificationError("duplicate_command_id", repr(command_ids))
    safe_command_ids = [re.sub(r"[^A-Za-z0-9._-]", "_", item) for item in command_ids]
    if len(safe_command_ids) != len(set(safe_command_ids)):
        raise LocalVerificationError("colliding_command_log_id", repr(command_ids))
    excluded = [str(item["path"]) for item in profile["capture"]["excluded_roots"]]
    if len(excluded) != len(set(excluded)):
        raise LocalVerificationError("duplicate_excluded_root", repr(excluded))
    for raw_path in excluded:
        if not _canonical_repository_path(raw_path):
            raise LocalVerificationError("invalid_excluded_root", raw_path)
    for command in commands:
        if not _canonical_repository_path(str(command["cwd"]), allow_root=True):
            raise LocalVerificationError("invalid_command_cwd", str(command["cwd"]))
        for argument in command["argv"]:
            unknown = set(_PLACEHOLDER.findall(str(argument))) - _ALLOWED_PLACEHOLDERS
            if unknown:
                raise LocalVerificationError(
                    "unknown_command_placeholder",
                    f"{command['command_id']}: {sorted(unknown)!r}",
                )
    if version in {PROFILE_VERSION_V1, PROFILE_VERSION}:
        claim_ids = [str(item["claim_id"]) for item in profile["claims"]]
        if len(claim_ids) != len(set(claim_ids)):
            raise LocalVerificationError("duplicate_claim_id", repr(claim_ids))
        command_id_set = set(command_ids)
        for claim in profile["claims"]:
            required_ids = [str(item) for item in claim["required_command_ids"]]
            if len(required_ids) != len(set(required_ids)):
                raise LocalVerificationError(
                    "duplicate_claim_command_id",
                    f"{claim['claim_id']}: {required_ids!r}",
                )
            unknown = sorted(set(required_ids) - command_id_set)
            if unknown:
                raise LocalVerificationError(
                    "claim_unknown_command_id",
                    f"{claim['claim_id']}: {unknown!r}",
                )


def load_profile(path: Path) -> dict[str, Any]:
    profile = load_json(path.resolve())
    validate_profile(profile)
    return profile


def _inside(root: Path, candidate: Path, *, code: str) -> Path:
    try:
        resolved = candidate.resolve()
    except OSError as exc:
        raise LocalVerificationError(code, f"cannot resolve path {candidate}: {exc}") from exc
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise LocalVerificationError(code, f"path escapes repository: {candidate}") from exc
    return resolved


def _has_symlink(root: Path, candidate: Path) -> bool:
    try:
        relative = candidate.absolute().relative_to(root.absolute())
    except ValueError:
        return True
    current = root.absolute()
    for part in relative.parts:
        current = current / part
        try:
            if current.is_symlink():
                return True
        except OSError as exc:
            raise LocalVerificationError(
                "symlink_inspection_failed",
                f"{current}: {exc}",
            ) from exc
    return False


def _path_is_under(relative: str, excluded_root: str) -> bool:
    return relative == excluded_root or relative.startswith(f"{excluded_root}/")


def _role_for_path(relative: str) -> str:
    parts = Path(relative).parts
    name = parts[-1]
    if name == "uv.lock" or name.endswith(("requirements.txt", "requirements.lock")):
        return "dependency"
    if name.endswith((".toml", ".yaml", ".yml")) or name in {".gitignore"}:
        return "configuration"
    if "validation" in parts and name.endswith((".json", ".md")):
        return "evidence"
    if parts[0] in {"docs", "tests"} or "tests" in parts or "fixtures" in parts:
        return "component"
    if name.endswith((".py", ".json")) or "schemas" in parts or "constitution" in parts:
        return "primary_subject"
    return "component"


def _enumerate_subject(
    root: Path,
    profile: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    capture = profile["capture"]
    excluded_roots = {
        str(item["path"]): str(item["reason"])
        for item in capture["excluded_roots"]
    }
    excluded_directory_names = set(capture["excluded_directory_names"])
    excluded_file_names = set(capture["excluded_file_names"])
    # Only versioned exclusion rules contribute to subject identity.  Recording
    # whichever generated caches happen to exist would make an excluded cache's
    # appearance or disappearance mutate the supposedly closed denominator.
    exclusions: dict[str, str] = dict(excluded_roots)
    files: list[Path] = []
    directory_identities: dict[Path, tuple[int, int, int]] = {}
    def fail_walk(error: OSError) -> None:
        raise LocalVerificationError("subject_walk_failed", str(error))

    for directory, raw_directory_names, raw_file_names in os.walk(
        root,
        topdown=True,
        onerror=fail_walk,
        followlinks=False,
    ):
        current = Path(directory)
        try:
            current_stat = current.stat(follow_symlinks=False)
        except OSError as exc:
            raise LocalVerificationError("subject_directory_stat_failed", str(exc)) from exc
        if not stat.S_ISDIR(current_stat.st_mode):
            raise LocalVerificationError("subject_directory_not_directory", str(current))
        directory_identities[current] = (
            current_stat.st_dev,
            current_stat.st_ino,
            current_stat.st_mtime_ns,
        )
        kept_directories: list[str] = []
        for name in sorted(raw_directory_names):
            candidate = current / name
            relative = candidate.relative_to(root).as_posix()
            configured_reason = next(
                (
                    reason
                    for excluded_root, reason in excluded_roots.items()
                    if _path_is_under(relative, excluded_root)
                ),
                None,
            )
            if configured_reason is not None:
                continue
            if name in excluded_directory_names:
                continue
            if candidate.is_symlink():
                raise LocalVerificationError("subject_symlink_rejected", relative)
            kept_directories.append(name)
        raw_directory_names[:] = kept_directories
        for name in sorted(raw_file_names):
            candidate = current / name
            relative = candidate.relative_to(root).as_posix()
            if any(_path_is_under(relative, excluded) for excluded in excluded_roots):
                continue
            if name in excluded_file_names:
                continue
            if candidate.is_symlink():
                raise LocalVerificationError("subject_symlink_rejected", relative)
            if not candidate.is_file():
                raise LocalVerificationError("subject_not_regular_file", relative)
            size = candidate.stat().st_size
            if size > int(capture["max_file_bytes"]):
                raise LocalVerificationError(
                    "subject_file_too_large",
                    f"{relative}: {size}",
                )
            files.append(candidate)
            if len(files) > int(capture["max_files"]):
                raise LocalVerificationError("subject_file_limit_exceeded", str(len(files)))
    for directory, expected_identity in directory_identities.items():
        try:
            observed = directory.stat(follow_symlinks=False)
        except OSError as exc:
            raise LocalVerificationError("subject_directory_changed", str(exc)) from exc
        identity = (observed.st_dev, observed.st_ino, observed.st_mtime_ns)
        if identity != expected_identity:
            raise LocalVerificationError("subject_directory_changed", str(directory))
    entries = []
    for path in sorted(files, key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix()
        path_identity = hashlib.sha256(relative.encode("utf-8")).hexdigest()[:24]
        entries.append(
            {
                "entry_id": f"subject.file.{path_identity}",
                "path": relative,
                "role": _role_for_path(relative),
                "content_digest": file_digest(path),
            }
        )
    if not any(entry["role"] == "primary_subject" for entry in entries):
        raise LocalVerificationError("primary_subject_missing", "capture has no primary subject")
    rendered_exclusions = [
        {"path": path, "reason": reason}
        for path, reason in sorted(exclusions.items())
    ]
    return entries, rendered_exclusions


def _distribution_snapshot() -> list[dict[str, str]]:
    observed: dict[str, str] = {}
    for distribution in metadata.distributions():
        name = str(distribution.metadata.get("Name") or "").strip().lower().replace("_", "-")
        if name:
            observed[name] = str(distribution.version)
    return [
        {"name": name, "version": observed[name]}
        for name in sorted(observed)
    ]


def _interpreter_distribution_snapshot(
    executable: Path,
    *,
    environment: Mapping[str, str],
) -> list[dict[str, str]]:
    program = (
        "import importlib.metadata as m,json;"
        "d={};"
        "exec(\"for x in m.distributions():\\n n=(x.metadata.get('Name') or '').strip().lower().replace('_','-')\\n if n:d[n]=str(x.version)\");"
        "print(json.dumps([{'name':n,'version':d[n]} for n in sorted(d)],separators=(',',':')))"
    )
    try:
        completed = subprocess.run(
            [str(executable), "-I", "-c", program],
            cwd=executable.parent,
            env=dict(environment),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise LocalVerificationError(
            "interpreter_distribution_capture_failed",
            f"{executable}: {exc}",
        ) from exc
    if completed.returncode != 0 or len(completed.stdout) > 16 * 1024 * 1024:
        raise LocalVerificationError(
            "interpreter_distribution_capture_failed",
            f"{executable}: exit={completed.returncode}",
        )
    try:
        value = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise LocalVerificationError(
            "interpreter_distribution_capture_invalid",
            str(executable),
        ) from exc
    if not isinstance(value, list) or any(
        not isinstance(item, dict)
        or set(item) != {"name", "version"}
        or not isinstance(item["name"], str)
        or not isinstance(item["version"], str)
        for item in value
    ):
        raise LocalVerificationError(
            "interpreter_distribution_capture_invalid",
            str(executable),
        )
    return value


def _resolve_tool(name: str, *, environment: Mapping[str, str]) -> Path:
    raw = shutil.which(name, path=environment.get("PATH"))
    if raw is None:
        raise LocalVerificationError("required_tool_missing", name)
    path = Path(raw)
    if not path.is_file():
        raise LocalVerificationError("required_tool_not_file", str(path))
    return path.resolve()


def _execution_environment(profile: Mapping[str, Any]) -> dict[str, str]:
    specification = profile["environment"]
    environment = {
        name: os.environ[name]
        for name in specification["inherit_names"]
        if name in os.environ
    }
    environment.update(
        {str(key): str(value) for key, value in specification["fixed_values"].items()}
    )
    return environment


def _validate_distribution_order(
    distributions: Sequence[Mapping[str, Any]],
    *,
    code: str,
) -> None:
    names = [str(item["name"]) for item in distributions]
    if names != sorted(names) or len(names) != len(set(names)):
        raise LocalVerificationError(code, repr(names))


def _validate_environment_snapshot_structure(snapshot: Mapping[str, Any]) -> None:
    _validate_with_schema(
        snapshot,
        schema_path=_ENVIRONMENT_SCHEMA_PATH,
        contract="local_environment_snapshot",
    )
    executable_ids = [str(item["executable_id"]) for item in snapshot["executables"]]
    if executable_ids != ["python.legacy", "python.vnext", "tool.uv"]:
        raise LocalVerificationError(
            "environment_executable_order_invalid",
            repr(executable_ids),
        )
    _validate_distribution_order(
        snapshot["installed_distributions"],
        code="environment_installed_distributions_order_invalid",
    )
    interpreter_ids = [
        str(item["executable_id"])
        for item in snapshot["interpreter_distributions"]
    ]
    if interpreter_ids != ["python.legacy", "python.vnext"]:
        raise LocalVerificationError(
            "environment_interpreter_order_invalid",
            repr(interpreter_ids),
        )
    for item in snapshot["interpreter_distributions"]:
        _validate_distribution_order(
            item["distributions"],
            code="environment_interpreter_distributions_order_invalid",
        )
    lock_paths = [str(item["path"]) for item in snapshot["lock_files"]]
    if lock_paths != sorted(lock_paths) or len(lock_paths) != len(set(lock_paths)):
        raise LocalVerificationError("environment_lock_order_invalid", repr(lock_paths))
    inherited_names = [str(item["name"]) for item in snapshot["inherited_environment"]]
    if len(inherited_names) != len(set(inherited_names)):
        raise LocalVerificationError(
            "environment_inherited_names_duplicate",
            repr(inherited_names),
        )
    if list(snapshot["limitations"]) != list(_ENVIRONMENT_LIMITATIONS):
        raise LocalVerificationError(
            "environment_limitations_mismatch",
            repr(snapshot["limitations"]),
        )


def capture_environment(root: Path, profile: Mapping[str, Any]) -> dict[str, Any]:
    environment = _execution_environment(profile)
    uv = _resolve_tool("uv", environment=environment)
    legacy_python = root / ".venv/bin/python"
    vnext_python = root / "vnext/.venv/bin/python"
    executables = []
    for executable_id, path in (
        ("python.legacy", legacy_python),
        ("python.vnext", vnext_python),
        ("tool.uv", uv),
    ):
        if not path.is_file():
            raise LocalVerificationError("required_executable_missing", str(path))
        resolved = path.resolve()
        executables.append(
            {
                "executable_id": executable_id,
                "invocation_path": str(path),
                "resolved_path": str(resolved),
                "file_digest": file_digest(resolved),
            }
        )
    inherited = []
    for name in profile["environment"]["inherit_names"]:
        value = environment.get(name)
        inherited.append(
            {
                "name": name,
                "present": value is not None,
                "value_digest": (
                    _digest_value(hashlib.sha256(value.encode("utf-8")).hexdigest())
                    if value is not None
                    else None
                ),
            }
        )
    locks = []
    for relative in ("uv.lock", "vnext/uv.lock"):
        path = root / relative
        if path.is_file():
            locks.append({"path": relative, "file_digest": file_digest(path)})
    interpreter_distributions = [
        {
            "executable_id": executable_id,
            "distributions": _interpreter_distribution_snapshot(
                path,
                environment=environment,
            ),
        }
        for executable_id, path in (
            ("python.legacy", legacy_python),
            ("python.vnext", vnext_python),
        )
    ]
    snapshot = {
        "schema_version": _ENVIRONMENT_VERSION,
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python_implementation": platform.python_implementation(),
            "python_version": platform.python_version(),
        },
        "executables": executables,
        "installed_distributions": _distribution_snapshot(),
        "interpreter_distributions": interpreter_distributions,
        "lock_files": locks,
        "inherited_environment": inherited,
        "fixed_environment": dict(sorted(profile["environment"]["fixed_values"].items())),
        "limitations": list(_ENVIRONMENT_LIMITATIONS),
    }
    _validate_environment_snapshot_structure(snapshot)
    return snapshot


def _identity_binding(entity_id: str, version: str, value: Any) -> dict[str, Any]:
    return {
        "entity_id": entity_id,
        "entity_version": version,
        "content_digest": canonical_digest(value),
    }


def capture_subject_manifest(
    root: Path,
    profile: Mapping[str, Any],
    environment_snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    root = root.resolve()
    validate_profile(profile)
    entries, exclusions = _enumerate_subject(root, profile)
    profile_binding = _identity_binding(
        str(profile["profile_id"]),
        str(profile["profile_version"]),
        profile,
    )
    environment_binding = _identity_binding(
        "environment.semantic-guard-local",
        "1",
        environment_snapshot,
    )
    denominator_identity = canonical_digest(
        {
            "entries": entries,
            "exclusions": exclusions,
            "environment_binding": environment_binding,
            "profile_binding": profile_binding,
        }
    )["value"]
    manifest = build_subject_manifest(
        manifest_id=f"manifest.repository.{denominator_identity[:24]}",
        manifest_version="1",
        root=str(profile["repository_root"]),
        inclusion_rule=str(profile["capture"]["inclusion_rule"]),
        subject_entries=entries,
        environment_bindings=[environment_binding],
        profile_bindings=[profile_binding],
        exclusions=exclusions,
    )
    validate_subject_manifest(manifest)
    return manifest


def verify_live_subject(
    root: Path,
    profile: Mapping[str, Any],
    environment_snapshot: Mapping[str, Any],
    expected_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    observed = capture_subject_manifest(root, profile, environment_snapshot)
    if observed["manifest_digest"] != expected_manifest["manifest_digest"]:
        raise LocalVerificationError(
            "subject_manifest_drift",
            (
                f"expected {expected_manifest['manifest_digest']['value']}, "
                f"observed {observed['manifest_digest']['value']}"
            ),
        )
    return observed


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )


def _write_new(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise LocalVerificationError("evidence_overwrite_rejected", str(path)) from exc


def _fsync_directory(path: Path) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    descriptor = os.open(path, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _new_run_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return f"run.local-verification.{stamp}.{secrets.token_hex(4)}"


def _substitute_arguments(
    arguments: Sequence[str],
    *,
    values: Mapping[str, str],
) -> list[str]:
    rendered: list[str] = []
    for argument in arguments:
        unknown = set(_PLACEHOLDER.findall(argument)) - set(values)
        if unknown:
            raise LocalVerificationError(
                "unresolved_command_placeholder",
                repr(sorted(unknown)),
            )
        rendered.append(_PLACEHOLDER.sub(lambda match: values[match.group(1)], argument))
    return rendered


def _command_executable(
    argv0: str,
    *,
    cwd: Path,
    environment: Mapping[str, str],
) -> Path:
    if "/" in argv0:
        candidate = Path(argv0)
        if not candidate.is_absolute():
            candidate = cwd / candidate
        if not candidate.is_file():
            raise LocalVerificationError("command_executable_missing", str(candidate))
        return candidate.resolve()
    return _resolve_tool(argv0, environment=environment)


def _output_record(
    path: Path,
    *,
    relative_to: Path,
    observed_size_bytes: int,
    truncated: bool,
) -> dict[str, Any]:
    return {
        "locator": path.relative_to(relative_to).as_posix(),
        "file_digest": file_digest(path),
        "size_bytes": path.stat().st_size,
        "observed_size_bytes": observed_size_bytes,
        "truncated": truncated,
    }


def _run_command(
    *,
    root: Path,
    run_directory: Path,
    command: Mapping[str, Any],
    values: Mapping[str, str],
    environment: Mapping[str, str],
    pre_manifest: Mapping[str, Any],
    profile: Mapping[str, Any],
    environment_snapshot: Mapping[str, Any],
    max_output_bytes: int,
    protected_bindings: Mapping[Path, Mapping[str, str]],
    run_directory_identity: tuple[int, int],
    logs_directory_identity: tuple[int, int],
) -> tuple[dict[str, Any], dict[str, Any]]:
    command_id = str(command["command_id"])
    cwd = _inside(root, root / str(command["cwd"]), code="command_cwd_outside_repository")
    if not cwd.is_dir() or _has_symlink(root, cwd):
        raise LocalVerificationError("command_cwd_invalid", str(cwd))
    argv = _substitute_arguments(command["argv"], values=values)
    executable = _command_executable(argv[0], cwd=cwd, environment=environment)
    safe_id = re.sub(r"[^A-Za-z0-9._-]", "_", command_id)
    stdout_path = run_directory / "logs" / f"{safe_id}.stdout"
    stderr_path = run_directory / "logs" / f"{safe_id}.stderr"
    if (run_directory.stat().st_dev, run_directory.stat().st_ino) != run_directory_identity:
        raise LocalVerificationError("run_directory_identity_changed", str(run_directory))
    if (stdout_path.parent.stat().st_dev, stdout_path.parent.stat().st_ino) != logs_directory_identity:
        raise LocalVerificationError("logs_directory_identity_changed", str(stdout_path.parent))
    started_at = _utc_now()
    start = time.monotonic()
    timed_out = False
    output_limit_exceeded = False
    deadline = start + float(command["timeout_seconds"])
    observed_sizes = {"stdout": 0, "stderr": 0}
    written_sizes = {"stdout": 0, "stderr": 0}
    artifact_directory = run_directory / "artifacts"
    pre_artifacts = _capture_artifact_bindings(
        artifact_directory,
        run_directory=run_directory,
    )
    with stdout_path.open("xb") as stdout_handle, stderr_path.open("xb") as stderr_handle:
        stdout_identity = os.fstat(stdout_handle.fileno())
        stderr_identity = os.fstat(stderr_handle.fileno())
        process = subprocess.Popen(
            argv,
            cwd=cwd,
            env=dict(environment),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            start_new_session=True,
        )
        assert process.stdout is not None
        assert process.stderr is not None
        streams = {
            process.stdout: ("stdout", stdout_handle),
            process.stderr: ("stderr", stderr_handle),
        }
        selector = selectors.DefaultSelector()
        for pipe in streams:
            os.set_blocking(pipe.fileno(), False)
            selector.register(pipe, selectors.EVENT_READ)
        killed = False
        while process.poll() is None or selector.get_map():
            remaining_to_deadline = deadline - time.monotonic()
            if remaining_to_deadline <= 0:
                timed_out = True
            if output_limit_exceeded or timed_out:
                if not killed:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        process.kill()
                    killed = True
                    # A descendant can escape the original process group.  Close
                    # every inherited read end so such a process cannot hold the
                    # verifier past its deadline.  The run remains invalid/timed
                    # out; this does not claim the escaped process was terminated.
                    for registered in list(selector.get_map().values()):
                        pipe = registered.fileobj
                        try:
                            selector.unregister(pipe)
                        except KeyError:  # pragma: no cover - defensive race guard.
                            pass
                        pipe.close()
                break
            wait_seconds = max(0.0, min(0.05, remaining_to_deadline))
            if selector.get_map():
                events = selector.select(wait_seconds)
            else:
                events = []
                try:
                    process.wait(timeout=wait_seconds)
                except subprocess.TimeoutExpired:
                    pass
            for key, _ in events:
                pipe = key.fileobj
                stream_name, output_handle = streams[pipe]
                try:
                    chunk = os.read(pipe.fileno(), 65536)
                except BlockingIOError:  # pragma: no cover - selector readiness race.
                    continue
                if not chunk:
                    selector.unregister(pipe)
                    pipe.close()
                    continue
                observed_sizes[stream_name] += len(chunk)
                writable = max_output_bytes - written_sizes[stream_name]
                if writable > 0:
                    retained = chunk[:writable]
                    output_handle.write(retained)
                    written_sizes[stream_name] += len(retained)
                if observed_sizes[stream_name] > max_output_bytes:
                    output_limit_exceeded = True
        try:
            process.wait(timeout=5.0 if killed else None)
        except subprocess.TimeoutExpired as exc:  # pragma: no cover - SIGKILL failure.
            raise LocalVerificationError(
                "command_process_did_not_terminate",
                command_id,
            ) from exc
        stdout_handle.flush()
        stderr_handle.flush()
        os.fsync(stdout_handle.fileno())
        os.fsync(stderr_handle.fileno())
        selector.close()
    post_artifacts = _capture_artifact_bindings(
        artifact_directory,
        run_directory=run_directory,
    )
    artifact_mutation_detected = _artifact_policy_violation(
        pre_artifacts,
        post_artifacts,
        effect=str(command["artifact_effect"]),
    )
    duration = time.monotonic() - start
    finished_at = _utc_now()
    stdout_observed = observed_sizes["stdout"]
    stderr_observed = observed_sizes["stderr"]
    evidence_mutation = False
    for path, expected_digest in protected_bindings.items():
        try:
            if file_digest(path) != expected_digest:
                evidence_mutation = True
        except LocalVerificationError:
            evidence_mutation = True
    for path, identity in (
        (stdout_path, stdout_identity),
        (stderr_path, stderr_identity),
    ):
        try:
            observed = path.stat(follow_symlinks=False)
            if path.is_symlink() or (observed.st_dev, observed.st_ino) != (
                identity.st_dev,
                identity.st_ino,
            ):
                evidence_mutation = True
        except OSError:
            evidence_mutation = True
    try:
        if (run_directory.stat().st_dev, run_directory.stat().st_ino) != run_directory_identity:
            evidence_mutation = True
        if (stdout_path.parent.stat().st_dev, stdout_path.parent.stat().st_ino) != logs_directory_identity:
            evidence_mutation = True
    except OSError:
        evidence_mutation = True
    try:
        post_manifest = capture_subject_manifest(root, profile, environment_snapshot)
        mutation_detected = (
            post_manifest["manifest_digest"] != pre_manifest["manifest_digest"]
            or evidence_mutation
        )
    except LocalVerificationError:
        post_manifest = pre_manifest
        mutation_detected = True
    if mutation_detected or artifact_mutation_detected or output_limit_exceeded:
        status = "invalid"
    elif timed_out:
        status = "timed_out"
    elif process.returncode == 0:
        status = "passed"
    else:
        status = "failed"
    record = {
        "command_id": command_id,
        "argv": argv,
        "cwd": str(cwd),
        "executable": {
            "resolved_path": str(executable),
            "file_digest": file_digest(executable),
        },
        "started_at": started_at,
        "finished_at": finished_at,
        "duration_seconds": round(duration, 9),
        "status": status,
        "exit_code": process.returncode,
        "timed_out": timed_out,
        "pre_manifest_identity_digest": pre_manifest["manifest_digest"],
        "post_manifest_identity_digest": post_manifest["manifest_digest"],
        "mutation_detected": mutation_detected,
        "artifact_mutation_detected": artifact_mutation_detected,
        "pre_artifacts": pre_artifacts,
        "post_artifacts": post_artifacts,
        "stdout": _output_record(
            stdout_path,
            relative_to=run_directory,
            observed_size_bytes=stdout_observed,
            truncated=stdout_observed > stdout_path.stat().st_size,
        ),
        "stderr": _output_record(
            stderr_path,
            relative_to=run_directory,
            observed_size_bytes=stderr_observed,
            truncated=stderr_observed > stderr_path.stat().st_size,
        ),
    }
    return record, post_manifest


def _relative_locator(path: Path, *, base: Path) -> str:
    return Path(os.path.relpath(path, start=base)).as_posix()


def _run_local_file(run_directory: Path, locator: str, *, code: str) -> Path:
    if not _canonical_repository_path(locator):
        raise LocalVerificationError(code, f"non-canonical run locator: {locator!r}")
    candidate = run_directory / locator
    if _has_symlink(run_directory, candidate):
        raise LocalVerificationError(code, f"run locator traverses symlink: {locator!r}")
    resolved = _inside(run_directory, candidate, code=code)
    if not resolved.is_file():
        raise LocalVerificationError(code, f"run file is missing: {locator!r}")
    return resolved


def _repository_file(
    repository_root: Path,
    base: Path,
    locator: str,
    *,
    code: str,
) -> Path:
    candidate = base / locator
    if _has_symlink(repository_root, candidate):
        raise LocalVerificationError(code, f"repository locator traverses symlink: {locator!r}")
    resolved = _inside(repository_root, candidate, code=code)
    if not resolved.is_file():
        raise LocalVerificationError(code, f"repository file is missing: {locator!r}")
    return resolved


def _validate_bound_file(path: Path, bound: Mapping[str, Any], *, code: str) -> None:
    if file_digest(path) != bound["file_digest"]:
        raise LocalVerificationError(code, str(path))


def _environment_executables(
    environment_snapshot: Mapping[str, Any],
) -> dict[str, Mapping[str, Any]]:
    raw = environment_snapshot.get("executables")
    if not isinstance(raw, list):
        raise LocalVerificationError("run_environment_invalid", "executables missing")
    result: dict[str, Mapping[str, Any]] = {}
    for item in raw:
        if not isinstance(item, dict) or not isinstance(item.get("executable_id"), str):
            raise LocalVerificationError("run_environment_invalid", repr(item))
        executable_id = str(item["executable_id"])
        if executable_id in result:
            raise LocalVerificationError("run_environment_duplicate_executable", executable_id)
        result[executable_id] = item
    expected = {"python.legacy", "python.vnext", "tool.uv"}
    if set(result) != expected:
        raise LocalVerificationError(
            "run_environment_executable_set_mismatch",
            f"expected {sorted(expected)!r}, observed {sorted(result)!r}",
        )
    return result


def _validate_timestamp_order(
    started: str,
    finished: str,
    *,
    code: str,
) -> tuple[datetime, datetime]:
    try:
        start_value = datetime.fromisoformat(started.replace("Z", "+00:00"))
        finish_value = datetime.fromisoformat(finished.replace("Z", "+00:00"))
    except ValueError as exc:
        raise LocalVerificationError(code, f"invalid timestamp: {exc}") from exc
    if finish_value < start_value:
        raise LocalVerificationError(code, f"finished before started: {started}, {finished}")
    return start_value, finish_value


def _validate_duration_consistency(
    duration_seconds: float,
    started: datetime,
    finished: datetime,
    *,
    code: str,
) -> float:
    wall_seconds = (finished - started).total_seconds()
    tolerance = max(
        _DURATION_BASE_TOLERANCE_SECONDS,
        _DURATION_RELATIVE_TOLERANCE
        * max(duration_seconds, wall_seconds, 1.0),
    )
    if abs(duration_seconds - wall_seconds) > tolerance:
        raise LocalVerificationError(
            code,
            (
                f"monotonic duration {duration_seconds} and wall interval "
                f"{wall_seconds} differ beyond tolerance {tolerance}"
            ),
        )
    return tolerance


def _capture_artifact_bindings(
    artifact_directory: Path,
    *,
    run_directory: Path,
) -> list[dict[str, Any]]:
    bindings: list[dict[str, Any]] = []

    def fail_walk(error: OSError) -> None:
        raise LocalVerificationError("artifact_walk_failed", str(error))

    for directory, raw_directories, raw_files in os.walk(
        artifact_directory,
        topdown=True,
        onerror=fail_walk,
        followlinks=False,
    ):
        current = Path(directory)
        for name in raw_directories:
            candidate = current / name
            if candidate.is_symlink():
                raise LocalVerificationError("artifact_symlink_rejected", str(candidate))
        for name in raw_files:
            candidate = current / name
            if candidate.is_symlink() or not candidate.is_file():
                raise LocalVerificationError("artifact_not_regular", str(candidate))
            bindings.append(
                {
                    "locator": candidate.relative_to(run_directory).as_posix(),
                    "file_digest": file_digest(candidate),
                    "size_bytes": candidate.stat().st_size,
                }
            )
    return sorted(bindings, key=lambda item: item["locator"])


def _artifact_policy_violation(
    pre_artifacts: Sequence[Mapping[str, Any]],
    post_artifacts: Sequence[Mapping[str, Any]],
    *,
    effect: str,
) -> bool:
    pre_by_locator = {str(item["locator"]): item for item in pre_artifacts}
    post_by_locator = {str(item["locator"]): item for item in post_artifacts}
    existing_changed = any(
        locator not in post_by_locator or post_by_locator[locator] != binding
        for locator, binding in pre_by_locator.items()
    )
    if existing_changed:
        return True
    if effect == "none":
        return list(pre_artifacts) != list(post_artifacts)
    if effect == "may_add":
        return False
    raise LocalVerificationError("unknown_artifact_effect", effect)


def _claim_results(
    profile: Mapping[str, Any],
    command_records: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    records = {str(item["command_id"]): item for item in command_records}
    results = []
    for claim in profile["claims"]:
        required = [str(item) for item in claim["required_command_ids"]]
        present = [records[item] for item in required if item in records]
        if len(present) != len(required):
            status = "not_observed"
        elif all(item["status"] == "passed" for item in present):
            status = "passed"
        else:
            status = "failed"
        results.append(
            {
                "claim_id": str(claim["claim_id"]),
                "required_command_ids": required,
                "status": status,
            }
        )
    return results


def _validate_legacy_run_record(
    record: Mapping[str, Any],
    *,
    run_directory: Path,
    repository_root: Path,
) -> None:
    _validate_with_schema(
        record,
        schema_path=_RUN_SCHEMA_PATH,
        contract="local_verification_run_v0",
    )
    material = dict(record)
    material.pop("run_record_digest", None)
    if record["run_record_digest"] != canonical_digest(material):
        raise LocalVerificationError("run_record_digest_mismatch", str(run_directory))
    if run_directory.name != record["run_id"]:
        raise LocalVerificationError("run_directory_id_mismatch", str(run_directory))
    profile_path = _repository_file(
        repository_root,
        run_directory,
        str(record["profile"]["locator"]),
        code="legacy_run_profile_unavailable",
    )
    _validate_bound_file(
        profile_path,
        record["profile"],
        code="legacy_run_profile_digest_mismatch",
    )
    for key in ("environment", "subject"):
        path = _run_local_file(
            run_directory,
            str(record[key]["locator"]),
            code="legacy_run_bound_file_outside_run",
        )
        _validate_bound_file(path, record[key], code="legacy_run_bound_file_mismatch")
    for command in record["commands"]:
        for stream in (command["stdout"], command["stderr"]):
            path = _run_local_file(
                run_directory,
                str(stream["locator"]),
                code="legacy_run_log_outside_run",
            )
            if path.stat().st_size != stream["size_bytes"]:
                raise LocalVerificationError("legacy_run_log_size_mismatch", str(path))
            _validate_bound_file(path, stream, code="legacy_run_log_mismatch")


def _validate_legacy_v1_run_record(
    record: Mapping[str, Any],
    *,
    run_directory: Path,
) -> None:
    """Read the superseded self-contained v1 format without granting trust."""

    _validate_with_schema(
        record,
        schema_path=_RUN_SCHEMA_V1_PATH,
        contract="local_verification_run_v1",
    )
    material = dict(record)
    material.pop("run_record_digest", None)
    if record["run_record_digest"] != canonical_digest(material):
        raise LocalVerificationError("run_record_digest_mismatch", str(run_directory))
    if run_directory.name != record["run_id"]:
        raise LocalVerificationError("run_directory_id_mismatch", str(run_directory))
    if (run_directory / "INCOMPLETE").exists():
        raise LocalVerificationError("run_incomplete", str(run_directory))
    for key in ("profile", "environment", "subject"):
        path = _run_local_file(
            run_directory,
            str(record[key]["locator"]),
            code="legacy_v1_run_bound_file_outside_run",
        )
        _validate_bound_file(path, record[key], code="legacy_v1_run_bound_file_mismatch")
    for artifact in record["artifacts"]:
        path = _run_local_file(
            run_directory,
            str(artifact["locator"]),
            code="legacy_v1_run_artifact_outside_run",
        )
        if path.stat().st_size != artifact["size_bytes"]:
            raise LocalVerificationError("legacy_v1_run_artifact_size_mismatch", str(path))
        _validate_bound_file(path, artifact, code="legacy_v1_run_artifact_mismatch")
    for command in record["commands"]:
        for stream in (command["stdout"], command["stderr"]):
            path = _run_local_file(
                run_directory,
                str(stream["locator"]),
                code="legacy_v1_run_log_outside_run",
            )
            if path.stat().st_size != stream["size_bytes"]:
                raise LocalVerificationError("legacy_v1_run_log_size_mismatch", str(path))
            _validate_bound_file(path, stream, code="legacy_v1_run_log_mismatch")
    run_path = run_directory / "run.json"
    if run_path.is_file() and load_json(run_path) != dict(record):
        raise LocalVerificationError("run_file_content_mismatch", str(run_path))


def validate_run_record(
    record: Mapping[str, Any],
    *,
    run_directory: Path,
    repository_root: Path,
    require_current_subject: bool = False,
    allow_incomplete: bool = False,
) -> None:
    repository_root = repository_root.resolve()
    run_directory = _inside(
        repository_root,
        run_directory,
        code="run_directory_outside_repository",
    )
    if _has_symlink(repository_root, run_directory) or not run_directory.is_dir():
        raise LocalVerificationError("run_directory_invalid", str(run_directory))
    version = record.get("schema_version")
    if version == RUN_VERSION_V0:
        if require_current_subject:
            raise LocalVerificationError(
                "legacy_run_cannot_be_current",
                "v0 runs are historical read-only records",
            )
        _validate_legacy_run_record(
            record,
            run_directory=run_directory,
            repository_root=repository_root,
        )
        return
    if version == RUN_VERSION_V1:
        if require_current_subject:
            raise LocalVerificationError(
                "legacy_v1_run_cannot_be_current",
                "v1 runs are historical read-only records",
            )
        _validate_legacy_v1_run_record(
            record,
            run_directory=run_directory,
        )
        return
    if version != RUN_VERSION:
        raise LocalVerificationError("run_version_mismatch", repr(version))
    _validate_with_schema(
        record,
        schema_path=_RUN_SCHEMA_V2_PATH,
        contract="local_verification_run",
    )
    material = dict(record)
    material.pop("run_record_digest", None)
    if record["run_record_digest"] != canonical_digest(material):
        raise LocalVerificationError("run_record_digest_mismatch", str(run_directory))
    if run_directory.name != record["run_id"]:
        raise LocalVerificationError("run_directory_id_mismatch", str(run_directory))
    if (run_directory / "INCOMPLETE").exists() and not allow_incomplete:
        raise LocalVerificationError("run_incomplete", str(run_directory))
    run_started, run_finished = _validate_timestamp_order(
        str(record["started_at"]),
        str(record["finished_at"]),
        code="run_timestamp_order_invalid",
    )
    _validate_duration_consistency(
        float(record["duration_seconds"]),
        run_started,
        run_finished,
        code="run_duration_mismatch",
    )

    bound_paths: dict[str, Path] = {}
    for key in ("profile", "environment", "subject"):
        bound = record[key]
        path = _run_local_file(
            run_directory,
            str(bound["locator"]),
            code="run_bound_file_outside_run",
        )
        _validate_bound_file(path, bound, code="run_bound_file_mismatch")
        bound_paths[key] = path

    profile = load_profile(bound_paths["profile"])
    if profile["schema_version"] != PROFILE_VERSION:
        raise LocalVerificationError(
            "run_profile_version_not_self_contained",
            repr(profile["schema_version"]),
        )
    if record["limitations"] != list(profile["limitations"]):
        raise LocalVerificationError(
            "run_limitations_mismatch",
            "run limitations must exactly match the sealed profile",
        )
    environment_snapshot = load_json(bound_paths["environment"])
    manifest = load_json(bound_paths["subject"])
    validate_subject_manifest(manifest)
    if record["subject"]["manifest_id"] != manifest["manifest_id"]:
        raise LocalVerificationError("run_manifest_id_mismatch", str(bound_paths["subject"]))
    if record["subject"]["manifest_version"] != manifest["manifest_version"]:
        raise LocalVerificationError("run_manifest_version_mismatch", str(bound_paths["subject"]))
    if record["subject"]["entry_count"] != len(manifest["subject_entries"]):
        raise LocalVerificationError("run_manifest_entry_count_mismatch", str(bound_paths["subject"]))
    if record["subject"]["identity_digest"] != manifest["manifest_digest"]:
        raise LocalVerificationError("run_manifest_identity_mismatch", str(bound_paths["subject"]))
    expected_profile_binding = _identity_binding(
        str(profile["profile_id"]),
        str(profile["profile_version"]),
        profile,
    )
    if manifest["profile_bindings"] != [expected_profile_binding]:
        raise LocalVerificationError("run_manifest_profile_binding_mismatch", str(bound_paths["subject"]))
    expected_environment_binding = _identity_binding(
        "environment.semantic-guard-local",
        "1",
        environment_snapshot,
    )
    if manifest["environment_bindings"] != [expected_environment_binding]:
        raise LocalVerificationError(
            "run_manifest_environment_binding_mismatch",
            str(bound_paths["subject"]),
        )
    if manifest["denominator"]["root"] != profile["repository_root"]:
        raise LocalVerificationError("run_manifest_root_mismatch", repr(manifest["denominator"]["root"]))

    _validate_environment_snapshot_structure(environment_snapshot)
    executable_bindings = _environment_executables(environment_snapshot)
    execution_environment = _execution_environment(profile)
    expected_executables = {
        "python.legacy": repository_root / ".venv/bin/python",
        "python.vnext": repository_root / "vnext/.venv/bin/python",
        "tool.uv": _resolve_tool("uv", environment=execution_environment),
    }
    for executable_id, expected_invocation in expected_executables.items():
        binding = executable_bindings[executable_id]
        try:
            expected_resolved = expected_invocation.resolve()
        except OSError as exc:
            raise LocalVerificationError(
                "run_environment_executable_resolution_failed",
                f"{expected_invocation}: {exc}",
            ) from exc
        if binding["invocation_path"] != str(expected_invocation):
            raise LocalVerificationError(
                "run_environment_executable_invocation_mismatch",
                executable_id,
            )
        if binding["resolved_path"] != str(expected_resolved):
            raise LocalVerificationError(
                "run_environment_executable_path_mismatch",
                executable_id,
            )
        if not expected_resolved.is_file() or file_digest(expected_resolved) != binding["file_digest"]:
            raise LocalVerificationError("run_environment_executable_mismatch", executable_id)
    if environment_snapshot.get("fixed_environment") != profile["environment"]["fixed_values"]:
        raise LocalVerificationError("run_environment_fixed_values_mismatch", "fixed_environment")
    inherited_names = [
        str(item["name"])
        for item in environment_snapshot["inherited_environment"]
    ]
    if inherited_names != list(profile["environment"]["inherit_names"]):
        raise LocalVerificationError(
            "run_environment_inherited_names_mismatch",
            repr(inherited_names),
        )
    manifest_entries = {
        str(item["path"]): item["content_digest"]
        for item in manifest["subject_entries"]
    }
    expected_lock_files = [
        {"path": path, "file_digest": manifest_entries[path]}
        for path in ("uv.lock", "vnext/uv.lock")
        if path in manifest_entries
    ]
    if environment_snapshot["lock_files"] != expected_lock_files:
        raise LocalVerificationError(
            "run_environment_lock_binding_mismatch",
            repr(environment_snapshot["lock_files"]),
        )

    declared_artifacts = list(record["artifacts"])
    artifact_locators = [str(item["locator"]) for item in declared_artifacts]
    if len(artifact_locators) != len(set(artifact_locators)):
        raise LocalVerificationError("run_duplicate_artifact_locator", repr(artifact_locators))
    for artifact in declared_artifacts:
        locator = str(artifact["locator"])
        if not locator.startswith("artifacts/"):
            raise LocalVerificationError("run_artifact_outside_artifact_root", locator)
        path = _run_local_file(run_directory, locator, code="run_artifact_outside_run")
        if path.stat().st_size != artifact["size_bytes"]:
            raise LocalVerificationError("run_artifact_size_mismatch", locator)
        _validate_bound_file(path, artifact, code="run_artifact_digest_mismatch")
    observed_artifacts = _capture_artifact_bindings(
        run_directory / "artifacts",
        run_directory=run_directory,
    )
    if declared_artifacts != observed_artifacts:
        raise LocalVerificationError("run_artifact_set_mismatch", str(run_directory))

    values = {
        "artifact_dir": str(run_directory / "artifacts"),
        "legacy_python": str(repository_root / ".venv/bin/python"),
        "manifest_path": str(bound_paths["subject"]),
        "repo_root": str(repository_root),
        "run_dir": str(run_directory),
        "uv": str(executable_bindings["tool.uv"]["resolved_path"]),
        "vnext_python": str(repository_root / "vnext/.venv/bin/python"),
    }
    wheels = [
        run_directory / locator
        for locator in artifact_locators
        if locator.endswith(".whl")
    ]
    if any("{wheel_path}" in argument for command in profile["commands"] for argument in command["argv"]):
        if len(wheels) != 1:
            raise LocalVerificationError("run_wheel_artifact_ambiguous", str(len(wheels)))
        values["wheel_path"] = str(wheels[0])

    command_records = list(record["commands"])
    profile_commands = list(profile["commands"])
    if len(command_records) > len(profile_commands):
        raise LocalVerificationError("run_command_count_exceeds_profile", str(len(command_records)))
    command_ids = [str(item["command_id"]) for item in command_records]
    if len(command_ids) != len(set(command_ids)):
        raise LocalVerificationError("run_duplicate_command_id", repr(command_ids))
    expected_pre_digest = manifest["manifest_digest"]
    expected_pre_artifacts: list[dict[str, Any]] = []
    log_locators: list[str] = []
    previous_finished = run_started
    for index, command_record in enumerate(command_records):
        command_profile = profile_commands[index]
        if command_record["command_id"] != command_profile["command_id"]:
            raise LocalVerificationError("run_command_order_mismatch", str(index))
        if command_record["pre_artifacts"] != expected_pre_artifacts:
            raise LocalVerificationError(
                "run_command_artifact_chain_mismatch",
                str(command_record["command_id"]),
            )
        expected_artifact_mutation = _artifact_policy_violation(
            command_record["pre_artifacts"],
            command_record["post_artifacts"],
            effect=str(command_profile["artifact_effect"]),
        )
        if command_record["artifact_mutation_detected"] != expected_artifact_mutation:
            raise LocalVerificationError(
                "run_command_artifact_mutation_mismatch",
                str(command_record["command_id"]),
            )
        expected_pre_artifacts = list(command_record["post_artifacts"])
        expected_argv = _substitute_arguments(command_profile["argv"], values=values)
        if command_record["argv"] != expected_argv:
            raise LocalVerificationError("run_command_argv_mismatch", str(command_record["command_id"]))
        expected_cwd = _inside(
            repository_root,
            repository_root / str(command_profile["cwd"]),
            code="run_command_cwd_outside_repository",
        )
        if command_record["cwd"] != str(expected_cwd):
            raise LocalVerificationError("run_command_cwd_mismatch", str(command_record["command_id"]))
        expected_executable = _command_executable(
            expected_argv[0],
            cwd=expected_cwd,
            environment=execution_environment,
        )
        if command_record["executable"]["resolved_path"] != str(expected_executable):
            raise LocalVerificationError("run_command_executable_path_mismatch", str(command_record["command_id"]))
        _validate_bound_file(
            expected_executable,
            command_record["executable"],
            code="run_command_executable_digest_mismatch",
        )
        command_started, command_finished = _validate_timestamp_order(
            str(command_record["started_at"]),
            str(command_record["finished_at"]),
            code="run_command_timestamp_order_invalid",
        )
        duration_tolerance = _validate_duration_consistency(
            float(command_record["duration_seconds"]),
            command_started,
            command_finished,
            code="run_command_duration_mismatch",
        )
        if command_started < run_started or command_finished > run_finished:
            raise LocalVerificationError(
                "run_command_outside_run_interval",
                str(command_record["command_id"]),
            )
        if command_started < previous_finished:
            raise LocalVerificationError(
                "run_command_interval_overlap",
                str(command_record["command_id"]),
            )
        previous_finished = command_finished
        timeout_seconds = float(command_profile["timeout_seconds"])
        if (
            not command_record["timed_out"]
            and float(command_record["duration_seconds"])
            > timeout_seconds + duration_tolerance
        ):
            raise LocalVerificationError(
                "run_command_duration_exceeds_timeout",
                str(command_record["command_id"]),
            )
        if command_record["pre_manifest_identity_digest"] != expected_pre_digest:
            raise LocalVerificationError("run_command_manifest_chain_mismatch", str(command_record["command_id"]))
        if (
            not command_record["mutation_detected"]
            and command_record["post_manifest_identity_digest"]
            != command_record["pre_manifest_identity_digest"]
        ):
            raise LocalVerificationError("run_command_unreported_mutation", str(command_record["command_id"]))
        expected_pre_digest = command_record["post_manifest_identity_digest"]
        output_limit_exceeded = False
        for stream_name in ("stdout", "stderr"):
            stream = command_record[stream_name]
            locator = str(stream["locator"])
            expected_safe_id = re.sub(r"[^A-Za-z0-9._-]", "_", str(command_record["command_id"]))
            expected_locator = f"logs/{expected_safe_id}.{stream_name}"
            if locator != expected_locator:
                raise LocalVerificationError("run_log_locator_mismatch", locator)
            path = _run_local_file(run_directory, locator, code="run_log_outside_run")
            if path.stat().st_size != stream["size_bytes"]:
                raise LocalVerificationError("run_log_size_mismatch", locator)
            _validate_bound_file(path, stream, code="run_log_digest_mismatch")
            limit = int(record["execution_limits"]["max_output_bytes_per_stream"])
            if stream["size_bytes"] > limit:
                raise LocalVerificationError("run_log_limit_violated", locator)
            if stream["truncated"]:
                if stream["size_bytes"] != limit or stream["observed_size_bytes"] <= limit:
                    raise LocalVerificationError("run_log_truncation_invalid", locator)
                output_limit_exceeded = True
            elif stream["observed_size_bytes"] != stream["size_bytes"]:
                raise LocalVerificationError("run_log_observed_size_mismatch", locator)
            log_locators.append(locator)
        if (
            command_record["mutation_detected"]
            or command_record["artifact_mutation_detected"]
            or output_limit_exceeded
        ):
            expected_status = "invalid"
        elif command_record["timed_out"]:
            expected_status = "timed_out"
        elif command_record["exit_code"] == 0:
            expected_status = "passed"
        else:
            expected_status = "failed"
        if command_record["status"] != expected_status:
            raise LocalVerificationError("run_command_status_mismatch", str(command_record["command_id"]))
        if index < len(command_records) - 1 and command_record["status"] != "passed":
            raise LocalVerificationError("run_fail_fast_violation", str(command_record["command_id"]))

    if declared_artifacts != expected_pre_artifacts:
        raise LocalVerificationError(
            "run_final_artifact_chain_mismatch",
            str(run_directory),
        )

    observed_logs = sorted(
        path.relative_to(run_directory).as_posix()
        for path in (run_directory / "logs").iterdir()
        if path.is_file()
    )
    if sorted(log_locators) != observed_logs:
        raise LocalVerificationError("run_log_set_mismatch", str(run_directory / "logs"))
    allowed_files = {
        "profile.json",
        "environment.json",
        "subject-manifest.json",
        *artifact_locators,
        *log_locators,
    }
    if allow_incomplete:
        allowed_files.add("INCOMPLETE")
    else:
        allowed_files.add("run.json")
    observed_run_files: set[str] = set()

    def fail_run_walk(error: OSError) -> None:
        raise LocalVerificationError("run_walk_failed", str(error))

    for directory, raw_directories, raw_files in os.walk(
        run_directory,
        topdown=True,
        onerror=fail_run_walk,
        followlinks=False,
    ):
        current = Path(directory)
        for name in raw_directories:
            if (current / name).is_symlink():
                raise LocalVerificationError("run_symlink_rejected", str(current / name))
        for name in raw_files:
            candidate = current / name
            if candidate.is_symlink() or not candidate.is_file():
                raise LocalVerificationError("run_nonregular_file_rejected", str(candidate))
            observed_run_files.add(candidate.relative_to(run_directory).as_posix())
    if observed_run_files != allowed_files:
        raise LocalVerificationError(
            "run_unbound_file_set",
            (
                f"expected {sorted(allowed_files)!r}, "
                f"observed {sorted(observed_run_files)!r}"
            ),
        )
    run_path = run_directory / "run.json"
    if run_path.is_file() and load_json(run_path) != dict(record):
        raise LocalVerificationError("run_file_content_mismatch", str(run_path))
    if record["status"] == "passed":
        if len(command_records) != len(profile_commands) or any(
            item["status"] != "passed" for item in command_records
        ):
            raise LocalVerificationError("run_passed_without_complete_profile", str(run_directory))
    else:
        if not command_records or command_records[-1]["status"] == "passed":
            raise LocalVerificationError("run_nonpassed_without_terminal_failure", str(run_directory))
        expected_overall = "invalid" if command_records[-1]["status"] == "invalid" else "failed"
        if record["status"] != expected_overall:
            raise LocalVerificationError("run_overall_status_mismatch", str(run_directory))
    expected_claims = _claim_results(profile, command_records)
    if record["claims"] != expected_claims:
        raise LocalVerificationError("run_claim_results_mismatch", str(run_directory))
    if require_current_subject:
        observed_environment = capture_environment(repository_root, profile)
        if observed_environment != environment_snapshot:
            raise LocalVerificationError(
                "run_environment_drift",
                str(bound_paths["environment"]),
            )
        verify_live_subject(repository_root, profile, environment_snapshot, manifest)


def execute_local_verification(
    *,
    root: Path,
    profile_path: Path,
    output_root: Path,
    run_id: str | None = None,
    max_output_bytes: int = 16 * 1024 * 1024,
) -> tuple[Path, dict[str, Any]]:
    root = root.resolve()
    lexical_profile_path = profile_path.absolute()
    if _has_symlink(root, lexical_profile_path):
        raise LocalVerificationError("profile_symlink_rejected", str(profile_path))
    profile_path = _inside(root, profile_path, code="profile_outside_repository")
    profile = load_profile(profile_path)
    if profile["schema_version"] != PROFILE_VERSION:
        raise LocalVerificationError(
            "profile_version_not_executable",
            "new runs require a self-contained v1 profile",
        )
    output_root = _inside(root, output_root, code="output_outside_repository")
    excluded_roots = [
        _inside(root, root / str(item["path"]), code="excluded_root_outside_repository")
        for item in profile["capture"]["excluded_roots"]
    ]
    if not any(output_root == excluded or output_root.is_relative_to(excluded) for excluded in excluded_roots):
        raise LocalVerificationError(
            "output_not_excluded_from_subject",
            str(output_root),
        )
    selected_run_id = run_id or _new_run_id()
    if re.fullmatch(r"(?!.*\.\.)[A-Za-z0-9][A-Za-z0-9._-]{0,127}", selected_run_id) is None:
        raise LocalVerificationError("invalid_run_id", selected_run_id)
    output_root.mkdir(parents=True, exist_ok=True)
    if _has_symlink(root, output_root) or not output_root.is_dir():
        raise LocalVerificationError("output_root_invalid", str(output_root))
    run_directory = _inside(
        output_root,
        output_root / selected_run_id,
        code="run_directory_outside_output_root",
    )
    try:
        run_directory.mkdir(exist_ok=False)
    except FileExistsError as exc:
        raise LocalVerificationError("run_id_collision", selected_run_id) from exc
    run_stat = run_directory.stat()
    run_directory_identity = (run_stat.st_dev, run_stat.st_ino)
    marker = run_directory / "INCOMPLETE"
    _write_new(marker, b"A completed run.json does not yet exist.\n")
    profile_snapshot_path = run_directory / "profile.json"
    source_profile_digest = file_digest(profile_path)
    try:
        profile_bytes = profile_path.read_bytes()
    except OSError as exc:
        raise LocalVerificationError("profile_snapshot_read_failed", str(exc)) from exc
    if file_digest(profile_path) != source_profile_digest:
        raise LocalVerificationError("profile_changed_during_snapshot", str(profile_path))
    _write_new(profile_snapshot_path, profile_bytes)
    snapshot_profile = load_profile(profile_snapshot_path)
    if snapshot_profile != profile:
        raise LocalVerificationError("profile_snapshot_mismatch", str(profile_path))
    profile = snapshot_profile
    started_at = _utc_now()
    run_start = time.monotonic()
    environment_snapshot = capture_environment(root, profile)
    environment_path = run_directory / "environment.json"
    _write_new(environment_path, _json_bytes(environment_snapshot))
    manifest = capture_subject_manifest(root, profile, environment_snapshot)
    manifest_path = run_directory / "subject-manifest.json"
    _write_new(manifest_path, _json_bytes(manifest))
    verify_live_subject(root, profile, environment_snapshot, manifest)
    protected_bindings = {
        profile_snapshot_path: file_digest(profile_snapshot_path),
        environment_path: file_digest(environment_path),
        manifest_path: file_digest(manifest_path),
    }
    environment = _execution_environment(profile)
    uv = _resolve_tool("uv", environment=environment)
    artifact_directory = run_directory / "artifacts"
    artifact_directory.mkdir()
    logs_directory = run_directory / "logs"
    logs_directory.mkdir()
    logs_stat = logs_directory.stat()
    logs_directory_identity = (logs_stat.st_dev, logs_stat.st_ino)
    values = {
        "artifact_dir": str(artifact_directory),
        "legacy_python": str(root / ".venv/bin/python"),
        "manifest_path": str(manifest_path),
        "repo_root": str(root),
        "run_dir": str(run_directory),
        "uv": str(uv),
        "vnext_python": str(root / "vnext/.venv/bin/python"),
    }
    commands: list[dict[str, Any]] = []
    current_manifest = manifest
    overall_status = "passed"
    for command in profile["commands"]:
        if "{wheel_path}" in command["argv"]:
            wheels = sorted(artifact_directory.glob("*.whl"))
            if len(wheels) != 1:
                raise LocalVerificationError(
                    "wheel_artifact_ambiguous",
                    f"expected one wheel, observed {len(wheels)}",
                )
            values["wheel_path"] = str(wheels[0])
        record, current_manifest = _run_command(
            root=root,
            run_directory=run_directory,
            command=command,
            values=values,
            environment=environment,
            pre_manifest=current_manifest,
            profile=profile,
            environment_snapshot=environment_snapshot,
            max_output_bytes=max_output_bytes,
            protected_bindings=protected_bindings,
            run_directory_identity=run_directory_identity,
            logs_directory_identity=logs_directory_identity,
        )
        commands.append(record)
        if record["status"] != "passed":
            overall_status = "invalid" if record["status"] == "invalid" else "failed"
            break
    finished_at = _utc_now()
    profile_file_digest = file_digest(profile_snapshot_path)
    environment_file_digest = file_digest(environment_path)
    manifest_file_digest = file_digest(manifest_path)
    artifacts = _capture_artifact_bindings(
        artifact_directory,
        run_directory=run_directory,
    )
    run_record: dict[str, Any] = {
        "schema_version": RUN_VERSION,
        "run_id": selected_run_id,
        "started_at": started_at,
        "finished_at": finished_at,
        "duration_seconds": round(time.monotonic() - run_start, 9),
        "status": overall_status,
        "execution_limits": {
            "max_output_bytes_per_stream": max_output_bytes,
            "fail_fast": True,
            "shell": False,
        },
        "profile": {
            "locator": profile_snapshot_path.relative_to(run_directory).as_posix(),
            "file_digest": profile_file_digest,
        },
        "environment": {
            "locator": environment_path.relative_to(run_directory).as_posix(),
            "file_digest": environment_file_digest,
        },
        "subject": {
            "locator": manifest_path.relative_to(run_directory).as_posix(),
            "file_digest": manifest_file_digest,
            "manifest_id": manifest["manifest_id"],
            "manifest_version": manifest["manifest_version"],
            "entry_count": len(manifest["subject_entries"]),
            "identity_digest": manifest["manifest_digest"],
        },
        "artifacts": artifacts,
        "commands": commands,
        "claims": _claim_results(profile, commands),
        "limitations": list(profile["limitations"]),
    }
    run_record["run_record_digest"] = canonical_digest(run_record)
    validate_run_record(
        run_record,
        run_directory=run_directory,
        repository_root=root,
        allow_incomplete=True,
    )
    record_path = run_directory / "run.json"
    _write_new(record_path, _json_bytes(run_record))
    _fsync_directory(run_directory)
    marker.unlink()
    _fsync_directory(run_directory)
    validate_run_record(
        run_record,
        run_directory=run_directory,
        repository_root=root,
    )
    return record_path, run_record


def verification_source_binding(
    *,
    repository_root: Path,
    run_path: Path,
) -> dict[str, Any]:
    root = repository_root.resolve()
    run_path = _inside(root, run_path, code="run_outside_repository")
    record = load_json(run_path)
    if record.get("schema_version") != RUN_VERSION:
        raise LocalVerificationError(
            "run_version_not_bindable",
            "legacy runs are readable for history but cannot become a trust binding",
        )
    validate_run_record(
        record,
        run_directory=run_path.parent,
        repository_root=root,
    )
    if record["status"] != "passed":
        raise LocalVerificationError("run_not_passed", str(run_path))
    manifest_path = (run_path.parent / record["subject"]["locator"]).resolve()
    manifest = load_json(manifest_path)
    validate_subject_manifest(manifest)
    profile_path = (run_path.parent / record["profile"]["locator"]).resolve()
    profile = load_profile(profile_path)
    source_base = root / "vnext/validation"
    bindings = []
    locators = []
    manifest_root = (root / manifest["denominator"]["root"]).resolve()
    for entry in manifest["subject_entries"]:
        path = (manifest_root / entry["path"]).resolve()
        locator = _relative_locator(path, base=source_base)
        locators.append(locator)
        bindings.append(
            {
                "subject_locator": locator,
                "digest": entry["content_digest"],
            }
        )
    command_refs = []
    for command in record["commands"]:
        command_refs.extend(
            [
                _relative_locator(run_path.parent / command["stdout"]["locator"], base=source_base),
                _relative_locator(run_path.parent / command["stderr"]["locator"], base=source_base),
            ]
        )
    return {
        "status": "bound",
        "subject_locators": locators,
        "digest_bindings": bindings,
        "manifest_ref": _relative_locator(manifest_path, base=source_base),
        "manifest_digest": file_digest(manifest_path),
        "environment_ref": _relative_locator(
            run_path.parent / record["environment"]["locator"],
            base=source_base,
        ),
        "command_or_log_refs": command_refs,
        "profile_binding": {
            "profile_id": profile["profile_id"],
            "profile_version": profile["profile_version"],
            "profile_file_digest": record["profile"]["file_digest"],
        },
        "claim_results": record["claims"],
        "limitations": list(record["limitations"]),
    }


__all__ = [
    "LocalVerificationError",
    "RUN_VERSION",
    "RUN_VERSION_V0",
    "RUN_VERSION_V1",
    "canonical_digest",
    "capture_environment",
    "capture_subject_manifest",
    "execute_local_verification",
    "file_digest",
    "load_profile",
    "validate_profile",
    "validate_run_record",
    "verification_source_binding",
    "verify_live_subject",
]
