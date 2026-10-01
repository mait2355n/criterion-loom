from __future__ import annotations

import re
import unittest
from copy import deepcopy

from jsonschema import ValidationError, validate

from semantic_guard_workflow.japanese_morphology import MorphologyUnavailableError
from semantic_guard_workflow.models import load_audit_result_schema
from semantic_guard_workflow.request_audit import audit_request
from semantic_guard_workflow.request_decision_frame import (
    PRECONDITION_ORDER_DIRECTION_RULE_ID,
    PRECONDITION_OUTCOME_RULE_ID,
)
from semantic_guard_workflow.semantic_assertions import extract_semantic_assertions

ROWS = "A：50kg\nB：60kg\nC：70kg\nD：80kg\nE：90kg\n"
QUESTION = "この5人の中で、Cの次に体重が重い人は誰でしょうか？"


class SignalProvider:
    _TOKEN_RE = re.compile(r"体重|重い|軽い|次|誰|人|者|の|に|が|[A-Za-z]")

    def __init__(self, *, invalid_surface: bool = False, reverse: bool = False) -> None:
        self.invalid_surface = invalid_surface
        self.reverse = reverse
        self.calls = 0

    def analyze(self, text: str) -> dict[str, object]:
        self.calls += 1
        tokens: list[dict[str, object]] = []
        for match in self._TOKEN_RE.finditer(text):
            surface = match.group(0)
            if surface in {"重い", "軽い"}:
                pos = ["形容詞", "一般", "*", "*", "形容詞", "連体形-一般"]
            elif surface in {"の", "に", "が"}:
                pos = ["助詞", "格助詞", "*", "*", "*", "*"]
            elif surface == "誰":
                pos = ["代名詞", "*", "*", "*", "*", "*"]
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
        if self.invalid_surface:
            target = next(item for item in tokens if item["surface"] == "重い")
            target["surface"] = "軽い"
        if self.reverse:
            tokens.reverse()
        return {
            "provider_id": "test-morphology",
            "provider_version": "1",
            "resource_version": "fixture",
            "split_mode": "C",
            "tokens": tokens,
        }


class UnavailableProvider:
    def analyze(self, text: str) -> dict[str, object]:
        raise MorphologyUnavailableError("test provider unavailable")


class RequestDecisionFrameTests(unittest.TestCase):
    def test_direction_gap_is_primary_with_or_without_numeric_evidence(self) -> None:
        cases = [
            (QUESTION, None),
            (ROWS + QUESTION, "outcome_divergent"),
            (ROWS.replace("B：60kg", "B：約60kg") + QUESTION, None),
        ]
        signatures: list[tuple[object, ...]] = []
        for text, impact_status in cases:
            with self.subTest(impact_status=impact_status):
                result = self._audit(text)
                frame = self._frame(result)
                finding = self._decision_finding(result)
                self.assertEqual(frame["status"], "direction_unbound")
                self.assertEqual(frame["direction_binding"]["status"], "missing")
                if impact_status is None:
                    self.assertNotIn("impact_evidence", frame)
                    self.assertNotIn("impact_evidence", finding["derivation"])
                else:
                    self.assertEqual(frame["impact_evidence"]["status"], impact_status)
                    self.assertFalse(frame["impact_evidence"]["affects_primary_finding"])
                self.assertNotIn("impact_evidence", finding["derivation"])
                self.assertIn("order_direction", result["missing"])
                signatures.append(
                    (
                        finding["rule_id"],
                        finding["match_status"],
                        finding["confidence"],
                        finding["warning_class"],
                    )
                )
        self.assertEqual(len(set(signatures)), 1)
        self.assertNotIn(PRECONDITION_OUTCOME_RULE_ID, self._all_rule_ids(cases[1][0]))

    def test_numeric_counterfactuals_remain_auxiliary_witnesses(self) -> None:
        result = self._audit(ROWS + QUESTION)
        impact = self._frame(result)["impact_evidence"]

        self.assertEqual(impact["status"], "outcome_divergent")
        self.assertFalse(impact["outcome_invariant"])
        self.assertEqual(
            [item["outcome"]["entity_id"] for item in impact["candidate_frames"]],
            ["B", "D"],
        )
        validate(instance=result, schema=load_audit_result_schema())

    def test_v3_schema_rejects_inconsistent_direction_binding_states(self) -> None:
        schema = load_audit_result_schema()
        unbound = self._audit(QUESTION)
        bound = self._audit("体重が重い順に並べたとき、" + QUESTION)
        validate(instance=unbound, schema=schema)
        validate(instance=bound, schema=schema)

        inconsistent_evaluation = deepcopy(unbound)
        evaluation = self._frame(inconsistent_evaluation)["evaluations"][0]
        evaluation.update(
            {"status": "satisfied", "finding_eligible": False, "confidence": "high"}
        )
        accepted_nonbinding = deepcopy(bound)
        self._frame(accepted_nonbinding)["direction_binding"]["accepted_evidence"][0][
            "relation"
        ] = "nonbinding"
        bound_direction_mismatch = deepcopy(bound)
        self._frame(bound_direction_mismatch)["direction_binding"]["direction"] = (
            "scale_low_pole_first"
        )
        bound_without_direction = deepcopy(bound)
        del self._frame(bound_without_direction)["direction_binding"]["direction"]

        open_expression_scale_mismatch = deepcopy(bound)
        self._frame(open_expression_scale_mismatch)["direction_open_expression"][
            "scale_id"
        ] = "height"
        operation_scale_mismatch = deepcopy(bound)
        self._frame(operation_scale_mismatch)["operation"]["scale_id"] = "height"
        required_constraint_scale_mismatch = deepcopy(bound)
        self._frame(required_constraint_scale_mismatch)["direction_binding"][
            "required_constraint"
        ]["scale_id"] = "height"
        accepted_evidence_scale_mismatch = deepcopy(bound)
        self._frame(accepted_evidence_scale_mismatch)["direction_binding"][
            "accepted_evidence"
        ][0]["scale_id"] = "height"
        open_expression_axis_mismatch = deepcopy(bound)
        self._frame(open_expression_axis_mismatch)["direction_open_expression"][
            "order_axis_id"
        ] = "stature"
        operation_axis_mismatch = deepcopy(bound)
        self._frame(operation_axis_mismatch)["operation"]["order_axis_id"] = "stature"
        required_constraint_axis_mismatch = deepcopy(bound)
        self._frame(required_constraint_axis_mismatch)["direction_binding"][
            "required_constraint"
        ]["order_axis_id"] = "stature"
        accepted_evidence_axis_mismatch = deepcopy(bound)
        self._frame(accepted_evidence_axis_mismatch)["direction_binding"][
            "accepted_evidence"
        ][0]["order_axis_id"] = "stature"
        accepted_evidence_unresolved_axis = deepcopy(bound)
        self._frame(accepted_evidence_unresolved_axis)["direction_binding"][
            "accepted_evidence"
        ][0]["axis_resolution"] = "unresolved"
        accepted_evidence_unknown_site = deepcopy(bound)
        self._frame(accepted_evidence_unknown_site)["direction_binding"][
            "accepted_evidence"
        ][0]["binding_site"] = "invented_binding_site"
        accepted_evidence_with_rejection = deepcopy(bound)
        self._frame(accepted_evidence_with_rejection)["direction_binding"][
            "accepted_evidence"
        ][0]["rejection_reasons"] = ["different_order_axis"]
        accepted_evidence_rejected_only_site = deepcopy(bound)
        self._frame(accepted_evidence_rejected_only_site)["direction_binding"][
            "accepted_evidence"
        ][0]["binding_site"] = "target_clause"
        comparison_pole_mismatch = deepcopy(bound)
        self._frame(comparison_pole_mismatch)["operation"]["comparison_pole"] = "low"
        operation_measure_mismatch = deepcopy(bound)
        self._frame(operation_measure_mismatch)["operation"]["measure"] = "標高"
        axis_scale_pair_mismatch = deepcopy(bound)
        pair_frame = self._frame(axis_scale_pair_mismatch)
        pair_frame["direction_open_expression"]["order_axis_id"] = "stature"
        pair_frame["operation"]["order_axis_id"] = "stature"
        pair_frame["direction_binding"]["required_constraint"][
            "order_axis_id"
        ] = "stature"
        pair_frame["direction_binding"]["accepted_evidence"][0][
            "order_axis_id"
        ] = "stature"
        duplicate_direction_options = deepcopy(bound)
        self._frame(duplicate_direction_options)["direction_open_expression"][
            "direction_options"
        ] = ["scale_high_pole_first", "scale_high_pole_first"]
        duplicate_allowed_directions = deepcopy(bound)
        self._frame(duplicate_allowed_directions)["direction_binding"][
            "required_constraint"
        ]["allowed_directions"] = [
            "scale_low_pole_first",
            "scale_low_pole_first",
        ]
        auxiliary_evidence_in_finding_derivation = deepcopy(unbound)
        self._decision_finding(auxiliary_evidence_in_finding_derivation)[
            "derivation"
        ]["impact_evidence"] = {"affects_primary_finding": False}

        for invalid in (
            inconsistent_evaluation,
            accepted_nonbinding,
            bound_direction_mismatch,
            bound_without_direction,
            open_expression_scale_mismatch,
            operation_scale_mismatch,
            required_constraint_scale_mismatch,
            accepted_evidence_scale_mismatch,
            open_expression_axis_mismatch,
            operation_axis_mismatch,
            required_constraint_axis_mismatch,
            accepted_evidence_axis_mismatch,
            accepted_evidence_unresolved_axis,
            accepted_evidence_unknown_site,
            accepted_evidence_with_rejection,
            accepted_evidence_rejected_only_site,
            comparison_pole_mismatch,
            operation_measure_mismatch,
            axis_scale_pair_mismatch,
            duplicate_direction_options,
            duplicate_allowed_directions,
            auxiliary_evidence_in_finding_derivation,
        ):
            with self.subTest(invalid=invalid), self.assertRaises(ValidationError):
                validate(instance=invalid, schema=schema)

    def test_repair_candidates_bind_the_direction_without_numeric_promotion(self) -> None:
        original = self._audit(ROWS + QUESTION)
        repairs = self._frame(original)["repair_candidates"]

        self.assertEqual(len(repairs), 2)
        self.assertEqual(
            self._decision_finding(original)["repair"]["rewrite_candidates"],
            [item["rewrite"] for item in repairs],
        )
        for repair in repairs:
            with self.subTest(repair=repair):
                rerun = self._audit(ROWS + repair["rewrite"])
                frame = self._frame(rerun)
                self.assertEqual(frame["status"], "direction_bound")
                self.assertEqual(frame["direction_binding"]["status"], "bound")
                self.assertNotIn(PRECONDITION_ORDER_DIRECTION_RULE_ID, self._rule_ids(rerun))

    def test_relaxed_mode_changes_severity_only(self) -> None:
        strict = self._audit(ROWS + QUESTION)
        relaxed = audit_request(
            ROWS + QUESTION,
            strict=False,
            morphology_provider=SignalProvider(),
        )
        self.assertEqual(self._decision_finding(strict)["severity"], "minor")
        self.assertEqual(self._decision_finding(relaxed)["severity"], "info")
        self.assertEqual(
            self._decision_finding(strict)["confidence"],
            self._decision_finding(relaxed)["confidence"],
        )

    def test_candidate_row_order_does_not_change_auxiliary_witnesses(self) -> None:
        shuffled = "D：80kg\nA：50kg\nE：90kg\nC：70kg\nB：60kg\n"
        impact = self._frame(self._audit(shuffled + QUESTION))["impact_evidence"]
        self.assertEqual(
            [item["outcome"]["entity_id"] for item in impact["candidate_frames"]],
            ["B", "D"],
        )

    def test_comparison_pole_does_not_choose_order_direction(self) -> None:
        for question in (
            QUESTION,
            "この5人の中で、Cの次に体重が軽い人は誰ですか？",
        ):
            with self.subTest(question=question):
                result = self._audit(ROWS + question)
                self.assertEqual(self._frame(result)["status"], "direction_unbound")
                self.assertIn(PRECONDITION_ORDER_DIRECTION_RULE_ID, self._rule_ids(result))

    def test_context_numeric_spans_remain_source_aligned(self) -> None:
        result = audit_request(QUESTION, context=ROWS, morphology_provider=SignalProvider())
        impact = self._frame(result)["impact_evidence"]
        self.assertEqual(self._frame(result)["status"], "direction_unbound")
        self.assertGreater(
            impact["candidate_frames"][0]["evidence_spans"][0]["start"],
            len(QUESTION),
        )

    def test_direct_same_scale_arrangements_bind(self) -> None:
        cases = [
            (
                "体重が重い順に並べたとき、" + QUESTION,
                "scale_high_pole_first",
                "explicit_measure",
            ),
            (
                "体重が軽い順に並べたとき、" + QUESTION,
                "scale_low_pole_first",
                "explicit_measure",
            ),
            (
                "重い順で並べたとき、" + QUESTION,
                "scale_high_pole_first",
                "inherited_from_target_frame",
            ),
            (
                "この5人を重い順で並べたとき、" + QUESTION,
                "scale_high_pole_first",
                "inherited_from_target_frame",
            ),
        ]
        for question, direction, axis_resolution in cases:
            with self.subTest(direction=direction, question=question):
                result = self._audit(ROWS + question)
                frame = self._frame(result)
                binding = frame["direction_binding"]
                self.assertEqual(frame["status"], "direction_bound")
                self.assertEqual(binding["status"], "bound")
                self.assertEqual(binding["direction"], direction)
                self.assertTrue(binding["accepted_evidence"])
                self.assertEqual(
                    binding["accepted_evidence"][0]["order_axis_id"],
                    "body_weight",
                )
                self.assertEqual(
                    binding["accepted_evidence"][0]["axis_resolution"],
                    axis_resolution,
                )
                self.assertNotIn(PRECONDITION_ORDER_DIRECTION_RULE_ID, self._rule_ids(result))

    def test_current_table_headers_bind_in_text_or_context(self) -> None:
        cases = [
            ("並び順：重い順\n" + ROWS + QUESTION, "", "scale_high_pole_first"),
            (
                "並び順：重い順\n" + ROWS + "Cの次に体重が重い人は誰ですか？",
                "",
                "scale_high_pole_first",
            ),
            (QUESTION, "並び順：軽い順\n" + ROWS, "scale_low_pole_first"),
        ]
        for text, context, direction in cases:
            with self.subTest(direction=direction):
                result = audit_request(
                    text,
                    context=context,
                    morphology_provider=SignalProvider(),
                )
                binding = self._frame(result)["direction_binding"]
                self.assertEqual(self._frame(result)["status"], "direction_bound")
                self.assertEqual(binding["direction"], direction)

    def test_noncurrent_postposed_or_other_table_headers_are_rejected(self) -> None:
        cases = [
            "旧版の設定:\n並び順：重い順\n" + ROWS + QUESTION,
            "候補案:\n並び順：重い順\n" + ROWS + QUESTION,
            ROWS + QUESTION + "\n並び順：重い順",
            (
                "並び順：重い順\nX：10kg\nY：20kg\n\n現行候補\n"
                + ROWS
                + QUESTION
            ),
        ]
        for text in cases:
            with self.subTest(text=text):
                result = self._audit(text)
                binding = self._frame(result)["direction_binding"]
                self.assertEqual(self._frame(result)["status"], "direction_unbound")
                self.assertEqual(binding["status"], "missing")
                self.assertTrue(binding["rejected_evidence"])

    def test_same_scale_phrase_for_another_set_is_nonbinding(self) -> None:
        cases = [
            (
                ROWS
                + "別班を体重が重い順に並べたときの記録を確認し、"
                + QUESTION,
                "not_directly_attached",
            ),
            (
                ROWS
                + "この3人を重い順に並べたとき、"
                + QUESTION,
                "different_candidate_set",
            ),
            (
                ROWS
                + "この5商品を重い順に並べたとき、"
                + QUESTION,
                "different_candidate_set",
            ),
        ]
        for text, reason in cases:
            with self.subTest(reason=reason):
                result = self._audit(text)
                binding = self._frame(result)["direction_binding"]
                self.assertEqual(self._frame(result)["status"], "direction_unbound")
                self.assertEqual(binding["accepted_evidence"], [])
                self.assertTrue(
                    any(
                        reason in item["rejection_reasons"][0]
                        for item in binding["rejected_evidence"]
                    )
                )

    def test_table_header_requires_the_current_candidate_set(self) -> None:
        text = "並び順：重い順\nX：10kg\nY：20kg\n" + QUESTION
        result = self._audit(text)
        binding = self._frame(result)["direction_binding"]

        self.assertEqual(self._frame(result)["status"], "direction_unbound")
        self.assertTrue(
            any(
                item.get("rejection_reasons") == ["different_candidate_set"]
                for item in binding["rejected_evidence"]
            )
        )

    def test_other_scale_and_tentative_directions_are_nonbinding(self) -> None:
        cases = [
            "身長が高い順に並べたとき、" + QUESTION,
            "体重が重い順かは未確定だが、" + QUESTION,
            "体重が重い順とは限らないが、" + QUESTION,
            "体重が重い順に並べたときという案は採用しないが、" + QUESTION,
        ]
        for question in cases:
            with self.subTest(question=question):
                result = self._audit(ROWS + question)
                binding = self._frame(result)["direction_binding"]
                self.assertEqual(self._frame(result)["status"], "direction_unbound")
                self.assertEqual(binding["status"], "missing")
                self.assertTrue(binding["rejected_evidence"])
        other_scale = self._frame(self._audit(ROWS + cases[0]))["direction_binding"]
        self.assertTrue(
            any(
                item.get("rejection_reasons") == ["different_scale"]
                for item in other_scale["rejected_evidence"]
            )
        )

    def test_conflicting_bound_directions_emit_the_same_primary_rule(self) -> None:
        text = (
            "並び順：重い順\n"
            + ROWS
            + "体重が軽い順に並べたとき、"
            + QUESTION
        )
        result = self._audit(text)
        frame = self._frame(result)
        finding = self._decision_finding(result)

        self.assertEqual(frame["status"], "direction_conflict")
        self.assertEqual(frame["direction_binding"]["status"], "conflict")
        self.assertEqual(len(frame["direction_binding"]["accepted_evidence"]), 2)
        self.assertEqual(finding["rule_id"], PRECONDITION_ORDER_DIRECTION_RULE_ID)
        self.assertIn("conflicting_condition:order_direction", finding["ambiguity_reasons"])

    def test_fenced_direction_header_is_rejected_but_live_gap_remains(self) -> None:
        result = self._audit("```text\n並び順：重い順\n```\n" + ROWS + QUESTION)
        binding = self._frame(result)["direction_binding"]
        self.assertEqual(self._frame(result)["status"], "direction_unbound")
        self.assertTrue(
            any(
                item.get("rejection_reasons") == ["quoted_or_code_example"]
                for item in binding["rejected_evidence"]
            )
        )

    def test_nonbinding_question_itself_is_not_a_requirement_finding(self) -> None:
        cases = [
            "例：" + QUESTION,
            "旧問題では、体重が重い順に並べたとき、" + QUESTION,
            "一例では、体重が重い順に並べたとき、" + QUESTION,
            "『" + QUESTION + "』という表現を検出する。",
            QUESTION + "\nこの問いは不採用とする。",
            QUESTION + "\nなお、この問いは不採用とする。",
        ]
        for text in cases:
            with self.subTest(text=text):
                result = self._audit(ROWS + text)
                self.assertEqual(
                    result["details"]["decision_frame_summary"]["status"],
                    "not_applicable",
                )
                self.assertNotIn(PRECONDITION_ORDER_DIRECTION_RULE_ID, self._rule_ids(result))

    def test_quoted_or_metalinguistic_direction_does_not_hide_a_live_gap(self) -> None:
        cases = [
            "「重い順」で並べたとき、" + QUESTION,
            "文言「重い順」を確認し、" + QUESTION,
            "重い順という表現を説明し、" + QUESTION,
        ]
        for text in cases:
            with self.subTest(text=text):
                result = self._audit(ROWS + text)
                frame = self._frame(result)
                self.assertEqual(frame["status"], "direction_unbound")
                self.assertIn(PRECONDITION_ORDER_DIRECTION_RULE_ID, self._rule_ids(result))
                if "「重い順」" in text:
                    self.assertTrue(
                        any(
                            item.get("rejection_reasons")
                            == ["quoted_or_code_example"]
                            for item in frame["direction_binding"]["rejected_evidence"]
                        )
                    )

    def test_fenced_example_question_is_ignored_but_later_live_question_is_audited(self) -> None:
        example = "```text\n" + ROWS + QUESTION + "\n```\n"
        example_only = self._audit(example)
        live = self._audit(example + ROWS + QUESTION)

        self.assertEqual(
            example_only["details"]["decision_frame_summary"]["status"],
            "not_applicable",
        )
        self.assertEqual(self._frame(live)["status"], "direction_unbound")

    def test_numeric_failures_do_not_change_primary_direction_audit(self) -> None:
        cases = [
            "A：50kg\nB：70kg\nC：70kg\nD：80kg\nE：90kg\n",
            "A：50kg\nB：60kg\nC：70kg\nD：80lb\nE：90kg\n",
            ROWS.replace("B：60kg", "B：60kg〜65kg"),
            ROWS.replace("B：60kg", "B：およそ60kg"),
            ROWS.replace("E：90kg\n", ""),
            ROWS + "平均：75kg\n",
            ROWS.replace("E：90kg", "C：90kg"),
            ROWS + QUESTION.replace("Cの次", "Zの次"),
        ]
        for rows in cases:
            with self.subTest(rows=rows):
                text = rows + QUESTION if not rows.endswith("？") else rows
                result = self._audit(text)
                frame = self._frame(result)
                finding = self._decision_finding(result)
                self.assertEqual(frame["status"], "direction_unbound")
                self.assertEqual(finding["match_status"], "matched")
                self.assertEqual(finding["confidence"], "medium")
                self.assertNotIn("impact_evidence", frame)

    def test_unsupported_or_nonselecting_grammar_is_not_applicable(self) -> None:
        cases = [
            "Cの次に体重を測る人は誰ですか？",
            "Cの次に来た人で、体重が重い人は誰ですか？",
            "Cの次に。体重が重い人は誰ですか？",
            "Cの次に体重が重い理由は誰が説明しますか？",
            "この5人の中で、Cの次に体重が重い人が来るのはいつですか？",
        ]
        for question in cases:
            with self.subTest(question=question):
                result = self._audit(ROWS + question)
                self.assertEqual(
                    result["details"]["decision_frame_summary"]["status"],
                    "not_applicable",
                )

    def test_multiple_questions_are_indeterminate(self) -> None:
        for text in (
            ROWS + QUESTION + "\nこの表の作成者は誰ですか？",
            ROWS + "今日は晴れますか。" + QUESTION,
        ):
            with self.subTest(text=text):
                summary = self._audit(text)["details"]["decision_frame_summary"]
                self.assertEqual(summary["status"], "indeterminate")
                self.assertEqual(summary["derivation_status"], "blocked_by_unknown")
                self.assertIn("multiple_questions", summary["unknown_reasons"])

    def test_invalid_or_unavailable_morphology_is_indeterminate(self) -> None:
        providers = (
            SignalProvider(invalid_surface=True),
            SignalProvider(reverse=True),
            UnavailableProvider(),
        )
        for provider in providers:
            with self.subTest(provider=provider):
                result = audit_request(ROWS + QUESTION, morphology_provider=provider)
                summary = result["details"]["decision_frame_summary"]
                self.assertEqual(summary["status"], "indeterminate")
                self.assertNotIn(PRECONDITION_ORDER_DIRECTION_RULE_ID, self._rule_ids(result))

    def test_provider_is_not_run_or_reported_by_default(self) -> None:
        result = audit_request(ROWS + QUESTION)
        self.assertNotIn("decision_frame_summary", result["details"])

    def test_root_audit_reuses_one_provider_execution(self) -> None:
        provider = SignalProvider()
        result = audit_request(ROWS + QUESTION, morphology_provider=provider)
        self.assertEqual(provider.calls, 1)
        self.assertEqual(self._frame(result)["status"], "direction_unbound")

    def test_explicit_provider_runs_even_when_relation_record_is_closed(self) -> None:
        provider = SignalProvider()
        text = (
            "目的: 応答時間を制限する。\n"
            "利用者: 運用者。\n"
            "シナリオ: 検索時。\n"
            "期待結果: 結果を返す。\n"
            "受入基準: p95 500ms以下。\n"
            "検証方法: 負荷試験で測定する。\n"
            "証拠: 試験結果を保存する。"
        )

        ir = extract_semantic_assertions(text, morphology_provider=provider)
        attempt = next(item for item in ir.attempts if item.stage == "morphology")

        self.assertEqual(provider.calls, 1)
        self.assertEqual(attempt.status, "executed")

    def test_non_requirement_kind_rejects_explicit_provider(self) -> None:
        with self.assertRaisesRegex(ValueError, "only for requirement"):
            audit_request("document", input_kind="document", morphology_provider=SignalProvider())

    @staticmethod
    def _rule_ids(result: dict[str, object]) -> set[str]:
        return {str(item.get("rule_id", "")) for item in result["findings"]}

    def _decision_finding(self, result: dict[str, object]) -> dict[str, object]:
        return next(
            item
            for item in result["findings"]
            if item.get("rule_id") == PRECONDITION_ORDER_DIRECTION_RULE_ID
        )

    @staticmethod
    def _frame(result: dict[str, object]) -> dict[str, object]:
        return result["details"]["decision_frame_summary"]["frames"][0]

    @staticmethod
    def _audit(text: str) -> dict[str, object]:
        return audit_request(text, morphology_provider=SignalProvider())

    def _all_rule_ids(self, text: str) -> set[str]:
        result = self._audit(text)
        emitted = self._rule_ids(result)
        evaluated = {
            str(item.get("rule_id", ""))
            for item in self._frame(result).get("evaluations", [])
            if isinstance(item, dict)
        }
        non_emitted = {
            str(item.get("rule_id", ""))
            for item in result["details"].get("non_emitted_rules", [])
            if isinstance(item, dict)
        }
        return emitted | evaluated | non_emitted


if __name__ == "__main__":
    unittest.main()
