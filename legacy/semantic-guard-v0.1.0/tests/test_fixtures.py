from __future__ import annotations

import json
import unittest
from pathlib import Path
from typing import Any

from semantic_guard.core import audit_diff, audit_plan, audit_request, finish_check, understand_target

FIXTURE_ROOT = Path(__file__).parent / "fixtures"


class FixtureRegressionTests(unittest.TestCase):
    def test_fixture_expectations(self) -> None:
        expected_files = sorted(FIXTURE_ROOT.rglob("*.expected.json"))
        self.assertGreater(len(expected_files), 0, "fixture expectation files must exist")

        for expected_path in expected_files:
            with self.subTest(fixture=str(expected_path.relative_to(FIXTURE_ROOT))):
                spec = _load_spec(expected_path)
                result = _run_fixture(spec, expected_path)
                _assert_expectations(self, result, spec.get("expect", {}), expected_path)


def _load_spec(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as file:
        spec = json.load(file)
    if not isinstance(spec, dict):
        raise AssertionError(f"{path}: fixture expectation must be a JSON object")
    return spec


def _fixture_text(spec: dict[str, Any], expected_path: Path) -> str:
    if "text" in spec:
        text = spec["text"]
        if not isinstance(text, str):
            raise AssertionError(f"{expected_path}: `text` must be a string")
        return text

    input_name = spec.get("input")
    if not isinstance(input_name, str):
        raise AssertionError(f"{expected_path}: `input` must point to a fixture text file")

    input_path = expected_path.parent / input_name
    if not input_path.exists():
        raise AssertionError(f"{expected_path}: missing input fixture {input_path}")
    return input_path.read_text(encoding="utf-8")


def _run_fixture(spec: dict[str, Any], expected_path: Path) -> dict[str, Any]:
    phase = spec.get("phase")
    text = _fixture_text(spec, expected_path)
    strict = bool(spec.get("strict", True))
    context = str(spec.get("context", ""))

    if phase == "understand_target":
        return understand_target(text, context=context, strict=strict)
    if phase == "audit_request":
        return audit_request(text, context=context, strict=strict, input_kind=str(spec.get("kind", "requirement")))
    if phase == "audit_plan":
        return audit_plan(
            text,
            request=str(spec.get("request", "")),
            context=context,
            strict=strict,
            input_kind=str(spec.get("kind", "plan")),
        )
    if phase == "audit_diff":
        return audit_diff(
            text,
            intent=str(spec.get("intent", "")),
            context=context,
            strict=strict,
            input_kind=str(spec.get("kind", "diff-summary")),
        )
    if phase == "finish_check":
        return finish_check(text, evidence=str(spec.get("evidence", "")), context=context, strict=strict)

    raise AssertionError(f"{expected_path}: unsupported fixture phase {phase!r}")


def _assert_expectations(
    case: unittest.TestCase,
    result: dict[str, Any],
    expect: dict[str, Any],
    expected_path: Path,
) -> None:
    if "phase" in expect:
        case.assertEqual(result["phase"], expect["phase"], f"{expected_path}: phase")
    if "status" in expect:
        case.assertEqual(result["status"], expect["status"], f"{expected_path}: status")
    if "score" in expect:
        _assert_score(case, float(result["score"]), expect["score"], expected_path)

    categories = {finding["category"] for finding in result["findings"]}
    _assert_members(case, categories, expect.get("categories", {}), "categories", expected_path)
    _assert_members(case, set(result["missing"]), expect.get("missing", {}), "missing", expected_path)
    _assert_details(case, result["details"], expect.get("details", {}), expected_path)


def _assert_score(
    case: unittest.TestCase,
    actual: float,
    expectation: Any,
    expected_path: Path,
) -> None:
    if isinstance(expectation, dict):
        if "min" in expectation:
            case.assertGreaterEqual(actual, float(expectation["min"]), f"{expected_path}: score min")
        if "max" in expectation:
            case.assertLessEqual(actual, float(expectation["max"]), f"{expected_path}: score max")
        return
    case.assertEqual(actual, float(expectation), f"{expected_path}: score")


def _assert_members(
    case: unittest.TestCase,
    actual: set[str],
    expectation: Any,
    label: str,
    expected_path: Path,
) -> None:
    if not expectation:
        return
    includes = expectation.get("includes", [])
    excludes = expectation.get("excludes", [])
    for item in includes:
        case.assertIn(item, actual, f"{expected_path}: expected {label} to include {item!r}; actual={sorted(actual)}")
    for item in excludes:
        case.assertNotIn(item, actual, f"{expected_path}: expected {label} to exclude {item!r}; actual={sorted(actual)}")


def _assert_details(
    case: unittest.TestCase,
    details: dict[str, Any],
    expectation: Any,
    expected_path: Path,
) -> None:
    if not expectation:
        return
    for key, expected_value in expectation.items():
        case.assertIn(key, details, f"{expected_path}: details missing {key!r}")
        if key == "claim_triples":
            _assert_claim_triples(case, details[key], expected_value, expected_path)
        else:
            case.assertEqual(details[key], expected_value, f"{expected_path}: details.{key}")


def _assert_claim_triples(
    case: unittest.TestCase,
    triples: Any,
    expectation: Any,
    expected_path: Path,
) -> None:
    case.assertIsInstance(triples, list, f"{expected_path}: details.claim_triples must be a list")
    if "min_count" in expectation:
        case.assertGreaterEqual(len(triples), int(expectation["min_count"]), f"{expected_path}: claim_triples min_count")

    any_expectations = expectation.get("any", [])
    if isinstance(any_expectations, dict):
        any_expectations = [any_expectations]

    for partial in any_expectations:
        case.assertTrue(
            any(_matches_partial(triple, partial) for triple in triples),
            f"{expected_path}: no claim triple matched {partial!r}; actual={triples!r}",
        )


def _matches_partial(actual: dict[str, Any], partial: dict[str, Any]) -> bool:
    for key, expected in partial.items():
        if key == "claim_contains":
            if str(expected) not in str(actual.get("claim", "")):
                return False
            continue
        if actual.get(key) != expected:
            return False
    return True


if __name__ == "__main__":
    unittest.main()
