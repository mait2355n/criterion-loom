from __future__ import annotations

import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from semantic_guard_workflow.requirement_relations import (
    FUNCTIONAL_REQUIREMENT_PROFILE,
    VERIFICATION_TARGET_MISMATCH_RULE_ID,
    audit_requirement_relations,
)


class _IR(SimpleNamespace):
    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": "semantic-assertion-ir/v0",
            "source_segments": [vars(item) for item in self.source_segments],
            "entities": [vars(item) for item in self.entities],
            "assertions": [vars(item) for item in self.assertions],
            "relations": [vars(item) for item in self.relations],
            "supports": [vars(item) for item in self.supports],
            "attempts": [vars(item) for item in self.attempts],
            "coverage": self.coverage,
        }


def _entity(
    entity_id: str,
    kind: str,
    text: str,
    *,
    state: str = "asserted",
    authority: str = "assertion_capable",
    segment_id: str = "",
    **attributes: object,
) -> SimpleNamespace:
    offset = sum((index + 1) * ord(character) for index, character in enumerate(entity_id)) * 10
    return SimpleNamespace(
        id=entity_id,
        kind=kind,
        text=text,
        normalized=text.lower(),
        state=state,
        authority=authority,
        source_segment_id=segment_id,
        support_ids=["sup.direct"],
        attributes=attributes,
        confidence="high",
        start=offset,
        end=offset + len(text),
    )


def _relation(
    relation_id: str,
    kind: str,
    from_id: str,
    to_id: str,
    *,
    state: str = "asserted",
    authority: str = "assertion_capable",
) -> SimpleNamespace:
    return SimpleNamespace(
        id=relation_id,
        kind=kind,
        from_id=from_id,
        to_id=to_id,
        state=state,
        authority=authority,
        discourse_scope="binding",
        temporal_scope="current",
        support_ids=["sup.direct"],
        confidence="high",
    )


def _complete_ir(
    *,
    criterion: str = "検索応答時間 p95 500ms 以下",
    method: str = "検索応答時間を benchmark で測定する",
    evidence: str = "検索 benchmark report",
) -> _IR:
    entities = [
        _entity("ent.req", "requirement", "REQ-SEARCH-001"),
        _entity("ent.subject", "scenario_actor", "検索API"),
        _entity("ent.behavior", "behavior", "検索結果を返す"),
        _entity("ent.result", "observable_result", "検索結果が返る"),
        _entity("ent.criterion", "acceptance_criterion", criterion, segment_id="seg.criterion"),
        _entity("ent.method", "verification_method", method, segment_id="seg.method"),
        _entity("ent.evidence", "evidence_artifact", evidence, segment_id="seg.evidence"),
    ]
    relations = [
        _relation("rel.applies", "applies_to", "ent.req", "ent.subject"),
        _relation("rel.performs", "performs", "ent.subject", "ent.behavior"),
        _relation("rel.produces", "produces", "ent.behavior", "ent.result"),
        _relation("rel.constrained", "constrained_by", "ent.result", "ent.criterion"),
        _relation("rel.verified", "verified_by", "ent.req", "ent.method"),
        _relation("rel.verifies", "verifies", "ent.method", "ent.criterion"),
        _relation("rel.evidence", "produces_evidence", "ent.method", "ent.evidence"),
    ]
    segments = [
        SimpleNamespace(
            id="seg.record",
            field="record",
            text="functional requirement record",
            discourse_scope="binding",
            temporal_scope="current",
        ),
        SimpleNamespace(
            id="seg.criterion",
            field="acceptance",
            text=criterion,
            discourse_scope="binding",
            temporal_scope="current",
        ),
        SimpleNamespace(
            id="seg.method",
            field="verification",
            text=method,
            discourse_scope="binding",
            temporal_scope="current",
        ),
        SimpleNamespace(
            id="seg.evidence",
            field="evidence",
            text=evidence,
            discourse_scope="binding",
            temporal_scope="current",
        ),
    ]
    return _IR(
        source_segments=segments,
        entities=entities,
        assertions=[],
        relations=relations,
        supports=[
            SimpleNamespace(
                id="sup.direct",
                tier="structured_field",
                authority="assertion_capable",
                source_segment_id="seg.record",
            )
        ],
        attempts=[
            SimpleNamespace(
                stage="structured_field",
                status="complete",
                authority="assertion_capable",
                provider_id="builtin.structured-field",
                provider_version="v0",
                resource_version="builtin-v0",
                split_mode="labelled_field",
                executed=True,
            )
        ],
        coverage={"kind": "closed_record", "fields": ["subject", "behavior", "result", "acceptance", "verification", "evidence"]},
        metadata={
            "input_coverage": "closed_record",
            "record_mode": "closed_record",
            "requirement_kind": "functional",
            "record_count": 1,
            "single_record": True,
        },
    )


def _audit(ir: _IR):
    with patch("semantic_guard_workflow.requirement_relations.extract_semantic_assertions", return_value=ir):
        return audit_requirement_relations("ignored by patched extractor")


class RequirementRelationProfileTests(unittest.TestCase):
    def test_structured_extractor_and_profile_integrate_without_required_delta(self) -> None:
        text = """Purpose: 検索結果を返す
User: 検索API
Scenario: 検索APIが検索要求を処理した場合、検索結果を返す
Expected result: 検索結果を p95 500ms以内で返す
Acceptance criteria: 検索応答時間 p95 500ms 以下
Verification method: 検索応答時間を benchmark で測定する
Evidence: 検索 benchmark report"""

        audit = audit_requirement_relations(text)

        self.assertEqual(audit.applicability_status, "applicable")
        self.assertEqual(audit.deltas, [])
        criterion = next(
            item for item in audit.ir.entities if item.kind == "acceptance_criterion"
        )
        method = next(
            item for item in audit.ir.entities if item.kind == "verification_method"
        )
        self.assertEqual((criterion.confidence, method.confidence), ("high", "high"))

    def test_structured_extractor_derives_only_explicit_verification_mismatch(self) -> None:
        text = """Purpose: 検索結果を返す
User: 検索API
Scenario: 検索APIが検索要求を処理した場合、検索結果を返す
Expected result: 検索結果を p95 500ms以内で返す
Acceptance criteria: 検索応答時間 p95 500ms 以下
Verification method: ログイン認証を pytest で試験する
Evidence: 認証 pytest result log"""

        audit = audit_requirement_relations(text)

        mismatch = next(item for item in audit.deltas if item.kind == "verification_mismatch")
        self.assertEqual(mismatch.status, "derived")
        self.assertEqual(mismatch.rule_id, VERIFICATION_TARGET_MISMATCH_RULE_ID)
        summary = audit.public_summary()
        self.assertEqual(summary["checks"][0]["status"], "mismatch")
        self.assertEqual(
            sum(item.get("rule_id") == VERIFICATION_TARGET_MISMATCH_RULE_ID for item in summary["checks"]),
            1,
        )

    def test_retired_or_proposed_method_never_emits_mismatch_or_alignment(self) -> None:
        methods = (
            "ログイン認証試験を削除する",
            "ログイン認証試験を中止する",
            "ログイン認証試験は廃止済み",
            "検索性能 benchmark を推奨する",
        )
        for method in methods:
            with self.subTest(method=method):
                text = f"""Purpose: 検索結果を返す
User: 検索API
Scenario: 検索APIが検索要求を処理した場合、検索結果を返す
Expected result: 検索結果を p95 500ms以内で返す
Acceptance criteria: 検索応答時間 p95 500ms 以下
Verification method: {method}
Evidence: 検索 benchmark report"""

                audit = audit_requirement_relations(text)
                rule_ids = {item.rule_id for item in audit.deltas if item.rule_id}
                self.assertNotIn(VERIFICATION_TARGET_MISMATCH_RULE_ID, rule_ids)
                self.assertNotIn("func.verifies", audit.satisfied_obligation_ids)
                self.assertEqual(audit.public_summary()["checks"][0]["status"], "unknown")

    def test_unlabelled_second_criterion_clause_blocks_alignment(self) -> None:
        text = """Purpose: 検索結果を返す
User: 検索API
Scenario: 検索APIが検索要求を処理した場合、検索結果を返す
Expected result: 検索結果を p95 500ms以内で返す
Acceptance criteria: 検索応答時間 p95 500ms 以下。認証成功率 99% 以上。
Verification method: 検索応答時間 benchmark
Evidence: 検索 benchmark report"""

        audit = audit_requirement_relations(text)

        self.assertEqual(audit.applicability_status, "unknown")
        summary = audit.public_summary()
        self.assertEqual(summary["checks"][0]["status"], "unknown")
        self.assertEqual(summary["coverage"]["unresolved_span_count"], 1)
        self.assertNotIn("func.verifies", audit.satisfied_obligation_ids)

    def test_unlabelled_english_second_criterion_clause_blocks_alignment(self) -> None:
        text = (
            "Purpose: return search results. Scenario: when operator searches, results return. "
            "Expected result: results return. Acceptance criteria: search response p95 500ms. "
            "Results are complete. Verification method: search performance benchmark. "
            "Evidence: search benchmark report.json."
        )

        audit = audit_requirement_relations(text)

        self.assertEqual(audit.applicability_status, "unknown")
        self.assertEqual(audit.public_summary()["checks"][0]["status"], "unknown")
        self.assertNotIn("func.verifies", audit.satisfied_obligation_ids)

    def test_conjoined_acceptance_targets_do_not_report_alignment(self) -> None:
        for criterion in (
            "検索応答時間 p95 500ms 以下かつ検索結果が完全",
            "search response p95 500ms and results are complete",
        ):
            with self.subTest(criterion=criterion):
                audit = _audit(
                    _complete_ir(
                        criterion=criterion,
                        method="検索応答時間を benchmark で測定する",
                    )
                )

                self.assertNotIn("func.verifies", audit.satisfied_obligation_ids)
                self.assertEqual(audit.public_summary()["checks"][0]["status"], "unknown")

    def test_non_target_authentication_mentions_do_not_derive_mismatch(self) -> None:
        for method in (
            "ログイン認証を除外して pytest を実施する",
            "ログイン認証ではなく pytest で別機能を試験する",
            "ログイン認証の準備後に pytest を実施する",
        ):
            with self.subTest(method=method):
                audit = _audit(
                    _complete_ir(
                        criterion="検索応答時間 p95 500ms 以下",
                        method=method,
                    )
                )

                mismatch = next(item for item in audit.deltas if item.kind == "verification_mismatch")
                self.assertEqual(mismatch.status, "candidate")
                self.assertEqual(mismatch.rule_id, "")
                self.assertNotIn("func.verifies", audit.satisfied_obligation_ids)
                self.assertEqual(audit.public_summary()["checks"][0]["status"], "unknown")

    def test_preparation_or_metalinguistic_method_does_not_report_alignment(self) -> None:
        for method in (
            "検索性能 benchmark の準備のみ",
            "検索性能 benchmark を検討する",
            "検索性能 benchmark の名称を記録する",
        ):
            with self.subTest(method=method):
                audit = _audit(
                    _complete_ir(
                        criterion="検索応答時間 p95 500ms 以下",
                        method=method,
                    )
                )

                self.assertNotIn("func.verifies", audit.satisfied_obligation_ids)
                self.assertEqual(audit.public_summary()["checks"][0]["status"], "unknown")

    def test_open_lexical_bag_remains_unmapped_even_with_all_keywords(self) -> None:
        for text in [
            "Purpose User Expected result Acceptance criteria Verification method Evidence",
            "目的 利用者 期待結果 受入基準 検証方法 証拠",
        ]:
            with self.subTest(text=text):
                audit = audit_requirement_relations(text)

                self.assertEqual(audit.applicability_status, "unknown")
                self.assertTrue(audit.deltas)
                self.assertTrue(all(item.status != "derived" for item in audit.deltas))
                self.assertTrue(all(item.kind == "unmapped_expression" for item in audit.deltas))

    def test_structured_negative_outcome_does_not_create_a_phantom_user_record(self) -> None:
        text = """Purpose: 機密情報を表示する
User: WebUI
Scenario: WebUIが未認証アクセスを処理した場合、機密情報を非表示にする
Expected result: 権限に応じた表示結果
Acceptance criteria: 未認証利用者には機密情報を表示しない
Verification method: 未認証表示制御 pytest
Evidence: 認証 pytest result log"""

        audit = audit_requirement_relations(text)

        self.assertEqual(audit.applicability_status, "applicable")
        subjects = [
            item for item in audit.ir.entities if item.kind == "scenario_actor"
        ]
        self.assertEqual(len(subjects), 2)
        self.assertEqual({item.text for item in subjects}, {"WebUI"})
        criterion = next(
            item for item in audit.ir.entities if item.kind == "acceptance_criterion"
        )
        self.assertEqual(criterion.state, "asserted")
        self.assertFalse(any(item.kind == "missing_node" for item in audit.deltas))

    def test_profile_declares_required_and_conditional_edges_stably(self) -> None:
        payload = FUNCTIONAL_REQUIREMENT_PROFILE.as_dict()

        self.assertEqual(payload["schema_version"], "requirement-relation-profile/v0")
        self.assertEqual(payload["profile_id"], "functional-requirement-record/v0")
        self.assertEqual(
            [item["id"] for item in payload["relation_obligations"]],
            [
                "func.applies_to",
                "func.performs",
                "func.acts_on",
                "func.triggered_by",
                "func.produces",
                "func.constrained_by",
                "func.uses_metric",
                "func.verified_by",
                "func.verifies",
                "func.measures",
                "func.produces_evidence",
            ],
        )

    def test_complete_closed_record_satisfies_required_edges_without_delta(self) -> None:
        audit = _audit(_complete_ir())

        self.assertEqual(audit.deltas, [])
        self.assertEqual(
            audit.satisfied_obligation_ids,
            [
                "func.applies_to",
                "func.constrained_by",
                "func.performs",
                "func.produces",
                "func.produces_evidence",
                "func.verified_by",
                "func.verifies",
            ],
        )

    def test_open_unmapped_text_does_not_derive_missing_nodes(self) -> None:
        ir = _IR(
            source_segments=[],
            entities=[],
            assertions=[],
            relations=[],
            supports=[],
            attempts=[SimpleNamespace(stage="direct_rule", status="unresolved")],
            coverage={"kind": "open_text", "unresolved_spans": [[0, 25]]},
            metadata={"input_coverage": "open_text"},
        )

        audit = _audit(ir)

        self.assertTrue(audit.deltas)
        self.assertTrue(all(item.kind == "unmapped_expression" for item in audit.deltas))
        self.assertTrue(all(item.status == "blocked_by_unknown" for item in audit.deltas))

    def test_candidate_dependency_or_llm_relation_never_satisfies_obligation(self) -> None:
        for authority in ["candidate_only", "signal_only"]:
            with self.subTest(authority=authority):
                ir = _complete_ir()
                relation = next(item for item in ir.relations if item.id == "rel.verified")
                relation.state = "candidate"
                relation.authority = authority

                audit = _audit(ir)

                self.assertNotIn("func.verified_by", audit.satisfied_obligation_ids)
                delta = next(item for item in audit.deltas if item.obligation_id == "func.verified_by")
                self.assertEqual(delta.kind, "ambiguous_scope")
                self.assertEqual(delta.status, "candidate")

    def test_missing_authority_support_or_scope_never_satisfies(self) -> None:
        for mutation in ["authority", "support", "scope"]:
            with self.subTest(mutation=mutation):
                ir = _complete_ir()
                relation = next(item for item in ir.relations if item.id == "rel.verified")
                if mutation == "authority":
                    relation.authority = ""
                elif mutation == "support":
                    relation.support_ids = []
                else:
                    relation.discourse_scope = ""
                    relation.temporal_scope = ""
                    relation.support_ids = ["sup.no-scope"]
                    ir.supports.append(
                        SimpleNamespace(
                            id="sup.no-scope",
                            tier="structured_field",
                            authority="assertion_capable",
                            source_segment_id="",
                        )
                    )

                audit = _audit(ir)

                self.assertNotIn("func.verified_by", audit.satisfied_obligation_ids)
                self.assertTrue(
                    any(item.obligation_id == "func.verified_by" for item in audit.deltas)
                )

    def test_candidate_support_does_not_downgrade_independent_asserted_support(self) -> None:
        ir = _complete_ir()
        relation = next(item for item in ir.relations if item.id == "rel.verified")
        relation.support_ids.append("sup.llm")
        ir.supports.append(
            SimpleNamespace(
                id="sup.llm",
                tier="llm",
                authority="candidate_only",
                source_segment_id="seg.record",
            )
        )

        audit = _audit(ir)

        self.assertIn("func.verified_by", audit.satisfied_obligation_ids)

    def test_quote_history_conditional_and_metalinguistic_segments_do_not_satisfy(self) -> None:
        for discourse, temporal in [
            ("quoted", "current"),
            ("binding", "historical"),
            ("example", "current"),
            ("metalinguistic", "current"),
        ]:
            with self.subTest(discourse=discourse, temporal=temporal):
                ir = _complete_ir()
                method = next(item for item in ir.entities if item.id == "ent.method")
                segment = next(item for item in ir.source_segments if item.id == "seg.method")
                segment.discourse_scope = discourse
                segment.temporal_scope = temporal

                audit = _audit(ir)

                self.assertNotIn("func.verified_by", audit.satisfied_obligation_ids)
                self.assertTrue(
                    any(item.obligation_id == "func.verified_by" for item in audit.deltas)
                )

    def test_negative_outcome_is_an_asserted_acceptance_criterion(self) -> None:
        audit = _audit(
            _complete_ir(
                criterion="未認証利用者には機密情報を表示しない",
                method="未認証表示制御 pytest",
                evidence="認証 pytest result log",
            )
        )

        self.assertIn("func.constrained_by", audit.satisfied_obligation_ids)
        self.assertNotIn("func.verifies", audit.satisfied_obligation_ids)
        self.assertEqual(audit.public_summary()["checks"][0]["status"], "unknown")
        self.assertFalse(any(item.kind == "missing_node" for item in audit.deltas))

    def test_explicit_absence_in_closed_record_derives_missing_node(self) -> None:
        ir = _complete_ir()
        criterion = next(item for item in ir.entities if item.id == "ent.criterion")
        criterion.state = "rejected"

        audit = _audit(ir)

        missing = [item for item in audit.deltas if item.kind == "missing_node"]
        self.assertTrue(missing)
        self.assertTrue(all(item.status == "derived" for item in missing))

    def test_bare_verification_dimension_mismatch_remains_candidate_and_not_satisfied(self) -> None:
        audit = _audit(
            _complete_ir(
                criterion="検索応答時間 p95 500ms 以下",
                method="ログイン認証 pytest",
            )
        )

        mismatch = next(item for item in audit.deltas if item.kind == "verification_mismatch")
        self.assertEqual(mismatch.status, "candidate")
        self.assertEqual(mismatch.rule_id, "")
        self.assertNotIn("func.verifies", audit.satisfied_obligation_ids)
        public = audit.public_summary()
        check = public["checks"][0]
        self.assertEqual(check["check_id"], "verification_verifies_acceptance")
        self.assertEqual(check["status"], "unknown")
        self.assertEqual(check["derivation_status"], "candidate")
        self.assertEqual(len(check["evidence_spans"]), 2)
        self.assertEqual({item["field"] for item in check["evidence_spans"]}, {"acceptance", "verification"})

    def test_matching_search_benchmark_has_no_verification_mismatch(self) -> None:
        audit = _audit(
            _complete_ir(
                criterion="検索応答時間 p95 500ms 以下",
                method="検索応答時間 benchmark",
            )
        )

        self.assertFalse(any(item.kind == "verification_mismatch" for item in audit.deltas))
        self.assertIn("func.verifies", audit.satisfied_obligation_ids)

    def test_multiple_method_dimensions_remain_unknown_without_derived_mismatch(self) -> None:
        audit = _audit(
            _complete_ir(
                criterion="検索応答時間 p95 500ms 以下",
                method="検索応答時間 benchmark とログイン認証 pytest",
            )
        )

        mismatch = next(item for item in audit.deltas if item.kind == "verification_mismatch")
        self.assertEqual(mismatch.status, "candidate")
        self.assertEqual(mismatch.rule_id, "")
        self.assertNotIn("func.verifies", audit.satisfied_obligation_ids)
        verification_check = audit.public_summary()["checks"][0]
        self.assertEqual(verification_check["check_id"], "verification_verifies_acceptance")
        self.assertEqual(verification_check["status"], "unknown")
        self.assertEqual(verification_check["derivation_status"], "candidate")

    def test_low_confidence_or_nonmeasurement_wording_cannot_derive_mismatch(self) -> None:
        ir = _complete_ir(
            criterion="検索応答時間 p95 500ms 以下",
            method="ログイン認証 pytest を準備する予定",
        )

        audit = _audit(ir)

        mismatch = next(item for item in audit.deltas if item.kind == "verification_mismatch")
        self.assertEqual(mismatch.status, "candidate")
        self.assertEqual(mismatch.rule_id, "")
        self.assertFalse(any(item.status == "derived" for item in audit.deltas))

    def test_multiple_unpaired_asserted_targets_never_use_an_arbitrary_pair(self) -> None:
        ir = _complete_ir(
            criterion="検索応答時間 p95 500ms 以下",
            method="ログイン認証 pytest",
        )
        ir.entities.extend(
            [
                _entity("ent.criterion.2", "acceptance_criterion", "認証成功率 99%"),
                _entity("ent.method.2", "verification_method", "検索応答時間 benchmark"),
            ]
        )
        ir.relations.extend(
            [
                _relation("rel.verifies.2", "verifies", "ent.method.2", "ent.criterion.2"),
            ]
        )

        audit = _audit(ir)

        self.assertFalse(
            any(item.kind == "verification_mismatch" and item.status == "derived" for item in audit.deltas)
        )
        ambiguity = next(
            item
            for item in audit.deltas
            if item.kind == "ambiguous_scope" and item.obligation_id == "func.verifies"
        )
        self.assertEqual(ambiguity.status, "conflict")
        self.assertNotIn("func.verifies", audit.satisfied_obligation_ids)

    def test_open_or_multi_record_input_cannot_derive_mismatch_or_missing(self) -> None:
        open_ir = _complete_ir(
            criterion="検索応答時間 p95 500ms 以下",
            method="ログイン認証 pytest",
        )
        open_ir.coverage["kind"] = "open_text"
        open_ir.metadata["record_mode"] = "open_text"
        open_ir.metadata["input_coverage"] = "open_text"
        multi_ir = _complete_ir(
            criterion="検索応答時間 p95 500ms 以下",
            method="ログイン認証 pytest",
        )
        multi_ir.entities.append(_entity("ent.req.2", "requirement", "REQ-OTHER-002"))
        multi_ir.metadata["record_count"] = 2
        multi_ir.metadata["single_record"] = False

        for ir in [open_ir, multi_ir]:
            with self.subTest(mode=ir.metadata["record_mode"], records=ir.metadata["record_count"]):
                audit = _audit(ir)
                self.assertEqual(audit.satisfied_obligation_ids, [])
                self.assertFalse(any(item.status == "derived" for item in audit.deltas))
                self.assertFalse(any(item.kind == "verification_mismatch" for item in audit.deltas))

    def test_unknown_requirement_kind_is_unknown_not_not_applicable(self) -> None:
        ir = _complete_ir()
        ir.metadata["requirement_kind"] = "unknown"

        audit = _audit(ir)

        self.assertEqual(audit.applicability_status, "unknown")
        self.assertEqual(audit.public_summary()["checks"][0]["status"], "unknown")

    def test_explicit_nonfunctional_kind_is_not_applicable(self) -> None:
        ir = _complete_ir()
        ir.metadata["requirement_kind"] = "quality-only"

        audit = _audit(ir)

        self.assertEqual(audit.applicability_status, "not_applicable")
        self.assertEqual(audit.public_summary()["checks"][0]["status"], "not_applicable")
        self.assertFalse(any(item.status == "derived" for item in audit.deltas))

    def test_aligned_public_evidence_uses_the_unique_verifies_pair(self) -> None:
        ir = _complete_ir()
        ir.entities.insert(
            0,
            _entity("ent.method.unpaired", "verification_method", "ログイン認証 pytest"),
        )
        ir.entities.insert(
            0,
            _entity("ent.criterion.unpaired", "acceptance_criterion", "認証成功率 99%"),
        )

        audit = _audit(ir)
        check = audit.public_summary()["checks"][0]

        self.assertEqual(check["status"], "aligned")
        self.assertEqual(
            [item["excerpt"] for item in check["evidence_spans"]],
            ["検索応答時間 p95 500ms 以下", "検索応答時間を benchmark で測定する"],
        )

    def test_unrelated_sast_evidence_is_reported_as_evidence_disconnect(self) -> None:
        audit = _audit(
            _complete_ir(
                method="検索応答時間 benchmark",
                evidence="SAST security log",
            )
        )

        disconnect = next(item for item in audit.deltas if item.kind == "evidence_disconnect")
        self.assertEqual(disconnect.status, "derived")
        self.assertEqual(disconnect.obligation_id, "func.produces_evidence")
        self.assertNotIn("func.produces_evidence", audit.satisfied_obligation_ids)

    def test_internal_and_public_summaries_are_json_stable(self) -> None:
        audit = _audit(_complete_ir())

        internal = json.dumps(audit.as_dict(), ensure_ascii=False, sort_keys=True)
        public = json.dumps(audit.public_summary(), ensure_ascii=False, sort_keys=True)

        self.assertIn('"schema_version": "requirement-relation-audit/v0"', internal)
        self.assertIn('"schema_version": "requirement-relation-summary/v1"', public)
        self.assertNotIn("semantic_assertion_ir", public)
        summary = audit.public_summary()
        self.assertEqual(summary["extractor_stages"], ["structured_field"])
        self.assertEqual(summary["attempts"][0]["provider_id"], "builtin.structured-field")
        self.assertEqual(summary["attempts"][0]["resource_version"], "builtin-v0")
        self.assertEqual(summary["checks"][0]["check_id"], "verification_verifies_acceptance")
        self.assertEqual(summary["checks"][0]["status"], "aligned")
        self.assertEqual(summary["checks"][0]["derivation_status"], "satisfied")
        self.assertEqual(len(summary["checks"][0]["evidence_spans"]), 2)
        self.assertNotIn("unresolved_spans", summary["coverage"])
        self.assertFalse(any(name.startswith("_") for name in summary["coverage"]["field_names"]))

    def test_public_summary_reports_candidate_conflict_count_and_source_coordinates(self) -> None:
        text = """Purpose: 検索結果を返す
User: 検索API
Scenario: 検索APIが検索要求を処理した場合、検索結果を返す
Expected result: 検索結果を p95 500ms以内で返す
Acceptance criteria: 検索応答時間 p95 500ms 以下
Verification method: ログイン認証 pytest
Evidence: 認証 pytest result log"""
        audit = audit_requirement_relations(text)
        audit.ir.coverage["candidate_conflicts"] = [{"resolution": "unresolved"}]

        summary = audit.public_summary()

        self.assertEqual(summary["coverage"]["candidate_conflict_count"], 1)
        spans = summary["checks"][0]["evidence_spans"]
        self.assertEqual({item["coordinate_space"] for item in spans}, {"combined_input/v1"})
        self.assertEqual({item["source_part"] for item in spans}, {"text"})


if __name__ == "__main__":
    unittest.main()
