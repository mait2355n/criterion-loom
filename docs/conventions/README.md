# Conventions

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
- shallow recovery surfaces for durable records.
- repository-specific profile declarations.
- document wording that must carry recoverable target, operation, output,
  decision, revision, or referent semantics.

They do not define each repository's internal module layout, domain model,
storage engine, visual design, or creative record structure.

Free-form prose is allowed for explanation and rationale. It should not be the
only place where a caller must find status, type, identity, evidence,
uncertainty, or next-action semantics.

Expression-precision checks use `doc.expression.*` rule ids inside
`audit-conventions --kind document`. They are not copy-editing rules. They warn
when wording such as "怪しい場所を試験できる内容として外に出す" leaves the
target, operation, output form, or decision actor unclear.

They also warn when demonstratives such as "それを外部へ出す" do not expose a
nearby referent. "未決定事項を抽出し、その一覧を JSON の findings として返す"
is acceptable for expression precision because the referent is recoverable in
the same sentence.

For durable records, keep a short top-level recovery surface: context, current
state, next action, and detail references. Put raw history and long rationale
behind references so record readers can resume work without walking a deep
archive first.
