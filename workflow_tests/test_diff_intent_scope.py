"""An explicit scope limit in the intent is compared with the files the diff changes.

Only stated limits are read. Whether the diff implements what the intent asks
for is left to review; this check answers one narrower question: did the change
stay inside what the request said it may touch?
"""
from __future__ import annotations

import unittest

from semantic_guard_workflow.core import audit_diff


SCOPE_RULE = "diff.traceability.intent_scope_conflict"

SOURCE_AND_TEST = """diff --git a/app/core.py b/app/core.py
--- a/app/core.py
+++ b/app/core.py
@@ -1,4 +1,4 @@
 def total(items):
-    return sum(item.price for item in items)
+    return sum(item.price * item.qty for item in items)
diff --git a/tests/test_core.py b/tests/test_core.py
--- a/tests/test_core.py
+++ b/tests/test_core.py
@@ -4,3 +4,6 @@
         self.assertEqual(total([Item(2, 1)]), 2)
+
+    def test_total_uses_quantity(self):
+        self.assertEqual(total([Item(2, 3)]), 6)
"""
TEST_ONLY = SOURCE_AND_TEST.split("diff --git a/tests/test_core.py")[1]
TEST_ONLY = "diff --git a/tests/test_core.py" + TEST_ONLY
DOCUMENT = """diff --git a/README.md b/README.md
--- a/README.md
+++ b/README.md
@@ -1 +1 @@
-Teh tool reads a diff.
+The tool reads a diff.
"""


def _rules(result: dict[str, object]) -> set[str]:
    return {item["rule_id"] for item in result["findings"] if "rule_id" in item}


class IntentScopeTests(unittest.TestCase):
    def test_the_same_diff_is_judged_by_the_limit_the_intent_states(self) -> None:
        unlimited = audit_diff(SOURCE_AND_TEST, intent="合計金額の計算に数量を反映する。")
        limited = audit_diff(SOURCE_AND_TEST, intent="READMEの誤字を修正する。コードは変更しない。")

        self.assertNotIn(SCOPE_RULE, _rules(unlimited))
        self.assertEqual(unlimited["status"], "pass")
        self.assertIn(SCOPE_RULE, _rules(limited))
        self.assertEqual(limited["status"], "block")
        self.assertIn("intent_scope_alignment", limited["missing"])

    def test_document_only_and_no_code_limits_reject_code_changes(self) -> None:
        for intent in (
            "READMEの誤字を修正する。コードは変更しない。",
            "ドキュメントのみ修正する。",
            "文書だけを直す。実装は触らない。",
            "ソースには手を入れない。説明文のみ更新する。",
            "Docs-only change: fix the README typo.",
            "Fix the typo. No code changes.",
            "Update the documentation without touching the code.",
            "Only the README changes; do not modify the implementation.",
        ):
            with self.subTest(intent=intent):
                result = audit_diff(SOURCE_AND_TEST, intent=intent)
                finding = next(item for item in result["findings"] if item.get("rule_id") == SCOPE_RULE)
                self.assertIn("app/core.py", finding["evidence"])
                self.assertTrue(finding["needs_human_decision"])

    def test_a_kept_limit_is_not_a_finding(self) -> None:
        for intent in (
            "READMEの誤字を修正する。コードは変更しない。",
            "Docs-only change: fix the README typo.",
        ):
            with self.subTest(intent=intent):
                result = audit_diff(DOCUMENT, intent=intent)
                self.assertNotIn(SCOPE_RULE, _rules(result))
                self.assertEqual(result["status"], "pass")

    def test_tests_only_limit_rejects_other_source_changes(self) -> None:
        for intent in ("テストのみ追加する。", "Tests-only change: cover quantity."):
            with self.subTest(intent=intent):
                self.assertIn(SCOPE_RULE, _rules(audit_diff(SOURCE_AND_TEST, intent=intent)))
                self.assertNotIn(SCOPE_RULE, _rules(audit_diff(TEST_ONLY, intent=intent)))

    def test_a_named_file_that_must_stay_is_checked(self) -> None:
        for intent in (
            "数量を反映する。README.md は変更しない。",
            "数量を反映する。README.mdは対象外。",
            "Reflect quantity. Do not change README.md.",
            "Reflect quantity. Leave README.md unchanged.",
            "Reflect quantity and keep `README.md` untouched.",
        ):
            with self.subTest(intent=intent):
                changed = audit_diff(SOURCE_AND_TEST + DOCUMENT, intent=intent)
                finding = next(item for item in changed["findings"] if item.get("rule_id") == SCOPE_RULE)
                self.assertIn("README.md", finding["evidence"])
                untouched = audit_diff(SOURCE_AND_TEST, intent=intent)
                self.assertNotIn(SCOPE_RULE, _rules(untouched))

    def test_the_limit_may_be_stated_in_the_context(self) -> None:
        result = audit_diff(
            SOURCE_AND_TEST,
            intent="READMEの誤字を修正する。",
            context="対象外: コードは変更しない。",
        )
        self.assertIn(SCOPE_RULE, _rules(result))

    def test_exceptions_conditions_and_unrelated_negations_are_not_limits(self) -> None:
        for intent in (
            "app/core.py 以外は変更しない。",
            "Change nothing except app/core.py.",
            "このコードは変更しないと動かないので修正する。",
            "pyproject.toml の依存は変更しない。数量を反映する。",
            "公開 API の挙動は変えない。数量を反映する。",
            "数量を反映する。エラーメッセージは変更しない。",
        ):
            with self.subTest(intent=intent):
                self.assertNotIn(SCOPE_RULE, _rules(audit_diff(SOURCE_AND_TEST, intent=intent)))

    def test_negated_only_declarations_are_not_scope_limits(self) -> None:
        for intent in (
            "ドキュメントのみの変更ではない。コードとテストを修正する。",
            "テストのみではなく本体も直す。",
            "文書だけの修正ではなくコードも直す。",
            "This is not a docs-only change; update source and tests.",
            "Not only tests change; update source too.",
        ):
            with self.subTest(intent=intent):
                result = audit_diff(SOURCE_AND_TEST, intent=intent)
                self.assertNotIn(SCOPE_RULE, _rules(result))
                self.assertNotEqual(result["status"], "block")

    def test_relaxed_mode_downgrades_to_major(self) -> None:
        result = audit_diff(SOURCE_AND_TEST, intent="Docs-only change.", strict=False)
        finding = next(item for item in result["findings"] if item.get("rule_id") == SCOPE_RULE)
        self.assertEqual(finding["severity"], "major")
        self.assertEqual(result["status"], "warn")


if __name__ == "__main__":
    unittest.main()
