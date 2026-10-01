from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from semantic_guard_vnext.environment_resolution import file_digest
from semantic_guard_vnext.qualified_environment import (
    _verify_locked_environment_match_v1,
    render_dependency_lock_verifier_v1,
)


EXPECTED_COMMON_ENVIRONMENT = {
    "LC_ALL": "C",
    "NO_COLOR": "1",
    "PYTHONDONTWRITEBYTECODE": "1",
    "UV_NO_PROGRESS": "1",
    "UV_OFFLINE": "1",
    "UV_PYTHON_DOWNLOADS": "never",
}


class U10DependencyLockPathContractTests(unittest.TestCase):
    def test_snapshot_renderer_matches_closed_candidate_contract(self) -> None:
        invocation = Path("/snapshot/vnext/tools/uv")
        python = Path("/snapshot/vnext/.venv/bin/python")
        project = Path("/snapshot/vnext")

        rendered = render_dependency_lock_verifier_v1(
            invocation=invocation,
            python_invocation=python,
            project_root=project,
            candidate_source="repository_relative",
            selected_extras=["nlp-ja", "nlp-ja-dependency"],
        )

        expected_environment = {**EXPECTED_COMMON_ENVIRONMENT, "PATH": ""}
        self.assertEqual(
            rendered,
            {
                "verification_mode": "uv_sync_check_frozen_exact/v1",
                "version_probe": {
                    "argv": [str(invocation), "--version"],
                    "environment": expected_environment,
                },
                "lock_check": {
                    "cwd": str(project),
                    "argv": [
                        str(invocation),
                        "sync",
                        "--check",
                        "--offline",
                        "--frozen",
                        "--no-install-project",
                        "--python",
                        str(python),
                        "--extra",
                        "nlp-ja",
                        "--extra",
                        "nlp-ja-dependency",
                    ],
                    "environment": expected_environment,
                },
            },
        )

    def test_homebrew_renderer_derives_only_adopted_uv_directory(self) -> None:
        with patch.dict(
            os.environ,
            {"PATH": "/attacker/bin:/usr/bin:/bin"},
            clear=False,
        ):
            rendered = render_dependency_lock_verifier_v1(
                invocation=Path("/opt/homebrew/bin/uv"),
                python_invocation=Path("/qualified/.venv/bin/python"),
                project_root=Path("/qualified"),
                candidate_source="platform_install_name",
                selected_extras=[],
            )

        for operation in ("version_probe", "lock_check"):
            self.assertEqual(
                rendered[operation]["argv"][0],
                "/opt/homebrew/bin/uv",
            )
            self.assertEqual(
                rendered[operation]["environment"]["PATH"],
                "/opt/homebrew/bin",
            )
            self.assertNotIn("/usr/bin", rendered[operation]["environment"]["PATH"])
            self.assertNotIn("/attacker/bin", rendered[operation]["environment"]["PATH"])

    def test_fresh_pre_post_snapshot_checks_ignore_parent_path_and_fake_uv(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            project = root / "vnext"
            tools = project / "tools"
            tools.mkdir(parents=True)
            uv = tools / "uv"
            uv.write_bytes(b"snapshot uv executable\n")
            uv.chmod(0o755)
            python = project / ".venv" / "bin" / "python"
            python.parent.mkdir(parents=True)
            python.write_bytes(b"snapshot python executable\n")
            python.chmod(0o755)
            pyproject = project / "pyproject.toml"
            lock = project / "uv.lock"
            pyproject.write_text("[project]\nname='fixture'\n", encoding="utf-8")
            lock.write_text("version = 1\n", encoding="utf-8")
            fake_directory = root / "attacker"
            fake_directory.mkdir()
            fake_uv = fake_directory / "uv"
            fake_uv.write_text("#!/bin/sh\nexit 99\n", encoding="utf-8")
            fake_uv.chmod(0o755)

            contract = {
                "install_name": "snapshot.uv",
                "candidate_source": "repository_relative",
                "candidate_locator": "vnext/tools/uv",
                "version_constraint": {"exact": "0.10.10"},
                "digest_constraint": {
                    "policy": "exact",
                    "digest": file_digest(uv),
                },
                "selected_extras": ["nlp-ja", "nlp-ja-dependency"],
            }
            lock_bindings = [
                {"path": "vnext/pyproject.toml", "resolved_path": str(pyproject)},
                {"path": "vnext/uv.lock", "resolved_path": str(lock)},
            ]
            calls: list[dict[str, object]] = []

            def completed(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
                calls.append({"argv": list(argv), **kwargs})
                if argv[1:] == ["--version"]:
                    return subprocess.CompletedProcess(
                        argv,
                        0,
                        stdout="uv 0.10.10\n",
                        stderr="",
                    )
                return subprocess.CompletedProcess(
                    argv,
                    0,
                    stdout="Checked 42 packages\nWould make no changes\n",
                    stderr="",
                )

            with patch(
                "semantic_guard_vnext.qualified_environment.subprocess.run",
                side_effect=completed,
            ):
                with patch.dict(os.environ, {"PATH": str(fake_directory)}, clear=False):
                    pre = _verify_locked_environment_match_v1(
                        contract,
                        python_invocation=python,
                        lock_bindings=lock_bindings,
                        repository_root=root,
                    )
                with patch.dict(
                    os.environ,
                    {"PATH": f"{root / 'other-attacker'}:/usr/bin"},
                    clear=False,
                ):
                    post = _verify_locked_environment_match_v1(
                        contract,
                        python_invocation=python,
                        lock_bindings=lock_bindings,
                        repository_root=root,
                    )

            self.assertEqual(pre, post)
            self.assertEqual(calls[:2], calls[2:])
            for call in calls:
                argv = call["argv"]
                environment = call["env"]
                self.assertEqual(argv[0], str(uv))
                self.assertNotEqual(argv[0], str(fake_uv))
                self.assertEqual(environment["PATH"], "")
                self.assertEqual(environment["UV_OFFLINE"], "1")
                self.assertEqual(environment["UV_PYTHON_DOWNLOADS"], "never")
            self.assertEqual(
                pre["command"],
                [
                    str(uv),
                    "sync",
                    "--check",
                    "--offline",
                    "--frozen",
                    "--no-install-project",
                    "--python",
                    str(python),
                    "--extra",
                    "nlp-ja",
                    "--extra",
                    "nlp-ja-dependency",
                ],
            )


if __name__ == "__main__":
    unittest.main()
