from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from semantic_guard_workflow import metamorphic
from semantic_guard_workflow.cli import main
from semantic_guard_workflow.evaluation import DEFAULT_FIXTURE_ROOT, _fixture_text, _load_spec
from semantic_guard_workflow.metamorphic import (
    ABLATION_DOCUMENTS,
    REWRITES,
    AblationDocument,
    RewriteSpec,
    evaluate_invariance,
    evaluate_metamorphic,
    evaluate_sensitivity,
)
from semantic_guard_workflow.text_normalization import normalize_audit_text

CHARACTER_LEVEL = ("fullwidth_ascii", "decomposed_kana", "halfwidth_katakana", "ideographic_space", "invisible_characters", "crlf")


class InvarianceTests(unittest.TestCase):
    def test_structural_rewrites_skip_code_and_ordered_blocks_with_reasons(self) -> None:
        rewrites = tuple(
            item for item in REWRITES
            if item.name in {"rotated_lines", "sentence_newlines"}
        )
        inputs = (
            '```python\nvalue = "甲。乙"\n```\n目的: 値を保存する。',
            '~~~python\nvalue = "甲。乙"\n~~~\n目的: 値を保存する。',
            "目的: 更新する。\n1. 退避する。\n2. 元資料を削除する。",
        )
        for text in inputs:
            with self.subTest(text=text), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                (root / "input.expected.json").write_text(json.dumps({
                    "phase": "audit_plan", "kind": "plan", "text": text,
                }), encoding="utf-8")
                with (
                    patch.object(metamorphic, "REWRITES", rewrites),
                    patch.object(metamorphic, "KNOWN_DRIFT", {}),
                ):
                    report = evaluate_invariance(root)
                self.assertEqual(report["checked"], 0)
                self.assertEqual(len(report["skipped"]), 2)
                self.assertTrue(all(row["reason"] for row in report["skipped"]))

    def test_structural_rewrites_still_exercise_flat_field_records(self) -> None:
        rewrites = tuple(
            item for item in REWRITES
            if item.name in {"rotated_lines", "sentence_newlines"}
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "input.expected.json").write_text(json.dumps({
                "phase": "audit_plan", "kind": "plan",
                "text": "目的: 値を保存する。\n対象外: 表示は変えない。",
            }), encoding="utf-8")
            with (
                patch.object(metamorphic, "REWRITES", rewrites),
                patch.object(metamorphic, "KNOWN_DRIFT", {}),
            ):
                report = evaluate_invariance(root)
        self.assertEqual(report["checked"], 2)

    def test_known_drift_rejects_unrelated_findings_and_changed_status(self) -> None:
        fixture = "requests/verification-target-mismatch.expected.json"
        rule = "req.relation.verification_target_mismatch"
        known = {
            (name, fixture): {
                "reason": "synthetic exception used to exercise the allowance",
                "status": {"before": "warn", "after": "pass"},
                "lost": [rule],
                "gained": [],
            }
            for name in ("fullwidth_ascii", "decomposed_kana", "halfwidth_katakana")
        }
        rewrites = tuple(item for item in REWRITES if item.name in {name for name, _ in known})
        original_rerun = metamorphic._rerun
        for mutation in ("exact", "finding", "status"):
            def altered(spec, expected_path, text):
                result = original_rerun(spec, expected_path, text)
                if expected_path.name == "verification-target-mismatch.expected.json":
                    result["status"] = "pass"
                    result["findings"] = [item for item in result["findings"] if item.get("rule_id") != rule]
                    if mutation == "finding":
                        result["findings"].append({
                            "severity": "blocker", "category": "security",
                            "rule_id": "req.example.unrelated_regression",
                        })
                    elif mutation == "status":
                        result["status"] = "blocked"
                return result

            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                target = root / "requests" / "verification-target-mismatch.expected.json"
                target.parent.mkdir()
                target.write_text((Path(DEFAULT_FIXTURE_ROOT) / "requests" / target.name).read_text(encoding="utf-8"), encoding="utf-8")
                with (
                    patch.object(metamorphic, "REWRITES", rewrites),
                    patch.object(metamorphic, "KNOWN_DRIFT", known),
                    patch.object(metamorphic, "_rerun", altered),
                ):
                    report = evaluate_invariance(root)
                if mutation == "exact":
                    self.assertTrue(report["passed"])
                    self.assertEqual(len(report["known_drift"]), 3)
                else:
                    self.assertFalse(report["passed"])
                    self.assertEqual(len(report["unexpected_drift"]), 3)

    def test_no_rewrite_drifts_on_the_repository_fixtures(self) -> None:
        self.assertEqual(metamorphic.KNOWN_DRIFT, {})
        report = evaluate_invariance()

        self.assertEqual(report["drifted"], 0)
        self.assertEqual(report["known_drift"], [])

    def test_repository_fixtures_are_stable_under_every_rewrite(self) -> None:
        report = evaluate_invariance()

        self.assertEqual(report["unexpected_drift"], [])
        self.assertEqual(report["stale_known_drift"], [])
        self.assertTrue(report["passed"])

    def test_every_rewrite_is_exercised(self) -> None:
        report = evaluate_invariance()

        for rewrite in REWRITES:
            with self.subTest(rewrite=rewrite.name):
                self.assertGreater(report["rewrites"][rewrite.name]["checked"], 0)

    def test_stability_is_high_and_the_only_drift_is_documented(self) -> None:
        report = evaluate_invariance()

        self.assertGreaterEqual(report["stability_rate"], 0.99)
        self.assertEqual(report["drifted"], len(report["known_drift"]))
        for entry in report["known_drift"]:
            self.assertTrue(entry["reason"])

    def test_character_level_rewrites_are_undone_by_normalization(self) -> None:
        by_name = {rewrite.name: rewrite for rewrite in REWRITES}
        for expected_path in sorted(Path(DEFAULT_FIXTURE_ROOT).rglob("*.expected.json")):
            spec = _load_spec(expected_path)
            if spec.get("phase") == "audit_diff":
                continue
            text = _fixture_text(spec, expected_path)
            for name in CHARACTER_LEVEL:
                with self.subTest(fixture=expected_path.name, rewrite=name):
                    self.assertEqual(
                        normalize_audit_text(by_name[name].apply(text)),
                        normalize_audit_text(text),
                    )

    def test_a_destructive_rewrite_is_reported_as_unexpected_drift(self) -> None:
        broken = RewriteSpec("truncate", "keeps only the first sentence", lambda text: text.split("。")[0] + "。")

        with patch.object(metamorphic, "REWRITES", (broken,)):
            report = evaluate_invariance()

        self.assertFalse(report["passed"])
        self.assertTrue(report["unexpected_drift"])
        self.assertEqual({row["rewrite"] for row in report["unexpected_drift"]}, {"truncate"})

    def test_an_exception_that_no_longer_occurs_is_reported_as_stale(self) -> None:
        bogus = {("crlf", "requests/ambiguous.expected.json"): {
            "reason": "never drifts", "status": {"before": "warn", "after": "pass"},
            "lost": ["req.example.absent"], "gained": [],
        }}

        with patch.object(metamorphic, "KNOWN_DRIFT", {**metamorphic.KNOWN_DRIFT, **bogus}):
            report = evaluate_invariance()

        self.assertFalse(report["passed"])
        self.assertEqual([row["rewrite"] for row in report["stale_known_drift"]], ["crlf"])

    def test_fixtures_bound_to_a_recorded_morphology_analysis_are_skipped(self) -> None:
        report = evaluate_invariance()
        morphology_fixtures = [
            path
            for path in Path(DEFAULT_FIXTURE_ROOT).rglob("*.expected.json")
            if _load_spec(path).get("morphology") is not None
        ]

        self.assertTrue(morphology_fixtures)
        self.assertLess(report["checked"], 14 * len(list(Path(DEFAULT_FIXTURE_ROOT).rglob("*.expected.json"))))


class SensitivityTests(unittest.TestCase):
    def test_deleting_a_field_raises_the_rule_that_owns_it(self) -> None:
        report = evaluate_sensitivity()

        self.assertEqual(report["mismatches"], [])
        self.assertTrue(report["passed"])

    def test_the_documents_start_clean(self) -> None:
        for document in evaluate_sensitivity()["documents"]:
            with self.subTest(document=document["document"]):
                self.assertEqual(document["base_status"], "pass")
                self.assertEqual(document["base_findings"], [])

    def test_a_wrong_expectation_is_reported(self) -> None:
        plan = ABLATION_DOCUMENTS[0]
        wrong = AblationDocument(
            plan.document_id,
            plan.phase,
            plan.fixture,
            {**plan.expectations, "戻し方": ("plan.risk.response_missing",)},
        )

        report = evaluate_sensitivity((wrong,))

        self.assertFalse(report["passed"])
        self.assertEqual([row["field"] for row in report["mismatches"]], ["戻し方"])

    def test_documented_silence_fails_once_the_deletion_raises_something(self) -> None:
        plan = ABLATION_DOCUMENTS[0]
        stale = AblationDocument(
            plan.document_id,
            plan.phase,
            plan.fixture,
            {**plan.expectations, "戻し方": "claimed to be covered elsewhere"},
        )

        report = evaluate_sensitivity((stale,))

        self.assertFalse(report["passed"])
        self.assertIn("deletion now raises findings", report["mismatches"][0]["note"])

    def test_a_field_without_an_expectation_is_reported(self) -> None:
        plan = ABLATION_DOCUMENTS[0]
        partial = AblationDocument(
            plan.document_id,
            plan.phase,
            plan.fixture,
            {key: value for key, value in plan.expectations.items() if key != "戻し方"},
        )

        report = evaluate_sensitivity((partial,))

        self.assertEqual([row["field"] for row in report["mismatches"]], ["戻し方"])

    def test_silent_deletions_carry_their_reason(self) -> None:
        silent = [
            row
            for document in evaluate_sensitivity()["documents"]
            for row in document["fields"]
            if not row["raised"]
        ]

        self.assertTrue(silent)
        for row in silent:
            self.assertTrue(row["silent_because"], row["field"])


class MetamorphicCliTests(unittest.TestCase):
    def test_cli_reports_a_passing_run(self) -> None:
        stdout = io.StringIO()
        with patch.object(sys, "argv", ["semantic-guard", "evaluate-metamorphic"]), redirect_stdout(stdout):
            main()
        payload = json.loads(stdout.getvalue())

        self.assertTrue(payload["passed"])
        self.assertIn("not field accuracy", payload["calibration_scope"])

    def test_cli_exits_nonzero_when_the_run_fails(self) -> None:
        broken = RewriteSpec("truncate", "keeps only the first sentence", lambda text: text.split("。")[0] + "。")
        stdout = io.StringIO()
        with (
            patch.object(metamorphic, "REWRITES", (broken,)),
            patch.object(sys, "argv", ["semantic-guard", "evaluate-metamorphic"]),
            redirect_stdout(stdout),
            self.assertRaises(SystemExit) as raised,
        ):
            main()

        self.assertEqual(raised.exception.code, 1)
        self.assertFalse(json.loads(stdout.getvalue())["passed"])

    def test_combined_report_requires_both_checks(self) -> None:
        report = evaluate_metamorphic()

        self.assertEqual(report["passed"], report["invariance"]["passed"] and report["sensitivity"]["passed"])


if __name__ == "__main__":
    unittest.main()
