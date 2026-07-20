from __future__ import annotations

import json
from pathlib import Path
import unittest

from semantic_guard.engine import audit_requirement_relations


class ConformanceCorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        path = (
            Path(__file__).resolve().parents[1]
            / "fixtures"
            / "requirement-relations"
            / "conformance.jsonl"
        )
        cls.cases = [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def test_cases_have_unique_identity_and_declared_basis(self) -> None:
        case_ids = [item["case_id"] for item in self.cases]

        self.assertEqual(len(case_ids), len(set(case_ids)))
        self.assertGreaterEqual(len(case_ids), 7)
        self.assertTrue(all(item.get("basis_kind") for item in self.cases))

    def test_all_conformance_expectations(self) -> None:
        failures: list[str] = []
        for case in self.cases:
            with self.subTest(case_id=case["case_id"]):
                report = audit_requirement_relations(
                    case["text"], analysis_mode="conditional"
                )
                expected = case["expected"]
                signal_codes = {item.reason_code for item in report.residual_signals}
                if expected.get("workflow") != report.result.workflow.value and "workflow" in expected:
                    failures.append(
                        f"{case['case_id']}: workflow={report.result.workflow.value}, expected={expected['workflow']}"
                    )
                if expected.get("workflow_not") == report.result.workflow.value:
                    failures.append(
                        f"{case['case_id']}: forbidden workflow={report.result.workflow.value}"
                    )
                if expected.get("outcome") != report.result.outcome.value and "outcome" in expected:
                    failures.append(
                        f"{case['case_id']}: outcome={report.result.outcome.value}, expected={expected['outcome']}"
                    )
                if expected.get("record_mode") != report.record.record_mode:
                    failures.append(
                        f"{case['case_id']}: record_mode={report.record.record_mode}, expected={expected.get('record_mode')}"
                    )
                missing = set(expected.get("required_signal_codes", [])) - signal_codes
                if missing:
                    failures.append(
                        f"{case['case_id']}: missing signals={sorted(missing)}"
                    )

        self.assertEqual(failures, [], "\n".join(failures))

    def test_scope_defeaters_never_strengthen_the_base_case(self) -> None:
        base = next(item for item in self.cases if item["case_id"] == "affirmative.closed.aligned")
        base_report = audit_requirement_relations(
            base["text"], analysis_mode="conditional"
        )
        self.assertTrue(base_report.result.is_pass)

        for case in self.cases:
            if not case["case_id"].startswith("defeater."):
                continue
            with self.subTest(case_id=case["case_id"]):
                report = audit_requirement_relations(
                    case["text"], analysis_mode="conditional"
                )
                self.assertFalse(report.result.is_pass)
                self.assertNotEqual(report.result.finality.value, "terminal")


if __name__ == "__main__":
    unittest.main()
