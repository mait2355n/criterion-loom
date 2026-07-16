from __future__ import annotations

import unittest

from semantic_guard import (
    AuditExecution,
    Challenge,
    Coverage,
    EvidenceRef,
    EvidenceRole,
    Finality,
    GuardCoverage,
    Hold,
    ObligationResult,
    Outcome,
    StageAuthority,
    AuditResult,
    Workflow,
    aggregate_audit_result,
)


DIRECT = StageAuthority.assertion_capable("direct-rule/v1")
CANDIDATE = StageAuthority.candidate_only("dependency-provider/v1")
POLICY = StageAuthority.policy_authority("residual-risk-policy/v1")
RELEASE_POLICY = StageAuthority.policy_authority(
    "hold-release-policy/v1",
    hold_apply=False,
    hold_release=True,
)


def complete_coverage() -> GuardCoverage:
    return GuardCoverage(
        status=Coverage.COMPLETE,
        required_checks=("record_boundary", "scope"),
        completed_checks=("record_boundary", "scope"),
    )


def support_evidence(evidence_id: str = "evidence.direct") -> EvidenceRef:
    return EvidenceRef(
        evidence_id=evidence_id,
        role=EvidenceRole.SUPPORT,
        authority=DIRECT,
        source_ref="requirement.txt",
    )


def candidate_evidence(evidence_id: str = "evidence.candidate") -> EvidenceRef:
    return EvidenceRef(
        evidence_id=evidence_id,
        role=EvidenceRole.CHALLENGE,
        authority=CANDIDATE,
        source_ref="requirement.txt",
    )


def policy_evidence(evidence_id: str = "evidence.policy") -> EvidenceRef:
    return EvidenceRef(
        evidence_id=evidence_id,
        role=EvidenceRole.CHALLENGE,
        authority=POLICY,
        source_ref="requirement.txt",
    )


def release_evidence(evidence_id: str = "evidence.release") -> EvidenceRef:
    return EvidenceRef(
        evidence_id=evidence_id,
        role=EvidenceRole.SIGNAL,
        authority=RELEASE_POLICY,
        source_ref="requirement.txt",
    )


def satisfied_obligation(obligation_id: str = "func.verifies") -> ObligationResult:
    return ObligationResult(
        obligation_id=obligation_id,
        outcome=Outcome.SATISFIED,
        finality=Finality.TERMINAL,
        challenge=Challenge.NONE,
        coverage=complete_coverage(),
        provenance=(support_evidence(f"evidence.{obligation_id}"),),
    )


def complete_execution(**overrides: object) -> AuditExecution:
    values: dict[str, object] = {
        "execution_id": "execution.test",
        "coverage": complete_coverage(),
    }
    values.update(overrides)
    return AuditExecution(**values)  # type: ignore[arg-type]


class ModelAuthorityTests(unittest.TestCase):
    def test_candidate_evidence_cannot_terminally_satisfy_obligation(self) -> None:
        proposed_support = EvidenceRef(
            evidence_id="candidate.as-support",
            role=EvidenceRole.SUPPORT,
            authority=CANDIDATE,
            source_ref="requirement.txt",
        )

        with self.assertRaisesRegex(ValueError, "assertion-capable"):
            ObligationResult(
                obligation_id="func.verifies",
                outcome=Outcome.SATISFIED,
                finality=Finality.TERMINAL,
                challenge=Challenge.NONE,
                coverage=complete_coverage(),
                provenance=(proposed_support,),
            )

    def test_candidate_evidence_cannot_release_hold(self) -> None:
        applied = policy_evidence("policy.applied")
        released = candidate_evidence("candidate.released")

        with self.assertRaisesRegex(ValueError, "hold_release"):
            Hold(
                hold_id="hold.scope",
                scope=("func.verifies",),
                reason="attachment is ambiguous",
                applied_by=applied,
                release_conditions=("assertion-capable re-evaluation",),
                released_by=released,
            )

    def test_candidate_evidence_cannot_apply_hold(self) -> None:
        with self.assertRaisesRegex(ValueError, "hold_apply"):
            Hold(
                hold_id="hold.scope",
                scope=("func.verifies",),
                reason="attachment is ambiguous",
                applied_by=candidate_evidence(),
                release_conditions=("versioned policy re-evaluation",),
            )

    def test_assertion_evidence_cannot_bypass_release_policy(self) -> None:
        with self.assertRaisesRegex(ValueError, "hold_release"):
            Hold(
                hold_id="hold.scope",
                scope=("func.verifies",),
                reason="attachment is ambiguous",
                applied_by=policy_evidence(),
                release_conditions=("versioned policy re-evaluation",),
                released_by=support_evidence(),
            )

    def test_versioned_release_policy_can_release_hold(self) -> None:
        hold = Hold(
            hold_id="hold.scope",
            scope=("func.verifies",),
            reason="attachment is ambiguous",
            applied_by=policy_evidence(),
            release_conditions=("assertion-capable re-evaluation",),
            released_by=release_evidence(),
        )

        self.assertFalse(hold.is_open)

    def test_terminal_satisfaction_rejects_partial_coverage(self) -> None:
        partial = GuardCoverage(
            status=Coverage.PARTIAL,
            required_checks=("record_boundary", "scope"),
            completed_checks=("record_boundary",),
            unresolved_reasons=("scope_not_checked",),
        )

        with self.assertRaisesRegex(ValueError, "complete obligation coverage"):
            ObligationResult(
                obligation_id="func.verifies",
                outcome=Outcome.SATISFIED,
                finality=Finality.TERMINAL,
                challenge=Challenge.NONE,
                coverage=partial,
                provenance=(support_evidence(),),
            )


class FailClosedAggregationTests(unittest.TestCase):
    def test_complete_terminal_required_obligations_allow_pass(self) -> None:
        result = aggregate_audit_result(
            execution=complete_execution(),
            obligations=(
                satisfied_obligation("func.verifies"),
                satisfied_obligation("func.produces_evidence"),
            ),
        )

        self.assertEqual(result.workflow, Workflow.PASS)
        self.assertEqual(result.outcome, Outcome.SATISFIED)
        self.assertEqual(result.finality, Finality.TERMINAL)
        self.assertEqual(result.challenge, Challenge.NONE)
        self.assertEqual(result.coverage, Coverage.COMPLETE)

    def test_unknown_obligation_never_becomes_pass(self) -> None:
        unresolved = ObligationResult(
            obligation_id="func.verifies",
            outcome=Outcome.UNDETERMINED,
            finality=Finality.PROVISIONAL,
            challenge=Challenge.OPEN,
            coverage=complete_coverage(),
            provenance=(candidate_evidence(),),
            unknown_reasons=("verification target has two plausible attachments",),
        )

        result = aggregate_audit_result(
            execution=complete_execution(),
            obligations=(unresolved,),
        )

        self.assertEqual(result.workflow, Workflow.WARN)
        self.assertEqual(result.outcome, Outcome.UNDETERMINED)
        self.assertEqual(result.challenge, Challenge.OPEN)
        self.assertIn("unknown:func.verifies", "\n".join(result.reasons))

    def test_provider_failure_never_becomes_pass(self) -> None:
        result = aggregate_audit_result(
            execution=complete_execution(
                provider_failures=("dependency-provider:timeout",),
            ),
            obligations=(satisfied_obligation(),),
        )

        self.assertEqual(result.workflow, Workflow.WARN)
        self.assertEqual(result.outcome, Outcome.UNDETERMINED)
        self.assertIn("provider_failure:dependency-provider:timeout", result.reasons)

    def test_partial_execution_coverage_never_becomes_pass(self) -> None:
        partial = GuardCoverage(
            status=Coverage.PARTIAL,
            required_checks=("record_boundary", "scope"),
            completed_checks=("record_boundary",),
            unresolved_reasons=("scope_not_checked",),
        )

        result = aggregate_audit_result(
            execution=complete_execution(coverage=partial),
            obligations=(satisfied_obligation(),),
        )

        self.assertEqual(result.workflow, Workflow.WARN)
        self.assertEqual(result.coverage, Coverage.PARTIAL)
        self.assertEqual(result.finality, Finality.PROVISIONAL)

    def test_open_execution_hold_never_becomes_pass(self) -> None:
        hold = Hold(
            hold_id="hold.attachment",
            scope=("func.verifies",),
            reason="candidate parser found a competing attachment",
            applied_by=policy_evidence(),
            release_conditions=("direct re-evaluation resolves the attachment",),
        )

        result = aggregate_audit_result(
            execution=complete_execution(holds=(hold,)),
            obligations=(satisfied_obligation(),),
        )

        self.assertEqual(result.workflow, Workflow.WARN)
        self.assertEqual(result.challenge, Challenge.OPEN)
        self.assertIn("open_hold:hold.attachment", result.reasons)

    def test_conflict_blocks_but_does_not_claim_refutation(self) -> None:
        conflict = ObligationResult(
            obligation_id="func.verifies",
            outcome=Outcome.UNDETERMINED,
            finality=Finality.PROVISIONAL,
            challenge=Challenge.CONFLICT,
            coverage=complete_coverage(),
            provenance=(candidate_evidence(),),
            interpretations=("method verifies latency", "method verifies throughput"),
            unknown_reasons=("equal-authority interpretations conflict",),
        )

        result = aggregate_audit_result(
            execution=complete_execution(),
            obligations=(conflict,),
        )

        self.assertEqual(result.workflow, Workflow.BLOCK)
        self.assertEqual(result.outcome, Outcome.UNDETERMINED)
        self.assertEqual(result.challenge, Challenge.CONFLICT)

    def test_integrity_failure_is_invalid_and_blocks(self) -> None:
        result = aggregate_audit_result(
            execution=complete_execution(
                integrity_failures=("source_digest_mismatch",),
            ),
            obligations=(satisfied_obligation(),),
        )

        self.assertEqual(result.workflow, Workflow.BLOCK)
        self.assertEqual(result.outcome, Outcome.INVALID)
        self.assertEqual(result.finality, Finality.INVALID)

    def test_empty_obligation_set_cannot_vacuously_pass(self) -> None:
        result = aggregate_audit_result(
            execution=complete_execution(),
            obligations=(),
        )

        self.assertEqual(result.workflow, Workflow.WARN)
        self.assertEqual(result.outcome, Outcome.UNDETERMINED)

    def test_explicit_terminal_not_applicable_can_pass(self) -> None:
        not_applicable = ObligationResult(
            obligation_id="profile.applicability",
            outcome=Outcome.NOT_APPLICABLE,
            finality=Finality.TERMINAL,
            challenge=Challenge.NONE,
            coverage=complete_coverage(),
            active=False,
            required=False,
            provenance=(support_evidence("evidence.not-applicable"),),
        )

        result = aggregate_audit_result(
            execution=complete_execution(),
            obligations=(not_applicable,),
        )

        self.assertEqual(result.workflow, Workflow.PASS)
        self.assertEqual(result.outcome, Outcome.NOT_APPLICABLE)

    def test_not_applicable_cannot_hide_an_active_required_obligation(self) -> None:
        with self.assertRaisesRegex(
            ValueError, "not_applicable requires an inactive, non-required obligation"
        ):
            ObligationResult(
                obligation_id="required.obligation",
                outcome=Outcome.NOT_APPLICABLE,
                finality=Finality.TERMINAL,
                challenge=Challenge.NONE,
                coverage=complete_coverage(),
                active=True,
                required=True,
                provenance=(support_evidence("evidence.invalid-na"),),
            )

    def test_wire_result_keeps_dimensions_separate_and_has_no_score(self) -> None:
        result = aggregate_audit_result(
            execution=complete_execution(),
            obligations=(satisfied_obligation(),),
        )

        payload = result.as_dict()
        self.assertEqual(payload["outcome"], "satisfied")
        self.assertEqual(payload["finality"], "terminal")
        self.assertEqual(payload["challenge"], "none")
        self.assertEqual(payload["coverage"], "complete")
        self.assertEqual(payload["workflow"], "pass")
        self.assertNotIn("score", payload)

    def test_manual_result_cannot_hide_partial_coverage_behind_complete(self) -> None:
        partial = GuardCoverage(
            status=Coverage.PARTIAL,
            required_checks=("record_boundary", "scope"),
            completed_checks=("record_boundary",),
            unresolved_reasons=("scope_not_checked",),
        )

        with self.assertRaisesRegex(ValueError, "aggregate coverage"):
            AuditResult(
                execution=complete_execution(coverage=partial),
                obligations=(satisfied_obligation(),),
                outcome=Outcome.UNDETERMINED,
                finality=Finality.PROVISIONAL,
                challenge=Challenge.NONE,
                coverage=Coverage.COMPLETE,
                workflow=Workflow.WARN,
            )

    def test_manual_pass_cannot_claim_refuted_outcome(self) -> None:
        with self.assertRaisesRegex(ValueError, "pass dimensions"):
            AuditResult(
                execution=complete_execution(),
                obligations=(satisfied_obligation(),),
                outcome=Outcome.REFUTED,
                finality=Finality.TERMINAL,
                challenge=Challenge.NONE,
                coverage=Coverage.COMPLETE,
                workflow=Workflow.PASS,
            )


if __name__ == "__main__":
    unittest.main()
