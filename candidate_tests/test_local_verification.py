from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest

from semantic_guard_vnext.local_verification import (
    LocalVerificationError,
    RUN_VERSION,
    RUN_VERSION_V0,
    _validate_environment_snapshot_structure,
    canonical_digest,
    capture_environment,
    capture_subject_manifest,
    execute_local_verification,
    file_digest,
    load_profile,
    validate_run_record,
    verification_source_binding,
    verify_live_subject,
)
from candidate_tests.fixtures.scripts.validate_verification_source import (
    _check_local_verification_run_binding,
)


class LocalVerificationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        (self.root / ".venv/bin").mkdir(parents=True)
        (self.root / "vnext/.venv/bin").mkdir(parents=True)
        (self.root / "vnext/validation").mkdir(parents=True)
        (self.root / ".venv/bin/python").symlink_to(Path(sys.executable).resolve())
        (self.root / "vnext/.venv/bin/python").symlink_to(Path(sys.executable).resolve())
        (self.root / "subject.py").write_text("VALUE = 1\n", encoding="utf-8")
        self.profile_path = self.root / "vnext/validation/profile.json"
        self.output_root = self.root / "vnext/validation/runs"
        self.profile = self._profile(["print('ok')"])
        self._write_profile(self.profile)

    def _profile(self, code: list[str]) -> dict:
        return {
            "schema_version": "semantic-guard-local-verification-profile/v2",
            "profile_id": "profile.local-test",
            "profile_version": "1",
            "repository_root": ".",
            "capture": {
                "inclusion_rule": "Every non-excluded regular test file is included.",
                "excluded_roots": [
                    {"path": ".venv", "reason": "Test interpreter environment."},
                    {"path": "vnext/.venv", "reason": "Test interpreter environment."},
                    {"path": "vnext/validation/runs", "reason": "Generated run evidence."},
                ],
                "excluded_directory_names": ["__pycache__"],
                "excluded_file_names": [".DS_Store"],
                "max_files": 100,
                "max_file_bytes": 1000000,
            },
            "environment": {
                "inherit_names": ["HOME", "PATH", "TMPDIR"],
                "fixed_values": {
                    "NO_COLOR": "1",
                    "PYTHONDONTWRITEBYTECODE": "1",
                },
            },
            "commands": [
                {
                    "command_id": f"verify.test-{index}",
                    "cwd": ".",
                    "argv": ["{vnext_python}", "-c", source],
                    "timeout_seconds": 30,
                    "artifact_effect": "none",
                }
                for index, source in enumerate(code, start=1)
            ],
            "claims": [
                {
                    "claim_id": "local_command_execution",
                    "required_command_ids": [
                        f"verify.test-{index}"
                        for index in range(1, len(code) + 1)
                    ],
                }
            ],
            "limitations": ["Test-only local observation."],
        }

    def _write_profile(self, profile: dict) -> None:
        self.profile_path.write_text(
            json.dumps(profile, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def _write_json(path: Path, value: dict) -> None:
        path.write_text(
            json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def _reseal_environment_tamper(
        self,
        record_path: Path,
        record: dict,
        mutator,
    ) -> dict:
        candidate = deepcopy(record)
        run_directory = record_path.parent
        environment_path = run_directory / candidate["environment"]["locator"]
        environment = json.loads(environment_path.read_text(encoding="utf-8"))
        mutator(environment)
        self._write_json(environment_path, environment)
        candidate["environment"]["file_digest"] = file_digest(environment_path)

        manifest_path = run_directory / candidate["subject"]["locator"]
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["environment_bindings"][0]["content_digest"] = canonical_digest(
            environment
        )
        manifest["manifest_digest"] = canonical_digest(
            {
                key: value
                for key, value in manifest.items()
                if key != "manifest_digest"
            }
        )
        self._write_json(manifest_path, manifest)
        candidate["subject"]["file_digest"] = file_digest(manifest_path)
        candidate["subject"]["identity_digest"] = manifest["manifest_digest"]
        for command in candidate["commands"]:
            command["pre_manifest_identity_digest"] = manifest["manifest_digest"]
            command["post_manifest_identity_digest"] = manifest["manifest_digest"]
        candidate["run_record_digest"] = canonical_digest(
            {
                key: value
                for key, value in candidate.items()
                if key != "run_record_digest"
            }
        )
        self._write_json(record_path, candidate)
        return candidate

    def test_capture_is_deterministic_and_detects_addition(self) -> None:
        profile = load_profile(self.profile_path)
        environment = capture_environment(self.root, profile)
        first = capture_subject_manifest(self.root, profile, environment)
        second = capture_subject_manifest(self.root, profile, environment)
        self.assertEqual(first, second)
        self.assertIn("subject.py", {entry["path"] for entry in first["subject_entries"]})

        (self.root / "added.py").write_text("ADDED = True\n", encoding="utf-8")
        with self.assertRaisesRegex(LocalVerificationError, "expected"):
            verify_live_subject(self.root, profile, environment, first)

    def test_environment_snapshot_structure_rejects_erased_evidence(self) -> None:
        profile = load_profile(self.profile_path)
        environment = capture_environment(self.root, profile)
        for field, erased in (
            ("platform", {}),
            ("installed_distributions", []),
            ("interpreter_distributions", []),
            ("inherited_environment", []),
            ("limitations", []),
        ):
            with self.subTest(field=field):
                candidate = deepcopy(environment)
                candidate[field] = erased
                with self.assertRaises(LocalVerificationError):
                    _validate_environment_snapshot_structure(candidate)

    def test_capture_rejects_symlink_in_active_subject(self) -> None:
        (self.root / "alias.py").symlink_to(self.root / "subject.py")
        profile = load_profile(self.profile_path)
        environment = capture_environment(self.root, profile)
        with self.assertRaisesRegex(LocalVerificationError, "alias.py"):
            capture_subject_manifest(self.root, profile, environment)

    def test_excluded_cache_presence_does_not_change_subject_identity(self) -> None:
        profile = load_profile(self.profile_path)
        environment = capture_environment(self.root, profile)
        first = capture_subject_manifest(self.root, profile, environment)
        (self.root / "__pycache__").mkdir()
        (self.root / "__pycache__/subject.pyc").write_bytes(b"generated")
        (self.root / ".DS_Store").write_bytes(b"generated")
        second = capture_subject_manifest(self.root, profile, environment)
        self.assertEqual(first, second)

    def test_passed_run_is_append_only_and_replayable(self) -> None:
        record_path, record = execute_local_verification(
            root=self.root,
            profile_path=self.profile_path,
            output_root=self.output_root,
            run_id="run.local-test.pass",
        )
        self.assertEqual(record["status"], "passed")
        self.assertFalse((record_path.parent / "INCOMPLETE").exists())
        validate_run_record(
            record,
            run_directory=record_path.parent,
            repository_root=self.root,
            require_current_subject=True,
        )
        binding = verification_source_binding(
            repository_root=self.root,
            run_path=record_path,
        )
        self.assertEqual(binding["status"], "bound")
        self.assertIn("../../subject.py", binding["subject_locators"])

        evidence = {
            "freshness": "stale",
            "subject_binding": binding,
        }
        bridge_errors: list[dict[str, str]] = []
        _check_local_verification_run_binding(
            root=self.root,
            base=self.root / "vnext/validation",
            evidence=evidence,
            evidence_index=0,
            run_path=record_path,
            run_document=record,
            manifest_path=record_path.parent / "subject-manifest.json",
            errors=bridge_errors,
        )
        self.assertEqual(bridge_errors, [])
        evidence["subject_binding"]["command_or_log_refs"] = []
        _check_local_verification_run_binding(
            root=self.root,
            base=self.root / "vnext/validation",
            evidence=evidence,
            evidence_index=0,
            run_path=record_path,
            run_document=record,
            manifest_path=record_path.parent / "subject-manifest.json",
            errors=bridge_errors,
        )
        self.assertTrue(
            any(
                error["code"] == "local_verification_log_refs_mismatch"
                for error in bridge_errors
            )
        )

        for field, expected_code in (
            ("profile_binding", "local_verification_profile_binding_mismatch"),
            ("claim_results", "local_verification_claim_results_mismatch"),
        ):
            with self.subTest(field=field):
                stripped = deepcopy(binding)
                stripped.pop(field)
                field_errors: list[dict[str, str]] = []
                _check_local_verification_run_binding(
                    root=self.root,
                    base=self.root / "vnext/validation",
                    evidence={"freshness": "stale", "subject_binding": stripped},
                    evidence_index=0,
                    run_path=record_path,
                    run_document=record,
                    manifest_path=record_path.parent / "subject-manifest.json",
                    errors=field_errors,
                )
                self.assertIn(expected_code, {item["code"] for item in field_errors})

        with self.assertRaisesRegex(LocalVerificationError, "run.local-test.pass"):
            execute_local_verification(
                root=self.root,
                profile_path=self.profile_path,
                output_root=self.output_root,
                run_id="run.local-test.pass",
            )

    def test_legacy_run_cannot_be_promoted_to_trust_binding(self) -> None:
        legacy_directory = self.output_root / "run.local-test.legacy"
        legacy_directory.mkdir(parents=True)
        legacy_path = legacy_directory / "run.json"
        legacy_path.write_text(
            json.dumps({"schema_version": RUN_VERSION_V0}) + "\n",
            encoding="utf-8",
        )

        with self.assertRaises(LocalVerificationError) as raised:
            verification_source_binding(
                repository_root=self.root,
                run_path=legacy_path,
            )
        self.assertEqual(raised.exception.code, "run_version_not_bindable")

        errors: list[dict[str, str]] = []
        _check_local_verification_run_binding(
            root=self.root,
            base=self.root / "vnext/validation",
            evidence={
                "freshness": "stale",
                "subject_binding": {
                    "environment_ref": None,
                    "command_or_log_refs": [],
                },
            },
            evidence_index=0,
            run_path=legacy_path,
            run_document={"schema_version": RUN_VERSION_V0},
            manifest_path=None,
            errors=errors,
        )
        self.assertEqual(
            [error["code"] for error in errors],
            ["local_verification_run_version_not_bindable"],
        )

    def test_malformed_v1_bridge_returns_structured_error(self) -> None:
        errors: list[dict[str, str]] = []
        _check_local_verification_run_binding(
            root=self.root,
            base=self.root / "vnext/validation",
            evidence={
                "freshness": "stale",
                "subject_binding": {
                    "environment_ref": None,
                    "command_or_log_refs": [],
                },
            },
            evidence_index=0,
            run_path=self.output_root / "malformed/run.json",
            run_document={
                "schema_version": RUN_VERSION
            },
            manifest_path=None,
            errors=errors,
        )
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0]["code"].startswith("local_verification_run_"))

    def test_overlong_run_locator_returns_structured_error(self) -> None:
        record_path, record = execute_local_verification(
            root=self.root,
            profile_path=self.profile_path,
            output_root=self.output_root,
            run_id="run.local-test.overlong-locator",
        )
        candidate = deepcopy(record)
        candidate["profile"]["locator"] = "a" * 10000
        candidate["run_record_digest"] = canonical_digest(
            {
                key: value
                for key, value in candidate.items()
                if key != "run_record_digest"
            }
        )
        errors: list[dict[str, str]] = []
        _check_local_verification_run_binding(
            root=self.root,
            base=self.root / "vnext/validation",
            evidence={
                "freshness": "stale",
                "subject_binding": verification_source_binding(
                    repository_root=self.root,
                    run_path=record_path,
                ),
            },
            evidence_index=0,
            run_path=record_path,
            run_document=candidate,
            manifest_path=record_path.parent / "subject-manifest.json",
            errors=errors,
        )
        self.assertTrue(errors)
        self.assertTrue(errors[0]["code"].startswith("local_verification_run_"))

    def test_subject_mutation_invalidates_successful_command(self) -> None:
        mutation = (
            "from pathlib import Path; "
            "Path('subject.py').write_text('VALUE = 2\\n', encoding='utf-8')"
        )
        self._write_profile(self._profile([mutation]))
        record_path, record = execute_local_verification(
            root=self.root,
            profile_path=self.profile_path,
            output_root=self.output_root,
            run_id="run.local-test.mutation",
        )
        self.assertEqual(record["status"], "invalid")
        self.assertTrue(record["commands"][0]["mutation_detected"])
        self.assertEqual(record["commands"][0]["exit_code"], 0)
        validate_run_record(
            record,
            run_directory=record_path.parent,
            repository_root=self.root,
        )

    def test_profile_rejects_unknown_placeholder(self) -> None:
        profile = deepcopy(self.profile)
        profile["commands"][0]["argv"][0] = "{arbitrary_shell}"
        self._write_profile(profile)
        with self.assertRaisesRegex(LocalVerificationError, "arbitrary_shell"):
            load_profile(self.profile_path)

    def test_run_id_is_one_safe_path_component(self) -> None:
        for run_id in ("a/../../../../escape", "nested/name", "a..b", "/absolute"):
            with self.subTest(run_id=run_id):
                with self.assertRaises(LocalVerificationError) as raised:
                    execute_local_verification(
                        root=self.root,
                        profile_path=self.profile_path,
                        output_root=self.output_root,
                        run_id=run_id,
                    )
                self.assertEqual(raised.exception.code, "invalid_run_id")
        self.assertFalse((self.root.parent / "escape").exists())

    def test_run_replay_rejects_semantic_tampering(self) -> None:
        record_path, record = execute_local_verification(
            root=self.root,
            profile_path=self.profile_path,
            output_root=self.output_root,
            run_id="run.local-test.tamper",
        )

        def rejected(mutator) -> None:
            candidate = deepcopy(record)
            mutator(candidate)
            candidate["run_record_digest"] = canonical_digest(
                {key: value for key, value in candidate.items() if key != "run_record_digest"}
            )
            with self.assertRaises(LocalVerificationError):
                validate_run_record(
                    candidate,
                    run_directory=record_path.parent,
                    repository_root=self.root,
                )

        rejected(lambda value: value["commands"].clear())
        rejected(lambda value: value.__setitem__("run_id", "run.other"))
        rejected(lambda value: value["environment"].__setitem__("locator", "../subject.py"))
        rejected(
            lambda value: value["commands"][0]["executable"].__setitem__(
                "resolved_path", "/nonexistent/python"
            )
        )
        rejected(lambda value: value["commands"][0].__setitem__("status", "failed"))

    def test_run_replay_rejects_temporal_and_limitation_laundering(self) -> None:
        record_path, record = execute_local_verification(
            root=self.root,
            profile_path=self.profile_path,
            output_root=self.output_root,
            run_id="run.local-test.temporal-tamper",
        )

        cases = (
            (
                "run_command_duration_mismatch",
                lambda value: value["commands"][0].__setitem__(
                    "duration_seconds", 9999.0
                ),
            ),
            (
                "run_duration_mismatch",
                lambda value: value.__setitem__("duration_seconds", 9999.0),
            ),
            (
                "run_limitations_mismatch",
                lambda value: value.__setitem__(
                    "limitations", ["No limitations; production qualified."]
                ),
            ),
        )
        for expected_code, mutator in cases:
            with self.subTest(expected_code=expected_code):
                candidate = deepcopy(record)
                mutator(candidate)
                candidate["run_record_digest"] = canonical_digest(
                    {
                        key: value
                        for key, value in candidate.items()
                        if key != "run_record_digest"
                    }
                )
                record_path.write_text(
                    json.dumps(candidate, ensure_ascii=False, indent=2, sort_keys=True)
                    + "\n",
                    encoding="utf-8",
                )
                with self.assertRaises(LocalVerificationError) as raised:
                    validate_run_record(
                        candidate,
                        run_directory=record_path.parent,
                        repository_root=self.root,
                    )
                self.assertEqual(raised.exception.code, expected_code)
        record_path.write_text(
            json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def test_run_replay_rejects_environment_and_tool_laundering(self) -> None:
        (self.root / "uv.lock").write_text("root-lock\n", encoding="utf-8")
        (self.root / "vnext/uv.lock").write_text("vnext-lock\n", encoding="utf-8")
        substitute = Path(sys.executable).resolve()

        def replace_uv(environment: dict) -> None:
            tool = next(
                item
                for item in environment["executables"]
                if item["executable_id"] == "tool.uv"
            )
            tool["invocation_path"] = str(substitute)
            tool["resolved_path"] = str(substitute)
            tool["file_digest"] = file_digest(substitute)

        cases = (
            ("uv-origin", replace_uv, "run_environment_executable_invocation_mismatch"),
            (
                "lock-erasure",
                lambda value: value.__setitem__("lock_files", []),
                "run_environment_lock_binding_mismatch",
            ),
        )
        for label, mutator, expected_code in cases:
            with self.subTest(label=label):
                record_path, record = execute_local_verification(
                    root=self.root,
                    profile_path=self.profile_path,
                    output_root=self.output_root,
                    run_id=f"run.local-test.environment-{label}",
                )
                candidate = self._reseal_environment_tamper(
                    record_path,
                    record,
                    mutator,
                )
                with self.assertRaises(LocalVerificationError) as raised:
                    validate_run_record(
                        candidate,
                        run_directory=record_path.parent,
                        repository_root=self.root,
                    )
                self.assertEqual(raised.exception.code, expected_code)

    def test_verified_artifact_cannot_be_replaced_by_later_command(self) -> None:
        profile = self._profile(
            [
                "from pathlib import Path; "
                "Path(r'{run_dir}/artifacts/x.whl').write_bytes(b'A')",
                "from pathlib import Path; "
                "assert Path(r'{run_dir}/artifacts/x.whl').read_bytes() == b'A'",
                "from pathlib import Path; "
                "Path(r'{run_dir}/artifacts/x.whl').write_bytes(b'B')",
            ]
        )
        profile["commands"][0]["artifact_effect"] = "may_add"
        self._write_profile(profile)

        record_path, record = execute_local_verification(
            root=self.root,
            profile_path=self.profile_path,
            output_root=self.output_root,
            run_id="run.local-test.artifact-replacement",
        )

        self.assertEqual(record["status"], "invalid")
        self.assertEqual(record["commands"][0]["status"], "passed")
        self.assertEqual(record["commands"][1]["status"], "passed")
        self.assertEqual(record["commands"][2]["status"], "invalid")
        self.assertTrue(record["commands"][2]["artifact_mutation_detected"])
        self.assertEqual(record["claims"][0]["status"], "failed")
        validate_run_record(
            record,
            run_directory=record_path.parent,
            repository_root=self.root,
        )

    def test_profile_snapshot_survives_source_profile_change(self) -> None:
        record_path, record = execute_local_verification(
            root=self.root,
            profile_path=self.profile_path,
            output_root=self.output_root,
            run_id="run.local-test.snapshot",
        )
        changed = deepcopy(self.profile)
        changed["limitations"] = ["The source profile changed after the run."]
        self._write_profile(changed)
        validate_run_record(
            record,
            run_directory=record_path.parent,
            repository_root=self.root,
        )
        self.assertEqual(record["profile"]["locator"], "profile.json")

    def test_output_limit_is_bounded_and_invalidates_claim(self) -> None:
        self._write_profile(self._profile(["print('x' * 4096)"]))
        record_path, record = execute_local_verification(
            root=self.root,
            profile_path=self.profile_path,
            output_root=self.output_root,
            run_id="run.local-test.output-limit",
            max_output_bytes=8,
        )
        self.assertEqual(record["status"], "invalid")
        output = record["commands"][0]["stdout"]
        self.assertEqual(output["size_bytes"], 8)
        self.assertGreater(output["observed_size_bytes"], 8)
        self.assertTrue(output["truncated"])
        self.assertEqual(record["claims"][0]["status"], "failed")
        validate_run_record(
            record,
            run_directory=record_path.parent,
            repository_root=self.root,
        )

    def test_timeout_applies_after_parent_exits_with_inherited_pipe(self) -> None:
        profile = self._profile(
            [
                "import subprocess, sys; "
                "subprocess.Popen([sys.executable, '-c', "
                "'import time; time.sleep(3)'], start_new_session=True)"
            ]
        )
        profile["commands"][0]["timeout_seconds"] = 1
        self._write_profile(profile)
        record_path, record = execute_local_verification(
            root=self.root,
            profile_path=self.profile_path,
            output_root=self.output_root,
            run_id="run.local-test.detached-pipe-timeout",
        )

        command = record["commands"][0]
        self.assertEqual(record["status"], "failed")
        self.assertEqual(command["status"], "timed_out")
        self.assertTrue(command["timed_out"])
        self.assertLess(command["duration_seconds"], 2.5)
        self.assertEqual(record["claims"][0]["status"], "failed")
        validate_run_record(
            record,
            run_directory=record_path.parent,
            repository_root=self.root,
        )

    def test_timeout_applies_when_direct_child_closes_output_pipes(self) -> None:
        profile = self._profile(
            ["import os, time; os.close(1); os.close(2); time.sleep(3)"]
        )
        profile["commands"][0]["timeout_seconds"] = 1
        self._write_profile(profile)
        _, record = execute_local_verification(
            root=self.root,
            profile_path=self.profile_path,
            output_root=self.output_root,
            run_id="run.local-test.closed-pipe-timeout",
        )

        command = record["commands"][0]
        self.assertEqual(record["status"], "failed")
        self.assertEqual(command["status"], "timed_out")
        self.assertTrue(command["timed_out"])
        self.assertLess(command["duration_seconds"], 2.5)
        self.assertEqual(record["claims"][0]["status"], "failed")

    def test_command_cannot_rewrite_protected_evidence(self) -> None:
        profile = self._profile(
            [
                "from pathlib import Path; "
                "Path(r'{run_dir}/environment.json').write_text('{}')"
            ]
        )
        self._write_profile(profile)
        with self.assertRaises(LocalVerificationError):
            execute_local_verification(
                root=self.root,
                profile_path=self.profile_path,
                output_root=self.output_root,
                run_id="run.local-test.evidence-mutation",
            )
        self.assertTrue(
            (self.output_root / "run.local-test.evidence-mutation/INCOMPLETE").is_file()
        )


if __name__ == "__main__":
    unittest.main()
