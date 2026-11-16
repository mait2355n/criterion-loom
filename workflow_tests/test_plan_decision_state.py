"""A plan field is satisfied by a decision, not by its label."""

from __future__ import annotations

from pathlib import Path
import unittest

from semantic_guard_workflow.plan_audit import audit_plan

GOOD_PLAN = Path(__file__).parent / "fixtures" / "plans" / "good.md"
PLACEHOLDERS = ("後で決める。", "未定。", "TBD。", "検討中。", "要検討。", "調整中。", "別途。", "")

# Few generic words, so that one label is the only mention of its field.
MINIMAL_PLAN = """目的: 設定読込を直す。
対象外: UI は変えない。
成果物: config.py の修正。
手順: 読込処理を直す。
順序: 先に読込、次に検証。
依存: 標準ライブラリのみ。
リスク: 互換性が崩れる。部分適用で抑える。
{verification}
妥当性: 目的に合うか保守者が見る。
{rollback}
{evidence}
未確定: なし。
"""
VERIFICATION = "検証: pytest を実行する。"
ROLLBACK = "戻し方: 差分を戻す。"
EVIDENCE = "証拠: 実行結果を残す。"


def minimal(verification: str = VERIFICATION, rollback: str = ROLLBACK, evidence: str = EVIDENCE) -> dict[str, object]:
    return audit_plan(MINIMAL_PLAN.format(verification=verification, rollback=rollback, evidence=evidence))


class PlanDecisionStateTests(unittest.TestCase):
    def test_the_good_plan_and_the_minimal_plan_still_satisfy_their_fields(self) -> None:
        result = audit_plan(GOOD_PLAN.read_text(encoding="utf-8"))

        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["findings"], [])
        for field in ("verification_plan", "rollback_or_recovery", "completion_evidence", "objective", "non_goals"):
            self.assertNotIn(field, minimal()["missing"])

    def test_a_plan_whose_every_value_is_postponed_does_not_pass(self) -> None:
        labels = [line.split(":")[0] for line in GOOD_PLAN.read_text(encoding="utf-8").splitlines()]
        for placeholder in PLACEHOLDERS:
            with self.subTest(placeholder=placeholder):
                result = audit_plan("\n".join(f"{label}: {placeholder}" for label in labels))

                self.assertNotEqual(result["status"], "pass")
                self.assertIn("objective", result["missing"])
                self.assertIn("verification_plan", result["missing"])
                self.assertIn("completion_evidence", result["missing"])

    def test_postponed_or_refused_values_do_not_satisfy_the_field(self) -> None:
        cases = {
            "verification_plan": ("verification", ("検証: 実施しない。", "検証: 行わない。", "検証: 後で決める。", "検証: なし。", "**検証**: 未定", "| 検証 | TBD |", "## 検証\n検討中")),
            "rollback_or_recovery": ("rollback", ("戻し方: 戻さない。", "戻し方: 後で決める。", "戻し方: 未定", "戻し方: なし。")),
            "completion_evidence": ("evidence", ("証拠: 残さない。", "証拠: 未定。", "証拠: TBD", "証拠: なし。")),
        }
        for field, (argument, values) in cases.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    self.assertIn(field, minimal(**{argument: value})["missing"])

    def test_nothing_is_an_answer_only_where_nothing_is_a_real_answer(self) -> None:
        for value in ("対象外: なし。", "対象外: 該当なし。"):
            with self.subTest(value=value):
                result = audit_plan(MINIMAL_PLAN.replace("対象外: UI は変えない。", value).format(
                    verification=VERIFICATION, rollback=ROLLBACK, evidence=EVIDENCE))
                self.assertNotIn("non_goals", result["missing"])
        for line in ("未確定: なし。", "未確定: 該当なし。"):
            result = audit_plan(MINIMAL_PLAN.replace("未確定: なし。", line).format(
                verification=VERIFICATION, rollback=ROLLBACK, evidence=EVIDENCE))
            self.assertNotIn("unknowns_or_decisions", result["missing"])
        # ...but "nothing" is not a verification plan, a rollback path, or an objective.
        self.assertIn("verification_plan", minimal(verification="検証: 該当なし。")["missing"])
        self.assertIn("objective", audit_plan("目的: なし。\n対象外: なし。")["missing"])

    def test_a_deferred_non_goals_or_unknowns_label_is_still_missing(self) -> None:
        for label, field in (("対象外", "non_goals"), ("未確定", "unknowns_or_decisions")):
            with self.subTest(label=label):
                text = MINIMAL_PLAN.format(verification=VERIFICATION, rollback=ROLLBACK, evidence=EVIDENCE)
                text = "\n".join(f"{label}: 後で決める。" if line.startswith(f"{label}:") else line for line in text.splitlines())
                self.assertIn(field, audit_plan(text)["missing"])


if __name__ == "__main__":
    unittest.main()
