from __future__ import annotations

import json
import unittest
from pathlib import Path

from semantic_guard_workflow.core import audit_plan, audit_request
from semantic_guard_workflow.evaluation import DEFAULT_FIXTURE_ROOT
from semantic_guard_workflow.plan_audit import _deliverable_item_count
from semantic_guard_workflow.request_direction_binding import direction_binding_contract_violations
from semantic_guard_workflow.request_signals import _has_quality_constraint_evidence
from semantic_guard_workflow.rule_mapping import enrich_finding_mapping
from semantic_guard_workflow.text_normalization import normalization_source_ranges, normalize_audit_text
from workflow_tests.test_request_direction_binding import CharacterSignalProvider

GOOD_REQUEST = json.loads(
    (Path(DEFAULT_FIXTURE_ROOT) / "requests" / "problem-mechanism-fit-good.expected.json").read_text(encoding="utf-8")
)["text"]


def _rule_ids(result: dict[str, object], phase: str) -> set[str]:
    return {
        str(enrich_finding_mapping(phase, finding).get("rule_id") or finding["category"])
        for finding in result["findings"]  # type: ignore[index]
    }


class NormalizeAuditTextTests(unittest.TestCase):
    def test_full_width_ascii_becomes_ascii(self) -> None:
        self.assertEqual(normalize_audit_text("ＡＰＩ：１２３"), "API:123")

    def test_decomposed_kana_is_composed(self) -> None:
        self.assertEqual(normalize_audit_text("ガ"), "ガ")
        self.assertEqual(normalize_audit_text("ﾃｽﾄ"), "テスト")

    def test_invisible_characters_are_removed(self) -> None:
        self.assertEqual(normalize_audit_text("﻿a​b⁠c­d"), "abcd")

    def test_every_unicode_format_character_is_removed(self) -> None:
        import unicodedata

        for code in list(range(0x20000)) + list(range(0xE0000, 0xE0200)):
            character = chr(code)
            if unicodedata.category(character) == "Cf":
                with self.subTest(code=hex(code)):
                    self.assertEqual(normalize_audit_text(f"a{character}b"), "ab")

    def test_selectors_joiners_and_tags_are_removed(self) -> None:
        # Not all of these are "Cf": variation selectors, the combining grapheme
        # joiner, Mongolian free variation selectors, and tag characters.
        for code in (0x034F, 0x180B, 0x180C, 0x180D, 0x180E, 0x180F, 0xFE00, 0xFE0F, 0xE0020, 0xE007F, 0xE0100, 0xE01EF):
            with self.subTest(code=hex(code)):
                self.assertEqual(normalize_audit_text(f"適{chr(code)}切"), "適切")

    def test_source_ranges_skip_every_removed_character(self) -> None:
        text = "適\u2062切\ufe0fに\U000e0020\u034f"
        normalized = normalize_audit_text(text)

        ranges = normalization_source_ranges(text)

        self.assertEqual(normalized, "適切に")
        self.assertEqual(len(ranges), len(normalized))
        self.assertEqual([text[start:end] for start, end in ranges][0], "適")

    def test_line_terminators_are_unified(self) -> None:
        self.assertEqual(normalize_audit_text("a\r\nb\rc d e"), "a\nb\nc\nd\ne")

    def test_normalization_is_idempotent(self) -> None:
        sample = "﻿ＡＰＩ：１２３\r\nガ​"
        once = normalize_audit_text(sample)
        self.assertEqual(normalize_audit_text(once), once)

    def test_non_text_and_empty_pass_through(self) -> None:
        self.assertEqual(normalize_audit_text(""), "")
        self.assertIsNone(normalize_audit_text(None))  # type: ignore[arg-type]


class SpellingDoesNotChangeTheVerdictTests(unittest.TestCase):
    def test_full_width_request_matches_its_ascii_form(self) -> None:
        plain = audit_request("利用者: 保守者。目的: 帳票を出力する。受入基準: 応答は 200ms 以内。検証方法: pytest。")
        wide = audit_request("利用者： 保守者。目的： 帳票を出力する。受入基準： 応答は ２００ｍｓ 以内。検証方法： ｐｙｔｅｓｔ。")

        self.assertEqual(_rule_ids(wide, "audit_request"), _rule_ids(plain, "audit_request"))
        self.assertEqual(wide["status"], plain["status"])

    def test_invisible_characters_inside_a_word_do_not_hide_the_finding(self) -> None:
        base = "利用者: 保守者。目的: 帳票を適切に出力する。受入基準: 応答は 200ms 以内。検証方法: pytest。"
        expected = _rule_ids(audit_request(base), "audit_request")
        self.assertIn("req.clarity.ambiguous_term", expected)
        plan = "目的: 古い設定を削除する。\n対象: config/\n検証: pytest\n"
        plan_expected = _rule_ids(audit_plan(plan), "audit_plan")
        self.assertIn("plan.governance.decision_gate_missing", plan_expected)

        for character in ("\u2062", "\u061c", "\u180e", "\u206a", "\ufe0f", "\U000e0020", "\u034f"):
            with self.subTest(code=hex(ord(character))):
                self.assertEqual(
                    _rule_ids(audit_request(base.replace("適切に", f"適{character}切に")), "audit_request"), expected
                )
                self.assertEqual(
                    _rule_ids(audit_plan(plan.replace("削除", f"削{character}除")), "audit_plan"), plan_expected
                )

    def test_decomposed_plan_matches_its_composed_form(self) -> None:
        plan = (Path(DEFAULT_FIXTURE_ROOT) / "plans" / "good.md").read_text(encoding="utf-8")
        import unicodedata

        composed = audit_plan(plan)
        decomposed = audit_plan(unicodedata.normalize("NFD", plan))

        self.assertEqual(_rule_ids(decomposed, "audit_plan"), _rule_ids(composed, "audit_plan"))
        self.assertEqual(decomposed["status"], composed["status"])

    def test_span_bearing_direction_binding_still_refers_to_the_callers_text(self) -> None:
        # The full-width question mark is rewritten by normalization. The
        # direction-binding contract check compares spans against the caller's
        # own text, so that audit must not see the normalized form.
        text = "横一列で、Aの次の項目はどれですか？"

        result = audit_request(text, morphology_provider=CharacterSignalProvider())
        summary = result["details"]["direction_binding_summary"]

        self.assertEqual(summary["frames"][0]["direction_binding"]["search_scope"]["text_region"], {"start": 0, "end": len(text)})
        self.assertEqual(direction_binding_contract_violations(summary, text), [])


class QuantityEvidenceTests(unittest.TestCase):
    def test_numeric_blockquotes_do_not_supply_quality_thresholds(self) -> None:
        for text in (
            "> 5つの画面を速くする。",
            "> > 5 sources を参照して画面を速くする。",
            "目的: 画面を速くする。\n> 5 sources を参照する。",
        ):
            with self.subTest(text=text):
                self.assertFalse(_has_quality_constraint_evidence(text))
                self.assertIn(
                    "req.quality.measurable_constraint_missing",
                    _rule_ids(audit_request(text), "audit_request"),
                )

    def test_quoted_numeric_comparisons_keep_their_threshold_evidence(self) -> None:
        for text in ("> p95 < 300ms", "> 処理時間 > 3秒", "CPU > 80", ">= 3"):
            with self.subTest(text=text):
                self.assertTrue(_has_quality_constraint_evidence(text))

    def test_comparators_count_only_next_to_a_number(self) -> None:
        for text in ("応答は200ms以内", "p95 < 300ms", "処理時間 > 3秒", "CPU ≤ 80%", "10 seconds", "1000件/秒"):
            with self.subTest(text=text):
                self.assertTrue(_has_quality_constraint_evidence(text))

    def test_markup_and_prose_do_not_count_as_a_threshold(self) -> None:
        for text in ("> 速くする", "A -> B に変換", "<div>表示</div>", "5 sources", "np95 の話", "速度を速く"):
            with self.subTest(text=text):
                self.assertFalse(_has_quality_constraint_evidence(text))

    def test_quoting_a_requirement_does_not_hide_a_missing_threshold(self) -> None:
        text = "目的: 画面を安全に速くする。"
        plain = _rule_ids(audit_request(text), "audit_request")
        quoted = _rule_ids(audit_request("> " + text), "audit_request")

        self.assertIn("req.quality.measurable_constraint_missing", plain)
        self.assertEqual(quoted, plain)


class PlanLayoutTests(unittest.TestCase):
    ONE_LINE = "目的: 設定を整理する。対象外: UI は変えない。成果物: 設定文書、README。手順: 調査、実装、検証。依存: 既存設定。"

    def test_deliverable_count_reads_only_the_deliverable_sentence(self) -> None:
        self.assertEqual(_deliverable_item_count(self.ONE_LINE), 2)
        self.assertEqual(_deliverable_item_count(self.ONE_LINE.replace("。", "。\n")), 2)

    def test_deliverable_count_is_zero_without_a_deliverable_sentence(self) -> None:
        self.assertEqual(_deliverable_item_count("目的: 設定を整理する。"), 0)

    def test_plan_verdict_does_not_depend_on_line_breaks(self) -> None:
        one_line = audit_plan(self.ONE_LINE)
        per_sentence = audit_plan(self.ONE_LINE.replace("。", "。\n"))

        self.assertEqual(_rule_ids(per_sentence, "audit_plan"), _rule_ids(one_line, "audit_plan"))

    def test_deliverables_do_not_satisfy_the_objective(self) -> None:
        plan = (Path(DEFAULT_FIXTURE_ROOT) / "plans" / "good.md").read_text(encoding="utf-8")
        without_objective = "\n".join(line for line in plan.split("\n") if not line.startswith("目的:"))

        result = audit_plan(without_objective)

        self.assertIn("objective", result["missing"])
        self.assertIn("plan.objective.purpose_missing", _rule_ids(result, "audit_plan"))

    def test_an_outcome_statement_still_counts_as_an_objective(self) -> None:
        result = audit_plan("成果: 設定の重複をなくす。\n対象外: UI。")

        self.assertNotIn("objective", result["missing"])


class DocumentStructureTests(unittest.TestCase):
    README = (Path(DEFAULT_FIXTURE_ROOT) / "documents" / "readme-good.md").read_text(encoding="utf-8")

    def test_headings_inside_quotes_and_lists_are_recognised(self) -> None:
        plain = _rule_ids(audit_request(self.README, input_kind="document"), "audit_request")
        for prefix in ("> ", "- "):
            with self.subTest(prefix=prefix):
                prefixed = "\n".join(
                    line if line.startswith("```") or line.strip() == "" or "semantic-guard" in line else prefix + line
                    for line in self.README.split("\n")
                )
                self.assertEqual(_rule_ids(audit_request(prefixed, input_kind="document"), "audit_request"), plain)

    def test_a_document_without_headings_is_still_flagged(self) -> None:
        plain = self.README.replace("## ", "").replace("# ", "")

        self.assertIn("doc.structure.heading_missing", _rule_ids(audit_request(plain, input_kind="document"), "audit_request"))


if __name__ == "__main__":
    unittest.main()
