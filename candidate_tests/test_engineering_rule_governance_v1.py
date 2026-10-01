from __future__ import annotations

import copy
import unittest

from semantic_guard_vnext.engineering_rule_governance import (
    CANDIDATE_AUTHORITY,
    EngineeringRuleGovernanceError,
    bind_external_human_decision,
    bind_external_human_review,
    build_candidate_review,
    build_governance_bundle,
    build_implementation_binding,
    build_pack_manifest,
    build_pending_human_decision,
    build_rule_basis,
    build_runtime_request,
    build_runtime_rule_request,
    resolve_runtime,
    sha256_digest,
    validate_governance_bundle,
)


FORMAL_AUTHORITY = {
    "finding_authority": "formal_finding",
    "routing_authority": "may_escalate_unresolved",
    "nonconformance_authority": "permitted",
    "satisfaction_authority": "permitted",
    "not_applicable_authority": "permitted",
    "hold_apply_authority": "permitted",
    "hold_release_authority": "permitted",
    "final_verdict_authority": "permitted",
}


def verifier_record(label: str) -> dict:
    return {
        "record_id": f"verifier.{label}",
        "locator": f"trust/verifiers/{label}.json",
        "content_digest": sha256_digest(f"verifier-content:{label}"),
    }


def source_binding(label: str = "basis", status: str = "verified") -> dict:
    return {
        "source_id": f"source.{label}",
        "source_version": "1",
        "locator": f"sources/{label}.md",
        "section_locator": "section.1",
        "content_digest": sha256_digest(f"source-{label}"),
        "binding_status": status,
    }


def revision_material() -> dict:
    return {
        "revision_targets": ["rule-level provenance"],
        "revision_reasons": ["source mapping is not sufficient"],
        "revision_owner_ref": "human.rule-owner",
        "next_action": "Bind the exact source and repeat domain review.",
        "resolution_conditions": ["Source and interpretation digests match."],
        "re_review_condition": "A new immutable rule basis is available.",
        "audit_finding_refs": ["finding.rule.source-unbound"],
    }


def external_human_review_fixture(basis: dict) -> dict:
    """Assemble external review input; production code must not create it."""

    record = {
        "schema_version": "engineering-rule-review/v1",
        "review_id": f"review.{basis['rule_id']}.ready",
        "rule_ref": {
            "rule_id": basis["rule_id"],
            "rule_version": basis["rule_version"],
            "basis_digest": copy.deepcopy(basis["basis_digest"]),
        },
        "review_source": "external_human_record",
        "reviewer_ref": "human.domain-reviewer",
        "reviewer_kind": "human",
        "review_independence": "independent_human_review",
        "review_authority": "adoption_material",
        "reviewer_qualification_refs": ["qualification.requirements-engineering"],
        "audit_assessment": "adoption_ready",
        "finding_refs": [],
        "evidence_status": "sufficient",
        "non_binding_recommendation": "accept",
        "recommendation_rationale": (
            "Supplied external review material is complete for this fixture."
        ),
        "review_evidence_refs": ["evidence.domain-review"],
    }
    record["review_digest"] = sha256_digest(record)
    return record


def external_human_decision_fixture(
    *,
    decision_id: str,
    target_kind: str,
    target_id: str,
    target_version: str,
    target_digest: dict,
    pack: dict,
    disposition: str,
    decision_owner_ref: str,
    rationale: str,
    granted_authority: dict,
    authenticity: str,
    authenticity_evidence_ref: str | None,
    decided_at: str,
    record_ref: str,
    revision: dict | None,
    decision_actor_kind: str = "human",
) -> dict:
    """Assemble external input explicitly; production code must not create it."""

    record = {
        "schema_version": "engineering-rule-human-decision/v1",
        "decision_id": decision_id,
        "target_kind": target_kind,
        "target_id": target_id,
        "target_version": target_version,
        "target_digest": copy.deepcopy(target_digest),
        "target_pack_manifest_digest": copy.deepcopy(pack["manifest_digest"]),
        "human_decision": disposition,
        "decision_source": "external_human_record",
        "decision_owner_ref": decision_owner_ref,
        "decision_actor_kind": decision_actor_kind,
        "decision_authenticity": {
            "status": authenticity,
            "evidence_ref": authenticity_evidence_ref,
        },
        "decided_at": decided_at,
        "record_ref": record_ref,
        "rationale": rationale,
        "granted_authority": copy.deepcopy(granted_authority),
        "revision": copy.deepcopy(revision),
    }
    record["decision_digest"] = sha256_digest(record)
    return record


def trusted_decision_verifier_fixture(decision: dict) -> bool:
    """Model an injected trust provider; it is not real identity evidence."""

    return (
        decision["decision_source"] == "external_human_record"
        and isinstance(decision["record_ref"], str)
        and decision["record_ref"].startswith("decisions/")
    )


trusted_decision_verifier_fixture.verifier_ref = verifier_record("decision-fixture")


def trusted_reviewer_verifier_fixture(review: dict) -> bool:
    """Model a distinct injected reviewer trust provider for tests only."""

    return (
        review["review_source"] == "external_human_record"
        and review["reviewer_kind"] == "human"
        and bool(review["review_evidence_refs"])
    )


trusted_reviewer_verifier_fixture.verifier_ref = verifier_record("reviewer-fixture")


class TrustedRuntimeVerifierFixture:
    """Model an injected receipt verifier; it is not a production trust root."""

    verifier_ref = verifier_record("runtime-fixture")

    def __call__(self, receipt: dict) -> bool:
        return (
            receipt["receipt_source"] == "external_resolution_record"
            and receipt["record_ref"].startswith("runtime-receipts/")
            and bool(receipt["evidence_refs"])
        )


trusted_runtime_verifier_fixture = TrustedRuntimeVerifierFixture()


def runtime_receipt_fixture(
    *, claim_kind: str, target_ref: str, claim_digest: dict, suffix: str
) -> dict:
    record = {
        "schema_version": "engineering-rule-runtime-receipt/v1",
        "receipt_id": f"runtime-receipt.{suffix}",
        "receipt_source": "external_resolution_record",
        "claim_kind": claim_kind,
        "target_ref": target_ref,
        "claim_digest": copy.deepcopy(claim_digest),
        "issuer_ref": "runtime-resolution-provider.fixture",
        "issued_at": "2026-07-18T00:02:00Z",
        "record_ref": f"runtime-receipts/{suffix}.json",
        "evidence_refs": [f"evidence.runtime.{suffix}"],
    }
    record["receipt_digest"] = sha256_digest(record)
    return record


def formal_runtime_receipts(
    bases: list[dict], implementations: list[dict], *, scope: str
) -> list[dict]:
    request_id = "runtime-request.fixture"
    profile = {
        "profile_id": "profile.functional-requirement",
        "profile_version": "v1",
        "basis_digest": sha256_digest("profile-basis"),
        "resolution_status": "resolved_formal",
    }
    obligation_digest = sha256_digest("obligation-assessment")
    receipts = [
        runtime_receipt_fixture(
            claim_kind="profile_resolution",
            target_ref=profile["profile_id"],
            claim_digest=sha256_digest(profile),
            suffix="profile",
        ),
        runtime_receipt_fixture(
            claim_kind="evidence_currency",
            target_ref=request_id,
            claim_digest=sha256_digest(
                {
                    "subject_scope_id": scope,
                    "evidence_currency": "current",
                    "obligation_assessment_digest": obligation_digest,
                }
            ),
            suffix="currency",
        ),
        runtime_receipt_fixture(
            claim_kind="obligation_assessment",
            target_ref=request_id,
            claim_digest=sha256_digest(
                {
                    "subject_scope_id": scope,
                    "all_required_obligations_satisfied": True,
                    "obligation_assessment_digest": obligation_digest,
                }
            ),
            suffix="obligations",
        ),
    ]
    for index, (basis, implementation) in enumerate(
        zip(bases, implementations), start=1
    ):
        for source_index, binding in enumerate(basis["source_bindings"], start=1):
            target_ref = "/".join(
                (
                    basis["rule_id"],
                    basis["rule_version"],
                    binding["source_id"],
                    binding["source_version"],
                    binding["section_locator"],
                )
            )
            receipts.append(
                runtime_receipt_fixture(
                    claim_kind="source_binding",
                    target_ref=target_ref,
                    claim_digest=sha256_digest(
                        {
                            "rule_ref": {
                                "rule_id": basis["rule_id"],
                                "rule_version": basis["rule_version"],
                                "basis_digest": basis["basis_digest"],
                            },
                            "source_binding": binding,
                        }
                    ),
                    suffix=f"source-{index}-{source_index}",
                )
            )
        receipts.append(
            runtime_receipt_fixture(
                claim_kind="implementation_verification",
                target_ref=implementation["binding_id"],
                claim_digest=sha256_digest(
                    {
                        "rule_ref": {
                            "rule_id": basis["rule_id"],
                            "rule_version": basis["rule_version"],
                            "basis_digest": basis["basis_digest"],
                        },
                        "binding_digest": implementation["binding_digest"],
                        "implementation_digest": implementation[
                            "implementation_digest"
                        ],
                        "implementation_status": implementation[
                            "implementation_status"
                        ],
                        "verification_evidence_refs": implementation[
                            "verification_evidence_refs"
                        ],
                    }
                ),
                suffix=f"implementation-{index}",
            )
        )
    return receipts


class EngineeringRuleGovernanceV1Tests(unittest.TestCase):
    def basis(
        self,
        suffix: str = "a",
        *,
        artifact_content: bytes | None = None,
        source_status: str = "verified",
        authority: dict | None = None,
        applicability_scope_ids: list[str] | None = None,
        exception_id: str | None = None,
    ) -> dict:
        return build_rule_basis(
            rule_id=f"engineering.functional.{suffix}",
            rule_version="v1",
            artifact_locator=f"rules/{suffix}.json",
            artifact_content=artifact_content or f"artifact-{suffix}".encode(),
            engineering_proposition=f"Rule {suffix} proposition.",
            interpretation=f"Bounded interpretation for {suffix}.",
            required_evidence=["source text", "counterexample set"],
            limitations=["Not universal natural-language truth."],
            source_bindings=[source_binding(suffix, source_status)],
            applicability_scope_ids=(
                applicability_scope_ids or ["scope.functional-requirement"]
            ),
            applicability_conditions=["A closed structured record is supplied."],
            exceptions=[
                {
                    "exception_id": exception_id or f"exception.{suffix}.formal-model",
                    "condition": "A separately validated formal model supplies the relation.",
                    "effect": "unresolved",
                }
            ],
            requested_authority=authority or FORMAL_AUTHORITY,
        )

    def review(
        self,
        basis: dict,
        *,
        ready: bool = False,
        reviewer_kind: str | None = None,
        independence: str | None = None,
    ) -> dict:
        if ready:
            record = external_human_review_fixture(basis)
            if reviewer_kind is not None:
                record["reviewer_kind"] = reviewer_kind
            if independence is not None:
                record["review_independence"] = independence
            if reviewer_kind is not None or independence is not None:
                record["review_digest"] = sha256_digest(
                    {
                        key: value
                        for key, value in record.items()
                        if key != "review_digest"
                    }
                )
            return bind_external_human_review(
                record,
                basis=basis,
            )
        return build_candidate_review(
            review_id=f"review.{basis['rule_id']}.candidate",
            basis=basis,
            reviewer_ref="ai.isolated-reviewer",
            reviewer_kind=reviewer_kind or "ai",
            review_independence=independence or "isolated_context_review",
            reviewer_qualification_refs=[],
            audit_assessment="adoption_not_ready",
            finding_refs=["finding.rule.source-unbound"],
            evidence_status="insufficient",
            non_binding_recommendation="request_revision",
            recommendation_rationale="The candidate lacks adoption evidence.",
            review_evidence_refs=["evidence.isolated-review"],
        )

    def implementation(self, basis: dict, *, verified: bool = False) -> dict:
        return build_implementation_binding(
            binding_id=f"binding.{basis['rule_id']}",
            basis=basis,
            implementation_id=f"implementation.{basis['rule_id']}",
            implementation_version="1",
            entry_point="semantic_guard_vnext.direct_rules:evaluate_direct_relations",
            artifacts=[
                {
                    "locator": "semantic_guard_vnext/direct_rules.py",
                    "content_digest": sha256_digest(
                        f"implementation-{basis['rule_id']}"
                    ),
                }
            ],
            implementation_status="verified" if verified else "partially_implemented",
            verification_evidence_refs=(
                ["evidence.implementation-verification"] if verified else []
            ),
        )

    def rule_decision(
        self,
        basis: dict,
        pack: dict,
        *,
        disposition: str = "pending",
        authenticity: str = "unproved",
        authority: dict | None = None,
    ) -> dict:
        if disposition == "pending":
            return build_pending_human_decision(
                decision_id=f"decision.{basis['rule_id']}.pending",
                target_kind="rule",
                target_id=basis["rule_id"],
                target_version=basis["rule_version"],
                target_digest=basis["basis_digest"],
                pack_manifest=pack,
                decision_owner_ref="human.rule-owner",
                rationale="An external rule disposition is still required.",
            )
        record = external_human_decision_fixture(
            decision_id=f"decision.{basis['rule_id']}.{disposition}",
            target_kind="rule",
            target_id=basis["rule_id"],
            target_version=basis["rule_version"],
            target_digest=basis["basis_digest"],
            pack=pack,
            disposition=disposition,
            decision_owner_ref="human.rule-owner",
            rationale="Explicit external fixture; not evidence of a real human act.",
            granted_authority=authority
            or (FORMAL_AUTHORITY if disposition == "accept" else CANDIDATE_AUTHORITY),
            authenticity=authenticity,
            authenticity_evidence_ref=(
                "evidence.human-authenticity" if authenticity == "verified" else None
            ),
            decided_at="2026-07-18T00:00:00Z",
            record_ref="decisions/rule.json",
            revision=revision_material() if disposition == "request_revision" else None,
        )
        return bind_external_human_decision(
            record,
            pack_manifest=pack,
            expected_target_kind="rule",
            expected_target_id=basis["rule_id"],
            expected_target_version=basis["rule_version"],
            expected_target_digest=basis["basis_digest"],
        )

    def h1_decision(
        self,
        pack: dict,
        *,
        disposition: str = "pending",
        authenticity: str = "unproved",
    ) -> dict:
        if disposition == "pending":
            return build_pending_human_decision(
                decision_id="decision.H1.pending",
                target_kind="h1_gate",
                target_id="H1",
                target_version=pack["pack_version"],
                target_digest=pack["manifest_digest"],
                pack_manifest=pack,
                decision_owner_ref="human.assurance-owner",
                rationale="An external H1 disposition is still required.",
            )
        record = external_human_decision_fixture(
            decision_id=f"decision.H1.{disposition}",
            target_kind="h1_gate",
            target_id="H1",
            target_version=pack["pack_version"],
            target_digest=pack["manifest_digest"],
            pack=pack,
            disposition=disposition,
            decision_owner_ref="human.assurance-owner",
            rationale="Explicit external H1 fixture; not evidence of a real human act.",
            granted_authority=CANDIDATE_AUTHORITY,
            authenticity=authenticity,
            authenticity_evidence_ref=(
                "evidence.h1-human-authenticity" if authenticity == "verified" else None
            ),
            decided_at="2026-07-18T00:01:00Z",
            record_ref="decisions/H1.json",
            revision=revision_material() if disposition == "request_revision" else None,
        )
        return bind_external_human_decision(
            record,
            pack_manifest=pack,
            expected_target_kind="h1_gate",
            expected_target_id="H1",
            expected_target_version=pack["pack_version"],
            expected_target_digest=pack["manifest_digest"],
        )

    def runtime_request(
        self,
        requests: list[dict],
        *,
        profile_status: str = "resolved_formal",
        evidence_currency: str = "current",
        satisfied: bool = True,
        active_exception_ids: list[str] | None = None,
        scope: str = "scope.functional-requirement",
        runtime_receipts: list[dict] | None = None,
    ) -> dict:
        return build_runtime_request(
            request_id="runtime-request.fixture",
            subject_scope_id=scope,
            profile_id="profile.functional-requirement",
            profile_version="v1",
            profile_basis_digest=sha256_digest("profile-basis"),
            profile_resolution_status=profile_status,
            evidence_currency=evidence_currency,
            all_required_obligations_satisfied=satisfied,
            obligation_assessment_digest=sha256_digest("obligation-assessment"),
            rule_requests=requests,
            active_exception_ids=active_exception_ids or [],
            runtime_receipts=runtime_receipts or [],
        )

    def candidate_bundle(self) -> dict:
        basis = self.basis()
        review = self.review(basis)
        implementation = self.implementation(basis)
        pack = build_pack_manifest(
            pack_id="engineering-rule-pack.functional",
            pack_version="v1",
            subject_scope_ids=["scope.functional-requirement"],
            required_bases=[basis],
        )
        decisions = [self.rule_decision(basis, pack), self.h1_decision(pack)]
        request = self.runtime_request(
            [
                build_runtime_rule_request(
                    basis=basis,
                    implementation_binding=implementation,
                    requested_authority=CANDIDATE_AUTHORITY,
                    observed_artifact_digest=basis["artifact_digest"],
                    observed_implementation_digest=implementation[
                        "implementation_digest"
                    ],
                )
            ]
        )
        return build_governance_bundle(
            bundle_id="bundle.engineering-rule-governance.fixture",
            bundle_version="1",
            rule_bases=[basis],
            reviews=[review],
            human_decisions=decisions,
            implementation_bindings=[implementation],
            pack_manifest=pack,
            runtime_request=request,
            resolution_id="resolution.fixture",
        )

    def test_candidate_bundle_is_closed_but_has_no_formal_authority(self) -> None:
        bundle = self.candidate_bundle()
        validate_governance_bundle(bundle)

        rule = bundle["runtime_resolution"]["rule_resolutions"][0]
        self.assertEqual(rule["resolution_status"], "candidate_only")
        self.assertEqual(rule["effective_authority"], CANDIDATE_AUTHORITY)
        self.assertEqual(rule["governance_states"]["evidence_status"], "insufficient")
        self.assertEqual(rule["governance_states"]["adoption_status"], "candidate")
        self.assertEqual(
            rule["governance_states"]["implementation_status"],
            "partially_implemented",
        )
        self.assertEqual(
            bundle["runtime_resolution"]["pack_resolution"]["formal_verdict_authority"],
            "none",
        )
        self.assertEqual(bundle["h1_gate_view"]["human_decision"], "pending")
        self.assertEqual(bundle["h1_gate_view"]["verdict_authority"], "none")

    def test_non_binding_request_revision_does_not_set_human_decision(self) -> None:
        bundle = self.candidate_bundle()
        gate = bundle["h1_gate_view"]

        self.assertEqual(gate["audit_assessment"], "adoption_not_ready")
        self.assertEqual(gate["non_binding_recommendation"], "request_revision")
        self.assertEqual(gate["human_decision"], "pending")

    def test_audit_side_builder_can_only_request_a_pending_decision(self) -> None:
        bundle = self.candidate_bundle()

        for decision in bundle["human_decisions"]:
            self.assertEqual(decision["human_decision"], "pending")
            self.assertEqual(decision["decision_source"], "pending_gate_request")
            self.assertEqual(decision["granted_authority"], CANDIDATE_AUTHORITY)
            self.assertIsNone(decision["record_ref"])

    def test_request_revision_requires_complete_revision_material(self) -> None:
        basis = self.basis()
        pack = build_pack_manifest(
            pack_id="engineering-rule-pack.functional",
            pack_version="v1",
            subject_scope_ids=["scope.functional-requirement"],
            required_bases=[basis],
        )
        record = external_human_decision_fixture(
            decision_id="decision.incomplete-revision",
            target_kind="h1_gate",
            target_id="H1",
            target_version="v1",
            target_digest=pack["manifest_digest"],
            pack=pack,
            disposition="request_revision",
            decision_owner_ref="human.owner",
            rationale="Incomplete on purpose.",
            granted_authority=CANDIDATE_AUTHORITY,
            authenticity="verified",
            authenticity_evidence_ref="evidence.human",
            decided_at="2026-07-18T00:00:00Z",
            record_ref="decisions/incomplete.json",
            revision=None,
        )
        with self.assertRaisesRegex(
            EngineeringRuleGovernanceError,
            "request_revision requires complete revision material",
        ):
            bind_external_human_decision(
                record,
                pack_manifest=pack,
                expected_target_kind="h1_gate",
                expected_target_id="H1",
                expected_target_version="v1",
                expected_target_digest=pack["manifest_digest"],
            )

    def test_ai_review_cannot_claim_independent_review(self) -> None:
        basis = self.basis()
        with self.assertRaisesRegex(
            EngineeringRuleGovernanceError,
            "AI review cannot be represented as independent review",
        ):
            self.review(
                basis,
                reviewer_kind="ai",
                independence="independent_human_review",
            )

        isolated = self.review(basis)
        self.assertEqual(isolated["review_authority"], "candidate_only")

        with self.assertRaisesRegex(
            EngineeringRuleGovernanceError,
            "cannot construct a human review",
        ):
            self.review(basis, reviewer_kind="human")

    def test_ai_cannot_construct_human_decision(self) -> None:
        basis = self.basis()
        pack = build_pack_manifest(
            pack_id="engineering-rule-pack.functional",
            pack_version="v1",
            subject_scope_ids=["scope.functional-requirement"],
            required_bases=[basis],
        )
        forged = external_human_decision_fixture(
            decision_id="decision.ai-forgery",
            target_kind="rule",
            target_id=basis["rule_id"],
            target_version=basis["rule_version"],
            target_digest=basis["basis_digest"],
            pack=pack,
            disposition="accept",
            decision_owner_ref="human.owner",
            decision_actor_kind="ai",
            rationale="Forgery fixture.",
            granted_authority=FORMAL_AUTHORITY,
            authenticity="verified",
            authenticity_evidence_ref="evidence.forged",
            decided_at="2026-07-18T00:00:00Z",
            record_ref="decisions/forged.json",
            revision=None,
        )
        with self.assertRaisesRegex(
            EngineeringRuleGovernanceError, "decision_actor_kind"
        ):
            bind_external_human_decision(
                forged,
                pack_manifest=pack,
                expected_target_kind="rule",
                expected_target_id=basis["rule_id"],
                expected_target_version=basis["rule_version"],
                expected_target_digest=basis["basis_digest"],
            )

    def test_artifact_change_invalidates_basis_without_trusted_normalizer(
        self,
    ) -> None:
        first = self.basis(artifact_content=b'{"a":1}')
        second = self.basis(artifact_content=b'{\n  "a": 1\n}')

        self.assertEqual(first["content_digest"], second["content_digest"])
        self.assertNotEqual(first["basis_digest"], second["basis_digest"])
        self.assertNotEqual(first["artifact_digest"], second["artifact_digest"])
        self.assertNotEqual(first["record_digest"], second["record_digest"])

    def test_source_change_changes_basis_digest(self) -> None:
        first = self.basis()
        changed_source = source_binding("a")
        changed_source["content_digest"] = sha256_digest("changed-source")
        second = build_rule_basis(
            rule_id=first["rule_id"],
            rule_version=first["rule_version"],
            artifact_locator=first["artifact_locator"],
            artifact_content=b"artifact-a",
            engineering_proposition=first["semantic_content"][
                "engineering_proposition"
            ],
            interpretation=first["semantic_content"]["interpretation"],
            required_evidence=first["semantic_content"]["required_evidence"],
            limitations=first["semantic_content"]["limitations"],
            source_bindings=[changed_source],
            applicability_scope_ids=first["applicability"]["scope_ids"],
            applicability_conditions=first["applicability"]["conditions"],
            exceptions=first["exceptions"],
            requested_authority=first["requested_authority"],
        )

        self.assertEqual(first["content_digest"], second["content_digest"])
        self.assertNotEqual(first["basis_digest"], second["basis_digest"])

    def resolved_components(
        self,
        *,
        authentic_rule: bool = True,
        basis: dict | None = None,
        pack_scope_ids: list[str] | None = None,
        runtime_scope: str = "scope.functional-requirement",
    ):
        basis = basis or self.basis()
        review = self.review(basis, ready=True)
        implementation = self.implementation(basis, verified=True)
        pack = build_pack_manifest(
            pack_id="engineering-rule-pack.functional",
            pack_version="v1",
            subject_scope_ids=(pack_scope_ids or ["scope.functional-requirement"]),
            required_bases=[basis],
        )
        rule_decision = self.rule_decision(
            basis,
            pack,
            disposition="accept",
            authenticity="verified" if authentic_rule else "unproved",
        )
        h1 = self.h1_decision(pack, disposition="accept", authenticity="verified")
        rule_request = build_runtime_rule_request(
            basis=basis,
            implementation_binding=implementation,
            requested_authority=FORMAL_AUTHORITY,
            observed_artifact_digest=basis["artifact_digest"],
            observed_implementation_digest=implementation["implementation_digest"],
        )
        request = self.runtime_request(
            [rule_request],
            scope=runtime_scope,
            runtime_receipts=formal_runtime_receipts(
                [basis], [implementation], scope=runtime_scope
            ),
        )
        return basis, review, implementation, pack, rule_decision, h1, request

    def test_empty_authenticity_evidence_does_not_formally_resolve_adoption(
        self,
    ) -> None:
        basis, review, implementation, pack, rule_decision, h1, request = (
            self.resolved_components(authentic_rule=False)
        )
        resolution = resolve_runtime(
            resolution_id="resolution.unproved-human",
            rule_bases=[basis],
            reviews=[review],
            human_decisions=[rule_decision, h1],
            implementation_bindings=[implementation],
            pack_manifest=pack,
            runtime_request=request,
            trusted_reviewer_verifier=trusted_reviewer_verifier_fixture,
            trusted_decision_verifier=trusted_decision_verifier_fixture,
            trusted_runtime_verifier=trusted_runtime_verifier_fixture,
        )

        rule = resolution["rule_resolutions"][0]
        self.assertEqual(rule["resolution_status"], "candidate_only")
        self.assertIn("human_decision_authenticity_unproved", rule["reason_codes"])
        self.assertEqual(
            resolution["pack_resolution"]["formal_verdict_authority"], "none"
        )

    def test_verified_flags_without_trusted_verifier_remain_candidate_only(
        self,
    ) -> None:
        basis, review, implementation, pack, rule_decision, h1, request = (
            self.resolved_components()
        )
        resolution = resolve_runtime(
            resolution_id="resolution.no-trust-provider",
            rule_bases=[basis],
            reviews=[review],
            human_decisions=[rule_decision, h1],
            implementation_bindings=[implementation],
            pack_manifest=pack,
            runtime_request=request,
            trusted_reviewer_verifier=trusted_reviewer_verifier_fixture,
            trusted_runtime_verifier=trusted_runtime_verifier_fixture,
        )

        rule = resolution["rule_resolutions"][0]
        self.assertEqual(rule["resolution_status"], "candidate_only")
        self.assertEqual(
            rule["governance_states"]["decision_trust_status"],
            "missing_verifier",
        )
        self.assertIn("human_decision_missing_verifier", rule["reason_codes"])
        self.assertIn("h1_human_decision_missing_verifier", rule["reason_codes"])
        self.assertEqual(
            resolution["pack_resolution"]["formal_verdict_authority"], "none"
        )

    def test_human_review_flags_without_reviewer_verifier_remain_candidate_only(
        self,
    ) -> None:
        basis, review, implementation, pack, rule_decision, h1, request = (
            self.resolved_components()
        )
        resolution = resolve_runtime(
            resolution_id="resolution.no-review-trust-provider",
            rule_bases=[basis],
            reviews=[review],
            human_decisions=[rule_decision, h1],
            implementation_bindings=[implementation],
            pack_manifest=pack,
            runtime_request=request,
            trusted_decision_verifier=trusted_decision_verifier_fixture,
            trusted_runtime_verifier=trusted_runtime_verifier_fixture,
        )

        rule = resolution["rule_resolutions"][0]
        self.assertEqual(rule["resolution_status"], "candidate_only")
        self.assertEqual(
            rule["governance_states"]["review_trust_status"],
            "missing_verifier",
        )
        self.assertIn("review_missing_verifier", rule["reason_codes"])
        self.assertEqual(
            resolution["pack_resolution"]["formal_verdict_authority"], "none"
        )

    def test_false_or_failing_trust_providers_fail_closed(self) -> None:
        basis, review, implementation, pack, rule_decision, h1, request = (
            self.resolved_components()
        )

        def reject(_: dict) -> bool:
            return False

        def fail(_: dict) -> bool:
            raise RuntimeError("trust provider unavailable")

        reject.verifier_ref = verifier_record("rejecting-fixture")
        fail.verifier_ref = verifier_record("failing-fixture")

        variants = (
            (reject, trusted_decision_verifier_fixture, "review_verification_failed"),
            (fail, trusted_decision_verifier_fixture, "review_verification_failed"),
            (
                trusted_reviewer_verifier_fixture,
                reject,
                "human_decision_verification_failed",
            ),
            (
                trusted_reviewer_verifier_fixture,
                fail,
                "human_decision_verification_failed",
            ),
        )
        for reviewer_verifier, decision_verifier, expected_reason in variants:
            with self.subTest(
                reason=expected_reason, verifier=reviewer_verifier.__name__
            ):
                resolution = resolve_runtime(
                    resolution_id="resolution.failed-trust-provider",
                    rule_bases=[basis],
                    reviews=[review],
                    human_decisions=[rule_decision, h1],
                    implementation_bindings=[implementation],
                    pack_manifest=pack,
                    runtime_request=request,
                    trusted_reviewer_verifier=reviewer_verifier,
                    trusted_decision_verifier=decision_verifier,
                    trusted_runtime_verifier=trusted_runtime_verifier_fixture,
                )
                rule = resolution["rule_resolutions"][0]
                self.assertEqual(rule["resolution_status"], "candidate_only")
                self.assertIn(expected_reason, rule["reason_codes"])
                self.assertEqual(
                    resolution["pack_resolution"]["formal_verdict_authority"],
                    "none",
                )

    def test_anonymous_true_verifiers_cannot_create_formal_authority(self) -> None:
        basis, review, implementation, pack, rule_decision, h1, request = (
            self.resolved_components()
        )
        resolution = resolve_runtime(
            resolution_id="resolution.anonymous-verifiers",
            rule_bases=[basis],
            reviews=[review],
            human_decisions=[rule_decision, h1],
            implementation_bindings=[implementation],
            pack_manifest=pack,
            runtime_request=request,
            trusted_reviewer_verifier=lambda _: True,
            trusted_decision_verifier=lambda _: True,
            trusted_runtime_verifier=trusted_runtime_verifier_fixture,
        )

        rule = resolution["rule_resolutions"][0]
        self.assertEqual(rule["resolution_status"], "candidate_only")
        self.assertEqual(
            rule["governance_states"]["review_trust_status"], "missing_verifier"
        )
        self.assertEqual(
            rule["governance_states"]["decision_trust_status"], "missing_verifier"
        )
        self.assertIsNone(resolution["trust_context"]["reviewer_verifier_ref"])
        self.assertIsNone(resolution["trust_context"]["decision_verifier_ref"])
        self.assertEqual(
            resolution["pack_resolution"]["formal_verdict_authority"], "none"
        )

    def test_supplied_verifier_claims_cannot_create_formal_authority(self) -> None:
        basis, review, implementation, pack, rule_decision, h1, request = (
            self.resolved_components()
        )
        resolution = resolve_runtime(
            resolution_id="resolution.exact",
            rule_bases=[basis],
            reviews=[review],
            human_decisions=[rule_decision, h1],
            implementation_bindings=[implementation],
            pack_manifest=pack,
            runtime_request=request,
            trusted_reviewer_verifier=trusted_reviewer_verifier_fixture,
            trusted_decision_verifier=trusted_decision_verifier_fixture,
            trusted_runtime_verifier=trusted_runtime_verifier_fixture,
        )

        self.assertEqual(
            resolution["rule_resolutions"][0]["resolution_status"],
            "candidate_only",
        )
        self.assertEqual(resolution["pack_resolution"]["status"], "candidate_only")
        self.assertEqual(
            resolution["pack_resolution"]["formal_verdict_authority"],
            "none",
        )
        self.assertEqual(
            resolution["pack_resolution"]["h1_decision_trust_status"],
            "verifier_claim_accepted",
        )
        self.assertIn(
            "external_trust_control_not_integrated",
            resolution["rule_resolutions"][0]["reason_codes"],
        )
        self.assertEqual(
            resolution["rule_resolutions"][0]["effective_authority"],
            CANDIDATE_AUTHORITY,
        )
        self.assertEqual(
            resolution["pack_resolution"]["runtime_verifier_ref"],
            trusted_runtime_verifier_fixture.verifier_ref,
        )
        self.assertEqual(
            resolution["pack_resolution"]["reviewer_verifier_ref"],
            trusted_reviewer_verifier_fixture.verifier_ref,
        )
        self.assertEqual(
            resolution["pack_resolution"]["decision_verifier_ref"],
            trusted_decision_verifier_fixture.verifier_ref,
        )
        self.assertEqual(
            resolution["trust_context"]["review_inputs"][0]["target_record_digest"],
            review["review_digest"],
        )
        self.assertEqual(len(resolution["trust_context"]["decision_inputs"]), 2)

    def test_runtime_rule_request_requires_explicit_observed_digests(self) -> None:
        basis = self.basis()
        implementation = self.implementation(basis)

        with self.assertRaises(TypeError):
            build_runtime_rule_request(
                basis=basis,
                implementation_binding=implementation,
                requested_authority=CANDIDATE_AUTHORITY,
            )

    def test_runtime_self_assertions_without_receipts_never_resolve_formally(
        self,
    ) -> None:
        basis, review, implementation, pack, rule_decision, h1, request = (
            self.resolved_components()
        )
        request["runtime_receipts"] = []
        resolution = resolve_runtime(
            resolution_id="resolution.runtime-self-assertions",
            rule_bases=[basis],
            reviews=[review],
            human_decisions=[rule_decision, h1],
            implementation_bindings=[implementation],
            pack_manifest=pack,
            runtime_request=request,
            trusted_reviewer_verifier=trusted_reviewer_verifier_fixture,
            trusted_decision_verifier=trusted_decision_verifier_fixture,
            trusted_runtime_verifier=trusted_runtime_verifier_fixture,
        )

        rule = resolution["rule_resolutions"][0]
        self.assertEqual(rule["resolution_status"], "candidate_only")
        for reason in (
            "profile_resolution_receipt_missing",
            "evidence_currency_receipt_missing",
            "obligation_assessment_receipt_missing",
            "source_binding_receipt_missing",
            "implementation_verification_receipt_missing",
        ):
            self.assertIn(reason, rule["reason_codes"])
        self.assertEqual(
            resolution["pack_resolution"]["formal_verdict_authority"], "none"
        )

    def test_sealed_receipts_without_runtime_verifier_remain_candidate_only(
        self,
    ) -> None:
        basis, review, implementation, pack, rule_decision, h1, request = (
            self.resolved_components()
        )
        resolution = resolve_runtime(
            resolution_id="resolution.runtime-verifier-missing",
            rule_bases=[basis],
            reviews=[review],
            human_decisions=[rule_decision, h1],
            implementation_bindings=[implementation],
            pack_manifest=pack,
            runtime_request=request,
            trusted_reviewer_verifier=trusted_reviewer_verifier_fixture,
            trusted_decision_verifier=trusted_decision_verifier_fixture,
        )

        rule = resolution["rule_resolutions"][0]
        self.assertEqual(rule["resolution_status"], "candidate_only")
        self.assertIn(
            "profile_resolution_trusted_runtime_verifier_missing",
            rule["reason_codes"],
        )
        self.assertIsNone(resolution["pack_resolution"]["runtime_verifier_ref"])

    def test_runtime_verifier_requires_a_stable_verifier_ref(self) -> None:
        basis, review, implementation, pack, rule_decision, h1, request = (
            self.resolved_components()
        )

        def verifier_without_ref(_: dict) -> bool:
            return True

        resolution = resolve_runtime(
            resolution_id="resolution.runtime-verifier-ref-missing",
            rule_bases=[basis],
            reviews=[review],
            human_decisions=[rule_decision, h1],
            implementation_bindings=[implementation],
            pack_manifest=pack,
            runtime_request=request,
            trusted_reviewer_verifier=trusted_reviewer_verifier_fixture,
            trusted_decision_verifier=trusted_decision_verifier_fixture,
            trusted_runtime_verifier=verifier_without_ref,
        )

        rule = resolution["rule_resolutions"][0]
        self.assertEqual(rule["resolution_status"], "candidate_only")
        self.assertIn(
            "profile_resolution_runtime_verifier_ref_missing",
            rule["reason_codes"],
        )

    def test_verified_source_and_implementation_require_trusted_receipts(
        self,
    ) -> None:
        basis, review, implementation, pack, rule_decision, h1, request = (
            self.resolved_components()
        )
        request["runtime_receipts"] = [
            receipt
            for receipt in request["runtime_receipts"]
            if receipt["claim_kind"]
            not in {"source_binding", "implementation_verification"}
        ]
        resolution = resolve_runtime(
            resolution_id="resolution.rule-receipts-missing",
            rule_bases=[basis],
            reviews=[review],
            human_decisions=[rule_decision, h1],
            implementation_bindings=[implementation],
            pack_manifest=pack,
            runtime_request=request,
            trusted_reviewer_verifier=trusted_reviewer_verifier_fixture,
            trusted_decision_verifier=trusted_decision_verifier_fixture,
            trusted_runtime_verifier=trusted_runtime_verifier_fixture,
        )

        rule = resolution["rule_resolutions"][0]
        self.assertEqual(rule["resolution_status"], "candidate_only")
        self.assertIn("source_binding_receipt_missing", rule["reason_codes"])
        self.assertIn(
            "implementation_verification_receipt_missing", rule["reason_codes"]
        )

    def test_runtime_receipt_claim_mismatch_is_unresolved(self) -> None:
        basis, review, implementation, pack, rule_decision, h1, request = (
            self.resolved_components()
        )
        receipt = next(
            item
            for item in request["runtime_receipts"]
            if item["claim_kind"] == "profile_resolution"
        )
        receipt["claim_digest"] = sha256_digest("different-profile-claim")
        receipt["receipt_digest"] = sha256_digest(
            {key: value for key, value in receipt.items() if key != "receipt_digest"}
        )
        resolution = resolve_runtime(
            resolution_id="resolution.runtime-receipt-mismatch",
            rule_bases=[basis],
            reviews=[review],
            human_decisions=[rule_decision, h1],
            implementation_bindings=[implementation],
            pack_manifest=pack,
            runtime_request=request,
            trusted_reviewer_verifier=trusted_reviewer_verifier_fixture,
            trusted_decision_verifier=trusted_decision_verifier_fixture,
            trusted_runtime_verifier=trusted_runtime_verifier_fixture,
        )

        rule = resolution["rule_resolutions"][0]
        self.assertEqual(rule["resolution_status"], "unresolved")
        self.assertIn("profile_resolution_receipt_claim_mismatch", rule["reason_codes"])

    def test_candidate_bundle_replay_requires_the_same_runtime_verifier(self) -> None:
        basis, review, implementation, pack, rule_decision, h1, request = (
            self.resolved_components()
        )
        bundle = build_governance_bundle(
            bundle_id="bundle.engineering-rule-governance.verifier-fixture",
            bundle_version="1",
            rule_bases=[basis],
            reviews=[review],
            human_decisions=[rule_decision, h1],
            implementation_bindings=[implementation],
            pack_manifest=pack,
            runtime_request=request,
            resolution_id="resolution.verifier-fixture",
            trusted_reviewer_verifier=trusted_reviewer_verifier_fixture,
            trusted_decision_verifier=trusted_decision_verifier_fixture,
            trusted_runtime_verifier=trusted_runtime_verifier_fixture,
        )

        validate_governance_bundle(
            bundle,
            trusted_reviewer_verifier=trusted_reviewer_verifier_fixture,
            trusted_decision_verifier=trusted_decision_verifier_fixture,
            trusted_runtime_verifier=trusted_runtime_verifier_fixture,
        )
        with self.assertRaisesRegex(
            EngineeringRuleGovernanceError, "runtime resolution replay mismatch"
        ):
            validate_governance_bundle(
                bundle,
                trusted_reviewer_verifier=trusted_reviewer_verifier_fixture,
                trusted_decision_verifier=trusted_decision_verifier_fixture,
            )

        stripped = copy.deepcopy(bundle)
        stripped["limitations"] = [
            item
            for item in stripped["limitations"]
            if not item.startswith("Sealed runtime receipts are portable records")
        ]
        stripped["bundle_digest"] = sha256_digest(
            {key: value for key, value in stripped.items() if key != "bundle_digest"}
        )
        with self.assertRaisesRegex(
            EngineeringRuleGovernanceError, "missing required limitations"
        ):
            validate_governance_bundle(
                stripped,
                trusted_reviewer_verifier=trusted_reviewer_verifier_fixture,
                trusted_decision_verifier=trusted_decision_verifier_fixture,
                trusted_runtime_verifier=trusted_runtime_verifier_fixture,
            )

    def test_untrusted_nonpending_h1_record_is_reported_but_not_projected(
        self,
    ) -> None:
        basis, review, implementation, pack, rule_decision, h1, request = (
            self.resolved_components()
        )
        bundle = build_governance_bundle(
            bundle_id="bundle.engineering-rule-governance.untrusted-h1",
            bundle_version="1",
            rule_bases=[basis],
            reviews=[review],
            human_decisions=[rule_decision, h1],
            implementation_bindings=[implementation],
            pack_manifest=pack,
            runtime_request=request,
            resolution_id="resolution.untrusted-h1",
            trusted_reviewer_verifier=trusted_reviewer_verifier_fixture,
            trusted_runtime_verifier=trusted_runtime_verifier_fixture,
        )

        gate = bundle["h1_gate_view"]
        self.assertEqual(gate["reported_human_decision"], "accept")
        self.assertEqual(gate["decision_trust_status"], "missing_verifier")
        self.assertEqual(gate["human_decision"], "pending")
        self.assertEqual(gate["verdict_authority"], "none")

    def test_implementation_digest_mismatch_is_unresolved(self) -> None:
        basis, review, implementation, pack, rule_decision, h1, request = (
            self.resolved_components()
        )
        request["rule_requests"][0]["implementation_digest"] = sha256_digest(
            "different-implementation"
        )
        resolution = resolve_runtime(
            resolution_id="resolution.implementation-mismatch",
            rule_bases=[basis],
            reviews=[review],
            human_decisions=[rule_decision, h1],
            implementation_bindings=[implementation],
            pack_manifest=pack,
            runtime_request=request,
            trusted_reviewer_verifier=trusted_reviewer_verifier_fixture,
            trusted_decision_verifier=trusted_decision_verifier_fixture,
            trusted_runtime_verifier=trusted_runtime_verifier_fixture,
        )

        rule = resolution["rule_resolutions"][0]
        self.assertEqual(rule["resolution_status"], "unresolved")
        self.assertIn("implementation_digest_mismatch", rule["reason_codes"])

    def test_scope_authority_and_active_exception_mismatches_fail_closed(self) -> None:
        basis, review, implementation, pack, rule_decision, h1, request = (
            self.resolved_components()
        )
        variants = []
        wrong_scope = copy.deepcopy(request)
        wrong_scope["subject_scope_id"] = "scope.similar-but-different"
        variants.append((wrong_scope, "rule_scope_mismatch"))
        wrong_authority = copy.deepcopy(request)
        wrong_authority["rule_requests"][0]["requested_authority"] = copy.deepcopy(
            CANDIDATE_AUTHORITY
        )
        variants.append((wrong_authority, "runtime_authority_request_mismatch"))
        active_exception = copy.deepcopy(request)
        active_exception["active_exception_ids"] = ["exception.a.formal-model"]
        variants.append((active_exception, "active_exception_requires_disposition"))
        unknown_exception = copy.deepcopy(request)
        unknown_exception["active_exception_ids"] = ["exception.unknown"]
        variants.append((unknown_exception, "unknown_active_exception_identifier"))

        for runtime_request, reason in variants:
            with self.subTest(reason=reason):
                resolution = resolve_runtime(
                    resolution_id=f"resolution.{reason}",
                    rule_bases=[basis],
                    reviews=[review],
                    human_decisions=[rule_decision, h1],
                    implementation_bindings=[implementation],
                    pack_manifest=pack,
                    runtime_request=runtime_request,
                    trusted_reviewer_verifier=trusted_reviewer_verifier_fixture,
                    trusted_decision_verifier=trusted_decision_verifier_fixture,
                    trusted_runtime_verifier=trusted_runtime_verifier_fixture,
                )
                rule = resolution["rule_resolutions"][0]
                self.assertEqual(rule["resolution_status"], "unresolved")
                self.assertIn(reason, rule["reason_codes"])

    def test_duplicate_active_exception_input_is_rejected(self) -> None:
        basis = self.basis()
        implementation = self.implementation(basis)
        request = build_runtime_rule_request(
            basis=basis,
            implementation_binding=implementation,
            requested_authority=CANDIDATE_AUTHORITY,
            observed_artifact_digest=basis["artifact_digest"],
            observed_implementation_digest=implementation["implementation_digest"],
        )
        with self.assertRaises(EngineeringRuleGovernanceError):
            self.runtime_request(
                [request],
                active_exception_ids=["exception.same", "exception.same"],
            )

    def test_cross_rule_duplicate_exception_identifiers_block_formal_resolution(
        self,
    ) -> None:
        scope = "scope.functional-requirement"
        bases = [
            self.basis("a", exception_id="exception.shared"),
            self.basis("b", exception_id="exception.shared"),
        ]
        reviews = [self.review(item, ready=True) for item in bases]
        implementations = [self.implementation(item, verified=True) for item in bases]
        pack = build_pack_manifest(
            pack_id="engineering-rule-pack.duplicate-exception",
            pack_version="v1",
            subject_scope_ids=[scope],
            required_bases=bases,
        )
        decisions = [
            self.rule_decision(
                item, pack, disposition="accept", authenticity="verified"
            )
            for item in bases
        ]
        decisions.append(
            self.h1_decision(pack, disposition="accept", authenticity="verified")
        )
        requests = [
            build_runtime_rule_request(
                basis=basis,
                implementation_binding=implementation,
                requested_authority=FORMAL_AUTHORITY,
                observed_artifact_digest=basis["artifact_digest"],
                observed_implementation_digest=implementation["implementation_digest"],
            )
            for basis, implementation in zip(bases, implementations)
        ]
        runtime_request = self.runtime_request(
            requests,
            scope=scope,
            runtime_receipts=formal_runtime_receipts(
                bases, implementations, scope=scope
            ),
        )

        resolution = resolve_runtime(
            resolution_id="resolution.duplicate-exception",
            rule_bases=bases,
            reviews=reviews,
            human_decisions=decisions,
            implementation_bindings=implementations,
            pack_manifest=pack,
            runtime_request=runtime_request,
            trusted_reviewer_verifier=trusted_reviewer_verifier_fixture,
            trusted_decision_verifier=trusted_decision_verifier_fixture,
            trusted_runtime_verifier=trusted_runtime_verifier_fixture,
        )

        self.assertEqual(resolution["pack_resolution"]["status"], "unresolved")
        self.assertIn(
            "duplicate_exception_identifier",
            resolution["pack_resolution"]["reason_codes"],
        )
        for rule in resolution["rule_resolutions"]:
            self.assertEqual(rule["resolution_status"], "unresolved")

    def test_h1_assessment_uses_only_required_rule_denominator(self) -> None:
        required = self.basis("required")
        excluded = self.basis("excluded")
        required_implementation = self.implementation(required, verified=True)
        excluded_implementation = self.implementation(excluded)
        pack = build_pack_manifest(
            pack_id="engineering-rule-pack.partitioned",
            pack_version="v1",
            subject_scope_ids=["scope.functional-requirement"],
            required_bases=[required],
            excluded_bases=[(excluded, "not applicable to this pack")],
        )
        reviews = [self.review(required, ready=True), self.review(excluded)]
        decisions = [
            self.rule_decision(
                required, pack, disposition="accept", authenticity="verified"
            ),
            self.rule_decision(excluded, pack),
            self.h1_decision(pack, disposition="accept", authenticity="verified"),
        ]
        rule_request = build_runtime_rule_request(
            basis=required,
            implementation_binding=required_implementation,
            requested_authority=FORMAL_AUTHORITY,
            observed_artifact_digest=required["artifact_digest"],
            observed_implementation_digest=required_implementation[
                "implementation_digest"
            ],
        )
        runtime_request = self.runtime_request(
            [rule_request],
            runtime_receipts=formal_runtime_receipts(
                [required],
                [required_implementation],
                scope="scope.functional-requirement",
            ),
        )

        bundle = build_governance_bundle(
            bundle_id="governance-bundle.partitioned",
            bundle_version="v1",
            rule_bases=[required, excluded],
            reviews=reviews,
            human_decisions=decisions,
            implementation_bindings=[
                required_implementation,
                excluded_implementation,
            ],
            pack_manifest=pack,
            runtime_request=runtime_request,
            resolution_id="resolution.partitioned",
            trusted_reviewer_verifier=trusted_reviewer_verifier_fixture,
            trusted_decision_verifier=trusted_decision_verifier_fixture,
            trusted_runtime_verifier=trusted_runtime_verifier_fixture,
        )

        gate = bundle["h1_gate_view"]
        self.assertEqual(gate["assessment_scope"], "required_rule_denominator")
        self.assertEqual(gate["audit_assessment"], "adoption_ready_for_human_decision")
        self.assertEqual(gate["non_required_review_count"], 1)
        self.assertEqual(
            gate["non_required_review_assessments"], ["adoption_not_ready"]
        )
        self.assertEqual(gate["verdict_authority"], "none")
        self.assertEqual(gate["blocking_status"], "blocking_positive_assurance")

    def test_rule_applicability_cannot_expand_the_adopted_pack_scope(self) -> None:
        declared_scope = "scope.pack-declared"
        outside_scope = "scope.outside-pack"
        basis = self.basis(applicability_scope_ids=[declared_scope, outside_scope])
        basis, review, implementation, pack, rule_decision, h1, request = (
            self.resolved_components(
                basis=basis,
                pack_scope_ids=[declared_scope],
                runtime_scope=outside_scope,
            )
        )

        resolution = resolve_runtime(
            resolution_id="resolution.pack-scope-boundary",
            rule_bases=[basis],
            reviews=[review],
            human_decisions=[rule_decision, h1],
            implementation_bindings=[implementation],
            pack_manifest=pack,
            runtime_request=request,
            trusted_reviewer_verifier=trusted_reviewer_verifier_fixture,
            trusted_decision_verifier=trusted_decision_verifier_fixture,
            trusted_runtime_verifier=trusted_runtime_verifier_fixture,
        )

        rule = resolution["rule_resolutions"][0]
        self.assertEqual(rule["resolution_status"], "unresolved")
        self.assertIn("pack_subject_scope_mismatch", rule["reason_codes"])
        self.assertEqual(resolution["pack_resolution"]["status"], "unresolved")
        self.assertEqual(
            resolution["pack_resolution"]["formal_verdict_authority"],
            "none",
        )
        self.assertIn(
            "pack_subject_scope_mismatch",
            resolution["pack_resolution"]["reason_codes"],
        )

    def test_every_required_rule_must_apply_to_the_runtime_scope(self) -> None:
        runtime_scope = "scope.pack-declared"
        first = self.basis("a", applicability_scope_ids=[runtime_scope])
        second = self.basis("b", applicability_scope_ids=["scope.different-rule-scope"])
        bases = [first, second]
        reviews = [self.review(item, ready=True) for item in bases]
        implementations = [self.implementation(item, verified=True) for item in bases]
        pack = build_pack_manifest(
            pack_id="engineering-rule-pack.functional",
            pack_version="v1",
            subject_scope_ids=[runtime_scope],
            required_bases=bases,
        )
        decisions = [
            self.rule_decision(
                item,
                pack,
                disposition="accept",
                authenticity="verified",
            )
            for item in bases
        ]
        decisions.append(
            self.h1_decision(pack, disposition="accept", authenticity="verified")
        )
        requests = [
            build_runtime_rule_request(
                basis=basis,
                implementation_binding=implementation,
                requested_authority=FORMAL_AUTHORITY,
                observed_artifact_digest=basis["artifact_digest"],
                observed_implementation_digest=implementation["implementation_digest"],
            )
            for basis, implementation in zip(bases, implementations)
        ]
        request = self.runtime_request(
            requests,
            scope=runtime_scope,
            runtime_receipts=formal_runtime_receipts(
                bases, implementations, scope=runtime_scope
            ),
        )

        resolution = resolve_runtime(
            resolution_id="resolution.required-rule-scope-boundary",
            rule_bases=bases,
            reviews=reviews,
            human_decisions=decisions,
            implementation_bindings=implementations,
            pack_manifest=pack,
            runtime_request=request,
            trusted_reviewer_verifier=trusted_reviewer_verifier_fixture,
            trusted_decision_verifier=trusted_decision_verifier_fixture,
            trusted_runtime_verifier=trusted_runtime_verifier_fixture,
        )

        by_rule = {item["rule_id"]: item for item in resolution["rule_resolutions"]}
        self.assertEqual(
            by_rule[first["rule_id"]]["resolution_status"], "candidate_only"
        )
        self.assertEqual(by_rule[second["rule_id"]]["resolution_status"], "unresolved")
        self.assertIn(
            "rule_scope_mismatch",
            by_rule[second["rule_id"]]["reason_codes"],
        )
        self.assertEqual(resolution["pack_resolution"]["status"], "unresolved")
        self.assertEqual(
            resolution["pack_resolution"]["formal_verdict_authority"],
            "none",
        )

    def test_legacy_or_similarly_named_rule_does_not_fallback(self) -> None:
        basis, review, implementation, pack, rule_decision, h1, request = (
            self.resolved_components()
        )
        for rule_id, version in (
            (basis["rule_id"], "v0"),
            (basis["rule_id"] + ".similar", "v1"),
        ):
            with self.subTest(rule_id=rule_id, version=version):
                altered = copy.deepcopy(request)
                altered["rule_requests"][0]["rule_id"] = rule_id
                altered["rule_requests"][0]["rule_version"] = version
                resolution = resolve_runtime(
                    resolution_id="resolution.no-fallback",
                    rule_bases=[basis],
                    reviews=[review],
                    human_decisions=[rule_decision, h1],
                    implementation_bindings=[implementation],
                    pack_manifest=pack,
                    runtime_request=altered,
                    trusted_reviewer_verifier=trusted_reviewer_verifier_fixture,
                    trusted_decision_verifier=trusted_decision_verifier_fixture,
                    trusted_runtime_verifier=trusted_runtime_verifier_fixture,
                )
                self.assertEqual(resolution["pack_resolution"]["status"], "unresolved")
                self.assertTrue(
                    any(
                        "unknown_or_unsupported_rule_identity" in item["reason_codes"]
                        or "runtime_rule_denominator_mismatch"
                        in resolution["pack_resolution"]["reason_codes"]
                        for item in resolution["rule_resolutions"]
                    )
                )

    def test_partial_adoption_never_becomes_pack_adoption(self) -> None:
        first = self.basis("a")
        second = self.basis("b")
        reviews = [self.review(first, ready=True), self.review(second)]
        implementations = [
            self.implementation(first, verified=True),
            self.implementation(second),
        ]
        pack = build_pack_manifest(
            pack_id="engineering-rule-pack.functional",
            pack_version="v1",
            subject_scope_ids=["scope.functional-requirement"],
            required_bases=[first, second],
        )
        decisions = [
            self.rule_decision(
                first, pack, disposition="accept", authenticity="verified"
            ),
            self.rule_decision(second, pack),
            self.h1_decision(pack, disposition="accept", authenticity="verified"),
        ]
        request = self.runtime_request(
            [
                build_runtime_rule_request(
                    basis=first,
                    implementation_binding=implementations[0],
                    requested_authority=FORMAL_AUTHORITY,
                    observed_artifact_digest=first["artifact_digest"],
                    observed_implementation_digest=implementations[0][
                        "implementation_digest"
                    ],
                ),
                build_runtime_rule_request(
                    basis=second,
                    implementation_binding=implementations[1],
                    requested_authority=CANDIDATE_AUTHORITY,
                    observed_artifact_digest=second["artifact_digest"],
                    observed_implementation_digest=implementations[1][
                        "implementation_digest"
                    ],
                ),
            ],
            runtime_receipts=formal_runtime_receipts(
                [first, second],
                implementations,
                scope="scope.functional-requirement",
            ),
        )
        resolution = resolve_runtime(
            resolution_id="resolution.partial",
            rule_bases=[first, second],
            reviews=reviews,
            human_decisions=decisions,
            implementation_bindings=implementations,
            pack_manifest=pack,
            runtime_request=request,
            trusted_reviewer_verifier=trusted_reviewer_verifier_fixture,
            trusted_decision_verifier=trusted_decision_verifier_fixture,
            trusted_runtime_verifier=trusted_runtime_verifier_fixture,
        )

        self.assertEqual(resolution["pack_resolution"]["resolved_formal_count"], 0)
        self.assertEqual(resolution["pack_resolution"]["candidate_count"], 2)
        self.assertEqual(resolution["pack_resolution"]["status"], "candidate_only")
        self.assertEqual(
            resolution["pack_resolution"]["formal_verdict_authority"], "none"
        )

    def test_trace_preserves_rule_source_scope_findings_and_governance_refs(
        self,
    ) -> None:
        bundle = self.candidate_bundle()
        rule = bundle["runtime_resolution"]["rule_resolutions"][0]
        trace = rule["trace"]

        self.assertEqual(trace["rule_ref"]["rule_id"], "engineering.functional.a")
        self.assertEqual(trace["subject_scope_id"], "scope.functional-requirement")
        self.assertEqual(trace["finding_refs"], ["finding.rule.source-unbound"])
        self.assertEqual(trace["source_bindings"][0]["source_id"], "source.a")
        for field in (
            "basis_record_digest",
            "review_digest",
            "human_decision_digest",
            "implementation_binding_digest",
            "pack_manifest_digest",
            "profile_basis_digest",
        ):
            self.assertEqual(trace[field]["algorithm"], "sha256")

    def test_digest_and_derived_state_tampering_is_rejected(self) -> None:
        bundle = self.candidate_bundle()
        changed_basis = copy.deepcopy(bundle)
        changed_basis["rule_bases"][0]["semantic_content"][
            "engineering_proposition"
        ] = "Changed without resealing."
        with self.assertRaisesRegex(
            EngineeringRuleGovernanceError, "rule content digest mismatch"
        ):
            validate_governance_bundle(changed_basis)

        changed_gate = copy.deepcopy(bundle)
        changed_gate["h1_gate_view"]["human_decision"] = "accept"
        with self.assertRaisesRegex(
            EngineeringRuleGovernanceError,
            "h1_gate_view/human_decision|H1 gate view replay mismatch",
        ):
            validate_governance_bundle(changed_gate)

    def test_bundle_build_is_deterministic(self) -> None:
        first = self.candidate_bundle()
        second = self.candidate_bundle()
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
