import copy
import json
import subprocess
import unittest

from jsonschema import Draft202012Validator

from semantic_guard_workflow.codex_exec_exploration import (
    CodexExecExplorationRequest,
    run_codex_exec_exploration,
)
from semantic_guard_workflow.request_exploration_review import (
    RequestExplorationInput,
    load_request_exploration_review_schema,
    validate_request_exploration_review,
)
from workflow_tests.test_request_exploration_review import VALID_EXPLORATION


OBJECT_GROUPS = (
    "extracted_information",
    "audience_hypotheses",
    "material_ambiguities",
    "questions",
    "spec_outline",
)
NONEMPTY_STRINGS = {
    "extracted_information": ("kind", "content"),
    "audience_hypotheses": ("id", "label"),
    "material_ambiguities": ("id", "category", "why_material", "question"),
    "questions": ("id", "question", "why"),
    "spec_outline": ("id", "title"),
}
EMPTY_ALLOWED_STRINGS = {
    "extracted_information": ("source",),
    "audience_hypotheses": ("evidence",),
    "material_ambiguities": ("evidence", "answer_shape"),
    "questions": ("answer_shape",),
}
STRING_ARRAYS = {
    "audience_hypotheses": ("scope_implications",),
    "material_ambiguities": ("known_information", "missing_information", "affects"),
    "questions": ("affects",),
    "spec_outline": ("known", "missing"),
}
ENUM_FIELDS = {
    "extracted_information": {
        "status": ("fact", "inference", "hypothesis", "unknown", "pending_decision"),
        "confidence": ("low", "medium", "high"),
    },
    "audience_hypotheses": {"confidence": ("low", "medium", "high")},
    "material_ambiguities": {"severity": ("blocker", "major", "minor", "info")},
    "questions": {"priority": ("must_ask", "ask_if_time", "defer")},
}


class ExplorationSchemaConformanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.schema_validator = Draft202012Validator(load_request_exploration_review_schema())

    def assert_invalid(self, payload: object) -> None:
        # The fixtures have explicit invalid expectations; the schema comparison
        # also detects accidental drift between that expectation and the contract.
        self.assertFalse(self.schema_validator.is_valid(payload))
        self.assertTrue(validate_request_exploration_review(payload))

    def assert_valid(self, payload: object) -> None:
        self.assertTrue(self.schema_validator.is_valid(payload))
        self.assertEqual(validate_request_exploration_review(payload), [])

    def test_observed_invalid_information_is_rejected(self) -> None:
        payload = copy.deepcopy(VALID_EXPLORATION)
        payload["extracted_information"][0].update(
            kind=123, content=None, source=False, final_decision="accept"
        )

        self.assertEqual(len(list(self.schema_validator.iter_errors(payload))), 4)
        self.assert_invalid(payload)

    def test_all_object_groups_reject_extra_and_missing_fields(self) -> None:
        for group in OBJECT_GROUPS:
            with self.subTest(group=group, mutation="extra authority"):
                payload = copy.deepcopy(VALID_EXPLORATION)
                payload[group][0]["final_decision"] = "accept"
                self.assert_invalid(payload)
            for field in VALID_EXPLORATION[group][0]:
                with self.subTest(group=group, missing=field):
                    payload = copy.deepcopy(VALID_EXPLORATION)
                    del payload[group][0][field]
                    self.assert_invalid(payload)

    def test_object_groups_reject_non_arrays_and_non_objects(self) -> None:
        for group in OBJECT_GROUPS:
            for value in (None, False, 1, "object", {}):
                for wrapped in (False, True):
                    if wrapped and isinstance(value, dict):
                        continue
                    with self.subTest(group=group, value=value, wrapped=wrapped):
                        payload = copy.deepcopy(VALID_EXPLORATION)
                        payload[group] = [value] if wrapped else value
                        self.assert_invalid(payload)

    def test_string_fields_reject_other_json_types(self) -> None:
        for fields_by_group in (NONEMPTY_STRINGS, EMPTY_ALLOWED_STRINGS, ENUM_FIELDS):
            for group, fields in fields_by_group.items():
                for field in fields:
                    for value in (None, False, 123, [], {}):
                        with self.subTest(group=group, field=field, value=value):
                            payload = copy.deepcopy(VALID_EXPLORATION)
                            payload[group][0][field] = value
                            self.assert_invalid(payload)

    def test_min_length_rejects_empty_strings(self) -> None:
        for group, fields in NONEMPTY_STRINGS.items():
            for field in fields:
                with self.subTest(group=group, field=field):
                    payload = copy.deepcopy(VALID_EXPLORATION)
                    payload[group][0][field] = ""
                    self.assert_invalid(payload)

    def test_string_arrays_reject_wrong_containers_and_members(self) -> None:
        paths = [(None, "non_decisions"), (None, "limits")]
        paths.extend((group, field) for group, fields in STRING_ARRAYS.items() for field in fields)
        for group, field in paths:
            for value in (None, False, 1, "array", {}, ["known", None], [False], [{}], [[]]):
                with self.subTest(group=group, field=field, value=value):
                    payload = copy.deepcopy(VALID_EXPLORATION)
                    target = payload if group is None else payload[group][0]
                    target[field] = value
                    self.assert_invalid(payload)

    def test_boolean_field_rejects_non_booleans(self) -> None:
        for value in (None, 0, 1, "true", [], {}):
            with self.subTest(value=value):
                payload = copy.deepcopy(VALID_EXPLORATION)
                payload["spec_outline"][0]["required"] = value
                self.assert_invalid(payload)

    def test_enumerations_reject_unknown_values(self) -> None:
        for group, fields in ENUM_FIELDS.items():
            for field in fields:
                with self.subTest(group=group, field=field):
                    payload = copy.deepcopy(VALID_EXPLORATION)
                    payload[group][0][field] = "not_a_declared_value"
                    self.assert_invalid(payload)
        for field in ("schema_version", "exploration_status"):
            for value in (None, False, 1, [], {}, "not_a_declared_value"):
                with self.subTest(field=field, value=value):
                    payload = copy.deepcopy(VALID_EXPLORATION)
                    payload[field] = value
                    self.assert_invalid(payload)

    def test_legal_empty_strings_arrays_and_whitespace_remain_valid(self) -> None:
        payload = copy.deepcopy(VALID_EXPLORATION)
        for group, fields in NONEMPTY_STRINGS.items():
            for field in fields:
                payload[group][0][field] = " "
        for group, fields in EMPTY_ALLOWED_STRINGS.items():
            for field in fields:
                payload[group][0][field] = ""
        for group, fields in STRING_ARRAYS.items():
            for field in fields:
                payload[group][0][field] = []
        payload["spec_outline"][0]["required"] = False
        payload["non_decisions"] = [""]
        payload["limits"] = []
        self.assert_valid(payload)

        for group in OBJECT_GROUPS:
            payload[group] = []
        self.assert_valid(payload)

    def test_all_declared_enum_values_remain_valid(self) -> None:
        for group, fields in ENUM_FIELDS.items():
            for field, values in fields.items():
                for value in values:
                    with self.subTest(group=group, field=field, value=value):
                        payload = copy.deepcopy(VALID_EXPLORATION)
                        payload[group][0][field] = value
                        self.assert_valid(payload)
        payload = copy.deepcopy(VALID_EXPLORATION)
        payload["exploration_status"] = "blocked_by_missing_context"
        self.assert_valid(payload)

    def test_top_level_malformed_json_values_return_errors(self) -> None:
        for value in (None, False, 1, "object", []):
            with self.subTest(value=value):
                self.assert_invalid(value)

    def test_top_level_diagnostics_preserve_every_missing_and_extra_field(self) -> None:
        payload = {"decision": "accept", "authorization": True}

        errors = validate_request_exploration_review(payload)

        for field in VALID_EXPLORATION:
            self.assertIn(f"missing required field: {field}", errors)
        self.assertIn("unexpected field: decision", errors)
        self.assertIn("unexpected field: authorization", errors)
        self.assertEqual(len(errors), len(set(errors)))

    def test_runtime_rejects_nested_authority_fields_without_publishing_payload(self) -> None:
        request = CodexExecExplorationRequest(RequestExplorationInput(text="仕様化前の情報を抽出する"))
        for group in OBJECT_GROUPS:
            with self.subTest(group=group):
                payload = copy.deepcopy(VALID_EXPLORATION)
                payload[group][0]["final_decision"] = "accept"

                def runner(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
                    return subprocess.CompletedProcess(command, 0, stdout=json.dumps(payload), stderr="")

                result = run_codex_exec_exploration(request, execute=True, runner=runner)

                self.assertTrue(result.executed)
                self.assertFalse(result.valid)
                self.assertEqual(result.execution_status, "invalid_exploration")
                self.assertEqual(result.failure_kind, "schema_mismatch")
                self.assertIsNone(result.exploration)
                self.assertTrue(result.errors)

    def test_runtime_rejects_invalid_types_as_schema_errors(self) -> None:
        request = CodexExecExplorationRequest(RequestExplorationInput(text="仕様化前の情報を抽出する"))
        cases = (
            (None, "exploration_status", []),
            ("extracted_information", "status", {}),
            ("extracted_information", "content", None),
            ("extracted_information", "source", False),
        )
        for group, field, value in cases:
            with self.subTest(group=group, field=field, value=value):
                payload = copy.deepcopy(VALID_EXPLORATION)
                target = payload if group is None else payload[group][0]
                target[field] = value

                def runner(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
                    return subprocess.CompletedProcess(command, 0, stdout=json.dumps(payload), stderr="")

                result = run_codex_exec_exploration(request, execute=True, runner=runner)

                self.assertFalse(result.valid)
                self.assertEqual(result.execution_status, "invalid_exploration")
                self.assertEqual(result.failure_kind, "schema_mismatch")
                self.assertIsNone(result.exploration)
                self.assertTrue(result.errors)


if __name__ == "__main__":
    unittest.main()
