# Canonical promotion decision: semantic-guard 1.0.0

Decision id: `canonical-promotion.semantic-guard.v1.0.0`

Decision date: 2026-07-17

Decision owner: repository owner

## Record surface

- `context`: promote the contract-first audit kernel from a side-by-side candidate into the canonical repository and package identity while preserving the former implementation as a frozen predecessor.
- `current_state`: implementation authority for repository canonicalization was given; release verification and final review still determine whether the resulting commit and artifacts are accepted.
- `action`: canonicalize the v1 source and public names, freeze 0.1.0, regenerate post-promotion evidence, then submit the exact diff and verification results for final human review.
- `detail_refs`: `README.md`, `CHANGELOG.md`, `PUBLIC-SNAPSHOT.md`, `docs/migration-v0.1.0-to-v1.0.0.md`, `docs/audits/canonicalization-audit-v1.0.0-2026-07-17.md`.

## Decision

The repository root, distribution `semantic-guard`, Python package `semantic_guard`, CLI `semantic-guard`, and MCP server `semantic-guard-mcp` are the canonical 1.0.0 implementation identity.

The former 0.1.0 source is retained under `legacy/semantic-guard-v0.1.0/` as a frozen predecessor. Its behaviour is comparison material, not the definition of correctness for v1.

The public v1 execution surface consists of:

- CLI: `audit-requirement`, `shadow-compare`, `schema`;
- MCP: `audit_requirement_relations_tool`, `shadow_compare_legacy_tool`, `semantic_guard_schema_tool`.

## Preserved purpose

The product continues to aim at auditing plans, actions, realization methods, and evidence across development work by using explicit requirements-engineering, planning-engineering, and software-systems-engineering knowledge. It also aims to make bounded claims about AI-agent actions inspectable where suitable observation and provenance exist.

Canonical promotion does not narrow that purpose. It narrows only what 1.0.0 may claim as presently executable: one requirement-relation vertical slice, schema access, and controlled legacy observation.

## Separate decisions not made here

This decision does not:

- adopt the candidate engineering rule pack or lifecycle profiles;
- establish field validity or operational qualification;
- attest external action or actor authenticity;
- authorize arbitrary external execution;
- mark every development lifecycle phase as integrated;
- switch a deployed operator environment to the new default;
- irreversibly retire every predecessor deployment;
- fill final human acceptance on behalf of the owner.

Repository canonicalization, policy adoption, operational transition, and final artifact acceptance remain separate decisions.

## Completion conditions

Promotion is technically closed only when:

1. public names and examples agree with the v1 contract;
2. the frozen predecessor is identifiable and excluded from canonical packaging;
3. verification-source, generated projection, rule-pack, unit, packaging, installed CLI/MCP, and legacy smoke checks pass against the promoted tree;
4. post-promotion evidence identifies the exact commit and wheel digest;
5. a human reviews the final diff, evidence, and residual risks.
