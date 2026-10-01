"""Self-describing observation-only envelope for legacy shadow comparisons.

The shadow command compares two historical analysis surfaces.  Agreement,
local ``pass`` values, and classified differences are migration observations;
none is a governed verdict.  This module binds the complete vNext observation,
legacy process observation, and comparison projection into one replayable
record with an authority ceiling that survives loss of CLI or MCP call context.
"""

from __future__ import annotations

import copy
from functools import lru_cache
import hashlib
import json
from typing import Any, Mapping, Sequence

from jsonschema import Draft202012Validator, FormatChecker, ValidationError

from .legacy_runner import normalize_legacy_result
from .public_contract import validate_public_audit
from .schema_access import schema_path


SCHEMA_VERSION = "legacy-shadow-observation-envelope/v1"
_SCHEMA_PATH = schema_path("legacy-shadow-observation-envelope.schema.json")
_GOVERNANCE_STATUS = "legacy_shadow_observation_only"
_DIGEST_CANONICALIZATION = "semantic-guard-canonical-json/v1"
_DIGEST_SCOPE = "all_members_except_envelope_id_and_semantic_digest"
_ALLOWED_USE = ["migration_analysis", "compatibility_observation"]
_FORBIDDEN_USE = [
    "formal_satisfaction",
    "formal_nonconformance",
    "hold_release",
    "control_plane_disposition",
    "human_acceptance",
]
_LIMITATIONS = [
    "Nested vNext and legacy pass values are historical analysis observations and have no authority outside this envelope.",
    "Comparison agreement or classification does not establish engineering correctness, action occurrence, or field qualification.",
    "The semantic digest detects accidental change but does not authenticate origin; trusted transport or an external signature is required against deliberate resealing.",
]


class LegacyShadowObservationValidationError(ValueError):
    """Raised when a legacy shadow observation cannot be replayed safely."""

    def __init__(self, errors: Sequence[Mapping[str, str]]) -> None:
        self.errors = tuple(dict(item) for item in errors)
        self.codes = tuple(str(item["code"]) for item in self.errors)
        summary = "; ".join(
            f"{item['code']}@{item['location']}: {item['message']}"
            for item in self.errors[:8]
        )
        if len(self.errors) > 8:
            summary += f"; ... {len(self.errors) - 8} more"
        super().__init__(summary)


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def semantic_digest_value(value: Any) -> dict[str, str]:
    return {
        "algorithm": "sha256",
        "canonicalization": _DIGEST_CANONICALIZATION,
        "scope": _DIGEST_SCOPE,
        "value": hashlib.sha256(_canonical(value)).hexdigest(),
    }


def _json_copy(value: Any) -> Any:
    """Copy through canonical JSON so dataclass tuples use transport arrays."""

    return json.loads(_canonical(value))


def _semantic_material(payload: Mapping[str, Any]) -> dict[str, Any]:
    material = copy.deepcopy(dict(payload))
    material.pop("envelope_id", None)
    material.pop("semantic_digest", None)
    return material


def _envelope_id(digest: Mapping[str, str]) -> str:
    return f"legacy-shadow-observation.{digest['value']}"


@lru_cache(maxsize=1)
def _validator() -> Draft202012Validator:
    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def build_legacy_shadow_observation(
    *,
    vnext: Mapping[str, Any],
    legacy: Mapping[str, Any],
    comparison: Mapping[str, Any],
) -> dict[str, Any]:
    """Build and replay one authority-bounded legacy shadow observation."""

    material = {
        "schema_version": SCHEMA_VERSION,
        "governance_status": _GOVERNANCE_STATUS,
        "authority_scope": "observation_only",
        "formal_authority": "none",
        "positive_assurance": False,
        "allowed_use": copy.deepcopy(_ALLOWED_USE),
        "forbidden_use": copy.deepcopy(_FORBIDDEN_USE),
        "limitations": copy.deepcopy(_LIMITATIONS),
        "vnext": _json_copy(dict(vnext)),
        "legacy": _json_copy(dict(legacy)),
        "comparison": _json_copy(dict(comparison)),
    }
    digest = semantic_digest_value(material)
    result = {
        **material,
        "envelope_id": _envelope_id(digest),
        "semantic_digest": digest,
    }
    return validate_legacy_shadow_observation(result)


def _error(code: str, location: str, message: str) -> dict[str, str]:
    return {"code": code, "location": location, "message": message}


def legacy_shadow_observation_errors(
    payload: Mapping[str, Any],
) -> tuple[dict[str, str], ...]:
    errors: list[dict[str, str]] = []
    if not isinstance(payload, Mapping):
        return (
            _error(
                "schema_error",
                "$",
                "legacy shadow observation must be an object",
            ),
        )

    schema_errors = sorted(
        _validator().iter_errors(payload),
        key=lambda item: tuple(str(part) for part in item.absolute_path),
    )
    errors.extend(
        _error(
            "schema_error",
            "$"
            + "".join(
                f"[{part}]" if isinstance(part, int) else f".{part}"
                for part in item.absolute_path
            ),
            item.message,
        )
        for item in schema_errors
    )
    if schema_errors:
        return tuple(errors)

    material = _semantic_material(payload)
    expected_digest = semantic_digest_value(material)
    if payload["semantic_digest"] != expected_digest:
        errors.append(
            _error(
                "semantic_digest_mismatch",
                "$.semantic_digest",
                "legacy shadow observation digest does not replay",
            )
        )
    if payload["envelope_id"] != _envelope_id(expected_digest):
        errors.append(
            _error(
                "envelope_id_mismatch",
                "$.envelope_id",
                "legacy shadow observation identity does not replay",
            )
        )

    if (
        payload["governance_status"] != _GOVERNANCE_STATUS
        or payload["authority_scope"] != "observation_only"
        or payload["formal_authority"] != "none"
        or payload["positive_assurance"] is not False
        or payload["allowed_use"] != _ALLOWED_USE
        or payload["forbidden_use"] != _FORBIDDEN_USE
        or payload["limitations"] != _LIMITATIONS
    ):
        errors.append(
            _error(
                "authority_boundary_mismatch",
                "$",
                "legacy shadow observation authority boundary is fixed",
            )
        )

    vnext = payload["vnext"]
    try:
        validate_public_audit(vnext)
    except (KeyError, TypeError, ValueError, ValidationError) as exc:
        errors.append(
            _error(
                "vnext_observation_invalid",
                "$.vnext",
                f"nested vNext observation is not the historical public contract: {exc}",
            )
        )

    legacy = payload["legacy"]
    execution = legacy["execution"]
    raw = legacy["raw_legacy_result"]
    normalized = legacy["normalized_legacy_observation"]
    if execution["result_schema_valid"] and (
        not isinstance(raw, Mapping) or raw.get("phase") != "audit_request"
    ):
        errors.append(
            _error(
                "legacy_raw_format_mismatch",
                "$.legacy.raw_legacy_result.phase",
                "schema-valid legacy material must retain the audit_request result format",
            )
        )
    if normalized is not None:
        if raw is None or not execution["result_schema_valid"]:
            errors.append(
                _error(
                    "legacy_normalization_without_valid_source",
                    "$.legacy.normalized_legacy_observation",
                    "normalized legacy material requires a schema-valid raw legacy result",
                )
            )
        elif normalize_legacy_result(raw) != normalized:
            errors.append(
                _error(
                    "legacy_normalization_mismatch",
                    "$.legacy.normalized_legacy_observation",
                    "normalized legacy material does not replay from the raw result",
                )
            )
    if execution["status"] == "completed" and (
        execution["exit_code"] != 0
        or not execution["stdout_valid_json"]
        or not execution["result_schema_valid"]
        or execution["adapter_pin_status"] != "manifest_pinned"
        or execution["baseline"]["status"] != "matched"
        or raw is None
        or normalized is None
    ):
        errors.append(
            _error(
                "legacy_completed_state_mismatch",
                "$.legacy.execution",
                "completed legacy execution requires a matched baseline, a manifest-pinned adapter, and successful schema-valid raw and normalized observations",
            )
        )

    comparison = payload["comparison"]
    expected_source_id = vnext.get("subject_ref", {}).get("entity_id")
    expected_workflow = vnext.get("workflow_disposition", {}).get("status")
    expected_outcome = vnext.get("audit_conclusion", {}).get("outcome")
    baseline_status = execution["baseline"]["status"]
    if comparison["source_id"] != expected_source_id:
        errors.append(
            _error(
                "comparison_subject_mismatch",
                "$.comparison.source_id",
                "comparison subject does not match the nested vNext observation",
            )
        )
    if (
        comparison["vnext_workflow"] != expected_workflow
        or comparison["vnext_outcome"] != expected_outcome
    ):
        errors.append(
            _error(
                "comparison_vnext_state_mismatch",
                "$.comparison",
                "comparison vNext state does not match the nested vNext observation",
            )
        )
    if (
        comparison["legacy_execution_status"] != execution["status"]
        or comparison["legacy_baseline_status"] != baseline_status
    ):
        errors.append(
            _error(
                "comparison_legacy_state_mismatch",
                "$.comparison",
                "comparison legacy state does not match the nested legacy observation",
            )
        )
    unresolved_count = sum(
        item["assessment"] == "unresolved_requires_review"
        for item in comparison["differences"]
    )
    if comparison["unresolved_requires_review_count"] != unresolved_count:
        errors.append(
            _error(
                "comparison_unresolved_count_mismatch",
                "$.comparison.unresolved_requires_review_count",
                "comparison unresolved count does not match its difference denominator",
            )
        )

    invocation = execution["invocation_fingerprint"]
    if invocation:
        expected_text_digest = str(expected_source_id).removeprefix("sha256:")
        if invocation.get("text_sha256") != expected_text_digest:
            errors.append(
                _error(
                    "legacy_invocation_subject_mismatch",
                    "$.legacy.execution.invocation_fingerprint.text_sha256",
                    "legacy invocation subject does not match the nested vNext subject",
                )
            )
    return tuple(errors)


def validate_legacy_shadow_observation(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    errors = legacy_shadow_observation_errors(payload)
    if errors:
        raise LegacyShadowObservationValidationError(errors)
    return copy.deepcopy(dict(payload))


__all__ = [
    "SCHEMA_VERSION",
    "LegacyShadowObservationValidationError",
    "build_legacy_shadow_observation",
    "legacy_shadow_observation_errors",
    "semantic_digest_value",
    "validate_legacy_shadow_observation",
]
