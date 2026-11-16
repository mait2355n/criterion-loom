"""A broad rewrite is bounded by stated controls, and the rules never contradict."""

from __future__ import annotations

import unittest

from semantic_guard_workflow.plan_audit import audit_plan

BROAD = "plan.scope.broad_scope_unbounded"
SEQUENCE = "plan.schedule.dependency_sequence_missing"
BOUNDED = (
    "目的: 全体を段階的に書き換える。\n"
    "作業分解: 段階1 は設定、段階2 は読込。\n"
    "成果物: config.py。\n"
    "対象外: UI は変えない。\n"
    "順序: 段階1 の後に段階2 を行う。\n"
    "検証: pytest を実行する。\n"
)
PLACEHOLDERS = ("後で決める。", "未定。", "TBD。", "検討中。", "別途。", "実施しない。", "なし。", "")


def outcome(plan: str) -> tuple[set[str], set[str]]:
    result = audit_plan(plan)
    emitted = {str(finding.get("rule_id")) for finding in result["findings"]}
    suppressed = {str(trace["rule_id"]) for trace in result["details"]["non_emitted_rules"]}
    return emitted, suppressed


class BroadScopeGuardrailTests(unittest.TestCase):
    def test_a_plan_with_every_control_stated_is_bounded(self) -> None:
        emitted, suppressed = outcome(BOUNDED)

        self.assertNotIn(BROAD, emitted)
        self.assertIn(BROAD, suppressed)

    def test_postponed_controls_do_not_bound_a_broad_rewrite(self) -> None:
        for placeholder in PLACEHOLDERS:
            with self.subTest(placeholder=placeholder):
                emitted, suppressed = outcome(f"目的: 全体を書き換える。\n進め方: {placeholder}\n")
                self.assertIn(BROAD, emitted)
                self.assertNotIn(BROAD, suppressed)

    def test_every_placeholder_is_treated_alike(self) -> None:
        # ``進め方: 後で決める`` used to suppress the finding while ``未定`` did not.
        flags = {
            placeholder: (BROAD in outcome(f"目的: 全体を書き換える。\n進め方: {placeholder}\n")[0])
            for placeholder in PLACEHOLDERS
        }

        self.assertEqual(set(flags.values()), {True}, flags)

    def test_each_single_label_control_must_be_stated_for_the_rewrite_to_be_bounded(self) -> None:
        for label in ("対象外", "順序", "検証"):
            for placeholder in PLACEHOLDERS:
                with self.subTest(label=label, placeholder=placeholder):
                    line = next(line for line in BOUNDED.splitlines() if line.startswith(f"{label}:"))
                    emitted, suppressed = outcome(BOUNDED.replace(line, f"{label}: {placeholder}"))
                    self.assertIn(BROAD, emitted)
                    self.assertNotIn(BROAD, suppressed)

    def test_the_breakdown_must_be_stated_when_nothing_else_names_one(self) -> None:
        plan = "目的: 全体を書き換える。\n作業分解: {p}\n対象外: UI は変えない。\n順序: 先に読込、次に保存。\n検証: pytest を実行する。\n"
        self.assertNotIn(BROAD, outcome(plan.format(p="設定、読込の二つに分ける。"))[0])
        for placeholder in PLACEHOLDERS:
            with self.subTest(placeholder=placeholder):
                self.assertIn(BROAD, outcome(plan.format(p=placeholder))[0])

    def test_refusing_to_verify_is_not_a_scope_boundary(self) -> None:
        plan = BOUNDED.replace("対象外: UI は変えない。", "手順: 検証はしない。")

        emitted, suppressed = outcome(plan)

        self.assertIn(BROAD, emitted)
        self.assertNotIn(BROAD, suppressed)

    def test_the_sequence_finding_and_the_work_package_suppression_never_coexist(self) -> None:
        for label in ("作業分解", "成果物", "対象外", "順序", "検証", "目的"):
            for placeholder in PLACEHOLDERS:
                line = next(line for line in BOUNDED.splitlines() if line.startswith(f"{label}:"))
                plan = BOUNDED.replace(line, f"{label}: {placeholder}")
                with self.subTest(label=label, placeholder=placeholder):
                    emitted, suppressed = outcome(plan)
                    self.assertFalse(SEQUENCE in emitted and BROAD in suppressed)


if __name__ == "__main__":
    unittest.main()
