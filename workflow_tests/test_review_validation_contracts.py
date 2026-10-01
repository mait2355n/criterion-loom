from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from jsonschema import Draft202012Validator

from semantic_guard_workflow.acceptance_review import (
    load_acceptance_review_bundle_schema,
    validate_acceptance_review_bundle,
)
from semantic_guard_workflow.llm_review import load_candidate_gap_review_schema, validate_candidate_gap_review
from semantic_guard_workflow.codex_exec_review import CodexExecReviewRequest, run_codex_exec_review


def _bundle() -> dict:
    return {
        "schema_version": "acceptance-review-bundle/v1",
        "original_request": "Review the guide.",
        "final_artifact": {"kind": "document", "reference": "", "summary": "Guide"},
        "deterministic_audits": [{"phase": "finish_check", "status": "pass", "summary": "Observed", "findings": [{}]}],
        "llm_reviews": [{
            "source": "reviewer", "valid": True, "review_status": "no_supplement_needed",
            "missing_aspects": [{}], "supplement_proposals": [{}], "rule_item_reviews": [{}],
            "human_decision_needed": ["Accept the guide?"],
        }],
        "adopted_supplements": [], "rejected_supplements": [], "deferred_supplements": [],
        "execution_evidence": [{"kind": "test", "command_or_reference": "receipt.json", "result": "pass", "passed": True}],
        "residual_risks": [{"risk": "Unreviewed prose", "severity": "minor", "mitigation": "Read the guide", "owner": ""}],
        "human_review_points": [{"question": "Accept?", "why_it_matters": "Human acceptance", "options": []}],
        "final_human_decision": {"status": "pending", "decided_by": "", "decided_at": "", "rationale": ""},
    }


def _review() -> dict:
    return {
        "schema_version": "candidate-gap-review/v2", "review_status": "needs_supplement",
        "missing_aspects": [{"kind": "evidence", "severity": "major", "why_it_matters": "Unverified", "supplement": "Run a check"}],
        "questionable_assumptions": [{"assumption": "Compatible", "risk": "Regression", "supplement": "Check compatibility"}],
        "possible_counter_conditions": [{"rule_id": "x", "does_not_apply_when": "Documentation only", "confidence": "medium", "reason": "Scope"}],
        "supplement_proposals": [{"target": "guide", "proposal": "Add evidence", "reason": "Verification"}],
        "human_decision_needed": ["Accept?"],
        "rule_item_reviews": [{"rule_id": "x", "inspected_items": [], "missing_items": [], "counter_condition_candidates": [], "supplement": "Review", "notes": "Observed"}],
    }


def _with_value(payload: dict, path: tuple, value: object) -> dict:
    changed = copy.deepcopy(payload)
    current = changed
    for component in path[:-1]:
        current = current[component]
    current[path[-1]] = value
    return changed


class ReviewValidationContractsTests(unittest.TestCase):
    def test_valid_controls_match_published_schemas(self) -> None:
        for payload, schema, validate in (
            (_bundle(), load_acceptance_review_bundle_schema(), validate_acceptance_review_bundle),
            (_review(), load_candidate_gap_review_schema(), validate_candidate_gap_review),
        ):
            with self.subTest(schema=schema["title"]):
                self.assertEqual(list(Draft202012Validator(schema).iter_errors(payload)), [])
                self.assertEqual(validate(payload), [])

    def test_bundle_rejects_wrong_array_element_types(self) -> None:
        paths = (
            ("deterministic_audits", 0, "findings", 0),
            ("llm_reviews", 0, "missing_aspects", 0),
            ("llm_reviews", 0, "supplement_proposals", 0),
            ("llm_reviews", 0, "rule_item_reviews", 0),
            ("llm_reviews", 0, "human_decision_needed", 0),
        )
        oracle = Draft202012Validator(load_acceptance_review_bundle_schema())
        for path in paths:
            for value in (42, None, [], True):
                payload = _with_value(_bundle(), path, value)
                with self.subTest(path=path, value=value):
                    self.assertFalse(oracle.is_valid(payload))
                    self.assertTrue(validate_acceptance_review_bundle(payload))

    def test_bundle_enum_wrong_types_return_diagnostics(self) -> None:
        paths = (
            ("deterministic_audits", 0, "status"), ("llm_reviews", 0, "review_status"),
            ("residual_risks", 0, "severity"), ("final_human_decision", "status"),
        )
        for path in paths:
            for value in ([], {}, None, 42, True):
                with self.subTest(path=path, value=value):
                    self.assertTrue(validate_acceptance_review_bundle(_with_value(_bundle(), path, value)))

    def test_review_enum_wrong_types_return_diagnostics(self) -> None:
        for path in (("review_status",), ("missing_aspects", 0, "severity"), ("possible_counter_conditions", 0, "confidence")):
            for value in ([], {}, None, 42, True):
                with self.subTest(path=path, value=value):
                    self.assertTrue(validate_candidate_gap_review(_with_value(_review(), path, value)))

    def test_review_accepts_only_schema_permitted_empty_strings(self) -> None:
        for path in (("questionable_assumptions", 0, "supplement"), ("supplement_proposals", 0, "reason"), ("rule_item_reviews", 0, "notes")):
            payload = _with_value(_review(), path, "")
            with self.subTest(path=path):
                self.assertTrue(Draft202012Validator(load_candidate_gap_review_schema()).is_valid(payload))
                self.assertEqual(validate_candidate_gap_review(payload), [])
        self.assertTrue(validate_candidate_gap_review(_with_value(_review(), ("missing_aspects", 0, "supplement"), "")))

    def test_existing_nonblank_and_human_decision_requirements_remain(self) -> None:
        self.assertTrue(validate_acceptance_review_bundle(_with_value(_bundle(), ("original_request",), "  ")))
        self.assertTrue(validate_candidate_gap_review(_with_value(_review(), ("missing_aspects", 0, "supplement"), "  ")))
        self.assertTrue(validate_acceptance_review_bundle(_with_value(_bundle(), ("final_human_decision", "status"), "accept")))

    def test_non_object_payloads_return_diagnostics(self) -> None:
        for value in (None, [], "review", 42, True):
            for validate in (validate_acceptance_review_bundle, validate_candidate_gap_review):
                with self.subTest(value=value, validate=validate.__name__):
                    self.assertTrue(validate(value))

    def test_nested_extra_and_missing_fields_remain_rejected(self) -> None:
        # Inputs are explicit negative controls: nested unknown fields and a
        # missing item field must be rejected at the same public Python boundary.
        for payload, validate, path in (
            (_bundle(), validate_acceptance_review_bundle, ("final_artifact",)),
            (_review(), validate_candidate_gap_review, ("missing_aspects", 0)),
        ):
            item = payload
            for component in path:
                item = item[component]
            item["approved"] = True
            with self.subTest(validate=validate.__name__):
                self.assertTrue(validate(payload))
                item.pop("approved")
                item.pop(next(iter(item)))
                self.assertTrue(validate(payload))

    def test_received_reviewer_enum_error_becomes_schema_mismatch(self) -> None:
        request = CodexExecReviewRequest.from_mapping({"candidate": "Review the guide.", "phase": "audit_request"})
        for payload, expected_valid in (
            (_review(), True),
            (_with_value(_review(), ("review_status",), []), False),
            (_with_value(_review(), ("missing_aspects", 0, "severity"), {}), False),
        ):
            def runner(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
                return subprocess.CompletedProcess(command, 0, stdout=json.dumps(payload), stderr="")

            with self.subTest(expected_valid=expected_valid, status=payload["review_status"]):
                result = run_codex_exec_review(request, execute=True, runner=runner)
                self.assertEqual(result.valid, expected_valid)
                self.assertEqual(result.execution_status, "valid_review" if expected_valid else "invalid_review")
                self.assertEqual(result.failure_kind, None if expected_valid else "schema_mismatch")

    def test_public_bundle_cli_reports_invalid_nested_input_as_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bundle.json"
            for payload, expected_valid in (
                (_bundle(), True),
                (_with_value(_bundle(), ("deterministic_audits", 0, "findings", 0), 42), False),
                (_with_value(_bundle(), ("final_human_decision", "status"), []), False),
            ):
                with self.subTest(payload=payload["final_human_decision"], expected_valid=expected_valid):
                    path.write_text(json.dumps(payload), encoding="utf-8")
                    result = subprocess.run(
                        [sys.executable, "-m", "semantic_guard_workflow.cli", "validate-acceptance-bundle", "--file", str(path)],
                        capture_output=True, text=True, check=False,
                    )
                    self.assertEqual(result.stderr, "")
                    output = json.loads(result.stdout)
                    self.assertEqual(output["valid"], expected_valid)
                    self.assertEqual(result.returncode, 0 if expected_valid else 1)


if __name__ == "__main__":
    unittest.main()
