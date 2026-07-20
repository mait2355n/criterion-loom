from __future__ import annotations

from dataclasses import replace
import unittest

from semantic_guard.dependency_projection import project_dependency_relations
from semantic_guard.direct_rules import DirectRelationAssessment
from semantic_guard.provider_receipts import (
    AnalyzerQualification,
    QualifiedAnalyzerRegistry,
    build_provider_execution_receipt,
    source_digest,
)
from semantic_guard.profiles import FUNCTIONAL_REQUIREMENT_PROFILE
from semantic_guard.providers import (
    AnalysisAttempt,
    AnalysisSpan,
    ProviderAuthority,
    ProviderRequest,
    RelationCandidate,
    ScopeCandidate,
)
from semantic_guard.records import ParsedRequirementRecord, parse_requirement_record
from semantic_guard.reassessment import (
    REQUIRED_CAPABILITIES,
    policy_scope,
    reassess_obligations,
    validate_reassessment_trace,
)
from semantic_guard.routing import build_unresolved_obligations


TEXT = """Purpose: 検索APIが検索結果を p95 500ms以内で返す
User: 検索API
Scenario: ここで、検索APIが検索要求を査定して検索結果を返す
Expected result: 検索結果を p95 500ms以内で返す
Acceptance criteria: 検索応答時間 p95 500ms 以下
Verification method: 検索結果の検索応答時間を benchmark で測定する
Evidence: 検索結果の検索応答時間 benchmark report"""


def _assessment(
    obligation_id: str,
    outcome: str = "unresolved",
    *,
    unknown_reasons: tuple[str, ...] | None = None,
) -> DirectRelationAssessment:
    eligible_reason = {
        "func.performs": ("scenario_actor_role_not_assertion_capable",),
        "func.acts_on": ("object_applicability_not_established",),
    }.get(obligation_id, ("direct_unresolved",))
    return DirectRelationAssessment(
        obligation_id=obligation_id,
        outcome=outcome,
        rule_id="direct.fixture/v0",
        from_field="fixture_from",
        to_field="fixture_to",
        evidence_spans=(),
        basis=("direct_fixture",) if outcome == "supported" else (),
        unknown_reasons=(
            unknown_reasons
            if unknown_reasons is not None
            else (eligible_reason if outcome == "unresolved" else ())
        ),
    )


def _span(record: ParsedRequirementRecord, value: str, *, after: str = "Scenario:") -> AnalysisSpan:
    start = record.source_text.index(value, record.source_text.index(after))
    return AnalysisSpan(start, start + len(value), "token")


def _attempt(
    record: ParsedRequirementRecord,
    *,
    provider_id: str = "qualified-fixture",
    provider_version: str = "1",
    resource_version: str = "model-1",
    status: str = "ok",
    fulfilled_capabilities: tuple[str, ...] = REQUIRED_CAPABILITIES,
    coverage: AnalysisSpan | None = None,
    actor: str = "検索API",
    obj: str = "検索要求",
    subject_dependency: str = "dependency:nsubj",
    object_dependency: str = "dependency:obj",
    extra_relations: tuple[RelationCandidate, ...] = (),
    scopes: tuple[ScopeCandidate, ...] = (),
) -> tuple[AnalysisAttempt, ProviderRequest]:
    scenario = record.one("scenario")
    assert scenario is not None
    actor_span = _span(record, actor)
    object_span = _span(record, obj)
    predicate_span = _span(record, "査定")
    target = coverage or AnalysisSpan(
        scenario.value_start, scenario.value_end, "scenario"
    )
    request = ProviderRequest(
        text=record.source_text,
        target_spans=(target,),
        reason_codes=("fixture",),
        requested_capabilities=REQUIRED_CAPABILITIES,
    )
    attempt = AnalysisAttempt(
        stage="dependency_parse",
        provider_id=provider_id,
        provider_version=provider_version,
        resource_version=resource_version,
        status=status,
        authority=ProviderAuthority(),
        requested_capabilities=request.requested_capabilities,
        fulfilled_capabilities=fulfilled_capabilities,
        covered_spans=(target,),
        relations=(
            RelationCandidate(subject_dependency, actor_span, predicate_span),
            RelationCandidate(object_dependency, object_span, predicate_span),
            *extra_relations,
        ),
        scopes=scopes,
    )
    return attempt, request


def _qualifications(
    *,
    provider_id: str = "qualified-fixture",
    provider_version: str = "1",
    resource_version: str = "model-1",
) -> QualifiedAnalyzerRegistry:
    return QualifiedAnalyzerRegistry(
        tuple(
            AnalyzerQualification(
                provider_id=provider_id,
                provider_version=provider_version,
                resource_version=resource_version,
                capabilities=REQUIRED_CAPABILITIES,
                policy_scope=policy_scope(obligation_id),
                qualification_basis="controlled fixture",
            )
            for obligation_id in ("func.performs", "func.acts_on")
        )
    )


def _run(
    record: ParsedRequirementRecord,
    assessments: tuple[DirectRelationAssessment, ...],
    attempts_and_requests: tuple[tuple[AnalysisAttempt, ProviderRequest], ...],
    *,
    registry: QualifiedAnalyzerRegistry | None = None,
    shadow: bool = False,
):
    attempts = tuple(item[0] for item in attempts_and_requests)
    receipts = tuple(
        build_provider_execution_receipt(request, attempt)
        for attempt, request in attempts_and_requests
    )
    projections = project_dependency_relations(record, attempts, receipts)
    source_id = source_digest(record.source_text)
    obligation_ids = {item.obligation_id for item in assessments}
    profile = replace(
        FUNCTIONAL_REQUIREMENT_PROFILE,
        obligations=tuple(
            item
            for item in FUNCTIONAL_REQUIREMENT_PROFILE.obligations
            if item.obligation_id in obligation_ids
        ),
    )
    initial_unresolved = build_unresolved_obligations(
        source_id=source_id,
        profile=profile,
        direct_assessments=assessments,
        residual_signals=(),
    )
    return reassess_obligations(
        source_id=source_id,
        profile_id=FUNCTIONAL_REQUIREMENT_PROFILE.profile_id,
        profile_version=FUNCTIONAL_REQUIREMENT_PROFILE.version,
        record=record,
        direct_assessments=assessments,
        initial_unresolved_obligations=initial_unresolved,
        projections=projections,
        attempts=attempts,
        receipts=receipts,
        registry=registry or QualifiedAnalyzerRegistry(),
        shadow=shadow,
    )


class ReassessmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.record = parse_requirement_record(TEXT)

    def test_qualified_exact_subject_and_object_triad_supports_only_target_relations(self) -> None:
        results = _run(
            self.record,
            (_assessment("func.performs"), _assessment("func.acts_on")),
            (_attempt(self.record),),
            registry=_qualifications(),
        )

        self.assertEqual([item.decision for item in results], ["supported", "supported"])
        self.assertTrue(all(item.effective_outcome == "supported" for item in results))
        self.assertTrue(all(item.receipt_ids for item in results))
        self.assertTrue(all(item.qualification_ids for item in results))

    def test_direct_supported_outcome_is_preserved(self) -> None:
        result = _run(
            self.record,
            (_assessment("func.performs", "supported"),),
            (_attempt(self.record),),
            registry=_qualifications(),
        )[0]

        self.assertEqual(result.decision, "preserved")
        self.assertEqual(result.effective_outcome, "supported")

    def test_empty_or_version_mismatched_qualification_is_fail_closed(self) -> None:
        unqualified = _run(
            self.record,
            (_assessment("func.performs"),),
            (_attempt(self.record),),
        )[0]
        mismatched = _run(
            self.record,
            (_assessment("func.performs"),),
            (_attempt(self.record),),
            registry=_qualifications(provider_version="2"),
        )[0]

        self.assertEqual(unqualified.decision, "abstain")
        self.assertEqual(mismatched.decision, "abstain")
        self.assertIn("analyzer_not_qualified_for_scope", unqualified.reasons)

    def test_partial_coverage_or_missing_capability_cannot_support(self) -> None:
        scenario = self.record.one("scenario")
        assert scenario is not None
        partial_span = AnalysisSpan(
            scenario.value_start,
            scenario.value_start + len("ここで"),
            "scenario-fragment",
        )
        partial = _run(
            self.record,
            (_assessment("func.performs"),),
            (_attempt(self.record, coverage=partial_span),),
            registry=_qualifications(),
        )[0]
        missing = _run(
            self.record,
            (_assessment("func.performs"),),
            (_attempt(self.record, fulfilled_capabilities=("dependency",)),),
            registry=_qualifications(),
        )[0]

        self.assertEqual(partial.decision, "abstain")
        self.assertIn("scenario_coverage_incomplete", partial.reasons)
        self.assertEqual(missing.decision, "abstain")
        self.assertIn("required_capability_missing", missing.reasons)

    def test_open_record_or_unsolicited_scenario_coverage_cannot_support(self) -> None:
        attempt, request = _attempt(self.record)
        scenario = self.record.one("scenario")
        assert scenario is not None
        unrelated_target = AnalysisSpan(0, len("Purpose"), "unrelated")
        unsolicited_request = replace(request, target_spans=(unrelated_target,))
        unsolicited_attempt = replace(
            attempt,
            requested_capabilities=unsolicited_request.requested_capabilities,
            covered_spans=(
                AnalysisSpan(scenario.value_start, scenario.value_end, "scenario"),
            ),
        )
        unsolicited = _run(
            self.record,
            (_assessment("func.performs"),),
            ((unsolicited_attempt, unsolicited_request),),
            registry=_qualifications(),
        )[0]
        open_record = replace(self.record, record_mode="open_text")
        open_result = _run(
            open_record,
            (_assessment("func.performs"),),
            (_attempt(open_record),),
            registry=_qualifications(),
        )[0]

        self.assertEqual(unsolicited.decision, "abstain")
        self.assertIn("scenario_coverage_incomplete", unsolicited.reasons)
        self.assertEqual(open_result.decision, "abstain")
        self.assertIn("record_boundary_not_closed_single", open_result.reasons)

    def test_actor_as_object_is_challenged_not_refuted_or_supported(self) -> None:
        text = TEXT.replace(
            "ここで、検索APIが検索要求を査定して検索結果を返す",
            "システムが検索APIを査定して検索結果を返す",
        )
        record = parse_requirement_record(text)
        attempt, request = _attempt(record, actor="システム", obj="検索API")
        result = _run(
            record,
            (_assessment("func.performs"),),
            ((attempt, request),),
            registry=_qualifications(),
        )[0]

        self.assertEqual(result.decision, "challenged_by_policy")
        self.assertEqual(result.effective_outcome, "unresolved")
        self.assertIn("declared_user_differs_from_plain_nsubj", result.reasons)

    def test_passive_negation_or_coordination_barrier_abstains(self) -> None:
        attempt, request = _attempt(self.record)
        actor = attempt.relations[0].from_span
        predicate = attempt.relations[0].to_span
        passive = replace(
            attempt,
            relations=(
                *attempt.relations,
                RelationCandidate("dependency:nsubj:pass", actor, predicate),
                RelationCandidate("dependency:conj", predicate, predicate),
            ),
            scopes=(ScopeCandidate("negation", predicate, predicate),),
        )
        result = _run(
            self.record,
            (_assessment("func.performs"),),
            ((passive, request),),
            registry=_qualifications(),
        )[0]

        self.assertEqual(result.decision, "abstain")
        self.assertTrue(any("unresolved_" in item for item in result.reasons))

    def test_direct_voice_reported_and_nominal_reasons_are_never_repromoted(self) -> None:
        for reason in (
            "scenario_actor_voice_not_agentive",
            "scenario_actor_assertion_reported_or_quoted",
            "scenario_actor_active_predicate_not_established",
        ):
            with self.subTest(reason=reason):
                result = _run(
                    self.record,
                    (
                        _assessment(
                            "func.performs",
                            unknown_reasons=(reason,),
                        ),
                    ),
                    (_attempt(self.record),),
                    registry=_qualifications(),
                )[0]

                self.assertEqual(result.decision, "abstain")
                self.assertEqual(result.effective_outcome, "unresolved")
                self.assertTrue(
                    result.reasons[0].startswith(
                        "direct_reason_not_reassessment_eligible:"
                    )
                )

    def test_source_voice_gate_blocks_plain_nsubj_even_without_token_voice(self) -> None:
        text = TEXT.replace("査定して", "査定させられて")
        record = parse_requirement_record(text)
        result = _run(
            record,
            (_assessment("func.performs"),),
            (_attempt(record),),
            registry=_qualifications(),
        )[0]

        self.assertEqual(result.decision, "abstain")
        self.assertIn("source_voice_or_causative_not_excluded", result.reasons)

    def test_actor_identity_does_not_delete_internal_space_or_fold_compatibility(self) -> None:
        for declared_user in ("検索 API", "検索ＡＰＩ"):
            with self.subTest(declared_user=declared_user):
                text = TEXT.replace("User: 検索API", f"User: {declared_user}")
                record = parse_requirement_record(text)
                result = _run(
                    record,
                    (_assessment("func.performs"),),
                    (_attempt(record),),
                    registry=_qualifications(),
                )[0]

                self.assertEqual(result.decision, "challenged_by_policy")
                self.assertIn(
                    "declared_user_differs_from_plain_nsubj",
                    result.reasons,
                )

    def test_trace_binding_rejects_other_source_prior_or_unresolved_replay(self) -> None:
        assessment = _assessment("func.performs")
        attempt, request = _attempt(self.record)
        receipt = build_provider_execution_receipt(request, attempt)
        projections = project_dependency_relations(
            self.record,
            (attempt,),
            (receipt,),
        )
        source_id = source_digest(self.record.source_text)
        profile = replace(
            FUNCTIONAL_REQUIREMENT_PROFILE,
            obligations=tuple(
                item
                for item in FUNCTIONAL_REQUIREMENT_PROFILE.obligations
                if item.obligation_id == "func.performs"
            ),
        )
        initial = build_unresolved_obligations(
            source_id=source_id,
            profile=profile,
            direct_assessments=(assessment,),
            residual_signals=(),
        )

        def invoke(
            *,
            supplied_source: str = source_id,
            supplied_assessment: DirectRelationAssessment = assessment,
            supplied_initial=initial,
        ):
            return reassess_obligations(
                source_id=supplied_source,
                profile_id=FUNCTIONAL_REQUIREMENT_PROFILE.profile_id,
                profile_version=FUNCTIONAL_REQUIREMENT_PROFILE.version,
                record=self.record,
                direct_assessments=(supplied_assessment,),
                initial_unresolved_obligations=supplied_initial,
                projections=projections,
                attempts=(attempt,),
                receipts=(receipt,),
                registry=_qualifications(),
            )

        with self.assertRaisesRegex(ValueError, "source_id"):
            invoke(supplied_source=source_digest("other source"))
        with self.assertRaisesRegex(ValueError, "prior assessment"):
            invoke(
                supplied_assessment=_assessment(
                    "func.performs",
                    unknown_reasons=("scenario_actor_voice_not_agentive",),
                )
            )
        with self.assertRaisesRegex(ValueError, "prior assessment"):
            invoke(
                supplied_initial=(
                    replace(initial[0], profile_version="other-profile-version"),
                )
            )
        valid = invoke()[0]
        validate_reassessment_trace(
            valid,
            source_id=source_id,
            profile_id=FUNCTIONAL_REQUIREMENT_PROFILE.profile_id,
            profile_version=FUNCTIONAL_REQUIREMENT_PROFILE.version,
            prior_assessment=assessment,
            initial_unresolved=initial[0],
        )
        scenario = self.record.one("scenario")
        assert scenario is not None
        replayed_unresolved = replace(
            initial[0],
            target_spans=(
                AnalysisSpan(
                    scenario.value_start,
                    scenario.value_start + 1,
                    "replayed-fragment",
                ),
            ),
        )
        with self.assertRaisesRegex(ValueError, "trace binding mismatch"):
            validate_reassessment_trace(
                valid,
                source_id=source_id,
                profile_id=FUNCTIONAL_REQUIREMENT_PROFILE.profile_id,
                profile_version=FUNCTIONAL_REQUIREMENT_PROFILE.version,
                prior_assessment=assessment,
                initial_unresolved=replayed_unresolved,
            )

    def test_multiple_subject_object_or_provider_is_challenged(self) -> None:
        attempt, request = _attempt(self.record)
        scenario = self.record.one("scenario")
        assert scenario is not None
        other_span = AnalysisSpan(
            scenario.value_start,
            scenario.value_start + len("ここで"),
            "token",
        )
        predicate = attempt.relations[0].to_span
        multiple_subject = replace(
            attempt,
            relations=(
                *attempt.relations,
                RelationCandidate("dependency:nsubj", other_span, predicate),
            ),
        )
        subject_result = _run(
            self.record,
            (_assessment("func.performs"),),
            ((multiple_subject, request),),
            registry=_qualifications(),
        )[0]
        second_attempt, second_request = _attempt(
            self.record,
            provider_id="qualified-fixture-2",
        )
        provider_result = _run(
            self.record,
            (_assessment("func.performs"),),
            ((attempt, request), (second_attempt, second_request)),
            registry=_qualifications(),
        )[0]

        self.assertEqual(subject_result.decision, "challenged_by_policy")
        self.assertEqual(provider_result.decision, "challenged_by_policy")

    def test_iobj_or_object_without_subject_never_supports_acts_on(self) -> None:
        iobj_result = _run(
            self.record,
            (_assessment("func.acts_on"),),
            (_attempt(self.record, object_dependency="dependency:iobj"),),
            registry=_qualifications(),
        )[0]
        attempt, request = _attempt(self.record)
        object_only = replace(attempt, relations=(attempt.relations[1],))
        object_only_result = _run(
            self.record,
            (_assessment("func.acts_on"),),
            ((object_only, request),),
            registry=_qualifications(),
        )[0]

        self.assertNotEqual(iobj_result.decision, "supported")
        self.assertNotEqual(object_only_result.decision, "supported")

    def test_llm_only_material_and_shadow_mode_never_promote(self) -> None:
        dependency, request = _attempt(self.record)
        llm = replace(
            dependency,
            stage="llm_candidate",
            provider_id="submitted-llm:test",
            relations=(
                RelationCandidate(
                    "performs",
                    dependency.relations[0].from_span,
                    dependency.relations[0].to_span,
                ),
            ),
        )
        llm_request = replace(request, requested_capabilities=("interpretation_candidates",))
        llm = replace(
            llm,
            requested_capabilities=llm_request.requested_capabilities,
            fulfilled_capabilities=llm_request.requested_capabilities,
        )
        llm_only = _run(
            self.record,
            (_assessment("func.performs"),),
            ((llm, llm_request),),
            registry=_qualifications(),
        )[0]
        shadow = _run(
            self.record,
            (_assessment("func.performs"),),
            ((dependency, request),),
            registry=_qualifications(),
            shadow=True,
        )[0]

        self.assertEqual(llm_only.decision, "abstain")
        self.assertEqual(shadow.decision, "shadow_observation")
        self.assertEqual(shadow.effective_outcome, "unresolved")


if __name__ == "__main__":
    unittest.main()
