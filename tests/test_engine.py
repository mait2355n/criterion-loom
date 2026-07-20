from __future__ import annotations

import hashlib
import unittest

from semantic_guard.engine import audit_requirement_relations
from semantic_guard.llm_candidates import SubmittedLLMCandidateProvider
from semantic_guard.provider_receipts import (
    AnalyzerQualification,
    QualifiedAnalyzerRegistry,
)
from semantic_guard.providers import (
    AnalysisAttempt,
    AnalysisSpan,
    ProviderAuthority,
    ProviderRequest,
    RelationCandidate,
    ScopeCandidate,
    TokenCandidate,
)
from semantic_guard.reassessment import REQUIRED_CAPABILITIES, policy_scope
from semantic_guard.public_contract import public_audit_payload
from semantic_guard.assurance_graph import (
    public_assurance_claim_v1,
    validate_assurance_claim_v1,
)


COMPLETE = """Purpose: 検索APIが検索結果を p95 500ms以内で返す
User: 検索API
Scenario: 検索APIが検索要求を処理して検索結果を返す
Expected result: 検索結果を p95 500ms以内で返す
Acceptance criteria: 検索応答時間 p95 500ms 以下
Verification method: 検索結果の検索応答時間を benchmark で測定する
Evidence: 検索結果の検索応答時間 benchmark report"""


class HostileMorphologyProvider:
    provider_id = "hostile-morphology"
    provider_version = "1"
    resource_version = "test"
    stage = "morphology"

    def analyze(self, request: ProviderRequest) -> AnalysisAttempt:
        return AnalysisAttempt(
            stage="morphology",
            provider_id=self.provider_id,
            provider_version=self.provider_version,
            resource_version=self.resource_version,
            status="ok",
            authority=ProviderAuthority(
                support=True,
                challenge_signal=True,
                apply_hold=True,
                release_hold=True,
            ),
            requested_capabilities=request.requested_capabilities,
            fulfilled_capabilities=request.requested_capabilities,
            covered_spans=request.target_spans,
            tokens=(
                TokenCandidate(
                    surface=request.text[0:1],
                    lemma="ない",
                    normalized="ない",
                    part_of_speech=("助動詞",),
                    start=0,
                    end=1,
                ),
            ),
        )


class HostileDependencyProvider:
    provider_id = "hostile-dependency"
    provider_version = "1"
    resource_version = "test"
    stage = "dependency_parse"

    def analyze(self, request: ProviderRequest) -> AnalysisAttempt:
        return AnalysisAttempt(
            stage="dependency_parse",
            provider_id=self.provider_id,
            provider_version=self.provider_version,
            resource_version=self.resource_version,
            status="ok",
            authority=ProviderAuthority(
                support=True,
                challenge_signal=True,
                apply_hold=True,
                release_hold=True,
            ),
            requested_capabilities=request.requested_capabilities,
            fulfilled_capabilities=request.requested_capabilities,
            covered_spans=request.target_spans,
            relations=(
                RelationCandidate(
                    relation_kind="produces",
                    from_span=AnalysisSpan(0, 1, "fabricated-from"),
                    to_span=AnalysisSpan(2, 3, "fabricated-to"),
                    confidence=1.0,
                    interpretation_id="interpretation.fabricated",
                    rationale="provider assertion deliberately conflicts with direct spans",
                ),
            ),
        )


class FailingMorphologyProvider:
    provider_id = "failing-morphology"
    provider_version = "1"
    resource_version = "test"
    stage = "morphology"

    def analyze(self, request: ProviderRequest) -> AnalysisAttempt:
        raise RuntimeError("planned provider failure")


class EmptyMorphologyProvider:
    provider_id = "empty-morphology"
    provider_version = "1"
    resource_version = "test"
    stage = "morphology"

    def analyze(self, request: ProviderRequest) -> AnalysisAttempt:
        start = next(
            (span.start for span in request.target_spans if span.start < span.end),
            0,
        )
        return AnalysisAttempt(
            stage="morphology",
            provider_id=self.provider_id,
            provider_version=self.provider_version,
            resource_version=self.resource_version,
            status="ok",
            authority=ProviderAuthority(),
            requested_capabilities=request.requested_capabilities,
            fulfilled_capabilities=request.requested_capabilities,
            covered_spans=request.target_spans,
            tokens=(
                TokenCandidate(
                    surface=request.text[start : start + 1],
                    lemma=request.text[start : start + 1],
                    normalized=request.text[start : start + 1],
                    part_of_speech=("fixture",),
                    start=start,
                    end=start + 1,
                ),
            ),
        )


class EmptyLLMProvider:
    provider_id = "empty-llm"
    provider_version = "1"
    resource_version = "test"
    stage = "llm_candidate"

    def analyze(self, request: ProviderRequest) -> AnalysisAttempt:
        return AnalysisAttempt(
            stage="llm_candidate",
            provider_id=self.provider_id,
            provider_version=self.provider_version,
            resource_version=self.resource_version,
            status="ok",
            authority=ProviderAuthority(),
            requested_capabilities=request.requested_capabilities,
            fulfilled_capabilities=request.requested_capabilities,
            covered_spans=request.target_spans,
        )


class ConditionDependencyProvider:
    provider_id = "condition-dependency"
    provider_version = "1"
    resource_version = "test"
    stage = "dependency_parse"

    def analyze(self, request: ProviderRequest) -> AnalysisAttempt:
        cue_start = request.text.index("場合は")
        target_start = request.text.index("返す", request.text.index("Scenario:"))
        cue = AnalysisSpan(cue_start, cue_start + len("場合は"), "condition")
        target = AnalysisSpan(
            target_start, target_start + len("返す"), "predicate"
        )
        return AnalysisAttempt(
            stage="dependency_parse",
            provider_id=self.provider_id,
            provider_version=self.provider_version,
            resource_version=self.resource_version,
            status="ok",
            authority=ProviderAuthority(),
            requested_capabilities=request.requested_capabilities,
            fulfilled_capabilities=request.requested_capabilities,
            covered_spans=request.target_spans,
            relations=(
                RelationCandidate(
                    relation_kind="dependency:advcl",
                    from_span=cue,
                    to_span=target,
                ),
            ),
            scopes=(ScopeCandidate("condition", cue, target),),
        )


class ProjectingConditionDependencyProvider:
    provider_id = "projecting-condition-dependency"
    provider_version = "1"
    resource_version = "test"
    stage = "dependency_parse"

    def analyze(self, request: ProviderRequest) -> AnalysisAttempt:
        cue_start = request.text.index("だけ")
        target_start = request.text.index("返す", request.text.index("Scenario:"))
        cue = AnalysisSpan(cue_start, cue_start + len("だけ"), "condition")
        target = AnalysisSpan(
            target_start, target_start + len("返す"), "predicate"
        )
        return AnalysisAttempt(
            stage="dependency_parse",
            provider_id=self.provider_id,
            provider_version=self.provider_version,
            resource_version=self.resource_version,
            status="ok",
            authority=ProviderAuthority(),
            requested_capabilities=request.requested_capabilities,
            fulfilled_capabilities=request.requested_capabilities,
            covered_spans=request.target_spans,
            relations=(
                RelationCandidate(
                    relation_kind="dependency:advcl",
                    from_span=cue,
                    to_span=target,
                    interpretation_id="dependency.condition.edge",
                ),
            ),
            scopes=(ScopeCandidate("condition", cue, target),),
        )


class ParserOnlyQuotationProvider:
    provider_id = "parser-only-quotation"
    provider_version = "1"
    resource_version = "test"
    stage = "dependency_parse"

    def analyze(self, request: ProviderRequest) -> AnalysisAttempt:
        cue_start = request.text.index("p95")
        target_start = request.text.index("500ms")
        cue = AnalysisSpan(cue_start, cue_start + len("p95"), "quotation")
        target = AnalysisSpan(target_start, target_start + len("500ms"), "target")
        return AnalysisAttempt(
            stage="dependency_parse",
            provider_id=self.provider_id,
            provider_version=self.provider_version,
            resource_version=self.resource_version,
            status="ok",
            authority=ProviderAuthority(),
            requested_capabilities=request.requested_capabilities,
            fulfilled_capabilities=request.requested_capabilities,
            covered_spans=request.target_spans,
            relations=(RelationCandidate("dependency:dep", cue, target),),
            scopes=(ScopeCandidate("quotation", cue, target),),
        )


class CapturingLLMProvider:
    provider_id = "capturing-llm"
    provider_version = "1"
    resource_version = "test"
    stage = "llm_candidate"

    def __init__(self) -> None:
        self.request: ProviderRequest | None = None

    def analyze(self, request: ProviderRequest) -> AnalysisAttempt:
        self.request = request
        return AnalysisAttempt(
            stage="llm_candidate",
            provider_id=self.provider_id,
            provider_version=self.provider_version,
            resource_version=self.resource_version,
            status="ok",
            authority=ProviderAuthority(),
            requested_capabilities=request.requested_capabilities,
            fulfilled_capabilities=request.requested_capabilities,
            covered_spans=request.target_spans,
        )


class QualifiedRelationDependencyProvider:
    provider_id = "qualified-relation-dependency"
    provider_version = "1"
    resource_version = "fixture-1"
    stage = "dependency_parse"

    def analyze(self, request: ProviderRequest) -> AnalysisAttempt:
        scenario_start = request.text.index("Scenario:")
        actor_start = request.text.index("検索API", scenario_start)
        object_start = request.text.index("検索要求", scenario_start)
        predicate_start = request.text.index("査定", scenario_start)
        actor = AnalysisSpan(actor_start, actor_start + len("検索API"), "actor")
        obj = AnalysisSpan(object_start, object_start + len("検索要求"), "object")
        predicate = AnalysisSpan(
            predicate_start,
            predicate_start + len("査定"),
            "predicate",
        )
        return AnalysisAttempt(
            stage=self.stage,
            provider_id=self.provider_id,
            provider_version=self.provider_version,
            resource_version=self.resource_version,
            status="ok",
            authority=ProviderAuthority(
                support=True,
                challenge_signal=True,
                apply_hold=True,
                release_hold=True,
            ),
            requested_capabilities=request.requested_capabilities,
            fulfilled_capabilities=request.requested_capabilities,
            covered_spans=request.target_spans,
            relations=(
                RelationCandidate("dependency:nsubj", actor, predicate),
                RelationCandidate("dependency:obj", obj, predicate),
            ),
        )


def _qualified_relation_registry() -> QualifiedAnalyzerRegistry:
    return QualifiedAnalyzerRegistry(
        tuple(
            AnalyzerQualification(
                provider_id=QualifiedRelationDependencyProvider.provider_id,
                provider_version=QualifiedRelationDependencyProvider.provider_version,
                resource_version=QualifiedRelationDependencyProvider.resource_version,
                capabilities=REQUIRED_CAPABILITIES,
                policy_scope=policy_scope(obligation_id),
                qualification_basis="controlled engine integration fixture",
            )
            for obligation_id in ("func.performs", "func.acts_on")
        )
    )


class EngineTests(unittest.TestCase):
    def test_only_qualified_receipt_bound_policy_can_promote_unresolved_relations(self) -> None:
        text = COMPLETE.replace(
            "検索APIが検索要求を処理して検索結果を返す",
            "ここで、検索APIが検索要求を査定して検索結果を返す",
        )
        providers = {
            "morphology_provider": EmptyMorphologyProvider(),
            "dependency_provider": QualifiedRelationDependencyProvider(),
            "analysis_mode": "conditional",
        }
        unqualified = audit_requirement_relations(text, **providers)
        qualified = audit_requirement_relations(
            text,
            **providers,
            analyzer_registry=_qualified_relation_registry(),
        )
        unqualified_by_id = {
            item.obligation_id: item for item in unqualified.result.obligations
        }
        qualified_by_id = {
            item.obligation_id: item for item in qualified.result.obligations
        }

        self.assertEqual(unqualified_by_id["func.performs"].outcome.value, "undetermined")
        self.assertEqual(qualified_by_id["func.performs"].outcome.value, "satisfied")
        self.assertEqual(qualified_by_id["func.acts_on"].outcome.value, "satisfied")
        self.assertTrue(qualified.result.is_pass)
        self.assertTrue(qualified.provider_execution_receipts)
        self.assertEqual(len(qualified.analyzer_qualifications), 1)
        performs_reassessment = next(
            item
            for item in qualified.obligation_reassessments
            if item.obligation_id == "func.performs"
        )
        self.assertIn(
            performs_reassessment.unresolved_id,
            {
                item.unresolved_id
                for item in qualified.initial_unresolved_obligations
            },
        )
        self.assertEqual(
            performs_reassessment.as_dict()["route_status"],
            "resolved_by_reassessment",
        )
        self.assertNotIn(
            "func.performs",
            {
                item.obligation_id
                for item in qualified.remaining_unresolved_obligations
            },
        )
        self.assertEqual(
            qualified.unresolved_obligations,
            qualified.remaining_unresolved_obligations,
        )
        self.assertTrue(
            any(
                item.authority.stage_id == "obligation-reassessment-policy/v0"
                and item.authority.support
                for item in qualified_by_id["func.performs"].provenance
            )
        )
        self.assertFalse(
            next(
                item
                for item in qualified.analysis_attempts
                if item.stage == "dependency_parse"
            ).authority.support
        )
        with self.assertRaisesRegex(ValueError, "audit-result/v0 cannot replay"):
            public_audit_payload(
                qualified,
                recorded_at="2026-07-16T00:00:00Z",
            )
        validate_assurance_claim_v1(
            public_assurance_claim_v1(
                qualified,
                recorded_at="2026-07-16T00:00:00Z",
            )
        )

    def test_shadow_reassessment_cannot_change_result(self) -> None:
        text = COMPLETE.replace(
            "検索APIが検索要求を処理して検索結果を返す",
            "ここで、検索APIが検索要求を査定して検索結果を返す",
        )
        providers = {
            "morphology_provider": EmptyMorphologyProvider(),
            "dependency_provider": QualifiedRelationDependencyProvider(),
            "analysis_mode": "shadow_all",
        }
        unqualified = audit_requirement_relations(text, **providers)
        qualified = audit_requirement_relations(
            text,
            **providers,
            analyzer_registry=_qualified_relation_registry(),
        )

        self.assertEqual(unqualified.result.as_dict(), qualified.result.as_dict())
        self.assertTrue(
            all(
                item.decision in {"preserved", "shadow_observation"}
                for item in qualified.obligation_reassessments
            )
        )

    def test_actor_as_object_cannot_terminally_pass_conditional_mode(self) -> None:
        text = COMPLETE.replace(
            "検索APIが検索要求を処理して検索結果を返す",
            "システムが検索APIを検索して検索結果を返す",
        )
        report = audit_requirement_relations(text, analysis_mode="conditional")
        performs = next(
            item for item in report.result.obligations if item.obligation_id == "func.performs"
        )

        self.assertEqual(performs.outcome.value, "undetermined")
        self.assertEqual(report.result.workflow.value, "warn")

    def test_default_assurance_mode_cannot_pass_when_required_providers_are_absent(self) -> None:
        report = audit_requirement_relations(COMPLETE)

        self.assertFalse(report.result.is_pass)
        self.assertEqual(report.analysis_mode, "assurance")
        self.assertEqual(
            set(report.result.execution.provider_failures),
            {
                "morphology:not_configured",
                "dependency_parse:not_configured",
                "llm_candidate:not_configured",
            },
        )

    def test_empty_input_is_explicitly_unresolved_not_an_exception(self) -> None:
        report = audit_requirement_relations("")

        self.assertFalse(report.result.is_pass)
        self.assertEqual(report.record.record_count, 0)
        self.assertIn(
            "record_boundary_not_single",
            {item.reason_code for item in report.residual_signals},
        )

    def test_explicit_conditional_mode_can_pass_without_optional_analysis(self) -> None:
        report = audit_requirement_relations(
            COMPLETE,
            analysis_mode="conditional",
        )

        self.assertEqual(report.record.record_mode, "closed_record")
        self.assertEqual(report.residual_signals, ())
        self.assertEqual(report.analysis_attempts, ())
        self.assertTrue(report.result.is_pass)

    def test_reported_speech_never_inherits_direct_satisfaction(self) -> None:
        text = COMPLETE.replace(
            "検索応答時間 p95 500ms 以下",
            "担当者によれば検索応答時間 p95 500ms 以下",
        )
        report = audit_requirement_relations(text)

        self.assertFalse(report.result.is_pass)
        self.assertIn(
            "reported_speech_present",
            {item.reason_code for item in report.residual_signals},
        )
        self.assertTrue(report.result.decision_requests)
        self.assertTrue(any(item.open_holds for item in report.result.obligations))

    def test_negated_criterion_never_becomes_terminal_satisfaction(self) -> None:
        text = COMPLETE.replace(
            "検索応答時間 p95 500ms 以下",
            "検索応答時間 p95 500ms 以下とは定めない",
        )
        report = audit_requirement_relations(text)

        self.assertFalse(report.result.is_pass)
        self.assertIn(
            "negation_scope_present",
            {item.reason_code for item in report.residual_signals},
        )

    def test_compound_scope_bypass_never_becomes_terminal_satisfaction(self) -> None:
        text = COMPLETE.replace(
            "検索応答時間 p95 500ms 以下",
            "担当者曰く【障害時だけ検索応答時間 p95 500ms 以下を認めない】は草案の文言にすぎぬ",
            1,
        )
        report = audit_requirement_relations(text)

        self.assertFalse(report.result.is_pass)
        self.assertNotEqual(report.result.finality.value, "terminal")
        self.assertGreaterEqual(len(report.residual_signals), 5)

    def test_unrelated_purpose_cannot_pass_by_structural_co_location(self) -> None:
        report = audit_requirement_relations(
            COMPLETE.replace("検索APIが検索結果を p95 500ms以内で返す", "請求書を破棄する", 1)
        )

        self.assertFalse(report.result.is_pass)
        by_id = {item.obligation_id: item for item in report.result.obligations}
        self.assertEqual(by_id["func.applies_to"].outcome.value, "undetermined")

    def test_shared_domain_word_cannot_hide_causal_and_constraint_mismatch(self) -> None:
        text = """目的: 検索機能を提供する
利用者: 検索API
シナリオ: 検索APIが検索要求を処理する
期待結果: 検索ログは削除される
受入基準: 検索応答時間は100ms以内
検証方法: 検索応答時間を測定する
証拠: 検索応答時間CSV"""

        report = audit_requirement_relations(text)
        by_id = {item.obligation_id: item for item in report.result.obligations}

        self.assertFalse(report.result.is_pass)
        self.assertEqual(by_id["func.produces"].outcome.value, "undetermined")
        self.assertEqual(
            by_id["func.constrained_by"].outcome.value,
            "undetermined",
        )

    def test_same_endpoint_with_opposing_actions_cannot_pass(self) -> None:
        text = """目的: 検索APIが監査対象ログ・audit_logを保存する
利用者: 検索API
シナリオ: 検索APIが監査対象ログ・audit_logを保存する
期待結果: 監査対象ログ・audit_logを100ms以内に削除する
受入基準: 監査対象ログ削除時間は100ms以内
検証方法: 監査対象ログ削除時間を測定する
証拠: 監査対象ログ削除時間CSV"""

        report = audit_requirement_relations(text)
        by_id = {item.obligation_id: item for item in report.result.obligations}

        self.assertFalse(report.result.is_pass)
        self.assertEqual(report.result.workflow.value, "block")
        self.assertEqual(by_id["func.produces"].outcome.value, "refuted")

    def test_open_text_cannot_pass_as_a_closed_record(self) -> None:
        report = audit_requirement_relations(
            COMPLETE + "\nこの行の意味役割は宣言されていない。"
        )

        self.assertFalse(report.result.is_pass)
        self.assertEqual(report.record.record_mode, "open_text")
        self.assertTrue(report.result.execution.open_holds)

    def test_required_provider_failure_is_evidence_not_silent_success(self) -> None:
        text = COMPLETE.replace(
            "検索応答時間 p95 500ms 以下",
            "検索応答時間 p95 500ms 以下とは定めない",
        )
        report = audit_requirement_relations(
            text,
            morphology_provider=FailingMorphologyProvider(),
        )

        self.assertFalse(report.result.is_pass)
        self.assertIn("morphology:failed", report.result.execution.provider_failures)

    def test_versioned_lifting_can_close_one_unambiguous_condition_attachment(self) -> None:
        text = COMPLETE.replace(
            "検索要求を処理して検索結果を返す",
            "検索要求を処理した場合は検索結果を返す",
        )
        report = audit_requirement_relations(
            text,
            morphology_provider=EmptyMorphologyProvider(),
            dependency_provider=ConditionDependencyProvider(),
            llm_provider=EmptyLLMProvider(),
        )

        self.assertTrue(report.result.is_pass)
        self.assertIn("resolved", {item.status for item in report.lifting_resolutions})
        released_holds = [
            hold
            for obligation in report.result.obligations
            for hold in obligation.holds
            if hold.released_by is not None
        ]
        self.assertTrue(released_holds)
        self.assertTrue(
            all(hold.released_by.authority.hold_release for hold in released_holds)
        )

    def test_dependency_projection_exposes_difference_from_direct_inapplicability(self) -> None:
        text = COMPLETE.replace(
            "検索要求を処理して検索結果を返す",
            "障害下でだけ検索要求を処理して検索結果を返す",
        )
        report = audit_requirement_relations(
            text,
            morphology_provider=EmptyMorphologyProvider(),
            dependency_provider=ProjectingConditionDependencyProvider(),
        )
        by_id = {item.obligation_id: item for item in report.result.obligations}

        self.assertFalse(report.result.is_pass)
        self.assertEqual(
            {item.candidate.relation_kind for item in report.dependency_projections},
            {"triggered_by"},
        )
        self.assertEqual(by_id["func.triggered_by"].challenge.value, "conflict")
        self.assertTrue(by_id["func.triggered_by"].interpretations)
        self.assertIn(
            "candidate_relation_conflict",
            {hold.reason for hold in by_id["func.triggered_by"].open_holds},
        )

    def test_assurance_mode_promotes_parser_only_scope_to_effective_hold(self) -> None:
        report = audit_requirement_relations(
            COMPLETE,
            morphology_provider=EmptyMorphologyProvider(),
            dependency_provider=ParserOnlyQuotationProvider(),
            analysis_mode="assurance",
        )

        self.assertFalse(report.result.is_pass)
        self.assertIn(
            "dependency_quotation_scope_candidate",
            {item.reason_code for item in report.residual_signals},
        )
        self.assertTrue(any(item.open_holds for item in report.result.obligations))

    def test_explicit_llm_bundle_runs_in_assurance_and_scope_becomes_hold_material(self) -> None:
        cue_start = COMPLETE.index("p95")
        target_start = COMPLETE.index("検索応答時間 p95 500ms 以下")
        bundle = {
            "schema_version": "semantic-guard-llm-candidates/v0",
            "bundle_id": "bundle.engine.countercondition",
            "model_id": "fixture-model",
            "model_version": "1",
            "prompt_profile_id": "requirement-relations",
            "prompt_profile_version": "v0",
            "source_digest": {
                "algorithm": "sha256",
                "value": hashlib.sha256(COMPLETE.encode("utf-8")).hexdigest(),
            },
            "relations": [],
            "scopes": [
                {
                    "scope_kind": "countercondition",
                    "cue_span": {
                        "start": cue_start,
                        "end": cue_start + len("p95"),
                        "role": "countercondition",
                    },
                    "target_span": {
                        "start": target_start,
                        "end": target_start + len("検索応答時間 p95 500ms 以下"),
                        "role": "acceptance_criteria",
                    },
                    "confidence": 0.5,
                }
            ],
            "diagnostics": [],
        }

        report = audit_requirement_relations(
            COMPLETE,
            llm_provider=SubmittedLLMCandidateProvider(bundle),
            analysis_mode="assurance",
        )

        self.assertIn(
            "llm_candidate",
            {attempt.stage for attempt in report.analysis_attempts},
        )
        self.assertIn(
            "llm_countercondition_candidate",
            {item.reason_code for item in report.residual_signals},
        )
        self.assertTrue(any(item.open_holds for item in report.result.obligations))

    def test_dependency_semantic_candidates_are_materialized_before_llm_stage(self) -> None:
        text = COMPLETE.replace(
            "検索要求を処理して検索結果を返す",
            "障害下でだけ検索要求を処理して検索結果を返す",
        )
        llm = CapturingLLMProvider()

        report = audit_requirement_relations(
            text,
            morphology_provider=EmptyMorphologyProvider(),
            dependency_provider=ProjectingConditionDependencyProvider(),
            llm_provider=llm,
            analysis_mode="assurance",
        )

        self.assertIsNotNone(llm.request)
        assert llm.request is not None
        self.assertEqual(
            {item.relation_kind for item in llm.request.upstream_relations},
            {"triggered_by"},
        )
        self.assertIn("condition", {item.scope_kind for item in llm.request.upstream_scopes})
        self.assertEqual(
            tuple(item.candidate for item in report.dependency_projections),
            llm.request.upstream_relations,
        )

    def test_shadow_analysis_cannot_change_the_effective_decision(self) -> None:
        baseline = audit_requirement_relations(
            COMPLETE,
            analysis_mode="conditional",
        )
        shadow = audit_requirement_relations(
            COMPLETE,
            morphology_provider=HostileMorphologyProvider(),
            dependency_provider=HostileDependencyProvider(),
            analysis_mode="shadow_all",
        )

        self.assertTrue(baseline.result.is_pass)
        self.assertTrue(shadow.result.is_pass)
        self.assertEqual(shadow.residual_signals, baseline.residual_signals)
        self.assertTrue(shadow.shadow_signals)
        self.assertEqual(
            tuple(item.interpretations for item in shadow.result.obligations),
            tuple(item.interpretations for item in baseline.result.obligations),
        )
        for attempt in shadow.analysis_attempts:
            self.assertFalse(attempt.authority.support)
            self.assertFalse(attempt.authority.apply_hold)
            self.assertFalse(attempt.authority.release_hold)


if __name__ == "__main__":
    unittest.main()
