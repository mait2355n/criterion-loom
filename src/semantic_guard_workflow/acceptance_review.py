from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from semantic_guard_workflow.resources import resource_path
from semantic_guard_workflow.schema_validation import _review_schema_errors

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


def validate_acceptance_review_bundle(payload: object, *, strict: bool = True) -> list[str]:
    """Check schema shape, then existing completion and human-decision constraints."""
    errors = _review_schema_errors(
        payload,
        load_acceptance_review_bundle_schema(),
        diagnostic_overrides={
            (("schema_version",), "const"): f"schema_version must be {ACCEPTANCE_BUNDLE_VERSION!r}",
        },
    )
    if not isinstance(payload, Mapping):
        return errors

    decision = payload.get("final_human_decision")
    if isinstance(decision, Mapping):
        status = decision.get("status")
        if isinstance(status, str) and status in HUMAN_DECISION_VALUES:
            for key in ("decided_by", "decided_at", "rationale"):
                _require_string(errors, decision, key, prefix="final_human_decision")

    if strict:
        if not payload.get("deterministic_audits"):
            errors.append("deterministic_audits must include at least one audit in strict mode")
        if not payload.get("execution_evidence"):
            errors.append("execution_evidence must include at least one evidence item in strict mode")
        if not payload.get("human_review_points"):
            errors.append("human_review_points must include at least one question in strict mode")
    return list(dict.fromkeys(errors))


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
