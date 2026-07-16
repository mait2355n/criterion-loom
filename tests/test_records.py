from __future__ import annotations

import unittest

from semantic_guard.records import parse_requirement_record


COMPLETE = """Purpose: 検索結果を返す
User: 検索API
Scenario: 検索APIが検索要求を処理した場合、検索結果を返す
Expected result: 検索結果を p95 500ms以内で返す
Acceptance criteria: 検索応答時間 p95 500ms 以下
Verification method: 検索応答時間を benchmark で測定する
Evidence: 検索 benchmark report"""


class RequirementRecordTests(unittest.TestCase):
    def test_complete_labelled_record_is_closed(self) -> None:
        record = parse_requirement_record(COMPLETE)

        self.assertEqual(record.record_mode, "closed_record")
        self.assertEqual(record.record_count, 1)
        self.assertEqual(record.missing_fields, ())
        self.assertEqual(record.duplicate_fields, ())
        self.assertEqual(record.unconsumed_spans, ())

    def test_source_coordinates_reproduce_exact_value(self) -> None:
        record = parse_requirement_record(COMPLETE)
        criterion = record.one("acceptance_criteria")

        self.assertIsNotNone(criterion)
        assert criterion is not None
        self.assertEqual(
            COMPLETE[criterion.value_start : criterion.value_end],
            "検索応答時間 p95 500ms 以下",
        )

    def test_unlabelled_line_keeps_record_open(self) -> None:
        record = parse_requirement_record(COMPLETE + "\nこの行の役割は宣言されていない。")

        self.assertEqual(record.record_mode, "open_text")
        self.assertEqual(len(record.unconsumed_spans), 1)
        self.assertIn("unconsumed_span_count:1", record.diagnostics)

    def test_duplicate_field_is_not_silently_selected(self) -> None:
        record = parse_requirement_record(COMPLETE + "\nEvidence: second report")

        self.assertEqual(record.record_mode, "open_text")
        self.assertEqual(record.duplicate_fields, ("evidence",))
        self.assertIsNone(record.one("evidence"))

    def test_explicit_separator_marks_multiple_records(self) -> None:
        record = parse_requirement_record(COMPLETE + "\n---\nPurpose: 別要求")

        self.assertEqual(record.record_mode, "open_text")
        self.assertEqual(record.record_count, 2)
        self.assertIn("multiple_records:2", record.diagnostics)


if __name__ == "__main__":
    unittest.main()
