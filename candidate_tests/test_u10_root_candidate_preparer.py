from __future__ import annotations

import copy
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import json
import os
from pathlib import Path
import pwd
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
import uuid
from unittest import mock

from jsonschema import Draft202012Validator


SCRIPT = Path(__file__).parent / "fixtures" / "scripts" / "prepare_u10_root_candidate.py"
SCHEMA_DIRECTORY = Path(__file__).parents[1] / "src" / "semantic_guard_vnext" / "validation" / "env-path-contracts"
SPEC = importlib.util.spec_from_file_location("u10_root_candidate_preparer", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
PREPARER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PREPARER)


class U10RootCandidatePreparerTests(unittest.TestCase):
    def setUp(self) -> None:
        # The policy selects 501:20; the host running these contract tests need
        # not contain that account. Keep the OS lookup boundary deterministic.
        self.worker_account = pwd.struct_passwd(
            ("u10-fixture-worker", "x", 501, 20, "", "/fixture/u10-worker", "/bin/sh")
        )
        self.enterContext(
            mock.patch.object(
                PREPARER, "pwd", SimpleNamespace(getpwnam=self._getpwnam)
            )
        )
        self.enterContext(
            mock.patch.object(PREPARER.os, "getgrouplist", self._getgrouplist)
        )

    def _getpwnam(self, name: str) -> pwd.struct_passwd:
        if name != self.worker_account.pw_name:
            raise KeyError(name)
        return self.worker_account

    def _getgrouplist(self, name: str, gid: int) -> list[int]:
        account = self._getpwnam(name)
        if gid != account.pw_gid:
            raise KeyError((name, gid))
        return [account.pw_gid, 80]

    def _mapping(
        self,
        source: Path,
        *,
        destination: str = "vnext/runtime",
        role: str = "test_runtime",
        origin_kind: str = "test_fixture",
        excluded_prefixes: list[str] | None = None,
    ) -> dict:
        return {
            "mapping_kind": "tree" if source.is_dir() else "file",
            "source_path": str(source),
            "destination": destination,
            "role": role,
            "origin_kind": origin_kind,
            "excluded_prefixes": excluded_prefixes or [],
        }

    def _fixture_inputs(self, root: Path) -> tuple[Path, list[dict], dict]:
        repository = root / "repository"
        source = repository / "source"
        source.mkdir(parents=True, exist_ok=True)
        regular = source / "module.py"
        regular.write_text("VALUE = 1\n", encoding="utf-8")
        regular.chmod(0o644)
        executable = source / "runner"
        executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        executable.chmod(0o755)

        vnext = repository / "vnext"
        snapshot_source = vnext / "src" / "semantic_guard_vnext"
        snapshot_source.mkdir(parents=True, exist_ok=True)
        (snapshot_source / "__init__.py").write_text("\n", encoding="utf-8")
        scripts = vnext / "scripts"
        scripts.mkdir(exist_ok=True)
        bootstrap = scripts / "u10_root_broker_bootstrap.py"
        bootstrap.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
        bootstrap.chmod(0o755)
        for name, content in (
            (
                "u10_root_broker_entrypoint.sh",
                "#!/bin/sh\nexit 0\n",
            ),
            (
                "u10_root_broker_outer_launcher.py",
                "#!/usr/bin/env python3\n",
            ),
            (
                "u10_root_candidate_installer_entrypoint.sh",
                "#!/bin/sh\nexit 0\n",
            ),
        ):
            path = scripts / name
            path.write_text(content, encoding="utf-8")
            path.chmod(0o755)
        (vnext / "pyproject.toml").write_text(
            '[project]\nname = "semantic-guard-vnext"\n', encoding="utf-8"
        )
        (vnext / "uv.lock").write_text("version = 1\n", encoding="utf-8")

        tools = repository / "qualified-tools"
        tools.mkdir(exist_ok=True)
        python = tools / "python"
        python.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        python.chmod(0o755)
        uv = tools / "uv"
        uv.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        uv.chmod(0o755)

        dependency_site = repository / "qualified-site-packages"
        dependency_site.mkdir(exist_ok=True)
        (dependency_site / "third_party.py").write_text(
            "VALUE = 'dependency'\n", encoding="utf-8"
        )
        editable_pointer = dependency_site / PREPARER.EDITABLE_POINTER_NAME
        editable_pointer.write_text(f"{(vnext / 'src').resolve()}\n", encoding="utf-8")
        package_data = dependency_site / PREPARER.PROJECT_IMPORT_NAME / "schemas"
        package_data.mkdir(parents=True, exist_ok=True)
        (package_data / "schema.json").write_text("{}\n", encoding="utf-8")
        dist_info = dependency_site / "semantic_guard_vnext-0.1.0.dist-info"
        dist_info.mkdir(exist_ok=True)
        (dist_info / "direct_url.json").write_text(
            json.dumps(
                {
                    "url": vnext.resolve().as_uri(),
                    "dir_info": {"editable": True},
                }
            ),
            encoding="utf-8",
        )
        exclusions = PREPARER.discover_project_dependency_exclusions_v1(
            dependency_site,
            snapshot_source_root=vnext / "src",
        )
        policy = PREPARER.dependency_environment_policy_v1(
            python_major_minor="3.13",
            excluded_project_entries=exclusions,
        )
        mappings = [
            self._mapping(source),
            self._mapping(
                vnext / "src",
                destination="vnext/src",
                role="subject_and_broker_source",
            ),
            self._mapping(
                scripts,
                destination="vnext/scripts",
                role="worker_and_candidate_tooling",
            ),
            self._mapping(
                vnext / "pyproject.toml",
                destination="vnext/pyproject.toml",
                role="dependency_contract",
            ),
            self._mapping(
                vnext / "uv.lock",
                destination="vnext/uv.lock",
                role="dependency_lock",
            ),
            self._mapping(
                python,
                destination="vnext/.venv/bin/python",
                role="python_interpreter",
            ),
            self._mapping(
                uv,
                destination="vnext/tools/uv",
                role="dependency_lock_verifier",
            ),
            self._mapping(
                dependency_site,
                destination=policy["dependency_import_root"],
                role="python_dependency_runtime",
                excluded_prefixes=exclusions,
            ),
        ]
        return repository, mappings, policy

    def _preactivation_inputs(
        self, root: Path, mappings: list[dict]
    ) -> dict:
        governance = root / "preactivation"
        governance.mkdir(parents=True, exist_ok=True)
        evidence_path = governance / "human-decision-evidence.json"
        evidence_path.write_text('{"source":"test-only"}\n', encoding="utf-8")
        entrypoint_path = governance / "trusted-entrypoint.txt"
        entrypoint_path.write_text("test-only trusted entrypoint\n", encoding="utf-8")
        decision_path = governance / "decision.json"
        decision = {
            "schema_version": "semantic-guard-u10-preactivation-decision/v1",
            "decision_id": "decision.u10.preactivation.test",
            "decision_version": "1.0.0-test",
            "record_kind": "u10_preactivation_scope_decision",
            "notation_profile": "entity-reference-notation/v0",
            "decision_entity_ref": "U-10 test decision・1374d221-6bf4-5682-b3d8-dd7897d24b78",
            "subject_entity_ref": f"U-10 governed verification environment・{PREPARER.U10_SUBJECT_ENTITY_ID}",
            "human_decision": "accept",
            "decision_owner": "human",
            "threat_boundary_selection": "local_bounded_repository_suite_only",
            "worker_identity_selection": "current_user_501_20_empty_supplementary_groups",
            "decision_evidence_ref": {
                "record_id": "evidence.u10.preactivation.test",
                "locator": str(evidence_path.resolve()),
                "content_digest": PREPARER.digest_bytes(evidence_path.read_bytes()),
                "trust_domain": "test-only",
            },
            "trusted_entrypoint_ref": {
                "record_id": "entrypoint.u10.preactivation.test",
                "locator": str(entrypoint_path.resolve()),
                "content_digest": PREPARER.digest_bytes(entrypoint_path.read_bytes()),
            },
            "recorded_at": "2026-01-01T00:00:00Z",
            "requalification_triggers": [
                "threat_boundary_change",
                "worker_identity_policy_change",
                "principal_resolution_change",
                "host_or_os_change",
                "sandbox_or_external_executor_change",
                "qualified_test_denominator_change",
            ],
            "u4_principal_authenticity": "unresolved",
            "authority_scope": "u10_preactivation_scope_selection_only",
            "formal_authority": "human_scope_selection_only",
            "positive_assurance_allowed": False,
        }
        decision["decision_digest"] = PREPARER.sealed_digest(
            decision, "decision_digest"
        )
        decision_raw = PREPARER.canonical_json_bytes(decision) + b"\n"
        decision_path.write_bytes(decision_raw)
        observation_path = governance / "worker-account-observation.json"
        observation = PREPARER.build_worker_account_observation_v1(
            decision=decision,
            decision_raw=decision_raw,
            decision_locator=decision_path,
            account_name=self.worker_account.pw_name,
            observed_at="2026-01-01T00:00:01Z",
            observation_entity_id=uuid.UUID("fa5ee53e-e613-4ea6-8348-9f47c0bbf180"),
        )
        observation_raw = PREPARER.canonical_json_bytes(observation) + b"\n"
        observation_path.write_bytes(observation_raw)
        resolution_path = governance / "worker-principal-resolution.json"
        resolution = PREPARER.build_worker_principal_resolution_v1(
            decision=decision,
            decision_raw=decision_raw,
            decision_locator=decision_path,
            observation=observation,
            observation_raw=observation_raw,
            observation_locator=observation_path,
            resolved_at="2026-01-01T00:00:02Z",
            resolution_entity_id=uuid.UUID("73b259d4-13db-4579-989a-994e37243bc7"),
        )
        resolution_raw = PREPARER.canonical_json_bytes(resolution) + b"\n"
        resolution_path.write_bytes(resolution_raw)
        mappings.extend(
            [
                self._mapping(
                    decision_path.resolve(),
                    destination="vnext/governance/u10-preactivation-decision.json",
                    role="u10_preactivation_decision_record",
                    origin_kind="trusted_human_decision_record",
                ),
                self._mapping(
                    observation_path.resolve(),
                    destination="vnext/governance/u10-worker-account-observation.json",
                    role="u10_worker_account_observation",
                    origin_kind="observed_worker_account_and_host",
                ),
                self._mapping(
                    resolution_path.resolve(),
                    destination="vnext/governance/u10-worker-principal-resolution.json",
                    role="u10_worker_principal_resolution",
                    origin_kind="observed_worker_principal_resolution",
                ),
            ]
        )
        return {
            "preactivation_decision": decision,
            "preactivation_decision_raw": decision_raw,
            "preactivation_decision_locator": decision_path,
            "worker_account_observation": observation,
            "worker_account_observation_raw": observation_raw,
            "worker_account_observation_locator": observation_path,
            "worker_principal_resolution": resolution,
            "worker_principal_resolution_raw": resolution_raw,
            "worker_principal_resolution_locator": resolution_path,
        }

    def _prepare(self, temporary: str, *, name: str = "bundle") -> tuple[Path, dict]:
        root = Path(temporary)
        repository, mappings, policy = self._fixture_inputs(root)
        boundary = self._preactivation_inputs(root, mappings)
        output = root / name
        manifest = PREPARER._prepare_bundle_from_mappings(
            mappings=mappings,
            dependency_environment_policy=policy,
            repository_root=repository,
            output=output,
            **boundary,
            installer_path=SCRIPT,
        )
        return output, manifest

    def _authorization(
        self,
        manifest: dict,
        bundle: Path,
        *,
        decision: str = "accept",
    ) -> dict:
        manifest_raw = (bundle / PREPARER.MANIFEST_NAME).read_bytes()
        authorization = {
            "schema_version": PREPARER.AUTHORIZATION_SCHEMA,
            "authorization_id": f"authorization.install.{manifest['bundle_id']}",
            "authorization_version": "1.0.0",
            "record_kind": "candidate_install_authorization",
            "bundle_id": manifest["bundle_id"],
            "bundle_digest": manifest["bundle_digest"],
            "source_bundle_path": str(bundle.resolve(strict=True)),
            "source_manifest_artifact_digest": PREPARER.digest_bytes(
                manifest_raw
            ),
            "target_candidate_path": manifest["target"]["candidate_path"],
            "authorized_operation": "install_candidate_only",
            "human_decision": decision,
            "decision_owner": "human",
            "recorded_at": "2026-07-19T00:00:00Z",
            "u4_principal_authenticity": "unresolved",
            "authority_scope": "u10_candidate_install_only",
            "candidate_install_ledger": {
                "root": manifest["target"]["candidate_install_ledger_root"],
                "policy": PREPARER._candidate_install_ledger_policy_v1(),
                "policy_digest": PREPARER.digest_bytes(
                    PREPARER.canonical_json_bytes(
                        PREPARER._candidate_install_ledger_policy_v1()
                    )
                ),
            },
            "formal_authority": "human_candidate_install_decision_only",
            "positive_assurance_allowed": False,
        }
        authorization["authorization_digest"] = PREPARER.sealed_digest(
            authorization, "authorization_digest"
        )
        return authorization

    def _make_mutable(self, root: Path) -> None:
        for raw_directory, directory_names, file_names in os.walk(
            root, topdown=False, followlinks=False
        ):
            base = Path(raw_directory)
            os.chmod(base, 0o700)
            for name in file_names:
                os.chmod(base / name, 0o600)
            for name in directory_names:
                os.chmod(base / name, 0o700)

    def _install_context(
        self, temporary: str
    ) -> tuple[Path, dict, Path, Path, dict]:
        bundle, manifest = self._prepare(temporary)
        candidate_root = Path(temporary) / "root" / "candidates"
        candidate_root.mkdir(parents=True, mode=0o700)
        ledger_root = (
            candidate_root.parent / "activations" / "candidate-installs"
        )
        authorization = self._authorization(manifest, bundle)
        return bundle, manifest, candidate_root, ledger_root, authorization

    def test_preparation_closes_payload_and_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            first, first_manifest = self._prepare(temporary, name="bundle-one")
            PREPARER.validate_bundle_manifest_v1(first_manifest)
            PREPARER.validate_bundle_files_v1(first, first_manifest)
            self.assertEqual(
                first_manifest["human_install_authorization"]["status"],
                "pending",
            )
            self.assertEqual(
                first_manifest["snapshot_activation"]["status"],
                "not_authorized",
            )
            self.assertFalse(first_manifest["positive_assurance_allowed"])
            self.assertEqual(
                first_manifest["dependency_environment_policy"]["status"],
                "candidate_prepared",
            )
            modes = {
                item["path"]: item["intended_mode"]
                for item in first_manifest["payload_denominator"]["entries"]
            }
            self.assertEqual(modes["vnext/runtime/module.py"], "0400")
            self.assertEqual(modes["vnext/runtime/runner"], "0500")

            second, second_manifest = self._prepare(temporary, name="bundle-two")
            PREPARER.validate_bundle_files_v1(second, second_manifest)
            self.assertEqual(first_manifest, second_manifest)

    def test_hostile_deferred_and_pending_scope_records_cannot_prepare_local_candidate(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repository, mappings, policy = self._fixture_inputs(root)
            boundary = self._preactivation_inputs(root, mappings)
            for threat, worker, human in (
                (
                    "hostile_code_in_scope_requires_external_executor",
                    None,
                    "accept",
                ),
                ("defer", None, "defer"),
            ):
                candidate_boundary = copy.deepcopy(boundary)
                decision = candidate_boundary["preactivation_decision"]
                decision["threat_boundary_selection"] = threat
                decision["worker_identity_selection"] = worker
                decision["human_decision"] = human
                decision["decision_digest"] = PREPARER.sealed_digest(
                    decision, "decision_digest"
                )
                candidate_boundary["preactivation_decision_raw"] = (
                    PREPARER.canonical_json_bytes(decision) + b"\n"
                )
                with self.assertRaises(
                    PREPARER.CandidateBoundaryError
                ) as observed:
                    PREPARER._prepare_bundle_from_mappings(
                        mappings=mappings,
                        dependency_environment_policy=policy,
                        repository_root=repository,
                        output=root / f"bundle-{threat}",
                        **candidate_boundary,
                        installer_path=SCRIPT,
                    )
                self.assertEqual(
                    observed.exception.code,
                    "candidate_local_profile_not_authorized_by_scope_decision",
                )

            pending_boundary = copy.deepcopy(boundary)
            resolution = pending_boundary["worker_principal_resolution"]
            resolution["resolution_state"] = "pending_principal_provisioning"
            resolution["derived_from"] = pending_boundary[
                "preactivation_decision"
            ]["decision_entity_ref"]
            for field in (
                "account_observation_ref",
                "principal_entity_ref",
                "account_name",
                "uid",
                "gid",
                "account_supplementary_gids",
                "effective_supplementary_gids",
                "umask",
                "login_shell",
                "non_login",
                "platform_binding",
                "resolved_at",
            ):
                resolution[field] = None
            resolution["resolution_digest"] = PREPARER.sealed_digest(
                resolution, "resolution_digest"
            )
            pending_boundary["worker_principal_resolution_raw"] = (
                PREPARER.canonical_json_bytes(resolution) + b"\n"
            )
            with self.assertRaises(PREPARER.CandidateBoundaryError) as observed:
                PREPARER._prepare_bundle_from_mappings(
                    mappings=mappings,
                    dependency_environment_policy=policy,
                    repository_root=repository,
                    output=root / "bundle-pending",
                    **pending_boundary,
                    installer_path=SCRIPT,
                )
            self.assertEqual(
                observed.exception.code, "candidate_worker_principal_not_resolved"
            )

    def test_locator_host_account_and_timestamp_substitution_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repository, mappings, policy = self._fixture_inputs(root)
            boundary = self._preactivation_inputs(root, mappings)
            locator_boundary = copy.deepcopy(boundary)
            resolution = locator_boundary["worker_principal_resolution"]
            resolution["decision_record_ref"] = copy.deepcopy(
                resolution["decision_record_ref"]
            )
            resolution["decision_record_ref"]["locator"] = str(
                root / "substituted-decision.json"
            )
            resolution["resolution_digest"] = PREPARER.sealed_digest(
                resolution, "resolution_digest"
            )
            locator_boundary["worker_principal_resolution_raw"] = (
                PREPARER.canonical_json_bytes(resolution) + b"\n"
            )
            with self.assertRaises(PREPARER.CandidateBoundaryError) as observed:
                PREPARER._prepare_bundle_from_mappings(
                    mappings=mappings,
                    dependency_environment_policy=policy,
                    repository_root=repository,
                    output=root / "bundle-locator",
                    **locator_boundary,
                    installer_path=SCRIPT,
                )
            self.assertEqual(
                observed.exception.code,
                "candidate_worker_principal_resolution_invalid",
            )

            decision = boundary["preactivation_decision"]
            decision_raw = boundary["preactivation_decision_raw"]
            decision_locator = boundary["preactivation_decision_locator"].resolve()
            for mutation, expected_code in (
                ("host", "candidate_worker_account_requalification_required"),
                ("account", "candidate_worker_account_observation_failed"),
                (
                    "timestamp",
                    "candidate_worker_account_observation_chronology_invalid",
                ),
            ):
                observation = copy.deepcopy(boundary["worker_account_observation"])
                if mutation == "host":
                    observation["platform_binding"]["hostname"] = "forged-host"
                    host_material = {
                        field: observation["platform_binding"][field]
                        for field in (
                            "os",
                            "architecture",
                            "os_release",
                            "platform_version",
                            "hostname",
                        )
                    }
                    observation["platform_binding"]["host_identity_digest"] = (
                        PREPARER.digest_bytes(
                            PREPARER.canonical_json_bytes(host_material)
                        )
                    )
                    observation["principal_entity_ref"] = (
                        PREPARER._principal_entity_ref_v1(
                            PREPARER._observation_material_v1(observation)
                        )
                    )
                elif mutation == "account":
                    observation["account_name"] = "missing-u10-principal"
                    observation["principal_entity_ref"] = (
                        PREPARER._principal_entity_ref_v1(
                            PREPARER._observation_material_v1(observation)
                        )
                    )
                else:
                    observation["observed_at"] = "2025-12-31T23:59:59Z"
                observation["observation_digest"] = PREPARER.sealed_digest(
                    observation, "observation_digest"
                )
                with self.assertRaises(
                    PREPARER.CandidateBoundaryError
                ) as observed:
                    PREPARER.validate_worker_account_observation_v1(
                        observation,
                        decision=decision,
                        decision_raw=decision_raw,
                        decision_locator=decision_locator,
                        reobserve_current=True,
                    )
                self.assertEqual(observed.exception.code, expected_code)

    def test_entity_collision_and_resolution_chronology_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _repository, mappings, _policy = self._fixture_inputs(root)
            boundary = self._preactivation_inputs(root, mappings)
            for mutation, expected_code in (
                (
                    "entity",
                    "candidate_worker_principal_resolution_entity_invalid",
                ),
                (
                    "timestamp",
                    "candidate_worker_principal_resolution_chronology_invalid",
                ),
            ):
                resolution = copy.deepcopy(boundary["worker_principal_resolution"])
                if mutation == "entity":
                    resolution["resolution_entity_ref"] = resolution[
                        "principal_entity_ref"
                    ]
                else:
                    resolution["resolved_at"] = "2026-01-01T00:00:00Z"
                resolution["resolution_digest"] = PREPARER.sealed_digest(
                    resolution, "resolution_digest"
                )
                with self.assertRaises(
                    PREPARER.CandidateBoundaryError
                ) as observed:
                    PREPARER.validate_worker_principal_resolution_v1(
                        resolution,
                        decision=boundary["preactivation_decision"],
                        decision_raw=boundary["preactivation_decision_raw"],
                        decision_locator=boundary[
                            "preactivation_decision_locator"
                        ].resolve(),
                        observation=boundary["worker_account_observation"],
                        observation_raw=boundary[
                            "worker_account_observation_raw"
                        ],
                        observation_locator=boundary[
                            "worker_account_observation_locator"
                        ].resolve(),
                        reobserve_current=True,
                    )
                self.assertEqual(observed.exception.code, expected_code)

    def test_entity_identity_uses_uuid_not_label_or_account_display_name(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _repository, mappings, _policy = self._fixture_inputs(root)
            boundary = self._preactivation_inputs(root, mappings)
            observation = copy.deepcopy(boundary["worker_account_observation"])
            observation["subject_entity_ref"] = (
                f"renamed U-10 subject・{PREPARER.U10_SUBJECT_ENTITY_ID}"
            )
            decision_entity_id = PREPARER._entity_id_v1(
                boundary["preactivation_decision"]["decision_entity_ref"],
                code="test",
            )
            principal_entity_id = PREPARER._entity_id_v1(
                observation["principal_entity_ref"], code="test"
            )
            observation["derived_from"] = f"renamed decision・{decision_entity_id}"
            observation["principal_entity_ref"] = (
                f"renamed account label・{principal_entity_id}"
            )
            observation["observation_digest"] = PREPARER.sealed_digest(
                observation, "observation_digest"
            )
            PREPARER.validate_worker_account_observation_v1(
                observation,
                decision=boundary["preactivation_decision"],
                decision_raw=boundary["preactivation_decision_raw"],
                decision_locator=boundary["preactivation_decision_locator"].resolve(),
                reobserve_current=True,
            )
            observation_raw = PREPARER.canonical_json_bytes(observation) + b"\n"
            resolution = copy.deepcopy(boundary["worker_principal_resolution"])
            observation_entity_id = PREPARER._entity_id_v1(
                observation["observation_entity_ref"], code="test"
            )
            resolution["subject_entity_ref"] = observation["subject_entity_ref"]
            resolution["derived_from"] = (
                f"renamed observation・{observation_entity_id}"
            )
            resolution["principal_entity_ref"] = observation[
                "principal_entity_ref"
            ]
            resolution["account_observation_ref"] = {
                "record_id": observation["observation_id"],
                "locator": str(
                    boundary["worker_account_observation_locator"].resolve()
                ),
                "artifact_digest": PREPARER.digest_bytes(observation_raw),
                "semantic_digest": observation["observation_digest"],
            }
            resolution["resolution_digest"] = PREPARER.sealed_digest(
                resolution, "resolution_digest"
            )
            PREPARER.validate_worker_principal_resolution_v1(
                resolution,
                decision=boundary["preactivation_decision"],
                decision_raw=boundary["preactivation_decision_raw"],
                decision_locator=boundary["preactivation_decision_locator"].resolve(),
                observation=observation,
                observation_raw=observation_raw,
                observation_locator=boundary[
                    "worker_account_observation_locator"
                ].resolve(),
                reobserve_current=True,
            )
            original_material = PREPARER._observation_material_v1(observation)
            renamed_material = copy.deepcopy(original_material)
            renamed_material["account_name"] = "renamed-display-account"
            self.assertEqual(
                PREPARER._entity_id_v1(
                    PREPARER._principal_entity_ref_v1(original_material), code="test"
                ),
                PREPARER._entity_id_v1(
                    PREPARER._principal_entity_ref_v1(renamed_material), code="test"
                ),
            )
            self.assertNotEqual(
                PREPARER._principal_entity_ref_v1(original_material),
                PREPARER._principal_entity_ref_v1(renamed_material),
            )

    def test_prepare_cli_requires_records_and_has_no_raw_uid_gid_inputs(self) -> None:
        parser = PREPARER._parser()
        arguments = parser.parse_args(
            [
                "prepare",
                "--repository-root",
                "/repository",
                "--python",
                "/python",
                "--uv",
                "/uv",
                "--output",
                "/output",
                "--preactivation-decision",
                "/decision.json",
                "--worker-principal-resolution",
                "/resolution.json",
            ]
        )
        self.assertEqual(arguments.preactivation_decision, Path("/decision.json"))
        self.assertFalse(hasattr(arguments, "worker_uid"))
        self.assertFalse(hasattr(arguments, "worker_gid"))

    def test_decision_evidence_must_exist_match_digest_and_avoid_symlinks(self) -> None:
        for mutation, expected_code in (
            ("missing", "candidate_preactivation_decision_evidence_unavailable"),
            (
                "digest",
                "candidate_preactivation_decision_evidence_digest_mismatch",
            ),
            ("symlink", "candidate_preactivation_decision_evidence_unavailable"),
        ):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                repository, mappings, policy = self._fixture_inputs(root)
                boundary = self._preactivation_inputs(root, mappings)
                decision = boundary["preactivation_decision"]
                evidence = Path(decision["decision_evidence_ref"]["locator"])
                if mutation == "missing":
                    evidence.unlink()
                elif mutation == "digest":
                    evidence.write_text("changed after decision\n", encoding="utf-8")
                else:
                    target = evidence.with_name("evidence-target.json")
                    target.write_bytes(evidence.read_bytes())
                    link = evidence.with_name("evidence-link.json")
                    link.symlink_to(target)
                    decision["decision_evidence_ref"]["locator"] = str(link)
                    decision["decision_evidence_ref"]["content_digest"] = (
                        PREPARER.digest_bytes(target.read_bytes())
                    )
                    decision["decision_digest"] = PREPARER.sealed_digest(
                        decision, "decision_digest"
                    )
                    boundary["preactivation_decision_raw"] = (
                        PREPARER.canonical_json_bytes(decision) + b"\n"
                    )
                with self.assertRaises(
                    PREPARER.CandidateBoundaryError
                ) as observed:
                    PREPARER._prepare_bundle_from_mappings(
                        mappings=mappings,
                        dependency_environment_policy=policy,
                        repository_root=repository,
                        output=root / f"bundle-{mutation}",
                        **boundary,
                        installer_path=SCRIPT,
                    )
                self.assertEqual(observed.exception.code, expected_code)

    def test_payload_tamper_and_unlisted_file_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle, manifest = self._prepare(temporary)
            payload = bundle / "payload"
            self._make_mutable(bundle)
            module = payload / "vnext" / "runtime" / "module.py"
            module.write_text("VALUE = 2\n", encoding="utf-8")
            with self.assertRaises(PREPARER.CandidateBoundaryError) as observed:
                PREPARER.validate_bundle_files_v1(bundle, manifest)
            self.assertEqual(
                observed.exception.code, "candidate_payload_artifact_mismatch"
            )

            module.write_text("VALUE = 1\n", encoding="utf-8")
            extra = payload / "vnext" / "runtime" / "unlisted.py"
            extra.write_text("UNLISTED = True\n", encoding="utf-8")
            with self.assertRaises(PREPARER.CandidateBoundaryError) as observed:
                PREPARER.validate_bundle_files_v1(bundle, manifest)
            self.assertEqual(
                observed.exception.code, "candidate_payload_denominator_mismatch"
            )

    def test_bundle_root_and_payload_empty_directory_denominators_are_closed(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle, manifest = self._prepare(temporary)
            self._make_mutable(bundle)
            extra_root = bundle / "unlisted-root-metadata"
            extra_root.write_text("forbidden\n", encoding="utf-8")
            with self.assertRaises(PREPARER.CandidateBoundaryError) as observed:
                PREPARER.validate_bundle_files_v1(bundle, manifest)
            self.assertEqual(
                observed.exception.code,
                "candidate_bundle_root_denominator_mismatch",
            )
            extra_root.unlink()
            empty = bundle / "payload" / "unlisted-empty-directory"
            empty.mkdir()
            with self.assertRaises(PREPARER.CandidateBoundaryError) as observed:
                PREPARER.validate_bundle_files_v1(bundle, manifest)
            self.assertEqual(
                observed.exception.code,
                "candidate_payload_directory_denominator_mismatch",
            )

    def test_symlink_outside_mapping_root_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repository, mappings, policy = self._fixture_inputs(root)
            boundary = self._preactivation_inputs(root, mappings)
            source = repository / "bad-source"
            source.mkdir()
            outside = root / "outside.txt"
            outside.write_text("secret\n", encoding="utf-8")
            (source / "escape").symlink_to(outside)
            mappings.append(self._mapping(source, destination="vnext/bad-runtime"))
            with self.assertRaises(PREPARER.CandidateBoundaryError) as observed:
                PREPARER._prepare_bundle_from_mappings(
                    mappings=mappings,
                    dependency_environment_policy=policy,
                    repository_root=repository,
                    output=root / "bundle",
                    **boundary,
                    installer_path=SCRIPT,
                )
            self.assertEqual(observed.exception.code, "candidate_source_escape")

    def test_candidate_install_never_activates_snapshot_or_trust_store(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle, manifest = self._prepare(temporary)
            candidate_root = Path(temporary) / "root" / "candidates"
            candidate_root.mkdir(parents=True, mode=0o700)
            authorization = self._authorization(manifest, bundle)
            receipt = PREPARER._install_candidate_bundle(
                bundle_root=bundle,
                authorization=authorization,
                candidate_root=candidate_root,
                required_uid=os.getuid(),
                enforce_fixed_target=False,
            )
            installed = candidate_root / manifest["bundle_id"]
            self.assertTrue(installed.is_dir())
            self.assertEqual(
                receipt["installation_state"],
                "candidate_installed_not_activated",
            )
            self.assertEqual(receipt["snapshot_adoption_status"], "pending")
            self.assertEqual(
                receipt["snapshot_lock_validation_status"],
                "pending_non_root_final_path_check",
            )
            self.assertFalse(receipt["active_snapshot_written"])
            self.assertFalse(receipt["active_trust_store_written"])
            self.assertFalse(receipt["positive_assurance_allowed"])
            pyvenv = installed / "payload" / "vnext" / ".venv" / "pyvenv.cfg"
            self.assertIn(
                str(installed / "payload"), pyvenv.read_text(encoding="utf-8")
            )
            self.assertFalse(
                (candidate_root.parent / "snapshots").exists(),
                "candidate installer must not create an active snapshot root",
            )
            self.assertFalse(
                (candidate_root.parent / "trust-store-current.json").exists(),
                "candidate installer must not create an active trust store",
            )
            self.assertEqual(
                stat_mode(installed / "payload" / "vnext" / "runtime" / "module.py"),
                0o400,
            )

    def test_install_records_validate_against_all_five_closed_schemas(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle, manifest, candidate_root, ledger_root, authorization = (
                self._install_context(temporary)
            )
            receipt = PREPARER._install_candidate_bundle(
                bundle_root=bundle,
                authorization=authorization,
                candidate_root=candidate_root,
                required_uid=os.getuid(),
                enforce_fixed_target=False,
            )
            consumption = json.loads(
                (
                    ledger_root
                    / f"{authorization['authorization_id']}.consumption.json"
                ).read_text(encoding="utf-8")
            )
            projection = json.loads(
                (
                    candidate_root
                    / manifest["bundle_id"]
                    / PREPARER.PROJECTION_NAME
                ).read_text(encoding="utf-8")
            )
            records = {
                "u10-root-candidate-bundle-v1.schema.json": manifest,
                "u10-candidate-install-authorization-v1.schema.json": authorization,
                "u10-candidate-install-authorization-consumption-v1.schema.json": consumption,
                "u10-candidate-install-projection-v1.schema.json": projection,
                "u10-candidate-install-receipt-v2.schema.json": receipt,
            }
            for name, record in records.items():
                schema = json.loads(
                    (SCHEMA_DIRECTORY / name).read_text(encoding="utf-8")
                )
                errors = list(Draft202012Validator(schema).iter_errors(record))
                self.assertEqual(errors, [], f"{name}: {errors}")
            self.assertNotIn("publication_occurred", projection)
            self.assertNotIn("installed_at", projection)
            self.assertEqual(
                receipt["publication_not_before"], consumption["reserved_at"]
            )
            self.assertLessEqual(
                receipt["publication_not_before"],
                receipt["publication_observed_at"],
            )
            self.assertLessEqual(
                receipt["publication_observed_at"], receipt["receipt_recorded_at"]
            )
            self.assertEqual(
                projection["installed_denominator"]["scope"], "payload_tree_only"
            )
            self.assertEqual(
                projection["metadata_denominator"]["scope"],
                "candidate_root_metadata_excluding_payload_tree",
            )
            self.assertEqual(
                set((candidate_root / manifest["bundle_id"]).iterdir()),
                {
                    candidate_root / manifest["bundle_id"] / "payload",
                    candidate_root / manifest["bundle_id"] / PREPARER.MANIFEST_NAME,
                    candidate_root
                    / manifest["bundle_id"]
                    / PREPARER.PROJECTION_NAME,
                },
            )

    def test_consumed_authorization_retries_same_occurrence_after_pre_publish_failure(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle, manifest, candidate_root, ledger_root, authorization = (
                self._install_context(temporary)
            )
            failure = PREPARER.CandidateBoundaryError(
                "test_pre_publish_failure", "injected"
            )
            with mock.patch.object(
                PREPARER, "_rename_directory_no_replace_v1", side_effect=failure
            ):
                with self.assertRaises(PREPARER.CandidateBoundaryError) as observed:
                    PREPARER._install_candidate_bundle(
                        bundle_root=bundle,
                        authorization=authorization,
                        candidate_root=candidate_root,
                        required_uid=os.getuid(),
                        enforce_fixed_target=False,
                    )
            self.assertEqual(observed.exception.code, "test_pre_publish_failure")
            consumption_path = (
                ledger_root / f"{authorization['authorization_id']}.consumption.json"
            )
            consumption = json.loads(consumption_path.read_text(encoding="utf-8"))
            self.assertFalse(
                (
                    ledger_root / f"{authorization['authorization_id']}.receipt.json"
                ).exists()
            )
            self.assertFalse((candidate_root / manifest["bundle_id"]).exists())
            self.assertEqual(list(candidate_root.glob(".installing.*")), [])

            receipt = PREPARER._install_candidate_bundle(
                bundle_root=bundle,
                authorization=authorization,
                candidate_root=candidate_root,
                required_uid=os.getuid(),
                enforce_fixed_target=False,
            )
            self.assertEqual(receipt["occurrence_id"], consumption["occurrence_id"])
            self.assertEqual(
                receipt["consumption_ref"]["consumption_digest"],
                consumption["consumption_digest"],
            )

    def test_completed_install_cannot_be_replayed_after_final_tree_deletion(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle, manifest, candidate_root, _ledger_root, authorization = (
                self._install_context(temporary)
            )
            PREPARER._install_candidate_bundle(
                bundle_root=bundle,
                authorization=authorization,
                candidate_root=candidate_root,
                required_uid=os.getuid(),
                enforce_fixed_target=False,
            )
            final = candidate_root / manifest["bundle_id"]
            self._make_mutable(final)
            shutil.rmtree(final)
            with self.assertRaises(PREPARER.CandidateBoundaryError) as observed:
                PREPARER._install_candidate_bundle(
                    bundle_root=bundle,
                    authorization=authorization,
                    candidate_root=candidate_root,
                    required_uid=os.getuid(),
                    enforce_fixed_target=False,
                )
            self.assertEqual(
                observed.exception.code, "candidate_install_completed_target_missing"
            )
            self.assertFalse(final.exists())

    def test_completed_chain_rejects_missing_immutable_authorization_copy(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle, _manifest, candidate_root, ledger_root, authorization = (
                self._install_context(temporary)
            )
            PREPARER._install_candidate_bundle(
                bundle_root=bundle,
                authorization=authorization,
                candidate_root=candidate_root,
                required_uid=os.getuid(),
                enforce_fixed_target=False,
            )
            archived = (
                ledger_root / f"{authorization['authorization_id']}.authorization.json"
            )
            archived.unlink()
            with self.assertRaises(PREPARER.CandidateBoundaryError) as observed:
                PREPARER._install_candidate_bundle(
                    bundle_root=bundle,
                    authorization=authorization,
                    candidate_root=candidate_root,
                    required_uid=os.getuid(),
                    enforce_fixed_target=False,
                )
            self.assertEqual(
                observed.exception.code,
                "candidate_install_authorization_archive_missing",
            )
            self.assertFalse(archived.exists(), "missing evidence must not be invented")

    def test_crash_stale_stage_is_removed_under_authorization_lock(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle, _manifest, candidate_root, _ledger_root, authorization = (
                self._install_context(temporary)
            )
            digest = authorization["authorization_digest"]["value"]
            stale = candidate_root / f".installing.{digest}.crash"
            (stale / "partial").mkdir(parents=True)
            (stale / "partial" / "fragment").write_text(
                "not an occurrence\n", encoding="utf-8"
            )
            receipt = PREPARER._install_candidate_bundle(
                bundle_root=bundle,
                authorization=authorization,
                candidate_root=candidate_root,
                required_uid=os.getuid(),
                enforce_fixed_target=False,
            )
            self.assertFalse(stale.exists())
            self.assertTrue(receipt["publication_occurred"])

    def test_append_only_link_crash_recovers_nlink_and_cleans_prelink_stale_temp(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            _bundle, _manifest, candidate_root, ledger_root, authorization = (
                self._install_context(temporary)
            )
            PREPARER._prepare_candidate_install_ledger_v1(
                candidate_root=candidate_root,
                ledger_root=ledger_root,
                required_uid=os.getuid(),
                enforce_fixed_target=False,
            )
            authorization_path, _consumption_path, _receipt_path = (
                PREPARER._ledger_record_paths_v1(
                    authorization, ledger_root=ledger_root
                )
            )
            raw = PREPARER._json_record_bytes_v1(authorization)
            linked_temp = (
                ledger_root / f".{authorization_path.name}.tmp.linked-crash"
            )
            PREPARER._write_exclusive(linked_temp, raw, mode=0o400)
            os.link(linked_temp, authorization_path, follow_symlinks=False)
            self.assertEqual(authorization_path.stat().st_nlink, 2)
            recovered, recovered_raw = PREPARER._read_ledger_record_raw_v1(
                authorization_path,
                ledger_root=ledger_root,
                required_uid=os.getuid(),
            )
            self.assertEqual(recovered, authorization)
            self.assertEqual(recovered_raw, raw)
            self.assertFalse(linked_temp.exists())
            self.assertEqual(authorization_path.stat().st_nlink, 1)

        with tempfile.TemporaryDirectory() as temporary:
            _bundle, _manifest, candidate_root, ledger_root, authorization = (
                self._install_context(temporary)
            )
            PREPARER._prepare_candidate_install_ledger_v1(
                candidate_root=candidate_root,
                ledger_root=ledger_root,
                required_uid=os.getuid(),
                enforce_fixed_target=False,
            )
            authorization_path, _consumption_path, _receipt_path = (
                PREPARER._ledger_record_paths_v1(
                    authorization, ledger_root=ledger_root
                )
            )
            raw = PREPARER._json_record_bytes_v1(authorization)
            stale_temp = ledger_root / f".{authorization_path.name}.tmp.prelink-crash"
            PREPARER._write_exclusive(stale_temp, raw, mode=0o400)
            PREPARER._publish_append_only_record_v1(
                path=authorization_path,
                record=authorization,
                ledger_root=ledger_root,
                required_uid=os.getuid(),
            )
            self.assertFalse(stale_temp.exists())
            self.assertEqual(authorization_path.stat().st_nlink, 1)

    def test_parent_fsync_failure_reconciles_exact_final_without_new_occurrence(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle, manifest, candidate_root, ledger_root, authorization = (
                self._install_context(temporary)
            )
            original = PREPARER._fsync_directory_v1
            failed = False

            def fail_once(path: Path, *, code: str) -> None:
                nonlocal failed
                if (
                    path == candidate_root
                    and code == "candidate_install_parent_fsync_failed"
                    and not failed
                ):
                    failed = True
                    raise PREPARER.CandidateBoundaryError(code, "injected")
                original(path, code=code)

            with mock.patch.object(PREPARER, "_fsync_directory_v1", fail_once):
                with self.assertRaises(PREPARER.CandidateBoundaryError) as observed:
                    PREPARER._install_candidate_bundle(
                        bundle_root=bundle,
                        authorization=authorization,
                        candidate_root=candidate_root,
                        required_uid=os.getuid(),
                        enforce_fixed_target=False,
                    )
            self.assertEqual(
                observed.exception.code, "candidate_install_parent_fsync_failed"
            )
            final = candidate_root / manifest["bundle_id"]
            original_projection = json.loads(
                (final / PREPARER.PROJECTION_NAME).read_text(encoding="utf-8")
            )
            self.assertFalse(
                (
                    ledger_root / f"{authorization['authorization_id']}.receipt.json"
                ).exists()
            )
            reconciled = PREPARER._install_candidate_bundle(
                bundle_root=bundle,
                authorization=authorization,
                candidate_root=candidate_root,
                required_uid=os.getuid(),
                enforce_fixed_target=False,
            )
            self.assertEqual(
                reconciled["projection_ref"]["projection_digest"],
                original_projection["projection_digest"],
            )
            self.assertEqual(
                reconciled["publication_not_before"],
                json.loads(
                    (
                        ledger_root
                        / f"{authorization['authorization_id']}.consumption.json"
                    ).read_text(encoding="utf-8")
                )["reserved_at"],
            )
            self.assertEqual(list(candidate_root.glob(".installing.*")), [])

    def test_stage_root_extra_entry_is_rejected_and_cleaned(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle, _manifest, candidate_root, _ledger_root, authorization = (
                self._install_context(temporary)
            )
            original = PREPARER._verify_frozen_installation_v1

            def inject_extra(**kwargs: object) -> None:
                stage = kwargs["stage"]
                assert isinstance(stage, Path)
                os.chmod(stage, 0o700)
                extra = stage / "unlisted-root-metadata"
                extra.write_text("forbidden\n", encoding="utf-8")
                extra.chmod(0o400)
                os.chmod(stage, 0o500)
                original(**kwargs)

            with mock.patch.object(
                PREPARER, "_verify_frozen_installation_v1", inject_extra
            ):
                with self.assertRaises(PREPARER.CandidateBoundaryError) as observed:
                    PREPARER._install_candidate_bundle(
                        bundle_root=bundle,
                        authorization=authorization,
                        candidate_root=candidate_root,
                        required_uid=os.getuid(),
                        enforce_fixed_target=False,
                    )
            self.assertEqual(
                observed.exception.code,
                "candidate_frozen_root_denominator_mismatch",
            )
            self.assertEqual(list(candidate_root.glob(".installing.*")), [])

    def test_partial_stage_creation_is_inside_cleanup_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle, _manifest, candidate_root, _ledger_root, authorization = (
                self._install_context(temporary)
            )
            original = PREPARER._ensure_directory_exact

            def fail_payload(path: Path, *, mode: int) -> None:
                if path.name == "payload" and path.parent.name.startswith(
                    ".installing."
                ):
                    raise PREPARER.CandidateBoundaryError(
                        "test_payload_create_failure", str(path)
                    )
                original(path, mode=mode)

            with mock.patch.object(PREPARER, "_ensure_directory_exact", fail_payload):
                with self.assertRaises(PREPARER.CandidateBoundaryError) as observed:
                    PREPARER._install_candidate_bundle(
                        bundle_root=bundle,
                        authorization=authorization,
                        candidate_root=candidate_root,
                        required_uid=os.getuid(),
                        enforce_fixed_target=False,
                    )
            self.assertEqual(observed.exception.code, "test_payload_create_failure")
            self.assertEqual(list(candidate_root.glob(".installing.*")), [])

    def test_parallel_same_authorization_creates_one_occurrence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle, _manifest, candidate_root, ledger_root, authorization = (
                self._install_context(temporary)
            )

            def install() -> tuple[str, object]:
                try:
                    return (
                        "ok",
                        PREPARER._install_candidate_bundle(
                            bundle_root=bundle,
                            authorization=authorization,
                            candidate_root=candidate_root,
                            required_uid=os.getuid(),
                            enforce_fixed_target=False,
                        ),
                    )
                except PREPARER.CandidateBoundaryError as exc:
                    return "rejected", exc.code

            with ThreadPoolExecutor(max_workers=2) as executor:
                results = list(executor.map(lambda _index: install(), range(2)))
            successes = [value for status, value in results if status == "ok"]
            self.assertGreaterEqual(len(successes), 1, results)
            self.assertEqual(
                len(
                    {
                        value["occurrence_id"]
                        for value in successes
                        if isinstance(value, dict)
                    }
                ),
                1,
            )
            self.assertEqual(
                len(list(ledger_root.glob("*.consumption.json"))), 1
            )
            self.assertEqual(len(list(ledger_root.glob("*.receipt.json"))), 1)
            self.assertEqual(list(ledger_root.glob(".*.tmp")), [])

    def test_parallel_different_authorizations_do_not_leave_losing_consumption(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle, _manifest, candidate_root, ledger_root, authorization = (
                self._install_context(temporary)
            )
            alternative = copy.deepcopy(authorization)
            alternative["authorization_id"] += ".alternative"
            alternative["authorization_digest"] = PREPARER.sealed_digest(
                alternative, "authorization_digest"
            )

            def install(selected: dict) -> tuple[str, object]:
                try:
                    return (
                        "ok",
                        PREPARER._install_candidate_bundle(
                            bundle_root=bundle,
                            authorization=selected,
                            candidate_root=candidate_root,
                            required_uid=os.getuid(),
                            enforce_fixed_target=False,
                        ),
                    )
                except PREPARER.CandidateBoundaryError as exc:
                    return "rejected", exc.code

            with ThreadPoolExecutor(max_workers=2) as executor:
                results = list(executor.map(install, (authorization, alternative)))
            self.assertEqual(
                sum(1 for status, _value in results if status == "ok"), 1, results
            )
            self.assertEqual(
                len(list(ledger_root.glob("*.consumption.json"))), 1, results
            )
            self.assertEqual(len(list(ledger_root.glob("*.receipt.json"))), 1)

    def test_unresolved_consumption_blocks_a_different_authorization(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle, _manifest, candidate_root, ledger_root, authorization = (
                self._install_context(temporary)
            )
            failure = PREPARER.CandidateBoundaryError(
                "test_pre_publish_failure", "injected"
            )
            with mock.patch.object(
                PREPARER, "_rename_directory_no_replace_v1", side_effect=failure
            ):
                with self.assertRaises(PREPARER.CandidateBoundaryError):
                    PREPARER._install_candidate_bundle(
                        bundle_root=bundle,
                        authorization=authorization,
                        candidate_root=candidate_root,
                        required_uid=os.getuid(),
                        enforce_fixed_target=False,
                    )

            alternative = copy.deepcopy(authorization)
            alternative["authorization_id"] += ".alternative"
            alternative["authorization_digest"] = PREPARER.sealed_digest(
                alternative, "authorization_digest"
            )
            with self.assertRaises(PREPARER.CandidateBoundaryError) as observed:
                PREPARER._install_candidate_bundle(
                    bundle_root=bundle,
                    authorization=alternative,
                    candidate_root=candidate_root,
                    required_uid=os.getuid(),
                    enforce_fixed_target=False,
                )
            self.assertEqual(
                observed.exception.code,
                "candidate_install_competing_consumption_unresolved",
            )
            self.assertEqual(len(list(ledger_root.glob("*.consumption.json"))), 1)
            self.assertFalse(
                (
                    ledger_root
                    / f"{alternative['authorization_id']}.authorization.json"
                ).exists()
            )
            self.assertFalse(
                (
                    ledger_root
                    / f"{alternative['authorization_id']}.consumption.json"
                ).exists()
            )

    @unittest.skipUnless(sys.platform == "darwin", "Darwin extended ACL contract")
    def test_candidate_root_extended_acl_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle, _manifest, candidate_root, _ledger_root, authorization = (
                self._install_context(temporary)
            )
            subprocess.run(
                ["/bin/chmod", "+a", "everyone allow add_file", str(candidate_root)],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            try:
                with self.assertRaises(PREPARER.CandidateBoundaryError) as observed:
                    PREPARER._install_candidate_bundle(
                        bundle_root=bundle,
                        authorization=authorization,
                        candidate_root=candidate_root,
                        required_uid=os.getuid(),
                        enforce_fixed_target=False,
                    )
                self.assertEqual(
                    observed.exception.code, "candidate_install_root_extended_acl"
                )
            finally:
                subprocess.run(
                    ["/bin/chmod", "-N", str(candidate_root)],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )

    def test_pending_or_cross_bundle_authorization_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle, manifest = self._prepare(temporary)
            pending = self._authorization(manifest, bundle, decision="pending")
            with self.assertRaises(PREPARER.CandidateBoundaryError):
                PREPARER.validate_install_authorization_v1(pending, manifest)

            changed = self._authorization(manifest, bundle)
            changed["bundle_id"] = "candidate.u10." + "0" * 64
            changed["authorization_digest"] = PREPARER.sealed_digest(
                changed, "authorization_digest"
            )
            with self.assertRaises(PREPARER.CandidateBoundaryError):
                PREPARER.validate_install_authorization_v1(changed, manifest)

            expanded = self._authorization(manifest, bundle)
            expanded["unreviewed_extension"] = True
            expanded["authorization_digest"] = PREPARER.sealed_digest(
                expanded, "authorization_digest"
            )
            with self.assertRaises(PREPARER.CandidateBoundaryError) as observed:
                PREPARER.validate_install_authorization_v1(expanded, manifest)
            self.assertEqual(
                observed.exception.code, "candidate_install_authorization_invalid"
            )

            timeless = self._authorization(manifest, bundle)
            timeless["recorded_at"] = "not-a-time"
            timeless["authorization_digest"] = PREPARER.sealed_digest(
                timeless, "authorization_digest"
            )
            with self.assertRaises(PREPARER.CandidateBoundaryError) as observed:
                PREPARER.validate_install_authorization_v1(timeless, manifest)
            self.assertEqual(
                observed.exception.code,
                "candidate_install_authorization_time_invalid",
            )

    def test_manifest_cannot_redirect_candidate_install_to_active_area(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            _bundle, manifest = self._prepare(temporary)
            forged = copy.deepcopy(manifest)
            forged["target"]["candidate_path"] = str(PREPARER.SNAPSHOT_ROOT / "forged")
            forged["bundle_digest"] = PREPARER.sealed_digest(forged, "bundle_digest")
            with self.assertRaises(PREPARER.CandidateBoundaryError) as observed:
                PREPARER.validate_bundle_manifest_v1(forged)
            self.assertEqual(observed.exception.code, "candidate_target_invalid")

    def test_manifest_cannot_inject_relocation_or_root_worker(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            _bundle, manifest = self._prepare(temporary)
            forged_template = copy.deepcopy(manifest)
            forged_template["root_generated_entries"][0]["content_template"] = (
                "home = /Users/attacker/runtime\n{candidate_payload}\n"
            )
            forged_template["bundle_digest"] = PREPARER.sealed_digest(
                forged_template, "bundle_digest"
            )
            with self.assertRaises(PREPARER.CandidateBoundaryError) as observed:
                PREPARER.validate_bundle_manifest_v1(forged_template)
            self.assertEqual(
                observed.exception.code, "candidate_generated_entries_invalid"
            )

            forged_worker = copy.deepcopy(manifest)
            forged_worker["worker_identity"]["uid"] = 0
            forged_worker["bundle_digest"] = PREPARER.sealed_digest(
                forged_worker, "bundle_digest"
            )
            with self.assertRaises(PREPARER.CandidateBoundaryError) as observed:
                PREPARER.validate_bundle_manifest_v1(forged_worker)
            self.assertEqual(
                observed.exception.code, "candidate_worker_identity_invalid"
            )

    def test_manifest_file_is_valid_json_and_digest_bound(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle, manifest = self._prepare(temporary)
            recorded = json.loads(
                (bundle / PREPARER.MANIFEST_NAME).read_text(encoding="utf-8")
            )
            self.assertEqual(recorded, manifest)
            self.assertEqual(
                recorded["bundle_digest"],
                PREPARER.sealed_digest(recorded, "bundle_digest"),
            )

    def test_editable_project_is_excluded_and_source_root_is_separate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle, manifest = self._prepare(temporary)
            policy = manifest["dependency_environment_policy"]
            dependency_root = policy["dependency_import_root"]
            paths = {
                item["path"] for item in manifest["payload_denominator"]["entries"]
            }
            self.assertIn(
                "vnext/src/semantic_guard_vnext/__init__.py",
                paths,
            )
            self.assertIn(PREPARER.ROOT_BROKER_BOOTSTRAP_PATH, paths)
            self.assertIn(f"{dependency_root}/third_party.py", paths)
            for excluded in policy["excluded_project_entries"]:
                excluded_root = f"{dependency_root}/{excluded}"
                self.assertFalse(
                    any(
                        path == excluded_root or path.startswith(f"{excluded_root}/")
                        for path in paths
                    ),
                    excluded_root,
                )
                self.assertFalse((bundle / "payload" / excluded_root).exists())

    def test_lock_check_spec_is_offline_frozen_and_excludes_project_install(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle, manifest = self._prepare(temporary)
            payload = (bundle / "payload").resolve()
            spec = PREPARER.snapshot_lock_check_spec_v1(
                manifest,
                candidate_payload=payload,
            )
            self.assertEqual(spec["cwd"], str(payload / "vnext"))
            self.assertEqual(
                spec["argv"],
                [
                    str(payload / "vnext" / "tools" / "uv"),
                    "sync",
                    "--check",
                    "--offline",
                    "--frozen",
                    "--no-install-project",
                    "--python",
                    str(payload / "vnext" / ".venv" / "bin" / "python"),
                    "--extra",
                    "nlp-ja",
                    "--extra",
                    "nlp-ja-dependency",
                ],
            )
            self.assertEqual(spec["execution_identity"], "non_root_worker")
            self.assertEqual(spec["mutation_authority"], "none")
            self.assertEqual(spec["snapshot_activation_authority"], "none")

    def test_dependency_mapping_cannot_retain_editable_project(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repository, mappings, policy = self._fixture_inputs(root)
            boundary = self._preactivation_inputs(root, mappings)
            dependency_mapping = next(
                item for item in mappings if item["role"] == "python_dependency_runtime"
            )
            dependency_mapping["excluded_prefixes"] = [
                item
                for item in dependency_mapping["excluded_prefixes"]
                if item != PREPARER.EDITABLE_POINTER_NAME
            ]
            with self.assertRaises(PREPARER.CandidateBoundaryError) as observed:
                PREPARER._prepare_bundle_from_mappings(
                    mappings=mappings,
                    dependency_environment_policy=policy,
                    repository_root=repository,
                    output=root / "bundle",
                    **boundary,
                    installer_path=SCRIPT,
                )
            self.assertEqual(
                observed.exception.code,
                "candidate_dependency_mapping_policy_mismatch",
            )

    def test_lock_check_rejects_reintroduced_editable_pointer(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle, manifest = self._prepare(temporary)
            self._make_mutable(bundle)
            payload = bundle / "payload"
            dependency_root = (
                payload
                / manifest["dependency_environment_policy"]["dependency_import_root"]
            )
            (dependency_root / PREPARER.EDITABLE_POINTER_NAME).write_text(
                "/untrusted/source\n", encoding="utf-8"
            )
            with self.assertRaises(PREPARER.CandidateBoundaryError) as observed:
                PREPARER.snapshot_lock_check_spec_v1(
                    manifest,
                    candidate_payload=payload,
                )
            self.assertEqual(
                observed.exception.code,
                "candidate_project_dependency_leaked",
            )


def stat_mode(path: Path) -> int:
    return path.stat().st_mode & 0o777


if __name__ == "__main__":
    unittest.main()
