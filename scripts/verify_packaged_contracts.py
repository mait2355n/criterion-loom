#!/usr/bin/env python3
"""Verify v1 contract resources from an installed wheel, not the source tree.

The verifier installs one local wheel into a fresh temporary virtual
environment, plants controlled decoy resources beside site-packages, and runs
a fixed audit program with isolated Python path handling.  It never accepts an
alternate Python executable, audit program, or resource directory from the
caller.

The wheel itself is necessarily imported by the audit process.  This is a
distribution-integrity check, not an operating-system sandbox for untrusted
code.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
from pathlib import PurePosixPath
import signal
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
from typing import Any, Mapping, Sequence
import zipfile


SCHEMA_VERSION = "semantic-guard-packaged-contract-verification/v0"
DEFAULT_TIMEOUT_SECONDS = 180.0
MIN_TIMEOUT_SECONDS = 15.0
MAX_TIMEOUT_SECONDS = 300.0
MAX_WHEEL_BYTES = 64 * 1024 * 1024
MAX_WHEEL_ENTRIES = 4096
MAX_WHEEL_UNCOMPRESSED_BYTES = 256 * 1024 * 1024
MAX_SDIST_BYTES = 64 * 1024 * 1024
MAX_SDIST_ENTRIES = 4096
MAX_SDIST_UNCOMPRESSED_BYTES = 256 * 1024 * 1024
MAX_CAPTURE_BYTES = 1024 * 1024
MAX_CHILD_FILE_BYTES = 256 * 1024 * 1024
MAX_CHILD_ADDRESS_SPACE_BYTES = 4 * 1024 * 1024 * 1024
MAX_CHILD_OPEN_FILES = 256

_ALLOWED_PACKAGED_VALIDATION_FILES = frozenset(
    {
        "engineering-rule-pack.candidate.json",
        "engineering-rule-pack.schema.json",
        "lifecycle-profile-registry.candidate.json",
    }
)
_ALLOWED_SDIST_ROOTS = frozenset(
    {
        ".gitignore",
        "LICENSE",
        "PKG-INFO",
        "README.md",
        "constitution",
        "pyproject.toml",
        "schemas",
        "src",
        "validation",
    }
)
_CANONICAL_SDIST_ROOT = "semantic_guard-1.1.0"
_CANONICAL_WHEEL_ROOTS = frozenset(
    {"semantic_guard", "semantic_guard-1.1.0.dist-info"}
)


_AUDIT_PROGRAM = r'''
from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.util
from importlib import resources
from importlib.metadata import distribution
import json
from pathlib import Path
import sys

from jsonschema import Draft202012Validator, FormatChecker


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


spec = importlib.util.find_spec("semantic_guard")
require(spec is not None and spec.submodule_search_locations, "installed package not found")
package_root = Path(tuple(spec.submodule_search_locations)[0]).resolve()
prefix = Path(sys.prefix).resolve()
try:
    package_root.relative_to(prefix)
except ValueError as exc:
    raise RuntimeError("semantic_guard was not imported from the isolated environment") from exc

# These locations reproduce the accidental source-tree fallbacks that an
# installed module could otherwise derive through Path(__file__).parents[2].
adjacent_root = package_root.parents[1]
decoy_validation = adjacent_root / "validation"
decoy_schemas = adjacent_root / "schemas"
decoy_validation.mkdir()
decoy_schemas.mkdir()
(adjacent_root / "pyproject.toml").write_text(
    "[project]\nname = 'decoy-neighbour'\nversion = '0'\n",
    encoding="utf-8",
)
(decoy_validation / "lifecycle-profile-registry.candidate.json").write_text(
    json.dumps({"schema_version": "decoy-lifecycle-profile/v0"}),
    encoding="utf-8",
)
(decoy_schemas / "operational-outcome-evaluation.schema.json").write_text(
    "{}\n",
    encoding="utf-8",
)

from semantic_guard import __version__, lifecycle_profiles
from semantic_guard import operational_outcomes
from semantic_guard.cli import build_parser
from semantic_guard.lifecycle_profiles import (
    load_candidate_registry,
    validate_lifecycle_profile_registry,
)
from semantic_guard.mcp_server import (
    audit_direction_binding_service,
    audit_requirement_relations_service,
    mcp,
    semantic_guard_schema_resource,
)
from semantic_guard.public_contract import KNOWN_SCHEMA_NAMES, load_public_schema
from semantic_guard.schema_access import schema_directory

installed_distribution = distribution("semantic-guard")
require(
    installed_distribution.metadata["Name"] == "semantic-guard",
    "installed distribution name is not canonical",
)
require(installed_distribution.version == "1.1.0", "installed distribution is not v1.1.0")
require(__version__ == installed_distribution.version, "package and distribution versions differ")
require(mcp.name == "semantic-guard", "MCP server name is not canonical")
mcp_tools = asyncio.run(mcp.list_tools())
mcp_resources = asyncio.run(mcp.list_resources())
mcp_resource_templates = asyncio.run(mcp.list_resource_templates())
require(
    {tool.name for tool in mcp_tools}
    == {
        "audit_direction_binding_tool",
        "audit_requirement_relations_tool",
        "semantic_guard_schema_tool",
        "shadow_compare_legacy_tool",
    },
    "MCP tool surface is not the canonical v1 contract",
)
require(
    {str(resource.uri) for resource in mcp_resources}
    == {"semantic-guard://constitution/v1"},
    "MCP static resource surface is not canonical",
)
require(
    {template.uriTemplate for template in mcp_resource_templates}
    == {"semantic-guard://schemas/{name}"},
    "MCP resource-template surface is not canonical",
)

selected_schema_directory = schema_directory().resolve()
selected_lifecycle = Path(lifecycle_profiles._CANDIDATE_PATH).resolve()
selected_operational = Path(operational_outcomes._SCHEMA_PATH).resolve()
require(
    selected_schema_directory == package_root / "schemas",
    f"schema directory escaped package: {selected_schema_directory}",
)
require(
    selected_lifecycle == package_root / "validation" / "lifecycle-profile-registry.candidate.json",
    f"lifecycle candidate escaped package: {selected_lifecycle}",
)
require(
    selected_operational == package_root / "schemas" / "operational-outcome-evaluation.schema.json",
    f"operational schema escaped package: {selected_operational}",
)

present_names = {
    path.name.removesuffix(".schema.json")
    for path in selected_schema_directory.glob("*.schema.json")
}
known_names = set(KNOWN_SCHEMA_NAMES)
require(len(known_names) == 24, f"expected 24 public schemas, found {len(known_names)}")
require(present_names == known_names, "KNOWN_SCHEMA_NAMES and packaged schemas differ")

loaded = {}
for name in sorted(known_names):
    schema = load_public_schema(name)
    Draft202012Validator.check_schema(schema)
    resource_schema = json.loads(semantic_guard_schema_resource(name))
    require(resource_schema == schema, f"MCP schema resource differs for {name}")
    loaded[name] = schema

parser = build_parser()
subparsers_action = next(
    action for action in parser._actions
    if isinstance(action, argparse._SubParsersAction)
)
schema_parser = subparsers_action.choices["schema"]
canonical_cli_commands = {
    "audit-requirement",
    "audit-direction-binding",
    "shadow-compare",
    "schema",
}
require(
    set(subparsers_action.choices) == canonical_cli_commands,
    "canonical CLI command surface differs from the four-command contract",
)
schema_name_action = next(action for action in schema_parser._actions if action.dest == "name")
require(set(schema_name_action.choices) == known_names, "CLI schema choices differ from public schemas")

try:
    load_public_schema("../common")
except ValueError:
    pass
else:
    raise RuntimeError("public schema loader accepted path selection")

lifecycle_registry = load_candidate_registry()
validate_lifecycle_profile_registry(lifecycle_registry)
require(
    lifecycle_registry.get("schema_version") == "lifecycle-profile-registry/v0",
    "wrong lifecycle candidate was loaded",
)
require(len(lifecycle_registry.get("profiles", [])) == 10, "lifecycle profile denominator is not ten")

package_resources = resources.files("semantic_guard")
engineering_schema_resource = package_resources.joinpath(
    "validation/engineering-rule-pack.schema.json"
)
engineering_candidate_resource = package_resources.joinpath(
    "validation/engineering-rule-pack.candidate.json"
)
require(engineering_schema_resource.is_file(), "engineering rule-pack schema is missing")
require(engineering_candidate_resource.is_file(), "engineering rule-pack candidate is missing")
engineering_schema = json.loads(engineering_schema_resource.read_text(encoding="utf-8"))
engineering_candidate = json.loads(engineering_candidate_resource.read_text(encoding="utf-8"))
Draft202012Validator.check_schema(engineering_schema)
engineering_errors = list(
    Draft202012Validator(
        engineering_schema,
        format_checker=FormatChecker(),
    ).iter_errors(engineering_candidate)
)
require(
    not engineering_errors,
    "engineering rule-pack candidate failed its packaged schema: "
    + "; ".join(error.message for error in engineering_errors[:3]),
)
require(len(engineering_candidate.get("rules", [])) == 11, "engineering rule denominator is not eleven")

operational_schema = load_public_schema("operational-outcome-evaluation")
require(
    not Draft202012Validator(operational_schema).is_valid({}),
    "public operational schema accepted an empty object",
)
require(
    not operational_outcomes._schema_validator().is_valid({}),
    "operational validator selected the permissive adjacent decoy",
)

audit_payload = audit_requirement_relations_service(
    """Purpose: 検索APIが検索結果を返す
User: 検索API
Scenario: 検索APIが検索要求を処理して検索結果を返す
Expected result: 検索結果を返す
Acceptance criteria: 検索結果を返す
Verification method: 検索結果を試験で確認する
Evidence: 検索結果の試験報告""",
    analysis_mode="conditional",
)
producer_records = [
    item
    for item in audit_payload["provenance"]
    if item["source_ref"].get("role") == "audit_producer"
]
require(len(producer_records) == 1, "public audit does not identify exactly one producer")
require(
    producer_records[0]["source_ref"].get("entity_version") == "1.1.0",
    "public audit producer version is not v1.1.0",
)
direction_payload = audit_direction_binding_service(
    "横一列で、Aの次の項目はどれですか？",
    recorded_at="2026-08-23T00:00:00Z",
)
require(
    direction_payload["primary_rule_evaluation"]["state"] == "indeterminate",
    "provider-free direction audit did not fail closed",
)
require(
    direction_payload["workflow_disposition"]["status"] == "warn",
    "provider-free direction audit has the wrong workflow disposition",
)
Draft202012Validator(
    loaded["direction-binding-audit"],
    format_checker=FormatChecker(),
).validate(direction_payload)
direction_tool_content, direction_tool_payload = asyncio.run(
    mcp.call_tool(
        "audit_direction_binding_tool",
        {
            "text": "横一列で、Aの次の項目はどれですか？",
            "recorded_at": "2026-08-23T00:00:00Z",
        },
    )
)
require(direction_tool_content, "direction-binding MCP dispatch returned no content")
require(
    direction_tool_payload == direction_payload,
    "direction-binding MCP dispatch differs from the service projection",
)

print(json.dumps({
    "schema_version": "semantic-guard-installed-contract-audit/v0",
    "status": "pass",
    "counts": {
        "public_schemas": len(loaded),
        "mcp_schema_resources": len(loaded),
        "cli_schema_names": len(schema_name_action.choices),
        "cli_commands": len(subparsers_action.choices),
        "lifecycle_profiles": len(lifecycle_registry["profiles"]),
        "engineering_rules": len(engineering_candidate["rules"]),
        "mcp_tools": len(mcp_tools),
        "mcp_resources": len(mcp_resources),
        "mcp_resource_templates": len(mcp_resource_templates),
        "producer_records": len(producer_records),
    },
    "checks": [
        "isolated_installed_import",
        "adjacent_decoys_not_selected",
        "public_schema_surface_closed",
        "mcp_schema_resources_match",
        "cli_schema_names_match",
        "canonical_cli_surface",
        "lifecycle_candidate_valid",
        "engineering_rule_pack_valid",
        "operational_empty_object_rejected",
        "canonical_distribution_identity",
        "canonical_mcp_surface",
        "public_audit_producer_version",
        "direction_binding_provider_free_fail_closed",
        "direction_binding_mcp_dispatch",
    ],
    "digests": {
        "state_assessment_schema_sha256": hashlib.sha256(
            json.dumps(
                loaded["state-assessment"],
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest(),
        "direction_binding_schema_sha256": hashlib.sha256(
            json.dumps(
                loaded["direction-binding-audit"],
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest(),
        "direction_binding_payload_sha256": hashlib.sha256(
            json.dumps(
                direction_payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest(),
    },
}, ensure_ascii=False, sort_keys=True))
'''


class VerificationFailure(RuntimeError):
    """Expected verifier failure with a stable machine-readable code."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        phase: str,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.phase = phase
        self.details = dict(details or {})


class JsonArgumentParser(argparse.ArgumentParser):
    """Keep argument failures inside the JSON result contract."""

    def error(self, message: str) -> None:
        raise VerificationFailure(
            "invalid_arguments",
            message,
            phase="arguments",
        )


@dataclass(frozen=True)
class ProcessResult:
    returncode: int
    stdout: str
    stderr: str


def _json_print(payload: Mapping[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_json_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _validate_wheel(path_value: str | Path) -> tuple[Path, int, str]:
    path = Path(path_value).expanduser()
    if path.suffix != ".whl":
        raise VerificationFailure(
            "wheel_suffix_invalid",
            "--wheel must name a .whl file",
            phase="wheel_preflight",
        )
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise VerificationFailure(
            "wheel_unavailable",
            f"wheel could not be inspected: {exc}",
            phase="wheel_preflight",
        ) from exc
    if not stat.S_ISREG(metadata.st_mode) or path.is_symlink():
        raise VerificationFailure(
            "wheel_not_regular_file",
            "--wheel must be a non-symlink regular file",
            phase="wheel_preflight",
        )
    if metadata.st_size <= 0 or metadata.st_size > MAX_WHEEL_BYTES:
        raise VerificationFailure(
            "wheel_size_out_of_bounds",
            f"wheel size must be within 1..{MAX_WHEEL_BYTES} bytes",
            phase="wheel_preflight",
            details={"observed_bytes": metadata.st_size},
        )
    resolved = path.resolve(strict=True)
    try:
        with zipfile.ZipFile(resolved) as archive:
            members = archive.infolist()
            if len(members) > MAX_WHEEL_ENTRIES:
                raise VerificationFailure(
                    "wheel_entry_limit_exceeded",
                    f"wheel contains more than {MAX_WHEEL_ENTRIES} entries",
                    phase="wheel_preflight",
                    details={"observed_entries": len(members)},
                )
            total_uncompressed = 0
            for member in members:
                normalized_name = member.filename.replace("\\", "/")
                parts = PurePosixPath(normalized_name).parts
                unix_mode = member.external_attr >> 16
                if (
                    not parts
                    or PurePosixPath(normalized_name).is_absolute()
                    or ".." in parts
                    or ":" in parts[0]
                    or member.flag_bits & 0x1
                    or stat.S_ISLNK(unix_mode)
                ):
                    raise VerificationFailure(
                        "wheel_member_unsafe",
                        f"unsafe wheel member: {member.filename!r}",
                        phase="wheel_preflight",
                    )
                if member.filename.casefold().endswith(".pth"):
                    raise VerificationFailure(
                        "wheel_pth_not_allowed",
                        f"wheel may not install executable .pth files: {member.filename!r}",
                        phase="wheel_preflight",
                    )
                if _wheel_member_crosses_distribution_boundary(parts):
                    raise VerificationFailure(
                        "wheel_distribution_boundary_violation",
                        f"non-runtime repository material entered the wheel: {member.filename!r}",
                        phase="wheel_preflight",
                    )
                total_uncompressed += member.file_size
                if total_uncompressed > MAX_WHEEL_UNCOMPRESSED_BYTES:
                    raise VerificationFailure(
                        "wheel_uncompressed_limit_exceeded",
                        "wheel uncompressed size exceeds the verifier limit",
                        phase="wheel_preflight",
                        details={"observed_bytes": total_uncompressed},
                    )
    except zipfile.BadZipFile as exc:
        raise VerificationFailure(
            "wheel_zip_invalid",
            "wheel is not a valid ZIP archive",
            phase="wheel_preflight",
        ) from exc
    return resolved, metadata.st_size, _sha256(resolved)


def _wheel_member_crosses_distribution_boundary(parts: tuple[str, ...]) -> bool:
    if not parts:
        return True
    if parts[0] not in _CANONICAL_WHEEL_ROOTS:
        return True
    if "semantic-guard-v0.1.0" in parts:
        return True
    if parts[0] == "semantic_guard-1.1.0.dist-info":
        if len(parts) == 2:
            return parts[1] not in {"METADATA", "RECORD", "WHEEL", "entry_points.txt"}
        return not (
            len(parts) == 3
            and parts[1] == "licenses"
            and parts[2] == "LICENSE"
        )
    if any(part in {"docs", "legacy", "migration", "tests"} for part in parts[1:]):
        return True
    if len(parts) >= 2 and parts[0] == "semantic_guard" and parts[1] == "validation":
        return len(parts) != 3 or parts[2] not in _ALLOWED_PACKAGED_VALIDATION_FILES
    return False


def _validate_sdist(path_value: str | Path | None) -> tuple[Path, int, str]:
    if path_value is None:
        raise VerificationFailure(
            "sdist_required",
            "--sdist is required so repository-only archives and histories are checked",
            phase="sdist_preflight",
        )
    path = Path(path_value).expanduser()
    if not path.name.endswith(".tar.gz"):
        raise VerificationFailure(
            "sdist_suffix_invalid",
            "--sdist must name a .tar.gz file",
            phase="sdist_preflight",
        )
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise VerificationFailure(
            "sdist_unavailable",
            f"sdist could not be inspected: {exc}",
            phase="sdist_preflight",
        ) from exc
    if not stat.S_ISREG(metadata.st_mode) or path.is_symlink():
        raise VerificationFailure(
            "sdist_not_regular_file",
            "--sdist must be a non-symlink regular file",
            phase="sdist_preflight",
        )
    if metadata.st_size <= 0 or metadata.st_size > MAX_SDIST_BYTES:
        raise VerificationFailure(
            "sdist_size_out_of_bounds",
            f"sdist size must be within 1..{MAX_SDIST_BYTES} bytes",
            phase="sdist_preflight",
            details={"observed_bytes": metadata.st_size},
        )
    resolved = path.resolve(strict=True)
    try:
        with tarfile.open(resolved, mode="r:gz") as archive:
            members = archive.getmembers()
            if len(members) > MAX_SDIST_ENTRIES:
                raise VerificationFailure(
                    "sdist_entry_limit_exceeded",
                    f"sdist contains more than {MAX_SDIST_ENTRIES} entries",
                    phase="sdist_preflight",
                    details={"observed_entries": len(members)},
                )
            total_uncompressed = 0
            for member in members:
                normalized_name = member.name.replace("\\", "/")
                parts = PurePosixPath(normalized_name).parts
                if (
                    not parts
                    or PurePosixPath(normalized_name).is_absolute()
                    or ".." in parts
                    or ":" in parts[0]
                    or parts[0] != _CANONICAL_SDIST_ROOT
                    or member.issym()
                    or member.islnk()
                    or member.isdev()
                    or not (member.isfile() or member.isdir())
                ):
                    raise VerificationFailure(
                        "sdist_member_unsafe",
                        f"unsafe sdist member: {member.name!r}",
                        phase="sdist_preflight",
                    )
                relative = parts[1:]
                if not relative:
                    continue
                if _sdist_member_crosses_distribution_boundary(relative):
                    raise VerificationFailure(
                        "sdist_distribution_boundary_violation",
                        f"repository-only material entered the sdist: {member.name!r}",
                        phase="sdist_preflight",
                    )
                total_uncompressed += member.size
                if total_uncompressed > MAX_SDIST_UNCOMPRESSED_BYTES:
                    raise VerificationFailure(
                        "sdist_uncompressed_limit_exceeded",
                        "sdist uncompressed size exceeds the verifier limit",
                        phase="sdist_preflight",
                        details={"observed_bytes": total_uncompressed},
                    )
    except tarfile.TarError as exc:
        raise VerificationFailure(
            "sdist_tar_invalid",
            "sdist is not a valid gzip-compressed tar archive",
            phase="sdist_preflight",
        ) from exc
    return resolved, metadata.st_size, _sha256(resolved)


def _sdist_member_crosses_distribution_boundary(parts: tuple[str, ...]) -> bool:
    if not parts or parts[0] not in _ALLOWED_SDIST_ROOTS:
        return True
    if parts[0] == "src" and len(parts) >= 2 and parts[1] != "semantic_guard":
        return True
    if any(part in {"docs", "legacy", "migration", "tests"} for part in parts[1:]):
        return True
    if parts[0] == "validation":
        return len(parts) != 2 or parts[1] not in _ALLOWED_PACKAGED_VALIDATION_FILES
    return False


def _child_limit_function(cpu_seconds: int):
    if os.name != "posix":
        return None

    def apply_limits() -> None:
        import resource

        def set_limit(name: str, desired: int) -> None:
            kind = getattr(resource, name, None)
            if kind is None:
                return
            _soft, hard = resource.getrlimit(kind)
            bounded = desired if hard == resource.RLIM_INFINITY else min(desired, hard)
            resource.setrlimit(kind, (bounded, bounded))

        set_limit("RLIMIT_CPU", cpu_seconds)
        set_limit("RLIMIT_FSIZE", MAX_CHILD_FILE_BYTES)
        # Darwin exposes RLIMIT_AS but rejects finite values in pre-exec
        # children.  Keep the portable input, archive, time, output, file and
        # descriptor bounds there; apply the address-space cap where the
        # platform actually supports it.
        if _address_space_limit_supported():
            set_limit("RLIMIT_AS", MAX_CHILD_ADDRESS_SPACE_BYTES)
        set_limit("RLIMIT_NOFILE", MAX_CHILD_OPEN_FILES)

    return apply_limits


def _address_space_limit_supported() -> bool:
    return os.name == "posix" and sys.platform != "darwin"


def _read_capture(handle: Any, *, stream: str, phase: str) -> str:
    handle.seek(0)
    data = handle.read(MAX_CAPTURE_BYTES + 1)
    if len(data) > MAX_CAPTURE_BYTES:
        raise VerificationFailure(
            "subprocess_output_limit_exceeded",
            f"{phase} {stream} exceeded {MAX_CAPTURE_BYTES} bytes",
            phase=phase,
        )
    return data.decode("utf-8", errors="replace")


def _run_process(
    command: Sequence[str],
    *,
    allowed_executables: frozenset[Path],
    cwd: Path,
    env: Mapping[str, str],
    timeout_seconds: float,
    phase: str,
) -> ProcessResult:
    if not command:
        raise VerificationFailure(
            "empty_command",
            "internal verifier command was empty",
            phase=phase,
        )
    executable = Path(command[0]).absolute()
    executable.resolve(strict=True)
    if executable not in allowed_executables:
        raise VerificationFailure(
            "executable_not_allowed",
            "verifier attempted to select an executable outside its fixed set",
            phase=phase,
        )
    cpu_seconds = max(2, math.ceil(timeout_seconds) + 2)
    popen_options: dict[str, Any] = {
        "cwd": cwd,
        "env": dict(env),
        "stdin": subprocess.DEVNULL,
        "text": False,
    }
    if os.name == "posix":
        popen_options["start_new_session"] = True
        popen_options["preexec_fn"] = _child_limit_function(cpu_seconds)

    with tempfile.TemporaryFile() as stdout_file, tempfile.TemporaryFile() as stderr_file:
        process = subprocess.Popen(
            list(command),
            stdout=stdout_file,
            stderr=stderr_file,
            **popen_options,
        )
        try:
            returncode = process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired as exc:
            if os.name == "posix":
                os.killpg(process.pid, signal.SIGKILL)
            else:
                process.kill()
            process.wait()
            raise VerificationFailure(
                "subprocess_timeout",
                f"{phase} exceeded {timeout_seconds:.1f} seconds",
                phase=phase,
            ) from exc
        stdout = _read_capture(stdout_file, stream="stdout", phase=phase)
        stderr = _read_capture(stderr_file, stream="stderr", phase=phase)
    return ProcessResult(returncode=returncode, stdout=stdout, stderr=stderr)


def _require_success(result: ProcessResult, *, phase: str) -> None:
    if result.returncode == 0:
        return
    raise VerificationFailure(
        "subprocess_failed",
        f"{phase} exited with status {result.returncode}",
        phase=phase,
        details={
            "returncode": result.returncode,
            "stderr": result.stderr[-4096:],
            "stdout": result.stdout[-4096:],
        },
    )


def _is_exact_console_version_output(stdout: str) -> bool:
    return stdout in {
        "semantic-guard 1.1.0\n",
        "semantic-guard 1.1.0\r\n",
    }


def _remaining(deadline: float, *, phase: str) -> float:
    value = deadline - time.monotonic()
    if value <= 0:
        raise VerificationFailure(
            "verification_timeout",
            "the packaged-contract verification deadline expired",
            phase=phase,
        )
    return value


def _venv_python(venv_root: Path) -> Path:
    if os.name == "nt":
        return venv_root / "Scripts" / "python.exe"
    return venv_root / "bin" / "python"


def _venv_console_script(venv_root: Path, name: str) -> Path:
    if os.name == "nt":
        return venv_root / "Scripts" / f"{name}.exe"
    return venv_root / "bin" / name


def _environment_value(environment: Mapping[str, str], name: str) -> str | None:
    for key, value in environment.items():
        if key.casefold() == name.casefold():
            return value
    return None


def _clean_environment(
    *,
    home: Path,
    temporary: Path,
    executable_directory: Path,
    base_environment: Mapping[str, str] | None = None,
    os_name: str | None = None,
) -> dict[str, str]:
    source_environment = os.environ if base_environment is None else base_environment
    selected_os = os.name if os_name is None else os_name
    environment = {
        "HOME": str(home),
        "PATH": str(executable_directory) + os.pathsep + os.defpath,
        "PIP_CONFIG_FILE": os.devnull,
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        "PIP_NO_INPUT": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONHASHSEED": "0",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONNOUSERSITE": "1",
        "PYTHONUTF8": "1",
        "TEMP": str(temporary),
        "TMP": str(temporary),
        "TMPDIR": str(temporary),
    }
    if selected_os == "nt":
        environment.update(
            {
                "APPDATA": str(home),
                "LOCALAPPDATA": str(home),
                "USERPROFILE": str(home),
            }
        )
        for name in ("SYSTEMROOT", "WINDIR"):
            value = _environment_value(source_environment, name)
            if value:
                environment[name] = value
    for name in (
        "ALL_PROXY",
        "HTTPS_PROXY",
        "HTTP_PROXY",
        "NO_PROXY",
        "SSL_CERT_FILE",
        "REQUESTS_CA_BUNDLE",
    ):
        value = _environment_value(source_environment, name)
        if value:
            environment[name] = value
    return environment


def verify_wheel(
    wheel_value: str | Path,
    *,
    sdist_value: str | Path | None = None,
    timeout_seconds: float,
) -> dict[str, Any]:
    if not MIN_TIMEOUT_SECONDS <= timeout_seconds <= MAX_TIMEOUT_SECONDS:
        raise VerificationFailure(
            "timeout_out_of_bounds",
            f"timeout must be between {MIN_TIMEOUT_SECONDS:g} and {MAX_TIMEOUT_SECONDS:g} seconds",
            phase="arguments",
        )
    wheel, wheel_bytes, wheel_digest = _validate_wheel(wheel_value)
    sdist, sdist_bytes, sdist_digest = _validate_sdist(sdist_value)
    deadline = time.monotonic() + timeout_seconds

    with tempfile.TemporaryDirectory(prefix="semantic-guard-wheel-") as directory:
        root = Path(directory).resolve()
        home = root / "home"
        temporary = root / "tmp"
        venv_root = root / "venv"
        home.mkdir()
        temporary.mkdir()

        bootstrap_environment = _clean_environment(
            home=home,
            temporary=temporary,
            executable_directory=Path(sys.executable).resolve().parent,
        )
        host_python = Path(sys.executable).absolute()
        host_python.resolve(strict=True)
        create_result = _run_process(
            [str(host_python), "-I", "-m", "venv", str(venv_root)],
            allowed_executables=frozenset({host_python}),
            cwd=root,
            env=bootstrap_environment,
            timeout_seconds=_remaining(deadline, phase="create_venv"),
            phase="create_venv",
        )
        _require_success(create_result, phase="create_venv")

        installed_python = _venv_python(venv_root).absolute()
        installed_python.resolve(strict=True)
        installed_environment = _clean_environment(
            home=home,
            temporary=temporary,
            executable_directory=installed_python.parent,
        )
        install_result = _run_process(
            [
                str(installed_python),
                "-I",
                "-m",
                "pip",
                "install",
                "--isolated",
                "--require-virtualenv",
                "--only-binary=:all:",
                "--no-input",
                "--no-compile",
                str(wheel),
            ],
            allowed_executables=frozenset({installed_python}),
            cwd=root,
            env=installed_environment,
            timeout_seconds=_remaining(deadline, phase="install_wheel"),
            phase="install_wheel",
        )
        _require_success(install_result, phase="install_wheel")

        audit_result = _run_process(
            [str(installed_python), "-I", "-c", _AUDIT_PROGRAM],
            allowed_executables=frozenset({installed_python}),
            cwd=root,
            env=installed_environment,
            timeout_seconds=_remaining(deadline, phase="audit_installed_wheel"),
            phase="audit_installed_wheel",
        )
        _require_success(audit_result, phase="audit_installed_wheel")
        try:
            installed_audit = json.loads(audit_result.stdout)
        except json.JSONDecodeError as exc:
            raise VerificationFailure(
                "installed_audit_output_invalid",
                "installed audit did not return exactly one JSON value",
                phase="audit_installed_wheel",
                details={"stdout": audit_result.stdout[-4096:]},
            ) from exc
        if not isinstance(installed_audit, dict) or installed_audit.get("status") != "pass":
            raise VerificationFailure(
                "installed_audit_not_passed",
                "installed audit did not report pass",
                phase="audit_installed_wheel",
                details={"audit": installed_audit},
            )

        console_script = _venv_console_script(
            venv_root,
            "semantic-guard",
        ).absolute()
        try:
            console_metadata = console_script.lstat()
        except OSError as exc:
            raise VerificationFailure(
                "console_entrypoint_missing",
                f"installed console entrypoint is unavailable: {exc}",
                phase="audit_console_entrypoint",
            ) from exc
        if not stat.S_ISREG(console_metadata.st_mode) or console_script.is_symlink():
            raise VerificationFailure(
                "console_entrypoint_not_regular",
                "installed console entrypoint must be a non-symlink regular file",
                phase="audit_console_entrypoint",
            )
        mcp_console_script = _venv_console_script(
            venv_root,
            "semantic-guard-mcp",
        ).absolute()
        try:
            mcp_console_metadata = mcp_console_script.lstat()
        except OSError as exc:
            raise VerificationFailure(
                "mcp_console_entrypoint_missing",
                f"installed MCP console entrypoint is unavailable: {exc}",
                phase="audit_console_entrypoint",
            ) from exc
        if (
            not stat.S_ISREG(mcp_console_metadata.st_mode)
            or mcp_console_script.is_symlink()
        ):
            raise VerificationFailure(
                "mcp_console_entrypoint_not_regular",
                "installed MCP console entrypoint must be a non-symlink regular file",
                phase="audit_console_entrypoint",
            )
        version_result = _run_process(
            [str(console_script), "--version"],
            allowed_executables=frozenset({console_script}),
            cwd=root,
            env=installed_environment,
            timeout_seconds=_remaining(deadline, phase="audit_console_version"),
            phase="audit_console_version",
        )
        _require_success(version_result, phase="audit_console_version")
        if (
            not _is_exact_console_version_output(version_result.stdout)
            or version_result.stderr
        ):
            raise VerificationFailure(
                "console_version_mismatch",
                "installed console version does not identify semantic-guard 1.1.0",
                phase="audit_console_version",
                details={
                    "stdout": version_result.stdout[-4096:],
                    "stderr": version_result.stderr[-4096:],
                },
            )
        console_result = _run_process(
            [str(console_script), "schema", "state-assessment"],
            allowed_executables=frozenset({console_script}),
            cwd=root,
            env=installed_environment,
            timeout_seconds=_remaining(deadline, phase="audit_console_entrypoint"),
            phase="audit_console_entrypoint",
        )
        _require_success(console_result, phase="audit_console_entrypoint")
        if console_result.stderr:
            raise VerificationFailure(
                "console_entrypoint_stderr_not_empty",
                "installed schema command wrote unexpected standard error",
                phase="audit_console_entrypoint",
                details={"stderr": console_result.stderr[-4096:]},
            )
        try:
            console_schema = json.loads(console_result.stdout)
        except json.JSONDecodeError as exc:
            raise VerificationFailure(
                "console_entrypoint_output_invalid",
                "installed schema command did not return exactly one JSON value",
                phase="audit_console_entrypoint",
                details={"stdout": console_result.stdout[-4096:]},
            ) from exc
        expected_schema_digest = (
            installed_audit.get("digests", {}).get(
                "state_assessment_schema_sha256"
            )
        )
        if (
            not isinstance(expected_schema_digest, str)
            or _canonical_json_sha256(console_schema) != expected_schema_digest
        ):
            raise VerificationFailure(
                "console_entrypoint_schema_mismatch",
                "installed console schema differs from load_public_schema",
                phase="audit_console_entrypoint",
            )

        direction_schema_result = _run_process(
            [str(console_script), "schema", "direction-binding-audit"],
            allowed_executables=frozenset({console_script}),
            cwd=root,
            env=installed_environment,
            timeout_seconds=_remaining(
                deadline,
                phase="audit_direction_schema_entrypoint",
            ),
            phase="audit_direction_schema_entrypoint",
        )
        _require_success(
            direction_schema_result,
            phase="audit_direction_schema_entrypoint",
        )
        if direction_schema_result.stderr:
            raise VerificationFailure(
                "direction_schema_entrypoint_stderr_not_empty",
                "installed direction schema command wrote unexpected standard error",
                phase="audit_direction_schema_entrypoint",
                details={"stderr": direction_schema_result.stderr[-4096:]},
            )
        try:
            direction_schema = json.loads(direction_schema_result.stdout)
        except json.JSONDecodeError as exc:
            raise VerificationFailure(
                "direction_schema_entrypoint_output_invalid",
                "installed direction schema command did not return one JSON value",
                phase="audit_direction_schema_entrypoint",
            ) from exc
        expected_direction_schema_digest = installed_audit.get("digests", {}).get(
            "direction_binding_schema_sha256"
        )
        if (
            not isinstance(expected_direction_schema_digest, str)
            or _canonical_json_sha256(direction_schema)
            != expected_direction_schema_digest
        ):
            raise VerificationFailure(
                "direction_schema_entrypoint_mismatch",
                "installed direction schema differs from load_public_schema",
                phase="audit_direction_schema_entrypoint",
            )

        direction_command = [
            str(console_script),
            "audit-direction-binding",
            "--text",
            "横一列で、Aの次の項目はどれですか？",
            "--recorded-at",
            "2026-08-23T00:00:00Z",
        ]
        direction_result = _run_process(
            direction_command,
            allowed_executables=frozenset({console_script}),
            cwd=root,
            env=installed_environment,
            timeout_seconds=_remaining(
                deadline,
                phase="audit_direction_console_entrypoint",
            ),
            phase="audit_direction_console_entrypoint",
        )
        _require_success(direction_result, phase="audit_direction_console_entrypoint")
        if direction_result.stderr:
            raise VerificationFailure(
                "direction_console_entrypoint_stderr_not_empty",
                "installed direction audit wrote unexpected standard error",
                phase="audit_direction_console_entrypoint",
                details={"stderr": direction_result.stderr[-4096:]},
            )
        try:
            direction_payload = json.loads(direction_result.stdout)
        except json.JSONDecodeError as exc:
            raise VerificationFailure(
                "direction_console_entrypoint_output_invalid",
                "installed direction audit did not return one JSON value",
                phase="audit_direction_console_entrypoint",
            ) from exc
        expected_direction_payload_digest = installed_audit.get("digests", {}).get(
            "direction_binding_payload_sha256"
        )
        if (
            not isinstance(expected_direction_payload_digest, str)
            or _canonical_json_sha256(direction_payload)
            != expected_direction_payload_digest
        ):
            raise VerificationFailure(
                "direction_console_entrypoint_mismatch",
                "installed direction audit differs from MCP/service projection",
                phase="audit_direction_console_entrypoint",
            )

        fail_on_result = _run_process(
            [*direction_command, "--fail-on", "warn"],
            allowed_executables=frozenset({console_script}),
            cwd=root,
            env=installed_environment,
            timeout_seconds=_remaining(
                deadline,
                phase="audit_direction_console_fail_on",
            ),
            phase="audit_direction_console_fail_on",
        )
        if (
            fail_on_result.returncode != 3
            or fail_on_result.stderr
            or _canonical_json_sha256(json.loads(fail_on_result.stdout))
            != expected_direction_payload_digest
        ):
            raise VerificationFailure(
                "direction_console_fail_on_mismatch",
                "installed --fail-on changed payload or did not return status 3",
                phase="audit_direction_console_fail_on",
                details={
                    "returncode": fail_on_result.returncode,
                    "stderr": fail_on_result.stderr[-4096:],
                },
            )

    checks = [
        *installed_audit["checks"],
        "installed_cli_version_match",
        "installed_cli_schema_match",
        "installed_direction_schema_match",
        "installed_direction_cli_projection_match",
        "installed_direction_cli_fail_on_match",
        "installed_mcp_console_entrypoint_present",
    ]
    counts = {
        **installed_audit["counts"],
        "console_entrypoints": 2,
        "console_entrypoint_schemas": 2,
        "direction_cli_invocations": 2,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "pass",
        "subject": {
            "wheel": str(wheel),
            "sha256": wheel_digest,
            "size_bytes": wheel_bytes,
            "sdist": str(sdist),
            "sdist_sha256": sdist_digest,
            "sdist_size_bytes": sdist_bytes,
        },
        "execution": {
            "timeout_seconds": timeout_seconds,
            "isolated_environment": True,
            "fixed_executables_only": True,
            "subprocess_output_limit_bytes": MAX_CAPTURE_BYTES,
            "wheel_size_limit_bytes": MAX_WHEEL_BYTES,
            "wheel_uncompressed_limit_bytes": MAX_WHEEL_UNCOMPRESSED_BYTES,
            "sdist_size_limit_bytes": MAX_SDIST_BYTES,
            "sdist_uncompressed_limit_bytes": MAX_SDIST_UNCOMPRESSED_BYTES,
            "child_file_limit_bytes": MAX_CHILD_FILE_BYTES,
            "child_address_space_limit_bytes": (
                MAX_CHILD_ADDRESS_SPACE_BYTES
                if _address_space_limit_supported()
                else None
            ),
            "child_open_file_limit": MAX_CHILD_OPEN_FILES,
        },
        "checks": checks,
        "counts": counts,
        "errors": [],
        "limitations": [
            "The supplied wheel is imported inside a temporary virtual environment; this is not an operating-system sandbox for untrusted code.",
            "Use only a trusted local build; a wheel is executable package code even when its resource paths and subprocesses are constrained by this verifier.",
            "Dependency resolution is limited to binary distributions but still depends on the configured package index, network, and current compatible dependency versions.",
            *(
                [
                    "Darwin does not accept a finite RLIMIT_AS for these child processes; wheel size, uncompressed size, wall time, CPU, output, child-file size, and open-file limits remain enforced there."
                ]
                if not _address_space_limit_supported()
                else []
            ),
            "Pass establishes packaged-resource accessibility and local contract replay only; it does not establish field validity, operational qualification, external authenticity, security certification, or human acceptance.",
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = JsonArgumentParser(description=__doc__)
    parser.add_argument("--wheel", required=True, help="Local semantic-guard .whl file.")
    parser.add_argument(
        "--sdist",
        required=True,
        help="Matching local semantic-guard .tar.gz source distribution.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=(
            f"Whole-run wall timeout; {MIN_TIMEOUT_SECONDS:g}..{MAX_TIMEOUT_SECONDS:g} "
            f"seconds (default {DEFAULT_TIMEOUT_SECONDS:g})."
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        arguments = build_parser().parse_args(argv)
        payload = verify_wheel(
            arguments.wheel,
            sdist_value=arguments.sdist,
            timeout_seconds=arguments.timeout_seconds,
        )
    except VerificationFailure as exc:
        payload = {
            "schema_version": SCHEMA_VERSION,
            "status": "error",
            "subject": None,
            "execution": None,
            "checks": [],
            "counts": {},
            "errors": [
                {
                    "code": exc.code,
                    "phase": exc.phase,
                    "message": str(exc),
                    "details": exc.details,
                }
            ],
            "limitations": [
                "No packaged-contract conclusion may be inferred from an error result."
            ],
        }
        _json_print(payload)
        return 1
    except Exception as exc:  # preserve a JSON failure envelope for unexpected faults
        payload = {
            "schema_version": SCHEMA_VERSION,
            "status": "error",
            "subject": None,
            "execution": None,
            "checks": [],
            "counts": {},
            "errors": [
                {
                    "code": "unexpected_verifier_error",
                    "phase": "verifier",
                    "message": f"{type(exc).__name__}: {exc}",
                    "details": {},
                }
            ],
            "limitations": [
                "No packaged-contract conclusion may be inferred from an error result."
            ],
        }
        _json_print(payload)
        return 1
    _json_print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
