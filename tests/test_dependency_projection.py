from __future__ import annotations

import unittest

from semantic_guard.dependency_projection import project_dependency_relations
from semantic_guard.provider_receipts import build_provider_execution_receipt
from semantic_guard.providers import (
    AnalysisAttempt,
    AnalysisSpan,
    ProviderAuthority,
    ProviderRequest,
    RelationCandidate,
    ScopeCandidate,
)
from semantic_guard.records import parse_requirement_record


TEXT = """Purpose: 検索APIが検索結果を p95 500ms以内で返す
User: 検索API
Scenario: 検索APIが検索要求を処理した場合、検索結果を返す
Expected result: 検索結果を p95 500ms以内で返す
Acceptance criteria: 検索応答時間 p95 500ms 以下
Verification method: 検索結果の検索応答時間を benchmark で測定する
Evidence: 検索結果の検索応答時間 benchmark report"""


def _span(value: str, *, after: str = "") -> AnalysisSpan:
    start = TEXT.index(value, TEXT.index(after) if after else 0)
    return AnalysisSpan(start, start + len(value), "token")


def _attempt(
    status: str = "ok",
    *,
    fulfilled_capabilities: tuple[str, ...] | None = None,
) -> AnalysisAttempt:
    actor = _span("検索API", after="Scenario:")
    obj = _span("検索要求")
    predicate = _span("処理")
    cue = _span("場合")
    return AnalysisAttempt(
        stage="dependency_parse",
        provider_id="fixture-ud",
        provider_version="1",
        resource_version="fixture-1",
        status=status,
        authority=ProviderAuthority(),
        requested_capabilities=("dependency", "scope"),
        fulfilled_capabilities=(
            fulfilled_capabilities
            if fulfilled_capabilities is not None
            else (("dependency", "scope") if status in {"ok", "partial"} else ())
        ),
        covered_spans=(
            AnalysisSpan(
                TEXT.index("検索APIが", TEXT.index("Scenario:")),
                TEXT.index("\nExpected result:"),
                "scenario",
            ),
        ),
        relations=(
            RelationCandidate("dependency:nsubj", actor, predicate),
            RelationCandidate("dependency:obj", obj, predicate),
            RelationCandidate("dependency:advcl", cue, predicate),
        ),
        scopes=(ScopeCandidate("condition", cue, predicate),),
    )


def _receipt(attempt: AnalysisAttempt):
    return build_provider_execution_receipt(
        ProviderRequest(
            text=TEXT,
            target_spans=attempt.covered_spans,
            reason_codes=("fixture",),
            requested_capabilities=attempt.requested_capabilities,
        ),
        attempt,
    )


class DependencyProjectionTests(unittest.TestCase):
    def test_source_aligned_ud_edges_become_versioned_semantic_candidates(self) -> None:
        projections = project_dependency_relations(
            parse_requirement_record(TEXT),
            (attempt := _attempt(),),
            (_receipt(attempt),),
        )

        self.assertEqual(
            {item.candidate.relation_kind for item in projections},
            {"performs", "acts_on", "triggered_by"},
        )
        self.assertTrue(all(item.rule_id.endswith("/v0") for item in projections))
        self.assertTrue(
            all("candidate_only" in item.candidate.rationale for item in projections)
        )
        self.assertTrue(all(item.receipt_id.startswith("receipt.") for item in projections))
        acts_on = next(
            item.candidate
            for item in projections
            if item.candidate.relation_kind == "acts_on"
        )
        self.assertEqual(TEXT[acts_on.from_span.start : acts_on.from_span.end], "処理")
        self.assertEqual(TEXT[acts_on.to_span.start : acts_on.to_span.end], "検索要求")

    def test_failed_dependency_attempt_cannot_be_projected(self) -> None:
        projections = project_dependency_relations(
            parse_requirement_record(TEXT),
            (attempt := _attempt("failed"),),
            (_receipt(attempt),),
        )

        self.assertEqual(projections, ())

    def test_partial_attempt_preserves_only_its_fulfilled_capability_outputs(self) -> None:
        projections = project_dependency_relations(
            parse_requirement_record(TEXT),
            (
                attempt := _attempt(
                    "partial", fulfilled_capabilities=("dependency",)
                ),
            ),
            (_receipt(attempt),),
        )

        self.assertEqual(
            {item.candidate.relation_kind for item in projections},
            {"performs", "acts_on"},
        )
        self.assertNotIn(
            "triggered_by",
            {item.candidate.relation_kind for item in projections},
        )

    def test_passive_subject_is_not_projected_as_performs(self) -> None:
        attempt = _attempt()
        passive = RelationCandidate(
            "dependency:nsubj:pass",
            attempt.relations[0].from_span,
            attempt.relations[0].to_span,
        )
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
            relations=(passive,),
        )

        projections = project_dependency_relations(
            parse_requirement_record(TEXT),
            (attempt,),
            (_receipt(attempt),),
        )

        self.assertNotIn(
            "performs",
            {item.candidate.relation_kind for item in projections},
        )

    def test_projection_without_engine_receipt_is_rejected(self) -> None:
        self.assertEqual(
            project_dependency_relations(parse_requirement_record(TEXT), (_attempt(),)),
            (),
        )


if __name__ == "__main__":
    unittest.main()
