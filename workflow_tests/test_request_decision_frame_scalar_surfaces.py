from __future__ import annotations

import unittest

from jsonschema import validate

from semantic_guard_workflow.decision_frame_scales import SCALE_SPECS
from semantic_guard_workflow.models import load_audit_result_schema
from semantic_guard_workflow.request_audit import audit_request
from semantic_guard_workflow.request_decision_frame import (
    DECISION_FRAME_SCHEMA_VERSION,
    PRECONDITION_ORDER_DIRECTION_RULE_ID,
)
from workflow_tests.test_request_decision_frame_generalized import (
    RegisteredScaleSignalProvider,
)

HEIGHT_QUESTION = "基準の次に身長が高いものはどれですか？"
BODY_WEIGHT_QUESTION = "基準の次に体重が重いものはどれですか？"
HEIGHT_ROWS = "低位：150cm\n基準：170cm\n高位：190cm\n"


class RequestDecisionFrameScalarSurfaceTests(unittest.TestCase):
    def test_arrangement_conditional_nara_binds_directly(self) -> None:
        result = self._audit("身長が高い順に並べるなら、" + HEIGHT_QUESTION)
        frame = self._frame(result)

        self.assertEqual(frame["status"], "direction_bound")
        self.assertEqual(
            frame["direction_binding"]["direction"],
            "scale_high_pole_first",
        )
        self.assertNotIn(
            PRECONDITION_ORDER_DIRECTION_RULE_ID,
            self._rule_ids(result),
        )
        self.assertEqual(
            result["details"]["decision_frame_summary"]["schema_version"],
            DECISION_FRAME_SCHEMA_VERSION,
        )
        validate(instance=result, schema=load_audit_result_schema())

    def test_explicit_ascending_and_descending_bind_every_registered_axis(self) -> None:
        cases = (
            ("昇", "scale_low_pole_first"),
            ("降", "scale_high_pole_first"),
        )
        for scale in SCALE_SPECS:
            for axis in scale.axes:
                for measure in axis.measure_terms:
                    question = (
                        f"基準の次に{measure}が"
                        f"{scale.canonical_high_term}ものはどれですか？"
                    )
                    for order_term, direction in cases:
                        text = f"{measure}の{order_term}順に並べたとき、{question}"
                        with self.subTest(
                            scale=scale.scale_id,
                            axis=axis.axis_id,
                            measure=measure,
                            order_term=order_term,
                        ):
                            result = self._audit(text)
                            frame = self._frame(result)
                            binding = frame["direction_binding"]
                            self.assertEqual(frame["status"], "direction_bound")
                            self.assertEqual(binding["direction"], direction)
                            self.assertEqual(
                                binding["accepted_evidence"][0]["order_axis_id"],
                                axis.axis_id,
                            )
                            self.assertEqual(
                                binding["accepted_evidence"][0]["axis_resolution"],
                                "explicit_measure",
                            )

    def test_ascending_and_descending_headers_require_an_explicit_axis(self) -> None:
        for scale in SCALE_SPECS:
            for axis in scale.axes:
                for measure in axis.measure_terms:
                    question = (
                        f"基準の次に{measure}が"
                        f"{scale.canonical_high_term}ものはどれですか？"
                    )
                    for order_term, direction in (
                        ("昇", "scale_low_pole_first"),
                        ("降", "scale_high_pole_first"),
                    ):
                        with self.subTest(
                            axis=axis.axis_id,
                            measure=measure,
                            order_term=order_term,
                        ):
                            result = self._audit(
                                f"{measure}の並び順：{order_term}順\n"
                                + HEIGHT_ROWS
                                + question
                            )
                            frame = self._frame(result)
                            self.assertEqual(frame["status"], "direction_bound")
                            self.assertEqual(
                                frame["direction_binding"]["direction"],
                                direction,
                            )

        for text in (
            "並び順：昇順\n" + HEIGHT_ROWS + HEIGHT_QUESTION,
            "並び順：降順\n" + HEIGHT_ROWS + HEIGHT_QUESTION,
            "標高の並び順：昇順\n" + HEIGHT_ROWS + HEIGHT_QUESTION,
            "身長の並び順：昇順\n" + HEIGHT_QUESTION,
            "身長の並び順：昇順\nX：150cm\nY：190cm\n" + HEIGHT_QUESTION,
        ):
            with self.subTest(text=text):
                frame = self._frame(self._audit(text))
                self.assertEqual(frame["status"], "direction_unbound")
                self.assertEqual(frame["direction_binding"]["status"], "missing")

    def test_pole_origin_surfaces_bind_every_registered_axis_and_term(self) -> None:
        for scale in SCALE_SPECS:
            for axis in scale.axes:
                for measure in axis.measure_terms:
                    question = (
                        f"基準の次に{measure}が"
                        f"{scale.canonical_high_term}ものはどれですか？"
                    )
                    families = (
                        (scale.high_terms, "ものから順に", "scale_high_pole_first"),
                        (scale.low_terms, "ものから順に", "scale_low_pole_first"),
                        (scale.high_terms, "方から", "scale_high_pole_first"),
                        (scale.low_terms, "方から", "scale_low_pole_first"),
                    )
                    for terms, suffix, direction in families:
                        for term in terms:
                            text = f"{measure}が{term}{suffix}並べたとき、{question}"
                            with self.subTest(
                                scale=scale.scale_id,
                                axis=axis.axis_id,
                                measure=measure,
                                term=term,
                                suffix=suffix,
                            ):
                                frame = self._frame(self._audit(text))
                                binding = frame["direction_binding"]
                                self.assertEqual(frame["status"], "direction_bound")
                                self.assertEqual(binding["direction"], direction)
                                self.assertEqual(
                                    binding["accepted_evidence"][0]["order_axis_id"],
                                    axis.axis_id,
                                )
                                self.assertEqual(
                                    binding["accepted_evidence"][0]["axis_resolution"],
                                    "explicit_measure",
                                )

    def test_bare_direction_surfaces_remain_unbound(self) -> None:
        cases = (
            "昇順に並べたとき、" + HEIGHT_QUESTION,
            "降順に並べたとき、" + HEIGHT_QUESTION,
            "高いものから順に並べたとき、" + HEIGHT_QUESTION,
            "重い方から並べたとき、" + BODY_WEIGHT_QUESTION,
        )
        for text in cases:
            with self.subTest(text=text):
                result = self._audit(text)
                frame = self._frame(result)
                self.assertEqual(frame["status"], "direction_unbound")
                self.assertEqual(frame["direction_binding"]["accepted_evidence"], [])
                self.assertIn(
                    PRECONDITION_ORDER_DIRECTION_RULE_ID,
                    self._rule_ids(result),
                )

    def test_new_surfaces_preserve_nonbinding_boundaries(self) -> None:
        cases = (
            (
                "標高の昇順に並べたとき、" + HEIGHT_QUESTION,
                "different_order_axis",
            ),
            (
                "体重の降順に並べたとき、" + HEIGHT_QUESTION,
                "different_scale",
            ),
            (
                "標高が高いものから順に並べたとき、" + HEIGHT_QUESTION,
                "different_order_axis",
            ),
            (
                "この3個を身長が高い順に並べるなら、この5個の中で、" + HEIGHT_QUESTION,
                "different_candidate_set",
            ),
            (
                "この3個を身長が高い方から並べるなら、"
                "この5個の中で、" + HEIGHT_QUESTION,
                "different_candidate_set",
            ),
            (
                "「身長が高いものから順」で並べたとき、" + HEIGHT_QUESTION,
                "quoted_or_code_example",
            ),
            (
                "「身長の降順」で並べたとき、" + HEIGHT_QUESTION,
                "quoted_or_code_example",
            ),
            (
                "身長の昇順に並べたときではなく、" + HEIGHT_QUESTION,
                "negated",
            ),
            (
                "身長が低いものから順に並べたときではなく、" + HEIGHT_QUESTION,
                "negated",
            ),
            (
                "身長が高い方から選ぶなら、" + HEIGHT_QUESTION,
                "unsupported_binding_form",
            ),
        )
        for text, reason in cases:
            with self.subTest(reason=reason, text=text):
                result = self._audit(text)
                frame = self._frame(result)
                binding = frame["direction_binding"]
                self.assertEqual(frame["status"], "direction_unbound")
                self.assertEqual(binding["accepted_evidence"], [])
                self.assertTrue(
                    any(
                        item.get("rejection_reasons") == [reason]
                        for item in binding["rejected_evidence"]
                    )
                )

    def test_historical_new_surface_does_not_become_a_live_frame(self) -> None:
        result = self._audit("旧版では身長が低い方から並べたとき、" + HEIGHT_QUESTION)
        summary = result["details"]["decision_frame_summary"]

        self.assertEqual(summary["status"], "not_applicable")
        self.assertEqual(summary["frames"], [])
        self.assertNotIn(
            PRECONDITION_ORDER_DIRECTION_RULE_ID,
            self._rule_ids(result),
        )

    def test_new_surface_conflict_uses_the_existing_primary_rule(self) -> None:
        text = (
            "身長の並び順：降順\n"
            + HEIGHT_ROWS
            + "身長が低いものから順に並べたとき、"
            + HEIGHT_QUESTION
        )
        result = self._audit(text)
        frame = self._frame(result)

        self.assertEqual(frame["status"], "direction_conflict")
        self.assertEqual(frame["direction_binding"]["status"], "conflict")
        self.assertEqual(len(frame["direction_binding"]["accepted_evidence"]), 2)
        self.assertIn(
            PRECONDITION_ORDER_DIRECTION_RULE_ID,
            self._rule_ids(result),
        )
        validate(instance=result, schema=load_audit_result_schema())

    @staticmethod
    def _audit(text: str) -> dict[str, object]:
        return audit_request(
            text,
            morphology_provider=RegisteredScaleSignalProvider(),
        )

    @staticmethod
    def _frame(result: dict[str, object]) -> dict[str, object]:
        return result["details"]["decision_frame_summary"]["frames"][0]

    @staticmethod
    def _rule_ids(result: dict[str, object]) -> set[str]:
        return {str(item.get("rule_id", "")) for item in result["findings"]}


if __name__ == "__main__":
    unittest.main()
