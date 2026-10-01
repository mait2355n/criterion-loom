from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import tempfile
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator

from semantic_guard_vnext.environment_governance import (
    build_adoption_request,
    resolve_adopted_environment,
    resolve_candidate_environment_material,
    validate_adoption_record,
    validate_candidate_environment_resolution,
)
from semantic_guard_vnext.environment_resolution import (
    EnvironmentResolutionError,
    canonical_digest,
    discover_parent_path_candidates,
    observe_resolved_environment,
    resolve_environment_candidate,
    validate_resolved_environment_profile,
)
from semantic_guard_vnext.execution_environment import (
    build_environment_snapshot,
    build_managed_environment,
    compare_pre_post_observations,
    render_absolute_command,
    validate_environment_snapshot,
)


class EnvironmentGovernanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.platform = {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        }
        self.host_ref = self._host_ref("host.test.current")
        self.profile = self._verification_profile()
        self.candidate = resolve_environment_candidate(
            self.profile,
            explicit_candidates={"python.vnext": [Path(sys.executable).absolute()]},
            host_identity_ref=self.host_ref,
            observed_platform=self.platform,
            environment_profile_id="environment.test.current",
        )
        self.current = observe_resolved_environment(
            self.candidate,
            host_identity_ref=self.host_ref,
            observed_platform=self.platform,
        )
        self.adoption_request = build_adoption_request(
            self.candidate,
            adoption_id="adoption.environment.test.current",
            adoption_version="1",
            decision_owner_ref=self._bound_ref("owner.human.test"),
        )
        self.adoption = self._accepted_adoption_fixture()
        self.decision_verifier = self._decision_verifier()
        self.host_identity_verifier = self._host_identity_verifier()

    @staticmethod
    def _digest(label: str) -> dict[str, str]:
        return canonical_digest({"label": label})

    @classmethod
    def _bound_ref(cls, record_id: str) -> dict:
        return {
            "record_id": record_id,
            "locator": f"records/{record_id}.json",
            "content_digest": cls._digest(record_id),
        }

    @classmethod
    def _host_ref(cls, host_id: str) -> dict:
        return {
            "host_id": host_id,
            "identity_digest": cls._digest(host_id),
            "evidence_ref": cls._bound_ref(f"host-evidence.{host_id}"),
        }

    def _verification_profile(self) -> dict:
        version = platform.python_version()
        return {
            "schema_version": "semantic-guard-local-verification-profile/v3",
            "profile_id": "profile.environment-governance.test",
            "profile_version": "1",
            "repository_root": ".",
            "environment_contract": {
                "tool_requirements": [
                    {
                        "tool_id": "python.vnext",
                        "candidate_source": "explicit",
                        "version_probe": "python",
                        "version_constraint": {"exact": version},
                        "digest_constraint": {"policy": "adopted_exact"},
                        "supported_platforms": [
                            {
                                "system": platform.system(),
                                "machine": platform.machine(),
                            }
                        ],
                    }
                ],
                "inherited_environment_allowlist": ["HOME", "LANG"],
                "fixed_environment": {
                    "NO_COLOR": "1",
                    "PYTHONDONTWRITEBYTECODE": "1",
                },
                "path_policy": "managed_minimal_from_adopted_tools",
                "adoption_required": True,
                "child_process_trace_required": True,
            },
            "commands": [
                {
                    "command_id": "verify.test",
                    "tool_id": "python.vnext",
                    "cwd": ".",
                    "arguments": ["-c", "print('ok')"],
                    "timeout_seconds": 30,
                    "artifact_effect": "none",
                }
            ],
            "formal_authority": "none",
            "positive_assurance_allowed": False,
            "limitations": [
                "Child-process executable tracing is required but not implemented."
            ],
        }

    def _accepted_adoption_fixture(self) -> dict:
        """Test-only external decision material; production code cannot build it."""

        record = deepcopy(self.adoption_request)
        record["record_kind"] = "adoption_decision"
        record["human_decision"] = "accept"
        record["decision_evidence_ref"] = {
            **self._bound_ref("decision.human.test"),
            "trust_domain": "trusted.test.entrypoint",
        }
        record["trusted_entrypoint_ref"] = self._bound_ref("entrypoint.test")
        record["limitations"] = [
            "External decision material remains unusable until its evidence is verified by a trusted entrypoint.",
            "Environment adoption does not grant engineering-verdict or final-acceptance authority.",
        ]
        record["adoption_digest"] = canonical_digest(
            {key: value for key, value in record.items() if key != "adoption_digest"}
        )
        validate_adoption_record(record)
        return record

    def _decision_verifier(self):
        def verifier(record: dict) -> bool:
            return (
                record.get("decision_evidence_ref", {}).get("trust_domain")
                == "trusted.test.entrypoint"
                and record.get("trusted_entrypoint_ref", {}).get("record_id")
                == "entrypoint.test"
            )

        verifier.verifier_ref = self._bound_ref("verifier.decision.test")
        return verifier

    def _host_identity_verifier(self):
        def verifier(material: dict) -> bool:
            current = material.get("current_host_identity_ref", {})
            return bool(
                material.get("candidate_host_identity_ref")
                and current.get("host_id", "").startswith("host.test.")
                and current.get("evidence_ref")
            )

        verifier.verifier_ref = self._bound_ref("verifier.host-identity.test")
        return verifier

    def _ready_resolution(self) -> dict:
        return resolve_adopted_environment(
            self.candidate,
            adoption_record=self.adoption,
            current_host_identity_ref=self.host_ref,
            trusted_decision_evidence_verifier=self.decision_verifier,
            trusted_host_identity_verifier=self.host_identity_verifier,
        )

    def _execution_context(self) -> dict:
        return {
            "verification_profile": self.profile,
            "candidate_profile": self.candidate,
            "adoption_record": self.adoption,
            "current_host_identity_ref": self.host_ref,
            "trusted_decision_evidence_verifier": self.decision_verifier,
            "trusted_host_identity_verifier": self.host_identity_verifier,
        }

    def test_new_schemas_are_valid_draft_2020_12(self) -> None:
        schema_root = (
            Path(__file__).resolve().parents[1] / "src/semantic_guard_vnext/validation/env-path-contracts"
        )
        for name in (
            "resolved-local-environment-profile.schema.json",
            "local-environment-adoption.schema.json",
            "local-environment-snapshot-v1.schema.json",
            "local-verification-profile-v3.schema.json",
        ):
            with self.subTest(name=name):
                document = json.loads((schema_root / name).read_text(encoding="utf-8"))
                Draft202012Validator.check_schema(document)

    def test_candidate_is_non_authoritative_and_rejects_ambiguous_resolution(
        self,
    ) -> None:
        self.assertEqual(self.candidate["lifecycle_state"], "candidate")
        self.assertEqual(self.candidate["formal_authority"], "none")
        self.assertFalse(self.candidate["positive_assurance_allowed"])
        validate_resolved_environment_profile(self.candidate)
        with self.assertRaises(EnvironmentResolutionError) as raised:
            resolve_environment_candidate(
                self.profile,
                explicit_candidates={
                    "python.vnext": [
                        Path(sys.executable).absolute(),
                        Path(sys.executable).resolve(),
                    ]
                },
                host_identity_ref=self.host_ref,
                observed_platform=self.platform,
            )
        self.assertEqual(raised.exception.code, "tool_resolution_not_unique")

    def test_candidate_resolution_is_closed_digest_sealed_and_non_authoritative(
        self,
    ) -> None:
        ready = self._ready_resolution()
        validate_candidate_environment_resolution(ready)
        self.assertEqual(
            ready["schema_version"],
            "semantic-guard-adopted-environment-candidate-resolution/v1",
        )
        self.assertEqual(ready["observation_source"], "internal_reobservation")
        self.assertEqual(ready["child_process_observation"], "not_implemented")
        self.assertEqual(ready["formal_authority"], "none")
        self.assertFalse(ready["environment_use_allowed"])
        self.assertFalse(ready["positive_assurance_allowed"])
        self.assertIn("external_trust_control_not_integrated", ready["reason_codes"])

        extra = deepcopy(ready)
        extra["forged_extra"] = "accepted"
        extra["resolution_digest"] = canonical_digest(
            {key: value for key, value in extra.items() if key != "resolution_digest"}
        )
        with self.assertRaises(EnvironmentResolutionError) as raised:
            validate_candidate_environment_resolution(extra)
        self.assertEqual(
            raised.exception.code, "candidate_environment_resolution_schema_invalid"
        )

    def test_effective_path_is_derived_from_verified_resolved_path(self) -> None:
        tool = self.candidate["resolved_tools"][0]
        expected_directory = str(Path(tool["resolved_path"]).parent)
        self.assertEqual(
            self.candidate["effective_path"]["entries"][0]["directory"],
            expected_directory,
        )
        self.assertEqual(
            self.candidate["effective_path"]["rendered_value"], expected_directory
        )

    def test_parent_path_is_discovery_only_and_fake_prefix_is_discarded(self) -> None:
        fake_directory = self.root / "fake-bin"
        fake_directory.mkdir()
        fake = fake_directory / "python"
        fake.write_text("#!/bin/sh\nexit 97\n", encoding="utf-8")
        fake.chmod(0o755)
        discovery = discover_parent_path_candidates(
            "python",
            parent_path=f"{fake_directory}{os.pathsep}{Path(sys.executable).parent}",
        )
        self.assertTrue(discovery["discovery_only"])
        self.assertEqual(discovery["formal_authority"], "none")
        self.assertIn(str(fake), discovery["candidate_paths"])

        resolution = self._ready_resolution()
        managed = build_managed_environment(
            resolution,
            **self._execution_context(),
            parent_environment={
                "PATH": f"{fake_directory}{os.pathsep}/unmanaged",
                "HOME": str(self.root),
                "SECRET": "not-inherited",
            },
        )
        self.assertNotIn(str(fake_directory), managed["PATH"])
        self.assertNotIn("SECRET", managed)
        rendered = render_absolute_command(
            self.profile["commands"][0],
            resolution=resolution,
            **self._execution_context(),
        )
        self.assertTrue(Path(rendered[0]).is_absolute())
        self.assertEqual(
            rendered[0], self.candidate["resolved_tools"][0]["resolved_path"]
        )

    def test_candidate_without_adoption_and_unverified_decision_are_rejected(
        self,
    ) -> None:
        candidate_only = resolve_adopted_environment(
            self.candidate,
            adoption_record=None,
            current_host_identity_ref=self.host_ref,
            trusted_decision_evidence_verifier=self.decision_verifier,
            trusted_host_identity_verifier=self.host_identity_verifier,
        )
        self.assertEqual(candidate_only["resolution_status"], "unresolved")
        self.assertFalse(candidate_only["environment_use_allowed"])

        pending = resolve_adopted_environment(
            self.candidate,
            adoption_record=self.adoption_request,
            current_host_identity_ref=self.host_ref,
            trusted_decision_evidence_verifier=self.decision_verifier,
            trusted_host_identity_verifier=self.host_identity_verifier,
        )
        self.assertEqual(pending["resolution_status"], "unresolved")
        self.assertIn("environment_not_accepted", pending["reason_codes"])

        unverified = resolve_adopted_environment(
            self.candidate,
            adoption_record=self.adoption,
            current_host_identity_ref=self.host_ref,
            trusted_decision_evidence_verifier=None,
            trusted_host_identity_verifier=self.host_identity_verifier,
        )
        self.assertEqual(unverified["resolution_status"], "unresolved")
        self.assertIn("decision_evidence_verifier_missing", unverified["reason_codes"])

    def test_decision_evidence_ref_is_mandatory_and_basis_is_exact(self) -> None:
        missing_evidence = deepcopy(self.adoption)
        missing_evidence.pop("decision_evidence_ref")
        missing_evidence["adoption_digest"] = canonical_digest(
            {
                key: value
                for key, value in missing_evidence.items()
                if key != "adoption_digest"
            }
        )
        with self.assertRaises(EnvironmentResolutionError) as raised:
            validate_adoption_record(missing_evidence)
        self.assertEqual(raised.exception.code, "environment_adoption_schema_invalid")

        wrong_basis = deepcopy(self.adoption)
        wrong_basis["environment_profile_ref"]["basis_digest"] = self._digest(
            "different-basis"
        )
        wrong_basis["adoption_digest"] = canonical_digest(
            {
                key: value
                for key, value in wrong_basis.items()
                if key != "adoption_digest"
            }
        )
        result = resolve_adopted_environment(
            self.candidate,
            adoption_record=wrong_basis,
            current_host_identity_ref=self.host_ref,
            trusted_decision_evidence_verifier=self.decision_verifier,
            trusted_host_identity_verifier=self.host_identity_verifier,
        )
        self.assertEqual(result["resolution_status"], "unresolved")
        self.assertIn("environment_adoption_basis_mismatch", result["reason_codes"])

    def test_platform_and_verified_host_drift_require_requalification(self) -> None:
        host_result = resolve_adopted_environment(
            self.candidate,
            adoption_record=self.adoption,
            current_host_identity_ref=self._host_ref("host.test.other"),
            trusted_decision_evidence_verifier=self.decision_verifier,
            trusted_host_identity_verifier=self.host_identity_verifier,
        )
        self.assertEqual(host_result["resolution_status"], "requalification_required")
        self.assertIn("host_identity_drift", host_result["reason_codes"])

        other_platform = {
            **self.platform,
            "release": f"{self.platform['release']}.drift",
        }
        with patch(
            "semantic_guard_vnext.environment_resolution.platform_observation",
            return_value=other_platform,
        ):
            platform_result = self._ready_resolution()
        self.assertEqual(
            platform_result["resolution_status"], "requalification_required"
        )
        self.assertIn("platform_drift", platform_result["reason_codes"])

    def test_stale_injected_observation_cannot_hide_tool_drift(self) -> None:
        probe = self.root / "python-probe"
        version = platform.python_version()
        probe.write_text(f"#!/bin/sh\nprintf '%s\\n' '{version}'\n", encoding="utf-8")
        probe.chmod(0o755)
        candidate = resolve_environment_candidate(
            self.profile,
            explicit_candidates={"python.vnext": [probe]},
            host_identity_ref=self.host_ref,
            observed_platform=self.platform,
            environment_profile_id="environment.test.mutable-tool",
        )
        stale_observation = observe_resolved_environment(
            candidate,
            host_identity_ref=self.host_ref,
            observed_platform=self.platform,
        )
        request = build_adoption_request(
            candidate,
            adoption_id="adoption.environment.test.mutable-tool",
            adoption_version="1",
            decision_owner_ref=self._bound_ref("owner.human.test"),
        )
        adoption = deepcopy(request)
        adoption["record_kind"] = "adoption_decision"
        adoption["human_decision"] = "accept"
        adoption["decision_evidence_ref"] = {
            **self._bound_ref("decision.human.test.mutable-tool"),
            "trust_domain": "trusted.test.entrypoint",
        }
        adoption["trusted_entrypoint_ref"] = self._bound_ref("entrypoint.test")
        adoption["limitations"] = list(self.adoption["limitations"])
        adoption["adoption_digest"] = canonical_digest(
            {key: value for key, value in adoption.items() if key != "adoption_digest"}
        )
        validate_adoption_record(adoption)

        # Same observable version, different file content.  Replaying the old
        # observation would hide this unless resolution observes the sealed path.
        probe.write_text(
            f"#!/bin/sh\n# changed after adoption\nprintf '%s\\n' '{version}'\n",
            encoding="utf-8",
        )
        probe.chmod(0o755)
        result = resolve_adopted_environment(
            candidate,
            adoption_record=adoption,
            current_host_identity_ref=self.host_ref,
            trusted_decision_evidence_verifier=self.decision_verifier,
            trusted_host_identity_verifier=self.host_identity_verifier,
            current_observation=stale_observation,
        )
        self.assertEqual(result["resolution_status"], "requalification_required")
        self.assertIn("resolved_tool_drift", result["reason_codes"])
        self.assertFalse(result["environment_use_allowed"])

    def test_self_reported_host_and_unbound_verifiers_fail_closed(self) -> None:
        without_host_verifier = resolve_adopted_environment(
            self.candidate,
            adoption_record=self.adoption,
            current_host_identity_ref=self.host_ref,
            trusted_decision_evidence_verifier=self.decision_verifier,
            trusted_host_identity_verifier=None,
        )
        self.assertEqual(without_host_verifier["resolution_status"], "unresolved")
        self.assertIn(
            "host_identity_verifier_missing", without_host_verifier["reason_codes"]
        )

        def unbound_verifier(_material: dict) -> bool:
            return True

        for name, decision_verifier, host_verifier, reason in (
            (
                "decision",
                unbound_verifier,
                self.host_identity_verifier,
                "decision_evidence_verifier_ref_invalid",
            ),
            (
                "host",
                self.decision_verifier,
                unbound_verifier,
                "host_identity_verifier_ref_invalid",
            ),
        ):
            with self.subTest(name=name):
                result = resolve_adopted_environment(
                    self.candidate,
                    adoption_record=self.adoption,
                    current_host_identity_ref=self.host_ref,
                    trusted_decision_evidence_verifier=decision_verifier,
                    trusted_host_identity_verifier=host_verifier,
                )
                self.assertEqual(result["resolution_status"], "unresolved")
                self.assertIn(reason, result["reason_codes"])

        invalid_ref_verifier = self._host_identity_verifier()
        invalid_ref_verifier.verifier_ref = {"record_id": "missing-digest"}
        invalid_verifier = resolve_adopted_environment(
            self.candidate,
            adoption_record=self.adoption,
            current_host_identity_ref=self.host_ref,
            trusted_decision_evidence_verifier=self.decision_verifier,
            trusted_host_identity_verifier=invalid_ref_verifier,
        )
        self.assertEqual(invalid_verifier["resolution_status"], "unresolved")
        self.assertIn(
            "host_identity_verifier_ref_invalid", invalid_verifier["reason_codes"]
        )

        invalid_host_ref = {"host_id": "host.test.current"}
        invalid_host = resolve_adopted_environment(
            self.candidate,
            adoption_record=self.adoption,
            current_host_identity_ref=invalid_host_ref,
            trusted_decision_evidence_verifier=self.decision_verifier,
            trusted_host_identity_verifier=self.host_identity_verifier,
        )
        self.assertEqual(invalid_host["resolution_status"], "unresolved")
        self.assertIn("current_host_identity_ref_invalid", invalid_host["reason_codes"])

    def test_rejecting_and_failing_trust_callbacks_are_unresolved(self) -> None:
        def rejecting(_material: dict) -> bool:
            return False

        def failing(_material: dict) -> bool:
            raise RuntimeError("trust service unavailable")

        rejecting.verifier_ref = self._bound_ref("verifier.rejecting.test")
        failing.verifier_ref = self._bound_ref("verifier.failing.test")
        cases = (
            (rejecting, self.host_identity_verifier, "decision_evidence_unverified"),
            (failing, self.host_identity_verifier, "decision_evidence_verifier_failed"),
            (self.decision_verifier, rejecting, "host_identity_unverified"),
            (self.decision_verifier, failing, "host_identity_verifier_failed"),
        )
        for decision_verifier, host_verifier, reason in cases:
            with self.subTest(reason=reason):
                result = resolve_adopted_environment(
                    self.candidate,
                    adoption_record=self.adoption,
                    current_host_identity_ref=self.host_ref,
                    trusted_decision_evidence_verifier=decision_verifier,
                    trusted_host_identity_verifier=host_verifier,
                )
                self.assertEqual(result["resolution_status"], "unresolved")
                self.assertIn(reason, result["reason_codes"])

    def test_version_constraint_mismatch_fails_closed(self) -> None:
        profile = deepcopy(self.profile)
        profile["environment_contract"]["tool_requirements"][0][
            "version_constraint"
        ] = {"exact": "0.0.0"}
        with self.assertRaises(EnvironmentResolutionError) as raised:
            resolve_environment_candidate(
                profile,
                explicit_candidates={"python.vnext": [Path(sys.executable).absolute()]},
                host_identity_ref=self.host_ref,
                observed_platform=self.platform,
            )
        self.assertEqual(raised.exception.code, "tool_version_constraint_mismatch")

    def test_version_comparison_normalizes_trailing_zero_components(self) -> None:
        profile = deepcopy(self.profile)
        profile["environment_contract"]["tool_requirements"][0][
            "version_constraint"
        ] = {"exact": f"{platform.python_version()}.0"}
        candidate = resolve_environment_candidate(
            profile,
            explicit_candidates={"python.vnext": [Path(sys.executable).absolute()]},
            host_identity_ref=self.host_ref,
            observed_platform=self.platform,
        )
        self.assertEqual(
            candidate["resolved_tools"][0]["version"], platform.python_version()
        )

    def test_pre_post_change_is_requalification_and_snapshot_has_no_assurance(
        self,
    ) -> None:
        ready = self._ready_resolution()
        self.assertEqual(ready["resolution_status"], "candidate_execution_material")
        self.assertFalse(ready["environment_use_allowed"])
        self.assertEqual(
            ready["trust_claim_states"],
            {
                "decision_evidence": "verifier_claim_accepted",
                "host_identity": "verifier_claim_accepted",
            },
        )
        self.assertFalse(ready["positive_assurance_allowed"])
        managed = build_managed_environment(
            ready,
            **self._execution_context(),
            parent_environment={"PATH": "/fake", "HOME": str(self.root)},
        )
        after = deepcopy(self.current)
        after["resolved_tools"][0]["file_digest"] = self._digest("post-change")
        comparison = compare_pre_post_observations(self.current, after)
        self.assertEqual(comparison["observation_status"], "requalification_required")
        self.assertIn("tool_changed_during_execution", comparison["reason_codes"])

        snapshot = build_environment_snapshot(
            self.candidate,
            verification_profile=self.profile,
            adoption_record=self.adoption,
            resolution=ready,
            trusted_decision_evidence_verifier=self.decision_verifier,
            trusted_host_identity_verifier=self.host_identity_verifier,
            managed_environment=managed,
            pre_observation=self.current,
            post_observation=after,
        )
        self.assertEqual(snapshot["observation_status"], "requalification_required")
        self.assertEqual(snapshot["child_process_observation"], "not_implemented")
        self.assertFalse(snapshot["positive_assurance_allowed"])
        self.assertEqual(snapshot["formal_authority"], "none")
        self.assertEqual(validate_environment_snapshot(snapshot), snapshot)

        forged = deepcopy(snapshot)
        forged["effective_path_observation"]["rendered_value"] = "/forged"
        forged["snapshot_digest"] = canonical_digest(
            {key: value for key, value in forged.items() if key != "snapshot_digest"}
        )
        with self.assertRaises(EnvironmentResolutionError) as raised:
            validate_environment_snapshot(forged)
        self.assertEqual(
            raised.exception.code, "environment_snapshot_effective_path_mismatch"
        )

    def test_preferred_environment_api_names_candidate_material_truthfully(
        self,
    ) -> None:
        preferred = resolve_candidate_environment_material(
            self.candidate,
            adoption_record=self.adoption,
            current_host_identity_ref=self.host_ref,
            trusted_decision_evidence_verifier=self.decision_verifier,
            trusted_host_identity_verifier=self.host_identity_verifier,
        )
        self.assertEqual(preferred, self._ready_resolution())
        self.assertEqual(preferred["resolution_status"], "candidate_execution_material")
        self.assertFalse(preferred["environment_use_allowed"])

    def test_stable_foreign_observations_cannot_form_a_stable_snapshot(self) -> None:
        ready = self._ready_resolution()
        managed = build_managed_environment(
            ready,
            **self._execution_context(),
            parent_environment={"HOME": str(self.root)},
        )
        foreign = deepcopy(ready["current_observation"])
        foreign["host_identity_ref"] = self._host_ref("host.test.foreign")
        foreign["resolved_tools"][0]["file_digest"] = self._digest(
            "foreign-tool-with-stable-self-observation"
        )
        snapshot = build_environment_snapshot(
            self.candidate,
            verification_profile=self.profile,
            adoption_record=self.adoption,
            resolution=ready,
            trusted_decision_evidence_verifier=self.decision_verifier,
            trusted_host_identity_verifier=self.host_identity_verifier,
            managed_environment=managed,
            pre_observation=foreign,
            post_observation=deepcopy(foreign),
        )
        self.assertEqual(snapshot["observation_status"], "requalification_required")
        self.assertIn(
            "pre_host_not_bound_to_candidate_resolution", snapshot["reason_codes"]
        )
        self.assertIn(
            "post_tools_not_bound_to_candidate_resolution", snapshot["reason_codes"]
        )
        self.assertEqual(
            snapshot["candidate_environment_resolution_ref"]["resolution_digest"],
            ready["resolution_digest"],
        )
        self.assertEqual(
            snapshot["verification_profile_basis_digest"],
            self.candidate["verification_profile_basis_digest"],
        )

    def test_snapshot_rejects_cross_subject_candidate_resolution(self) -> None:
        ready = deepcopy(self._ready_resolution())
        foreign = self._host_ref("host.test.foreign")
        ready["current_observation"]["host_identity_ref"] = foreign
        ready["resolution_digest"] = canonical_digest(
            {key: value for key, value in ready.items() if key != "resolution_digest"}
        )
        validate_candidate_environment_resolution(ready)
        with self.assertRaises(EnvironmentResolutionError) as raised:
            build_environment_snapshot(
                self.candidate,
                verification_profile=self.profile,
                adoption_record=self.adoption,
                resolution=ready,
                trusted_decision_evidence_verifier=self.decision_verifier,
                trusted_host_identity_verifier=self.host_identity_verifier,
                managed_environment={
                    "PATH": self.candidate["effective_path"]["rendered_value"]
                },
                pre_observation=ready["current_observation"],
                post_observation=ready["current_observation"],
            )
        self.assertEqual(
            raised.exception.code, "snapshot_resolution_host_candidate_mismatch"
        )

    def test_managed_environment_uses_only_digest_bound_contract(self) -> None:
        ready = self._ready_resolution()
        managed = build_managed_environment(
            ready,
            **self._execution_context(),
            parent_environment={
                "PATH": "/unmanaged",
                "HOME": str(self.root),
                "LANG": "ja_JP.UTF-8",
                "NO_COLOR": "caller-value-must-not-win",
                "PYTHONPATH": "/attacker/pythonpath",
                "PYTHONHOME": "/attacker/pythonhome",
                "DYLD_INSERT_LIBRARIES": "/attacker/inject.dylib",
            },
        )
        self.assertEqual(managed["HOME"], str(self.root))
        self.assertEqual(managed["LANG"], "ja_JP.UTF-8")
        self.assertEqual(managed["NO_COLOR"], "1")
        self.assertEqual(managed["PYTHONDONTWRITEBYTECODE"], "1")
        self.assertEqual(managed["PATH"], ready["effective_path"]["rendered_value"])
        for prohibited in (
            "PYTHONPATH",
            "PYTHONHOME",
            "DYLD_INSERT_LIBRARIES",
        ):
            self.assertNotIn(prohibited, managed)

    def test_execution_rejects_unadopted_environment_contract_widening(self) -> None:
        widened = deepcopy(self.profile)
        widened["environment_contract"]["inherited_environment_allowlist"].append(
            "PYTHONPATH"
        )
        with self.assertRaises(EnvironmentResolutionError) as raised:
            build_managed_environment(
                self._ready_resolution(),
                **{
                    **self._execution_context(),
                    "verification_profile": widened,
                },
                parent_environment={"PYTHONPATH": "/attacker/pythonpath"},
            )
        self.assertEqual(raised.exception.code, "verification_profile_basis_mismatch")

        replaced_fixed = deepcopy(self.profile)
        replaced_fixed["environment_contract"]["fixed_environment"]["NO_COLOR"] = (
            "attacker-value"
        )
        with self.assertRaises(EnvironmentResolutionError) as raised:
            build_managed_environment(
                self._ready_resolution(),
                **{
                    **self._execution_context(),
                    "verification_profile": replaced_fixed,
                },
                parent_environment={},
            )
        self.assertEqual(raised.exception.code, "verification_profile_basis_mismatch")

    def test_execution_helpers_reject_forged_ready_and_modified_path(self) -> None:
        fake_ready = {
            "resolution_status": "candidate_execution_material",
            "environment_use_allowed": False,
            "effective_path": {"rendered_value": "/attacker/bin"},
            "resolved_tools": [
                {"tool_id": "python.vnext", "resolved_path": "/attacker/python"}
            ],
        }
        with self.assertRaises(EnvironmentResolutionError) as raised:
            build_managed_environment(
                fake_ready,
                **self._execution_context(),
                parent_environment={},
            )
        self.assertEqual(
            raised.exception.code, "candidate_environment_resolution_schema_invalid"
        )

        changed_path = deepcopy(self._ready_resolution())
        changed_path["effective_path"]["rendered_value"] = "/attacker/bin"
        changed_path["effective_path"]["content_digest"] = canonical_digest(
            "/attacker/bin"
        )
        changed_path["resolution_digest"] = canonical_digest(
            {
                key: value
                for key, value in changed_path.items()
                if key != "resolution_digest"
            }
        )
        with self.assertRaises(EnvironmentResolutionError) as raised:
            build_managed_environment(
                changed_path,
                **self._execution_context(),
                parent_environment={},
            )
        self.assertEqual(
            raised.exception.code,
            "candidate_environment_resolution_path_projection_mismatch",
        )

    def test_execution_helpers_replay_context_and_reject_modified_tool(self) -> None:
        forged = deepcopy(self._ready_resolution())
        forged_tool = "/attacker/bin/python"
        for tool in (
            forged["resolved_tools"][0],
            forged["current_observation"]["resolved_tools"][0],
        ):
            tool["resolved_path"] = forged_tool
        forged_path = {
            "policy": "managed_minimal_from_adopted_tools",
            "entries": [
                {
                    "directory": "/attacker/bin",
                    "source_tool_ids": ["python.vnext"],
                }
            ],
            "rendered_value": "/attacker/bin",
            "content_digest": {
                "algorithm": "sha256",
                "value": hashlib.sha256(b"/attacker/bin").hexdigest(),
            },
        }
        forged["effective_path"] = deepcopy(forged_path)
        forged["current_observation"]["effective_path"] = deepcopy(forged_path)
        forged["resolution_digest"] = canonical_digest(
            {key: value for key, value in forged.items() if key != "resolution_digest"}
        )
        validate_candidate_environment_resolution(forged)
        with self.assertRaises(EnvironmentResolutionError) as raised:
            render_absolute_command(
                self.profile["commands"][0],
                resolution=forged,
                **self._execution_context(),
            )
        self.assertEqual(
            raised.exception.code, "environment_resolution_replay_mismatch"
        )

        missing_trust_context = self._execution_context()
        missing_trust_context["trusted_host_identity_verifier"] = None
        with self.assertRaises(EnvironmentResolutionError) as raised:
            render_absolute_command(
                self.profile["commands"][0],
                resolution=self._ready_resolution(),
                **missing_trust_context,
            )
        self.assertEqual(
            raised.exception.code, "environment_resolution_replay_not_candidate"
        )


if __name__ == "__main__":
    unittest.main()
