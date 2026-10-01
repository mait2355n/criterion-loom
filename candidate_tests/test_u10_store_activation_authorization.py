from __future__ import annotations

import base64
import copy
from contextlib import ExitStack
from pathlib import Path
import stat
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

import semantic_guard_u10_broker.core as core
from semantic_guard_u10_broker.protected_io import BrokerBoundaryError

try:
    from .test_u10_history_and_launch_contracts import _active_store, _sealed
    from .u10_publisher_contract_fixture import publisher_contract_binding
except ImportError:  # unittest discovery imports test modules as top-level names.
    if __package__:
        raise
    from candidate_tests.test_u10_history_and_launch_contracts import _active_store, _sealed
    from candidate_tests.u10_publisher_contract_fixture import publisher_contract_binding


AUTHORIZATION_ROOT = Path(
    "/Library/Application Support/semantic-guard/u10/authorizations"
)
STORE_ACTIVATION_BASIS_ROOT = Path(
    "/Library/Application Support/semantic-guard/u10/store-activation-bases"
)
KEY_ID = "00000000-0000-4000-8000-000000000001"


class U10StoreActivationAuthorizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        private_key = Ed25519PrivateKey.generate()
        public_raw = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        cls.public_key_base64 = base64.b64encode(public_raw).decode("ascii")

    def _candidate_store(self) -> dict:
        store = _active_store(self.public_key_base64)
        store["signing_key"]["key_id"] = KEY_ID
        store["lifecycle_state"] = "candidate"
        store["activation_authorization_ref"] = None
        store["snapshot_root"]["resource_state"] = "candidate"
        store["signing_key"]["key_state"] = "candidate"
        store["nonce_ledger"]["resource_state"] = "candidate"
        store["result_spool"]["resource_state"] = "candidate"
        for entry_id, entry in store["entries"].items():
            entry["entry_state"] = "candidate"
            entry["snapshot_manifest_binding"]["lifecycle_state"] = "candidate"
            entry["eligibility_source_binding"]["lifecycle_state"] = "candidate"
            entry.pop("adoption_record_binding", None)
            entry["environment_adoption_binding"] = None
            store["entries"][entry_id] = _sealed(entry, "entry_digest")
        store["store_activation_basis_digest"] = (
            core.store_activation_basis_digest_v2(store)
        )
        return _sealed(store, "store_digest")

    def _authorization(self, store: dict, basis_ref: dict) -> dict:
        authorization = {
            "schema_version": (
                "semantic-guard-u10-store-activation-authorization/v1"
            ),
            "authorization_id": (
                f"authorization.{store['store_revision_id']}"
            ),
            "authorization_version": "1.0.0",
            "record_kind": "store_activation_authorization",
            "human_decision": "accept",
            "decision_owner": "human",
            "store_id": store["store_id"],
            "store_revision_id": store["store_revision_id"],
            "store_version": store["store_version"],
            "store_activation_basis_digest": copy.deepcopy(
                store["store_activation_basis_digest"]
            ),
            "store_activation_basis_ref": copy.deepcopy(basis_ref),
            "authorized_operation": "publish_exact_active_store_revision",
            "transition_kind": "initial_activation",
            "prior_store_ref": None,
            "prior_revocation_ref": None,
            "recorded_at": "2026-07-20T00:00:00Z",
            "u4_principal_authenticity": "unresolved",
            "authority_scope": "u10_store_activation_only",
            "formal_authority": "human_activation_decision_only",
            "positive_assurance_allowed": False,
        }
        return _sealed(authorization, "authorization_digest")

    def _active_store_and_authorization(self) -> tuple[dict, dict, bytes]:
        store = self._candidate_store()
        store["lifecycle_state"] = "active"
        store["snapshot_root"]["resource_state"] = "active"
        store["signing_key"]["key_state"] = "active"
        store["nonce_ledger"]["resource_state"] = "active"
        store["result_spool"]["resource_state"] = "active"
        for entry_id, entry in store["entries"].items():
            entry["entry_state"] = "active"
            entry["snapshot_manifest_binding"]["lifecycle_state"] = "active"
            entry["environment_adoption_binding"] = {
                "record_id": "environment-adoption.u10.history-test",
                "locator": (
                    "/Library/Application Support/semantic-guard/u10/"
                    "authorizations/environment-adoption.u10.history-test.json"
                ),
                "artifact_digest": core.digest_bytes(b"environment-adoption"),
                "semantic_digest": core.digest_bytes(b"environment-adoption-semantic"),
            }
            store["entries"][entry_id] = _sealed(entry, "entry_digest")
        entry_id = next(iter(store["entries"]))
        manifest_binding = store["entries"][entry_id]["snapshot_manifest_binding"]
        manifest_ref = {
            "record_id": manifest_binding["snapshot_id"],
            "locator": manifest_binding["locator"],
            "artifact_digest": copy.deepcopy(manifest_binding["artifact_digest"]),
            "semantic_digest": copy.deepcopy(manifest_binding["manifest_digest"]),
        }
        signing_key_ref = {
            "key_id": KEY_ID,
            "key_entity_ref": f"U-10 signing key・{KEY_ID}",
            "locator": (
                "/Library/Application Support/semantic-guard/u10/keys/"
                f"generations/{KEY_ID}/public-metadata.json"
            ),
            "artifact_digest": core.digest_bytes(b"key-metadata-raw"),
            "metadata_digest": core.digest_bytes(b"key-metadata-semantic"),
            "generation_authorization_ref": {
                "authorization_id": "authorization.key.fixture",
                "locator": (
                    "/Library/Application Support/semantic-guard/u10/"
                    "activations/key-transitions/"
                    "authorization.key.fixture.authorization.json"
                ),
                "artifact_digest": core.digest_bytes(
                    b"key-authorization-raw"
                ),
                "authorization_digest": core.digest_bytes(b"key-authorization"),
            },
            "generation_consumption_ref": {
                "consumption_id": "consumption.authorization.key.fixture",
                "locator": (
                    "/Library/Application Support/semantic-guard/u10/"
                    "activations/key-transitions/"
                    "authorization.key.fixture.consumption.json"
                ),
                "artifact_digest": core.digest_bytes(
                    b"key-consumption-raw"
                ),
                "consumption_digest": core.digest_bytes(
                    b"key-consumption-semantic"
                ),
            },
        }
        selector_raw_digest = core.digest_bytes(b"key-selector-raw")
        signing_key_selector_ref = {
            "selector_id": "selector.authorization.key.fixture",
            "locator": (
                "/Library/Application Support/semantic-guard/u10/keys/"
                "selector-history/sha256/"
                f"{selector_raw_digest['value']}.json"
            ),
            "artifact_digest": selector_raw_digest,
            "selector_digest": core.digest_bytes(
                b"key-selector-semantic"
            ),
        }
        transition_digest = core.store_activation_transition_digest_v2(
            snapshot_manifest_ref=manifest_ref,
            entry_id=entry_id,
            prior_store_ref=None,
            prior_revocation_ref=None,
            signing_key_ref=signing_key_ref,
            signing_key_selector_ref=signing_key_selector_ref,
        )
        store["store_revision_id"] = (
            f"revision.u10.{transition_digest['value']}"
        )
        store["store_activation_basis_digest"] = (
            core.store_activation_basis_digest_v2(store)
        )
        basis_id = f"store-basis.{transition_digest['value']}"
        snapshot_activation_authorization_ref = {
            "record_id": "authorization.snapshot.history-test",
            "locator": (
                "/Library/Application Support/semantic-guard/u10/"
                "authorizations/authorization.snapshot.history-test.json"
            ),
            "artifact_digest": core.digest_bytes(b"snapshot-authorization-raw"),
            "semantic_digest": core.digest_bytes(
                b"snapshot-authorization-semantic"
            ),
        }
        basis = {
            "schema_version": "semantic-guard-u10-store-activation-basis/v2",
            "basis_id": basis_id,
            "basis_version": "2.0.0",
            "record_kind": "exact_store_activation_basis_candidate",
            "store_content": core.store_activation_content_v1(store),
            "store_activation_basis_digest": copy.deepcopy(
                store["store_activation_basis_digest"]
            ),
            "store_transition_digest": transition_digest,
            "entry_id": entry_id,
            "snapshot_manifest_ref": manifest_ref,
            "snapshot_activation_authorization_ref": (
                snapshot_activation_authorization_ref
            ),
            "signing_key_ref": signing_key_ref,
            "signing_key_selector_ref": signing_key_selector_ref,
            "prior_store_ref": None,
            "prior_revocation_ref": None,
            "publisher_contract_binding": publisher_contract_binding(),
            "prepared_at": "2026-07-20T00:00:00Z",
            "publication_state": "not_published",
            "formal_authority": "none",
            "positive_assurance_allowed": False,
        }
        basis = _sealed(basis, "basis_digest")
        basis_raw = core.canonical_json_bytes(basis)
        basis_ref = {
            "record_id": basis_id,
            "locator": str(
                STORE_ACTIVATION_BASIS_ROOT
                / "authorization.snapshot.history-test.store-basis.json"
            ),
            "artifact_digest": core.digest_bytes(basis_raw),
            "semantic_digest": copy.deepcopy(basis["basis_digest"]),
        }
        self._current_basis = basis
        self._current_basis_raw = basis_raw
        authorization = self._authorization(store, basis_ref)
        raw = core.canonical_json_bytes(authorization)
        store["activation_authorization_ref"] = {
            "record_id": authorization["authorization_id"],
            "locator": str(
                AUTHORIZATION_ROOT
                / f"{authorization['authorization_id']}.json"
            ),
            "artifact_digest": core.digest_bytes(raw),
            "semantic_digest": copy.deepcopy(
                authorization["authorization_digest"]
            ),
            "owner_uid": 0,
            "owner_gid": 0,
            "write_protection": "not_group_or_world_writable",
        }
        store = _sealed(store, "store_digest")
        return store, authorization, raw

    def _validate_with_mocked_artifact(
        self,
        store: dict,
        raw: bytes,
    ) -> None:
        # Keep the semantic checks live while replacing only root-owned I/O.
        # Patching both seams permits either a dedicated reader or the common
        # artifact reader without weakening the locator-boundary assertion.
        with ExitStack() as stack:
            if hasattr(core, "_verify_root_artifact"):
                stack.enter_context(
                    patch.object(
                        core,
                        "_verify_root_artifact",
                        side_effect=lambda reference: (
                            self._current_basis_raw
                            if reference.get("locator", "").startswith(
                                str(STORE_ACTIVATION_BASIS_ROOT)
                            )
                            else raw
                        ),
                    )
                )
            stack.enter_context(
                patch.object(core, "read_protected_file", return_value=raw)
            )
            stack.enter_context(
                patch.object(
                    core.Path,
                    "lstat",
                    return_value=SimpleNamespace(
                        st_uid=0,
                        st_gid=0,
                        st_nlink=1,
                        st_mode=stat.S_IFREG | 0o444,
                    ),
                )
            )
            core._validate_store_activation_authorization_v1(store)

    def _bind_authorization_artifact(
        self,
        store: dict,
        authorization: dict,
    ) -> tuple[dict, bytes]:
        bound = copy.deepcopy(store)
        raw = core.canonical_json_bytes(authorization)
        bound["activation_authorization_ref"]["artifact_digest"] = (
            core.digest_bytes(raw)
        )
        bound["activation_authorization_ref"]["semantic_digest"] = (
            copy.deepcopy(authorization["authorization_digest"])
        )
        return _sealed(bound, "store_digest"), raw

    def test_store_activation_basis_is_exact_and_excludes_only_state_wrappers(
        self,
    ) -> None:
        store = self._candidate_store()
        expected = store["store_activation_basis_digest"]

        for field, replacement in (
            ("lifecycle_state", "revoked"),
            ("activation_authorization_ref", {"ignored": True}),
            ("revocation_ref", {"ignored": True}),
            ("store_digest", {"algorithm": "sha256", "value": "f" * 64}),
            (
                "store_activation_basis_digest",
                {"algorithm": "sha256", "value": "e" * 64},
            ),
        ):
            with self.subTest(excluded_field=field):
                changed = copy.deepcopy(store)
                changed[field] = replacement
                self.assertEqual(
                    core.store_activation_basis_digest_v2(changed), expected
                )

        material_changes = (
            ("store_revision_id", "revision.u10.history-test.changed"),
            ("store_version", "2.0.1"),
            ("broker_runtime_version", "different-runtime"),
            ("formal_authority", "forged-authority"),
            ("positive_assurance_allowed", True),
        )
        for field, replacement in material_changes:
            with self.subTest(bound_field=field):
                changed = copy.deepcopy(store)
                changed[field] = replacement
                self.assertNotEqual(
                    core.store_activation_basis_digest_v2(changed), expected
                )

    def test_transition_identity_binds_prior_state_and_signing_key(self) -> None:
        self._active_store_and_authorization()
        basis = self._current_basis
        common = {
            "snapshot_manifest_ref": basis["snapshot_manifest_ref"],
            "entry_id": basis["entry_id"],
            "prior_store_ref": None,
            "prior_revocation_ref": None,
            "signing_key_ref": basis["signing_key_ref"],
            "signing_key_selector_ref": basis[
                "signing_key_selector_ref"
            ],
        }
        baseline = core.store_activation_transition_digest_v2(**common)
        self.assertEqual(
            core.store_activation_transition_digest_v2(**common), baseline
        )
        for field, replacement in (
            (
                "prior_store_ref",
                {
                    "store_id": "store.u10.prior",
                    "store_revision_id": "revision.u10.prior",
                    "store_version": "2.0.0",
                    "store_activation_basis_digest": core.digest_bytes(b"basis"),
                    "artifact_digest": core.digest_bytes(b"artifact"),
                    "semantic_digest": core.digest_bytes(b"semantic"),
                },
            ),
            (
                "prior_revocation_ref",
                {
                    "revocation_id": "revocation.u10.prior",
                    "artifact_digest": core.digest_bytes(b"revocation-artifact"),
                    "semantic_digest": core.digest_bytes(b"revocation-semantic"),
                },
            ),
            (
                "signing_key_ref",
                {
                    **basis["signing_key_ref"],
                    "metadata_digest": core.digest_bytes(b"rotated-key"),
                },
            ),
            (
                "signing_key_selector_ref",
                {
                    **basis["signing_key_selector_ref"],
                    "selector_digest": core.digest_bytes(
                        b"different-selector-head"
                    ),
                },
            ),
        ):
            with self.subTest(field=field):
                changed = copy.deepcopy(common)
                changed[field] = replacement
                self.assertNotEqual(
                    core.store_activation_transition_digest_v2(**changed),
                    baseline,
                )

    def test_exact_human_authorization_is_accepted_without_granting_assurance(
        self,
    ) -> None:
        store, authorization, raw = self._active_store_and_authorization()
        core.validate_root_trust_store_v2(store)
        self._validate_with_mocked_artifact(store, raw)
        self.assertEqual(authorization["human_decision"], "accept")
        self.assertEqual(authorization["u4_principal_authenticity"], "unresolved")
        self.assertFalse(authorization["positive_assurance_allowed"])
        self.assertEqual(store["formal_authority"], "none")
        self.assertFalse(store["positive_assurance_allowed"])

    def test_authorization_id_resolves_exact_basis_and_renders_store(self) -> None:
        store, authorization, authorization_raw = (
            self._active_store_and_authorization()
        )
        publisher = publisher_contract_binding()
        expected_result = {"published": True}
        trusted_stat = SimpleNamespace(
            st_uid=0,
            st_gid=0,
            st_nlink=1,
            st_mode=stat.S_IFREG | 0o444,
        )
        with (
            patch.object(
                core,
                "_validate_publisher_contract_binding_v1",
                return_value=publisher,
            ),
            patch.object(
                core,
                "read_protected_file",
                return_value=authorization_raw,
            ),
            patch.object(core.Path, "lstat", return_value=trusted_stat),
            patch.object(
                core,
                "_verify_root_artifact",
                return_value=self._current_basis_raw,
            ),
            patch.object(
                core,
                "_publish_active_root_trust_store_bytes_v2",
                return_value=expected_result,
            ) as publish,
        ):
            observed = core.publish_active_root_trust_store_by_id_v1(
                authorization["authorization_id"],
                publisher_contract_binding=publisher,
            )

        self.assertEqual(observed, expected_result)
        publish.assert_called_once()
        rendered_raw, rendered_publisher = publish.call_args.args
        self.assertEqual(rendered_publisher, publisher)
        self.assertEqual(
            core._load_json_bytes(rendered_raw, "test_rendered_store"),
            store,
        )
        core.validate_root_trust_store_v2(store)

    def test_authorization_seal_and_exact_store_binding_are_enforced(self) -> None:
        store, authorization, _ = self._active_store_and_authorization()
        mutations = {
            "broken_seal": ("recorded_at", "2026-07-20T00:00:01Z", False),
            "store_id": ("store_id", "store.u10.other", True),
            "store_revision": (
                "store_revision_id",
                "revision.u10.history-test.other",
                True,
            ),
            "store_version": ("store_version", "999.0.0", True),
            "basis": (
                "store_activation_basis_digest",
                {"algorithm": "sha256", "value": "a" * 64},
                True,
            ),
            "operation": ("authorized_operation", "inspect_only", True),
            "human_decision": ("human_decision", "pending", True),
            "decision_owner": ("decision_owner", "ai_agent", True),
            "u4": ("u4_principal_authenticity", "resolved", True),
            "authority_scope": ("authority_scope", "all_u10_operations", True),
            "formal_authority": ("formal_authority", "positive_assurance", True),
            "positive_assurance": ("positive_assurance_allowed", True, True),
        }
        for name, (field, replacement, reseal) in mutations.items():
            with self.subTest(name=name):
                changed = copy.deepcopy(authorization)
                changed[field] = replacement
                if reseal:
                    changed = _sealed(changed, "authorization_digest")
                bound_store, changed_raw = self._bind_authorization_artifact(
                    store, changed
                )
                with self.assertRaises(BrokerBoundaryError):
                    self._validate_with_mocked_artifact(
                        bound_store, changed_raw
                    )

        mismatched_ref = copy.deepcopy(store)
        mismatched_ref["activation_authorization_ref"]["semantic_digest"] = {
            "algorithm": "sha256",
            "value": "b" * 64,
        }
        mismatched_ref = _sealed(mismatched_ref, "store_digest")
        with self.assertRaises(BrokerBoundaryError):
            self._validate_with_mocked_artifact(
                mismatched_ref, core.canonical_json_bytes(authorization)
            )

    def test_null_outside_root_and_tampered_authorization_are_rejected(self) -> None:
        candidate = self._candidate_store()
        active_without_authorization = copy.deepcopy(candidate)
        active_without_authorization["lifecycle_state"] = "active"
        active_without_authorization = _sealed(
            active_without_authorization, "store_digest"
        )
        with self.assertRaises(BrokerBoundaryError):
            core._validate_store_activation_authorization_v1(
                active_without_authorization
            )

        store, authorization, raw = self._active_store_and_authorization()
        outside = copy.deepcopy(store)
        outside["activation_authorization_ref"]["locator"] = (
            "/Library/Application Support/semantic-guard/u10/"
            "snapshots/forged-authorization.json"
        )
        outside = _sealed(outside, "store_digest")
        with self.assertRaises(BrokerBoundaryError):
            self._validate_with_mocked_artifact(outside, raw)

        tampered = copy.deepcopy(authorization)
        tampered["store_version"] = "tampered-after-seal"
        tampered_store, tampered_raw = self._bind_authorization_artifact(
            store, tampered
        )
        with self.assertRaises(BrokerBoundaryError):
            self._validate_with_mocked_artifact(
                tampered_store, tampered_raw
            )

    def test_candidate_structure_is_not_active_publication_authority(self) -> None:
        candidate = self._candidate_store()
        core.validate_root_trust_store_v2(candidate)
        with (
            patch.object(core.os, "geteuid", return_value=0),
            patch.object(core, "_verify_declared_directory") as directory_check,
            patch.object(
                core,
                "_validate_store_activation_authorization_v1",
                side_effect=BrokerBoundaryError(
                    "u10_store_activation_authorization_required",
                    candidate["store_revision_id"],
                ),
            ) as authorization_gate,
            patch.object(
                core, "_seal_root_trust_store_history_under_lock_v2"
            ) as history_write,
        ):
            active_with_unverified_authorization, _, _ = (
                self._active_store_and_authorization()
            )
            raw = core.canonical_json_bytes(active_with_unverified_authorization)
            with self.assertRaises(BrokerBoundaryError) as observed:
                core.publish_active_root_trust_store_v2(raw)
            self.assertEqual(
                observed.exception.code,
                "u10_unbound_publisher_invocation_prohibited",
            )
            authorization_gate.assert_not_called()
            directory_check.assert_not_called()
            history_write.assert_not_called()


if __name__ == "__main__":
    unittest.main()
