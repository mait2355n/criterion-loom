from __future__ import annotations

import re
import unittest
from copy import deepcopy

from jsonschema import ValidationError, validate

from semantic_guard_workflow.direction_spaces import DIRECTION_SPACE_SPECS
from semantic_guard_workflow.japanese_morphology import MorphologyUnavailableError
from semantic_guard_workflow.models import load_audit_result_schema
from semantic_guard_workflow.request_audit import audit_request
from semantic_guard_workflow.request_decision_frame import PRECONDITION_ORDER_DIRECTION_RULE_ID
from semantic_guard_workflow.request_direction_binding import (
    direction_binding_contract_violations,
)


class CharacterSignalProvider:
    """Source-aligned morphology signal sufficient for deterministic grammar tests."""

    def analyze(self, text: str) -> dict[str, object]:
        tokens: list[dict[str, object]] = []
        for match in re.finditer(r"体重|重い|軽い|\s+|.", text, re.DOTALL):
            surface = match.group(0)
            if surface.isspace():
                pos = ["空白", "*", "*", "*", "*", "*"]
            elif surface in "、，,。！？!?「」『』`":
                pos = ["補助記号", "*", "*", "*", "*", "*"]
            elif surface in {"の", "に", "へ", "で", "を", "は", "が", "と"}:
                pos = ["助詞", "格助詞", "*", "*", "*", "*"]
            else:
                pos = ["名詞", "普通名詞", "一般", "*", "*", "*"]
            tokens.append(
                {
                    "surface": surface,
                    "normalized": surface,
                    "lemma": surface,
                    "pos": pos,
                    "start": match.start(),
                    "end": match.end(),
                }
            )
        return {
            "provider_id": "character-signal-test",
            "provider_version": "1",
            "resource_version": "fixture",
            "split_mode": "C",
            "tokens": tokens,
        }


class UnavailableProvider:
    def analyze(self, text: str) -> dict[str, object]:
        raise MorphologyUnavailableError("fixture unavailable")


class RequestDirectionBindingTests(unittest.TestCase):
    CASES = (
        (
            "横一列",
            "左から右へ",
            "右から左へ",
            "horizontal_left_right",
            "left_to_right",
            "right_to_left",
        ),
        (
            "縦一列",
            "上から下へ",
            "下から上へ",
            "vertical_top_bottom",
            "top_to_bottom",
            "bottom_to_top",
        ),
        (
            "奥行き方向",
            "手前から奥へ",
            "奥から手前へ",
            "front_back",
            "front_to_back",
            "back_to_front",
        ),
        (
            "時系列",
            "過去から未来へ",
            "未来から過去へ",
            "past_future",
            "past_to_future",
            "future_to_past",
        ),
        (
            "円周上",
            "時計回りに",
            "反時計回りに",
            "clockwise_counterclockwise",
            "clockwise",
            "counterclockwise",
        ),
        (
            "経路上",
            "起点から終点へ",
            "終点から起点へ",
            "origin_destination",
            "origin_to_destination",
            "destination_to_origin",
        ),
    )

    def test_registry_has_six_distinct_two_direction_axes(self) -> None:
        axes = [spec.direction_axis_id for spec in DIRECTION_SPACE_SPECS]
        options = [
            option.option_id
            for spec in DIRECTION_SPACE_SPECS
            for option in spec.options
        ]

        self.assertEqual(len(axes), 6)
        self.assertEqual(len(set(axes)), 6)
        self.assertEqual(len(options), 12)
        self.assertEqual(len(set(options)), 12)
        self.assertTrue(all(len(spec.options) == 2 for spec in DIRECTION_SPACE_SPECS))

    def test_all_registered_domains_detect_missing_and_both_bound_directions(
        self,
    ) -> None:
        for basis, first, second, axis_id, first_id, second_id in self.CASES:
            with self.subTest(axis=axis_id, form="missing"):
                result = self._audit(f"{basis}で、Aの次の項目はどれですか？")
                frame = self._frame(result)
                self.assertEqual(frame["status"], "direction_unbound")
                self.assertEqual(frame["direction_binding"]["status"], "missing")
                self.assertEqual(
                    frame["direction_binding"]["search_scope"]["text_region"]["end"],
                    len(f"{basis}で、Aの次の項目はどれですか？"),
                )
                self.assertEqual(
                    frame["operation"]["direction_axis_id"],
                    axis_id,
                )
                self.assertIn(
                    PRECONDITION_ORDER_DIRECTION_RULE_ID,
                    self._rule_ids(result),
                )
                self.assertEqual(
                    len(self._decision_findings(result)),
                    1,
                )
            for surface, option_id in ((first, first_id), (second, second_id)):
                with self.subTest(axis=axis_id, direction=option_id):
                    result = self._audit(
                        f"{basis}を{surface}辿るとき、Aの次の項目はどれですか？"
                    )
                    frame = self._frame(result)
                    self.assertEqual(frame["status"], "direction_bound")
                    self.assertEqual(frame["direction_binding"]["direction"], option_id)
                    self.assertNotIn(
                        PRECONDITION_ORDER_DIRECTION_RULE_ID,
                        self._rule_ids(result),
                    )

    def test_binding_from_another_axis_is_rejected_and_does_not_close_gap(self) -> None:
        result = self._audit("横一列を上から下へ辿るとき、Aの次の項目はどれですか？")
        binding = self._frame(result)["direction_binding"]

        self.assertEqual(binding["status"], "missing")
        self.assertEqual(binding["accepted_evidence"], [])
        self.assertEqual(
            binding["rejected_evidence"][0]["rejection_reasons"],
            ["different_direction_axis"],
        )
        self.assertIn(PRECONDITION_ORDER_DIRECTION_RULE_ID, self._rule_ids(result))

    def test_two_opposed_directions_produce_one_conflict_finding(self) -> None:
        result = self._audit(
            "横一列を左から右へ又は右から左へ辿るとき、Aの次の項目はどれですか？"
        )
        frame = self._frame(result)

        self.assertEqual(frame["status"], "direction_conflict")
        self.assertEqual(frame["direction_binding"]["status"], "conflict")
        self.assertEqual(len(frame["direction_binding"]["accepted_evidence"]), 2)
        self.assertEqual(len(self._decision_findings(result)), 1)

    def test_unknown_direction_surface_is_indeterminate_not_actionable_gap(
        self,
    ) -> None:
        result = self._audit("円周上を右回りに辿るとき、Aの次の印はどれですか？")
        frame = self._frame(result)

        self.assertEqual(frame["status"], "direction_indeterminate")
        self.assertEqual(frame["direction_binding"]["status"], "indeterminate")
        self.assertEqual(self._decision_findings(result), [])
        traces = [
            item
            for item in result["details"]["non_emitted_rules"]
            if item.get("source") == "direction_binding_summary"
        ]
        self.assertEqual(traces[0]["emission_status"], "unknown")

    def test_negated_direction_is_rejected_without_inferring_its_opposite(self) -> None:
        result = self._audit(
            "円周上を時計回りではなく反時計回りに辿るとき、Aの次の印はどれですか？"
        )
        binding = self._frame(result)["direction_binding"]

        self.assertEqual(binding["status"], "bound")
        self.assertEqual(binding["direction"], "counterclockwise")
        self.assertEqual(
            binding["rejected_evidence"][0]["rejection_reasons"],
            ["negated"],
        )

    def test_negation_surface_variants_cannot_become_a_false_binding(self) -> None:
        for negator in ("ではなく", "でなく", "ではない", "でない", "、ではなく"):
            with self.subTest(negator=negator, opposite=False):
                result = self._audit(
                    f"横一列を左から右へ{negator}辿るとき、Aの次の項目はどれですか？"
                )
                binding = self._frame(result)["direction_binding"]
                self.assertEqual(binding["status"], "missing")
                self.assertEqual(binding["accepted_evidence"], [])
                self.assertEqual(
                    binding["rejected_evidence"][0]["rejection_reasons"],
                    ["negated"],
                )
                self.assertEqual(len(self._decision_findings(result)), 1)

            with self.subTest(negator=negator, opposite=True):
                result = self._audit(
                    f"横一列を左から右へ{negator}右から左へ辿るとき、"
                    "Aの次の項目はどれですか？"
                )
                binding = self._frame(result)["direction_binding"]
                self.assertEqual(binding["status"], "bound")
                self.assertEqual(binding["direction"], "right_to_left")
                self.assertEqual(len(binding["accepted_evidence"]), 1)
                self.assertEqual(len(binding["rejected_evidence"]), 1)
                self.assertEqual(self._decision_findings(result), [])

    def test_quoted_direction_is_rejected_without_hiding_the_live_gap(self) -> None:
        for quoted in (
            "「左から右へ」",
            '"左から右へ"',
            "`左から右へ`",
        ):
            with self.subTest(quoted=quoted):
                result = self._audit(
                    f"横一列を{quoted}辿るとき、Aの次の項目はどれですか？"
                )
                binding = self._frame(result)["direction_binding"]

                self.assertEqual(binding["status"], "missing")
                self.assertEqual(binding["accepted_evidence"], [])
                self.assertEqual(binding["unresolved_evidence"], [])
                self.assertEqual(
                    binding["rejected_evidence"][0]["rejection_reasons"],
                    ["quoted_or_code_example"],
                )
                self.assertEqual(len(self._decision_findings(result)), 1)

    def test_duplicate_same_direction_is_not_a_conflict(self) -> None:
        result = self._audit(
            "横一列を左から右へ又は左から右へ辿るとき、Aの次の項目はどれですか？"
        )
        binding = self._frame(result)["direction_binding"]

        self.assertEqual(binding["status"], "bound")
        self.assertEqual(binding["direction"], "left_to_right")
        self.assertEqual(len(binding["accepted_evidence"]), 2)

    def test_nearby_defaults_and_postposed_directions_do_not_bind(self) -> None:
        cases = (
            "通常は左から右へ進む。横一列で、Aの次の項目はどれですか？",
            "横一列で、Aの次の項目はどれですか？左から右へ辿る。",
        )
        for text in cases:
            with self.subTest(text=text):
                result = self._audit(text)
                frame = self._frame(result)
                self.assertEqual(frame["status"], "direction_unbound")
                self.assertEqual(frame["direction_binding"]["accepted_evidence"], [])

    def test_text_context_boundary_is_preserved_by_runtime_reconstruction(self) -> None:
        text = "横一列で、Aの次の項目はどれですか？"
        context = "候補一覧は別資料にある。"
        result = audit_request(
            text,
            context=context,
            morphology_provider=CharacterSignalProvider(),
        )
        summary = result["details"]["direction_binding_summary"]
        scope = summary["frames"][0]["direction_binding"]["search_scope"]

        self.assertEqual(summary["status"], "direction_unbound")
        self.assertEqual(scope["text_region"], {"start": 0, "end": len(text)})
        self.assertEqual(
            scope["context_region"],
            {"start": len(text) + 1, "end": len(text) + 1 + len(context)},
        )
        self.assertEqual(
            direction_binding_contract_violations(
                summary,
                f"{text}\n{context}",
                context_start=len(text) + 1,
            ),
            [],
        )

    def test_unregistered_direction_spaces_are_outside_the_closed_registry(
        self,
    ) -> None:
        for text in (
            "依存グラフで、Aの次の節点はどれですか？",
            "方位上で、Aの次の地点はどれですか？",
            "Aの次の項目はどれですか？",
        ):
            with self.subTest(text=text):
                result = self._audit(text)
                summary = result["details"]["direction_binding_summary"]
                self.assertEqual(summary["status"], "not_applicable")
                self.assertEqual(self._decision_findings(result), [])

    def test_multiple_direction_open_questions_fail_closed(self) -> None:
        result = self._audit(
            "横一列で、Aの次の項目はどれですか？時系列で、Bの次の事象はどれですか？"
        )
        summary = result["details"]["direction_binding_summary"]

        self.assertEqual(summary["status"], "indeterminate")
        self.assertEqual(summary["unknown_reasons"], ["multiple_questions"])
        self.assertEqual(summary["frames"], [])
        self.assertEqual(self._decision_findings(result), [])

    def test_quoted_metalinguistic_and_fenced_examples_do_not_emit(self) -> None:
        cases = (
            (
                "「横一列を左から右へ辿るとき、Aの次の項目はどれですか？」"
                "という表現を検出する。"
            ),
            "旧版では横一列を左から右へ辿るとき、Aの次の項目はどれですか？",
            "```text\n横一列で、Aの次の項目はどれですか？\n```",
        )
        for text in cases:
            with self.subTest(text=text):
                result = self._audit(text)
                summary = result["details"]["direction_binding_summary"]
                self.assertEqual(summary["status"], "not_applicable")
                self.assertEqual(self._decision_findings(result), [])

    def test_repairs_bind_without_candidate_results_or_numeric_evidence(self) -> None:
        original = self._audit("時系列で、Aの次の事象はどれですか？")
        frame = self._frame(original)

        self.assertEqual(frame["candidate_set_binding"]["status"], "not_required")
        self.assertNotIn("impact_evidence", frame)
        for candidate in frame["repair_candidates"]:
            with self.subTest(candidate=candidate):
                rerun = self._audit(candidate["rewrite"])
                rerun_frame = self._frame(rerun)
                self.assertEqual(rerun_frame["status"], "direction_bound")
                self.assertNotIn(
                    PRECONDITION_ORDER_DIRECTION_RULE_ID,
                    self._rule_ids(rerun),
                )

    def test_scalar_and_non_scalar_detectors_have_one_primary_emitter_each(
        self,
    ) -> None:
        scalar = self._audit("Cの次に体重が重い人は誰ですか？")
        directional = self._audit("横一列で、Aの次の項目はどれですか？")

        self.assertEqual(
            scalar["details"]["direction_binding_summary"]["status"],
            "not_applicable",
        )
        self.assertEqual(
            directional["details"]["decision_frame_summary"]["status"],
            "not_applicable",
        )
        self.assertEqual(len(self._decision_findings(scalar)), 1)
        self.assertEqual(len(self._decision_findings(directional)), 1)

    def test_provider_unavailability_is_indeterminate_without_gap_finding(self) -> None:
        result = audit_request(
            "横一列で、Aの次の項目はどれですか？",
            morphology_provider=UnavailableProvider(),
        )
        summary = result["details"]["direction_binding_summary"]

        self.assertEqual(summary["status"], "indeterminate")
        self.assertEqual(summary["frames"], [])
        self.assertEqual(self._decision_findings(result), [])

    def test_v1_schema_rejects_state_and_domain_mutations(self) -> None:
        schema = load_audit_result_schema()
        unbound = self._audit("横一列で、Aの次の項目はどれですか？")
        bound = self._audit("横一列を左から右へ辿るとき、Aの次の項目はどれですか？")
        unknown = self._audit("円周上を右回りに辿るとき、Aの次の印はどれですか？")
        validate(instance=unbound, schema=schema)
        validate(instance=bound, schema=schema)
        validate(instance=unknown, schema=schema)

        missing_with_accepted = deepcopy(unbound)
        self._frame(missing_with_accepted)["direction_binding"]["accepted_evidence"] = (
            deepcopy(self._frame(bound)["direction_binding"]["accepted_evidence"])
        )
        bound_without_direction = deepcopy(bound)
        del self._frame(bound_without_direction)["direction_binding"]["direction"]
        bound_with_unresolved = deepcopy(bound)
        self._frame(bound_with_unresolved)["direction_binding"][
            "unresolved_evidence"
        ] = deepcopy(self._frame(unknown)["direction_binding"]["unresolved_evidence"])
        wrong_domain = deepcopy(bound)
        self._frame(wrong_domain)["operation"]["direction_axis_id"] = "past_future"
        unknown_without_evidence = deepcopy(unknown)
        self._frame(unknown_without_evidence)["direction_binding"][
            "unresolved_evidence"
        ] = []
        missing_search_scope = deepcopy(bound)
        del self._frame(missing_search_scope)["direction_binding"]["search_scope"][
            "target_clause_span"
        ]
        missing_relation_span = deepcopy(bound)
        del self._frame(missing_relation_span)["direction_binding"][
            "accepted_evidence"
        ][0]["relation_span"]
        forged_direction_span = deepcopy(bound)
        self._frame(forged_direction_span)["source_span"]["forged"] = 1
        unavailable_with_frame = deepcopy(bound)
        unavailable_with_frame["details"]["direction_binding_summary"]["morphology"][
            "status"
        ] = "unavailable"
        forged_reference_lemma = deepcopy(bound)
        self._frame(forged_reference_lemma)["morphology_signal"]["reference"]["tokens"][
            0
        ]["lemma"] = "偽補題"

        for invalid in (
            missing_with_accepted,
            bound_without_direction,
            bound_with_unresolved,
            wrong_domain,
            unknown_without_evidence,
            missing_search_scope,
            missing_relation_span,
            forged_direction_span,
            unavailable_with_frame,
            forged_reference_lemma,
        ):
            with self.subTest(invalid=invalid), self.assertRaises(ValidationError):
                validate(instance=invalid, schema=schema)

    def test_runtime_contract_checks_source_local_equalities(self) -> None:
        text = "横一列を左から右へ辿るとき、Aの次の項目はどれですか？"
        result = self._audit(text)
        summary = result["details"]["direction_binding_summary"]
        self.assertEqual(direction_binding_contract_violations(summary, text), [])

        mutated = deepcopy(summary)
        mutated["frames"][0]["direction_binding"]["required_constraint"][
            "direction_basis_id"
        ] = "direction-basis:1:2"
        self.assertIn(
            "direction_basis_id_mismatch",
            direction_binding_contract_violations(mutated, text),
        )

    def test_runtime_contract_rebinds_claims_to_source_grammar(self) -> None:
        schema = load_audit_result_schema()
        text = "横一列を左から右へ辿るとき、Aの次の項目はどれですか？"
        bound = self._audit(text)

        reversed_direction = deepcopy(bound)
        reversed_binding = self._frame(reversed_direction)["direction_binding"]
        reversed_binding["direction"] = "right_to_left"
        reversed_binding["accepted_evidence"][0]["value"] = "right_to_left"

        changed_domain = deepcopy(bound)
        changed_frame = self._frame(changed_domain)
        changed_frame["direction_open_expression"].update(
            {
                "direction_domain_id": "temporal_sequence",
                "direction_axis_id": "past_future",
                "direction_options": ["past_to_future", "future_to_past"],
            }
        )
        changed_frame["operation"].update(
            {
                "direction_domain_id": "temporal_sequence",
                "direction_axis_id": "past_future",
            }
        )
        changed_binding = changed_frame["direction_binding"]
        changed_binding["direction"] = "past_to_future"
        changed_binding["required_constraint"].update(
            {
                "direction_domain_id": "temporal_sequence",
                "direction_axis_id": "past_future",
                "allowed_directions": ["past_to_future", "future_to_past"],
            }
        )
        changed_binding["accepted_evidence"][0].update(
            {
                "direction_domain_id": "temporal_sequence",
                "direction_axis_id": "past_future",
                "value": "past_to_future",
            }
        )
        changed_frame["evaluations"][0]["candidate_conditions"] = [
            "past_to_future",
            "future_to_past",
        ]

        moved_basis = deepcopy(bound)
        moved_frame = self._frame(moved_basis)
        moved_frame["direction_open_expression"]["direction_basis_span"] = {
            "start": 4,
            "end": 9,
            "excerpt": "左から右へ",
        }
        for owner in (
            moved_frame["direction_open_expression"],
            moved_frame["operation"],
            moved_frame["direction_binding"]["required_constraint"],
            moved_frame["direction_binding"]["accepted_evidence"][0],
        ):
            owner["direction_basis_id"] = "direction-basis:4:9"

        moved_evidence = deepcopy(bound)
        self._frame(moved_evidence)["direction_binding"]["accepted_evidence"][0][
            "source_span"
        ] = {"start": 0, "end": 3, "excerpt": "横一列"}

        for attacked in (
            reversed_direction,
            changed_domain,
            moved_basis,
            moved_evidence,
        ):
            with self.subTest(attacked=attacked):
                validate(instance=attacked, schema=schema)
                summary = attacked["details"]["direction_binding_summary"]
                self.assertIn(
                    "direction_binding_not_source_reproducible",
                    direction_binding_contract_violations(summary, text),
                )

        wrong_axis_text = "横一列を上から下へ辿るとき、Aの次の項目はどれですか？"
        relabeled_rejection = self._audit(wrong_axis_text)
        rejected = self._frame(relabeled_rejection)["direction_binding"][
            "rejected_evidence"
        ][0]
        rejected.update(
            {
                "direction_domain_id": "temporal_sequence",
                "direction_axis_id": "past_future",
                "value": "past_to_future",
            }
        )
        validate(instance=relabeled_rejection, schema=schema)
        self.assertIn(
            "direction_binding_not_source_reproducible",
            direction_binding_contract_violations(
                relabeled_rejection["details"]["direction_binding_summary"],
                wrong_axis_text,
            ),
        )

    def test_runtime_contract_rechecks_source_wide_nonbinding_gates(self) -> None:
        text = "横一列で、Aの次の項目はどれですか？"
        summary = self._audit(text)["details"]["direction_binding_summary"]

        appended_question = f"{text}時系列で、Bの次の事象はどれですか？"
        self.assertIn(
            "canonical_multiple_questions",
            direction_binding_contract_violations(summary, appended_question),
        )

        metalinguistic = f"{text}という表現を検出する。"
        self.assertIn(
            "canonical_nonbinding_source_frame",
            direction_binding_contract_violations(summary, metalinguistic),
        )

        command_suffix = "時系列で、Bの次の事象を選ぶ。"
        padded_source = f"{text}{'補' * len(command_suffix)}"
        padded_summary = self._audit(padded_source)["details"][
            "direction_binding_summary"
        ]
        same_length_two_commands = f"{text}{command_suffix}"
        self.assertEqual(len(padded_source), len(same_length_two_commands))
        self.assertIn(
            "canonical_candidate_operation_count",
            direction_binding_contract_violations(
                padded_summary,
                same_length_two_commands,
            ),
        )

    def test_runtime_contract_rejects_fenced_frame_relocation(self) -> None:
        text = "横一列で、Aの次の項目を選ぶ。"
        prefix = "```text\n"
        suffix = "\n```"
        padded_source = f"{text}{'補' * (len(prefix) + len(suffix))}"
        summary = deepcopy(
            self._audit(padded_source)["details"]["direction_binding_summary"]
        )
        self._shift_one_frame_summary(summary, len(prefix))
        fenced_source = f"{prefix}{text}{suffix}"

        self.assertEqual(len(padded_source), len(fenced_source))
        self.assertIn(
            "canonical_fenced_source_frame",
            direction_binding_contract_violations(summary, fenced_source),
        )

    def test_runtime_contract_requires_executed_morphology_provenance(self) -> None:
        text = "横一列を左から右へ辿るとき、Aの次の項目はどれですか？"
        summary = deepcopy(self._audit(text)["details"]["direction_binding_summary"])
        summary["morphology"] = {
            "status": "unavailable",
            "authority": "signal_only",
            "provider_id": "forged",
        }

        violations = direction_binding_contract_violations(summary, text)
        self.assertIn("canonical_morphology_not_executed", violations)

    @staticmethod
    def _audit(text: str) -> dict[str, object]:
        return audit_request(text, morphology_provider=CharacterSignalProvider())

    @staticmethod
    def _frame(result: dict[str, object]) -> dict[str, object]:
        return result["details"]["direction_binding_summary"]["frames"][0]

    @staticmethod
    def _rule_ids(result: dict[str, object]) -> set[str]:
        return {
            str(item.get("rule_id"))
            for item in result["findings"]
            if item.get("rule_id")
        }

    @staticmethod
    def _decision_findings(result: dict[str, object]) -> list[dict[str, object]]:
        return [
            item
            for item in result["findings"]
            if item.get("rule_id") == PRECONDITION_ORDER_DIRECTION_RULE_ID
        ]

    @staticmethod
    def _shift_one_frame_summary(summary: dict[str, object], delta: int) -> None:
        frame = summary["frames"][0]

        def shift_span(span: dict[str, object]) -> None:
            span["start"] += delta
            span["end"] += delta

        shift_span(frame["source_span"])
        frame["frame_id"] = (
            f"direction-binding:{frame['source_span']['start']}:"
            f"{frame['source_span']['end']}"
        )
        expression = frame["direction_open_expression"]
        shift_span(expression["source_span"])
        shift_span(expression["direction_basis_span"])
        basis_id = (
            f"direction-basis:{expression['direction_basis_span']['start']}:"
            f"{expression['direction_basis_span']['end']}"
        )
        expression["direction_basis_id"] = basis_id

        operation = frame["operation"]
        operation["direction_basis_id"] = basis_id
        reference = frame["morphology_signal"]["reference"]
        reference["start"] += delta
        reference["end"] += delta
        for token in reference["tokens"]:
            token["start"] += delta
            token["end"] += delta
        next_signal = frame["morphology_signal"]["next"]
        next_signal["start"] += delta
        next_signal["end"] += delta
        operation["reference_member_key"] = (
            f"source-member:{reference['start']}:{reference['end']}"
        )

        binding = frame["direction_binding"]
        binding["required_constraint"]["direction_basis_id"] = basis_id
        shift_span(binding["search_scope"]["target_clause_span"])
        for collection in (
            binding["accepted_evidence"],
            binding["rejected_evidence"],
            binding["unresolved_evidence"],
        ):
            for evidence in collection:
                evidence["direction_basis_id"] = basis_id
                shift_span(evidence["source_span"])
                if "relation_span" in evidence:
                    shift_span(evidence["relation_span"])


if __name__ == "__main__":
    unittest.main()
