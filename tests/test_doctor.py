from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from semantic_guard.doctor import run_doctor
from semantic_guard.models import load_audit_result_schema


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


if __name__ == "__main__":
    unittest.main()
