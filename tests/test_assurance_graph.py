from __future__ import annotations

import copy
from dataclasses import replace
import unittest

from jsonschema import ValidationError

from semantic_guard.assurance_graph import (
    _attempt_from_payload,
    _finish_runtime_derivation,
    _reassessment_identity,
    build_assurance_claim_v1,
    public_assurance_claim_v1,
    validate_assurance_claim_v1,
)
from semantic_guard.provider_receipts import attempt_output_digest
from semantic_guard.engine import audit_requirement_relations
from semantic_guard.provider_receipts import QualifiedAnalyzerRegistry
from semantic_guard.public_contract import (
    public_audit_payload,
    validate_public_audit,
)

from tests.test_engine import (
    EmptyMorphologyProvider,
    QualifiedRelationDependencyProvider,
    _qualified_relation_registry,
)
from tests.test_public_contract import COMPLETE, RECORDED_AT


class AssuranceGraphTests(unittest.TestCase):
    def _claim(self):
        return public_assurance_claim_v1(
            audit_requirement_relations(COMPLETE),
            recorded_at=RECORDED_AT,
        )

    def _qualified_report(
        self,
        registry: QualifiedAnalyzerRegistry | None = None,
    ):
        text = COMPLETE.replace(
            "検索APIが検索要求を処理して検索結果を返す",
            "ここで、検索APIが検索要求を査定して検索結果を返す",
        )
        return audit_requirement_relations(
            text,
            morphology_provider=EmptyMorphologyProvider(),
            dependency_provider=QualifiedRelationDependencyProvider(),
            analysis_mode="conditional",
            analyzer_registry=registry or _qualified_relation_registry(),
        )

    def _qualified_claim(
        self,
        registry: QualifiedAnalyzerRegistry | None = None,
    ):
        return public_assurance_claim_v1(
            self._qualified_report(registry),
            recorded_at=RECORDED_AT,
        )

    @staticmethod
    def _redigested_runtime(claim, mutation):
        basis = copy.deepcopy(
            claim["runtime_derivation"]["reassessment_basis"]
        )
        basis.pop("basis_digest")
        mutation(basis)
        return _finish_runtime_derivation(basis)

    def test_generated_v1_claim_is_closed_and_replayable(self) -> None:
        claim = self._claim()
        validate_assurance_claim_v1(claim)

        self.assertEqual(claim["schema_version"], "assurance-claim/v1")
        self.assertEqual(len(claim["proof_obligations"]), 9)
        self.assertTrue(all(item["status"] == "satisfied" for item in claim["proof_obligations"]))
        self.assertTrue(claim["derivation_graph"]["nodes"])
        self.assertTrue(claim["derivation_graph"]["edges"])
        self.assertTrue(
            all(
                not values
                for name, values in claim["runtime_derivation"][
                    "reassessment_basis"
                ].items()
                if name
                in {
                    "analysis_attempts",
                    "provider_receipts",
                    "analyzer_qualifications",
                    "dependency_projections",
                    "prior_assessments",
                    "initial_unresolved_obligations",
                    "obligation_reassessments",
                }
            )
        )
        self.assertEqual(
            claim["authority_boundary"]["final_acceptance_owner"],
            "human",
        )
        self.assertIsNone(
            claim["runtime_derivation"]["reassessment_basis"]["source_text"]
        )

    def test_qualified_reassessment_requires_v1_runtime_replay_material(self) -> None:
        report = self._qualified_report()
        with self.assertRaisesRegex(ValueError, "audit-result/v0 cannot replay"):
            public_audit_payload(report, recorded_at=RECORDED_AT)

        claim = public_assurance_claim_v1(report, recorded_at=RECORDED_AT)
        validate_assurance_claim_v1(claim)
        embedded_audit = claim["basis_snapshot"]["public_audit"]
        with self.assertRaisesRegex(
            ValidationError,
            "audit-result/v0 cannot replay qualified reassessment support",
        ):
            validate_public_audit(embedded_audit)
        with self.assertRaisesRegex(
            ValidationError,
            "qualified reassessment support requires runtime derivation material",
        ):
            build_assurance_claim_v1(embedded_audit)

        replayed = build_assurance_claim_v1(
            embedded_audit,
            runtime_derivation=claim["runtime_derivation"],
        )
        self.assertEqual(replayed, claim)
        basis = claim["runtime_derivation"]["reassessment_basis"]
        self.assertTrue(
            all(
                basis[name]
                for name in (
                    "provider_receipts",
                    "analyzer_qualifications",
                    "dependency_projections",
                    "prior_assessments",
                    "initial_unresolved_obligations",
                    "obligation_reassessments",
                )
            )
        )
        node_kinds = {
            item["node_kind"] for item in claim["derivation_graph"]["nodes"]
        }
        self.assertTrue(
            {
                "provider_receipt",
                "analyzer_qualification",
                "dependency_projection",
                "prior_assessment",
                "unresolved_route",
                "obligation_reassessment",
            }.issubset(node_kinds)
        )
        edge_kinds = {
            item["edge_kind"] for item in claim["derivation_graph"]["edges"]
        }
        self.assertTrue(
            {
                "qualifies_execution",
                "records_execution",
                "projects_dependency",
                "reassesses_prior",
                "resolves_unresolved",
                "derives_support",
                "records_runtime_derivation",
                "binds_runtime_derivation",
            }.issubset(edge_kinds)
        )

    def test_runtime_basis_omissions_are_rejected_after_redigesting(self) -> None:
        claim = self._qualified_claim()
        embedded_audit = claim["basis_snapshot"]["public_audit"]
        for collection in (
            "provider_receipts",
            "analyzer_qualifications",
            "dependency_projections",
            "prior_assessments",
            "initial_unresolved_obligations",
            "obligation_reassessments",
        ):
            with self.subTest(collection=collection):
                runtime = self._redigested_runtime(
                    claim,
                    lambda basis, name=collection: basis.__setitem__(name, []),
                )
                with self.assertRaisesRegex(
                    ValidationError,
                    "closed non-empty runtime basis",
                ):
                    build_assurance_claim_v1(
                        embedded_audit,
                        runtime_derivation=runtime,
                    )

    def test_runtime_basis_substitutions_are_rejected_after_redigesting(self) -> None:
        claim = self._qualified_claim()
        embedded_audit = claim["basis_snapshot"]["public_audit"]

        def substitute_receipt(basis):
            basis["provider_receipts"][0]["provider_version"] += "-forged"

        def substitute_qualification(basis):
            basis["analyzer_qualifications"][0][
                "qualification_basis"
            ] += " forged"

        def substitute_prior(basis):
            basis["prior_assessments"][0]["basis"].append("forged")

        def substitute_unresolved(basis):
            basis["initial_unresolved_obligations"][0][
                "direct_reasons"
            ].append("forged")

        substitutions = {
            "receipt": substitute_receipt,
            "qualification": substitute_qualification,
            "prior": substitute_prior,
            "unresolved": substitute_unresolved,
        }
        for label, mutation in substitutions.items():
            with self.subTest(substitution=label):
                runtime = self._redigested_runtime(claim, mutation)
                with self.assertRaises(ValidationError):
                    build_assurance_claim_v1(
                        embedded_audit,
                        runtime_derivation=runtime,
                    )

        def substitute_policy(basis):
            reassessment = basis["obligation_reassessments"][0]
            reassessment["policy_rule_id"] = "obligation-reassessment-policy/forged"
            reassessment["resolved_by"] = "obligation-reassessment-policy/forged"
            reassessment["reassessment_id"] = _reassessment_identity(reassessment)

        changed_policy_runtime = self._redigested_runtime(
            claim,
            substitute_policy,
        )
        self.assertNotEqual(
            changed_policy_runtime["runtime_derivation_digest"],
            claim["runtime_derivation"]["runtime_derivation_digest"],
        )
        with self.assertRaisesRegex(
            ValidationError,
            "policy or identity mismatch",
        ):
            build_assurance_claim_v1(
                embedded_audit,
                runtime_derivation=changed_policy_runtime,
            )

    def test_qualification_change_rekeys_the_complete_claim(self) -> None:
        original_registry = _qualified_relation_registry()
        changed_registry = QualifiedAnalyzerRegistry(
            tuple(
                replace(
                    item,
                    qualification_basis=item.qualification_basis + " revised",
                )
                for item in original_registry.records
            )
        )
        original = self._qualified_claim(original_registry)
        changed = self._qualified_claim(changed_registry)

        self.assertNotEqual(original["claim_id"], changed["claim_id"])
        self.assertNotEqual(
            original["runtime_derivation"]["runtime_derivation_digest"],
            changed["runtime_derivation"]["runtime_derivation_digest"],
        )
        validate_assurance_claim_v1(changed)

    def test_embedded_source_and_raw_attempt_are_required_for_engine_replay(self) -> None:
        claim = self._qualified_claim()
        graph = claim["derivation_graph"]
        self.assertIn(
            "runtime_source", {item["node_kind"] for item in graph["nodes"]}
        )
        self.assertIn(
            "analysis_attempt", {item["node_kind"] for item in graph["nodes"]}
        )
        self.assertIn(
            "materializes_receipt", {item["edge_kind"] for item in graph["edges"]}
        )

        changed_source = self._redigested_runtime(
            claim,
            lambda basis: basis.__setitem__(
                "source_text", basis["source_text"] + "\nsubstituted"
            ),
        )
        with self.assertRaisesRegex(ValidationError, "source text digest mismatch"):
            build_assurance_claim_v1(
                claim["basis_snapshot"]["public_audit"],
                runtime_derivation=changed_source,
            )

        def remove_dependency_attempt(basis):
            basis["analysis_attempts"] = [
                item
                for item in basis["analysis_attempts"]
                if item["stage"] != "dependency_parse"
            ]

        missing_attempt = self._redigested_runtime(claim, remove_dependency_attempt)
        with self.assertRaisesRegex(ValidationError, "not bound to one embedded"):
            build_assurance_claim_v1(
                claim["basis_snapshot"]["public_audit"],
                runtime_derivation=missing_attempt,
            )

        def substitute_attempt_output(basis):
            attempt = next(
                item
                for item in basis["analysis_attempts"]
                if item["stage"] == "dependency_parse"
            )
            attempt["relations"][0]["rationale"] += "; substituted"
            output_digest = attempt_output_digest(_attempt_from_payload(attempt))
            attempt["output_digest"] = output_digest
            attempt["attempt_id"] = "analysis-attempt." + output_digest[7:]

        substituted_attempt = self._redigested_runtime(
            claim, substitute_attempt_output
        )
        with self.assertRaisesRegex(ValidationError, "receipt output is not bound"):
            build_assurance_claim_v1(
                claim["basis_snapshot"]["public_audit"],
                runtime_derivation=substituted_attempt,
            )

    def test_unqualified_analyzer_cannot_create_runtime_support(self) -> None:
        text = COMPLETE.replace(
            "検索APIが検索要求を処理して検索結果を返す",
            "ここで、検索APIが検索要求を査定して検索結果を返す",
        )
        report = audit_requirement_relations(
            text,
            morphology_provider=EmptyMorphologyProvider(),
            dependency_provider=QualifiedRelationDependencyProvider(),
            analysis_mode="conditional",
        )
        public_audit = public_audit_payload(report, recorded_at=RECORDED_AT)
        validate_public_audit(public_audit)
        claim = public_assurance_claim_v1(report, recorded_at=RECORDED_AT)
        validate_assurance_claim_v1(claim)

        basis = claim["runtime_derivation"]["reassessment_basis"]
        self.assertFalse(basis["obligation_reassessments"])
        self.assertFalse(
            any(
                effect["kind"] == "support"
                and effect["actor_ref"]["entity_id"]
                == "obligation-reassessment-policy/v0"
                for effect in public_audit["authority_effects"]
            )
        )

    def test_subject_proposition_rule_and_evidence_substitution_are_rejected(self) -> None:
        mutations = []

        wrong_subject = self._claim()
        wrong_subject["base_claim"]["subject_ref"] = {
            "reference_kind": "ref",
            "entity_id": "subject.other",
            "label_hint": "other",
        }
        mutations.append(wrong_subject)

        wrong_proposition = self._claim()
        wrong_proposition["base_claim"]["proposition"] = "Unrelated proposition."
        mutations.append(wrong_proposition)

        empty_rules = self._claim()
        empty_rules["base_claim"]["rules"] = []
        mutations.append(empty_rules)

        wrong_evidence = self._claim()
        wrong_evidence["base_claim"]["supporting_evidence_refs"] = [
            {
                "reference_kind": "ref",
                "entity_id": "evidence.other",
                "label_hint": "other",
            }
        ]
        mutations.append(wrong_evidence)

        for claim in mutations:
            with self.subTest(mutation=claim["base_claim"]["claim_id"]):
                with self.assertRaises(ValidationError):
                    validate_assurance_claim_v1(claim)

    def test_unresolved_evidence_endpoint_and_cycle_are_rejected(self) -> None:
        unresolved = self._claim()
        unresolved["derivation_graph"]["edges"][0]["from_node_ref"]["entity_id"] = (
            "derivation-node.absent"
        )
        with self.assertRaisesRegex(ValidationError, "unresolved node endpoint"):
            validate_assurance_claim_v1(unresolved)

        cyclic = self._claim()
        first = cyclic["derivation_graph"]["edges"][0]
        root = cyclic["derivation_graph"]["root_node_ref"]
        first["from_node_ref"] = copy.deepcopy(root)
        first["to_node_ref"] = copy.deepcopy(root)
        with self.assertRaisesRegex(ValidationError, "cycle"):
            validate_assurance_claim_v1(cyclic)

    def test_duplicate_evidence_accounting_and_unfulfilled_proof_are_rejected(self) -> None:
        duplicate = self._claim()
        evidence = next(
            item
            for item in duplicate["derivation_graph"]["nodes"]
            if item["node_kind"] == "evidence"
        )
        duplicate["derivation_graph"]["nodes"].append(copy.deepcopy(evidence))
        with self.assertRaisesRegex(ValidationError, "duplicate node"):
            validate_assurance_claim_v1(duplicate)

        unfulfilled = self._claim()
        unfulfilled["proof_obligations"][0]["status"] = "undetermined"
        with self.assertRaises(ValidationError):
            validate_assurance_claim_v1(unfulfilled)

    def test_profile_and_limitation_substitution_are_rejected(self) -> None:
        wrong_profile = self._claim()
        wrong_profile["claim_profile_ref"]["entity_id"] = "profile.other"
        with self.assertRaisesRegex(ValidationError, "claim profile"):
            validate_assurance_claim_v1(wrong_profile)

        weakened_limitations = self._claim()
        weakened_limitations["limitations"] = ["Everything is proved."]
        with self.assertRaisesRegex(ValidationError, "limitations"):
            validate_assurance_claim_v1(weakened_limitations)


if __name__ == "__main__":
    unittest.main()
