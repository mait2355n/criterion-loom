from __future__ import annotations

import base64
import copy
import json
from pathlib import Path
import stat
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from jsonschema import Draft202012Validator, FormatChecker

import semantic_guard_u10_broker.core as core
from semantic_guard_u10_broker.protected_io import BrokerBoundaryError


SCHEMA_DIRECTORY = (
    Path(__file__).parents[1] / "src" / "semantic_guard_vnext" / "validation" / "env-path-contracts"
)
ENTRY_ID = "entry.u10.history-test"
COMMAND_ID = "verify.u10.history-test"


def _digest(label: str) -> dict[str, str]:
    return core.digest_bytes(label.encode("utf-8"))


def _sealed(value: dict, field: str) -> dict:
    result = copy.deepcopy(value)
    material = copy.deepcopy(result)
    material.pop(field, None)
    result[field] = core.digest_bytes(core.canonical_json_bytes(material))
    return result


def _root_artifact(record_id: str, name: str) -> dict:
    return {
        "record_id": record_id,
        "locator": (
            "/Library/Application Support/semantic-guard/u10/"
            f"snapshots/snapshot.u10.history/{name}"
        ),
        "artifact_digest": _digest(f"artifact:{record_id}"),
        "semantic_digest": _digest(f"semantic:{record_id}"),
        "owner_uid": 0,
        "owner_gid": 0,
        "write_protection": "not_group_or_world_writable",
    }


def _fixed_root_artifact(record_id: str, locator: str) -> dict:
    return {
        "record_id": record_id,
        "locator": locator,
        "artifact_digest": _digest(f"artifact:{record_id}"),
        "semantic_digest": _digest(f"semantic:{record_id}"),
        "owner_uid": 0,
        "owner_gid": 0,
        "write_protection": "not_group_or_world_writable",
    }


def _plain_root_artifact(record_id: str, locator: str) -> dict:
    return {
        "record_id": record_id,
        "locator": locator,
        "artifact_digest": _digest(f"artifact:{record_id}"),
        "semantic_digest": _digest(f"semantic:{record_id}"),
    }


def _host_runtime_ref(
    logical_id: str, locator: str, resolved_locator: str
) -> dict:
    return {
        "logical_id": logical_id,
        "locator": locator,
        "resolved_locator": resolved_locator,
        "artifact_digest": _digest(f"host-runtime:{logical_id}"),
        "owner_uid": 0,
        "write_protection": (
            "absolute_ancestor_chain_not_group_or_world_writable"
        ),
    }


def _preactivation_boundary(snapshot_root: str) -> dict:
    candidate_hash = _digest("candidate-bundle-id")["value"]
    candidate_id = f"candidate.u10.{candidate_hash}"

    def snapshot_ref(record_id: str, name: str, label: str) -> dict:
        return {
            "record_id": record_id,
            "locator": f"{snapshot_root}/governance/{name}",
            "artifact_digest": _digest(f"artifact:{label}"),
            "semantic_digest": _digest(f"semantic:{label}"),
        }

    decision_ref = {
        "record_id": "decision.u10.history-test",
        "source_locator": "/Users/test/u10-decision.json",
        "source_artifact_digest": _digest("artifact:decision"),
        "candidate_relative_locator": "vnext/governance/u10-decision.json",
        "candidate_artifact_digest": _digest("artifact:decision"),
        "semantic_digest": _digest("semantic:decision"),
        "snapshot_artifact_ref": snapshot_ref(
            "decision.u10.history-test", "u10-decision.json", "decision"
        ),
    }
    resolution_ref = {
        "record_id": "resolution.u10.history-test",
        "source_locator": "/Users/test/u10-principal-resolution.json",
        "source_artifact_digest": _digest("artifact:resolution"),
        "candidate_relative_locator": (
            "vnext/governance/u10-principal-resolution.json"
        ),
        "candidate_artifact_digest": _digest("artifact:resolution"),
        "semantic_digest": _digest("semantic:resolution"),
        "snapshot_artifact_ref": snapshot_ref(
            "resolution.u10.history-test",
            "u10-principal-resolution.json",
            "resolution",
        ),
    }
    observation_ref = {
        "record_id": "observation.u10.history-test",
        "source_locator": "/Users/test/u10-account-observation.json",
        "source_artifact_digest": _digest("artifact:observation"),
        "candidate_relative_locator": (
            "vnext/governance/u10-account-observation.json"
        ),
        "candidate_artifact_digest": _digest("artifact:observation"),
        "semantic_digest": _digest("semantic:observation"),
        "snapshot_artifact_ref": snapshot_ref(
            "observation.u10.history-test",
            "u10-account-observation.json",
            "observation",
        ),
    }
    candidate_snapshot_ref = snapshot_ref(
        candidate_id, "u10-candidate-bundle-manifest.json", "candidate"
    )
    return {
        "profile": "u10-local-bounded-preactivation-binding/v1",
        "candidate_bundle_ref": {
            "bundle_id": candidate_id,
            "bundle_version": "2.0.0-candidate",
            "candidate_locator": (
                "/Library/Application Support/semantic-guard/u10/candidates/"
                f"{candidate_id}/bundle-manifest.json"
            ),
            "artifact_digest": candidate_snapshot_ref["artifact_digest"],
            "bundle_digest": candidate_snapshot_ref["semantic_digest"],
            "snapshot_artifact_ref": candidate_snapshot_ref,
        },
        "boundary_binding_digest": _digest("boundary"),
        "decision_record_ref": decision_ref,
        "worker_account_observation_ref": observation_ref,
        "worker_principal_resolution_ref": resolution_ref,
        "subject_entity_id": "acfb8b85-2f75-5e82-a641-b3b3b6e023d6",
        "worker_principal_entity_id": (
            "22222222-2222-4222-8222-222222222222"
        ),
        "threat_boundary": "local_bounded_repository_suite_only",
        "worker_identity_policy": (
            "current_user_501_20_empty_supplementary_groups"
        ),
        "qualification_scope": (
            "repository_owned_closed_verification_suite_only"
        ),
        "hostile_code_assurance": (
            "prohibited_requires_separate_external_executor_profile"
        ),
        "requalification_triggers": [
            "threat_boundary_change",
            "worker_identity_policy_change",
            "principal_resolution_change",
            "host_or_os_change",
            "sandbox_or_external_executor_change",
            "qualified_test_denominator_change",
        ],
        "effective_worker_identity": {
            "uid": 501,
            "gid": 20,
            "effective_supplementary_gids": [],
            "umask": 63,
        },
    }


def _active_store(public_key_base64: str) -> dict:
    snapshot_root = (
        "/Library/Application Support/semantic-guard/u10/"
        "snapshots/snapshot.u10.history"
    )
    closed_repository_ref = {
        "manifest_id": "manifest.u10.history-test",
        "manifest_version": "1.0.0",
        "locator": "validation/closed-test-manifest.json",
        "artifact_digest": _digest("closed-repository-artifact"),
        "manifest_digest": _digest("closed-manifest-semantic"),
    }
    closed_snapshot_ref = {
        **closed_repository_ref,
        "locator": f"{snapshot_root}/closed-test-manifest.json",
    }
    entry = {
        "entry_state": "active",
        "repository_binding": {
            "canonical_path": "/Users/test/semantic-guard",
            "device_id": 1,
            "inode": 2,
        },
        "snapshot_manifest_binding": {
            "snapshot_id": "snapshot.u10.history-test",
            "snapshot_version": "1.0.0",
            "lifecycle_state": "active",
            "locator": f"{snapshot_root}/u10-execution-snapshot-manifest-v1.json",
            "artifact_digest": _digest("snapshot-manifest-artifact"),
            "manifest_digest": _digest("snapshot-manifest-semantic"),
        },
        "preactivation_boundary_binding": _preactivation_boundary(
            snapshot_root
        ),
        "eligibility_source_binding": {
            "source_id": "source.u10.history-test",
            "source_version": "1.0.0",
            "lifecycle_state": "candidate",
            "locator": "validation/eligibility-source.json",
            "artifact_digest": _digest("source-artifact"),
            "source_digest": _digest("source-semantic"),
        },
        "verification_profile_binding": {
            "profile_id": "profile.u10.history-test",
            "profile_version": "1.0.0",
            "locator": "validation/verification-profile.json",
            "artifact_digest": _digest("profile-artifact"),
            "content_digest": _digest("profile-semantic"),
        },
        "environment_profile_binding": {
            "environment_profile_id": "environment.u10.history-test",
            "environment_profile_version": "1.0.0",
            "locator": "validation/environment-profile.json",
            "artifact_digest": _digest("environment-artifact"),
            "basis_digest": _digest("environment-semantic"),
        },
        "environment_adoption_binding": _plain_root_artifact(
            "adoption.environment.u10.history-test",
            "/Library/Application Support/semantic-guard/u10/"
            "authorizations/adoption.environment.u10.history-test.json",
        ),
        "commands": {
            COMMAND_ID: {
                "command_definition_digest": _digest("command-definition"),
                "closed_test_manifest_binding": closed_repository_ref,
                "snapshot_closed_test_manifest_ref": closed_snapshot_ref,
            }
        },
        "execution_uid": 501,
        "execution_gid": 20,
        "execution_supplementary_gids": [],
        "execution_umask": 63,
        "granted_capability": "verification_process_launch",
        "formal_authority": "none",
        "positive_assurance_allowed": False,
    }
    entry = _sealed(entry, "entry_digest")
    store = {
        "schema_version": "semantic-guard-u10-root-trust-store/v2",
        "store_id": "store.u10.history-test",
        "store_revision_id": "revision.u10.history-test.1",
        "store_version": "2.0.0",
        "store_activation_basis_digest": _digest("pending-store-basis"),
        "activation_authorization_ref": _root_artifact(
            "authorization.revision.u10.history-test.1",
            "authorizations/authorization.revision.u10.history-test.1.json",
        ),
        "lifecycle_state": "active",
        "broker_runtime_version": core.BROKER_VERSION,
        "broker_entrypoint_ref": _fixed_root_artifact(
            "broker.entrypoint.u10.history-test",
            "/Library/Application Support/semantic-guard/u10/bootstrap/"
            "u10_root_broker_entrypoint.sh",
        ),
        "broker_outer_launcher_ref": _fixed_root_artifact(
            "broker.outer-launcher.u10.history-test",
            "/Library/Application Support/semantic-guard/u10/bootstrap/"
            "u10_root_broker_outer_launcher.py",
        ),
        "broker_launch_platform": {
            "profile": "darwin-root-wrapper-qualified-effective-python/v2",
            "shell_ref": _host_runtime_ref(
                "shell.system", "/bin/sh", "/bin/sh"
            ),
            "shell_flags": ["-p"],
            "environment_cleaner_ref": _host_runtime_ref(
                "env.system", "/usr/bin/env", "/usr/bin/env"
            ),
            "effective_python_ref": _host_runtime_ref(
                "python.effective.system",
                "/Library/Developer/CommandLineTools/Library/Frameworks/"
                "Python3.framework/Versions/3.9/bin/python3.9",
                "/Library/Developer/CommandLineTools/Library/Frameworks/"
                "Python3.framework/Versions/3.9/bin/python3.9",
            ),
            "effective_python_path_ref": _fixed_root_artifact(
                "python.effective-path.u10.history-test",
                "/Library/Application Support/semantic-guard/u10/bootstrap/"
                "effective-python.path",
            ),
            "effective_runtime_manifest_ref": _fixed_root_artifact(
                "python.effective-runtime.u10.history-test",
                "/Library/Application Support/semantic-guard/u10/bootstrap/"
                "effective-python-runtime-manifest.json",
            ),
            "environment_policy": (
                "privileged_sh_p_then_env_i_direct_effective_execve/v3"
            ),
            "os_injected_environment_policy": (
                "cf_user_text_encoding_uid_bound_then_removed/v1"
            ),
            "python_flags": ["-I", "-S", "-B"],
        },
        "broker_runtime_ref": _root_artifact(
            "broker.runtime.u10.history-test", "u10_root_broker_bootstrap.py"
        ),
        "current_selector": {
            "path": (
                "/Library/Application Support/semantic-guard/u10/"
                "trust-store-current.json"
            ),
            "owner_uid": 0,
            "owner_gid": 0,
            "mode": "0444",
            "publication_policy": (
                "history_fsync_before_atomic_current_replace/v1"
            ),
            "activation_ledger_path": (
                "/Library/Application Support/semantic-guard/u10/"
                "activations/store-transitions"
            ),
            "activation_ledger_policy": (
                "authorization_id_interval_receipt_atomic_publish/v3"
            ),
            "activation_ledger_retention_policy": (
                "no_automatic_deletion_while_store_revision_is_retained/v1"
            ),
            "revocation_selector_path": (
                "/Library/Application Support/semantic-guard/u10/"
                "trust-store-current-revocation.json"
            ),
            "revocation_history_path": (
                "/Library/Application Support/semantic-guard/u10/"
                "revocations/sha256"
            ),
            "revocation_ledger_path": (
                "/Library/Application Support/semantic-guard/u10/"
                "activations/store-revocations"
            ),
            "revocation_ledger_policy": (
                "authorization_id_interval_receipt_atomic_publish/v2"
            ),
            "revocation_ledger_retention_policy": (
                "no_automatic_deletion_while_store_revision_is_retained/v1"
            ),
            "revocation_decision_root_path": (
                "/Library/Application Support/semantic-guard/u10/"
                "authorizations"
            ),
            "revocation_decision_entry_policy": (
                "fixed_root_record_id_resolution_no_caller_raw/v1"
            ),
            "revocation_publication_policy": (
                "decision_consumption_history_selector_interval_receipt_recovery/v4"
            ),
        },
        "trust_store_history": {
            "path": (
                "/Library/Application Support/semantic-guard/u10/"
                "trust-store-history/sha256"
            ),
            "owner_uid": 0,
            "owner_gid": 0,
            "directory_mode": "0755",
            "artifact_mode": "0444",
            "address_profile": "sha256_raw_artifact_filename/v1",
            "write_policy": "root_o_excl_create_once_no_replace/v1",
            "retention_policy": "no_automatic_deletion_while_referenced/v1",
        },
        "coordination_lock": {
            "path": "/Library/Application Support/semantic-guard/u10/trust-store.lock",
            "owner_uid": 0,
            "owner_gid": 0,
            "mode": "0600",
            "protocol": "shared_execution_exclusive_activation_flock/v1",
        },
        "snapshot_root": {
            "path": "/Library/Application Support/semantic-guard/u10/snapshots",
            "resource_state": "active",
            "owner_uid": 0,
            "owner_gid": 0,
            "mode": "0755",
            "write_policy": "root_broker_content_addressed_snapshot_only/v1",
        },
        "signing_key": {
            "key_id": "key.u10.history-test",
            "key_state": "active",
            "algorithm": "ed25519",
            "public_key_base64": public_key_base64,
            "private_key_path": (
                "/Library/Application Support/semantic-guard/u10/"
                "keys/history-test.pem"
            ),
            "private_key_owner_uid": 0,
            "private_key_owner_gid": 0,
            "private_key_mode": "0600",
            "key_usage": "u10_broker_execution_attestation_only",
        },
        "nonce_ledger": {
            "ledger_root": (
                "/Library/Application Support/semantic-guard/u10/nonce-ledger"
            ),
            "resource_state": "active",
            "owner_uid": 0,
            "owner_gid": 0,
            "directory_mode": "0700",
            "record_format": "semantic-guard-u10-request-nonce-record/v1",
            "record_locator_scheme": "sha256(entry_id_nul_request_nonce).json",
            "write_policy": "one_record_per_nonce_o_excl_create_once/v1",
            "replay_policy": "reject_if_nonce_record_already_exists",
        },
        "result_spool": {
            "path": "/Library/Application Support/semantic-guard/u10/spool",
            "resource_state": "active",
            "owner_uid": 0,
            "owner_gid": 0,
            "mode": "0755",
            "write_policy": "root_broker_create_once_content_addressed_results/v1",
        },
        "entries": {ENTRY_ID: entry},
        "u4_authority_resolution": {
            "requirement_id": "U-4",
            "status": "unresolved",
            "consequence": (
                "does_not_establish_principal_identity_delegation_or_"
                "revocation_authority"
            ),
            "resolution_ref": None,
        },
        "revocation_ref": None,
        "formal_authority": "none",
        "positive_assurance_allowed": False,
    }
    store["store_activation_basis_digest"] = (
        core.store_activation_basis_digest_v2(store)
    )
    return _sealed(store, "store_digest")


def _worker_launch_contract() -> dict:
    def envelope_artifact(record_id: str, name: str) -> dict:
        reference = _root_artifact(record_id, name)
        return {
            member: reference[member]
            for member in (
                "record_id",
                "locator",
                "artifact_digest",
                "semantic_digest",
            )
        }

    return {
        "worker_version": "2.0.0-candidate",
        "interpreter_ref": envelope_artifact(
            "worker.python.u10.history-test", "vnext/.venv/bin/python"
        ),
        "entrypoint_ref": envelope_artifact(
            "worker.entrypoint.u10.history-test", "u10_snapshot_worker.py"
        ),
        "python_flags": ["-I", "-S", "-B"],
        "working_directory": (
            "/Library/Application Support/semantic-guard/u10/"
            "snapshots/snapshot.u10.history"
        ),
        "environment": {
            "PATH": "",
            "LC_ALL": "C",
            "PYTHONDONTWRITEBYTECODE": "1",
        },
        "process_group_policy": (
            "worker_and_inner_runner_share_root_reaped_group/v1"
        ),
    }


def _worker_and_broker_observations() -> tuple[dict, dict]:
    process = {
        "pid": 8101,
        "parent_pid": 8100,
        "process_group_id": 8101,
        "session_id": 8101,
    }
    return (
        {
            "process": process,
            "interval": {
                "started_at": "2026-07-20T00:00:01Z",
                "finished_at": "2026-07-20T00:00:05Z",
            },
        },
        {
            "process": {
                **process,
                "observed_at": "2026-07-20T00:00:00.500000Z",
            },
            "exit_code": 0,
            "process_group_quiescence": {
                "process_group_id": 8101,
                "state": "absent",
                "observed_at": "2026-07-20T00:00:05.500000Z",
            },
        },
    )


class U10HistoryAndLaunchContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.private_key = Ed25519PrivateKey.generate()
        public_raw = cls.private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        cls.store = _active_store(base64.b64encode(public_raw).decode("ascii"))
        core.validate_root_trust_store_v2(cls.store)
        cls.store_raw = core.canonical_json_bytes(cls.store)
        cls.history_ref = core.derive_historical_store_ref_v2(
            cls.store, cls.store_raw
        )

    def test_v2_trust_store_and_v2_base_envelope_schemas_remain(self) -> None:
        root_v2 = SCHEMA_DIRECTORY / "u10-root-trust-store-v2.schema.json"
        envelope_v2 = (
            SCHEMA_DIRECTORY
            / "broker-attested-execution-envelope-v2.schema.json"
        )
        self.assertTrue(root_v2.is_file())
        self.assertTrue(envelope_v2.is_file())
        self.assertFalse(
            (SCHEMA_DIRECTORY / "u10-root-trust-store-v1.schema.json").exists()
        )
        self.assertFalse(
            (
                SCHEMA_DIRECTORY
                / "broker-attested-execution-envelope-v1.schema.json"
            ).exists()
        )
        self.assertEqual(
            json.loads(root_v2.read_text(encoding="utf-8"))["properties"]
            ["schema_version"]["const"],
            "semantic-guard-u10-root-trust-store/v2",
        )
        self.assertEqual(
            json.loads(envelope_v2.read_text(encoding="utf-8"))["properties"]
            ["schema_version"]["const"],
            "semantic-guard-broker-attested-execution-envelope/v2",
        )

    def test_history_reference_is_raw_sha256_content_addressed(self) -> None:
        artifact_digest = core.digest_bytes(self.store_raw)
        self.assertEqual(self.history_ref["artifact_digest"], artifact_digest)
        self.assertEqual(
            self.history_ref["locator"],
            (
                "/Library/Application Support/semantic-guard/u10/"
                "trust-store-history/sha256/"
                f"{artifact_digest['value']}.json"
            ),
        )
        self.assertEqual(
            Path(self.history_ref["locator"]).stem,
            artifact_digest["value"],
        )
        self.assertEqual(self.history_ref["semantic_digest"], self.store["store_digest"])

    def _load_history(self, reference: dict, raw: bytes) -> tuple[dict, bytes]:
        root_owned_regular = SimpleNamespace(
            st_uid=0,
            st_gid=0,
            st_mode=stat.S_IFREG | 0o444,
            st_nlink=1,
        )
        with (
            patch.object(core, "read_protected_file", return_value=raw),
            patch.object(core.Path, "lstat", return_value=root_owned_regular),
            patch.object(core, "_verify_declared_directory"),
        ):
            return core.load_historical_root_trust_store_v2(reference)

    def test_history_loader_rejects_locator_and_digest_context_tampering(self) -> None:
        cases: list[tuple[str, dict, bytes, str]] = []

        locator = copy.deepcopy(self.history_ref)
        locator["locator"] = (
            "/Library/Application Support/semantic-guard/u10/"
            f"other-history/{locator['artifact_digest']['value']}.json"
        )
        cases.append(
            ("locator", locator, self.store_raw, "u10_historical_store_path_mismatch")
        )

        basename = copy.deepcopy(self.history_ref)
        basename["artifact_digest"] = _digest("different-raw")
        cases.append(
            ("basename", basename, self.store_raw, "u10_historical_store_path_mismatch")
        )

        cases.append(
            (
                "raw",
                copy.deepcopy(self.history_ref),
                self.store_raw + b"\n",
                "u10_historical_store_artifact_mismatch",
            )
        )

        semantic = copy.deepcopy(self.history_ref)
        semantic["semantic_digest"] = _digest("different-semantic-store")
        cases.append(
            (
                "semantic",
                semantic,
                self.store_raw,
                "u10_historical_store_context_mismatch",
            )
        )

        revision = copy.deepcopy(self.history_ref)
        revision["store_revision_id"] = "revision.u10.history-test.tampered"
        cases.append(
            (
                "store_revision",
                revision,
                self.store_raw,
                "u10_historical_store_context_mismatch",
            )
        )

        for name, reference, raw, expected_code in cases:
            with self.subTest(name=name):
                with self.assertRaises(BrokerBoundaryError) as observed:
                    self._load_history(reference, raw)
                self.assertEqual(observed.exception.code, expected_code)

    def test_currency_distinguishes_superseded_and_in_place_state_tamper(
        self,
    ) -> None:
        statement = {
            "trust_entry_ref": {"entry_id": ENTRY_ID},
            "trust_store_ref": copy.deepcopy(self.history_ref),
        }

        superseded = copy.deepcopy(self.store)
        superseded["store_revision_id"] = "revision.u10.history-test.2"
        superseded["store_version"] = "2.1.0"
        with patch.object(
            core,
            "load_fixed_root_trust_store_record_v2",
            return_value=(superseded, core.canonical_json_bytes(superseded)),
        ), patch.object(
            core, "_validate_store_activation_authorization_v1"
        ), patch.object(
            core, "_load_activation_transition_receipt_v1"
        ), patch.object(
            core, "_load_complete_store_activation_chain_v1"
        ), patch.object(
            core,
            "load_historical_root_trust_store_v2",
            return_value=(
                superseded,
                core.canonical_json_bytes(superseded),
            ),
        ), patch.object(
            core, "load_current_store_revocation_v1", return_value=None
        ):
            result = core._assess_current_currency_v2(statement, self.store)
        self.assertEqual(result["status"], "superseded")
        self.assertEqual(
            result["reason_codes"],
            ["newer_or_different_store_revision_requires_requalification"],
        )

        same_identity_different_digest = copy.deepcopy(self.store)
        same_identity_different_digest["store_digest"] = _digest(
            "same-identity-different-content"
        )
        with patch.object(
            core,
            "load_fixed_root_trust_store_record_v2",
            return_value=(
                same_identity_different_digest,
                core.canonical_json_bytes(same_identity_different_digest),
            ),
        ), patch.object(
            core, "_validate_store_activation_authorization_v1"
        ), patch.object(
            core, "_load_activation_transition_receipt_v1"
        ), patch.object(
            core, "_load_complete_store_activation_chain_v1"
        ), patch.object(
            core,
            "load_historical_root_trust_store_v2",
            return_value=(
                same_identity_different_digest,
                core.canonical_json_bytes(same_identity_different_digest),
            ),
        ), patch.object(
            core, "load_current_store_revocation_v1", return_value=None
        ):
            result = core._assess_current_currency_v2(statement, self.store)
        self.assertEqual(result["status"], "unresolved")
        self.assertEqual(
            result["reason_codes"],
            ["same_store_identity_with_different_content"],
        )

        in_place_state_mutations = {
            "store": (
                ("lifecycle_state",),
                "u10_current_store_not_governed",
            ),
            "entry": (
                ("entries", ENTRY_ID, "entry_state"),
                "same_store_identity_with_different_content",
            ),
            "key": (
                ("signing_key", "key_state"),
                "same_store_identity_with_different_content",
            ),
        }
        for name, (path, expected_reason) in (
            in_place_state_mutations.items()
        ):
            with self.subTest(in_place_state_mutation=name):
                current = copy.deepcopy(self.store)
                target = current
                for member in path[:-1]:
                    target = target[member]
                target[path[-1]] = "revoked"
                with patch.object(
                    core,
                    "load_fixed_root_trust_store_record_v2",
                    return_value=(current, core.canonical_json_bytes(current)),
                ), patch.object(
                    core, "_validate_store_activation_authorization_v1"
                ), patch.object(
                    core, "_load_activation_transition_receipt_v1"
                ), patch.object(
                    core, "_load_complete_store_activation_chain_v1"
                ), patch.object(
                    core,
                    "load_historical_root_trust_store_v2",
                    return_value=(
                        current,
                        core.canonical_json_bytes(current),
                    ),
                ), patch.object(
                    core,
                    "load_current_store_revocation_v1",
                    return_value=None,
                ):
                    result = core._assess_current_currency_v2(
                        statement, self.store
                    )
                self.assertEqual(result["status"], "unresolved")
                self.assertEqual(
                    result["reason_codes"],
                    [expected_reason],
                )

    def test_current_currency_requires_valid_activation_authorization(self) -> None:
        statement = {
            "trust_entry_ref": {"entry_id": ENTRY_ID},
            "trust_store_ref": copy.deepcopy(self.history_ref),
        }
        authorization_error = BrokerBoundaryError(
            "u10_store_activation_authorization_missing",
            self.store["store_revision_id"],
        )
        with patch.object(
            core,
            "load_fixed_root_trust_store_record_v2",
            return_value=(self.store, self.store_raw),
        ), patch.object(
            core,
            "_load_complete_store_activation_chain_v1",
            side_effect=authorization_error,
        ):
            result = core._assess_current_currency_v2(statement, self.store)
        self.assertEqual(result["status"], "unresolved")
        self.assertEqual(
            result["reason_codes"],
            ["u10_store_activation_authorization_missing"],
        )

    def test_historical_signature_does_not_fall_back_to_current_selector(self) -> None:
        statement = {
            "key_id": self.store["signing_key"]["key_id"],
            "signature_domain": "semantic-guard.u10.broker-execution-attestation/v2",
            "trust_store_ref": copy.deepcopy(self.history_ref),
            "trust_entry_ref": {"entry_id": ENTRY_ID},
            "occurrence_id": "occurrence.u10.history-test",
        }
        signature = core._sign_statement(statement, self.private_key)
        envelope = {
            "schema_version": "semantic-guard-broker-attested-execution-envelope/v2",
            "signed_statement": statement,
            "signature": {
                "algorithm": "ed25519",
                "encoding": "base64",
                "signed_member": "signed_statement",
                "value": base64.b64encode(signature).decode("ascii"),
            },
            "envelope_digest": _digest("schema-validation-is-isolated-here"),
        }
        unavailable = BrokerBoundaryError(
            "u10_root_trust_store_unavailable", "current selector absent"
        )
        with (
            patch.object(core, "_validate"),
            patch.object(core, "_sealed_digest"),
            patch.object(
                core,
                "load_historical_root_trust_store_v2",
                return_value=(self.store, self.store_raw),
            ) as historical_loader,
            patch.object(
                core,
                "load_fixed_root_trust_store_record_v2",
                side_effect=unavailable,
            ) as current_loader,
        ):
            observed_store, observed_raw = core._verify_historical_signature_v2(
                envelope
            )
            historical_loader.assert_called_once_with(self.history_ref)
            current_loader.assert_not_called()
            self.assertEqual(observed_store, self.store)
            self.assertEqual(observed_raw, self.store_raw)

            currency = core._assess_current_currency_v2(statement, self.store)
            self.assertEqual(currency["status"], "unresolved")
            self.assertEqual(
                currency["reason_codes"], ["u10_root_trust_store_unavailable"]
            )
            current_loader.assert_called_once_with()

    def test_signature_domain_is_v2_and_v1_domain_cannot_verify(self) -> None:
        envelope_schema = json.loads(
            (
                SCHEMA_DIRECTORY
                / "broker-attested-execution-envelope-v2.schema.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(
            core.SIGNATURE_PREFIX,
            b"semantic-guard:u10-broker-envelope:v2\0",
        )
        self.assertEqual(
            envelope_schema["properties"]["signed_statement"]["properties"]
            ["signature_domain"]["const"],
            "semantic-guard.u10.broker-execution-attestation/v2",
        )
        statement = {
            "signature_domain": "semantic-guard.u10.broker-execution-attestation/v2",
            "worker_launch_contract": _worker_launch_contract(),
        }
        signature = core._sign_statement(statement, self.private_key)
        self.private_key.public_key().verify(
            signature,
            core.SIGNATURE_PREFIX + core.canonical_json_bytes(statement),
        )
        with self.assertRaises(InvalidSignature):
            self.private_key.public_key().verify(
                signature,
                b"semantic-guard:u10-broker-envelope:v1\0"
                + core.canonical_json_bytes(statement),
            )

    def test_separated_worker_and_broker_observation_schema_and_signature_reject_tampering(self) -> None:
        envelope_schema = json.loads(
            (
                SCHEMA_DIRECTORY
                / "broker-attested-execution-envelope-v2.schema.json"
            ).read_text(encoding="utf-8")
        )
        launch_contract_schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$defs": envelope_schema["$defs"],
            "$ref": "#/$defs/worker_launch_contract",
        }
        validator = Draft202012Validator(
            launch_contract_schema, format_checker=FormatChecker()
        )
        launch_contract = _worker_launch_contract()
        self.assertEqual(list(validator.iter_errors(launch_contract)), [])

        changed_flags = copy.deepcopy(launch_contract)
        changed_flags["python_flags"] = ["-I", "-S", "-E"]
        changed_path = copy.deepcopy(launch_contract)
        changed_path["environment"]["PATH"] = "/tmp/attacker"
        changed_policy = copy.deepcopy(launch_contract)
        changed_policy["process_group_policy"] = "detached_unreaped/v1"
        changed_workdir = copy.deepcopy(launch_contract)
        changed_workdir["working_directory"] = "/tmp/attacker"
        injected = copy.deepcopy(launch_contract)
        injected["untrusted_argument"] = "--skip-verification"

        for name, changed in (
            ("python_flags", changed_flags),
            ("path", changed_path),
            ("process_group_policy", changed_policy),
            ("working_directory", changed_workdir),
            ("extra_member", injected),
        ):
            with self.subTest(schema_tamper=name):
                self.assertNotEqual(list(validator.iter_errors(changed)), [])

        worker_report, broker_observation = (
            _worker_and_broker_observations()
        )
        for definition, candidate in (
            ("worker_reported_observation", worker_report),
            ("broker_execution_observation", broker_observation),
        ):
            observation_validator = Draft202012Validator(
                {
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "$defs": envelope_schema["$defs"],
                    "$ref": f"#/$defs/{definition}",
                },
                format_checker=FormatChecker(),
            )
            self.assertEqual(
                list(observation_validator.iter_errors(candidate)), []
            )

        statement = {
            "signature_domain": "semantic-guard.u10.broker-execution-attestation/v2",
            "worker_launch_contract": launch_contract,
            "worker_reported_observation": worker_report,
            "broker_execution_observation": broker_observation,
            "started_at": "2026-07-20T00:00:00Z",
            "finished_at": "2026-07-20T00:00:06Z",
        }
        signature = core._sign_statement(statement, self.private_key)
        tampered_statement = copy.deepcopy(statement)
        tampered_statement["broker_execution_observation"]["process"][
            "pid"
        ] += 1
        with self.assertRaises(BrokerBoundaryError) as observed:
            core._verify_statement_signature(
                tampered_statement, signature, self.private_key.public_key()
            )
        self.assertEqual(observed.exception.code, "u10_envelope_signature_invalid")


if __name__ == "__main__":
    unittest.main()
