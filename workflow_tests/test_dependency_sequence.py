from __future__ import annotations

from pathlib import Path
import unittest

from semantic_guard_workflow.plan_audit import audit_plan


GOOD_PLAN = Path(__file__).parent / "fixtures" / "plans" / "good.md"
SEQUENCE_RULE = "plan.schedule.dependency_sequence_missing"


def plan_with_sequence(sequence: str) -> str:
    lines = GOOD_PLAN.read_text(encoding="utf-8").splitlines()
    assert sum(line.startswith("順序:") for line in lines) == 1
    return "\n".join(sequence if line.startswith("順序:") else line for line in lines)


class DependencySequenceAssertionTests(unittest.TestCase):
    def test_markdown_wrapped_deferred_sequence_does_not_satisfy_the_obligation(self) -> None:
        for prefix in ("- ", "* ", "+ ", "> ", ">> ", "# ", "## ", "1) ", "1. ", "> - ## ", "- > ## "):
            for deferred in ("順序は後で決める。", "その順序は未定。"):
                sequence = prefix + deferred
                with self.subTest(sequence=sequence):
                    result = audit_plan(plan_with_sequence(sequence))

                    self.assertIn("dependency_sequence", result["missing"])
                    self.assertIn(SEQUENCE_RULE, {finding["rule_id"] for finding in result["findings"]})
                    self.assertEqual(result["details"]["planning_structure"]["dependency_sequence"], "")

    def test_markdown_wrapped_concrete_order_preserves_original_evidence(self) -> None:
        for prefix in ("- ", "* ", "+ ", "> ", ">> ", "# ", "## ", "1) ", "1. ", "> - ## ", "- > ## "):
            for concrete in ("順序はAの後でBを行う。", "設計を先に終え、その後で試験する。"):
                sequence = prefix + concrete
                with self.subTest(sequence=sequence):
                    result = audit_plan(plan_with_sequence(sequence))

                    self.assertNotIn("dependency_sequence", result["missing"])
                    self.assertNotIn(SEQUENCE_RULE, {finding["rule_id"] for finding in result["findings"]})
                    self.assertEqual(result["details"]["planning_structure"]["dependency_sequence"], sequence)

    def test_deferred_sequence_does_not_satisfy_the_obligation(self) -> None:
        for sequence in (
            "順序: 後で決める。",
            "順序: 未定。",
            "dependency sequence: TBD.",
            "順序は後で決める。",
            "その順序は未定。",
            "順序を別途定める予定。",
            "後で決める。",
            "後で決める予定。",
        ):
            with self.subTest(sequence=sequence):
                result = audit_plan(plan_with_sequence(sequence))

                self.assertIn("dependency_sequence", result["missing"])
                self.assertIn(SEQUENCE_RULE, {finding["rule_id"] for finding in result["findings"]})
                self.assertEqual(result["details"]["planning_structure"]["dependency_sequence"], "")

    def test_concrete_order_is_preserved(self) -> None:
        for sequence in (
            "順序: Aの後でBを行う。",
            "順序: Aの後にBを行う。",
            "dependency sequence: Run B after A.",
            "Run B after A.",
            "設計を先に終え、その後で試験する。",
            "Aの後でBを行う。",
            "順序はAの後でBを行い、Cの順序は未定。",
            "順序は後で決めるが、Aの後にBを行う。",
        ):
            with self.subTest(sequence=sequence):
                result = audit_plan(plan_with_sequence(sequence))

                self.assertNotIn("dependency_sequence", result["missing"])
                self.assertNotIn(SEQUENCE_RULE, {finding["rule_id"] for finding in result["findings"]})
                self.assertEqual(result["details"]["planning_structure"]["dependency_sequence"], sequence)

    def test_current_concrete_order_wins_over_a_deferred_statement(self) -> None:
        current = "順序: Aの後にBを行う。"
        for deferred in (
            "順序: 後で決める。",
            "順序は後で決める。",
            "その順序は未定。",
            "順序を別途定める予定。",
        ):
            with self.subTest(deferred=deferred):
                result = audit_plan(plan_with_sequence(f"{deferred}\n{current}"))

                self.assertNotIn("dependency_sequence", result["missing"])
                self.assertEqual(result["details"]["planning_structure"]["dependency_sequence"], current)

    def test_deferred_clause_does_not_remove_a_following_concrete_sentence(self) -> None:
        current = "Run B after A."
        for separator in ("。", ". ", "; ", "\n"):
            with self.subTest(separator=separator):
                sequence = f"順序は後で決める{separator}{current}"
                result = audit_plan(plan_with_sequence(sequence))

                self.assertNotIn("dependency_sequence", result["missing"])
                evidence = result["details"]["planning_structure"]["dependency_sequence"]
                self.assertIn(current, evidence)
                self.assertNotIn("後で決める", evidence)


if __name__ == "__main__":
    unittest.main()
