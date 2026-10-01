#!/usr/bin/python3
"""Stdlib-only outer verifier for the U-10 root broker.

This file is installed outside every execution snapshot.  A fixed root-owned
shell entrypoint clears the parent environment before the OS-protected system
Python loads this verifier.  Only after the exact current store, its immutable
history original, activation authorization, two-phase activation ledger,
complete snapshot denominator, snapshot interpreter, and inner bootstrap have
been checked does this process replace itself with the snapshot interpreter.
"""

from __future__ import annotations

import ctypes
from datetime import datetime, timedelta
import errno
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import plistlib
import pwd
import re
import stat
import subprocess
import sys
from typing import Any
import uuid


U10_ROOT = Path("/Library/Application Support/semantic-guard/u10")
CURRENT_STORE = U10_ROOT / "trust-store-current.json"
HISTORY_ROOT = U10_ROOT / "trust-store-history" / "sha256"
AUTHORIZATION_ROOT = U10_ROOT / "authorizations"
STORE_ACTIVATION_BASIS_ROOT = U10_ROOT / "store-activation-bases"
STORE_ACTIVATION_LEDGER_ROOT = U10_ROOT / "activations" / "store-transitions"
STORE_ACTIVATION_LEDGER_POLICY = (
    "authorization_id_interval_receipt_atomic_publish/v3"
)
STORE_ACTIVATION_LEDGER_RETENTION_POLICY = (
    "no_automatic_deletion_while_store_revision_is_retained/v1"
)
REVOCATION_SELECTOR = U10_ROOT / "trust-store-current-revocation.json"
REVOCATION_ROOT = U10_ROOT / "revocations" / "sha256"
REVOCATION_LEDGER_ROOT = U10_ROOT / "activations" / "store-revocations"
REVOCATION_LEDGER_POLICY = (
    "authorization_id_interval_receipt_atomic_publish/v2"
)
REVOCATION_LEDGER_RETENTION_POLICY = (
    "no_automatic_deletion_while_store_revision_is_retained/v1"
)
SNAPSHOT_ROOT = U10_ROOT / "snapshots"
SNAPSHOT_PROJECTION_LEDGER_ROOT = (
    U10_ROOT / "activations" / "snapshot-projections"
)
SNAPSHOT_ACTIVATION_LEDGER_ROOT = (
    U10_ROOT / "activations" / "snapshot-activations"
)
SNAPSHOT_ACTIVATION_ROOT = U10_ROOT / "activations" / "snapshots"
ENTRYPOINT = U10_ROOT / "bootstrap" / "u10_root_broker_entrypoint.sh"
OUTER_LAUNCHER = U10_ROOT / "bootstrap" / "u10_root_broker_outer_launcher.py"
EFFECTIVE_PYTHON_PATH = U10_ROOT / "bootstrap" / "effective-python.path"
EFFECTIVE_RUNTIME_MANIFEST = (
    U10_ROOT / "bootstrap" / "effective-python-runtime-manifest.json"
)
INNER_NAME = "u10_root_broker_bootstrap.py"
MANIFEST_NAME = "u10-execution-snapshot-manifest-v1.json"
_ENTITY_REFERENCE_V1 = re.compile(
    r"^.{1,200}・(?P<entity_id>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$"
)
_NON_LOGIN_SHELLS_V1 = frozenset(
    {"/bin/false", "/usr/bin/false", "/sbin/nologin", "/usr/sbin/nologin"}
)
EXPECTED_ENVIRONMENT = {
    "PATH": "",
    "LC_ALL": "C",
    "PYTHONDONTWRITEBYTECODE": "1",
    "SEMANTIC_GUARD_U10_LAUNCH": "fixed-root-wrapper-v3",
}
FORBIDDEN_ENVIRONMENT_PREFIXES = ("DYLD_", "LD_", "PYTHONPATH", "PYTHONHOME")
RUNTIME_CLOSURE_PROFILE = "darwin-executed-image-common-root-closure/v1"
RUNTIME_OS_EXCLUSION_PROFILE = (
    "darwin-dyld-system-library-roots-os-build-bound/v1"
)
RUNTIME_OS_ASSET_ROOTS = (Path("/System/Library"), Path("/usr/lib"))
RUNTIME_PROBE_ENVIRONMENT = {
    "PATH": "",
    "LC_ALL": "C",
    "PYTHONDONTWRITEBYTECODE": "1",
}
RUNTIME_PROBE = r'''
import ctypes
import datetime
import errno
import hashlib
import json
import os
import pathlib
import plistlib
import re
import site
import stat
import sys
import sysconfig
import typing

OS_ROOTS = ("/System/Library", "/usr/lib")
EXPECTED_ENVIRONMENT = {"PATH": "", "LC_ALL": "C", "PYTHONDONTWRITEBYTECODE": "1"}
observed_environment = dict(os.environ)
injected = observed_environment.pop("__CF_USER_TEXT_ENCODING", None)
if injected is not None:
    matched = re.fullmatch(r"0x([0-9A-Fa-f]+):0x[0-9A-Fa-f]+:0x[0-9A-Fa-f]+", str(injected))
    if matched is None or int(matched.group(1), 16) != os.geteuid():
        raise RuntimeError("unexpected Darwin environment injection")
if observed_environment != EXPECTED_ENVIRONMENT:
    raise RuntimeError("runtime probe environment is not closed")
def canonical(raw):
    path = pathlib.Path(str(raw))
    if not path.is_absolute() or path != pathlib.Path(os.path.normpath(str(path))):
        raise RuntimeError("non-canonical probe path: %r" % (raw,))
    return str(path)
def record(raw):
    locator = canonical(raw)
    path = pathlib.Path(locator)
    state = "present" if path.exists() or path.is_symlink() else "absent"
    return {"locator": locator, "resolved_locator": str(path.resolve(strict=False)), "state": state}
def under(path, root):
    try:
        pathlib.Path(path).relative_to(pathlib.Path(root))
        return True
    except ValueError:
        return False
libc = ctypes.CDLL(None, use_errno=True)
ns_get_executable_path = libc._NSGetExecutablePath
ns_get_executable_path.argtypes = [ctypes.c_char_p, ctypes.POINTER(ctypes.c_uint32)]
ns_get_executable_path.restype = ctypes.c_int
size = ctypes.c_uint32(0)
ns_get_executable_path(None, ctypes.byref(size))
if size.value <= 1 or size.value > 1024 * 1024:
    raise RuntimeError("invalid _NSGetExecutablePath size")
buffer = ctypes.create_string_buffer(size.value)
if ns_get_executable_path(buffer, ctypes.byref(size)) != 0:
    raise RuntimeError("_NSGetExecutablePath failed")
dyld_image_count = libc._dyld_image_count
dyld_image_count.argtypes = []
dyld_image_count.restype = ctypes.c_uint32
dyld_get_image_name = libc._dyld_get_image_name
dyld_get_image_name.argtypes = [ctypes.c_uint32]
dyld_get_image_name.restype = ctypes.c_char_p
dyld = []
for index in range(dyld_image_count()):
    raw_name = dyld_get_image_name(index)
    if not raw_name:
        raise RuntimeError("dyld image without a name")
    item = record(os.fsdecode(raw_name))
    matching_roots = [root for root in OS_ROOTS if under(item["locator"], root) and under(item["resolved_locator"], root)]
    if len(matching_roots) == 1:
        item["classification"] = "excluded_os_asset"
        item["os_asset_root"] = matching_roots[0]
    else:
        item["classification"] = "runtime_tree"
        item["os_asset_root"] = None
    dyld.append(item)
dyld.sort(key=lambda item: (item["resolved_locator"], item["locator"]))
if len({(item["locator"], item["resolved_locator"]) for item in dyld}) != len(dyld):
    raise RuntimeError("duplicate dyld image")
sys_path = [record(item) for item in sys.path]
if len({item["locator"] for item in sys_path}) != len(sys_path):
    raise RuntimeError("duplicate sys.path entry")
stdlib_roots = []
for name in ("stdlib", "platstdlib"):
    item = record(sysconfig.get_path(name))
    item["kind"] = name
    stdlib_roots.append(item)
stdlib_roots.sort(key=lambda item: item["kind"])
site_values = [("site.getsitepackages", item) for item in site.getsitepackages()]
for name in ("purelib", "platlib"):
    site_values.append(("sysconfig.%s" % name, sysconfig.get_path(name)))
active_sys_path = {item["resolved_locator"] for item in sys_path}
site_roots = []
for source, value in site_values:
    item = record(value)
    item["source"] = source
    item["active"] = item["resolved_locator"] in active_sys_path
    item["disposition"] = "runtime_tree" if item["active"] else "suppressed_by_isolated_no_site"
    site_roots.append(item)
site_roots.sort(key=lambda item: (item["resolved_locator"], item["source"]))
module_origins = []
for name, module in sorted(sys.modules.items()):
    if name == "__main__":
        continue
    origin = getattr(module, "__file__", None)
    if origin is None:
        continue
    item = record(origin)
    item["module"] = name
    module_origins.append(item)
result = {
    "probe_profile": "darwin-executed-image-common-root-closure/v1",
    "runtime_version": ".".join(map(str, sys.version_info[:3])),
    "probe_execution_identity": {"effective_uid": os.geteuid(), "effective_gid": os.getegid()},
    "process_image": {"sys_executable": record(sys.executable), "ns_get_executable_path": record(os.fsdecode(buffer.value))},
    "python_prefixes": {"prefix": record(sys.prefix), "base_prefix": record(sys.base_prefix)},
    "sys_path": sys_path,
    "stdlib_roots": stdlib_roots,
    "site_roots": site_roots,
    "site_policy": "isolated_no_site_only_active_paths_enter_runtime_closure/v1",
    "imported_module_origins": module_origins,
    "dyld_images": dyld,
    "os_asset_exclusion": {"profile": "darwin-dyld-system-library-roots-os-build-bound/v1", "allowed_roots": list(OS_ROOTS), "scope": "dyld_images_only", "binding": "exact_platform_binding_and_os_build_artifact"},
}
print(json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False))
'''
BROKER_PACKAGE = "semantic_guard_u10_broker"
STABLE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}$")
RFC3339_PATTERN = re.compile(
    r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:)(\d{2})(\.\d+)?(Z|[+-]\d{2}:\d{2})$"
)
STORE_REF_FIELDS = frozenset(
    {
        "store_id",
        "store_revision_id",
        "store_version",
        "store_activation_basis_digest",
        "artifact_digest",
        "semantic_digest",
    }
)
REVOCATION_REF_FIELDS = frozenset(
    {"revocation_id", "artifact_digest", "semantic_digest"}
)
ROOT_ARTIFACT_REF_FIELDS = frozenset(
    {"record_id", "locator", "artifact_digest", "semantic_digest"}
)
STORE_ACTIVATION_BASIS_FIELDS = frozenset(
    {
        "schema_version",
        "basis_id",
        "basis_version",
        "record_kind",
        "store_content",
        "store_activation_basis_digest",
        "store_transition_digest",
        "entry_id",
        "snapshot_manifest_ref",
        "snapshot_activation_authorization_ref",
        "signing_key_ref",
        "signing_key_selector_ref",
        "prior_store_ref",
        "prior_revocation_ref",
        "publisher_contract_binding",
        "prepared_at",
        "publication_state",
        "formal_authority",
        "positive_assurance_allowed",
        "basis_digest",
    }
)
KEY_SELECTOR_REF_FIELDS = frozenset(
    {"selector_id", "locator", "artifact_digest", "selector_digest"}
)
KEY_PUBLIC_METADATA_REF_FIELDS = frozenset(
    {
        "key_id",
        "key_entity_ref",
        "locator",
        "artifact_digest",
        "metadata_digest",
        "generation_authorization_ref",
        "generation_consumption_ref",
    }
)
STORE_ACTIVATION_RECEIPT_FIELDS = frozenset(
    {
        "schema_version",
        "receipt_id",
        "record_kind",
        "public_operation",
        "public_identifier",
        "authorization_id",
        "authorization_digest",
        "consumption_digest",
        "store_activation_basis_ref",
        "transition_kind",
        "prior_store_ref",
        "prior_revocation_ref",
        "activated_store_ref",
        "publisher_contract_binding",
        "publication_not_before",
        "publication_observed_at",
        "receipt_recorded_at",
        "formal_authority",
        "positive_assurance_allowed",
        "receipt_digest",
    }
)
STORE_ACTIVATION_CONSUMPTION_FIELDS = frozenset(
    {
        "schema_version",
        "consumption_id",
        "record_kind",
        "public_operation",
        "public_identifier",
        "authorization_id",
        "authorization_digest",
        "store_activation_basis_ref",
        "transition_kind",
        "prior_store_ref",
        "prior_revocation_ref",
        "target_store_ref",
        "publisher_contract_binding",
        "reserved_at",
        "publication_occurred",
        "formal_authority",
        "positive_assurance_allowed",
        "consumption_digest",
    }
)
STORE_REVOCATION_FIELDS = frozenset(
    {
        "schema_version",
        "revocation_id",
        "revocation_version",
        "record_kind",
        "human_decision",
        "decision_owner",
        "target_store_id",
        "target_store_revision_id",
        "target_store_version",
        "target_store_activation_basis_digest",
        "target_store_artifact_digest",
        "target_store_digest",
        "target_activation_receipt_ref",
        "publisher_contract_binding",
        "revoked_operation",
        "decision_entry_profile",
        "recorded_at",
        "reason",
        "u4_principal_authenticity",
        "authority_scope",
        "formal_authority",
        "positive_assurance_allowed",
        "revocation_digest",
    }
)
STORE_REVOCATION_CONSUMPTION_FIELDS = frozenset(
    {
        "schema_version",
        "consumption_id",
        "record_kind",
        "revocation_id",
        "revocation_digest",
        "target_store_ref",
        "target_activation_receipt_ref",
        "consumed_at",
        "publication_occurred",
        "formal_authority",
        "positive_assurance_allowed",
        "consumption_digest",
    }
)
STORE_REVOCATION_RECEIPT_FIELDS = frozenset(
    {
        "schema_version",
        "receipt_id",
        "record_kind",
        "publisher_operation_id",
        "publisher_euid",
        "revocation_id",
        "revocation_digest",
        "consumption_digest",
        "target_store_ref",
        "target_activation_receipt_ref",
        "history_ref",
        "publisher_contract_binding",
        "selector_path",
        "publication_not_before",
        "publication_observed_at",
        "receipt_recorded_at",
        "formal_authority",
        "positive_assurance_allowed",
        "receipt_digest",
    }
)


class OuterLaunchError(RuntimeError):
    pass


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


def _assert_no_extended_acl(path: Path) -> None:
    """Reject every Darwin extended ACL, including inherited allow entries."""

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
        raise OuterLaunchError(f"extended ACL is prohibited: {path}")
    observed_errno = ctypes.get_errno()
    if observed_errno != errno.ENOENT:
        raise OuterLaunchError(
            f"extended ACL could not be observed: {path}: errno={observed_errno}"
        )


def _consume_os_injected_environment() -> None:
    """Validate then remove Darwin's process-local CF encoding injection."""

    allowed = set(EXPECTED_ENVIRONMENT)
    observed = set(os.environ)
    extra = observed - allowed
    if extra == {"__CF_USER_TEXT_ENCODING"}:
        value = os.environ["__CF_USER_TEXT_ENCODING"]
        matched = re.fullmatch(
            r"0x([0-9A-Fa-f]+):0x[0-9A-Fa-f]+:0x[0-9A-Fa-f]+",
            value,
        )
        if matched is None or int(matched.group(1), 16) != os.geteuid():
            raise OuterLaunchError("invalid Darwin process-local environment injection")
        os.environ.pop("__CF_USER_TEXT_ENCODING", None)
        observed = set(os.environ)
    if observed != allowed:
        raise OuterLaunchError(
            f"outer launcher environment denominator mismatch: {sorted(observed)!r}"
        )


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise OuterLaunchError(
            f"canonical JSON material invalid: {type(exc).__name__}"
        ) from exc


def _strict_json_clone(value: Any) -> Any:
    """Clone through the same finite, duplicate-safe JSON contract."""

    return strict_json_loads(_canonical(value))


def _digest(raw: bytes) -> dict[str, str]:
    return {"algorithm": "sha256", "value": hashlib.sha256(raw).hexdigest()}


def _sealed(value: dict[str, Any], field: str) -> dict[str, str]:
    material = dict(value)
    material.pop(field, None)
    return _digest(_canonical(material))


def _is_digest(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == {"algorithm", "value"}
        and value.get("algorithm") == "sha256"
        and isinstance(value.get("value"), str)
        and len(value["value"]) == 64
        and all(character in "0123456789abcdef" for character in value["value"])
    )


def _is_publisher_contract_binding(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    required = {
        "allowed_operations", "artifacts", "binding_digest",
        "bootstrap_provenance_ref", "broker_runtime_ref",
        "caller_environment_injection_allowed",
        "caller_supplied_inline_authority_allowed",
        "caller_supplied_paths_allowed", "caller_supplied_raw_payloads_allowed",
        "contract_id", "control_runtime_ref", "formal_authority",
        "launch_profile", "positive_assurance_allowed",
        "public_argument_denominator", "schema_version",
    }
    if (
        set(value) != required
        or value.get("schema_version")
        != "semantic-guard-u10-control-publisher-contract-binding/v1"
        or value.get("contract_id")
        != "semantic-guard.u10.fixed-root-control-publisher.v1"
        or value.get("launch_profile")
        != "fixed-root-wrapper-broker-outer-control-runtime-dispatcher/v1"
        or value.get("public_argument_denominator")
        != ["operation", "identifier"]
        or value.get("allowed_operations")
        != [
            "activate-snapshot",
            "activate-store",
            "key",
            "project-snapshot",
            "revoke-store",
        ]
        or value.get("formal_authority") != "none"
        or any(
            value.get(field) is not False
            for field in (
                "caller_environment_injection_allowed",
                "caller_supplied_inline_authority_allowed",
                "caller_supplied_paths_allowed",
                "caller_supplied_raw_payloads_allowed",
                "positive_assurance_allowed",
            )
        )
        or not _is_digest(value.get("binding_digest"))
        or value.get("binding_digest") != _sealed(value, "binding_digest")
    ):
        return False
    bootstrap = "/Library/Application Support/semantic-guard/u10/bootstrap"
    expected_artifacts = {
        "broker_outer_launcher": f"{bootstrap}/u10_root_broker_outer_launcher.py",
        "initial_trust_provisioner": f"{bootstrap}/u10_initial_trust_provisioner.py",
        "root_control_dispatcher": f"{bootstrap}/u10_root_control_dispatcher.py",
        "root_control_entrypoint": f"{bootstrap}/u10_root_control_entrypoint.sh",
        "root_control_outer_launcher": f"{bootstrap}/u10_root_control_outer_launcher.py",
        "snapshot_store_producer": f"{bootstrap}/u10_snapshot_store_production.py",
    }
    artifacts = value.get("artifacts")
    if not isinstance(artifacts, dict) or set(artifacts) != set(
        expected_artifacts
    ):
        return False
    for name, locator in expected_artifacts.items():
        reference = artifacts[name]
        if (
            not isinstance(reference, dict)
            or set(reference) != {"locator", "artifact_digest"}
            or reference.get("locator") != locator
            or not _is_digest(reference.get("artifact_digest"))
        ):
            return False
    expected_runtime_paths = {
        "broker_runtime_ref": (
            f"{bootstrap}/effective-python.path",
            f"{bootstrap}/effective-python-runtime-manifest.json",
        ),
        "control_runtime_ref": (
            f"{bootstrap}/control-effective-python.path",
            f"{bootstrap}/control-python-runtime-manifest.json",
        ),
    }
    for field, (effective_path, manifest_path) in expected_runtime_paths.items():
        reference = value.get(field)
        expected_fields = {
            "effective_python_path",
            "effective_python_path_artifact_digest",
            "runtime_manifest_artifact_digest",
            "runtime_manifest_digest",
            "runtime_manifest_locator",
            "runtime_tree_digest",
        }
        if field == "control_runtime_ref":
            expected_fields.add("broker_package_binding")
        if (
            not isinstance(reference, dict)
            or set(reference) != expected_fields
            or reference.get("effective_python_path") != effective_path
            or reference.get("runtime_manifest_locator") != manifest_path
            or any(
                not _is_digest(reference.get(name))
                for name in (
                    "effective_python_path_artifact_digest",
                    "runtime_manifest_artifact_digest",
                    "runtime_manifest_digest",
                    "runtime_tree_digest",
                )
            )
        ):
            return False
    package = value["control_runtime_ref"].get("broker_package_binding")
    if (
        not isinstance(package, dict)
        or set(package) != {"entry_count", "package_root", "tree_digest"}
        or not isinstance(package.get("entry_count"), int)
        or isinstance(package.get("entry_count"), bool)
        or package["entry_count"] < 1
        or not isinstance(package.get("package_root"), str)
        or not package["package_root"].startswith("/")
        or not _is_digest(package.get("tree_digest"))
    ):
        return False
    provenance = value.get("bootstrap_provenance_ref")
    chain = provenance.get("chain_artifact_digests") if isinstance(provenance, dict) else None
    return (
        isinstance(provenance, dict)
        and set(provenance)
        == {
            "authorization_id", "binding_artifact_digest",
            "binding_digest", "binding_id", "chain_artifact_digests",
            "locator", "plan_id",
        }
        and provenance.get("locator")
        == "/Library/Application Support/semantic-guard/u10/bootstrap/initial-bootstrap-provenance-binding.json"
        and all(
            _is_stable_id(provenance.get(name))
            for name in ("binding_id", "authorization_id", "plan_id")
        )
        and _is_digest(provenance.get("binding_artifact_digest"))
        and _is_digest(provenance.get("binding_digest"))
        and isinstance(chain, dict)
        and set(chain) == {"authorization", "consumption", "plan", "receipt"}
        and all(_is_digest(item) for item in chain.values())
    )


def _is_stable_id(value: Any) -> bool:
    return isinstance(value, str) and STABLE_ID_PATTERN.fullmatch(value) is not None


def _parse_rfc3339_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    matched = RFC3339_PATTERN.fullmatch(value)
    if matched is None:
        return None
    prefix, second, fraction, zone = matched.groups()
    normalized_second = "59" if second == "60" else second
    normalized_zone = "+00:00" if zone == "Z" else zone
    try:
        observed = datetime.fromisoformat(
            f"{prefix}{normalized_second}{fraction or ''}{normalized_zone}"
        )
    except ValueError:
        return None
    if observed.tzinfo is None:
        return None
    return observed + timedelta(seconds=1) if second == "60" else observed


def _is_rfc3339_datetime(value: Any) -> bool:
    return _parse_rfc3339_datetime(value) is not None


def _is_store_transition_ref(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == STORE_REF_FIELDS
        and _is_stable_id(value.get("store_id"))
        and _is_stable_id(value.get("store_revision_id"))
        and isinstance(value.get("store_version"), str)
        and 1 <= len(value["store_version"]) <= 128
        and _is_digest(value.get("store_activation_basis_digest"))
        and _is_digest(value.get("artifact_digest"))
        and _is_digest(value.get("semantic_digest"))
    )


def _is_revocation_transition_ref(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == REVOCATION_REF_FIELDS
        and _is_stable_id(value.get("revocation_id"))
        and _is_digest(value.get("artifact_digest"))
        and _is_digest(value.get("semantic_digest"))
    )


def _is_root_artifact_ref(value: Any) -> bool:
    if not isinstance(value, dict) or set(value) != ROOT_ARTIFACT_REF_FIELDS:
        return False
    try:
        locator = Path(str(value.get("locator", "")))
        locator.relative_to(U10_ROOT)
    except ValueError:
        return False
    return (
        locator.is_absolute()
        and locator == Path(os.path.normpath(str(locator)))
        and _is_stable_id(value.get("record_id"))
        and _is_digest(value.get("artifact_digest"))
        and _is_digest(value.get("semantic_digest"))
    )


def _is_key_selector_ref_v2(value: Any) -> bool:
    if not isinstance(value, dict) or set(value) != KEY_SELECTOR_REF_FIELDS:
        return False
    artifact_digest = value.get("artifact_digest")
    if not _is_digest(artifact_digest):
        return False
    locator = U10_ROOT / "keys" / "selector-history" / "sha256" / (
        f"{artifact_digest['value']}.json"
    )
    return (
        _is_stable_id(value.get("selector_id"))
        and value.get("locator") == str(locator)
        and _is_digest(value.get("selector_digest"))
    )


def _is_key_public_metadata_ref_v2(value: Any) -> bool:
    if (
        not isinstance(value, dict)
        or set(value) != KEY_PUBLIC_METADATA_REF_FIELDS
        or not isinstance(value.get("key_id"), str)
    ):
        return False
    try:
        key_id = str(uuid.UUID(value["key_id"]))
    except ValueError:
        return False
    locator = U10_ROOT / "keys" / "generations" / key_id / (
        "public-metadata.json"
    )
    return (
        value.get("key_id") == key_id
        and isinstance(value.get("key_entity_ref"), str)
        and _ENTITY_REFERENCE_V1.fullmatch(value["key_entity_ref"])
        is not None
        and value.get("locator") == str(locator)
        and _is_digest(value.get("artifact_digest"))
        and _is_digest(value.get("metadata_digest"))
        and isinstance(value.get("generation_authorization_ref"), dict)
        and isinstance(value.get("generation_consumption_ref"), dict)
    )


def _has_valid_transition_context(value: dict[str, Any]) -> bool:
    required = {"transition_kind", "prior_store_ref", "prior_revocation_ref"}
    if not required.issubset(value):
        return False
    transition_kind = value.get("transition_kind")
    prior_store_ref = value.get("prior_store_ref")
    prior_revocation_ref = value.get("prior_revocation_ref")
    if transition_kind == "initial_activation":
        return prior_store_ref is None and prior_revocation_ref is None
    if transition_kind == "replace_current_revision":
        return _is_store_transition_ref(prior_store_ref) and (
            prior_revocation_ref is None
            or _is_revocation_transition_ref(prior_revocation_ref)
        )
    return False


def _store_transition_ref(store: dict[str, Any], raw: bytes) -> dict[str, Any]:
    return {
        "store_id": store.get("store_id"),
        "store_revision_id": store.get("store_revision_id"),
        "store_version": store.get("store_version"),
        "store_activation_basis_digest": store.get("store_activation_basis_digest"),
        "artifact_digest": _digest(raw),
        "semantic_digest": store.get("store_digest"),
    }


def _snapshot_basis(value: dict[str, Any]) -> dict[str, str]:
    material = _strict_json_clone(value)
    for field in (
        "lifecycle_state",
        "immutability_verification",
        "environment_adoption_ref",
        "snapshot_adoption_authorization_ref",
        "activation_ref",
        "revocation_ref",
        "snapshot_basis_digest",
        "manifest_digest",
    ):
        material.pop(field, None)
    storage = material.get("root_storage")
    if isinstance(storage, dict):
        storage.pop("storage_state", None)
    return _digest(_canonical(material))


def _store_activation_content(value: dict[str, Any]) -> dict[str, Any]:
    material = _strict_json_clone(value)
    for field in (
        "lifecycle_state",
        "store_activation_basis_digest",
        "activation_authorization_ref",
        "revocation_ref",
        "store_digest",
    ):
        material.pop(field, None)
    return material


def _store_activation_basis(value: dict[str, Any]) -> dict[str, str]:
    return _digest(_canonical(_store_activation_content(value)))


def _store_activation_transition_digest(
    basis: dict[str, Any],
) -> dict[str, str]:
    material = {
        "schema_version": "semantic-guard-u10-store-transition-basis/v2",
        "snapshot_manifest_ref": basis.get("snapshot_manifest_ref"),
        "entry_id": basis.get("entry_id"),
        "prior_store_ref": basis.get("prior_store_ref"),
        "prior_revocation_ref": basis.get("prior_revocation_ref"),
        "signing_key_ref": basis.get("signing_key_ref"),
        "signing_key_selector_ref": basis.get(
            "signing_key_selector_ref"
        ),
    }
    return _digest(_canonical(material))


def _absolute_chain(path: Path) -> list[Path]:
    if not path.is_absolute() or path != Path(os.path.normpath(str(path))):
        raise OuterLaunchError(f"non-canonical absolute path: {path}")
    current = Path(path.anchor)
    result = [current]
    for part in path.parts[1:]:
        current /= part
        result.append(current)
    return result


def _validate_ancestors(path: Path, *, include_leaf: bool) -> None:
    chain = _absolute_chain(path if include_leaf else path.parent)
    for item in chain:
        observed = item.lstat()
        _assert_no_extended_acl(item)
        if (
            stat.S_ISLNK(observed.st_mode)
            or observed.st_uid != 0
            or observed.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
            or not stat.S_ISDIR(observed.st_mode)
        ):
            raise OuterLaunchError(f"untrusted absolute ancestor: {item}")


def _read_root_file(
    path: Path,
    *,
    exact_mode: int | None = None,
    allow_hardlinks: bool = False,
) -> bytes:
    _validate_ancestors(path, include_leaf=False)
    before = path.lstat()
    _assert_no_extended_acl(path)
    if (
        stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_uid != 0
        or before.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
        or (before.st_nlink != 1 and not allow_hardlinks)
        or (exact_mode is not None and stat.S_IMODE(before.st_mode) != exact_mode)
    ):
        raise OuterLaunchError(f"untrusted root artifact: {path}")
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        opened = os.fstat(descriptor)
        identity = (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
        )
        if (
            opened.st_dev,
            opened.st_ino,
            opened.st_size,
            opened.st_mtime_ns,
            opened.st_ctime_ns,
        ) != identity:
            raise OuterLaunchError(f"artifact changed before read: {path}")
        chunks: list[bytes] = []
        total = 0
        while block := os.read(descriptor, 1024 * 1024):
            total += len(block)
            if total > 64 * 1024 * 1024:
                raise OuterLaunchError(f"artifact too large: {path}")
            chunks.append(block)
        after = os.fstat(descriptor)
        if (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        ) != identity:
            raise OuterLaunchError(f"artifact changed during read: {path}")
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _json(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = strict_json_loads(raw)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise OuterLaunchError(f"unreadable {label}") from exc
    if not isinstance(value, dict):
        raise OuterLaunchError(f"non-object {label}")
    return value


def _inside(root: Path, value: Any) -> Path:
    path = Path(str(value))
    if not path.is_absolute() or path != Path(os.path.normpath(str(path))):
        raise OuterLaunchError(f"non-canonical snapshot path: {path}")
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise OuterLaunchError(f"snapshot path escaped: {path}") from exc
    return path


def _verify_root_ref(
    reference: dict[str, Any],
    expected: Path,
    *,
    semantic_is_raw: bool = True,
) -> bytes:
    if Path(str(reference.get("locator"))) != expected:
        raise OuterLaunchError(f"root artifact locator mismatch: {expected}")
    raw = _read_root_file(expected)
    observed = expected.lstat()
    if (
        reference.get("owner_uid") != 0
        or reference.get("owner_gid") != 0
        or observed.st_uid != reference.get("owner_uid")
        or observed.st_gid != reference.get("owner_gid")
        or observed.st_nlink != 1
        or reference.get("write_protection")
        != "not_group_or_world_writable"
        or reference.get("artifact_digest") != _digest(raw)
        or (
            semantic_is_raw
            and reference.get("semantic_digest") != _digest(raw)
        )
    ):
        raise OuterLaunchError(f"root artifact binding mismatch: {expected}")
    return raw


def _verify_plain_root_ref(
    reference: dict[str, Any],
    expected: Path,
    *,
    semantic_digest: dict[str, str] | None = None,
    exact_mode: int | None = None,
) -> bytes:
    if not _is_root_artifact_ref(reference) or Path(
        str(reference.get("locator"))
    ) != expected:
        raise OuterLaunchError(f"plain root artifact locator mismatch: {expected}")
    raw = _read_root_file(expected, exact_mode=exact_mode)
    if (
        reference.get("artifact_digest") != _digest(raw)
        or (
            semantic_digest is not None
            and reference.get("semantic_digest") != semantic_digest
        )
    ):
        raise OuterLaunchError(f"plain root artifact binding mismatch: {expected}")
    return raw


def _verify_host_ref(reference: dict[str, Any], expected: Path) -> None:
    if Path(str(reference.get("locator"))) != expected:
        raise OuterLaunchError(f"host runtime locator mismatch: {expected}")
    _validate_ancestors(expected, include_leaf=False)
    raw = _read_root_file(expected, allow_hardlinks=True)
    resolved = Path(os.path.realpath(expected))
    if (
        Path(str(reference.get("resolved_locator"))) != resolved
        or reference.get("owner_uid") != 0
        or reference.get("artifact_digest") != _digest(raw)
        or reference.get("write_protection")
        != "absolute_ancestor_chain_not_group_or_world_writable"
    ):
        raise OuterLaunchError(f"host runtime binding mismatch: {expected}")


def _runtime_path_is_under(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _runtime_inclusion_paths(observation: dict[str, Any]) -> list[Path]:
    try:
        records = [
            observation["process_image"]["sys_executable"],
            observation["process_image"]["ns_get_executable_path"],
            observation["python_prefixes"]["prefix"],
            observation["python_prefixes"]["base_prefix"],
        ]
        records.extend(observation["sys_path"])
        records.extend(observation["stdlib_roots"])
        records.extend(
            item
            for item in observation["site_roots"]
            if item["active"] is True
        )
        records.extend(observation["imported_module_origins"])
        records.extend(
            item
            for item in observation["dyld_images"]
            if item["classification"] == "runtime_tree"
        )
        paths = [
            Path(item[field])
            for item in records
            for field in ("locator", "resolved_locator")
        ]
    except (KeyError, TypeError, ValueError) as exc:
        raise OuterLaunchError("bootstrap runtime closure malformed") from exc
    return paths


def _derive_runtime_root(observation: dict[str, Any]) -> Path:
    expected_exclusion = {
        "profile": RUNTIME_OS_EXCLUSION_PROFILE,
        "allowed_roots": [str(path) for path in RUNTIME_OS_ASSET_ROOTS],
        "scope": "dyld_images_only",
        "binding": "exact_platform_binding_and_os_build_artifact",
    }
    if (
        observation.get("probe_profile") != RUNTIME_CLOSURE_PROFILE
        or observation.get("probe_execution_identity")
        != {"effective_uid": 0, "effective_gid": 0}
        or observation.get("os_asset_exclusion") != expected_exclusion
    ):
        raise OuterLaunchError("bootstrap runtime closure contract mismatch")
    dyld = observation.get("dyld_images")
    if not isinstance(dyld, list) or not dyld:
        raise OuterLaunchError("bootstrap dyld denominator missing")
    for item in dyld:
        locator = Path(str(item.get("locator", "")))
        resolved = Path(str(item.get("resolved_locator", "")))
        if item.get("classification") == "excluded_os_asset":
            root = Path(str(item.get("os_asset_root", "")))
            if root not in RUNTIME_OS_ASSET_ROOTS or not (
                _runtime_path_is_under(locator, root)
                and _runtime_path_is_under(resolved, root)
            ):
                raise OuterLaunchError("invalid excluded OS dyld image")
        elif (
            item.get("classification") != "runtime_tree"
            or item.get("os_asset_root") is not None
        ):
            raise OuterLaunchError("invalid non-OS dyld image")
    paths = _runtime_inclusion_paths(observation)
    if not paths or any(not path.is_absolute() for path in paths):
        raise OuterLaunchError("bootstrap runtime closure path mismatch")
    try:
        root = Path(os.path.commonpath([str(path) for path in paths]))
    except ValueError as exc:
        raise OuterLaunchError("bootstrap runtime has no common root") from exc
    if (
        not root.is_dir()
        or Path(os.path.realpath(root)) != root
        or any(not _runtime_path_is_under(path, root) for path in paths)
    ):
        raise OuterLaunchError("bootstrap runtime derived root mismatch")
    prefix = Path(observation["python_prefixes"]["prefix"]["resolved_locator"])
    base_prefix = Path(
        observation["python_prefixes"]["base_prefix"]["resolved_locator"]
    )
    if prefix != base_prefix or root != base_prefix:
        raise OuterLaunchError("bootstrap runtime base_prefix mismatch")
    return root


def _probe_bootstrap_runtime(interpreter: Path) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            [str(interpreter), "-I", "-S", "-B", "-c", RUNTIME_PROBE],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
            env=RUNTIME_PROBE_ENVIRONMENT,
            text=True,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise OuterLaunchError("bootstrap runtime execution probe failed") from exc
    if completed.returncode != 0:
        raise OuterLaunchError(
            "bootstrap runtime execution probe failed: "
            + completed.stderr[:1000]
        )
    try:
        observation = strict_json_loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise OuterLaunchError("bootstrap runtime probe unreadable") from exc
    if not isinstance(observation, dict):
        raise OuterLaunchError("bootstrap runtime probe malformed")
    _derive_runtime_root(observation)
    return observation


def _validate_current_process_runtime_closure(
    observation: dict[str, Any], root: Path, interpreter: Path
) -> None:
    # The exact child probe above proves the fixed interpreter's repeatable
    # closure.  These observations additionally bind the already-running outer
    # verifier rather than assuming the child stands in for its parent.
    if Path(os.path.realpath(sys.executable)) != interpreter:
        raise OuterLaunchError("running bootstrap interpreter mismatch")
    libc = ctypes.CDLL(None, use_errno=True)
    ns_get_executable_path = libc._NSGetExecutablePath
    ns_get_executable_path.argtypes = [
        ctypes.c_char_p,
        ctypes.POINTER(ctypes.c_uint32),
    ]
    ns_get_executable_path.restype = ctypes.c_int
    size = ctypes.c_uint32(0)
    ns_get_executable_path(None, ctypes.byref(size))
    if size.value <= 1 or size.value > 1024 * 1024:
        raise OuterLaunchError("running bootstrap process image unavailable")
    buffer = ctypes.create_string_buffer(size.value)
    if ns_get_executable_path(buffer, ctypes.byref(size)) != 0:
        raise OuterLaunchError("running bootstrap process image unavailable")
    running_image = Path(os.path.realpath(os.fsdecode(buffer.value)))
    expected_image = Path(
        observation["process_image"]["ns_get_executable_path"][
            "resolved_locator"
        ]
    )
    if running_image != expected_image or not _runtime_path_is_under(
        running_image, root
    ):
        raise OuterLaunchError("running bootstrap process image escaped closure")
    if [str(Path(item)) for item in sys.path] != [
        item["locator"] for item in observation["sys_path"]
    ]:
        raise OuterLaunchError("running bootstrap sys.path mismatch")
    dyld_image_count = libc._dyld_image_count
    dyld_image_count.argtypes = []
    dyld_image_count.restype = ctypes.c_uint32
    dyld_get_image_name = libc._dyld_get_image_name
    dyld_get_image_name.argtypes = [ctypes.c_uint32]
    dyld_get_image_name.restype = ctypes.c_char_p
    for index in range(dyld_image_count()):
        raw_name = dyld_get_image_name(index)
        if not raw_name:
            raise OuterLaunchError("running dyld image name unavailable")
        path = Path(os.path.realpath(os.fsdecode(raw_name)))
        if _runtime_path_is_under(path, root):
            continue
        if not any(
            _runtime_path_is_under(path, os_root)
            for os_root in RUNTIME_OS_ASSET_ROOTS
        ):
            raise OuterLaunchError(f"running non-OS dyld image escaped: {path}")
    for name, module in sys.modules.items():
        if name == "__main__":
            continue
        origin = getattr(module, "__file__", None)
        if origin is None:
            continue
        path = Path(os.path.realpath(origin))
        if not _runtime_path_is_under(path, root):
            raise OuterLaunchError(f"running module origin escaped: {name}: {path}")


def _host_runtime_tree_entries(root: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    _validate_ancestors(root, include_leaf=True)
    for raw_directory, directories, files in os.walk(
        root, topdown=True, followlinks=False
    ):
        base = Path(raw_directory)
        directories.sort()
        files.sort()
        for name in (*directories, *files):
            path = base / name
            observed = path.lstat()
            _assert_no_extended_acl(path)
            if observed.st_uid != 0:
                raise OuterLaunchError(f"non-root bootstrap runtime path: {path}")
            common = {
                "path": path.relative_to(root).as_posix(),
                "mode": stat.S_IMODE(observed.st_mode),
                "uid": observed.st_uid,
                "gid": observed.st_gid,
            }
            if stat.S_ISLNK(observed.st_mode):
                target = os.readlink(path)
                resolved = Path(os.path.realpath(path))
                try:
                    resolved.relative_to(root)
                except ValueError as exc:
                    raise OuterLaunchError(
                        f"bootstrap runtime symlink escaped: {path}"
                    ) from exc
                entries.append({**common, "kind": "symlink", "target": target})
            elif stat.S_ISDIR(observed.st_mode):
                if observed.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
                    raise OuterLaunchError(f"mutable bootstrap runtime path: {path}")
                entries.append({**common, "kind": "directory"})
            elif stat.S_ISREG(observed.st_mode):
                if observed.st_nlink != 1:
                    raise OuterLaunchError(f"hard-linked bootstrap runtime file: {path}")
                raw = _read_root_file(path)
                entries.append(
                    {
                        **common,
                        "kind": "file",
                        "size": observed.st_size,
                        "artifact_digest": _digest(raw),
                    }
                )
            else:
                raise OuterLaunchError(f"special bootstrap runtime path: {path}")
    entries.sort(key=lambda item: str(item["path"]))
    return entries


def _validate_bootstrap_runtime_manifest(
    platform_contract: dict[str, Any],
) -> dict[str, Any]:
    reference = platform_contract.get("effective_runtime_manifest_ref")
    if not isinstance(reference, dict):
        raise OuterLaunchError("bootstrap runtime manifest reference missing")
    raw = _verify_root_ref(reference, EFFECTIVE_RUNTIME_MANIFEST, semantic_is_raw=False)
    manifest = _json(raw, "bootstrap runtime manifest")
    if set(manifest) != {
        "schema_version",
        "runtime_id",
        "runtime_version",
        "runtime_root",
        "runtime_root_mode",
        "runtime_root_uid",
        "runtime_root_gid",
        "effective_interpreter_locator",
        "effective_interpreter_artifact_digest",
        "runtime_closure",
        "platform_binding",
        "tree_denominator",
        "trust_boundary",
        "formal_authority",
        "positive_assurance_allowed",
        "manifest_digest",
    }:
        raise OuterLaunchError("bootstrap runtime manifest fields mismatch")
    if (
        manifest.get("schema_version")
        != "semantic-guard-u10-bootstrap-runtime-manifest/v1"
        or manifest.get("manifest_digest") != _sealed(manifest, "manifest_digest")
        or manifest.get("manifest_digest") != reference.get("semantic_digest")
        or manifest.get("formal_authority") != "none"
        or manifest.get("positive_assurance_allowed") is not False
        or manifest.get("trust_boundary")
        != {
            "covered": "root_owned_runtime_tree_resistant_to_non_root_tampering",
            "not_claimed": "root_or_os_compromise_resistance",
        }
    ):
        raise OuterLaunchError("bootstrap runtime manifest contract mismatch")
    uname = os.uname()
    system_version_path = Path(
        "/System/Library/CoreServices/SystemVersion.plist"
    )
    system_version_raw = _read_root_file(system_version_path)
    try:
        system_version = plistlib.loads(system_version_raw)
    except plistlib.InvalidFileException as exc:
        raise OuterLaunchError("SystemVersion.plist is unreadable") from exc
    expected_platform = {
        "system": uname.sysname,
        "release": uname.release,
        "kernel_version": uname.version,
        "machine": uname.machine,
        "os_build_artifact": {
            "locator": str(system_version_path),
            "product_build_version": system_version.get("ProductBuildVersion"),
            "artifact_digest": _digest(system_version_raw),
        },
        "binding_profile": (
            "uname_kernel_and_system_version_artifact_exact/v2"
        ),
    }
    if manifest.get("platform_binding") != expected_platform:
        raise OuterLaunchError("bootstrap runtime platform mismatch")
    observed_version = ".".join(map(str, sys.version_info[:3]))
    runtime_closure = manifest.get("runtime_closure")
    if not isinstance(runtime_closure, dict):
        raise OuterLaunchError("bootstrap runtime closure missing")
    observed_closure = _probe_bootstrap_runtime(
        Path(str(manifest.get("effective_interpreter_locator", "")))
    )
    if runtime_closure != observed_closure:
        raise OuterLaunchError("bootstrap runtime execution closure mismatch")
    derived_root = _derive_runtime_root(observed_closure)
    if (
        manifest.get("runtime_version") != observed_version
        or observed_closure.get("runtime_version") != observed_version
    ):
        raise OuterLaunchError("bootstrap runtime version mismatch")
    root = Path(str(manifest.get("runtime_root", "")))
    interpreter = Path(str(manifest.get("effective_interpreter_locator", "")))
    effective_ref = platform_contract["effective_python_ref"]
    if (
        not root.is_absolute()
        or root != Path(os.path.normpath(str(root)))
        or Path(os.path.realpath(root)) != root
        or not interpreter.is_absolute()
        or interpreter != Path(os.path.normpath(str(interpreter)))
        or Path(os.path.realpath(interpreter)) != interpreter
        or Path(str(effective_ref.get("locator"))) != interpreter
        or Path(str(effective_ref.get("resolved_locator"))) != interpreter
        or Path(os.path.realpath(sys.executable)) != interpreter
        or root != derived_root
    ):
        raise OuterLaunchError("bootstrap runtime interpreter mismatch")
    try:
        interpreter.relative_to(root)
    except ValueError as exc:
        raise OuterLaunchError("bootstrap interpreter escaped runtime root") from exc
    _validate_ancestors(root, include_leaf=True)
    root_observed = root.lstat()
    if (
        manifest.get("runtime_root_uid") != root_observed.st_uid
        or manifest.get("runtime_root_gid") != root_observed.st_gid
        or manifest.get("runtime_root_mode")
        != stat.S_IMODE(root_observed.st_mode)
    ):
        raise OuterLaunchError("bootstrap runtime root binding mismatch")
    entries = _host_runtime_tree_entries(root)
    denominator = manifest.get("tree_denominator")
    if (
        not isinstance(denominator, dict)
        or set(denominator) != {"status", "entry_count", "entries", "tree_digest"}
        or denominator.get("status") != "closed"
        or denominator.get("entry_count") != len(entries)
        or denominator.get("entries") != entries
        or denominator.get("tree_digest") != _digest(_canonical({"entries": entries}))
    ):
        raise OuterLaunchError("bootstrap runtime denominator mismatch")
    interpreter_raw = _read_root_file(interpreter)
    if (
        manifest.get("effective_interpreter_artifact_digest")
        != _digest(interpreter_raw)
        or effective_ref.get("artifact_digest") != _digest(interpreter_raw)
    ):
        raise OuterLaunchError("bootstrap runtime interpreter digest mismatch")
    _validate_current_process_runtime_closure(runtime_closure, root, interpreter)
    return manifest


def _tree_records(root: Path, excluded: frozenset[Path]) -> tuple[list[dict], set[Path]]:
    records: list[dict] = []
    regular: set[Path] = set()
    for raw_directory, directories, files in os.walk(
        root, topdown=True, followlinks=False
    ):
        base = Path(raw_directory)
        directories.sort()
        files.sort()
        for name in (*directories, *files):
            path = base / name
            if path in excluded:
                continue
            observed = path.lstat()
            _assert_no_extended_acl(path)
            if (
                stat.S_ISLNK(observed.st_mode)
                or observed.st_uid != 0
                or observed.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
            ):
                raise OuterLaunchError(f"mutable snapshot path: {path}")
            relative = path.relative_to(root).as_posix()
            if stat.S_ISDIR(observed.st_mode):
                records.append(
                    {"path": relative, "kind": "directory", "mode": stat.S_IMODE(observed.st_mode), "uid": observed.st_uid, "gid": observed.st_gid}
                )
            elif stat.S_ISREG(observed.st_mode):
                if observed.st_nlink != 1:
                    raise OuterLaunchError(f"hard-linked snapshot file: {path}")
                raw = _read_root_file(path)
                regular.add(path)
                records.append(
                    {"path": relative, "kind": "file", "mode": stat.S_IMODE(observed.st_mode), "uid": observed.st_uid, "gid": observed.st_gid, "size": observed.st_size, "digest": _digest(raw)}
                )
            else:
                raise OuterLaunchError(f"special snapshot path: {path}")
    return records, regular


def _validate_store_activation_basis(
    store: dict[str, Any], authorization: dict[str, Any]
) -> dict[str, Any]:
    reference = authorization.get("store_activation_basis_ref")
    if not _is_root_artifact_ref(reference):
        raise OuterLaunchError("store activation basis reference invalid")
    snapshot_authorization_ref: dict[str, Any] | None = None
    path = Path(str(reference["locator"]))
    if path.parent != STORE_ACTIVATION_BASIS_ROOT:
        raise OuterLaunchError("store activation basis outside fixed root")
    raw = _read_root_file(path, exact_mode=0o444)
    basis = _json(raw, "store activation basis")
    if isinstance(basis.get("snapshot_activation_authorization_ref"), dict):
        snapshot_authorization_ref = basis[
            "snapshot_activation_authorization_ref"
        ]
    transition_digest = _store_activation_transition_digest(basis)
    content = basis.get("store_content")
    entry = (
        content.get("entries", {}).get(basis.get("entry_id"))
        if isinstance(content, dict)
        else None
    )
    manifest_binding = (
        entry.get("snapshot_manifest_binding")
        if isinstance(entry, dict)
        else None
    )
    signing_key = content.get("signing_key") if isinstance(content, dict) else None
    signing_key_ref = basis.get("signing_key_ref")
    signing_key_selector_ref = basis.get("signing_key_selector_ref")
    if (
        set(basis) != STORE_ACTIVATION_BASIS_FIELDS
        or basis.get("schema_version")
        != "semantic-guard-u10-store-activation-basis/v2"
        or basis.get("basis_version") != "2.0.0"
        or basis.get("record_kind")
        != "exact_store_activation_basis_candidate"
        or basis.get("basis_digest") != _sealed(basis, "basis_digest")
        or reference.get("artifact_digest") != _digest(raw)
        or reference.get("semantic_digest") != basis.get("basis_digest")
        or reference.get("record_id") != basis.get("basis_id")
        or not isinstance(snapshot_authorization_ref, dict)
        or path.name
        != f"{snapshot_authorization_ref.get('record_id')}.store-basis.json"
        or not _is_root_artifact_ref(snapshot_authorization_ref)
        or Path(str(snapshot_authorization_ref.get("locator"))).parent
        != AUTHORIZATION_ROOT
        or not isinstance(content, dict)
        or content != _store_activation_content(store)
        or basis.get("store_activation_basis_digest")
        != _digest(_canonical(content))
        or basis.get("store_activation_basis_digest")
        != store.get("store_activation_basis_digest")
        or basis.get("store_transition_digest") != transition_digest
        or basis.get("basis_id")
        != f"store-basis.{transition_digest['value']}"
        or content.get("store_revision_id")
        != f"revision.u10.{transition_digest['value']}"
        or not isinstance(manifest_binding, dict)
        or manifest_binding.get("locator")
        != basis.get("snapshot_manifest_ref", {}).get("locator")
        or manifest_binding.get("artifact_digest")
        != basis.get("snapshot_manifest_ref", {}).get("artifact_digest")
        or manifest_binding.get("manifest_digest")
        != basis.get("snapshot_manifest_ref", {}).get("semantic_digest")
        or not isinstance(signing_key, dict)
        or not _is_key_public_metadata_ref_v2(signing_key_ref)
        or not _is_key_selector_ref_v2(signing_key_selector_ref)
        or signing_key.get("key_id") != signing_key_ref.get("key_id")
        or not _is_publisher_contract_binding(
            basis.get("publisher_contract_binding")
        )
        or not _is_rfc3339_datetime(basis.get("prepared_at"))
        or basis.get("publication_state") != "not_published"
        or basis.get("formal_authority") != "none"
        or basis.get("positive_assurance_allowed") is not False
        or authorization.get("prior_store_ref")
        != basis.get("prior_store_ref")
        or authorization.get("prior_revocation_ref")
        != basis.get("prior_revocation_ref")
    ):
        raise OuterLaunchError("store activation basis mismatch")
    recorded_at = _parse_rfc3339_datetime(authorization.get("recorded_at"))
    prepared_at = _parse_rfc3339_datetime(basis.get("prepared_at"))
    if (
        recorded_at is None
        or prepared_at is None
        or prepared_at > recorded_at
    ):
        raise OuterLaunchError("store activation basis chronology mismatch")
    return basis


def _validate_authorization(
    store: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    reference = store.get("activation_authorization_ref")
    if not isinstance(reference, dict):
        raise OuterLaunchError("activation authorization missing")
    record_id = str(reference.get("record_id", ""))
    path = AUTHORIZATION_ROOT / f"{record_id}.json"
    raw = _verify_root_ref(reference, path, semantic_is_raw=False)
    value = _json(raw, "activation authorization")
    if (
        value.get("schema_version")
        != "semantic-guard-u10-store-activation-authorization/v1"
        or value.get("authorization_id") != record_id
        or value.get("human_decision") != "accept"
        or value.get("decision_owner") != "human"
        or value.get("store_id") != store.get("store_id")
        or value.get("store_revision_id") != store.get("store_revision_id")
        or value.get("store_version") != store.get("store_version")
        or value.get("store_activation_basis_digest")
        != store.get("store_activation_basis_digest")
        or value.get("authorized_operation")
        != "publish_exact_active_store_revision"
        or value.get("u4_principal_authenticity") != "unresolved"
        or value.get("positive_assurance_allowed") is not False
        or not _is_stable_id(value.get("authorization_id"))
        or not _has_valid_transition_context(value)
        or value.get("authorization_digest") != _sealed(value, "authorization_digest")
        or value.get("authorization_digest") != reference.get("semantic_digest")
    ):
        raise OuterLaunchError("activation authorization mismatch")
    return value, _validate_store_activation_basis(store, value)


def _is_activation_authorization_consumption(value: dict[str, Any]) -> bool:
    return (
        set(value) == STORE_ACTIVATION_CONSUMPTION_FIELDS
        and value.get("schema_version")
        == "semantic-guard-u10-store-activation-authorization-consumption/v1"
        and _is_stable_id(value.get("consumption_id"))
        and value.get("record_kind") == "activation_authorization_consumption"
        and value.get("public_operation") == "activate-store"
        and value.get("public_identifier") == value.get("authorization_id")
        and _is_stable_id(value.get("authorization_id"))
        and _is_digest(value.get("authorization_digest"))
        and _is_root_artifact_ref(value.get("store_activation_basis_ref"))
        and _has_valid_transition_context(value)
        and _is_store_transition_ref(value.get("target_store_ref"))
        and _is_publisher_contract_binding(
            value.get("publisher_contract_binding")
        )
        and _is_rfc3339_datetime(value.get("reserved_at"))
        and value.get("publication_occurred") is False
        and value.get("formal_authority") == "none"
        and value.get("positive_assurance_allowed") is False
        and _is_digest(value.get("consumption_digest"))
    )


def _is_activation_transition_receipt(value: dict[str, Any]) -> bool:
    return (
        set(value) == STORE_ACTIVATION_RECEIPT_FIELDS
        and value.get("schema_version")
        == "semantic-guard-u10-store-activation-transition-receipt/v2"
        and _is_stable_id(value.get("receipt_id"))
        and value.get("record_kind") == "activation_transition_occurrence"
        and value.get("public_operation") == "activate-store"
        and value.get("public_identifier") == value.get("authorization_id")
        and _is_stable_id(value.get("authorization_id"))
        and _is_digest(value.get("authorization_digest"))
        and _is_digest(value.get("consumption_digest"))
        and _is_root_artifact_ref(value.get("store_activation_basis_ref"))
        and _has_valid_transition_context(value)
        and _is_store_transition_ref(value.get("activated_store_ref"))
        and _is_publisher_contract_binding(
            value.get("publisher_contract_binding")
        )
        and _is_rfc3339_datetime(value.get("publication_not_before"))
        and _is_rfc3339_datetime(value.get("publication_observed_at"))
        and _is_rfc3339_datetime(value.get("receipt_recorded_at"))
        and value.get("formal_authority") == "none"
        and value.get("positive_assurance_allowed") is False
        and _is_digest(value.get("receipt_digest"))
    )


def _validate_activation_transition_records_value(
    store: dict[str, Any],
    store_raw: bytes,
    authorization: dict[str, Any],
    consumption: dict[str, Any],
    receipt: dict[str, Any],
) -> None:
    if not _has_valid_transition_context(authorization):
        raise OuterLaunchError("activation authorization transition mismatch")
    if not _is_activation_authorization_consumption(consumption):
        raise OuterLaunchError("activation authorization consumption contract mismatch")
    if not _is_activation_transition_receipt(receipt):
        raise OuterLaunchError("activation transition receipt contract mismatch")
    if consumption.get("consumption_digest") != _sealed(
        consumption,
        "consumption_digest",
    ):
        raise OuterLaunchError("activation authorization consumption digest mismatch")
    if receipt.get("receipt_digest") != _sealed(receipt, "receipt_digest"):
        raise OuterLaunchError("activation transition receipt digest mismatch")
    recorded_at = _parse_rfc3339_datetime(authorization.get("recorded_at"))
    reserved_at = _parse_rfc3339_datetime(consumption.get("reserved_at"))
    publication_not_before = _parse_rfc3339_datetime(
        receipt.get("publication_not_before")
    )
    publication_observed_at = _parse_rfc3339_datetime(
        receipt.get("publication_observed_at")
    )
    receipt_recorded_at = _parse_rfc3339_datetime(
        receipt.get("receipt_recorded_at")
    )
    # This is record ordering, not a claim that any external clock is authentic.
    if (
        recorded_at is None
        or reserved_at is None
        or publication_not_before is None
        or publication_observed_at is None
        or receipt_recorded_at is None
        or publication_not_before != reserved_at
        or not recorded_at <= reserved_at <= publication_observed_at
        or publication_observed_at > receipt_recorded_at
    ):
        raise OuterLaunchError("activation transition record chronology mismatch")
    authorization_id = authorization.get("authorization_id")
    exact_store_ref = _store_transition_ref(store, store_raw)
    if (
        consumption.get("consumption_id") != f"consumption.{authorization_id}"
        or consumption.get("public_identifier") != authorization_id
        or consumption.get("authorization_id") != authorization_id
        or consumption.get("authorization_digest")
        != authorization.get("authorization_digest")
        or consumption.get("store_activation_basis_ref")
        != authorization.get("store_activation_basis_ref")
        or consumption.get("transition_kind") != authorization.get("transition_kind")
        or consumption.get("prior_store_ref") != authorization.get("prior_store_ref")
        or consumption.get("prior_revocation_ref")
        != authorization.get("prior_revocation_ref")
        or consumption.get("target_store_ref") != exact_store_ref
    ):
        raise OuterLaunchError("activation authorization consumption context mismatch")
    if (
        receipt.get("receipt_id") != f"receipt.{authorization_id}"
        or receipt.get("public_identifier") != authorization_id
        or receipt.get("authorization_id") != authorization_id
        or receipt.get("authorization_digest")
        != authorization.get("authorization_digest")
        or receipt.get("consumption_digest") != consumption.get("consumption_digest")
        or receipt.get("store_activation_basis_ref")
        != authorization.get("store_activation_basis_ref")
        or receipt.get("transition_kind") != authorization.get("transition_kind")
        or receipt.get("prior_store_ref") != authorization.get("prior_store_ref")
        or receipt.get("prior_revocation_ref")
        != authorization.get("prior_revocation_ref")
        or receipt.get("activated_store_ref") != exact_store_ref
        or receipt.get("publisher_contract_binding")
        != consumption.get("publisher_contract_binding")
    ):
        raise OuterLaunchError("activation transition receipt context mismatch")


def _read_activation_ledger_record(path: Path, label: str) -> dict[str, Any]:
    raw = _read_root_file(path, exact_mode=0o444)
    observed = path.lstat()
    if (
        not stat.S_ISREG(observed.st_mode)
        or observed.st_uid != 0
        or observed.st_gid != 0
        or stat.S_IMODE(observed.st_mode) != 0o444
        or observed.st_nlink != 1
    ):
        raise OuterLaunchError(f"untrusted {label}")
    return _json(raw, label)


def _validate_activation_ledger_directory() -> None:
    _validate_ancestors(STORE_ACTIVATION_LEDGER_ROOT, include_leaf=True)
    observed = STORE_ACTIVATION_LEDGER_ROOT.lstat()
    if (
        observed.st_uid != 0
        or observed.st_gid != 0
        or stat.S_IMODE(observed.st_mode) != 0o755
    ):
        raise OuterLaunchError("untrusted store activation ledger directory")


def _validate_activation_transition_records(
    store: dict[str, Any],
    store_raw: bytes,
    authorization: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    selector = store.get("current_selector")
    if (
        not isinstance(selector, dict)
        or selector.get("activation_ledger_path") != str(STORE_ACTIVATION_LEDGER_ROOT)
        or selector.get("activation_ledger_policy") != STORE_ACTIVATION_LEDGER_POLICY
        or selector.get("activation_ledger_retention_policy")
        != STORE_ACTIVATION_LEDGER_RETENTION_POLICY
    ):
        raise OuterLaunchError("store activation ledger selector mismatch")
    _validate_activation_ledger_directory()
    authorization_id = authorization.get("authorization_id")
    if not _is_stable_id(authorization_id):
        raise OuterLaunchError("activation authorization id mismatch")
    consumption = _read_activation_ledger_record(
        STORE_ACTIVATION_LEDGER_ROOT / f"{authorization_id}.consumption.json",
        "activation authorization consumption",
    )
    receipt = _read_activation_ledger_record(
        STORE_ACTIVATION_LEDGER_ROOT / f"{authorization_id}.receipt.json",
        "activation transition receipt",
    )
    _validate_activation_transition_records_value(
        store,
        store_raw,
        authorization,
        consumption,
        receipt,
    )
    return consumption, receipt


def _activation_receipt_ref(receipt: dict[str, Any]) -> dict[str, Any]:
    return {
        "receipt_id": receipt.get("receipt_id"),
        "receipt_digest": receipt.get("receipt_digest"),
        "publication_observed_at": receipt.get("publication_observed_at"),
        "receipt_recorded_at": receipt.get("receipt_recorded_at"),
    }


def _is_activation_receipt_ref(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and set(value)
        == {
            "receipt_id",
            "receipt_digest",
            "publication_observed_at",
            "receipt_recorded_at",
        }
        and _is_stable_id(value.get("receipt_id"))
        and _is_digest(value.get("receipt_digest"))
        and _is_rfc3339_datetime(value.get("publication_observed_at"))
        and _is_rfc3339_datetime(value.get("receipt_recorded_at"))
    )


def _read_exact_root_record(path: Path, label: str) -> bytes:
    raw = _read_root_file(path, exact_mode=0o444)
    observed = path.lstat()
    if (
        not stat.S_ISREG(observed.st_mode)
        or observed.st_uid != 0
        or observed.st_gid != 0
        or stat.S_IMODE(observed.st_mode) != 0o444
        or observed.st_nlink != 1
    ):
        raise OuterLaunchError(f"untrusted {label}: {path}")
    return raw


def _validate_revocation_decision_shape(value: dict[str, Any]) -> None:
    if (
        set(value) != STORE_REVOCATION_FIELDS
        or value.get("schema_version")
        != "semantic-guard-u10-store-revocation-record/v1"
        or not _is_stable_id(value.get("revocation_id"))
        or re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9._-]{0,255}",
            str(value.get("revocation_id", "")),
        )
        is None
        or not isinstance(value.get("revocation_version"), str)
        or not 1 <= len(value["revocation_version"]) <= 128
        or value.get("record_kind") != "store_revocation"
        or value.get("human_decision") != "accept"
        or value.get("decision_owner") != "human"
        or not _is_stable_id(value.get("target_store_id"))
        or not _is_stable_id(value.get("target_store_revision_id"))
        or not isinstance(value.get("target_store_version"), str)
        or not _is_digest(value.get("target_store_activation_basis_digest"))
        or not _is_digest(value.get("target_store_artifact_digest"))
        or not _is_digest(value.get("target_store_digest"))
        or not _is_activation_receipt_ref(
            value.get("target_activation_receipt_ref")
        )
        or value.get("revoked_operation") != "revoke_exact_store_revision"
        or value.get("decision_entry_profile")
        != "fixed_root_authorization_record/v1"
        or not _is_rfc3339_datetime(value.get("recorded_at"))
        or not isinstance(value.get("reason"), str)
        or not 1 <= len(value["reason"]) <= 4096
        or value.get("u4_principal_authenticity") != "unresolved"
        or value.get("authority_scope") != "u10_store_revocation_only"
        or value.get("formal_authority")
        != "human_revocation_decision_only"
        or value.get("positive_assurance_allowed") is not False
        or not _is_digest(value.get("revocation_digest"))
        or value.get("revocation_digest") != _sealed(value, "revocation_digest")
    ):
        raise OuterLaunchError("store revocation decision contract mismatch")


def _validate_current_revocation_state(
    store: dict[str, Any],
    store_raw: bytes,
    activation_receipt: dict[str, Any],
) -> None:
    selector = store.get("current_selector")
    if (
        not isinstance(selector, dict)
        or selector.get("revocation_selector_path") != str(REVOCATION_SELECTOR)
        or selector.get("revocation_history_path") != str(REVOCATION_ROOT)
        or selector.get("revocation_ledger_path") != str(REVOCATION_LEDGER_ROOT)
        or selector.get("revocation_ledger_policy") != REVOCATION_LEDGER_POLICY
        or selector.get("revocation_ledger_retention_policy")
        != REVOCATION_LEDGER_RETENTION_POLICY
        or selector.get("revocation_decision_root_path")
        != str(AUTHORIZATION_ROOT)
        or selector.get("revocation_decision_entry_policy")
        != "fixed_root_record_id_resolution_no_caller_raw/v1"
        or selector.get("revocation_publication_policy")
        != "decision_consumption_history_selector_interval_receipt_recovery/v4"
    ):
        raise OuterLaunchError("store revocation publication contract mismatch")
    for root, label in (
        (REVOCATION_ROOT, "revocation history"),
        (REVOCATION_LEDGER_ROOT, "revocation ledger"),
    ):
        _validate_ancestors(root, include_leaf=True)
        observed = root.lstat()
        if (
            observed.st_uid != 0
            or observed.st_gid != 0
            or stat.S_IMODE(observed.st_mode) != 0o755
        ):
            raise OuterLaunchError(f"untrusted {label} directory")

    exact_store_ref = _store_transition_ref(store, store_raw)
    exact_activation_receipt_ref = _activation_receipt_ref(activation_receipt)
    matches: list[tuple[dict[str, Any], bytes, Path]] = []
    try:
        history_paths = sorted(REVOCATION_ROOT.iterdir(), key=lambda item: item.name)
    except OSError as exc:
        raise OuterLaunchError("revocation history unavailable") from exc
    for path in history_paths:
        if re.fullmatch(r"[0-9a-f]{64}\.json", path.name) is None:
            raise OuterLaunchError("revocation history denominator mismatch")
        raw = _read_exact_root_record(path, "revocation history record")
        if path.name != f"{_digest(raw)['value']}.json":
            raise OuterLaunchError("revocation history artifact mismatch")
        value = _json(raw, "revocation history record")
        _validate_revocation_decision_shape(value)
        if (
            value.get("target_store_id") == store.get("store_id")
            and value.get("target_store_revision_id")
            == store.get("store_revision_id")
            and value.get("target_store_version") == store.get("store_version")
        ):
            if (
                value.get("target_store_activation_basis_digest")
                != store.get("store_activation_basis_digest")
                or value.get("target_store_artifact_digest") != _digest(store_raw)
                or value.get("target_store_digest") != store.get("store_digest")
                or value.get("target_activation_receipt_ref")
                != exact_activation_receipt_ref
            ):
                raise OuterLaunchError("store revocation target mismatch")
            matches.append((value, raw, path))
    if len(matches) > 1:
        raise OuterLaunchError("multiple revocations for current store revision")

    selector_present = REVOCATION_SELECTOR.exists() or REVOCATION_SELECTOR.is_symlink()
    selector_raw = (
        _read_exact_root_record(REVOCATION_SELECTOR, "revocation selector")
        if selector_present
        else None
    )
    if not matches and selector_raw is None:
        return
    if not matches or selector_raw is None:
        raise OuterLaunchError("revocation publication incomplete")
    revocation, revocation_raw, history_path = matches[0]
    if selector_raw != revocation_raw:
        raise OuterLaunchError("revocation selector history mismatch")
    decision_id = str(revocation["revocation_id"])
    decision_raw = _read_exact_root_record(
        AUTHORIZATION_ROOT / f"{decision_id}.json",
        "root revocation decision",
    )
    if decision_raw != revocation_raw:
        raise OuterLaunchError("root revocation decision history mismatch")

    consumption_raw = _read_exact_root_record(
        REVOCATION_LEDGER_ROOT / f"{decision_id}.consumption.json",
        "revocation authorization consumption",
    )
    consumption = _json(consumption_raw, "revocation authorization consumption")
    if (
        set(consumption) != STORE_REVOCATION_CONSUMPTION_FIELDS
        or consumption.get("schema_version")
        != "semantic-guard-u10-store-revocation-authorization-consumption/v1"
        or consumption.get("consumption_id") != f"consumption.{decision_id}"
        or consumption.get("record_kind")
        != "revocation_authorization_consumption"
        or consumption.get("revocation_id") != decision_id
        or consumption.get("revocation_digest")
        != revocation.get("revocation_digest")
        or consumption.get("target_store_ref") != exact_store_ref
        or consumption.get("target_activation_receipt_ref")
        != exact_activation_receipt_ref
        or not _is_publisher_contract_binding(
            consumption.get("publisher_contract_binding")
        )
        or not _is_rfc3339_datetime(consumption.get("consumed_at"))
        or consumption.get("publication_occurred") is not False
        or consumption.get("formal_authority") != "none"
        or consumption.get("positive_assurance_allowed") is not False
        or consumption.get("consumption_digest")
        != _sealed(consumption, "consumption_digest")
    ):
        raise OuterLaunchError("revocation consumption contract mismatch")

    receipt_raw = _read_exact_root_record(
        REVOCATION_LEDGER_ROOT / f"{decision_id}.receipt.json",
        "revocation publication receipt",
    )
    receipt = _json(receipt_raw, "revocation publication receipt")
    expected_history_ref = {
        "locator": str(history_path),
        "artifact_digest": _digest(revocation_raw),
    }
    if (
        set(receipt) != STORE_REVOCATION_RECEIPT_FIELDS
        or receipt.get("schema_version")
        != "semantic-guard-u10-store-revocation-publication-receipt/v2"
        or receipt.get("receipt_id") != f"receipt.{decision_id}"
        or receipt.get("record_kind") != "revocation_publication_occurrence"
        or receipt.get("publisher_operation_id")
        != "semantic-guard.u10.publish-store-revocation.v1"
        or receipt.get("publisher_euid") != 0
        or receipt.get("revocation_id") != decision_id
        or receipt.get("revocation_digest") != revocation.get("revocation_digest")
        or receipt.get("consumption_digest")
        != consumption.get("consumption_digest")
        or receipt.get("target_store_ref") != exact_store_ref
        or receipt.get("target_activation_receipt_ref")
        != exact_activation_receipt_ref
        or receipt.get("history_ref") != expected_history_ref
        or not _is_publisher_contract_binding(
            receipt.get("publisher_contract_binding")
        )
        or receipt.get("publisher_contract_binding")
        != consumption.get("publisher_contract_binding")
        or receipt.get("selector_path") != str(REVOCATION_SELECTOR)
        or not _is_rfc3339_datetime(receipt.get("publication_not_before"))
        or not _is_rfc3339_datetime(receipt.get("publication_observed_at"))
        or not _is_rfc3339_datetime(receipt.get("receipt_recorded_at"))
        or receipt.get("formal_authority") != "none"
        or receipt.get("positive_assurance_allowed") is not False
        or receipt.get("receipt_digest") != _sealed(receipt, "receipt_digest")
    ):
        raise OuterLaunchError("revocation publication receipt mismatch")
    recorded_at = _parse_rfc3339_datetime(revocation.get("recorded_at"))
    consumed_at = _parse_rfc3339_datetime(consumption.get("consumed_at"))
    publication_not_before = _parse_rfc3339_datetime(
        receipt.get("publication_not_before")
    )
    publication_observed_at = _parse_rfc3339_datetime(
        receipt.get("publication_observed_at")
    )
    receipt_recorded_at = _parse_rfc3339_datetime(
        receipt.get("receipt_recorded_at")
    )
    activation_receipt_recorded_at = _parse_rfc3339_datetime(
        activation_receipt.get("receipt_recorded_at")
    )
    if (
        recorded_at is None
        or consumed_at is None
        or publication_not_before is None
        or publication_observed_at is None
        or receipt_recorded_at is None
        or activation_receipt_recorded_at is None
        or publication_not_before != consumed_at
        or not recorded_at <= consumed_at <= publication_observed_at
        or publication_observed_at > receipt_recorded_at
        or recorded_at < activation_receipt_recorded_at
    ):
        raise OuterLaunchError("revocation publication chronology mismatch")
    raise OuterLaunchError("current store is revoked")


def _read_compact_root_ref(
    reference: dict[str, Any],
    *,
    parent: Path,
) -> tuple[dict[str, Any], bytes]:
    record_id = str(reference.get("record_id", ""))
    path = Path(str(reference.get("locator", "")))
    if path.parent != parent or path.name != f"{record_id}.json" or not record_id:
        raise OuterLaunchError(f"root record path mismatch: {path}")
    raw = _read_root_file(path)
    if reference.get("artifact_digest") != _digest(raw):
        raise OuterLaunchError(f"root record artifact mismatch: {path}")
    value = _json(raw, path.name)
    return value, raw


def _validate_snapshot_adoption(
    manifest: dict[str, Any],
    entry_id: str,
    *,
    projection_receipt_ref: dict[str, Any],
    environment_adoption_ref: dict[str, Any],
) -> dict[str, Any]:
    reference = manifest.get("snapshot_adoption_authorization_ref")
    if not isinstance(reference, dict):
        raise OuterLaunchError("snapshot adoption authorization missing")
    value, raw = _read_compact_root_ref(
        reference,
        parent=AUTHORIZATION_ROOT,
    )
    if (
        raw != _canonical(value) + b"\n"
        or
        value.get("schema_version")
        != "semantic-guard-u10-snapshot-adoption-authorization/v1"
        or value.get("authorization_id") != reference.get("record_id")
        or value.get("human_decision") != "accept"
        or value.get("decision_owner") != "human"
        or value.get("snapshot_id") != manifest.get("snapshot_id")
        or value.get("snapshot_version") != manifest.get("snapshot_version")
        or value.get("snapshot_basis_digest")
        != manifest.get("snapshot_basis_digest")
        or value.get("entry_id") != entry_id
        or value.get("projection_receipt_ref") != projection_receipt_ref
        or value.get("environment_adoption_ref") != environment_adoption_ref
        or value.get("authorized_operation") != "adopt_exact_immutable_snapshot"
        or value.get("u4_principal_authenticity") != "unresolved"
        or value.get("positive_assurance_allowed") is not False
        or value.get("authorization_digest") != _sealed(value, "authorization_digest")
        or value.get("authorization_digest") != reference.get("semantic_digest")
    ):
        raise OuterLaunchError("snapshot adoption authorization mismatch")
    return value


def _validate_snapshot_activation(
    manifest: dict[str, Any],
    entry_id: str,
    environment_adoption: dict[str, Any],
    snapshot_adoption: dict[str, Any],
    manifest_raw: bytes,
) -> dict[str, dict[str, Any]]:
    reference = manifest.get("activation_ref")
    if not isinstance(reference, dict):
        raise OuterLaunchError("snapshot activation basis missing")
    basis, _raw = _read_compact_root_ref(
        reference,
        parent=SNAPSHOT_ACTIVATION_ROOT,
    )
    verification = manifest.get("immutability_verification")
    if not isinstance(verification, dict):
        raise OuterLaunchError("snapshot immutability verification missing")
    if (
        basis.get("schema_version")
        != "semantic-guard-u10-snapshot-activation-basis/v1"
        or basis.get("activation_basis_id") != reference.get("record_id")
        or basis.get("snapshot_id") != manifest.get("snapshot_id")
        or basis.get("snapshot_version") != manifest.get("snapshot_version")
        or basis.get("snapshot_basis_digest")
        != manifest.get("snapshot_basis_digest")
        or basis.get("entry_id") != entry_id
        or basis.get("adoption_id")
        != environment_adoption.get("adoption_id")
        or basis.get("adoption_version")
        != environment_adoption.get("adoption_version")
        or basis.get("adoption_digest")
        != environment_adoption.get("adoption_digest")
        or basis.get("environment_adoption_ref")
        != manifest.get("environment_adoption_ref")
        or basis.get("projection_receipt_ref")
        != environment_adoption.get("projection_receipt_ref")
        or basis.get("snapshot_adoption_authorization_ref")
        != manifest.get("snapshot_adoption_authorization_ref")
        or basis.get("immutability_verified_at") != verification.get("verified_at")
        or basis.get("preparation_status")
        != "prepared_for_manifest_publication"
        or basis.get("formal_authority") != "none"
        or basis.get("positive_assurance_allowed") is not False
        or basis.get("activation_basis_digest")
        != _sealed(basis, "activation_basis_digest")
        or basis.get("activation_basis_digest")
        != reference.get("semantic_digest")
    ):
        raise OuterLaunchError("snapshot activation basis mismatch")

    authorization_id = str(snapshot_adoption.get("authorization_id", ""))
    consumption_path = (
        SNAPSHOT_ACTIVATION_LEDGER_ROOT / f"{authorization_id}.consumption.json"
    )
    receipt_path = (
        SNAPSHOT_ACTIVATION_LEDGER_ROOT / f"{authorization_id}.receipt.json"
    )
    consumption_raw = _read_root_file(consumption_path, exact_mode=0o400)
    receipt_raw = _read_root_file(receipt_path, exact_mode=0o400)
    consumption = _json(consumption_raw, "snapshot activation consumption")
    receipt = _json(receipt_raw, "snapshot activation receipt")
    authorization_ref = manifest["snapshot_adoption_authorization_ref"]
    expected_manifest_ref = {
        "record_id": manifest["snapshot_id"],
        "locator": str(
            Path(str(manifest["root_storage"]["snapshot_path"])) / MANIFEST_NAME
        ),
        "artifact_digest": _digest(manifest_raw),
        "semantic_digest": manifest["manifest_digest"],
    }
    store_basis_ref = receipt.get("store_activation_basis_ref")
    if not _is_root_artifact_ref(store_basis_ref):
        raise OuterLaunchError("snapshot store basis reference invalid")
    store_basis_path = Path(str(store_basis_ref["locator"]))
    if (
        store_basis_path.parent != STORE_ACTIVATION_BASIS_ROOT
        or store_basis_path.name
        != f"{authorization_id}.store-basis.json"
    ):
        raise OuterLaunchError("snapshot store basis path mismatch")
    store_basis_raw = _read_root_file(store_basis_path, exact_mode=0o444)
    store_basis = _json(store_basis_raw, "snapshot store activation basis")
    store_transition_digest = _store_activation_transition_digest(store_basis)
    store_content = store_basis.get("store_content")
    store_entry = (
        store_content.get("entries", {}).get(entry_id)
        if isinstance(store_content, dict)
        else None
    )
    store_manifest_binding = (
        store_entry.get("snapshot_manifest_binding")
        if isinstance(store_entry, dict)
        else None
    )
    if (
        set(store_basis) != STORE_ACTIVATION_BASIS_FIELDS
        or store_basis.get("schema_version")
        != "semantic-guard-u10-store-activation-basis/v2"
        or store_basis.get("basis_version") != "2.0.0"
        or store_basis.get("basis_digest")
        != _sealed(store_basis, "basis_digest")
        or store_basis_ref.get("record_id") != store_basis.get("basis_id")
        or store_basis_ref.get("artifact_digest") != _digest(store_basis_raw)
        or store_basis_ref.get("semantic_digest")
        != store_basis.get("basis_digest")
        or store_basis.get("snapshot_activation_authorization_ref")
        != authorization_ref
        or store_basis.get("snapshot_manifest_ref") != expected_manifest_ref
        or store_basis.get("entry_id") != entry_id
        or store_basis.get("store_transition_digest")
        != store_transition_digest
        or store_basis.get("basis_id")
        != f"store-basis.{store_transition_digest['value']}"
        or not isinstance(store_content, dict)
        or store_content.get("store_revision_id")
        != f"revision.u10.{store_transition_digest['value']}"
        or store_basis.get("store_activation_basis_digest")
        != _digest(_canonical(store_content))
        or not _is_key_public_metadata_ref_v2(
            store_basis.get("signing_key_ref")
        )
        or not _is_key_selector_ref_v2(
            store_basis.get("signing_key_selector_ref")
        )
        or not isinstance(store_manifest_binding, dict)
        or store_manifest_binding.get("locator")
        != expected_manifest_ref["locator"]
        or store_manifest_binding.get("artifact_digest")
        != expected_manifest_ref["artifact_digest"]
        or store_manifest_binding.get("manifest_digest")
        != expected_manifest_ref["semantic_digest"]
        or store_basis.get("publisher_contract_binding")
        != receipt.get("publisher_contract_binding")
        or not _is_rfc3339_datetime(store_basis.get("prepared_at"))
        or store_basis.get("publication_state") != "not_published"
        or store_basis.get("formal_authority") != "none"
        or store_basis.get("positive_assurance_allowed") is not False
    ):
        raise OuterLaunchError("snapshot store activation basis mismatch")
    if (
        consumption.get("schema_version")
        != "semantic-guard-u10-snapshot-activation-authorization-consumption/v1"
        or consumption.get("record_kind")
        != "snapshot_adoption_authorization_consumption"
        or consumption.get("public_operation") != "activate-snapshot"
        or consumption.get("public_identifier") != authorization_id
        or consumption.get("authorization_ref") != authorization_ref
        or consumption.get("projection_receipt_ref")
        != environment_adoption.get("projection_receipt_ref")
        or consumption.get("environment_adoption_ref")
        != manifest.get("environment_adoption_ref")
        or consumption.get("snapshot_id") != manifest.get("snapshot_id")
        or consumption.get("snapshot_basis_digest")
        != manifest.get("snapshot_basis_digest")
        or consumption.get("manifest_publication_occurred") is not False
        or consumption.get("formal_authority") != "none"
        or consumption.get("positive_assurance_allowed") is not False
        or not _is_publisher_contract_binding(
            consumption.get("publisher_contract_binding")
        )
        or consumption.get("consumption_digest")
        != _sealed(consumption, "consumption_digest")
        or receipt.get("schema_version")
        != "semantic-guard-u10-snapshot-activation-publication-receipt/v1"
        or receipt.get("record_kind")
        != "active_snapshot_manifest_publication_occurrence"
        or receipt.get("public_operation") != "activate-snapshot"
        or receipt.get("public_identifier") != authorization_id
        or receipt.get("authorization_ref") != authorization_ref
        or receipt.get("consumption_ref")
        != {
            "consumption_id": consumption.get("consumption_id"),
            "consumption_digest": consumption.get("consumption_digest"),
        }
        or receipt.get("projection_receipt_ref")
        != environment_adoption.get("projection_receipt_ref")
        or receipt.get("environment_adoption_ref")
        != manifest.get("environment_adoption_ref")
        or receipt.get("activation_ref") != reference
        or receipt.get("snapshot_manifest_ref") != expected_manifest_ref
        or receipt.get("completion_scope")
        != "snapshot_manifest_and_exact_store_basis_candidate_published"
        or receipt.get("publisher_contract_binding")
        != consumption.get("publisher_contract_binding")
        or receipt.get("publication_occurred") is not True
        or receipt.get("formal_authority") != "none"
        or receipt.get("positive_assurance_allowed") is not False
        or receipt.get("receipt_digest") != _sealed(receipt, "receipt_digest")
    ):
        raise OuterLaunchError("snapshot activation occurrence mismatch")
    prepared_at = _parse_rfc3339_datetime(store_basis.get("prepared_at"))
    publication_observed_at = _parse_rfc3339_datetime(
        receipt.get("publication_observed_at")
    )
    if (
        prepared_at is None
        or publication_observed_at is None
        or prepared_at > publication_observed_at
    ):
        raise OuterLaunchError("snapshot store basis chronology mismatch")
    return {
        "basis": basis,
        "consumption": consumption,
        "receipt": receipt,
        "store_activation_basis": store_basis,
    }


def _validate_environment_adoption_artifact(
    *,
    manifest: dict[str, Any],
    snapshot: Path,
    entries: dict[str, Any],
    entry: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    reference = manifest.get("environment_adoption_ref")
    binding = entry.get("environment_adoption_binding")
    if not isinstance(reference, dict) or binding != reference:
        raise OuterLaunchError("environment adoption binding missing")
    value, _raw = _read_compact_root_ref(
        reference,
        parent=AUTHORIZATION_ROOT,
    )
    if (
        value.get("schema_version")
        != "semantic-guard-u10-snapshot-environment-adoption/v1"
        or value.get("adoption_id") != reference.get("record_id")
        or value.get("record_kind")
        != "snapshot_environment_adoption_decision"
        or value.get("human_decision") != "accept"
        or value.get("decision_owner") != "human"
        or value.get("authorized_operation")
        != "adopt_exact_projected_snapshot_environment"
        or value.get("decision_effect_scope")
        != "u10_exact_projected_snapshot_environment_use_gate_only"
        or value.get("u4_principal_authenticity") != "unresolved"
        or value.get("adoption_digest") != _sealed(value, "adoption_digest")
        or value.get("adoption_digest") != reference.get("semantic_digest")
        or value.get("formal_authority") != "none"
        or value.get("positive_assurance_allowed") is not False
    ):
        raise OuterLaunchError("environment adoption record mismatch")
    projection_ref = value.get("projection_receipt_ref")
    if not isinstance(projection_ref, dict):
        raise OuterLaunchError("snapshot projection receipt reference missing")
    projection_path = Path(str(projection_ref.get("locator", "")))
    if (
        projection_path.parent != SNAPSHOT_PROJECTION_LEDGER_ROOT
        or not projection_path.name.endswith(".receipt.json")
    ):
        raise OuterLaunchError("snapshot projection receipt path mismatch")
    projection_raw = _read_root_file(projection_path, exact_mode=0o400)
    if projection_ref.get("artifact_digest") != _digest(projection_raw):
        raise OuterLaunchError("snapshot projection receipt artifact mismatch")
    projection = _json(projection_raw, "snapshot projection receipt")
    authorization_id = str(projection.get("public_identifier", ""))
    consumption_path = (
        SNAPSHOT_PROJECTION_LEDGER_ROOT / f"{authorization_id}.consumption.json"
    )
    authorization_path = (
        SNAPSHOT_PROJECTION_LEDGER_ROOT / f"{authorization_id}.authorization.json"
    )
    consumption_raw = _read_root_file(consumption_path, exact_mode=0o400)
    authorization_raw = _read_root_file(authorization_path, exact_mode=0o400)
    consumption = _json(consumption_raw, "snapshot projection consumption")
    authorization = _json(authorization_raw, "snapshot projection authorization")
    authorization_ref = {
        "authorization_id": authorization_id,
        "artifact_digest": _digest(authorization_raw),
        "authorization_digest": authorization.get("authorization_digest"),
    }
    projected_basis = projection.get("projected_environment_basis")
    expected_snapshot_ref = {
        "snapshot_id": manifest.get("snapshot_id"),
        "snapshot_version": manifest.get("snapshot_version"),
        "snapshot_path": str(snapshot),
        "tree_digest": manifest.get("root_storage", {}).get("tree_digest"),
        "snapshot_basis_digest": manifest.get("snapshot_basis_digest"),
    }
    expected_source_ref = {
        key: manifest.get("eligibility_source_ref", {}).get(key)
        for key in (
            "source_id", "source_version", "lifecycle_state",
            "snapshot_artifact_ref", "source_digest",
        )
    }
    expected_profile_ref = {
        key: manifest.get("verification_profile_ref", {}).get(key)
        for key in (
            "profile_id", "profile_version", "snapshot_artifact_ref",
            "content_digest",
        )
    }
    environment_manifest_ref = manifest.get("environment_profile_ref", {})
    expected_environment_ref = {
        "environment_profile_id": environment_manifest_ref.get(
            "environment_profile_id"
        ),
        "environment_profile_version": environment_manifest_ref.get(
            "environment_profile_version"
        ),
        "lifecycle_state": "candidate",
        "snapshot_artifact_ref": environment_manifest_ref.get(
            "snapshot_artifact_ref"
        ),
        "basis_digest": environment_manifest_ref.get("basis_digest"),
    }
    if (
        projection.get("schema_version")
        != "semantic-guard-u10-snapshot-projection-receipt/v1"
        or projection.get("receipt_id") != projection_ref.get("record_id")
        or projection.get("receipt_digest") != _sealed(projection, "receipt_digest")
        or projection.get("receipt_digest") != projection_ref.get("semantic_digest")
        or projection.get("public_operation") != "project-snapshot"
        or projection_path.name != f"{authorization_id}.receipt.json"
        or projection.get("projection_occurred") is not True
        or projection.get("snapshot_manifest_published") is not False
        or not _is_publisher_contract_binding(
            projection.get("publisher_contract_binding")
        )
        or consumption.get("schema_version")
        != "semantic-guard-u10-snapshot-projection-authorization-consumption/v1"
        or consumption.get("public_operation") != "project-snapshot"
        or consumption.get("public_identifier") != authorization_id
        or consumption.get("authorization_ref") != authorization_ref
        or consumption.get("publisher_contract_binding")
        != projection.get("publisher_contract_binding")
        or consumption.get("consumption_digest")
        != _sealed(consumption, "consumption_digest")
        or projection.get("consumption_ref")
        != {
            "consumption_id": consumption.get("consumption_id"),
            "consumption_digest": consumption.get("consumption_digest"),
        }
        or authorization.get("schema_version")
        != "semantic-guard-u10-snapshot-projection-authorization/v1"
        or authorization.get("authorization_id") != authorization_id
        or authorization.get("authorization_digest")
        != _sealed(authorization, "authorization_digest")
        or projection.get("authorization_ref") != authorization_ref
        or projection.get("snapshot_ref") != authorization.get("target_snapshot")
        or projection.get("snapshot_ref")
        != {
            "snapshot_id": manifest.get("snapshot_id"),
            "snapshot_version": manifest.get("snapshot_version"),
            "snapshot_path": str(snapshot),
            "entry_id": manifest.get("prepared_for_entry_id"),
        }
        or value.get("snapshot_ref") != expected_snapshot_ref
        or not isinstance(projected_basis, dict)
        or projected_basis.get("eligibility_source_ref") != expected_source_ref
        or projected_basis.get("verification_profile_ref") != expected_profile_ref
        or projected_basis.get("environment_profile_ref")
        != expected_environment_ref
        or projected_basis.get("basis_digest")
        != _sealed(projected_basis, "basis_digest")
        or value.get("eligibility_source_ref") != expected_source_ref
        or value.get("verification_profile_ref") != expected_profile_ref
        or value.get("environment_profile_ref") != expected_environment_ref
        or value.get("host_identity_evidence_ref")
        != projected_basis.get("host_identity_evidence_ref")
        or value.get("decision_owner_ref")
        != projected_basis.get("decision_owner_ref")
        or projection.get("tree_digest")
        != manifest.get("root_storage", {}).get("tree_digest")
        or projection.get("snapshot_basis_digest")
        != manifest.get("snapshot_basis_digest")
        or projection.get("artifact_denominator", {}).get("denominator_digest")
        != _digest(_canonical(entries))
    ):
        raise OuterLaunchError("external environment projection binding mismatch")
    host_ref = value.get("host_identity_evidence_ref")
    host_matches = [
        artifact
        for artifact in entries.values()
        if isinstance(artifact, dict)
        and artifact.get("role") == "host_identity_evidence"
        and isinstance(host_ref, dict)
        and artifact.get("snapshot_ref") == host_ref.get("snapshot_artifact_ref")
    ]
    if len(host_matches) != 1:
        raise OuterLaunchError("external host evidence denominator mismatch")
    for field in (
        "decision_owner_authority_evidence_ref",
        "decision_evidence_ref",
        "trusted_entrypoint_ref",
    ):
        evidence_ref = value.get(field)
        if not isinstance(evidence_ref, dict):
            raise OuterLaunchError(f"{field} missing")
        evidence_path = Path(str(evidence_ref.get("locator", "")))
        try:
            evidence_path.relative_to(U10_ROOT)
        except ValueError as exc:
            raise OuterLaunchError(f"{field} outside root") from exc
        evidence_raw = _read_root_file(evidence_path)
        if evidence_ref.get("artifact_digest") != _digest(evidence_raw):
            raise OuterLaunchError(f"{field} artifact mismatch")
    return value, projection


def _entity_id_from_reference(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise OuterLaunchError(f"{label} is not an entity reference")
    matched = _ENTITY_REFERENCE_V1.fullmatch(value)
    if matched is None:
        raise OuterLaunchError(f"{label} is not an entity reference")
    return matched.group("entity_id")


def _current_worker_account_material(account_name: Any) -> dict[str, Any]:
    if not isinstance(account_name, str) or not account_name:
        raise OuterLaunchError("worker account re-observation failed")
    try:
        account = pwd.getpwnam(account_name)
        all_group_ids = sorted(
            set(os.getgrouplist(account.pw_name, account.pw_gid))
        )
    except (KeyError, OSError) as exc:
        raise OuterLaunchError("worker account re-observation failed") from exc
    host_material = {
        "os": platform.system(),
        "architecture": platform.machine(),
        "os_release": platform.release(),
        "platform_version": platform.version(),
        "hostname": platform.node(),
    }
    if any(not isinstance(value, str) or not value for value in host_material.values()):
        raise OuterLaunchError("host platform re-observation failed")
    return {
        "account_name": account.pw_name,
        "uid": account.pw_uid,
        "gid": account.pw_gid,
        "account_supplementary_gids": [
            group_id for group_id in all_group_ids if group_id != account.pw_gid
        ],
        "login_shell": account.pw_shell,
        "home_directory": account.pw_dir,
        "non_login": account.pw_shell in _NON_LOGIN_SHELLS_V1,
        "platform_binding": {
            **host_material,
            "host_identity_digest": _digest(_canonical(host_material)),
        },
    }


def _current_host_identity_material() -> dict[str, Any]:
    observed_platform = {
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
    }
    node_name_digest = _digest(
        _canonical({"platform_node": platform.node()})
    )
    hardware_identifier_digest = _digest(
        _canonical({"uuid_getnode": f"{uuid.getnode():012x}"})
    )
    identity_material = {
        "observed_platform": observed_platform,
        "node_name_digest": node_name_digest,
        "hardware_identifier_digest": hardware_identifier_digest,
        "observation_method": "platform-node-and-uuid-getnode-hashed/v1",
    }
    return {
        **identity_material,
        "identity_digest": _digest(_canonical(identity_material)),
    }


def _validate_current_host_identity_evidence(
    *,
    manifest: dict[str, Any],
    snapshot: Path,
    entries: dict[str, Any],
) -> None:
    environment_ref = manifest.get("environment_profile_ref")
    if not isinstance(environment_ref, dict):
        raise OuterLaunchError("environment profile reference missing")
    environment_snapshot_ref = environment_ref.get("snapshot_artifact_ref")
    matches = [
        artifact
        for artifact in entries.values()
        if isinstance(artifact, dict)
        and artifact.get("role") == "environment_profile"
        and artifact.get("snapshot_ref") == environment_snapshot_ref
    ]
    if len(matches) != 1 or not isinstance(environment_snapshot_ref, dict):
        raise OuterLaunchError("environment profile denominator mismatch")
    environment_path = _inside(
        snapshot, environment_snapshot_ref.get("locator")
    )
    environment_raw = _read_root_file(environment_path)
    environment = _json(environment_raw, "environment profile")
    if (
        environment_snapshot_ref.get("artifact_digest")
        != _digest(environment_raw)
        or environment.get("basis_digest")
        != environment_ref.get("basis_digest")
        or environment.get("basis_digest")
        != _sealed(environment, "basis_digest")
    ):
        raise OuterLaunchError("environment profile binding mismatch")
    host_ref = environment.get("host_identity_ref")
    evidence_ref = host_ref.get("evidence_ref") if isinstance(host_ref, dict) else None
    if not isinstance(evidence_ref, dict):
        raise OuterLaunchError("host identity evidence reference missing")
    host_matches = []
    for artifact in entries.values():
        if not isinstance(artifact, dict) or artifact.get("role") != "host_identity_evidence":
            continue
        source_ref = artifact.get("source_ref")
        if (
            isinstance(source_ref, dict)
            and source_ref.get("record_id") == evidence_ref.get("record_id")
            and source_ref.get("locator") == evidence_ref.get("locator")
            and source_ref.get("artifact_digest")
            == evidence_ref.get("content_digest")
        ):
            host_matches.append(artifact)
    if len(host_matches) != 1:
        raise OuterLaunchError("host identity evidence denominator mismatch")
    reference = host_matches[0].get("snapshot_ref")
    if not isinstance(reference, dict):
        raise OuterLaunchError("host identity snapshot reference missing")
    raw = _read_root_file(_inside(snapshot, reference.get("locator")))
    evidence = _json(raw, "host identity evidence")
    required_fields = {
        "schema_version",
        "evidence_id",
        "observed_platform",
        "node_name_digest",
        "hardware_identifier_digest",
        "identity_digest",
        "observation_method",
        "formal_authority",
        "positive_assurance_allowed",
        "limitations",
        "evidence_digest",
    }
    expected_host_id = (
        f"host.local.{evidence.get('identity_digest', {}).get('value', '')[:24]}"
    )
    observed = {
        key: evidence.get(key)
        for key in (
            "observed_platform",
            "node_name_digest",
            "hardware_identifier_digest",
            "observation_method",
            "identity_digest",
        )
    }
    if (
        set(evidence) != required_fields
        or evidence.get("schema_version")
        != "semantic-guard-local-host-identity-evidence/v1"
        or evidence.get("evidence_id") != evidence_ref.get("record_id")
        or _digest(raw) != evidence_ref.get("content_digest")
        or reference.get("artifact_digest") != _digest(raw)
        or reference.get("semantic_digest") != evidence.get("evidence_digest")
        or evidence.get("evidence_digest") != _sealed(evidence, "evidence_digest")
        or host_ref.get("host_id") != expected_host_id
        or host_ref.get("identity_digest") != evidence.get("identity_digest")
        or environment.get("platform") != evidence.get("observed_platform")
        or observed != _current_host_identity_material()
    ):
        raise OuterLaunchError("host identity re-observation mismatch")


def _validate_preactivation_boundary(
    *,
    manifest: dict[str, Any],
    entry: dict[str, Any],
    snapshot: Path,
    entries: dict[str, Any],
) -> None:
    binding = manifest.get("preactivation_boundary_binding")
    required_binding = {
        "profile",
        "candidate_bundle_ref",
        "boundary_binding_digest",
        "decision_record_ref",
        "worker_account_observation_ref",
        "worker_principal_resolution_ref",
        "subject_entity_id",
        "worker_principal_entity_id",
        "threat_boundary",
        "worker_identity_policy",
        "qualification_scope",
        "hostile_code_assurance",
        "requalification_triggers",
        "effective_worker_identity",
    }
    if (
        not isinstance(binding, dict)
        or set(binding) != required_binding
        or binding != entry.get("preactivation_boundary_binding")
    ):
        raise OuterLaunchError("preactivation store/snapshot binding mismatch")

    def load_bound_artifact(
        reference: dict[str, Any], role: str, label: str
    ) -> tuple[dict[str, Any], bytes, dict[str, Any]]:
        snapshot_ref = reference.get("snapshot_artifact_ref")
        matches = [
            artifact
            for artifact in entries.values()
            if isinstance(artifact, dict)
            and artifact.get("role") == role
            and artifact.get("snapshot_ref") == snapshot_ref
        ]
        if len(matches) != 1 or not isinstance(snapshot_ref, dict):
            raise OuterLaunchError(f"{label} denominator binding mismatch")
        path = _inside(snapshot, snapshot_ref.get("locator"))
        raw = _read_root_file(path)
        if snapshot_ref.get("artifact_digest") != _digest(raw):
            raise OuterLaunchError(f"{label} artifact digest mismatch")
        return _json(raw, label), raw, matches[0]

    candidate_ref = binding.get("candidate_bundle_ref")
    if not isinstance(candidate_ref, dict):
        raise OuterLaunchError("candidate bundle reference missing")
    candidate, candidate_raw, candidate_entry = load_bound_artifact(
        candidate_ref,
        "u10_candidate_bundle_manifest",
        "candidate bundle manifest",
    )
    expected_candidate_source = {
        "record_id": candidate_ref.get("bundle_id"),
        "locator": candidate_ref.get("candidate_locator"),
        "artifact_digest": candidate_ref.get("artifact_digest"),
        "semantic_digest": candidate_ref.get("bundle_digest"),
    }
    if (
        candidate.get("schema_version")
        != "semantic-guard-u10-root-candidate-bundle/v1"
        or candidate.get("bundle_id") != candidate_ref.get("bundle_id")
        or candidate.get("bundle_version") != candidate_ref.get("bundle_version")
        or candidate.get("bundle_digest") != candidate_ref.get("bundle_digest")
        or candidate.get("bundle_digest") != _sealed(candidate, "bundle_digest")
        or candidate_ref.get("artifact_digest") != _digest(candidate_raw)
        or candidate_ref.get("snapshot_artifact_ref", {}).get("artifact_digest")
        != candidate_ref.get("artifact_digest")
        or candidate_ref.get("snapshot_artifact_ref", {}).get("semantic_digest")
        != candidate_ref.get("bundle_digest")
        or candidate_entry.get("source_ref") != expected_candidate_source
    ):
        raise OuterLaunchError("candidate bundle propagation mismatch")
    candidate_boundary = candidate.get("preactivation_boundary_refs")
    if (
        not isinstance(candidate_boundary, dict)
        or candidate_boundary.get("binding_digest")
        != _sealed(candidate_boundary, "binding_digest")
        or binding.get("boundary_binding_digest")
        != candidate_boundary.get("binding_digest")
    ):
        raise OuterLaunchError("candidate boundary digest mismatch")
    for field in (
        "profile",
        "threat_boundary",
        "worker_identity_policy",
        "qualification_scope",
        "hostile_code_assurance",
        "requalification_triggers",
    ):
        if binding.get(field) != candidate_boundary.get(field):
            raise OuterLaunchError("candidate boundary context mismatch")

    loaded: dict[str, dict[str, Any]] = {}
    for field, role, semantic_field in (
        (
            "decision_record_ref",
            "u10_preactivation_decision_record",
            "decision_digest",
        ),
        (
            "worker_account_observation_ref",
            "u10_worker_account_observation",
            "observation_digest",
        ),
        (
            "worker_principal_resolution_ref",
            "u10_worker_principal_resolution",
            "resolution_digest",
        ),
    ):
        reference = binding.get(field)
        candidate_record = candidate_boundary.get(field)
        if not isinstance(reference, dict) or not isinstance(
            candidate_record, dict
        ):
            raise OuterLaunchError("preactivation record reference missing")
        value, raw, artifact = load_bound_artifact(reference, role, field)
        projected = {
            "record_id": candidate_record.get("record_id"),
            "source_locator": candidate_record.get("source_locator"),
            "source_artifact_digest": candidate_record.get(
                "source_artifact_digest"
            ),
            "candidate_relative_locator": candidate_record.get(
                "bundled_locator"
            ),
            "candidate_artifact_digest": candidate_record.get(
                "bundled_artifact_digest"
            ),
            "semantic_digest": candidate_record.get("semantic_digest"),
            "snapshot_artifact_ref": reference.get("snapshot_artifact_ref"),
        }
        candidate_artifact_locator = str(
            Path(str(candidate_ref["candidate_locator"])).parent
            / "payload"
            / str(reference["candidate_relative_locator"])
        )
        expected_source = {
            "record_id": reference.get("record_id"),
            "locator": candidate_artifact_locator,
            "artifact_digest": reference.get("candidate_artifact_digest"),
            "semantic_digest": reference.get("semantic_digest"),
        }
        if (
            reference != projected
            or artifact.get("source_ref") != expected_source
            or reference.get("source_artifact_digest") != _digest(raw)
            or reference.get("candidate_artifact_digest") != _digest(raw)
            or reference.get("snapshot_artifact_ref", {}).get("artifact_digest")
            != _digest(raw)
            or reference.get("snapshot_artifact_ref", {}).get("semantic_digest")
            != reference.get("semantic_digest")
            or value.get(semantic_field) != reference.get("semantic_digest")
            or value.get(semantic_field) != _sealed(value, semantic_field)
        ):
            raise OuterLaunchError("preactivation record propagation mismatch")
        loaded[field] = value

    decision = loaded["decision_record_ref"]
    observation = loaded["worker_account_observation_ref"]
    resolution = loaded["worker_principal_resolution_ref"]
    decision_ref = binding["decision_record_ref"]
    expected_resolution_decision_ref = {
        "record_id": decision_ref["record_id"],
        "locator": decision_ref["source_locator"],
        "artifact_digest": decision_ref["source_artifact_digest"],
        "semantic_digest": decision_ref["semantic_digest"],
    }
    observation_ref = binding["worker_account_observation_ref"]
    expected_resolution_observation_ref = {
        "record_id": observation_ref["record_id"],
        "locator": observation_ref["source_locator"],
        "artifact_digest": observation_ref["source_artifact_digest"],
        "semantic_digest": observation_ref["semantic_digest"],
    }
    effective = binding.get("effective_worker_identity")
    observed_account = {
        field: observation[field]
        for field in (
            "account_name",
            "uid",
            "gid",
            "account_supplementary_gids",
            "login_shell",
            "home_directory",
            "non_login",
            "platform_binding",
        )
    }
    if (
        decision.get("schema_version")
        != "semantic-guard-u10-preactivation-decision/v1"
        or decision.get("decision_id") != decision_ref["record_id"]
        or decision.get("human_decision") != "accept"
        or decision.get("decision_owner") != "human"
        or decision.get("threat_boundary_selection")
        != binding["threat_boundary"]
        or decision.get("worker_identity_selection")
        != binding["worker_identity_policy"]
        or _entity_id_from_reference(
            decision.get("subject_entity_ref"), "subject_entity_ref"
        )
        != binding["subject_entity_id"]
        or observation.get("schema_version")
        != "semantic-guard-u10-worker-account-observation/v1"
        or observation.get("observation_id") != observation_ref["record_id"]
        or observation.get("decision_record_ref")
        != expected_resolution_decision_ref
        or observation.get("worker_identity_selection")
        != binding["worker_identity_policy"]
        or _entity_id_from_reference(
            observation.get("subject_entity_ref"),
            "observation subject_entity_ref",
        )
        != binding["subject_entity_id"]
        or _entity_id_from_reference(
            observation.get("derived_from"), "observation derived_from"
        )
        != _entity_id_from_reference(
            decision.get("decision_entity_ref"), "decision_entity_ref"
        )
        or _entity_id_from_reference(
            observation.get("principal_entity_ref"),
            "observation principal_entity_ref",
        )
        != binding["worker_principal_entity_id"]
        or _current_worker_account_material(observation.get("account_name"))
        != observed_account
        or resolution.get("schema_version")
        != "semantic-guard-u10-worker-principal-resolution/v1"
        or resolution.get("resolution_id")
        != binding["worker_principal_resolution_ref"]["record_id"]
        or resolution.get("resolution_state") != "resolved"
        or resolution.get("worker_identity_selection")
        != binding["worker_identity_policy"]
        or resolution.get("decision_record_ref")
        != expected_resolution_decision_ref
        or resolution.get("account_observation_ref")
        != expected_resolution_observation_ref
        or _entity_id_from_reference(
            resolution.get("derived_from"), "derived_from"
        )
        != _entity_id_from_reference(
            observation.get("observation_entity_ref"),
            "observation_entity_ref",
        )
        or _entity_id_from_reference(
            resolution.get("principal_entity_ref"), "principal_entity_ref"
        )
        != binding["worker_principal_entity_id"]
        or resolution.get("account_name") != observation.get("account_name")
        or resolution.get("uid") != observation.get("uid")
        or resolution.get("gid") != observation.get("gid")
        or resolution.get("account_supplementary_gids")
        != observation.get("account_supplementary_gids")
        or resolution.get("login_shell") != observation.get("login_shell")
        or resolution.get("non_login") != observation.get("non_login")
        or resolution.get("platform_binding")
        != observation.get("platform_binding")
        or not isinstance(effective, dict)
        or effective
        != {
            "uid": resolution.get("uid"),
            "gid": resolution.get("gid"),
            "effective_supplementary_gids": resolution.get(
                "effective_supplementary_gids"
            ),
            "umask": resolution.get("umask"),
        }
        or effective
        != {
            "uid": manifest["worker_identity"]["uid"],
            "gid": manifest["worker_identity"]["gid"],
            "effective_supplementary_gids": manifest["worker_identity"][
                "effective_supplementary_gids"
            ],
            "umask": manifest["worker_identity"]["umask"],
        }
        or effective
        != {
            "uid": entry["execution_uid"],
            "gid": entry["execution_gid"],
            "effective_supplementary_gids": entry[
                "execution_supplementary_gids"
            ],
            "umask": entry["execution_umask"],
        }
        or manifest["worker_identity"]["account_supplementary_gids"]
        != observation["account_supplementary_gids"]
        or manifest["worker_identity"]["login_shell"]
        != observation["login_shell"]
        or manifest["worker_identity"]["non_login"]
        != observation["non_login"]
        or manifest["worker_identity"]["principal_entity_id"]
        != binding["worker_principal_entity_id"]
        or manifest["worker_identity"]["principal_resolution_digest"]
        != binding["worker_principal_resolution_ref"]["semantic_digest"]
    ):
        raise OuterLaunchError("preactivation identity context mismatch")
    decision_time = _parse_rfc3339_datetime(decision.get("recorded_at"))
    observation_time = _parse_rfc3339_datetime(observation.get("observed_at"))
    resolution_time = _parse_rfc3339_datetime(resolution.get("resolved_at"))
    if (
        decision_time is None
        or observation_time is None
        or resolution_time is None
        or not decision_time <= observation_time <= resolution_time
    ):
        raise OuterLaunchError("preactivation chronology mismatch")


def _validate_snapshot_chronology(
    manifest: dict[str, Any],
    environment_adoption: dict[str, Any],
    snapshot_adoption: dict[str, Any],
    activation: dict[str, dict[str, Any]],
) -> None:
    verification = manifest.get("immutability_verification")
    if not isinstance(verification, dict):
        raise OuterLaunchError("snapshot immutability verification missing")
    verified_at = _parse_rfc3339_datetime(verification.get("verified_at"))
    environment_adoption_recorded_at = _parse_rfc3339_datetime(
        environment_adoption.get("recorded_at")
    )
    snapshot_adoption_recorded_at = _parse_rfc3339_datetime(
        snapshot_adoption.get("recorded_at")
    )
    basis = activation["basis"]
    consumption = activation["consumption"]
    receipt = activation["receipt"]
    reserved_at = _parse_rfc3339_datetime(consumption.get("reserved_at"))
    activation_prepared_at = _parse_rfc3339_datetime(
        consumption.get("activation_prepared_at")
    )
    basis_prepared_at = _parse_rfc3339_datetime(
        basis.get("activation_prepared_at")
    )
    publication_observed_at = _parse_rfc3339_datetime(
        receipt.get("publication_observed_at")
    )
    receipt_recorded_at = _parse_rfc3339_datetime(
        receipt.get("receipt_recorded_at")
    )
    activation_verified_at = _parse_rfc3339_datetime(
        basis.get("immutability_verified_at")
    )
    # This rejects retrospective ordering, but does not authenticate a clock.
    if (
        verified_at is None
        or environment_adoption_recorded_at is None
        or snapshot_adoption_recorded_at is None
        or reserved_at is None
        or activation_prepared_at is None
        or basis_prepared_at is None
        or publication_observed_at is None
        or receipt_recorded_at is None
        or activation_verified_at != verified_at
        or activation_prepared_at != basis_prepared_at
        or receipt.get("publication_not_before") != consumption.get("reserved_at")
        or not verified_at
        <= environment_adoption_recorded_at
        <= snapshot_adoption_recorded_at
        <= reserved_at
        <= activation_prepared_at
        <= publication_observed_at
        <= receipt_recorded_at
    ):
        raise OuterLaunchError("snapshot verification adoption chronology mismatch")


def _request(arguments: list[str]) -> dict[str, str]:
    if len(arguments) != 6 or arguments[0::2] != [
        "--entry-id",
        "--command-id",
        "--request-nonce",
    ]:
        raise OuterLaunchError("invalid request argument denominator")
    nonce = arguments[5]
    if len(nonce) != 64 or any(item not in "0123456789abcdef" for item in nonce):
        raise OuterLaunchError("invalid request nonce")
    return {"entry_id": arguments[1], "command_id": arguments[3], "request_nonce": nonce}


def _validate_startup() -> None:
    if os.geteuid() != 0:
        raise OuterLaunchError("outer launcher requires euid 0")
    if not (sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode):
        raise OuterLaunchError("outer launcher requires -I -S -B")
    if Path(__file__).absolute() != OUTER_LAUNCHER or Path(__file__).is_symlink():
        raise OuterLaunchError("outer launcher path is not fixed")
    _consume_os_injected_environment()
    for name, value in EXPECTED_ENVIRONMENT.items():
        if os.environ.get(name) != value:
            raise OuterLaunchError(f"outer launcher environment mismatch: {name}")
    if any(
        name.startswith(FORBIDDEN_ENVIRONMENT_PREFIXES)
        and name != "PYTHONDONTWRITEBYTECODE"
        for name in os.environ
    ):
        raise OuterLaunchError("loader or Python environment injection detected")


def _validate_store() -> tuple[dict[str, Any], bytes]:
    raw = _read_root_file(CURRENT_STORE, exact_mode=0o444)
    store = _json(raw, "current store")
    if (
        store.get("schema_version") != "semantic-guard-u10-root-trust-store/v2"
        or store.get("lifecycle_state") != "active"
        or store.get("store_digest") != _sealed(store, "store_digest")
        or store.get("store_activation_basis_digest")
        != _store_activation_basis(store)
        or store.get("positive_assurance_allowed") is not False
        or store.get("current_selector", {}).get("path") != str(CURRENT_STORE)
        or store.get("current_selector", {}).get("revocation_selector_path")
        != str(REVOCATION_SELECTOR)
    ):
        raise OuterLaunchError("current store contract mismatch")
    history = HISTORY_ROOT / f"{_digest(raw)['value']}.json"
    if _read_root_file(history, exact_mode=0o444) != raw:
        raise OuterLaunchError("current store history mismatch")
    authorization, store_activation_basis = _validate_authorization(store)
    activation_consumption, activation_receipt = (
        _validate_activation_transition_records(store, raw, authorization)
    )
    if (
        store_activation_basis["publisher_contract_binding"]
        != activation_consumption["publisher_contract_binding"]
    ):
        raise OuterLaunchError("store activation publisher binding mismatch")
    _validate_current_revocation_state(store, raw, activation_receipt)
    _verify_root_ref(store["broker_entrypoint_ref"], ENTRYPOINT)
    _verify_root_ref(store["broker_outer_launcher_ref"], OUTER_LAUNCHER)
    platform = store["broker_launch_platform"]
    if (
        platform.get("profile")
        != "darwin-root-wrapper-qualified-effective-python/v2"
        or platform.get("environment_policy")
        != "privileged_sh_p_then_env_i_direct_effective_execve/v3"
        or platform.get("shell_flags") != ["-p"]
        or platform.get("os_injected_environment_policy")
        != "cf_user_text_encoding_uid_bound_then_removed/v1"
        or platform.get("python_flags") != ["-I", "-S", "-B"]
    ):
        raise OuterLaunchError("broker launch platform mismatch")
    _verify_host_ref(platform["shell_ref"], Path("/bin/sh"))
    _verify_host_ref(platform["environment_cleaner_ref"], Path("/usr/bin/env"))
    effective_path_raw = _verify_root_ref(
        platform["effective_python_path_ref"], EFFECTIVE_PYTHON_PATH
    )
    try:
        effective_path_text = effective_path_raw.decode("utf-8")
    except UnicodeError as exc:
        raise OuterLaunchError("effective Python path is not UTF-8") from exc
    if (
        not effective_path_text.endswith("\n")
        or effective_path_text.count("\n") != 1
        or "\x00" in effective_path_text
    ):
        raise OuterLaunchError("effective Python path record is not one sealed line")
    effective_path = Path(effective_path_text[:-1])
    if (
        not effective_path.is_absolute()
        or effective_path != Path(os.path.normpath(str(effective_path)))
        or Path(os.path.realpath(effective_path)) != effective_path
    ):
        raise OuterLaunchError("effective Python path is not canonical")
    _verify_host_ref(platform["effective_python_ref"], effective_path)
    if Path(os.path.realpath(sys.executable)) != Path(
        str(platform["effective_python_ref"]["resolved_locator"])
    ):
        raise OuterLaunchError("outer interpreter mismatch")
    _validate_bootstrap_runtime_manifest(platform)
    return store, raw


def _validate_snapshot(store: dict[str, Any], request: dict[str, str]) -> tuple[Path, Path, dict[str, Any]]:
    entry = store.get("entries", {}).get(request["entry_id"])
    if not isinstance(entry, dict) or entry.get("entry_state") != "active":
        raise OuterLaunchError("requested trust entry is not active")
    if entry.get("entry_digest") != _sealed(entry, "entry_digest"):
        raise OuterLaunchError("trust entry digest mismatch")
    if request["command_id"] not in entry.get("commands", {}):
        raise OuterLaunchError("requested command is not allowed")
    binding = entry["snapshot_manifest_binding"]
    manifest_path = Path(str(binding["locator"]))
    raw = _read_root_file(manifest_path)
    if binding.get("artifact_digest") != _digest(raw):
        raise OuterLaunchError("snapshot manifest artifact mismatch")
    manifest = _json(raw, "snapshot manifest")
    if (
        manifest.get("schema_version")
        != "semantic-guard-u10-execution-snapshot-manifest/v1"
        or manifest.get("lifecycle_state") != "active"
        or manifest.get("prepared_for_entry_id") != request["entry_id"]
        or manifest.get("manifest_digest") != _sealed(manifest, "manifest_digest")
        or manifest.get("manifest_digest") != binding.get("manifest_digest")
        or manifest.get("snapshot_basis_digest") != _snapshot_basis(manifest)
    ):
        raise OuterLaunchError("snapshot manifest binding mismatch")
    snapshot = Path(str(manifest["root_storage"]["snapshot_path"]))
    if snapshot.parent != SNAPSHOT_ROOT or manifest_path != snapshot / MANIFEST_NAME:
        raise OuterLaunchError("snapshot root binding mismatch")
    _validate_ancestors(snapshot, include_leaf=True)
    observed_root = snapshot.lstat()
    if stat.S_IMODE(observed_root.st_mode) != 0o555:
        raise OuterLaunchError("active snapshot root mode is not 0555")
    records, regular = _tree_records(snapshot, frozenset({manifest_path}))
    if _digest(_canonical({"entries": records})) != manifest["root_storage"]["tree_digest"]:
        raise OuterLaunchError("snapshot tree digest mismatch")
    denominator = manifest["artifact_denominator"]
    if denominator.get("status") != "closed" or not isinstance(denominator.get("entries"), dict):
        raise OuterLaunchError("snapshot denominator is not closed")
    entries = denominator["entries"]
    declared: set[Path] = set()
    for artifact_id, artifact in entries.items():
        reference = artifact["snapshot_ref"]
        if reference.get("record_id") != artifact_id:
            raise OuterLaunchError("snapshot artifact identity mismatch")
        locator = _inside(snapshot, reference["locator"])
        artifact_raw = _read_root_file(locator)
        if reference.get("artifact_digest") != _digest(artifact_raw):
            raise OuterLaunchError(f"snapshot artifact digest mismatch: {artifact_id}")
        declared.add(locator)
    if declared != regular or len(declared) != len(entries):
        raise OuterLaunchError("snapshot regular-file denominator mismatch")
    _validate_preactivation_boundary(
        manifest=manifest,
        entry=entry,
        snapshot=snapshot,
        entries=entries,
    )
    _validate_current_host_identity_evidence(
        manifest=manifest,
        snapshot=snapshot,
        entries=entries,
    )
    environment_adoption, projection = _validate_environment_adoption_artifact(
        manifest=manifest,
        snapshot=snapshot,
        entries=entries,
        entry=entry,
    )
    adoption = _validate_snapshot_adoption(
        manifest,
        request["entry_id"],
        projection_receipt_ref=environment_adoption["projection_receipt_ref"],
        environment_adoption_ref=manifest["environment_adoption_ref"],
    )
    activation = _validate_snapshot_activation(
        manifest,
        request["entry_id"],
        environment_adoption,
        adoption,
        raw,
    )
    _validate_snapshot_chronology(
        manifest,
        environment_adoption,
        adoption,
        activation,
    )
    launch = manifest["broker_launch_contract"]
    if (
        launch.get("invocation_mode")
        != "fixed_root_wrapper_outer_verifier_then_snapshot_execve/v2"
        or launch.get("entrypoint_ref") != store["broker_entrypoint_ref"]
        or launch.get("outer_launcher_ref") != store["broker_outer_launcher_ref"]
        or launch.get("platform_binding_digest")
        != _digest(_canonical(store["broker_launch_platform"]))
        or launch.get("python_flags") != ["-I", "-S", "-B"]
        or launch.get("environment_policy")
        != "env_i_direct_qualified_python_then_exact_snapshot_execve/v3"
    ):
        raise OuterLaunchError("snapshot outer launch contract mismatch")
    inner_ref = manifest["broker_runtime_ref"]
    if inner_ref != store["broker_runtime_ref"]:
        raise OuterLaunchError("inner broker runtime store mismatch")
    inner = _inside(snapshot, inner_ref["locator"])
    if inner.name != INNER_NAME or _digest(_read_root_file(inner)) != inner_ref["artifact_digest"]:
        raise OuterLaunchError("inner broker runtime mismatch")
    runtime = manifest["worker_runtime"]
    interpreter_ref = runtime["interpreter_snapshot_ref"]
    interpreter = _inside(snapshot, interpreter_ref["locator"])
    if _digest(_read_root_file(interpreter)) != interpreter_ref["artifact_digest"]:
        raise OuterLaunchError("snapshot interpreter mismatch")
    subject = _inside(snapshot, runtime["subject_source_root"]["locator"])
    package = subject / BROKER_PACKAGE
    if not package.is_dir() or package.is_symlink():
        raise OuterLaunchError("trusted broker package missing from subject source")
    for tree in runtime["dependency_import_roots"]:
        dependency = _inside(snapshot, tree["locator"])
        for child in dependency.iterdir():
            if child.name == BROKER_PACKAGE or child.name.startswith(f"{BROKER_PACKAGE}."):
                raise OuterLaunchError("dependency broker namespace collision")
    return interpreter, inner, manifest


def main(argv: list[str] | None = None) -> int:
    _validate_startup()
    request_arguments = list(sys.argv[1:] if argv is None else argv)
    request = _request(request_arguments)
    store, _store_raw = _validate_store()
    interpreter, inner, manifest = _validate_snapshot(store, request)
    os.umask(0o077)
    environment = {
        "PATH": "",
        "LC_ALL": "C",
        "PYTHONDONTWRITEBYTECODE": "1",
        "SEMANTIC_GUARD_U10_OUTER_VERIFICATION": manifest["manifest_digest"]["value"],
    }
    os.execve(
        str(interpreter),
        [str(interpreter), "-I", "-S", "-B", str(inner), *request_arguments],
        environment,
    )
    raise OuterLaunchError("snapshot execve returned unexpectedly")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OuterLaunchError, OSError, KeyError, TypeError, ValueError) as exc:
        print(f"U-10 outer launcher failed: {exc}", file=sys.stderr)
        raise SystemExit(70)
