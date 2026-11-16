from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any
from unittest.mock import patch

from semantic_guard_workflow.cli import main
from semantic_guard_workflow.escalation import review_if_needed
from semantic_guard_workflow.llm_review import SCHEMA_VERSION, candidate_gap_review_schema_path
from semantic_guard_workflow.mcp_server import (
    llm_explore_request_tool,
    llm_review_command_tool,
    llm_review_run_tool,
    llm_review_start_tool,
    review_if_needed_start_tool,
    review_if_needed_tool,
)
from semantic_guard_workflow.runtime.backends import (
    BACKEND_CLAUDE,
    BACKEND_CODEX,
    BACKEND_COMMAND,
    build_agent_command,
    extract_agent_output,
    resolve_model,
    validate_backend,
    validate_mcp_backend,
)
from semantic_guard_workflow.runtime.exploration import CodexExecExplorationRequest, run_codex_exec_exploration
from semantic_guard_workflow.runtime.review import CodexExecReviewRequest, build_codex_exec_command, run_codex_exec_review
from semantic_guard_workflow.runtime.review_jobs import ReviewJobStore

SCHEMA_PATH = candidate_gap_review_schema_path()


def _review(**overrides: Any) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "review_status": "needs_supplement",
        "missing_aspects": [
            {
                "kind": "acceptance_criteria",
                "severity": "major",
                "why_it_matters": "速いという要求を検証できない。",
                "supplement": "対象画面、計測条件、しきい値を明記する。",
            }
        ],
        "questionable_assumptions": [],
        "possible_counter_conditions": [],
        "supplement_proposals": [],
        "rule_item_reviews": [],
        "human_decision_needed": [],
    }
    payload.update(overrides)
    return payload


def _claude_envelope(**fields: object) -> str:
    envelope: dict[str, object] = {"type": "result", "subtype": "success", "is_error": False}
    envelope.update(fields)
    return json.dumps(envelope, ensure_ascii=False)


def _request(backend: str, **overrides: Any) -> CodexExecReviewRequest:
    payload = {"candidate": "要求: 画面をいい感じに速くする。", "phase": "audit_request"}
    return CodexExecReviewRequest.from_mapping(payload, backend=backend, **overrides)


def _runner(stdout: str, returncode: int = 0, calls: list[dict[str, Any]] | None = None):
    def run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        if calls is not None:
            calls.append({"command": command, **kwargs})
        return subprocess.CompletedProcess(command, returncode, stdout=stdout, stderr="")

    return run


class BackendSelectionTests(unittest.TestCase):
    def test_validate_backend_rejects_unknown_and_inconsistent_selection(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown backend"):
            validate_backend("gemini")
        with self.assertRaisesRegex(ValueError, "requires a non-empty agent command"):
            validate_backend(BACKEND_COMMAND)
        with self.assertRaisesRegex(ValueError, "only valid with backend 'command'"):
            validate_backend(BACKEND_CLAUDE, ["tool"])
        validate_backend(BACKEND_COMMAND, ["tool"])

    def test_mcp_never_accepts_the_operator_command_backend(self) -> None:
        validate_mcp_backend(BACKEND_CODEX)
        validate_mcp_backend(BACKEND_CLAUDE)
        with self.assertRaisesRegex(ValueError, "not available over MCP"):
            validate_mcp_backend(BACKEND_COMMAND)
        with self.assertRaisesRegex(ValueError, "not available over MCP"):
            validate_mcp_backend("nonsense")

    def test_unset_model_resolves_to_each_backends_own_default(self) -> None:
        self.assertEqual(resolve_model(BACKEND_CODEX, ""), "gpt-5.4-mini")
        self.assertEqual(resolve_model(BACKEND_CLAUDE, ""), "sonnet")
        self.assertEqual(resolve_model(BACKEND_CLAUDE, "gpt-5.4-mini"), "sonnet")
        self.assertEqual(resolve_model(BACKEND_CLAUDE, "opus"), "opus")
        self.assertEqual(resolve_model(BACKEND_CODEX, "gpt-test"), "gpt-test")

    def test_codex_remains_the_default_backend(self) -> None:
        request = CodexExecReviewRequest.from_mapping({"candidate": "要求: x。", "phase": "audit_request"})

        self.assertEqual(request.backend, BACKEND_CODEX)
        self.assertEqual(build_codex_exec_command(request)[:2], ["codex", "exec"])


class ClaudeBackendTests(unittest.TestCase):
    def test_command_isolates_the_reviewer_and_inlines_the_schema(self) -> None:
        request = _request(BACKEND_CLAUDE)

        command = build_codex_exec_command(request)

        self.assertEqual(command[:4], ["claude", "-p", "--output-format", "json"])
        self.assertEqual(command[command.index("--model") + 1], "sonnet")
        self.assertEqual(command[command.index("--tools") + 1], "")
        for flag in ("--no-session-persistence", "--strict-mcp-config", "--disable-slash-commands"):
            self.assertIn(flag, command)
        self.assertEqual(command[command.index("--setting-sources") + 1], "")
        self.assertNotIn("--cd", command)
        inline = json.loads(command[command.index("--json-schema") + 1])
        stored = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        # Claude Code cannot resolve the draft 2020-12 meta-schema reference.
        self.assertNotIn("$schema", inline)
        self.assertNotIn("$id", inline)
        self.assertEqual(inline, {key: value for key, value in stored.items() if key not in ("$schema", "$id")})

    def test_binary_and_model_are_overridable(self) -> None:
        request = _request(BACKEND_CLAUDE, model="opus", agent_binary="/opt/bin/claude")

        command = build_codex_exec_command(request)

        self.assertEqual(command[0], "/opt/bin/claude")
        self.assertEqual(command[command.index("--model") + 1], "opus")

    def test_structured_output_envelope_is_validated_as_the_review(self) -> None:
        stdout = _claude_envelope(structured_output=_review(), result="ignored")
        calls: list[dict[str, Any]] = []

        result = run_codex_exec_review(
            _request(BACKEND_CLAUDE, working_directory="/tmp/project"), execute=True, runner=_runner(stdout, calls=calls)
        )

        self.assertTrue(result.valid)
        self.assertEqual(result.execution_status, "valid_review")
        self.assertEqual(result.backend, BACKEND_CLAUDE)
        self.assertEqual(result.review, _review())
        self.assertEqual(calls[0]["cwd"], "/tmp/project")
        self.assertIn("candidate_gap_reviewer", calls[0]["input"])
        self.assertEqual(result.as_dict()["backend"], BACKEND_CLAUDE)

    def test_result_string_is_used_when_structured_output_is_absent(self) -> None:
        fenced = "```json\n" + json.dumps(_review(), ensure_ascii=False) + "\n```"

        result = run_codex_exec_review(
            _request(BACKEND_CLAUDE), execute=True, runner=_runner(_claude_envelope(result=fenced))
        )

        self.assertTrue(result.valid)
        self.assertEqual(result.review, _review())

    def test_envelope_that_reports_an_error_is_not_a_review(self) -> None:
        stdout = _claude_envelope(is_error=True, result="rate limited")

        result = run_codex_exec_review(_request(BACKEND_CLAUDE), execute=True, runner=_runner(stdout))

        self.assertFalse(result.valid)
        self.assertEqual(result.execution_status, "invalid_review")
        self.assertEqual(result.failure_kind, "agent_error")
        self.assertIn("rate limited", result.errors[0])

    def test_only_a_clean_success_envelope_is_accepted(self) -> None:
        structured = _review()
        fenced = "```json\n" + json.dumps(structured, ensure_ascii=False) + "\n```"
        cases = {
            "error_during_execution": {"subtype": "error_during_execution", "structured_output": structured},
            "error_max_turns": {"subtype": "error_max_turns", "structured_output": structured},
            "error_max_turns_result_string": {"subtype": "error_max_turns", "result": fenced},
            "is_error_string": {"is_error": "true", "structured_output": structured},
            "is_error_false_string": {"is_error": "false", "structured_output": structured},
            "is_error_integer": {"is_error": 1, "structured_output": structured},
            "is_error_zero": {"is_error": 0, "structured_output": structured},
            "is_error_null": {"is_error": None, "structured_output": structured},
            "permission_denied": {
                "permission_denials": [{"tool_name": "Bash", "tool_use_id": "t1", "tool_input": {}}],
                "structured_output": structured,
            },
            "permission_denials_not_a_list": {"permission_denials": "Bash", "structured_output": structured},
        }
        for name, fields in cases.items():
            with self.subTest(name=name):
                result = run_codex_exec_review(
                    _request(BACKEND_CLAUDE), execute=True, runner=_runner(_claude_envelope(**fields))
                )

                self.assertFalse(result.valid)
                self.assertIsNone(result.review)
                self.assertEqual(result.execution_status, "invalid_review")
                self.assertEqual(result.failure_kind, "agent_error")
                self.assertTrue(result.errors)

    def test_failure_reasons_are_reported(self) -> None:
        result = run_codex_exec_review(
            _request(BACKEND_CLAUDE),
            execute=True,
            runner=_runner(
                _claude_envelope(
                    subtype="error_max_turns",
                    is_error="true",
                    permission_denials=[{"tool_name": "Bash"}],
                    structured_output=_review(),
                )
            ),
        )

        joined = "\n".join(result.errors)
        self.assertIn("'error_max_turns'", joined)
        self.assertIn("is_error", joined)
        self.assertIn("Bash", joined)

    def test_status_fields_are_required_from_the_claude_envelope(self) -> None:
        for missing in ("subtype", "is_error"):
            with self.subTest(missing=missing):
                envelope = json.loads(_claude_envelope(structured_output=_review()))
                del envelope[missing]

                result = run_codex_exec_review(
                    _request(BACKEND_CLAUDE), execute=True, runner=_runner(json.dumps(envelope))
                )

                self.assertFalse(result.valid)
                self.assertEqual(result.failure_kind, "agent_error")

    def test_success_envelope_with_empty_permission_denials_is_accepted(self) -> None:
        result = run_codex_exec_review(
            _request(BACKEND_CLAUDE),
            execute=True,
            runner=_runner(_claude_envelope(permission_denials=[], structured_output=_review())),
        )

        self.assertTrue(result.valid)

    def test_envelope_without_payload_is_invalid(self) -> None:
        result = run_codex_exec_review(_request(BACKEND_CLAUDE), execute=True, runner=_runner(_claude_envelope()))

        self.assertFalse(result.valid)
        self.assertEqual(result.failure_kind, "invalid_json")

    def test_schema_violation_in_structured_output_is_rejected(self) -> None:
        stdout = _claude_envelope(structured_output=_review(review_status="approved"))

        result = run_codex_exec_review(_request(BACKEND_CLAUDE), execute=True, runner=_runner(stdout))

        self.assertFalse(result.valid)
        self.assertEqual(result.failure_kind, "schema_mismatch")

    def test_failure_messages_name_the_backend_not_codex(self) -> None:
        result = run_codex_exec_review(_request(BACKEND_CLAUDE), execute=True, runner=_runner("", returncode=1))

        self.assertEqual(result.failure_kind, "non_zero_exit")
        self.assertEqual(result.errors, ["claude agent exited with status 1"])

    def test_exploration_uses_the_same_backend_contract(self) -> None:
        request = CodexExecExplorationRequest.from_mapping({"text": "割り勘アプリを作りたい"}, backend=BACKEND_CLAUDE)

        dry = run_codex_exec_exploration(request)

        self.assertEqual(dry.execution_status, "dry_run")
        self.assertEqual(dry.command[0], "claude")
        self.assertEqual(dry.backend, BACKEND_CLAUDE)


class CommandBackendTests(unittest.TestCase):
    TEMPLATE = ["my-agent", "--model", "{model}", "--schema", "{schema_path}", "--cwd", "{working_directory}"]

    def test_placeholders_are_substituted_and_unused_schema_is_not_read(self) -> None:
        command = build_agent_command(
            backend=BACKEND_COMMAND,
            binary="",
            schema_path=SCHEMA_PATH,
            model="m-1",
            working_directory="/work",
            agent_command=self.TEMPLATE,
        )

        self.assertEqual(command, ["my-agent", "--model", "m-1", "--schema", str(SCHEMA_PATH), "--cwd", "/work"])

    def test_schema_json_placeholder_inlines_the_compact_schema(self) -> None:
        command = build_agent_command(
            backend=BACKEND_COMMAND,
            binary="",
            schema_path=SCHEMA_PATH,
            model="",
            working_directory=None,
            agent_command=["agent", "{schema_json}"],
        )

        self.assertEqual(json.loads(command[1])["title"], "CandidateGapReview")
        self.assertNotIn("$schema", json.loads(command[1]))

    def test_fenced_json_from_an_unconstrained_agent_is_accepted(self) -> None:
        fenced = "```json\n" + json.dumps(_review(), ensure_ascii=False) + "\n```\n"
        request = _request(BACKEND_COMMAND, agent_command=["agent"])

        result = run_codex_exec_review(request, execute=True, runner=_runner(fenced))

        self.assertTrue(result.valid)
        self.assertEqual(result.backend, BACKEND_COMMAND)

    def test_plain_json_passes_through_untouched(self) -> None:
        text, errors, failure = extract_agent_output(BACKEND_COMMAND, json.dumps(_review()))

        self.assertEqual((json.loads(text), errors, failure), (_review(), [], None))

    def test_codex_output_is_never_rewritten(self) -> None:
        fenced = "```json\n{}\n```"

        text, errors, failure = extract_agent_output(BACKEND_CODEX, fenced)

        self.assertEqual((text, errors, failure), (fenced, [], None))

    def test_envelope_from_a_generic_agent_is_checked_for_the_status_it_reports(self) -> None:
        structured = _review()
        accepted = [
            json.dumps({"structured_output": structured}),
            json.dumps({"is_error": False, "structured_output": structured}),
            json.dumps({"subtype": "success", "is_error": False, "structured_output": structured}),
        ]
        for stdout in accepted:
            with self.subTest(stdout=stdout):
                text, errors, failure = extract_agent_output(BACKEND_COMMAND, stdout)
                self.assertEqual((json.loads(text), errors, failure), (structured, [], None))

        rejected = [
            {"is_error": 1, "structured_output": structured},
            {"is_error": "true", "structured_output": structured},
            {"is_error": False, "subtype": "error_max_turns", "structured_output": structured},
            {"structured_output": structured, "permission_denials": [{"tool_name": "Bash"}]},
        ]
        for envelope in rejected:
            with self.subTest(envelope=envelope):
                _text, errors, failure = extract_agent_output(BACKEND_COMMAND, json.dumps(envelope))
                self.assertEqual(failure, "agent_error")
                self.assertTrue(errors)

    def test_request_without_a_template_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            _request(BACKEND_COMMAND)


class McpBackendTests(unittest.TestCase):
    PAYLOAD = {"candidate": "要求: 画面をいい感じに速くする。", "phase": "audit_request"}

    def test_claude_dry_run_is_available_over_mcp(self) -> None:
        result = llm_review_command_tool(self.PAYLOAD, backend="claude")

        self.assertEqual(result["command"][0], "claude")
        self.assertEqual(result["backend"], "claude")
        self.assertFalse(result["executed"])

    def test_default_backend_is_still_codex(self) -> None:
        result = llm_review_run_tool(self.PAYLOAD)

        self.assertEqual(result["command"][:2], ["codex", "exec"])
        self.assertEqual(result["backend"], "codex")

    def test_command_backend_is_refused_without_starting_anything(self) -> None:
        with (
            patch("semantic_guard_workflow.runtime.codex_exec.subprocess.run") as run,
            patch("semantic_guard_workflow.runtime.process.subprocess.Popen") as popen,
        ):
            results = [
                llm_review_command_tool(self.PAYLOAD, backend="command"),
                llm_review_run_tool(self.PAYLOAD, execute=True, backend="command"),
                llm_explore_request_tool("割り勘アプリを作りたい", execute=True, backend="command"),
            ]
        run.assert_not_called()
        popen.assert_not_called()
        for result in results:
            self.assertEqual(result["execution_status"], "input_error")
            self.assertIn("not available over MCP", result["errors"][0])

    def test_job_tools_refuse_the_command_backend(self) -> None:
        started = llm_review_start_tool(self.PAYLOAD, backend="command")
        escalated = review_if_needed_start_tool(self.PAYLOAD, backend="command")
        sync = review_if_needed_tool(self.PAYLOAD, backend="command")

        self.assertEqual(started["state"], "input_error")
        self.assertEqual(escalated["state"], "input_error")
        self.assertEqual(sync["review_result"]["execution_status"], "input_error")


class EscalationAndJobTests(unittest.TestCase):
    PAYLOAD = {
        "candidate": "要求: 画面をいい感じに速くする。",
        "phase": "audit_request",
        "audit_result": {
            "phase": "audit_request",
            "status": "block",
            "findings": [
                {
                    "category": "clarity",
                    "severity": "blocker",
                    "finding": "曖昧語 `いい感じ` が含まれている。",
                    "warning_class": "possible false positive",
                }
            ],
        },
    }

    def test_review_if_needed_runs_the_selected_backend(self) -> None:
        calls: list[dict[str, Any]] = []
        stdout = _claude_envelope(structured_output=_review())

        result = review_if_needed(
            self.PAYLOAD, execute=True, backend=BACKEND_CLAUDE, runner=_runner(stdout, calls=calls)
        )

        self.assertTrue(result["escalation"]["needed"])
        self.assertEqual(result["review_result"]["backend"], BACKEND_CLAUDE)
        self.assertTrue(result["review_result"]["valid"])
        self.assertEqual(calls[0]["command"][0], "claude")

    def test_review_if_needed_reports_a_bad_selection_as_input_error(self) -> None:
        result = review_if_needed(self.PAYLOAD, execute=True, backend=BACKEND_COMMAND)

        self.assertTrue(result["escalation"]["needed"])
        self.assertEqual(result["review_result"]["execution_status"], "input_error")

    def test_background_job_carries_the_backend(self) -> None:
        store = ReviewJobStore()
        request = _request(BACKEND_CLAUDE)
        stdout = _claude_envelope(structured_output=_review())

        snapshot = store.start(request, runner=_runner(stdout))
        for _ in range(200):
            snapshot = store.get(snapshot["job_id"])
            if snapshot["done"]:
                break
            time.sleep(0.01)

        self.assertEqual(snapshot["state"], "completed")
        self.assertEqual(snapshot["command"][0], "claude")
        self.assertEqual(snapshot["review_result"]["backend"], BACKEND_CLAUDE)


class CliBackendTests(unittest.TestCase):
    PAYLOAD = json.dumps({"candidate": "要求: 画面をいい感じに速くする。", "phase": "audit_request"}, ensure_ascii=False)

    def _run(self, *args: str) -> dict[str, Any]:
        stdout = io.StringIO()
        with patch.object(sys, "argv", ["semantic-guard", *args]), redirect_stdout(stdout):
            main()
        return json.loads(stdout.getvalue())

    def test_claude_backend_dry_run(self) -> None:
        result = self._run("llm-review-run", "--text", self.PAYLOAD, "--backend", "claude")

        self.assertEqual(result["backend"], "claude")
        self.assertEqual(result["command"][0], "claude")
        self.assertEqual(result["command"][result["command"].index("--model") + 1], "sonnet")

    def test_default_model_for_codex_is_unchanged(self) -> None:
        result = self._run("llm-review-run", "--text", self.PAYLOAD)

        self.assertEqual(result["command"][result["command"].index("-m") + 1], "gpt-5.4-mini")

    def test_command_backend_template_is_split_like_a_shell_line(self) -> None:
        result = self._run(
            "llm-review-command",
            "--text",
            self.PAYLOAD,
            "--backend",
            "command",
            "--agent-command",
            "my-agent --model '{model}' --schema {schema_path}",
            "--model",
            "m-1",
        )

        self.assertEqual(result["command"][:3], ["my-agent", "--model", "m-1"])
        self.assertEqual(result["command"][4], result["schema_path"])

    def test_command_backend_without_template_is_a_usage_error(self) -> None:
        with patch.object(sys, "argv", ["semantic-guard", "llm-review-run", "--text", self.PAYLOAD, "--backend", "command"]):
            with self.assertRaises(SystemExit) as raised, patch("sys.stderr", io.StringIO()):
                main()

        self.assertEqual(raised.exception.code, 2)

    def test_quoted_windows_command_path_preserves_backslashes_and_spaces(self) -> None:
        for path in (r"C:\tools\agent.exe", r"C:\Program Files\Agent\agent.exe"):
            with self.subTest(path=path):
                result = self._run(
                    "llm-review-command", "--text", self.PAYLOAD,
                    "--backend", "command", "--agent-command",
                    f'"{path}" --schema "{{schema_path}}"',
                )
                self.assertEqual(result["command"][0], path)
                self.assertEqual(result["command"][2], result["schema_path"])

    def test_exploration_backend_flag(self) -> None:
        result = self._run("llm-explore-request", "--text", "割り勘アプリを作りたい", "--backend", "claude")

        self.assertEqual(result["command"][0], "claude")


@unittest.skipUnless(
    os.environ.get("SEMANTIC_GUARD_LIVE_AGENT") == "claude",
    "set SEMANTIC_GUARD_LIVE_AGENT=claude to run the real Claude Code reviewer once",
)
class LiveClaudeTests(unittest.TestCase):
    def test_real_reviewer_returns_a_schema_valid_review(self) -> None:
        request = _request(BACKEND_CLAUDE, model=os.environ.get("SEMANTIC_GUARD_LIVE_MODEL", "haiku"), timeout_seconds=170)

        result = run_codex_exec_review(request, execute=True)

        self.assertTrue(result.valid, result.errors)
        self.assertEqual(Path(result.schema_path), SCHEMA_PATH)


if __name__ == "__main__":
    unittest.main()
