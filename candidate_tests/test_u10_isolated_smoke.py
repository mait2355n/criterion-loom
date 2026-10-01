from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
RUNNER = (Path(__file__).parent / "fixtures/scripts/governed_test_runner_bootstrap.py").resolve()
SMOKE_SOURCE = (
    REPOSITORY_ROOT / "src/semantic_guard_vnext/u10_containment_smoke.py"
).resolve()
ISOLATED_MODULE = "semantic_guard_u10_isolated_smoke"
EXPECTED_IDS = [
    f"{ISOLATED_MODULE}.U10ContainmentSmokeTests.test_direct_fork_is_denied_by_kernel_policy",
    f"{ISOLATED_MODULE}.U10ContainmentSmokeTests.test_subprocess_creation_is_denied_by_kernel_policy",
]


@unittest.skipUnless(
    sys.platform == "darwin" and Path("/usr/bin/sandbox-exec").is_file(),
    "U-10 containment runner requires macOS sandbox-exec",
)
class U10IsolatedSmokeRunnerTests(unittest.TestCase):
    def _run(
        self,
        source: Path,
        expected_ids: list[str],
        *,
        module_name: str = ISOLATED_MODULE,
        source_digest: str | None = None,
    ) -> tuple[subprocess.CompletedProcess[bytes], list[dict[str, object]]]:
        python = Path(sys.executable).resolve(strict=True)
        exact_source = source.resolve(strict=True)
        digest = source_digest or hashlib.sha256(exact_source.read_bytes()).hexdigest()
        sandbox_profile = (
            "(version 1)(allow default)(deny file-write*)"
            "(deny process-fork)(deny process-exec)"
            f'(allow process-exec (literal "{python}"))'
        )
        argv = [
            "/usr/bin/sandbox-exec",
            "-p",
            sandbox_profile,
            str(python),
            "-I",
            "-S",
            str(RUNNER),
            "--test-source-file",
            str(exact_source),
            "--test-source-digest",
            digest,
            "--test-module-name",
            module_name,
        ]
        for test_id in expected_ids:
            argv.extend(["--expected-test-id", test_id])
        read_fd, write_fd = os.pipe()
        environment = {
            "PATH": "/usr/bin:/bin",
            "SEMANTIC_GUARD_TRACE_FD": str(write_fd),
            "SEMANTIC_GUARD_EXECUTION_NONCE": "1" * 64,
            "SEMANTIC_GUARD_COMMAND_DIGEST": "2" * 64,
            "SEMANTIC_GUARD_SUBJECT_MANIFEST_DIGEST": "3" * 64,
        }
        try:
            completed = subprocess.run(
                argv,
                cwd=REPOSITORY_ROOT,
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                pass_fds=(write_fd,),
                timeout=30,
            )
            os.close(write_fd)
            write_fd = -1
            raw_trace = b""
            while block := os.read(read_fd, 65536):
                raw_trace += block
        finally:
            if write_fd >= 0:
                os.close(write_fd)
            os.close(read_fd)
        records = [json.loads(line) for line in raw_trace.splitlines()]
        return completed, records

    def test_exact_file_runs_only_two_tests_without_subject_import_root(self) -> None:
        completed, records = self._run(SMOKE_SOURCE, EXPECTED_IDS)

        self.assertEqual(completed.returncode, 0, completed.stderr.decode())
        started = next(item for item in records if item["event"] == "runner_started")
        self.assertNotIn("subject_import_roots", started)
        self.assertNotIn("targets", started)
        verified = next(
            item for item in records if item["event"] == "test_source_verified"
        )
        self.assertEqual(
            verified["test_source_binding"]["source_file"], str(SMOKE_SOURCE)
        )
        self.assertEqual(
            verified["test_source_binding"]["source_digest"],
            hashlib.sha256(SMOKE_SOURCE.read_bytes()).hexdigest(),
        )
        completed_record = next(
            item for item in records if item["event"] == "test_run_completed"
        )
        self.assertEqual(completed_record["tests_run"], 2)
        self.assertEqual(completed_record["test_ids"], EXPECTED_IDS)

    def test_digest_mismatch_rejects_source_before_test_discovery(self) -> None:
        completed, records = self._run(
            SMOKE_SOURCE, EXPECTED_IDS, source_digest="0" * 64
        )

        self.assertEqual(completed.returncode, 78)
        self.assertIn("test_source_rejected", {item["event"] for item in records})
        self.assertNotIn("test_run_completed", {item["event"] for item in records})

    def test_zero_extra_and_missing_denominators_are_rejected(self) -> None:
        cases = {
            "zero": [],
            "extra_loaded": EXPECTED_IDS[:1],
            "missing_loaded": [*EXPECTED_IDS, f"{ISOLATED_MODULE}.missing_test"],
        }
        for name, expected_ids in cases.items():
            with self.subTest(name=name):
                completed, records = self._run(SMOKE_SOURCE, expected_ids)
                self.assertEqual(completed.returncode, 78)
                self.assertIn(
                    "test_denominator_mismatch",
                    {item["event"] for item in records},
                )
                self.assertNotIn(
                    "test_run_completed", {item["event"] for item in records}
                )

    def test_all_skipped_denominator_is_not_success(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "all_skipped.py"
            source.write_text(
                "import unittest\n"
                "class Smoke(unittest.TestCase):\n"
                "    @unittest.skip('fixture')\n"
                "    def test_skipped(self):\n"
                "        pass\n",
                encoding="utf-8",
            )
            completed, records = self._run(
                source,
                ["isolated_all_skip.Smoke.test_skipped"],
                module_name="isolated_all_skip",
            )

        self.assertEqual(completed.returncode, 1)
        record = next(item for item in records if item["event"] == "test_run_completed")
        self.assertEqual(record["tests_run"], 1)
        self.assertEqual(record["skipped"], 1)
        self.assertIs(record["successful"], False)

    def test_partially_skipped_denominator_is_not_success(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "partially_skipped.py"
            source.write_text(
                "import unittest\n"
                "class Smoke(unittest.TestCase):\n"
                "    def test_executed(self):\n"
                "        pass\n"
                "    @unittest.skip('fixture')\n"
                "    def test_skipped(self):\n"
                "        pass\n",
                encoding="utf-8",
            )
            expected_ids = [
                "isolated_partial_skip.Smoke.test_executed",
                "isolated_partial_skip.Smoke.test_skipped",
            ]
            completed, records = self._run(
                source,
                expected_ids,
                module_name="isolated_partial_skip",
            )

        self.assertEqual(completed.returncode, 1)
        record = next(item for item in records if item["event"] == "test_run_completed")
        self.assertEqual(record["tests_run"], 2)
        self.assertEqual(record["skipped"], 1)
        self.assertEqual(record["test_ids"], expected_ids)
        self.assertIs(record["successful"], False)


if __name__ == "__main__":
    unittest.main()
