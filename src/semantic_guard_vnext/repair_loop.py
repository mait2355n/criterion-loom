"""Bounded repair/re-audit records and responsibility-correct material.

This module deliberately stops at audit material.  It does not dispatch a
repair, choose its priority, grant authority, ask a human on the caller's
behalf, or accept the result.  A changed artifact is never counted as a repair
effect until a separate after-audit record is bound and compared.
"""

from __future__ import annotations

import copy
from datetime import datetime
from functools import lru_cache
import hashlib
import json
from typing import Any, Iterable, Mapping, Sequence

from jsonschema import Draft202012Validator, FormatChecker

from .schema_access import schema_directory


RESPONSIBILITY_POLICY_VERSION = "responsibility-policy/v2"
RESPONSIBILITY_MATERIAL_VERSION = "responsibility-material/v0"
REPAIR_CYCLE_VERSION = "repair-cycle/v2"
REPAIR_REVIEW_VERSION = "repair-independent-review/v1"
_REPAIR_EFFECT_TRANSITION_RULE = "repair-effect-transition/v1"

_SCHEMA_DIR = schema_directory()
_HUMAN_ONLY_RIGHTS = frozenset(
    {
        "change_intent_or_scope",
        "accept_residual_risk",
        "grant_or_expand_authority",
        "authorize_external_effect",
        "final_acceptance",
    }
)
_HUMAN_CLASSES = frozenset(
    {"human_requester", "human_reviewer", "human_approver"}
)
_REQUIRED_SHORTCUT_BARRIERS = frozenset(
    {
        "finding_suppression_is_not_repair",
        "changed_output_without_reaudit_is_not_success",
    }
)
_LOCAL_EFFECT_LIMITATION = (
    "The effect is limited to the declared before/after audit and does not "
    "establish field repair effectiveness, human comprehension, or acceptance."
)
_AUTHORITY_LIMITATION = (
    "semantic-guard emitted audit material only; execution, sequencing, "
    "authority, escalation, and acceptance remain external."
)
_REVIEW_LIMITATION = (
    "Independent-review identity, record, and evidence are structurally bound, "
    "but their external existence, authenticity, and organizational independence "
    "remain unproved."
)


class RepairContractError(ValueError):
    """Raised when a repair or responsibility contract fails closed."""


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _digest(value: Any) -> dict[str, str]:
    return {
        "algorithm": "sha256",
        "value": hashlib.sha256(_canonical(value)).hexdigest(),
    }


def _without(value: Mapping[str, Any], *fields: str) -> dict[str, Any]:
    result = copy.deepcopy(dict(value))
    for field in fields:
        result.pop(field, None)
    return result


def _derived_id(prefix: str, value: Mapping[str, Any], *excluded: str) -> str:
    material = _without(value, *excluded)
    return f"{prefix}." + hashlib.sha256(_canonical(material)).hexdigest()


def _digest_key(value: Mapping[str, Any]) -> tuple[str, str]:
    return str(value["algorithm"]), str(value["value"])


def _digest_is_placeholder(value: Mapping[str, Any]) -> bool:
    return str(value.get("value", "")) == "0" * 64


def _ref_key(value: Mapping[str, Any]) -> tuple[str, str]:
    return str(value["entity_id"]), str(value["entity_digest"]["value"])


def _versioned_ref_key(value: Mapping[str, Any]) -> tuple[str, str, str]:
    return (
        str(value["entity_id"]),
        str(value["entity_version"]),
        str(value["entity_digest"]["value"]),
    )


def _policy_ref(policy: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "entity_id": policy["policy_id"],
        "entity_version": policy["policy_version"],
        "entity_digest": copy.deepcopy(policy["policy_digest"]),
    }


def _material_ref(material: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "entity_id": material["material_id"],
        "entity_digest": copy.deepcopy(material["material_digest"]),
    }


def _responsibility_policy_basis_material(
    policy: Mapping[str, Any],
) -> dict[str, Any]:
    return _without(
        policy,
        "adoption_state",
        "human_decision_ref",
        "policy_basis_digest",
        "policy_digest",
    )


@lru_cache(maxsize=None)
def _validator(name: str) -> Draft202012Validator:
    schema = json.loads((_SCHEMA_DIR / name).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


@lru_cache(maxsize=1)
def _independent_review_validator() -> Draft202012Validator:
    root = json.loads(
        (_SCHEMA_DIR / "repair-cycle.schema.json").read_text(encoding="utf-8")
    )
    schema = {
        "$schema": root["$schema"],
        "$defs": root["$defs"],
        "$ref": "#/$defs/independent_review_record",
    }
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _schema_validate(value: Mapping[str, Any], name: str, contract: str) -> None:
    errors = sorted(
        _validator(name).iter_errors(value),
        key=lambda item: tuple(str(part) for part in item.absolute_path),
    )
    if errors:
        issue = errors[0]
        location = "/".join(str(part) for part in issue.absolute_path) or "/"
        raise RepairContractError(
            f"{contract} schema violation at {location}: {issue.message}"
        )


def _validate_independent_review_schema(review: Mapping[str, Any]) -> None:
    errors = sorted(
        _independent_review_validator().iter_errors(review),
        key=lambda item: tuple(str(part) for part in item.absolute_path),
    )
    if errors:
        issue = errors[0]
        location = "/".join(str(part) for part in issue.absolute_path) or "/"
        raise RepairContractError(
            f"independent repair review schema violation at {location}: "
            f"{issue.message}"
        )


def _unique(values: Sequence[Mapping[str, Any]], field: str, location: str) -> None:
    seen: set[str] = set()
    for item in values:
        value = str(item[field])
        if value in seen:
            raise RepairContractError(f"duplicate {field} in {location}: {value}")
        seen.add(value)


def _parse_time(value: str, location: str) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith(("Z", "z")) else value
    try:
        result = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise RepairContractError(f"invalid timestamp at {location}: {value}") from exc
    if result.tzinfo is None or result.utcoffset() is None:
        raise RepairContractError(f"timestamp lacks timezone at {location}: {value}")
    return result


def build_responsibility_policy(
    *,
    policy_id: str,
    policy_version: str,
    adoption_state: str,
    roles: Sequence[Mapping[str, Any]],
    issue_rules: Sequence[Mapping[str, Any]],
    human_decision_ref: Mapping[str, Any] | None = None,
    repair_effect_policy: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a policy record without inventing its human adoption."""

    policy: dict[str, Any] = {
        "schema_version": RESPONSIBILITY_POLICY_VERSION,
        "policy_id": policy_id,
        "policy_version": policy_version,
        "adoption_state": adoption_state,
        "human_decision_ref": (
            copy.deepcopy(dict(human_decision_ref))
            if human_decision_ref is not None
            else None
        ),
        "roles": sorted(
            (copy.deepcopy(dict(item)) for item in roles),
            key=lambda item: item["role_id"],
        ),
        "issue_rules": sorted(
            (copy.deepcopy(dict(item)) for item in issue_rules),
            key=lambda item: item["issue_class"],
        ),
        "repair_effect_policy": copy.deepcopy(
            dict(
                repair_effect_policy
                or {
                    "transition_rule_id": _REPAIR_EFFECT_TRANSITION_RULE,
                    "independent_review_required": True,
                }
            )
        ),
    }
    policy["policy_basis_digest"] = _digest(
        _responsibility_policy_basis_material(policy)
    )
    policy["policy_digest"] = _digest(policy)
    validate_responsibility_policy(policy)
    return policy


def validate_responsibility_policy(policy: Mapping[str, Any]) -> None:
    _schema_validate(
        policy,
        "responsibility-policy.schema.json",
        "responsibility policy",
    )
    expected = _digest(_without(policy, "policy_digest"))
    if policy["policy_digest"] != expected:
        raise RepairContractError("responsibility policy digest mismatch")
    expected_basis = _digest(_responsibility_policy_basis_material(policy))
    if policy["policy_basis_digest"] != expected_basis:
        raise RepairContractError("responsibility policy basis digest mismatch")
    if policy["adoption_state"] == "adopted":
        decision = policy["human_decision_ref"]
        if decision["decided_by"] != decision["decision_maker_identity"][
            "entity_id"
        ]:
            raise RepairContractError(
                "responsibility policy decision identity does not match decided_by"
            )
        expected_target = {
            "decision_kind": "adopt_responsibility_policy",
            "target_id": policy["policy_id"],
            "target_version": policy["policy_version"],
            "target_basis_digest": policy["policy_basis_digest"],
        }
        for field, expected_value in expected_target.items():
            if decision[field] != expected_value:
                raise RepairContractError(
                    f"human adoption decision {field} does not target this responsibility policy basis"
                )

    roles = list(policy["roles"])
    rules = list(policy["issue_rules"])
    _unique(roles, "role_id", "roles")
    _unique(rules, "issue_class", "issue_rules")
    role_by_id = {str(item["role_id"]): item for item in roles}
    if not any(item["actor_class"] == "coding_agent" for item in roles):
        raise RepairContractError("policy must define at least one coding-agent role")
    if not any(item["actor_class"] in _HUMAN_CLASSES for item in roles):
        raise RepairContractError("policy must define at least one human role")

    for role in roles:
        rights = set(role["decision_rights"])
        if role["actor_class"] not in _HUMAN_CLASSES and rights & _HUMAN_ONLY_RIGHTS:
            denied = sorted(rights & _HUMAN_ONLY_RIGHTS)
            raise RepairContractError(
                f"non-human role {role['role_id']} cannot hold human-only rights: {denied}"
            )

    for rule in rules:
        accountable = str(rule["accountable_role_id"])
        permitted = tuple(str(item) for item in rule["permitted_role_ids"])
        unknown = sorted(({accountable, *permitted}) - set(role_by_id))
        if unknown:
            raise RepairContractError(
                f"issue rule {rule['issue_class']} references unknown roles: {unknown}"
            )
        if accountable not in permitted:
            raise RepairContractError(
                f"accountable role must be among permitted roles for {rule['issue_class']}"
            )
        required = str(rule["required_right"])
        for role_id in permitted:
            if required not in role_by_id[role_id]["decision_rights"]:
                raise RepairContractError(
                    f"role {role_id} lacks {required} for {rule['issue_class']}"
                )
        if required in _HUMAN_ONLY_RIGHTS and any(
            role_by_id[role_id]["actor_class"] not in _HUMAN_CLASSES
            for role_id in permitted
        ):
            raise RepairContractError(
                f"human-only issue {rule['issue_class']} permits a non-human role"
            )


def _role_and_rule(
    policy: Mapping[str, Any], role_id: str, issue_class: str
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    role = next(
        (item for item in policy["roles"] if item["role_id"] == role_id),
        None,
    )
    if role is None:
        raise RepairContractError(f"unknown audience role: {role_id}")
    rule = next(
        (item for item in policy["issue_rules"] if item["issue_class"] == issue_class),
        None,
    )
    if rule is None:
        raise RepairContractError(f"no responsibility rule for issue: {issue_class}")
    return role, rule


def build_responsibility_material(
    *,
    policy: Mapping[str, Any],
    material_kind: str,
    audience_role_id: str,
    audit_ref: Mapping[str, Any],
    subject_ref: Mapping[str, Any],
    issue_class: str,
    observed_facts: Sequence[str],
    evidence_refs: Sequence[Mapping[str, Any]],
    limitations: Sequence[str],
    unresolved_scope: Sequence[str],
    repair_targets: Sequence[Mapping[str, Any]] = (),
    decision_questions: Sequence[Mapping[str, Any]] = (),
    available_actions: Sequence[Mapping[str, Any]] = (),
    stop_conditions: Sequence[str],
    escalation_conditions: Sequence[str],
) -> dict[str, Any]:
    """Project audit facts for one responsibility layer.

    An adopted external policy is required because selecting decision rights is
    a human governance act, not a semantic-guard default.
    """

    validate_responsibility_policy(policy)
    if policy["adoption_state"] != "adopted":
        raise RepairContractError(
            "responsibility material requires an externally adopted policy"
        )
    role, _rule = _role_and_rule(policy, audience_role_id, issue_class)
    prohibited = sorted(
        _HUMAN_ONLY_RIGHTS - set(role["decision_rights"])
        if role["actor_class"] == "coding_agent"
        else {"final_acceptance"} - set(role["decision_rights"])
    )
    if not prohibited:
        # A material projection must still say what it does not decide.
        prohibited = ["grant_or_expand_authority"]

    material: dict[str, Any] = {
        "schema_version": RESPONSIBILITY_MATERIAL_VERSION,
        "material_kind": material_kind,
        "audience": {
            "role_id": audience_role_id,
            "actor_class": role["actor_class"],
        },
        "policy_ref": _policy_ref(policy),
        "audit_ref": copy.deepcopy(dict(audit_ref)),
        "subject_ref": copy.deepcopy(dict(subject_ref)),
        "issue_class": issue_class,
        "observed_facts": list(observed_facts),
        "evidence_refs": [copy.deepcopy(dict(item)) for item in evidence_refs],
        "limitations": list(limitations),
        "unresolved_scope": list(unresolved_scope),
        "repair_targets": sorted(
            (copy.deepcopy(dict(item)) for item in repair_targets),
            key=lambda item: item["target_id"],
        ),
        "decision_questions": sorted(
            (copy.deepcopy(dict(item)) for item in decision_questions),
            key=lambda item: item["question_id"],
        ),
        "available_actions": sorted(
            (copy.deepcopy(dict(item)) for item in available_actions),
            key=lambda item: item["action_id"],
        ),
        "stop_conditions": list(stop_conditions),
        "escalation_conditions": list(escalation_conditions),
        "prohibited_decisions": prohibited,
        "routing_boundary": {
            "semantic_guard_role": "emit_audit_material_only",
            "routing_owner": "external_caller_or_control_plane",
            "is_command": False,
            "is_authority_grant": False,
            "is_human_decision": False,
        },
    }
    material["material_id"] = _derived_id(
        "responsibility-material", material, "material_id", "material_digest"
    )
    material["material_digest"] = _digest(material)
    validate_responsibility_material(material, policy)
    return material


def validate_responsibility_material(
    material: Mapping[str, Any], policy: Mapping[str, Any]
) -> None:
    _schema_validate(
        material,
        "responsibility-material.schema.json",
        "responsibility material",
    )
    validate_responsibility_policy(policy)
    if policy["adoption_state"] != "adopted":
        raise RepairContractError(
            "responsibility material cannot rely on an unadopted policy"
        )
    if _versioned_ref_key(material["policy_ref"]) != _versioned_ref_key(
        _policy_ref(policy)
    ):
        raise RepairContractError("responsibility policy reference mismatch")

    expected_id = _derived_id(
        "responsibility-material",
        material,
        "material_id",
        "material_digest",
    )
    if material["material_id"] != expected_id:
        raise RepairContractError("responsibility material id mismatch")
    expected_digest = _digest(_without(material, "material_digest"))
    if material["material_digest"] != expected_digest:
        raise RepairContractError("responsibility material digest mismatch")

    role, rule = _role_and_rule(
        policy,
        str(material["audience"]["role_id"]),
        str(material["issue_class"]),
    )
    if material["audience"]["actor_class"] != role["actor_class"]:
        raise RepairContractError("audience actor class differs from adopted policy")
    role_rights = set(role["decision_rights"])
    for action in material["available_actions"]:
        required = str(action["required_right"])
        if required not in role_rights:
            raise RepairContractError(
                f"audience role lacks action right {required}: {action['action_id']}"
            )
        if action["side_effect_class"] in {"external", "irreversible_or_unknown"}:
            raise RepairContractError(
                "audit material cannot present external or irreversible work as an available action"
            )

    if material["material_kind"] == "agent_repair":
        missing = _HUMAN_ONLY_RIGHTS - set(material["prohibited_decisions"])
        if missing:
            raise RepairContractError(
                f"agent material fails to prohibit human-only decisions: {sorted(missing)}"
            )
        for target in material["repair_targets"]:
            barriers = set(target["prohibited_shortcuts"])
            if not _REQUIRED_SHORTCUT_BARRIERS <= barriers:
                raise RepairContractError(
                    f"repair target {target['target_id']} lacks anti-gaming barriers"
                )
    else:
        if str(material["audience"]["role_id"]) not in rule["permitted_role_ids"]:
            raise RepairContractError(
                "human decision material audience is not permitted by the adopted rule"
            )
        for question in material["decision_questions"]:
            if question["required_right"] != rule["required_right"]:
                raise RepairContractError(
                    "decision question right differs from the adopted issue rule"
                )
            if question["required_right"] not in role_rights:
                raise RepairContractError(
                    "human audience lacks the decision right named by the question"
                )


def _effect_basis_material(effect: Mapping[str, Any]) -> dict[str, Any]:
    return _without(effect, "effect_basis_digest", "independent_review_refs")


def _seal_effect_basis(effect: dict[str, Any]) -> dict[str, Any]:
    effect["effect_basis_digest"] = _digest(_effect_basis_material(effect))
    return effect


def _empty_effect(findings: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return _seal_effect_basis({
        "status": "not_assessed",
        "claim_scope": "declared_local_reaudit_only",
        "field_repair_effect": "not_evaluated",
        "finding_results": [],
        "regression_results": [],
        "escalation_result": "not_assessed",
        "overall_effect": "not_assessed",
        "unresolved_remainder": sorted(str(item["finding_id"]) for item in findings),
        "independent_review_refs": [],
        "limitations": [
            _LOCAL_EFFECT_LIMITATION,
            _AUTHORITY_LIMITATION,
            _REVIEW_LIMITATION,
        ],
    })


def _cycle_identity_material(cycle: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": cycle["schema_version"],
        "subject_ref": cycle["subject_ref"],
        "before_audit_ref": cycle["before_audit_ref"],
        "findings": cycle["findings"],
    }


def _cycle_identity_ref(cycle: Mapping[str, Any]) -> dict[str, Any]:
    basis = _without(
        cycle,
        "after_audit_ref",
        "effect_assessment",
        "cycle_digest",
    )
    return {
        "cycle_id": cycle["cycle_id"],
        "cycle_basis_digest": _digest(basis),
    }


def _validate_independent_review_intrinsic(review: Mapping[str, Any]) -> None:
    _validate_independent_review_schema(review)
    if review["schema_version"] != REPAIR_REVIEW_VERSION:
        raise RepairContractError("unsupported independent repair review version")
    if review["reviewer_kind"] != "human":
        raise RepairContractError("independent repair reviewer must be human")
    if review["relationship_to_subject"] != "independent":
        raise RepairContractError("repair review relationship must be independent")
    if review["external_to_semantic_guard"] is not True:
        raise RepairContractError("repair review must be external to semantic-guard")
    if review["authenticity_status"] != "unverified":
        raise RepairContractError(
            "repair review external authenticity must remain unverified"
        )
    if review["status"] != "accepted":
        raise RepairContractError("independent repair review is not accepted")
    _parse_time(review["reviewed_at"], "independent_review.reviewed_at")
    evidence_refs = list(review["evidence_refs"])
    if not evidence_refs:
        raise RepairContractError("independent repair review requires evidence")
    _unique(evidence_refs, "entity_id", "independent_review.evidence_refs")
    protected_digests = [
        review["reviewer_identity"]["entity_digest"],
        review["target_cycle_ref"]["cycle_basis_digest"],
        review["target_after_audit_ref"]["entity_digest"],
        review["target_effect_basis_digest"],
        review["record_ref"]["record_digest"],
        *(item["entity_digest"] for item in evidence_refs),
    ]
    if any(_digest_is_placeholder(item) for item in protected_digests):
        raise RepairContractError(
            "independent repair review cannot use a zero placeholder digest"
        )
    expected = _digest(_without(review, "review_digest"))
    if review["review_digest"] != expected:
        raise RepairContractError("independent repair review digest mismatch")


def _validate_independent_review_record(
    review: Mapping[str, Any],
    *,
    cycle: Mapping[str, Any],
    after_audit_ref: Mapping[str, Any],
    effect_basis_digest: Mapping[str, Any],
) -> None:
    _validate_independent_review_intrinsic(review)
    if review["target_cycle_ref"] != _cycle_identity_ref(cycle):
        raise RepairContractError("repair review targets another cycle identity")
    if review["target_after_audit_ref"] != after_audit_ref:
        raise RepairContractError("repair review targets another after-audit record")
    if review["target_effect_basis_digest"] != effect_basis_digest:
        raise RepairContractError("repair review targets another effect basis")
    attempt = cycle["repair_attempt"]
    if attempt is None:
        raise RepairContractError("repair review requires a recorded attempt")
    if _parse_time(review["reviewed_at"], "independent_review.reviewed_at") < _parse_time(
        attempt["completed_at"], "repair_attempt.completed_at"
    ):
        raise RepairContractError("independent repair review predates the repair attempt")


def build_independent_repair_review(
    *,
    review_id: str,
    reviewer_identity: Mapping[str, Any],
    target_cycle_ref: Mapping[str, Any],
    target_after_audit_ref: Mapping[str, Any],
    target_effect_basis_digest: Mapping[str, Any],
    reviewed_at: str,
    evidence_refs: Sequence[Mapping[str, Any]],
    record_ref: Mapping[str, Any],
    limitations: Sequence[str],
    reviewer_kind: str = "human",
    relationship_to_subject: str = "independent",
    external_to_semantic_guard: bool = True,
    status: str = "accepted",
    authenticity_status: str = "unverified",
) -> dict[str, Any]:
    """Shape a digest-bound external review without authenticating it."""

    review: dict[str, Any] = {
        "schema_version": REPAIR_REVIEW_VERSION,
        "review_id": review_id,
        "reviewer_identity": copy.deepcopy(dict(reviewer_identity)),
        "reviewer_kind": reviewer_kind,
        "relationship_to_subject": relationship_to_subject,
        "external_to_semantic_guard": external_to_semantic_guard,
        "target_cycle_ref": copy.deepcopy(dict(target_cycle_ref)),
        "target_after_audit_ref": copy.deepcopy(dict(target_after_audit_ref)),
        "target_effect_basis_digest": copy.deepcopy(
            dict(target_effect_basis_digest)
        ),
        "status": status,
        "reviewed_at": reviewed_at,
        "authenticity_status": authenticity_status,
        "evidence_refs": [copy.deepcopy(dict(item)) for item in evidence_refs],
        "record_ref": copy.deepcopy(dict(record_ref)),
        "limitations": list(dict.fromkeys([*limitations, _REVIEW_LIMITATION])),
    }
    review["review_digest"] = _digest(review)
    _validate_independent_review_intrinsic(review)
    return review


def build_repair_cycle(
    *,
    subject_ref: Mapping[str, Any],
    before_audit_ref: Mapping[str, Any],
    findings: Sequence[Mapping[str, Any]],
    responsibility_materials: Sequence[Mapping[str, Any]],
    responsibility_policy: Mapping[str, Any],
) -> dict[str, Any]:
    """Create a finding-to-repair plan; no execution is implied."""

    normalized_findings = sorted(
        (copy.deepcopy(dict(item)) for item in findings),
        key=lambda item: item["finding_id"],
    )
    cycle: dict[str, Any] = {
        "schema_version": REPAIR_CYCLE_VERSION,
        "subject_ref": copy.deepcopy(dict(subject_ref)),
        "before_audit_ref": copy.deepcopy(dict(before_audit_ref)),
        "findings": normalized_findings,
        "repair_attempt": None,
        "after_audit_ref": None,
        "effect_assessment": _empty_effect(normalized_findings),
        "authority_boundary": {
            "semantic_guard_role": "audit_and_reaudit_only",
            "execution_owner": "external_caller_or_control_plane",
            "sequencing_owner": "external_caller_or_control_plane",
            "final_acceptance_owner": "human",
            "executes_repair": False,
            "accepts_result": False,
        },
    }
    cycle["cycle_id"] = "repair-cycle." + hashlib.sha256(
        _canonical(_cycle_identity_material(cycle))
    ).hexdigest()
    cycle["cycle_digest"] = _digest(cycle)
    validate_repair_cycle(cycle, responsibility_materials, responsibility_policy)
    return cycle


def _attempt_id(attempt: Mapping[str, Any]) -> str:
    return _derived_id("repair-attempt", attempt, "attempt_id", "attempt_digest")


def record_repair_attempt(
    cycle: Mapping[str, Any],
    *,
    executed_by: Mapping[str, Any],
    authority_evidence_ref: Mapping[str, Any],
    started_at: str,
    completed_at: str,
    before_subject_digest: Mapping[str, Any],
    after_subject_digest: Mapping[str, Any],
    change_evidence_refs: Sequence[Mapping[str, Any]],
    stop_condition_result: str,
    responsibility_materials: Sequence[Mapping[str, Any]],
    responsibility_policy: Mapping[str, Any],
    self_report_ref: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Bind an externally executed attempt without treating it as success."""

    validate_repair_cycle(cycle, responsibility_materials, responsibility_policy)
    if cycle["repair_attempt"] is not None:
        raise RepairContractError("repair attempt already recorded")
    attempt: dict[str, Any] = {
        "executed_by": copy.deepcopy(dict(executed_by)),
        "authority_evidence_ref": copy.deepcopy(dict(authority_evidence_ref)),
        "started_at": started_at,
        "completed_at": completed_at,
        "before_subject_digest": copy.deepcopy(dict(before_subject_digest)),
        "after_subject_digest": copy.deepcopy(dict(after_subject_digest)),
        "change_evidence_refs": [
            copy.deepcopy(dict(item)) for item in change_evidence_refs
        ],
        "self_report_ref": (
            copy.deepcopy(dict(self_report_ref))
            if self_report_ref is not None
            else None
        ),
        "stop_condition_result": stop_condition_result,
    }
    attempt["attempt_id"] = _attempt_id(attempt)
    attempt["attempt_digest"] = _digest(attempt)
    result = copy.deepcopy(dict(cycle))
    result["repair_attempt"] = attempt
    result["cycle_digest"] = _digest(_without(result, "cycle_digest"))
    validate_repair_cycle(result, responsibility_materials, responsibility_policy)
    return result


def _guard_ids(findings: Iterable[Mapping[str, Any]]) -> set[str]:
    return {
        str(guard)
        for finding in findings
        for guard in finding["repair_target"]["regression_guards"]
    }


def _after_subject_ref(cycle: Mapping[str, Any]) -> dict[str, Any]:
    attempt = cycle["repair_attempt"]
    if attempt is None:
        raise RepairContractError("after-subject binding requires a recorded attempt")
    return {
        "entity_id": cycle["subject_ref"]["entity_id"],
        "entity_version": cycle["subject_ref"]["entity_version"],
        "entity_digest": copy.deepcopy(attempt["after_subject_digest"]),
    }


def _derive_finding_effect(before_outcome: str, after_outcome: str) -> str:
    """Apply the conservative, versioned repair transition rule."""

    if after_outcome == "supported":
        return "resolved"
    if after_outcome == "unknown":
        return "unknown"
    if after_outcome == before_outcome:
        return "unchanged"
    if after_outcome in {"refuted", "invalid"}:
        return "worsened"
    return "unknown"


def _derive_overall(
    *,
    finding_results: Sequence[Mapping[str, Any]],
    regression_results: Sequence[Mapping[str, Any]],
    escalation_result: str,
    stop_condition_result: str,
    subject_changed: bool,
) -> str:
    effects = [str(item["effect"]) for item in finding_results]
    guards = [str(item["outcome"]) for item in regression_results]
    resolved = effects.count("resolved")
    negative = (
        "worsened" in effects
        or "failed" in guards
        or escalation_result == "missed"
        or stop_condition_result == "violated"
    )
    unknown = (
        "unknown" in effects
        or "unknown" in guards
        or escalation_result == "unknown"
        or stop_condition_result == "unknown"
    )
    if negative:
        return "mixed" if resolved else "regressed"
    if unknown:
        return "mixed" if resolved else "indeterminate"
    if resolved == len(effects) and all(item == "passed" for item in guards):
        return "improved" if subject_changed else "indeterminate"
    if resolved:
        return "mixed"
    if all(item == "unchanged" for item in effects) and all(
        item == "passed" for item in guards
    ):
        return "no_change"
    return "indeterminate"


def _prepare_effect_assessment(
    cycle: Mapping[str, Any],
    *,
    after_audit_ref: Mapping[str, Any],
    finding_results: Sequence[Mapping[str, Any]],
    regression_results: Sequence[Mapping[str, Any]],
    escalation_result: str,
    limitations: Sequence[str],
) -> dict[str, Any]:
    attempt = cycle["repair_attempt"]
    if attempt is None:
        raise RepairContractError("changed output alone cannot be assessed without an attempt")
    if _ref_key(after_audit_ref) == _ref_key(cycle["before_audit_ref"]):
        raise RepairContractError("after audit must be a distinct observed audit record")

    normalized_findings = sorted(
        (copy.deepcopy(dict(item)) for item in finding_results),
        key=lambda item: item["finding_id"],
    )
    normalized_guards = sorted(
        (copy.deepcopy(dict(item)) for item in regression_results),
        key=lambda item: item["guard_id"],
    )
    for result in normalized_findings:
        expected_effect = _derive_finding_effect(
            str(result["before_outcome"]), str(result["after_outcome"])
        )
        if result["effect"] != expected_effect:
            raise RepairContractError(
                f"finding {result['finding_id']} effect contradicts "
                f"{_REPAIR_EFFECT_TRANSITION_RULE}: declared {result['effect']}, "
                f"derived {expected_effect}"
            )
    unresolved = sorted(
        str(item["finding_id"])
        for item in normalized_findings
        if item["effect"] != "resolved"
    )
    subject_changed = _digest_key(attempt["before_subject_digest"]) != _digest_key(
        attempt["after_subject_digest"]
    )
    overall = _derive_overall(
        finding_results=normalized_findings,
        regression_results=normalized_guards,
        escalation_result=escalation_result,
        stop_condition_result=str(attempt["stop_condition_result"]),
        subject_changed=subject_changed,
    )
    return _seal_effect_basis({
        "status": "evaluated",
        "claim_scope": "declared_local_reaudit_only",
        "field_repair_effect": "not_evaluated",
        "finding_results": normalized_findings,
        "regression_results": normalized_guards,
        "escalation_result": escalation_result,
        "overall_effect": overall,
        "unresolved_remainder": unresolved,
        "independent_review_refs": [],
        "limitations": list(
            dict.fromkeys(
                [
                    *limitations,
                    _LOCAL_EFFECT_LIMITATION,
                    _AUTHORITY_LIMITATION,
                    _REVIEW_LIMITATION,
                ]
            )
        ),
    })


def build_repair_effect_review_basis(
    cycle: Mapping[str, Any],
    *,
    after_audit_ref: Mapping[str, Any],
    finding_results: Sequence[Mapping[str, Any]],
    regression_results: Sequence[Mapping[str, Any]],
    escalation_result: str,
    limitations: Sequence[str],
    responsibility_materials: Sequence[Mapping[str, Any]],
    responsibility_policy: Mapping[str, Any],
) -> dict[str, Any]:
    """Expose the exact non-cyclic target an external reviewer must sign off."""

    validate_repair_cycle(cycle, responsibility_materials, responsibility_policy)
    effect = _prepare_effect_assessment(
        cycle,
        after_audit_ref=after_audit_ref,
        finding_results=finding_results,
        regression_results=regression_results,
        escalation_result=escalation_result,
        limitations=limitations,
    )
    return {
        "target_cycle_ref": _cycle_identity_ref(cycle),
        "target_after_audit_ref": copy.deepcopy(dict(after_audit_ref)),
        "target_effect_basis_digest": copy.deepcopy(
            effect["effect_basis_digest"]
        ),
    }


def assess_repair_effect(
    cycle: Mapping[str, Any],
    *,
    after_audit_ref: Mapping[str, Any],
    finding_results: Sequence[Mapping[str, Any]],
    regression_results: Sequence[Mapping[str, Any]],
    escalation_result: str,
    independent_review_refs: Sequence[Mapping[str, Any]],
    limitations: Sequence[str],
    responsibility_materials: Sequence[Mapping[str, Any]],
    responsibility_policy: Mapping[str, Any],
) -> dict[str, Any]:
    """Compare an explicit after-audit with the before state."""

    validate_repair_cycle(cycle, responsibility_materials, responsibility_policy)
    effect = _prepare_effect_assessment(
        cycle,
        after_audit_ref=after_audit_ref,
        finding_results=finding_results,
        regression_results=regression_results,
        escalation_result=escalation_result,
        limitations=limitations,
    )
    reviews = [copy.deepcopy(dict(item)) for item in independent_review_refs]
    if any("review_id" not in item for item in reviews):
        raise RepairContractError(
            "independent_review_refs require typed independent review records"
        )
    reviews.sort(key=lambda item: item["review_id"])
    _unique(reviews, "review_id", "independent_review_refs")
    for review in reviews:
        _validate_independent_review_record(
            review,
            cycle=cycle,
            after_audit_ref=after_audit_ref,
            effect_basis_digest=effect["effect_basis_digest"],
        )
    effect["independent_review_refs"] = reviews
    result = copy.deepcopy(dict(cycle))
    result["after_audit_ref"] = copy.deepcopy(dict(after_audit_ref))
    result["effect_assessment"] = effect
    result["cycle_digest"] = _digest(_without(result, "cycle_digest"))
    validate_repair_cycle(result, responsibility_materials, responsibility_policy)
    return result


def validate_repair_cycle(
    cycle: Mapping[str, Any],
    responsibility_materials: Sequence[Mapping[str, Any]],
    responsibility_policy: Mapping[str, Any],
) -> None:
    _schema_validate(cycle, "repair-cycle.schema.json", "repair cycle")
    validate_responsibility_policy(responsibility_policy)
    materials = list(responsibility_materials)
    for material in materials:
        validate_responsibility_material(material, responsibility_policy)
    _unique(materials, "material_id", "responsibility_materials")
    material_by_ref = {_ref_key(_material_ref(item)): item for item in materials}

    findings = list(cycle["findings"])
    _unique(findings, "finding_id", "findings")
    expected_cycle_id = "repair-cycle." + hashlib.sha256(
        _canonical(_cycle_identity_material(cycle))
    ).hexdigest()
    if cycle["cycle_id"] != expected_cycle_id:
        raise RepairContractError("repair cycle id mismatch")
    expected_digest = _digest(_without(cycle, "cycle_digest"))
    if cycle["cycle_digest"] != expected_digest:
        raise RepairContractError("repair cycle digest mismatch")

    for finding in findings:
        ref = _ref_key(finding["responsibility_material_ref"])
        material = material_by_ref.get(ref)
        if material is None:
            raise RepairContractError(
                f"finding {finding['finding_id']} has no exact responsibility material"
            )
        if material["material_kind"] != "agent_repair":
            raise RepairContractError(
                f"finding {finding['finding_id']} does not reference agent repair material"
            )
        targets = {
            str(item["target_id"]): item for item in material["repair_targets"]
        }
        target_id = str(finding["repair_target"]["target_id"])
        if target_id not in targets or targets[target_id] != finding["repair_target"]:
            raise RepairContractError(
                f"finding {finding['finding_id']} repair target differs from its material"
            )
        if not _REQUIRED_SHORTCUT_BARRIERS <= set(
            finding["repair_target"]["prohibited_shortcuts"]
        ):
            raise RepairContractError(
                f"finding {finding['finding_id']} lacks anti-gaming barriers"
            )

    attempt = cycle["repair_attempt"]
    if attempt is not None:
        expected_attempt_id = _attempt_id(attempt)
        if attempt["attempt_id"] != expected_attempt_id:
            raise RepairContractError("repair attempt id mismatch")
        expected_attempt_digest = _digest(_without(attempt, "attempt_digest"))
        if attempt["attempt_digest"] != expected_attempt_digest:
            raise RepairContractError("repair attempt digest mismatch")
        if _parse_time(attempt["completed_at"], "repair_attempt.completed_at") < _parse_time(
            attempt["started_at"], "repair_attempt.started_at"
        ):
            raise RepairContractError("repair attempt completed before it started")
        if _digest_key(attempt["before_subject_digest"]) != _digest_key(
            cycle["subject_ref"]["entity_digest"]
        ):
            raise RepairContractError("attempt before digest differs from cycle subject")

    effect = cycle["effect_assessment"]
    expected_effect_basis = _digest(_effect_basis_material(effect))
    if effect["effect_basis_digest"] != expected_effect_basis:
        raise RepairContractError("repair effect basis digest mismatch")
    if _REVIEW_LIMITATION not in effect["limitations"]:
        raise RepairContractError(
            "effect assessment omits the independent-review authenticity limitation"
        )
    finding_ids = {str(item["finding_id"]) for item in findings}
    if effect["status"] == "not_assessed":
        if set(effect["unresolved_remainder"]) != finding_ids:
            raise RepairContractError(
                "unassessed repair cycle must retain every finding as unresolved"
            )
        return

    if attempt is None or cycle["after_audit_ref"] is None:
        raise RepairContractError("evaluated effect requires attempt and after audit")
    if _ref_key(cycle["after_audit_ref"]) == _ref_key(cycle["before_audit_ref"]):
        raise RepairContractError("before audit cannot be replayed as after audit")
    finding_results = list(effect["finding_results"])
    regression_results = list(effect["regression_results"])
    _unique(finding_results, "finding_id", "finding_results")
    _unique(regression_results, "guard_id", "regression_results")
    if {str(item["finding_id"]) for item in finding_results} != finding_ids:
        raise RepairContractError("effect assessment must cover every finding exactly once")
    expected_guards = _guard_ids(findings)
    actual_guards = {str(item["guard_id"]) for item in regression_results}
    if actual_guards != expected_guards:
        raise RepairContractError("effect assessment must cover every regression guard")
    before_by_id = {
        str(item["finding_id"]): str(item["before_outcome"]) for item in findings
    }
    finding_by_id = {str(item["finding_id"]): item for item in findings}
    self_report_key = (
        _ref_key(attempt["self_report_ref"])
        if attempt["self_report_ref"] is not None
        else None
    )
    for result in finding_results:
        finding_id = str(result["finding_id"])
        if result["before_outcome"] != before_by_id[finding_id]:
            raise RepairContractError(
                f"before outcome substitution for finding {finding_id}"
            )
        derived_effect = _derive_finding_effect(
            str(result["before_outcome"]), str(result["after_outcome"])
        )
        if result["effect"] != derived_effect:
            raise RepairContractError(
                f"finding {finding_id} effect contradicts "
                f"{_REPAIR_EFFECT_TRANSITION_RULE}: declared {result['effect']}, "
                f"derived {derived_effect}"
            )
        audit_result = result["after_audit_result_ref"]
        expected_after_subject = _after_subject_ref(cycle)
        if (
            audit_result["audit_ref"] != cycle["after_audit_ref"]
            or audit_result["subject_ref"] != expected_after_subject
            or audit_result["obligation_id"]
            != finding_by_id[finding_id]["obligation_id"]
            or audit_result["outcome"] != result["after_outcome"]
        ):
            raise RepairContractError(
                f"after-audit result binding mismatch for finding {finding_id}"
            )
        evidence = list(result["reaudit_evidence_refs"])
        if result["effect"] != "unknown" and not evidence:
            raise RepairContractError(
                f"effect {result['effect']} lacks re-audit evidence for {finding_id}"
            )
        if evidence and self_report_key is not None and all(
            _ref_key(item) == self_report_key for item in evidence
        ):
            raise RepairContractError(
                f"self-report alone cannot establish repair effect for {finding_id}"
            )
        typed_result_key = (
            str(audit_result["result_id"]),
            str(audit_result["result_digest"]["value"]),
        )
        if typed_result_key not in {_ref_key(item) for item in evidence}:
            raise RepairContractError(
                f"typed after-audit result is absent from re-audit evidence for {finding_id}"
            )
    for result in regression_results:
        if result["outcome"] != "unknown" and not result["evidence_refs"]:
            raise RepairContractError(
                f"regression result lacks evidence for {result['guard_id']}"
            )
        execution_result = result["execution_result_ref"]
        if (
            execution_result["audit_ref"] != cycle["after_audit_ref"]
            or execution_result["subject_ref"] != _after_subject_ref(cycle)
            or execution_result["guard_id"] != result["guard_id"]
            or execution_result["outcome"] != result["outcome"]
        ):
            raise RepairContractError(
                f"regression execution result binding mismatch for {result['guard_id']}"
            )
        typed_result_key = (
            str(execution_result["result_id"]),
            str(execution_result["result_digest"]["value"]),
        )
        if typed_result_key not in {
            _ref_key(item) for item in result["evidence_refs"]
        }:
            raise RepairContractError(
                f"typed regression result is absent from evidence for {result['guard_id']}"
            )

    if (
        responsibility_policy["repair_effect_policy"][
            "independent_review_required"
        ]
        and not effect["independent_review_refs"]
    ):
        raise RepairContractError(
            "adopted responsibility policy requires independent repair review"
        )
    reviews = list(effect["independent_review_refs"])
    _unique(reviews, "review_id", "independent_review_refs")
    for review in reviews:
        _validate_independent_review_record(
            review,
            cycle=cycle,
            after_audit_ref=cycle["after_audit_ref"],
            effect_basis_digest=effect["effect_basis_digest"],
        )

    expected_unresolved = {
        str(item["finding_id"])
        for item in finding_results
        if item["effect"] != "resolved"
    }
    if set(effect["unresolved_remainder"]) != expected_unresolved:
        raise RepairContractError("unresolved remainder differs from finding effects")
    derived = _derive_overall(
        finding_results=finding_results,
        regression_results=regression_results,
        escalation_result=str(effect["escalation_result"]),
        stop_condition_result=str(attempt["stop_condition_result"]),
        subject_changed=_digest_key(attempt["before_subject_digest"])
        != _digest_key(attempt["after_subject_digest"]),
    )
    if effect["overall_effect"] != derived:
        raise RepairContractError(
            f"overall repair effect mismatch: declared {effect['overall_effect']}, derived {derived}"
        )
    if _LOCAL_EFFECT_LIMITATION not in effect["limitations"]:
        raise RepairContractError("effect assessment omits its local-only limitation")
    if _AUTHORITY_LIMITATION not in effect["limitations"]:
        raise RepairContractError("effect assessment omits the authority boundary")


__all__ = [
    "RepairContractError",
    "assess_repair_effect",
    "build_independent_repair_review",
    "build_repair_cycle",
    "build_repair_effect_review_basis",
    "build_responsibility_material",
    "build_responsibility_policy",
    "record_repair_attempt",
    "validate_repair_cycle",
    "validate_responsibility_material",
    "validate_responsibility_policy",
]
