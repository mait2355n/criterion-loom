# Logical Audit Third Rule Bundle 2026-06-02

## Purpose

This document records the first post-summary expansion of the logical-audit rule set.

The goal is not to migrate every request rule. The goal is to add rules whose current findings already have deterministic request facts and stable scope conditions.

## Audience And Use

Use this document when deciding whether the next logical-audit expansion preserved the earlier derivation boundary, when checking why these five rules were chosen, or when adding a later structure/profile bundle.

This is a change-control record for maintainers and Codex work, not a public release note or final acceptance record.

## Output Mode Change

CLI and MCP `audit-request` now default to logical trace `summary`.

Available modes:

- `summary`: emit `details.logical_trace_summary`, omit full `details.logical_trace`.
- `full`: emit both summary and full trace.
- `none`: omit both logical trace surfaces.

Core `audit_request()` keeps full trace output for compatibility with tests, fixture evaluation, and direct Python callers.

## Added Executable Rules

This bundle adds logical trace and `finding.derivation` support for:

- `req.achievement.criteria_missing`
- `req.evidence.artifact_missing`
- `req.acceptance.rejection_condition_missing`
- `req.context.scenario_missing`
- `req.structure.observable_behavior_missing`

Together with the earlier two rules, current request logical-audit output evaluates seven rules:

- `req.verifiability.acceptance_missing`
- `req.achievement.criteria_missing`
- `req.verification.method_detail_missing`
- `req.evidence.artifact_missing`
- `req.acceptance.rejection_condition_missing`
- `req.context.scenario_missing`
- `req.structure.observable_behavior_missing`

## Selection Boundary

Included rules had to satisfy all of these conditions:

- Existing `audit-request` already emitted a corresponding finding.
- The finding condition already had deterministic request facts or structure/profile fields.
- The rule could be expressed as input-kind countercondition, scope countercondition, obligation, and categorical derivation status.
- The derivation does not need LLM-reviewed facts.

Deferred rules:

- `req.scope.non_goals_missing`: already has `non_emitted_rules` / suppression tracing and should be migrated separately.
- `req.context.precondition_trigger_missing`, `req.result.expected_result_missing`, `req.interface.contract_missing`: candidates for a later structure-focused bundle.
- `req.stakeholder.source_missing`, `req.quality.measurable_constraint_missing`, `req.priority.multiple_requirements_unprioritized`, `req.uncertainty.unclassified_uncertainty`: candidates for later profile and classification bundles.

## Non-Claims

The added derivations do not prove natural-language truth, semantic satisfaction, safety, release readiness, or human acceptance.

The derivations only say that, within the current extracted facts and executable predicate, the rule status was derived, satisfied, not applicable, blocked, or conflicted.

## Fixture Coverage

New request fixtures pin the summary-rule shape for the added rules:

- `tests/fixtures/requests/achievement-criteria-missing.expected.json`
- `tests/fixtures/requests/evidence-artifact-missing.expected.json`
- `tests/fixtures/requests/rejection-condition-missing.expected.json`
- `tests/fixtures/requests/scenario-context-missing.expected.json`
- `tests/fixtures/requests/observable-behavior-missing.expected.json`

These fixtures prefer `logical_trace_summary_rule` over full `logical_trace_rule` to avoid brittle full-trace expectations.

## Verification Evidence

Representative commands:

```sh
uv run --python 3.13 --project . python -m unittest tests.test_logic tests.test_core tests.test_mcp_tools -v
uv run --python 3.13 --project . python -m unittest tests.test_evaluation tests.test_fixtures -v
uv run --python 3.13 --project . semantic-guard evaluate-fixtures --include-passed
uv run --python 3.13 --project . semantic-guard audit-request --text '目的: 速度改善をしたい。'
uv run --python 3.13 --project . semantic-guard audit-request --logical-trace full --text '目的: 速度改善をしたい。'
uv run --python 3.13 --project . semantic-guard audit-request --logical-trace none --text '目的: 速度改善をしたい。'
```

Observed result:

- Targeted logic/core/MCP tests passed.
- Full test suite passed: 129 tests OK.
- Compile check passed.
- Fixture and evaluation tests passed.
- `evaluate-fixtures --include-passed` reported 21 total, 21 passed, pass rate 1.0.
- CLI `summary` omitted `details.logical_trace` and kept `details.logical_trace_summary`.
- CLI `full` emitted seven evaluated rules in `details.logical_trace`.
- CLI `none` omitted logical trace and summary fields.
