from __future__ import annotations

import unittest

from semantic_guard.lifting import evaluate_lifting_resolutions
from semantic_guard.providers import (
    AnalysisAttempt,
    AnalysisSpan,
    ProviderAuthority,
    RelationCandidate,
    ScopeCandidate,
)
from semantic_guard.records import parse_requirement_record
from semantic_guard.residual_risk import scan_residual_risks


TEXT = """Purpose: 検索APIが検索結果を p95 500ms以内で返す
User: 検索API
Scenario: 検索APIが検索要求を処理した場合は検索結果を返す
Expected result: 検索結果を p95 500ms以内で返す
Acceptance criteria: 検索応答時間 p95 500ms 以下
Verification method: 検索結果の検索応答時間を benchmark で測定する
Evidence: 検索結果の検索応答時間 benchmark report"""


def dependency_attempt(text: str, cue: AnalysisSpan, target: AnalysisSpan) -> AnalysisAttempt:
    return AnalysisAttempt(
        stage="dependency_parse",
        provider_id="test-dependency",
        provider_version="1",
        resource_version="fixture",
        status="ok",
        authority=ProviderAuthority(),
        requested_capabilities=("dependency", "scope"),
        fulfilled_capabilities=("dependency", "scope"),
        covered_spans=(AnalysisSpan(0, len(text), "document"),),
        relations=(
            RelationCandidate(
                relation_kind="dependency:advcl",
                from_span=cue,
                to_span=target,
            ),
        ),
        scopes=(ScopeCandidate("condition", cue, target),),
    )


class LiftingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.record = parse_requirement_record(TEXT)
        self.signal = next(
            item
            for item in scan_residual_risks(self.record)
            if item.reason_code == "conditional_or_exception_scope_present"
        )
        cue_start = TEXT.index("場合は")
        target_start = TEXT.index("返す", TEXT.index("Scenario:"))
        self.cue = AnalysisSpan(cue_start, cue_start + len("場合は"), "condition")
        self.target = AnalysisSpan(
            target_start, target_start + len("返す"), "predicate"
        )

    def test_single_source_aligned_attachment_can_be_lifted(self) -> None:
        resolutions = evaluate_lifting_resolutions(
            (self.signal,),
            self.record,
            (dependency_attempt(TEXT, self.cue, self.target),),
        )

        self.assertEqual(resolutions[0].status, "resolved")
        self.assertEqual(resolutions[0].rule_id, "lifting.condition-attachment/v0")

    def test_candidate_without_dependency_edge_cannot_release(self) -> None:
        attempt = dependency_attempt(TEXT, self.cue, self.target)
        attempt = AnalysisAttempt(
            stage=attempt.stage,
            provider_id=attempt.provider_id,
            provider_version=attempt.provider_version,
            resource_version=attempt.resource_version,
            status=attempt.status,
            authority=attempt.authority,
            requested_capabilities=attempt.requested_capabilities,
            fulfilled_capabilities=attempt.fulfilled_capabilities,
            covered_spans=attempt.covered_spans,
            scopes=attempt.scopes,
        )

        resolution = evaluate_lifting_resolutions(
            (self.signal,), self.record, (attempt,)
        )[0]

        self.assertEqual(resolution.status, "unresolved")

    def test_competing_attachments_cannot_release(self) -> None:
        first = dependency_attempt(TEXT, self.cue, self.target)
        other_start = TEXT.index("処理した")
        other = AnalysisSpan(other_start, other_start + len("処理した"), "predicate")
        second = dependency_attempt(TEXT, self.cue, other)

        resolution = evaluate_lifting_resolutions(
            (self.signal,), self.record, (first, second)
        )[0]

        self.assertEqual(resolution.status, "unresolved")
        self.assertIn("multiple_condition_attachments", resolution.reasons)

    def test_missing_scope_capability_cannot_release(self) -> None:
        attempt = dependency_attempt(TEXT, self.cue, self.target)
        attempt = AnalysisAttempt(
            stage=attempt.stage,
            provider_id=attempt.provider_id,
            provider_version=attempt.provider_version,
            resource_version=attempt.resource_version,
            status="partial",
            authority=attempt.authority,
            requested_capabilities=attempt.requested_capabilities,
            fulfilled_capabilities=("dependency",),
            covered_spans=attempt.covered_spans,
            relations=attempt.relations,
            scopes=attempt.scopes,
        )

        resolution = evaluate_lifting_resolutions(
            (self.signal,), self.record, (attempt,)
        )[0]

        self.assertEqual(resolution.status, "unresolved")


if __name__ == "__main__":
    unittest.main()
