"""Governed sidecar-to-retirement transition audit material.

The transition contract evaluates evidence and exact external decision refs for
``sidecar -> opt_in -> shadow -> default -> predecessor_retired``.  It never
executes a transition, changes a default, schedules work, accepts risk,
disposes artifacts, or retires the predecessor.
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

from .operational_qualification import (
    qualification_ref,
    validate_deployment_envelope,
    validate_operational_profile,
    validate_operational_qualification,
)


TRANSITION_VERSION = "transition-plan/v0"
STAGES = ("sidecar", "opt_in", "shadow", "default", "predecessor_retired")
DEFAULT_RETIRE_GATES = (
    "field_validity",
    "operational_qualification",
    "human_use_validation",
    "security_assessment",
    "register_readiness",
    "compatibility_migration",
    "shadow_observation",
    "rollback_recovery_rehearsal",
    "independent_observation",
)
STAGE_GATE_REQUIREMENTS: dict[str, tuple[str, ...]] = {
    "sidecar": (
        "field_validity",
        "operational_qualification",
        "security_assessment",
        "rollback_recovery_rehearsal",
        "independent_observation",
    ),
    "opt_in": (
        "field_validity",
        "operational_qualification",
        "human_use_validation",
        "security_assessment",
        "register_readiness",
        "compatibility_migration",
        "rollback_recovery_rehearsal",
        "independent_observation",
    ),
    "shadow": (
        "field_validity",
        "operational_qualification",
        "human_use_validation",
        "security_assessment",
        "register_readiness",
        "compatibility_migration",
        "rollback_recovery_rehearsal",
        "independent_observation",
    ),
    "default": DEFAULT_RETIRE_GATES,
    "predecessor_retired": DEFAULT_RETIRE_GATES,
}
INDEPENDENT_GATE_KINDS = frozenset(
    {
        "field_validity",
        "human_use_validation",
        "security_assessment",
        "independent_observation",
    }
)

_SCHEMA_DIR = schema_directory()
_LIMITATIONS = (
    "Transition eligibility is bounded to the supplied plan, exact refs, evidence times, and current operational qualification.",
    "Digest and decision-record closure do not authenticate an external human, reviewer, signature, clock, platform, or artifact locator.",
    "A synthetic passage, unit test, schema test, or smoke test is not field, operational, human-use, security, shadow, recovery, or cutover evidence.",
    "The result is audit material only; it does not deploy, schedule, change a default, accept risk, dispose artifacts, or retire a predecessor.",
)
_AUTHORITY_BOUNDARY = {
    "semantic_guard_role": "audit_transition_eligibility_only",
    "deploy": False,
    "schedule": False,
    "change_default": False,
    "accept_risk": False,
    "dispose": False,
    "retire": False,
    "final_decision_owner": "human",
}


class TransitionControlError(ValueError):
    """Raised when transition-control material fails closed."""


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


def _parse_time(value: str, location: str) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith(("Z", "z")) else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise TransitionControlError(
            f"invalid timestamp at {location}: {value}"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise TransitionControlError(
            f"timestamp lacks timezone at {location}: {value}"
        )
    return parsed


def _format_path(parts: Iterable[Any]) -> str:
    return "/".join(str(part) for part in parts) or "/"


@lru_cache(maxsize=1)
def _schema() -> dict[str, Any]:
    return json.loads(
        (_SCHEMA_DIR / "transition-plan.schema.json").read_text(encoding="utf-8")
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
        raise TransitionControlError(
            f"{contract} schema violation at {_format_path(issue.absolute_path)}: "
            f"{issue.message}"
        )


def _require_unique(
    values: Sequence[Mapping[str, Any]], field: str, location: str
) -> None:
    identities = [str(item[field]) for item in values]
    duplicates = sorted(
        {identity for identity in identities if identities.count(identity) > 1}
    )
    if duplicates:
        raise TransitionControlError(
            f"duplicate {field} at {location}: {duplicates!r}"
        )


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


def _artifact_ref_key(value: Mapping[str, Any]) -> tuple[str, str, str]:
    return (
        str(value["artifact_id"]),
        str(value["artifact_version"]),
        str(value["content_digest"]["value"]),
    )


def _validate_artifact_ref(value: Mapping[str, Any], location: str) -> None:
    _validate_schema(value, _subvalidator("artifact_ref"), location)


def _abort_ref(criterion: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "criterion_id": criterion["criterion_id"],
        "criterion_version": criterion["criterion_version"],
        "criterion_digest": copy.deepcopy(criterion["criterion_digest"]),
    }


def _entry_ref(stage: str, gate_kind: str) -> dict[str, Any]:
    material = {
        "criterion_id": f"entry.{stage}.{gate_kind}",
        "criterion_version": "transition-entry-criterion/v0",
        "gate_kind": gate_kind,
    }
    return {**material, "criterion_digest": _digest(material)}


def _stage_sequence(
    abort_criteria: Sequence[Mapping[str, Any]],
    rollback_recovery_plan_ref: Mapping[str, Any],
) -> list[dict[str, Any]]:
    abort_refs = [_abort_ref(item) for item in abort_criteria]
    return [
        {
            "stage": stage,
            "ordinal": ordinal,
            "entry_criteria_refs": [
                _entry_ref(stage, gate_kind)
                for gate_kind in STAGE_GATE_REQUIREMENTS[stage]
            ],
            "abort_criterion_refs": copy.deepcopy(abort_refs),
            "rollback_recovery_plan_ref": copy.deepcopy(
                dict(rollback_recovery_plan_ref)
            ),
        }
        for ordinal, stage in enumerate(STAGES)
    ]


def build_abort_criterion(
    *,
    criterion_id: str,
    criterion_version: str,
    metric: str,
    comparator: str,
    threshold_value: float,
    unit: str,
) -> dict[str, Any]:
    criterion: dict[str, Any] = {
        "criterion_id": criterion_id,
        "criterion_version": criterion_version,
        "metric": metric,
        "comparator": comparator,
        "threshold_value": threshold_value,
        "unit": unit,
        "trigger_action": "abort_and_rollback",
    }
    criterion["criterion_digest"] = _digest(criterion)
    validate_abort_criterion(criterion)
    return criterion


def validate_abort_criterion(criterion: Mapping[str, Any]) -> None:
    _validate_schema(criterion, _subvalidator("abort_criterion"), "abort criterion")
    if criterion["criterion_digest"] != _digest(
        _without(criterion, "criterion_digest")
    ):
        raise TransitionControlError("abort criterion digest mismatch")


def build_compatibility_window(
    *,
    window_id: str,
    window_version: str,
    starts_at: str,
    ends_at: str,
    predecessor_ref: Mapping[str, Any],
    successor_ref: Mapping[str, Any],
    compatibility_evidence_ref: Mapping[str, Any],
) -> dict[str, Any]:
    window: dict[str, Any] = {
        "window_id": window_id,
        "window_version": window_version,
        "starts_at": starts_at,
        "ends_at": ends_at,
        "predecessor_ref": copy.deepcopy(dict(predecessor_ref)),
        "successor_ref": copy.deepcopy(dict(successor_ref)),
        "compatibility_evidence_ref": copy.deepcopy(
            dict(compatibility_evidence_ref)
        ),
    }
    window["window_digest"] = _digest(window)
    validate_compatibility_window(window)
    return window


def validate_compatibility_window(window: Mapping[str, Any]) -> None:
    _validate_schema(
        window,
        _subvalidator("compatibility_window"),
        "compatibility window",
    )
    starts = _parse_time(str(window["starts_at"]), "compatibility_window.starts_at")
    ends = _parse_time(str(window["ends_at"]), "compatibility_window.ends_at")
    if ends <= starts:
        raise TransitionControlError(
            "compatibility window ends_at must follow starts_at"
        )
    if window["predecessor_ref"] == window["successor_ref"]:
        raise TransitionControlError(
            "transition predecessor and successor cannot be the same identity"
        )
    _validate_artifact_ref(
        window["compatibility_evidence_ref"],
        "compatibility evidence ref",
    )
    if window["window_digest"] != _digest(_without(window, "window_digest")):
        raise TransitionControlError("compatibility window digest mismatch")


def build_stage_completion(
    *,
    stage: str,
    completed_at: str,
    scope_digest: Mapping[str, Any],
    completion_ref: Mapping[str, Any],
    evidence_origin: str,
) -> dict[str, Any]:
    completion: dict[str, Any] = {
        "stage": stage,
        "completed_at": completed_at,
        "status": "completed",
        "scope_digest": copy.deepcopy(dict(scope_digest)),
        "completion_ref": copy.deepcopy(dict(completion_ref)),
        "evidence_origin": evidence_origin,
    }
    completion["completion_digest"] = _digest(completion)
    validate_stage_completion(completion)
    return completion


def validate_stage_completion(completion: Mapping[str, Any]) -> None:
    _validate_schema(
        completion,
        _subvalidator("stage_completion"),
        "stage completion",
    )
    _parse_time(str(completion["completed_at"]), "stage_completion.completed_at")
    if completion["completion_digest"] != _digest(
        _without(completion, "completion_digest")
    ):
        raise TransitionControlError("stage completion digest mismatch")


def build_gate_evidence(
    *,
    gate_id: str,
    gate_kind: str,
    target_stage: str,
    artifact_ref: Mapping[str, Any],
    scope_digest: Mapping[str, Any],
    execution_id: str,
    status: str,
    observed_at: str,
    expires_at: str,
    time_trust: str,
    trust_class: str,
    evidence_origin: str,
    before_state_digest: Mapping[str, Any] | None = None,
    after_state_digest: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    evidence: dict[str, Any] = {
        "gate_id": gate_id,
        "gate_kind": gate_kind,
        "target_stage": target_stage,
        "artifact_ref": copy.deepcopy(dict(artifact_ref)),
        "scope_digest": copy.deepcopy(dict(scope_digest)),
        "execution_id": execution_id,
        "status": status,
        "observed_at": observed_at,
        "expires_at": expires_at,
        "time_trust": time_trust,
        "trust_class": trust_class,
        "evidence_origin": evidence_origin,
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
    }
    evidence["evidence_digest"] = _digest(evidence)
    validate_gate_evidence(evidence)
    return evidence


def validate_gate_evidence(evidence: Mapping[str, Any]) -> None:
    _validate_schema(evidence, _subvalidator("gate_evidence"), "gate evidence")
    observed = _parse_time(str(evidence["observed_at"]), "gate_evidence.observed_at")
    expires = _parse_time(str(evidence["expires_at"]), "gate_evidence.expires_at")
    if expires <= observed:
        raise TransitionControlError("gate evidence expires_at must follow observed_at")
    before = evidence["before_state_digest"]
    after = evidence["after_state_digest"]
    if evidence["gate_kind"] == "rollback_recovery_rehearsal":
        if before is None or after is None:
            raise TransitionControlError(
                "rollback/recovery rehearsal requires before and after state digests"
            )
    if before is not None and after is not None and before == after:
        raise TransitionControlError(
            "rollback/recovery before and after states are identical"
        )
    if evidence["evidence_digest"] != _digest(
        _without(evidence, "evidence_digest")
    ):
        raise TransitionControlError("gate evidence digest mismatch")


def build_abort_observation(
    *,
    observation_id: str,
    criterion: Mapping[str, Any],
    target_stage: str,
    scope_digest: Mapping[str, Any],
    execution_id: str,
    observed_at: str,
    triggered: bool,
    response: str,
    evidence_origin: str,
    evidence_ref: Mapping[str, Any],
) -> dict[str, Any]:
    validate_abort_criterion(criterion)
    observation: dict[str, Any] = {
        "observation_id": observation_id,
        "criterion_ref": _abort_ref(criterion),
        "target_stage": target_stage,
        "scope_digest": copy.deepcopy(dict(scope_digest)),
        "execution_id": execution_id,
        "observed_at": observed_at,
        "triggered": triggered,
        "response": response,
        "evidence_origin": evidence_origin,
        "evidence_ref": copy.deepcopy(dict(evidence_ref)),
    }
    observation["observation_digest"] = _digest(observation)
    validate_abort_observation(observation, criterion=criterion)
    return observation


def validate_abort_observation(
    observation: Mapping[str, Any],
    *,
    criterion: Mapping[str, Any] | None = None,
) -> None:
    _validate_schema(
        observation,
        _subvalidator("abort_observation"),
        "abort observation",
    )
    _parse_time(str(observation["observed_at"]), "abort_observation.observed_at")
    if criterion is not None and observation["criterion_ref"] != _abort_ref(criterion):
        raise TransitionControlError("abort observation criterion reference mismatch")
    if observation["triggered"] and observation["response"] != "aborted_and_rollback_started":
        raise TransitionControlError(
            "abort criterion was triggered but execution continued or rollback was not started"
        )
    if not observation["triggered"] and observation["response"] != "not_triggered":
        raise TransitionControlError(
            "untriggered abort criterion has an inconsistent response"
        )
    if observation["observation_digest"] != _digest(
        _without(observation, "observation_digest")
    ):
        raise TransitionControlError("abort observation digest mismatch")


def _validate_transition_decision(
    record: Mapping[str, Any],
    *,
    expected_kind: str,
    target_id: str,
    target_version: str,
    target_stage: str | None,
    target_digest: Mapping[str, Any],
    require_irreversibility_ack: bool,
    not_after: str | None = None,
) -> None:
    _validate_schema(
        record,
        _subvalidator("external_human_decision"),
        "transition human decision",
    )
    if (
        record["decision_kind"] != expected_kind
        or record["target_id"] != target_id
        or record["target_version"] != target_version
        or record["target_stage"] != target_stage
        or record["target_digest"] != target_digest
    ):
        raise TransitionControlError(
            "transition human decision target or decision kind mismatch"
        )
    acknowledgements = record["acknowledgements"]
    expected_ack = require_irreversibility_ack
    if (
        acknowledgements["rollback_unavailable"] is not expected_ack
        or acknowledgements["predecessor_recovery_unavailable"] is not expected_ack
    ):
        raise TransitionControlError(
            "transition human decision irreversibility acknowledgements mismatch"
        )
    decided_at = _parse_time(str(record["decided_at"]), "decision.decided_at")
    if not_after is not None and decided_at > _parse_time(not_after, "not_after"):
        raise TransitionControlError(
            "transition human decision occurs after the gate assessment"
        )


def _configuration_material(plan: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: copy.deepcopy(plan[key])
        for key in (
            "schema_version",
            "plan_id",
            "plan_version",
            "predecessor_ref",
            "successor_ref",
            "deployment_envelope_ref",
            "operational_qualification_ref",
            "scope_digest",
            "stage_sequence",
            "abort_criteria",
            "compatibility_window",
            "migration_plan_refs",
            "rollback_recovery_plan_ref",
            "disposal_retirement_plan_ref",
        )
    }


def _gate_set_material(plan: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "plan_configuration_digest": copy.deepcopy(
            plan["plan_configuration_digest"]
        ),
        "target_stage": plan["target_stage"],
        "stage_history": copy.deepcopy(plan["stage_history"]),
        "gate_evidence": copy.deepcopy(plan["gate_evidence"]),
        "abort_observations": copy.deepcopy(plan["abort_observations"]),
        "operational_qualification_ref": copy.deepcopy(
            plan["operational_qualification_ref"]
        ),
        "assessed_at": plan["assessed_at"],
        "time_trust": plan["time_trust"],
    }


def _retirement_basis_material(plan: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "plan_id": plan["plan_id"],
        "plan_version": plan["plan_version"],
        "target_stage": "predecessor_retired",
        "predecessor_ref": copy.deepcopy(plan["predecessor_ref"]),
        "disposal_retirement_plan_ref": copy.deepcopy(
            plan["disposal_retirement_plan_ref"]
        ),
        "gate_set_digest": copy.deepcopy(plan["gate_set_digest"]),
        "rollback_available_after_retirement": False,
        "predecessor_recovery_available_after_retirement": False,
    }


def _history_prefix(target_stage: str) -> tuple[str, ...]:
    return STAGES[: STAGES.index(target_stage)]


def _qualification_current_at(
    qualification: Mapping[str, Any], assessed_at: str
) -> bool:
    assessed = _parse_time(assessed_at, "transition.assessed_at")
    max_age = timedelta(
        seconds=int(qualification["profile_ref"]["max_evidence_age_seconds"])
    )
    for observation in qualification["scenario_observations"]:
        observed = _parse_time(
            str(observation["observed_at"]),
            "operational_observation.observed_at",
        )
        expires = _parse_time(
            str(observation["expires_at"]),
            "operational_observation.expires_at",
        )
        if assessed < observed or assessed >= expires or assessed - observed > max_age:
            return False
    return True


def _derive_transition_outcome_reasons(
    plan: Mapping[str, Any],
    *,
    operational_qualification: Mapping[str, Any],
) -> list[str]:
    reasons: list[str] = []

    def add(reason: str) -> None:
        if reason not in reasons:
            reasons.append(reason)

    if plan["adoption_state"] != "adopted":
        add("transition_plan_not_adopted")
    if plan["time_trust"] != "trusted":
        add("transition_assessment_time_untrusted")
    assessed = _parse_time(str(plan["assessed_at"]), "assessed_at")
    if plan["adoption_decision_ref"] is not None and assessed < _parse_time(
        str(plan["adoption_decision_ref"]["decided_at"]),
        "adoption_decision.decided_at",
    ):
        add("transition_assessment_precedes_plan_adoption")
    window_start = _parse_time(
        str(plan["compatibility_window"]["starts_at"]),
        "compatibility_window.starts_at",
    )
    window_end = _parse_time(
        str(plan["compatibility_window"]["ends_at"]),
        "compatibility_window.ends_at",
    )
    if plan["target_stage"] == "default" and not (
        window_start <= assessed < window_end
    ):
        add("default_outside_compatibility_window")
    elif plan["target_stage"] != "predecessor_retired" and assessed >= window_end:
        add("transition_evidence_after_compatibility_window")
    elif assessed < window_start:
        add("transition_precedes_compatibility_window")

    if operational_qualification["outcome"] not in {
        "eligible",
        "human_authorized",
    }:
        add("operational_qualification_not_eligible")
    if not _qualification_current_at(operational_qualification, str(plan["assessed_at"])):
        add("operational_qualification_stale")

    for evidence in plan["gate_evidence"]:
        gate = str(evidence["gate_kind"])
        observed = _parse_time(str(evidence["observed_at"]), "gate.observed_at")
        expires = _parse_time(str(evidence["expires_at"]), "gate.expires_at")
        if evidence["status"] != "passed":
            add(f"gate_{gate}_{evidence['status']}")
        if evidence["evidence_origin"] == "synthetic_fixture":
            add(f"gate_{gate}_synthetic")
        if evidence["time_trust"] != "trusted":
            add(f"gate_{gate}_time_untrusted")
        if assessed < observed or assessed >= expires:
            add(f"gate_{gate}_stale")
        if gate in INDEPENDENT_GATE_KINDS and evidence["trust_class"] not in {
            "independently_observed",
            "signed",
        }:
            add(f"gate_{gate}_not_independent")
    for completion in plan["stage_history"]:
        if completion["evidence_origin"] == "synthetic_fixture":
            add(f"stage_{completion['stage']}_synthetic_completion")
    if any(item["triggered"] for item in plan["abort_observations"]):
        add("abort_condition_triggered")
    return sorted(reasons)


def build_transition_plan(
    *,
    plan_id: str,
    plan_version: str,
    adoption_state: str,
    predecessor_ref: Mapping[str, Any],
    successor_ref: Mapping[str, Any],
    operational_profile: Mapping[str, Any],
    deployment_envelope: Mapping[str, Any],
    operational_qualification: Mapping[str, Any],
    abort_criteria: Sequence[Mapping[str, Any]],
    compatibility_window: Mapping[str, Any],
    migration_plan_refs: Mapping[str, Any],
    rollback_recovery_plan_ref: Mapping[str, Any],
    disposal_retirement_plan_ref: Mapping[str, Any],
    target_stage: str,
    stage_history: Sequence[Mapping[str, Any]],
    gate_evidence: Sequence[Mapping[str, Any]],
    abort_observations: Sequence[Mapping[str, Any]],
    assessed_at: str,
    time_trust: str,
    adoption_decision_ref: Mapping[str, Any] | None = None,
    retirement_decision_ref: Mapping[str, Any] | None = None,
    cutover_decision_ref: Mapping[str, Any] | None = None,
    irreversibility_decision_ref: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if target_stage not in STAGE_GATE_REQUIREMENTS:
        raise TransitionControlError(f"unknown transition target stage: {target_stage}")
    validate_operational_profile(operational_profile)
    validate_deployment_envelope(
        deployment_envelope,
        operational_profile=operational_profile,
    )
    validate_operational_qualification(
        operational_qualification,
        operational_profile=operational_profile,
        deployment_envelope=deployment_envelope,
        current_scope_manifest_refs=operational_qualification[
            "scope_manifest_refs"
        ],
    )
    _parse_time(assessed_at, "assessed_at")
    if predecessor_ref == successor_ref:
        raise TransitionControlError(
            "transition predecessor and successor cannot be the same identity"
        )
    criteria = sorted(
        (copy.deepcopy(dict(item)) for item in abort_criteria),
        key=lambda item: item["criterion_id"],
    )
    if not criteria:
        raise TransitionControlError("transition plan requires abort criteria")
    for criterion in criteria:
        validate_abort_criterion(criterion)
    _require_unique(criteria, "criterion_id", "abort_criteria")
    validate_compatibility_window(compatibility_window)
    if (
        compatibility_window["predecessor_ref"] != predecessor_ref
        or compatibility_window["successor_ref"] != successor_ref
    ):
        raise TransitionControlError(
            "compatibility window predecessor or successor reference mismatch"
        )
    _validate_schema(
        migration_plan_refs,
        _subvalidator("migration_plan_refs"),
        "migration plan refs",
    )
    for value in migration_plan_refs.values():
        _validate_artifact_ref(value, "migration plan artifact")
    _validate_artifact_ref(rollback_recovery_plan_ref, "rollback recovery plan ref")
    _validate_artifact_ref(
        disposal_retirement_plan_ref,
        "disposal retirement plan ref",
    )

    scope_digest = copy.deepcopy(operational_qualification["scope_digest"])
    history = [copy.deepcopy(dict(item)) for item in stage_history]
    for item in history:
        validate_stage_completion(item)
    required_gate_kinds = STAGE_GATE_REQUIREMENTS[target_stage]
    copied_gates = [copy.deepcopy(dict(item)) for item in gate_evidence]
    unknown_gate_kinds = sorted(
        {
            str(item.get("gate_kind"))
            for item in copied_gates
            if item.get("gate_kind") not in required_gate_kinds
        }
    )
    if unknown_gate_kinds:
        raise TransitionControlError(
            "target-stage evidence contains unknown gate kinds: "
            + ", ".join(unknown_gate_kinds)
        )
    gates = sorted(
        copied_gates,
        key=lambda item: required_gate_kinds.index(str(item["gate_kind"])),
    )
    for item in gates:
        validate_gate_evidence(item)
    aborts = sorted(
        (copy.deepcopy(dict(item)) for item in abort_observations),
        key=lambda item: str(item["criterion_ref"]["criterion_id"]),
    )
    criteria_by_id = {str(item["criterion_id"]): item for item in criteria}
    for item in aborts:
        criterion = criteria_by_id.get(str(item["criterion_ref"]["criterion_id"]))
        if criterion is None:
            raise TransitionControlError("abort observation references unknown criterion")
        validate_abort_observation(item, criterion=criterion)

    plan: dict[str, Any] = {
        "schema_version": TRANSITION_VERSION,
        "plan_id": plan_id,
        "plan_version": plan_version,
        "predecessor_ref": copy.deepcopy(dict(predecessor_ref)),
        "successor_ref": copy.deepcopy(dict(successor_ref)),
        "deployment_envelope_ref": _envelope_ref(deployment_envelope),
        "operational_qualification_ref": qualification_ref(
            operational_qualification
        ),
        "scope_digest": scope_digest,
        "stage_sequence": _stage_sequence(criteria, rollback_recovery_plan_ref),
        "abort_criteria": criteria,
        "compatibility_window": copy.deepcopy(dict(compatibility_window)),
        "migration_plan_refs": copy.deepcopy(dict(migration_plan_refs)),
        "rollback_recovery_plan_ref": copy.deepcopy(
            dict(rollback_recovery_plan_ref)
        ),
        "disposal_retirement_plan_ref": copy.deepcopy(
            dict(disposal_retirement_plan_ref)
        ),
    }
    plan["plan_configuration_digest"] = _digest(_configuration_material(plan))
    plan["adoption_state"] = adoption_state
    plan["adoption_decision_ref"] = (
        copy.deepcopy(dict(adoption_decision_ref))
        if adoption_decision_ref is not None
        else None
    )
    plan["retirement_decision_ref"] = (
        copy.deepcopy(dict(retirement_decision_ref))
        if retirement_decision_ref is not None
        else None
    )
    plan["target_stage"] = target_stage
    plan["stage_history"] = history
    plan["gate_evidence"] = gates
    plan["abort_observations"] = aborts
    plan["assessed_at"] = assessed_at
    plan["time_trust"] = time_trust
    plan["gate_set_digest"] = _digest(_gate_set_material(plan))
    plan["retirement_basis_digest"] = _digest(_retirement_basis_material(plan))
    plan["cutover_decision_ref"] = (
        copy.deepcopy(dict(cutover_decision_ref))
        if cutover_decision_ref is not None
        else None
    )
    plan["irreversibility_decision_ref"] = (
        copy.deepcopy(dict(irreversibility_decision_ref))
        if irreversibility_decision_ref is not None
        else None
    )
    reasons = _derive_transition_outcome_reasons(
        plan,
        operational_qualification=operational_qualification,
    )
    if reasons and (
        cutover_decision_ref is not None or irreversibility_decision_ref is not None
    ):
        raise TransitionControlError(
            "human decision cannot override failed, stale, synthetic, aborted, or out-of-scope transition evidence"
        )
    if not reasons and cutover_decision_ref is not None:
        _validate_transition_decision(
            plan["cutover_decision_ref"],
            expected_kind="authorize_cutover_stage",
            target_id=plan_id,
            target_version=plan_version,
            target_stage=target_stage,
            target_digest=plan["gate_set_digest"],
            require_irreversibility_ack=False,
            not_after=assessed_at,
        )
    if irreversibility_decision_ref is not None:
        if target_stage != "predecessor_retired" or cutover_decision_ref is None:
            raise TransitionControlError(
                "irreversibility decision is valid only beside a predecessor-retirement cutover decision"
            )
        _validate_transition_decision(
            plan["irreversibility_decision_ref"],
            expected_kind="authorize_irreversible_predecessor_retirement",
            target_id=plan_id,
            target_version=plan_version,
            target_stage="predecessor_retired",
            target_digest=plan["retirement_basis_digest"],
            require_irreversibility_ack=True,
            not_after=assessed_at,
        )
        if (
            plan["irreversibility_decision_ref"]["decision_id"]
            == plan["cutover_decision_ref"]["decision_id"]
        ):
            raise TransitionControlError(
                "retirement irreversibility and cutover authorization require separate decisions"
            )
    if reasons:
        plan["outcome"] = "not_eligible"
    elif cutover_decision_ref is None:
        plan["outcome"] = "eligible"
    elif target_stage == "predecessor_retired" and irreversibility_decision_ref is None:
        plan["outcome"] = "eligible"
    else:
        plan["outcome"] = "human_authorized"
    plan["limitations"] = list(_LIMITATIONS)
    plan["authority_boundary"] = copy.deepcopy(_AUTHORITY_BOUNDARY)
    plan["transition_digest"] = _digest(plan)
    validate_transition_plan(
        plan,
        operational_profile=operational_profile,
        deployment_envelope=deployment_envelope,
        operational_qualification=operational_qualification,
    )
    return plan


def validate_transition_plan(
    plan: Mapping[str, Any],
    *,
    operational_profile: Mapping[str, Any],
    deployment_envelope: Mapping[str, Any],
    operational_qualification: Mapping[str, Any],
) -> None:
    _validate_schema(plan, _validator(), "transition plan")
    validate_operational_profile(operational_profile)
    validate_deployment_envelope(
        deployment_envelope,
        operational_profile=operational_profile,
    )
    validate_operational_qualification(
        operational_qualification,
        operational_profile=operational_profile,
        deployment_envelope=deployment_envelope,
        current_scope_manifest_refs=operational_qualification[
            "scope_manifest_refs"
        ],
    )
    if plan["predecessor_ref"] == plan["successor_ref"]:
        raise TransitionControlError(
            "transition predecessor and successor cannot be the same identity"
        )
    if plan["deployment_envelope_ref"] != _envelope_ref(deployment_envelope):
        raise TransitionControlError("transition deployment envelope reference mismatch")
    if plan["operational_qualification_ref"] != qualification_ref(
        operational_qualification
    ):
        raise TransitionControlError(
            "transition operational qualification reference mismatch"
        )
    if plan["scope_digest"] != operational_qualification["scope_digest"]:
        raise TransitionControlError("transition scope digest mismatch")

    criteria = list(plan["abort_criteria"])
    for criterion in criteria:
        validate_abort_criterion(criterion)
    _require_unique(criteria, "criterion_id", "abort_criteria")
    if plan["stage_sequence"] != _stage_sequence(
        criteria,
        plan["rollback_recovery_plan_ref"],
    ):
        raise TransitionControlError("transition stage sequence does not replay exactly")
    if [item["stage"] for item in plan["stage_sequence"]] != list(STAGES):
        raise TransitionControlError("transition stage order mismatch")

    validate_compatibility_window(plan["compatibility_window"])
    if (
        plan["compatibility_window"]["predecessor_ref"] != plan["predecessor_ref"]
        or plan["compatibility_window"]["successor_ref"] != plan["successor_ref"]
    ):
        raise TransitionControlError(
            "compatibility window predecessor or successor reference mismatch"
        )
    _validate_schema(
        plan["migration_plan_refs"],
        _subvalidator("migration_plan_refs"),
        "migration plan refs",
    )
    if plan["plan_configuration_digest"] != _digest(_configuration_material(plan)):
        raise TransitionControlError("transition plan configuration digest mismatch")

    state = str(plan["adoption_state"])
    adoption = plan["adoption_decision_ref"]
    retirement = plan["retirement_decision_ref"]
    if state == "pending":
        if adoption is not None or retirement is not None:
            raise TransitionControlError(
                "pending transition plan cannot carry adoption or retirement decisions"
            )
    else:
        if adoption is None:
            raise TransitionControlError(
                "adopted or retired transition plan requires external human adoption"
            )
        _validate_transition_decision(
            adoption,
            expected_kind="adopt_transition_plan",
            target_id=str(plan["plan_id"]),
            target_version=str(plan["plan_version"]),
            target_stage=None,
            target_digest=plan["plan_configuration_digest"],
            require_irreversibility_ack=False,
        )
        if state == "adopted" and retirement is not None:
            raise TransitionControlError(
                "adopted transition plan cannot already carry plan retirement"
            )
        if state == "retired":
            if retirement is None:
                raise TransitionControlError(
                    "retired transition plan requires a separate retirement decision"
                )
            _validate_transition_decision(
                retirement,
                expected_kind="retire_transition_plan",
                target_id=str(plan["plan_id"]),
                target_version=str(plan["plan_version"]),
                target_stage=None,
                target_digest=plan["plan_configuration_digest"],
                require_irreversibility_ack=False,
            )
            if adoption["decision_id"] == retirement["decision_id"]:
                raise TransitionControlError(
                    "transition plan adoption and retirement require separate decisions"
                )
            if _parse_time(
                str(retirement["decided_at"]), "retirement_decision.decided_at"
            ) < _parse_time(
                str(adoption["decided_at"]), "adoption_decision.decided_at"
            ):
                raise TransitionControlError(
                    "transition plan retirement decision predates adoption"
                )

    history = list(plan["stage_history"])
    for completion in history:
        validate_stage_completion(completion)
        if completion["scope_digest"] != plan["scope_digest"]:
            raise TransitionControlError("stage history is outside transition scope")
        if _parse_time(str(completion["completed_at"]), "completed_at") > _parse_time(
            str(plan["assessed_at"]), "assessed_at"
        ):
            raise TransitionControlError("stage completion occurs after assessment")
    if tuple(item["stage"] for item in history) != _history_prefix(
        str(plan["target_stage"])
    ):
        raise TransitionControlError(
            "stage history must be the exact completed prefix before the target stage"
        )

    gates = list(plan["gate_evidence"])
    for evidence in gates:
        validate_gate_evidence(evidence)
        if (
            evidence["target_stage"] != plan["target_stage"]
            or evidence["scope_digest"] != plan["scope_digest"]
        ):
            raise TransitionControlError(
                "gate evidence target stage or closed scope mismatch"
            )
    if tuple(item["gate_kind"] for item in gates) != STAGE_GATE_REQUIREMENTS[
        str(plan["target_stage"])
    ]:
        raise TransitionControlError(
            "gate evidence must cover every target-stage entry requirement exactly once"
        )
    _require_unique(gates, "gate_id", "gate_evidence")
    _require_unique(gates, "execution_id", "gate_evidence")
    operational_gate = next(
        item for item in gates if item["gate_kind"] == "operational_qualification"
    )
    expected_qualification_artifact = {
        "artifact_id": operational_qualification["qualification_id"],
        "artifact_version": operational_qualification["qualification_version"],
        "content_digest": operational_qualification["qualification_digest"],
    }
    actual_qualification_artifact = {
        key: operational_gate["artifact_ref"][key]
        for key in ("artifact_id", "artifact_version", "content_digest")
    }
    if actual_qualification_artifact != expected_qualification_artifact:
        raise TransitionControlError(
            "operational gate does not exactly reference the supplied qualification"
        )
    expected_operational_status = (
        "passed"
        if operational_qualification["outcome"] in {"eligible", "human_authorized"}
        else "failed"
    )
    if operational_gate["status"] != expected_operational_status:
        raise TransitionControlError(
            "operational gate status forges the qualification outcome"
        )
    register_gate = next(
        (item for item in gates if item["gate_kind"] == "register_readiness"),
        None,
    )
    if register_gate is not None and _artifact_ref_key(
        register_gate["artifact_ref"]
    ) != _artifact_ref_key(plan["migration_plan_refs"]["register_update_ref"]):
        raise TransitionControlError(
            "register gate does not reference the bound register update plan"
        )
    migration_gate = next(
        (item for item in gates if item["gate_kind"] == "compatibility_migration"),
        None,
    )
    if migration_gate is not None and _artifact_ref_key(
        migration_gate["artifact_ref"]
    ) != _artifact_ref_key(plan["migration_plan_refs"]["evidence_migration_ref"]):
        raise TransitionControlError(
            "compatibility/migration gate does not reference the bound evidence migration plan"
        )
    rollback_gate = next(
        item for item in gates if item["gate_kind"] == "rollback_recovery_rehearsal"
    )
    if _artifact_ref_key(rollback_gate["artifact_ref"]) != _artifact_ref_key(
        plan["rollback_recovery_plan_ref"]
    ):
        raise TransitionControlError(
            "rollback/recovery gate does not reference the bound rehearsal plan"
        )

    aborts = list(plan["abort_observations"])
    criteria_by_id = {str(item["criterion_id"]): item for item in criteria}
    for observation in aborts:
        criterion = criteria_by_id.get(str(observation["criterion_ref"]["criterion_id"]))
        if criterion is None:
            raise TransitionControlError("abort observation references unknown criterion")
        validate_abort_observation(observation, criterion=criterion)
        if (
            observation["target_stage"] != plan["target_stage"]
            or observation["scope_digest"] != plan["scope_digest"]
        ):
            raise TransitionControlError(
                "abort observation target stage or scope mismatch"
            )
    if [item["criterion_ref"]["criterion_id"] for item in aborts] != [
        item["criterion_id"] for item in criteria
    ]:
        raise TransitionControlError(
            "abort observations must cover every abort criterion exactly once"
        )
    _require_unique(aborts, "observation_id", "abort_observations")
    all_execution_ids = [str(item["execution_id"]) for item in gates] + [
        str(item["execution_id"]) for item in aborts
    ]
    if len(all_execution_ids) != len(set(all_execution_ids)):
        raise TransitionControlError(
            "transition gate or rehearsal execution was replayed under multiple claims"
        )

    if plan["gate_set_digest"] != _digest(_gate_set_material(plan)):
        raise TransitionControlError("transition gate set digest mismatch")
    if plan["retirement_basis_digest"] != _digest(
        _retirement_basis_material(plan)
    ):
        raise TransitionControlError("retirement irreversibility basis digest mismatch")
    reasons = _derive_transition_outcome_reasons(
        plan,
        operational_qualification=operational_qualification,
    )
    cutover = plan["cutover_decision_ref"]
    irreversibility = plan["irreversibility_decision_ref"]
    if reasons and (cutover is not None or irreversibility is not None):
        raise TransitionControlError(
            "human decision cannot override failed, stale, synthetic, aborted, or out-of-scope transition evidence"
        )
    if cutover is not None:
        _validate_transition_decision(
            cutover,
            expected_kind="authorize_cutover_stage",
            target_id=str(plan["plan_id"]),
            target_version=str(plan["plan_version"]),
            target_stage=str(plan["target_stage"]),
            target_digest=plan["gate_set_digest"],
            require_irreversibility_ack=False,
            not_after=str(plan["assessed_at"]),
        )
    if irreversibility is not None:
        if plan["target_stage"] != "predecessor_retired" or cutover is None:
            raise TransitionControlError(
                "irreversibility decision is valid only beside predecessor-retirement cutover"
            )
        _validate_transition_decision(
            irreversibility,
            expected_kind="authorize_irreversible_predecessor_retirement",
            target_id=str(plan["plan_id"]),
            target_version=str(plan["plan_version"]),
            target_stage="predecessor_retired",
            target_digest=plan["retirement_basis_digest"],
            require_irreversibility_ack=True,
            not_after=str(plan["assessed_at"]),
        )
        if irreversibility["decision_id"] == cutover["decision_id"]:
            raise TransitionControlError(
                "retirement irreversibility and cutover require separate decisions"
            )
    if reasons:
        expected_outcome = "not_eligible"
    elif cutover is None:
        expected_outcome = "eligible"
    elif plan["target_stage"] == "predecessor_retired" and irreversibility is None:
        expected_outcome = "eligible"
    else:
        expected_outcome = "human_authorized"
    if plan["outcome"] != expected_outcome:
        raise TransitionControlError("transition outcome does not replay")
    if tuple(plan["limitations"]) != _LIMITATIONS:
        raise TransitionControlError("transition limitations mismatch")
    if plan["authority_boundary"] != _AUTHORITY_BOUNDARY:
        raise TransitionControlError("transition authority boundary mismatch")
    if plan["transition_digest"] != _digest(
        _without(plan, "transition_digest")
    ):
        raise TransitionControlError("transition digest mismatch")


__all__ = [
    "DEFAULT_RETIRE_GATES",
    "STAGES",
    "STAGE_GATE_REQUIREMENTS",
    "TransitionControlError",
    "build_abort_criterion",
    "build_abort_observation",
    "build_compatibility_window",
    "build_gate_evidence",
    "build_stage_completion",
    "build_transition_plan",
    "validate_abort_criterion",
    "validate_abort_observation",
    "validate_compatibility_window",
    "validate_gate_evidence",
    "validate_stage_completion",
    "validate_transition_plan",
]
