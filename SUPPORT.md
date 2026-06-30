# Support

## Purpose

This file explains where to ask for help and what information makes an issue
actionable.

## Audience And Use

Use this file before opening an issue or asking for help with the CLI, MCP
server, schemas, fixtures, documentation, or companion Codex skill.

## Where To Ask

- Bugs: use the bug report issue template.
- Documentation problems: use the documentation issue template.
- Fixture, false-positive, or false-negative examples: use the fixture/rule gap
  issue template.
- Sensitive reports: use `SECURITY.md`, not a public issue with secrets.

## What To Include

Include the smallest redacted example that shows the problem:

```text
Command:
uv run --python 3.13 --project . semantic-guard audit-request --file request.md

Expected:
...

Actual:
...

Verification:
...
```

For rule or fixture issues, include whether the example is a good warning, a
noisy warning, a missed warning, or documentation confusion.

## Issue Contract

Useful support requests name these fields:

- `summary`: what is wrong or unclear.
- `surface`: CLI, MCP, schema, fixture, documentation, or skill.
- `command`: the smallest redacted command or input.
- `expected`: the status, finding, missing field, or output you expected.
- `actual`: the status, finding, missing field, traceback, or behavior observed.
- `verification`: tests, fixture evaluation, doctor output, or reason not run.

## Scope Limits

This project does not provide broad requirements-engineering consulting,
security certification, legal review, or guaranteed natural-language accuracy.
Support is limited to this repository, its CLI, MCP server, schemas, fixtures,
documentation, and companion Codex skill.
