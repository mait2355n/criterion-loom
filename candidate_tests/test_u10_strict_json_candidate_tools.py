from __future__ import annotations

from contextlib import redirect_stdout
from importlib.machinery import ModuleSpec
import importlib.util
import io
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock


SCRIPT_ROOT = Path(__file__).parent / "fixtures" / "scripts"


def _load(name: str, filename: str):
    specification = importlib.util.spec_from_file_location(
        name, SCRIPT_ROOT / filename
    )
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    sys.modules[name] = module
    specification.loader.exec_module(module)
    return module


candidate = _load(
    "u10_strict_json_root_candidate_test",
    "prepare_u10_root_candidate.py",
)
_prior_candidate_module = sys.modules.get("prepare_u10_root_candidate")
sys.modules["prepare_u10_root_candidate"] = candidate
try:
    preactivation = _load(
        "u10_strict_json_preactivation_test",
        "prepare_u10_preactivation_records.py",
    )
finally:
    if _prior_candidate_module is None:
        sys.modules.pop("prepare_u10_root_candidate", None)
    else:
        sys.modules["prepare_u10_root_candidate"] = _prior_candidate_module
environment_candidate = _load(
    "u10_strict_json_environment_candidate_test",
    "generate_u10_environment_candidate.py",
)


class U10StrictJSONCandidateToolTests(unittest.TestCase):
    def test_decoders_accept_unambiguous_finite_json(self) -> None:
        raw = b'{"items":[1,2.5,{"enabled":false}],"name":"candidate"}'
        expected = {
            "items": [1, 2.5, {"enabled": False}],
            "name": "candidate",
        }
        self.assertEqual(candidate.strict_json_loads(raw), expected)
        self.assertEqual(environment_candidate.strict_json_loads(raw), expected)

    def test_all_external_decoders_reject_ambiguous_or_nonfinite_json(
        self,
    ) -> None:
        payloads = (
            b'{"outer":{"same":1,"same":2}}',
            b'{"same":1,"s\\u0061me":2}',
            b'{"value":NaN}',
            b'{"value":Infinity}',
            b'{"value":-Infinity}',
            b'{"value":1e999}',
        )
        decoders = (
            candidate.strict_json_loads,
            environment_candidate.strict_json_loads,
        )
        for decoder in decoders:
            for raw in payloads:
                with self.subTest(decoder=decoder.__module__, raw=raw):
                    with self.assertRaises(json.JSONDecodeError):
                        decoder(raw)

    def test_bundle_manifest_rejects_before_schema_validation(self) -> None:
        payloads = (
            b'{"nested":{"x":1,"x":2}}',
            b'{"value":NaN}',
            b'{"value":1e999}',
        )
        for raw in payloads:
            with self.subTest(raw=raw), tempfile.TemporaryDirectory() as temporary:
                bundle = Path(temporary).resolve()
                manifest = bundle / candidate.MANIFEST_NAME
                manifest.write_bytes(raw)
                manifest.chmod(0o600)
                with mock.patch.object(
                    candidate, "validate_bundle_manifest_v1"
                ) as validator:
                    with self.assertRaises(candidate.CandidateBoundaryError):
                        candidate._load_bundle_manifest_raw_v1(bundle)
                    validator.assert_not_called()

    def test_subprocess_json_rejects_before_result_contract_validation(self) -> None:
        payloads = (
            '{"base_prefix":"/x","nested":{"x":1,"x":2}}',
            '{"base_prefix":"/x","value":NaN}',
            '{"base_prefix":"/x","value":1e999}',
        )
        for stdout in payloads:
            completed = subprocess.CompletedProcess(
                args=[], returncode=0, stdout=stdout, stderr=""
            )
            with self.subTest(stdout=stdout), mock.patch.object(
                candidate.subprocess, "run", return_value=completed
            ):
                with self.assertRaises(candidate.CandidateBoundaryError):
                    candidate._python_layout(Path("/qualified/python"))

    def test_preactivation_rejects_before_validation_and_output(self) -> None:
        payloads = (
            b'{"nested":{"x":1,"x":2}}',
            b'{"value":NaN}',
            b'{"value":1e999}',
        )
        for raw in payloads:
            with self.subTest(raw=raw), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                output = root / "observation.json"
                with (
                    mock.patch.object(
                        candidate,
                        "_read_stable_regular",
                        return_value=(raw, root / "decision.json", mock.Mock()),
                    ),
                    mock.patch.object(
                        candidate, "validate_preactivation_decision_v1"
                    ) as validator,
                ):
                    with self.assertRaises(candidate.CandidateBoundaryError):
                        preactivation.observe(
                            decision_path=root / "decision.json",
                            output=output,
                            account_name="worker",
                        )
                    validator.assert_not_called()
                self.assertFalse(output.exists())

    def test_environment_profile_rejects_before_validation_and_output(self) -> None:
        payloads = (
            b'{"nested":{"x":1,"x":2}}',
            b'{"value":NaN}',
            b'{"value":1e999}',
        )
        for raw in payloads:
            with self.subTest(raw=raw), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                profile = root / environment_candidate.PROFILE_LOCATOR
                profile.parent.mkdir(parents=True)
                profile.write_bytes(raw)
                with (
                    mock.patch.object(
                        environment_candidate, "validate_verification_profile_v4"
                    ) as validator,
                    mock.patch.object(
                        environment_candidate, "_write_candidate"
                    ) as writer,
                ):
                    with self.assertRaises(json.JSONDecodeError):
                        environment_candidate.generate(root, replace=False)
                    validator.assert_not_called()
                    writer.assert_not_called()

    def test_output_serializers_reject_before_emitting_or_writing(self) -> None:
        with self.assertRaises(ValueError):
            candidate.canonical_json_bytes({"value": math.nan})
        with self.assertRaises(ValueError):
            candidate._json_record_bytes_v1({"value": math.inf})
        candidate_stdout = io.StringIO()
        with self.assertRaises(ValueError), redirect_stdout(candidate_stdout):
            candidate._json_output({"value": -math.inf})
        self.assertEqual(candidate_stdout.getvalue(), "")
        with self.assertRaises(ValueError):
            environment_candidate._artifact_bytes({"value": math.nan})

        tool_stdout = io.StringIO()
        with (
            mock.patch.object(
                preactivation, "observe", return_value={"value": math.nan}
            ),
            self.assertRaises(ValueError),
            redirect_stdout(tool_stdout),
        ):
            preactivation.main(
                [
                    "observe",
                    "--decision",
                    "/unused/decision.json",
                    "--output",
                    "/unused/output.json",
                ]
            )
        self.assertEqual(tool_stdout.getvalue(), "")

    def test_finite_output_serialization_is_digest_compatible(self) -> None:
        value = {"z": "日本語", "a": [1, 2]}
        self.assertEqual(
            candidate.canonical_json_bytes(value),
            b'{"a":[1,2],"z":"\xe6\x97\xa5\xe6\x9c\xac\xe8\xaa\x9e"}',
        )
        expected_pretty = (
            json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)
            + "\n"
        ).encode("utf-8")
        self.assertEqual(environment_candidate._artifact_bytes(value), expected_pretty)

    def test_jsonl_output_guard_rejects_ambiguous_or_nonfinite_records(self) -> None:
        payloads = (
            b'{"nested":{"x":1,"x":2}}\n',
            b'{"value":NaN}\n',
            b'{"value":1e999}\n',
        )
        for raw in payloads:
            with self.subTest(raw=raw):
                with self.assertRaises(RuntimeError):
                    environment_candidate._validate_strict_json_lines(raw)

    def test_root_candidate_rejects_nonexistent_module_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            module = types.ModuleType("adversarial_missing_origin")
            module.__file__ = str(Path(temporary).resolve() / "missing.pyc")
            with self.assertRaisesRegex(
                candidate.CandidateBoundaryError, "existing file"
            ):
                candidate._validate_bootstrap_module_origin_v1(
                    module.__name__, module
                )

    def test_root_candidate_rejects_unverified_originless_module(self) -> None:
        module = types.ModuleType("adversarial_originless")
        module.__spec__ = ModuleSpec(
            module.__name__, loader=None, origin="ordinary-loader"
        )
        with self.assertRaisesRegex(
            candidate.CandidateBoundaryError, "unverified"
        ):
            candidate._validate_bootstrap_module_origin_v1(module.__name__, module)

    def test_root_candidate_allows_verified_intrinsic_and_namespace_origins(
        self,
    ) -> None:
        for origin in ("built-in", "frozen"):
            module = types.ModuleType(f"qualified_{origin}")
            module.__spec__ = ModuleSpec(
                module.__name__, loader=None, origin=origin
            )
            candidate._validate_bootstrap_module_origin_v1(module.__name__, module)

        with tempfile.TemporaryDirectory() as temporary:
            namespace = Path(temporary).resolve() / "namespace"
            namespace.mkdir()
            module = types.ModuleType("qualified_namespace")
            specification = ModuleSpec(
                module.__name__, loader=None, is_package=True
            )
            specification.submodule_search_locations = [str(namespace)]
            module.__spec__ = specification
            with mock.patch.object(
                candidate, "_validate_owned_directory_chain"
            ) as chain_validator:
                candidate._validate_bootstrap_module_origin_v1(
                    module.__name__, module
                )
            chain_validator.assert_called_once_with(namespace, required_uid=0)


if __name__ == "__main__":
    unittest.main()
