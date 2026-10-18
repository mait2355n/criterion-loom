"""The shared definition of a "decision": one value, one state, whatever its spelling.

Every cell of the word-by-format tables below must classify the same way, so a
deferral cannot hide behind Markdown decoration, a table cell, a trailing
parenthesis, or a qualifier, and a concrete value is never taken for a placeholder.
"""

from __future__ import annotations

import time
import unittest

from semantic_guard_workflow.assertion_context import find_field_assertion

TERM = "検証"

FORMATS = (
    "{t}: {w}",
    "{t}：{w}。",
    "- {t}: {w}",
    "* **{t}**: {w}",
    "**{t}**: **{w}**",
    "**{t}:** {w}",
    "> {t}: {w}",
    "1. {t}: {w}",
    "## {t}\n{w}",
    "## {t}\n\n- {w}",
    "| {t} | {w} |",
    "| 項目 | 値 |\n|---|---|\n| {t} | {w} |",
    "{t}: `{w}`",
    "{t}: {w} (TBD)",
    "{t}: {w}（理由は別紙）",
)
PROSE_FORMATS = ("{t}は{w}。", "{t}は、{w}。", "その{t}は{w}")

DEFERRED = (
    "後で決める",
    "未定",
    "TBD",
    "TBC",
    "TODO",
    "検討中",
    "要検討",
    "調整中",
    "別途",
    "追って決める",
    "未決定",
    "未確定",
    "保留",
    "後日",
    "後ほど記載する",
    "後で確認する",
    "今後決定する予定",
    "別途定める予定",
    "現時点では未定です",
    "まだ未定",
    "一旦保留",
    "to be determined",
    "not yet decided",
    "pending",
    "decide later",
    "under discussion",
    "不明",
)
DECLARED_NONE = ("なし", "無し", "特になし", "ありません", "none", "不要")
NOT_APPLICABLE = ("該当なし", "該当無し", "n/a", "N/A", "not applicable", "対象外")
NEGATED = ("実施しない", "行わない", "未実施", "行いません", "実施せず", "skipped")
EMPTY = ("", "-", "—", "…", "未記入", "空欄")
DECIDED = (
    "pytest で試験する",
    "p95 500ms 以下",
    "後で pytest を実行する",
    "未定義の挙動を禁止する",
    "検討中の案はA案を採用する",
    "unit tests run in CI",
)


def _cases(words: tuple[str, ...], formats: tuple[str, ...]) -> list[tuple[str, str]]:
    return [(fmt.format(t=TERM, w=word), word) for word in words for fmt in formats]


class DecisionStateTests(unittest.TestCase):
    def assert_state(self, text: str, state: str, *, accept_none: bool = False) -> None:
        match = find_field_assertion(text, [TERM], accept_none=accept_none)
        self.assertIsNotNone(match, text)
        self.assertEqual(match.state, state, f"{text!r} -> {match.state}/{match.reason}")

    def test_deferrals_are_deferred_in_every_format(self) -> None:
        for text, _ in _cases(DEFERRED, FORMATS + PROSE_FORMATS):
            with self.subTest(text=text):
                self.assert_state(text, "deferred")
                self.assertEqual(find_field_assertion(text, [TERM]).status, "rejected")

    def test_declared_none_is_none_in_every_format(self) -> None:
        for text, _ in _cases(DECLARED_NONE, FORMATS):
            with self.subTest(text=text):
                self.assert_state(text, "declared_none")
                self.assertEqual(find_field_assertion(text, [TERM]).status, "rejected")
                self.assertEqual(find_field_assertion(text, [TERM], accept_none=True).status, "present")

    def test_not_applicable_is_its_own_state_in_every_format(self) -> None:
        for text, _ in _cases(NOT_APPLICABLE, FORMATS):
            with self.subTest(text=text):
                self.assert_state(text, "not_applicable")
                self.assertEqual(find_field_assertion(text, [TERM]).status, "rejected")
                self.assertEqual(find_field_assertion(text, [TERM], accept_none=True).status, "present")

    def test_negations_are_negated_in_every_format(self) -> None:
        for text, _ in _cases(NEGATED, FORMATS):
            with self.subTest(text=text):
                self.assert_state(text, "negated")
                self.assertEqual(find_field_assertion(text, [TERM], accept_none=True).status, "rejected")

    def test_empty_values_are_empty(self) -> None:
        for text, _ in _cases(EMPTY, ("{t}: {w}", "- {t}: {w}", "**{t}**: {w}", "| {t} | {w} |")):
            with self.subTest(text=text):
                self.assert_state(text, "empty")

    def test_concrete_values_are_decided_in_every_format(self) -> None:
        for text, _ in _cases(DECIDED, FORMATS + PROSE_FORMATS):
            with self.subTest(text=text):
                self.assert_state(text, "decided")
                self.assertEqual(find_field_assertion(text, [TERM]).status, "present")

    def test_a_concrete_value_wins_over_a_deferral_elsewhere(self) -> None:
        text = "検証: 後で決める。\n検証手順: pytest を実行する。"

        self.assertEqual(find_field_assertion(text, [TERM]).status, "present")

    def test_compound_labels_carry_their_own_value(self) -> None:
        for text, state in (
            ("検証結果: 未定", "deferred"),
            ("**検証結果**: 未定", "deferred"),
            ("| 検証結果 | 未定 |", "deferred"),
            ("検証結果: pytest 全件成功", "decided"),
        ):
            with self.subTest(text=text):
                self.assert_state(text, state)

    def test_mixed_placeholders_are_not_a_decision(self) -> None:
        for value in ("TBD / 未定", "未定、後で決める", "TBD or pending", "未定・保留"):
            with self.subTest(value=value):
                self.assert_state(f"{TERM}: {value}", "deferred")

    def test_pathological_values_are_linear(self) -> None:
        n = 100_000
        for text in (
            f"{TERM}: 未定" + " " * n + "x",
            f"{TERM}: (" + " " * n + "x",
            f"| {TERM} | " + " " * n + "x",
            f"{TERM}: " + "(" * n,
            f"{TERM}: " + "現在は" * n,
            f"{TERM}: 未定" + "です" * n + "x",
            f"{TERM}: " + "=" * n,
            f"{TERM}: " + "*" * n + "未定",
            f"{TERM}: x" + " / " * n,
            f"{TERM}" + "検証" * n,
            f"{TERM}は未定。" * 10_000,
            f"{TERM}: 未定。\n" * 10_000,
            f"## {TERM}\n" * 10_000,
            f"| {TERM} | 未定 |" * 10_000,
        ):
            with self.subTest(prefix=text[:24]):
                started = time.perf_counter()
                find_field_assertion(text, [TERM])
                self.assertLess(time.perf_counter() - started, 0.5)


if __name__ == "__main__":
    unittest.main()
