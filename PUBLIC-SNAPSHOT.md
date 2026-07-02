# Public Snapshot 2026-07-02

## Purpose

This file records the intended GitHub publication shape for Criterion Loom,
whose package, CLI, and MCP server name remains `semantic-guard`.

## Audience And Use

Use this file when checking whether the 2026-07-02 candidate tree is suitable
to publish as a public GitHub repository or to use as the base for publication
cleanup.

This file records maintainer publication intent. Downstream users should rely
on tagged releases, CI results, and package metadata rather than treating this
file as release approval.

## Snapshot Contract

The public tree should be runnable from its own root, should not depend on a
private working checkout, and should avoid local-only paths, backup
directories, generated caches, private notes, and unreviewed work records.

## Status And Scope

This is the 2026-07-02 shared publication candidate after the
expression-precision audit slice.

It keeps the package implementation, tests, fixtures, schemas, the companion
Codex skill, public health files, CI workflow template,
expression-precision documents, and public-facing documentation.

It is not a production-readiness claim. Criterion Loom is a publishable v0.1
tool with deterministic heuristics, local fixture calibration, optional LLM
review helpers, expression-precision convention checks, and a final
human-decision boundary.

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
  - `docs/release/github-publication-summary-2026-07-02.md`
  - `docs/release/expression-precision-reference-heuristic-2026-07-01.md`
  - `docs/release/expression-precision-corpus-sweep-2026-07-02.md`
  - `docs/release/ci-workflow-template.yml`
  - `docs/release/public-repository-readiness.md`
  - `docs/release/public-writing-guidelines.md`
  - `docs/release/publication-format.md`

## Secondary Working Records

This candidate still contains dated design notes, dogfood records, comparison
drafts, implementation plans, and handoff records. They are secondary context,
not the first publication surface.

Before a final GitHub push, either archive them under a clearly named working
record area, exclude them from the source tree, or rewrite them as maintained
documentation.

## Excluded From Final Publication Unless Rewritten

- `.git/`
- `.venv/`
- `.backups/`
- `__pycache__/` and `*.pyc`
- `.DS_Store`
- raw local build outputs
- private machine paths
- local acceptance-bundle drafts
- conflict-audit and conflict-fix records that have not been rewritten
- dated dogfood notes that are not referenced as maintained calibration
  evidence

## Verification Intent

Run from the repository root after dependencies are available:

```sh
uv run --python 3.13 --project . python -m compileall src/semantic_guard tests
uv run --python 3.13 --project . python -m unittest discover -s tests -v
uv run --python 3.13 --project . semantic-guard evaluate-fixtures --include-passed
uv run --python 3.13 --project . semantic-guard doctor
uv run --python 3.13 --project . semantic-guard audit-result-schema
uv run --python 3.13 --project . semantic-guard rule-detector-map
uv run --python 3.13 --project . python -m json.tool docs/release/expression-precision-corpus-sweep-2026-07-02.raw.json
```

Document-audit entry points:

```sh
uv run --python 3.13 --project . semantic-guard audit-request --kind document --file README.md
uv run --python 3.13 --project . semantic-guard audit-request --kind document --file README.ja.md
uv run --python 3.13 --project . semantic-guard audit-conventions --kind document --file README.md
uv run --python 3.13 --project . semantic-guard audit-conventions --kind document --file README.ja.md
```

## Evidence Sources

Publication suitability should be judged from these records together:

- this included/excluded file list;
- `SHARED-SNAPSHOT-20260702.md`;
- `docs/release/github-publication-summary-2026-07-02.md`;
- `docs/release/github-publication-checklist.md`;
- `docs/release/publication-format.md`;
- final publish-environment command logs;
- GitHub Actions results after publication.

## Do Not Claim

- Do not claim fixture or corpus results prove general natural-language
  understanding accuracy.
- Do not claim Criterion Loom replaces human judgment, release review, legal
  review, security scanning, or final acceptance.
- Do not claim dated working records are the current public contract when they
  disagree with README, schemas, or maintained docs.
