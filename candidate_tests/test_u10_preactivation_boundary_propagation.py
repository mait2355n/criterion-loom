from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator

import semantic_guard_u10_broker.core as core
from semantic_guard_u10_broker.protected_io import BrokerBoundaryError


SCHEMA_ROOT = Path(__file__).parents[1] / "src" / "semantic_guard_vnext" / "validation" / "env-path-contracts"
OUTER_PATH = Path(__file__).parent / "fixtures" / "scripts" / "u10_root_broker_outer_launcher.py"
SPEC = importlib.util.spec_from_file_location(
    "u10_outer_preactivation_propagation_tests", OUTER_PATH
)
assert SPEC is not None and SPEC.loader is not None
OUTER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(OUTER)

SUBJECT_ID = "acfb8b85-2f75-5e82-a641-b3b3b6e023d6"
DECISION_IDENTITY = "11111111-1111-4111-8111-111111111111"
OBSERVATION_IDENTITY = "22222222-2222-4222-8222-222222222222"
PRINCIPAL_IDENTITY = "33333333-3333-4333-8333-333333333333"


def _digest(raw: bytes | str) -> dict[str, str]:
    if isinstance(raw, str):
        raw = raw.encode("utf-8")
    return core.digest_bytes(raw)


def _seal(value: dict, field: str) -> dict:
    result = copy.deepcopy(value)
    material = copy.deepcopy(result)
    material.pop(field, None)
    result[field] = _digest(core.canonical_json_bytes(material))
    return result


def _raw(value: dict) -> bytes:
    return core.canonical_json_bytes(value)


def _chain() -> tuple[dict, dict, Path, dict, dict[str, bytes], dict]:
    snapshot = Path(
        "/Library/Application Support/semantic-guard/u10/snapshots/"
        "snapshot.u10.boundary-test"
    )
    decision = _seal(
        {
            "schema_version": "semantic-guard-u10-preactivation-decision/v1",
            "decision_id": "decision.u10.boundary-test",
            "decision_entity_ref": f"decision label・{DECISION_IDENTITY}",
            "subject_entity_ref": f"U-10 subject・{SUBJECT_ID}",
            "human_decision": "accept",
            "decision_owner": "human",
            "threat_boundary_selection": "local_bounded_repository_suite_only",
            "worker_identity_selection": (
                "current_user_501_20_empty_supplementary_groups"
            ),
            "recorded_at": "2026-07-20T00:00:00Z",
        },
        "decision_digest",
    )
    decision_raw = _raw(decision)
    decision_source = "/source/u10-decision.json"
    exact_decision_ref = {
        "record_id": decision["decision_id"],
        "locator": decision_source,
        "artifact_digest": _digest(decision_raw),
        "semantic_digest": decision["decision_digest"],
    }
    platform_material = {
        "os": "Darwin",
        "architecture": "arm64",
        "os_release": "25.0.0",
        "platform_version": "Darwin Kernel Version test",
        "hostname": "u10-test-host",
    }
    platform_binding = {
        **platform_material,
        "host_identity_digest": _digest(_raw(platform_material)),
    }
    observation = _seal(
        {
            "schema_version": (
                "semantic-guard-u10-worker-account-observation/v1"
            ),
            "observation_id": "observation.u10.boundary-test",
            "observation_entity_ref": (
                f"account observation・{OBSERVATION_IDENTITY}"
            ),
            "subject_entity_ref": f"renamed subject・{SUBJECT_ID}",
            "derived_from": f"renamed decision・{DECISION_IDENTITY}",
            "decision_record_ref": exact_decision_ref,
            "worker_identity_selection": (
                "current_user_501_20_empty_supplementary_groups"
            ),
            "principal_entity_ref": f"worker principal・{PRINCIPAL_IDENTITY}",
            "account_name": "test-worker",
            "uid": 501,
            "gid": 20,
            "account_supplementary_gids": [12, 61],
            "login_shell": "/bin/zsh",
            "home_directory": "/Users/test-worker",
            "non_login": False,
            "platform_binding": platform_binding,
            "observed_at": "2026-07-20T00:00:01Z",
        },
        "observation_digest",
    )
    observation_raw = _raw(observation)
    observation_source = "/source/u10-account-observation.json"
    resolution = _seal(
        {
            "schema_version": (
                "semantic-guard-u10-worker-principal-resolution/v1"
            ),
            "resolution_id": "resolution.u10.boundary-test",
            "decision_record_ref": exact_decision_ref,
            "account_observation_ref": {
                "record_id": observation["observation_id"],
                "locator": observation_source,
                "artifact_digest": _digest(observation_raw),
                "semantic_digest": observation["observation_digest"],
            },
            "derived_from": f"renamed observation・{OBSERVATION_IDENTITY}",
            "worker_identity_selection": (
                "current_user_501_20_empty_supplementary_groups"
            ),
            "resolution_state": "resolved",
            "principal_entity_ref": f"renamed principal・{PRINCIPAL_IDENTITY}",
            "account_name": observation["account_name"],
            "uid": 501,
            "gid": 20,
            "account_supplementary_gids": [12, 61],
            "effective_supplementary_gids": [],
            "umask": 63,
            "login_shell": "/bin/zsh",
            "non_login": False,
            "platform_binding": platform_binding,
            "resolved_at": "2026-07-20T00:00:02Z",
        },
        "resolution_digest",
    )
    resolution_raw = _raw(resolution)

    records = {
        "decision_record_ref": (
            decision,
            decision_raw,
            decision_source,
            "governance/u10-decision.json",
            "u10_preactivation_decision_record",
            "decision_digest",
        ),
        "worker_account_observation_ref": (
            observation,
            observation_raw,
            observation_source,
            "governance/u10-account-observation.json",
            "u10_worker_account_observation",
            "observation_digest",
        ),
        "worker_principal_resolution_ref": (
            resolution,
            resolution_raw,
            "/source/u10-principal-resolution.json",
            "governance/u10-principal-resolution.json",
            "u10_worker_principal_resolution",
            "resolution_digest",
        ),
    }
    candidate_boundary: dict = {
        "profile": "u10-local-bounded-preactivation-binding/v1",
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
    }
    for field, (value, raw, source, relative, _role, semantic_field) in records.items():
        candidate_boundary[field] = {
            "record_id": value[
                {
                    "decision_record_ref": "decision_id",
                    "worker_account_observation_ref": "observation_id",
                    "worker_principal_resolution_ref": "resolution_id",
                }[field]
            ],
            "source_locator": source,
            "source_artifact_digest": _digest(raw),
            "bundled_locator": relative,
            "bundled_artifact_digest": _digest(raw),
            "semantic_digest": value[semantic_field],
        }
    candidate_boundary = _seal(candidate_boundary, "binding_digest")
    candidate_payload_hash = _digest("candidate payload")["value"]
    candidate_id = f"candidate.u10.{candidate_payload_hash}"
    candidate = _seal(
        {
            "schema_version": "semantic-guard-u10-root-candidate-bundle/v1",
            "bundle_id": candidate_id,
            "bundle_version": "2.0.0-candidate",
            "preactivation_boundary_refs": candidate_boundary,
        },
        "bundle_digest",
    )
    candidate_raw = _raw(candidate)
    candidate_locator = (
        "/Library/Application Support/semantic-guard/u10/candidates/"
        f"{candidate_id}/bundle-manifest.json"
    )

    raw_by_locator: dict[str, bytes] = {}
    entries: dict[str, dict] = {}

    def snapshot_ref(record_id: str, name: str, raw: bytes, semantic: dict) -> dict:
        reference = {
            "record_id": record_id,
            "locator": str(snapshot / "governance" / name),
            "artifact_digest": _digest(raw),
            "semantic_digest": semantic,
        }
        raw_by_locator[reference["locator"]] = raw
        return reference

    candidate_snapshot_ref = snapshot_ref(
        candidate_id,
        "u10-candidate-bundle-manifest.json",
        candidate_raw,
        candidate["bundle_digest"],
    )
    entries[candidate_id] = {
        "role": "u10_candidate_bundle_manifest",
        "source_ref": {
            "record_id": candidate_id,
            "locator": candidate_locator,
            "artifact_digest": _digest(candidate_raw),
            "semantic_digest": candidate["bundle_digest"],
        },
        "snapshot_ref": candidate_snapshot_ref,
    }
    binding: dict = {
        "profile": candidate_boundary["profile"],
        "candidate_bundle_ref": {
            "bundle_id": candidate_id,
            "bundle_version": candidate["bundle_version"],
            "candidate_locator": candidate_locator,
            "artifact_digest": _digest(candidate_raw),
            "bundle_digest": candidate["bundle_digest"],
            "snapshot_artifact_ref": candidate_snapshot_ref,
        },
        "boundary_binding_digest": candidate_boundary["binding_digest"],
        "subject_entity_id": SUBJECT_ID,
        "worker_principal_entity_id": PRINCIPAL_IDENTITY,
        "threat_boundary": candidate_boundary["threat_boundary"],
        "worker_identity_policy": candidate_boundary["worker_identity_policy"],
        "qualification_scope": candidate_boundary["qualification_scope"],
        "hostile_code_assurance": candidate_boundary[
            "hostile_code_assurance"
        ],
        "requalification_triggers": candidate_boundary[
            "requalification_triggers"
        ],
        "effective_worker_identity": {
            "uid": 501,
            "gid": 20,
            "effective_supplementary_gids": [],
            "umask": 63,
        },
    }
    for field, (value, raw, _source, relative, role, semantic_field) in records.items():
        candidate_record = candidate_boundary[field]
        reference = snapshot_ref(
            candidate_record["record_id"],
            Path(relative).name,
            raw,
            value[semantic_field],
        )
        binding[field] = {
            "record_id": candidate_record["record_id"],
            "source_locator": candidate_record["source_locator"],
            "source_artifact_digest": candidate_record[
                "source_artifact_digest"
            ],
            "candidate_relative_locator": relative,
            "candidate_artifact_digest": candidate_record[
                "bundled_artifact_digest"
            ],
            "semantic_digest": candidate_record["semantic_digest"],
            "snapshot_artifact_ref": reference,
        }
        entries[candidate_record["record_id"]] = {
            "role": role,
            "source_ref": {
                "record_id": candidate_record["record_id"],
                "locator": str(
                    Path(candidate_locator).parent / "payload" / relative
                ),
                "artifact_digest": _digest(raw),
                "semantic_digest": value[semantic_field],
            },
            "snapshot_ref": reference,
        }

    worker = {
        "uid": 501,
        "gid": 20,
        "account_supplementary_gids": [12, 61],
        "effective_supplementary_gids": [],
        "umask": 63,
        "login_shell": "/bin/zsh",
        "non_login": False,
        "root_prohibited": True,
        "principal_entity_id": PRINCIPAL_IDENTITY,
        "principal_resolution_digest": resolution["resolution_digest"],
    }
    manifest = {
        "snapshot_id": "snapshot.u10.boundary-test",
        "preactivation_boundary_binding": binding,
        "worker_identity": worker,
    }
    entry = {
        "preactivation_boundary_binding": copy.deepcopy(binding),
        "execution_uid": 501,
        "execution_gid": 20,
        "execution_supplementary_gids": [],
        "execution_umask": 63,
    }
    observed_account = {
        field: observation[field]
        for field in (
            "account_name",
            "uid",
            "gid",
            "account_supplementary_gids",
            "login_shell",
            "home_directory",
            "non_login",
            "platform_binding",
        )
    }
    return manifest, entry, snapshot, entries, raw_by_locator, observed_account


class U10PreactivationBoundaryPropagationTests(unittest.TestCase):
    def _validate_core(
        self,
        manifest: dict,
        entry: dict,
        snapshot: Path,
        entries: dict,
        raw_by_locator: dict[str, bytes],
        observed_account: dict,
    ) -> None:
        def read(_root: Path, reference: dict) -> bytes:
            return raw_by_locator[str(reference["locator"])]

        with (
            patch.object(core, "_validate"),
            patch.object(core, "_read_snapshot_artifact", side_effect=read),
            patch.object(
                core,
                "_current_worker_account_material_v1",
                return_value=observed_account,
            ),
        ):
            core._validate_preactivation_boundary_binding_v1(
                manifest=manifest,
                entry=entry,
                snapshot_path=snapshot,
                entries=entries,
                reobserve_current_account=True,
            )

    def test_positive_chain_preserves_uuid_identity_despite_label_changes(self) -> None:
        values = _chain()
        self._validate_core(*values)

    def test_core_rejects_digest_id_subject_principal_uid_and_byte_tampering(self) -> None:
        mutations = {}
        base = _chain()

        changed = copy.deepcopy(base[:4])
        changed[0]["preactivation_boundary_binding"][
            "boundary_binding_digest"
        ] = _digest("forged boundary")
        changed[1]["preactivation_boundary_binding"] = copy.deepcopy(
            changed[0]["preactivation_boundary_binding"]
        )
        mutations["boundary_digest"] = (*changed, base[4], base[5])

        for label, field, value in (
            ("subject_id", "subject_entity_id", DECISION_IDENTITY),
            ("principal_id", "worker_principal_entity_id", OBSERVATION_IDENTITY),
        ):
            changed = copy.deepcopy(base[:4])
            changed[0]["preactivation_boundary_binding"][field] = value
            changed[1]["preactivation_boundary_binding"] = copy.deepcopy(
                changed[0]["preactivation_boundary_binding"]
            )
            mutations[label] = (*changed, base[4], base[5])

        changed = copy.deepcopy(base[:4])
        changed[0]["preactivation_boundary_binding"][
            "effective_worker_identity"
        ]["uid"] = 502
        changed[1]["preactivation_boundary_binding"] = copy.deepcopy(
            changed[0]["preactivation_boundary_binding"]
        )
        mutations["uid"] = (*changed, base[4], base[5])

        changed = copy.deepcopy(base[:4])
        changed[0]["preactivation_boundary_binding"]["decision_record_ref"][
            "record_id"
        ] = "decision.u10.substituted"
        changed[1]["preactivation_boundary_binding"] = copy.deepcopy(
            changed[0]["preactivation_boundary_binding"]
        )
        mutations["decision_record_id"] = (*changed, base[4], base[5])

        changed = copy.deepcopy(base[:4])
        changed[0]["preactivation_boundary_binding"][
            "worker_account_observation_ref"
        ]["semantic_digest"] = _digest("forged observation semantic")
        changed[1]["preactivation_boundary_binding"] = copy.deepcopy(
            changed[0]["preactivation_boundary_binding"]
        )
        mutations["observation_semantic_digest"] = (
            *changed,
            base[4],
            base[5],
        )

        changed = copy.deepcopy(base[:4])
        changed[0]["preactivation_boundary_binding"][
            "effective_worker_identity"
        ]["effective_supplementary_gids"] = [999]
        changed[1]["preactivation_boundary_binding"] = copy.deepcopy(
            changed[0]["preactivation_boundary_binding"]
        )
        mutations["effective_group"] = (*changed, base[4], base[5])

        changed_raw = dict(base[4])
        decision_locator = base[0]["preactivation_boundary_binding"][
            "decision_record_ref"
        ]["snapshot_artifact_ref"]["locator"]
        changed_raw[decision_locator] += b" "
        mutations["one_byte"] = (*base[:4], changed_raw, base[5])

        for label, values in mutations.items():
            with self.subTest(label=label), self.assertRaises(
                BrokerBoundaryError
            ):
                self._validate_core(*values)

    def test_core_rejects_current_host_or_account_drift(self) -> None:
        values = list(_chain())
        values[5] = copy.deepcopy(values[5])
        values[5]["platform_binding"]["hostname"] = "wrong-place"
        with self.assertRaises(BrokerBoundaryError):
            self._validate_core(*values)

    def test_historical_chain_validation_does_not_reobserve_current_host(
        self,
    ) -> None:
        manifest, entry, snapshot, entries, raw_by_locator, _observed = _chain()

        def read(_root: Path, reference: dict) -> bytes:
            return raw_by_locator[str(reference["locator"])]

        with (
            patch.object(core, "_validate"),
            patch.object(core, "_read_snapshot_artifact", side_effect=read),
            patch.object(
                core,
                "_current_worker_account_material_v1",
                side_effect=AssertionError("historical validation reobserved host"),
            ),
        ):
            core._validate_preactivation_boundary_binding_v1(
                manifest=manifest,
                entry=entry,
                snapshot_path=snapshot,
                entries=entries,
                reobserve_current_account=False,
            )

    def test_outer_checks_the_same_chain_and_rejects_uid_substitution(self) -> None:
        manifest, entry, snapshot, entries, raw_by_locator, observed = _chain()

        def read(path: Path, **_kwargs) -> bytes:
            return raw_by_locator[str(path)]

        with (
            patch.object(OUTER, "_read_root_file", side_effect=read),
            patch.object(
                OUTER,
                "_current_worker_account_material",
                return_value=observed,
            ),
        ):
            OUTER._validate_preactivation_boundary(
                manifest=manifest,
                entry=entry,
                snapshot=snapshot,
                entries=entries,
            )
            forged = copy.deepcopy(manifest)
            forged["worker_identity"]["uid"] = 502
            with self.assertRaises(OUTER.OuterLaunchError):
                OUTER._validate_preactivation_boundary(
                    manifest=forged,
                    entry=entry,
                    snapshot=snapshot,
                    entries=entries,
                )

    def test_outer_rejects_observation_byte_tamper_and_host_drift(self) -> None:
        manifest, entry, snapshot, entries, raw_by_locator, observed = _chain()
        observation_locator = manifest["preactivation_boundary_binding"][
            "worker_account_observation_ref"
        ]["snapshot_artifact_ref"]["locator"]

        changed_raw = dict(raw_by_locator)
        changed_raw[observation_locator] += b" "

        def read_changed(path: Path, **_kwargs) -> bytes:
            return changed_raw[str(path)]

        with (
            patch.object(OUTER, "_read_root_file", side_effect=read_changed),
            patch.object(
                OUTER,
                "_current_worker_account_material",
                return_value=observed,
            ),
            self.assertRaises(OUTER.OuterLaunchError),
        ):
            OUTER._validate_preactivation_boundary(
                manifest=manifest,
                entry=entry,
                snapshot=snapshot,
                entries=entries,
            )

        def read_exact(path: Path, **_kwargs) -> bytes:
            return raw_by_locator[str(path)]

        drifted = copy.deepcopy(observed)
        drifted["platform_binding"]["hostname"] = "different-host"
        with (
            patch.object(OUTER, "_read_root_file", side_effect=read_exact),
            patch.object(
                OUTER,
                "_current_worker_account_material",
                return_value=drifted,
            ),
            self.assertRaises(OUTER.OuterLaunchError),
        ):
            OUTER._validate_preactivation_boundary(
                manifest=manifest,
                entry=entry,
                snapshot=snapshot,
                entries=entries,
            )

    def test_all_public_contracts_require_identical_closed_binding(self) -> None:
        schemas = {
            path.name: json.loads(path.read_text(encoding="utf-8"))
            for path in (
                SCHEMA_ROOT / "u10-execution-snapshot-manifest-v1.schema.json",
                SCHEMA_ROOT / "u10-root-trust-store-v2.schema.json",
                SCHEMA_ROOT / "broker-attested-execution-envelope-v2.schema.json",
            )
        }
        definitions = [
            schema["$defs"]["preactivation_boundary_binding"]
            for schema in schemas.values()
        ]
        self.assertTrue(all(item == definitions[0] for item in definitions[1:]))
        binding = _chain()[0]["preactivation_boundary_binding"]
        validator = Draft202012Validator(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "$defs": next(iter(schemas.values()))["$defs"],
                "$ref": "#/$defs/preactivation_boundary_binding",
            }
        )
        self.assertEqual(list(validator.iter_errors(binding)), [])
        for field in (
            "candidate_bundle_ref",
            "worker_account_observation_ref",
            "subject_entity_id",
            "worker_principal_entity_id",
            "effective_worker_identity",
        ):
            old = copy.deepcopy(binding)
            old.pop(field)
            with self.subTest(old_contract_missing=field):
                self.assertNotEqual(list(validator.iter_errors(old)), [])


if __name__ == "__main__":
    unittest.main()
