# Public Snapshot

## Purpose

This file records what is included in the GitHub-oriented publication snapshot and what is intentionally excluded from the local working checkout.

## Audience And Use

Use this file when checking whether the public tree contains only publishable package files, tests, fixtures, schemas, skills, and documentation. It is for maintainers preparing the repository for GitHub.

## Snapshot Contract

The snapshot should be runnable from its own root and should not depend on the
local working checkout. Local-only paths, backup directories, generated caches,
private work notes, and unredacted private inputs stay out. Selected dated
design, audit, and acceptance records may remain as historical evidence only
after hygiene review; they are not current guidance or public-contract sources.

## Status And Scope

The initial source snapshot was prepared on 2026-06-04. Publication hygiene was
revised on 2026-07-16. This is a GitHub repository source tree, not a package
release guarantee or a production readiness claim.

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
- selected dated design, dogfood, audit, and acceptance records under `docs/`
  that passed the same local-path and sensitive-material review. These files
  preserve implementation history and do not override the README, schemas, or
  current public-facing documents.

## Excluded

- `.venv/`
- `.backups/`
- `__pycache__/` and `*.pyc`
- private or machine-specific work records
- unredacted local inputs and acceptance material
- generated build, test, or reviewer output that is not selected evidence

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
