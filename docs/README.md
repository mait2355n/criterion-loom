# Documentation Map

This directory contains the public-facing documentation set and secondary
working records for Criterion Loom.

The technical package, CLI, and MCP server names remain `semantic-guard`.

## Purpose

This map helps a new reader find the current publication surface before reading
dated work notes.

The repository has dogfood records and implementation notes. They are useful
history, but the recommended public entry points are the README, current name
map, positioning documents, expression-precision notes, reviewer-boundary
documents, rule model, fixture format, audit-result schema, doctor command, and
calibration snapshot listed below.

Dated working records may still contain wording that the current
`audit-conventions --kind document` rules would flag. Treat those findings as
history and calibration material unless the same wording appears in the README,
current maps, quickstarts, skill contract, or release-facing publication notes.

Japanese manuals for Criterion Loom usage are available under `docs/ja/`, with
the top-level Japanese entry point at `../README.ja.md`.

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

Normal audit commands write JSON to stdout with `phase`, `status`, `score`,
`findings`, `missing`, `next_actions`, and `details`. CLI usage errors write
argparse messages to stderr and exit with code 2. The detailed CLI/MCP contract
lives in `../skills/semantic-implementation/references/mcp-contract.md`.

## Public-Facing Set

Use these first when preparing a public repository, README copy, release notes,
or comparison material:

- `../README.md`: current status, setup, commands, output shape, and limits.
- `../README.ja.md`: Japanese usage guide, boundaries, commands, and output reading notes.
- `naming.md`: public names and technical-name mapping.
- `../CONTRIBUTING.md`: contribution and verification rules.
- `../SECURITY.md`: security-reporting policy and scope limits.
- `../SUPPORT.md`: support routing and issue-quality expectations.
- `../CHANGELOG.md`: public snapshot and future change log.
- `ja/README.md`: Japanese documentation map.
- `ja/naming.md`: Japanese public names and technical-name mapping.
- `ja/quickstart.md`: Japanese quickstart and demonstration commands.
- `public-comparison-2026-06-02.md`: English public positioning and non-claims.
- `public-comparison-2026-06-02.ja.md`: Japanese public positioning and non-claims.
- `llm-reviewer.md`: LLM reviewer role boundary.
- `ambiguity-confidence-design.md`: deterministic ambiguity, confidence, and review-routing-pressure boundary.
- `public-wording-audit-feature-brief.md`: requirements and applied README.ja.md indicators for public wording precision audit.
- `acceptance-review-bundle.md`: final human-review bundle contract.
- `conventions/README.md`: cross-repository coding and I/O convention source of truth.
- `rule-model.md`: rule catalog model.
- `fixture-record-design.md`: fixture record and local calibration format.
- `field-corpus-2026-06-04.md`: field-corpus review backlog and promotion rule.
- `calibration-report-2026-06-05.md`: current calibration snapshot.
- `../schemas/audit-result.schema.json`: common audit-result JSON Schema.
- `release/github-publication-checklist.md`: GitHub publication checklist.
- `release/github-publication-summary-2026-07-02.md`: publication handoff for the current publishable v0.1 snapshot with expression-precision audit.
- `release/expression-precision-reference-heuristic-2026-07-01.md`: implementation boundary for unclear demonstrative-reference detection.
- `release/expression-precision-corpus-sweep-2026-07-02.md`: local corpus sweep summary for expression-precision threshold design.
- `release/expression-contract-family-implementation-2026-07-02.md`: implementation note for capability and mapping contract-family expression findings.
- `release/expression-operation-ambiguity-scan-2026-07-02.md`: operation-wording ambiguity scan and triage source.
- `release/llm-document-expression-audit-triage-2026-07-02.md`: triage note for LLM-suggested document-expression findings.
- `release/plan-ir-contradiction-priority-design-2026-07-02.md`: plan-rule priority design note for contradiction and release-profile findings.
- `release/public-writing-guidelines.md`: public wording and claim-boundary rules.
- `release/publication-format.md`: recommended repository shape and publication sequence.
- `release/public-repository-readiness.md`: public health file and presentation review.
- `../skills/semantic-implementation/README.md`: companion Codex skill install and sync contract.
- `../skills/semantic-implementation/SKILL.md`: companion Codex skill routing.

## Working Records

Dated design notes, dogfood records, conflict audits, implementation plans, and
acceptance bundles are working records. They may explain why a decision exists,
but they are secondary material for a new reader.

- `expression-precision-audit-handoff-2026-06-30.md`: restart note for the planned expression-precision audit feature. Read it after repository reconciliation and before implementing `doc.expression.*` rules.
- `agent-revision-loop-positioning-2026-06-30.md`: earlier positioning note for the agent-side revision loop and outward wording.
- `prototypes/origin-requirement.md`: origin requirement for future prototype work and concept-drift checks.
- `ja/public-positioning-note.md`: Japanese claim-boundary note for public positioning; not a public README substitute.
- `release/repository-update-plan-2026-06-30.md`: repository-side update plan for the public v0.1 completion stance and audit-performance work.
- `release/repository-update-handoff-2026-06-30.md`: compact handoff for whoever applies the repository update.

When a working record conflicts with the README or the public-facing set above,
treat the README and current public-facing documents as the publication surface,
then inspect the dated record only for history.
