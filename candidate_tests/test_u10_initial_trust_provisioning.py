from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import uuid

from jsonschema import Draft202012Validator
from referencing import Registry, Resource


SCRIPT_ROOT = Path(__file__).parent / "fixtures" / "scripts"
SCHEMA_ROOT = Path(__file__).parents[1] / "src" / "semantic_guard_vnext" / "validation" / "env-path-contracts"


def _load(name: str, path: Path):
    specification = importlib.util.spec_from_file_location(name, path)
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    sys.modules[name] = module
    try:
        specification.loader.exec_module(module)
    finally:
        sys.modules.pop(name, None)
    return module


provisioner = _load(
    "u10_initial_trust_provisioner_test",
    SCRIPT_ROOT / "u10_initial_trust_provisioner.py",
)
capsule_builder = _load(
    "u10_initial_bootstrap_capsule_builder_test",
    SCRIPT_ROOT / "prepare_u10_initial_bootstrap_capsule.py",
)


def _timestamp(delta: timedelta = timedelta()) -> str:
    return (
        datetime.now(timezone.utc) + delta
    ).isoformat().replace("+00:00", "Z")


def _dummy_digest(character: str = "0") -> dict[str, str]:
    return {"algorithm": "sha256", "value": character * 64}


def _publisher_binding(character: str = "0") -> dict:
    runtime = {
        "effective_python_path": str(provisioner.BROKER_EFFECTIVE_PATH),
        "effective_python_path_artifact_digest": _dummy_digest(character),
        "runtime_manifest_locator": str(provisioner.BROKER_RUNTIME_MANIFEST),
        "runtime_manifest_artifact_digest": _dummy_digest(character),
        "runtime_manifest_digest": _dummy_digest(character),
        "runtime_tree_digest": _dummy_digest(character),
    }
    control_runtime = {
        **runtime,
        "effective_python_path": str(provisioner.CONTROL_EFFECTIVE_PATH),
        "runtime_manifest_locator": str(provisioner.CONTROL_RUNTIME_MANIFEST),
        "broker_package_binding": {
            "package_root": str(
                provisioner.U10_ROOT
                / "bootstrap"
                / "semantic_guard_u10_broker"
            ),
            "entry_count": 1,
            "tree_digest": _dummy_digest(character),
        },
    }
    value = {
        "schema_version": provisioner.CONTROL_PUBLISHER_BINDING_SCHEMA,
        "contract_id": provisioner.CONTROL_PUBLISHER_CONTRACT_ID,
        "launch_profile": (
            "fixed-root-wrapper-broker-outer-control-runtime-dispatcher/v1"
        ),
        "public_argument_denominator": ["operation", "identifier"],
        "allowed_operations": [
            "activate-snapshot",
            "activate-store",
            "key",
            "project-snapshot",
            "revoke-store",
        ],
        "caller_supplied_paths_allowed": False,
        "caller_supplied_raw_payloads_allowed": False,
        "caller_supplied_inline_authority_allowed": False,
        "caller_environment_injection_allowed": False,
        "artifacts": {
            name: {
                "locator": str(path),
                "artifact_digest": _dummy_digest(character),
            }
            for name, path in provisioner.CONTROL_PUBLISHER_ARTIFACTS.items()
        },
        "broker_runtime_ref": runtime,
        "control_runtime_ref": control_runtime,
        "bootstrap_provenance_ref": {
            "locator": str(
                provisioner.INITIAL_BOOTSTRAP_PROVENANCE_BINDING
            ),
            "binding_id": "binding.bootstrap.test",
            "binding_artifact_digest": _dummy_digest(character),
            "binding_digest": _dummy_digest(character),
            "authorization_id": "bootstrap.authorization.test",
            "plan_id": "bootstrap.plan.test",
            "chain_artifact_digests": {
                name: _dummy_digest(character)
                for name in ("authorization", "plan", "consumption", "receipt")
            },
        },
        "formal_authority": "none",
        "positive_assurance_allowed": False,
    }
    value["binding_digest"] = provisioner.sealed_digest(
        value, "binding_digest"
    )
    return value


class KeyFixture:
    def __init__(self, root: Path) -> None:
        self.uid = os.geteuid()
        self.u10_root = root / "u10"
        self.paths = provisioner.KeyPaths(
            u10_root=self.u10_root,
            authorization_root=self.u10_root / "authorizations" / "key",
            ledger_root=self.u10_root / "activations" / "key-transitions",
            key_root=self.u10_root / "keys",
            generation_root=self.u10_root / "keys" / "generations",
            revocation_root=self.u10_root / "keys" / "revocations",
            selector_history_root=(
                self.u10_root / "keys" / "selector-history" / "sha256"
            ),
            selector_path=self.u10_root / "keys" / "current.json",
            trust_store_lock_path=self.u10_root / "trust-store.lock",
            lock_path=self.u10_root / "keys" / "key-transition.lock",
        )
        for directory in (
            self.u10_root,
            self.u10_root / "authorizations",
            self.paths.authorization_root,
            self.u10_root / "activations",
            self.paths.ledger_root,
            self.paths.key_root,
            self.paths.generation_root,
            self.paths.revocation_root,
            self.paths.key_root / "selector-history",
            self.paths.selector_history_root,
        ):
            directory.mkdir(exist_ok=True)
            directory.chmod(0o700)
        for lock_path in (
            self.paths.trust_store_lock_path,
            self.paths.lock_path,
        ):
            lock_path.write_bytes(b"")
            lock_path.chmod(0o600)

    def authorize(
        self,
        authorization_id: str,
        operation: str,
        key_id: str,
        expected_current_key_id: str | None,
    ) -> dict:
        current = provisioner._load_current_selector_v2(
            self.paths, uid=self.uid
        )
        prior_selector_ref = None if current is None else current[2]
        transition_mode = {
            "rotate": "rotate_active_key",
            "revoke": "revoke_active_key",
        }.get(operation)
        if operation == "generate":
            transition_mode = (
                "initialize_empty_store"
                if prior_selector_ref is None
                else "generate_from_no_active_key"
            )
        value = {
            "schema_version": provisioner.KEY_AUTH_SCHEMA,
            "authorization_id": authorization_id,
            "authorization_version": "2.0.0",
            "record_kind": "signing_key_operation_authorization",
            "key_operation": operation,
            "transition_mode": transition_mode,
            "key_id": key_id,
            "key_entity_ref": f"署名鍵 {key_id}・{key_id}",
            "expected_current_key_id": expected_current_key_id,
            "prior_selector_ref": prior_selector_ref,
            "target_generation_path": str(
                self.paths.generation_root / key_id
            ),
            "target_public_metadata_path": str(
                self.paths.generation_root / key_id / "public-metadata.json"
            ),
            "target_private_key_path": str(
                self.paths.generation_root / key_id / "private.ed25519"
            ),
            "authorized_algorithm": "Ed25519",
            "authorized_operation": "apply_exact_key_lifecycle_transition_v2",
            "human_decision": "accept",
            "decision_owner": "human",
            "recorded_at": _timestamp(timedelta(minutes=-2)),
            "not_before": _timestamp(timedelta(minutes=-1)),
            "expires_at": _timestamp(timedelta(hours=1)),
            "u4_principal_authenticity": "unresolved",
            "authority_scope": "u10_signing_key_transition_only",
            "formal_authority": "human_key_transition_decision_only",
            "positive_assurance_allowed": False,
        }
        value["authorization_digest"] = provisioner.sealed_digest(
            value, "authorization_digest"
        )
        path = self.paths.authorization_root / f"{authorization_id}.json"
        path.write_bytes(provisioner.json_record_bytes(value))
        path.chmod(0o400)
        return value

    def execute(self, authorization_id: str, binding: dict) -> dict:
        return provisioner.execute_key_authorization(
            authorization_id,
            publisher_contract_binding=binding,
            paths=self.paths,
            required_uid=self.uid,
        )


class U10KeyProvisioningTests(unittest.TestCase):
    def test_generate_rotate_revoke_are_append_only_and_do_not_export_private(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = KeyFixture(Path(temporary).resolve())
            binding = _publisher_binding()
            first_key = str(uuid.uuid4())
            second_key = str(uuid.uuid4())
            fixture.authorize("key.generate.test", "generate", first_key, None)
            generated = fixture.execute("key.generate.test", binding)
            self.assertEqual(generated["key_state"], "active")
            private_path = fixture.paths.generation_root / first_key / "private.ed25519"
            metadata_path = fixture.paths.generation_root / first_key / "public-metadata.json"
            self.assertEqual(private_path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(metadata_path.stat().st_mode & 0o777, 0o444)
            self.assertEqual(private_path.stat().st_nlink, 1)
            private_raw = private_path.read_bytes()
            self.assertEqual(len(private_raw), 32)

            fixture.authorize(
                "key.rotate.test", "rotate", second_key, first_key
            )
            rotated = fixture.execute("key.rotate.test", binding)
            self.assertEqual(rotated["key_id"], second_key)
            fixture.authorize(
                "key.revoke.test", "revoke", second_key, second_key
            )
            revoked = fixture.execute("key.revoke.test", binding)
            self.assertEqual(revoked["key_state"], "revoked_no_active_key")
            selector = json.loads(fixture.paths.selector_path.read_bytes())
            self.assertEqual(selector["state"], "no_active_key")

            encoded_private = base64.b64encode(private_raw)
            for path in fixture.u10_root.rglob("*.json"):
                self.assertNotIn(encoded_private, path.read_bytes())

    def test_completed_replay_preserves_old_publisher_binding(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = KeyFixture(Path(temporary).resolve())
            key_id = str(uuid.uuid4())
            fixture.authorize("key.replay.test", "generate", key_id, None)
            first = fixture.execute("key.replay.test", _publisher_binding("0"))
            replay = fixture.execute("key.replay.test", _publisher_binding("1"))
            self.assertEqual(first, replay)
            self.assertEqual(
                replay["publisher_contract_binding"],
                _publisher_binding("0"),
            )

    def test_incomplete_recovery_rejects_changed_publisher_binding(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = KeyFixture(Path(temporary).resolve())
            key_id = str(uuid.uuid4())
            fixture.authorize("key.crash.test", "generate", key_id, None)
            original = provisioner._load_cryptography

            def fail_crypto():
                raise provisioner.U10ProvisioningError(
                    "test_crash_after_consumption", "expected"
                )

            provisioner._load_cryptography = fail_crypto
            try:
                with self.assertRaisesRegex(
                    provisioner.U10ProvisioningError,
                    "test_crash_after_consumption",
                ):
                    fixture.execute("key.crash.test", _publisher_binding("0"))
            finally:
                provisioner._load_cryptography = original
            with self.assertRaisesRegex(
                provisioner.U10ProvisioningError,
                "u10_key_recovery_publisher_contract_changed",
            ):
                fixture.execute("key.crash.test", _publisher_binding("1"))

    def test_private_material_replacement_is_detected_on_replay(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = KeyFixture(Path(temporary).resolve())
            key_id = str(uuid.uuid4())
            fixture.authorize("key.tamper.test", "generate", key_id, None)
            fixture.execute("key.tamper.test", _publisher_binding())
            private_path = fixture.paths.generation_root / key_id / "private.ed25519"
            private_path.write_bytes(b"x" * 32)
            private_path.chmod(0o600)
            with self.assertRaisesRegex(
                provisioner.U10ProvisioningError,
                "u10_private_public_key_mismatch",
            ):
                fixture.execute("key.tamper.test", _publisher_binding())

    def test_key_api_and_standalone_cli_reject_unbound_use(self) -> None:
        with self.assertRaises(TypeError):
            provisioner.execute_key_authorization("key.missing.binding")
        with self.assertRaisesRegex(
            provisioner.U10ProvisioningError,
            "u10_provisioner_usage_invalid",
        ):
            provisioner.main(["key", "key.missing.binding"])

    def test_produced_key_records_match_published_schemas(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = KeyFixture(Path(temporary).resolve())
            binding = _publisher_binding()
            key_id = str(uuid.uuid4())
            authorization_id = "key.schema.test"
            authorization = fixture.authorize(
                authorization_id, "generate", key_id, None
            )
            receipt = fixture.execute(authorization_id, binding)
            consumption = json.loads(
                (
                    fixture.paths.ledger_root
                    / f"{authorization_id}.consumption.json"
                ).read_bytes()
            )
            metadata = json.loads(
                (
                    fixture.paths.generation_root
                    / key_id
                    / "public-metadata.json"
                ).read_bytes()
            )
            selector = json.loads(fixture.paths.selector_path.read_bytes())
            revocation_authorization_id = "key.schema.revoke"
            revocation_authorization = fixture.authorize(
                revocation_authorization_id, "revoke", key_id, key_id
            )
            revocation_receipt = fixture.execute(
                revocation_authorization_id, binding
            )
            revocation_consumption = json.loads(
                (
                    fixture.paths.ledger_root
                    / f"{revocation_authorization_id}.consumption.json"
                ).read_bytes()
            )
            revocation = json.loads(
                (
                    fixture.paths.revocation_root
                    / key_id
                    / f"{revocation_authorization_id}.json"
                ).read_bytes()
            )
            revoked_selector = json.loads(
                fixture.paths.selector_path.read_bytes()
            )

            temporary_prefix = str(fixture.u10_root)
            production_prefix = str(provisioner.U10_ROOT)

            def production_paths(value):
                if isinstance(value, dict):
                    return {
                        key: production_paths(item)
                        for key, item in value.items()
                    }
                if isinstance(value, list):
                    return [production_paths(item) for item in value]
                if isinstance(value, str) and value.startswith(
                    temporary_prefix
                ):
                    return production_prefix + value[len(temporary_prefix) :]
                return value

            publisher_schema = json.loads(
                (
                    SCHEMA_ROOT
                    / "u10-control-publisher-contract-binding-v1.schema.json"
                ).read_text(encoding="utf-8")
            )
            registry = Registry().with_resource(
                publisher_schema["$id"],
                Resource.from_contents(publisher_schema),
            )
            records = (
                (
                    "u10-key-operation-authorization-v2.schema.json",
                    production_paths(authorization),
                ),
                (
                    "u10-key-operation-authorization-consumption-v2.schema.json",
                    production_paths(consumption),
                ),
                (
                    "u10-signing-key-metadata-v2.schema.json",
                    production_paths(metadata),
                ),
                (
                    "u10-signing-key-selector-v2.schema.json",
                    production_paths(selector),
                ),
                (
                    "u10-key-operation-receipt-v2.schema.json",
                    production_paths(receipt),
                ),
                (
                    "u10-key-operation-authorization-v2.schema.json",
                    production_paths(revocation_authorization),
                ),
                (
                    "u10-key-operation-authorization-consumption-v2.schema.json",
                    production_paths(revocation_consumption),
                ),
                (
                    "u10-signing-key-revocation-v2.schema.json",
                    production_paths(revocation),
                ),
                (
                    "u10-signing-key-selector-v2.schema.json",
                    production_paths(revoked_selector),
                ),
                (
                    "u10-key-operation-receipt-v2.schema.json",
                    production_paths(revocation_receipt),
                ),
            )
            for schema_name, record in records:
                schema = json.loads(
                    (SCHEMA_ROOT / schema_name).read_text(encoding="utf-8")
                )
                errors = list(
                    Draft202012Validator(
                        schema,
                        registry=registry,
                        format_checker=Draft202012Validator.FORMAT_CHECKER,
                    ).iter_errors(record)
                )
                self.assertEqual(errors, [], (schema_name, errors))


class U10RuntimeObservationTests(unittest.TestCase):
    def _capsule(self, root: Path) -> tuple[bytes, dict, Path]:
        interpreter = root / "runtime" / "python"
        interpreter.parent.mkdir()
        interpreter.write_bytes(b"qualified-interpreter-fixture")
        interpreter.chmod(0o755)
        members = {
            "bootstrap/u10_initial_trust_provisioner.py": (
                SCRIPT_ROOT / "u10_initial_trust_provisioner.py"
            ).read_bytes(),
            "bootstrap/prepare_u10_bootstrap_runtime_manifest.py": b"broker",
            "bootstrap/prepare_u10_control_runtime_manifest.py": b"control",
        }
        for name, raw in members.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
            path.chmod(0o600)
        entries = [
            {
                "role": role,
                "member": member,
                "artifact_digest": provisioner.digest_bytes(members[member]),
            }
            for role, member in (
                (
                    "initial_capsule_provisioner",
                    "bootstrap/u10_initial_trust_provisioner.py",
                ),
                (
                    "broker_runtime_manifest_generator",
                    "bootstrap/prepare_u10_bootstrap_runtime_manifest.py",
                ),
                (
                    "control_runtime_manifest_generator",
                    "bootstrap/prepare_u10_control_runtime_manifest.py",
                ),
            )
        ]
        kit = {
            "status": "closed",
            "entry_count": len(entries),
            "entries": entries,
            "denominator_digest": provisioner.digest_bytes(
                provisioner.canonical_json_bytes({"entries": entries})
            ),
        }
        request_id = "runtime.observation.test"
        request = {
            "schema_version": provisioner.RUNTIME_OBSERVATION_REQUEST_SCHEMA,
            "request_id": request_id,
            "request_version": "1.0.0",
            "record_kind": "bootstrap_runtime_root_observation_request",
            "runtime_bindings": {
                "broker": {
                    "effective_interpreter_locator": str(interpreter),
                    "effective_interpreter_artifact_digest": (
                        provisioner.digest_bytes(interpreter.read_bytes())
                    ),
                    "python_flags": ["-I", "-S", "-B"],
                    "manifest_generator_role": (
                        "broker_runtime_manifest_generator"
                    ),
                },
                "control": {
                    "effective_interpreter_locator": str(interpreter),
                    "effective_interpreter_artifact_digest": (
                        provisioner.digest_bytes(interpreter.read_bytes())
                    ),
                    "python_flags": ["-I", "-B"],
                    "manifest_generator_role": (
                        "control_runtime_manifest_generator"
                    ),
                },
            },
            "bootstrap_kit_denominator": kit,
            "authorized_operation": "observe_exact_root_runtimes_only",
            "human_decision": "accept",
            "decision_owner": "human",
            "recorded_at": _timestamp(timedelta(minutes=-2)),
            "not_before": _timestamp(timedelta(minutes=-1)),
            "expires_at": _timestamp(timedelta(hours=1)),
            "authority_scope": "root_runtime_observation_no_target_publication",
            "formal_authority": "human_root_observation_decision_only",
            "positive_assurance_allowed": False,
        }
        request["request_digest"] = provisioner.sealed_digest(
            request, "request_digest"
        )
        request_path = root / "observation-request.json"
        request_path.write_bytes(provisioner.json_record_bytes(request))
        request_path.chmod(0o600)
        capsule, _directive = capsule_builder.build_observation_capsule(
            observation_request_path=request_path,
            member_root=root,
        )
        return capsule, request, interpreter

    @staticmethod
    def _manifest_builder(**kwargs) -> dict:
        value = {
            "schema_version": "test-only-runtime-manifest/v1",
            "runtime_name": kwargs["runtime_name"],
        }
        value["manifest_digest"] = provisioner.sealed_digest(
            value, "manifest_digest"
        )
        return value

    def test_observation_initializes_only_preboot_ledger_and_replays(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            capsule, request, _interpreter = self._capsule(root)
            ledger = root / "preboot-ledger"
            receipt = provisioner.execute_runtime_observation_from_capsule(
                capsule,
                request["request_id"],
                ledger_root=ledger,
                runtime_manifest_builder=self._manifest_builder,
                required_uid=os.geteuid(),
            )
            self.assertEqual(
                receipt["preboot_ledger_initialization"]["root_state"],
                "created_by_observation_loader",
            )
            self.assertFalse(receipt["target_publication_occurred"])
            self.assertFalse(receipt["key_generation_occurred"])
            self.assertEqual(ledger.stat().st_mode & 0o777, 0o700)
            self.assertEqual(
                (ledger / "runtime-observation.lock").stat().st_mode & 0o777,
                0o600,
            )
            replay = provisioner.execute_runtime_observation_from_capsule(
                capsule,
                request["request_id"],
                ledger_root=ledger,
                runtime_manifest_builder=self._manifest_builder,
                required_uid=os.geteuid(),
            )
            self.assertEqual(replay, receipt)

    def test_observation_rejects_interpreter_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            capsule, request, interpreter = self._capsule(root)
            interpreter.write_bytes(b"replaced-interpreter")
            with self.assertRaisesRegex(
                provisioner.U10ProvisioningError,
                "u10_runtime_observation_interpreter_digest_mismatch",
            ):
                provisioner.execute_runtime_observation_from_capsule(
                    capsule,
                    request["request_id"],
                    ledger_root=root / "preboot-ledger",
                    runtime_manifest_builder=self._manifest_builder,
                    required_uid=os.geteuid(),
                )

    def test_capsule_builder_rejects_symlink_member(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            target = root / "target"
            target.write_bytes(b"target")
            link = root / "link"
            link.symlink_to(target)
            with self.assertRaisesRegex(
                capsule_builder.CapsuleBuildError,
                "member is not one regular file",
            ):
                capsule_builder._read_once(link, root=root)

    def test_digest_aligned_capsule_with_invalid_human_chain_never_executes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            capsule_raw, request, _interpreter = self._capsule(root)
            capsule = json.loads(capsule_raw)
            record_name = (
                "records/bootstrap-runtime-observation-requests/"
                f"{request['request_id']}.json"
            )
            for member in capsule["members"]:
                if member["name"] != record_name:
                    continue
                altered = json.loads(base64.b64decode(member["content"]))
                altered["human_decision"] = "reject"
                raw = provisioner.json_record_bytes(altered)
                member["content"] = base64.b64encode(raw).decode("ascii")
                member["artifact_digest"] = provisioner.digest_bytes(raw)
            malicious_raw = provisioner.json_record_bytes(capsule)
            capsule_path = root / "malicious-capsule.json"
            capsule_path.write_bytes(malicious_raw)
            provisioner_member = next(
                member
                for member in capsule["members"]
                if member["name"]
                == "bootstrap/u10_initial_trust_provisioner.py"
            )
            completed = subprocess.run(
                [
                    "/usr/bin/python3",
                    "-I",
                    "-S",
                    "-B",
                    "-c",
                    capsule_builder.LOADER,
                    str(capsule_path),
                    provisioner.digest_bytes(malicious_raw)["value"],
                    provisioner_member["artifact_digest"]["value"],
                    request["request_id"],
                ],
                check=False,
                capture_output=True,
                text=True,
                env={"PATH": "", "LC_ALL": "C"},
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("runtime observation request chain invalid", completed.stderr)


class U10BootstrapDenominatorContractTests(unittest.TestCase):
    def test_plan_schema_requires_fixed_control_and_runtime_generator_roles(self) -> None:
        schema = json.loads(
            (
                SCHEMA_ROOT / "u10-bootstrap-provisioning-plan-v1.schema.json"
            ).read_text(encoding="utf-8")
        )
        requirements = schema["$defs"]["target_denominator"]["properties"][
            "entries"
        ]["allOf"]
        role_paths = {
            clause["contains"]["properties"]["role"]["const"]: clause[
                "contains"
            ]["properties"]["relative_path"]["const"]
            for clause in requirements
        }
        self.assertEqual(len(role_paths), 45)
        self.assertEqual(
            role_paths["root_control_dispatcher"],
            "bootstrap/u10_root_control_dispatcher.py",
        )
        self.assertEqual(
            role_paths["control_runtime_manifest_generator"],
            "bootstrap/prepare_u10_control_runtime_manifest.py",
        )
        self.assertEqual(
            role_paths["broker_runtime_manifest_generator"],
            "bootstrap/prepare_u10_bootstrap_runtime_manifest.py",
        )
        self.assertEqual(
            role_paths["snapshot_store_producer"],
            "bootstrap/u10_snapshot_store_production.py",
        )
        self.assertEqual(
            role_paths["store_activation_basis_directory"],
            "store-activation-bases",
        )
        self.assertEqual(
            role_paths["initial_fixed_entrypoint"],
            "bootstrap/u10_initial_trust_entrypoint.sh",
        )

    def test_two_stage_publication_is_atomic_closed_and_provenance_resolves(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            observation_helper = U10RuntimeObservationTests()
            observation_capsule, observation_request, interpreter = (
                observation_helper._capsule(root)
            )
            ledger = root / "preboot-ledger"
            observation_receipt = (
                provisioner.execute_runtime_observation_from_capsule(
                    observation_capsule,
                    observation_request["request_id"],
                    ledger_root=ledger,
                    runtime_manifest_builder=(
                        observation_helper._manifest_builder
                    ),
                    required_uid=os.geteuid(),
                )
            )
            broker_manifest_raw = (
                ledger
                / f"{observation_request['request_id']}.broker-runtime-manifest.json"
            ).read_bytes()
            control_manifest_raw = (
                ledger
                / f"{observation_request['request_id']}.control-runtime-manifest.json"
            ).read_bytes()
            observation_receipt_raw = provisioner.json_record_bytes(
                observation_receipt
            )
            evidence = {
                "records/root-observation/receipt.json": observation_receipt_raw,
                "records/root-observation/broker-manifest.json": (
                    broker_manifest_raw
                ),
                "records/root-observation/control-manifest.json": (
                    control_manifest_raw
                ),
            }
            for member, raw in evidence.items():
                path = root / member
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
                path.chmod(0o600)

            for name in (
                "u10_root_broker_entrypoint.sh",
                "u10_root_broker_outer_launcher.py",
                "u10_root_candidate_installer_entrypoint.sh",
                "prepare_u10_root_candidate.py",
                "u10_root_control_entrypoint.sh",
                "u10_root_control_outer_launcher.py",
                "u10_root_control_dispatcher.py",
            ):
                path = root / "bootstrap" / name
                path.write_bytes(f"test payload: {name}\n".encode())
                path.chmod(0o600)
            for name in (
                "u10_initial_trust_entrypoint.sh",
                "u10_snapshot_store_production.py",
            ):
                source = SCRIPT_ROOT / name
                target = root / "bootstrap" / name
                target.write_bytes(source.read_bytes())
                target.chmod(0o600)

            schema = json.loads(
                (
                    SCHEMA_ROOT
                    / "u10-bootstrap-provisioning-plan-v1.schema.json"
                ).read_text(encoding="utf-8")
            )
            requirements = schema["$defs"]["target_denominator"][
                "properties"
            ]["entries"]["allOf"]
            contracts = [
                {
                    name: definition["const"]
                    for name, definition in clause["contains"][
                        "properties"
                    ].items()
                    if "const" in definition
                }
                for clause in requirements
            ]
            authorization_id = "bootstrap.publication.test"
            plan_id = "bootstrap.plan.test"
            broker_manifest = json.loads(broker_manifest_raw)
            control_manifest = json.loads(control_manifest_raw)
            plan: dict = {
                "schema_version": provisioner.BOOTSTRAP_PLAN_SCHEMA,
                "plan_id": plan_id,
                "plan_version": "1.0.0",
                "record_kind": "initial_u10_root_provisioning_plan",
                "target_root": str(provisioner.U10_ROOT),
                "target_root_mode": 0o755,
                "expected_authorization_id": authorization_id,
                "preboot_ledger_binding": {
                    "root": str(provisioner.PREBOOT_LEDGER_ROOT),
                    "policy": (
                        "append_only_exact_id_resolution_outside_target/v1"
                    ),
                    "authorization_record": (
                        f"{authorization_id}.authorization.json"
                    ),
                    "plan_record": f"{authorization_id}.plan.json",
                    "consumption_record": (
                        f"{authorization_id}.consumption.json"
                    ),
                    "receipt_record": f"{authorization_id}.receipt.json",
                },
                "runtime_bindings": {
                    "broker": {
                        "effective_interpreter_locator": str(interpreter),
                        "effective_interpreter_artifact_digest": (
                            provisioner.digest_bytes(interpreter.read_bytes())
                        ),
                        "python_flags": ["-I", "-S", "-B"],
                        "effective_path_target": str(
                            provisioner.BROKER_EFFECTIVE_PATH
                        ),
                        "manifest_target": str(
                            provisioner.BROKER_RUNTIME_MANIFEST
                        ),
                        "manifest_generator_role": (
                            "broker_runtime_manifest_generator"
                        ),
                        "expected_manifest_digest": broker_manifest[
                            "manifest_digest"
                        ],
                    },
                    "control": {
                        "effective_interpreter_locator": str(interpreter),
                        "effective_interpreter_artifact_digest": (
                            provisioner.digest_bytes(interpreter.read_bytes())
                        ),
                        "python_flags": ["-I", "-B"],
                        "effective_path_target": str(
                            provisioner.CONTROL_EFFECTIVE_PATH
                        ),
                        "manifest_target": str(
                            provisioner.CONTROL_RUNTIME_MANIFEST
                        ),
                        "manifest_generator_role": (
                            "control_runtime_manifest_generator"
                        ),
                        "expected_manifest_digest": control_manifest[
                            "manifest_digest"
                        ],
                    },
                },
                "root_observation_ref": {
                    "request_id": observation_request["request_id"],
                    "receipt_id": observation_receipt["receipt_id"],
                    "receipt_member": "records/root-observation/receipt.json",
                    "receipt_artifact_digest": provisioner.digest_bytes(
                        observation_receipt_raw
                    ),
                    "receipt_digest": observation_receipt["receipt_digest"],
                    "broker_manifest_member": (
                        "records/root-observation/broker-manifest.json"
                    ),
                    "broker_manifest_artifact_digest": (
                        provisioner.digest_bytes(broker_manifest_raw)
                    ),
                    "broker_manifest_digest": broker_manifest[
                        "manifest_digest"
                    ],
                    "control_manifest_member": (
                        "records/root-observation/control-manifest.json"
                    ),
                    "control_manifest_artifact_digest": (
                        provisioner.digest_bytes(control_manifest_raw)
                    ),
                    "control_manifest_digest": control_manifest[
                        "manifest_digest"
                    ],
                },
                "trust_boundary": {
                    "covered": (
                        "exact_capsule_bytes_root_observation_and_atomic_"
                        "initial_publication"
                    ),
                    "not_claimed": (
                        "root_os_or_hardware_compromise_resistance"
                    ),
                },
                "formal_authority": "none",
                "positive_assurance_allowed": False,
            }
            kit_entries = []
            for role, member in (
                (
                    "initial_capsule_provisioner",
                    "bootstrap/u10_initial_trust_provisioner.py",
                ),
                (
                    "broker_runtime_manifest_generator",
                    "bootstrap/prepare_u10_bootstrap_runtime_manifest.py",
                ),
                (
                    "control_runtime_manifest_generator",
                    "bootstrap/prepare_u10_control_runtime_manifest.py",
                ),
                (
                    "initial_fixed_entrypoint",
                    "bootstrap/u10_initial_trust_entrypoint.sh",
                ),
            ):
                raw = (root / member).read_bytes()
                kit_entries.append(
                    {
                        "role": role,
                        "member": member,
                        "artifact_digest": provisioner.digest_bytes(raw),
                    }
                )
            plan["bootstrap_kit_denominator"] = {
                "status": "closed",
                "entry_count": len(kit_entries),
                "entries": kit_entries,
                "denominator_digest": provisioner.digest_bytes(
                    provisioner.canonical_json_bytes(
                        {"entries": kit_entries}
                    )
                ),
            }
            binding_raw = provisioner.json_record_bytes(
                provisioner.build_bootstrap_provenance_binding(plan)
            )
            generated = {
                "generated_broker_effective_path": (
                    f"{interpreter}\n".encode()
                ),
                "generated_broker_runtime_manifest": broker_manifest_raw,
                "generated_control_effective_path": (
                    f"{interpreter}\n".encode()
                ),
                "generated_control_runtime_manifest": control_manifest_raw,
                "generated_bootstrap_provenance_binding": binding_raw,
                "generated_empty_lock_file": b"",
            }
            entries = []
            for contract in contracts:
                relative_path = contract["relative_path"]
                kind = contract["kind"]
                role = contract["role"]
                mode = contract.get(
                    "mode",
                    0o755 if kind == "directory" else (
                        0o555 if relative_path.endswith(".sh") else 0o400
                    ),
                )
                entry = {
                    "relative_path": relative_path,
                    "kind": kind,
                    "mode": mode,
                    "uid": 0,
                    "gid": 0,
                    "role": role,
                }
                if kind == "file":
                    source = contract.get("source", relative_path)
                    raw = generated.get(source)
                    if raw is None:
                        raw = (root / source).read_bytes()
                    entry.update(
                        {
                            "source": source,
                            "artifact_digest": provisioner.digest_bytes(raw),
                        }
                    )
                entries.append(entry)
            entries.sort(key=lambda item: item["relative_path"])
            plan["target_denominator"] = {
                "status": "closed",
                "entry_count": len(entries),
                "entries": entries,
                "tree_digest": provisioner.digest_bytes(
                    provisioner.canonical_json_bytes({"entries": entries})
                ),
            }
            plan["plan_digest"] = provisioner.sealed_digest(
                plan, "plan_digest"
            )
            plan_path = root / "bootstrap-plan.json"
            plan_raw = provisioner.json_record_bytes(plan)
            plan_path.write_bytes(plan_raw)
            plan_path.chmod(0o600)
            authorization = {
                "schema_version": provisioner.BOOTSTRAP_AUTH_SCHEMA,
                "authorization_id": authorization_id,
                "authorization_version": "1.0.0",
                "record_kind": "bootstrap_provisioning_authorization",
                "plan_ref": {
                    "plan_id": plan_id,
                    "plan_version": "1.0.0",
                    "record_member": f"records/bootstrap-plans/{plan_id}.json",
                    "artifact_digest": provisioner.digest_bytes(plan_raw),
                    "semantic_digest": plan["plan_digest"],
                },
                "target_root": str(provisioner.U10_ROOT),
                "authorized_operation": "publish_exact_initial_u10_root",
                "human_decision": "accept",
                "decision_owner": "human",
                "recorded_at": _timestamp(timedelta(minutes=-2)),
                "not_before": _timestamp(timedelta(minutes=-1)),
                "expires_at": _timestamp(timedelta(hours=1)),
                "authority_scope": "initial_u10_root_publication_only",
                "u4_principal_authenticity": "unresolved",
                "formal_authority": (
                    "human_bootstrap_publication_decision_only"
                ),
                "positive_assurance_allowed": False,
            }
            authorization["authorization_digest"] = provisioner.sealed_digest(
                authorization, "authorization_digest"
            )
            authorization_path = root / "bootstrap-authorization.json"
            authorization_path.write_bytes(
                provisioner.json_record_bytes(authorization)
            )
            authorization_path.chmod(0o600)
            capsule_raw, _directive = capsule_builder.build_capsule(
                authorization_path=authorization_path,
                plan_path=plan_path,
                member_root=root,
            )
            target = root / "published-u10"
            receipt = provisioner.execute_initial_bootstrap_from_capsule(
                capsule_raw,
                authorization_id,
                paths=provisioner.BootstrapPaths(
                    target_root=target, ledger_root=ledger
                ),
                runtime_manifest_builder=(
                    observation_helper._manifest_builder
                ),
                required_uid=os.geteuid(),
            )
            self.assertTrue(receipt["publication_occurred"])
            self.assertEqual(receipt["key_state"], "not_generated")
            self.assertEqual(
                {
                    path.relative_to(target).as_posix()
                    for path in target.rglob("*")
                },
                {entry["relative_path"] for entry in entries},
            )
            chain = provisioner.validate_bootstrap_provenance_chain(
                binding_path=(
                    target
                    / "bootstrap"
                    / "initial-bootstrap-provenance-binding.json"
                ),
                target_root=target,
                ledger_root=ledger,
                required_uid=os.geteuid(),
            )
            self.assertEqual(
                chain["authorization"]["authorization_id"], authorization_id
            )
            replay = provisioner.execute_initial_bootstrap_from_capsule(
                capsule_raw,
                authorization_id,
                paths=provisioner.BootstrapPaths(
                    target_root=target, ledger_root=ledger
                ),
                runtime_manifest_builder=(
                    observation_helper._manifest_builder
                ),
                required_uid=os.geteuid(),
            )
            self.assertEqual(replay, receipt)


if __name__ == "__main__":
    unittest.main()
