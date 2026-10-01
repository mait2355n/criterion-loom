"""Closed operational-qualification and requalification contracts.

The builders only project supplied observations and external decision records
into deterministic audit material.  They never deploy, schedule, change a
default, accept risk, retire a predecessor, or manufacture a human decision.

Record closure is intentionally narrower than real-world readiness.  Digests
bind supplied material but do not authenticate an external record, clock,
platform, reviewer, or human actor.
"""

from __future__ import annotations

import copy
from datetime import datetime, timedelta
from functools import lru_cache
import hashlib
import json
from typing import Any, Iterable, Mapping, Sequence

from jsonschema import Draft202012Validator, FormatChecker

from .schema_access import schema_directory


PROFILE_VERSION = "operational-qualification-profile/v0"
ENVELOPE_VERSION = "deployment-envelope/v0"
OBSERVATION_VERSION = "operational-scenario-observation/v0"
REVIEW_VERSION = "independent-operational-review/v0"
QUALIFICATION_VERSION = "operational-qualification/v0"

DEPLOYMENT_MODES = (
    "local",
    "ci",
    "sidecar",
    "service",
    "external_provider",
)
REQUIRED_SCENARIOS = (
    "duration",
    "concurrency",
    "load",
    "resource_exhaustion",
    "provider_failure",
    "restart",
    "recovery",
    "compatibility",
    "platform",
    "observability",
    "incident",
    "rollback_trigger",
)
SCENARIO_EXECUTION_POLICY: dict[str, tuple[str, ...]] = {
    "duration": ("soak_test", "production_observation"),
    "concurrency": ("concurrency_test", "production_observation"),
    "load": ("load_test", "production_observation"),
    "resource_exhaustion": ("resource_exhaustion_test",),
    "provider_failure": ("fault_injection",),
    "restart": ("restart_rehearsal",),
    "recovery": ("recovery_rehearsal",),
    "compatibility": ("compatibility_test",),
    "platform": ("platform_test", "production_observation"),
    "observability": ("observability_test", "production_observation"),
    "incident": ("incident_rehearsal",),
    "rollback_trigger": ("rollback_rehearsal",),
}
STATEFUL_SCENARIOS = frozenset(
    {
        "resource_exhaustion",
        "provider_failure",
        "restart",
        "recovery",
        "incident",
        "rollback_trigger",
    }
)
CHANGE_DIMENSIONS = (
    "subject",
    "environment",
    "dependency",
    "provider",
    "configuration",
    "profile",
    "envelope",
)
_SCOPE_FIELDS = {
    "subject": "subject_manifest_ref",
    "environment": "environment_manifest_ref",
    "dependency": "dependency_manifest_ref",
    "provider": "provider_manifest_ref",
    "configuration": "configuration_manifest_ref",
}

_SCHEMA_DIR = schema_directory()
_LIMITATIONS = (
    "Operational eligibility is bounded to the supplied closed manifests, selected deployment envelope, thresholds, and observations.",
    "Digest closure does not authenticate clocks, platforms, providers, reviewers, evidence locators, signatures, or human actors.",
    "Semantic field validity, security, and human acceptance remain independent open dimensions and are not closed by this qualification.",
    "The result is audit material only; it does not deploy, schedule, change a default, accept risk, or retire a predecessor.",
)
_AUTHORITY_BOUNDARY = {
    "semantic_guard_role": "audit_operational_qualification_only",
    "deploy": False,
    "schedule": False,
    "change_default": False,
    "accept_risk": False,
    "retire": False,
    "final_decision_owner": "human",
}
_OPEN_DIMENSIONS = {
    "semantic_field_validity": "open",
    "security": "open",
    "human_acceptance": "open",
}


class OperationalQualificationError(ValueError):
    """Raised when an operational qualification fails closed."""


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _digest(value: Any) -> dict[str, str]:
    return {"algorithm": "sha256", "value": _sha256(value)}


def _without(value: Mapping[str, Any], *fields: str) -> dict[str, Any]:
    result = copy.deepcopy(dict(value))
    for field in fields:
        result.pop(field, None)
    return result


def _format_path(parts: Iterable[Any]) -> str:
    return "/".join(str(part) for part in parts) or "/"


def _parse_time(value: str, location: str) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith(("Z", "z")) else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise OperationalQualificationError(
            f"invalid timestamp at {location}: {value}"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise OperationalQualificationError(
            f"timestamp lacks timezone at {location}: {value}"
        )
    return parsed


@lru_cache(maxsize=1)
def _schema() -> dict[str, Any]:
    return json.loads(
        (_SCHEMA_DIR / "operational-qualification.schema.json").read_text(
            encoding="utf-8"
        )
    )


@lru_cache(maxsize=1)
def _validator() -> Draft202012Validator:
    schema = _schema()
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


@lru_cache(maxsize=None)
def _subvalidator(definition: str) -> Draft202012Validator:
    root = _schema()
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$defs": root["$defs"],
        "$ref": f"#/$defs/{definition}",
    }
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _validate_schema(
    value: Mapping[str, Any],
    validator: Draft202012Validator,
    contract: str,
) -> None:
    issues = sorted(
        validator.iter_errors(value),
        key=lambda issue: tuple(str(part) for part in issue.absolute_path),
    )
    if issues:
        issue = issues[0]
        raise OperationalQualificationError(
            f"{contract} schema violation at {_format_path(issue.absolute_path)}: "
            f"{issue.message}"
        )


def _require_unique(
    values: Sequence[Mapping[str, Any]],
    field: str,
    location: str,
) -> None:
    identities = [str(value[field]) for value in values]
    duplicates = sorted(
        {identity for identity in identities if identities.count(identity) > 1}
    )
    if duplicates:
        raise OperationalQualificationError(
            f"duplicate {field} at {location}: {duplicates!r}"
        )


def _digest_value(value: Mapping[str, Any]) -> str:
    return str(value["value"])


def _profile_ref(profile: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "profile_id": profile["profile_id"],
        "profile_version": profile["profile_version"],
        "profile_digest": copy.deepcopy(profile["profile_digest"]),
        "adoption_state": profile["adoption_state"],
        "adopted_at": (
            profile["adoption_decision_ref"]["decided_at"]
            if profile["adoption_decision_ref"] is not None
            else None
        ),
        "max_evidence_age_seconds": profile["max_evidence_age_seconds"],
    }


def _envelope_ref(envelope: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "envelope_id": envelope["envelope_id"],
        "envelope_version": envelope["envelope_version"],
        "envelope_digest": copy.deepcopy(envelope["envelope_digest"]),
        "selected_mode": envelope["selected_mode"],
        "selection_state": envelope["selection_state"],
        "selected_at": (
            envelope["selection_decision_ref"]["decided_at"]
            if envelope["selection_decision_ref"] is not None
            else None
        ),
    }


def _threshold_ref(threshold: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "threshold_id": threshold["threshold_id"],
        "threshold_version": threshold["threshold_version"],
        "threshold_digest": copy.deepcopy(threshold["threshold_digest"]),
    }


def qualification_ref(qualification: Mapping[str, Any]) -> dict[str, Any]:
    """Return the exact digest-bound qualification reference."""

    return {
        "qualification_id": qualification["qualification_id"],
        "qualification_version": qualification["qualification_version"],
        "qualification_digest": copy.deepcopy(qualification["qualification_digest"]),
        "scope_digest": copy.deepcopy(qualification["scope_digest"]),
        "profile_ref": copy.deepcopy(qualification["profile_ref"]),
        "deployment_envelope_ref": copy.deepcopy(
            qualification["deployment_envelope_ref"]
        ),
    }


def validate_external_human_decision(
    record: Mapping[str, Any],
    *,
    expected_kind: str,
    target_id: str,
    target_version: str,
    target_digest: Mapping[str, Any],
    not_after: str | None = None,
) -> None:
    """Validate the binding of a supplied external human record.

    This checks record shape and exact target binding only.  It does not prove
    that the named human, signature, locator, or trust source exists.
    """

    _validate_schema(record, _subvalidator("external_human_decision"), "human decision")
    if (
        record["decision_kind"] != expected_kind
        or record["target_id"] != target_id
        or record["target_version"] != target_version
        or record["target_digest"] != target_digest
    ):
        raise OperationalQualificationError(
            "external human decision target or decision kind mismatch"
        )
    decided_at = _parse_time(str(record["decided_at"]), "human_decision.decided_at")
    if not_after is not None and decided_at > _parse_time(not_after, "not_after"):
        raise OperationalQualificationError(
            "external human decision occurs after the enclosing assessment"
        )


def _scenario_policy_material() -> list[dict[str, Any]]:
    return [
        {
            "scenario_id": scenario,
            "accepted_execution_kinds": list(SCENARIO_EXECUTION_POLICY[scenario]),
            "state_transition_required": scenario in STATEFUL_SCENARIOS,
        }
        for scenario in REQUIRED_SCENARIOS
    ]


def _change_policy_material() -> list[dict[str, Any]]:
    return [
        {
            "dimension": dimension,
            "invalidates_prior": True,
            "requires_requalification": True,
        }
        for dimension in CHANGE_DIMENSIONS
    ]


def build_operational_profile(
    *,
    profile_id: str,
    profile_version: str,
    adoption_state: str,
    max_evidence_age_seconds: int,
    adoption_decision_ref: Mapping[str, Any] | None = None,
    retirement_decision_ref: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a candidate, adopted, or retired qualification profile.

    Callers commonly build ``pending`` first, obtain ``profile_basis_digest``,
    and only then supply a separately acquired external adoption record.
    """

    basis = {
        "schema_version": PROFILE_VERSION,
        "profile_id": profile_id,
        "profile_version": profile_version,
        "supported_deployment_modes": list(DEPLOYMENT_MODES),
        "required_scenarios": list(REQUIRED_SCENARIOS),
        "scenario_execution_policy": _scenario_policy_material(),
        "max_evidence_age_seconds": max_evidence_age_seconds,
        "change_invalidation": _change_policy_material(),
    }
    profile: dict[str, Any] = {
        **basis,
        "profile_basis_digest": _digest(basis),
        "adoption_state": adoption_state,
        "adoption_decision_ref": (
            copy.deepcopy(dict(adoption_decision_ref))
            if adoption_decision_ref is not None
            else None
        ),
        "retirement_decision_ref": (
            copy.deepcopy(dict(retirement_decision_ref))
            if retirement_decision_ref is not None
            else None
        ),
    }
    profile["profile_digest"] = _digest(profile)
    validate_operational_profile(profile)
    return profile


def validate_operational_profile(profile: Mapping[str, Any]) -> None:
    _validate_schema(profile, _subvalidator("operational_profile"), "operational profile")
    if tuple(profile["supported_deployment_modes"]) != DEPLOYMENT_MODES:
        raise OperationalQualificationError(
            "operational profile must bind every deployment mode exactly once"
        )
    if tuple(profile["required_scenarios"]) != REQUIRED_SCENARIOS:
        raise OperationalQualificationError(
            "operational profile must bind every required scenario exactly once"
        )
    if profile["scenario_execution_policy"] != _scenario_policy_material():
        raise OperationalQualificationError("scenario execution policy mismatch")
    if profile["change_invalidation"] != _change_policy_material():
        raise OperationalQualificationError("change invalidation policy mismatch")
    basis = {
        key: copy.deepcopy(profile[key])
        for key in (
            "schema_version",
            "profile_id",
            "profile_version",
            "supported_deployment_modes",
            "required_scenarios",
            "scenario_execution_policy",
            "max_evidence_age_seconds",
            "change_invalidation",
        )
    }
    if profile["profile_basis_digest"] != _digest(basis):
        raise OperationalQualificationError("operational profile basis digest mismatch")
    state = str(profile["adoption_state"])
    adoption = profile["adoption_decision_ref"]
    retirement = profile["retirement_decision_ref"]
    if state == "pending":
        if adoption is not None or retirement is not None:
            raise OperationalQualificationError(
                "pending operational profile cannot carry adoption or retirement decisions"
            )
    else:
        if adoption is None:
            raise OperationalQualificationError(
                "adopted or retired operational profile requires external human adoption"
            )
        validate_external_human_decision(
            adoption,
            expected_kind="adopt_operational_profile",
            target_id=str(profile["profile_id"]),
            target_version=str(profile["profile_version"]),
            target_digest=profile["profile_basis_digest"],
        )
        if state == "adopted" and retirement is not None:
            raise OperationalQualificationError(
                "adopted operational profile cannot already carry retirement"
            )
        if state == "retired":
            if retirement is None:
                raise OperationalQualificationError(
                    "retired operational profile requires a separate human retirement decision"
                )
            validate_external_human_decision(
                retirement,
                expected_kind="retire_operational_profile",
                target_id=str(profile["profile_id"]),
                target_version=str(profile["profile_version"]),
                target_digest=profile["profile_basis_digest"],
            )
            if retirement["decision_id"] == adoption["decision_id"]:
                raise OperationalQualificationError(
                    "profile adoption and retirement must be separate decisions"
                )
            if _parse_time(
                str(retirement["decided_at"]), "retirement_decision.decided_at"
            ) < _parse_time(
                str(adoption["decided_at"]), "adoption_decision.decided_at"
            ):
                raise OperationalQualificationError(
                    "profile retirement decision predates profile adoption"
                )
    if profile["profile_digest"] != _digest(_without(profile, "profile_digest")):
        raise OperationalQualificationError("operational profile digest mismatch")


def build_scenario_threshold(
    *,
    threshold_id: str,
    threshold_version: str,
    scenario_id: str,
    metric: str,
    comparator: str,
    target_value: float,
    unit: str,
    observation_window_seconds: int,
) -> dict[str, Any]:
    threshold: dict[str, Any] = {
        "threshold_id": threshold_id,
        "threshold_version": threshold_version,
        "scenario_id": scenario_id,
        "metric": metric,
        "comparator": comparator,
        "target_value": target_value,
        "unit": unit,
        "observation_window_seconds": observation_window_seconds,
    }
    threshold["threshold_digest"] = _digest(threshold)
    validate_scenario_threshold(threshold)
    return threshold


def validate_scenario_threshold(threshold: Mapping[str, Any]) -> None:
    _validate_schema(threshold, _subvalidator("scenario_threshold"), "scenario threshold")
    if threshold["threshold_digest"] != _digest(
        _without(threshold, "threshold_digest")
    ):
        raise OperationalQualificationError("scenario threshold digest mismatch")


def build_deployment_envelope(
    *,
    envelope_id: str,
    envelope_version: str,
    operational_profile: Mapping[str, Any],
    selected_mode: str,
    platform_manifest_ref: Mapping[str, Any],
    scenario_thresholds: Sequence[Mapping[str, Any]],
    selection_decision_ref: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    validate_operational_profile(operational_profile)
    thresholds = sorted(
        (copy.deepcopy(dict(item)) for item in scenario_thresholds),
        key=lambda item: REQUIRED_SCENARIOS.index(str(item["scenario_id"])),
    )
    for threshold in thresholds:
        validate_scenario_threshold(threshold)
    basis = {
        "schema_version": ENVELOPE_VERSION,
        "envelope_id": envelope_id,
        "envelope_version": envelope_version,
        "profile_ref": _profile_ref(operational_profile),
        "selected_mode": selected_mode,
        "platform_manifest_ref": copy.deepcopy(dict(platform_manifest_ref)),
        "scenario_thresholds": thresholds,
    }
    envelope: dict[str, Any] = {
        **basis,
        "envelope_basis_digest": _digest(basis),
        "selection_state": (
            "selected" if selection_decision_ref is not None else "pending"
        ),
        "selection_decision_ref": (
            copy.deepcopy(dict(selection_decision_ref))
            if selection_decision_ref is not None
            else None
        ),
    }
    envelope["envelope_digest"] = _digest(envelope)
    validate_deployment_envelope(
        envelope,
        operational_profile=operational_profile,
    )
    return envelope


def validate_deployment_envelope(
    envelope: Mapping[str, Any],
    *,
    operational_profile: Mapping[str, Any] | None = None,
) -> None:
    _validate_schema(envelope, _subvalidator("deployment_envelope"), "deployment envelope")
    thresholds = list(envelope["scenario_thresholds"])
    for threshold in thresholds:
        validate_scenario_threshold(threshold)
    if [item["scenario_id"] for item in thresholds] != list(REQUIRED_SCENARIOS):
        raise OperationalQualificationError(
            "deployment envelope must bind every required scenario exactly once in profile order"
        )
    _require_unique(thresholds, "threshold_id", "scenario_thresholds")
    basis = {
        key: copy.deepcopy(envelope[key])
        for key in (
            "schema_version",
            "envelope_id",
            "envelope_version",
            "profile_ref",
            "selected_mode",
            "platform_manifest_ref",
            "scenario_thresholds",
        )
    }
    if envelope["envelope_basis_digest"] != _digest(basis):
        raise OperationalQualificationError("deployment envelope basis digest mismatch")
    if operational_profile is not None:
        validate_operational_profile(operational_profile)
        if envelope["profile_ref"] != _profile_ref(operational_profile):
            raise OperationalQualificationError(
                "deployment envelope profile reference mismatch"
            )
    selection = envelope["selection_decision_ref"]
    if envelope["selection_state"] == "pending":
        if selection is not None:
            raise OperationalQualificationError(
                "pending deployment envelope cannot carry a selection decision"
            )
    else:
        if selection is None:
            raise OperationalQualificationError(
                "selected deployment envelope requires an external human decision"
            )
        validate_external_human_decision(
            selection,
            expected_kind="select_deployment_envelope",
            target_id=str(envelope["envelope_id"]),
            target_version=str(envelope["envelope_version"]),
            target_digest=envelope["envelope_basis_digest"],
        )
        if envelope["profile_ref"]["adoption_state"] != "adopted":
            raise OperationalQualificationError(
                "deployment envelope cannot be selected under a non-adopted profile"
            )
        if _parse_time(
            str(selection["decided_at"]), "selection_decision.decided_at"
        ) < _parse_time(
            str(envelope["profile_ref"]["adopted_at"]), "profile_ref.adopted_at"
        ):
            raise OperationalQualificationError(
                "deployment envelope selection predates profile adoption"
            )
    if envelope["envelope_digest"] != _digest(_without(envelope, "envelope_digest")):
        raise OperationalQualificationError("deployment envelope digest mismatch")


def _threshold_met(value: float | None, comparator: str, target: float) -> bool:
    if value is None:
        return False
    if comparator == "lte":
        return value <= target
    if comparator == "lt":
        return value < target
    if comparator == "gte":
        return value >= target
    if comparator == "gt":
        return value > target
    if comparator == "eq":
        return value == target
    raise OperationalQualificationError(f"unknown threshold comparator: {comparator}")


def build_scenario_observation(
    *,
    observation_id: str,
    execution_id: str,
    threshold: Mapping[str, Any],
    deployment_envelope: Mapping[str, Any],
    scope_manifest_refs: Mapping[str, Any],
    execution_kind: str,
    evidence_origin: str,
    status: str,
    observed_at: str,
    expires_at: str,
    time_trust: str,
    measured_value: float | None,
    executor_ref: Mapping[str, Any],
    raw_evidence_refs: Sequence[Mapping[str, Any]],
    before_state_digest: Mapping[str, Any] | None = None,
    after_state_digest: Mapping[str, Any] | None = None,
    limitations: Sequence[str] = (),
) -> dict[str, Any]:
    validate_scenario_threshold(threshold)
    validate_deployment_envelope(deployment_envelope)
    measurement = {
        "value": measured_value,
        "unit": threshold["unit"],
        "comparator": threshold["comparator"],
        "threshold_met": _threshold_met(
            measured_value,
            str(threshold["comparator"]),
            float(threshold["target_value"]),
        ),
    }
    observation: dict[str, Any] = {
        "schema_version": OBSERVATION_VERSION,
        "observation_id": observation_id,
        "execution_id": execution_id,
        "scenario_id": threshold["scenario_id"],
        "execution_kind": execution_kind,
        "evidence_origin": evidence_origin,
        "status": status,
        "observed_at": observed_at,
        "expires_at": expires_at,
        "time_trust": time_trust,
        "deployment_mode": deployment_envelope["selected_mode"],
        "platform_manifest_ref": copy.deepcopy(
            deployment_envelope["platform_manifest_ref"]
        ),
        "scope_digest": _digest(scope_manifest_refs),
        "envelope_ref": _envelope_ref(deployment_envelope),
        "threshold_ref": _threshold_ref(threshold),
        "measurement": measurement,
        "executor_ref": copy.deepcopy(dict(executor_ref)),
        "raw_evidence_refs": sorted(
            (copy.deepcopy(dict(item)) for item in raw_evidence_refs),
            key=lambda item: item["evidence_id"],
        ),
        "before_state_digest": (
            copy.deepcopy(dict(before_state_digest))
            if before_state_digest is not None
            else None
        ),
        "after_state_digest": (
            copy.deepcopy(dict(after_state_digest))
            if after_state_digest is not None
            else None
        ),
        "limitations": sorted(set(limitations)),
    }
    observation["observation_digest"] = _digest(observation)
    validate_scenario_observation(
        observation,
        threshold=threshold,
        deployment_envelope=deployment_envelope,
        scope_manifest_refs=scope_manifest_refs,
    )
    return observation


def validate_scenario_observation(
    observation: Mapping[str, Any],
    *,
    threshold: Mapping[str, Any] | None = None,
    deployment_envelope: Mapping[str, Any] | None = None,
    scope_manifest_refs: Mapping[str, Any] | None = None,
) -> None:
    _validate_schema(
        observation,
        _subvalidator("scenario_observation"),
        "scenario observation",
    )
    observed_at = _parse_time(str(observation["observed_at"]), "observed_at")
    expires_at = _parse_time(str(observation["expires_at"]), "expires_at")
    if expires_at <= observed_at:
        raise OperationalQualificationError("observation expires_at must follow observed_at")
    raw = list(observation["raw_evidence_refs"])
    _require_unique(raw, "evidence_id", "raw_evidence_refs")
    digests = [_digest_value(item["content_digest"]) for item in raw]
    if len(digests) != len(set(digests)):
        raise OperationalQualificationError(
            "one observation cannot count the same raw evidence digest twice"
        )
    before = observation["before_state_digest"]
    after = observation["after_state_digest"]
    if observation["scenario_id"] in STATEFUL_SCENARIOS and (
        before is None or after is None
    ):
        raise OperationalQualificationError(
            "stateful rehearsal requires distinct before and after state digests"
        )
    if before is not None and after is not None and before == after:
        raise OperationalQualificationError(
            "before and after state digests are identical; no state transition was observed"
        )
    if observation["status"] == "passed" and not observation["measurement"][
        "threshold_met"
    ]:
        raise OperationalQualificationError(
            "passed scenario observation does not meet its declared threshold"
        )
    if threshold is not None:
        validate_scenario_threshold(threshold)
        if observation["scenario_id"] != threshold["scenario_id"]:
            raise OperationalQualificationError("scenario threshold subject mismatch")
        if observation["threshold_ref"] != _threshold_ref(threshold):
            raise OperationalQualificationError("scenario threshold reference mismatch")
        expected_met = _threshold_met(
            observation["measurement"]["value"],
            str(threshold["comparator"]),
            float(threshold["target_value"]),
        )
        if (
            observation["measurement"]["unit"] != threshold["unit"]
            or observation["measurement"]["comparator"] != threshold["comparator"]
            or observation["measurement"]["threshold_met"] != expected_met
        ):
            raise OperationalQualificationError(
                "scenario measurement does not replay under the bound threshold"
            )
    if deployment_envelope is not None:
        validate_deployment_envelope(deployment_envelope)
        if (
            observation["envelope_ref"] != _envelope_ref(deployment_envelope)
            or observation["deployment_mode"]
            != deployment_envelope["selected_mode"]
            or observation["platform_manifest_ref"]
            != deployment_envelope["platform_manifest_ref"]
        ):
            raise OperationalQualificationError(
                "scenario observation is outside the selected deployment envelope or platform"
            )
    if scope_manifest_refs is not None and observation["scope_digest"] != _digest(
        scope_manifest_refs
    ):
        raise OperationalQualificationError(
            "scenario observation is outside the closed qualification manifest scope"
        )
    if observation["observation_digest"] != _digest(
        _without(observation, "observation_digest")
    ):
        raise OperationalQualificationError("scenario observation digest mismatch")


def validate_independent_review_record(
    review: Mapping[str, Any],
    *,
    qualification_id: str,
    qualification_version: str,
    review_basis_digest: Mapping[str, Any],
    executor_refs: Sequence[Mapping[str, Any]],
    earliest_reviewed_at: str,
    assessed_at: str,
) -> None:
    _validate_schema(
        review,
        _subvalidator("independent_review_record"),
        "independent review",
    )
    if (
        review["target_qualification_id"] != qualification_id
        or review["target_qualification_version"] != qualification_version
        or review["target_basis_digest"] != review_basis_digest
    ):
        raise OperationalQualificationError(
            "independent review target does not match qualification basis"
        )
    reviewer_id = str(review["reviewer_ref"]["entity_id"])
    if reviewer_id in {str(item["entity_id"]) for item in executor_refs}:
        raise OperationalQualificationError(
            "independent reviewer cannot be an executor of the reviewed observations"
        )
    reviewed_at = _parse_time(str(review["reviewed_at"]), "reviewed_at")
    if reviewed_at < _parse_time(earliest_reviewed_at, "earliest_reviewed_at"):
        raise OperationalQualificationError(
            "independent review predates the observation set"
        )
    if reviewed_at > _parse_time(assessed_at, "assessed_at"):
        raise OperationalQualificationError(
            "independent review occurs after qualification assessment"
        )
    raw = list(review["raw_evidence_refs"])
    _require_unique(raw, "evidence_id", "independent_review.raw_evidence_refs")
    if review["review_digest"] != _digest(_without(review, "review_digest")):
        raise OperationalQualificationError("independent review digest mismatch")


def _latest_observation_time(observations: Sequence[Mapping[str, Any]]) -> str:
    return str(
        max(
            observations,
            key=lambda item: _parse_time(
                str(item["observed_at"]), "scenario_observation.observed_at"
            ),
        )["observed_at"]
    )


def _changed_dimensions(
    *,
    profile_ref: Mapping[str, Any],
    envelope_ref: Mapping[str, Any],
    scope_manifest_refs: Mapping[str, Any],
    previous_qualification: Mapping[str, Any] | None,
) -> list[str]:
    if previous_qualification is None:
        return []
    changed: list[str] = []
    previous_scope = previous_qualification["scope_manifest_refs"]
    for dimension, field in _SCOPE_FIELDS.items():
        if scope_manifest_refs[field] != previous_scope[field]:
            changed.append(dimension)
    if profile_ref != previous_qualification["profile_ref"]:
        changed.append("profile")
    if envelope_ref != previous_qualification["deployment_envelope_ref"]:
        changed.append("envelope")
    return [dimension for dimension in CHANGE_DIMENSIONS if dimension in changed]


def _raw_evidence_digests(observations: Sequence[Mapping[str, Any]]) -> set[str]:
    return {
        _digest_value(raw["content_digest"])
        for observation in observations
        for raw in observation["raw_evidence_refs"]
    }


def _change_assessment(
    *,
    profile_ref: Mapping[str, Any],
    envelope_ref: Mapping[str, Any],
    scope_manifest_refs: Mapping[str, Any],
    observations: Sequence[Mapping[str, Any]],
    previous_qualification: Mapping[str, Any] | None,
) -> dict[str, Any]:
    changed = _changed_dimensions(
        profile_ref=profile_ref,
        envelope_ref=envelope_ref,
        scope_manifest_refs=scope_manifest_refs,
        previous_qualification=previous_qualification,
    )
    replayed_execution_ids: list[str] = []
    replayed_evidence_digests: list[str] = []
    if previous_qualification is not None:
        previous_execution_ids = {
            str(item["execution_id"])
            for item in previous_qualification["scenario_observations"]
        }
        replayed_execution_ids = sorted(
            {
                str(item["execution_id"])
                for item in observations
                if str(item["execution_id"]) in previous_execution_ids
            }
        )
        replayed_evidence_digests = sorted(
            _raw_evidence_digests(observations)
            & _raw_evidence_digests(previous_qualification["scenario_observations"])
        )
    return {
        "prior_qualification_ref": (
            qualification_ref(previous_qualification)
            if previous_qualification is not None
            else None
        ),
        "changed_dimensions": changed,
        "prior_invalidated": bool(changed),
        "requalification_required": bool(changed),
        "replayed_execution_ids": replayed_execution_ids,
        "replayed_evidence_digests": replayed_evidence_digests,
    }


def _review_basis_material(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "qualification_id": record["qualification_id"],
        "qualification_version": record["qualification_version"],
        "profile_ref": copy.deepcopy(record["profile_ref"]),
        "deployment_envelope_ref": copy.deepcopy(
            record["deployment_envelope_ref"]
        ),
        "scope_manifest_refs": copy.deepcopy(record["scope_manifest_refs"]),
        "scope_digest": copy.deepcopy(record["scope_digest"]),
        "assessed_at": record["assessed_at"],
        "time_trust": record["time_trust"],
        "scenario_observations": copy.deepcopy(record["scenario_observations"]),
        "change_assessment": copy.deepcopy(record["change_assessment"]),
    }


def _authorization_basis_material(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "review_basis_digest": copy.deepcopy(record["review_basis_digest"]),
        "independent_review_record": copy.deepcopy(
            record["independent_review_record"]
        ),
        "eligibility": copy.deepcopy(record["eligibility"]),
        "independent_open_dimensions": copy.deepcopy(
            record["independent_open_dimensions"]
        ),
        "limitations": copy.deepcopy(record["limitations"]),
        "authority_boundary": copy.deepcopy(record["authority_boundary"]),
    }


def _derive_eligibility(record: Mapping[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []

    def add(reason: str) -> None:
        if reason not in reasons:
            reasons.append(reason)

    if record["profile_ref"]["adoption_state"] != "adopted":
        add("operational_profile_not_adopted")
    if record["deployment_envelope_ref"]["selection_state"] != "selected":
        add("deployment_envelope_not_human_selected")
    if record["time_trust"] != "trusted":
        add("qualification_time_untrusted")

    assessed_at = _parse_time(str(record["assessed_at"]), "assessed_at")
    adopted_at = (
        _parse_time(str(record["profile_ref"]["adopted_at"]), "profile_ref.adopted_at")
        if record["profile_ref"]["adopted_at"] is not None
        else None
    )
    selected_at = (
        _parse_time(
            str(record["deployment_envelope_ref"]["selected_at"]),
            "deployment_envelope_ref.selected_at",
        )
        if record["deployment_envelope_ref"]["selected_at"] is not None
        else None
    )
    if adopted_at is not None and assessed_at < adopted_at:
        add("qualification_precedes_profile_adoption")
    if selected_at is not None and assessed_at < selected_at:
        add("qualification_precedes_envelope_selection")
    max_age = timedelta(
        seconds=int(record["profile_ref"]["max_evidence_age_seconds"])
    )
    for observation in record["scenario_observations"]:
        scenario = str(observation["scenario_id"])
        observed_at = _parse_time(str(observation["observed_at"]), "observed_at")
        expires_at = _parse_time(str(observation["expires_at"]), "expires_at")
        if observation["status"] != "passed":
            add(f"scenario_{scenario}_{observation['status']}")
        if observation["evidence_origin"] == "synthetic_fixture":
            add(f"scenario_{scenario}_synthetic_evidence")
        if observation["time_trust"] != "trusted":
            add(f"scenario_{scenario}_time_untrusted")
        if assessed_at < observed_at:
            add(f"scenario_{scenario}_observation_in_future")
        if adopted_at is not None and observed_at < adopted_at:
            add(f"scenario_{scenario}_precedes_profile_adoption")
        if selected_at is not None and observed_at < selected_at:
            add(f"scenario_{scenario}_precedes_envelope_selection")
        if assessed_at >= expires_at or assessed_at - observed_at > max_age:
            add(f"scenario_{scenario}_stale")
        if observation["execution_kind"] not in SCENARIO_EXECUTION_POLICY[scenario]:
            add(f"scenario_{scenario}_execution_not_operationally_qualifying")
        if not observation["measurement"]["threshold_met"]:
            add(f"scenario_{scenario}_threshold_not_met")

    review = record["independent_review_record"]
    if review is None:
        add("independent_review_missing")
    elif review["status"] != "accepted":
        add(f"independent_review_{review['status']}")

    change = record["change_assessment"]
    if change["replayed_execution_ids"] or change["replayed_evidence_digests"]:
        add("replayed_requalification_evidence")

    return {
        "status": "eligible" if not reasons else "not_eligible",
        "reasons": sorted(reasons),
    }


def build_operational_qualification(
    *,
    qualification_id: str,
    qualification_version: str,
    operational_profile: Mapping[str, Any],
    deployment_envelope: Mapping[str, Any],
    scope_manifest_refs: Mapping[str, Any],
    assessed_at: str,
    time_trust: str,
    scenario_observations: Sequence[Mapping[str, Any]],
    independent_review_record: Mapping[str, Any] | None = None,
    previous_qualification: Mapping[str, Any] | None = None,
    human_authorization_record: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    validate_operational_profile(operational_profile)
    validate_deployment_envelope(
        deployment_envelope,
        operational_profile=operational_profile,
    )
    if deployment_envelope["platform_manifest_ref"] != scope_manifest_refs[
        "environment_manifest_ref"
    ]:
        raise OperationalQualificationError(
            "selected deployment platform is outside the closed environment manifest"
        )
    _parse_time(assessed_at, "assessed_at")
    observations = sorted(
        (copy.deepcopy(dict(item)) for item in scenario_observations),
        key=lambda item: REQUIRED_SCENARIOS.index(str(item["scenario_id"])),
    )
    thresholds = {
        str(item["scenario_id"]): item
        for item in deployment_envelope["scenario_thresholds"]
    }
    for observation in observations:
        scenario = str(observation["scenario_id"])
        if scenario not in thresholds:
            raise OperationalQualificationError(
                f"observation has no deployment threshold: {scenario}"
            )
        validate_scenario_observation(
            observation,
            threshold=thresholds[scenario],
            deployment_envelope=deployment_envelope,
            scope_manifest_refs=scope_manifest_refs,
        )
    scenario_ids = [str(item["scenario_id"]) for item in observations]
    if scenario_ids != list(REQUIRED_SCENARIOS):
        raise OperationalQualificationError(
            "scenario observations must cover every required scenario exactly once"
        )
    _require_unique(observations, "observation_id", "scenario_observations")
    _require_unique(observations, "execution_id", "scenario_observations")

    if previous_qualification is not None:
        validate_operational_qualification(previous_qualification)
    profile_ref = _profile_ref(operational_profile)
    envelope_ref = _envelope_ref(deployment_envelope)
    change = _change_assessment(
        profile_ref=profile_ref,
        envelope_ref=envelope_ref,
        scope_manifest_refs=scope_manifest_refs,
        observations=observations,
        previous_qualification=previous_qualification,
    )
    if change["replayed_execution_ids"] or change["replayed_evidence_digests"]:
        raise OperationalQualificationError(
            "requalification cannot replay prior execution or raw evidence material"
        )

    record: dict[str, Any] = {
        "schema_version": QUALIFICATION_VERSION,
        "qualification_id": qualification_id,
        "qualification_version": qualification_version,
        "profile_ref": profile_ref,
        "deployment_envelope_ref": envelope_ref,
        "scope_manifest_refs": copy.deepcopy(dict(scope_manifest_refs)),
        "scope_digest": _digest(scope_manifest_refs),
        "assessed_at": assessed_at,
        "time_trust": time_trust,
        "scenario_observations": observations,
        "change_assessment": change,
    }
    record["review_basis_digest"] = _digest(_review_basis_material(record))
    review = (
        copy.deepcopy(dict(independent_review_record))
        if independent_review_record is not None
        else None
    )
    record["independent_review_record"] = review
    if review is not None:
        validate_independent_review_record(
            review,
            qualification_id=qualification_id,
            qualification_version=qualification_version,
            review_basis_digest=record["review_basis_digest"],
            executor_refs=[item["executor_ref"] for item in observations],
            earliest_reviewed_at=_latest_observation_time(observations),
            assessed_at=assessed_at,
        )
    record["eligibility"] = _derive_eligibility(record)
    record["independent_open_dimensions"] = copy.deepcopy(_OPEN_DIMENSIONS)
    record["limitations"] = list(_LIMITATIONS)
    record["authority_boundary"] = copy.deepcopy(_AUTHORITY_BOUNDARY)
    record["authorization_basis_digest"] = _digest(
        _authorization_basis_material(record)
    )
    authorization = (
        copy.deepcopy(dict(human_authorization_record))
        if human_authorization_record is not None
        else None
    )
    record["human_authorization_record"] = authorization
    if authorization is not None:
        if record["eligibility"]["status"] != "eligible":
            raise OperationalQualificationError(
                "human authorization cannot override operational ineligibility"
            )
        validate_external_human_decision(
            authorization,
            expected_kind="authorize_operational_use",
            target_id=qualification_id,
            target_version=qualification_version,
            target_digest=record["authorization_basis_digest"],
            not_after=assessed_at,
        )
        record["outcome"] = "human_authorized"
    else:
        record["outcome"] = record["eligibility"]["status"]
    record["qualification_digest"] = _digest(record)
    validate_operational_qualification(
        record,
        operational_profile=operational_profile,
        deployment_envelope=deployment_envelope,
        current_scope_manifest_refs=scope_manifest_refs,
        previous_qualification=previous_qualification,
    )
    return record


def validate_operational_qualification(
    qualification: Mapping[str, Any],
    *,
    operational_profile: Mapping[str, Any] | None = None,
    deployment_envelope: Mapping[str, Any] | None = None,
    current_scope_manifest_refs: Mapping[str, Any] | None = None,
    previous_qualification: Mapping[str, Any] | None = None,
) -> None:
    _validate_schema(qualification, _validator(), "operational qualification")
    _parse_time(str(qualification["assessed_at"]), "assessed_at")
    if operational_profile is not None:
        validate_operational_profile(operational_profile)
        if qualification["profile_ref"] != _profile_ref(operational_profile):
            raise OperationalQualificationError(
                "qualification operational profile reference mismatch"
            )
    if deployment_envelope is not None:
        validate_deployment_envelope(
            deployment_envelope,
            operational_profile=operational_profile,
        )
        if qualification["deployment_envelope_ref"] != _envelope_ref(
            deployment_envelope
        ):
            raise OperationalQualificationError(
                "qualification deployment envelope reference mismatch"
            )
    if current_scope_manifest_refs is not None and qualification[
        "scope_manifest_refs"
    ] != current_scope_manifest_refs:
        raise OperationalQualificationError(
            "qualification manifest scope differs from the current closed scope"
        )
    if deployment_envelope is not None and deployment_envelope[
        "platform_manifest_ref"
    ] != qualification["scope_manifest_refs"]["environment_manifest_ref"]:
        raise OperationalQualificationError(
            "selected deployment platform is outside the closed environment manifest"
        )
    if qualification["scope_digest"] != _digest(
        qualification["scope_manifest_refs"]
    ):
        raise OperationalQualificationError("qualification scope digest mismatch")

    observations = list(qualification["scenario_observations"])
    scenario_ids = [str(item["scenario_id"]) for item in observations]
    if scenario_ids != list(REQUIRED_SCENARIOS):
        raise OperationalQualificationError(
            "scenario observations must cover every required scenario exactly once"
        )
    _require_unique(observations, "observation_id", "scenario_observations")
    _require_unique(observations, "execution_id", "scenario_observations")
    threshold_by_scenario = (
        {
            str(item["scenario_id"]): item
            for item in deployment_envelope["scenario_thresholds"]
        }
        if deployment_envelope is not None
        else {}
    )
    for observation in observations:
        validate_scenario_observation(
            observation,
            threshold=threshold_by_scenario.get(str(observation["scenario_id"])),
            deployment_envelope=deployment_envelope,
            scope_manifest_refs=qualification["scope_manifest_refs"],
        )

    expected_change = _change_assessment(
        profile_ref=qualification["profile_ref"],
        envelope_ref=qualification["deployment_envelope_ref"],
        scope_manifest_refs=qualification["scope_manifest_refs"],
        observations=observations,
        previous_qualification=previous_qualification,
    )
    if qualification["change_assessment"] != expected_change:
        if (
            qualification["change_assessment"]["prior_qualification_ref"] is not None
            and previous_qualification is None
        ):
            raise OperationalQualificationError(
                "prior qualification material is required to replay change invalidation"
            )
        raise OperationalQualificationError("change invalidation assessment mismatch")
    if expected_change["replayed_execution_ids"] or expected_change[
        "replayed_evidence_digests"
    ]:
        raise OperationalQualificationError(
            "replayed rehearsal or raw evidence cannot satisfy requalification"
        )

    expected_review_basis = _digest(_review_basis_material(qualification))
    if qualification["review_basis_digest"] != expected_review_basis:
        raise OperationalQualificationError("independent review basis digest mismatch")
    review = qualification["independent_review_record"]
    if review is not None:
        validate_independent_review_record(
            review,
            qualification_id=str(qualification["qualification_id"]),
            qualification_version=str(qualification["qualification_version"]),
            review_basis_digest=expected_review_basis,
            executor_refs=[item["executor_ref"] for item in observations],
            earliest_reviewed_at=_latest_observation_time(observations),
            assessed_at=str(qualification["assessed_at"]),
        )
    if qualification["eligibility"] != _derive_eligibility(qualification):
        raise OperationalQualificationError("operational eligibility does not replay")
    if qualification["independent_open_dimensions"] != _OPEN_DIMENSIONS:
        raise OperationalQualificationError(
            "operational qualification cannot close field validity, security, or human acceptance"
        )
    if tuple(qualification["limitations"]) != _LIMITATIONS:
        raise OperationalQualificationError("operational qualification limitations mismatch")
    if qualification["authority_boundary"] != _AUTHORITY_BOUNDARY:
        raise OperationalQualificationError("operational authority boundary mismatch")
    expected_authorization_basis = _digest(
        _authorization_basis_material(qualification)
    )
    if qualification["authorization_basis_digest"] != expected_authorization_basis:
        raise OperationalQualificationError("authorization basis digest mismatch")
    authorization = qualification["human_authorization_record"]
    if authorization is None:
        expected_outcome = qualification["eligibility"]["status"]
    else:
        if qualification["eligibility"]["status"] != "eligible":
            raise OperationalQualificationError(
                "human authorization cannot override operational ineligibility"
            )
        validate_external_human_decision(
            authorization,
            expected_kind="authorize_operational_use",
            target_id=str(qualification["qualification_id"]),
            target_version=str(qualification["qualification_version"]),
            target_digest=expected_authorization_basis,
            not_after=str(qualification["assessed_at"]),
        )
        expected_outcome = "human_authorized"
    if qualification["outcome"] != expected_outcome:
        raise OperationalQualificationError("operational qualification outcome mismatch")
    if qualification["qualification_digest"] != _digest(
        _without(qualification, "qualification_digest")
    ):
        raise OperationalQualificationError("operational qualification digest mismatch")


__all__ = [
    "CHANGE_DIMENSIONS",
    "DEPLOYMENT_MODES",
    "OperationalQualificationError",
    "REQUIRED_SCENARIOS",
    "SCENARIO_EXECUTION_POLICY",
    "STATEFUL_SCENARIOS",
    "build_deployment_envelope",
    "build_operational_profile",
    "build_operational_qualification",
    "build_scenario_observation",
    "build_scenario_threshold",
    "qualification_ref",
    "validate_deployment_envelope",
    "validate_external_human_decision",
    "validate_independent_review_record",
    "validate_operational_profile",
    "validate_operational_qualification",
    "validate_scenario_observation",
    "validate_scenario_threshold",
]
