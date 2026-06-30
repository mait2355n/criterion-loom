from __future__ import annotations

import json
import unittest

from semantic_guard.rule_mapping import rule_detector_mappings, rule_detector_mapping, unmapped_rule_ids
from semantic_guard.rules import RULES, RULES_BY_ID, get_rule, rules_for_discipline, rules_for_phase


class RuleCatalogTests(unittest.TestCase):
    def test_rule_ids_are_unique(self) -> None:
        ids = [rule.id for rule in RULES]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(set(ids), set(RULES_BY_ID))

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
                self.assertEqual(item["source_module"], "semantic_guard.core")
                self.assertTrue(item["source_functions"])

    def test_logical_rule_mapping_exposes_predicate_id(self) -> None:
        mapping = rule_detector_mapping("req.verifiability.acceptance_missing")

        self.assertEqual(mapping.predicate_id, "req.verifiability.acceptance_missing/v1")


if __name__ == "__main__":
    unittest.main()
