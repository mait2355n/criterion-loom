from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from semantic_guard_vnext.cli import main
from semantic_guard_vnext.governance_materials import (
    default_candidate_governance_materials,
)
from semantic_guard_vnext.legacy_runner import MAX_REQUIREMENT_INPUT_BYTES


COMPLETE = """Purpose: 検索APIが検索結果を p95 500ms以内で返す
User: 検索API
Scenario: 検索APIが検索要求を処理して検索結果を返す
Expected result: 検索結果を p95 500ms以内で返す
Acceptance criteria: 検索応答時間 p95 500ms 以下
Verification method: 検索結果の検索応答時間を benchmark で測定する
Evidence: 検索結果の検索応答時間 benchmark report"""

REPORTED = """Purpose: 検索APIが検索結果を p95 500ms以内で返す
User: 検索API
Scenario: 検索APIが検索要求を処理して検索結果を返す
Expected result: 検索結果を p95 500ms以内で返す
Acceptance criteria: 担当者によれば検索応答時間 p95 500ms 以下
Verification method: 検索結果の検索応答時間を benchmark で測定する
Evidence: 検索結果の検索応答時間 benchmark report"""


def llm_bundle(text: str) -> dict:
    method_start = text.index("検索結果の検索応答時間を benchmark")
    method_end = method_start + len("検索結果の検索応答時間を benchmark で測定する")
    criterion_start = text.index("担当者によれば検索応答時間")
    criterion_end = criterion_start + len("担当者によれば検索応答時間 p95 500ms 以下")
    return {
        "schema_version": "semantic-guard-vnext-llm-candidates/v0",
        "bundle_id": "bundle.cli.fixture",
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
                    "end": method_end,
                    "role": "verification_method",
                },
                "to_span": {
                    "start": criterion_start,
                    "end": criterion_end,
                    "role": "acceptance_criteria",
                },
                "interpretation_id": "interpretation.cli.fixture",
                "rationale": "Caller proposes a verification-target relation; candidate only.",
            }
        ],
        "scopes": [],
        "diagnostics": [],
    }


class CliTests(unittest.TestCase):
    def invoke(self, *args: str) -> tuple[int, dict]:
        output = StringIO()
        with redirect_stdout(output):
            status = main(args)
        return status, json.loads(output.getvalue())

    def test_invalid_recorded_at_is_a_public_cli_input_error(self) -> None:
        cases = [
            ("yesterday", "governed-v1"),
            ("", "governed-v1"),
            ("123", "governed-v1"),
            ("2026-07-16", "governed-v1"),
            ("2026-07-16T00:00:00", "governed-v1"),
            ("2026-02-30T00:00:00Z", "governed-v1"),
            ("2026-07-16T25:00:00Z", "governed-v1"),
            ("2026-07-16T00:00:00+24:00", "governed-v1"),
            ("yesterday", "public"),
            ("yesterday", "legacy-public-v0"),
            ("yesterday", "legacy-assurance-v1"),
            ("yesterday", "legacy-compat"),
            ("yesterday", "legacy-internal-debug-v0"),
        ]
        for timestamp, output in cases:
            with self.subTest(timestamp=timestamp, output=output):
                process = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "semantic_guard_vnext.cli",
                        "audit-requirement",
                        "--text",
                        COMPLETE,
                        "--recorded-at",
                        timestamp,
                        "--output",
                        output,
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                self.assertEqual(process.returncode, 2, process.stderr)
                self.assertEqual(process.stdout, "")
                self.assertIn("--recorded-at", process.stderr)
                self.assertIn("RFC 3339", process.stderr)
                self.assertNotIn("Traceback", process.stderr)

    def test_invalid_recorded_at_is_rejected_before_audit_or_shadow_execution(
        self,
    ) -> None:
        for command in ("audit-requirement", "shadow-compare"):
            with self.subTest(command=command):
                output, error = StringIO(), StringIO()
                with (
                    patch(
                        "semantic_guard_vnext.cli.audit_requirement_relations_vnext",
                        side_effect=AssertionError("analysis must not start"),
                    ) as audit,
                    redirect_stdout(output),
                    redirect_stderr(error),
                    self.assertRaises(SystemExit) as caught,
                ):
                    main((command, "--text", COMPLETE, "--recorded-at", "yesterday"))
                self.assertEqual(caught.exception.code, 2)
                self.assertEqual(output.getvalue(), "")
                self.assertIn("--recorded-at", error.getvalue())
                audit.assert_not_called()

    def test_valid_recorded_at_survives_the_public_cli_unchanged(self) -> None:
        for timestamp, fail_on, expected_exit in (
            ("2026-07-16T00:00:00Z", (), 3),
            ("2026-07-16T09:00:00.125+09:00", ("--fail-on", "never"), 0),
        ):
            with self.subTest(timestamp=timestamp, fail_on=fail_on):
                process = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "semantic_guard_vnext.cli",
                        "audit-requirement",
                        "--text",
                        COMPLETE,
                        "--recorded-at",
                        timestamp,
                        *fail_on,
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                self.assertEqual(process.returncode, expected_exit, process.stderr)
                self.assertEqual(process.stderr, "")
                payload = json.loads(process.stdout)
                self.assertEqual(payload["recorded_at"], timestamp)
                self.assertEqual(
                    payload["assurance_assessment"]["workflow_disposition"], "block"
                )

    def test_public_audit_safe_default_does_not_pass_without_required_providers(
        self,
    ) -> None:
        status, payload = self.invoke(
            "audit-requirement",
            "--text",
            COMPLETE,
            "--recorded-at",
            "2026-07-16T00:00:00Z",
        )

        self.assertEqual(status, 3)
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

    def test_direct_short_circuit_requires_explicit_conditional_mode(self) -> None:
        status, payload = self.invoke(
            "audit-requirement",
            "--text",
            COMPLETE,
            "--analysis-mode",
            "conditional",
            "--recorded-at",
            "2026-07-16T00:00:00Z",
        )

        self.assertEqual(status, 3)
        self.assertEqual(
            payload["legacy_analysis_observation"]["observed_workflow_disposition"],
            "pass",
        )
        self.assertEqual(
            payload["assurance_assessment"]["workflow_disposition"], "block"
        )
        self.assertEqual(
            payload["assurance_assessment"]["formal_verdict_authority"], "none"
        )

    def test_governance_material_file_substitution_is_rejected_not_ignored(
        self,
    ) -> None:
        materials = default_candidate_governance_materials()
        materials["engineering_rule_pack_candidate"]["document"]["rules"][0][
            "engineering_proposition"
        ] = "substituted through CLI"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "governance-materials.json"
            path.write_text(json.dumps(materials, ensure_ascii=False), encoding="utf-8")
            status, payload = self.invoke(
                "audit-requirement",
                "--text",
                COMPLETE,
                "--governance-materials",
                str(path),
            )

        axis = payload["governance_material_assessment"]["engineering_rule_governance"]
        self.assertEqual(status, 3)
        self.assertEqual(axis["input_status"], "rejected")
        self.assertEqual(axis["binding_status"], "invalid")
        self.assertEqual(
            payload["governance_resolution"]["observation_binding_status"],
            "not_bound",
        )
        self.assertEqual(
            payload["assurance_assessment"]["workflow_disposition"], "block"
        )

    def test_field_material_type_errors_are_serialized_as_rejected(self) -> None:
        for value in (None, {}, 1, False, "invalid", []):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "governance-materials.json"
                path.write_text(
                    json.dumps({"field_performance_bundle": value}), encoding="utf-8"
                )
                status, payload = self.invoke(
                    "audit-requirement",
                    "--text",
                    COMPLETE,
                    "--governance-materials",
                    str(path),
                )

                material = payload["governance_material_assessment"]
                axis = material["field_performance_evidence"]
                self.assertEqual(status, 3)
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

    def test_legacy_compatibility_is_explicit_and_separate(self) -> None:
        status, payload = self.invoke(
            "audit-requirement",
            "--text",
            COMPLETE,
            "--output",
            "legacy-compat",
        )

        self.assertEqual(status, 0)
        self.assertEqual(payload["governance_status"], "legacy_ungoverned")
        self.assertEqual(payload["authority_scope"], "observation_only")
        self.assertEqual(payload["formal_authority"], "none")
        self.assertFalse(payload["positive_assurance"])
        self.assertIn("score_semantics", payload["legacy_payload"]["details"])

    def test_schema_command_returns_closed_contract(self) -> None:
        status, payload = self.invoke("schema", "audit-result")

        self.assertEqual(status, 0)
        self.assertFalse(payload["unevaluatedProperties"])

        status, payload = self.invoke("schema", "assurance-claim-v1")
        self.assertEqual(status, 0)
        self.assertEqual(
            payload["properties"]["schema_version"]["const"], "assurance-claim/v1"
        )

        status, payload = self.invoke("schema", "repair-cycle")
        self.assertEqual(status, 0)
        self.assertEqual(
            payload["properties"]["schema_version"]["const"], "repair-cycle/v2"
        )

        status, payload = self.invoke("schema", "legacy-output-envelope")
        self.assertEqual(status, 0)
        self.assertEqual(payload["properties"]["positive_assurance"]["const"], False)

    def test_legacy_assurance_v1_output_is_explicit_and_keeps_human_boundary(
        self,
    ) -> None:
        status, payload = self.invoke(
            "audit-requirement",
            "--text",
            COMPLETE,
            "--analysis-mode",
            "conditional",
            "--output",
            "legacy-assurance-v1",
            "--recorded-at",
            "2026-07-16T00:00:00Z",
        )

        self.assertEqual(status, 0)
        self.assertEqual(
            payload["schema_version"], "legacy-ungoverned-output-envelope/v0"
        )
        self.assertEqual(payload["output_format"], "legacy-assurance-v1")
        legacy = payload["legacy_payload"]
        self.assertEqual(legacy["schema_version"], "assurance-claim/v1")
        self.assertEqual(legacy["base_claim"]["schema_version"], "assurance-claim/v0")
        self.assertEqual(
            legacy["authority_boundary"]["final_acceptance_owner"], "human"
        )

    def test_fail_on_warn_emits_json_then_returns_audit_exit_code(self) -> None:
        status, payload = self.invoke(
            "audit-requirement",
            "--text",
            REPORTED,
            "--fail-on",
            "warn",
            "--recorded-at",
            "2026-07-16T00:00:00Z",
        )

        self.assertEqual(
            payload["assurance_assessment"]["workflow_disposition"], "block"
        )
        self.assertEqual(status, 3)

    def test_governed_default_exit_is_fail_closed_but_transport_only_is_explicit(
        self,
    ) -> None:
        default_status, _ = self.invoke(
            "audit-requirement",
            "--text",
            COMPLETE,
        )
        transport_status, payload = self.invoke(
            "audit-requirement",
            "--text",
            COMPLETE,
            "--fail-on",
            "never",
        )

        self.assertEqual(default_status, 3)
        self.assertEqual(transport_status, 0)
        self.assertEqual(payload["assurance_assessment"]["status"], "unresolved")

    def test_unqualified_assurance_output_name_is_not_public(self) -> None:
        with redirect_stderr(StringIO()):
            with self.assertRaises(SystemExit) as caught:
                main(
                    (
                        "audit-requirement",
                        "--text",
                        COMPLETE,
                        "--output",
                        "assurance-v1",
                    )
                )

        self.assertEqual(caught.exception.code, 2)

    def test_unqualified_internal_debug_name_is_not_public(self) -> None:
        with redirect_stderr(StringIO()):
            with self.assertRaises(SystemExit) as caught:
                main(
                    (
                        "audit-requirement",
                        "--text",
                        COMPLETE,
                        "--output",
                        "internal-debug",
                    )
                )
        self.assertEqual(caught.exception.code, 2)

        status, payload = self.invoke(
            "audit-requirement",
            "--text",
            COMPLETE,
            "--analysis-mode",
            "conditional",
            "--output",
            "legacy-internal-debug-v0",
        )
        self.assertEqual(status, 0)
        self.assertEqual(payload["governance_status"], "legacy_ungoverned")
        self.assertEqual(payload["authority_scope"], "observation_only")
        self.assertEqual(payload["formal_authority"], "none")
        self.assertFalse(payload["positive_assurance"])
        self.assertEqual(payload["legacy_payload"]["result"]["workflow"], "pass")

    def test_fail_on_block_stops_governed_unresolved(self) -> None:
        status, payload = self.invoke(
            "audit-requirement",
            "--text",
            REPORTED,
            "--fail-on",
            "block",
            "--recorded-at",
            "2026-07-16T00:00:00Z",
        )

        self.assertEqual(
            payload["assurance_assessment"]["workflow_disposition"], "block"
        )
        self.assertEqual(status, 3)

    def test_oversized_text_is_rejected_before_analysis(self) -> None:
        with redirect_stderr(StringIO()):
            with self.assertRaises(SystemExit) as raised:
                main(
                    (
                        "audit-requirement",
                        "--text",
                        "a" * (MAX_REQUIREMENT_INPUT_BYTES + 1),
                    )
                )

        self.assertEqual(raised.exception.code, 2)

    def test_digest_bound_llm_candidate_bundle_is_connected_as_candidate_only(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "candidates.json"
            path.write_text(
                json.dumps(llm_bundle(REPORTED), ensure_ascii=False),
                encoding="utf-8",
            )
            status, payload = self.invoke(
                "audit-requirement",
                "--text",
                REPORTED,
                "--llm-candidates",
                str(path),
                "--output",
                "legacy-public-v0",
                "--recorded-at",
                "2026-07-16T00:00:00Z",
            )

        self.assertEqual(status, 0)
        self.assertEqual(payload["governance_status"], "legacy_ungoverned")
        self.assertEqual(payload["authority_scope"], "observation_only")
        self.assertEqual(payload["formal_authority"], "none")
        self.assertFalse(payload["positive_assurance"])
        legacy = payload["legacy_payload"]
        llm_run = next(
            item for item in legacy["analysis_runs"] if item["provider_kind"] == "llm"
        )
        self.assertEqual(llm_run["maximum_evidentiary_authority"], "candidate_only")
        verifies = next(
            item
            for item in legacy["obligation_results"]
            if item["obligation_id"] == "func.verifies"
        )
        self.assertIn(
            "interpretation.cli.fixture",
            {item["interpretation_id"] for item in verifies["interpretations"]},
        )
        candidate = next(
            item
            for item in verifies["interpretations"]
            if item["interpretation_id"] == "interpretation.cli.fixture"
        )
        self.assertEqual(candidate["status"], "candidate")
        self.assertEqual(candidate["supporting_evidence_refs"], [])


if __name__ == "__main__":
    unittest.main()
