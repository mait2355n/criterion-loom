# Criterion Loom Naming

## Purpose

This document defines the public names for the Criterion Loom project and maps them to the existing technical package, CLI commands, MCP server, and Codex skill.

## Audience And Use

Use this document when writing README copy, repository descriptions, release notes, or contribution material. It prevents the public project name from being confused with the technical package name.

## Name Map

| Public Name | Meaning | Technical Surface |
| --- | --- | --- |
| **Criterion Loom** | whole public project and audit system | repository: `criterion-loom`; package remains `semantic-guard` |
| **Loom Guide** | Codex skill that guides work through the audit sequence | `skills/semantic-implementation/` |
| **Need Thread** | requirements audit for need, stakeholder, scope, verification, quality, priority, and uncertainty | `semantic-guard audit-request` |
| **Plan Warp** | planning audit for work breakdown, sequence, risk, validation, progress, rollback, and evidence | `semantic-guard audit-plan` |
| **Change Weft** | implementation audit for changed meaning, public contract, failure handling, tests, docs, operations, and finish evidence | `semantic-guard audit-diff` and `semantic-guard finish-check` |

## Technical Names That Stay

The Python package, CLI command, and MCP server keep the `semantic-guard` name for compatibility:

```sh
uv run --python 3.13 --project . semantic-guard --help
uv run --python 3.13 --project . semantic-guard-mcp
```

The skill directory keeps the `semantic-implementation` name because Codex skill loading uses that technical identifier.

## Contract And Scope

This is a naming contract, not a change to the CLI JSON shape.

Criterion Loom commands still return the `semantic-guard` audit fields such as
`phase`, `status`, `score`, `findings`, `missing`, `next_actions`, and
`details`. The name map only tells readers which public name to use when
describing each command family.

The technical evidence for these names is the repository layout: `pyproject.toml`
for package and command names, `README.md` for public overview, and
`skills/semantic-implementation/` for the Codex skill.

## Supporting Surfaces

These commands support the public four-part shape but are not separate public pillars:

- `understand-target`: target-understanding precheck.
- `trace-report`: cross-segment traceability report.
- `llm-review-*` and `review-if-needed`: intermediate reviewer material.
- `acceptance-bundle-*`: human final-review bundle support.
- `evaluate-fixtures`: local calibration evaluation.

## Naming Rule

Use **Criterion Loom** when talking about the public project. Use `semantic-guard` only when referring to package installation, CLI commands, MCP configuration, schemas, or code paths.

Do not present the names as separate products. Loom Guide, Need Thread, Plan Warp, and Change Weft are parts of Criterion Loom.
