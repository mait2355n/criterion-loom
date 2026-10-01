from __future__ import annotations

import copy
import base64
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

import semantic_guard_u10_broker.core as core
from semantic_guard_u10_broker.protected_io import BrokerBoundaryError

try:
    from .test_u10_store_activation_authorization import (
        U10StoreActivationAuthorizationTests as _AuthorizationFixture,
        _sealed,
    )
    from .u10_publisher_contract_fixture import publisher_contract_binding
except ImportError:
    from candidate_tests.test_u10_store_activation_authorization import (
        U10StoreActivationAuthorizationTests as _AuthorizationFixture,
        _sealed,
    )
    from candidate_tests.u10_publisher_contract_fixture import publisher_contract_binding


SCRIPT = Path(__file__).parent / "fixtures" / "scripts" / "u10_snapshot_store_production.py"
SPEC = importlib.util.spec_from_file_location(
    "u10_snapshot_store_production_reservation_test", SCRIPT
)
assert SPEC is not None and SPEC.loader is not None
producer = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = producer
SPEC.loader.exec_module(producer)


class U10StoreBasisReservationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _AuthorizationFixture.setUpClass()

    def test_snapshot_environment_adoption_requires_canonical_record_bytes(
        self,
    ) -> None:
        adoption = {
            "schema_version": (
                "semantic-guard-u10-snapshot-environment-adoption/v1"
            ),
            "adoption_id": "adoption.u10.noncanonical-test",
        }
        raw = producer.json_record_bytes(adoption)
        reference = {
            "locator": (
                "/Library/Application Support/semantic-guard/u10/"
                "authorizations/adoption.u10.noncanonical-test.json"
            )
        }
        with (
            patch.object(
                producer, "_verify_root_artifact_ref", return_value=raw
            ),
            patch.object(producer, "_validate_schema"),
            patch.object(producer, "_verify_seal"),
            self.assertRaises(producer.U10SnapshotProductionError) as observed,
        ):
            producer._load_snapshot_environment_adoption(
                reference,
                paths=producer.SnapshotPaths(),
                projection={},
                projection_path=Path("/tmp/projection.json"),
                projection_raw=b"{}\n",
            )
        self.assertEqual(
            observed.exception.code,
            "u10_snapshot_environment_adoption_noncanonical",
        )

    def _fixture(self) -> tuple[dict, bytes, dict, dict, dict, dict]:
        source = _AuthorizationFixture()
        source.public_key_base64 = (
            _AuthorizationFixture.public_key_base64
        )
        source._active_store_and_authorization()
        basis = copy.deepcopy(source._current_basis)
        content = copy.deepcopy(basis["store_content"])
        entry_id = basis["entry_id"]
        manifest_binding = content["entries"][entry_id][
            "snapshot_manifest_binding"
        ]
        manifest = {
            "snapshot_id": manifest_binding["snapshot_id"],
            "prepared_for_entry_id": entry_id,
            "manifest_digest": copy.deepcopy(
                manifest_binding["manifest_digest"]
            ),
            "root_storage": {
                "snapshot_path": str(Path(manifest_binding["locator"]).parent)
            },
        }
        manifest_raw = producer.json_record_bytes(manifest)
        manifest_binding["artifact_digest"] = producer.digest_bytes(manifest_raw)
        content["entries"][entry_id] = _sealed(
            content["entries"][entry_id], "entry_digest"
        )
        return (
            manifest,
            manifest_raw,
            content,
            copy.deepcopy(content["signing_key"]),
            copy.deepcopy(basis["signing_key_ref"]),
            copy.deepcopy(basis["signing_key_selector_ref"]),
        )

    def test_retry_resolves_one_prepublication_basis_without_recomputation(
        self,
    ) -> None:
        (
            manifest,
            manifest_raw,
            content,
            signing_key,
            signing_key_ref,
            signing_key_selector_ref,
        ) = self._fixture()
        snapshot_authorization_ref = {
            "record_id": "authorization.snapshot.reservation-test",
            "locator": (
                "/Library/Application Support/semantic-guard/u10/"
                "authorizations/authorization.snapshot.reservation-test.json"
            ),
            "artifact_digest": producer.digest_bytes(b"snapshot-auth-raw"),
            "semantic_digest": producer.digest_bytes(b"snapshot-auth-semantic"),
        }
        publisher = publisher_contract_binding()

        def render_content(**kwargs):
            rendered = copy.deepcopy(content)
            rendered["store_revision_id"] = kwargs["store_revision_id"]
            return rendered

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            basis_root = root / "store-activation-bases"
            root.mkdir(mode=0o700, exist_ok=True)
            basis_root.mkdir(mode=0o700)
            paths = producer.SnapshotPaths(
                u10_root=root,
                store_activation_basis_root=basis_root,
            )
            with (
                patch.object(
                    producer,
                    "_validate_publisher_contract_binding",
                    return_value=publisher,
                ),
                patch.object(
                    producer,
                    "_active_signing_key_context",
                    return_value=(
                        signing_key,
                        signing_key_ref,
                        signing_key_selector_ref,
                    ),
                ) as key_resolution,
                patch.object(
                    producer,
                    "_initial_store_content",
                    side_effect=render_content,
                ) as content_render,
                patch.object(
                    producer,
                    "_utc_now",
                    return_value="2026-07-20T00:00:01Z",
                ),
            ):
                first = producer._prepare_store_activation_basis_candidate(
                    manifest=manifest,
                    manifest_raw=manifest_raw,
                    snapshot_activation_authorization_ref=(
                        snapshot_authorization_ref
                    ),
                    projection_authorization={},
                    publisher_contract_binding=publisher,
                    paths=paths,
                    enforce_fixed_paths=False,
                )
            key_resolution.assert_called_once()
            content_render.assert_called_once()

            reservation_path = (
                basis_root
                / "authorization.snapshot.reservation-test.store-basis.json"
            )
            first_raw = reservation_path.read_bytes()
            first_basis = producer._json(
                first_raw, code="test_store_basis_unreadable"
            )
            self.assertEqual(first["locator"], str(reservation_path))
            self.assertEqual(
                first_basis["prepared_at"], "2026-07-20T00:00:01Z"
            )

            with (
                patch.object(
                    producer,
                    "_validate_publisher_contract_binding",
                    return_value=publisher,
                ),
                patch.object(
                    producer,
                    "_active_signing_key_context",
                    side_effect=AssertionError("retry re-resolved mutable key"),
                ),
                patch.object(
                    producer,
                    "_initial_store_content",
                    side_effect=AssertionError("retry re-rendered content"),
                ),
                patch.object(
                    producer,
                    "_utc_now",
                    return_value="2026-07-20T00:09:59Z",
                ),
            ):
                second = producer._prepare_store_activation_basis_candidate(
                    manifest=manifest,
                    manifest_raw=manifest_raw,
                    snapshot_activation_authorization_ref=(
                        snapshot_authorization_ref
                    ),
                    projection_authorization={},
                    publisher_contract_binding=publisher,
                    paths=paths,
                    enforce_fixed_paths=False,
                )

            self.assertEqual(second, first)
            self.assertEqual(reservation_path.read_bytes(), first_raw)

            changed_publisher = copy.deepcopy(publisher)
            changed_publisher["artifacts"]["snapshot_store_producer"][
                "artifact_digest"
            ] = producer.digest_bytes(b"changed-producer")
            changed_publisher["binding_digest"] = producer.sealed_digest(
                changed_publisher, "binding_digest"
            )
            with patch.object(
                producer,
                "_validate_publisher_contract_binding",
                return_value=changed_publisher,
            ):
                with self.assertRaises(
                    producer.U10SnapshotProductionError
                ) as observed:
                    producer._prepare_store_activation_basis_candidate(
                        manifest=manifest,
                        manifest_raw=manifest_raw,
                        snapshot_activation_authorization_ref=(
                            snapshot_authorization_ref
                        ),
                        projection_authorization={},
                        publisher_contract_binding=changed_publisher,
                        paths=paths,
                        enforce_fixed_paths=False,
                    )
            self.assertEqual(
                observed.exception.code,
                "u10_store_activation_basis_publisher_contract_changed",
            )

    def test_completed_receipt_path_never_reconstructs_missing_basis(
        self,
    ) -> None:
        (
            manifest,
            manifest_raw,
            _content,
            _signing_key,
            _signing_key_ref,
            _signing_key_selector_ref,
        ) = self._fixture()
        snapshot_authorization_ref = {
            "record_id": "authorization.snapshot.completed-receipt",
            "locator": (
                "/Library/Application Support/semantic-guard/u10/"
                "authorizations/authorization.snapshot.completed-receipt.json"
            ),
            "artifact_digest": producer.digest_bytes(b"snapshot-auth-raw"),
            "semantic_digest": producer.digest_bytes(b"snapshot-auth-semantic"),
        }
        publisher = publisher_contract_binding()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            basis_root = root / "store-activation-bases"
            root.mkdir(mode=0o700, exist_ok=True)
            basis_root.mkdir(mode=0o700)
            paths = producer.SnapshotPaths(
                u10_root=root,
                store_activation_basis_root=basis_root,
            )
            with (
                patch.object(
                    producer,
                    "_validate_publisher_contract_binding",
                    return_value=publisher,
                ),
                patch.object(
                    producer,
                    "_active_signing_key_context",
                    side_effect=AssertionError("missing basis was reconstructed"),
                ),
                self.assertRaises(
                    producer.U10SnapshotProductionError
                ) as observed,
            ):
                producer._prepare_store_activation_basis_candidate(
                    manifest=manifest,
                    manifest_raw=manifest_raw,
                    snapshot_activation_authorization_ref=(
                        snapshot_authorization_ref
                    ),
                    projection_authorization={},
                    publisher_contract_binding=publisher,
                    paths=paths,
                    enforce_fixed_paths=False,
                    create_if_missing=False,
                )
            self.assertEqual(
                observed.exception.code,
                "u10_store_activation_basis_missing_after_receipt",
            )
            self.assertEqual(list(basis_root.iterdir()), [])

    def test_append_only_basis_link_crash_recovers_exact_pending_inode(
        self,
    ) -> None:
        value = {
            "schema_version": "test-store-basis-link-recovery/v1",
            "basis_id": "store-basis.link-recovery",
        }
        raw = producer.json_record_bytes(value)
        with tempfile.TemporaryDirectory() as temporary:
            ledger = Path(temporary)
            final = ledger / "authorization.snapshot.test.store-basis.json"
            pending = ledger / f".{final.name}.pending"
            pending.write_bytes(raw)
            pending.chmod(0o444)
            # Model a crash after link(2) published the final name but before
            # the private pending name was unlinked and the directory fsynced.
            os.link(pending, final)
            self.assertEqual(final.stat().st_nlink, 2)

            observed = producer._publish_append_only_record(
                final,
                value,
                ledger_root=ledger,
                mode=0o444,
            )

            self.assertEqual(observed, raw)
            self.assertTrue(final.exists())
            self.assertFalse(pending.exists())
            self.assertEqual(final.stat().st_nlink, 1)

    def test_append_only_basis_pending_write_crash_resumes_publication(
        self,
    ) -> None:
        value = {
            "schema_version": "test-store-basis-pending-recovery/v1",
            "basis_id": "store-basis.pending-recovery",
        }
        raw = producer.json_record_bytes(value)
        with tempfile.TemporaryDirectory() as temporary:
            ledger = Path(temporary)
            final = ledger / "authorization.snapshot.test.store-basis.json"
            pending = ledger / f".{final.name}.pending"
            pending.write_bytes(raw)
            pending.chmod(0o444)

            observed = producer._publish_append_only_record(
                final,
                value,
                ledger_root=ledger,
                mode=0o444,
            )

            self.assertEqual(observed, raw)
            self.assertTrue(final.exists())
            self.assertFalse(pending.exists())
            self.assertEqual(final.stat().st_nlink, 1)

    def test_root_generated_raw_key_is_the_only_accepted_private_format(
        self,
    ) -> None:
        key = Ed25519PrivateKey.generate()
        raw = key.private_bytes(
            serialization.Encoding.Raw,
            serialization.PrivateFormat.Raw,
            serialization.NoEncryption(),
        )
        public = key.public_key().public_bytes(
            serialization.Encoding.Raw,
            serialization.PublicFormat.Raw,
        )
        path = Path(
            "/Library/Application Support/semantic-guard/u10/keys/"
            "generations/00000000-0000-4000-8000-000000000001/"
            "private.ed25519"
        )
        self.assertEqual(
            core._ed25519_private_key_from_root_raw_v1(
                raw, path=path
            ).public_key().public_bytes(
                serialization.Encoding.Raw,
                serialization.PublicFormat.Raw,
            ),
            public,
        )
        self.assertEqual(
            producer._ed25519_private_key_from_root_raw(
                raw, path=path
            ).public_key().public_bytes(
                serialization.Encoding.Raw,
                serialization.PublicFormat.Raw,
            ),
            public,
        )

        pem = key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        for malformed in (raw[:-1], raw + b"x", pem):
            with self.subTest(length=len(malformed)):
                with self.assertRaises(BrokerBoundaryError):
                    core._ed25519_private_key_from_root_raw_v1(
                        malformed, path=path
                    )
                with self.assertRaises(
                    producer.U10SnapshotProductionError
                ):
                    producer._ed25519_private_key_from_root_raw(
                        malformed, path=path
                    )
        store = {
            "signing_key": {
                "private_key_path": str(path),
                "public_key_base64": base64.b64encode(public).decode("ascii"),
            }
        }
        with patch.object(core, "read_protected_file", return_value=raw):
            core._load_private_key(store)
            store["signing_key"]["public_key_base64"] = base64.b64encode(
                b"\x00" * 32
            ).decode("ascii")
            with self.assertRaises(BrokerBoundaryError) as mismatch:
                core._load_private_key(store)
        self.assertEqual(mismatch.exception.code, "u10_signing_key_public_mismatch")

    def test_store_activation_rechecks_current_selector_metadata_and_private_key(
        self,
    ) -> None:
        key_id = "00000000-0000-4000-8000-000000000001"
        private_path = core.KEY_ROOT / "generations" / key_id / "private.ed25519"
        public_base64 = base64.b64encode(b"p" * 32).decode("ascii")
        metadata = {
            "key_id": key_id,
            "public_key": {"value": public_base64},
        }
        metadata_ref = {"key_id": key_id, "locator": "metadata"}
        selector_ref = {"selector_id": "selector.key-v2", "locator": "selector"}
        replay = {
            "current_selector": {"state": "active"},
            "current_selector_ref": selector_ref,
            "active_key": {
                "public_metadata": metadata,
                "public_metadata_ref": metadata_ref,
                "private_material_ref": {"locator": str(private_path)},
            },
        }
        projection = {
            "key_id": key_id,
            "key_state": "active",
            "algorithm": "ed25519",
            "public_key_base64": public_base64,
            "private_key_path": str(private_path),
            "private_key_owner_uid": 0,
            "private_key_owner_gid": 0,
            "private_key_mode": "0600",
            "key_usage": "u10_broker_execution_attestation_only",
        }
        store = {"signing_key": projection}
        basis = {
            "schema_version": "semantic-guard-u10-store-activation-basis/v2",
            "signing_key_ref": metadata_ref,
            "signing_key_selector_ref": selector_ref,
            "store_content": {"signing_key": projection},
        }
        sentinel = object()
        with (
            patch.object(
                core,
                "resolve_current_signing_key_chain_v2_under_trust_store_lock",
                return_value=replay,
            ),
            patch.object(core, "_load_private_key", return_value=sentinel),
        ):
            observed = core._validate_current_signing_key_for_store_activation_v2(
                store, basis
            )
        self.assertIs(observed, sentinel)

        changed_basis = copy.deepcopy(basis)
        changed_basis["signing_key_selector_ref"] = {
            "selector_id": "selector.stale",
            "locator": "selector-stale",
        }
        with (
            patch.object(
                core,
                "resolve_current_signing_key_chain_v2_under_trust_store_lock",
                return_value=replay,
            ),
            self.assertRaises(BrokerBoundaryError) as stale,
        ):
            core._validate_current_signing_key_for_store_activation_v2(
                store, changed_basis
            )
        self.assertEqual(
            stale.exception.code,
            "u10_store_activation_signing_key_chain_mismatch",
        )

        with self.assertRaises(BrokerBoundaryError) as legacy:
            core._validate_current_signing_key_for_store_activation_v1({}, {})
        self.assertEqual(
            legacy.exception.code, "u10_legacy_key_selector_read_only"
        )


if __name__ == "__main__":
    unittest.main()
