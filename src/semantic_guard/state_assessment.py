"""Closed subject binding, evidence validity, and independent state axes.

The builders in this module are pure with respect to their inputs: callers
provide every identity, digest, policy, and timestamp.  Validation checks
record-internal closure and deterministic replay.  It does not authenticate a
clock, discover the correct real-world denominator, execute requalification,
or make a human acceptance decision.
"""

from __future__ import annotations

import copy
from datetime import datetime, timedelta
from functools import lru_cache
import hashlib
import json
import re
from typing import Any, Iterable, Mapping, Sequence

from jsonschema import Draft202012Validator, FormatChecker

from .schema_access import schema_directory


SUBJECT_MANIFEST_VERSION = "subject-manifest/v0"
VALIDITY_POLICY_VERSION = "evidence-validity-policy/v2"
EVIDENCE_OBSERVATION_VERSION = "state-evidence-observation/v1"
STATE_ASSESSMENT_VERSION = "state-assessment/v2"

_SCHEMA_DIR = schema_directory()
_EXPLICIT_AXES = ("implementation", "verification", "validation", "assurance")
_DEFAULT_AXIS_VALUES = {
    "implementation": "not_assessed",
    "verification": "not_assessed",
    "validation": "not_assessed",
    "assurance": "not_assessed",
}
_AXIS_VALUES = {
    "implementation": frozenset({"missing", "partial", "implemented"}),
    "verification": frozenset({"not_run", "passed", "failed", "invalid"}),
    "validation": frozenset(
        {
            "not_evaluated",
            "supported_in_context",
            "inconclusive",
            "refuted_in_context",
        }
    ),
    "assurance": frozenset({"unbound", "undetermined", "satisfied", "refuted"}),
}
_FRESHNESS_RANK = {"current": 0, "stale": 1, "unbound": 2}
_TIME_LIMITATION = (
    "Timestamp comparisons use caller-supplied clock claims; this assessment "
    "does not establish trusted-time authenticity."
)
_DENOMINATOR_LIMITATION = (
    "Closed-world subject binding covers the declared manifest only; it does "
    "not prove that the selected real-world denominator is complete."
)
_CONTROL_LIMITATION = (
    "Requalification output names required evidence only; it does not set "
    "priority, delegate execution, or authorize external effects."
)


class StateAssessmentError(ValueError):
    """Raised when a state-assessment contract fails closed."""


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


def _without_digest(value: Mapping[str, Any], field: str) -> dict[str, Any]:
    result = copy.deepcopy(dict(value))
    result.pop(field, None)
    return result


def _digest_value(value: Mapping[str, Any]) -> str:
    return str(value["value"])


def _format_path(parts: Iterable[Any]) -> str:
    result = "/".join(str(part) for part in parts)
    return result or "/"


@lru_cache(maxsize=None)
def _schema(name: str) -> dict[str, Any]:
    path = _SCHEMA_DIR / name
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def _validator(name: str) -> Draft202012Validator:
    schema = _schema(name)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


@lru_cache(maxsize=1)
def _evidence_validator() -> Draft202012Validator:
    state_schema = _schema("state-assessment.schema.json")
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$defs": state_schema["$defs"],
        "$ref": "#/$defs/evidence_observation",
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
        raise StateAssessmentError(
            f"{contract} schema violation at {_format_path(issue.absolute_path)}: "
            f"{issue.message}"
        )


def _parse_timestamp(value: str, location: str) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith(("Z", "z")) else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise StateAssessmentError(f"invalid timestamp at {location}: {value}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise StateAssessmentError(f"timestamp lacks timezone at {location}: {value}")
    return parsed


def _validate_repository_path(value: str, location: str) -> None:
    if (
        not value
        or value in {".", ".."}
        or value.startswith("/")
        or value.startswith("./")
        or "\\" in value
        or "\x00" in value
        or re.match(r"^[A-Za-z]:", value)
        or any(part in {"", ".", ".."} for part in value.split("/"))
    ):
        raise StateAssessmentError(
            f"non-canonical or traversing repository path at {location}: {value!r}"
        )


def _require_unique(
    values: Sequence[Mapping[str, Any]],
    field: str,
    location: str,
) -> None:
    observed = [str(value[field]) for value in values]
    duplicates = sorted({item for item in observed if observed.count(item) > 1})
    if duplicates:
        raise StateAssessmentError(
            f"duplicate {field} at {location}: {duplicates!r}"
        )


def _sort_bindings(values: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        (copy.deepcopy(dict(value)) for value in values),
        key=lambda value: (value["entity_id"], value["entity_version"]),
    )


def _binding_key(value: Mapping[str, Any]) -> tuple[str, str, str]:
    return (
        str(value["entity_id"]),
        str(value["entity_version"]),
        _digest_value(value["content_digest"]),
    )


def _binding_set(values: Iterable[Mapping[str, Any]]) -> set[tuple[str, str, str]]:
    return {_binding_key(value) for value in values}


def _manifest_ref(manifest: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "manifest_id": manifest["manifest_id"],
        "manifest_version": manifest["manifest_version"],
        "manifest_digest": copy.deepcopy(manifest["manifest_digest"]),
    }


def _policy_ref(policy: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "policy_id": policy["policy_id"],
        "policy_version": policy["policy_version"],
        "policy_digest": copy.deepcopy(policy["policy_digest"]),
    }


def _evidence_ref(evidence: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "evidence_id": evidence["evidence_id"],
        "content_digest": copy.deepcopy(evidence["content_digest"]),
    }


def _validity_policy_basis_material(policy: Mapping[str, Any]) -> dict[str, Any]:
    material = copy.deepcopy(dict(policy))
    for field in (
        "adoption_state",
        "human_decision_ref",
        "policy_basis_digest",
        "policy_digest",
    ):
        material.pop(field, None)
    return material


def _acceptance_basis_material(assessment: Mapping[str, Any]) -> dict[str, Any]:
    """Exclude the human response and final seals from its technical target."""

    material = copy.deepcopy(dict(assessment))
    for field in (
        "human_acceptance_record",
        "acceptance_basis_digest",
        "assessment_digest",
    ):
        material.pop(field, None)
    material["axes"].pop("human_acceptance", None)
    material["axis_derivations"].pop("human_acceptance", None)
    return material


def build_subject_manifest(
    *,
    manifest_id: str,
    manifest_version: str,
    root: str,
    inclusion_rule: str,
    subject_entries: Sequence[Mapping[str, Any]],
    environment_bindings: Sequence[Mapping[str, Any]],
    profile_bindings: Sequence[Mapping[str, Any]],
    exclusions: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Build a deterministic closed-world subject manifest."""

    sorted_entries = sorted(
        (copy.deepcopy(dict(item)) for item in subject_entries),
        key=lambda item: (item["path"], item["entry_id"]),
    )
    sorted_exclusions = sorted(
        (copy.deepcopy(dict(item)) for item in exclusions),
        key=lambda item: item["path"],
    )
    manifest: dict[str, Any] = {
        "schema_version": SUBJECT_MANIFEST_VERSION,
        "manifest_id": manifest_id,
        "manifest_version": manifest_version,
        "denominator": {
            "status": "closed",
            "root": root,
            "inclusion_rule": inclusion_rule,
            "exclusions": sorted_exclusions,
            "subject_entry_count": len(sorted_entries),
        },
        "subject_entries": sorted_entries,
        "environment_bindings": _sort_bindings(environment_bindings),
        "profile_bindings": _sort_bindings(profile_bindings),
    }
    manifest["manifest_digest"] = _digest(manifest)
    validate_subject_manifest(manifest)
    return manifest


def validate_subject_manifest(manifest: Mapping[str, Any]) -> None:
    _validate_schema(
        manifest,
        _validator("subject-manifest.schema.json"),
        "subject manifest",
    )
    entries = list(manifest["subject_entries"])
    if not any(entry["role"] == "primary_subject" for entry in entries):
        raise StateAssessmentError(
            "self-selected evidence-only denominator has no primary subject"
        )
    if int(manifest["denominator"]["subject_entry_count"]) != len(entries):
        raise StateAssessmentError("subject_entry_count does not match subject_entries")
    _validate_repository_path(str(manifest["denominator"]["root"]), "denominator.root")
    for index, entry in enumerate(entries):
        _validate_repository_path(str(entry["path"]), f"subject_entries[{index}].path")
    exclusions = list(manifest["denominator"]["exclusions"])
    for index, exclusion in enumerate(exclusions):
        _validate_repository_path(
            str(exclusion["path"]), f"denominator.exclusions[{index}].path"
        )
    _require_unique(entries, "entry_id", "subject_entries")
    _require_unique(entries, "path", "subject_entries")
    _require_unique(exclusions, "path", "denominator.exclusions")
    included_paths = {str(entry["path"]) for entry in entries}
    excluded_paths = {str(item["path"]) for item in exclusions}
    overlap = sorted(included_paths & excluded_paths)
    if overlap:
        raise StateAssessmentError(
            f"paths cannot be both included and excluded: {overlap!r}"
        )
    for field in ("environment_bindings", "profile_bindings"):
        bindings = list(manifest[field])
        _require_unique(bindings, "entity_id", field)
    expected = _digest(_without_digest(manifest, "manifest_digest"))
    if manifest["manifest_digest"] != expected:
        raise StateAssessmentError(
            "manifest digest mismatch: the subject denominator or identity bindings changed"
        )


def build_validity_policy(
    *,
    policy_id: str,
    policy_version: str,
    adoption_state: str,
    evidence_kind_rules: Sequence[Mapping[str, Any]],
    change_invalidation: Mapping[str, Mapping[str, Any]],
    human_decision_ref: Mapping[str, Any] | None = None,
    untrusted_time_result: str = "stale",
) -> dict[str, Any]:
    """Build a versioned evidence-validity policy without adopting it."""

    policy: dict[str, Any] = {
        "schema_version": VALIDITY_POLICY_VERSION,
        "policy_id": policy_id,
        "policy_version": policy_version,
        "adoption_state": adoption_state,
        "human_decision_ref": (
            copy.deepcopy(dict(human_decision_ref))
            if human_decision_ref is not None
            else None
        ),
        "clock_requirement": {
            "trusted_time_required": True,
            "untrusted_time_result": untrusted_time_result,
        },
        "evidence_kind_rules": sorted(
            (copy.deepcopy(dict(rule)) for rule in evidence_kind_rules),
            key=lambda rule: rule["evidence_kind"],
        ),
        "change_invalidation": copy.deepcopy(dict(change_invalidation)),
    }
    policy["policy_basis_digest"] = _digest(
        _validity_policy_basis_material(policy)
    )
    policy["policy_digest"] = _digest(policy)
    validate_validity_policy(policy)
    return policy


def validate_validity_policy(policy: Mapping[str, Any]) -> None:
    _validate_schema(
        policy,
        _validator("evidence-validity-policy.schema.json"),
        "evidence validity policy",
    )
    _require_unique(
        list(policy["evidence_kind_rules"]),
        "evidence_kind",
        "evidence_kind_rules",
    )
    for rule in policy["evidence_kind_rules"]:
        ceilings = list(rule["claim_ceiling"])
        _require_unique(
            ceilings,
            "axis",
            f"evidence_kind_rules.{rule['evidence_kind']}.claim_ceiling",
        )
        for ceiling in ceilings:
            axis = str(ceiling["axis"])
            values = set(str(item) for item in ceiling["allowed_values"])
            if not values <= _AXIS_VALUES[axis]:
                raise StateAssessmentError(
                    f"claim ceiling for {rule['evidence_kind']} has invalid "
                    f"{axis} values: {sorted(values - _AXIS_VALUES[axis])!r}"
                )
    expected_basis = _digest(_validity_policy_basis_material(policy))
    if policy["policy_basis_digest"] != expected_basis:
        raise StateAssessmentError("validity policy basis digest mismatch")
    if policy["adoption_state"] == "adopted":
        decision = policy["human_decision_ref"]
        if decision["decided_by"] != decision["decision_maker_identity"][
            "entity_id"
        ]:
            raise StateAssessmentError(
                "validity policy decision identity does not match decided_by"
            )
        expected_target = {
            "decision_kind": "adopt_evidence_validity_policy",
            "target_id": policy["policy_id"],
            "target_version": policy["policy_version"],
            "target_basis_digest": policy["policy_basis_digest"],
        }
        for field, expected_value in expected_target.items():
            if decision[field] != expected_value:
                raise StateAssessmentError(
                    f"human adoption decision {field} does not target this validity policy basis"
                )
    expected = _digest(_without_digest(policy, "policy_digest"))
    if policy["policy_digest"] != expected:
        raise StateAssessmentError("validity policy digest mismatch")


def build_evidence_observation(
    *,
    evidence_id: str,
    evidence_kind: str,
    content_digest: Mapping[str, Any],
    subject_manifest: Mapping[str, Any],
    observed_at: str,
    expires_at: str,
    time_trust: str,
    environment_identity: Mapping[str, Any],
    tool_identity: Mapping[str, Any],
    profile_identity: Mapping[str, Any],
    rule_identities: Sequence[Mapping[str, Any]],
    covered_claim_dimensions: Sequence[str],
    claim_effects: Sequence[Mapping[str, Any]],
    trust_class: str,
    limitations: Sequence[str] = (),
) -> dict[str, Any]:
    validate_subject_manifest(subject_manifest)
    observation: dict[str, Any] = {
        "schema_version": EVIDENCE_OBSERVATION_VERSION,
        "evidence_id": evidence_id,
        "evidence_kind": evidence_kind,
        "content_digest": copy.deepcopy(dict(content_digest)),
        "subject_manifest_ref": _manifest_ref(subject_manifest),
        "observed_at": observed_at,
        "expires_at": expires_at,
        "time_trust": time_trust,
        "environment_identity": copy.deepcopy(dict(environment_identity)),
        "tool_identity": copy.deepcopy(dict(tool_identity)),
        "profile_identity": copy.deepcopy(dict(profile_identity)),
        "rule_identities": _sort_bindings(rule_identities),
        "covered_claim_dimensions": sorted(set(covered_claim_dimensions)),
        "claim_effects": sorted(
            (copy.deepcopy(dict(item)) for item in claim_effects),
            key=lambda item: (item["axis"], item["value"], item["rule_id"]),
        ),
        "trust_class": trust_class,
        "limitations": sorted(set(limitations)),
    }
    observation["observation_digest"] = _digest(observation)
    validate_evidence_observation(observation)
    return observation


def validate_evidence_observation(observation: Mapping[str, Any]) -> None:
    _validate_schema(observation, _evidence_validator(), "evidence observation")
    observed_at = _parse_timestamp(str(observation["observed_at"]), "observed_at")
    expires_at = _parse_timestamp(str(observation["expires_at"]), "expires_at")
    if expires_at <= observed_at:
        raise StateAssessmentError("expires_at must be later than observed_at")
    _require_unique(
        list(observation["rule_identities"]),
        "entity_id",
        "rule_identities",
    )
    effects = list(observation["claim_effects"])
    effect_axes = [str(item["axis"]) for item in effects]
    if len(effect_axes) != len(set(effect_axes)):
        raise StateAssessmentError("an evidence observation cannot claim conflicting axis effects")
    if set(effect_axes) != set(observation["covered_claim_dimensions"]):
        raise StateAssessmentError(
            "covered_claim_dimensions must equal the axes in claim_effects"
        )
    rule_ids = {str(item["entity_id"]) for item in observation["rule_identities"]}
    for effect in effects:
        if effect["rule_id"] not in rule_ids:
            raise StateAssessmentError(
                f"claim effect for {effect['axis']} references an unbound rule"
            )
    expected = _digest(_without_digest(observation, "observation_digest"))
    if observation["observation_digest"] != expected:
        raise StateAssessmentError("evidence observation digest mismatch")


def _policy_rules(policy: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {
        str(rule["evidence_kind"]): rule for rule in policy["evidence_kind_rules"]
    }


def _merge_freshness(current: str, candidate: str) -> str:
    return candidate if _FRESHNESS_RANK[candidate] > _FRESHNESS_RANK[current] else current


def _evaluate_evidence(
    evidence: Mapping[str, Any],
    *,
    manifest: Mapping[str, Any],
    policy: Mapping[str, Any],
    assessed_at: str,
    assessment_time_trust: str,
    current_context: Mapping[str, Any],
) -> dict[str, Any]:
    kind = str(evidence["evidence_kind"])
    rule = _policy_rules(policy).get(kind)
    evaluated_at = _parse_timestamp(assessed_at, "assessed_at")
    freshness = "current"
    subject_binding = "bound"
    reasons: list[str] = []
    changes: list[str] = []
    required_kinds: set[str] = set()

    def invalidate(reason: str, result: str, evidence_kinds: Iterable[str]) -> None:
        nonlocal freshness
        if reason not in reasons:
            reasons.append(reason)
        freshness = _merge_freshness(freshness, result)
        required_kinds.update(str(item) for item in evidence_kinds)

    if policy["adoption_state"] != "adopted":
        fallback = (
            rule["requalification_evidence_kinds"]
            if rule is not None
            else ["independent_review"]
        )
        invalidate("policy_not_adopted", "unbound", fallback)
    else:
        adopted_at = _parse_timestamp(
            str(policy["human_decision_ref"]["decided_at"]),
            "validity_policy.human_decision_ref.decided_at",
        )
        if evaluated_at < adopted_at:
            fallback = (
                rule["requalification_evidence_kinds"]
                if rule is not None
                else ["independent_review"]
            )
            invalidate("policy_not_adopted_at_assessment", "unbound", fallback)

    expected_manifest_ref = _manifest_ref(manifest)
    if evidence["subject_manifest_ref"] != expected_manifest_ref:
        subject_binding = "unbound"
        change_rule = policy["change_invalidation"]["subject_digest_change"]
        changes.append("subject_digest_change")
        invalidate(
            "subject_manifest_mismatch",
            "unbound",
            change_rule["requalification_evidence_kinds"],
        )

    comparisons = (
        (
            "environment_digest_change",
            _binding_key(evidence["environment_identity"])
            in _binding_set(current_context["environment_bindings"])
            and _binding_set(manifest["environment_bindings"])
            == _binding_set(current_context["environment_bindings"]),
        ),
        (
            "tool_digest_change",
            _binding_key(evidence["tool_identity"])
            == _binding_key(current_context["tool_identity"]),
        ),
        (
            "profile_digest_change",
            _binding_key(evidence["profile_identity"])
            in _binding_set(current_context["profile_bindings"])
            and _binding_set(manifest["profile_bindings"])
            == _binding_set(current_context["profile_bindings"]),
        ),
        (
            "rule_digest_change",
            _binding_set(evidence["rule_identities"])
            == _binding_set(current_context["rule_bindings"]),
        ),
    )
    for change_name, matches in comparisons:
        if matches:
            continue
        change_rule = policy["change_invalidation"][change_name]
        changes.append(change_name)
        invalidate(
            change_name,
            str(change_rule["freshness_after_change"]),
            change_rule["requalification_evidence_kinds"],
        )

    if rule is None:
        invalidate("evidence_kind_not_governed", "unbound", ["independent_review"])
    else:
        if evidence["trust_class"] not in rule["accepted_trust_classes"]:
            invalidate(
                "trust_class_not_accepted",
                "unbound",
                rule["requalification_evidence_kinds"],
            )
        observed_at = _parse_timestamp(
            str(evidence["observed_at"]), f"{evidence['evidence_id']}.observed_at"
        )
        expires_at = _parse_timestamp(
            str(evidence["expires_at"]), f"{evidence['evidence_id']}.expires_at"
        )
        if evaluated_at < observed_at:
            invalidate(
                "assessment_precedes_observation",
                "stale",
                rule["requalification_evidence_kinds"],
            )
        policy_expiry = observed_at + timedelta(seconds=int(rule["max_age_seconds"]))
        effective_expiry = min(expires_at, policy_expiry)
        if evaluated_at >= effective_expiry:
            reason = (
                "evidence_expired"
                if expires_at <= policy_expiry
                else "evidence_age_exceeds_policy"
            )
            invalidate(reason, "stale", rule["requalification_evidence_kinds"])

    if assessment_time_trust != "trusted" or evidence["time_trust"] != "trusted":
        fallback = (
            rule["requalification_evidence_kinds"]
            if rule is not None
            else ["independent_review"]
        )
        invalidate(
            "untrusted_time",
            str(policy["clock_requirement"]["untrusted_time_result"]),
            fallback,
        )

    return {
        "evidence_ref": _evidence_ref(evidence),
        "subject_binding": subject_binding,
        "freshness": freshness,
        "reasons": sorted(reasons),
        "invalidating_changes": sorted(changes),
        "required_requalification_evidence_kinds": sorted(required_kinds),
    }


def _overall_freshness(
    evaluations: Sequence[Mapping[str, Any]],
    policy: Mapping[str, Any],
) -> str:
    if policy["adoption_state"] != "adopted" or not evaluations:
        return "unbound"
    result = "current"
    for evaluation in evaluations:
        result = _merge_freshness(result, str(evaluation["freshness"]))
    return result


def _build_requalification_plan(
    evaluations: Sequence[Mapping[str, Any]],
    policy: Mapping[str, Any],
) -> dict[str, Any]:
    invalid = [item for item in evaluations if item["freshness"] != "current"]
    if not evaluations:
        fallback = sorted(
            {
                kind
                for rule in policy["evidence_kind_rules"]
                for kind in rule["requalification_evidence_kinds"]
            }
        )
        reasons = ["no_evidence"]
        requirements = [{"reason": "no_evidence", "evidence_kinds": fallback}]
        return {
            "required": True,
            "reasons": reasons,
            "invalidated_evidence_refs": [],
            "required_evidence_kinds": fallback,
            "requirements": requirements,
            "next_assessment_trigger": (
                "Reassess after evidence satisfying every listed requirement is registered."
            ),
        }
    if not invalid:
        return {
            "required": False,
            "reasons": [],
            "invalidated_evidence_refs": [],
            "required_evidence_kinds": [],
            "requirements": [],
            "next_assessment_trigger": (
                "Reassess on subject, environment, tool, profile, rule, policy, or expiry change."
            ),
        }
    reason_to_kinds: dict[str, set[str]] = {}
    for evaluation in invalid:
        kinds = set(evaluation["required_requalification_evidence_kinds"])
        for reason in evaluation["reasons"]:
            reason_to_kinds.setdefault(str(reason), set()).update(kinds)
    requirements = [
        {"reason": reason, "evidence_kinds": sorted(kinds)}
        for reason, kinds in sorted(reason_to_kinds.items())
    ]
    all_kinds = sorted({kind for kinds in reason_to_kinds.values() for kind in kinds})
    return {
        "required": True,
        "reasons": sorted(reason_to_kinds),
        "invalidated_evidence_refs": sorted(
            (copy.deepcopy(item["evidence_ref"]) for item in invalid),
            key=lambda item: item["evidence_id"],
        ),
        "required_evidence_kinds": all_kinds,
        "requirements": requirements,
        "next_assessment_trigger": (
            "Reassess after evidence satisfying every listed requirement is registered."
        ),
    }


def _refs_for_ids(
    evidence_by_id: Mapping[str, Mapping[str, Any]],
    evidence_ids: Iterable[str],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for evidence_id in sorted(set(evidence_ids)):
        evidence = evidence_by_id.get(evidence_id)
        if evidence is None:
            raise StateAssessmentError(f"unknown evidence reference: {evidence_id}")
        result.append(_evidence_ref(evidence))
    return result


def _rules_for_ids(
    rule_by_id: Mapping[str, Mapping[str, Any]],
    rule_ids: Iterable[str],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for rule_id in sorted(set(rule_ids)):
        rule = rule_by_id.get(rule_id)
        if rule is None:
            raise StateAssessmentError(f"unknown rule reference: {rule_id}")
        result.append(copy.deepcopy(dict(rule)))
    return result


def _claim_ceiling(
    policy: Mapping[str, Any], evidence_kind: str
) -> dict[str, set[str]]:
    rule = _policy_rules(policy).get(evidence_kind)
    if rule is None:
        return {}
    return {
        str(item["axis"]): {str(value) for value in item["allowed_values"]}
        for item in rule["claim_ceiling"]
    }


def _derive_explicit_axes(
    *,
    observations: Sequence[Mapping[str, Any]],
    evaluations: Sequence[Mapping[str, Any]],
    validity_policy: Mapping[str, Any],
    support_ids: set[str],
    counter_ids: set[str],
    rules: Sequence[Mapping[str, Any]],
    requested_axes: Mapping[str, str],
    basis_inputs: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[str, str], dict[str, Any]]:
    evidence_by_id = {str(item["evidence_id"]): item for item in observations}
    rule_by_id = {str(item["entity_id"]): item for item in rules}
    evaluation_by_id = {
        str(item["evidence_ref"]["evidence_id"]): item for item in evaluations
    }
    candidates: dict[str, list[tuple[str, str, str]]] = {
        axis: [] for axis in _EXPLICIT_AXES
    }

    for evidence in observations:
        evidence_id = str(evidence["evidence_id"])
        ceiling = _claim_ceiling(validity_policy, str(evidence["evidence_kind"]))
        for effect in evidence["claim_effects"]:
            axis = str(effect["axis"])
            value = str(effect["value"])
            if value not in ceiling.get(axis, set()):
                raise StateAssessmentError(
                    f"evidence kind {evidence['evidence_kind']} exceeds its claim ceiling "
                    f"with {axis}={value}"
                )
            evaluation = evaluation_by_id[evidence_id]
            if (
                evidence_id in support_ids
                and evaluation["freshness"] == "current"
                and evaluation["subject_binding"] == "bound"
            ):
                candidates[axis].append(
                    (evidence_id, value, str(effect["rule_id"]))
                )

    axes: dict[str, str] = {}
    derivations: dict[str, Any] = {}
    for axis in _EXPLICIT_AXES:
        requested = requested_axes.get(axis)
        if requested is not None and requested not in {
            "not_assessed",
            *_AXIS_VALUES[axis],
        }:
            raise StateAssessmentError(f"invalid {axis} assertion: {requested}")
        asserted = None if requested in (None, "not_assessed") else requested
        basis = basis_inputs.get(axis)
        effect_values = {value for _evidence_id, value, _rule_id in candidates[axis]}
        if len(effect_values) > 1:
            raise StateAssessmentError(
                f"conflicting typed evidence effects for {axis}: {sorted(effect_values)!r}"
            )

        if effect_values:
            derived = next(iter(effect_values))
            if asserted is not None and asserted != derived:
                raise StateAssessmentError(
                    f"asserted {axis}={asserted} contradicts typed evidence effect {derived}"
                )
            evidence_ids = {
                evidence_id for evidence_id, _value, _rule_id in candidates[axis]
            }
            rule_ids = {rule_id for _evidence_id, _value, rule_id in candidates[axis]}
            if basis is not None:
                supplied_evidence = set(str(item) for item in basis.get("evidence_ids", ()))
                supplied_rules = set(str(item) for item in basis.get("rule_ids", ()))
                if supplied_evidence != evidence_ids or supplied_rules != rule_ids:
                    raise StateAssessmentError(
                        f"axis basis for {axis} differs from its typed evidence effects"
                    )
            axes[axis] = derived
            derivations[axis] = {
                "mode": "typed_evidence_effect",
                "value": derived,
                "asserted_value": asserted,
                "basis_evidence_refs": _refs_for_ids(evidence_by_id, evidence_ids),
                "basis_rule_refs": _rules_for_ids(rule_by_id, rule_ids),
                "rationale": (
                    "Derived from current, subject-bound supporting evidence effects "
                    "within the adopted evidence-kind claim ceiling."
                ),
            }
            continue

        if asserted is None:
            if basis is not None:
                raise StateAssessmentError(
                    f"not_assessed axis {axis} cannot carry a positive basis"
                )
            axes[axis] = "not_assessed"
            derivations[axis] = {
                "mode": "not_assessed",
                "value": "not_assessed",
                "asserted_value": None,
                "basis_evidence_refs": [],
                "basis_rule_refs": [],
                "rationale": "No typed evidence effect or explicit assertion was supplied.",
            }
            continue

        if basis is None:
            raise StateAssessmentError(
                f"explicit assertion for {axis} requires its own audit basis"
            )
        evidence_ids = set(str(item) for item in basis.get("evidence_ids", ()))
        rule_ids = set(str(item) for item in basis.get("rule_ids", ()))
        rationale = str(basis.get("rationale", ""))
        if not rationale or (not evidence_ids and not rule_ids):
            raise StateAssessmentError(
                f"explicit assertion for {axis} requires a rationale and evidence or rule basis"
            )
        counter_basis = evidence_ids & counter_ids
        if counter_basis:
            raise StateAssessmentError(
                f"counterevidence cannot be used as a positive {axis} basis: {sorted(counter_basis)!r}"
            )
        if not evidence_ids <= support_ids:
            raise StateAssessmentError(f"unknown supporting evidence basis for {axis}")
        evidence_refs = _refs_for_ids(evidence_by_id, evidence_ids)
        rule_refs = _rules_for_ids(rule_by_id, rule_ids)
        for evidence_id in evidence_ids:
            evidence = evidence_by_id[evidence_id]
            ceiling = _claim_ceiling(
                validity_policy, str(evidence["evidence_kind"])
            )
            if asserted not in ceiling.get(axis, set()):
                raise StateAssessmentError(
                    f"evidence kind {evidence['evidence_kind']} cannot support asserted "
                    f"{axis}={asserted}; claim ceiling exceeded"
                )
        axes[axis] = "not_assessed"
        derivations[axis] = {
            "mode": "asserted_input_unproved",
            "value": "not_assessed",
            "asserted_value": asserted,
            "basis_evidence_refs": evidence_refs,
            "basis_rule_refs": rule_refs,
            "rationale": rationale,
        }
    return axes, derivations


def build_state_assessment(
    *,
    assessment_id: str,
    proposition: str,
    subject_manifest: Mapping[str, Any],
    validity_policy: Mapping[str, Any],
    assessed_at: str,
    time_trust: str,
    evidence_observations: Sequence[Mapping[str, Any]],
    current_environment_bindings: Sequence[Mapping[str, Any]],
    current_tool_identity: Mapping[str, Any],
    current_profile_bindings: Sequence[Mapping[str, Any]],
    applied_rules: Sequence[Mapping[str, Any]],
    axis_values: Mapping[str, str] | None = None,
    axis_basis: Mapping[str, Mapping[str, Any]] | None = None,
    supporting_evidence_ids: Sequence[str] = (),
    counterevidence_ids: Sequence[str] = (),
    unproven_scope: Sequence[str] = (),
    human_acceptance_record: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build and replay-validate an independent-axis state assessment."""

    validate_subject_manifest(subject_manifest)
    validate_validity_policy(validity_policy)
    _parse_timestamp(assessed_at, "assessed_at")

    observations = sorted(
        (copy.deepcopy(dict(item)) for item in evidence_observations),
        key=lambda item: item["evidence_id"],
    )
    for observation in observations:
        validate_evidence_observation(observation)
    _require_unique(observations, "evidence_id", "evidence_observations")
    evidence_by_id = {str(item["evidence_id"]): item for item in observations}

    support_ids = set(supporting_evidence_ids)
    counter_ids = set(counterevidence_ids)
    if support_ids & counter_ids:
        raise StateAssessmentError(
            f"evidence cannot both support and counter: {sorted(support_ids & counter_ids)!r}"
        )
    declared_ids = set(evidence_by_id)
    if support_ids | counter_ids != declared_ids:
        raise StateAssessmentError(
            "supporting and counterevidence references must cover every declared evidence "
            f"exactly once; declared={sorted(declared_ids)!r}, "
            f"referenced={sorted(support_ids | counter_ids)!r}"
        )

    rules = _sort_bindings(applied_rules)
    _require_unique(rules, "entity_id", "applied_rules")
    current_context = {
        "environment_bindings": _sort_bindings(current_environment_bindings),
        "tool_identity": copy.deepcopy(dict(current_tool_identity)),
        "profile_bindings": _sort_bindings(current_profile_bindings),
        "rule_bindings": copy.deepcopy(rules),
    }

    evaluations = [
        _evaluate_evidence(
            item,
            manifest=subject_manifest,
            policy=validity_policy,
            assessed_at=assessed_at,
            assessment_time_trust=time_trust,
            current_context=current_context,
        )
        for item in observations
    ]
    freshness = _overall_freshness(evaluations, validity_policy)

    requested_axes = dict(axis_values or {})
    forbidden_axes = set(requested_axes) - set(_EXPLICIT_AXES)
    if forbidden_axes:
        raise StateAssessmentError(
            "freshness and human acceptance are not explicit-input axes: "
            f"{sorted(forbidden_axes)!r}"
        )
    basis_inputs = dict(axis_basis or {})
    unknown_basis_axes = set(basis_inputs) - set(_EXPLICIT_AXES)
    if unknown_basis_axes:
        raise StateAssessmentError(
            "axis basis cannot target freshness or human acceptance: "
            f"{sorted(unknown_basis_axes)!r}"
        )
    axes, axis_derivations = _derive_explicit_axes(
        observations=observations,
        evaluations=evaluations,
        validity_policy=validity_policy,
        support_ids=support_ids,
        counter_ids=counter_ids,
        rules=rules,
        requested_axes=requested_axes,
        basis_inputs=basis_inputs,
    )

    axes["freshness"] = freshness
    axis_derivations["freshness"] = {
        "mode": "validity_policy_derivation",
        "value": freshness,
        "evidence_evaluation_refs": [
            copy.deepcopy(item["evidence_ref"]) for item in evaluations
        ],
        "rationale": (
            "Freshness is the fail-closed aggregate of subject binding, policy "
            "adoption, time, expiry, trust, and identity-change evaluations."
        ),
    }

    acceptance_record = (
        copy.deepcopy(dict(human_acceptance_record))
        if human_acceptance_record is not None
        else None
    )
    axes["human_acceptance"] = "pending"
    axis_derivations["human_acceptance"] = {
        "mode": "pending_without_external_record",
        "value": "pending",
        "decision_record_ref": None,
        "rationale": "State assessment cannot make the human acceptance decision.",
    }

    requalification_plan = _build_requalification_plan(
        evaluations, validity_policy
    )
    assessment: dict[str, Any] = {
        "schema_version": STATE_ASSESSMENT_VERSION,
        "assessment_id": assessment_id,
        "proposition": proposition,
        "subject_manifest_ref": _manifest_ref(subject_manifest),
        "validity_policy_ref": _policy_ref(validity_policy),
        "current_context": current_context,
        "assessed_at": assessed_at,
        "time_trust": time_trust,
        "axes": axes,
        "axis_derivations": axis_derivations,
        "evidence_observations": observations,
        "evidence_evaluations": evaluations,
        "applied_rules": rules,
        "supporting_evidence_refs": _refs_for_ids(evidence_by_id, support_ids),
        "counterevidence_refs": _refs_for_ids(evidence_by_id, counter_ids),
        "unproven_scope": sorted(set(unproven_scope)),
        "requalification_plan": requalification_plan,
        "human_acceptance_record": None,
        "limitations": [
            _CONTROL_LIMITATION,
            _DENOMINATOR_LIMITATION,
            _TIME_LIMITATION,
        ],
    }
    assessment["acceptance_basis_digest"] = _digest(
        _acceptance_basis_material(assessment)
    )
    if acceptance_record is not None:
        if acceptance_record.get("decided_by") != acceptance_record.get(
            "decision_maker_identity", {}
        ).get("entity_id"):
            raise StateAssessmentError(
                "human acceptance decision identity does not match decided_by"
            )
        expected_target = {
            "decision_kind": "accept_state_assessment",
            "assessment_id": assessment_id,
            "subject_manifest_ref": _manifest_ref(subject_manifest),
            "target_basis_digest": assessment["acceptance_basis_digest"],
        }
        for field, expected_value in expected_target.items():
            if acceptance_record.get(field) != expected_value:
                raise StateAssessmentError(
                    f"human acceptance record {field} targets another technical assessment basis"
                )
        if _parse_timestamp(
            str(acceptance_record.get("decided_at")),
            "human_acceptance_record.decided_at",
        ) < _parse_timestamp(assessed_at, "assessed_at"):
            raise StateAssessmentError(
                "human acceptance record predates the assessment it claims to decide"
            )
        assessment["human_acceptance_record"] = acceptance_record
        assessment["axes"]["human_acceptance"] = str(acceptance_record["status"])
        assessment["axis_derivations"]["human_acceptance"] = {
            "mode": "external_human_record",
            "value": acceptance_record["status"],
            "decision_record_ref": copy.deepcopy(acceptance_record["record_ref"]),
            "rationale": "Copied from the explicitly supplied external human record.",
        }
    assessment["assessment_digest"] = _digest(assessment)
    validate_state_assessment(
        assessment,
        subject_manifest=subject_manifest,
        validity_policy=validity_policy,
    )
    return assessment


def _validate_ref_collection(
    references: Sequence[Mapping[str, Any]],
    evidence_by_id: Mapping[str, Mapping[str, Any]],
    location: str,
) -> set[str]:
    ids = [str(reference["evidence_id"]) for reference in references]
    if len(ids) != len(set(ids)):
        raise StateAssessmentError(f"duplicate evidence reference at {location}")
    for reference in references:
        evidence = evidence_by_id.get(str(reference["evidence_id"]))
        if evidence is None:
            raise StateAssessmentError(
                f"dangling evidence reference at {location}: {reference['evidence_id']}"
            )
        if reference["content_digest"] != evidence["content_digest"]:
            raise StateAssessmentError(
                f"evidence digest mismatch at {location}: {reference['evidence_id']}"
            )
    return set(ids)


def validate_state_assessment(
    assessment: Mapping[str, Any],
    *,
    subject_manifest: Mapping[str, Any],
    validity_policy: Mapping[str, Any],
) -> None:
    """Validate and deterministically replay a state assessment."""

    validate_subject_manifest(subject_manifest)
    validate_validity_policy(validity_policy)
    _validate_schema(
        assessment,
        _validator("state-assessment.schema.json"),
        "state assessment",
    )
    expected_digest = _digest(_without_digest(assessment, "assessment_digest"))
    if assessment["assessment_digest"] != expected_digest:
        raise StateAssessmentError("state assessment digest mismatch")
    expected_acceptance_basis = _digest(_acceptance_basis_material(assessment))
    if assessment["acceptance_basis_digest"] != expected_acceptance_basis:
        raise StateAssessmentError("state assessment acceptance basis digest mismatch")
    if assessment["subject_manifest_ref"] != _manifest_ref(subject_manifest):
        raise StateAssessmentError("assessment subject manifest reference mismatch")
    if assessment["validity_policy_ref"] != _policy_ref(validity_policy):
        raise StateAssessmentError("assessment validity policy reference mismatch")

    observations = list(assessment["evidence_observations"])
    for observation in observations:
        validate_evidence_observation(observation)
    _require_unique(observations, "evidence_id", "evidence_observations")
    evidence_by_id = {str(item["evidence_id"]): item for item in observations}
    support_ids = _validate_ref_collection(
        list(assessment["supporting_evidence_refs"]),
        evidence_by_id,
        "supporting_evidence_refs",
    )
    counter_ids = _validate_ref_collection(
        list(assessment["counterevidence_refs"]),
        evidence_by_id,
        "counterevidence_refs",
    )
    if support_ids & counter_ids or support_ids | counter_ids != set(evidence_by_id):
        raise StateAssessmentError(
            "supporting and counterevidence references must partition observations"
        )

    rules = list(assessment["applied_rules"])
    _require_unique(rules, "entity_id", "applied_rules")
    context = assessment["current_context"]
    for field in ("environment_bindings", "profile_bindings", "rule_bindings"):
        _require_unique(list(context[field]), "entity_id", f"current_context.{field}")
    if _binding_set(context["rule_bindings"]) != _binding_set(rules):
        raise StateAssessmentError(
            "current context rule bindings differ from applied rules"
        )

    replayed_evaluations = [
        _evaluate_evidence(
            item,
            manifest=subject_manifest,
            policy=validity_policy,
            assessed_at=str(assessment["assessed_at"]),
            assessment_time_trust=str(assessment["time_trust"]),
            current_context=context,
        )
        for item in observations
    ]
    if assessment["evidence_evaluations"] != replayed_evaluations:
        raise StateAssessmentError("evidence evaluations do not replay exactly")
    freshness = _overall_freshness(replayed_evaluations, validity_policy)
    if assessment["axes"]["freshness"] != freshness:
        raise StateAssessmentError("freshness axis does not match validity replay")
    freshness_derivation = assessment["axis_derivations"]["freshness"]
    if freshness_derivation["value"] != freshness:
        raise StateAssessmentError("freshness derivation value does not match axis")
    expected_evaluation_refs = [
        copy.deepcopy(item["evidence_ref"]) for item in replayed_evaluations
    ]
    if freshness_derivation["evidence_evaluation_refs"] != expected_evaluation_refs:
        raise StateAssessmentError("freshness derivation omits evidence evaluations")

    replay_requested: dict[str, str] = {}
    replay_basis: dict[str, Mapping[str, Any]] = {}
    for axis in _EXPLICIT_AXES:
        derivation = assessment["axis_derivations"][axis]
        if derivation["asserted_value"] is not None:
            replay_requested[axis] = str(derivation["asserted_value"])
        if derivation["basis_evidence_refs"] or derivation["basis_rule_refs"]:
            replay_basis[axis] = {
                "evidence_ids": [
                    item["evidence_id"]
                    for item in derivation["basis_evidence_refs"]
                ],
                "rule_ids": [
                    item["entity_id"] for item in derivation["basis_rule_refs"]
                ],
                "rationale": derivation["rationale"],
            }
    replayed_axes, replayed_derivations = _derive_explicit_axes(
        observations=observations,
        evaluations=replayed_evaluations,
        validity_policy=validity_policy,
        support_ids=support_ids,
        counter_ids=counter_ids,
        rules=rules,
        requested_axes=replay_requested,
        basis_inputs=replay_basis,
    )
    if any(assessment["axes"][axis] != replayed_axes[axis] for axis in _EXPLICIT_AXES):
        raise StateAssessmentError("explicit state axes do not replay from typed evidence effects")
    if any(
        assessment["axis_derivations"][axis] != replayed_derivations[axis]
        for axis in _EXPLICIT_AXES
    ):
        raise StateAssessmentError("explicit axis derivations do not replay exactly")

    record = assessment["human_acceptance_record"]
    acceptance = assessment["axes"]["human_acceptance"]
    acceptance_derivation = assessment["axis_derivations"]["human_acceptance"]
    if record is None:
        if (
            acceptance != "pending"
            or acceptance_derivation["mode"] != "pending_without_external_record"
            or acceptance_derivation["value"] != "pending"
            or acceptance_derivation["decision_record_ref"] is not None
        ):
            raise StateAssessmentError(
                "human acceptance must remain pending without an external record"
            )
    else:
        if (
            record["decision_kind"] != "accept_state_assessment"
            or record["assessment_id"] != assessment["assessment_id"]
            or record["subject_manifest_ref"] != assessment["subject_manifest_ref"]
            or record["target_basis_digest"]
            != assessment["acceptance_basis_digest"]
            or record["status"] != acceptance
            or acceptance_derivation["mode"] != "external_human_record"
            or acceptance_derivation["value"] != acceptance
            or acceptance_derivation["decision_record_ref"] != record["record_ref"]
        ):
            raise StateAssessmentError(
                "human acceptance axis is not bound to the explicit external record"
            )
        if record["decided_by"] != record["decision_maker_identity"]["entity_id"]:
            raise StateAssessmentError(
                "human acceptance decision identity does not match decided_by"
            )
        if _parse_timestamp(
            str(record["decided_at"]), "human_acceptance_record.decided_at"
        ) < _parse_timestamp(str(assessment["assessed_at"]), "assessed_at"):
            raise StateAssessmentError(
                "human acceptance record predates the assessment it claims to decide"
            )

    replayed_plan = _build_requalification_plan(
        replayed_evaluations, validity_policy
    )
    if assessment["requalification_plan"] != replayed_plan:
        raise StateAssessmentError("requalification plan does not replay exactly")
