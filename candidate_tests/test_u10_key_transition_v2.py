from __future__ import annotations

from copy import deepcopy
from datetime import timedelta
import json
import os
from pathlib import Path
import tempfile
import unittest
import uuid

from candidate_tests.test_u10_initial_trust_provisioning import (
    KeyFixture,
    SCHEMA_ROOT,
    _publisher_binding,
    _timestamp,
    provisioner,
)


def _write_record(path: Path, value: dict, *, mode: int) -> bytes:
    raw = provisioner.json_record_bytes(value)
    path.write_bytes(raw)
    path.chmod(mode)
    return raw


def _replace_record(path: Path, value: dict, *, mode: int) -> bytes:
    path.chmod(0o600)
    return _write_record(path, value, mode=mode)


def _tree_snapshot(root: Path) -> tuple[tuple[object, ...], ...]:
    result: list[tuple[object, ...]] = []
    for path in sorted(root.rglob("*")):
        observed = path.lstat()
        relative = path.relative_to(root).as_posix()
        mode = observed.st_mode & 0o777
        if path.is_dir():
            result.append(("directory", relative, mode))
        else:
            result.append(("file", relative, mode, path.read_bytes()))
    return tuple(result)


def _replace_published_revocation(
    fixture: KeyFixture,
    revocation: dict,
) -> None:
    current = provisioner._load_current_selector_v2(fixture.paths, uid=fixture.uid)
    assert current is not None
    selector, _selector_raw, selector_ref = current
    assert selector["state"] == "no_active_key"
    authorization_id = selector["transition_evidence_selector"]["authorization_ref"][
        "authorization_id"
    ]
    receipt_path = fixture.paths.ledger_root / f"{authorization_id}.receipt.json"
    receipt = provisioner.strict_json_loads(receipt_path.read_bytes())

    revocation["revocation_digest"] = provisioner.sealed_digest(
        revocation, "revocation_digest"
    )
    revocation_raw = provisioner.json_record_bytes(revocation)
    revocation_ref = provisioner._revocation_ref_v2(
        revocation, revocation_raw, paths=fixture.paths
    )
    old_revocation_path = Path(selector["revocation_ref"]["locator"])
    new_revocation_path = Path(revocation_ref["locator"])
    revocation_directory = old_revocation_path.parent
    revocation_directory.chmod(0o700)
    if old_revocation_path != new_revocation_path:
        old_revocation_path.unlink()
        _write_record(new_revocation_path, revocation, mode=0o444)
    else:
        _replace_record(new_revocation_path, revocation, mode=0o444)
    revocation_directory.chmod(0o555)

    replacement_selector = deepcopy(selector)
    replacement_selector["revocation_ref"] = revocation_ref
    replacement_selector["selector_digest"] = provisioner.sealed_digest(
        replacement_selector, "selector_digest"
    )
    replacement_selector_raw = provisioner.json_record_bytes(replacement_selector)
    replacement_selector_ref = provisioner._selector_ref_v2(
        replacement_selector,
        replacement_selector_raw,
        paths=fixture.paths,
    )
    Path(selector_ref["locator"]).unlink()
    _write_record(
        Path(replacement_selector_ref["locator"]),
        replacement_selector,
        mode=0o444,
    )
    provisioner._atomic_replace(
        fixture.paths.selector_path,
        replacement_selector_raw,
        mode=0o444,
    )

    receipt["revocation_ref"] = revocation_ref
    receipt["published_selector_ref"] = replacement_selector_ref
    receipt["receipt_digest"] = provisioner.sealed_digest(receipt, "receipt_digest")
    _replace_record(receipt_path, receipt, mode=0o444)


def _install_legacy_v1_transition(
    fixture: KeyFixture,
    *,
    authorization_id: str,
    operation: str,
    key_id: str,
    expected_current_key_id: str | None,
) -> dict:
    authorization = {
        "schema_version": provisioner.KEY_AUTH_SCHEMA_V1,
        "authorization_id": authorization_id,
        "authorization_version": "1.0.0",
        "record_kind": "signing_key_operation_authorization",
        "key_operation": operation,
        "key_id": key_id,
        "key_entity_ref": f"旧署名鍵 {key_id}・{key_id}",
        "expected_current_key_id": expected_current_key_id,
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
        "recorded_at": _timestamp(timedelta(minutes=-5)),
        "not_before": _timestamp(timedelta(minutes=-4)),
        "expires_at": _timestamp(timedelta(hours=1)),
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
    authorization_ref = {
        "authorization_id": authorization_id,
        "authorization_digest": authorization["authorization_digest"],
    }
    binding = _publisher_binding()
    reserved_at = _timestamp(timedelta(minutes=-3))
    consumption = {
        "schema_version": provisioner.KEY_CONSUMPTION_SCHEMA_V1,
        "consumption_id": f"consumption.{authorization_id}",
        "record_kind": "key_operation_authorization_consumption",
        "authorization_ref": {
            **authorization_ref,
            "artifact_digest": provisioner.digest_bytes(authorization_raw),
        },
        "key_operation": operation,
        "key_id": key_id,
        "occurrence_id": (f"key.{authorization['authorization_digest']['value']}"),
        "publisher_contract_binding": binding,
        "reserved_at": reserved_at,
        "publication_occurred": False,
        "formal_authority": "none",
        "positive_assurance_allowed": False,
    }
    consumption["consumption_digest"] = provisioner.sealed_digest(
        consumption, "consumption_digest"
    )
    _write_record(
        fixture.paths.ledger_root / f"{authorization_id}.consumption.json",
        consumption,
        mode=0o400,
    )
    public_ref = None
    if operation in {"generate", "rotate"}:
        generation = fixture.paths.generation_root / key_id
        generation.mkdir(mode=0o700)
        private_type, encoding, private_format, public_format = (
            provisioner._load_cryptography()
        )
        private = private_type.generate()
        no_encryption = __import__(
            "cryptography.hazmat.primitives.serialization",
            fromlist=["NoEncryption"],
        ).NoEncryption()
        private_raw = private.private_bytes(
            encoding.Raw, private_format.Raw, no_encryption
        )
        public_raw = private.public_key().public_bytes(encoding.Raw, public_format.Raw)
        private_path = generation / "private.ed25519"
        private_path.write_bytes(private_raw)
        private_path.chmod(0o600)
        metadata = {
            "schema_version": provisioner.KEY_METADATA_SCHEMA_V1,
            "key_id": key_id,
            "key_entity_ref": authorization["key_entity_ref"],
            "record_kind": "signing_key_public_metadata",
            "algorithm": "Ed25519",
            "public_key": {
                "encoding": "raw_base64",
                "value": provisioner.base64.b64encode(public_raw).decode("ascii"),
            },
            "private_material": {
                "locator": str(private_path),
                "storage_state": "root_only_0600_not_exported",
            },
            "authorization_ref": authorization_ref,
            "generation_evidence_selector": (
                provisioner._generation_evidence_selector(
                    authorization_id, fixture.paths
                )
            ),
            "created_at": _timestamp(timedelta(minutes=-2)),
            "formal_authority": "none",
            "positive_assurance_allowed": False,
        }
        metadata["metadata_digest"] = provisioner.sealed_digest(
            metadata, "metadata_digest"
        )
        metadata_raw = _write_record(
            generation / "public-metadata.json", metadata, mode=0o444
        )
        generation.chmod(0o555)
        public_ref = provisioner._legacy_public_metadata_ref_v1(
            metadata, metadata_raw, paths=fixture.paths
        )
    else:
        revocation_directory = fixture.paths.revocation_root / key_id
        revocation_directory.mkdir(mode=0o700)
        revocation = {
            "schema_version": provisioner.KEY_REVOCATION_SCHEMA_V1,
            "revocation_id": f"revocation.{authorization_id}",
            "record_kind": "signing_key_revocation_occurrence",
            "key_id": key_id,
            "key_entity_ref": authorization["key_entity_ref"],
            "authorization_ref": authorization_ref,
            "revoked_at": _timestamp(timedelta(minutes=-2)),
            "private_material_disposition": (
                "retained_root_only_not_exported_pending_retention_policy"
            ),
            "formal_authority": "none",
            "positive_assurance_allowed": False,
        }
        revocation["revocation_digest"] = provisioner.sealed_digest(
            revocation, "revocation_digest"
        )
        _write_record(
            revocation_directory / f"{authorization_id}.json",
            revocation,
            mode=0o444,
        )
        revocation_directory.chmod(0o555)

    selected_at = _timestamp(timedelta(minutes=-2))
    selector = {
        "schema_version": provisioner.KEY_SELECTOR_SCHEMA_V1,
        "selector_id": f"selector.{authorization_id}",
        "record_kind": "current_signing_key_selector",
        "transition_authorization_ref": authorization_ref,
        "state": "active" if operation != "revoke" else "no_active_key",
        "key_id": key_id if operation != "revoke" else None,
        "key_entity_ref": (
            authorization["key_entity_ref"] if operation != "revoke" else None
        ),
        "public_metadata_ref": public_ref,
        "selected_at": selected_at,
        "formal_authority": "none",
        "positive_assurance_allowed": False,
    }
    selector["selector_digest"] = provisioner.sealed_digest(selector, "selector_digest")
    selector_raw = provisioner.json_record_bytes(selector)
    selector_path = fixture.paths.selector_history_root / (
        f"{provisioner.digest_bytes(selector_raw)['value']}.json"
    )
    selector_path.write_bytes(selector_raw)
    selector_path.chmod(0o444)
    receipt = {
        "schema_version": provisioner.KEY_RECEIPT_SCHEMA_V1,
        "receipt_id": f"receipt.{authorization_id}",
        "record_kind": "signing_key_operation_occurrence",
        "occurrence_id": consumption["occurrence_id"],
        "authorization_ref": authorization_ref,
        "consumption_ref": {
            "consumption_id": consumption["consumption_id"],
            "consumption_digest": consumption["consumption_digest"],
        },
        "key_operation": operation,
        "key_id": key_id,
        "public_metadata_ref": public_ref,
        "generation_evidence_selector": (
            provisioner._generation_evidence_selector(authorization_id, fixture.paths)
            if operation != "revoke"
            else None
        ),
        "publisher_contract_binding": binding,
        "private_material_evidence": (
            "root_owned_0600_present_not_disclosed"
            if operation != "revoke"
            else "unchanged_not_disclosed"
        ),
        "publication_not_before": reserved_at,
        "publication_observed_at": selected_at,
        "receipt_recorded_at": _timestamp(timedelta(minutes=-1)),
        "publication_occurred": True,
        "key_state": ("active" if operation != "revoke" else "revoked_no_active_key"),
        "human_adoption_status": "pending",
        "u4_principal_authenticity": "unresolved",
        "formal_authority": "none",
        "positive_assurance_allowed": False,
    }
    receipt["receipt_digest"] = provisioner.sealed_digest(receipt, "receipt_digest")
    _write_record(
        fixture.paths.ledger_root / f"{authorization_id}.receipt.json",
        receipt,
        mode=0o444,
    )
    return {
        "authorization": authorization,
        "consumption": consumption,
        "selector": selector,
        "receipt": receipt,
    }


class U10KeyTransitionV2Tests(unittest.TestCase):
    def _assert_rejected_without_mutation(
        self,
        fixture: KeyFixture,
        authorization_id: str,
        pattern: str,
    ) -> None:
        before = _tree_snapshot(fixture.u10_root)
        with self.assertRaisesRegex(
            provisioner.U10ProvisioningError,
            pattern,
        ):
            fixture.execute(authorization_id, _publisher_binding())
        self.assertEqual(_tree_snapshot(fixture.u10_root), before)

    def test_fixed_lock_path_and_acquisition_order_without_create(self) -> None:
        self.assertEqual(
            provisioner.TRUST_STORE_LOCK_PATH,
            provisioner.U10_ROOT / "trust-store.lock",
        )
        with tempfile.TemporaryDirectory() as temporary:
            fixture = KeyFixture(Path(temporary).resolve())
            key_id = str(uuid.uuid4())
            fixture.authorize("key.lock.order", "generate", key_id, None)
            opened: list[tuple[Path, int]] = []
            original_open = provisioner.os.open

            def tracking_open(path, flags, *args, **kwargs):
                candidate = Path(path)
                if candidate in {
                    fixture.paths.trust_store_lock_path,
                    fixture.paths.lock_path,
                }:
                    opened.append((candidate, flags))
                return original_open(path, flags, *args, **kwargs)

            provisioner.os.open = tracking_open
            try:
                fixture.execute("key.lock.order", _publisher_binding())
            finally:
                provisioner.os.open = original_open
            self.assertEqual(
                [path for path, _flags in opened[:2]],
                [
                    fixture.paths.trust_store_lock_path,
                    fixture.paths.lock_path,
                ],
            )
            for _path, flags in opened[:2]:
                self.assertEqual(flags & os.O_CREAT, 0)

    def test_both_lock_files_must_preexist(self) -> None:
        for attribute in ("trust_store_lock_path", "lock_path"):
            with (
                self.subTest(lock=attribute),
                tempfile.TemporaryDirectory() as temporary,
            ):
                fixture = KeyFixture(Path(temporary).resolve())
                missing = getattr(fixture.paths, attribute)
                missing.unlink()
                key_id = str(uuid.uuid4())
                fixture.authorize(f"key.missing.{attribute}", "generate", key_id, None)
                with self.assertRaisesRegex(
                    provisioner.U10ProvisioningError,
                    "u10_key_lock_missing",
                ):
                    fixture.execute(f"key.missing.{attribute}", _publisher_binding())
                self.assertFalse(missing.exists())

    def test_v1_authorization_is_read_only_and_never_consumed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = KeyFixture(Path(temporary).resolve())
            key_id = str(uuid.uuid4())
            value = fixture.authorize("key.legacy", "generate", key_id, None)
            value["schema_version"] = provisioner.KEY_AUTH_SCHEMA_V1
            value["authorization_version"] = "1.0.0"
            value["authorized_operation"] = "apply_exact_key_lifecycle_transition"
            value.pop("transition_mode")
            value.pop("prior_selector_ref")
            value["authorization_digest"] = provisioner.sealed_digest(
                value, "authorization_digest"
            )
            path = fixture.paths.authorization_root / "key.legacy.json"
            path.chmod(0o600)
            path.write_bytes(provisioner.json_record_bytes(value))
            path.chmod(0o400)
            with self.assertRaisesRegex(
                provisioner.U10ProvisioningError,
                "u10_key_legacy_authorization_read_only",
            ):
                fixture.execute("key.legacy", _publisher_binding())
            self.assertFalse(
                (fixture.paths.ledger_root / "key.legacy.consumption.json").exists()
            )

    def test_authorization_requires_exact_prior_selector_reference(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = KeyFixture(Path(temporary).resolve())
            first = str(uuid.uuid4())
            second = str(uuid.uuid4())
            fixture.authorize("key.prior.first", "generate", first, None)
            fixture.execute("key.prior.first", _publisher_binding())
            value = fixture.authorize("key.prior.second", "rotate", second, first)
            value["prior_selector_ref"]["selector_digest"] = {
                "algorithm": "sha256",
                "value": "f" * 64,
            }
            value["authorization_digest"] = provisioner.sealed_digest(
                value, "authorization_digest"
            )
            path = fixture.paths.authorization_root / "key.prior.second.json"
            path.chmod(0o600)
            path.write_bytes(provisioner.json_record_bytes(value))
            path.chmod(0o400)
            with self.assertRaisesRegex(
                provisioner.U10ProvisioningError,
                "u10_key_prior_selector_mismatch",
            ):
                fixture.execute("key.prior.second", _publisher_binding())

    def test_selector_rollback_and_branch_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = KeyFixture(Path(temporary).resolve())
            first = str(uuid.uuid4())
            second = str(uuid.uuid4())
            fixture.authorize("key.rollback.first", "generate", first, None)
            fixture.execute("key.rollback.first", _publisher_binding())
            first_current = provisioner._load_current_selector_v2(
                fixture.paths, uid=fixture.uid
            )
            self.assertIsNotNone(first_current)
            fixture.authorize("key.rollback.second", "rotate", second, first)
            fixture.execute("key.rollback.second", _publisher_binding())
            assert first_current is not None
            provisioner._atomic_replace(
                fixture.paths.selector_path, first_current[1], mode=0o444
            )
            with self.assertRaisesRegex(
                provisioner.U10ProvisioningError,
                "u10_key_selector_branch_or_rollback",
            ):
                provisioner.replay_key_transition_chain_v2(
                    paths=fixture.paths, required_uid=fixture.uid
                )

        with tempfile.TemporaryDirectory() as temporary:
            fixture = KeyFixture(Path(temporary).resolve())
            key_id = str(uuid.uuid4())
            fixture.authorize("key.branch", "generate", key_id, None)
            fixture.execute("key.branch", _publisher_binding())
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
            ref = provisioner._selector_ref_v2(branch, raw, paths=fixture.paths)
            provisioner._atomic_append_only(Path(ref["locator"]), branch, mode=0o444)
            with self.assertRaisesRegex(
                provisioner.U10ProvisioningError,
                "u10_key_selector_branch_or_rollback",
            ):
                provisioner.replay_key_transition_chain_v2(
                    paths=fixture.paths, required_uid=fixture.uid
                )

    def test_current_selector_must_match_history_raw_exactly(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = KeyFixture(Path(temporary).resolve())
            key_id = str(uuid.uuid4())
            fixture.authorize("key.history.raw", "generate", key_id, None)
            fixture.execute("key.history.raw", _publisher_binding())
            selector = json.loads(fixture.paths.selector_path.read_bytes())
            selector["selected_at"] = _timestamp(timedelta(seconds=2))
            selector["selector_digest"] = provisioner.sealed_digest(
                selector, "selector_digest"
            )
            provisioner._atomic_replace(
                fixture.paths.selector_path,
                provisioner.json_record_bytes(selector),
                mode=0o444,
            )
            with self.assertRaisesRegex(
                provisioner.U10ProvisioningError,
                "u10_file_unavailable",
            ):
                provisioner.replay_key_transition_chain_v2(
                    paths=fixture.paths, required_uid=fixture.uid
                )

    def test_crash_after_history_before_current_recovers(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = KeyFixture(Path(temporary).resolve())
            key_id = str(uuid.uuid4())
            authorization_id = "key.crash.history"
            fixture.authorize(authorization_id, "generate", key_id, None)
            original_replace = provisioner._atomic_replace
            failed = False

            def fail_selector_replace(path, raw, *, mode):
                nonlocal failed
                if path == fixture.paths.selector_path and not failed:
                    failed = True
                    raise provisioner.U10ProvisioningError(
                        "test_crash_before_current", str(path)
                    )
                return original_replace(path, raw, mode=mode)

            provisioner._atomic_replace = fail_selector_replace
            try:
                with self.assertRaisesRegex(
                    provisioner.U10ProvisioningError,
                    "test_crash_before_current",
                ):
                    fixture.execute(authorization_id, _publisher_binding())
            finally:
                provisioner._atomic_replace = original_replace
            self.assertFalse(fixture.paths.selector_path.exists())
            receipt = fixture.execute(authorization_id, _publisher_binding())
            self.assertEqual(receipt["key_state"], "active")
            replay = provisioner.replay_key_transition_chain_v2(
                paths=fixture.paths, required_uid=fixture.uid
            )
            self.assertEqual(replay["transition_count"], 1)

    def test_crash_after_current_before_receipt_recovers(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = KeyFixture(Path(temporary).resolve())
            key_id = str(uuid.uuid4())
            authorization_id = "key.crash.receipt"
            fixture.authorize(authorization_id, "generate", key_id, None)
            receipt_path = (
                fixture.paths.ledger_root / f"{authorization_id}.receipt.json"
            )
            original_append = provisioner._atomic_append_only
            failed = False

            def fail_receipt(path, record, *, mode):
                nonlocal failed
                if path == receipt_path and not failed:
                    failed = True
                    raise provisioner.U10ProvisioningError(
                        "test_crash_before_receipt", str(path)
                    )
                return original_append(path, record, mode=mode)

            provisioner._atomic_append_only = fail_receipt
            try:
                with self.assertRaisesRegex(
                    provisioner.U10ProvisioningError,
                    "test_crash_before_receipt",
                ):
                    fixture.execute(authorization_id, _publisher_binding())
            finally:
                provisioner._atomic_append_only = original_append
            self.assertTrue(fixture.paths.selector_path.exists())
            self.assertFalse(receipt_path.exists())
            receipt = fixture.execute(authorization_id, _publisher_binding())
            self.assertTrue(receipt["publication_occurred"])

    def test_replay_returns_active_refs_and_oldest_first_sequence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = KeyFixture(Path(temporary).resolve())
            first = str(uuid.uuid4())
            second = str(uuid.uuid4())
            fixture.authorize("key.replay.first", "generate", first, None)
            fixture.execute("key.replay.first", _publisher_binding())
            fixture.authorize("key.replay.second", "rotate", second, first)
            fixture.execute("key.replay.second", _publisher_binding())
            replay = provisioner.replay_key_transition_chain_v2(
                paths=fixture.paths, required_uid=fixture.uid
            )
            self.assertEqual(replay["transition_count"], 2)
            self.assertEqual(replay["active_key"]["key_id"], second)
            self.assertEqual(
                replay["active_key"]["private_material_ref"]["locator"],
                str(fixture.paths.generation_root / second / "private.ed25519"),
            )
            self.assertEqual(
                [item["transition_mode"] for item in replay["transition_sequence"]],
                ["initialize_empty_store", "rotate_active_key"],
            )
            self.assertNotIn("private_raw", replay["active_key"])

    def test_receipt_owns_exact_final_refs_without_digest_cycle(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = KeyFixture(Path(temporary).resolve())
            key_id = str(uuid.uuid4())
            authorization_id = "key.refs"
            fixture.authorize(authorization_id, "generate", key_id, None)
            receipt = fixture.execute(authorization_id, _publisher_binding())
            selector_raw = fixture.paths.selector_path.read_bytes()
            metadata_raw = (
                fixture.paths.generation_root / key_id / "public-metadata.json"
            ).read_bytes()
            self.assertNotIn(b"receipt_digest", selector_raw)
            self.assertNotIn(b"receipt_digest", metadata_raw)
            selector = json.loads(selector_raw)
            self.assertEqual(
                receipt["published_selector_ref"],
                provisioner._selector_ref_v2(
                    selector, selector_raw, paths=fixture.paths
                ),
            )
            self.assertEqual(
                receipt["public_metadata_ref"],
                selector["public_metadata_ref"],
            )

    def test_human_emergency_closure_unblocks_only_unpublished_transition(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = KeyFixture(Path(temporary).resolve())
            abandoned_key = str(uuid.uuid4())
            abandoned_id = "key.abandoned"
            fixture.authorize(abandoned_id, "generate", abandoned_key, None)
            original_crypto = provisioner._load_cryptography

            def fail_crypto():
                raise provisioner.U10ProvisioningError(
                    "test_abandon_before_material", abandoned_id
                )

            provisioner._load_cryptography = fail_crypto
            try:
                with self.assertRaisesRegex(
                    provisioner.U10ProvisioningError,
                    "test_abandon_before_material",
                ):
                    fixture.execute(abandoned_id, _publisher_binding())
            finally:
                provisioner._load_cryptography = original_crypto
            consumption_path = (
                fixture.paths.ledger_root / f"{abandoned_id}.consumption.json"
            )
            consumption_raw = consumption_path.read_bytes()
            consumption = json.loads(consumption_raw)
            closure = {
                "schema_version": provisioner.KEY_EMERGENCY_CLOSURE_SCHEMA,
                "closure_id": f"emergency-closure.{abandoned_id}",
                "record_kind": "key_transition_emergency_closure",
                "authorization_ref": consumption["authorization_ref"],
                "consumption_ref": {
                    "consumption_id": consumption["consumption_id"],
                    "locator": str(consumption_path),
                    "artifact_digest": provisioner.digest_bytes(consumption_raw),
                    "consumption_digest": consumption["consumption_digest"],
                },
                "prior_selector_ref": consumption["prior_selector_ref"],
                "published_selector_ref": None,
                "closure_disposition": "abandoned_before_publication",
                "closure_reason": "fixture-authorized abandonment",
                "human_decision": "accept_emergency_closure",
                "decision_owner": "human",
                "recorded_at": _timestamp(),
                "u4_principal_authenticity": "unresolved",
                "formal_authority": ("human_emergency_closure_decision_only"),
                "positive_assurance_allowed": False,
                "transition_success_claimed": False,
            }
            closure["closure_digest"] = provisioner.sealed_digest(
                closure, "closure_digest"
            )
            provisioner.validate_key_emergency_closure_v1(closure, paths=fixture.paths)
            closure_path = (
                fixture.paths.ledger_root / f"{abandoned_id}.emergency-closure.json"
            )
            closure_path.write_bytes(provisioner.json_record_bytes(closure))
            closure_path.chmod(0o444)
            replacement = str(uuid.uuid4())
            fixture.authorize("key.after.closure", "generate", replacement, None)
            receipt = fixture.execute("key.after.closure", _publisher_binding())
            self.assertEqual(receipt["key_id"], replacement)
            self.assertFalse(closure["transition_success_claimed"])

    def test_closed_ledger_denominator_rejects_anomalies_before_write(self) -> None:
        cases = {
            "unknown_suffix": "u10_key_transition_ledger_entry_unexpected",
            "unknown_schema": "u10_key_transition_ledger_schema_unknown",
            "orphan_authorization": ("u10_key_transition_unclosed_or_orphaned"),
            "orphan_consumption": "u10_key_transition_unclosed_or_orphaned",
            "orphan_receipt": "u10_key_transition_unclosed_or_orphaned",
            "wrong_kind_legacy": "u10_key_transition_ledger_schema_unknown",
        }
        for case, pattern in cases.items():
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temporary:
                fixture = KeyFixture(Path(temporary).resolve())
                selected_id = f"key.denominator.{case}"
                fixture.authorize(selected_id, "generate", str(uuid.uuid4()), None)
                if case == "unknown_suffix":
                    path = fixture.paths.ledger_root / "unexpected.record"
                    path.write_bytes(b"unexpected")
                    path.chmod(0o400)
                elif case == "unknown_schema":
                    _write_record(
                        fixture.paths.ledger_root / "unknown.authorization.json",
                        {"schema_version": "unknown/v999"},
                        mode=0o400,
                    )
                elif case == "orphan_authorization":
                    orphan = fixture.authorize(
                        "key.orphan.authorization",
                        "generate",
                        str(uuid.uuid4()),
                        None,
                    )
                    _write_record(
                        fixture.paths.ledger_root
                        / "key.orphan.authorization.authorization.json",
                        orphan,
                        mode=0o400,
                    )
                elif case == "orphan_consumption":
                    _write_record(
                        fixture.paths.ledger_root
                        / "key.orphan.consumption.consumption.json",
                        {"schema_version": provisioner.KEY_CONSUMPTION_SCHEMA},
                        mode=0o400,
                    )
                elif case == "orphan_receipt":
                    _write_record(
                        fixture.paths.ledger_root / "key.orphan.receipt.receipt.json",
                        {"schema_version": provisioner.KEY_RECEIPT_SCHEMA},
                        mode=0o444,
                    )
                else:
                    _write_record(
                        fixture.paths.ledger_root / "key.wrong.kind.consumption.json",
                        {"schema_version": provisioner.KEY_AUTH_SCHEMA_V1},
                        mode=0o400,
                    )
                self._assert_rejected_without_mutation(fixture, selected_id, pattern)

    def test_orphaned_v2_material_is_rejected_before_write(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = KeyFixture(Path(temporary).resolve())
            old_key = str(uuid.uuid4())
            fixture.authorize("key.material.old", "generate", old_key, None)
            fixture.execute("key.material.old", _publisher_binding())
            for path in tuple(fixture.paths.ledger_root.iterdir()):
                path.unlink()
            for path in tuple(fixture.paths.selector_history_root.iterdir()):
                path.unlink()
            fixture.paths.selector_path.unlink()
            selected_id = "key.material.new"
            fixture.authorize(selected_id, "generate", str(uuid.uuid4()), None)
            self._assert_rejected_without_mutation(
                fixture, selected_id, "u10_key_generation_orphaned"
            )

    def test_fake_v1_records_cannot_hide_behind_legacy_schema(self) -> None:
        cases = {
            "selector": "u10_key_selector_shape_invalid",
            "ledger": "u10_key_consumption_time_invalid",
            "metadata": "u10_key_metadata_shape_invalid",
            "revocation": "u10_key_revocation_shape_invalid",
        }
        for case, pattern in cases.items():
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temporary:
                fixture = KeyFixture(Path(temporary).resolve())
                selected_id = f"key.fake.v1.{case}"
                fixture.authorize(selected_id, "generate", str(uuid.uuid4()), None)
                if case == "selector":
                    value = {"schema_version": provisioner.KEY_SELECTOR_SCHEMA_V1}
                    raw = provisioner.json_record_bytes(value)
                    path = fixture.paths.selector_history_root / (
                        f"{provisioner.digest_bytes(raw)['value']}.json"
                    )
                    path.write_bytes(raw)
                    path.chmod(0o444)
                elif case == "ledger":
                    schemas = {
                        "authorization": provisioner.KEY_AUTH_SCHEMA_V1,
                        "consumption": provisioner.KEY_CONSUMPTION_SCHEMA_V1,
                        "receipt": provisioner.KEY_RECEIPT_SCHEMA_V1,
                    }
                    modes = {
                        "authorization": 0o400,
                        "consumption": 0o400,
                        "receipt": 0o444,
                    }
                    for kind, schema in schemas.items():
                        _write_record(
                            fixture.paths.ledger_root / f"key.fake.legacy.{kind}.json",
                            {"schema_version": schema},
                            mode=modes[kind],
                        )
                elif case == "metadata":
                    key_id = str(uuid.uuid4())
                    generation = fixture.paths.generation_root / key_id
                    generation.mkdir(mode=0o700)
                    private = generation / "private.ed25519"
                    private.write_bytes(b"x" * 32)
                    private.chmod(0o600)
                    _write_record(
                        generation / "public-metadata.json",
                        {"schema_version": provisioner.KEY_METADATA_SCHEMA_V1},
                        mode=0o444,
                    )
                    generation.chmod(0o555)
                else:
                    key_id = str(uuid.uuid4())
                    revocation = fixture.paths.revocation_root / key_id
                    revocation.mkdir(mode=0o700)
                    _write_record(
                        revocation / "key.fake.revocation.json",
                        {"schema_version": provisioner.KEY_REVOCATION_SCHEMA_V1},
                        mode=0o444,
                    )
                    revocation.chmod(0o555)
                self._assert_rejected_without_mutation(fixture, selected_id, pattern)

    def test_genuine_v1_history_remains_read_compatible(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = KeyFixture(Path(temporary).resolve())
            legacy_key = str(uuid.uuid4())
            rotated_key = str(uuid.uuid4())
            _install_legacy_v1_transition(
                fixture,
                authorization_id="key.legacy.generate",
                operation="generate",
                key_id=legacy_key,
                expected_current_key_id=None,
            )
            _install_legacy_v1_transition(
                fixture,
                authorization_id="key.legacy.rotate",
                operation="rotate",
                key_id=rotated_key,
                expected_current_key_id=legacy_key,
            )
            _install_legacy_v1_transition(
                fixture,
                authorization_id="key.legacy.revoke",
                operation="revoke",
                key_id=rotated_key,
                expected_current_key_id=rotated_key,
            )
            selected_id = "key.after.legacy"
            selected_key = str(uuid.uuid4())
            fixture.authorize(selected_id, "generate", selected_key, None)
            receipt = fixture.execute(selected_id, _publisher_binding())
            self.assertEqual(receipt["key_id"], selected_key)
            self.assertTrue(receipt["publication_occurred"])

    def test_legacy_v1_time_bindings_are_rejected_before_write(self) -> None:
        cases = {
            "publication": "u10_key_legacy_transition_chain_mismatch",
            "selector": "u10_key_legacy_selector_chain_mismatch",
        }
        for case, pattern in cases.items():
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temporary:
                fixture = KeyFixture(Path(temporary).resolve())
                legacy = _install_legacy_v1_transition(
                    fixture,
                    authorization_id=f"key.legacy.time.{case}",
                    operation="generate",
                    key_id=str(uuid.uuid4()),
                    expected_current_key_id=None,
                )
                authorization_id = legacy["authorization"]["authorization_id"]
                if case == "publication":
                    receipt = deepcopy(legacy["receipt"])
                    receipt["publication_not_before"] = _timestamp(
                        timedelta(minutes=-4)
                    )
                    receipt["receipt_digest"] = provisioner.sealed_digest(
                        receipt, "receipt_digest"
                    )
                    _replace_record(
                        fixture.paths.ledger_root / f"{authorization_id}.receipt.json",
                        receipt,
                        mode=0o444,
                    )
                else:
                    selector = deepcopy(legacy["selector"])
                    selector_raw = provisioner.json_record_bytes(selector)
                    old_path = fixture.paths.selector_history_root / (
                        f"{provisioner.digest_bytes(selector_raw)['value']}.json"
                    )
                    old_path.unlink()
                    selector["selected_at"] = _timestamp(timedelta(minutes=-1))
                    selector["selector_digest"] = provisioner.sealed_digest(
                        selector, "selector_digest"
                    )
                    selector_raw = provisioner.json_record_bytes(selector)
                    _write_record(
                        fixture.paths.selector_history_root
                        / f"{provisioner.digest_bytes(selector_raw)['value']}.json",
                        selector,
                        mode=0o444,
                    )
                selected_id = f"key.after.legacy.time.{case}"
                fixture.authorize(selected_id, "generate", str(uuid.uuid4()), None)
                self._assert_rejected_without_mutation(fixture, selected_id, pattern)

    def test_legacy_generation_denominator_is_closed(self) -> None:
        cases = {
            "extra_file": "u10_key_generation_denominator_mismatch",
            "missing_private": "u10_key_generation_denominator_mismatch",
            "bad_directory_name": ("u10_key_legacy_generation_identifier_mismatch"),
        }
        for case, pattern in cases.items():
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temporary:
                fixture = KeyFixture(Path(temporary).resolve())
                legacy_key = str(uuid.uuid4())
                _install_legacy_v1_transition(
                    fixture,
                    authorization_id="key.legacy.denominator",
                    operation="generate",
                    key_id=legacy_key,
                    expected_current_key_id=None,
                )
                generation = fixture.paths.generation_root / legacy_key
                if case == "extra_file":
                    generation.chmod(0o755)
                    extra = generation / "unexpected.bin"
                    extra.write_bytes(b"unexpected")
                    extra.chmod(0o444)
                    generation.chmod(0o555)
                elif case == "missing_private":
                    generation.chmod(0o755)
                    (generation / "private.ed25519").unlink()
                    generation.chmod(0o555)
                else:
                    generation.rename(
                        fixture.paths.generation_root / "wrong-generation-name"
                    )
                selected_id = f"key.after.legacy.{case}"
                fixture.authorize(selected_id, "generate", str(uuid.uuid4()), None)
                self._assert_rejected_without_mutation(fixture, selected_id, pattern)

    def test_legacy_revocation_denominator_is_closed(self) -> None:
        cases = {
            "extra_file": "u10_key_revocation_entry_unexpected",
            "missing_record": "u10_key_revocation_directory_orphaned",
            "bad_directory_name": ("u10_key_legacy_revocation_orphaned"),
        }
        for case, pattern in cases.items():
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temporary:
                fixture = KeyFixture(Path(temporary).resolve())
                legacy_key = str(uuid.uuid4())
                _install_legacy_v1_transition(
                    fixture,
                    authorization_id="key.legacy.generate",
                    operation="generate",
                    key_id=legacy_key,
                    expected_current_key_id=None,
                )
                _install_legacy_v1_transition(
                    fixture,
                    authorization_id="key.legacy.revoke",
                    operation="revoke",
                    key_id=legacy_key,
                    expected_current_key_id=legacy_key,
                )
                revocation = fixture.paths.revocation_root / legacy_key
                if case == "extra_file":
                    revocation.chmod(0o755)
                    extra = revocation / "unexpected.bin"
                    extra.write_bytes(b"unexpected")
                    extra.chmod(0o444)
                    revocation.chmod(0o555)
                elif case == "missing_record":
                    revocation.chmod(0o755)
                    (revocation / "key.legacy.revoke.json").unlink()
                    revocation.chmod(0o555)
                else:
                    revocation.rename(fixture.paths.revocation_root / str(uuid.uuid4()))
                selected_id = f"key.after.revocation.{case}"
                fixture.authorize(selected_id, "generate", str(uuid.uuid4()), None)
                self._assert_rejected_without_mutation(fixture, selected_id, pattern)

    def test_revocation_reference_cannot_switch_to_another_transition(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = KeyFixture(Path(temporary).resolve())
            key_id = str(uuid.uuid4())
            fixture.authorize("key.revocation.seed", "generate", key_id, None)
            fixture.execute("key.revocation.seed", _publisher_binding())
            authorization_id = "key.revocation.actual"
            fixture.authorize(authorization_id, "revoke", key_id, key_id)
            fixture.execute(authorization_id, _publisher_binding())
            selected_id = "key.revocation.after-detached"
            fixture.authorize(selected_id, "generate", str(uuid.uuid4()), None)

            revocation_path = (
                fixture.paths.revocation_root / key_id / f"{authorization_id}.json"
            )
            revocation = provisioner.strict_json_loads(revocation_path.read_bytes())
            detached_id = "key.revocation.detached"
            detached_authorization_ref = deepcopy(revocation["authorization_ref"])
            detached_authorization_ref["authorization_id"] = detached_id
            detached_authorization_ref["locator"] = str(
                fixture.paths.ledger_root / f"{detached_id}.authorization.json"
            )
            detached_consumption_ref = deepcopy(revocation["consumption_ref"])
            detached_consumption_ref["consumption_id"] = f"consumption.{detached_id}"
            detached_consumption_ref["locator"] = str(
                fixture.paths.ledger_root / f"{detached_id}.consumption.json"
            )
            revocation["revocation_id"] = f"revocation.{detached_id}"
            revocation["authorization_ref"] = detached_authorization_ref
            revocation["consumption_ref"] = detached_consumption_ref
            revocation["transition_evidence_selector"]["authorization_ref"] = (
                detached_authorization_ref
            )
            revocation["transition_evidence_selector"]["consumption_ref"] = (
                detached_consumption_ref
            )
            revocation["transition_evidence_selector"]["receipt_locator"] = str(
                fixture.paths.ledger_root / f"{detached_id}.receipt.json"
            )
            _replace_published_revocation(fixture, revocation)

            self._assert_rejected_without_mutation(
                fixture,
                selected_id,
                "u10_key_selector_v2_context_mismatch",
            )

    def test_revocation_internal_refs_must_match_selected_transition(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = KeyFixture(Path(temporary).resolve())
            key_id = str(uuid.uuid4())
            fixture.authorize("key.revocation.seed", "generate", key_id, None)
            fixture.execute("key.revocation.seed", _publisher_binding())
            authorization_id = "key.revocation.bound"
            fixture.authorize(authorization_id, "revoke", key_id, key_id)
            fixture.execute(authorization_id, _publisher_binding())
            selected_id = "key.revocation.after-ref-mismatch"
            fixture.authorize(selected_id, "generate", str(uuid.uuid4()), None)

            revocation_path = (
                fixture.paths.revocation_root / key_id / f"{authorization_id}.json"
            )
            revocation = provisioner.strict_json_loads(revocation_path.read_bytes())
            altered_authorization_ref = deepcopy(revocation["authorization_ref"])
            altered_authorization_ref["artifact_digest"] = {
                "algorithm": "sha256",
                "value": "a" * 64,
            }
            altered_authorization_ref["authorization_digest"] = {
                "algorithm": "sha256",
                "value": "b" * 64,
            }
            altered_consumption_ref = deepcopy(revocation["consumption_ref"])
            altered_consumption_ref["artifact_digest"] = {
                "algorithm": "sha256",
                "value": "c" * 64,
            }
            altered_consumption_ref["consumption_digest"] = {
                "algorithm": "sha256",
                "value": "d" * 64,
            }
            revocation["authorization_ref"] = altered_authorization_ref
            revocation["consumption_ref"] = altered_consumption_ref
            revocation["transition_evidence_selector"]["authorization_ref"] = (
                altered_authorization_ref
            )
            revocation["transition_evidence_selector"]["consumption_ref"] = (
                altered_consumption_ref
            )
            _replace_published_revocation(fixture, revocation)

            self._assert_rejected_without_mutation(
                fixture,
                selected_id,
                "u10_key_revocation_transition_mismatch",
            )

    def test_replay_reconstructs_complete_loaded_record_refs(self) -> None:
        for helper_name in ("_authorization_ref_v2", "_consumption_ref_v2"):
            with (
                self.subTest(helper=helper_name),
                tempfile.TemporaryDirectory() as temporary,
            ):
                fixture = KeyFixture(Path(temporary).resolve())
                key_id = str(uuid.uuid4())
                authorization_id = f"key.ref.{helper_name}"
                fixture.authorize(authorization_id, "generate", key_id, None)
                fixture.execute(authorization_id, _publisher_binding())
                current = provisioner._load_current_selector_v2(
                    fixture.paths, uid=fixture.uid
                )
                assert current is not None
                original = getattr(provisioner, helper_name)

                def altered_ref(*args, **kwargs):
                    observed = original(*args, **kwargs)
                    observed["locator"] += ".other"
                    return observed

                setattr(provisioner, helper_name, altered_ref)
                try:
                    with self.assertRaisesRegex(
                        provisioner.U10ProvisioningError,
                        "u10_key_transition_chain_mismatch",
                    ):
                        provisioner._read_transition_records_v2(
                            current[0],
                            current[2],
                            paths=fixture.paths,
                            uid=fixture.uid,
                            allow_missing_receipt=False,
                        )
                finally:
                    setattr(provisioner, helper_name, original)

    def test_metadata_internal_refs_must_match_selected_transition(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = KeyFixture(Path(temporary).resolve())
            key_id = str(uuid.uuid4())
            authorization_id = "key.metadata.bound"
            fixture.authorize(authorization_id, "generate", key_id, None)
            fixture.execute(authorization_id, _publisher_binding())
            current = provisioner._load_current_selector_v2(
                fixture.paths, uid=fixture.uid
            )
            assert current is not None
            selector = deepcopy(current[0])
            metadata_path = Path(selector["public_metadata_ref"]["locator"])
            metadata = provisioner.strict_json_loads(metadata_path.read_bytes())
            metadata["authorization_ref"]["artifact_digest"] = {
                "algorithm": "sha256",
                "value": "e" * 64,
            }
            metadata["transition_evidence_selector"]["authorization_ref"] = metadata[
                "authorization_ref"
            ]
            metadata["metadata_digest"] = provisioner.sealed_digest(
                metadata, "metadata_digest"
            )
            metadata_raw = _replace_record(metadata_path, metadata, mode=0o444)
            selector["public_metadata_ref"] = provisioner._public_metadata_ref_v2(
                metadata, metadata_raw, paths=fixture.paths
            )

            with self.assertRaisesRegex(
                provisioner.U10ProvisioningError,
                "u10_key_metadata_transition_mismatch",
            ):
                provisioner._read_transition_records_v2(
                    selector,
                    current[2],
                    paths=fixture.paths,
                    uid=fixture.uid,
                    allow_missing_receipt=False,
                )

    def test_receipt_times_must_match_reservation_and_selector(self) -> None:
        for field in ("publication_not_before", "publication_observed_at"):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temporary:
                fixture = KeyFixture(Path(temporary).resolve())
                key_id = str(uuid.uuid4())
                authorization_id = f"key.receipt.time.{field}"
                fixture.authorize(authorization_id, "generate", key_id, None)
                fixture.execute(authorization_id, _publisher_binding())
                current = provisioner._load_current_selector_v2(
                    fixture.paths, uid=fixture.uid
                )
                assert current is not None
                receipt_path = (
                    fixture.paths.ledger_root / f"{authorization_id}.receipt.json"
                )
                receipt = provisioner.strict_json_loads(receipt_path.read_bytes())
                if field == "publication_not_before":
                    receipt[field] = _timestamp(timedelta(minutes=-2))
                else:
                    receipt[field] = receipt["publication_not_before"]
                receipt["receipt_digest"] = provisioner.sealed_digest(
                    receipt, "receipt_digest"
                )
                _replace_record(receipt_path, receipt, mode=0o444)

                with self.assertRaisesRegex(
                    provisioner.U10ProvisioningError,
                    "u10_key_transition_receipt_chain_mismatch",
                ):
                    provisioner._read_transition_records_v2(
                        current[0],
                        current[2],
                        paths=fixture.paths,
                        uid=fixture.uid,
                        allow_missing_receipt=False,
                    )

    def test_receipt_rejects_revocation_ref_for_another_transition(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = KeyFixture(Path(temporary).resolve())
            key_id = str(uuid.uuid4())
            fixture.authorize("key.receipt.seed", "generate", key_id, None)
            fixture.execute("key.receipt.seed", _publisher_binding())
            authorization_id = "key.receipt.revoke"
            fixture.authorize(authorization_id, "revoke", key_id, key_id)
            fixture.execute(authorization_id, _publisher_binding())
            receipt_path = (
                fixture.paths.ledger_root / f"{authorization_id}.receipt.json"
            )
            receipt = provisioner.strict_json_loads(receipt_path.read_bytes())
            detached_id = "key.receipt.detached"
            receipt["revocation_ref"]["revocation_id"] = f"revocation.{detached_id}"
            receipt["revocation_ref"]["locator"] = str(
                fixture.paths.revocation_root / key_id / f"{detached_id}.json"
            )
            receipt["receipt_digest"] = provisioner.sealed_digest(
                receipt, "receipt_digest"
            )

            with self.assertRaisesRegex(
                provisioner.U10ProvisioningError,
                "u10_key_receipt_v2_context_mismatch",
            ):
                provisioner.validate_key_receipt_v2(receipt, paths=fixture.paths)

    def test_selector_schema_exports_public_metadata_ref_definition(self) -> None:
        schema = json.loads(
            (SCHEMA_ROOT / "u10-signing-key-selector-v2.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertIn("public_metadata_ref", schema["$defs"])


if __name__ == "__main__":
    unittest.main()
