"""Fail-closed adapters from the saved v0 candidates into H1/H2 v1 records.

The two saved candidate artifacts predate the governed H1 and H2 contracts.
This module preserves their meaning and provenance while constructing the
candidate-only records required by the current resolvers.  It never invents
human adoption, independent review, implementation verification, source-text
authenticity, applicability decisions, or formal authority.

A caller-supplied content-addressed reference proves only that the supplied
bytes or canonical document match that reference.  It is not an external
trust root.  Default repository paths are additionally pinned to the exact
candidate bytes reviewed when this adapter version was created.
"""

from __future__ import annotations

import ast
import copy
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable, Mapping, Sequence

from jsonschema import Draft202012Validator, FormatChecker

from .engineering_rule_governance import (
    CANDIDATE_AUTHORITY,
    build_candidate_review,
    build_governance_bundle,
    build_implementation_binding,
    build_pack_manifest,
    build_pending_human_decision,
    build_rule_basis,
    build_runtime_request,
    build_runtime_rule_request,
    sha256_bytes,
    sha256_digest,
    validate_governance_bundle,
)
from .lifecycle_governance import (
    CORE_STAGES,
    _digest as lifecycle_digest,
    assess_candidate_lifecycle_runtime,
    build_applicability_record,
    build_runtime_rule_binding,
    build_stage_profile,
    build_stage_registry,
    build_tailoring,
    profile_ref,
    validate_runtime_resolution,
    validate_runtime_rule_binding,
    validate_stage_profile,
    validate_stage_registry,
    validate_tailoring,
)
from .lifecycle_profiles import (
    LifecycleProfileRegistryValidationError,
    validate_lifecycle_profile_registry,
)
from .schema_access import schema_path


H1_ADAPTER_VERSION = "engineering-rule-pack-candidate-adapter/v1"
H2_ADAPTER_VERSION = "lifecycle-profile-registry-candidate-adapter/v1"

_PINNED_H1_SOURCE_REF: dict[str, Any] = {
    "record_id": "engineering-rule-pack.functional-requirement-record.candidate",
    "locator": "validation/engineering-rule-pack.candidate.json",
    "content_digest": {
        "algorithm": "sha256",
        "value": "ef19b8e287d2a80f529c462b0bbc4e3623118e2d8b44e5aba10f0fb7a255da57",
    },
}
_PINNED_H2_SOURCE_REF: dict[str, Any] = {
    "record_id": "lifecycle-profile-registry.semantic-guard-vnext.candidate",
    "locator": "validation/lifecycle-profile-registry.candidate.json",
    "content_digest": {
        "algorithm": "sha256",
        "value": "380559e15e5bfbf113b0f2b45ce260f2e3ee1a9e674b51f232c0db875290eb59",
    },
}
DEFAULT_H1_SOURCE_REF: dict[str, Any] = copy.deepcopy(_PINNED_H1_SOURCE_REF)
DEFAULT_H2_SOURCE_REF: dict[str, Any] = copy.deepcopy(_PINNED_H2_SOURCE_REF)

_H1_CANDIDATE_NAME = "engineering-rule-pack.candidate.json"
_H1_CANDIDATE_SCHEMA_NAME = "engineering-rule-pack.schema.json"
_H2_CANDIDATE_NAME = "lifecycle-profile-registry.candidate.json"
_ADAPTER_SCHEMA_NAME = "candidate-governance-adapters.schema.json"
_DIRECT_RULE_LOCATOR = "vnext/src/semantic_guard_vnext/direct_rules.py"
_PROFILE_LOCATOR = "vnext/src/semantic_guard_vnext/profiles.py"
_OBLIGATION_PATTERN = re.compile(r"^func\.[a-z0-9_]+$")
_DIRECT_RULE_PATTERN = re.compile(r"^direct\.[a-z0-9.-]+/v[0-9]+$")

_H1_UNRESOLVED_CODES = (
    "external_source_text_not_content_addressed",
    "external_trust_control_not_integrated",
    "human_adoption_pending",
    "implementation_verification_missing",
    "independent_review_not_performed",
    "required_obligations_unassessed",
    "runtime_profile_unresolved",
)
_H2_UNRESOLVED_CODES = (
    "engineering_basis_not_bound_to_adopted_rules",
    "external_trust_control_not_integrated",
    "human_adoption_pending",
    "implementation_binding_missing",
    "manifest_contracts_not_formally_defined",
    "stage_applicability_unresolved",
    "tailoring_decision_missing",
)


class CandidateGovernanceAdapterError(ValueError):
    """Raised when an old candidate cannot be mapped exactly and safely."""


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _copy(value: Mapping[str, Any]) -> dict[str, Any]:
    return copy.deepcopy(dict(value))


def _without(value: Mapping[str, Any], *fields: str) -> dict[str, Any]:
    result = _copy(value)
    for field in fields:
        result.pop(field, None)
    return result


def _bytes_digest(value: bytes) -> dict[str, str]:
    return {"algorithm": "sha256", "value": hashlib.sha256(value).hexdigest()}


def _record_ref(record_id: str, locator: str, value: Any) -> dict[str, Any]:
    return {
        "record_id": record_id,
        "locator": locator,
        "content_digest": sha256_digest(value),
    }


def _digest_ref(
    record_id: str, locator: str, digest: Mapping[str, Any]
) -> dict[str, Any]:
    return {
        "record_id": record_id,
        "locator": locator,
        "content_digest": _copy(digest),
    }


def _conversion_digest(value: Mapping[str, Any]) -> dict[str, str]:
    return sha256_digest(_without(value, "conversion_digest"))


def _stable_unique(values: Iterable[str], label: str) -> list[str]:
    result = list(values)
    if any(not isinstance(value, str) or not value for value in result):
        raise CandidateGovernanceAdapterError(
            f"{label} values must be non-empty strings"
        )
    if len(result) != len(set(result)):
        raise CandidateGovernanceAdapterError(f"duplicate {label}")
    return result


def _validation_path(name: str) -> Path:
    here = Path(__file__).resolve()
    packaged = here.parent / "validation" / name
    if packaged.is_file():
        return packaged
    raise CandidateGovernanceAdapterError(
        f"candidate validation artifact is unavailable: {name}"
    )


def _default_candidate_path(name: str) -> Path:
    return _validation_path(name)


@lru_cache(maxsize=1)
def candidate_governance_adapter_schema() -> dict[str, Any]:
    schema = json.loads(schema_path(_ADAPTER_SCHEMA_NAME).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return schema


@lru_cache(maxsize=None)
def _adapter_validator(definition: str) -> Draft202012Validator:
    root = candidate_governance_adapter_schema()
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$defs": root["$defs"],
        "$ref": f"#/$defs/{definition}",
    }
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _schema_validate(value: Mapping[str, Any], definition: str, label: str) -> None:
    failures = sorted(
        _adapter_validator(definition).iter_errors(value),
        key=lambda item: tuple(str(part) for part in item.absolute_path),
    )
    if failures:
        failure = failures[0]
        location = "/".join(str(part) for part in failure.absolute_path) or "/"
        raise CandidateGovernanceAdapterError(
            f"{label} schema violation at {location}: {failure.message}"
        )


def _validate_record_ref(value: Mapping[str, Any], label: str) -> dict[str, Any]:
    copied = _copy(value)
    _schema_validate(copied, "recordRef", label)
    return copied


def _schema_file_ref(path: Path, record_id: str, locator: str) -> dict[str, Any]:
    content = path.read_bytes()
    return {
        "record_id": record_id,
        "locator": locator,
        "content_digest": _bytes_digest(content),
    }


def _canonical_document_ref(
    source_ref: Mapping[str, Any], document: Mapping[str, Any]
) -> dict[str, Any]:
    return {
        "record_id": f"{source_ref['record_id']}.canonical",
        "locator": f"{source_ref['locator']}#canonical-json",
        "content_digest": _bytes_digest(_canonical(document)),
    }


def _document_transport(
    document: Mapping[str, Any], source_ref: Mapping[str, Any]
) -> dict[str, Any]:
    supplied = _validate_record_ref(source_ref, "candidate document source ref")
    expected = _bytes_digest(_canonical(document))
    if supplied["content_digest"] != expected:
        raise CandidateGovernanceAdapterError(
            "candidate document does not match its canonical source_ref"
        )
    return {
        "kind": "canonical_document",
        "supplied_ref": supplied,
        "canonical_document_ref": copy.deepcopy(supplied),
        "authenticity_state": "unresolved",
        "trust_effect": "none",
    }


def _bytes_transport(
    content: bytes,
    source_ref: Mapping[str, Any],
    *,
    kind: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(content, bytes):
        raise TypeError("candidate content must be bytes")
    supplied = _validate_record_ref(source_ref, "candidate byte source ref")
    if supplied["content_digest"] != _bytes_digest(content):
        raise CandidateGovernanceAdapterError(
            "candidate bytes do not match the expected source_ref"
        )
    try:
        document = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CandidateGovernanceAdapterError(
            "candidate bytes are not UTF-8 JSON"
        ) from exc
    if not isinstance(document, dict):
        raise CandidateGovernanceAdapterError("candidate JSON root must be an object")
    transport = {
        "kind": kind,
        "supplied_ref": supplied,
        "canonical_document_ref": _canonical_document_ref(supplied, document),
        "authenticity_state": "unresolved",
        "trust_effect": "none",
    }
    return document, transport


def _read_pinned_path(
    path: str | Path | None,
    *,
    default_name: str,
    default_ref: Mapping[str, Any],
    expected_source_ref: Mapping[str, Any] | None,
) -> tuple[dict[str, Any], dict[str, Any], bytes, Path]:
    target = _default_candidate_path(default_name) if path is None else Path(path)
    if path is not None and expected_source_ref is None:
        raise CandidateGovernanceAdapterError(
            "a non-default candidate path requires an expected_source_ref"
        )
    expected = default_ref if expected_source_ref is None else expected_source_ref
    first = target.read_bytes()
    second = target.read_bytes()
    if first != second:
        raise CandidateGovernanceAdapterError("candidate file changed while being read")
    document, transport = _bytes_transport(first, expected, kind="path_bytes")
    return document, transport, first, target


def _validate_transport_against_source(
    transport: Mapping[str, Any],
    document: Mapping[str, Any],
    source_bytes: bytes | None,
) -> None:
    _schema_validate(transport, "sourceTransport", "candidate source transport")
    canonical = _bytes_digest(_canonical(document))
    if transport["canonical_document_ref"]["content_digest"] != canonical:
        raise CandidateGovernanceAdapterError("canonical document digest mismatch")
    kind = transport["kind"]
    if kind == "canonical_document":
        if transport["supplied_ref"] != transport["canonical_document_ref"]:
            raise CandidateGovernanceAdapterError(
                "canonical document transport refs differ"
            )
        return
    if source_bytes is None:
        raise CandidateGovernanceAdapterError(
            "byte/path adapter validation requires the original source bytes"
        )
    if transport["supplied_ref"]["content_digest"] != _bytes_digest(source_bytes):
        raise CandidateGovernanceAdapterError("source byte digest mismatch")
    try:
        replay = json.loads(source_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CandidateGovernanceAdapterError(
            "source bytes are not replayable JSON"
        ) from exc
    if replay != document:
        raise CandidateGovernanceAdapterError(
            "source bytes and canonical source document differ"
        )


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
        values = {item.arg: item.value for item in node.value.keywords if item.arg}
        profile_id = values.get("profile_id")
        version = values.get("version")
        if (
            isinstance(profile_id, ast.Constant)
            and isinstance(profile_id.value, str)
            and isinstance(version, ast.Constant)
            and isinstance(version.value, str)
        ):
            return profile_id.value, version.value
        break
    raise CandidateGovernanceAdapterError(
        "FUNCTIONAL_REQUIREMENT_PROFILE identity is not statically readable"
    )


def _validate_h1_candidate(document: Mapping[str, Any]) -> dict[str, Any]:
    schema_file = _validation_path(_H1_CANDIDATE_SCHEMA_NAME)
    schema = json.loads(schema_file.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    failures = sorted(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(
            document
        ),
        key=lambda item: tuple(str(part) for part in item.absolute_path),
    )
    if failures:
        failure = failures[0]
        location = "/".join(str(part) for part in failure.absolute_path) or "/"
        raise CandidateGovernanceAdapterError(
            f"engineering-rule candidate schema violation at {location}: "
            f"{failure.message}"
        )
    candidate = _copy(document)
    if candidate.get("$schema") != "./engineering-rule-pack.schema.json":
        raise CandidateGovernanceAdapterError(
            "engineering-rule schema ref is not exact"
        )
    if (
        candidate["status"] != "candidate_pending_human_adoption"
        or candidate["runtime_authority"] != "none"
        or candidate["standards_conformance_claimed"] is not False
    ):
        raise CandidateGovernanceAdapterError(
            "engineering-rule candidate exceeds its candidate-only boundary"
        )
    governance = candidate["governance"]
    for field in ("independent_review", "human_adoption"):
        if governance[field] != {
            "status": "not_performed",
            "evidence_refs": [],
            "authority_ref": None,
        }:
            raise CandidateGovernanceAdapterError(
                f"candidate {field} cannot be promoted by the adapter"
            )

    package_dir = Path(__file__).resolve().parent
    direct_rule_path = package_dir / "direct_rules.py"
    profile_path = package_dir / "profiles.py"
    expected_obligations = _ast_string_set(profile_path, _OBLIGATION_PATTERN)
    expected_direct_rules = _ast_string_set(direct_rule_path, _DIRECT_RULE_PATTERN)
    expected_profile = _profile_identity(profile_path)
    profile = candidate["profile"]
    if (
        profile["local_locator"] != _PROFILE_LOCATOR
        or (profile["profile_id"], profile["version"]) != expected_profile
    ):
        raise CandidateGovernanceAdapterError(
            "candidate profile identity does not exactly match the local profile"
        )

    sources = list(candidate["sources"])
    source_ids = _stable_unique(
        (item["source_id"] for item in sources), "candidate source id"
    )
    source_by_id = dict(zip(source_ids, sources, strict=True))
    rules = list(candidate["rules"])
    keys = _stable_unique(
        (f"{item['rule_id']}@{item['version']}" for item in rules),
        "candidate rule identity",
    )
    del keys
    observed_obligations: list[str] = []
    observed_direct_rules: list[str] = []
    for rule in rules:
        if (
            rule["adoption_state"] != "candidate_pending_human_adoption"
            or rule["runtime_authority"] != "none"
            or rule["adoption_evidence_refs"]
            or rule["independent_review_evidence_refs"]
        ):
            raise CandidateGovernanceAdapterError(
                f"candidate rule {rule['rule_id']} exceeds candidate-only authority"
            )
        observed_obligations.extend(rule["profile_obligation_refs"])
        if len(rule["profile_obligation_refs"]) != 1:
            raise CandidateGovernanceAdapterError(
                "each candidate engineering rule must map exactly one obligation"
            )
        obligation = str(rule["profile_obligation_refs"][0])
        expected_rule_id = "engineering.functional." + obligation.removeprefix(
            "func."
        ).replace("_", "-")
        if rule["rule_id"] != expected_rule_id or rule["version"] != "v0":
            raise CandidateGovernanceAdapterError(
                "candidate engineering-rule identity is not the exact "
                "obligation-derived v0 identity"
            )
        observed_direct_rules.extend(
            item["rule_id"] for item in rule["local_implementation_rule_refs"]
        )
        _stable_unique(rule["profile_obligation_refs"], "profile obligation ref")
        _stable_unique(
            (item["rule_id"] for item in rule["local_implementation_rule_refs"]),
            "local implementation rule ref",
        )
        referenced_sources = _stable_unique(
            (
                f"{item['source_id']}::{item['section_locator']}"
                for item in rule["source_refs"]
            ),
            "rule source-section ref",
        )
        for source_ref in rule["source_refs"]:
            source = source_by_id.get(source_ref["source_id"])
            if source is None:
                raise CandidateGovernanceAdapterError(
                    f"dangling source id: {source_ref['source_id']}"
                )
            if source_ref["section_locator"] not in source["section_locators"]:
                raise CandidateGovernanceAdapterError(
                    "source section locator does not exactly match its source entry"
                )
        del referenced_sources

    if len(observed_obligations) != len(set(observed_obligations)):
        raise CandidateGovernanceAdapterError(
            "candidate repeats a profile-obligation mapping"
        )
    if set(observed_obligations) != expected_obligations:
        raise CandidateGovernanceAdapterError(
            "candidate profile-obligation denominator is not exact"
        )
    if len(observed_direct_rules) != len(set(observed_direct_rules)):
        raise CandidateGovernanceAdapterError(
            "candidate repeats a local direct-rule mapping"
        )
    if set(observed_direct_rules) != expected_direct_rules:
        raise CandidateGovernanceAdapterError(
            "candidate direct-rule denominator is not exact"
        )
    return candidate


def _h1_schema_ref() -> dict[str, Any]:
    return _schema_file_ref(
        _validation_path(_H1_CANDIDATE_SCHEMA_NAME),
        "schema.engineering-rule-pack.candidate.v0",
        "validation/engineering-rule-pack.schema.json",
    )


def _h1_source_entry_refs(
    candidate: Mapping[str, Any], canonical_ref: Mapping[str, Any]
) -> list[dict[str, Any]]:
    return [
        _record_ref(
            f"candidate-source-entry.{source['source_id']}",
            f"{canonical_ref['locator']}#/sources/{index}",
            source,
        )
        for index, source in enumerate(candidate["sources"])
    ]


def _build_h1_adapter_result(
    candidate: Mapping[str, Any],
    source_transport: Mapping[str, Any],
    *,
    obligation_assessment_digest: Mapping[str, Any] | None,
    authority_source_ids: Sequence[str],
) -> dict[str, Any]:
    candidate = _validate_h1_candidate(candidate)
    transport = copy.deepcopy(dict(source_transport))
    canonical_ref = transport["canonical_document_ref"]
    authority_ids = sorted(_stable_unique(authority_source_ids, "authority source id"))
    if obligation_assessment_digest is None:
        assessment_digest = sha256_digest(
            {
                "state": "unassessed_candidate_conversion",
                "candidate_document_digest": canonical_ref["content_digest"],
                "authority_source_ids": authority_ids,
            }
        )
    else:
        assessment_digest = _copy(obligation_assessment_digest)
        _schema_validate(
            {
                "record_id": "obligation-assessment.digest-check",
                "locator": "urn:obligation-assessment:digest-check",
                "content_digest": assessment_digest,
            },
            "recordRef",
            "obligation assessment digest",
        )

    sources = list(candidate["sources"])
    source_by_id = {str(item["source_id"]): item for item in sources}
    source_indexes = {
        str(item["source_id"]): index for index, item in enumerate(sources)
    }
    direct_rule_path = Path(__file__).resolve().parent / "direct_rules.py"
    direct_rule_content = direct_rule_path.read_bytes()
    direct_rule_digest = sha256_bytes(direct_rule_content)
    bases: list[dict[str, Any]] = []
    reviews: list[dict[str, Any]] = []
    implementations: list[dict[str, Any]] = []

    for index, rule in enumerate(candidate["rules"]):
        source_bindings: list[dict[str, Any]] = []
        for source_ref in rule["source_refs"]:
            source = source_by_id[str(source_ref["source_id"])]
            source_index = source_indexes[str(source_ref["source_id"])]
            source_bindings.append(
                {
                    "source_id": source["source_id"],
                    "source_version": source["version"],
                    "locator": f"{canonical_ref['locator']}#/sources/{source_index}",
                    "section_locator": source_ref["section_locator"],
                    # This digest addresses the candidate metadata entry, not
                    # the external source text.  The unverified status and
                    # required limitation keep that distinction explicit.
                    "content_digest": sha256_digest(source),
                    "binding_status": "unverified",
                }
            )
        exceptions = [
            {
                "exception_id": f"exception.{rule['rule_id']}.{item_index + 1}",
                "condition": condition,
                "effect": "unresolved",
            }
            for item_index, condition in enumerate(rule["counterconditions"])
        ]
        basis = build_rule_basis(
            rule_id=str(rule["rule_id"]),
            # The governed contract deliberately excludes legacy v0 rule
            # versions.  This is a new candidate v1 basis derived from the
            # exact v0 entry; the mapping below preserves the source version.
            rule_version="v1",
            artifact_locator=(
                f"{canonical_ref['locator']}#/rules/{index}:canonical-json"
            ),
            artifact_content=_canonical(rule),
            engineering_proposition=str(rule["engineering_proposition"]),
            interpretation=str(rule["interpretation"]),
            required_evidence=list(rule["required_evidence"]),
            limitations=[
                *rule["limitations"],
                "Adapter source-binding digests address candidate metadata entries only; external exact source text remains unverified.",
                "Candidate local-rule correspondence is not implementation verification or engineering-rule adoption.",
            ],
            source_bindings=source_bindings,
            applicability_scope_ids=list(rule["profile_obligation_refs"]),
            applicability_conditions=list(rule["applicability"]),
            exceptions=exceptions,
            requested_authority=CANDIDATE_AUTHORITY,
        )
        local_ref = rule["local_implementation_rule_refs"][0]
        implementation = build_implementation_binding(
            binding_id=f"binding.{rule['rule_id']}.{rule['version']}.candidate",
            basis=basis,
            implementation_id=str(local_ref["rule_id"]),
            implementation_version=str(local_ref["rule_id"]).rsplit("/", 1)[-1],
            entry_point=str(local_ref["rule_id"]),
            artifacts=[
                {
                    "locator": _DIRECT_RULE_LOCATOR,
                    "content_digest": direct_rule_digest,
                }
            ],
            implementation_status="partially_implemented",
            verification_evidence_refs=[],
        )
        review = build_candidate_review(
            review_id=f"review.{rule['rule_id']}.{rule['version']}.adapter",
            basis=basis,
            reviewer_ref="semantic-guard.candidate-adapter.h1",
            reviewer_kind="tool",
            review_independence="self_review",
            reviewer_qualification_refs=[],
            audit_assessment="adoption_not_ready",
            finding_refs=[
                f"finding.{rule['rule_id']}.external-source-unverified",
                f"finding.{rule['rule_id']}.human-adoption-pending",
            ],
            evidence_status="unverified",
            non_binding_recommendation="request_revision",
            recommendation_rationale=(
                "The v0 candidate supplies useful engineering propositions but "
                "not exact external source text, independent review, human "
                "adoption, or verified implementation evidence."
            ),
            review_evidence_refs=[],
        )
        bases.append(basis)
        implementations.append(implementation)
        reviews.append(review)

    manifest = build_pack_manifest(
        pack_id=str(candidate["pack_id"]),
        pack_version="v1",
        subject_scope_ids=[str(candidate["profile"]["profile_id"])],
        required_bases=bases,
    )
    decisions = [
        build_pending_human_decision(
            decision_id=f"decision.{basis['rule_id']}.{basis['rule_version']}.pending",
            target_kind="rule",
            target_id=str(basis["rule_id"]),
            target_version=str(basis["rule_version"]),
            target_digest=basis["basis_digest"],
            pack_manifest=manifest,
            decision_owner_ref="human.engineering-rule-adopter.unspecified",
            rationale=(
                "The saved v0 candidate records no completed human adoption for "
                "this exact governed basis."
            ),
        )
        for basis in bases
    ]
    h1_decision = build_pending_human_decision(
        decision_id="decision.H1.engineering-rule-pack.pending",
        target_kind="h1_gate",
        target_id="H1",
        target_version="v1",
        target_digest=manifest["manifest_digest"],
        pack_manifest=manifest,
        decision_owner_ref="human.engineering-rule-pack-owner.unspecified",
        rationale=(
            "H1 remains pending because rule-level adoption and external trust "
            "controls are absent from the saved candidate."
        ),
    )
    decisions.append(h1_decision)
    rule_requests = [
        build_runtime_rule_request(
            basis=basis,
            implementation_binding=implementation,
            requested_authority=CANDIDATE_AUTHORITY,
            observed_artifact_digest=basis["artifact_digest"],
            observed_implementation_digest=implementation["implementation_digest"],
        )
        for basis, implementation in zip(bases, implementations, strict=True)
    ]
    runtime_request = build_runtime_request(
        request_id=f"runtime-request.h1-adapter.{canonical_ref['content_digest']['value'][:24]}",
        subject_scope_id=str(candidate["profile"]["profile_id"]),
        profile_id=str(candidate["profile"]["profile_id"]),
        profile_version=str(candidate["profile"]["version"]),
        profile_basis_digest=sha256_digest(candidate["profile"]),
        profile_resolution_status="candidate_only",
        evidence_currency="unbound",
        all_required_obligations_satisfied=False,
        obligation_assessment_digest=assessment_digest,
        rule_requests=rule_requests,
    )
    bundle = build_governance_bundle(
        bundle_id=f"bundle.h1-candidate-adapter.{canonical_ref['content_digest']['value'][:24]}",
        bundle_version="v1",
        rule_bases=bases,
        reviews=reviews,
        human_decisions=decisions,
        implementation_bindings=implementations,
        pack_manifest=manifest,
        runtime_request=runtime_request,
        resolution_id=f"resolution.h1-candidate-adapter.{canonical_ref['content_digest']['value'][:24]}",
    )

    decision_by_key = {
        (item["target_id"], item["target_version"]): item
        for item in decisions
        if item["target_kind"] == "rule"
    }
    review_by_key = {
        (item["rule_ref"]["rule_id"], item["rule_ref"]["rule_version"]): item
        for item in reviews
    }
    implementation_by_key = {
        (item["rule_ref"]["rule_id"], item["rule_ref"]["rule_version"]): item
        for item in implementations
    }
    rule_mappings: list[dict[str, Any]] = []
    for index, (rule, basis) in enumerate(zip(candidate["rules"], bases, strict=True)):
        key = (basis["rule_id"], basis["rule_version"])
        review = review_by_key[key]
        implementation = implementation_by_key[key]
        decision = decision_by_key[key]
        mapping: dict[str, Any] = {
            "input_rule_ref": _record_ref(
                f"candidate-rule-entry.{rule['rule_id']}.{rule['version']}",
                f"{canonical_ref['locator']}#/rules/{index}",
                rule,
            ),
            "basis_ref": {
                "rule_id": basis["rule_id"],
                "rule_version": basis["rule_version"],
                "basis_digest": copy.deepcopy(basis["basis_digest"]),
                "record_digest": copy.deepcopy(basis["record_digest"]),
            },
            "review_ref": _digest_ref(
                review["review_id"],
                f"urn:engineering-rule-review:{review['review_id']}",
                review["review_digest"],
            ),
            "implementation_ref": _digest_ref(
                implementation["binding_id"],
                f"urn:engineering-rule-implementation:{implementation['binding_id']}",
                implementation["binding_digest"],
            ),
            "pending_decision_ref": _digest_ref(
                decision["decision_id"],
                f"urn:engineering-rule-decision:{decision['decision_id']}",
                decision["decision_digest"],
            ),
            "unresolved_codes": list(_H1_UNRESOLVED_CODES),
        }
        mapping["conversion_digest"] = _conversion_digest(mapping)
        rule_mappings.append(mapping)

    resolution = bundle["runtime_resolution"]
    material: dict[str, Any] = {
        "schema_version": H1_ADAPTER_VERSION,
        "adapter_id": f"adapter.h1.{canonical_ref['content_digest']['value'][:24]}",
        "source_transport": transport,
        "input_schema_ref": _h1_schema_ref(),
        "obligation_assessment_digest": assessment_digest,
        "authority_source_ids": authority_ids,
        "source_entry_refs": _h1_source_entry_refs(candidate, canonical_ref),
        "rule_mappings": rule_mappings,
        "governance_bundle": bundle,
        "resolver_ref": {
            "record_id": resolution["resolution_id"],
            "content_digest": copy.deepcopy(resolution["resolution_digest"]),
        },
        "adapter_state": "candidate_with_unresolved_prerequisites",
        "formal_authority": "none",
        "unresolved_codes": list(_H1_UNRESOLVED_CODES),
    }
    return {**material, "adapter_digest": sha256_digest(material)}


def validate_engineering_rule_pack_adapter_result(
    result: Mapping[str, Any],
    *,
    source_document: Mapping[str, Any],
    source_bytes: bytes | None = None,
) -> dict[str, Any]:
    """Replay an H1 adapter result against the exact source document.

    Byte/path results additionally require the original bytes.  This prevents
    a canonical reserialization from being mistaken for the pinned file that
    was actually read.
    """

    copied = _copy(result)
    _schema_validate(copied, "h1AdapterResult", "H1 candidate adapter result")
    if copied["adapter_digest"] != sha256_digest(_without(copied, "adapter_digest")):
        raise CandidateGovernanceAdapterError("H1 adapter digest mismatch")
    _validate_transport_against_source(
        copied["source_transport"], source_document, source_bytes
    )
    candidate = _validate_h1_candidate(source_document)
    expected_schema_ref = _h1_schema_ref()
    if copied["input_schema_ref"] != expected_schema_ref:
        raise CandidateGovernanceAdapterError("H1 input schema ref mismatch")
    validate_governance_bundle(copied["governance_bundle"])
    rebuilt = _build_h1_adapter_result(
        candidate,
        copied["source_transport"],
        obligation_assessment_digest=copied["obligation_assessment_digest"],
        authority_source_ids=copied["authority_source_ids"],
    )
    if copied != rebuilt:
        raise CandidateGovernanceAdapterError(
            "H1 adapter result does not replay from the exact candidate"
        )
    resolution = copied["governance_bundle"]["runtime_resolution"]
    if (
        resolution["pack_resolution"]["formal_verdict_authority"] != "none"
        or copied["governance_bundle"]["h1_gate_view"]["human_decision"] != "pending"
        or copied["governance_bundle"]["h1_gate_view"]["verdict_authority"] != "none"
        or copied["formal_authority"] != "none"
    ):
        raise CandidateGovernanceAdapterError(
            "H1 candidate adapter attempted a formal or human-decision promotion"
        )
    return copied


def adapt_engineering_rule_pack_document(
    document: Mapping[str, Any],
    *,
    source_ref: Mapping[str, Any],
    obligation_assessment_digest: Mapping[str, Any] | None = None,
    authority_source_ids: Sequence[str] = (),
) -> dict[str, Any]:
    """Adapt a canonical in-memory candidate document without trusting it."""

    candidate = _copy(document)
    transport = _document_transport(candidate, source_ref)
    result = _build_h1_adapter_result(
        candidate,
        transport,
        obligation_assessment_digest=obligation_assessment_digest,
        authority_source_ids=authority_source_ids,
    )
    return validate_engineering_rule_pack_adapter_result(
        result, source_document=candidate
    )


def adapt_engineering_rule_pack_bytes(
    content: bytes,
    *,
    source_ref: Mapping[str, Any],
    obligation_assessment_digest: Mapping[str, Any] | None = None,
    authority_source_ids: Sequence[str] = (),
) -> dict[str, Any]:
    """Adapt exact candidate bytes bound to a caller-supplied reference."""

    candidate, transport = _bytes_transport(content, source_ref, kind="bytes")
    result = _build_h1_adapter_result(
        candidate,
        transport,
        obligation_assessment_digest=obligation_assessment_digest,
        authority_source_ids=authority_source_ids,
    )
    return validate_engineering_rule_pack_adapter_result(
        result, source_document=candidate, source_bytes=content
    )


def adapt_engineering_rule_pack_candidate(
    path: str | Path | None = None,
    *,
    expected_source_ref: Mapping[str, Any] | None = None,
    obligation_assessment_digest: Mapping[str, Any] | None = None,
    authority_source_ids: Sequence[str] = (),
) -> dict[str, Any]:
    """Adapt the pinned repository candidate, or an explicitly pinned path."""

    candidate, transport, content, _ = _read_pinned_path(
        path,
        default_name=_H1_CANDIDATE_NAME,
        default_ref=_PINNED_H1_SOURCE_REF,
        expected_source_ref=expected_source_ref,
    )
    result = _build_h1_adapter_result(
        candidate,
        transport,
        obligation_assessment_digest=obligation_assessment_digest,
        authority_source_ids=authority_source_ids,
    )
    return validate_engineering_rule_pack_adapter_result(
        result, source_document=candidate, source_bytes=content
    )


def load_default_engineering_rule_pack_candidate() -> tuple[
    dict[str, Any], bytes, dict[str, Any]
]:
    """Return the pinned default H1 candidate, exact bytes, and raw file ref.

    Loading and digest agreement establish repository-resource identity only.
    The returned reference has no adoption, authenticity, or runtime-authority
    effect.  Copies are returned so callers cannot mutate a cached source.
    """

    candidate, transport, content, _ = _read_pinned_path(
        None,
        default_name=_H1_CANDIDATE_NAME,
        default_ref=_PINNED_H1_SOURCE_REF,
        expected_source_ref=None,
    )
    return _copy(candidate), bytes(content), _copy(transport["supplied_ref"])


def _validate_h2_candidate(document: Mapping[str, Any]) -> dict[str, Any]:
    try:
        candidate = validate_lifecycle_profile_registry(document)
    except LifecycleProfileRegistryValidationError as exc:
        raise CandidateGovernanceAdapterError(
            f"lifecycle-profile candidate is not closed: {exc}"
        ) from exc
    if candidate.get("$schema") != "../schemas/lifecycle-profile-registry.schema.json":
        raise CandidateGovernanceAdapterError(
            "lifecycle-profile schema ref is not exact"
        )
    if tuple(candidate["stage_order"]) != CORE_STAGES:
        raise CandidateGovernanceAdapterError(
            "lifecycle-profile stage denominator is not exact"
        )
    profile_keys = _stable_unique(
        (f"{item['profile_id']}@{item['version']}" for item in candidate["profiles"]),
        "lifecycle profile identity",
    )
    del profile_keys
    if tuple(item["stage"] for item in candidate["profiles"]) != CORE_STAGES:
        raise CandidateGovernanceAdapterError(
            "lifecycle profiles do not exactly follow the core denominator"
        )
    return candidate


def _h2_schema_ref() -> dict[str, Any]:
    path = schema_path("lifecycle-profile-registry.schema.json")
    return _schema_file_ref(
        path,
        "schema.lifecycle-profile-registry.candidate.v0",
        "schemas/lifecycle-profile-registry.schema.json",
    )


def _canonical_strings(values: Sequence[Mapping[str, Any]]) -> list[str]:
    return [_canonical(item).decode("utf-8") for item in values]


def _h2_input_contract_material(profile: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "entry_conditions": copy.deepcopy(profile["entry_conditions"]),
        "required_semantic_fields": copy.deepcopy(profile["required_semantic_fields"]),
        "upstream_trace": copy.deepcopy(profile["upstream_trace"]),
    }


def _h2_output_contract_material(profile: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "exit_conditions": copy.deepcopy(profile["exit_conditions"]),
        "required_relationships": copy.deepcopy(profile["required_relationships"]),
        "downstream_trace": copy.deepcopy(profile["downstream_trace"]),
        "non_goals": copy.deepcopy(profile["non_goals"]),
        "hollow_success_conditions": copy.deepcopy(
            profile["hollow_success_conditions"]
        ),
        "human_acceptance_questions": copy.deepcopy(
            profile["human_acceptance_questions"]
        ),
        "unresolved": copy.deepcopy(profile["unresolved"]),
    }


def _h2_unresolved_basis(
    profile: Mapping[str, Any], canonical_ref: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    stage = str(profile["stage"])
    content_digest = lifecycle_digest(profile["obligation_templates"])
    basis_material = {
        "state": "unresolved_placeholder_not_engineering_rule",
        "stage_id": stage,
        "candidate_profile_digest": copy.deepcopy(profile["profile_digest"]),
        "candidate_obligation_content_digest": content_digest,
        "reason": (
            "The v0 lifecycle profile lists obligation templates and OR traces "
            "but does not bind this stage to an adopted, content-addressed "
            "engineering-rule denominator."
        ),
    }
    basis_digest = lifecycle_digest(basis_material)
    requirement = {
        "rule_id": f"unresolved.engineering-basis.{stage}",
        "rule_version": "candidate-1",
        "content_digest": content_digest,
        "basis_digest": basis_digest,
        "reported_adoption_status": "candidate",
        "human_adoption_ref": None,
        "applicability": (
            "Unresolved placeholder for the missing adopted engineering-rule "
            f"denominator of lifecycle stage {stage}; it is not an engineering rule."
        ),
        "required_authorities": [
            "candidate_finding",
            "unresolved_escalation",
        ],
    }
    basis_ref = _digest_ref(
        f"unresolved.engineering-basis.{stage}",
        f"{canonical_ref['locator']}#/profiles/{CORE_STAGES.index(stage)}/obligation_templates:unresolved-basis",
        basis_digest,
    )
    return requirement, basis_ref


def _build_h2_adapter_result(
    candidate: Mapping[str, Any],
    source_transport: Mapping[str, Any],
    *,
    subject_scope_ref: Mapping[str, Any] | None,
) -> dict[str, Any]:
    candidate = _validate_h2_candidate(candidate)
    transport = copy.deepcopy(dict(source_transport))
    canonical_ref = transport["canonical_document_ref"]
    subject_ref = (
        copy.deepcopy(canonical_ref)
        if subject_scope_ref is None
        else _validate_record_ref(subject_scope_ref, "lifecycle subject scope ref")
    )

    governed_profiles: list[dict[str, Any]] = []
    runtime_bindings: list[dict[str, Any]] = []
    profile_mappings: list[dict[str, Any]] = []
    core_profiles: dict[str, dict[str, Any]] = {}
    applicability_records: list[dict[str, Any]] = []
    tailoring_triggers: list[str] = []

    for index, profile in enumerate(candidate["profiles"]):
        stage = str(profile["stage"])
        input_material = _h2_input_contract_material(profile)
        output_material = _h2_output_contract_material(profile)
        input_contract_ref = _record_ref(
            f"candidate-profile-contract.{stage}.input",
            f"{canonical_ref['locator']}#/profiles/{index}:input-contract-projection",
            input_material,
        )
        output_contract_ref = _record_ref(
            f"candidate-profile-contract.{stage}.output",
            f"{canonical_ref['locator']}#/profiles/{index}:output-contract-projection",
            output_material,
        )
        requirement, unresolved_basis_ref = _h2_unresolved_basis(profile, canonical_ref)
        implementation_material = {
            "state": "unresolved_no_implementation_binding",
            "source_profile_id": profile["profile_id"],
            "source_profile_version": profile["version"],
            "source_profile_digest": copy.deepcopy(profile["profile_digest"]),
            "reason": (
                "The saved candidate profile identifies validation material but "
                "does not bind an executable implementation artifact."
            ),
        }
        implementation_digest = lifecycle_digest(implementation_material)
        validation_obligations = [
            *(
                f"validation_material:{value}"
                for value in _canonical_strings(profile["validation_materials"])
            ),
            *(
                f"verification_evidence_type:{value}"
                for value in _canonical_strings(profile["verification_evidence_types"])
            ),
        ]
        governed = build_stage_profile(
            profile_id=str(profile["profile_id"]),
            profile_version=str(profile["version"]),
            stage_id=stage,
            purpose=str(profile["purpose"]),
            entry_conditions=_canonical_strings(profile["entry_conditions"]),
            exit_conditions=_canonical_strings(profile["exit_conditions"]),
            applicability_policy=(
                "The saved profile is pending human adoption and contains no "
                "case-specific applicability decision; tailoring remains unresolved."
            ),
            input_manifest_contract=input_contract_ref,
            output_manifest_contract=output_contract_ref,
            obligations=_canonical_strings(profile["obligation_templates"]),
            engineering_basis_refs=[requirement],
            validation_obligations=validation_obligations,
            requalification_triggers=_canonical_strings(
                profile["requalification_triggers"]
            ),
            implementation_digest=implementation_digest,
            reported_adoption_status="candidate",
            human_adoption_ref=None,
        )
        binding = build_runtime_rule_binding(
            rule_id=str(requirement["rule_id"]),
            rule_version=str(requirement["rule_version"]),
            content_digest=requirement["content_digest"],
            basis_digest=requirement["basis_digest"],
            implementation_digest=implementation_digest,
            reported_adoption_status="candidate",
            human_adoption_ref=None,
            authority={
                "candidate_finding": True,
                "unresolved_escalation": True,
                "nonconformance": False,
                "satisfaction": False,
                "final_verdict": False,
            },
        )
        unresolved_material = {
            "stage_id": stage,
            "source_unresolved": copy.deepcopy(profile["unresolved"]),
            "adapter_unresolved_codes": list(_H2_UNRESOLVED_CODES),
        }
        unresolved_ref = _record_ref(
            f"unresolved.lifecycle-profile-adapter.{stage}",
            f"{canonical_ref['locator']}#/profiles/{index}/unresolved:adapter",
            unresolved_material,
        )
        applicability = build_applicability_record(
            stage_id=stage,
            reported_applicability_state="unresolved",
            unresolved_ref=unresolved_ref,
        )
        governed_profiles.append(governed)
        runtime_bindings.append(binding)
        core_profiles[stage] = governed
        applicability_records.append(applicability)
        tailoring_triggers.extend(
            _canonical_strings(profile["requalification_triggers"])
        )

        output_ref = profile_ref(governed, require_trusted_decisions=False)
        mapping: dict[str, Any] = {
            "input_profile_ref": _record_ref(
                f"candidate-profile-entry.{profile['profile_id']}.{profile['version']}",
                f"{canonical_ref['locator']}#/profiles/{index}",
                profile,
            ),
            "output_profile_ref": output_ref,
            "input_contract_ref": input_contract_ref,
            "output_contract_ref": output_contract_ref,
            "unresolved_basis_ref": unresolved_basis_ref,
            "runtime_rule_binding_ref": _digest_ref(
                f"runtime-binding.{requirement['rule_id']}.{requirement['rule_version']}",
                f"urn:lifecycle-runtime-rule:{requirement['rule_id']}:{requirement['rule_version']}",
                binding["binding_digest"],
            ),
            "implementation_state": "unresolved_no_implementation_binding",
            "unresolved_codes": list(_H2_UNRESOLVED_CODES),
        }
        mapping["conversion_digest"] = _conversion_digest(mapping)
        profile_mappings.append(mapping)

    registry = build_stage_registry(
        registry_id=str(candidate["registry_id"]),
        registry_version=str(candidate["version"]),
        core_profiles=core_profiles,
        reported_adoption_status="candidate",
        human_adoption_ref=None,
    )
    decision_owner_material = {
        "state": "unresolved",
        "required_role": "human lifecycle tailoring owner",
        "source_registry_digest": copy.deepcopy(candidate["registry_digest"]),
    }
    tailoring = build_tailoring(
        tailoring_id="tailoring.unresolved.candidate-registry-adapter",
        tailoring_version="candidate-1",
        subject_scope_ref=subject_ref,
        risk_class="unresolved",
        core_stage_applicability=applicability_records,
        basis_refs=[canonical_ref, _h2_schema_ref()],
        decision_owner_ref={
            "entity_id": "unresolved.lifecycle-tailoring-decision-owner",
            "entity_version": "candidate-1",
            "content_digest": lifecycle_digest(decision_owner_material),
        },
        reactivation_triggers=tailoring_triggers,
        reported_adoption_status="candidate",
        human_adoption_ref=None,
    )
    resolution = assess_candidate_lifecycle_runtime(
        registry=registry,
        tailoring=tailoring,
        subject_scope_ref=subject_ref,
        profiles=governed_profiles,
        rule_bindings=runtime_bindings,
    )
    material: dict[str, Any] = {
        "schema_version": H2_ADAPTER_VERSION,
        "adapter_id": f"adapter.h2.{canonical_ref['content_digest']['value'][:24]}",
        "source_transport": transport,
        "input_schema_ref": _h2_schema_ref(),
        "subject_scope_ref": subject_ref,
        "profile_mappings": profile_mappings,
        "governed_profiles": governed_profiles,
        "stage_registry": registry,
        "tailoring": tailoring,
        "runtime_rule_bindings": runtime_bindings,
        "runtime_resolution": resolution,
        "resolver_ref": {
            "record_id": resolution["resolution_id"],
            "content_digest": copy.deepcopy(resolution["resolution_digest"]),
        },
        "adapter_state": "candidate_with_unresolved_prerequisites",
        "formal_authority": "none",
        "unresolved_codes": list(_H2_UNRESOLVED_CODES),
    }
    return {**material, "adapter_digest": sha256_digest(material)}


def validate_lifecycle_profile_adapter_result(
    result: Mapping[str, Any],
    *,
    source_document: Mapping[str, Any],
    source_bytes: bytes | None = None,
) -> dict[str, Any]:
    """Replay an H2 adapter result against the exact source document."""

    copied = _copy(result)
    _schema_validate(copied, "h2AdapterResult", "H2 candidate adapter result")
    if copied["adapter_digest"] != sha256_digest(_without(copied, "adapter_digest")):
        raise CandidateGovernanceAdapterError("H2 adapter digest mismatch")
    _validate_transport_against_source(
        copied["source_transport"], source_document, source_bytes
    )
    candidate = _validate_h2_candidate(source_document)
    if copied["input_schema_ref"] != _h2_schema_ref():
        raise CandidateGovernanceAdapterError("H2 input schema ref mismatch")
    for profile in copied["governed_profiles"]:
        validate_stage_profile(profile, require_trusted_decisions=False)
    validate_stage_registry(copied["stage_registry"], require_trusted_decisions=False)
    validate_tailoring(copied["tailoring"], require_trusted_decisions=False)
    for binding in copied["runtime_rule_bindings"]:
        validate_runtime_rule_binding(binding, require_trusted_decisions=False)
    validate_runtime_resolution(copied["runtime_resolution"])
    rebuilt = _build_h2_adapter_result(
        candidate,
        copied["source_transport"],
        subject_scope_ref=copied["subject_scope_ref"],
    )
    if copied != rebuilt:
        raise CandidateGovernanceAdapterError(
            "H2 adapter result does not replay from the exact candidate"
        )
    if (
        copied["runtime_resolution"]["resolution_state"] != "unresolved"
        or copied["runtime_resolution"]["formal_authority"] != "none"
        or copied["runtime_resolution"]["allowed_use"]
        != "candidate_and_unresolved_only"
        or copied["stage_registry"]["reported_adoption_status"] != "candidate"
        or copied["tailoring"]["reported_adoption_status"] != "candidate"
        or copied["formal_authority"] != "none"
    ):
        raise CandidateGovernanceAdapterError(
            "H2 candidate adapter attempted an adoption or formal promotion"
        )
    return copied


def adapt_lifecycle_profile_registry_document(
    document: Mapping[str, Any],
    *,
    source_ref: Mapping[str, Any],
    subject_scope_ref: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Adapt a canonical in-memory lifecycle candidate without trusting it."""

    candidate = _copy(document)
    transport = _document_transport(candidate, source_ref)
    result = _build_h2_adapter_result(
        candidate,
        transport,
        subject_scope_ref=subject_scope_ref,
    )
    return validate_lifecycle_profile_adapter_result(result, source_document=candidate)


def adapt_lifecycle_profile_registry_bytes(
    content: bytes,
    *,
    source_ref: Mapping[str, Any],
    subject_scope_ref: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Adapt exact lifecycle-candidate bytes bound to a supplied reference."""

    candidate, transport = _bytes_transport(content, source_ref, kind="bytes")
    result = _build_h2_adapter_result(
        candidate,
        transport,
        subject_scope_ref=subject_scope_ref,
    )
    return validate_lifecycle_profile_adapter_result(
        result, source_document=candidate, source_bytes=content
    )


def adapt_lifecycle_profile_registry_candidate(
    path: str | Path | None = None,
    *,
    expected_source_ref: Mapping[str, Any] | None = None,
    subject_scope_ref: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Adapt the pinned repository lifecycle candidate or a pinned path."""

    candidate, transport, content, _ = _read_pinned_path(
        path,
        default_name=_H2_CANDIDATE_NAME,
        default_ref=_PINNED_H2_SOURCE_REF,
        expected_source_ref=expected_source_ref,
    )
    result = _build_h2_adapter_result(
        candidate,
        transport,
        subject_scope_ref=subject_scope_ref,
    )
    return validate_lifecycle_profile_adapter_result(
        result, source_document=candidate, source_bytes=content
    )


def load_default_lifecycle_profile_registry_candidate() -> tuple[
    dict[str, Any], bytes, dict[str, Any]
]:
    """Return the pinned default H2 candidate, exact bytes, and raw file ref.

    This helper exposes packaged/source-tree resources for replay.  It does not
    authenticate their author, adopt any profile, or grant formal authority.
    """

    candidate, transport, content, _ = _read_pinned_path(
        None,
        default_name=_H2_CANDIDATE_NAME,
        default_ref=_PINNED_H2_SOURCE_REF,
        expected_source_ref=None,
    )
    return _copy(candidate), bytes(content), _copy(transport["supplied_ref"])


__all__ = [
    "CandidateGovernanceAdapterError",
    "DEFAULT_H1_SOURCE_REF",
    "DEFAULT_H2_SOURCE_REF",
    "H1_ADAPTER_VERSION",
    "H2_ADAPTER_VERSION",
    "adapt_engineering_rule_pack_bytes",
    "adapt_engineering_rule_pack_candidate",
    "adapt_engineering_rule_pack_document",
    "adapt_lifecycle_profile_registry_bytes",
    "adapt_lifecycle_profile_registry_candidate",
    "adapt_lifecycle_profile_registry_document",
    "candidate_governance_adapter_schema",
    "load_default_engineering_rule_pack_candidate",
    "load_default_lifecycle_profile_registry_candidate",
    "validate_engineering_rule_pack_adapter_result",
    "validate_lifecycle_profile_adapter_result",
]
