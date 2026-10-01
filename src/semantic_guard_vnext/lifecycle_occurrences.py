"""Typed lifecycle entities, occurrences, evidence, handoffs, and completion.

The builders produce closed, digest-bound candidate audit records.  They keep
entity identity separate from labels and content, and occurrence evidence
separate from engineering correctness or human acceptance.
"""

from __future__ import annotations

import copy
from datetime import datetime
from typing import Any, Callable, Mapping, Sequence

from .assurance_roles import validate_role_binding
from .lifecycle_governance import (
    DecisionVerifier,
    LifecycleGovernanceError,
    _copy,
    _digest,
    _record_key,
    _schema_validate,
    _validate_digest,
    profile_ref,
)


SUBJECT_ENTITY_VERSION = "lifecycle-subject-entity/v1"
SUBJECT_SNAPSHOT_VERSION = "lifecycle-subject-snapshot/v1"
ARTIFACT_MANIFEST_VERSION = "lifecycle-artifact-manifest/v1"
HANDOFF_VERSION = "lifecycle-handoff/v1"
STAGE_OCCURRENCE_VERSION = "lifecycle-stage-occurrence/v1"
OCCURRENCE_EVIDENCE_VERSION = "occurrence-evidence/v1"
COMPLETION_CLAIM_VERSION = "lifecycle-completion-claim/v1"

HarnessVerifier = Callable[[Mapping[str, Any]], bool]
CompletionVerifier = Callable[[Mapping[str, Any]], bool]

_TRUST_ROOT_UNRESOLVED = "control_plane_trust_registry_not_integrated"
_OCCURRENCE_LIMITATION = (
    "Stage state axes are reported claims; occurrence remains unresolved until "
    "a separately governed evidence and trust-root contract resolves them."
)
_CALLBACK_LIMITATION = (
    "A supplied callback and verifier_ref can record a verifier claim only; "
    "they are not a control-plane trust registry or signature trust root."
)


class LifecycleOccurrenceError(LifecycleGovernanceError):
    """Raised when an occurrence or handoff claim cannot be replayed."""


def _time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise LifecycleOccurrenceError(f"invalid date-time: {value!r}") from exc
    if parsed.tzinfo is None:
        raise LifecycleOccurrenceError("date-time must carry an explicit timezone")
    return parsed


def _identity_key(value: Mapping[str, Any]) -> tuple[str, str, str]:
    return (
        str(value["entity_id"]),
        str(value["entity_version"]),
        str(value["content_digest"]["value"]),
    )


def _role_binding_record_ref(binding: Mapping[str, Any]) -> dict[str, Any]:
    validate_role_binding(binding)
    return {
        "record_id": binding["binding_id"],
        "locator": f"urn:assurance-role-binding:{binding['binding_id']}",
        "content_digest": copy.deepcopy(binding["binding_digest"]),
    }


def _trusted_verifier_ref(verifier: Callable[..., Any] | None) -> dict[str, Any] | None:
    if verifier is None:
        return None
    verifier_ref = getattr(verifier, "verifier_ref", None)
    if not isinstance(verifier_ref, Mapping):
        return None
    try:
        _schema_validate(verifier_ref, "recordRef", "trusted external verifier")
    except LifecycleGovernanceError:
        return None
    return _copy(verifier_ref)


def build_subject_entity(
    *,
    entity_id: str,
    entity_kind: str,
    label: str,
    created_at: str,
    derived_from_ref: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    material = {
        "schema_version": SUBJECT_ENTITY_VERSION,
        "entity_id": entity_id,
        "entity_kind": entity_kind,
        "label": label,
        "created_at": created_at,
        "derived_from_ref": _copy(derived_from_ref) if derived_from_ref else None,
    }
    result = {**material, "entity_digest": _digest(material)}
    validate_subject_entity(result)
    return result


def validate_subject_entity(entity: Mapping[str, Any]) -> dict[str, Any]:
    _schema_validate(entity, "subjectEntity", "lifecycle subject entity")
    _time(str(entity["created_at"]))
    derived = entity["derived_from_ref"]
    if derived is not None and derived["entity_id"] == entity["entity_id"]:
        raise LifecycleOccurrenceError(
            "derived_from denotes another entity; versions use subject snapshots"
        )
    _validate_digest(entity, "entity_digest", "subject entity")
    return _copy(entity)


def entity_ref(entity: Mapping[str, Any]) -> dict[str, Any]:
    validate_subject_entity(entity)
    return {
        "entity_id": entity["entity_id"],
        "entity_digest": copy.deepcopy(entity["entity_digest"]),
    }


def build_subject_snapshot(
    *,
    snapshot_id: str,
    subject_entity_id: str,
    snapshot_version: str,
    content_digest: Mapping[str, Any],
    captured_at: str,
    artifact_manifest_ref: Mapping[str, Any] | None = None,
    previous_snapshot_ref: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    material = {
        "schema_version": SUBJECT_SNAPSHOT_VERSION,
        "snapshot_id": snapshot_id,
        "subject_entity_id": subject_entity_id,
        "snapshot_version": snapshot_version,
        "content_digest": _copy(content_digest),
        "captured_at": captured_at,
        "artifact_manifest_ref": (
            _copy(artifact_manifest_ref) if artifact_manifest_ref else None
        ),
        "previous_snapshot_ref": (
            _copy(previous_snapshot_ref) if previous_snapshot_ref else None
        ),
    }
    result = {**material, "snapshot_digest": _digest(material)}
    validate_subject_snapshot(result)
    return result


def validate_subject_snapshot(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    _schema_validate(snapshot, "subjectSnapshot", "lifecycle subject snapshot")
    _time(str(snapshot["captured_at"]))
    previous = snapshot["previous_snapshot_ref"]
    if previous is not None:
        if previous["subject_entity_id"] != snapshot["subject_entity_id"]:
            raise LifecycleOccurrenceError(
                "snapshot predecessor belongs to another entity"
            )
        if previous["snapshot_id"] == snapshot["snapshot_id"]:
            raise LifecycleOccurrenceError("snapshot cannot be its own predecessor")
    _validate_digest(snapshot, "snapshot_digest", "subject snapshot")
    return _copy(snapshot)


def snapshot_ref(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    validate_subject_snapshot(snapshot)
    return {
        "snapshot_id": snapshot["snapshot_id"],
        "subject_entity_id": snapshot["subject_entity_id"],
        "content_digest": copy.deepcopy(snapshot["content_digest"]),
        "snapshot_digest": copy.deepcopy(snapshot["snapshot_digest"]),
    }


def build_artifact_manifest(
    *,
    manifest_id: str,
    manifest_version: str,
    subject_entity_ref: Mapping[str, Any],
    subject_snapshot_ref: Mapping[str, Any],
    scope_ref: Mapping[str, Any],
    items: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    material = {
        "schema_version": ARTIFACT_MANIFEST_VERSION,
        "manifest_id": manifest_id,
        "manifest_version": manifest_version,
        "subject_entity_ref": _copy(subject_entity_ref),
        "subject_snapshot_ref": _copy(subject_snapshot_ref),
        "scope_ref": _copy(scope_ref),
        "closure_state": "closed",
        "items": sorted(
            (_copy(item) for item in items), key=lambda item: item["item_id"]
        ),
    }
    result = {**material, "manifest_digest": _digest(material)}
    validate_artifact_manifest(result)
    return result


def validate_artifact_manifest(manifest: Mapping[str, Any]) -> dict[str, Any]:
    _schema_validate(manifest, "artifactManifest", "lifecycle artifact manifest")
    if manifest["closure_state"] != "closed":
        raise LifecycleOccurrenceError("handoff requires a closed manifest")
    if (
        manifest["subject_entity_ref"]["entity_id"]
        != manifest["subject_snapshot_ref"]["subject_entity_id"]
    ):
        raise LifecycleOccurrenceError("manifest entity and snapshot identities differ")
    item_ids = [str(item["item_id"]) for item in manifest["items"]]
    if len(item_ids) != len(set(item_ids)):
        raise LifecycleOccurrenceError("manifest item identifiers must be unique")
    _validate_digest(manifest, "manifest_digest", "artifact manifest")
    return _copy(manifest)


def manifest_ref(manifest: Mapping[str, Any]) -> dict[str, Any]:
    validate_artifact_manifest(manifest)
    return {
        "manifest_id": manifest["manifest_id"],
        "manifest_version": manifest["manifest_version"],
        "manifest_digest": copy.deepcopy(manifest["manifest_digest"]),
    }


def validate_artifact_manifest_closed(
    manifest: Mapping[str, Any],
    *,
    subject_entity: Mapping[str, Any],
    subject_snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate a manifest against the concrete subject records it names."""

    validate_artifact_manifest(manifest)
    validate_subject_entity(subject_entity)
    validate_subject_snapshot(subject_snapshot)
    if subject_snapshot["subject_entity_id"] != subject_entity["entity_id"]:
        raise LifecycleOccurrenceError(
            "concrete subject snapshot belongs to another subject entity"
        )
    if manifest["subject_entity_ref"] != entity_ref(subject_entity):
        raise LifecycleOccurrenceError("manifest subject entity reference is not exact")
    if manifest["subject_snapshot_ref"] != snapshot_ref(subject_snapshot):
        raise LifecycleOccurrenceError(
            "manifest subject snapshot reference is not exact"
        )
    return _copy(manifest)


def _manifest_item_map(manifest: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {str(item["item_id"]): item for item in manifest["items"]}


def build_handoff(
    *,
    handoff_id: str,
    source_manifest: Mapping[str, Any],
    target_manifest: Mapping[str, Any],
    target_stage_occurrence: Mapping[str, Any],
    target_stage_output_manifest: Mapping[str, Any],
    subject_entity: Mapping[str, Any],
    subject_snapshot: Mapping[str, Any],
    exceptions: Sequence[Mapping[str, Any]] = (),
    introduced_items: Sequence[Mapping[str, Any]] = (),
    trusted_decision_verifier: DecisionVerifier | None = None,
) -> dict[str, Any]:
    material = {
        "schema_version": HANDOFF_VERSION,
        "handoff_id": handoff_id,
        "source_manifest_ref": manifest_ref(source_manifest),
        "target_manifest_ref": manifest_ref(target_manifest),
        "target_stage_occurrence_ref": occurrence_record_ref(
            target_stage_occurrence,
            trusted_decision_verifier=trusted_decision_verifier,
        ),
        "default_disposition": "preserved",
        "exceptions": sorted(
            (_copy(item) for item in exceptions),
            key=lambda item: item["source_item_id"],
        ),
        "introduced_items": sorted(
            (_copy(item) for item in introduced_items),
            key=lambda item: item["output_item_id"],
        ),
        "formal_authority": "none",
    }
    result = {**material, "handoff_digest": _digest(material)}
    validate_handoff_closed(
        result,
        source_manifest=source_manifest,
        target_manifest=target_manifest,
        target_stage_occurrence=target_stage_occurrence,
        target_stage_output_manifest=target_stage_output_manifest,
        subject_entity=subject_entity,
        subject_snapshot=subject_snapshot,
        trusted_decision_verifier=trusted_decision_verifier,
    )
    return result


def validate_handoff(
    handoff: Mapping[str, Any],
    *,
    source_manifest: Mapping[str, Any],
    target_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    _schema_validate(handoff, "handoff", "lifecycle handoff")
    validate_artifact_manifest(source_manifest)
    validate_artifact_manifest(target_manifest)
    if handoff["source_manifest_ref"] != manifest_ref(source_manifest):
        raise LifecycleOccurrenceError("handoff source manifest reference is not exact")
    if handoff["target_manifest_ref"] != manifest_ref(target_manifest):
        raise LifecycleOccurrenceError("handoff target manifest reference is not exact")
    if (
        source_manifest["subject_entity_ref"]["entity_id"]
        != target_manifest["subject_entity_ref"]["entity_id"]
    ):
        raise LifecycleOccurrenceError(
            "handoff cannot silently replace the subject entity"
        )

    source = _manifest_item_map(source_manifest)
    target = _manifest_item_map(target_manifest)
    exceptions = {str(item["source_item_id"]): item for item in handoff["exceptions"]}
    if len(exceptions) != len(handoff["exceptions"]):
        raise LifecycleOccurrenceError(
            "a source item has multiple handoff dispositions"
        )
    introduced = {
        str(item["output_item_id"]): item for item in handoff["introduced_items"]
    }
    if len(introduced) != len(handoff["introduced_items"]):
        raise LifecycleOccurrenceError("an output item is introduced more than once")
    if set(exceptions) - set(source):
        raise LifecycleOccurrenceError("handoff exception names an absent source item")
    transformed_outputs = [
        str(item["output_item_id"])
        for item in handoff["exceptions"]
        if item["disposition"] == "transformed" and item["output_item_id"] is not None
    ]
    if len(transformed_outputs) != len(set(transformed_outputs)):
        raise LifecycleOccurrenceError(
            "multiple transformations cannot silently converge on one output item"
        )
    if set(transformed_outputs) & set(introduced):
        raise LifecycleOccurrenceError(
            "one output item cannot be both transformed and introduced"
        )

    expected_target: set[str] = set()
    for item_id, source_item in source.items():
        exception = exceptions.get(item_id)
        if exception is None:
            if item_id not in target or target[item_id] != source_item:
                raise LifecycleOccurrenceError(
                    f"preserved manifest item changed or disappeared: {item_id}"
                )
            expected_target.add(item_id)
            continue
        output_id = exception["output_item_id"]
        if exception["disposition"] == "transformed":
            if output_id is None or output_id not in target or output_id == item_id:
                raise LifecycleOccurrenceError(
                    f"transformed item {item_id} lacks a distinct output item"
                )
            if output_id in source:
                raise LifecycleOccurrenceError(
                    f"transformed item {item_id} cannot reuse a source item identity"
                )
            expected_target.add(str(output_id))
        else:
            if output_id is not None:
                raise LifecycleOccurrenceError(
                    f"{exception['disposition']} item {item_id} cannot name output"
                )
        if item_id in target:
            raise LifecycleOccurrenceError(
                f"disposed source item remains in target without preservation: {item_id}"
            )

    for output_id in introduced:
        if output_id in source or output_id not in target:
            raise LifecycleOccurrenceError(
                f"introduced item is absent from target or collides with source: {output_id}"
            )
        expected_target.add(output_id)
    if set(target) != expected_target:
        unknown = sorted(set(target) - expected_target)
        missing = sorted(expected_target - set(target))
        raise LifecycleOccurrenceError(
            f"handoff target is not closed; unaccounted={unknown!r}, missing={missing!r}"
        )
    _validate_digest(handoff, "handoff_digest", "handoff")
    return _copy(handoff)


def build_stage_occurrence(
    *,
    stage_occurrence_id: str,
    stage_id: str,
    profile: Mapping[str, Any],
    configuration_snapshot_ref: Mapping[str, Any],
    subject_entity: Mapping[str, Any],
    subject_snapshot: Mapping[str, Any],
    applicability_ref: Mapping[str, Any],
    observed_at: str,
    actor_ref: Mapping[str, Any],
    role: str,
    authority_ref: Mapping[str, Any] | None,
    input_manifest: Mapping[str, Any],
    output_manifest: Mapping[str, Any],
    state_axes: Mapping[str, Any],
    started_at: str | None = None,
    finished_at: str | None = None,
    trusted_decision_verifier: DecisionVerifier | None = None,
) -> dict[str, Any]:
    material = {
        "schema_version": STAGE_OCCURRENCE_VERSION,
        "stage_occurrence_id": stage_occurrence_id,
        "stage_id": stage_id,
        "profile_ref": profile_ref(
            profile,
            trusted_decision_verifier=trusted_decision_verifier,
            require_trusted_decisions=False,
        ),
        "configuration_snapshot_ref": _copy(configuration_snapshot_ref),
        "subject_entity_ref": entity_ref(subject_entity),
        "subject_snapshot_ref": snapshot_ref(subject_snapshot),
        "applicability_ref": _copy(applicability_ref),
        "observed_at": observed_at,
        "actor_ref": _copy(actor_ref),
        "role": role,
        "authority_ref": _copy(authority_ref) if authority_ref else None,
        "input_manifest_ref": manifest_ref(input_manifest),
        "output_manifest_ref": manifest_ref(output_manifest),
        "started_at": started_at,
        "finished_at": finished_at,
        "state_axes": _copy(state_axes),
        "state_axes_semantics": "reported_claim",
        "occurrence_resolution_state": "unresolved",
        "claim_authority": "candidate_only",
        "formal_authority": "none",
        "limitations": [_OCCURRENCE_LIMITATION],
    }
    result = {**material, "occurrence_digest": _digest(material)}
    validate_stage_occurrence_closed(
        result,
        subject_entity=subject_entity,
        subject_snapshot=subject_snapshot,
        input_manifest=input_manifest,
        output_manifest=output_manifest,
        trusted_decision_verifier=trusted_decision_verifier,
    )
    return result


def _validate_stage_axes(
    axes: Mapping[str, Any],
    *,
    occurrence_id: str,
    stage_id: str,
    basis_digest: Mapping[str, Any],
    trusted_decision_verifier: DecisionVerifier | None,
    require_trusted_decisions: bool,
) -> None:
    del trusted_decision_verifier, require_trusted_decisions
    requirement = axes["decision_requirement"]
    decision = axes["human_decision"]
    decision_ref = axes["human_decision_ref"]
    if requirement == "none":
        if decision != "none" or decision_ref is not None:
            raise LifecycleOccurrenceError(
                "a stage without a human gate cannot synthesize pending or decision state"
            )
    elif decision == "pending":
        if decision_ref is not None:
            raise LifecycleOccurrenceError(
                "pending human decision must not have a record"
            )
    elif decision == "none" or decision_ref is None:
        raise LifecycleOccurrenceError(
            "human-gated stage lacks pending or resolved decision"
        )
    else:
        raise LifecycleOccurrenceError(
            "stage human decision must remain pending until a control-plane "
            "trust-root contract is integrated"
        )

    disposition = axes["human_disposition"]
    disposition_ref = axes["human_disposition_ref"]
    if disposition == "waived":
        raise LifecycleOccurrenceError(
            "stage waiver cannot be resolved by a supplied decision callback"
        )
    elif disposition_ref is not None:
        raise LifecycleOccurrenceError("non-waived occurrence carries waiver record")


def validate_stage_occurrence(
    occurrence: Mapping[str, Any],
    *,
    trusted_decision_verifier: DecisionVerifier | None = None,
    require_trusted_decisions: bool = True,
) -> dict[str, Any]:
    _schema_validate(occurrence, "stageOccurrence", "lifecycle stage occurrence")
    _time(str(occurrence["observed_at"]))
    if occurrence["profile_ref"]["profile_id"] == occurrence["stage_occurrence_id"]:
        raise LifecycleOccurrenceError(
            "profile definition and occurrence identities must differ"
        )
    if occurrence["profile_ref"]["stage_id"] != occurrence["stage_id"]:
        raise LifecycleOccurrenceError(
            "stage occurrence and stage profile identities are not aligned"
        )
    if (
        occurrence["subject_entity_ref"]["entity_id"]
        != occurrence["subject_snapshot_ref"]["subject_entity_id"]
    ):
        raise LifecycleOccurrenceError(
            "occurrence entity and snapshot identities differ"
        )
    started = occurrence["started_at"]
    finished = occurrence["finished_at"]
    timed_stage = occurrence["stage_id"] in {"action", "verification"}
    if timed_stage and (
        started is None or finished is None or occurrence["authority_ref"] is None
    ):
        raise LifecycleOccurrenceError(
            "action and verification occurrences require time bounds and authority"
        )
    if (started is None) != (finished is None):
        raise LifecycleOccurrenceError("occurrence time bounds must be paired")
    if started is not None and _time(str(started)) > _time(str(finished)):
        raise LifecycleOccurrenceError("occurrence finishes before it starts")
    _validate_stage_axes(
        occurrence["state_axes"],
        occurrence_id=str(occurrence["stage_occurrence_id"]),
        stage_id=str(occurrence["stage_id"]),
        basis_digest=occurrence["profile_ref"]["basis_digest"],
        trusted_decision_verifier=trusted_decision_verifier,
        require_trusted_decisions=require_trusted_decisions,
    )
    axes = occurrence["state_axes"]
    if (
        occurrence["state_axes_semantics"] != "reported_claim"
        or occurrence["occurrence_resolution_state"] != "unresolved"
        or occurrence["claim_authority"] != "candidate_only"
    ):
        raise LifecycleOccurrenceError(
            "stage occurrence must retain reported-claim and unresolved semantics"
        )
    if occurrence["limitations"] != [_OCCURRENCE_LIMITATION]:
        raise LifecycleOccurrenceError("stage occurrence limitation does not replay")
    if (
        axes["applicability_state"] == "not_applicable"
        and axes["execution_state"] == "completed"
    ):
        raise LifecycleOccurrenceError(
            "not-applicable stage cannot claim completed execution"
        )
    _validate_digest(occurrence, "occurrence_digest", "stage occurrence")
    return _copy(occurrence)


def validate_stage_occurrence_closed(
    occurrence: Mapping[str, Any],
    *,
    subject_entity: Mapping[str, Any],
    subject_snapshot: Mapping[str, Any],
    input_manifest: Mapping[str, Any],
    output_manifest: Mapping[str, Any],
    trusted_decision_verifier: DecisionVerifier | None = None,
    require_trusted_decisions: bool = True,
) -> dict[str, Any]:
    """Validate one occurrence against every concrete subject and manifest.

    The structural validator is intentionally usable when only a stored
    occurrence is available.  This closed validator is the required API when
    a caller wants to claim that the occurrence names particular input/output
    manifests and a particular subject snapshot.
    """

    validate_stage_occurrence(
        occurrence,
        trusted_decision_verifier=trusted_decision_verifier,
        require_trusted_decisions=require_trusted_decisions,
    )
    validate_artifact_manifest_closed(
        input_manifest,
        subject_entity=subject_entity,
        subject_snapshot=subject_snapshot,
    )
    validate_artifact_manifest_closed(
        output_manifest,
        subject_entity=subject_entity,
        subject_snapshot=subject_snapshot,
    )
    if occurrence["subject_entity_ref"] != entity_ref(subject_entity):
        raise LifecycleOccurrenceError(
            "stage occurrence subject entity reference is not exact"
        )
    if occurrence["subject_snapshot_ref"] != snapshot_ref(subject_snapshot):
        raise LifecycleOccurrenceError(
            "stage occurrence subject snapshot reference is not exact"
        )
    if occurrence["input_manifest_ref"] != manifest_ref(input_manifest):
        raise LifecycleOccurrenceError(
            "stage occurrence input manifest reference is not exact"
        )
    if occurrence["output_manifest_ref"] != manifest_ref(output_manifest):
        raise LifecycleOccurrenceError(
            "stage occurrence output manifest reference is not exact"
        )
    return _copy(occurrence)


def validate_handoff_closed(
    handoff: Mapping[str, Any],
    *,
    source_manifest: Mapping[str, Any],
    target_manifest: Mapping[str, Any],
    target_stage_occurrence: Mapping[str, Any],
    target_stage_output_manifest: Mapping[str, Any],
    subject_entity: Mapping[str, Any],
    subject_snapshot: Mapping[str, Any],
    trusted_decision_verifier: DecisionVerifier | None = None,
    require_trusted_decisions: bool = True,
) -> dict[str, Any]:
    """Close a handoff over its concrete target occurrence and input subject."""

    validate_handoff(
        handoff,
        source_manifest=source_manifest,
        target_manifest=target_manifest,
    )
    validate_artifact_manifest(source_manifest)
    if source_manifest["subject_entity_ref"] != entity_ref(subject_entity):
        raise LifecycleOccurrenceError(
            "handoff source manifest subject entity reference is not exact"
        )
    validate_stage_occurrence_closed(
        target_stage_occurrence,
        subject_entity=subject_entity,
        subject_snapshot=subject_snapshot,
        input_manifest=target_manifest,
        output_manifest=target_stage_output_manifest,
        trusted_decision_verifier=trusted_decision_verifier,
        require_trusted_decisions=require_trusted_decisions,
    )
    expected_occurrence_ref = occurrence_record_ref(
        target_stage_occurrence,
        trusted_decision_verifier=trusted_decision_verifier,
        require_trusted_decisions=require_trusted_decisions,
    )
    if handoff["target_stage_occurrence_ref"] != expected_occurrence_ref:
        raise LifecycleOccurrenceError(
            "handoff target stage occurrence reference is not exact"
        )
    if handoff["target_manifest_ref"] != target_stage_occurrence["input_manifest_ref"]:
        raise LifecycleOccurrenceError(
            "handoff target manifest is not the target occurrence input manifest"
        )
    if (
        target_manifest["subject_entity_ref"]
        != target_stage_occurrence["subject_entity_ref"]
        or target_manifest["subject_snapshot_ref"]
        != target_stage_occurrence["subject_snapshot_ref"]
    ):
        raise LifecycleOccurrenceError(
            "handoff target manifest subject is not the target occurrence subject"
        )
    return _copy(handoff)


def occurrence_ref(
    occurrence: Mapping[str, Any],
    *,
    trusted_decision_verifier: DecisionVerifier | None = None,
    require_trusted_decisions: bool = True,
) -> dict[str, Any]:
    validate_stage_occurrence(
        occurrence,
        trusted_decision_verifier=trusted_decision_verifier,
        require_trusted_decisions=require_trusted_decisions,
    )
    return {
        "stage_occurrence_id": occurrence["stage_occurrence_id"],
        "occurrence_digest": copy.deepcopy(occurrence["occurrence_digest"]),
    }


def occurrence_record_ref(
    occurrence: Mapping[str, Any],
    *,
    locator: str | None = None,
    trusted_decision_verifier: DecisionVerifier | None = None,
    require_trusted_decisions: bool = True,
) -> dict[str, Any]:
    validate_stage_occurrence(
        occurrence,
        trusted_decision_verifier=trusted_decision_verifier,
        require_trusted_decisions=require_trusted_decisions,
    )
    occurrence_id = str(occurrence["stage_occurrence_id"])
    return {
        "record_id": occurrence_id,
        "locator": locator or f"urn:lifecycle-occurrence:{occurrence_id}",
        "content_digest": copy.deepcopy(occurrence["occurrence_digest"]),
    }


def _harness_verification_context(
    *,
    stage_occurrence_ref: Mapping[str, Any],
    occurrence_kind: str,
    actor_ref: Mapping[str, Any],
    authority_ref: Mapping[str, Any],
    target_snapshot_ref: Mapping[str, Any],
    environment_ref: Mapping[str, Any],
    tool_refs: Sequence[Mapping[str, Any]],
    started_at: str,
    finished_at: str,
    input_refs: Sequence[Mapping[str, Any]],
    raw_result_refs: Sequence[Mapping[str, Any]],
    output_refs: Sequence[Mapping[str, Any]],
    observer_ref: Mapping[str, Any],
    observer_role_binding_ref: Mapping[str, Any],
    observer_authority_ref: Mapping[str, Any],
    reported_outcome: str,
    verification_method_ref: Mapping[str, Any] | None,
    self_report_ref: Mapping[str, Any] | None,
) -> dict[str, Any]:
    return {
        "stage_occurrence_ref": _copy(stage_occurrence_ref),
        "occurrence_kind": occurrence_kind,
        "actor_ref": _copy(actor_ref),
        "authority_ref": _copy(authority_ref),
        "target_snapshot_ref": _copy(target_snapshot_ref),
        "environment_ref": _copy(environment_ref),
        "tool_refs": sorted((_copy(item) for item in tool_refs), key=_identity_key),
        "started_at": started_at,
        "finished_at": finished_at,
        "input_refs": sorted((_copy(item) for item in input_refs), key=_record_key),
        "raw_result_refs": sorted(
            (_copy(item) for item in raw_result_refs), key=_record_key
        ),
        "output_refs": sorted((_copy(item) for item in output_refs), key=_record_key),
        "observer_ref": _copy(observer_ref),
        "observer_role_binding_ref": _copy(observer_role_binding_ref),
        "observer_authority_ref": _copy(observer_authority_ref),
        "reported_observation_method": "claimed_execution_harness",
        "reported_outcome": reported_outcome,
        "verification_method_ref": (
            _copy(verification_method_ref) if verification_method_ref else None
        ),
        "self_report_ref": _copy(self_report_ref) if self_report_ref else None,
    }


def _evaluate_harness_verification(
    context: Mapping[str, Any],
    trusted_harness_verifier: HarnessVerifier | None,
) -> tuple[str, dict[str, Any] | None, str, list[str]]:
    if trusted_harness_verifier is None:
        return (
            "unresolved",
            None,
            "not_supplied",
            [_TRUST_ROOT_UNRESOLVED, "trusted_harness_verifier_missing"],
        )
    verifier_ref = _trusted_verifier_ref(trusted_harness_verifier)
    if verifier_ref is None:
        return (
            "unresolved",
            None,
            "verifier_ref_invalid",
            [_TRUST_ROOT_UNRESOLVED, "trusted_harness_verifier_ref_invalid"],
        )
    try:
        verified = bool(trusted_harness_verifier(_copy(context)))
    except Exception:
        return (
            "unresolved",
            verifier_ref,
            "verifier_unavailable",
            [_TRUST_ROOT_UNRESOLVED, "trusted_harness_verifier_unavailable"],
        )
    if not verified:
        return (
            "unresolved",
            verifier_ref,
            "verifier_claim_rejected",
            [_TRUST_ROOT_UNRESOLVED, "trusted_harness_verifier_rejected_claim"],
        )
    return (
        "unresolved",
        verifier_ref,
        "verifier_claim_accepted",
        [_TRUST_ROOT_UNRESOLVED, "verifier_claim_accepted_without_trust_root"],
    )


def build_occurrence_evidence(
    *,
    occurrence_evidence_id: str,
    occurrence_kind: str,
    stage_occurrence: Mapping[str, Any],
    actor_ref: Mapping[str, Any],
    authority_ref: Mapping[str, Any],
    target_snapshot_ref: Mapping[str, Any],
    environment_ref: Mapping[str, Any],
    tool_refs: Sequence[Mapping[str, Any]],
    started_at: str,
    finished_at: str,
    input_refs: Sequence[Mapping[str, Any]],
    raw_result_refs: Sequence[Mapping[str, Any]],
    output_refs: Sequence[Mapping[str, Any]],
    observer_ref: Mapping[str, Any],
    observer_role_binding: Mapping[str, Any],
    reported_outcome: str,
    verification_method_ref: Mapping[str, Any] | None = None,
    self_report_ref: Mapping[str, Any] | None = None,
    limitations: Sequence[str] = (),
    trusted_decision_verifier: DecisionVerifier | None = None,
    trusted_harness_verifier: HarnessVerifier | None = None,
) -> dict[str, Any]:
    stage_ref = occurrence_record_ref(
        stage_occurrence,
        trusted_decision_verifier=trusted_decision_verifier,
    )
    role_binding_ref = _role_binding_record_ref(observer_role_binding)
    observer_authority_ref = observer_role_binding["authority_ref"]
    if observer_authority_ref is None:
        raise LifecycleOccurrenceError(
            "execution-harness observer lacks external authority evidence"
        )
    context = _harness_verification_context(
        stage_occurrence_ref=stage_ref,
        occurrence_kind=occurrence_kind,
        actor_ref=actor_ref,
        authority_ref=authority_ref,
        target_snapshot_ref=target_snapshot_ref,
        environment_ref=environment_ref,
        tool_refs=tool_refs,
        started_at=started_at,
        finished_at=finished_at,
        input_refs=input_refs,
        raw_result_refs=raw_result_refs,
        output_refs=output_refs,
        observer_ref=observer_ref,
        observer_role_binding_ref=role_binding_ref,
        observer_authority_ref=observer_authority_ref,
        reported_outcome=reported_outcome,
        verification_method_ref=verification_method_ref,
        self_report_ref=self_report_ref,
    )
    (
        harness_state,
        harness_verifier_ref,
        harness_verifier_claim,
        harness_unresolved_reasons,
    ) = _evaluate_harness_verification(context, trusted_harness_verifier)
    material = {
        "schema_version": OCCURRENCE_EVIDENCE_VERSION,
        "occurrence_evidence_id": occurrence_evidence_id,
        "occurrence_kind": occurrence_kind,
        "stage_occurrence_ref": stage_ref,
        "actor_ref": context["actor_ref"],
        "authority_ref": context["authority_ref"],
        "target_snapshot_ref": context["target_snapshot_ref"],
        "environment_ref": context["environment_ref"],
        "tool_refs": context["tool_refs"],
        "started_at": started_at,
        "finished_at": finished_at,
        "input_refs": context["input_refs"],
        "raw_result_refs": context["raw_result_refs"],
        "output_refs": context["output_refs"],
        "observer_ref": context["observer_ref"],
        "observer_role_binding_ref": role_binding_ref,
        "observer_authority_ref": context["observer_authority_ref"],
        "reported_observation_method": "claimed_execution_harness",
        "reported_outcome": reported_outcome,
        "external_harness_state": harness_state,
        "harness_verifier_claim": harness_verifier_claim,
        "harness_verifier_ref": harness_verifier_ref,
        "harness_verification_input_digest": _digest(context),
        "external_harness_unresolved_reasons": harness_unresolved_reasons,
        "trust_root_resolution_state": "not_integrated",
        "trust_root_ref": None,
        "verification_method_ref": context["verification_method_ref"],
        "self_report_ref": context["self_report_ref"],
        "claim_authority": "candidate_only",
        "formal_authority": "none",
        "limitations": sorted(
            set(
                [
                    *limitations,
                    "Occurrence evidence records observed facts, not engineering correctness or human acceptance.",
                    "A self-report is supplemental and never substitutes for harness raw-result evidence.",
                    _CALLBACK_LIMITATION,
                ]
            )
        ),
    }
    result = {**material, "evidence_digest": _digest(material)}
    validate_occurrence_evidence(
        result,
        stage_occurrence=stage_occurrence,
        observer_role_binding=observer_role_binding,
        trusted_decision_verifier=trusted_decision_verifier,
        trusted_harness_verifier=trusted_harness_verifier,
    )
    return result


def validate_occurrence_evidence(
    evidence: Mapping[str, Any],
    *,
    stage_occurrence: Mapping[str, Any],
    observer_role_binding: Mapping[str, Any],
    trusted_decision_verifier: DecisionVerifier | None = None,
    trusted_harness_verifier: HarnessVerifier | None = None,
) -> dict[str, Any]:
    _schema_validate(evidence, "occurrenceEvidence", "occurrence evidence")
    validate_stage_occurrence(
        stage_occurrence, trusted_decision_verifier=trusted_decision_verifier
    )
    if evidence["stage_occurrence_ref"] != occurrence_record_ref(
        stage_occurrence, trusted_decision_verifier=trusted_decision_verifier
    ):
        raise LifecycleOccurrenceError("evidence occurrence reference is not exact")
    validate_role_binding(observer_role_binding)
    if evidence["observer_role_binding_ref"] != _role_binding_record_ref(
        observer_role_binding
    ):
        raise LifecycleOccurrenceError("observer role binding reference is not exact")
    if evidence["observer_authority_ref"] != observer_role_binding["authority_ref"]:
        raise LifecycleOccurrenceError(
            "observer authority differs from its role binding"
        )
    if observer_role_binding["actor_ref"] != evidence["observer_ref"]:
        raise LifecycleOccurrenceError(
            "observer identity differs from its role binding"
        )
    if observer_role_binding["role_surface"] != "execution_harness" or not {
        "observe_occurrence",
        "collect_raw_evidence",
    }.issubset(observer_role_binding["granted_capabilities"]):
        raise LifecycleOccurrenceError(
            "observer lacks the execution-harness candidate capability binding"
        )
    if evidence["occurrence_kind"] != stage_occurrence["stage_id"]:
        raise LifecycleOccurrenceError(
            "evidence kind differs from its stage occurrence"
        )
    if evidence["actor_ref"] != stage_occurrence["actor_ref"]:
        raise LifecycleOccurrenceError(
            "evidence actor differs from its stage occurrence"
        )
    if evidence["authority_ref"] != stage_occurrence["authority_ref"]:
        raise LifecycleOccurrenceError(
            "evidence authority differs from its stage occurrence"
        )
    if evidence["target_snapshot_ref"] != stage_occurrence["subject_snapshot_ref"]:
        raise LifecycleOccurrenceError(
            "evidence target snapshot differs from its stage occurrence"
        )
    if (
        evidence["started_at"] != stage_occurrence["started_at"]
        or evidence["finished_at"] != stage_occurrence["finished_at"]
    ):
        raise LifecycleOccurrenceError(
            "evidence time bounds differ from its stage occurrence"
        )
    if _identity_key(evidence["observer_ref"]) == _identity_key(evidence["actor_ref"]):
        raise LifecycleOccurrenceError(
            "actor self-report cannot establish occurrence evidence"
        )
    if (
        evidence["occurrence_kind"] == "verification"
        and evidence["verification_method_ref"] is None
    ):
        raise LifecycleOccurrenceError("verification occurrence lacks method evidence")
    if (
        evidence["occurrence_kind"] == "action"
        and evidence["verification_method_ref"] is not None
    ):
        raise LifecycleOccurrenceError(
            "action occurrence cannot masquerade as verification"
        )
    if _time(str(evidence["started_at"])) > _time(str(evidence["finished_at"])):
        raise LifecycleOccurrenceError("occurrence evidence finishes before it starts")
    if not evidence["raw_result_refs"]:
        raise LifecycleOccurrenceError(
            "occurrence evidence requires raw harness results"
        )
    context = _harness_verification_context(
        stage_occurrence_ref=evidence["stage_occurrence_ref"],
        occurrence_kind=str(evidence["occurrence_kind"]),
        actor_ref=evidence["actor_ref"],
        authority_ref=evidence["authority_ref"],
        target_snapshot_ref=evidence["target_snapshot_ref"],
        environment_ref=evidence["environment_ref"],
        tool_refs=evidence["tool_refs"],
        started_at=str(evidence["started_at"]),
        finished_at=str(evidence["finished_at"]),
        input_refs=evidence["input_refs"],
        raw_result_refs=evidence["raw_result_refs"],
        output_refs=evidence["output_refs"],
        observer_ref=evidence["observer_ref"],
        observer_role_binding_ref=evidence["observer_role_binding_ref"],
        observer_authority_ref=evidence["observer_authority_ref"],
        reported_outcome=str(evidence["reported_outcome"]),
        verification_method_ref=evidence["verification_method_ref"],
        self_report_ref=evidence["self_report_ref"],
    )
    if evidence["harness_verification_input_digest"] != _digest(context):
        raise LifecycleOccurrenceError(
            "harness verification input digest does not replay"
        )
    (
        expected_state,
        expected_verifier_ref,
        expected_verifier_claim,
        expected_reasons,
    ) = _evaluate_harness_verification(context, trusted_harness_verifier)
    if (
        evidence["external_harness_state"] != expected_state
        or evidence["harness_verifier_claim"] != expected_verifier_claim
        or evidence["harness_verifier_ref"] != expected_verifier_ref
        or evidence["external_harness_unresolved_reasons"] != expected_reasons
    ):
        raise LifecycleOccurrenceError(
            "external harness resolution does not replay through its trusted verifier"
        )
    if (
        evidence["trust_root_resolution_state"] != "not_integrated"
        or evidence["trust_root_ref"] is not None
    ):
        raise LifecycleOccurrenceError(
            "occurrence evidence cannot self-establish an external trust root"
        )
    if _CALLBACK_LIMITATION not in evidence["limitations"]:
        raise LifecycleOccurrenceError("callback trust limitation is missing")
    _validate_digest(evidence, "evidence_digest", "occurrence evidence")
    return _copy(evidence)


def _completion_verification_context(
    *,
    completion_claim_id: str,
    subject_snapshot_ref: Mapping[str, Any],
    reported_technical_completion_state: str,
    obligation_result_refs: Sequence[Mapping[str, Any]],
    verification_evidence_refs: Sequence[Mapping[str, Any]],
    unresolved_refs: Sequence[Mapping[str, Any]],
    residual_risk_refs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "completion_claim_id": completion_claim_id,
        "subject_snapshot_ref": _copy(subject_snapshot_ref),
        "reported_technical_completion_state": reported_technical_completion_state,
        "obligation_result_refs": sorted(
            (_copy(item) for item in obligation_result_refs), key=_record_key
        ),
        "verification_evidence_refs": sorted(
            (_copy(item) for item in verification_evidence_refs), key=_record_key
        ),
        "unresolved_refs": sorted(
            (_copy(item) for item in unresolved_refs), key=_record_key
        ),
        "residual_risk_refs": sorted(
            (_copy(item) for item in residual_risk_refs), key=_record_key
        ),
    }


def _evaluate_completion_verification(
    context: Mapping[str, Any],
    trusted_completion_verifier: CompletionVerifier | None,
) -> tuple[str, dict[str, Any] | None, str, list[str]]:
    if trusted_completion_verifier is None:
        return (
            "unresolved",
            None,
            "not_supplied",
            [_TRUST_ROOT_UNRESOLVED, "trusted_completion_verifier_missing"],
        )
    verifier_ref = _trusted_verifier_ref(trusted_completion_verifier)
    if verifier_ref is None:
        return (
            "unresolved",
            None,
            "verifier_ref_invalid",
            [_TRUST_ROOT_UNRESOLVED, "trusted_completion_verifier_ref_invalid"],
        )
    try:
        verified = bool(trusted_completion_verifier(_copy(context)))
    except Exception:
        return (
            "unresolved",
            verifier_ref,
            "verifier_unavailable",
            [_TRUST_ROOT_UNRESOLVED, "trusted_completion_verifier_unavailable"],
        )
    if not verified:
        return (
            "unresolved",
            verifier_ref,
            "verifier_claim_rejected",
            [_TRUST_ROOT_UNRESOLVED, "trusted_completion_verifier_rejected_claim"],
        )
    return (
        "unresolved",
        verifier_ref,
        "verifier_claim_accepted",
        [_TRUST_ROOT_UNRESOLVED, "verifier_claim_accepted_without_trust_root"],
    )


def _completion_basis(claim: Mapping[str, Any]) -> dict[str, Any]:
    return _digest(
        {
            key: copy.deepcopy(claim[key])
            for key in (
                "schema_version",
                "completion_claim_id",
                "subject_snapshot_ref",
                "reported_technical_completion_state",
                "completion_resolution_state",
                "completion_verifier_claim",
                "completion_verifier_ref",
                "completion_verification_input_digest",
                "completion_unresolved_reasons",
                "trust_root_resolution_state",
                "trust_root_ref",
                "obligation_result_refs",
                "verification_evidence_refs",
                "unresolved_refs",
                "residual_risk_refs",
            )
        }
    )


def completion_basis_digest(claim: Mapping[str, Any]) -> dict[str, Any]:
    _schema_validate(claim, "completionClaim", "lifecycle completion claim")
    return _completion_basis(claim)


def build_completion_claim(
    *,
    completion_claim_id: str,
    subject_snapshot_ref: Mapping[str, Any],
    reported_technical_completion_state: str,
    obligation_result_refs: Sequence[Mapping[str, Any]],
    verification_evidence_refs: Sequence[Mapping[str, Any]],
    unresolved_refs: Sequence[Mapping[str, Any]] = (),
    residual_risk_refs: Sequence[Mapping[str, Any]] = (),
    human_decision: str = "pending",
    human_decision_ref: Mapping[str, Any] | None = None,
    trusted_decision_verifier: DecisionVerifier | None = None,
    trusted_completion_verifier: CompletionVerifier | None = None,
) -> dict[str, Any]:
    if human_decision != "pending" or human_decision_ref is not None:
        raise LifecycleOccurrenceError(
            "human completion decision must remain pending until a control-plane "
            "trust-root contract is integrated"
        )
    context = _completion_verification_context(
        completion_claim_id=completion_claim_id,
        subject_snapshot_ref=subject_snapshot_ref,
        reported_technical_completion_state=reported_technical_completion_state,
        obligation_result_refs=obligation_result_refs,
        verification_evidence_refs=verification_evidence_refs,
        unresolved_refs=unresolved_refs,
        residual_risk_refs=residual_risk_refs,
    )
    (
        completion_resolution_state,
        completion_verifier_ref,
        completion_verifier_claim,
        completion_unresolved_reasons,
    ) = _evaluate_completion_verification(context, trusted_completion_verifier)
    material = {
        "schema_version": COMPLETION_CLAIM_VERSION,
        "completion_claim_id": completion_claim_id,
        "subject_snapshot_ref": context["subject_snapshot_ref"],
        "reported_technical_completion_state": reported_technical_completion_state,
        "completion_resolution_state": completion_resolution_state,
        "completion_verifier_claim": completion_verifier_claim,
        "completion_verifier_ref": completion_verifier_ref,
        "completion_verification_input_digest": _digest(context),
        "completion_unresolved_reasons": completion_unresolved_reasons,
        "trust_root_resolution_state": "not_integrated",
        "trust_root_ref": None,
        "obligation_result_refs": context["obligation_result_refs"],
        "verification_evidence_refs": context["verification_evidence_refs"],
        "unresolved_refs": context["unresolved_refs"],
        "residual_risk_refs": context["residual_risk_refs"],
        "human_decision": "pending",
        "human_decision_ref": None,
        "claim_authority": "candidate_only",
        "formal_authority": "none",
        "limitations": [
            "Technical completion is a reported claim and remains unresolved.",
            _CALLBACK_LIMITATION,
        ],
    }
    result = {**material, "claim_digest": _digest(material)}
    validate_completion_claim(
        result,
        trusted_decision_verifier=trusted_decision_verifier,
        trusted_completion_verifier=trusted_completion_verifier,
    )
    return result


def validate_completion_claim(
    claim: Mapping[str, Any],
    *,
    trusted_decision_verifier: DecisionVerifier | None = None,
    trusted_completion_verifier: CompletionVerifier | None = None,
    require_trusted_decisions: bool = True,
) -> dict[str, Any]:
    del trusted_decision_verifier, require_trusted_decisions
    _schema_validate(claim, "completionClaim", "lifecycle completion claim")
    state = claim["reported_technical_completion_state"]
    if state == "completed" and (
        not claim["obligation_result_refs"]
        or not claim["verification_evidence_refs"]
        or claim["unresolved_refs"]
    ):
        raise LifecycleOccurrenceError(
            "technical completion requires obligation and verification evidence and no unresolved item"
        )
    context = _completion_verification_context(
        completion_claim_id=str(claim["completion_claim_id"]),
        subject_snapshot_ref=claim["subject_snapshot_ref"],
        reported_technical_completion_state=str(
            claim["reported_technical_completion_state"]
        ),
        obligation_result_refs=claim["obligation_result_refs"],
        verification_evidence_refs=claim["verification_evidence_refs"],
        unresolved_refs=claim["unresolved_refs"],
        residual_risk_refs=claim["residual_risk_refs"],
    )
    if claim["completion_verification_input_digest"] != _digest(context):
        raise LifecycleOccurrenceError(
            "completion verification input digest does not replay"
        )
    (
        expected_resolution_state,
        expected_verifier_ref,
        expected_verifier_claim,
        expected_unresolved_reasons,
    ) = _evaluate_completion_verification(context, trusted_completion_verifier)
    if (
        claim["completion_resolution_state"] != expected_resolution_state
        or claim["completion_verifier_claim"] != expected_verifier_claim
        or claim["completion_verifier_ref"] != expected_verifier_ref
        or claim["completion_unresolved_reasons"] != expected_unresolved_reasons
    ):
        raise LifecycleOccurrenceError(
            "completion resolution does not replay through its trusted verifier"
        )
    if (
        claim["trust_root_resolution_state"] != "not_integrated"
        or claim["trust_root_ref"] is not None
    ):
        raise LifecycleOccurrenceError(
            "completion claim cannot self-establish an external trust root"
        )
    if claim["human_decision"] != "pending" or claim["human_decision_ref"] is not None:
        raise LifecycleOccurrenceError("completion human decision must remain pending")
    if claim["claim_authority"] != "candidate_only":
        raise LifecycleOccurrenceError("completion claim authority exceeds candidate")
    if _CALLBACK_LIMITATION not in claim["limitations"]:
        raise LifecycleOccurrenceError("callback trust limitation is missing")
    _validate_digest(claim, "claim_digest", "completion claim")
    return _copy(claim)
