"""Portable logical-tool resolution for ENV-PATH-001.

This module deliberately stops at candidate material.  Discovering or
resolving an executable never adopts it and never grants verdict authority.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import stat
import subprocess
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


PROFILE_VERSION = "semantic-guard-local-verification-profile/v3"
RESOLVED_ENVIRONMENT_VERSION = "semantic-guard-resolved-local-environment-profile/v0"


def environment_schema_directory() -> Path:
    """Resolve ENV-PATH contracts only inside the candidate package."""

    here = Path(__file__).resolve()
    packaged = here.parent / "validation" / "env-path-contracts"
    sentinel = "local-verification-profile-v3.schema.json"
    if (packaged / sentinel).is_file():
        return packaged
    raise FileNotFoundError(
        "semantic-guard ENV-PATH schemas are unavailable in the candidate package"
    )


_SCHEMA_DIRECTORY = environment_schema_directory()
_PROFILE_SCHEMA = _SCHEMA_DIRECTORY / "local-verification-profile-v3.schema.json"
_RESOLVED_SCHEMA = _SCHEMA_DIRECTORY / "resolved-local-environment-profile.schema.json"
_VERSION_COMPONENT = re.compile(r"\d+")


class EnvironmentResolutionError(RuntimeError):
    """Fail-closed resolution error carrying a stable machine code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _digest(value: bytes) -> dict[str, str]:
    return {"algorithm": "sha256", "value": hashlib.sha256(value).hexdigest()}


def canonical_digest(value: Any) -> dict[str, str]:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return _digest(encoded)


def file_digest(path: Path) -> dict[str, str]:
    digest = hashlib.sha256()
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise EnvironmentResolutionError(
            "tool_digest_open_failed", f"{path}: {exc}"
        ) from exc
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise EnvironmentResolutionError("tool_not_regular", str(path))
        while block := os.read(descriptor, 1024 * 1024):
            digest.update(block)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    before_identity = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    after_identity = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    if before_identity != after_identity:
        raise EnvironmentResolutionError("tool_changed_during_digest", str(path))
    return {"algorithm": "sha256", "value": digest.hexdigest()}


def _validate_schema(value: Mapping[str, Any], path: Path, contract: str) -> None:
    try:
        schema = json.loads(path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise EnvironmentResolutionError(
            "schema_unavailable", f"{path}: {exc}"
        ) from exc
    issues = sorted(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(value),
        key=lambda issue: tuple(str(part) for part in issue.absolute_path),
    )
    if issues:
        issue = issues[0]
        location = "/".join(str(part) for part in issue.absolute_path) or "$"
        raise EnvironmentResolutionError(
            f"{contract}_schema_invalid", f"{location}: {issue.message}"
        )


def _validate_schema_definition(
    value: Mapping[str, Any],
    *,
    path: Path,
    definition: str,
    contract: str,
) -> None:
    """Validate a reusable schema definition without trusting caller shape."""

    try:
        document = json.loads(path.read_text(encoding="utf-8"))
        schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$defs": document["$defs"],
            "$ref": f"#/$defs/{definition}",
        }
        Draft202012Validator.check_schema(schema)
    except (KeyError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise EnvironmentResolutionError(
            "schema_unavailable", f"{path}: {exc}"
        ) from exc
    issues = sorted(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(value),
        key=lambda issue: tuple(str(part) for part in issue.absolute_path),
    )
    if issues:
        issue = issues[0]
        location = "/".join(str(part) for part in issue.absolute_path) or "$"
        raise EnvironmentResolutionError(
            f"{contract}_schema_invalid", f"{location}: {issue.message}"
        )


def validate_content_addressed_ref(value: Mapping[str, Any]) -> None:
    """Validate the common record-id, locator, and content-digest reference."""

    _validate_schema_definition(
        value,
        path=_RESOLVED_SCHEMA,
        definition="digest_bound_ref",
        contract="content_addressed_ref",
    )


def validate_host_identity_ref(value: Mapping[str, Any]) -> None:
    """Validate a host identity reference as content-addressed evidence material."""

    _validate_schema_definition(
        value,
        path=_RESOLVED_SCHEMA,
        definition="host_identity_ref",
        contract="host_identity_ref",
    )


def validate_verification_profile(profile: Mapping[str, Any]) -> None:
    _validate_schema(profile, _PROFILE_SCHEMA, "verification_profile_v3")
    tool_ids = [
        str(item["tool_id"])
        for item in profile["environment_contract"]["tool_requirements"]
    ]
    if len(tool_ids) != len(set(tool_ids)):
        raise EnvironmentResolutionError("duplicate_tool_id", repr(tool_ids))
    declared = set(tool_ids)
    for command in profile["commands"]:
        if command["tool_id"] not in declared:
            raise EnvironmentResolutionError(
                "command_unknown_tool_id",
                f"{command['command_id']}: {command['tool_id']}",
            )


def validate_resolved_environment_profile(profile: Mapping[str, Any]) -> None:
    _validate_schema(profile, _RESOLVED_SCHEMA, "resolved_environment_profile")
    material = dict(profile)
    observed_digest = material.pop("basis_digest")
    if canonical_digest(material) != observed_digest:
        raise EnvironmentResolutionError(
            "environment_basis_digest_mismatch",
            str(profile.get("environment_profile_id")),
        )
    tool_ids = [str(item["tool_id"]) for item in profile["resolved_tools"]]
    if len(tool_ids) != len(set(tool_ids)):
        raise EnvironmentResolutionError("duplicate_resolved_tool_id", repr(tool_ids))


def platform_observation() -> dict[str, str]:
    return {
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
    }


def discover_parent_path_candidates(
    tool_name: str,
    *,
    parent_path: str | None = None,
) -> dict[str, Any]:
    """Return discovery-only PATH candidates without selecting or adopting one."""

    if not tool_name or "/" in tool_name or "\\" in tool_name:
        raise EnvironmentResolutionError("invalid_discovery_tool_name", tool_name)
    raw_path = os.environ.get("PATH", "") if parent_path is None else parent_path
    candidates: list[str] = []
    seen: set[str] = set()
    for raw_directory in raw_path.split(os.pathsep):
        if not raw_directory:
            continue
        candidate = Path(raw_directory) / tool_name
        try:
            absolute = str(candidate.absolute())
            usable = candidate.is_file() and os.access(candidate, os.X_OK)
        except OSError:
            usable = False
            absolute = str(candidate)
        if usable and absolute not in seen:
            seen.add(absolute)
            candidates.append(absolute)
    return {
        "tool_name": tool_name,
        "discovery_only": True,
        "formal_authority": "none",
        "candidate_paths": candidates,
    }


def _version_tuple(value: str) -> tuple[int, ...]:
    components = [int(item) for item in _VERSION_COMPONENT.findall(value)]
    if not components:
        raise EnvironmentResolutionError("tool_version_unparseable", value)
    while len(components) > 1 and components[-1] == 0:
        components.pop()
    return tuple(components)


def _version_matches(version: str, constraint: Mapping[str, Any]) -> bool:
    observed = _version_tuple(version)
    exact = constraint.get("exact")
    minimum = constraint.get("minimum_inclusive")
    maximum = constraint.get("maximum_exclusive")
    if exact is not None and observed != _version_tuple(str(exact)):
        return False
    if minimum is not None and observed < _version_tuple(str(minimum)):
        return False
    if maximum is not None and observed >= _version_tuple(str(maximum)):
        return False
    return True


def _observe_version(path: Path, probe_kind: str) -> str:
    if probe_kind == "python":
        argv = [
            str(path),
            "-I",
            "-c",
            "import platform; print(platform.python_version())",
        ]
        pattern = re.compile(r"^([0-9]+(?:\.[0-9]+)+)$")
    elif probe_kind == "uv":
        argv = [str(path), "--version"]
        pattern = re.compile(r"^uv\s+([^\s]+)")
    else:  # Schema validation should make this unreachable.
        raise EnvironmentResolutionError("unsupported_version_probe", probe_kind)
    try:
        completed = subprocess.run(
            argv,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            check=False,
            timeout=15,
            env={"PATH": "", "LC_ALL": "C"},
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise EnvironmentResolutionError(
            "tool_version_probe_failed", f"{path}: {exc}"
        ) from exc
    output = completed.stdout.decode("utf-8", errors="replace").strip()
    if completed.returncode != 0:
        raise EnvironmentResolutionError(
            "tool_version_probe_failed",
            f"{path}: exit={completed.returncode}",
        )
    match = pattern.match(output)
    if match is None:
        raise EnvironmentResolutionError(
            "tool_version_unparseable", f"{path}: {output!r}"
        )
    return match.group(1)


def _platform_matches(
    observed: Mapping[str, str], supported: Sequence[Mapping[str, Any]]
) -> bool:
    return any(
        item["system"] == observed["system"]
        and item["machine"] == observed["machine"]
        and (
            "release_pattern" not in item
            or re.fullmatch(str(item["release_pattern"]), observed["release"])
            is not None
        )
        for item in supported
    )


def effective_path_from_resolved_tools(
    resolved_tools: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Derive the managed PATH only from verified real executable locations."""

    by_directory: dict[str, list[str]] = {}
    order: list[str] = []
    for tool in resolved_tools:
        resolved_path = Path(str(tool["resolved_path"]))
        if not resolved_path.is_absolute():
            raise EnvironmentResolutionError(
                "resolved_tool_path_not_absolute", str(resolved_path)
            )
        directory = str(resolved_path.parent)
        if directory not in by_directory:
            by_directory[directory] = []
            order.append(directory)
        by_directory[directory].append(str(tool["tool_id"]))
    entries = [
        {
            "directory": directory,
            "source_tool_ids": sorted(by_directory[directory]),
        }
        for directory in order
    ]
    rendered = os.pathsep.join(order)
    return {
        "policy": "managed_minimal_from_adopted_tools",
        "entries": entries,
        "rendered_value": rendered,
        "content_digest": _digest(rendered.encode("utf-8")),
    }


def _observe_tool(
    requirement: Mapping[str, Any],
    candidate_path: Path,
    observed_platform: Mapping[str, str],
    *,
    enforce_constraints: bool = True,
) -> dict[str, Any]:
    if not candidate_path.is_absolute():
        raise EnvironmentResolutionError(
            "tool_candidate_not_absolute", str(candidate_path)
        )
    try:
        if not candidate_path.is_file():
            raise EnvironmentResolutionError(
                "tool_candidate_not_file", str(candidate_path)
            )
        resolved = candidate_path.resolve(strict=True)
    except OSError as exc:
        raise EnvironmentResolutionError(
            "tool_candidate_resolution_failed", f"{candidate_path}: {exc}"
        ) from exc
    if not resolved.is_file():
        raise EnvironmentResolutionError("tool_candidate_not_file", str(resolved))
    version = _observe_version(resolved, str(requirement["version_probe"]))
    version_match = _version_matches(version, requirement["version_constraint"])
    platform_match = _platform_matches(
        observed_platform, requirement["supported_platforms"]
    )
    digest = file_digest(resolved)
    digest_constraint = requirement["digest_constraint"]
    digest_match = digest_constraint[
        "policy"
    ] == "adopted_exact" or digest == digest_constraint.get("digest")
    if enforce_constraints and not platform_match:
        raise EnvironmentResolutionError(
            "unsupported_tool_platform", str(requirement["tool_id"])
        )
    if enforce_constraints and not version_match:
        raise EnvironmentResolutionError(
            "tool_version_constraint_mismatch",
            f"{requirement['tool_id']}: {version}",
        )
    if enforce_constraints and not digest_match:
        raise EnvironmentResolutionError(
            "tool_digest_constraint_mismatch", str(requirement["tool_id"])
        )
    return {
        "tool_id": str(requirement["tool_id"]),
        "candidate_source": str(requirement["candidate_source"]),
        "invocation_path": str(candidate_path),
        "resolved_path": str(resolved),
        "version": version,
        "version_probe": str(requirement["version_probe"]),
        "file_digest": digest,
        "constraint_evaluation": {
            "version_matches": version_match,
            "digest_matches": digest_match,
            "platform_matches": platform_match,
        },
    }


def resolve_environment_candidate(
    verification_profile: Mapping[str, Any],
    *,
    explicit_candidates: Mapping[str, Sequence[Path]],
    host_identity_ref: Mapping[str, Any],
    observed_platform: Mapping[str, str] | None = None,
    environment_profile_id: str = "environment.local.candidate",
    environment_profile_version: str = "1",
) -> dict[str, Any]:
    """Resolve explicit candidates into a non-authoritative environment profile."""

    validate_verification_profile(verification_profile)
    platform_value = dict(observed_platform or platform_observation())
    requirements = verification_profile["environment_contract"]["tool_requirements"]
    resolved_tools: list[dict[str, Any]] = []
    for requirement in requirements:
        tool_id = str(requirement["tool_id"])
        raw_candidates = explicit_candidates.get(tool_id, ())
        unique_candidates: list[Path] = []
        seen: set[str] = set()
        for raw in raw_candidates:
            candidate = Path(raw).absolute()
            key = str(candidate)
            if key not in seen:
                seen.add(key)
                unique_candidates.append(candidate)
        if len(unique_candidates) != 1:
            raise EnvironmentResolutionError(
                "tool_resolution_not_unique",
                f"{tool_id}: observed {len(unique_candidates)} explicit candidates",
            )
        resolved_tools.append(
            _observe_tool(requirement, unique_candidates[0], platform_value)
        )
    portable_basis = {
        "profile_id": verification_profile["profile_id"],
        "profile_version": verification_profile["profile_version"],
        "environment_contract": verification_profile["environment_contract"],
    }
    candidate: dict[str, Any] = {
        "schema_version": RESOLVED_ENVIRONMENT_VERSION,
        "environment_profile_id": environment_profile_id,
        "environment_profile_version": environment_profile_version,
        "lifecycle_state": "candidate",
        "formal_authority": "none",
        "positive_assurance_allowed": False,
        "verification_profile_basis_digest": canonical_digest(portable_basis),
        "platform": platform_value,
        "host_identity_ref": dict(host_identity_ref),
        "resolved_tools": resolved_tools,
        "effective_path": effective_path_from_resolved_tools(resolved_tools),
        "limitations": [
            "Candidate generation is not human adoption and grants no execution or verdict authority.",
            "Child-process executable observation is not implemented; positive assurance is prohibited.",
            "Pre/post file observations do not close an adversarial change-and-restore race.",
        ],
    }
    candidate["basis_digest"] = canonical_digest(candidate)
    validate_resolved_environment_profile(candidate)
    return candidate


def observe_resolved_environment(
    candidate_profile: Mapping[str, Any],
    *,
    host_identity_ref: Mapping[str, Any],
    observed_platform: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Observe current state only through paths sealed in a candidate profile."""

    validate_resolved_environment_profile(candidate_profile)
    current_platform = dict(observed_platform or platform_observation())
    tools = []
    for expected in candidate_profile["resolved_tools"]:
        path = Path(str(expected["invocation_path"]))
        requirement = {
            "tool_id": expected["tool_id"],
            "candidate_source": expected["candidate_source"],
            "version_probe": expected["version_probe"],
            "version_constraint": {"exact": expected["version"]},
            "digest_constraint": {
                "policy": "exact",
                "digest": expected["file_digest"],
            },
            "supported_platforms": [
                {
                    "system": candidate_profile["platform"]["system"],
                    "machine": candidate_profile["platform"]["machine"],
                    "release_pattern": re.escape(
                        str(candidate_profile["platform"]["release"])
                    ),
                }
            ],
        }
        tools.append(
            _observe_tool(
                requirement,
                path,
                current_platform,
                enforce_constraints=False,
            )
        )
    return {
        "platform": current_platform,
        "host_identity_ref": dict(host_identity_ref),
        "resolved_tools": tools,
        "effective_path": effective_path_from_resolved_tools(tools),
    }


__all__ = [
    "EnvironmentResolutionError",
    "PROFILE_VERSION",
    "RESOLVED_ENVIRONMENT_VERSION",
    "canonical_digest",
    "discover_parent_path_candidates",
    "effective_path_from_resolved_tools",
    "environment_schema_directory",
    "file_digest",
    "observe_resolved_environment",
    "platform_observation",
    "resolve_environment_candidate",
    "validate_content_addressed_ref",
    "validate_host_identity_ref",
    "validate_resolved_environment_profile",
    "validate_verification_profile",
]
