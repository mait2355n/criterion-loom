"""Removing or switching off a test must not look better than leaving it alone.

Before these checks, a source change with no test change warned, while the same
change plus a deleted test file or an added ``@unittest.skip`` passed: any
touched test path counted as a test change.
"""
from __future__ import annotations

import unittest

from semantic_guard_workflow.core import audit_diff
from semantic_guard_workflow.mcp_server import audit_diff_tool


REDUCTION_RULE = "diff.test_obligation.tests_removed_or_disabled"
NO_TESTS_RULE = "diff.test_obligation.source_without_tests"
INTENT = "合計金額の計算に数量を反映する。"

SOURCE = """diff --git a/app/core.py b/app/core.py
--- a/app/core.py
+++ b/app/core.py
@@ -1,4 +1,4 @@
 def total(items):
-    return sum(item.price for item in items)
+    return sum(item.price * item.qty for item in items)
"""
DELETED_TEST = """diff --git a/tests/test_core.py b/tests/test_core.py
deleted file mode 100644
--- a/tests/test_core.py
+++ /dev/null
@@ -1,4 +0,0 @@
-import unittest
-class T(unittest.TestCase):
-    def test_total(self):
-        self.assertEqual(total([Item(2, 1)]), 2)
"""
NEW_TEST = """diff --git a/tests/test_total.py b/tests/test_total.py
new file mode 100644
--- /dev/null
+++ b/tests/test_total.py
@@ -0,0 +1,4 @@
+import unittest
+class T(unittest.TestCase):
+    def test_total(self):
+        self.assertEqual(total([Item(2, 1)]), 2)
"""
ADDED_TEST = """diff --git a/tests/test_core.py b/tests/test_core.py
--- a/tests/test_core.py
+++ b/tests/test_core.py
@@ -4,3 +4,6 @@
         self.assertEqual(total([Item(2, 1)]), 2)
+
+    def test_total_uses_quantity(self):
+        self.assertEqual(total([Item(2, 3)]), 6)
"""
DELETED_FEATURE = """diff --git a/app/legacy_export.py b/app/legacy_export.py
deleted file mode 100644
--- a/app/legacy_export.py
+++ /dev/null
@@ -1,2 +0,0 @@
-def export_legacy(rows):
-    return [str(row) for row in rows]
diff --git a/tests/test_legacy_export.py b/tests/test_legacy_export.py
deleted file mode 100644
--- a/tests/test_legacy_export.py
+++ /dev/null
@@ -1,2 +0,0 @@
-def test_export_legacy():
-    assert export_legacy([1]) == ["1"]
"""


def _test_file_change(marker_line: str, *, added: bool = True) -> str:
    sign = "+" if added else "-"
    return (
        "diff --git a/tests/test_core.py b/tests/test_core.py\n"
        "--- a/tests/test_core.py\n"
        "+++ b/tests/test_core.py\n"
        "@@ -1,5 +1,6 @@\n"
        " import unittest\n"
        " class T(unittest.TestCase):\n"
        f"{sign}{marker_line}\n"
        "     def test_total(self):\n"
        "         self.assertEqual(total([Item(2, 1)]), 2)\n"
    )


def _rules(result: dict[str, object]) -> set[str]:
    return {item["rule_id"] for item in result["findings"] if "rule_id" in item}


class TestReductionTests(unittest.TestCase):
    def test_removing_tests_is_never_better_than_leaving_them(self) -> None:
        untouched = audit_diff(SOURCE, intent=INTENT)
        deleted = audit_diff(SOURCE + DELETED_TEST, intent=INTENT)
        skipped = audit_diff(SOURCE + _test_file_change('    @unittest.skip("flaky")'), intent=INTENT)

        self.assertEqual(untouched["status"], "warn")
        self.assertEqual(_rules(untouched), {NO_TESTS_RULE})
        for worse in (deleted, skipped):
            self.assertEqual(worse["status"], "block")
            self.assertIn(REDUCTION_RULE, _rules(worse))
            self.assertLess(worse["score"], untouched["score"])

    def test_a_deleted_test_file_does_not_discharge_the_test_obligation(self) -> None:
        result = audit_diff(SOURCE + DELETED_TEST, intent=INTENT)
        self.assertEqual(_rules(result), {NO_TESTS_RULE, REDUCTION_RULE})
        self.assertTrue({"test_obligation", "test_preservation"} <= set(result["missing"]))
        finding = next(item for item in result["findings"] if item["rule_id"] == REDUCTION_RULE)
        self.assertIn("tests/test_core.py", finding["evidence"])

    def test_deleting_only_a_test_file_is_flagged(self) -> None:
        result = audit_diff(DELETED_TEST, intent="テストを安定化する。")
        self.assertEqual(_rules(result), {REDUCTION_RULE})
        self.assertEqual(result["status"], "block")

    def test_unconditional_disable_markers_are_flagged(self) -> None:
        for marker in (
            '    @unittest.skip("flaky")',
            "    @pytest.mark.skip",
            '    @pytest.mark.skip(reason="flaky")',
            "    @pytest.mark.xfail",
            "    @unittest.expectedFailure",
            "    it.skip('adds', () => {",
            "    xit('adds', () => {",
            "    describe.skip('core', () => {",
            "    @Disabled",
            "    #[ignore]",
        ):
            with self.subTest(marker=marker):
                result = audit_diff(SOURCE + _test_file_change(marker), intent=INTENT)
                self.assertIn(REDUCTION_RULE, _rules(result))
                self.assertEqual(result["status"], "block")

    def test_conditional_guards_and_reenabling_are_not_removals(self) -> None:
        cases = (
            _test_file_change('    @unittest.skipIf(sys.platform == "win32", "posix only")'),
            _test_file_change('    @unittest.skipUnless(shutil.which("git"), "needs git")'),
            _test_file_change('    @pytest.mark.skipif(sys.version_info < (3, 12), reason="3.12+")'),
            _test_file_change('    @unittest.skip("flaky")', added=False),
        )
        for diff in cases:
            with self.subTest(diff=diff.splitlines()[6]):
                result = audit_diff(SOURCE + diff, intent=INTENT)
                self.assertNotIn(REDUCTION_RULE, _rules(result))
                self.assertNotIn(NO_TESTS_RULE, _rules(result))

    def test_moved_renamed_and_added_tests_are_not_removals(self) -> None:
        renamed = (
            "diff --git a/tests/test_core.py b/tests/test_core.py\n"
            "--- a/tests/test_core.py\n"
            "+++ b/tests/test_core.py\n"
            "@@ -2,4 +2,4 @@\n"
            " class T(unittest.TestCase):\n"
            "-    def test_total(self):\n"
            "+    def test_total_sums_prices(self):\n"
            "         self.assertEqual(total([Item(2, 1)]), 2)\n"
        )
        for label, diff in (
            ("moved to a new file", SOURCE + DELETED_TEST + NEW_TEST),
            ("renamed", SOURCE + renamed),
            ("added", SOURCE + ADDED_TEST),
        ):
            with self.subTest(case=label):
                result = audit_diff(diff, intent=INTENT)
                self.assertEqual(_rules(result) & {REDUCTION_RULE, NO_TESTS_RULE}, set())

    def test_net_loss_of_test_definitions_is_flagged(self) -> None:
        two_removed_one_added = (
            "diff --git a/tests/test_core.py b/tests/test_core.py\n"
            "--- a/tests/test_core.py\n"
            "+++ b/tests/test_core.py\n"
            "@@ -2,7 +2,4 @@\n"
            " class T(unittest.TestCase):\n"
            "-    def test_total(self):\n"
            "-        self.assertEqual(total([Item(2, 1)]), 2)\n"
            "-    def test_empty(self):\n"
            "-        self.assertEqual(total([]), 0)\n"
            "+    def test_smoke(self):\n"
            "+        self.assertTrue(total)\n"
        )
        result = audit_diff(SOURCE + two_removed_one_added, intent=INTENT)
        finding = next(item for item in result["findings"] if item["rule_id"] == REDUCTION_RULE)
        self.assertIn("削除 2 件 / 追加 1 件", finding["evidence"])

    def test_a_declared_test_change_in_the_intent_accounts_for_it(self) -> None:
        for diff, declaration in (
            (SOURCE + DELETED_TEST, "旧テスト tests/test_core.py は重複のため削除する。"),
            (SOURCE + DELETED_TEST, "The old tests in tests/test_core.py are removed as duplicates."),
            (SOURCE + _test_file_change('    @unittest.skip("flaky")'), "不安定なテストは一時的にスキップする。"),
        ):
            with self.subTest(declaration=declaration):
                result = audit_diff(diff, intent=INTENT + " " + declaration)
                self.assertNotIn(REDUCTION_RULE, _rules(result))

    def test_a_requested_feature_removal_takes_its_tests_with_it(self) -> None:
        requested = audit_diff(DELETED_FEATURE, intent="旧エクスポート機能を削除する。")
        self.assertEqual(_rules(requested) & {REDUCTION_RULE, NO_TESTS_RULE}, set())

        silent = audit_diff(DELETED_FEATURE, intent="エクスポートを整理する。")
        self.assertIn(REDUCTION_RULE, _rules(silent))

    def test_a_prose_summary_that_lists_a_deleted_test_is_read(self) -> None:
        summary = "変更ファイル:\n- 更新: app/core.py\n- 削除: tests/test_core.py\n"
        result = audit_diff(summary, intent=INTENT)
        self.assertTrue({NO_TESTS_RULE, REDUCTION_RULE} <= _rules(result))

    def test_relaxed_mode_downgrades_to_major(self) -> None:
        result = audit_diff(SOURCE + DELETED_TEST, intent=INTENT, strict=False)
        finding = next(item for item in result["findings"] if item["rule_id"] == REDUCTION_RULE)
        self.assertEqual(finding["severity"], "major")
        self.assertEqual(result["status"], "warn")

    def test_mcp_service_uses_the_same_boundary(self) -> None:
        result = audit_diff_tool(diff=SOURCE + DELETED_TEST, intent=INTENT)
        self.assertEqual(result["status"], "block")
        self.assertIn(REDUCTION_RULE, _rules(result))


if __name__ == "__main__":
    unittest.main()
