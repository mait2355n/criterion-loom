from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from semantic_guard_workflow import evaluation
from semantic_guard_workflow.evaluation import DEFAULT_FIXTURE_ROOT, evaluate_fixture_tree
from semantic_guard_workflow.rule_mapping import enrich_finding_mapping, infer_rule_id
from semantic_guard_workflow.rules import RULES, RULES_BY_ID

PACKAGE = Path(evaluation.__file__).resolve().parent

# Needs a recorded morphology analysis, which the strict/relaxed replay below skips.
# Its policy is asserted by the direction-binding tests.
NEEDS_MORPHOLOGY = {"req.precondition.order_direction_unspecified"}

PHASE_BY_PREFIX = {
    "req": "audit_request",
    "doc": "audit_request",
    "plan": "audit_plan",
    "diff": "audit_diff",
    "finish": "finish_check",
}

# Sources whose string literals name catalog rules rather than detectors.
RULE_ID_SOURCES = (
    "audit_common.py",
    "diff_audit.py",
    "document_audit.py",
    "finish_audit.py",
    "plan_audit.py",
    "request_audit.py",
    "request_findings.py",
)
RULE_ID_LITERAL = re.compile(r'"((?:req|plan|diff|finish|doc)\.[a-z0-9_]+\.[a-z0-9_]+)"')


def _replay_fixtures():
    for expected_path in sorted(Path(DEFAULT_FIXTURE_ROOT).rglob("*.expected.json")):
        spec = json.loads(expected_path.read_text(encoding="utf-8"))
        yield expected_path, spec


class CatalogMatchesBehaviourTests(unittest.TestCase):
    def test_severity_policy_matches_what_the_detectors_emit(self) -> None:
        mismatches: list[tuple[str, str, str, str, str]] = []
        for expected_path, spec in _replay_fixtures():
            if spec.get("morphology") is not None:
                continue
            for strict in (True, False):
                result = evaluation._run_fixture({**spec, "strict": strict}, expected_path)
                mode = "strict" if strict else "relaxed"
                for finding in result["findings"]:
                    rule_id = enrich_finding_mapping(spec["phase"], finding).get("rule_id")
                    if rule_id not in RULES_BY_ID or rule_id in NEEDS_MORPHOLOGY:
                        continue
                    policy = {item.mode: item.severity for item in RULES_BY_ID[rule_id].severity_policy}
                    if policy[mode] != finding["severity"]:
                        mismatches.append((rule_id, mode, finding["severity"], policy[mode], expected_path.stem))

        self.assertEqual(mismatches, [])

    def test_every_replayed_finding_is_attributed_to_a_catalog_rule(self) -> None:
        unattributed: list[tuple[str, str]] = []
        for expected_path, spec in _replay_fixtures():
            result = evaluation._run_fixture(spec, expected_path)
            for finding in result["findings"]:
                rule_id = enrich_finding_mapping(spec["phase"], finding).get("rule_id")
                if rule_id not in RULES_BY_ID:
                    unattributed.append((expected_path.stem, finding["finding"]))

        self.assertEqual(unattributed, [])

    def test_every_rule_has_a_positive_and_a_negative_fixture(self) -> None:
        coverage = evaluate_fixture_tree()["rule_catalog_coverage"]

        self.assertEqual(coverage["unhit_rule_ids"], [])
        self.assertEqual(coverage["unguarded_rule_ids"], [])
        self.assertEqual(coverage["unemitted_rule_ids"], [])

    def test_rule_ids_written_in_detectors_exist_in_the_catalog(self) -> None:
        unknown: list[tuple[str, str]] = []
        for name in RULE_ID_SOURCES:
            for literal in RULE_ID_LITERAL.findall((PACKAGE / name).read_text(encoding="utf-8")):
                if literal not in RULES_BY_ID:
                    unknown.append((name, literal))

        self.assertEqual(unknown, [])


class CatalogShapeTests(unittest.TestCase):
    def test_rule_id_prefix_names_the_phase(self) -> None:
        for rule in RULES:
            with self.subTest(rule=rule.id):
                self.assertEqual(rule.phase, PHASE_BY_PREFIX[rule.id.split(".", 1)[0]])

    def test_finding_texts_are_unambiguous_within_a_phase(self) -> None:
        # infer_rule_id attributes a finding by substring, so no rule's text may
        # contain another's within the same phase.
        for left in RULES:
            for right in RULES:
                if left is right or left.phase != right.phase:
                    continue
                with self.subTest(left=left.id, right=right.id):
                    self.assertNotIn(left.finding, right.finding)

    def test_each_rule_text_attributes_to_itself(self) -> None:
        for rule in RULES:
            if "曖昧語" in rule.finding:
                continue  # attributed explicitly: the emitted text carries the matched term
            with self.subTest(rule=rule.id):
                self.assertEqual(infer_rule_id(rule.phase, {"finding": rule.finding}), rule.id)

    def test_every_severity_policy_covers_both_modes(self) -> None:
        for rule in RULES:
            with self.subTest(rule=rule.id):
                self.assertEqual({item.mode for item in rule.severity_policy}, {"strict", "relaxed"})

    def test_relaxed_never_exceeds_strict(self) -> None:
        order = {"info": 0, "minor": 1, "major": 2, "blocker": 3}
        for rule in RULES:
            policy = {item.mode: item.severity for item in rule.severity_policy}
            with self.subTest(rule=rule.id):
                self.assertLessEqual(order[policy["relaxed"]], order[policy["strict"]])


if __name__ == "__main__":
    unittest.main()
