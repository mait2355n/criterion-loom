from __future__ import annotations

import base64
from copy import deepcopy
from datetime import timedelta
import os
from pathlib import Path
import tempfile
import unittest
import uuid

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

import semantic_guard_u10_broker.core as core
from semantic_guard_u10_broker.protected_io import BrokerBoundaryError

try:
    from .test_u10_initial_trust_provisioning import (
        KeyFixture,
        _publisher_binding,
        _timestamp,
        provisioner,
    )
except ImportError:
    from candidate_tests.test_u10_initial_trust_provisioning import (
        KeyFixture,
        _publisher_binding,
        _timestamp,
        provisioner,
    )


def _paths(fixture: KeyFixture) -> core.KeyChainPaths:
    return core.KeyChainPaths(
        u10_root=fixture.paths.u10_root,
        ledger_root=fixture.paths.ledger_root,
        key_root=fixture.paths.key_root,
        generation_root=fixture.paths.generation_root,
        revocation_root=fixture.paths.revocation_root,
        selector_history_root=fixture.paths.selector_history_root,
        selector_path=fixture.paths.selector_path,
        lock_path=fixture.paths.lock_path,
    )


def _write_record(path: Path, value: dict, *, mode: int) -> bytes:
    raw = provisioner.json_record_bytes(value)
    if path.exists():
        path.chmod(0o600)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    path.chmod(mode)
    return raw


def _install_legacy_generate_history(
    fixture: KeyFixture,
    *,
    authorization_id: str = "key.legacy.complete",
) -> dict[str, object]:
    key_id = str(uuid.uuid4())
    key_entity_ref = f"旧署名鍵 {key_id}・{key_id}"
    authorization = {
        "schema_version": provisioner.KEY_AUTH_SCHEMA_V1,
        "authorization_id": authorization_id,
        "authorization_version": "1.0.0",
        "record_kind": "signing_key_operation_authorization",
        "key_operation": "generate",
        "key_id": key_id,
        "key_entity_ref": key_entity_ref,
        "expected_current_key_id": None,
        "target_generation_path": str(fixture.paths.generation_root / key_id),
        "target_public_metadata_path": str(
            fixture.paths.generation_root / key_id / "public-metadata.json"
        ),
        "target_private_key_path": str(
            fixture.paths.generation_root / key_id / "private.ed25519"
        ),
        "authorized_algorithm": "Ed25519",
        "authorized_operation": "apply_exact_key_lifecycle_transition",
        "human_decision": "accept",
        "decision_owner": "human",
        "recorded_at": _timestamp(timedelta(minutes=-10)),
        "not_before": _timestamp(timedelta(minutes=-9)),
        "expires_at": _timestamp(timedelta(minutes=10)),
        "u4_principal_authenticity": "unresolved",
        "authority_scope": "u10_signing_key_transition_only",
        "formal_authority": "human_key_transition_decision_only",
        "positive_assurance_allowed": False,
    }
    authorization["authorization_digest"] = provisioner.sealed_digest(
        authorization, "authorization_digest"
    )
    authorization_path = (
        fixture.paths.ledger_root / f"{authorization_id}.authorization.json"
    )
    authorization_raw = _write_record(authorization_path, authorization, mode=0o400)
    semantic_authorization_ref = {
        "authorization_id": authorization_id,
        "authorization_digest": authorization["authorization_digest"],
    }
    consumption = {
        "schema_version": provisioner.KEY_CONSUMPTION_SCHEMA_V1,
        "consumption_id": f"consumption.{authorization_id}",
        "record_kind": "key_operation_authorization_consumption",
        "authorization_ref": {
            **semantic_authorization_ref,
            "artifact_digest": provisioner.digest_bytes(authorization_raw),
        },
        "key_operation": "generate",
        "key_id": key_id,
        "occurrence_id": f"key.{authorization['authorization_digest']['value']}",
        "publisher_contract_binding": _publisher_binding(),
        "reserved_at": _timestamp(timedelta(minutes=-8)),
        "publication_occurred": False,
        "formal_authority": "none",
        "positive_assurance_allowed": False,
    }
    consumption["consumption_digest"] = provisioner.sealed_digest(
        consumption, "consumption_digest"
    )
    consumption_path = (
        fixture.paths.ledger_root / f"{authorization_id}.consumption.json"
    )
    _write_record(consumption_path, consumption, mode=0o400)
    evidence_selector = {
        "ledger_root": str(fixture.paths.ledger_root),
        "authorization_record": f"{authorization_id}.authorization.json",
        "consumption_record": f"{authorization_id}.consumption.json",
        "receipt_record": f"{authorization_id}.receipt.json",
        "resolution_policy": (
            "resolve_exact_generation_authorization_consumption_receipt/v1"
        ),
    }
    generation = fixture.paths.generation_root / key_id
    generation.mkdir()
    generation.chmod(0o700)
    private_raw = bytes(range(1, 33))
    private = Ed25519PrivateKey.from_private_bytes(private_raw)
    public_raw = private.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )
    private_path = generation / "private.ed25519"
    private_path.write_bytes(private_raw)
    private_path.chmod(0o600)
    metadata = {
        "schema_version": provisioner.KEY_METADATA_SCHEMA_V1,
        "key_id": key_id,
        "key_entity_ref": key_entity_ref,
        "record_kind": "signing_key_public_metadata",
        "algorithm": "Ed25519",
        "public_key": {
            "encoding": "raw_base64",
            "value": base64.b64encode(public_raw).decode("ascii"),
        },
        "private_material": {
            "locator": str(private_path),
            "storage_state": "root_only_0600_not_exported",
        },
        "authorization_ref": semantic_authorization_ref,
        "generation_evidence_selector": evidence_selector,
        "created_at": _timestamp(timedelta(minutes=-7)),
        "formal_authority": "none",
        "positive_assurance_allowed": False,
    }
    metadata["metadata_digest"] = provisioner.sealed_digest(metadata, "metadata_digest")
    metadata_path = generation / "public-metadata.json"
    metadata_raw = _write_record(metadata_path, metadata, mode=0o444)
    public_metadata_ref = {
        "key_id": key_id,
        "key_entity_ref": key_entity_ref,
        "metadata_locator": str(metadata_path),
        "metadata_artifact_digest": provisioner.digest_bytes(metadata_raw),
        "metadata_digest": metadata["metadata_digest"],
        "generation_authorization_ref": semantic_authorization_ref,
        "generation_receipt_selector": {
            "ledger_root": str(fixture.paths.ledger_root),
            "receipt_record": f"{authorization_id}.receipt.json",
            "resolution_policy": "resolve_exact_generation_receipt/v1",
        },
    }
    receipt = {
        "schema_version": provisioner.KEY_RECEIPT_SCHEMA_V1,
        "receipt_id": f"receipt.{authorization_id}",
        "record_kind": "signing_key_operation_occurrence",
        "occurrence_id": f"key.{authorization['authorization_digest']['value']}",
        "authorization_ref": semantic_authorization_ref,
        "consumption_ref": {
            "consumption_id": f"consumption.{authorization_id}",
            "consumption_digest": consumption["consumption_digest"],
        },
        "key_operation": "generate",
        "key_id": key_id,
        "public_metadata_ref": public_metadata_ref,
        "generation_evidence_selector": evidence_selector,
        "publisher_contract_binding": consumption["publisher_contract_binding"],
        "private_material_evidence": "root_owned_0600_present_not_disclosed",
        "publication_not_before": consumption["reserved_at"],
        "publication_observed_at": _timestamp(timedelta(minutes=-5)),
        "receipt_recorded_at": _timestamp(timedelta(minutes=-4)),
        "publication_occurred": True,
        "key_state": "active",
        "human_adoption_status": "pending",
        "u4_principal_authenticity": "unresolved",
        "formal_authority": "none",
        "positive_assurance_allowed": False,
    }
    receipt["receipt_digest"] = provisioner.sealed_digest(receipt, "receipt_digest")
    receipt_path = fixture.paths.ledger_root / f"{authorization_id}.receipt.json"
    _write_record(receipt_path, receipt, mode=0o444)
    selector = {
        "schema_version": provisioner.KEY_SELECTOR_SCHEMA_V1,
        "selector_id": f"selector.{authorization_id}",
        "record_kind": "current_signing_key_selector",
        "state": "active",
        "key_id": key_id,
        "key_entity_ref": key_entity_ref,
        "public_metadata_ref": public_metadata_ref,
        "transition_authorization_ref": semantic_authorization_ref,
        "selected_at": receipt["publication_observed_at"],
        "formal_authority": "none",
        "positive_assurance_allowed": False,
    }
    selector["selector_digest"] = provisioner.sealed_digest(selector, "selector_digest")
    selector_raw = provisioner.json_record_bytes(selector)
    selector_path = fixture.paths.selector_history_root / (
        f"{provisioner.digest_bytes(selector_raw)['value']}.json"
    )
    _write_record(selector_path, selector, mode=0o444)
    return {
        "authorization": authorization,
        "authorization_path": authorization_path,
        "consumption": consumption,
        "generation": generation,
        "metadata": metadata,
        "metadata_path": metadata_path,
        "receipt": receipt,
        "receipt_path": receipt_path,
        "selector": selector,
        "selector_path": selector_path,
    }


def _install_legacy_alias_history(
    fixture: KeyFixture,
    source: dict[str, object],
    *,
    authorization_id: str,
) -> None:
    """Install a second complete v1 chain that aliases the first metadata path."""

    authorization = deepcopy(source["authorization"])
    authorization["authorization_id"] = authorization_id
    authorization["authorization_digest"] = provisioner.sealed_digest(
        authorization, "authorization_digest"
    )
    authorization_path = (
        fixture.paths.ledger_root / f"{authorization_id}.authorization.json"
    )
    authorization_raw = _write_record(authorization_path, authorization, mode=0o400)
    authorization_ref = {
        "authorization_id": authorization_id,
        "authorization_digest": authorization["authorization_digest"],
    }

    consumption = deepcopy(source["consumption"])
    consumption["consumption_id"] = f"consumption.{authorization_id}"
    consumption["authorization_ref"] = {
        **authorization_ref,
        "artifact_digest": provisioner.digest_bytes(authorization_raw),
    }
    consumption["occurrence_id"] = (
        f"key.{authorization['authorization_digest']['value']}"
    )
    consumption["consumption_digest"] = provisioner.sealed_digest(
        consumption, "consumption_digest"
    )
    _write_record(
        fixture.paths.ledger_root / f"{authorization_id}.consumption.json",
        consumption,
        mode=0o400,
    )

    public_ref = deepcopy(source["receipt"])["public_metadata_ref"]
    public_ref["generation_authorization_ref"] = authorization_ref
    public_ref["generation_receipt_selector"]["receipt_record"] = (
        f"{authorization_id}.receipt.json"
    )
    evidence = deepcopy(source["receipt"])["generation_evidence_selector"]
    evidence["authorization_record"] = f"{authorization_id}.authorization.json"
    evidence["consumption_record"] = f"{authorization_id}.consumption.json"
    evidence["receipt_record"] = f"{authorization_id}.receipt.json"

    receipt = deepcopy(source["receipt"])
    receipt["receipt_id"] = f"receipt.{authorization_id}"
    receipt["occurrence_id"] = consumption["occurrence_id"]
    receipt["authorization_ref"] = authorization_ref
    receipt["consumption_ref"] = {
        "consumption_id": consumption["consumption_id"],
        "consumption_digest": consumption["consumption_digest"],
    }
    receipt["public_metadata_ref"] = public_ref
    receipt["generation_evidence_selector"] = evidence
    receipt["receipt_digest"] = provisioner.sealed_digest(receipt, "receipt_digest")
    _write_record(
        fixture.paths.ledger_root / f"{authorization_id}.receipt.json",
        receipt,
        mode=0o444,
    )

    selector = deepcopy(source["selector"])
    selector["selector_id"] = f"selector.{authorization_id}"
    selector["transition_authorization_ref"] = authorization_ref
    selector["public_metadata_ref"] = public_ref
    selector["selector_digest"] = provisioner.sealed_digest(selector, "selector_digest")
    selector_raw = provisioner.json_record_bytes(selector)
    selector_path = fixture.paths.selector_history_root / (
        f"{provisioner.digest_bytes(selector_raw)['value']}.json"
    )
    _write_record(selector_path, selector, mode=0o444)


class U10CoreKeyChainV2Tests(unittest.TestCase):
    def test_complete_v1_history_remains_read_only_compatible(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = KeyFixture(Path(temporary).resolve())
            current_key = str(uuid.uuid4())
            fixture.authorize("key.core.current", "generate", current_key, None)
            fixture.execute("key.core.current", _publisher_binding())
            legacy = _install_legacy_generate_history(fixture)

            replay = core.resolve_current_signing_key_chain_v2_under_trust_store_lock(
                paths=_paths(fixture), required_uid=fixture.uid
            )

            self.assertEqual(replay["transition_count"], 1)
            self.assertEqual(replay["active_key"]["key_id"], current_key)
            self.assertNotEqual(legacy["metadata"]["key_id"], current_key)

    def test_v1_publication_not_before_must_equal_reservation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = KeyFixture(Path(temporary).resolve())
            legacy = _install_legacy_generate_history(fixture)
            receipt = deepcopy(legacy["receipt"])
            receipt["publication_not_before"] = _timestamp(timedelta(minutes=-7))
            receipt["receipt_digest"] = provisioner.sealed_digest(
                receipt, "receipt_digest"
            )
            _write_record(legacy["receipt_path"], receipt, mode=0o444)

            with self.assertRaises(BrokerBoundaryError) as observed:
                core.resolve_current_signing_key_chain_v2_under_trust_store_lock(
                    paths=_paths(fixture), required_uid=fixture.uid
                )
            self.assertEqual(
                observed.exception.code,
                "u10_key_legacy_transition_context_mismatch",
            )

    def test_v1_selector_time_must_equal_publication_observation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = KeyFixture(Path(temporary).resolve())
            legacy = _install_legacy_generate_history(fixture)
            selector = deepcopy(legacy["selector"])
            legacy["selector_path"].unlink()
            selector["selected_at"] = _timestamp(timedelta(minutes=-3))
            selector["selector_digest"] = provisioner.sealed_digest(
                selector, "selector_digest"
            )
            selector_raw = provisioner.json_record_bytes(selector)
            selector_path = fixture.paths.selector_history_root / (
                f"{provisioner.digest_bytes(selector_raw)['value']}.json"
            )
            _write_record(selector_path, selector, mode=0o444)

            with self.assertRaises(BrokerBoundaryError) as observed:
                core.resolve_current_signing_key_chain_v2_under_trust_store_lock(
                    paths=_paths(fixture), required_uid=fixture.uid
                )
            self.assertEqual(
                observed.exception.code,
                "u10_key_legacy_selector_context_mismatch",
            )

    def test_v1_metadata_locator_cannot_be_shared_by_two_chains(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = KeyFixture(Path(temporary).resolve())
            legacy = _install_legacy_generate_history(
                fixture, authorization_id="key.z.actual"
            )
            _install_legacy_alias_history(
                fixture,
                legacy,
                authorization_id="key.a.alias",
            )

            with self.assertRaises(BrokerBoundaryError) as observed:
                core.resolve_current_signing_key_chain_v2_under_trust_store_lock(
                    paths=_paths(fixture), required_uid=fixture.uid
                )
            self.assertEqual(
                observed.exception.code,
                "u10_key_legacy_metadata_ref_duplicate",
            )

    def test_minimal_fake_v1_selector_history_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = KeyFixture(Path(temporary).resolve())
            key_id = str(uuid.uuid4())
            fixture.authorize("key.core.fake-selector", "generate", key_id, None)
            fixture.execute("key.core.fake-selector", _publisher_binding())
            fake = {"schema_version": provisioner.KEY_SELECTOR_SCHEMA_V1}
            raw = provisioner.json_record_bytes(fake)
            path = fixture.paths.selector_history_root / (
                f"{provisioner.digest_bytes(raw)['value']}.json"
            )
            _write_record(path, fake, mode=0o444)

            with self.assertRaises(BrokerBoundaryError) as observed:
                core.resolve_current_signing_key_chain_v2_under_trust_store_lock(
                    paths=_paths(fixture), required_uid=fixture.uid
                )
            self.assertEqual(observed.exception.code, "u10_key_legacy_selector_invalid")

    def test_v1_completed_ledger_without_selector_history_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = KeyFixture(Path(temporary).resolve())
            key_id = str(uuid.uuid4())
            fixture.authorize("key.core.missing-selector", "generate", key_id, None)
            fixture.execute("key.core.missing-selector", _publisher_binding())
            legacy = _install_legacy_generate_history(fixture)
            legacy["selector_path"].unlink()

            with self.assertRaises(BrokerBoundaryError) as observed:
                core.resolve_current_signing_key_chain_v2_under_trust_store_lock(
                    paths=_paths(fixture), required_uid=fixture.uid
                )
            self.assertEqual(
                observed.exception.code,
                "u10_key_legacy_selector_closure_mismatch",
            )

    def test_wrong_kind_v1_ledger_record_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = KeyFixture(Path(temporary).resolve())
            key_id = str(uuid.uuid4())
            fixture.authorize("key.core.wrong-kind", "generate", key_id, None)
            fixture.execute("key.core.wrong-kind", _publisher_binding())
            legacy = _install_legacy_generate_history(fixture)
            authorization = deepcopy(legacy["authorization"])
            authorization["record_kind"] = "key_operation_authorization_consumption"
            authorization["authorization_digest"] = provisioner.sealed_digest(
                authorization, "authorization_digest"
            )
            _write_record(legacy["authorization_path"], authorization, mode=0o400)

            with self.assertRaises(BrokerBoundaryError) as observed:
                core.resolve_current_signing_key_chain_v2_under_trust_store_lock(
                    paths=_paths(fixture), required_uid=fixture.uid
                )
            self.assertEqual(
                observed.exception.code, "u10_key_legacy_authorization_invalid"
            )

    def test_malformed_v1_generation_metadata_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = KeyFixture(Path(temporary).resolve())
            key_id = str(uuid.uuid4())
            fixture.authorize("key.core.bad-metadata", "generate", key_id, None)
            fixture.execute("key.core.bad-metadata", _publisher_binding())
            legacy = _install_legacy_generate_history(fixture)
            metadata = deepcopy(legacy["metadata"])
            metadata["metadata_digest"] = {
                "algorithm": "sha256",
                "value": "f" * 64,
            }
            _write_record(legacy["metadata_path"], metadata, mode=0o444)

            with self.assertRaises(BrokerBoundaryError) as observed:
                core.resolve_current_signing_key_chain_v2_under_trust_store_lock(
                    paths=_paths(fixture), required_uid=fixture.uid
                )
            self.assertEqual(
                observed.exception.code,
                "u10_key_legacy_metadata_seal_mismatch",
            )

    def test_extra_member_in_v1_generation_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = KeyFixture(Path(temporary).resolve())
            key_id = str(uuid.uuid4())
            fixture.authorize("key.core.extra", "generate", key_id, None)
            fixture.execute("key.core.extra", _publisher_binding())
            legacy = _install_legacy_generate_history(fixture)
            extra = legacy["generation"] / "unexpected.bin"
            extra.write_bytes(b"unexpected")
            extra.chmod(0o444)

            with self.assertRaises(BrokerBoundaryError) as observed:
                core.resolve_current_signing_key_chain_v2_under_trust_store_lock(
                    paths=_paths(fixture), required_uid=fixture.uid
                )
            self.assertEqual(
                observed.exception.code,
                "u10_key_generation_denominator_mismatch",
            )

    def test_minimal_fake_v1_revocation_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = KeyFixture(Path(temporary).resolve())
            key_id = str(uuid.uuid4())
            fixture.authorize("key.core.fake-revocation", "generate", key_id, None)
            fixture.execute("key.core.fake-revocation", _publisher_binding())
            legacy_key_id = str(uuid.uuid4())
            directory = fixture.paths.revocation_root / legacy_key_id
            directory.mkdir()
            directory.chmod(0o700)
            fake = {"schema_version": provisioner.KEY_REVOCATION_SCHEMA_V1}
            _write_record(directory / "key.legacy.revoke.json", fake, mode=0o444)

            with self.assertRaises(BrokerBoundaryError) as observed:
                core.resolve_current_signing_key_chain_v2_under_trust_store_lock(
                    paths=_paths(fixture), required_uid=fixture.uid
                )
            self.assertEqual(
                observed.exception.code, "u10_key_legacy_revocation_invalid"
            )

    def test_replays_oldest_first_without_private_bytes_or_store_relock(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = KeyFixture(Path(temporary).resolve())
            first = str(uuid.uuid4())
            second = str(uuid.uuid4())
            fixture.authorize("key.core.first", "generate", first, None)
            fixture.execute("key.core.first", _publisher_binding())
            fixture.authorize("key.core.second", "rotate", second, first)
            fixture.execute("key.core.second", _publisher_binding())
            private_raw = (
                fixture.paths.generation_root / second / "private.ed25519"
            ).read_bytes()
            opened: list[tuple[Path, int]] = []
            original_open = core.os.open

            def tracking_open(path, flags, *args, **kwargs):
                candidate = Path(path)
                if candidate in {
                    fixture.paths.lock_path,
                    fixture.paths.trust_store_lock_path,
                }:
                    opened.append((candidate, flags))
                return original_open(path, flags, *args, **kwargs)

            core.os.open = tracking_open
            try:
                replay = (
                    core.resolve_current_signing_key_chain_v2_under_trust_store_lock(
                        paths=_paths(fixture), required_uid=fixture.uid
                    )
                )
            finally:
                core.os.open = original_open
            self.assertEqual(replay["transition_count"], 2)
            self.assertEqual(replay["active_key"]["key_id"], second)
            self.assertEqual(
                [item["transition_mode"] for item in replay["transition_sequence"]],
                ["initialize_empty_store", "rotate_active_key"],
            )
            self.assertNotIn(private_raw, repr(replay).encode())
            self.assertEqual(
                [path for path, _flags in opened], [fixture.paths.lock_path]
            )
            self.assertEqual(opened[0][1] & os.O_CREAT, 0)

    def test_selector_branch_or_rollback_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = KeyFixture(Path(temporary).resolve())
            key_id = str(uuid.uuid4())
            fixture.authorize("key.core.branch", "generate", key_id, None)
            fixture.execute("key.core.branch", _publisher_binding())
            current = provisioner._load_current_selector_v2(
                fixture.paths, uid=fixture.uid
            )
            assert current is not None
            branch = deepcopy(current[0])
            branch["selected_at"] = _timestamp(timedelta(seconds=1))
            branch["selector_digest"] = provisioner.sealed_digest(
                branch, "selector_digest"
            )
            raw = provisioner.json_record_bytes(branch)
            reference = provisioner._selector_ref_v2(branch, raw, paths=fixture.paths)
            provisioner._atomic_append_only(
                Path(reference["locator"]), branch, mode=0o444
            )
            with self.assertRaises(BrokerBoundaryError) as observed:
                core.resolve_current_signing_key_chain_v2_under_trust_store_lock(
                    paths=_paths(fixture), required_uid=fixture.uid
                )
            self.assertEqual(
                observed.exception.code,
                "u10_key_selector_branch_or_rollback",
            )

    def test_missing_transition_receipt_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = KeyFixture(Path(temporary).resolve())
            key_id = str(uuid.uuid4())
            authorization_id = "key.core.receipt"
            fixture.authorize(authorization_id, "generate", key_id, None)
            fixture.execute(authorization_id, _publisher_binding())
            (fixture.paths.ledger_root / f"{authorization_id}.receipt.json").unlink()
            with self.assertRaises(BrokerBoundaryError) as observed:
                core.resolve_current_signing_key_chain_v2_under_trust_store_lock(
                    paths=_paths(fixture), required_uid=fixture.uid
                )
            self.assertEqual(
                observed.exception.code, "u10_key_transition_receipt_missing"
            )

    def test_private_public_key_replacement_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = KeyFixture(Path(temporary).resolve())
            key_id = str(uuid.uuid4())
            fixture.authorize("key.core.private", "generate", key_id, None)
            fixture.execute("key.core.private", _publisher_binding())
            private_path = fixture.paths.generation_root / key_id / "private.ed25519"
            private_path.chmod(0o600)
            private_path.write_bytes(b"x" * 32)
            private_path.chmod(0o600)
            with self.assertRaises(BrokerBoundaryError) as observed:
                core.resolve_current_signing_key_chain_v2_under_trust_store_lock(
                    paths=_paths(fixture), required_uid=fixture.uid
                )
            self.assertEqual(observed.exception.code, "u10_key_private_public_mismatch")


if __name__ == "__main__":
    unittest.main()
