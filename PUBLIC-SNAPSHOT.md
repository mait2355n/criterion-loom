# Public Snapshot 2026-06-04

## Purpose

This file records what is included in the GitHub-oriented publication snapshot and what is intentionally excluded from the local working checkout.

## Audience And Use

Use this file when checking whether the public tree contains only publishable package files, tests, fixtures, schemas, skills, and documentation. It is for maintainers preparing the repository for GitHub.

## Snapshot Contract

The snapshot should be runnable from its own root, should not depend on the local working checkout, and should avoid local-only paths, backup directories, generated caches, dated dogfood records, and private work notes.

## Status And Scope

This is the 2026-06-04 publication snapshot. It is intended as a GitHub repository source tree, not as a package release guarantee or a production readiness claim.

## Usage

From this directory, verify the snapshot with:

```sh
uv run --python 3.13 --project . semantic-guard evaluate-fixtures
uv run --python 3.13 --project . semantic-guard doctor
uv run --python 3.13 --project . python -m unittest discover -s tests -v
```

## Snapshot Fields

This file records source, included files, excluded files, and verification commands. The important review fields are `Source`, `Included`, `Excluded`, and `Verification Intent`.

## Source

- Source checkout: local working checkout
- Snapshot path: this directory

## Included

- package metadata: `.gitignore`, `LICENSE`, `README.md`, `pyproject.toml`,
  `uv.lock`
- repository support: `.github/`, `CONTRIBUTING.md`, `SECURITY.md`,
  `CHANGELOG.md`
- implementation: `src/`
- schemas: `schemas/`
- tests and fixtures: `tests/`
- companion Codex skill: `skills/semantic-implementation/`
- public-facing docs:
  - `README.ja.md`
  - `docs/README.md`
  - `docs/naming.md`
  - `docs/ja/README.md`
  - `docs/ja/naming.md`
  - `docs/ja/quickstart.md`
  - `docs/ja/company-evidence.md`
  - `docs/public-comparison-2026-06-02.md`
  - `docs/public-comparison-2026-06-02.ja.md`
  - `docs/llm-reviewer.md`
  - `docs/acceptance-review-bundle.md`
  - `docs/rule-model.md`
      - `docs/fixture-record-design.md`
      - `docs/field-corpus-2026-06-04.md`
      - `docs/calibration-report-2026-06-04.md`
      - `docs/calibration-report-2026-06-05.md`
      - `docs/release/github-publication-checklist.md`

## Excluded

- `.venv/`
- `.backups/`
- `__pycache__/` and `*.pyc`
- dated dogfood records
- conflict audits
- implementation plans
- local acceptance-bundle work records

## Verification Intent

Verify this snapshot from its own root, not from the working checkout:

```sh
uv run --python 3.13 --project . semantic-guard --help
uv run --python 3.13 --project . semantic-guard evaluate-fixtures --include-passed
uv run --python 3.13 --project . semantic-guard doctor
uv run --python 3.13 --project . semantic-guard audit-result-schema
uv run --python 3.13 --project . semantic-guard rule-detector-map
uv run --python 3.13 --project . python -m unittest discover -s tests -v
```
