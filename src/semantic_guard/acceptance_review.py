from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from semantic_guard.resources import resource_path

ACCEPTANCE_BUNDLE_VERSION = "acceptance-review-bundle/v1"
FINAL_DECISIONS = {"pending", "accept", "request_revision", "defer"}
HUMAN_DECISION_VALUES = {"accept", "request_revision", "defer"}
AUDIT_STATUSES = {"pass", "warn", "block"}
REVIEW_STATUSES = {"no_supplement_needed", "needs_supplement", "blocked_by_missing_context"}
SEVERITIES = {"blocker", "major", "minor", "info"}
SCHEMA_FILE = resource_path("schemas", "acceptance-review-bundle.schema.json")


def acceptance_review_bundle_schema_path() -> Path:
    return SCHEMA_FILE


def load_acceptance_review_bundle_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_FILE.read_text(encoding="utf-8"))


def build_acceptance_review_bundle_template(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": ACCEPTANCE_BUNDLE_VERSION,
        "original_request": _optional_string(payload, "original_request", "request"),
        "final_artifact": _artifact_from_payload(payload.get("final_artifact")),
        "deterministic_audits": _list_of_mappings(payload.get("deterministic_audits", []), "deterministic_audits"),
        "llm_reviews": _normalized_llm_reviews(payload.get("llm_reviews", [])),
        "adopted_supplements": _list_of_mappings(payload.get("adopted_supplements", []), "adopted_supplements"),
        "rejected_supplements": _list_of_mappings(payload.get("rejected_supplements", []), "rejected_supplements"),
        "deferred_supplements": _list_of_mappings(payload.get("deferred_supplements", []), "deferred_supplements"),
        "execution_evidence": _list_of_mappings(payload.get("execution_evidence", []), "execution_evidence"),
        "residual_risks": _list_of_mappings(payload.get("residual_risks", []), "residual_risks"),
        "human_review_points": _list_of_mappings(payload.get("human_review_points", []), "human_review_points"),
        "final_human_decision": _final_decision_from_payload(payload.get("final_human_decision")),
    }


def validate_acceptance_review_bundle(payload: Mapping[str, Any], *, strict: bool = True) -> list[str]:
    errors: list[str] = []
    allowed = {
        "schema_version",
        "original_request",
        "final_artifact",
        "deterministic_audits",
        "llm_reviews",
        "adopted_supplements",
        "rejected_supplements",
        "deferred_supplements",
        "execution_evidence",
        "residual_risks",
        "human_review_points",
        "final_human_decision",
    }
    for key in sorted(allowed):
        if key not in payload:
            errors.append(f"missing required field: {key}")
    for key in sorted(set(payload) - allowed):
        errors.append(f"unexpected field: {key}")

    if payload.get("schema_version") != ACCEPTANCE_BUNDLE_VERSION:
        errors.append(f"schema_version must be {ACCEPTANCE_BUNDLE_VERSION!r}")
    _require_string(errors, payload, "original_request")
    _validate_artifact(errors, payload.get("final_artifact"))
    _validate_deterministic_audits(errors, payload.get("deterministic_audits"))
    _validate_llm_reviews(errors, payload.get("llm_reviews"))
    _validate_supplements(errors, payload.get("adopted_supplements"), "adopted_supplements", deferred=False)
    _validate_supplements(errors, payload.get("rejected_supplements"), "rejected_supplements", deferred=False)
    _validate_supplements(errors, payload.get("deferred_supplements"), "deferred_supplements", deferred=True)
    _validate_execution_evidence(errors, payload.get("execution_evidence"))
    _validate_residual_risks(errors, payload.get("residual_risks"))
    _validate_human_review_points(errors, payload.get("human_review_points"))
    _validate_final_decision(errors, payload.get("final_human_decision"))

    if strict:
        if not payload.get("deterministic_audits"):
            errors.append("deterministic_audits must include at least one audit in strict mode")
        if not payload.get("execution_evidence"):
            errors.append("execution_evidence must include at least one evidence item in strict mode")
        if not payload.get("human_review_points"):
            errors.append("human_review_points must include at least one question in strict mode")
    return errors


def _artifact_from_payload(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return {
            "kind": _string_value(value.get("kind")),
            "reference": _string_value(value.get("reference")),
            "summary": _string_value(value.get("summary")),
        }
    return {"kind": "", "reference": "", "summary": ""}


def _final_decision_from_payload(value: Any) -> dict[str, str]:
    if isinstance(value, Mapping):
        status = _string_value(value.get("status")) or "pending"
        return {
            "status": status,
            "decided_by": _string_value(value.get("decided_by")),
            "decided_at": _string_value(value.get("decided_at")),
            "rationale": _string_value(value.get("rationale")),
        }
    return {"status": "pending", "decided_by": "", "decided_at": "", "rationale": ""}


def _normalized_llm_reviews(value: Any) -> list[dict[str, Any]]:
    reviews = _list_of_mappings(value, "llm_reviews")
    normalized: list[dict[str, Any]] = []
    for review in reviews:
        if "review" in review and isinstance(review.get("review"), Mapping):
            source = _string_value(review.get("source")) or "codex_exec"
            valid = bool(review.get("valid"))
            review_payload = review["review"]
            normalized.append(
                {
                    "source": source,
                    "valid": valid,
                    "review_status": _string_value(review_payload.get("review_status")),
                    "missing_aspects": list(review_payload.get("missing_aspects", [])),
                    "supplement_proposals": list(review_payload.get("supplement_proposals", [])),
                    "rule_item_reviews": list(review_payload.get("rule_item_reviews", [])),
                    "human_decision_needed": list(review_payload.get("human_decision_needed", [])),
                }
            )
        else:
            normalized.append(dict(review))
    return normalized


def _validate_artifact(errors: list[str], value: Any) -> None:
    if not isinstance(value, Mapping):
        errors.append("final_artifact must be an object")
        return
    _allowed_keys(errors, value, "final_artifact", {"kind", "reference", "summary"})
    _require_string(errors, value, "kind", prefix="final_artifact")
    _require_string(errors, value, "summary", prefix="final_artifact")
    if "reference" not in value or not isinstance(value.get("reference"), str):
        errors.append("final_artifact.reference must be a string")


def _validate_deterministic_audits(errors: list[str], value: Any) -> None:
    for index, item in _iter_object_array(errors, value, "deterministic_audits"):
        _allowed_keys(errors, item, f"deterministic_audits[{index}]", {"phase", "status", "summary", "findings"})
        _require_string(errors, item, "phase", prefix=f"deterministic_audits[{index}]")
        _require_string(errors, item, "summary", prefix=f"deterministic_audits[{index}]")
        if item.get("status") not in AUDIT_STATUSES:
            errors.append(f"deterministic_audits[{index}].status must be one of {sorted(AUDIT_STATUSES)}")
        if not isinstance(item.get("findings"), list):
            errors.append(f"deterministic_audits[{index}].findings must be an array")


def _validate_llm_reviews(errors: list[str], value: Any) -> None:
    forbidden = {"approved", "rejected", "accepted", "final_decision", "verdict"}
    allowed = {"source", "valid", "review_status", "missing_aspects", "supplement_proposals", "rule_item_reviews", "human_decision_needed"}
    for index, item in _iter_object_array(errors, value, "llm_reviews"):
        _allowed_keys(errors, item, f"llm_reviews[{index}]", allowed)
        for key in sorted(forbidden & set(item)):
            errors.append(f"llm_reviews[{index}] must not include decision field: {key}")
        _require_string(errors, item, "source", prefix=f"llm_reviews[{index}]")
        if not isinstance(item.get("valid"), bool):
            errors.append(f"llm_reviews[{index}].valid must be a boolean")
        if item.get("review_status") not in REVIEW_STATUSES:
            errors.append(f"llm_reviews[{index}].review_status must be one of {sorted(REVIEW_STATUSES)}")
        for key in ("missing_aspects", "supplement_proposals", "rule_item_reviews", "human_decision_needed"):
            if not isinstance(item.get(key), list):
                errors.append(f"llm_reviews[{index}].{key} must be an array")


def _validate_supplements(errors: list[str], value: Any, key: str, *, deferred: bool) -> None:
    required = {"source", "target", "supplement", "reason", "decision_needed"} if deferred else {"source", "target", "supplement", "reason", "evidence"}
    for index, item in _iter_object_array(errors, value, key):
        _allowed_keys(errors, item, f"{key}[{index}]", required)
        for field in sorted(required):
            if field == "evidence":
                if not isinstance(item.get(field), str):
                    errors.append(f"{key}[{index}].{field} must be a string")
                continue
            _require_string(errors, item, field, prefix=f"{key}[{index}]")


def _validate_execution_evidence(errors: list[str], value: Any) -> None:
    for index, item in _iter_object_array(errors, value, "execution_evidence"):
        _allowed_keys(errors, item, f"execution_evidence[{index}]", {"kind", "command_or_reference", "result", "passed"})
        for field in ("kind", "command_or_reference", "result"):
            _require_string(errors, item, field, prefix=f"execution_evidence[{index}]")
        if not isinstance(item.get("passed"), bool):
            errors.append(f"execution_evidence[{index}].passed must be a boolean")


def _validate_residual_risks(errors: list[str], value: Any) -> None:
    for index, item in _iter_object_array(errors, value, "residual_risks"):
        _allowed_keys(errors, item, f"residual_risks[{index}]", {"risk", "severity", "mitigation", "owner"})
        _require_string(errors, item, "risk", prefix=f"residual_risks[{index}]")
        _require_string(errors, item, "mitigation", prefix=f"residual_risks[{index}]")
        if not isinstance(item.get("owner"), str):
            errors.append(f"residual_risks[{index}].owner must be a string")
        if item.get("severity") not in SEVERITIES:
            errors.append(f"residual_risks[{index}].severity must be one of {sorted(SEVERITIES)}")


def _validate_human_review_points(errors: list[str], value: Any) -> None:
    for index, item in _iter_object_array(errors, value, "human_review_points"):
        _allowed_keys(errors, item, f"human_review_points[{index}]", {"question", "why_it_matters", "options"})
        _require_string(errors, item, "question", prefix=f"human_review_points[{index}]")
        _require_string(errors, item, "why_it_matters", prefix=f"human_review_points[{index}]")
        options = item.get("options")
        if not isinstance(options, list) or any(not isinstance(option, str) or not option.strip() for option in options):
            errors.append(f"human_review_points[{index}].options must be an array of non-empty strings")


def _validate_final_decision(errors: list[str], value: Any) -> None:
    if not isinstance(value, Mapping):
        errors.append("final_human_decision must be an object")
        return
    _allowed_keys(errors, value, "final_human_decision", {"status", "decided_by", "decided_at", "rationale"})
    status = value.get("status")
    if status not in FINAL_DECISIONS:
        errors.append(f"final_human_decision.status must be one of {sorted(FINAL_DECISIONS)}")
    if status in HUMAN_DECISION_VALUES:
        for key in ("decided_by", "decided_at", "rationale"):
            _require_string(errors, value, key, prefix="final_human_decision")
    else:
        for key in ("decided_by", "decided_at", "rationale"):
            if not isinstance(value.get(key), str):
                errors.append(f"final_human_decision.{key} must be a string")


def _iter_object_array(errors: list[str], value: Any, key: str) -> list[tuple[int, Mapping[str, Any]]]:
    if not isinstance(value, list):
        errors.append(f"{key} must be an array")
        return []
    result: list[tuple[int, Mapping[str, Any]]] = []
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            errors.append(f"{key}[{index}] must be an object")
            continue
        result.append((index, item))
    return result


def _allowed_keys(errors: list[str], item: Mapping[str, Any], prefix: str, allowed: set[str]) -> None:
    for key in sorted(set(item) - allowed):
        errors.append(f"{prefix} has unexpected field: {key}")
    for key in sorted(allowed):
        if key not in item:
            errors.append(f"{prefix} missing required field: {key}")


def _require_string(errors: list[str], item: Mapping[str, Any], key: str, *, prefix: str = "") -> None:
    label = f"{prefix}.{key}" if prefix else key
    value = item.get(key)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label} must be a non-empty string")


def _optional_string(payload: Mapping[str, Any], *keys: str) -> str:
    for key in keys:
        if key in payload:
            return _string_value(payload.get(key))
    return ""


def _string_value(value: Any) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError("expected string value")
    return value


def _list_of_mappings(value: Any, key: str) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"`{key}` must be an array")
    result: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            raise ValueError(f"`{key}[{index}]` must be an object")
        result.append(dict(item))
    return result
