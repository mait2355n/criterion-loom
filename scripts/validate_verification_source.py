from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
import hashlib
from importlib import metadata
import json
from pathlib import Path
import platform
import re
import sys
from typing import Any
from urllib.parse import unquote

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError
from referencing import Registry, Resource
from referencing.exceptions import (
    CannotDetermineSpecification,
    NoSuchResource,
    PointerToNowhere,
    Unresolvable,
)

from semantic_guard.verification_projection import (
    render_verification_projection,
)


RESULT_SCHEMA_VERSION = "semantic-guard-verification-validation-result/v0"
VERIFICATION_SOURCE_SCHEMA_ID = (
    "https://semantic-guard.local/v1/validation/verification-source.schema.json"
)
VERIFICATION_SOURCE_SCHEMA_REF = "./verification-source.schema.json"
GAP_REGISTER_SCHEMA_ID = (
    "https://semantic-guard.local/v1/validation/verification-gap-register.schema.json"
)
GAP_REGISTER_SCHEMA_REF = "./verification-gap-register.schema.json"
GAP_REGISTER_VERSION = "semantic-guard-verification-gap-register/v0"
GAP_SOURCE_LOCATOR = "verification-source.json"
COMMON_SCHEMA_ID = "https://semantic-guard.local/v1/schemas/common.schema.json"
SUBJECT_MANIFEST_VERSION = "semantic-guard-evidence-subject-manifest/v0"
VALIDATOR_PATH = Path(__file__).resolve()


def _sha256(path: Path) -> str:
    value = _file_digest(path, "sha256")
    if value is None:  # pragma: no cover - sha256 is required by Python.
        raise RuntimeError("sha256 is unavailable")
    return value


def _canonical_json_digest(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _text_digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _file_digest(path: Path, algorithm: str) -> str | None:
    if algorithm == "other":
        return None
    try:
        digest = hashlib.new(algorithm)
    except ValueError:
        return None
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _error(
    errors: list[dict[str, str]],
    code: str,
    location: str,
    message: str,
) -> None:
    errors.append({"code": code, "location": location, "message": message})


def _load_json(
    path: Path,
    errors: list[dict[str, str]],
    location: str,
) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        _error(errors, "json_load_failed", location, str(exc))
        return None
    if not isinstance(value, dict):
        _error(errors, "json_root_not_object", location, "JSON root must be an object")
        return None
    return value


def _resolve_inside_root(
    root: Path,
    base: Path,
    raw_path: str,
    errors: list[dict[str, str]],
    location: str,
) -> Path | None:
    try:
        candidate = Path(raw_path)
        if not candidate.is_absolute():
            candidate = base / candidate
        resolved = candidate.resolve()
    except (OSError, RuntimeError, ValueError) as exc:
        _error(errors, "invalid_path", location, str(exc))
        return None
    try:
        resolved.relative_to(root)
    except ValueError:
        _error(
            errors,
            "path_outside_repository",
            location,
            f"resolved path escapes repository root: {resolved}",
        )
        return None
    return resolved


def _require_file(
    path: Path | None,
    errors: list[dict[str, str]],
    location: str,
) -> bool:
    if path is None:
        return False
    if not path.is_file():
        _error(errors, "path_missing", location, f"file does not exist: {path}")
        return False
    return True


def _check_local_locator(
    root: Path,
    base: Path,
    locator: str,
    errors: list[dict[str, str]],
    location: str,
) -> None:
    path_part, separator, fragment = locator.partition("#")
    if not path_part:
        _error(
            errors,
            "invalid_detail_ref",
            location,
            "repository-local locator requires a path before any fragment",
        )
        return
    path = _resolve_inside_root(root, base, path_part, errors, location)
    if not _require_file(path, errors, location):
        return
    if not separator or fragment == "":
        return
    if path.suffix.lower() != ".json":
        _error(
            errors,
            "unsupported_locator_fragment",
            location,
            "fragments are verified only for JSON files",
        )
        return
    pointer = unquote(fragment)
    if not pointer.startswith("/"):
        _error(
            errors,
            "invalid_json_pointer",
            location,
            f"JSON Pointer fragment must start with '/': {fragment}",
        )
        return
    try:
        value: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        _error(errors, "locator_json_load_failed", location, str(exc))
        return
    for raw_token in pointer[1:].split("/"):
        if re.search(r"~(?![01])", raw_token):
            _error(
                errors,
                "invalid_json_pointer",
                location,
                f"invalid escape in JSON Pointer token: {raw_token}",
            )
            return
        token = raw_token.replace("~1", "/").replace("~0", "~")
        if isinstance(value, dict) and token in value:
            value = value[token]
            continue
        if isinstance(value, list):
            try:
                index = int(token)
            except ValueError:
                index = -1
            if 0 <= index < len(value):
                value = value[index]
                continue
        _error(
            errors,
            "json_pointer_not_found",
            location,
            f"pointer token not found: {token}",
        )
        return


def _locator_identity(
    root: Path,
    base: Path,
    locator: str,
    errors: list[dict[str, str]],
    location: str,
) -> tuple[Path, str | None] | None:
    path_part, separator, fragment = locator.partition("#")
    if not path_part:
        _error(
            errors,
            "invalid_detail_ref",
            location,
            "repository-local locator requires a path before any fragment",
        )
        return None
    path = _resolve_inside_root(root, base, path_part, errors, location)
    if path is None:
        return None
    return (path, unquote(fragment) if separator else None)


def _check_unique_definitions(
    source: dict[str, Any],
    errors: list[dict[str, str]],
) -> None:
    collections = (
        "state_profiles",
        "evidence_observations",
        "verification_items",
        "implementation_conformance_items",
        "views",
        "unresolved_items",
    )
    definitions: list[tuple[str, str]] = []
    definitions.append((source["register_id"], "register_id"))
    for collection in collections:
        for index, item in enumerate(source[collection]):
            definitions.append((item["entity_id"], f"{collection}[{index}].entity_id"))
    for index, effect in enumerate(source["evidence_effects"]):
        definitions.append(
            (effect["effect_id"], f"evidence_effects[{index}].effect_id")
        )
    for unresolved_index, unresolved in enumerate(source["unresolved_items"]):
        for obligation_index, obligation in enumerate(
            unresolved["resolution_obligations"]
        ):
            definitions.append(
                (
                    obligation["obligation_id"],
                    (
                        f"unresolved_items[{unresolved_index}].resolution_obligations"
                        f"[{obligation_index}].obligation_id"
                    ),
                )
            )
        for path_index, path in enumerate(unresolved["resolution_paths"]):
            definitions.append(
                (
                    path["path_id"],
                    (
                        f"unresolved_items[{unresolved_index}].resolution_paths"
                        f"[{path_index}].path_id"
                    ),
                )
            )

    counts = Counter(entity_id for entity_id, _ in definitions)
    for entity_id, count in sorted(counts.items()):
        if count > 1:
            locations = [location for value, location in definitions if value == entity_id]
            _error(
                errors,
                "duplicate_entity_id",
                ",".join(locations),
                f"entity_id is defined {count} times: {entity_id}",
            )


def _extract_origin_requirement_ids(text: str) -> set[str]:
    return set(re.findall(r"^###\s+(OR-[0-9]+)\b", text, flags=re.MULTILINE))


def _extract_constitution_subject_ids(text: str) -> set[str]:
    invariant_ids = re.findall(
        r"^\s*-\s+invariant_id:\s*([A-Za-z0-9][A-Za-z0-9._:/-]*)\s*$",
        text,
        flags=re.MULTILINE,
    )
    stage_ids = re.findall(
        r"^\s+stage_ref:\s*[^\n]*・(stage\.[A-Za-z0-9._:/-]+)\s*$",
        text,
        flags=re.MULTILINE,
    )
    return set(invariant_ids) | set(stage_ids)


def _check_resolved_reference_kind(
    reference: dict[str, Any],
    errors: list[dict[str, str]],
    location: str,
) -> None:
    if reference["reference_kind"] != "ref":
        _error(
            errors,
            "non_resolved_reference_kind",
            location,
            f"closed verification references require ref, observed {reference['reference_kind']}",
        )


def _check_reference_id_uniqueness(
    references: list[dict[str, Any]],
    errors: list[dict[str, str]],
    location: str,
) -> None:
    counts = Counter(reference["entity_id"] for reference in references)
    for entity_id, count in sorted(counts.items()):
        if count > 1:
            _error(
                errors,
                "duplicate_reference_entity_id",
                location,
                f"entity_id is referenced {count} times: {entity_id}",
            )


def _check_reference_closure(
    root: Path,
    source_path: Path,
    source: dict[str, Any],
    errors: list[dict[str, str]],
) -> None:
    _check_unique_definitions(source, errors)
    state_profiles_by_id = {
        item["entity_id"]: item for item in source["state_profiles"]
    }
    state_ids = set(state_profiles_by_id)
    evidence_by_id = {
        item["entity_id"]: item for item in source["evidence_observations"]
    }
    evidence_ids = set(evidence_by_id)
    verification_ids = {item["entity_id"] for item in source["verification_items"]}
    conformance_ids = {
        item["entity_id"] for item in source["implementation_conformance_items"]
    }
    view_ids = {item["entity_id"] for item in source["views"]}
    upstream_ids = {
        item["ref"]["entity_id"] for item in source["upstream_sources"]
    }
    upstream_counts = Counter(
        item["ref"]["entity_id"] for item in source["upstream_sources"]
    )
    for entity_id, count in sorted(upstream_counts.items()):
        if count > 1:
            _error(
                errors,
                "duplicate_upstream_entity_id",
                "upstream_sources",
                f"entity_id is declared {count} times: {entity_id}",
            )
    origin_requirement_ids: set[str] = set()
    conformance_subject_ids = set(upstream_ids)
    for index, upstream in enumerate(source["upstream_sources"]):
        _check_resolved_reference_kind(
            upstream["ref"], errors, f"upstream_sources[{index}].ref"
        )
        location = f"upstream_sources[{index}].path"
        path = _resolve_inside_root(
            root,
            source_path.parent,
            upstream["path"],
            errors,
            location,
        )
        if not _require_file(path, errors, location):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            _error(errors, "reference_source_unreadable", location, str(exc))
            continue
        if upstream["authority"] == "purpose":
            origin_requirement_ids.update(_extract_origin_requirement_ids(text))
        if upstream["authority"] == "normative_model":
            conformance_subject_ids.update(_extract_constitution_subject_ids(text))

    auditable_items = source["verification_items"] + source[
        "implementation_conformance_items"
    ]
    auditable_item_by_id = {
        item["entity_id"]: item for item in auditable_items
    }
    auditable_item_ids = verification_ids | conformance_ids
    evidence_effect_ids = [
        effect["effect_id"] for effect in source["evidence_effects"]
    ]
    for effect_id, count in sorted(Counter(evidence_effect_ids).items()):
        if count > 1:
            _error(
                errors,
                "duplicate_evidence_effect_id",
                "evidence_effects",
                f"effect_id is defined {count} times: {effect_id}",
            )
    defined_non_effect_ids = (
        state_ids
        | evidence_ids
        | verification_ids
        | conformance_ids
        | view_ids
        | {item["entity_id"] for item in source["unresolved_items"]}
    )
    for effect_id in sorted(set(evidence_effect_ids) & defined_non_effect_ids):
        _error(
            errors,
            "duplicate_entity_id",
            "evidence_effects",
            f"effect_id collides with another entity: {effect_id}",
        )
    evidence_effects_by_item: dict[str, list[dict[str, Any]]] = {}
    for effect_index, effect in enumerate(source["evidence_effects"]):
        location = f"evidence_effects[{effect_index}]"
        _check_reference_id_uniqueness(
            effect["item_refs"], errors, f"{location}.item_refs"
        )
        _check_resolved_reference_kind(
            effect["evidence_ref"], errors, f"{location}.evidence_ref"
        )
        evidence_id = effect["evidence_ref"]["entity_id"]
        if evidence_id not in evidence_ids:
            _error(
                errors,
                "unresolved_evidence_effect_evidence_ref",
                f"{location}.evidence_ref",
                evidence_id,
            )
        for item_index, item_reference in enumerate(effect["item_refs"]):
            item_location = f"{location}.item_refs[{item_index}]"
            _check_resolved_reference_kind(item_reference, errors, item_location)
            item_id = item_reference["entity_id"]
            if item_id not in auditable_item_ids:
                _error(
                    errors,
                    "unresolved_evidence_effect_item_ref",
                    item_location,
                    item_id,
                )
                continue
            lifecycle_surfaces = set(effect.get("lifecycle_surfaces", []))
            if lifecycle_surfaces:
                target_item = auditable_item_by_id[item_id]
                declared_assessments = target_item.get(
                    "lifecycle_surface_assessments"
                )
                declared_surfaces = {
                    assessment["surface"]
                    for assessment in (declared_assessments or [])
                }
                if not declared_assessments or not lifecycle_surfaces.issubset(
                    declared_surfaces
                ):
                    _error(
                        errors,
                        "evidence_effect_invalid_lifecycle_surface_scope",
                        f"{location}.lifecycle_surfaces",
                        (
                            f"{sorted(lifecycle_surfaces)!r} is not a subset of "
                            f"the target item's assessments {sorted(declared_surfaces)!r}"
                        ),
                    )
            evidence_effects_by_item.setdefault(item_id, []).append(effect)

    for item in auditable_items:
        entity_id = item["entity_id"]
        _check_reference_id_uniqueness(
            item["origin_requirement_refs"],
            errors,
            f"{entity_id}.origin_requirement_refs",
        )
        for index, origin_ref in enumerate(item["origin_requirement_refs"]):
            location = f"{entity_id}.origin_requirement_refs[{index}]"
            _check_resolved_reference_kind(origin_ref, errors, location)
            origin_id = origin_ref["entity_id"]
            if origin_id not in origin_requirement_ids:
                _error(errors, "unresolved_origin_requirement_ref", location, origin_id)
        state_ref = item["state_profile_ref"]["entity_id"]
        _check_resolved_reference_kind(
            item["state_profile_ref"], errors, f"{entity_id}.state_profile_ref"
        )
        if state_ref not in state_ids:
            _error(
                errors,
                "unresolved_state_profile_ref",
                f"{entity_id}.state_profile_ref",
                state_ref,
            )
        for field in ("evidence_refs", "counterevidence_refs"):
            _check_reference_id_uniqueness(
                item[field], errors, f"{entity_id}.{field}"
            )
            for index, reference in enumerate(item[field]):
                ref_id = reference["entity_id"]
                _check_resolved_reference_kind(
                    reference, errors, f"{entity_id}.{field}[{index}]"
                )
                if ref_id not in evidence_ids:
                    _error(
                        errors,
                        "unresolved_evidence_ref",
                        f"{entity_id}.{field}[{index}]",
                        ref_id,
                    )
        state_profile = state_profiles_by_id.get(state_ref)
        if state_profile is not None:
            assurance = state_profile["state"]["assurance"]
            challenge_requires_evidence = (
                assurance["outcome"] == "refuted"
                or assurance["challenge"] in {"open", "conflict"}
            )
            typed_effects = evidence_effects_by_item.get(entity_id, [])
            positive_effects = [
                effect
                for effect in typed_effects
                if effect["effect"] in {"supports", "contextualizes"}
            ]
            negative_effects = [
                effect
                for effect in typed_effects
                if effect["effect"] in {"refutes", "challenges"}
            ]
            declared_evidence_ids = {
                reference["entity_id"] for reference in item["evidence_refs"]
            }
            typed_evidence_ids = {
                effect["evidence_ref"]["entity_id"] for effect in positive_effects
            }
            if declared_evidence_ids != typed_evidence_ids:
                _error(
                    errors,
                    "evidence_effect_mismatch",
                    f"{entity_id}.evidence_refs",
                    (
                        f"declared={sorted(declared_evidence_ids)!r}, "
                        f"typed={sorted(typed_evidence_ids)!r}"
                    ),
                )
            declared_counter_ids = {
                reference["entity_id"] for reference in item["counterevidence_refs"]
            }
            typed_counter_ids = {
                effect["evidence_ref"]["entity_id"] for effect in negative_effects
            }
            if declared_counter_ids != typed_counter_ids:
                _error(
                    errors,
                    "counterevidence_effect_mismatch",
                    f"{entity_id}.counterevidence_refs",
                    (
                        f"declared={sorted(declared_counter_ids)!r}, "
                        f"typed={sorted(typed_counter_ids)!r}"
                    ),
                )
            required_support_dimensions: set[str] = set()
            if state_profile["state"]["implementation"] == "implemented":
                required_support_dimensions.add("implementation")
            if state_profile["state"]["verification"] == "passed":
                required_support_dimensions.add("verification")
            if state_profile["state"]["validation"] == "supported_in_context":
                required_support_dimensions.add("validation")
            if assurance["outcome"] == "satisfied":
                required_support_dimensions.add("assurance")
            supported_dimensions = {
                dimension
                for effect in positive_effects
                if effect["effect"] == "supports"
                and not effect.get("lifecycle_surfaces")
                for dimension in effect["claim_dimensions"]
            }
            missing_support_dimensions = (
                required_support_dimensions - supported_dimensions
            )
            if missing_support_dimensions:
                _error(
                    errors,
                    "missing_supporting_evidence_effect_dimension",
                    f"{entity_id}.evidence_refs",
                    (
                        "state requires typed support for dimensions "
                        f"{sorted(missing_support_dimensions)!r}"
                    ),
                )
            negative_state_dimensions: set[str] = set()
            if state_profile["state"]["implementation"] == "missing":
                negative_state_dimensions.add("implementation")
            if state_profile["state"]["verification"] in {"failed", "invalid"}:
                negative_state_dimensions.add("verification")
            if state_profile["state"]["validation"] == "refuted_in_context":
                negative_state_dimensions.add("validation")
            if negative_state_dimensions and assurance["outcome"] == "satisfied":
                _error(
                    errors,
                    "state_axis_assurance_conflict",
                    f"{entity_id}.state_profile_ref",
                    (
                        "satisfied assurance conflicts with negative state axes "
                        f"{sorted(negative_state_dimensions)!r}"
                    ),
                )
            negative_effect_dimensions = {
                dimension
                for effect in negative_effects
                for dimension in effect["claim_dimensions"]
            }
            if negative_state_dimensions and not negative_state_dimensions.issubset(
                negative_effect_dimensions
            ):
                _error(
                    errors,
                    "negative_state_missing_evidence_effect_dimension",
                    f"{entity_id}.counterevidence_refs",
                    (
                        "negative state axes lack typed negative effects for "
                        f"{sorted(negative_state_dimensions - negative_effect_dimensions)!r}"
                    ),
                )
            conflicting_dimensions = negative_state_dimensions & supported_dimensions
            if conflicting_dimensions and assurance["challenge"] != "conflict":
                _error(
                    errors,
                    "state_axis_evidence_polarity_conflict",
                    f"{entity_id}.state_profile_ref",
                    (
                        "negative state axes conflict with supporting effects for "
                        f"{sorted(conflicting_dimensions)!r} without "
                        "assurance.challenge=conflict"
                    ),
                )
            has_refuting_effect = any(
                effect["effect"] == "refutes" for effect in negative_effects
            )
            has_challenging_effect = any(
                effect["effect"] == "challenges" for effect in negative_effects
            )
            if has_challenging_effect and assurance["challenge"] == "none":
                _error(
                    errors,
                    "challenge_effect_state_conflict",
                    f"{entity_id}.state_profile_ref",
                    "a challenges effect exists while assurance.challenge is none",
                )
            if has_refuting_effect and assurance["outcome"] != "refuted":
                _error(
                    errors,
                    "challenge_effect_state_conflict",
                    f"{entity_id}.state_profile_ref",
                    "a refutes effect requires assurance.outcome=refuted",
                )
            if assurance["outcome"] == "refuted" and not has_refuting_effect:
                _error(
                    errors,
                    "missing_refuting_evidence_effect",
                    f"{entity_id}.counterevidence_refs",
                    (
                        f"state profile {state_ref} requires a located refutes effect"
                    ),
                )
            if challenge_requires_evidence and not negative_effects:
                _error(
                    errors,
                    "missing_challenge_evidence_effect",
                    f"{entity_id}.counterevidence_refs",
                    f"state profile {state_ref} requires a typed challenge evidence effect",
                )
            if state_profile["state"]["freshness"] == "current":
                for evidence_reference in (
                    item["evidence_refs"] + item["counterevidence_refs"]
                ):
                    observation = evidence_by_id.get(evidence_reference["entity_id"])
                    if observation is None:
                        continue
                    if (
                        observation["freshness"] != "current"
                        or observation["subject_binding"]["status"] != "bound"
                    ):
                        _error(
                            errors,
                            "current_state_uses_noncurrent_evidence",
                            f"{entity_id}.state_profile_ref",
                            (
                                f"current state {state_ref} references noncurrent or "
                                f"unbound evidence {observation['entity_id']}"
                            ),
                        )

    for item in source["verification_items"]:
        assessments = item.get("lifecycle_surface_assessments")
        if assessments is not None:
            surface_counts = Counter(
                assessment["surface"] for assessment in assessments
            )
            for surface, count in sorted(surface_counts.items()):
                if count > 1:
                    _error(
                        errors,
                        "duplicate_lifecycle_surface_assessment",
                        f"{item['entity_id']}.lifecycle_surface_assessments",
                        f"surface is assessed {count} times: {surface}",
                    )
            declared_surfaces = set(item["lifecycle_surfaces"])
            assessed_surfaces = set(surface_counts)
            if declared_surfaces != assessed_surfaces:
                _error(
                    errors,
                    "lifecycle_surface_assessment_coverage_mismatch",
                    f"{item['entity_id']}.lifecycle_surface_assessments",
                    (
                        f"declared={sorted(declared_surfaces)!r}, "
                        f"assessed={sorted(assessed_surfaces)!r}"
                    ),
                )
            for assessment_index, assessment in enumerate(assessments):
                location = (
                    f"{item['entity_id']}.lifecycle_surface_assessments"
                    f"[{assessment_index}]"
                )
                state_reference = assessment["state_profile_ref"]
                _check_resolved_reference_kind(
                    state_reference, errors, f"{location}.state_profile_ref"
                )
                if state_reference["entity_id"] not in state_ids:
                    _error(
                        errors,
                        "unresolved_state_profile_ref",
                        f"{location}.state_profile_ref",
                        state_reference["entity_id"],
                    )
                _check_reference_id_uniqueness(
                    assessment["evidence_refs"], errors, f"{location}.evidence_refs"
                )
                for evidence_index, evidence_reference in enumerate(
                    assessment["evidence_refs"]
                ):
                    evidence_location = f"{location}.evidence_refs[{evidence_index}]"
                    _check_resolved_reference_kind(
                        evidence_reference, errors, evidence_location
                    )
                    if evidence_reference["entity_id"] not in evidence_ids:
                        _error(
                            errors,
                            "unresolved_evidence_ref",
                            evidence_location,
                            evidence_reference["entity_id"],
                        )
                assessment_state = state_profiles_by_id.get(
                    state_reference["entity_id"]
                )
                parent_evidence_ids = {
                    reference["entity_id"] for reference in item["evidence_refs"]
                }
                assessment_evidence_ids = {
                    reference["entity_id"]
                    for reference in assessment["evidence_refs"]
                }
                undeclared_assessment_evidence = (
                    assessment_evidence_ids - parent_evidence_ids
                )
                if undeclared_assessment_evidence:
                    _error(
                        errors,
                        "lifecycle_assessment_evidence_not_declared_by_item",
                        f"{location}.evidence_refs",
                        (
                            "assessment evidence is absent from the parent item: "
                            f"{sorted(undeclared_assessment_evidence)!r}"
                        ),
                    )
                if assessment_state is not None:
                    assessment_assurance = assessment_state["state"]["assurance"]
                    required_dimensions: set[str] = set()
                    if assessment_state["state"]["implementation"] == "implemented":
                        required_dimensions.add("implementation")
                    if assessment_state["state"]["verification"] == "passed":
                        required_dimensions.add("verification")
                    if (
                        assessment_state["state"]["validation"]
                        == "supported_in_context"
                    ):
                        required_dimensions.add("validation")
                    if assessment_assurance["outcome"] == "satisfied":
                        required_dimensions.add("assurance")
                    supported_dimensions = {
                        dimension
                        for effect in evidence_effects_by_item.get(
                            item["entity_id"], []
                        )
                        if effect["effect"] == "supports"
                        and effect["evidence_ref"]["entity_id"]
                        in assessment_evidence_ids
                        and assessment["surface"]
                        in effect.get("lifecycle_surfaces", [])
                        for dimension in effect["claim_dimensions"]
                    }
                    missing_dimensions = required_dimensions - supported_dimensions
                    if missing_dimensions:
                        _error(
                            errors,
                            "missing_lifecycle_assessment_support_dimension",
                            f"{location}.evidence_refs",
                            (
                                "assessment state requires typed support for "
                                f"{sorted(missing_dimensions)!r}"
                            ),
                        )
                    negative_dimensions: set[str] = set()
                    if assessment_state["state"]["implementation"] == "missing":
                        negative_dimensions.add("implementation")
                    if assessment_state["state"]["verification"] in {
                        "failed",
                        "invalid",
                    }:
                        negative_dimensions.add("verification")
                    if (
                        assessment_state["state"]["validation"]
                        == "refuted_in_context"
                    ):
                        negative_dimensions.add("validation")
                    negative_effect_dimensions = {
                        dimension
                        for effect in evidence_effects_by_item.get(
                            item["entity_id"], []
                        )
                        if effect["effect"] in {"refutes", "challenges"}
                        and assessment["surface"]
                        in effect.get("lifecycle_surfaces", [])
                        for dimension in effect["claim_dimensions"]
                    }
                    missing_negative_dimensions = (
                        negative_dimensions - negative_effect_dimensions
                    )
                    if missing_negative_dimensions:
                        _error(
                            errors,
                            "missing_lifecycle_assessment_negative_dimension",
                            f"{location}.state_profile_ref",
                            (
                                "negative assessment state requires a scoped typed "
                                "negative effect for "
                                f"{sorted(missing_negative_dimensions)!r}"
                            ),
                        )
                    conflicting_dimensions = (
                        negative_dimensions & supported_dimensions
                    )
                    if (
                        conflicting_dimensions
                        and assessment_assurance["challenge"] != "conflict"
                    ):
                        _error(
                            errors,
                            "lifecycle_assessment_evidence_polarity_conflict",
                            f"{location}.state_profile_ref",
                            (
                                "negative assessment state conflicts with scoped "
                                "supporting effects for "
                                f"{sorted(conflicting_dimensions)!r}"
                            ),
                        )
                if (
                    assessment_state is not None
                    and assessment_state["state"]["freshness"] == "current"
                ):
                    for evidence_reference in assessment["evidence_refs"]:
                        observation = evidence_by_id.get(
                            evidence_reference["entity_id"]
                        )
                        if observation is None:
                            continue
                        if (
                            observation["freshness"] != "current"
                            or observation["subject_binding"]["status"] != "bound"
                        ):
                            _error(
                                errors,
                                "current_state_uses_noncurrent_evidence",
                                f"{location}.state_profile_ref",
                                (
                                    f"current state {state_reference['entity_id']} "
                                    f"references noncurrent or unbound evidence "
                                    f"{observation['entity_id']}"
                                ),
                            )
        for index, basis in enumerate(item["knowledge_basis"]):
            ref_id = basis["source_ref"]["entity_id"]
            _check_resolved_reference_kind(
                basis["source_ref"],
                errors,
                f"{item['entity_id']}.knowledge_basis[{index}].source_ref",
            )
            if ref_id not in upstream_ids:
                _error(
                    errors,
                    "unresolved_knowledge_source_ref",
                    f"{item['entity_id']}.knowledge_basis[{index}]",
                    ref_id,
                )

    for item in source["implementation_conformance_items"]:
        reference = item["subject_ref"]
        location = f"{item['entity_id']}.subject_ref"
        _check_resolved_reference_kind(reference, errors, location)
        subject_id = reference["entity_id"]
        if subject_id not in conformance_subject_ids:
            _error(errors, "unresolved_conformance_subject_ref", location, subject_id)
        conformance_state = state_profiles_by_id.get(
            item["state_profile_ref"]["entity_id"]
        )
        if conformance_state is not None and (
            conformance_state["state"]["freshness"] == "current"
            or conformance_state["state"]["assurance"]["finality"] == "terminal"
        ):
            _error(
                errors,
                "conformance_current_without_reverification_contract",
                f"{item['entity_id']}.state_profile_ref",
                (
                    "implementation conformance items cannot be current or terminal "
                    "until their contract includes explicit reverification"
                ),
            )

    item_ids = auditable_item_ids
    for view in source["views"]:
        _check_reference_id_uniqueness(
            view["item_refs"], errors, f"{view['entity_id']}.item_refs"
        )
        for index, reference in enumerate(view["item_refs"]):
            ref_id = reference["entity_id"]
            _check_resolved_reference_kind(
                reference, errors, f"{view['entity_id']}.item_refs[{index}]"
            )
            if ref_id not in item_ids:
                _error(
                    errors,
                    "unresolved_view_item_ref",
                    f"{view['entity_id']}.item_refs[{index}]",
                    ref_id,
                )

    state_by_id = {
        profile["entity_id"]: profile["state"] for profile in source["state_profiles"]
    }
    auditable_by_id = {item["entity_id"]: item for item in auditable_items}
    view_items_by_id = {
        view["entity_id"]: {
            reference["entity_id"] for reference in view["item_refs"]
        }
        for view in source["views"]
    }
    obligations = [
        obligation
        for unresolved in source["unresolved_items"]
        for obligation in unresolved["resolution_obligations"]
    ]
    obligation_counts = Counter(
        obligation["obligation_id"] for obligation in obligations
    )
    for obligation_id, count in sorted(obligation_counts.items()):
        if count > 1:
            _error(
                errors,
                "duplicate_obligation_id",
                "unresolved_items.resolution_obligations",
                f"obligation_id is defined {count} times: {obligation_id}",
            )
    obligation_ids = set(obligation_counts)
    already_defined_ids = (
        state_ids | evidence_ids | verification_ids | conformance_ids | view_ids
    )
    for obligation_id in sorted(obligation_ids & already_defined_ids):
        _error(
            errors,
            "duplicate_entity_id",
            "unresolved_items.resolution_obligations",
            f"obligation_id collides with another entity: {obligation_id}",
        )
    obligation_graph: dict[str, set[str]] = {
        obligation_id: set() for obligation_id in obligation_ids
    }
    for obligation in obligations:
        obligation_id = obligation["obligation_id"]
        references = obligation["precondition_obligation_refs"]
        _check_reference_id_uniqueness(
            references,
            errors,
            f"{obligation_id}.precondition_obligation_refs",
        )
        for reference_index, reference in enumerate(references):
            location = (
                f"{obligation_id}.precondition_obligation_refs[{reference_index}]"
            )
            _check_resolved_reference_kind(reference, errors, location)
            prerequisite_id = reference["entity_id"]
            if prerequisite_id not in obligation_ids:
                _error(
                    errors,
                    "unresolved_obligation_precondition_ref",
                    location,
                    prerequisite_id,
                )
                continue
            if prerequisite_id == obligation_id:
                _error(
                    errors,
                    "self_referential_obligation_precondition",
                    location,
                    prerequisite_id,
                )
                continue
            obligation_graph[obligation_id].add(prerequisite_id)

    visited_obligations: set[str] = set()
    visiting_obligations: set[str] = set()

    def visit_obligation(obligation_id: str) -> None:
        if obligation_id in visited_obligations:
            return
        if obligation_id in visiting_obligations:
            _error(
                errors,
                "cyclic_obligation_preconditions",
                "unresolved_items.resolution_obligations",
                obligation_id,
            )
            return
        visiting_obligations.add(obligation_id)
        for prerequisite_id in sorted(obligation_graph[obligation_id]):
            visit_obligation(prerequisite_id)
        visiting_obligations.remove(obligation_id)
        visited_obligations.add(obligation_id)

    for obligation_id in sorted(obligation_graph):
        visit_obligation(obligation_id)

    obligation_by_id = {
        obligation["obligation_id"]: obligation for obligation in obligations
    }
    for unresolved_index, unresolved in enumerate(source["unresolved_items"]):
        local_obligation_ids = {
            obligation["obligation_id"]
            for obligation in unresolved["resolution_obligations"]
        }
        covered_obligation_ids: set[str] = set()
        for path_index, path in enumerate(unresolved["resolution_paths"]):
            location = (
                f"unresolved_items[{unresolved_index}].resolution_paths[{path_index}]"
            )
            references = path["required_obligation_refs"]
            _check_reference_id_uniqueness(
                references, errors, f"{location}.required_obligation_refs"
            )
            path_obligation_ids = {
                reference["entity_id"] for reference in references
            }
            for reference_index, reference in enumerate(references):
                reference_location = (
                    f"{location}.required_obligation_refs[{reference_index}]"
                )
                _check_resolved_reference_kind(
                    reference, errors, reference_location
                )
                obligation_id = reference["entity_id"]
                if obligation_id not in local_obligation_ids:
                    _error(
                        errors,
                        "unresolved_resolution_path_obligation_ref",
                        reference_location,
                        (
                            f"{obligation_id} is not defined by "
                            f"{unresolved['entity_id']}"
                        ),
                    )
                    continue
                covered_obligation_ids.add(obligation_id)
            for obligation_id in sorted(path_obligation_ids & local_obligation_ids):
                obligation = obligation_by_id[obligation_id]
                local_preconditions = {
                    reference["entity_id"]
                    for reference in obligation["precondition_obligation_refs"]
                    if reference["entity_id"] in local_obligation_ids
                }
                missing_preconditions = local_preconditions - path_obligation_ids
                if missing_preconditions:
                    _error(
                        errors,
                        "resolution_path_missing_local_precondition",
                        f"{location}.required_obligation_refs",
                        (
                            f"{obligation_id} requires local prerequisites "
                            f"{sorted(missing_preconditions)!r} in the same path"
                        ),
                    )
        missing_coverage = local_obligation_ids - covered_obligation_ids
        if missing_coverage:
            _error(
                errors,
                "resolution_path_missing_obligation_coverage",
                f"{unresolved['entity_id']}.resolution_paths",
                f"uncovered obligations: {sorted(missing_coverage)!r}",
            )

    resolution_path_ids = {
        path["path_id"]
        for unresolved in source["unresolved_items"]
        for path in unresolved["resolution_paths"]
    }
    disallowed_upstream_collisions = upstream_ids & (
        {source["register_id"]}
        | state_ids
        | verification_ids
        | conformance_ids
        | view_ids
        | {item["entity_id"] for item in source["unresolved_items"]}
        | set(evidence_effect_ids)
        | obligation_ids
        | resolution_path_ids
    )
    for entity_id in sorted(disallowed_upstream_collisions):
        _error(
            errors,
            "upstream_identity_collides_with_local_definition",
            "upstream_sources",
            entity_id,
        )

    unresolved_targets = item_ids | view_ids
    for item in source["unresolved_items"]:
        _check_reference_id_uniqueness(
            item["affected_entity_refs"],
            errors,
            f"{item['entity_id']}.affected_entity_refs",
        )
        for index, reference in enumerate(item["affected_entity_refs"]):
            ref_id = reference["entity_id"]
            _check_resolved_reference_kind(
                reference,
                errors,
                f"{item['entity_id']}.affected_entity_refs[{index}]",
            )
            if ref_id not in unresolved_targets:
                _error(
                    errors,
                    "unresolved_affected_entity_ref",
                    f"{item['entity_id']}.affected_entity_refs[{index}]",
                    ref_id,
                )
        claim_effect = item["claim_effect"]
        affected_item_ids: set[str] = set()
        for reference in item["affected_entity_refs"]:
            affected_id = reference["entity_id"]
            if affected_id in auditable_by_id:
                affected_item_ids.add(affected_id)
            affected_item_ids.update(view_items_by_id.get(affected_id, set()))
        if claim_effect != "does_not_block_claim" and not affected_item_ids:
            _error(
                errors,
                "blocking_effect_without_stateful_target",
                f"{item['entity_id']}.affected_entity_refs",
                "a blocking claim effect requires at least one affected verification or conformance item",
            )
        for affected_id in sorted(affected_item_ids):
            affected_item = auditable_by_id[affected_id]
            state_id = affected_item["state_profile_ref"]["entity_id"]
            state = state_by_id.get(state_id)
            if state is None:
                continue
            assurance = state["assurance"]
            if (
                claim_effect in {"partially_blocks_claim", "blocks_claim"}
                and assurance["finality"] == "terminal"
                and assurance["outcome"] == "satisfied"
            ):
                _error(
                    errors,
                    "claim_effect_state_conflict",
                    f"{item['entity_id']}.claim_effect",
                    (
                        f"{claim_effect} conflicts with terminal satisfied "
                        f"assurance on {affected_id}"
                    ),
                )
            if (
                claim_effect == "blocks_claim"
                and assurance["outcome"] == "satisfied"
            ):
                _error(
                    errors,
                    "claim_effect_state_conflict",
                    f"{item['entity_id']}.claim_effect",
                    f"blocks_claim conflicts with satisfied assurance on {affected_id}",
                )


def _check_paths_and_digests(
    root: Path,
    source_path: Path,
    source: dict[str, Any],
    errors: list[dict[str, str]],
) -> None:
    base = source_path.parent
    upstream_by_id = {
        upstream["ref"]["entity_id"]: upstream
        for upstream in source["upstream_sources"]
    }
    upstream_paths_by_id: dict[str, Path] = {}
    for index, upstream in enumerate(source["upstream_sources"]):
        location = f"upstream_sources[{index}].path"
        path = _resolve_inside_root(root, base, upstream["path"], errors, location)
        if path is not None:
            upstream_paths_by_id[upstream["ref"]["entity_id"]] = path
        if not _require_file(path, errors, location):
            continue
        version_or_digest = upstream["version_or_digest"]
        digest_prefixes = ("sha256", "sha512", "blake3", "other")
        algorithm, separator, expected = version_or_digest.partition(":")
        if separator and algorithm in digest_prefixes:
            actual = _file_digest(path, algorithm)
            if actual is None:
                _error(
                    errors,
                    "unsupported_digest_algorithm",
                    location,
                    algorithm,
                )
            elif actual != expected:
                _error(
                    errors,
                    "upstream_digest_mismatch",
                    location,
                    f"expected {expected}, observed {actual}",
                )

    for index, evidence in enumerate(source["evidence_observations"]):
        location = f"evidence_observations[{index}].source_path"
        path = _resolve_inside_root(
            root,
            base,
            evidence["source_path"],
            errors,
            location,
        )
        shared_upstream = upstream_by_id.get(evidence["entity_id"])
        if shared_upstream is not None:
            upstream_path = upstream_paths_by_id.get(evidence["entity_id"])
            if path is not None and upstream_path is not None and path != upstream_path:
                _error(
                    errors,
                    "shared_identity_path_mismatch",
                    location,
                    (
                        f"evidence {evidence['entity_id']} resolves to {path}, "
                        f"but its upstream reference resolves to {upstream_path}"
                    ),
                )
            upstream_algorithm, separator, upstream_value = shared_upstream[
                "version_or_digest"
            ].partition(":")
            evidence_digest = evidence["content_digest"]
            if (
                not separator
                or upstream_algorithm != evidence_digest["algorithm"]
                or upstream_value.lower() != evidence_digest["value"].lower()
            ):
                _error(
                    errors,
                    "shared_identity_digest_mismatch",
                    f"evidence_observations[{index}].content_digest",
                    (
                        f"evidence {evidence['entity_id']} and its upstream "
                        "reference declare different content identities"
                    ),
                )
        if not _require_file(path, errors, location):
            continue
        content_digest = evidence.get("content_digest")
        if content_digest:
            algorithm = content_digest["algorithm"]
            expected = content_digest["value"].lower()
            actual = _file_digest(path, algorithm)
            if actual is None:
                _error(
                    errors,
                    "unsupported_digest_algorithm",
                    location,
                    algorithm,
                )
            elif actual != expected:
                _error(
                    errors,
                    "evidence_digest_mismatch",
                    location,
                    f"expected {expected}, observed {actual}",
                )

        subject_binding = evidence["subject_binding"]
        binding_locator_counts = Counter(
            binding["subject_locator"]
            for binding in subject_binding["digest_bindings"]
        )
        for subject_locator, count in sorted(binding_locator_counts.items()):
            if count > 1:
                _error(
                    errors,
                    "duplicate_subject_digest_binding",
                    f"evidence_observations[{index}].subject_binding.digest_bindings",
                    f"subject_locator is bound {count} times: {subject_locator}",
                )
        if subject_binding["status"] == "bound":
            locator_set = set(subject_binding["subject_locators"])
            binding_locator_set = {
                binding["subject_locator"]
                for binding in subject_binding["digest_bindings"]
            }
            if locator_set != binding_locator_set:
                _error(
                    errors,
                    "incomplete_subject_digest_coverage",
                    f"evidence_observations[{index}].subject_binding",
                    (
                        f"subject_locators={sorted(locator_set)!r}, "
                        f"digest_binding_locators={sorted(binding_locator_set)!r}"
                    ),
                )
        for binding_index, binding in enumerate(subject_binding["digest_bindings"]):
            binding_location = (
                f"evidence_observations[{index}].subject_binding."
                f"digest_bindings[{binding_index}]"
            )
            subject_path = _resolve_inside_root(
                root,
                base,
                binding["subject_locator"],
                errors,
                f"{binding_location}.subject_locator",
            )
            if not _require_file(
                subject_path, errors, f"{binding_location}.subject_locator"
            ):
                continue
            algorithm = binding["digest"]["algorithm"]
            expected = binding["digest"]["value"].lower()
            actual = _file_digest(subject_path, algorithm)
            if actual is None:
                _error(
                    errors,
                    "unsupported_digest_algorithm",
                    f"{binding_location}.digest",
                    algorithm,
                )
            elif actual != expected:
                _error(
                    errors,
                    "subject_digest_mismatch",
                    f"{binding_location}.digest",
                    f"expected {expected}, observed {actual}",
                )

        manifest_ref = subject_binding["manifest_ref"]
        manifest_digest = subject_binding["manifest_digest"]
        manifest_location = (
            f"evidence_observations[{index}].subject_binding.manifest_ref"
        )
        manifest_path: Path | None = None
        if (manifest_ref is None) != (manifest_digest is None):
            _error(
                errors,
                "incomplete_manifest_binding",
                manifest_location,
                "manifest_ref and manifest_digest must be present or absent together",
            )
        if manifest_ref is not None:
            manifest_path = _resolve_inside_root(
                root, base, manifest_ref, errors, manifest_location
            )
            if _require_file(manifest_path, errors, manifest_location):
                if manifest_digest is not None:
                    actual_manifest_digest = _file_digest(
                        manifest_path, manifest_digest["algorithm"]
                    )
                    if actual_manifest_digest is None:
                        _error(
                            errors,
                            "unsupported_digest_algorithm",
                            manifest_location,
                            manifest_digest["algorithm"],
                        )
                    elif actual_manifest_digest != manifest_digest["value"].lower():
                        _error(
                            errors,
                            "manifest_digest_mismatch",
                            manifest_location,
                            (
                                f"expected {manifest_digest['value'].lower()}, "
                                f"observed {actual_manifest_digest}"
                            ),
                        )

        if (
            evidence["evidence_kind"] == "test_execution"
            and subject_binding["status"] == "bound"
            and manifest_path is not None
            and manifest_path.is_file()
        ):
            manifest = _load_json(manifest_path, errors, manifest_location)
            if manifest is not None:
                required_manifest_keys = {
                    "schema_version",
                    "closed_world",
                    "subjects",
                    "limitations",
                }
                if set(manifest) != required_manifest_keys:
                    _error(
                        errors,
                        "subject_manifest_shape_invalid",
                        manifest_location,
                        (
                            f"expected keys {sorted(required_manifest_keys)!r}, "
                            f"observed {sorted(manifest)!r}"
                        ),
                    )
                if manifest.get("schema_version") != SUBJECT_MANIFEST_VERSION:
                    _error(
                        errors,
                        "subject_manifest_version_mismatch",
                        manifest_location,
                        repr(manifest.get("schema_version")),
                    )
                if manifest.get("closed_world") is not True:
                    _error(
                        errors,
                        "subject_manifest_not_closed",
                        manifest_location,
                        "bound test evidence requires closed_world=true",
                    )
                manifest_subjects = manifest.get("subjects")
                valid_manifest_subjects = isinstance(manifest_subjects, list) and bool(
                    manifest_subjects
                )
                manifest_binding_map: dict[str, tuple[str, str]] = {}
                if valid_manifest_subjects:
                    for subject_index, subject in enumerate(manifest_subjects):
                        subject_location = (
                            f"{manifest_location}.subjects[{subject_index}]"
                        )
                        if not isinstance(subject, dict) or set(subject) != {
                            "subject_locator",
                            "digest",
                        }:
                            valid_manifest_subjects = False
                            _error(
                                errors,
                                "subject_manifest_entry_invalid",
                                subject_location,
                                "entry requires only subject_locator and digest",
                            )
                            continue
                        locator = subject.get("subject_locator")
                        digest = subject.get("digest")
                        if (
                            not isinstance(locator, str)
                            or not locator
                            or not isinstance(digest, dict)
                            or set(digest) != {"algorithm", "value"}
                            or digest.get("algorithm") != "sha256"
                            or not isinstance(digest.get("value"), str)
                            or re.fullmatch(r"[0-9a-fA-F]{64}", digest["value"])
                            is None
                        ):
                            valid_manifest_subjects = False
                            _error(
                                errors,
                                "subject_manifest_entry_invalid",
                                subject_location,
                                "entry requires a locator and SHA-256 digest",
                            )
                            continue
                        if locator in manifest_binding_map:
                            valid_manifest_subjects = False
                            _error(
                                errors,
                                "subject_manifest_duplicate_locator",
                                subject_location,
                                locator,
                            )
                            continue
                        manifest_binding_map[locator] = (
                            digest["algorithm"],
                            digest["value"].lower(),
                        )
                else:
                    _error(
                        errors,
                        "subject_manifest_subjects_invalid",
                        manifest_location,
                        "subjects must be a non-empty array",
                    )
                limitations = manifest.get("limitations")
                if (
                    not isinstance(limitations, list)
                    or not limitations
                    or any(not isinstance(value, str) or not value for value in limitations)
                ):
                    _error(
                        errors,
                        "subject_manifest_limitations_invalid",
                        manifest_location,
                        "limitations must be a non-empty string array",
                    )
                if valid_manifest_subjects:
                    declared_binding_map = {
                        binding["subject_locator"]: (
                            binding["digest"]["algorithm"],
                            binding["digest"]["value"].lower(),
                        )
                        for binding in subject_binding["digest_bindings"]
                    }
                    if manifest_binding_map != declared_binding_map:
                        _error(
                            errors,
                            "subject_manifest_binding_mismatch",
                            manifest_location,
                            "manifest subjects differ from subject_binding.digest_bindings",
                        )
                    if set(manifest_binding_map) != set(
                        subject_binding["subject_locators"]
                    ):
                        _error(
                            errors,
                            "subject_manifest_denominator_mismatch",
                            manifest_location,
                            "manifest subjects differ from subject_locators",
                        )
                    evidence_source_path = path
                    non_report_subjects = []
                    for locator in manifest_binding_map:
                        subject_path = _resolve_inside_root(
                            root, base, locator, errors, manifest_location
                        )
                        if (
                            subject_path is not None
                            and subject_path not in {evidence_source_path, manifest_path}
                        ):
                            non_report_subjects.append(subject_path)
                    if not non_report_subjects:
                        _error(
                            errors,
                            "test_execution_subject_is_only_evidence_record",
                            manifest_location,
                            (
                                "bound test evidence requires at least one tested "
                                "subject distinct from the evidence report and manifest"
                            ),
                        )

        elevated_basis = evidence["elevated_trust_basis"]
        for basis_field in (
            "independence_basis_ref",
            "signature_or_attestation_ref",
            "formal_verification_result_ref",
        ):
            basis_ref = elevated_basis[basis_field]
            if basis_ref is not None:
                _check_local_locator(
                    root,
                    base,
                    basis_ref,
                    errors,
                    (
                        f"evidence_observations[{index}].elevated_trust_basis."
                        f"{basis_field}"
                    ),
                )

        source_identity = _locator_identity(
            root,
            base,
            evidence["source_path"],
            errors,
            f"evidence_observations[{index}].source_path",
        )
        digest_bound_paths = {
            resolved
            for binding_index, binding in enumerate(
                subject_binding["digest_bindings"]
            )
            if (
                resolved := _resolve_inside_root(
                    root,
                    base,
                    binding["subject_locator"],
                    errors,
                    (
                        f"evidence_observations[{index}].subject_binding."
                        f"digest_bindings[{binding_index}].subject_locator"
                    ),
                )
            )
            is not None
        }
        if source_identity is not None:
            digest_bound_paths.add(source_identity[0])
        for locator_index, locator in enumerate(evidence["observation_locators"]):
            locator_location = (
                f"evidence_observations[{index}].observation_locators"
                f"[{locator_index}]"
            )
            _check_local_locator(root, base, locator, errors, locator_location)
            locator_identity = _locator_identity(
                root, base, locator, errors, locator_location
            )
            if (
                locator_identity is not None
                and locator_identity[0] not in digest_bound_paths
            ):
                _error(
                    errors,
                    "observation_locator_path_not_digest_bound",
                    locator_location,
                    (
                        f"locator path {locator_identity[0]} is neither the "
                        "content-digested source_path nor a digest-bound subject"
                    ),
                )

        for detail_index, detail_ref in enumerate(evidence["detail_refs"]):
            detail_location = f"evidence_observations[{index}].detail_refs[{detail_index}]"
            _check_local_locator(root, base, detail_ref, errors, detail_location)

        environment_ref = subject_binding["environment_ref"]
        if environment_ref is not None:
            _check_local_locator(
                root,
                base,
                environment_ref,
                errors,
                f"evidence_observations[{index}].subject_binding.environment_ref",
            )
        for locator_index, locator in enumerate(
            subject_binding["command_or_log_refs"]
        ):
            _check_local_locator(
                root,
                base,
                locator,
                errors,
                (
                    f"evidence_observations[{index}].subject_binding."
                    f"command_or_log_refs[{locator_index}]"
                ),
            )

    for effect_index, effect in enumerate(source["evidence_effects"]):
        effect_location = (
            f"evidence_effects[{effect_index}].observation_locator"
        )
        _check_local_locator(
            root,
            base,
            effect["observation_locator"],
            errors,
            effect_location,
        )
        observation = next(
            (
                item
                for item in source["evidence_observations"]
                if item["entity_id"] == effect["evidence_ref"]["entity_id"]
            ),
            None,
        )
        if observation is None:
            continue
        effect_identity = _locator_identity(
            root,
            base,
            effect["observation_locator"],
            errors,
            effect_location,
        )
        allowed_identities = {
            identity
            for locator_index, raw_locator in enumerate(
                observation["observation_locators"]
            )
            if (
                identity := _locator_identity(
                    root,
                    base,
                    raw_locator,
                    errors,
                    f"{effect_location}.evidence_scope[{locator_index}]",
                )
            )
            is not None
        }
        if effect_identity is not None and effect_identity not in allowed_identities:
            _error(
                errors,
                "evidence_effect_locator_outside_observation",
                effect_location,
                (
                    f"locator {effect['observation_locator']!r} is not declared by "
                    f"evidence {observation['entity_id']}"
                ),
            )

    procedure_refs: list[tuple[str, str]] = []
    for item in source["verification_items"]:
        for field in ("verification_method", "validation_method", "reverification"):
            for index, raw_path in enumerate(item[field]["procedure_refs"]):
                procedure_refs.append(
                    (raw_path, f"{item['entity_id']}.{field}.procedure_refs[{index}]")
                )
    for item in source["implementation_conformance_items"]:
        for index, raw_path in enumerate(item["procedure_refs"]):
            procedure_refs.append(
                (raw_path, f"{item['entity_id']}.procedure_refs[{index}]")
            )
    for raw_path, location in procedure_refs:
        path = _resolve_inside_root(root, root, raw_path, errors, location)
        _require_file(path, errors, location)

    decision_record_ref = source["human_acceptance"]["decision_record_ref"]
    if decision_record_ref is not None:
        _check_local_locator(
            root,
            base,
            decision_record_ref,
            errors,
            "human_acceptance.decision_record_ref",
        )

    for index, raw_path in enumerate(source["record_surface"]["detail_refs"]):
        location = f"record_surface.detail_refs[{index}]"
        path = _resolve_inside_root(root, base, raw_path, errors, location)
        _require_file(path, errors, location)


def _parse_timestamp(
    value: str,
    errors: list[dict[str, str]],
    location: str,
) -> datetime | None:
    normalized = value
    if normalized.endswith(("Z", "z")):
        normalized = f"{normalized[:-1]}+00:00"
    if len(normalized) > 10 and normalized[10] in {"t", "T"}:
        normalized = f"{normalized[:10]}T{normalized[11:]}"
    end_of_day = re.match(
        r"^(\d{4}-\d{2}-\d{2})T24:00:00(?:\.0+)?([+-]\d{2}:\d{2})$",
        normalized,
    )
    try:
        if end_of_day is not None:
            normalized = (
                f"{end_of_day.group(1)}T00:00:00{end_of_day.group(2)}"
            )
            return datetime.fromisoformat(normalized) + timedelta(days=1)
        return datetime.fromisoformat(normalized)
    except (TypeError, ValueError) as exc:
        _error(errors, "timestamp_parse_failed", location, str(exc))
        return None


def _check_temporal_consistency(
    source: dict[str, Any],
    errors: list[dict[str, str]],
) -> None:
    recorded_at = _parse_timestamp(source["recorded_at"], errors, "recorded_at")
    if recorded_at is None:
        return
    evidence_times: dict[str, datetime] = {}
    for index, evidence in enumerate(source["evidence_observations"]):
        location = f"evidence_observations[{index}].observed_at"
        observed_at = _parse_timestamp(evidence["observed_at"], errors, location)
        if observed_at is None:
            continue
        evidence_times[evidence["entity_id"]] = observed_at
        if observed_at > recorded_at:
            _error(
                errors,
                "observation_after_register_time",
                f"evidence_observations[{index}].observed_at",
                f"observed_at {observed_at.isoformat()} exceeds recorded_at {recorded_at.isoformat()}",
            )

    state_by_id = {
        profile["entity_id"]: profile["state"]
        for profile in source["state_profiles"]
    }
    for item in source["verification_items"]:
        reverification = item["reverification"]
        last_raw = reverification["last_evaluated_at"]
        valid_raw = reverification["valid_until"]
        last_evaluated_at = (
            _parse_timestamp(
                last_raw,
                errors,
                f"{item['entity_id']}.reverification.last_evaluated_at",
            )
            if last_raw
            else None
        )
        valid_until = (
            _parse_timestamp(
                valid_raw,
                errors,
                f"{item['entity_id']}.reverification.valid_until",
            )
            if valid_raw
            else None
        )
        if last_evaluated_at is not None and last_evaluated_at > recorded_at:
            _error(
                errors,
                "evaluation_after_register_time",
                f"{item['entity_id']}.reverification.last_evaluated_at",
                (
                    f"last_evaluated_at {last_evaluated_at.isoformat()} exceeds "
                    f"recorded_at {recorded_at.isoformat()}"
                ),
            )
        state = state_by_id.get(item["state_profile_ref"]["entity_id"])
        if state is not None:
            assurance = state["assurance"]
            evaluated_state = (
                state["verification"] not in {"not_run", "not_applicable"}
                or state["validation"]
                not in {"not_evaluated", "not_applicable"}
                or assurance["outcome"] in {"satisfied", "refuted"}
            )
            if evaluated_state and last_evaluated_at is None:
                _error(
                    errors,
                    "evaluated_state_missing_evaluation_time",
                    f"{item['entity_id']}.reverification.last_evaluated_at",
                    "an evaluated verification or assurance state requires last_evaluated_at",
                )
            if reverification["status"] in {"due", "blocked"} and (
                state["freshness"] == "current"
                or assurance["finality"] == "terminal"
            ):
                _error(
                    errors,
                    "reverification_status_conflicts_with_current_state",
                    f"{item['entity_id']}.reverification.status",
                    (
                        f"{reverification['status']} cannot coexist with current "
                        "freshness or terminal assurance"
                    ),
                )
        referenced_evidence_ids = {
            reference["entity_id"]
            for reference in item["evidence_refs"] + item["counterevidence_refs"]
        }
        referenced_evidence_ids.update(
            reference["entity_id"]
            for assessment in item.get("lifecycle_surface_assessments", [])
            for reference in assessment["evidence_refs"]
        )
        referenced_times = [
            evidence_times[evidence_id]
            for evidence_id in referenced_evidence_ids
            if evidence_id in evidence_times
        ]
        if last_evaluated_at is not None and referenced_times:
            latest_evidence_at = max(referenced_times)
            if last_evaluated_at < latest_evidence_at:
                _error(
                    errors,
                    "evaluation_precedes_referenced_evidence",
                    f"{item['entity_id']}.reverification.last_evaluated_at",
                    (
                        f"last_evaluated_at {last_evaluated_at.isoformat()} precedes "
                        f"latest referenced evidence {latest_evidence_at.isoformat()}"
                    ),
                )
        if valid_until is not None and last_evaluated_at is None:
            _error(
                errors,
                "validity_without_evaluation_time",
                f"{item['entity_id']}.reverification.valid_until",
                "valid_until requires last_evaluated_at",
            )
        if (
            last_evaluated_at is not None
            and valid_until is not None
            and valid_until < last_evaluated_at
        ):
            _error(
                errors,
                "validity_precedes_evaluation",
                f"{item['entity_id']}.reverification.valid_until",
                (
                    f"valid_until {valid_until.isoformat()} precedes "
                    f"last_evaluated_at {last_evaluated_at.isoformat()}"
                ),
            )
        if (
            valid_until is not None
            and valid_until < recorded_at
            and reverification["status"] not in {"due", "blocked"}
        ):
            _error(
                errors,
                "expired_reverification_not_marked_due",
                f"{item['entity_id']}.reverification.status",
                (
                    f"valid_until {valid_until.isoformat()} precedes "
                    f"recorded_at {recorded_at.isoformat()}"
                ),
            )

    decided_raw = source["human_acceptance"]["decided_at"]
    if decided_raw is not None:
        decided_at = _parse_timestamp(
            decided_raw, errors, "human_acceptance.decided_at"
        )
        if decided_at is None:
            return
        if decided_at > recorded_at:
            _error(
                errors,
                "human_decision_after_register_time",
                "human_acceptance.decided_at",
                f"decided_at {decided_at.isoformat()} exceeds recorded_at {recorded_at.isoformat()}",
            )
        if evidence_times and decided_at < max(evidence_times.values()):
            _error(
                errors,
                "human_decision_precedes_registered_evidence",
                "human_acceptance.decided_at",
                (
                    f"decided_at {decided_at.isoformat()} precedes the latest "
                    f"registered evidence {max(evidence_times.values()).isoformat()}"
                ),
            )


def _derive_declared_gaps(
    source: dict[str, Any],
    errors: list[dict[str, str]],
) -> list[dict[str, Any]]:
    field_specs = (
        (
            "verification_items",
            "unproven_scope",
            "verification_unproven_scope",
        ),
        (
            "verification_items",
            "residual_risks",
            "verification_residual_risk",
        ),
        (
            "implementation_conformance_items",
            "remaining_obligations",
            "conformance_remaining_obligation",
        ),
    )
    records: list[dict[str, Any]] = []
    identity_locations: dict[str, list[str]] = {}
    for collection, field, gap_kind in field_specs:
        for item_index, item in enumerate(source[collection]):
            item_id = item["entity_id"]
            for content_index, content in enumerate(item[field]):
                source_locator = (
                    f"{GAP_SOURCE_LOCATOR}#/{collection}/{item_index}/{field}/"
                    f"{content_index}"
                )
                gap_digest = _canonical_json_digest(
                    {
                        "content": content,
                        "gap_kind": gap_kind,
                        "item_id": item_id,
                    }
                )
                gap_id = f"gap.sha256.{gap_digest}"
                identity_locations.setdefault(gap_id, []).append(source_locator)
                records.append(
                    {
                        "gap_id": gap_id,
                        "gap_kind": gap_kind,
                        "source_locator": source_locator,
                        "item_ref": {
                            "reference_kind": "ref",
                            "entity_id": item_id,
                        },
                        "content": content,
                        "content_digest": {
                            "algorithm": "sha256",
                            "value": _text_digest(content),
                        },
                    }
                )
    for gap_id, locations in sorted(identity_locations.items()):
        if len(locations) > 1:
            _error(
                errors,
                "duplicate_declared_gap_identity",
                ",".join(locations),
                f"declared denominator produces duplicate identity {gap_id}",
            )
    return sorted(records, key=lambda record: record["gap_id"])


def _gap_set_digest(gaps: list[dict[str, Any]]) -> str:
    return _canonical_json_digest(sorted(gaps, key=lambda gap: gap["gap_id"]))


def _check_unresolved_gap_ref(
    unresolved_ref: dict[str, Any],
    item_id: str,
    unresolved_by_id: dict[str, dict[str, Any]],
    errors: list[dict[str, str]],
    location: str,
) -> None:
    unresolved_id = unresolved_ref["entity_id"]
    unresolved = unresolved_by_id.get(unresolved_id)
    if unresolved is None:
        _error(
            errors,
            "unresolved_gap_disposition_ref",
            location,
            unresolved_id,
        )
        return
    affected_ids = {
        reference["entity_id"] for reference in unresolved["affected_entity_refs"]
    }
    if item_id not in affected_ids:
        _error(
            errors,
            "gap_item_not_affected_by_unresolved",
            location,
            f"{unresolved_id} does not affect {item_id}",
        )


def _check_gap_register(
    root: Path,
    source_sha256: str | None,
    source: dict[str, Any],
    register_path: Path,
    register: dict[str, Any],
    errors: list[dict[str, str]],
) -> None:
    if register["schema_version"] != GAP_REGISTER_VERSION:
        _error(
            errors,
            "gap_register_version_mismatch",
            "gap_register.schema_version",
            (
                f"expected {GAP_REGISTER_VERSION}, observed "
                f"{register['schema_version']!r}"
            ),
        )
    expected_source_locator = GAP_SOURCE_LOCATOR
    if register["source"]["locator"] != expected_source_locator:
        _error(
            errors,
            "gap_register_source_locator_mismatch",
            "gap_register.source.locator",
            (
                f"expected {expected_source_locator!r}, observed "
                f"{register['source']['locator']!r}"
            ),
        )
    declared_source_digest = register["source"]["content_digest"]["value"]
    if source_sha256 is None or declared_source_digest != source_sha256:
        _error(
            errors,
            "gap_register_source_digest_mismatch",
            "gap_register.source.content_digest",
            f"expected {source_sha256!r}, observed {declared_source_digest!r}",
        )

    expected_records = _derive_declared_gaps(source, errors)
    expected_by_id = {record["gap_id"]: record for record in expected_records}
    actual_gaps = register["gaps"]
    actual_id_counts = Counter(gap["gap_id"] for gap in actual_gaps)
    actual_locator_counts = Counter(gap["source_locator"] for gap in actual_gaps)
    for gap_id, count in sorted(actual_id_counts.items()):
        if count > 1:
            _error(
                errors,
                "duplicate_gap_id",
                "gap_register.gaps",
                f"{gap_id} occurs {count} times",
            )
    for locator, count in sorted(actual_locator_counts.items()):
        if count > 1:
            _error(
                errors,
                "duplicate_gap_source_locator",
                "gap_register.gaps",
                f"{locator} occurs {count} times",
            )

    actual_by_id: dict[str, dict[str, Any]] = {}
    for gap in actual_gaps:
        actual_by_id.setdefault(gap["gap_id"], gap)
    for gap_id in sorted(set(expected_by_id) - set(actual_by_id)):
        _error(
            errors,
            "missing_gap_record",
            "gap_register.gaps",
            f"missing {gap_id} at {expected_by_id[gap_id]['source_locator']}",
        )
    for gap_id in sorted(set(actual_by_id) - set(expected_by_id)):
        _error(
            errors,
            "unexpected_gap_record",
            "gap_register.gaps",
            gap_id,
        )

    comparison_codes = {
        "gap_kind": "gap_kind_mismatch",
        "source_locator": "gap_source_locator_mismatch",
        "content": "gap_content_mismatch",
        "content_digest": "gap_content_digest_mismatch",
    }
    for gap_id in sorted(set(expected_by_id) & set(actual_by_id)):
        expected = expected_by_id[gap_id]
        actual = actual_by_id[gap_id]
        for field, code in comparison_codes.items():
            if actual[field] != expected[field]:
                _error(
                    errors,
                    code,
                    f"gap_register.gaps[{gap_id}].{field}",
                    f"expected {expected[field]!r}, observed {actual[field]!r}",
                )
        actual_item_ref = actual["item_ref"]
        if (
            actual_item_ref["reference_kind"] != "ref"
            or actual_item_ref["entity_id"] != expected["item_ref"]["entity_id"]
        ):
            _error(
                errors,
                "gap_item_ref_mismatch",
                f"gap_register.gaps[{gap_id}].item_ref",
                (
                    f"expected {expected['item_ref']!r}, observed "
                    f"{actual_item_ref!r}"
                ),
            )

    unresolved_by_id = {
        item["entity_id"]: item for item in source["unresolved_items"]
    }
    evidence_by_id = {
        item["entity_id"]: item for item in source["evidence_observations"]
    }
    supporting_effects = {
        (effect["evidence_ref"]["entity_id"], item_ref["entity_id"])
        for effect in source["evidence_effects"]
        if effect["effect"] == "supports"
        for item_ref in effect["item_refs"]
    }
    for gap_index, gap in enumerate(actual_gaps):
        location = f"gap_register.gaps[{gap_index}].disposition"
        item_id = gap["item_ref"]["entity_id"]
        disposition = gap["disposition"]
        kind = disposition["kind"]
        if kind == "canonical_unresolved":
            _check_unresolved_gap_ref(
                disposition["unresolved_ref"],
                item_id,
                unresolved_by_id,
                errors,
                f"{location}.unresolved_ref",
            )
        elif kind == "resolved":
            evidence_ids = [
                reference["entity_id"] for reference in disposition["evidence_refs"]
            ]
            if len(evidence_ids) != len(set(evidence_ids)):
                _error(
                    errors,
                    "duplicate_resolved_gap_evidence_ref",
                    f"{location}.evidence_refs",
                    "resolved evidence references must be unique",
                )
            has_supporting_effect = False
            for evidence_index, evidence_id in enumerate(evidence_ids):
                evidence_location = f"{location}.evidence_refs[{evidence_index}]"
                evidence = evidence_by_id.get(evidence_id)
                if evidence is None:
                    _error(
                        errors,
                        "resolved_gap_evidence_ref_dangling",
                        evidence_location,
                        evidence_id,
                    )
                    continue
                if (
                    evidence["freshness"] != "current"
                    or evidence["subject_binding"]["status"] != "bound"
                ):
                    _error(
                        errors,
                        "resolved_gap_evidence_not_current_bound",
                        evidence_location,
                        evidence_id,
                    )
                if (evidence_id, item_id) in supporting_effects:
                    has_supporting_effect = True
            if not has_supporting_effect:
                _error(
                    errors,
                    "resolved_gap_missing_item_support",
                    f"{location}.evidence_refs",
                    f"no referenced supports effect targets {item_id}",
                )
            assessed_gap_id = disposition["completion_assessment"][
                "assessed_gap_id"
            ]
            if assessed_gap_id != gap["gap_id"]:
                _error(
                    errors,
                    "resolved_gap_assessment_identity_mismatch",
                    f"{location}.completion_assessment.assessed_gap_id",
                    f"expected {gap['gap_id']}, observed {assessed_gap_id}",
                )
        elif kind == "not_applicable":
            decision = disposition["accepted_human_decision"]
            locator = decision["locator"]
            locator_location = f"{location}.accepted_human_decision.locator"
            _check_local_locator(
                root,
                register_path.parent,
                locator,
                errors,
                locator_location,
            )
            identity = _locator_identity(
                root,
                register_path.parent,
                locator,
                errors,
                locator_location,
            )
            if identity is not None:
                decision_path, _ = identity
                if decision_path.is_file():
                    observed_digest = _sha256(decision_path)
                    declared_digest = decision["content_digest"]["value"]
                    if observed_digest != declared_digest:
                        _error(
                            errors,
                            "not_applicable_decision_digest_mismatch",
                            f"{location}.accepted_human_decision.content_digest",
                            (
                                f"expected {observed_digest}, observed "
                                f"{declared_digest}"
                            ),
                        )
        elif kind == "control_plane_handoff":
            _check_unresolved_gap_ref(
                disposition["audit_unresolved_ref"],
                item_id,
                unresolved_by_id,
                errors,
                f"{location}.audit_unresolved_ref",
            )
            handoff_locator = disposition.get("handoff_locator")
            if handoff_locator is not None:
                _check_local_locator(
                    root,
                    register_path.parent,
                    handoff_locator,
                    errors,
                    f"{location}.handoff_locator",
                )

    observed_gap_set_digest = register["gap_set_digest"]["value"]
    expected_gap_set_digest = _gap_set_digest(actual_gaps)
    if observed_gap_set_digest != expected_gap_set_digest:
        _error(
            errors,
            "gap_set_digest_mismatch",
            "gap_register.gap_set_digest",
            (
                f"expected {expected_gap_set_digest}, observed "
                f"{observed_gap_set_digest}"
            ),
        )


def _check_projection(
    projection_path: Path,
    source: dict[str, Any],
    source_sha256: str,
    source_ref: str,
    errors: list[dict[str, str]],
) -> None:
    try:
        projection = projection_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        _error(errors, "projection_load_failed", "projection", str(exc))
        return

    expected = render_verification_projection(
        source,
        source_sha256=source_sha256,
        source_ref=source_ref,
    )
    if projection != expected:
        observed_lines = projection.splitlines()
        expected_lines = expected.splitlines()
        mismatch_line = next(
            (
                index
                for index, (observed, wanted) in enumerate(
                    zip(observed_lines, expected_lines, strict=False), start=1
                )
                if observed != wanted
            ),
            min(len(observed_lines), len(expected_lines)) + 1,
        )
        _error(
            errors,
            "projection_value_mismatch",
            f"projection:{mismatch_line}",
            (
                "projection is not the exact deterministic rendering of the "
                f"source; first differing line={mismatch_line}"
            ),
        )


def _argument_path(root: Path, value: str | None, default: Path) -> Path:
    if value is None:
        return default.resolve()
    path = Path(value)
    if not path.is_absolute():
        path = root / path
    return path.resolve()


def _display_path(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description=(
            "Validate the internal verification source, local reference closure, "
            "bound file digests, and exact deterministic Markdown projection equality."
        )
    )
    parser.add_argument("--source")
    parser.add_argument("--schema")
    parser.add_argument("--projection")
    parser.add_argument("--gap-register")
    parser.add_argument("--gap-register-schema")
    args = parser.parse_args()

    source_path = _argument_path(
        root,
        args.source,
        root / "validation/verification-source.json",
    )
    schema_path = _argument_path(
        root,
        args.schema,
        root / "validation/verification-source.schema.json",
    )
    projection_path = _argument_path(
        root,
        args.projection,
        root / "validation/verification-source.generated.md",
    )
    gap_register_path = _argument_path(
        root,
        args.gap_register,
        root / "validation/verification-gap-register.json",
    )
    gap_register_schema_path = _argument_path(
        root,
        args.gap_register_schema,
        root / "validation/verification-gap-register.schema.json",
    )
    common_path = root / "schemas/common.schema.json"

    errors: list[dict[str, str]] = []
    source_allowed = (
        _resolve_inside_root(root, root, str(source_path), errors, "source") is not None
    )
    schema_allowed = (
        _resolve_inside_root(root, root, str(schema_path), errors, "schema") is not None
    )
    projection_allowed = (
        _resolve_inside_root(root, root, str(projection_path), errors, "projection")
        is not None
    )
    gap_register_allowed = (
        _resolve_inside_root(
            root, root, str(gap_register_path), errors, "gap_register"
        )
        is not None
    )
    gap_register_schema_allowed = (
        _resolve_inside_root(
            root,
            root,
            str(gap_register_schema_path),
            errors,
            "gap_register_schema",
        )
        is not None
    )
    tracked_paths = {
        "source": source_path if source_allowed else None,
        "schema": schema_path if schema_allowed else None,
        "common_schema": common_path,
        "projection": projection_path if projection_allowed else None,
        "gap_register": gap_register_path if gap_register_allowed else None,
        "gap_register_schema": (
            gap_register_schema_path if gap_register_schema_allowed else None
        ),
        "validator": VALIDATOR_PATH,
    }
    initial_digests: dict[str, str | None] = {}
    for label, path in tracked_paths.items():
        try:
            initial_digests[label] = (
                _sha256(path) if path is not None and path.is_file() else None
            )
        except OSError as exc:
            initial_digests[label] = None
            _error(errors, "artifact_digest_failed", label, str(exc))
    source = _load_json(source_path, errors, "source") if source_allowed else None
    schema = _load_json(schema_path, errors, "schema") if schema_allowed else None
    gap_register = (
        _load_json(gap_register_path, errors, "gap_register")
        if gap_register_allowed
        else None
    )
    gap_register_schema = (
        _load_json(
            gap_register_schema_path,
            errors,
            "gap_register_schema",
        )
        if gap_register_schema_allowed
        else None
    )
    common = _load_json(common_path, errors, "common_schema")
    schema_passed = False
    gap_register_schema_passed = False

    checks: dict[str, str] = {
        "schema_validation": "not_run",
        "reference_closure": "not_run",
        "paths_and_digests": "not_run",
        "temporal_consistency": "not_run",
        "projection_surface": "not_run",
        "gap_register": "not_run",
    }
    if source is not None and schema is not None and common is not None:
        schema_error_count = len(errors)
        if schema.get("$id") != VERIFICATION_SOURCE_SCHEMA_ID:
            _error(
                errors,
                "schema_identity_mismatch",
                "schema.$id",
                f"expected {VERIFICATION_SOURCE_SCHEMA_ID}, observed {schema.get('$id')!r}",
            )
        if source.get("$schema") != VERIFICATION_SOURCE_SCHEMA_REF:
            _error(
                errors,
                "source_schema_ref_mismatch",
                "source.$schema",
                f"expected {VERIFICATION_SOURCE_SCHEMA_REF}, observed {source.get('$schema')!r}",
            )
        try:
            Draft202012Validator.check_schema(schema)
            Draft202012Validator.check_schema(common)
            if common.get("$id") != COMMON_SCHEMA_ID:
                _error(
                    errors,
                    "common_schema_identity_mismatch",
                    "common_schema.$id",
                    f"expected {COMMON_SCHEMA_ID}, observed {common.get('$id')!r}",
                )
            registry = Registry().with_resource(
                schema["$id"], Resource.from_contents(schema)
            )
            registry = registry.with_resource(
                common["$id"], Resource.from_contents(common)
            )
            validator = Draft202012Validator(
                schema,
                registry=registry,
                format_checker=FormatChecker(),
            )
            for issue in sorted(
                validator.iter_errors(source),
                key=lambda error: tuple(str(part) for part in error.absolute_path),
            ):
                location = "/".join(str(part) for part in issue.absolute_path) or "/"
                _error(errors, "schema_validation_failed", location, issue.message)
        except (
            CannotDetermineSpecification,
            KeyError,
            NoSuchResource,
            PointerToNowhere,
            SchemaError,
            TypeError,
            Unresolvable,
            ValueError,
        ) as exc:
            _error(errors, "schema_initialization_failed", "schema", str(exc))
        schema_passed = len(errors) == schema_error_count
        checks["schema_validation"] = "passed" if schema_passed else "failed"

        if schema_passed:
            closure_error_count = len(errors)
            _check_reference_closure(root, source_path, source, errors)
            checks["reference_closure"] = (
                "passed" if len(errors) == closure_error_count else "failed"
            )

            path_error_count = len(errors)
            _check_paths_and_digests(root, source_path, source, errors)
            checks["paths_and_digests"] = (
                "passed" if len(errors) == path_error_count else "failed"
            )

            temporal_error_count = len(errors)
            _check_temporal_consistency(source, errors)
            checks["temporal_consistency"] = (
                "passed" if len(errors) == temporal_error_count else "failed"
            )

            if projection_allowed:
                projection_error_count = len(errors)
                source_digest = initial_digests["source"]
                if source_digest is None:
                    _error(
                        errors,
                        "projection_source_digest_unavailable",
                        "projection",
                        "source digest was unavailable at validation start",
                    )
                else:
                    _check_projection(
                        projection_path,
                        source,
                        source_digest,
                        source_path.name,
                        errors,
                    )
                checks["projection_surface"] = (
                    "passed" if len(errors) == projection_error_count else "failed"
                )

    if gap_register is not None and gap_register_schema is not None:
        gap_schema_error_count = len(errors)
        if gap_register_schema.get("$id") != GAP_REGISTER_SCHEMA_ID:
            _error(
                errors,
                "gap_register_schema_identity_mismatch",
                "gap_register_schema.$id",
                (
                    f"expected {GAP_REGISTER_SCHEMA_ID}, observed "
                    f"{gap_register_schema.get('$id')!r}"
                ),
            )
        if gap_register.get("$schema") != GAP_REGISTER_SCHEMA_REF:
            _error(
                errors,
                "gap_register_schema_ref_mismatch",
                "gap_register.$schema",
                (
                    f"expected {GAP_REGISTER_SCHEMA_REF}, observed "
                    f"{gap_register.get('$schema')!r}"
                ),
            )
        try:
            Draft202012Validator.check_schema(gap_register_schema)
            gap_validator = Draft202012Validator(
                gap_register_schema,
                format_checker=FormatChecker(),
            )
            for issue in sorted(
                gap_validator.iter_errors(gap_register),
                key=lambda error: tuple(str(part) for part in error.absolute_path),
            ):
                issue_location = (
                    "/".join(str(part) for part in issue.absolute_path) or "/"
                )
                _error(
                    errors,
                    "gap_register_schema_validation_failed",
                    issue_location,
                    issue.message,
                )
        except (SchemaError, TypeError, ValueError) as exc:
            _error(
                errors,
                "gap_register_schema_initialization_failed",
                "gap_register_schema",
                str(exc),
            )
        gap_register_schema_passed = len(errors) == gap_schema_error_count
        if not gap_register_schema_passed:
            checks["gap_register"] = "failed"

    if (
        schema_passed
        and gap_register_schema_passed
        and source is not None
        and gap_register is not None
    ):
        gap_error_count = len(errors)
        _check_gap_register(
            root,
            initial_digests["source"],
            source,
            gap_register_path,
            gap_register,
            errors,
        )
        checks["gap_register"] = (
            "passed" if len(errors) == gap_error_count else "failed"
        )

    for label, path in tracked_paths.items():
        initial_digest = initial_digests[label]
        try:
            final_digest = (
                _sha256(path) if path is not None and path.is_file() else None
            )
        except OSError as exc:
            final_digest = None
            _error(errors, "artifact_digest_failed", label, str(exc))
        if final_digest != initial_digest:
            _error(
                errors,
                "artifact_changed_during_validation",
                label,
                f"initial={initial_digest!r}, final={final_digest!r}",
            )
            checks["paths_and_digests"] = "failed"
            if label == "projection":
                checks["projection_surface"] = "failed"
            if label in {"source", "gap_register", "gap_register_schema"}:
                checks["gap_register"] = "failed"

    if any(digest is None for digest in initial_digests.values()):
        checks["paths_and_digests"] = "failed"
    if initial_digests["projection"] is None:
        checks["projection_surface"] = "failed"
    if (
        initial_digests["gap_register"] is None
        or initial_digests["gap_register_schema"] is None
    ):
        checks["gap_register"] = "failed"

    errors.sort(key=lambda item: (item["code"], item["location"], item["message"]))
    counts: dict[str, int] = {}
    if source is not None:
        for collection in (
            "state_profiles",
            "evidence_observations",
            "evidence_effects",
            "verification_items",
            "implementation_conformance_items",
            "views",
            "unresolved_items",
        ):
            value = source.get(collection)
            if isinstance(value, list):
                counts[collection] = len(value)
        unresolved_items = source.get("unresolved_items")
        if isinstance(unresolved_items, list) and all(
            isinstance(item, dict) for item in unresolved_items
        ):
            obligation_collections = [
                item.get("resolution_obligations") for item in unresolved_items
            ]
            path_collections = [
                item.get("resolution_paths") for item in unresolved_items
            ]
            if all(isinstance(value, list) for value in obligation_collections):
                counts["resolution_obligations"] = sum(
                    len(value) for value in obligation_collections
                )
            if all(isinstance(value, list) for value in path_collections):
                counts["resolution_paths"] = sum(
                    len(value) for value in path_collections
                )
    if gap_register is not None and isinstance(gap_register.get("gaps"), list):
        counts["gap_records"] = len(gap_register["gaps"])

    try:
        jsonschema_version = metadata.version("jsonschema")
    except metadata.PackageNotFoundError:  # pragma: no cover - runtime dependency.
        jsonschema_version = "unknown"
    executed_at = datetime.now(timezone.utc).isoformat()
    result = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "status": "ok" if not errors else "error",
        "subject": {
            "source": _display_path(root, source_path),
            "source_sha256": (
                initial_digests["source"]
            ),
            "schema": _display_path(root, schema_path),
            "schema_sha256": (
                initial_digests["schema"]
            ),
            "common_schema": _display_path(root, common_path),
            "common_schema_sha256": (
                initial_digests["common_schema"]
            ),
            "projection": _display_path(root, projection_path),
            "projection_sha256": (
                initial_digests["projection"]
            ),
            "gap_register": _display_path(root, gap_register_path),
            "gap_register_sha256": initial_digests["gap_register"],
            "gap_register_schema": _display_path(
                root, gap_register_schema_path
            ),
            "gap_register_schema_sha256": initial_digests[
                "gap_register_schema"
            ],
            "gap_set_sha256": (
                gap_register.get("gap_set_digest", {}).get("value")
                if gap_register is not None
                else None
            ),
        },
        "execution": {
            "validator": _display_path(root, VALIDATOR_PATH),
            "validator_sha256": initial_digests["validator"],
            "executed_at": executed_at,
            "python_version": platform.python_version(),
            "jsonschema_version": jsonschema_version,
        },
        "checks": checks,
        "counts": counts,
        "errors": errors,
        "limitations": [
            "Projection checking requires exact equality with a deterministic complete-node rendering; prose outside that generated projection remains non-canonical explanatory material.",
            "A successful result is an internal consistency observation, not field validation, action authenticity, or human acceptance.",
            "Temporal checks establish record-internal ordering and expiry consistency, not trusted time or clock authenticity.",
            "Start/end digest guards reject tracked-artifact mutation during a run but do not provide a trusted filesystem snapshot or resistance to adversarial change-and-restore races.",
            "Gap-register completeness is bounded to the three declared source arrays; it does not establish that the denominator captures unknown unknowns.",
            "Resolved and non-applicable dispositions are checked for typed, located support and authority records, not for external-world truth beyond those records.",
        ],
    }
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
