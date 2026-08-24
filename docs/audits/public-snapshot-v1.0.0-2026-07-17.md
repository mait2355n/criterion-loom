# Historical public snapshot: semantic-guard 1.0.0

> Historical evidence recorded on 2026-07-17. This file does not describe the current 1.1.0 execution surface. Current commands, schemas, and limits are listed in [`../../PUBLIC-SNAPSHOT.md`](../../PUBLIC-SNAPSHOT.md).

Snapshot date: 2026-07-17

## Identity

- Distribution: `semantic-guard`
- Version: `1.0.0`
- CLI: `semantic-guard`
- MCP server: `semantic-guard-mcp`
- Python package: `semantic_guard`
- Canonical source at the recorded time: repository root
- Predecessor source at the recorded time: `legacy/semantic-guard-v0.1.0/`

## Public execution surface at the recorded time

CLI commands:

- `audit-requirement`
- `shadow-compare`
- `schema`

MCP tools:

- `audit_requirement_relations_tool`
- `shadow_compare_legacy_tool`
- `semantic_guard_schema_tool`

The schema tool exposed 23 closed contract schemas. Schema availability did not assert that every sidecar had a public end-to-end workflow.

## Snapshot contents

- Canonical audit kernel under `src/semantic_guard/`
- Closed schemas under `schemas/`
- Constitution under `constitution/`
- Unit and conformance tests under `tests/`
- Versioned verification source and generated projection under `validation/`
- Package verification and validation scripts under `scripts/`
- Repository companion Codex Skill under `skills/semantic-implementation/`; it was excluded from wheel and sdist and was not installed automatically
- The then-frozen 0.1.0 source under `legacy/semantic-guard-v0.1.0/`
- Publication, migration, operation, security, support, and contribution documents
- GitHub Actions checks for canonical and predecessor surfaces

## Evidence status

The repository contained dated historical records created before canonical promotion. They were useful observations but did not, by themselves, bind the 1.0.0 source or wheel.

Release evidence had to identify the exact commit, wheel digest, commands, environment, and outcomes generated after canonicalization. CI success established local contract and packaging checks only.

## Explicit limits

This snapshot did not establish:

- statistical accuracy or value on practical-domain documents;
- public workflow coverage for every development lifecycle phase;
- authenticity of external AI-agent actions or identities;
- human adoption of candidate rule packs or lifecycle profiles;
- security certification or operational qualification;
- operational default cutover or irreversible predecessor retirement;
- final human acceptance.

The corresponding canonical-promotion decision is recorded in `../canonical-promotion-decision.md`. Verification findings and remaining closure conditions are recorded in `canonicalization-audit-v1.0.0-2026-07-17.md`.
