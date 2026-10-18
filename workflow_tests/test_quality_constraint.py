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
            "ユーザーが1回押す", "a->3 items", "<div>3 items</div>", "List<3>", "x<3", "以内で対応する",
            "受入基準: 未定", "基準: TBD", "閾値は後で決める",
        ):
            with self.subTest(text=text):
                self.assertFalse(has_constraint(text))

    def test_real_constraints_count(self) -> None:
        for text in (
            "応答は3秒以内", "p95 < 300ms", "99.9%以上", "100 MB 以下", "500ms", "3 hours", "2 days", "1000 rps",
            "latency <= 200 ms", "≤200ms", "≦ 5", "50ミリ秒", "10TB", "p99", "10件以内", "3 mins", "> 95%",
            "SLO: 99.9%", "受入基準: p95 500ms 以下", "> p95 < 300ms の引用",
        ):
            with self.subTest(text=text):
                self.assertTrue(has_constraint(text))

    def test_the_rule_is_raised_when_a_quality_word_has_no_constraint(self) -> None:
        for sentence in ("それ以上の議論は不要", "要件は以下の通り", "対象は3分野", "5件の画面を対象にする", "ユーザーが1回押す"):
            with self.subTest(sentence=sentence):
                result = audit_request(f"利用者: 保守者。目的: 検索を速くする。{sentence}。")
                self.assertIn(RULE, {finding.get("rule_id") for finding in result["findings"]})

    def test_long_digit_runs_are_linear(self) -> None:
        for text in ("1" * 100_000, "1." * 50_000, "1," * 50_000, "a" + "1 " * 50_000):
            with self.subTest(prefix=text[:8]):
                started = time.perf_counter()
                has_constraint(text)
                self.assertLess(time.perf_counter() - started, 0.5)


if __name__ == "__main__":
    unittest.main()
