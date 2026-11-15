"""Reviewer option validation: timeouts, argument values and working directories."""

from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Callable
from unittest.mock import patch

from semantic_guard_workflow import mcp_server
from semantic_guard_workflow.cli import main
from semantic_guard_workflow.runtime.backends import (
    MAX_TIMEOUT_SECONDS,
    WORKDIR_ROOTS_ENV,
    build_agent_command,
    mcp_working_directory_roots,
    resolve_mcp_working_directory,
    resolve_working_directory,
    validate_timeout_seconds,
)
from semantic_guard_workflow.runtime.exploration import CodexExecExplorationRequest
from semantic_guard_workflow.runtime.review import CodexExecReviewRequest, run_codex_exec_review
from workflow_tests.agent_fakes import POSIX

PAYLOAD = {"candidate": "要求: 画面をいい感じに速くする。", "phase": "audit_request"}
# Escalation is not needed here, so only up-front validation can reject the call.
NOT_NEEDED_PAYLOAD = {
    "candidate": "要求: 利用者: 保守者。目的: 設定を保存する。受入基準: 設定が保存される。",
    "phase": "audit_request",
    "deterministic_audit": {"phase": "audit_request", "status": "pass", "score": 1.0, "findings": []},
}
IDEA = "割り勘アプリを作りたい"

Tool = Callable[..., dict[str, Any]]
TOOLS: dict[str, Tool] = {
    "llm_review_command_tool": lambda **kw: mcp_server.llm_review_command_tool(PAYLOAD, **kw),
    "llm_review_run_tool": lambda **kw: mcp_server.llm_review_run_tool(PAYLOAD, execute=True, **kw),
    "llm_review_start_tool": lambda **kw: mcp_server.llm_review_start_tool(PAYLOAD, **kw),
    "review_if_needed_tool": lambda **kw: mcp_server.review_if_needed_tool(NOT_NEEDED_PAYLOAD, execute=True, **kw),
    "review_if_needed_start_tool": lambda **kw: mcp_server.review_if_needed_start_tool(NOT_NEEDED_PAYLOAD, **kw),
    "llm_explore_request_tool": lambda **kw: mcp_server.llm_explore_request_tool(IDEA, execute=True, **kw),
    "llm_explore_request_start_tool": lambda **kw: mcp_server.llm_explore_request_start_tool(IDEA, **kw),
}


def _input_error_of(result: dict[str, Any]) -> dict[str, Any] | None:
    """The part of a tool result that reports an input error, if it does."""
    for candidate in (result, result.get("review_result") or {}):
        if candidate.get("execution_status") == "input_error" or candidate.get("state") == "input_error":
            return candidate
    return None


@contextlib.contextmanager
def _no_process_may_start():
    with (
        patch("semantic_guard_workflow.runtime.process.subprocess.Popen") as popen,
        patch("semantic_guard_workflow.runtime.codex_exec.subprocess.run") as run,
    ):
        yield
    popen.assert_not_called()
    run.assert_not_called()


class TimeoutValidationTests(unittest.TestCase):
    def test_only_a_positive_finite_bounded_number_is_a_timeout(self) -> None:
        for value in (1, 30, 180, 0.5, MAX_TIMEOUT_SECONDS):
            with self.subTest(accepted=value):
                validate_timeout_seconds(value)
        for value in (0, -1, -0.5, MAX_TIMEOUT_SECONDS + 1, 10**9, float("inf"), float("nan"), True, False, None, "5"):
            with self.subTest(rejected=value), self.assertRaisesRegex(ValueError, "timeout_seconds"):
                validate_timeout_seconds(value)

    def test_requests_reject_a_bad_timeout_at_construction(self) -> None:
        for value in (0, -3, 10**9, float("nan")):
            with self.subTest(timeout=value):
                with self.assertRaisesRegex(ValueError, "timeout_seconds"):
                    CodexExecReviewRequest.from_mapping(PAYLOAD, timeout_seconds=value)
                with self.assertRaisesRegex(ValueError, "timeout_seconds"):
                    CodexExecExplorationRequest.from_mapping({"text": IDEA}, timeout_seconds=value)

    def test_every_mcp_llm_tool_rejects_a_bad_timeout_without_starting_anything(self) -> None:
        for name, tool in TOOLS.items():
            for value in (0, -3, 10**9):
                with self.subTest(tool=name, timeout=value), _no_process_may_start():
                    error = _input_error_of(tool(timeout_seconds=value))

                    self.assertIsNotNone(error)
                    self.assertIn("timeout_seconds", " ".join(error["errors"]))

    def test_cli_rejects_a_bad_timeout_for_every_reviewer_command(self) -> None:
        review = json.dumps(PAYLOAD, ensure_ascii=False)
        needless = json.dumps(NOT_NEEDED_PAYLOAD, ensure_ascii=False)
        commands = {
            "llm-review-command": ["--text", review],
            "llm-review-run": ["--text", review, "--execute"],
            "review-if-needed": ["--text", needless, "--execute"],
        }
        for name, arguments in commands.items():
            for value, message in (("0", "must be positive"), ("-3", "must be positive"), ("3601", "must be at most")):
                with self.subTest(command=name, timeout=value), _no_process_may_start():
                    stderr = io.StringIO()
                    with patch.object(sys, "argv", ["semantic-guard", name, *arguments, "--timeout-seconds", value]):
                        with self.assertRaises(SystemExit) as raised, patch("sys.stderr", stderr):
                            main()

                    self.assertEqual(raised.exception.code, 2)
                    self.assertIn(f"--timeout-seconds {message}", stderr.getvalue())

    def test_cli_exploration_reports_a_bad_timeout_as_structured_input_error(self) -> None:
        stdout = io.StringIO()
        argv = ["semantic-guard", "llm-explore-request", "--text", IDEA, "--timeout-seconds", "0", "--execute"]
        with _no_process_may_start(), patch.object(sys, "argv", argv), contextlib.redirect_stdout(stdout):
            with self.assertRaises(SystemExit) as raised:
                main()

        self.assertEqual(raised.exception.code, 1)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["execution_status"], "input_error")
        self.assertEqual(payload["errors"], ["--timeout-seconds must be positive"])


class ArgumentValueTests(unittest.TestCase):
    def test_nul_and_control_characters_are_input_errors_not_exceptions(self) -> None:
        cases = {
            "model_nul": {"model": "a\x00b"},
            "model_newline": {"model": "a\nb"},
            "model_option_like": {"model": "--dangerously-skip-permissions"},
            "working_directory_nul": {"working_directory": "/tmp/a\x00b"},
        }
        for name, tool in TOOLS.items():
            for case, options in cases.items():
                with self.subTest(tool=name, case=case), _no_process_may_start():
                    self.assertIsNotNone(_input_error_of(tool(**options)))

    def test_requests_reject_values_that_cannot_be_process_arguments(self) -> None:
        for options in (
            {"model": "a\x00b"},
            {"working_directory": "a\x00b"},
            {"agent_binary": "a\x00b"},
            {"model": "\udcff\ud800"},
        ):
            with self.subTest(options=options), self.assertRaises(ValueError):
                CodexExecReviewRequest.from_mapping(PAYLOAD, **options)
        with self.assertRaises(ValueError):
            CodexExecReviewRequest.from_mapping(
                PAYLOAD, backend="command", agent_command=["agent", "a\x00b"]
            )

    def test_a_value_that_still_reaches_the_runner_becomes_execution_error(self) -> None:
        request = CodexExecReviewRequest.from_mapping(
            PAYLOAD, backend="command", agent_command=[sys.executable, "-c", "pass"]
        )
        # Bypass construction-time validation to prove the runtime boundary is structured too.
        object.__setattr__(request, "agent_command", (sys.executable, "-c", "a\x00b"))

        result = run_codex_exec_review(request, execute=True)

        self.assertEqual(result.execution_status, "execution_error")
        self.assertEqual(result.failure_kind, "execution_error")

    def test_cli_rejects_nul_in_model_before_starting_anything(self) -> None:
        for name, extra in (("llm-review-run", ["--execute"]), ("review-if-needed", ["--execute"])):
            with self.subTest(command=name), _no_process_may_start():
                stderr = io.StringIO()
                text = json.dumps(PAYLOAD if name == "llm-review-run" else NOT_NEEDED_PAYLOAD, ensure_ascii=False)
                argv = ["semantic-guard", name, "--text", text, "--model", "a\x00b", *extra]
                with patch.object(sys, "argv", argv), self.assertRaises(SystemExit) as raised, patch("sys.stderr", stderr):
                    main()

                self.assertEqual(raised.exception.code, 2)
                self.assertNotIn("Traceback", stderr.getvalue())


class WorkingDirectoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary.cleanup)
        self.root = Path(self._temporary.name).resolve()
        (self.root / "project" / "sub").mkdir(parents=True)
        (self.root / "elsewhere").mkdir()

    def test_resolution_returns_the_real_path_of_an_existing_directory(self) -> None:
        sub = self.root / "project" / "sub"
        link = self.root / "link"
        if POSIX:
            link.symlink_to(sub, target_is_directory=True)

        self.assertEqual(resolve_working_directory(str(sub)), str(sub))
        self.assertEqual(resolve_working_directory(sub), str(sub))
        self.assertEqual(resolve_working_directory(str(sub / ".." / "sub")), str(sub))
        if POSIX:
            self.assertEqual(resolve_working_directory(str(link)), str(sub))
        with contextlib.chdir(self.root / "project"):
            self.assertEqual(resolve_working_directory("sub"), str(sub))
        self.assertIsNone(resolve_working_directory(None))
        self.assertIsNone(resolve_working_directory(""))

    def test_resolution_rejects_missing_non_directory_and_nul(self) -> None:
        a_file = self.root / "file.txt"
        a_file.write_text("x", encoding="utf-8")
        for value, message in (
            (str(self.root / "missing"), "does not exist"),
            (str(a_file), "not a directory"),
            (str(a_file / "below"), "does not exist"),
            ("a\x00b", "NUL"),
        ):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, message):
                resolve_working_directory(value)

    def test_allowed_roots_contain_the_directory_or_reject_it(self) -> None:
        project = self.root / "project"
        sub = project / "sub"
        elsewhere = self.root / "elsewhere"

        self.assertEqual(resolve_working_directory(str(project), allowed_roots=[project]), str(project))
        self.assertEqual(resolve_working_directory(str(sub), allowed_roots=[project]), str(sub))
        for outside in (elsewhere, project / ".." / "elsewhere", self.root):
            with self.subTest(outside=outside), self.assertRaisesRegex(ValueError, "outside"):
                resolve_working_directory(str(outside), allowed_roots=[project])
        with self.assertRaisesRegex(ValueError, "outside"):
            resolve_working_directory(str(sub), allowed_roots=[])

    @unittest.skipUnless(POSIX, "symlinks")
    def test_a_symlink_inside_the_root_cannot_lead_outside_it(self) -> None:
        project = self.root / "project"
        (project / "escape").symlink_to(self.root / "elsewhere", target_is_directory=True)

        with self.assertRaisesRegex(ValueError, "outside"):
            resolve_working_directory(str(project / "escape"), allowed_roots=[project])

    def test_mcp_roots_are_the_current_directory_and_the_environment_list(self) -> None:
        project = self.root / "project"
        elsewhere = self.root / "elsewhere"
        listed = os.pathsep.join([str(elsewhere), "", str(self.root / "missing")])
        with contextlib.chdir(project):
            self.assertEqual(mcp_working_directory_roots({}), [project])
            self.assertEqual(mcp_working_directory_roots({WORKDIR_ROOTS_ENV: listed}), [project, elsewhere])
            self.assertEqual(resolve_mcp_working_directory(str(elsewhere), {WORKDIR_ROOTS_ENV: listed}), str(elsewhere))
            with self.assertRaisesRegex(ValueError, "outside"):
                resolve_mcp_working_directory(str(elsewhere), {})
            self.assertIsNone(resolve_mcp_working_directory("", {}))

    def test_mcp_tools_accept_a_directory_under_the_server_cwd(self) -> None:
        project = self.root / "project"
        with contextlib.chdir(project), patch.dict(os.environ, {WORKDIR_ROOTS_ENV: ""}):
            for value in ("sub", str(project / "sub")):
                with self.subTest(value=value):
                    result = mcp_server.llm_review_command_tool(PAYLOAD, working_directory=value)

                    self.assertEqual(result["execution_status"], "dry_run")
                    command = result["command"]
                    self.assertEqual(command[command.index("--cd") + 1], str(project / "sub"))

    def test_every_mcp_llm_tool_refuses_a_directory_outside_the_allowed_roots(self) -> None:
        project = self.root / "project"
        outside = self.root / "elsewhere"
        for name, tool in TOOLS.items():
            for value, message in (
                (str(outside), "outside"),
                (str(project / ".." / "elsewhere"), "outside"),
                (str(project / "missing"), "does not exist"),
            ):
                with self.subTest(tool=name, value=value), _no_process_may_start():
                    with contextlib.chdir(project), patch.dict(os.environ, {WORKDIR_ROOTS_ENV: ""}):
                        error = _input_error_of(tool(working_directory=value))

                    self.assertIsNotNone(error)
                    self.assertIn(message, " ".join(error["errors"]))

    def test_the_environment_list_widens_what_mcp_may_use(self) -> None:
        project = self.root / "project"
        outside = self.root / "elsewhere"
        with contextlib.chdir(project), patch.dict(os.environ, {WORKDIR_ROOTS_ENV: str(outside)}):
            result = mcp_server.llm_review_command_tool(PAYLOAD, working_directory=str(outside))

        self.assertEqual(result["execution_status"], "dry_run")
        self.assertEqual(result["command"][result["command"].index("--cd") + 1], str(outside))

    def test_cli_only_requires_the_directory_to_exist(self) -> None:
        text = json.dumps(PAYLOAD, ensure_ascii=False)
        outside = self.root / "elsewhere"
        stdout = io.StringIO()
        with contextlib.chdir(self.root / "project"):
            argv = ["semantic-guard", "llm-review-run", "--text", text, "--working-directory", str(outside)]
            with patch.object(sys, "argv", argv), contextlib.redirect_stdout(stdout):
                main()
        command = json.loads(stdout.getvalue())["command"]
        self.assertEqual(command[command.index("--cd") + 1], str(outside))

        for name, expected in (("llm-review-run", 2), ("llm-review-command", 2), ("review-if-needed", 2)):
            with self.subTest(command=name), _no_process_may_start():
                stderr = io.StringIO()
                argv = ["semantic-guard", name, "--text", text, "--working-directory", str(self.root / "missing")]
                with patch.object(sys, "argv", argv), self.assertRaises(SystemExit) as raised, patch("sys.stderr", stderr):
                    main()

                self.assertEqual(raised.exception.code, expected)
                self.assertIn("--working-directory", stderr.getvalue())
                self.assertIn("does not exist", stderr.getvalue())

    def test_cli_exploration_reports_a_missing_directory_as_structured_input_error(self) -> None:
        stdout = io.StringIO()
        argv = [
            "semantic-guard", "llm-explore-request", "--text", IDEA, "--execute",
            "--working-directory", str(self.root / "missing"),
        ]
        with _no_process_may_start(), patch.object(sys, "argv", argv), contextlib.redirect_stdout(stdout):
            with self.assertRaises(SystemExit) as raised:
                main()

        self.assertEqual(raised.exception.code, 1)
        self.assertEqual(json.loads(stdout.getvalue())["execution_status"], "input_error")

    def test_cli_resolves_a_relative_directory_once(self) -> None:
        text = json.dumps(PAYLOAD, ensure_ascii=False)
        stdout = io.StringIO()
        with contextlib.chdir(self.root / "project"):
            argv = ["semantic-guard", "llm-review-command", "--text", text, "--working-directory", "sub"]
            with patch.object(sys, "argv", argv), contextlib.redirect_stdout(stdout):
                main()

        command = json.loads(stdout.getvalue())["command"]
        self.assertEqual(command[command.index("--cd") + 1], str(self.root / "project" / "sub"))

    def test_a_relative_directory_is_not_applied_twice_by_cd_and_cwd(self) -> None:
        sub = self.root / "project" / "sub"
        with contextlib.chdir(self.root / "project"):
            command = build_agent_command(
                backend="codex", binary="codex", schema_path="schema.json", model="m", working_directory="sub"
            )
        self.assertEqual(command[command.index("--cd") + 1], str(sub))

    @unittest.skipUnless(POSIX, "runs a child process")
    def test_the_child_sees_the_same_existing_directory_whatever_it_was_called(self) -> None:
        child = "import os, sys; print(os.getcwd() == os.path.realpath(sys.argv[1]) and os.path.isdir(sys.argv[1]))"
        with contextlib.chdir(self.root / "project"):
            request = CodexExecReviewRequest.from_mapping(
                PAYLOAD,
                backend="command",
                agent_command=[sys.executable, "-c", child, "{working_directory}"],
                working_directory="sub",
            )
            result = run_codex_exec_review(request, execute=True)

        self.assertEqual(result.stdout.strip(), "True")


if __name__ == "__main__":
    unittest.main()
