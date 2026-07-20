from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import unittest

from semantic_guard.operational_qualification import (
    OperationalQualificationError,
    REQUIRED_SCENARIOS,
    SCENARIO_EXECUTION_POLICY,
    STATEFUL_SCENARIOS,
    build_deployment_envelope,
    build_operational_profile,
    build_operational_qualification,
    build_scenario_observation,
    build_scenario_threshold,
    validate_operational_profile,
    validate_operational_qualification,
)


def digest(label: str) -> dict[str, str]:
    return {
        "algorithm": "sha256",
        "value": hashlib.sha256(label.encode("utf-8")).hexdigest(),
    }


def refresh_digest(value: dict, field: str) -> None:
    material = deepcopy(value)
    material.pop(field, None)
    encoded = json.dumps(
        material,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    value[field] = {
        "algorithm": "sha256",
        "value": hashlib.sha256(encoded).hexdigest(),
    }


def manifest_ref(kind: str, suffix: str = "a") -> dict:
    return {
        "manifest_id": f"manifest.{kind}.{suffix}",
        "manifest_version": "1",
        "manifest_digest": digest(f"manifest-{kind}-{suffix}"),
    }


def identity(name: str) -> dict:
    return {
        "entity_id": f"actor.{name}",
        "entity_version": "1",
        "content_digest": digest(f"actor-{name}"),
    }


def raw_evidence(name: str) -> dict:
    return {
        "evidence_id": f"evidence.{name}",
        "locator": f"evidence/{name}.json",
        "evidence_kind": "execution_log",
        "content_digest": digest(f"evidence-{name}"),
    }


def human_decision(
    kind: str,
    target_id: str,
    target_version: str,
    target_digest: dict,
    label: str,
    *,
    decided_at: str = "2026-07-16T00:00:00Z",
) -> dict:
    return {
        "decision_id": f"decision.{label}",
        "decision_kind": kind,
        "decision_source": "external_human_record",
        "actor_kind": "human",
        "decided_by": "human.owner",
        "decided_at": decided_at,
        "status": "accepted",
        "target_id": target_id,
        "target_version": target_version,
        "target_digest": deepcopy(target_digest),
        "trust_class": "signed",
        "record_ref": {
            "record_id": f"record.{label}",
            "locator": f"decisions/{label}.json",
            "content_digest": digest(f"decision-record-{label}"),
        },
    }


class OperationalQualificationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.scope = {
            f"{kind}_manifest_ref": manifest_ref(kind)
            for kind in (
                "subject",
                "environment",
                "dependency",
                "provider",
                "configuration",
            )
        }
        pending = build_operational_profile(
            profile_id="profile.operational",
            profile_version="1",
            adoption_state="pending",
            max_evidence_age_seconds=7200,
        )
        self.profile = build_operational_profile(
            profile_id="profile.operational",
            profile_version="1",
            adoption_state="adopted",
            max_evidence_age_seconds=7200,
            adoption_decision_ref=human_decision(
                "adopt_operational_profile",
                "profile.operational",
                "1",
                pending["profile_basis_digest"],
                "profile-adoption",
            ),
        )
        self.thresholds = [
            build_scenario_threshold(
                threshold_id=f"threshold.{scenario}",
                threshold_version="1",
                scenario_id=scenario,
                metric=f"metric.{scenario}",
                comparator="lte",
                target_value=10,
                unit="count",
                observation_window_seconds=60,
            )
            for scenario in REQUIRED_SCENARIOS
        ]
        pending_envelope = build_deployment_envelope(
            envelope_id="envelope.service",
            envelope_version="1",
            operational_profile=self.profile,
            selected_mode="service",
            platform_manifest_ref=self.scope["environment_manifest_ref"],
            scenario_thresholds=self.thresholds,
        )
        self.envelope = build_deployment_envelope(
            envelope_id="envelope.service",
            envelope_version="1",
            operational_profile=self.profile,
            selected_mode="service",
            platform_manifest_ref=self.scope["environment_manifest_ref"],
            scenario_thresholds=self.thresholds,
            selection_decision_ref=human_decision(
                "select_deployment_envelope",
                "envelope.service",
                "1",
                pending_envelope["envelope_basis_digest"],
                "envelope-selection",
            ),
        )
        self.observations = self._observations()

    def _observations(
        self,
        *,
        suffix: str = "a",
        envelope: dict | None = None,
        scope: dict | None = None,
    ) -> list[dict]:
        used_envelope = envelope or self.envelope
        used_scope = scope or self.scope
        thresholds = used_envelope["scenario_thresholds"]
        return [
            build_scenario_observation(
                observation_id=f"observation.{scenario}.{suffix}",
                execution_id=f"execution.{scenario}.{suffix}",
                threshold=threshold,
                deployment_envelope=used_envelope,
                scope_manifest_refs=used_scope,
                execution_kind=SCENARIO_EXECUTION_POLICY[scenario][0],
                evidence_origin="controlled_execution",
                status="passed",
                observed_at="2026-07-16T00:10:00Z",
                expires_at="2026-07-16T02:10:00Z",
                time_trust="trusted",
                measured_value=5,
                executor_ref=identity("executor"),
                raw_evidence_refs=[raw_evidence(f"{scenario}-{suffix}")],
                before_state_digest=(
                    digest(f"before-{scenario}-{suffix}")
                    if scenario in STATEFUL_SCENARIOS
                    else None
                ),
                after_state_digest=(
                    digest(f"after-{scenario}-{suffix}")
                    if scenario in STATEFUL_SCENARIOS
                    else None
                ),
            )
            for scenario, threshold in zip(
                REQUIRED_SCENARIOS,
                thresholds,
                strict=True,
            )
        ]

    def _review(self, basis_digest: dict, *, reviewer: str = "reviewer") -> dict:
        review = {
            "schema_version": "independent-operational-review/v0",
            "review_id": f"review.{reviewer}",
            "review_source": "external_independent_record",
            "reviewer_ref": identity(reviewer),
            "reviewed_at": "2026-07-16T00:30:00Z",
            "status": "accepted",
            "target_qualification_id": "qualification.service",
            "target_qualification_version": "1",
            "target_basis_digest": deepcopy(basis_digest),
            "trust_class": "independently_observed",
            "raw_evidence_refs": [raw_evidence(f"review-{reviewer}")],
        }
        refresh_digest(review, "review_digest")
        return review

    def _qualification(
        self,
        *,
        observations: list[dict] | None = None,
        profile: dict | None = None,
        envelope: dict | None = None,
        scope: dict | None = None,
        previous: dict | None = None,
        authorize: bool = False,
    ) -> dict:
        used_observations = observations or self.observations
        used_profile = profile or self.profile
        used_envelope = envelope or self.envelope
        used_scope = scope or self.scope
        preliminary = build_operational_qualification(
            qualification_id="qualification.service",
            qualification_version="1",
            operational_profile=used_profile,
            deployment_envelope=used_envelope,
            scope_manifest_refs=used_scope,
            assessed_at="2026-07-16T01:00:00Z",
            time_trust="trusted",
            scenario_observations=used_observations,
            previous_qualification=previous,
        )
        review = self._review(preliminary["review_basis_digest"])
        eligible = build_operational_qualification(
            qualification_id="qualification.service",
            qualification_version="1",
            operational_profile=used_profile,
            deployment_envelope=used_envelope,
            scope_manifest_refs=used_scope,
            assessed_at="2026-07-16T01:00:00Z",
            time_trust="trusted",
            scenario_observations=used_observations,
            independent_review_record=review,
            previous_qualification=previous,
        )
        if not authorize:
            return eligible
        authorization = human_decision(
            "authorize_operational_use",
            "qualification.service",
            "1",
            eligible["authorization_basis_digest"],
            "operational-authorization",
            decided_at="2026-07-16T00:45:00Z",
        )
        return build_operational_qualification(
            qualification_id="qualification.service",
            qualification_version="1",
            operational_profile=used_profile,
            deployment_envelope=used_envelope,
            scope_manifest_refs=used_scope,
            assessed_at="2026-07-16T01:00:00Z",
            time_trust="trusted",
            scenario_observations=used_observations,
            independent_review_record=review,
            previous_qualification=previous,
            human_authorization_record=authorization,
        )

    def test_profile_lifecycle_requires_separate_external_human_records(self) -> None:
        pending = build_operational_profile(
            profile_id="profile.lifecycle",
            profile_version="1",
            adoption_state="pending",
            max_evidence_age_seconds=3600,
        )
        with self.assertRaisesRegex(
            OperationalQualificationError,
            "requires external human adoption",
        ):
            build_operational_profile(
                profile_id="profile.lifecycle",
                profile_version="1",
                adoption_state="adopted",
                max_evidence_age_seconds=3600,
            )
        adoption = human_decision(
            "adopt_operational_profile",
            "profile.lifecycle",
            "1",
            pending["profile_basis_digest"],
            "lifecycle-adoption",
        )
        retirement = human_decision(
            "retire_operational_profile",
            "profile.lifecycle",
            "1",
            pending["profile_basis_digest"],
            "lifecycle-retirement",
        )
        retired = build_operational_profile(
            profile_id="profile.lifecycle",
            profile_version="1",
            adoption_state="retired",
            max_evidence_age_seconds=3600,
            adoption_decision_ref=adoption,
            retirement_decision_ref=retirement,
        )
        validate_operational_profile(retired)

    def test_all_scenarios_independent_review_and_human_authorization_are_separate(self) -> None:
        eligible = self._qualification()
        self.assertEqual(eligible["outcome"], "eligible")
        self.assertEqual(eligible["eligibility"]["reasons"], [])
        self.assertEqual(
            eligible["independent_open_dimensions"],
            {
                "semantic_field_validity": "open",
                "security": "open",
                "human_acceptance": "open",
            },
        )
        self.assertFalse(eligible["authority_boundary"]["deploy"])

        authorized = self._qualification(authorize=True)
        self.assertEqual(authorized["outcome"], "human_authorized")
        validate_operational_qualification(
            authorized,
            operational_profile=self.profile,
            deployment_envelope=self.envelope,
            current_scope_manifest_refs=self.scope,
        )

    def test_missing_scenario_is_contract_invalid(self) -> None:
        with self.assertRaisesRegex(
            OperationalQualificationError,
            "every required scenario exactly once",
        ):
            self._qualification(observations=self.observations[:-1])

    def test_failed_not_run_out_of_scope_stale_and_synthetic_never_qualify(self) -> None:
        mutations = {
            "failed": lambda item: item.__setitem__("status", "failed"),
            "not_run": lambda item: item.__setitem__("status", "not_run"),
            "out_of_scope": lambda item: item.__setitem__("status", "out_of_scope"),
            "stale": lambda item: item.__setitem__(
                "expires_at", "2026-07-16T00:50:00Z"
            ),
            "synthetic": lambda item: item.__setitem__(
                "evidence_origin", "synthetic_fixture"
            ),
        }
        for label, mutation in mutations.items():
            with self.subTest(label=label):
                observations = deepcopy(self.observations)
                mutation(observations[0])
                refresh_digest(observations[0], "observation_digest")
                qualification = self._qualification(observations=observations)
                self.assertEqual(qualification["outcome"], "not_eligible")

    def test_unit_schema_or_smoke_runs_alone_do_not_establish_readiness(self) -> None:
        for execution_kind in ("unit_test", "schema_test", "smoke_test"):
            with self.subTest(execution_kind=execution_kind):
                observations = deepcopy(self.observations)
                for observation in observations:
                    observation["execution_kind"] = execution_kind
                    refresh_digest(observation, "observation_digest")
                qualification = self._qualification(observations=observations)
                self.assertEqual(qualification["outcome"], "not_eligible")
                self.assertTrue(
                    any(
                        "execution_not_operationally_qualifying" in reason
                        for reason in qualification["eligibility"]["reasons"]
                    )
                )

    def test_out_of_scope_platform_and_identical_before_after_are_rejected(self) -> None:
        observations = deepcopy(self.observations)
        observations[0]["platform_manifest_ref"] = manifest_ref(
            "environment", "other"
        )
        refresh_digest(observations[0], "observation_digest")
        with self.assertRaisesRegex(
            OperationalQualificationError,
            "outside the selected deployment envelope or platform",
        ):
            self._qualification(observations=observations)

        rollback = next(
            item
            for item in self.observations
            if item["scenario_id"] == "rollback_trigger"
        )
        identical = deepcopy(rollback)
        identical["after_state_digest"] = deepcopy(identical["before_state_digest"])
        refresh_digest(identical, "observation_digest")
        with self.assertRaisesRegex(
            OperationalQualificationError,
            "no state transition was observed",
        ):
            build_operational_qualification(
                qualification_id="qualification.service",
                qualification_version="1",
                operational_profile=self.profile,
                deployment_envelope=self.envelope,
                scope_manifest_refs=self.scope,
                assessed_at="2026-07-16T01:00:00Z",
                time_trust="trusted",
                scenario_observations=[
                    identical if item["scenario_id"] == "rollback_trigger" else item
                    for item in self.observations
                ],
            )

    def test_change_invalidates_prior_and_replayed_rehearsal_is_rejected(self) -> None:
        previous = self._qualification()
        changed_scope = deepcopy(self.scope)
        changed_scope["environment_manifest_ref"] = manifest_ref(
            "environment", "b"
        )
        pending_envelope = build_deployment_envelope(
            envelope_id="envelope.service",
            envelope_version="2",
            operational_profile=self.profile,
            selected_mode="service",
            platform_manifest_ref=changed_scope["environment_manifest_ref"],
            scenario_thresholds=self.thresholds,
        )
        changed_envelope = build_deployment_envelope(
            envelope_id="envelope.service",
            envelope_version="2",
            operational_profile=self.profile,
            selected_mode="service",
            platform_manifest_ref=changed_scope["environment_manifest_ref"],
            scenario_thresholds=self.thresholds,
            selection_decision_ref=human_decision(
                "select_deployment_envelope",
                "envelope.service",
                "2",
                pending_envelope["envelope_basis_digest"],
                "changed-envelope-selection",
            ),
        )
        fresh = self._observations(
            suffix="b",
            envelope=changed_envelope,
            scope=changed_scope,
        )
        replayed = deepcopy(fresh)
        for current, old in zip(replayed, self.observations, strict=True):
            current["execution_id"] = old["execution_id"]
            current["raw_evidence_refs"] = deepcopy(old["raw_evidence_refs"])
            refresh_digest(current, "observation_digest")
        with self.assertRaisesRegex(
            OperationalQualificationError,
            "cannot replay prior execution or raw evidence",
        ):
            self._qualification(
                observations=replayed,
                envelope=changed_envelope,
                scope=changed_scope,
                previous=previous,
            )

        requalified = self._qualification(
            observations=fresh,
            envelope=changed_envelope,
            scope=changed_scope,
            previous=previous,
        )
        self.assertEqual(requalified["outcome"], "eligible")
        self.assertTrue(requalified["change_assessment"]["prior_invalidated"])
        self.assertEqual(
            requalified["change_assessment"]["changed_dimensions"],
            ["environment", "envelope"],
        )

    def test_independent_reviewer_and_human_decision_substitution_are_rejected(self) -> None:
        preliminary = build_operational_qualification(
            qualification_id="qualification.service",
            qualification_version="1",
            operational_profile=self.profile,
            deployment_envelope=self.envelope,
            scope_manifest_refs=self.scope,
            assessed_at="2026-07-16T01:00:00Z",
            time_trust="trusted",
            scenario_observations=self.observations,
        )
        executor_review = self._review(
            preliminary["review_basis_digest"], reviewer="executor"
        )
        with self.assertRaisesRegex(
            OperationalQualificationError,
            "reviewer cannot be an executor",
        ):
            build_operational_qualification(
                qualification_id="qualification.service",
                qualification_version="1",
                operational_profile=self.profile,
                deployment_envelope=self.envelope,
                scope_manifest_refs=self.scope,
                assessed_at="2026-07-16T01:00:00Z",
                time_trust="trusted",
                scenario_observations=self.observations,
                independent_review_record=executor_review,
            )

        eligible = self._qualification()
        forged = human_decision(
            "authorize_operational_use",
            "qualification.other",
            "1",
            eligible["authorization_basis_digest"],
            "forged-authorization",
            decided_at="2026-07-16T00:45:00Z",
        )
        with self.assertRaisesRegex(
            OperationalQualificationError,
            "target or decision kind mismatch",
        ):
            build_operational_qualification(
                qualification_id="qualification.service",
                qualification_version="1",
                operational_profile=self.profile,
                deployment_envelope=self.envelope,
                scope_manifest_refs=self.scope,
                assessed_at="2026-07-16T01:00:00Z",
                time_trust="trusted",
                scenario_observations=self.observations,
                independent_review_record=eligible["independent_review_record"],
                human_authorization_record=forged,
            )


if __name__ == "__main__":
    unittest.main()
