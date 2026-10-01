from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator, FormatChecker

import semantic_guard_u10_broker.core as core
from semantic_guard_u10_broker.protected_io import BrokerBoundaryError
from semantic_guard_u10_broker.supervisor import (
    _whole_worker_timeout_seconds,
)


SCHEMA_PATH = (
    Path(__file__).parents[1]
    / "src"
    / "semantic_guard_vnext"
    / "validation"
    / "env-path-contracts"
    / "broker-attested-execution-envelope-v2.schema.json"
)
COMMAND_ID = "verify.u10.phase-budget"


def _digest(label: str) -> dict[str, str]:
    return core.digest_bytes(label.encode("utf-8"))


def _preactivation_boundary() -> dict:
    candidate_hash = _digest("candidate-bundle")["value"]
    candidate_id = f"candidate.u10.{candidate_hash}"

    def snapshot_ref(record_id: str, name: str, label: str) -> dict:
        return {
            "record_id": record_id,
            "locator": f"/snapshot/governance/{name}",
            "artifact_digest": _digest(f"artifact:{label}"),
            "semantic_digest": _digest(f"semantic:{label}"),
        }

    decision_snapshot = snapshot_ref(
        "decision.u10.phase-budget", "decision.json", "decision"
    )
    resolution_snapshot = snapshot_ref(
        "resolution.u10.phase-budget", "resolution.json", "resolution"
    )
    observation_snapshot = snapshot_ref(
        "observation.u10.phase-budget", "observation.json", "observation"
    )
    candidate_snapshot = snapshot_ref(
        candidate_id, "candidate.json", "candidate"
    )
    return {
        "profile": "u10-local-bounded-preactivation-binding/v1",
        "candidate_bundle_ref": {
            "bundle_id": candidate_id,
            "bundle_version": "2.0.0-candidate",
            "candidate_locator": (
                "/Library/Application Support/semantic-guard/u10/candidates/"
                f"{candidate_id}/bundle-manifest.json"
            ),
            "artifact_digest": candidate_snapshot["artifact_digest"],
            "bundle_digest": candidate_snapshot["semantic_digest"],
            "snapshot_artifact_ref": candidate_snapshot,
        },
        "boundary_binding_digest": _digest("boundary"),
        "decision_record_ref": {
            "record_id": "decision.u10.phase-budget",
            "source_locator": "/source/decision.json",
            "source_artifact_digest": decision_snapshot["artifact_digest"],
            "candidate_relative_locator": "governance/decision.json",
            "candidate_artifact_digest": decision_snapshot["artifact_digest"],
            "semantic_digest": decision_snapshot["semantic_digest"],
            "snapshot_artifact_ref": decision_snapshot,
        },
        "worker_account_observation_ref": {
            "record_id": "observation.u10.phase-budget",
            "source_locator": "/source/observation.json",
            "source_artifact_digest": observation_snapshot["artifact_digest"],
            "candidate_relative_locator": "governance/observation.json",
            "candidate_artifact_digest": observation_snapshot[
                "artifact_digest"
            ],
            "semantic_digest": observation_snapshot["semantic_digest"],
            "snapshot_artifact_ref": observation_snapshot,
        },
        "worker_principal_resolution_ref": {
            "record_id": "resolution.u10.phase-budget",
            "source_locator": "/source/resolution.json",
            "source_artifact_digest": resolution_snapshot["artifact_digest"],
            "candidate_relative_locator": "governance/resolution.json",
            "candidate_artifact_digest": resolution_snapshot[
                "artifact_digest"
            ],
            "semantic_digest": resolution_snapshot["semantic_digest"],
            "snapshot_artifact_ref": resolution_snapshot,
        },
        "subject_entity_id": "acfb8b85-2f75-5e82-a641-b3b3b6e023d6",
        "worker_principal_entity_id": (
            "22222222-2222-4222-8222-222222222222"
        ),
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
        "effective_worker_identity": {
            "uid": 501,
            "gid": 20,
            "effective_supplementary_gids": [],
            "umask": 63,
        },
    }


def _snapshot() -> dict:
    return {
        "broker_runtime_ref": {"record_id": "broker.u10.phase-budget"},
        "worker_identity": {
            "uid": 501,
            "gid": 20,
            "account_supplementary_gids": [12, 61],
            "effective_supplementary_gids": [],
            "umask": 63,
            "login_shell": "/bin/zsh",
            "non_login": False,
            "root_prohibited": True,
            "principal_entity_id": (
                "22222222-2222-4222-8222-222222222222"
            ),
            "principal_resolution_digest": _digest("semantic:resolution"),
        },
        "worker_runtime": {
            "phase_budget": {
                "profile": "u10-compositional-worker-budget/v1",
                "pre_environment_reobservation_seconds": 240,
                "post_environment_reobservation_seconds": 240,
                "evidence_finalization_seconds": 30,
                "process_reap_seconds": 10,
            }
        },
        "command_bindings": {
            COMMAND_ID: {
                "governed_command_timeout_seconds": 180,
                "command_definition_digest": _digest("command"),
                "closed_test_manifest_ref": {
                    "manifest_id": "manifest.u10.phase-budget",
                    "manifest_version": "1.0.0",
                    "snapshot_artifact_ref": {
                        "locator": "/snapshot/closed-test-manifest.json",
                        "artifact_digest": _digest("closed-artifact"),
                    },
                    "manifest_digest": _digest("closed-semantic"),
                },
            }
        },
        "snapshot_id": "snapshot.u10.phase-budget",
        "snapshot_version": "1.0.0",
        "manifest_digest": _digest("snapshot-semantic"),
        "preactivation_boundary_binding": _preactivation_boundary(),
        "verification_profile_ref": {
            "profile_id": "profile.u10.phase-budget",
            "profile_version": "1.0.0",
            "snapshot_artifact_ref": {
                "locator": "/snapshot/profile.json",
                "artifact_digest": _digest("profile-artifact"),
            },
            "content_digest": _digest("profile-semantic"),
        },
        "environment_profile_ref": {
            "environment_profile_id": "environment.u10.phase-budget",
            "environment_profile_version": "1.0.0",
            "snapshot_artifact_ref": {
                "locator": "/snapshot/environment.json",
                "artifact_digest": _digest("environment-artifact"),
            },
            "basis_digest": _digest("environment-semantic"),
        },
        "eligibility_source_ref": {
            "source_id": "source.u10.phase-budget",
            "source_version": "1.0.0",
            "snapshot_artifact_ref": {
                "locator": "/snapshot/source.json",
                "artifact_digest": _digest("source-artifact"),
            },
            "source_digest": _digest("source-semantic"),
        },
    }


def _context_and_ref() -> tuple[dict, dict]:
    budget = core.resolve_worker_phase_budget_v1(_snapshot(), COMMAND_ID)
    context = {field: None for field in core._BROKER_CONTEXT_FIELDS_V1}
    context.update(
        {
            "schema_version": "semantic-guard-u10-worker-context/v1",
            "run_id": "run.u10.phase-budget",
            "entry_id": "entry.u10.phase-budget",
            "command_id": COMMAND_ID,
            "phase_budget": budget,
        }
    )
    reference = core.bind_broker_context_phase_budget_v1(
        {
            "run_id": context["run_id"],
            "schema_version": context["schema_version"],
            "locator": (
                "/Library/Application Support/semantic-guard/u10/"
                "spool/run.u10.phase-budget/broker-context.json"
            ),
            "artifact_digest": _digest("context-artifact"),
            "semantic_digest": core.digest_bytes(
                core.canonical_json_bytes(context)
            ),
        },
        budget,
    )
    return context, reference


def _execution_observations() -> tuple[dict, dict]:
    process = {
        "pid": 51001,
        "parent_pid": 51000,
        "process_group_id": 51001,
        "session_id": 51001,
    }
    worker = {
        "process": process,
        "interval": {
            "started_at": "2026-07-20T00:00:01Z",
            "finished_at": "2026-07-20T00:00:05Z",
        },
    }
    broker = {
        "process": {
            **process,
            "observed_at": "2026-07-20T00:00:01.500000Z",
        },
        "exit_code": 0,
        "process_group_quiescence": {
            "process_group_id": 51001,
            "state": "absent",
            "observed_at": "2026-07-20T00:00:05.500000Z",
        },
    }
    return worker, broker


class U10PhaseBudgetBindingTests(unittest.TestCase):
    def test_budget_is_composed_from_snapshot_and_command(self) -> None:
        budget = core.resolve_worker_phase_budget_v1(_snapshot(), COMMAND_ID)
        self.assertEqual(
            budget,
            {
                "profile": "u10-compositional-worker-budget/v1",
                "pre_environment_reobservation_seconds": 240,
                "post_environment_reobservation_seconds": 240,
                "evidence_finalization_seconds": 30,
                "process_reap_seconds": 10,
                "governed_command_timeout_seconds": 180,
                "whole_run_timeout_seconds": 700.0,
            },
        )

    def test_context_and_signed_reference_require_exact_value_and_digest(self) -> None:
        context, reference = _context_and_ref()
        core._validate_broker_context_phase_budget_v1(
            broker_context=context,
            context_ref=reference,
            snapshot=_snapshot(),
            command_id=COMMAND_ID,
        )

        cases: list[tuple[str, dict, dict, str]] = []
        missing_context = copy.deepcopy(context)
        missing_context.pop("phase_budget")
        cases.append(
            (
                "missing_context_field",
                missing_context,
                reference,
                "u10_envelope_context_binding_mismatch",
            )
        )
        extra_context = copy.deepcopy(context)
        extra_context["untrusted_budget_override"] = 1
        cases.append(
            (
                "extra_context_field",
                extra_context,
                reference,
                "u10_envelope_context_binding_mismatch",
            )
        )
        extra_phase = copy.deepcopy(context)
        extra_phase["phase_budget"]["untrusted_phase"] = 1
        cases.append(
            (
                "extra_phase_field",
                extra_phase,
                reference,
                "u10_envelope_phase_budget_binding_mismatch",
            )
        )
        changed_context = copy.deepcopy(context)
        changed_context["phase_budget"][
            "governed_command_timeout_seconds"
        ] = 179
        cases.append(
            (
                "changed_context_value",
                changed_context,
                reference,
                "u10_envelope_phase_budget_binding_mismatch",
            )
        )
        missing_signed = copy.deepcopy(reference)
        missing_signed["phase_budget"].pop("process_reap_seconds")
        cases.append(
            (
                "missing_signed_phase",
                context,
                missing_signed,
                "u10_envelope_phase_budget_binding_mismatch",
            )
        )
        changed_digest = copy.deepcopy(reference)
        changed_digest["phase_budget_digest"] = _digest("forged-budget")
        cases.append(
            (
                "changed_signed_digest",
                context,
                changed_digest,
                "u10_envelope_phase_budget_binding_mismatch",
            )
        )

        for name, observed_context, observed_ref, expected_code in cases:
            with self.subTest(name=name), self.assertRaises(
                BrokerBoundaryError
            ) as observed:
                core._validate_broker_context_phase_budget_v1(
                    broker_context=observed_context,
                    context_ref=observed_ref,
                    snapshot=_snapshot(),
                    command_id=COMMAND_ID,
                )
            self.assertEqual(observed.exception.code, expected_code)

    def test_statement_builder_places_budget_value_and_digest_under_signature(
        self,
    ) -> None:
        snapshot = _snapshot()
        context, reference = _context_and_ref()
        broker_ref = {
            key: value
            for key, value in reference.items()
            if key not in {"phase_budget", "phase_budget_digest"}
        }
        execution_context = {
            "store": {
                "store_id": "store.u10.phase-budget",
                "store_revision_id": "revision.u10.phase-budget.1",
                "store_version": "2.0.0",
                "signing_key": {"key_id": "key.u10.phase-budget"},
                "broker_runtime_version": core.BROKER_VERSION,
                "broker_runtime_ref": snapshot["broker_runtime_ref"],
            },
            "entry": {
                "entry_digest": _digest("entry"),
                "preactivation_boundary_binding": snapshot[
                    "preactivation_boundary_binding"
                ],
                "snapshot_manifest_binding": {
                    "locator": "/snapshot/manifest.json",
                    "artifact_digest": _digest("snapshot-artifact"),
                },
            },
            "snapshot": snapshot,
            "request": {
                "entry_id": context["entry_id"],
                "command_id": COMMAND_ID,
                "request_nonce": "1" * 64,
            },
            "store_history_ref": {"store_id": "store.u10.phase-budget"},
            "nonce_record_path": "/nonce/record.json",
            "nonce_record": {"recorded_at": "2026-07-20T00:00:00Z"},
            "snapshot_command": snapshot["command_bindings"][COMMAND_ID],
        }
        worker_report, broker_observation = _execution_observations()
        with (
            patch.object(core, "read_protected_file", return_value=b"nonce"),
            patch.object(
                core, "_utc_now", return_value="2026-07-20T00:00:07Z"
            ),
        ):
            statement = core.build_statement_skeleton_v2(
                context=execution_context,
                envelope_id="envelope.u10.phase-budget",
                execution_nonce="2" * 64,
                worker_launch_contract={},
                worker_reported_observation=worker_report,
                broker_execution_observation=broker_observation,
                broker_context_ref=broker_ref,
                worker_outcome_ref={},
                receipt_ref={},
                receipt_interval={
                    "started_at": "2026-07-20T00:00:02Z",
                    "finished_at": "2026-07-20T00:00:04Z",
                },
                started_at="2026-07-20T00:00:00Z",
                finished_at="2026-07-20T00:00:06Z",
            )
        self.assertEqual(statement["broker_context_ref"], reference)
        self.assertEqual(statement["started_at"], "2026-07-20T00:00:00Z")
        self.assertEqual(statement["finished_at"], "2026-07-20T00:00:06Z")
        self.assertEqual(
            statement["worker_reported_observation"], worker_report
        )
        self.assertEqual(
            statement["broker_execution_observation"], broker_observation
        )

    def test_non_finite_phase_budget_and_canonical_json_are_rejected(
        self,
    ) -> None:
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                snapshot = _snapshot()
                snapshot["worker_runtime"]["phase_budget"][
                    "process_reap_seconds"
                ] = value
                with self.assertRaises(BrokerBoundaryError) as resolved:
                    core.resolve_worker_phase_budget_v1(snapshot, COMMAND_ID)
                self.assertEqual(
                    resolved.exception.code,
                    "u10_worker_phase_budget_invalid",
                )
                with self.assertRaises(BrokerBoundaryError) as supervised:
                    _whole_worker_timeout_seconds(snapshot, COMMAND_ID)
                self.assertEqual(
                    supervised.exception.code,
                    "u10_worker_phase_budget_invalid",
                )
                with self.assertRaises(BrokerBoundaryError) as canonical:
                    core.canonical_json_bytes({"non_finite": value})
                self.assertEqual(
                    canonical.exception.code,
                    "u10_canonical_json_invalid",
                )

    def test_root_worker_receipt_interval_order_and_root_observation_bounds(
        self,
    ) -> None:
        worker, broker = _execution_observations()
        arguments = {
            "worker_reported_observation": worker,
            "broker_execution_observation": broker,
            "receipt_started_at": "2026-07-20T00:00:02Z",
            "receipt_finished_at": "2026-07-20T00:00:04Z",
            "started_at": "2026-07-20T00:00:00Z",
            "finished_at": "2026-07-20T00:00:06Z",
            "attested_at": "2026-07-20T00:00:07Z",
        }
        core._validate_execution_observations_v2(**arguments)

        # No relative order is imposed between worker start and the immediate
        # root process observation.
        process_before_worker = copy.deepcopy(arguments)
        process_before_worker["broker_execution_observation"]["process"][
            "observed_at"
        ] = "2026-07-20T00:00:00.500000Z"
        core._validate_execution_observations_v2(**process_before_worker)

        cases = {}
        root_after_worker = copy.deepcopy(arguments)
        root_after_worker["started_at"] = "2026-07-20T00:00:01.100000Z"
        cases["root_after_worker"] = root_after_worker
        receipt_before_worker = copy.deepcopy(arguments)
        receipt_before_worker["receipt_started_at"] = (
            "2026-07-20T00:00:00.500000Z"
        )
        cases["receipt_before_worker"] = receipt_before_worker
        worker_before_receipt_end = copy.deepcopy(arguments)
        worker_before_receipt_end["worker_reported_observation"][
            "interval"
        ]["finished_at"] = "2026-07-20T00:00:03Z"
        cases["worker_before_receipt_end"] = worker_before_receipt_end
        process_before_root = copy.deepcopy(arguments)
        process_before_root["broker_execution_observation"]["process"][
            "observed_at"
        ] = "2026-07-19T23:59:59Z"
        cases["process_before_root"] = process_before_root
        quiescence_after_root = copy.deepcopy(arguments)
        quiescence_after_root["broker_execution_observation"][
            "process_group_quiescence"
        ]["observed_at"] = "2026-07-20T00:00:07Z"
        cases["quiescence_after_root"] = quiescence_after_root

        for name, candidate in cases.items():
            with self.subTest(name=name), self.assertRaises(
                BrokerBoundaryError
            ) as observed:
                core._validate_execution_observations_v2(**candidate)
            self.assertEqual(observed.exception.code, "u10_time_order_invalid")

    def test_broker_and_worker_process_identifiers_cannot_diverge(self) -> None:
        worker, broker = _execution_observations()
        for field in ("pid", "process_group_id", "session_id"):
            changed_worker = copy.deepcopy(worker)
            changed_worker["process"][field] += 1
            with self.subTest(field=field), self.assertRaises(
                BrokerBoundaryError
            ) as observed:
                core._validate_execution_observations_v2(
                    worker_reported_observation=changed_worker,
                    broker_execution_observation=broker,
                    receipt_started_at="2026-07-20T00:00:02Z",
                    receipt_finished_at="2026-07-20T00:00:04Z",
                    started_at="2026-07-20T00:00:00Z",
                    finished_at="2026-07-20T00:00:06Z",
                )
            self.assertEqual(
                observed.exception.code,
                "u10_broker_worker_process_mismatch",
            )

    def test_observation_schema_requires_root_evidence_and_closed_shapes(
        self,
    ) -> None:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        projection_schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$defs": schema["$defs"],
            "type": "object",
            "required": [
                "worker_reported_observation",
                "broker_execution_observation",
            ],
            "properties": {
                "worker_reported_observation": {
                    "$ref": "#/$defs/worker_reported_observation"
                },
                "broker_execution_observation": {
                    "$ref": "#/$defs/broker_execution_observation"
                },
            },
            "unevaluatedProperties": False,
        }
        validator = Draft202012Validator(
            projection_schema, format_checker=FormatChecker()
        )
        worker, broker = _execution_observations()
        valid = {
            "worker_reported_observation": worker,
            "broker_execution_observation": broker,
        }
        self.assertEqual(list(validator.iter_errors(valid)), [])

        self_report_only = {
            "worker_reported_observation": copy.deepcopy(worker)
        }
        extra_root_claim = copy.deepcopy(valid)
        extra_root_claim["broker_execution_observation"]["untrusted"] = True
        nonzero_exit = copy.deepcopy(valid)
        nonzero_exit["broker_execution_observation"]["exit_code"] = 1
        malformed_time = copy.deepcopy(valid)
        malformed_time["broker_execution_observation"]["process"][
            "observed_at"
        ] = "not-a-time"
        for name, candidate in (
            ("self_report_only", self_report_only),
            ("extra_root_claim", extra_root_claim),
            ("nonzero_exit", nonzero_exit),
            ("malformed_time", malformed_time),
        ):
            with self.subTest(name=name):
                self.assertNotEqual(
                    list(validator.iter_errors(candidate)), []
                )

    def test_observation_validator_rejects_missing_root_mapping(self) -> None:
        worker, _broker = _execution_observations()
        with self.assertRaises(BrokerBoundaryError) as observed:
            core._validate_execution_observations_v2(
                worker_reported_observation=worker,
                broker_execution_observation=None,  # type: ignore[arg-type]
                receipt_started_at="2026-07-20T00:00:02Z",
                receipt_finished_at="2026-07-20T00:00:04Z",
                started_at="2026-07-20T00:00:00Z",
                finished_at="2026-07-20T00:00:06Z",
            )
        self.assertEqual(
            observed.exception.code,
            "u10_broker_execution_observation_invalid",
        )

    def test_schema_rejects_missing_extra_or_invalid_phase_budget(self) -> None:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        validator = Draft202012Validator(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "$defs": schema["$defs"],
                "$ref": "#/$defs/broker_context_ref",
            }
        )
        _context, reference = _context_and_ref()
        self.assertEqual(list(validator.iter_errors(reference)), [])

        missing = copy.deepcopy(reference)
        missing.pop("phase_budget")
        extra = copy.deepcopy(reference)
        extra["phase_budget"]["untrusted_phase"] = 1
        invalid = copy.deepcopy(reference)
        invalid["phase_budget"]["whole_run_timeout_seconds"] = 1
        for name, candidate in (
            ("missing", missing),
            ("extra", extra),
            ("invalid", invalid),
        ):
            with self.subTest(name=name):
                self.assertNotEqual(list(validator.iter_errors(candidate)), [])


if __name__ == "__main__":
    unittest.main()
