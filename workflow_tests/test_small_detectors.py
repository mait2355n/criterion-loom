"""Small detector defects: word boundaries, spans, line breaks and counting."""

from __future__ import annotations

import unittest

from semantic_guard_workflow.core import audit_plan, audit_request
from semantic_guard_workflow.plan_audit import _deliverable_item_count
from semantic_guard_workflow.text_utils import excerpt_around, first_match


def rule_ids(result: dict[str, object]) -> set[object]:
    return {finding.get("rule_id") for finding in result["findings"]}


class WordBoundaryTests(unittest.TestCase):
    def test_not_inside_another_word_is_no_scope_boundary(self) -> None:
        result = audit_request("Users get a notification when a note is saved.")

        self.assertIn("req.scope.non_goals_missing", rule_ids(result))

    def test_a_real_english_boundary_still_counts(self) -> None:
        result = audit_request("Users get a notification. Do not change the billing flow.")

        self.assertNotIn("req.scope.non_goals_missing", rule_ids(result))

    def test_tool_names_inside_other_words_do_not_fix_the_solution(self) -> None:
        for text in ("利用者: 運用者。目的: client の一覧を表示する。capital rapid.", "The capital city of the rapid client"):
            with self.subTest(text=text):
                self.assertNotIn("req.solution.implementation_fixed", rule_ids(audit_request(text)))

    def test_a_tool_name_as_a_word_still_does(self) -> None:
        self.assertIn("req.solution.implementation_fixed", rule_ids(audit_request("利用者: 運用者。目的: 一覧を CLI で表示する。")))


class SpanAndLineTests(unittest.TestCase):
    def test_the_turkish_dotted_capital_does_not_shift_a_span(self) -> None:
        self.assertEqual(first_match("İİ\nsecond line has TOKEN here", ["token"]), "second line has TOKEN here")

    def test_fact_spans_index_the_original_text_after_a_dotted_capital(self) -> None:
        text = "İ" * 5 + "\n利用者: 運用者。目的: 検索応答性能を保証する。\n受入基準: 応答は 200ms 以内。"

        facts = audit_request(text)["details"]["logical_trace"]["facts"]
        spans = [span for fact in facts for span in fact["evidence"] if span.get("start") is not None]

        self.assertTrue(spans)
        for span in spans:
            self.assertIn(text[span["start"]:span["end"]].lower(), span["excerpt"].lower() + text[span["start"]:span["end"]].lower())
            self.assertEqual(text[span["start"]:span["end"]][:1], text[span["start"]:span["end"]][:1])
        label = next(span for span in spans if text[span["start"]:span["end"]] == "受入基準")
        self.assertEqual(label["excerpt"], "受入基準: 応答は 200ms 以内。")

    def test_excerpts_stop_at_every_kind_of_line_break(self) -> None:
        cases = (
            ("a\rb TARGET c\rd", "b TARGET c"),
            ("甲 乙 TARGET 丙 丁", "乙 TARGET 丙"),
            ("a\x85b TARGET c\x85d", "b TARGET c"),
            ("a b TARGET c d", "b TARGET c"),
            ("a\nb TARGET c\nd", "b TARGET c"),
        )
        for text, expected in cases:
            with self.subTest(text=repr(text)):
                start = text.index("TARGET")
                self.assertEqual(excerpt_around(text, start, start + len("TARGET")), expected)


class DeliverableCountTests(unittest.TestCase):
    def test_list_items_under_the_label_are_counted(self) -> None:
        self.assertEqual(_deliverable_item_count("成果物:\n- 文書A\n- 文書B\n- 文書C\n手順: 作る"), 3)
        self.assertEqual(_deliverable_item_count("成果物:\n1. 文書A\n2. 文書B\n"), 2)

    def test_a_path_is_one_deliverable(self) -> None:
        self.assertEqual(_deliverable_item_count("成果物: src/app.py、tests/test_app.py"), 2)
        self.assertEqual(_deliverable_item_count("成果物: src/app.py"), 1)

    def test_a_spaced_or_full_width_slash_separates_deliverables(self) -> None:
        self.assertEqual(_deliverable_item_count("成果物: 文書A / 文書B"), 2)
        self.assertEqual(_deliverable_item_count("成果物: 文書A／文書B"), 2)

    def test_the_count_stops_at_a_semicolon(self) -> None:
        self.assertEqual(_deliverable_item_count("成果物: 文書A、文書B; 手順: 調査、実装、検証。"), 2)
        self.assertEqual(_deliverable_item_count("成果物: 文書A、文書B；手順: 調査、実装、検証。"), 2)


class PlanContextTests(unittest.TestCase):
    PLAN = "目的: 設定読込を直す。\n検証: 後で決める。\n"

    def test_request_and_context_do_not_cancel_the_plans_own_deferral(self) -> None:
        for kwargs in (
            {"request": "設定読込を直し、検証を行うこと。"},
            {"context": "検証は pytest"},
            {"context": "検証: pytest を実行する。"},
        ):
            with self.subTest(kwargs=kwargs):
                self.assertIn("verification_plan", audit_plan(self.PLAN, **kwargs)["missing"])

    def test_request_and_context_fill_a_field_the_plan_does_not_state(self) -> None:
        plan = "目的: 設定読込を直す。\n"

        self.assertIn("verification_plan", audit_plan(plan)["missing"])
        self.assertNotIn("verification_plan", audit_plan(plan, context="検証: pytest を実行する。")["missing"])


if __name__ == "__main__":
    unittest.main()
