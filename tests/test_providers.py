from __future__ import annotations

import unittest

from semantic_guard.japanese_morphology import SudachiMorphologyProvider
from semantic_guard.providers import (
    AnalysisAttempt,
    AnalysisSpan,
    ProviderAuthority,
    ProviderRequest,
    RelationCandidate,
    run_provider,
)


class HostileProvider:
    stage = "dependency_parse"
    provider_id = "hostile"
    provider_version = "1"
    resource_version = "model-1"

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
            covered_spans=(AnalysisSpan(0, len(request.text)),),
            relations=(
                RelationCandidate(
                    relation_kind="verifies",
                    from_span=AnalysisSpan(0, 3),
                    to_span=AnalysisSpan(4, 7),
                    confidence=1.0,
                ),
            ),
        )


class InvalidSpanProvider(HostileProvider):
    def analyze(self, request: ProviderRequest) -> AnalysisAttempt:
        attempt = super().analyze(request)
        return AnalysisAttempt(
            stage=attempt.stage,
            provider_id=attempt.provider_id,
            provider_version=attempt.provider_version,
            resource_version=attempt.resource_version,
            status=attempt.status,
            authority=attempt.authority,
            requested_capabilities=attempt.requested_capabilities,
            fulfilled_capabilities=attempt.fulfilled_capabilities,
            covered_spans=(AnalysisSpan(0, len(request.text) + 10),),
            relations=(
                RelationCandidate(
                    relation_kind="verifies",
                    from_span=AnalysisSpan(0, 2),
                    to_span=AnalysisSpan(5, len(request.text) + 1),
                ),
            ),
        )


class NoneProvider(HostileProvider):
    def analyze(self, request: ProviderRequest):
        return None


class MismatchedAttemptProvider(HostileProvider):
    def analyze(self, request: ProviderRequest) -> AnalysisAttempt:
        attempt = super().analyze(request)
        return AnalysisAttempt(
            stage="llm_candidate",
            provider_id="spoofed-provider",
            provider_version="spoofed-version",
            resource_version="spoofed-resource",
            status="ok",
            authority=attempt.authority,
            requested_capabilities=attempt.requested_capabilities,
            fulfilled_capabilities=attempt.fulfilled_capabilities,
            covered_spans=attempt.covered_spans,
            relations=attempt.relations,
        )


class MorphologyRelationProvider(HostileProvider):
    stage = "morphology"

    def analyze(self, request: ProviderRequest) -> AnalysisAttempt:
        return AnalysisAttempt(
            stage="morphology",
            provider_id=self.provider_id,
            provider_version=self.provider_version,
            resource_version=self.resource_version,
            status="ok",
            authority=ProviderAuthority(challenge_signal=True),
            requested_capabilities=request.requested_capabilities,
            fulfilled_capabilities=request.requested_capabilities,
            covered_spans=(AnalysisSpan(0, len(request.text)),),
            relations=(
                RelationCandidate(
                    relation_kind="produces",
                    from_span=AnalysisSpan(0, 2),
                    to_span=AnalysisSpan(3, 5),
                ),
            ),
        )


class EmptyMorphologyOutputProvider:
    stage = "morphology"
    provider_id = "empty-morphology-output"
    provider_version = "1"
    resource_version = "fixture"

    def analyze(self, request: ProviderRequest) -> AnalysisAttempt:
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
        )


class TinyCoverageProvider(HostileProvider):
    def analyze(self, request: ProviderRequest) -> AnalysisAttempt:
        attempt = super().analyze(request)
        return AnalysisAttempt(
            stage=attempt.stage,
            provider_id=attempt.provider_id,
            provider_version=attempt.provider_version,
            resource_version=attempt.resource_version,
            status="ok",
            authority=attempt.authority,
            requested_capabilities=request.requested_capabilities,
            fulfilled_capabilities=request.requested_capabilities,
            covered_spans=(AnalysisSpan(0, 1, "tiny"),),
            relations=attempt.relations,
        )


class MissingCapabilityProvider(HostileProvider):
    def analyze(self, request: ProviderRequest) -> AnalysisAttempt:
        attempt = super().analyze(request)
        return AnalysisAttempt(
            stage=attempt.stage,
            provider_id=attempt.provider_id,
            provider_version=attempt.provider_version,
            resource_version=attempt.resource_version,
            status="ok",
            authority=attempt.authority,
            requested_capabilities=request.requested_capabilities,
            fulfilled_capabilities=(),
            covered_spans=attempt.covered_spans,
            relations=attempt.relations,
        )


class UnrequestedCapabilityProvider(HostileProvider):
    def analyze(self, request: ProviderRequest) -> AnalysisAttempt:
        attempt = super().analyze(request)
        return AnalysisAttempt(
            stage=attempt.stage,
            provider_id=attempt.provider_id,
            provider_version=attempt.provider_version,
            resource_version=attempt.resource_version,
            status="ok",
            authority=attempt.authority,
            requested_capabilities=request.requested_capabilities,
            fulfilled_capabilities=("not-requested",),
            covered_spans=attempt.covered_spans,
            relations=attempt.relations,
        )


class ProviderBoundaryTests(unittest.TestCase):
    def request(self) -> ProviderRequest:
        return ProviderRequest(
            text="abcdefghi",
            target_spans=(AnalysisSpan(0, 9, "document"),),
            reason_codes=("attachment_unknown",),
            requested_capabilities=("dependency",),
        )

    def test_provider_cannot_self_grant_support_or_hold_release(self) -> None:
        attempt = run_provider(HostileProvider(), self.request(), stage="dependency_parse")

        self.assertFalse(attempt.authority.support)
        self.assertTrue(attempt.authority.challenge_signal)
        self.assertFalse(attempt.authority.apply_hold)
        self.assertFalse(attempt.authority.release_hold)

    def test_morphology_declares_only_capabilities_it_directly_provides(self) -> None:
        self.assertEqual(
            SudachiMorphologyProvider.capabilities,
            frozenset({"tokenization", "lemma", "part_of_speech"}),
        )
        self.assertNotIn("scope_cues", SudachiMorphologyProvider.capabilities)

    def test_invalid_source_spans_are_dropped_and_reported(self) -> None:
        attempt = run_provider(InvalidSpanProvider(), self.request(), stage="dependency_parse")

        self.assertEqual(attempt.status, "failed")
        self.assertEqual(attempt.covered_spans, ())
        self.assertEqual(attempt.relations, ())
        self.assertIn("invalid_covered_span_dropped", attempt.diagnostics)
        self.assertIn("invalid_relation_span_dropped", attempt.diagnostics)

    def test_not_configured_is_explicit(self) -> None:
        attempt = run_provider(None, self.request(), stage="morphology")

        self.assertEqual(attempt.status, "not_configured")
        self.assertIn("provider_not_configured", attempt.diagnostics)

    def test_non_attempt_return_is_a_failed_observation_not_an_exception(self) -> None:
        attempt = run_provider(NoneProvider(), self.request(), stage="dependency_parse")

        self.assertEqual(attempt.status, "failed")
        self.assertIn(
            "provider_contract_invalid:return_type:NoneType",
            attempt.diagnostics,
        )

    def test_attempt_stage_and_identity_spoofing_invalidates_candidates(self) -> None:
        attempt = run_provider(
            MismatchedAttemptProvider(), self.request(), stage="dependency_parse"
        )

        self.assertEqual(attempt.status, "failed")
        self.assertEqual(attempt.provider_id, "hostile")
        self.assertIn("attempt_stage_mismatch:llm_candidate", attempt.diagnostics)
        self.assertTrue(
            any(item.startswith("provider_id_mismatch:") for item in attempt.diagnostics)
        )

    def test_morphology_cannot_emit_semantic_relation_candidates(self) -> None:
        attempt = run_provider(
            MorphologyRelationProvider(), self.request(), stage="morphology"
        )

        self.assertEqual(attempt.status, "failed")
        self.assertEqual(attempt.relations, ())
        self.assertFalse(attempt.authority.challenge_signal)
        self.assertIn(
            "stage_output_not_permitted:morphology:relations",
            attempt.diagnostics,
        )

    def test_empty_successful_morphology_output_is_invalid_coverage(self) -> None:
        attempt = run_provider(
            EmptyMorphologyOutputProvider(),
            self.request(),
            stage="morphology",
        )

        self.assertEqual(attempt.status, "failed")
        self.assertIn(
            "provider_coverage_invalid:morphology:no_tokens",
            attempt.diagnostics,
        )

    def test_one_character_coverage_cannot_claim_complete_target_union(self) -> None:
        attempt = run_provider(
            TinyCoverageProvider(),
            self.request(),
            stage="dependency_parse",
        )

        self.assertEqual(attempt.status, "partial")
        self.assertEqual(attempt.fulfilled_capabilities, ())
        self.assertEqual(attempt.missing_capabilities, ("dependency",))
        self.assertIn("provider_target_coverage_partial:1:9", attempt.diagnostics)
        self.assertFalse(attempt.authority.support)
        self.assertFalse(attempt.authority.release_hold)

    def test_missing_requested_capability_downgrades_ok_to_partial(self) -> None:
        attempt = run_provider(
            MissingCapabilityProvider(),
            self.request(),
            stage="dependency_parse",
        )

        self.assertEqual(attempt.status, "partial")
        self.assertEqual(attempt.requested_capabilities, ("dependency",))
        self.assertEqual(attempt.fulfilled_capabilities, ())
        self.assertEqual(attempt.missing_capabilities, ("dependency",))
        self.assertIn(
            "provider_capabilities_unfulfilled:dependency",
            attempt.diagnostics,
        )

    def test_fulfilling_an_unrequested_capability_is_contract_failure(self) -> None:
        attempt = run_provider(
            UnrequestedCapabilityProvider(),
            self.request(),
            stage="dependency_parse",
        )

        self.assertEqual(attempt.status, "failed")
        self.assertEqual(attempt.fulfilled_capabilities, ())
        self.assertIn(
            "provider_fulfilled_unrequested_capability",
            attempt.diagnostics,
        )


if __name__ == "__main__":
    unittest.main()
