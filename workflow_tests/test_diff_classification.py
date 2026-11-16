"""Test files, change intent and failure handling in ``audit_diff``."""

from __future__ import annotations

import unittest

from semantic_guard_workflow.diff_audit import _is_test_file, audit_diff

SOURCE_DIFF = "diff --git a/src/app.py b/src/app.py\n+++ b/src/app.py\n{body}\n"
TEST_OBLIGATION = "diff.test_obligation.source_without_tests"
FAILURE_GAP = "diff.implementation.failure_handling_gap"


def rules(diff: str, intent: str = "設定を読む") -> set[object]:
    return {finding.get("rule_id") for finding in audit_diff(diff, intent=intent)["findings"]}


class TestFileClassificationTests(unittest.TestCase):
    def test_conventional_test_files_are_recognized(self) -> None:
        for path in (
            "tests/test_a.py", "test_a.py", "a_test.go", "pkg/a_test.go", "web/app.test.ts", "web/app.spec.js",
            "src/__tests__/a.ts", "FooTest.java", "src/main/FooTests.swift", "conftest.py", "tests.py",
            "src/test/java/Foo.java", "x_spec.rb", "workflow_tests/foo.py", "candidate-tests/foo.py",
        ):
            with self.subTest(path=path):
                self.assertTrue(_is_test_file(path))

    def test_words_that_merely_contain_test_are_not_test_files(self) -> None:
        for path in (
            "src/latest_release.py", "src/attest_signature.py", "src/contest_scoring.py", "src/detest.py",
            "docs/testing.md", "src/protest/handler.py", "latest/app.py", "contest/app.py",
        ):
            with self.subTest(path=path):
                self.assertFalse(_is_test_file(path))

    def test_a_source_change_with_a_lookalike_name_still_needs_a_test(self) -> None:
        for path in ("src/latest_release.py", "src/attest_signature.py", "src/contest_scoring.py"):
            with self.subTest(path=path):
                diff = f"diff --git a/{path} b/{path}\n+++ b/{path}\n+value = 1\n"
                self.assertIn(TEST_OBLIGATION, rules(diff))

    def test_go_source_with_its_test_file_satisfies_the_obligation(self) -> None:
        diff = (
            "diff --git a/a.go b/a.go\n+++ b/a.go\n+func A() {}\n"
            "diff --git a/a_test.go b/a_test.go\n+++ b/a_test.go\n+func TestA(t *testing.T) {}\n"
        )

        self.assertNotIn(TEST_OBLIGATION, rules(diff))


class DiffIntentTests(unittest.TestCase):
    def test_a_placeholder_intent_is_no_intent(self) -> None:
        diff = SOURCE_DIFF.format(body="+x = 1")
        for intent in ("", "未定", "TBD", "-", ".", "後で決める", "検討中", "なし"):
            with self.subTest(intent=intent):
                result = audit_diff(diff, intent=intent)
                self.assertIn("intent", result["missing"])

    def test_a_real_intent_is_accepted(self) -> None:
        result = audit_diff(SOURCE_DIFF.format(body="+x = 1"), intent="設定の読込を直す。")

        self.assertNotIn("intent", result["missing"])


class FailureHandlingEvidenceTests(unittest.TestCase):
    RISKY = "+subprocess.run(command)"

    def test_a_comment_promising_handling_later_is_not_handling(self) -> None:
        for comment in ("+# TODO: 例外処理は後で追加する", "+// TODO: handle timeout later", "+# try again later, catch errors"):
            with self.subTest(comment=comment):
                self.assertIn(FAILURE_GAP, rules(SOURCE_DIFF.format(body=f"{comment}\n{self.RISKY}")))

    def test_identifiers_that_contain_the_words_are_not_handling(self) -> None:
        body = "+entry = build()\n+retry_count = 3\n+subprocess.run(entry)"

        self.assertIn(FAILURE_GAP, rules(SOURCE_DIFF.format(body=body)))

    def test_real_handling_is_accepted(self) -> None:
        for body in (
            "+try:\n+    subprocess.run(command, check=True)\n+except OSError:\n+    pass",
            "+subprocess.run(command, timeout=10)",
            "+result = subprocess.run(command)\n+if result.returncode:\n+    raise RuntimeError()",
            "+validate_input(command)\n+subprocess.run(command)",
        ):
            with self.subTest(body=body):
                self.assertNotIn(FAILURE_GAP, rules(SOURCE_DIFF.format(body=body)))


if __name__ == "__main__":
    unittest.main()
