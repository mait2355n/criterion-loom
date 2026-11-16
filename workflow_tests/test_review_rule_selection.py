"""Which rules a reviewer is shown, what it is told about exclusions, and bad rule ids."""

from __future__ import annotations

import unittest

from semantic_guard_workflow.core import audit_request
from semantic_guard_workflow.llm_review import CandidateGapReviewInput, build_candidate_gap_review_prompt
from semantic_guard_workflow.mcp_server import llm_review_command_tool, llm_review_run_tool


def related_prefixes(payload: dict[str, object]) -> set[str]:
    review_input = CandidateGapReviewInput.from_mapping(payload)
    return {str(rule["id"]).split(".")[0] for rule in review_input.related_rules}


class RelatedRuleSelectionTests(unittest.TestCase):
    REQUEST = audit_request("利用者: 運用者。目的: 検索を速くする。")
    DOCUMENT = audit_request("# Title\n\n## Overview\n\nA document.\n", input_kind="document")

    def test_a_requirement_review_is_not_shown_document_rules(self) -> None:
        for name, payload in (
            ("audit result", {"candidate": "x", "phase": "audit_request", "deterministic_audit": self.REQUEST}),
            ("no audit", {"candidate": "x", "phase": "audit_request"}),
            ("explicit kind", {"candidate": "x", "phase": "audit_request", "input_kind": "requirement"}),
        ):
            with self.subTest(name):
                self.assertEqual(related_prefixes(payload), {"req"})

    def test_a_document_review_is_shown_only_document_rules(self) -> None:
        for name, payload in (
            ("audit result", {"candidate": "x", "phase": "audit_request", "deterministic_audit": self.DOCUMENT}),
            ("explicit kind", {"candidate": "x", "phase": "audit_request", "input_kind": "document"}),
        ):
            with self.subTest(name):
                self.assertEqual(related_prefixes(payload), {"doc"})

    def test_the_prompt_for_a_requirement_is_smaller_than_the_unfiltered_one(self) -> None:
        filtered = build_candidate_gap_review_prompt(
            CandidateGapReviewInput.from_mapping({"candidate": "x", "phase": "audit_request"})
        )
        everything = build_candidate_gap_review_prompt(
            CandidateGapReviewInput.from_mapping({"candidate": "x", "phase": "audit_request", "input_kind": "document"})
        )

        self.assertNotIn("doc.usage.example_missing", filtered)
        self.assertNotIn("req.clarity.ambiguous_term", everything)

    def test_explicit_rule_ids_are_honoured_whatever_their_prefix(self) -> None:
        payload = {"candidate": "x", "rule_ids": ["doc.usage.example_missing", "req.clarity.ambiguous_term"]}

        self.assertEqual(related_prefixes(payload), {"doc", "req"})

    def test_the_other_phases_are_unchanged(self) -> None:
        self.assertEqual(related_prefixes({"candidate": "x", "phase": "audit_plan"}), {"plan"})
        self.assertEqual(related_prefixes({"candidate": "x", "phase": "finish_check"}), {"finish"})


class UnknownRuleIdTests(unittest.TestCase):
    def test_an_unknown_rule_id_is_a_value_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "no.such.rule"):
            CandidateGapReviewInput.from_mapping({"candidate": "x", "rule_ids": ["no.such.rule"]})

    def test_the_mcp_tools_report_it_as_an_input_error(self) -> None:
        payload = {"candidate": "x", "rule_ids": ["req.clarity.ambiguous_term", "no.such.rule"]}
        for result in (llm_review_command_tool(payload), llm_review_run_tool(payload)):
            with self.subTest(tool=result):
                self.assertEqual(result["execution_status"], "input_error")
                self.assertFalse(result["valid"])
                self.assertIn("no.such.rule", " ".join(result["errors"]))

    def test_a_non_array_rule_ids_is_still_an_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "array"):
            CandidateGapReviewInput.from_mapping({"candidate": "x", "rule_ids": "req.clarity.ambiguous_term"})


class ExclusionConditionTests(unittest.TestCase):
    def test_the_prompt_says_the_exclusions_are_advisory(self) -> None:
        prompt = build_candidate_gap_review_prompt(CandidateGapReviewInput.from_mapping({"candidate": "x", "phase": "audit_plan"}))

        self.assertIn("does_not_apply_when は助言", prompt)
        self.assertIn("強制しているとは限らない", prompt)

    def test_a_description_of_the_existing_implementation_is_not_a_fixed_solution(self) -> None:
        for text in ("現行実装は PostgreSQL に保存している。", "Currently the service stores data in SQLite.", "既存の MCP 経由で呼び出している。"):
            with self.subTest(text=text):
                self.assertNotIn("req.solution.implementation_fixed", {f.get("rule_id") for f in audit_request(text)["findings"]})

    def test_a_new_requirement_that_fixes_the_product_still_is(self) -> None:
        for text in ("利用者: 運用者。目的: 一覧を表示する。保存は PostgreSQL を使う。", "The service shall store data in SQLite."):
            with self.subTest(text=text):
                self.assertIn("req.solution.implementation_fixed", {f.get("rule_id") for f in audit_request(text)["findings"]})


if __name__ == "__main__":
    unittest.main()
