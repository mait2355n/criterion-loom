from __future__ import annotations

import json
import unittest

from semantic_guard.acceptance_review import (
    ACCEPTANCE_BUNDLE_VERSION,
    build_acceptance_review_bundle_template,
    load_acceptance_review_bundle_schema,
    validate_acceptance_review_bundle,
)


def _valid_bundle() -> dict[str, object]:
    return build_acceptance_review_bundle_template(
        {
            "original_request": "codex exec reviewer adapter を実装し、最終人間監査bundleを作る。",
            "final_artifact": {
                "kind": "code",
                "reference": "src/semantic_guard/acceptance_review.py",
                "summary": "acceptance_review_bundle の生成と検証を追加した。",
            },
            "deterministic_audits": [
                {
                    "phase": "finish_check",
                    "status": "pass",
                    "summary": "試験と実行証拠が揃っている。",
                    "findings": [],
                }
            ],
            "llm_reviews": [
                {
                    "source": "codex_exec",
                    "valid": True,
                    "review_status": "needs_supplement",
                    "missing_aspects": [{"kind": "evidence", "severity": "minor"}],
                    "supplement_proposals": [{"target": "docs", "proposal": "制限を追記する。"}],
                    "rule_item_reviews": [{"rule_id": "finish.evidence.acceptance_missing"}],
                    "human_decision_needed": ["公開できる完成度か。"],
                }
            ],
            "adopted_supplements": [
                {
                    "source": "codex_exec",
                    "target": "docs",
                    "supplement": "制限を追記した。",
                    "reason": "最終判断材料に必要。",
                    "evidence": "docs/llm-reviewer.md",
                }
            ],
            "rejected_supplements": [
                {
                    "source": "codex_exec",
                    "target": "runtime",
                    "supplement": "自動承認を追加する。",
                    "reason": "LLMに最終合否を渡さないため。",
                    "evidence": "",
                }
            ],
            "deferred_supplements": [
                {
                    "source": "human",
                    "target": "release",
                    "supplement": "公開前のREADME polish。",
                    "reason": "機能完成とは別の公開品質判断。",
                    "decision_needed": "公開前に実施するか。",
                }
            ],
            "execution_evidence": [
                {
                    "kind": "test",
                    "command_or_reference": "python -m unittest discover -s tests -v",
                    "result": "OK",
                    "passed": True,
                }
            ],
            "residual_risks": [
                {
                    "risk": "LLM査読は意味的に誤る可能性がある。",
                    "severity": "minor",
                    "mitigation": "最終判断は人が行う。",
                    "owner": "human",
                }
            ],
            "human_review_points": [
                {
                    "question": "この成果物を受け入れるか。",
                    "why_it_matters": "最終合否は人が決めるため。",
                    "options": ["accept", "request_revision", "defer"],
                }
            ],
        }
    )


class AcceptanceReviewTests(unittest.TestCase):
    def test_schema_loads(self) -> None:
        schema = load_acceptance_review_bundle_schema()

        self.assertEqual(schema["properties"]["schema_version"]["const"], ACCEPTANCE_BUNDLE_VERSION)
        self.assertIn("final_human_decision", schema["required"])
        self.assertIn("request_revision", schema["properties"]["final_human_decision"]["properties"]["status"]["enum"])

    def test_template_builds_pending_human_decision(self) -> None:
        bundle = build_acceptance_review_bundle_template(
            {
                "request": "最終評価bundleが欲しい。",
                "final_artifact": {"kind": "document", "reference": "README.md", "summary": "説明を更新した。"},
            }
        )

        self.assertEqual(bundle["schema_version"], ACCEPTANCE_BUNDLE_VERSION)
        self.assertEqual(bundle["original_request"], "最終評価bundleが欲しい。")
        self.assertEqual(bundle["final_human_decision"]["status"], "pending")
        json.dumps(bundle, ensure_ascii=False)

    def test_validate_accepts_ready_bundle(self) -> None:
        self.assertEqual(validate_acceptance_review_bundle(_valid_bundle()), [])

    def test_validate_no_strict_accepts_scaffold(self) -> None:
        bundle = build_acceptance_review_bundle_template(
            {
                "original_request": "要求",
                "final_artifact": {"kind": "document", "reference": "", "summary": "成果物"},
            }
        )

        self.assertEqual(validate_acceptance_review_bundle(bundle, strict=False), [])

    def test_validate_strict_rejects_missing_final_review_material(self) -> None:
        bundle = build_acceptance_review_bundle_template(
            {
                "original_request": "要求",
                "final_artifact": {"kind": "document", "reference": "", "summary": "成果物"},
            }
        )

        errors = validate_acceptance_review_bundle(bundle)

        self.assertIn("deterministic_audits must include at least one audit in strict mode", errors)
        self.assertIn("execution_evidence must include at least one evidence item in strict mode", errors)
        self.assertIn("human_review_points must include at least one question in strict mode", errors)

    def test_validate_rejects_llm_decision_field(self) -> None:
        bundle = _valid_bundle()
        bundle["llm_reviews"][0]["approved"] = True  # type: ignore[index]

        errors = validate_acceptance_review_bundle(bundle)

        self.assertTrue(any("approved" in error for error in errors))

    def test_validate_requires_human_rationale_after_decision(self) -> None:
        bundle = _valid_bundle()
        bundle["final_human_decision"] = {"status": "accept", "decided_by": "", "decided_at": "", "rationale": ""}

        errors = validate_acceptance_review_bundle(bundle)

        self.assertTrue(any("final_human_decision.decided_by" in error for error in errors))
        self.assertTrue(any("final_human_decision.decided_at" in error for error in errors))
        self.assertTrue(any("final_human_decision.rationale" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
