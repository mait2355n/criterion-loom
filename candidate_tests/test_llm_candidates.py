from __future__ import annotations

import hashlib
import unittest
from unittest.mock import patch

from jsonschema import ValidationError

from semantic_guard_vnext.llm_candidates import SubmittedLLMCandidateProvider
from semantic_guard_vnext.providers import AnalysisSpan, ProviderRequest, run_provider
from semantic_guard_vnext.schema_access import schema_path


TEXT = "対象を検証する"


def _bundle(text: str = TEXT) -> dict:
    return {
        "schema_version": "semantic-guard-vnext-llm-candidates/v0",
        "bundle_id": "bundle.fixture.1",
        "model_id": "fixture-model",
        "model_version": "2026-07-15",
        "prompt_profile_id": "requirement-relations",
        "prompt_profile_version": "v0",
        "source_digest": {
            "algorithm": "sha256",
            "value": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        },
        "relations": [
            {
                "relation_kind": "verifies",
                "from_span": {"start": 3, "end": 7, "role": "method"},
                "to_span": {"start": 0, "end": 2, "role": "criterion"},
                "confidence": 0.5,
                "interpretation_id": "interpretation.fixture.1",
                "rationale": "candidate-only fixture",
            }
        ],
        "scopes": [],
        "diagnostics": [],
    }


class SubmittedLLMCandidateTests(unittest.TestCase):
    def request(self, text: str = TEXT) -> ProviderRequest:
        return ProviderRequest(
            text=text,
            target_spans=(AnalysisSpan(0, len(text), "record"),),
            reason_codes=("unresolved",),
            requested_capabilities=(
                "interpretation_candidates",
                "countercondition_candidates",
            ),
        )

    def test_digest_bound_bundle_remains_candidate_only(self) -> None:
        attempt = run_provider(
            SubmittedLLMCandidateProvider(_bundle()),
            self.request(),
            stage="llm_candidate",
        )

        self.assertEqual(attempt.status, "ok")
        self.assertEqual(
            attempt.fulfilled_capabilities,
            ("interpretation_candidates", "countercondition_candidates"),
        )
        self.assertEqual(len(attempt.relations), 1)
        self.assertFalse(attempt.authority.support)
        self.assertTrue(attempt.authority.challenge_signal)
        self.assertFalse(attempt.authority.apply_hold)
        self.assertFalse(attempt.authority.release_hold)

    def test_bundle_for_other_source_fails_closed(self) -> None:
        attempt = run_provider(
            SubmittedLLMCandidateProvider(_bundle("別の原文")),
            self.request(),
            stage="llm_candidate",
        )

        self.assertEqual(attempt.status, "failed")
        self.assertTrue(
            any("llm_candidate_source_digest_mismatch" in item for item in attempt.diagnostics)
        )

    def test_closed_bundle_rejects_undeclared_fields(self) -> None:
        bundle = _bundle()
        bundle["unbounded_claim"] = True

        with self.assertRaises(ValidationError):
            SubmittedLLMCandidateProvider(bundle)

    def test_candidate_schema_is_resolved_through_schema_access(self) -> None:
        with patch(
            "semantic_guard_vnext.llm_candidates.schema_path",
            wraps=schema_path,
        ) as resolver:
            SubmittedLLMCandidateProvider(_bundle())

        resolver.assert_called_once_with("llm-candidate-input.schema.json")


if __name__ == "__main__":
    unittest.main()
