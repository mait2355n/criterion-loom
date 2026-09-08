from __future__ import annotations

from contextlib import redirect_stdout
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "distribution_binding.py"
SPEC = importlib.util.spec_from_file_location("distribution_binding", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
binding = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = binding
SPEC.loader.exec_module(binding)

COMMIT = "a" * 40
TREE = "b" * 40
WHEEL_NAME = "semantic_guard-1.1.0-py3-none-any.whl"
SDIST_NAME = "semantic_guard-1.1.0.tar.gz"
WHEEL_BYTES = b"fixed wheel fixture\n"
SDIST_BYTES = b"fixed source fixture\n"


def write_fixture(root: Path) -> Path:
    (root / "pyproject.toml").write_text(
        "[project]\nname = 'semantic-guard'\nversion = '1.1.0'\n",
        encoding="utf-8",
    )
    dist = root / "dist"
    dist.mkdir()
    (dist / WHEEL_NAME).write_bytes(WHEEL_BYTES)
    (dist / SDIST_NAME).write_bytes(SDIST_BYTES)
    return dist


def create_fixture_binding(root: Path, dist: Path) -> dict[str, object]:
    return binding.create_binding(
        root,
        dist,
        source_commit=COMMIT,
        source_tree=TREE,
    )


class DistributionBindingTests(unittest.TestCase):
    def test_create_and_check_match_an_independent_fixed_bytes_oracle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dist = write_fixture(root)

            result = create_fixture_binding(root, dist)

            wheel_digest = hashlib.sha256(WHEEL_BYTES).hexdigest()
            sdist_digest = hashlib.sha256(SDIST_BYTES).hexdigest()
            expected_manifest = {
                "schema_version": binding.SCHEMA_VERSION,
                "project": {"name": "semantic-guard", "version": "1.1.0"},
                "source": {
                    "commit": {"algorithm": "git-sha1", "value": COMMIT},
                    "tree": {"algorithm": "git-sha1", "value": TREE},
                    "tracked_worktree": "clean",
                },
                "artifacts": [
                    {
                        "kind": "sdist",
                        "filename": SDIST_NAME,
                        "sha256": sdist_digest,
                        "size_bytes": len(SDIST_BYTES),
                    },
                    {
                        "kind": "wheel",
                        "filename": WHEEL_NAME,
                        "sha256": wheel_digest,
                        "size_bytes": len(WHEEL_BYTES),
                    },
                ],
                "limitations": list(binding._LIMITATIONS),
            }
            expected_manifest_bytes = (
                json.dumps(expected_manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
            ).encode("utf-8")
            expected_checksums = "".join(
                f"{digest}  {filename}\n"
                for filename, digest in sorted(
                    (
                        (WHEEL_NAME, wheel_digest),
                        (SDIST_NAME, sdist_digest),
                        (
                            binding.MANIFEST_FILENAME,
                            hashlib.sha256(expected_manifest_bytes).hexdigest(),
                        ),
                    )
                )
            )
            self.assertEqual(
                (dist / binding.MANIFEST_FILENAME).read_bytes(),
                expected_manifest_bytes,
            )
            self.assertEqual(
                (dist / binding.CHECKSUMS_FILENAME).read_text(encoding="utf-8"),
                expected_checksums,
            )
            self.assertEqual(result["status"], "pass")
            self.assertEqual(
                binding.check_binding(
                    root,
                    dist,
                    source_commit=COMMIT,
                    source_tree=TREE,
                )["status"],
                "pass",
            )

    def test_create_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dist = write_fixture(root)
            create_fixture_binding(root, dist)
            first = (
                (dist / binding.MANIFEST_FILENAME).read_bytes(),
                (dist / binding.CHECKSUMS_FILENAME).read_bytes(),
            )

            create_fixture_binding(root, dist)

            second = (
                (dist / binding.MANIFEST_FILENAME).read_bytes(),
                (dist / binding.CHECKSUMS_FILENAME).read_bytes(),
            )
            self.assertEqual(second, first)

    def test_artifact_tamper_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dist = write_fixture(root)
            create_fixture_binding(root, dist)
            tampered = bytearray(WHEEL_BYTES)
            tampered[0] ^= 1
            (dist / WHEEL_NAME).write_bytes(tampered)

            with self.assertRaises(binding.BindingFailure) as caught:
                binding.check_binding(root, dist, source_commit=COMMIT, source_tree=TREE)

            self.assertEqual(caught.exception.code, "manifest_mismatch")

    def test_commit_and_tree_mismatch_are_rejected(self) -> None:
        for label, commit, tree in (
            ("commit", "c" * 40, TREE),
            ("tree", COMMIT, "d" * 40),
        ):
            with self.subTest(label=label), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                dist = write_fixture(root)
                create_fixture_binding(root, dist)
                with self.assertRaises(binding.BindingFailure) as caught:
                    binding.check_binding(root, dist, source_commit=commit, source_tree=tree)
                self.assertEqual(caught.exception.code, "manifest_mismatch")

    def test_manifest_project_identity_tamper_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dist = write_fixture(root)
            create_fixture_binding(root, dist)
            manifest_path = dist / binding.MANIFEST_FILENAME
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["project"]["version"] = "9.9.9"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            with self.assertRaises(binding.BindingFailure) as caught:
                binding.check_binding(root, dist, source_commit=COMMIT, source_tree=TREE)

            self.assertEqual(caught.exception.code, "manifest_mismatch")

    def test_missing_and_duplicate_artifacts_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dist = write_fixture(root)
            (dist / SDIST_NAME).unlink()
            with self.assertRaises(binding.BindingFailure) as caught:
                create_fixture_binding(root, dist)
            self.assertEqual(caught.exception.code, "artifact_count_invalid")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dist = write_fixture(root)
            (dist / "semantic_guard-1.1.0-1-py3-none-any.whl").write_bytes(b"duplicate")
            with self.assertRaises(binding.BindingFailure) as caught:
                create_fixture_binding(root, dist)
            self.assertEqual(caught.exception.code, "artifact_count_invalid")

    def test_unexpected_distribution_member_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dist = write_fixture(root)
            (dist / "unbound-note.txt").write_text("not part of the bundle", encoding="utf-8")

            with self.assertRaises(binding.BindingFailure) as caught:
                create_fixture_binding(root, dist)

            self.assertEqual(caught.exception.code, "artifact_set_invalid")

    def test_malformed_manifest_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dist = write_fixture(root)
            create_fixture_binding(root, dist)
            (dist / binding.MANIFEST_FILENAME).write_text("{", encoding="utf-8")

            with self.assertRaises(binding.BindingFailure) as caught:
                binding.check_binding(root, dist, source_commit=COMMIT, source_tree=TREE)

            self.assertEqual(caught.exception.code, "manifest_json_invalid")

    def test_duplicate_manifest_key_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dist = write_fixture(root)
            create_fixture_binding(root, dist)
            manifest_path = dist / binding.MANIFEST_FILENAME
            manifest_text = manifest_path.read_text(encoding="utf-8")
            manifest_path.write_text(
                manifest_text.replace(
                    '"schema_version": "semantic-guard-distribution-binding/v0",',
                    '"schema_version": "semantic-guard-distribution-binding/v0",\n'
                    '  "schema_version": "semantic-guard-distribution-binding/v0",',
                    1,
                ),
                encoding="utf-8",
            )

            with self.assertRaises(binding.BindingFailure) as caught:
                binding.check_binding(root, dist, source_commit=COMMIT, source_tree=TREE)

            self.assertEqual(caught.exception.code, "manifest_json_invalid")

    def test_checksum_sidecar_tamper_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dist = write_fixture(root)
            create_fixture_binding(root, dist)
            checksums_path = dist / binding.CHECKSUMS_FILENAME
            checksums_path.write_text("0" * 64 + "  forged.whl\n", encoding="utf-8")

            with self.assertRaises(binding.BindingFailure) as caught:
                binding.check_binding(root, dist, source_commit=COMMIT, source_tree=TREE)

            self.assertEqual(caught.exception.code, "checksums_mismatch")

    def test_symlink_artifact_and_sidecar_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dist = write_fixture(root)
            wheel = dist / WHEEL_NAME
            target = root / "wheel-target"
            target.write_bytes(wheel.read_bytes())
            wheel.unlink()
            wheel.symlink_to(target)
            with self.assertRaises(binding.BindingFailure) as caught:
                create_fixture_binding(root, dist)
            self.assertEqual(caught.exception.code, "artifact_unavailable")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dist = write_fixture(root)
            target = root / "manifest-target"
            target.write_text("target", encoding="utf-8")
            (dist / binding.MANIFEST_FILENAME).symlink_to(target)
            with self.assertRaises(binding.BindingFailure) as caught:
                create_fixture_binding(root, dist)
            self.assertEqual(caught.exception.code, "sidecar_path_invalid")

    def test_unsafe_manifest_filename_is_rejected_before_comparison(self) -> None:
        for unsafe in ("../escape.tar.gz", "white space.tar.gz", "制御.tar.gz", "line\n.tar.gz"):
            with self.subTest(filename=unsafe), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                dist = write_fixture(root)
                create_fixture_binding(root, dist)
                manifest_path = dist / binding.MANIFEST_FILENAME
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                manifest["artifacts"][0]["filename"] = unsafe
                manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

                with self.assertRaises(binding.BindingFailure) as caught:
                    binding.check_binding(root, dist, source_commit=COMMIT, source_tree=TREE)

                self.assertEqual(caught.exception.code, "unsafe_filename")

    def test_project_version_drift_rejects_old_artifact_names(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dist = write_fixture(root)
            create_fixture_binding(root, dist)
            (root / "pyproject.toml").write_text(
                "[project]\nname = 'semantic-guard'\nversion = '1.2.0'\n",
                encoding="utf-8",
            )

            with self.assertRaises(binding.BindingFailure) as caught:
                binding.check_binding(root, dist, source_commit=COMMIT, source_tree=TREE)

            self.assertEqual(caught.exception.code, "artifact_name_mismatch")

    def test_cli_error_is_one_json_value_and_nonzero(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            status = binding.main(
                [
                    "check",
                    "--project-root",
                    "/definitely/missing",
                    "--dist-dir",
                    "/definitely/missing/dist",
                ]
            )
        payload = json.loads(output.getvalue())
        self.assertEqual(status, 1)
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["errors"][0]["code"], "unexpected_binding_error")

    def test_cli_binds_clean_git_head_and_rejects_tracked_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dist = write_fixture(root)
            (root / ".gitignore").write_text("dist/\n", encoding="utf-8")
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            subprocess.run(
                ["git", "-C", str(root), "config", "user.name", "Binding Test"],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(root), "config", "user.email", "binding@example.invalid"],
                check=True,
            )
            subprocess.run(["git", "-C", str(root), "add", "."], check=True)
            subprocess.run(
                ["git", "-C", str(root), "commit", "-q", "-m", "fixture"],
                check=True,
            )
            commit = subprocess.run(
                ["git", "-C", str(root), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()

            output = io.StringIO()
            with redirect_stdout(output):
                status = binding.main(
                    [
                        "create",
                        "--project-root",
                        str(root),
                        "--dist-dir",
                        str(dist),
                        "--expected-commit",
                        commit,
                    ]
                )
            self.assertEqual(status, 0)
            self.assertEqual(json.loads(output.getvalue())["status"], "pass")

            output = io.StringIO()
            with redirect_stdout(output):
                status = binding.main(
                    [
                        "check",
                        "--project-root",
                        str(root),
                        "--dist-dir",
                        str(dist),
                        "--expected-commit",
                        "c" * 40,
                    ]
                )
            payload = json.loads(output.getvalue())
            self.assertEqual(status, 1)
            self.assertEqual(payload["errors"][0]["code"], "expected_commit_mismatch")

            (root / "pyproject.toml").write_text(
                "[project]\nname = 'semantic-guard'\nversion = '1.1.1'\n",
                encoding="utf-8",
            )
            output = io.StringIO()
            with redirect_stdout(output):
                status = binding.main(
                    [
                        "check",
                        "--project-root",
                        str(root),
                        "--dist-dir",
                        str(dist),
                        "--expected-commit",
                        commit,
                    ]
                )
            payload = json.loads(output.getvalue())
            self.assertEqual(status, 1)
            self.assertEqual(payload["errors"][0]["code"], "git_worktree_dirty")


if __name__ == "__main__":
    unittest.main()
