from __future__ import annotations

from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
from io import StringIO
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from semantic_guard_vnext.cli import main as cli_main
from semantic_guard_vnext.engine import audit_requirement_relations_vnext
from semantic_guard_vnext.legacy_runner import (
    BaselineCheck,
    LegacyExecution,
    LegacyObservation,
    normalize_legacy_result,
)
from semantic_guard_vnext.legacy_shadow_observation import (
    LegacyShadowObservationValidationError,
    build_legacy_shadow_observation,
    semantic_digest_value,
    validate_legacy_shadow_observation,
)
from semantic_guard_vnext.mcp_server import shadow_compare_legacy_vnext_tool
from semantic_guard_vnext.public_contract import (
    KNOWN_SCHEMA_NAMES,
    load_public_schema,
    public_audit_payload,
)
from semantic_guard_vnext.shadow import compare_with_legacy


COMPLETE = """Purpose: 検索APIが検索結果を p95 500ms以内で返す
User: 検索API
Scenario: 検索APIが検索要求を処理して検索結果を返す
Expected result: 検索結果を p95 500ms以内で返す
Acceptance criteria: 検索応答時間 p95 500ms 以下
Verification method: 検索結果の検索応答時間を benchmark で測定する
Evidence: 検索結果の検索応答時間 benchmark report"""
RECORDED_AT = "2026-07-18T00:00:00Z"


def legacy_observation(text: str, *, status: str = "pass") -> LegacyObservation:
    raw = {
        "phase": "audit_request",
        "status": status,
        "score": 1.0,
        "findings": [],
        "missing": [],
        "next_actions": [],
        "details": {"requirement_relation_summary": {}},
    }
    raw_bytes = json.dumps(raw, ensure_ascii=False).encode("utf-8")
    return LegacyObservation(
        schema_version="semantic-guard-legacy-observation/v0",
        execution=LegacyExecution(
            status="completed",
            command=("/pinned/python", "/pinned/adapter.py"),
            exit_code=0,
            stdout_valid_json=True,
            stderr="",
            baseline=BaselineCheck(
                status="matched",
                checked_files=2,
                mismatches=(),
                manifest_sha256="a" * 64,
                pin_profile="semantic-guard-requirement-relations-legacy/v1",
                runtime_interpreter_path=".venv/bin/python",
                runtime_python_version="3.13",
            ),
            result_schema_valid=True,
            adapter_pin_status="manifest_pinned",
            invocation_fingerprint={
                "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "context_sha256": hashlib.sha256(b"").hexdigest(),
                "strict": True,
                "profile": "default",
                "logical_trace": "summary",
                "timeout_seconds": 30.0,
                "environment_profile": "semantic-guard-legacy-normalized/v0",
            },
            stdout_sha256=hashlib.sha256(raw_bytes).hexdigest(),
            stdout_bytes=len(raw_bytes),
        ),
        raw_legacy_result=raw,
        normalized_legacy_observation=normalize_legacy_result(raw),
    )


def shadow_payload() -> dict:
    report = audit_requirement_relations_vnext(COMPLETE, analysis_mode="conditional")
    legacy = legacy_observation(COMPLETE)
    return build_legacy_shadow_observation(
        vnext=public_audit_payload(report, recorded_at=RECORDED_AT),
        legacy=legacy.as_dict(),
        comparison=compare_with_legacy(report, legacy).as_dict(),
    )


def reseal(payload: dict) -> None:
    material = deepcopy(payload)
    material.pop("envelope_id", None)
    material.pop("semantic_digest", None)
    digest = semantic_digest_value(material)
    payload["semantic_digest"] = digest
    payload["envelope_id"] = f"legacy-shadow-observation.{digest['value']}"


class LegacyShadowObservationTests(unittest.TestCase):
    def test_schema_is_available_through_the_public_registry(self) -> None:
        self.assertIn("legacy-shadow-observation-envelope", KNOWN_SCHEMA_NAMES)
        schema = load_public_schema("legacy-shadow-observation-envelope")
        self.assertEqual(
            schema["properties"]["schema_version"]["const"],
            "legacy-shadow-observation-envelope/v1",
        )

    def test_nested_local_passes_never_cross_outer_authority_boundary(self) -> None:
        payload = shadow_payload()
        validate_legacy_shadow_observation(payload)

        self.assertEqual(
            payload["schema_version"], "legacy-shadow-observation-envelope/v1"
        )
        self.assertEqual(payload["governance_status"], "legacy_shadow_observation_only")
        self.assertEqual(payload["authority_scope"], "observation_only")
        self.assertEqual(payload["formal_authority"], "none")
        self.assertFalse(payload["positive_assurance"])
        self.assertEqual(
            payload["semantic_digest"]["canonicalization"],
            "semantic-guard-canonical-json/v1",
        )
        self.assertEqual(
            payload["semantic_digest"]["scope"],
            "all_members_except_envelope_id_and_semantic_digest",
        )
        self.assertEqual(payload["vnext"]["workflow_disposition"]["status"], "pass")
        self.assertEqual(
            payload["legacy"]["normalized_legacy_observation"]["top_level"][
                "legacy_status"
            ],
            "pass",
        )

    def test_nested_change_without_reseal_is_rejected(self) -> None:
        payload = shadow_payload()
        payload["comparison"]["differences"][0]["rationale"] += " changed"

        with self.assertRaises(LegacyShadowObservationValidationError) as caught:
            validate_legacy_shadow_observation(payload)
        self.assertIn("semantic_digest_mismatch", caught.exception.codes)
        self.assertIn("envelope_id_mismatch", caught.exception.codes)

    def test_resealed_authority_escalation_is_rejected(self) -> None:
        payload = shadow_payload()
        payload["formal_authority"] = "bounded"
        payload["positive_assurance"] = True
        reseal(payload)

        with self.assertRaises(LegacyShadowObservationValidationError) as caught:
            validate_legacy_shadow_observation(payload)
        self.assertIn("schema_error", caught.exception.codes)

    def test_resealed_vnext_format_substitution_is_rejected(self) -> None:
        payload = shadow_payload()
        payload["vnext"] = deepcopy(payload["legacy"])
        reseal(payload)

        with self.assertRaises(LegacyShadowObservationValidationError) as caught:
            validate_legacy_shadow_observation(payload)
        self.assertIn("vnext_observation_invalid", caught.exception.codes)

    def test_resealed_legacy_or_comparison_format_substitution_is_rejected(
        self,
    ) -> None:
        for field in ("legacy", "comparison"):
            with self.subTest(field=field):
                payload = shadow_payload()
                payload[field] = {
                    "schema_version": "substituted/v99",
                    "formal_authority": "formal",
                }
                reseal(payload)
                with self.assertRaises(
                    LegacyShadowObservationValidationError
                ) as caught:
                    validate_legacy_shadow_observation(payload)
                self.assertIn("schema_error", caught.exception.codes)

    def test_resealed_comparison_subject_or_state_substitution_is_rejected(
        self,
    ) -> None:
        payload = shadow_payload()
        payload["comparison"]["source_id"] = "sha256:" + ("0" * 64)
        payload["comparison"]["vnext_workflow"] = "block"
        reseal(payload)

        with self.assertRaises(LegacyShadowObservationValidationError) as caught:
            validate_legacy_shadow_observation(payload)
        self.assertIn("comparison_subject_mismatch", caught.exception.codes)
        self.assertIn("comparison_vnext_state_mismatch", caught.exception.codes)

    def test_resealed_legacy_normalization_substitution_is_rejected(self) -> None:
        payload = shadow_payload()
        payload["legacy"]["normalized_legacy_observation"]["top_level"][
            "legacy_status"
        ] = "block"
        reseal(payload)

        with self.assertRaises(LegacyShadowObservationValidationError) as caught:
            validate_legacy_shadow_observation(payload)
        self.assertIn("legacy_normalization_mismatch", caught.exception.codes)

    def test_resealed_legacy_raw_format_substitution_is_rejected(self) -> None:
        payload = shadow_payload()
        payload["legacy"]["raw_legacy_result"]["phase"] = "substituted"
        reseal(payload)

        with self.assertRaises(LegacyShadowObservationValidationError) as caught:
            validate_legacy_shadow_observation(payload)
        self.assertIn("legacy_raw_format_mismatch", caught.exception.codes)

    def test_resealed_completed_state_cannot_drop_runtime_pins(self) -> None:
        payload = shadow_payload()
        payload["legacy"]["execution"]["adapter_pin_status"] = "untrusted"
        payload["legacy"]["execution"]["baseline"]["status"] = "drifted"
        reseal(payload)

        with self.assertRaises(LegacyShadowObservationValidationError) as caught:
            validate_legacy_shadow_observation(payload)
        self.assertIn("legacy_completed_state_mismatch", caught.exception.codes)

    def test_cli_shadow_path_returns_the_authority_bounded_envelope(self) -> None:
        output = StringIO()
        with (
            patch(
                "semantic_guard_vnext.cli.run_legacy_request",
                return_value=legacy_observation(COMPLETE),
            ),
            redirect_stdout(output),
        ):
            status = cli_main(
                (
                    "shadow-compare",
                    "--text",
                    COMPLETE,
                    "--analysis-mode",
                    "conditional",
                    "--legacy-root",
                    ".",
                )
            )
        payload = json.loads(output.getvalue())

        self.assertEqual(status, 0)
        self.assertEqual(
            payload["schema_version"], "legacy-shadow-observation-envelope/v1"
        )
        self.assertEqual(payload["formal_authority"], "none")
        self.assertFalse(payload["positive_assurance"])
        self.assertEqual(payload["vnext"]["workflow_disposition"]["status"], "pass")

    def test_mcp_shadow_path_returns_the_authority_bounded_envelope(self) -> None:
        paths = (Path("/legacy"), Path("/legacy/baseline"), Path("/legacy/adapter"))
        with (
            patch(
                "semantic_guard_vnext.mcp_server._fixed_legacy_shadow_paths",
                return_value=paths,
            ),
            patch(
                "semantic_guard_vnext.mcp_server.run_legacy_request",
                return_value=legacy_observation(COMPLETE),
            ),
        ):
            payload = shadow_compare_legacy_vnext_tool(
                COMPLETE,
                analysis_mode="conditional",
            )

        self.assertEqual(
            payload["schema_version"], "legacy-shadow-observation-envelope/v1"
        )
        self.assertEqual(payload["authority_scope"], "observation_only")
        self.assertEqual(payload["formal_authority"], "none")
        self.assertFalse(payload["positive_assurance"])
        self.assertEqual(payload["vnext"]["workflow_disposition"]["status"], "pass")


if __name__ == "__main__":
    unittest.main()
