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
    Silent,
    Verdict,
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

    def _known_drift_report(self, mutation: str, status_after: str, hiding: bool = False) -> dict[str, object]:
        fixture = "requests/verification-target-mismatch.expected.json"
        rule = "req.relation.verification_target_mismatch"
        known = {
            (name, fixture): {
                "reason": "synthetic exception used to exercise the allowance",
                "status": {"before": "warn", "after": status_after},
                "lost": [rule] if hiding else [],
                "gained": [],
            }
            for name in ("fullwidth_ascii", "decomposed_kana", "halfwidth_katakana")
        }
        rewrites = tuple(item for item in REWRITES if item.name in {name for name, _ in known})
        original_rerun = metamorphic._rerun

        def altered(spec, expected_path, text):
            result = original_rerun(spec, expected_path, text)
            if expected_path.name == "verification-target-mismatch.expected.json":
                result["status"] = status_after
                if hiding:
                    result["findings"] = [item for item in result["findings"] if item.get("rule_id") != rule]
                if mutation == "finding":
                    result["findings"].append({"severity": "blocker", "category": "security", "rule_id": "req.example.unrelated_regression"})
                elif mutation == "status":
                    result["status"] = "blocked"
            return result

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "requests" / "verification-target-mismatch.expected.json"
            target.parent.mkdir()
            target.write_text((Path(DEFAULT_FIXTURE_ROOT) / "requests" / target.name).read_text(encoding="utf-8"), encoding="utf-8")
            with (
                patch.object(metamorphic, "REWRITES", rewrites),
                patch.object(metamorphic, "KNOWN_DRIFT", known),
                patch.object(metamorphic, "_rerun", altered),
            ):
                return evaluate_invariance(root)

    def test_known_drift_accepts_only_the_exact_recorded_delta(self) -> None:
        # warn -> block with no rule change is excused exactly as recorded.
        report = self._known_drift_report("exact", "block")
        self.assertTrue(report["passed"])
        self.assertEqual(len(report["known_drift"]), 3)

        for mutation in ("finding", "status"):
            with self.subTest(mutation=mutation):
                report = self._known_drift_report(mutation, "block")
                self.assertFalse(report["passed"])
                self.assertEqual(len(report["unexpected_drift"]), 3)

    def test_an_exception_may_not_excuse_a_finding_that_vanished_into_a_pass(self) -> None:
        report = self._known_drift_report("exact", "pass", hiding=True)

        self.assertEqual(len(report["known_drift"]), 3)
        self.assertEqual(len(report["known_drift_hiding_findings"]), 3)
        self.assertFalse(report["passed"])

    def test_no_rewrite_drifts_on_the_repository_fixtures(self) -> None:
        self.assertEqual(metamorphic.KNOWN_DRIFT, {})
        report = evaluate_invariance()

        self.assertEqual(report["drifted"], 0)
        self.assertEqual(report["known_drift"], [])

    def test_a_narrowed_invisible_character_set_makes_the_harness_fail(self) -> None:
        import re

        narrowed = re.compile("[\ufeff\u200b]")
        with (
            patch("semantic_guard_workflow.text_normalization._invisible_pattern", lambda: narrowed),
        ):
            report = evaluate_invariance()

        self.assertFalse(report["passed"])
        self.assertIn("invisible_inside_words", {row["rewrite"] for row in report["unexpected_drift"]})

    def test_the_signature_sees_severity_score_and_gaps(self) -> None:
        base = {"status": "warn", "score": 0.8, "missing": ["a"], "findings": [{"severity": "major", "category": "x", "rule_id": "r.one"}]}
        verdict = metamorphic._signature(base, "audit_plan")
        self.assertIsInstance(verdict, Verdict)

        for change, mutate in {
            "severity": lambda r: r["findings"][0].update(severity="minor"),
            "score": lambda r: r.update(score=0.7),
            "missing": lambda r: r.update(missing=["a", "b"]),
            "count": lambda r: r["findings"].append({"severity": "major", "category": "x", "rule_id": "r.one"}),
        }.items():
            with self.subTest(change=change):
                variant = json.loads(json.dumps(base))
                mutate(variant)
                self.assertNotEqual(metamorphic._signature(variant, "audit_plan"), verdict)

    def test_a_severity_change_in_a_variant_is_reported_as_drift(self) -> None:
        original = metamorphic._rerun
        broken = RewriteSpec("one_space", "adds a trailing space", lambda text: text + " ")

        def lowered(spec, path, text):
            result = original(spec, path, text)
            for finding in result["findings"]:
                finding["severity"] = "info"
            return result

        with patch.object(metamorphic, "REWRITES", (broken,)), patch.object(metamorphic, "_rerun", lowered):
            report = evaluate_invariance()

        self.assertFalse(report["passed"])
        self.assertTrue(any("findings" in row.get("other", {}) or row["status"]["before"] != row["status"]["after"] for row in report["unexpected_drift"]))

    def test_rewrites_that_change_nothing_are_not_counted_as_checks(self) -> None:
        report = evaluate_invariance()

        self.assertGreater(report["identity"], 0)
        self.assertEqual(report["checked"], sum(row["checked"] for row in report["rewrites"].values()))
        for name, row in report["rewrites"].items():
            with self.subTest(rewrite=name):
                self.assertGreater(row["checked"], 0)
        self.assertGreaterEqual(report["checked"], metamorphic.MINIMUM_CHECKED_COMPARISONS)

    def test_an_empty_or_missing_tree_does_not_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            empty = evaluate_invariance(temporary)
        missing = evaluate_invariance(Path(temporary) / "nowhere")

        self.assertFalse(empty["passed"])
        self.assertTrue(empty["too_few_comparisons"])
        self.assertFalse(missing["passed"])
        self.assertIn("not a directory", missing["error"])
        self.assertFalse(evaluate_metamorphic(Path(temporary) / "nowhere")["passed"])

    def test_the_new_rewrites_cover_every_line_terminator_and_format_character(self) -> None:
        names = {rewrite.name for rewrite in REWRITES}

        self.assertTrue({"invisible_inside_words", "cr_line_breaks", "line_separators", "paragraph_separators", "next_line_breaks"} <= names)
        by_name = {rewrite.name: rewrite for rewrite in REWRITES}
        self.assertEqual(by_name["crlf"].apply("a\r\nb\nc"), "a\r\nb\r\nc")
        inside = by_name["invisible_inside_words"].apply("検証方法: pytest を実行する。")
        self.assertNotEqual(inside, "検証方法: pytest を実行する。")
        self.assertEqual(normalize_audit_text(inside), "検証方法: pytest を実行する。")

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
            {**plan.expectations, "戻し方": Silent("claimed to be covered elsewhere", also_remove=("証拠",), expected_rules=("plan.completion.evidence_missing",))},
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


class SilentEntryTests(unittest.TestCase):
    def _report(self, field: str, entry: object) -> dict[str, object]:
        plan = ABLATION_DOCUMENTS[0]
        document = AblationDocument(plan.document_id, plan.phase, plan.fixture, {**plan.expectations, field: entry})
        return evaluate_sensitivity((document,))

    def test_a_bare_reason_is_no_longer_accepted(self) -> None:
        report = self._report("依存", "covered elsewhere")

        self.assertFalse(report["passed"])
        self.assertIn("Silent entry", report["mismatches"][0]["note"])

    def test_the_joint_removal_must_raise_the_stated_rule(self) -> None:
        wrong = Silent("claims a rule that never fires", also_remove=("順序",), expected_rules=("plan.risk.rollback_missing",))

        report = self._report("依存", wrong)

        self.assertFalse(report["passed"])
        self.assertIn("did not raise", report["mismatches"][0]["note"])

    def test_the_joint_removal_must_leave_the_stated_gap(self) -> None:
        wrong = Silent("claims a gap that stays closed", also_remove=("順序",), expected_missing=("rollback_or_recovery",))

        self.assertFalse(self._report("依存", wrong)["passed"])

    def test_fields_to_remove_together_must_exist(self) -> None:
        report = self._report("依存", Silent("names a field that is not there", also_remove=("存在しない",), expected_missing=("dependencies",)))

        self.assertFalse(report["passed"])
        self.assertIn("do not exist", report["mismatches"][0]["note"])

    def test_a_silent_entry_must_state_what_it_expects(self) -> None:
        report = self._report("依存", Silent("explains nothing", also_remove=("順序",)))

        self.assertFalse(report["passed"])
        self.assertIn("must state", report["mismatches"][0]["note"])

    def test_a_cover_that_is_gone_is_reported(self) -> None:
        report = self._report("依存", Silent("claims wording that is not in the text", also_remove=("順序",), still_present="存在しない語"))

        self.assertFalse(report["passed"])
        self.assertIn("stated cover is gone", report["mismatches"][0]["note"])


class RuleCoverageTests(unittest.TestCase):
    def test_the_assertions_cover_a_stated_share_of_the_catalog(self) -> None:
        report = evaluate_sensitivity()

        self.assertGreaterEqual(report["asserted_rule_count"], metamorphic.MINIMUM_ASSERTED_RULES)
        self.assertEqual(report["catalog_rule_count"], 73)
        catalog = {rule.id for rule in metamorphic.RULES}
        self.assertTrue(set(report["asserted_rules"]) <= catalog)

    def test_dropping_a_document_below_the_floor_fails(self) -> None:
        report = evaluate_sensitivity()
        reduced = tuple(document for document in ABLATION_DOCUMENTS if document.phase == "audit_plan")
        with patch.object(metamorphic, "ABLATION_DOCUMENTS", reduced):
            floor = evaluate_sensitivity()

        self.assertTrue(report["passed"])
        self.assertFalse(floor["passed"])
        self.assertTrue(any("rules are asserted" in row["note"] for row in floor["mismatches"]))

    def test_finish_and_document_phases_are_exercised(self) -> None:
        phases = {(document["document"], document["phase"]) for document in evaluate_sensitivity()["documents"]}

        self.assertIn(("finish/public-behavior-good", "finish_check"), phases)
        self.assertIn(("documents/readme-good", "audit_request"), phases)


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

    def test_cli_reports_a_bad_path_as_json_and_fails(self) -> None:
        stdout = io.StringIO()
        with (
            patch.object(sys, "argv", ["semantic-guard", "evaluate-metamorphic", "--path", "/nonexistent-fixture-root"]),
            redirect_stdout(stdout),
            self.assertRaises(SystemExit) as raised,
        ):
            main()

        self.assertEqual(raised.exception.code, 1)
        payload = json.loads(stdout.getvalue())
        self.assertFalse(payload["passed"])
        self.assertIn("not a directory", payload["error"])

    def test_combined_report_requires_both_checks(self) -> None:
        report = evaluate_metamorphic()

        self.assertEqual(report["passed"], report["invariance"]["passed"] and report["sensitivity"]["passed"])


if __name__ == "__main__":
    unittest.main()
