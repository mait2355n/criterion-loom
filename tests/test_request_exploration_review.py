import unittest

from semantic_guard.request_exploration_review import (
    RequestExplorationInput,
    build_request_exploration_prompt,
    load_request_exploration_review_schema,
    validate_request_exploration_review,
)


VALID_EXPLORATION = {
    "schema_version": "request-exploration-review/v1",
    "exploration_status": "complete",
    "extracted_information": [
        {
            "kind": "initial_idea",
            "content": "割り勘アプリを作りたい",
            "source": "user_text",
            "status": "fact",
            "confidence": "high",
        }
    ],
    "audience_hypotheses": [
        {
            "id": "organizer",
            "label": "幹事",
            "evidence": "割り勘",
            "scope_implications": ["expense entry", "settlement summary"],
            "confidence": "medium",
        }
    ],
    "material_ambiguities": [
        {
            "id": "settlement_boundary",
            "category": "payment",
            "severity": "major",
            "known_information": ["割り勘が対象"],
            "missing_information": ["実決済を扱うか"],
            "why_material": "実決済を扱うかで権限と安全境界が変わる。",
            "affects": ["scope", "privacy", "authority"],
            "evidence": "割り勘アプリ",
            "question": "実決済まで扱う？",
            "answer_shape": "no real payment; payment link only; full payment flow",
        }
    ],
    "questions": [
        {
            "id": "settlement_boundary",
            "question": "実決済まで扱う？",
            "why": "権限と安全境界が変わる。",
            "affects": ["scope", "privacy", "authority"],
            "answer_shape": "no real payment; payment link only; full payment flow",
            "priority": "must_ask",
        }
    ],
    "spec_outline": [
        {
            "id": "target_audience",
            "title": "対象利用者",
            "known": ["幹事の可能性"],
            "missing": ["主利用者"],
            "required": True,
        }
    ],
    "non_decisions": ["does not approve implementation"],
    "limits": ["input text only"],
}


class RequestExplorationReviewTests(unittest.TestCase):
    def test_schema_file_loads(self) -> None:
        schema = load_request_exploration_review_schema()

        self.assertEqual(schema["title"], "semantic-guard request exploration review")
        self.assertIn("questions", schema["required"])

    def test_validate_accepts_minimum_valid_exploration(self) -> None:
        self.assertEqual(validate_request_exploration_review(VALID_EXPLORATION), [])

    def test_validate_rejects_bad_enum_and_extra_field(self) -> None:
        payload = dict(VALID_EXPLORATION)
        payload["exploration_status"] = "approved"
        payload["decision"] = "accept"

        errors = validate_request_exploration_review(payload)

        self.assertIn("unexpected field: decision", errors)
        self.assertIn("exploration_status must be one of complete, blocked_by_missing_context", errors)

    def test_prompt_builds_interviewer_boundary(self) -> None:
        prompt = build_request_exploration_prompt(
            RequestExplorationInput(text="割り勘アプリを作りたい", deterministic_exploration={"phase": "explore_request"})
        )

        self.assertIn("request_exploration_interviewer", prompt)
        self.assertIn("取れる情報をすべて拾い", prompt)
        self.assertIn("仕様、実装計画、承認、棄却、最終受入判断をしてはならない", prompt)


if __name__ == "__main__":
    unittest.main()
