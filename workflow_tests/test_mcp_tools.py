from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from semantic_guard_workflow.mcp_server import (
    acceptance_bundle_template_tool,
    audit_artifact_membership_tool,
    audit_conventions_tool,
    audit_decision_state_tool,
    audit_result_schema_tool,
    audit_request_tool,
    audit_plan_tool,
    doctor_tool,
    evaluate_fixtures_tool,
    conventions_catalog_tool,
    explore_request_tool,
    llm_explore_request_tool,
    llm_explore_request_start_tool,
    llm_exploration_status_tool,
    llm_review_command_tool,
    llm_review_run_tool,
    llm_review_start_tool,
    llm_review_status_tool,
    review_if_needed_tool,
    review_if_needed_start_tool,
    request_exploration_review_schema_tool,
    rule_detector_map_tool,
    trace_report_tool,
    validate_acceptance_bundle_tool,
)
from workflow_tests.test_request_decision_frame import QUESTION, ROWS, SignalProvider


class MCPToolTests(unittest.TestCase):
    def test_explore_request_tool_returns_material_questions(self) -> None:
        result = explore_request_tool("割り勘アプリを作りたい")

        self.assertEqual(result["phase"], "explore_request")
        self.assertEqual(result["status"], "warn")
        self.assertIn("target_audience", result["missing"])
        self.assertIn("severity_profile", result["details"])

    def test_llm_explore_request_tool_defaults_to_dry_run(self) -> None:
        result = llm_explore_request_tool("割り勘アプリを作りたい")

        self.assertFalse(result["executed"])
        self.assertEqual(result["execution_status"], "dry_run")
        self.assertIn("request_exploration_interviewer", result["prompt"])

    def test_llm_explore_request_start_tool_reports_input_error_without_running(self) -> None:
        result = llm_explore_request_start_tool("")

        self.assertEqual(result["state"], "input_error")
        self.assertTrue(result["done"])
        self.assertFalse(result["valid"])
        self.assertIn("`text` must be a non-empty string", result["errors"])

    def test_llm_exploration_status_tool_reports_missing_job(self) -> None:
        result = llm_exploration_status_tool("missing")

        self.assertEqual(result["state"], "not_found")
        self.assertTrue(result["done"])
        self.assertFalse(result["exploration_received"])

    def test_evaluate_fixtures_tool_reports_calibration_summary(self) -> None:
        result = evaluate_fixtures_tool()

        self.assertGreater(result["total"], 0)
        self.assertEqual(result["failed"], 0)
        self.assertEqual(result["pass_rate"], 1.0)

    def test_audit_plan_tool_accepts_profile(self) -> None:
        result = audit_plan_tool(
            "目的: 設定を公開する。対象外: UI。成果物: config。手順: 調査、実装、検証。"
            "依存: config。リスク: 運用が壊れる。検証: unittest。妥当性: 利用者が判断する。"
            "判断主体: 利用者。確認点: 実装後。戻し方: backup。証拠: コマンド結果。未確定: なし。",
            profile="release",
        )

        self.assertEqual(result["details"]["severity_profile"]["name"], "release")

    def test_audit_decision_state_tool_reports_profiled_result(self) -> None:
        result = audit_decision_state_tool("未決定: 判断基準。owner: 人間。next_action: 基準を書く。", profile="dogfood")

        self.assertEqual(result["phase"], "audit_decision_state")
        self.assertIn("severity_profile", result["details"])
        self.assertEqual(result["details"]["severity_profile"]["name"], "dogfood")
        self.assertGreaterEqual(result["details"]["decision_state_report"]["unresolved_item_count"], 1)

    def test_audit_artifact_membership_tool_matches_public_contract(self) -> None:
        result = audit_artifact_membership_tool(
            "アナタがさっき言った通り、秘密鍵を成果物へ含めない。",
            artifact_id="artifact.guide",
            artifact_kind="guide",
            purpose="安全な運用案内を渡す",
            audience="運用担当者",
            intended_use="公開可否を判断する",
            required_elements=["秘密鍵を成果物へ含めない。"],
        )
        assessment = result["details"]["assessments"][0]

        self.assertEqual(result["phase"], "audit_artifact_membership")
        self.assertEqual(result["details"]["schema_version"], "artifact-membership-audit/v0")
        self.assertEqual(assessment["membership_status"], "mixed")
        self.assertEqual(assessment["recommended_disposition"], "retain_transformed")
        self.assertEqual(assessment["performed_action"], "none")
        self.assertEqual(assessment["truth_assessment"]["status"], "not_performed")
        self.assertIn("severity_profile", result["details"])

    def test_audit_artifact_membership_tool_withholds_split_source_fragments(self) -> None:
        result = audit_artifact_membership_tool(
            "alpha-sensitive\n\nbeta-sensitive",
            artifact_id="artifact.guide",
            artifact_kind="guide",
            purpose="alpha-sensitive",
            audience="beta-sensitive",
            intended_use="Review publication",
            non_exportable_context=["alpha-sensitivebeta-sensitive"],
        )
        serialized = json.dumps(result, ensure_ascii=False)

        self.assertNotIn("alpha-sensitive", serialized)
        self.assertNotIn("beta-sensitive", serialized)
        self.assertFalse(result["details"]["context_excision_assessment"]["excision_ready"])

    def test_audit_request_tool_defaults_to_logical_trace_summary(self) -> None:
        result = audit_request_tool("目的: 速度改善をしたい。")
        full = audit_request_tool("目的: 速度改善をしたい。", logical_trace="full")
        none = audit_request_tool("目的: 速度改善をしたい。", logical_trace="none")

        self.assertIn("logical_trace_summary", result["details"])
        self.assertNotIn("logical_trace", result["details"])
        self.assertIn("logical_trace", full["details"])
        self.assertNotIn("logical_trace", none["details"])
        self.assertNotIn("logical_trace_summary", none["details"])
        self.assertIn("requirement_relation_summary", result["details"])
        self.assertIn("requirement_relation_summary", full["details"])
        self.assertIn("requirement_relation_summary", none["details"])
        self.assertEqual(
            result["details"]["requirement_relation_summary"]["schema_version"],
            "requirement-relation-summary/v1",
        )

    def test_audit_request_tool_accepts_opt_in_morphology(self) -> None:
        provider = SignalProvider()
        with patch("semantic_guard_workflow.mcp_server.SudachiMorphologyProvider", return_value=provider):
            result = audit_request_tool(ROWS + QUESTION, morphology="sudachi")

        self.assertEqual(provider.calls, 1)
        self.assertEqual(
            result["details"]["decision_frame_summary"]["status"],
            "direction_unbound",
        )
        self.assertIn(
            "req.precondition.order_direction_unspecified",
            {item.get("rule_id") for item in result["findings"]},
        )

    def test_audit_request_tool_rejects_unknown_morphology(self) -> None:
        with self.assertRaisesRegex(ValueError, "none or sudachi"):
            audit_request_tool("request", morphology="unknown")

    def test_audit_request_tool_rejects_morphology_for_document(self) -> None:
        with self.assertRaisesRegex(ValueError, "only for requirement"):
            audit_request_tool("document", kind="document", morphology="sudachi")

    def test_trace_report_tool_builds_report(self) -> None:
        result = trace_report_tool(
            {
                "request": "利用者: 保守者。目的: evaluate-fixtures が JSON summary を返す。",
                "plan": "目的: evaluate-fixtures JSON summary を実装する。検証: unittest と CLI。",
                "finish": "完了要約: evaluate-fixtures JSON summary を追加した。",
                "evidence": "受入証拠: semantic-guard evaluate-fixtures が JSON summary を返した。",
            }
        )

        self.assertEqual(result["phase"], "trace_report")
        self.assertIn("links", result)

    def test_schema_mapping_and_doctor_tools(self) -> None:
        schema = audit_result_schema_tool()
        exploration_schema = request_exploration_review_schema_tool()
        mapping = rule_detector_map_tool()
        catalog = conventions_catalog_tool()
        doctor = doctor_tool(run_fixtures=False)

        self.assertEqual(schema["title"], "semantic-guard audit result")
        self.assertEqual(exploration_schema["title"], "semantic-guard request exploration review")
        self.assertEqual(mapping["rule_count"], mapping["mapping_count"])
        self.assertEqual(mapping["unmapped_rule_ids"], [])
        self.assertGreater(len(mapping["mappings"]), 0)
        self.assertEqual(catalog["schema_version"], "semantic-guard-conventions/v1")
        self.assertEqual(doctor["phase"], "doctor")
        self.assertIn(doctor["status"], {"pass", "warn"})

    def test_audit_conventions_tool_reports_contract_gaps(self) -> None:
        result = audit_conventions_tool("API response JSON を返す。失敗時も error を返す。")

        self.assertEqual(result["phase"], "audit_conventions")
        self.assertEqual(result["status"], "warn")
        self.assertIn("conv.structure.versioned_shape", result["missing"])
        self.assertIn("conv.output.envelope", result["missing"])
        self.assertIn("severity_profile", result["details"])

    def test_llm_review_command_tool_is_dry_run(self) -> None:
        result = llm_review_command_tool({"candidate": "要求: いい感じに速くする。", "phase": "audit_request"})

        self.assertFalse(result["executed"])
        self.assertEqual(result["execution_status"], "dry_run")
        self.assertIn("codex", result["command"])
        self.assertIn("candidate_gap_reviewer", result["prompt"])

    def test_llm_review_run_tool_defaults_to_dry_run(self) -> None:
        result = llm_review_run_tool({"candidate": "計画: 実装する。", "phase": "audit_plan"})

        self.assertFalse(result["executed"])
        self.assertEqual(result["execution_status"], "dry_run")

    def test_llm_review_start_tool_reports_input_error_without_running(self) -> None:
        result = llm_review_start_tool({"phase": "audit_request"})

        self.assertEqual(result["state"], "input_error")
        self.assertTrue(result["done"])
        self.assertFalse(result["valid"])
        self.assertIn("`candidate` must be a non-empty string", result["errors"])

    def test_llm_review_status_tool_reports_missing_job(self) -> None:
        result = llm_review_status_tool("missing")

        self.assertEqual(result["state"], "not_found")
        self.assertTrue(result["done"])
        self.assertFalse(result["review_received"])

    def test_review_if_needed_tool_defaults_to_dry_run(self) -> None:
        result = review_if_needed_tool(
            {
                "candidate": "計画本文",
                "phase": "audit_plan",
                "deterministic_audit": {
                    "phase": "audit_plan",
                    "status": "warn",
                    "score": 0.82,
                    "findings": [
                        {
                            "severity": "major",
                            "category": "planning",
                            "finding": "計画に `verification_plan` が見えない。",
                            "warning_class": "possible false positive",
                            "nearest_candidates": ["点検方針: 人間が画面を見る。"],
                        }
                    ],
                },
            }
        )

        self.assertTrue(result["escalation"]["needed"])
        self.assertFalse(result["review_result"]["executed"])
        self.assertEqual(result["review_result"]["execution_status"], "dry_run")

    def test_review_if_needed_start_tool_returns_not_needed_without_job(self) -> None:
        result = review_if_needed_start_tool(
            {
                "candidate": "要求: 利用者: 保守者。目的: 設定を保存する。受入基準: 設定が保存される。",
                "phase": "audit_request",
                "deterministic_audit": {"phase": "audit_request", "status": "pass", "score": 1.0, "findings": []},
            }
        )

        self.assertEqual(result["state"], "not_needed")
        self.assertIsNone(result["job_id"])
        self.assertFalse(result["escalation"]["needed"])

    def test_acceptance_bundle_tools(self) -> None:
        bundle = acceptance_bundle_template_tool(
            {
                "original_request": "最終評価bundleを作る。",
                "final_artifact": {"kind": "document", "reference": "README.md", "summary": "説明を更新した。"},
            }
        )

        self.assertEqual(bundle["schema_version"], "acceptance-review-bundle/v1")
        result = validate_acceptance_bundle_tool(bundle, strict=False)
        self.assertEqual(result, {"valid": True, "errors": []})


if __name__ == "__main__":
    unittest.main()
