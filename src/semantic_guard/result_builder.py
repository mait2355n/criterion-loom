from __future__ import annotations

from collections.abc import Callable

from semantic_guard.models import AuditResult, Finding
from semantic_guard.rule_mapping import infer_rule_id, repair_for_finding

LogicalTraceSummaryBuilder = Callable[[dict[str, object]], dict[str, object]]


def score_from_findings(findings: list[Finding]) -> float:
    score = 1.0
    for finding in findings:
        if finding.severity == "blocker":
            score -= 0.35
        elif finding.severity == "major":
            score -= 0.18
        elif finding.severity == "minor":
            score -= 0.07
    return max(0.0, score)


def build_result(
    *,
    phase: str,
    findings: list[Finding],
    missing: list[str],
    score: float,
    details: dict[str, object],
    next_actions: list[str],
    logical_trace_summary_builder: LogicalTraceSummaryBuilder | None = None,
) -> dict[str, object]:
    _enrich_findings(phase, findings)
    if any(finding.severity == "blocker" for finding in findings):
        status = "block"
    elif any(finding.severity in {"major", "minor"} for finding in findings):
        status = "warn"
    elif findings and score < 0.75:
        status = "warn"
    else:
        status = "pass"
    enriched_details = dict(details)
    non_emitted_rules = _normalized_non_emitted_rules(
        enriched_details.get("non_emitted_rules") or enriched_details.get("suppressed_rules")
    )
    warning_class_counts = _warning_class_counts(findings)
    match_status_counts = _match_status_counts(findings)
    confidence_counts = _confidence_counts(findings)
    ambiguity_reason_counts = _ambiguity_reason_counts(findings)
    enriched_details["non_emitted_rules"] = non_emitted_rules
    enriched_details["suppressed_rules"] = non_emitted_rules
    enriched_details["suppressed_rule_counts"] = _suppressed_rule_counts(non_emitted_rules)
    enriched_details["non_emitted_rule_counts"] = _non_emitted_rule_counts(non_emitted_rules)
    enriched_details["warning_class_counts"] = warning_class_counts
    enriched_details["match_status_counts"] = match_status_counts
    enriched_details["confidence_counts"] = confidence_counts
    enriched_details["ambiguity_reason_counts"] = ambiguity_reason_counts
    enriched_details["diagnostics"] = _diagnostic_envelope(
        findings=findings,
        non_emitted_rules=non_emitted_rules,
        warning_class_counts=warning_class_counts,
        match_status_counts=match_status_counts,
        confidence_counts=confidence_counts,
        ambiguity_reason_counts=ambiguity_reason_counts,
    )
    logical_trace = enriched_details.get("logical_trace")
    if isinstance(logical_trace, dict) and logical_trace_summary_builder is not None:
        rules_evaluated = logical_trace.get("rules_evaluated", [])
        facts = logical_trace.get("facts", [])
        logical_trace_summary = logical_trace_summary_builder(logical_trace)
        enriched_details["logical_trace_summary"] = logical_trace_summary
        enriched_details["diagnostics"]["logical_trace"] = {
            "schema_version": logical_trace.get("schema_version", ""),
            "scope": logical_trace.get("scope", ""),
            "derivation_scope": logical_trace.get("derivation_scope", ""),
            "rule_count": len(rules_evaluated) if isinstance(rules_evaluated, list) else 0,
            "fact_count": len(facts) if isinstance(facts, list) else 0,
            "summary_schema_version": logical_trace_summary.get("schema_version", ""),
        }
    return AuditResult(
        phase=phase,
        status=status,
        score=score,
        findings=findings,
        missing=missing,
        next_actions=next_actions,
        details=enriched_details,
    ).as_dict()


def next_actions(findings: list[Finding], fallback: str) -> list[str]:
    if not findings:
        return []
    blockers = [finding for finding in findings if finding.severity == "blocker"]
    if blockers:
        return [blockers[0].suggested_fix or fallback]
    majors = [finding for finding in findings if finding.severity == "major"]
    if majors:
        return [majors[0].suggested_fix or fallback]
    return [fallback]


def _enrich_findings(phase: str, findings: list[Finding]) -> None:
    for finding in findings:
        if not finding.rule_id:
            finding.rule_id = infer_rule_id(phase, finding)
        if not finding.repair:
            finding.repair = repair_for_finding(finding.rule_id, finding)


def _warning_class_counts(findings: list[Finding]) -> dict[str, int]:
    counts = {"actionable": 0, "generic caution": 0, "possible false positive": 0}
    for finding in findings:
        counts[finding.warning_class] = counts.get(finding.warning_class, 0) + 1
    return counts


def _match_status_counts(findings: list[Finding]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for finding in findings:
        if finding.match_status:
            counts[finding.match_status] = counts.get(finding.match_status, 0) + 1
    return dict(sorted(counts.items()))


def _confidence_counts(findings: list[Finding]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for finding in findings:
        if finding.confidence:
            counts[finding.confidence] = counts.get(finding.confidence, 0) + 1
    return dict(sorted(counts.items()))


def _ambiguity_reason_counts(findings: list[Finding]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for finding in findings:
        for reason in finding.ambiguity_reasons:
            counts[reason] = counts.get(reason, 0) + 1
    return dict(sorted(counts.items()))


def _normalized_suppressed_rules(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _normalized_non_emitted_rules(value: object) -> list[dict[str, object]]:
    normalized = _normalized_suppressed_rules(value)
    for item in normalized:
        if "emission_status" not in item:
            item["emission_status"] = "not_applicable"
        if "match_status" not in item:
            item["match_status"] = "not_applicable" if item["emission_status"] == "not_applicable" else "matched"
    return normalized


def _suppressed_rule_counts(suppressed_rules: list[dict[str, object]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in suppressed_rules:
        rule_id = item.get("rule_id")
        if isinstance(rule_id, str) and rule_id:
            counts[rule_id] = counts.get(rule_id, 0) + 1
    return dict(sorted(counts.items()))


def _non_emitted_rule_counts(non_emitted_rules: list[dict[str, object]]) -> dict[str, object]:
    by_rule_id: dict[str, int] = {}
    by_emission_status: dict[str, int] = {}
    for item in non_emitted_rules:
        rule_id = str(item.get("rule_id", ""))
        emission_status = str(item.get("emission_status", "unknown"))
        if rule_id:
            by_rule_id[rule_id] = by_rule_id.get(rule_id, 0) + 1
        by_emission_status[emission_status] = by_emission_status.get(emission_status, 0) + 1
    return {
        "by_rule_id": dict(sorted(by_rule_id.items())),
        "by_emission_status": dict(sorted(by_emission_status.items())),
    }


def _diagnostic_envelope(
    *,
    findings: list[Finding],
    non_emitted_rules: list[dict[str, object]],
    warning_class_counts: dict[str, int],
    match_status_counts: dict[str, int],
    confidence_counts: dict[str, int],
    ambiguity_reason_counts: dict[str, int],
) -> dict[str, object]:
    return {
        "emitted_findings": {
            "count": len(findings),
            "by_category": _finding_category_counts(findings),
            "by_rule_id": _finding_rule_counts(findings),
            "warning_class_counts": warning_class_counts,
        },
        "non_emitted_rules": {
            "count": len(non_emitted_rules),
            **_non_emitted_rule_counts(non_emitted_rules),
        },
        "field_match_diagnostics": {
            "match_status_counts": match_status_counts,
            "confidence_counts": confidence_counts,
            "ambiguity_reason_counts": ambiguity_reason_counts,
        },
    }


def _finding_category_counts(findings: list[Finding]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for finding in findings:
        counts[finding.category] = counts.get(finding.category, 0) + 1
    return dict(sorted(counts.items()))


def _finding_rule_counts(findings: list[Finding]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for finding in findings:
        if finding.rule_id:
            counts[finding.rule_id] = counts.get(finding.rule_id, 0) + 1
    return dict(sorted(counts.items()))
