from __future__ import annotations

import copy
from contextlib import ExitStack, nullcontext
from datetime import datetime
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import semantic_guard_u10_broker.core as core
from semantic_guard_u10_broker.protected_io import BrokerBoundaryError
from candidate_tests.u10_publisher_contract_fixture import publisher_contract_binding


def _digest(label: str) -> dict[str, str]:
    return core.digest_bytes(label.encode("utf-8"))


def _seal(value: dict, field: str) -> dict:
    sealed = copy.deepcopy(value)
    sealed.pop(field, None)
    sealed[field] = core.digest_bytes(core.canonical_json_bytes(sealed))
    return sealed


class U10RevocationTransactionTests(unittest.TestCase):
    def _store(self, root: Path) -> tuple[dict, bytes, dict]:
        activation_receipt = {
            "receipt_id": "receipt.authorization.store-test",
            "receipt_digest": _digest("activation-receipt"),
            "publication_observed_at": "2026-07-19T00:00:00Z",
            "receipt_recorded_at": "2026-07-19T00:00:30Z",
        }
        store = {
            "store_id": "store.u10.revocation-test",
            "store_revision_id": "revision.u10.revocation-test",
            "store_version": "2.0.0",
            "store_activation_basis_digest": _digest("store-basis"),
            "store_digest": _digest("store-semantic"),
            "lifecycle_state": "active",
            "current_selector": {
                "path": str(core.TRUST_STORE_PATH),
                "publication_policy": (
                    "history_fsync_before_atomic_current_replace/v1"
                ),
                "activation_ledger_path": str(core.STORE_ACTIVATION_LEDGER_ROOT),
                "activation_ledger_policy": (
                    "authorization_id_interval_receipt_atomic_publish/v3"
                ),
                "activation_ledger_retention_policy": (
                    "no_automatic_deletion_while_store_revision_is_retained/v1"
                ),
                "revocation_selector_path": str(root / "current-revocation.json"),
                "revocation_history_path": str(root / "history"),
                "revocation_ledger_path": str(root / "ledger"),
                "revocation_ledger_policy": (
                    "authorization_id_interval_receipt_atomic_publish/v2"
                ),
                "revocation_ledger_retention_policy": (
                    "no_automatic_deletion_while_store_revision_is_retained/v1"
                ),
                "revocation_decision_root_path": str(root / "authorizations"),
                "revocation_decision_entry_policy": (
                    "fixed_root_record_id_resolution_no_caller_raw/v1"
                ),
                "revocation_publication_policy": (
                    "decision_consumption_history_selector_interval_"
                    "receipt_recovery/v4"
                ),
            },
        }
        store["store_activation_basis_digest"] = (
            core.store_activation_basis_digest_v2(store)
        )
        raw = core.canonical_json_bytes(store)
        return store, raw, activation_receipt

    def _decision(
        self,
        store: dict,
        store_raw: bytes,
        activation_receipt: dict,
        *,
        revocation_id: str = "revocation.u10.test",
    ) -> dict:
        value = {
            "schema_version": "semantic-guard-u10-store-revocation-record/v1",
            "revocation_id": revocation_id,
            "revocation_version": "1.0.0",
            "record_kind": "store_revocation",
            "human_decision": "accept",
            "decision_owner": "human",
            "target_store_id": store["store_id"],
            "target_store_revision_id": store["store_revision_id"],
            "target_store_version": store["store_version"],
            "target_store_activation_basis_digest": copy.deepcopy(
                store["store_activation_basis_digest"]
            ),
            "target_store_artifact_digest": core.digest_bytes(store_raw),
            "target_store_digest": copy.deepcopy(store["store_digest"]),
            "target_activation_receipt_ref": copy.deepcopy(activation_receipt),
            "revoked_operation": "revoke_exact_store_revision",
            "decision_entry_profile": "fixed_root_authorization_record/v1",
            "recorded_at": "2026-07-19T00:01:00Z",
            "reason": "adversarial transaction test",
            "u4_principal_authenticity": "unresolved",
            "authority_scope": "u10_store_revocation_only",
            "formal_authority": "human_revocation_decision_only",
            "positive_assurance_allowed": False,
        }
        return _seal(value, "revocation_digest")

    def _fake_root_lstat(self, real_lstat):
        def observed(path: Path):
            value = real_lstat(path)
            fields = list(value)
            fields[4] = 0
            fields[5] = 0
            return os.stat_result(fields)

        return observed

    def _transaction_context(self, root: Path, store: dict, store_raw: bytes, receipt: dict):
        real_lstat = Path.lstat
        live_validate = core._validate

        def read_test_record(path: Path, **_kwargs) -> bytes:
            try:
                return Path(path).read_bytes()
            except OSError as exc:
                raise BrokerBoundaryError("protected_file_unavailable", str(path)) from exc

        def validate_with_fixed_production_locators(value, schema_name, code):
            if schema_name != "u10-store-revocation-publication-receipt-v2.schema.json":
                return live_validate(value, schema_name, code)
            projected = copy.deepcopy(value)
            digest = projected["history_ref"]["artifact_digest"]["value"]
            projected["history_ref"]["locator"] = (
                "/Library/Application Support/semantic-guard/u10/"
                f"revocations/sha256/{digest}.json"
            )
            projected["selector_path"] = (
                "/Library/Application Support/semantic-guard/u10/"
                "trust-store-current-revocation.json"
            )
            return live_validate(projected, schema_name, code)

        stack = ExitStack()
        binding = publisher_contract_binding()
        stack.enter_context(patch.object(core, "U10_ROOT", root))
        stack.enter_context(
            patch.object(core, "AUTHORIZATION_ROOT", root / "authorizations")
        )
        stack.enter_context(patch.object(core, "REVOCATION_ROOT", root / "history"))
        stack.enter_context(
            patch.object(core, "REVOCATION_LEDGER_ROOT", root / "ledger")
        )
        stack.enter_context(
            patch.object(core, "REVOCATION_SELECTOR_PATH", root / "current-revocation.json")
        )
        stack.enter_context(patch.object(core.os, "geteuid", return_value=0))
        stack.enter_context(
            patch.object(
                core,
                "_validate_publisher_contract_binding_v1",
                return_value=binding,
            )
        )
        stack.enter_context(
            patch.object(
                core,
                "publish_store_revocation_record_v1",
                side_effect=lambda identifier: core.publish_store_revocation_by_id_v1(
                    identifier,
                    publisher_contract_binding=binding,
                ),
            )
        )
        stack.enter_context(
            patch.object(core, "trust_store_coordination_lock", return_value=nullcontext())
        )
        stack.enter_context(
            patch.object(
                core,
                "load_fixed_root_trust_store_record_v2",
                return_value=(store, store_raw),
            )
        )
        stack.enter_context(
            patch.object(
                core,
                "_load_complete_store_activation_chain_v1",
                return_value=({}, {}, receipt),
            )
        )
        stack.enter_context(
            patch.object(
                core,
                "_validate_store_activation_authorization_v1",
                return_value={"authorization_id": "authorization.store-test"},
            )
        )
        stack.enter_context(
            patch.object(
                core, "_cleanup_activation_transaction_temporaries_under_lock_v1"
            )
        )
        stack.enter_context(
            patch.object(
                core,
                "load_historical_root_trust_store_v2",
                return_value=(store, store_raw),
            )
        )
        stack.enter_context(patch.object(core, "_verify_declared_directory"))
        stack.enter_context(patch.object(core, "validate_directory_chain"))
        stack.enter_context(
            patch.object(
                core,
                "read_protected_file",
                side_effect=read_test_record,
            )
        )
        stack.enter_context(
            patch.object(core, "_validate", side_effect=validate_with_fixed_production_locators)
        )
        stack.enter_context(
            patch.object(Path, "lstat", autospec=True, side_effect=self._fake_root_lstat(real_lstat))
        )
        return stack

    def _prepare(self, root: Path) -> tuple[dict, bytes, dict, dict, bytes]:
        for path in (root / "authorizations", root / "history", root / "ledger"):
            path.mkdir(parents=True, mode=0o755, exist_ok=True)
        store, store_raw, activation_receipt = self._store(root)
        decision = self._decision(store, store_raw, activation_receipt)
        decision_raw = core.canonical_json_bytes(decision)
        decision_path = root / "authorizations" / f"{decision['revocation_id']}.json"
        decision_path.write_bytes(decision_raw)
        decision_path.chmod(0o444)
        return store, store_raw, activation_receipt, decision, decision_raw

    def test_fixed_decision_is_consumed_then_published_with_occurrence_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            store, store_raw, activation_receipt, decision, decision_raw = self._prepare(root)
            with self._transaction_context(root, store, store_raw, activation_receipt):
                result = core.publish_store_revocation_record_v1(
                    decision["revocation_id"]
                )
                self.assertEqual(result["publication_status"], "published_exact_revocation")
                self.assertEqual((root / "current-revocation.json").read_bytes(), decision_raw)
                consumption = json.loads(
                    (root / "ledger" / f"{decision['revocation_id']}.consumption.json").read_text()
                )
                receipt = json.loads(
                    (root / "ledger" / f"{decision['revocation_id']}.receipt.json").read_text()
                )
                self.assertFalse(consumption["publication_occurred"])
                self.assertEqual(receipt["publisher_euid"], 0)
                self.assertLessEqual(
                    datetime.fromisoformat(consumption["consumed_at"].replace("Z", "+00:00")),
                    datetime.fromisoformat(
                        receipt["publication_observed_at"].replace("Z", "+00:00")
                    ),
                )
                repeated = core.publish_store_revocation_record_v1(
                    decision["revocation_id"]
                )
                self.assertEqual(repeated["publication_status"], "already_published_exact")

    def test_each_durable_boundary_recovers_only_the_same_transaction(self) -> None:
        boundaries = (
            "_write_revocation_consumption_under_lock_v1",
            "_seal_store_revocation_history_under_lock_v1",
            "_atomic_replace_v1",
            "_write_revocation_publication_receipt_under_lock_v1",
        )
        for boundary in boundaries:
            with self.subTest(boundary=boundary), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                store, store_raw, activation_receipt, decision, decision_raw = self._prepare(root)
                with self._transaction_context(root, store, store_raw, activation_receipt), ExitStack() as stack:
                    original = getattr(core, boundary)
                    raised = False

                    def crash_after_durable_write(*args, **kwargs):
                        nonlocal raised
                        result = original(*args, **kwargs)
                        relevant = boundary != "_atomic_replace_v1" or args[0] == root / "current-revocation.json"
                        if relevant and not raised:
                            raised = True
                            raise BrokerBoundaryError("injected_process_death", boundary)
                        return result

                    stack.enter_context(patch.object(core, boundary, side_effect=crash_after_durable_write))
                    with self.assertRaises(BrokerBoundaryError) as failed:
                        core.publish_store_revocation_record_v1(decision["revocation_id"])
                    self.assertEqual(failed.exception.code, "injected_process_death")
                    recovered = core.publish_store_revocation_record_v1(decision["revocation_id"])
                    self.assertIn(
                        recovered["publication_status"],
                        {
                            "published_exact_revocation",
                            "already_published_exact",
                            "publication_observed_and_receipt_recovered",
                        },
                    )
                    self.assertEqual((root / "current-revocation.json").read_bytes(), decision_raw)

    def test_caller_bytes_traversal_and_wrong_activation_receipt_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            store, store_raw, activation_receipt, decision, _decision_raw = self._prepare(root)
            with self._transaction_context(root, store, store_raw, activation_receipt):
                for invalid in (b"{}", "../forged", "nested/forged"):
                    with self.subTest(invalid=invalid), self.assertRaises(BrokerBoundaryError):
                        core.publish_store_revocation_record_v1(invalid)  # type: ignore[arg-type]

                changed = copy.deepcopy(decision)
                changed["target_activation_receipt_ref"]["receipt_digest"] = _digest(
                    "wrong-receipt"
                )
                changed = _seal(changed, "revocation_digest")
                path = root / "authorizations" / f"{decision['revocation_id']}.json"
                path.chmod(0o644)
                path.write_bytes(core.canonical_json_bytes(changed))
                path.chmod(0o444)
                with self.assertRaises(BrokerBoundaryError) as failed:
                    core.publish_store_revocation_record_v1(decision["revocation_id"])
                self.assertEqual(
                    failed.exception.code,
                    "u10_store_revocation_record_context_mismatch",
                )

    def test_history_without_receipt_is_incomplete_not_a_valid_revocation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            store, store_raw, activation_receipt, decision, decision_raw = self._prepare(root)
            history = root / "history" / f"{core.digest_bytes(decision_raw)['value']}.json"
            history.write_bytes(decision_raw)
            history.chmod(0o444)
            (root / "current-revocation.json").write_bytes(decision_raw)
            (root / "current-revocation.json").chmod(0o444)
            with self._transaction_context(root, store, store_raw, activation_receipt):
                with self.assertRaises(BrokerBoundaryError):
                    core.load_current_store_revocation_v1(
                        store,
                        store_raw,
                        activation_receipt=activation_receipt,
                    )

    def test_internal_link_crash_windows_are_cleaned_before_strict_loading(self) -> None:
        cases = ("consumption_post_link", "history_pre_link", "history_post_link")
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                store, store_raw, activation_receipt, decision, decision_raw = self._prepare(root)
                with self._transaction_context(root, store, store_raw, activation_receipt):
                    if case == "consumption_post_link":
                        core._write_revocation_consumption_under_lock_v1(
                            store,
                            store_raw,
                            decision,
                            activation_receipt,
                            publisher_contract_binding(),
                        )
                        final = root / "ledger" / f"{decision['revocation_id']}.consumption.json"
                        hidden = root / "ledger" / (
                            f".{decision['revocation_id']}.consumption.link-crash.tmp"
                        )
                        os.link(final, hidden)
                        self.assertEqual(final.stat().st_nlink, 2)
                    else:
                        digest = core.digest_bytes(decision_raw)["value"]
                        hidden = root / "history" / (
                            f".{digest}.revocation-history.crash.tmp"
                        )
                        hidden.write_bytes(decision_raw)
                        hidden.chmod(0o444)
                        if case == "history_post_link":
                            final = root / "history" / f"{digest}.json"
                            os.link(hidden, final)
                            self.assertEqual(final.stat().st_nlink, 2)
                    result = core.publish_store_revocation_record_v1(
                        decision["revocation_id"]
                    )
                    self.assertEqual(
                        result["publication_status"], "published_exact_revocation"
                    )
                    self.assertFalse(hidden.exists())

    def test_other_decision_cannot_steal_an_unfinished_consumed_transition(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            store, store_raw, activation_receipt, first, _first_raw = self._prepare(root)
            second = self._decision(
                store,
                store_raw,
                activation_receipt,
                revocation_id="revocation.u10.second",
            )
            second_path = root / "authorizations" / f"{second['revocation_id']}.json"
            second_path.write_bytes(core.canonical_json_bytes(second))
            second_path.chmod(0o444)
            with self._transaction_context(root, store, store_raw, activation_receipt):
                core._write_revocation_consumption_under_lock_v1(
                    store,
                    store_raw,
                    first,
                    activation_receipt,
                    publisher_contract_binding(),
                )
                with self.assertRaises(BrokerBoundaryError) as blocked:
                    core.publish_store_revocation_record_v1(second["revocation_id"])
                self.assertEqual(
                    blocked.exception.code,
                    "u10_competing_revocation_consumption_unresolved",
                )
                self.assertFalse(
                    (
                        root
                        / "ledger"
                        / f"{second['revocation_id']}.consumption.json"
                    ).exists()
                )

    def test_completed_revocation_pair_requires_cross_digest_and_monotonic_time(self) -> None:
        for mutation in ("consumption_digest", "publication_observed_at"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                store, store_raw, activation_receipt, decision, _raw = self._prepare(root)
                with self._transaction_context(root, store, store_raw, activation_receipt):
                    core.publish_store_revocation_record_v1(decision["revocation_id"])
                    receipt_path = (
                        root / "ledger" / f"{decision['revocation_id']}.receipt.json"
                    )
                    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
                    if mutation == "consumption_digest":
                        receipt["consumption_digest"] = _digest("other-consumption")
                    else:
                        receipt["publication_observed_at"] = (
                            "2026-07-18T23:59:00Z"
                        )
                    receipt = _seal(receipt, "receipt_digest")
                    receipt_path.chmod(0o644)
                    receipt_path.write_bytes(core.canonical_json_bytes(receipt))
                    receipt_path.chmod(0o444)
                    with self.assertRaises(BrokerBoundaryError) as blocked:
                        core.publish_store_revocation_record_v1(
                            decision["revocation_id"]
                        )
                    self.assertEqual(
                        blocked.exception.code,
                        "u10_store_revocation_ledger_record_context_mismatch",
                    )


if __name__ == "__main__":
    unittest.main()
