from __future__ import annotations

import argparse
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError


RESULT_VERSION = "semantic-guard-engineering-rule-pack-validation-result/v0"
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACK = ROOT / "validation/engineering-rule-pack.candidate.json"
DEFAULT_SCHEMA = ROOT / "validation/engineering-rule-pack.schema.json"
PROFILE_PATH = ROOT / "src/semantic_guard/profiles.py"
DIRECT_RULE_PATH = ROOT / "src/semantic_guard/direct_rules.py"
PROFILE_LOCATOR = "src/semantic_guard/profiles.py"
DIRECT_RULE_LOCATOR = "src/semantic_guard/direct_rules.py"
OBLIGATION_PATTERN = re.compile(r"^func\.[a-z0-9_]+$")
DIRECT_RULE_PATTERN = re.compile(r"^direct\.[a-z0-9.-]+/v[0-9]+$")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON root must be an object")
    return value


def _location(path: Any) -> str:
    parts = [str(item) for item in path]
    return "$" if not parts else "$." + ".".join(parts)


def _error(
    errors: list[dict[str, str]],
    code: str,
    location: str,
    message: str,
) -> None:
    errors.append({"code": code, "location": location, "message": message})


def _ast_string_set(path: Path, pattern: re.Pattern[str]) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and pattern.fullmatch(node.value)
    }


def _profile_identity(path: Path) -> tuple[str, str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name)
            and target.id == "FUNCTIONAL_REQUIREMENT_PROFILE"
            for target in node.targets
        ):
            continue
        if not isinstance(node.value, ast.Call):
            break
        keywords = {item.arg: item.value for item in node.value.keywords if item.arg}
        profile_id = keywords.get("profile_id")
        version = keywords.get("version")
        if (
            isinstance(profile_id, ast.Constant)
            and isinstance(profile_id.value, str)
            and isinstance(version, ast.Constant)
            and isinstance(version.value, str)
        ):
            return profile_id.value, version.value
        break
    raise ValueError("FUNCTIONAL_REQUIREMENT_PROFILE identity is not statically readable")


def _check_counter_coverage(
    *,
    expected: set[str],
    observed: list[str],
    errors: list[dict[str, str]],
    missing_code: str,
    dangling_code: str,
    duplicate_code: str,
    noun: str,
) -> None:
    counter = Counter(observed)
    for item in sorted(expected - set(counter)):
        _error(errors, missing_code, "$.rules", f"missing {noun} mapping: {item}")
    for item in sorted(set(counter) - expected):
        _error(errors, dangling_code, "$.rules", f"dangling {noun} reference: {item}")
    for item, count in sorted(counter.items()):
        if count > 1:
            _error(
                errors,
                duplicate_code,
                "$.rules",
                f"{noun} is mapped {count} times: {item}",
            )


def _review_record_consistency(
    record: dict[str, Any],
    *,
    location: str,
    errors: list[dict[str, str]],
) -> None:
    status = record.get("status")
    evidence = record.get("evidence_refs", [])
    authority = record.get("authority_ref")
    if status == "completed" and (not evidence or not authority):
        _error(
            errors,
            "completed_review_without_evidence",
            location,
            "completed review requires evidence_refs and authority_ref",
        )
    if status == "not_performed" and (evidence or authority is not None):
        _error(
            errors,
            "unperformed_review_has_evidence",
            location,
            "not_performed review must not carry evidence or authority",
        )


def _semantic_validate(pack: dict[str, Any], errors: list[dict[str, str]]) -> dict[str, int]:
    expected_obligations = _ast_string_set(PROFILE_PATH, OBLIGATION_PATTERN)
    expected_direct_rules = _ast_string_set(DIRECT_RULE_PATH, DIRECT_RULE_PATTERN)
    local_profile_id, local_profile_version = _profile_identity(PROFILE_PATH)

    profile = pack["profile"]
    if profile["local_locator"] != PROFILE_LOCATOR or not PROFILE_PATH.is_file():
        _error(
            errors,
            "profile_locator_invalid",
            "$.profile.local_locator",
            "profile locator must resolve to the current repository profile source",
        )
    if (profile["profile_id"], profile["version"]) != (
        local_profile_id,
        local_profile_version,
    ):
        _error(
            errors,
            "profile_identity_mismatch",
            "$.profile",
            f"declared {profile['profile_id']}/{profile['version']} does not match "
            f"local {local_profile_id}/{local_profile_version}",
        )

    sources = pack["sources"]
    source_ids = [item["source_id"] for item in sources]
    source_counter = Counter(source_ids)
    for source_id, count in sorted(source_counter.items()):
        if count > 1:
            _error(
                errors,
                "duplicate_source_id",
                "$.sources",
                f"source_id appears {count} times: {source_id}",
            )
    source_sections = {
        source["source_id"]: set(source["section_locators"]) for source in sources
    }

    revising_sources: set[str] = set()
    source_exactness: dict[str, bool] = {}
    source_digest_verified: dict[str, bool] = {}
    for index, source in enumerate(sources):
        location = f"$.sources.{index}"
        acquisition = source["acquisition"]
        digest = acquisition["content_digest"]
        exact = acquisition["exact_source_text_acquired"]
        digest_verified = digest["state"] == "verified" and bool(digest.get("value"))
        source_exactness[source["source_id"]] = exact
        source_digest_verified[source["source_id"]] = digest_verified
        if acquisition["state"] == "exact_text_acquired" and not exact:
            _error(
                errors,
                "source_acquisition_state_inconsistent",
                f"{location}.acquisition",
                "exact_text_acquired state requires exact_source_text_acquired=true",
            )
        if exact and (acquisition["state"] != "exact_text_acquired" or not digest_verified):
            _error(
                errors,
                "source_digest_missing",
                f"{location}.acquisition",
                "exact source text requires exact_text_acquired state and a verified digest",
            )
        if not exact and digest["state"] == "verified":
            _error(
                errors,
                "source_digest_scope_ambiguous",
                f"{location}.acquisition.content_digest",
                "a verified content digest cannot be presented as source-text digest when exact text is not acquired",
            )
        if source["status"] == "published_current_to_be_revised":
            revising_sources.add(source["source_id"])
            trigger_text = " ".join(source["review_triggers"]).casefold()
            if not any(
                marker in trigger_text
                for marker in ("replacement", "revision", "revised", "dis 29148", "supersed")
            ):
                _error(
                    errors,
                    "revision_review_trigger_missing",
                    f"{location}.review_triggers",
                    "a to-be-revised source requires an explicit replacement/revision trigger",
                )

    rules = pack["rules"]
    rule_keys = [f"{rule['rule_id']}@{rule['version']}" for rule in rules]
    for key, count in sorted(Counter(rule_keys).items()):
        if count > 1:
            _error(
                errors,
                "duplicate_rule_version",
                "$.rules",
                f"rule identity appears {count} times: {key}",
            )

    observed_obligations: list[str] = []
    observed_direct_rules: list[str] = []
    used_sources: set[str] = set()
    governance = pack["governance"]
    independent_review = governance["independent_review"]
    human_adoption = governance["human_adoption"]
    _review_record_consistency(
        independent_review,
        location="$.governance.independent_review",
        errors=errors,
    )
    _review_record_consistency(
        human_adoption,
        location="$.governance.human_adoption",
        errors=errors,
    )

    for index, rule in enumerate(rules):
        location = f"$.rules.{index}"
        observed_obligations.extend(rule["profile_obligation_refs"])
        for local_ref in rule["local_implementation_rule_refs"]:
            observed_direct_rules.append(local_ref["rule_id"])
            if (
                local_ref["locator"] != DIRECT_RULE_LOCATOR
                or not DIRECT_RULE_PATH.is_file()
            ):
                _error(
                    errors,
                    "local_rule_locator_invalid",
                    f"{location}.local_implementation_rule_refs",
                    "local direct-rule locator is not the current repository source",
                )

        referenced_sources: set[str] = set()
        for ref_index, source_ref in enumerate(rule["source_refs"]):
            source_id = source_ref["source_id"]
            referenced_sources.add(source_id)
            used_sources.add(source_id)
            ref_location = f"{location}.source_refs.{ref_index}"
            if source_id not in source_sections:
                _error(
                    errors,
                    "dangling_source_ref",
                    f"{ref_location}.source_id",
                    f"unknown source_id: {source_id}",
                )
                continue
            if source_ref["section_locator"] not in source_sections[source_id]:
                _error(
                    errors,
                    "dangling_section_ref",
                    f"{ref_location}.section_locator",
                    f"section is not declared by {source_id}: {source_ref['section_locator']}",
                )

        state = rule["adoption_state"]
        runtime = rule["runtime_authority"]
        if state != "adopted" and runtime != "none":
            _error(
                errors,
                "runtime_authority_for_unadopted_rule",
                f"{location}.runtime_authority",
                "only an adopted rule may receive runtime authority",
            )
        if state == "candidate_pending_human_adoption":
            if rule["adoption_evidence_refs"] or rule["independent_review_evidence_refs"]:
                _error(
                    errors,
                    "candidate_has_adoption_evidence",
                    location,
                    "candidate rule must not imply completed review or adoption",
                )
        if state == "adopted":
            if not rule["adoption_evidence_refs"]:
                _error(
                    errors,
                    "adoption_evidence_missing",
                    f"{location}.adoption_evidence_refs",
                    "adopted rule requires human adoption evidence",
                )
            if not rule["independent_review_evidence_refs"]:
                _error(
                    errors,
                    "independent_review_evidence_missing",
                    f"{location}.independent_review_evidence_refs",
                    "adopted rule requires independent review evidence",
                )
            if independent_review["status"] != "completed":
                _error(
                    errors,
                    "independent_review_not_completed",
                    location,
                    "adopted rule requires completed pack-level independent review",
                )
            if human_adoption["status"] != "completed":
                _error(
                    errors,
                    "human_adoption_not_completed",
                    location,
                    "adopted rule requires completed pack-level human adoption",
                )
            for source_id in sorted(referenced_sources):
                if source_id in source_exactness and (
                    not source_exactness[source_id]
                    or not source_digest_verified[source_id]
                ):
                    _error(
                        errors,
                        "adopted_rule_uses_unbound_source",
                        location,
                        f"adopted rule references source without acquired exact text and verified digest: {source_id}",
                    )

        if referenced_sources & revising_sources:
            trigger_text = " ".join(rule["review_triggers"]).casefold()
            if not any(
                marker in trigger_text
                for marker in ("replacement", "revision", "revised", "dis 29148", "supersed")
            ):
                _error(
                    errors,
                    "rule_revision_trigger_missing",
                    f"{location}.review_triggers",
                    "rule referencing a to-be-revised source requires a replacement/revision trigger",
                )

        superseded_by = rule["supersession"]["superseded_by"]
        if superseded_by is not None and superseded_by not in set(rule_keys):
            _error(
                errors,
                "dangling_superseded_by",
                f"{location}.supersession.superseded_by",
                f"replacement is not present in this pack: {superseded_by}",
            )

    _check_counter_coverage(
        expected=expected_obligations,
        observed=observed_obligations,
        errors=errors,
        missing_code="missing_obligation_mapping",
        dangling_code="dangling_obligation_ref",
        duplicate_code="duplicate_obligation_mapping",
        noun="profile obligation",
    )
    _check_counter_coverage(
        expected=expected_direct_rules,
        observed=observed_direct_rules,
        errors=errors,
        missing_code="missing_direct_rule_mapping",
        dangling_code="dangling_direct_rule_ref",
        duplicate_code="duplicate_direct_rule_mapping",
        noun="local direct rule",
    )

    for source_id in sorted(set(source_ids) - used_sources):
        _error(
            errors,
            "unmapped_source",
            "$.sources",
            f"source has no rule mapping: {source_id}",
        )

    if pack["standards_conformance_claimed"]:
        _error(
            errors,
            "unsupported_standards_conformance_claim",
            "$.standards_conformance_claimed",
            "this partial candidate register cannot claim standards conformance",
        )
    if pack["status"] != "adopted" and pack["runtime_authority"] != "none":
        _error(
            errors,
            "pack_runtime_authority_without_adoption",
            "$.runtime_authority",
            "unadopted pack must have runtime_authority=none",
        )
    if pack["status"] == "adopted":
        if independent_review["status"] != "completed" or human_adoption["status"] != "completed":
            _error(
                errors,
                "pack_adoption_evidence_missing",
                "$.governance",
                "adopted pack requires completed independent review and human adoption",
            )
        if any(rule["adoption_state"] != "adopted" for rule in rules):
            _error(
                errors,
                "pack_rule_adoption_mismatch",
                "$.rules",
                "an adopted pack cannot contain unadopted rules",
            )
    elif any(rule["adoption_state"] == "adopted" for rule in rules):
        _error(
            errors,
            "rule_adopted_inside_unadopted_pack",
            "$.rules",
            "an unadopted pack cannot contain an adopted rule",
        )

    return {
        "sources": len(sources),
        "rules": len(rules),
        "profile_obligations": len(expected_obligations),
        "local_direct_rules": len(expected_direct_rules),
        "mapped_source_refs": sum(len(rule["source_refs"]) for rule in rules),
    }


def validate(pack_path: Path, schema_path: Path) -> tuple[dict[str, Any], int]:
    errors: list[dict[str, str]] = []
    counts = {
        "sources": 0,
        "rules": 0,
        "profile_obligations": 0,
        "local_direct_rules": 0,
        "mapped_source_refs": 0,
    }
    checks = {"schema": "not_run", "mapping": "not_run", "governance": "not_run"}
    try:
        schema = _load_json(schema_path)
        Draft202012Validator.check_schema(schema)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, SchemaError) as exc:
        _error(errors, "schema_load_failed", str(schema_path), str(exc))
        result = {
            "schema_version": RESULT_VERSION,
            "status": "failed",
            "subject": {"pack_path": str(pack_path), "schema_path": str(schema_path)},
            "checks": checks,
            "counts": counts,
            "errors": errors,
        }
        return result, 1

    try:
        pack = _load_json(pack_path)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        _error(errors, "pack_load_failed", str(pack_path), str(exc))
        result = {
            "schema_version": RESULT_VERSION,
            "status": "failed",
            "subject": {"pack_path": str(pack_path), "schema_path": str(schema_path)},
            "checks": checks,
            "counts": counts,
            "errors": errors,
        }
        return result, 1

    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    for failure in sorted(validator.iter_errors(pack), key=lambda item: list(item.path)):
        _error(
            errors,
            "schema_validation_failed",
            _location(failure.path),
            failure.message,
        )
    if errors:
        checks["schema"] = "failed"
    else:
        checks["schema"] = "passed"
        try:
            counts = _semantic_validate(pack, errors)
        except (OSError, UnicodeError, SyntaxError, ValueError) as exc:
            _error(errors, "local_source_inspection_failed", "$", str(exc))
        checks["mapping"] = "failed" if errors else "passed"
        checks["governance"] = "failed" if errors else "passed"

    subject: dict[str, Any] = {
        "pack_path": str(pack_path),
        "schema_path": str(schema_path),
    }
    if pack_path.is_file():
        subject["pack_sha256"] = _sha256(pack_path)
    if schema_path.is_file():
        subject["schema_sha256"] = _sha256(schema_path)
    result = {
        "schema_version": RESULT_VERSION,
        "status": "failed" if errors else "ok",
        "subject": subject,
        "checks": checks,
        "counts": counts,
        "errors": errors,
    }
    return result, 1 if errors else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fail-closed validation for the engineering rule-pack candidate register."
    )
    parser.add_argument("--pack", type=Path, default=DEFAULT_PACK)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    arguments = parser.parse_args(argv)
    result, exit_code = validate(arguments.pack.resolve(), arguments.schema.resolve())
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
