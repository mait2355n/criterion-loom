from __future__ import annotations

import inspect
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from semantic_guard_vnext.legacy_runner import MAX_REQUIREMENT_INPUT_BYTES
from semantic_guard_vnext.governance_materials import (
    default_candidate_governance_materials,
)
from semantic_guard_vnext.mcp_server import (
    LEGACY_SHADOW_ENABLE_ENV,
    LEGACY_SHADOW_ROOT_ENV,
    _fixed_legacy_shadow_paths,
    audit_requirement_relations_service,
    semantic_guard_vnext_constitution_resource,
    semantic_guard_vnext_schema_resource,
    semantic_guard_vnext_schema_tool,
    shadow_compare_legacy_vnext_tool,
)


COMPLETE = """Purpose: 検索APIが検索結果を p95 500ms以内で返す
User: 検索API
Scenario: 検索APIが検索要求を処理して検索結果を返す
Expected result: 検索結果を p95 500ms以内で返す
Acceptance criteria: 検索応答時間 p95 500ms 以下
Verification method: 検索結果の検索応答時間を benchmark で測定する
Evidence: 検索結果の検索応答時間 benchmark report"""

REPORTED = COMPLETE.replace(
    "検索応答時間 p95 500ms 以下",
    "担当者によれば検索応答時間 p95 500ms 以下",
    1,
)


def llm_bundle(text: str) -> dict:
    method_start = text.index("検索結果の検索応答時間を benchmark")
    criterion_start = text.index("担当者によれば検索応答時間")
    return {
        "schema_version": "semantic-guard-vnext-llm-candidates/v0",
        "bundle_id": "bundle.mcp.fixture",
        "model_id": "calling-agent",
        "model_version": "fixture-1",
        "prompt_profile_id": "requirement-relations",
        "prompt_profile_version": "v0",
        "source_digest": {
            "algorithm": "sha256",
            "value": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        },
        "relations": [
            {
                "relation_kind": "verifies",
                "from_span": {
                    "start": method_start,
                    "end": method_start
                    + len("検索結果の検索応答時間を benchmark で測定する"),
                    "role": "verification_method",
                },
                "to_span": {
                    "start": criterion_start,
                    "end": criterion_start
                    + len("担当者によれば検索応答時間 p95 500ms 以下"),
                    "role": "acceptance_criteria",
                },
                "interpretation_id": "interpretation.mcp.fixture",
                "rationale": "Caller candidate only.",
            }
        ],
        "scopes": [],
        "diagnostics": [],
    }


class McpServiceTests(unittest.TestCase):
    def test_public_service_safe_default_requires_analysis_providers(self) -> None:
        payload = audit_requirement_relations_service(COMPLETE)

        self.assertEqual(payload["schema_version"], "governed-requirement-audit/v1")
        self.assertEqual(
            payload["legacy_analysis_observation"]["analysis_mode"], "assurance"
        )
        self.assertEqual(
            payload["assurance_assessment"]["workflow_disposition"], "block"
        )
        governance = payload["governance_material_assessment"]
        h1 = governance["engineering_rule_governance"]
        h2 = governance["lifecycle_profile_governance"]
        self.assertEqual(h1["input_status"], "candidate_assessed")
        self.assertEqual(h1["binding_status"], "matched_candidate")
        self.assertEqual(len(h1["validated_record"]["rule_mappings"]), 11)
        self.assertEqual(h2["input_status"], "candidate_assessed")
        self.assertEqual(h2["binding_status"], "matched_candidate")
        self.assertEqual(len(h2["validated_record"]["profile_mappings"]), 10)
        self.assertEqual(
            payload["governance_resolution"]["observation_binding_status"],
            "matched",
        )
        self.assertEqual(
            payload["governance_resolution"]["h1_verdict_authority"], "none"
        )
        self.assertFalse(governance["positive_assurance"])
        self.assertEqual(
            set(
                payload["legacy_analysis_observation"]["required_provider_failure_ids"]
            ),
            {
                "morphology:not_configured",
                "dependency_parse:not_configured",
                "llm_candidate:not_configured",
            },
        )
        self.assertEqual(
            payload["authority_boundary"]["final_acceptance_owner"], "human"
        )
        self.assertEqual(
            [
                item["stage"]
                for item in payload["legacy_analysis_material"]["analysis_attempts"]
            ],
            [
                "structured_parse",
                "direct_rules",
                "morphology",
                "dependency_parse",
                "llm_candidate",
            ],
        )

    def test_service_direct_short_circuit_is_explicit(self) -> None:
        payload = audit_requirement_relations_service(
            COMPLETE,
            analysis_mode="conditional",
        )

        self.assertEqual(
            payload["legacy_analysis_observation"]["observed_workflow_disposition"],
            "pass",
        )
        self.assertEqual(
            payload["assurance_assessment"]["workflow_disposition"], "block"
        )

    def test_service_reports_candidate_material_substitution_as_rejected(self) -> None:
        materials = default_candidate_governance_materials()
        materials["engineering_rule_pack_candidate"]["document"]["rules"][0][
            "engineering_proposition"
        ] = "substituted through MCP"
        payload = audit_requirement_relations_service(
            COMPLETE,
            governance_materials=materials,
        )

        axis = payload["governance_material_assessment"]["engineering_rule_governance"]
        self.assertEqual(axis["input_status"], "rejected")
        self.assertEqual(axis["binding_status"], "invalid")
        self.assertEqual(
            payload["governance_resolution"]["observation_binding_status"],
            "not_bound",
        )
        self.assertEqual(
            payload["assurance_assessment"]["workflow_disposition"], "block"
        )

    def test_field_material_type_errors_are_returned_as_rejected(self) -> None:
        for value in (None, {}, 1, False, "invalid", []):
            with self.subTest(value=value):
                payload = audit_requirement_relations_service(
                    COMPLETE, governance_materials={"field_performance_bundle": value}
                )

                material = payload["governance_material_assessment"]
                axis = material["field_performance_evidence"]
                self.assertEqual(axis["input_material"], value)
                self.assertEqual(
                    axis["input_status"], "missing" if value is None else "rejected"
                )
                self.assertEqual(
                    axis["binding_status"], "not_bound" if value is None else "invalid"
                )
                self.assertIsNone(axis["validated_record"])
                self.assertEqual(material["formal_authority"], "none")
                self.assertFalse(material["positive_assurance"])
                self.assertEqual(
                    payload["assurance_assessment"]["workflow_disposition"], "block"
                )

    def test_service_does_not_attach_governance_material_to_legacy_output(self) -> None:
        with self.assertRaisesRegex(ValueError, "governance_materials"):
            audit_requirement_relations_service(
                COMPLETE,
                governance_materials={},
                output="legacy-public-v0",
            )

    def test_invalid_provider_choice_is_not_silently_ignored(self) -> None:
        with self.assertRaisesRegex(ValueError, "morphology must be"):
            audit_requirement_relations_service(COMPLETE, morphology="unknown")

    def test_schema_tool_is_closed_to_known_names(self) -> None:
        payload = semantic_guard_vnext_schema_tool("audit-result")
        self.assertFalse(payload["unevaluatedProperties"])

        v1 = semantic_guard_vnext_schema_tool("assurance-claim-v1")
        self.assertEqual(
            v1["properties"]["schema_version"]["const"], "assurance-claim/v1"
        )

        sidecar = semantic_guard_vnext_schema_tool("state-assessment")
        self.assertEqual(
            sidecar["properties"]["schema_version"]["const"],
            "state-assessment/v2",
        )

        with self.assertRaisesRegex(ValueError, "unknown schema"):
            semantic_guard_vnext_schema_tool("arbitrary-path")

    def test_service_legacy_assurance_v1_is_opt_in_and_replayable(self) -> None:
        payload = audit_requirement_relations_service(
            COMPLETE,
            analysis_mode="conditional",
            output="legacy-assurance-v1",
        )

        self.assertEqual(
            payload["schema_version"], "legacy-ungoverned-output-envelope/v0"
        )
        self.assertEqual(payload["governance_status"], "legacy_ungoverned")
        self.assertEqual(payload["authority_scope"], "observation_only")
        self.assertEqual(payload["formal_authority"], "none")
        self.assertFalse(payload["positive_assurance"])
        legacy = payload["legacy_payload"]
        self.assertEqual(legacy["schema_version"], "assurance-claim/v1")
        self.assertTrue(legacy["proof_obligations"])
        self.assertEqual(
            legacy["authority_boundary"]["final_acceptance_owner"], "human"
        )

    def test_service_legacy_internal_debug_is_nested_and_self_describing(
        self,
    ) -> None:
        payload = audit_requirement_relations_service(
            COMPLETE,
            analysis_mode="conditional",
            output="legacy-internal-debug-v0",
        )

        stored = json.loads(json.dumps(payload, ensure_ascii=False))
        self.assertEqual(stored["output_format"], "legacy-internal-debug-v0")
        self.assertEqual(stored["governance_status"], "legacy_ungoverned")
        self.assertEqual(stored["authority_scope"], "observation_only")
        self.assertEqual(stored["formal_authority"], "none")
        self.assertFalse(stored["positive_assurance"])
        self.assertEqual(stored["legacy_payload"]["result"]["workflow"], "pass")

    def test_unqualified_assurance_output_name_is_not_public(self) -> None:
        with self.assertRaisesRegex(ValueError, "legacy-assurance-v1"):
            audit_requirement_relations_service(
                COMPLETE,
                analysis_mode="conditional",
                output="assurance-v1",
            )

    def test_public_service_rejects_oversized_input(self) -> None:
        with self.assertRaisesRegex(ValueError, "exceeds"):
            audit_requirement_relations_service("a" * (MAX_REQUIREMENT_INPUT_BYTES + 1))

    def test_shadow_tool_does_not_accept_caller_selected_paths(self) -> None:
        parameters = inspect.signature(shadow_compare_legacy_vnext_tool).parameters

        self.assertNotIn("legacy_root", parameters)
        self.assertNotIn("baseline_manifest", parameters)
        self.assertNotIn("legacy_adapter", parameters)

    def test_shadow_paths_are_disabled_by_default(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "disabled"):
            _fixed_legacy_shadow_paths({})

    def test_shadow_root_must_be_operator_supplied_absolute_path(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "absolute"):
            _fixed_legacy_shadow_paths(
                {
                    LEGACY_SHADOW_ENABLE_ENV: "1",
                    LEGACY_SHADOW_ROOT_ENV: "relative/path",
                }
            )

    def test_shadow_paths_are_fixed_under_operator_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline = root / "vnext" / "migration" / "legacy-baseline-2026-07-16.json"
            adapter = root / "vnext" / "scripts" / "legacy_request_adapter.py"
            interpreter = root / ".venv" / "bin" / "python"
            for path in (baseline, adapter, interpreter):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("placeholder", encoding="utf-8")
            baseline.write_bytes(
                (
                    Path(__file__).resolve().parent
                    / "fixtures"
                    / "legacy-baseline-2026-07-16.json"
                ).read_bytes()
            )
            interpreter.chmod(0o755)

            resolved = _fixed_legacy_shadow_paths(
                {
                    LEGACY_SHADOW_ENABLE_ENV: "1",
                    LEGACY_SHADOW_ROOT_ENV: str(root),
                }
            )

            self.assertEqual(
                resolved, (root.resolve(), baseline.resolve(), adapter.resolve())
            )

    def test_shadow_manifest_is_pinned_by_server_digest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline = root / "vnext" / "migration" / "legacy-baseline-2026-07-16.json"
            adapter = root / "vnext" / "scripts" / "legacy_request_adapter.py"
            interpreter = root / ".venv" / "bin" / "python"
            for path in (baseline, adapter, interpreter):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("placeholder", encoding="utf-8")
            interpreter.chmod(0o755)

            with self.assertRaisesRegex(RuntimeError, "server-pinned"):
                _fixed_legacy_shadow_paths(
                    {
                        LEGACY_SHADOW_ENABLE_ENV: "1",
                        LEGACY_SHADOW_ROOT_ENV: str(root),
                    }
                )

    def test_contract_resources_are_read_only_serializations(self) -> None:
        schema = json.loads(semantic_guard_vnext_schema_resource("audit-result"))
        constitution = semantic_guard_vnext_constitution_resource()

        self.assertEqual(
            schema["$id"],
            "https://semantic-guard.local/vnext/schemas/audit-result.schema.json",
        )
        self.assertIn("semantic-guard-vnext-constitution", constitution)

    def test_service_accepts_digest_bound_caller_llm_candidates(self) -> None:
        payload = audit_requirement_relations_service(
            REPORTED,
            llm_candidate_bundle=llm_bundle(REPORTED),
            output="legacy-public-v0",
        )

        stored = json.loads(json.dumps(payload, ensure_ascii=False))
        self.assertEqual(stored["governance_status"], "legacy_ungoverned")
        self.assertEqual(stored["authority_scope"], "observation_only")
        self.assertEqual(stored["formal_authority"], "none")
        self.assertFalse(stored["positive_assurance"])
        legacy = payload["legacy_payload"]
        llm_run = next(
            item for item in legacy["analysis_runs"] if item["provider_kind"] == "llm"
        )
        self.assertEqual(llm_run["execution"]["status"], "complete")
        self.assertFalse(llm_run["authority_rights"]["support"])
        self.assertFalse(llm_run["authority_rights"]["hold_release"])

    def test_llm_bundle_for_another_source_fails_as_provider_observation(self) -> None:
        bundle = llm_bundle(REPORTED)
        bundle["source_digest"]["value"] = hashlib.sha256(
            "別の原文".encode("utf-8")
        ).hexdigest()
        payload = audit_requirement_relations_service(
            REPORTED,
            llm_candidate_bundle=bundle,
            output="legacy-public-v0",
        )

        legacy = payload["legacy_payload"]
        llm_run = next(
            item for item in legacy["analysis_runs"] if item["provider_kind"] == "llm"
        )
        self.assertEqual(llm_run["execution"]["status"], "failed")
        self.assertTrue(
            any(
                "source_digest_mismatch" in item
                for item in llm_run["execution"]["diagnostics"]
            )
        )


if __name__ == "__main__":
    unittest.main()
