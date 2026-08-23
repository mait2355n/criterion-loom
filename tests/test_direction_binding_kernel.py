from __future__ import annotations

import re
import unittest
from collections.abc import Iterable, Mapping

from semantic_guard.decision_frame_scales import (
    NUMERIC_PROJECTION_SPECS,
    SCALE_SPECS,
    all_comparison_terms,
    all_measure_terms,
    numeric_projection_for_scale,
)
from semantic_guard.direction_binding_core import resolve_direction_binding
from semantic_guard.direction_spaces import (
    DIRECTION_SPACE_SPECS,
    direction_axis_ids,
    direction_option_ids,
)
from semantic_guard.request_decision_frame import audit_precondition_sufficiency
from semantic_guard.request_direction_binding import (
    audit_direction_binding_sufficiency,
)


_COMPARISON_TERMS = frozenset(all_comparison_terms())
_TOKEN_TERMS = tuple(
    sorted(
        {*all_measure_terms(), *_COMPARISON_TERMS, "基準", "次"},
        key=lambda value: (-len(value), value),
    )
)
_TOKEN_RE = re.compile(
    "|".join(re.escape(term) for term in _TOKEN_TERMS) + r"|\s+|.",
    re.DOTALL,
)
_PARTICLES = frozenset({"の", "に", "が", "は", "を", "で", "と", "へ", "か"})
_PUNCTUATION = frozenset("、，,。！？!?\"「」『』`：:")


def _fake_ir(text: str) -> dict[str, object]:
    """Build the smallest source-aligned morphology IR used by both detectors."""

    tokens: list[dict[str, object]] = []
    for match in _TOKEN_RE.finditer(text):
        surface = match.group(0)
        if surface.isspace():
            primary_pos = "空白"
        elif surface in _COMPARISON_TERMS:
            primary_pos = "形容詞"
        elif surface in _PARTICLES:
            primary_pos = "助詞"
        elif surface in _PUNCTUATION:
            primary_pos = "補助記号"
        else:
            primary_pos = "名詞"
        tokens.append(
            {
                "surface": surface,
                "normalized": surface,
                "lemma": surface,
                "pos": [primary_pos, "*", "*", "*", "*", "*"],
                "start": match.start(),
                "end": match.end(),
            }
        )
    return {
        "text": text,
        "context": "",
        "source_text": text,
        "attempts": [
            {
                "stage": "morphology",
                "status": "executed",
                "authority": "signal_only",
                "provider_id": "direction-binding-kernel-test",
                "provider_version": "1",
                "resource_version": "fixture",
                "split_mode": "C",
                "diagnostics": [],
            }
        ],
        "supports": [
            {
                "tier": "morphology",
                "authority": "signal_only",
                "metadata": {"tokens": tokens},
            }
        ],
    }


def _frame(summary: Mapping[str, object]) -> Mapping[str, object]:
    frames = summary["frames"]
    if not isinstance(frames, list) or len(frames) != 1:
        raise AssertionError(f"expected exactly one frame: {frames!r}")
    frame = frames[0]
    if not isinstance(frame, Mapping):
        raise AssertionError(f"frame is not a mapping: {frame!r}")
    return frame


def _binding(frame: Mapping[str, object]) -> Mapping[str, object]:
    binding = frame["direction_binding"]
    if not isinstance(binding, Mapping):
        raise AssertionError(f"binding is not a mapping: {binding!r}")
    return binding


def _primary_eligible_count(summaries: Iterable[Mapping[str, object]]) -> int:
    count = 0
    for summary in summaries:
        frames = summary.get("frames", [])
        if not isinstance(frames, list):
            continue
        for frame in frames:
            if not isinstance(frame, Mapping):
                continue
            evaluations = frame.get("evaluations", [])
            if not isinstance(evaluations, list):
                continue
            count += sum(
                1
                for evaluation in evaluations
                if isinstance(evaluation, Mapping)
                and evaluation.get("finding_eligible") is True
            )
    return count


class DirectionBindingKernelTests(unittest.TestCase):
    def test_registries_close_over_the_expected_denominators(self) -> None:
        scalar_axes = [axis for scale in SCALE_SPECS for axis in scale.axes]
        scalar_axis_ids = [axis.axis_id for axis in scalar_axes]
        projected_scales = {
            scale.scale_id
            for scale in SCALE_SPECS
            if numeric_projection_for_scale(scale) is not None
        }

        self.assertEqual(len(SCALE_SPECS), 14)
        self.assertEqual(len(scalar_axes), 49)
        self.assertEqual(len(set(scalar_axis_ids)), 49)
        self.assertEqual(len(all_measure_terms()), 56)
        self.assertEqual(len(NUMERIC_PROJECTION_SPECS), 13)
        self.assertEqual(len(projected_scales), 13)
        self.assertEqual(
            projected_scales | {"rating"},
            {scale.scale_id for scale in SCALE_SPECS},
        )

        self.assertEqual(len(DIRECTION_SPACE_SPECS), 6)
        self.assertEqual(len(direction_axis_ids()), 6)
        self.assertEqual(len(set(direction_axis_ids())), 6)
        self.assertEqual(len(direction_option_ids()), 12)
        self.assertEqual(len(set(direction_option_ids())), 12)
        self.assertTrue(all(len(spec.options) == 2 for spec in DIRECTION_SPACE_SPECS))

    def test_pure_kernel_is_domain_neutral_and_fail_closed(self) -> None:
        first = {"value": "forward"}
        duplicate = {"value": "forward"}
        opposite = {"value": "backward"}

        self.assertEqual(resolve_direction_binding([]).status, "missing")
        bound = resolve_direction_binding([first])
        self.assertEqual((bound.status, bound.selected_direction), ("bound", "forward"))
        duplicate_bound = resolve_direction_binding([first, duplicate])
        self.assertEqual(
            (duplicate_bound.status, duplicate_bound.selected_direction),
            ("bound", "forward"),
        )
        conflict = resolve_direction_binding([first, opposite])
        self.assertEqual(
            (conflict.status, conflict.reason),
            ("conflict", "multiple_directions"),
        )
        unresolved = resolve_direction_binding(
            [first],
            unresolved_evidence=[{"value": ""}],
        )
        self.assertEqual(
            (unresolved.status, unresolved.reason),
            ("indeterminate", "direction_evidence_unresolved"),
        )

    def test_every_scalar_axis_detects_missing_and_both_bindings(self) -> None:
        visited_axes: set[str] = set()
        for scale in SCALE_SPECS:
            for axis in scale.axes:
                visited_axes.add(axis.axis_id)
                measure = axis.measure_terms[0]
                question = (
                    f"基準の次に{measure}が{scale.canonical_high_term}"
                    "ものはどれですか？"
                )
                with self.subTest(axis=axis.axis_id, binding="missing"):
                    summary = audit_precondition_sufficiency(_fake_ir(question))
                    frame = _frame(summary)
                    self.assertEqual(summary["status"], "direction_unbound")
                    self.assertEqual(frame["status"], "direction_unbound")
                    self.assertEqual(frame["operation"]["order_axis_id"], axis.axis_id)
                    self.assertEqual(_binding(frame)["status"], "missing")

                for term, expected in (
                    (scale.canonical_high_term, "scale_high_pole_first"),
                    (scale.canonical_low_term, "scale_low_pole_first"),
                ):
                    text = f"{measure}が{term}順に並べたとき、{question}"
                    with self.subTest(axis=axis.axis_id, binding=expected):
                        summary = audit_precondition_sufficiency(_fake_ir(text))
                        frame = _frame(summary)
                        binding = _binding(frame)
                        self.assertEqual(summary["status"], "direction_bound")
                        self.assertEqual(frame["status"], "direction_bound")
                        self.assertEqual(binding["status"], "bound")
                        self.assertEqual(binding["direction"], expected)
                        self.assertEqual(
                            binding["accepted_evidence"][0]["order_axis_id"],
                            axis.axis_id,
                        )

        self.assertEqual(len(visited_axes), 49)

    def test_cross_axis_evidence_is_rejected_for_both_detectors(self) -> None:
        scalar = audit_precondition_sufficiency(
            _fake_ir(
                "標高が高い順に並べたとき、"
                "基準の次に身長が高いものはどれですか？"
            )
        )
        scalar_binding = _binding(_frame(scalar))
        self.assertEqual(scalar_binding["status"], "missing")
        self.assertEqual(scalar_binding["accepted_evidence"], [])
        self.assertIn(
            ["different_order_axis"],
            [item["rejection_reasons"] for item in scalar_binding["rejected_evidence"]],
        )

        directional = audit_direction_binding_sufficiency(
            _fake_ir(
                "横一列を上から下へ辿るとき、"
                "Aの次の項目はどれですか？"
            )
        )
        directional_binding = _binding(_frame(directional))
        self.assertEqual(directional_binding["status"], "missing")
        self.assertEqual(directional_binding["accepted_evidence"], [])
        self.assertEqual(
            directional_binding["rejected_evidence"][0]["rejection_reasons"],
            ["different_direction_axis"],
        )

    def test_all_non_scalar_axes_detect_missing_and_both_directions(self) -> None:
        visited_directions: set[str] = set()
        for spec in DIRECTION_SPACE_SPECS:
            basis = spec.basis_terms[0]
            missing_text = f"{basis}で、Aの次の項目はどれですか？"
            with self.subTest(axis=spec.direction_axis_id, binding="missing"):
                summary = audit_direction_binding_sufficiency(_fake_ir(missing_text))
                frame = _frame(summary)
                self.assertEqual(summary["status"], "direction_unbound")
                self.assertEqual(
                    frame["operation"]["direction_axis_id"],
                    spec.direction_axis_id,
                )
                self.assertEqual(_binding(frame)["status"], "missing")

            for option in spec.options:
                visited_directions.add(option.option_id)
                text = (
                    f"{basis}を{option.canonical_surface}辿るとき、"
                    "Aの次の項目はどれですか？"
                )
                with self.subTest(
                    axis=spec.direction_axis_id,
                    binding=option.option_id,
                ):
                    summary = audit_direction_binding_sufficiency(_fake_ir(text))
                    frame = _frame(summary)
                    binding = _binding(frame)
                    self.assertEqual(summary["status"], "direction_bound")
                    self.assertEqual(binding["status"], "bound")
                    self.assertEqual(binding["direction"], option.option_id)

        self.assertEqual(visited_directions, set(direction_option_ids()))

    def test_non_scalar_conflict_duplicate_and_nonbinding_boundaries(self) -> None:
        cases = (
            (
                "conflict",
                "横一列を左から右へ又は右から左へ辿るとき、"
                "Aの次の項目はどれですか？",
                "conflict",
                2,
                None,
            ),
            (
                "duplicate",
                "横一列を左から右へ又は左から右へ辿るとき、"
                "Aの次の項目はどれですか？",
                "bound",
                2,
                None,
            ),
            (
                "unknown",
                "円周上を右回りに辿るとき、"
                "Aの次の印はどれですか？",
                "indeterminate",
                0,
                None,
            ),
            (
                "negated",
                "横一列を左から右へではなく辿るとき、"
                "Aの次の項目はどれですか？",
                "missing",
                0,
                "negated",
            ),
            (
                "quoted",
                "横一列を「左から右へ」辿るとき、"
                "Aの次の項目はどれですか？",
                "missing",
                0,
                "quoted_or_code_example",
            ),
            (
                "postposed",
                "横一列で、Aの次の項目はどれですか？"
                "左から右へ辿る。",
                "missing",
                0,
                None,
            ),
            (
                "default",
                "通常は左から右へ進む。"
                "横一列で、Aの次の項目はどれですか？",
                "missing",
                0,
                None,
            ),
        )
        for name, text, expected_status, accepted_count, rejection_reason in cases:
            with self.subTest(case=name):
                summary = audit_direction_binding_sufficiency(_fake_ir(text))
                binding = _binding(_frame(summary))
                self.assertEqual(binding["status"], expected_status)
                self.assertEqual(len(binding["accepted_evidence"]), accepted_count)
                if rejection_reason is not None:
                    self.assertEqual(
                        binding["rejected_evidence"][0]["rejection_reasons"],
                        [rejection_reason],
                    )
        conflict = _binding(
            _frame(audit_direction_binding_sufficiency(_fake_ir(cases[0][1])))
        )
        self.assertEqual(conflict["reason"], "multiple_traversal_directions")
        duplicate = _binding(
            _frame(audit_direction_binding_sufficiency(_fake_ir(cases[1][1])))
        )
        self.assertEqual(duplicate["direction"], "left_to_right")
        unknown = _binding(
            _frame(audit_direction_binding_sufficiency(_fake_ir(cases[2][1])))
        )
        self.assertEqual(
            unknown["unknown_reasons"],
            ["direction_evidence_unresolved"],
        )
        self.assertEqual(len(unknown["unresolved_evidence"]), 1)

    def test_numeric_projection_cannot_change_the_primary_scalar_judgment(self) -> None:
        question = (
            "この5人の中で、Cの次に体重が重い人は誰ですか？"
        )
        rows = "A：50kg\nB：60kg\nC：70kg\nD：80kg\nE：90kg\n"
        without_numeric = audit_precondition_sufficiency(_fake_ir(question))
        with_numeric = audit_precondition_sufficiency(_fake_ir(rows + question))
        plain_frame = _frame(without_numeric)
        numeric_frame = _frame(with_numeric)

        self.assertNotIn("impact_evidence", plain_frame)
        self.assertEqual(
            numeric_frame["impact_evidence"]["status"],
            "outcome_divergent",
        )
        self.assertIs(
            numeric_frame["impact_evidence"]["affects_primary_finding"],
            False,
        )
        self.assertEqual(without_numeric["status"], with_numeric["status"])
        for key in ("status", "missing_conditions", "evaluations"):
            self.assertEqual(plain_frame[key], numeric_frame[key])
        self.assertEqual(
            _binding(plain_frame)["status"],
            _binding(numeric_frame)["status"],
        )

    def test_detectors_have_at_most_one_primary_emitter(self) -> None:
        texts = (
            "基準の次に体重が重いものはどれですか？",
            "体重が重い順に並べたとき、"
            "基準の次に体重が重いものはどれですか？",
            "横一列で、Aの次の項目はどれですか？",
            "横一列を左から右へ辿るとき、"
            "Aの次の項目はどれですか？",
        )
        for text in texts:
            with self.subTest(text=text):
                semantic_ir = _fake_ir(text)
                scalar = audit_precondition_sufficiency(semantic_ir)
                non_scalar = audit_direction_binding_sufficiency(semantic_ir)
                self.assertLessEqual(
                    _primary_eligible_count((scalar, non_scalar)),
                    1,
                )
                self.assertLessEqual(
                    sum(bool(summary["frames"]) for summary in (scalar, non_scalar)),
                    1,
                )


if __name__ == "__main__":
    unittest.main()
