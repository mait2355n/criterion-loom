# Changelog

All notable public-facing changes should be recorded here.

This project does not yet have versioned public releases. Dates below describe publication snapshots, not release guarantees.

## Purpose

This changelog records user-visible repository, CLI, MCP, fixture, schema, and documentation changes. It is not a release-readiness claim.

## Audience And Use

Use this file to understand what changed between public snapshots or future releases before reading detailed docs or diffs.

## Status And Scope

Current entries describe repository snapshots and unreleased work. They do not imply package publication, production readiness, or broad detector accuracy.

## Entry Contract

Each entry should identify the date or version, the affected surface, the change summary, and any caveat about calibration or public claims.

Entry fields are date or version, affected surface, change summary, verification note, and public-claim caveat.

Verification commands for a snapshot are normally:

```sh
uv run --python 3.13 --project . python -m unittest discover -s tests -v
uv run --python 3.13 --project . semantic-guard evaluate-fixtures --include-passed
uv run --python 3.13 --project . semantic-guard doctor
```

## Unreleased

- Add the Criterion Loom public naming map: Loom Guide, Need Thread, Plan Warp, and Change Weft, while keeping `semantic-guard` as the package, CLI, and MCP server name.
- Add GitHub repository support files: CI workflow, issue templates, pull request template, contributing guide, security policy, and release checklist.

## 2026-06-05 Public Maturity Pass

- Add `doctor`, `audit-result-schema`, and `rule-detector-map` CLI/MCP support commands.
- Add the common audit-result JSON Schema at `schemas/audit-result.schema.json`.
- Add catalog-to-detector mapping coverage for all 36 current catalog rules.
- Update GitHub Actions CI to verify Python 3.11 and 3.13 with compile, unit tests, fixture evaluation, and `doctor`.
- Promote three accepted field-corpus examples into deterministic fixtures, raising the local fixture count from 36 to 39.
- Keep the same caveat: local fixture pass rate and rule coverage are calibration signals only, not broad detector accuracy.

## 2026-06-04 Public Snapshot

- Publish a runnable `semantic-guard` snapshot with CLI, MCP server, tests, fixtures, schemas, public documentation, and the companion `semantic-implementation` skill.
- Include Japanese usage and quickstart documents.
- Expand local calibration fixtures to 36 deterministic fixture expectations.
- Add a 30-entry field corpus for good warnings, noisy warnings, and likely misses.
- Keep explicit non-claims: not a security scanner, not a release gate, not a formal requirements verifier, and not a replacement for human final acceptance.
