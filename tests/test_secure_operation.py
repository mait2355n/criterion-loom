from __future__ import annotations

import copy
import unittest

from semantic_guard.secure_operation import (
    CONTROL_KINDS,
    NONAPPLICABILITY_CONDITIONS,
    REQUALIFICATION_DIMENSIONS,
    build_condition_result,
    build_control_profile,
    build_control_result,
    build_data_item,
    build_destination,
    build_evidence_observation,
    build_external_human_decision,
    build_flow_component,
    build_flow_observation,
    build_independent_review,
    build_information_flow,
    build_nonapplicability_profile,
    build_purpose,
    build_requalification_trigger,
    build_retention_observation,
    build_restart_test,
    build_retention_rule,
    build_scope_entry,
    build_scope_manifest,
    build_secure_operation_assessment,
    build_secure_operation_profile,
    build_trigger_assessment,
    digest_value,
    _graph_reaches_retention,
    secure_operation_errors,
    validate_secure_operation,
    versioned_ref,
)


ASSESSED_AT = "2026-07-16T13:00:00Z"
OBSERVED_AT = "2026-07-16T12:00:00Z"
EXPIRES_AT = "2026-07-16T14:00:00Z"
REVIEW_ID = "review.secure-operation"
REVIEW_EVIDENCE_ID = "evidence.independent-review"
SCOPE_EVIDENCE_ID = "evidence.scope-inventory"
REVIEWER_REF = versioned_ref("human.independent-reviewer", "1")
INVENTORY_AUTHORITY_REF = versioned_ref("authority.scope-inventory", "1")


def _attributes(
    *,
    data_classes: tuple[str, ...] = ("synthetic",),
    source_kind: str = "synthetic",
    real_material: bool = False,
    execution_location: str = "local",
    external_provider: bool = False,
    durable: bool = False,
    persistent_log: bool = False,
    persistent_artifact: bool = False,
    privileged: bool = False,
    credential_present: bool = False,
) -> dict[str, object]:
    return {
        "data_classes": list(data_classes),
        "source_kind": source_kind,
        "real_material": real_material,
        "execution_location": execution_location,
        "external_provider": external_provider,
        "durable": durable,
        "persistent_log": persistent_log,
        "persistent_artifact": persistent_artifact,
        "privileged": privileged,
        "credential_present": credential_present,
    }


def _entry(
    entry_id: str,
    kind: str,
    attributes: dict[str, object],
) -> dict[str, object]:
    return build_scope_entry(
        entry_id=entry_id,
        entry_kind=kind,
        locator=f"fixture://{entry_id}",
        content_digest=digest_value({"entry": entry_id}),
        attributes=attributes,
    )


def _manifest(
    manifest_id: str,
    kind: str,
    entries: list[dict[str, object]],
) -> dict[str, object]:
    return build_scope_manifest(
        manifest_id=manifest_id,
        manifest_version="1",
        manifest_kind=kind,
        closure_rule=f"Enumerate every {kind} entry in the declared denominator.",
        inventory_authority_ref=INVENTORY_AUTHORITY_REF,
        inventory_evidence_refs=[SCOPE_EVIDENCE_ID],
        entries=entries,
    )


def _evidence(
    evidence_id: str,
    evidence_kind: str,
    scope_digest_value: dict[str, str],
    claim_refs: list[str],
    *,
    trust_class: str = "tool_observed",
    relationship: str = "tool_observer",
    observed_at: str = OBSERVED_AT,
    observer_ref: dict[str, object] | None = None,
) -> dict[str, object]:
    return build_evidence_observation(
        evidence_id=evidence_id,
        evidence_kind=evidence_kind,
        locator=f"evidence://{evidence_id}",
        content_digest=digest_value({"observation": evidence_id}),
        scope_digest_value=scope_digest_value,
        claim_refs=claim_refs,
        observer={
            "observer_ref": (
                observer_ref
                if observer_ref is not None
                else versioned_ref(f"observer.{evidence_id}", "1")
            ),
            "observer_kind": "human" if relationship == "independent" else "tool",
            "relationship_to_subject": relationship,
        },
        trust_class=trust_class,
        observed_at=observed_at,
        expires_at=EXPIRES_AT,
        time_trust="trusted",
        limitations=["Observation is limited to the digest-bound declared scope."],
    )


def _decision(
    *,
    decision_id: str,
    decision_kind: str,
    profile: dict[str, object],
    scope_digest_value: dict[str, object],
    decision_sequence: int = 1,
    decided_at: str = "2026-07-16T11:00:00Z",
) -> dict[str, object]:
    return build_external_human_decision(
        decision_id=decision_id,
        decision_sequence=decision_sequence,
        decision_kind=decision_kind,
        decided_by="human.policy-owner",
        decided_at=decided_at,
        target_id=str(profile["profile_id"]),
        target_version=str(profile["profile_version"]),
        target_digest=profile["profile_basis_digest"],
        target_scope_digest=scope_digest_value,
        trust_class="signed",
        record_ref={
            "record_id": f"record.{decision_id}",
            "locator": f"decision://{decision_id}",
            "content_digest": digest_value({"record": decision_id}),
        },
        rationale="The human policy owner selected this exact digest-bound profile.",
    )


def _finalize(
    *,
    path: str,
    claimed_environment: str,
    manifests: list[dict[str, object]],
    evidence: list[dict[str, object]],
    decisions: list[dict[str, object]],
    unresolved_scope: list[dict[str, object]],
    contract: dict[str, object],
    include_review: bool,
) -> dict[str, object]:
    kwargs = {
        "assessment_id": "assessment.secure-operation",
        "assessment_version": "1",
        "path": path,
        "assessed_at": ASSESSED_AT,
        "time_trust": "trusted",
        "claimed_environment": claimed_environment,
        "scope_manifests": manifests,
        "evidence_observations": evidence,
        "human_decision_records": decisions,
        "unresolved_scope": unresolved_scope,
        "path_contract": contract,
    }
    preliminary = build_secure_operation_assessment(**kwargs)
    if not include_review:
        return preliminary
    review = build_independent_review(
        review_id=REVIEW_ID,
        reviewer_ref=REVIEWER_REF,
        target_assessment_id="assessment.secure-operation",
        target_assessment_version="1",
        target_basis_digest=preliminary["review_basis_digest"],
        status="accepted",
        reviewed_at="2026-07-16T12:30:00Z",
        expires_at=EXPIRES_AT,
        time_trust="trusted",
        evidence_refs=[REVIEW_EVIDENCE_ID],
    )
    return build_secure_operation_assessment(
        **kwargs,
        independent_review_record=review,
    )


def _reassess(
    bundle: dict[str, object],
    *,
    contract: dict[str, object] | None = None,
) -> dict[str, object]:
    return _finalize(
        path=str(bundle["path"]),
        claimed_environment=str(bundle["claimed_environment"]),
        manifests=copy.deepcopy(bundle["scope_manifests"]),
        evidence=copy.deepcopy(bundle["evidence_observations"]),
        decisions=copy.deepcopy(bundle["human_decision_records"]),
        unresolved_scope=copy.deepcopy(bundle["unresolved_scope"]),
        contract=copy.deepcopy(contract or bundle["path_contract"]),
        include_review=bundle["independent_review_record"] is not None,
    )


def _adopted_bundle(
    *,
    profile_status: str = "adopted",
    include_decision: bool = True,
    include_review: bool = True,
    subject_classes: tuple[str, ...] = ("public",),
    data_class: str = "public",
    sink_kind: str = "artifact",
    missing_sink_retention: bool = False,
    runtime_processor_external: bool = False,
    component_processor_external: bool | None = None,
    sink_allowed_class: str | None = None,
    unresolved_scope: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    sink_persistence = {
        "persistent_log": sink_kind == "log",
        "persistent_artifact": sink_kind == "artifact",
    }
    subject = _entry(
        "subject.input",
        "subject",
        _attributes(
            data_classes=subject_classes,
            source_kind="operational_material",
            real_material=True,
        ),
    )
    configuration = _entry(
        "configuration.application",
        "configuration",
        _attributes(source_kind="local_fixture"),
    )
    runtime_entries = [
        _entry(
            "runtime.source",
            "runtime_path",
            _attributes(data_classes=(data_class,), source_kind="operational_material"),
        ),
        _entry(
            "runtime.processor",
            "runtime_path",
            _attributes(
                data_classes=(data_class,),
                source_kind="operational_material",
                execution_location=(
                    "external" if runtime_processor_external else "local"
                ),
                external_provider=runtime_processor_external,
            ),
        ),
        _entry(
            "runtime.sink",
            "runtime_path",
            _attributes(
                data_classes=(data_class,),
                source_kind="operational_material",
                durable=True,
                **sink_persistence,
            ),
        ),
        _entry(
            "runtime.retention",
            "runtime_path",
            _attributes(data_classes=(data_class,), source_kind="operational_material"),
        ),
    ]
    manifests = [
        _manifest("manifest.subject", "subject", [subject]),
        _manifest("manifest.configuration", "configuration", [configuration]),
        _manifest("manifest.runtime", "runtime_path", runtime_entries),
    ]
    scope_digest_value = digest_value(
        sorted(manifests, key=lambda item: (item["manifest_kind"], item["manifest_id"]))
    )

    purpose = build_purpose(
        purpose_id="purpose.audit",
        version="1",
        description="Process only the declared fields for the declared audit purpose.",
        allowed_data_classes=[data_class],
    )
    destination_kinds = ("processor", sink_kind, "retention")
    destinations = [
        build_destination(
            destination_id=f"destination.{kind}",
            version="1",
            component_kind=kind,
            external=(kind == "processor" and runtime_processor_external),
            allowed_data_classes=[
                sink_allowed_class
                if kind == sink_kind and sink_allowed_class is not None
                else data_class
            ],
            allowed_purpose_refs=["purpose.audit"],
        )
        for kind in destination_kinds
    ]
    retention = build_retention_rule(
        retention_id="retention.declared",
        version="1",
        data_classes=[data_class],
        maximum_seconds=3600,
        deletion_evidence_required=True,
    )
    controls = [
        build_control_profile(
            control_id=f"control.{kind}",
            version="1",
            control_kind=kind,
            requirements=[f"Evidence for {kind} is required."],
        )
        for kind in CONTROL_KINDS
    ]
    triggers = [
        build_requalification_trigger(
            trigger_id=f"trigger.{dimension}",
            version="1",
            dimension=dimension,
            condition=f"Requalify whenever {dimension} changes.",
            required_evidence_kinds=["runtime_observation"],
        )
        for dimension in REQUALIFICATION_DIMENSIONS
    ]
    decision_id = "decision.secure-profile"
    profile = build_secure_operation_profile(
        profile_id="profile.secure-operation",
        profile_version="1",
        status=profile_status,
        decision_record_ref=None if profile_status == "pending" else decision_id,
        purposes=[purpose],
        destination_allowlist=destinations,
        retention_rules=[retention],
        classification_policy={
            "redaction_required_classes": ["personal", "secret"],
            "encryption_in_transit_required_classes": [data_class],
            "encryption_at_rest_required_classes": [data_class],
            "external_transmission_allowed_classes": ["public"],
            "prohibited_log_classes": ["secret"],
            "raw_secret_material_prohibited": True,
        },
        control_profiles=controls,
        requalification_triggers=triggers,
        max_evidence_age_seconds=14_400,
    )
    decisions: list[dict[str, object]] = []
    if include_decision and profile_status != "pending":
        decisions.append(
            _decision(
                decision_id=decision_id,
                decision_kind=(
                    "adopt_secure_operation_profile"
                    if profile_status == "adopted"
                    else "retire_secure_operation_profile"
                ),
                profile=profile,
                scope_digest_value=scope_digest_value,
            )
        )

    processor_external = (
        runtime_processor_external
        if component_processor_external is None
        else component_processor_external
    )
    components = [
        build_flow_component(
            component_id="component.source",
            component_kind="source",
            runtime_entry_ref="runtime.source",
            destination_ref=None,
            external=False,
            persistent=False,
            privileged=False,
            retention_rule_ref=None,
            encryption_at_rest="not_applicable",
            least_privilege_scopes=[],
            credential_binding_ref=None,
        ),
        build_flow_component(
            component_id="component.processor",
            component_kind="processor",
            runtime_entry_ref="runtime.processor",
            destination_ref="destination.processor",
            external=processor_external,
            persistent=False,
            privileged=False,
            retention_rule_ref=None,
            encryption_at_rest="not_applicable",
            least_privilege_scopes=[],
            credential_binding_ref=None,
        ),
        build_flow_component(
            component_id="component.sink",
            component_kind=sink_kind,
            runtime_entry_ref="runtime.sink",
            destination_ref=f"destination.{sink_kind}",
            external=False,
            persistent=True,
            privileged=False,
            retention_rule_ref=(
                None if missing_sink_retention else "retention.declared"
            ),
            encryption_at_rest="applied",
            least_privilege_scopes=[],
            credential_binding_ref=None,
        ),
        build_flow_component(
            component_id="component.retention",
            component_kind="retention",
            runtime_entry_ref="runtime.retention",
            destination_ref="destination.retention",
            external=False,
            persistent=False,
            privileged=False,
            retention_rule_ref="retention.declared",
            encryption_at_rest="not_applicable",
            least_privilege_scopes=[],
            credential_binding_ref=None,
        ),
    ]
    data = build_data_item(
        data_id="data.input",
        data_class=data_class,
        subject_entry_ref="subject.input",
        source_component_ref="component.source",
        allowed_purpose_refs=["purpose.audit"],
        field_names=["body"],
    )
    stages = (
        ("source-processor", "component.source", "component.processor"),
        ("processor-sink", "component.processor", "component.sink"),
        ("sink-retention", "component.sink", "component.retention"),
    )
    flows: list[dict[str, object]] = []
    observations: list[dict[str, object]] = []
    evidence: list[dict[str, object]] = []
    for suffix, source_ref, target_ref in stages:
        flow_id = f"flow.{suffix}"
        observation_id = f"observation.{suffix}"
        evidence_id = f"evidence.{suffix}"
        flow = build_information_flow(
            flow_id=flow_id,
            data_ref="data.input",
            from_component_ref=source_ref,
            to_component_ref=target_ref,
            purpose_ref="purpose.audit",
            transmitted_fields=["body"],
            minimization="applied",
            redaction=(
                "applied" if data_class in {"personal", "secret"} else "not_applicable"
            ),
            encryption_in_transit="applied",
            credential_binding_ref=None,
            evidence_refs=[evidence_id],
        )
        observation = build_flow_observation(
            observation_id=observation_id,
            flow=flow,
            evidence_refs=[evidence_id],
        )
        flows.append(flow)
        observations.append(observation)
        evidence.append(
            _evidence(
                evidence_id,
                "information_flow_observation",
                scope_digest_value,
                [flow_id, observation_id],
            )
        )

    trigger_evidence_id = "evidence.triggers"
    control_evidence_kinds = {
        "encryption": "control_test",
        "credential": "control_test",
        "least_privilege": "control_test",
        "dependency": "dependency_scan",
        "resource_limit": "resource_test",
        "denial_of_service": "dos_test",
        "incident_response": "incident_rehearsal",
        "notification": "notification_rehearsal",
    }
    control_evidence_refs = {
        str(control["control_id"]): f"evidence.control.{control['control_kind']}"
        for control in controls
    }
    evidence.extend(
        _evidence(
            control_evidence_refs[str(control["control_id"])],
            control_evidence_kinds[str(control["control_kind"])],
            scope_digest_value,
            [str(control["control_id"])],
        )
        for control in controls
    )
    retention_observation_id = "observation.retention-sink"
    retention_evidence_refs = ["evidence.retention", "evidence.deletion"]
    evidence.extend(
        [
            _evidence(
                SCOPE_EVIDENCE_ID,
                "scope_inventory",
                scope_digest_value,
                [str(item["manifest_id"]) for item in manifests],
                observer_ref=INVENTORY_AUTHORITY_REF,
            ),
            _evidence(
                trigger_evidence_id,
                "runtime_observation",
                scope_digest_value,
                [str(trigger["trigger_id"]) for trigger in triggers],
            ),
        ]
    )
    retention_observations: list[dict[str, object]] = []
    if not missing_sink_retention:
        evidence.extend(
            [
                _evidence(
                    retention_evidence_refs[0],
                    "retention_test",
                    scope_digest_value,
                    [retention_observation_id],
                ),
                _evidence(
                    retention_evidence_refs[1],
                    "deletion_test",
                    scope_digest_value,
                    [retention_observation_id],
                ),
            ]
        )
        retention_observations.append(
            build_retention_observation(
                observation_id=retention_observation_id,
                component_ref="component.sink",
                retention_rule=retention,
                configured_maximum_seconds=3600,
                deletion_evidence_present=True,
                evidence_refs=retention_evidence_refs,
            )
        )
    if include_review:
        evidence.append(
            _evidence(
                REVIEW_EVIDENCE_ID,
                "independent_review",
                scope_digest_value,
                [REVIEW_ID],
                trust_class="independently_observed",
                relationship="independent",
                observer_ref=REVIEWER_REF,
            )
        )
    contract = {
        "kind": "adopted_profile",
        "profile": profile,
        "data_items": [data],
        "components": components,
        "declared_flows": flows,
        "flow_observations": observations,
        "retention_observations": retention_observations,
        "control_results": [
            build_control_result(
                control=control,
                status="satisfied",
                evidence_refs=[control_evidence_refs[str(control["control_id"])]],
            )
            for control in controls
        ],
        "trigger_assessments": [
            build_trigger_assessment(
                trigger=trigger,
                status="not_observed",
                evidence_refs=[trigger_evidence_id],
            )
            for trigger in triggers
        ],
    }
    return _finalize(
        path="adopted_profile",
        claimed_environment="development",
        manifests=manifests,
        evidence=evidence,
        decisions=decisions,
        unresolved_scope=unresolved_scope or [],
        contract=contract,
        include_review=include_review,
    )


def _nonapplicable_bundle(
    *,
    profile_status: str = "adopted",
    include_decision: bool = True,
    include_review: bool = True,
    claimed_environment: str = "local_fixture",
    condition_trust: str = "tool_observed",
    observed_at: str = OBSERVED_AT,
    restart_matches: bool = True,
    restart_before_matches: bool = True,
    restart_observed_at: str | None = None,
    external_provider: bool = False,
    real_material: bool = False,
    subject_source_kind: str | None = None,
    durable: bool = False,
    sensitive: bool = False,
    subject_classes: tuple[str, ...] | None = None,
    privileged: bool = False,
    unresolved_scope: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    effective_subject_classes = (
        subject_classes
        if subject_classes is not None
        else (("internal",) if sensitive else ("synthetic",))
    )
    subject = _entry(
        "subject.fixture",
        "subject",
        _attributes(
            data_classes=effective_subject_classes,
            source_kind=(
                subject_source_kind
                if subject_source_kind is not None
                else ("operational_material" if real_material else "synthetic")
            ),
            real_material=real_material,
        ),
    )
    configuration = _entry(
        "configuration.local",
        "configuration",
        _attributes(source_kind="local_fixture"),
    )
    runtime = _entry(
        "runtime.local",
        "runtime_path",
        _attributes(
            source_kind="local_fixture",
            execution_location="external" if external_provider else "local",
            external_provider=external_provider,
            durable=durable,
            persistent_artifact=durable,
            privileged=privileged,
        ),
    )
    manifests = [
        _manifest("manifest.subject", "subject", [subject]),
        _manifest("manifest.configuration", "configuration", [configuration]),
        _manifest("manifest.runtime", "runtime_path", [runtime]),
    ]
    scope_digest_value = digest_value(
        sorted(manifests, key=lambda item: (item["manifest_kind"], item["manifest_id"]))
    )
    decision_id = "decision.nonapplicability"
    profile = build_nonapplicability_profile(
        profile_id="profile.local-nonapplicability",
        profile_version="1",
        status=profile_status,
        decision_record_ref=None if profile_status == "pending" else decision_id,
        max_evidence_age_seconds=14_400,
    )
    decisions: list[dict[str, object]] = []
    if include_decision and profile_status != "pending":
        decisions.append(
            _decision(
                decision_id=decision_id,
                decision_kind=(
                    "select_nonapplicability_boundary"
                    if profile_status == "adopted"
                    else "retire_nonapplicability_boundary"
                ),
                profile=profile,
                scope_digest_value=scope_digest_value,
            )
        )
    runtime_condition_evidence_id = "evidence.boundary-runtime"
    restart_evidence_id = "evidence.restart"
    evidence_relationship = (
        "self" if condition_trust == "self_reported" else "tool_observer"
    )
    evidence = [
        _evidence(
            SCOPE_EVIDENCE_ID,
            "scope_inventory",
            scope_digest_value,
            [
                *(str(item["manifest_id"]) for item in manifests),
                "synthetic",
                "no_sensitive",
            ],
            trust_class=condition_trust,
            relationship=evidence_relationship,
            observed_at=observed_at,
            observer_ref=INVENTORY_AUTHORITY_REF,
        ),
        _evidence(
            runtime_condition_evidence_id,
            "runtime_observation",
            scope_digest_value,
            ["local", "nonprivileged", "nondurable", "no_external"],
            trust_class=condition_trust,
            relationship=evidence_relationship,
            observed_at=observed_at,
        ),
        _evidence(
            restart_evidence_id,
            "restart_test",
            scope_digest_value,
            ["test.restart-boundary"],
            trust_class=condition_trust,
            relationship=evidence_relationship,
            observed_at=observed_at,
        ),
    ]
    if include_review:
        evidence.append(
            _evidence(
                REVIEW_EVIDENCE_ID,
                "independent_review",
                scope_digest_value,
                [REVIEW_ID],
                trust_class="independently_observed",
                relationship="independent",
                observed_at=observed_at,
                observer_ref=REVIEWER_REF,
            )
        )
    configuration_digest = manifests[1]["manifest_digest"]
    runtime_digest = manifests[2]["manifest_digest"]
    restart = build_restart_test(
        test_id="test.restart-boundary",
        before_configuration_digest=(
            configuration_digest
            if restart_before_matches
            else digest_value("changed-before")
        ),
        before_runtime_path_digest=runtime_digest,
        after_configuration_digest=(
            configuration_digest if restart_matches else digest_value("changed")
        ),
        after_runtime_path_digest=runtime_digest,
        status="passed",
        observed_at=restart_observed_at or observed_at,
        expires_at=EXPIRES_AT,
        time_trust="trusted",
        evidence_refs=[restart_evidence_id],
    )
    synthetic_scope = (
        set(effective_subject_classes) <= {"synthetic"}
        and not real_material
        and (
            subject_source_kind
            if subject_source_kind is not None
            else ("operational_material" if real_material else "synthetic")
        )
        in {"synthetic", "local_fixture", "not_applicable"}
    )
    condition_statuses = {
        "synthetic": synthetic_scope,
        "local": not external_provider,
        "nonprivileged": not privileged,
        "nondurable": not durable,
        "no_external": not external_provider,
        "no_sensitive": not bool(
            set(effective_subject_classes)
            & {"internal", "confidential", "personal", "secret"}
        ),
    }
    contract = {
        "kind": "verified_nonapplicability",
        "profile": profile,
        "condition_results": [
            build_condition_result(
                condition_id=condition,
                status=(
                    "confirmed" if condition_statuses[condition] else "refuted"
                ),
                scope_digest_value=scope_digest_value,
                evidence_refs=[
                    SCOPE_EVIDENCE_ID
                    if condition in {"synthetic", "no_sensitive"}
                    else runtime_condition_evidence_id
                ],
            )
            for condition in NONAPPLICABILITY_CONDITIONS
        ],
        "restart_test": restart,
    }
    return _finalize(
        path="verified_nonapplicability",
        claimed_environment=claimed_environment,
        manifests=manifests,
        evidence=evidence,
        decisions=decisions,
        unresolved_scope=unresolved_scope or [],
        contract=contract,
        include_review=include_review,
    )


def _codes(bundle: dict[str, object]) -> set[str]:
    return {item["code"] for item in secure_operation_errors(bundle)}


def _redigest(value: dict[str, object], digest_field: str) -> None:
    value[digest_field] = digest_value(
        {key: item for key, item in value.items() if key != digest_field}
    )


def test_adopted_profile_closes_flow_and_preserves_authority_boundary() -> None:
    bundle = _adopted_bundle()

    assert validate_secure_operation(bundle) == bundle
    assert bundle["result"]["status"] == "declared_profile_internally_consistent"
    assert bundle["result"]["reason_codes"] == []
    assert "external_human_decision_authenticity_unproved" in bundle["result"][
        "unproved_claim_codes"
    ]
    assert bundle["authority_boundary"] == {
        "semantic_guard_role": "audit_declared_information_handling_only",
        "adopt_policy": False,
        "verify_external_authenticity": False,
        "strong_positive_claims_enabled": False,
        "determine_classification_truth": False,
        "issue_credentials": False,
        "transmit_external_data": False,
        "declare_incident": False,
        "accept_risk": False,
        "final_acceptance_owner": "human",
    }
    assert _adopted_bundle() == bundle


def test_unverified_strings_cannot_encode_legacy_strong_positive_status() -> None:
    bundle = _adopted_bundle()
    bundle["result"]["status"] = "profile_controls_satisfied"
    _redigest(bundle["result"], "result_digest")
    _redigest(bundle, "assessment_digest")

    assert "schema_validation_failed" in _codes(bundle)


def test_verified_nonapplicability_requires_all_observed_boundaries() -> None:
    bundle = _nonapplicable_bundle()

    assert validate_secure_operation(bundle) == bundle
    assert bundle["result"]["status"] == (
        "declared_nonapplicability_internally_consistent"
    )
    assert "independent_review_authenticity_unproved" in bundle["result"][
        "unproved_claim_codes"
    ]
    assert bundle["result"]["reactivation_triggers"] == []
    assert _nonapplicable_bundle() == bundle


def test_profile_lifecycle_never_implies_adoption() -> None:
    for status in ("pending", "retired"):
        bundle = _adopted_bundle(profile_status=status)

        assert validate_secure_operation(bundle) == bundle
        assert bundle["result"]["status"] == "not_established"
        assert "profile_not_adopted" in bundle["result"]["reason_codes"]


def test_adopted_profile_without_exact_human_record_is_rejected() -> None:
    bundle = _adopted_bundle(include_decision=False)

    assert "effective_policy_decision_mismatch" in _codes(bundle)


def test_missing_flow_observation_fails_exact_coverage() -> None:
    bundle = _adopted_bundle()
    contract = copy.deepcopy(bundle["path_contract"])
    contract["flow_observations"].pop()
    rebuilt = _reassess(bundle, contract=contract)

    assert "flow_exact_coverage_mismatch" in _codes(rebuilt)


def test_substituted_flow_observation_is_detected() -> None:
    bundle = _adopted_bundle()
    contract = copy.deepcopy(bundle["path_contract"])
    observation = contract["flow_observations"][0]
    observation["flow_digest"] = copy.deepcopy(
        contract["declared_flows"][1]["flow_digest"]
    )
    observation["observation_digest"] = digest_value(
        {key: value for key, value in observation.items() if key != "observation_digest"}
    )
    rebuilt = _reassess(bundle, contract=contract)

    assert "flow_observation_substitution" in _codes(rebuilt)


def test_classification_laundering_is_a_hard_integrity_failure() -> None:
    bundle = _adopted_bundle(
        subject_classes=("confidential",),
        data_class="public",
    )

    assert "classification_laundering" in _codes(bundle)


def test_hidden_external_llm_cannot_be_laundered_as_local_component() -> None:
    bundle = _adopted_bundle(
        runtime_processor_external=True,
        component_processor_external=False,
    )

    assert "component_runtime_binding_mismatch" in _codes(bundle)


def test_runtime_inventory_cannot_hide_an_unmapped_component() -> None:
    bundle = _adopted_bundle()
    contract = copy.deepcopy(bundle["path_contract"])
    contract["components"] = [
        component
        for component in contract["components"]
        if component["component_id"] != "component.processor"
    ]
    rebuilt = _reassess(bundle, contract=contract)

    assert "runtime_component_exact_coverage_mismatch" in _codes(rebuilt)


def test_internal_destination_allowlist_applies_class_and_purpose_scope() -> None:
    bundle = _adopted_bundle(sink_allowed_class="synthetic")

    assert validate_secure_operation(bundle) == bundle
    assert bundle["result"]["status"] == "not_established"
    assert "destination_scope_not_allowed" in bundle["result"]["reason_codes"]


def test_persistent_artifact_without_retention_is_not_satisfied() -> None:
    bundle = _adopted_bundle(missing_sink_retention=True)

    assert validate_secure_operation(bundle) == bundle
    assert bundle["result"]["status"] == "not_established"
    assert "retention_rule_missing" in bundle["result"]["reason_codes"]


def test_secret_log_is_explicitly_rejected_even_when_other_controls_pass() -> None:
    bundle = _adopted_bundle(
        subject_classes=("secret",),
        data_class="secret",
        sink_kind="log",
    )

    assert validate_secure_operation(bundle) == bundle
    assert bundle["result"]["status"] == "not_established"
    assert "prohibited_data_class_logged" in bundle["result"]["reason_codes"]


def test_policy_digest_mutation_breaks_human_decision_binding() -> None:
    bundle = _adopted_bundle()
    bundle["path_contract"]["profile"]["classification_policy"][
        "prohibited_log_classes"
    ] = ["personal", "secret"]

    assert {
        "assessment_digest_mismatch",
        "profile_basis_digest_mismatch",
        "profile_digest_mismatch",
    }.issubset(_codes(bundle))


def test_forged_nonapplicability_result_cannot_override_replay() -> None:
    bundle = _nonapplicable_bundle()
    result = bundle["result"]
    result["status"] = "reactivated"
    result["result_digest"] = digest_value(
        {key: value for key, value in result.items() if key != "result_digest"}
    )
    bundle["assessment_digest"] = digest_value(
        {key: value for key, value in bundle.items() if key != "assessment_digest"}
    )

    assert _codes(bundle) == {"result_replay_mismatch"}


def test_stale_evidence_never_establishes_nonapplicability() -> None:
    bundle = _nonapplicable_bundle(observed_at="2026-07-16T06:00:00Z")

    assert validate_secure_operation(bundle) == bundle
    assert bundle["result"]["status"] == "not_established"
    assert "condition_evidence_not_current_or_trusted" in bundle["result"][
        "reason_codes"
    ]


def test_restart_binding_change_automatically_reactivates_profile() -> None:
    bundle = _nonapplicable_bundle(restart_matches=False)

    assert validate_secure_operation(bundle) == bundle
    assert bundle["result"]["status"] == "reactivated"
    assert "restart_binding_mismatch" in bundle["result"][
        "reactivation_triggers"
    ]


def test_fixture_evidence_cannot_generalize_to_production() -> None:
    bundle = _nonapplicable_bundle(claimed_environment="production")

    assert validate_secure_operation(bundle) == bundle
    assert bundle["result"]["status"] == "reactivated"
    assert "production_scope_requested" in bundle["result"][
        "reactivation_triggers"
    ]


def test_public_source_kind_reactivates_even_if_real_flag_is_laundered() -> None:
    bundle = _nonapplicable_bundle(
        subject_source_kind="public_material",
        real_material=False,
    )

    assert validate_secure_operation(bundle) == bundle
    assert bundle["result"]["status"] == "reactivated"
    assert "real_material_observed" in bundle["result"][
        "reactivation_triggers"
    ]


def test_self_reported_declarations_never_establish_nonapplicability() -> None:
    bundle = _nonapplicable_bundle(condition_trust="self_reported")

    assert validate_secure_operation(bundle) == bundle
    assert bundle["result"]["status"] == "not_established"
    assert "condition_evidence_not_current_or_trusted" in bundle["result"][
        "reason_codes"
    ]


def test_independent_review_is_mandatory_for_declared_internal_consistency() -> None:
    bundle = _nonapplicable_bundle(include_review=False)

    assert validate_secure_operation(bundle) == bundle
    assert bundle["result"]["status"] == "not_established"
    assert "independent_review_not_established" in bundle["result"][
        "reason_codes"
    ]


def test_unresolved_scope_is_preserved_and_blocks_nonapplicability() -> None:
    unresolved = {
        "scope_id": "scope.unknown-sidecar",
        "blocking": False,
        "owner_kind": "human",
        "reason": "A possible sidecar path has not been observed.",
        "evidence_refs": [],
    }
    bundle = _nonapplicable_bundle(unresolved_scope=[unresolved])

    assert validate_secure_operation(bundle) == bundle
    assert bundle["result"]["status"] == "not_established"
    assert bundle["result"]["unresolved_scope_refs"] == [
        "scope.unknown-sidecar"
    ]


def test_observed_boundary_change_automatically_reactivates() -> None:
    cases = [
        ({"external_provider": True}, "external_provider_observed"),
        ({"real_material": True}, "real_material_observed"),
        ({"durable": True}, "durable_output_observed"),
        ({"sensitive": True}, "sensitive_data_observed"),
        ({"privileged": True}, "privilege_observed"),
    ]
    for kwargs, trigger in cases:
        bundle = _nonapplicable_bundle(**kwargs)

        assert validate_secure_operation(bundle) == bundle
        assert bundle["result"]["status"] == "reactivated"
        assert trigger in bundle["result"]["reactivation_triggers"]


def test_latest_retirement_overrides_earlier_adoption_for_same_basis_and_scope() -> None:
    bundle = _adopted_bundle()
    profile = bundle["path_contract"]["profile"]
    bundle["human_decision_records"].append(
        _decision(
            decision_id="decision.secure-profile.retire",
            decision_kind="retire_secure_operation_profile",
            profile=profile,
            scope_digest_value=bundle["scope_digest"],
            decision_sequence=2,
            decided_at="2026-07-16T12:45:00Z",
        )
    )
    rebuilt = _reassess(bundle)

    assert "effective_policy_decision_mismatch" in _codes(rebuilt)
    assert rebuilt["result"]["status"] == "not_established"


def test_same_sequence_policy_conflict_is_rejected() -> None:
    bundle = _adopted_bundle()
    profile = bundle["path_contract"]["profile"]
    bundle["human_decision_records"].append(
        _decision(
            decision_id="decision.secure-profile.conflict",
            decision_kind="retire_secure_operation_profile",
            profile=profile,
            scope_digest_value=bundle["scope_digest"],
            decision_sequence=1,
        )
    )
    rebuilt = _reassess(bundle)

    assert "conflicting_policy_decisions" in _codes(rebuilt)


def test_policy_decision_is_bound_to_exact_scope_digest() -> None:
    bundle = _adopted_bundle()
    decision = bundle["human_decision_records"][0]
    decision["target_scope_digest"] = digest_value("different-scope")
    _redigest(decision, "decision_digest")
    rebuilt = _reassess(bundle)

    assert "effective_policy_decision_mismatch" in _codes(rebuilt)


def test_self_observer_cannot_launder_itself_as_tool_observed() -> None:
    bundle = _nonapplicable_bundle()
    evidence = next(
        item
        for item in bundle["evidence_observations"]
        if item["evidence_id"] == "evidence.boundary-runtime"
    )
    evidence["observer"]["relationship_to_subject"] = "self"
    _redigest(evidence, "evidence_digest")
    rebuilt = _reassess(bundle)

    assert "evidence_trust_relationship_mismatch" in _codes(rebuilt)


def test_public_class_cannot_be_confirmed_as_synthetic_scope() -> None:
    bundle = _nonapplicable_bundle(subject_classes=("public",))

    assert validate_secure_operation(bundle) == bundle
    assert bundle["result"]["status"] == "not_established"
    synthetic = next(
        item
        for item in bundle["path_contract"]["condition_results"]
        if item["condition_id"] == "synthetic"
    )
    synthetic["status"] = "confirmed"
    _redigest(synthetic, "result_digest")
    rebuilt = _reassess(bundle)

    assert "nonapplicability_condition_scope_contradiction" in _codes(rebuilt)


def test_restart_before_digest_change_reactivates() -> None:
    bundle = _nonapplicable_bundle(restart_before_matches=False)

    assert validate_secure_operation(bundle) == bundle
    assert bundle["result"]["status"] == "reactivated"
    assert "restart_binding_mismatch" in bundle["result"][
        "reactivation_triggers"
    ]


def test_restart_record_itself_obeys_profile_maximum_age() -> None:
    bundle = _nonapplicable_bundle(
        restart_observed_at="2026-07-16T06:00:00Z"
    )

    assert validate_secure_operation(bundle) == bundle
    assert bundle["result"]["status"] == "not_established"
    assert "restart_test_not_current_or_trusted" in bundle["result"][
        "reason_codes"
    ]


def test_condition_claim_rejects_unrelated_evidence_kind() -> None:
    bundle = _nonapplicable_bundle()
    evidence = next(
        item
        for item in bundle["evidence_observations"]
        if item["evidence_id"] == "evidence.boundary-runtime"
    )
    evidence["evidence_kind"] = "control_test"
    _redigest(evidence, "evidence_digest")
    rebuilt = _reassess(bundle)

    assert "evidence_kind_not_allowed_for_claim" in _codes(rebuilt)


def test_inventory_evidence_must_match_declared_inventory_authority() -> None:
    bundle = _adopted_bundle()
    evidence = next(
        item
        for item in bundle["evidence_observations"]
        if item["evidence_id"] == SCOPE_EVIDENCE_ID
    )
    evidence["observer"]["observer_ref"] = versioned_ref("authority.other", "1")
    _redigest(evidence, "evidence_digest")
    rebuilt = _reassess(bundle)

    assert "inventory_evidence_authority_mismatch" in _codes(rebuilt)


def test_trigger_claim_enforces_profile_required_evidence_kind() -> None:
    bundle = _adopted_bundle()
    evidence = next(
        item
        for item in bundle["evidence_observations"]
        if item["evidence_id"] == "evidence.triggers"
    )
    evidence["evidence_kind"] = "control_test"
    _redigest(evidence, "evidence_digest")
    rebuilt = _reassess(bundle)

    assert {
        "evidence_kind_not_allowed_for_claim",
        "trigger_required_evidence_kind_missing",
    }.issubset(_codes(rebuilt))


def test_independent_review_requires_review_kind_and_same_observer_identity() -> None:
    bundle = _nonapplicable_bundle()
    evidence = next(
        item
        for item in bundle["evidence_observations"]
        if item["evidence_id"] == REVIEW_EVIDENCE_ID
    )
    evidence["evidence_kind"] = "control_test"
    evidence["observer"]["observer_ref"] = versioned_ref("observer.other", "1")
    _redigest(evidence, "evidence_digest")
    rebuilt = _reassess(bundle)
    codes = _codes(rebuilt)

    assert "independent_review_evidence_kind_mismatch" in codes
    assert "reviewer_evidence_identity_mismatch" in codes


def test_missing_retention_observation_blocks_internal_consistency() -> None:
    bundle = _adopted_bundle()
    contract = copy.deepcopy(bundle["path_contract"])
    contract["retention_observations"] = []
    evidence = [
        item
        for item in bundle["evidence_observations"]
        if item["evidence_id"] not in {"evidence.retention", "evidence.deletion"}
    ]
    rebuilt = _finalize(
        path="adopted_profile",
        claimed_environment="development",
        manifests=copy.deepcopy(bundle["scope_manifests"]),
        evidence=copy.deepcopy(evidence),
        decisions=copy.deepcopy(bundle["human_decision_records"]),
        unresolved_scope=[],
        contract=contract,
        include_review=True,
    )

    assert validate_secure_operation(rebuilt) == rebuilt
    assert rebuilt["result"]["status"] == "not_established"
    assert "retention_effect_unproved" in rebuilt["result"]["reason_codes"]


def test_required_deletion_evidence_cannot_be_omitted() -> None:
    bundle = _adopted_bundle()
    contract = copy.deepcopy(bundle["path_contract"])
    observation = contract["retention_observations"][0]
    observation["deletion_evidence_present"] = False
    observation["evidence_refs"] = ["evidence.retention"]
    _redigest(observation, "observation_digest")
    evidence = [
        item
        for item in bundle["evidence_observations"]
        if item["evidence_id"] != "evidence.deletion"
    ]
    rebuilt = _finalize(
        path="adopted_profile",
        claimed_environment="development",
        manifests=copy.deepcopy(bundle["scope_manifests"]),
        evidence=copy.deepcopy(evidence),
        decisions=copy.deepcopy(bundle["human_decision_records"]),
        unresolved_scope=[],
        contract=contract,
        include_review=True,
    )

    assert "retention_required_evidence_kind_missing" in _codes(rebuilt)
    assert rebuilt["result"]["status"] == "not_established"


def test_deep_flow_graph_uses_iterative_evaluation() -> None:
    count = 1400
    components = {
        f"component.{index}": {"component_kind": "processor"}
        for index in range(count)
    }
    components["component.0"]["component_kind"] = "source"
    components[f"component.{count - 1}"]["component_kind"] = "retention"
    flows = [
        {
            "data_ref": "data.deep",
            "from_component_ref": f"component.{index}",
            "to_component_ref": f"component.{index + 1}",
        }
        for index in range(count - 1)
    ]

    assert _graph_reaches_retention(
        "data.deep", "component.0", flows, components
    )


def test_collection_limit_fails_before_expensive_replay() -> None:
    bundle = _nonapplicable_bundle()
    bundle["evidence_observations"] = [
        copy.deepcopy(bundle["evidence_observations"][0]) for _ in range(4097)
    ]

    assert _codes(bundle) == {"input_resource_limit_exceeded"}


def load_tests(
    loader: unittest.TestLoader,
    tests: unittest.TestSuite,
    pattern: str | None,
) -> unittest.TestSuite:
    """Expose the function cases to the standard-library unittest runner."""

    del loader, tests, pattern
    suite = unittest.TestSuite()
    for name, function in sorted(globals().items()):
        if name.startswith("test_") and callable(function):
            suite.addTest(unittest.FunctionTestCase(function, description=name))
    return suite
