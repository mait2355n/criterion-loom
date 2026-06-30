from __future__ import annotations

import json
import subprocess
import unittest

from semantic_guard.escalation import decide_escalation, review_if_needed
from semantic_guard.llm_review import SCHEMA_VERSION


def _uncertain_audit() -> dict[str, object]:
    return {
        "phase": "audit_plan",
        "status": "warn",
        "score": 0.82,
        "findings": [
            {
                "severity": "major",
                "category": "planning",
                "finding": "計画に `verification_plan` が見えない。",
                "warning_class": "possible false positive",
                "nearest_candidates": ["点検方針: 人間が画面を見る。"],
            }
        ],
        "missing": ["verification_plan"],
        "details": {},
    }


def _valid_review() -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "review_status": "needs_supplement",
        "missing_aspects": [
            {
                "kind": "verification_plan",
                "severity": "major",
                "why_it_matters": "点検方針が検証として十分か判断が必要。",
                "supplement": "検証方法、判断主体、成功条件を補う。",
            }
        ],
        "questionable_assumptions": [],
        "possible_counter_conditions": [
            {
                "rule_id": "plan.validation.problem_fit_missing",
                "does_not_apply_when": "既に別欄で検証方法が十分に明記されている。",
                "confidence": "medium",
                "reason": "近傍候補が存在するため。",
            }
        ],
        "supplement_proposals": [],
        "rule_item_reviews": [],
        "human_decision_needed": [],
    }


class EscalationTests(unittest.TestCase):
    def test_decide_escalation_marks_possible_false_positive(self) -> None:
        decision = decide_escalation(
            candidate="計画本文",
            phase="audit_plan",
            deterministic_audit=_uncertain_audit(),
        )

        self.assertTrue(decision["needed"])
        self.assertEqual(decision["mode"], "dry_run")
        self.assertIn("possible_false_positive", decision["reasons"])
        self.assertIn("major_or_blocking_gap_has_candidate", decision["reasons"])
        self.assertEqual(decision["target"], "candidate_gap_reviewer")
        self.assertEqual(decision["pressure"]["score_semantics"], "review routing pressure; not correctness probability")
        self.assertGreater(decision["pressure"]["score"], 0)
        self.assertIn("countercondition_plausibility", decision["dimensions"])
        self.assertTrue(decision["signals"])
        self.assertIn("does_not_clear_deterministic_findings", decision["non_decisions"])
        self.assertEqual(decision["payload"]["phase"], "audit_plan")

    def test_review_if_needed_skips_passed_audit(self) -> None:
        result = review_if_needed(
            {
                "candidate": "計画本文",
                "phase": "audit_plan",
                "deterministic_audit": {"phase": "audit_plan", "status": "pass", "score": 1.0, "findings": []},
            }
        )

        self.assertFalse(result["escalation"]["needed"])
        self.assertIsNone(result["review_result"])
        self.assertEqual(result["escalation"]["pressure"]["level"], "none")
        self.assertEqual(result["escalation"]["signals"], [])

    def test_decide_escalation_uses_structured_match_diagnostics(self) -> None:
        decision = decide_escalation(
            candidate="差分本文",
            phase="audit_diff",
            deterministic_audit={
                "phase": "audit_diff",
                "status": "warn",
                "score": 0.86,
                "findings": [
                    {
                        "severity": "major",
                        "category": "security",
                        "finding": "安全性に関わる差分の可能性がある。",
                        "warning_class": "generic caution",
                        "match_status": "unknown",
                        "confidence": "low",
                        "ambiguity_reasons": ["high_impact_low_specificity"],
                    }
                ],
            },
        )

        self.assertTrue(decision["needed"])
        self.assertIn("unknown_match_status", decision["reasons"])
        self.assertIn("high_impact_low_confidence", decision["reasons"])
        self.assertIn("structured_ambiguity_reason", decision["reasons"])
        self.assertEqual(decision["dimensions"]["uncertainty"], "high")

    def test_clear_missing_without_candidate_does_not_escalate_to_llm(self) -> None:
        decision = decide_escalation(
            candidate="要求本文",
            phase="audit_request",
            deterministic_audit={
                "phase": "audit_request",
                "status": "block",
                "score": 0.55,
                "findings": [
                    {
                        "severity": "blocker",
                        "category": "verifiability",
                        "finding": "要求の達成確認方法が見えない。",
                        "warning_class": "actionable",
                        "match_status": "missing",
                        "confidence": "high",
                    }
                ],
                "missing": ["verification_or_acceptance"],
            },
        )

        self.assertFalse(decision["needed"])
        self.assertEqual(decision["reasons"], [])
        self.assertEqual(decision["pressure"]["score"], 0)
        self.assertEqual(decision["pressure"]["level"], "none")

    def test_fresh_eyes_context_can_request_independent_review_for_passed_audit(self) -> None:
        result = review_if_needed(
            {
                "candidate": "公開文書を更新し、試験を実行した。",
                "phase": "finish_check",
                "deterministic_audit": {"phase": "finish_check", "status": "pass", "score": 1.0, "findings": []},
                "review_context": {
                    "independent_review_requested": True,
                    "self_reviewed": True,
                    "public_release": True,
                    "changed_files_count": 12,
                },
                "non_goals": "合否決定はしない。",
            }
        )

        escalation = result["escalation"]
        self.assertTrue(escalation["needed"])
        self.assertIn("independent_review_requested", escalation["reasons"])
        self.assertIn("context_contamination_risk", escalation["reasons"])
        self.assertEqual(escalation["dimensions"]["independent_review_value"], "medium")
        self.assertGreaterEqual(escalation["pressure"]["score"], 60)
        self.assertFalse(result["review_result"]["executed"])
        self.assertEqual(result["review_result"]["execution_status"], "dry_run")
        self.assertIn("routing_assessment", result["review_result"]["prompt"])
        self.assertIn("review routing pressure; not correctness probability", result["review_result"]["prompt"])

    def test_problem_solution_structure_can_escalate_passed_audit(self) -> None:
        result = review_if_needed(
            {
                "candidate": "問題: import が止まる。解決策: retry 回数を増やす。受入基準: import が止まらない。",
                "phase": "audit_request",
                "deterministic_audit": {"phase": "audit_request", "status": "pass", "score": 1.0, "findings": []},
            }
        )

        escalation = result["escalation"]
        self.assertTrue(escalation["needed"])
        self.assertIn("candidate_mechanism_fit_unclear", escalation["reasons"])
        self.assertIn("candidate_symptom_suppression_risk", escalation["reasons"])
        self.assertEqual(escalation["dimensions"]["mechanism_fit_uncertainty"], "high")
        self.assertFalse(result["review_result"]["executed"])
        self.assertIn("problem-solution fit", result["review_result"]["prompt"])

    def test_problem_mechanism_rule_escalates_for_supplement_review(self) -> None:
        result = review_if_needed(
            {
                "candidate": "要求本文",
                "phase": "audit_request",
                "deterministic_audit": {
                    "phase": "audit_request",
                    "status": "warn",
                    "score": 0.8,
                    "findings": [
                        {
                            "severity": "major",
                            "category": "solution_fit",
                            "rule_id": "req.solution.problem_mechanism_fit_missing",
                            "finding": "解決策が問題の原因構造または発生機構へどう作用するかが見えない。",
                            "warning_class": "generic caution",
                        }
                    ],
                },
            }
        )

        self.assertTrue(result["escalation"]["needed"])
        self.assertIn("problem_mechanism_fit_gap", result["escalation"]["reasons"])

    def test_review_if_needed_dry_run_builds_exec_review(self) -> None:
        result = review_if_needed(
            {
                "candidate": "計画本文",
                "phase": "audit_plan",
                "deterministic_audit": _uncertain_audit(),
                "non_goals": "合否決定はしない。",
            }
        )

        self.assertTrue(result["escalation"]["needed"])
        self.assertFalse(result["review_result"]["executed"])
        self.assertEqual(result["review_result"]["execution_status"], "dry_run")
        self.assertIn("codex", result["review_result"]["command"])
        self.assertIn("candidate_gap_reviewer", result["review_result"]["prompt"])

    def test_review_if_needed_reports_input_error_before_execution(self) -> None:
        result = review_if_needed(
            {
                "phase": "audit_plan",
                "deterministic_audit": _uncertain_audit(),
            },
            execute=True,
        )

        self.assertTrue(result["escalation"]["needed"])
        self.assertEqual(result["review_result"]["execution_status"], "input_error")
        self.assertFalse(result["review_result"]["executed"])
        self.assertFalse(result["review_result"]["valid"])
        self.assertIn("`candidate` must be a non-empty string", result["review_result"]["errors"])

    def test_review_if_needed_execute_uses_runner_only_when_needed(self) -> None:
        calls: list[dict[str, object]] = []

        def runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            calls.append({"command": command, **kwargs})
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps(_valid_review()), stderr="")

        result = review_if_needed(
            {
                "candidate": "計画本文",
                "phase": "audit_plan",
                "deterministic_audit": _uncertain_audit(),
            },
            execute=True,
            runner=runner,
        )

        self.assertTrue(result["review_result"]["executed"])
        self.assertTrue(result["review_result"]["valid"])
        self.assertEqual(len(calls), 1)
        self.assertIn("candidate_gap_reviewer", str(calls[0]["input"]))


if __name__ == "__main__":
    unittest.main()
