from __future__ import annotations

import unittest

from semantic_guard.direct_rules import evaluate_direct_relations
from semantic_guard.records import parse_requirement_record


COMPLETE = """Purpose: 検索APIが検索結果を p95 500ms以内で返す
User: 検索API
Scenario: 検索APIが検索要求を処理して検索結果を返す
Expected result: 検索結果を p95 500ms以内で返す
Acceptance criteria: 検索応答時間 p95 500ms 以下
Verification method: 検索結果の検索応答時間を benchmark で測定する
Evidence: 検索結果の検索応答時間 benchmark report"""


class DirectRuleTests(unittest.TestCase):
    def test_actor_occurrence_as_object_cannot_support_performs(self) -> None:
        text = COMPLETE.replace(
            "検索APIが検索要求を処理して検索結果を返す",
            "システムが検索APIを検索して検索結果を返す",
        )
        record = parse_requirement_record(text)
        result = {
            item.obligation_id: item for item in evaluate_direct_relations(record)
        }["func.performs"]

        self.assertEqual(result.outcome, "unresolved")
        self.assertEqual(result.rule_id, "direct.structured.actor-scenario/v2")
        self.assertIn("scenario_actor_role_not_assertion_capable", result.unknown_reasons)

    def test_explicit_actor_subject_supports_performs(self) -> None:
        record = parse_requirement_record(COMPLETE)
        result = {
            item.obligation_id: item for item in evaluate_direct_relations(record)
        }["func.performs"]

        self.assertEqual(result.outcome, "supported")
        self.assertEqual(result.basis, ("explicit_scenario_actor_active_assertion",))

    def test_passive_subject_cannot_support_performs(self) -> None:
        text = COMPLETE.replace(
            "検索APIが検索要求を処理して検索結果を返す",
            "検索APIが処理される",
        )
        result = self.by_id(text)["func.performs"]

        self.assertEqual(result.outcome, "unresolved")
        self.assertIn("scenario_actor_voice_not_agentive", result.unknown_reasons)

    def test_nominal_subject_cannot_support_performs(self) -> None:
        text = COMPLETE.replace(
            "検索APIが検索要求を処理して検索結果を返す",
            "検索APIは主要機能である",
        )
        result = self.by_id(text)["func.performs"]

        self.assertEqual(result.outcome, "unresolved")
        self.assertIn(
            "scenario_actor_active_predicate_not_established",
            result.unknown_reasons,
        )

    def test_causative_or_reported_actor_clause_cannot_support_performs(self) -> None:
        for scenario, reason in (
            ("検索APIが利用者に検索させる", "scenario_actor_voice_not_agentive"),
            (
                "検索APIが検索要求を処理すると記載される",
                "scenario_actor_assertion_reported_or_quoted",
            ),
        ):
            with self.subTest(scenario=scenario):
                text = COMPLETE.replace(
                    "検索APIが検索要求を処理して検索結果を返す",
                    scenario,
                )
                result = self.by_id(text)["func.performs"]

                self.assertEqual(result.outcome, "unresolved")
                self.assertIn(reason, result.unknown_reasons)

    def by_id(self, text: str):
        return {
            item.obligation_id: item
            for item in evaluate_direct_relations(parse_requirement_record(text))
        }

    def test_every_profile_obligation_has_one_result(self) -> None:
        results = evaluate_direct_relations(parse_requirement_record(COMPLETE))

        self.assertEqual(len(results), 11)
        self.assertEqual(len({item.obligation_id for item in results}), 11)

    def test_complete_record_supports_only_strongly_anchored_cross_field_relations(self) -> None:
        results = self.by_id(COMPLETE)

        self.assertEqual(results["func.constrained_by"].outcome, "supported")
        self.assertEqual(results["func.verified_by"].outcome, "supported")
        self.assertEqual(results["func.verifies"].outcome, "supported")
        self.assertEqual(results["func.produces_evidence"].outcome, "supported")

    def test_shared_domain_word_does_not_prove_causal_or_constraint_alignment(self) -> None:
        text = """目的: 検索機能を提供する
利用者: 検索API
シナリオ: 検索APIが検索要求を処理する
期待結果: 検索ログは削除される
受入基準: 検索応答時間は100ms以内
検証方法: 検索応答時間を測定する
証拠: 検索応答時間CSV"""

        results = self.by_id(text)

        self.assertEqual(results["func.produces"].outcome, "unresolved")
        self.assertEqual(results["func.constrained_by"].outcome, "unresolved")
        self.assertIn(
            "shared_dimension_is_candidate_not_relation_proof",
            results["func.produces"].unknown_reasons,
        )

    def test_same_endpoint_with_opposing_actions_refutes_result_alignment(self) -> None:
        text = """目的: 検索APIが監査対象ログ・audit_logを保存する
利用者: 検索API
シナリオ: 検索APIが監査対象ログ・audit_logを保存する
期待結果: 監査対象ログ・audit_logを100ms以内に削除する
受入基準: 監査対象ログ削除時間は100ms以内
検証方法: 監査対象ログ削除時間を測定する
証拠: 監査対象ログ削除時間CSV"""

        results = self.by_id(text)

        self.assertEqual(results["func.produces"].outcome, "refuted")
        self.assertTrue(
            any(
                item.startswith("incompatible_")
                for item in results["func.produces"].basis
            )
        )

    def test_distinct_recognized_dimensions_refute_verification_alignment(self) -> None:
        text = COMPLETE.replace(
            "検索結果の検索応答時間を benchmark で測定する",
            "ログイン認証を pytest で検証する",
        )
        results = self.by_id(text)

        self.assertEqual(results["func.verifies"].outcome, "refuted")
        self.assertTrue(results["func.verifies"].basis)

    def test_missing_metric_makes_conditional_metric_obligations_not_applicable(self) -> None:
        text = COMPLETE.replace("検索応答時間 p95 500ms 以下", "検索結果が表示される")
        results = self.by_id(text)

        self.assertEqual(results["func.uses_metric"].outcome, "not_applicable")
        self.assertEqual(results["func.measures"].outcome, "not_applicable")

    def test_unrelated_purpose_is_not_supported_by_field_co_location(self) -> None:
        text = COMPLETE.replace(
            "検索APIが検索結果を p95 500ms以内で返す",
            "請求書を破棄する",
            1,
        )
        results = self.by_id(text)

        self.assertEqual(results["func.applies_to"].outcome, "unresolved")
        self.assertEqual(results["func.verified_by"].outcome, "unresolved")

    def test_absent_object_marker_is_unresolved_not_terminally_inapplicable(self) -> None:
        text = COMPLETE.replace(
            "検索APIが検索要求を処理して検索結果を返す",
            "検索APIが要求へ応答した場合、結果が表示される",
        )
        results = self.by_id(text)

        self.assertEqual(results["func.acts_on"].outcome, "unresolved")

    def test_condition_variant_is_not_misclassified_as_inapplicable(self) -> None:
        text = COMPLETE.replace("検索要求を処理して", "障害時のみ検索要求を処理して")
        results = self.by_id(text)

        self.assertEqual(results["func.triggered_by"].outcome, "supported")


if __name__ == "__main__":
    unittest.main()
