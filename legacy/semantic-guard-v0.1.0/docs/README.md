# Documentation Map

This directory contains public-facing documents and working records for
Criterion Loom.

The technical package, CLI, and MCP server names remain `semantic-guard`.

## Purpose

This map helps a new reader find the current publication surface before reading
dated work notes.

The repository has many dogfood records and implementation notes. They are
useful history, but the recommended public entry points are the README, current
name map, positioning documents, reviewer-boundary documents, rule model,
fixture format, audit-result schema, doctor command, and calibration snapshot
listed below.

Japanese manuals for Criterion Loom usage and company-facing evidence are available under
`docs/ja/`, with the top-level Japanese entry point at `../README.ja.md`.

## Usage

Start from the repository root:

```sh
uv run --python 3.13 --project . semantic-guard explore-request --text "割り勘アプリを作りたい"
uv run --python 3.13 --project . semantic-guard llm-explore-request --text "割り勘アプリを作りたい" --dry-run
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
- `../SECURITY.md`: security-reporting policy and scope limits.
- `../CHANGELOG.md`: public snapshot and future change log.
- `ja/README.md`: Japanese documentation map.
- `ja/naming.md`: Japanese public names and technical-name mapping.
- `ja/quickstart.md`: Japanese quickstart and demonstration commands.
- `ja/company-evidence.md`: Japanese company-facing achievement evidence guide.
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
- `../skills/semantic-implementation/README.md`: companion Codex skill install and sync contract.
- `../skills/semantic-implementation/SKILL.md`: companion Codex skill routing.

## Working Records

Dated design notes, dogfood records, conflict audits, implementation plans, and
acceptance bundles are working records. They may explain why a decision exists,
but they are secondary material for a new reader.

When a working record conflicts with the README or the public-facing set above,
treat the README and current public-facing documents as the publication surface,
then inspect the dated record only for history.
