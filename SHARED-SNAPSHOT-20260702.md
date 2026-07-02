# Shared Snapshot 2026-07-02

## Purpose

This directory is the shared GitHub-publication candidate for Criterion Loom /
`semantic-guard` after the expression-precision audit slice.

It is a cleaned source snapshot for review and GitHub publication work, not a
GitHub push, release approval, or final human acceptance record.

## Audience And Use

This file is for maintainers and future Codex sessions that need to resume
publication cleanup from the 2026-07-02 shared candidate.

Use it as a snapshot ledger: it names the source tree, files supplemented from
the previous public candidate, verification evidence, local cleanup checks, and
remaining publication decisions.

## Output Contract Boundary

This Markdown file does not define the CLI, MCP, API, JSON Schema, or command
output contract. Those contracts remain in `README.md`, `README.ja.md`,
`docs/conventions/`, `schemas/`, `src/`, and `skills/semantic-implementation/`.

For machine-readable audit output, rely on commands such as `audit-request`,
`audit-conventions`, `evaluate-fixtures`, `doctor`, `audit-result-schema`, and
`rule-detector-map`. Their JSON envelopes use fields such as `status`, `score`,
`findings`, `missing`, `next_actions`, and `details`.

## Sources

- Primary source tree: local development checkout used for the 2026-07-02
  expression-precision work
- Supplemental public-health files copied from the previous shared candidate:
  `semantic-guard-public-candidate-20260630`

Supplemented files:

- `SECURITY.md`
- `CODE_OF_CONDUCT.md`
- `SUPPORT.md`
- `.github/ISSUE_TEMPLATE/`
- `.github/dependabot.yml`
- `.github/pull_request_template.md`
- `docs/release/ci-workflow-template.yml`
- `docs/release/public-repository-readiness.md`
- `docs/release/public-writing-guidelines.md`
- `docs/release/publication-format.md`
- `docs/public-wording-audit-feature-brief.md`

## Current Publication Handle

Start from:

- `docs/release/github-publication-summary-2026-07-02.md`
- `docs/release/github-publication-checklist.md`
- `docs/release/expression-precision-reference-heuristic-2026-07-01.md`
- `docs/release/expression-precision-corpus-sweep-2026-07-02.md`

The raw corpus JSON is included as local calibration evidence:

- `docs/release/expression-precision-corpus-sweep-2026-07-02.raw.json`

## Documentation Cleanup Notes

After the initial shared snapshot, the public README and documentation map were
updated to keep the 2026-07-02 expression-precision work as the base while
restoring the public v0.1 wording boundary:

- `README.ja.md` now describes CLI / MCP / companion skill surfaces, agent-side
  revision, human final decision, local regression limits, and `doc.expression.*`
  checks.
- `README.md` now presents the candidate as a publishable v0.1 tool with
  maintained CLI, MCP, skill, schema, fixture, convention-audit, and CI-template
  surfaces.
- `PUBLIC-SNAPSHOT.md` now reflects the 2026-07-02 candidate and current
  expression-precision scope.
- `docs/README.md` separates public-facing documents from secondary working
  records.

These wording edits still need full dependency-backed verification in the final
publish environment, but the public entry documents have been rechecked with the
local commands listed below.

## Verification

The initial expression-precision snapshot was verified with the project
environment kept outside the snapshot:

```sh
UV_PROJECT_ENVIRONMENT=/tmp/semantic_guard_public_candidate_20260702_venv \
  uv run --python 3.13 --project . python -m compileall src/semantic_guard tests
UV_PROJECT_ENVIRONMENT=/tmp/semantic_guard_public_candidate_20260702_venv \
  uv run --python 3.13 --project . python -m unittest discover -s tests -v
UV_PROJECT_ENVIRONMENT=/tmp/semantic_guard_public_candidate_20260702_venv \
  uv run --python 3.13 --project . semantic-guard evaluate-fixtures
UV_PROJECT_ENVIRONMENT=/tmp/semantic_guard_public_candidate_20260702_venv \
  uv run --python 3.13 --project . semantic-guard doctor
UV_PROJECT_ENVIRONMENT=/tmp/semantic_guard_public_candidate_20260702_venv \
  uv run --python 3.13 --project . python -m json.tool docs/release/expression-precision-corpus-sweep-2026-07-02.raw.json
```

Observed results:

- compileall completed.
- unit tests: 217 passed.
- fixture evaluation: 45/45 passed.
- doctor: 9 checks passed, 0 warnings, 0 blockers.
- corpus raw JSON parsed successfully.
- final hygiene scan printed no `.git`, `.venv`, `.pytest_cache`, `.backups`,
  `__pycache__`, `*.pyc`, or `.DS_Store` paths.
- dated handoff documents were sanitized so local machine paths are represented
  as placeholders. Remaining absolute-path marker strings are limited to the
  source detector pattern and the publication checklist example.

Post-cleanup checks run in the local documentation-cleanup environment:

- Python AST parse over `src/` and `tests/`: 44 files parsed.
- JSON parse completed for `docs/conventions/base-contract.json`,
  `schemas/audit-result.schema.json`,
  `schemas/request-exploration-review.schema.json`, and
  `docs/release/expression-precision-corpus-sweep-2026-07-02.raw.json`.
- `semantic-guard evaluate-fixtures`: 45/45 passed.
- Document audits:
  - `audit-request --kind document` passed for `README.md`, `README.ja.md`, and
    `docs/README.md`.
  - `audit-conventions --kind document` passed for `README.md`,
    `README.ja.md`, and `docs/public-wording-audit-feature-brief.md`.
- Hygiene scan printed no `.git`, `.venv`, `.pytest_cache`, `.backups`,
  `__pycache__`, `*.pyc`, or `.DS_Store` paths.
- Local absolute-path scan only found the source detector pattern and the
  publication checklist example.

The local cleanup environment did not have `uv`, `jsonschema`, or the `mcp`
package installed. A direct `doctor --no-fixtures` run therefore reported one
blocker: `mcp.server.fastmcp` could not be imported. Re-run the full `uv`
verification in the final publish environment before pushing.

## Do Not Claim

- Do not claim this snapshot has already been pushed to GitHub.
- Do not claim fixture or corpus results prove general natural-language
  understanding accuracy.
- Do not claim Criterion Loom replaces human judgment, release review, legal
  review, security scanning, or final acceptance.

## Next Action

Review the publication summary, decide whether to keep the raw corpus JSON and
secondary working records in the public repository, then initialize or copy this
snapshot into the actual GitHub publication flow.
