# Documentation Map

This directory contains the public-facing documentation set for Criterion Loom.

The technical package, CLI, and MCP server names remain `semantic-guard`.

## Purpose

This map gives a new reader the intended public entry points without requiring
them to read dated work notes or private development history.

## Usage

Start from the repository root:

```sh
uv run --python 3.13 --project . semantic-guard explore-request --text "split-bill app"
uv run --python 3.13 --project . semantic-guard llm-explore-request --text "split-bill app" --dry-run
uv run --python 3.13 --project . semantic-guard audit-request --kind document --file README.md
uv run --python 3.13 --project . semantic-guard audit-request --kind document --file docs/calibration-report-2026-06-05.md
uv run --python 3.13 --project . semantic-guard evaluate-fixtures
uv run --python 3.13 --project . semantic-guard doctor
uv run --python 3.13 --project . semantic-guard audit-conventions --file docs/conventions/base-contract.md
uv run --python 3.13 --project . semantic-guard audit-result-schema
uv run --python 3.13 --project . semantic-guard request-exploration-review-schema
uv run --python 3.13 --project . semantic-guard rule-detector-map
uv run --python 3.13 --project . semantic-guard conventions-catalog
```

Use this file as a navigation aid, not as a replacement for the linked
documents.

## Public-Facing Set

Use these first when preparing a public repository, README copy, release notes,
or comparison material:

- `../README.md`: current status, setup, commands, output shape, and limits.
- `../README.ja.md`: Japanese usage guide, boundaries, commands, and output reading notes.
- `naming.md`: public names and technical-name mapping.
- `../CONTRIBUTING.md`: contribution and verification rules.
- `../CODE_OF_CONDUCT.md`: public discussion and conduct boundary.
- `../SUPPORT.md`: support routing and issue-quality expectations.
- `../SECURITY.md`: security-reporting policy and scope limits.
- `../CHANGELOG.md`: public snapshot and future change log.
- `ja/README.md`: Japanese documentation map.
- `ja/naming.md`: Japanese public names and technical-name mapping.
- `ja/quickstart.md`: Japanese quickstart and demonstration commands.
- `public-comparison-2026-06-02.md`: English public positioning and non-claims.
- `public-comparison-2026-06-02.ja.md`: Japanese public positioning and non-claims.
- `llm-reviewer.md`: LLM reviewer role boundary.
- `ambiguity-confidence-design.md`: deterministic ambiguity, confidence, and review-routing-pressure boundary.
- `acceptance-review-bundle.md`: final human-review bundle contract.
- `conventions/README.md`: cross-repository coding and I/O convention source of truth.
- `rule-model.md`: rule catalog model.
- `fixture-record-design.md`: fixture record and local calibration format.
- `field-corpus-2026-06-04.md`: field-corpus review backlog and promotion rule.
- `calibration-report-2026-06-05.md`: current calibration snapshot.
- `../schemas/audit-result.schema.json`: common audit-result JSON Schema.
- `release/github-publication-checklist.md`: GitHub publication checklist.
- `release/publication-format.md`: recommended repository shape and publication sequence.
- `release/public-repository-readiness.md`: public health file and presentation review.
- `../skills/semantic-implementation/README.md`: companion Codex skill install and sync contract.
- `../skills/semantic-implementation/SKILL.md`: companion Codex skill routing.

## Archival Material

Dated design notes, dogfood records, conflict audits, implementation plans, and
acceptance-bundle work records are intentionally excluded from this public
candidate. They may remain useful in private history, but they should not be the
first surface a public reader sees.

If an archival record is later promoted into the public repository, rewrite it
as current documentation first: name its audience, status, maintained claims,
non-goals, and verification evidence.
