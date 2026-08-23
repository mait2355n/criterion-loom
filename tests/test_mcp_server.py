from __future__ import annotations

import asyncio
import inspect
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from semantic_guard.legacy_runner import MAX_REQUIREMENT_INPUT_BYTES
from semantic_guard.mcp_server import (
    LEGACY_SHADOW_ENABLE_ENV,
    LEGACY_SHADOW_ROOT_ENV,
    _LEGACY_BASELINE,
    _LEGACY_BASELINE_SHA256,
    _fixed_legacy_shadow_paths,
    audit_direction_binding_service,
    audit_requirement_relations_service,
    semantic_guard_constitution_resource,
    semantic_guard_schema_resource,
    semantic_guard_schema_tool,
    shadow_compare_legacy_tool,
)
from semantic_guard.mcp_server import mcp


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
        "schema_version": "semantic-guard-llm-candidates/v0",
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
                    "end": method_start + len("検索結果の検索応答時間を benchmark で測定する"),
                    "role": "verification_method",
                },
                "to_span": {
                    "start": criterion_start,
                    "end": criterion_start + len("担当者によれば検索応答時間 p95 500ms 以下"),
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
    def test_shadow_baseline_identity_is_the_frozen_2026_07_17_capture(self) -> None:
        self.assertEqual(
            _LEGACY_BASELINE,
            Path("vnext/migration/legacy-baseline-2026-07-17.json"),
        )
        self.assertEqual(
            _LEGACY_BASELINE_SHA256,
            "df7acb77fe03495d11e82dff44b4674ae020bab852da7f706bc86c55a8d53fe4",
        )

    def test_mcp_identity_and_resource_uris_are_canonical(self) -> None:
        self.assertEqual(mcp.name, "semantic-guard")
        self.assertEqual(
            {item.name for item in asyncio.run(mcp.list_tools())},
            {
                "audit_requirement_relations_tool",
                "audit_direction_binding_tool",
                "semantic_guard_schema_tool",
                "shadow_compare_legacy_tool",
            },
        )
        self.assertEqual(
            {str(item.uri) for item in asyncio.run(mcp.list_resources())},
            {"semantic-guard://constitution/v1"},
        )
        self.assertEqual(
            {
                item.uriTemplate
                for item in asyncio.run(mcp.list_resource_templates())
            },
            {"semantic-guard://schemas/{name}"},
        )

    def test_public_service_safe_default_requires_analysis_providers(self) -> None:
        payload = audit_requirement_relations_service(COMPLETE)

        self.assertEqual(payload["schema_version"], "semantic-guard-audit-result/v0")
        self.assertEqual(payload["analysis_mode"], "assurance")
        self.assertEqual(payload["workflow_disposition"]["status"], "warn")
        self.assertEqual(
            set(payload["execution"]["required_provider_failure_ids"]),
            {
                "morphology:not_configured",
                "dependency_parse:not_configured",
                "llm_candidate:not_configured",
            },
        )
        self.assertEqual(
            payload["workflow_disposition"]["acceptance_owner"],
            "human_external_to_semantic_guard",
        )

    def test_direction_binding_service_fails_closed_without_morphology(self) -> None:
        payload = audit_direction_binding_service(
            "横一列で、Aの次の項目はどれですか？",
            recorded_at="2026-08-23T00:00:00Z",
        )

        self.assertEqual(
            payload["schema_version"],
            "semantic-guard-direction-binding-audit/v1",
        )
        self.assertEqual(payload["primary_rule_evaluation"]["state"], "indeterminate")
        self.assertEqual(payload["workflow_disposition"]["status"], "warn")
        self.assertEqual(payload["execution"]["authority"], "signal_only")

    def test_service_direct_short_circuit_is_explicit(self) -> None:
        payload = audit_requirement_relations_service(
            COMPLETE,
            analysis_mode="conditional",
        )

        self.assertEqual(payload["workflow_disposition"]["status"], "pass")

    def test_invalid_provider_choice_is_not_silently_ignored(self) -> None:
        with self.assertRaisesRegex(ValueError, "morphology must be"):
            audit_requirement_relations_service(COMPLETE, morphology="unknown")

    def test_schema_tool_is_closed_to_known_names(self) -> None:
        payload = semantic_guard_schema_tool("audit-result")
        self.assertFalse(payload["unevaluatedProperties"])

        v1 = semantic_guard_schema_tool("assurance-claim-v1")
        self.assertEqual(v1["properties"]["schema_version"]["const"], "assurance-claim/v1")

        sidecar = semantic_guard_schema_tool("state-assessment")
        self.assertEqual(
            sidecar["properties"]["schema_version"]["const"],
            "state-assessment/v2",
        )

        with self.assertRaisesRegex(ValueError, "unknown schema"):
            semantic_guard_schema_tool("arbitrary-path")

    def test_service_assurance_v1_is_opt_in_and_replayable(self) -> None:
        payload = audit_requirement_relations_service(
            COMPLETE,
            analysis_mode="conditional",
            output="assurance-v1",
        )

        self.assertEqual(payload["schema_version"], "assurance-claim/v1")
        self.assertTrue(payload["proof_obligations"])
        self.assertEqual(payload["authority_boundary"]["final_acceptance_owner"], "human")

    def test_public_service_rejects_oversized_input(self) -> None:
        with self.assertRaisesRegex(ValueError, "exceeds"):
            audit_requirement_relations_service(
                "a" * (MAX_REQUIREMENT_INPUT_BYTES + 1)
            )

    def test_shadow_tool_does_not_accept_caller_selected_paths(self) -> None:
        parameters = inspect.signature(shadow_compare_legacy_tool).parameters

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
            baseline = root / "vnext" / "migration" / "legacy-baseline-2026-07-17.json"
            adapter = root / "vnext" / "scripts" / "legacy_request_adapter.py"
            interpreter = root / ".venv" / "bin" / "python"
            for path in (baseline, adapter, interpreter):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("placeholder", encoding="utf-8")
            interpreter.chmod(0o755)

            fixture_digest = hashlib.sha256(baseline.read_bytes()).hexdigest()
            with patch(
                "semantic_guard.mcp_server._LEGACY_BASELINE_SHA256",
                fixture_digest,
            ):
                resolved = _fixed_legacy_shadow_paths(
                    {
                        LEGACY_SHADOW_ENABLE_ENV: "1",
                        LEGACY_SHADOW_ROOT_ENV: str(root),
                    }
                )

            self.assertEqual(resolved, (root.resolve(), baseline.resolve(), adapter.resolve()))

    def test_shadow_manifest_is_pinned_by_server_digest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline = root / "vnext" / "migration" / "legacy-baseline-2026-07-17.json"
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
        schema = json.loads(semantic_guard_schema_resource("audit-result"))
        constitution = semantic_guard_constitution_resource()

        self.assertEqual(
            schema["$id"],
            "https://semantic-guard.local/v1/schemas/audit-result.schema.json",
        )
        self.assertIn("semantic-guard-constitution", constitution)

    def test_service_accepts_digest_bound_caller_llm_candidates(self) -> None:
        payload = audit_requirement_relations_service(
            REPORTED,
            llm_candidate_bundle=llm_bundle(REPORTED),
        )

        llm_run = next(
            item for item in payload["analysis_runs"] if item["provider_kind"] == "llm"
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
        )

        llm_run = next(
            item for item in payload["analysis_runs"] if item["provider_kind"] == "llm"
        )
        self.assertEqual(llm_run["execution"]["status"], "failed")
        self.assertTrue(
            any("source_digest_mismatch" in item for item in llm_run["execution"]["diagnostics"])
        )


if __name__ == "__main__":
    unittest.main()
