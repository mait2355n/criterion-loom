#!/usr/bin/env python3
"""Prepare and install a *candidate-only* U-10 root snapshot bundle.

This file deliberately implements two separate trust transitions:

``prepare``
    Runs without privilege.  It copies the selected repository, Python runtime,
    dependency tree, and ``uv`` executable into a closed, digest-bound bundle.

``install``
    Runs only from an exact root-owned bootstrap path.  It accepts a root-owned
    human authorization record for *candidate installation only*, replays the
    closed denominator, and copies it into the fixed U-10 candidate area.

The installer never writes the active trust store or the active snapshot area,
never creates an adoption decision, and never executes payload code as root.
Activation and adoption therefore remain separate operations.
"""

from __future__ import annotations

import argparse
from collections.abc import Iterable, Iterator, Mapping, Sequence
from contextlib import contextmanager
import ctypes
from datetime import datetime, timezone
import errno
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import platform
import pwd
import re
import secrets
import shutil
import stat
import subprocess
import sys
from typing import Any
from urllib.parse import unquote, urlparse
import uuid


U10_ROOT = Path("/Library/Application Support/semantic-guard/u10")
CANDIDATE_ROOT = U10_ROOT / "candidates"
SNAPSHOT_ROOT = U10_ROOT / "snapshots"
TRUST_STORE_PATH = U10_ROOT / "trust-store-current.json"
AUTHORIZATION_ROOT = U10_ROOT / "authorizations"
CANDIDATE_INSTALL_LEDGER_ROOT = U10_ROOT / "activations" / "candidate-installs"
BOOTSTRAP_INSTALLER_PATH = U10_ROOT / "bootstrap" / "prepare_u10_root_candidate.py"
ROOT_INSTALLER_ENTRYPOINT_PATH = (
    U10_ROOT / "bootstrap" / "u10_root_candidate_installer_entrypoint.sh"
)
ROOT_BOOTSTRAP_DISCOVERY_LAUNCHER = Path("/usr/bin/python3")
ROOT_EFFECTIVE_PYTHON_PATH_FILE = U10_ROOT / "bootstrap" / "effective-python.path"
ROOT_BOOTSTRAP_SHELL = Path("/bin/sh")
ROOT_ENVIRONMENT_CLEANER = Path("/usr/bin/env")

BUNDLE_SCHEMA = "semantic-guard-u10-root-candidate-bundle/v1"
AUTHORIZATION_SCHEMA = "semantic-guard-u10-candidate-install-authorization/v1"
CONSUMPTION_SCHEMA = (
    "semantic-guard-u10-candidate-install-authorization-consumption/v1"
)
PROJECTION_SCHEMA = "semantic-guard-u10-candidate-install-projection/v1"
RECEIPT_SCHEMA = "semantic-guard-u10-candidate-install-receipt/v2"
WORKER_ACCOUNT_OBSERVATION_SCHEMA = (
    "semantic-guard-u10-worker-account-observation/v1"
)
MANIFEST_NAME = "bundle-manifest.json"
PROJECTION_NAME = "candidate-install-projection.json"
PYVENV_TEMPLATE = (
    "home = {candidate_payload}/vnext/.venv/bin\n"
    "implementation = CPython\n"
    "include-system-site-packages = false\n"
    "prompt = semantic-guard-u10-candidate\n"
)
DEPENDENCY_ENVIRONMENT_PROFILE = (
    "u10-subject-source-separated-dependency-environment/v1"
)
LOCK_VALIDATION_PROFILE = "uv-sync-offline-frozen-no-install-project/v1"
PROJECT_DISTRIBUTION = "semantic-guard-vnext"
PROJECT_IMPORT_NAME = "semantic_guard_vnext"
EDITABLE_POINTER_NAME = "_editable_impl_semantic_guard_vnext.pth"
ROOT_BROKER_BOOTSTRAP_PATH = "vnext/scripts/u10_root_broker_bootstrap.py"
ROOT_BROKER_ENTRYPOINT_PATH = "vnext/scripts/u10_root_broker_entrypoint.sh"
ROOT_BROKER_OUTER_LAUNCHER_PATH = (
    "vnext/scripts/u10_root_broker_outer_launcher.py"
)
ROOT_INSTALLER_ENTRYPOINT_SOURCE_PATH = (
    "vnext/scripts/u10_root_candidate_installer_entrypoint.sh"
)
SNAPSHOT_SOURCE_ROOT = "vnext/src"
LOCK_CHECK_ARGUMENTS = (
    "sync",
    "--check",
    "--offline",
    "--frozen",
    "--no-install-project",
    "--python",
    "{candidate_payload}/vnext/.venv/bin/python",
    "--extra",
    "nlp-ja",
    "--extra",
    "nlp-ja-dependency",
)
SNAPSHOT_ACTIVATION_FOLLOW_UP = (
    "independent inactive snapshot projection, non-root final-path "
    "uv sync --check --offline --frozen --no-install-project lock validation, "
    "post-relocation closed-denominator sealing, schema validation, immutability "
    "verification, and human adoption"
)

_STABLE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}$")
_LEDGER_COMPONENT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,199}$")
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_ENTITY_REF = re.compile(
    r"^.{1,200}・[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
U10_SUBJECT_ENTITY_ID = "acfb8b85-2f75-5e82-a641-b3b3b6e023d6"
_NON_LOGIN_SHELLS = frozenset(
    {"/bin/false", "/usr/bin/false", "/sbin/nologin", "/usr/sbin/nologin"}
)
_PREPARE_EXCLUDED_NAMES = frozenset({"__pycache__"})


def _candidate_install_ledger_policy_v1() -> dict[str, Any]:
    return {
        "profile": "append-only-candidate-install-transaction-ledger/v1",
        "record_set": [
            "immutable_authorization_copy",
            "prepublication_authorization_consumption",
            "postpublication_occurrence_receipt",
        ],
        "publication": (
            "complete_file_fsync_atomic_link_no_replace_directory_fsync"
        ),
        "coordination": (
            "target_bundle_flock_with_per_authorization_stale_stage_cleanup"
        ),
        "retention": (
            "retain_authorization_consumption_and_receipt_while_candidate_or_"
            "downstream_evidence_is_referenced"
        ),
        "temporary_artifacts": (
            "non_occurrence_cleanup_under_target_bundle_transaction_lock"
        ),
    }


class CandidateBoundaryError(RuntimeError):
    """Fail-closed candidate preparation/installation error."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


def _strict_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise json.JSONDecodeError(f"duplicate object key: {key!r}", key, 0)
        value[key] = item
    return value


def _reject_nonfinite_json_constant(value: str) -> Any:
    raise json.JSONDecodeError(f"non-finite JSON number: {value}", value, 0)


def _strict_json_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise json.JSONDecodeError(f"non-finite JSON number: {value}", value, 0)
    return parsed


def strict_json_loads(raw: str | bytes | bytearray) -> Any:
    return json.loads(
        raw,
        object_pairs_hook=_strict_json_object,
        parse_constant=_reject_nonfinite_json_constant,
        parse_float=_strict_json_float,
    )


def _assert_no_extended_acl(path: Path, *, code: str) -> None:
    if sys.platform != "darwin":
        return
    libc = ctypes.CDLL(None, use_errno=True)
    acl_get_link = libc.acl_get_link_np
    acl_get_link.argtypes = [ctypes.c_char_p, ctypes.c_int]
    acl_get_link.restype = ctypes.c_void_p
    acl_free = libc.acl_free
    acl_free.argtypes = [ctypes.c_void_p]
    acl_free.restype = ctypes.c_int
    ctypes.set_errno(0)
    acl = acl_get_link(os.fsencode(path), 0x00000100)
    if acl:
        acl_free(acl)
        raise CandidateBoundaryError(code, str(path))
    observed_errno = ctypes.get_errno()
    if observed_errno != errno.ENOENT:
        raise CandidateBoundaryError(
            "candidate_acl_observation_failed",
            f"{path}: errno={observed_errno}",
        )


def _validate_os_injected_environment_v1(
    environment: Mapping[str, str], *, expected: Mapping[str, str], code: str
) -> None:
    observed = dict(environment)
    injected = observed.pop("__CF_USER_TEXT_ENCODING", None)
    if injected is not None:
        matched = re.fullmatch(
            r"0x([0-9A-Fa-f]+):0x[0-9A-Fa-f]+:0x[0-9A-Fa-f]+",
            injected,
        )
        if matched is None or int(matched.group(1), 16) != os.geteuid():
            raise CandidateBoundaryError(code, repr(environment))
    if observed != dict(expected):
        raise CandidateBoundaryError(code, repr(environment))


def _discover_effective_bootstrap_python_v1() -> Path:
    """Resolve the xcrun discovery launcher, then qualify direct execution."""

    expected_environment = {
        "PATH": "",
        "LC_ALL": "C",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    probe = (
        "import json, os, pathlib, sys; "
        "print(json.dumps({'executable': "
        "str(pathlib.Path(sys.executable).resolve()), "
        "'environment': dict(os.environ)}, sort_keys=True, allow_nan=False))"
    )

    def run(path: Path) -> dict[str, Any]:
        try:
            completed = subprocess.run(
                [str(path), "-I", "-S", "-B", "-c", probe],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=30,
                env=expected_environment,
                text=True,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise CandidateBoundaryError(
                "candidate_bootstrap_interpreter_discovery_failed", str(path)
            ) from exc
        if completed.returncode != 0:
            raise CandidateBoundaryError(
                "candidate_bootstrap_interpreter_discovery_failed",
                completed.stderr[:1000],
            )
        try:
            value = strict_json_loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise CandidateBoundaryError(
                "candidate_bootstrap_interpreter_discovery_failed",
                completed.stdout[:1000],
            ) from exc
        if not isinstance(value, dict) or set(value) != {"executable", "environment"}:
            raise CandidateBoundaryError(
                "candidate_bootstrap_interpreter_discovery_failed", repr(value)
            )
        environment = value["environment"]
        if not isinstance(environment, dict) or not all(
            isinstance(key, str) and isinstance(item, str)
            for key, item in environment.items()
        ):
            raise CandidateBoundaryError(
                "candidate_bootstrap_interpreter_discovery_failed", repr(environment)
            )
        # xcrun may enrich discovery.  Direct execution below must not.
        if path != ROOT_BOOTSTRAP_DISCOVERY_LAUNCHER:
            _validate_os_injected_environment_v1(
                environment,
                expected=expected_environment,
                code="candidate_effective_interpreter_environment_untrusted",
            )
        return value

    discovered = run(ROOT_BOOTSTRAP_DISCOVERY_LAUNCHER)
    try:
        effective = Path(str(discovered["executable"])).resolve(strict=True)
    except OSError as exc:
        raise CandidateBoundaryError(
            "candidate_bootstrap_interpreter_discovery_failed",
            repr(discovered.get("executable")),
        ) from exc
    if (
        not effective.is_absolute()
        or effective != Path(os.path.normpath(str(effective)))
        or effective.is_symlink()
    ):
        raise CandidateBoundaryError(
            "candidate_effective_interpreter_untrusted", str(effective)
        )
    direct = run(effective)
    if Path(str(direct["executable"])) != effective:
        raise CandidateBoundaryError(
            "candidate_effective_interpreter_identity_mismatch", str(effective)
        )
    return effective


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def digest_bytes(value: bytes) -> dict[str, str]:
    return {"algorithm": "sha256", "value": hashlib.sha256(value).hexdigest()}


def sealed_digest(value: Mapping[str, Any], field: str) -> dict[str, str]:
    material = dict(value)
    material.pop(field, None)
    return digest_bytes(canonical_json_bytes(material))


def _json_record_bytes_v1(value: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        ).encode("utf-8")
        + b"\n"
    )


def _utc_now_v1() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_rfc3339_v1(value: Any, *, code: str) -> datetime:
    if not isinstance(value, str) or not value or len(value) > 64:
        raise CandidateBoundaryError(code, repr(value))
    try:
        observed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CandidateBoundaryError(code, value) from exc
    if observed.tzinfo is None or observed.utcoffset() is None:
        raise CandidateBoundaryError(code, value)
    return observed.astimezone(timezone.utc)


def _require_exact_fields(
    value: Mapping[str, Any], expected: set[str], code: str
) -> None:
    if set(value) != expected:
        raise CandidateBoundaryError(
            code,
            f"expected={sorted(expected)!r}; observed={sorted(value)!r}",
        )


def _require_digest(value: Any, code: str) -> dict[str, str]:
    if (
        not isinstance(value, Mapping)
        or set(value) != {"algorithm", "value"}
        or value.get("algorithm") != "sha256"
        or not isinstance(value.get("value"), str)
        or _DIGEST.fullmatch(str(value["value"])) is None
    ):
        raise CandidateBoundaryError(code, repr(value))
    return dict(value)


def _safe_relative_path(raw: str, *, code: str) -> PurePosixPath:
    if not isinstance(raw, str) or not raw or "\x00" in raw or "\\" in raw:
        raise CandidateBoundaryError(code, repr(raw))
    path = PurePosixPath(raw)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise CandidateBoundaryError(code, raw)
    if path.as_posix() != raw:
        raise CandidateBoundaryError(code, raw)
    return path


def _require_entity_ref_v1(value: Any, *, code: str) -> str:
    if not isinstance(value, str) or _ENTITY_REF.fullmatch(value) is None:
        raise CandidateBoundaryError(code, repr(value))
    return value


def _entity_id_v1(value: Any, *, code: str) -> str:
    reference = _require_entity_ref_v1(value, code=code)
    return reference.rsplit("・", 1)[1]


def _require_distinct_entity_refs_v1(
    references: Mapping[str, Any], *, code: str
) -> None:
    identities: dict[str, str] = {}
    for field, reference in references.items():
        entity_id = _entity_id_v1(reference, code=code)
        previous = identities.get(entity_id)
        if previous is not None:
            raise CandidateBoundaryError(
                code, f"{previous} and {field} reuse entity_id={entity_id}"
            )
        identities[entity_id] = field


def _host_platform_material_v1() -> dict[str, Any]:
    material: dict[str, Any] = {
        "os": platform.system(),
        "architecture": platform.machine(),
        "os_release": platform.release(),
        "platform_version": platform.version(),
        "hostname": platform.node(),
    }
    if any(not isinstance(value, str) or not value for value in material.values()):
        raise CandidateBoundaryError(
            "candidate_worker_account_observation_failed", "platform binding"
        )
    material["host_identity_digest"] = digest_bytes(canonical_json_bytes(material))
    return material


def _worker_account_material_v1(account_name: str) -> dict[str, Any]:
    if not isinstance(account_name, str) or not account_name:
        raise CandidateBoundaryError(
            "candidate_worker_account_observation_failed", repr(account_name)
        )
    try:
        account = pwd.getpwnam(account_name)
        all_group_ids = sorted(set(os.getgrouplist(account.pw_name, account.pw_gid)))
    except (KeyError, OSError) as exc:
        raise CandidateBoundaryError(
            "candidate_worker_account_observation_failed", account_name
        ) from exc
    return {
        "account_name": account.pw_name,
        "uid": account.pw_uid,
        "gid": account.pw_gid,
        "account_supplementary_gids": [
            group_id for group_id in all_group_ids if group_id != account.pw_gid
        ],
        "login_shell": account.pw_shell,
        "home_directory": account.pw_dir,
        "non_login": account.pw_shell in _NON_LOGIN_SHELLS,
        "platform_binding": _host_platform_material_v1(),
    }


def _principal_entity_ref_v1(account: Mapping[str, Any]) -> str:
    host_digest = _require_digest(
        account["platform_binding"]["host_identity_digest"],
        "candidate_worker_account_observation_invalid",
    )["value"]
    principal_id = uuid.uuid5(
        uuid.NAMESPACE_URL,
        (
            "https://semantic-guard.local/entities/u10-worker-principal/"
            f"{host_digest}/{account['uid']}"
        ),
    )
    return f"U-10 worker principal {account['account_name']}・{principal_id}"


def _observation_material_v1(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "account_name": value["account_name"],
        "uid": value["uid"],
        "gid": value["gid"],
        "account_supplementary_gids": value["account_supplementary_gids"],
        "login_shell": value["login_shell"],
        "home_directory": value["home_directory"],
        "non_login": value["non_login"],
        "platform_binding": value["platform_binding"],
    }


def _require_artifact_ref_v1(value: Any, *, code: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise CandidateBoundaryError(code, repr(value))
    _require_exact_fields(
        value,
        {"record_id", "locator", "artifact_digest", "semantic_digest"},
        code,
    )
    if (
        not isinstance(value.get("record_id"), str)
        or _STABLE_ID.fullmatch(str(value["record_id"])) is None
        or not isinstance(value.get("locator"), str)
        or not value["locator"]
    ):
        raise CandidateBoundaryError(code, repr(value))
    _require_digest(value.get("artifact_digest"), code)
    _require_digest(value.get("semantic_digest"), code)
    return dict(value)


def _read_absolute_nonsymlink_evidence_v1(
    locator: Any, *, code: str
) -> tuple[bytes, Path]:
    if not isinstance(locator, str) or not locator:
        raise CandidateBoundaryError(code, repr(locator))
    path = Path(locator)
    if (
        not path.is_absolute()
        or path != Path(os.path.normpath(str(path)))
        or str(path) != locator
    ):
        raise CandidateBoundaryError(code, f"non-canonical absolute locator: {locator}")
    current = Path(path.anchor)
    for index, part in enumerate(path.parts[1:], start=1):
        current /= part
        try:
            observed = current.lstat()
        except OSError as exc:
            raise CandidateBoundaryError(code, str(current)) from exc
        if stat.S_ISLNK(observed.st_mode):
            raise CandidateBoundaryError(code, f"symlink component: {current}")
        if index < len(path.parts) - 1 and not stat.S_ISDIR(observed.st_mode):
            raise CandidateBoundaryError(code, f"non-directory component: {current}")
    raw, resolved, _observed = _read_stable_regular(path)
    if resolved != path:
        raise CandidateBoundaryError(code, f"locator changed on resolution: {path}")
    return raw, resolved


def validate_preactivation_decision_evidence_v1(
    value: Mapping[str, Any]
) -> None:
    """Resolve both decision evidence locators and verify their exact bytes.

    Version 1 intentionally permits only canonical absolute, entirely
    non-symlink local paths.  Repository-relative or search-path resolution is
    not part of this contract and must not be guessed by a caller.
    """

    validate_preactivation_decision_v1(value)
    for field in ("decision_evidence_ref", "trusted_entrypoint_ref"):
        reference = value[field]
        raw, _resolved = _read_absolute_nonsymlink_evidence_v1(
            reference["locator"],
            code="candidate_preactivation_decision_evidence_unavailable",
        )
        if digest_bytes(raw) != reference["content_digest"]:
            raise CandidateBoundaryError(
                "candidate_preactivation_decision_evidence_digest_mismatch",
                field,
            )


def validate_preactivation_decision_v1(value: Mapping[str, Any]) -> None:
    _require_exact_fields(
        value,
        {
            "schema_version",
            "decision_id",
            "decision_version",
            "record_kind",
            "notation_profile",
            "decision_entity_ref",
            "subject_entity_ref",
            "human_decision",
            "decision_owner",
            "threat_boundary_selection",
            "worker_identity_selection",
            "decision_evidence_ref",
            "trusted_entrypoint_ref",
            "recorded_at",
            "requalification_triggers",
            "u4_principal_authenticity",
            "authority_scope",
            "formal_authority",
            "positive_assurance_allowed",
            "decision_digest",
        },
        "candidate_preactivation_decision_invalid",
    )
    decision_entity_id = _entity_id_v1(
        value.get("decision_entity_ref"),
        code="candidate_preactivation_decision_invalid",
    )
    subject_entity_id = _entity_id_v1(
        value.get("subject_entity_ref"),
        code="candidate_preactivation_decision_invalid",
    )
    if (
        subject_entity_id != U10_SUBJECT_ENTITY_ID
        or decision_entity_id == subject_entity_id
    ):
        raise CandidateBoundaryError(
            "candidate_preactivation_decision_entity_invalid",
            f"decision={decision_entity_id}; subject={subject_entity_id}",
        )
    decision_evidence = value.get("decision_evidence_ref")
    trusted_entrypoint = value.get("trusted_entrypoint_ref")
    if not isinstance(decision_evidence, Mapping) or not isinstance(
        trusted_entrypoint, Mapping
    ):
        raise CandidateBoundaryError(
            "candidate_preactivation_decision_invalid", "evidence reference shape"
        )
    _require_exact_fields(
        decision_evidence,
        {"record_id", "locator", "content_digest", "trust_domain"},
        "candidate_preactivation_decision_invalid",
    )
    _require_exact_fields(
        trusted_entrypoint,
        {"record_id", "locator", "content_digest"},
        "candidate_preactivation_decision_invalid",
    )
    for reference in (decision_evidence, trusted_entrypoint):
        if (
            not isinstance(reference.get("record_id"), str)
            or _STABLE_ID.fullmatch(str(reference["record_id"])) is None
            or not isinstance(reference.get("locator"), str)
            or not reference["locator"]
        ):
            raise CandidateBoundaryError(
                "candidate_preactivation_decision_invalid", repr(reference)
            )
        _require_digest(
            reference.get("content_digest"),
            "candidate_preactivation_decision_invalid",
        )
    if (
        not isinstance(decision_evidence.get("trust_domain"), str)
        or _STABLE_ID.fullmatch(str(decision_evidence["trust_domain"])) is None
    ):
        raise CandidateBoundaryError(
            "candidate_preactivation_decision_invalid", repr(decision_evidence)
        )
    threat = value.get("threat_boundary_selection")
    worker = value.get("worker_identity_selection")
    decision = value.get("human_decision")
    expected_triggers = [
        "threat_boundary_change",
        "worker_identity_policy_change",
        "principal_resolution_change",
        "host_or_os_change",
        "sandbox_or_external_executor_change",
        "qualified_test_denominator_change",
    ]
    valid_selection = (
        threat == "local_bounded_repository_suite_only"
        and worker
        in {
            "dedicated_non_login_service_principal",
            "current_user_501_20_empty_supplementary_groups",
        }
        and decision == "accept"
    ) or (
        threat == "local_bounded_repository_suite_only"
        and worker == "defer"
        and decision == "defer"
    ) or (
        threat == "hostile_code_in_scope_requires_external_executor"
        and worker is None
        and decision == "accept"
    ) or (threat == "defer" and worker is None and decision == "defer")
    if (
        value.get("schema_version")
        != "semantic-guard-u10-preactivation-decision/v1"
        or value.get("record_kind") != "u10_preactivation_scope_decision"
        or value.get("notation_profile") != "entity-reference-notation/v0"
        or not isinstance(value.get("decision_id"), str)
        or _STABLE_ID.fullmatch(str(value["decision_id"])) is None
        or not isinstance(value.get("decision_version"), str)
        or not value["decision_version"]
        or value.get("decision_owner") != "human"
        or not valid_selection
        or value.get("requalification_triggers") != expected_triggers
        or value.get("u4_principal_authenticity") != "unresolved"
        or value.get("authority_scope")
        != "u10_preactivation_scope_selection_only"
        or value.get("formal_authority") != "human_scope_selection_only"
        or value.get("positive_assurance_allowed") is not False
    ):
        raise CandidateBoundaryError(
            "candidate_preactivation_decision_invalid", "binding or authority"
        )
    _parse_rfc3339_v1(
        value.get("recorded_at"), code="candidate_preactivation_decision_time_invalid"
    )
    if _require_digest(
        value.get("decision_digest"),
        "candidate_preactivation_decision_digest_invalid",
    ) != sealed_digest(value, "decision_digest"):
        raise CandidateBoundaryError(
            "candidate_preactivation_decision_digest_mismatch",
            str(value.get("decision_id")),
        )


def build_worker_account_observation_v1(
    *,
    decision: Mapping[str, Any],
    decision_raw: bytes,
    decision_locator: Path,
    account_name: str,
    observed_at: str | None = None,
    observation_entity_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Observe an OS account selected by an existing human decision.

    The function records facts only.  It cannot create, upgrade, or replace the
    human decision and grants no execution or assurance authority.
    """

    validate_preactivation_decision_evidence_v1(decision)
    if (
        decision["threat_boundary_selection"]
        != "local_bounded_repository_suite_only"
        or decision["human_decision"] != "accept"
        or decision["worker_identity_selection"] == "defer"
    ):
        raise CandidateBoundaryError(
            "candidate_worker_observation_scope_not_selected",
            str(decision["threat_boundary_selection"]),
        )
    exact_decision_locator = decision_locator.resolve(strict=True)
    account = _worker_account_material_v1(account_name)
    selection = decision["worker_identity_selection"]
    if selection == "current_user_501_20_empty_supplementary_groups" and (
        account["uid"] != 501 or account["gid"] != 20
    ):
        raise CandidateBoundaryError(
            "candidate_worker_account_policy_mismatch",
            f"{account['uid']}:{account['gid']}",
        )
    if (
        selection == "dedicated_non_login_service_principal"
        and account["non_login"] is not True
    ):
        raise CandidateBoundaryError(
            "candidate_worker_account_policy_mismatch", account["login_shell"]
        )
    observation_uuid = observation_entity_id or uuid.uuid4()
    observation_time = observed_at or _utc_now_v1()
    _parse_rfc3339_v1(
        observation_time, code="candidate_worker_account_observation_time_invalid"
    )
    observation: dict[str, Any] = {
        "schema_version": WORKER_ACCOUNT_OBSERVATION_SCHEMA,
        "observation_id": f"observation.u10.worker-account.{observation_uuid}",
        "observation_version": "1.0.0",
        "record_kind": "u10_worker_account_observation",
        "notation_profile": "entity-reference-notation/v0",
        "observation_entity_ref": (
            f"U-10 worker account observation・{observation_uuid}"
        ),
        "subject_entity_ref": decision["subject_entity_ref"],
        "derived_from": decision["decision_entity_ref"],
        "decision_record_ref": {
            "record_id": decision["decision_id"],
            "locator": str(exact_decision_locator),
            "artifact_digest": digest_bytes(decision_raw),
            "semantic_digest": decision["decision_digest"],
        },
        "worker_identity_selection": selection,
        "principal_entity_ref": _principal_entity_ref_v1(account),
        **account,
        "observation_method": "python_pwd_getgrouplist_platform_local/v1",
        "observed_at": observation_time,
        "formal_authority": "none",
        "positive_assurance_allowed": False,
    }
    observation["observation_digest"] = sealed_digest(
        observation, "observation_digest"
    )
    validate_worker_account_observation_v1(
        observation,
        decision=decision,
        decision_raw=decision_raw,
        decision_locator=exact_decision_locator,
        reobserve_current=False,
    )
    return observation


def validate_worker_account_observation_v1(
    value: Mapping[str, Any],
    *,
    decision: Mapping[str, Any],
    decision_raw: bytes,
    decision_locator: Path,
    reobserve_current: bool,
) -> None:
    _require_exact_fields(
        value,
        {
            "schema_version",
            "observation_id",
            "observation_version",
            "record_kind",
            "notation_profile",
            "observation_entity_ref",
            "subject_entity_ref",
            "derived_from",
            "decision_record_ref",
            "worker_identity_selection",
            "principal_entity_ref",
            "account_name",
            "uid",
            "gid",
            "account_supplementary_gids",
            "login_shell",
            "home_directory",
            "non_login",
            "platform_binding",
            "observation_method",
            "observed_at",
            "formal_authority",
            "positive_assurance_allowed",
            "observation_digest",
        },
        "candidate_worker_account_observation_invalid",
    )
    validate_preactivation_decision_v1(decision)
    decision_ref = _require_artifact_ref_v1(
        value.get("decision_record_ref"),
        code="candidate_worker_account_observation_invalid",
    )
    exact_decision_ref = {
        "record_id": decision["decision_id"],
        "locator": str(decision_locator),
        "artifact_digest": digest_bytes(decision_raw),
        "semantic_digest": decision["decision_digest"],
    }
    platform_binding = value.get("platform_binding")
    if not isinstance(platform_binding, Mapping):
        raise CandidateBoundaryError(
            "candidate_worker_account_observation_invalid", "platform binding"
        )
    _require_exact_fields(
        platform_binding,
        {
            "os",
            "architecture",
            "os_release",
            "platform_version",
            "hostname",
            "host_identity_digest",
        },
        "candidate_worker_account_observation_invalid",
    )
    host_material = {
        field: platform_binding[field]
        for field in (
            "os",
            "architecture",
            "os_release",
            "platform_version",
            "hostname",
        )
    }
    if any(
        not isinstance(item, str) or not item for item in host_material.values()
    ) or _require_digest(
        platform_binding.get("host_identity_digest"),
        "candidate_worker_account_observation_invalid",
    ) != digest_bytes(canonical_json_bytes(host_material)):
        raise CandidateBoundaryError(
            "candidate_worker_account_observation_host_invalid",
            str(value.get("observation_id")),
        )
    observation_entity_ref = _require_entity_ref_v1(
        value.get("observation_entity_ref"),
        code="candidate_worker_account_observation_invalid",
    )
    principal_entity_ref = _require_entity_ref_v1(
        value.get("principal_entity_ref"),
        code="candidate_worker_account_observation_invalid",
    )
    _require_distinct_entity_refs_v1(
        {
            "decision_entity_ref": decision["decision_entity_ref"],
            "subject_entity_ref": decision["subject_entity_ref"],
            "observation_entity_ref": observation_entity_ref,
            "principal_entity_ref": principal_entity_ref,
        },
        code="candidate_worker_account_observation_entity_invalid",
    )
    account_groups = value.get("account_supplementary_gids")
    if (
        value.get("schema_version") != WORKER_ACCOUNT_OBSERVATION_SCHEMA
        or value.get("record_kind") != "u10_worker_account_observation"
        or value.get("notation_profile") != "entity-reference-notation/v0"
        or not isinstance(value.get("observation_id"), str)
        or _STABLE_ID.fullmatch(str(value["observation_id"])) is None
        or not isinstance(value.get("observation_version"), str)
        or not value["observation_version"]
        or _entity_id_v1(
            value.get("subject_entity_ref"),
            code="candidate_worker_account_observation_invalid",
        )
        != _entity_id_v1(
            decision["subject_entity_ref"],
            code="candidate_worker_account_observation_invalid",
        )
        or _entity_id_v1(
            value.get("derived_from"),
            code="candidate_worker_account_observation_invalid",
        )
        != _entity_id_v1(
            decision["decision_entity_ref"],
            code="candidate_worker_account_observation_invalid",
        )
        or decision_ref != exact_decision_ref
        or value.get("worker_identity_selection")
        != decision.get("worker_identity_selection")
        or not isinstance(value.get("account_name"), str)
        or not value["account_name"]
        or not isinstance(value.get("uid"), int)
        or isinstance(value.get("uid"), bool)
        or value["uid"] <= 0
        or not isinstance(value.get("gid"), int)
        or isinstance(value.get("gid"), bool)
        or value["gid"] <= 0
        or not isinstance(account_groups, list)
        or any(
            not isinstance(group_id, int)
            or isinstance(group_id, bool)
            or group_id <= 0
            for group_id in account_groups
        )
        or account_groups != sorted(set(account_groups))
        or value["gid"] in account_groups
        or not isinstance(value.get("login_shell"), str)
        or not value["login_shell"]
        or not isinstance(value.get("home_directory"), str)
        or not value["home_directory"]
        or value.get("non_login") != (value["login_shell"] in _NON_LOGIN_SHELLS)
        or value.get("observation_method")
        != "python_pwd_getgrouplist_platform_local/v1"
        or value.get("formal_authority") != "none"
        or value.get("positive_assurance_allowed") is not False
    ):
        raise CandidateBoundaryError(
            "candidate_worker_account_observation_invalid", "binding or facts"
        )
    if _entity_id_v1(
        principal_entity_ref,
        code="candidate_worker_account_observation_invalid",
    ) != _entity_id_v1(
        _principal_entity_ref_v1(_observation_material_v1(value)),
        code="candidate_worker_account_observation_invalid",
    ):
        raise CandidateBoundaryError(
            "candidate_worker_account_principal_identity_mismatch",
            principal_entity_ref,
        )
    selection = value["worker_identity_selection"]
    if selection == "current_user_501_20_empty_supplementary_groups" and (
        value["uid"] != 501 or value["gid"] != 20
    ):
        raise CandidateBoundaryError(
            "candidate_worker_account_policy_mismatch",
            f"{value['uid']}:{value['gid']}",
        )
    if (
        selection == "dedicated_non_login_service_principal"
        and value["non_login"] is not True
    ):
        raise CandidateBoundaryError(
            "candidate_worker_account_policy_mismatch", value["login_shell"]
        )
    decision_time = _parse_rfc3339_v1(
        decision["recorded_at"], code="candidate_preactivation_decision_time_invalid"
    )
    observed_time = _parse_rfc3339_v1(
        value.get("observed_at"),
        code="candidate_worker_account_observation_time_invalid",
    )
    if observed_time < decision_time:
        raise CandidateBoundaryError(
            "candidate_worker_account_observation_chronology_invalid",
            str(value.get("observation_id")),
        )
    if _require_digest(
        value.get("observation_digest"),
        "candidate_worker_account_observation_digest_invalid",
    ) != sealed_digest(value, "observation_digest"):
        raise CandidateBoundaryError(
            "candidate_worker_account_observation_digest_mismatch",
            str(value.get("observation_id")),
        )
    if reobserve_current:
        observed_now = _worker_account_material_v1(value["account_name"])
        if observed_now != _observation_material_v1(value):
            raise CandidateBoundaryError(
                "candidate_worker_account_requalification_required",
                str(value.get("observation_id")),
            )


def build_worker_principal_resolution_v1(
    *,
    decision: Mapping[str, Any],
    decision_raw: bytes,
    decision_locator: Path,
    observation: Mapping[str, Any],
    observation_raw: bytes,
    observation_locator: Path,
    resolved_at: str | None = None,
    resolution_entity_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    exact_decision_locator = decision_locator.resolve(strict=True)
    exact_observation_locator = observation_locator.resolve(strict=True)
    validate_worker_account_observation_v1(
        observation,
        decision=decision,
        decision_raw=decision_raw,
        decision_locator=exact_decision_locator,
        reobserve_current=True,
    )
    resolution_uuid = resolution_entity_id or uuid.uuid4()
    resolution_time = resolved_at or _utc_now_v1()
    resolution: dict[str, Any] = {
        "schema_version": "semantic-guard-u10-worker-principal-resolution/v1",
        "resolution_id": f"resolution.u10.worker-principal.{resolution_uuid}",
        "resolution_version": "1.0.0",
        "record_kind": "u10_worker_principal_resolution",
        "notation_profile": "entity-reference-notation/v0",
        "resolution_entity_ref": f"U-10 worker principal resolution・{resolution_uuid}",
        "subject_entity_ref": decision["subject_entity_ref"],
        "decision_record_ref": observation["decision_record_ref"],
        "account_observation_ref": {
            "record_id": observation["observation_id"],
            "locator": str(exact_observation_locator),
            "artifact_digest": digest_bytes(observation_raw),
            "semantic_digest": observation["observation_digest"],
        },
        "derived_from": observation["observation_entity_ref"],
        "worker_identity_selection": observation["worker_identity_selection"],
        "resolution_state": "resolved",
        "principal_entity_ref": observation["principal_entity_ref"],
        "account_name": observation["account_name"],
        "uid": observation["uid"],
        "gid": observation["gid"],
        "account_supplementary_gids": observation[
            "account_supplementary_gids"
        ],
        "effective_supplementary_gids": [],
        "umask": 0o77,
        "login_shell": observation["login_shell"],
        "non_login": observation["non_login"],
        "platform_binding": observation["platform_binding"],
        "resolved_at": resolution_time,
        "formal_authority": "none",
        "positive_assurance_allowed": False,
    }
    resolution["resolution_digest"] = sealed_digest(
        resolution, "resolution_digest"
    )
    validate_worker_principal_resolution_v1(
        resolution,
        decision=decision,
        decision_raw=decision_raw,
        decision_locator=exact_decision_locator,
        observation=observation,
        observation_raw=observation_raw,
        observation_locator=exact_observation_locator,
        reobserve_current=True,
    )
    return resolution


def validate_worker_principal_resolution_v1(
    value: Mapping[str, Any],
    *,
    decision: Mapping[str, Any],
    decision_raw: bytes,
    decision_locator: Path,
    observation: Mapping[str, Any] | None = None,
    observation_raw: bytes | None = None,
    observation_locator: Path | None = None,
    reobserve_current: bool = False,
) -> None:
    _require_exact_fields(
        value,
        {
            "schema_version",
            "resolution_id",
            "resolution_version",
            "record_kind",
            "notation_profile",
            "resolution_entity_ref",
            "subject_entity_ref",
            "decision_record_ref",
            "account_observation_ref",
            "derived_from",
            "worker_identity_selection",
            "resolution_state",
            "principal_entity_ref",
            "account_name",
            "uid",
            "gid",
            "account_supplementary_gids",
            "effective_supplementary_gids",
            "umask",
            "login_shell",
            "non_login",
            "platform_binding",
            "resolved_at",
            "formal_authority",
            "positive_assurance_allowed",
            "resolution_digest",
        },
        "candidate_worker_principal_resolution_invalid",
    )
    decision_ref = _require_artifact_ref_v1(
        value.get("decision_record_ref"),
        code="candidate_worker_principal_resolution_invalid",
    )
    account_ref = value.get("account_observation_ref")
    selection = value.get("worker_identity_selection")
    resolved = value.get("resolution_state") == "resolved"
    if resolved:
        if (
            observation is None
            or observation_raw is None
            or observation_locator is None
            or account_ref is None
        ):
            raise CandidateBoundaryError(
                "candidate_worker_principal_resolution_invalid",
                "resolved principal lacks exact account observation",
            )
        account_ref = _require_artifact_ref_v1(
            account_ref,
            code="candidate_worker_principal_resolution_invalid",
        )
        validate_worker_account_observation_v1(
            observation,
            decision=decision,
            decision_raw=decision_raw,
            decision_locator=decision_locator,
            reobserve_current=reobserve_current,
        )
    elif any(
        value.get(field) is not None
        for field in (
            "account_observation_ref",
            "principal_entity_ref",
            "account_name",
            "uid",
            "gid",
            "account_supplementary_gids",
            "effective_supplementary_gids",
            "umask",
            "login_shell",
            "non_login",
            "platform_binding",
            "resolved_at",
        )
    ):
        raise CandidateBoundaryError(
            "candidate_worker_principal_resolution_invalid",
            "pending resolution contains invented principal facts",
        )
    exact_decision_ref = {
        "record_id": decision["decision_id"],
        "locator": str(decision_locator),
        "artifact_digest": digest_bytes(decision_raw),
        "semantic_digest": decision["decision_digest"],
    }
    if (
        value.get("schema_version")
        != "semantic-guard-u10-worker-principal-resolution/v1"
        or value.get("record_kind") != "u10_worker_principal_resolution"
        or value.get("notation_profile") != "entity-reference-notation/v0"
        or not isinstance(value.get("resolution_id"), str)
        or _STABLE_ID.fullmatch(str(value["resolution_id"])) is None
        or not isinstance(value.get("resolution_version"), str)
        or not value["resolution_version"]
        or _entity_id_v1(
            value.get("subject_entity_ref"),
            code="candidate_worker_principal_resolution_invalid",
        )
        != _entity_id_v1(
            decision.get("subject_entity_ref"),
            code="candidate_worker_principal_resolution_invalid",
        )
        or decision_ref != exact_decision_ref
        or selection != decision.get("worker_identity_selection")
        or selection
        not in {
            "dedicated_non_login_service_principal",
            "current_user_501_20_empty_supplementary_groups",
        }
        or value.get("resolution_state")
        not in {"pending_principal_provisioning", "resolved"}
        or value.get("formal_authority") != "none"
        or value.get("positive_assurance_allowed") is not False
    ):
        raise CandidateBoundaryError(
            "candidate_worker_principal_resolution_invalid", "binding or authority"
        )
    if resolved:
        assert observation is not None
        assert observation_raw is not None
        assert observation_locator is not None
        assert isinstance(account_ref, Mapping)
        exact_observation_ref = {
            "record_id": observation["observation_id"],
            "locator": str(observation_locator),
            "artifact_digest": digest_bytes(observation_raw),
            "semantic_digest": observation["observation_digest"],
        }
        resolution_entity_ref = _require_entity_ref_v1(
            value.get("resolution_entity_ref"),
            code="candidate_worker_principal_resolution_invalid",
        )
        principal_entity_ref = _require_entity_ref_v1(
            value.get("principal_entity_ref"),
            code="candidate_worker_principal_resolution_invalid",
        )
        _require_distinct_entity_refs_v1(
            {
                "decision_entity_ref": decision["decision_entity_ref"],
                "subject_entity_ref": decision["subject_entity_ref"],
                "observation_entity_ref": observation["observation_entity_ref"],
                "resolution_entity_ref": resolution_entity_ref,
                "principal_entity_ref": principal_entity_ref,
            },
            code="candidate_worker_principal_resolution_entity_invalid",
        )
        uid = value.get("uid")
        gid = value.get("gid")
        if (
            account_ref != exact_observation_ref
            or _entity_id_v1(
                value.get("derived_from"),
                code="candidate_worker_principal_resolution_invalid",
            )
            != _entity_id_v1(
                observation.get("observation_entity_ref"),
                code="candidate_worker_principal_resolution_invalid",
            )
            or _entity_id_v1(
                value.get("principal_entity_ref"),
                code="candidate_worker_principal_resolution_invalid",
            )
            != _entity_id_v1(
                observation.get("principal_entity_ref"),
                code="candidate_worker_principal_resolution_invalid",
            )
            or value.get("account_name") != observation.get("account_name")
            or not isinstance(uid, int)
            or isinstance(uid, bool)
            or uid <= 0
            or not isinstance(gid, int)
            or isinstance(gid, bool)
            or gid <= 0
            or uid != observation.get("uid")
            or gid != observation.get("gid")
            or value.get("account_supplementary_gids")
            != observation.get("account_supplementary_gids")
            or value.get("effective_supplementary_gids") != []
            or value.get("umask") != 0o77
            or value.get("login_shell") != observation.get("login_shell")
            or not isinstance(value.get("non_login"), bool)
            or value.get("non_login") != observation.get("non_login")
            or value.get("platform_binding")
            != observation.get("platform_binding")
            or (
                selection == "dedicated_non_login_service_principal"
                and value.get("non_login") is not True
            )
            or (
                selection == "current_user_501_20_empty_supplementary_groups"
                and (uid != 501 or gid != 20)
            )
        ):
            raise CandidateBoundaryError(
                "candidate_worker_principal_resolution_invalid",
                "resolved principal facts do not implement the selected policy",
            )
        observation_time = _parse_rfc3339_v1(
            observation["observed_at"],
            code="candidate_worker_account_observation_time_invalid",
        )
        resolved_time = _parse_rfc3339_v1(
            value.get("resolved_at"),
            code="candidate_worker_principal_resolution_time_invalid",
        )
        if resolved_time < observation_time:
            raise CandidateBoundaryError(
                "candidate_worker_principal_resolution_chronology_invalid",
                str(value.get("resolution_id")),
            )
    else:
        resolution_entity_id = _entity_id_v1(
            value.get("resolution_entity_ref"),
            code="candidate_worker_principal_resolution_invalid",
        )
        decision_entity_id = _entity_id_v1(
            decision["decision_entity_ref"],
            code="candidate_worker_principal_resolution_invalid",
        )
        subject_entity_id = _entity_id_v1(
            decision["subject_entity_ref"],
            code="candidate_worker_principal_resolution_invalid",
        )
        if (
            resolution_entity_id in {decision_entity_id, subject_entity_id}
            or _entity_id_v1(
                value.get("derived_from"),
                code="candidate_worker_principal_resolution_invalid",
            )
            != _entity_id_v1(
                decision.get("decision_entity_ref"),
                code="candidate_worker_principal_resolution_invalid",
            )
        ):
            raise CandidateBoundaryError(
                "candidate_worker_principal_resolution_entity_invalid",
                resolution_entity_id,
            )
    if _require_digest(
        value.get("resolution_digest"),
        "candidate_worker_principal_resolution_digest_invalid",
    ) != sealed_digest(value, "resolution_digest"):
        raise CandidateBoundaryError(
            "candidate_worker_principal_resolution_digest_mismatch",
            str(value.get("resolution_id")),
        )


def _write_all(descriptor: int, value: bytes) -> None:
    offset = 0
    while offset < len(value):
        written = os.write(descriptor, value[offset:])
        if written <= 0:
            raise CandidateBoundaryError("candidate_write_incomplete", str(offset))
        offset += written


def _ensure_directory_exact(path: Path, *, mode: int) -> None:
    missing: list[Path] = []
    current = path
    while not current.exists():
        if current.is_symlink():
            raise CandidateBoundaryError(
                "candidate_directory_symlink", str(current)
            )
        missing.append(current)
        if current == current.parent:
            break
        current = current.parent
    for candidate in reversed(missing):
        try:
            os.mkdir(candidate, mode)
            os.chmod(candidate, mode)
        except FileExistsError:
            pass
        except OSError as exc:
            raise CandidateBoundaryError(
                "candidate_directory_create_failed", str(candidate)
            ) from exc
        try:
            created = candidate.lstat()
        except OSError as exc:
            raise CandidateBoundaryError(
                "candidate_directory_unavailable", str(candidate)
            ) from exc
        if stat.S_ISLNK(created.st_mode) or not stat.S_ISDIR(created.st_mode):
            raise CandidateBoundaryError(
                "candidate_directory_invalid", str(candidate)
            )
        _assert_no_extended_acl(
            candidate, code="candidate_directory_extended_acl"
        )
    try:
        observed = path.lstat()
    except OSError as exc:
        raise CandidateBoundaryError(
            "candidate_directory_unavailable", str(path)
        ) from exc
    if stat.S_ISLNK(observed.st_mode) or not stat.S_ISDIR(observed.st_mode):
        raise CandidateBoundaryError("candidate_directory_invalid", str(path))
    _assert_no_extended_acl(path, code="candidate_directory_extended_acl")


def _write_exclusive(path: Path, value: bytes, *, mode: int) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags, mode)
    except OSError as exc:
        raise CandidateBoundaryError("candidate_write_failed", str(path)) from exc
    try:
        _write_all(descriptor, value)
        os.fchmod(descriptor, mode)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    _assert_no_extended_acl(path, code="candidate_file_extended_acl")


def _fsync_directory_v1(path: Path, *, code: str) -> None:
    try:
        descriptor = os.open(
            path,
            os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
        )
    except OSError as exc:
        raise CandidateBoundaryError(code, str(path)) from exc
    try:
        os.fsync(descriptor)
    except OSError as exc:
        raise CandidateBoundaryError(code, str(path)) from exc
    finally:
        os.close(descriptor)


def _fsync_frozen_tree_bottom_up_v1(root: Path) -> None:
    for raw_directory, directory_names, file_names in os.walk(
        root, topdown=False, followlinks=False
    ):
        base = Path(raw_directory)
        for name in file_names:
            path = base / name
            observed = path.lstat()
            if not stat.S_ISREG(observed.st_mode) or observed.st_nlink != 1:
                raise CandidateBoundaryError("candidate_fsync_file_invalid", str(path))
            _assert_no_extended_acl(path, code="candidate_fsync_file_extended_acl")
            flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
            try:
                descriptor = os.open(path, flags)
                try:
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
            except OSError as exc:
                raise CandidateBoundaryError(
                    "candidate_fsync_file_failed", str(path)
                ) from exc
        for name in directory_names:
            directory = base / name
            observed = directory.lstat()
            if stat.S_ISLNK(observed.st_mode) or not stat.S_ISDIR(observed.st_mode):
                raise CandidateBoundaryError(
                    "candidate_fsync_directory_invalid", str(directory)
                )
            _assert_no_extended_acl(
                directory, code="candidate_fsync_directory_extended_acl"
            )
            _fsync_directory_v1(
                directory, code="candidate_fsync_directory_failed"
            )
        _assert_no_extended_acl(base, code="candidate_fsync_directory_extended_acl")
        _fsync_directory_v1(base, code="candidate_fsync_directory_failed")


def _remove_private_tree_v1(path: Path) -> None:
    """Remove only a transaction-owned staging tree; never follow links."""

    if not path.exists() and not path.is_symlink():
        return
    if path.is_symlink():
        raise CandidateBoundaryError("candidate_stage_symlink", str(path))
    for raw_directory, directory_names, file_names in os.walk(
        path, topdown=False, followlinks=False
    ):
        base = Path(raw_directory)
        try:
            os.chmod(base, 0o700)
        except OSError:
            pass
        for name in file_names:
            candidate = base / name
            observed = candidate.lstat()
            if stat.S_ISLNK(observed.st_mode) or not stat.S_ISREG(observed.st_mode):
                raise CandidateBoundaryError("candidate_stage_special_entry", str(candidate))
            os.chmod(candidate, 0o600)
        for name in directory_names:
            candidate = base / name
            observed = candidate.lstat()
            if stat.S_ISLNK(observed.st_mode) or not stat.S_ISDIR(observed.st_mode):
                raise CandidateBoundaryError("candidate_stage_special_entry", str(candidate))
            os.chmod(candidate, 0o700)
    shutil.rmtree(path)


def _read_stable_regular(
    path: Path,
    *,
    authorized_root: Path | None = None,
    maximum_bytes: int = 1024 * 1024 * 1024,
) -> tuple[bytes, Path, os.stat_result]:
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise CandidateBoundaryError("candidate_source_unavailable", str(path)) from exc
    if authorized_root is not None:
        try:
            resolved.relative_to(authorized_root.resolve(strict=True))
        except (OSError, ValueError) as exc:
            raise CandidateBoundaryError("candidate_source_escape", str(path)) from exc
    _assert_no_extended_acl(resolved, code="candidate_source_extended_acl")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(resolved, flags)
    except OSError as exc:
        raise CandidateBoundaryError("candidate_source_open_failed", str(path)) from exc
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise CandidateBoundaryError("candidate_source_not_regular", str(path))
        chunks: list[bytes] = []
        size = 0
        while True:
            block = os.read(descriptor, min(1024 * 1024, maximum_bytes + 1 - size))
            if not block:
                break
            size += len(block)
            if size > maximum_bytes:
                raise CandidateBoundaryError("candidate_source_too_large", str(path))
            chunks.append(block)
        after = os.fstat(descriptor)
        identity_before = (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
        )
        identity_after = (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        )
        if identity_before != identity_after:
            raise CandidateBoundaryError("candidate_source_changed", str(path))
        return b"".join(chunks), resolved, before
    finally:
        os.close(descriptor)


def _copy_source_file(
    source: Path,
    destination: Path,
    *,
    authorized_root: Path,
) -> tuple[dict[str, str], int, str, Path]:
    raw, resolved, observed = _read_stable_regular(
        source, authorized_root=authorized_root
    )
    intended_mode = "0500" if observed.st_mode & 0o111 else "0400"
    _ensure_directory_exact(destination.parent, mode=0o700)
    _write_exclusive(destination, raw, mode=int(intended_mode, 8))
    return digest_bytes(raw), len(raw), intended_mode, resolved


def _excluded(relative: PurePosixPath, prefixes: Sequence[PurePosixPath]) -> bool:
    if relative.suffix == ".pyc" or any(
        part in _PREPARE_EXCLUDED_NAMES for part in relative.parts
    ):
        return True
    return any(relative == prefix or prefix in relative.parents for prefix in prefixes)


def _tree_files(
    root: Path,
    *,
    excluded_prefixes: Sequence[str] = (),
) -> list[tuple[PurePosixPath, Path]]:
    try:
        exact_root = root.resolve(strict=True)
    except OSError as exc:
        raise CandidateBoundaryError("candidate_tree_unavailable", str(root)) from exc
    if not exact_root.is_dir():
        raise CandidateBoundaryError("candidate_tree_not_directory", str(root))
    prefixes = tuple(
        _safe_relative_path(item, code="candidate_exclusion_path_invalid")
        for item in excluded_prefixes
    )
    results: list[tuple[PurePosixPath, Path]] = []
    for raw_directory, directory_names, file_names in os.walk(
        exact_root, topdown=True, followlinks=False
    ):
        base = Path(raw_directory)
        relative_base = base.relative_to(exact_root)
        retained_directories: list[str] = []
        for name in sorted(directory_names):
            candidate = base / name
            relative = PurePosixPath((relative_base / name).as_posix())
            if _excluded(relative, prefixes):
                continue
            observed = candidate.lstat()
            if stat.S_ISLNK(observed.st_mode):
                raise CandidateBoundaryError(
                    "candidate_symlink_directory_prohibited", str(candidate)
                )
            if not stat.S_ISDIR(observed.st_mode):
                raise CandidateBoundaryError(
                    "candidate_tree_special_entry", str(candidate)
                )
            retained_directories.append(name)
        directory_names[:] = retained_directories
        for name in sorted(file_names):
            candidate = base / name
            relative = PurePosixPath((relative_base / name).as_posix())
            if _excluded(relative, prefixes):
                continue
            observed = candidate.lstat()
            if not (stat.S_ISREG(observed.st_mode) or stat.S_ISLNK(observed.st_mode)):
                raise CandidateBoundaryError(
                    "candidate_tree_special_entry", str(candidate)
                )
            if stat.S_ISLNK(observed.st_mode):
                try:
                    candidate.resolve(strict=True).relative_to(exact_root)
                except (OSError, ValueError) as exc:
                    raise CandidateBoundaryError(
                        "candidate_source_escape", str(candidate)
                    ) from exc
            results.append((relative, candidate))
    results.sort(key=lambda item: item[0].as_posix())
    return results


def discover_project_dependency_exclusions_v1(
    site_packages: Path,
    *,
    snapshot_source_root: Path,
) -> list[str]:
    """Find and verify the editable project material that must not be copied.

    The dependency import root is a third-party dependency denominator.  The
    semantic-guard source is captured separately under ``vnext/src``.  Keeping
    the editable pointer, generated package-data directory, or distribution
    metadata in both places would retain the preparing repository path and make
    the resulting snapshot dependent on that path.
    """

    try:
        dependency_root = site_packages.resolve(strict=True)
        source_root = snapshot_source_root.resolve(strict=True)
    except OSError as exc:
        raise CandidateBoundaryError(
            "candidate_project_dependency_source_unavailable",
            f"{site_packages}; {snapshot_source_root}",
        ) from exc
    if not dependency_root.is_dir() or not source_root.is_dir():
        raise CandidateBoundaryError(
            "candidate_project_dependency_source_invalid",
            f"{dependency_root}; {source_root}",
        )

    children = sorted(dependency_root.iterdir(), key=lambda item: item.name)
    editable_pointers = [
        item
        for item in children
        if item.name == EDITABLE_POINTER_NAME
        or (
            PROJECT_IMPORT_NAME in item.name
            and item.name.endswith((".pth", ".egg-link"))
        )
    ]
    distribution_metadata = [
        item
        for item in children
        if item.name.startswith(f"{PROJECT_IMPORT_NAME}-")
        and item.name.endswith(".dist-info")
    ]
    package_data = dependency_root / PROJECT_IMPORT_NAME
    if (
        len(editable_pointers) != 1
        or editable_pointers[0].name != EDITABLE_POINTER_NAME
        or len(distribution_metadata) != 1
        or not package_data.is_dir()
        or package_data.is_symlink()
    ):
        raise CandidateBoundaryError(
            "candidate_project_dependency_shape_invalid",
            repr(
                {
                    "editable_pointers": [item.name for item in editable_pointers],
                    "distribution_metadata": [
                        item.name for item in distribution_metadata
                    ],
                    "package_data": package_data.is_dir(),
                }
            ),
        )

    pointer_raw, _pointer_resolved, _pointer_stat = _read_stable_regular(
        editable_pointers[0], authorized_root=dependency_root
    )
    try:
        pointer_lines = [
            line.strip()
            for line in pointer_raw.decode("utf-8").splitlines()
            if line.strip()
        ]
    except UnicodeError as exc:
        raise CandidateBoundaryError(
            "candidate_editable_pointer_invalid", editable_pointers[0].name
        ) from exc
    if not pointer_lines or set(pointer_lines) != {str(source_root)}:
        raise CandidateBoundaryError(
            "candidate_editable_pointer_invalid", repr(pointer_lines)
        )

    direct_url = distribution_metadata[0] / "direct_url.json"
    direct_url_raw, _direct_url_resolved, _direct_url_stat = _read_stable_regular(
        direct_url, authorized_root=dependency_root
    )
    try:
        direct_url_record = strict_json_loads(direct_url_raw)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CandidateBoundaryError(
            "candidate_editable_direct_url_invalid", str(direct_url)
        ) from exc
    raw_url = (
        direct_url_record.get("url") if isinstance(direct_url_record, dict) else None
    )
    dir_info = (
        direct_url_record.get("dir_info")
        if isinstance(direct_url_record, dict)
        else None
    )
    try:
        parsed = urlparse(raw_url) if isinstance(raw_url, str) else None
        direct_url_root = (
            Path(unquote(parsed.path)).resolve(strict=True)
            if parsed is not None
            and parsed.scheme == "file"
            and parsed.netloc in {"", "localhost"}
            else None
        )
    except (OSError, ValueError):
        direct_url_root = None
    if (
        not isinstance(dir_info, dict)
        or dir_info.get("editable") is not True
        or direct_url_root != source_root.parent
    ):
        raise CandidateBoundaryError(
            "candidate_editable_direct_url_invalid", repr(direct_url_record)
        )

    return sorted(
        {
            editable_pointers[0].name,
            distribution_metadata[0].name,
            package_data.name,
        }
    )


def dependency_environment_policy_v1(
    *,
    python_major_minor: str,
    excluded_project_entries: Sequence[str],
) -> dict[str, Any]:
    """Build the digest-bound source/dependency separation policy."""

    dependency_root = f"vnext/.venv/lib/python{python_major_minor}/site-packages"
    return {
        "profile": DEPENDENCY_ENVIRONMENT_PROFILE,
        "status": "candidate_prepared",
        "project_distribution": PROJECT_DISTRIBUTION,
        "dependency_import_root": dependency_root,
        "excluded_project_entries": sorted(excluded_project_entries),
        "snapshot_source_root": SNAPSHOT_SOURCE_ROOT,
        "required_repository_entries": [
            ROOT_BROKER_BOOTSTRAP_PATH,
            ROOT_BROKER_ENTRYPOINT_PATH,
            ROOT_BROKER_OUTER_LAUNCHER_PATH,
            ROOT_INSTALLER_ENTRYPOINT_SOURCE_PATH,
        ],
        "lock_validation": {
            "profile": LOCK_VALIDATION_PROFILE,
            "working_directory": "vnext",
            "uv_executable": "vnext/tools/uv",
            "python_executable": "vnext/.venv/bin/python",
            "arguments": list(LOCK_CHECK_ARGUMENTS),
            "execution_identity": "non_root_worker",
            "success_condition": "exit_0_from_non_mutating_check",
        },
    }


def _validate_dependency_environment_policy_v1(
    policy: Any,
    *,
    payload_paths: Sequence[str],
) -> None:
    if not isinstance(policy, Mapping):
        raise CandidateBoundaryError(
            "candidate_dependency_environment_policy_invalid", repr(policy)
        )
    _require_exact_fields(
        policy,
        {
            "profile",
            "status",
            "project_distribution",
            "dependency_import_root",
            "excluded_project_entries",
            "snapshot_source_root",
            "required_repository_entries",
            "lock_validation",
        },
        "candidate_dependency_environment_policy_invalid",
    )
    if (
        policy.get("profile") != DEPENDENCY_ENVIRONMENT_PROFILE
        or policy.get("status") != "candidate_prepared"
        or policy.get("project_distribution") != PROJECT_DISTRIBUTION
        or policy.get("snapshot_source_root") != SNAPSHOT_SOURCE_ROOT
        or policy.get("required_repository_entries")
        != [
            ROOT_BROKER_BOOTSTRAP_PATH,
            ROOT_BROKER_ENTRYPOINT_PATH,
            ROOT_BROKER_OUTER_LAUNCHER_PATH,
            ROOT_INSTALLER_ENTRYPOINT_SOURCE_PATH,
        ]
    ):
        raise CandidateBoundaryError(
            "candidate_dependency_environment_policy_invalid", "fixed contract"
        )

    dependency_root = _safe_relative_path(
        str(policy.get("dependency_import_root", "")),
        code="candidate_dependency_import_root_invalid",
    ).as_posix()
    if (
        re.fullmatch(
            r"vnext/\.venv/lib/python[0-9]+\.[0-9]+/site-packages",
            dependency_root,
        )
        is None
    ):
        raise CandidateBoundaryError(
            "candidate_dependency_import_root_invalid", dependency_root
        )
    exclusions = policy.get("excluded_project_entries")
    if not isinstance(exclusions, list) or any(
        not isinstance(item, str) for item in exclusions
    ):
        raise CandidateBoundaryError(
            "candidate_project_dependency_exclusion_invalid", repr(exclusions)
        )
    if exclusions != sorted(set(exclusions)) or any(
        "/" in item
        or _safe_relative_path(
            item, code="candidate_project_dependency_exclusion_invalid"
        ).as_posix()
        != item
        for item in exclusions
    ):
        raise CandidateBoundaryError(
            "candidate_project_dependency_exclusion_invalid", repr(exclusions)
        )
    metadata = [
        item
        for item in exclusions
        if item.startswith(f"{PROJECT_IMPORT_NAME}-") and item.endswith(".dist-info")
    ]
    if (
        EDITABLE_POINTER_NAME not in exclusions
        or PROJECT_IMPORT_NAME not in exclusions
        or len(metadata) != 1
    ):
        raise CandidateBoundaryError(
            "candidate_project_dependency_exclusion_incomplete", repr(exclusions)
        )

    lock_validation = policy.get("lock_validation")
    if not isinstance(lock_validation, Mapping):
        raise CandidateBoundaryError(
            "candidate_lock_validation_policy_invalid", repr(lock_validation)
        )
    _require_exact_fields(
        lock_validation,
        {
            "profile",
            "working_directory",
            "uv_executable",
            "python_executable",
            "arguments",
            "execution_identity",
            "success_condition",
        },
        "candidate_lock_validation_policy_invalid",
    )
    expected_lock = {
        "profile": LOCK_VALIDATION_PROFILE,
        "working_directory": "vnext",
        "uv_executable": "vnext/tools/uv",
        "python_executable": "vnext/.venv/bin/python",
        "arguments": list(LOCK_CHECK_ARGUMENTS),
        "execution_identity": "non_root_worker",
        "success_condition": "exit_0_from_non_mutating_check",
    }
    if dict(lock_validation) != expected_lock:
        raise CandidateBoundaryError(
            "candidate_lock_validation_policy_invalid", repr(lock_validation)
        )

    path_set = set(payload_paths)
    required_paths = {
        *policy["required_repository_entries"],
        "vnext/pyproject.toml",
        "vnext/uv.lock",
        str(lock_validation["uv_executable"]),
        str(lock_validation["python_executable"]),
    }
    missing = required_paths - path_set
    if missing:
        raise CandidateBoundaryError(
            "candidate_dependency_required_entry_missing", repr(sorted(missing))
        )
    source_prefix = f"{SNAPSHOT_SOURCE_ROOT}/"
    if not any(path.startswith(source_prefix) for path in path_set):
        raise CandidateBoundaryError(
            "candidate_snapshot_source_root_empty", SNAPSHOT_SOURCE_ROOT
        )
    for exclusion in exclusions:
        excluded_root = f"{dependency_root}/{exclusion}"
        if any(
            path == excluded_root or path.startswith(f"{excluded_root}/")
            for path in path_set
        ):
            raise CandidateBoundaryError(
                "candidate_project_dependency_leaked", excluded_root
            )


def _validate_dependency_mapping_v1(
    policy: Mapping[str, Any], mappings: Sequence[Mapping[str, Any]]
) -> None:
    dependency_mappings = [
        item
        for item in mappings
        if item.get("role") == "python_dependency_runtime"
        and item.get("destination") == policy.get("dependency_import_root")
    ]
    observed_exclusions = (
        dependency_mappings[0].get("excluded_prefixes")
        if len(dependency_mappings) == 1
        else None
    )
    if (
        not isinstance(observed_exclusions, list)
        or any(not isinstance(item, str) for item in observed_exclusions)
        or sorted(observed_exclusions) != policy.get("excluded_project_entries")
    ):
        raise CandidateBoundaryError(
            "candidate_dependency_mapping_policy_mismatch",
            repr(dependency_mappings),
        )


def _mapping_files(mapping: Mapping[str, Any]) -> Iterable[tuple[str, Path]]:
    source = Path(str(mapping["source_path"]))
    destination = _safe_relative_path(
        str(mapping["destination"]), code="candidate_mapping_destination_invalid"
    )
    kind = str(mapping["mapping_kind"])
    if kind == "file":
        yield destination.as_posix(), source
        return
    if kind != "tree":
        raise CandidateBoundaryError("candidate_mapping_kind_invalid", kind)
    for relative, candidate in _tree_files(
        source,
        excluded_prefixes=tuple(mapping.get("excluded_prefixes", ())),
    ):
        yield (destination / relative).as_posix(), candidate


def _repository_binding(repository_root: Path) -> dict[str, Any]:
    exact = repository_root.resolve(strict=True)
    observed = exact.stat()
    if not stat.S_ISDIR(observed.st_mode):
        raise CandidateBoundaryError("candidate_repository_not_directory", str(exact))
    return {
        "canonical_path": str(exact),
        "device_id": observed.st_dev,
        "inode": observed.st_ino,
    }


def _freeze_tree(root: Path, *, owner_uid: int | None = None) -> None:
    for raw_directory, directory_names, file_names in os.walk(
        root, topdown=False, followlinks=False
    ):
        base = Path(raw_directory)
        for name in file_names:
            path = base / name
            observed = path.lstat()
            if not stat.S_ISREG(observed.st_mode) or observed.st_nlink != 1:
                raise CandidateBoundaryError("candidate_freeze_file_invalid", str(path))
            if owner_uid is not None and observed.st_uid != owner_uid:
                raise CandidateBoundaryError(
                    "candidate_freeze_owner_mismatch", str(path)
                )
            os.chmod(path, 0o500 if observed.st_mode & 0o111 else 0o400)
            _assert_no_extended_acl(
                path, code="candidate_freeze_file_extended_acl"
            )
        for name in directory_names:
            path = base / name
            observed = path.lstat()
            if not stat.S_ISDIR(observed.st_mode):
                raise CandidateBoundaryError(
                    "candidate_freeze_directory_invalid", str(path)
                )
            if owner_uid is not None and observed.st_uid != owner_uid:
                raise CandidateBoundaryError(
                    "candidate_freeze_owner_mismatch", str(path)
                )
            os.chmod(path, 0o500)
            _assert_no_extended_acl(
                path, code="candidate_freeze_directory_extended_acl"
            )
    os.chmod(root, 0o500)
    _assert_no_extended_acl(root, code="candidate_freeze_directory_extended_acl")


def _prepare_bundle_from_mappings(
    *,
    mappings: Sequence[Mapping[str, Any]],
    dependency_environment_policy: Mapping[str, Any],
    repository_root: Path,
    output: Path,
    preactivation_decision: Mapping[str, Any],
    preactivation_decision_raw: bytes,
    preactivation_decision_locator: Path,
    worker_account_observation: Mapping[str, Any],
    worker_account_observation_raw: bytes,
    worker_account_observation_locator: Path,
    worker_principal_resolution: Mapping[str, Any],
    worker_principal_resolution_raw: bytes,
    worker_principal_resolution_locator: Path,
    installer_path: Path,
) -> dict[str, Any]:
    """Create a closed candidate bundle.  This function never grants authority."""

    for label, record, raw in (
        (
            "preactivation_decision",
            preactivation_decision,
            preactivation_decision_raw,
        ),
        (
            "worker_account_observation",
            worker_account_observation,
            worker_account_observation_raw,
        ),
        (
            "worker_principal_resolution",
            worker_principal_resolution,
            worker_principal_resolution_raw,
        ),
    ):
        try:
            decoded = strict_json_loads(raw)
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise CandidateBoundaryError(
                "candidate_preactivation_boundary_unreadable", label
            ) from exc
        if decoded != record:
            raise CandidateBoundaryError(
                "candidate_preactivation_boundary_object_raw_mismatch", label
            )
    validate_preactivation_decision_evidence_v1(preactivation_decision)
    if (
        preactivation_decision["threat_boundary_selection"]
        != "local_bounded_repository_suite_only"
        or preactivation_decision["human_decision"] != "accept"
        or preactivation_decision["worker_identity_selection"] == "defer"
    ):
        raise CandidateBoundaryError(
            "candidate_local_profile_not_authorized_by_scope_decision",
            str(preactivation_decision["threat_boundary_selection"]),
        )
    decision_locator = preactivation_decision_locator.resolve(strict=True)
    observation_locator = worker_account_observation_locator.resolve(strict=True)
    resolution_locator = worker_principal_resolution_locator.resolve(strict=True)
    validate_worker_principal_resolution_v1(
        worker_principal_resolution,
        decision=preactivation_decision,
        decision_raw=preactivation_decision_raw,
        decision_locator=decision_locator,
        observation=worker_account_observation,
        observation_raw=worker_account_observation_raw,
        observation_locator=observation_locator,
        reobserve_current=True,
    )
    if worker_principal_resolution["resolution_state"] != "resolved":
        raise CandidateBoundaryError(
            "candidate_worker_principal_not_resolved",
            str(worker_principal_resolution["resolution_id"]),
        )
    worker_uid = int(worker_principal_resolution["uid"])
    worker_gid = int(worker_principal_resolution["gid"])
    if worker_uid <= 0 or worker_gid <= 0:
        raise CandidateBoundaryError(
            "candidate_worker_identity_invalid", f"{worker_uid}:{worker_gid}"
        )
    _validate_dependency_mapping_v1(dependency_environment_policy, mappings)
    output = output.absolute()
    if output.exists() or output.is_symlink():
        raise CandidateBoundaryError("candidate_output_exists", str(output))
    _ensure_directory_exact(output.parent, mode=0o700)
    stage = output.parent / f".{output.name}.preparing.{secrets.token_hex(16)}"
    payload = stage / "payload"
    try:
        _ensure_directory_exact(stage, mode=0o700)
        _ensure_directory_exact(payload, mode=0o700)
        installer_raw, installer_resolved, _ = _read_stable_regular(installer_path)
        installer_entrypoint_raw, installer_entrypoint_resolved, _ = (
            _read_stable_regular(
                repository_root / ROOT_INSTALLER_ENTRYPOINT_SOURCE_PATH,
                authorized_root=repository_root,
            )
        )
        for bootstrap_host_path in (
            ROOT_BOOTSTRAP_SHELL,
            ROOT_ENVIRONMENT_CLEANER,
            ROOT_BOOTSTRAP_DISCOVERY_LAUNCHER,
        ):
            _validate_owned_directory_chain(
                bootstrap_host_path.parent,
                required_uid=0,
            )
        shell_raw, shell_resolved, shell_observed = _read_stable_regular(
            ROOT_BOOTSTRAP_SHELL
        )
        cleaner_raw, cleaner_resolved, cleaner_observed = _read_stable_regular(
            ROOT_ENVIRONMENT_CLEANER
        )
        discovery_raw, discovery_resolved, discovery_observed = (
            _read_stable_regular(ROOT_BOOTSTRAP_DISCOVERY_LAUNCHER)
        )
        effective_interpreter = _discover_effective_bootstrap_python_v1()
        _validate_owned_directory_chain(
            effective_interpreter.parent,
            required_uid=0,
        )
        interpreter_raw, interpreter_resolved, interpreter_observed = (
            _read_stable_regular(effective_interpreter)
        )
        if (
            shell_observed.st_uid != 0
            or shell_observed.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
            or cleaner_observed.st_uid != 0
            or cleaner_observed.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
            or discovery_observed.st_uid != 0
            or discovery_observed.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
            or interpreter_resolved != effective_interpreter
            or interpreter_observed.st_uid != 0
            or interpreter_observed.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
        ):
            raise CandidateBoundaryError(
                "candidate_bootstrap_interpreter_untrusted",
                str(effective_interpreter),
            )
        entries: list[dict[str, Any]] = []
        seen: set[str] = set()
        ordered_mappings = sorted(
            (dict(item) for item in mappings),
            key=lambda item: (
                str(item.get("destination", "")),
                str(item.get("source_path", "")),
            ),
        )
        for mapping in ordered_mappings:
            _require_exact_fields(
                mapping,
                {
                    "mapping_kind",
                    "source_path",
                    "destination",
                    "role",
                    "origin_kind",
                    "excluded_prefixes",
                },
                "candidate_mapping_fields_invalid",
            )
            source_root = Path(str(mapping["source_path"])).resolve(strict=True)
            authorized_root = (
                source_root if source_root.is_dir() else source_root.parent
            )
            for relative, source in _mapping_files(mapping):
                _safe_relative_path(relative, code="candidate_payload_path_invalid")
                if relative in seen:
                    raise CandidateBoundaryError(
                        "candidate_payload_path_collision", relative
                    )
                seen.add(relative)
                artifact_digest, size, mode, resolved = _copy_source_file(
                    source,
                    payload / Path(*PurePosixPath(relative).parts),
                    authorized_root=authorized_root,
                )
                entries.append(
                    {
                        "path": relative,
                        "role": str(mapping["role"]),
                        "source_ref": {
                            "origin_kind": str(mapping["origin_kind"]),
                            "locator": str(source),
                            "resolved_locator": str(resolved),
                            "artifact_digest": artifact_digest,
                        },
                        "artifact_digest": artifact_digest,
                        "size": size,
                        "intended_mode": mode,
                    }
                )
        entries.sort(key=lambda item: str(item["path"]))
        decision_entries = [
            entry
            for entry in entries
            if entry["role"] == "u10_preactivation_decision_record"
        ]
        principal_entries = [
            entry
            for entry in entries
            if entry["role"] == "u10_worker_principal_resolution"
        ]
        observation_entries = [
            entry
            for entry in entries
            if entry["role"] == "u10_worker_account_observation"
        ]
        if (
            len(decision_entries) != 1
            or len(observation_entries) != 1
            or len(principal_entries) != 1
        ):
            raise CandidateBoundaryError(
                "candidate_preactivation_boundary_denominator_invalid",
                repr(
                    {
                        "decision_entries": len(decision_entries),
                        "observation_entries": len(observation_entries),
                        "principal_entries": len(principal_entries),
                    }
                ),
            )
        decision_entry = decision_entries[0]
        observation_entry = observation_entries[0]
        principal_entry = principal_entries[0]
        decision_ref = worker_principal_resolution["decision_record_ref"]
        observation_ref = worker_principal_resolution[
            "account_observation_ref"
        ]
        if (
            decision_entry["artifact_digest"]
            != digest_bytes(preactivation_decision_raw)
            or decision_entry["source_ref"]["artifact_digest"]
            != digest_bytes(preactivation_decision_raw)
            or decision_entry["source_ref"]["locator"] != decision_ref["locator"]
            or decision_entry["source_ref"]["resolved_locator"]
            != str(decision_locator)
            or observation_entry["artifact_digest"]
            != digest_bytes(worker_account_observation_raw)
            or observation_entry["source_ref"]["artifact_digest"]
            != digest_bytes(worker_account_observation_raw)
            or observation_entry["source_ref"]["locator"]
            != observation_ref["locator"]
            or observation_entry["source_ref"]["resolved_locator"]
            != str(observation_locator)
            or principal_entry["artifact_digest"]
            != digest_bytes(worker_principal_resolution_raw)
            or principal_entry["source_ref"]["artifact_digest"]
            != digest_bytes(worker_principal_resolution_raw)
            or principal_entry["source_ref"]["resolved_locator"]
            != str(resolution_locator)
        ):
            raise CandidateBoundaryError(
                "candidate_preactivation_boundary_artifact_mismatch",
                str(preactivation_decision["decision_id"]),
            )
        preactivation_boundary_refs: dict[str, Any] = {
            "profile": "u10-local-bounded-preactivation-binding/v1",
            "decision_record_ref": {
                "record_id": preactivation_decision["decision_id"],
                "source_locator": decision_entry["source_ref"]["locator"],
                "source_artifact_digest": decision_entry["source_ref"][
                    "artifact_digest"
                ],
                "bundled_locator": decision_entry["path"],
                "bundled_artifact_digest": decision_entry["artifact_digest"],
                "semantic_digest": preactivation_decision["decision_digest"],
            },
            "worker_account_observation_ref": {
                "record_id": worker_account_observation["observation_id"],
                "source_locator": observation_entry["source_ref"]["locator"],
                "source_artifact_digest": observation_entry["source_ref"][
                    "artifact_digest"
                ],
                "bundled_locator": observation_entry["path"],
                "bundled_artifact_digest": observation_entry["artifact_digest"],
                "semantic_digest": worker_account_observation[
                    "observation_digest"
                ],
            },
            "worker_principal_resolution_ref": {
                "record_id": worker_principal_resolution["resolution_id"],
                "source_locator": principal_entry["source_ref"]["locator"],
                "source_artifact_digest": principal_entry["source_ref"][
                    "artifact_digest"
                ],
                "bundled_locator": principal_entry["path"],
                "bundled_artifact_digest": principal_entry["artifact_digest"],
                "semantic_digest": worker_principal_resolution[
                    "resolution_digest"
                ],
            },
            "threat_boundary": "local_bounded_repository_suite_only",
            "worker_identity_policy": preactivation_decision[
                "worker_identity_selection"
            ],
            "qualification_scope": "repository_owned_closed_verification_suite_only",
            "hostile_code_assurance": "prohibited_requires_separate_external_executor_profile",
            "requalification_triggers": list(
                preactivation_decision["requalification_triggers"]
            ),
        }
        preactivation_boundary_refs["binding_digest"] = sealed_digest(
            preactivation_boundary_refs, "binding_digest"
        )
        payload_directories = _payload_directory_denominator_v1(
            str(item["path"]) for item in entries
        )
        _validate_dependency_environment_policy_v1(
            dependency_environment_policy,
            payload_paths=[str(item["path"]) for item in entries],
        )
        payload_digest = digest_bytes(
            canonical_json_bytes(
                {"directories": payload_directories, "entries": entries}
            )
        )
        bundle_id = f"candidate.u10.{payload_digest['value']}"
        target = CANDIDATE_ROOT / bundle_id
        generated_path = "vnext/.venv/pyvenv.cfg"
        if generated_path in seen:
            raise CandidateBoundaryError(
                "candidate_generated_path_collision", generated_path
            )
        manifest: dict[str, Any] = {
            "schema_version": BUNDLE_SCHEMA,
            "bundle_id": bundle_id,
            "bundle_version": "2.0.0-candidate",
            "bundle_state": "candidate_uninstalled",
            "notation_profile": "entity-reference-notation/v0",
            "source_repository_binding": _repository_binding(repository_root),
            "preactivation_boundary_refs": preactivation_boundary_refs,
            "installer_ref": {
                "record_id": "installer.semantic-guard.u10.root-candidate.v1",
                "source_locator": str(installer_resolved),
                "required_bootstrap_locator": str(BOOTSTRAP_INSTALLER_PATH),
                "entrypoint_source_locator": str(installer_entrypoint_resolved),
                "required_entrypoint_locator": str(ROOT_INSTALLER_ENTRYPOINT_PATH),
                "entrypoint_artifact_digest": digest_bytes(
                    installer_entrypoint_raw
                ),
                "required_shell_locator": str(ROOT_BOOTSTRAP_SHELL),
                "shell_resolved_locator": str(shell_resolved),
                "shell_artifact_digest": digest_bytes(shell_raw),
                "shell_flags": ["-p"],
                "environment_cleaner_locator": str(ROOT_ENVIRONMENT_CLEANER),
                "environment_cleaner_resolved_locator": str(cleaner_resolved),
                "environment_cleaner_artifact_digest": digest_bytes(cleaner_raw),
                "environment_policy": (
                    "privileged_sh_p_then_env_i_direct_effective_execve/v3"
                ),
                "os_injected_environment_policy": (
                    "cf_user_text_encoding_uid_bound_then_removed/v1"
                ),
                "discovery_launcher_locator": str(
                    ROOT_BOOTSTRAP_DISCOVERY_LAUNCHER
                ),
                "discovery_launcher_resolved_locator": str(discovery_resolved),
                "discovery_launcher_artifact_digest": digest_bytes(discovery_raw),
                "effective_interpreter_locator": str(interpreter_resolved),
                "effective_interpreter_artifact_digest": digest_bytes(
                    interpreter_raw
                ),
                "required_effective_interpreter_path_locator": str(
                    ROOT_EFFECTIVE_PYTHON_PATH_FILE
                ),
                "effective_interpreter_path_artifact_digest": digest_bytes(
                    f"{interpreter_resolved}\n".encode("utf-8")
                ),
                "artifact_digest": digest_bytes(installer_raw),
            },
            "worker_identity": {
                "uid": worker_uid,
                "gid": worker_gid,
                "account_supplementary_gids": worker_principal_resolution[
                    "account_supplementary_gids"
                ],
                "effective_supplementary_gids": [],
                "umask": 0o77,
                "login_shell": worker_principal_resolution["login_shell"],
                "non_login": worker_principal_resolution["non_login"],
                "root_prohibited": True,
                "principal_entity_ref": worker_principal_resolution[
                    "principal_entity_ref"
                ],
                "principal_resolution_digest": worker_principal_resolution[
                    "resolution_digest"
                ],
            },
            "target": {
                "candidate_root": str(CANDIDATE_ROOT),
                "candidate_path": str(target),
                "candidate_install_ledger_root": str(
                    CANDIDATE_INSTALL_LEDGER_ROOT
                ),
                "candidate_install_ledger_policy": (
                    _candidate_install_ledger_policy_v1()
                ),
                "active_snapshot_root": str(SNAPSHOT_ROOT),
                "active_trust_store": str(TRUST_STORE_PATH),
                "install_scope": (
                    "inactive_candidate_tree_and_append_only_install_ledger_only"
                ),
            },
            "payload_denominator": {
                "status": "closed",
                "directory_count": len(payload_directories),
                "directories": payload_directories,
                "entry_count": len(entries),
                "entries": entries,
                "payload_digest": payload_digest,
            },
            "dependency_environment_policy": dict(dependency_environment_policy),
            "root_generated_entries": [
                {
                    "path": generated_path,
                    "generation_profile": "u10-relocatable-pyvenv-config/v1",
                    "content_template": PYVENV_TEMPLATE,
                    "intended_mode": "0400",
                }
            ],
            "human_install_authorization": {
                "status": "pending",
                "authorized_operation": None,
                "authorization_ref": None,
            },
            "snapshot_activation": {
                "status": "not_authorized",
                "required_follow_up": SNAPSHOT_ACTIVATION_FOLLOW_UP,
            },
            "u4_principal_authenticity": {
                "requirement_id": "U-4",
                "status": "unresolved",
                "consequence": (
                    "root-owned authorization placement is an operational gate; "
                    "it does not prove principal identity, delegation, or revocation"
                ),
            },
            "formal_authority": "none",
            "positive_assurance_allowed": False,
        }
        manifest["bundle_digest"] = sealed_digest(manifest, "bundle_digest")
        validate_bundle_manifest_v1(manifest)
        _write_exclusive(
            stage / MANIFEST_NAME,
            json.dumps(
                manifest,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
                allow_nan=False,
            ).encode("utf-8")
            + b"\n",
            mode=0o400,
        )
        _freeze_tree(payload)
        os.chmod(stage, 0o500)
        os.replace(stage, output)
        return manifest
    except BaseException:
        _remove_private_tree_v1(stage)
        raise


def _python_layout(python_path: Path) -> dict[str, str]:
    script = (
        "import json, pathlib, sys, sysconfig; "
        "print(json.dumps({"
        "'base_prefix': str(pathlib.Path(sys.base_prefix).resolve()),"
        "'executable': str(pathlib.Path(sys.executable).resolve()),"
        "'version': f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}'"
        "}, sort_keys=True, allow_nan=False))"
    )
    try:
        completed = subprocess.run(
            [str(python_path), "-I", "-S", "-c", script],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
            env={"PATH": "", "LC_ALL": "C", "PYTHONDONTWRITEBYTECODE": "1"},
            text=True,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise CandidateBoundaryError("candidate_python_probe_failed", str(exc)) from exc
    if completed.returncode != 0:
        raise CandidateBoundaryError(
            "candidate_python_probe_failed", completed.stderr[:1000]
        )
    try:
        value = strict_json_loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise CandidateBoundaryError(
            "candidate_python_probe_invalid", completed.stdout[:1000]
        ) from exc
    if not isinstance(value, dict) or set(value) != {
        "base_prefix",
        "executable",
        "version",
    }:
        raise CandidateBoundaryError("candidate_python_probe_invalid", repr(value))
    result = {key: str(item) for key, item in value.items()}
    major_minor = ".".join(result["version"].split(".")[:2])
    # ``-S`` intentionally avoids executing .pth/sitecustomize material, but
    # on Python 3.13 it also reports the base prefix.  The qualified project
    # dependency root is therefore derived from the invocation path, not from
    # the base interpreter's sysconfig result.
    invocation_root = python_path.absolute().parent.parent
    pyvenv = invocation_root / "pyvenv.cfg"
    site_packages = invocation_root / "lib" / f"python{major_minor}" / "site-packages"
    if not pyvenv.is_file() or not site_packages.is_dir():
        raise CandidateBoundaryError(
            "candidate_python_environment_not_venv", str(invocation_root)
        )
    result["site_packages"] = str(site_packages.resolve(strict=True))
    result["environment_root"] = str(invocation_root.resolve(strict=True))
    return result


def prepare_repository_bundle_v1(
    *,
    repository_root: Path,
    python_path: Path,
    uv_path: Path,
    output: Path,
    preactivation_decision_path: Path,
    worker_principal_resolution_path: Path,
) -> dict[str, Any]:
    root = repository_root.resolve(strict=True)
    vnext = root / "vnext"
    if (
        not (vnext / "pyproject.toml").is_file()
        or not (vnext / "src" / "semantic_guard_u10_broker" / "core.py").is_file()
        or not (vnext / "scripts" / "u10_root_broker_bootstrap.py").is_file()
    ):
        raise CandidateBoundaryError("candidate_repository_shape_invalid", str(root))
    decision_raw, decision_resolved, _decision_stat = _read_stable_regular(
        preactivation_decision_path
    )
    resolution_raw, resolution_resolved, _resolution_stat = _read_stable_regular(
        worker_principal_resolution_path
    )
    try:
        preactivation_decision = strict_json_loads(decision_raw)
        worker_principal_resolution = strict_json_loads(resolution_raw)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CandidateBoundaryError(
            "candidate_preactivation_boundary_unreadable", str(exc)
        ) from exc
    if not isinstance(preactivation_decision, dict) or not isinstance(
        worker_principal_resolution, dict
    ):
        raise CandidateBoundaryError(
            "candidate_preactivation_boundary_unreadable", "record shape"
        )
    validate_preactivation_decision_v1(preactivation_decision)
    observation_reference = worker_principal_resolution.get(
        "account_observation_ref"
    )
    if not isinstance(observation_reference, Mapping):
        raise CandidateBoundaryError(
            "candidate_worker_principal_resolution_invalid",
            "missing account observation reference",
        )
    observation_reference = _require_artifact_ref_v1(
        observation_reference,
        code="candidate_worker_principal_resolution_invalid",
    )
    observation_raw, observation_resolved, _observation_stat = (
        _read_stable_regular(Path(observation_reference["locator"]))
    )
    try:
        worker_account_observation = strict_json_loads(observation_raw)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CandidateBoundaryError(
            "candidate_preactivation_boundary_unreadable", str(exc)
        ) from exc
    if not isinstance(worker_account_observation, dict):
        raise CandidateBoundaryError(
            "candidate_preactivation_boundary_unreadable", "observation shape"
        )
    validate_worker_principal_resolution_v1(
        worker_principal_resolution,
        decision=preactivation_decision,
        decision_raw=decision_raw,
        decision_locator=decision_resolved,
        observation=worker_account_observation,
        observation_raw=observation_raw,
        observation_locator=observation_resolved,
        reobserve_current=True,
    )
    layout = _python_layout(python_path)
    base = Path(layout["base_prefix"])
    executable = Path(layout["executable"])
    site_packages = Path(layout["site_packages"])
    major_minor = ".".join(layout["version"].split(".")[:2])
    project_dependency_exclusions = discover_project_dependency_exclusions_v1(
        site_packages,
        snapshot_source_root=vnext / "src",
    )
    dependency_policy = dependency_environment_policy_v1(
        python_major_minor=major_minor,
        excluded_project_entries=project_dependency_exclusions,
    )
    base_lib = base / "lib"
    # The uv-managed base runtime carries its own pip seed in site-packages,
    # while the qualified project environment carries the adopted dependency
    # denominator at another path.  Both map to the relocated environment, so
    # the base seed must be excluded or the two sources would collide.
    base_site_packages = PurePosixPath(f"python{major_minor}/site-packages")
    try:
        observed_base_site = site_packages.relative_to(base_lib)
    except ValueError:
        observed_base_site = None
    base_exclusions = (base_site_packages.as_posix(),)
    if observed_base_site is not None and observed_base_site != base_site_packages:
        base_exclusions = (
            base_site_packages.as_posix(),
            observed_base_site.as_posix(),
        )
    environment_contract_root = vnext / "validation" / "env-path-contracts"
    selected_profile_path = (
        environment_contract_root / "local-verification-profile-v4.candidate.json"
    )
    selected_profile_raw, selected_profile_resolved, _ = _read_stable_regular(
        selected_profile_path,
        authorized_root=root,
    )
    try:
        selected_profile = strict_json_loads(selected_profile_raw)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CandidateBoundaryError(
            "candidate_selected_verification_profile_unreadable", str(exc)
        ) from exc
    if not isinstance(selected_profile, Mapping):
        raise CandidateBoundaryError(
            "candidate_selected_verification_profile_unreadable", "not object"
        )
    closed_manifest_paths: set[Path] = set()
    commands = selected_profile.get("commands")
    if not isinstance(commands, list) or not commands:
        raise CandidateBoundaryError(
            "candidate_selected_verification_profile_invalid", "commands"
        )
    for command in commands:
        if not isinstance(command, Mapping):
            raise CandidateBoundaryError(
                "candidate_selected_verification_profile_invalid", "command"
            )
        reference = command.get("closed_test_manifest_ref")
        if not isinstance(reference, Mapping):
            raise CandidateBoundaryError(
                "candidate_selected_verification_profile_invalid",
                "closed_test_manifest_ref",
            )
        locator_path = _safe_relative_path(
            str(reference.get("locator", "")),
            code="candidate_closed_test_manifest_locator_invalid",
        )
        locator = locator_path.as_posix()
        if not locator.startswith("vnext/validation/env-path-contracts/"):
            raise CandidateBoundaryError(
                "candidate_closed_test_manifest_locator_outside_contract_root",
                locator,
            )
        closed_path = root / locator
        raw, resolved, _ = _read_stable_regular(closed_path, authorized_root=root)
        if digest_bytes(raw) != reference.get("content_digest"):
            raise CandidateBoundaryError(
                "candidate_closed_test_manifest_digest_mismatch", locator
            )
        closed_manifest_paths.add(resolved)

    # The candidate carries the contract schemas and one explicitly selected
    # verification profile with its closed test manifests.  Repository-local
    # resolved environment, adoption, host, containment and trace material is
    # deliberately excluded: the final snapshot path is re-observed later.
    environment_contract_material: list[tuple[str, Path, str, str]] = []
    for schema_path in sorted(environment_contract_root.glob("*.schema.json")):
        environment_contract_material.append(
            (
                "file",
                schema_path,
                f"vnext/validation/env-path-contracts/{schema_path.name}",
                "u10_contract_schema",
            )
        )
    environment_contract_material.append(
        (
            "file",
            selected_profile_resolved,
            "vnext/validation/env-path-contracts/local-verification-profile-v4.candidate.json",
            "u10_selected_verification_profile",
        )
    )
    for closed_path in sorted(closed_manifest_paths):
        environment_contract_material.append(
            (
                "file",
                closed_path,
                f"vnext/validation/env-path-contracts/{closed_path.name}",
                "u10_selected_closed_test_manifest",
            )
        )

    repository_material = [
        (
            "tree",
            vnext / "src",
            "vnext/src",
            "subject_and_broker_source",
        ),
        (
            "tree",
            vnext / "scripts",
            "vnext/scripts",
            "worker_and_candidate_tooling",
        ),
        (
            "file",
            vnext / "pyproject.toml",
            "vnext/pyproject.toml",
            "dependency_contract",
        ),
        (
            "file",
            vnext / "uv.lock",
            "vnext/uv.lock",
            "dependency_lock",
        ),
        (
            "file",
            vnext
            / "docs"
            / "governance-revision"
            / "public-operation-assurance-and-invocation-directive-2026-07-19.md",
            "vnext/docs/governance-revision/public-operation-assurance-and-invocation-directive-2026-07-19.md",
            "candidate_decision_owner_reference",
        ),
    ]
    repository_material.extend(environment_contract_material)
    mappings: list[dict[str, Any]] = [
        {
            "mapping_kind": mapping_kind,
            "source_path": str(source),
            "destination": destination,
            "role": role,
            "origin_kind": "repository_tree",
            "excluded_prefixes": [],
        }
        for mapping_kind, source, destination, role in repository_material
    ]
    mappings.extend(
        [
            {
                "mapping_kind": "file",
                "source_path": str(decision_resolved),
                "destination": "vnext/governance/u10-preactivation-decision.json",
                "role": "u10_preactivation_decision_record",
                "origin_kind": "trusted_human_decision_record",
                "excluded_prefixes": [],
            },
            {
                "mapping_kind": "file",
                "source_path": str(resolution_resolved),
                "destination": "vnext/governance/u10-worker-principal-resolution.json",
                "role": "u10_worker_principal_resolution",
                "origin_kind": "observed_worker_principal_resolution",
                "excluded_prefixes": [],
            },
            {
                "mapping_kind": "file",
                "source_path": str(observation_resolved),
                "destination": "vnext/governance/u10-worker-account-observation.json",
                "role": "u10_worker_account_observation",
                "origin_kind": "observed_worker_account_and_host",
                "excluded_prefixes": [],
            },
            {
                "mapping_kind": "file",
                "source_path": str(executable),
                "destination": "vnext/.venv/bin/python",
                "role": "python_interpreter",
                "origin_kind": "qualified_python_runtime",
                "excluded_prefixes": [],
            },
            {
                "mapping_kind": "tree",
                "source_path": str(base_lib),
                "destination": "vnext/.venv/lib",
                "role": "python_standard_runtime",
                "origin_kind": "qualified_python_runtime",
                "excluded_prefixes": list(base_exclusions),
            },
            {
                "mapping_kind": "tree",
                "source_path": str(site_packages),
                "destination": f"vnext/.venv/lib/python{major_minor}/site-packages",
                "role": "python_dependency_runtime",
                "origin_kind": "qualified_python_environment",
                "excluded_prefixes": project_dependency_exclusions,
            },
            {
                "mapping_kind": "file",
                "source_path": str(uv_path.resolve(strict=True)),
                "destination": "vnext/tools/uv",
                "role": "dependency_lock_verifier",
                "origin_kind": "qualified_uv_runtime",
                "excluded_prefixes": [],
            },
        ]
    )
    return _prepare_bundle_from_mappings(
        mappings=mappings,
        dependency_environment_policy=dependency_policy,
        repository_root=root,
        output=output,
        preactivation_decision=preactivation_decision,
        preactivation_decision_raw=decision_raw,
        preactivation_decision_locator=decision_resolved,
        worker_account_observation=worker_account_observation,
        worker_account_observation_raw=observation_raw,
        worker_account_observation_locator=observation_resolved,
        worker_principal_resolution=worker_principal_resolution,
        worker_principal_resolution_raw=resolution_raw,
        worker_principal_resolution_locator=resolution_resolved,
        installer_path=Path(__file__),
    )


def validate_bundle_manifest_v1(manifest: Mapping[str, Any]) -> None:
    _require_exact_fields(
        manifest,
        {
            "schema_version",
            "bundle_id",
            "bundle_version",
            "bundle_state",
            "notation_profile",
            "source_repository_binding",
            "preactivation_boundary_refs",
            "installer_ref",
            "worker_identity",
            "target",
            "payload_denominator",
            "dependency_environment_policy",
            "root_generated_entries",
            "human_install_authorization",
            "snapshot_activation",
            "u4_principal_authenticity",
            "formal_authority",
            "positive_assurance_allowed",
            "bundle_digest",
        },
        "candidate_bundle_fields_invalid",
    )
    if (
        manifest.get("schema_version") != BUNDLE_SCHEMA
        or manifest.get("bundle_version") != "2.0.0-candidate"
        or manifest.get("bundle_state") != "candidate_uninstalled"
        or manifest.get("notation_profile") != "entity-reference-notation/v0"
        or manifest.get("formal_authority") != "none"
        or manifest.get("positive_assurance_allowed") is not False
    ):
        raise CandidateBoundaryError("candidate_bundle_state_invalid", "top-level")
    bundle_id = manifest.get("bundle_id")
    if not isinstance(bundle_id, str) or _STABLE_ID.fullmatch(bundle_id) is None:
        raise CandidateBoundaryError("candidate_bundle_id_invalid", repr(bundle_id))
    payload = manifest.get("payload_denominator")
    if not isinstance(payload, Mapping):
        raise CandidateBoundaryError(
            "candidate_payload_denominator_invalid", repr(payload)
        )
    _require_exact_fields(
        payload,
        {
            "status",
            "directory_count",
            "directories",
            "entry_count",
            "entries",
            "payload_digest",
        },
        "candidate_payload_denominator_invalid",
    )
    entries = payload.get("entries")
    if (
        payload.get("status") != "closed"
        or not isinstance(entries, list)
        or not entries
    ):
        raise CandidateBoundaryError(
            "candidate_payload_denominator_invalid", "not closed"
        )
    if payload.get("entry_count") != len(entries):
        raise CandidateBoundaryError(
            "candidate_payload_count_mismatch", repr(payload.get("entry_count"))
        )
    paths: list[str] = []
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise CandidateBoundaryError("candidate_payload_entry_invalid", repr(entry))
        _require_exact_fields(
            entry,
            {"path", "role", "source_ref", "artifact_digest", "size", "intended_mode"},
            "candidate_payload_entry_invalid",
        )
        path = _safe_relative_path(
            str(entry.get("path", "")), code="candidate_payload_path_invalid"
        ).as_posix()
        paths.append(path)
        if entry.get("intended_mode") not in {"0400", "0500"}:
            raise CandidateBoundaryError("candidate_payload_mode_invalid", path)
        if not isinstance(entry.get("size"), int) or int(entry["size"]) < 0:
            raise CandidateBoundaryError("candidate_payload_size_invalid", path)
        artifact_digest = _require_digest(
            entry.get("artifact_digest"), "candidate_payload_digest_invalid"
        )
        source_ref = entry.get("source_ref")
        if not isinstance(source_ref, Mapping):
            raise CandidateBoundaryError("candidate_source_ref_invalid", path)
        _require_exact_fields(
            source_ref,
            {"origin_kind", "locator", "resolved_locator", "artifact_digest"},
            "candidate_source_ref_invalid",
        )
        if (
            _require_digest(
                source_ref.get("artifact_digest"), "candidate_source_digest_invalid"
            )
            != artifact_digest
        ):
            raise CandidateBoundaryError("candidate_source_digest_mismatch", path)
    if paths != sorted(paths) or len(paths) != len(set(paths)):
        raise CandidateBoundaryError(
            "candidate_payload_paths_not_closed", repr(paths[:20])
        )
    boundary = manifest.get("preactivation_boundary_refs")
    if not isinstance(boundary, Mapping):
        raise CandidateBoundaryError(
            "candidate_preactivation_boundary_invalid", repr(boundary)
        )
    _require_exact_fields(
        boundary,
        {
            "profile",
            "decision_record_ref",
            "worker_account_observation_ref",
            "worker_principal_resolution_ref",
            "threat_boundary",
            "worker_identity_policy",
            "qualification_scope",
            "hostile_code_assurance",
            "requalification_triggers",
            "binding_digest",
        },
        "candidate_preactivation_boundary_invalid",
    )
    expected_triggers = [
        "threat_boundary_change",
        "worker_identity_policy_change",
        "principal_resolution_change",
        "host_or_os_change",
        "sandbox_or_external_executor_change",
        "qualified_test_denominator_change",
    ]
    for field, role in (
        ("decision_record_ref", "u10_preactivation_decision_record"),
        ("worker_account_observation_ref", "u10_worker_account_observation"),
        ("worker_principal_resolution_ref", "u10_worker_principal_resolution"),
    ):
        reference = boundary.get(field)
        if not isinstance(reference, Mapping):
            raise CandidateBoundaryError(
                "candidate_preactivation_boundary_invalid", field
            )
        _require_exact_fields(
            reference,
            {
                "record_id",
                "source_locator",
                "source_artifact_digest",
                "bundled_locator",
                "bundled_artifact_digest",
                "semantic_digest",
            },
            "candidate_preactivation_boundary_invalid",
        )
        for digest_field in (
            "source_artifact_digest",
            "bundled_artifact_digest",
            "semantic_digest",
        ):
            _require_digest(
                reference.get(digest_field),
                "candidate_preactivation_boundary_invalid",
            )
        matching = [
            entry
            for entry in entries
            if entry["path"] == reference.get("bundled_locator")
            and entry["role"] == role
            and entry["artifact_digest"]
            == reference.get("bundled_artifact_digest")
            and entry["source_ref"]["locator"]
            == reference.get("source_locator")
            and entry["source_ref"]["artifact_digest"]
            == reference.get("source_artifact_digest")
        ]
        if len(matching) != 1:
            raise CandidateBoundaryError(
                "candidate_preactivation_boundary_denominator_invalid", field
            )
    if (
        boundary.get("profile") != "u10-local-bounded-preactivation-binding/v1"
        or boundary.get("threat_boundary")
        != "local_bounded_repository_suite_only"
        or boundary.get("worker_identity_policy")
        not in {
            "dedicated_non_login_service_principal",
            "current_user_501_20_empty_supplementary_groups",
        }
        or boundary.get("qualification_scope")
        != "repository_owned_closed_verification_suite_only"
        or boundary.get("hostile_code_assurance")
        != "prohibited_requires_separate_external_executor_profile"
        or boundary.get("requalification_triggers") != expected_triggers
        or _require_digest(
            boundary.get("binding_digest"),
            "candidate_preactivation_boundary_invalid",
        )
        != sealed_digest(boundary, "binding_digest")
    ):
        raise CandidateBoundaryError(
            "candidate_preactivation_boundary_invalid", "binding or scope"
        )
    directories = payload.get("directories")
    if (
        not isinstance(directories, list)
        or any(not isinstance(item, str) for item in directories)
        or directories != _payload_directory_denominator_v1(paths)
        or payload.get("directory_count") != len(directories)
    ):
        raise CandidateBoundaryError(
            "candidate_payload_directory_denominator_invalid", repr(directories)
        )
    _validate_dependency_environment_policy_v1(
        manifest.get("dependency_environment_policy"), payload_paths=paths
    )
    expected_payload_digest = digest_bytes(
        canonical_json_bytes({"directories": directories, "entries": entries})
    )
    if (
        _require_digest(
            payload.get("payload_digest"), "candidate_payload_digest_invalid"
        )
        != expected_payload_digest
    ):
        raise CandidateBoundaryError("candidate_payload_digest_mismatch", bundle_id)
    expected_bundle_id = f"candidate.u10.{expected_payload_digest['value']}"
    if bundle_id != expected_bundle_id:
        raise CandidateBoundaryError("candidate_bundle_identity_mismatch", bundle_id)
    target = manifest.get("target")
    if not isinstance(target, Mapping):
        raise CandidateBoundaryError("candidate_target_invalid", repr(target))
    _require_exact_fields(
        target,
        {
            "candidate_root",
            "candidate_path",
            "candidate_install_ledger_root",
            "candidate_install_ledger_policy",
            "active_snapshot_root",
            "active_trust_store",
            "install_scope",
        },
        "candidate_target_invalid",
    )
    if target != {
        "candidate_root": str(CANDIDATE_ROOT),
        "candidate_path": str(CANDIDATE_ROOT / bundle_id),
        "candidate_install_ledger_root": str(CANDIDATE_INSTALL_LEDGER_ROOT),
        "candidate_install_ledger_policy": _candidate_install_ledger_policy_v1(),
        "active_snapshot_root": str(SNAPSHOT_ROOT),
        "active_trust_store": str(TRUST_STORE_PATH),
        "install_scope": (
            "inactive_candidate_tree_and_append_only_install_ledger_only"
        ),
    }:
        raise CandidateBoundaryError("candidate_target_invalid", repr(target))
    generated = manifest.get("root_generated_entries")
    if not isinstance(generated, list) or len(generated) != 1:
        raise CandidateBoundaryError(
            "candidate_generated_entries_invalid", repr(generated)
        )
    generated_entry = generated[0]
    if not isinstance(generated_entry, Mapping) or set(generated_entry) != {
        "path",
        "generation_profile",
        "content_template",
        "intended_mode",
    }:
        raise CandidateBoundaryError(
            "candidate_generated_entries_invalid", repr(generated_entry)
        )
    if (
        generated_entry.get("path") != "vnext/.venv/pyvenv.cfg"
        or generated_entry.get("generation_profile")
        != "u10-relocatable-pyvenv-config/v1"
        or generated_entry.get("intended_mode") != "0400"
        or generated_entry.get("content_template") != PYVENV_TEMPLATE
        or generated_entry["path"] in set(paths)
    ):
        raise CandidateBoundaryError(
            "candidate_generated_entries_invalid", repr(generated_entry)
        )
    installer_ref = manifest.get("installer_ref")
    if not isinstance(installer_ref, Mapping):
        raise CandidateBoundaryError(
            "candidate_installer_ref_invalid", repr(installer_ref)
        )
    _require_exact_fields(
        installer_ref,
        {
            "record_id",
            "source_locator",
            "required_bootstrap_locator",
            "entrypoint_source_locator",
            "required_entrypoint_locator",
            "entrypoint_artifact_digest",
            "required_shell_locator",
            "shell_resolved_locator",
            "shell_artifact_digest",
            "shell_flags",
            "environment_cleaner_locator",
            "environment_cleaner_resolved_locator",
            "environment_cleaner_artifact_digest",
            "environment_policy",
            "os_injected_environment_policy",
            "discovery_launcher_locator",
            "discovery_launcher_resolved_locator",
            "discovery_launcher_artifact_digest",
            "effective_interpreter_locator",
            "effective_interpreter_artifact_digest",
            "required_effective_interpreter_path_locator",
            "effective_interpreter_path_artifact_digest",
            "artifact_digest",
        },
        "candidate_installer_ref_invalid",
    )
    if (
        installer_ref.get("record_id")
        != "installer.semantic-guard.u10.root-candidate.v1"
        or installer_ref.get("required_bootstrap_locator")
        != str(BOOTSTRAP_INSTALLER_PATH)
        or installer_ref.get("discovery_launcher_locator")
        != str(ROOT_BOOTSTRAP_DISCOVERY_LAUNCHER)
        or installer_ref.get("required_effective_interpreter_path_locator")
        != str(ROOT_EFFECTIVE_PYTHON_PATH_FILE)
        or installer_ref.get("required_entrypoint_locator")
        != str(ROOT_INSTALLER_ENTRYPOINT_PATH)
        or installer_ref.get("required_shell_locator")
        != str(ROOT_BOOTSTRAP_SHELL)
        or installer_ref.get("environment_cleaner_locator")
        != str(ROOT_ENVIRONMENT_CLEANER)
        or installer_ref.get("shell_flags") != ["-p"]
        or installer_ref.get("environment_policy")
        != "privileged_sh_p_then_env_i_direct_effective_execve/v3"
        or installer_ref.get("os_injected_environment_policy")
        != "cf_user_text_encoding_uid_bound_then_removed/v1"
    ):
        raise CandidateBoundaryError(
            "candidate_installer_ref_invalid", repr(installer_ref)
        )
    _require_digest(
        installer_ref.get("artifact_digest"), "candidate_installer_digest_invalid"
    )
    _require_digest(
        installer_ref.get("entrypoint_artifact_digest"),
        "candidate_installer_entrypoint_digest_invalid",
    )
    _require_digest(
        installer_ref.get("shell_artifact_digest"),
        "candidate_installer_shell_digest_invalid",
    )
    _require_digest(
        installer_ref.get("environment_cleaner_artifact_digest"),
        "candidate_installer_environment_cleaner_digest_invalid",
    )
    _require_digest(
        installer_ref.get("discovery_launcher_artifact_digest"),
        "candidate_installer_discovery_launcher_digest_invalid",
    )
    _require_digest(
        installer_ref.get("effective_interpreter_artifact_digest"),
        "candidate_installer_interpreter_digest_invalid",
    )
    _require_digest(
        installer_ref.get("effective_interpreter_path_artifact_digest"),
        "candidate_installer_interpreter_path_digest_invalid",
    )
    effective_interpreter = Path(
        str(installer_ref.get("effective_interpreter_locator", ""))
    )
    discovery_resolved = Path(
        str(installer_ref.get("discovery_launcher_resolved_locator", ""))
    )
    shell_resolved = Path(str(installer_ref.get("shell_resolved_locator", "")))
    cleaner_resolved = Path(
        str(installer_ref.get("environment_cleaner_resolved_locator", ""))
    )
    if (
        not effective_interpreter.is_absolute()
        or effective_interpreter
        != Path(os.path.normpath(str(effective_interpreter)))
        or not discovery_resolved.is_absolute()
        or discovery_resolved
        != Path(os.path.normpath(str(discovery_resolved)))
        or not shell_resolved.is_absolute()
        or shell_resolved != Path(os.path.normpath(str(shell_resolved)))
        or not cleaner_resolved.is_absolute()
        or cleaner_resolved != Path(os.path.normpath(str(cleaner_resolved)))
        or installer_ref["effective_interpreter_path_artifact_digest"]
        != digest_bytes(f"{effective_interpreter}\n".encode("utf-8"))
    ):
        raise CandidateBoundaryError(
            "candidate_installer_interpreter_binding_invalid",
            repr(installer_ref),
        )
    worker_identity = manifest.get("worker_identity")
    if not isinstance(worker_identity, Mapping):
        raise CandidateBoundaryError(
            "candidate_worker_identity_invalid", repr(worker_identity)
        )
    _require_exact_fields(
        worker_identity,
        {
            "uid",
            "gid",
            "account_supplementary_gids",
            "effective_supplementary_gids",
            "umask",
            "login_shell",
            "non_login",
            "root_prohibited",
            "principal_entity_ref",
            "principal_resolution_digest",
        },
        "candidate_worker_identity_invalid",
    )
    if (
        not isinstance(worker_identity.get("uid"), int)
        or worker_identity["uid"] <= 0
        or not isinstance(worker_identity.get("gid"), int)
        or worker_identity["gid"] <= 0
        or not isinstance(worker_identity.get("account_supplementary_gids"), list)
        or any(
            not isinstance(group_id, int)
            or isinstance(group_id, bool)
            or group_id <= 0
            for group_id in worker_identity["account_supplementary_gids"]
        )
        or worker_identity["account_supplementary_gids"]
        != sorted(set(worker_identity["account_supplementary_gids"]))
        or worker_identity["gid"]
        in worker_identity["account_supplementary_gids"]
        or worker_identity.get("effective_supplementary_gids") != []
        or worker_identity.get("umask") != 0o77
        or not isinstance(worker_identity.get("login_shell"), str)
        or not worker_identity["login_shell"]
        or not isinstance(worker_identity.get("non_login"), bool)
        or worker_identity.get("root_prohibited") is not True
        or _ENTITY_REF.fullmatch(
            str(worker_identity.get("principal_entity_ref", ""))
        )
        is None
        or _require_digest(
            worker_identity.get("principal_resolution_digest"),
            "candidate_worker_identity_invalid",
        )
        != boundary["worker_principal_resolution_ref"]["semantic_digest"]
    ):
        raise CandidateBoundaryError(
            "candidate_worker_identity_invalid", repr(worker_identity)
        )
    authorization = manifest.get("human_install_authorization")
    activation = manifest.get("snapshot_activation")
    u4 = manifest.get("u4_principal_authenticity")
    if authorization != {
        "status": "pending",
        "authorized_operation": None,
        "authorization_ref": None,
    }:
        raise CandidateBoundaryError(
            "candidate_embedded_authorization_prohibited", repr(authorization)
        )
    if activation != {
        "status": "not_authorized",
        "required_follow_up": SNAPSHOT_ACTIVATION_FOLLOW_UP,
    }:
        raise CandidateBoundaryError(
            "candidate_activation_state_invalid", repr(activation)
        )
    if (
        not isinstance(u4, Mapping)
        or u4.get("requirement_id") != "U-4"
        or u4.get("status") != "unresolved"
    ):
        raise CandidateBoundaryError("candidate_u4_state_invalid", repr(u4))
    if _require_digest(
        manifest.get("bundle_digest"), "candidate_bundle_digest_invalid"
    ) != sealed_digest(manifest, "bundle_digest"):
        raise CandidateBoundaryError("candidate_bundle_digest_mismatch", bundle_id)


def snapshot_lock_check_spec_v1(
    manifest: Mapping[str, Any], *, candidate_payload: Path
) -> dict[str, Any]:
    """Render the exact non-mutating, non-root lock check for activation review."""

    validate_bundle_manifest_v1(manifest)
    try:
        payload = candidate_payload.resolve(strict=True)
    except OSError as exc:
        raise CandidateBoundaryError(
            "candidate_lock_check_payload_unavailable", str(candidate_payload)
        ) from exc
    if not payload.is_dir() or payload.is_symlink():
        raise CandidateBoundaryError(
            "candidate_lock_check_payload_invalid", str(payload)
        )
    policy = manifest["dependency_environment_policy"]
    lock_validation = policy["lock_validation"]
    dependency_root = payload / Path(
        *_safe_relative_path(
            str(policy["dependency_import_root"]),
            code="candidate_dependency_import_root_invalid",
        ).parts
    )
    uv = payload / Path(
        *_safe_relative_path(
            str(lock_validation["uv_executable"]),
            code="candidate_lock_check_tool_invalid",
        ).parts
    )
    python = payload / Path(
        *_safe_relative_path(
            str(lock_validation["python_executable"]),
            code="candidate_lock_check_python_invalid",
        ).parts
    )
    working_directory = payload / Path(
        *_safe_relative_path(
            str(lock_validation["working_directory"]),
            code="candidate_lock_check_working_directory_invalid",
        ).parts
    )
    if not dependency_root.is_dir() or dependency_root.is_symlink():
        raise CandidateBoundaryError(
            "candidate_dependency_import_root_invalid", str(dependency_root)
        )
    for excluded in policy["excluded_project_entries"]:
        candidate = dependency_root / str(excluded)
        try:
            candidate.lstat()
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise CandidateBoundaryError(
                "candidate_project_dependency_state_unreadable", str(candidate)
            ) from exc
        raise CandidateBoundaryError(
            "candidate_project_dependency_leaked", str(candidate)
        )
    for path, code in (
        (uv, "candidate_lock_check_tool_invalid"),
        (python, "candidate_lock_check_python_invalid"),
        (
            payload / ROOT_BROKER_BOOTSTRAP_PATH,
            "candidate_root_broker_bootstrap_missing",
        ),
        (payload / "vnext/pyproject.toml", "candidate_dependency_contract_missing"),
        (payload / "vnext/uv.lock", "candidate_dependency_lock_missing"),
    ):
        try:
            observed = path.lstat()
        except OSError as exc:
            raise CandidateBoundaryError(code, str(path)) from exc
        if stat.S_ISLNK(observed.st_mode) or not stat.S_ISREG(observed.st_mode):
            raise CandidateBoundaryError(code, str(path))
    if not working_directory.is_dir() or working_directory.is_symlink():
        raise CandidateBoundaryError(
            "candidate_lock_check_working_directory_invalid",
            str(working_directory),
        )
    source_root = payload / SNAPSHOT_SOURCE_ROOT
    if not source_root.is_dir() or source_root.is_symlink():
        raise CandidateBoundaryError(
            "candidate_snapshot_source_root_invalid", str(source_root)
        )
    placeholder = "{candidate_payload}"
    rendered_arguments = [
        str(item).replace(placeholder, str(payload))
        for item in lock_validation["arguments"]
    ]
    return {
        "profile": LOCK_VALIDATION_PROFILE,
        "cwd": str(working_directory),
        "argv": [str(uv), *rendered_arguments],
        "environment": {
            "LC_ALL": "C",
            "NO_COLOR": "1",
            "PATH": "",
            "PYTHONDONTWRITEBYTECODE": "1",
            "UV_NO_PROGRESS": "1",
            "UV_OFFLINE": "1",
            "UV_PYTHON_DOWNLOADS": "never",
        },
        "execution_identity": "non_root_worker",
        "mutation_authority": "none",
        "success_condition": "exit_0_from_non_mutating_check",
        "snapshot_activation_authority": "none",
    }


def _validate_source_bundle_path_v1(bundle_root: Path) -> Path:
    if (
        not bundle_root.is_absolute()
        or bundle_root != Path(os.path.normpath(str(bundle_root)))
    ):
        raise CandidateBoundaryError(
            "candidate_source_bundle_path_untrusted", str(bundle_root)
        )
    try:
        resolved = bundle_root.resolve(strict=True)
        observed = bundle_root.lstat()
    except OSError as exc:
        raise CandidateBoundaryError(
            "candidate_source_bundle_path_unavailable", str(bundle_root)
        ) from exc
    if (
        resolved != bundle_root
        or stat.S_ISLNK(observed.st_mode)
        or not stat.S_ISDIR(observed.st_mode)
    ):
        raise CandidateBoundaryError(
            "candidate_source_bundle_path_untrusted", str(bundle_root)
        )
    return bundle_root


def _load_bundle_manifest_raw_v1(
    bundle_root: Path,
) -> tuple[dict[str, Any], bytes]:
    _validate_source_bundle_path_v1(bundle_root)
    raw, _resolved, _observed = _read_stable_regular(
        bundle_root / MANIFEST_NAME, authorized_root=bundle_root
    )
    try:
        value = strict_json_loads(raw)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CandidateBoundaryError(
            "candidate_manifest_unreadable", str(bundle_root)
        ) from exc
    if not isinstance(value, dict):
        raise CandidateBoundaryError("candidate_manifest_unreadable", str(bundle_root))
    validate_bundle_manifest_v1(value)
    return value, raw


def _load_bundle_manifest(bundle_root: Path) -> dict[str, Any]:
    value, _raw = _load_bundle_manifest_raw_v1(bundle_root)
    return value


def _enumerate_payload(bundle_root: Path) -> tuple[set[str], set[str]]:
    payload = bundle_root / "payload"
    if not payload.is_dir() or payload.is_symlink():
        raise CandidateBoundaryError("candidate_payload_root_invalid", str(payload))
    observed: set[str] = set()
    observed_directories: set[str] = set()
    for raw_directory, directory_names, file_names in os.walk(
        payload, topdown=True, followlinks=False
    ):
        base = Path(raw_directory)
        _assert_no_extended_acl(
            base, code="candidate_payload_directory_extended_acl"
        )
        for name in sorted(directory_names):
            path = base / name
            item = path.lstat()
            if stat.S_ISLNK(item.st_mode) or not stat.S_ISDIR(item.st_mode):
                raise CandidateBoundaryError(
                    "candidate_payload_special_entry", str(path)
                )
            _assert_no_extended_acl(
                path, code="candidate_payload_directory_extended_acl"
            )
            observed_directories.add(path.relative_to(payload).as_posix())
        for name in sorted(file_names):
            path = base / name
            item = path.lstat()
            if not stat.S_ISREG(item.st_mode) or item.st_nlink != 1:
                raise CandidateBoundaryError(
                    "candidate_payload_special_entry", str(path)
                )
            observed.add(path.relative_to(payload).as_posix())
    return observed, observed_directories


def validate_bundle_files_v1(bundle_root: Path, manifest: Mapping[str, Any]) -> None:
    try:
        bundle_names = {entry.name for entry in os.scandir(bundle_root)}
    except OSError as exc:
        raise CandidateBoundaryError(
            "candidate_bundle_root_unreadable", str(bundle_root)
        ) from exc
    expected_bundle_names = {"payload", MANIFEST_NAME}
    if bundle_names != expected_bundle_names:
        raise CandidateBoundaryError(
            "candidate_bundle_root_denominator_mismatch",
            f"missing={sorted(expected_bundle_names - bundle_names)!r}; "
            f"extra={sorted(bundle_names - expected_bundle_names)!r}",
        )
    _assert_no_extended_acl(
        bundle_root, code="candidate_bundle_root_extended_acl"
    )
    expected = {
        str(item["path"]) for item in manifest["payload_denominator"]["entries"]
    }
    observed, observed_directories = _enumerate_payload(bundle_root)
    if observed != expected:
        raise CandidateBoundaryError(
            "candidate_payload_denominator_mismatch",
            f"missing={sorted(expected - observed)!r}; extra={sorted(observed - expected)!r}",
        )
    expected_directories = set(manifest["payload_denominator"]["directories"])
    if observed_directories != expected_directories:
        raise CandidateBoundaryError(
            "candidate_payload_directory_denominator_mismatch",
            f"missing={sorted(expected_directories - observed_directories)!r}; "
            f"extra={sorted(observed_directories - expected_directories)!r}",
        )
    for entry in manifest["payload_denominator"]["entries"]:
        path = bundle_root / "payload" / Path(*PurePosixPath(str(entry["path"])).parts)
        raw, _resolved, observed_stat = _read_stable_regular(
            path, authorized_root=bundle_root
        )
        if (
            digest_bytes(raw) != entry["artifact_digest"]
            or len(raw) != entry["size"]
            or observed_stat.st_nlink != 1
        ):
            raise CandidateBoundaryError(
                "candidate_payload_artifact_mismatch", str(entry["path"])
            )
    boundary = manifest["preactivation_boundary_refs"]
    loaded: dict[str, tuple[dict[str, Any], bytes]] = {}
    for field in (
        "decision_record_ref",
        "worker_account_observation_ref",
        "worker_principal_resolution_ref",
    ):
        reference = boundary[field]
        path = bundle_root / "payload" / Path(
            *_safe_relative_path(
                str(reference["bundled_locator"]),
                code="candidate_preactivation_boundary_invalid",
            ).parts
        )
        raw, _resolved, _observed = _read_stable_regular(
            path, authorized_root=bundle_root
        )
        if digest_bytes(raw) != reference["bundled_artifact_digest"]:
            raise CandidateBoundaryError(
                "candidate_preactivation_boundary_artifact_mismatch", field
            )
        try:
            value = strict_json_loads(raw)
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise CandidateBoundaryError(
                "candidate_preactivation_boundary_unreadable", field
            ) from exc
        if not isinstance(value, dict):
            raise CandidateBoundaryError(
                "candidate_preactivation_boundary_unreadable", field
            )
        loaded[field] = (value, raw)
    decision, decision_raw = loaded["decision_record_ref"]
    observation, observation_raw = loaded["worker_account_observation_ref"]
    resolution, _resolution_raw = loaded["worker_principal_resolution_ref"]
    validate_preactivation_decision_v1(decision)
    validate_worker_principal_resolution_v1(
        resolution,
        decision=decision,
        decision_raw=decision_raw,
        decision_locator=Path(boundary["decision_record_ref"]["source_locator"]),
        observation=observation,
        observation_raw=observation_raw,
        observation_locator=Path(
            boundary["worker_account_observation_ref"]["source_locator"]
        ),
        reobserve_current=True,
    )
    if (
        decision["decision_digest"]
        != boundary["decision_record_ref"]["semantic_digest"]
        or observation["observation_digest"]
        != boundary["worker_account_observation_ref"]["semantic_digest"]
        or resolution["resolution_digest"]
        != boundary["worker_principal_resolution_ref"]["semantic_digest"]
        or decision["threat_boundary_selection"] != boundary["threat_boundary"]
        or decision["worker_identity_selection"]
        != boundary["worker_identity_policy"]
        or resolution["resolution_state"] != "resolved"
        or _entity_id_v1(
            resolution["principal_entity_ref"],
            code="candidate_preactivation_boundary_context_mismatch",
        )
        != _entity_id_v1(
            manifest["worker_identity"]["principal_entity_ref"],
            code="candidate_preactivation_boundary_context_mismatch",
        )
        or resolution["uid"] != manifest["worker_identity"]["uid"]
        or resolution["gid"] != manifest["worker_identity"]["gid"]
        or resolution["account_supplementary_gids"]
        != manifest["worker_identity"]["account_supplementary_gids"]
        or resolution["effective_supplementary_gids"]
        != manifest["worker_identity"]["effective_supplementary_gids"]
        or resolution["login_shell"]
        != manifest["worker_identity"]["login_shell"]
        or resolution["non_login"]
        != manifest["worker_identity"]["non_login"]
    ):
        raise CandidateBoundaryError(
            "candidate_preactivation_boundary_context_mismatch",
            str(decision.get("decision_id")),
        )


def validate_install_authorization_v1(
    authorization: Mapping[str, Any],
    manifest: Mapping[str, Any] | None = None,
    *,
    bundle_root: Path | None = None,
    manifest_raw: bytes | None = None,
) -> None:
    _require_exact_fields(
        authorization,
        {
            "schema_version",
            "authorization_id",
            "authorization_version",
            "record_kind",
            "bundle_id",
            "bundle_digest",
            "source_bundle_path",
            "source_manifest_artifact_digest",
            "target_candidate_path",
            "authorized_operation",
            "human_decision",
            "decision_owner",
            "recorded_at",
            "u4_principal_authenticity",
            "authority_scope",
            "candidate_install_ledger",
            "formal_authority",
            "positive_assurance_allowed",
            "authorization_digest",
        },
        "candidate_install_authorization_invalid",
    )
    authorization_id = authorization.get("authorization_id")
    if (
        not isinstance(authorization_id, str)
        or _LEDGER_COMPONENT_ID.fullmatch(authorization_id) is None
    ):
        raise CandidateBoundaryError(
            "candidate_install_authorization_invalid", repr(authorization_id)
        )
    ledger_binding = authorization.get("candidate_install_ledger")
    if not isinstance(ledger_binding, Mapping):
        raise CandidateBoundaryError(
            "candidate_install_authorization_invalid", "ledger binding"
        )
    _require_exact_fields(
        ledger_binding,
        {"root", "policy", "policy_digest"},
        "candidate_install_authorization_invalid",
    )
    expected_ledger_policy = _candidate_install_ledger_policy_v1()
    bundle_id = authorization.get("bundle_id")
    source_bundle_path = Path(str(authorization.get("source_bundle_path", "")))
    _validate_source_bundle_path_v1(source_bundle_path)
    if (
        authorization.get("schema_version") != AUTHORIZATION_SCHEMA
        or authorization.get("authorization_version") != "1.0.0"
        or authorization.get("record_kind")
        != "candidate_install_authorization"
        or not isinstance(bundle_id, str)
        or _LEDGER_COMPONENT_ID.fullmatch(bundle_id) is None
        or authorization.get("target_candidate_path")
        != str(CANDIDATE_ROOT / bundle_id)
        or authorization.get("authorized_operation") != "install_candidate_only"
        or authorization.get("human_decision") != "accept"
        or authorization.get("decision_owner") != "human"
        or authorization.get("authority_scope") != "u10_candidate_install_only"
        or ledger_binding.get("root") != str(CANDIDATE_INSTALL_LEDGER_ROOT)
        or ledger_binding.get("policy") != expected_ledger_policy
        or ledger_binding.get("policy_digest")
        != digest_bytes(canonical_json_bytes(expected_ledger_policy))
        or authorization.get("u4_principal_authenticity") != "unresolved"
        or authorization.get("formal_authority")
        != "human_candidate_install_decision_only"
        or authorization.get("positive_assurance_allowed") is not False
    ):
        raise CandidateBoundaryError(
            "candidate_install_authorization_invalid", "binding or authority"
        )
    _parse_rfc3339_v1(
        authorization.get("recorded_at"),
        code="candidate_install_authorization_time_invalid",
    )
    if _require_digest(
        authorization.get("authorization_digest"),
        "candidate_install_authorization_digest_invalid",
    ) != sealed_digest(authorization, "authorization_digest"):
        raise CandidateBoundaryError(
            "candidate_install_authorization_digest_mismatch", str(authorization_id)
        )
    _require_digest(
        authorization.get("bundle_digest"),
        "candidate_install_authorization_bundle_digest_invalid",
    )
    _require_digest(
        authorization.get("source_manifest_artifact_digest"),
        "candidate_install_authorization_manifest_digest_invalid",
    )
    if manifest is None:
        return
    expected_raw = manifest_raw
    if expected_raw is None:
        expected_raw = (
            json.dumps(
                manifest,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
                allow_nan=False,
            ).encode("utf-8")
            + b"\n"
        )
    if (
        authorization.get("bundle_id") != manifest["bundle_id"]
        or authorization.get("bundle_digest") != manifest["bundle_digest"]
        or authorization.get("target_candidate_path")
        != manifest["target"]["candidate_path"]
        or authorization.get("source_manifest_artifact_digest")
        != digest_bytes(expected_raw)
        or (bundle_root is not None and source_bundle_path != bundle_root)
    ):
        raise CandidateBoundaryError(
            "candidate_install_authorization_invalid",
            "source bundle or manifest binding",
        )


def _validate_owned_directory(path: Path, *, required_uid: int) -> None:
    try:
        observed = path.lstat()
    except OSError as exc:
        raise CandidateBoundaryError(
            "candidate_install_root_unavailable", str(path)
        ) from exc
    if (
        stat.S_ISLNK(observed.st_mode)
        or not stat.S_ISDIR(observed.st_mode)
        or observed.st_uid != required_uid
        or observed.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
    ):
        raise CandidateBoundaryError("candidate_install_root_untrusted", str(path))
    _assert_no_extended_acl(path, code="candidate_install_root_extended_acl")


def _validate_owned_directory_chain(path: Path, *, required_uid: int) -> None:
    if not path.is_absolute():
        raise CandidateBoundaryError("candidate_install_root_untrusted", str(path))
    current = Path(path.anchor)
    _validate_owned_directory(current, required_uid=required_uid)
    for part in path.parts[1:]:
        current /= part
        _validate_owned_directory(current, required_uid=required_uid)


def _validate_owned_directory_exact_mode_v1(
    path: Path, *, required_uid: int, required_mode: int
) -> None:
    _validate_owned_directory(path, required_uid=required_uid)
    if stat.S_IMODE(path.lstat().st_mode) != required_mode:
        raise CandidateBoundaryError(
            "candidate_install_ledger_directory_mode_mismatch", str(path)
        )


def _prepare_candidate_install_ledger_v1(
    *,
    candidate_root: Path,
    ledger_root: Path,
    required_uid: int,
    enforce_fixed_target: bool,
) -> None:
    expected = CANDIDATE_INSTALL_LEDGER_ROOT
    if enforce_fixed_target and ledger_root != expected:
        raise CandidateBoundaryError(
            "candidate_install_ledger_override", str(ledger_root)
        )
    if ledger_root.parent.parent != candidate_root.parent:
        raise CandidateBoundaryError(
            "candidate_install_ledger_root_mismatch", str(ledger_root)
        )
    _validate_owned_directory(candidate_root.parent, required_uid=required_uid)
    _ensure_directory_exact(ledger_root.parent, mode=0o700)
    _ensure_directory_exact(ledger_root, mode=0o700)
    _validate_owned_directory_exact_mode_v1(
        ledger_root.parent, required_uid=required_uid, required_mode=0o700
    )
    _validate_owned_directory_exact_mode_v1(
        ledger_root, required_uid=required_uid, required_mode=0o700
    )
    _fsync_directory_v1(
        ledger_root.parent, code="candidate_install_ledger_directory_fsync_failed"
    )
    _fsync_directory_v1(
        candidate_root.parent, code="candidate_install_ledger_directory_fsync_failed"
    )


def _ledger_record_paths_v1(
    authorization: Mapping[str, Any], *, ledger_root: Path
) -> tuple[Path, Path, Path]:
    authorization_id = str(authorization["authorization_id"])
    if _LEDGER_COMPONENT_ID.fullmatch(authorization_id) is None:
        raise CandidateBoundaryError(
            "candidate_install_authorization_id_invalid", authorization_id
        )
    return (
        ledger_root / f"{authorization_id}.authorization.json",
        ledger_root / f"{authorization_id}.consumption.json",
        ledger_root / f"{authorization_id}.receipt.json",
    )


@contextmanager
def _candidate_install_transaction_lock_v1(
    *,
    manifest: Mapping[str, Any],
    ledger_root: Path,
    required_uid: int,
) -> Iterator[None]:
    target_identity = (
        f"{manifest['bundle_id']}\0{manifest['target']['candidate_path']}"
    )
    lock_name = hashlib.sha256(target_identity.encode("utf-8")).hexdigest()
    lock_path = ledger_root / f".target-lock.{lock_name}"
    base_flags = (
        os.O_RDWR
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    created = False
    try:
        descriptor = os.open(
            lock_path, base_flags | os.O_CREAT | os.O_EXCL, 0o600
        )
        created = True
    except FileExistsError:
        try:
            direct = lock_path.lstat()
        except OSError as exc:
            raise CandidateBoundaryError(
                "candidate_install_lock_open_failed", str(lock_path)
            ) from exc
        if (
            stat.S_ISLNK(direct.st_mode)
            or not stat.S_ISREG(direct.st_mode)
            or direct.st_uid != required_uid
            or direct.st_nlink != 1
            or stat.S_IMODE(direct.st_mode) != 0o600
        ):
            raise CandidateBoundaryError(
                "candidate_install_lock_invalid", str(lock_path)
            )
        try:
            descriptor = os.open(lock_path, base_flags)
        except OSError as exc:
            raise CandidateBoundaryError(
                "candidate_install_lock_open_failed", str(lock_path)
            ) from exc
    except OSError as exc:
        raise CandidateBoundaryError(
            "candidate_install_lock_open_failed", str(lock_path)
        ) from exc
    try:
        if created:
            os.fchmod(descriptor, 0o600)
        os.fsync(descriptor)
        observed = os.fstat(descriptor)
        rebound = lock_path.lstat()
        if (
            not stat.S_ISREG(observed.st_mode)
            or observed.st_uid != required_uid
            or observed.st_nlink != 1
            or stat.S_IMODE(observed.st_mode) != 0o600
            or rebound.st_dev != observed.st_dev
            or rebound.st_ino != observed.st_ino
        ):
            raise CandidateBoundaryError(
                "candidate_install_lock_invalid", str(lock_path)
            )
        _assert_no_extended_acl(
            lock_path, code="candidate_install_lock_extended_acl"
        )
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
        except OSError as exc:
            raise CandidateBoundaryError(
                "candidate_install_lock_failed", str(lock_path)
            ) from exc
        _fsync_directory_v1(
            ledger_root, code="candidate_install_ledger_directory_fsync_failed"
        )
        yield
    finally:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)


def _cleanup_stale_install_stages_v1(
    *, candidate_root: Path, authorization: Mapping[str, Any], required_uid: int
) -> None:
    authorization_digest = _require_digest(
        authorization["authorization_digest"],
        "candidate_install_authorization_digest_invalid",
    )["value"]
    prefix = f".installing.{authorization_digest}."
    removed = False
    for path in tuple(candidate_root.iterdir()):
        if not path.name.startswith(prefix):
            continue
        observed = path.lstat()
        if (
            stat.S_ISLNK(observed.st_mode)
            or not stat.S_ISDIR(observed.st_mode)
            or observed.st_uid != required_uid
        ):
            raise CandidateBoundaryError(
                "candidate_install_stale_stage_invalid", str(path)
            )
        _assert_no_extended_acl(
            path, code="candidate_install_stale_stage_extended_acl"
        )
        _remove_private_tree_v1(path)
        removed = True
    if removed:
        _fsync_directory_v1(
            candidate_root, code="candidate_install_stale_stage_cleanup_fsync_failed"
        )


def _read_ledger_record_raw_v1(
    path: Path, *, ledger_root: Path, required_uid: int
) -> tuple[dict[str, Any], bytes]:
    try:
        direct = path.lstat()
    except OSError as exc:
        raise CandidateBoundaryError(
            "candidate_install_ledger_record_unavailable", str(path)
        ) from exc
    if stat.S_ISLNK(direct.st_mode) or not stat.S_ISREG(direct.st_mode):
        raise CandidateBoundaryError(
            "candidate_install_ledger_record_invalid", str(path)
        )
    if (
        direct.st_uid != required_uid
        or stat.S_IMODE(direct.st_mode) != 0o400
        or direct.st_nlink not in {1, 2}
    ):
        raise CandidateBoundaryError(
            "candidate_install_ledger_record_invalid", str(path)
        )
    if direct.st_nlink == 2:
        prefix = f".{path.name}.tmp."
        linked_temporaries: list[Path] = []
        for candidate in ledger_root.iterdir():
            if not candidate.name.startswith(prefix):
                continue
            observed = candidate.lstat()
            if (
                stat.S_ISREG(observed.st_mode)
                and observed.st_dev == direct.st_dev
                and observed.st_ino == direct.st_ino
            ):
                linked_temporaries.append(candidate)
        if len(linked_temporaries) != 1:
            raise CandidateBoundaryError(
                "candidate_install_ledger_link_recovery_ambiguous", str(path)
            )
        linked = linked_temporaries[0]
        _assert_no_extended_acl(
            linked, code="candidate_install_ledger_record_extended_acl"
        )
        linked.unlink()
        _fsync_directory_v1(
            ledger_root, code="candidate_install_ledger_directory_fsync_failed"
        )
        direct = path.lstat()
        if direct.st_nlink != 1:
            raise CandidateBoundaryError(
                "candidate_install_ledger_link_recovery_failed", str(path)
            )
    raw, _resolved, observed = _read_stable_regular(
        path, authorized_root=ledger_root, maximum_bytes=16 * 1024 * 1024
    )
    if (
        observed.st_uid != required_uid
        or observed.st_nlink != 1
        or stat.S_IMODE(observed.st_mode) != 0o400
    ):
        raise CandidateBoundaryError(
            "candidate_install_ledger_record_invalid", str(path)
        )
    try:
        value = strict_json_loads(raw)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CandidateBoundaryError(
            "candidate_install_ledger_record_unreadable", str(path)
        ) from exc
    if not isinstance(value, dict):
        raise CandidateBoundaryError(
            "candidate_install_ledger_record_unreadable", str(path)
        )
    return value, raw


def _cleanup_stale_record_temporaries_v1(
    path: Path, *, ledger_root: Path, required_uid: int
) -> None:
    prefix = f".{path.name}.tmp."
    removed = False
    for candidate in tuple(ledger_root.iterdir()):
        if not candidate.name.startswith(prefix):
            continue
        observed = candidate.lstat()
        if (
            stat.S_ISLNK(observed.st_mode)
            or not stat.S_ISREG(observed.st_mode)
            or observed.st_uid != required_uid
            or observed.st_nlink != 1
            or stat.S_IMODE(observed.st_mode) != 0o400
        ):
            raise CandidateBoundaryError(
                "candidate_install_ledger_stale_temporary_invalid", str(candidate)
            )
        _assert_no_extended_acl(
            candidate, code="candidate_install_ledger_record_extended_acl"
        )
        candidate.unlink()
        removed = True
    if removed:
        _fsync_directory_v1(
            ledger_root, code="candidate_install_ledger_directory_fsync_failed"
        )


def _try_read_ledger_record_raw_v1(
    path: Path, *, ledger_root: Path, required_uid: int
) -> tuple[dict[str, Any], bytes] | None:
    try:
        path.lstat()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise CandidateBoundaryError(
            "candidate_install_ledger_record_unavailable", str(path)
        ) from exc
    return _read_ledger_record_raw_v1(
        path, ledger_root=ledger_root, required_uid=required_uid
    )


def _publish_append_only_record_v1(
    *,
    path: Path,
    record: Mapping[str, Any],
    ledger_root: Path,
    required_uid: int,
) -> bytes:
    """Publish one complete immutable record without replacing an existing one."""

    raw = _json_record_bytes_v1(record)
    existing = _try_read_ledger_record_raw_v1(
        path, ledger_root=ledger_root, required_uid=required_uid
    )
    if existing is not None:
        if existing[1] != raw:
            raise CandidateBoundaryError(
                "candidate_install_ledger_record_collision", str(path)
            )
        _cleanup_stale_record_temporaries_v1(
            path, ledger_root=ledger_root, required_uid=required_uid
        )
        _fsync_directory_v1(
            ledger_root, code="candidate_install_ledger_directory_fsync_failed"
        )
        reloaded = _read_ledger_record_raw_v1(
            path, ledger_root=ledger_root, required_uid=required_uid
        )
        if reloaded[1] != raw:
            raise CandidateBoundaryError(
                "candidate_install_ledger_post_publish_mismatch", str(path)
            )
        return reloaded[1]
    _cleanup_stale_record_temporaries_v1(
        path, ledger_root=ledger_root, required_uid=required_uid
    )
    temporary = ledger_root / f".{path.name}.tmp.{secrets.token_hex(16)}"
    try:
        _write_exclusive(temporary, raw, mode=0o400)
        try:
            os.link(temporary, path, follow_symlinks=False)
        except FileExistsError:
            observed = _read_ledger_record_raw_v1(
                path, ledger_root=ledger_root, required_uid=required_uid
            )
            if observed[1] != raw:
                raise CandidateBoundaryError(
                    "candidate_install_ledger_record_collision", str(path)
                )
        except OSError as exc:
            raise CandidateBoundaryError(
                "candidate_install_ledger_record_publish_failed", str(path)
            ) from exc
        finally:
            if temporary.exists():
                temporary.unlink()
        _fsync_directory_v1(
            ledger_root, code="candidate_install_ledger_directory_fsync_failed"
        )
        observed = _read_ledger_record_raw_v1(
            path, ledger_root=ledger_root, required_uid=required_uid
        )
        if observed[1] != raw:
            raise CandidateBoundaryError(
                "candidate_install_ledger_post_publish_mismatch", str(path)
            )
        return observed[1]
    finally:
        if temporary.exists():
            temporary.unlink()


def _validate_install_consumption_v1(
    consumption: Mapping[str, Any],
    *,
    authorization: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> None:
    _require_exact_fields(
        consumption,
        {
            "schema_version",
            "consumption_id",
            "record_kind",
            "authorization_ref",
            "bundle_ref",
            "target_candidate_path",
            "occurrence_id",
            "reserved_at",
            "installation_occurred",
            "formal_authority",
            "positive_assurance_allowed",
            "consumption_digest",
        },
        "candidate_install_consumption_invalid",
    )
    authorization_ref = consumption.get("authorization_ref")
    bundle_ref = consumption.get("bundle_ref")
    if not isinstance(authorization_ref, Mapping) or not isinstance(
        bundle_ref, Mapping
    ):
        raise CandidateBoundaryError(
            "candidate_install_consumption_invalid", "reference shape"
        )
    _require_exact_fields(
        authorization_ref,
        {
            "authorization_id",
            "authorization_digest",
            "authorized_operation",
            "record_locator",
            "artifact_digest",
        },
        "candidate_install_consumption_invalid",
    )
    _require_exact_fields(
        bundle_ref,
        {"bundle_id", "bundle_digest"},
        "candidate_install_consumption_invalid",
    )
    if (
        consumption.get("schema_version") != CONSUMPTION_SCHEMA
        or consumption.get("record_kind")
        != "candidate_install_authorization_consumption"
        or authorization_ref.get("authorization_id")
        != authorization["authorization_id"]
        or authorization_ref.get("authorization_digest")
        != authorization["authorization_digest"]
        or authorization_ref.get("authorized_operation")
        != "install_candidate_only"
        or authorization_ref.get("record_locator")
        != f"{authorization['authorization_id']}.authorization.json"
        or authorization_ref.get("artifact_digest")
        != digest_bytes(_json_record_bytes_v1(authorization))
        or bundle_ref.get("bundle_id") != manifest["bundle_id"]
        or bundle_ref.get("bundle_digest") != manifest["bundle_digest"]
        or consumption.get("target_candidate_path")
        != manifest["target"]["candidate_path"]
        or consumption.get("installation_occurred") is not False
        or consumption.get("formal_authority") != "none"
        or consumption.get("positive_assurance_allowed") is not False
    ):
        raise CandidateBoundaryError(
            "candidate_install_consumption_invalid", "binding or authority"
        )
    for field in ("consumption_id", "occurrence_id"):
        value = consumption.get(field)
        if not isinstance(value, str) or _LEDGER_COMPONENT_ID.fullmatch(value) is None:
            raise CandidateBoundaryError(
                "candidate_install_consumption_invalid", f"{field}={value!r}"
            )
    if _require_digest(
        consumption.get("consumption_digest"),
        "candidate_install_consumption_digest_invalid",
    ) != sealed_digest(consumption, "consumption_digest"):
        raise CandidateBoundaryError(
            "candidate_install_consumption_digest_mismatch",
            str(consumption.get("consumption_id")),
        )
    recorded_at = _parse_rfc3339_v1(
        authorization["recorded_at"],
        code="candidate_install_authorization_time_invalid",
    )
    reserved_at = _parse_rfc3339_v1(
        consumption.get("reserved_at"),
        code="candidate_install_consumption_time_invalid",
    )
    if recorded_at > reserved_at:
        raise CandidateBoundaryError(
            "candidate_install_consumption_chronology_invalid",
            str(consumption.get("consumption_id")),
        )


def _new_install_consumption_v1(
    authorization: Mapping[str, Any], manifest: Mapping[str, Any]
) -> dict[str, Any]:
    authorization_digest = _require_digest(
        authorization["authorization_digest"],
        "candidate_install_authorization_digest_invalid",
    )["value"]
    consumption: dict[str, Any] = {
        "schema_version": CONSUMPTION_SCHEMA,
        "consumption_id": f"consumption.install.{authorization_digest}",
        "record_kind": "candidate_install_authorization_consumption",
        "authorization_ref": {
            "authorization_id": authorization["authorization_id"],
            "authorization_digest": authorization["authorization_digest"],
            "authorized_operation": "install_candidate_only",
            "record_locator": (
                f"{authorization['authorization_id']}.authorization.json"
            ),
            "artifact_digest": digest_bytes(_json_record_bytes_v1(authorization)),
        },
        "bundle_ref": {
            "bundle_id": manifest["bundle_id"],
            "bundle_digest": manifest["bundle_digest"],
        },
        "target_candidate_path": manifest["target"]["candidate_path"],
        "occurrence_id": f"occurrence.install.{authorization_digest}",
        "reserved_at": _utc_now_v1(),
        "installation_occurred": False,
        "formal_authority": "none",
        "positive_assurance_allowed": False,
    }
    consumption["consumption_digest"] = sealed_digest(
        consumption, "consumption_digest"
    )
    _validate_install_consumption_v1(
        consumption, authorization=authorization, manifest=manifest
    )
    return consumption


def _validate_installed_entry_v1(entry: Mapping[str, Any]) -> None:
    _require_exact_fields(
        entry,
        {"path", "artifact_digest", "size", "installed_mode", "source"},
        "candidate_install_receipt_entry_invalid",
    )
    _safe_relative_path(
        str(entry.get("path")), code="candidate_install_receipt_entry_invalid"
    )
    _require_digest(
        entry.get("artifact_digest"), "candidate_install_receipt_entry_invalid"
    )
    if (
        not isinstance(entry.get("size"), int)
        or isinstance(entry.get("size"), bool)
        or int(entry["size"]) < 0
        or entry.get("installed_mode") not in {"0400", "0500"}
        or entry.get("source")
        not in {"closed_bundle_payload", "root_generated_relocation_binding"}
    ):
        raise CandidateBoundaryError(
            "candidate_install_receipt_entry_invalid", repr(dict(entry))
        )


def _payload_directory_denominator_v1(paths: Iterable[str]) -> list[str]:
    directories: set[str] = set()
    for raw in paths:
        path = _safe_relative_path(
            raw, code="candidate_install_receipt_entry_invalid"
        )
        for depth in range(1, len(path.parts)):
            directories.add(PurePosixPath(*path.parts[:depth]).as_posix())
    return sorted(directories)


def validate_install_projection_v1(
    projection: Mapping[str, Any],
    *,
    authorization: Mapping[str, Any],
    consumption: Mapping[str, Any],
    manifest: Mapping[str, Any],
    installed_candidate_path: Path,
) -> None:
    _require_exact_fields(
        projection,
        {
            "schema_version",
            "projection_id",
            "record_kind",
            "occurrence_id",
            "authorization_ref",
            "consumption_ref",
            "bundle_ref",
            "projected_candidate_path",
            "installed_denominator",
            "metadata_denominator",
            "post_freeze_verification_status",
            "post_freeze_verified_payload_digest",
            "installation_state",
            "dependency_environment_status",
            "snapshot_lock_validation_status",
            "snapshot_adoption_status",
            "active_snapshot_written",
            "active_trust_store_written",
            "u4_principal_authenticity",
            "formal_authority",
            "positive_assurance_allowed",
            "projection_digest",
        },
        "candidate_install_receipt_invalid",
    )
    authorization_ref = projection.get("authorization_ref")
    consumption_ref = projection.get("consumption_ref")
    bundle_ref = projection.get("bundle_ref")
    denominator = projection.get("installed_denominator")
    metadata = projection.get("metadata_denominator")
    if not all(
        isinstance(item, Mapping)
        for item in (
            authorization_ref,
            consumption_ref,
            bundle_ref,
            denominator,
            metadata,
        )
    ):
        raise CandidateBoundaryError(
            "candidate_install_receipt_invalid", "nested record shape"
        )
    _require_exact_fields(
        authorization_ref,
        {
            "authorization_id",
            "authorization_digest",
            "authorized_operation",
            "record_locator",
            "artifact_digest",
        },
        "candidate_install_receipt_invalid",
    )
    _require_exact_fields(
        consumption_ref,
        {"consumption_id", "consumption_digest"},
        "candidate_install_receipt_invalid",
    )
    _require_exact_fields(
        bundle_ref,
        {"bundle_id", "bundle_digest"},
        "candidate_install_receipt_invalid",
    )
    _require_exact_fields(
        denominator,
        {
            "status",
            "scope",
            "directory_count",
            "directories",
            "entry_count",
            "entries",
            "tree_digest",
        },
        "candidate_install_receipt_invalid",
    )
    _require_exact_fields(
        metadata,
        {
            "status",
            "scope",
            "entry_count",
            "manifest_entry",
            "projection_entry",
        },
        "candidate_install_receipt_invalid",
    )
    manifest_entry = metadata.get("manifest_entry")
    projection_entry = metadata.get("projection_entry")
    if not isinstance(manifest_entry, Mapping) or not isinstance(
        projection_entry, Mapping
    ):
        raise CandidateBoundaryError(
            "candidate_install_receipt_invalid", "metadata entry shape"
        )
    _require_exact_fields(
        manifest_entry,
        {"path", "role", "artifact_digest", "size", "installed_mode"},
        "candidate_install_receipt_invalid",
    )
    _require_exact_fields(
        projection_entry,
        {"path", "role", "integrity_binding", "installed_mode"},
        "candidate_install_receipt_invalid",
    )
    entries = denominator.get("entries")
    if not isinstance(entries, list) or not entries:
        raise CandidateBoundaryError(
            "candidate_install_receipt_invalid", "payload entries"
        )
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise CandidateBoundaryError(
                "candidate_install_receipt_entry_invalid", repr(entry)
            )
        _validate_installed_entry_v1(entry)
    paths = [str(item["path"]) for item in entries]
    directories = denominator.get("directories")
    if (
        not isinstance(directories, list)
        or any(not isinstance(item, str) for item in directories)
        or directories != _payload_directory_denominator_v1(paths)
    ):
        raise CandidateBoundaryError(
            "candidate_install_receipt_directory_denominator_invalid",
            repr(directories),
        )
    if paths != sorted(paths) or len(paths) != len(set(paths)):
        raise CandidateBoundaryError(
            "candidate_install_receipt_denominator_invalid", repr(paths)
        )
    if (
        projection.get("schema_version") != PROJECTION_SCHEMA
        or projection.get("record_kind") != "candidate_installation_projection"
        or projection.get("occurrence_id") != consumption["occurrence_id"]
        or authorization_ref.get("authorization_id")
        != authorization["authorization_id"]
        or authorization_ref.get("authorization_digest")
        != authorization["authorization_digest"]
        or authorization_ref.get("authorized_operation")
        != "install_candidate_only"
        or authorization_ref != consumption["authorization_ref"]
        or consumption_ref.get("consumption_id") != consumption["consumption_id"]
        or consumption_ref.get("consumption_digest")
        != consumption["consumption_digest"]
        or bundle_ref.get("bundle_id") != manifest["bundle_id"]
        or bundle_ref.get("bundle_digest") != manifest["bundle_digest"]
        or projection.get("projected_candidate_path")
        != str(installed_candidate_path)
        or denominator.get("status") != "closed"
        or denominator.get("scope") != "payload_tree_only"
        or denominator.get("directory_count") != len(directories)
        or denominator.get("entry_count") != len(entries)
        or denominator.get("tree_digest")
        != digest_bytes(
            canonical_json_bytes(
                {"directories": directories, "entries": entries}
            )
        )
        or metadata.get("status") != "closed_by_path_and_contract"
        or metadata.get("scope")
        != "candidate_root_metadata_excluding_payload_tree"
        or metadata.get("entry_count") != 2
        or manifest_entry.get("path") != MANIFEST_NAME
        or manifest_entry.get("role") != "source_bundle_manifest"
        or manifest_entry.get("installed_mode") != "0400"
        or projection_entry
        != {
            "path": PROJECTION_NAME,
            "role": "candidate_install_prepublication_projection",
            "integrity_binding": "self_sealed_projection_digest",
            "installed_mode": "0400",
        }
        or projection.get("post_freeze_verification_status")
        != "exact_root_names_payload_files_modes_sizes_digests_and_metadata_contracts"
        or projection.get("post_freeze_verified_payload_digest")
        != denominator.get("tree_digest")
        or projection.get("installation_state")
        != "candidate_projected_not_published"
        or projection.get("dependency_environment_status")
        != "project_distribution_excluded_source_root_separate"
        or projection.get("snapshot_lock_validation_status")
        != "pending_non_root_final_path_check"
        or projection.get("snapshot_adoption_status") != "pending"
        or projection.get("active_snapshot_written") is not False
        or projection.get("active_trust_store_written") is not False
        or projection.get("u4_principal_authenticity") != "unresolved"
        or projection.get("formal_authority") != "none"
        or projection.get("positive_assurance_allowed") is not False
    ):
        raise CandidateBoundaryError(
            "candidate_install_receipt_invalid", "binding, scope, or authority"
        )
    projection_id = projection.get("projection_id")
    if not isinstance(projection_id, str) or _LEDGER_COMPONENT_ID.fullmatch(
        projection_id
    ) is None:
        raise CandidateBoundaryError(
            "candidate_install_receipt_invalid", f"projection_id={projection_id!r}"
        )
    _require_digest(
        manifest_entry.get("artifact_digest"),
        "candidate_install_receipt_invalid",
    )
    if not isinstance(manifest_entry.get("size"), int) or isinstance(
        manifest_entry.get("size"), bool
    ):
        raise CandidateBoundaryError(
            "candidate_install_receipt_invalid", "manifest size"
        )
    if _require_digest(
        projection.get("projection_digest"),
        "candidate_install_receipt_digest_invalid",
    ) != sealed_digest(projection, "projection_digest"):
        raise CandidateBoundaryError(
            "candidate_install_receipt_digest_mismatch", str(projection_id)
        )


def validate_install_receipt_v2(
    receipt: Mapping[str, Any],
    *,
    authorization: Mapping[str, Any],
    consumption: Mapping[str, Any],
    manifest: Mapping[str, Any],
    projection: Mapping[str, Any],
    projection_raw: bytes,
    installed_candidate_path: Path,
) -> None:
    _require_exact_fields(
        receipt,
        {
            "schema_version",
            "receipt_id",
            "record_kind",
            "occurrence_id",
            "authorization_ref",
            "consumption_ref",
            "bundle_ref",
            "installed_candidate_path",
            "projection_ref",
            "publication_not_before",
            "publication_observed_at",
            "receipt_recorded_at",
            "publication_occurred",
            "installation_state",
            "snapshot_lock_validation_status",
            "snapshot_adoption_status",
            "active_snapshot_written",
            "active_trust_store_written",
            "u4_principal_authenticity",
            "formal_authority",
            "positive_assurance_allowed",
            "receipt_digest",
        },
        "candidate_install_receipt_invalid",
    )
    authorization_ref = receipt.get("authorization_ref")
    consumption_ref = receipt.get("consumption_ref")
    bundle_ref = receipt.get("bundle_ref")
    projection_ref = receipt.get("projection_ref")
    if not all(
        isinstance(item, Mapping)
        for item in (
            authorization_ref,
            consumption_ref,
            bundle_ref,
            projection_ref,
        )
    ):
        raise CandidateBoundaryError(
            "candidate_install_receipt_invalid", "reference shape"
        )
    _require_exact_fields(
        authorization_ref,
        {
            "authorization_id",
            "authorization_digest",
            "authorized_operation",
            "record_locator",
            "artifact_digest",
        },
        "candidate_install_receipt_invalid",
    )
    _require_exact_fields(
        consumption_ref,
        {"consumption_id", "consumption_digest"},
        "candidate_install_receipt_invalid",
    )
    _require_exact_fields(
        bundle_ref,
        {"bundle_id", "bundle_digest"},
        "candidate_install_receipt_invalid",
    )
    _require_exact_fields(
        projection_ref,
        {"projection_id", "locator", "artifact_digest", "projection_digest"},
        "candidate_install_receipt_invalid",
    )
    receipt_id = receipt.get("receipt_id")
    if not isinstance(receipt_id, str) or _LEDGER_COMPONENT_ID.fullmatch(
        receipt_id
    ) is None:
        raise CandidateBoundaryError(
            "candidate_install_receipt_invalid", f"receipt_id={receipt_id!r}"
        )
    if (
        receipt.get("schema_version") != RECEIPT_SCHEMA
        or receipt.get("record_kind") != "candidate_installation_occurrence"
        or receipt.get("occurrence_id") != consumption["occurrence_id"]
        or authorization_ref != consumption["authorization_ref"]
        or consumption_ref
        != {
            "consumption_id": consumption["consumption_id"],
            "consumption_digest": consumption["consumption_digest"],
        }
        or bundle_ref
        != {
            "bundle_id": manifest["bundle_id"],
            "bundle_digest": manifest["bundle_digest"],
        }
        or receipt.get("installed_candidate_path")
        != str(installed_candidate_path)
        or projection_ref
        != {
            "projection_id": projection["projection_id"],
            "locator": str(installed_candidate_path / PROJECTION_NAME),
            "artifact_digest": digest_bytes(projection_raw),
            "projection_digest": projection["projection_digest"],
        }
        or receipt.get("publication_not_before") != consumption["reserved_at"]
        or receipt.get("publication_occurred") is not True
        or receipt.get("installation_state")
        != "candidate_installed_not_activated"
        or receipt.get("snapshot_lock_validation_status")
        != "pending_non_root_final_path_check"
        or receipt.get("snapshot_adoption_status") != "pending"
        or receipt.get("active_snapshot_written") is not False
        or receipt.get("active_trust_store_written") is not False
        or receipt.get("u4_principal_authenticity") != "unresolved"
        or receipt.get("formal_authority") != "none"
        or receipt.get("positive_assurance_allowed") is not False
    ):
        raise CandidateBoundaryError(
            "candidate_install_receipt_invalid", "binding, scope, or authority"
        )
    if _require_digest(
        receipt.get("receipt_digest"), "candidate_install_receipt_digest_invalid"
    ) != sealed_digest(receipt, "receipt_digest"):
        raise CandidateBoundaryError(
            "candidate_install_receipt_digest_mismatch", str(receipt_id)
        )
    reserved_at = _parse_rfc3339_v1(
        consumption["reserved_at"], code="candidate_install_consumption_time_invalid"
    )
    publication_not_before = _parse_rfc3339_v1(
        receipt.get("publication_not_before"),
        code="candidate_install_receipt_time_invalid",
    )
    publication_observed_at = _parse_rfc3339_v1(
        receipt.get("publication_observed_at"),
        code="candidate_install_receipt_time_invalid",
    )
    receipt_recorded_at = _parse_rfc3339_v1(
        receipt.get("receipt_recorded_at"),
        code="candidate_install_receipt_time_invalid",
    )
    if not (
        reserved_at
        == publication_not_before
        <= publication_observed_at
        <= receipt_recorded_at
    ):
        raise CandidateBoundaryError(
            "candidate_install_receipt_chronology_invalid", str(receipt_id)
        )


def _copy_verified_payload(
    *,
    bundle_root: Path,
    manifest: Mapping[str, Any],
    destination: Path,
) -> list[dict[str, Any]]:
    copied: list[dict[str, Any]] = []
    for entry in manifest["payload_denominator"]["entries"]:
        relative = PurePosixPath(str(entry["path"]))
        source = bundle_root / "payload" / Path(*relative.parts)
        raw, _resolved, observed = _read_stable_regular(
            source, authorized_root=bundle_root
        )
        if (
            observed.st_nlink != 1
            or len(raw) != entry["size"]
            or digest_bytes(raw) != entry["artifact_digest"]
        ):
            raise CandidateBoundaryError(
                "candidate_payload_artifact_mismatch", relative.as_posix()
            )
        target = destination / Path(*relative.parts)
        _ensure_directory_exact(target.parent, mode=0o700)
        mode = int(str(entry["intended_mode"]), 8)
        _write_exclusive(target, raw, mode=mode)
        copied.append(
            {
                "path": relative.as_posix(),
                "artifact_digest": entry["artifact_digest"],
                "size": entry["size"],
                "installed_mode": entry["intended_mode"],
                "source": "closed_bundle_payload",
            }
        )
    return copied


def _verify_frozen_installation_v1(
    *,
    stage: Path,
    installed_entries: Sequence[Mapping[str, Any]],
    installed_directories: Sequence[str],
    manifest_raw: bytes,
    projection_raw: bytes,
    required_uid: int,
) -> None:
    payload = stage / "payload"
    try:
        root_names = {entry.name for entry in os.scandir(stage)}
    except OSError as exc:
        raise CandidateBoundaryError(
            "candidate_frozen_root_unreadable", str(stage)
        ) from exc
    expected_root_names = {
        "payload",
        MANIFEST_NAME,
        PROJECTION_NAME,
    }
    if root_names != expected_root_names:
        raise CandidateBoundaryError(
            "candidate_frozen_root_denominator_mismatch",
            f"missing={sorted(expected_root_names - root_names)!r}; "
            f"extra={sorted(root_names - expected_root_names)!r}",
        )
    expected = {str(entry["path"]): dict(entry) for entry in installed_entries}
    if len(expected) != len(installed_entries):
        raise CandidateBoundaryError(
            "candidate_installed_denominator_duplicate", repr(sorted(expected))
        )
    observed_paths: set[str] = set()
    observed_directories: set[str] = set()
    for raw_directory, directory_names, file_names in os.walk(
        payload, topdown=True, followlinks=False
    ):
        base = Path(raw_directory)
        _assert_no_extended_acl(
            base, code="candidate_frozen_directory_extended_acl"
        )
        for name in directory_names:
            directory = base / name
            observed_directories.add(directory.relative_to(payload).as_posix())
            observed = directory.lstat()
            if (
                stat.S_ISLNK(observed.st_mode)
                or not stat.S_ISDIR(observed.st_mode)
                or observed.st_uid != required_uid
                or stat.S_IMODE(observed.st_mode) != 0o500
            ):
                raise CandidateBoundaryError(
                    "candidate_frozen_directory_mismatch", str(directory)
                )
            _assert_no_extended_acl(
                directory, code="candidate_frozen_directory_extended_acl"
            )
        for name in file_names:
            path = base / name
            relative = path.relative_to(payload).as_posix()
            observed_paths.add(relative)
            expected_entry = expected.get(relative)
            if expected_entry is None:
                raise CandidateBoundaryError(
                    "candidate_frozen_denominator_extra", relative
                )
            raw, _resolved, observed = _read_stable_regular(
                path, authorized_root=stage
            )
            expected_mode = int(str(expected_entry["installed_mode"]), 8)
            if (
                observed.st_uid != required_uid
                or observed.st_nlink != 1
                or stat.S_IMODE(observed.st_mode) != expected_mode
                or len(raw) != expected_entry["size"]
                or digest_bytes(raw) != expected_entry["artifact_digest"]
            ):
                raise CandidateBoundaryError(
                    "candidate_frozen_artifact_mismatch", relative
                )
    missing = set(expected) - observed_paths
    if missing:
        raise CandidateBoundaryError(
            "candidate_frozen_denominator_missing", repr(sorted(missing))
        )
    expected_directories = set(installed_directories)
    if observed_directories != expected_directories:
        raise CandidateBoundaryError(
            "candidate_frozen_directory_denominator_mismatch",
            f"missing={sorted(expected_directories - observed_directories)!r}; "
            f"extra={sorted(observed_directories - expected_directories)!r}",
        )
    for path, expected_raw in (
        (stage / MANIFEST_NAME, manifest_raw),
        (stage / PROJECTION_NAME, projection_raw),
    ):
        raw, _resolved, observed = _read_stable_regular(
            path, authorized_root=stage
        )
        if (
            raw != expected_raw
            or observed.st_uid != required_uid
            or observed.st_nlink != 1
            or stat.S_IMODE(observed.st_mode) != 0o400
        ):
            raise CandidateBoundaryError(
                "candidate_frozen_metadata_mismatch", str(path)
            )
    stage_observed = stage.lstat()
    payload_observed = payload.lstat()
    if (
        stage_observed.st_uid != required_uid
        or payload_observed.st_uid != required_uid
        or stat.S_IMODE(stage_observed.st_mode) != 0o500
        or stat.S_IMODE(payload_observed.st_mode) != 0o500
    ):
        raise CandidateBoundaryError(
            "candidate_frozen_root_mismatch", str(stage)
        )
    _assert_no_extended_acl(stage, code="candidate_frozen_directory_extended_acl")
    _assert_no_extended_acl(payload, code="candidate_frozen_directory_extended_acl")


def _build_install_projection_v1(
    *,
    authorization: Mapping[str, Any],
    consumption: Mapping[str, Any],
    manifest: Mapping[str, Any],
    final: Path,
    installed_entries: Sequence[Mapping[str, Any]],
    manifest_raw: bytes,
) -> dict[str, Any]:
    entries = [dict(item) for item in installed_entries]
    directories = _payload_directory_denominator_v1(
        str(item["path"]) for item in entries
    )
    observed_tree_digest = digest_bytes(
        canonical_json_bytes({"directories": directories, "entries": entries})
    )
    authorization_digest = _require_digest(
        authorization["authorization_digest"],
        "candidate_install_authorization_digest_invalid",
    )["value"]
    projection: dict[str, Any] = {
        "schema_version": PROJECTION_SCHEMA,
        "projection_id": f"projection.install.{authorization_digest}",
        "record_kind": "candidate_installation_projection",
        "occurrence_id": consumption["occurrence_id"],
        "authorization_ref": {
            **dict(consumption["authorization_ref"]),
        },
        "consumption_ref": {
            "consumption_id": consumption["consumption_id"],
            "consumption_digest": consumption["consumption_digest"],
        },
        "bundle_ref": {
            "bundle_id": manifest["bundle_id"],
            "bundle_digest": manifest["bundle_digest"],
        },
        "projected_candidate_path": str(final),
        "installed_denominator": {
            "status": "closed",
            "scope": "payload_tree_only",
            "directory_count": len(directories),
            "directories": directories,
            "entry_count": len(entries),
            "entries": entries,
            "tree_digest": observed_tree_digest,
        },
        "metadata_denominator": {
            "status": "closed_by_path_and_contract",
            "scope": "candidate_root_metadata_excluding_payload_tree",
            "entry_count": 2,
            "manifest_entry": {
                "path": MANIFEST_NAME,
                "role": "source_bundle_manifest",
                "artifact_digest": digest_bytes(manifest_raw),
                "size": len(manifest_raw),
                "installed_mode": "0400",
            },
            "projection_entry": {
                "path": PROJECTION_NAME,
                "role": "candidate_install_prepublication_projection",
                "integrity_binding": "self_sealed_projection_digest",
                "installed_mode": "0400",
            },
        },
        "post_freeze_verification_status": (
            "exact_root_names_payload_files_modes_sizes_digests_and_metadata_contracts"
        ),
        "post_freeze_verified_payload_digest": observed_tree_digest,
        "installation_state": "candidate_projected_not_published",
        "dependency_environment_status": (
            "project_distribution_excluded_source_root_separate"
        ),
        "snapshot_lock_validation_status": "pending_non_root_final_path_check",
        "snapshot_adoption_status": "pending",
        "active_snapshot_written": False,
        "active_trust_store_written": False,
        "u4_principal_authenticity": "unresolved",
        "formal_authority": "none",
        "positive_assurance_allowed": False,
    }
    projection["projection_digest"] = sealed_digest(
        projection, "projection_digest"
    )
    validate_install_projection_v1(
        projection,
        authorization=authorization,
        consumption=consumption,
        manifest=manifest,
        installed_candidate_path=final,
    )
    return projection


def _build_install_receipt_v2(
    *,
    authorization: Mapping[str, Any],
    consumption: Mapping[str, Any],
    manifest: Mapping[str, Any],
    final: Path,
    projection: Mapping[str, Any],
    projection_raw: bytes,
    publication_observed_at: str,
) -> dict[str, Any]:
    receipt_recorded_at = _utc_now_v1()
    authorization_digest = _require_digest(
        authorization["authorization_digest"],
        "candidate_install_authorization_digest_invalid",
    )["value"]
    receipt: dict[str, Any] = {
        "schema_version": RECEIPT_SCHEMA,
        "receipt_id": f"receipt.install.{authorization_digest}",
        "record_kind": "candidate_installation_occurrence",
        "occurrence_id": consumption["occurrence_id"],
        "authorization_ref": dict(consumption["authorization_ref"]),
        "consumption_ref": {
            "consumption_id": consumption["consumption_id"],
            "consumption_digest": consumption["consumption_digest"],
        },
        "bundle_ref": {
            "bundle_id": manifest["bundle_id"],
            "bundle_digest": manifest["bundle_digest"],
        },
        "installed_candidate_path": str(final),
        "projection_ref": {
            "projection_id": projection["projection_id"],
            "locator": str(final / PROJECTION_NAME),
            "artifact_digest": digest_bytes(projection_raw),
            "projection_digest": projection["projection_digest"],
        },
        "publication_not_before": consumption["reserved_at"],
        "publication_observed_at": publication_observed_at,
        "receipt_recorded_at": receipt_recorded_at,
        "publication_occurred": True,
        "installation_state": "candidate_installed_not_activated",
        "snapshot_lock_validation_status": "pending_non_root_final_path_check",
        "snapshot_adoption_status": "pending",
        "active_snapshot_written": False,
        "active_trust_store_written": False,
        "u4_principal_authenticity": "unresolved",
        "formal_authority": "none",
        "positive_assurance_allowed": False,
    }
    receipt["receipt_digest"] = sealed_digest(receipt, "receipt_digest")
    validate_install_receipt_v2(
        receipt,
        authorization=authorization,
        consumption=consumption,
        manifest=manifest,
        projection=projection,
        projection_raw=projection_raw,
        installed_candidate_path=final,
    )
    return receipt


def _load_installed_projection_v1(
    *,
    final: Path,
    authorization: Mapping[str, Any],
    consumption: Mapping[str, Any],
    manifest: Mapping[str, Any],
    required_uid: int,
) -> tuple[dict[str, Any], bytes]:
    try:
        observed_final = final.lstat()
    except OSError as exc:
        raise CandidateBoundaryError(
            "candidate_install_final_unavailable", str(final)
        ) from exc
    if (
        stat.S_ISLNK(observed_final.st_mode)
        or not stat.S_ISDIR(observed_final.st_mode)
        or observed_final.st_uid != required_uid
        or stat.S_IMODE(observed_final.st_mode) != 0o500
    ):
        raise CandidateBoundaryError("candidate_install_final_invalid", str(final))
    _assert_no_extended_acl(final, code="candidate_install_final_extended_acl")
    manifest_raw = (
        json.dumps(
            manifest,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        ).encode("utf-8")
        + b"\n"
    )
    projection_path = final / PROJECTION_NAME
    projection_raw, _resolved, observed_projection = _read_stable_regular(
        projection_path, authorized_root=final, maximum_bytes=16 * 1024 * 1024
    )
    if (
        observed_projection.st_uid != required_uid
        or observed_projection.st_nlink != 1
        or stat.S_IMODE(observed_projection.st_mode) != 0o400
    ):
        raise CandidateBoundaryError(
            "candidate_install_projection_file_invalid", str(projection_path)
        )
    try:
        projection = strict_json_loads(projection_raw)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CandidateBoundaryError(
            "candidate_install_projection_unreadable", str(projection_path)
        ) from exc
    if not isinstance(projection, dict):
        raise CandidateBoundaryError(
            "candidate_install_projection_unreadable", str(projection_path)
        )
    validate_install_projection_v1(
        projection,
        authorization=authorization,
        consumption=consumption,
        manifest=manifest,
        installed_candidate_path=final,
    )
    manifest_entry = projection["metadata_denominator"]["manifest_entry"]
    if (
        manifest_entry["artifact_digest"] != digest_bytes(manifest_raw)
        or manifest_entry["size"] != len(manifest_raw)
    ):
        raise CandidateBoundaryError(
            "candidate_install_manifest_binding_mismatch", str(final)
        )
    _verify_frozen_installation_v1(
        stage=final,
        installed_entries=projection["installed_denominator"]["entries"],
        installed_directories=projection["installed_denominator"]["directories"],
        manifest_raw=manifest_raw,
        projection_raw=projection_raw,
        required_uid=required_uid,
    )
    return projection, projection_raw


def _rename_directory_no_replace_v1(source: Path, target: Path) -> bool:
    """Atomically publish a directory, returning false when target already exists."""

    libc = ctypes.CDLL(None, use_errno=True)
    if sys.platform == "darwin":
        rename = getattr(libc, "renameatx_np", None)
        at_fdcwd = -2
        no_replace = 0x00000004
    elif sys.platform.startswith("linux"):
        rename = getattr(libc, "renameat2", None)
        at_fdcwd = -100
        no_replace = 1
    else:
        rename = None
        at_fdcwd = 0
        no_replace = 0
    if rename is None:
        raise CandidateBoundaryError(
            "candidate_install_atomic_no_replace_unsupported", sys.platform
        )
    rename.argtypes = [
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    ]
    rename.restype = ctypes.c_int
    ctypes.set_errno(0)
    result = rename(
        at_fdcwd,
        os.fsencode(source),
        at_fdcwd,
        os.fsencode(target),
        no_replace,
    )
    if result == 0:
        return True
    observed_errno = ctypes.get_errno()
    if observed_errno in {errno.EEXIST, errno.ENOTEMPTY}:
        return False
    raise CandidateBoundaryError(
        "candidate_install_atomic_publish_failed",
        f"{source} -> {target}: errno={observed_errno}",
    )


def _reconcile_published_candidate_v1(
    *,
    final: Path,
    candidate_root: Path,
    receipt_path: Path,
    ledger_root: Path,
    authorization: Mapping[str, Any],
    consumption: Mapping[str, Any],
    manifest: Mapping[str, Any],
    required_uid: int,
) -> dict[str, Any]:
    """Finish only the durable evidence for one already-published exact tree."""

    projection, projection_raw = _load_installed_projection_v1(
        final=final,
        authorization=authorization,
        consumption=consumption,
        manifest=manifest,
        required_uid=required_uid,
    )
    _fsync_directory_v1(
        candidate_root, code="candidate_install_parent_fsync_failed"
    )
    reloaded, reloaded_raw = _load_installed_projection_v1(
        final=final,
        authorization=authorization,
        consumption=consumption,
        manifest=manifest,
        required_uid=required_uid,
    )
    if reloaded != projection or reloaded_raw != projection_raw:
        raise CandidateBoundaryError(
            "candidate_install_reconcile_recheck_mismatch", str(final)
        )
    external = _try_read_ledger_record_raw_v1(
        receipt_path, ledger_root=ledger_root, required_uid=required_uid
    )
    if external is not None:
        validate_install_receipt_v2(
            external[0],
            authorization=authorization,
            consumption=consumption,
            manifest=manifest,
            projection=projection,
            projection_raw=projection_raw,
            installed_candidate_path=final,
        )
        return external[0]
    publication_observed_at = _utc_now_v1()
    receipt = _build_install_receipt_v2(
        authorization=authorization,
        consumption=consumption,
        manifest=manifest,
        final=final,
        projection=projection,
        projection_raw=projection_raw,
        publication_observed_at=publication_observed_at,
    )
    receipt_raw = _json_record_bytes_v1(receipt)
    published_raw = _publish_append_only_record_v1(
        path=receipt_path,
        record=receipt,
        ledger_root=ledger_root,
        required_uid=required_uid,
    )
    if published_raw != receipt_raw:
        raise CandidateBoundaryError(
            "candidate_install_receipt_ledger_mismatch", str(receipt_path)
        )
    return receipt


def _assert_no_competing_candidate_consumption_v1(
    *,
    ledger_root: Path,
    current_consumption_path: Path,
    authorization: Mapping[str, Any],
    manifest: Mapping[str, Any],
    required_uid: int,
) -> None:
    """Keep one target from accumulating incompatible consumed authorizations."""

    for path in sorted(ledger_root.glob("*.consumption.json")):
        if path == current_consumption_path:
            continue
        candidate, _raw = _read_ledger_record_raw_v1(
            path, ledger_root=ledger_root, required_uid=required_uid
        )
        bundle_ref = candidate.get("bundle_ref")
        if not isinstance(bundle_ref, Mapping) or (
            bundle_ref.get("bundle_id") != manifest["bundle_id"]
            or candidate.get("target_candidate_path")
            != manifest["target"]["candidate_path"]
        ):
            continue
        authorization_ref = candidate.get("authorization_ref")
        if not isinstance(authorization_ref, Mapping):
            raise CandidateBoundaryError(
                "candidate_install_competing_consumption_invalid", str(path)
            )
        other_authorization_id = authorization_ref.get("authorization_id")
        if other_authorization_id == authorization["authorization_id"]:
            raise CandidateBoundaryError(
                "candidate_install_consumption_locator_collision", str(path)
            )
        locator = authorization_ref.get("record_locator")
        if (
            not isinstance(locator, str)
            or locator != f"{other_authorization_id}.authorization.json"
            or _safe_relative_path(
                locator, code="candidate_install_competing_consumption_invalid"
            ).parent
            != PurePosixPath(".")
        ):
            raise CandidateBoundaryError(
                "candidate_install_competing_consumption_invalid", str(path)
            )
        other_authorization_record = _read_ledger_record_raw_v1(
            ledger_root / locator,
            ledger_root=ledger_root,
            required_uid=required_uid,
        )
        other_authorization = other_authorization_record[0]
        validate_install_authorization_v1(other_authorization, manifest)
        _validate_install_consumption_v1(
            candidate,
            authorization=other_authorization,
            manifest=manifest,
        )
        other_receipt = ledger_root / f"{other_authorization_id}.receipt.json"
        if other_receipt.exists() or other_receipt.is_symlink():
            raise CandidateBoundaryError(
                "candidate_install_already_completed_by_other_occurrence",
                str(other_receipt),
            )
        raise CandidateBoundaryError(
            "candidate_install_competing_consumption_unresolved", str(path)
        )


def _install_candidate_bundle_under_lock_v1(
    *,
    bundle_root: Path,
    authorization: Mapping[str, Any],
    candidate_root: Path = CANDIDATE_ROOT,
    install_ledger_root: Path | None = None,
    required_uid: int = 0,
    enforce_fixed_target: bool = True,
) -> dict[str, Any]:
    """Consume one authorization and publish one candidate occurrence only."""

    manifest, manifest_raw = _load_bundle_manifest_raw_v1(bundle_root)
    validate_bundle_files_v1(bundle_root, manifest)
    validate_install_authorization_v1(
        authorization,
        manifest,
        bundle_root=bundle_root,
        manifest_raw=manifest_raw,
    )
    if enforce_fixed_target:
        _validate_owned_directory_chain(candidate_root, required_uid=required_uid)
    else:
        _validate_owned_directory(candidate_root, required_uid=required_uid)
    if enforce_fixed_target and candidate_root != CANDIDATE_ROOT:
        raise CandidateBoundaryError(
            "candidate_install_target_override", str(candidate_root)
        )
    final = candidate_root / str(manifest["bundle_id"])
    if enforce_fixed_target and str(final) != manifest["target"]["candidate_path"]:
        raise CandidateBoundaryError("candidate_install_target_mismatch", str(final))
    ledger_root = (
        install_ledger_root
        if install_ledger_root is not None
        else (
            CANDIDATE_INSTALL_LEDGER_ROOT
            if enforce_fixed_target
            else candidate_root.parent / "activations" / "candidate-installs"
        )
    )
    _prepare_candidate_install_ledger_v1(
        candidate_root=candidate_root,
        ledger_root=ledger_root,
        required_uid=required_uid,
        enforce_fixed_target=enforce_fixed_target,
    )
    authorization_path, consumption_path, receipt_path = _ledger_record_paths_v1(
        authorization, ledger_root=ledger_root
    )
    _assert_no_competing_candidate_consumption_v1(
        ledger_root=ledger_root,
        current_consumption_path=consumption_path,
        authorization=authorization,
        manifest=manifest,
        required_uid=required_uid,
    )
    archived_authorization = _try_read_ledger_record_raw_v1(
        authorization_path, ledger_root=ledger_root, required_uid=required_uid
    )
    preexisting_consumption = _try_read_ledger_record_raw_v1(
        consumption_path, ledger_root=ledger_root, required_uid=required_uid
    )
    preexisting_receipt = _try_read_ledger_record_raw_v1(
        receipt_path, ledger_root=ledger_root, required_uid=required_uid
    )
    if archived_authorization is None and (
        preexisting_consumption is not None or preexisting_receipt is not None
    ):
        raise CandidateBoundaryError(
            "candidate_install_authorization_archive_missing",
            str(authorization_path),
        )
    authorization_raw = _publish_append_only_record_v1(
        path=authorization_path,
        record=authorization,
        ledger_root=ledger_root,
        required_uid=required_uid,
    )
    if authorization_raw != _json_record_bytes_v1(authorization):
        raise CandidateBoundaryError(
            "candidate_install_authorization_archive_mismatch",
            str(authorization_path),
        )
    consumption_record = preexisting_consumption
    consumption: dict[str, Any] | None = None
    if consumption_record is not None:
        consumption = consumption_record[0]
        _validate_install_consumption_v1(
            consumption, authorization=authorization, manifest=manifest
        )
    external_receipt = preexisting_receipt
    if external_receipt is not None and consumption is None:
        raise CandidateBoundaryError(
            "candidate_install_receipt_without_consumption", str(receipt_path)
        )
    if final.exists() or final.is_symlink():
        if consumption is None:
            raise CandidateBoundaryError(
                "candidate_install_existing_target_unbound", str(final)
            )
        return _reconcile_published_candidate_v1(
            final=final,
            candidate_root=candidate_root,
            receipt_path=receipt_path,
            ledger_root=ledger_root,
            authorization=authorization,
            consumption=consumption,
            manifest=manifest,
            required_uid=required_uid,
        )
    if external_receipt is not None:
        assert consumption is not None
        raise CandidateBoundaryError(
            "candidate_install_completed_target_missing", str(final)
        )
    if consumption is None:
        proposed_consumption = _new_install_consumption_v1(authorization, manifest)
        try:
            _publish_append_only_record_v1(
                path=consumption_path,
                record=proposed_consumption,
                ledger_root=ledger_root,
                required_uid=required_uid,
            )
            consumption = proposed_consumption
        except CandidateBoundaryError as exc:
            if exc.code != "candidate_install_ledger_record_collision":
                raise
            raced = _read_ledger_record_raw_v1(
                consumption_path,
                ledger_root=ledger_root,
                required_uid=required_uid,
            )
            consumption = raced[0]
        _validate_install_consumption_v1(
            consumption, authorization=authorization, manifest=manifest
        )
    authorization_digest = _require_digest(
        authorization["authorization_digest"],
        "candidate_install_authorization_digest_invalid",
    )["value"]
    stage = candidate_root / (
        f".installing.{authorization_digest}.{secrets.token_hex(16)}"
    )
    payload = stage / "payload"
    try:
        _ensure_directory_exact(stage, mode=0o700)
        _ensure_directory_exact(payload, mode=0o700)
        installed_entries = _copy_verified_payload(
            bundle_root=bundle_root,
            manifest=manifest,
            destination=payload,
        )
        generated = manifest["root_generated_entries"][0]
        generated_relative = PurePosixPath(str(generated["path"]))
        generated_path = payload / Path(*generated_relative.parts)
        _ensure_directory_exact(generated_path.parent, mode=0o700)
        generated_raw = (
            str(generated["content_template"])
            .format(candidate_payload=str(final / "payload"))
            .encode("utf-8")
        )
        _write_exclusive(generated_path, generated_raw, mode=0o400)
        installed_entries.append(
            {
                "path": generated_relative.as_posix(),
                "artifact_digest": digest_bytes(generated_raw),
                "size": len(generated_raw),
                "installed_mode": "0400",
                "source": "root_generated_relocation_binding",
            }
        )
        installed_entries.sort(key=lambda item: str(item["path"]))
        manifest_raw = (
            json.dumps(
                manifest,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
                allow_nan=False,
            ).encode("utf-8")
            + b"\n"
        )
        _write_exclusive(stage / MANIFEST_NAME, manifest_raw, mode=0o400)
        projection = _build_install_projection_v1(
            authorization=authorization,
            consumption=consumption,
            manifest=manifest,
            final=final,
            installed_entries=installed_entries,
            manifest_raw=manifest_raw,
        )
        projection_raw = (
            json.dumps(
                projection,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
                allow_nan=False,
            ).encode("utf-8")
            + b"\n"
        )
        _write_exclusive(
            stage / PROJECTION_NAME,
            projection_raw,
            mode=0o400,
        )
        _freeze_tree(stage, owner_uid=required_uid)
        _fsync_frozen_tree_bottom_up_v1(stage)
        _verify_frozen_installation_v1(
            stage=stage,
            installed_entries=installed_entries,
            installed_directories=projection["installed_denominator"]["directories"],
            manifest_raw=manifest_raw,
            projection_raw=projection_raw,
            required_uid=required_uid,
        )
        published = _rename_directory_no_replace_v1(stage, final)
        if not published:
            _remove_private_tree_v1(stage)
        return _reconcile_published_candidate_v1(
            final=final,
            candidate_root=candidate_root,
            receipt_path=receipt_path,
            ledger_root=ledger_root,
            authorization=authorization,
            consumption=consumption,
            manifest=manifest,
            required_uid=required_uid,
        )
    except BaseException:
        _remove_private_tree_v1(stage)
        raise


def _install_candidate_bundle(
    *,
    bundle_root: Path,
    authorization: Mapping[str, Any],
    candidate_root: Path = CANDIDATE_ROOT,
    install_ledger_root: Path | None = None,
    required_uid: int = 0,
    enforce_fixed_target: bool = True,
) -> dict[str, Any]:
    """Serialize one authorization's install/recovery transaction."""

    # Production reaches this function only after the fixed ID-only entrypoint
    # has resolved the root-held authorization, whose source locator is already
    # canonical.  Test fixtures live below macOS' /var -> /private/var alias;
    # normalize that injected, non-production locator before exercising the
    # same transaction rather than weakening the production path check.
    if not enforce_fixed_target:
        try:
            bundle_root = bundle_root.resolve(strict=True)
        except OSError as exc:
            raise CandidateBoundaryError(
                "candidate_source_bundle_path_unavailable", str(bundle_root)
            ) from exc
    manifest, manifest_raw = _load_bundle_manifest_raw_v1(bundle_root)
    validate_bundle_files_v1(bundle_root, manifest)
    validate_install_authorization_v1(
        authorization,
        manifest,
        bundle_root=bundle_root,
        manifest_raw=manifest_raw,
    )
    if enforce_fixed_target:
        _validate_owned_directory_chain(candidate_root, required_uid=required_uid)
    else:
        _validate_owned_directory(candidate_root, required_uid=required_uid)
    ledger_root = (
        install_ledger_root
        if install_ledger_root is not None
        else (
            CANDIDATE_INSTALL_LEDGER_ROOT
            if enforce_fixed_target
            else candidate_root.parent / "activations" / "candidate-installs"
        )
    )
    _prepare_candidate_install_ledger_v1(
        candidate_root=candidate_root,
        ledger_root=ledger_root,
        required_uid=required_uid,
        enforce_fixed_target=enforce_fixed_target,
    )
    with _candidate_install_transaction_lock_v1(
        manifest=manifest,
        ledger_root=ledger_root,
        required_uid=required_uid,
    ):
        _cleanup_stale_install_stages_v1(
            candidate_root=candidate_root,
            authorization=authorization,
            required_uid=required_uid,
        )
        return _install_candidate_bundle_under_lock_v1(
            bundle_root=bundle_root,
            authorization=authorization,
            candidate_root=candidate_root,
            install_ledger_root=ledger_root,
            required_uid=required_uid,
            enforce_fixed_target=enforce_fixed_target,
        )


def _validate_bootstrap_module_origin_v1(name: str, module: object) -> None:
    origin = getattr(module, "__file__", None)
    if origin:
        candidate = Path(str(origin))
        if candidate.suffix in {".pyc", ".pyo"} and not candidate.exists():
            candidate = Path(str(candidate)[:-1])
        if (
            not candidate.is_absolute()
            or not candidate.exists()
            or not candidate.is_file()
        ):
            raise CandidateBoundaryError(
                "candidate_bootstrap_module_origin_untrusted",
                f"{name}={candidate}: origin is not one existing file",
            )
        _validate_owned_directory_chain(candidate.parent, required_uid=0)
        observed_module = candidate.lstat()
        if (
            stat.S_ISLNK(observed_module.st_mode)
            or not stat.S_ISREG(observed_module.st_mode)
            or observed_module.st_uid != 0
            or observed_module.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
        ):
            raise CandidateBoundaryError(
                "candidate_bootstrap_module_origin_untrusted",
                f"{name}={candidate}",
            )
        return

    specification = getattr(module, "__spec__", None)
    specification_origin = getattr(specification, "origin", None)
    if specification_origin in {"built-in", "frozen"}:
        return
    namespace_locations = getattr(
        specification, "submodule_search_locations", None
    )
    if (
        specification_origin not in {None, "namespace"}
        or namespace_locations is None
    ):
        raise CandidateBoundaryError(
            "candidate_bootstrap_module_origin_untrusted",
            f"{name}={specification_origin!r}: origin is unverified",
        )
    locations = tuple(namespace_locations)
    if not locations:
        raise CandidateBoundaryError(
            "candidate_bootstrap_module_origin_untrusted",
            f"{name}: namespace has no locations",
        )
    for location in locations:
        candidate = Path(str(location))
        if (
            not candidate.is_absolute()
            or not candidate.exists()
            or not candidate.is_dir()
        ):
            raise CandidateBoundaryError(
                "candidate_bootstrap_module_origin_untrusted",
                f"{name}={candidate}: namespace location is unavailable",
            )
        _validate_owned_directory_chain(candidate, required_uid=0)


def _assert_root_bootstrap_installer(manifest: Mapping[str, Any]) -> None:
    if os.geteuid() != 0:
        raise CandidateBoundaryError(
            "candidate_install_requires_root", str(os.geteuid())
        )
    if not (
        sys.flags.isolated
        and sys.flags.no_site
        and sys.flags.dont_write_bytecode
        and getattr(sys.flags, "safe_path", True)
    ):
        raise CandidateBoundaryError(
            "candidate_bootstrap_flags_untrusted", repr(sys.flags)
        )
    required_environment = {
        "PATH": "",
        "LC_ALL": "C",
        "PYTHONDONTWRITEBYTECODE": "1",
        "SEMANTIC_GUARD_U10_INSTALL_LAUNCH": (
            "fixed-root-installer-wrapper-v2"
        ),
    }
    _validate_os_injected_environment_v1(
        os.environ,
        expected=required_environment,
        code="candidate_bootstrap_environment_untrusted",
    )
    os.environ.pop("__CF_USER_TEXT_ENCODING", None)
    if any(
        (
            name.startswith("DYLD_")
            or name.startswith("LD_")
            or name in {"PYTHONPATH", "PYTHONHOME"}
        )
        for name in os.environ
    ):
        raise CandidateBoundaryError(
            "candidate_bootstrap_environment_untrusted", repr(dict(os.environ))
        )
    raw_path = Path(__file__).absolute()
    if raw_path != BOOTSTRAP_INSTALLER_PATH or raw_path.is_symlink():
        raise CandidateBoundaryError(
            "candidate_bootstrap_path_untrusted", str(raw_path)
        )
    _validate_owned_directory_chain(raw_path.parent, required_uid=0)
    observed = raw_path.lstat()
    if (
        not stat.S_ISREG(observed.st_mode)
        or observed.st_uid != 0
        or observed.st_nlink != 1
        or observed.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
    ):
        raise CandidateBoundaryError(
            "candidate_bootstrap_file_untrusted", str(raw_path)
        )
    interpreter = Path(os.path.realpath(sys.executable))
    if (
        not interpreter.is_absolute()
        or interpreter != Path(os.path.normpath(str(interpreter)))
        or interpreter.is_symlink()
    ):
        raise CandidateBoundaryError(
            "candidate_bootstrap_interpreter_untrusted", str(interpreter)
        )
    raw, _resolved, _stat = _read_stable_regular(raw_path)
    if digest_bytes(raw) != manifest["installer_ref"]["artifact_digest"]:
        raise CandidateBoundaryError(
            "candidate_bootstrap_digest_mismatch", str(raw_path)
        )
    entrypoint = ROOT_INSTALLER_ENTRYPOINT_PATH
    _validate_owned_directory_chain(entrypoint.parent, required_uid=0)
    entrypoint_raw, _entrypoint_resolved, entrypoint_observed = (
        _read_stable_regular(entrypoint)
    )
    if (
        entrypoint_observed.st_uid != 0
        or entrypoint_observed.st_nlink != 1
        or entrypoint_observed.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
        or digest_bytes(entrypoint_raw)
        != manifest["installer_ref"]["entrypoint_artifact_digest"]
    ):
        raise CandidateBoundaryError(
            "candidate_bootstrap_entrypoint_untrusted", str(entrypoint)
        )
    for path, resolved_field, digest_field in (
        (
            ROOT_BOOTSTRAP_SHELL,
            "shell_resolved_locator",
            "shell_artifact_digest",
        ),
        (
            ROOT_ENVIRONMENT_CLEANER,
            "environment_cleaner_resolved_locator",
            "environment_cleaner_artifact_digest",
        ),
    ):
        _validate_owned_directory_chain(path.parent, required_uid=0)
        host_raw, host_resolved, host_observed = _read_stable_regular(path)
        if (
            host_observed.st_uid != 0
            or host_observed.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
            or str(host_resolved) != manifest["installer_ref"][resolved_field]
            or digest_bytes(host_raw) != manifest["installer_ref"][digest_field]
        ):
            raise CandidateBoundaryError(
                "candidate_bootstrap_host_launcher_untrusted", str(path)
            )
    discovery_raw, discovery_resolved, discovery_stat = _read_stable_regular(
        ROOT_BOOTSTRAP_DISCOVERY_LAUNCHER
    )
    effective_path_raw, _effective_path_resolved, effective_path_stat = (
        _read_stable_regular(ROOT_EFFECTIVE_PYTHON_PATH_FILE)
    )
    if (
        effective_path_stat.st_uid != 0
        or effective_path_stat.st_nlink != 1
        or effective_path_stat.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
        or digest_bytes(effective_path_raw)
        != manifest["installer_ref"][
            "effective_interpreter_path_artifact_digest"
        ]
        or not effective_path_raw.endswith(b"\n")
        or effective_path_raw.count(b"\n") != 1
        or b"\x00" in effective_path_raw
    ):
        raise CandidateBoundaryError(
            "candidate_bootstrap_interpreter_path_untrusted",
            str(ROOT_EFFECTIVE_PYTHON_PATH_FILE),
        )
    try:
        recorded_interpreter = Path(effective_path_raw[:-1].decode("utf-8"))
    except UnicodeError as exc:
        raise CandidateBoundaryError(
            "candidate_bootstrap_interpreter_path_untrusted",
            str(ROOT_EFFECTIVE_PYTHON_PATH_FILE),
        ) from exc
    interpreter_raw, interpreter_resolved, interpreter_stat = _read_stable_regular(
        recorded_interpreter
    )
    _validate_owned_directory_chain(
        ROOT_BOOTSTRAP_DISCOVERY_LAUNCHER.parent,
        required_uid=0,
    )
    _validate_owned_directory_chain(
        interpreter_resolved.parent,
        required_uid=0,
    )
    if (
        str(discovery_resolved)
        != manifest["installer_ref"]["discovery_launcher_resolved_locator"]
        or discovery_stat.st_uid != 0
        or discovery_stat.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
        or digest_bytes(discovery_raw)
        != manifest["installer_ref"]["discovery_launcher_artifact_digest"]
        or interpreter != interpreter_resolved
        or str(interpreter_resolved)
        != manifest["installer_ref"]["effective_interpreter_locator"]
        or interpreter_stat.st_uid != 0
        or interpreter_stat.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
        or digest_bytes(interpreter_raw)
        != manifest["installer_ref"]["effective_interpreter_artifact_digest"]
    ):
        raise CandidateBoundaryError(
            "candidate_bootstrap_interpreter_untrusted", str(interpreter)
        )
    for value in sys.path:
        if not value:
            continue
        candidate = Path(value)
        if not candidate.is_absolute():
            raise CandidateBoundaryError(
                "candidate_bootstrap_sys_path_untrusted", value
            )
        if candidate.exists():
            _validate_owned_directory_chain(
                candidate if candidate.is_dir() else candidate.parent,
                required_uid=0,
            )
    for name, module in tuple(sys.modules.items()):
        _validate_bootstrap_module_origin_v1(name, module)


def _read_root_authorization_by_bundle_id_v1(
    bundle_id: str,
) -> dict[str, Any]:
    if _LEDGER_COMPONENT_ID.fullmatch(bundle_id) is None:
        raise CandidateBoundaryError(
            "candidate_install_bundle_id_invalid", repr(bundle_id)
        )
    authorization_path = AUTHORIZATION_ROOT / f"{bundle_id}.json"
    _validate_owned_directory_chain(authorization_path.parent, required_uid=0)
    try:
        observed = authorization_path.lstat()
    except OSError as exc:
        raise CandidateBoundaryError(
            "candidate_authorization_file_unavailable", str(authorization_path)
        ) from exc
    if (
        stat.S_ISLNK(observed.st_mode)
        or not stat.S_ISREG(observed.st_mode)
        or observed.st_uid != 0
        or observed.st_nlink != 1
        or observed.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
    ):
        raise CandidateBoundaryError(
            "candidate_authorization_file_untrusted", str(authorization_path)
        )
    raw, _resolved, _stat = _read_stable_regular(
        authorization_path, authorized_root=AUTHORIZATION_ROOT
    )
    try:
        value = strict_json_loads(raw)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CandidateBoundaryError(
            "candidate_authorization_unreadable", str(authorization_path)
        ) from exc
    if not isinstance(value, dict):
        raise CandidateBoundaryError(
            "candidate_authorization_unreadable", str(authorization_path)
        )
    validate_install_authorization_v1(value)
    if value.get("bundle_id") != bundle_id:
        raise CandidateBoundaryError(
            "candidate_authorization_bundle_id_mismatch", bundle_id
        )
    return value


def _json_output(value: Mapping[str, Any]) -> None:
    print(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare = subparsers.add_parser(
        "prepare", help="build an unprivileged closed candidate bundle"
    )
    prepare.add_argument("--repository-root", type=Path, required=True)
    prepare.add_argument("--python", type=Path, required=True)
    prepare.add_argument("--uv", type=Path, required=True)
    prepare.add_argument("--output", type=Path, required=True)
    prepare.add_argument("--preactivation-decision", type=Path, required=True)
    prepare.add_argument(
        "--worker-principal-resolution", type=Path, required=True
    )
    install = subparsers.add_parser(
        "install", help="install a separately authorized candidate bundle"
    )
    install.add_argument("--bundle-id", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        if arguments.command == "prepare":
            if os.geteuid() == 0:
                raise CandidateBoundaryError(
                    "candidate_prepare_as_root_prohibited", "prepare"
                )
            result = prepare_repository_bundle_v1(
                repository_root=arguments.repository_root,
                python_path=arguments.python,
                uv_path=arguments.uv,
                output=arguments.output,
                preactivation_decision_path=arguments.preactivation_decision,
                worker_principal_resolution_path=(
                    arguments.worker_principal_resolution
                ),
            )
            _json_output(
                {
                    "status": "candidate_bundle_prepared",
                    "bundle_id": result["bundle_id"],
                    "bundle_digest": result["bundle_digest"],
                    "human_install_authorization": "pending",
                    "formal_authority": "none",
                    "positive_assurance_allowed": False,
                }
            )
            return 0
        authorization = _read_root_authorization_by_bundle_id_v1(
            arguments.bundle_id
        )
        bundle_root = Path(str(authorization["source_bundle_path"]))
        manifest, manifest_raw = _load_bundle_manifest_raw_v1(bundle_root)
        validate_install_authorization_v1(
            authorization,
            manifest,
            bundle_root=bundle_root,
            manifest_raw=manifest_raw,
        )
        _assert_root_bootstrap_installer(manifest)
        receipt = _install_candidate_bundle(
            bundle_root=bundle_root,
            authorization=authorization,
        )
        _json_output(receipt)
        return 0
    except CandidateBoundaryError as exc:
        print(
            json.dumps(
                {
                    "status": "error",
                    "error": {"code": exc.code, "detail": exc.detail},
                    "formal_authority": "none",
                },
                ensure_ascii=False,
                sort_keys=True,
                allow_nan=False,
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
