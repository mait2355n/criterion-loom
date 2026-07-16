# Public Snapshot: semantic-guard 1.0.0

Snapshot date: 2026-07-17

## Identity

- Distribution: `semantic-guard`
- Version: `1.0.0`
- CLI: `semantic-guard`
- MCP server: `semantic-guard-mcp`
- Python package: `semantic_guard`
- Canonical source: repository root
- Frozen predecessor source: `legacy/semantic-guard-v0.1.0/`

## Public execution surface

CLI commands:

- `audit-requirement`
- `shadow-compare`
- `schema`

MCP tools:

- `audit_requirement_relations_tool`
- `shadow_compare_legacy_tool`
- `semantic_guard_schema_tool`

The schema tool exposes 23 closed contract schemas. Schema availability does not assert that every sidecar has a public end-to-end workflow.

## Snapshot contents

- Canonical audit kernel under `src/semantic_guard/`
- Closed schemas under `schemas/`
- Constitution under `constitution/`
- Unit and conformance tests under `tests/`
- Versioned verification source and generated projection under `validation/`
- Package verification and validation scripts under `scripts/`
- Repository companion Codex skill under `skills/semantic-implementation/`; it is excluded from wheel and sdist and is not installed automatically
- Frozen 0.1.0 source under `legacy/semantic-guard-v0.1.0/`
- Publication, migration, operation, security, support, and contribution documents
- GitHub Actions checks for the canonical and frozen legacy surfaces

## Evidence status

The repository contains dated historical records created before canonical promotion. They remain useful observations but do not, by themselves, bind the 1.0.0 source or wheel.

Release evidence must identify the exact commit, wheel digest, commands, environment, and outcomes generated after canonicalization. CI success establishes local contract and packaging checks only.

## Explicit limits

This snapshot does not establish:

- statistical accuracy or value on practical-domain documents;
- public workflow coverage for every development lifecycle phase;
- authenticity of external AI-agent actions or identities;
- human adoption of candidate rule packs or lifecycle profiles;
- security certification or operational qualification;
- operational default cutover or irreversible predecessor retirement;
- final human acceptance.

The canonical-promotion decision is recorded in `docs/canonical-promotion-decision.md`. Verification findings and remaining closure conditions are recorded in `docs/audits/canonicalization-audit-v1.0.0-2026-07-17.md`.
