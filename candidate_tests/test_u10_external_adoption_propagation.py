from __future__ import annotations

import copy
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from semantic_guard_u10_broker import core
from semantic_guard_u10_broker.protected_io import BrokerBoundaryError
from semantic_guard_u10_broker.supervisor import (
    _environment_adoption_context_v2,
    _validate_worker_outcome,
    execute_root_broker_request_v2,
)


SCRIPT_PATH = Path(__file__).parent / "fixtures" / "scripts" / "u10_snapshot_worker.py"
SCHEMA_ROOT = Path(__file__).parents[1] / "src" / "semantic_guard_vnext" / "validation" / "env-path-contracts"


def _load_worker():
    specification = importlib.util.spec_from_file_location(
        "u10_external_adoption_worker_test",
        SCRIPT_PATH,
    )
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    try:
        specification.loader.exec_module(module)
    finally:
        sys.modules.pop(specification.name, None)
    return module


worker = _load_worker()


def _digest(label: str) -> dict[str, str]:
    return core.digest_bytes(label.encode("utf-8"))


def _environment_adoption() -> dict:
    value = {
        "schema_version": "semantic-guard-u10-snapshot-environment-adoption/v1",
        "adoption_id": "adoption.u10.propagation-test",
        "adoption_version": "1.0.0-test",
        "record_kind": "snapshot_environment_adoption_decision",
        "human_decision": "accept",
        "formal_authority": "none",
        "positive_assurance_allowed": False,
    }
    value["adoption_digest"] = core.digest_bytes(core.canonical_json_bytes(value))
    return value


def _environment_adoption_ref(adoption: dict) -> dict:
    return {
        "record_id": adoption["adoption_id"],
        "locator": (
            "/Library/Application Support/semantic-guard/u10/authorizations/"
            f"{adoption['adoption_id']}.json"
        ),
        "artifact_digest": core.digest_bytes(
            core.canonical_json_bytes(adoption) + b"\n"
        ),
        "semantic_digest": adoption["adoption_digest"],
    }


def _trusted_context() -> dict:
    adoption = _environment_adoption()
    return {
        "request": {
            "entry_id": "entry.u10.propagation-test",
            "command_id": "verify.u10.propagation-test",
            "request_nonce": "a" * 64,
        },
        "receipt_id": "receipt.u10.propagation-test",
        "environment_adoption": adoption,
        "environment_adoption_ref": _environment_adoption_ref(adoption),
        "nonce_record": {"recorded_at": "2026-07-20T00:00:00Z"},
        "snapshot": {
            "worker_identity": {
                "uid": 501,
                "gid": 20,
                "effective_supplementary_gids": [],
                "umask": 63,
            },
            "worker_runtime": {"worker_version": "u10-worker/v2"},
            "eligibility_source_ref": {"source_digest": _digest("source")},
            "verification_profile_ref": {"content_digest": _digest("profile")},
            "environment_profile_ref": {"basis_digest": _digest("environment")},
        },
    }


def _receipt(context: dict) -> dict:
    adoption = context["environment_adoption"]
    value = {
        "receipt_id": context["receipt_id"],
        "command_id": context["request"]["command_id"],
        "execution_nonce": "b" * 64,
        "execution_status": "passed",
        "trust_source_ref": {
            "source_digest": context["snapshot"]["eligibility_source_ref"][
                "source_digest"
            ]
        },
        "verification_profile_ref": {
            "content_digest": context["snapshot"]["verification_profile_ref"][
                "content_digest"
            ]
        },
        "environment_profile_ref": {
            "basis_digest": context["snapshot"]["environment_profile_ref"][
                "basis_digest"
            ]
        },
        "adoption_ref": {
            "adoption_id": adoption["adoption_id"],
            "adoption_version": adoption["adoption_version"],
            "adoption_digest": adoption["adoption_digest"],
        },
        "started_at": "2026-07-20T00:00:02Z",
        "finished_at": "2026-07-20T00:00:03Z",
    }
    value["receipt_digest"] = core.digest_bytes(core.canonical_json_bytes(value))
    return value


def _outcome(
    context: dict, worker_directory: Path, receipt: dict
) -> tuple[dict, bytes]:
    raw = (
        json.dumps(
            receipt,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    pid = 52001
    return (
        {
            "schema_version": "semantic-guard-u10-worker-outcome/v1",
            "worker_version": context["snapshot"]["worker_runtime"]["worker_version"],
            "run_id": "run.u10.propagation-test",
            "entry_id": context["request"]["entry_id"],
            "command_id": context["request"]["command_id"],
            "request_nonce": context["request"]["request_nonce"],
            "worker_identity": {
                "uid": 501,
                "gid": 20,
                "supplementary_gids": [],
                "umask": 63,
            },
            "launch_observation": {
                "pid": pid,
                "parent_pid": os.getpid(),
                "process_group_id": pid,
                "session_id": pid,
            },
            "receipt_locator": str(worker_directory / "receipt.json"),
            "receipt_artifact_digest": core.digest_bytes(raw),
            "receipt_semantic_digest": receipt["receipt_digest"],
            "execution_nonce": receipt["execution_nonce"],
            "execution_status": receipt["execution_status"],
            "started_at": "2026-07-20T00:00:01Z",
            "finished_at": "2026-07-20T00:00:04Z",
            "formal_authority": "none",
            "positive_assurance_allowed": False,
        },
        raw,
    )


def _broker_process() -> dict:
    return {
        "pid": 52001,
        "parent_pid": os.getpid(),
        "process_group_id": 52001,
        "session_id": 52001,
        "observed_at": "2026-07-20T00:00:00.500000Z",
    }


class U10ExternalAdoptionPropagationTests(unittest.TestCase):
    def test_execution_context_rejects_noncanonical_adoption_record(self) -> None:
        adoption = _environment_adoption()
        raw = (
            json.dumps(
                adoption,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
        path = core.AUTHORIZATION_ROOT / f"{adoption['adoption_id']}.json"
        reference = core._exact_root_record_ref_v1(
            record_id=adoption["adoption_id"],
            path=path,
            raw=raw,
            semantic_digest=adoption["adoption_digest"],
        )
        with (
            patch.object(
                core,
                "_load_sealed_root_record_v1",
                return_value=(adoption, raw, path),
            ),
            self.assertRaises(BrokerBoundaryError) as observed,
        ):
            core._load_execution_environment_adoption_v1(
                snapshot={"environment_adoption_ref": reference},
                entry={"environment_adoption_binding": reference},
                entry_id="entry.u10.propagation-test",
            )
        self.assertEqual(
            observed.exception.code,
            "u10_snapshot_environment_adoption_noncanonical",
        )

    def test_v3_verifier_requires_v2_store_activation_basis(self) -> None:
        authorization = {
            "store_activation_basis_ref": {"record_id": "legacy-basis"}
        }
        with (
            patch.object(
                core,
                "_validate_store_activation_authorization_v1",
                return_value=authorization,
            ),
            patch.object(
                core,
                "_load_store_activation_basis_v2",
                side_effect=BrokerBoundaryError(
                    "u10_store_activation_basis_invalid", "legacy v1"
                ),
            ),
            patch.object(
                core, "_verify_broker_attested_envelope_with_store_v2"
            ) as generic,
            self.assertRaises(BrokerBoundaryError) as observed,
        ):
            core._verify_broker_attested_envelope_with_store_v3(
                {}, store={}
            )
        self.assertEqual(
            observed.exception.code, "u10_store_activation_basis_invalid"
        )
        generic.assert_not_called()

    def test_retired_v2_operation_does_not_silently_emit_v3(self) -> None:
        with self.assertRaises(BrokerBoundaryError) as captured:
            execute_root_broker_request_v2({})
        self.assertEqual(
            captured.exception.code,
            "u10_broker_execution_contract_v2_retired",
        )

    def test_worker_validates_exact_record_and_passes_external_adoption(self) -> None:
        context = _trusted_context()
        context["source_ref"] = {"source_digest": _digest("source")}
        captured: dict = {}

        class Service:
            def __init__(self, source, **keywords) -> None:
                captured["source"] = source
                captured.update(keywords)

        qualified = types.SimpleNamespace(EnvironmentEligibilityService=Service)
        source = {"source_id": "source.u10.propagation-test"}
        service = worker._build_environment_eligibility_service(
            qualified,
            source,
            context,
            Path("/snapshot"),
        )
        self.assertIsInstance(service, Service)
        self.assertEqual(captured["external_adoption"], context["environment_adoption"])
        self.assertEqual(captured["expected_source_digest"], _digest("source"))

    def test_worker_rejects_tampered_adoption_bindings(self) -> None:
        cases = {}
        changed_record_id = _trusted_context()
        changed_record_id["environment_adoption_ref"]["record_id"] = "adoption.forged"
        cases["record_id"] = changed_record_id
        changed_locator = _trusted_context()
        changed_locator["environment_adoption_ref"]["locator"] += ".forged"
        cases["locator"] = changed_locator
        changed_artifact = _trusted_context()
        changed_artifact["environment_adoption_ref"]["artifact_digest"] = _digest(
            "forged"
        )
        cases["artifact_digest"] = changed_artifact
        changed_semantic = _trusted_context()
        changed_semantic["environment_adoption_ref"]["semantic_digest"] = _digest(
            "forged"
        )
        cases["semantic_digest"] = changed_semantic
        changed_body = _trusted_context()
        changed_body["environment_adoption"]["human_decision"] = "reject"
        changed_body["environment_adoption_ref"]["artifact_digest"] = core.digest_bytes(
            worker._canonical_json_record_bytes(changed_body["environment_adoption"])
        )
        cases["sealed_body"] = changed_body

        for name, context in cases.items():
            with self.subTest(name=name), self.assertRaises(RuntimeError):
                worker._validate_environment_adoption_binding(context)

    def test_supervisor_projects_only_exact_adoption_context(self) -> None:
        context = _trusted_context()
        projected = _environment_adoption_context_v2(context)
        self.assertEqual(
            set(projected),
            {"environment_adoption_ref", "environment_adoption"},
        )
        self.assertEqual(
            projected["environment_adoption"], context["environment_adoption"]
        )
        self.assertEqual(
            projected["environment_adoption_ref"],
            context["environment_adoption_ref"],
        )

        for field in ("environment_adoption", "environment_adoption_ref"):
            changed = _trusted_context()
            changed.pop(field)
            with (
                self.subTest(missing=field),
                self.assertRaises(BrokerBoundaryError) as observed,
            ):
                _environment_adoption_context_v2(changed)
            self.assertEqual(
                observed.exception.code,
                "u10_environment_adoption_context_binding_mismatch",
            )

        tampered_bindings = {}
        wrong_locator = _trusted_context()
        wrong_locator["environment_adoption_ref"]["locator"] = "/tmp/adoption.json"
        tampered_bindings["locator"] = wrong_locator
        wrong_artifact = _trusted_context()
        wrong_artifact["environment_adoption_ref"]["artifact_digest"] = _digest(
            "forged"
        )
        tampered_bindings["artifact_digest"] = wrong_artifact
        wrong_semantic = _trusted_context()
        wrong_semantic["environment_adoption_ref"]["semantic_digest"] = _digest(
            "forged"
        )
        tampered_bindings["semantic_digest"] = wrong_semantic

        for name, changed in tampered_bindings.items():
            with (
                self.subTest(tampered=name),
                self.assertRaises(BrokerBoundaryError) as observed,
            ):
                _environment_adoption_context_v2(changed)
            self.assertEqual(
                observed.exception.code,
                "u10_environment_adoption_context_binding_mismatch",
            )

    def test_supervisor_receipt_must_repeat_exact_adoption_ref(self) -> None:
        context = _trusted_context()
        receipt = _receipt(context)
        with tempfile.TemporaryDirectory() as temporary:
            worker_directory = Path(temporary)
            outcome, raw = _outcome(context, worker_directory, receipt)
            with patch(
                "semantic_guard_u10_broker.supervisor.read_protected_file",
                return_value=raw,
            ):
                observed, observed_raw = _validate_worker_outcome(
                    outcome,
                    context=context,
                    run_id=outcome["run_id"],
                    worker_directory=worker_directory,
                    broker_process_observation=_broker_process(),
                )
            self.assertEqual(observed, receipt)
            self.assertEqual(observed_raw, raw)

            changed = copy.deepcopy(receipt)
            changed["adoption_ref"]["adoption_version"] = "forged"
            changed.pop("receipt_digest")
            changed["receipt_digest"] = core.digest_bytes(
                core.canonical_json_bytes(changed)
            )
            changed_outcome, changed_raw = _outcome(
                context,
                worker_directory,
                changed,
            )
            with (
                patch(
                    "semantic_guard_u10_broker.supervisor.read_protected_file",
                    return_value=changed_raw,
                ),
                self.assertRaises(BrokerBoundaryError) as raised,
            ):
                _validate_worker_outcome(
                    changed_outcome,
                    context=context,
                    run_id=changed_outcome["run_id"],
                    worker_directory=worker_directory,
                    broker_process_observation=_broker_process(),
                )
            self.assertEqual(
                raised.exception.code,
                "u10_worker_receipt_binding_mismatch",
            )

    def test_v3_schema_requires_candidate_source_adoption_and_context_v2(self) -> None:
        v2 = json.loads(
            (
                SCHEMA_ROOT / "broker-attested-execution-envelope-v2.schema.json"
            ).read_text(encoding="utf-8")
        )
        v3 = json.loads(
            (
                SCHEMA_ROOT / "broker-attested-execution-envelope-v3.schema.json"
            ).read_text(encoding="utf-8")
        )
        Draft202012Validator.check_schema(v3)
        self.assertIn(
            "environment_adoption_ref",
            v3["properties"]["signed_statement"]["required"],
        )
        self.assertEqual(
            v3["$defs"]["eligibility_source_ref"]["properties"]["lifecycle_state"][
                "const"
            ],
            "candidate",
        )
        self.assertEqual(
            v3["$defs"]["broker_context_ref"]["properties"]["schema_version"]["const"],
            "semantic-guard-u10-worker-context/v2",
        )

        registry = (
            Registry()
            .with_resource(v2["$id"], Resource.from_contents(v2))
            .with_resource(v3["$id"], Resource.from_contents(v3))
        )

        def validator(definition: str) -> Draft202012Validator:
            return Draft202012Validator(
                {"$ref": f"{v3['$id']}#/$defs/{definition}"},
                registry=registry,
            )

        adoption = _environment_adoption()
        adoption_ref = _environment_adoption_ref(adoption)
        self.assertEqual(
            list(validator("environment_adoption_ref").iter_errors(adoption_ref)),
            [],
        )
        wrong_root = copy.deepcopy(adoption_ref)
        wrong_root["locator"] = "/tmp/adoption.json"
        self.assertNotEqual(
            list(validator("environment_adoption_ref").iter_errors(wrong_root)),
            [],
        )

        source_ref = {
            "source_id": "source.u10.propagation-test",
            "source_version": "1.0.0-test",
            "lifecycle_state": "candidate",
            "locator": (
                "/Library/Application Support/semantic-guard/u10/snapshots/"
                "snapshot.test/source.json"
            ),
            "artifact_digest": _digest("source-artifact"),
            "source_digest": _digest("source-semantic"),
        }
        self.assertEqual(
            list(validator("eligibility_source_ref").iter_errors(source_ref)),
            [],
        )
        source_ref["lifecycle_state"] = "adopted"
        self.assertNotEqual(
            list(validator("eligibility_source_ref").iter_errors(source_ref)),
            [],
        )


if __name__ == "__main__":
    unittest.main()
