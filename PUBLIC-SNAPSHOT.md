# Public Snapshot 2026-06-30

## Purpose

This file records the intended GitHub publication shape for Criterion Loom,
whose package, CLI, and MCP server name remains `semantic-guard`.

## Audience And Use

Use this file when checking whether the repository tree is suitable to publish
as a public GitHub repository. It records maintainer publication intent.
Downstream users should rely on tagged releases, CI results, and package
metadata rather than treating this file as a release-readiness statement.

## Snapshot Contract

The public tree should be runnable from its own root, should not depend on a
private working checkout, and should avoid local-only paths, backup directories,
generated caches, dated dogfood records, conflict-audit records, and local
acceptance-bundle work files.

## Status And Scope

This is a GitHub-oriented source candidate derived from the 2026-06-29 package
staging snapshot. It keeps the package implementation, tests, fixtures, schemas,
the companion Codex skill, repository hygiene files, and public-facing
documentation.

It is not a production-readiness claim. Criterion Loom is a publishable v0.1
tool with deterministic heuristics, local fixture calibration, optional LLM
review helpers, and a final human-decision boundary.

## Included

- package metadata: `.gitignore`, `LICENSE`, `README.md`, `README.ja.md`,
  `pyproject.toml`, `uv.lock`
- repository support: `.github/`, `CONTRIBUTING.md`, `SECURITY.md`,
  `CODE_OF_CONDUCT.md`, `SUPPORT.md`, `CHANGELOG.md`
- implementation: `src/`
- schemas: `schemas/`
- tests, fixtures, and field corpus: `tests/`
- companion Codex skill: `skills/semantic-implementation/`
- public-facing docs:
  - `docs/README.md`
  - `docs/naming.md`
  - `docs/ja/README.md`
  - `docs/ja/naming.md`
  - `docs/ja/quickstart.md`
  - `docs/public-comparison-2026-06-02.md`
  - `docs/public-comparison-2026-06-02.ja.md`
  - `docs/llm-reviewer.md`
  - `docs/ambiguity-confidence-design.md`
  - `docs/public-wording-audit-feature-brief.md`
  - `docs/acceptance-review-bundle.md`
  - `docs/conventions/`
  - `docs/rule-model.md`
  - `docs/fixture-record-design.md`
  - `docs/field-corpus-2026-06-04.md`
  - `docs/calibration-report-2026-06-04.md`
  - `docs/calibration-report-2026-06-05.md`
  - `docs/release/github-publication-checklist.md`
  - `docs/release/ci-workflow-template.yml`
  - `docs/release/public-writing-guidelines.md`
  - `docs/release/publication-format.md`
  - `docs/release/public-repository-readiness.md`

The active GitHub Actions workflow is intentionally not included in
`.github/workflows/` for the initial GitHub publication. The workflow template
is kept under `docs/release/ci-workflow-template.yml` and can be restored as
`.github/workflows/ci.yml` after the publishing credential has GitHub
`workflow` scope.

## Excluded

- `.git/`
- `.venv/`
- `.backups/`
- `__pycache__/` and `*.pyc`
- `.DS_Store`
- dated dogfood records
- conflict audits and conflict-fix plans
- implementation planning records that are not part of the current public
  documentation surface
- local acceptance-bundle work records

## Verification Intent

Run from the repository root after dependencies are available:

```sh
uv run --python 3.13 --project . semantic-guard --help
uv run --python 3.13 --project . semantic-guard evaluate-fixtures --include-passed
uv run --python 3.13 --project . semantic-guard doctor
uv run --python 3.13 --project . semantic-guard audit-result-schema
uv run --python 3.13 --project . semantic-guard rule-detector-map
uv run --python 3.13 --project . python -m unittest discover -s tests -v
```

Document-audit entry points:

```sh
uv run --python 3.13 --project . semantic-guard audit-request --kind document --file README.md
uv run --python 3.13 --project . semantic-guard audit-request --kind document --file README.ja.md
uv run --python 3.13 --project . semantic-guard audit-conventions --kind document --file README.md
```

## Evidence Sources

Publication suitability should be judged from these records together:

- this included/excluded file list;
- `docs/release/github-publication-checklist.md`;
- `docs/release/publication-format.md`;
- the final publish-environment command log;
- GitHub Actions results after the workflow template is restored.

## Local Recheck Notes

This copied candidate was locally inspected in an environment with Python 3.12.5
but without `uv`, `pytest`, or the `mcp` package available. In that environment:

- direct CLI document audits for `README.md` and `README.ja.md` passed;
- direct CLI convention audit for `README.md` passed;
- direct `doctor` ran, blocked on the missing `mcp` dependency, and warned
  that the active GitHub Actions workflow is deferred to the release template;
- fixture evaluation through `doctor` reported 45/45 passed;
- direct `evaluate-fixtures` reported 45/45 passed;
- `audit-result-schema` and `rule-detector-map` printed successfully, with
  41/41 detector mappings and no unmapped rule ids;
- `python3 -m unittest discover -s tests -v` ran 184 tests but did not pass in
  this dependency-incomplete environment: 1 failure and 2 errors were tied to
  the missing `mcp` dependency and `doctor` status expectations;
- `python3 -m compileall src/semantic_guard tests` passed before generated
  cache files were removed from the candidate.

The earlier package staging note records broader verification on Python 3.11 and
Python 3.13. Re-run the full verification commands above in the final publish
environment before pushing.
