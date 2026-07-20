from __future__ import annotations

import unittest

from semantic_guard.engine import audit_requirement_relations
from semantic_guard.providers import (
    AnalysisAttempt,
    ProviderAuthority,
    ProviderRequest,
    TokenCandidate,
)
from semantic_guard.routing import capabilities_for_stage


COMPLETE = """Purpose: 検索APIが検索結果を p95 500ms以内で返す
User: 検索API
Scenario: 検索APIが検索要求を処理して検索結果を返す
Expected result: 検索結果を p95 500ms以内で返す
Acceptance criteria: 検索応答時間 p95 500ms 以下
Verification method: 検索結果の検索応答時間を benchmark で測定する
Evidence: 検索結果の検索応答時間 benchmark report"""


class CapturingMorphologyProvider:
    provider_id = "capturing-morphology"
    provider_version = "1"
    resource_version = "fixture"
    stage = "morphology"

    def __init__(self) -> None:
        self.request: ProviderRequest | None = None

    def analyze(self, request: ProviderRequest) -> AnalysisAttempt:
        self.request = request
        start = next(
            span.start for span in request.target_spans if span.start < span.end
        )
        surface = request.text[start : start + 1]
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
                    surface=surface,
                    lemma=surface,
                    normalized=surface,
                    part_of_speech=("fixture",),
                    start=start,
                    end=start + 1,
                ),
            ),
        )


class CapturingDependencyProvider:
    provider_id = "capturing-dependency"
    provider_version = "1"
    resource_version = "fixture"
    stage = "dependency_parse"

    def __init__(self) -> None:
        self.request: ProviderRequest | None = None

    def analyze(self, request: ProviderRequest) -> AnalysisAttempt:
        self.request = request
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
            tokens=request.upstream_tokens,
        )


class FailingMorphologyProvider:
    provider_id = "unavailable-morphology"
    provider_version = "1"
    resource_version = "fixture"
    stage = "morphology"

    def analyze(self, request: ProviderRequest) -> AnalysisAttempt:
        raise RuntimeError("fixture unavailable")


class NeverCalledProvider:
    provider_id = "never-called"
    provider_version = "1"
    resource_version = "fixture"

    def __init__(self, stage: str) -> None:
        self.stage = stage

    def analyze(self, request: ProviderRequest) -> AnalysisAttempt:
        raise AssertionError("a skipped provider must not be called")


class RoutingContractTests(unittest.TestCase):
    def test_conditional_capabilities_follow_reason_and_unknowns_fail_safe(self) -> None:
        self.assertEqual(
            capabilities_for_stage(
                "dependency_parse",
                ("scenario_actor_role_not_assertion_capable",),
            ),
            ("dependency", "predicate_argument", "coordination"),
        )
        self.assertEqual(
            capabilities_for_stage(
                "dependency_parse",
                ("negation_scope_present",),
            ),
            ("dependency", "scope", "polarity_scope"),
        )
        self.assertIn(
            "coreference_candidate",
            capabilities_for_stage(
                "dependency_parse",
                ("future_reason_not_yet_governed",),
            ),
        )
        self.assertEqual(
            capabilities_for_stage(
                "llm_candidate",
                ("llm_countercondition_candidate",),
            ),
            ("countercondition_candidates",),
        )

    def test_route_identities_and_serialization_are_deterministic(self) -> None:
        text = COMPLETE.replace(
            "検索APIが検索結果を p95 500ms以内で返す",
            "請求書を破棄する",
            1,
        )

        first = audit_requirement_relations(text, analysis_mode="conditional")
        second = audit_requirement_relations(text, analysis_mode="conditional")

        self.assertEqual(
            [item.as_dict() for item in first.unresolved_obligations],
            [item.as_dict() for item in second.unresolved_obligations],
        )
        self.assertEqual(
            [item.as_dict() for item in first.stage_plans],
            [item.as_dict() for item in second.stage_plans],
        )
        self.assertEqual(
            len({item.stage_plan_id for item in first.stage_plans}),
            3,
        )
        self.assertTrue(
            all(item.direct_rule_version.startswith("v") for item in first.unresolved_obligations)
        )

    def test_residual_reasons_retain_their_requested_route_and_planned_stage(self) -> None:
        text = COMPLETE.replace(
            "検索要求を処理して検索結果を返す",
            "検索要求を処理した場合は検索結果を返す",
        ).replace(
            "検索応答時間 p95 500ms 以下",
            "検索応答時間 p95 500ms 以下とは定めない",
        )

        report = audit_requirement_relations(text, analysis_mode="conditional")
        routes = {
            pair
            for item in report.unresolved_obligations
            for pair in item.reason_routes
        }
        plans = {item.stage: item for item in report.stage_plans}

        self.assertIn(("negation_scope_present", "morphology"), routes)
        self.assertIn(
            ("conditional_or_exception_scope_present", "dependency_parse"),
            routes,
        )
        self.assertIn("negation_scope_present", plans["morphology"].reason_codes)
        self.assertIn(
            "conditional_or_exception_scope_present",
            plans["dependency_parse"].reason_codes,
        )
        serialized = plans["dependency_parse"].as_dict()["reason_routing"]
        self.assertTrue(
            any(
                item == {
                    "reason_code": "conditional_or_exception_scope_present",
                    "requested_route": "dependency_parse",
                    "planned_stage": "dependency_parse",
                }
                for item in serialized
            )
        )

    def test_direct_unknown_reasons_and_target_denominator_reach_requests(self) -> None:
        text = COMPLETE.replace(
            "検索APIが検索結果を p95 500ms以内で返す",
            "請求書を破棄する",
            1,
        )
        morphology = CapturingMorphologyProvider()
        dependency = CapturingDependencyProvider()

        report = audit_requirement_relations(
            text,
            analysis_mode="conditional",
            morphology_provider=morphology,
            dependency_provider=dependency,
        )
        plans = {item.stage: item for item in report.stage_plans}
        direct_reasons = {
            reason
            for item in report.unresolved_obligations
            for reason in item.direct_unknown_reasons
        }

        self.assertIn("no_assertion_capable_target_alignment", direct_reasons)
        self.assertIsNotNone(morphology.request)
        self.assertIsNotNone(dependency.request)
        assert morphology.request is not None
        assert dependency.request is not None
        self.assertIn(
            "no_assertion_capable_target_alignment",
            morphology.request.reason_codes,
        )
        self.assertIn(
            "no_assertion_capable_target_alignment",
            dependency.request.reason_codes,
        )
        self.assertEqual(plans["morphology"].target_spans, morphology.request.target_spans)
        self.assertEqual(
            plans["dependency_parse"].target_spans,
            dependency.request.target_spans,
        )
        denominator = plans["morphology"].as_dict()["target_denominator"]
        self.assertEqual(denominator["span_count"], len(morphology.request.target_spans))
        self.assertEqual(
            denominator["obligation_count"],
            len(plans["morphology"].target_obligation_ids),
        )
        self.assertEqual(
            set(plans["morphology"].target_obligation_ids),
            set(plans["morphology"].driver_obligation_ids),
        )

    def test_skipped_not_configured_and_attempt_failure_are_distinct(self) -> None:
        skipped = audit_requirement_relations(
            COMPLETE,
            analysis_mode="conditional",
        )
        self.assertEqual(
            {item.execution_state for item in skipped.stage_plans},
            {"skipped_not_needed"},
        )
        self.assertEqual(
            {item.availability for item in skipped.stage_plans},
            {"not_needed"},
        )

        not_configured = audit_requirement_relations(COMPLETE)
        self.assertEqual(
            {item.execution_state for item in not_configured.stage_plans},
            {"not_configured"},
        )
        self.assertEqual(
            {item.availability for item in not_configured.stage_plans},
            {"not_configured"},
        )

        text = COMPLETE.replace(
            "検索応答時間 p95 500ms 以下",
            "検索応答時間 p95 500ms 以下とは定めない",
        )
        unavailable = audit_requirement_relations(
            text,
            analysis_mode="conditional",
            morphology_provider=FailingMorphologyProvider(),
        )
        morphology_plan = next(
            item for item in unavailable.stage_plans if item.stage == "morphology"
        )
        self.assertEqual(morphology_plan.execution_state, "attempted_failed")
        self.assertEqual(morphology_plan.availability, "unavailable")
        self.assertEqual(morphology_plan.attempt_status, "failed")

    def test_required_llm_not_configured_is_an_explicit_attempt_and_receipt(self) -> None:
        report = audit_requirement_relations(COMPLETE)
        llm_attempts = [
            item for item in report.analysis_attempts if item.stage == "llm_candidate"
        ]
        self.assertEqual(len(llm_attempts), 1)
        self.assertEqual(llm_attempts[0].status, "not_configured")
        self.assertTrue(
            any(
                item.stage == "llm_candidate" and item.provider_id == "not-configured"
                for item in report.provider_execution_receipts
            )
        )
        llm_plan = next(
            item for item in report.stage_plans if item.stage == "llm_candidate"
        )
        self.assertEqual(llm_plan.execution_state, "not_configured")
        self.assertEqual(llm_plan.required_capabilities, llm_attempts[0].requested_capabilities)

    def test_route_observation_does_not_change_existing_disposition(self) -> None:
        baseline = audit_requirement_relations(
            COMPLETE,
            analysis_mode="conditional",
        )
        configured_but_skipped = audit_requirement_relations(
            COMPLETE,
            analysis_mode="conditional",
            morphology_provider=NeverCalledProvider("morphology"),
            dependency_provider=NeverCalledProvider("dependency_parse"),
            llm_provider=NeverCalledProvider("llm_candidate"),
        )

        self.assertEqual(configured_but_skipped.result, baseline.result)
        self.assertTrue(configured_but_skipped.result.is_pass)
        self.assertEqual(configured_but_skipped.analysis_attempts, ())
        self.assertTrue(
            all(
                item.route_decision == "skipped_not_needed"
                for item in configured_but_skipped.stage_plans
            )
        )


if __name__ == "__main__":
    unittest.main()
