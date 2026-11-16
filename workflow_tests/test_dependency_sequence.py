from __future__ import annotations

from pathlib import Path
import time
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

    def test_deferral_and_back_reference_sentences_do_not_state_an_order(self) -> None:
        for sequence in (
            "期限は後で決める。",
            "担当者は後で決める。",
            "予算は後で見積もる。",
            "ログは後で確認する。",
            "先に述べた通り範囲は限定する。",
            "後で検討する。",
            "依存: 後で決める。",
            "依存: 未定。",
            "以前に説明した。",
            "外部依存なし。",
        ):
            with self.subTest(sequence=sequence):
                result = audit_plan(plan_with_sequence(sequence))

                self.assertIn("dependency_sequence", result["missing"])
                self.assertIn(SEQUENCE_RULE, {finding["rule_id"] for finding in result["findings"]})

    def test_order_constructs_state_an_order_without_a_label(self) -> None:
        for sequence in (
            "設計を先に終え、その後で試験する。",
            "Aの後でBを行う。",
            "依存: Aの後でB",
            "順序: A→B→C",
            "まずAを実装し、次にBを行う。",
            "Aを終えてから試験する。",
            "公開前に確認する。",
            "完了次第Bを始める。",
            "Aを先に実装し、Bを後で追加する。",
            "Bは A に depends on",
            "Run A, then B.",
        ):
            with self.subTest(sequence=sequence):
                result = audit_plan(plan_with_sequence(sequence))

                self.assertNotIn("dependency_sequence", result["missing"])
                self.assertEqual(result["details"]["planning_structure"]["dependency_sequence"], sequence)

    def test_long_whitespace_runs_are_linear(self) -> None:
        for body in ("順序: x" + " " * 100_000, "順序:" + " " * 100_000 + "x", "順序: x" + " \t" * 50_000):
            with self.subTest(length=len(body)):
                started = time.perf_counter()
                audit_plan(plan_with_sequence(body))
                # Linear time costs a few tenths of a second at this size; the quadratic
                # relation match this guards against took tens of seconds.
                self.assertLess(time.perf_counter() - started, 2.0)


class SequenceStatementTests(unittest.TestCase):
    PLAN = (
        "目的: 退行検出を作る。\n対象外: 大規模改変はしない。\n手順: 形式設計、fixture 追加、実装、検証、文書化。\n"
        "{order}\n検証: unittest を実行する。\n妥当性: 保守者が確認する。\n判断主体: 保守者が受入を判断する。\n"
        "戻し方: 差分を戻す。\n証拠: 結果を残す。\n"
    )

    def missing(self, order: str, **options: str) -> bool:
        return "dependency_sequence" in audit_plan(self.PLAN.format(order=order), **options)["missing"]

    def evidence(self, order: str) -> str:
        return audit_plan(self.PLAN.format(order=order))["details"]["planning_structure"]["dependency_sequence"]

    def test_every_way_of_saying_the_order_is_undecided_leaves_it_missing(self) -> None:
        for value in (
            "未決", "後日決定", "今後検討", "決まっていない", "順番は未定", "決まり次第記載する",
            "設計が終わった後で決める", "撤回し、後で決める", "別途協議", "決定次第追記する",
        ):
            with self.subTest(value=value):
                self.assertTrue(self.missing(f"順序: {value}"))
                self.assertTrue(self.missing(f"順序は{value}。"))

    def test_the_request_and_the_context_do_not_decide_an_order_the_plan_leaves_open(self) -> None:
        for options in (
            {"request": "Release the report after approval by the reviewer."},
            {"context": "Previously: tests run before merge."},
            {"request": "Aの後でBを行う。", "context": "順序: Bの後でC"},
        ):
            with self.subTest(options=options):
                self.assertTrue(self.missing("順序は後で決める。", **options))

    def test_the_request_still_fills_an_order_the_plan_does_not_state(self) -> None:
        plan = self.PLAN.format(order="")
        self.assertIn("dependency_sequence", audit_plan(plan)["missing"])
        self.assertNotIn("dependency_sequence", audit_plan(plan, request="Run B after A.")["missing"])

    def test_the_last_statement_of_the_order_stands(self) -> None:
        retracted = (
            "順序: Aの後にBを行う。\n順序: 後で決める。",
            "順序: Aの後にBを行う。\n改訂: 順序は撤回し、後で決める。",
        )
        for order in retracted:
            with self.subTest(order=order):
                self.assertTrue(self.missing(order))
        self.assertFalse(self.missing("順序: 後で決める。\n順序: Aの後にBを行う。"))
        # A concrete order stated as a sentence is not retracted by a deferred detail elsewhere.
        self.assertFalse(self.missing("Aの後でBを行う。順序の詳細は後で決める。"))

    def test_contradictory_concrete_orders_are_not_compared(self) -> None:
        self.assertFalse(self.missing("順序: Aの後にB。\n順序: Bの後にA。"))

    def test_evidence_is_a_piece_of_the_input(self) -> None:
        order = "Aの後でB。順序は未定。Cの後でD"
        evidence = self.evidence(order)

        self.assertTrue(evidence)
        self.assertIn(evidence, self.PLAN.format(order=order))
        self.assertNotIn("未定", evidence)

    def test_deliverables_count_the_same_under_a_heading(self) -> None:
        from semantic_guard_workflow.plan_audit import _deliverable_item_count

        head = "目的: 調査報告を作る。\n手順: 調査、執筆、校正。\n"
        for deliverables in (
            "成果物: report.md、summary.md、notes.md",
            "成果物:\n- report.md\n- summary.md\n- notes.md",
            "## 成果物\n- report.md\n- summary.md\n- notes.md",
        ):
            with self.subTest(deliverables=deliverables):
                self.assertEqual(_deliverable_item_count(head + deliverables + "\n検証: 確認する。\n"), 3)


if __name__ == "__main__":
    unittest.main()
