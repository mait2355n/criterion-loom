from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from semantic_guard.acceptance_review import build_acceptance_review_bundle_template, validate_acceptance_review_bundle
from semantic_guard.codex_exec_exploration import (
    DEFAULT_CODEX_MODEL as DEFAULT_EXPLORATION_CODEX_MODEL,
    DEFAULT_TIMEOUT_SECONDS as DEFAULT_EXPLORATION_TIMEOUT_SECONDS,
    CodexExecExplorationRequest,
    run_codex_exec_exploration,
)
from semantic_guard.codex_exec_review import DEFAULT_CODEX_MODEL, DEFAULT_TIMEOUT_SECONDS, CodexExecReviewRequest, run_codex_exec_review
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
from semantic_guard.exploration_jobs import ExplorationJobStore
from semantic_guard.models import load_audit_result_schema
from semantic_guard.request_exploration_review import load_request_exploration_review_schema
from semantic_guard.review_jobs import ReviewJobStore, start_review_if_needed_job
from semantic_guard.rule_mapping import rule_detector_mappings, unmapped_rule_ids
from semantic_guard.rules import RULES
from semantic_guard.severity_profiles import apply_severity_profile
from semantic_guard.traceability import build_trace_report

mcp = FastMCP("semantic-guard", json_response=True)
_review_jobs = ReviewJobStore()
_exploration_jobs = ExplorationJobStore()


@mcp.tool()
def explore_request_tool(text: str, context: str = "", strict: bool = True, profile: str = "default") -> dict[str, object]:
    """Expose material ambiguities and necessary questions before turning an open-ended idea into a spec."""
    return apply_severity_profile(explore_request(text=text, context=context, strict=strict), profile)


@mcp.tool()
def llm_explore_request_tool(
    text: str,
    context: str = "",
    execute: bool = False,
    model: str = DEFAULT_EXPLORATION_CODEX_MODEL,
    timeout_seconds: int = DEFAULT_EXPLORATION_TIMEOUT_SECONDS,
    working_directory: str = "",
    include_schema: bool = False,
) -> dict[str, object]:
    """Run or dry-run an isolated LLM exploration reviewer for pre-spec questions. Dry-run is the default."""
    deterministic_exploration = explore_request(text=text, context=context, strict=True)
    try:
        request = CodexExecExplorationRequest.from_mapping(
            {
                "text": text,
                "context": context,
                "deterministic_exploration": deterministic_exploration,
            },
            model=model,
            timeout_seconds=timeout_seconds,
            working_directory=working_directory or None,
            codex_binary="codex",
            include_schema_in_prompt=include_schema,
        )
    except ValueError as exc:
        return {"executed": False, "execution_status": "input_error", "valid": False, "errors": [str(exc)]}
    return run_codex_exec_exploration(request, execute=execute).as_dict()


@mcp.tool()
def llm_explore_request_start_tool(
    text: str,
    context: str = "",
    model: str = DEFAULT_EXPLORATION_CODEX_MODEL,
    timeout_seconds: int = DEFAULT_EXPLORATION_TIMEOUT_SECONDS,
    working_directory: str = "",
    include_schema: bool = False,
) -> dict[str, object]:
    """Start the isolated LLM exploration reviewer as a pollable background job."""
    deterministic_exploration = explore_request(text=text, context=context, strict=True)
    try:
        request = CodexExecExplorationRequest.from_mapping(
            {
                "text": text,
                "context": context,
                "deterministic_exploration": deterministic_exploration,
            },
            model=model,
            timeout_seconds=timeout_seconds,
            working_directory=working_directory or None,
            codex_binary="codex",
            include_schema_in_prompt=include_schema,
        )
    except ValueError as exc:
        return {
            "job_id": None,
            "state": "input_error",
            "done": True,
            "running": False,
            "process_finished": False,
            "exploration_received": False,
            "response_state": "input_error",
            "valid": False,
            "errors": [str(exc)],
        }
    return _exploration_jobs.start(request, metadata={"kind": "llm_explore_request"})


@mcp.tool()
def llm_exploration_status_tool(job_id: str, include_result: bool = True, include_prompt: bool = False) -> dict[str, object]:
    """Return a background LLM exploration job state: running, completed, failed, timed_out, or not_found."""
    return _exploration_jobs.get(job_id, include_result=include_result, include_prompt=include_prompt)


@mcp.tool()
def understand_target_tool(text: str, context: str = "", strict: bool = True, profile: str = "default") -> dict[str, object]:
    """Audit whether the target, purpose, value, non-goals, unknowns, and validation route are understood."""
    return apply_severity_profile(understand_target(text=text, context=context, strict=strict), profile)


@mcp.tool()
def audit_request_tool(
    text: str,
    context: str = "",
    strict: bool = True,
    kind: str = "requirement",
    profile: str = "default",
    logical_trace: str = "summary",
) -> dict[str, object]:
    """Audit requirements or documents with kind-aware checks."""
    result = apply_severity_profile(audit_request(text=text, context=context, strict=strict, input_kind=kind), profile)
    return apply_logical_trace_mode(result, logical_trace)


@mcp.tool()
def audit_decision_state_tool(
    text: str,
    context: str = "",
    strict: bool = True,
    kind: str = "document",
    profile: str = "default",
) -> dict[str, object]:
    """Expose decided, undecided, hypothetical, inferred, value-judgment, and evidence-gap states without resolving them."""
    return apply_severity_profile(audit_decision_state(text=text, context=context, strict=strict, input_kind=kind), profile)


@mcp.tool()
def audit_plan_tool(
    plan: str,
    request: str = "",
    context: str = "",
    strict: bool = True,
    kind: str = "plan",
    profile: str = "default",
) -> dict[str, object]:
    """Audit an implementation plan for scope, decomposition, risk, verification, validation, and completion evidence."""
    return apply_severity_profile(audit_plan(plan=plan, request=request, context=context, strict=strict, input_kind=kind), profile)


@mcp.tool()
def audit_diff_tool(
    diff: str,
    intent: str = "",
    context: str = "",
    strict: bool = True,
    kind: str = "diff-summary",
    profile: str = "default",
) -> dict[str, object]:
    """Audit a diff or change summary for traceability, meaning preservation, quality, security, tests, and docs."""
    return apply_severity_profile(audit_diff(diff=diff, intent=intent, context=context, strict=strict, input_kind=kind), profile)


@mcp.tool()
def finish_check_tool(
    summary: str,
    evidence: str = "",
    context: str = "",
    strict: bool = True,
    profile: str = "default",
) -> dict[str, object]:
    """Audit completion evidence, acceptance evidence, residual risk, and release blockers."""
    return apply_severity_profile(finish_check(summary=summary, evidence=evidence, context=context, strict=strict), profile)


@mcp.tool()
def audit_conventions_tool(
    text: str,
    context: str = "",
    strict: bool = True,
    kind: str = "document",
    profile: str = "default",
) -> dict[str, object]:
    """Audit public I/O, CLI, MCP, error, record, and repository-profile convention coverage."""
    return apply_severity_profile(audit_conventions(text=text, context=context, strict=strict, input_kind=kind), profile)


@mcp.tool()
def conventions_catalog_tool() -> dict[str, object]:
    """Return the machine-readable baseline convention catalog."""
    return load_conventions_catalog()


@mcp.tool()
def evaluate_fixtures_tool(path: str = str(DEFAULT_FIXTURE_ROOT), include_passed: bool = False) -> dict[str, object]:
    """Evaluate local calibration fixtures and return structured pass/fail data."""
    return evaluate_fixture_tree(path, include_passed=include_passed)


@mcp.tool()
def trace_report_tool(payload: dict[str, Any]) -> dict[str, object]:
    """Build a request-plan-diff-finish trace report from a JSON payload."""
    return build_trace_report(payload)


@mcp.tool()
def audit_result_schema_tool() -> dict[str, object]:
    """Return the shared AuditResult JSON schema."""
    return load_audit_result_schema()


@mcp.tool()
def request_exploration_review_schema_tool() -> dict[str, object]:
    """Return the LLM request-exploration review output schema."""
    return load_request_exploration_review_schema()


@mcp.tool()
def rule_detector_map_tool() -> dict[str, object]:
    """Return rule ids mapped to detector and predicate surfaces."""
    mappings = rule_detector_mappings()
    return {
        "rule_count": len(RULES),
        "mapping_count": len(mappings),
        "unmapped_rule_ids": unmapped_rule_ids(),
        "mappings": mappings,
    }


@mcp.tool()
def doctor_tool(project_root: str = ".", run_fixtures: bool = True) -> dict[str, object]:
    """Check local semantic-guard environment, schemas, mappings, CI, and fixtures."""
    return run_doctor(project_root, run_fixtures=run_fixtures)


@mcp.tool()
def llm_review_command_tool(
    payload: dict[str, Any],
    model: str = DEFAULT_CODEX_MODEL,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    working_directory: str = "",
    include_schema: bool = False,
) -> dict[str, object]:
    """Build the isolated codex exec LLM reviewer command and prompt without executing it."""
    try:
        request = CodexExecReviewRequest.from_mapping(
            payload,
            model=model,
            timeout_seconds=timeout_seconds,
            working_directory=working_directory or None,
            codex_binary="codex",
            include_schema_in_prompt=include_schema,
        )
    except ValueError as exc:
        return {"executed": False, "execution_status": "input_error", "valid": False, "errors": [str(exc)]}
    return run_codex_exec_review(request, execute=False).as_dict()


@mcp.tool()
def llm_review_run_tool(
    payload: dict[str, Any],
    execute: bool = False,
    model: str = DEFAULT_CODEX_MODEL,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    working_directory: str = "",
    include_schema: bool = False,
) -> dict[str, object]:
    """Run or dry-run the isolated codex exec LLM reviewer. Dry-run is the default."""
    try:
        request = CodexExecReviewRequest.from_mapping(
            payload,
            model=model,
            timeout_seconds=timeout_seconds,
            working_directory=working_directory or None,
            codex_binary="codex",
            include_schema_in_prompt=include_schema,
        )
    except ValueError as exc:
        return {"executed": False, "execution_status": "input_error", "valid": False, "errors": [str(exc)]}
    return run_codex_exec_review(request, execute=execute).as_dict()


@mcp.tool()
def llm_review_start_tool(
    payload: dict[str, Any],
    model: str = DEFAULT_CODEX_MODEL,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    working_directory: str = "",
    include_schema: bool = False,
) -> dict[str, object]:
    """Start the isolated codex exec LLM reviewer as a pollable background job."""
    try:
        request = CodexExecReviewRequest.from_mapping(
            payload,
            model=model,
            timeout_seconds=timeout_seconds,
            working_directory=working_directory or None,
            codex_binary="codex",
            include_schema_in_prompt=include_schema,
        )
    except ValueError as exc:
        return {
            "job_id": None,
            "state": "input_error",
            "done": True,
            "running": False,
            "process_finished": False,
            "review_received": False,
            "response_state": "input_error",
            "valid": False,
            "errors": [str(exc)],
        }
    return _review_jobs.start(request, metadata={"kind": "llm_review"})


@mcp.tool()
def review_if_needed_start_tool(
    payload: dict[str, Any],
    model: str = DEFAULT_CODEX_MODEL,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    working_directory: str = "",
    include_schema: bool = False,
) -> dict[str, object]:
    """Start an isolated reviewer job only when review-if-needed escalation says it is useful."""
    return start_review_if_needed_job(
        _review_jobs,
        payload,
        model=model,
        timeout_seconds=timeout_seconds,
        working_directory=working_directory,
        include_schema=include_schema,
    )


@mcp.tool()
def llm_review_status_tool(job_id: str, include_result: bool = True, include_prompt: bool = False) -> dict[str, object]:
    """Return a background reviewer job state: running, completed, failed, timed_out, or not_found."""
    return _review_jobs.get(job_id, include_result=include_result, include_prompt=include_prompt)


@mcp.tool()
def review_if_needed_tool(
    payload: dict[str, Any],
    execute: bool = False,
    model: str = DEFAULT_CODEX_MODEL,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    working_directory: str = "",
    include_schema: bool = False,
) -> dict[str, object]:
    """Escalate deterministic audit uncertainty to the isolated reviewer when needed. Dry-run is the default."""
    return review_if_needed(
        payload,
        execute=execute,
        model=model,
        timeout_seconds=timeout_seconds,
        working_directory=working_directory,
        include_schema=include_schema,
    )


@mcp.tool()
def acceptance_bundle_template_tool(payload: dict[str, Any]) -> dict[str, object]:
    """Build an acceptance review bundle scaffold for the final human decision."""
    try:
        return build_acceptance_review_bundle_template(payload)
    except ValueError as exc:
        return {"schema_version": "acceptance-review-bundle/v1", "input_error": str(exc)}


@mcp.tool()
def validate_acceptance_bundle_tool(bundle: dict[str, Any], strict: bool = True) -> dict[str, object]:
    """Validate an acceptance review bundle before a human final decision."""
    errors = validate_acceptance_review_bundle(bundle, strict=strict)
    return {"valid": not errors, "errors": errors}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
