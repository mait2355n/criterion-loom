from __future__ import annotations

import unittest
import random

from semantic_guard_workflow.core import audit_diff, audit_plan, audit_request
from semantic_guard_workflow.plan_audit import _deliverable_item_count
from semantic_guard_workflow.rule_mapping import enrich_finding_mapping
from semantic_guard_workflow.text_normalization import normalization_source_ranges, normalize_audit_text


class NormalizationContractTests(unittest.TestCase):
    def test_removed_format_characters_do_not_split_a_crlf_source_range(self) -> None:
        for separator in ("\u200b", "\ufeff", "\u200b\u2060\ufeff"):
            with self.subTest(separator=repr(separator)):
                source = "\r" + separator + "\n"
                self.assertEqual(normalize_audit_text(source), "\n")
                self.assertEqual(normalization_source_ranges(source), [(0, len(source))])
                with_mark = source + "\u0301"
                self.assertEqual(normalization_source_ranges(with_mark),
                                 [(0, len(with_mark)), (0, len(with_mark))])

    def test_removed_format_characters_do_not_prevent_combining_composition(self) -> None:
        for separator in ("\u200b", "\ufeff", "\u200b\u2060\ufeff"):
            with self.subTest(separator=repr(separator)):
                source = "カ" + separator + "\u3099"
                normalized = normalize_audit_text(source)
                self.assertEqual(normalized, "ガ")
                self.assertEqual(normalize_audit_text(normalized), normalized)
                self.assertEqual(normalization_source_ranges(source), [(0, len(source))])

    def test_normalized_characters_map_to_original_composition_ranges(self) -> None:
        source = "\ufeffＡカ\u3099㍿\r\n"
        self.assertEqual(normalize_audit_text(source), "Aガ株式会社\n")
        self.assertEqual(normalization_source_ranges(source),
                         [(1, 2), (2, 4), (4, 5), (4, 5), (4, 5), (4, 5), (5, 7)])

    def test_source_mapping_preserves_normalization_and_order_across_unicode_sequences(self) -> None:
        rng = random.Random(20261017)
        alphabet = "Ａaカ\u3099ﾊﾞ㍿\r\n\u200b\ufeff\u1100\u1161\u11a8\u0301\u0327\u2028"
        for _ in range(200):
            text = "".join(rng.choice(alphabet) for _ in range(30))
            ranges = normalization_source_ranges(text)
            normalized = normalize_audit_text(text)
            self.assertEqual(normalize_audit_text(normalized), normalized)
            self.assertEqual(len(ranges), len(normalized))
            previous = (-1, -1)
            pieces = []
            for start, end in ranges:
                self.assertTrue(0 <= start < end <= len(text))
                self.assertGreaterEqual(start, previous[0])
                if (start, end) != previous:
                    pieces.append(normalize_audit_text(text[start:end]))
                previous = (start, end)
            self.assertEqual("".join(pieces), normalize_audit_text(text))

    def test_logical_verification_spans_use_the_callers_original_coordinates(self) -> None:
        for prefix in ("\ufeff", "カ\u3099の補足。", "㍿への補足。", "補足。\r\n",
                       "\r\u200b\n", "\r\ufeff\n", "\r\u200b\u2060\ufeff\n",
                       "カ\u200b\u3099の補足。"):
            for source in ("request", "context"):
                with self.subTest(prefix=repr(prefix), source=source):
                    body = prefix + "目的: 検索する。受入基準: 200ms以内。検証方法: pytest。"
                    text, context = (body, "") if source == "request" else ("目的: 検索する。", body)
                    result = audit_request(text, context=context)
                    fact = next(item for item in result["details"]["logical_trace"]["facts"]
                                if item["id"] == "fact.text.has_verification_language")
                    span = fact["evidence"][0]
                    self.assertEqual(span["source"], source)
                    self.assertEqual(body[span["start"]:span["end"]], "受入基準")

    def test_request_diff_dispatch_preserves_unicode_file_identity(self) -> None:
        for name in ("Ａ.py", "カ\u3099.py", "file\u200bname.py"):
            with self.subTest(name=name):
                diff = f'diff --git a/{name} b/{name}\n--- a/{name}\n+++ b/{name}\n@@ -0,0 +1 @@\n+name = "Ａ"\n'
                direct = audit_diff(diff, intent="変更する")
                routed = audit_request(diff, context="変更する", input_kind="diff-summary")
                self.assertEqual(routed["details"]["changed_files"], direct["details"]["changed_files"])
                self.assertEqual(routed["details"]["changed_files"], [name])

    def test_diff_summary_signals_do_not_depend_on_spelling(self) -> None:
        wide = lambda text: "".join(chr(ord(c) + 0xFEE0) if 0x21 <= ord(c) <= 0x7E else c for c in text)
        for sentence in ("token を平文で保存する。", "SQL を連結で組み立てる。", "cookie を共有する。"):
            for variant in (sentence, wide(sentence)):
                with self.subTest(variant=variant):
                    for result in (
                        audit_request(variant, context="目的: 表示を整える。", input_kind="diff-summary"),
                        audit_diff(variant, intent="目的: 表示を整える。"),
                    ):
                        self.assertEqual(result["status"], "warn")
                        self.assertIn(
                            "diff.security.sensitive_surface_change",
                            {finding.get("rule_id") for finding in result["findings"]},
                        )

    def test_unified_diff_signals_do_not_depend_on_spelling(self) -> None:
        plain = "diff --git a/src/app.py b/src/app.py\n+++ b/src/app.py\n+password = request.args['p']\n+subprocess.run(cmd)\n"
        wide = plain.replace("password", "ｐａｓｓｗｏｒｄ").replace("subprocess", "ｓｕｂｐｒｏｃｅｓｓ")

        def shape(result: dict[str, object]) -> tuple[object, ...]:
            return (
                result["status"],
                sorted(str(finding.get("rule_id") or finding["category"]) for finding in result["findings"]),
                sorted(result["details"]["implementation_signals"]),
                result["details"]["changed_files"],
            )

        self.assertEqual(shape(audit_diff(wide, intent="設定を読む")), shape(audit_diff(plain, intent="設定を読む")))


class DeliverableFieldTests(unittest.TestCase):
    def test_explicit_deliverable_field_follows_sentence_or_clause_boundaries(self) -> None:
        for separator in ("; ", "；", ". ", "。", "\n"):
            with self.subTest(separator=separator):
                plan = "目的: 成果物の形式、用途、配置を決める" + separator + "成果物: 文書。"
                self.assertEqual(_deliverable_item_count(plan), 1)

    def test_explicit_deliverables_are_not_shadowed_by_words_in_the_objective(self) -> None:
        for objective in ("目的: 出力を整理する。", "目的: 成果物を整理する。", "Objective: audit output."):
            for separator in ("\n", " "):
                with self.subTest(objective=objective, separator=repr(separator)):
                    deliverables = "成果物: 文書A、文書B、文書C。"
                    first = separator.join((objective, deliverables, "手順: 文書を作る。"))
                    reordered = separator.join((deliverables, objective, "手順: 文書を作る。"))
                    self.assertEqual(_deliverable_item_count(first), 3)
                    self.assertEqual(_deliverable_item_count(first), _deliverable_item_count(reordered))
                    for plan in (first, reordered):
                        result = audit_plan(plan)
                        rules = {enrich_finding_mapping("audit_plan", item).get("rule_id")
                                 for item in result["findings"]}
                        self.assertIn("plan.structure.work_package_decomposition_missing", rules)
