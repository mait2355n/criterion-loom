from __future__ import annotations

import copy

import json

import os

from pathlib import Path

import platform

import subprocess

import tempfile

import unittest

from unittest.mock import patch

from semantic_guard_vnext.environment_resolution import (
    EnvironmentResolutionError,
    canonical_digest,
    file_digest,
)

from semantic_guard_vnext.governed_environment_execution import (
    COMMAND_DIGEST_ENV,
    EXECUTION_NONCE_ENV,
    SUBJECT_MANIFEST_DIGEST_ENV,
    _process_trace_assessment,
    build_managed_environment_v1,
    _execute_governed_command_with_service_v1,
    render_governed_command_v1,
    validate_execution_receipt_v1,
)

from semantic_guard_vnext.qualified_environment import (
    ADOPTION_VERSION,
    ELIGIBILITY_RESOLUTION_VERSION,
    EnvironmentEligibilityService,
    TRACE_FD_ENV,
    artifact_bytes,
    build_adoption_request_v1,
    build_candidate_eligibility_source,
    build_environment_candidate_material,
    environment_profile_ref,
    load_closed_test_manifest_v1,
    render_dependency_lock_verifier_v1,
    validate_adoption_record_v1,
    validate_eligibility_resolution,
    validate_eligibility_source,
    validate_resolved_environment_profile_v1,
    validate_verification_profile_v4,
    verification_profile_ref,
)

REPOSITORY_ROOT = Path(__file__).resolve().parent / "fixtures" / "qualified_profile_repository"

PROFILE_PATH = (
    REPOSITORY_ROOT
    / "vnext/validation/env-path-contracts/local-verification-profile-v4.candidate.json"
)

def _load_profile() -> dict[str, object]:
    return json.loads(PROFILE_PATH.read_text(encoding="utf-8"))

def _reseal(value: dict[str, object], field: str) -> None:
    value.pop(field, None)
    value[field] = canonical_digest(value)

def _flip_digest(digest: dict[str, str]) -> dict[str, str]:
    changed = copy.deepcopy(digest)
    first = changed["value"][0]
    changed["value"] = ("1" if first == "0" else "0") + changed["value"][1:]
    return changed

class U10ProfileContractAdversarialTests(unittest.TestCase):
    def setUp(self) -> None:
        self.profile = _load_profile()

    def test_v4_profile_is_valid_but_has_no_assurance_authority(self) -> None:
        validate_verification_profile_v4(self.profile)
        self.assertEqual(self.profile["formal_authority"], "none")
        self.assertIs(self.profile["positive_assurance_allowed"], False)

    def test_missing_duplicate_and_wrong_role_tool_denominators_are_rejected(self) -> None:
        requirements = self.profile["environment_contract"]["tool_requirements"]

        missing = copy.deepcopy(self.profile)
        missing["environment_contract"]["tool_requirements"] = requirements[:-1]

        duplicate = copy.deepcopy(self.profile)
        duplicate["environment_contract"]["tool_requirements"][-1] = copy.deepcopy(
            requirements[1]
        )

        wrong_role = copy.deepcopy(self.profile)
        wrong_role["environment_contract"]["tool_requirements"][1][
            "logical_role"
        ] = "python_test_runner"

        for name, invalid in (
            ("missing", missing),
            ("duplicate", duplicate),
            ("wrong_role", wrong_role),
        ):
            with self.subTest(name=name), self.assertRaises(
                EnvironmentResolutionError
            ):
                validate_verification_profile_v4(invalid)

    def test_empty_adoption_observation_and_receipt_are_rejected(self) -> None:
        with self.assertRaises(EnvironmentResolutionError):
            validate_adoption_record_v1({})
        with self.assertRaises(EnvironmentResolutionError):
            validate_eligibility_resolution(
                {}, candidate_profile={}, verification_profile={}, source={}
            )
        with self.assertRaises(EnvironmentResolutionError):
            validate_execution_receipt_v1(
                {},
                verification_profile={},
                candidate_profile={},
                source={},
                eligibility_resolution={},
                repository_root=REPOSITORY_ROOT,
            )

    def test_partial_skip_trace_cannot_report_success(self) -> None:
        nonce = "1" * 64
        command_digest = "2" * 64
        manifest_digest = "3" * 64
        expected_test_ids = ["isolated.Smoke.test_executed", "isolated.Smoke.test_skipped"]
        bindings = [
            {
                "module_name": "isolated",
                "source_file": "/fixture/isolated.py",
                "source_digest": "4" * 64,
            }
        ]
        expected_command = {
            "command_digest": {"algorithm": "sha256", "value": command_digest},
            "closed_test_manifest_ref": {
                "content_digest": {"algorithm": "sha256", "value": manifest_digest}
            },
            "interpreter_tool": {"resolved_path": "/fixture/python"},
            "test_source_bindings": bindings,
            "expected_test_ids": expected_test_ids,
            "cwd": "/fixture",
            "active_dependency_import_roots": [],
        }
        common = {
            "trace_protocol": "semantic-guard-process-containment-trace/v1",
            "execution_nonce": nonce,
            "command_digest": command_digest,
            "subject_manifest_digest": manifest_digest,
        }
        records = [
            {
                **common,
                "sequence": 1,
                "event": "containment_activated",
                "outer_probe": "fork_and_non_python_exec_denied",
            },
            {
                **common,
                "sequence": 2,
                "event": "runner_started",
                "executable": "/fixture/python",
                "test_source_bindings": bindings,
                "expected_test_ids": expected_test_ids,
                "cwd": "/fixture",
                "dependency_import_roots": [],
                "isolated": True,
                "no_site": True,
            },
            {
                **common,
                "sequence": 3,
                "event": "test_run_completed",
                "successful": True,
                "tests_run": 2,
                "failures": 0,
                "errors": 0,
                "skipped": 1,
                "test_ids": expected_test_ids,
                "executed_child_count": 0,
            },
        ]
        raw_trace = b"".join(
            json.dumps(record, sort_keys=True).encode("utf-8") + b"\n"
            for record in records
        )

        assessment, result, reasons = _process_trace_assessment(
            raw_trace,
            expected_command=expected_command,
            execution_nonce=nonce,
        )

        self.assertEqual(assessment["trace_status"], "complete_no_children")
        self.assertEqual(result["result_status"], "failed")
        self.assertEqual(result["skipped"], 1)
        self.assertEqual(reasons, [])

    def test_parent_path_pythonpath_and_dyld_are_not_in_managed_environment(self) -> None:
        effective_path = {
            "policy": "managed_minimal_from_adopted_invocation_paths",
            "entries": [
                {
                    "directory": "/qualified/bin",
                    "source_tool_ids": ["python.vnext"],
                }
            ],
            "rendered_value": "/qualified/bin",
            "content_digest": canonical_digest({"path": "/qualified/bin"}),
        }
        resolution = {
            "schema_version": ELIGIBILITY_RESOLUTION_VERSION,
            "resolution_status": "eligible_scoped",
            "environment_use_allowed": True,
            "effective_path": effective_path,
        }
        managed, projection = build_managed_environment_v1(
            self.profile,
            resolution,
            parent_environment={
                "PATH": "/attacker/bin:/usr/bin",
                "PYTHONPATH": "/attacker/python",
                "PYTHONHOME": "/attacker/home",
                "DYLD_INSERT_LIBRARIES": "/attacker/lib.dylib",
                "DYLD_LIBRARY_PATH": "/attacker/lib",
                "UNLISTED_SECRET": "must-not-cross",
            },
        )
        self.assertEqual(managed["PATH"], "/qualified/bin")
        self.assertTrue(
            {
                "LC_ALL",
                "NO_COLOR",
                "PATH",
                "PYTHONDONTWRITEBYTECODE",
                "PYTHONHASHSEED",
            }.issuperset(managed)
        )
        self.assertFalse(
            {
                "PYTHONPATH",
                "PYTHONHOME",
                "DYLD_INSERT_LIBRARIES",
                "DYLD_LIBRARY_PATH",
                "UNLISTED_SECRET",
            }
            & set(managed)
        )
        self.assertEqual(sorted(managed), projection["variable_names"])

    def test_closed_test_manifest_rejects_empty_or_tampered_denominators(self) -> None:
        reference = self.profile["commands"][0]["closed_test_manifest_ref"]
        manifest = load_closed_test_manifest_v1(
            reference,
            repository_root=REPOSITORY_ROOT,
            expected_command_id="verify.u10.containment-smoke",
        )
        self.assertEqual(manifest["test_denominator"]["test_count"], 2)

        tampered_ref = copy.deepcopy(reference)
        tampered_ref["content_digest"] = _flip_digest(
            tampered_ref["content_digest"]
        )
        with self.assertRaises(EnvironmentResolutionError):
            load_closed_test_manifest_v1(
                tampered_ref,
                repository_root=REPOSITORY_ROOT,
                expected_command_id="verify.u10.containment-smoke",
            )

        empty = copy.deepcopy(manifest)
        empty["test_denominator"]["test_count"] = 0
        empty["test_denominator"]["expected_test_ids"] = []
        _reseal(empty, "manifest_digest")
        schema_path = (
            REPOSITORY_ROOT
            / "vnext/validation/env-path-contracts/closed-verification-test-manifest-v1.schema.json"
        )
        from jsonschema import Draft202012Validator

        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        self.assertTrue(list(Draft202012Validator(schema).iter_errors(empty)))

    def test_lock_environment_evidence_contract_is_identical_across_schemas(
        self,
    ) -> None:
        contract_root = REPOSITORY_ROOT / "vnext/validation/env-path-contracts"
        resolved_schema = json.loads(
            (
                contract_root
                / "resolved-local-environment-profile-v1.schema.json"
            ).read_text(encoding="utf-8")
        )
        eligibility_schema = json.loads(
            (
                contract_root
                / "environment-eligibility-resolution-v1.schema.json"
            ).read_text(encoding="utf-8")
        )
        resolved_contract = resolved_schema["$defs"]["lock_environment_match"]
        eligibility_contract = eligibility_schema["$defs"][
            "lock_environment_match"
        ]

        self.assertEqual(
            set(resolved_contract["required"]),
            set(eligibility_contract["required"]),
        )
        self.assertEqual(
            resolved_contract["properties"],
            eligibility_contract["properties"],
        )
        self.assertIs(resolved_contract["unevaluatedProperties"], False)
        self.assertIs(eligibility_contract["unevaluatedProperties"], False)
