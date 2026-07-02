# Publication Format

## Purpose

This document describes the recommended GitHub repository shape for publishing
Criterion Loom as `semantic-guard`.

## Audience And Use

This document is for maintainers preparing the first public GitHub repository or
reviewing a publication candidate before push. Use it to decide what belongs in
the source tree, what should stay archival, and which verification commands must
be rerun in the final publish environment.

## Repository Shape

Keep the public repository as a source-first Python package with a companion
Codex skill:

```text
.
├── .github/
│   ├── ISSUE_TEMPLATE/
│   └── pull_request_template.md
├── docs/
│   ├── ja/
│   ├── release/
│   ├── conventions/
│   └── README.md
├── schemas/
├── skills/semantic-implementation/
├── src/semantic_guard/
├── tests/
├── README.md
├── README.ja.md
├── LICENSE
├── CONTRIBUTING.md
├── SECURITY.md
├── CHANGELOG.md
├── PUBLIC-SNAPSHOT.md
├── pyproject.toml
└── uv.lock
```

## Public Entry Points

Use these as the first layer of public documentation:

- `README.md`: English main entry point, status, install, CLI, MCP, skill, output contract, and limits.
- `README.ja.md`: Japanese main entry point with practical usage and evidence boundaries.
- `docs/README.md`: documentation map.
- `docs/public-comparison-2026-06-02.md`: comparison against adjacent tools and what this project is not.
- `docs/conventions/README.md`: baseline convention and expression-precision audit map.
- `docs/public-wording-audit-feature-brief.md`: public wording precision requirements and README.ja.md review indicators.
- `docs/release/github-publication-checklist.md`: pre-push checklist.
- `docs/release/expression-precision-reference-heuristic-2026-07-01.md`: demonstrative-reference heuristic boundary.
- `docs/release/expression-precision-corpus-sweep-2026-07-02.md`: corpus sweep summary for expression-precision threshold design.
- `PUBLIC-SNAPSHOT.md`: included/excluded publication contract.

## Publication Sequence

1. Publish the cleaned source tree as the first GitHub repository.
2. Keep package distribution artifacts out of the repository unless they are
   produced by a release workflow.
3. Add repository URLs and badges only after the real repository exists.
4. Re-run full verification in the final publish environment.
5. Restore the CI template as `.github/workflows/ci.yml` when the publishing
   credential has GitHub `workflow` scope.
6. Tag a first public release only after CI passes on GitHub.

## What To Keep Private Or Archival

Do not include these in the first public surface:

- private working-checkout paths or host-specific staging notes;
- `.git/`, `.venv/`, `.backups/`, `.DS_Store`, `__pycache__/`, `*.pyc`;
- dated dogfood notes;
- conflict-audit logs and conflict-fix plans;
- implementation planning records that have not been rewritten as maintained docs;
- local acceptance-bundle work records;
- built `dist/` artifacts copied from local staging.

## Claims Discipline

The public repository should be explicit about these boundaries:

- fixture pass rate is local calibration evidence, not general accuracy;
- `doctor` is a project-shape diagnostic, not a security or release authority;
- LLM reviewer output is supplemental evidence, not final acceptance;
- final human decision remains outside the tool;
- this is a publishable v0.1 tool, not a completed requirements-engineering engine.

For concrete wording rules, see `docs/release/public-writing-guidelines.md`.

## Verification

Run from the repository root:

```sh
uv run --python 3.13 --project . semantic-guard --help
uv run --python 3.13 --project . semantic-guard evaluate-fixtures --include-passed
uv run --python 3.13 --project . semantic-guard doctor
uv run --python 3.13 --project . semantic-guard audit-request --kind document --file README.md
uv run --python 3.13 --project . semantic-guard audit-request --kind document --file README.ja.md
uv run --python 3.13 --project . semantic-guard audit-conventions --kind document --file README.md
uv run --python 3.13 --project . python -m unittest discover -s tests -v
```

Record the command results in release notes before pushing a public tag.
