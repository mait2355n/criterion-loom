# Conventions

> **Historical boundary (0.1.0 publication-repaired archive).** This document
> describes the predecessor as recorded for the 0.1.0 line; it is not current 1.x
> state or operating guidance. Original-byte authority: tag `v0.1.0`, commit
> `e0a3dd39f17385b66f6361ade25eb44bed6e1ab3`.

This directory is the source of truth for cross-repository coding and I/O
conventions used by `semantic-guard`.

The conventions here are structure-first, but they are not meant to flatten each
project into one internal architecture. They define the public contract shape
that lets Codex, CLI tools, MCP tools, skills, fixtures, and human review
material interoperate without guessing.

## Files

- `base-contract.md`: human-readable baseline contract.
- `base-contract.json`: machine-readable baseline used by `audit-conventions`.

## Status

The first contract is `draft`. Deterministic checks should warn by default until
the remaining preference decisions are confirmed and promoted.

## Use

From the repository root:

```sh
uv run --python 3.13 --project . semantic-guard audit-conventions --file plan.md
uv run --python 3.13 --project . semantic-guard conventions-catalog
```

MCP callers can use:

- `audit_conventions_tool`
- `conventions_catalog_tool`

## Boundary

These conventions govern shared surfaces:

- machine-readable output.
- error payloads.
- CLI streams and exit codes.
- durable logs, audit records, and evidence.
- uncertainty marking.
- repository-specific profile declarations.

They do not define each repository's internal module layout, domain model,
storage engine, visual design, or creative record structure.

Free-form prose is allowed for explanation and rationale. It should not be the
only place where a caller must find status, type, identity, evidence,
uncertainty, or next-action semantics.
