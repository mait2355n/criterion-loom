"""Qualified U-10 environment candidate and eligibility resolution.

This is the stricter successor path to the historical v3/v0 candidate-only
helpers.  It binds the Python environment, dependency roots, a site-free test
runner bootstrap, the exact verification profile, host observation, and a
file-backed adoption source.  It never creates a human decision.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import stat
import subprocess
import uuid
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from .environment_resolution import (
    EnvironmentResolutionError,
    canonical_digest,
    environment_schema_directory,
    file_digest,
    platform_observation,
)


PROFILE_VERSION = "semantic-guard-local-verification-profile/v4"
ENVIRONMENT_VERSION = "semantic-guard-resolved-local-environment-profile/v1"
HOST_EVIDENCE_VERSION = "semantic-guard-local-host-identity-evidence/v1"
CONTAINMENT_EVIDENCE_VERSION = "semantic-guard-process-containment-probe/v1"
ADOPTION_VERSION = "semantic-guard-local-environment-adoption/v1"
ELIGIBILITY_SOURCE_VERSION = "semantic-guard-environment-eligibility-source/v1"
ELIGIBILITY_RESOLUTION_VERSION = "semantic-guard-environment-eligibility-resolution/v1"
CLOSED_TEST_MANIFEST_VERSION = (
    "semantic-guard-closed-verification-test-manifest/v1"
)
CONTAINMENT_PROTOCOL = "macos-sandbox-no-process-creation/v1"
TRACE_PROTOCOL = "semantic-guard-process-containment-trace/v1"
TRACE_FD_ENV = "SEMANTIC_GUARD_TRACE_FD"
EXECUTION_NONCE_ENV = "SEMANTIC_GUARD_EXECUTION_NONCE"
COMMAND_DIGEST_ENV = "SEMANTIC_GUARD_COMMAND_DIGEST"
SUBJECT_MANIFEST_DIGEST_ENV = "SEMANTIC_GUARD_SUBJECT_MANIFEST_DIGEST"
HOST_OBSERVER_RECORD_ID = "semantic_guard_vnext.qualified_environment.host_observer.v1"
ELIGIBILITY_RESOLVER_RECORD_ID = "semantic_guard_vnext.qualified_environment.resolver.v1"
EXECUTION_HARNESS_RECORD_ID = (
    "semantic_guard_vnext.governed_environment_execution.harness.v1"
)

_SCHEMA_DIRECTORY = environment_schema_directory()
_PROFILE_SCHEMA = _SCHEMA_DIRECTORY / "local-verification-profile-v4.schema.json"
_ENVIRONMENT_SCHEMA = (
    _SCHEMA_DIRECTORY / "resolved-local-environment-profile-v1.schema.json"
)
_HOST_EVIDENCE_SCHEMA = (
    _SCHEMA_DIRECTORY / "local-host-identity-evidence-v1.schema.json"
)
_CONTAINMENT_EVIDENCE_SCHEMA = (
    _SCHEMA_DIRECTORY / "process-containment-probe-v1.schema.json"
)
_ADOPTION_SCHEMA = _SCHEMA_DIRECTORY / "local-environment-adoption-v1.schema.json"
_ELIGIBILITY_SOURCE_SCHEMA = (
    _SCHEMA_DIRECTORY / "environment-eligibility-source-v1.schema.json"
)
_ELIGIBILITY_RESOLUTION_SCHEMA = (
    _SCHEMA_DIRECTORY / "environment-eligibility-resolution-v1.schema.json"
)
_CLOSED_TEST_MANIFEST_SCHEMA = (
    _SCHEMA_DIRECTORY / "closed-verification-test-manifest-v1.schema.json"
)
_SNAPSHOT_ENVIRONMENT_ADOPTION_SCHEMA = (
    _SCHEMA_DIRECTORY / "u10-snapshot-environment-adoption-v1.schema.json"
)
QUALIFIED_ENVIRONMENT_CONTRACT_SCHEMA_NAMES = (
    "local-verification-profile-v4.schema.json",
    "resolved-local-environment-profile-v1.schema.json",
    "local-host-identity-evidence-v1.schema.json",
    "process-containment-probe-v1.schema.json",
    "local-environment-adoption-v1.schema.json",
    "environment-eligibility-source-v1.schema.json",
    "environment-eligibility-resolution-v1.schema.json",
    "governed-environment-execution-receipt-v1.schema.json",
    "closed-verification-test-manifest-v1.schema.json",
    "u10-root-trust-store-v2.schema.json",
    "broker-attested-execution-envelope-v2.schema.json",
    "broker-attested-execution-envelope-v3.schema.json",
    "u10-execution-request-v1.schema.json",
    "u10-execution-snapshot-manifest-v1.schema.json",
    "u10-store-activation-authorization-v1.schema.json",
    "u10-store-revocation-record-v1.schema.json",
    "u10-snapshot-adoption-authorization-v1.schema.json",
    "u10-snapshot-environment-adoption-v1.schema.json",
    "u10-store-activation-authorization-consumption-v1.schema.json",
    "u10-store-activation-transition-receipt-v2.schema.json",
    "u10-store-revocation-authorization-consumption-v1.schema.json",
    "u10-store-revocation-publication-receipt-v2.schema.json",
    "u10-bootstrap-runtime-manifest-v1.schema.json",
    "u10-bootstrap-provenance-binding-v1.schema.json",
    "u10-bootstrap-provisioning-authorization-v1.schema.json",
    "u10-bootstrap-provisioning-consumption-v1.schema.json",
    "u10-bootstrap-provisioning-plan-v1.schema.json",
    "u10-bootstrap-provisioning-receipt-v1.schema.json",
    "u10-bootstrap-runtime-observation-receipt-v1.schema.json",
    "u10-bootstrap-runtime-observation-request-v1.schema.json",
    "u10-control-publisher-contract-binding-v1.schema.json",
    "u10-control-runtime-manifest-v1.schema.json",
    "u10-initial-bootstrap-capsule-v1.schema.json",
    "u10-key-operation-authorization-consumption-v2.schema.json",
    "u10-key-operation-authorization-v2.schema.json",
    "u10-key-operation-receipt-v2.schema.json",
    "u10-signing-key-metadata-v2.schema.json",
    "u10-signing-key-revocation-v2.schema.json",
    "u10-signing-key-selector-v2.schema.json",
    "u10-key-transition-emergency-closure-v1.schema.json",
    "u10-snapshot-activation-authorization-consumption-v1.schema.json",
    "u10-snapshot-activation-basis-v1.schema.json",
    "u10-snapshot-activation-publication-receipt-v1.schema.json",
    "u10-snapshot-projection-authorization-consumption-v1.schema.json",
    "u10-snapshot-projection-authorization-v1.schema.json",
    "u10-snapshot-projection-receipt-v1.schema.json",
    "u10-store-activation-basis-v2.schema.json",
    "u10-candidate-install-authorization-v1.schema.json",
    "u10-candidate-install-authorization-consumption-v1.schema.json",
    "u10-candidate-install-projection-v1.schema.json",
    "u10-candidate-install-receipt-v2.schema.json",
    "u10-preactivation-decision-v1.schema.json",
    "u10-worker-account-observation-v1.schema.json",
    "u10-worker-principal-resolution-v1.schema.json",
    "u10-root-candidate-bundle-v1.schema.json",
)
_VERSION_COMPONENT = re.compile(r"\d+")
_DISTRIBUTION_SEPARATOR = re.compile(r"[-_.]+")
_RUNNER_VERSION_PATTERN = re.compile(
    rb'^RUNNER_VERSION\s*=\s*["\']([0-9][0-9A-Za-z.+_-]*)["\']\s*$',
    re.MULTILINE,
)

DEPENDENCY_LOCK_VERIFICATION_MODE = "uv_sync_check_frozen_exact/v1"
_UV_LOCK_CHECK_BASE_ARGUMENTS = (
    "sync",
    "--check",
    "--offline",
    "--frozen",
    "--no-install-project",
    "--python",
)


def _strict_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise json.JSONDecodeError(
                f"duplicate object key: {key!r}", key, 0
            )
        value[key] = item
    return value


def _reject_nonfinite_json_constant(value: str) -> Any:
    raise json.JSONDecodeError(f"non-finite JSON number: {value}", value, 0)


def _strict_json_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise json.JSONDecodeError(
            f"non-finite JSON number: {value}", value, 0
        )
    return parsed


def strict_json_loads(raw: str | bytes | bytearray) -> Any:
    return json.loads(
        raw,
        object_pairs_hook=_strict_json_object,
        parse_constant=_reject_nonfinite_json_constant,
        parse_float=_strict_json_float,
    )


def _json_clone(value: Any) -> Any:
    return strict_json_loads(
        json.dumps(value, ensure_ascii=False, allow_nan=False)
    )


def outer_sandbox_profile(python_resolved_path: str) -> str:
    if not Path(python_resolved_path).is_absolute() or '"' in python_resolved_path:
        raise EnvironmentResolutionError(
            "outer_sandbox_python_path_invalid", python_resolved_path
        )
    return (
        "(version 1)(allow default)(deny file-write*)(deny process-fork)(deny process-exec)"
        f'(allow process-exec (literal "{python_resolved_path}"))'
    )


def _validate_schema(
    value: Mapping[str, Any], path: Path, contract: str
) -> None:
    try:
        schema = strict_json_loads(path.read_bytes())
        Draft202012Validator.check_schema(schema)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise EnvironmentResolutionError(
            "schema_unavailable", f"{path}: {exc}"
        ) from exc
    issues = sorted(
        Draft202012Validator(
            schema, format_checker=FormatChecker()
        ).iter_errors(value),
        key=lambda issue: tuple(str(part) for part in issue.absolute_path),
    )
    if issues:
        issue = issues[0]
        location = "/".join(str(part) for part in issue.absolute_path) or "$"
        raise EnvironmentResolutionError(
            f"{contract}_schema_invalid", f"{location}: {issue.message}"
        )


def _sha256_bytes(value: bytes) -> dict[str, str]:
    return {"algorithm": "sha256", "value": hashlib.sha256(value).hexdigest()}


def artifact_bytes(value: Mapping[str, Any]) -> bytes:
    """Return the only supported JSON artifact serialization for U-10 refs."""

    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def artifact_content_digest(value: Mapping[str, Any]) -> dict[str, str]:
    return _sha256_bytes(artifact_bytes(value))


def _sealed_digest(value: Mapping[str, Any], field: str, code: str) -> None:
    material = dict(value)
    observed = material.pop(field)
    if canonical_digest(material) != observed:
        raise EnvironmentResolutionError(code, str(value.get("schema_version")))


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


def _inside_repository(root: Path, locator: str, *, code: str) -> Path:
    if not _canonical_repository_path(locator):
        raise EnvironmentResolutionError(code, locator)
    candidate = root / locator
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, ValueError) as exc:
        raise EnvironmentResolutionError(code, locator) from exc
    return resolved


def _repository_invocation_path(root: Path, locator: str) -> tuple[Path, Path]:
    """Keep a repository-owned invocation name while allowing its final symlink target outside."""

    if not _canonical_repository_path(locator):
        raise EnvironmentResolutionError("tool_candidate_locator_invalid", locator)
    invocation = (root / locator).absolute()
    try:
        invocation.parent.resolve(strict=True).relative_to(root)
        invocation.lstat()
        resolved = invocation.resolve(strict=True)
    except (OSError, ValueError) as exc:
        raise EnvironmentResolutionError("tool_candidate_locator_invalid", locator) from exc
    if not resolved.is_file():
        raise EnvironmentResolutionError("tool_candidate_not_file", str(resolved))
    return invocation, resolved


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
    return not (
        (exact is not None and observed != _version_tuple(str(exact)))
        or (minimum is not None and observed < _version_tuple(str(minimum)))
        or (maximum is not None and observed >= _version_tuple(str(maximum)))
    )


def _platform_matches(
    observed: Mapping[str, str], supported: Sequence[Mapping[str, Any]]
) -> bool:
    for item in supported:
        try:
            release_matches = "release_pattern" not in item or re.fullmatch(
                str(item["release_pattern"]), observed["release"]
            ) is not None
        except re.error as exc:
            raise EnvironmentResolutionError(
                "invalid_release_pattern", str(item.get("release_pattern"))
            ) from exc
        if (
            item["system"] == observed["system"]
            and item["machine"] == observed["machine"]
            and release_matches
        ):
            return True
    return False


def verification_profile_ref(profile: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "profile_id": profile["profile_id"],
        "profile_version": profile["profile_version"],
        "content_digest": canonical_digest(profile),
    }


def environment_profile_ref(profile: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "environment_profile_id": profile["environment_profile_id"],
        "environment_profile_version": profile["environment_profile_version"],
        "basis_digest": profile["basis_digest"],
    }


def adoption_ref(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "adoption_id": record["adoption_id"],
        "adoption_version": record["adoption_version"],
        "adoption_digest": record["adoption_digest"],
    }


def validate_verification_profile_v4(profile: Mapping[str, Any]) -> None:
    _validate_schema(profile, _PROFILE_SCHEMA, "verification_profile_v4")
    requirements = list(profile["environment_contract"]["tool_requirements"])
    tool_ids = [str(item["tool_id"]) for item in requirements]
    if any(
        tool_ids.count(expected) != 1
        for expected in (
            "containment_launcher.vnext",
            "python.vnext",
            "test_runner.vnext",
        )
    ):
        raise EnvironmentResolutionError("qualified_tool_denominator_mismatch", repr(tool_ids))
    command_ids = [str(item["command_id"]) for item in profile["commands"]]
    if len(command_ids) != len(set(command_ids)):
        raise EnvironmentResolutionError("duplicate_command_id", repr(command_ids))
    fixed = set(profile["environment_contract"]["fixed_environment"])
    inherited = set(
        profile["environment_contract"]["inherited_environment_allowlist"]
    )
    if fixed & inherited:
        raise EnvironmentResolutionError(
            "environment_contract_variable_conflict", repr(sorted(fixed & inherited))
        )
    for requirement in requirements:
        locator = str(requirement["candidate_locator"])
        if (
            requirement["candidate_source"] == "repository_relative"
            and not _canonical_repository_path(locator)
        ):
            raise EnvironmentResolutionError("tool_candidate_locator_invalid", locator)
        for lock_path in requirement["capability_contract"]["lock_paths"]:
            if not _canonical_repository_path(str(lock_path)):
                raise EnvironmentResolutionError("lock_path_invalid", str(lock_path))
        for platform_contract in requirement["supported_platforms"]:
            if "release_pattern" in platform_contract:
                try:
                    re.compile(str(platform_contract["release_pattern"]))
                except re.error as exc:
                    raise EnvironmentResolutionError(
                        "invalid_release_pattern",
                        str(platform_contract["release_pattern"]),
                    ) from exc


def load_closed_test_manifest_v1(
    reference: Mapping[str, Any],
    *,
    repository_root: Path,
    expected_command_id: str,
) -> dict[str, Any]:
    """Load and close every subject/test denominator before qualification."""

    locator = str(reference.get("locator", ""))
    path = _inside_repository(
        repository_root.resolve(strict=True),
        locator,
        code="closed_test_manifest_locator_invalid",
    )
    if file_digest(path) != reference.get("content_digest"):
        raise EnvironmentResolutionError(
            "closed_test_manifest_artifact_digest_mismatch", locator
        )
    try:
        manifest = strict_json_loads(path.read_bytes())
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise EnvironmentResolutionError(
            "closed_test_manifest_load_failed", f"{locator}: {exc}"
        ) from exc
    if not isinstance(manifest, dict):
        raise EnvironmentResolutionError(
            "closed_test_manifest_root_not_object", locator
        )
    _validate_schema(
        manifest, _CLOSED_TEST_MANIFEST_SCHEMA, "closed_test_manifest_v1"
    )
    _sealed_digest(
        manifest,
        "manifest_digest",
        "closed_test_manifest_digest_mismatch",
    )
    if manifest["schema_version"] != CLOSED_TEST_MANIFEST_VERSION:
        raise EnvironmentResolutionError(
            "closed_test_manifest_version_mismatch", locator
        )
    if manifest["command_id"] != expected_command_id:
        raise EnvironmentResolutionError(
            "closed_test_manifest_command_mismatch", expected_command_id
        )
    subject = manifest["subject_denominator"]
    tests = manifest["test_denominator"]
    if subject["entry_count"] != len(subject["entries"]):
        raise EnvironmentResolutionError(
            "closed_subject_denominator_count_mismatch", expected_command_id
        )
    if tests["module_count"] != len(tests["modules"]):
        raise EnvironmentResolutionError(
            "closed_test_module_count_mismatch", expected_command_id
        )
    if len(tests["test_source_refs"]) != len(tests["modules"]):
        raise EnvironmentResolutionError(
            "closed_test_source_module_cardinality_mismatch",
            expected_command_id,
        )
    if tests["test_count"] != len(tests["expected_test_ids"]):
        raise EnvironmentResolutionError(
            "closed_test_denominator_count_mismatch", expected_command_id
        )
    if not tests["modules"] or not tests["expected_test_ids"]:
        raise EnvironmentResolutionError(
            "closed_test_denominator_empty", expected_command_id
        )
    references = [
        item["artifact_ref"] for item in subject["entries"]
    ] + list(tests["test_source_refs"])
    ref_keys: set[tuple[str, str]] = set()
    for artifact_ref in references:
        ref_key = (str(artifact_ref["record_id"]), str(artifact_ref["locator"]))
        if ref_key in ref_keys:
            raise EnvironmentResolutionError(
                "closed_test_manifest_duplicate_artifact_ref", repr(ref_key)
            )
        ref_keys.add(ref_key)
        artifact = _inside_repository(
            repository_root.resolve(strict=True),
            str(artifact_ref["locator"]),
            code="closed_test_manifest_artifact_locator_invalid",
        )
        if file_digest(artifact) != artifact_ref["content_digest"]:
            raise EnvironmentResolutionError(
                "closed_test_manifest_subject_digest_mismatch",
                str(artifact_ref["locator"]),
            )
    return manifest


def validate_profile_closed_test_manifests_v1(
    profile: Mapping[str, Any], *, repository_root: Path
) -> dict[str, dict[str, Any]]:
    validate_verification_profile_v4(profile)
    for command in profile["commands"]:
        if (
            command["containment_launcher_tool_id"]
            != "containment_launcher.vnext"
            or command["interpreter_tool_id"] != "python.vnext"
            or command["tool_id"] != "test_runner.vnext"
        ):
            raise EnvironmentResolutionError(
                "command_tool_denominator_mismatch", str(command["command_id"])
            )
        if not _canonical_repository_path(str(command["cwd"]), allow_root=True):
            raise EnvironmentResolutionError(
                "command_cwd_invalid", str(command["cwd"])
            )
    manifests: dict[str, dict[str, Any]] = {}
    for command in profile["commands"]:
        command_id = str(command["command_id"])
        manifests[command_id] = load_closed_test_manifest_v1(
            command["closed_test_manifest_ref"],
            repository_root=repository_root,
            expected_command_id=command_id,
        )
    return manifests


def _host_evidence_body(evidence_id: str) -> dict[str, Any]:
    observed_platform = platform_observation()
    node_digest = canonical_digest({"platform_node": platform.node()})
    hardware_digest = canonical_digest({"uuid_getnode": f"{uuid.getnode():012x}"})
    identity_material = {
        "observed_platform": observed_platform,
        "node_name_digest": node_digest,
        "hardware_identifier_digest": hardware_digest,
        "observation_method": "platform-node-and-uuid-getnode-hashed/v1",
    }
    return {
        "schema_version": HOST_EVIDENCE_VERSION,
        "evidence_id": evidence_id,
        **identity_material,
        "identity_digest": canonical_digest(identity_material),
        "formal_authority": "none",
        "positive_assurance_allowed": False,
        "limitations": [
            "Hashed local identifiers reduce disclosure but are not a hardware trust anchor.",
            "Clone, spoof, ownership, principal identity, and revocation remain outside U-10.",
            "A different OS release or machine requires a newly adopted environment profile.",
        ],
    }


def capture_host_identity_evidence(
    *, evidence_id: str = "evidence.host.local.u10"
) -> dict[str, Any]:
    evidence = _host_evidence_body(evidence_id)
    evidence["evidence_digest"] = canonical_digest(evidence)
    validate_host_identity_evidence(evidence)
    return evidence


def validate_host_identity_evidence(evidence: Mapping[str, Any]) -> None:
    _validate_schema(evidence, _HOST_EVIDENCE_SCHEMA, "host_identity_evidence")
    _sealed_digest(
        evidence, "evidence_digest", "host_identity_evidence_digest_mismatch"
    )
    identity_material = {
        "observed_platform": evidence["observed_platform"],
        "node_name_digest": evidence["node_name_digest"],
        "hardware_identifier_digest": evidence["hardware_identifier_digest"],
        "observation_method": evidence["observation_method"],
    }
    if canonical_digest(identity_material) != evidence["identity_digest"]:
        raise EnvironmentResolutionError(
            "host_identity_digest_mismatch", str(evidence["evidence_id"])
        )


def _artifact_ref(
    record_id: str, locator: str, value: Mapping[str, Any]
) -> dict[str, Any]:
    if not _canonical_repository_path(locator):
        raise EnvironmentResolutionError("artifact_locator_invalid", locator)
    return {
        "record_id": record_id,
        "locator": locator,
        "content_digest": artifact_content_digest(value),
    }


def host_identity_ref(
    evidence: Mapping[str, Any], *, locator: str
) -> dict[str, Any]:
    validate_host_identity_evidence(evidence)
    return {
        "host_id": f"host.local.{evidence['identity_digest']['value'][:24]}",
        "identity_digest": evidence["identity_digest"],
        "evidence_ref": _artifact_ref(
            str(evidence["evidence_id"]), locator, evidence
        ),
    }


def _invocation_identity(
    invocation: Path, resolved: Path, resolved_digest: Mapping[str, Any]
) -> dict[str, Any]:
    try:
        metadata = invocation.lstat()
    except OSError as exc:
        raise EnvironmentResolutionError(
            "tool_invocation_lstat_failed", str(invocation)
        ) from exc
    if stat.S_ISLNK(metadata.st_mode):
        path_kind = "symlink"
        symlink_target: str | None = os.readlink(invocation)
    elif stat.S_ISREG(metadata.st_mode):
        path_kind = "regular"
        symlink_target = None
    else:
        raise EnvironmentResolutionError("tool_invocation_kind_invalid", str(invocation))
    material = {
        "invocation_path": str(invocation),
        "path_kind": path_kind,
        "symlink_target": symlink_target,
        "resolved_path": str(resolved),
        "resolved_file_digest": resolved_digest,
    }
    return {
        "path_kind": path_kind,
        "symlink_target": symlink_target,
        "identity_digest": canonical_digest(material),
    }


def _directory_manifest(path: Path) -> tuple[int, dict[str, str]]:
    try:
        root = path.resolve(strict=True)
    except OSError as exc:
        raise EnvironmentResolutionError("import_root_unavailable", str(path)) from exc
    if not root.is_dir():
        raise EnvironmentResolutionError("import_root_not_directory", str(root))
    entries: list[dict[str, Any]] = []
    for directory, raw_directories, raw_files in os.walk(root, followlinks=False):
        current = Path(directory)
        for name in sorted(raw_directories):
            candidate = current / name
            if candidate.is_symlink():
                entries.append(
                    {
                        "path": candidate.relative_to(root).as_posix(),
                        "kind": "symlink",
                        "target": os.readlink(candidate),
                    }
                )
        for name in sorted(raw_files):
            candidate = current / name
            relative = candidate.relative_to(root).as_posix()
            if candidate.is_symlink():
                entries.append(
                    {"path": relative, "kind": "symlink", "target": os.readlink(candidate)}
                )
            else:
                entries.append(
                    {"path": relative, "kind": "file", "file_digest": file_digest(candidate)}
                )
    if not entries:
        raise EnvironmentResolutionError("import_root_empty", str(root))
    entries.sort(key=lambda item: (str(item["path"]), str(item["kind"])))
    return len(entries), canonical_digest(entries)


def _lock_binding(root: Path, locator: str) -> dict[str, Any]:
    resolved = _inside_repository(root, locator, code="lock_path_invalid")
    return {
        "path": locator,
        "resolved_path": str(resolved),
        "file_digest": file_digest(resolved),
    }


def _normalize_distribution_name(value: str) -> str:
    normalized = _DISTRIBUTION_SEPARATOR.sub("-", value).lower()
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", normalized):
        raise EnvironmentResolutionError("distribution_name_invalid", value)
    return normalized


def _python_site_path(invocation: Path, version: str) -> Path:
    environment_root = invocation.parent.parent
    components = version.split(".")
    if len(components) < 2:
        raise EnvironmentResolutionError("tool_version_unparseable", version)
    candidate = environment_root / "lib" / f"python{components[0]}.{components[1]}" / "site-packages"
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise EnvironmentResolutionError("python_site_packages_unavailable", str(candidate)) from exc
    if not resolved.is_dir():
        raise EnvironmentResolutionError("python_site_packages_not_directory", str(resolved))
    return resolved


def _run_json_probe(argv: list[str], *, code: str, timeout: float = 30) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            argv,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            check=False,
            timeout=timeout,
            env={"PATH": "", "LC_ALL": "C", "PYTHONDONTWRITEBYTECODE": "1"},
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise EnvironmentResolutionError(code, f"{argv[0]}: {exc}") from exc
    if completed.returncode != 0:
        raise EnvironmentResolutionError(
            code,
            f"{argv[0]}: exit={completed.returncode}; stderr={completed.stderr[:400]!r}",
        )
    try:
        value = strict_json_loads(completed.stdout)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise EnvironmentResolutionError(code, f"invalid probe JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise EnvironmentResolutionError(code, "probe result is not an object")
    return value


_PYTHON_CAPABILITY_PROBE = r'''
import importlib.machinery, importlib.metadata, json, os, platform, sys
site_root = os.path.realpath(sys.argv[1])
required = json.loads(sys.argv[2])
distributions = []
for item in importlib.metadata.distributions(path=[site_root]):
    name = item.metadata.get("Name")
    if name:
        distributions.append({"name": name, "version": item.version})
modules = []
for module in required:
    top = module.split(".", 1)[0]
    spec = importlib.machinery.PathFinder.find_spec(top, [site_root])
    modules.append({"module": module, "origin": None if spec is None else spec.origin})
stdlib_roots = []
for raw in sys.path:
    if raw and os.path.isdir(raw):
        resolved = os.path.realpath(raw)
        if resolved not in stdlib_roots:
            stdlib_roots.append(resolved)
print(json.dumps({
    "reported_executable": sys.executable,
    "sys_prefix": sys.prefix,
    "sys_base_prefix": sys.base_prefix,
    "implementation": platform.python_implementation(),
    "python_version": platform.python_version(),
    "stdlib_roots": stdlib_roots,
    "site_root": site_root,
    "distributions": distributions,
    "required_modules": modules,
}, sort_keys=True, allow_nan=False))
'''


def _python_runtime_binding(
    invocation: Path,
    version: str,
    capability: Mapping[str, Any],
    repository_root: Path,
) -> dict[str, Any]:
    site_root = _python_site_path(invocation, version)
    probe = _run_json_probe(
        [
            str(invocation),
            "-I",
            "-S",
            "-c",
            _PYTHON_CAPABILITY_PROBE,
            str(site_root),
            json.dumps(
                list(capability["required_modules"]), allow_nan=False
            ),
        ],
        code="python_capability_probe_failed",
    )
    distributions = [
        {
            "name": _normalize_distribution_name(str(item["name"])),
            "version": str(item["version"]),
        }
        for item in probe["distributions"]
    ]
    counts = Counter(item["name"] for item in distributions)
    duplicates = sorted(name for name, count in counts.items() if count > 1)
    if duplicates:
        raise EnvironmentResolutionError("duplicate_distribution_name", repr(duplicates))
    distributions.sort(key=lambda item: (item["name"], item["version"]))
    module_observations: list[dict[str, Any]] = []
    expected_modules = list(capability["required_modules"])
    raw_modules = list(probe["required_modules"])
    if [item.get("module") for item in raw_modules] != expected_modules:
        raise EnvironmentResolutionError("required_module_probe_mismatch", repr(raw_modules))
    for item in raw_modules:
        origin = item.get("origin")
        if not isinstance(origin, str):
            raise EnvironmentResolutionError("required_module_unavailable", str(item.get("module")))
        origin_path = Path(origin).resolve(strict=True)
        try:
            origin_path.relative_to(site_root)
        except ValueError as exc:
            raise EnvironmentResolutionError(
                "required_module_origin_outside_dependency_root", origin
            ) from exc
        module_observations.append(
            {"module": str(item["module"]), "available": True}
        )
    raw_stdlib = [Path(item).resolve(strict=True) for item in probe["stdlib_roots"]]
    # The containing stdlib root already includes lib-dynload; retain a closed,
    # non-overlapping denominator and add the venv site root separately.
    stdlib_roots = [
        candidate
        for candidate in raw_stdlib
        if not any(
            candidate != other and candidate.is_relative_to(other)
            for other in raw_stdlib
        )
    ]
    import_roots: list[dict[str, Any]] = []
    for candidate in stdlib_roots:
        count, digest = _directory_manifest(candidate)
        import_roots.append(
            {
                "root_kind": "stdlib",
                "path": str(candidate),
                "file_count": count,
                "manifest_digest": digest,
            }
        )
    site_count, site_digest = _directory_manifest(site_root)
    import_roots.append(
        {
            "root_kind": "site_packages",
            "path": str(site_root),
            "file_count": site_count,
            "manifest_digest": site_digest,
        }
    )
    import_roots.sort(key=lambda item: (item["root_kind"], item["path"]))
    pyvenv_path = invocation.parent.parent / "pyvenv.cfg"
    pyvenv = _lock_binding(
        repository_root,
        pyvenv_path.resolve(strict=True).relative_to(repository_root).as_posix(),
    )
    return {
        "reported_executable": str(probe["reported_executable"]),
        "environment_root": str(invocation.parent.parent.resolve(strict=True)),
        "sys_prefix": str(probe["sys_prefix"]),
        "sys_base_prefix": str(probe["sys_base_prefix"]),
        "implementation": str(probe["implementation"]),
        "python_version": str(probe["python_version"]),
        "pyvenv_config": pyvenv,
        "distributions": distributions,
        "distributions_digest": canonical_digest(distributions),
        "required_modules": module_observations,
        "dependency_import_roots": import_roots,
    }


def _observe_version(invocation: Path, probe_kind: str) -> str:
    if probe_kind == "python":
        result = _run_json_probe(
            [
                str(invocation),
                "-I",
                "-S",
                "-c",
                (
                    "import json,platform; "
                    "print(json.dumps({'version': platform.python_version()}, "
                    "allow_nan=False))"
                ),
            ],
            code="tool_version_probe_failed",
        )
        return str(result["version"])
    if probe_kind == "python_script_header":
        try:
            prefix = invocation.read_bytes()[:16384]
        except OSError as exc:
            raise EnvironmentResolutionError("tool_version_probe_failed", str(invocation)) from exc
        match = _RUNNER_VERSION_PATTERN.search(prefix)
        if match is None:
            raise EnvironmentResolutionError("tool_version_unparseable", str(invocation))
        return match.group(1).decode("ascii")
    if probe_kind == "platform_release":
        return platform.release()
    raise EnvironmentResolutionError("unsupported_version_probe", probe_kind)


def render_dependency_lock_verifier_v1(
    *,
    invocation: Path,
    python_invocation: Path,
    project_root: Path,
    candidate_source: str,
    selected_extras: Sequence[str],
) -> dict[str, Any]:
    """Render the closed ``uv`` version and lock-check invocations.

    The candidate preparer is a stand-alone root bootstrap and deliberately
    cannot import subject-package code before the snapshot is trusted.  This
    pure renderer therefore preserves the same versioned argument/environment
    contract on the repository-side pre/fresh-observation path without making
    that unsafe dependency reversal.
    """

    for path, code in (
        (invocation, "dependency_lock_verifier_path_not_absolute"),
        (python_invocation, "dependency_lock_python_path_not_absolute"),
        (project_root, "dependency_lock_project_root_not_absolute"),
    ):
        if not path.is_absolute():
            raise EnvironmentResolutionError(code, str(path))
    if candidate_source == "repository_relative":
        effective_path = ""
    elif candidate_source == "platform_install_name":
        # Derive the only search root from the adopted invocation location.
        # Do not admit parent PATH or unrelated system directories.
        effective_path = str(invocation.parent)
    else:
        raise EnvironmentResolutionError(
            "dependency_lock_verifier_candidate_source_invalid",
            candidate_source,
        )
    extras = [str(item) for item in selected_extras]
    if any(
        re.fullmatch(r"[a-z0-9][a-z0-9-]*", extra) is None
        for extra in extras
    ):
        raise EnvironmentResolutionError(
            "dependency_lock_verifier_extra_invalid", repr(extras)
        )
    environment = {
        "LC_ALL": "C",
        "NO_COLOR": "1",
        "PATH": effective_path,
        "PYTHONDONTWRITEBYTECODE": "1",
        "UV_NO_PROGRESS": "1",
        "UV_OFFLINE": "1",
        "UV_PYTHON_DOWNLOADS": "never",
    }
    lock_argv = [
        str(invocation),
        *_UV_LOCK_CHECK_BASE_ARGUMENTS,
        str(python_invocation),
    ]
    for extra in extras:
        lock_argv.extend(["--extra", extra])
    return {
        "verification_mode": DEPENDENCY_LOCK_VERIFICATION_MODE,
        "version_probe": {
            "argv": [str(invocation), "--version"],
            "environment": dict(environment),
        },
        "lock_check": {
            "cwd": str(project_root),
            "argv": lock_argv,
            "environment": dict(environment),
        },
    }


def _verify_locked_environment_match_v1(
    contract: Mapping[str, Any],
    *,
    python_invocation: Path,
    lock_bindings: Sequence[Mapping[str, Any]],
    repository_root: Path,
) -> dict[str, Any]:
    candidate_source = contract.get("candidate_source")
    if (
        contract.get("install_name") == "homebrew.uv"
        and candidate_source == "platform_install_name"
        and contract.get("candidate_locator") == "homebrew.uv"
    ):
        invocation = Path("/opt/homebrew/bin/uv")
    elif (
        contract.get("install_name") == "snapshot.uv"
        and candidate_source == "repository_relative"
    ):
        invocation = _inside_repository(
            repository_root.resolve(strict=True),
            str(contract.get("candidate_locator", "")),
            code="dependency_lock_verifier_locator_invalid",
        )
    else:
        raise EnvironmentResolutionError(
            "dependency_lock_verifier_install_name_unknown",
            str(contract.get("install_name")),
        )
    try:
        resolved = invocation.resolve(strict=True)
    except OSError as exc:
        raise EnvironmentResolutionError(
            "dependency_lock_verifier_unavailable", str(invocation)
        ) from exc
    if not resolved.is_file() or not os.access(invocation, os.X_OK):
        raise EnvironmentResolutionError(
            "dependency_lock_verifier_unavailable", str(invocation)
        )
    selected_extras = [str(item) for item in contract["selected_extras"]]
    lock_parents = {
        Path(str(item["resolved_path"])).resolve(strict=True).parent
        for item in lock_bindings
        if Path(str(item["path"])).name in {"pyproject.toml", "uv.lock"}
    }
    if len(lock_parents) != 1:
        raise EnvironmentResolutionError(
            "dependency_lock_project_root_not_unique", repr(sorted(map(str, lock_parents)))
        )
    project_root = next(iter(lock_parents))
    try:
        project_root.relative_to(repository_root.resolve(strict=True))
    except ValueError as exc:
        raise EnvironmentResolutionError(
            "dependency_lock_project_root_outside_repository", str(project_root)
        ) from exc
    execution = render_dependency_lock_verifier_v1(
        invocation=resolved,
        python_invocation=python_invocation,
        project_root=project_root,
        candidate_source=str(candidate_source),
        selected_extras=selected_extras,
    )
    version_spec = execution["version_probe"]
    try:
        version_probe = subprocess.run(
            version_spec["argv"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
            env=version_spec["environment"],
            text=True,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise EnvironmentResolutionError(
            "dependency_lock_verifier_version_probe_failed", str(exc)
        ) from exc
    match = re.match(r"^uv\s+([0-9][0-9A-Za-z.+_-]*)\b", version_probe.stdout)
    if version_probe.returncode != 0 or match is None:
        raise EnvironmentResolutionError(
            "dependency_lock_verifier_version_probe_failed",
            version_probe.stdout + version_probe.stderr,
        )
    version = match.group(1)
    if not _version_matches(version, contract["version_constraint"]):
        raise EnvironmentResolutionError(
            "dependency_lock_verifier_version_mismatch", version
        )
    digest = file_digest(resolved)
    digest_contract = contract["digest_constraint"]
    if (
        digest_contract["policy"] == "exact"
        and digest != digest_contract["digest"]
    ):
        raise EnvironmentResolutionError(
            "dependency_lock_verifier_digest_mismatch", str(invocation)
        )
    lock_spec = execution["lock_check"]
    command = lock_spec["argv"]
    try:
        completed = subprocess.run(
            command,
            cwd=lock_spec["cwd"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=120,
            env=lock_spec["environment"],
            text=True,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise EnvironmentResolutionError(
            "dependency_lock_environment_check_failed", str(exc)
        ) from exc
    output = completed.stdout + completed.stderr
    count_match = re.search(r"Checked\s+([1-9][0-9]*)\s+packages\b", output)
    if (
        completed.returncode != 0
        or count_match is None
        or "Would make no changes" not in output
    ):
        raise EnvironmentResolutionError(
            "dependency_lock_environment_mismatch", output.strip()
        )
    result: dict[str, Any] = {
        "verification_mode": execution["verification_mode"],
        "tool_id": "uv.vnext",
        "invocation_path": str(invocation),
        "resolved_path": str(resolved),
        "version": version,
        "file_digest": digest,
        "selected_extras": selected_extras,
        "command": command,
        "effective_environment": lock_spec["environment"],
        "checked_package_count": int(count_match.group(1)),
        "match_status": "exact_no_changes",
    }
    result["result_digest"] = canonical_digest(result)
    return result


def _observe_tool_v1(
    requirement: Mapping[str, Any],
    *,
    repository_root: Path,
    observed_platform: Mapping[str, str],
) -> dict[str, Any]:
    locator = str(requirement["candidate_locator"])
    if requirement["candidate_source"] == "platform_install_name":
        if locator != "macos.sandbox-exec":
            raise EnvironmentResolutionError("platform_install_name_unknown", locator)
        invocation = Path("/usr/bin/sandbox-exec")
        try:
            resolved = invocation.resolve(strict=True)
        except OSError as exc:
            raise EnvironmentResolutionError("containment_launcher_unavailable", str(invocation)) from exc
    else:
        invocation, resolved = _repository_invocation_path(repository_root, locator)
    if requirement["logical_role"] in {"python_interpreter", "containment_launcher"} and not os.access(invocation, os.X_OK):
        raise EnvironmentResolutionError("tool_candidate_not_executable", str(invocation))
    resolved_digest = file_digest(resolved)
    version = _observe_version(invocation, str(requirement["version_probe"]))
    platform_match = _platform_matches(
        observed_platform, requirement["supported_platforms"]
    )
    version_match = _version_matches(version, requirement["version_constraint"])
    digest_contract = requirement["digest_constraint"]
    digest_match = digest_contract["policy"] == "adopted_exact" or resolved_digest == digest_contract.get("digest")
    if not platform_match:
        raise EnvironmentResolutionError("unsupported_tool_platform", str(requirement["tool_id"]))
    if not version_match:
        raise EnvironmentResolutionError(
            "tool_version_constraint_mismatch", f"{requirement['tool_id']}: {version}"
        )
    if not digest_match:
        raise EnvironmentResolutionError("tool_digest_constraint_mismatch", str(requirement["tool_id"]))
    capability_contract = requirement["capability_contract"]
    locks = [
        _lock_binding(repository_root, str(path))
        for path in capability_contract["lock_paths"]
    ]
    locks.sort(key=lambda item: str(item["path"]))
    containment_runtime: dict[str, Any] | None = None
    if capability_contract["kind"] == "python_environment":
        python_runtime: dict[str, Any] | None = _python_runtime_binding(
            invocation, version, capability_contract, repository_root
        )
        bootstrap_runtime: dict[str, Any] | None = None
    elif capability_contract["kind"] == "python_bootstrap":
        python_runtime = None
        bootstrap_runtime = {
            "interpreter_tool_id": "python.vnext",
            "startup_flags": ["-I", "-S"],
            "containment_before_external_import": True,
        }
    else:
        python_runtime = None
        bootstrap_runtime = None
        containment_runtime = {
            "provider_id": "macos.sandbox-exec",
            "install_name": "/usr/bin/sandbox-exec",
            "outer_policy": "deny_file_write_fork_and_non_python_exec_before_runner",
            "inner_protocol": CONTAINMENT_PROTOCOL,
        }
    capability_binding: dict[str, Any] = {
        "kind": str(capability_contract["kind"]),
        "python_runtime": python_runtime,
        "bootstrap_runtime": bootstrap_runtime,
        "containment_runtime": containment_runtime,
        "lock_bindings": locks,
        "lock_set_digest": canonical_digest(locks),
    }
    capability_binding["binding_digest"] = canonical_digest(capability_binding)
    return {
        "tool_id": str(requirement["tool_id"]),
        "logical_role": str(requirement["logical_role"]),
        "candidate_source": str(requirement["candidate_source"]),
        "candidate_locator": locator,
        "invocation_path": str(invocation),
        "invocation_identity": _invocation_identity(invocation, resolved, resolved_digest),
        "resolved_path": str(resolved),
        "version": version,
        "version_probe": str(requirement["version_probe"]),
        "file_digest": resolved_digest,
        "capability_binding": capability_binding,
        "constraint_evaluation": {
            "version_matches": True,
            "digest_matches": True,
            "platform_matches": True,
            "capability_matches": True,
        },
    }


def _effective_path(resolved_tools: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    directories: list[str] = []
    source_ids: dict[str, list[str]] = {}
    for tool in resolved_tools:
        invocation = Path(str(tool["invocation_path"]))
        if not invocation.is_absolute():
            raise EnvironmentResolutionError("invocation_path_not_absolute", str(invocation))
        directory = str(invocation.parent)
        if directory not in source_ids:
            directories.append(directory)
            source_ids[directory] = []
        source_ids[directory].append(str(tool["tool_id"]))
    entries = [
        {"directory": item, "source_tool_ids": sorted(source_ids[item])}
        for item in directories
    ]
    rendered = os.pathsep.join(directories)
    return {
        "policy": "managed_minimal_from_adopted_invocation_paths",
        "entries": entries,
        "rendered_value": rendered,
        "content_digest": _sha256_bytes(rendered.encode("utf-8")),
    }


def _parse_trace(raw: bytes) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_number, raw_line in enumerate(raw.splitlines(), 1):
        try:
            value = strict_json_loads(raw_line)
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise EnvironmentResolutionError(
                "containment_trace_invalid", f"line {line_number}: {exc}"
            ) from exc
        if not isinstance(value, dict):
            raise EnvironmentResolutionError("containment_trace_invalid", f"line {line_number}")
        records.append(value)
    if not records or [item.get("sequence") for item in records] != list(range(1, len(records) + 1)):
        raise EnvironmentResolutionError("containment_trace_sequence_invalid", repr(records))
    if any(item.get("trace_protocol") != TRACE_PROTOCOL for item in records):
        raise EnvironmentResolutionError("containment_trace_protocol_mismatch", repr(records))
    return records


def _probe_containment(
    launcher_tool: Mapping[str, Any],
    python_tool: Mapping[str, Any],
    runner_tool: Mapping[str, Any],
    *,
    evidence_id: str,
    evidence_locator: str,
    trace_locator: str,
    observed_platform: Mapping[str, str],
) -> tuple[dict[str, Any], bytes]:
    read_fd, write_fd = os.pipe()
    argv = [
        str(launcher_tool["invocation_path"]),
        "-p",
        outer_sandbox_profile(str(python_tool["resolved_path"])),
        str(python_tool["resolved_path"]),
        "-I",
        "-S",
        str(runner_tool["invocation_path"]),
        "--probe-containment",
    ]
    environment = {
        "PATH": os.pathsep.join(
            [
                str(Path(str(tool["invocation_path"])).parent)
                for tool in (launcher_tool, python_tool, runner_tool)
            ]
        ),
        "LC_ALL": "C",
        "PYTHONDONTWRITEBYTECODE": "1",
        TRACE_FD_ENV: str(write_fd),
    }
    probe_binding = canonical_digest(
        {
            "probe": "u10_containment_capability",
            "launcher": launcher_tool["file_digest"],
            "python": python_tool["file_digest"],
            "runner": runner_tool["file_digest"],
        }
    )["value"]
    environment[EXECUTION_NONCE_ENV] = probe_binding
    environment[COMMAND_DIGEST_ENV] = probe_binding
    environment[SUBJECT_MANIFEST_DIGEST_ENV] = probe_binding
    try:
        try:
            completed = subprocess.run(
                argv,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=30,
                env=environment,
                pass_fds=(write_fd,),
            )
        finally:
            os.close(write_fd)
        trace_bytes = b""
        while block := os.read(read_fd, 65536):
            trace_bytes += block
    except (OSError, subprocess.SubprocessError) as exc:
        raise EnvironmentResolutionError("containment_probe_failed", str(exc)) from exc
    finally:
        os.close(read_fd)
    records = _parse_trace(trace_bytes)
    activation = [item for item in records if item.get("event") == "containment_activated"]
    completion = [
        item for item in records if item.get("event") == "containment_probe_completed"
    ]
    if (
        completed.returncode != 0
        or len(activation) != 1
        or len(completion) != 1
        or completion[0].get("enforcement_status") != "effective"
        or completion[0].get("executed_child_count") != 0
        or int(completion[0].get("process_creation_attempt_count", 0)) < 2
    ):
        raise EnvironmentResolutionError(
            "containment_probe_not_effective",
            f"exit={completed.returncode}; records={records!r}; stderr={completed.stderr[:400]!r}",
        )
    trace_ref = {
        "record_id": f"{evidence_id}.trace",
        "locator": trace_locator,
        "content_digest": _sha256_bytes(trace_bytes),
    }
    evidence: dict[str, Any] = {
        "schema_version": CONTAINMENT_EVIDENCE_VERSION,
        "evidence_id": evidence_id,
        "protocol": CONTAINMENT_PROTOCOL,
        "platform": dict(observed_platform),
        "launcher_invocation_path": str(launcher_tool["invocation_path"]),
        "launcher_resolved_path": str(launcher_tool["resolved_path"]),
        "launcher_file_digest": launcher_tool["file_digest"],
        "outer_policy": "deny_file_write_fork_and_non_python_exec_before_runner",
        "runner_invocation_path": str(runner_tool["invocation_path"]),
        "runner_resolved_path": str(runner_tool["resolved_path"]),
        "runner_file_digest": runner_tool["file_digest"],
        "probe_command_digest": canonical_digest(argv),
        "activation_status": "effective",
        "trace_status": "complete_no_children",
        "process_creation_attempt_count": int(
            completion[0]["process_creation_attempt_count"]
        ),
        "executed_child_count": 0,
        "trace_ref": trace_ref,
        "trace_digest": canonical_digest(records),
        "formal_authority": "none",
        "positive_assurance_allowed": False,
        "limitations": [
            "The macOS sandbox API is deprecated and this profile is restricted to the exact observed OS release and machine.",
            "The probe establishes no-process-creation behavior for this bootstrap path, not general application correctness.",
            "Kernel, dyld shared-cache, clone/spoof, and natural-person trust remain outside this evidence.",
        ],
    }
    evidence["evidence_digest"] = canonical_digest(evidence)
    validate_containment_probe_evidence(evidence)
    if evidence["trace_ref"]["locator"] != trace_locator:
        raise EnvironmentResolutionError("containment_trace_locator_mismatch", trace_locator)
    if _artifact_ref(evidence_id, evidence_locator, evidence)["content_digest"] != artifact_content_digest(evidence):
        raise AssertionError("unreachable artifact digest mismatch")
    return evidence, trace_bytes


def validate_containment_probe_evidence(evidence: Mapping[str, Any]) -> None:
    _validate_schema(
        evidence, _CONTAINMENT_EVIDENCE_SCHEMA, "containment_probe_evidence"
    )
    _sealed_digest(
        evidence,
        "evidence_digest",
        "containment_probe_evidence_digest_mismatch",
    )


def build_environment_candidate_material(
    verification_profile: Mapping[str, Any],
    *,
    repository_root: Path,
    environment_profile_id: str,
    environment_profile_version: str,
    host_evidence_locator: str,
    containment_evidence_locator: str,
    containment_trace_locator: str,
) -> dict[str, Any]:
    """Build candidate material only; this grants no execution permission."""

    validate_verification_profile_v4(verification_profile)
    root = repository_root.resolve(strict=True)
    validate_profile_closed_test_manifests_v1(
        verification_profile, repository_root=root
    )
    observed_platform = platform_observation()
    host_evidence = capture_host_identity_evidence()
    host_ref = host_identity_ref(host_evidence, locator=host_evidence_locator)
    tools = [
        _observe_tool_v1(
            requirement,
            repository_root=root,
            observed_platform=observed_platform,
        )
        for requirement in verification_profile["environment_contract"]["tool_requirements"]
    ]
    tools.sort(key=lambda item: str(item["tool_id"]))
    by_id = {str(item["tool_id"]): item for item in tools}
    if set(by_id) != {
        "containment_launcher.vnext",
        "python.vnext",
        "test_runner.vnext",
    }:
        raise EnvironmentResolutionError("qualified_tool_denominator_mismatch", repr(sorted(by_id)))
    python_binding = by_id["python.vnext"]["capability_binding"]
    python_runtime = python_binding["python_runtime"]
    if not isinstance(python_runtime, dict):
        raise EnvironmentResolutionError(
            "python_runtime_binding_missing", "python.vnext"
        )
    python_runtime["lock_environment_match"] = _verify_locked_environment_match_v1(
        verification_profile["environment_contract"]["dependency_lock_verifier"],
        python_invocation=Path(str(by_id["python.vnext"]["invocation_path"])),
        lock_bindings=python_binding["lock_bindings"],
        repository_root=root,
    )
    python_binding.pop("binding_digest", None)
    python_binding["binding_digest"] = canonical_digest(python_binding)
    containment_evidence, containment_trace = _probe_containment(
        by_id["containment_launcher.vnext"],
        by_id["python.vnext"],
        by_id["test_runner.vnext"],
        evidence_id="evidence.containment.local.u10",
        evidence_locator=containment_evidence_locator,
        trace_locator=containment_trace_locator,
        observed_platform=observed_platform,
    )
    containment_ref = _artifact_ref(
        str(containment_evidence["evidence_id"]),
        containment_evidence_locator,
        containment_evidence,
    )
    containment_material = {
        "protocol": CONTAINMENT_PROTOCOL,
        "platform_scope": observed_platform,
        "process_creation_policy": "prohibited_after_runner_start",
        "qualification_status": "candidate_observed",
        "probe_evidence_ref": containment_ref,
    }
    containment_material["capability_digest"] = canonical_digest(
        containment_material
    )
    candidate: dict[str, Any] = {
        "schema_version": ENVIRONMENT_VERSION,
        "environment_profile_id": environment_profile_id,
        "environment_profile_version": environment_profile_version,
        "lifecycle_state": "candidate",
        "formal_authority": "none",
        "positive_assurance_allowed": False,
        "verification_profile_ref": verification_profile_ref(verification_profile),
        "platform": observed_platform,
        "host_identity_ref": host_ref,
        "resolved_tools": tools,
        "effective_path": _effective_path(tools),
        "containment_capability": containment_material,
        "limitations": [
            "Candidate generation and schema validity do not constitute human adoption.",
            "The macOS sandbox API is deprecated; use on another OS release or machine requires requalification.",
            "U-4 principal identity, delegated authority, revocation, and external trust-root questions remain unresolved.",
            "Before/after hashing detects change but does not eliminate every observation-to-exec race without an immutable filesystem or stronger OS attestation.",
        ],
    }
    candidate["basis_digest"] = canonical_digest(candidate)
    validate_resolved_environment_profile_v1(
        candidate, verification_profile=verification_profile
    )
    return {
        "host_identity_evidence": host_evidence,
        "containment_probe_evidence": containment_evidence,
        "containment_trace_bytes": containment_trace,
        "resolved_environment_profile": candidate,
    }


def _validate_capability_binding(binding: Mapping[str, Any]) -> None:
    _sealed_digest(binding, "binding_digest", "capability_binding_digest_mismatch")
    locks = list(binding["lock_bindings"])
    if canonical_digest(locks) != binding["lock_set_digest"]:
        raise EnvironmentResolutionError("lock_set_digest_mismatch", repr(locks))
    runtime = binding["python_runtime"]
    if runtime is not None:
        distributions = list(runtime["distributions"])
        if distributions != sorted(
            distributions, key=lambda item: (str(item["name"]), str(item["version"]))
        ):
            raise EnvironmentResolutionError("distribution_order_invalid", repr(distributions))
        names = [str(item["name"]) for item in distributions]
        if len(names) != len(set(names)):
            raise EnvironmentResolutionError("duplicate_distribution_name", repr(names))
        if canonical_digest(distributions) != runtime["distributions_digest"]:
            raise EnvironmentResolutionError("distributions_digest_mismatch", repr(names))
        lock_match = dict(runtime["lock_environment_match"])
        observed_lock_match_digest = lock_match.pop("result_digest", None)
        if (
            observed_lock_match_digest is None
            or canonical_digest(lock_match) != observed_lock_match_digest
            or runtime["lock_environment_match"]["match_status"]
            != "exact_no_changes"
            or runtime["lock_environment_match"]["checked_package_count"] < 1
        ):
            raise EnvironmentResolutionError(
                "dependency_lock_environment_match_invalid", repr(names)
            )
        root_kinds = [str(item["root_kind"]) for item in runtime["dependency_import_roots"]]
        if root_kinds.count("site_packages") != 1 or "stdlib" not in root_kinds:
            raise EnvironmentResolutionError("dependency_import_root_denominator_mismatch", repr(root_kinds))


def validate_resolved_environment_profile_v1(
    profile: Mapping[str, Any],
    *,
    verification_profile: Mapping[str, Any] | None = None,
) -> None:
    _validate_schema(profile, _ENVIRONMENT_SCHEMA, "resolved_environment_profile_v1")
    _sealed_digest(profile, "basis_digest", "environment_basis_digest_mismatch")
    tools = list(profile["resolved_tools"])
    ids = [str(item["tool_id"]) for item in tools]
    if any(
        ids.count(expected) != 1
        for expected in (
            "containment_launcher.vnext",
            "python.vnext",
            "test_runner.vnext",
        )
    ):
        raise EnvironmentResolutionError("qualified_tool_denominator_mismatch", repr(ids))
    for tool in tools:
        invocation = Path(str(tool["invocation_path"]))
        resolved = Path(str(tool["resolved_path"]))
        if not invocation.is_absolute() or not resolved.is_absolute():
            raise EnvironmentResolutionError("tool_path_not_absolute", str(invocation))
        identity_material = {
            "invocation_path": str(invocation),
            "path_kind": tool["invocation_identity"]["path_kind"],
            "symlink_target": tool["invocation_identity"]["symlink_target"],
            "resolved_path": str(resolved),
            "resolved_file_digest": tool["file_digest"],
        }
        if canonical_digest(identity_material) != tool["invocation_identity"]["identity_digest"]:
            raise EnvironmentResolutionError("invocation_identity_digest_mismatch", str(tool["tool_id"]))
        if (
            tool["invocation_identity"]["path_kind"] == "regular"
            and tool["invocation_identity"]["symlink_target"] is not None
        ):
            raise EnvironmentResolutionError("regular_invocation_has_symlink_target", str(tool["tool_id"]))
        if (
            tool["invocation_identity"]["path_kind"] == "symlink"
            and tool["invocation_identity"]["symlink_target"] is None
        ):
            raise EnvironmentResolutionError("symlink_invocation_target_missing", str(tool["tool_id"]))
        _validate_capability_binding(tool["capability_binding"])
    if _effective_path(tools) != profile["effective_path"]:
        raise EnvironmentResolutionError("effective_path_derivation_mismatch", str(profile["environment_profile_id"]))
    containment = dict(profile["containment_capability"])
    observed_containment_digest = containment.pop("capability_digest")
    if canonical_digest(containment) != observed_containment_digest:
        raise EnvironmentResolutionError("containment_capability_digest_mismatch", str(profile["environment_profile_id"]))
    if profile["platform"]["system"] != "Darwin":
        raise EnvironmentResolutionError("containment_platform_not_darwin", repr(profile["platform"]))
    if verification_profile is not None:
        validate_verification_profile_v4(verification_profile)
        if verification_profile_ref(verification_profile) != profile["verification_profile_ref"]:
            raise EnvironmentResolutionError("verification_profile_ref_mismatch", str(profile["environment_profile_id"]))
        requirements = {
            str(item["tool_id"]): item
            for item in verification_profile["environment_contract"]["tool_requirements"]
        }
        for tool in tools:
            requirement = requirements[str(tool["tool_id"])]
            if (
                tool["logical_role"] != requirement["logical_role"]
                or tool["candidate_source"] != requirement["candidate_source"]
                or tool["candidate_locator"] != requirement["candidate_locator"]
                or tool["version_probe"] != requirement["version_probe"]
                or tool["capability_binding"]["kind"] != requirement["capability_contract"]["kind"]
                or [item["path"] for item in tool["capability_binding"]["lock_bindings"]]
                != sorted(str(item) for item in requirement["capability_contract"]["lock_paths"])
            ):
                raise EnvironmentResolutionError("tool_requirement_projection_mismatch", str(tool["tool_id"]))
            runtime = tool["capability_binding"]["python_runtime"]
            if runtime is not None and [item["module"] for item in runtime["required_modules"]] != list(requirement["capability_contract"]["required_modules"]):
                raise EnvironmentResolutionError("required_module_projection_mismatch", str(tool["tool_id"]))


def build_adoption_request_v1(
    candidate_profile: Mapping[str, Any],
    verification_profile: Mapping[str, Any],
    *,
    adoption_id: str,
    adoption_version: str,
    decision_owner_ref: Mapping[str, Any],
) -> dict[str, Any]:
    validate_resolved_environment_profile_v1(
        candidate_profile, verification_profile=verification_profile
    )
    record: dict[str, Any] = {
        "schema_version": ADOPTION_VERSION,
        "record_kind": "adoption_request",
        "adoption_id": adoption_id,
        "adoption_version": adoption_version,
        "human_decision": "pending",
        "recorded_at": None,
        "environment_profile_ref": environment_profile_ref(candidate_profile),
        "execution_scope_ref": verification_profile_ref(verification_profile),
        "decision_owner_ref": dict(decision_owner_ref),
        "decision_owner_authority_evidence_ref": None,
        "decision_evidence_ref": None,
        "trusted_entrypoint_ref": None,
        "formal_authority": "none",
        "positive_assurance_allowed": False,
        "limitations": [
            "This request is candidate decision material and is not human adoption.",
            "Environment adoption never grants engineering verdict, risk acceptance, or final acceptance authority.",
            "U-4 principal authenticity and revocation remain a separate governance dependency.",
        ],
    }
    record["adoption_digest"] = canonical_digest(record)
    validate_adoption_record_v1(record)
    return record


def validate_adoption_record_v1(record: Mapping[str, Any]) -> None:
    _validate_schema(record, _ADOPTION_SCHEMA, "environment_adoption_v1")
    _sealed_digest(record, "adoption_digest", "environment_adoption_digest_mismatch")
    if record["record_kind"] == "adoption_request" and record["human_decision"] != "pending":
        raise EnvironmentResolutionError("adoption_request_decision_invalid", str(record["adoption_id"]))
    if record["record_kind"] == "adoption_decision" and record["human_decision"] == "pending":
        raise EnvironmentResolutionError("adoption_decision_pending", str(record["adoption_id"]))


def implementation_ref(record_id: str, *, repository_root: Path) -> dict[str, Any]:
    root = repository_root.resolve(strict=True)
    path = Path(__file__).resolve(strict=True)
    try:
        locator = path.relative_to(root).as_posix()
    except ValueError as exc:
        raise EnvironmentResolutionError("implementation_outside_repository", str(path)) from exc
    return {
        "record_id": record_id,
        "locator": locator,
        "content_digest": file_digest(path),
    }


def repository_file_ref(
    record_id: str,
    locator: str,
    *,
    repository_root: Path,
) -> dict[str, Any]:
    root = repository_root.resolve(strict=True)
    path = _inside_repository(root, locator, code="implementation_ref_locator_invalid")
    return {
        "record_id": record_id,
        "locator": locator,
        "content_digest": file_digest(path),
    }


def contract_schema_refs(*, repository_root: Path) -> list[dict[str, Any]]:
    return [
        repository_file_ref(
            f"schema.env-path.{name}",
            f"vnext/validation/env-path-contracts/{name}",
            repository_root=repository_root,
        )
        for name in QUALIFIED_ENVIRONMENT_CONTRACT_SCHEMA_NAMES
    ]


def build_candidate_eligibility_source(
    adoption_request: Mapping[str, Any],
    *,
    repository_root: Path,
    source_id: str,
    source_version: str,
) -> dict[str, Any]:
    validate_adoption_record_v1(adoption_request)
    if adoption_request["record_kind"] != "adoption_request":
        raise EnvironmentResolutionError("candidate_source_requires_adoption_request", source_id)
    source: dict[str, Any] = {
        "schema_version": ELIGIBILITY_SOURCE_VERSION,
        "source_id": source_id,
        "source_version": source_version,
        "lifecycle_state": "candidate",
        "adoption_record": dict(adoption_request),
        "host_observer_ref": implementation_ref(
            HOST_OBSERVER_RECORD_ID, repository_root=repository_root
        ),
        "resolver_implementation_ref": implementation_ref(
            ELIGIBILITY_RESOLVER_RECORD_ID, repository_root=repository_root
        ),
        "execution_harness_ref": repository_file_ref(
            EXECUTION_HARNESS_RECORD_ID,
            "vnext/src/semantic_guard_vnext/governed_environment_execution.py",
            repository_root=repository_root,
        ),
        "contract_schema_refs": contract_schema_refs(
            repository_root=repository_root
        ),
        "source_provenance": {
            "evidence_source": "locally generated U-10 candidate; human adoption not yet recorded",
            "acquisition_method": "local_candidate_generation",
            "inference_status": "pending_human_decision",
            "decision_owner": "human",
            "pending_decision": True,
        },
        "formal_authority": "none",
        "positive_assurance_allowed": False,
        "limitations": [
            "Candidate source state cannot authorize environment use.",
            "Only an independently pinned adopted source with an accepted exact-scope decision can be resolved.",
            "Shape and digest validation do not prove principal identity or delegated authority.",
        ],
    }
    source["source_digest"] = canonical_digest(source)
    validate_eligibility_source(source)
    return source


def validate_eligibility_source(source: Mapping[str, Any]) -> None:
    _validate_schema(source, _ELIGIBILITY_SOURCE_SCHEMA, "eligibility_source_v1")
    _sealed_digest(source, "source_digest", "eligibility_source_digest_mismatch")
    adoption = source.get("adoption_record")
    if not isinstance(adoption, Mapping):
        raise EnvironmentResolutionError("eligibility_source_adoption_missing", str(source.get("source_id")))
    validate_adoption_record_v1(adoption)
    if source["lifecycle_state"] == "adopted":
        if adoption["record_kind"] != "adoption_decision" or adoption["human_decision"] != "accept":
            raise EnvironmentResolutionError("adopted_source_without_accept_decision", str(source["source_id"]))
    elif adoption["human_decision"] == "accept":
        raise EnvironmentResolutionError("nonadopted_source_contains_accept_decision", str(source["source_id"]))


def validate_snapshot_environment_adoption_v1(
    adoption: Mapping[str, Any],
) -> None:
    """Validate only the external decision record's closed structure and seal.

    Root-held artifact authenticity and protected-path bindings are verified by
    the U-10 broker before this record reaches the non-root resolver.
    """

    _validate_schema(
        adoption,
        _SNAPSHOT_ENVIRONMENT_ADOPTION_SCHEMA,
        "snapshot_environment_adoption_v1",
    )
    _sealed_digest(
        adoption,
        "adoption_digest",
        "snapshot_environment_adoption_digest_mismatch",
    )
    if (
        adoption["record_kind"] != "snapshot_environment_adoption_decision"
        or adoption["human_decision"] != "accept"
        or adoption["decision_owner"] != "human"
        or adoption["authorized_operation"]
        != "adopt_exact_projected_snapshot_environment"
        or adoption["decision_effect_scope"]
        != "u10_exact_projected_snapshot_environment_use_gate_only"
        or adoption["formal_authority"] != "none"
        or adoption["positive_assurance_allowed"] is not False
    ):
        raise EnvironmentResolutionError(
            "snapshot_environment_adoption_authority_invalid",
            str(adoption.get("adoption_id")),
        )


def _load_json_artifact(path: Path) -> dict[str, Any]:
    try:
        value = strict_json_loads(path.read_bytes())
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise EnvironmentResolutionError("artifact_load_failed", f"{path}: {exc}") from exc
    if not isinstance(value, dict):
        raise EnvironmentResolutionError("artifact_root_not_object", str(path))
    return value


def _verify_repository_ref(reference: Mapping[str, Any], *, repository_root: Path) -> Path:
    locator = str(reference.get("locator", ""))
    resolved = _inside_repository(repository_root, locator, code="artifact_ref_locator_invalid")
    if file_digest(resolved) != reference.get("content_digest"):
        raise EnvironmentResolutionError("artifact_ref_digest_mismatch", locator)
    return resolved


def _verify_snapshot_artifact_ref(
    reference: Mapping[str, Any], *, repository_root: Path
) -> Path:
    locator = reference.get("locator")
    if not isinstance(locator, str):
        raise EnvironmentResolutionError("snapshot_artifact_ref_locator_invalid", repr(locator))
    path = Path(locator)
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(repository_root)
    except (OSError, ValueError) as exc:
        raise EnvironmentResolutionError(
            "snapshot_artifact_ref_outside_repository", locator
        ) from exc
    if file_digest(resolved) != reference.get("artifact_digest"):
        raise EnvironmentResolutionError("snapshot_artifact_ref_digest_mismatch", locator)
    return resolved


def _unresolved(*reason_codes: str) -> dict[str, Any]:
    return {
        "schema_version": "semantic-guard-environment-eligibility-result/v1",
        "resolution_status": "unresolved",
        "reason_codes": sorted(set(reason_codes)),
        "environment_use_allowed": False,
        "formal_authority": "none",
        "positive_assurance_allowed": False,
    }


class EnvironmentEligibilityService:
    """Composition-root resolver; invocation callers cannot supply trust claims."""

    def __init__(
        self,
        source: Mapping[str, Any],
        *,
        expected_source_digest: Mapping[str, Any],
        repository_root: Path,
        external_adoption: Mapping[str, Any] | None = None,
    ) -> None:
        self._repository_root = repository_root.resolve(strict=True)
        self._source = _json_clone(source)
        self._external_adoption = (
            None
            if external_adoption is None
            else _json_clone(external_adoption)
        )
        validate_eligibility_source(self._source)
        if self._external_adoption is not None:
            validate_snapshot_environment_adoption_v1(self._external_adoption)
        if self._source["source_digest"] != dict(expected_source_digest):
            raise EnvironmentResolutionError("eligibility_source_external_pin_mismatch", str(self._source["source_id"]))
        for field, expected_id in (
            ("host_observer_ref", HOST_OBSERVER_RECORD_ID),
            ("resolver_implementation_ref", ELIGIBILITY_RESOLVER_RECORD_ID),
            ("execution_harness_ref", EXECUTION_HARNESS_RECORD_ID),
        ):
            reference = self._source[field]
            if reference["record_id"] != expected_id:
                raise EnvironmentResolutionError("eligibility_implementation_id_mismatch", str(reference["record_id"]))
            _verify_repository_ref(reference, repository_root=self._repository_root)
        expected_schema_refs = contract_schema_refs(
            repository_root=self._repository_root
        )
        if self._source["contract_schema_refs"] != expected_schema_refs:
            raise EnvironmentResolutionError(
                "eligibility_contract_schema_set_mismatch",
                str(self._source["source_id"]),
            )
        for reference in self._source["contract_schema_refs"]:
            _verify_repository_ref(
                reference, repository_root=self._repository_root
            )

    @property
    def repository_root(self) -> Path:
        return self._repository_root

    @property
    def source(self) -> dict[str, Any]:
        return _json_clone(self._source)

    @property
    def external_adoption(self) -> dict[str, Any] | None:
        if self._external_adoption is None:
            return None
        return _json_clone(self._external_adoption)

    @classmethod
    def from_file(
        cls,
        source_path: Path,
        *,
        expected_source_digest: Mapping[str, Any],
        repository_root: Path,
        external_adoption: Mapping[str, Any] | None = None,
    ) -> "EnvironmentEligibilityService":
        root = repository_root.resolve(strict=True)
        source_resolved = source_path.resolve(strict=True)
        try:
            source_resolved.relative_to(root)
        except ValueError as exc:
            raise EnvironmentResolutionError("eligibility_source_outside_repository", str(source_path)) from exc
        return cls(
            _load_json_artifact(source_resolved),
            expected_source_digest=expected_source_digest,
            repository_root=root,
            external_adoption=external_adoption,
        )

    def resolve(
        self,
        candidate_profile: Mapping[str, Any],
        verification_profile: Mapping[str, Any],
    ) -> dict[str, Any]:
        try:
            validate_resolved_environment_profile_v1(
                candidate_profile, verification_profile=verification_profile
            )
            validate_verification_profile_v4(verification_profile)
        except EnvironmentResolutionError as exc:
            return _unresolved(exc.code)
        if self._external_adoption is None:
            return _unresolved("external_environment_adoption_required")
        adoption = self._external_adoption
        source_ref = adoption["eligibility_source_ref"]
        if (
            self._source["lifecycle_state"] != "candidate"
            or self._source["adoption_record"]["record_kind"] != "adoption_request"
            or self._source["adoption_record"]["human_decision"] != "pending"
            or source_ref["source_id"] != self._source["source_id"]
            or source_ref["source_version"] != self._source["source_version"]
            or source_ref["lifecycle_state"] != "candidate"
            or source_ref["source_digest"] != self._source["source_digest"]
        ):
            return _unresolved("external_environment_adoption_source_mismatch")
        environment_ref = adoption["environment_profile_ref"]
        if {
            "environment_profile_id": environment_ref["environment_profile_id"],
            "environment_profile_version": environment_ref[
                "environment_profile_version"
            ],
            "basis_digest": environment_ref["basis_digest"],
        } != environment_profile_ref(candidate_profile):
            return _unresolved("environment_adoption_basis_mismatch")
        profile_ref = adoption["verification_profile_ref"]
        if {
            "profile_id": profile_ref["profile_id"],
            "profile_version": profile_ref["profile_version"],
            "content_digest": profile_ref["content_digest"],
        } != verification_profile_ref(verification_profile):
            return _unresolved("environment_adoption_execution_scope_mismatch")
        if (
            adoption["decision_owner_ref"]
            != self._source["adoption_record"]["decision_owner_ref"]
        ):
            return _unresolved("environment_adoption_decision_owner_mismatch")
        try:
            source_path = _verify_snapshot_artifact_ref(
                source_ref["snapshot_artifact_ref"],
                repository_root=self._repository_root,
            )
            profile_path = _verify_snapshot_artifact_ref(
                profile_ref["snapshot_artifact_ref"],
                repository_root=self._repository_root,
            )
            environment_path = _verify_snapshot_artifact_ref(
                environment_ref["snapshot_artifact_ref"],
                repository_root=self._repository_root,
            )
            host_adoption_ref = adoption["host_identity_evidence_ref"]
            host_path_from_adoption = _verify_snapshot_artifact_ref(
                host_adoption_ref["snapshot_artifact_ref"],
                repository_root=self._repository_root,
            )
            if (
                _load_json_artifact(source_path) != self._source
                or _load_json_artifact(profile_path) != dict(verification_profile)
                or _load_json_artifact(environment_path) != dict(candidate_profile)
                or source_ref["snapshot_artifact_ref"]["semantic_digest"]
                != self._source["source_digest"]
                or profile_ref["snapshot_artifact_ref"]["semantic_digest"]
                != verification_profile_ref(verification_profile)["content_digest"]
                or environment_ref["snapshot_artifact_ref"]["semantic_digest"]
                != candidate_profile["basis_digest"]
                or host_adoption_ref["identity_digest"]
                != candidate_profile["host_identity_ref"]["identity_digest"]
                or host_adoption_ref["snapshot_artifact_ref"]["artifact_digest"]
                != candidate_profile["host_identity_ref"]["evidence_ref"][
                    "content_digest"
                ]
            ):
                return _unresolved("external_environment_adoption_artifact_mismatch")
        except EnvironmentResolutionError as exc:
            return _unresolved(exc.code)
        try:
            host_path = _verify_repository_ref(
                candidate_profile["host_identity_ref"]["evidence_ref"],
                repository_root=self._repository_root,
            )
            stored_host = _load_json_artifact(host_path)
            if host_path != host_path_from_adoption:
                return _unresolved("external_environment_adoption_host_mismatch")
            validate_host_identity_evidence(stored_host)
            fresh_host = capture_host_identity_evidence(
                evidence_id=str(stored_host["evidence_id"])
            )
            fresh_host_ref = host_identity_ref(
                fresh_host,
                locator=str(candidate_profile["host_identity_ref"]["evidence_ref"]["locator"]),
            )
            if fresh_host_ref != candidate_profile["host_identity_ref"]:
                return _unresolved("host_identity_requalification_required")
            if fresh_host["observed_platform"] != candidate_profile["platform"]:
                return _unresolved("platform_requalification_required")
            containment_path = _verify_repository_ref(
                candidate_profile["containment_capability"]["probe_evidence_ref"],
                repository_root=self._repository_root,
            )
            stored_containment = _load_json_artifact(containment_path)
            validate_containment_probe_evidence(stored_containment)
            _verify_repository_ref(
                stored_containment["trace_ref"], repository_root=self._repository_root
            )
            fresh_material = build_environment_candidate_material(
                verification_profile,
                repository_root=self._repository_root,
                environment_profile_id=str(candidate_profile["environment_profile_id"]),
                environment_profile_version=str(candidate_profile["environment_profile_version"]),
                host_evidence_locator=str(candidate_profile["host_identity_ref"]["evidence_ref"]["locator"]),
                containment_evidence_locator=str(candidate_profile["containment_capability"]["probe_evidence_ref"]["locator"]),
                containment_trace_locator=str(stored_containment["trace_ref"]["locator"]),
            )
        except EnvironmentResolutionError as exc:
            return _unresolved(exc.code)
        observed_candidate = fresh_material["resolved_environment_profile"]
        if observed_candidate != dict(candidate_profile):
            return _unresolved("environment_requalification_required")
        observation: dict[str, Any] = {
            "observation_kind": "fresh_exact_environment_reobservation/v1",
            "platform": observed_candidate["platform"],
            "host_identity_ref": observed_candidate["host_identity_ref"],
            "resolved_tools": observed_candidate["resolved_tools"],
            "effective_path": observed_candidate["effective_path"],
            "containment_capability": observed_candidate["containment_capability"],
        }
        observation["observation_digest"] = canonical_digest(observation)
        result: dict[str, Any] = {
            "schema_version": ELIGIBILITY_RESOLUTION_VERSION,
            "resolution_status": "eligible_scoped",
            "reason_codes": [],
            "environment_use_allowed": True,
            "permission_kind": "verification_process_launch",
            "environment_profile_ref": environment_profile_ref(candidate_profile),
            "execution_scope_ref": verification_profile_ref(verification_profile),
            "adoption_ref": {
                "adoption_id": adoption["adoption_id"],
                "adoption_version": adoption["adoption_version"],
                "adoption_digest": adoption["adoption_digest"],
            },
            "trust_source_ref": {
                "source_id": self._source["source_id"],
                "source_version": self._source["source_version"],
                "source_digest": self._source["source_digest"],
            },
            "host_resolution": {
                "expected_host_identity_ref": candidate_profile["host_identity_ref"],
                "observed_host_identity_ref": fresh_host_ref,
                "identity_match_status": "exact",
                "observer_ref": self._source["host_observer_ref"],
            },
            "current_observation": observation,
            "resolved_tools": candidate_profile["resolved_tools"],
            "effective_path": candidate_profile["effective_path"],
            "containment_requirement": {
                "protocol": CONTAINMENT_PROTOCOL,
                "process_creation_policy": "prohibited_after_runner_start",
            },
            "formal_authority": "none",
            "positive_assurance_allowed": False,
            "limitations": [
                "Eligibility authorizes only this exact verification-process launch scope.",
                "Eligibility is not an engineering verdict, risk acceptance, or final acceptance.",
                "U-4 principal authenticity and external revocation remain separately governed.",
                "The qualified containment mechanism is limited to the exact adopted macOS profile.",
            ],
        }
        result["resolution_digest"] = canonical_digest(result)
        validate_eligibility_resolution(
            result,
            candidate_profile=candidate_profile,
            verification_profile=verification_profile,
            source=self._source,
            external_adoption=adoption,
        )
        return result


def validate_eligibility_resolution(
    result: Mapping[str, Any],
    *,
    candidate_profile: Mapping[str, Any],
    verification_profile: Mapping[str, Any],
    source: Mapping[str, Any],
    external_adoption: Mapping[str, Any] | None = None,
) -> None:
    _validate_schema(result, _ELIGIBILITY_RESOLUTION_SCHEMA, "eligibility_resolution_v1")
    _sealed_digest(result, "resolution_digest", "eligibility_resolution_digest_mismatch")
    if external_adoption is None:
        raise EnvironmentResolutionError(
            "external_environment_adoption_required",
            str(result.get("resolution_status")),
        )
    validate_snapshot_environment_adoption_v1(external_adoption)
    if result["environment_profile_ref"] != environment_profile_ref(candidate_profile):
        raise EnvironmentResolutionError("eligibility_environment_ref_mismatch", str(result.get("resolution_status")))
    if result["execution_scope_ref"] != verification_profile_ref(verification_profile):
        raise EnvironmentResolutionError("eligibility_scope_ref_mismatch", str(result.get("resolution_status")))
    expected_adoption_ref = {
        "adoption_id": external_adoption["adoption_id"],
        "adoption_version": external_adoption["adoption_version"],
        "adoption_digest": external_adoption["adoption_digest"],
    }
    if result["adoption_ref"] != expected_adoption_ref:
        raise EnvironmentResolutionError("eligibility_adoption_ref_mismatch", str(result.get("resolution_status")))
    expected_source_ref = {
        "source_id": source["source_id"],
        "source_version": source["source_version"],
        "source_digest": source["source_digest"],
    }
    if result["trust_source_ref"] != expected_source_ref:
        raise EnvironmentResolutionError("eligibility_source_ref_mismatch", str(result.get("resolution_status")))
    host_resolution = result["host_resolution"]
    if (
        host_resolution["expected_host_identity_ref"]
        != candidate_profile["host_identity_ref"]
        or host_resolution["observed_host_identity_ref"]
        != candidate_profile["host_identity_ref"]
        or host_resolution["observer_ref"] != source["host_observer_ref"]
    ):
        raise EnvironmentResolutionError(
            "eligibility_host_resolution_projection_mismatch",
            str(result.get("resolution_status")),
        )
    if result["resolved_tools"] != candidate_profile["resolved_tools"] or result["effective_path"] != candidate_profile["effective_path"]:
        raise EnvironmentResolutionError("eligibility_observation_projection_mismatch", str(result.get("resolution_status")))
    observation = result["current_observation"]
    observation_material = dict(observation)
    observed_digest = observation_material.pop("observation_digest", None)
    if observed_digest is None or canonical_digest(observation_material) != observed_digest:
        raise EnvironmentResolutionError("eligibility_observation_digest_mismatch", str(result.get("resolution_status")))
    if (
        observation.get("resolved_tools") != candidate_profile["resolved_tools"]
        or observation.get("effective_path") != candidate_profile["effective_path"]
        or observation.get("host_identity_ref") != candidate_profile["host_identity_ref"]
        or observation.get("platform") != candidate_profile["platform"]
        or observation.get("containment_capability") != candidate_profile["containment_capability"]
    ):
        raise EnvironmentResolutionError("eligibility_current_observation_mismatch", str(result.get("resolution_status")))
