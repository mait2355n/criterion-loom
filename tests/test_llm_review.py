from __future__ import annotations

import json
import unittest

from semantic_guard.llm_review import (
    SCHEMA_VERSION,
    CandidateGapReviewInput,
    build_candidate_gap_review_prompt,
    candidate_gap_review_schema_path,
    load_candidate_gap_review_schema,
    review_guidance_for_phase,
    validate_candidate_gap_review,
)


class LLMReviewTests(unittest.TestCase):
    def test_schema_file_loads_and_has_no_decision_field(self) -> None:
        schema = load_candidate_gap_review_schema()
        self.assertEqual(schema["properties"]["schema_version"]["const"], SCHEMA_VERSION)
        self.assertTrue(candidate_gap_review_schema_path().exists())
        properties = set(schema["properties"])
        self.assertNotIn("approved", properties)
        self.assertNotIn("final_decision", properties)
        self.assertNotIn("verdict", properties)

    def test_prompt_builds_gap_reviewer_boundary(self) -> None:
        review_input = CandidateGapReviewInput.from_mapping(
            {
                "candidate": "計画: 実装する。検証は後で考える。",
                "request": "不足分の指摘と補填案が欲しい。",
                "audit_result": {"status": "warn", "missing": ["validation_plan"]},
                "rule_ids": ["plan.validation.problem_fit_missing"],
                "non_goals": "合否決定はしない。",
                "phase": "audit_plan",
            }
        )

        prompt = build_candidate_gap_review_prompt(review_input)

        self.assertIn("candidate_gap_reviewer", prompt)
        self.assertIn("合否判定、承認、却下", prompt)
        self.assertIn("phase_guidance", prompt)
        self.assertIn("project planning and technical planning", prompt)
        self.assertIn("rule_item_reviews", prompt)
        self.assertIn("schema内のobject propertiesはすべて出力する", prompt)
        self.assertIn("supplement_proposals", prompt)
        self.assertIn("plan.validation.problem_fit_missing", prompt)
        self.assertIn(SCHEMA_VERSION, prompt)

    def test_phase_without_explicit_rules_loads_phase_rules(self) -> None:
        review_input = CandidateGapReviewInput.from_mapping(
            {
                "candidate": "要求: いい感じに速くする。",
                "phase": "audit_request",
            }
        )

        rule_ids = {rule["id"] for rule in review_input.related_rules}

        self.assertIn("req.verifiability.acceptance_missing", rule_ids)
        self.assertIn("req.scope.non_goals_missing", rule_ids)

    def test_phase_guidance_is_specific(self) -> None:
        request_guidance = review_guidance_for_phase("audit_request")
        plan_guidance = review_guidance_for_phase("audit_plan")

        self.assertEqual(request_guidance["knowledge_area"], "requirements engineering")
        self.assertEqual(plan_guidance["knowledge_area"], "project planning and technical planning")
        self.assertIn("acceptance criteria", " ".join(request_guidance["inspect"]))
        self.assertIn("risk register", " ".join(plan_guidance["inspect"]))

    def test_prompt_can_include_schema(self) -> None:
        prompt = build_candidate_gap_review_prompt(CandidateGapReviewInput(candidate="候補"), include_schema=True)
        self.assertIn("## Output Schema", prompt)
        self.assertIn('"review_status"', prompt)

    def test_validate_accepts_minimum_valid_review(self) -> None:
        payload = {
            "schema_version": SCHEMA_VERSION,
            "review_status": "needs_supplement",
            "missing_aspects": [
                {
                    "kind": "validation_route",
                    "severity": "major",
                    "why_it_matters": "目的適合を確認できない。",
                    "supplement": "受入条件を追加する。",
                }
            ],
            "questionable_assumptions": [
                {
                    "assumption": "既存挙動は変わらない。",
                    "risk": "CLI変更が出力を変える可能性がある。",
                    "supplement": "既存CLI試験を残す。",
                }
            ],
            "possible_counter_conditions": [
                {
                    "rule_id": "diff.test_obligation.source_without_tests",
                    "does_not_apply_when": "文書だけの変更である。",
                    "confidence": "medium",
                    "reason": "差分にソース変更が無い。",
                }
            ],
            "supplement_proposals": [
                {
                    "target": "plan",
                    "proposal": "完了証拠を明記する。",
                    "reason": "finish_checkで必要になる。",
                }
            ],
            "rule_item_reviews": [
                {
                    "rule_id": "plan.validation.problem_fit_missing",
                    "inspected_items": ["concern", "applies_when", "evidence_required"],
                    "missing_items": ["妥当性確認方法"],
                    "counter_condition_candidates": [],
                    "supplement": "目的に合うことを誰が何で確認するかを計画へ足す。",
                    "notes": "中途監査として補填候補だけを返す。",
                }
            ],
            "human_decision_needed": ["codex exec方式を採用するか。"],
        }

        self.assertEqual(validate_candidate_gap_review(payload), [])
        json.dumps(payload, ensure_ascii=False)

    def test_validate_rejects_decision_like_extra_field(self) -> None:
        payload = {
            "schema_version": SCHEMA_VERSION,
            "review_status": "no_supplement_needed",
            "missing_aspects": [],
            "questionable_assumptions": [],
            "possible_counter_conditions": [],
            "supplement_proposals": [],
            "rule_item_reviews": [],
            "human_decision_needed": [],
            "approved": True,
        }

        errors = validate_candidate_gap_review(payload)

        self.assertIn("unexpected field: approved", errors)

    def test_validate_rejects_bad_enum_and_missing_required_item(self) -> None:
        payload = {
            "schema_version": SCHEMA_VERSION,
            "review_status": "approved",
            "missing_aspects": [{"kind": "validation_route", "severity": "major"}],
            "questionable_assumptions": [],
            "possible_counter_conditions": [],
            "supplement_proposals": [],
            "rule_item_reviews": [{"rule_id": "x", "inspected_items": "not-list", "missing_items": []}],
            "human_decision_needed": [],
        }

        errors = validate_candidate_gap_review(payload)

        self.assertTrue(any("review_status" in error for error in errors))
        self.assertTrue(any("why_it_matters" in error for error in errors))
        self.assertTrue(any("supplement" in error for error in errors))
        self.assertTrue(any("inspected_items" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
