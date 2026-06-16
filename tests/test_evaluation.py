from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from semantic_guard.evaluation import evaluate_fixture_tree

FIXTURE_ROOT = Path(__file__).parent / "fixtures"


class FixtureEvaluationTests(unittest.TestCase):
    def test_current_fixture_tree_passes(self) -> None:
        result = evaluate_fixture_tree(FIXTURE_ROOT, include_passed=True)
        self.assertGreater(result["total"], 0)
        self.assertEqual(result["failed"], 0)
        self.assertEqual(result["passed"], result["total"])
        self.assertTrue(result["results"])
        label_metrics = result["metrics"]["label_metrics"]
        self.assertGreater(label_metrics["expected_finding_total"], 0)
        self.assertGreater(label_metrics["forbidden_finding_total"], 0)
        self.assertEqual(label_metrics["false_negative"], 0)
        self.assertEqual(label_metrics["false_positive"], 0)
        self.assertGreater(label_metrics["expected_rule_total"], 0)
        self.assertEqual(label_metrics["expected_rule_missed"], 0)
        self.assertIn("req.interface.contract_missing", result["metrics"]["rule_hits"])
        coverage = result["rule_catalog_coverage"]
        self.assertTrue(coverage["local_calibration_only"])
        self.assertGreater(coverage["catalog_rule_count"], 0)
        self.assertIn("req.interface.contract_missing", coverage["fixture_labeled_rule_ids"])
        self.assertIn("finish.evidence.tests_missing", coverage["fixture_labeled_rule_ids"])
        self.assertEqual(coverage["unhit_rule_count"], 0)
        self.assertEqual(coverage["unemitted_rule_count"], 0)

    def test_fixture_evaluation_reports_expectation_failures(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            expected_path = root / "bad.expected.json"
            expected_path.write_text(
                json.dumps(
                    {
                        "id": "BAD-001",
                        "title": "intentional status mismatch",
                        "phase": "audit_request",
                        "kind": "requirement",
                        "text": "画面をいい感じにする",
                        "strict": True,
                        "expect": {"status": "pass"},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            result = evaluate_fixture_tree(root, include_passed=True)

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["failed"], 1)
        issue_checks = {issue["check"] for issue in result["results"][0]["issues"]}
        self.assertIn("status", issue_checks)

    def test_fixture_evaluation_counts_label_true_positive_and_true_negative(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            expected_path = root / "labels.expected.json"
            expected_path.write_text(
                json.dumps(
                    {
                        "id": "LABELS-001",
                        "title": "label metrics",
                        "phase": "audit_request",
                        "kind": "requirement",
                        "text": "画面をいい感じにする",
                        "strict": True,
                        "labels": {
                            "expected_findings": [{"category": "clarity"}],
                            "forbidden_findings": [{"category": "interface"}],
                        },
                        "expect": {"status": "block"},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            result = evaluate_fixture_tree(root, include_passed=True)

        label_metrics = result["metrics"]["label_metrics"]
        self.assertEqual(result["failed"], 0)
        self.assertEqual(label_metrics["true_positive"], 1)
        self.assertEqual(label_metrics["true_negative"], 1)
        self.assertEqual(label_metrics["expected_finding_recall"], 1.0)
        self.assertEqual(label_metrics["forbidden_finding_clean_rate"], 1.0)

    def test_fixture_evaluation_counts_label_false_positive_and_false_negative(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            expected_path = root / "bad-labels.expected.json"
            expected_path.write_text(
                json.dumps(
                    {
                        "id": "BAD-LABELS-001",
                        "title": "bad label metrics",
                        "phase": "audit_request",
                        "kind": "requirement",
                        "text": "画面をいい感じにする",
                        "strict": True,
                        "labels": {
                            "expected_findings": [{"category": "interface"}],
                            "forbidden_findings": [{"category": "clarity"}],
                        },
                        "expect": {"status": "block"},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            result = evaluate_fixture_tree(root, include_passed=True)

        label_metrics = result["metrics"]["label_metrics"]
        self.assertEqual(result["failed"], 1)
        self.assertEqual(label_metrics["false_negative"], 1)
        self.assertEqual(label_metrics["false_positive"], 1)
        issue_checks = {issue["check"] for issue in result["results"][0]["issues"]}
        self.assertIn("labels.expected_findings", issue_checks)
        self.assertIn("labels.forbidden_findings", issue_checks)

    def test_fixture_evaluation_counts_expected_and_forbidden_rule_labels(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            expected_path = root / "rules.expected.json"
            expected_path.write_text(
                json.dumps(
                    {
                        "id": "RULES-001",
                        "title": "rule metrics",
                        "phase": "audit_request",
                        "kind": "requirement",
                        "text": "画面をいい感じにする",
                        "strict": True,
                        "labels": {
                            "expected_rules": ["req.verifiability.acceptance_missing"],
                            "forbidden_rules": ["req.interface.contract_missing"],
                        },
                        "expect": {"status": "block"},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            result = evaluate_fixture_tree(root, include_passed=True)

        label_metrics = result["metrics"]["label_metrics"]
        self.assertEqual(result["failed"], 0)
        self.assertEqual(label_metrics["expected_rule_matched"], 1)
        self.assertEqual(label_metrics["forbidden_rule_clean"], 1)
        self.assertEqual(label_metrics["expected_rule_recall"], 1.0)
        self.assertEqual(label_metrics["forbidden_rule_clean_rate"], 1.0)

    def test_fixture_evaluation_can_match_logical_derivation_expectations(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            expected_path = root / "derivation.expected.json"
            expected_path.write_text(
                json.dumps(
                    {
                        "id": "DERIVATION-001",
                        "title": "logical derivation expectation",
                        "phase": "audit_request",
                        "kind": "requirement",
                        "text": "目的: 速度改善をしたい。",
                        "strict": True,
                        "expect": {
                            "status": "block",
                            "derivation_status": "derived",
                            "derivation_rule_id": "req.verifiability.acceptance_missing",
                            "derivation_missing_obligation": "obl.req.verifiability.verification_or_acceptance",
                            "derivation_countercondition": "ctr.req.verifiability.input_kind_not_requirement",
                            "derivation_fact": "text.has_verification_language",
                            "logical_trace_rule": {
                                "rule_id": "req.verifiability.acceptance_missing",
                                "status": "derived",
                            },
                            "logical_trace_summary_rule": {
                                "rule_id": "req.verifiability.acceptance_missing",
                                "status": "derived",
                                "finding_count": 1,
                            },
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            result = evaluate_fixture_tree(root, include_passed=True)

        self.assertEqual(result["failed"], 0)
        self.assertEqual(result["metrics"]["derivation_rule_hits"]["req.verifiability.acceptance_missing"], 1)
        self.assertEqual(result["metrics"]["derivation_status_hits"]["derived"], 1)
        self.assertEqual(result["metrics"]["logical_trace_rule_hits"]["req.verifiability.acceptance_missing"], 1)
        self.assertEqual(result["metrics"]["logical_trace_summary_rule_hits"]["req.verifiability.acceptance_missing"], 1)

    def test_fixture_evaluation_can_match_ambiguity_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            expected_path = root / "ambiguity.expected.json"
            expected_path.write_text(
                json.dumps(
                    {
                        "id": "AMBIGUITY-001",
                        "title": "structured ambiguity diagnostics",
                        "phase": "audit_plan",
                        "kind": "plan",
                        "text": (
                            "目的: 欠落候補を表示する。\n"
                            "対象外: 判定器の大改修はしない。\n"
                            "成果物: core.py。\n"
                            "手順: 実装、整理。\n"
                            "依存: 既存 API。\n"
                            "リスク: 誤警告。\n"
                            "点検方針: 人間が画面を見る。\n"
                            "妥当性: 要望に合う。\n"
                            "戻し方: 差分を戻す。\n"
                            "証拠: 結果を残す。\n"
                            "未確定: なし。\n"
                        ),
                        "strict": True,
                        "labels": {
                            "expected_findings": [
                                {
                                    "finding_contains": "verification_plan",
                                    "match_status": "partial",
                                    "confidence": "medium",
                                    "ambiguity_reason": "weak_synonym",
                                    "candidate_status": "partial",
                                    "candidate_matched_by": "field_hint",
                                }
                            ]
                        },
                        "expect": {"status": "block"},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            result = evaluate_fixture_tree(root, include_passed=True)

        self.assertEqual(result["failed"], 0)
        self.assertEqual(result["metrics"]["match_status_hits"]["partial"], 1)
        self.assertEqual(result["metrics"]["confidence_hits"]["medium"], 1)
        self.assertEqual(result["metrics"]["ambiguity_reason_hits"]["weak_synonym"], 1)


if __name__ == "__main__":
    unittest.main()
