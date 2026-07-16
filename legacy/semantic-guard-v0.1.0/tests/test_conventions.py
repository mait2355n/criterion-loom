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


if __name__ == "__main__":
    unittest.main()
