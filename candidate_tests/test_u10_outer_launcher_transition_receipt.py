from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import stat
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import call, patch

from jsonschema import Draft202012Validator, FormatChecker
from candidate_tests.u10_publisher_contract_fixture import publisher_contract_binding


SCRIPT = Path(__file__).parent / "fixtures" / "scripts" / "u10_root_broker_outer_launcher.py"
SCHEMA_DIRECTORY = Path(__file__).parents[1] / "src" / "semantic_guard_vnext" / "validation" / "env-path-contracts"
SPEC = importlib.util.spec_from_file_location(
    "u10_root_broker_outer_launcher_transition_receipt_tests",
    SCRIPT,
)
assert SPEC is not None and SPEC.loader is not None
OUTER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(OUTER)


def _digest(label: str) -> dict[str, str]:
    return OUTER._digest(label.encode("utf-8"))


def _store() -> tuple[dict, bytes]:
    store = {
        "schema_version": "semantic-guard-u10-root-trust-store/v2",
        "store_id": "store.u10.outer-receipt-test",
        "store_revision_id": "store-revision.u10.outer-receipt-test",
        "store_version": "1.0.0",
        "current_selector": {
            "path": str(OUTER.CURRENT_STORE),
            "activation_ledger_path": str(OUTER.STORE_ACTIVATION_LEDGER_ROOT),
            "activation_ledger_policy": OUTER.STORE_ACTIVATION_LEDGER_POLICY,
            "activation_ledger_retention_policy": (
                OUTER.STORE_ACTIVATION_LEDGER_RETENTION_POLICY
            ),
            "revocation_selector_path": str(OUTER.REVOCATION_SELECTOR),
        },
        "lifecycle_state": "active",
        "positive_assurance_allowed": False,
    }
    store["store_activation_basis_digest"] = OUTER._store_activation_basis(store)
    store["store_digest"] = OUTER._sealed(store, "store_digest")
    return store, OUTER._canonical(store) + b"\n"


def _prior_store_ref(label: str = "prior") -> dict:
    return {
        "store_id": f"store.u10.{label}",
        "store_revision_id": f"store-revision.u10.{label}",
        "store_version": "0.9.0",
        "store_activation_basis_digest": _digest(f"{label}:basis"),
        "artifact_digest": _digest(f"{label}:artifact"),
        "semantic_digest": _digest(f"{label}:semantic"),
    }


def _prior_revocation_ref(label: str = "prior") -> dict:
    return {
        "revocation_id": f"revocation.u10.{label}",
        "artifact_digest": _digest(f"{label}:revocation-artifact"),
        "semantic_digest": _digest(f"{label}:revocation-semantic"),
    }


def _authorization(*, replacement: bool = False) -> dict:
    return {
        "authorization_id": "authorization.u10.outer-receipt-test",
        "authorization_digest": _digest("authorization"),
        "store_activation_basis_ref": {
            "record_id": "store-basis.outer-receipt-test",
            "locator": (
                "/Library/Application Support/semantic-guard/u10/"
                "store-activation-bases/authorization.snapshot.outer."
                "store-basis.json"
            ),
            "artifact_digest": _digest("store-basis-artifact"),
            "semantic_digest": _digest("store-basis-semantic"),
        },
        "recorded_at": "2026-07-19T23:59:59Z",
        "transition_kind": (
            "replace_current_revision" if replacement else "initial_activation"
        ),
        "prior_store_ref": _prior_store_ref() if replacement else None,
        "prior_revocation_ref": _prior_revocation_ref() if replacement else None,
    }


def _consumption(
    store: dict,
    store_raw: bytes,
    authorization: dict,
) -> dict:
    value = {
        "schema_version": (
            "semantic-guard-u10-store-activation-authorization-consumption/v1"
        ),
        "consumption_id": f"consumption.{authorization['authorization_id']}",
        "record_kind": "activation_authorization_consumption",
        "public_operation": "activate-store",
        "public_identifier": authorization["authorization_id"],
        "authorization_id": authorization["authorization_id"],
        "authorization_digest": authorization["authorization_digest"],
        "store_activation_basis_ref": authorization[
            "store_activation_basis_ref"
        ],
        "transition_kind": authorization["transition_kind"],
        "prior_store_ref": authorization["prior_store_ref"],
        "prior_revocation_ref": authorization["prior_revocation_ref"],
        "target_store_ref": OUTER._store_transition_ref(store, store_raw),
        "publisher_contract_binding": publisher_contract_binding(),
        "reserved_at": "2026-07-20T00:00:00Z",
        "publication_occurred": False,
        "formal_authority": "none",
        "positive_assurance_allowed": False,
    }
    value["consumption_digest"] = OUTER._sealed(value, "consumption_digest")
    return value


def _receipt(
    store: dict,
    store_raw: bytes,
    authorization: dict,
    consumption: dict,
) -> dict:
    value = {
        "schema_version": (
            "semantic-guard-u10-store-activation-transition-receipt/v2"
        ),
        "receipt_id": f"receipt.{authorization['authorization_id']}",
        "record_kind": "activation_transition_occurrence",
        "public_operation": "activate-store",
        "public_identifier": authorization["authorization_id"],
        "authorization_id": authorization["authorization_id"],
        "authorization_digest": authorization["authorization_digest"],
        "consumption_digest": consumption["consumption_digest"],
        "store_activation_basis_ref": authorization[
            "store_activation_basis_ref"
        ],
        "transition_kind": authorization["transition_kind"],
        "prior_store_ref": authorization["prior_store_ref"],
        "prior_revocation_ref": authorization["prior_revocation_ref"],
        "activated_store_ref": OUTER._store_transition_ref(store, store_raw),
        "publisher_contract_binding": consumption[
            "publisher_contract_binding"
        ],
        "publication_not_before": consumption["reserved_at"],
        "publication_observed_at": "2026-07-20T00:00:01Z",
        "receipt_recorded_at": "2026-07-20T00:00:02Z",
        "formal_authority": "none",
        "positive_assurance_allowed": False,
    }
    value["receipt_digest"] = OUTER._sealed(value, "receipt_digest")
    return value


def _records(
    *,
    replacement: bool = False,
) -> tuple[dict, bytes, dict, dict, dict]:
    store, store_raw = _store()
    authorization = _authorization(replacement=replacement)
    consumption = _consumption(store, store_raw, authorization)
    receipt = _receipt(store, store_raw, authorization, consumption)
    return store, store_raw, authorization, consumption, receipt


def _reseal(value: dict, field: str) -> None:
    value[field] = OUTER._sealed(value, field)


def _metadata(
    *,
    uid: int = 0,
    gid: int = 0,
    mode: int = stat.S_IFREG | 0o444,
    nlink: int = 1,
) -> SimpleNamespace:
    return SimpleNamespace(st_uid=uid, st_gid=gid, st_mode=mode, st_nlink=nlink)


class U10OuterLauncherTransitionReceiptTests(unittest.TestCase):
    def test_environment_adoption_requires_canonical_record_bytes(self) -> None:
        adoption = {
            "schema_version": (
                "semantic-guard-u10-snapshot-environment-adoption/v1"
            ),
            "adoption_id": "adoption.u10.noncanonical-test",
        }
        raw = (
            json.dumps(adoption, ensure_ascii=False, sort_keys=True, indent=2)
            + "\n"
        ).encode("utf-8")
        reference = {"record_id": adoption["adoption_id"]}
        with (
            patch.object(
                OUTER,
                "_read_compact_root_ref",
                return_value=(adoption, raw),
            ),
            self.assertRaises(OUTER.OuterLaunchError) as observed,
        ):
            OUTER._validate_environment_adoption_artifact(
                manifest={"environment_adoption_ref": reference},
                snapshot=Path("/tmp/snapshot"),
                entries={},
                entry={"environment_adoption_binding": reference},
            )
        self.assertEqual(
            str(observed.exception), "environment adoption record mismatch"
        )

    def test_valid_two_phase_records_match_live_schemas(self) -> None:
        _store_value, _store_raw, _authorization_value, consumption, receipt = (
            _records()
        )
        cases = {
            "u10-store-activation-authorization-consumption-v1.schema.json": (
                consumption
            ),
            "u10-store-activation-transition-receipt-v2.schema.json": receipt,
        }
        for schema_name, value in cases.items():
            with self.subTest(schema=schema_name):
                schema = json.loads(
                    (SCHEMA_DIRECTORY / schema_name).read_text(encoding="utf-8")
                )
                Draft202012Validator(
                    schema,
                    format_checker=FormatChecker(),
                ).validate(value)

    def test_valid_two_phase_records_use_fixed_ledger_names(self) -> None:
        store, store_raw, authorization, consumption, receipt = _records()
        consumption_raw = OUTER._canonical(consumption) + b"\n"
        receipt_raw = OUTER._canonical(receipt) + b"\n"
        root = OUTER.STORE_ACTIVATION_LEDGER_ROOT
        authorization_id = authorization["authorization_id"]

        with (
            patch.object(
                OUTER,
                "_read_root_file",
                side_effect=[consumption_raw, receipt_raw],
            ) as reader,
            patch.object(
                OUTER.Path,
                "lstat",
                side_effect=[_metadata(), _metadata()],
            ),
            patch.object(OUTER, "_validate_activation_ledger_directory"),
        ):
            observed = OUTER._validate_activation_transition_records(
                store,
                store_raw,
                authorization,
            )

        self.assertEqual(observed, (consumption, receipt))
        self.assertEqual(
            reader.call_args_list,
            [
                call(
                    root / f"{authorization_id}.consumption.json",
                    exact_mode=0o444,
                ),
                call(
                    root / f"{authorization_id}.receipt.json",
                    exact_mode=0o444,
                ),
            ],
        )

    def test_current_selector_pins_two_phase_ledger_path_and_policy(self) -> None:
        store, store_raw, authorization, _consumption_value, _receipt_value = _records()
        cases = {
            "path": ("activation_ledger_path", "/tmp/attacker-ledger"),
            "policy": ("activation_ledger_policy", "single_phase_o_excl/v1"),
        }
        for label, (field, value) in cases.items():
            with self.subTest(label=label):
                mutated = copy.deepcopy(store)
                mutated["current_selector"][field] = value
                with patch.object(OUTER, "_read_root_file") as reader:
                    with self.assertRaises(OUTER.OuterLaunchError):
                        OUTER._validate_activation_transition_records(
                            mutated,
                            store_raw,
                            authorization,
                        )
                reader.assert_not_called()

    def test_ledger_directory_is_root_root_0755(self) -> None:
        cases = {
            "owner": _metadata(uid=501, mode=stat.S_IFDIR | 0o755),
            "group": _metadata(gid=20, mode=stat.S_IFDIR | 0o755),
            "mode": _metadata(mode=stat.S_IFDIR | 0o700),
        }
        for label, metadata in cases.items():
            with self.subTest(label=label):
                with (
                    patch.object(OUTER, "_validate_ancestors"),
                    patch.object(OUTER.Path, "lstat", return_value=metadata),
                ):
                    with self.assertRaises(OUTER.OuterLaunchError):
                        OUTER._validate_activation_ledger_directory()

        with (
            patch.object(OUTER, "_validate_ancestors") as ancestors,
            patch.object(
                OUTER.Path,
                "lstat",
                return_value=_metadata(mode=stat.S_IFDIR | 0o755),
            ),
        ):
            OUTER._validate_activation_ledger_directory()
        ancestors.assert_called_once_with(
            OUTER.STORE_ACTIVATION_LEDGER_ROOT,
            include_leaf=True,
        )

    def test_each_ledger_record_is_root_root_0444_and_single_link(self) -> None:
        cases = {
            "owner": _metadata(uid=501),
            "group": _metadata(gid=20),
            "mode": _metadata(mode=stat.S_IFREG | 0o400),
            "hardlink": _metadata(nlink=2),
            "not_regular": _metadata(mode=stat.S_IFDIR | 0o444),
        }
        for label, metadata in cases.items():
            with self.subTest(label=label):
                with (
                    patch.object(OUTER, "_read_root_file", return_value=b"{}"),
                    patch.object(OUTER.Path, "lstat", return_value=metadata),
                ):
                    with self.assertRaises(OUTER.OuterLaunchError):
                        OUTER._read_activation_ledger_record(
                            OUTER.STORE_ACTIVATION_LEDGER_ROOT / "record.json",
                            "activation ledger record",
                        )

    def test_consumption_contract_is_closed_non_occurrence_and_sealed(self) -> None:
        store, store_raw, authorization, valid, receipt = _records()
        cases = {}

        extra = copy.deepcopy(valid)
        extra["unexpected"] = "field"
        cases["extra_field"] = extra

        wrong_kind = copy.deepcopy(valid)
        wrong_kind["record_kind"] = "activation_transition_occurrence"
        cases["record_kind"] = wrong_kind

        bad_time = copy.deepcopy(valid)
        bad_time["reserved_at"] = "2026-07-20"
        cases["reserved_at"] = bad_time

        occurrence_claim = copy.deepcopy(valid)
        occurrence_claim["publication_occurred"] = True
        cases["publication_occurred"] = occurrence_claim

        authority = copy.deepcopy(valid)
        authority["formal_authority"] = "human"
        cases["formal_authority"] = authority

        malformed_ref = copy.deepcopy(valid)
        malformed_ref["target_store_ref"]["unexpected"] = "field"
        cases["target_store_ref_closure"] = malformed_ref

        for label, mutated in cases.items():
            with self.subTest(label=label):
                _reseal(mutated, "consumption_digest")
                with self.assertRaises(OUTER.OuterLaunchError):
                    OUTER._validate_activation_transition_records_value(
                        store,
                        store_raw,
                        authorization,
                        mutated,
                        receipt,
                    )

        bad_seal = copy.deepcopy(valid)
        bad_seal["consumption_digest"] = _digest("forged-consumption-seal")
        with self.assertRaises(OUTER.OuterLaunchError):
            OUTER._validate_activation_transition_records_value(
                store,
                store_raw,
                authorization,
                bad_seal,
                receipt,
            )

    def test_occurrence_receipt_contract_is_closed_and_sealed(self) -> None:
        store, store_raw, authorization, consumption, valid = _records()
        cases = {}

        extra = copy.deepcopy(valid)
        extra["unexpected"] = "field"
        cases["extra_field"] = extra

        wrong_kind = copy.deepcopy(valid)
        wrong_kind["record_kind"] = "activation_authorization_consumption"
        cases["record_kind"] = wrong_kind

        bad_time = copy.deepcopy(valid)
        bad_time["publication_observed_at"] = "2026-07-20"
        cases["publication_observed_at"] = bad_time

        authority = copy.deepcopy(valid)
        authority["formal_authority"] = "human"
        cases["formal_authority"] = authority

        positive = copy.deepcopy(valid)
        positive["positive_assurance_allowed"] = True
        cases["positive_assurance"] = positive

        malformed_ref = copy.deepcopy(valid)
        malformed_ref["activated_store_ref"]["unexpected"] = "field"
        cases["activated_store_ref_closure"] = malformed_ref

        for label, mutated in cases.items():
            with self.subTest(label=label):
                _reseal(mutated, "receipt_digest")
                with self.assertRaises(OUTER.OuterLaunchError):
                    OUTER._validate_activation_transition_records_value(
                        store,
                        store_raw,
                        authorization,
                        consumption,
                        mutated,
                    )

        bad_seal = copy.deepcopy(valid)
        bad_seal["receipt_digest"] = _digest("forged-receipt-seal")
        with self.assertRaises(OUTER.OuterLaunchError):
            OUTER._validate_activation_transition_records_value(
                store,
                store_raw,
                authorization,
                consumption,
                bad_seal,
            )

    def test_both_phases_match_authorization_transition_context(self) -> None:
        store, store_raw, authorization, consumption, receipt = _records(
            replacement=True
        )
        for phase in ("consumption", "receipt"):
            for field, value in (
                ("authorization_id", "authorization.u10.other"),
                ("authorization_digest", _digest("other-authorization")),
                ("prior_store_ref", _prior_store_ref("other")),
                ("prior_revocation_ref", _prior_revocation_ref("other")),
            ):
                with self.subTest(phase=phase, field=field):
                    mutated_consumption = copy.deepcopy(consumption)
                    mutated_receipt = copy.deepcopy(receipt)
                    target = (
                        mutated_consumption
                        if phase == "consumption"
                        else mutated_receipt
                    )
                    target[field] = value
                    seal_field = (
                        "consumption_digest"
                        if phase == "consumption"
                        else "receipt_digest"
                    )
                    _reseal(target, seal_field)
                    if phase == "consumption":
                        mutated_receipt["consumption_digest"] = target[
                            "consumption_digest"
                        ]
                        _reseal(mutated_receipt, "receipt_digest")
                    with self.assertRaises(OUTER.OuterLaunchError):
                        OUTER._validate_activation_transition_records_value(
                            store,
                            store_raw,
                            authorization,
                            mutated_consumption,
                            mutated_receipt,
                        )

    def test_receipt_binds_exact_consumption_digest(self) -> None:
        store, store_raw, authorization, consumption, receipt = _records()
        receipt["consumption_digest"] = _digest("other-consumption")
        _reseal(receipt, "receipt_digest")
        with self.assertRaises(OUTER.OuterLaunchError):
            OUTER._validate_activation_transition_records_value(
                store,
                store_raw,
                authorization,
                consumption,
                receipt,
            )

    def test_recorded_consumed_and_publication_interval_times_are_monotonic(
        self,
    ) -> None:
        cases = {
            "authorization_after_consumption": (
                "authorization",
                "recorded_at",
                "2026-07-20T00:00:01Z",
            ),
            "consumption_after_receipt": (
                "consumption",
                "reserved_at",
                "2026-07-20T00:00:02Z",
            ),
            "receipt_before_consumption": (
                "receipt",
                "publication_observed_at",
                "2026-07-19T23:59:58Z",
            ),
            "receipt_recorded_before_observation": (
                "receipt",
                "receipt_recorded_at",
                "2026-07-20T00:00:00Z",
            ),
            "publication_lower_bound_differs_from_consumption": (
                "receipt",
                "publication_not_before",
                "2026-07-19T23:59:59Z",
            ),
        }
        for label, (phase, field, value) in cases.items():
            with self.subTest(label=label):
                store, store_raw, authorization, consumption, receipt = _records()
                target = {
                    "authorization": authorization,
                    "consumption": consumption,
                    "receipt": receipt,
                }[phase]
                target[field] = value
                if phase == "consumption":
                    _reseal(consumption, "consumption_digest")
                    receipt["consumption_digest"] = consumption["consumption_digest"]
                    _reseal(receipt, "receipt_digest")
                elif phase == "receipt":
                    _reseal(receipt, "receipt_digest")
                with self.assertRaises(OUTER.OuterLaunchError):
                    OUTER._validate_activation_transition_records_value(
                        store,
                        store_raw,
                        authorization,
                        consumption,
                        receipt,
                    )

    def test_snapshot_verification_adoption_activation_times_are_monotonic(
        self,
    ) -> None:
        manifest = {
            "immutability_verification": {"verified_at": "2026-07-20T00:00:00Z"}
        }
        environment_adoption = {"recorded_at": "2026-07-20T00:00:01Z"}
        snapshot_adoption = {"recorded_at": "2026-07-20T00:00:02Z"}
        activation = {
            "basis": {
                "immutability_verified_at": "2026-07-20T00:00:00Z",
                "activation_prepared_at": "2026-07-20T00:00:04Z",
            },
            "consumption": {
                "reserved_at": "2026-07-20T00:00:03Z",
                "activation_prepared_at": "2026-07-20T00:00:04Z",
            },
            "receipt": {
                "publication_not_before": "2026-07-20T00:00:03Z",
                "publication_observed_at": "2026-07-20T00:00:05Z",
                "receipt_recorded_at": "2026-07-20T00:00:06Z",
            },
        }
        OUTER._validate_snapshot_chronology(
            manifest,
            environment_adoption,
            snapshot_adoption,
            activation,
        )

        cases = {}
        verified_after_adoption = (
            copy.deepcopy(manifest),
            copy.deepcopy(environment_adoption),
            copy.deepcopy(snapshot_adoption),
            copy.deepcopy(activation),
        )
        verified_after_adoption[0]["immutability_verification"]["verified_at"] = (
            "2026-07-20T00:00:02Z"
        )
        verified_after_adoption[3]["basis"]["immutability_verified_at"] = (
            "2026-07-20T00:00:02Z"
        )
        cases["verified_after_adoption"] = verified_after_adoption

        environment_adoption_after_snapshot_adoption = (
            copy.deepcopy(manifest),
            {"recorded_at": "2026-07-20T00:00:03Z"},
            copy.deepcopy(snapshot_adoption),
            copy.deepcopy(activation),
        )
        cases["environment_adoption_after_snapshot_adoption"] = (
            environment_adoption_after_snapshot_adoption
        )

        snapshot_adoption_after_reservation = (
            copy.deepcopy(manifest),
            copy.deepcopy(environment_adoption),
            {"recorded_at": "2026-07-20T00:00:04Z"},
            copy.deepcopy(activation),
        )
        cases["snapshot_adoption_after_reservation"] = (
            snapshot_adoption_after_reservation
        )

        activation_verification_mismatch = (
            copy.deepcopy(manifest),
            copy.deepcopy(environment_adoption),
            copy.deepcopy(snapshot_adoption),
            copy.deepcopy(activation),
        )
        activation_verification_mismatch[3]["basis"][
            "immutability_verified_at"
        ] = "2026-07-19T23:59:59Z"
        cases["activation_verification_mismatch"] = activation_verification_mismatch

        for label, values in cases.items():
            with self.subTest(label=label):
                with self.assertRaises(OUTER.OuterLaunchError):
                    OUTER._validate_snapshot_chronology(*values)

    def test_outer_snapshot_basis_binds_exact_environment_adoption_record(
        self,
    ) -> None:
        authorization_id = "authorization.snapshot-adoption"
        entry_id = "entry.u10.adoption-binding"
        manifest_raw = b"manifest"
        authorization_ref = {
            "record_id": authorization_id,
            "locator": str(
                OUTER.AUTHORIZATION_ROOT / f"{authorization_id}.json"
            ),
            "artifact_digest": _digest("snapshot-adoption-authorization-artifact"),
            "semantic_digest": _digest("snapshot-adoption-authorization"),
        }
        environment_adoption_ref = {
            "record_id": "adoption.environment.exact",
            "locator": str(
                OUTER.AUTHORIZATION_ROOT / "adoption.environment.exact.json"
            ),
            "artifact_digest": _digest("environment-adoption-artifact"),
            "semantic_digest": _digest("environment-adoption"),
        }
        projection_receipt_ref = {
            "record_id": "receipt.snapshot-projection",
            "locator": str(
                OUTER.SNAPSHOT_PROJECTION_LEDGER_ROOT
                / "authorization.snapshot-projection.receipt.json"
            ),
            "artifact_digest": _digest("projection-receipt-artifact"),
            "semantic_digest": _digest("projection-receipt"),
        }
        manifest = {
            "snapshot_id": "snapshot.u10.adoption-binding",
            "snapshot_version": "1.0.0",
            "snapshot_basis_digest": _digest("snapshot-basis"),
            "snapshot_adoption_authorization_ref": authorization_ref,
            "environment_adoption_ref": environment_adoption_ref,
            "immutability_verification": {
                "verified_at": "2026-07-20T00:00:00Z"
            },
            "root_storage": {
                "snapshot_path": str(
                    OUTER.SNAPSHOT_ROOT / "snapshot.u10.adoption-binding"
                )
            },
            "manifest_digest": _digest("manifest-semantic"),
            "activation_ref": {
                "record_id": "basis.snapshot-adoption",
                "locator": str(
                    OUTER.SNAPSHOT_ACTIVATION_ROOT
                    / "basis.snapshot-adoption.json"
                ),
                "artifact_digest": _digest("snapshot-basis-artifact"),
                "semantic_digest": _digest("placeholder"),
            },
        }
        environment_adoption = {
            "adoption_id": "adoption.environment.exact",
            "adoption_version": "1.0.0",
            "adoption_digest": _digest("environment-adoption"),
            "projection_receipt_ref": projection_receipt_ref,
        }
        snapshot_adoption = {"authorization_id": authorization_id}
        activation_basis = {
            "schema_version": (
                "semantic-guard-u10-snapshot-activation-basis/v1"
            ),
            "activation_basis_id": "basis.snapshot-adoption",
            "snapshot_id": manifest["snapshot_id"],
            "snapshot_version": manifest["snapshot_version"],
            "snapshot_basis_digest": manifest["snapshot_basis_digest"],
            "entry_id": entry_id,
            "adoption_id": environment_adoption["adoption_id"],
            "adoption_version": environment_adoption["adoption_version"],
            "adoption_digest": environment_adoption["adoption_digest"],
            "environment_adoption_ref": environment_adoption_ref,
            "projection_receipt_ref": projection_receipt_ref,
            "snapshot_adoption_authorization_ref": authorization_ref,
            "immutability_verified_at": "2026-07-20T00:00:00Z",
            "activation_prepared_at": "2026-07-20T00:00:00Z",
            "preparation_status": "prepared_for_manifest_publication",
            "formal_authority": "none",
            "positive_assurance_allowed": False,
        }
        activation_basis["activation_basis_digest"] = OUTER._sealed(
            activation_basis, "activation_basis_digest"
        )
        manifest["activation_ref"]["semantic_digest"] = activation_basis[
            "activation_basis_digest"
        ]
        expected_manifest_ref = {
            "record_id": manifest["snapshot_id"],
            "locator": str(
                Path(manifest["root_storage"]["snapshot_path"])
                / OUTER.MANIFEST_NAME
            ),
            "artifact_digest": OUTER._digest(manifest_raw),
            "semantic_digest": manifest["manifest_digest"],
        }
        publisher = publisher_contract_binding()
        key_id = "00000000-0000-4000-8000-000000000001"
        key_authorization_id = "authorization.key.outer-fixture"
        key_authorization_ref = {
            "authorization_id": key_authorization_id,
            "locator": str(
                OUTER.U10_ROOT
                / "activations/key-transitions"
                / f"{key_authorization_id}.authorization.json"
            ),
            "artifact_digest": _digest("key-authorization-artifact"),
            "authorization_digest": _digest("key-authorization-semantic"),
        }
        key_consumption_ref = {
            "consumption_id": f"consumption.{key_authorization_id}",
            "locator": str(
                OUTER.U10_ROOT
                / "activations/key-transitions"
                / f"{key_authorization_id}.consumption.json"
            ),
            "artifact_digest": _digest("key-consumption-artifact"),
            "consumption_digest": _digest("key-consumption-semantic"),
        }
        signing_key_ref = {
            "key_id": key_id,
            "key_entity_ref": f"U-10 signing key・{key_id}",
            "locator": str(
                OUTER.U10_ROOT
                / "keys/generations"
                / key_id
                / "public-metadata.json"
            ),
            "artifact_digest": _digest("key-metadata-artifact"),
            "metadata_digest": _digest("key-metadata-semantic"),
            "generation_authorization_ref": key_authorization_ref,
            "generation_consumption_ref": key_consumption_ref,
        }
        selector_artifact_digest = _digest("key-selector-artifact")
        signing_key_selector_ref = {
            "selector_id": f"selector.{key_authorization_id}",
            "locator": str(
                OUTER.U10_ROOT
                / "keys/selector-history/sha256"
                / f"{selector_artifact_digest['value']}.json"
            ),
            "artifact_digest": selector_artifact_digest,
            "selector_digest": _digest("key-selector-semantic"),
        }
        store_basis = {
            "schema_version": "semantic-guard-u10-store-activation-basis/v2",
            "basis_id": "placeholder",
            "basis_version": "2.0.0",
            "record_kind": "exact_store_activation_basis_candidate",
            "store_content": {
                "store_revision_id": "placeholder",
                "entries": {
                    entry_id: {
                        "snapshot_manifest_binding": {
                            "locator": expected_manifest_ref["locator"],
                            "artifact_digest": expected_manifest_ref[
                                "artifact_digest"
                            ],
                            "manifest_digest": expected_manifest_ref[
                                "semantic_digest"
                            ],
                        }
                    }
                },
            },
            "store_activation_basis_digest": _digest("placeholder"),
            "store_transition_digest": _digest("placeholder"),
            "entry_id": entry_id,
            "snapshot_manifest_ref": expected_manifest_ref,
            "snapshot_activation_authorization_ref": authorization_ref,
            "signing_key_ref": signing_key_ref,
            "signing_key_selector_ref": signing_key_selector_ref,
            "prior_store_ref": None,
            "prior_revocation_ref": None,
            "publisher_contract_binding": publisher,
            "prepared_at": "2026-07-20T00:00:00Z",
            "publication_state": "not_published",
            "formal_authority": "none",
            "positive_assurance_allowed": False,
        }
        transition_digest = OUTER._store_activation_transition_digest(store_basis)
        store_basis["store_transition_digest"] = transition_digest
        store_basis["basis_id"] = f"store-basis.{transition_digest['value']}"
        store_basis["store_content"]["store_revision_id"] = (
            f"revision.u10.{transition_digest['value']}"
        )
        store_basis["store_activation_basis_digest"] = OUTER._digest(
            OUTER._canonical(store_basis["store_content"])
        )
        store_basis["basis_digest"] = OUTER._sealed(store_basis, "basis_digest")
        store_basis_raw = OUTER._canonical(store_basis) + b"\n"
        store_basis_ref = {
            "record_id": store_basis["basis_id"],
            "locator": str(
                OUTER.STORE_ACTIVATION_BASIS_ROOT
                / f"{authorization_id}.store-basis.json"
            ),
            "artifact_digest": OUTER._digest(store_basis_raw),
            "semantic_digest": store_basis["basis_digest"],
        }
        consumption = {
            "schema_version": (
                "semantic-guard-u10-snapshot-activation-authorization-consumption/v1"
            ),
            "consumption_id": f"consumption.{authorization_id}",
            "record_kind": "snapshot_adoption_authorization_consumption",
            "public_operation": "activate-snapshot",
            "public_identifier": authorization_id,
            "authorization_ref": authorization_ref,
            "projection_receipt_ref": projection_receipt_ref,
            "environment_adoption_ref": environment_adoption_ref,
            "snapshot_id": manifest["snapshot_id"],
            "snapshot_basis_digest": manifest["snapshot_basis_digest"],
            "publisher_contract_binding": publisher,
            "manifest_publication_occurred": False,
            "formal_authority": "none",
            "positive_assurance_allowed": False,
        }
        consumption["consumption_digest"] = OUTER._sealed(
            consumption, "consumption_digest"
        )
        receipt = {
            "schema_version": (
                "semantic-guard-u10-snapshot-activation-publication-receipt/v1"
            ),
            "record_kind": "active_snapshot_manifest_publication_occurrence",
            "public_operation": "activate-snapshot",
            "public_identifier": authorization_id,
            "authorization_ref": authorization_ref,
            "consumption_ref": {
                "consumption_id": consumption["consumption_id"],
                "consumption_digest": consumption["consumption_digest"],
            },
            "projection_receipt_ref": projection_receipt_ref,
            "environment_adoption_ref": environment_adoption_ref,
            "activation_ref": manifest["activation_ref"],
            "snapshot_manifest_ref": expected_manifest_ref,
            "store_activation_basis_ref": store_basis_ref,
            "completion_scope": (
                "snapshot_manifest_and_exact_store_basis_candidate_published"
            ),
            "publisher_contract_binding": publisher,
            "publication_occurred": True,
            "publication_observed_at": "2026-07-20T00:00:01Z",
            "formal_authority": "none",
            "positive_assurance_allowed": False,
        }
        receipt["receipt_digest"] = OUTER._sealed(receipt, "receipt_digest")
        consumption_raw = OUTER._canonical(consumption) + b"\n"
        receipt_raw = OUTER._canonical(receipt) + b"\n"

        def read_root(path: Path, **_kwargs) -> bytes:
            if path == OUTER.STORE_ACTIVATION_BASIS_ROOT / (
                f"{authorization_id}.store-basis.json"
            ):
                return store_basis_raw
            if path == OUTER.SNAPSHOT_ACTIVATION_LEDGER_ROOT / (
                f"{authorization_id}.consumption.json"
            ):
                return consumption_raw
            if path == OUTER.SNAPSHOT_ACTIVATION_LEDGER_ROOT / (
                f"{authorization_id}.receipt.json"
            ):
                return receipt_raw
            raise AssertionError(f"unexpected path: {path}")

        with (
            patch.object(
                OUTER,
                "_read_compact_root_ref",
                return_value=(activation_basis, b"activation-basis"),
            ),
            patch.object(OUTER, "_read_root_file", side_effect=read_root),
        ):
            observed = OUTER._validate_snapshot_activation(
                manifest,
                entry_id,
                environment_adoption,
                snapshot_adoption,
                manifest_raw,
            )
        self.assertEqual(observed["basis"], activation_basis)
        self.assertEqual(observed["store_activation_basis"], store_basis)

        for field in ("adoption_id", "adoption_version", "adoption_digest"):
            with self.subTest(field=field):
                forged = copy.deepcopy(activation_basis)
                forged[field] = (
                    _digest("forged-adoption")
                    if field == "adoption_digest"
                    else f"forged-{field}"
                )
                forged["activation_basis_digest"] = OUTER._sealed(
                    forged, "activation_basis_digest"
                )
                forged_manifest = copy.deepcopy(manifest)
                forged_manifest["activation_ref"]["semantic_digest"] = forged[
                    "activation_basis_digest"
                ]
                with patch.object(
                    OUTER,
                    "_read_compact_root_ref",
                    return_value=(forged, b"activation-basis"),
                ), self.assertRaises(OUTER.OuterLaunchError):
                    OUTER._validate_snapshot_activation(
                        forged_manifest,
                        entry_id,
                        environment_adoption,
                        snapshot_adoption,
                        manifest_raw,
                    )

    def test_both_store_refs_match_exact_current_store(self) -> None:
        cases = {
            "store_id": "store.u10.other",
            "store_revision_id": "store-revision.u10.other",
            "store_version": "2.0.0",
            "store_activation_basis_digest": _digest("other-basis"),
            "artifact_digest": _digest("other-raw-artifact"),
            "semantic_digest": _digest("other-semantic-store"),
        }
        for phase, field_name in (
            ("consumption", "target_store_ref"),
            ("receipt", "activated_store_ref"),
        ):
            for field, value in cases.items():
                with self.subTest(phase=phase, field=field):
                    store, store_raw, authorization, consumption, receipt = _records()
                    target = consumption if phase == "consumption" else receipt
                    target[field_name][field] = value
                    seal_field = (
                        "consumption_digest"
                        if phase == "consumption"
                        else "receipt_digest"
                    )
                    _reseal(target, seal_field)
                    if phase == "consumption":
                        receipt["consumption_digest"] = consumption[
                            "consumption_digest"
                        ]
                        _reseal(receipt, "receipt_digest")
                    with self.assertRaises(OUTER.OuterLaunchError):
                        OUTER._validate_activation_transition_records_value(
                            store,
                            store_raw,
                            authorization,
                            consumption,
                            receipt,
                        )

    def test_invalid_authorization_transition_context_is_rejected(self) -> None:
        store, store_raw, _authorization_value, consumption, receipt = _records()
        cases = {}

        initial_with_prior = _authorization()
        initial_with_prior["prior_store_ref"] = _prior_store_ref()
        cases["initial_with_prior"] = initial_with_prior

        replacement_without_prior = _authorization(replacement=True)
        replacement_without_prior["prior_store_ref"] = None
        cases["replacement_without_prior"] = replacement_without_prior

        missing_transition = _authorization()
        missing_transition.pop("transition_kind")
        cases["missing_transition"] = missing_transition

        for label, authorization in cases.items():
            with self.subTest(label=label):
                with self.assertRaises(OUTER.OuterLaunchError):
                    OUTER._validate_activation_transition_records_value(
                        store,
                        store_raw,
                        authorization,
                        consumption,
                        receipt,
                    )

    def test_store_validation_checks_both_phases_before_runtime_refs(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            current_store = root / "trust-store-current.json"
            history_root = root / "history"
            revocation_selector = root / "revocation-selector.json"
            with (
                patch.object(OUTER, "CURRENT_STORE", current_store),
                patch.object(OUTER, "HISTORY_ROOT", history_root),
                patch.object(OUTER, "REVOCATION_SELECTOR", revocation_selector),
            ):
                store, store_raw = _store()
                authorization = _authorization()
                transition_error = OUTER.OuterLaunchError("transition rejected")
                with (
                    patch.object(
                        OUTER,
                        "_read_root_file",
                        return_value=store_raw,
                    ) as reader,
                    patch.object(
                        OUTER,
                        "_validate_authorization",
                        return_value=(
                            authorization,
                            {
                                "publisher_contract_binding": (
                                    publisher_contract_binding()
                                )
                            },
                        ),
                    ),
                    patch.object(
                        OUTER,
                        "_validate_activation_transition_records",
                        side_effect=transition_error,
                    ) as validate_records,
                    patch.object(OUTER, "_verify_root_ref") as verify_root_ref,
                ):
                    with self.assertRaisesRegex(
                        OUTER.OuterLaunchError,
                        "transition rejected",
                    ):
                        OUTER._validate_store()

                self.assertEqual(reader.call_count, 2)
                validate_records.assert_called_once_with(
                    store,
                    store_raw,
                    authorization,
                )
                verify_root_ref.assert_not_called()


if __name__ == "__main__":
    unittest.main()
