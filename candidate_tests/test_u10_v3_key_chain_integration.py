from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import uuid

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

import semantic_guard_u10_broker.core as core
import semantic_guard_u10_broker.supervisor as supervisor

try:
    from .test_u10_initial_trust_provisioning import (
        KeyFixture,
        _publisher_binding,
        provisioner,
    )
except ImportError:
    from candidate_tests.test_u10_initial_trust_provisioning import (
        KeyFixture,
        _publisher_binding,
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


def _current_head(fixture: KeyFixture) -> dict:
    current = provisioner._load_current_selector_v2(fixture.paths, uid=fixture.uid)
    assert current is not None
    return current[2]


def _baseline_currency(status: str = "current") -> dict:
    return {
        "status": status,
        "observed_at": "2026-07-20T00:00:00Z",
        "current_store_ref": {"fixture": True},
        "current_entry_state": "active",
        "current_key_state": "active",
        "reason_codes": [],
    }


class U10V3KeyChainCurrencyTests(unittest.TestCase):
    def _assess(
        self,
        fixture: KeyFixture,
        *,
        historical_head: dict,
        historical_key_id: str,
        baseline_status: str = "current",
    ) -> dict:
        original_replay = (
            core.resolve_current_signing_key_chain_v2_under_trust_store_lock
        )
        lock_depth = 0

        @contextmanager
        def store_lock(*, exclusive: bool):
            nonlocal lock_depth
            self.assertFalse(exclusive)
            lock_depth += 1
            try:
                yield
            finally:
                lock_depth -= 1

        def replay():
            self.assertEqual(lock_depth, 1)
            return original_replay(paths=_paths(fixture), required_uid=fixture.uid)

        historical_store = {"signing_key": {"key_id": historical_key_id}}
        authorization = {"store_activation_basis_ref": {"record_id": "basis.fixture"}}
        basis = {"signing_key_selector_ref": historical_head}
        with (
            patch.object(
                core,
                "trust_store_coordination_lock",
                side_effect=store_lock,
            ),
            patch.object(
                core,
                "_assess_current_currency_v2",
                return_value=_baseline_currency(baseline_status),
            ),
            patch.object(
                core,
                "_validate_store_activation_authorization_v1",
                return_value=authorization,
            ),
            patch.object(
                core,
                "_load_store_activation_basis_v2",
                return_value=(basis, b"basis\n"),
            ),
            patch.object(
                core,
                "resolve_current_signing_key_chain_v2_under_trust_store_lock",
                side_effect=replay,
            ),
        ):
            result = core._assess_current_currency_v3({}, historical_store)
        self.assertEqual(lock_depth, 0)
        return result

    def test_v3_currency_tracks_current_revoke_rotate_and_generate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = KeyFixture(Path(temporary).resolve())
            first = str(uuid.uuid4())
            second = str(uuid.uuid4())
            third = str(uuid.uuid4())

            fixture.authorize("key.currency.first", "generate", first, None)
            fixture.execute("key.currency.first", _publisher_binding())
            first_head = _current_head(fixture)
            current = self._assess(
                fixture,
                historical_head=first_head,
                historical_key_id=first,
            )
            self.assertEqual(current["status"], "current")

            fixture.authorize("key.currency.rotate", "rotate", second, first)
            fixture.execute("key.currency.rotate", _publisher_binding())
            rotated = self._assess(
                fixture,
                historical_head=first_head,
                historical_key_id=first,
            )
            self.assertEqual(rotated["status"], "superseded")

            second_head = _current_head(fixture)
            fixture.authorize("key.currency.revoke", "revoke", second, second)
            fixture.execute("key.currency.revoke", _publisher_binding())
            revoked = self._assess(
                fixture,
                historical_head=second_head,
                historical_key_id=second,
            )
            self.assertEqual(revoked["status"], "revoked")

            no_active_head = _current_head(fixture)
            fixture.authorize("key.currency.third", "generate", third, None)
            fixture.execute("key.currency.third", _publisher_binding())
            regenerated = self._assess(
                fixture,
                historical_head=no_active_head,
                historical_key_id=second,
            )
            self.assertEqual(regenerated["status"], "superseded")

    def test_v3_currency_maps_unrelated_missing_and_corrupt_history_unresolved(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = KeyFixture(Path(temporary).resolve())
            key_id = str(uuid.uuid4())
            fixture.authorize("key.currency.gap", "generate", key_id, None)
            fixture.execute("key.currency.gap", _publisher_binding())
            current_head = _current_head(fixture)

            unrelated = dict(current_head)
            unrelated["selector_id"] = "selector.unrelated"
            result = self._assess(
                fixture,
                historical_head=unrelated,
                historical_key_id=key_id,
            )
            self.assertEqual(result["status"], "unresolved")
            self.assertEqual(
                result["reason_codes"],
                ["historical_key_selector_not_in_live_chain"],
            )

            history_path = Path(current_head["locator"])
            original_raw = history_path.read_bytes()
            history_path.unlink()
            missing = self._assess(
                fixture,
                historical_head=current_head,
                historical_key_id=key_id,
            )
            self.assertEqual(missing["status"], "unresolved")
            self.assertNotEqual(missing["reason_codes"], [])

            history_path.write_bytes(b"{}\n")
            history_path.chmod(0o444)
            corrupt = self._assess(
                fixture,
                historical_head=current_head,
                historical_key_id=key_id,
            )
            self.assertEqual(corrupt["status"], "unresolved")
            self.assertNotEqual(corrupt["reason_codes"], [])

            history_path.chmod(0o600)
            history_path.write_bytes(original_raw)
            history_path.chmod(0o444)


class U10V3KeyChainExecutionWiringTests(unittest.TestCase):
    def test_v3_envelope_builder_replays_key_chain_under_caller_store_lock(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = KeyFixture(Path(temporary).resolve())
            key_id = str(uuid.uuid4())
            fixture.authorize("key.builder.first", "generate", key_id, None)
            fixture.execute("key.builder.first", _publisher_binding())
            original_replay = (
                core.resolve_current_signing_key_chain_v2_under_trust_store_lock
            )
            replay = original_replay(paths=_paths(fixture), required_uid=fixture.uid)
            metadata = replay["active_key"]["public_metadata"]
            private_ref = replay["active_key"]["private_material_ref"]
            store_signing_key = {
                "key_id": key_id,
                "key_state": "active",
                "algorithm": "ed25519",
                "public_key_base64": metadata["public_key"]["value"],
                "private_key_path": private_ref["locator"],
                "private_key_owner_uid": 0,
                "private_key_owner_gid": 0,
                "private_key_mode": "0600",
                "key_usage": "u10_broker_execution_attestation_only",
            }
            store = {"signing_key": store_signing_key}
            basis = {
                "schema_version": "semantic-guard-u10-store-activation-basis/v2",
                "signing_key_ref": replay["active_key"]["public_metadata_ref"],
                "signing_key_selector_ref": replay["current_selector_ref"],
                "store_content": {"signing_key": store_signing_key},
            }
            trust_ref = {"fixture": "historical-store"}
            statement = {"key_id": key_id, "trust_store_ref": trust_ref}
            private_key = Ed25519PrivateKey.generate()
            lock_depth = 0
            replay_calls = 0
            opened_locks: list[Path] = []
            original_open = core.os.open

            @contextmanager
            def caller_store_lock():
                nonlocal lock_depth
                lock_depth += 1
                try:
                    yield
                finally:
                    lock_depth -= 1

            def replay_under_lock():
                nonlocal replay_calls
                self.assertEqual(lock_depth, 1)
                replay_calls += 1
                return original_replay(paths=_paths(fixture), required_uid=fixture.uid)

            def tracking_open(path, flags, *args, **kwargs):
                candidate = Path(path)
                if candidate in {
                    fixture.paths.lock_path,
                    fixture.paths.trust_store_lock_path,
                }:
                    opened_locks.append(candidate)
                return original_open(path, flags, *args, **kwargs)

            core.os.open = tracking_open
            try:
                with (
                    caller_store_lock(),
                    patch.object(
                        core,
                        "load_active_root_trust_store_for_execution_v2",
                        return_value=(store, b"store\n"),
                    ),
                    patch.object(
                        core,
                        "_validate_store_activation_authorization_v1",
                        return_value={
                            "store_activation_basis_ref": {"record_id": "basis.fixture"}
                        },
                    ),
                    patch.object(
                        core,
                        "_load_store_activation_basis_v2",
                        return_value=(basis, b"basis\n"),
                    ),
                    patch.object(
                        core,
                        "resolve_current_signing_key_chain_v2_under_trust_store_lock",
                        side_effect=replay_under_lock,
                    ),
                    patch.object(core, "_load_private_key", return_value=private_key),
                    patch.object(
                        core,
                        "derive_historical_store_ref_v2",
                        return_value=trust_ref,
                    ),
                    patch.object(
                        core,
                        "_verify_broker_attested_envelope_with_store_v3",
                        return_value={},
                    ),
                    patch.object(core, "_validate", return_value=None),
                ):
                    envelope = core._build_signed_envelope_v3(statement, store=store)
            finally:
                core.os.open = original_open
            self.assertEqual(envelope["schema_version"].rsplit("/", 1)[-1], "v3")
            self.assertEqual(replay_calls, 1)
            self.assertEqual(opened_locks, [fixture.paths.lock_path])

    def test_v3_execution_enters_key_replay_while_store_lock_is_held(self) -> None:
        class ReplayReached(RuntimeError):
            pass

        with tempfile.TemporaryDirectory() as temporary:
            fixture = KeyFixture(Path(temporary).resolve())
            key_id = str(uuid.uuid4())
            fixture.authorize("key.execution.first", "generate", key_id, None)
            fixture.execute("key.execution.first", _publisher_binding())
            original_replay = (
                core.resolve_current_signing_key_chain_v2_under_trust_store_lock
            )
            lock_depth = 0
            opened_locks: list[Path] = []
            original_open = core.os.open

            @contextmanager
            def store_lock(*, exclusive: bool):
                nonlocal lock_depth
                self.assertFalse(exclusive)
                lock_depth += 1
                try:
                    yield
                finally:
                    lock_depth -= 1

            def probe_v3_store_load():
                self.assertEqual(lock_depth, 1)
                original_replay(paths=_paths(fixture), required_uid=fixture.uid)
                raise ReplayReached

            def tracking_open(path, flags, *args, **kwargs):
                candidate = Path(path)
                if candidate in {
                    fixture.paths.lock_path,
                    fixture.paths.trust_store_lock_path,
                }:
                    opened_locks.append(candidate)
                return original_open(path, flags, *args, **kwargs)

            core.os.open = tracking_open
            try:
                with (
                    patch.object(
                        supervisor.os,
                        "geteuid",
                        side_effect=[0, fixture.uid],
                    ),
                    patch.object(
                        supervisor,
                        "trust_store_coordination_lock",
                        side_effect=store_lock,
                    ),
                    patch.object(
                        core, "validate_execution_request_v1", return_value=None
                    ),
                    patch.object(
                        core,
                        "load_active_root_trust_store_for_execution_v3",
                        side_effect=probe_v3_store_load,
                    ),
                ):
                    with self.assertRaises(ReplayReached):
                        supervisor.execute_root_broker_request_v3({"fixture": True})
            finally:
                core.os.open = original_open
            self.assertEqual(lock_depth, 0)
            self.assertEqual(opened_locks, [fixture.paths.lock_path])


if __name__ == "__main__":
    unittest.main()
