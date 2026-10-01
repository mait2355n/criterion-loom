"""Root supervisor for one U-10 snapshot execution request."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import secrets
import signal
import stat
import subprocess
import time
from typing import Any

from .core import (
    build_statement_skeleton_v3,
    canonical_json_bytes,
    revalidate_trusted_execution_context_v2,
    resolve_trusted_execution_context_v2,
)
from .internal_operations import (
    build_signed_envelope_v3 as _build_signed_envelope_v3,
    require_time_order as _require_time_order,
)
from .protected_io import (
    AUTHORIZATION_ROOT,
    BrokerBoundaryError,
    EVIDENCE_SPOOL_ROOT,
    digest_bytes,
    read_protected_file,
    strict_json_loads,
    trust_store_coordination_lock,
    validate_directory_chain,
    validate_protected_tree,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _write_exclusive(path: Path, raw: bytes, *, mode: int) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags, mode)
    try:
        # ``open(..., mode)`` is filtered through the caller's process umask.
        # The broker contract requires the requested mode itself, so establish
        # it explicitly on the already-open, O_EXCL-created descriptor before
        # publishing any content.
        os.fchmod(descriptor, mode)
        offset = 0
        while offset < len(raw):
            offset += os.write(descriptor, raw[offset:])
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    parent_descriptor = os.open(
        path.parent,
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
    )
    try:
        os.fsync(parent_descriptor)
    finally:
        os.close(parent_descriptor)


def _snapshot_flat_ref(value: Mapping[str, Any], semantic_field: str) -> dict[str, Any]:
    reference = value["snapshot_artifact_ref"]
    return {
        "record_id": reference["record_id"],
        "locator": reference["locator"],
        "artifact_digest": reference["artifact_digest"],
        semantic_field: value[semantic_field],
    }


def _environment_adoption_context_v2(
    context: Mapping[str, Any],
) -> dict[str, Any]:
    """Project one exact broker-verified adoption into the worker context."""

    reference = context.get("environment_adoption_ref")
    adoption = context.get("environment_adoption")
    if (
        not isinstance(reference, Mapping)
        or set(reference)
        != {"record_id", "locator", "artifact_digest", "semantic_digest"}
        or not isinstance(adoption, Mapping)
    ):
        raise BrokerBoundaryError(
            "u10_environment_adoption_context_binding_mismatch",
            str(context.get("request", {}).get("entry_id", "unknown")),
        )
    adoption_value = dict(adoption)
    adoption_id = adoption_value.get("adoption_id")
    adoption_version = adoption_value.get("adoption_version")
    adoption_digest = adoption_value.get("adoption_digest")
    record_raw = canonical_json_bytes(adoption_value) + b"\n"
    material = dict(adoption_value)
    material.pop("adoption_digest", None)
    if (
        not isinstance(adoption_id, str)
        or not adoption_id
        or not isinstance(adoption_version, str)
        or not adoption_version
        or reference.get("record_id") != adoption_id
        or Path(str(reference.get("locator", "")))
        != AUTHORIZATION_ROOT / f"{adoption_id}.json"
        or reference.get("artifact_digest") != digest_bytes(record_raw)
        or reference.get("semantic_digest") != adoption_digest
        or adoption_digest != digest_bytes(canonical_json_bytes(material))
    ):
        raise BrokerBoundaryError(
            "u10_environment_adoption_context_binding_mismatch",
            str(adoption_id),
        )
    normalized = strict_json_loads(record_raw)
    if not isinstance(normalized, dict):
        raise BrokerBoundaryError(
            "u10_environment_adoption_context_binding_mismatch",
            str(adoption_id),
        )
    return {
        "environment_adoption_ref": dict(reference),
        "environment_adoption": normalized,
    }


def _new_run_directory(entry_id: str) -> tuple[str, Path, Path]:
    validate_directory_chain(EVIDENCE_SPOOL_ROOT, EVIDENCE_SPOOL_ROOT)
    token = secrets.token_hex(24)
    run_id = f"run.u10.{token}"
    entry_component = hashlib.sha256(entry_id.encode("utf-8")).hexdigest()
    run_directory = EVIDENCE_SPOOL_ROOT / f"{entry_component}.{token}"
    try:
        os.mkdir(run_directory, 0o700)
    except OSError as exc:
        raise BrokerBoundaryError(
            "u10_spool_run_create_failed", str(run_directory)
        ) from exc
    worker_directory = run_directory / "worker"
    try:
        os.mkdir(worker_directory, 0o700)
    except OSError as exc:
        raise BrokerBoundaryError(
            "u10_worker_spool_create_failed", str(worker_directory)
        ) from exc
    for directory in (EVIDENCE_SPOOL_ROOT, run_directory):
        descriptor = os.open(
            directory,
            os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
        )
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    return run_id, run_directory, worker_directory


def _freeze_worker_tree(root: Path, *, worker_uid: int) -> None:
    for raw_directory, directories, files, directory_fd in os.fwalk(
        root, topdown=False, follow_symlinks=False
    ):
        observed_directory = os.fstat(directory_fd)
        if (
            not stat.S_ISDIR(observed_directory.st_mode)
            or observed_directory.st_uid != worker_uid
        ):
            raise BrokerBoundaryError(
                "u10_worker_directory_untrusted", str(raw_directory)
            )
        for name in directories:
            observed = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
            if (
                not stat.S_ISDIR(observed.st_mode)
                or observed.st_uid != 0
                or observed.st_gid != 0
                or stat.S_IMODE(observed.st_mode) != 0o500
            ):
                raise BrokerBoundaryError(
                    "u10_worker_directory_untrusted",
                    str(Path(raw_directory) / name),
                )
        for name in files:
            flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
            descriptor = os.open(name, flags, dir_fd=directory_fd)
            try:
                observed = os.fstat(descriptor)
                if (
                    not stat.S_ISREG(observed.st_mode)
                    or observed.st_uid != worker_uid
                    or observed.st_nlink != 1
                ):
                    raise BrokerBoundaryError(
                        "u10_worker_artifact_untrusted",
                        str(Path(raw_directory) / name),
                    )
                os.fchown(descriptor, 0, 0)
                os.fchmod(descriptor, 0o400)
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        os.fchown(directory_fd, 0, 0)
        os.fchmod(directory_fd, 0o500)
        os.fsync(directory_fd)
    validate_protected_tree(root)


def _ensure_worker_process_group_quiescent(process_id: int) -> str:
    try:
        os.killpg(process_id, signal.SIGKILL)
    except ProcessLookupError:
        return _utc_now()
    except OSError as exc:
        raise BrokerBoundaryError(
            "u10_worker_process_group_check_failed", str(process_id)
        ) from exc
    for _ in range(50):
        try:
            os.killpg(process_id, 0)
        except ProcessLookupError:
            break
        time.sleep(0.01)
    else:
        raise BrokerBoundaryError(
            "u10_worker_process_group_not_quiescent", str(process_id)
        )
    raise BrokerBoundaryError("u10_worker_residual_process_killed", str(process_id))


def _confirm_worker_process_group_absent(process_id: int) -> str:
    for _ in range(50):
        try:
            os.killpg(process_id, 0)
        except ProcessLookupError:
            return _utc_now()
        except OSError as exc:
            raise BrokerBoundaryError(
                "u10_worker_process_group_check_failed", str(process_id)
            ) from exc
        time.sleep(0.01)
    raise BrokerBoundaryError("u10_worker_process_group_not_quiescent", str(process_id))


def _observe_launched_worker_process(
    process: subprocess.Popen[bytes],
) -> dict[str, Any]:
    """Record the process identifiers observed by root after ``Popen``."""

    try:
        process_group_id = os.getpgid(process.pid)
        session_id = os.getsid(process.pid)
    except OSError as exc:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        finally:
            process.wait()
        _confirm_worker_process_group_absent(process.pid)
        raise BrokerBoundaryError(
            "u10_worker_process_observation_failed", str(process.pid)
        ) from exc
    return {
        "pid": process.pid,
        "parent_pid": os.getpid(),
        "process_group_id": process_group_id,
        "session_id": session_id,
        "observed_at": _utc_now(),
    }


def _whole_worker_timeout_seconds(
    snapshot: Mapping[str, Any],
    command_id: str,
) -> float:
    phase = snapshot["worker_runtime"]["phase_budget"]
    command_timeout = snapshot["command_bindings"][command_id][
        "governed_command_timeout_seconds"
    ]
    values = [
        phase["pre_environment_reobservation_seconds"],
        command_timeout,
        phase["post_environment_reobservation_seconds"],
        phase["evidence_finalization_seconds"],
        phase["process_reap_seconds"],
    ]
    if any(
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or value <= 0
        for value in values
    ):
        raise BrokerBoundaryError("u10_worker_phase_budget_invalid", repr(values))
    return float(sum(values))


def _validate_worker_outcome(
    outcome: Mapping[str, Any],
    *,
    context: Mapping[str, Any],
    run_id: str,
    worker_directory: Path,
    broker_process_observation: Mapping[str, Any],
) -> tuple[dict[str, Any], bytes]:
    required = {
        "schema_version",
        "worker_version",
        "run_id",
        "entry_id",
        "command_id",
        "request_nonce",
        "worker_identity",
        "launch_observation",
        "receipt_locator",
        "receipt_artifact_digest",
        "receipt_semantic_digest",
        "execution_nonce",
        "execution_status",
        "started_at",
        "finished_at",
        "formal_authority",
        "positive_assurance_allowed",
    }
    if set(outcome) != required:
        raise BrokerBoundaryError(
            "u10_worker_outcome_field_mismatch", repr(sorted(outcome))
        )
    request = context["request"]
    expected_identity = context["snapshot"]["worker_identity"]
    expected_effective_identity = {
        "uid": expected_identity["uid"],
        "gid": expected_identity["gid"],
        "supplementary_gids": expected_identity["effective_supplementary_gids"],
        "umask": expected_identity["umask"],
    }
    expected_runtime = context["snapshot"]["worker_runtime"]
    observed_identity = outcome.get("worker_identity")
    if (
        not isinstance(observed_identity, Mapping)
        or set(observed_identity) != {"uid", "gid", "supplementary_gids", "umask"}
        or outcome["schema_version"] != "semantic-guard-u10-worker-outcome/v1"
        or outcome["worker_version"] != expected_runtime["worker_version"]
        or outcome["run_id"] != run_id
        or outcome["entry_id"] != request["entry_id"]
        or outcome["command_id"] != request["command_id"]
        or outcome["request_nonce"] != request["request_nonce"]
        or outcome["worker_identity"] != expected_effective_identity
        or outcome["formal_authority"] != "none"
        or outcome["positive_assurance_allowed"] is not False
    ):
        raise BrokerBoundaryError("u10_worker_outcome_binding_mismatch", run_id)
    root_process = broker_process_observation
    if (
        not isinstance(root_process, Mapping)
        or set(root_process)
        != {
            "pid",
            "parent_pid",
            "process_group_id",
            "session_id",
            "observed_at",
        }
        or any(
            type(root_process[name]) is not int or root_process[name] <= 0
            for name in (
                "pid",
                "parent_pid",
                "process_group_id",
                "session_id",
            )
        )
        or root_process["parent_pid"] != os.getpid()
        or root_process["pid"] != root_process["process_group_id"]
        or root_process["pid"] != root_process["session_id"]
    ):
        raise BrokerBoundaryError("u10_broker_process_observation_invalid", run_id)
    _require_time_order(("broker_process_observed_at", root_process["observed_at"]))
    observation = outcome["launch_observation"]
    expected_worker_process = {
        name: root_process[name]
        for name in (
            "pid",
            "parent_pid",
            "process_group_id",
            "session_id",
        )
    }
    if (
        not isinstance(observation, Mapping)
        or set(observation) != {"pid", "parent_pid", "process_group_id", "session_id"}
        or any(
            type(observation[name]) is not int or observation[name] <= 0
            for name in observation
        )
        or dict(observation) != expected_worker_process
    ):
        raise BrokerBoundaryError("u10_worker_launch_observation_mismatch", run_id)
    receipt_path = Path(str(outcome["receipt_locator"]))
    try:
        receipt_path.relative_to(worker_directory)
    except ValueError as exc:
        raise BrokerBoundaryError(
            "u10_worker_receipt_outside_spool", str(receipt_path)
        ) from exc
    raw = read_protected_file(receipt_path, protected_root=worker_directory)
    if digest_bytes(raw) != outcome["receipt_artifact_digest"]:
        raise BrokerBoundaryError("u10_worker_receipt_artifact_mismatch", run_id)
    try:
        receipt = strict_json_loads(raw)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise BrokerBoundaryError("u10_worker_receipt_unreadable", run_id) from exc
    if not isinstance(receipt, dict):
        raise BrokerBoundaryError("u10_worker_receipt_unreadable", run_id)
    material = dict(receipt)
    semantic = material.pop("receipt_digest", None)
    environment_adoption = context.get("environment_adoption")
    if not isinstance(environment_adoption, Mapping):
        raise BrokerBoundaryError("u10_worker_receipt_binding_mismatch", run_id)
    expected_adoption_ref = {
        "adoption_id": environment_adoption.get("adoption_id"),
        "adoption_version": environment_adoption.get("adoption_version"),
        "adoption_digest": environment_adoption.get("adoption_digest"),
    }
    if (
        semantic != digest_bytes(canonical_json_bytes(material))
        or semantic != outcome["receipt_semantic_digest"]
        or receipt.get("receipt_id") != context["receipt_id"]
        or receipt.get("command_id") != request["command_id"]
        or receipt.get("execution_nonce") != outcome["execution_nonce"]
        or receipt.get("execution_status") != outcome["execution_status"]
        or receipt.get("trust_source_ref", {}).get("source_digest")
        != context["snapshot"]["eligibility_source_ref"]["source_digest"]
        or receipt.get("verification_profile_ref", {}).get("content_digest")
        != context["snapshot"]["verification_profile_ref"]["content_digest"]
        or receipt.get("environment_profile_ref", {}).get("basis_digest")
        != context["snapshot"]["environment_profile_ref"]["basis_digest"]
        or receipt.get("adoption_ref") != expected_adoption_ref
    ):
        raise BrokerBoundaryError("u10_worker_receipt_binding_mismatch", run_id)
    _require_time_order(
        ("nonce_recorded_at", context["nonce_record"]["recorded_at"]),
        ("worker_started_at", outcome["started_at"]),
        ("receipt_started_at", receipt["started_at"]),
        ("receipt_finished_at", receipt["finished_at"]),
        ("worker_finished_at", outcome["finished_at"]),
    )
    return receipt, raw


def execute_root_broker_request_v3(request: Mapping[str, Any]) -> dict[str, Any]:
    """Execute one request under the v3 adoption-bound result contract."""

    if os.geteuid() != 0:
        raise BrokerBoundaryError("u10_root_broker_requires_root", str(os.geteuid()))
    with trust_store_coordination_lock(exclusive=False):
        return _execute_root_broker_request_under_lock_v3(request)


def execute_root_broker_request_v2(request: Mapping[str, Any]) -> dict[str, Any]:
    """Reject the retired v2 result contract instead of silently upgrading."""

    del request
    raise BrokerBoundaryError(
        "u10_broker_execution_contract_v2_retired",
        "use execute_root_broker_request_v3",
    )


def _execute_root_broker_request_under_lock_v3(
    request: Mapping[str, Any],
) -> dict[str, Any]:
    context = resolve_trusted_execution_context_v2(request)
    snapshot = context["snapshot"]
    worker = snapshot["worker_runtime"]
    uid = int(snapshot["worker_identity"]["uid"])
    gid = int(snapshot["worker_identity"]["gid"])
    run_id, run_directory, worker_directory = _new_run_directory(
        str(request["entry_id"])
    )
    os.chown(run_directory, 0, gid)
    os.chmod(run_directory, 0o750)
    os.chown(worker_directory, uid, gid)
    os.chmod(worker_directory, 0o700)
    receipt_id = f"receipt.u10.{secrets.token_hex(24)}"
    envelope_id = f"envelope.u10.{secrets.token_hex(24)}"
    output_directory = worker_directory / "occurrence"
    source_root = worker["subject_source_root"]
    adoption_context = _environment_adoption_context_v2(context)
    worker_context = {
        "schema_version": "semantic-guard-u10-worker-context/v2",
        "run_id": run_id,
        "receipt_id": receipt_id,
        "entry_id": request["entry_id"],
        "command_id": request["command_id"],
        "request_nonce": request["request_nonce"],
        "snapshot_root": snapshot["root_storage"]["snapshot_path"],
        "evidence_store_root": str(worker_directory),
        "output_directory": str(output_directory),
        "source_ref": _snapshot_flat_ref(
            snapshot["eligibility_source_ref"], "source_digest"
        ),
        "profile_ref": _snapshot_flat_ref(
            snapshot["verification_profile_ref"], "content_digest"
        ),
        "environment_ref": _snapshot_flat_ref(
            snapshot["environment_profile_ref"], "basis_digest"
        ),
        **adoption_context,
        "worker_identity": {
            "uid": uid,
            "gid": gid,
            "supplementary_gids": snapshot["worker_identity"][
                "effective_supplementary_gids"
            ],
            "umask": snapshot["worker_identity"]["umask"],
        },
        "worker_launch": {
            "worker_version": worker["worker_version"],
            "interpreter_ref": worker["interpreter_snapshot_ref"],
            "entrypoint_ref": worker["worker_entrypoint_snapshot_ref"],
            "python_flags": ["-I", "-S", "-B"],
            "working_directory": snapshot["root_storage"]["snapshot_path"],
            "environment": {
                "PATH": "",
                "LC_ALL": "C",
                "PYTHONDONTWRITEBYTECODE": "1",
            },
            "process_group_policy": (
                "worker_and_inner_runner_share_root_reaped_group/v1"
            ),
        },
        "dependency_import_roots": [
            item["locator"] for item in worker["dependency_import_roots"]
        ],
        "subject_source_root": source_root["locator"],
        "phase_budget": {
            **worker["phase_budget"],
            "governed_command_timeout_seconds": snapshot["command_bindings"][
                str(request["command_id"])
            ]["governed_command_timeout_seconds"],
            "whole_run_timeout_seconds": _whole_worker_timeout_seconds(
                snapshot, str(request["command_id"])
            ),
        },
    }
    context_path = run_directory / "broker-context.json"
    context_raw = (
        json.dumps(
            worker_context,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        ).encode("utf-8")
        + b"\n"
    )
    _write_exclusive(
        context_path,
        context_raw,
        mode=0o640,
    )
    os.chown(context_path, 0, gid)
    interpreter = str(worker["interpreter_snapshot_ref"]["locator"])
    entrypoint = str(worker["worker_entrypoint_snapshot_ref"]["locator"])
    stdout_path = run_directory / "worker-stdout.log"
    stderr_path = run_directory / "worker-stderr.log"
    try:
        with stdout_path.open("xb") as stdout, stderr_path.open("xb") as stderr:
            root_started_at = _utc_now()
            process = subprocess.Popen(
                [
                    interpreter,
                    "-I",
                    "-S",
                    "-B",
                    entrypoint,
                    "--broker-context",
                    str(context_path),
                ],
                cwd=str(snapshot["root_storage"]["snapshot_path"]),
                env={"PATH": "", "LC_ALL": "C", "PYTHONDONTWRITEBYTECODE": "1"},
                stdin=subprocess.DEVNULL,
                stdout=stdout,
                stderr=stderr,
                start_new_session=True,
                user=uid,
                group=gid,
                extra_groups=tuple(
                    snapshot["worker_identity"]["effective_supplementary_gids"]
                ),
                umask=int(snapshot["worker_identity"]["umask"]),
            )
            broker_process_observation = _observe_launched_worker_process(process)
            try:
                exit_code = process.wait(
                    timeout=worker_context["phase_budget"]["whole_run_timeout_seconds"]
                )
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                finally:
                    process.wait()
                _confirm_worker_process_group_absent(process.pid)
                raise BrokerBoundaryError(
                    "u10_worker_whole_run_timed_out",
                    f"{run_id}: {worker_context['phase_budget']!r}",
                )
    except OSError as exc:
        raise BrokerBoundaryError("u10_worker_launch_failed", run_id) from exc
    quiescence_observed_at = _ensure_worker_process_group_quiescent(process.pid)
    if exit_code != 0:
        raise BrokerBoundaryError("u10_worker_failed", f"{run_id}: {exit_code}")
    _freeze_worker_tree(worker_directory, worker_uid=uid)
    outcome_path = worker_directory / "worker-outcome.json"
    outcome_raw = read_protected_file(outcome_path, protected_root=worker_directory)
    try:
        outcome = strict_json_loads(outcome_raw)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise BrokerBoundaryError("u10_worker_outcome_unreadable", run_id) from exc
    context = {**context, "receipt_id": receipt_id}
    receipt, receipt_raw = _validate_worker_outcome(
        outcome,
        context=context,
        run_id=run_id,
        worker_directory=worker_directory,
        broker_process_observation=broker_process_observation,
    )
    context = revalidate_trusted_execution_context_v2(context)
    receipt_ref = {
        "receipt_id": receipt_id,
        "schema_version": "semantic-guard-governed-environment-execution-receipt/v1",
        "locator": outcome["receipt_locator"],
        "artifact_digest": digest_bytes(receipt_raw),
        "semantic_digest": receipt["receipt_digest"],
    }
    worker_outcome_ref = {
        "run_id": run_id,
        "schema_version": "semantic-guard-u10-worker-outcome/v1",
        "locator": str(outcome_path),
        "artifact_digest": digest_bytes(outcome_raw),
        "semantic_digest": digest_bytes(canonical_json_bytes(outcome)),
    }
    broker_context_ref = {
        "run_id": run_id,
        "schema_version": "semantic-guard-u10-worker-context/v2",
        "locator": str(context_path),
        "artifact_digest": digest_bytes(context_raw),
        "semantic_digest": digest_bytes(canonical_json_bytes(worker_context)),
    }
    root_finished_at = _utc_now()
    statement = build_statement_skeleton_v3(
        context=context,
        envelope_id=envelope_id,
        execution_nonce=receipt["execution_nonce"],
        worker_launch_contract=worker_context["worker_launch"],
        worker_reported_observation={
            "process": outcome["launch_observation"],
            "interval": {
                "started_at": outcome["started_at"],
                "finished_at": outcome["finished_at"],
            },
        },
        broker_execution_observation={
            "process": broker_process_observation,
            "exit_code": exit_code,
            "process_group_quiescence": {
                "process_group_id": broker_process_observation["process_group_id"],
                "state": "absent",
                "observed_at": quiescence_observed_at,
            },
        },
        broker_context_ref=broker_context_ref,
        worker_outcome_ref=worker_outcome_ref,
        receipt_ref=receipt_ref,
        receipt_interval={
            "started_at": receipt["started_at"],
            "finished_at": receipt["finished_at"],
        },
        started_at=root_started_at,
        finished_at=root_finished_at,
    )
    envelope = _build_signed_envelope_v3(statement, store=context["store"])
    envelope_path = run_directory / "broker-attested-envelope.json"
    _write_exclusive(
        envelope_path,
        json.dumps(
            envelope,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        ).encode("utf-8")
        + b"\n",
        mode=0o400,
    )
    return envelope
