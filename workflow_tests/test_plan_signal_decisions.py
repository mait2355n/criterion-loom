"""Planning structure signals count stated decisions, not postponed labels."""

from __future__ import annotations

import unittest

from semantic_guard_workflow.plan_audit import audit_plan

BASE = "目的: 設定読込を直す。\n対象外: UI は変えない。\n手順: 調査、実装、検証。\n順序: 先に調査、次に実装。\nリスク: 互換性が崩れる恐れがある。\n"


def structure(extra: str) -> dict[str, str]:
    return audit_plan(BASE + extra)["details"]["planning_structure"]  # type: ignore[index]


class PlanSignalDecisionTests(unittest.TestCase):
    def test_an_explicit_order_retraction_cancels_an_earlier_unlabelled_order(self) -> None:
        for concrete in ("A→B。", "Aの後でBを行う。"):
            for deferred in ("順序: 未定。", "順序は後で決める。", "改訂: 順序は撤回し、後で決める。"):
                with self.subTest(concrete=concrete, deferred=deferred):
                    plan = BASE.replace("順序: 先に調査、次に実装。", concrete + "\n" + deferred)
                    result = audit_plan(plan)
                    self.assertEqual(result["details"]["planning_structure"]["dependency_sequence"], "")
                    self.assertIn("dependency_sequence", result["missing"])

    def test_a_later_concrete_order_and_a_deferred_detail_keep_their_meaning(self) -> None:
        for sequence in ("順序: 未定。\nA→B。", "A→B。順序の詳細は後で決める。"):
            with self.subTest(sequence=sequence):
                plan = BASE.replace("順序: 先に調査、次に実装。", sequence)
                result = audit_plan(plan)
                self.assertNotIn("dependency_sequence", result["missing"])
                self.assertEqual(result["details"]["planning_structure"]["dependency_sequence"], "A→B。")

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


class QualitySignalDecisionTests(unittest.TestCase):
    """A one-line postponement must not clear a quality signal, whatever the signal is."""

    MIGRATION = "目的: 複数の設定を移行する。\n対象外: UI。\n成果物: 設定一覧、移行手順、検証結果。\n手順: 設計、実装、検証。\n"
    CASES = (
        ("progress_control", MIGRATION, "進捗: {v}", "進捗: 毎日の確認点で報告する。"),
        ("change_control", MIGRATION, "{v}", "変更管理: 差分は承認してから反映する。"),
        ("validation_owner", MIGRATION + "受入基準: 満たすこと。\n", "判断主体: {v}", "判断主体: 保守者が受入を判断する。"),
        ("release_provenance", "目的: 公開する。\n対象外: UI。\n", "版: {v}", "版: タグ v1.2 と署名付き成果物を残す。"),
        ("idempotency", "目的: 同期ジョブを再試行して通知を送信する。\n対象外: UI。\n", "冪等性: {v}", "冪等性: 再送しても重複通知を送らないよう識別子で判定する。"),
    )

    def signals(self, plan: str) -> dict[str, object]:
        return audit_plan(plan)["details"]["planning_signals"]  # type: ignore[return-value]

    def test_a_postponed_value_leaves_the_signal_raised(self) -> None:
        for key, trigger, template, _ in self.CASES:
            self.assertIn(key, self.signals(trigger), f"{key}: the trigger plan must raise it")
            for value in ("未定", "後で決める", "TBD", "検討中", "保留"):
                with self.subTest(key=key, value=value):
                    self.assertIn(key, self.signals(trigger + template.format(v=value) + "\n"))

    def test_a_stated_value_clears_the_signal(self) -> None:
        for key, trigger, _, stated in self.CASES:
            with self.subTest(key=key):
                self.assertNotIn(key, self.signals(trigger + stated + "\n"))


if __name__ == "__main__":
    unittest.main()
