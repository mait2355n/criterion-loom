# Public Surface: Criterion Loom / semantic-guard 1.1.0

Documentation date: 2026-08-24

This file describes the current public source contract. It is not release-artifact evidence, a deployment record, or a claim that every repository document describes the current implementation.

## Identity

- Public project and repository name: Criterion Loom / `criterion-loom`
- Distribution: `semantic-guard`
- Version: `1.1.0`
- CLI: `semantic-guard`
- MCP server: `semantic-guard-mcp`
- Python package: `semantic_guard`
- Canonical repository object: `canonical repository object・51d473df-7d86-466d-a9f4-47a01ff70d44`, GitHub repository ID `1270877024`
- Publication-repaired predecessor: `legacy/semantic-guard-v0.1.0/`

The public project label and the technical package names are related labels, not interchangeable identity authorities. The dated [post-transfer observation](docs/audits/repository-transfer-observation-2026-08-24.md) records the current GitHub owner/name observation separately from the stable repository ID.

## Public execution surface

CLI commands:

- `audit-requirement`
- `audit-direction-binding`
- `shadow-compare`
- `schema`

MCP tools:

- `audit_requirement_relations_tool`
- `audit_direction_binding_tool`
- `shadow_compare_legacy_tool`
- `semantic_guard_schema_tool`

The schema tool exposes 24 closed contract schemas. Schema availability does not assert that every sidecar has a public end-to-end workflow.

## Public source contents

- Canonical audit kernel under `src/semantic_guard/`
- Closed schemas under `schemas/`
- Constitution under `constitution/`
- Unit and conformance tests under `tests/`
- Versioned verification source and generated projection under `validation/`
- Package verification and validation scripts under `scripts/`
- Repository companion Skill under `skills/semantic-implementation/`; it is excluded from wheel and sdist and is not installed automatically
- Publication-repaired 0.1.0 archive under `legacy/semantic-guard-v0.1.0/`; its manifest identifies the original Git anchor and disclosed repairs
- Publication, migration, operation, security, support, and contribution documents
- GitHub Actions checks for canonical and legacy compatibility surfaces

## Evidence boundary

The current implementation status is summarized in `docs/implementation-status.md`. Dated records support only their identified subject, source, environment, and observation time. CI success establishes the checks run against its identified commit; it does not establish field validity, external authenticity, or human acceptance.

Package or release evidence must identify the exact commit, artifact digest, commands, environment, and outcomes. This documentation snapshot does not identify a published index artifact or deployed runtime.

## Explicit limits

This public surface does not establish:

- statistical accuracy or value on practical-domain documents;
- public workflow coverage for every development lifecycle phase;
- authenticity of external AI-agent actions or identities;
- human adoption of candidate rule packs or lifecycle profiles;
- security certification or operational qualification;
- equivalence between a selected local artifact and a hosted or index artifact;
- operational default cutover or irreversible predecessor retirement;
- final human acceptance.

The 1.0.0 snapshot is preserved as [dated historical evidence](docs/audits/public-snapshot-v1.0.0-2026-07-17.md). Canonicalization, repository transfer, deployment, policy adoption, and human acceptance remain separate facts.
