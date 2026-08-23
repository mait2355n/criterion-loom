from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from semantic_guard.cli import build_parser, main
from semantic_guard.legacy_runner import MAX_REQUIREMENT_INPUT_BYTES


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
        "schema_version": "semantic-guard-llm-candidates/v0",
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
                "from_span": {"start": method_start, "end": method_end, "role": "verification_method"},
                "to_span": {"start": criterion_start, "end": criterion_end, "role": "acceptance_criteria"},
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

    def test_version_identifies_the_canonical_release(self) -> None:
        output = StringIO()
        with redirect_stdout(output):
            with self.assertRaises(SystemExit) as raised:
                main(("--version",))

        self.assertEqual(raised.exception.code, 0)
        self.assertEqual(output.getvalue(), "semantic-guard 1.1.0\n")

    def test_direction_input_help_names_the_direction_expression(self) -> None:
        parser = build_parser()
        subparsers = next(action for action in parser._actions if action.dest == "command")
        help_text = subparsers.choices["audit-direction-binding"].format_help()

        self.assertIn("Direction-open expression text.", help_text)
        self.assertNotIn("Requirement record text.", help_text)

    def test_public_audit_safe_default_does_not_pass_without_required_providers(self) -> None:
        status, payload = self.invoke(
            "audit-requirement",
            "--text",
            COMPLETE,
            "--recorded-at",
            "2026-07-16T00:00:00Z",
        )

        self.assertEqual(status, 0)
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

        self.assertEqual(status, 0)
        self.assertEqual(payload["workflow_disposition"]["status"], "pass")

    def test_legacy_compatibility_is_explicit_and_separate(self) -> None:
        status, payload = self.invoke(
            "audit-requirement",
            "--text",
            COMPLETE,
            "--output",
            "legacy-compat",
        )

        self.assertEqual(status, 0)
        self.assertEqual(
            set(payload),
            {"phase", "status", "score", "findings", "missing", "next_actions", "details"},
        )
        self.assertIn("score_semantics", payload["details"])

    def test_schema_command_returns_closed_contract(self) -> None:
        status, payload = self.invoke("schema", "audit-result")

        self.assertEqual(status, 0)
        self.assertFalse(payload["unevaluatedProperties"])

        status, payload = self.invoke("schema", "assurance-claim-v1")
        self.assertEqual(status, 0)
        self.assertEqual(payload["properties"]["schema_version"]["const"], "assurance-claim/v1")

        status, payload = self.invoke("schema", "repair-cycle")
        self.assertEqual(status, 0)
        self.assertEqual(payload["properties"]["schema_version"]["const"], "repair-cycle/v2")

    def test_assurance_v1_output_is_explicit_and_keeps_human_boundary(self) -> None:
        status, payload = self.invoke(
            "audit-requirement",
            "--text",
            COMPLETE,
            "--analysis-mode",
            "conditional",
            "--output",
            "assurance-v1",
            "--recorded-at",
            "2026-07-16T00:00:00Z",
        )

        self.assertEqual(status, 0)
        self.assertEqual(payload["schema_version"], "assurance-claim/v1")
        self.assertEqual(payload["base_claim"]["schema_version"], "assurance-claim/v0")
        self.assertEqual(payload["authority_boundary"]["final_acceptance_owner"], "human")

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

        self.assertEqual(payload["workflow_disposition"]["status"], "warn")
        self.assertEqual(status, 3)

    def test_fail_on_block_does_not_reclassify_warn(self) -> None:
        status, payload = self.invoke(
            "audit-requirement",
            "--text",
            REPORTED,
            "--fail-on",
            "block",
            "--recorded-at",
            "2026-07-16T00:00:00Z",
        )

        self.assertEqual(payload["workflow_disposition"]["status"], "warn")
        self.assertEqual(status, 0)

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

    def test_digest_bound_llm_candidate_bundle_is_connected_as_candidate_only(self) -> None:
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
                "--recorded-at",
                "2026-07-16T00:00:00Z",
            )

        self.assertEqual(status, 0)
        llm_run = next(
            item for item in payload["analysis_runs"] if item["provider_kind"] == "llm"
        )
        self.assertEqual(llm_run["maximum_evidentiary_authority"], "candidate_only")
        verifies = next(
            item for item in payload["obligation_results"] if item["obligation_id"] == "func.verifies"
        )
        self.assertIn(
            "interpretation.cli.fixture",
            {item["interpretation_id"] for item in verifies["interpretations"]},
        )
        candidate = next(
            item for item in verifies["interpretations"]
            if item["interpretation_id"] == "interpretation.cli.fixture"
        )
        self.assertEqual(candidate["status"], "candidate")
        self.assertEqual(candidate["supporting_evidence_refs"], [])


if __name__ == "__main__":
    unittest.main()
