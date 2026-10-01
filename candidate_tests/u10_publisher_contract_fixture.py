from __future__ import annotations

import copy
import hashlib
import json


def _digest(label: str) -> dict[str, str]:
    return {
        "algorithm": "sha256",
        "value": hashlib.sha256(label.encode("utf-8")).hexdigest(),
    }


def publisher_contract_binding() -> dict:
    bootstrap = "/Library/Application Support/semantic-guard/u10/bootstrap"
    artifacts = {
        "broker_outer_launcher": f"{bootstrap}/u10_root_broker_outer_launcher.py",
        "initial_trust_provisioner": f"{bootstrap}/u10_initial_trust_provisioner.py",
        "root_control_dispatcher": f"{bootstrap}/u10_root_control_dispatcher.py",
        "root_control_entrypoint": f"{bootstrap}/u10_root_control_entrypoint.sh",
        "root_control_outer_launcher": f"{bootstrap}/u10_root_control_outer_launcher.py",
        "snapshot_store_producer": f"{bootstrap}/u10_snapshot_store_production.py",
    }
    value = {
        "schema_version": (
            "semantic-guard-u10-control-publisher-contract-binding/v1"
        ),
        "contract_id": "semantic-guard.u10.fixed-root-control-publisher.v1",
        "launch_profile": (
            "fixed-root-wrapper-broker-outer-control-runtime-dispatcher/v1"
        ),
        "public_argument_denominator": ["operation", "identifier"],
        "allowed_operations": [
            "activate-snapshot",
            "activate-store",
            "key",
            "project-snapshot",
            "revoke-store",
        ],
        "caller_supplied_paths_allowed": False,
        "caller_supplied_raw_payloads_allowed": False,
        "caller_supplied_inline_authority_allowed": False,
        "caller_environment_injection_allowed": False,
        "artifacts": {
            name: {"locator": locator, "artifact_digest": _digest(name)}
            for name, locator in sorted(artifacts.items())
        },
        "broker_runtime_ref": {
            "effective_python_path": f"{bootstrap}/effective-python.path",
            "effective_python_path_artifact_digest": _digest("broker-path"),
            "runtime_manifest_locator": (
                f"{bootstrap}/effective-python-runtime-manifest.json"
            ),
            "runtime_manifest_artifact_digest": _digest("broker-manifest-raw"),
            "runtime_manifest_digest": _digest("broker-manifest"),
            "runtime_tree_digest": _digest("broker-tree"),
        },
        "control_runtime_ref": {
            "effective_python_path": f"{bootstrap}/control-effective-python.path",
            "effective_python_path_artifact_digest": _digest("control-path"),
            "runtime_manifest_locator": (
                f"{bootstrap}/control-python-runtime-manifest.json"
            ),
            "runtime_manifest_artifact_digest": _digest("control-manifest-raw"),
            "runtime_manifest_digest": _digest("control-manifest"),
            "runtime_tree_digest": _digest("control-tree"),
            "broker_package_binding": {
                "package_root": "/opt/semantic-guard-u10-control/semantic_guard_u10_broker",
                "entry_count": 4,
                "tree_digest": _digest("broker-package"),
            },
        },
        "bootstrap_provenance_ref": {
            "locator": (
                f"{bootstrap}/initial-bootstrap-provenance-binding.json"
            ),
            "binding_id": "binding.bootstrap.u10.fixture",
            "binding_artifact_digest": _digest("binding-raw"),
            "binding_digest": _digest("binding"),
            "authorization_id": "authorization.bootstrap.u10.fixture",
            "plan_id": "plan.bootstrap.u10.fixture",
            "chain_artifact_digests": {
                name: _digest(f"chain:{name}")
                for name in ("authorization", "plan", "consumption", "receipt")
            },
        },
        "formal_authority": "none",
        "positive_assurance_allowed": False,
    }
    material = copy.deepcopy(value)
    value["binding_digest"] = {
        "algorithm": "sha256",
        "value": hashlib.sha256(
            json.dumps(
                material,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest(),
    }
    return value
