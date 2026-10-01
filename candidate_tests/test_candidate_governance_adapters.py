from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest

from jsonschema import Draft202012Validator

from semantic_guard_vnext.candidate_governance_adapters import (
    CandidateGovernanceAdapterError,
    DEFAULT_H1_SOURCE_REF,
    DEFAULT_H2_SOURCE_REF,
    adapt_engineering_rule_pack_bytes,
    adapt_engineering_rule_pack_candidate,
    adapt_engineering_rule_pack_document,
    adapt_lifecycle_profile_registry_bytes,
    adapt_lifecycle_profile_registry_candidate,
    adapt_lifecycle_profile_registry_document,
    candidate_governance_adapter_schema,
    load_default_engineering_rule_pack_candidate,
    load_default_lifecycle_profile_registry_candidate,
    validate_engineering_rule_pack_adapter_result,
    validate_lifecycle_profile_adapter_result,
)
from semantic_guard_vnext.engineering_rule_governance import sha256_bytes, sha256_digest
from semantic_guard_vnext.lifecycle_profiles import seal_lifecycle_profile_registry


ROOT = Path(__file__).resolve().parents[1] / "src" / "semantic_guard_vnext"
H1_CANDIDATE = ROOT / "validation/engineering-rule-pack.candidate.json"
H2_CANDIDATE = ROOT / "validation/lifecycle-profile-registry.candidate.json"


def canonical_ref(document: dict, label: str) -> dict:
    content = json.dumps(
        document,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return {
        "record_id": f"candidate.{label}",
        "locator": f"urn:test:candidate:{label}",
        "content_digest": sha256_bytes(content),
    }


def subject_ref(label: str) -> dict:
    return {
        "record_id": f"subject.{label}",
        "locator": f"urn:test:subject:{label}",
        "content_digest": sha256_digest({"subject": label}),
    }


class CandidateGovernanceAdapterTests(unittest.TestCase):
    def h1_document(self) -> dict:
        return json.loads(H1_CANDIDATE.read_text(encoding="utf-8"))

    def h2_document(self) -> dict:
        return json.loads(H2_CANDIDATE.read_text(encoding="utf-8"))

    def test_adapter_schema_is_draft_2020_12_valid(self) -> None:
        Draft202012Validator.check_schema(candidate_governance_adapter_schema())

    def test_default_candidate_loaders_return_pinned_independent_copies(self) -> None:
        h1_document, h1_bytes, h1_ref = load_default_engineering_rule_pack_candidate()
        h2_document, h2_bytes, h2_ref = (
            load_default_lifecycle_profile_registry_candidate()
        )
        self.assertEqual(h1_ref, DEFAULT_H1_SOURCE_REF)
        self.assertEqual(h2_ref, DEFAULT_H2_SOURCE_REF)
        self.assertEqual(sha256_bytes(h1_bytes), h1_ref["content_digest"])
        self.assertEqual(sha256_bytes(h2_bytes), h2_ref["content_digest"])
        self.assertEqual(json.loads(h1_bytes), h1_document)
        self.assertEqual(json.loads(h2_bytes), h2_document)
        h1_document["rules"].clear()
        h2_document["profiles"].clear()
        fresh_h1, _, _ = load_default_engineering_rule_pack_candidate()
        fresh_h2, _, _ = load_default_lifecycle_profile_registry_candidate()
        self.assertEqual(len(fresh_h1["rules"]), 11)
        self.assertEqual(len(fresh_h2["profiles"]), 10)

    def test_real_h1_candidate_reaches_governed_runtime_unresolved(self) -> None:
        obligation_digest = sha256_digest({"assessment": "public-request"})
        result = adapt_engineering_rule_pack_candidate(
            obligation_assessment_digest=obligation_digest,
            authority_source_ids=["authority.request", "authority.profile"],
        )
        bundle = result["governance_bundle"]
        resolution = bundle["runtime_resolution"]
        self.assertEqual(len(result["source_entry_refs"]), 5)
        self.assertEqual(len(result["rule_mappings"]), 11)
        self.assertEqual(len(bundle["rule_bases"]), 11)
        self.assertEqual(len(bundle["implementation_bindings"]), 11)
        self.assertEqual(len(bundle["human_decisions"]), 12)
        self.assertEqual(
            bundle["runtime_resolution"]["runtime_request"][
                "obligation_assessment_digest"
            ],
            obligation_digest,
        )
        self.assertEqual(
            result["authority_source_ids"],
            ["authority.profile", "authority.request"],
        )
        self.assertEqual(resolution["pack_resolution"]["status"], "unresolved")
        self.assertEqual(
            resolution["pack_resolution"]["formal_verdict_authority"], "none"
        )
        self.assertEqual(bundle["h1_gate_view"]["human_decision"], "pending")
        self.assertEqual(bundle["h1_gate_view"]["verdict_authority"], "none")
        self.assertEqual(result["formal_authority"], "none")
        self.assertTrue(
            all(
                mapping["input_rule_ref"]["record_id"].endswith(".v0")
                and mapping["basis_ref"]["rule_version"] == "v1"
                for mapping in result["rule_mappings"]
            )
        )
        self.assertTrue(
            all(
                binding["implementation_status"] == "partially_implemented"
                for binding in bundle["implementation_bindings"]
            )
        )
        self.assertTrue(
            all(
                source["binding_status"] == "unverified"
                for basis in bundle["rule_bases"]
                for source in basis["source_bindings"]
            )
        )

    def test_h1_document_source_ref_is_content_binding_not_authority(self) -> None:
        document = self.h1_document()
        document["rules"][0]["engineering_proposition"] += " Candidate revision."
        result = adapt_engineering_rule_pack_document(
            document, source_ref=canonical_ref(document, "h1-revision")
        )
        self.assertEqual(result["source_transport"]["authenticity_state"], "unresolved")
        self.assertEqual(result["source_transport"]["trust_effect"], "none")
        self.assertEqual(result["formal_authority"], "none")
        self.assertEqual(
            result["governance_bundle"]["h1_gate_view"]["human_decision"],
            "pending",
        )

    def test_h1_document_rejects_wrong_canonical_ref(self) -> None:
        document = self.h1_document()
        reference = canonical_ref(document, "h1")
        reference["content_digest"] = sha256_digest("wrong")
        with self.assertRaisesRegex(
            CandidateGovernanceAdapterError, "canonical source_ref"
        ):
            adapt_engineering_rule_pack_document(document, source_ref=reference)

    def test_h1_bytes_reject_content_substitution_against_old_ref(self) -> None:
        content = H1_CANDIDATE.read_bytes()
        document = json.loads(content)
        document["rules"][0]["interpretation"] += " substituted"
        changed = json.dumps(document, ensure_ascii=False).encode("utf-8")
        with self.assertRaisesRegex(
            CandidateGovernanceAdapterError, "expected source_ref"
        ):
            adapt_engineering_rule_pack_bytes(changed, source_ref=DEFAULT_H1_SOURCE_REF)

    def test_h1_near_rule_id_fails_even_with_new_content_ref(self) -> None:
        document = self.h1_document()
        document["rules"][0]["rule_id"] += "-near"
        with self.assertRaisesRegex(
            CandidateGovernanceAdapterError,
            "engineering-rule identity",
        ):
            adapt_engineering_rule_pack_document(
                document, source_ref=canonical_ref(document, "h1-near-id")
            )

    def test_h1_duplicate_and_missing_entries_fail_closed(self) -> None:
        duplicate = self.h1_document()
        duplicate["rules"][1] = copy.deepcopy(duplicate["rules"][0])
        with self.assertRaises(CandidateGovernanceAdapterError):
            adapt_engineering_rule_pack_document(
                duplicate, source_ref=canonical_ref(duplicate, "h1-duplicate")
            )
        missing = self.h1_document()
        missing["sources"].pop()
        with self.assertRaises(CandidateGovernanceAdapterError):
            adapt_engineering_rule_pack_document(
                missing, source_ref=canonical_ref(missing, "h1-missing")
            )

    def test_h1_adapter_result_tamper_fails_replay(self) -> None:
        document = self.h1_document()
        result = adapt_engineering_rule_pack_document(
            document, source_ref=canonical_ref(document, "h1-replay")
        )
        result["rule_mappings"][0]["unresolved_codes"].pop()
        result["rule_mappings"][0]["conversion_digest"] = sha256_digest(
            {
                key: value
                for key, value in result["rule_mappings"][0].items()
                if key != "conversion_digest"
            }
        )
        result["adapter_digest"] = sha256_digest(
            {key: value for key, value in result.items() if key != "adapter_digest"}
        )
        with self.assertRaisesRegex(CandidateGovernanceAdapterError, "does not replay"):
            validate_engineering_rule_pack_adapter_result(
                result, source_document=document
            )

    def test_custom_path_requires_expected_ref(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".json") as handle:
            handle.write(H1_CANDIDATE.read_bytes())
            handle.flush()
            with self.assertRaisesRegex(
                CandidateGovernanceAdapterError, "requires an expected_source_ref"
            ):
                adapt_engineering_rule_pack_candidate(handle.name)

    def test_real_h2_candidate_reaches_runtime_with_exact_rule_denominator(
        self,
    ) -> None:
        subject = subject_ref("real-h2")
        result = adapt_lifecycle_profile_registry_candidate(subject_scope_ref=subject)
        resolution = result["runtime_resolution"]
        self.assertEqual(len(result["profile_mappings"]), 10)
        self.assertEqual(len(result["governed_profiles"]), 10)
        self.assertEqual(len(result["runtime_rule_bindings"]), 10)
        self.assertEqual(len(resolution["required_rule_denominator"]), 10)
        self.assertEqual(len(resolution["supplied_rule_bindings"]), 10)
        self.assertEqual(
            {
                (item["rule_id"], item["rule_version"])
                for item in resolution["required_rule_denominator"]
            },
            {
                (item["rule_id"], item["rule_version"])
                for item in resolution["supplied_rule_bindings"]
            },
        )
        self.assertNotIn(
            "runtime_rule_not_required",
            {
                reason
                for item in resolution["resolution_items"]
                for reason in item["reasons"]
            },
        )
        self.assertEqual(result["subject_scope_ref"], subject)
        self.assertEqual(result["tailoring"]["subject_scope_ref"], subject)
        self.assertEqual(resolution["subject_scope_ref"], subject)
        self.assertEqual(resolution["resolution_state"], "unresolved")
        self.assertGreater(resolution["blocking_unresolved_count"], 0)
        self.assertEqual(resolution["formal_authority"], "none")
        self.assertEqual(
            result["stage_registry"]["reported_adoption_status"], "candidate"
        )
        self.assertEqual(result["tailoring"]["reported_adoption_status"], "candidate")
        self.assertEqual(result["formal_authority"], "none")
        self.assertTrue(
            all(
                profile["reported_adoption_status"] == "candidate"
                and profile["human_adoption_ref"] is None
                for profile in result["governed_profiles"]
            )
        )

    def test_h2_document_source_ref_and_subject_do_not_grant_authority(self) -> None:
        document = self.h2_document()
        subject = subject_ref("document-h2")
        result = adapt_lifecycle_profile_registry_document(
            document,
            source_ref=canonical_ref(document, "h2-document"),
            subject_scope_ref=subject,
        )
        self.assertEqual(result["source_transport"]["authenticity_state"], "unresolved")
        self.assertEqual(result["source_transport"]["trust_effect"], "none")
        self.assertEqual(result["runtime_resolution"]["formal_authority"], "none")
        self.assertEqual(result["runtime_resolution"]["resolution_state"], "unresolved")

    def test_h2_bytes_reject_content_substitution_against_old_ref(self) -> None:
        document = self.h2_document()
        document["profiles"][0]["purpose"] += " substituted"
        changed = json.dumps(document, ensure_ascii=False).encode("utf-8")
        with self.assertRaisesRegex(
            CandidateGovernanceAdapterError, "expected source_ref"
        ):
            adapt_lifecycle_profile_registry_bytes(
                changed, source_ref=DEFAULT_H2_SOURCE_REF
            )

    def test_h2_near_profile_id_fails_after_digest_reseal(self) -> None:
        document = self.h2_document()
        document["profiles"][0]["profile_id"] = "lifecycle-profile.requests"
        resealed = seal_lifecycle_profile_registry(document)
        with self.assertRaisesRegex(
            CandidateGovernanceAdapterError, "profile_id_stage_mismatch"
        ):
            adapt_lifecycle_profile_registry_document(
                resealed, source_ref=canonical_ref(resealed, "h2-near-id")
            )

    def test_h2_duplicate_and_missing_profiles_fail_closed(self) -> None:
        duplicate = self.h2_document()
        duplicate["profiles"][1] = copy.deepcopy(duplicate["profiles"][0])
        duplicate = seal_lifecycle_profile_registry(duplicate)
        with self.assertRaises(CandidateGovernanceAdapterError):
            adapt_lifecycle_profile_registry_document(
                duplicate, source_ref=canonical_ref(duplicate, "h2-duplicate")
            )
        missing = self.h2_document()
        missing["profiles"].pop()
        missing = seal_lifecycle_profile_registry(missing)
        with self.assertRaises(CandidateGovernanceAdapterError):
            adapt_lifecycle_profile_registry_document(
                missing, source_ref=canonical_ref(missing, "h2-missing")
            )

    def test_h2_adapter_result_tamper_fails_replay(self) -> None:
        document = self.h2_document()
        result = adapt_lifecycle_profile_registry_document(
            document, source_ref=canonical_ref(document, "h2-replay")
        )
        result["profile_mappings"][0]["implementation_state"] = (
            "unresolved_no_implementation_binding"
        )
        result["profile_mappings"][0]["unresolved_codes"].pop()
        result["profile_mappings"][0]["conversion_digest"] = sha256_digest(
            {
                key: value
                for key, value in result["profile_mappings"][0].items()
                if key != "conversion_digest"
            }
        )
        result["adapter_digest"] = sha256_digest(
            {key: value for key, value in result.items() if key != "adapter_digest"}
        )
        with self.assertRaisesRegex(CandidateGovernanceAdapterError, "does not replay"):
            validate_lifecycle_profile_adapter_result(result, source_document=document)


if __name__ == "__main__":
    unittest.main()
