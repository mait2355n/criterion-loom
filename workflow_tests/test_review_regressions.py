"""Defects found by re-running a review's recorded repros, each pinned where it was found."""

from __future__ import annotations

import io
import sys
import time
import unittest
from contextlib import redirect_stderr
from unittest.mock import patch

from semantic_guard_workflow.cli import main
from semantic_guard_workflow.conventions import audit_conventions
from semantic_guard_workflow.core import audit_diff, audit_plan, audit_request
from semantic_guard_workflow.request_signals import _precondition_or_trigger_signal as precondition
from semantic_guard_workflow.rule_mapping import infer_rule_id
from semantic_guard_workflow.traceability import build_trace_report


class SpansAndExcerptsTests(unittest.TestCase):
    BODY = ["目的: 検索を速くする。", "背景: 現行は遅い。", "利用者: 運用者。", "受入基準: 200ms以内。", "検証方法: pytest。", "対象外: UI。"]

    def test_an_excerpt_is_one_line_whatever_ends_the_lines(self) -> None:
        excerpts = set()
        for separator in ("\n", "\r\n", "\r", " ", "\x85"):
            result = audit_request(separator.join(self.BODY))
            fact = next(item for item in result["details"]["logical_trace"]["facts"] if item["id"] == "fact.text.requires_scenario_context")
            excerpts.add(fact["evidence"][0]["excerpt"])

        self.assertEqual(excerpts, {"対象外: UI。"})


class ReferentLineTests(unittest.TestCase):
    def test_a_referent_line_says_which_text_it_is_in(self) -> None:
        details = audit_conventions("それを外部へ出す。", context="C1\nC2", input_kind="document")["details"]["expression_precision"]

        self.assertTrue(details["referent_resolutions"])
        for item in details["referent_resolutions"]:
            self.assertEqual((item["source"], item["source_line"], item["line"]), ("text", 1, 3))

    def test_a_line_in_the_context_is_marked_as_context(self) -> None:
        details = audit_conventions("書類を整理する。", context="それを外部へ出す。", input_kind="document")["details"]["expression_precision"]

        sources = {item["source"] for item in details["referent_resolutions"]}
        self.assertTrue(sources <= {"context", "text"})


class TraceReportSpellingTests(unittest.TestCase):
    REQUEST = "目的: 検索応答時間を短縮する。受入基準: 検索応答時間の p95 が 500ms 以下。検証方法: pytest で性能試験を実行する。"
    PLAN = "目的: 検索応答時間を短縮する。手順: 性能試験を追加し、検索応答時間の p95 を測定する。検証方法: pytest。"

    def strengths(self, plan: str) -> list[str]:
        return [link["strength"] for link in build_trace_report({"request": self.REQUEST, "plan": plan})["links"]]

    def test_links_do_not_depend_on_spelling(self) -> None:
        base = self.strengths(self.PLAN)

        self.assertEqual(self.strengths(self.PLAN.replace("検索応答時間", "検索応答​時間")), base)
        self.assertEqual(self.strengths(self.PLAN.replace("p95", "ｐ９５")), base)


class RuleAttributionTests(unittest.TestCase):
    def test_a_short_text_inside_a_rules_wording_attributes_nothing(self) -> None:
        for phase, text in (("audit_request", "。"), ("audit_diff", "証拠"), ("audit_diff", "API")):
            with self.subTest(text=text):
                self.assertEqual(infer_rule_id(phase, {"finding": text}), "")

    def test_a_finding_that_quotes_the_rules_wording_still_belongs_to_it(self) -> None:
        from semantic_guard_workflow.rules import RULES

        rule = next(item for item in RULES if item.phase == "audit_plan" and item.finding)
        self.assertEqual(infer_rule_id("audit_plan", {"finding": rule.finding}), rule.id)
        self.assertEqual(infer_rule_id("audit_plan", {"finding": rule.finding + " 補足"}), rule.id)


class InputKindTests(unittest.TestCase):
    def test_the_plan_and_diff_audits_refuse_another_kind(self) -> None:
        with self.assertRaisesRegex(ValueError, "audit_plan audits a plan"):
            audit_plan("利用者: 保守者。目的: 旧 JSON を読み込む。", input_kind="requirement")
        with self.assertRaisesRegex(ValueError, "audit_diff audits a diff summary"):
            audit_diff("Changed files: a.py", input_kind="document")
        self.assertEqual(audit_plan("目的: 直す。", input_kind="plan")["phase"], "audit_plan")

    def test_the_cli_reports_the_mismatch_as_a_usage_error(self) -> None:
        for command in ("audit-plan", "audit-diff"):
            with self.subTest(command=command):
                stderr = io.StringIO()
                argv = ["semantic-guard", command, "--kind", "requirement", "--text", "目的: 旧 JSON を読み込む。"]
                with patch.object(sys, "argv", argv), redirect_stderr(stderr), self.assertRaises(SystemExit) as raised:
                    main()

                self.assertEqual(raised.exception.code, 2)
                self.assertIn("--kind requirement", stderr.getvalue())


class LabelSynonymCollisionTests(unittest.TestCase):
    """A label that is a natural synonym must not be mistaken for another field."""

    def test_a_completion_condition_is_not_a_precondition(self) -> None:
        for text in ("完了条件: 200ms 以内", "不合格条件: 500ms 超", "受入条件: pytest 通過", "終了条件: 全件処理"):
            with self.subTest(text=text):
                self.assertEqual(precondition(text), "")
        self.assertTrue(precondition("条件: 認証済みの場合"))
        self.assertTrue(precondition("前提条件: 管理者であること"))

    def test_a_responsible_person_does_not_answer_a_risk_or_a_hazard(self) -> None:
        plan = (
            "目的: 通信設定を直して接続失敗を減らす。\n対象外: UI。\n手順: 調査、修正、検証。\n"
            "判断主体: 保守者が受入を判断する。\n"
        )
        renamed = plan.replace("判断主体", "責任者")

        self.assertEqual(
            {finding["rule_id"] for finding in audit_plan(plan)["findings"]},
            {finding["rule_id"] for finding in audit_plan(renamed)["findings"]},
        )

    def test_the_natural_synonyms_are_accepted_as_the_field_they_name(self) -> None:
        request = (
            "利用者: 運用者。ねらい: 検索を速くする。シナリオ: 運用者が検索語を入力した場合、一覧が返る。"
            "完了条件: 検索応答時間の p95 が 500ms 以下。検証方法: pytest で p95 を測る。証拠: 結果を保存する。"
            "不合格条件: p95 が 500ms を超えた場合は差し戻し。対象外: UI刷新。"
        )
        rules = {finding["rule_id"] for finding in audit_request(request)["findings"]}

        self.assertNotIn("req.necessity.purpose_trace_missing", rules)
        self.assertNotIn("req.quality.measurable_constraint_missing", rules)


class LongRequestTests(unittest.TestCase):
    def test_many_records_are_audited_in_roughly_linear_time(self) -> None:
        unit = "目的: 検索する。受入基準: 200ms以内。検証方法: pytest。\n"
        started = time.perf_counter()
        audit_request(unit * 800)  # 29,600 characters took 22 s when each record rescanned the others
        self.assertLess(time.perf_counter() - started, 5.0)


if __name__ == "__main__":
    unittest.main()
