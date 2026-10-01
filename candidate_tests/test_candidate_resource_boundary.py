from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from semantic_guard_vnext import candidate_governance_adapters as adapters
from semantic_guard_vnext import environment_resolution, lifecycle_profiles
from semantic_guard_vnext import local_verification, mcp_server, schema_access
from semantic_guard_u10_broker import core as broker


class CandidateResourceBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.package = self.root / "src" / "semantic_guard_vnext"
        self.package.mkdir(parents=True)
        (self.root / "pyproject.toml").write_text("[project]\nname='decoy'\n")

    def decoy(self, relative: str) -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}")
        return path

    def test_missing_candidate_schema_does_not_use_canonical_root(self) -> None:
        self.decoy("schemas/common.schema.json")
        with patch.object(schema_access, "__file__", str(self.package / "schema_access.py")):
            with self.assertRaises(FileNotFoundError):
                schema_access.schema_directory()

    def test_missing_governance_resource_does_not_use_canonical_root(self) -> None:
        name = "engineering-rule-pack.candidate.json"
        self.decoy("validation/" + name)
        with patch.object(adapters, "__file__", str(self.package / "candidate_governance_adapters.py")):
            with self.assertRaises(adapters.CandidateGovernanceAdapterError):
                adapters._validation_path(name)

    def test_missing_environment_schema_does_not_use_root_contracts(self) -> None:
        self.decoy("validation/env-path-contracts/local-verification-profile-v3.schema.json")
        with patch.object(environment_resolution, "__file__", str(self.package / "environment_resolution.py")):
            with self.assertRaises(FileNotFoundError):
                environment_resolution.environment_schema_directory()

    def test_broker_never_selects_root_environment_contracts(self) -> None:
        self.decoy("validation/env-path-contracts/u10-root-trust-store-v2.schema.json")
        broker_file = self.root / "src" / "semantic_guard_u10_broker" / "core.py"
        with patch.object(broker, "__file__", str(broker_file)):
            with self.assertRaises(broker.BrokerBoundaryError):
                broker._schema_directory()
            expected = self.package / "validation" / "env-path-contracts"
            expected.mkdir(parents=True)
            (expected / "u10-root-trust-store-v2.schema.json").write_text("{}")
            self.assertEqual(broker._schema_directory(), expected)

    def test_constitution_missing_from_package_does_not_use_root(self) -> None:
        self.decoy("constitution/semantic-guard-vnext-constitution.yaml")
        with (
            patch.object(mcp_server.resources, "files", return_value=self.package),
            patch.object(mcp_server, "__file__", str(self.package / "mcp_server.py")),
            self.assertRaises(FileNotFoundError),
        ):
            mcp_server.semantic_guard_vnext_constitution_resource()

    def test_lifecycle_default_ignores_existing_root_candidate(self) -> None:
        self.decoy("validation/lifecycle-profile-registry.candidate.json")
        namespace = {
            "__name__": "semantic_guard_vnext._resource_boundary_probe",
            "__package__": "semantic_guard_vnext",
            "__file__": str(self.package / "lifecycle_profiles.py"),
        }
        source = Path(lifecycle_profiles.__file__).read_text()
        exec(compile(source, namespace["__file__"], "exec"), namespace)
        expected = self.package / "validation/lifecycle-profile-registry.candidate.json"
        self.assertEqual(namespace["_CANDIDATE_PATH"], expected)
        self.assertFalse(expected.exists())

    def test_local_verification_contracts_are_package_local(self) -> None:
        package = Path(local_verification.__file__).resolve().parent
        self.assertEqual(local_verification._VALIDATION_DIRECTORY, package / "validation")
        for name in (
            "_PROFILE_SCHEMA_PATH", "_PROFILE_SCHEMA_V1_PATH", "_PROFILE_SCHEMA_V2_PATH",
            "_RUN_SCHEMA_PATH", "_RUN_SCHEMA_V1_PATH", "_RUN_SCHEMA_V2_PATH",
            "_ENVIRONMENT_SCHEMA_PATH",
        ):
            self.assertTrue(getattr(local_verification, name).is_file(), name)


if __name__ == "__main__":
    unittest.main()
