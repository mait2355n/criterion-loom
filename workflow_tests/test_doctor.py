from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from semantic_guard_workflow.doctor import run_doctor
from semantic_guard_workflow.models import load_audit_result_schema


class DoctorTests(unittest.TestCase):
    def test_audit_result_schema_loads(self) -> None:
        schema = load_audit_result_schema()

        self.assertEqual(schema["properties"]["status"]["enum"], ["pass", "warn", "block"])
        self.assertIn("details", schema["required"])

    def test_doctor_blocks_missing_project_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = run_doctor(Path(directory), run_fixtures=False)

        self.assertEqual(result["status"], "block")
        self.assertTrue(any(check["name"] == "project_files" and check["status"] == "block" for check in result["checks"]))

    def test_doctor_passes_or_warns_for_checkout_without_fixtures(self) -> None:
        result = run_doctor(".", run_fixtures=False)

        self.assertIn(result["status"], {"pass", "warn"})
        self.assertTrue(any(check["name"] == "rule_detector_mapping" for check in result["checks"]))
        self.assertTrue(any(check["name"] == "conventions" for check in result["checks"]))

    def test_doctor_blocks_unimportable_detector_module(self) -> None:
        mappings = [
            {
                "rule_id": "test.detector.unimportable",
                "source_module": "semantic_guard_workflow.module_that_does_not_exist",
                "source_functions": ["detect"],
            }
        ]
        with (
            patch("semantic_guard_workflow.doctor.unmapped_rule_ids", return_value=[]),
            patch("semantic_guard_workflow.doctor.rule_detector_mappings", return_value=mappings),
        ):
            result = run_doctor(".", run_fixtures=False)

        mapping_check = next(check for check in result["checks"] if check["name"] == "rule_detector_mapping")
        self.assertEqual(result["status"], "block")
        self.assertEqual(mapping_check["status"], "block")
        self.assertEqual(mapping_check["details"]["import_errors"][0]["rule_id"], "test.detector.unimportable")

    def test_doctor_blocks_missing_detector_symbol(self) -> None:
        mappings = [
            {
                "rule_id": "test.detector.missing_symbol",
                "source_module": "semantic_guard_workflow.doctor",
                "source_functions": ["detector_that_does_not_exist"],
            }
        ]
        with (
            patch("semantic_guard_workflow.doctor.unmapped_rule_ids", return_value=[]),
            patch("semantic_guard_workflow.doctor.rule_detector_mappings", return_value=mappings),
        ):
            result = run_doctor(".", run_fixtures=False)

        mapping_check = next(check for check in result["checks"] if check["name"] == "rule_detector_mapping")
        self.assertEqual(result["status"], "block")
        self.assertEqual(mapping_check["status"], "block")
        self.assertEqual(
            mapping_check["details"]["missing_symbols"],
            [
                {
                    "rule_id": "test.detector.missing_symbol",
                    "source_module": "semantic_guard_workflow.doctor",
                    "source_function": "detector_that_does_not_exist",
                }
            ],
        )

    def test_doctor_blocks_detector_symbol_reexported_from_another_module(self) -> None:
        mappings = [
            {
                "rule_id": "test.detector.reexported",
                "source_module": "semantic_guard_workflow.doctor",
                "source_functions": ["load_conventions_catalog"],
            }
        ]
        with (
            patch("semantic_guard_workflow.doctor.unmapped_rule_ids", return_value=[]),
            patch("semantic_guard_workflow.doctor.rule_detector_mappings", return_value=mappings),
        ):
            result = run_doctor(".", run_fixtures=False)

        mapping_check = next(check for check in result["checks"] if check["name"] == "rule_detector_mapping")
        self.assertEqual(result["status"], "block")
        self.assertEqual(mapping_check["status"], "block")
        self.assertEqual(
            mapping_check["details"]["misplaced_symbols"],
            [
                {
                    "rule_id": "test.detector.reexported",
                    "source_module": "semantic_guard_workflow.doctor",
                    "source_function": "load_conventions_catalog",
                    "defining_module": "semantic_guard_workflow.conventions",
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
