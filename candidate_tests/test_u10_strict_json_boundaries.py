from __future__ import annotations

import base64
import hashlib
from importlib.machinery import ModuleSpec
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock

from semantic_guard_u10_broker import protected_io
from semantic_guard_u10_broker import core
from semantic_guard_u10_broker import supervisor
from semantic_guard_vnext import qualified_environment


SCRIPT_ROOT = Path(__file__).parent / "fixtures" / "scripts"


def _load(name: str, filename: str):
    specification = importlib.util.spec_from_file_location(
        name, SCRIPT_ROOT / filename
    )
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    sys.modules[name] = module
    try:
        specification.loader.exec_module(module)
    finally:
        sys.modules.pop(name, None)
    return module


provisioner = _load(
    "u10_strict_json_provisioner_test",
    "u10_initial_trust_provisioner.py",
)
capsule_builder = _load(
    "u10_strict_json_capsule_builder_test",
    "prepare_u10_initial_bootstrap_capsule.py",
)
bootstrap_manifest = _load(
    "u10_strict_json_bootstrap_manifest_test",
    "prepare_u10_bootstrap_runtime_manifest.py",
)
control_manifest = _load(
    "u10_strict_json_control_manifest_test",
    "prepare_u10_control_runtime_manifest.py",
)
root_bootstrap = _load(
    "u10_strict_json_root_bootstrap_test",
    "u10_root_broker_bootstrap.py",
)
snapshot_worker = _load(
    "u10_strict_json_snapshot_worker_test",
    "u10_snapshot_worker.py",
)
control_outer = _load(
    "u10_strict_json_control_outer_test",
    "u10_root_control_outer_launcher.py",
)
control_dispatcher = _load(
    "u10_strict_json_control_dispatcher_test",
    "u10_root_control_dispatcher.py",
)
snapshot_projector = _load(
    "u10_strict_json_snapshot_projector_test",
    "u10_snapshot_environment_projector.py",
)
snapshot_store_producer = _load(
    "u10_strict_json_snapshot_store_producer_test",
    "u10_snapshot_store_production.py",
)
broker_outer = _load(
    "u10_strict_json_broker_outer_test",
    "u10_root_broker_outer_launcher.py",
)


STRICT_DECODERS = {
    "protected_io": protected_io.strict_json_loads,
    "initial_trust_provisioner": provisioner.strict_json_loads,
    "initial_bootstrap_capsule": capsule_builder.strict_json_loads,
    "bootstrap_runtime_manifest": bootstrap_manifest.strict_json_loads,
    "control_runtime_manifest": control_manifest.strict_json_loads,
    "root_broker_bootstrap": root_bootstrap.strict_json_loads,
    "snapshot_worker": snapshot_worker.strict_json_loads,
    "control_outer": control_outer.strict_json_loads,
    "snapshot_projector": snapshot_projector.strict_json_loads,
    "snapshot_store_producer": snapshot_store_producer.strict_json_loads,
    "broker_outer": broker_outer.strict_json_loads,
    "qualified_environment": qualified_environment.strict_json_loads,
}


class U10StrictJSONBoundaryTests(unittest.TestCase):
    def test_all_boundary_decoders_accept_one_unambiguous_finite_value(self) -> None:
        raw = b'{"items":[1,2.5,{"enabled":false}],"name":"u10"}'
        expected = {
            "items": [1, 2.5, {"enabled": False}],
            "name": "u10",
        }
        for name, decoder in STRICT_DECODERS.items():
            with self.subTest(boundary=name):
                self.assertEqual(decoder(raw), expected)

    def test_all_boundary_decoders_reject_nested_duplicate_keys(self) -> None:
        raw = b'{"outer":{"same":1,"same":2}}'
        for name, decoder in STRICT_DECODERS.items():
            with self.subTest(boundary=name):
                with self.assertRaises(json.JSONDecodeError):
                    decoder(raw)

    def test_store_route_wrappers_reject_ambiguous_json(self) -> None:
        malformed_values = (
            b'{"outer":{"same":1,"same":2}}',
            b'{"value":NaN}',
        )
        for raw in malformed_values:
            with self.subTest(boundary="broker-core", raw=raw):
                with self.assertRaises(protected_io.BrokerBoundaryError):
                    core._load_json_bytes(raw, "u10_strict_json_test")
            with self.subTest(boundary="snapshot-store-producer", raw=raw):
                with self.assertRaises(
                    snapshot_store_producer.U10SnapshotProductionError
                ):
                    snapshot_store_producer._json(
                        raw, code="u10_strict_json_test"
                    )
            with self.subTest(boundary="broker-outer", raw=raw):
                with self.assertRaises(broker_outer.OuterLaunchError):
                    broker_outer._json(raw, "u10 strict json test")

    def test_store_route_encoders_reject_non_finite_numbers(self) -> None:
        value = {"nested": {"value": float("nan")}}
        with self.assertRaises(protected_io.BrokerBoundaryError):
            core.canonical_json_bytes(value)
        with self.assertRaises(
            snapshot_store_producer.U10SnapshotProductionError
        ):
            snapshot_store_producer.canonical_json_bytes(value)
        with self.assertRaises(
            snapshot_store_producer.U10SnapshotProductionError
        ):
            snapshot_store_producer.json_record_bytes(value)
        with self.assertRaises(broker_outer.OuterLaunchError):
            broker_outer._canonical(value)

    def test_all_boundary_decoders_reject_nonfinite_numbers(self) -> None:
        payloads = (
            b'{"value":NaN}',
            b'{"value":Infinity}',
            b'{"value":-Infinity}',
            b'{"value":1e400}',
            b'{"value":1e999}',
        )
        for name, decoder in STRICT_DECODERS.items():
            for raw in payloads:
                with self.subTest(boundary=name, raw=raw):
                    with self.assertRaises(json.JSONDecodeError):
                        decoder(raw)

    def test_canonical_digest_bytes_are_stable_for_finite_values(self) -> None:
        value = {"z": "日本語", "a": [1, 2]}
        expected = b'{"a":[1,2],"z":"\xe6\x97\xa5\xe6\x9c\xac\xe8\xaa\x9e"}'
        serializers = {
            "protected_io": protected_io.canonical_json_bytes,
            "initial_trust_provisioner": provisioner.canonical_json_bytes,
            "bootstrap_runtime_manifest": bootstrap_manifest._canonical,
            "control_runtime_manifest": control_manifest._canonical,
            "root_broker_bootstrap": root_bootstrap._canonical,
            "control_outer": control_outer._canonical,
        }
        for name, serializer in serializers.items():
            with self.subTest(boundary=name):
                self.assertEqual(serializer(value), expected)

    def test_all_canonical_serializers_reject_nonfinite_values(self) -> None:
        serializers = {
            "protected_io": protected_io.canonical_json_bytes,
            "initial_trust_provisioner": provisioner.canonical_json_bytes,
            "bootstrap_runtime_manifest": bootstrap_manifest._canonical,
            "control_runtime_manifest": control_manifest._canonical,
            "root_broker_bootstrap": root_bootstrap._canonical,
            "control_outer": control_outer._canonical,
            "qualified_environment_artifact": (
                qualified_environment.artifact_bytes
            ),
        }
        for name, serializer in serializers.items():
            for value in (math.nan, math.inf, -math.inf):
                with self.subTest(boundary=name, value=value):
                    with self.assertRaises(ValueError):
                        serializer({"value": value})

    def test_provisioner_rejects_strict_json_before_capsule_contract(self) -> None:
        raw = b'{"schema_version":"wrong","nested":{"x":1,"x":2}}'
        with self.assertRaises(provisioner.U10ProvisioningError) as raised:
            provisioner._decode_capsule(raw)
        self.assertEqual(raised.exception.code, "u10_capsule_unreadable")

    def test_capsule_builder_rejects_strict_json_before_projection(self) -> None:
        for raw in (b'{"nested":{"x":1,"x":2}}', b'{"value":NaN}'):
            with self.subTest(raw=raw):
                with self.assertRaises(capsule_builder.CapsuleBuildError):
                    capsule_builder._load_json(raw, "adversarial")

    def test_runtime_probe_consumers_reject_ambiguous_output(self) -> None:
        completed = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout='{"probe_profile":"x","nested":{"x":1,"x":2}}',
            stderr="",
        )
        with mock.patch.object(
            bootstrap_manifest.subprocess, "run", return_value=completed
        ):
            with self.assertRaises(bootstrap_manifest.BootstrapManifestError):
                bootstrap_manifest._probe_interpreter(Path("/runtime/python"))
        with mock.patch.object(
            control_manifest.subprocess, "run", return_value=completed
        ):
            with self.assertRaises(control_manifest.ControlRuntimeManifestError):
                control_manifest._probe(Path("/runtime/python"))
        with mock.patch.object(
            control_outer.subprocess, "run", return_value=completed
        ):
            with self.assertRaises(control_outer.ControlOuterError):
                control_outer._probe_control_runtime(Path("/runtime/python"))

    def test_dispatcher_and_supervisor_use_strict_boundary_decoder(self) -> None:
        payloads = (
            b'{"outer":{"same":1,"same":2}}',
            b'{"value":NaN}',
            b'{"value":1e999}',
        )
        for raw in payloads:
            with self.subTest(boundary="dispatcher", raw=raw):
                with self.assertRaises(control_dispatcher.ControlDispatchError):
                    control_dispatcher._load_json(raw, "adversarial")
            with self.subTest(boundary="supervisor", raw=raw):
                with self.assertRaises(json.JSONDecodeError):
                    supervisor.strict_json_loads(raw)

    def test_worker_rejects_before_creating_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "worker-output.json"
            with self.assertRaises(ValueError):
                snapshot_worker._write_exclusive(output, {"value": math.nan})
            self.assertFalse(output.exists())

    def test_module_origin_validators_reject_nonexistent_file(self) -> None:
        validators = {
            "root_bootstrap": (
                root_bootstrap._validate_loaded_module_origin,
                root_bootstrap.BootstrapError,
            ),
            "snapshot_worker": (
                snapshot_worker._validate_module_origin,
                RuntimeError,
            ),
        }
        with tempfile.TemporaryDirectory() as temporary:
            snapshot = Path(temporary).resolve()
            module = types.ModuleType("adversarial_missing_origin")
            module.__file__ = str(snapshot / "missing.pyc")
            for name, (validator, error) in validators.items():
                with self.subTest(boundary=name):
                    with self.assertRaisesRegex(error, "existing file"):
                        validator(snapshot, module.__name__, module)

    def test_module_origin_validators_reject_unverified_originless_module(
        self,
    ) -> None:
        validators = (
            (
                root_bootstrap._validate_loaded_module_origin,
                root_bootstrap.BootstrapError,
            ),
            (snapshot_worker._validate_module_origin, RuntimeError),
        )
        with tempfile.TemporaryDirectory() as temporary:
            snapshot = Path(temporary).resolve()
            module = types.ModuleType("adversarial_originless")
            module.__spec__ = ModuleSpec(
                module.__name__, loader=None, origin="ordinary-loader"
            )
            for validator, error in validators:
                with self.assertRaisesRegex(error, "unverified"):
                    validator(snapshot, module.__name__, module)

    def test_module_origin_validators_allow_only_verified_intrinsic_origins(
        self,
    ) -> None:
        validators = (
            root_bootstrap._validate_loaded_module_origin,
            snapshot_worker._validate_module_origin,
        )
        with tempfile.TemporaryDirectory() as temporary:
            snapshot = Path(temporary).resolve()
            namespace = snapshot / "qualified-namespace"
            namespace.mkdir()
            modules = []
            for origin in ("built-in", "frozen"):
                module = types.ModuleType(f"qualified_{origin}")
                module.__spec__ = ModuleSpec(
                    module.__name__, loader=None, origin=origin
                )
                modules.append(module)
            namespace_module = types.ModuleType("qualified_namespace")
            namespace_specification = ModuleSpec(
                namespace_module.__name__, loader=None, is_package=True
            )
            namespace_specification.submodule_search_locations = [
                str(namespace)
            ]
            namespace_module.__spec__ = namespace_specification
            modules.append(namespace_module)
            for validator in validators:
                for module in modules:
                    with self.subTest(
                        validator=validator.__module__, module=module.__name__
                    ):
                        validator(snapshot, module.__name__, module)

    def test_missing_pyc_may_resolve_only_to_existing_snapshot_source(self) -> None:
        validators = (
            root_bootstrap._validate_loaded_module_origin,
            snapshot_worker._validate_module_origin,
        )
        with tempfile.TemporaryDirectory() as temporary:
            snapshot = Path(temporary).resolve()
            source = snapshot / "module.py"
            source.write_text("VALUE = 1\n", encoding="utf-8")
            module = types.ModuleType("qualified_source_fallback")
            module.__file__ = f"{source}c"
            for validator in validators:
                validator(snapshot, module.__name__, module)

    def test_embedded_loader_rejects_malformed_member_before_execution(self) -> None:
        malformed_members = (
            b'{"schema_version":"x","nested":{"x":1,"x":2}}',
            b'{"schema_version":"x","value":NaN}',
        )
        for malformed in malformed_members:
            with self.subTest(malformed=malformed):
                self._assert_embedded_loader_rejects_before_execution(malformed)

    def _assert_embedded_loader_rejects_before_execution(
        self, malformed_authorization: bytes
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            marker = root / "provisioner-executed"
            provisioner_raw = (
                "from pathlib import Path\n"
                f"Path({str(marker)!r}).write_text('executed')\n"
            ).encode("utf-8")
            authorization_id = "strict-json-test"

            def member(name: str, raw: bytes) -> dict:
                return {
                    "name": name,
                    "encoding": "base64",
                    "content": base64.b64encode(raw).decode("ascii"),
                    "artifact_digest": {
                        "algorithm": "sha256",
                        "value": hashlib.sha256(raw).hexdigest(),
                    },
                }

            capsule = {
                "schema_version": capsule_builder.CAPSULE_SCHEMA,
                "capsule_kind": "bootstrap_publication",
                "invocation_id": authorization_id,
                "members": [
                    member(
                        "records/bootstrap-authorizations/"
                        f"{authorization_id}.json",
                        malformed_authorization,
                    ),
                    member(capsule_builder.PROVISIONER_MEMBER, provisioner_raw),
                ],
                "formal_authority": "none",
                "positive_assurance_allowed": False,
            }
            capsule_raw = (
                json.dumps(
                    capsule,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                    allow_nan=False,
                ).encode("utf-8")
                + b"\n"
            )
            capsule_path = root / "capsule.json"
            capsule_path.write_bytes(capsule_raw)
            completed = subprocess.run(
                [
                    sys.executable,
                    "-I",
                    "-S",
                    "-B",
                    "-c",
                    capsule_builder.LOADER,
                    str(capsule_path),
                    hashlib.sha256(capsule_raw).hexdigest(),
                    hashlib.sha256(provisioner_raw).hexdigest(),
                    authorization_id,
                ],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                text=True,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("strict JSON rejection", completed.stderr)
            self.assertFalse(marker.exists())


if __name__ == "__main__":
    unittest.main()
