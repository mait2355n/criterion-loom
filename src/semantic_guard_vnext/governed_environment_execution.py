"""Scoped U-10 execution and receipt generation.

Only an ``EnvironmentEligibilityService`` can open this path.  The service
replays the exact adopted environment and full verification scope; an
invocation caller cannot supply adoption, host, or verifier callbacks.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import secrets
import signal
import subprocess
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from .environment_resolution import EnvironmentResolutionError, canonical_digest, file_digest
from .qualified_environment import (
    CONTAINMENT_PROTOCOL,
    ELIGIBILITY_RESOLUTION_VERSION,
    TRACE_FD_ENV,
    EnvironmentEligibilityService,
    _parse_trace,
    artifact_bytes,
    build_environment_candidate_material,
    strict_json_loads,
    environment_profile_ref,
    environment_schema_directory,
    load_closed_test_manifest_v1,
    outer_sandbox_profile,
    validate_eligibility_resolution,
    validate_eligibility_source,
    validate_resolved_environment_profile_v1,
    validate_verification_profile_v4,
    verification_profile_ref,
)


RECEIPT_VERSION = "semantic-guard-governed-environment-execution-receipt/v1"
EXECUTION_NONCE_ENV = "SEMANTIC_GUARD_EXECUTION_NONCE"
COMMAND_DIGEST_ENV = "SEMANTIC_GUARD_COMMAND_DIGEST"
SUBJECT_MANIFEST_DIGEST_ENV = "SEMANTIC_GUARD_SUBJECT_MANIFEST_DIGEST"
_RECEIPT_SCHEMA = (
    environment_schema_directory()
    / "governed-environment-execution-receipt-v1.schema.json"
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _inside_repository(root: Path, path: Path, *, code: str) -> Path:
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, ValueError) as exc:
        raise EnvironmentResolutionError(code, str(path)) from exc
    return resolved


def _new_output_directory(root: Path, requested: Path) -> Path:
    absolute = requested.absolute()
    try:
        absolute.parent.resolve(strict=True).relative_to(root)
    except (OSError, ValueError) as exc:
        raise EnvironmentResolutionError(
            "execution_output_parent_invalid", str(requested)
        ) from exc
    try:
        absolute.mkdir(mode=0o700)
    except OSError as exc:
        raise EnvironmentResolutionError(
            "execution_output_directory_create_failed", str(requested)
        ) from exc
    return absolute


def _write_exclusive(path: Path, value: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    descriptor = os.open(path, flags, 0o600)
    try:
        os.fchmod(descriptor, 0o600)
        offset = 0
        while offset < len(value):
            offset += os.write(descriptor, value[offset:])
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    parent_fd = os.open(
        path.parent,
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
    )
    try:
        os.fsync(parent_fd)
    finally:
        os.close(parent_fd)


def _artifact_ref(root: Path, path: Path, record_id: str) -> dict[str, Any]:
    resolved = _inside_repository(root, path, code="execution_artifact_outside_repository")
    return {
        "record_id": record_id,
        "locator": resolved.relative_to(root).as_posix(),
        "content_digest": file_digest(resolved),
    }


def _verify_ref(root: Path, reference: Mapping[str, Any]) -> Path:
    locator = str(reference.get("locator", ""))
    if not locator or locator.startswith("/") or ".." in Path(locator).parts:
        raise EnvironmentResolutionError("execution_reference_locator_invalid", locator)
    resolved = _inside_repository(
        root, root / locator, code="execution_reference_locator_invalid"
    )
    if file_digest(resolved) != reference.get("content_digest"):
        raise EnvironmentResolutionError("execution_reference_digest_mismatch", locator)
    return resolved


def _used_tool_ref(tool: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "tool_id": tool["tool_id"],
        "invocation_path": tool["invocation_path"],
        "resolved_path": tool["resolved_path"],
        "version": tool["version"],
        "file_digest": tool["file_digest"],
        "capability_binding_digest": tool["capability_binding"]["binding_digest"],
    }


def build_managed_environment_v1(
    verification_profile: Mapping[str, Any],
    eligibility_resolution: Mapping[str, Any],
    *,
    parent_environment: Mapping[str, str],
) -> tuple[dict[str, str], dict[str, Any]]:
    validate_verification_profile_v4(verification_profile)
    if (
        eligibility_resolution.get("schema_version") != ELIGIBILITY_RESOLUTION_VERSION
        or eligibility_resolution.get("resolution_status") != "eligible_scoped"
        or eligibility_resolution.get("environment_use_allowed") is not True
    ):
        raise EnvironmentResolutionError(
            "environment_not_eligible_for_execution",
            str(eligibility_resolution.get("resolution_status")),
        )
    contract = verification_profile["environment_contract"]
    inherited = [str(item) for item in contract["inherited_environment_allowlist"]]
    fixed = {str(key): str(value) for key, value in contract["fixed_environment"].items()}
    if set(inherited) & set(fixed):
        raise EnvironmentResolutionError(
            "environment_contract_variable_conflict",
            repr(sorted(set(inherited) & set(fixed))),
        )
    environment = {
        name: str(parent_environment[name])
        for name in inherited
        if name in parent_environment
    }
    environment.update(fixed)
    environment["PATH"] = str(eligibility_resolution["effective_path"]["rendered_value"])
    forbidden = {
        name
        for name in environment
        if name in {"PYTHONPATH", "PYTHONHOME"} or name.startswith("DYLD_")
    }
    if forbidden:
        raise EnvironmentResolutionError(
            "forbidden_environment_variable", repr(sorted(forbidden))
        )
    variable_digests = {
        name: canonical_digest({"name": name, "value": value})
        for name, value in sorted(environment.items())
    }
    receipt_projection: dict[str, Any] = {
        "effective_path": eligibility_resolution["effective_path"],
        "variable_names": sorted(environment),
        "variable_digests": variable_digests,
    }
    receipt_projection["content_digest"] = canonical_digest(receipt_projection)
    return dict(sorted(environment.items())), receipt_projection


def render_governed_command_v1(
    command_id: str,
    verification_profile: Mapping[str, Any],
    candidate_profile: Mapping[str, Any],
    *,
    repository_root: Path,
) -> dict[str, Any]:
    validate_verification_profile_v4(verification_profile)
    validate_resolved_environment_profile_v1(
        candidate_profile, verification_profile=verification_profile
    )
    commands = [
        item
        for item in verification_profile["commands"]
        if item["command_id"] == command_id
    ]
    if len(commands) != 1:
        raise EnvironmentResolutionError(
            "verification_command_resolution_not_unique", command_id
        )
    command = commands[0]
    by_id = {
        str(item["tool_id"]): item for item in candidate_profile["resolved_tools"]
    }
    if set(by_id) != {
        "containment_launcher.vnext",
        "python.vnext",
        "test_runner.vnext",
    }:
        raise EnvironmentResolutionError(
            "qualified_tool_denominator_mismatch", repr(sorted(by_id))
        )
    launcher = by_id["containment_launcher.vnext"]
    python_tool = by_id["python.vnext"]
    runner = by_id["test_runner.vnext"]
    root = repository_root.resolve(strict=True)
    closed_manifest_ref = dict(command["closed_test_manifest_ref"])
    closed_manifest = load_closed_test_manifest_v1(
        closed_manifest_ref,
        repository_root=root,
        expected_command_id=command_id,
    )
    test_modules = list(closed_manifest["test_denominator"]["modules"])
    expected_test_ids = list(
        closed_manifest["test_denominator"]["expected_test_ids"]
    )
    cwd_locator = str(command["cwd"])
    cwd = root if cwd_locator == "." else _inside_repository(
        root, root / cwd_locator, code="verification_command_cwd_invalid"
    )
    if not cwd.is_dir():
        raise EnvironmentResolutionError("verification_command_cwd_invalid", str(cwd))
    test_source_bindings = []
    for module_name, reference in zip(
        test_modules,
        closed_manifest["test_denominator"]["test_source_refs"],
        strict=True,
    ):
        source_path = _inside_repository(
            root,
            root / str(reference["locator"]),
            code="verification_test_source_invalid",
        )
        test_source_bindings.append(
            {
                "module_name": str(module_name),
                "source_file": str(source_path),
                "source_digest": str(reference["content_digest"]["value"]),
            }
        )
    python_runtime = python_tool["capability_binding"]["python_runtime"]
    if python_runtime is None:
        raise EnvironmentResolutionError("python_runtime_binding_missing", command_id)
    dependency_roots = [
        str(item["path"])
        for item in python_runtime["dependency_import_roots"]
        if item["root_kind"] == "site_packages"
    ]
    if len(dependency_roots) != 1:
        raise EnvironmentResolutionError(
            "site_packages_root_resolution_not_unique", repr(dependency_roots)
        )
    argv = [
        str(launcher["invocation_path"]),
        "-p",
        outer_sandbox_profile(str(python_tool["resolved_path"])),
        str(python_tool["resolved_path"]),
        "-I",
        "-S",
        "-B",
        str(runner["invocation_path"]),
    ]
    # U-10 smoke uses only the stdlib and exact source bytes.  Site-packages
    # remain qualified as environment material but are not placed on sys.path.
    for binding in test_source_bindings:
        argv.extend(["--test-source-file", binding["source_file"]])
        argv.extend(["--test-source-digest", binding["source_digest"]])
        argv.extend(["--test-module-name", binding["module_name"]])
    for test_id in expected_test_ids:
        argv.extend(["--expected-test-id", str(test_id)])
    rendered: dict[str, Any] = {
        "containment_launcher_tool": _used_tool_ref(launcher),
        "interpreter_tool": _used_tool_ref(python_tool),
        "runner_tool": _used_tool_ref(runner),
        "argv": argv,
        "cwd": str(cwd),
        "qualified_dependency_import_roots": dependency_roots,
        "active_dependency_import_roots": [],
        "test_source_bindings": test_source_bindings,
        "closed_test_manifest_ref": closed_manifest_ref,
        "expected_test_ids": expected_test_ids,
        "timeout_seconds": command["timeout_seconds"],
        "artifact_effect": command["artifact_effect"],
    }
    rendered["command_digest"] = canonical_digest(rendered)
    return rendered


def _observation_digest_valid(observation: Mapping[str, Any]) -> bool:
    if observation.get("observation_kind") != "fresh_exact_environment_reobservation/v1":
        return False
    material = dict(observation)
    observed = material.pop("observation_digest", None)
    return observed is not None and canonical_digest(material) == observed


def _unavailable_observation(reason: str) -> dict[str, Any]:
    return {
        "observation_kind": "unavailable/v1",
        "reason_codes": [reason],
        "formal_authority": "none",
        "positive_assurance_allowed": False,
    }


def _candidate_observation_projection(
    candidate_profile: Mapping[str, Any],
) -> dict[str, Any]:
    observation: dict[str, Any] = {
        "observation_kind": "fresh_exact_environment_reobservation/v1",
        "platform": candidate_profile["platform"],
        "host_identity_ref": candidate_profile["host_identity_ref"],
        "resolved_tools": candidate_profile["resolved_tools"],
        "effective_path": candidate_profile["effective_path"],
        "containment_capability": candidate_profile["containment_capability"],
    }
    observation["observation_digest"] = canonical_digest(observation)
    return observation


_TRACE_REASON_CODES = {
    "containment_trace_invalid",
    "containment_trace_sequence_invalid",
    "containment_trace_protocol_mismatch",
    "process_containment_trace_incomplete",
    "process_containment_trace_binding_mismatch",
}


def _process_trace_assessment(
    raw_trace: bytes,
    *,
    expected_command: Mapping[str, Any],
    execution_nonce: str,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    reasons: list[str] = []
    try:
        records = _parse_trace(raw_trace)
    except EnvironmentResolutionError as exc:
        return (
            {
                "activation_status": "not_observed",
                "trace_status": "incomplete",
                "executable_set_completeness": "incomplete",
                "process_creation_attempt_count": 0,
                "executed_child_count": None,
            },
            {
                "result_status": "unavailable",
                "tests_run": None,
                "failures": None,
                "errors": None,
                "skipped": None,
                "test_ids": [],
            },
            [exc.code],
        )
    activations = [item for item in records if item.get("event") == "containment_activated"]
    starts = [item for item in records if item.get("event") == "runner_started"]
    completions = [item for item in records if item.get("event") == "test_run_completed"]
    process_attempts = [
        item for item in records if item.get("event") == "process_creation_attempt"
    ]
    forbidden_exec_attempts = [
        item
        for item in process_attempts
        if str(item.get("audit_event", "")).startswith("os.exec")
        or str(item.get("audit_event", "")).startswith("os.spawn")
        or item.get("audit_event") == "os.posix_spawn"
    ]
    expected_bindings = {
        "execution_nonce": execution_nonce,
        "command_digest": expected_command["command_digest"]["value"],
        "subject_manifest_digest": expected_command["closed_test_manifest_ref"][
            "content_digest"
        ]["value"],
    }
    bindings_match = all(
        all(record.get(name) == value for name, value in expected_bindings.items())
        for record in records
    )
    start_matches = (
        len(starts) == 1
        and starts[0].get("executable")
        == expected_command["interpreter_tool"]["resolved_path"]
        and starts[0].get("test_source_bindings")
        == expected_command["test_source_bindings"]
        and starts[0].get("expected_test_ids")
        == expected_command["expected_test_ids"]
        and starts[0].get("cwd") == expected_command["cwd"]
        and starts[0].get("dependency_import_roots")
        == expected_command["active_dependency_import_roots"]
    )
    expected_test_ids = list(expected_command["expected_test_ids"])
    complete = (
        bindings_match
        and
        len(activations) == 1
        and activations[0].get("outer_probe")
        == "fork_and_non_python_exec_denied"
        and start_matches
        and starts[0].get("isolated") is True
        and starts[0].get("no_site") is True
        and len(completions) == 1
        and completions[0].get("executed_child_count") == 0
        and completions[0].get("test_ids") == expected_test_ids
        and completions[0].get("tests_run") == len(expected_test_ids)
        and len(expected_test_ids) > 0
        and not forbidden_exec_attempts
        and records[-1].get("event") == "test_run_completed"
    )
    if not complete:
        reasons.append("process_containment_trace_incomplete")
    if not bindings_match or not start_matches:
        reasons.append("process_containment_trace_binding_mismatch")
    completion = completions[0] if len(completions) == 1 else None
    completion_is_successful = (
        completion is not None
        and completion.get("successful") is True
        and type(completion.get("failures")) is int
        and int(completion.get("failures", 0)) == 0
        and type(completion.get("errors")) is int
        and int(completion.get("errors", 0)) == 0
        and type(completion.get("skipped")) is int
        and int(completion.get("skipped", 0)) == 0
    )
    structured = (
        {
            "result_status": "successful" if completion_is_successful else "failed",
            "tests_run": int(completion.get("tests_run", 0)),
            "failures": int(completion.get("failures", 0)),
            "errors": int(completion.get("errors", 0)),
            "skipped": int(completion.get("skipped", 0)),
            "test_ids": list(completion.get("test_ids", [])),
        }
        if completion is not None
        else {
            "result_status": "unavailable",
            "tests_run": None,
            "failures": None,
            "errors": None,
            "skipped": None,
            "test_ids": [],
        }
    )
    return (
        {
            "activation_status": "activated" if len(activations) == 1 else "not_observed",
            "trace_status": "complete_no_children" if complete else "incomplete",
            "executable_set_completeness": "complete" if complete else "incomplete",
            "process_creation_attempt_count": len(process_attempts),
            "executed_child_count": 0 if complete else None,
        },
        structured,
        reasons,
    )


def _execute_governed_command_with_service_v1(
    command_id: str,
    verification_profile: Mapping[str, Any],
    candidate_profile: Mapping[str, Any],
    *,
    eligibility_service: EnvironmentEligibilityService,
    output_directory: Path,
    receipt_id: str,
    evidence_store_root: Path | None = None,
    execution_uid: int | None,
    execution_gid: int | None,
    extra_groups: tuple[int, ...] | None,
    umask: int,
    child_start_new_session: bool = True,
    parent_environment: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Internal engine; operational callers must use the external root broker.

    A caller-supplied eligibility service is intentionally retained only for
    isolated contract tests.  Receipts from this helper are not externally
    attested and cannot close U-10 by themselves.
    """
    subject_root = eligibility_service.repository_root
    evidence_root = (
        subject_root
        if evidence_store_root is None
        else evidence_store_root.resolve(strict=True)
    )
    if not evidence_root.is_dir():
        raise EnvironmentResolutionError(
            "execution_evidence_store_not_directory", str(evidence_root)
        )
    for name, value in (
        ("execution_uid", execution_uid),
        ("execution_gid", execution_gid),
    ):
        if value is not None and (
            isinstance(value, bool) or not isinstance(value, int) or value < 0
        ):
            raise EnvironmentResolutionError(
                "execution_principal_invalid", f"{name}={value!r}"
            )
    if extra_groups is not None and (
        any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0
            for value in extra_groups
        )
        or len(set(extra_groups)) != len(extra_groups)
    ):
        raise EnvironmentResolutionError(
            "execution_extra_groups_invalid", repr(extra_groups)
        )
    if (
        isinstance(umask, bool)
        or not isinstance(umask, int)
        or not 0 <= umask <= 0o777
    ):
        raise EnvironmentResolutionError("execution_umask_invalid", repr(umask))
    resolution = eligibility_service.resolve(candidate_profile, verification_profile)
    if resolution.get("environment_use_allowed") is not True:
        raise EnvironmentResolutionError(
            "environment_not_eligible_for_execution",
            repr(resolution.get("reason_codes", [])),
        )
    source = eligibility_service.source
    external_adoption = eligibility_service.external_adoption
    if external_adoption is None:
        raise EnvironmentResolutionError(
            "external_environment_adoption_required", command_id
        )
    validate_eligibility_resolution(
        resolution,
        candidate_profile=candidate_profile,
        verification_profile=verification_profile,
        source=source,
        external_adoption=external_adoption,
    )
    active_adoption_ref = {
        "adoption_id": external_adoption["adoption_id"],
        "adoption_version": external_adoption["adoption_version"],
        "adoption_digest": external_adoption["adoption_digest"],
    }
    command = render_governed_command_v1(
        command_id,
        verification_profile,
        candidate_profile,
        repository_root=subject_root,
    )
    actual_environment, environment_projection = build_managed_environment_v1(
        verification_profile,
        resolution,
        parent_environment=os.environ if parent_environment is None else parent_environment,
    )
    execution_nonce = secrets.token_hex(32)
    actual_environment[EXECUTION_NONCE_ENV] = execution_nonce
    actual_environment[COMMAND_DIGEST_ENV] = command["command_digest"]["value"]
    actual_environment[SUBJECT_MANIFEST_DIGEST_ENV] = command[
        "closed_test_manifest_ref"
    ]["content_digest"]["value"]
    run_directory = _new_output_directory(evidence_root, output_directory)
    stdout_path = run_directory / "stdout.log"
    stderr_path = run_directory / "stderr.log"
    trace_path = run_directory / "process-trace.jsonl"
    receipt_path = run_directory / "receipt.json"
    read_fd, write_fd = os.pipe()
    actual_environment[TRACE_FD_ENV] = str(write_fd)
    environment_projection = {
        "effective_path": environment_projection["effective_path"],
        "variable_names": sorted(actual_environment),
        "variable_digests": {
            name: canonical_digest({"name": name, "value": value})
            for name, value in sorted(actual_environment.items())
        },
    }
    environment_projection["content_digest"] = canonical_digest(
        environment_projection
    )
    started_at = _utc_now()
    timed_out = False
    exit_code: int | None = None
    try:
        with stdout_path.open("xb") as stdout_file, stderr_path.open("xb") as stderr_file:
            process = subprocess.Popen(
                command["argv"],
                cwd=command["cwd"],
                env=actual_environment,
                stdin=subprocess.DEVNULL,
                stdout=stdout_file,
                stderr=stderr_file,
                pass_fds=(write_fd,),
                start_new_session=child_start_new_session,
                user=execution_uid,
                group=execution_gid,
                extra_groups=extra_groups,
                umask=umask,
            )
            os.close(write_fd)
            write_fd = -1
            try:
                exit_code = process.wait(timeout=float(command["timeout_seconds"]))
            except subprocess.TimeoutExpired:
                timed_out = True
                try:
                    if child_start_new_session:
                        os.killpg(process.pid, signal.SIGTERM)
                    else:
                        process.terminate()
                    process.wait(timeout=5)
                except (OSError, subprocess.TimeoutExpired):
                    try:
                        if child_start_new_session:
                            os.killpg(process.pid, signal.SIGKILL)
                        else:
                            process.kill()
                    except OSError:
                        pass
                    process.wait()
                exit_code = process.returncode
                if not child_start_new_session:
                    raise EnvironmentResolutionError(
                        "worker_child_timed_out_requires_root_reap",
                        str(command_id),
                    )
        trace_bytes = b""
        while block := os.read(read_fd, 65536):
            trace_bytes += block
    finally:
        if write_fd >= 0:
            os.close(write_fd)
        os.close(read_fd)
    _write_exclusive(trace_path, trace_bytes)
    finished_at = _utc_now()
    containment, structured_result, reasons = _process_trace_assessment(
        trace_bytes,
        expected_command=command,
        execution_nonce=execution_nonce,
    )
    try:
        stored_containment_path = _verify_ref(
            subject_root,
            candidate_profile["containment_capability"]["probe_evidence_ref"],
        )
        stored_containment = strict_json_loads(
            stored_containment_path.read_bytes()
        )
        fresh_material = build_environment_candidate_material(
            verification_profile,
            repository_root=subject_root,
            environment_profile_id=str(candidate_profile["environment_profile_id"]),
            environment_profile_version=str(candidate_profile["environment_profile_version"]),
            host_evidence_locator=str(
                candidate_profile["host_identity_ref"]["evidence_ref"]["locator"]
            ),
            containment_evidence_locator=str(
                candidate_profile["containment_capability"]["probe_evidence_ref"]["locator"]
            ),
            containment_trace_locator=str(stored_containment["trace_ref"]["locator"]),
        )
        post_candidate = fresh_material["resolved_environment_profile"]
        if post_candidate == dict(candidate_profile):
            post_observation = _candidate_observation_projection(post_candidate)
        else:
            post_observation = _unavailable_observation(
                "environment_changed_during_execution"
            )
            reasons.append("environment_changed_during_execution")
    except (EnvironmentResolutionError, OSError, KeyError, json.JSONDecodeError) as exc:
        reason = (
            exc.code
            if isinstance(exc, EnvironmentResolutionError)
            else "post_observation_failed"
        )
        post_observation = _unavailable_observation(reason)
        reasons.append(reason)
    pre_observation = resolution["current_observation"]
    observations_stable = (
        _observation_digest_valid(pre_observation)
        and _observation_digest_valid(post_observation)
        and pre_observation == post_observation
    )
    if not observations_stable:
        reasons.append("environment_observation_not_stable")
    reasons = sorted(set(reasons))
    if timed_out:
        execution_status = "timed_out"
        reasons.append("verification_command_timed_out")
    elif (
        exit_code == 0
        and containment["trace_status"] == "complete_no_children"
        and structured_result["result_status"] == "successful"
        and structured_result["skipped"] == 0
        and observations_stable
        and not reasons
    ):
        execution_status = "passed"
    elif containment["trace_status"] != "complete_no_children" or not observations_stable:
        execution_status = "invalid"
    else:
        execution_status = "failed"
    reasons = sorted(set(reasons))
    by_id = {
        str(item["tool_id"]): item for item in candidate_profile["resolved_tools"]
    }
    trace_ref = _artifact_ref(evidence_root, trace_path, f"{receipt_id}.trace")
    containment.update(
        {
            "protocol": CONTAINMENT_PROTOCOL,
            "process_creation_policy": "prohibited_after_runner_start",
            "used_executable_refs": [
                _used_tool_ref(by_id["containment_launcher.vnext"]),
                _used_tool_ref(by_id["python.vnext"]),
            ],
            "used_tool_refs": [
                _used_tool_ref(by_id["containment_launcher.vnext"]),
                _used_tool_ref(by_id["python.vnext"]),
                _used_tool_ref(by_id["test_runner.vnext"]),
            ],
            "trace_ref": trace_ref,
        }
    )
    receipt: dict[str, Any] = {
        "schema_version": RECEIPT_VERSION,
        "receipt_id": receipt_id,
        "command_id": command_id,
        "execution_nonce": execution_nonce,
        "execution_status": execution_status,
        "environment_use_allowed_at_start": True,
        "subject_manifest_ref": dict(command["closed_test_manifest_ref"]),
        "verification_profile_ref": verification_profile_ref(verification_profile),
        "environment_profile_ref": environment_profile_ref(candidate_profile),
        "adoption_ref": active_adoption_ref,
        "trust_source_ref": {
            "source_id": source["source_id"],
            "source_version": source["source_version"],
            "source_digest": source["source_digest"],
        },
        "eligibility_resolution_ref": {
            "schema_version": ELIGIBILITY_RESOLUTION_VERSION,
            "resolution_digest": resolution["resolution_digest"],
        },
        "command": command,
        "managed_environment": environment_projection,
        "started_at": started_at,
        "finished_at": finished_at,
        "exit_code": exit_code,
        "pre_observation": pre_observation,
        "post_observation": post_observation,
        "observation_status": "stable" if observations_stable else "requalification_required",
        "reason_codes": reasons,
        "process_containment": containment,
        "structured_result": structured_result,
        "stdout_ref": _artifact_ref(
            evidence_root, stdout_path, f"{receipt_id}.stdout"
        ),
        "stderr_ref": _artifact_ref(
            evidence_root, stderr_path, f"{receipt_id}.stderr"
        ),
        "formal_authority": "none",
        "positive_assurance_allowed": False,
        "limitations": [
            "This receipt establishes occurrence and bounded environment evidence, not engineering correctness.",
            "The macOS sandbox mechanism is deprecated and limited to the adopted host/OS profile.",
            "Test code shares the runner process; trace-channel tamper resistance is bounded and not a hostile-code security boundary.",
            "U-4 principal identity, delegation, and external revocation remain separately governed.",
        ],
    }
    receipt["receipt_digest"] = canonical_digest(receipt)
    validate_execution_receipt_v1(
        receipt,
        verification_profile=verification_profile,
        candidate_profile=candidate_profile,
        source=source,
        eligibility_resolution=resolution,
        external_adoption=external_adoption,
        repository_root=subject_root,
        evidence_store_root=evidence_root,
    )
    _write_exclusive(receipt_path, artifact_bytes(receipt))
    return receipt


def validate_execution_receipt_v1(
    receipt: Mapping[str, Any],
    *,
    verification_profile: Mapping[str, Any],
    candidate_profile: Mapping[str, Any],
    source: Mapping[str, Any],
    eligibility_resolution: Mapping[str, Any],
    external_adoption: Mapping[str, Any] | None = None,
    repository_root: Path,
    evidence_store_root: Path | None = None,
) -> None:
    validate_eligibility_source(source)
    if external_adoption is None:
        raise EnvironmentResolutionError(
            "external_environment_adoption_required",
            str(receipt.get("receipt_id")),
        )
    validate_eligibility_resolution(
        eligibility_resolution,
        candidate_profile=candidate_profile,
        verification_profile=verification_profile,
        source=source,
        external_adoption=external_adoption,
    )
    try:
        schema = strict_json_loads(_RECEIPT_SCHEMA.read_bytes())
        Draft202012Validator.check_schema(schema)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise EnvironmentResolutionError(
            "schema_unavailable", f"{_RECEIPT_SCHEMA}: {exc}"
        ) from exc
    issues = sorted(
        Draft202012Validator(
            schema, format_checker=FormatChecker()
        ).iter_errors(receipt),
        key=lambda issue: tuple(str(part) for part in issue.absolute_path),
    )
    if issues:
        issue = issues[0]
        location = "/".join(str(part) for part in issue.absolute_path) or "$"
        raise EnvironmentResolutionError(
            "execution_receipt_schema_invalid", f"{location}: {issue.message}"
        )
    material = dict(receipt)
    observed_digest = material.pop("receipt_digest")
    if canonical_digest(material) != observed_digest:
        raise EnvironmentResolutionError(
            "execution_receipt_digest_mismatch", str(receipt.get("receipt_id"))
        )
    if receipt["verification_profile_ref"] != verification_profile_ref(verification_profile):
        raise EnvironmentResolutionError("execution_receipt_profile_ref_mismatch", str(receipt["receipt_id"]))
    if receipt["environment_profile_ref"] != environment_profile_ref(candidate_profile):
        raise EnvironmentResolutionError("execution_receipt_environment_ref_mismatch", str(receipt["receipt_id"]))
    expected_adoption_ref = {
        "adoption_id": external_adoption["adoption_id"],
        "adoption_version": external_adoption["adoption_version"],
        "adoption_digest": external_adoption["adoption_digest"],
    }
    if receipt["adoption_ref"] != expected_adoption_ref:
        raise EnvironmentResolutionError("execution_receipt_adoption_ref_mismatch", str(receipt["receipt_id"]))
    if receipt["eligibility_resolution_ref"]["resolution_digest"] != eligibility_resolution["resolution_digest"]:
        raise EnvironmentResolutionError("execution_receipt_eligibility_ref_mismatch", str(receipt["receipt_id"]))
    expected_source_ref = {
        "source_id": source["source_id"],
        "source_version": source["source_version"],
        "source_digest": source["source_digest"],
    }
    if receipt["trust_source_ref"] != expected_source_ref:
        raise EnvironmentResolutionError(
            "execution_receipt_trust_source_ref_mismatch",
            str(receipt["receipt_id"]),
        )
    command = dict(receipt["command"])
    command_digest = command.pop("command_digest")
    if canonical_digest(command) != command_digest:
        raise EnvironmentResolutionError("execution_command_digest_mismatch", str(receipt["command_id"]))
    environment = dict(receipt["managed_environment"])
    environment_digest = environment.pop("content_digest")
    if canonical_digest(environment) != environment_digest:
        raise EnvironmentResolutionError("managed_environment_digest_mismatch", str(receipt["receipt_id"]))
    if sorted(receipt["managed_environment"]["variable_digests"]) != receipt["managed_environment"]["variable_names"]:
        raise EnvironmentResolutionError("managed_environment_variable_projection_mismatch", str(receipt["receipt_id"]))
    if receipt["managed_environment"]["effective_path"] != candidate_profile["effective_path"]:
        raise EnvironmentResolutionError(
            "managed_environment_path_mismatch", str(receipt["receipt_id"])
        )
    variable_digests = receipt["managed_environment"]["variable_digests"]
    fixed = {
        **verification_profile["environment_contract"]["fixed_environment"],
        "PATH": candidate_profile["effective_path"]["rendered_value"],
    }
    for name, value in fixed.items():
        if variable_digests.get(name) != canonical_digest(
            {"name": name, "value": value}
        ):
            raise EnvironmentResolutionError(
                "managed_environment_fixed_value_mismatch", name
            )
    allowed_names = (
        set(fixed)
        | set(
            verification_profile["environment_contract"][
                "inherited_environment_allowlist"
            ]
        )
        | {
            TRACE_FD_ENV,
            EXECUTION_NONCE_ENV,
            COMMAND_DIGEST_ENV,
            SUBJECT_MANIFEST_DIGEST_ENV,
        }
    )
    expected_dynamic = {
        EXECUTION_NONCE_ENV: receipt["execution_nonce"],
        COMMAND_DIGEST_ENV: receipt["command"]["command_digest"]["value"],
        SUBJECT_MANIFEST_DIGEST_ENV: receipt["subject_manifest_ref"][
            "content_digest"
        ]["value"],
    }
    if any(
        variable_digests.get(name)
        != canonical_digest({"name": name, "value": value})
        for name, value in expected_dynamic.items()
    ):
        raise EnvironmentResolutionError(
            "managed_environment_execution_binding_mismatch",
            str(receipt["receipt_id"]),
        )
    if set(variable_digests) - allowed_names or not (
        {TRACE_FD_ENV, *expected_dynamic}.issubset(variable_digests)
    ):
        raise EnvironmentResolutionError(
            "managed_environment_variable_denominator_mismatch",
            repr(sorted(variable_digests)),
        )
    expected_observation = eligibility_resolution["current_observation"]
    candidate_observation = _candidate_observation_projection(candidate_profile)
    if expected_observation != candidate_observation:
        raise EnvironmentResolutionError(
            "execution_receipt_eligibility_observation_projection_mismatch",
            str(receipt["receipt_id"]),
        )
    if receipt["pre_observation"] != expected_observation:
        raise EnvironmentResolutionError(
            "execution_receipt_pre_observation_mismatch",
            str(receipt["receipt_id"]),
        )
    post_observation = receipt["post_observation"]
    if (
        post_observation.get("observation_kind")
        == "fresh_exact_environment_reobservation/v1"
    ):
        if post_observation != expected_observation:
            raise EnvironmentResolutionError(
                "execution_receipt_post_observation_mismatch",
                str(receipt["receipt_id"]),
            )
    elif not set(post_observation.get("reason_codes", ())).issubset(
        receipt["reason_codes"]
    ):
        raise EnvironmentResolutionError(
            "execution_receipt_post_observation_reason_mismatch",
            str(receipt["receipt_id"]),
        )
    if (
        receipt["observation_status"] == "stable"
        and post_observation != expected_observation
    ):
        raise EnvironmentResolutionError(
            "execution_receipt_stable_observation_mismatch",
            str(receipt["receipt_id"]),
        )
    passed = receipt["execution_status"] == "passed"
    if passed and not (
        receipt["exit_code"] == 0
        and receipt["observation_status"] == "stable"
        and not receipt["reason_codes"]
        and receipt["pre_observation"] == receipt["post_observation"]
        and _observation_digest_valid(receipt["pre_observation"])
        and receipt["process_containment"]["activation_status"] == "activated"
        and receipt["process_containment"]["trace_status"] == "complete_no_children"
        and receipt["process_containment"]["executable_set_completeness"] == "complete"
        and receipt["process_containment"]["executed_child_count"] == 0
        and receipt["structured_result"]["result_status"] == "successful"
        and receipt["structured_result"]["failures"] == 0
        and receipt["structured_result"]["errors"] == 0
        and receipt["structured_result"]["skipped"] == 0
        and receipt["structured_result"]["tests_run"]
        == len(receipt["command"]["expected_test_ids"])
        and receipt["structured_result"]["tests_run"] > 0
        and receipt["structured_result"]["test_ids"]
        == receipt["command"]["expected_test_ids"]
    ):
        raise EnvironmentResolutionError("passed_receipt_invariant_violation", str(receipt["receipt_id"]))
    started = datetime.fromisoformat(str(receipt["started_at"]).replace("Z", "+00:00"))
    finished = datetime.fromisoformat(str(receipt["finished_at"]).replace("Z", "+00:00"))
    if finished < started:
        raise EnvironmentResolutionError("execution_receipt_time_order_invalid", str(receipt["receipt_id"]))
    subject_root = repository_root.resolve(strict=True)
    evidence_root = (
        subject_root
        if evidence_store_root is None
        else evidence_store_root.resolve(strict=True)
    )
    if not evidence_root.is_dir():
        raise EnvironmentResolutionError(
            "execution_evidence_store_not_directory", str(evidence_root)
        )
    expected_command = render_governed_command_v1(
        str(receipt["command_id"]),
        verification_profile,
        candidate_profile,
        repository_root=subject_root,
    )
    if receipt["command"] != expected_command:
        raise EnvironmentResolutionError(
            "execution_receipt_command_projection_mismatch",
            str(receipt["command_id"]),
        )
    if receipt["subject_manifest_ref"] != expected_command["closed_test_manifest_ref"]:
        raise EnvironmentResolutionError(
            "execution_receipt_subject_manifest_mismatch",
            str(receipt["command_id"]),
        )
    _verify_ref(subject_root, receipt["subject_manifest_ref"])
    for field in ("stdout_ref", "stderr_ref"):
        _verify_ref(evidence_root, receipt[field])
    trace_path = _verify_ref(
        evidence_root, receipt["process_containment"]["trace_ref"]
    )
    trace_assessment, trace_result, trace_reasons = _process_trace_assessment(
        trace_path.read_bytes(),
        expected_command=expected_command,
        execution_nonce=str(receipt["execution_nonce"]),
    )
    for field in (
        "activation_status",
        "trace_status",
        "executable_set_completeness",
        "process_creation_attempt_count",
        "executed_child_count",
    ):
        if receipt["process_containment"][field] != trace_assessment[field]:
            raise EnvironmentResolutionError(
                "execution_receipt_trace_projection_mismatch", field
            )
    if receipt["structured_result"] != trace_result:
        raise EnvironmentResolutionError(
            "execution_receipt_structured_result_mismatch",
            str(receipt["receipt_id"]),
        )
    declared_trace_reasons = set(receipt["reason_codes"]) & _TRACE_REASON_CODES
    if declared_trace_reasons != set(trace_reasons):
        raise EnvironmentResolutionError(
            "execution_receipt_trace_reason_projection_mismatch",
            str(receipt["receipt_id"]),
        )
    by_id = {
        str(item["tool_id"]): item
        for item in candidate_profile["resolved_tools"]
    }
    expected_used_tools = [
        _used_tool_ref(by_id["containment_launcher.vnext"]),
        _used_tool_ref(by_id["python.vnext"]),
        _used_tool_ref(by_id["test_runner.vnext"]),
    ]
    if receipt["process_containment"]["used_tool_refs"] != expected_used_tools:
        raise EnvironmentResolutionError(
            "execution_receipt_used_tool_projection_mismatch",
            str(receipt["receipt_id"]),
        )
    if receipt["process_containment"]["used_executable_refs"] != expected_used_tools[:2]:
        raise EnvironmentResolutionError(
            "execution_receipt_used_executable_projection_mismatch",
            str(receipt["receipt_id"]),
        )
