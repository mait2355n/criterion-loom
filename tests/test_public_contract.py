from __future__ import annotations

import copy
from dataclasses import replace
from pathlib import Path
import unittest

from jsonschema import ValidationError

from semantic_guard.engine import (
    audit_requirement_relations as _audit_requirement_relations,
)
from semantic_guard import __version__
from semantic_guard.provider_receipts import AnalyzerQualification
from semantic_guard.providers import (
    AnalysisAttempt,
    AnalysisSpan,
    ProviderAuthority,
    ProviderRequest,
    RelationCandidate,
    ScopeCandidate,
    TokenCandidate,
)
from semantic_guard.public_contract import (
    KNOWN_SCHEMA_NAMES,
    public_audit_payload,
    validate_public_audit,
)
from semantic_guard.reassessment import REQUIRED_CAPABILITIES, policy_scope


COMPLETE = """Purpose: 検索APIが検索結果を p95 500ms以内で返す
User: 検索API
Scenario: 検索APIが検索要求を処理して検索結果を返す
Expected result: 検索結果を p95 500ms以内で返す
Acceptance criteria: 検索応答時間 p95 500ms 以下
Verification method: 検索結果の検索応答時間を benchmark で測定する
Evidence: 検索結果の検索応答時間 benchmark report"""

RECORDED_AT = "2026-07-16T00:00:00Z"


class SchemaRegistryTests(unittest.TestCase):
    def test_known_schema_names_cover_every_bundled_contract(self) -> None:
        schema_dir = Path(__file__).resolve().parents[1] / "schemas"
        present = {
            path.name.removesuffix(".schema.json")
            for path in schema_dir.glob("*.schema.json")
        }
        self.assertEqual(KNOWN_SCHEMA_NAMES, present)


def audit_requirement_relations(text: str, **kwargs):
    """Keep projection tests isolated; production default is assurance."""

    kwargs.setdefault("analysis_mode", "conditional")
    return _audit_requirement_relations(text, **kwargs)


class PassiveMorphology:
    provider_id = "passive-morphology"
    provider_version = "test-v1"
    resource_version = "fixture-v1"
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
        )


class HostileDependencyCandidate:
    provider_id = "hostile-dependency"
    provider_version = "test-v1"
    resource_version = "fixture-v1"
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
                    interpretation_id="interpretation.hostile-candidate",
                    rationale="A deliberately conflicting candidate for authority-boundary testing.",
                ),
            ),
        )


class EmptyMorphology:
    provider_id = "empty-morphology"
    provider_version = "test-v1"
    resource_version = "fixture-v1"
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


class ConditionDependency:
    provider_id = "condition-dependency"
    provider_version = "test-v1"
    resource_version = "fixture-v1"
    stage = "dependency_parse"

    def analyze(self, request: ProviderRequest) -> AnalysisAttempt:
        cue_start = request.text.index("場合は")
        target_start = request.text.index("返す", request.text.index("Scenario:"))
        cue = AnalysisSpan(cue_start, cue_start + len("場合は"), "condition")
        target = AnalysisSpan(target_start, target_start + len("返す"), "predicate")
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


class PublicContractTests(unittest.TestCase):
    def test_public_audit_identifies_its_producer_release(self) -> None:
        payload = public_audit_payload(
            audit_requirement_relations(COMPLETE),
            recorded_at=RECORDED_AT,
        )
        producer = next(
            item
            for item in payload["provenance"]
            if item["source_ref"].get("role") == "audit_producer"
        )

        self.assertEqual(__version__, "1.1.0")
        self.assertEqual(producer["source_ref"]["entity_id"], "semantic-guard")
        self.assertEqual(producer["source_ref"]["entity_version"], __version__)
        validate_public_audit(payload)

    def test_audit_identity_binds_receipt_reassessment_and_qualification_trace(self) -> None:
        report = _audit_requirement_relations(COMPLETE)
        receipt = report.provider_execution_receipts[0]
        receipt_changed = replace(
            report,
            provider_execution_receipts=(
                replace(receipt, upstream_usage=("changed-upstream-usage",)),
                *report.provider_execution_receipts[1:],
            ),
        )
        reassessment_changed = replace(
            report,
            obligation_reassessments=(
                replace(
                    report.obligation_reassessments[0],
                    reasons=("changed-reassessment-trace",),
                ),
                *report.obligation_reassessments[1:],
            ),
        )
        qualification_changed = replace(
            report,
            analyzer_qualifications=(
                AnalyzerQualification(
                    provider_id="fixture",
                    provider_version="1",
                    resource_version="resource-1",
                    capabilities=REQUIRED_CAPABILITIES,
                    policy_scope=policy_scope("func.performs"),
                    qualification_basis="audit identity fixture",
                ),
            ),
        )
        ids = {
            public_audit_payload(item, recorded_at=RECORDED_AT)["audit_id"]
            for item in (
                report,
                receipt_changed,
                reassessment_changed,
                qualification_changed,
            )
        }

        self.assertEqual(len(ids), 4)
        replayed_prior = replace(
            report,
            direct_assessments=(
                replace(report.direct_assessments[0], rule_id="replayed-rule/v0"),
                *report.direct_assessments[1:],
            ),
        )
        with self.assertRaisesRegex(ValueError, "trace binding mismatch"):
            public_audit_payload(replayed_prior, recorded_at=RECORDED_AT)

    def test_invalid_recorded_at_is_rejected_by_runtime_format_checker(self) -> None:
        payload = public_audit_payload(
            audit_requirement_relations(COMPLETE),
            recorded_at="not-a-date-time",
        )

        with self.assertRaises(ValidationError):
            validate_public_audit(payload)

    def test_terminal_pass_projects_every_closed_contract_section(self) -> None:
        report = audit_requirement_relations(COMPLETE)

        payload = public_audit_payload(report, recorded_at=RECORDED_AT)
        validate_public_audit(payload)

        self.assertEqual(payload["workflow_disposition"]["status"], "pass")
        self.assertEqual(payload["audit_conclusion"]["outcome"], "satisfied")
        self.assertEqual(payload["open_hold_ids"], [])
        self.assertEqual(payload["unresolved_required_obligation_ids"], [])
        self.assertTrue(payload["obligation_results"])
        self.assertTrue(payload["assurance_claims"])
        self.assertTrue(payload["source_spans"])
        self.assertTrue(payload["provenance"])
        self.assertEqual(
            payload["workflow_disposition"]["acceptance_owner"],
            "human_external_to_semantic_guard",
        )
        claim = payload["assurance_claims"][0]
        self.assertEqual(claim["assurance_level"], "derived_under_profile")
        self.assertIn("not human acceptance", claim["proposition"])
        self.assertEqual(payload["coverage"]["status"], "complete")
        self.assertEqual(payload["execution"]["coverage"]["status"], "complete")
        self.assertTrue(
            all(
                span["excerpt_verification"]
                == "not_reverified_without_source_text"
                for span in payload["source_spans"]
            )
        )

    def test_audit_identity_distinguishes_observations_of_the_same_subject(self) -> None:
        conditional = public_audit_payload(
            audit_requirement_relations(COMPLETE, analysis_mode="conditional"),
            recorded_at=RECORDED_AT,
        )
        assurance = public_audit_payload(
            audit_requirement_relations(COMPLETE, analysis_mode="assurance"),
            recorded_at=RECORDED_AT,
        )

        validate_public_audit(conditional)
        validate_public_audit(assurance)

        self.assertEqual(conditional["subject_ref"], assurance["subject_ref"])
        self.assertNotEqual(conditional["audit_id"], assurance["audit_id"])
        self.assertNotEqual(
            conditional["assurance_claims"][0]["claim_id"],
            assurance["assurance_claims"][0]["claim_id"],
        )
        self.assertNotEqual(
            conditional["assurance_claims"][0]["interpretations"][0]["interpretation_id"],
            assurance["assurance_claims"][0]["interpretations"][0]["interpretation_id"],
        )
        self.assertEqual(conditional["workflow_disposition"]["status"], "pass")
        self.assertEqual(assurance["workflow_disposition"]["status"], "warn")

        unresolved_text = COMPLETE.replace(
            "検索応答時間 p95 500ms 以下",
            "担当者によれば検索応答時間 p95 500ms 以下",
        )
        unresolved_conditional = public_audit_payload(
            audit_requirement_relations(
                unresolved_text,
                analysis_mode="conditional",
            ),
            recorded_at=RECORDED_AT,
        )
        unresolved_assurance = public_audit_payload(
            audit_requirement_relations(
                unresolved_text,
                analysis_mode="assurance",
            ),
            recorded_at=RECORDED_AT,
        )
        validate_public_audit(unresolved_conditional)
        validate_public_audit(unresolved_assurance)
        self.assertEqual(
            unresolved_conditional["subject_ref"],
            unresolved_assurance["subject_ref"],
        )
        self.assertNotEqual(
            unresolved_conditional["assurance_claims"][0]["unproven_scope"][0]["range_id"],
            unresolved_assurance["assurance_claims"][0]["unproven_scope"][0]["range_id"],
        )

    def test_public_validator_rejects_pass_with_unresolved_required_obligation(self) -> None:
        payload = public_audit_payload(
            audit_requirement_relations(COMPLETE),
            recorded_at=RECORDED_AT,
        )
        invalid = copy.deepcopy(payload)
        obligation = next(item for item in invalid["obligation_results"] if item["required"])
        obligation["outcome"] = "undetermined"
        obligation["finality"] = "provisional"
        obligation["unknown_reasons"] = ["other"]

        with self.assertRaisesRegex(
            ValidationError,
            "unresolved_required_obligation_ids",
        ):
            validate_public_audit(invalid)

        invalid["unresolved_required_obligation_ids"] = [obligation["obligation_id"]]
        invalid["workflow_disposition"]["status"] = "warn"
        with self.assertRaisesRegex(
            ValidationError,
            "workflow and audit conclusion",
        ):
            validate_public_audit(invalid)

    def test_public_validator_rejects_aggregate_coverage_mismatch(self) -> None:
        payload = public_audit_payload(
            audit_requirement_relations(COMPLETE),
            recorded_at=RECORDED_AT,
        )
        invalid = copy.deepcopy(payload)
        invalid["coverage"] = copy.deepcopy(invalid["coverage"])
        invalid["coverage"]["status"] = "partial"
        invalid["audit_conclusion"]["outcome"] = "undetermined"
        invalid["audit_conclusion"]["finality"] = "provisional"
        invalid["workflow_disposition"]["status"] = "warn"

        with self.assertRaisesRegex(ValidationError, "top-level coverage"):
            validate_public_audit(invalid)

    def test_public_validator_rejects_challenge_and_hold_projection_mismatches(self) -> None:
        text = COMPLETE.replace(
            "検索応答時間 p95 500ms 以下",
            "担当者によれば検索応答時間 p95 500ms 以下",
        )
        payload = public_audit_payload(
            audit_requirement_relations(text),
            recorded_at=RECORDED_AT,
        )

        missing_top_hold = copy.deepcopy(payload)
        missing_top_hold["open_hold_ids"] = []
        with self.assertRaisesRegex(ValidationError, "top-level open_hold_ids"):
            validate_public_audit(missing_top_hold)

        wrong_challenge = copy.deepcopy(payload)
        wrong_challenge["audit_conclusion"]["challenge"] = "none"
        with self.assertRaisesRegex(ValidationError, "conclusion challenge"):
            validate_public_audit(wrong_challenge)

        wrong_local_hold = copy.deepcopy(payload)
        obligation = next(
            item for item in wrong_local_hold["obligation_results"] if item["open_hold_ids"]
        )
        obligation["open_hold_ids"] = []
        with self.assertRaisesRegex(ValidationError, "open_hold_ids disagree with holds"):
            validate_public_audit(wrong_local_hold)

    def test_public_validator_rejects_source_identity_and_digest_mismatches(self) -> None:
        payload = public_audit_payload(
            audit_requirement_relations(COMPLETE),
            recorded_at=RECORDED_AT,
        )

        wrong_source = copy.deepcopy(payload)
        wrong_source["source_spans"][0]["source_ref"]["entity_id"] = (
            "sha256:" + "f" * 64
        )
        with self.assertRaisesRegex(ValidationError, "source_ref disagrees"):
            validate_public_audit(wrong_source)

        wrong_digest = copy.deepcopy(payload)
        wrong_digest["source_spans"][0]["source_digest"]["value"] = "0" * 64
        with self.assertRaisesRegex(ValidationError, "digest disagrees"):
            validate_public_audit(wrong_digest)

        wrong_subject = copy.deepcopy(payload)
        wrong_subject["subject_ref"]["entity_id"] = "sha256:" + "e" * 64
        with self.assertRaisesRegex(ValidationError, "input provenance source_ref"):
            validate_public_audit(wrong_subject)

    def test_public_validator_rejects_assurance_claim_meaning_substitution(self) -> None:
        payload = public_audit_payload(
            audit_requirement_relations(COMPLETE),
            recorded_at=RECORDED_AT,
        )

        wrong_subject = copy.deepcopy(payload)
        wrong_subject["assurance_claims"][0]["subject_ref"] = {
            "reference_kind": "ref",
            "entity_id": "subject.unrelated",
            "label_hint": "unrelated subject",
        }
        with self.assertRaisesRegex(ValidationError, "subject_ref disagrees"):
            validate_public_audit(wrong_subject)

        wrong_proposition = copy.deepcopy(payload)
        wrong_proposition["assurance_claims"][0]["proposition"] = (
            "An unrelated action occurred."
        )
        with self.assertRaisesRegex(ValidationError, "proposition disagrees"):
            validate_public_audit(wrong_proposition)

        empty_rules = copy.deepcopy(payload)
        empty_rules["assurance_claims"][0]["rules"] = []
        with self.assertRaises(ValidationError):
            validate_public_audit(empty_rules)

        substituted_evidence = copy.deepcopy(payload)
        substituted_evidence["assurance_claims"][0]["supporting_evidence_refs"] = [
            {
                "reference_kind": "ref",
                "entity_id": "evidence.unrelated",
                "label_hint": "unrelated evidence",
            }
        ]
        with self.assertRaisesRegex(ValidationError, "supporting evidence disagrees"):
            validate_public_audit(substituted_evidence)

    def test_public_validator_rejects_assurance_claim_state_divergence(self) -> None:
        payload = public_audit_payload(
            audit_requirement_relations(COMPLETE),
            recorded_at=RECORDED_AT,
        )
        invalid = copy.deepcopy(payload)
        claim = invalid["assurance_claims"][0]
        claim["outcome"] = "refuted"
        claim["finality"] = "terminal"
        claim["challenge"] = "open"
        claim["coverage"]["status"] = "partial"
        claim["challenging_evidence_refs"] = [claim["supporting_evidence_refs"][0]]
        claim["authority_effects"] = [
            {**claim["authority_effects"][0], "kind": "challenge"}
        ]

        with self.assertRaises(ValidationError):
            validate_public_audit(invalid)

    def test_decision_request_human_authority_combinations_are_closed(self) -> None:
        text = COMPLETE.replace(
            "検索応答時間 p95 500ms 以下",
            "担当者によれば検索応答時間 p95 500ms 以下",
        )
        payload = public_audit_payload(
            audit_requirement_relations(text),
            recorded_at=RECORDED_AT,
        )
        self.assertTrue(payload["decision_requests"])
        invalid = copy.deepcopy(payload)
        request = invalid["decision_requests"][0]
        request["issue_class"] = "final_acceptance"
        request["decision_need"]["resolution_kind"] = "final_acceptance"
        request["decision_need"]["required_authority"] = "evidence_acquisition"

        with self.assertRaises(ValidationError):
            validate_public_audit(invalid)

    def test_public_validator_does_not_claim_to_reverify_excerpt_without_source(self) -> None:
        payload = public_audit_payload(
            audit_requirement_relations(COMPLETE),
            recorded_at=RECORDED_AT,
        )

        self.assertTrue(payload["source_spans"])
        self.assertTrue(
            all(
                item["excerpt_verification"]
                == "not_reverified_without_source_text"
                for item in payload["source_spans"]
            )
        )
        invalid = copy.deepcopy(payload)
        invalid["source_spans"][0]["excerpt_verification"] = "verified"
        with self.assertRaises(ValidationError):
            validate_public_audit(invalid)

    def test_public_analysis_run_exposes_and_rechecks_capability_sets(self) -> None:
        payload = public_audit_payload(
            audit_requirement_relations(
                COMPLETE,
                morphology_provider=PassiveMorphology(),
                dependency_provider=HostileDependencyCandidate(),
                analysis_mode="shadow_all",
            ),
            recorded_at=RECORDED_AT,
        )
        validate_public_audit(payload)

        complete = next(
            item
            for item in payload["analysis_runs"]
            if item["execution"]["status"] == "complete"
        )
        execution = complete["execution"]
        self.assertEqual(complete["resource_version"], "fixture-v1")
        self.assertEqual(
            execution["fulfilled_capabilities"],
            execution["requested_capabilities"],
        )
        self.assertEqual(execution["missing_capabilities"], [])

        unrequested = copy.deepcopy(payload)
        run = next(
            item
            for item in unrequested["analysis_runs"]
            if item["execution"]["status"] == "complete"
        )
        run["execution"]["fulfilled_capabilities"].append("unrequested")
        with self.assertRaisesRegex(ValidationError, "outside its requested"):
            validate_public_audit(unrequested)

        wrong_difference = copy.deepcopy(payload)
        run = next(
            item
            for item in wrong_difference["analysis_runs"]
            if item["execution"]["status"] == "complete"
        )
        run["execution"]["fulfilled_capabilities"] = []
        with self.assertRaisesRegex(ValidationError, "missing_capabilities"):
            validate_public_audit(wrong_difference)

    def test_unresolved_warn_preserves_holds_and_decision_material(self) -> None:
        text = COMPLETE.replace(
            "検索応答時間 p95 500ms 以下",
            "担当者によれば検索応答時間 p95 500ms 以下",
        )
        report = audit_requirement_relations(text)

        payload = public_audit_payload(report, recorded_at=RECORDED_AT)
        validate_public_audit(payload)

        self.assertEqual(payload["workflow_disposition"]["status"], "warn")
        self.assertTrue(payload["unresolved_required_obligation_ids"])
        self.assertTrue(payload["open_hold_ids"])
        self.assertTrue(payload["decision_requests"])
        decision = payload["decision_requests"][0]
        self.assertTrue(decision["audit_holds"])
        self.assertFalse(decision["routing_boundary"]["is_control_decision"])
        self.assertFalse(decision["routing_boundary"]["is_human_question"])

    def test_conflicting_candidate_can_block_but_never_gains_support_or_hold_power(self) -> None:
        text = COMPLETE.replace(
            "検索応答時間 p95 500ms 以下",
            "検索応答時間 p95 500ms 以下とは定めない",
        )
        report = audit_requirement_relations(
            text,
            morphology_provider=PassiveMorphology(),
            dependency_provider=HostileDependencyCandidate(),
        )

        payload = public_audit_payload(report, recorded_at=RECORDED_AT)
        validate_public_audit(payload)

        self.assertEqual(payload["workflow_disposition"]["status"], "block")
        dependency = next(
            item for item in payload["analysis_runs"] if item["provider_kind"] == "dependency"
        )
        self.assertEqual(dependency["maximum_evidentiary_authority"], "candidate_only")
        self.assertFalse(dependency["authority_rights"]["support"])
        self.assertFalse(dependency["authority_rights"]["hold_apply"])
        self.assertFalse(dependency["authority_rights"]["hold_release"])
        self.assertFalse(dependency["output_contract"]["raw_output_may_satisfy_obligation"])
        self.assertFalse(
            any(
                effect["actor_ref"]["entity_id"] == "hostile-dependency"
                and effect["kind"] in {"support", "hold_apply", "hold_release"}
                for effect in payload["authority_effects"]
            )
        )

    def test_closed_schema_rejects_unknown_fields(self) -> None:
        payload = public_audit_payload(
            audit_requirement_relations(COMPLETE),
            recorded_at=RECORDED_AT,
        )
        invalid = copy.deepcopy(payload)
        invalid["uncontracted_claim"] = "the adapter must not silently widen the contract"

        with self.assertRaises(ValidationError):
            validate_public_audit(invalid)

    def test_terminal_refutation_carries_challenge_authority_evidence(self) -> None:
        text = """Purpose: x
User: y
Scenario: yが検索を処理する
Expected result: search
Acceptance criteria: accuracy 90%
Verification method: latencyを測定
Evidence: report"""
        payload = public_audit_payload(
            audit_requirement_relations(text),
            recorded_at=RECORDED_AT,
        )

        validate_public_audit(payload)

        self.assertEqual(payload["audit_conclusion"]["outcome"], "refuted")
        refuted = [
            item for item in payload["obligation_results"] if item["outcome"] == "refuted"
        ]
        self.assertTrue(refuted)
        self.assertTrue(
            all(
                any(effect["kind"] == "challenge" for effect in item["authority_effects"])
                for item in refuted
            )
        )

    def test_unavailable_shadow_runs_are_observational_not_effective_execution_gaps(self) -> None:
        report = audit_requirement_relations(COMPLETE, analysis_mode="shadow_all")

        payload = public_audit_payload(report, recorded_at=RECORDED_AT)
        validate_public_audit(payload)

        self.assertEqual(payload["workflow_disposition"]["status"], "pass")
        self.assertTrue(payload["analysis_runs"])
        self.assertTrue(
            all(item["execution"]["status"] == "unavailable" for item in payload["analysis_runs"])
        )
        self.assertEqual(payload["execution"]["attempted_stage_refs"], [])
        self.assertEqual(payload["execution"]["not_evaluated_stage_refs"], [])
        self.assertEqual(payload["analysis_mode"], "shadow_all")
        self.assertTrue(
            all(
                item["decision_influence"] == "shadow_observation"
                for item in payload["analysis_runs"]
            )
        )

    def test_shadow_signals_are_published_only_as_non_decisional_observations(self) -> None:
        report = audit_requirement_relations(
            COMPLETE,
            morphology_provider=PassiveMorphology(),
            dependency_provider=HostileDependencyCandidate(),
            analysis_mode="shadow_all",
        )

        payload = public_audit_payload(report, recorded_at=RECORDED_AT)
        validate_public_audit(payload)

        self.assertTrue(payload["shadow_observations"])
        self.assertTrue(
            all(
                item["decision_influence"] == "none"
                for item in payload["shadow_observations"]
            )
        )
        observation_ids = {
            item["observation_id"] for item in payload["shadow_observations"]
        }
        self.assertTrue(observation_ids.isdisjoint(payload["blocking_residual_risk_ids"]))
        self.assertFalse(
            any(
                item["risk_id"] in observation_ids
                for item in payload["assurance_claims"][0]["residual_risks"]
            )
        )
        shadow_provenance_ids = {
            record["provenance_id"]
            for run in payload["analysis_runs"]
            for record in run["provenance"]
        }
        assurance_provenance_ids = {
            record["provenance_id"]
            for record in payload["assurance_claims"][0]["provenance"]
        }
        self.assertTrue(
            shadow_provenance_ids.isdisjoint(assurance_provenance_ids)
        )
        self.assertEqual(payload["workflow_disposition"]["status"], "pass")

    def test_shadow_mode_rejects_effective_analysis_run_label(self) -> None:
        payload = public_audit_payload(
            audit_requirement_relations(COMPLETE, analysis_mode="shadow_all"),
            recorded_at=RECORDED_AT,
        )
        invalid = copy.deepcopy(payload)
        invalid["analysis_runs"][0]["decision_influence"] = "effective"

        with self.assertRaises(ValidationError):
            validate_public_audit(invalid)

    def test_shadow_candidate_cannot_be_copied_into_effective_interpretations(self) -> None:
        payload = public_audit_payload(
            audit_requirement_relations(
                COMPLETE,
                morphology_provider=PassiveMorphology(),
                dependency_provider=HostileDependencyCandidate(),
                analysis_mode="shadow_all",
            ),
            recorded_at=RECORDED_AT,
        )
        invalid = copy.deepcopy(payload)
        candidate = next(
            interpretation
            for run in invalid["analysis_runs"]
            for interpretation in run["interpretations"]
            if interpretation["status"] == "candidate"
        )
        invalid["interpretations"].append(candidate)

        with self.assertRaisesRegex(ValidationError, "shadow observation or candidate"):
            validate_public_audit(invalid)

    def test_provider_candidate_is_retained_per_obligation_without_support(self) -> None:
        text = COMPLETE.replace(
            "検索応答時間 p95 500ms 以下",
            "検索応答時間 p95 500ms 以下とは定めない",
        )
        report = audit_requirement_relations(
            text,
            morphology_provider=PassiveMorphology(),
            dependency_provider=HostileDependencyCandidate(),
        )

        payload = public_audit_payload(report, recorded_at=RECORDED_AT)
        validate_public_audit(payload)

        produces = next(
            item
            for item in payload["obligation_results"]
            if item["obligation_id"] == "func.produces"
        )
        candidate = next(
            item
            for item in produces["interpretations"]
            if item["interpretation_id"] == "interpretation.hostile-candidate"
        )
        self.assertEqual(candidate["status"], "candidate")
        self.assertEqual(candidate["supporting_evidence_refs"], [])
        self.assertTrue(
            any(
                item["entity_id"] == "hostile-dependency"
                for item in candidate["derived_from"]
            )
        )

    def test_dependency_projection_candidate_retains_rule_and_provider_lineage(self) -> None:
        text = COMPLETE.replace(
            "検索要求を処理して検索結果を返す",
            "検索要求を処理した場合は検索結果を返す",
        )
        report = audit_requirement_relations(
            text,
            morphology_provider=EmptyMorphology(),
            dependency_provider=ConditionDependency(),
        )

        payload = public_audit_payload(report, recorded_at=RECORDED_AT)
        validate_public_audit(payload)

        triggered_by = next(
            item
            for item in payload["obligation_results"]
            if item["obligation_id"] == "func.triggered_by"
        )
        candidate = next(
            item for item in triggered_by["interpretations"] if item["status"] == "candidate"
        )
        lineage_ids = {item["entity_id"] for item in candidate["derived_from"]}
        self.assertIn("projection.condition-trigger/v0", lineage_ids)
        self.assertIn("condition-dependency", lineage_ids)
        self.assertTrue(any(item.startswith("projection.") for item in lineage_ids))
        self.assertEqual(candidate["supporting_evidence_refs"], [])
        with self.assertRaisesRegex(ValueError, "absent provider receipt"):
            public_audit_payload(
                replace(report, provider_execution_receipts=()),
                recorded_at=RECORDED_AT,
            )

    def test_analyzer_stage_cannot_be_forged_as_support_actor(self) -> None:
        payload = public_audit_payload(
            audit_requirement_relations(COMPLETE),
            recorded_at=RECORDED_AT,
        )
        invalid = copy.deepcopy(payload)
        support = next(
            item for item in invalid["authority_effects"] if item["kind"] == "support"
        )
        support["actor_ref"]["entity_id"] = "stage.morphology"
        support["actor_ref"]["label_hint"] = "morphology"

        with self.assertRaisesRegex(ValidationError, "actor ceiling|forbidden"):
            validate_public_audit(invalid)

    def test_morphology_stage_cannot_be_forged_as_challenge_actor(self) -> None:
        text = COMPLETE.replace(
            "検索応答時間 p95 500ms 以下",
            "担当者によれば検索応答時間 p95 500ms 以下",
        )
        payload = public_audit_payload(
            audit_requirement_relations(text),
            recorded_at=RECORDED_AT,
        )
        invalid = copy.deepcopy(payload)
        challenge = next(
            item for item in invalid["authority_effects"] if item["kind"] == "challenge"
        )
        challenge["actor_ref"]["entity_id"] = "stage.morphology"
        challenge["actor_ref"]["label_hint"] = "morphology"

        with self.assertRaisesRegex(ValidationError, "actor ceiling|forbidden"):
            validate_public_audit(invalid)

    def test_morphology_provider_cannot_claim_challenge_right(self) -> None:
        report = audit_requirement_relations(
            COMPLETE,
            morphology_provider=PassiveMorphology(),
            analysis_mode="shadow_all",
        )
        payload = public_audit_payload(report, recorded_at=RECORDED_AT)
        invalid = copy.deepcopy(payload)
        morphology = next(
            item for item in invalid["analysis_runs"] if item["provider_kind"] == "morphology"
        )
        morphology["authority_rights"]["challenge"] = True

        with self.assertRaises(ValidationError):
            validate_public_audit(invalid)

    def test_provider_declared_candidate_only_cannot_be_forged_as_support_actor(self) -> None:
        text = COMPLETE.replace(
            "検索応答時間 p95 500ms 以下",
            "検索応答時間 p95 500ms 以下とは定めない",
        )
        payload = public_audit_payload(
            audit_requirement_relations(
                text,
                morphology_provider=PassiveMorphology(),
                dependency_provider=HostileDependencyCandidate(),
            ),
            recorded_at=RECORDED_AT,
        )
        invalid = copy.deepcopy(payload)
        support = next(
            item for item in invalid["authority_effects"] if item["kind"] == "support"
        )
        support["actor_ref"]["entity_id"] = "hostile-dependency"
        support["actor_ref"]["label_hint"] = "hostile-dependency"

        with self.assertRaisesRegex(ValidationError, "actor ceiling|forbidden"):
            validate_public_audit(invalid)

    def test_hold_effects_are_registered_in_each_enclosing_contract(self) -> None:
        text = COMPLETE.replace(
            "検索応答時間 p95 500ms 以下",
            "担当者によれば検索応答時間 p95 500ms 以下",
        )
        payload = public_audit_payload(
            audit_requirement_relations(text),
            recorded_at=RECORDED_AT,
        )
        validate_public_audit(payload)

        containers = [
            *payload["obligation_results"],
            *payload["assurance_claims"],
            *payload["decision_requests"],
        ]
        for container in containers:
            effects = {
                item["effect_id"] for item in container["authority_effects"]
            }
            holds = [
                *container.get("holds", []),
                *container.get("audit_holds", []),
            ]
            for hold in holds:
                self.assertIn(hold["applied_by"]["effect_id"], effects)
                if "released_by" in hold:
                    self.assertIn(hold["released_by"]["effect_id"], effects)

    def test_hold_reference_to_absent_effect_is_rejected(self) -> None:
        text = COMPLETE.replace(
            "検索応答時間 p95 500ms 以下",
            "担当者によれば検索応答時間 p95 500ms 以下",
        )
        payload = public_audit_payload(
            audit_requirement_relations(text),
            recorded_at=RECORDED_AT,
        )
        invalid = copy.deepcopy(payload)
        claim_hold = invalid["assurance_claims"][0]["holds"][0]
        claim_hold["applied_by"]["effect_id"] = "effect.absent"

        with self.assertRaisesRegex(ValidationError, "absent authority effect"):
            validate_public_audit(invalid)

    def test_hold_release_is_attributed_to_versioned_lifting_not_provider(self) -> None:
        text = COMPLETE.replace(
            "検索要求を処理して検索結果を返す",
            "検索要求を処理した場合は検索結果を返す",
        )
        report = audit_requirement_relations(
            text,
            morphology_provider=EmptyMorphology(),
            dependency_provider=ConditionDependency(),
        )

        payload = public_audit_payload(report, recorded_at=RECORDED_AT)
        validate_public_audit(payload)

        self.assertEqual(payload["workflow_disposition"]["status"], "pass")
        release_effects = [
            item for item in payload["authority_effects"] if item["kind"] == "hold_release"
        ]
        self.assertTrue(release_effects)
        self.assertTrue(
            all(
                item["actor_ref"]["entity_id"] == "lifting.condition-attachment/v0"
                for item in release_effects
            )
        )
        self.assertTrue(
            all(
                not run["authority_rights"]["hold_release"]
                for run in payload["analysis_runs"]
            )
        )

    def test_cross_field_span_order_is_validated(self) -> None:
        payload = public_audit_payload(
            audit_requirement_relations(COMPLETE),
            recorded_at=RECORDED_AT,
        )
        invalid = copy.deepcopy(payload)
        invalid["source_spans"][0]["start"] = invalid["source_spans"][0]["end_exclusive"] + 1

        with self.assertRaisesRegex(ValidationError, "end_exclusive"):
            validate_public_audit(invalid)


if __name__ == "__main__":
    unittest.main()
