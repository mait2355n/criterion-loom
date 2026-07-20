"""Candidate lifecycle-profile registry and fail-closed validation.

The registry supplies meaning contracts for the ten lifecycle stages.  It is
candidate audit material only: validation never adopts a profile, grants
decision or execution authority, establishes that an action occurred, or
performs human final acceptance.
"""

from __future__ import annotations

import copy
from functools import lru_cache
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from jsonschema import Draft202012Validator, FormatChecker

from .schema_access import schema_path


SCHEMA_VERSION = "lifecycle-profile-registry/v0"
SUMMARY_VERSION = "lifecycle-profile-registry-summary/v0"
STAGES = (
    "request",
    "exploration",
    "requirement",
    "decision",
    "plan",
    "action",
    "realization",
    "diff",
    "verification",
    "completion",
)
STAGE_RANK = {stage: index for index, stage in enumerate(STAGES)}
TRACE_STAGE_BY_PROFILE_STAGE = {
    "request": "request",
    "exploration": "exploration_question",
    "requirement": "requirement",
    "decision": "decision",
    "plan": "plan",
    "action": "action",
    "realization": "realization",
    "diff": "diff",
    "verification": "verification",
    "completion": "completion_claim",
}
ORIGIN_REQUIREMENTS = frozenset({"OR-01", "OR-02", "OR-03"})

_SCHEMA_PATH = schema_path("lifecycle-profile-registry.schema.json")
_SOURCE_CANDIDATE_PATH = (
    Path(__file__).resolve().parents[2]
    / "validation/lifecycle-profile-registry.candidate.json"
)
_PACKAGED_CANDIDATE_PATH = (
    Path(__file__).resolve().parent
    / "validation/lifecycle-profile-registry.candidate.json"
)
_SOURCE_ROOT = Path(__file__).resolve().parents[2]
_CANDIDATE_PATH = (
    _PACKAGED_CANDIDATE_PATH
    if _PACKAGED_CANDIDATE_PATH.is_file()
    else _SOURCE_CANDIDATE_PATH
    if (_SOURCE_ROOT / "pyproject.toml").is_file()
    and (_SOURCE_ROOT / "src" / "semantic_guard").resolve()
    == Path(__file__).resolve().parent
    and _SOURCE_CANDIDATE_PATH.is_file()
    else _PACKAGED_CANDIDATE_PATH
)
_SUMMARY_AUTHORITY_STATEMENT = (
    "All lifecycle profiles remain pending human adoption; semantic-guard "
    "validates candidate material only and holds no adoption, execution, or "
    "final-acceptance authority."
)

_REQUIRED_PROMOTIONS = {
    "decision": frozenset(
        {"audit_result_implies_decision", "agent_infers_human_decision"}
    ),
    "action": frozenset(
        {
            "description_implies_occurrence",
            "audit_result_grants_execution_authority",
        }
    ),
    "completion": frozenset(
        {
            "local_tests_imply_final_acceptance",
            "audit_result_implies_final_acceptance",
        }
    ),
}


class LifecycleProfileRegistryValidationError(ValueError):
    """Raised when a candidate registry fails schema or semantic closure."""

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
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    """Return a deterministic SHA-256 for canonical JSON material."""

    return hashlib.sha256(_canonical(value)).hexdigest()


def digest_value(value: Any) -> dict[str, str]:
    return {"algorithm": "sha256", "value": canonical_sha256(value)}


def _without(value: Mapping[str, Any], *fields: str) -> dict[str, Any]:
    result = copy.deepcopy(dict(value))
    for field in fields:
        result.pop(field, None)
    return result


def _profile_material(profile: Mapping[str, Any]) -> dict[str, Any]:
    return _without(profile, "profile_digest")


def _registry_material(registry: Mapping[str, Any]) -> dict[str, Any]:
    return _without(registry, "registry_digest", "summary")


def _summary_material(summary: Mapping[str, Any]) -> dict[str, Any]:
    return _without(summary, "summary_digest")


def _schema_location(path: Iterable[Any]) -> str:
    values = [str(item) for item in path]
    return "$" if not values else "$." + ".".join(values)


def _add(
    errors: list[dict[str, str]], code: str, location: str, message: str
) -> None:
    errors.append({"code": code, "location": location, "message": message})


def _duplicates(values: Iterable[str]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return duplicates


def _list_or_empty(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


@lru_cache(maxsize=1)
def lifecycle_profile_registry_schema() -> dict[str, Any]:
    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return schema


@lru_cache(maxsize=1)
def _schema_validator() -> Draft202012Validator:
    return Draft202012Validator(
        lifecycle_profile_registry_schema(), format_checker=FormatChecker()
    )


def load_candidate_registry(path: str | Path | None = None) -> dict[str, Any]:
    """Load the repository candidate without granting it runtime authority."""

    target = _CANDIDATE_PATH if path is None else Path(path)
    return json.loads(target.read_text(encoding="utf-8"))


def build_registry_summary(registry: Mapping[str, Any]) -> dict[str, Any]:
    """Replay the saved summary from content-addressed source material."""

    profiles = list(registry.get("profiles", []))
    ordered = sorted(
        profiles,
        key=lambda item: STAGE_RANK.get(str(item.get("stage", "")), len(STAGES)),
    )
    coverage = {
        origin: sorted(
            str(profile.get("profile_id", ""))
            for profile in profiles
            if origin
            in set(profile.get("upstream_trace", {}).get("origin_requirements", []))
        )
        for origin in sorted(ORIGIN_REQUIREMENTS)
    }
    statuses = [str(profile.get("status", "")) for profile in profiles]
    material: dict[str, Any] = {
        "schema_version": SUMMARY_VERSION,
        "registry_id": registry.get("registry_id"),
        "registry_version": registry.get("version"),
        "registry_digest": copy.deepcopy(registry.get("registry_digest")),
        "profile_count": len(profiles),
        "stage_order": list(registry.get("stage_order", [])),
        "profile_refs": [
            {
                "stage": profile.get("stage"),
                "profile_id": profile.get("profile_id"),
                "version": profile.get("version"),
                "profile_digest": copy.deepcopy(profile.get("profile_digest")),
            }
            for profile in ordered
        ],
        "origin_coverage": coverage,
        "adoption_counts": {
            "pending_human_adoption": statuses.count("pending_human_adoption"),
            "adopted": statuses.count("adopted"),
        },
        "authority_statement": _SUMMARY_AUTHORITY_STATEMENT,
    }
    return {**material, "summary_digest": digest_value(material)}


def seal_lifecycle_profile_registry(registry: Mapping[str, Any]) -> dict[str, Any]:
    """Content-address a candidate and rebuild its deterministic summary.

    This is a pure structural operation.  The returned status remains
    ``candidate`` and every profile remains ``pending_human_adoption``.
    """

    sealed = copy.deepcopy(dict(registry))
    sealed.pop("registry_digest", None)
    sealed.pop("summary", None)
    sealed_profiles: list[dict[str, Any]] = []
    for raw_profile in sealed.get("profiles", []):
        profile = _without(raw_profile, "profile_digest")
        profile["profile_digest"] = digest_value(profile)
        sealed_profiles.append(profile)
    sealed["profiles"] = sealed_profiles
    sealed["registry_digest"] = digest_value(_registry_material(sealed))
    sealed["summary"] = build_registry_summary(sealed)
    return sealed


def _preflight_semantic_errors(
    registry: Mapping[str, Any], errors: list[dict[str, str]]
) -> None:
    """Find critical boundary errors even when the JSON Schema also fails."""

    if registry.get("status") != "candidate":
        _add(
            errors,
            "adoption_authority_violation",
            "$.status",
            "the registry may only describe a candidate pending human adoption",
        )
    authority = registry.get("authority_boundary")
    expected_registry_authority = {
        "adoption_owner": "human",
        "semantic_guard_adoption_authority": "none",
        "agent_adoption_authority": "none",
        "runtime_authority": "none",
        "final_acceptance_owner": "human",
    }
    if not isinstance(authority, Mapping) or dict(authority) != expected_registry_authority:
        _add(
            errors,
            "adoption_authority_violation",
            "$.authority_boundary",
            "profile adoption and final acceptance remain human-owned; runtime authority is none",
        )

    stage_order = registry.get("stage_order")
    if not isinstance(stage_order, list) or tuple(stage_order) != STAGES:
        _add(
            errors,
            "stage_order_invalid",
            "$.stage_order",
            "the closed ten-stage denominator or its order changed",
        )

    profiles = registry.get("profiles")
    if not isinstance(profiles, list):
        _add(
            errors,
            "stage_denominator_incomplete",
            "$.profiles",
            "profiles must be a closed list of all ten stages",
        )
        return

    stages = [str(item.get("stage", "")) for item in profiles if isinstance(item, Mapping)]
    if len(profiles) != len(STAGES) or set(stages) != set(STAGES):
        missing = sorted(set(STAGES) - set(stages))
        extra = sorted(set(stages) - set(STAGES))
        _add(
            errors,
            "stage_denominator_incomplete",
            "$.profiles",
            f"expected exactly ten stages; missing={missing}, extra={extra}",
        )
    if tuple(stages) != STAGES:
        _add(
            errors,
            "profile_order_invalid",
            "$.profiles",
            "profile order must replay the declared lifecycle order",
        )

    denominator_fields = (
        "entry_conditions",
        "exit_conditions",
        "required_semantic_fields",
        "required_relationships",
        "obligation_templates",
        "non_goals",
        "hollow_success_conditions",
        "verification_evidence_types",
        "validation_materials",
        "human_acceptance_questions",
        "unresolved",
        "requalification_triggers",
    )
    for index, profile in enumerate(profiles):
        if not isinstance(profile, Mapping):
            continue
        location = f"$.profiles.{index}"
        stage = str(profile.get("stage", ""))
        if profile.get("status") != "pending_human_adoption":
            _add(
                errors,
                "adoption_authority_violation",
                f"{location}.status",
                "a profile cannot claim adoption before a located human decision",
            )
        for field in denominator_fields:
            value = profile.get(field)
            if not isinstance(value, list) or not value:
                _add(
                    errors,
                    "empty_required_denominator",
                    f"{location}.{field}",
                    "a required semantic denominator cannot be absent or empty",
                )

        upstream = profile.get("upstream_trace")
        if isinstance(upstream, Mapping):
            origins = set(_list_or_empty(upstream.get("origin_requirements")))
            if origins != ORIGIN_REQUIREMENTS:
                _add(
                    errors,
                    "origin_trace_incomplete",
                    f"{location}.upstream_trace.origin_requirements",
                    "every profile must remain traceable to OR-01, OR-02, and OR-03",
                )
            refs = upstream.get("stage_refs", [])
            if isinstance(refs, list):
                for ref in refs:
                    if ref not in STAGE_RANK:
                        _add(
                            errors,
                            "unknown_stage_reference",
                            f"{location}.upstream_trace.stage_refs",
                            f"unknown upstream stage: {ref}",
                        )
                    elif stage in STAGE_RANK and STAGE_RANK[ref] >= STAGE_RANK[stage]:
                        _add(
                            errors,
                            "stage_reference_direction_invalid",
                            f"{location}.upstream_trace.stage_refs",
                            f"upstream reference is not earlier than {stage}: {ref}",
                        )
        downstream = profile.get("downstream_trace")
        if isinstance(downstream, Mapping):
            refs = downstream.get("stage_refs", [])
            if isinstance(refs, list):
                for ref in refs:
                    if ref not in STAGE_RANK:
                        _add(
                            errors,
                            "unknown_stage_reference",
                            f"{location}.downstream_trace.stage_refs",
                            f"unknown downstream stage: {ref}",
                        )
                    elif stage in STAGE_RANK and STAGE_RANK[ref] <= STAGE_RANK[stage]:
                        _add(
                            errors,
                            "stage_reference_direction_invalid",
                            f"{location}.downstream_trace.stage_refs",
                            f"downstream reference is not later than {stage}: {ref}",
                        )

        hollow = _list_or_empty(profile.get("hollow_success_conditions"))
        kinds = {
            item.get("condition_kind")
            for item in hollow
            if isinstance(item, Mapping)
        }
        if "artifact_presence_only" not in kinds:
            _add(
                errors,
                "hollow_success_coverage_missing",
                f"{location}.hollow_success_conditions",
                "artifact presence alone must be named as a hollow-success condition",
            )

        profile_authority = profile.get("authority_boundary")
        if not isinstance(profile_authority, Mapping):
            _add(
                errors,
                "profile_authority_boundary_invalid",
                f"{location}.authority_boundary",
                "profile authority boundary is missing",
            )
            continue
        if (
            profile_authority.get("semantic_guard_role")
            != "audit_material_validation_only"
            or profile_authority.get("final_acceptance_authority") != "human_only"
        ):
            _add(
                errors,
                "profile_authority_boundary_invalid",
                f"{location}.authority_boundary",
                "semantic-guard may validate audit material but final acceptance remains human-only",
            )
        prohibited = set(
            _list_or_empty(profile_authority.get("prohibited_promotions"))
        )
        missing_promotions = _REQUIRED_PROMOTIONS.get(stage, frozenset()) - prohibited
        if missing_promotions:
            code = {
                "decision": "decision_authority_violation",
                "action": "action_authority_violation",
                "completion": "completion_authority_violation",
            }[stage]
            _add(
                errors,
                code,
                f"{location}.authority_boundary.prohibited_promotions",
                f"required prohibited promotions missing: {sorted(missing_promotions)}",
            )
        if stage == "decision" and not (
            profile_authority.get("claim_owner") == "human"
            and profile_authority.get("decision_authority") == "human_only"
            and profile_authority.get("execution_authority") == "not_applicable"
            and profile_authority.get("occurrence_evidence_required") is False
        ):
            _add(
                errors,
                "decision_authority_violation",
                f"{location}.authority_boundary",
                "decision ownership is human and cannot be inferred from an audit result",
            )
        if stage == "action" and not (
            profile_authority.get("claim_owner") == "explicitly_authorized_actor"
            and profile_authority.get("decision_authority")
            == "external_authority_record_required"
            and profile_authority.get("execution_authority")
            == "external_authority_record_required"
            and profile_authority.get("occurrence_evidence_required") is True
        ):
            _add(
                errors,
                "action_authority_violation",
                f"{location}.authority_boundary",
                "action requires an explicitly authorized actor and separate occurrence evidence",
            )
        if stage == "completion" and not (
            profile_authority.get("claim_owner") == "explicitly_authorized_actor"
            and profile_authority.get("decision_authority") == "not_applicable"
            and profile_authority.get("execution_authority") == "not_applicable"
            and profile_authority.get("occurrence_evidence_required") is False
            and profile_authority.get("final_acceptance_authority") == "human_only"
        ):
            _add(
                errors,
                "completion_authority_violation",
                f"{location}.authority_boundary",
                "an authorized actor may make a completion claim, but only a human may accept it",
            )


def lifecycle_profile_registry_errors(
    registry: Mapping[str, Any],
) -> tuple[dict[str, str], ...]:
    """Return deterministic, fail-closed registry validation errors."""

    errors: list[dict[str, str]] = []
    schema_failures = sorted(
        _schema_validator().iter_errors(registry), key=lambda item: list(item.path)
    )
    for failure in schema_failures:
        _add(
            errors,
            "schema_validation_failed",
            _schema_location(failure.path),
            failure.message,
        )
    _preflight_semantic_errors(registry, errors)
    if schema_failures:
        return tuple(errors)

    profiles = list(registry["profiles"])
    profile_ids = [str(profile["profile_id"]) for profile in profiles]
    for duplicate in sorted(_duplicates(profile_ids)):
        _add(errors, "duplicate_profile_id", "$.profiles", duplicate)
    stages = [str(profile["stage"]) for profile in profiles]
    for duplicate in sorted(_duplicates(stages)):
        _add(errors, "duplicate_profile_stage", "$.profiles", duplicate)

    nested_id_fields = {
        "entry_conditions": "condition_id",
        "exit_conditions": "condition_id",
        "required_semantic_fields": "field_id",
        "required_relationships": "relationship_id",
        "obligation_templates": "obligation_id",
        "hollow_success_conditions": "condition_id",
        "verification_evidence_types": "evidence_type",
        "validation_materials": "material_id",
        "human_acceptance_questions": "question_id",
        "unresolved": "unresolved_id",
        "requalification_triggers": "trigger_id",
    }
    for index, profile in enumerate(profiles):
        location = f"$.profiles.{index}"
        stage = str(profile["stage"])
        expected_profile_id = f"lifecycle-profile.{stage}"
        if profile["profile_id"] != expected_profile_id:
            _add(
                errors,
                "profile_id_stage_mismatch",
                f"{location}.profile_id",
                f"expected {expected_profile_id}",
            )
        expected_trace_stage = TRACE_STAGE_BY_PROFILE_STAGE[stage]
        if profile["lifecycle_trace_stage"] != expected_trace_stage:
            _add(
                errors,
                "lifecycle_trace_stage_mismatch",
                f"{location}.lifecycle_trace_stage",
                f"expected {expected_trace_stage}",
            )

        expected_upstream = [] if stage == STAGES[0] else [STAGES[STAGE_RANK[stage] - 1]]
        expected_downstream = [] if stage == STAGES[-1] else [STAGES[STAGE_RANK[stage] + 1]]
        if profile["upstream_trace"]["stage_refs"] != expected_upstream:
            _add(
                errors,
                "adjacent_upstream_trace_invalid",
                f"{location}.upstream_trace.stage_refs",
                f"expected immediate predecessor trace {expected_upstream}",
            )
        if profile["downstream_trace"]["stage_refs"] != expected_downstream:
            _add(
                errors,
                "adjacent_downstream_trace_invalid",
                f"{location}.downstream_trace.stage_refs",
                f"expected immediate successor trace {expected_downstream}",
            )

        obligation_origins = {
            origin
            for obligation in profile["obligation_templates"]
            for origin in obligation["origin_trace"]
        }
        if obligation_origins != ORIGIN_REQUIREMENTS:
            _add(
                errors,
                "obligation_origin_trace_incomplete",
                f"{location}.obligation_templates",
                "obligation templates must collectively cover OR-01, OR-02, and OR-03",
            )
        for field, id_field in nested_id_fields.items():
            ids = [str(item[id_field]) for item in profile[field]]
            for duplicate in sorted(_duplicates(ids)):
                _add(
                    errors,
                    "duplicate_profile_member_id",
                    f"{location}.{field}",
                    duplicate,
                )

        expected_profile_digest = digest_value(_profile_material(profile))
        if profile["profile_digest"] != expected_profile_digest:
            _add(
                errors,
                "profile_digest_mismatch",
                f"{location}.profile_digest",
                "profile content changed after content addressing",
            )

    expected_registry_digest = digest_value(_registry_material(registry))
    if registry["registry_digest"] != expected_registry_digest:
        _add(
            errors,
            "registry_digest_mismatch",
            "$.registry_digest",
            "registry content changed after content addressing",
        )

    expected_summary = build_registry_summary(
        {**dict(registry), "registry_digest": expected_registry_digest}
    )
    if registry["summary"] != expected_summary:
        _add(
            errors,
            "summary_replay_mismatch",
            "$.summary",
            "saved summary does not replay exactly from the candidate registry",
        )
    elif registry["summary"]["summary_digest"] != digest_value(
        _summary_material(registry["summary"])
    ):
        _add(
            errors,
            "summary_digest_mismatch",
            "$.summary.summary_digest",
            "summary digest does not replay",
        )

    return tuple(errors)


def validate_lifecycle_profile_registry(
    registry: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate and return a copy; never adopt or activate the profiles."""

    errors = lifecycle_profile_registry_errors(registry)
    if errors:
        raise LifecycleProfileRegistryValidationError(errors)
    return copy.deepcopy(dict(registry))
