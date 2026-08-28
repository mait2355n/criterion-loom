from __future__ import annotations

from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import tomllib
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "verify_packaged_contracts.py"
SPEC = importlib.util.spec_from_file_location("verify_packaged_contracts", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
verifier = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = verifier
SPEC.loader.exec_module(verifier)


class PackagedContractVerifierTests(unittest.TestCase):
    def test_fixed_installed_audit_program_compiles(self) -> None:
        compile(verifier._AUDIT_PROGRAM, "<installed-contract-audit>", "exec")
        self.assertIn("adjacent_decoys_not_selected", verifier._AUDIT_PROGRAM)
        self.assertIn("operational_empty_object_rejected", verifier._AUDIT_PROGRAM)
        self.assertIn("field_intake_module_and_schema_packaged", verifier._AUDIT_PROGRAM)
        self.assertIn("canonical_distribution_identity", verifier._AUDIT_PROGRAM)
        self.assertIn("canonical_mcp_surface", verifier._AUDIT_PROGRAM)
        self.assertIn("public_audit_producer_version", verifier._AUDIT_PROGRAM)
        self.assertIn("direction_binding_provider_free_fail_closed", verifier._AUDIT_PROGRAM)
        self.assertIn("direction_binding_mcp_dispatch", verifier._AUDIT_PROGRAM)
        self.assertIn("canonical_cli_surface", verifier._AUDIT_PROGRAM)
        self.assertIn('"cli_commands": len(subparsers_action.choices)', verifier._AUDIT_PROGRAM)

    def test_wheel_manifest_includes_all_non_module_contract_resources(self) -> None:
        configuration = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        self.assertEqual(configuration["project"]["name"], "semantic-guard")
        self.assertEqual(configuration["project"]["version"], "1.1.0")
        self.assertEqual(
            set(configuration["project"]["scripts"]),
            {"semantic-guard", "semantic-guard-mcp"},
        )
        force_include = configuration["tool"]["hatch"]["build"]["targets"]["wheel"]["force-include"]
        self.assertEqual(force_include["schemas"], "semantic_guard/schemas")
        self.assertIn("validation/lifecycle-profile-registry.candidate.json", force_include)
        self.assertIn("validation/engineering-rule-pack.candidate.json", force_include)
        self.assertIn("validation/engineering-rule-pack.schema.json", force_include)
        sdist_include = set(
            configuration["tool"]["hatch"]["build"]["targets"]["sdist"]["include"]
        )
        self.assertIn("/src/semantic_guard", sdist_include)
        self.assertIn("/schemas", sdist_include)
        self.assertNotIn("/legacy", sdist_include)
        self.assertNotIn("/docs", sdist_include)
        self.assertNotIn("/tests", sdist_include)

    def test_failure_is_one_json_value_and_nonzero(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            status = verifier.main(
                [
                    "--wheel",
                    "/definitely/missing.whl",
                    "--sdist",
                    "/definitely/missing.tar.gz",
                ]
            )
        payload = json.loads(output.getvalue())
        self.assertEqual(status, 1)
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["errors"][0]["code"], "wheel_unavailable")

    def test_timeout_is_bounded_before_any_subprocess(self) -> None:
        with self.assertRaises(verifier.VerificationFailure) as caught:
            verifier.verify_wheel("missing.whl", timeout_seconds=1)
        self.assertEqual(caught.exception.code, "timeout_out_of_bounds")

    def test_symlink_wheel_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target.whl"
            target.write_bytes(b"not empty")
            link = root / "link.whl"
            link.symlink_to(target)
            with self.assertRaises(verifier.VerificationFailure) as caught:
                verifier._validate_wheel(link)
        self.assertEqual(caught.exception.code, "wheel_not_regular_file")

    def test_wheel_member_path_traversal_and_pth_are_rejected(self) -> None:
        for member, expected in (
            ("../escape.py", "wheel_member_unsafe"),
            ("..\\escape.py", "wheel_member_unsafe"),
            ("payload/activate.pth", "wheel_pth_not_allowed"),
        ):
            with self.subTest(member=member), tempfile.TemporaryDirectory() as directory:
                wheel = Path(directory) / "candidate.whl"
                with zipfile.ZipFile(wheel, "w") as archive:
                    archive.writestr(member, "x")
                with self.assertRaises(verifier.VerificationFailure) as caught:
                    verifier._validate_wheel(wheel)
                self.assertEqual(caught.exception.code, expected)

    def test_wheel_rejects_repository_only_archive_material(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            wheel = Path(directory) / "candidate.whl"
            with zipfile.ZipFile(wheel, "w") as archive:
                archive.writestr("legacy/semantic-guard-v0.1.0/README.md", "legacy")
            with self.assertRaises(verifier.VerificationFailure) as caught:
                verifier._validate_wheel(wheel)
        self.assertEqual(caught.exception.code, "wheel_distribution_boundary_violation")

    def test_sdist_rejects_repository_only_archive_and_validation_history(self) -> None:
        forbidden_members = (
            "semantic_guard-1.1.0/legacy/semantic-guard-v0.1.0/README.md",
            "semantic_guard-1.1.0/docs/audits/internal.md",
            "semantic_guard-1.1.0/validation/local-contract-verification.json",
        )
        for member in forbidden_members:
            with self.subTest(member=member), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                payload = root / "payload"
                payload.write_text("repository-only", encoding="utf-8")
                archive_path = root / "candidate.tar.gz"
                with tarfile.open(archive_path, "w:gz") as archive:
                    archive.add(payload, arcname=member)
                with self.assertRaises(verifier.VerificationFailure) as caught:
                    verifier._validate_sdist(archive_path)
                self.assertEqual(
                    caught.exception.code,
                    "sdist_distribution_boundary_violation",
                )

    def test_subprocess_executable_must_be_in_fixed_set(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(verifier.VerificationFailure) as caught:
                verifier._run_process(
                    [sys.executable, "-c", "raise SystemExit(0)"],
                    allowed_executables=frozenset(),
                    cwd=Path(directory),
                    env={},
                    timeout_seconds=15,
                    phase="test",
                )
        self.assertEqual(caught.exception.code, "executable_not_allowed")

    def test_public_arguments_cannot_select_executable_or_audit_program(self) -> None:
        destinations = {
            action.dest for action in verifier.build_parser()._actions
        }
        self.assertEqual(destinations, {"help", "wheel", "sdist", "timeout_seconds"})


if __name__ == "__main__":
    unittest.main()
