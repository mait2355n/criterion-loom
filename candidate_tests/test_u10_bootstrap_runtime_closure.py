from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

from jsonschema import Draft202012Validator

import semantic_guard_u10_broker.core as core
from semantic_guard_u10_broker.protected_io import BrokerBoundaryError
import semantic_guard_u10_broker.runtime_closure as runtime_closure


SCRIPT_ROOT = Path(__file__).parent / "fixtures" / "scripts"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


generator = _load(
    "u10_bootstrap_runtime_manifest_generator",
    SCRIPT_ROOT / "prepare_u10_bootstrap_runtime_manifest.py",
)
outer = _load(
    "u10_bootstrap_runtime_outer_launcher",
    SCRIPT_ROOT / "u10_root_broker_outer_launcher.py",
)


def _path_record(path: Path, *, state: str = "present") -> dict:
    return {
        "locator": str(path),
        "resolved_locator": str(path),
        "state": state,
    }


class U10BootstrapRuntimeClosureTests(unittest.TestCase):
    def test_core_private_names_are_identity_reexports(self) -> None:
        names = (
            "_RUNTIME_CLOSURE_PROFILE",
            "_RUNTIME_OS_EXCLUSION_PROFILE",
            "_RUNTIME_OS_ASSET_ROOTS",
            "_RUNTIME_PROBE_ENVIRONMENT",
            "_RUNTIME_PROBE",
            "_ref_artifact_digest",
            "_verify_root_artifact",
            "_verify_host_runtime_artifact",
            "_validate_absolute_root_owned_chain_v1",
            "_runtime_path_is_under_v1",
            "_runtime_inclusion_paths_v1",
            "_derive_runtime_root_v1",
            "_probe_bootstrap_runtime_v1",
            "_validate_current_process_runtime_closure_v1",
            "_host_runtime_tree_entries_v1",
        )
        for name in names:
            with self.subTest(name=name):
                self.assertIs(
                    getattr(core, name),
                    getattr(runtime_closure, name),
                )

    def _observation(self, base: Path) -> dict:
        interpreter = base / "bin" / "python3"
        process_image = base / "Resources" / "Python"
        stdlib = base / "lib" / "python3.9"
        module = stdlib / "json.py"
        framework = base / "Python3"
        for path in (interpreter, process_image, module, framework):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"fixture\n")
        inactive_site = base.parent / "unqualified-site-packages"
        return {
            "probe_profile": generator.RUNTIME_CLOSURE_PROFILE,
            "runtime_version": "3.9.6",
            "probe_execution_identity": {
                "effective_uid": 0,
                "effective_gid": 0,
            },
            "process_image": {
                "sys_executable": _path_record(interpreter),
                "ns_get_executable_path": _path_record(process_image),
            },
            "python_prefixes": {
                "prefix": _path_record(base),
                "base_prefix": _path_record(base),
            },
            "sys_path": [_path_record(stdlib)],
            "stdlib_roots": [
                {**_path_record(stdlib), "kind": "platstdlib"},
                {**_path_record(stdlib), "kind": "stdlib"},
            ],
            "site_roots": [
                {
                    **_path_record(inactive_site, state="absent"),
                    "source": "sysconfig.purelib",
                    "active": False,
                    "disposition": "suppressed_by_isolated_no_site",
                }
            ],
            "site_policy": (
                "isolated_no_site_only_active_paths_enter_runtime_closure/v1"
            ),
            "imported_module_origins": [
                {**_path_record(module), "module": "json"}
            ],
            "dyld_images": [
                {
                    **_path_record(framework),
                    "classification": "runtime_tree",
                    "os_asset_root": None,
                },
                {
                    **_path_record(
                        Path("/usr/lib/libSystem.B.dylib"), state="absent"
                    ),
                    "classification": "excluded_os_asset",
                    "os_asset_root": "/usr/lib",
                },
            ],
            "os_asset_exclusion": {
                "profile": generator.OS_ASSET_EXCLUSION_PROFILE,
                "allowed_roots": ["/System/Library", "/usr/lib"],
                "scope": "dyld_images_only",
                "binding": "exact_platform_binding_and_os_build_artifact",
            },
        }

    def test_common_root_is_exact_isolated_base_prefix_in_all_verifiers(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary).resolve() / "runtime"
            observation = self._observation(base)
            self.assertEqual(generator._derive_runtime_root(observation), base)
            self.assertEqual(outer._derive_runtime_root(observation), base)
            self.assertEqual(core._derive_runtime_root_v1(observation), base)

    def test_caller_cannot_narrow_runtime_root_to_bin(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary).resolve() / "runtime"
            observation = self._observation(base)
            interpreter = base / "bin" / "python3"
            with mock.patch.object(
                generator,
                "_probe_interpreter",
                return_value=("3.9.6", interpreter, observation),
            ):
                with self.assertRaisesRegex(
                    generator.BootstrapManifestError,
                    "not the execution-derived runtime root",
                ):
                    generator.build_manifest(
                        interpreter, expected_runtime_root=interpreter.parent
                    )

    def test_non_os_dyld_image_outside_base_prefix_is_not_excludable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            base = root / "runtime"
            observation = self._observation(base)
            injected = root / "injected" / "evil.dylib"
            injected.parent.mkdir()
            injected.write_bytes(b"evil\n")
            observation["dyld_images"].append(
                {
                    **_path_record(injected),
                    "classification": "runtime_tree",
                    "os_asset_root": None,
                }
            )
            with self.assertRaisesRegex(
                generator.BootstrapManifestError, "not the isolated base_prefix"
            ):
                generator._derive_runtime_root(observation)
            with self.assertRaisesRegex(
                outer.OuterLaunchError, "base_prefix mismatch"
            ):
                outer._derive_runtime_root(observation)
            with self.assertRaisesRegex(
                BrokerBoundaryError, "u10_bootstrap_runtime_base_prefix_mismatch"
            ):
                core._derive_runtime_root_v1(observation)

    def test_fake_os_classification_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary).resolve() / "runtime"
            observation = self._observation(base)
            observation["dyld_images"].append(
                {
                    **_path_record(Path("/opt/attacker/evil.dylib"), state="absent"),
                    "classification": "excluded_os_asset",
                    "os_asset_root": "/usr/lib",
                }
            )
            with self.assertRaisesRegex(
                generator.BootstrapManifestError, "invalid excluded OS"
            ):
                generator._derive_runtime_root(observation)
            with self.assertRaisesRegex(
                outer.OuterLaunchError, "invalid excluded OS"
            ):
                outer._derive_runtime_root(observation)
            with self.assertRaisesRegex(
                BrokerBoundaryError, "u10_bootstrap_runtime_os_exclusion_mismatch"
            ):
                core._derive_runtime_root_v1(observation)

    @unittest.skipUnless(os.uname().sysname == "Darwin", "Darwin-only probe")
    def test_real_probe_sources_agree_and_derive_effective_base_prefix(self) -> None:
        discovery = subprocess.run(
            [
                "/usr/bin/python3",
                "-I",
                "-S",
                "-B",
                "-c",
                "import json,os,sys; print(json.dumps({'executable': os.path.realpath(sys.executable)}))",
            ],
            check=True,
            capture_output=True,
            text=True,
            env=generator.PROBE_ENVIRONMENT,
        )
        interpreter = Path(json.loads(discovery.stdout)["executable"])

        def execute(source: str, environment: dict[str, str]) -> dict:
            result = subprocess.run(
                [str(interpreter), "-I", "-S", "-B", "-c", source],
                check=True,
                capture_output=True,
                text=True,
                env=environment,
            )
            return json.loads(result.stdout)

        generated = execute(generator.RUNTIME_PROBE, generator.PROBE_ENVIRONMENT)
        outer_observed = execute(
            outer.RUNTIME_PROBE, outer.RUNTIME_PROBE_ENVIRONMENT
        )
        core_observed = execute(core._RUNTIME_PROBE, core._RUNTIME_PROBE_ENVIRONMENT)
        self.assertEqual(generated, outer_observed)
        self.assertEqual(generated, core_observed)
        for observation in (generated, outer_observed, core_observed):
            observation["probe_execution_identity"] = {
                "effective_uid": 0,
                "effective_gid": 0,
            }
        expected = Path(
            generated["python_prefixes"]["base_prefix"]["resolved_locator"]
        )
        self.assertEqual(generator._derive_runtime_root(generated), expected)
        self.assertEqual(outer._derive_runtime_root(outer_observed), expected)
        self.assertEqual(core._derive_runtime_root_v1(core_observed), expected)
        self.assertNotEqual(expected, interpreter.parent)
        digest = {"algorithm": "sha256", "value": "0" * 64}
        schema = json.loads(
            (
                Path(__file__).parents[1]
                / "src" / "semantic_guard_vnext" / "validation"
                / "env-path-contracts"
                / "u10-bootstrap-runtime-manifest-v1.schema.json"
            ).read_text(encoding="utf-8")
        )
        manifest = {
            "schema_version": (
                "semantic-guard-u10-bootstrap-runtime-manifest/v1"
            ),
            "runtime_id": "runtime.u10.bootstrap.test",
            "runtime_version": generated["runtime_version"],
            "runtime_root": str(expected),
            "runtime_root_mode": 493,
            "runtime_root_uid": 0,
            "runtime_root_gid": 0,
            "effective_interpreter_locator": str(interpreter),
            "effective_interpreter_artifact_digest": digest,
            "runtime_closure": generated,
            "platform_binding": {
                "system": "Darwin",
                "release": "test",
                "kernel_version": "test",
                "machine": "test",
                "os_build_artifact": {
                    "locator": (
                        "/System/Library/CoreServices/SystemVersion.plist"
                    ),
                    "product_build_version": "test",
                    "artifact_digest": digest,
                },
                "binding_profile": (
                    "uname_kernel_and_system_version_artifact_exact/v2"
                ),
            },
            "tree_denominator": {
                "status": "closed",
                "entry_count": 1,
                "entries": [
                    {
                        "path": "lib",
                        "kind": "directory",
                        "mode": 493,
                        "uid": 0,
                        "gid": 0,
                    }
                ],
                "tree_digest": digest,
            },
            "trust_boundary": {
                "covered": (
                    "root_owned_runtime_tree_resistant_to_non_root_tampering"
                ),
                "not_claimed": "root_or_os_compromise_resistance",
            },
            "formal_authority": "none",
            "positive_assurance_allowed": False,
            "manifest_digest": digest,
        }
        errors = list(Draft202012Validator(schema).iter_errors(manifest))
        self.assertEqual(errors, [], [error.message for error in errors])


if __name__ == "__main__":
    unittest.main()
