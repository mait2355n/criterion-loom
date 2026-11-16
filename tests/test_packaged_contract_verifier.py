from __future__ import annotations

from contextlib import redirect_stdout
import ast
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
    def test_installed_audit_reads_text_resources_as_utf8(self) -> None:
        reads = [
            node for node in ast.walk(ast.parse(verifier._AUDIT_PROGRAM))
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr == "read_text"
        ]
        self.assertGreaterEqual(len(reads), 4)
        for node in reads:
            with self.subTest(line=node.lineno):
                encodings = [item.value for item in node.keywords if item.arg == "encoding"]
                self.assertEqual(len(encodings), 1)
                self.assertIsInstance(encodings[0], ast.Constant)
                self.assertEqual(encodings[0].value, "utf-8")

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
        for check in ("shared_wheel_namespace_isolation", "workflow_owned_resources",
                      "workflow_plan_finish_membership_cli", "candidate_owned_resources",
                      "candidate_governance_remains_unadopted"):
            self.assertIn(check, verifier._AUDIT_PROGRAM)
        self.assertIn('"cli_commands": len(subparsers_action.choices)', verifier._AUDIT_PROGRAM)

    def test_wheel_manifest_includes_all_non_module_contract_resources(self) -> None:
        configuration = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        self.assertEqual(configuration["project"]["name"], "semantic-guard")
        self.assertEqual(configuration["project"]["version"], "1.2.0.dev0")
        self.assertEqual(
            set(configuration["project"]["scripts"]),
            {"semantic-guard", "semantic-guard-mcp", "semantic-guard-workflow",
             "semantic-guard-workflow-mcp", "semantic-guard-vnext", "semantic-guard-vnext-mcp"},
        )
        force_include = configuration["tool"]["hatch"]["build"]["targets"]["wheel"]["force-include"]
        self.assertEqual(force_include["schemas"], "semantic_guard/schemas")
        self.assertIn("validation/lifecycle-profile-registry.candidate.json", force_include)
        self.assertIn("validation/engineering-rule-pack.candidate.json", force_include)
        self.assertIn("validation/engineering-rule-pack.schema.json", force_include)
        sdist_include = set(
            configuration["tool"]["hatch"]["build"]["targets"]["sdist"]["include"]
        )
        for namespace in verifier._RUNTIME_NAMESPACES:
            self.assertIn("/src/" + namespace, sdist_include)
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

    def test_added_namespaces_accept_only_owned_runtime_resources(self) -> None:
        allowed_members = (
            "semantic_guard_workflow/cli.py",
            "semantic_guard_workflow/runtime/review.py",
            "semantic_guard_workflow/_resources/schemas/audit-result.schema.json",
            "semantic_guard_workflow/_resources/docs/conventions/base-contract.json",
            "semantic_guard_workflow/_resources/tests/fixtures/plans/good.expected.json",
            "semantic_guard_vnext/schemas/governed-audit-result.schema.json",
            "semantic_guard_vnext/validation/local-verification-profile.schema.json",
            "semantic_guard_vnext/validation/env-path-contracts/local-environment-adoption.schema.json",
            "semantic_guard_u10_broker/core.py",
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            wheel = root / "candidate.whl"
            sdist = root / "candidate.tar.gz"
            with zipfile.ZipFile(wheel, "w") as archive:
                for member in set(allowed_members) | verifier._ALLOWED_ADDITIONAL_RESOURCES:
                    archive.writestr(member, "runtime")
            verifier._validate_wheel(wheel)
            with tarfile.open(sdist, "w:gz") as archive:
                for member in set(allowed_members) | verifier._ALLOWED_ADDITIONAL_RESOURCES:
                    data = b"runtime"
                    info = tarfile.TarInfo(verifier._CANONICAL_SDIST_ROOT + "/src/" + member)
                    info.size = len(data)
                    archive.addfile(info, io.BytesIO(data))
            verifier._validate_sdist(sdist)

    def test_missing_runtime_resource_is_rejected_even_outside_smoke_path(self) -> None:
        omitted_members = (
            "semantic_guard_workflow/_resources/schemas/acceptance-review-bundle.schema.json",
            "semantic_guard_workflow/_resources/tests/fixtures/plans/good.expected.json",
            "semantic_guard_vnext/validation/env-path-contracts/local-environment-adoption.schema.json",
        )
        for missing in omitted_members:
            with self.subTest(missing=missing), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                members = verifier._ALLOWED_ADDITIONAL_RESOURCES - {missing}
                wheel = root / "candidate.whl"
                with zipfile.ZipFile(wheel, "w") as archive:
                    for member in members:
                        archive.writestr(member, "runtime")
                with self.assertRaises(verifier.VerificationFailure) as caught:
                    verifier._validate_wheel(wheel)
                self.assertEqual(caught.exception.code, "wheel_required_resource_missing")
                self.assertEqual(caught.exception.details["missing_resources"], [missing])
                sdist = root / "candidate.tar.gz"
                with tarfile.open(sdist, "w:gz") as archive:
                    for member in members:
                        data = b"runtime"
                        info = tarfile.TarInfo(verifier._CANONICAL_SDIST_ROOT + "/src/" + member)
                        info.size = len(data)
                        archive.addfile(info, io.BytesIO(data))
                with self.assertRaises(verifier.VerificationFailure) as caught:
                    verifier._validate_sdist(sdist)
                self.assertEqual(caught.exception.code, "sdist_required_resource_missing")
                self.assertEqual(caught.exception.details["missing_resources"], [missing])

    def test_added_namespace_resource_allowlist_rejects_plausible_leaks(self) -> None:
        forbidden_members = (
            "semantic_guard_workflow/_resources/docs/audits/internal.md",
            "semantic_guard_workflow/_resources/docs/conventions/internal.md",
            "semantic_guard_workflow/_resources/tests/test_local.py",
            "semantic_guard_workflow/_resources/tests/fixtures/private-history.json",
            "semantic_guard_workflow/_resources/schemas/unknown.schema.json",
            "semantic_guard_workflow/docs/internal.md",
            "semantic_guard_vnext/validation/local-contract-verification.json",
            "semantic_guard_vnext/validation/env-path-contracts/private-receipt.json",
            "semantic_guard_vnext/migration/baseline.json",
            "semantic_guard_vnext/__pycache__/core.pyc",
            "semantic_guard_u10_broker/validation/private-key.json",
        )
        for member in forbidden_members:
            with self.subTest(member=member), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                wheel = root / "candidate.whl"
                with zipfile.ZipFile(wheel, "w") as archive:
                    archive.writestr(member, "repository-only")
                with self.assertRaises(verifier.VerificationFailure) as caught:
                    verifier._validate_wheel(wheel)
                self.assertEqual(caught.exception.code, "wheel_distribution_boundary_violation")
                sdist = root / "candidate.tar.gz"
                with tarfile.open(sdist, "w:gz") as archive:
                    data = b"repository-only"
                    info = tarfile.TarInfo(verifier._CANONICAL_SDIST_ROOT + "/src/" + member)
                    info.size = len(data)
                    archive.addfile(info, io.BytesIO(data))
                with self.assertRaises(verifier.VerificationFailure) as caught:
                    verifier._validate_sdist(sdist)
                self.assertEqual(caught.exception.code, "sdist_distribution_boundary_violation")

    def test_fixed_resource_allowlist_matches_owned_source_resources(self) -> None:
        observed = set()
        for namespace, directories in (
            ("semantic_guard_workflow", ("_resources",)),
            ("semantic_guard_vnext", ("schemas", "constitution", "validation")),
        ):
            for directory in directories:
                observed.update(
                    path.relative_to(ROOT / "src").as_posix()
                    for path in (ROOT / "src" / namespace / directory).rglob("*")
                    if path.is_file() and "__pycache__" not in path.parts
                )
        self.assertEqual(observed, verifier._ALLOWED_ADDITIONAL_RESOURCES)

    def test_sdist_rejects_repository_only_archive_and_validation_history(self) -> None:
        forbidden_members = (
            "semantic_guard-1.2.0.dev0/legacy/semantic-guard-v0.1.0/README.md",
            "semantic_guard-1.2.0.dev0/docs/audits/internal.md",
            "semantic_guard-1.2.0.dev0/validation/local-contract-verification.json",
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

    def test_console_version_accepts_only_standard_line_endings(self) -> None:
        for stdout in (
            "semantic-guard 1.2.0.dev0\n",
            "semantic-guard 1.2.0.dev0\r\n",
        ):
            with self.subTest(stdout=repr(stdout)):
                self.assertTrue(verifier._is_exact_console_version_output(stdout))

        for stdout in (
            "semantic-guard 1.2.0.dev0",
            "semantic-guard 1.2.0.dev0\r",
            "semantic-guard 1.2.0.dev0\nextra\n",
            "semantic-guard 1.2.1\n",
        ):
            with self.subTest(stdout=repr(stdout)):
                self.assertFalse(verifier._is_exact_console_version_output(stdout))

    def test_clean_environment_preserves_windows_bootstrap_and_confines_user_paths(self) -> None:
        base = {
            "SystemRoot": r"C:\Windows",
            "WINDIR": r"C:\Windows",
            "USERPROFILE": r"C:\Users\runner",
            "TEMP": r"C:\Users\runner\Temp",
            "PYTHONPATH": r"D:\source",
            "pythonhome": r"C:\host-python",
            "https_proxy": "http://proxy.example.invalid:8080",
        }
        home = Path("controlled-home")
        temporary = Path("controlled-tmp")
        environment = verifier._clean_environment(
            home=home,
            temporary=temporary,
            executable_directory=Path("venv") / "Scripts",
            base_environment=base,
            os_name="nt",
        )

        self.assertEqual(environment["SYSTEMROOT"], r"C:\Windows")
        self.assertEqual(environment["WINDIR"], r"C:\Windows")
        for name in ("HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA"):
            self.assertEqual(environment[name], str(home))
        for name in ("TEMP", "TMP", "TMPDIR"):
            self.assertEqual(environment[name], str(temporary))
        self.assertNotIn("pythonpath", {name.casefold() for name in environment})
        self.assertNotIn("pythonhome", {name.casefold() for name in environment})
        self.assertEqual(environment["PYTHONIOENCODING"], "utf-8")
        self.assertEqual(environment["PYTHONUTF8"], "1")
        self.assertEqual(
            environment["HTTPS_PROXY"],
            "http://proxy.example.invalid:8080",
        )

    def test_public_arguments_cannot_select_executable_or_audit_program(self) -> None:
        destinations = {
            action.dest for action in verifier.build_parser()._actions
        }
        self.assertEqual(destinations, {"help", "wheel", "sdist", "binding_manifest", "timeout_seconds"})


class PackagedContractVerifierIntegrityTests(unittest.TestCase):
    def test_the_main_namespace_accepts_only_code_and_its_data_directories(self) -> None:
        stray = (
            "id_rsa", ".env", ".git/config", "audit-log.jsonl", "node_modules/x.js", "a:b.py", "secrets.txt",
            "schemas/nested/x.json", "schemas/notes.md", "constitution/key.pem", "module.pyc",
        )
        for relative in stray:
            parts = ("semantic_guard", *relative.split("/"))
            with self.subTest(member=relative):
                self.assertTrue(verifier._wheel_member_crosses_distribution_boundary(parts))
                self.assertTrue(verifier._sdist_member_crosses_distribution_boundary(("src", *parts)))
        for relative in ("__init__.py", "core.py", "py.typed", "schemas/audit-result.schema.json", "constitution/semantic-guard-constitution.yaml"):
            parts = ("semantic_guard", *relative.split("/"))
            with self.subTest(member=relative):
                self.assertFalse(verifier._wheel_member_crosses_distribution_boundary(parts))
                self.assertFalse(verifier._sdist_member_crosses_distribution_boundary(("src", *parts)))

    def test_top_level_sdist_data_directories_are_checked_too(self) -> None:
        self.assertTrue(verifier._sdist_member_crosses_distribution_boundary(("schemas", "id_rsa")))
        self.assertTrue(verifier._sdist_member_crosses_distribution_boundary(("constitution", "x.pem")))
        self.assertFalse(verifier._sdist_member_crosses_distribution_boundary(("schemas", "audit-result.schema.json")))

    def test_an_input_is_copied_once_and_hashed_while_copying(self) -> None:
        import hashlib

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = root / "pkg-1.0-py3-none-any.whl"
            original.write_bytes(b"first bytes")

            copy, digest = verifier._snapshot_input(
                original, root / "private", kind="wheel", suffix=".whl", maximum_bytes=1024
            )
            original.write_bytes(b"swapped after the copy")

            self.assertEqual(copy.read_bytes(), b"first bytes")
            self.assertEqual(digest, hashlib.sha256(b"first bytes").hexdigest())
            self.assertNotEqual(copy, original)
            self.assertEqual(copy.name, original.name)

    def test_a_symlink_or_oversized_input_is_not_copied(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "real.whl"
            target.write_bytes(b"x" * 10)
            link = root / "link.whl"
            link.symlink_to(target)

            with self.assertRaises(verifier.VerificationFailure) as symlink:
                verifier._snapshot_input(link, root / "a", kind="wheel", suffix=".whl", maximum_bytes=1024)
            with self.assertRaises(verifier.VerificationFailure) as large:
                verifier._snapshot_input(target, root / "b", kind="wheel", suffix=".whl", maximum_bytes=5)

            self.assertEqual(symlink.exception.code, "wheel_not_regular_file")
            self.assertEqual(large.exception.code, "wheel_size_out_of_bounds")

    def test_the_result_is_ascii_json_whatever_the_stdout_encoding(self) -> None:
        class Narrow(io.TextIOWrapper):
            pass

        buffer = io.BytesIO()
        stream = io.TextIOWrapper(buffer, encoding="cp1252", errors="strict")
        with redirect_stdout(stream):
            verifier._json_print({"message": "日本語のエラー", "status": "error"})
        stream.flush()

        self.assertEqual(json.loads(buffer.getvalue().decode("ascii")), {"message": "日本語のエラー", "status": "error"})

    def test_binding_manifest_digests_are_read_for_the_named_files_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "distribution-binding.json"
            manifest.write_text(
                json.dumps({"artifacts": [
                    {"kind": "wheel", "filename": "pkg-1-py3-none-any.whl", "sha256": "a" * 64},
                    {"kind": "sdist", "filename": "pkg-1.tar.gz", "sha256": "b" * 64},
                ]}),
                encoding="utf-8",
            )

            digests = verifier._expected_digests_from_binding(manifest, "pkg-1-py3-none-any.whl", "pkg-1.tar.gz")
            self.assertEqual(digests, {"wheel": "a" * 64, "sdist": "b" * 64})
            with self.assertRaises(verifier.VerificationFailure) as other:
                verifier._expected_digests_from_binding(manifest, "other-1-py3-none-any.whl", "pkg-1.tar.gz")
            self.assertEqual(other.exception.code, "binding_manifest_mismatch")

    def test_a_missing_or_malformed_binding_manifest_is_a_structured_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            broken = Path(directory) / "broken.json"
            broken.write_text("{not json", encoding="utf-8")
            for path in (broken, Path(directory) / "absent.json"):
                with self.subTest(path=path.name), self.assertRaises(verifier.VerificationFailure) as caught:
                    verifier._expected_digests_from_binding(path, "a.whl", "a.tar.gz")
                self.assertEqual(caught.exception.code, "binding_manifest_invalid")

    def test_the_cli_accepts_a_binding_manifest(self) -> None:
        arguments = verifier.build_parser().parse_args(
            ["--wheel", "a.whl", "--sdist", "a.tar.gz", "--binding-manifest", "dist/distribution-binding.json"]
        )

        self.assertEqual(arguments.binding_manifest, "dist/distribution-binding.json")

    def test_child_limits_are_reported_only_where_they_apply(self) -> None:
        self.assertEqual(verifier._child_limits_supported(), verifier.os.name == "posix")
        self.assertEqual(verifier._child_limit_function(5) is not None, verifier._child_limits_supported())


if __name__ == "__main__":
    unittest.main()
