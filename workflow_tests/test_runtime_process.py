"""Reviewer child-process mechanics exercised against fake executables."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from semantic_guard_workflow.runtime.process import MAX_OUTPUT_BYTES, run_agent_process
from semantic_guard_workflow.runtime.review import CodexExecReviewRequest, run_codex_exec_review
from workflow_tests.agent_fakes import ANSWER_VALID_REVIEW, POSIX, VALID_REVIEW, path_with, write_fake_agent

_DRIVER = """
import json
from semantic_guard_workflow import mcp_server

result = mcp_server.llm_review_run_tool({"candidate": "ascii", "request": "ascii"}, execute=True)
print(json.dumps({key: result[key] for key in ("execution_status", "valid", "errors")}))
"""


@unittest.skipUnless(POSIX, "fake agents are /bin/sh wrappers")
class LocaleIndependenceTests(unittest.TestCase):
    def test_ascii_locale_does_not_break_a_utf8_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bin_dir = Path(directory)
            write_fake_agent(bin_dir, "codex", ANSWER_VALID_REVIEW)
            env = {
                **os.environ,
                "PATH": path_with(bin_dir),
                "LC_ALL": "C",
                "LANG": "C",
                "PYTHONCOERCECLOCALE": "0",
                "PYTHONUTF8": "0",
            }
            env.pop("PYTHONIOENCODING", None)

            completed = subprocess.run(
                [sys.executable, "-c", _DRIVER], env=env, capture_output=True, text=True, check=False
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["execution_status"], "valid_review")


def _is_running(pid: int) -> bool:
    try:
        state = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8").rsplit(")", 1)[1].split()[0]
    except (OSError, IndexError):
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        return True
    return state != "Z"


def _wait_until_stopped(pid: int, seconds: float = 5.0) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if not _is_running(pid):
            return True
        time.sleep(0.05)
    return not _is_running(pid)


def _review_with_script(script: str, timeout_seconds: float) -> object:
    request = CodexExecReviewRequest.from_mapping(
        {"candidate": "c", "request": "r"},
        backend="command",
        agent_command=[sys.executable, "-c", script],
        timeout_seconds=timeout_seconds,
    )
    return run_codex_exec_review(request, execute=True)


_SLEEPING_DESCENDANT = "import subprocess, sys; subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])"


@unittest.skipUnless(POSIX, "process groups are POSIX only here")
class ProcessGroupTests(unittest.TestCase):
    def test_timeout_stops_descendants_of_the_agent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            pid_file = Path(directory) / "descendant.pid"
            script = (
                "import subprocess, sys, time\n"
                "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
                f"open({str(pid_file)!r}, 'w').write(str(child.pid))\n"
                "time.sleep(60)\n"
            )

            result = _review_with_script(script, timeout_seconds=2)

            self.assertEqual(result.execution_status, "timeout")
            self.assertTrue(result.timed_out)
            pid = int(pid_file.read_text(encoding="utf-8"))
            self.assertTrue(_wait_until_stopped(pid), "the descendant of the timed-out agent is still running")

    def test_finished_agent_is_not_reported_as_timeout_because_a_descendant_holds_the_pipe(self) -> None:
        script = f"{_SLEEPING_DESCENDANT}\nprint({json.dumps(VALID_REVIEW)!r})"

        started = time.monotonic()
        result = _review_with_script(script, timeout_seconds=20)
        elapsed = time.monotonic() - started

        self.assertEqual(result.execution_status, "valid_review", result.errors)
        self.assertFalse(result.timed_out)
        self.assertLess(elapsed, 10)

    def test_descendant_left_behind_by_a_finished_agent_is_stopped(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            pid_file = Path(directory) / "descendant.pid"
            script = (
                "import subprocess, sys\n"
                "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
                f"open({str(pid_file)!r}, 'w').write(str(child.pid))\n"
                f"print({json.dumps(VALID_REVIEW)!r})\n"
            )

            result = _review_with_script(script, timeout_seconds=20)

            self.assertEqual(result.execution_status, "valid_review", result.errors)
            pid = int(pid_file.read_text(encoding="utf-8"))
            self.assertTrue(_wait_until_stopped(pid), "a descendant of the finished agent is still running")

    def test_agent_runs_in_its_own_process_group(self) -> None:
        completed = run_agent_process(
            [sys.executable, "-c", "import os; print(os.getpgrp() == os.getpid())"], input="", timeout=10
        )

        self.assertEqual(completed.stdout.strip(), "True")


class RunAgentProcessTests(unittest.TestCase):
    def test_captures_text_and_exit_status(self) -> None:
        script = "import sys; sys.stdout.write(sys.stdin.read().upper()); sys.stderr.write('warn'); sys.exit(3)"

        completed = run_agent_process([sys.executable, "-c", script], input="あいう abc", timeout=10)

        self.assertEqual((completed.returncode, completed.stdout, completed.stderr), (3, "あいう ABC", "warn"))
        self.assertFalse(completed.stdout_truncated)
        self.assertFalse(completed.stderr_truncated)

    def test_invalid_utf8_from_the_child_is_replaced_not_raised(self) -> None:
        script = "import sys; sys.stdout.buffer.write(b'ok\\xff\\xfe')"

        completed = run_agent_process([sys.executable, "-c", script], input="", timeout=10)

        self.assertEqual(completed.stdout, "ok\ufffd\ufffd")

    def test_unpaired_surrogate_in_the_prompt_is_replaced_not_raised(self) -> None:
        completed = run_agent_process(
            [sys.executable, "-c", "import sys; sys.stdout.buffer.write(sys.stdin.buffer.read())"],
            input="a\ud800b",
            timeout=10,
        )

        self.assertEqual(completed.stdout, "a?b")

    def test_agent_that_ignores_stdin_does_not_hang_a_large_prompt(self) -> None:
        completed = run_agent_process([sys.executable, "-c", "pass"], input="x" * (4 * 1024 * 1024), timeout=20)

        self.assertEqual(completed.returncode, 0)

    def test_timeout_carries_the_partial_output(self) -> None:
        script = "import sys, time; print('partial', flush=True); sys.stderr.write('late'); sys.stderr.flush(); time.sleep(60)"

        with self.assertRaises(subprocess.TimeoutExpired) as raised:
            run_agent_process([sys.executable, "-c", script], input="", timeout=2)

        self.assertEqual(raised.exception.stdout.strip(), "partial")
        self.assertEqual(raised.exception.stderr, "late")

    def test_missing_executable_and_nul_bytes_raise_before_any_process_starts(self) -> None:
        with self.assertRaises(OSError):
            run_agent_process(["/nonexistent/semantic-guard-agent"], input="", timeout=5)
        with self.assertRaises(ValueError):
            run_agent_process([sys.executable, "a\x00b"], input="", timeout=5)

    def test_output_beyond_the_limit_is_cut_and_marked(self) -> None:
        script = "import sys; sys.stdout.write('o' * 6_000_000); sys.stderr.write('e' * 5_000_000)"

        completed = run_agent_process([sys.executable, "-c", script], input="", timeout=30)

        self.assertTrue(completed.stdout_truncated)
        self.assertTrue(completed.stderr_truncated)
        for stream, char in ((completed.stdout, "o"), (completed.stderr, "e")):
            body, marker = stream.split("\n[output truncated", 1)
            self.assertEqual(body, char * MAX_OUTPUT_BYTES)
            self.assertIn(f"first {MAX_OUTPUT_BYTES} bytes", marker)


class OutputLimitTests(unittest.TestCase):
    def test_oversized_stdout_is_an_explicit_truncation_failure(self) -> None:
        result = _review_with_script("import sys; sys.stdout.write('{' + ' ' * 6_000_000 + '}')", timeout_seconds=30)

        self.assertFalse(result.valid)
        self.assertEqual(result.execution_status, "invalid_review")
        self.assertEqual(result.failure_kind, "output_truncated")
        self.assertIn("stdout exceeded", result.errors[0])
        self.assertLess(len(result.stdout), MAX_OUTPUT_BYTES + 200)

    def test_oversized_stderr_is_cut_but_a_valid_review_stays_valid(self) -> None:
        script = f"import sys; sys.stderr.write('e' * 6_000_000); print({json.dumps(VALID_REVIEW)!r})"

        result = _review_with_script(script, timeout_seconds=30)

        self.assertTrue(result.valid, result.errors)
        self.assertIn("[output truncated", result.stderr)
        self.assertLess(len(result.stderr), MAX_OUTPUT_BYTES + 200)

    def test_oversized_output_from_an_injected_runner_is_bounded_too(self) -> None:
        def runner(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(command, 1, stdout="x" * (MAX_OUTPUT_BYTES + 10), stderr="")

        request = CodexExecReviewRequest.from_mapping({"candidate": "c", "request": "r"})
        result = run_codex_exec_review(request, execute=True, runner=runner)

        self.assertEqual(result.failure_kind, "non_zero_exit")
        self.assertIn("[output truncated", result.stdout)
        self.assertLess(len(result.stdout), MAX_OUTPUT_BYTES + 200)
        self.assertTrue(any("stdout exceeded" in error for error in result.errors))


if __name__ == "__main__":
    unittest.main()
