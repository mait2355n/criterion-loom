"""Fail-closed trust resolution and Ed25519 attestation for U-10.

The public request contains only an entry identifier, command identifier, and
one-shot nonce.  All paths, digests, identities, and output locations are
resolved from the fixed root-owned store.
"""

from __future__ import annotations

import base64
from collections.abc import Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import plistlib
import pwd
import re
import secrets
import stat
import sys
from typing import Any
import uuid

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.exceptions import InvalidSignature
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

from .internal_contracts import (
    CONTROL_ALLOWED_OPERATIONS_V1,
    STORE_ACTIVATION_LEDGER_POLICY_V3,
    STORE_LEDGER_RETENTION_POLICY_V1,
    STORE_REVOCATION_LEDGER_POLICY_V2,
)
from .protected_io import (
    AUTHORIZATION_ROOT,
    BROKER_EFFECTIVE_PYTHON_PATH,
    BROKER_EFFECTIVE_RUNTIME_MANIFEST_PATH,
    BROKER_ENTRYPOINT_PATH,
    BROKER_OUTER_LAUNCHER_PATH,
    CONTROL_EFFECTIVE_PYTHON_PATH,
    CONTROL_RUNTIME_MANIFEST_PATH,
    BrokerBoundaryError,
    EVIDENCE_SPOOL_ROOT,
    KEY_ROOT,
    INITIAL_BOOTSTRAP_PROVENANCE_BINDING_PATH,
    INITIAL_TRUST_PROVISIONER_PATH,
    NONCE_LEDGER_ROOT,
    REVOCATION_ROOT,
    REVOCATION_LEDGER_ROOT,
    REVOCATION_SELECTOR_PATH,
    ROOT_CONTROL_DISPATCHER_PATH,
    ROOT_CONTROL_ENTRYPOINT_PATH,
    ROOT_CONTROL_OUTER_LAUNCHER_PATH,
    SNAPSHOT_STORE_PRODUCER_PATH,
    SNAPSHOT_PROJECTION_LEDGER_ROOT,
    SNAPSHOT_ACTIVATION_LEDGER_ROOT,
    SNAPSHOT_ACTIVATION_ROOT,
    SNAPSHOT_ROOT,
    STORE_ACTIVATION_BASIS_ROOT,
    STORE_ACTIVATION_LEDGER_ROOT,
    TRUST_STORE_PATH,
    TRUST_STORE_HISTORY_ROOT,
    TRUST_STORE_LOCK_PATH,
    U10_ROOT,
    digest_bytes,
    read_protected_file,
    reserve_nonce_once,
    strict_json_loads,
    trust_store_coordination_lock,
    validate_directory_chain,
    validate_protected_tree,
)
from .darwin_acl import assert_no_extended_acl
from .runtime_closure import (
    _RUNTIME_CLOSURE_PROFILE,
    _RUNTIME_OS_EXCLUSION_PROFILE,
    _RUNTIME_OS_ASSET_ROOTS,
    _RUNTIME_PROBE_ENVIRONMENT,
    _RUNTIME_PROBE,
    _derive_runtime_root_v1,
    _host_runtime_tree_entries_v1,
    _probe_bootstrap_runtime_v1,
    _ref_artifact_digest,
    _runtime_inclusion_paths_v1,
    _runtime_path_is_under_v1,
    _validate_absolute_root_owned_chain_v1,
    _validate_current_process_runtime_closure_v1,
    _verify_host_runtime_artifact,
    _verify_root_artifact,
)


BROKER_ID = "semantic-guard.u10.root-execution-broker"
BROKER_VERSION = "3.0.0-candidate"
SIGNATURE_PREFIX = b"semantic-guard:u10-broker-envelope:v2\0"
SIGNATURE_PREFIX_V3 = b"semantic-guard:u10-broker-envelope:v3\0"
_BROKER_CONTEXT_FIELDS_V1 = frozenset(
    {
        "schema_version",
        "run_id",
        "receipt_id",
        "entry_id",
        "command_id",
        "request_nonce",
        "snapshot_root",
        "evidence_store_root",
        "output_directory",
        "source_ref",
        "profile_ref",
        "environment_ref",
        "worker_identity",
        "worker_launch",
        "dependency_import_roots",
        "subject_source_root",
        "phase_budget",
    }
)
_BROKER_CONTEXT_FIELDS_V2 = frozenset(
    {
        *_BROKER_CONTEXT_FIELDS_V1,
        "environment_adoption_ref",
        "environment_adoption",
    }
)
_WORKER_PHASE_BUDGET_FIELDS_V1 = frozenset(
    {
        "profile",
        "pre_environment_reobservation_seconds",
        "post_environment_reobservation_seconds",
        "evidence_finalization_seconds",
        "process_reap_seconds",
        "governed_command_timeout_seconds",
        "whole_run_timeout_seconds",
    }
)
_ENTITY_REFERENCE_V1 = re.compile(
    r"^.{1,200}・(?P<entity_id>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$"
)
_NON_LOGIN_SHELLS_V1 = frozenset(
    {"/bin/false", "/usr/bin/false", "/sbin/nologin", "/usr/sbin/nologin"}
)
_CONTROL_VERIFICATION_MARKER_V1 = "fixed-control-outer-v1"
_CONTROL_PUBLISHER_CONTRACT_ID_V1 = "semantic-guard.u10.fixed-root-control-publisher.v1"
_CONTROL_ALLOWED_OPERATIONS_V1 = list(CONTROL_ALLOWED_OPERATIONS_V1)
_CONTROL_ARTIFACT_PATHS_V1 = {
    "broker_outer_launcher": BROKER_OUTER_LAUNCHER_PATH,
    "initial_trust_provisioner": INITIAL_TRUST_PROVISIONER_PATH,
    "root_control_dispatcher": ROOT_CONTROL_DISPATCHER_PATH,
    "root_control_entrypoint": ROOT_CONTROL_ENTRYPOINT_PATH,
    "root_control_outer_launcher": ROOT_CONTROL_OUTER_LAUNCHER_PATH,
    "snapshot_store_producer": SNAPSHOT_STORE_PRODUCER_PATH,
}
_PUBLICATION_IDENTIFIER_V1 = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,255}$")

_KEY_AUTHORIZATION_SCHEMA_V2 = "u10-key-operation-authorization-v2.schema.json"
_KEY_CONSUMPTION_SCHEMA_V2 = (
    "u10-key-operation-authorization-consumption-v2.schema.json"
)
_KEY_METADATA_SCHEMA_V2 = "u10-signing-key-metadata-v2.schema.json"
_KEY_REVOCATION_SCHEMA_V2 = "u10-signing-key-revocation-v2.schema.json"
_KEY_SELECTOR_SCHEMA_V2 = "u10-signing-key-selector-v2.schema.json"
_KEY_RECEIPT_SCHEMA_V2 = "u10-key-operation-receipt-v2.schema.json"
_KEY_EMERGENCY_CLOSURE_SCHEMA_V1 = "u10-key-transition-emergency-closure-v1.schema.json"
_KEY_LEGACY_SCHEMA_NAME_BY_KIND_V1 = {
    "authorization": "u10-key-operation-authorization-v1.schema.json",
    "consumption": "u10-key-operation-authorization-consumption-v1.schema.json",
    "metadata": "u10-signing-key-metadata-v1.schema.json",
    "revocation": "u10-signing-key-revocation-v1.schema.json",
    "selector": "u10-signing-key-selector-v1.schema.json",
    "receipt": "u10-key-operation-receipt-v1.schema.json",
}
_KEY_LEGACY_SEAL_FIELD_BY_KIND_V1 = {
    "authorization": "authorization_digest",
    "consumption": "consumption_digest",
    "metadata": "metadata_digest",
    "revocation": "revocation_digest",
    "selector": "selector_digest",
    "receipt": "receipt_digest",
}
_KEY_RECORD_SCHEMA_IDS_V2 = {
    "authorization": "semantic-guard-u10-key-operation-authorization/v2",
    "consumption": ("semantic-guard-u10-key-operation-authorization-consumption/v2"),
    "metadata": "semantic-guard-u10-signing-key-metadata/v2",
    "revocation": "semantic-guard-u10-signing-key-revocation/v2",
    "selector": "semantic-guard-u10-signing-key-selector/v2",
    "receipt": "semantic-guard-u10-key-operation-receipt/v2",
    "emergency_closure": ("semantic-guard-u10-key-transition-emergency-closure/v1"),
}
_KEY_LEGACY_SCHEMA_ID_BY_KIND_V1 = {
    "authorization": "semantic-guard-u10-key-operation-authorization/v1",
    "consumption": ("semantic-guard-u10-key-operation-authorization-consumption/v1"),
    "metadata": "semantic-guard-u10-signing-key-metadata/v1",
    "revocation": "semantic-guard-u10-signing-key-revocation/v1",
    "selector": "semantic-guard-u10-signing-key-selector/v1",
    "receipt": "semantic-guard-u10-key-operation-receipt/v1",
}


@dataclass(frozen=True)
class KeyChainPaths:
    """Fixed U-10 key-chain denominator, with a synthetic-test projection."""

    u10_root: Path = U10_ROOT
    ledger_root: Path = U10_ROOT / "activations" / "key-transitions"
    key_root: Path = KEY_ROOT
    generation_root: Path = KEY_ROOT / "generations"
    revocation_root: Path = KEY_ROOT / "revocations"
    selector_history_root: Path = KEY_ROOT / "selector-history" / "sha256"
    selector_path: Path = KEY_ROOT / "current.json"
    lock_path: Path = KEY_ROOT / "key-transition.lock"


def canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    """Encode signed/digested U-10 material without non-finite numbers."""

    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise BrokerBoundaryError(
            "u10_canonical_json_invalid", type(exc).__name__
        ) from exc


def _strict_json_clone(value: Any) -> Any:
    """Clone JSON material without admitting non-finite values."""

    return strict_json_loads(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    )


def _is_finite_positive_number_v1(value: Any) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
        and value > 0
    )


def _require_digest_value_v1(value: Any, *, code: str) -> dict[str, str]:
    if (
        not isinstance(value, Mapping)
        or set(value) != {"algorithm", "value"}
        or value.get("algorithm") != "sha256"
        or re.fullmatch(r"[0-9a-f]{64}", str(value.get("value", ""))) is None
    ):
        raise BrokerBoundaryError(code, repr(value))
    return {"algorithm": "sha256", "value": str(value["value"])}


def _publisher_artifact_ref_v1(path: Path) -> dict[str, Any]:
    raw = read_protected_file(path, protected_root=U10_ROOT)
    observed = path.lstat()
    if (
        observed.st_uid != 0
        or observed.st_gid != 0
        or observed.st_nlink != 1
        or observed.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
    ):
        raise BrokerBoundaryError("u10_publisher_artifact_untrusted", str(path))
    return {"locator": str(path), "artifact_digest": digest_bytes(raw)}


def _broker_package_binding_from_control_manifest_v1(
    manifest: Mapping[str, Any],
) -> dict[str, Any]:
    try:
        runtime_root = Path(str(manifest["runtime_root"]))
        required_modules = manifest["runtime_closure"]["required_modules"]
        module_records = [
            item
            for item in required_modules
            if item.get("module") == "semantic_guard_u10_broker"
        ]
        if len(module_records) != 1:
            raise ValueError("broker module denominator")
        origin = Path(str(module_records[0]["origin"]["resolved_locator"]))
        package_root = origin.parent
        package_root.relative_to(runtime_root)
        entries = []
        for item in manifest["tree_denominator"]["entries"]:
            absolute = runtime_root / str(item["path"])
            if absolute == package_root or absolute.is_relative_to(package_root):
                entries.append(_strict_json_clone(item))
        if not entries:
            raise ValueError("empty broker package denominator")
    except (KeyError, TypeError, ValueError) as exc:
        raise BrokerBoundaryError(
            "u10_control_broker_package_binding_invalid", repr(exc)
        ) from exc
    return {
        "package_root": str(package_root),
        "entry_count": len(entries),
        "tree_digest": digest_bytes(canonical_json_bytes({"entries": entries})),
    }


def build_current_publisher_contract_binding_v1(
    provenance_chain: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the static fixed-publisher contract after control preflight.

    This is not an occurrence record and contains neither the requested
    identifier nor an invocation timestamp.  The outer launcher, not a caller,
    supplies the verification marker and exact bootstrap/runtime digests.
    """

    if os.environ.get("SEMANTIC_GUARD_U10_CONTROL_VERIFIED") != (
        _CONTROL_VERIFICATION_MARKER_V1
    ):
        raise BrokerBoundaryError(
            "u10_control_outer_verification_missing", "publisher binding"
        )
    if set(provenance_chain) != {
        "artifact_digests",
        "authorization",
        "binding",
        "consumption",
        "formal_authority",
        "plan",
        "positive_assurance_allowed",
        "receipt",
    }:
        raise BrokerBoundaryError(
            "u10_bootstrap_provenance_chain_shape_invalid",
            repr(sorted(provenance_chain)),
        )
    binding = provenance_chain["binding"]
    artifacts = provenance_chain["artifact_digests"]
    if not isinstance(binding, Mapping) or not isinstance(artifacts, Mapping):
        raise BrokerBoundaryError(
            "u10_bootstrap_provenance_chain_shape_invalid", "mapping"
        )
    control_raw = read_protected_file(
        CONTROL_RUNTIME_MANIFEST_PATH, protected_root=U10_ROOT
    )
    control_effective_path_raw = read_protected_file(
        CONTROL_EFFECTIVE_PYTHON_PATH, protected_root=U10_ROOT
    )
    control_manifest = _load_json_bytes(
        control_raw, "u10_control_runtime_manifest_unreadable"
    )
    _validate(
        control_manifest,
        "u10-control-runtime-manifest-v1.schema.json",
        "u10_control_runtime_manifest_invalid",
    )
    _sealed_digest(
        control_manifest,
        "manifest_digest",
        "u10_control_runtime_manifest_digest_mismatch",
    )
    broker_runtime_raw = read_protected_file(
        BROKER_EFFECTIVE_RUNTIME_MANIFEST_PATH, protected_root=U10_ROOT
    )
    broker_effective_path_raw = read_protected_file(
        BROKER_EFFECTIVE_PYTHON_PATH, protected_root=U10_ROOT
    )
    broker_runtime = _load_json_bytes(
        broker_runtime_raw, "u10_bootstrap_runtime_manifest_unreadable"
    )
    _validate(
        broker_runtime,
        "u10-bootstrap-runtime-manifest-v1.schema.json",
        "u10_bootstrap_runtime_manifest_invalid",
    )
    _sealed_digest(
        broker_runtime,
        "manifest_digest",
        "u10_bootstrap_runtime_manifest_digest_mismatch",
    )
    value: dict[str, Any] = {
        "schema_version": ("semantic-guard-u10-control-publisher-contract-binding/v1"),
        "contract_id": _CONTROL_PUBLISHER_CONTRACT_ID_V1,
        "launch_profile": (
            "fixed-root-wrapper-broker-outer-control-runtime-dispatcher/v1"
        ),
        "public_argument_denominator": ["operation", "identifier"],
        "allowed_operations": list(_CONTROL_ALLOWED_OPERATIONS_V1),
        "caller_supplied_paths_allowed": False,
        "caller_supplied_raw_payloads_allowed": False,
        "caller_supplied_inline_authority_allowed": False,
        "caller_environment_injection_allowed": False,
        "artifacts": {
            name: _publisher_artifact_ref_v1(path)
            for name, path in sorted(_CONTROL_ARTIFACT_PATHS_V1.items())
        },
        "broker_runtime_ref": {
            "effective_python_path": str(BROKER_EFFECTIVE_PYTHON_PATH),
            "effective_python_path_artifact_digest": digest_bytes(
                broker_effective_path_raw
            ),
            "runtime_manifest_locator": str(BROKER_EFFECTIVE_RUNTIME_MANIFEST_PATH),
            "runtime_manifest_artifact_digest": digest_bytes(broker_runtime_raw),
            "runtime_manifest_digest": broker_runtime["manifest_digest"],
            "runtime_tree_digest": broker_runtime["tree_denominator"]["tree_digest"],
        },
        "control_runtime_ref": {
            "effective_python_path": str(CONTROL_EFFECTIVE_PYTHON_PATH),
            "effective_python_path_artifact_digest": digest_bytes(
                control_effective_path_raw
            ),
            "runtime_manifest_locator": str(CONTROL_RUNTIME_MANIFEST_PATH),
            "runtime_manifest_artifact_digest": digest_bytes(control_raw),
            "runtime_manifest_digest": control_manifest["manifest_digest"],
            "runtime_tree_digest": control_manifest["tree_denominator"]["tree_digest"],
            "broker_package_binding": (
                _broker_package_binding_from_control_manifest_v1(control_manifest)
            ),
        },
        "bootstrap_provenance_ref": {
            "locator": str(INITIAL_BOOTSTRAP_PROVENANCE_BINDING_PATH),
            "binding_id": binding.get("binding_id"),
            "binding_artifact_digest": artifacts.get("binding"),
            "binding_digest": binding.get("binding_digest"),
            "authorization_id": binding.get("authorization_id"),
            "plan_id": binding.get("plan_id"),
            "chain_artifact_digests": {
                name: artifacts.get(name)
                for name in (
                    "authorization",
                    "plan",
                    "consumption",
                    "receipt",
                )
            },
        },
        "formal_authority": "none",
        "positive_assurance_allowed": False,
    }
    value["binding_digest"] = digest_bytes(canonical_json_bytes(value))
    _validate_publisher_contract_binding_v1(value, enforce_current=True)
    return value


def _validate_publisher_contract_binding_v1(
    value: Any, *, enforce_current: bool
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise BrokerBoundaryError("u10_publisher_contract_binding_invalid", repr(value))
    _validate(
        value,
        "u10-control-publisher-contract-binding-v1.schema.json",
        "u10_publisher_contract_binding_invalid",
    )
    required = {
        "allowed_operations",
        "artifacts",
        "binding_digest",
        "bootstrap_provenance_ref",
        "broker_runtime_ref",
        "caller_environment_injection_allowed",
        "caller_supplied_inline_authority_allowed",
        "caller_supplied_paths_allowed",
        "caller_supplied_raw_payloads_allowed",
        "contract_id",
        "control_runtime_ref",
        "formal_authority",
        "launch_profile",
        "positive_assurance_allowed",
        "public_argument_denominator",
        "schema_version",
    }
    if (
        set(value) != required
        or value.get("schema_version")
        != "semantic-guard-u10-control-publisher-contract-binding/v1"
        or value.get("contract_id") != _CONTROL_PUBLISHER_CONTRACT_ID_V1
        or value.get("launch_profile")
        != "fixed-root-wrapper-broker-outer-control-runtime-dispatcher/v1"
        or value.get("public_argument_denominator") != ["operation", "identifier"]
        or value.get("allowed_operations") != _CONTROL_ALLOWED_OPERATIONS_V1
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
        or value.get("formal_authority") != "none"
    ):
        raise BrokerBoundaryError(
            "u10_publisher_contract_binding_invalid", "fixed fields"
        )
    material = _strict_json_clone(value)
    observed_digest = material.pop("binding_digest", None)
    if observed_digest != digest_bytes(canonical_json_bytes(material)):
        raise BrokerBoundaryError(
            "u10_publisher_contract_binding_digest_mismatch",
            repr(observed_digest),
        )
    artifacts = value.get("artifacts")
    if not isinstance(artifacts, Mapping) or set(artifacts) != set(
        _CONTROL_ARTIFACT_PATHS_V1
    ):
        raise BrokerBoundaryError("u10_publisher_contract_binding_invalid", "artifacts")
    for name, path in _CONTROL_ARTIFACT_PATHS_V1.items():
        reference = artifacts.get(name)
        if (
            not isinstance(reference, Mapping)
            or set(reference) != {"locator", "artifact_digest"}
            or reference.get("locator") != str(path)
        ):
            raise BrokerBoundaryError("u10_publisher_contract_binding_invalid", name)
        _require_digest_value_v1(
            reference.get("artifact_digest"),
            code="u10_publisher_contract_binding_invalid",
        )
    for field, path, manifest_path in (
        (
            "broker_runtime_ref",
            BROKER_EFFECTIVE_PYTHON_PATH,
            BROKER_EFFECTIVE_RUNTIME_MANIFEST_PATH,
        ),
        (
            "control_runtime_ref",
            CONTROL_EFFECTIVE_PYTHON_PATH,
            CONTROL_RUNTIME_MANIFEST_PATH,
        ),
    ):
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
            not isinstance(reference, Mapping)
            or set(reference) != expected_fields
            or reference.get("effective_python_path") != str(path)
            or reference.get("runtime_manifest_locator") != str(manifest_path)
        ):
            raise BrokerBoundaryError("u10_publisher_contract_binding_invalid", field)
        for digest_field in (
            "effective_python_path_artifact_digest",
            "runtime_manifest_artifact_digest",
            "runtime_manifest_digest",
            "runtime_tree_digest",
        ):
            _require_digest_value_v1(
                reference.get(digest_field),
                code="u10_publisher_contract_binding_invalid",
            )
    package = value["control_runtime_ref"].get("broker_package_binding")
    if (
        not isinstance(package, Mapping)
        or set(package) != {"entry_count", "package_root", "tree_digest"}
        or not isinstance(package.get("entry_count"), int)
        or package.get("entry_count", 0) < 1
        or not Path(str(package.get("package_root", ""))).is_absolute()
    ):
        raise BrokerBoundaryError(
            "u10_publisher_contract_binding_invalid", "broker package"
        )
    _require_digest_value_v1(
        package.get("tree_digest"),
        code="u10_publisher_contract_binding_invalid",
    )
    provenance = value.get("bootstrap_provenance_ref")
    if (
        not isinstance(provenance, Mapping)
        or set(provenance)
        != {
            "authorization_id",
            "binding_artifact_digest",
            "binding_digest",
            "binding_id",
            "chain_artifact_digests",
            "locator",
            "plan_id",
        }
        or provenance.get("locator") != str(INITIAL_BOOTSTRAP_PROVENANCE_BINDING_PATH)
        or not isinstance(provenance.get("binding_id"), str)
        or not isinstance(provenance.get("authorization_id"), str)
        or not isinstance(provenance.get("plan_id"), str)
    ):
        raise BrokerBoundaryError(
            "u10_publisher_contract_binding_invalid", "provenance"
        )
    for digest_field in ("binding_artifact_digest", "binding_digest"):
        _require_digest_value_v1(
            provenance.get(digest_field),
            code="u10_publisher_contract_binding_invalid",
        )
    chain = provenance.get("chain_artifact_digests")
    if not isinstance(chain, Mapping) or set(chain) != {
        "authorization",
        "consumption",
        "plan",
        "receipt",
    }:
        raise BrokerBoundaryError(
            "u10_publisher_contract_binding_invalid", "provenance chain"
        )
    for digest in chain.values():
        _require_digest_value_v1(digest, code="u10_publisher_contract_binding_invalid")
    normalized = _strict_json_clone(value)
    if not enforce_current:
        return normalized
    if (
        os.geteuid() != 0
        or os.environ.get("SEMANTIC_GUARD_U10_CONTROL_VERIFIED")
        != _CONTROL_VERIFICATION_MARKER_V1
        or not sys.flags.isolated
        or sys.flags.no_site
        or not sys.flags.dont_write_bytecode
    ):
        raise BrokerBoundaryError(
            "u10_control_outer_verification_missing", "current process"
        )
    for name, path in _CONTROL_ARTIFACT_PATHS_V1.items():
        if artifacts[name] != _publisher_artifact_ref_v1(path):
            raise BrokerBoundaryError("u10_publisher_artifact_changed", str(path))
    for field, manifest_path, schema_name, code in (
        (
            "broker_runtime_ref",
            BROKER_EFFECTIVE_RUNTIME_MANIFEST_PATH,
            "u10-bootstrap-runtime-manifest-v1.schema.json",
            "u10_bootstrap_runtime_manifest_invalid",
        ),
        (
            "control_runtime_ref",
            CONTROL_RUNTIME_MANIFEST_PATH,
            "u10-control-runtime-manifest-v1.schema.json",
            "u10_control_runtime_manifest_invalid",
        ),
    ):
        raw = read_protected_file(manifest_path, protected_root=U10_ROOT)
        effective_path = (
            BROKER_EFFECTIVE_PYTHON_PATH
            if field == "broker_runtime_ref"
            else CONTROL_EFFECTIVE_PYTHON_PATH
        )
        effective_path_raw = read_protected_file(
            effective_path, protected_root=U10_ROOT
        )
        manifest = _load_json_bytes(raw, code)
        _validate(manifest, schema_name, code)
        _sealed_digest(manifest, "manifest_digest", code)
        reference = value[field]
        if (
            reference["effective_python_path_artifact_digest"]
            != digest_bytes(effective_path_raw)
            or reference["runtime_manifest_artifact_digest"] != digest_bytes(raw)
            or reference["runtime_manifest_digest"] != manifest["manifest_digest"]
            or reference["runtime_tree_digest"]
            != manifest["tree_denominator"]["tree_digest"]
        ):
            raise BrokerBoundaryError("u10_publisher_runtime_binding_changed", field)
        if field == "control_runtime_ref" and reference[
            "broker_package_binding"
        ] != _broker_package_binding_from_control_manifest_v1(manifest):
            raise BrokerBoundaryError(
                "u10_publisher_broker_package_binding_changed", field
            )
    provenance_raw = read_protected_file(
        INITIAL_BOOTSTRAP_PROVENANCE_BINDING_PATH, protected_root=U10_ROOT
    )
    provenance_value = _load_json_bytes(
        provenance_raw, "u10_bootstrap_provenance_binding_unreadable"
    )
    _sealed_digest(
        provenance_value,
        "binding_digest",
        "u10_bootstrap_provenance_binding_digest_mismatch",
    )
    if (
        provenance["binding_artifact_digest"] != digest_bytes(provenance_raw)
        or provenance["binding_digest"] != provenance_value.get("binding_digest")
        or provenance["binding_id"] != provenance_value.get("binding_id")
        or provenance["authorization_id"] != provenance_value.get("authorization_id")
        or provenance["plan_id"] != provenance_value.get("plan_id")
    ):
        raise BrokerBoundaryError(
            "u10_bootstrap_provenance_binding_changed",
            str(INITIAL_BOOTSTRAP_PROVENANCE_BINDING_PATH),
        )
    return normalized


def _schema_directory() -> Path:
    here = Path(__file__).resolve()
    installed = (
        here.parent.parent
        / "semantic_guard_vnext"
        / "validation"
        / "env-path-contracts"
    )
    if (installed / "u10-root-trust-store-v2.schema.json").is_file():
        return installed
    raise BrokerBoundaryError("broker_schema_directory_unavailable", str(here))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _timestamp_v1(value: str, *, code: str) -> datetime:
    try:
        observed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise BrokerBoundaryError(code, value) from exc
    if observed.tzinfo is None:
        raise BrokerBoundaryError(code, value)
    return observed.astimezone(timezone.utc)


def _load_schema(name: str) -> dict[str, Any]:
    path = _schema_directory() / name
    try:
        value = strict_json_loads(path.read_bytes())
        if not isinstance(value, dict):
            raise BrokerBoundaryError(
                "broker_schema_unavailable", f"schema root is not an object: {path}"
            )
        Draft202012Validator.check_schema(value)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BrokerBoundaryError("broker_schema_unavailable", str(path)) from exc
    return value


def _validate(value: Mapping[str, Any], schema_name: str, code: str) -> None:
    registry = Registry()
    for candidate_path in sorted(_schema_directory().glob("*.schema.json")):
        candidate = _load_schema(candidate_path.name)
        resource_id = candidate.get("$id")
        if isinstance(resource_id, str):
            registry = registry.with_resource(
                resource_id,
                Resource.from_contents(candidate),
            )
    issues = sorted(
        Draft202012Validator(
            _load_schema(schema_name),
            registry=registry,
            format_checker=FormatChecker(),
        ).iter_errors(value),
        key=lambda item: tuple(str(part) for part in item.absolute_path),
    )
    if issues:
        issue = issues[0]
        location = "/".join(str(part) for part in issue.absolute_path) or "$"
        raise BrokerBoundaryError(code, f"{location}: {issue.message}")


def _sealed_digest(value: Mapping[str, Any], field: str, code: str) -> None:
    material = dict(value)
    observed = material.pop(field, None)
    if observed != digest_bytes(canonical_json_bytes(material)):
        raise BrokerBoundaryError(code, str(observed))


def snapshot_basis_digest_v1(value: Mapping[str, Any]) -> dict[str, str]:
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
    root_storage = material.get("root_storage")
    if isinstance(root_storage, dict):
        root_storage.pop("storage_state", None)
    return digest_bytes(canonical_json_bytes(material))


def store_activation_basis_digest_v2(
    value: Mapping[str, Any],
) -> dict[str, str]:
    """Seal the exact store basis without creating a digest/reference cycle.

    The lifecycle disposition, its authorization reference, revocation record,
    and the two derived digests are deliberately outside the activation basis.
    All executable content, identities, authorities, and subordinate states
    remain covered.
    """

    material = store_activation_content_v1(value)
    return digest_bytes(canonical_json_bytes(material))


def store_activation_transition_digest_v1(
    *,
    snapshot_manifest_ref: Mapping[str, Any],
    entry_id: str,
    prior_store_ref: Mapping[str, Any] | None,
    prior_revocation_ref: Mapping[str, Any] | None,
    signing_key_ref: Mapping[str, Any],
) -> dict[str, str]:
    """Address one exact store transition independently of wall-clock time.

    A snapshot can be activated against more than one prior store state.  Its
    manifest digest alone therefore cannot identify the resulting revision.
    The transition address binds every mutable predecessor plus the exact
    selected signing-key metadata reference before revision and basis IDs are
    derived.
    """

    material = {
        "schema_version": "semantic-guard-u10-store-transition-basis/v1",
        "snapshot_manifest_ref": _strict_json_clone(snapshot_manifest_ref),
        "entry_id": entry_id,
        "prior_store_ref": _strict_json_clone(prior_store_ref),
        "prior_revocation_ref": _strict_json_clone(prior_revocation_ref),
        "signing_key_ref": _strict_json_clone(signing_key_ref),
    }
    return digest_bytes(canonical_json_bytes(material))


def store_activation_transition_digest_v2(
    *,
    snapshot_manifest_ref: Mapping[str, Any],
    entry_id: str,
    prior_store_ref: Mapping[str, Any] | None,
    prior_revocation_ref: Mapping[str, Any] | None,
    signing_key_ref: Mapping[str, Any],
    signing_key_selector_ref: Mapping[str, Any],
) -> dict[str, str]:
    """Address a store transition and the replayable v2 key-chain head."""

    material = {
        "schema_version": "semantic-guard-u10-store-transition-basis/v2",
        "snapshot_manifest_ref": _strict_json_clone(snapshot_manifest_ref),
        "entry_id": entry_id,
        "prior_store_ref": _strict_json_clone(prior_store_ref),
        "prior_revocation_ref": _strict_json_clone(prior_revocation_ref),
        "signing_key_ref": _strict_json_clone(signing_key_ref),
        "signing_key_selector_ref": _strict_json_clone(signing_key_selector_ref),
    }
    return digest_bytes(canonical_json_bytes(material))


def store_activation_content_v1(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    """Return every non-lifecycle store field covered by human adoption."""

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


def resolve_worker_phase_budget_v1(
    snapshot: Mapping[str, Any], command_id: str
) -> dict[str, Any]:
    """Resolve the exact worker budget from snapshot and command bindings."""

    worker_runtime = snapshot.get("worker_runtime")
    command_bindings = snapshot.get("command_bindings")
    if not isinstance(worker_runtime, Mapping) or not isinstance(
        command_bindings, Mapping
    ):
        raise BrokerBoundaryError("u10_worker_phase_budget_invalid", command_id)
    static_budget = worker_runtime.get("phase_budget")
    command = command_bindings.get(command_id)
    required_static_fields = _WORKER_PHASE_BUDGET_FIELDS_V1 - {
        "governed_command_timeout_seconds",
        "whole_run_timeout_seconds",
    }
    if (
        not isinstance(static_budget, Mapping)
        or set(static_budget) != required_static_fields
        or static_budget.get("profile") != "u10-compositional-worker-budget/v1"
        or not isinstance(command, Mapping)
    ):
        raise BrokerBoundaryError("u10_worker_phase_budget_invalid", command_id)
    command_timeout = command.get("governed_command_timeout_seconds")
    phase_values = [
        static_budget.get("pre_environment_reobservation_seconds"),
        command_timeout,
        static_budget.get("post_environment_reobservation_seconds"),
        static_budget.get("evidence_finalization_seconds"),
        static_budget.get("process_reap_seconds"),
    ]
    if any(not _is_finite_positive_number_v1(value) for value in phase_values):
        raise BrokerBoundaryError("u10_worker_phase_budget_invalid", repr(phase_values))
    return {
        **dict(static_budget),
        "governed_command_timeout_seconds": command_timeout,
        "whole_run_timeout_seconds": float(sum(phase_values)),
    }


def bind_broker_context_phase_budget_v1(
    broker_context_ref: Mapping[str, Any], phase_budget: Mapping[str, Any]
) -> dict[str, Any]:
    """Bind the worker budget visibly into the signed context reference."""

    budget = dict(phase_budget)
    numeric_values = [value for name, value in budget.items() if name != "profile"]
    if set(budget) != _WORKER_PHASE_BUDGET_FIELDS_V1 or any(
        not _is_finite_positive_number_v1(value) for value in numeric_values
    ):
        raise BrokerBoundaryError(
            "u10_envelope_phase_budget_binding_mismatch", repr(sorted(budget))
        )
    return {
        **dict(broker_context_ref),
        "phase_budget": budget,
        "phase_budget_digest": digest_bytes(canonical_json_bytes(budget)),
    }


def _validate_broker_context_phase_budget_v1(
    *,
    broker_context: Mapping[str, Any],
    context_ref: Mapping[str, Any],
    snapshot: Mapping[str, Any],
    command_id: str,
) -> None:
    context_version = broker_context.get("schema_version")
    if context_version == "semantic-guard-u10-worker-context/v1":
        expected_fields = _BROKER_CONTEXT_FIELDS_V1
    elif context_version == "semantic-guard-u10-worker-context/v2":
        expected_fields = _BROKER_CONTEXT_FIELDS_V2
    else:
        expected_fields = frozenset()
    if set(broker_context) != expected_fields:
        raise BrokerBoundaryError("u10_envelope_context_binding_mismatch", command_id)
    observed = broker_context.get("phase_budget")
    signed = context_ref.get("phase_budget")
    if (
        not isinstance(observed, Mapping)
        or not isinstance(signed, Mapping)
        or set(observed) != _WORKER_PHASE_BUDGET_FIELDS_V1
        or set(signed) != _WORKER_PHASE_BUDGET_FIELDS_V1
        or any(
            not _is_finite_positive_number_v1(value)
            for name, value in observed.items()
            if name != "profile"
        )
        or any(
            not _is_finite_positive_number_v1(value)
            for name, value in signed.items()
            if name != "profile"
        )
    ):
        raise BrokerBoundaryError(
            "u10_envelope_phase_budget_binding_mismatch", command_id
        )
    expected = resolve_worker_phase_budget_v1(snapshot, command_id)
    expected_digest = digest_bytes(canonical_json_bytes(expected))
    if (
        dict(observed) != expected
        or dict(signed) != expected
        or context_ref.get("phase_budget_digest") != expected_digest
    ):
        raise BrokerBoundaryError(
            "u10_envelope_phase_budget_binding_mismatch", command_id
        )


def _load_json_bytes(raw: bytes, code: str) -> dict[str, Any]:
    try:
        value = strict_json_loads(raw)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise BrokerBoundaryError(code, str(exc)) from exc
    if not isinstance(value, dict):
        raise BrokerBoundaryError(code, "root is not an object")
    return value


def _verify_declared_directory(
    path: Path,
    *,
    uid: int,
    gid: int,
    mode: int,
    code: str,
) -> None:
    validate_directory_chain(path, path, required_uid=uid)
    observed = path.lstat()
    if observed.st_gid != gid or stat.S_IMODE(observed.st_mode) != mode:
        raise BrokerBoundaryError(
            code,
            f"{path}: uid={observed.st_uid} gid={observed.st_gid} "
            f"mode={stat.S_IMODE(observed.st_mode):04o}",
        )


def _fsync_directory_v1(path: Path, *, code: str) -> None:
    try:
        descriptor = os.open(
            path,
            os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
        )
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    except OSError as exc:
        raise BrokerBoundaryError(code, str(path)) from exc


def _remove_transaction_temporaries_v1(
    directory: Path, *, prefix: str, code: str
) -> None:
    """Remove only root-owned transaction temporaries while a writer lock is held."""

    removed = False
    try:
        candidates = tuple(directory.iterdir())
    except OSError as exc:
        raise BrokerBoundaryError(code, str(directory)) from exc
    for candidate in candidates:
        if not candidate.name.startswith(prefix) or not candidate.name.endswith(".tmp"):
            continue
        observed = candidate.lstat()
        try:
            assert_no_extended_acl(candidate)
        except (OSError, PermissionError) as exc:
            raise BrokerBoundaryError(code, str(candidate)) from exc
        if (
            stat.S_ISLNK(observed.st_mode)
            or not stat.S_ISREG(observed.st_mode)
            or observed.st_uid != 0
            or observed.st_gid != 0
            or observed.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
        ):
            raise BrokerBoundaryError(code, str(candidate))
        try:
            candidate.unlink()
        except OSError as exc:
            raise BrokerBoundaryError(code, str(candidate)) from exc
        removed = True
    if removed:
        _fsync_directory_v1(directory, code=code)


def _atomic_create_once_v1(
    path: Path,
    raw: bytes,
    *,
    mode: int,
    temporary_prefix: str,
    collision_code: str,
    create_code: str,
    durability_code: str,
) -> bool:
    """Publish complete bytes under an unused final name without partial finals.

    A unique temporary is fully written and fsynced first.  ``link`` provides
    no-replace publication.  If death occurs after the link but before temp
    removal, the next exclusive transaction removes the root-owned temp and
    recovers the already complete final occurrence.
    """

    directory = path.parent
    _remove_transaction_temporaries_v1(
        directory,
        prefix=temporary_prefix,
        code=create_code,
    )
    try:
        path.lstat()
    except FileNotFoundError:
        pass
    except OSError as exc:
        raise BrokerBoundaryError(create_code, str(path)) from exc
    else:
        existing = read_protected_file(path, protected_root=directory)
        if existing != raw:
            raise BrokerBoundaryError(collision_code, str(path))
        _fsync_directory_v1(directory, code=durability_code)
        return False

    temporary = directory / (f"{temporary_prefix}{secrets.token_hex(16)}.tmp")
    try:
        descriptor = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
            0o600,
        )
    except OSError as exc:
        raise BrokerBoundaryError(create_code, str(temporary)) from exc
    try:
        offset = 0
        while offset < len(raw):
            written = os.write(descriptor, raw[offset:])
            if written <= 0:
                raise BrokerBoundaryError(create_code, str(temporary))
            offset += written
        os.fchmod(descriptor, mode)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    try:
        try:
            os.link(temporary, path, follow_symlinks=False)
        except FileExistsError:
            existing = read_protected_file(path, protected_root=directory)
            if existing != raw:
                raise BrokerBoundaryError(collision_code, str(path))
        except OSError as exc:
            raise BrokerBoundaryError(create_code, str(path)) from exc
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        except OSError as exc:
            raise BrokerBoundaryError(create_code, str(temporary)) from exc
    _fsync_directory_v1(directory, code=durability_code)
    observed = read_protected_file(path, protected_root=directory)
    if observed != raw:
        raise BrokerBoundaryError(collision_code, str(path))
    return True


def _atomic_replace_v1(
    path: Path,
    raw: bytes,
    *,
    mode: int,
    temporary_prefix: str,
    create_code: str,
    durability_code: str,
) -> None:
    """Replace a selector from a fully durable, uniquely named temporary."""

    directory = path.parent
    _remove_transaction_temporaries_v1(
        directory,
        prefix=temporary_prefix,
        code=create_code,
    )
    temporary = directory / f"{temporary_prefix}{secrets.token_hex(16)}.tmp"
    try:
        descriptor = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
            0o600,
        )
    except OSError as exc:
        raise BrokerBoundaryError(create_code, str(temporary)) from exc
    try:
        offset = 0
        while offset < len(raw):
            written = os.write(descriptor, raw[offset:])
            if written <= 0:
                raise BrokerBoundaryError(create_code, str(temporary))
            offset += written
        os.fchmod(descriptor, mode)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    try:
        os.replace(temporary, path)
        _fsync_directory_v1(directory, code=durability_code)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        except OSError as exc:
            raise BrokerBoundaryError(create_code, str(temporary)) from exc


def _principal_mode_bits(
    observed: os.stat_result,
    *,
    uid: int,
    gid: int,
    supplementary_gids: tuple[int, ...],
) -> int:
    mode = stat.S_IMODE(observed.st_mode)
    if observed.st_uid == uid:
        return (mode >> 6) & 0b111
    if observed.st_gid in {gid, *supplementary_gids}:
        return (mode >> 3) & 0b111
    return mode & 0b111


def _verify_worker_snapshot_access(
    root: Path,
    *,
    uid: int,
    gid: int,
    supplementary_gids: tuple[int, ...],
    interpreter: Path,
) -> None:
    for path in (root, *sorted(root.rglob("*"))):
        observed = path.lstat()
        bits = _principal_mode_bits(
            observed,
            uid=uid,
            gid=gid,
            supplementary_gids=supplementary_gids,
        )
        if stat.S_ISDIR(observed.st_mode):
            required = 0b101
        elif stat.S_ISREG(observed.st_mode):
            required = 0b101 if path == interpreter else 0b100
        else:
            raise BrokerBoundaryError("u10_snapshot_special_file", str(path))
        if bits & required != required:
            raise BrokerBoundaryError(
                "u10_snapshot_worker_access_denied",
                f"{path}: bits={bits:03b} required={required:03b}",
            )


def validate_execution_request_v1(request: Mapping[str, Any]) -> None:
    _validate(
        request,
        "u10-execution-request-v1.schema.json",
        "u10_execution_request_invalid",
    )


def validate_root_trust_store_v2(store: Mapping[str, Any]) -> None:
    _validate(
        store,
        "u10-root-trust-store-v2.schema.json",
        "u10_root_trust_store_invalid",
    )
    _sealed_digest(store, "store_digest", "u10_root_trust_store_digest_mismatch")
    if store["store_activation_basis_digest"] != store_activation_basis_digest_v2(
        store
    ):
        raise BrokerBoundaryError(
            "u10_store_activation_basis_digest_mismatch",
            str(store["store_activation_basis_digest"]),
        )
    for entry_id, entry in store["entries"].items():
        _sealed_digest(
            entry,
            "entry_digest",
            "u10_root_trust_entry_digest_mismatch",
        )
        if entry_id != str(entry_id):
            raise BrokerBoundaryError("u10_root_trust_entry_id_invalid", entry_id)
        boundary = entry["preactivation_boundary_binding"]
        effective = boundary["effective_worker_identity"]
        if effective != {
            "uid": entry["execution_uid"],
            "gid": entry["execution_gid"],
            "effective_supplementary_gids": entry["execution_supplementary_gids"],
            "umask": entry["execution_umask"],
        }:
            raise BrokerBoundaryError(
                "u10_root_trust_entry_preactivation_identity_mismatch",
                str(entry_id),
            )


def _load_store_activation_basis_v1(
    reference: Mapping[str, Any],
) -> tuple[dict[str, Any], bytes]:
    record_id = str(reference.get("record_id", ""))
    path = Path(str(reference.get("locator", "")))
    if (
        path.parent != STORE_ACTIVATION_BASIS_ROOT
        or not path.name.endswith(".store-basis.json")
        or not record_id
    ):
        raise BrokerBoundaryError("u10_store_activation_basis_path_mismatch", str(path))
    raw = _verify_root_artifact(reference)
    basis = _load_json_bytes(raw, "u10_store_activation_basis_unreadable")
    _validate(
        basis,
        "u10-store-activation-basis-v1.schema.json",
        "u10_store_activation_basis_invalid",
    )
    _sealed_digest(
        basis,
        "basis_digest",
        "u10_store_activation_basis_digest_mismatch",
    )
    _validate_publisher_contract_binding_v1(
        basis["publisher_contract_binding"], enforce_current=False
    )
    exact_ref = _exact_root_record_ref_v1(
        record_id=basis["basis_id"],
        path=path,
        raw=raw,
        semantic_digest=basis["basis_digest"],
    )
    content = basis["store_content"]
    transition_digest = store_activation_transition_digest_v1(
        snapshot_manifest_ref=basis["snapshot_manifest_ref"],
        entry_id=str(basis["entry_id"]),
        prior_store_ref=basis["prior_store_ref"],
        prior_revocation_ref=basis["prior_revocation_ref"],
        signing_key_ref=basis["signing_key_ref"],
    )
    entry = content.get("entries", {}).get(basis["entry_id"])
    entry_manifest = (
        entry.get("snapshot_manifest_binding") if isinstance(entry, Mapping) else None
    )
    signing_key = content.get("signing_key")
    signing_key_ref = basis["signing_key_ref"]
    snapshot_authorization_ref = basis["snapshot_activation_authorization_ref"]
    if (
        dict(reference) != exact_ref
        or path.name
        != (f"{snapshot_authorization_ref.get('record_id')}.store-basis.json")
        or basis["store_activation_basis_digest"]
        != digest_bytes(canonical_json_bytes(content))
        or basis["store_transition_digest"] != transition_digest
        or basis["basis_id"] != f"store-basis.{transition_digest['value']}"
        or content.get("store_revision_id")
        != f"revision.u10.{transition_digest['value']}"
        or not isinstance(entry_manifest, Mapping)
        or entry_manifest.get("locator")
        != basis["snapshot_manifest_ref"].get("locator")
        or entry_manifest.get("artifact_digest")
        != basis["snapshot_manifest_ref"].get("artifact_digest")
        or entry_manifest.get("manifest_digest")
        != basis["snapshot_manifest_ref"].get("semantic_digest")
        or not isinstance(signing_key, Mapping)
        or signing_key.get("key_id") != signing_key_ref.get("key_id")
        or basis["publication_state"] != "not_published"
    ):
        raise BrokerBoundaryError(
            "u10_store_activation_basis_binding_mismatch", record_id
        )
    return basis, raw


def _load_store_activation_basis_v2(
    reference: Mapping[str, Any],
) -> tuple[dict[str, Any], bytes]:
    """Load one current store basis bound to a replayable v2 key-chain head."""

    record_id = str(reference.get("record_id", ""))
    path = Path(str(reference.get("locator", "")))
    if (
        path.parent != STORE_ACTIVATION_BASIS_ROOT
        or not path.name.endswith(".store-basis.json")
        or not record_id
    ):
        raise BrokerBoundaryError("u10_store_activation_basis_path_mismatch", str(path))
    raw = _verify_root_artifact(reference)
    basis = _load_json_bytes(raw, "u10_store_activation_basis_unreadable")
    _validate(
        basis,
        "u10-store-activation-basis-v2.schema.json",
        "u10_store_activation_basis_invalid",
    )
    _sealed_digest(
        basis,
        "basis_digest",
        "u10_store_activation_basis_digest_mismatch",
    )
    _validate_publisher_contract_binding_v1(
        basis["publisher_contract_binding"], enforce_current=False
    )
    exact_ref = _exact_root_record_ref_v1(
        record_id=basis["basis_id"],
        path=path,
        raw=raw,
        semantic_digest=basis["basis_digest"],
    )
    content = basis["store_content"]
    transition_digest = store_activation_transition_digest_v2(
        snapshot_manifest_ref=basis["snapshot_manifest_ref"],
        entry_id=str(basis["entry_id"]),
        prior_store_ref=basis["prior_store_ref"],
        prior_revocation_ref=basis["prior_revocation_ref"],
        signing_key_ref=basis["signing_key_ref"],
        signing_key_selector_ref=basis["signing_key_selector_ref"],
    )
    entry = content.get("entries", {}).get(basis["entry_id"])
    entry_manifest = (
        entry.get("snapshot_manifest_binding") if isinstance(entry, Mapping) else None
    )
    signing_key = content.get("signing_key")
    signing_key_ref = basis["signing_key_ref"]
    snapshot_authorization_ref = basis["snapshot_activation_authorization_ref"]
    if (
        dict(reference) != exact_ref
        or path.name
        != (f"{snapshot_authorization_ref.get('record_id')}.store-basis.json")
        or basis["store_activation_basis_digest"]
        != digest_bytes(canonical_json_bytes(content))
        or basis["store_transition_digest"] != transition_digest
        or basis["basis_id"] != f"store-basis.{transition_digest['value']}"
        or content.get("store_revision_id")
        != f"revision.u10.{transition_digest['value']}"
        or not isinstance(entry_manifest, Mapping)
        or entry_manifest.get("locator")
        != basis["snapshot_manifest_ref"].get("locator")
        or entry_manifest.get("artifact_digest")
        != basis["snapshot_manifest_ref"].get("artifact_digest")
        or entry_manifest.get("manifest_digest")
        != basis["snapshot_manifest_ref"].get("semantic_digest")
        or not isinstance(signing_key, Mapping)
        or signing_key.get("key_id") != signing_key_ref.get("key_id")
        or basis["publication_state"] != "not_published"
    ):
        raise BrokerBoundaryError(
            "u10_store_activation_basis_binding_mismatch", record_id
        )
    return basis, raw


def _load_store_activation_basis_any_v1(
    reference: Mapping[str, Any],
) -> tuple[dict[str, Any], bytes]:
    """Dispatch only for completed historical-chain replay.

    Current mutation and v3 execution call the v2 loader directly.  This
    dispatcher exists solely so an already completed v1 store remains
    inspectable without silently qualifying it for new execution.
    """

    path = Path(str(reference.get("locator", "")))
    raw = _verify_root_artifact(reference)
    value = _load_json_bytes(raw, "u10_store_activation_basis_unreadable")
    schema_version = value.get("schema_version")
    if schema_version == "semantic-guard-u10-store-activation-basis/v1":
        return _load_store_activation_basis_v1(reference)
    if schema_version == "semantic-guard-u10-store-activation-basis/v2":
        return _load_store_activation_basis_v2(reference)
    raise BrokerBoundaryError(
        "u10_store_activation_basis_version_unsupported",
        f"{path}: {schema_version!r}",
    )


def _validate_store_activation_authorization_v1(
    store: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate a root-held human decision for one exact active store basis.

    This gate authorizes only publication/use of the named store revision.  It
    does not establish U-4 principal authenticity, engineering correctness, or
    positive assurance.
    """

    reference = store.get("activation_authorization_ref")
    if not isinstance(reference, Mapping):
        raise BrokerBoundaryError(
            "u10_store_activation_authorization_missing",
            str(store.get("store_revision_id")),
        )
    path = Path(str(reference.get("locator", "")))
    record_id = str(reference.get("record_id", ""))
    if (
        path.parent != AUTHORIZATION_ROOT
        or path.name != f"{record_id}.json"
        or not record_id
    ):
        raise BrokerBoundaryError(
            "u10_store_activation_authorization_path_mismatch", str(path)
        )
    raw = _verify_root_artifact(reference)
    authorization = _load_json_bytes(
        raw, "u10_store_activation_authorization_unreadable"
    )
    _validate(
        authorization,
        "u10-store-activation-authorization-v1.schema.json",
        "u10_store_activation_authorization_invalid",
    )
    _sealed_digest(
        authorization,
        "authorization_digest",
        "u10_store_activation_authorization_digest_mismatch",
    )
    basis, _basis_raw = _load_store_activation_basis_any_v1(
        authorization["store_activation_basis_ref"]
    )
    if (
        authorization["authorization_id"] != record_id
        or authorization["authorization_digest"] != reference["semantic_digest"]
        or authorization["store_id"] != store["store_id"]
        or authorization["store_revision_id"] != store["store_revision_id"]
        or authorization["store_version"] != store["store_version"]
        or authorization["store_activation_basis_digest"]
        != store["store_activation_basis_digest"]
        or authorization["store_activation_basis_digest"]
        != store_activation_basis_digest_v2(store)
        or basis["store_content"] != store_activation_content_v1(store)
        or basis["store_activation_basis_digest"]
        != store["store_activation_basis_digest"]
        or basis["prior_store_ref"] != authorization["prior_store_ref"]
        or basis["prior_revocation_ref"] != authorization["prior_revocation_ref"]
        or _timestamp_v1(
            str(authorization["recorded_at"]),
            code="u10_store_activation_authorization_time_invalid",
        )
        < _timestamp_v1(
            str(basis["prepared_at"]),
            code="u10_store_activation_basis_time_invalid",
        )
    ):
        raise BrokerBoundaryError(
            "u10_store_activation_authorization_context_mismatch", record_id
        )
    return authorization


def _store_transition_ref_v1(store: Mapping[str, Any], raw: bytes) -> dict[str, Any]:
    return {
        "store_id": store["store_id"],
        "store_revision_id": store["store_revision_id"],
        "store_version": store["store_version"],
        "store_activation_basis_digest": store["store_activation_basis_digest"],
        "artifact_digest": digest_bytes(raw),
        "semantic_digest": store["store_digest"],
    }


def _revocation_transition_ref_v1(
    revocation: Mapping[str, Any], raw: bytes
) -> dict[str, Any]:
    return {
        "revocation_id": revocation["revocation_id"],
        "artifact_digest": digest_bytes(raw),
        "semantic_digest": revocation["revocation_digest"],
    }


def _validate_store_activation_transition_v1(
    authorization: Mapping[str, Any],
    *,
    prior_store: Mapping[str, Any] | None,
    prior_store_raw: bytes | None,
    prior_revocation: tuple[Mapping[str, Any], bytes] | None,
) -> None:
    if prior_store is None:
        expected_kind = "initial_activation"
        expected_store_ref = None
        expected_revocation_ref = None
    else:
        if prior_store_raw is None:
            raise BrokerBoundaryError(
                "u10_store_activation_prior_raw_missing",
                str(prior_store["store_revision_id"]),
            )
        expected_kind = "replace_current_revision"
        expected_store_ref = _store_transition_ref_v1(prior_store, prior_store_raw)
        expected_revocation_ref = (
            _revocation_transition_ref_v1(*prior_revocation)
            if prior_revocation is not None
            else None
        )
    if (
        authorization["transition_kind"] != expected_kind
        or authorization["prior_store_ref"] != expected_store_ref
        or authorization["prior_revocation_ref"] != expected_revocation_ref
    ):
        raise BrokerBoundaryError(
            "u10_store_activation_transition_context_mismatch",
            str(authorization["authorization_id"]),
        )


def _activation_authorization_consumption_path(
    authorization_id: str,
) -> Path:
    return STORE_ACTIVATION_LEDGER_ROOT / (f"{authorization_id}.consumption.json")


def _activation_transition_receipt_path(authorization_id: str) -> Path:
    return STORE_ACTIVATION_LEDGER_ROOT / f"{authorization_id}.receipt.json"


def _cleanup_activation_transaction_temporaries_under_lock_v1(
    authorization_id: str,
) -> None:
    for suffix, code in (
        ("consumption", "u10_store_activation_consumption_create_failed"),
        ("receipt", "u10_store_activation_receipt_create_failed"),
    ):
        _remove_transaction_temporaries_v1(
            STORE_ACTIVATION_LEDGER_ROOT,
            prefix=f".{authorization_id}.{suffix}.",
            code=code,
        )


def _cleanup_current_activation_temporaries_under_lock_v1() -> None:
    try:
        TRUST_STORE_PATH.lstat()
    except FileNotFoundError:
        return
    except OSError as exc:
        raise BrokerBoundaryError(
            "u10_current_store_unavailable", str(TRUST_STORE_PATH)
        ) from exc
    current_store, _current_raw = load_fixed_root_trust_store_record_v2()
    current_authorization = _validate_store_activation_authorization_v1(current_store)
    _cleanup_activation_transaction_temporaries_under_lock_v1(
        str(current_authorization["authorization_id"])
    )


def _load_activation_authorization_consumption_v1(
    store: Mapping[str, Any],
    store_raw: bytes,
    authorization: Mapping[str, Any],
) -> tuple[dict[str, Any], bytes]:
    selector = store["current_selector"]
    if (
        selector["activation_ledger_path"] != str(STORE_ACTIVATION_LEDGER_ROOT)
        or selector["activation_ledger_policy"]
        != STORE_ACTIVATION_LEDGER_POLICY_V3
        or selector["activation_ledger_retention_policy"]
        != STORE_LEDGER_RETENTION_POLICY_V1
    ):
        raise BrokerBoundaryError(
            "u10_store_activation_ledger_contract_mismatch",
            str(selector.get("activation_ledger_path")),
        )
    _verify_declared_directory(
        STORE_ACTIVATION_LEDGER_ROOT,
        uid=0,
        gid=0,
        mode=0o755,
        code="u10_store_activation_ledger_directory_mismatch",
    )
    path = _activation_authorization_consumption_path(
        str(authorization["authorization_id"])
    )
    raw = read_protected_file(path, protected_root=STORE_ACTIVATION_LEDGER_ROOT)
    observed = path.lstat()
    if (
        observed.st_uid != 0
        or observed.st_gid != 0
        or stat.S_IMODE(observed.st_mode) != 0o444
        or observed.st_nlink != 1
    ):
        raise BrokerBoundaryError(
            "u10_store_activation_consumption_untrusted", str(path)
        )
    consumption = _load_json_bytes(raw, "u10_store_activation_consumption_unreadable")
    _validate(
        consumption,
        "u10-store-activation-authorization-consumption-v1.schema.json",
        "u10_store_activation_consumption_invalid",
    )
    _sealed_digest(
        consumption,
        "consumption_digest",
        "u10_store_activation_consumption_digest_mismatch",
    )
    _validate_publisher_contract_binding_v1(
        consumption.get("publisher_contract_binding"),
        enforce_current=False,
    )
    if (
        consumption["consumption_id"]
        != f"consumption.{authorization['authorization_id']}"
        or consumption["public_operation"] != "activate-store"
        or consumption["public_identifier"] != authorization["authorization_id"]
        or consumption["authorization_id"] != authorization["authorization_id"]
        or consumption["authorization_digest"] != authorization["authorization_digest"]
        or consumption["store_activation_basis_ref"]
        != authorization["store_activation_basis_ref"]
        or consumption["transition_kind"] != authorization["transition_kind"]
        or consumption["prior_store_ref"] != authorization["prior_store_ref"]
        or consumption["prior_revocation_ref"] != authorization["prior_revocation_ref"]
        or consumption["target_store_ref"] != _store_transition_ref_v1(store, store_raw)
        or _timestamp_v1(
            str(consumption["reserved_at"]),
            code="u10_store_activation_consumption_time_invalid",
        )
        < _timestamp_v1(
            str(authorization["recorded_at"]),
            code="u10_store_activation_authorization_time_invalid",
        )
    ):
        raise BrokerBoundaryError(
            "u10_store_activation_consumption_context_mismatch", str(path)
        )
    return consumption, raw


def _write_activation_authorization_consumption_under_lock_v1(
    store: Mapping[str, Any],
    store_raw: bytes,
    authorization: Mapping[str, Any],
    publisher_contract_binding: Mapping[str, Any],
) -> dict[str, Any]:
    _verify_declared_directory(
        STORE_ACTIVATION_LEDGER_ROOT,
        uid=0,
        gid=0,
        mode=0o755,
        code="u10_store_activation_ledger_directory_mismatch",
    )
    _remove_transaction_temporaries_v1(
        STORE_ACTIVATION_LEDGER_ROOT,
        prefix=f".{authorization['authorization_id']}.consumption.",
        code="u10_store_activation_consumption_create_failed",
    )
    existing = _try_load_activation_authorization_consumption_v1(
        store, store_raw, authorization
    )
    if existing is not None:
        _fsync_directory_v1(
            STORE_ACTIVATION_LEDGER_ROOT,
            code="u10_store_activation_ledger_directory_fsync_failed",
        )
        return existing[0]
    reserved_at = _utc_now()
    if _timestamp_v1(
        reserved_at,
        code="u10_store_activation_consumption_time_invalid",
    ) < _timestamp_v1(
        str(authorization["recorded_at"]),
        code="u10_store_activation_authorization_time_invalid",
    ):
        raise BrokerBoundaryError(
            "u10_store_activation_consumption_chronology_invalid",
            str(authorization["authorization_id"]),
        )
    consumption: dict[str, Any] = {
        "schema_version": (
            "semantic-guard-u10-store-activation-authorization-consumption/v1"
        ),
        "consumption_id": (f"consumption.{authorization['authorization_id']}"),
        "record_kind": "activation_authorization_consumption",
        "public_operation": "activate-store",
        "public_identifier": authorization["authorization_id"],
        "authorization_id": authorization["authorization_id"],
        "authorization_digest": authorization["authorization_digest"],
        "store_activation_basis_ref": authorization["store_activation_basis_ref"],
        "transition_kind": authorization["transition_kind"],
        "prior_store_ref": authorization["prior_store_ref"],
        "prior_revocation_ref": authorization["prior_revocation_ref"],
        "target_store_ref": _store_transition_ref_v1(store, store_raw),
        "publisher_contract_binding": _strict_json_clone(publisher_contract_binding),
        "reserved_at": reserved_at,
        "publication_occurred": False,
        "formal_authority": "none",
        "positive_assurance_allowed": False,
    }
    consumption["consumption_digest"] = digest_bytes(canonical_json_bytes(consumption))
    raw = canonical_json_bytes(consumption)
    path = _activation_authorization_consumption_path(
        str(authorization["authorization_id"])
    )
    _atomic_create_once_v1(
        path,
        raw,
        mode=0o444,
        temporary_prefix=(f".{authorization['authorization_id']}.consumption."),
        collision_code="u10_store_activation_consumption_collision",
        create_code="u10_store_activation_consumption_create_failed",
        durability_code="u10_store_activation_ledger_directory_fsync_failed",
    )
    observed, _observed_raw = _load_activation_authorization_consumption_v1(
        store, store_raw, authorization
    )
    return observed


def _try_load_activation_authorization_consumption_v1(
    store: Mapping[str, Any],
    store_raw: bytes,
    authorization: Mapping[str, Any],
) -> tuple[dict[str, Any], bytes] | None:
    path = _activation_authorization_consumption_path(
        str(authorization["authorization_id"])
    )
    try:
        path.lstat()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise BrokerBoundaryError(
            "u10_store_activation_consumption_unavailable", str(path)
        ) from exc
    return _load_activation_authorization_consumption_v1(
        store, store_raw, authorization
    )


def _load_activation_transition_receipt_v1(
    store: Mapping[str, Any],
    store_raw: bytes,
    authorization: Mapping[str, Any],
    consumption: Mapping[str, Any],
) -> tuple[dict[str, Any], bytes]:
    path = _activation_transition_receipt_path(str(authorization["authorization_id"]))
    raw = read_protected_file(path, protected_root=STORE_ACTIVATION_LEDGER_ROOT)
    observed = path.lstat()
    if (
        observed.st_uid != 0
        or observed.st_gid != 0
        or stat.S_IMODE(observed.st_mode) != 0o444
        or observed.st_nlink != 1
    ):
        raise BrokerBoundaryError("u10_store_activation_receipt_untrusted", str(path))
    receipt = _load_json_bytes(raw, "u10_store_activation_receipt_unreadable")
    _validate(
        receipt,
        "u10-store-activation-transition-receipt-v2.schema.json",
        "u10_store_activation_receipt_invalid",
    )
    _sealed_digest(
        receipt,
        "receipt_digest",
        "u10_store_activation_receipt_digest_mismatch",
    )
    _validate_publisher_contract_binding_v1(
        receipt.get("publisher_contract_binding"),
        enforce_current=False,
    )
    if (
        receipt["receipt_id"] != f"receipt.{authorization['authorization_id']}"
        or receipt["public_operation"] != "activate-store"
        or receipt["public_identifier"] != authorization["authorization_id"]
        or receipt["authorization_id"] != authorization["authorization_id"]
        or receipt["authorization_digest"] != authorization["authorization_digest"]
        or receipt["consumption_digest"] != consumption["consumption_digest"]
        or receipt["store_activation_basis_ref"]
        != authorization["store_activation_basis_ref"]
        or receipt["transition_kind"] != authorization["transition_kind"]
        or receipt["prior_store_ref"] != authorization["prior_store_ref"]
        or receipt["prior_revocation_ref"] != authorization["prior_revocation_ref"]
        or receipt["activated_store_ref"] != _store_transition_ref_v1(store, store_raw)
        or receipt["publisher_contract_binding"]
        != consumption["publisher_contract_binding"]
        or receipt["publication_not_before"] != consumption["reserved_at"]
        or _timestamp_v1(
            str(receipt["publication_observed_at"]),
            code="u10_store_activation_receipt_time_invalid",
        )
        < _timestamp_v1(
            str(consumption["reserved_at"]),
            code="u10_store_activation_consumption_time_invalid",
        )
        or _timestamp_v1(
            str(receipt["receipt_recorded_at"]),
            code="u10_store_activation_receipt_time_invalid",
        )
        < _timestamp_v1(
            str(receipt["publication_observed_at"]),
            code="u10_store_activation_receipt_time_invalid",
        )
    ):
        raise BrokerBoundaryError(
            "u10_store_activation_receipt_context_mismatch", str(path)
        )
    return receipt, raw


def _write_activation_transition_receipt_under_lock_v1(
    store: Mapping[str, Any],
    store_raw: bytes,
    authorization: Mapping[str, Any],
    consumption: Mapping[str, Any],
    *,
    publication_observed_at: str,
) -> dict[str, Any]:
    _remove_transaction_temporaries_v1(
        STORE_ACTIVATION_LEDGER_ROOT,
        prefix=f".{authorization['authorization_id']}.receipt.",
        code="u10_store_activation_receipt_create_failed",
    )
    existing = _try_load_activation_transition_receipt_v1(
        store, store_raw, authorization, consumption
    )
    if existing is not None:
        _fsync_directory_v1(
            STORE_ACTIVATION_LEDGER_ROOT,
            code="u10_store_activation_ledger_directory_fsync_failed",
        )
        return existing[0]
    if _timestamp_v1(
        publication_observed_at,
        code="u10_store_activation_receipt_time_invalid",
    ) < _timestamp_v1(
        str(consumption["reserved_at"]),
        code="u10_store_activation_consumption_time_invalid",
    ):
        raise BrokerBoundaryError(
            "u10_store_activation_receipt_chronology_invalid",
            str(authorization["authorization_id"]),
        )
    receipt_recorded_at = _utc_now()
    if _timestamp_v1(
        receipt_recorded_at,
        code="u10_store_activation_receipt_time_invalid",
    ) < _timestamp_v1(
        publication_observed_at,
        code="u10_store_activation_receipt_time_invalid",
    ):
        raise BrokerBoundaryError(
            "u10_store_activation_receipt_chronology_invalid",
            str(authorization["authorization_id"]),
        )
    receipt: dict[str, Any] = {
        "schema_version": ("semantic-guard-u10-store-activation-transition-receipt/v2"),
        "receipt_id": f"receipt.{authorization['authorization_id']}",
        "record_kind": "activation_transition_occurrence",
        "public_operation": "activate-store",
        "public_identifier": authorization["authorization_id"],
        "authorization_id": authorization["authorization_id"],
        "authorization_digest": authorization["authorization_digest"],
        "consumption_digest": consumption["consumption_digest"],
        "store_activation_basis_ref": authorization["store_activation_basis_ref"],
        "transition_kind": authorization["transition_kind"],
        "prior_store_ref": authorization["prior_store_ref"],
        "prior_revocation_ref": authorization["prior_revocation_ref"],
        "activated_store_ref": _store_transition_ref_v1(store, store_raw),
        "publisher_contract_binding": consumption["publisher_contract_binding"],
        "publication_not_before": consumption["reserved_at"],
        "publication_observed_at": publication_observed_at,
        "receipt_recorded_at": receipt_recorded_at,
        "formal_authority": "none",
        "positive_assurance_allowed": False,
    }
    receipt["receipt_digest"] = digest_bytes(canonical_json_bytes(receipt))
    raw = canonical_json_bytes(receipt)
    path = _activation_transition_receipt_path(str(authorization["authorization_id"]))
    _atomic_create_once_v1(
        path,
        raw,
        mode=0o444,
        temporary_prefix=f".{authorization['authorization_id']}.receipt.",
        collision_code="u10_store_activation_receipt_collision",
        create_code="u10_store_activation_receipt_create_failed",
        durability_code="u10_store_activation_ledger_directory_fsync_failed",
    )
    observed, _observed_raw = _load_activation_transition_receipt_v1(
        store, store_raw, authorization, consumption
    )
    return observed


def _try_load_activation_transition_receipt_v1(
    store: Mapping[str, Any],
    store_raw: bytes,
    authorization: Mapping[str, Any],
    consumption: Mapping[str, Any],
) -> tuple[dict[str, Any], bytes] | None:
    path = _activation_transition_receipt_path(str(authorization["authorization_id"]))
    try:
        path.lstat()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise BrokerBoundaryError(
            "u10_store_activation_receipt_unavailable", str(path)
        ) from exc
    return _load_activation_transition_receipt_v1(
        store, store_raw, authorization, consumption
    )


def _read_exact_root_ledger_record_v1(
    path: Path, *, root: Path, code: str
) -> tuple[dict[str, Any], bytes]:
    raw = read_protected_file(path, protected_root=root)
    observed = path.lstat()
    if (
        observed.st_uid != 0
        or observed.st_gid != 0
        or stat.S_IMODE(observed.st_mode) != 0o444
        or observed.st_nlink != 1
    ):
        raise BrokerBoundaryError(code, str(path))
    return _load_json_bytes(raw, code), raw


def _assert_no_competing_activation_consumption_v1(
    authorization: Mapping[str, Any],
) -> None:
    """Reject an unresolved single-use transition from the same prior state."""

    _verify_declared_directory(
        STORE_ACTIVATION_LEDGER_ROOT,
        uid=0,
        gid=0,
        mode=0o755,
        code="u10_store_activation_ledger_directory_mismatch",
    )
    try:
        paths = sorted(
            STORE_ACTIVATION_LEDGER_ROOT.iterdir(), key=lambda item: item.name
        )
    except OSError as exc:
        raise BrokerBoundaryError(
            "u10_store_activation_ledger_unavailable",
            str(STORE_ACTIVATION_LEDGER_ROOT),
        ) from exc
    consumptions: dict[str, dict[str, Any]] = {}
    receipts: dict[str, dict[str, Any]] = {}
    for path in paths:
        matched = re.fullmatch(
            r"([A-Za-z0-9][A-Za-z0-9._-]{0,255})\.(consumption|receipt)\.json",
            path.name,
        )
        if matched is None:
            raise BrokerBoundaryError(
                "u10_store_activation_ledger_denominator_invalid", str(path)
            )
        record_id, kind = matched.groups()
        value, _raw = _read_exact_root_ledger_record_v1(
            path,
            root=STORE_ACTIVATION_LEDGER_ROOT,
            code="u10_store_activation_ledger_record_untrusted",
        )
        if kind == "consumption":
            _validate(
                value,
                "u10-store-activation-authorization-consumption-v1.schema.json",
                "u10_store_activation_consumption_invalid",
            )
            _sealed_digest(
                value,
                "consumption_digest",
                "u10_store_activation_consumption_digest_mismatch",
            )
            if (
                value["authorization_id"] != record_id
                or value["consumption_id"] != f"consumption.{record_id}"
            ):
                raise BrokerBoundaryError(
                    "u10_store_activation_ledger_record_context_mismatch",
                    str(path),
                )
            consumptions[record_id] = value
        else:
            _validate(
                value,
                "u10-store-activation-transition-receipt-v2.schema.json",
                "u10_store_activation_receipt_invalid",
            )
            _sealed_digest(
                value,
                "receipt_digest",
                "u10_store_activation_receipt_digest_mismatch",
            )
            if (
                value["authorization_id"] != record_id
                or value["receipt_id"] != f"receipt.{record_id}"
            ):
                raise BrokerBoundaryError(
                    "u10_store_activation_ledger_record_context_mismatch",
                    str(path),
                )
            receipts[record_id] = value
    if set(receipts) - set(consumptions):
        raise BrokerBoundaryError(
            "u10_store_activation_receipt_without_consumption",
            repr(sorted(set(receipts) - set(consumptions))),
        )
    requested_id = str(authorization["authorization_id"])
    requested_context = (
        authorization["transition_kind"],
        authorization["prior_store_ref"],
        authorization["prior_revocation_ref"],
    )
    for record_id, consumption in consumptions.items():
        receipt = receipts.get(record_id)
        if receipt is not None and (
            receipt["authorization_digest"] != consumption["authorization_digest"]
            or receipt["authorization_id"] != consumption["authorization_id"]
            or receipt["consumption_digest"] != consumption["consumption_digest"]
            or receipt["transition_kind"] != consumption["transition_kind"]
            or receipt["prior_store_ref"] != consumption["prior_store_ref"]
            or receipt["prior_revocation_ref"] != consumption["prior_revocation_ref"]
            or receipt["activated_store_ref"] != consumption["target_store_ref"]
            or receipt["publisher_contract_binding"]
            != consumption["publisher_contract_binding"]
            or receipt["publication_not_before"] != consumption["reserved_at"]
            or _timestamp_v1(
                str(receipt["publication_observed_at"]),
                code="u10_store_activation_receipt_time_invalid",
            )
            < _timestamp_v1(
                str(consumption["reserved_at"]),
                code="u10_store_activation_consumption_time_invalid",
            )
            or _timestamp_v1(
                str(receipt["receipt_recorded_at"]),
                code="u10_store_activation_receipt_time_invalid",
            )
            < _timestamp_v1(
                str(receipt["publication_observed_at"]),
                code="u10_store_activation_receipt_time_invalid",
            )
        ):
            raise BrokerBoundaryError(
                "u10_store_activation_ledger_record_context_mismatch",
                record_id,
            )
        observed_context = (
            consumption["transition_kind"],
            consumption["prior_store_ref"],
            consumption["prior_revocation_ref"],
        )
        if (
            record_id != requested_id
            and receipt is None
            and observed_context == requested_context
        ):
            raise BrokerBoundaryError(
                "u10_competing_activation_consumption_unresolved", record_id
            )


def _load_complete_store_activation_chain_v1(
    store: Mapping[str, Any],
    store_raw: bytes,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    authorization = _validate_store_activation_authorization_v1(store)
    consumption, _consumption_raw = _load_activation_authorization_consumption_v1(
        store, store_raw, authorization
    )
    receipt, _receipt_raw = _load_activation_transition_receipt_v1(
        store, store_raw, authorization, consumption
    )
    return authorization, consumption, receipt


def _validate_store_revocation_value_v1(
    revocation: Mapping[str, Any],
    *,
    store: Mapping[str, Any],
    store_raw: bytes,
    activation_receipt: Mapping[str, Any],
) -> None:
    _validate(
        revocation,
        "u10-store-revocation-record-v1.schema.json",
        "u10_store_revocation_record_invalid",
    )
    _sealed_digest(
        revocation,
        "revocation_digest",
        "u10_store_revocation_record_digest_mismatch",
    )
    if (
        revocation["target_store_id"] != store["store_id"]
        or revocation["target_store_revision_id"] != store["store_revision_id"]
        or revocation["target_store_version"] != store["store_version"]
        or revocation["target_store_activation_basis_digest"]
        != store["store_activation_basis_digest"]
        or revocation["target_store_activation_basis_digest"]
        != store_activation_basis_digest_v2(store)
        or revocation["target_store_artifact_digest"] != digest_bytes(store_raw)
        or revocation["target_store_digest"] != store["store_digest"]
        or revocation["target_activation_receipt_ref"]
        != {
            "receipt_id": activation_receipt["receipt_id"],
            "receipt_digest": activation_receipt["receipt_digest"],
            "publication_observed_at": activation_receipt["publication_observed_at"],
            "receipt_recorded_at": activation_receipt["receipt_recorded_at"],
        }
        or _timestamp_v1(
            str(revocation["recorded_at"]),
            code="u10_store_revocation_time_invalid",
        )
        < _timestamp_v1(
            str(activation_receipt["receipt_recorded_at"]),
            code="u10_store_activation_receipt_time_invalid",
        )
    ):
        raise BrokerBoundaryError(
            "u10_store_revocation_record_context_mismatch",
            str(revocation.get("revocation_id")),
        )


def _load_current_revocation_artifact_unbound_v1() -> (
    tuple[dict[str, Any], bytes] | None
):
    """Read the fixed revocation selector without choosing its target.

    This split is needed for crash-safe store replacement.  A process may die
    after the new current store is selected but before the old store's exact
    revocation selector is removed.  The unbound reader still proves the
    selector and immutable history; the transition authorization decides
    whether it is the one stale selector that may be removed on retry.
    """

    try:
        observed = REVOCATION_SELECTOR_PATH.lstat()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise BrokerBoundaryError(
            "u10_store_revocation_selector_unavailable",
            str(REVOCATION_SELECTOR_PATH),
        ) from exc
    raw = read_protected_file(REVOCATION_SELECTOR_PATH, protected_root=U10_ROOT)
    if (
        observed.st_uid != 0
        or observed.st_gid != 0
        or stat.S_IMODE(observed.st_mode) != 0o444
        or observed.st_nlink != 1
    ):
        raise BrokerBoundaryError(
            "u10_store_revocation_selector_untrusted",
            str(REVOCATION_SELECTOR_PATH),
        )
    revocation = _load_json_bytes(raw, "u10_store_revocation_record_unreadable")
    _validate(
        revocation,
        "u10-store-revocation-record-v1.schema.json",
        "u10_store_revocation_record_invalid",
    )
    _sealed_digest(
        revocation,
        "revocation_digest",
        "u10_store_revocation_record_digest_mismatch",
    )
    artifact_digest = digest_bytes(raw)
    history_path = REVOCATION_ROOT / f"{artifact_digest['value']}.json"
    history_raw = read_protected_file(history_path, protected_root=REVOCATION_ROOT)
    history_observed = history_path.lstat()
    if (
        history_observed.st_uid != 0
        or history_observed.st_gid != 0
        or stat.S_IMODE(history_observed.st_mode) != 0o444
        or history_observed.st_nlink != 1
        or history_raw != raw
    ):
        raise BrokerBoundaryError(
            "u10_store_revocation_history_mismatch", str(history_path)
        )
    return revocation, raw


def _scan_revocation_history_for_store_v1(
    store: Mapping[str, Any],
    store_raw: bytes,
    activation_receipt: Mapping[str, Any],
) -> tuple[dict[str, Any], bytes] | None:
    _verify_declared_directory(
        REVOCATION_ROOT,
        uid=0,
        gid=0,
        mode=0o755,
        code="u10_revocation_history_directory_mismatch",
    )
    matches: list[tuple[dict[str, Any], bytes]] = []
    try:
        paths = sorted(REVOCATION_ROOT.iterdir(), key=lambda path: path.name)
    except OSError as exc:
        raise BrokerBoundaryError(
            "u10_revocation_history_unavailable", str(REVOCATION_ROOT)
        ) from exc
    for path in paths:
        if re.fullmatch(r"[0-9a-f]{64}\.json", path.name) is None:
            raise BrokerBoundaryError(
                "u10_revocation_history_denominator_invalid", str(path)
            )
        raw = read_protected_file(path, protected_root=REVOCATION_ROOT)
        observed = path.lstat()
        if (
            observed.st_uid != 0
            or observed.st_gid != 0
            or stat.S_IMODE(observed.st_mode) != 0o444
            or observed.st_nlink != 1
            or path.name != f"{digest_bytes(raw)['value']}.json"
        ):
            raise BrokerBoundaryError(
                "u10_revocation_history_artifact_invalid", str(path)
            )
        revocation = _load_json_bytes(raw, "u10_store_revocation_record_unreadable")
        _validate(
            revocation,
            "u10-store-revocation-record-v1.schema.json",
            "u10_store_revocation_record_invalid",
        )
        _sealed_digest(
            revocation,
            "revocation_digest",
            "u10_store_revocation_record_digest_mismatch",
        )
        if (
            revocation["target_store_id"] == store["store_id"]
            and revocation["target_store_revision_id"] == store["store_revision_id"]
            and revocation["target_store_version"] == store["store_version"]
        ):
            _validate_store_revocation_value_v1(
                revocation,
                store=store,
                store_raw=store_raw,
                activation_receipt=activation_receipt,
            )
            matches.append((revocation, raw))
    if len(matches) > 1:
        raise BrokerBoundaryError(
            "u10_multiple_revocations_for_store_revision",
            str(store["store_revision_id"]),
        )
    return matches[0] if matches else None


def _activation_receipt_ref_v1(
    receipt: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "receipt_id": receipt["receipt_id"],
        "receipt_digest": receipt["receipt_digest"],
        "publication_observed_at": receipt["publication_observed_at"],
        "receipt_recorded_at": receipt["receipt_recorded_at"],
    }


def _revocation_consumption_path_v1(revocation_id: str) -> Path:
    return REVOCATION_LEDGER_ROOT / f"{revocation_id}.consumption.json"


def _revocation_publication_receipt_path_v1(revocation_id: str) -> Path:
    return REVOCATION_LEDGER_ROOT / f"{revocation_id}.receipt.json"


def _validate_revocation_ledger_contract_v1(
    store: Mapping[str, Any],
) -> None:
    selector = store["current_selector"]
    if (
        selector["revocation_ledger_path"] != str(REVOCATION_LEDGER_ROOT)
        or selector["revocation_ledger_policy"]
        != STORE_REVOCATION_LEDGER_POLICY_V2
        or selector["revocation_ledger_retention_policy"]
        != STORE_LEDGER_RETENTION_POLICY_V1
    ):
        raise BrokerBoundaryError(
            "u10_store_revocation_ledger_contract_mismatch",
            str(selector.get("revocation_ledger_path")),
        )
    _verify_declared_directory(
        REVOCATION_LEDGER_ROOT,
        uid=0,
        gid=0,
        mode=0o755,
        code="u10_store_revocation_ledger_directory_mismatch",
    )


def _load_revocation_consumption_v1(
    store: Mapping[str, Any],
    store_raw: bytes,
    revocation: Mapping[str, Any],
    activation_receipt: Mapping[str, Any],
) -> tuple[dict[str, Any], bytes]:
    _validate_revocation_ledger_contract_v1(store)
    path = _revocation_consumption_path_v1(str(revocation["revocation_id"]))
    raw = read_protected_file(path, protected_root=REVOCATION_LEDGER_ROOT)
    observed = path.lstat()
    if (
        observed.st_uid != 0
        or observed.st_gid != 0
        or stat.S_IMODE(observed.st_mode) != 0o444
        or observed.st_nlink != 1
    ):
        raise BrokerBoundaryError(
            "u10_store_revocation_consumption_untrusted", str(path)
        )
    value = _load_json_bytes(raw, "u10_store_revocation_consumption_unreadable")
    _validate(
        value,
        "u10-store-revocation-authorization-consumption-v1.schema.json",
        "u10_store_revocation_consumption_invalid",
    )
    _sealed_digest(
        value,
        "consumption_digest",
        "u10_store_revocation_consumption_digest_mismatch",
    )
    _validate_publisher_contract_binding_v1(
        value.get("publisher_contract_binding"),
        enforce_current=False,
    )
    if (
        value["consumption_id"] != f"consumption.{revocation['revocation_id']}"
        or value["revocation_id"] != revocation["revocation_id"]
        or value["revocation_digest"] != revocation["revocation_digest"]
        or value["target_store_ref"] != _store_transition_ref_v1(store, store_raw)
        or value["target_activation_receipt_ref"]
        != _activation_receipt_ref_v1(activation_receipt)
        or _timestamp_v1(
            str(value["consumed_at"]),
            code="u10_store_revocation_consumption_time_invalid",
        )
        < _timestamp_v1(
            str(revocation["recorded_at"]),
            code="u10_store_revocation_time_invalid",
        )
    ):
        raise BrokerBoundaryError(
            "u10_store_revocation_consumption_context_mismatch", str(path)
        )
    return value, raw


def _try_load_revocation_consumption_v1(
    store: Mapping[str, Any],
    store_raw: bytes,
    revocation: Mapping[str, Any],
    activation_receipt: Mapping[str, Any],
) -> tuple[dict[str, Any], bytes] | None:
    path = _revocation_consumption_path_v1(str(revocation["revocation_id"]))
    try:
        path.lstat()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise BrokerBoundaryError(
            "u10_store_revocation_consumption_unavailable", str(path)
        ) from exc
    return _load_revocation_consumption_v1(
        store, store_raw, revocation, activation_receipt
    )


def _write_revocation_consumption_under_lock_v1(
    store: Mapping[str, Any],
    store_raw: bytes,
    revocation: Mapping[str, Any],
    activation_receipt: Mapping[str, Any],
    publisher_contract_binding: Mapping[str, Any],
) -> dict[str, Any]:
    _validate_revocation_ledger_contract_v1(store)
    existing = _try_load_revocation_consumption_v1(
        store, store_raw, revocation, activation_receipt
    )
    if existing is not None:
        _fsync_directory_v1(
            REVOCATION_LEDGER_ROOT,
            code="u10_store_revocation_ledger_directory_fsync_failed",
        )
        return existing[0]
    consumed_at = _utc_now()
    if _timestamp_v1(
        consumed_at,
        code="u10_store_revocation_consumption_time_invalid",
    ) < _timestamp_v1(
        str(revocation["recorded_at"]),
        code="u10_store_revocation_time_invalid",
    ):
        raise BrokerBoundaryError(
            "u10_store_revocation_consumption_chronology_invalid",
            str(revocation["revocation_id"]),
        )
    value: dict[str, Any] = {
        "schema_version": (
            "semantic-guard-u10-store-revocation-authorization-consumption/v1"
        ),
        "consumption_id": f"consumption.{revocation['revocation_id']}",
        "record_kind": "revocation_authorization_consumption",
        "revocation_id": revocation["revocation_id"],
        "revocation_digest": revocation["revocation_digest"],
        "target_store_ref": _store_transition_ref_v1(store, store_raw),
        "target_activation_receipt_ref": _activation_receipt_ref_v1(activation_receipt),
        "publisher_contract_binding": _strict_json_clone(publisher_contract_binding),
        "consumed_at": consumed_at,
        "publication_occurred": False,
        "formal_authority": "none",
        "positive_assurance_allowed": False,
    }
    value["consumption_digest"] = digest_bytes(canonical_json_bytes(value))
    raw = canonical_json_bytes(value)
    _atomic_create_once_v1(
        _revocation_consumption_path_v1(str(revocation["revocation_id"])),
        raw,
        mode=0o444,
        temporary_prefix=f".{revocation['revocation_id']}.consumption.",
        collision_code="u10_store_revocation_consumption_collision",
        create_code="u10_store_revocation_consumption_create_failed",
        durability_code="u10_store_revocation_ledger_directory_fsync_failed",
    )
    observed, _ = _load_revocation_consumption_v1(
        store, store_raw, revocation, activation_receipt
    )
    return observed


def _revocation_history_ref_v1(raw: bytes) -> dict[str, Any]:
    artifact_digest = digest_bytes(raw)
    return {
        "locator": str(REVOCATION_ROOT / f"{artifact_digest['value']}.json"),
        "artifact_digest": artifact_digest,
    }


def _load_revocation_publication_receipt_v1(
    store: Mapping[str, Any],
    store_raw: bytes,
    revocation: Mapping[str, Any],
    revocation_raw: bytes,
    activation_receipt: Mapping[str, Any],
    consumption: Mapping[str, Any],
) -> tuple[dict[str, Any], bytes]:
    _validate_revocation_ledger_contract_v1(store)
    path = _revocation_publication_receipt_path_v1(str(revocation["revocation_id"]))
    raw = read_protected_file(path, protected_root=REVOCATION_LEDGER_ROOT)
    observed = path.lstat()
    if (
        observed.st_uid != 0
        or observed.st_gid != 0
        or stat.S_IMODE(observed.st_mode) != 0o444
        or observed.st_nlink != 1
    ):
        raise BrokerBoundaryError("u10_store_revocation_receipt_untrusted", str(path))
    value = _load_json_bytes(raw, "u10_store_revocation_receipt_unreadable")
    _validate(
        value,
        "u10-store-revocation-publication-receipt-v2.schema.json",
        "u10_store_revocation_receipt_invalid",
    )
    _sealed_digest(
        value,
        "receipt_digest",
        "u10_store_revocation_receipt_digest_mismatch",
    )
    _validate_publisher_contract_binding_v1(
        value.get("publisher_contract_binding"),
        enforce_current=False,
    )
    if (
        value["receipt_id"] != f"receipt.{revocation['revocation_id']}"
        or value["revocation_id"] != revocation["revocation_id"]
        or value["revocation_digest"] != revocation["revocation_digest"]
        or value["consumption_digest"] != consumption["consumption_digest"]
        or value["target_store_ref"] != _store_transition_ref_v1(store, store_raw)
        or value["target_activation_receipt_ref"]
        != _activation_receipt_ref_v1(activation_receipt)
        or value["history_ref"] != _revocation_history_ref_v1(revocation_raw)
        or value["publisher_contract_binding"]
        != consumption["publisher_contract_binding"]
        or value["publication_not_before"] != consumption["consumed_at"]
        or _timestamp_v1(
            str(value["publication_observed_at"]),
            code="u10_store_revocation_receipt_time_invalid",
        )
        < _timestamp_v1(
            str(consumption["consumed_at"]),
            code="u10_store_revocation_consumption_time_invalid",
        )
        or _timestamp_v1(
            str(value["receipt_recorded_at"]),
            code="u10_store_revocation_receipt_time_invalid",
        )
        < _timestamp_v1(
            str(value["publication_observed_at"]),
            code="u10_store_revocation_receipt_time_invalid",
        )
    ):
        raise BrokerBoundaryError(
            "u10_store_revocation_receipt_context_mismatch", str(path)
        )
    return value, raw


def _try_load_revocation_publication_receipt_v1(
    store: Mapping[str, Any],
    store_raw: bytes,
    revocation: Mapping[str, Any],
    revocation_raw: bytes,
    activation_receipt: Mapping[str, Any],
    consumption: Mapping[str, Any],
) -> tuple[dict[str, Any], bytes] | None:
    path = _revocation_publication_receipt_path_v1(str(revocation["revocation_id"]))
    try:
        path.lstat()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise BrokerBoundaryError(
            "u10_store_revocation_receipt_unavailable", str(path)
        ) from exc
    return _load_revocation_publication_receipt_v1(
        store,
        store_raw,
        revocation,
        revocation_raw,
        activation_receipt,
        consumption,
    )


def _write_revocation_publication_receipt_under_lock_v1(
    store: Mapping[str, Any],
    store_raw: bytes,
    revocation: Mapping[str, Any],
    revocation_raw: bytes,
    activation_receipt: Mapping[str, Any],
    consumption: Mapping[str, Any],
    *,
    publication_observed_at: str,
) -> dict[str, Any]:
    existing = _try_load_revocation_publication_receipt_v1(
        store,
        store_raw,
        revocation,
        revocation_raw,
        activation_receipt,
        consumption,
    )
    if existing is not None:
        _fsync_directory_v1(
            REVOCATION_LEDGER_ROOT,
            code="u10_store_revocation_ledger_directory_fsync_failed",
        )
        return existing[0]
    if _timestamp_v1(
        publication_observed_at,
        code="u10_store_revocation_receipt_time_invalid",
    ) < _timestamp_v1(
        str(consumption["consumed_at"]),
        code="u10_store_revocation_consumption_time_invalid",
    ):
        raise BrokerBoundaryError(
            "u10_store_revocation_receipt_chronology_invalid",
            str(revocation["revocation_id"]),
        )
    receipt_recorded_at = _utc_now()
    if _timestamp_v1(
        receipt_recorded_at,
        code="u10_store_revocation_receipt_time_invalid",
    ) < _timestamp_v1(
        publication_observed_at,
        code="u10_store_revocation_receipt_time_invalid",
    ):
        raise BrokerBoundaryError(
            "u10_store_revocation_receipt_chronology_invalid",
            str(revocation["revocation_id"]),
        )
    value: dict[str, Any] = {
        "schema_version": (
            "semantic-guard-u10-store-revocation-publication-receipt/v2"
        ),
        "receipt_id": f"receipt.{revocation['revocation_id']}",
        "record_kind": "revocation_publication_occurrence",
        "publisher_operation_id": ("semantic-guard.u10.publish-store-revocation.v1"),
        "publisher_euid": 0,
        "revocation_id": revocation["revocation_id"],
        "revocation_digest": revocation["revocation_digest"],
        "consumption_digest": consumption["consumption_digest"],
        "target_store_ref": _store_transition_ref_v1(store, store_raw),
        "target_activation_receipt_ref": _activation_receipt_ref_v1(activation_receipt),
        "history_ref": _revocation_history_ref_v1(revocation_raw),
        "publisher_contract_binding": consumption["publisher_contract_binding"],
        "selector_path": str(REVOCATION_SELECTOR_PATH),
        "publication_not_before": consumption["consumed_at"],
        "publication_observed_at": publication_observed_at,
        "receipt_recorded_at": receipt_recorded_at,
        "formal_authority": "none",
        "positive_assurance_allowed": False,
    }
    value["receipt_digest"] = digest_bytes(canonical_json_bytes(value))
    raw = canonical_json_bytes(value)
    _atomic_create_once_v1(
        _revocation_publication_receipt_path_v1(str(revocation["revocation_id"])),
        raw,
        mode=0o444,
        temporary_prefix=f".{revocation['revocation_id']}.receipt.",
        collision_code="u10_store_revocation_receipt_collision",
        create_code="u10_store_revocation_receipt_create_failed",
        durability_code="u10_store_revocation_ledger_directory_fsync_failed",
    )
    observed, _ = _load_revocation_publication_receipt_v1(
        store,
        store_raw,
        revocation,
        revocation_raw,
        activation_receipt,
        consumption,
    )
    return observed


def _load_complete_revocation_publication_chain_v1(
    store: Mapping[str, Any],
    store_raw: bytes,
    revocation: Mapping[str, Any],
    revocation_raw: bytes,
    activation_receipt: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    consumption, _ = _load_revocation_consumption_v1(
        store, store_raw, revocation, activation_receipt
    )
    receipt, _ = _load_revocation_publication_receipt_v1(
        store,
        store_raw,
        revocation,
        revocation_raw,
        activation_receipt,
        consumption,
    )
    return consumption, receipt


def _assert_no_competing_revocation_consumption_v1(
    *,
    requested_revocation_id: str,
    store: Mapping[str, Any],
    store_raw: bytes,
    activation_receipt: Mapping[str, Any],
) -> None:
    """Reject any other consumed decision for the same exact active store."""

    _validate_revocation_ledger_contract_v1(store)
    try:
        paths = sorted(REVOCATION_LEDGER_ROOT.iterdir(), key=lambda item: item.name)
    except OSError as exc:
        raise BrokerBoundaryError(
            "u10_store_revocation_ledger_unavailable",
            str(REVOCATION_LEDGER_ROOT),
        ) from exc
    consumptions: dict[str, dict[str, Any]] = {}
    receipts: dict[str, dict[str, Any]] = {}
    for path in paths:
        matched = re.fullmatch(
            r"([A-Za-z0-9][A-Za-z0-9._-]{0,255})\.(consumption|receipt)\.json",
            path.name,
        )
        if matched is None:
            raise BrokerBoundaryError(
                "u10_store_revocation_ledger_denominator_invalid", str(path)
            )
        record_id, kind = matched.groups()
        value, _raw = _read_exact_root_ledger_record_v1(
            path,
            root=REVOCATION_LEDGER_ROOT,
            code="u10_store_revocation_ledger_record_untrusted",
        )
        if kind == "consumption":
            _validate(
                value,
                "u10-store-revocation-authorization-consumption-v1.schema.json",
                "u10_store_revocation_consumption_invalid",
            )
            _sealed_digest(
                value,
                "consumption_digest",
                "u10_store_revocation_consumption_digest_mismatch",
            )
            if (
                value["revocation_id"] != record_id
                or value["consumption_id"] != f"consumption.{record_id}"
            ):
                raise BrokerBoundaryError(
                    "u10_store_revocation_ledger_record_context_mismatch",
                    str(path),
                )
            consumptions[record_id] = value
        else:
            _validate(
                value,
                "u10-store-revocation-publication-receipt-v2.schema.json",
                "u10_store_revocation_receipt_invalid",
            )
            _sealed_digest(
                value,
                "receipt_digest",
                "u10_store_revocation_receipt_digest_mismatch",
            )
            if (
                value["revocation_id"] != record_id
                or value["receipt_id"] != f"receipt.{record_id}"
            ):
                raise BrokerBoundaryError(
                    "u10_store_revocation_ledger_record_context_mismatch",
                    str(path),
                )
            receipts[record_id] = value
    if set(receipts) - set(consumptions):
        raise BrokerBoundaryError(
            "u10_store_revocation_receipt_without_consumption",
            repr(sorted(set(receipts) - set(consumptions))),
        )
    target_store_ref = _store_transition_ref_v1(store, store_raw)
    target_activation_ref = _activation_receipt_ref_v1(activation_receipt)
    for record_id, consumption in consumptions.items():
        receipt = receipts.get(record_id)
        if receipt is not None and (
            receipt["revocation_id"] != consumption["revocation_id"]
            or receipt["consumption_digest"] != consumption["consumption_digest"]
            or receipt["revocation_digest"] != consumption["revocation_digest"]
            or receipt["target_store_ref"] != consumption["target_store_ref"]
            or receipt["target_activation_receipt_ref"]
            != consumption["target_activation_receipt_ref"]
            or receipt["publisher_contract_binding"]
            != consumption["publisher_contract_binding"]
            or receipt["publication_not_before"] != consumption["consumed_at"]
            or _timestamp_v1(
                str(receipt["publication_observed_at"]),
                code="u10_store_revocation_receipt_time_invalid",
            )
            < _timestamp_v1(
                str(consumption["consumed_at"]),
                code="u10_store_revocation_consumption_time_invalid",
            )
            or _timestamp_v1(
                str(receipt["receipt_recorded_at"]),
                code="u10_store_revocation_receipt_time_invalid",
            )
            < _timestamp_v1(
                str(receipt["publication_observed_at"]),
                code="u10_store_revocation_receipt_time_invalid",
            )
        ):
            raise BrokerBoundaryError(
                "u10_store_revocation_ledger_record_context_mismatch",
                record_id,
            )
        if (
            record_id != requested_revocation_id
            and consumption["target_store_ref"] == target_store_ref
            and consumption["target_activation_receipt_ref"] == target_activation_ref
        ):
            raise BrokerBoundaryError(
                (
                    "u10_competing_revocation_consumption_unresolved"
                    if receipt is None
                    else "u10_competing_revocation_publication_completed"
                ),
                record_id,
            )


def load_current_store_revocation_v1(
    store: Mapping[str, Any],
    store_raw: bytes,
    *,
    activation_receipt: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], bytes] | None:
    """Load the separately published disposition for the exact active store.

    Absence means no local revocation has been published.  Presence must be an
    exact root-owned selector and must have an identical content-addressed
    history original; malformed or stale selectors never become revocation.
    """

    if store["current_selector"]["revocation_selector_path"] != str(
        REVOCATION_SELECTOR_PATH
    ) or store["current_selector"]["revocation_history_path"] != str(REVOCATION_ROOT):
        raise BrokerBoundaryError("u10_revocation_root_path_mismatch", "fixed paths")
    if activation_receipt is None:
        activation_receipt = _load_complete_store_activation_chain_v1(store, store_raw)[
            2
        ]
    history_result = _scan_revocation_history_for_store_v1(
        store, store_raw, activation_receipt
    )
    selector_result = _load_current_revocation_artifact_unbound_v1()
    if history_result is None and selector_result is None:
        return None
    if history_result is None or selector_result is None:
        raise BrokerBoundaryError(
            "u10_revocation_publication_incomplete",
            str(REVOCATION_SELECTOR_PATH),
        )
    revocation, raw = history_result
    if selector_result[1] != raw:
        raise BrokerBoundaryError(
            "u10_revocation_selector_history_mismatch",
            str(REVOCATION_SELECTOR_PATH),
        )
    _decision, decision_raw = _load_root_revocation_decision_v1(
        str(revocation["revocation_id"]),
        store=store,
        store_raw=store_raw,
        activation_receipt=activation_receipt,
    )
    if decision_raw != raw:
        raise BrokerBoundaryError(
            "u10_store_revocation_decision_history_mismatch",
            str(revocation["revocation_id"]),
        )
    _load_complete_revocation_publication_chain_v1(
        store, store_raw, revocation, raw, activation_receipt
    )
    return revocation, raw


def _existing_revocation_selector_is_removable() -> bool:
    try:
        observed = REVOCATION_SELECTOR_PATH.lstat()
    except FileNotFoundError:
        return False
    except OSError as exc:
        raise BrokerBoundaryError(
            "u10_store_revocation_selector_unavailable",
            str(REVOCATION_SELECTOR_PATH),
        ) from exc
    if (
        stat.S_ISLNK(observed.st_mode)
        or not stat.S_ISREG(observed.st_mode)
        or observed.st_uid != 0
        or observed.st_gid != 0
        or stat.S_IMODE(observed.st_mode) != 0o444
        or observed.st_nlink != 1
    ):
        raise BrokerBoundaryError(
            "u10_store_revocation_selector_untrusted",
            str(REVOCATION_SELECTOR_PATH),
        )
    return True


def load_fixed_root_trust_store_record_v2() -> tuple[dict[str, Any], bytes]:
    """Read the current selector without claiming it is executable or current."""

    raw = read_protected_file(TRUST_STORE_PATH, protected_root=U10_ROOT)
    observed = TRUST_STORE_PATH.lstat()
    if (
        observed.st_uid != 0
        or observed.st_gid != 0
        or stat.S_IMODE(observed.st_mode) != 0o444
        or observed.st_nlink != 1
    ):
        raise BrokerBoundaryError(
            "u10_current_store_artifact_untrusted", str(TRUST_STORE_PATH)
        )
    store = _load_json_bytes(raw, "u10_root_trust_store_unreadable")
    validate_root_trust_store_v2(store)
    if store["current_selector"]["path"] != str(TRUST_STORE_PATH):
        raise BrokerBoundaryError("u10_current_store_path_mismatch", "fixed path")
    return store, raw


def derive_historical_store_ref_v2(
    store: Mapping[str, Any],
    raw: bytes,
) -> dict[str, Any]:
    artifact_digest = digest_bytes(raw)
    return {
        "schema_version": "semantic-guard-u10-root-trust-store/v2",
        "store_id": store["store_id"],
        "store_revision_id": store["store_revision_id"],
        "store_version": store["store_version"],
        "lifecycle_state": "active",
        "locator": str(TRUST_STORE_HISTORY_ROOT / f"{artifact_digest['value']}.json"),
        "artifact_digest": artifact_digest,
        "semantic_digest": store["store_digest"],
        "basis_role": "current_at_attestation",
    }


def load_historical_root_trust_store_v2(
    reference: Mapping[str, Any],
) -> tuple[dict[str, Any], bytes]:
    expected_fields = {
        "schema_version",
        "store_id",
        "store_revision_id",
        "store_version",
        "lifecycle_state",
        "locator",
        "artifact_digest",
        "semantic_digest",
        "basis_role",
    }
    if set(reference) != expected_fields:
        raise BrokerBoundaryError("u10_historical_store_ref_invalid", repr(reference))
    artifact_digest = reference.get("artifact_digest")
    if (
        reference.get("schema_version") != "semantic-guard-u10-root-trust-store/v2"
        or reference.get("lifecycle_state") != "active"
        or reference.get("basis_role") != "current_at_attestation"
        or not isinstance(artifact_digest, Mapping)
        or artifact_digest.get("algorithm") != "sha256"
    ):
        raise BrokerBoundaryError("u10_historical_store_ref_invalid", repr(reference))
    path = Path(str(reference["locator"]))
    expected_path = TRUST_STORE_HISTORY_ROOT / f"{artifact_digest.get('value')}.json"
    if path != expected_path:
        raise BrokerBoundaryError("u10_historical_store_path_mismatch", str(path))
    raw = read_protected_file(path, protected_root=TRUST_STORE_HISTORY_ROOT)
    observed = path.lstat()
    if (
        observed.st_uid != 0
        or observed.st_gid != 0
        or stat.S_IMODE(observed.st_mode) != 0o444
        or observed.st_nlink != 1
        or digest_bytes(raw) != artifact_digest
    ):
        raise BrokerBoundaryError("u10_historical_store_artifact_mismatch", str(path))
    store = _load_json_bytes(raw, "u10_historical_store_unreadable")
    validate_root_trust_store_v2(store)
    _verify_declared_directory(
        TRUST_STORE_HISTORY_ROOT,
        uid=int(store["trust_store_history"]["owner_uid"]),
        gid=int(store["trust_store_history"]["owner_gid"]),
        mode=int(store["trust_store_history"]["directory_mode"], 8),
        code="u10_history_directory_mismatch",
    )
    if (
        store["schema_version"] != reference["schema_version"]
        or store["store_id"] != reference["store_id"]
        or store["store_revision_id"] != reference["store_revision_id"]
        or store["store_version"] != reference["store_version"]
        or store["lifecycle_state"] != reference["lifecycle_state"]
        or store["store_digest"] != reference["semantic_digest"]
    ):
        raise BrokerBoundaryError("u10_historical_store_context_mismatch", str(path))
    return store, raw


def _verify_current_selector_contract_v1(store: Mapping[str, Any]) -> None:
    selector = store["current_selector"]
    expected = {
        "path": str(TRUST_STORE_PATH),
        "publication_policy": ("history_fsync_before_atomic_current_replace/v1"),
        "activation_ledger_path": str(STORE_ACTIVATION_LEDGER_ROOT),
        "activation_ledger_policy": STORE_ACTIVATION_LEDGER_POLICY_V3,
        "activation_ledger_retention_policy": STORE_LEDGER_RETENTION_POLICY_V1,
        "revocation_selector_path": str(REVOCATION_SELECTOR_PATH),
        "revocation_history_path": str(REVOCATION_ROOT),
        "revocation_ledger_path": str(REVOCATION_LEDGER_ROOT),
        "revocation_ledger_policy": STORE_REVOCATION_LEDGER_POLICY_V2,
        "revocation_ledger_retention_policy": STORE_LEDGER_RETENTION_POLICY_V1,
        "revocation_decision_root_path": str(AUTHORIZATION_ROOT),
        "revocation_decision_entry_policy": (
            "fixed_root_record_id_resolution_no_caller_raw/v1"
        ),
        "revocation_publication_policy": (
            "decision_consumption_history_selector_interval_receipt_recovery/v4"
        ),
    }
    for field, value in expected.items():
        if selector[field] != value:
            raise BrokerBoundaryError(
                "u10_current_selector_contract_mismatch",
                f"{field}: {selector[field]!r}",
            )


def _load_current_store_activation_context_v1(
    *,
    allow_missing_receipt: bool = False,
) -> (
    tuple[
        dict[str, Any],
        bytes,
        dict[str, Any],
        dict[str, Any],
        tuple[dict[str, Any], bytes] | None,
        tuple[dict[str, Any], bytes] | None,
    ]
    | None
):
    """Resolve the exact current store, its consumed authorization and history.

    The revocation selector is returned after structural/history validation but
    before target binding.  Publication retry needs to distinguish a revocation
    of the current store from the one exact stale selector named by a completed
    replacement authorization.
    """

    validate_directory_chain(U10_ROOT, U10_ROOT)
    try:
        TRUST_STORE_PATH.lstat()
    except FileNotFoundError:
        if _load_current_revocation_artifact_unbound_v1() is not None:
            raise BrokerBoundaryError(
                "u10_revocation_without_current_store",
                str(REVOCATION_SELECTOR_PATH),
            )
        return None
    except OSError as exc:
        raise BrokerBoundaryError(
            "u10_current_store_unavailable", str(TRUST_STORE_PATH)
        ) from exc

    store, raw = load_fixed_root_trust_store_record_v2()
    if store["lifecycle_state"] != "active":
        raise BrokerBoundaryError(
            "u10_root_trust_store_not_active",
            str(store["lifecycle_state"]),
        )
    _verify_current_selector_contract_v1(store)
    authorization = _validate_store_activation_authorization_v1(store)
    consumption, _consumption_raw = _load_activation_authorization_consumption_v1(
        store, raw, authorization
    )
    if allow_missing_receipt:
        receipt = _try_load_activation_transition_receipt_v1(
            store, raw, authorization, consumption
        )
    else:
        receipt = _load_activation_transition_receipt_v1(
            store, raw, authorization, consumption
        )
    historical_store, historical_raw = load_historical_root_trust_store_v2(
        derive_historical_store_ref_v2(store, raw)
    )
    if historical_store != store or historical_raw != raw:
        raise BrokerBoundaryError(
            "u10_current_history_mismatch", str(store["store_revision_id"])
        )
    if allow_missing_receipt:
        revocation = _load_current_revocation_artifact_unbound_v1()
    else:
        revocation = load_current_store_revocation_v1(
            store,
            raw,
            activation_receipt=receipt[0],
        )
    return store, raw, authorization, consumption, receipt, revocation


def _validate_prior_revocation_binding_v1(
    prior_store: Mapping[str, Any],
    prior_store_raw: bytes,
    prior_revocation: tuple[Mapping[str, Any], bytes] | None,
    activation_receipt: Mapping[str, Any],
) -> None:
    if prior_revocation is None:
        return
    _validate_store_revocation_value_v1(
        prior_revocation[0],
        store=prior_store,
        store_raw=prior_store_raw,
        activation_receipt=activation_receipt,
    )
    _load_complete_revocation_publication_chain_v1(
        prior_store,
        prior_store_raw,
        prior_revocation[0],
        prior_revocation[1],
        activation_receipt,
    )


def _remove_exact_revocation_selector_under_lock_v1(
    expected_ref: Mapping[str, Any],
) -> None:
    observed = _load_current_revocation_artifact_unbound_v1()
    if observed is None or _revocation_transition_ref_v1(*observed) != expected_ref:
        raise BrokerBoundaryError(
            "u10_revocation_selector_transition_mismatch",
            str(REVOCATION_SELECTOR_PATH),
        )
    try:
        REVOCATION_SELECTOR_PATH.unlink()
    except OSError as exc:
        raise BrokerBoundaryError(
            "u10_revocation_selector_remove_failed",
            str(REVOCATION_SELECTOR_PATH),
        ) from exc
    directory_fd = os.open(
        U10_ROOT,
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
    )
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
    try:
        REVOCATION_SELECTOR_PATH.lstat()
    except FileNotFoundError:
        return
    except OSError as exc:
        raise BrokerBoundaryError(
            "u10_revocation_selector_post_remove_unavailable",
            str(REVOCATION_SELECTOR_PATH),
        ) from exc
    raise BrokerBoundaryError(
        "u10_revocation_selector_post_remove_mismatch",
        str(REVOCATION_SELECTOR_PATH),
    )


def _seal_root_trust_store_history_under_lock_v2(
    store: Mapping[str, Any],
    raw: bytes,
) -> dict[str, Any]:
    reference = derive_historical_store_ref_v2(store, raw)
    path = Path(str(reference["locator"]))
    _verify_declared_directory(
        TRUST_STORE_HISTORY_ROOT,
        uid=0,
        gid=0,
        mode=0o755,
        code="u10_history_directory_mismatch",
    )
    _atomic_create_once_v1(
        path,
        raw,
        mode=0o444,
        temporary_prefix=f".{reference['artifact_digest']['value']}.history.",
        collision_code="u10_history_collision",
        create_code="u10_history_create_failed",
        durability_code="u10_history_directory_fsync_failed",
    )
    historical_store, historical_raw = load_historical_root_trust_store_v2(reference)
    if historical_store != store or historical_raw != raw:
        raise BrokerBoundaryError("u10_history_post_write_mismatch", str(path))
    return reference


def seal_root_trust_store_history_v2(raw: bytes) -> dict[str, Any]:
    """Create the immutable history original before an activator publishes it."""

    if os.geteuid() != 0:
        raise BrokerBoundaryError("u10_root_broker_requires_root", str(os.geteuid()))
    store = _load_json_bytes(raw, "u10_root_trust_store_unreadable")
    validate_root_trust_store_v2(store)
    if store["lifecycle_state"] != "active":
        raise BrokerBoundaryError(
            "u10_root_trust_store_not_active", str(store["lifecycle_state"])
        )
    _verify_current_selector_contract_v1(store)
    authorization = _validate_store_activation_authorization_v1(store)
    _load_store_activation_basis_v2(authorization["store_activation_basis_ref"])
    with trust_store_coordination_lock(exclusive=True):
        authorization = _validate_store_activation_authorization_v1(store)
        _load_store_activation_basis_v2(authorization["store_activation_basis_ref"])
        _cleanup_activation_transaction_temporaries_under_lock_v1(
            str(authorization["authorization_id"])
        )
        _cleanup_current_activation_temporaries_under_lock_v1()
        _assert_no_competing_activation_consumption_v1(authorization)
        current = _load_current_store_activation_context_v1(allow_missing_receipt=True)
        if current is not None and current[1] == raw:
            return derive_historical_store_ref_v2(store, raw)
        prior_store = current[0] if current is not None else None
        prior_store_raw = current[1] if current is not None else None
        prior_revocation = current[5] if current is not None else None
        if prior_store is not None and prior_store_raw is not None:
            if current[4] is None:
                receipt_tuple = _load_activation_transition_receipt_v1(
                    prior_store,
                    prior_store_raw,
                    current[2],
                    current[3],
                )
            else:
                receipt_tuple = current[4]
            _validate_prior_revocation_binding_v1(
                prior_store,
                prior_store_raw,
                prior_revocation,
                receipt_tuple[0],
            )
            if (
                prior_store["store_id"] == store["store_id"]
                and prior_store["store_revision_id"] == store["store_revision_id"]
            ):
                raise BrokerBoundaryError(
                    "u10_same_store_revision_content_changed",
                    str(store["store_revision_id"]),
                )
        _validate_store_activation_transition_v1(
            authorization,
            prior_store=prior_store,
            prior_store_raw=prior_store_raw,
            prior_revocation=prior_revocation,
        )
        _try_load_activation_authorization_consumption_v1(store, raw, authorization)
        return _seal_root_trust_store_history_under_lock_v2(store, raw)


def _publish_active_root_trust_store_bytes_v2(
    raw: bytes,
    publisher_contract_binding: Mapping[str, Any],
) -> dict[str, Any]:
    """Consume one exact transition authorization, then select its store.

    The append-only consumption record is durable before current replacement.
    This makes a crash retryable without making an authorization reusable for a
    different prior state.  A result is executable only when the fixed current
    selector, consumption record, immutable history and absence of an exact
    current-store revocation all agree.
    """

    _validate_publisher_contract_binding_v1(
        publisher_contract_binding, enforce_current=True
    )
    if os.geteuid() != 0:
        raise BrokerBoundaryError("u10_root_broker_requires_root", str(os.geteuid()))
    store = _load_json_bytes(raw, "u10_root_trust_store_unreadable")
    validate_root_trust_store_v2(store)
    if (
        store["lifecycle_state"] != "active"
        or store["broker_runtime_version"] != BROKER_VERSION
        or store["current_selector"]["path"] != str(TRUST_STORE_PATH)
    ):
        raise BrokerBoundaryError(
            "u10_store_not_publishable", store["store_revision_id"]
        )
    _verify_current_selector_contract_v1(store)
    authorization = _validate_store_activation_authorization_v1(store)
    _load_store_activation_basis_v2(authorization["store_activation_basis_ref"])
    for binding, path, mode_field in (
        (store["snapshot_root"], SNAPSHOT_ROOT, "mode"),
        (store["result_spool"], EVIDENCE_SPOOL_ROOT, "mode"),
        (store["trust_store_history"], TRUST_STORE_HISTORY_ROOT, "directory_mode"),
    ):
        _verify_declared_directory(
            path,
            uid=int(binding["owner_uid"]),
            gid=int(binding["owner_gid"]),
            mode=int(binding[mode_field], 8),
            code="u10_publish_store_directory_mismatch",
        )
    _verify_declared_directory(
        NONCE_LEDGER_ROOT,
        uid=int(store["nonce_ledger"]["owner_uid"]),
        gid=int(store["nonce_ledger"]["owner_gid"]),
        mode=int(store["nonce_ledger"]["directory_mode"], 8),
        code="u10_publish_store_directory_mismatch",
    )
    runtime_raw = _verify_root_artifact(store["broker_runtime_ref"])
    if store["broker_runtime_ref"]["semantic_digest"] != digest_bytes(runtime_raw):
        raise BrokerBoundaryError(
            "u10_publish_broker_runtime_mismatch", store["store_revision_id"]
        )
    _validate_bootstrap_runtime_manifest_v1(
        store["broker_launch_platform"], enforce_running_interpreter=True
    )
    _load_private_key(store)
    for entry_id, entry in store["entries"].items():
        if entry["entry_state"] == "active":
            load_active_snapshot_manifest_v1(
                store,
                str(entry_id),
                enforce_current_runtime=False,
            )
    with trust_store_coordination_lock(exclusive=True):
        _validate_publisher_contract_binding_v1(
            publisher_contract_binding, enforce_current=True
        )
        authorization = _validate_store_activation_authorization_v1(store)
        basis, _basis_raw = _load_store_activation_basis_v2(
            authorization["store_activation_basis_ref"]
        )
        if basis["publisher_contract_binding"] != publisher_contract_binding:
            raise BrokerBoundaryError(
                "u10_store_activation_basis_publisher_contract_changed",
                str(authorization["authorization_id"]),
            )
        _validate_current_signing_key_for_store_activation_v2(store, basis)
        for entry_id, entry in store["entries"].items():
            if entry["entry_state"] == "active":
                load_active_snapshot_manifest_v1(
                    store,
                    str(entry_id),
                    enforce_current_runtime=False,
                )
        _cleanup_activation_transaction_temporaries_under_lock_v1(
            str(authorization["authorization_id"])
        )
        _cleanup_current_activation_temporaries_under_lock_v1()
        _assert_no_competing_activation_consumption_v1(authorization)
        current = _load_current_store_activation_context_v1(allow_missing_receipt=True)
        if current is not None and current[1] == raw:
            consumption = current[3]
            current_receipt = current[4]
            current_revocation = current[5]
            _fsync_directory_v1(
                TRUST_STORE_HISTORY_ROOT,
                code="u10_history_directory_fsync_failed",
            )
            _fsync_directory_v1(
                STORE_ACTIVATION_LEDGER_ROOT,
                code="u10_store_activation_ledger_directory_fsync_failed",
            )
            _fsync_directory_v1(
                U10_ROOT,
                code="u10_current_store_directory_fsync_failed",
            )
            if current_receipt is None:
                reloaded_store, reloaded_raw = load_fixed_root_trust_store_record_v2()
                if reloaded_store != store or reloaded_raw != raw:
                    raise BrokerBoundaryError(
                        "u10_current_store_retry_recheck_mismatch",
                        str(store["store_revision_id"]),
                    )
                receipt_value = _write_activation_transition_receipt_under_lock_v1(
                    store,
                    raw,
                    authorization,
                    consumption,
                    publication_observed_at=_utc_now(),
                )
            else:
                receipt_value = current_receipt[0]
            stale_prior_revocation_ref: Mapping[str, Any] | None = None
            if current_revocation is not None:
                try:
                    _validate_store_revocation_value_v1(
                        current_revocation[0],
                        store=store,
                        store_raw=raw,
                        activation_receipt=receipt_value,
                    )
                except BrokerBoundaryError as exc:
                    expected_prior = authorization["prior_revocation_ref"]
                    if (
                        exc.code != "u10_store_revocation_record_context_mismatch"
                        or expected_prior is None
                        or _revocation_transition_ref_v1(*current_revocation)
                        != expected_prior
                    ):
                        raise
                    stale_prior_revocation_ref = expected_prior
                else:
                    _load_complete_revocation_publication_chain_v1(
                        store,
                        raw,
                        current_revocation[0],
                        current_revocation[1],
                        receipt_value,
                    )
                    raise BrokerBoundaryError(
                        "u10_revoked_store_reactivation_prohibited",
                        str(store["store_revision_id"]),
                    )
            if stale_prior_revocation_ref is not None:
                _remove_exact_revocation_selector_under_lock_v1(
                    stale_prior_revocation_ref
                )
            return derive_historical_store_ref_v2(store, raw)

        prior_store = current[0] if current is not None else None
        prior_store_raw = current[1] if current is not None else None
        prior_revocation = current[5] if current is not None else None
        if prior_store is not None and prior_store_raw is not None:
            if current[4] is None:
                receipt_tuple = _load_activation_transition_receipt_v1(
                    prior_store,
                    prior_store_raw,
                    current[2],
                    current[3],
                )
            else:
                receipt_tuple = current[4]
            _validate_prior_revocation_binding_v1(
                prior_store,
                prior_store_raw,
                prior_revocation,
                receipt_tuple[0],
            )
            if (
                prior_store["store_id"] == store["store_id"]
                and prior_store["store_revision_id"] == store["store_revision_id"]
            ):
                raise BrokerBoundaryError(
                    "u10_same_store_revision_content_changed",
                    str(store["store_revision_id"]),
                )
        _validate_store_activation_transition_v1(
            authorization,
            prior_store=prior_store,
            prior_store_raw=prior_store_raw,
            prior_revocation=prior_revocation,
        )
        existing_consumption = _try_load_activation_authorization_consumption_v1(
            store, raw, authorization
        )
        if existing_consumption is not None:
            existing_consumption_value = existing_consumption[0]
        else:
            existing_consumption_value = None
        if existing_consumption_value is not None and (
            _try_load_activation_transition_receipt_v1(
                store,
                raw,
                authorization,
                existing_consumption_value,
            )
            is not None
        ):
            raise BrokerBoundaryError(
                "u10_activation_receipt_without_current_target",
                str(authorization["authorization_id"]),
            )
        if (
            existing_consumption_value is not None
            and existing_consumption_value["publisher_contract_binding"]
            != publisher_contract_binding
        ):
            raise BrokerBoundaryError(
                "u10_activation_recovery_publisher_contract_changed",
                str(authorization["authorization_id"]),
            )
        history_ref = _seal_root_trust_store_history_under_lock_v2(store, raw)
        if existing_consumption_value is None:
            consumption = _write_activation_authorization_consumption_under_lock_v1(
                store,
                raw,
                authorization,
                publisher_contract_binding,
            )
        else:
            consumption = existing_consumption_value
        _atomic_replace_v1(
            TRUST_STORE_PATH,
            raw,
            mode=0o444,
            temporary_prefix=".trust-store-current.",
            create_code="u10_current_store_stage_failed",
            durability_code="u10_current_store_directory_fsync_failed",
        )
        current_store, current_raw = load_fixed_root_trust_store_record_v2()
        if current_store != store or current_raw != raw:
            raise BrokerBoundaryError(
                "u10_current_store_post_publish_mismatch", store["store_revision_id"]
            )
        _write_activation_transition_receipt_under_lock_v1(
            store,
            raw,
            authorization,
            consumption,
            publication_observed_at=_utc_now(),
        )
        _load_activation_transition_receipt_v1(store, raw, authorization, consumption)
        if prior_revocation is not None:
            expected_prior = authorization["prior_revocation_ref"]
            if expected_prior is None:
                raise BrokerBoundaryError(
                    "u10_store_activation_prior_revocation_missing",
                    str(authorization["authorization_id"]),
                )
            _remove_exact_revocation_selector_under_lock_v1(expected_prior)
        if _load_current_revocation_artifact_unbound_v1() is not None:
            raise BrokerBoundaryError(
                "u10_store_activation_revocation_cleanup_incomplete",
                str(REVOCATION_SELECTOR_PATH),
            )
    return history_ref


def _render_active_root_trust_store_from_basis_v1(
    *,
    basis: Mapping[str, Any],
    authorization: Mapping[str, Any],
    authorization_ref: Mapping[str, Any],
) -> tuple[dict[str, Any], bytes]:
    """Deterministically render, but do not publish, one authorized store."""

    store = _strict_json_clone(basis["store_content"])
    store.update(
        {
            "store_activation_basis_digest": basis["store_activation_basis_digest"],
            "activation_authorization_ref": _strict_json_clone(authorization_ref),
            "lifecycle_state": "active",
            "revocation_ref": None,
        }
    )
    store["store_digest"] = digest_bytes(canonical_json_bytes(store))
    if (
        authorization["store_id"] != store.get("store_id")
        or authorization["store_revision_id"] != store.get("store_revision_id")
        or authorization["store_version"] != store.get("store_version")
        or authorization["store_activation_basis_digest"]
        != store["store_activation_basis_digest"]
        or authorization["prior_store_ref"] != basis["prior_store_ref"]
        or authorization["prior_revocation_ref"] != basis["prior_revocation_ref"]
    ):
        raise BrokerBoundaryError(
            "u10_store_activation_authorization_basis_mismatch",
            str(authorization.get("authorization_id")),
        )
    raw = canonical_json_bytes(store)
    return store, raw


def publish_active_root_trust_store_by_id_v1(
    authorization_id: str,
    *,
    publisher_contract_binding: Mapping[str, Any],
) -> dict[str, Any]:
    """Resolve human authorization and render its exact active store by ID."""

    if (
        not isinstance(authorization_id, str)
        or _PUBLICATION_IDENTIFIER_V1.fullmatch(authorization_id) is None
    ):
        raise BrokerBoundaryError(
            "u10_store_activation_authorization_identifier_invalid",
            repr(authorization_id),
        )
    _validate_publisher_contract_binding_v1(
        publisher_contract_binding, enforce_current=True
    )
    authorization_path = AUTHORIZATION_ROOT / f"{authorization_id}.json"
    authorization_raw = read_protected_file(
        authorization_path, protected_root=AUTHORIZATION_ROOT
    )
    observed = authorization_path.lstat()
    if (
        observed.st_uid != 0
        or observed.st_gid != 0
        or stat.S_IMODE(observed.st_mode) not in {0o400, 0o444}
        or observed.st_nlink != 1
    ):
        raise BrokerBoundaryError(
            "u10_store_activation_authorization_untrusted",
            str(authorization_path),
        )
    authorization = _load_json_bytes(
        authorization_raw, "u10_store_activation_authorization_unreadable"
    )
    _validate(
        authorization,
        "u10-store-activation-authorization-v1.schema.json",
        "u10_store_activation_authorization_invalid",
    )
    _sealed_digest(
        authorization,
        "authorization_digest",
        "u10_store_activation_authorization_digest_mismatch",
    )
    if authorization.get("authorization_id") != authorization_id:
        raise BrokerBoundaryError(
            "u10_store_activation_authorization_identifier_mismatch",
            authorization_id,
        )
    basis, _basis_raw = _load_store_activation_basis_v2(
        authorization["store_activation_basis_ref"]
    )
    if basis["publisher_contract_binding"] != publisher_contract_binding:
        raise BrokerBoundaryError(
            "u10_store_activation_basis_publisher_contract_changed",
            authorization_id,
        )
    authorization_ref = _exact_root_managed_record_ref_v1(
        record_id=authorization_id,
        path=authorization_path,
        raw=authorization_raw,
        semantic_digest=authorization["authorization_digest"],
    )
    _store, raw = _render_active_root_trust_store_from_basis_v1(
        basis=basis,
        authorization=authorization,
        authorization_ref=authorization_ref,
    )
    return _publish_active_root_trust_store_bytes_v2(raw, publisher_contract_binding)


def publish_active_root_trust_store_v2(raw: bytes) -> dict[str, Any]:
    """Reject the retired raw-byte publication surface.

    Retaining this symbol makes an unsafe integration fail closed instead of
    silently reaching the new ID-only production path.
    """

    del raw
    raise BrokerBoundaryError(
        "u10_unbound_publisher_invocation_prohibited",
        "use fixed control entrypoint with activate-store IDENTIFIER",
    )


def _seal_store_revocation_history_under_lock_v1(raw: bytes) -> Path:
    artifact_digest = digest_bytes(raw)
    path = REVOCATION_ROOT / f"{artifact_digest['value']}.json"
    _verify_declared_directory(
        REVOCATION_ROOT,
        uid=0,
        gid=0,
        mode=0o755,
        code="u10_revocation_history_directory_mismatch",
    )
    _atomic_create_once_v1(
        path,
        raw,
        mode=0o444,
        temporary_prefix=f".{artifact_digest['value']}.revocation-history.",
        collision_code="u10_revocation_history_collision",
        create_code="u10_revocation_history_create_failed",
        durability_code="u10_revocation_history_directory_fsync_failed",
    )
    if read_protected_file(path, protected_root=REVOCATION_ROOT) != raw:
        raise BrokerBoundaryError(
            "u10_revocation_history_post_write_mismatch", str(path)
        )
    return path


def _load_root_revocation_decision_v1(
    revocation_id: str,
    *,
    store: Mapping[str, Any],
    store_raw: bytes,
    activation_receipt: Mapping[str, Any],
) -> tuple[dict[str, Any], bytes]:
    """Resolve one fixed root decision by identifier; never trust caller JSON."""

    if (
        not isinstance(revocation_id, str)
        or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,255}", revocation_id) is None
    ):
        raise BrokerBoundaryError(
            "u10_store_revocation_id_invalid", repr(revocation_id)
        )
    selector = store["current_selector"]
    if (
        selector["revocation_decision_root_path"] != str(AUTHORIZATION_ROOT)
        or selector["revocation_decision_entry_policy"]
        != "fixed_root_record_id_resolution_no_caller_raw/v1"
    ):
        raise BrokerBoundaryError(
            "u10_store_revocation_decision_contract_mismatch", revocation_id
        )
    path = AUTHORIZATION_ROOT / f"{revocation_id}.json"
    raw = read_protected_file(path, protected_root=AUTHORIZATION_ROOT)
    observed = path.lstat()
    if (
        observed.st_uid != 0
        or observed.st_gid != 0
        or stat.S_IMODE(observed.st_mode) != 0o444
        or observed.st_nlink != 1
    ):
        raise BrokerBoundaryError("u10_store_revocation_decision_untrusted", str(path))
    revocation = _load_json_bytes(raw, "u10_store_revocation_record_unreadable")
    if revocation.get("revocation_id") != revocation_id:
        raise BrokerBoundaryError(
            "u10_store_revocation_decision_id_mismatch", str(path)
        )
    _validate_store_revocation_value_v1(
        revocation,
        store=store,
        store_raw=store_raw,
        activation_receipt=activation_receipt,
    )
    return revocation, raw


def _publish_store_revocation_record_v1(
    revocation_id: str,
    publisher_contract_binding: Mapping[str, Any],
) -> dict[str, Any]:
    """Publish one fixed root-held revocation decision for the active store.

    The active store original is never rewritten into a fictitious revoked
    variant.  The caller supplies only a stable identifier.  The root-held
    decision, its one-shot consumption, immutable history, fixed selector and
    post-publication occurrence receipt remain separate durable propositions.
    """

    _validate_publisher_contract_binding_v1(
        publisher_contract_binding, enforce_current=True
    )
    if os.geteuid() != 0:
        raise BrokerBoundaryError("u10_root_broker_requires_root", str(os.geteuid()))
    with trust_store_coordination_lock(exclusive=True):
        store, store_raw = load_fixed_root_trust_store_record_v2()
        if store["lifecycle_state"] != "active":
            raise BrokerBoundaryError(
                "u10_root_trust_store_not_active", str(store["lifecycle_state"])
            )
        _verify_current_selector_contract_v1(store)
        current_authorization = _validate_store_activation_authorization_v1(store)
        _cleanup_activation_transaction_temporaries_under_lock_v1(
            str(current_authorization["authorization_id"])
        )
        _authorization, _activation_consumption, activation_receipt = (
            _load_complete_store_activation_chain_v1(store, store_raw)
        )
        historical, historical_raw = load_historical_root_trust_store_v2(
            derive_historical_store_ref_v2(store, store_raw)
        )
        if historical != store or historical_raw != store_raw:
            raise BrokerBoundaryError(
                "u10_current_history_mismatch", str(store["store_revision_id"])
            )
        revocation, raw = _load_root_revocation_decision_v1(
            revocation_id,
            store=store,
            store_raw=store_raw,
            activation_receipt=activation_receipt,
        )
        # A process may die after atomic-create links the complete final name
        # but before unlinking its hidden temporary.  Clean only this exact
        # transaction's root-owned temporaries before any loader enforces the
        # final file's single-link invariant or the history denominator.
        artifact_digest = digest_bytes(raw)
        for directory, prefix, code in (
            (
                REVOCATION_LEDGER_ROOT,
                f".{revocation_id}.consumption.",
                "u10_store_revocation_consumption_create_failed",
            ),
            (
                REVOCATION_LEDGER_ROOT,
                f".{revocation_id}.receipt.",
                "u10_store_revocation_receipt_create_failed",
            ),
            (
                REVOCATION_ROOT,
                f".{artifact_digest['value']}.revocation-history.",
                "u10_revocation_history_create_failed",
            ),
            (
                U10_ROOT,
                ".trust-store-current-revocation.",
                "u10_revocation_selector_stage_failed",
            ),
        ):
            _remove_transaction_temporaries_v1(
                directory,
                prefix=prefix,
                code=code,
            )
        _assert_no_competing_revocation_consumption_v1(
            requested_revocation_id=revocation_id,
            store=store,
            store_raw=store_raw,
            activation_receipt=activation_receipt,
        )
        history_existing = _scan_revocation_history_for_store_v1(
            store, store_raw, activation_receipt
        )
        if history_existing is not None and history_existing[1] != raw:
            raise BrokerBoundaryError(
                "u10_store_already_revoked", str(store["store_revision_id"])
            )
        existing_consumption = _try_load_revocation_consumption_v1(
            store, store_raw, revocation, activation_receipt
        )
        existing_receipt = None
        if existing_consumption is not None:
            existing_receipt = _try_load_revocation_publication_receipt_v1(
                store,
                store_raw,
                revocation,
                raw,
                activation_receipt,
                existing_consumption[0],
            )
        selector_existing = _load_current_revocation_artifact_unbound_v1()
        if existing_receipt is not None:
            if (
                history_existing is not None
                and selector_existing is not None
                and selector_existing[1] == raw
            ):
                _fsync_directory_v1(
                    REVOCATION_ROOT,
                    code="u10_revocation_history_directory_fsync_failed",
                )
                _fsync_directory_v1(
                    REVOCATION_LEDGER_ROOT,
                    code="u10_store_revocation_ledger_directory_fsync_failed",
                )
                _fsync_directory_v1(
                    U10_ROOT,
                    code="u10_revocation_selector_directory_fsync_failed",
                )
                return {
                    "revocation_id": revocation["revocation_id"],
                    "selector_path": str(REVOCATION_SELECTOR_PATH),
                    "history_path": str(_revocation_history_ref_v1(raw)["locator"]),
                    "consumption_path": str(
                        _revocation_consumption_path_v1(revocation_id)
                    ),
                    "receipt_path": str(
                        _revocation_publication_receipt_path_v1(revocation_id)
                    ),
                    "artifact_digest": digest_bytes(raw),
                    "publication_status": "already_published_exact",
                    "formal_authority": "none",
                    "positive_assurance_allowed": False,
                }
            raise BrokerBoundaryError(
                "u10_revocation_completed_state_mismatch", revocation_id
            )
        if (
            existing_consumption is not None
            and history_existing is not None
            and history_existing[1] == raw
            and selector_existing is not None
            and selector_existing[1] == raw
        ):
            receipt = _write_revocation_publication_receipt_under_lock_v1(
                store,
                store_raw,
                revocation,
                raw,
                activation_receipt,
                existing_consumption[0],
                publication_observed_at=_utc_now(),
            )
            return {
                "revocation_id": revocation["revocation_id"],
                "selector_path": str(REVOCATION_SELECTOR_PATH),
                "history_path": str(_revocation_history_ref_v1(raw)["locator"]),
                "consumption_path": str(_revocation_consumption_path_v1(revocation_id)),
                "receipt_path": str(
                    _revocation_publication_receipt_path_v1(revocation_id)
                ),
                "receipt_digest": receipt["receipt_digest"],
                "artifact_digest": digest_bytes(raw),
                "publication_status": "publication_observed_and_receipt_recovered",
                "formal_authority": "none",
                "positive_assurance_allowed": False,
            }
        if selector_existing is not None and selector_existing[1] != raw:
            raise BrokerBoundaryError(
                "u10_store_already_revoked", str(store["store_revision_id"])
            )
        if (
            existing_consumption is not None
            and existing_consumption[0]["publisher_contract_binding"]
            != publisher_contract_binding
        ):
            raise BrokerBoundaryError(
                "u10_revocation_recovery_publisher_contract_changed",
                revocation_id,
            )
        if existing_consumption is None:
            consumption = _write_revocation_consumption_under_lock_v1(
                store,
                store_raw,
                revocation,
                activation_receipt,
                publisher_contract_binding,
            )
        else:
            consumption = existing_consumption[0]
        history_path = _seal_store_revocation_history_under_lock_v1(raw)
        _atomic_replace_v1(
            REVOCATION_SELECTOR_PATH,
            raw,
            mode=0o444,
            temporary_prefix=".trust-store-current-revocation.",
            create_code="u10_revocation_selector_stage_failed",
            durability_code="u10_revocation_selector_directory_fsync_failed",
        )
        selected = _load_current_revocation_artifact_unbound_v1()
        if selected is None or selected[1] != raw:
            raise BrokerBoundaryError(
                "u10_revocation_selector_post_publish_mismatch",
                str(REVOCATION_SELECTOR_PATH),
            )
        receipt = _write_revocation_publication_receipt_under_lock_v1(
            store,
            store_raw,
            revocation,
            raw,
            activation_receipt,
            consumption,
            publication_observed_at=_utc_now(),
        )
        published = load_current_store_revocation_v1(
            store, store_raw, activation_receipt=activation_receipt
        )
        if published is None or published[1] != raw:
            raise BrokerBoundaryError(
                "u10_revocation_selector_post_publish_mismatch",
                str(REVOCATION_SELECTOR_PATH),
            )
    return {
        "revocation_id": revocation["revocation_id"],
        "selector_path": str(REVOCATION_SELECTOR_PATH),
        "history_path": str(history_path),
        "consumption_path": str(_revocation_consumption_path_v1(revocation_id)),
        "receipt_path": str(_revocation_publication_receipt_path_v1(revocation_id)),
        "receipt_digest": receipt["receipt_digest"],
        "artifact_digest": digest_bytes(raw),
        "publication_status": "published_exact_revocation",
        "formal_authority": "none",
        "positive_assurance_allowed": False,
    }


def publish_store_revocation_by_id_v1(
    revocation_id: str,
    *,
    publisher_contract_binding: Mapping[str, Any],
) -> dict[str, Any]:
    if (
        not isinstance(revocation_id, str)
        or _PUBLICATION_IDENTIFIER_V1.fullmatch(revocation_id) is None
    ):
        raise BrokerBoundaryError(
            "u10_store_revocation_identifier_invalid", repr(revocation_id)
        )
    return _publish_store_revocation_record_v1(
        revocation_id, publisher_contract_binding
    )


def publish_store_revocation_record_v1(
    revocation_id: str,
) -> dict[str, Any]:
    del revocation_id
    raise BrokerBoundaryError(
        "u10_unbound_publisher_invocation_prohibited",
        "use fixed control entrypoint with revoke-store IDENTIFIER",
    )


def load_active_root_trust_store_for_execution_v2() -> tuple[dict[str, Any], bytes]:
    if os.geteuid() != 0:
        raise BrokerBoundaryError("u10_root_broker_requires_root", str(os.geteuid()))
    store, raw = load_fixed_root_trust_store_record_v2()
    if store["lifecycle_state"] != "active":
        raise BrokerBoundaryError(
            "u10_root_trust_store_not_active", str(store["lifecycle_state"])
        )
    if store["broker_runtime_version"] != BROKER_VERSION:
        raise BrokerBoundaryError(
            "u10_broker_runtime_version_mismatch",
            str(store["broker_runtime_version"]),
        )
    _verify_current_selector_contract_v1(store)
    _load_complete_store_activation_chain_v1(store, raw)
    if load_current_store_revocation_v1(store, raw) is not None:
        raise BrokerBoundaryError(
            "u10_root_trust_store_revoked", str(store["store_revision_id"])
        )
    if store["signing_key"]["key_state"] != "active" or not isinstance(
        store["signing_key"]["public_key_base64"], str
    ):
        raise BrokerBoundaryError(
            "u10_signing_key_not_active", str(store["signing_key"]["key_id"])
        )
    if store["nonce_ledger"]["ledger_root"] != str(NONCE_LEDGER_ROOT):
        raise BrokerBoundaryError("u10_nonce_ledger_path_mismatch", "fixed path")
    if store["result_spool"]["path"] != str(EVIDENCE_SPOOL_ROOT):
        raise BrokerBoundaryError("u10_evidence_spool_path_mismatch", "fixed path")
    if store["snapshot_root"]["path"] != str(SNAPSHOT_ROOT):
        raise BrokerBoundaryError("u10_snapshot_root_path_mismatch", "fixed path")
    if store["trust_store_history"]["path"] != str(TRUST_STORE_HISTORY_ROOT):
        raise BrokerBoundaryError("u10_history_root_path_mismatch", "fixed path")
    if store["coordination_lock"]["path"] != str(TRUST_STORE_LOCK_PATH):
        raise BrokerBoundaryError("u10_coordination_lock_path_mismatch", "fixed path")
    _verify_declared_directory(
        NONCE_LEDGER_ROOT,
        uid=int(store["nonce_ledger"]["owner_uid"]),
        gid=int(store["nonce_ledger"]["owner_gid"]),
        mode=int(store["nonce_ledger"]["directory_mode"], 8),
        code="u10_nonce_ledger_directory_mismatch",
    )
    for binding, path, code in (
        (store["snapshot_root"], SNAPSHOT_ROOT, "u10_snapshot_root_directory_mismatch"),
        (store["result_spool"], EVIDENCE_SPOOL_ROOT, "u10_spool_directory_mismatch"),
    ):
        _verify_declared_directory(
            path,
            uid=int(binding["owner_uid"]),
            gid=int(binding["owner_gid"]),
            mode=int(binding["mode"], 8),
            code=code,
        )
    _verify_declared_directory(
        TRUST_STORE_HISTORY_ROOT,
        uid=int(store["trust_store_history"]["owner_uid"]),
        gid=int(store["trust_store_history"]["owner_gid"]),
        mode=int(store["trust_store_history"]["directory_mode"], 8),
        code="u10_history_directory_mismatch",
    )
    lock_observed = TRUST_STORE_LOCK_PATH.lstat()
    try:
        assert_no_extended_acl(TRUST_STORE_LOCK_PATH)
    except (OSError, PermissionError) as exc:
        raise BrokerBoundaryError(
            "u10_coordination_lock_acl_untrusted", str(TRUST_STORE_LOCK_PATH)
        ) from exc
    if (
        not stat.S_ISREG(lock_observed.st_mode)
        or stat.S_ISLNK(lock_observed.st_mode)
        or lock_observed.st_uid != int(store["coordination_lock"]["owner_uid"])
        or lock_observed.st_gid != int(store["coordination_lock"]["owner_gid"])
        or stat.S_IMODE(lock_observed.st_mode)
        != int(store["coordination_lock"]["mode"], 8)
        or lock_observed.st_nlink != 1
    ):
        raise BrokerBoundaryError(
            "u10_coordination_lock_mismatch", str(TRUST_STORE_LOCK_PATH)
        )
    for reference, expected, code in (
        (
            store["broker_entrypoint_ref"],
            BROKER_ENTRYPOINT_PATH,
            "u10_broker_entrypoint_mismatch",
        ),
        (
            store["broker_outer_launcher_ref"],
            BROKER_OUTER_LAUNCHER_PATH,
            "u10_broker_outer_launcher_mismatch",
        ),
    ):
        if Path(str(reference["locator"])) != expected:
            raise BrokerBoundaryError(code, str(reference["locator"]))
        artifact_raw = _verify_root_artifact(reference)
        if reference["semantic_digest"] != digest_bytes(artifact_raw):
            raise BrokerBoundaryError(code, str(expected))
    launch_platform = store["broker_launch_platform"]
    if (
        launch_platform["profile"]
        != "darwin-root-wrapper-qualified-effective-python/v2"
        or launch_platform["environment_policy"]
        != "privileged_sh_p_then_env_i_direct_effective_execve/v3"
        or launch_platform["shell_flags"] != ["-p"]
        or launch_platform["os_injected_environment_policy"]
        != "cf_user_text_encoding_uid_bound_then_removed/v1"
        or launch_platform["python_flags"] != ["-I", "-S", "-B"]
    ):
        raise BrokerBoundaryError("u10_broker_launch_platform_mismatch", "contract")
    for reference, expected in (
        (launch_platform["shell_ref"], Path("/bin/sh")),
        (launch_platform["environment_cleaner_ref"], Path("/usr/bin/env")),
    ):
        if Path(str(reference["locator"])) != expected:
            raise BrokerBoundaryError(
                "u10_host_runtime_path_mismatch", str(reference["locator"])
            )
        _verify_host_runtime_artifact(reference)
    effective_path_raw = _verify_root_artifact(
        launch_platform["effective_python_path_ref"]
    )
    if (
        Path(str(launch_platform["effective_python_path_ref"]["locator"]))
        != BROKER_EFFECTIVE_PYTHON_PATH
        or not effective_path_raw.endswith(b"\n")
        or effective_path_raw.count(b"\n") != 1
        or b"\x00" in effective_path_raw
    ):
        raise BrokerBoundaryError(
            "u10_effective_python_path_binding_mismatch",
            str(BROKER_EFFECTIVE_PYTHON_PATH),
        )
    try:
        effective_path = Path(effective_path_raw[:-1].decode("utf-8"))
    except UnicodeError as exc:
        raise BrokerBoundaryError(
            "u10_effective_python_path_binding_mismatch",
            str(BROKER_EFFECTIVE_PYTHON_PATH),
        ) from exc
    effective_ref = launch_platform["effective_python_ref"]
    if (
        not effective_path.is_absolute()
        or effective_path != Path(os.path.normpath(str(effective_path)))
        or Path(os.path.realpath(effective_path)) != effective_path
        or Path(str(effective_ref["locator"])) != effective_path
        or Path(str(effective_ref["resolved_locator"])) != effective_path
    ):
        raise BrokerBoundaryError(
            "u10_effective_python_path_binding_mismatch", str(effective_path)
        )
    _verify_host_runtime_artifact(effective_ref)
    _validate_bootstrap_runtime_manifest_v1(
        launch_platform, enforce_running_interpreter=False
    )
    runtime_ref = store["broker_runtime_ref"]
    runtime_path = Path(str(runtime_ref["locator"]))
    try:
        runtime_path.relative_to(SNAPSHOT_ROOT)
    except ValueError as exc:
        raise BrokerBoundaryError(
            "u10_broker_runtime_path_mismatch", str(runtime_path)
        ) from exc
    if runtime_path.name != "u10_root_broker_bootstrap.py":
        raise BrokerBoundaryError("u10_broker_runtime_path_mismatch", str(runtime_path))
    runtime_raw = _verify_root_artifact(runtime_ref)
    if runtime_ref["semantic_digest"] != digest_bytes(runtime_raw):
        raise BrokerBoundaryError(
            "u10_broker_runtime_semantic_digest_mismatch", str(runtime_path)
        )
    _load_private_key(store)
    historical_store, historical_raw = load_historical_root_trust_store_v2(
        derive_historical_store_ref_v2(store, raw)
    )
    if historical_store != store or historical_raw != raw:
        raise BrokerBoundaryError(
            "u10_current_history_mismatch", store["store_revision_id"]
        )
    return store, raw


def load_active_root_trust_store_for_execution_v3() -> tuple[dict[str, Any], bytes]:
    """Resolve a current store whose exact v2 key-chain head is still live.

    The caller must already hold ``trust-store.lock``.  The v2 loader performs
    the established store and snapshot checks; this additional gate rejects a
    legacy basis and binds the current key chain before any nonce reservation
    or signing operation.
    """

    store, raw = load_active_root_trust_store_for_execution_v2()
    authorization = _validate_store_activation_authorization_v1(store)
    basis, _basis_raw = _load_store_activation_basis_v2(
        authorization["store_activation_basis_ref"]
    )
    _validate_current_signing_key_for_store_activation_v2(store, basis)
    return store, raw


def _validate_bootstrap_runtime_manifest_v1(
    platform_contract: Mapping[str, Any],
    *,
    enforce_running_interpreter: bool,
) -> dict[str, Any]:
    reference = platform_contract["effective_runtime_manifest_ref"]
    if Path(str(reference["locator"])) != BROKER_EFFECTIVE_RUNTIME_MANIFEST_PATH:
        raise BrokerBoundaryError(
            "u10_bootstrap_runtime_manifest_path_mismatch",
            str(reference["locator"]),
        )
    raw = _verify_root_artifact(reference)
    manifest = _load_json_bytes(raw, "u10_bootstrap_runtime_manifest_unreadable")
    _validate(
        manifest,
        "u10-bootstrap-runtime-manifest-v1.schema.json",
        "u10_bootstrap_runtime_manifest_invalid",
    )
    _sealed_digest(
        manifest,
        "manifest_digest",
        "u10_bootstrap_runtime_manifest_digest_mismatch",
    )
    if manifest["manifest_digest"] != reference["semantic_digest"]:
        raise BrokerBoundaryError(
            "u10_bootstrap_runtime_manifest_binding_mismatch",
            str(reference["record_id"]),
        )
    uname = os.uname()
    system_version_path = Path("/System/Library/CoreServices/SystemVersion.plist")
    system_version_raw = read_protected_file(
        system_version_path,
        protected_root=Path("/"),
        required_uid=0,
        maximum_bytes=1024 * 1024,
    )
    try:
        system_version = plistlib.loads(system_version_raw)
    except plistlib.InvalidFileException as exc:
        raise BrokerBoundaryError(
            "u10_bootstrap_runtime_os_build_unreadable",
            str(system_version_path),
        ) from exc
    expected_platform = {
        "system": uname.sysname,
        "release": uname.release,
        "kernel_version": uname.version,
        "machine": uname.machine,
        "os_build_artifact": {
            "locator": str(system_version_path),
            "product_build_version": system_version.get("ProductBuildVersion"),
            "artifact_digest": digest_bytes(system_version_raw),
        },
        "binding_profile": ("uname_kernel_and_system_version_artifact_exact/v2"),
    }
    if manifest["platform_binding"] != expected_platform:
        raise BrokerBoundaryError(
            "u10_bootstrap_runtime_platform_mismatch", repr(uname)
        )
    root = Path(str(manifest["runtime_root"]))
    interpreter = Path(str(manifest["effective_interpreter_locator"]))
    effective_ref = platform_contract["effective_python_ref"]
    if (
        not root.is_absolute()
        or root != Path(os.path.normpath(str(root)))
        or Path(os.path.realpath(root)) != root
        or not interpreter.is_absolute()
        or interpreter != Path(os.path.normpath(str(interpreter)))
        or Path(os.path.realpath(interpreter)) != interpreter
        or Path(str(effective_ref["locator"])) != interpreter
        or Path(str(effective_ref["resolved_locator"])) != interpreter
    ):
        raise BrokerBoundaryError(
            "u10_bootstrap_runtime_interpreter_mismatch", str(interpreter)
        )
    runtime_closure = manifest["runtime_closure"]
    observed_closure = _probe_bootstrap_runtime_v1(interpreter)
    if runtime_closure != observed_closure:
        raise BrokerBoundaryError(
            "u10_bootstrap_runtime_execution_closure_mismatch",
            str(interpreter),
        )
    derived_root = _derive_runtime_root_v1(observed_closure)
    if (
        root != derived_root
        or manifest["runtime_version"] != observed_closure["runtime_version"]
    ):
        raise BrokerBoundaryError(
            "u10_bootstrap_runtime_derived_root_mismatch", str(root)
        )
    try:
        interpreter.relative_to(root)
    except ValueError as exc:
        raise BrokerBoundaryError(
            "u10_bootstrap_runtime_interpreter_escape", str(interpreter)
        ) from exc
    _validate_absolute_root_owned_chain_v1(root)
    validate_directory_chain(root, root, required_uid=0)
    root_observed = root.lstat()
    if (
        root_observed.st_uid != manifest["runtime_root_uid"]
        or root_observed.st_gid != manifest["runtime_root_gid"]
        or stat.S_IMODE(root_observed.st_mode) != manifest["runtime_root_mode"]
    ):
        raise BrokerBoundaryError("u10_bootstrap_runtime_root_mismatch", str(root))
    entries = _host_runtime_tree_entries_v1(root)
    denominator = manifest["tree_denominator"]
    if (
        denominator["entry_count"] != len(entries)
        or denominator["entries"] != entries
        or denominator["tree_digest"]
        != digest_bytes(canonical_json_bytes({"entries": entries}))
    ):
        raise BrokerBoundaryError(
            "u10_bootstrap_runtime_denominator_mismatch", str(root)
        )
    interpreter_raw = read_protected_file(
        interpreter,
        protected_root=root,
        required_uid=0,
        maximum_bytes=256 * 1024 * 1024,
    )
    if manifest["effective_interpreter_artifact_digest"] != digest_bytes(
        interpreter_raw
    ) or effective_ref["artifact_digest"] != digest_bytes(interpreter_raw):
        raise BrokerBoundaryError(
            "u10_bootstrap_runtime_interpreter_digest_mismatch",
            str(interpreter),
        )
    if enforce_running_interpreter:
        if manifest["runtime_version"] != ".".join(map(str, sys.version_info[:3])):
            raise BrokerBoundaryError(
                "u10_bootstrap_runtime_running_interpreter_mismatch",
                str(sys.executable),
            )
        _validate_current_process_runtime_closure_v1(runtime_closure, root, interpreter)
    return manifest


def _parse_time(value: Any, code: str) -> datetime:
    return _timestamp_v1(str(value), code=code)


def _require_time_order(*values: tuple[str, Any]) -> None:
    parsed = [(name, _parse_time(value, "u10_time_invalid")) for name, value in values]
    for (earlier_name, earlier), (later_name, later) in zip(parsed, parsed[1:]):
        if later < earlier:
            raise BrokerBoundaryError(
                "u10_time_order_invalid", f"{earlier_name}>{later_name}"
            )


def _snapshot_artifact_id(
    entries: Mapping[str, Any],
    reference: Mapping[str, Any],
    *,
    role: str | None = None,
) -> str:
    matches = [
        str(artifact_id)
        for artifact_id, artifact in entries.items()
        if artifact["snapshot_ref"] == reference
        and (role is None or artifact["role"] == role)
    ]
    if len(matches) != 1:
        raise BrokerBoundaryError(
            "u10_snapshot_artifact_reference_ambiguous",
            repr({"role": role, "matches": matches, "reference": reference}),
        )
    return matches[0]


def _read_snapshot_artifact(
    snapshot_path: Path,
    reference: Mapping[str, Any],
) -> bytes:
    path = Path(str(reference["locator"]))
    try:
        path.relative_to(snapshot_path)
    except ValueError as exc:
        raise BrokerBoundaryError("u10_snapshot_artifact_outside", str(path)) from exc
    raw = read_protected_file(path, protected_root=snapshot_path)
    if digest_bytes(raw) != reference["artifact_digest"]:
        raise BrokerBoundaryError("u10_snapshot_artifact_digest_mismatch", str(path))
    return raw


def _semantic_json_artifact(
    *,
    snapshot_path: Path,
    entries: Mapping[str, Any],
    reference: Mapping[str, Any],
    role: str,
    semantic_field: str | None,
    schema_name: str,
    code: str,
) -> dict[str, Any]:
    _snapshot_artifact_id(entries, reference, role=role)
    raw = _read_snapshot_artifact(snapshot_path, reference)
    value = _load_json_bytes(raw, code)
    _validate(value, schema_name, code)
    if semantic_field is None:
        observed = digest_bytes(canonical_json_bytes(value))
    else:
        _sealed_digest(value, semantic_field, f"{code}_semantic_digest_invalid")
        observed = value[semantic_field]
    if observed != reference["semantic_digest"]:
        raise BrokerBoundaryError(f"{code}_semantic_digest_mismatch", str(reference))
    return value


def _entity_id_from_reference_v1(value: Any, *, code: str) -> str:
    """Return only the identity authority from a label-right UUID reference."""

    if not isinstance(value, str):
        raise BrokerBoundaryError(code, repr(value))
    matched = _ENTITY_REFERENCE_V1.fullmatch(value)
    if matched is None:
        raise BrokerBoundaryError(code, value)
    return matched.group("entity_id")


def _current_worker_account_material_v1(account_name: Any) -> dict[str, Any]:
    if not isinstance(account_name, str) or not account_name:
        raise BrokerBoundaryError(
            "u10_snapshot_worker_account_reobservation_failed",
            repr(account_name),
        )
    try:
        account = pwd.getpwnam(account_name)
        all_group_ids = sorted(set(os.getgrouplist(account.pw_name, account.pw_gid)))
    except (KeyError, OSError) as exc:
        raise BrokerBoundaryError(
            "u10_snapshot_worker_account_reobservation_failed", account_name
        ) from exc
    host_material = {
        "os": platform.system(),
        "architecture": platform.machine(),
        "os_release": platform.release(),
        "platform_version": platform.version(),
        "hostname": platform.node(),
    }
    if any(not isinstance(value, str) or not value for value in host_material.values()):
        raise BrokerBoundaryError(
            "u10_snapshot_worker_account_reobservation_failed",
            "host platform",
        )
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
            "host_identity_digest": digest_bytes(canonical_json_bytes(host_material)),
        },
    }


def _current_host_identity_material_v1() -> dict[str, Any]:
    observed_platform = {
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
    }
    node_name_digest = digest_bytes(
        canonical_json_bytes({"platform_node": platform.node()})
    )
    hardware_identifier_digest = digest_bytes(
        canonical_json_bytes({"uuid_getnode": f"{uuid.getnode():012x}"})
    )
    identity_material = {
        "observed_platform": observed_platform,
        "node_name_digest": node_name_digest,
        "hardware_identifier_digest": hardware_identifier_digest,
        "observation_method": "platform-node-and-uuid-getnode-hashed/v1",
    }
    return {
        **identity_material,
        "identity_digest": digest_bytes(canonical_json_bytes(identity_material)),
    }


def _validate_current_host_identity_evidence_v1(
    *,
    snapshot_path: Path,
    entries: Mapping[str, Any],
    environment: Mapping[str, Any],
    reobserve_current_host: bool,
) -> None:
    """Bind the environment profile to one closed host-evidence artifact.

    The artifact remains evidence rather than a hardware trust anchor.  Current
    re-observation only prevents a snapshot qualified on one host/OS from being
    silently used on another.
    """

    host_ref = environment.get("host_identity_ref")
    if not isinstance(host_ref, Mapping):
        raise BrokerBoundaryError("u10_snapshot_host_identity_ref_missing", "")
    evidence_ref = host_ref.get("evidence_ref")
    if not isinstance(evidence_ref, Mapping):
        raise BrokerBoundaryError("u10_snapshot_host_evidence_ref_missing", "")
    matches = [
        artifact
        for artifact in entries.values()
        if artifact.get("role") == "host_identity_evidence"
        and artifact.get("source_ref", {}).get("record_id")
        == evidence_ref.get("record_id")
        and artifact.get("source_ref", {}).get("locator") == evidence_ref.get("locator")
        and artifact.get("source_ref", {}).get("artifact_digest")
        == evidence_ref.get("content_digest")
    ]
    if len(matches) != 1:
        raise BrokerBoundaryError(
            "u10_snapshot_host_evidence_denominator_mismatch",
            str(evidence_ref.get("record_id", "")),
        )
    artifact = matches[0]
    raw = _read_snapshot_artifact(snapshot_path, artifact["snapshot_ref"])
    evidence = _load_json_bytes(raw, "u10_snapshot_host_evidence_unreadable")
    _validate(
        evidence,
        "local-host-identity-evidence-v1.schema.json",
        "u10_snapshot_host_evidence_invalid",
    )
    _sealed_digest(
        evidence,
        "evidence_digest",
        "u10_snapshot_host_evidence_digest_invalid",
    )
    expected_host_id = f"host.local.{evidence['identity_digest']['value'][:24]}"
    if (
        evidence["evidence_id"] != evidence_ref.get("record_id")
        or digest_bytes(raw) != evidence_ref.get("content_digest")
        or artifact["snapshot_ref"]["semantic_digest"] != evidence["evidence_digest"]
        or host_ref.get("host_id") != expected_host_id
        or host_ref.get("identity_digest") != evidence["identity_digest"]
        or environment.get("platform") != evidence["observed_platform"]
    ):
        raise BrokerBoundaryError(
            "u10_snapshot_host_evidence_binding_mismatch",
            str(evidence_ref.get("record_id", "")),
        )
    if reobserve_current_host:
        current = _current_host_identity_material_v1()
        observed = {
            key: evidence[key]
            for key in (
                "observed_platform",
                "node_name_digest",
                "hardware_identifier_digest",
                "observation_method",
                "identity_digest",
            )
        }
        if current != observed:
            raise BrokerBoundaryError(
                "u10_snapshot_host_reobservation_mismatch",
                str(evidence_ref.get("record_id", "")),
            )


def _validate_preactivation_boundary_binding_v1(
    *,
    manifest: Mapping[str, Any],
    entry: Mapping[str, Any],
    snapshot_path: Path,
    entries: Mapping[str, Any],
    reobserve_current_account: bool,
) -> None:
    """Close candidate scope and principal evidence into one runtime binding.

    Labels remain display hints: cross-record identity comparisons use only the
    UUID at the right edge of ``label・uuid``.  Raw artifact and semantic
    digests are still checked independently.
    """

    binding = manifest.get("preactivation_boundary_binding")
    if not isinstance(binding, Mapping) or binding != entry.get(
        "preactivation_boundary_binding"
    ):
        raise BrokerBoundaryError(
            "u10_snapshot_preactivation_store_binding_mismatch",
            str(manifest.get("snapshot_id", "")),
        )

    candidate_ref = binding["candidate_bundle_ref"]
    candidate_snapshot_ref = candidate_ref["snapshot_artifact_ref"]
    candidate_artifact_id = _snapshot_artifact_id(
        entries,
        candidate_snapshot_ref,
        role="u10_candidate_bundle_manifest",
    )
    candidate_entry = entries[candidate_artifact_id]
    expected_candidate_source = {
        "record_id": candidate_ref["bundle_id"],
        "locator": candidate_ref["candidate_locator"],
        "artifact_digest": candidate_ref["artifact_digest"],
        "semantic_digest": candidate_ref["bundle_digest"],
    }
    candidate_raw = _read_snapshot_artifact(snapshot_path, candidate_snapshot_ref)
    candidate = _load_json_bytes(
        candidate_raw, "u10_snapshot_candidate_bundle_unreadable"
    )
    _validate(
        candidate,
        "u10-root-candidate-bundle-v1.schema.json",
        "u10_snapshot_candidate_bundle_invalid",
    )
    _sealed_digest(
        candidate,
        "bundle_digest",
        "u10_snapshot_candidate_bundle_digest_mismatch",
    )
    if (
        candidate_entry["source_ref"] != expected_candidate_source
        or candidate_ref["artifact_digest"] != digest_bytes(candidate_raw)
        or candidate_snapshot_ref["artifact_digest"] != candidate_ref["artifact_digest"]
        or candidate_snapshot_ref["semantic_digest"] != candidate_ref["bundle_digest"]
        or candidate["bundle_id"] != candidate_ref["bundle_id"]
        or candidate["bundle_version"] != candidate_ref["bundle_version"]
        or candidate["bundle_digest"] != candidate_ref["bundle_digest"]
    ):
        raise BrokerBoundaryError(
            "u10_snapshot_candidate_bundle_binding_mismatch",
            str(candidate_ref.get("bundle_id", "")),
        )

    candidate_boundary = candidate["preactivation_boundary_refs"]
    if (
        candidate_boundary["binding_digest"]
        != digest_bytes(
            canonical_json_bytes(
                {
                    key: value
                    for key, value in candidate_boundary.items()
                    if key != "binding_digest"
                }
            )
        )
        or binding["boundary_binding_digest"] != candidate_boundary["binding_digest"]
    ):
        raise BrokerBoundaryError(
            "u10_snapshot_candidate_boundary_digest_mismatch",
            str(candidate_ref["bundle_id"]),
        )

    copied_fields = (
        "profile",
        "threat_boundary",
        "worker_identity_policy",
        "qualification_scope",
        "hostile_code_assurance",
        "requalification_triggers",
    )
    if any(binding[field] != candidate_boundary[field] for field in copied_fields):
        raise BrokerBoundaryError(
            "u10_snapshot_candidate_boundary_context_mismatch",
            str(candidate_ref["bundle_id"]),
        )

    loaded: dict[str, dict[str, Any]] = {}
    for field, role, schema_name, semantic_field in (
        (
            "decision_record_ref",
            "u10_preactivation_decision_record",
            "u10-preactivation-decision-v1.schema.json",
            "decision_digest",
        ),
        (
            "worker_account_observation_ref",
            "u10_worker_account_observation",
            "u10-worker-account-observation-v1.schema.json",
            "observation_digest",
        ),
        (
            "worker_principal_resolution_ref",
            "u10_worker_principal_resolution",
            "u10-worker-principal-resolution-v1.schema.json",
            "resolution_digest",
        ),
    ):
        reference = binding[field]
        candidate_record = candidate_boundary[field]
        snapshot_ref = reference["snapshot_artifact_ref"]
        artifact_id = _snapshot_artifact_id(entries, snapshot_ref, role=role)
        artifact = entries[artifact_id]
        candidate_artifact_locator = str(
            Path(str(candidate_ref["candidate_locator"])).parent
            / "payload"
            / str(reference["candidate_relative_locator"])
        )
        expected_source = {
            "record_id": reference["record_id"],
            "locator": candidate_artifact_locator,
            "artifact_digest": reference["candidate_artifact_digest"],
            "semantic_digest": reference["semantic_digest"],
        }
        raw = _read_snapshot_artifact(snapshot_path, snapshot_ref)
        value = _load_json_bytes(raw, f"u10_snapshot_{role}_unreadable")
        _validate(value, schema_name, f"u10_snapshot_{role}_invalid")
        _sealed_digest(
            value,
            semantic_field,
            f"u10_snapshot_{role}_semantic_digest_invalid",
        )
        expected_record_projection = {
            "record_id": candidate_record["record_id"],
            "source_locator": candidate_record["source_locator"],
            "source_artifact_digest": candidate_record["source_artifact_digest"],
            "candidate_relative_locator": candidate_record["bundled_locator"],
            "candidate_artifact_digest": candidate_record["bundled_artifact_digest"],
            "semantic_digest": candidate_record["semantic_digest"],
            "snapshot_artifact_ref": snapshot_ref,
        }
        if (
            dict(reference) != expected_record_projection
            or artifact["source_ref"] != expected_source
            or reference["source_artifact_digest"] != digest_bytes(raw)
            or reference["candidate_artifact_digest"] != digest_bytes(raw)
            or snapshot_ref["artifact_digest"] != digest_bytes(raw)
            or snapshot_ref["semantic_digest"] != reference["semantic_digest"]
            or value[semantic_field] != reference["semantic_digest"]
        ):
            raise BrokerBoundaryError(
                "u10_snapshot_preactivation_record_binding_mismatch", field
            )
        loaded[field] = value

    decision = loaded["decision_record_ref"]
    observation = loaded["worker_account_observation_ref"]
    resolution = loaded["worker_principal_resolution_ref"]
    decision_reference = resolution["decision_record_ref"]
    decision_binding = binding["decision_record_ref"]
    effective = binding["effective_worker_identity"]
    expected_resolution_decision_ref = {
        "record_id": decision_binding["record_id"],
        "locator": decision_binding["source_locator"],
        "artifact_digest": decision_binding["source_artifact_digest"],
        "semantic_digest": decision_binding["semantic_digest"],
    }
    observation_binding = binding["worker_account_observation_ref"]
    expected_resolution_observation_ref = {
        "record_id": observation_binding["record_id"],
        "locator": observation_binding["source_locator"],
        "artifact_digest": observation_binding["source_artifact_digest"],
        "semantic_digest": observation_binding["semantic_digest"],
    }
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
    current_account = (
        _current_worker_account_material_v1(observation["account_name"])
        if reobserve_current_account
        else observed_account
    )
    if (
        decision["decision_id"] != decision_binding["record_id"]
        or decision["human_decision"] != "accept"
        or decision["decision_owner"] != "human"
        or decision["threat_boundary_selection"] != binding["threat_boundary"]
        or decision["worker_identity_selection"] != binding["worker_identity_policy"]
        or _entity_id_from_reference_v1(
            decision["subject_entity_ref"],
            code="u10_snapshot_subject_entity_reference_invalid",
        )
        != binding["subject_entity_id"]
        or observation["observation_id"] != observation_binding["record_id"]
        or observation["decision_record_ref"] != expected_resolution_decision_ref
        or observation["worker_identity_selection"] != binding["worker_identity_policy"]
        or _entity_id_from_reference_v1(
            observation["subject_entity_ref"],
            code="u10_snapshot_observation_subject_reference_invalid",
        )
        != binding["subject_entity_id"]
        or _entity_id_from_reference_v1(
            observation["derived_from"],
            code="u10_snapshot_observation_lineage_reference_invalid",
        )
        != _entity_id_from_reference_v1(
            decision["decision_entity_ref"],
            code="u10_snapshot_decision_entity_reference_invalid",
        )
        or _entity_id_from_reference_v1(
            observation["principal_entity_ref"],
            code="u10_snapshot_observation_principal_reference_invalid",
        )
        != binding["worker_principal_entity_id"]
        or current_account != observed_account
        or resolution["resolution_id"]
        != binding["worker_principal_resolution_ref"]["record_id"]
        or resolution["resolution_state"] != "resolved"
        or resolution["worker_identity_selection"] != binding["worker_identity_policy"]
        or decision_reference != expected_resolution_decision_ref
        or resolution["account_observation_ref"] != expected_resolution_observation_ref
        or _entity_id_from_reference_v1(
            resolution["derived_from"],
            code="u10_snapshot_resolution_lineage_reference_invalid",
        )
        != _entity_id_from_reference_v1(
            observation["observation_entity_ref"],
            code="u10_snapshot_observation_entity_reference_invalid",
        )
        or _entity_id_from_reference_v1(
            resolution["principal_entity_ref"],
            code="u10_snapshot_principal_entity_reference_invalid",
        )
        != binding["worker_principal_entity_id"]
        or resolution["account_name"] != observation["account_name"]
        or resolution["uid"] != observation["uid"]
        or resolution["gid"] != observation["gid"]
        or resolution["account_supplementary_gids"]
        != observation["account_supplementary_gids"]
        or resolution["login_shell"] != observation["login_shell"]
        or resolution["non_login"] != observation["non_login"]
        or resolution["platform_binding"] != observation["platform_binding"]
        or effective
        != {
            "uid": resolution["uid"],
            "gid": resolution["gid"],
            "effective_supplementary_gids": resolution["effective_supplementary_gids"],
            "umask": resolution["umask"],
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
            "effective_supplementary_gids": entry["execution_supplementary_gids"],
            "umask": entry["execution_umask"],
        }
        or manifest["worker_identity"]["account_supplementary_gids"]
        != observation["account_supplementary_gids"]
        or manifest["worker_identity"]["login_shell"] != observation["login_shell"]
        or manifest["worker_identity"]["non_login"] != observation["non_login"]
        or manifest["worker_identity"]["principal_entity_id"]
        != binding["worker_principal_entity_id"]
        or manifest["worker_identity"]["principal_resolution_digest"]
        != binding["worker_principal_resolution_ref"]["semantic_digest"]
    ):
        raise BrokerBoundaryError(
            "u10_snapshot_preactivation_identity_context_mismatch",
            str(decision.get("decision_id", "")),
        )
    _require_time_order(
        ("preactivation_decision_recorded_at", decision["recorded_at"]),
        ("worker_account_observed_at", observation["observed_at"]),
        ("worker_principal_resolved_at", resolution["resolved_at"]),
    )


def _validate_snapshot_adoption_authorization_v1(
    manifest: Mapping[str, Any],
    *,
    entry_id: str,
    projection_receipt_ref: Mapping[str, Any],
    environment_adoption_ref: Mapping[str, Any],
) -> dict[str, Any]:
    reference = manifest.get("snapshot_adoption_authorization_ref")
    if not isinstance(reference, Mapping):
        raise BrokerBoundaryError(
            "u10_snapshot_adoption_authorization_missing", entry_id
        )
    record_id = str(reference.get("record_id", ""))
    path = Path(str(reference.get("locator", "")))
    if (
        path.parent != AUTHORIZATION_ROOT
        or path.name != f"{record_id}.json"
        or not record_id
    ):
        raise BrokerBoundaryError(
            "u10_snapshot_adoption_authorization_path_mismatch", str(path)
        )
    raw = _verify_root_artifact(reference)
    authorization = _load_json_bytes(
        raw, "u10_snapshot_adoption_authorization_unreadable"
    )
    _validate(
        authorization,
        "u10-snapshot-adoption-authorization-v1.schema.json",
        "u10_snapshot_adoption_authorization_invalid",
    )
    _sealed_digest(
        authorization,
        "authorization_digest",
        "u10_snapshot_adoption_authorization_digest_mismatch",
    )
    if (
        authorization["authorization_id"] != record_id
        or authorization["authorization_digest"] != reference["semantic_digest"]
        or authorization["snapshot_id"] != manifest["snapshot_id"]
        or authorization["snapshot_version"] != manifest["snapshot_version"]
        or authorization["snapshot_basis_digest"] != manifest["snapshot_basis_digest"]
        or authorization["snapshot_basis_digest"] != snapshot_basis_digest_v1(manifest)
        or authorization["entry_id"] != entry_id
        or authorization["projection_receipt_ref"] != projection_receipt_ref
        or authorization["environment_adoption_ref"] != environment_adoption_ref
    ):
        raise BrokerBoundaryError(
            "u10_snapshot_adoption_authorization_context_mismatch", record_id
        )
    return authorization


def _exact_root_record_ref_v1(
    *,
    record_id: str,
    path: Path,
    raw: bytes,
    semantic_digest: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "record_id": record_id,
        "locator": str(path),
        "artifact_digest": digest_bytes(raw),
        "semantic_digest": dict(semantic_digest),
    }


def _exact_root_managed_record_ref_v1(
    *,
    record_id: str,
    path: Path,
    raw: bytes,
    semantic_digest: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        **_exact_root_record_ref_v1(
            record_id=record_id,
            path=path,
            raw=raw,
            semantic_digest=semantic_digest,
        ),
        "owner_uid": 0,
        "owner_gid": 0,
        "write_protection": "not_group_or_world_writable",
    }


def _load_sealed_root_record_v1(
    reference: Mapping[str, Any],
    *,
    expected_root: Path,
    expected_name: str,
    schema_name: str,
    seal_field: str,
    unreadable_code: str,
    invalid_code: str,
    digest_code: str,
) -> tuple[dict[str, Any], bytes, Path]:
    path = Path(str(reference.get("locator", "")))
    if path.parent != expected_root or path.name != expected_name:
        raise BrokerBoundaryError(invalid_code, str(path))
    raw = _verify_root_artifact(reference)
    value = _load_json_bytes(raw, unreadable_code)
    _validate(value, schema_name, invalid_code)
    _sealed_digest(value, seal_field, digest_code)
    return value, raw, path


def _validate_snapshot_environment_adoption_v1(
    *,
    manifest: Mapping[str, Any],
    entry: Mapping[str, Any],
    entry_id: str,
    source: Mapping[str, Any],
    profile: Mapping[str, Any],
    environment: Mapping[str, Any],
    entries: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Validate the external environment decision and projection occurrence.

    Candidate lifecycle remains inside the immutable snapshot.  Only this
    root-held, digest-bound decision opens the exact environment-use gate; it
    neither rewrites the candidate source nor grants an engineering verdict.
    """

    reference = manifest.get("environment_adoption_ref")
    if not isinstance(reference, Mapping):
        raise BrokerBoundaryError("u10_snapshot_environment_adoption_missing", entry_id)
    adoption_id = str(reference.get("record_id", ""))
    adoption, adoption_raw, adoption_path = _load_sealed_root_record_v1(
        reference,
        expected_root=AUTHORIZATION_ROOT,
        expected_name=f"{adoption_id}.json",
        schema_name="u10-snapshot-environment-adoption-v1.schema.json",
        seal_field="adoption_digest",
        unreadable_code="u10_snapshot_environment_adoption_unreadable",
        invalid_code="u10_snapshot_environment_adoption_invalid",
        digest_code="u10_snapshot_environment_adoption_digest_mismatch",
    )
    if adoption_raw != canonical_json_bytes(adoption) + b"\n":
        raise BrokerBoundaryError(
            "u10_snapshot_environment_adoption_noncanonical",
            str(adoption_path),
        )
    exact_adoption_ref = _exact_root_record_ref_v1(
        record_id=adoption["adoption_id"],
        path=adoption_path,
        raw=adoption_raw,
        semantic_digest=adoption["adoption_digest"],
    )
    if (
        adoption_id != adoption["adoption_id"]
        or dict(reference) != exact_adoption_ref
        or entry.get("environment_adoption_binding") != exact_adoption_ref
        or adoption["formal_authority"] != "none"
        or adoption["positive_assurance_allowed"] is not False
    ):
        raise BrokerBoundaryError(
            "u10_snapshot_environment_adoption_binding_mismatch", entry_id
        )

    projection_ref = adoption["projection_receipt_ref"]
    projection_locator = Path(str(projection_ref.get("locator", "")))
    if (
        projection_locator.parent != SNAPSHOT_PROJECTION_LEDGER_ROOT
        or not projection_locator.name.endswith(".receipt.json")
    ):
        raise BrokerBoundaryError(
            "u10_snapshot_projection_receipt_path_mismatch",
            str(projection_locator),
        )
    projection, projection_raw, _ = _load_sealed_root_record_v1(
        projection_ref,
        expected_root=SNAPSHOT_PROJECTION_LEDGER_ROOT,
        expected_name=projection_locator.name,
        schema_name="u10-snapshot-projection-receipt-v1.schema.json",
        seal_field="receipt_digest",
        unreadable_code="u10_snapshot_projection_receipt_unreadable",
        invalid_code="u10_snapshot_projection_receipt_invalid",
        digest_code="u10_snapshot_projection_receipt_digest_mismatch",
    )
    exact_projection_ref = _exact_root_record_ref_v1(
        record_id=projection["receipt_id"],
        path=projection_locator,
        raw=projection_raw,
        semantic_digest=projection["receipt_digest"],
    )
    projection_authorization_id = str(projection["public_identifier"])
    if (
        dict(projection_ref) != exact_projection_ref
        or projection_locator.name != f"{projection_authorization_id}.receipt.json"
        or projection["public_operation"] != "project-snapshot"
        or projection["projection_occurred"] is not True
        or projection["snapshot_manifest_published"] is not False
    ):
        raise BrokerBoundaryError(
            "u10_snapshot_projection_receipt_binding_mismatch", entry_id
        )
    _validate_publisher_contract_binding_v1(
        projection["publisher_contract_binding"], enforce_current=False
    )

    projection_consumption_path = (
        SNAPSHOT_PROJECTION_LEDGER_ROOT
        / f"{projection_authorization_id}.consumption.json"
    )
    projection_consumption_raw = read_protected_file(
        projection_consumption_path,
        protected_root=SNAPSHOT_PROJECTION_LEDGER_ROOT,
    )
    projection_consumption = _load_json_bytes(
        projection_consumption_raw,
        "u10_snapshot_projection_consumption_unreadable",
    )
    _validate(
        projection_consumption,
        "u10-snapshot-projection-authorization-consumption-v1.schema.json",
        "u10_snapshot_projection_consumption_invalid",
    )
    _sealed_digest(
        projection_consumption,
        "consumption_digest",
        "u10_snapshot_projection_consumption_digest_mismatch",
    )
    _validate_publisher_contract_binding_v1(
        projection_consumption["publisher_contract_binding"],
        enforce_current=False,
    )
    if (
        projection_consumption["public_operation"] != "project-snapshot"
        or projection_consumption["public_identifier"] != projection_authorization_id
        or projection_consumption["publisher_contract_binding"]
        != projection["publisher_contract_binding"]
        or projection["consumption_ref"]
        != {
            "consumption_id": projection_consumption["consumption_id"],
            "consumption_digest": projection_consumption["consumption_digest"],
        }
    ):
        raise BrokerBoundaryError(
            "u10_snapshot_projection_consumption_binding_mismatch", entry_id
        )

    archived_authorization_path = (
        SNAPSHOT_PROJECTION_LEDGER_ROOT
        / f"{projection_authorization_id}.authorization.json"
    )
    archived_authorization_raw = read_protected_file(
        archived_authorization_path,
        protected_root=SNAPSHOT_PROJECTION_LEDGER_ROOT,
    )
    projection_authorization = _load_json_bytes(
        archived_authorization_raw,
        "u10_snapshot_projection_authorization_unreadable",
    )
    _validate(
        projection_authorization,
        "u10-snapshot-projection-authorization-v1.schema.json",
        "u10_snapshot_projection_authorization_invalid",
    )
    _sealed_digest(
        projection_authorization,
        "authorization_digest",
        "u10_snapshot_projection_authorization_digest_mismatch",
    )
    expected_projection_authorization_ref = {
        "authorization_id": projection_authorization_id,
        "artifact_digest": digest_bytes(archived_authorization_raw),
        "authorization_digest": projection_authorization["authorization_digest"],
    }
    if (
        projection_authorization["authorization_id"] != projection_authorization_id
        or projection["authorization_ref"] != expected_projection_authorization_ref
        or projection_consumption["authorization_ref"]
        != expected_projection_authorization_ref
        or projection["bundle_ref"] != projection_authorization["bundle_ref"]
        or projection["snapshot_ref"] != projection_authorization["target_snapshot"]
    ):
        raise BrokerBoundaryError(
            "u10_snapshot_projection_authorization_binding_mismatch", entry_id
        )

    expected_snapshot_ref = {
        "snapshot_id": manifest["snapshot_id"],
        "snapshot_version": manifest["snapshot_version"],
        "snapshot_path": manifest["root_storage"]["snapshot_path"],
        "tree_digest": manifest["root_storage"]["tree_digest"],
        "snapshot_basis_digest": manifest["snapshot_basis_digest"],
    }
    expected_projected_basis = {
        "eligibility_source_ref": {
            "source_id": manifest["eligibility_source_ref"]["source_id"],
            "source_version": manifest["eligibility_source_ref"]["source_version"],
            "lifecycle_state": manifest["eligibility_source_ref"]["lifecycle_state"],
            "snapshot_artifact_ref": manifest["eligibility_source_ref"][
                "snapshot_artifact_ref"
            ],
            "source_digest": manifest["eligibility_source_ref"]["source_digest"],
        },
        "verification_profile_ref": {
            "profile_id": manifest["verification_profile_ref"]["profile_id"],
            "profile_version": manifest["verification_profile_ref"]["profile_version"],
            "snapshot_artifact_ref": manifest["verification_profile_ref"][
                "snapshot_artifact_ref"
            ],
            "content_digest": manifest["verification_profile_ref"]["content_digest"],
        },
        "environment_profile_ref": {
            "environment_profile_id": manifest["environment_profile_ref"][
                "environment_profile_id"
            ],
            "environment_profile_version": manifest["environment_profile_ref"][
                "environment_profile_version"
            ],
            "lifecycle_state": environment["lifecycle_state"],
            "snapshot_artifact_ref": manifest["environment_profile_ref"][
                "snapshot_artifact_ref"
            ],
            "basis_digest": manifest["environment_profile_ref"]["basis_digest"],
        },
        "host_identity_evidence_ref": adoption["host_identity_evidence_ref"],
        "decision_owner_ref": source["adoption_record"]["decision_owner_ref"],
    }
    expected_projected_basis["basis_digest"] = digest_bytes(
        canonical_json_bytes(expected_projected_basis)
    )
    if (
        source["lifecycle_state"] != "candidate"
        or source["adoption_record"]["record_kind"] != "adoption_request"
        or source["adoption_record"]["human_decision"] != "pending"
        or source["adoption_record"]["recorded_at"] is not None
        or adoption["snapshot_ref"] != expected_snapshot_ref
        or adoption["eligibility_source_ref"]
        != expected_projected_basis["eligibility_source_ref"]
        or adoption["verification_profile_ref"]
        != expected_projected_basis["verification_profile_ref"]
        or adoption["environment_profile_ref"]
        != expected_projected_basis["environment_profile_ref"]
        or adoption["decision_owner_ref"]
        != expected_projected_basis["decision_owner_ref"]
        or projection["projected_environment_basis"] != expected_projected_basis
        or projection["tree_digest"] != manifest["root_storage"]["tree_digest"]
        or projection["snapshot_basis_digest"] != manifest["snapshot_basis_digest"]
        or projection["artifact_denominator"]["denominator_digest"]
        != digest_bytes(canonical_json_bytes(entries))
    ):
        raise BrokerBoundaryError(
            "u10_snapshot_external_environment_basis_mismatch", entry_id
        )

    host_ref = adoption["host_identity_evidence_ref"]
    host_matches = [
        artifact
        for artifact in entries.values()
        if artifact.get("role") == "host_identity_evidence"
        and artifact.get("snapshot_ref") == host_ref["snapshot_artifact_ref"]
    ]
    if len(host_matches) != 1:
        raise BrokerBoundaryError(
            "u10_snapshot_external_host_evidence_mismatch", entry_id
        )
    host_raw = _read_snapshot_artifact(
        Path(str(manifest["root_storage"]["snapshot_path"])),
        host_ref["snapshot_artifact_ref"],
    )
    host_value = _load_json_bytes(
        host_raw, "u10_snapshot_external_host_evidence_unreadable"
    )
    _validate(
        host_value,
        "local-host-identity-evidence-v1.schema.json",
        "u10_snapshot_external_host_evidence_invalid",
    )
    _sealed_digest(
        host_value,
        "evidence_digest",
        "u10_snapshot_external_host_evidence_digest_mismatch",
    )
    if (
        host_ref["evidence_id"] != host_value["evidence_id"]
        or host_ref["identity_digest"] != host_value["identity_digest"]
        or host_ref["evidence_digest"] != host_value["evidence_digest"]
    ):
        raise BrokerBoundaryError(
            "u10_snapshot_external_host_evidence_mismatch", entry_id
        )

    for field in (
        "decision_owner_authority_evidence_ref",
        "decision_evidence_ref",
        "trusted_entrypoint_ref",
    ):
        _verify_root_artifact(adoption[field])
    _require_repository_refs_in_denominator(
        adoption["decision_owner_ref"], entries=entries
    )
    _require_time_order(
        (
            "snapshot_projection_authorized_at",
            projection_authorization["recorded_at"],
        ),
        (
            "snapshot_projection_reserved_at",
            projection_consumption["reserved_at"],
        ),
        (
            "snapshot_projection_dependency_started_at",
            projection["dependency_lock_check"]["started_at"],
        ),
        (
            "snapshot_projection_dependency_finished_at",
            projection["dependency_lock_check"]["finished_at"],
        ),
        (
            "snapshot_environment_projection_started_at",
            projection["environment_projection_check"]["started_at"],
        ),
        (
            "snapshot_environment_projection_finished_at",
            projection["environment_projection_check"]["finished_at"],
        ),
        ("snapshot_immutability_verified_at", projection["immutability_verified_at"]),
        ("snapshot_projection_observed_at", projection["projection_observed_at"]),
        ("snapshot_projection_receipt_recorded_at", projection["receipt_recorded_at"]),
        ("snapshot_environment_adopted_at", adoption["recorded_at"]),
    )
    return adoption, projection, projection_authorization


def _load_execution_environment_adoption_v1(
    *,
    snapshot: Mapping[str, Any],
    entry: Mapping[str, Any],
    entry_id: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Re-read the exact external adoption for the worker trust context.

    ``load_active_snapshot_manifest_v1`` has already validated the complete
    adoption/projection/authorization chain.  This second read deliberately
    keeps the exact decision material alive in the trusted execution context
    instead of silently collapsing it into the candidate source.
    """

    reference = snapshot.get("environment_adoption_ref")
    if not isinstance(reference, Mapping):
        raise BrokerBoundaryError("u10_snapshot_environment_adoption_missing", entry_id)
    adoption_id = str(reference.get("record_id", ""))
    adoption, raw, path = _load_sealed_root_record_v1(
        reference,
        expected_root=AUTHORIZATION_ROOT,
        expected_name=f"{adoption_id}.json",
        schema_name="u10-snapshot-environment-adoption-v1.schema.json",
        seal_field="adoption_digest",
        unreadable_code="u10_snapshot_environment_adoption_unreadable",
        invalid_code="u10_snapshot_environment_adoption_invalid",
        digest_code="u10_snapshot_environment_adoption_digest_mismatch",
    )
    if raw != canonical_json_bytes(adoption) + b"\n":
        raise BrokerBoundaryError(
            "u10_snapshot_environment_adoption_noncanonical", str(path)
        )
    exact_ref = _exact_root_record_ref_v1(
        record_id=adoption["adoption_id"],
        path=path,
        raw=raw,
        semantic_digest=adoption["adoption_digest"],
    )
    if (
        adoption_id != adoption["adoption_id"]
        or dict(reference) != exact_ref
        or entry.get("environment_adoption_binding") != exact_ref
        or adoption["formal_authority"] != "none"
        or adoption["positive_assurance_allowed"] is not False
    ):
        raise BrokerBoundaryError(
            "u10_snapshot_environment_adoption_binding_mismatch", entry_id
        )
    return adoption, exact_ref


def _source_ref_matches(
    source_ref: Mapping[str, Any], reference: Mapping[str, Any]
) -> bool:
    semantic = reference.get("content_digest")
    return (
        source_ref.get("record_id") == reference.get("record_id")
        and source_ref.get("locator") == reference.get("locator")
        and source_ref.get("semantic_digest") == semantic
    )


def _require_repository_refs_in_denominator(
    value: Any,
    *,
    entries: Mapping[str, Any],
) -> None:
    if isinstance(value, Mapping):
        if {
            "record_id",
            "locator",
            "content_digest",
        }.issubset(value):
            matches = [
                artifact_id
                for artifact_id, artifact in entries.items()
                if _source_ref_matches(artifact["source_ref"], value)
            ]
            if len(matches) != 1:
                raise BrokerBoundaryError(
                    "u10_repository_reference_not_closed",
                    repr({"reference": value, "matches": matches}),
                )
        for child in value.values():
            _require_repository_refs_in_denominator(child, entries=entries)
    elif isinstance(value, list):
        for child in value:
            _require_repository_refs_in_denominator(child, entries=entries)


def _tree_digest(root: Path, *, excluded: frozenset[Path]) -> dict[str, str]:
    records: list[dict[str, Any]] = []
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
            relative = path.relative_to(root).as_posix()
            if stat.S_ISDIR(observed.st_mode):
                records.append(
                    {
                        "path": relative,
                        "kind": "directory",
                        "mode": stat.S_IMODE(observed.st_mode),
                        "uid": observed.st_uid,
                        "gid": observed.st_gid,
                    }
                )
            elif stat.S_ISREG(observed.st_mode):
                raw = read_protected_file(path, protected_root=root)
                records.append(
                    {
                        "path": relative,
                        "kind": "file",
                        "mode": stat.S_IMODE(observed.st_mode),
                        "uid": observed.st_uid,
                        "gid": observed.st_gid,
                        "size": observed.st_size,
                        "digest": digest_bytes(raw),
                    }
                )
            else:
                raise BrokerBoundaryError("u10_snapshot_special_file", str(path))
    return digest_bytes(canonical_json_bytes({"entries": records}))


def _regular_file_set(root: Path, *, excluded: frozenset[Path]) -> set[Path]:
    """Return the exact regular-file denominator for a protected tree."""

    result: set[Path] = set()
    for raw_directory, directories, files in os.walk(
        root, topdown=True, followlinks=False
    ):
        base = Path(raw_directory)
        directories.sort()
        files.sort()
        for name in files:
            path = base / name
            if path in excluded:
                continue
            observed = path.lstat()
            if not stat.S_ISREG(observed.st_mode) or stat.S_ISLNK(observed.st_mode):
                raise BrokerBoundaryError("u10_snapshot_special_file", str(path))
            result.add(path)
    return result


def load_active_snapshot_manifest_v1(
    store: Mapping[str, Any],
    entry_id: str,
    *,
    enforce_current_runtime: bool = True,
    reobserve_current_account: bool = True,
) -> tuple[dict[str, Any], dict[str, Any]]:
    entry = store["entries"].get(entry_id)
    if not isinstance(entry, Mapping) or entry.get("entry_state") != "active":
        raise BrokerBoundaryError("u10_trust_entry_not_active", entry_id)
    binding = entry["snapshot_manifest_binding"]
    manifest_path = Path(str(binding["locator"]))
    raw = read_protected_file(manifest_path, protected_root=SNAPSHOT_ROOT)
    if digest_bytes(raw) != binding["artifact_digest"]:
        raise BrokerBoundaryError("u10_snapshot_manifest_artifact_mismatch", entry_id)
    manifest = _load_json_bytes(raw, "u10_snapshot_manifest_unreadable")
    _validate(
        manifest,
        "u10-execution-snapshot-manifest-v1.schema.json",
        "u10_snapshot_manifest_invalid",
    )
    _sealed_digest(manifest, "manifest_digest", "u10_snapshot_manifest_digest_mismatch")
    if manifest["snapshot_basis_digest"] != snapshot_basis_digest_v1(manifest):
        raise BrokerBoundaryError("u10_snapshot_basis_digest_mismatch", entry_id)
    if manifest["lifecycle_state"] != "active":
        raise BrokerBoundaryError("u10_snapshot_manifest_not_active", entry_id)
    if manifest["prepared_for_entry_id"] != entry_id:
        raise BrokerBoundaryError("u10_snapshot_entry_binding_mismatch", entry_id)
    if manifest["manifest_digest"] != binding["manifest_digest"]:
        raise BrokerBoundaryError("u10_snapshot_semantic_digest_mismatch", entry_id)
    if (
        manifest["snapshot_id"] != binding["snapshot_id"]
        or manifest["snapshot_version"] != binding["snapshot_version"]
    ):
        raise BrokerBoundaryError("u10_snapshot_identity_mismatch", entry_id)
    snapshot_path = Path(str(manifest["root_storage"]["snapshot_path"]))
    try:
        manifest_path.relative_to(snapshot_path)
    except ValueError as exc:
        raise BrokerBoundaryError(
            "u10_snapshot_manifest_outside_snapshot", str(manifest_path)
        ) from exc
    validate_protected_tree(snapshot_path)
    _verify_declared_directory(
        snapshot_path,
        uid=int(manifest["root_storage"]["owner_uid"]),
        gid=int(manifest["root_storage"]["owner_gid"]),
        mode=int(manifest["root_storage"]["directory_mode"], 8),
        code="u10_snapshot_directory_mismatch",
    )
    observed_tree = _tree_digest(
        snapshot_path,
        excluded=frozenset({manifest_path}),
    )
    if observed_tree != manifest["root_storage"]["tree_digest"]:
        raise BrokerBoundaryError("u10_snapshot_tree_digest_mismatch", entry_id)
    entries = manifest["artifact_denominator"]["entries"]
    for artifact_id, artifact in entries.items():
        reference = artifact["snapshot_ref"]
        if artifact_id != reference["record_id"]:
            raise BrokerBoundaryError(
                "u10_snapshot_artifact_identity_mismatch", str(artifact_id)
            )
        _read_snapshot_artifact(snapshot_path, reference)
    snapshot_refs = [
        canonical_json_bytes(artifact["snapshot_ref"]) for artifact in entries.values()
    ]
    if len(snapshot_refs) != len(set(snapshot_refs)):
        raise BrokerBoundaryError("u10_snapshot_duplicate_artifact_ref", entry_id)
    declared_regular_files = {
        Path(str(artifact["snapshot_ref"]["locator"])) for artifact in entries.values()
    }
    observed_regular_files = _regular_file_set(
        snapshot_path,
        excluded=frozenset({manifest_path}),
    )
    if declared_regular_files != observed_regular_files:
        raise BrokerBoundaryError(
            "u10_snapshot_artifact_denominator_not_closed",
            repr(
                {
                    "missing": sorted(
                        map(str, observed_regular_files - declared_regular_files)
                    ),
                    "extra": sorted(
                        map(str, declared_regular_files - observed_regular_files)
                    ),
                }
            ),
        )
    _validate_preactivation_boundary_binding_v1(
        manifest=manifest,
        entry=entry,
        snapshot_path=snapshot_path,
        entries=entries,
        reobserve_current_account=reobserve_current_account,
    )
    if manifest["broker_runtime_ref"] != store["broker_runtime_ref"]:
        raise BrokerBoundaryError("u10_snapshot_broker_runtime_mismatch", entry_id)
    launch_contract = manifest["broker_launch_contract"]
    if (
        launch_contract["entrypoint_ref"] != store["broker_entrypoint_ref"]
        or launch_contract["outer_launcher_ref"] != store["broker_outer_launcher_ref"]
        or launch_contract["platform_binding_digest"]
        != digest_bytes(canonical_json_bytes(store["broker_launch_platform"]))
    ):
        raise BrokerBoundaryError(
            "u10_snapshot_outer_launch_binding_mismatch", entry_id
        )
    broker_raw = _verify_root_artifact(manifest["broker_runtime_ref"])
    if manifest["broker_runtime_ref"]["semantic_digest"] != digest_bytes(broker_raw):
        raise BrokerBoundaryError(
            "u10_snapshot_broker_runtime_semantic_mismatch", entry_id
        )
    _snapshot_artifact_id(
        entries, manifest["broker_runtime_ref"], role="broker_runtime"
    )
    runtime = manifest["worker_runtime"]
    expected_roles = {
        "python_interpreter": runtime["interpreter_snapshot_ref"],
        "worker_entrypoint": runtime["worker_entrypoint_snapshot_ref"],
    }
    for role, expected_ref in expected_roles.items():
        matches = [
            artifact["snapshot_ref"]
            for artifact in entries.values()
            if artifact["role"] == role
        ]
        if matches != [expected_ref]:
            raise BrokerBoundaryError(
                "u10_snapshot_worker_runtime_denominator_mismatch", role
            )
    expected_worker = {
        "uid": entry["execution_uid"],
        "gid": entry["execution_gid"],
        "effective_supplementary_gids": entry["execution_supplementary_gids"],
        "umask": entry["execution_umask"],
    }
    if {
        field: manifest["worker_identity"][field] for field in expected_worker
    } != expected_worker or manifest["worker_identity"]["root_prohibited"] is not True:
        raise BrokerBoundaryError("u10_snapshot_worker_identity_mismatch", entry_id)
    _verify_worker_snapshot_access(
        snapshot_path,
        uid=int(expected_worker["uid"]),
        gid=int(expected_worker["gid"]),
        supplementary_gids=tuple(expected_worker["effective_supplementary_gids"]),
        interpreter=Path(str(runtime["interpreter_snapshot_ref"]["locator"])),
    )
    if enforce_current_runtime:
        interpreter = Path(str(runtime["interpreter_snapshot_ref"]["locator"]))
        if Path(os.path.realpath(sys.executable)) != interpreter:
            raise BrokerBoundaryError(
                "u10_broker_interpreter_not_snapshot_bound", str(sys.executable)
            )
        for runtime_file in (
            Path(__file__).resolve(strict=True),
            Path(__file__).with_name("protected_io.py").resolve(strict=True),
            Path(__file__).with_name("supervisor.py").resolve(strict=True),
            Path(__file__).with_name("__init__.py").resolve(strict=True),
        ):
            try:
                runtime_file.relative_to(snapshot_path)
            except ValueError as exc:
                raise BrokerBoundaryError(
                    "u10_broker_module_not_snapshot_bound", str(runtime_file)
                ) from exc
            matches = [
                artifact_id
                for artifact_id, artifact in entries.items()
                if artifact["role"] == "broker_runtime"
                and Path(str(artifact["snapshot_ref"]["locator"])) == runtime_file
            ]
            if len(matches) != 1:
                raise BrokerBoundaryError(
                    "u10_broker_module_denominator_mismatch", str(runtime_file)
                )
    runtime_tree_refs = [
        runtime["subject_source_root"],
        *runtime["dependency_import_roots"],
    ]
    runtime_tree_paths = [Path(str(item["locator"])) for item in runtime_tree_refs]
    if len(runtime_tree_paths) != len(set(runtime_tree_paths)) or any(
        left != right and (left in right.parents or right in left.parents)
        for index, left in enumerate(runtime_tree_paths)
        for right in runtime_tree_paths[index + 1 :]
    ):
        raise BrokerBoundaryError(
            "u10_snapshot_runtime_tree_overlap", repr(runtime_tree_paths)
        )
    for tree_ref in runtime_tree_refs:
        tree_path = Path(str(tree_ref["locator"]))
        validate_protected_tree(tree_path)
        if _tree_digest(tree_path, excluded=frozenset()) != tree_ref["tree_digest"]:
            raise BrokerBoundaryError(
                "u10_snapshot_runtime_tree_digest_mismatch",
                str(tree_ref["tree_id"]),
            )
        required_ids = set(tree_ref["required_artifact_ids"])
        if not required_ids.issubset(entries):
            raise BrokerBoundaryError(
                "u10_snapshot_runtime_tree_artifact_missing",
                str(tree_ref["tree_id"]),
            )
        observed_tree_ids: set[str] = set()
        for artifact_id, artifact in entries.items():
            locator = Path(str(artifact["snapshot_ref"]["locator"]))
            try:
                locator.relative_to(tree_path)
            except ValueError:
                continue
            observed_tree_ids.add(str(artifact_id))
        if required_ids != observed_tree_ids:
            raise BrokerBoundaryError(
                "u10_snapshot_runtime_tree_denominator_mismatch",
                repr(
                    {
                        "tree_id": tree_ref["tree_id"],
                        "missing": sorted(observed_tree_ids - required_ids),
                        "extra": sorted(required_ids - observed_tree_ids),
                    }
                ),
            )
    if {
        key: manifest["source_repository_binding"][key]
        for key in ("canonical_path", "device_id", "inode")
    } != entry["repository_binding"]:
        raise BrokerBoundaryError("u10_snapshot_repository_binding_mismatch", entry_id)
    binding_specs = (
        (
            entry["eligibility_source_binding"],
            manifest["eligibility_source_ref"],
            "source_id",
            "source_version",
            "source_digest",
            "lifecycle_state",
        ),
        (
            entry["verification_profile_binding"],
            manifest["verification_profile_ref"],
            "profile_id",
            "profile_version",
            "content_digest",
            None,
        ),
        (
            entry["environment_profile_binding"],
            manifest["environment_profile_ref"],
            "environment_profile_id",
            "environment_profile_version",
            "basis_digest",
            None,
        ),
    )
    for (
        entry_binding,
        manifest_ref,
        id_field,
        version_field,
        digest_field,
        state_field,
    ) in binding_specs:
        source_ref = manifest_ref["source_artifact_ref"]
        checks = (
            entry_binding[id_field] == manifest_ref[id_field],
            entry_binding[version_field] == manifest_ref[version_field],
            entry_binding["locator"] == source_ref["locator"],
            entry_binding["artifact_digest"] == source_ref["artifact_digest"],
            entry_binding[digest_field] == manifest_ref[digest_field],
        )
        if state_field is not None:
            checks = (*checks, entry_binding[state_field] == manifest_ref[state_field])
        if not all(checks):
            raise BrokerBoundaryError(
                "u10_snapshot_trust_entry_binding_mismatch", digest_field
            )
    source = _semantic_json_artifact(
        snapshot_path=snapshot_path,
        entries=entries,
        reference=manifest["eligibility_source_ref"]["snapshot_artifact_ref"],
        role="eligibility_source",
        semantic_field="source_digest",
        schema_name="environment-eligibility-source-v1.schema.json",
        code="u10_snapshot_eligibility_source_invalid",
    )
    profile = _semantic_json_artifact(
        snapshot_path=snapshot_path,
        entries=entries,
        reference=manifest["verification_profile_ref"]["snapshot_artifact_ref"],
        role="verification_profile",
        semantic_field=None,
        schema_name="local-verification-profile-v4.schema.json",
        code="u10_snapshot_verification_profile_invalid",
    )
    environment = _semantic_json_artifact(
        snapshot_path=snapshot_path,
        entries=entries,
        reference=manifest["environment_profile_ref"]["snapshot_artifact_ref"],
        role="environment_profile",
        semantic_field="basis_digest",
        schema_name="resolved-local-environment-profile-v1.schema.json",
        code="u10_snapshot_environment_profile_invalid",
    )
    _validate_current_host_identity_evidence_v1(
        snapshot_path=snapshot_path,
        entries=entries,
        environment=environment,
        reobserve_current_host=reobserve_current_account,
    )
    if (
        source["source_id"] != manifest["eligibility_source_ref"]["source_id"]
        or source["source_version"]
        != manifest["eligibility_source_ref"]["source_version"]
        or source["lifecycle_state"]
        != manifest["eligibility_source_ref"]["lifecycle_state"]
        or profile["profile_id"] != manifest["verification_profile_ref"]["profile_id"]
        or profile["profile_version"]
        != manifest["verification_profile_ref"]["profile_version"]
        or environment["environment_profile_id"]
        != manifest["environment_profile_ref"]["environment_profile_id"]
        or environment["environment_profile_version"]
        != manifest["environment_profile_ref"]["environment_profile_version"]
    ):
        raise BrokerBoundaryError("u10_snapshot_semantic_identity_mismatch", entry_id)
    adoption, projection, _projection_authorization = (
        _validate_snapshot_environment_adoption_v1(
            manifest=manifest,
            entry=entry,
            entry_id=entry_id,
            source=source,
            profile=profile,
            environment=environment,
            entries=entries,
        )
    )
    immutability = manifest["immutability_verification"]
    if immutability["verifier_runtime_ref"] != store["broker_runtime_ref"]:
        raise BrokerBoundaryError(
            "u10_snapshot_immutability_verifier_mismatch", entry_id
        )
    _verify_root_artifact(immutability["verifier_runtime_ref"])
    activation_ref = manifest["activation_ref"]
    snapshot_adoption_authorization = _validate_snapshot_adoption_authorization_v1(
        manifest,
        entry_id=entry_id,
        projection_receipt_ref=adoption["projection_receipt_ref"],
        environment_adoption_ref=manifest["environment_adoption_ref"],
    )
    activation_basis_path = Path(str(activation_ref["locator"]))
    if activation_basis_path.parent != SNAPSHOT_ACTIVATION_ROOT:
        raise BrokerBoundaryError(
            "u10_snapshot_activation_outside_activation_root", entry_id
        )
    activation_basis, activation_basis_raw, _ = _load_sealed_root_record_v1(
        activation_ref,
        expected_root=SNAPSHOT_ACTIVATION_ROOT,
        expected_name=activation_basis_path.name,
        schema_name="u10-snapshot-activation-basis-v1.schema.json",
        seal_field="activation_basis_digest",
        unreadable_code="u10_snapshot_activation_basis_unreadable",
        invalid_code="u10_snapshot_activation_basis_invalid",
        digest_code="u10_snapshot_activation_basis_digest_invalid",
    )
    exact_activation_basis_ref = _exact_root_record_ref_v1(
        record_id=activation_basis["activation_basis_id"],
        path=activation_basis_path,
        raw=activation_basis_raw,
        semantic_digest=activation_basis["activation_basis_digest"],
    )
    if (
        dict(activation_ref) != exact_activation_basis_ref
        or activation_basis_path.name
        != f"{activation_basis['activation_basis_id']}.json"
        or activation_basis["snapshot_id"] != manifest["snapshot_id"]
        or activation_basis["snapshot_version"] != manifest["snapshot_version"]
        or activation_basis["snapshot_basis_digest"]
        != manifest["snapshot_basis_digest"]
        or activation_basis["entry_id"] != entry_id
        or activation_basis["adoption_id"] != adoption["adoption_id"]
        or activation_basis["adoption_version"] != adoption["adoption_version"]
        or activation_basis["adoption_digest"] != adoption["adoption_digest"]
        or activation_basis["environment_adoption_ref"]
        != manifest["environment_adoption_ref"]
        or activation_basis["projection_receipt_ref"]
        != adoption["projection_receipt_ref"]
        or activation_basis["snapshot_adoption_authorization_ref"]
        != manifest["snapshot_adoption_authorization_ref"]
        or snapshot_adoption_authorization["authorization_digest"]
        != manifest["snapshot_adoption_authorization_ref"]["semantic_digest"]
        or activation_basis["immutability_verified_at"] != immutability["verified_at"]
        or projection["immutability_verified_at"] != immutability["verified_at"]
        or activation_basis["preparation_status"] != "prepared_for_manifest_publication"
    ):
        raise BrokerBoundaryError("u10_snapshot_activation_binding_mismatch", entry_id)

    activation_authorization_id = snapshot_adoption_authorization["authorization_id"]
    activation_consumption_path = (
        SNAPSHOT_ACTIVATION_LEDGER_ROOT
        / f"{activation_authorization_id}.consumption.json"
    )
    activation_consumption_raw = read_protected_file(
        activation_consumption_path,
        protected_root=SNAPSHOT_ACTIVATION_LEDGER_ROOT,
    )
    activation_consumption = _load_json_bytes(
        activation_consumption_raw,
        "u10_snapshot_activation_consumption_unreadable",
    )
    _validate(
        activation_consumption,
        "u10-snapshot-activation-authorization-consumption-v1.schema.json",
        "u10_snapshot_activation_consumption_invalid",
    )
    _sealed_digest(
        activation_consumption,
        "consumption_digest",
        "u10_snapshot_activation_consumption_digest_mismatch",
    )
    _validate_publisher_contract_binding_v1(
        activation_consumption["publisher_contract_binding"],
        enforce_current=False,
    )
    activation_receipt_path = (
        SNAPSHOT_ACTIVATION_LEDGER_ROOT / f"{activation_authorization_id}.receipt.json"
    )
    activation_receipt_raw = read_protected_file(
        activation_receipt_path,
        protected_root=SNAPSHOT_ACTIVATION_LEDGER_ROOT,
    )
    activation_receipt = _load_json_bytes(
        activation_receipt_raw,
        "u10_snapshot_activation_receipt_unreadable",
    )
    _validate(
        activation_receipt,
        "u10-snapshot-activation-publication-receipt-v1.schema.json",
        "u10_snapshot_activation_receipt_invalid",
    )
    _sealed_digest(
        activation_receipt,
        "receipt_digest",
        "u10_snapshot_activation_receipt_digest_mismatch",
    )
    _validate_publisher_contract_binding_v1(
        activation_receipt["publisher_contract_binding"],
        enforce_current=False,
    )
    expected_authorization_ref = _exact_root_record_ref_v1(
        record_id=snapshot_adoption_authorization["authorization_id"],
        path=Path(str(manifest["snapshot_adoption_authorization_ref"]["locator"])),
        raw=_verify_root_artifact(manifest["snapshot_adoption_authorization_ref"]),
        semantic_digest=snapshot_adoption_authorization["authorization_digest"],
    )
    expected_manifest_ref = _exact_root_record_ref_v1(
        record_id=manifest["snapshot_id"],
        path=manifest_path,
        raw=raw,
        semantic_digest=manifest["manifest_digest"],
    )
    store_activation_basis, _store_activation_basis_raw = (
        _load_store_activation_basis_any_v1(
            activation_receipt["store_activation_basis_ref"]
        )
    )
    if (
        activation_consumption["public_operation"] != "activate-snapshot"
        or activation_consumption["public_identifier"] != activation_authorization_id
        or activation_consumption["authorization_ref"] != expected_authorization_ref
        or activation_consumption["projection_receipt_ref"]
        != adoption["projection_receipt_ref"]
        or activation_consumption["environment_adoption_ref"]
        != manifest["environment_adoption_ref"]
        or activation_consumption["snapshot_id"] != manifest["snapshot_id"]
        or activation_consumption["snapshot_basis_digest"]
        != manifest["snapshot_basis_digest"]
        or activation_consumption["manifest_publication_occurred"] is not False
        or activation_receipt["public_operation"] != "activate-snapshot"
        or activation_receipt["public_identifier"] != activation_authorization_id
        or activation_receipt["authorization_ref"] != expected_authorization_ref
        or activation_receipt["consumption_ref"]
        != {
            "consumption_id": activation_consumption["consumption_id"],
            "consumption_digest": activation_consumption["consumption_digest"],
        }
        or activation_receipt["projection_receipt_ref"]
        != adoption["projection_receipt_ref"]
        or activation_receipt["environment_adoption_ref"]
        != manifest["environment_adoption_ref"]
        or activation_receipt["activation_ref"] != exact_activation_basis_ref
        or activation_receipt["snapshot_manifest_ref"] != expected_manifest_ref
        or activation_receipt["completion_scope"]
        != "snapshot_manifest_and_exact_store_basis_candidate_published"
        or store_activation_basis["snapshot_manifest_ref"] != expected_manifest_ref
        or store_activation_basis["snapshot_activation_authorization_ref"]
        != expected_authorization_ref
        or store_activation_basis["publisher_contract_binding"]
        != activation_receipt["publisher_contract_binding"]
        or activation_receipt["publisher_contract_binding"]
        != activation_consumption["publisher_contract_binding"]
        or activation_receipt["publication_occurred"] is not True
    ):
        raise BrokerBoundaryError(
            "u10_snapshot_activation_occurrence_binding_mismatch", entry_id
        )
    _require_time_order(
        ("immutability_verified_at", immutability["verified_at"]),
        ("environment_adoption_recorded_at", adoption["recorded_at"]),
        (
            "snapshot_adoption_authorized_at",
            snapshot_adoption_authorization["recorded_at"],
        ),
        ("snapshot_activation_reserved_at", activation_consumption["reserved_at"]),
        (
            "snapshot_activation_prepared_at",
            activation_consumption["activation_prepared_at"],
        ),
        (
            "snapshot_activation_basis_prepared_at",
            activation_basis["activation_prepared_at"],
        ),
        (
            "store_activation_basis_prepared_at",
            store_activation_basis["prepared_at"],
        ),
        (
            "snapshot_manifest_publication_observed_at",
            activation_receipt["publication_observed_at"],
        ),
        (
            "snapshot_activation_receipt_recorded_at",
            activation_receipt["receipt_recorded_at"],
        ),
    )
    _require_repository_refs_in_denominator(source, entries=entries)
    _require_repository_refs_in_denominator(profile, entries=entries)
    _require_repository_refs_in_denominator(environment, entries=entries)
    if set(entry["commands"]) != set(manifest["command_bindings"]):
        raise BrokerBoundaryError("u10_snapshot_command_denominator_mismatch", entry_id)
    for command_id, snapshot_command in manifest["command_bindings"].items():
        command = entry["commands"][command_id]
        profile_commands = [
            item for item in profile["commands"] if item["command_id"] == command_id
        ]
        if len(profile_commands) != 1:
            raise BrokerBoundaryError(
                "u10_snapshot_profile_command_missing", command_id
            )
        profile_command = profile_commands[0]
        observed_command_digest = digest_bytes(canonical_json_bytes(profile_command))
        if (
            command["command_definition_digest"]
            != snapshot_command["command_definition_digest"]
            or command["command_definition_digest"] != observed_command_digest
            or snapshot_command["governed_command_timeout_seconds"]
            != profile_command["timeout_seconds"]
        ):
            raise BrokerBoundaryError(
                "u10_snapshot_command_digest_mismatch", command_id
            )
        closed_ref = snapshot_command["closed_test_manifest_ref"]
        closed = _semantic_json_artifact(
            snapshot_path=snapshot_path,
            entries=entries,
            reference=closed_ref["snapshot_artifact_ref"],
            role="closed_test_manifest",
            semantic_field="manifest_digest",
            schema_name="closed-verification-test-manifest-v1.schema.json",
            code="u10_snapshot_closed_manifest_invalid",
        )
        if (
            closed["manifest_id"] != closed_ref["manifest_id"]
            or closed["manifest_version"] != closed_ref["manifest_version"]
            or closed["command_id"] != command_id
            or profile_command["closed_test_manifest_ref"]
            != {
                "record_id": closed_ref["manifest_id"],
                "locator": closed_ref["source_artifact_ref"]["locator"],
                "content_digest": closed_ref["source_artifact_ref"]["artifact_digest"],
            }
            or command["closed_test_manifest_binding"]
            != {
                "manifest_id": closed_ref["manifest_id"],
                "manifest_version": closed_ref["manifest_version"],
                "locator": closed_ref["source_artifact_ref"]["locator"],
                "artifact_digest": closed_ref["source_artifact_ref"]["artifact_digest"],
                "manifest_digest": closed_ref["manifest_digest"],
            }
            or command["snapshot_closed_test_manifest_ref"]
            != {
                "manifest_id": closed_ref["manifest_id"],
                "manifest_version": closed_ref["manifest_version"],
                "locator": closed_ref["snapshot_artifact_ref"]["locator"],
                "artifact_digest": closed_ref["snapshot_artifact_ref"][
                    "artifact_digest"
                ],
                "manifest_digest": closed_ref["manifest_digest"],
            }
            or set(snapshot_command["required_snapshot_artifact_ids"]) != set(entries)
        ):
            raise BrokerBoundaryError(
                "u10_snapshot_closed_command_mismatch", command_id
            )
        _require_repository_refs_in_denominator(closed, entries=entries)
    return dict(entry), manifest


def resolve_trusted_execution_context_v1(
    request: Mapping[str, Any],
    *,
    _require_v2_key_chain: bool = False,
) -> dict[str, Any]:
    """Resolve a caller-minimal request against only the fixed root trust root."""

    validate_execution_request_v1(request)
    store, store_raw = (
        load_active_root_trust_store_for_execution_v3()
        if _require_v2_key_chain
        else load_active_root_trust_store_for_execution_v2()
    )
    entry_id = str(request["entry_id"])
    entry, snapshot = load_active_snapshot_manifest_v1(store, entry_id)
    environment_adoption, environment_adoption_ref = (
        _load_execution_environment_adoption_v1(
            snapshot=snapshot,
            entry=entry,
            entry_id=entry_id,
        )
    )
    command_id = str(request["command_id"])
    command = entry["commands"].get(command_id)
    snapshot_command = snapshot["command_bindings"].get(command_id)
    if not isinstance(command, Mapping) or not isinstance(snapshot_command, Mapping):
        raise BrokerBoundaryError("u10_command_not_allowed", command_id)
    if (
        command["command_definition_digest"]
        != snapshot_command["command_definition_digest"]
    ):
        raise BrokerBoundaryError("u10_command_digest_mismatch", command_id)
    manifest_ref = snapshot_command["closed_test_manifest_ref"]["snapshot_artifact_ref"]
    if (
        command["snapshot_closed_test_manifest_ref"]["artifact_digest"]
        != manifest_ref["artifact_digest"]
    ):
        raise BrokerBoundaryError("u10_closed_manifest_artifact_mismatch", command_id)
    nonce_path, nonce_record = reserve_nonce_once(request)
    context = {
        "request": dict(request),
        "store": store,
        "store_artifact_digest": digest_bytes(store_raw),
        "store_history_ref": derive_historical_store_ref_v2(store, store_raw),
        "entry": entry,
        "snapshot": snapshot,
        "environment_adoption": environment_adoption,
        "environment_adoption_ref": environment_adoption_ref,
        "command": dict(command),
        "snapshot_command": dict(snapshot_command),
        "nonce_record_path": str(nonce_path),
        "nonce_record": nonce_record,
    }
    return context


def revalidate_trusted_execution_context_v1(
    context: Mapping[str, Any],
    *,
    _require_v2_key_chain: bool = False,
) -> dict[str, Any]:
    """Re-resolve every mutable root before signing an occurrence."""

    request = context["request"]
    store, store_raw = (
        load_active_root_trust_store_for_execution_v3()
        if _require_v2_key_chain
        else load_active_root_trust_store_for_execution_v2()
    )
    entry_id = str(request["entry_id"])
    entry, snapshot = load_active_snapshot_manifest_v1(store, entry_id)
    environment_adoption, environment_adoption_ref = (
        _load_execution_environment_adoption_v1(
            snapshot=snapshot,
            entry=entry,
            entry_id=entry_id,
        )
    )
    command_id = str(request["command_id"])
    command = entry["commands"].get(command_id)
    snapshot_command = snapshot["command_bindings"].get(command_id)
    if (
        store != context["store"]
        or digest_bytes(store_raw) != context["store_artifact_digest"]
        or derive_historical_store_ref_v2(store, store_raw)
        != context["store_history_ref"]
        or entry != context["entry"]
        or snapshot != context["snapshot"]
        or environment_adoption != context["environment_adoption"]
        or environment_adoption_ref != context["environment_adoption_ref"]
        or command != context["command"]
        or snapshot_command != context["snapshot_command"]
    ):
        raise BrokerBoundaryError(
            "u10_execution_context_changed_before_signing", entry_id
        )
    nonce_path = Path(str(context["nonce_record_path"]))
    nonce_raw = read_protected_file(nonce_path, protected_root=NONCE_LEDGER_ROOT)
    nonce_record = _load_json_bytes(nonce_raw, "u10_nonce_record_unreadable")
    if nonce_record != context["nonce_record"]:
        raise BrokerBoundaryError("u10_nonce_changed_before_signing", entry_id)
    return {
        **dict(context),
        "store": store,
        "store_artifact_digest": digest_bytes(store_raw),
        "store_history_ref": derive_historical_store_ref_v2(store, store_raw),
        "entry": entry,
        "snapshot": snapshot,
        "environment_adoption": environment_adoption,
        "environment_adoption_ref": environment_adoption_ref,
        "command": dict(command),
        "snapshot_command": dict(snapshot_command),
    }


def resolve_trusted_execution_context_v2(
    request: Mapping[str, Any],
) -> dict[str, Any]:
    """Resolve a v3 execution context only through a live v2 key chain."""

    return resolve_trusted_execution_context_v1(request, _require_v2_key_chain=True)


def revalidate_trusted_execution_context_v2(
    context: Mapping[str, Any],
) -> dict[str, Any]:
    """Recheck the store, adoption, snapshot and v2 key head before signing."""

    return revalidate_trusted_execution_context_v1(context, _require_v2_key_chain=True)


def _coerce_key_chain_paths_v2(
    value: KeyChainPaths | Mapping[str, Any],
) -> KeyChainPaths:
    if isinstance(value, KeyChainPaths):
        paths = value
    elif isinstance(value, Mapping):
        expected = {
            "generation_root",
            "key_root",
            "ledger_root",
            "lock_path",
            "revocation_root",
            "selector_history_root",
            "selector_path",
            "u10_root",
        }
        if set(value) != expected:
            raise BrokerBoundaryError(
                "u10_key_chain_paths_shape_invalid", repr(sorted(value))
            )
        paths = KeyChainPaths(
            **{name: Path(str(value[name])) for name in sorted(expected)}
        )
    else:
        raise BrokerBoundaryError(
            "u10_key_chain_paths_shape_invalid", type(value).__name__
        )
    expected_paths = KeyChainPaths(
        u10_root=paths.u10_root,
        ledger_root=paths.u10_root / "activations" / "key-transitions",
        key_root=paths.u10_root / "keys",
        generation_root=paths.u10_root / "keys" / "generations",
        revocation_root=paths.u10_root / "keys" / "revocations",
        selector_history_root=(paths.u10_root / "keys" / "selector-history" / "sha256"),
        selector_path=paths.u10_root / "keys" / "current.json",
        lock_path=paths.u10_root / "keys" / "key-transition.lock",
    )
    if paths != expected_paths:
        raise BrokerBoundaryError("u10_key_chain_paths_not_derived", repr(paths))
    for path in paths.__dict__.values():
        normalized = Path(os.path.normpath(str(path)))
        if not path.is_absolute() or normalized != path:
            raise BrokerBoundaryError("u10_key_chain_path_not_canonical", str(path))
    return paths


def _validate_key_chain_path_authority_v2(
    paths: KeyChainPaths, *, required_uid: int
) -> None:
    if required_uid < 0:
        raise BrokerBoundaryError(
            "u10_key_chain_required_uid_invalid", str(required_uid)
        )
    if required_uid == 0:
        if os.geteuid() != 0:
            raise BrokerBoundaryError(
                "u10_key_chain_replay_requires_root", str(os.geteuid())
            )
        if paths != KeyChainPaths():
            raise BrokerBoundaryError("u10_key_chain_paths_not_fixed", repr(paths))
        return
    if paths == KeyChainPaths() or paths.u10_root == U10_ROOT:
        raise BrokerBoundaryError(
            "u10_key_chain_synthetic_paths_required", str(paths.u10_root)
        )
    if os.geteuid() != required_uid:
        raise BrokerBoundaryError(
            "u10_key_chain_synthetic_uid_mismatch",
            f"effective={os.geteuid()}; required={required_uid}",
        )


@contextmanager
def _key_transition_shared_lock_under_trust_store_v2(
    paths: KeyChainPaths, *, required_uid: int
):
    """Take only the subordinate key lock; the caller already holds store lock."""

    validate_directory_chain(
        paths.u10_root,
        paths.lock_path.parent,
        required_uid=required_uid,
    )
    try:
        before = paths.lock_path.lstat()
    except OSError as exc:
        raise BrokerBoundaryError(
            "u10_key_transition_lock_missing", str(paths.lock_path)
        ) from exc
    try:
        assert_no_extended_acl(paths.lock_path)
    except (OSError, PermissionError) as exc:
        raise BrokerBoundaryError(
            "u10_key_transition_lock_acl_untrusted", str(paths.lock_path)
        ) from exc
    if (
        stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_uid != required_uid
        or (required_uid == 0 and before.st_gid != 0)
        or stat.S_IMODE(before.st_mode) != 0o600
        or before.st_nlink != 1
    ):
        raise BrokerBoundaryError(
            "u10_key_transition_lock_untrusted", str(paths.lock_path)
        )
    try:
        descriptor = os.open(
            paths.lock_path,
            os.O_RDWR | getattr(os, "O_NOFOLLOW", 0),
        )
    except OSError as exc:
        raise BrokerBoundaryError(
            "u10_key_transition_lock_open_failed", str(paths.lock_path)
        ) from exc
    try:
        opened = os.fstat(descriptor)
        if (
            opened.st_dev,
            opened.st_ino,
            opened.st_mode,
            opened.st_uid,
            opened.st_gid,
            opened.st_nlink,
        ) != (
            before.st_dev,
            before.st_ino,
            before.st_mode,
            before.st_uid,
            before.st_gid,
            before.st_nlink,
        ):
            raise BrokerBoundaryError(
                "u10_key_transition_lock_changed", str(paths.lock_path)
            )
        fcntl.flock(descriptor, fcntl.LOCK_SH)
        yield
    finally:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)


def _key_record_bytes_v2(value: Mapping[str, Any]) -> bytes:
    return canonical_json_bytes(value) + b"\n"


def _read_key_record_v2(
    path: Path,
    *,
    protected_root: Path,
    required_uid: int,
    exact_mode: int,
    code: str,
) -> tuple[dict[str, Any], bytes]:
    raw = read_protected_file(
        path,
        protected_root=protected_root,
        required_uid=required_uid,
        private=exact_mode in {0o400, 0o600},
        maximum_bytes=2 * 1024 * 1024,
    )
    observed = path.lstat()
    if (
        not stat.S_ISREG(observed.st_mode)
        or observed.st_uid != required_uid
        or (required_uid == 0 and observed.st_gid != 0)
        or stat.S_IMODE(observed.st_mode) != exact_mode
        or observed.st_nlink != 1
    ):
        raise BrokerBoundaryError(code, f"untrusted file state: {path}")
    try:
        value = strict_json_loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BrokerBoundaryError(code, str(path)) from exc
    if not isinstance(value, dict) or raw != _key_record_bytes_v2(value):
        raise BrokerBoundaryError(code, f"non-canonical raw bytes: {path}")
    return value, raw


def _schema_project_key_paths_v2(value: Any, *, paths: KeyChainPaths) -> Any:
    """Project only the synthetic root so the fixed schemas remain authoritative."""

    if paths == KeyChainPaths():
        return value
    source = str(paths.u10_root)
    target = str(U10_ROOT)
    if isinstance(value, str):
        if value == source:
            return target
        if value.startswith(source + os.sep):
            return target + value[len(source) :]
        return value
    if isinstance(value, list):
        return [_schema_project_key_paths_v2(item, paths=paths) for item in value]
    if isinstance(value, Mapping):
        return {
            str(key): _schema_project_key_paths_v2(item, paths=paths)
            for key, item in value.items()
        }
    return value


def _validate_key_record_schema_v2(
    value: Mapping[str, Any],
    *,
    paths: KeyChainPaths,
    schema_name: str,
    code: str,
) -> None:
    projected = _schema_project_key_paths_v2(value, paths=paths)
    if not isinstance(projected, Mapping):
        raise BrokerBoundaryError(code, "projected record is not a mapping")
    _validate(projected, schema_name, code)


def _key_timestamp_v2(value: Any, *, code: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise BrokerBoundaryError(code, repr(value))
    return _timestamp_v1(value, code=code)


def _key_digest_v2(value: Any, *, code: str) -> dict[str, str]:
    return _require_digest_value_v1(value, code=code)


def _legacy_key_record_authorization_id_v1(
    value: Mapping[str, Any],
    raw: bytes,
    *,
    kind: str,
    path: Path,
    paths: KeyChainPaths,
) -> str:
    """Validate a legacy record completely before excluding it from v2 replay.

    A v1 schema label is classification input, not proof that an arbitrary file
    is harmless history.  Legacy records remain read-only, but must still be
    kind-correct, sealed, canonically located, and internally identifiable.
    """

    schema_name = _KEY_LEGACY_SCHEMA_NAME_BY_KIND_V1.get(kind)
    seal_field = _KEY_LEGACY_SEAL_FIELD_BY_KIND_V1.get(kind)
    if schema_name is None or seal_field is None:
        raise BrokerBoundaryError("u10_key_legacy_kind_unknown", kind)
    code = f"u10_key_legacy_{kind}_invalid"
    _validate_key_record_schema_v2(
        value,
        paths=paths,
        schema_name=schema_name,
        code=code,
    )
    _sealed_digest(value, seal_field, f"u10_key_legacy_{kind}_seal_mismatch")
    if raw != _key_record_bytes_v2(value):
        raise BrokerBoundaryError(code, f"non-canonical raw bytes: {path}")

    if kind == "authorization":
        authorization_id = str(value["authorization_id"])
        key_id = str(value["key_id"])
        expected_path = paths.ledger_root / f"{authorization_id}.authorization.json"
        if (
            path != expected_path
            or str(value["key_entity_ref"]).rsplit("・", 1)[-1] != key_id
            or value["target_generation_path"] != str(paths.generation_root / key_id)
            or value["target_public_metadata_path"]
            != str(paths.generation_root / key_id / "public-metadata.json")
            or value["target_private_key_path"]
            != str(paths.generation_root / key_id / "private.ed25519")
        ):
            raise BrokerBoundaryError(code, str(path))
        recorded = _key_timestamp_v2(
            value["recorded_at"], code="u10_key_legacy_authorization_time_invalid"
        )
        not_before = _key_timestamp_v2(
            value["not_before"], code="u10_key_legacy_authorization_time_invalid"
        )
        expires = _key_timestamp_v2(
            value["expires_at"], code="u10_key_legacy_authorization_time_invalid"
        )
        if not recorded <= not_before <= expires:
            raise BrokerBoundaryError(
                "u10_key_legacy_authorization_time_invalid", authorization_id
            )
        return authorization_id

    if kind == "consumption":
        authorization_id = str(value["authorization_ref"]["authorization_id"])
        if (
            path != paths.ledger_root / f"{authorization_id}.consumption.json"
            or value["consumption_id"] != f"consumption.{authorization_id}"
            or value["occurrence_id"]
            != f"key.{value['authorization_ref']['authorization_digest']['value']}"
        ):
            raise BrokerBoundaryError(code, str(path))
        _validate_publisher_contract_binding_v1(
            value["publisher_contract_binding"], enforce_current=False
        )
        _key_timestamp_v2(
            value["reserved_at"], code="u10_key_legacy_consumption_time_invalid"
        )
        return authorization_id

    if kind == "receipt":
        authorization_id = str(value["authorization_ref"]["authorization_id"])
        if (
            path != paths.ledger_root / f"{authorization_id}.receipt.json"
            or value["receipt_id"] != f"receipt.{authorization_id}"
            or value["consumption_ref"]["consumption_id"]
            != f"consumption.{authorization_id}"
            or value["occurrence_id"]
            != f"key.{value['authorization_ref']['authorization_digest']['value']}"
        ):
            raise BrokerBoundaryError(code, str(path))
        _validate_publisher_contract_binding_v1(
            value["publisher_contract_binding"], enforce_current=False
        )
        publication_not_before = _key_timestamp_v2(
            value["publication_not_before"],
            code="u10_key_legacy_receipt_time_invalid",
        )
        observed_at = _key_timestamp_v2(
            value["publication_observed_at"],
            code="u10_key_legacy_receipt_time_invalid",
        )
        recorded_at = _key_timestamp_v2(
            value["receipt_recorded_at"],
            code="u10_key_legacy_receipt_time_invalid",
        )
        if not publication_not_before <= observed_at <= recorded_at:
            raise BrokerBoundaryError(
                "u10_key_legacy_receipt_time_invalid", authorization_id
            )
        return authorization_id

    if kind == "selector":
        authorization_id = str(
            value["transition_authorization_ref"]["authorization_id"]
        )
        expected_path = paths.selector_history_root / (
            f"{digest_bytes(raw)['value']}.json"
        )
        if (
            path != expected_path
            or value["selector_id"] != f"selector.{authorization_id}"
        ):
            raise BrokerBoundaryError(code, str(path))
        if value["state"] == "active":
            key_id = str(value["key_id"])
            metadata_ref = value["public_metadata_ref"]
            receipt_selector = metadata_ref["generation_receipt_selector"]
            if (
                str(value["key_entity_ref"]).rsplit("・", 1)[-1] != key_id
                or metadata_ref["key_id"] != key_id
                or metadata_ref["key_entity_ref"] != value["key_entity_ref"]
                or metadata_ref["metadata_locator"]
                != str(paths.generation_root / key_id / "public-metadata.json")
                or metadata_ref["generation_authorization_ref"]
                != value["transition_authorization_ref"]
                or receipt_selector["ledger_root"] != str(paths.ledger_root)
                or receipt_selector["receipt_record"]
                != f"{authorization_id}.receipt.json"
            ):
                raise BrokerBoundaryError(code, authorization_id)
        _key_timestamp_v2(
            value["selected_at"], code="u10_key_legacy_selector_time_invalid"
        )
        return authorization_id

    if kind == "metadata":
        authorization_id = str(value["authorization_ref"]["authorization_id"])
        key_id = str(value["key_id"])
        evidence = value["generation_evidence_selector"]
        if (
            path != paths.generation_root / key_id / "public-metadata.json"
            or str(value["key_entity_ref"]).rsplit("・", 1)[-1] != key_id
            or value["private_material"]
            != {
                "locator": str(paths.generation_root / key_id / "private.ed25519"),
                "storage_state": "root_only_0600_not_exported",
            }
            or evidence["ledger_root"] != str(paths.ledger_root)
            or evidence["authorization_record"]
            != f"{authorization_id}.authorization.json"
            or evidence["consumption_record"] != f"{authorization_id}.consumption.json"
            or evidence["receipt_record"] != f"{authorization_id}.receipt.json"
        ):
            raise BrokerBoundaryError(code, str(path))
        try:
            public_raw = base64.b64decode(value["public_key"]["value"], validate=True)
        except (TypeError, ValueError) as exc:
            raise BrokerBoundaryError(code, str(path)) from exc
        if len(public_raw) != 32:
            raise BrokerBoundaryError(code, str(path))
        _key_timestamp_v2(
            value["created_at"], code="u10_key_legacy_metadata_time_invalid"
        )
        return authorization_id

    authorization_id = str(value["authorization_ref"]["authorization_id"])
    key_id = str(value["key_id"])
    if (
        path != paths.revocation_root / key_id / f"{authorization_id}.json"
        or value["revocation_id"] != f"revocation.{authorization_id}"
        or str(value["key_entity_ref"]).rsplit("・", 1)[-1] != key_id
    ):
        raise BrokerBoundaryError(code, str(path))
    _key_timestamp_v2(
        value["revoked_at"], code="u10_key_legacy_revocation_time_invalid"
    )
    return authorization_id


def _validate_key_selector_ref_v2(
    value: Any, *, paths: KeyChainPaths, code: str
) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != {
        "artifact_digest",
        "locator",
        "selector_digest",
        "selector_id",
    }:
        raise BrokerBoundaryError(code, repr(value))
    artifact_digest = _key_digest_v2(value["artifact_digest"], code=code)
    _key_digest_v2(value["selector_digest"], code=code)
    expected = paths.selector_history_root / (f"{artifact_digest['value']}.json")
    if value["locator"] != str(expected):
        raise BrokerBoundaryError(code, str(value["locator"]))
    return dict(value)


def _validate_key_authorization_ref_v2(
    value: Any, *, paths: KeyChainPaths, code: str
) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != {
        "artifact_digest",
        "authorization_digest",
        "authorization_id",
        "locator",
    }:
        raise BrokerBoundaryError(code, repr(value))
    authorization_id = str(value["authorization_id"])
    if value["locator"] != str(
        paths.ledger_root / f"{authorization_id}.authorization.json"
    ):
        raise BrokerBoundaryError(code, str(value["locator"]))
    _key_digest_v2(value["artifact_digest"], code=code)
    _key_digest_v2(value["authorization_digest"], code=code)
    return dict(value)


def _validate_key_consumption_ref_v2(
    value: Any, *, paths: KeyChainPaths, code: str
) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != {
        "artifact_digest",
        "consumption_digest",
        "consumption_id",
        "locator",
    }:
        raise BrokerBoundaryError(code, repr(value))
    consumption_id = str(value["consumption_id"])
    if not consumption_id.startswith("consumption."):
        raise BrokerBoundaryError(code, consumption_id)
    authorization_id = consumption_id.removeprefix("consumption.")
    if value["locator"] != str(
        paths.ledger_root / f"{authorization_id}.consumption.json"
    ):
        raise BrokerBoundaryError(code, str(value["locator"]))
    _key_digest_v2(value["artifact_digest"], code=code)
    _key_digest_v2(value["consumption_digest"], code=code)
    return dict(value)


def _validate_key_evidence_selector_v2(
    value: Any, *, paths: KeyChainPaths, code: str
) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != {
        "authorization_ref",
        "consumption_ref",
        "ledger_root",
        "prior_selector_ref",
        "receipt_locator",
        "resolution_policy",
    }:
        raise BrokerBoundaryError(code, repr(value))
    authorization_ref = _validate_key_authorization_ref_v2(
        value["authorization_ref"], paths=paths, code=code
    )
    consumption_ref = _validate_key_consumption_ref_v2(
        value["consumption_ref"], paths=paths, code=code
    )
    prior_ref = value["prior_selector_ref"]
    if prior_ref is not None:
        _validate_key_selector_ref_v2(prior_ref, paths=paths, code=code)
    authorization_id = authorization_ref["authorization_id"]
    if (
        value["ledger_root"] != str(paths.ledger_root)
        or consumption_ref["consumption_id"] != f"consumption.{authorization_id}"
        or value["receipt_locator"]
        != str(paths.ledger_root / f"{authorization_id}.receipt.json")
        or value["resolution_policy"] != "resolve_exact_key_transition_chain/v2"
    ):
        raise BrokerBoundaryError(code, str(authorization_id))
    return dict(value)


def _key_selector_ref_v2(
    selector: Mapping[str, Any], raw: bytes, *, paths: KeyChainPaths
) -> dict[str, Any]:
    artifact_digest = digest_bytes(raw)
    return {
        "selector_id": selector["selector_id"],
        "locator": str(
            paths.selector_history_root / f"{artifact_digest['value']}.json"
        ),
        "artifact_digest": artifact_digest,
        "selector_digest": selector["selector_digest"],
    }


def _key_authorization_ref_v2(
    authorization: Mapping[str, Any],
    raw: bytes,
    *,
    paths: KeyChainPaths,
) -> dict[str, Any]:
    authorization_id = str(authorization["authorization_id"])
    return {
        "authorization_id": authorization_id,
        "locator": str(paths.ledger_root / f"{authorization_id}.authorization.json"),
        "artifact_digest": digest_bytes(raw),
        "authorization_digest": authorization["authorization_digest"],
    }


def _key_consumption_ref_v2(
    consumption: Mapping[str, Any],
    raw: bytes,
    *,
    paths: KeyChainPaths,
) -> dict[str, Any]:
    authorization_id = str(consumption["authorization_ref"]["authorization_id"])
    return {
        "consumption_id": consumption["consumption_id"],
        "locator": str(paths.ledger_root / f"{authorization_id}.consumption.json"),
        "artifact_digest": digest_bytes(raw),
        "consumption_digest": consumption["consumption_digest"],
    }


def _validate_key_authorization_v2(
    value: Mapping[str, Any],
    *,
    paths: KeyChainPaths,
    effective_at: datetime,
) -> dict[str, Any]:
    _validate_key_record_schema_v2(
        value,
        paths=paths,
        schema_name=_KEY_AUTHORIZATION_SCHEMA_V2,
        code="u10_key_authorization_v2_invalid",
    )
    _sealed_digest(
        value,
        "authorization_digest",
        "u10_key_authorization_seal_mismatch",
    )
    key_id = str(value["key_id"])
    entity_ref = str(value["key_entity_ref"])
    prior_ref = value["prior_selector_ref"]
    if prior_ref is not None:
        _validate_key_selector_ref_v2(
            prior_ref,
            paths=paths,
            code="u10_key_authorization_prior_selector_invalid",
        )
    operation = str(value["key_operation"])
    mode = str(value["transition_mode"])
    expected_modes = {
        "generate": (
            "initialize_empty_store"
            if prior_ref is None
            else "generate_from_no_active_key"
        ),
        "rotate": "rotate_active_key",
        "revoke": "revoke_active_key",
    }
    expected_current = value["expected_current_key_id"]
    if (
        entity_ref.rsplit("・", 1)[-1] != key_id
        or value["target_generation_path"] != str(paths.generation_root / key_id)
        or value["target_public_metadata_path"]
        != str(paths.generation_root / key_id / "public-metadata.json")
        or value["target_private_key_path"]
        != str(paths.generation_root / key_id / "private.ed25519")
        or mode != expected_modes[operation]
        or (operation == "generate" and expected_current is not None)
        or (operation in {"rotate", "revoke"} and not isinstance(expected_current, str))
        or (operation == "rotate" and expected_current == key_id)
        or (operation == "revoke" and expected_current != key_id)
    ):
        raise BrokerBoundaryError(
            "u10_key_authorization_context_mismatch",
            str(value["authorization_id"]),
        )
    recorded_at = _key_timestamp_v2(
        value["recorded_at"], code="u10_key_authorization_time_invalid"
    )
    not_before = _key_timestamp_v2(
        value["not_before"], code="u10_key_authorization_time_invalid"
    )
    expires_at = _key_timestamp_v2(
        value["expires_at"], code="u10_key_authorization_time_invalid"
    )
    if not (recorded_at <= not_before <= effective_at <= expires_at):
        raise BrokerBoundaryError(
            "u10_key_authorization_time_invalid", str(effective_at)
        )
    return dict(value)


def _validate_key_consumption_v2(
    value: Mapping[str, Any],
    *,
    raw: bytes,
    authorization: Mapping[str, Any],
    authorization_raw: bytes,
    paths: KeyChainPaths,
) -> dict[str, Any]:
    _validate_key_record_schema_v2(
        value,
        paths=paths,
        schema_name=_KEY_CONSUMPTION_SCHEMA_V2,
        code="u10_key_consumption_v2_invalid",
    )
    _sealed_digest(
        value,
        "consumption_digest",
        "u10_key_consumption_seal_mismatch",
    )
    authorization_ref = _key_authorization_ref_v2(
        authorization, authorization_raw, paths=paths
    )
    _validate_key_authorization_ref_v2(
        value["authorization_ref"],
        paths=paths,
        code="u10_key_consumption_authorization_ref_invalid",
    )
    prior_ref = value["prior_selector_ref"]
    if prior_ref is not None:
        _validate_key_selector_ref_v2(
            prior_ref,
            paths=paths,
            code="u10_key_consumption_prior_selector_invalid",
        )
    _validate_publisher_contract_binding_v1(
        value["publisher_contract_binding"], enforce_current=False
    )
    authorization_id = str(authorization["authorization_id"])
    if (
        value["authorization_ref"] != authorization_ref
        or value["consumption_id"] != f"consumption.{authorization_id}"
        or value["prior_selector_ref"] != authorization["prior_selector_ref"]
        or value["key_operation"] != authorization["key_operation"]
        or value["transition_mode"] != authorization["transition_mode"]
        or value["key_id"] != authorization["key_id"]
        or value["occurrence_id"]
        != f"key.{authorization['authorization_digest']['value']}"
        or raw != _key_record_bytes_v2(value)
    ):
        raise BrokerBoundaryError(
            "u10_key_consumption_context_mismatch", authorization_id
        )
    return dict(value)


def _validate_key_public_metadata_ref_v2(
    value: Any, *, paths: KeyChainPaths, code: str
) -> dict[str, Any]:
    expected_keys = {
        "artifact_digest",
        "generation_authorization_ref",
        "generation_consumption_ref",
        "key_entity_ref",
        "key_id",
        "locator",
        "metadata_digest",
    }
    if not isinstance(value, Mapping) or set(value) != expected_keys:
        raise BrokerBoundaryError(code, repr(value))
    key_id = str(value["key_id"])
    if str(value["key_entity_ref"]).rsplit("・", 1)[-1] != key_id or value[
        "locator"
    ] != str(paths.generation_root / key_id / "public-metadata.json"):
        raise BrokerBoundaryError(code, key_id)
    _key_digest_v2(value["artifact_digest"], code=code)
    _key_digest_v2(value["metadata_digest"], code=code)
    _validate_key_authorization_ref_v2(
        value["generation_authorization_ref"], paths=paths, code=code
    )
    _validate_key_consumption_ref_v2(
        value["generation_consumption_ref"], paths=paths, code=code
    )
    return dict(value)


def _key_public_metadata_ref_v2(
    metadata: Mapping[str, Any], raw: bytes, *, paths: KeyChainPaths
) -> dict[str, Any]:
    return {
        "key_id": metadata["key_id"],
        "key_entity_ref": metadata["key_entity_ref"],
        "locator": str(
            paths.generation_root / str(metadata["key_id"]) / "public-metadata.json"
        ),
        "artifact_digest": digest_bytes(raw),
        "metadata_digest": metadata["metadata_digest"],
        "generation_authorization_ref": metadata["authorization_ref"],
        "generation_consumption_ref": metadata["consumption_ref"],
    }


def _read_private_key_for_chain_v2(
    metadata: Mapping[str, Any],
    *,
    paths: KeyChainPaths,
    required_uid: int,
) -> dict[str, Any]:
    key_id = str(metadata["key_id"])
    path = paths.generation_root / key_id / "private.ed25519"
    if metadata["private_material"] != {
        "locator": str(path),
        "storage_state": "root_only_0600_not_exported",
    }:
        raise BrokerBoundaryError("u10_key_private_material_ref_mismatch", key_id)
    raw = read_protected_file(
        path,
        protected_root=paths.key_root,
        required_uid=required_uid,
        private=True,
        maximum_bytes=33,
    )
    observed = path.lstat()
    if (
        not stat.S_ISREG(observed.st_mode)
        or observed.st_uid != required_uid
        or (required_uid == 0 and observed.st_gid != 0)
        or stat.S_IMODE(observed.st_mode) != 0o600
        or observed.st_nlink != 1
        or len(raw) != 32
    ):
        raise BrokerBoundaryError("u10_key_private_material_invalid", str(path))
    try:
        private = Ed25519PrivateKey.from_private_bytes(raw)
        public_raw = private.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
    except ValueError as exc:
        raise BrokerBoundaryError(
            "u10_key_private_material_invalid", str(path)
        ) from exc
    if base64.b64encode(public_raw).decode("ascii") != metadata["public_key"]["value"]:
        raise BrokerBoundaryError("u10_key_private_public_mismatch", key_id)
    return dict(metadata["private_material"])


def _validate_key_metadata_v2(
    value: Mapping[str, Any],
    *,
    raw: bytes,
    selector: Mapping[str, Any],
    authorization_ref: Mapping[str, Any],
    consumption_ref: Mapping[str, Any],
    paths: KeyChainPaths,
    required_uid: int,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    _validate_key_record_schema_v2(
        value,
        paths=paths,
        schema_name=_KEY_METADATA_SCHEMA_V2,
        code="u10_key_metadata_v2_invalid",
    )
    _sealed_digest(value, "metadata_digest", "u10_key_metadata_seal_mismatch")
    evidence = _validate_key_evidence_selector_v2(
        value["transition_evidence_selector"],
        paths=paths,
        code="u10_key_metadata_evidence_invalid",
    )
    key_id = str(value["key_id"])
    try:
        public_raw = base64.b64decode(value["public_key"]["value"], validate=True)
    except (TypeError, ValueError) as exc:
        raise BrokerBoundaryError("u10_key_public_material_invalid", key_id) from exc
    if (
        len(public_raw) != 32
        or str(value["key_entity_ref"]).rsplit("・", 1)[-1] != key_id
        or value["authorization_ref"] != authorization_ref
        or value["consumption_ref"] != consumption_ref
        or value["prior_selector_ref"] != selector["previous_selector_ref"]
        or evidence != selector["transition_evidence_selector"]
    ):
        raise BrokerBoundaryError("u10_key_metadata_context_mismatch", key_id)
    metadata_ref = _key_public_metadata_ref_v2(value, raw, paths=paths)
    if selector["public_metadata_ref"] != metadata_ref:
        raise BrokerBoundaryError("u10_key_metadata_ref_mismatch", key_id)
    private_ref = _read_private_key_for_chain_v2(
        value, paths=paths, required_uid=required_uid
    )
    _key_timestamp_v2(value["created_at"], code="u10_key_metadata_time_invalid")
    return dict(value), metadata_ref, private_ref


def _validate_key_revocation_ref_v2(
    value: Any, *, paths: KeyChainPaths, code: str
) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != {
        "artifact_digest",
        "key_id",
        "locator",
        "revocation_digest",
        "revocation_id",
    }:
        raise BrokerBoundaryError(code, repr(value))
    revocation_id = str(value["revocation_id"])
    if not revocation_id.startswith("revocation."):
        raise BrokerBoundaryError(code, revocation_id)
    authorization_id = revocation_id.removeprefix("revocation.")
    key_id = str(value["key_id"])
    if value["locator"] != str(
        paths.revocation_root / key_id / f"{authorization_id}.json"
    ):
        raise BrokerBoundaryError(code, str(value["locator"]))
    _key_digest_v2(value["artifact_digest"], code=code)
    _key_digest_v2(value["revocation_digest"], code=code)
    return dict(value)


def _key_revocation_ref_v2(
    revocation: Mapping[str, Any], raw: bytes, *, paths: KeyChainPaths
) -> dict[str, Any]:
    authorization_id = str(revocation["authorization_ref"]["authorization_id"])
    key_id = str(revocation["key_id"])
    return {
        "revocation_id": revocation["revocation_id"],
        "key_id": key_id,
        "locator": str(paths.revocation_root / key_id / f"{authorization_id}.json"),
        "artifact_digest": digest_bytes(raw),
        "revocation_digest": revocation["revocation_digest"],
    }


def _validate_key_revocation_v2(
    value: Mapping[str, Any],
    *,
    raw: bytes,
    selector: Mapping[str, Any],
    authorization_ref: Mapping[str, Any],
    consumption_ref: Mapping[str, Any],
    paths: KeyChainPaths,
) -> tuple[dict[str, Any], dict[str, Any]]:
    _validate_key_record_schema_v2(
        value,
        paths=paths,
        schema_name=_KEY_REVOCATION_SCHEMA_V2,
        code="u10_key_revocation_v2_invalid",
    )
    _sealed_digest(value, "revocation_digest", "u10_key_revocation_seal_mismatch")
    evidence = _validate_key_evidence_selector_v2(
        value["transition_evidence_selector"],
        paths=paths,
        code="u10_key_revocation_evidence_invalid",
    )
    authorization_id = str(authorization_ref["authorization_id"])
    if (
        value["revocation_id"] != f"revocation.{authorization_id}"
        or value["authorization_ref"] != authorization_ref
        or value["consumption_ref"] != consumption_ref
        or value["prior_selector_ref"] != selector["previous_selector_ref"]
        or evidence != selector["transition_evidence_selector"]
    ):
        raise BrokerBoundaryError(
            "u10_key_revocation_context_mismatch", authorization_id
        )
    revocation_ref = _key_revocation_ref_v2(value, raw, paths=paths)
    if selector["revocation_ref"] != revocation_ref:
        raise BrokerBoundaryError("u10_key_revocation_ref_mismatch", authorization_id)
    _key_timestamp_v2(value["revoked_at"], code="u10_key_revocation_time_invalid")
    return dict(value), revocation_ref


def _validate_key_selector_v2(
    value: Mapping[str, Any], *, paths: KeyChainPaths
) -> dict[str, Any]:
    if value.get("schema_version") != _KEY_RECORD_SCHEMA_IDS_V2["selector"]:
        raise BrokerBoundaryError(
            "u10_key_legacy_selector_requires_explicit_migration",
            str(value.get("schema_version")),
        )
    _validate_key_record_schema_v2(
        value,
        paths=paths,
        schema_name=_KEY_SELECTOR_SCHEMA_V2,
        code="u10_key_selector_v2_invalid",
    )
    _sealed_digest(value, "selector_digest", "u10_key_selector_seal_mismatch")
    evidence = _validate_key_evidence_selector_v2(
        value["transition_evidence_selector"],
        paths=paths,
        code="u10_key_selector_evidence_invalid",
    )
    previous_ref = value["previous_selector_ref"]
    if previous_ref is not None:
        _validate_key_selector_ref_v2(
            previous_ref,
            paths=paths,
            code="u10_key_selector_previous_ref_invalid",
        )
    authorization_id = str(evidence["authorization_ref"]["authorization_id"])
    mode = str(value["transition_mode"])
    if (
        value["selector_id"] != f"selector.{authorization_id}"
        or evidence["prior_selector_ref"] != previous_ref
        or (mode == "initialize_empty_store" and previous_ref is not None)
        or (mode != "initialize_empty_store" and previous_ref is None)
    ):
        raise BrokerBoundaryError("u10_key_selector_context_mismatch", authorization_id)
    if value["state"] == "active":
        public_ref = _validate_key_public_metadata_ref_v2(
            value["public_metadata_ref"],
            paths=paths,
            code="u10_key_selector_public_metadata_ref_invalid",
        )
        if (
            value["key_id"] != public_ref["key_id"]
            or value["key_entity_ref"] != public_ref["key_entity_ref"]
            or value["revocation_ref"] is not None
            or mode == "revoke_active_key"
        ):
            raise BrokerBoundaryError(
                "u10_key_selector_state_mismatch", authorization_id
            )
    else:
        revocation_ref = _validate_key_revocation_ref_v2(
            value["revocation_ref"],
            paths=paths,
            code="u10_key_selector_revocation_ref_invalid",
        )
        if (
            any(
                value[field] is not None
                for field in ("key_id", "key_entity_ref", "public_metadata_ref")
            )
            or mode != "revoke_active_key"
            or revocation_ref["revocation_id"] != f"revocation.{authorization_id}"
        ):
            raise BrokerBoundaryError(
                "u10_key_selector_state_mismatch", authorization_id
            )
    _key_timestamp_v2(value["selected_at"], code="u10_key_selector_time_invalid")
    return dict(value)


def _read_key_selector_ref_v2(
    reference: Mapping[str, Any],
    *,
    paths: KeyChainPaths,
    required_uid: int,
) -> tuple[dict[str, Any], bytes, dict[str, Any]]:
    expected_ref = _validate_key_selector_ref_v2(
        reference, paths=paths, code="u10_key_selector_ref_invalid"
    )
    value, raw = _read_key_record_v2(
        Path(str(expected_ref["locator"])),
        protected_root=paths.key_root,
        required_uid=required_uid,
        exact_mode=0o444,
        code="u10_key_selector_history_unreadable",
    )
    selector = _validate_key_selector_v2(value, paths=paths)
    observed_ref = _key_selector_ref_v2(selector, raw, paths=paths)
    if observed_ref != expected_ref:
        raise BrokerBoundaryError(
            "u10_key_selector_history_ref_mismatch",
            str(expected_ref["locator"]),
        )
    return selector, raw, observed_ref


def _load_current_key_selector_v2(
    paths: KeyChainPaths, *, required_uid: int
) -> tuple[dict[str, Any], bytes, dict[str, Any]] | None:
    if not paths.selector_path.exists() and not paths.selector_path.is_symlink():
        return None
    value, raw = _read_key_record_v2(
        paths.selector_path,
        protected_root=paths.key_root,
        required_uid=required_uid,
        exact_mode=0o444,
        code="u10_key_current_selector_unreadable",
    )
    selector = _validate_key_selector_v2(value, paths=paths)
    reference = _key_selector_ref_v2(selector, raw, paths=paths)
    _history, history_raw, history_ref = _read_key_selector_ref_v2(
        reference, paths=paths, required_uid=required_uid
    )
    if history_raw != raw or history_ref != reference:
        raise BrokerBoundaryError(
            "u10_key_current_selector_history_mismatch",
            str(paths.selector_path),
        )
    return selector, raw, reference


def _scan_key_selector_history_v2(
    paths: KeyChainPaths, *, required_uid: int
) -> tuple[
    dict[str, tuple[dict[str, Any], bytes, dict[str, Any]]],
    dict[str, tuple[dict[str, Any], bytes, Path]],
]:
    validate_directory_chain(
        paths.u10_root,
        paths.selector_history_root,
        required_uid=required_uid,
    )
    result: dict[str, tuple[dict[str, Any], bytes, dict[str, Any]]] = {}
    legacy: dict[str, tuple[dict[str, Any], bytes, Path]] = {}
    for path in sorted(paths.selector_history_root.iterdir()):
        if path.name.startswith(".") or path.suffix != ".json":
            raise BrokerBoundaryError(
                "u10_key_selector_history_entry_unexpected", str(path)
            )
        value, raw = _read_key_record_v2(
            path,
            protected_root=paths.key_root,
            required_uid=required_uid,
            exact_mode=0o444,
            code="u10_key_selector_history_unreadable",
        )
        schema_version = value.get("schema_version")
        if schema_version == _KEY_LEGACY_SCHEMA_ID_BY_KIND_V1["selector"]:
            authorization_id = _legacy_key_record_authorization_id_v1(
                value,
                raw,
                kind="selector",
                path=path,
                paths=paths,
            )
            if authorization_id in legacy:
                raise BrokerBoundaryError(
                    "u10_key_legacy_selector_duplicate", authorization_id
                )
            legacy[authorization_id] = (value, raw, path)
            continue
        if schema_version != _KEY_RECORD_SCHEMA_IDS_V2["selector"]:
            raise BrokerBoundaryError(
                "u10_key_selector_history_schema_unknown",
                str(schema_version),
            )
        selector = _validate_key_selector_v2(value, paths=paths)
        reference = _key_selector_ref_v2(selector, raw, paths=paths)
        if Path(reference["locator"]) != path:
            raise BrokerBoundaryError(
                "u10_key_selector_history_filename_mismatch", str(path)
            )
        digest = str(reference["artifact_digest"]["value"])
        if digest in result:
            raise BrokerBoundaryError("u10_key_selector_history_duplicate", digest)
        result[digest] = (selector, raw, reference)
    return result, legacy


def _validate_key_receipt_v2(
    value: Mapping[str, Any],
    *,
    raw: bytes,
    selector: Mapping[str, Any],
    selector_ref: Mapping[str, Any],
    authorization: Mapping[str, Any],
    authorization_ref: Mapping[str, Any],
    consumption: Mapping[str, Any],
    consumption_ref: Mapping[str, Any],
    paths: KeyChainPaths,
) -> dict[str, Any]:
    _validate_key_record_schema_v2(
        value,
        paths=paths,
        schema_name=_KEY_RECEIPT_SCHEMA_V2,
        code="u10_key_receipt_v2_invalid",
    )
    _sealed_digest(value, "receipt_digest", "u10_key_receipt_seal_mismatch")
    _validate_key_authorization_ref_v2(
        value["authorization_ref"],
        paths=paths,
        code="u10_key_receipt_authorization_ref_invalid",
    )
    _validate_key_consumption_ref_v2(
        value["consumption_ref"],
        paths=paths,
        code="u10_key_receipt_consumption_ref_invalid",
    )
    _validate_key_selector_ref_v2(
        value["published_selector_ref"],
        paths=paths,
        code="u10_key_receipt_selector_ref_invalid",
    )
    _validate_publisher_contract_binding_v1(
        value["publisher_contract_binding"], enforce_current=False
    )
    authorization_id = str(authorization["authorization_id"])
    if (
        value["receipt_id"] != f"receipt.{authorization_id}"
        or value["occurrence_id"] != consumption["occurrence_id"]
        or value["authorization_ref"] != authorization_ref
        or value["consumption_ref"] != consumption_ref
        or value["prior_selector_ref"] != selector["previous_selector_ref"]
        or value["published_selector_ref"] != selector_ref
        or value["key_operation"] != authorization["key_operation"]
        or value["transition_mode"] != selector["transition_mode"]
        or value["key_id"] != authorization["key_id"]
        or value["publisher_contract_binding"]
        != consumption["publisher_contract_binding"]
        or value["publication_not_before"] != consumption["reserved_at"]
        or value["publication_observed_at"] != selector["selected_at"]
        or value["public_metadata_ref"] != selector["public_metadata_ref"]
        or value["revocation_ref"] != selector["revocation_ref"]
        or raw != _key_record_bytes_v2(value)
    ):
        raise BrokerBoundaryError("u10_key_receipt_chain_mismatch", authorization_id)
    not_before = _key_timestamp_v2(
        value["publication_not_before"],
        code="u10_key_receipt_time_invalid",
    )
    observed_at = _key_timestamp_v2(
        value["publication_observed_at"],
        code="u10_key_receipt_time_invalid",
    )
    recorded_at = _key_timestamp_v2(
        value["receipt_recorded_at"], code="u10_key_receipt_time_invalid"
    )
    if not (not_before <= observed_at <= recorded_at):
        raise BrokerBoundaryError("u10_key_receipt_time_invalid", authorization_id)
    if selector["state"] == "active":
        if (
            value["private_material_evidence"]
            != "root_owned_0600_present_not_disclosed"
            or value["key_state"] != "active"
        ):
            raise BrokerBoundaryError(
                "u10_key_receipt_state_mismatch", authorization_id
            )
    elif (
        value["private_material_evidence"] != "unchanged_not_disclosed"
        or value["key_state"] != "revoked_no_active_key"
    ):
        raise BrokerBoundaryError("u10_key_receipt_state_mismatch", authorization_id)
    return dict(value)


def _read_key_transition_v2(
    selector: Mapping[str, Any],
    selector_ref: Mapping[str, Any],
    *,
    paths: KeyChainPaths,
    required_uid: int,
) -> dict[str, Any]:
    evidence = selector["transition_evidence_selector"]
    authorization_ref = evidence["authorization_ref"]
    consumption_ref = evidence["consumption_ref"]
    authorization, authorization_raw = _read_key_record_v2(
        Path(str(authorization_ref["locator"])),
        protected_root=paths.ledger_root,
        required_uid=required_uid,
        exact_mode=0o400,
        code="u10_key_authorization_archive_unreadable",
    )
    consumption, consumption_raw = _read_key_record_v2(
        Path(str(consumption_ref["locator"])),
        protected_root=paths.ledger_root,
        required_uid=required_uid,
        exact_mode=0o400,
        code="u10_key_consumption_unreadable",
    )
    if (
        authorization.get("schema_version")
        != _KEY_RECORD_SCHEMA_IDS_V2["authorization"]
    ):
        raise BrokerBoundaryError(
            "u10_key_legacy_authorization_read_only",
            str(authorization.get("schema_version")),
        )
    if consumption.get("schema_version") != _KEY_RECORD_SCHEMA_IDS_V2["consumption"]:
        raise BrokerBoundaryError(
            "u10_key_legacy_consumption_read_only",
            str(consumption.get("schema_version")),
        )
    reserved_at = _key_timestamp_v2(
        consumption.get("reserved_at"), code="u10_key_consumption_time_invalid"
    )
    authorization = _validate_key_authorization_v2(
        authorization, paths=paths, effective_at=reserved_at
    )
    consumption = _validate_key_consumption_v2(
        consumption,
        raw=consumption_raw,
        authorization=authorization,
        authorization_raw=authorization_raw,
        paths=paths,
    )
    observed_authorization_ref = _key_authorization_ref_v2(
        authorization, authorization_raw, paths=paths
    )
    observed_consumption_ref = _key_consumption_ref_v2(
        consumption, consumption_raw, paths=paths
    )
    if (
        authorization_ref != observed_authorization_ref
        or consumption_ref != observed_consumption_ref
        or selector["previous_selector_ref"] != authorization["prior_selector_ref"]
        or evidence["prior_selector_ref"] != authorization["prior_selector_ref"]
        or selector["transition_mode"] != authorization["transition_mode"]
    ):
        raise BrokerBoundaryError(
            "u10_key_transition_chain_mismatch",
            str(authorization["authorization_id"]),
        )
    metadata: dict[str, Any] | None = None
    metadata_ref: dict[str, Any] | None = None
    private_ref: dict[str, Any] | None = None
    revocation: dict[str, Any] | None = None
    revocation_ref: dict[str, Any] | None = None
    if selector["state"] == "active":
        metadata_ref = _validate_key_public_metadata_ref_v2(
            selector["public_metadata_ref"],
            paths=paths,
            code="u10_key_metadata_ref_invalid",
        )
        metadata_value, metadata_raw = _read_key_record_v2(
            Path(str(metadata_ref["locator"])),
            protected_root=paths.key_root,
            required_uid=required_uid,
            exact_mode=0o444,
            code="u10_key_metadata_unreadable",
        )
        metadata, observed_metadata_ref, private_ref = _validate_key_metadata_v2(
            metadata_value,
            raw=metadata_raw,
            selector=selector,
            authorization_ref=observed_authorization_ref,
            consumption_ref=observed_consumption_ref,
            paths=paths,
            required_uid=required_uid,
        )
        if observed_metadata_ref != metadata_ref:
            raise BrokerBoundaryError(
                "u10_key_metadata_ref_mismatch",
                str(authorization["authorization_id"]),
            )
    else:
        revocation_ref = _validate_key_revocation_ref_v2(
            selector["revocation_ref"],
            paths=paths,
            code="u10_key_revocation_ref_invalid",
        )
        revocation_value, revocation_raw = _read_key_record_v2(
            Path(str(revocation_ref["locator"])),
            protected_root=paths.key_root,
            required_uid=required_uid,
            exact_mode=0o444,
            code="u10_key_revocation_unreadable",
        )
        revocation, observed_revocation_ref = _validate_key_revocation_v2(
            revocation_value,
            raw=revocation_raw,
            selector=selector,
            authorization_ref=observed_authorization_ref,
            consumption_ref=observed_consumption_ref,
            paths=paths,
        )
        if observed_revocation_ref != revocation_ref:
            raise BrokerBoundaryError(
                "u10_key_revocation_ref_mismatch",
                str(authorization["authorization_id"]),
            )
    receipt_path = Path(str(evidence["receipt_locator"]))
    if not receipt_path.exists() and not receipt_path.is_symlink():
        raise BrokerBoundaryError(
            "u10_key_transition_receipt_missing", str(receipt_path)
        )
    receipt_value, receipt_raw = _read_key_record_v2(
        receipt_path,
        protected_root=paths.ledger_root,
        required_uid=required_uid,
        exact_mode=0o444,
        code="u10_key_receipt_unreadable",
    )
    receipt = _validate_key_receipt_v2(
        receipt_value,
        raw=receipt_raw,
        selector=selector,
        selector_ref=selector_ref,
        authorization=authorization,
        authorization_ref=observed_authorization_ref,
        consumption=consumption,
        consumption_ref=observed_consumption_ref,
        paths=paths,
    )
    return {
        "authorization": authorization,
        "authorization_ref": observed_authorization_ref,
        "consumption": consumption,
        "consumption_ref": observed_consumption_ref,
        "metadata": metadata,
        "metadata_ref": metadata_ref,
        "private_material_ref": private_ref,
        "revocation": revocation,
        "revocation_ref": revocation_ref,
        "receipt": receipt,
        "receipt_ref": {
            "receipt_id": receipt["receipt_id"],
            "locator": str(receipt_path),
            "artifact_digest": digest_bytes(receipt_raw),
            "receipt_digest": receipt["receipt_digest"],
        },
    }


def _validate_key_transition_sequence_v2(
    sequence: list[dict[str, Any]],
) -> None:
    previous: dict[str, Any] | None = None
    for item in sequence:
        selector = item["selector"]
        selector_ref = item["selector_ref"]
        transition = item["transition"]
        authorization = transition["authorization"]
        consumption = transition["consumption"]
        mode = str(selector["transition_mode"])
        operation = str(authorization["key_operation"])
        prior_selector = None if previous is None else previous["selector"]
        prior_ref = None if previous is None else previous["selector_ref"]
        prior_active_key = (
            None
            if prior_selector is None or prior_selector["state"] != "active"
            else prior_selector["key_id"]
        )
        if (
            selector["previous_selector_ref"] != prior_ref
            or authorization["prior_selector_ref"] != prior_ref
            or consumption["prior_selector_ref"] != prior_ref
            or authorization["expected_current_key_id"] != prior_active_key
        ):
            raise BrokerBoundaryError(
                "u10_key_transition_predecessor_mismatch",
                str(authorization["authorization_id"]),
            )
        if mode == "initialize_empty_store":
            valid_state = previous is None and operation == "generate"
        elif mode == "generate_from_no_active_key":
            valid_state = (
                prior_selector is not None
                and prior_selector["state"] == "no_active_key"
                and operation == "generate"
            )
        elif mode == "rotate_active_key":
            valid_state = (
                prior_selector is not None
                and prior_selector["state"] == "active"
                and operation == "rotate"
                and authorization["key_id"] != prior_active_key
            )
        else:
            valid_state = (
                mode == "revoke_active_key"
                and prior_selector is not None
                and prior_selector["state"] == "active"
                and operation == "revoke"
                and authorization["key_id"] == prior_active_key
            )
        if not valid_state:
            raise BrokerBoundaryError("u10_key_transition_mode_state_mismatch", mode)
        selected_at = _key_timestamp_v2(
            selector["selected_at"], code="u10_key_selector_time_invalid"
        )
        reserved_at = _key_timestamp_v2(
            consumption["reserved_at"],
            code="u10_key_consumption_time_invalid",
        )
        artifact = transition["metadata"] or transition["revocation"]
        artifact_time_field = (
            "created_at" if transition["metadata"] is not None else "revoked_at"
        )
        artifact_time = _key_timestamp_v2(
            artifact[artifact_time_field], code="u10_key_artifact_time_invalid"
        )
        if not (reserved_at <= artifact_time <= selected_at):
            raise BrokerBoundaryError(
                "u10_key_transition_time_order_invalid",
                str(authorization["authorization_id"]),
            )
        if previous is not None:
            prior_selected = _key_timestamp_v2(
                prior_selector["selected_at"],
                code="u10_key_selector_time_invalid",
            )
            if prior_selected > reserved_at:
                raise BrokerBoundaryError(
                    "u10_key_transition_time_order_invalid",
                    str(authorization["authorization_id"]),
                )
        if selector["state"] == "active":
            metadata = transition["metadata"]
            if (
                metadata is None
                or metadata["key_id"] != authorization["key_id"]
                or metadata["key_entity_ref"] != authorization["key_entity_ref"]
            ):
                raise BrokerBoundaryError(
                    "u10_key_transition_key_identity_mismatch",
                    str(authorization["authorization_id"]),
                )
        else:
            revocation = transition["revocation"]
            if (
                revocation is None
                or revocation["key_id"] != authorization["key_id"]
                or revocation["key_entity_ref"] != authorization["key_entity_ref"]
            ):
                raise BrokerBoundaryError(
                    "u10_key_transition_key_identity_mismatch",
                    str(authorization["authorization_id"]),
                )
        previous = {
            "selector": selector,
            "selector_ref": selector_ref,
        }


def _validate_key_emergency_closure_v1(
    value: Mapping[str, Any],
    *,
    authorization_ref: Mapping[str, Any],
    consumption_ref: Mapping[str, Any],
    paths: KeyChainPaths,
) -> dict[str, Any]:
    _validate_key_record_schema_v2(
        value,
        paths=paths,
        schema_name=_KEY_EMERGENCY_CLOSURE_SCHEMA_V1,
        code="u10_key_emergency_closure_invalid",
    )
    _sealed_digest(
        value,
        "closure_digest",
        "u10_key_emergency_closure_seal_mismatch",
    )
    authorization_id = str(authorization_ref["authorization_id"])
    if (
        value["closure_id"] != f"emergency-closure.{authorization_id}"
        or value["authorization_ref"] != authorization_ref
        or value["consumption_ref"] != consumption_ref
        or value["closure_disposition"] != "abandoned_before_publication"
        or value["published_selector_ref"] is not None
    ):
        raise BrokerBoundaryError(
            "u10_key_emergency_closure_context_mismatch", authorization_id
        )
    if value["prior_selector_ref"] is not None:
        _validate_key_selector_ref_v2(
            value["prior_selector_ref"],
            paths=paths,
            code="u10_key_emergency_closure_prior_ref_invalid",
        )
    _key_timestamp_v2(
        value["recorded_at"], code="u10_key_emergency_closure_time_invalid"
    )
    return dict(value)


def _scan_key_transition_ledger_v2(
    *,
    paths: KeyChainPaths,
    required_uid: int,
    sequence: list[dict[str, Any]],
    legacy_selectors: Mapping[str, tuple[dict[str, Any], bytes, Path]],
) -> dict[str, dict[str, Any]]:
    validate_directory_chain(
        paths.u10_root, paths.ledger_root, required_uid=required_uid
    )
    suffixes = {
        ".authorization.json": ("authorization", 0o400),
        ".consumption.json": ("consumption", 0o400),
        ".receipt.json": ("receipt", 0o444),
        ".emergency-closure.json": ("emergency_closure", 0o444),
    }
    records: dict[str, dict[str, tuple[dict[str, Any], bytes]]] = {
        kind: {} for kind, _mode in suffixes.values()
    }
    legacy_records: dict[str, dict[str, tuple[dict[str, Any], bytes]]] = {
        kind: {} for kind in ("authorization", "consumption", "receipt")
    }
    for path in sorted(paths.ledger_root.iterdir()):
        matches = [
            (suffix, kind, mode)
            for suffix, (kind, mode) in suffixes.items()
            if path.name.endswith(suffix)
        ]
        if len(matches) != 1:
            raise BrokerBoundaryError(
                "u10_key_transition_ledger_entry_unexpected", str(path)
            )
        suffix, kind, mode = matches[0]
        authorization_id = path.name.removesuffix(suffix)
        value, raw = _read_key_record_v2(
            path,
            protected_root=paths.ledger_root,
            required_uid=required_uid,
            exact_mode=mode,
            code="u10_key_transition_ledger_record_unreadable",
        )
        schema_version = value.get("schema_version")
        if schema_version == _KEY_LEGACY_SCHEMA_ID_BY_KIND_V1.get(kind):
            legacy_authorization_id = _legacy_key_record_authorization_id_v1(
                value,
                raw,
                kind=kind,
                path=path,
                paths=paths,
            )
            if legacy_authorization_id != authorization_id:
                raise BrokerBoundaryError(
                    "u10_key_legacy_ledger_identifier_mismatch", str(path)
                )
            if legacy_authorization_id in legacy_records[kind]:
                raise BrokerBoundaryError("u10_key_legacy_ledger_duplicate", str(path))
            legacy_records[kind][legacy_authorization_id] = (value, raw)
            continue
        if schema_version != _KEY_RECORD_SCHEMA_IDS_V2[kind]:
            raise BrokerBoundaryError(
                "u10_key_transition_ledger_schema_unknown",
                f"{path}: {schema_version}",
            )
        if authorization_id in records[kind]:
            raise BrokerBoundaryError("u10_key_transition_ledger_duplicate", str(path))
        records[kind][authorization_id] = (value, raw)
    committed: dict[str, dict[str, Any]] = {
        str(item["transition"]["authorization"]["authorization_id"]): item
        for item in sequence
    }
    for authorization_id, item in committed.items():
        transition = item["transition"]
        expected = {
            "authorization": transition["authorization"],
            "consumption": transition["consumption"],
            "receipt": transition["receipt"],
        }
        for kind, value in expected.items():
            observed = records[kind].get(authorization_id)
            if observed is None or observed[0] != value:
                raise BrokerBoundaryError(
                    "u10_key_transition_ledger_chain_mismatch",
                    f"{authorization_id}: {kind}",
                )
        if authorization_id in records["emergency_closure"]:
            raise BrokerBoundaryError(
                "u10_key_committed_transition_has_emergency_closure",
                authorization_id,
            )
    all_ids = set().union(*(set(items) for items in records.values()))
    for authorization_id in sorted(all_ids - set(committed)):
        authorization_item = records["authorization"].get(authorization_id)
        consumption_item = records["consumption"].get(authorization_id)
        receipt_item = records["receipt"].get(authorization_id)
        closure_item = records["emergency_closure"].get(authorization_id)
        if (
            authorization_item is None
            or consumption_item is None
            or receipt_item is not None
            or closure_item is None
        ):
            raise BrokerBoundaryError(
                "u10_key_transition_unclosed_or_orphaned", authorization_id
            )
        authorization_value, authorization_raw = authorization_item
        consumption_value, consumption_raw = consumption_item
        reserved_at = _key_timestamp_v2(
            consumption_value.get("reserved_at"),
            code="u10_key_consumption_time_invalid",
        )
        authorization = _validate_key_authorization_v2(
            authorization_value, paths=paths, effective_at=reserved_at
        )
        consumption = _validate_key_consumption_v2(
            consumption_value,
            raw=consumption_raw,
            authorization=authorization,
            authorization_raw=authorization_raw,
            paths=paths,
        )
        authorization_ref = _key_authorization_ref_v2(
            authorization, authorization_raw, paths=paths
        )
        consumption_ref = _key_consumption_ref_v2(
            consumption, consumption_raw, paths=paths
        )
        closure = _validate_key_emergency_closure_v1(
            closure_item[0],
            authorization_ref=authorization_ref,
            consumption_ref=consumption_ref,
            paths=paths,
        )
        if closure["prior_selector_ref"] != consumption["prior_selector_ref"]:
            raise BrokerBoundaryError(
                "u10_key_emergency_closure_chain_mismatch", authorization_id
            )

    legacy_id_sets = {kind: set(items) for kind, items in legacy_records.items()}
    legacy_ids = set().union(*legacy_id_sets.values())
    if any(ids != legacy_ids for ids in legacy_id_sets.values()):
        raise BrokerBoundaryError(
            "u10_key_legacy_transition_unclosed",
            repr({kind: sorted(ids) for kind, ids in legacy_id_sets.items()}),
        )
    if set(legacy_selectors) != legacy_ids:
        raise BrokerBoundaryError(
            "u10_key_legacy_selector_closure_mismatch",
            repr(
                {
                    "missing": sorted(legacy_ids - set(legacy_selectors)),
                    "orphaned": sorted(set(legacy_selectors) - legacy_ids),
                }
            ),
        )

    completed: dict[str, dict[str, Any]] = {}
    for authorization_id in sorted(legacy_ids):
        authorization, authorization_raw = legacy_records["authorization"][
            authorization_id
        ]
        consumption, _consumption_raw = legacy_records["consumption"][authorization_id]
        receipt, _receipt_raw = legacy_records["receipt"][authorization_id]
        authorization_ref = {
            "authorization_id": authorization_id,
            "authorization_digest": authorization["authorization_digest"],
        }
        archived_authorization_ref = {
            **authorization_ref,
            "artifact_digest": digest_bytes(authorization_raw),
        }
        consumption_ref = {
            "consumption_id": f"consumption.{authorization_id}",
            "consumption_digest": consumption["consumption_digest"],
        }
        reserved_at = _key_timestamp_v2(
            consumption["reserved_at"],
            code="u10_key_legacy_consumption_time_invalid",
        )
        not_before = _key_timestamp_v2(
            authorization["not_before"],
            code="u10_key_legacy_authorization_time_invalid",
        )
        expires_at = _key_timestamp_v2(
            authorization["expires_at"],
            code="u10_key_legacy_authorization_time_invalid",
        )
        publication_not_before = _key_timestamp_v2(
            receipt["publication_not_before"],
            code="u10_key_legacy_receipt_time_invalid",
        )
        if (
            consumption["authorization_ref"] != archived_authorization_ref
            or receipt["authorization_ref"] != authorization_ref
            or receipt["consumption_ref"] != consumption_ref
            or consumption["key_operation"] != authorization["key_operation"]
            or receipt["key_operation"] != authorization["key_operation"]
            or consumption["key_id"] != authorization["key_id"]
            or receipt["key_id"] != authorization["key_id"]
            or consumption["publisher_contract_binding"]
            != receipt["publisher_contract_binding"]
            or not not_before <= reserved_at <= expires_at
            or publication_not_before != reserved_at
        ):
            raise BrokerBoundaryError(
                "u10_key_legacy_transition_context_mismatch", authorization_id
            )
        expected_current_key_id = authorization["expected_current_key_id"]
        operation = authorization["key_operation"]
        if (
            (operation == "generate" and expected_current_key_id is not None)
            or (
                operation in {"rotate", "revoke"}
                and not isinstance(expected_current_key_id, str)
            )
            or (
                operation == "revoke"
                and expected_current_key_id != authorization["key_id"]
            )
        ):
            raise BrokerBoundaryError(
                "u10_key_legacy_transition_context_mismatch", authorization_id
            )
        selector_item = legacy_selectors.get(authorization_id)
        if selector_item is not None:
            selector = selector_item[0]
            expected_state = "no_active_key" if operation == "revoke" else "active"
            if (
                selector["transition_authorization_ref"] != authorization_ref
                or selector["selected_at"] != receipt["publication_observed_at"]
                or selector["state"] != expected_state
                or selector["key_id"]
                != (None if operation == "revoke" else authorization["key_id"])
                or (
                    operation != "revoke"
                    and selector["public_metadata_ref"]
                    != receipt["public_metadata_ref"]
                )
            ):
                raise BrokerBoundaryError(
                    "u10_key_legacy_selector_context_mismatch", authorization_id
                )
        completed[authorization_id] = {
            "authorization": authorization,
            "authorization_ref": authorization_ref,
            "consumption": consumption,
            "consumption_ref": consumption_ref,
            "receipt": receipt,
            "selector": None if selector_item is None else selector_item[0],
        }
    return completed


def _scan_key_material_denominator_v2(
    *,
    paths: KeyChainPaths,
    required_uid: int,
    sequence: list[dict[str, Any]],
    legacy_transitions: Mapping[str, Mapping[str, Any]],
) -> None:
    referenced_metadata = {
        str(item["transition"]["metadata_ref"]["locator"])
        for item in sequence
        if item["transition"]["metadata_ref"] is not None
    }
    referenced_revocations = {
        str(item["transition"]["revocation_ref"]["locator"])
        for item in sequence
        if item["transition"]["revocation_ref"] is not None
    }
    expected_legacy_metadata: dict[str, str] = {}
    for authorization_id, item in legacy_transitions.items():
        if item["authorization"]["key_operation"] not in {"generate", "rotate"}:
            continue
        locator = str(item["receipt"]["public_metadata_ref"]["metadata_locator"])
        if locator in expected_legacy_metadata:
            raise BrokerBoundaryError("u10_key_legacy_metadata_ref_duplicate", locator)
        expected_legacy_metadata[locator] = authorization_id
    expected_legacy_revocations = {
        str(
            paths.revocation_root
            / str(item["authorization"]["key_id"])
            / f"{authorization_id}.json"
        ): authorization_id
        for authorization_id, item in legacy_transitions.items()
        if item["authorization"]["key_operation"] == "revoke"
    }
    observed_legacy_metadata: set[str] = set()
    observed_legacy_revocations: set[str] = set()
    validate_directory_chain(
        paths.u10_root, paths.generation_root, required_uid=required_uid
    )
    for generation in sorted(paths.generation_root.iterdir()):
        if generation.name.startswith("."):
            raise BrokerBoundaryError(
                "u10_key_generation_stage_orphaned", str(generation)
            )
        validate_directory_chain(paths.key_root, generation, required_uid=required_uid)
        metadata_path = generation / "public-metadata.json"
        if not metadata_path.exists() and not metadata_path.is_symlink():
            raise BrokerBoundaryError(
                "u10_key_generation_metadata_missing", str(generation)
            )
        metadata, _raw = _read_key_record_v2(
            metadata_path,
            protected_root=paths.key_root,
            required_uid=required_uid,
            exact_mode=0o444,
            code="u10_key_generation_metadata_unreadable",
        )
        if {item.name for item in generation.iterdir()} != {
            "private.ed25519",
            "public-metadata.json",
        }:
            raise BrokerBoundaryError(
                "u10_key_generation_denominator_mismatch", str(generation)
            )
        schema_version = metadata.get("schema_version")
        if schema_version == _KEY_LEGACY_SCHEMA_ID_BY_KIND_V1["metadata"]:
            authorization_id = _legacy_key_record_authorization_id_v1(
                metadata,
                _raw,
                kind="metadata",
                path=metadata_path,
                paths=paths,
            )
            transition = legacy_transitions.get(authorization_id)
            if (
                transition is None
                or transition["authorization"]["key_operation"]
                not in {"generate", "rotate"}
                or expected_legacy_metadata.get(str(metadata_path)) != authorization_id
                or metadata["authorization_ref"] != transition["authorization_ref"]
                or metadata["generation_evidence_selector"]
                != transition["receipt"]["generation_evidence_selector"]
            ):
                raise BrokerBoundaryError(
                    "u10_key_legacy_generation_orphaned", str(metadata_path)
                )
            observed_ref = {
                "key_id": metadata["key_id"],
                "key_entity_ref": metadata["key_entity_ref"],
                "metadata_locator": str(metadata_path),
                "metadata_artifact_digest": digest_bytes(_raw),
                "metadata_digest": metadata["metadata_digest"],
                "generation_authorization_ref": metadata["authorization_ref"],
                "generation_receipt_selector": {
                    "ledger_root": str(paths.ledger_root),
                    "receipt_record": f"{authorization_id}.receipt.json",
                    "resolution_policy": "resolve_exact_generation_receipt/v1",
                },
            }
            if transition["receipt"]["public_metadata_ref"] != observed_ref:
                raise BrokerBoundaryError(
                    "u10_key_legacy_generation_ref_mismatch", str(metadata_path)
                )
            _read_private_key_for_chain_v2(
                metadata, paths=paths, required_uid=required_uid
            )
            observed_legacy_metadata.add(str(metadata_path))
            continue
        if schema_version != _KEY_RECORD_SCHEMA_IDS_V2["metadata"]:
            raise BrokerBoundaryError(
                "u10_key_generation_schema_unknown", str(metadata_path)
            )
        if str(metadata_path) not in referenced_metadata:
            raise BrokerBoundaryError("u10_key_generation_orphaned", str(metadata_path))
    validate_directory_chain(
        paths.u10_root, paths.revocation_root, required_uid=required_uid
    )
    for key_directory in sorted(paths.revocation_root.iterdir()):
        if key_directory.name.startswith("."):
            raise BrokerBoundaryError(
                "u10_key_revocation_stage_orphaned", str(key_directory)
            )
        validate_directory_chain(
            paths.key_root, key_directory, required_uid=required_uid
        )
        observed_entries = 0
        for path in sorted(key_directory.iterdir()):
            if path.suffix != ".json" or path.name.startswith("."):
                raise BrokerBoundaryError(
                    "u10_key_revocation_entry_unexpected", str(path)
                )
            revocation, _raw = _read_key_record_v2(
                path,
                protected_root=paths.key_root,
                required_uid=required_uid,
                exact_mode=0o444,
                code="u10_key_revocation_unreadable",
            )
            observed_entries += 1
            schema_version = revocation.get("schema_version")
            if schema_version == _KEY_LEGACY_SCHEMA_ID_BY_KIND_V1["revocation"]:
                authorization_id = _legacy_key_record_authorization_id_v1(
                    revocation,
                    _raw,
                    kind="revocation",
                    path=path,
                    paths=paths,
                )
                transition = legacy_transitions.get(authorization_id)
                if (
                    transition is None
                    or transition["authorization"]["key_operation"] != "revoke"
                    or expected_legacy_revocations.get(str(path)) != authorization_id
                    or revocation["authorization_ref"]
                    != transition["authorization_ref"]
                    or revocation["key_id"] != transition["authorization"]["key_id"]
                ):
                    raise BrokerBoundaryError(
                        "u10_key_legacy_revocation_orphaned", str(path)
                    )
                observed_legacy_revocations.add(str(path))
                continue
            if schema_version != _KEY_RECORD_SCHEMA_IDS_V2["revocation"]:
                raise BrokerBoundaryError(
                    "u10_key_revocation_schema_unknown", str(path)
                )
            if str(path) not in referenced_revocations:
                raise BrokerBoundaryError("u10_key_revocation_orphaned", str(path))
        if observed_entries == 0:
            raise BrokerBoundaryError(
                "u10_key_revocation_directory_orphaned", str(key_directory)
            )
    missing_metadata = sorted(set(expected_legacy_metadata) - observed_legacy_metadata)
    if missing_metadata:
        raise BrokerBoundaryError(
            "u10_key_legacy_generation_missing", ",".join(missing_metadata)
        )
    missing_revocations = sorted(
        set(expected_legacy_revocations) - observed_legacy_revocations
    )
    if missing_revocations:
        raise BrokerBoundaryError(
            "u10_key_legacy_revocation_missing", ",".join(missing_revocations)
        )


def resolve_current_signing_key_chain_v2_under_trust_store_lock(
    *,
    paths: KeyChainPaths | Mapping[str, Any] = KeyChainPaths(),
    required_uid: int = 0,
) -> dict[str, Any]:
    """Replay the complete v2 key chain while the caller holds store lock.

    This function deliberately does not acquire ``trust-store.lock``.  It takes
    only the subordinate shared key-transition lock, validates every committed
    v2 transition and the closed ledger denominator, and never returns private
    key bytes.
    """

    resolved_paths = _coerce_key_chain_paths_v2(paths)
    _validate_key_chain_path_authority_v2(resolved_paths, required_uid=required_uid)
    with _key_transition_shared_lock_under_trust_store_v2(
        resolved_paths, required_uid=required_uid
    ):
        history, legacy_selectors = _scan_key_selector_history_v2(
            resolved_paths, required_uid=required_uid
        )
        current = _load_current_key_selector_v2(
            resolved_paths, required_uid=required_uid
        )
        reverse_chain: list[tuple[dict[str, Any], bytes, dict[str, Any]]] = []
        observed_digests: set[str] = set()
        item = current
        while item is not None:
            selector, raw, selector_ref = item
            digest = str(selector_ref["artifact_digest"]["value"])
            if digest in observed_digests:
                raise BrokerBoundaryError("u10_key_selector_cycle", digest)
            observed_digests.add(digest)
            stored = history.get(digest)
            if stored is None or stored[1] != raw or stored[2] != selector_ref:
                raise BrokerBoundaryError("u10_key_selector_history_mismatch", digest)
            reverse_chain.append(item)
            previous_ref = selector["previous_selector_ref"]
            item = (
                None
                if previous_ref is None
                else _read_key_selector_ref_v2(
                    previous_ref,
                    paths=resolved_paths,
                    required_uid=required_uid,
                )
            )
        extras = sorted(set(history) - observed_digests)
        if extras:
            raise BrokerBoundaryError(
                "u10_key_selector_branch_or_rollback", ",".join(extras)
            )
        sequence: list[dict[str, Any]] = []
        for selector, _raw, selector_ref in reversed(reverse_chain):
            transition = _read_key_transition_v2(
                selector,
                selector_ref,
                paths=resolved_paths,
                required_uid=required_uid,
            )
            sequence.append(
                {
                    "selector": selector,
                    "selector_ref": selector_ref,
                    "transition": transition,
                }
            )
        _validate_key_transition_sequence_v2(sequence)
        legacy_transitions = _scan_key_transition_ledger_v2(
            paths=resolved_paths,
            required_uid=required_uid,
            sequence=sequence,
            legacy_selectors=legacy_selectors,
        )
        _scan_key_material_denominator_v2(
            paths=resolved_paths,
            required_uid=required_uid,
            sequence=sequence,
            legacy_transitions=legacy_transitions,
        )
        current_after = _load_current_key_selector_v2(
            resolved_paths, required_uid=required_uid
        )
        if current_after != current:
            raise BrokerBoundaryError(
                "u10_key_current_selector_changed_during_replay",
                str(resolved_paths.selector_path),
            )
        transition_sequence = [
            {
                "selector_ref": item["selector_ref"],
                "previous_selector_ref": item["selector"]["previous_selector_ref"],
                "transition_mode": item["selector"]["transition_mode"],
                "authorization_ref": item["transition"]["authorization_ref"],
                "consumption_ref": item["transition"]["consumption_ref"],
                "receipt_ref": item["transition"]["receipt_ref"],
                "public_metadata_ref": item["transition"]["metadata_ref"],
                "revocation_ref": item["transition"]["revocation_ref"],
            }
            for item in sequence
        ]
        active_key: dict[str, Any] | None = None
        if sequence and sequence[-1]["selector"]["state"] == "active":
            transition = sequence[-1]["transition"]
            metadata = transition["metadata"]
            active_key = {
                "key_id": metadata["key_id"],
                "key_entity_ref": metadata["key_entity_ref"],
                "public_metadata": metadata,
                "public_metadata_ref": transition["metadata_ref"],
                "private_material_ref": transition["private_material_ref"],
            }
        return {
            "schema_version": "semantic-guard-u10-key-chain-replay/v1",
            "replay_status": "complete",
            "current_selector": None if current is None else current[0],
            "current_selector_ref": None if current is None else current[2],
            "active_key": active_key,
            "transition_sequence": transition_sequence,
            "transition_count": len(transition_sequence),
            "formal_authority": "none",
            "positive_assurance_allowed": False,
        }


def _ed25519_private_key_from_root_raw_v1(
    raw: bytes, *, path: Path
) -> Ed25519PrivateKey:
    if len(raw) != 32:
        raise BrokerBoundaryError("u10_signing_key_raw_length_invalid", str(path))
    try:
        key = Ed25519PrivateKey.from_private_bytes(raw)
    except ValueError as exc:
        raise BrokerBoundaryError("u10_signing_key_unreadable", str(path)) from exc
    return key


def _load_private_key(store: Mapping[str, Any]) -> Ed25519PrivateKey:
    config = store["signing_key"]
    path = Path(str(config["private_key_path"]))
    raw = read_protected_file(
        path,
        protected_root=KEY_ROOT,
        private=True,
    )
    key = _ed25519_private_key_from_root_raw_v1(raw, path=path)
    public_raw = key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    observed_public = base64.b64encode(public_raw).decode("ascii")
    if observed_public != config["public_key_base64"]:
        raise BrokerBoundaryError("u10_signing_key_public_mismatch", str(path))
    return key


def _validate_current_signing_key_for_store_activation_v1(
    store: Mapping[str, Any],
    basis: Mapping[str, Any],
) -> Ed25519PrivateKey:
    del store, basis
    raise BrokerBoundaryError(
        "u10_legacy_key_selector_read_only",
        "store activation requires the replayable v2 key chain",
    )


def _validate_current_signing_key_for_store_activation_v2(
    store: Mapping[str, Any],
    basis: Mapping[str, Any],
) -> Ed25519PrivateKey:
    """Match the basis and store projection to the complete live v2 chain."""

    replay = resolve_current_signing_key_chain_v2_under_trust_store_lock()
    active_key = replay.get("active_key")
    selector_ref = replay.get("current_selector_ref")
    if not isinstance(active_key, Mapping) or not isinstance(selector_ref, Mapping):
        raise BrokerBoundaryError(
            "u10_store_activation_active_signing_key_required",
            str(replay.get("current_selector")),
        )
    metadata = active_key["public_metadata"]
    metadata_ref = active_key["public_metadata_ref"]
    private_ref = active_key["private_material_ref"]
    expected_store_projection = {
        "key_id": metadata["key_id"],
        "key_state": "active",
        "algorithm": "ed25519",
        "public_key_base64": metadata["public_key"]["value"],
        "private_key_path": private_ref["locator"],
        "private_key_owner_uid": 0,
        "private_key_owner_gid": 0,
        "private_key_mode": "0600",
        "key_usage": "u10_broker_execution_attestation_only",
    }
    store_content = basis.get("store_content")
    basis_signing_key = (
        store_content.get("signing_key") if isinstance(store_content, Mapping) else None
    )
    if (
        basis.get("schema_version") != "semantic-guard-u10-store-activation-basis/v2"
        or basis.get("signing_key_ref") != metadata_ref
        or basis.get("signing_key_selector_ref") != selector_ref
        or store.get("signing_key") != expected_store_projection
        or basis_signing_key != expected_store_projection
    ):
        raise BrokerBoundaryError(
            "u10_store_activation_signing_key_chain_mismatch",
            str(store.get("signing_key", {}).get("key_id")),
        )
    return _load_private_key(store)


def _sign_statement(
    statement: Mapping[str, Any],
    private_key: Ed25519PrivateKey,
    *,
    signature_prefix: bytes = SIGNATURE_PREFIX,
) -> bytes:
    return private_key.sign(signature_prefix + canonical_json_bytes(statement))


def _verify_statement_signature(
    statement: Mapping[str, Any],
    signature: bytes,
    public_key: Ed25519PublicKey,
    *,
    signature_prefix: bytes = SIGNATURE_PREFIX,
) -> None:
    try:
        public_key.verify(
            signature,
            signature_prefix + canonical_json_bytes(statement),
        )
    except InvalidSignature as exc:
        raise BrokerBoundaryError("u10_envelope_signature_invalid", "ed25519") from exc


def _validate_execution_observations_v2(
    *,
    worker_reported_observation: Mapping[str, Any],
    broker_execution_observation: Mapping[str, Any],
    receipt_started_at: Any,
    receipt_finished_at: Any,
    started_at: Any,
    finished_at: Any,
    attested_at: Any | None = None,
) -> None:
    """Validate root claims separately from bound worker self-report."""

    worker_required = {"process", "interval"}
    worker_process_fields = {
        "pid",
        "parent_pid",
        "process_group_id",
        "session_id",
    }
    root_required = {
        "process",
        "exit_code",
        "process_group_quiescence",
    }
    root_process_fields = {*worker_process_fields, "observed_at"}
    if not isinstance(worker_reported_observation, Mapping) or not isinstance(
        broker_execution_observation, Mapping
    ):
        raise BrokerBoundaryError("u10_broker_execution_observation_invalid", "shape")
    worker_process = worker_reported_observation.get("process")
    worker_interval = worker_reported_observation.get("interval")
    root_process = broker_execution_observation.get("process")
    quiescence = broker_execution_observation.get("process_group_quiescence")
    if (
        set(worker_reported_observation) != worker_required
        or not isinstance(worker_process, Mapping)
        or set(worker_process) != worker_process_fields
        or not isinstance(worker_interval, Mapping)
        or set(worker_interval) != {"started_at", "finished_at"}
        or set(broker_execution_observation) != root_required
        or not isinstance(root_process, Mapping)
        or set(root_process) != root_process_fields
        or not isinstance(quiescence, Mapping)
        or set(quiescence) != {"process_group_id", "state", "observed_at"}
        or any(
            type(value) is not int or value <= 0 for value in worker_process.values()
        )
        or any(
            type(root_process[name]) is not int or root_process[name] <= 0
            for name in worker_process_fields
        )
        or type(broker_execution_observation.get("exit_code")) is not int
        or broker_execution_observation.get("exit_code") != 0
        or type(quiescence.get("process_group_id")) is not int
        or quiescence.get("process_group_id") <= 0
        or quiescence.get("state") != "absent"
    ):
        raise BrokerBoundaryError("u10_broker_execution_observation_invalid", "shape")
    expected_worker_process = {
        name: root_process[name] for name in worker_process_fields
    }
    if (
        dict(worker_process) != expected_worker_process
        or root_process["pid"] != root_process["process_group_id"]
        or root_process["pid"] != root_process["session_id"]
        or quiescence["process_group_id"] != root_process["process_group_id"]
    ):
        raise BrokerBoundaryError(
            "u10_broker_worker_process_mismatch", "process identifiers"
        )
    _require_time_order(
        ("root_started_at", started_at),
        ("worker_started_at", worker_interval["started_at"]),
        ("receipt_started_at", receipt_started_at),
        ("receipt_finished_at", receipt_finished_at),
        ("worker_finished_at", worker_interval["finished_at"]),
        ("root_finished_at", finished_at),
    )
    # Process observation and worker self-report can race.  Both root
    # observations only need to lie within the root-owned occurrence interval.
    _require_time_order(
        ("root_started_at", started_at),
        ("process_observed_at", root_process["observed_at"]),
        ("root_finished_at", finished_at),
    )
    _require_time_order(
        ("root_started_at", started_at),
        ("process_group_quiescence_observed_at", quiescence["observed_at"]),
        ("root_finished_at", finished_at),
    )
    if attested_at is not None:
        _require_time_order(
            ("root_finished_at", finished_at),
            ("attested_at", attested_at),
        )


def _build_signed_envelope_v2(
    signed_statement: Mapping[str, Any],
    *,
    store: Mapping[str, Any],
) -> dict[str, Any]:
    if signed_statement.get("key_id") != store["signing_key"]["key_id"]:
        raise BrokerBoundaryError("u10_statement_key_id_mismatch", "key_id")
    fixed_store, store_raw = load_active_root_trust_store_for_execution_v2()
    if fixed_store != store:
        raise BrokerBoundaryError("u10_signing_store_changed", "fixed store")
    if signed_statement.get("trust_store_ref") != derive_historical_store_ref_v2(
        store, store_raw
    ):
        raise BrokerBoundaryError("u10_signing_history_ref_mismatch", "history ref")
    placeholder_signature = base64.b64encode(bytes(64)).decode("ascii")
    provisional: dict[str, Any] = {
        "schema_version": "semantic-guard-broker-attested-execution-envelope/v2",
        "signed_statement": dict(signed_statement),
        "signature": {
            "algorithm": "ed25519",
            "encoding": "base64",
            "signed_member": "signed_statement",
            "value": placeholder_signature,
        },
    }
    provisional["envelope_digest"] = digest_bytes(canonical_json_bytes(provisional))
    _verify_broker_attested_envelope_with_store_v2(
        provisional,
        store=store,
        store_raw=store_raw,
        verify_signature=False,
    )
    private_key = _load_private_key(store)
    signature = _sign_statement(signed_statement, private_key)
    envelope: dict[str, Any] = {
        "schema_version": "semantic-guard-broker-attested-execution-envelope/v2",
        "signed_statement": dict(signed_statement),
        "signature": {
            "algorithm": "ed25519",
            "encoding": "base64",
            "signed_member": "signed_statement",
            "value": base64.b64encode(signature).decode("ascii"),
        },
    }
    envelope["envelope_digest"] = digest_bytes(canonical_json_bytes(envelope))
    _validate(
        envelope,
        "broker-attested-execution-envelope-v2.schema.json",
        "u10_broker_envelope_invalid",
    )
    _verify_broker_attested_envelope_with_store_v2(
        envelope,
        store=store,
        store_raw=store_raw,
    )
    return envelope


def _build_signed_envelope_v3(
    signed_statement: Mapping[str, Any],
    *,
    store: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the external-adoption-bound execution envelope."""

    if signed_statement.get("key_id") != store["signing_key"]["key_id"]:
        raise BrokerBoundaryError("u10_statement_key_id_mismatch", "key_id")
    fixed_store, store_raw = load_active_root_trust_store_for_execution_v3()
    if fixed_store != store:
        raise BrokerBoundaryError("u10_signing_store_changed", "fixed store")
    if signed_statement.get("trust_store_ref") != derive_historical_store_ref_v2(
        store, store_raw
    ):
        raise BrokerBoundaryError("u10_signing_history_ref_mismatch", "history ref")
    placeholder_signature = base64.b64encode(bytes(64)).decode("ascii")
    provisional: dict[str, Any] = {
        "schema_version": ("semantic-guard-broker-attested-execution-envelope/v3"),
        "signed_statement": dict(signed_statement),
        "signature": {
            "algorithm": "ed25519",
            "encoding": "base64",
            "signed_member": "signed_statement",
            "value": placeholder_signature,
        },
    }
    provisional["envelope_digest"] = digest_bytes(canonical_json_bytes(provisional))
    _verify_broker_attested_envelope_with_store_v3(
        provisional,
        store=store,
        store_raw=store_raw,
        verify_signature=False,
    )
    private_key = _load_private_key(store)
    signature = _sign_statement(
        signed_statement,
        private_key,
        signature_prefix=SIGNATURE_PREFIX_V3,
    )
    envelope: dict[str, Any] = {
        "schema_version": ("semantic-guard-broker-attested-execution-envelope/v3"),
        "signed_statement": dict(signed_statement),
        "signature": {
            "algorithm": "ed25519",
            "encoding": "base64",
            "signed_member": "signed_statement",
            "value": base64.b64encode(signature).decode("ascii"),
        },
    }
    envelope["envelope_digest"] = digest_bytes(canonical_json_bytes(envelope))
    _validate(
        envelope,
        "broker-attested-execution-envelope-v3.schema.json",
        "u10_broker_envelope_invalid",
    )
    _verify_broker_attested_envelope_with_store_v3(
        envelope,
        store=store,
        store_raw=store_raw,
    )
    return envelope


def _verify_broker_attested_envelope_with_store_v2(
    envelope: Mapping[str, Any],
    *,
    store: Mapping[str, Any],
    store_raw: bytes | None = None,
    verify_signature: bool = True,
    envelope_schema_name: str = "broker-attested-execution-envelope-v2.schema.json",
    signature_prefix: bytes = SIGNATURE_PREFIX,
    require_external_adoption: bool = False,
) -> dict[str, Any]:
    validate_root_trust_store_v2(store)
    _validate(
        envelope,
        envelope_schema_name,
        "u10_broker_envelope_invalid",
    )
    _sealed_digest(envelope, "envelope_digest", "u10_envelope_digest_mismatch")
    statement = envelope["signed_statement"]
    if statement["key_id"] != store["signing_key"]["key_id"]:
        raise BrokerBoundaryError("u10_envelope_key_id_mismatch", "key_id")
    if verify_signature:
        try:
            public_raw = base64.b64decode(
                store["signing_key"]["public_key_base64"], validate=True
            )
            public_key = Ed25519PublicKey.from_public_bytes(public_raw)
            signature = base64.b64decode(envelope["signature"]["value"], validate=True)
            _verify_statement_signature(
                statement,
                signature,
                public_key,
                signature_prefix=signature_prefix,
            )
        except (ValueError, BrokerBoundaryError) as exc:
            raise BrokerBoundaryError(
                "u10_envelope_signature_invalid", "ed25519"
            ) from exc
    store_ref = statement["trust_store_ref"]
    entry_ref = statement["trust_entry_ref"]
    entry_id = str(entry_ref["entry_id"])
    entry = store["entries"].get(entry_id)
    if store_raw is None:
        raise BrokerBoundaryError("u10_historical_store_raw_required", entry_id)
    _verify_current_selector_contract_v1(store)
    _load_complete_store_activation_chain_v1(store, store_raw)
    expected_store_ref = derive_historical_store_ref_v2(store, store_raw)
    if (
        store_ref != expected_store_ref
        or not isinstance(entry, Mapping)
        or entry_ref["store_id"] != store["store_id"]
        or entry_ref["store_revision_id"] != store["store_revision_id"]
        or entry_ref["store_version"] != store["store_version"]
        or entry_ref["entry_digest"] != entry.get("entry_digest")
        or entry_ref["entry_state"] != "active"
    ):
        raise BrokerBoundaryError("u10_envelope_store_context_mismatch", entry_id)
    request = statement["request"]
    if request["entry_id"] != entry_id:
        raise BrokerBoundaryError("u10_envelope_request_entry_mismatch", entry_id)
    _entry, snapshot = load_active_snapshot_manifest_v1(
        store,
        entry_id,
        enforce_current_runtime=False,
        reobserve_current_account=False,
    )
    expected_environment_adoption_ref = snapshot.get("environment_adoption_ref")
    if require_external_adoption and (
        not isinstance(expected_environment_adoption_ref, Mapping)
        or statement.get("environment_adoption_ref")
        != expected_environment_adoption_ref
        or statement.get("eligibility_source_ref", {}).get("lifecycle_state")
        != "candidate"
    ):
        raise BrokerBoundaryError(
            "u10_envelope_environment_adoption_mismatch", entry_id
        )
    if (
        statement["broker"]["broker_id"] != BROKER_ID
        or statement["broker"]["broker_version"] != store["broker_runtime_version"]
        or statement["broker"]["runtime_ref"] != store["broker_runtime_ref"]
        or snapshot["broker_runtime_ref"] != store["broker_runtime_ref"]
    ):
        raise BrokerBoundaryError("u10_envelope_broker_runtime_mismatch", entry_id)
    expected_worker = {
        "uid": snapshot["worker_identity"]["uid"],
        "gid": snapshot["worker_identity"]["gid"],
        "supplementary_gids": snapshot["worker_identity"][
            "effective_supplementary_gids"
        ],
        "umask": snapshot["worker_identity"]["umask"],
    }
    if statement["worker_identity"] != expected_worker:
        raise BrokerBoundaryError("u10_envelope_worker_identity_mismatch", entry_id)
    if (
        statement["preactivation_boundary_binding"]
        != snapshot["preactivation_boundary_binding"]
        or statement["preactivation_boundary_binding"]
        != entry["preactivation_boundary_binding"]
        or statement["preactivation_boundary_binding"]["effective_worker_identity"]
        != {
            "uid": expected_worker["uid"],
            "gid": expected_worker["gid"],
            "effective_supplementary_gids": expected_worker["supplementary_gids"],
            "umask": expected_worker["umask"],
        }
    ):
        raise BrokerBoundaryError(
            "u10_envelope_preactivation_binding_mismatch", entry_id
        )
    context_ref = statement["broker_context_ref"]
    context_path = Path(str(context_ref["locator"]))
    context_raw = read_protected_file(
        context_path,
        protected_root=EVIDENCE_SPOOL_ROOT,
    )
    if context_ref["artifact_digest"] != digest_bytes(context_raw):
        raise BrokerBoundaryError("u10_envelope_context_artifact_mismatch", entry_id)
    broker_context = _load_json_bytes(
        context_raw,
        "u10_envelope_context_unreadable",
    )
    command_id = str(request["command_id"])
    _validate_broker_context_phase_budget_v1(
        broker_context=broker_context,
        context_ref=context_ref,
        snapshot=snapshot,
        command_id=command_id,
    )
    if (
        context_ref["schema_version"] != broker_context.get("schema_version")
        or context_ref["semantic_digest"]
        != digest_bytes(canonical_json_bytes(broker_context))
        or context_ref["run_id"] != broker_context.get("run_id")
        or broker_context.get("entry_id") != entry_id
        or broker_context.get("command_id") != request["command_id"]
        or broker_context.get("request_nonce") != request["request_nonce"]
        or broker_context.get("snapshot_root")
        != snapshot["root_storage"]["snapshot_path"]
        or broker_context.get("worker_identity") != expected_worker
    ):
        raise BrokerBoundaryError("u10_envelope_context_binding_mismatch", entry_id)
    expected_context_refs = {
        "source_ref": {
            "record_id": snapshot["eligibility_source_ref"]["snapshot_artifact_ref"][
                "record_id"
            ],
            "locator": snapshot["eligibility_source_ref"]["snapshot_artifact_ref"][
                "locator"
            ],
            "artifact_digest": snapshot["eligibility_source_ref"][
                "snapshot_artifact_ref"
            ]["artifact_digest"],
            "source_digest": snapshot["eligibility_source_ref"]["source_digest"],
        },
        "profile_ref": {
            "record_id": snapshot["verification_profile_ref"]["snapshot_artifact_ref"][
                "record_id"
            ],
            "locator": snapshot["verification_profile_ref"]["snapshot_artifact_ref"][
                "locator"
            ],
            "artifact_digest": snapshot["verification_profile_ref"][
                "snapshot_artifact_ref"
            ]["artifact_digest"],
            "content_digest": snapshot["verification_profile_ref"]["content_digest"],
        },
        "environment_ref": {
            "record_id": snapshot["environment_profile_ref"]["snapshot_artifact_ref"][
                "record_id"
            ],
            "locator": snapshot["environment_profile_ref"]["snapshot_artifact_ref"][
                "locator"
            ],
            "artifact_digest": snapshot["environment_profile_ref"][
                "snapshot_artifact_ref"
            ]["artifact_digest"],
            "basis_digest": snapshot["environment_profile_ref"]["basis_digest"],
        },
    }
    if any(
        broker_context.get(name) != expected
        for name, expected in expected_context_refs.items()
    ):
        raise BrokerBoundaryError(
            "u10_envelope_context_qualification_mismatch", entry_id
        )
    if require_external_adoption:
        context_adoption_ref = broker_context.get("environment_adoption_ref")
        context_adoption = broker_context.get("environment_adoption")
        if not isinstance(context_adoption, Mapping):
            raise BrokerBoundaryError(
                "u10_envelope_context_environment_adoption_mismatch",
                entry_id,
            )
        _validate(
            context_adoption,
            "u10-snapshot-environment-adoption-v1.schema.json",
            "u10_envelope_context_environment_adoption_invalid",
        )
        _sealed_digest(
            context_adoption,
            "adoption_digest",
            "u10_envelope_context_environment_adoption_digest_mismatch",
        )
        exact_context_adoption_ref = {
            "record_id": context_adoption["adoption_id"],
            "locator": expected_environment_adoption_ref["locator"],
            "artifact_digest": digest_bytes(
                canonical_json_bytes(context_adoption) + b"\n"
            ),
            "semantic_digest": context_adoption["adoption_digest"],
        }
        if (
            context_ref.get("schema_version") != "semantic-guard-u10-worker-context/v2"
            or context_adoption_ref != expected_environment_adoption_ref
            or context_adoption_ref != statement["environment_adoption_ref"]
            or exact_context_adoption_ref != context_adoption_ref
            or context_adoption["formal_authority"] != "none"
            or context_adoption["positive_assurance_allowed"] is not False
        ):
            raise BrokerBoundaryError(
                "u10_envelope_context_environment_adoption_mismatch",
                entry_id,
            )
    worker_runtime = snapshot["worker_runtime"]
    expected_static_launch = {
        "worker_version": worker_runtime["worker_version"],
        "interpreter_ref": worker_runtime["interpreter_snapshot_ref"],
        "entrypoint_ref": worker_runtime["worker_entrypoint_snapshot_ref"],
        "python_flags": ["-I", "-S", "-B"],
        "working_directory": snapshot["root_storage"]["snapshot_path"],
        "environment": {
            "PATH": "",
            "LC_ALL": "C",
            "PYTHONDONTWRITEBYTECODE": "1",
        },
        "process_group_policy": ("worker_and_inner_runner_share_root_reaped_group/v1"),
    }
    if (
        broker_context.get("worker_launch") != expected_static_launch
        or statement["worker_launch_contract"] != expected_static_launch
    ):
        raise BrokerBoundaryError("u10_envelope_context_launch_mismatch", entry_id)
    if (
        broker_context.get("dependency_import_roots")
        != [item["locator"] for item in worker_runtime["dependency_import_roots"]]
        or broker_context.get("subject_source_root")
        != worker_runtime["subject_source_root"]["locator"]
    ):
        raise BrokerBoundaryError("u10_envelope_context_import_root_mismatch", entry_id)
    evidence_root = Path(str(broker_context["evidence_store_root"]))
    output_directory = Path(str(broker_context["output_directory"]))
    if (
        context_path.name != "broker-context.json"
        or evidence_root.name != "worker"
        or evidence_root.parent != context_path.parent
        or output_directory != evidence_root / "occurrence"
    ):
        raise BrokerBoundaryError("u10_envelope_context_spool_mismatch", entry_id)
    command = entry["commands"].get(command_id)
    if (
        not isinstance(command, Mapping)
        or statement["command_binding"]["command_id"] != command_id
        or statement["command_binding"]["command_definition_digest"]
        != command["command_definition_digest"]
        or statement["command_binding"]["closed_test_manifest_ref"]
        != command["snapshot_closed_test_manifest_ref"]
    ):
        raise BrokerBoundaryError("u10_envelope_command_context_mismatch", command_id)
    snapshot_ref = statement["snapshot_manifest_ref"]
    expected_snapshot = entry["snapshot_manifest_binding"]
    if (
        snapshot_ref["snapshot_id"] != expected_snapshot["snapshot_id"]
        or snapshot_ref["snapshot_version"] != expected_snapshot["snapshot_version"]
        or snapshot_ref["locator"] != expected_snapshot["locator"]
        or snapshot_ref["artifact_digest"] != expected_snapshot["artifact_digest"]
        or snapshot_ref["semantic_digest"] != expected_snapshot["manifest_digest"]
        or snapshot_ref["lifecycle_state"] != "active"
    ):
        raise BrokerBoundaryError("u10_envelope_snapshot_context_mismatch", entry_id)
    expected_statement_refs = (
        (
            statement["verification_profile_ref"],
            snapshot["verification_profile_ref"],
            "content_digest",
            ("profile_id", "profile_version"),
        ),
        (
            statement["environment_profile_ref"],
            snapshot["environment_profile_ref"],
            "basis_digest",
            ("environment_profile_id", "environment_profile_version"),
        ),
        (
            statement["eligibility_source_ref"],
            snapshot["eligibility_source_ref"],
            "source_digest",
            ("source_id", "source_version", "lifecycle_state"),
        ),
    )
    for (
        statement_ref,
        snapshot_value,
        semantic_field,
        identity_fields,
    ) in expected_statement_refs:
        snapshot_artifact_ref = snapshot_value["snapshot_artifact_ref"]
        expected = {
            **{name: snapshot_value[name] for name in identity_fields},
            "locator": snapshot_artifact_ref["locator"],
            "artifact_digest": snapshot_artifact_ref["artifact_digest"],
            semantic_field: snapshot_value[semantic_field],
        }
        if statement_ref != expected:
            raise BrokerBoundaryError(
                "u10_envelope_qualification_context_mismatch", semantic_field
            )
    nonce_ref = statement["nonce_consumption"]["nonce_record_ref"]
    expected_nonce_name = (
        hashlib.sha256(f"{entry_id}\0{request['request_nonce']}".encode()).hexdigest()
        + ".json"
    )
    if Path(str(nonce_ref["locator"])).name != expected_nonce_name:
        raise BrokerBoundaryError("u10_envelope_nonce_context_mismatch", entry_id)
    nonce_raw = read_protected_file(
        Path(str(nonce_ref["locator"])), protected_root=NONCE_LEDGER_ROOT
    )
    if nonce_ref["artifact_digest"] != digest_bytes(nonce_raw):
        raise BrokerBoundaryError("u10_envelope_nonce_artifact_mismatch", entry_id)
    nonce_record = _load_json_bytes(nonce_raw, "u10_nonce_record_unreadable")
    if (
        nonce_ref["semantic_digest"] != digest_bytes(canonical_json_bytes(nonce_record))
        or nonce_record.get("entry_id") != entry_id
        or nonce_record.get("command_id") != command_id
        or nonce_record.get("request_nonce") != request["request_nonce"]
        or nonce_record.get("recorded_at")
        != statement["nonce_consumption"]["recorded_at"]
        or nonce_record.get("state") != "consumed_before_launch"
    ):
        raise BrokerBoundaryError("u10_envelope_nonce_record_mismatch", entry_id)
    outcome_ref = statement["worker_outcome_ref"]
    if Path(str(outcome_ref["locator"])) != evidence_root / "worker-outcome.json":
        raise BrokerBoundaryError("u10_envelope_worker_outcome_path_mismatch", entry_id)
    outcome_raw = read_protected_file(
        Path(str(outcome_ref["locator"])), protected_root=EVIDENCE_SPOOL_ROOT
    )
    if outcome_ref["artifact_digest"] != digest_bytes(outcome_raw):
        raise BrokerBoundaryError(
            "u10_envelope_worker_outcome_artifact_mismatch", entry_id
        )
    outcome = _load_json_bytes(outcome_raw, "u10_worker_outcome_unreadable")
    worker_reported_observation = statement["worker_reported_observation"]
    broker_execution_observation = statement["broker_execution_observation"]
    observed_process = outcome.get("launch_observation")
    if (
        outcome_ref["semantic_digest"] != digest_bytes(canonical_json_bytes(outcome))
        or outcome_ref["run_id"] != outcome.get("run_id")
        or outcome.get("schema_version") != outcome_ref["schema_version"]
        or outcome.get("worker_version") != worker_runtime["worker_version"]
        or outcome.get("entry_id") != entry_id
        or outcome.get("command_id") != command_id
        or outcome.get("request_nonce") != request["request_nonce"]
        or outcome.get("worker_identity") != statement["worker_identity"]
        or outcome.get("execution_nonce") != statement["execution_nonce"]
        or outcome.get("started_at")
        != worker_reported_observation.get("interval", {}).get("started_at")
        or outcome.get("finished_at")
        != worker_reported_observation.get("interval", {}).get("finished_at")
        or outcome.get("formal_authority") != "none"
        or outcome.get("positive_assurance_allowed") is not False
        or outcome_ref["run_id"] != context_ref["run_id"]
        or broker_context.get("receipt_id") != statement["receipt_ref"]["receipt_id"]
        or not isinstance(observed_process, Mapping)
        or worker_reported_observation.get("process") != dict(observed_process)
    ):
        raise BrokerBoundaryError(
            "u10_envelope_worker_outcome_context_mismatch", entry_id
        )
    receipt_ref = statement["receipt_ref"]
    if Path(str(receipt_ref["locator"])) != output_directory / "receipt.json":
        raise BrokerBoundaryError("u10_envelope_receipt_path_mismatch", entry_id)
    receipt_raw = read_protected_file(
        Path(str(receipt_ref["locator"])), protected_root=EVIDENCE_SPOOL_ROOT
    )
    if receipt_ref["artifact_digest"] != digest_bytes(receipt_raw):
        raise BrokerBoundaryError("u10_envelope_receipt_artifact_mismatch", entry_id)
    receipt = _load_json_bytes(receipt_raw, "u10_envelope_receipt_unreadable")
    _validate(
        receipt,
        "governed-environment-execution-receipt-v1.schema.json",
        "u10_envelope_receipt_invalid",
    )
    receipt_material = dict(receipt)
    receipt_semantic = receipt_material.pop("receipt_digest", None)
    if (
        receipt_semantic != digest_bytes(canonical_json_bytes(receipt_material))
        or receipt_semantic != receipt_ref["semantic_digest"]
        or receipt.get("receipt_id") != receipt_ref["receipt_id"]
        or receipt.get("command_id") != command_id
        or receipt.get("execution_nonce") != statement["execution_nonce"]
        or receipt.get("execution_status") != outcome.get("execution_status")
        or outcome.get("receipt_locator") != receipt_ref["locator"]
        or outcome.get("receipt_artifact_digest") != receipt_ref["artifact_digest"]
        or outcome.get("receipt_semantic_digest") != receipt_ref["semantic_digest"]
        or receipt.get("formal_authority") != "none"
        or receipt.get("positive_assurance_allowed") is not False
    ):
        raise BrokerBoundaryError("u10_envelope_receipt_context_mismatch", entry_id)
    if (
        receipt.get("verification_profile_ref", {}).get("profile_id")
        != statement["verification_profile_ref"]["profile_id"]
        or receipt.get("verification_profile_ref", {}).get("profile_version")
        != statement["verification_profile_ref"]["profile_version"]
        or receipt.get("verification_profile_ref", {}).get("content_digest")
        != statement["verification_profile_ref"]["content_digest"]
        or receipt.get("environment_profile_ref", {}).get("environment_profile_id")
        != statement["environment_profile_ref"]["environment_profile_id"]
        or receipt.get("environment_profile_ref", {}).get("environment_profile_version")
        != statement["environment_profile_ref"]["environment_profile_version"]
        or receipt.get("environment_profile_ref", {}).get("basis_digest")
        != statement["environment_profile_ref"]["basis_digest"]
        or receipt.get("trust_source_ref", {}).get("source_id")
        != statement["eligibility_source_ref"]["source_id"]
        or receipt.get("trust_source_ref", {}).get("source_version")
        != statement["eligibility_source_ref"]["source_version"]
        or receipt.get("trust_source_ref", {}).get("source_digest")
        != statement["eligibility_source_ref"]["source_digest"]
        or receipt.get("subject_manifest_ref", {}).get("record_id")
        != statement["command_binding"]["closed_test_manifest_ref"]["manifest_id"]
        or receipt.get("subject_manifest_ref", {}).get("content_digest")
        != statement["command_binding"]["closed_test_manifest_ref"]["artifact_digest"]
    ):
        raise BrokerBoundaryError(
            "u10_envelope_receipt_qualification_mismatch", entry_id
        )
    if require_external_adoption:
        context_adoption = broker_context["environment_adoption"]
        expected_receipt_adoption_ref = {
            "adoption_id": context_adoption["adoption_id"],
            "adoption_version": context_adoption["adoption_version"],
            "adoption_digest": context_adoption["adoption_digest"],
        }
        if receipt.get("adoption_ref") != expected_receipt_adoption_ref:
            raise BrokerBoundaryError(
                "u10_envelope_receipt_adoption_mismatch", entry_id
            )
    _require_time_order(
        ("nonce_recorded_at", nonce_record["recorded_at"]),
        ("root_started_at", statement["started_at"]),
    )
    _validate_execution_observations_v2(
        worker_reported_observation=worker_reported_observation,
        broker_execution_observation=broker_execution_observation,
        receipt_started_at=receipt["started_at"],
        receipt_finished_at=receipt["finished_at"],
        started_at=statement["started_at"],
        finished_at=statement["finished_at"],
        attested_at=statement["attested_at"],
    )
    return {
        "signature_status": (
            "valid" if verify_signature else "not_checked_in_context_phase"
        ),
        "historical_store_state": store["lifecycle_state"],
        "historical_entry_state": store["entries"]
        .get(statement["trust_entry_ref"]["entry_id"], {})
        .get("entry_state", "unresolved"),
        "signed_context_status": "verified",
        "evidence_authority": "broker_observed_execution_occurrence_only",
        "formal_authority": "none",
        "positive_assurance_allowed": False,
        "u4_authority_status": "unresolved",
    }


def _verify_broker_attested_envelope_with_store_v3(
    envelope: Mapping[str, Any],
    *,
    store: Mapping[str, Any],
    store_raw: bytes | None = None,
    verify_signature: bool = True,
) -> dict[str, Any]:
    """Verify the v3 envelope with an explicit external-adoption chain."""

    authorization = _validate_store_activation_authorization_v1(store)
    _load_store_activation_basis_v2(authorization["store_activation_basis_ref"])

    return _verify_broker_attested_envelope_with_store_v2(
        envelope,
        store=store,
        store_raw=store_raw,
        verify_signature=verify_signature,
        envelope_schema_name=("broker-attested-execution-envelope-v3.schema.json"),
        signature_prefix=SIGNATURE_PREFIX_V3,
        require_external_adoption=True,
    )


def _verify_historical_signature_v2(
    envelope: Mapping[str, Any],
) -> tuple[dict[str, Any], bytes]:
    _validate(
        envelope,
        "broker-attested-execution-envelope-v2.schema.json",
        "u10_broker_envelope_invalid",
    )
    _sealed_digest(envelope, "envelope_digest", "u10_envelope_digest_mismatch")
    statement = envelope["signed_statement"]
    store, raw = load_historical_root_trust_store_v2(statement["trust_store_ref"])
    if statement["key_id"] != store["signing_key"]["key_id"]:
        raise BrokerBoundaryError("u10_envelope_key_id_mismatch", "key_id")
    try:
        public_raw = base64.b64decode(
            store["signing_key"]["public_key_base64"], validate=True
        )
        public_key = Ed25519PublicKey.from_public_bytes(public_raw)
        signature = base64.b64decode(envelope["signature"]["value"], validate=True)
        _verify_statement_signature(statement, signature, public_key)
    except (ValueError, BrokerBoundaryError) as exc:
        raise BrokerBoundaryError("u10_envelope_signature_invalid", "ed25519") from exc
    return store, raw


def _verify_historical_signature_v3(
    envelope: Mapping[str, Any],
) -> tuple[dict[str, Any], bytes]:
    _validate(
        envelope,
        "broker-attested-execution-envelope-v3.schema.json",
        "u10_broker_envelope_invalid",
    )
    _sealed_digest(envelope, "envelope_digest", "u10_envelope_digest_mismatch")
    statement = envelope["signed_statement"]
    store, raw = load_historical_root_trust_store_v2(statement["trust_store_ref"])
    if statement["key_id"] != store["signing_key"]["key_id"]:
        raise BrokerBoundaryError("u10_envelope_key_id_mismatch", "key_id")
    try:
        public_raw = base64.b64decode(
            store["signing_key"]["public_key_base64"], validate=True
        )
        public_key = Ed25519PublicKey.from_public_bytes(public_raw)
        signature = base64.b64decode(envelope["signature"]["value"], validate=True)
        _verify_statement_signature(
            statement,
            signature,
            public_key,
            signature_prefix=SIGNATURE_PREFIX_V3,
        )
    except (ValueError, BrokerBoundaryError) as exc:
        raise BrokerBoundaryError("u10_envelope_signature_invalid", "ed25519") from exc
    return store, raw


def _assess_current_currency_v2(
    statement: Mapping[str, Any],
    historical_store: Mapping[str, Any],
) -> dict[str, Any]:
    observed_at = _utc_now()
    entry_id = str(statement["trust_entry_ref"]["entry_id"])
    try:
        current, raw = load_fixed_root_trust_store_record_v2()
    except BrokerBoundaryError as exc:
        return {
            "status": "unresolved",
            "observed_at": observed_at,
            "current_store_ref": None,
            "current_entry_state": "unresolved",
            "current_key_state": "unresolved",
            "reason_codes": [exc.code],
        }
    current_entry = current["entries"].get(entry_id)
    current_entry_state = (
        current_entry.get("entry_state", "unresolved")
        if isinstance(current_entry, Mapping)
        else "unresolved"
    )
    current_ref = {
        "store_id": current["store_id"],
        "store_revision_id": current["store_revision_id"],
        "store_version": current["store_version"],
        "lifecycle_state": current["lifecycle_state"],
        "artifact_digest": digest_bytes(raw),
        "semantic_digest": current["store_digest"],
    }
    historical_key_id = str(historical_store["signing_key"]["key_id"])
    current_key = current["signing_key"]
    current_governance_error: BrokerBoundaryError | None = None
    current_revocation: tuple[dict[str, Any], bytes] | None = None
    if current["lifecycle_state"] == "active":
        try:
            _verify_current_selector_contract_v1(current)
            _load_complete_store_activation_chain_v1(current, raw)
            current_history, current_history_raw = load_historical_root_trust_store_v2(
                derive_historical_store_ref_v2(current, raw)
            )
            if current_history != current or current_history_raw != raw:
                raise BrokerBoundaryError(
                    "u10_current_history_mismatch",
                    str(current["store_revision_id"]),
                )
            current_revocation = load_current_store_revocation_v1(current, raw)
        except BrokerBoundaryError as exc:
            current_governance_error = exc
    else:
        current_governance_error = BrokerBoundaryError(
            "u10_current_store_not_governed", current["lifecycle_state"]
        )
    exact_revocation_target = (
        current_revocation is not None
        and current["store_id"] == historical_store["store_id"]
        and current["store_revision_id"] == historical_store["store_revision_id"]
        and current["store_version"] == historical_store["store_version"]
        and current["store_activation_basis_digest"]
        == historical_store["store_activation_basis_digest"]
        and current["store_digest"] == historical_store["store_digest"]
        and digest_bytes(raw) == statement["trust_store_ref"]["artifact_digest"]
        and current_entry_state == "active"
        and current_key["key_id"] == historical_key_id
        and current_key["key_state"] == "active"
    )
    if current_governance_error is not None:
        status = "unresolved"
        reasons = [current_governance_error.code]
    elif exact_revocation_target:
        status = "revoked"
        reasons = ["historical_authority_currently_revoked"]
    elif current_revocation is not None:
        status = "unresolved"
        reasons = ["different_current_store_is_locally_revoked"]
    elif (
        current["store_id"] == historical_store["store_id"]
        and current["store_revision_id"] == historical_store["store_revision_id"]
        and current["store_version"] == historical_store["store_version"]
        and current["store_digest"] == historical_store["store_digest"]
        and digest_bytes(raw) == statement["trust_store_ref"]["artifact_digest"]
        and current["lifecycle_state"] == "active"
        and current_entry_state == "active"
        and current_key["key_state"] == "active"
    ):
        status = "current"
        reasons = []
    elif (
        current["store_id"] == historical_store["store_id"]
        and current["store_revision_id"] == historical_store["store_revision_id"]
        and current["store_version"] == historical_store["store_version"]
    ):
        status = "unresolved"
        reasons = ["same_store_identity_with_different_content"]
    elif current["store_id"] == historical_store["store_id"]:
        status = "superseded"
        reasons = ["newer_or_different_store_revision_requires_requalification"]
    else:
        status = "unresolved"
        reasons = ["different_current_trust_root"]
    return {
        "status": status,
        "observed_at": observed_at,
        "current_store_ref": current_ref,
        "current_entry_state": current_entry_state,
        "current_key_state": current_key["key_state"],
        "reason_codes": reasons,
    }


def _assess_current_currency_v3(
    statement: Mapping[str, Any],
    historical_store: Mapping[str, Any],
) -> dict[str, Any]:
    """Add live v2 key-head currency without changing historical authenticity."""

    with trust_store_coordination_lock(exclusive=False):
        result = _assess_current_currency_v2(statement, historical_store)
        if result["status"] in {"revoked", "unresolved"}:
            return result
        try:
            authorization = _validate_store_activation_authorization_v1(
                historical_store
            )
            historical_basis, _basis_raw = _load_store_activation_basis_v2(
                authorization["store_activation_basis_ref"]
            )
            historical_head = historical_basis["signing_key_selector_ref"]
            replay = resolve_current_signing_key_chain_v2_under_trust_store_lock()
        except BrokerBoundaryError as exc:
            return {
                **result,
                "status": "unresolved",
                "current_key_state": "unresolved",
                "reason_codes": [exc.code],
            }
        current_head = replay.get("current_selector_ref")
        if current_head == historical_head:
            return result
        sequence = replay.get("transition_sequence")
        if not isinstance(sequence, list):
            return {
                **result,
                "status": "unresolved",
                "current_key_state": "unresolved",
                "reason_codes": ["u10_key_chain_replay_result_invalid"],
            }
        matching_indexes = [
            index
            for index, item in enumerate(sequence)
            if isinstance(item, Mapping) and item.get("selector_ref") == historical_head
        ]
        if len(matching_indexes) != 1:
            return {
                **result,
                "status": "unresolved",
                "current_key_state": "unresolved",
                "reason_codes": ["historical_key_selector_not_in_live_chain"],
            }
        successors = sequence[matching_indexes[0] + 1 :]
        if not successors:
            return {
                **result,
                "status": "unresolved",
                "current_key_state": "unresolved",
                "reason_codes": ["live_key_head_relation_inconsistent"],
            }
        first = successors[0]
        transition_mode = first.get("transition_mode")
        historical_key_id = historical_store["signing_key"]["key_id"]
        revocation_ref = first.get("revocation_ref")
        if (
            transition_mode == "revoke_active_key"
            and isinstance(revocation_ref, Mapping)
            and revocation_ref.get("key_id") == historical_key_id
        ):
            key_status = "revoked"
            key_state = "revoked"
            reason = "historical_signing_key_revoked_by_live_chain"
        elif transition_mode in {
            "rotate_active_key",
            "generate_from_no_active_key",
        }:
            key_status = "superseded"
            key_state = "superseded"
            reason = "historical_signing_key_superseded_by_live_chain"
        else:
            key_status = "unresolved"
            key_state = "unresolved"
            reason = "historical_key_successor_relation_invalid"
        if result["status"] == "superseded" and key_status == "revoked":
            # A direct key revocation is the more specific present-currency
            # reason; neither status changes historical signature validity.
            pass
        elif result["status"] == "superseded":
            key_status = "superseded"
            reason = "newer_or_different_store_revision_requires_requalification"
        return {
            **result,
            "status": key_status,
            "current_key_state": key_state,
            "reason_codes": [reason],
        }


def verify_broker_attested_envelope_v2(
    envelope: Mapping[str, Any],
) -> dict[str, Any]:
    """Separate historical occurrence authenticity from present currency."""

    store, raw = _verify_historical_signature_v2(envelope)
    context_error: BrokerBoundaryError | None = None
    try:
        context_result = _verify_broker_attested_envelope_with_store_v2(
            envelope,
            store=store,
            store_raw=raw,
            verify_signature=False,
        )
    except BrokerBoundaryError as exc:
        context_error = exc
        context_result = None
    if context_error is None:
        context_result["signature_status"] = "valid_preverified"
        authenticity_status = "verified"
        signed_context_status = "verified"
        reason_codes: list[str] = []
    else:
        unresolved_evidence_codes = {
            "protected_file_unavailable",
            "protected_directory_unavailable",
            "broker_schema_directory_unavailable",
            "broker_schema_unavailable",
        }
        signed_context_status = (
            "unresolved_evidence"
            if context_error.code in unresolved_evidence_codes
            else "invalid"
        )
        authenticity_status = f"signature_valid_context_{signed_context_status}"
        reason_codes = [context_error.code]
    return {
        "schema_version": "semantic-guard-u10-envelope-verification-result/v2",
        "historical_authenticity": {
            "status": authenticity_status,
            "signature_status": "valid",
            "historical_store_artifact_status": "exact",
            "signed_context_status": signed_context_status,
            "historical_store_ref": dict(
                envelope["signed_statement"]["trust_store_ref"]
            ),
            "reason_codes": reason_codes,
        },
        "current_currency": _assess_current_currency_v2(
            envelope["signed_statement"], store
        ),
        "authority_ceiling": {
            "evidence_authority": "broker_observed_execution_occurrence_only",
            "formal_authority": "none",
            "positive_assurance_allowed": False,
            "u4_authority_status": "unresolved",
        },
        "signed_context": context_result,
    }


def verify_broker_attested_envelope_v3(
    envelope: Mapping[str, Any],
) -> dict[str, Any]:
    """Verify v3 while separating occurrence authenticity from currency."""

    store, raw = _verify_historical_signature_v3(envelope)
    context_error: BrokerBoundaryError | None = None
    try:
        context_result = _verify_broker_attested_envelope_with_store_v3(
            envelope,
            store=store,
            store_raw=raw,
            verify_signature=False,
        )
    except BrokerBoundaryError as exc:
        context_error = exc
        context_result = None
    if context_error is None:
        context_result["signature_status"] = "valid_preverified"
        authenticity_status = "verified"
        signed_context_status = "verified"
        reason_codes: list[str] = []
    else:
        unresolved_evidence_codes = {
            "protected_file_unavailable",
            "protected_directory_unavailable",
            "broker_schema_directory_unavailable",
            "broker_schema_unavailable",
        }
        signed_context_status = (
            "unresolved_evidence"
            if context_error.code in unresolved_evidence_codes
            else "invalid"
        )
        authenticity_status = f"signature_valid_context_{signed_context_status}"
        reason_codes = [context_error.code]
    return {
        "schema_version": "semantic-guard-u10-envelope-verification-result/v3",
        "historical_authenticity": {
            "status": authenticity_status,
            "signature_status": "valid",
            "historical_store_artifact_status": "exact",
            "signed_context_status": signed_context_status,
            "historical_store_ref": dict(
                envelope["signed_statement"]["trust_store_ref"]
            ),
            "reason_codes": reason_codes,
        },
        "current_currency": _assess_current_currency_v3(
            envelope["signed_statement"], store
        ),
        "authority_ceiling": {
            "evidence_authority": "broker_observed_execution_occurrence_only",
            "formal_authority": "none",
            "positive_assurance_allowed": False,
            "u4_authority_status": "unresolved",
        },
        "signed_context": context_result,
    }


def build_statement_skeleton_v2(
    *,
    context: Mapping[str, Any],
    envelope_id: str,
    execution_nonce: str,
    worker_launch_contract: Mapping[str, Any],
    worker_reported_observation: Mapping[str, Any],
    broker_execution_observation: Mapping[str, Any],
    broker_context_ref: Mapping[str, Any],
    worker_outcome_ref: Mapping[str, Any],
    receipt_ref: Mapping[str, Any],
    receipt_interval: Mapping[str, Any],
    started_at: str,
    finished_at: str,
) -> dict[str, Any]:
    """Build the closed statement projection after a worker receipt is frozen."""

    store = context["store"]
    entry = context["entry"]
    snapshot = context["snapshot"]
    nonce_path = Path(str(context["nonce_record_path"]))
    nonce_raw = read_protected_file(nonce_path, protected_root=NONCE_LEDGER_ROOT)
    command_id = str(context["request"]["command_id"])
    snapshot_command = context["snapshot_command"]
    closed_ref = snapshot_command["closed_test_manifest_ref"]
    phase_budget = resolve_worker_phase_budget_v1(snapshot, command_id)
    attested_at = _utc_now()
    value = {
        "statement_schema_version": "semantic-guard-u10-broker-signed-statement/v2",
        "envelope_id": envelope_id,
        "key_id": store["signing_key"]["key_id"],
        "signature_domain": "semantic-guard.u10.broker-execution-attestation/v2",
        "canonicalization_profile": "semantic-guard-canonical-json/v1",
        "broker": {
            "broker_id": BROKER_ID,
            "broker_version": store["broker_runtime_version"],
            "runtime_ref": store["broker_runtime_ref"],
        },
        "trust_store_ref": dict(context["store_history_ref"]),
        "trust_entry_ref": {
            "store_id": store["store_id"],
            "store_revision_id": store["store_revision_id"],
            "store_version": store["store_version"],
            "entry_id": context["request"]["entry_id"],
            "entry_state": "active",
            "entry_digest": entry["entry_digest"],
        },
        "request": dict(context["request"]),
        "nonce_consumption": {
            "ledger_root": str(NONCE_LEDGER_ROOT),
            "nonce_record_ref": {
                "record_id": f"nonce.{context['request']['request_nonce']}",
                "locator": str(nonce_path),
                "artifact_digest": digest_bytes(nonce_raw),
                "semantic_digest": digest_bytes(
                    canonical_json_bytes(context["nonce_record"])
                ),
            },
            "recorded_at": context["nonce_record"]["recorded_at"],
            "replay_check": "record_absent_then_o_excl_created_before_launch",
        },
        "snapshot_manifest_ref": {
            "snapshot_id": snapshot["snapshot_id"],
            "snapshot_version": snapshot["snapshot_version"],
            "lifecycle_state": "active",
            "locator": entry["snapshot_manifest_binding"]["locator"],
            "artifact_digest": entry["snapshot_manifest_binding"]["artifact_digest"],
            "semantic_digest": snapshot["manifest_digest"],
        },
        "preactivation_boundary_binding": _strict_json_clone(
            snapshot["preactivation_boundary_binding"]
        ),
        "worker_identity": {
            "uid": snapshot["worker_identity"]["uid"],
            "gid": snapshot["worker_identity"]["gid"],
            "supplementary_gids": snapshot["worker_identity"][
                "effective_supplementary_gids"
            ],
            "umask": snapshot["worker_identity"]["umask"],
        },
        "worker_launch_contract": dict(worker_launch_contract),
        "worker_reported_observation": _strict_json_clone(worker_reported_observation),
        "broker_execution_observation": _strict_json_clone(
            broker_execution_observation
        ),
        "command_binding": {
            "command_id": command_id,
            "command_definition_digest": snapshot_command["command_definition_digest"],
            "closed_test_manifest_ref": {
                "manifest_id": closed_ref["manifest_id"],
                "manifest_version": closed_ref["manifest_version"],
                "locator": closed_ref["snapshot_artifact_ref"]["locator"],
                "artifact_digest": closed_ref["snapshot_artifact_ref"][
                    "artifact_digest"
                ],
                "manifest_digest": closed_ref["manifest_digest"],
            },
        },
        "verification_profile_ref": {
            "profile_id": snapshot["verification_profile_ref"]["profile_id"],
            "profile_version": snapshot["verification_profile_ref"]["profile_version"],
            "locator": snapshot["verification_profile_ref"]["snapshot_artifact_ref"][
                "locator"
            ],
            "artifact_digest": snapshot["verification_profile_ref"][
                "snapshot_artifact_ref"
            ]["artifact_digest"],
            "content_digest": snapshot["verification_profile_ref"]["content_digest"],
        },
        "environment_profile_ref": {
            "environment_profile_id": snapshot["environment_profile_ref"][
                "environment_profile_id"
            ],
            "environment_profile_version": snapshot["environment_profile_ref"][
                "environment_profile_version"
            ],
            "locator": snapshot["environment_profile_ref"]["snapshot_artifact_ref"][
                "locator"
            ],
            "artifact_digest": snapshot["environment_profile_ref"][
                "snapshot_artifact_ref"
            ]["artifact_digest"],
            "basis_digest": snapshot["environment_profile_ref"]["basis_digest"],
        },
        "eligibility_source_ref": {
            "source_id": snapshot["eligibility_source_ref"]["source_id"],
            "source_version": snapshot["eligibility_source_ref"]["source_version"],
            "lifecycle_state": "adopted",
            "locator": snapshot["eligibility_source_ref"]["snapshot_artifact_ref"][
                "locator"
            ],
            "artifact_digest": snapshot["eligibility_source_ref"][
                "snapshot_artifact_ref"
            ]["artifact_digest"],
            "source_digest": snapshot["eligibility_source_ref"]["source_digest"],
        },
        "execution_nonce": execution_nonce,
        "broker_context_ref": bind_broker_context_phase_budget_v1(
            broker_context_ref, phase_budget
        ),
        "worker_outcome_ref": dict(worker_outcome_ref),
        "receipt_ref": dict(receipt_ref),
        "started_at": started_at,
        "finished_at": finished_at,
        "attested_at": attested_at,
        "authority_ceiling": {
            "evidence_authority": "broker_observed_execution_occurrence_only",
            "formal_authority": "none",
            "positive_assurance_allowed": False,
            "human_decision_authority": "none",
            "engineering_correctness_authority": "none",
            "u4_authority_status": "unresolved",
        },
    }
    if set(receipt_interval) != {"started_at", "finished_at"}:
        raise BrokerBoundaryError(
            "u10_execution_receipt_interval_invalid", repr(receipt_interval)
        )
    _validate_execution_observations_v2(
        worker_reported_observation=value["worker_reported_observation"],
        broker_execution_observation=value["broker_execution_observation"],
        receipt_started_at=receipt_interval["started_at"],
        receipt_finished_at=receipt_interval["finished_at"],
        started_at=started_at,
        finished_at=finished_at,
        attested_at=attested_at,
    )
    return value


def build_statement_skeleton_v3(
    *,
    context: Mapping[str, Any],
    envelope_id: str,
    execution_nonce: str,
    worker_launch_contract: Mapping[str, Any],
    worker_reported_observation: Mapping[str, Any],
    broker_execution_observation: Mapping[str, Any],
    broker_context_ref: Mapping[str, Any],
    worker_outcome_ref: Mapping[str, Any],
    receipt_ref: Mapping[str, Any],
    receipt_interval: Mapping[str, Any],
    started_at: str,
    finished_at: str,
) -> dict[str, Any]:
    """Build a statement that preserves candidate source and exact adoption."""

    value = build_statement_skeleton_v2(
        context=context,
        envelope_id=envelope_id,
        execution_nonce=execution_nonce,
        worker_launch_contract=worker_launch_contract,
        worker_reported_observation=worker_reported_observation,
        broker_execution_observation=broker_execution_observation,
        broker_context_ref=broker_context_ref,
        worker_outcome_ref=worker_outcome_ref,
        receipt_ref=receipt_ref,
        receipt_interval=receipt_interval,
        started_at=started_at,
        finished_at=finished_at,
    )
    snapshot = context["snapshot"]
    adoption_ref = context.get("environment_adoption_ref")
    if (
        not isinstance(adoption_ref, Mapping)
        or adoption_ref != snapshot.get("environment_adoption_ref")
        or snapshot["eligibility_source_ref"]["lifecycle_state"] != "candidate"
    ):
        raise BrokerBoundaryError(
            "u10_statement_environment_adoption_mismatch",
            str(context["request"]["entry_id"]),
        )
    value["statement_schema_version"] = "semantic-guard-u10-broker-signed-statement/v3"
    value["signature_domain"] = "semantic-guard.u10.broker-execution-attestation/v3"
    value["eligibility_source_ref"]["lifecycle_state"] = "candidate"
    value["environment_adoption_ref"] = dict(adoption_ref)
    return value
