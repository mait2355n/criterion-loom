"""What counts as a measurable quality constraint."""

from __future__ import annotations

import time
import unittest

from semantic_guard_workflow.core import audit_request
from semantic_guard_workflow.request_signals import _has_quality_constraint_evidence as has_constraint

RULE = "req.quality.measurable_constraint_missing"


class QualityConstraintTests(unittest.TestCase):
    def test_words_and_units_that_are_not_constraints_do_not_count(self) -> None:
        for text in (
            "それ以上の議論は不要", "要件は以下の通り", "It is slow today", "対象は3分野", "5件の画面を対象にする",
            "ユーザーが1回押す", "a->3 items", "a => 3 items", "<div>3 items</div>", "List<3>", "x<3", "3 < x", "1000件", "以内で対応する",
            "受入基準: 未定", "基準: TBD", "閾値は後で決める",
            # rejected, withdrawn, dated or denied figures, and figures in containers that assert nothing
            "（閾値: 300ms は却下された）", "300ms 以内にはしない。", "> 300ms 以内（旧案）", "```\np95 < 300ms\n```",
            "- > 5つの画面を速くする。", "1. > 5つの画面を速くする。", "* > 5つの画面を速くする。",
            "~~~\n500ms\n~~~", "It was 300ms previously.", "The 200ms limit was rejected.",
        ):
            with self.subTest(text=text):
                self.assertFalse(has_constraint(text))

    def test_real_constraints_count(self) -> None:
        for text in (
            "応答は3秒以内", "p95 < 300ms", "99.9%以上", "100 MB 以下", "500ms", "3 hours", "2 days", "1000 rps",
            "latency <= 200 ms", "≤200ms", "≦ 5", "50ミリ秒", "10TB", "p99", "10件以内", "3 mins", "> 95%",
            "SLO: 99.9%", "受入基準: p95 500ms 以下", "> p95 < 300ms の引用",
            "3日間", "2週間以内", "5分間", "応答は300ms以内にする。リトライはしない。", "```\nコード\n```\n応答 300ms 以内",
        ):
            with self.subTest(text=text):
                self.assertTrue(has_constraint(text))

    def test_the_rule_is_raised_when_a_quality_word_has_no_constraint(self) -> None:
        for sentence in ("それ以上の議論は不要", "要件は以下の通り", "対象は3分野", "5件の画面を対象にする", "ユーザーが1回押す"):
            with self.subTest(sentence=sentence):
                result = audit_request(f"利用者: 保守者。目的: 検索を速くする。{sentence}。")
                self.assertIn(RULE, {finding.get("rule_id") for finding in result["findings"]})

    def test_a_figure_in_a_rejected_sentence_does_not_hide_a_real_one_elsewhere(self) -> None:
        self.assertTrue(has_constraint("旧案の 300ms は却下した。新しい上限は 200ms 以内とする。"))
        self.assertFalse(has_constraint("旧案の 300ms は却下した。\n新しい上限は未定。"))

    def test_many_sentences_are_judged_linearly(self) -> None:
        for text in ("却下 1s。" * 30_000, "300ms 以内にはしない。" * 20_000, "x " * 100_000 + "500ms"):
            with self.subTest(prefix=text[:8]):
                started = time.perf_counter()
                has_constraint(text)
                self.assertLess(time.perf_counter() - started, 1.0)

    def test_long_digit_runs_are_linear(self) -> None:
        for text in ("1" * 100_000, "1." * 50_000, "1," * 50_000, "a" + "1 " * 50_000):
            with self.subTest(prefix=text[:8]):
                started = time.perf_counter()
                has_constraint(text)
                self.assertLess(time.perf_counter() - started, 0.5)


if __name__ == "__main__":
    unittest.main()
