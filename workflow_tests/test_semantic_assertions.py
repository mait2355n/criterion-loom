from __future__ import annotations

import json
import unittest

from semantic_guard_workflow.semantic_assertions import (
    SEMANTIC_ASSERTION_IR_VERSION,
    extract_semantic_assertions,
)


def _entities(ir, kind: str):
    return [item for item in ir.entities if item.kind == kind]


def _field_entities(ir, field: str):
    return [item for item in ir.entities if item.attributes.get("field") == field]


class SemanticAssertionExtractionTests(unittest.TestCase):
    def test_structured_functional_record_has_source_linked_core_relations(self) -> None:
        text = """Purpose: 検索を速くする
User: 運用者
Scenario: 運用者が検索語を入力した場合、結果一覧が返る。
Expected result: 結果一覧が返る
Acceptance criteria: p95 500ms 以下
Verification method: benchmark
Evidence: benchmark-report.json"""

        ir = extract_semantic_assertions(text)

        self.assertEqual(ir.schema_version, SEMANTIC_ASSERTION_IR_VERSION)
        self.assertEqual(ir.metadata["requirement_kind"], "functional")
        self.assertEqual(ir.metadata["record_mode"], "closed_record")
        self.assertEqual(len(_entities(ir, "requirement")), 1)
        self.assertTrue(all(item.state == "asserted" for item in ir.entities if item.authority == "assertion_capable"))
        triggered = next(item for item in ir.relations if item.kind == "triggered_by")
        entity_by_id = {item.id: item for item in ir.entities}
        self.assertEqual(entity_by_id[triggered.from_id].kind, "behavior")
        self.assertEqual(entity_by_id[triggered.to_id].kind, "condition")
        self.assertEqual(triggered.state, "asserted")

    def test_negative_outcome_is_asserted_with_negative_polarity(self) -> None:
        ir = extract_semantic_assertions(
            "Acceptance criteria: 未認証利用者には機密情報を表示しない。"
        )

        criterion = _entities(ir, "acceptance_criterion")[0]
        assertion = next(item for item in ir.assertions if item.object_id == criterion.id)
        self.assertEqual((criterion.state, assertion.polarity), ("asserted", "negative"))
        self.assertEqual(_field_entities(ir, "user"), [])
        self.assertEqual(ir.metadata["record_count"], 1)

    def test_unauthed_actor_can_still_have_a_positive_asserted_action(self) -> None:
        ir = extract_semantic_assertions(
            "受入基準: 未認証利用者を監査ログに記録する。"
        )

        criterion = _entities(ir, "acceptance_criterion")[0]
        assertion = next(item for item in ir.assertions if item.object_id == criterion.id)
        self.assertEqual((criterion.state, assertion.polarity), ("asserted", "positive"))

    def test_exception_requirement_is_not_mistaken_for_an_example(self) -> None:
        ir = extract_semantic_assertions(
            "目的: 例外処理を記録する。"
            "シナリオ: 運用者が例外を検出した場合、例外記録が返る。"
            "期待結果: 例外記録が返る。"
            "受入基準: 例外記録率 100%。"
            "検証方法: pytest で例外処理を試験する。"
            "証拠: 例外試験結果。"
        )

        self.assertEqual(ir.metadata["requirement_kind"], "functional")
        self.assertEqual(ir.metadata["record_mode"], "closed_record")
        content = [item for item in ir.entities if item.id != "entity:root"]
        self.assertFalse(any(item.discourse_scope == "example" for item in content))

    def test_hostile_scenario_actor_is_not_typed_as_requirement_authority(self) -> None:
        ir = extract_semantic_assertions(
            "シナリオ: 攻撃者が不正要求を送信した場合、システムは要求を拒否する。"
        )

        actor = _entities(ir, "scenario_actor")[0]
        behavior = _entities(ir, "behavior")[0]
        result = _entities(ir, "observable_result")[0]
        self.assertEqual(actor.text, "攻撃者")
        self.assertIn("不正要求を送信", behavior.text)
        self.assertIn("システムは要求を拒否", result.text)
        self.assertNotIn("responsible", actor.kind)

    def test_explicit_absence_is_rejected_not_asserted(self) -> None:
        for text in (
            "受入基準: 未定。",
            "検証方法は実施しないこととする。",
            "Evidence: pending owner decision.",
        ):
            with self.subTest(text=text):
                ir = extract_semantic_assertions(text)
                content = [item for item in ir.entities if item.id != "entity:root"]
                self.assertTrue(content)
                self.assertTrue(all(item.state == "rejected" for item in content))
                self.assertTrue(all(item.authority == "signal_only" for item in content))

    def test_retired_or_proposed_method_is_not_current_asserted_method(self) -> None:
        cases = {
            "検証方法: ログイン認証試験を削除する。": "rejected",
            "検証方法: ログイン認証試験を中止する。": "rejected",
            "検証方法: ログイン認証試験は廃止済み。": "rejected",
            "検証方法: 検索性能 benchmark を推奨する。": "candidate",
        }
        for text, expected_state in cases.items():
            with self.subTest(text=text):
                method = _entities(extract_semantic_assertions(text), "verification_method")[0]
                self.assertEqual(method.state, expected_state)
                self.assertNotEqual(method.authority, "assertion_capable")

    def test_negative_method_content_is_not_mistaken_for_absence(self) -> None:
        ir = extract_semantic_assertions("検証方法は実行を伴わない静的解析。")

        method = _entities(ir, "verification_method")[0]
        self.assertEqual(method.state, "asserted")
        self.assertEqual(method.text, "検証方法は実行を伴わない静的解析。")

    def test_structured_and_direct_fields_can_share_one_physical_line(self) -> None:
        text = (
            "目的: 機密情報を検査する。"
            "検証方法は実行しない静的解析。"
            "証拠は保存しない機密情報の検出一覧。"
        )

        ir = extract_semantic_assertions(text)

        method = _entities(ir, "verification_method")[0]
        evidence = _entities(ir, "evidence_artifact")[0]
        self.assertEqual((method.state, evidence.state), ("asserted", "asserted"))
        self.assertEqual(method.text, "検証方法は実行しない静的解析。")
        self.assertEqual(evidence.text, "証拠は保存しない機密情報の検出一覧。")

    def test_quoted_historical_value_cannot_beat_current_rejection(self) -> None:
        text = "旧版では「検証方法: pytest」だった。\n検証方法: 未定。"

        ir = extract_semantic_assertions(text)

        methods = _field_entities(ir, "verification_method")
        self.assertEqual({item.state for item in methods}, {"candidate", "rejected"})
        self.assertEqual(ir.coverage["field_states"]["verification_method"], "rejected")
        self.assertEqual(ir.metadata["record_count"], 1)
        historical = next(item for item in methods if item.temporal_scope == "historical")
        self.assertEqual(historical.authority, "candidate_only")

    def test_quote_and_example_are_candidate_only(self) -> None:
        for text in (
            "「検証方法: pytest」",
            "例: 証拠: test-result.json",
        ):
            with self.subTest(text=text):
                ir = extract_semantic_assertions(text)
                content = [item for item in ir.entities if item.id != "entity:root"]
                self.assertTrue(content)
                self.assertTrue(all(item.state == "candidate" for item in content))
                self.assertTrue(all(item.authority == "candidate_only" for item in content))

    def test_metalinguistic_use_is_not_a_field_assertion(self) -> None:
        ir = extract_semantic_assertions("「検証方法」という語を削除する。")

        method = _entities(ir, "verification_method")[0]
        self.assertEqual(method.discourse_scope, "metalinguistic")
        self.assertEqual((method.state, method.authority), ("candidate", "candidate_only"))

    def test_adoption_proposal_is_candidate_but_normal_trigger_is_binding(self) -> None:
        proposed = extract_semantic_assertions("採用案: 検証方法: dependency parser")
        normal = extract_semantic_assertions(
            "シナリオ: 利用者が検索語を入力した場合、結果一覧が返る。"
        )

        self.assertEqual(_entities(proposed, "verification_method")[0].state, "candidate")
        scenario = _field_entities(normal, "scenario")[0]
        self.assertEqual((scenario.discourse_scope, scenario.temporal_scope, scenario.state), ("binding", "current", "asserted"))
        self.assertTrue(_field_entities(normal, "_scenario_behavior"))
        self.assertTrue(_field_entities(normal, "_scenario_result"))

    def test_morphology_is_signal_only_and_retains_valid_token_offsets(self) -> None:
        class Provider:
            def analyze(self, text: str):
                return {
                    "provider_id": "fake-morph",
                    "provider_version": "1",
                    "resource_version": "dict-1",
                    "split_mode": "C",
                    "tokens": [
                        {"surface": text, "normalized": text, "lemma": text, "pos": ["名詞"], "start": 0, "end": len(text)},
                        {"surface": "bad", "normalized": "bad", "pos": ["名詞"], "start": -1, "end": 1},
                    ],
                }

        ir = extract_semantic_assertions("曖昧な自由文", morphology_provider=Provider())

        support = next(item for item in ir.supports if item.tier == "morphology")
        attempt = next(item for item in ir.attempts if item.stage == "morphology")
        self.assertEqual((support.authority, attempt.authority), ("signal_only", "signal_only"))
        self.assertEqual(len(support.metadata["tokens"]), 1)
        self.assertIn("morphology.invalid_span:1", ir.diagnostics)
        self.assertFalse(any(item.attributes.get("source") == "morphology" for item in ir.relations))

    def test_dependency_and_llm_claims_are_forced_to_candidate_authority(self) -> None:
        text = "検索結果を返す"

        class Dependency:
            def analyze(self, _: str):
                return {
                    "provider_id": "hostile-parser",
                    "candidates": [
                        {
                            "type": "entity",
                            "kind": "behavior",
                            "start": 0,
                            "end": len(text),
                            "state": "asserted",
                            "authority": "assertion_capable",
                        }
                    ],
                }

        ir = extract_semantic_assertions(
            text,
            dependency_provider=Dependency(),
            llm_candidates=[
                {
                    "type": "assertion",
                    "kind": "behavior_claim",
                    "subject_id": "entity:root",
                    "start": 0,
                    "end": len(text),
                    "state": "asserted",
                    "authority": "assertion_capable",
                    "polarity": "positive",
                }
            ],
        )

        candidates = [
            item
            for item in (*ir.entities, *ir.assertions)
            if item.authority == "candidate_only"
        ]
        self.assertGreaterEqual(len(candidates), 2)
        self.assertTrue(all(item.state == "candidate" for item in candidates))

    def test_candidate_agreement_does_not_promote_and_conflict_is_retained(self) -> None:
        text = "検索結果を返す"

        class Dependency:
            def analyze(self, _: str):
                return {
                    "candidates": [
                        {
                            "type": "assertion",
                            "kind": "behavior_claim",
                            "subject_id": "entity:root",
                            "start": 0,
                            "end": len(text),
                            "state": "asserted",
                            "polarity": "positive",
                        }
                    ]
                }

        agreed = extract_semantic_assertions(
            text,
            dependency_provider=Dependency(),
            llm_candidates=[
                {
                    "type": "assertion",
                    "kind": "behavior_claim",
                    "subject_id": "entity:root",
                    "start": 0,
                    "end": len(text),
                    "polarity": "positive",
                }
            ],
        )
        self.assertEqual(
            [item.state for item in agreed.assertions if item.kind == "behavior_claim"],
            ["candidate", "candidate"],
        )
        self.assertEqual(agreed.coverage["candidate_conflicts"], [])

        conflicted = extract_semantic_assertions(
            text,
            dependency_provider=Dependency(),
            llm_candidates=[
                {
                    "type": "assertion",
                    "kind": "behavior_claim",
                    "subject_id": "entity:root",
                    "start": 0,
                    "end": len(text),
                    "polarity": "negative",
                }
            ],
        )
        self.assertTrue(conflicted.coverage["candidate_conflicts"])
        self.assertTrue(any(item.startswith("candidate_conflict:") for item in conflicted.diagnostics))
        self.assertTrue(all(item.state == "candidate" for item in conflicted.assertions))

    def test_invalid_dependency_and_llm_spans_are_diagnostics_not_objects(self) -> None:
        class Dependency:
            def analyze(self, _: str):
                return {"candidates": [{"type": "entity", "kind": "behavior", "start": 99, "end": 100}]}

        ir = extract_semantic_assertions(
            "短文",
            dependency_provider=Dependency(),
            llm_candidates=[{"type": "entity", "kind": "behavior", "start": -1, "end": 1}],
        )

        self.assertIn("dependency_parse.invalid_span:0", ir.diagnostics)
        self.assertIn("llm.invalid_span:0", ir.diagnostics)
        self.assertEqual([item for item in ir.entities if item.id != "entity:root"], [])

    def test_same_record_cooccurrence_does_not_assert_alignment_or_provenance(self) -> None:
        text = """目的: 検索を速くする
利用者: 運用者
シナリオ: 運用者が検索語を入力した場合、結果一覧が返る。
期待結果: 結果一覧が返る
受入基準: p95 500ms 以下
検証方法: 手動でログイン画面を見る
証拠: 任意の画面写真"""

        ir = extract_semantic_assertions(text)

        relations = {item.kind: item for item in ir.relations}
        self.assertEqual(relations["verified_by"].state, "asserted")
        self.assertEqual(relations["verifies"].state, "candidate")
        self.assertEqual(relations["produces_evidence"].state, "candidate")
        self.assertEqual(relations["verifies"].authority, "candidate_only")

    def test_one_line_fields_are_bounded_and_scope_does_not_bleed(self) -> None:
        text = (
            "目的: 検索する。 シナリオ: 利用者が検索した場合、結果が返る。 "
            "期待結果: 結果。 受入基準: p95以下。 検証方法: benchmark。 証拠: log。"
        )

        ir = extract_semantic_assertions(text)

        values = {item.attributes["field"]: item.text for item in ir.entities if "field" in item.attributes and not item.attributes["field"].startswith("_")}
        self.assertEqual(values["purpose"], "検索する。")
        self.assertEqual(values["acceptance_criteria"], "p95以下。")
        self.assertEqual(values["verification_method"], "benchmark。")
        self.assertEqual(_field_entities(ir, "scenario")[0].temporal_scope, "current")

    def test_unlabelled_second_criterion_clause_keeps_record_open(self) -> None:
        text = (
            "目的: 検索する。シナリオ: 利用者が検索した場合、結果が返る。"
            "期待結果: 結果が返る。受入基準: 検索応答時間 p95 500ms 以下。"
            "認証成功率 99% 以上。検証方法: 検索応答時間をベンチマーク測定する。"
            "証拠: 検索ベンチマーク結果。"
        )

        ir = extract_semantic_assertions(text)

        self.assertEqual(ir.metadata["record_mode"], "open_text")
        self.assertTrue(ir.coverage["unresolved"])
        self.assertEqual(len(ir.coverage["unresolved_spans"]), 1)
        unresolved = ir.coverage["unresolved_spans"][0]
        self.assertIn("認証成功率", ir.source_text[unresolved["start"] : unresolved["end"]])
        self.assertIn("structured_field.unresolved_trailing_clause", ir.diagnostics[0])

    def test_unlabelled_english_second_criterion_clause_keeps_record_open(self) -> None:
        text = (
            "Purpose: return search results. Scenario: when operator searches, results return. "
            "Expected result: results return. Acceptance criteria: search response p95 500ms. "
            "Results are complete. Verification method: search performance benchmark. "
            "Evidence: search benchmark report.json."
        )

        ir = extract_semantic_assertions(text)

        self.assertEqual(ir.metadata["record_mode"], "open_text")
        self.assertEqual(len(ir.coverage["unresolved_spans"]), 1)
        unresolved = ir.coverage["unresolved_spans"][0]
        self.assertIn("Results are complete", ir.source_text[unresolved["start"] : unresolved["end"]])

    def test_bare_condition_and_keyword_bags_do_not_close_a_record(self) -> None:
        for text in (
            "Purpose User Expected result Acceptance criteria Verification method Evidence",
            "目的 利用者 期待結果 受入基準 検証方法 証拠",
            "不合格条件: p95超過なら差し戻す",
            "条件: 100 rps",
        ):
            with self.subTest(text=text):
                ir = extract_semantic_assertions(text)
                self.assertEqual(ir.metadata["record_mode"], "open_text")
                self.assertEqual(ir.metadata["requirement_kind"], "unknown")
                self.assertFalse(any(item.state == "asserted" for item in ir.entities if item.id != "entity:root"))

    def test_repeated_core_labels_and_requirement_ids_are_multi_record(self) -> None:
        for text in (
            "目的: A\n目的: B",
            "REQ-A\nシナリオ: 利用者がAした場合、結果A。\nREQ-B\nシナリオ: 利用者がBした場合、結果B。",
        ):
            with self.subTest(text=text):
                ir = extract_semantic_assertions(text)
                self.assertGreater(ir.metadata["record_count"], 1)
                self.assertFalse(ir.metadata["single_record"])
                self.assertEqual(ir.metadata["record_mode"], "open_text")

    def test_context_uses_an_explicit_combined_offset_space(self) -> None:
        text = "目的: 検索する"
        context = "証拠: report.json"

        ir = extract_semantic_assertions(text, context)

        layout = ir.metadata["source_layout"]
        evidence = _entities(ir, "evidence_artifact")[0]
        self.assertEqual(ir.source_text[evidence.start : evidence.end], evidence.text)
        self.assertGreaterEqual(evidence.start, layout["context"]["start"])
        self.assertEqual(layout["coordinate_space"], "combined_input/v1")

    def test_serialization_is_json_safe_and_all_spans_reference_source_text(self) -> None:
        ir = extract_semantic_assertions("受入基準: 未認証利用者には表示しない。")

        payload = ir.as_dict()
        encoded = json.dumps(payload, ensure_ascii=False)
        self.assertIn(SEMANTIC_ASSERTION_IR_VERSION, encoded)
        for segment in ir.source_segments:
            self.assertEqual(ir.source_text[segment.start : segment.end], segment.text)
        for entity in ir.entities:
            self.assertEqual(ir.source_text[entity.start : entity.end], entity.text)
        for assertion in ir.assertions:
            self.assertEqual(ir.source_text[assertion.start : assertion.end], assertion.text)


if __name__ == "__main__":
    unittest.main()
