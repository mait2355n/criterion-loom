from __future__ import annotations

from contextlib import ExitStack
import copy
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


def _authorization(identifier: str) -> dict:
    return {
        "authorization_id": identifier,
        "transition_kind": "initial_activation",
        "prior_store_ref": None,
        "prior_revocation_ref": None,
    }


def _consumption(identifier: str) -> dict:
    basis_ref = {
        "record_id": f"store-basis.{identifier}",
        "locator": (
            "/Library/Application Support/semantic-guard/u10/"
            f"store-activation-bases/{identifier}.store-basis.json"
        ),
        "artifact_digest": _digest(f"store-basis-artifact:{identifier}"),
        "semantic_digest": _digest(f"store-basis-semantic:{identifier}"),
    }
    value = {
        "schema_version": (
            "semantic-guard-u10-store-activation-authorization-consumption/v1"
        ),
        "consumption_id": f"consumption.{identifier}",
        "record_kind": "activation_authorization_consumption",
        "public_operation": "activate-store",
        "public_identifier": identifier,
        "authorization_id": identifier,
        "authorization_digest": _digest(f"authorization:{identifier}"),
        "store_activation_basis_ref": basis_ref,
        "transition_kind": "initial_activation",
        "prior_store_ref": None,
        "prior_revocation_ref": None,
        "target_store_ref": {
            "store_id": "store.u10.activation-test",
            "store_revision_id": f"revision.{identifier}",
            "store_version": "2.0.0",
            "store_activation_basis_digest": _digest(f"basis:{identifier}"),
            "artifact_digest": _digest(f"artifact:{identifier}"),
            "semantic_digest": _digest(f"semantic:{identifier}"),
        },
        "publisher_contract_binding": publisher_contract_binding(),
        "reserved_at": "2026-07-19T00:01:00Z",
        "publication_occurred": False,
        "formal_authority": "none",
        "positive_assurance_allowed": False,
    }
    return _seal(value, "consumption_digest")


def _receipt(consumption: dict) -> dict:
    identifier = consumption["authorization_id"]
    value = {
        "schema_version": (
            "semantic-guard-u10-store-activation-transition-receipt/v2"
        ),
        "receipt_id": f"receipt.{identifier}",
        "record_kind": "activation_transition_occurrence",
        "public_operation": "activate-store",
        "public_identifier": identifier,
        "authorization_id": identifier,
        "authorization_digest": consumption["authorization_digest"],
        "consumption_digest": consumption["consumption_digest"],
        "store_activation_basis_ref": consumption[
            "store_activation_basis_ref"
        ],
        "transition_kind": consumption["transition_kind"],
        "prior_store_ref": consumption["prior_store_ref"],
        "prior_revocation_ref": consumption["prior_revocation_ref"],
        "activated_store_ref": consumption["target_store_ref"],
        "publisher_contract_binding": consumption[
            "publisher_contract_binding"
        ],
        "publication_not_before": consumption["reserved_at"],
        "publication_observed_at": "2026-07-19T00:02:00Z",
        "receipt_recorded_at": "2026-07-19T00:03:00Z",
        "formal_authority": "none",
        "positive_assurance_allowed": False,
    }
    return _seal(value, "receipt_digest")


class U10ActivationTransactionRecoveryTests(unittest.TestCase):
    def _context(self, ledger: Path) -> ExitStack:
        real_lstat = Path.lstat

        def root_lstat(path: Path):
            observed = real_lstat(path)
            fields = list(observed)
            fields[4] = 0
            fields[5] = 0
            return os.stat_result(fields)

        def read(path: Path, **_kwargs) -> bytes:
            try:
                return Path(path).read_bytes()
            except OSError as exc:
                raise BrokerBoundaryError("protected_file_unavailable", str(path)) from exc

        stack = ExitStack()
        stack.enter_context(
            patch.object(core, "STORE_ACTIVATION_LEDGER_ROOT", ledger)
        )
        stack.enter_context(patch.object(core, "_verify_declared_directory"))
        stack.enter_context(patch.object(core, "read_protected_file", side_effect=read))
        stack.enter_context(
            patch.object(Path, "lstat", autospec=True, side_effect=root_lstat)
        )
        return stack

    def test_other_authorization_cannot_steal_unfinished_prior_transition(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            ledger = Path(temporary)
            first = _consumption("authorization.first")
            first_path = ledger / "authorization.first.consumption.json"
            first_path.write_bytes(core.canonical_json_bytes(first))
            first_path.chmod(0o444)
            with self._context(ledger):
                core._assert_no_competing_activation_consumption_v1(
                    _authorization("authorization.first")
                )
                with self.assertRaises(BrokerBoundaryError) as blocked:
                    core._assert_no_competing_activation_consumption_v1(
                        _authorization("authorization.second")
                    )
                self.assertEqual(
                    blocked.exception.code,
                    "u10_competing_activation_consumption_unresolved",
                )

    def test_completed_other_transition_is_not_mislabelled_as_unfinished(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            ledger = Path(temporary)
            consumption = _consumption("authorization.first")
            receipt = _receipt(consumption)
            for suffix, value in (
                ("consumption", consumption),
                ("receipt", receipt),
            ):
                path = ledger / f"authorization.first.{suffix}.json"
                path.write_bytes(core.canonical_json_bytes(value))
                path.chmod(0o444)
            with self._context(ledger):
                core._assert_no_competing_activation_consumption_v1(
                    _authorization("authorization.second")
                )

    def test_link_crash_cleanup_restores_single_link_before_loader(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            ledger = Path(temporary)
            authorization_id = "authorization.link-crash"
            final = ledger / f"{authorization_id}.receipt.json"
            final.write_bytes(b"complete receipt bytes")
            final.chmod(0o444)
            hidden = ledger / f".{authorization_id}.receipt.linked.tmp"
            os.link(final, hidden)
            self.assertEqual(final.stat().st_nlink, 2)
            with self._context(ledger):
                core._cleanup_activation_transaction_temporaries_under_lock_v1(
                    authorization_id
                )
            self.assertFalse(hidden.exists())
            self.assertEqual(final.stat().st_nlink, 1)

    def test_completed_pair_requires_cross_digest_and_monotonic_time(self) -> None:
        for mutation in ("authorization_digest", "publication_observed_at"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary:
                ledger = Path(temporary)
                consumption = _consumption("authorization.first")
                receipt = _receipt(consumption)
                if mutation == "authorization_digest":
                    receipt["authorization_digest"] = _digest("other-authorization")
                else:
                    receipt["publication_observed_at"] = "2026-07-18T23:59:00Z"
                receipt = _seal(receipt, "receipt_digest")
                for suffix, value in (("consumption", consumption), ("receipt", receipt)):
                    path = ledger / f"authorization.first.{suffix}.json"
                    path.write_bytes(core.canonical_json_bytes(value))
                    path.chmod(0o444)
                with self._context(ledger), self.assertRaises(BrokerBoundaryError) as blocked:
                    core._assert_no_competing_activation_consumption_v1(
                        _authorization("authorization.second")
                    )
                self.assertEqual(
                    blocked.exception.code,
                    "u10_store_activation_ledger_record_context_mismatch",
                )


if __name__ == "__main__":
    unittest.main()
