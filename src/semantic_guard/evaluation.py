from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from semantic_guard.core import audit_diff, audit_plan, audit_request, finish_check, understand_target
from semantic_guard.resources import resource_path
from semantic_guard.rule_mapping import enrich_finding_mapping
from semantic_guard.rules import RULES

DEFAULT_FIXTURE_ROOT = resource_path("tests", "fixtures")


def evaluate_fixture_tree(root: str | Path = DEFAULT_FIXTURE_ROOT, include_passed: bool = False) -> dict[str, object]:
    fixture_root = Path(root)
    expected_files = sorted(fixture_root.rglob("*.expected.json"))
    results = [evaluate_fixture(path, fixture_root) for path in expected_files]
    failures = [result for result in results if not result["passed"]]
    phase_counts = _count_by(results, "phase")
    actual_status_counts = _count_by(results, "actual_status")
    expected_status_counts = _count_by(results, "expected_status")

    returned_results = results if include_passed else failures
    return {
        "fixture_root": str(fixture_root),
        "total": len(results),
        "passed": len(results) - len(failures),
        "failed": len(failures),
        "pass_rate": round((len(results) - len(failures)) / len(results), 3) if results else 0.0,
        "phase_counts": phase_counts,
        "expected_status_counts": expected_status_counts,
        "actual_status_counts": actual_status_counts,
        "metrics": _aggregate_metrics(results),
        "rule_catalog_coverage": _rule_catalog_coverage(results),
        "results": returned_results,
    }


def evaluate_fixture(expected_path: str | Path, fixture_root: str | Path | None = None) -> dict[str, object]:
    path = Path(expected_path)
    root = Path(fixture_root) if fixture_root is not None else path.parent
    fixture_label = _relative_label(path, root)
    try:
        spec = _load_spec(path)
        result = _run_fixture(spec, path)
        issues = _expectation_issues(result, spec.get("expect", {}))
        labels = _evaluate_labels(result, spec.get("labels", {}))
        issues.extend(labels["issues"])
        phase = str(spec.get("phase", ""))
        expected_status = _expected_status(spec.get("expect", {}))
        actual_status = str(result.get("status", ""))
        actual_findings = [
            enrich_finding_mapping(phase, finding)
            for finding in result.get("findings", [])
            if isinstance(finding, dict)
        ]
        actual_categories = sorted(
            {str(finding.get("category", "")) for finding in actual_findings}
        )
        actual_missing = sorted(map(str, result.get("missing", [])))
        actual_rule_ids = sorted({str(finding.get("rule_id", "")) for finding in actual_findings if finding.get("rule_id")})
        actual_match_statuses = sorted(
            {str(finding.get("match_status", "")) for finding in actual_findings if finding.get("match_status")}
        )
        actual_confidences = sorted(
            {str(finding.get("confidence", "")) for finding in actual_findings if finding.get("confidence")}
        )
        actual_ambiguity_reasons = sorted(
            {
                str(reason)
                for finding in actual_findings
                for reason in finding.get("ambiguity_reasons", [])
                if isinstance(reason, str)
            }
        )
        actual_derivations = _finding_derivations(result)
        actual_derivation_rule_ids = sorted({str(derivation.get("rule_id", "")) for derivation in actual_derivations if derivation.get("rule_id")})
        actual_derivation_statuses = sorted({str(derivation.get("status", "")) for derivation in actual_derivations if derivation.get("status")})
        actual_logical_trace_rule_ids = _logical_trace_rule_ids(result)
        actual_logical_trace_summary_rule_ids = _logical_trace_summary_rule_ids(result)
        fixture_rule_labels = _fixture_rule_labels(spec.get("labels", {}))
    except Exception as exc:  # noqa: BLE001 - fixture evaluation should report bad fixtures as data.
        spec = {}
        labels = _empty_label_report()
        issues = [{"check": "fixture.error", "expected": "valid fixture", "actual": str(exc)}]
        phase = ""
        expected_status = ""
        actual_status = ""
        actual_categories = []
        actual_missing = []
        actual_rule_ids = []
        actual_match_statuses = []
        actual_confidences = []
        actual_ambiguity_reasons = []
        actual_derivation_rule_ids = []
        actual_derivation_statuses = []
        actual_logical_trace_rule_ids = []
        actual_logical_trace_summary_rule_ids = []
        fixture_rule_labels = {"expected": [], "forbidden": []}

    return {
        "fixture": fixture_label,
        "id": str(spec.get("id", "")),
        "title": str(spec.get("title", "")),
        "phase": phase,
        "expected_status": expected_status,
        "actual_status": actual_status,
        "actual_categories": actual_categories,
        "actual_missing": actual_missing,
        "actual_rule_ids": actual_rule_ids,
        "actual_match_statuses": actual_match_statuses,
        "actual_confidences": actual_confidences,
        "actual_ambiguity_reasons": actual_ambiguity_reasons,
        "actual_derivation_rule_ids": actual_derivation_rule_ids,
        "actual_derivation_statuses": actual_derivation_statuses,
        "actual_logical_trace_rule_ids": actual_logical_trace_rule_ids,
        "actual_logical_trace_summary_rule_ids": actual_logical_trace_summary_rule_ids,
        "fixture_rule_labels": fixture_rule_labels,
        "labels": labels["summary"],
        "label_metrics": labels["metrics"],
        "passed": not issues,
        "issues": issues,
    }


def _load_spec(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as file:
        spec = json.load(file)
    if not isinstance(spec, dict):
        raise ValueError("fixture expectation must be a JSON object")
    return spec


def _fixture_text(spec: dict[str, Any], expected_path: Path) -> str:
    if "text" in spec:
        text = spec["text"]
        if not isinstance(text, str):
            raise ValueError("`text` must be a string")
        return text

    input_name = spec.get("input")
    if not isinstance(input_name, str):
        raise ValueError("`input` must point to a fixture text file when `text` is absent")

    input_path = expected_path.parent / input_name
    if not input_path.exists():
        raise ValueError(f"missing input fixture {input_path}")
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

    raise ValueError(f"unsupported fixture phase {phase!r}")


def _expectation_issues(result: dict[str, Any], expect: Any) -> list[dict[str, object]]:
    if not isinstance(expect, dict):
        return [{"check": "expect", "expected": "object", "actual": type(expect).__name__}]

    issues: list[dict[str, object]] = []
    _compare_scalar(issues, "phase", expect, result)
    _compare_scalar(issues, "status", expect, result)
    if "score" in expect:
        _compare_score(issues, float(result.get("score", 0.0)), expect["score"])

    categories = {str(finding.get("category", "")) for finding in result.get("findings", []) if isinstance(finding, dict)}
    _compare_members(issues, "categories", categories, expect.get("categories", {}))
    _compare_members(issues, "missing", set(map(str, result.get("missing", []))), expect.get("missing", {}))
    _compare_details(issues, result.get("details", {}), expect.get("details", {}))
    _compare_derivation_expectations(issues, result, expect)
    return issues


def _evaluate_labels(result: dict[str, Any], labels: Any) -> dict[str, object]:
    report = _empty_label_report()
    if not labels:
        return report
    if not isinstance(labels, dict):
        report["issues"].append({"check": "labels", "expected": "object", "actual": type(labels).__name__})
        return report

    phase = str(result.get("phase", ""))
    findings = [
        enrich_finding_mapping(phase, finding)
        for finding in result.get("findings", [])
        if isinstance(finding, dict)
    ]
    expected_findings = _label_list(report, labels, "expected_findings")
    forbidden_findings = _label_list(report, labels, "forbidden_findings")
    expected_rules = _string_list(report, labels, "expected_rules")
    forbidden_rules = _string_list(report, labels, "forbidden_rules")

    for index, spec in enumerate(expected_findings):
        matches = [finding for finding in findings if _finding_matches(finding, spec)]
        if matches:
            report["summary"]["expected_findings"]["matched"].append(_label_match_summary(index, spec, matches[0]))
            report["metrics"]["expected_finding_matched"] += 1
            report["metrics"]["true_positive"] += 1
        else:
            report["summary"]["expected_findings"]["missed"].append({"index": index, "spec": spec})
            report["metrics"]["expected_finding_missed"] += 1
            report["metrics"]["false_negative"] += 1
            report["issues"].append(
                {
                    "check": "labels.expected_findings",
                    "expected": spec,
                    "actual": "no matching finding",
                }
            )
        report["metrics"]["expected_finding_total"] += 1

    for index, spec in enumerate(forbidden_findings):
        matches = [finding for finding in findings if _finding_matches(finding, spec)]
        if matches:
            report["summary"]["forbidden_findings"]["matched"].append(_label_match_summary(index, spec, matches[0]))
            report["metrics"]["forbidden_finding_matched"] += 1
            report["metrics"]["false_positive"] += 1
            report["issues"].append(
                {
                    "check": "labels.forbidden_findings",
                    "expected": f"no finding matching {spec}",
                    "actual": _finding_summary(matches[0]),
                }
            )
        else:
            report["summary"]["forbidden_findings"]["clean"].append({"index": index, "spec": spec})
            report["metrics"]["forbidden_finding_clean"] += 1
            report["metrics"]["true_negative"] += 1
        report["metrics"]["forbidden_finding_total"] += 1

    actual_rule_ids = {str(finding.get("rule_id", "")) for finding in findings if finding.get("rule_id")}
    for rule_id in expected_rules:
        report["metrics"]["expected_rule_total"] += 1
        if rule_id in actual_rule_ids:
            report["summary"]["expected_rules"]["matched"].append(rule_id)
            report["metrics"]["expected_rule_matched"] += 1
        else:
            report["summary"]["expected_rules"]["missed"].append(rule_id)
            report["metrics"]["expected_rule_missed"] += 1
            report["issues"].append({"check": "labels.expected_rules", "expected": rule_id, "actual": sorted(actual_rule_ids)})

    for rule_id in forbidden_rules:
        report["metrics"]["forbidden_rule_total"] += 1
        if rule_id in actual_rule_ids:
            report["summary"]["forbidden_rules"]["matched"].append(rule_id)
            report["metrics"]["forbidden_rule_matched"] += 1
            report["issues"].append({"check": "labels.forbidden_rules", "expected": f"not {rule_id}", "actual": sorted(actual_rule_ids)})
        else:
            report["summary"]["forbidden_rules"]["clean"].append(rule_id)
            report["metrics"]["forbidden_rule_clean"] += 1

    _refresh_label_rates(report["metrics"])
    return report


def _empty_label_report() -> dict[str, Any]:
    return {
        "summary": {
            "expected_findings": {"matched": [], "missed": []},
            "forbidden_findings": {"clean": [], "matched": []},
            "expected_rules": {"matched": [], "missed": []},
            "forbidden_rules": {"clean": [], "matched": []},
        },
        "metrics": _empty_label_metrics(),
        "issues": [],
    }


def _empty_label_metrics() -> dict[str, int | float]:
    return {
        "expected_finding_total": 0,
        "expected_finding_matched": 0,
        "expected_finding_missed": 0,
        "forbidden_finding_total": 0,
        "forbidden_finding_clean": 0,
        "forbidden_finding_matched": 0,
        "expected_rule_total": 0,
        "expected_rule_matched": 0,
        "expected_rule_missed": 0,
        "forbidden_rule_total": 0,
        "forbidden_rule_clean": 0,
        "forbidden_rule_matched": 0,
        "true_positive": 0,
        "false_negative": 0,
        "true_negative": 0,
        "false_positive": 0,
        "expected_finding_recall": 0.0,
        "forbidden_finding_clean_rate": 0.0,
        "expected_rule_recall": 0.0,
        "forbidden_rule_clean_rate": 0.0,
    }


def _label_list(report: dict[str, Any], labels: dict[str, Any], key: str) -> list[dict[str, Any]]:
    raw_items = labels.get(key, [])
    if raw_items is None:
        return []
    if not isinstance(raw_items, list):
        report["issues"].append({"check": f"labels.{key}", "expected": "list", "actual": type(raw_items).__name__})
        return []

    items: list[dict[str, Any]] = []
    for index, item in enumerate(raw_items):
        if not isinstance(item, dict):
            report["issues"].append(
                {"check": f"labels.{key}[{index}]", "expected": "object", "actual": type(item).__name__}
            )
            continue
        items.append(item)
    return items


def _string_list(report: dict[str, Any], labels: dict[str, Any], key: str) -> list[str]:
    raw_items = labels.get(key, [])
    if raw_items is None:
        return []
    if not isinstance(raw_items, list):
        report["issues"].append({"check": f"labels.{key}", "expected": "list", "actual": type(raw_items).__name__})
        return []
    items: list[str] = []
    for index, item in enumerate(raw_items):
        if not isinstance(item, str):
            report["issues"].append(
                {"check": f"labels.{key}[{index}]", "expected": "string", "actual": type(item).__name__}
            )
            continue
        items.append(item)
    return items


def _fixture_rule_labels(labels: Any) -> dict[str, list[str]]:
    if not isinstance(labels, dict):
        return {"expected": [], "forbidden": []}
    expected = labels.get("expected_rules", [])
    forbidden = labels.get("forbidden_rules", [])
    return {
        "expected": sorted({str(item) for item in expected if isinstance(item, str)}),
        "forbidden": sorted({str(item) for item in forbidden if isinstance(item, str)}),
    }


def _finding_matches(finding: dict[str, Any], spec: dict[str, Any]) -> bool:
    exact_fields = ["severity", "category", "warning_class", "rule_id", "match_status", "confidence"]
    for field in exact_fields:
        if field in spec and str(finding.get(field, "")) != str(spec[field]):
            return False

    contains_fields = {
        "finding_contains": "finding",
        "evidence_contains": "evidence",
        "suggested_fix_contains": "suggested_fix",
    }
    for spec_key, finding_key in contains_fields.items():
        if spec_key in spec and str(spec[spec_key]) not in str(finding.get(finding_key, "")):
            return False

    if "basis_contains" in spec:
        basis = [str(item) for item in finding.get("basis", [])]
        if not any(str(spec["basis_contains"]) in item for item in basis):
            return False

    if "semantic_boundary" in spec:
        boundaries = [str(item) for item in finding.get("semantic_boundaries", [])]
        if str(spec["semantic_boundary"]) not in boundaries:
            return False

    if "nearest_candidate_contains" in spec:
        candidates = [str(item) for item in finding.get("nearest_candidates", [])]
        if not any(str(spec["nearest_candidate_contains"]) in candidate for candidate in candidates):
            return False

    if "ambiguity_reason" in spec:
        reasons = [str(item) for item in finding.get("ambiguity_reasons", [])]
        if str(spec["ambiguity_reason"]) not in reasons:
            return False

    candidate_specs = {
        "candidate_status": "status",
        "candidate_matched_by": "matched_by",
        "candidate_rejected_by": "rejected_by",
    }
    candidate_matches = [item for item in finding.get("candidate_matches", []) if isinstance(item, dict)]
    for spec_key, candidate_key in candidate_specs.items():
        if spec_key not in spec:
            continue
        expected = str(spec[spec_key])
        if not any(_candidate_value_contains(candidate, candidate_key, expected) for candidate in candidate_matches):
            return False

    return True


def _candidate_value_contains(candidate: dict[str, Any], key: str, expected: str) -> bool:
    value = candidate.get(key)
    if isinstance(value, list):
        return any(expected == str(item) for item in value)
    return expected == str(value)


def _label_match_summary(index: int, spec: dict[str, Any], finding: dict[str, Any]) -> dict[str, object]:
    return {"index": index, "spec": spec, "finding": _finding_summary(finding)}


def _finding_summary(finding: dict[str, Any]) -> dict[str, object]:
    return {
        "severity": finding.get("severity", ""),
        "category": finding.get("category", ""),
        "finding": finding.get("finding", ""),
        "warning_class": finding.get("warning_class", ""),
        "rule_id": finding.get("rule_id", ""),
        "match_status": finding.get("match_status", ""),
        "confidence": finding.get("confidence", ""),
    }


def _refresh_label_rates(metrics: dict[str, int | float]) -> None:
    expected_total = int(metrics["expected_finding_total"])
    forbidden_total = int(metrics["forbidden_finding_total"])
    metrics["expected_finding_recall"] = round(int(metrics["expected_finding_matched"]) / expected_total, 3) if expected_total else 0.0
    metrics["forbidden_finding_clean_rate"] = (
        round(int(metrics["forbidden_finding_clean"]) / forbidden_total, 3) if forbidden_total else 0.0
    )
    expected_rule_total = int(metrics["expected_rule_total"])
    forbidden_rule_total = int(metrics["forbidden_rule_total"])
    metrics["expected_rule_recall"] = round(int(metrics["expected_rule_matched"]) / expected_rule_total, 3) if expected_rule_total else 0.0
    metrics["forbidden_rule_clean_rate"] = (
        round(int(metrics["forbidden_rule_clean"]) / forbidden_rule_total, 3) if forbidden_rule_total else 0.0
    )


def _compare_scalar(issues: list[dict[str, object]], key: str, expect: dict[str, Any], result: dict[str, Any]) -> None:
    if key in expect and result.get(key) != expect[key]:
        issues.append({"check": key, "expected": expect[key], "actual": result.get(key)})


def _compare_score(issues: list[dict[str, object]], actual: float, expectation: Any) -> None:
    if isinstance(expectation, dict):
        if "min" in expectation and actual < float(expectation["min"]):
            issues.append({"check": "score.min", "expected": expectation["min"], "actual": actual})
        if "max" in expectation and actual > float(expectation["max"]):
            issues.append({"check": "score.max", "expected": expectation["max"], "actual": actual})
        return
    if actual != float(expectation):
        issues.append({"check": "score", "expected": float(expectation), "actual": actual})


def _compare_members(
    issues: list[dict[str, object]],
    label: str,
    actual: set[str],
    expectation: Any,
) -> None:
    if not expectation:
        return
    if not isinstance(expectation, dict):
        issues.append({"check": label, "expected": "object", "actual": type(expectation).__name__})
        return

    for item in expectation.get("includes", []):
        if item not in actual:
            issues.append({"check": f"{label}.includes", "expected": item, "actual": sorted(actual)})
    for item in expectation.get("excludes", []):
        if item in actual:
            issues.append({"check": f"{label}.excludes", "expected": f"not {item}", "actual": sorted(actual)})


def _compare_details(issues: list[dict[str, object]], details: Any, expectation: Any) -> None:
    if not expectation:
        return
    if not isinstance(details, dict) or not isinstance(expectation, dict):
        issues.append({"check": "details", "expected": "object", "actual": type(details).__name__})
        return

    for key, expected_value in expectation.items():
        if key not in details:
            issues.append({"check": f"details.{key}", "expected": expected_value, "actual": "<missing>"})
            continue
        if key == "claim_triples":
            _compare_claim_triples(issues, details[key], expected_value)
        elif details[key] != expected_value:
            issues.append({"check": f"details.{key}", "expected": expected_value, "actual": details[key]})


def _compare_derivation_expectations(issues: list[dict[str, object]], result: dict[str, Any], expect: dict[str, Any]) -> None:
    derivation_expectation_keys = {
        "derivation_status",
        "derivation_rule_id",
        "derivation_missing_obligation",
        "derivation_countercondition",
        "derivation_fact",
        "logical_trace_rule",
        "logical_trace_summary_rule",
        "logical_trace_unknown",
        "logical_trace_conflict",
    }
    if not derivation_expectation_keys & set(expect):
        return

    derivations = _finding_derivations(result)
    trace = _logical_trace(result)
    trace_summary = _logical_trace_summary(result)
    _expect_any_value(
        issues,
        "derivation_status",
        expect.get("derivation_status"),
        [str(derivation.get("status", "")) for derivation in derivations],
    )
    _expect_any_value(
        issues,
        "derivation_rule_id",
        expect.get("derivation_rule_id"),
        [str(derivation.get("rule_id", "")) for derivation in derivations],
    )
    _expect_any_serialized_item(
        issues,
        "derivation_missing_obligation",
        expect.get("derivation_missing_obligation"),
        [
            obligation
            for derivation in derivations
            for obligation in derivation.get("missing_obligations", [])
            if isinstance(obligation, dict)
        ],
    )
    _expect_any_serialized_item(
        issues,
        "derivation_countercondition",
        expect.get("derivation_countercondition"),
        [
            countercondition
            for derivation in derivations
            for countercondition in derivation.get("counterconditions_checked", [])
            if isinstance(countercondition, dict)
        ],
    )
    _expect_any_serialized_item(
        issues,
        "derivation_fact",
        expect.get("derivation_fact"),
        [fact for derivation in derivations for fact in derivation.get("facts_used", []) if isinstance(fact, dict)],
    )
    _expect_any_serialized_item(
        issues,
        "logical_trace_rule",
        expect.get("logical_trace_rule"),
        [rule for rule in trace.get("rules_evaluated", []) if isinstance(rule, dict)],
    )
    _expect_any_serialized_item(
        issues,
        "logical_trace_summary_rule",
        expect.get("logical_trace_summary_rule"),
        [rule for rule in trace_summary.get("rules", []) if isinstance(rule, dict)],
    )
    _expect_any_value(
        issues,
        "logical_trace_unknown",
        expect.get("logical_trace_unknown"),
        [str(item) for item in trace.get("unknowns", []) if isinstance(item, str)],
    )
    _expect_any_value(
        issues,
        "logical_trace_conflict",
        expect.get("logical_trace_conflict"),
        [str(item) for item in trace.get("conflicts", []) if isinstance(item, str)],
    )


def _expect_any_value(
    issues: list[dict[str, object]],
    key: str,
    expectation: Any,
    actual_values: list[str],
) -> None:
    if expectation is None:
        return
    for expected in _expectation_items(expectation):
        expected_text = str(expected)
        if not any(expected_text == actual or expected_text in actual for actual in actual_values):
            issues.append({"check": key, "expected": expected, "actual": sorted(actual_values)})


def _expect_any_serialized_item(
    issues: list[dict[str, object]],
    key: str,
    expectation: Any,
    actual_items: list[dict[str, Any]],
) -> None:
    if expectation is None:
        return
    serialized = [json.dumps(item, ensure_ascii=False, sort_keys=True) for item in actual_items]
    for expected in _expectation_items(expectation):
        if isinstance(expected, dict):
            if not any(_matches_partial(item, expected) for item in actual_items):
                issues.append({"check": key, "expected": expected, "actual": actual_items})
            continue
        expected_text = str(expected)
        if not any(expected_text in item for item in serialized):
            issues.append({"check": key, "expected": expected, "actual": actual_items})


def _expectation_items(expectation: Any) -> list[Any]:
    if isinstance(expectation, list):
        return expectation
    return [expectation]


def _finding_derivations(result: dict[str, Any]) -> list[dict[str, Any]]:
    derivations: list[dict[str, Any]] = []
    for finding in result.get("findings", []):
        if not isinstance(finding, dict):
            continue
        derivation = finding.get("derivation")
        if isinstance(derivation, dict):
            derivations.append(derivation)
    return derivations


def _logical_trace(result: dict[str, Any]) -> dict[str, Any]:
    details = result.get("details", {})
    if not isinstance(details, dict):
        return {}
    trace = details.get("logical_trace", {})
    return trace if isinstance(trace, dict) else {}


def _logical_trace_summary(result: dict[str, Any]) -> dict[str, Any]:
    details = result.get("details", {})
    if not isinstance(details, dict):
        return {}
    summary = details.get("logical_trace_summary", {})
    return summary if isinstance(summary, dict) else {}


def _logical_trace_rule_ids(result: dict[str, Any]) -> list[str]:
    trace = _logical_trace(result)
    return sorted(
        {
            str(rule.get("rule_id", ""))
            for rule in trace.get("rules_evaluated", [])
            if isinstance(rule, dict) and rule.get("rule_id")
        }
    )


def _logical_trace_summary_rule_ids(result: dict[str, Any]) -> list[str]:
    summary = _logical_trace_summary(result)
    return sorted(
        {
            str(rule.get("rule_id", ""))
            for rule in summary.get("rules", [])
            if isinstance(rule, dict) and rule.get("rule_id")
        }
    )


def _compare_claim_triples(issues: list[dict[str, object]], triples: Any, expectation: Any) -> None:
    if not isinstance(triples, list):
        issues.append({"check": "details.claim_triples", "expected": "list", "actual": type(triples).__name__})
        return
    if "min_count" in expectation and len(triples) < int(expectation["min_count"]):
        issues.append({"check": "details.claim_triples.min_count", "expected": expectation["min_count"], "actual": len(triples)})

    any_expectations = expectation.get("any", [])
    if isinstance(any_expectations, dict):
        any_expectations = [any_expectations]

    for partial in any_expectations:
        if not any(isinstance(triple, dict) and _matches_partial(triple, partial) for triple in triples):
            issues.append({"check": "details.claim_triples.any", "expected": partial, "actual": triples})


def _matches_partial(actual: dict[str, Any], partial: dict[str, Any]) -> bool:
    for key, expected in partial.items():
        if key == "claim_contains":
            if str(expected) not in str(actual.get("claim", "")):
                return False
            continue
        if actual.get(key) != expected:
            return False
    return True


def _expected_status(expect: Any) -> str:
    if isinstance(expect, dict):
        return str(expect.get("status", ""))
    return ""


def _count_by(results: list[dict[str, object]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for result in results:
        value = str(result.get(key, ""))
        if not value:
            value = "<unset>"
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _aggregate_metrics(results: list[dict[str, object]]) -> dict[str, object]:
    label_metrics = _empty_label_metrics()
    category_hits: dict[str, int] = {}
    missing_hits: dict[str, int] = {}
    rule_hits: dict[str, int] = {}
    match_status_hits: dict[str, int] = {}
    confidence_hits: dict[str, int] = {}
    ambiguity_reason_hits: dict[str, int] = {}
    derivation_rule_hits: dict[str, int] = {}
    derivation_status_hits: dict[str, int] = {}
    logical_trace_rule_hits: dict[str, int] = {}
    logical_trace_summary_rule_hits: dict[str, int] = {}
    status_confusion: dict[str, int] = {}

    for result in results:
        for category in result.get("actual_categories", []):
            key = str(category)
            category_hits[key] = category_hits.get(key, 0) + 1
        for missing in result.get("actual_missing", []):
            key = str(missing)
            missing_hits[key] = missing_hits.get(key, 0) + 1
        for rule_id in result.get("actual_rule_ids", []):
            key = str(rule_id)
            rule_hits[key] = rule_hits.get(key, 0) + 1
        for match_status in result.get("actual_match_statuses", []):
            key = str(match_status)
            match_status_hits[key] = match_status_hits.get(key, 0) + 1
        for confidence in result.get("actual_confidences", []):
            key = str(confidence)
            confidence_hits[key] = confidence_hits.get(key, 0) + 1
        for reason in result.get("actual_ambiguity_reasons", []):
            key = str(reason)
            ambiguity_reason_hits[key] = ambiguity_reason_hits.get(key, 0) + 1
        for rule_id in result.get("actual_derivation_rule_ids", []):
            key = str(rule_id)
            derivation_rule_hits[key] = derivation_rule_hits.get(key, 0) + 1
        for derivation_status in result.get("actual_derivation_statuses", []):
            key = str(derivation_status)
            derivation_status_hits[key] = derivation_status_hits.get(key, 0) + 1
        for rule_id in result.get("actual_logical_trace_rule_ids", []):
            key = str(rule_id)
            logical_trace_rule_hits[key] = logical_trace_rule_hits.get(key, 0) + 1
        for rule_id in result.get("actual_logical_trace_summary_rule_ids", []):
            key = str(rule_id)
            logical_trace_summary_rule_hits[key] = logical_trace_summary_rule_hits.get(key, 0) + 1

        expected_status = str(result.get("expected_status", "")) or "<unset>"
        actual_status = str(result.get("actual_status", "")) or "<unset>"
        confusion_key = f"{expected_status}->{actual_status}"
        status_confusion[confusion_key] = status_confusion.get(confusion_key, 0) + 1

        item_metrics = result.get("label_metrics", {})
        if isinstance(item_metrics, dict):
            for key, value in item_metrics.items():
                if key in {
                    "expected_finding_recall",
                    "forbidden_finding_clean_rate",
                    "expected_rule_recall",
                    "forbidden_rule_clean_rate",
                }:
                    continue
                label_metrics[key] = int(label_metrics[key]) + int(value)

    _refresh_label_rates(label_metrics)
    return {
        "label_metrics": label_metrics,
        "category_hits": dict(sorted(category_hits.items())),
        "missing_hits": dict(sorted(missing_hits.items())),
        "rule_hits": dict(sorted(rule_hits.items())),
        "match_status_hits": dict(sorted(match_status_hits.items())),
        "confidence_hits": dict(sorted(confidence_hits.items())),
        "ambiguity_reason_hits": dict(sorted(ambiguity_reason_hits.items())),
        "derivation_rule_hits": dict(sorted(derivation_rule_hits.items())),
        "derivation_status_hits": dict(sorted(derivation_status_hits.items())),
        "logical_trace_rule_hits": dict(sorted(logical_trace_rule_hits.items())),
        "logical_trace_summary_rule_hits": dict(sorted(logical_trace_summary_rule_hits.items())),
        "status_confusion": dict(sorted(status_confusion.items())),
    }


def _rule_catalog_coverage(results: list[dict[str, object]]) -> dict[str, object]:
    catalog_rule_ids = sorted(rule.id for rule in RULES)
    expected_rule_ids: set[str] = set()
    forbidden_rule_ids: set[str] = set()
    emitted_rule_ids: set[str] = set()

    for result in results:
        labels = result.get("fixture_rule_labels", {})
        if isinstance(labels, dict):
            expected_rule_ids.update(str(item) for item in labels.get("expected", []) if item)
            forbidden_rule_ids.update(str(item) for item in labels.get("forbidden", []) if item)
        emitted_rule_ids.update(str(item) for item in result.get("actual_rule_ids", []) if item)

    labeled_rule_ids = expected_rule_ids | forbidden_rule_ids
    catalog_set = set(catalog_rule_ids)
    return {
        "local_calibration_only": True,
        "catalog_rule_count": len(catalog_rule_ids),
        "fixture_expected_rule_ids": sorted(expected_rule_ids),
        "fixture_forbidden_rule_ids": sorted(forbidden_rule_ids),
        "fixture_labeled_rule_ids": sorted(labeled_rule_ids),
        "emitted_rule_ids": sorted(emitted_rule_ids),
        "unhit_rule_ids": sorted(catalog_set - labeled_rule_ids),
        "unhit_rule_count": len(catalog_set - labeled_rule_ids),
        "unemitted_rule_ids": sorted(catalog_set - emitted_rule_ids),
        "unemitted_rule_count": len(catalog_set - emitted_rule_ids),
    }


def _relative_label(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)
