from __future__ import annotations

import importlib
import json
import unittest

from semantic_guard_workflow.rule_mapping import (
    rule_detector_mapping,
    rule_detector_mappings,
    unmapped_rule_ids,
)
from semantic_guard_workflow.rules import (
    RULES,
    RULES_BY_ID,
    get_rule,
    rules_for_discipline,
    rules_for_phase,
)


class RuleCatalogTests(unittest.TestCase):
    def test_rule_ids_are_unique(self) -> None:
        ids = [rule.id for rule in RULES]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(set(ids), set(RULES_BY_ID))

    def test_retired_numeric_outcome_rule_is_not_active(self) -> None:
        self.assertNotIn("req.precondition.outcome_not_invariant", RULES_BY_ID)
        with self.assertRaises(KeyError):
            rule_detector_mapping("req.precondition.outcome_not_invariant")

    def test_rules_have_engineering_shape(self) -> None:
        for rule in RULES:
            with self.subTest(rule=rule.id):
                self.assertRegex(rule.id, r"^[a-z]+(?:\.[a-z0-9_]+)+$")
                self.assertTrue(rule.engineering_basis)
                self.assertTrue(rule.concern)
                self.assertTrue(rule.applies_when)
                self.assertTrue(rule.does_not_apply_when)
                self.assertTrue(rule.evidence_required)
                self.assertTrue(rule.severity_policy)
                self.assertTrue(rule.finding)
                self.assertTrue(rule.remediation)

    def test_rules_include_reverse_application_conditions(self) -> None:
        for rule in RULES:
            with self.subTest(rule=rule.id):
                self.assertGreaterEqual(len(rule.does_not_apply_when), 2)

    def test_catalog_covers_core_audit_phases_and_disciplines(self) -> None:
        phases = {rule.phase for rule in RULES}
        self.assertIn("audit_request", phases)
        self.assertIn("audit_plan", phases)
        self.assertIn("audit_diff", phases)
        self.assertIn("finish_check", phases)

        disciplines = {rule.discipline for rule in RULES}
        self.assertIn("requirements_engineering", disciplines)
        self.assertIn("project_planning", disciplines)
        self.assertIn("software_engineering", disciplines)
        self.assertIn("secure_development", disciplines)
        self.assertIn("semantic_preservation", disciplines)

    def test_rule_lookup_helpers(self) -> None:
        rule = get_rule("req.verifiability.acceptance_missing")
        self.assertEqual(rule.phase, "audit_request")
        self.assertIn(rule, rules_for_phase("audit_request"))
        self.assertIn(rule, rules_for_discipline("requirements_engineering"))

    def test_rule_serialization_is_json_safe(self) -> None:
        payload = [rule.as_dict() for rule in RULES]
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        self.assertIn("does_not_apply_when", encoded)
        self.assertIn("engineering_basis", encoded)

    def test_rule_detector_mapping_covers_catalog(self) -> None:
        self.assertEqual(unmapped_rule_ids(), [])
        mappings = rule_detector_mappings()
        self.assertEqual({item["rule_id"] for item in mappings}, {rule.id for rule in RULES})
        for item in mappings:
            with self.subTest(rule=item["rule_id"]):
                self.assertTrue(item["detector_id"])
                self.assertTrue(str(item["source_module"]).startswith("semantic_guard_workflow."))
                self.assertTrue(item["source_functions"])

    def test_rule_detector_mapping_sources_resolve(self) -> None:
        for mapping in rule_detector_mappings():
            with self.subTest(rule=mapping["rule_id"]):
                module = importlib.import_module(str(mapping["source_module"]))
                for source_function in mapping["source_functions"]:
                    symbol_name = str(source_function)
                    self.assertTrue(
                        hasattr(module, symbol_name),
                        f"{mapping['source_module']}.{symbol_name} does not resolve",
                    )
                    symbol = getattr(module, symbol_name)
                    self.assertEqual(
                        getattr(symbol, "__module__", ""),
                        mapping["source_module"],
                        f"{mapping['source_module']}.{symbol_name} is only re-exported there",
                    )

    def test_logical_rule_mapping_exposes_predicate_id(self) -> None:
        mapping = rule_detector_mapping("req.verifiability.acceptance_missing")

        self.assertEqual(mapping.predicate_id, "req.verifiability.acceptance_missing/v1")


if __name__ == "__main__":
    unittest.main()
