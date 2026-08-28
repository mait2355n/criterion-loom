from __future__ import annotations

from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "validation/verification-source.json"
RESULT_SCHEMA = ROOT / "validation/verification-validation-result.schema.json"
GAP_REGISTER = ROOT / "validation/verification-gap-register.json"
CONSTITUTION = ROOT / "constitution/semantic-guard-constitution.yaml"
SCRIPT = ROOT / "scripts/validate_verification_source.py"


class VerificationSourceValidatorTests(unittest.TestCase):
    def _run(self, *arguments: str) -> tuple[subprocess.CompletedProcess[str], dict]:
        completed = subprocess.run(
            [sys.executable, str(SCRIPT), *arguments],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=20.0,
            check=False,
        )
        try:
            result = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:  # pragma: no cover - assertion aid.
            self.fail(
                f"validator did not emit JSON: returncode={completed.returncode}, "
                f"stdout={completed.stdout!r}, stderr={completed.stderr!r}, error={exc}"
            )
        schema = json.loads(RESULT_SCHEMA.read_text(encoding="utf-8"))
        Draft202012Validator(schema).validate(result)
        return completed, result

    def _write_source(self, source: dict) -> Path:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".json",
            prefix="verification-source-test-",
            dir=ROOT / "validation",
            delete=False,
        ) as handle:
            json.dump(source, handle, ensure_ascii=False)
            handle.write("\n")
            path = Path(handle.name)
        self.addCleanup(path.unlink, missing_ok=True)
        return path

    def _write_json_artifact(self, value: dict, prefix: str) -> Path:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".json",
            prefix=prefix,
            dir=ROOT / "validation",
            delete=False,
        ) as handle:
            json.dump(value, handle, ensure_ascii=False, sort_keys=True)
            handle.write("\n")
            path = Path(handle.name)
        self.addCleanup(path.unlink, missing_ok=True)
        return path

    def _source(self) -> dict:
        return json.loads(SOURCE.read_text(encoding="utf-8"))

    def _gap_register(self) -> dict:
        return json.loads(GAP_REGISTER.read_text(encoding="utf-8"))

    def _refresh_gap_set_digest(self, register: dict) -> None:
        canonical = json.dumps(
            sorted(register["gaps"], key=lambda gap: gap["gap_id"]),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        register["gap_set_digest"]["value"] = hashlib.sha256(canonical).hexdigest()

    def _write_gap_register(self, register: dict) -> Path:
        self._refresh_gap_set_digest(register)
        return self._write_json_artifact(register, "verification-gap-register-test-")

    def test_default_source_and_projection_pass(self) -> None:
        completed, result = self._run()
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(set(result["checks"].values()), {"passed"})
        self.assertRegex(result["execution"]["validator_sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(result["subject"]["schema_sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(result["subject"]["projection_sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(
            result["subject"]["gap_register_sha256"], r"^[0-9a-f]{64}$"
        )
        self.assertRegex(result["subject"]["gap_set_sha256"], r"^[0-9a-f]{64}$")
        source = self._source()
        expected_gap_count = sum(
            len(item[field])
            for collection, field in (
                ("verification_items", "unproven_scope"),
                ("verification_items", "residual_risks"),
                ("implementation_conformance_items", "remaining_obligations"),
            )
            for item in source[collection]
        )
        self.assertEqual(result["counts"]["gap_records"], expected_gap_count)

    def test_canonical_constitution_rejects_stale_origin_digest(self) -> None:
        origin_digest = hashlib.sha256(
            (ROOT / "docs/prototypes/origin-requirement.md").read_bytes()
        ).hexdigest()
        constitution_text = CONSTITUTION.read_text(encoding="utf-8")
        tampered = constitution_text.replace(
            f"value: {origin_digest}",
            f"value: {'0' * 64}",
            1,
        )
        self.assertNotEqual(tampered, constitution_text)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".yaml",
            prefix="constitution-stale-origin-test-",
            dir=ROOT / "constitution",
            delete=False,
        ) as handle:
            handle.write(tampered)
            constitution_path = Path(handle.name)
        self.addCleanup(constitution_path.unlink, missing_ok=True)

        constitution_digest = hashlib.sha256(
            constitution_path.read_bytes()
        ).hexdigest()
        constitution_locator = f"../constitution/{constitution_path.name}"
        source = self._source()
        upstream = next(
            item
            for item in source["upstream_sources"]
            if item["ref"]["entity_id"] == "constitution.semantic-guard.r0"
        )
        upstream["path"] = constitution_locator
        upstream["version_or_digest"] = f"sha256:{constitution_digest}"
        evidence = next(
            item
            for item in source["evidence_observations"]
            if item["entity_id"].startswith("evidence.constitution.snapshot.")
        )
        evidence["source_path"] = constitution_locator
        evidence["content_digest"]["value"] = constitution_digest
        evidence["subject_binding"]["subject_locators"] = [constitution_locator]
        evidence["subject_binding"]["digest_bindings"] = [
            {
                "subject_locator": constitution_locator,
                "digest": {
                    "algorithm": "sha256",
                    "value": constitution_digest,
                },
            }
        ]
        evidence["observation_locators"] = [constitution_locator]
        evidence["detail_refs"] = [constitution_locator]
        source_path = self._write_source(source)

        completed, result = self._run("--source", str(source_path))
        self.assertEqual(completed.returncode, 1)
        self.assertTrue(
            any(
                error["code"] == "constitution_origin_digest_mismatch"
                for error in result["errors"]
            )
        )

    def test_gap_register_rejects_removed_declared_gap(self) -> None:
        register = self._gap_register()
        removed = register["gaps"].pop()
        register_path = self._write_gap_register(register)
        completed, result = self._run("--gap-register", str(register_path))
        self.assertEqual(completed.returncode, 1)
        self.assertTrue(
            any(
                error["code"] == "missing_gap_record"
                and removed["gap_id"] in error["message"]
                for error in result["errors"]
            )
        )
        self.assertEqual(result["checks"]["gap_register"], "failed")

    def test_gap_register_detects_new_source_gap_omission(self) -> None:
        source = self._source()
        source["verification_items"][0]["unproven_scope"].append(
            "A newly declared gap must not disappear from the register."
        )
        source_path = self._write_source(source)
        register = self._gap_register()
        register["source"]["content_digest"]["value"] = hashlib.sha256(
            source_path.read_bytes()
        ).hexdigest()
        register_path = self._write_gap_register(register)
        completed, result = self._run(
            "--source",
            str(source_path),
            "--gap-register",
            str(register_path),
        )
        self.assertEqual(completed.returncode, 1)
        self.assertTrue(
            any(error["code"] == "missing_gap_record" for error in result["errors"])
        )

    def test_gap_register_rejects_duplicate_identity_and_locator(self) -> None:
        register = self._gap_register()
        register["gaps"].append(deepcopy(register["gaps"][0]))
        register_path = self._write_gap_register(register)
        completed, result = self._run("--gap-register", str(register_path))
        codes = {error["code"] for error in result["errors"]}
        self.assertEqual(completed.returncode, 1)
        self.assertIn("duplicate_gap_id", codes)
        self.assertIn("duplicate_gap_source_locator", codes)

    def test_gap_register_rejects_changed_locator(self) -> None:
        register = self._gap_register()
        gap = register["gaps"][0]
        prefix, _, raw_index = gap["source_locator"].rpartition("/")
        gap["source_locator"] = f"{prefix}/{int(raw_index) + 1}"
        register_path = self._write_gap_register(register)
        completed, result = self._run("--gap-register", str(register_path))
        self.assertEqual(completed.returncode, 1)
        self.assertTrue(
            any(
                error["code"] == "gap_source_locator_mismatch"
                for error in result["errors"]
            )
        )

    def test_gap_register_rejects_changed_content_digest(self) -> None:
        register = self._gap_register()
        register["gaps"][0]["content_digest"]["value"] = "0" * 64
        register_path = self._write_gap_register(register)
        completed, result = self._run("--gap-register", str(register_path))
        self.assertEqual(completed.returncode, 1)
        self.assertTrue(
            any(
                error["code"] == "gap_content_digest_mismatch"
                for error in result["errors"]
            )
        )

    def test_gap_register_rejects_dangling_unresolved_disposition(self) -> None:
        register = self._gap_register()
        register["gaps"][0]["disposition"] = {
            "kind": "canonical_unresolved",
            "unresolved_ref": {
                "reference_kind": "ref",
                "entity_id": "unresolved.does-not-exist",
            },
        }
        register_path = self._write_gap_register(register)
        completed, result = self._run("--gap-register", str(register_path))
        self.assertEqual(completed.returncode, 1)
        self.assertTrue(
            any(
                error["code"] == "unresolved_gap_disposition_ref"
                for error in result["errors"]
            )
        )

    def test_gap_register_rejects_unresolved_that_does_not_affect_item(self) -> None:
        register = self._gap_register()
        source = self._source()
        gap = register["gaps"][0]
        item_id = gap["item_ref"]["entity_id"]
        unrelated = next(
            item
            for item in source["unresolved_items"]
            if item_id
            not in {
                reference["entity_id"]
                for reference in item["affected_entity_refs"]
            }
        )
        gap["disposition"] = {
            "kind": "canonical_unresolved",
            "unresolved_ref": {
                "reference_kind": "ref",
                "entity_id": unrelated["entity_id"],
            },
        }
        register_path = self._write_gap_register(register)
        completed, result = self._run("--gap-register", str(register_path))
        self.assertEqual(completed.returncode, 1)
        self.assertTrue(
            any(
                error["code"] == "gap_item_not_affected_by_unresolved"
                for error in result["errors"]
            )
        )

    def test_gap_register_rejects_gap_set_digest_tamper(self) -> None:
        register = self._gap_register()
        register["gap_set_digest"]["value"] = "0" * 64
        path = self._write_json_artifact(
            register, "verification-gap-register-digest-test-"
        )
        completed, result = self._run("--gap-register", str(path))
        self.assertEqual(completed.returncode, 1)
        self.assertTrue(
            any(
                error["code"] == "gap_set_digest_mismatch"
                for error in result["errors"]
            )
        )

    def test_gap_register_rejects_false_resolved_disposition(self) -> None:
        register = self._gap_register()
        gap = register["gaps"][0]
        gap["disposition"] = {
            "kind": "resolved",
            "evidence_refs": [
                {
                    "reference_kind": "ref",
                    "entity_id": "evidence.integrated-verification.2026-07-16",
                }
            ],
            "completion_rule": "The declared gap is closed by current bound evidence.",
            "completion_assessment": {
                "status": "satisfied",
                "assessed_gap_id": gap["gap_id"],
                "assessor_ref": "assessor.test",
                "assessed_at": "2026-07-16T12:00:00+09:00",
            },
        }
        register_path = self._write_gap_register(register)
        completed, result = self._run("--gap-register", str(register_path))
        codes = {error["code"] for error in result["errors"]}
        self.assertEqual(completed.returncode, 1)
        self.assertIn("resolved_gap_evidence_not_current_bound", codes)
        self.assertIn("resolved_gap_missing_item_support", codes)

    def test_gap_register_not_applicable_requires_human_record_and_reactivation(self) -> None:
        register = self._gap_register()
        register["gaps"][0]["disposition"] = {
            "kind": "not_applicable",
            "accepted_human_decision": {
                "decision_id": "decision.test",
                "status": "accepted",
                "locator": "verification-source.json",
                "content_digest": {"algorithm": "sha256", "value": "0" * 64},
                "decided_by": "human.test",
                "decided_at": "2026-07-16T12:00:00+09:00",
                "scope": "test",
            },
            "reactivation": {"triggers": [], "review_by": None},
        }
        register_path = self._write_gap_register(register)
        completed, result = self._run("--gap-register", str(register_path))
        self.assertEqual(completed.returncode, 1)
        self.assertTrue(
            any(
                error["code"] == "gap_register_schema_validation_failed"
                for error in result["errors"]
            )
        )

    def test_gap_register_handoff_must_preserve_audit_unresolved_ref(self) -> None:
        register = self._gap_register()
        register["gaps"][0]["disposition"] = {
            "kind": "control_plane_handoff",
            "handoff_id": "handoff.test",
        }
        register_path = self._write_gap_register(register)
        completed, result = self._run("--gap-register", str(register_path))
        self.assertEqual(completed.returncode, 1)
        self.assertTrue(
            any(
                error["code"] == "gap_register_schema_validation_failed"
                for error in result["errors"]
            )
        )

    def test_validator_digest_failure_keeps_a_schema_valid_error_envelope(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "verification_source_validator_digest_failure", SCRIPT
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        original_sha256 = module._sha256

        def fail_validator_digest(path: Path) -> str:
            if path == module.VALIDATOR_PATH:
                raise OSError("simulated validator digest failure")
            return original_sha256(path)

        output = io.StringIO()
        with (
            patch.object(module, "_sha256", side_effect=fail_validator_digest),
            patch.object(sys, "argv", [str(SCRIPT)]),
            redirect_stdout(output),
        ):
            returncode = module.main()

        result = json.loads(output.getvalue())
        schema = json.loads(RESULT_SCHEMA.read_text(encoding="utf-8"))
        Draft202012Validator(schema).validate(result)
        self.assertEqual(returncode, 1)
        self.assertEqual(result["status"], "error")
        self.assertIsNone(result["execution"]["validator_sha256"])
        self.assertEqual(result["checks"]["paths_and_digests"], "failed")
        self.assertTrue(
            any(error["code"] == "artifact_digest_failed" for error in result["errors"])
        )

    def test_schema_invalid_source_stays_in_error_envelope(self) -> None:
        source_path = self._write_source({})
        completed, result = self._run("--source", str(source_path))
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["checks"]["schema_validation"], "failed")
        self.assertEqual(result["checks"]["reference_closure"], "not_run")
        self.assertTrue(
            any(error["code"] == "schema_validation_failed" for error in result["errors"])
        )

    def test_wrong_collection_type_stays_in_error_envelope(self) -> None:
        source = self._source()
        source["state_profiles"] = 1
        source_path = self._write_source(source)
        completed, result = self._run("--source", str(source_path))
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["checks"]["schema_validation"], "failed")
        self.assertNotIn("state_profiles", result["counts"])

    def test_origin_and_subject_reference_typos_fail_closure(self) -> None:
        source = self._source()
        source["verification_items"][0]["origin_requirement_refs"][0][
            "entity_id"
        ] = "OR-999"
        source["implementation_conformance_items"][0]["subject_ref"][
            "entity_id"
        ] = "INV-VN-999"
        source_path = self._write_source(source)
        completed, result = self._run("--source", str(source_path))
        codes = {error["code"] for error in result["errors"]}
        self.assertEqual(completed.returncode, 1)
        self.assertIn("unresolved_origin_requirement_ref", codes)
        self.assertIn("unresolved_conformance_subject_ref", codes)

    def test_lifecycle_surface_assessments_require_exact_closed_coverage(self) -> None:
        source = self._source()
        item = source["verification_items"][0]
        item["lifecycle_surface_assessments"] = [
            item["lifecycle_surface_assessments"][0]
        ]
        item["lifecycle_surface_assessments"][0]["state_profile_ref"][
            "entity_id"
        ] = "state.typo"
        item["lifecycle_surface_assessments"][0]["evidence_refs"][0][
            "entity_id"
        ] = "evidence.typo"
        source_path = self._write_source(source)
        completed, result = self._run("--source", str(source_path))
        codes = {error["code"] for error in result["errors"]}
        self.assertEqual(completed.returncode, 1)
        self.assertIn("lifecycle_surface_assessment_coverage_mismatch", codes)
        self.assertIn("unresolved_state_profile_ref", codes)
        self.assertIn("unresolved_evidence_ref", codes)

    def test_lifecycle_surface_support_cannot_bleed_across_subclaims(self) -> None:
        source = self._source()
        item = source["verification_items"][0]
        for assessment in item["lifecycle_surface_assessments"]:
            assessment["state_profile_ref"] = {
                "reference_kind": "ref",
                "entity_id": "state.local-verified-not-validated",
                "label_hint": "local verified",
            }
            assessment["evidence_refs"] = [deepcopy(item["evidence_refs"][1])]
        source_path = self._write_source(source)
        completed, result = self._run("--source", str(source_path))
        self.assertEqual(completed.returncode, 1)
        missing_locations = {
            error["location"]
            for error in result["errors"]
            if error["code"] == "missing_lifecycle_assessment_support_dimension"
        }
        self.assertEqual(len(missing_locations), 9)

    def test_lifecycle_scoped_support_cannot_satisfy_parent_aggregate(self) -> None:
        source = self._source()
        item = source["verification_items"][0]
        item["state_profile_ref"] = {
            "reference_kind": "ref",
            "entity_id": "state.local-verified-not-validated",
            "label_hint": "local verified",
        }
        source_path = self._write_source(source)
        completed, result = self._run("--source", str(source_path))
        self.assertEqual(completed.returncode, 1)
        errors = [
            error
            for error in result["errors"]
            if error["code"] == "missing_supporting_evidence_effect_dimension"
            and error["location"]
            == "verification.or01.lifecycle-surface-coverage.evidence_refs"
        ]
        self.assertEqual(len(errors), 1)
        self.assertIn("implementation", errors[0]["message"])
        self.assertIn("verification", errors[0]["message"])
        self.assertIn("assurance", errors[0]["message"])

    def test_unbound_extra_subject_cannot_be_called_bound(self) -> None:
        source = self._source()
        binding = source["evidence_observations"][0]["subject_binding"]
        binding["subject_locators"].append("../constitution/semantic-guard-constitution.yaml")
        source_path = self._write_source(source)
        completed, result = self._run("--source", str(source_path))
        self.assertEqual(completed.returncode, 1)
        self.assertTrue(
            any(
                error["code"] == "incomplete_subject_digest_coverage"
                for error in result["errors"]
            )
        )

    def test_digest_mismatch_fails(self) -> None:
        source = self._source()
        source["evidence_observations"][0]["content_digest"]["value"] = "0" * 64
        source_path = self._write_source(source)
        completed, result = self._run("--source", str(source_path))
        self.assertEqual(completed.returncode, 1)
        self.assertTrue(
            any(error["code"] == "evidence_digest_mismatch" for error in result["errors"])
        )

    def test_unsupported_digest_algorithm_fails_closed(self) -> None:
        source = self._source()
        source["evidence_observations"][0]["content_digest"] = {
            "algorithm": "other",
            "value": "opaque-digest",
        }
        source_path = self._write_source(source)
        completed, result = self._run("--source", str(source_path))
        self.assertEqual(completed.returncode, 1)
        self.assertTrue(
            any(
                error["code"] == "unsupported_digest_algorithm"
                for error in result["errors"]
            )
        )

    def test_upstream_source_requires_sha256_binding(self) -> None:
        source = self._source()
        source["upstream_sources"][0]["version_or_digest"] = "version-only"
        source_path = self._write_source(source)
        completed, result = self._run("--source", str(source_path))
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(result["checks"]["schema_validation"], "failed")

    def test_shared_upstream_and_evidence_identity_requires_same_content(self) -> None:
        source = self._source()
        old_id = "evidence.real-nlp-smoke.2026-07-16"
        shared_id = "document.prototype-origin-requirement.v3"

        def replace_identity(value: object) -> object:
            if isinstance(value, dict):
                return {key: replace_identity(item) for key, item in value.items()}
            if isinstance(value, list):
                return [replace_identity(item) for item in value]
            return shared_id if value == old_id else value

        source = replace_identity(source)
        self.assertIsInstance(source, dict)
        source_path = self._write_source(source)
        completed, result = self._run("--source", str(source_path))
        codes = {error["code"] for error in result["errors"]}
        self.assertEqual(completed.returncode, 1)
        self.assertIn("shared_identity_path_mismatch", codes)
        self.assertIn("shared_identity_digest_mismatch", codes)

    def test_signed_trust_class_requires_elevated_trust_basis(self) -> None:
        source = self._source()
        source["evidence_observations"][0]["trust_class"] = "signed"
        source_path = self._write_source(source)
        completed, result = self._run("--source", str(source_path))
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(result["checks"]["schema_validation"], "failed")

    def test_independent_trust_requires_observer_and_located_basis(self) -> None:
        source = self._source()
        evidence = source["evidence_observations"][0]
        evidence["trust_class"] = "independently_observed"
        source_path = self._write_source(source)
        completed, result = self._run("--source", str(source_path))
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(result["checks"]["schema_validation"], "failed")

        evidence["elevated_trust_basis"]["observer_ref"] = "observer.example"
        evidence["elevated_trust_basis"]["independence_basis_ref"] = "missing.json"
        source_path = self._write_source(source)
        completed, result = self._run("--source", str(source_path))
        self.assertEqual(completed.returncode, 1)
        self.assertTrue(any(error["code"] == "path_missing" for error in result["errors"]))

    def test_bound_test_execution_requires_environment_and_log(self) -> None:
        source = self._source()
        evidence = source["evidence_observations"][0]
        evidence["evidence_kind"] = "test_execution"
        source_path = self._write_source(source)
        completed, result = self._run("--source", str(source_path))
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(result["checks"]["schema_validation"], "failed")

    def test_bound_test_execution_requires_digest_bound_manifest(self) -> None:
        source = self._source()
        evidence = next(
            evidence
            for evidence in source["evidence_observations"]
            if evidence["entity_id"]
            == "evidence.integrated-verification.2026-07-16"
        )
        evidence["subject_binding"].update(
            {
                "status": "bound",
                "subject_locators": ["integrated-verification-2026-07-16.json"],
                "digest_bindings": [
                    {
                        "subject_locator": "integrated-verification-2026-07-16.json",
                        "digest": deepcopy(evidence["content_digest"]),
                    }
                ],
            }
        )
        evidence["freshness"] = "current"
        source_path = self._write_source(source)
        completed, result = self._run("--source", str(source_path))
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(result["checks"]["schema_validation"], "failed")

    def test_bound_test_execution_rejects_self_selected_report_denominator(self) -> None:
        source = self._source()
        evidence = next(
            evidence
            for evidence in source["evidence_observations"]
            if evidence["entity_id"]
            == "evidence.integrated-verification.2026-07-16"
        )
        binding = {
            "subject_locator": "integrated-verification-2026-07-16.json",
            "digest": deepcopy(evidence["content_digest"]),
        }
        manifest = {
            "schema_version": "semantic-guard-evidence-subject-manifest/v0",
            "closed_world": True,
            "subjects": [binding],
            "limitations": ["Test-only manifest containing only the evidence report."],
        }
        manifest_path = self._write_json_artifact(
            manifest, "verification-subject-manifest-test-"
        )
        evidence["subject_binding"].update(
            {
                "status": "bound",
                "subject_locators": [binding["subject_locator"]],
                "digest_bindings": [binding],
                "manifest_ref": manifest_path.name,
                "manifest_digest": {
                    "algorithm": "sha256",
                    "value": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
                },
            }
        )
        evidence["freshness"] = "current"
        source_path = self._write_source(source)
        completed, result = self._run("--source", str(source_path))
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(result["checks"]["schema_validation"], "passed")
        self.assertTrue(
            any(
                error["code"]
                == "test_execution_subject_is_only_evidence_record"
                for error in result["errors"]
            )
        )

    def test_bound_test_execution_accepts_digest_bound_closed_manifest(self) -> None:
        source = self._source()
        evidence = next(
            evidence
            for evidence in source["evidence_observations"]
            if evidence["entity_id"]
            == "evidence.integrated-verification.2026-07-16"
        )
        subject_path = ROOT / "src/semantic_guard/engine.py"
        binding = {
            "subject_locator": "../src/semantic_guard/engine.py",
            "digest": {
                "algorithm": "sha256",
                "value": hashlib.sha256(subject_path.read_bytes()).hexdigest(),
            },
        }
        manifest = {
            "schema_version": "semantic-guard-evidence-subject-manifest/v0",
            "closed_world": True,
            "subjects": [binding],
            "limitations": ["Test-only single-file subject denominator."],
        }
        manifest_path = self._write_json_artifact(
            manifest, "verification-subject-manifest-valid-test-"
        )
        evidence["subject_binding"].update(
            {
                "status": "bound",
                "subject_locators": [binding["subject_locator"]],
                "digest_bindings": [binding],
                "manifest_ref": manifest_path.name,
                "manifest_digest": {
                    "algorithm": "sha256",
                    "value": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
                },
            }
        )
        source_path = self._write_source(source)
        completed, result = self._run("--source", str(source_path))
        manifest_errors = [
            error
            for error in result["errors"]
            if "manifest" in error["code"]
            or error["code"] == "test_execution_subject_is_only_evidence_record"
        ]
        self.assertEqual(completed.returncode, 1)  # Temporary source mismatches projection.
        self.assertEqual(result["checks"]["schema_validation"], "passed")
        self.assertEqual(manifest_errors, [])

    def test_unbound_state_cannot_be_terminal_or_complete(self) -> None:
        source = self._source()
        assurance = source["state_profiles"][0]["state"]["assurance"]
        assurance.update(
            {
                "finality": "terminal",
                "challenge": "none",
                "coverage": "complete",
            }
        )
        source_path = self._write_source(source)
        completed, result = self._run("--source", str(source_path))
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(result["checks"]["schema_validation"], "failed")

    def test_current_state_requires_current_bound_referenced_evidence(self) -> None:
        source = self._source()
        source["state_profiles"][1]["state"]["freshness"] = "current"
        source_path = self._write_source(source)
        completed, result = self._run("--source", str(source_path))
        self.assertEqual(completed.returncode, 1)
        self.assertTrue(
            any(
                error["code"] == "current_state_uses_noncurrent_evidence"
                for error in result["errors"]
            )
        )

    def test_challenged_state_requires_counterevidence(self) -> None:
        source = self._source()
        source["verification_items"][0]["counterevidence_refs"] = []
        source_path = self._write_source(source)
        completed, result = self._run("--source", str(source_path))
        self.assertEqual(completed.returncode, 1)
        self.assertTrue(
            any(
                error["code"] == "counterevidence_effect_mismatch"
                for error in result["errors"]
            )
        )

    def test_support_reference_cannot_impersonate_typed_counterevidence(self) -> None:
        source = self._source()
        item = source["verification_items"][0]
        item["counterevidence_refs"] = [item["evidence_refs"][0]]
        source_path = self._write_source(source)
        completed, result = self._run("--source", str(source_path))
        self.assertEqual(completed.returncode, 1)
        self.assertTrue(
            any(
                error["code"] == "counterevidence_effect_mismatch"
                for error in result["errors"]
            )
        )

    def test_typed_challenge_effect_cannot_be_hidden_by_satisfied_state(self) -> None:
        source = self._source()
        assurance = source["state_profiles"][0]["state"]["assurance"]
        assurance["outcome"] = "satisfied"
        assurance["challenge"] = "none"
        source_path = self._write_source(source)
        completed, result = self._run("--source", str(source_path))
        self.assertEqual(completed.returncode, 1)
        self.assertTrue(
            any(
                error["code"] == "challenge_effect_state_conflict"
                for error in result["errors"]
            )
        )

    def test_negative_effect_requires_assurance_claim_dimension(self) -> None:
        source = self._source()
        effect = next(
            effect
            for effect in source["evidence_effects"]
            if effect["effect"] == "challenges"
        )
        effect["claim_dimensions"] = ["verification"]
        source_path = self._write_source(source)
        completed, result = self._run("--source", str(source_path))
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(result["checks"]["schema_validation"], "failed")

    def test_negative_state_axis_cannot_coexist_with_satisfied_assurance(self) -> None:
        source = self._source()
        profile = next(
            profile
            for profile in source["state_profiles"]
            if profile["entity_id"] == "state.local-verified-not-validated"
        )
        profile["state"]["verification"] = "failed"
        profile["state"]["assurance"].update(
            {"outcome": "satisfied", "challenge": "none"}
        )
        source_path = self._write_source(source)
        completed, result = self._run("--source", str(source_path))
        self.assertEqual(completed.returncode, 1)
        self.assertTrue(
            any(
                error["code"] == "state_axis_assurance_conflict"
                for error in result["errors"]
            )
        )

    def test_negative_state_requires_negative_effect_and_rejects_hidden_support(self) -> None:
        source = self._source()
        item = source["implementation_conformance_items"][0]
        item["state_profile_ref"] = {
            "reference_kind": "ref",
            "entity_id": "state.missing-not-evaluated",
            "label_hint": "missing",
        }
        source_path = self._write_source(source)
        completed, result = self._run("--source", str(source_path))
        codes = {error["code"] for error in result["errors"]}
        self.assertEqual(completed.returncode, 1)
        self.assertIn("negative_state_missing_evidence_effect_dimension", codes)
        self.assertIn("state_axis_evidence_polarity_conflict", codes)

    def test_negative_lifecycle_subclaim_requires_scoped_negative_effect(self) -> None:
        source = self._source()
        assessment = source["verification_items"][0][
            "lifecycle_surface_assessments"
        ][0]
        assessment["state_profile_ref"] = {
            "reference_kind": "ref",
            "entity_id": "state.missing-not-evaluated",
            "label_hint": "missing",
        }
        source_path = self._write_source(source)
        completed, result = self._run("--source", str(source_path))
        self.assertEqual(completed.returncode, 1)
        self.assertTrue(
            any(
                error["code"]
                == "missing_lifecycle_assessment_negative_dimension"
                for error in result["errors"]
            )
        )

    def test_closed_refutation_may_be_terminal_without_open_challenge(self) -> None:
        source = self._source()
        integrated = next(
            evidence
            for evidence in source["evidence_observations"]
            if evidence["entity_id"]
            == "evidence.integrated-verification.2026-07-16"
        )
        integrated["subject_binding"].update(
            {
                "status": "bound",
                "subject_locators": ["integrated-verification-2026-07-16.json"],
                "digest_bindings": [
                    {
                        "subject_locator": "integrated-verification-2026-07-16.json",
                        "digest": deepcopy(integrated["content_digest"]),
                    }
                ],
            }
        )
        integrated["evidence_kind"] = "tool_output"
        integrated["freshness"] = "current"
        profile = deepcopy(source["state_profiles"][0])
        profile["entity_id"] = "state.test-terminal-refuted"
        profile["label"] = "test terminal refutation"
        profile["state"]["freshness"] = "current"
        profile["state"]["assurance"].update(
            {"finality": "terminal", "challenge": "none", "coverage": "complete"}
        )
        source["state_profiles"].append(profile)
        source["verification_items"][0]["state_profile_ref"] = {
            "reference_kind": "ref",
            "entity_id": profile["entity_id"],
            "label_hint": profile["label"],
        }
        source_path = self._write_source(source)
        completed, result = self._run("--source", str(source_path))
        codes = {error["code"] for error in result["errors"]}
        self.assertEqual(completed.returncode, 1)  # Temporary source mismatches projection.
        self.assertEqual(result["checks"]["schema_validation"], "passed")
        self.assertNotIn("challenge_effect_state_conflict", codes)
        self.assertNotIn("claim_effect_state_conflict", codes)

    def test_contextual_effect_cannot_support_positive_state_dimensions(self) -> None:
        source = self._source()
        effect = next(
            effect
            for effect in source["evidence_effects"]
            if effect["effect_id"]
            == "effect.human-boundary.integrated-acceptance.supports"
        )
        effect["effect"] = "contextualizes"
        effect["claim_dimensions"] = ["proposition"]
        source_path = self._write_source(source)
        completed, result = self._run("--source", str(source_path))
        self.assertEqual(completed.returncode, 1)
        self.assertTrue(
            any(
                error["code"] == "missing_supporting_evidence_effect_dimension"
                for error in result["errors"]
            )
        )

    def test_evidence_effect_locator_requires_exact_declared_observation(self) -> None:
        source = self._source()
        effect = next(
            effect
            for effect in source["evidence_effects"]
            if effect["effect_id"]
            == "effect.bounded-claim.public-trust-basis.challenges"
        )
        effect["observation_locator"] = (
            "../schemas/common.schema.json#/$defs/digest"
        )
        source_path = self._write_source(source)
        completed, result = self._run("--source", str(source_path))
        self.assertEqual(completed.returncode, 1)
        self.assertTrue(
            any(
                error["code"] == "evidence_effect_locator_outside_observation"
                for error in result["errors"]
            )
        )

    def test_blocking_unresolved_item_constrains_view_members(self) -> None:
        source = self._source()
        unresolved = source["unresolved_items"][-1]
        unresolved["claim_effect"] = "blocks_claim"
        source_path = self._write_source(source)
        completed, result = self._run("--source", str(source_path))
        self.assertEqual(completed.returncode, 1)
        self.assertTrue(
            any(error["code"] == "claim_effect_state_conflict" for error in result["errors"])
        )

    def test_not_defined_method_is_exclusive_and_has_no_procedure(self) -> None:
        source = self._source()
        method = source["verification_items"][0]["validation_method"]
        method["method_types"] = ["not_defined", "test"]
        method["procedure_refs"] = ["README.md"]
        source_path = self._write_source(source)
        completed, result = self._run("--source", str(source_path))
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(result["checks"]["schema_validation"], "failed")

    def test_human_resolution_obligation_requires_decision_question(self) -> None:
        source = self._source()
        obligation = next(
            obligation
            for unresolved in source["unresolved_items"]
            for obligation in unresolved["resolution_obligations"]
            if obligation["authority_class"] == "human_required"
        )
        obligation["decision_question"] = None
        source_path = self._write_source(source)
        completed, result = self._run("--source", str(source_path))
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(result["checks"]["schema_validation"], "failed")

    def test_obligation_preconditions_require_closed_acyclic_refs(self) -> None:
        source = self._source()
        obligations = source["unresolved_items"][0]["resolution_obligations"]
        obligations[0]["precondition_obligation_refs"] = [
            {
                "reference_kind": "ref",
                "entity_id": obligations[1]["obligation_id"],
                "label_hint": "cycle-a",
            }
        ]
        obligations[1]["precondition_obligation_refs"] = [
            {
                "reference_kind": "ref",
                "entity_id": obligations[0]["obligation_id"],
                "label_hint": "cycle-b",
            },
            {
                "reference_kind": "ref",
                "entity_id": "obligation.missing",
                "label_hint": "missing",
            },
        ]
        source_path = self._write_source(source)
        completed, result = self._run("--source", str(source_path))
        codes = {error["code"] for error in result["errors"]}
        self.assertEqual(completed.returncode, 1)
        self.assertIn("cyclic_obligation_preconditions", codes)
        self.assertIn("unresolved_obligation_precondition_ref", codes)

    def test_resolution_paths_require_local_closed_obligation_coverage(self) -> None:
        source = self._source()
        unresolved = source["unresolved_items"][0]
        path = unresolved["resolution_paths"][0]
        path["required_obligation_refs"] = [path["required_obligation_refs"][2]]
        path["required_obligation_refs"].append(
            {
                "reference_kind": "ref",
                "entity_id": "obligation.projection.generate-or-compare",
                "label_hint": "other unresolved obligation",
            }
        )
        source_path = self._write_source(source)
        completed, result = self._run("--source", str(source_path))
        codes = {error["code"] for error in result["errors"]}
        self.assertEqual(completed.returncode, 1)
        self.assertIn("unresolved_resolution_path_obligation_ref", codes)
        self.assertIn("resolution_path_missing_local_precondition", codes)
        self.assertIn("resolution_path_missing_obligation_coverage", codes)

    def test_local_definition_ids_share_one_namespace(self) -> None:
        source = self._source()
        source["unresolved_items"][0]["resolution_paths"][0]["path_id"] = (
            source["evidence_effects"][0]["effect_id"]
        )
        source_path = self._write_source(source)
        completed, result = self._run("--source", str(source_path))
        self.assertEqual(completed.returncode, 1)
        self.assertTrue(
            any(error["code"] == "duplicate_entity_id" for error in result["errors"])
        )

        source = self._source()
        source["upstream_sources"][0]["ref"]["entity_id"] = (
            source["verification_items"][0]["entity_id"]
        )
        source_path = self._write_source(source)
        completed, result = self._run("--source", str(source_path))
        self.assertEqual(completed.returncode, 1)
        self.assertTrue(
            any(
                error["code"]
                == "upstream_identity_collides_with_local_definition"
                for error in result["errors"]
            )
        )

    def test_temporal_order_and_expiry_are_checked(self) -> None:
        source = self._source()
        source["evidence_observations"][0]["observed_at"] = "2099-01-01T00:00:00Z"
        reverification = source["verification_items"][0]["reverification"]
        reverification["status"] = "defined"
        reverification["last_evaluated_at"] = "2026-07-16T08:00:00+09:00"
        reverification["valid_until"] = "2026-07-16T08:10:00+09:00"
        source_path = self._write_source(source)
        completed, result = self._run("--source", str(source_path))
        codes = {error["code"] for error in result["errors"]}
        self.assertEqual(completed.returncode, 1)
        self.assertIn("observation_after_register_time", codes)
        self.assertIn("expired_reverification_not_marked_due", codes)
        self.assertEqual(result["checks"]["temporal_consistency"], "failed")

    def test_evaluation_validity_and_human_decision_cannot_postdate_register(self) -> None:
        source = self._source()
        reverification = source["verification_items"][0]["reverification"]
        reverification["status"] = "defined"
        reverification["last_evaluated_at"] = "2099-01-02T00:00:00Z"
        reverification["valid_until"] = "2099-01-01T00:00:00Z"
        source["human_acceptance"].update(
            {
                "status": "accept",
                "decision_record_ref": "../README.md",
                "decided_at": "2099-01-03T00:00:00Z",
            }
        )
        source_path = self._write_source(source)
        completed, result = self._run("--source", str(source_path))
        codes = {error["code"] for error in result["errors"]}
        self.assertEqual(completed.returncode, 1)
        self.assertIn("evaluation_after_register_time", codes)
        self.assertIn("validity_precedes_evaluation", codes)
        self.assertIn("human_decision_after_register_time", codes)
        self.assertEqual(result["checks"]["temporal_consistency"], "failed")

    def test_evaluation_cannot_precede_referenced_evidence(self) -> None:
        source = self._source()
        item = next(
            item
            for item in source["verification_items"]
            if item["entity_id"] == "verification.or02.bounded-claim-model"
        )
        item["reverification"]["last_evaluated_at"] = (
            "2026-07-16T09:00:00+09:00"
        )
        source_path = self._write_source(source)
        completed, result = self._run("--source", str(source_path))
        self.assertEqual(completed.returncode, 1)
        self.assertTrue(
            any(
                error["code"] == "evaluation_precedes_referenced_evidence"
                for error in result["errors"]
            )
        )

    def test_validity_and_evaluated_validation_require_evaluation_time(self) -> None:
        source = self._source()
        item = next(
            item
            for item in source["verification_items"]
            if item["entity_id"] == "verification.or03.repair-effect"
        )
        state = next(
            profile
            for profile in source["state_profiles"]
            if profile["entity_id"] == item["state_profile_ref"]["entity_id"]
        )
        state["state"]["validation"] = "inconclusive"
        item["reverification"]["valid_until"] = "2026-07-17T00:00:00+09:00"
        source_path = self._write_source(source)
        completed, result = self._run("--source", str(source_path))
        codes = {error["code"] for error in result["errors"]}
        self.assertEqual(completed.returncode, 1)
        self.assertIn("evaluated_state_missing_evaluation_time", codes)
        self.assertIn("validity_without_evaluation_time", codes)

    def test_due_reverification_and_conformance_without_contract_cannot_be_current(self) -> None:
        source = self._source()
        profile = next(
            profile
            for profile in source["state_profiles"]
            if profile["entity_id"] == "state.boundary-verified"
        )
        profile["state"]["freshness"] = "current"
        item = next(
            item
            for item in source["verification_items"]
            if item["entity_id"] == "verification.or03.human-decision-boundary"
        )
        item["reverification"]["status"] = "due"
        source_path = self._write_source(source)
        completed, result = self._run("--source", str(source_path))
        codes = {error["code"] for error in result["errors"]}
        self.assertEqual(completed.returncode, 1)
        self.assertIn("reverification_status_conflicts_with_current_state", codes)
        self.assertIn("conformance_current_without_reverification_contract", codes)

    def test_rfc3339_case_variants_never_escape_json_envelope(self) -> None:
        source = self._source()
        source["recorded_at"] = source["recorded_at"].replace("+09:00", "z")
        source_path = self._write_source(source)
        completed, result = self._run("--source", str(source_path))
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(result["checks"]["schema_validation"], "passed")
        self.assertEqual(result["checks"]["temporal_consistency"], "passed")
        self.assertFalse(
            any(error["code"] == "timestamp_parse_failed" for error in result["errors"])
        )

        source["recorded_at"] = "2026-07-16T24:00:00Z"
        source_path = self._write_source(source)
        completed, result = self._run("--source", str(source_path))
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(result["status"], "error")

    def test_evidence_refs_cannot_be_empty(self) -> None:
        source = self._source()
        source["verification_items"][0]["evidence_refs"] = []
        source_path = self._write_source(source)
        completed, result = self._run("--source", str(source_path))
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(result["checks"]["schema_validation"], "failed")

    def test_wrong_schema_identity_is_rejected(self) -> None:
        completed, result = self._run(
            "--schema", "schemas/common.schema.json"
        )
        self.assertEqual(completed.returncode, 1)
        self.assertTrue(
            any(error["code"] == "schema_identity_mismatch" for error in result["errors"])
        )

    def test_repository_escape_is_rejected_without_reading_target(self) -> None:
        completed, result = self._run("--source", "/etc/passwd")
        self.assertEqual(completed.returncode, 1)
        self.assertIsNone(result["subject"]["source_sha256"])
        self.assertTrue(
            any(error["code"] == "path_outside_repository" for error in result["errors"])
        )

    def test_invalid_path_stays_in_error_envelope(self) -> None:
        source = self._source()
        source["record_surface"]["detail_refs"].append("\u0000")
        source_path = self._write_source(source)
        completed, result = self._run("--source", str(source_path))
        self.assertEqual(completed.returncode, 1)
        self.assertTrue(
            any(error["code"] == "invalid_path" for error in result["errors"])
        )

    def test_missing_evidence_detail_reference_fails(self) -> None:
        source = self._source()
        source["evidence_observations"][0]["detail_refs"] = ["missing-evidence.txt"]
        source_path = self._write_source(source)
        completed, result = self._run("--source", str(source_path))
        self.assertEqual(completed.returncode, 1)
        self.assertTrue(any(error["code"] == "path_missing" for error in result["errors"]))

    def test_missing_json_pointer_locator_fails(self) -> None:
        source = self._source()
        source["evidence_observations"][2]["subject_binding"][
            "environment_ref"
        ] = "integrated-verification-2026-07-16.json#/missing"
        source_path = self._write_source(source)
        completed, result = self._run("--source", str(source_path))
        self.assertEqual(completed.returncode, 1)
        self.assertTrue(
            any(error["code"] == "json_pointer_not_found" for error in result["errors"])
        )

    def test_nonpending_human_acceptance_requires_decision_record(self) -> None:
        source = deepcopy(self._source())
        source["human_acceptance"]["status"] = "accept"
        source_path = self._write_source(source)
        completed, result = self._run("--source", str(source_path))
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(result["checks"]["schema_validation"], "failed")

    def test_human_decision_record_must_exist_inside_repository(self) -> None:
        source = self._source()
        source["human_acceptance"].update(
            {
                "status": "accept",
                "decision_record_ref": "missing-human-decision.json",
                "decided_at": source["recorded_at"],
            }
        )
        source_path = self._write_source(source)
        completed, result = self._run("--source", str(source_path))
        self.assertEqual(completed.returncode, 1)
        self.assertTrue(any(error["code"] == "path_missing" for error in result["errors"]))


if __name__ == "__main__":
    unittest.main()
