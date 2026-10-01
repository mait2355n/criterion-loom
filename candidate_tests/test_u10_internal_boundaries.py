from __future__ import annotations

import ast
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import semantic_guard_u10_broker.internal_operations as internal_operations
from semantic_guard_u10_broker.internal_contracts import (
    CONTROL_ALLOWED_OPERATIONS_V1,
    STORE_ACTIVATION_LEDGER_POLICY_V3,
    STORE_LEDGER_RETENTION_POLICY_V1,
    STORE_REVOCATION_LEDGER_POLICY_V2,
)
import semantic_guard_u10_broker.supervisor as supervisor


ROOT = Path(__file__).parents[1]
SCRIPTS = Path(__file__).parent / "fixtures" / "scripts"
SCHEMAS = ROOT / "src" / "semantic_guard_vnext" / "validation" / "env-path-contracts"


def _load_script(name: str, module_name: str):
    path = SCRIPTS / name
    specification = importlib.util.spec_from_file_location(module_name, path)
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


CONTROL_OUTER = _load_script(
    "u10_root_control_outer_launcher.py",
    "u10_internal_boundary_control_outer",
)
BROKER_OUTER = _load_script(
    "u10_root_broker_outer_launcher.py",
    "u10_internal_boundary_broker_outer",
)
DISPATCHER = _load_script(
    "u10_root_control_dispatcher.py",
    "u10_internal_boundary_dispatcher",
)
SNAPSHOT_PRODUCER = _load_script(
    "u10_snapshot_store_production.py",
    "u10_internal_boundary_snapshot_producer",
)


class U10InternalBoundaryTests(unittest.TestCase):
    def test_trusted_callers_use_one_explicit_internal_operation_surface(self) -> None:
        self.assertEqual(
            set(internal_operations.__all__),
            {
                "build_signed_envelope_v3",
                "load_current_store_activation_context_v1",
                "require_time_order",
                "revocation_transition_ref_v1",
                "store_transition_ref_v1",
                "validate_publisher_contract_binding_v1",
            },
        )
        self.assertTrue(
            all(not name.startswith("_") for name in internal_operations.__all__)
        )
        self.assertIs(
            supervisor._build_signed_envelope_v3,
            internal_operations.build_signed_envelope_v3,
        )
        self.assertIs(
            supervisor._require_time_order,
            internal_operations.require_time_order,
        )
        self.assertIs(
            SNAPSHOT_PRODUCER._load_current_store_activation_context_v1,
            internal_operations.load_current_store_activation_context_v1,
        )
        self.assertIs(
            SNAPSHOT_PRODUCER._validate_publisher_contract_binding_v1,
            internal_operations.validate_publisher_contract_binding_v1,
        )

    def test_trusted_callers_do_not_import_private_core_symbols_directly(self) -> None:
        package_root = ROOT / "src" / "semantic_guard_u10_broker"
        allowed_private_bridge = package_root / "internal_operations.py"
        targets = sorted(
            path
            for search_root in (package_root, SCRIPTS)
            for path in search_root.rglob("*.py")
            if path != allowed_private_bridge
        )
        for path in targets:
            with self.subTest(path=path):
                tree = ast.parse(path.read_text(encoding="utf-8"))
                private_names = [
                    alias.name
                    for node in ast.walk(tree)
                    if isinstance(node, ast.ImportFrom)
                    and (
                        node.module == "semantic_guard_u10_broker.core"
                        or (node.level == 1 and node.module == "core")
                    )
                    for alias in node.names
                    if alias.name.startswith("_")
                ]
                self.assertEqual(private_names, [])

    def test_control_operation_mirrors_match_package_contract(self) -> None:
        expected = tuple(CONTROL_ALLOWED_OPERATIONS_V1)
        self.assertEqual(tuple(sorted(CONTROL_OUTER.ALLOWED_OPERATIONS)), expected)
        self.assertEqual(tuple(sorted(DISPATCHER.ALLOWED_OPERATIONS)), expected)

        schema = json.loads(
            (
                SCHEMAS
                / "u10-control-publisher-contract-binding-v1.schema.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(
            tuple(schema["properties"]["allowed_operations"]["const"]),
            expected,
        )
        wrapper = (SCRIPTS / "u10_root_control_entrypoint.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("|".join(expected), wrapper)

    def test_store_ledger_policy_mirrors_match_package_contract(self) -> None:
        self.assertEqual(
            BROKER_OUTER.STORE_ACTIVATION_LEDGER_POLICY,
            STORE_ACTIVATION_LEDGER_POLICY_V3,
        )
        self.assertEqual(
            BROKER_OUTER.STORE_ACTIVATION_LEDGER_RETENTION_POLICY,
            STORE_LEDGER_RETENTION_POLICY_V1,
        )
        self.assertEqual(
            BROKER_OUTER.REVOCATION_LEDGER_POLICY,
            STORE_REVOCATION_LEDGER_POLICY_V2,
        )
        self.assertEqual(
            BROKER_OUTER.REVOCATION_LEDGER_RETENTION_POLICY,
            STORE_LEDGER_RETENTION_POLICY_V1,
        )

        schema = json.loads(
            (
                SCHEMAS / "u10-root-trust-store-v2.schema.json"
            ).read_text(encoding="utf-8")
        )
        selector = schema["properties"]["current_selector"]["properties"]
        self.assertEqual(
            selector["activation_ledger_policy"]["const"],
            STORE_ACTIVATION_LEDGER_POLICY_V3,
        )
        self.assertEqual(
            selector["activation_ledger_retention_policy"]["const"],
            STORE_LEDGER_RETENTION_POLICY_V1,
        )
        self.assertEqual(
            selector["revocation_ledger_policy"]["const"],
            STORE_REVOCATION_LEDGER_POLICY_V2,
        )
        self.assertEqual(
            selector["revocation_ledger_retention_policy"]["const"],
            STORE_LEDGER_RETENTION_POLICY_V1,
        )

        with patch.object(
            SNAPSHOT_PRODUCER,
            "_store_entry_from_active_snapshot",
            return_value={},
        ):
            content = SNAPSHOT_PRODUCER._initial_store_content(
                manifest={
                    "broker_runtime_ref": {},
                    "prepared_for_entry_id": "entry.u10.test",
                },
                manifest_ref={},
                projection_authorization={
                    "broker_entrypoint_ref": {},
                    "broker_outer_launcher_ref": {},
                    "broker_launch_platform": {},
                },
                signing_key={},
                store_revision_id="revision.u10.test",
                prior_store=None,
            )
        current_selector = content["current_selector"]
        self.assertEqual(
            current_selector["activation_ledger_policy"],
            STORE_ACTIVATION_LEDGER_POLICY_V3,
        )
        self.assertEqual(
            current_selector["activation_ledger_retention_policy"],
            STORE_LEDGER_RETENTION_POLICY_V1,
        )
        self.assertEqual(
            current_selector["revocation_ledger_policy"],
            STORE_REVOCATION_LEDGER_POLICY_V2,
        )
        self.assertEqual(
            current_selector["revocation_ledger_retention_policy"],
            STORE_LEDGER_RETENTION_POLICY_V1,
        )


if __name__ == "__main__":
    unittest.main()
