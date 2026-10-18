"""Planning structure signals count stated decisions, not postponed labels."""

from __future__ import annotations

import unittest

from semantic_guard_workflow.plan_audit import audit_plan

BASE = "目的: 設定読込を直す。\n対象外: UI は変えない。\n手順: 調査、実装、検証。\n順序: 先に調査、次に実装。\nリスク: 互換性が崩れる恐れがある。\n"


def structure(extra: str) -> dict[str, str]:
    return audit_plan(BASE + extra)["details"]["planning_structure"]  # type: ignore[index]


class PlanSignalDecisionTests(unittest.TestCase):
    def test_a_stated_risk_response_counts(self) -> None:
        for line in ("対策: 部分適用で抑える。", "緩和: 段階的に切り替える。", "Mitigation: roll out by stage."):
            with self.subTest(line=line):
                self.assertTrue(structure(line)["risk_response"])

    def test_a_postponed_risk_response_does_not(self) -> None:
        for line in ("対策: 後で決める。", "対応: 未定。", "緩和: TBD", "対策: 保留", "リスク対応: 検討中", "保留。", "Mitigation: TBD."):
            with self.subTest(line=line):
                result = audit_plan(BASE + line)
                self.assertEqual(result["details"]["planning_structure"]["risk_response"], "")
                self.assertIn("plan.risk.response_missing", {f.get("rule_id") for f in result["findings"]})

    def test_postponed_resource_gate_and_baseline_labels_do_not_count(self) -> None:
        for label, key in (("資源", "estimation_or_resource_basis"), ("決定点", "decision_gate"), ("基準線", "control_baseline")):
            for value in ("後で決める。", "未定。", "TBD。"):
                with self.subTest(label=label, value=value):
                    self.assertEqual(structure(f"{label}: {value}")[key], "")

    def test_stated_resource_gate_and_baseline_labels_count(self) -> None:
        for label, value, key in (
            ("資源", "Codex が一作業単位で実施する。", "estimation_or_resource_basis"),
            ("決定点", "公開前に保守者が承認する。", "decision_gate"),
            ("基準線", "既存 API の出力を判定基準にする。", "control_baseline"),
        ):
            with self.subTest(label=label):
                self.assertTrue(structure(f"{label}: {value}")[key])

    def test_inflected_english_terms_still_match(self) -> None:
        plan = "Objective: fix.\nRisks And Responses: breakage is limited by optional fields.\n"

        self.assertTrue(audit_plan(plan)["details"]["planning_structure"]["risk_response"])


if __name__ == "__main__":
    unittest.main()
