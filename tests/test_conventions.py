from __future__ import annotations

import unittest

from semantic_guard.conventions import audit_conventions, load_conventions_catalog


class ConventionTests(unittest.TestCase):
    def test_catalog_loads_base_contract(self) -> None:
        catalog = load_conventions_catalog()

        self.assertEqual(catalog["schema_version"], "semantic-guard-conventions/v1")
        self.assertEqual(catalog["id"], "base-contract")
        self.assertTrue(catalog["rules"])

    def test_audit_conventions_detects_mcp_output_contract_gap(self) -> None:
        result = audit_conventions("MCP tool を実装し JSON result を返す。")

        self.assertEqual(result["phase"], "audit_conventions")
        self.assertEqual(result["status"], "warn")
        self.assertIn("conv.structure.versioned_shape", result["missing"])
        self.assertIn("conv.output.envelope", result["missing"])
        self.assertTrue(result["details"]["surfaces"]["mcp"])

    def test_audit_conventions_passes_non_public_note(self) -> None:
        result = audit_conventions("内部メモ: 実装方針を考える。")

        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["missing"], [])

    def test_audit_conventions_detects_record_surface_gap(self) -> None:
        result = audit_conventions("JSONL 台帳に監査記録を保存する。schema_version と evidence を持つ。")

        self.assertEqual(result["status"], "warn")
        self.assertIn("conv.record.shallow_context_surface", result["missing"])

    def test_audit_conventions_accepts_shallow_record_surface(self) -> None:
        result = audit_conventions(
            "JSONL 台帳に監査記録を保存する。schema_version を持ち、fields は record_surface, evidence, "
            "inference_status, pending_decision。type は string, object, array, boolean。"
            "record_surface は context, current_state, next_action, detail_refs を持つ。"
            "timestamp は ISO 8601 timezone 付き。evidence source を記録し、inference と pending を分ける。"
        )

        self.assertNotIn("conv.record.shallow_context_surface", result["missing"])


if __name__ == "__main__":
    unittest.main()
