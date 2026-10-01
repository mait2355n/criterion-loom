from __future__ import annotations

from contextlib import ExitStack
import importlib.util
import json
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator, FormatChecker

import semantic_guard_u10_broker.core as core
from semantic_guard_u10_broker.protected_io import BrokerBoundaryError
from candidate_tests.u10_publisher_contract_fixture import publisher_contract_binding


ROOT = Path(__file__).parents[1]
SCRIPTS = Path(__file__).parent / "fixtures" / "scripts"
SCHEMAS = ROOT / "src" / "semantic_guard_vnext" / "validation" / "env-path-contracts"


def _load_script(name: str, module_name: str):
    path = SCRIPTS / name
    specification = importlib.util.spec_from_file_location(module_name, path)
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


OUTER = _load_script(
    "u10_root_control_outer_launcher.py", "u10_root_control_outer_tests"
)
BROKER_OUTER = _load_script(
    "u10_root_broker_outer_launcher.py",
    "u10_root_broker_outer_publisher_binding_tests",
)
DISPATCHER = _load_script(
    "u10_root_control_dispatcher.py", "u10_root_control_dispatcher_tests"
)


class U10FixedControlEntryTests(unittest.TestCase):
    def test_wrapper_is_two_argument_and_two_runtime_stage_contract(self) -> None:
        source = (SCRIPTS / "u10_root_control_entrypoint.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn('if [ "$#" -ne 2 ]', source)
        self.assertIn(
            "activate-snapshot|activate-store|key|project-snapshot|revoke-store",
            source,
        )
        self.assertIn("effective-python.path", source)
        self.assertIn('"$effective_python" -I -S -B', source)
        self.assertIn("u10_root_control_outer_launcher.py", source)
        self.assertNotIn("control-effective-python.path", source)

        outer_source = (SCRIPTS / "u10_root_control_outer_launcher.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("control-effective-python.path", outer_source)
        self.assertIn('"-I",\n            "-B"', outer_source)
        self.assertIn("u10_root_control_dispatcher.py", outer_source)

    def test_argument_denominator_rejects_path_raw_and_extra_values(self) -> None:
        for request in (
            [],
            ["activate-store"],
            ["activate-store", "id", "extra"],
            ["unknown", "id"],
            ["activate-store", "../store"],
            ["activate-store", "/tmp/store.json"],
            ["activate-store", '{"inline":true}'],
        ):
            with self.subTest(request=request):
                with self.assertRaises(OUTER.ControlOuterError):
                    OUTER._request(request)
                with self.assertRaises(DISPATCHER.ControlDispatchError):
                    DISPATCHER._request(request)
        for operation in (
            "activate-snapshot",
            "activate-store",
            "key",
            "project-snapshot",
            "revoke-store",
        ):
            self.assertEqual(
                OUTER._request([operation, "record.u10-1"]),
                (operation, "record.u10-1"),
            )

    def test_wrapper_rejects_invalid_requests_before_environment_resolution(
        self,
    ) -> None:
        wrapper = SCRIPTS / "u10_root_control_entrypoint.sh"
        for request in (
            [],
            ["activate-store"],
            ["activate-store", "id", "extra"],
            ["unknown", "id"],
            ["project-snapshot", "/tmp/authorization.json"],
            ["activate-snapshot", '{"inline":true}'],
        ):
            with self.subTest(request=request):
                observed = subprocess.run(
                    [str(wrapper), *request],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                    text=True,
                )
                self.assertEqual(observed.returncode, 64)

    def test_outer_environment_denominator_rejects_injection(self) -> None:
        expected = dict(OUTER.EXPECTED_ENVIRONMENT)
        with (
            patch.object(OUTER.os, "geteuid", return_value=0),
            patch.object(OUTER.os, "getegid", return_value=0),
            patch.object(
                OUTER.sys,
                "flags",
                SimpleNamespace(
                    isolated=1,
                    no_site=1,
                    dont_write_bytecode=1,
                ),
            ),
            patch.object(OUTER, "CONTROL_OUTER", Path(OUTER.__file__)),
            patch.dict(OUTER.os.environ, expected, clear=True),
        ):
            OUTER._validate_startup()
            OUTER.os.environ["PYTHONPATH"] = "/tmp/injected"
            with self.assertRaises(OUTER.ControlOuterError):
                OUTER._validate_startup()

    def test_publisher_binding_schema_and_historical_tamper_rejection(self) -> None:
        binding = publisher_contract_binding()
        schema = json.loads(
            (SCHEMAS / "u10-control-publisher-contract-binding-v1.schema.json")
            .read_text(encoding="utf-8")
        )
        Draft202012Validator(
            schema, format_checker=FormatChecker()
        ).validate(binding)
        self.assertEqual(
            core._validate_publisher_contract_binding_v1(
                binding, enforce_current=False
            ),
            binding,
        )
        tampered = json.loads(json.dumps(binding))
        tampered["allowed_operations"].append("raw-json")
        with self.assertRaises(BrokerBoundaryError) as observed:
            core._validate_publisher_contract_binding_v1(
                tampered, enforce_current=False
            )
        self.assertIn(
            observed.exception.code,
            {
                "u10_publisher_contract_binding_invalid",
                "u10_publisher_contract_binding_digest_mismatch",
            },
        )

    def test_execution_outer_rejects_relocated_historical_publisher(self) -> None:
        binding = publisher_contract_binding()
        self.assertTrue(BROKER_OUTER._is_publisher_contract_binding(binding))
        binding["artifacts"]["snapshot_store_producer"]["locator"] = (
            "/tmp/u10_snapshot_store_production.py"
        )
        material = json.loads(json.dumps(binding))
        material.pop("binding_digest")
        binding["binding_digest"] = core.digest_bytes(
            core.canonical_json_bytes(material)
        )
        self.assertFalse(BROKER_OUTER._is_publisher_contract_binding(binding))

    def test_retired_direct_publication_surfaces_fail_closed(self) -> None:
        with self.assertRaises(BrokerBoundaryError) as activation:
            core.publish_active_root_trust_store_v2(b"{}")
        self.assertEqual(
            activation.exception.code,
            "u10_unbound_publisher_invocation_prohibited",
        )
        with self.assertRaises(BrokerBoundaryError) as revocation:
            core.publish_store_revocation_record_v1("revocation.u10.test")
        self.assertEqual(
            revocation.exception.code,
            "u10_unbound_publisher_invocation_prohibited",
        )

    def test_store_activation_resolves_only_fixed_authorization_identifier(
        self,
    ) -> None:
        binding = publisher_contract_binding()
        with tempfile.TemporaryDirectory() as temporary:
            authorization_root = Path(temporary)
            authorization_id = "authorization.u10.test"
            authorization_path = authorization_root / f"{authorization_id}.json"
            authorization_raw = b"{}"
            authorization_path.write_bytes(authorization_raw)
            authorization_path.chmod(0o444)
            basis_ref = {
                "record_id": "store-basis.test",
                "locator": str(core.STORE_ACTIVATION_BASIS_ROOT / "test.json"),
                "artifact_digest": core.digest_bytes(b"basis"),
                "semantic_digest": core.digest_bytes(b"basis-semantic"),
            }
            authorization = {
                "authorization_id": authorization_id,
                "authorization_digest": core.digest_bytes(b"authorization"),
                "store_activation_basis_ref": basis_ref,
            }
            basis = {"publisher_contract_binding": binding}
            rendered_raw = b'{"lifecycle_state":"active"}'
            real_lstat = Path.lstat

            def root_lstat(target: Path):
                observed = real_lstat(target)
                fields = list(observed)
                fields[4] = 0
                fields[5] = 0
                return os.stat_result(fields)

            def read(target: Path, **_kwargs):
                self.assertEqual(Path(target), authorization_path)
                return authorization_raw

            with ExitStack() as stack:
                stack.enter_context(
                    patch.object(core, "AUTHORIZATION_ROOT", authorization_root)
                )
                stack.enter_context(
                    patch.object(core, "read_protected_file", side_effect=read)
                )
                stack.enter_context(
                    patch.object(
                        Path, "lstat", autospec=True, side_effect=root_lstat
                    )
                )
                stack.enter_context(
                    patch.object(core, "_validate_publisher_contract_binding_v1")
                )
                stack.enter_context(
                    patch.object(core, "_load_json_bytes", return_value=authorization)
                )
                stack.enter_context(patch.object(core, "_validate"))
                stack.enter_context(patch.object(core, "_sealed_digest"))
                stack.enter_context(
                    patch.object(
                        core,
                        "_load_store_activation_basis_v2",
                        return_value=(basis, b"basis"),
                    )
                )
                render = stack.enter_context(
                    patch.object(
                        core,
                        "_render_active_root_trust_store_from_basis_v1",
                        return_value=({"lifecycle_state": "active"}, rendered_raw),
                    )
                )
                publish = stack.enter_context(
                    patch.object(
                        core,
                        "_publish_active_root_trust_store_bytes_v2",
                        return_value={"publication_status": "synthetic"},
                    )
                )
                result = core.publish_active_root_trust_store_by_id_v1(
                    authorization_id,
                    publisher_contract_binding=binding,
                )
                self.assertEqual(result["publication_status"], "synthetic")
                publish.assert_called_once_with(rendered_raw, binding)
                self.assertEqual(
                    render.call_args.kwargs["authorization"], authorization
                )
                self.assertEqual(render.call_args.kwargs["basis"], basis)
                for invalid in ("../escape", "/tmp/store", "nested/store", b"raw"):
                    with self.subTest(invalid=invalid), self.assertRaises(
                        BrokerBoundaryError
                    ):
                        core.publish_active_root_trust_store_by_id_v1(
                            invalid,  # type: ignore[arg-type]
                            publisher_contract_binding=binding,
                        )

    def test_dispatcher_passes_one_static_binding_to_all_operations(self) -> None:
        binding = publisher_contract_binding()
        provenance = {
            "binding": {"binding_digest": {"value": "a" * 64}}
        }
        provisioner = SimpleNamespace(
            validate_bootstrap_provenance_chain=lambda: provenance,
            execute_key_authorization=lambda identifier, **kwargs: {
                "operation": "key",
                "identifier": identifier,
                "binding": kwargs["publisher_contract_binding"],
            },
        )
        producer = SimpleNamespace(
            project_snapshot_by_authorization_id=lambda identifier, **kwargs: {
                "operation": "project-snapshot",
                "identifier": identifier,
                "binding": kwargs["publisher_contract_binding"],
            },
            activate_snapshot_by_authorization_id=lambda identifier, **kwargs: {
                "operation": "activate-snapshot",
                "identifier": identifier,
                "binding": kwargs["publisher_contract_binding"],
            },
        )
        with (
            patch.object(DISPATCHER, "_load_provisioner", return_value=provisioner),
            patch.object(
                DISPATCHER.core,
                "build_current_publisher_contract_binding_v1",
                return_value=binding,
            ),
            patch.object(
                DISPATCHER.core,
                "publish_active_root_trust_store_by_id_v1",
                return_value={"operation": "activate"},
            ) as activate,
            patch.object(
                DISPATCHER.core,
                "publish_store_revocation_by_id_v1",
                return_value={"operation": "revoke"},
            ) as revoke,
            patch.object(
                DISPATCHER,
                "_load_snapshot_producer",
                return_value=producer,
            ) as load_snapshot_producer,
            patch.dict(
                DISPATCHER.os.environ,
                {"SEMANTIC_GUARD_U10_BOOTSTRAP_BINDING_DIGEST": "a" * 64},
                clear=False,
            ),
        ):
            DISPATCHER.dispatch("activate-store", "store.1")
            activate.assert_called_once_with(
                "store.1", publisher_contract_binding=binding
            )
            DISPATCHER.dispatch("revoke-store", "revocation.1")
            revoke.assert_called_once_with(
                "revocation.1", publisher_contract_binding=binding
            )
            key = DISPATCHER.dispatch("key", "key-authorization.1")
            self.assertEqual(key["binding"], binding)
            projected = DISPATCHER.dispatch(
                "project-snapshot", "snapshot-projection-authorization.1"
            )
            activated = DISPATCHER.dispatch(
                "activate-snapshot", "snapshot-adoption-authorization.1"
            )
            self.assertEqual(projected["binding"], binding)
            self.assertEqual(activated["binding"], binding)
            self.assertEqual(load_snapshot_producer.call_count, 2)

    def test_snapshot_producer_loader_executes_only_bound_fixed_bytes(
        self,
    ) -> None:
        binding = publisher_contract_binding()
        with tempfile.TemporaryDirectory() as temporary:
            producer_path = Path(temporary) / "u10_snapshot_store_production.py"
            raw = b"VALUE = 'bound-producer'\n"
            producer_path.write_bytes(raw)
            producer_path.chmod(0o400)
            binding["artifacts"]["snapshot_store_producer"][
                "artifact_digest"
            ] = core.digest_bytes(raw)
            real_lstat = Path.lstat

            def root_lstat(target: Path):
                observed = real_lstat(target)
                fields = list(observed)
                fields[4] = 0
                fields[5] = 0
                return os.stat_result(fields)

            with (
                patch.object(
                    DISPATCHER,
                    "SNAPSHOT_STORE_PRODUCER_PATH",
                    producer_path,
                ),
                patch.object(
                    DISPATCHER,
                    "read_protected_file",
                    side_effect=lambda target, **_kwargs: Path(
                        target
                    ).read_bytes(),
                ),
                patch.object(
                    Path, "lstat", autospec=True, side_effect=root_lstat
                ),
            ):
                loaded = DISPATCHER._load_snapshot_producer(binding)
                self.assertEqual(loaded.VALUE, "bound-producer")
                binding["artifacts"]["snapshot_store_producer"][
                    "artifact_digest"
                ] = core.digest_bytes(b"different")
                with self.assertRaises(DISPATCHER.ControlDispatchError):
                    DISPATCHER._load_snapshot_producer(binding)


if __name__ == "__main__":
    unittest.main()
