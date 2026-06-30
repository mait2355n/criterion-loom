from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from semantic_guard.acceptance_review import (
    build_acceptance_review_bundle_template,
    load_acceptance_review_bundle_schema,
    validate_acceptance_review_bundle,
)
from semantic_guard.codex_exec_exploration import (
    DEFAULT_CODEX_MODEL as DEFAULT_EXPLORATION_CODEX_MODEL,
    DEFAULT_TIMEOUT_SECONDS as DEFAULT_EXPLORATION_TIMEOUT_SECONDS,
    CodexExecExplorationRequest,
    run_codex_exec_exploration,
)
from semantic_guard.codex_exec_review import (
    DEFAULT_CODEX_MODEL,
    DEFAULT_TIMEOUT_SECONDS,
    CodexExecReviewRequest,
    run_codex_exec_review,
)
from semantic_guard.conventions import audit_conventions, load_conventions_catalog
from semantic_guard.core import (
    apply_logical_trace_mode,
    audit_decision_state,
    audit_diff,
    audit_plan,
    audit_request,
    finish_check,
    understand_target,
)
from semantic_guard.doctor import run_doctor
from semantic_guard.escalation import review_if_needed
from semantic_guard.evaluation import DEFAULT_FIXTURE_ROOT, evaluate_fixture_tree
from semantic_guard.exploration import explore_request
from semantic_guard.llm_review import (
    CandidateGapReviewInput,
    build_candidate_gap_review_prompt,
    load_candidate_gap_review_schema,
    validate_candidate_gap_review,
)
from semantic_guard.models import load_audit_result_schema
from semantic_guard.request_exploration_review import load_request_exploration_review_schema
from semantic_guard.rule_mapping import rule_detector_mappings, unmapped_rule_ids
from semantic_guard.rules import RULES
from semantic_guard.severity_profiles import PROFILE_NAMES, apply_severity_profile
from semantic_guard.traceability import build_trace_report


def main() -> None:
    parser = argparse.ArgumentParser(prog="semantic-guard")
    subparsers = parser.add_subparsers(dest="command", required=True)

    _add_text_command(subparsers, "explore-request")
    _add_text_command(subparsers, "understand-target")
    _add_text_command(subparsers, "audit-request")
    _add_text_command(subparsers, "audit-decision-state")
    _add_text_command(subparsers, "audit-plan")
    _add_text_command(subparsers, "audit-diff")
    _add_text_command(subparsers, "finish-check")
    _add_text_command(subparsers, "audit-conventions")
    _add_json_command(subparsers, "llm-review-prompt")
    subparsers.add_parser("llm-review-schema")
    subparsers.add_parser("request-exploration-review-schema")
    _add_llm_exploration_command(subparsers)
    _add_json_command(subparsers, "validate-llm-review")
    _add_llm_review_command(subparsers, "llm-review-command")
    _add_llm_review_command(subparsers, "llm-review-run")
    _add_review_if_needed_command(subparsers, "review-if-needed")
    _add_evaluate_fixtures_command(subparsers)
    _add_doctor_command(subparsers)
    _add_json_command(subparsers, "trace-report")
    subparsers.add_parser("audit-result-schema")
    subparsers.add_parser("rule-detector-map")
    subparsers.add_parser("conventions-catalog")
    subparsers.add_parser("acceptance-bundle-schema")
    _add_json_command(subparsers, "acceptance-bundle-template")
    _add_json_command(subparsers, "validate-acceptance-bundle")

    args = parser.parse_args()
    if args.command == "llm-review-schema":
        print(json.dumps(load_candidate_gap_review_schema(), ensure_ascii=False, indent=2))
        return
    if args.command == "request-exploration-review-schema":
        print(json.dumps(load_request_exploration_review_schema(), ensure_ascii=False, indent=2))
        return
    if args.command == "acceptance-bundle-schema":
        print(json.dumps(load_acceptance_review_bundle_schema(), ensure_ascii=False, indent=2))
        return
    if args.command == "audit-result-schema":
        print(json.dumps(load_audit_result_schema(), ensure_ascii=False, indent=2))
        return
    if args.command == "conventions-catalog":
        print(json.dumps(load_conventions_catalog(), ensure_ascii=False, indent=2))
        return
    if args.command == "rule-detector-map":
        mappings = rule_detector_mappings()
        print(
            json.dumps(
                {
                    "rule_count": len(RULES),
                    "mapping_count": len(mappings),
                    "unmapped_rule_ids": unmapped_rule_ids(),
                    "mappings": mappings,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return
    if args.command == "llm-review-prompt":
        payload = _read_json_input(args)
        review_input = CandidateGapReviewInput.from_mapping(payload)
        print(build_candidate_gap_review_prompt(review_input, include_schema=args.include_schema))
        return
    if args.command == "validate-llm-review":
        payload = _read_json_input(args)
        errors = validate_candidate_gap_review(payload)
        print(json.dumps({"valid": not errors, "errors": errors}, ensure_ascii=False, indent=2))
        if errors:
            raise SystemExit(1)
        return
    if args.command == "llm-explore-request":
        text = _read_input(args)
        payload = {
            "text": text,
            "context": args.context or "",
            "deterministic_exploration": explore_request(text, context=args.context or "", strict=not args.no_strict),
            "constraints": args.constraints or "",
            "non_goals": args.non_goals or "",
            "known_sources": args.known_sources or "",
        }
        try:
            request = CodexExecExplorationRequest.from_mapping(
                payload,
                model=args.model,
                timeout_seconds=args.timeout_seconds,
                working_directory=args.working_directory,
                codex_binary=args.codex_binary,
                include_schema_in_prompt=args.include_schema,
            )
        except ValueError as exc:
            print(
                json.dumps(
                    {"executed": False, "execution_status": "input_error", "valid": False, "errors": [str(exc)]},
                    ensure_ascii=False,
                    indent=2,
                )
            )
            raise SystemExit(1) from exc
        result = run_codex_exec_exploration(request, execute=args.execute)
        print(json.dumps(result.as_dict(), ensure_ascii=False, indent=2))
        if result.executed and not result.valid:
            raise SystemExit(1)
        return
    if args.command == "llm-review-command":
        payload = _read_json_input(args)
        request = _codex_exec_request_from_args(payload, args)
        result = run_codex_exec_review(request, execute=False)
        print(json.dumps(result.as_dict(), ensure_ascii=False, indent=2))
        return
    if args.command == "llm-review-run":
        payload = _read_json_input(args)
        request = _codex_exec_request_from_args(payload, args)
        result = run_codex_exec_review(request, execute=args.execute)
        print(json.dumps(result.as_dict(), ensure_ascii=False, indent=2))
        if result.executed and not result.valid:
            raise SystemExit(1)
        return
    if args.command == "review-if-needed":
        payload = _read_json_input(args)
        result = review_if_needed(
            payload,
            execute=args.execute,
            model=args.model,
            timeout_seconds=args.timeout_seconds,
            working_directory=args.working_directory or "",
            include_schema=args.include_schema,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        review_result = result.get("review_result")
        if args.execute and isinstance(review_result, dict) and review_result.get("executed") and not review_result.get("valid"):
            raise SystemExit(1)
        return
    if args.command == "evaluate-fixtures":
        result = evaluate_fixture_tree(args.path, include_passed=args.include_passed)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if result["failed"]:
            raise SystemExit(1)
        return
    if args.command == "doctor":
        result = run_doctor(args.project_root, run_fixtures=not args.no_fixtures)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if result["status"] == "block":
            raise SystemExit(1)
        return
    if args.command == "trace-report":
        payload = _read_json_input(args)
        print(json.dumps(build_trace_report(payload), ensure_ascii=False, indent=2))
        return
    if args.command == "acceptance-bundle-template":
        payload = _read_json_input(args)
        print(json.dumps(build_acceptance_review_bundle_template(payload), ensure_ascii=False, indent=2))
        return
    if args.command == "validate-acceptance-bundle":
        payload = _read_json_input(args)
        errors = validate_acceptance_review_bundle(payload, strict=not args.no_strict)
        print(json.dumps({"valid": not errors, "errors": errors}, ensure_ascii=False, indent=2))
        if errors:
            raise SystemExit(1)
        return

    text = _read_input(args)
    strict = not args.no_strict
    kind = args.kind or _default_kind(args.command)

    if args.command == "explore-request":
        result = explore_request(text, context=args.context or "", strict=strict)
    elif args.command == "understand-target":
        result = understand_target(text, context=args.context or "", strict=strict)
    elif args.command == "audit-request":
        result = audit_request(text, context=args.context or "", strict=strict, input_kind=kind)
    elif args.command == "audit-decision-state":
        result = audit_decision_state(text, context=args.context or "", strict=strict, input_kind=kind)
    elif args.command == "audit-plan":
        result = audit_plan(text, request=args.request or "", context=args.context or "", strict=strict, input_kind=kind)
    elif args.command == "audit-diff":
        stdin_intent = ""
        if args.intent is None and args.text is None and args.file is None:
            text, stdin_intent = _extract_audit_diff_metadata(text)
        result = audit_diff(text, intent=args.intent or stdin_intent or "", context=args.context or "", strict=strict, input_kind=kind)
    elif args.command == "finish-check":
        result = finish_check(text, evidence=args.evidence or "", context=args.context or "", strict=strict)
    elif args.command == "audit-conventions":
        result = audit_conventions(text, context=args.context or "", strict=strict, input_kind=kind)
    else:
        raise SystemExit(f"unknown command: {args.command}")

    result = apply_severity_profile(result, args.profile)
    if args.command == "audit-request":
        result = apply_logical_trace_mode(result, args.logical_trace)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def _add_text_command(subparsers: argparse._SubParsersAction[argparse.ArgumentParser], name: str) -> None:
    parser = subparsers.add_parser(name)
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--text", help="Text to audit.")
    source.add_argument("--file", help="File to audit. Reads stdin when neither --text nor --file is provided.")
    parser.add_argument("--context", help="Optional contextual text.")
    parser.add_argument("--request", help="Optional request text for audit-plan.")
    parser.add_argument("--intent", help="Optional request or plan text for audit-diff.")
    parser.add_argument("--evidence", help="Optional evidence text for finish-check.")
    parser.add_argument(
        "--kind",
        choices=["requirement", "plan", "document", "diff-summary"],
        help="Input kind. Defaults depend on the command.",
    )
    parser.add_argument("--no-strict", action="store_true", help="Downgrade strict blockers where possible.")
    parser.add_argument("--profile", choices=PROFILE_NAMES, default="default", help="Severity profile to apply to findings.")
    if name == "audit-request":
        parser.add_argument(
            "--logical-trace",
            choices=["summary", "full", "none"],
            default="summary",
            help="Logical trace output detail for audit-request. Default: summary.",
        )


def _add_json_command(subparsers: argparse._SubParsersAction[argparse.ArgumentParser], name: str) -> None:
    parser = subparsers.add_parser(name)
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--text", help="JSON text.")
    source.add_argument("--file", help="JSON file. Reads stdin when neither --text nor --file is provided.")
    if name == "llm-review-prompt":
        parser.add_argument("--include-schema", action="store_true", help="Append the output JSON schema to the prompt.")
    if name == "validate-acceptance-bundle":
        parser.add_argument("--no-strict", action="store_true", help="Validate shape without requiring final-review evidence completeness.")


def _add_llm_exploration_command(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("llm-explore-request")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--text", help="Open-ended idea or request text to explore.")
    source.add_argument("--file", help="File containing an open-ended idea or request. Reads stdin when neither --text nor --file is provided.")
    parser.add_argument("--context", help="Optional contextual text.")
    parser.add_argument("--constraints", help="Known constraints to pass to the exploration reviewer.")
    parser.add_argument("--non-goals", help="Known non-goals to pass to the exploration reviewer.")
    parser.add_argument("--known-sources", help="Known source list or evidence notes available to the reviewer.")
    parser.add_argument("--no-strict", action="store_true", help="Downgrade strict blockers in the deterministic preflight.")
    parser.add_argument("--model", default=DEFAULT_EXPLORATION_CODEX_MODEL, help="Codex model for the isolated exploration reviewer.")
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=DEFAULT_EXPLORATION_TIMEOUT_SECONDS,
        help="Timeout for codex exec when --execute is used.",
    )
    parser.add_argument("--working-directory", help="Working directory passed to codex exec with --cd.")
    parser.add_argument("--codex-binary", default="codex", help="Codex executable to run.")
    parser.add_argument("--include-schema", action="store_true", help="Append the output JSON schema to the prompt.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Default. Build prompt and command without running codex exec.")
    mode.add_argument("--execute", action="store_true", help="Run codex exec and validate its JSON output.")


def _add_llm_review_command(subparsers: argparse._SubParsersAction[argparse.ArgumentParser], name: str) -> None:
    parser = subparsers.add_parser(name)
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--text", help="JSON review bundle.")
    source.add_argument("--file", help="JSON review bundle file. Reads stdin when neither --text nor --file is provided.")
    parser.add_argument("--model", default=DEFAULT_CODEX_MODEL, help="Codex model for the isolated reviewer.")
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="Timeout for codex exec when --execute is used.",
    )
    parser.add_argument("--working-directory", help="Working directory passed to codex exec with --cd.")
    parser.add_argument("--codex-binary", default="codex", help="Codex executable to run.")
    parser.add_argument("--include-schema", action="store_true", help="Append the output JSON schema to the prompt.")
    if name == "llm-review-run":
        mode = parser.add_mutually_exclusive_group()
        mode.add_argument("--dry-run", action="store_true", help="Build command and prompt without running codex exec.")
        mode.add_argument("--execute", action="store_true", help="Run codex exec and validate its JSON output.")


def _add_review_if_needed_command(subparsers: argparse._SubParsersAction[argparse.ArgumentParser], name: str) -> None:
    parser = subparsers.add_parser(name)
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--text", help="JSON escalation bundle.")
    source.add_argument("--file", help="JSON escalation bundle file. Reads stdin when neither --text nor --file is provided.")
    parser.add_argument("--model", default=DEFAULT_CODEX_MODEL, help="Codex model for the isolated reviewer.")
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="Timeout for codex exec when --execute is used.",
    )
    parser.add_argument("--working-directory", help="Working directory passed to codex exec with --cd.")
    parser.add_argument("--include-schema", action="store_true", help="Append the output JSON schema to the prompt.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Default. Build command and prompt only when escalation is needed.")
    mode.add_argument("--execute", action="store_true", help="Run codex exec only when escalation is needed.")


def _add_evaluate_fixtures_command(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("evaluate-fixtures")
    parser.add_argument(
        "--path",
        default=str(DEFAULT_FIXTURE_ROOT),
        help="Fixture root containing *.expected.json files.",
    )
    parser.add_argument("--include-passed", action="store_true", help="Include passed fixture rows in `results`.")


def _add_doctor_command(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("doctor")
    parser.add_argument("--project-root", default=".", help="Project checkout root to inspect.")
    parser.add_argument("--no-fixtures", action="store_true", help="Skip fixture evaluation.")


def _read_input(args: argparse.Namespace) -> str:
    if args.text is not None:
        return args.text
    if args.file is not None:
        return Path(args.file).read_text(encoding="utf-8")
    return sys.stdin.read()


def _extract_audit_diff_metadata(text: str) -> tuple[str, str]:
    lines = text.splitlines(keepends=True)
    for index, line in enumerate(lines):
        if not line.strip():
            continue
        match = re.match(r"^[ \t]*Intent[:：][ \t]*(?P<intent>.+?)\s*$", line)
        if not match:
            return text, ""
        intent = match.group("intent").strip()
        if not intent:
            return text, ""
        return "".join(lines[:index] + lines[index + 1 :]), intent
    return text, ""


def _read_json_input(args: argparse.Namespace) -> dict[str, object]:
    raw = _read_input(args)
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid JSON input: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit("JSON input must be an object")
    return payload


def _codex_exec_request_from_args(payload: dict[str, object], args: argparse.Namespace) -> CodexExecReviewRequest:
    if args.timeout_seconds <= 0:
        raise SystemExit("--timeout-seconds must be positive")
    return CodexExecReviewRequest.from_mapping(
        payload,
        model=args.model,
        timeout_seconds=args.timeout_seconds,
        working_directory=args.working_directory,
        codex_binary=args.codex_binary,
        include_schema_in_prompt=args.include_schema,
    )


def _default_kind(command: str) -> str:
    if command == "audit-plan":
        return "plan"
    if command == "audit-diff":
        return "diff-summary"
    if command in {"explore-request", "understand-target", "audit-decision-state", "finish-check"}:
        return "document"
    if command == "audit-conventions":
        return "document"
    return "requirement"


if __name__ == "__main__":
    main()
