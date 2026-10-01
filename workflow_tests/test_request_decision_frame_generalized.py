from __future__ import annotations

import re
import unittest
from typing import ClassVar

from semantic_guard_workflow.decision_frame_scales import (
    SCALE_SPECS,
    DirectionalScaleSpec,
    numeric_projection_for_scale,
)
from semantic_guard_workflow.models import load_audit_result_schema
from semantic_guard_workflow.request_audit import audit_request
from semantic_guard_workflow.request_decision_frame import (
    PRECONDITION_ORDER_DIRECTION_RULE_ID,
    PRECONDITION_OUTCOME_RULE_ID,
)

BODY_WEIGHT_ROWS = "A：50kg\nB：60kg\nC：70kg\nD：80kg\nE：90kg\n"
BODY_WEIGHT_QUESTION = "この5人の中で、Cの次に体重が重い人は誰ですか？"

HEIGHT_ROWS = (
    "候補種別：人\n"
    "佐藤花子：150cm\n"
    "鈴木一郎：160cm\n"
    "田中美咲：170cm\n"
    "山田太郎：180cm\n"
    "高橋蓮：190cm\n"
)
HEIGHT_QUESTION = "この5人の中で、田中美咲の次に身長が高い人は誰ですか？"

PRICE_ROWS = (
    "候補種別：商品\n"
    "商品A：100円\n"
    "商品B：200円\n"
    "商品C：300円\n"
    "商品D：400円\n"
)
PRICE_QUESTION = "この4商品の中で、商品Cの次に価格が高い商品はどれですか？"

POPULATION_ROWS = (
    "候補種別：都市\n"
    "東京：14000000人\n"
    "大阪：8800000人\n"
    "名古屋：2300000人\n"
    "福岡：1600000人\n"
)
POPULATION_QUESTION = "この4都市の中で、大阪の次に人口が多い都市はどこですか？"


class GeneralizedSignalProvider:
    """Small source-aligned provider shaped like a Sudachi result.

    Compound references and measures deliberately consist of multiple noun
    tokens in several cases.  The decision-frame detector must preserve their
    source span rather than assume that one entity or measure equals one token.
    """

    _LEXEMES: ClassVar[set[str]] = {
        "田中",
        "美咲",
        "山田",
        "太郎",
        "佐藤",
        "花子",
        "鈴木",
        "一郎",
        "高橋",
        "東京",
        "商品",
        "優先度",
        "魔力度",
        "身長",
        "価格",
        "人口",
        "体重",
        "機能",
        "都市",
        "理由",
        "旧版",
        "問題",
        "問い",
        "採用",
        "説明",
        "ください",
        "とき",
        "並べ",
        "選ん",
        "高い",
        "低い",
        "重い",
        "軽い",
        "安い",
        "多い",
        "少ない",
        "この",
        "どれ",
        "どこ",
        "誰",
        "次",
        "順",
        "案",
        "例",
        "人",
        "中",
        "蓮",
        "の",
        "に",
        "が",
        "は",
        "を",
        "で",
        "と",
        "し",
        "ない",
        "です",
        "ます",
        "か",
    }
    _TOKEN_RE = re.compile(
        "|".join(re.escape(item) for item in sorted(_LEXEMES, key=len, reverse=True))
        + r"|[A-Za-z]+|[0-9]+(?:\.[0-9]+)?|[α-ωΑ-Ω]"
        + r"|[一-龥ぁ-んァ-ヶー]|[：:、。？?「」『』`]+|\s+"
    )
    _ADJECTIVES: ClassVar[set[str]] = {
        "高い",
        "低い",
        "重い",
        "軽い",
        "安い",
        "多い",
        "少ない",
    }
    _PARTICLES: ClassVar[set[str]] = {"の", "に", "が", "は", "を", "で", "と", "か"}
    _PRONOUNS: ClassVar[set[str]] = {"誰", "どれ", "どこ"}
    _VERB_LEMMAS: ClassVar[dict[str, str]] = {
        "並べ": "並べる",
        "選ん": "選ぶ",
        "し": "する",
    }

    def __init__(self) -> None:
        self.calls = 0

    def analyze(self, text: str) -> dict[str, object]:
        self.calls += 1
        tokens: list[dict[str, object]] = []
        for match in self._TOKEN_RE.finditer(text):
            surface = match.group(0)
            lemma = self._VERB_LEMMAS.get(surface, surface)
            if surface.isspace():
                pos = ["空白", "*", "*", "*", "*", "*"]
            elif re.fullmatch(r"[：:、。？?「」『』`]+", surface):
                pos = ["補助記号", "*", "*", "*", "*", "*"]
            elif surface in self._ADJECTIVES:
                pos = ["形容詞", "一般", "*", "*", "形容詞", "連体形-一般"]
            elif surface in self._PARTICLES:
                pos = ["助詞", "格助詞", "*", "*", "*", "*"]
            elif surface in self._PRONOUNS:
                pos = ["代名詞", "*", "*", "*", "*", "*"]
            elif surface in self._VERB_LEMMAS:
                pos = ["動詞", "一般", "*", "*", "五段", "連用形"]
            elif surface in {"です", "ます", "ない", "ください"}:
                pos = ["助動詞", "*", "*", "*", "*", "*"]
            elif surface.isdigit():
                pos = ["名詞", "数詞", "*", "*", "*", "*"]
            else:
                pos = ["名詞", "普通名詞", "一般", "*", "*", "*"]
            tokens.append(
                {
                    "surface": surface,
                    "normalized": lemma,
                    "lemma": lemma,
                    "pos": pos,
                    "start": match.start(),
                    "end": match.end(),
                }
            )
        return {
            "provider_id": "generalized-test-morphology",
            "provider_version": "1",
            "resource_version": "fixture",
            "split_mode": "C",
            "tokens": tokens,
        }


class RegisteredScaleSignalProvider:
    """Source-aligned signal provider covering the complete scale registry."""

    _TERMS: ClassVar[set[str]] = {
        "基準",
        "もの",
        "どれ",
        "です",
        "並べ",
        "とき",
        "次",
        "順",
        "の",
        "に",
        "が",
        "は",
        "た",
        "か",
        *(
            term
            for scale in SCALE_SPECS
            for term in (*scale.measure_terms, *scale.high_terms, *scale.low_terms)
        ),
    }
    _TOKEN_RE: ClassVar[re.Pattern[str]] = re.compile(
        "|".join(re.escape(item) for item in sorted(_TERMS, key=len, reverse=True))
        + r"|[、。？?]|\s+"
    )
    _COMPARATORS: ClassVar[set[str]] = {
        term
        for scale in SCALE_SPECS
        for term in (*scale.high_terms, *scale.low_terms)
    }

    def analyze(self, text: str) -> dict[str, object]:
        tokens: list[dict[str, object]] = []
        for match in self._TOKEN_RE.finditer(text):
            surface = match.group(0)
            if surface.isspace():
                pos = ["空白", "*", "*", "*", "*", "*"]
            elif surface in self._COMPARATORS:
                pos = ["形容詞", "一般", "*", "*", "形容詞", "終止形-一般"]
            elif surface in {"の", "に", "が", "は"}:
                pos = ["助詞", "格助詞", "*", "*", "*", "*"]
            elif surface in {"、", "。", "？", "?"}:
                pos = ["補助記号", "*", "*", "*", "*", "*"]
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
            "provider_id": "registered-scale-test-morphology",
            "provider_version": "1",
            "resource_version": "fixture",
            "split_mode": "C",
            "tokens": tokens,
        }


class GeneralizedRequestDecisionFrameTests(unittest.TestCase):
    def test_directional_axes_and_numeric_projections_are_separate(self) -> None:
        directional_fields = set(DirectionalScaleSpec.__dataclass_fields__)
        self.assertTrue(
            {"unit_aliases", "witness_policy", "high_pole_numeric_order"}.isdisjoint(
                directional_fields
            )
        )
        self.assertIsNone(numeric_projection_for_scale("rating"))
        self.assertIsNotNone(numeric_projection_for_scale("body_mass"))

        registered_contract = {
            (scale.scale_id, axis.axis_id): frozenset(axis.measure_terms)
            for scale in SCALE_SPECS
            for axis in scale.axes
        }
        schema = load_audit_result_schema()
        schema_axes = set(schema["$defs"]["decisionFrameOrderAxisId"]["enum"])
        self.assertEqual(schema_axes, {axis for _scale, axis in registered_contract})

        axis_contracts = [
            item["oneOf"]
            for item in schema["$defs"]["decisionFrameV3"]["allOf"]
            if "oneOf" in item
            and item["oneOf"]
            and all(
                "order_axis_id"
                in branch["properties"]["direction_open_expression"]["properties"]
                for branch in item["oneOf"]
            )
        ]
        self.assertEqual(len(axis_contracts), 1)
        schema_contract = {}
        for branch in axis_contracts[0]:
            expression = branch["properties"]["direction_open_expression"][
                "properties"
            ]
            operation = branch["properties"]["operation"]["properties"]
            key = (
                expression["scale_id"]["const"],
                expression["order_axis_id"]["const"],
            )
            self.assertNotIn(key, schema_contract)
            schema_contract[key] = frozenset(operation["measure"]["enum"])
        self.assertEqual(schema_contract, registered_contract)

    def test_all_registered_scales_share_one_direction_binding_contract(self) -> None:
        provider = RegisteredScaleSignalProvider()
        for scale in SCALE_SPECS:
            measure = scale.measure_terms[0]
            high = scale.canonical_high_term
            question = f"基準の次に{measure}が{high}ものはどれですか？"
            with self.subTest(scale=scale.scale_id, form="unbound"):
                result = audit_request(question, morphology_provider=provider)
                frame = result["details"]["decision_frame_summary"]["frames"][0]
                self.assertEqual(frame["status"], "direction_unbound")
                self.assertEqual(frame["operation"]["scale_id"], scale.scale_id)
                self.assertIn(PRECONDITION_ORDER_DIRECTION_RULE_ID, self._rule_ids(result))
                self.assertNotIn("impact_evidence", frame)
            for term, direction in (
                (scale.canonical_high_term, "scale_high_pole_first"),
                (scale.canonical_low_term, "scale_low_pole_first"),
            ):
                with self.subTest(scale=scale.scale_id, direction=direction):
                    result = audit_request(
                        f"{measure}が{term}順に並べたとき、{question}",
                        morphology_provider=provider,
                    )
                    frame = result["details"]["decision_frame_summary"]["frames"][0]
                    self.assertEqual(frame["status"], "direction_bound")
                    self.assertEqual(
                        frame["direction_binding"]["direction"], direction
                    )
                    self.assertNotIn(
                        PRECONDITION_ORDER_DIRECTION_RULE_ID, self._rule_ids(result)
                    )

    def test_direction_binding_requires_the_same_order_axis(self) -> None:
        provider = RegisteredScaleSignalProvider()
        cases = [
            ("標高", "身長", "高い"),
            ("危険度", "優先度", "高い"),
            ("人口", "在庫数", "多い"),
            ("期間", "応答時間", "長い"),
            ("所要時間", "処理時間", "長い"),
        ]
        for binding_measure, target_measure, term in cases:
            text = (
                f"{binding_measure}が{term}順に並べたとき、"
                f"基準の次に{target_measure}が{term}ものはどれですか？"
            )
            with self.subTest(binding_measure=binding_measure, target=target_measure):
                result = audit_request(text, morphology_provider=provider)
                frame = result["details"]["decision_frame_summary"]["frames"][0]
                binding = frame["direction_binding"]
                self.assertEqual(frame["status"], "direction_unbound")
                self.assertEqual(binding["accepted_evidence"], [])
                self.assertTrue(
                    any(
                        item.get("rejection_reasons") == ["different_order_axis"]
                        for item in binding["rejected_evidence"]
                    )
                )
                self.assertIn(
                    PRECONDITION_ORDER_DIRECTION_RULE_ID,
                    self._rule_ids(result),
                )

    def test_registered_axis_synonyms_can_bind(self) -> None:
        provider = RegisteredScaleSignalProvider()
        cases = [
            ("価格", "値段", "高い", "price"),
            ("点数", "得点", "高い", "score"),
            ("重量", "重さ", "重い", "weight"),
        ]
        for binding_measure, target_measure, term, axis_id in cases:
            text = (
                f"{binding_measure}が{term}順に並べたとき、"
                f"基準の次に{target_measure}が{term}ものはどれですか？"
            )
            with self.subTest(axis_id=axis_id):
                result = audit_request(text, morphology_provider=provider)
                frame = result["details"]["decision_frame_summary"]["frames"][0]
                self.assertEqual(frame["status"], "direction_bound")
                self.assertEqual(frame["operation"]["order_axis_id"], axis_id)
                self.assertEqual(
                    frame["direction_binding"]["accepted_evidence"][0][
                        "order_axis_id"
                    ],
                    axis_id,
                )

    def test_arrangement_conditional_to_can_bind(self) -> None:
        text = (
            "身長が高い順に並べると、"
            "基準の次に身長が高いものはどれですか？"
        )
        result = audit_request(
            text,
            morphology_provider=RegisteredScaleSignalProvider(),
        )
        frame = result["details"]["decision_frame_summary"]["frames"][0]

        self.assertEqual(frame["status"], "direction_bound")
        self.assertEqual(frame["operation"]["order_axis_id"], "stature")

    def test_table_header_for_another_order_axis_is_nonbinding(self) -> None:
        rows = (
            "佐藤花子：低\n"
            "鈴木一郎：中\n"
            "田中美咲：中\n"
            "山田太郎：高\n"
            "高橋蓮：最高\n"
        )
        result = self._audit("標高の並び順：高い順\n" + rows + HEIGHT_QUESTION)
        frame = result["details"]["decision_frame_summary"]["frames"][0]
        binding = frame["direction_binding"]

        self.assertEqual(frame["status"], "direction_unbound")
        self.assertTrue(
            any(
                item.get("rejection_reasons") == ["different_order_axis"]
                for item in binding["rejected_evidence"]
            )
        )

        same_axis = self._audit("身長の並び順：高い順\n" + HEIGHT_ROWS + HEIGHT_QUESTION)
        same_axis_frame = same_axis["details"]["decision_frame_summary"]["frames"][0]
        self.assertEqual(same_axis_frame["status"], "direction_bound")
        self.assertEqual(
            same_axis_frame["direction_binding"]["direction"],
            "scale_high_pole_first",
        )

    def test_non_numeric_known_scales_emit_only_direction_rule(self) -> None:
        cases = [
            "田中の次に身長が高い人は誰ですか？",
            "商品Bの次に価格が高い商品はどれですか？",
            "東京の次に人口が多い都市はどこですか？",
        ]

        for text in cases:
            with self.subTest(text=text):
                self._assert_direction_only(text)

    def test_non_numeric_selection_directive_emits_direction_rule(self) -> None:
        self._assert_direction_only("案βの次に優先度が高い機能を選んでください。")

    def test_general_names_and_known_numeric_scales_keep_the_primary_rule(self) -> None:
        cases = [
            HEIGHT_ROWS + HEIGHT_QUESTION,
            PRICE_ROWS + PRICE_QUESTION,
            POPULATION_ROWS + POPULATION_QUESTION,
        ]

        for text in cases:
            with self.subTest(text=text):
                self._assert_direction_with_auxiliary_impact(text)

    def test_existing_body_weight_witness_keeps_the_primary_rule(self) -> None:
        self._assert_direction_with_auxiliary_impact(
            BODY_WEIGHT_ROWS + BODY_WEIGHT_QUESTION
        )

    def test_explicit_same_scale_direction_resolves_without_either_rule(self) -> None:
        text = "身長が高い順に並べたとき、田中の次の人は誰ですか？"

        result = self._audit(text)

        self._assert_no_decision_findings(result)
        self.assertEqual(
            result["details"]["decision_frame_summary"]["status"],
            "direction_bound",
        )

    def test_nonbinding_discourse_does_not_emit_either_rule(self) -> None:
        cases = [
            "「田中の次に身長が高い人は誰ですか？」という例文を解析する。",
            "例：田中の次に身長が高い人は誰ですか？",
            "旧版の問題：田中の次に身長が高い人は誰ですか？",
            "田中の次に身長が高い人は誰ですか？この問いは採用しない。",
            HEIGHT_ROWS + "例えば、" + HEIGHT_QUESTION,
            HEIGHT_ROWS + "以前の問題として、" + HEIGHT_QUESTION,
            HEIGHT_ROWS + "仮に、" + HEIGHT_QUESTION,
            HEIGHT_ROWS + HEIGHT_QUESTION + "この問いは不採用とする。",
            HEIGHT_ROWS + HEIGHT_QUESTION + "この問いの採用は見送る。",
        ]

        for text in cases:
            with self.subTest(text=text):
                self._assert_no_decision_findings(self._audit(text))

    def test_untyped_row_does_not_become_a_candidate_entity(self) -> None:
        text = (
            "商品A：100円\n"
            "商品B：200円\n"
            "予算：300円\n"
            "この3商品の中で、商品Bの次に価格が高い商品はどれですか？"
        )

        result = self._audit(text)
        rule_ids = self._rule_ids(result)
        summary = result["details"]["decision_frame_summary"]

        self.assertIn(PRECONDITION_ORDER_DIRECTION_RULE_ID, rule_ids)
        self.assertNotIn(PRECONDITION_OUTCOME_RULE_ID, rule_ids)
        self.assertEqual(summary["status"], "direction_unbound")
        self.assertNotIn("impact_evidence", summary["frames"][0])

    def test_candidate_rows_must_bind_directly_to_the_current_question(self) -> None:
        cases = [
            PRICE_ROWS + "これは参考表です。\n" + PRICE_QUESTION,
            PRICE_ROWS.replace("候補種別：商品", "候補種別：人") + PRICE_QUESTION,
        ]

        for text in cases:
            with self.subTest(text=text):
                result = self._audit(text)
                rule_ids = self._rule_ids(result)
                frame = result["details"]["decision_frame_summary"]["frames"][0]

                self.assertIn(PRECONDITION_ORDER_DIRECTION_RULE_ID, rule_ids)
                self.assertNotIn(PRECONDITION_OUTCOME_RULE_ID, rule_ids)
                self.assertNotIn("impact_evidence", frame)

    def test_nearby_binding_discourse_is_not_suppressed_by_keyword_alone(self) -> None:
        question = "田中の次に身長が高い人は誰ですか？"
        cases = [
            "仮に障害が起きた場合でも、" + question,
            "以前より処理は速いが、" + question,
            "例外として、" + question,
            question + "別案は不採用とする。",
            question + "不採用条件を記録する。",
            question + "この問いの採用は見送らない。",
        ]

        for text in cases:
            with self.subTest(text=text):
                self._assert_direction_only(text)

    def test_unsupported_or_nonselecting_grammar_does_not_emit(self) -> None:
        cases = [
            "田中の次に高い人は誰ですか？",
            "田中の次に魔力度が高い人は誰ですか？",
            "田中の次に身長が高い理由は誰が説明しますか？",
        ]

        for text in cases:
            with self.subTest(text=text):
                self._assert_no_decision_findings(self._audit(text))

    def test_multiple_operations_and_fenced_examples_do_not_emit(self) -> None:
        cases = [
            (
                "田中の次に身長が高い人は誰ですか？"
                "商品Bの次に価格が高い商品はどれですか？"
            ),
            "```text\n田中の次に身長が高い人は誰ですか？\n```\n",
        ]

        for text in cases:
            with self.subTest(text=text):
                self._assert_no_decision_findings(self._audit(text))

    def _assert_direction_only(self, text: str) -> None:
        result = self._audit(text)
        rule_ids = self._rule_ids(result)
        frame = result["details"]["decision_frame_summary"]["frames"][0]

        self.assertIn(PRECONDITION_ORDER_DIRECTION_RULE_ID, rule_ids)
        self.assertNotIn(PRECONDITION_OUTCOME_RULE_ID, rule_ids)
        self.assertEqual(frame["status"], "direction_unbound")
        self.assertEqual(frame["direction_binding"]["status"], "missing")
        finding = next(
            item
            for item in result["findings"]
            if item.get("rule_id") == PRECONDITION_ORDER_DIRECTION_RULE_ID
        )
        self.assertTrue(finding["needs_human_decision"])
        self.assertEqual(finding["match_status"], "matched")
        self.assertEqual(finding["confidence"], "medium")

    def _assert_direction_with_auxiliary_impact(self, text: str) -> None:
        result = self._audit(text)
        rule_ids = self._rule_ids(result)
        frame = result["details"]["decision_frame_summary"]["frames"][0]

        self.assertIn(PRECONDITION_ORDER_DIRECTION_RULE_ID, rule_ids)
        self.assertNotIn(PRECONDITION_OUTCOME_RULE_ID, rule_ids)
        self.assertEqual(
            result["details"]["decision_frame_summary"]["status"],
            "direction_unbound",
        )
        self.assertEqual(
            frame["impact_evidence"]["candidate_membership_evidence"][
                "membership_status"
            ],
            "source_declared",
        )
        self.assertEqual(frame["impact_evidence"]["status"], "outcome_divergent")
        self.assertFalse(frame["impact_evidence"]["affects_primary_finding"])
        finding = next(
            item
            for item in result["findings"]
            if item.get("rule_id") == PRECONDITION_ORDER_DIRECTION_RULE_ID
        )
        self.assertNotIn("impact_evidence", finding["derivation"])
        self.assertEqual(finding["match_status"], "matched")
        self.assertEqual(finding["confidence"], "medium")
        self.assertFalse(
            any(
                item.get("rule_id") == PRECONDITION_OUTCOME_RULE_ID
                for item in result["details"]["non_emitted_rules"]
            )
        )

    def _audit(self, text: str) -> dict[str, object]:
        return audit_request(text, morphology_provider=GeneralizedSignalProvider())

    @staticmethod
    def _rule_ids(result: dict[str, object]) -> set[str]:
        return {str(item.get("rule_id", "")) for item in result["findings"]}

    def _assert_no_decision_findings(self, result: dict[str, object]) -> None:
        rule_ids = self._rule_ids(result)
        self.assertNotIn(PRECONDITION_ORDER_DIRECTION_RULE_ID, rule_ids)
        self.assertNotIn(PRECONDITION_OUTCOME_RULE_ID, rule_ids)


if __name__ == "__main__":
    unittest.main()
