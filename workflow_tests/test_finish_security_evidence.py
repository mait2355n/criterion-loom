"""A security word is evidence only where a confirmation is stated."""

from __future__ import annotations

import unittest

from semantic_guard_workflow.finish_audit import finish_check

BASE = "認証処理を変更した。pytest を実行して全件成功した。受入基準の p95 500ms 以下を満たした。残リスクなし。"


def security_findings(extra: str) -> list[object]:
    result = finish_check(BASE + extra, evidence="pytest 42 passed")
    return [finding for finding in result["findings"] if finding["category"] == "security"]


class FinishSecurityEvidenceTests(unittest.TestCase):
    def test_a_security_change_without_any_statement_is_flagged(self) -> None:
        self.assertTrue(security_findings(""))

    def test_negations_deferrals_and_bare_words_are_not_evidence(self) -> None:
        for extra in (
            "セキュリティ確認は未実施。",
            "手動確認はしていない。",
            "安全。",
            "dependency",
            "セキュリティ: 未定",
            "セキュリティ: なし",
            "手動確認: していない",
            "セキュリティ確認は後で行う。",
            "secret scan: 実施しない",
            "OWASP: TBD",
        ):
            with self.subTest(extra=extra):
                self.assertTrue(security_findings(extra))

    def test_a_stated_confirmation_is_evidence(self) -> None:
        for extra in (
            "手動確認: 認可の境界を確認した",
            "セキュリティ: 問題なし",
            "secret scan を実行した。",
            "OWASP の項目を確認した。",
            "依存の安全性を確認した。",
            "Dependency scan: no findings",
            "セキュリティ試験で機密情報の表示が0件と確認。",
        ):
            with self.subTest(extra=extra):
                self.assertFalse(security_findings(extra))

    def test_one_negation_does_not_cancel_a_separate_confirmation(self) -> None:
        self.assertFalse(security_findings("セキュリティ確認は未実施。手動確認: 認可の境界を確認した。"))


if __name__ == "__main__":
    unittest.main()
