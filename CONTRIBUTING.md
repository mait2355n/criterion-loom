# Contributing

Criterion Loom's `semantic-guard` package is a small research prototype for meaning-first audits of Codex work. Contributions should preserve the public boundary: this is not a general natural-language understanding engine, a security scanner, or a replacement for human acceptance.

## Purpose

This guide defines how to propose changes without weakening the repository's audit boundaries, fixture discipline, or public non-claims.

## Audience And Use

Use this file if you want to change code, rules, fixtures, field-corpus entries, schemas, CI, or public documentation. It is written for maintainers and contributors who need a concise verification contract before opening a pull request.

## Useful Contributions

- tighter deterministic checks with focused fixtures.
- false-positive and false-negative examples for the field corpus.
- clearer public documentation and runnable examples.
- safer CLI or MCP contracts.
- tests that preserve existing non-claims and human-decision boundaries.

## Local Verification

Run these from the repository root before proposing a change:

```sh
uv run --python 3.13 --project . python -m compileall src/semantic_guard tests
uv run --python 3.13 --project . python -m unittest discover -s tests -v
uv run --python 3.13 --project . semantic-guard evaluate-fixtures --include-passed
uv run --python 3.13 --project . semantic-guard doctor
```

If public documentation changes, also run document audit on the changed files:

```sh
uv run --python 3.13 --project . semantic-guard audit-request --kind document --file README.md
uv run --python 3.13 --project . semantic-guard audit-request --kind document --file README.ja.md
```

## Pull Request Contract

A pull request should state the changed surface, the reason for the change, the verification commands that were run, and any public contract impact. If CLI output, MCP tools, schemas, or rule ids changed, call that out explicitly in the pull request summary.

If a rule is added or moved, update `rule-detector-map` coverage and add or adjust fixtures before treating the rule as part of the public catalog.

## Fixture And Corpus Policy

Use deterministic fixtures under `tests/fixtures/` for behavior that should become a stable regression check.

Use the field corpus under `tests/field-corpus/` for examples that are plausible but still need review. Do not promote a corpus entry into a detector only because it is easy to keyword-match.

## Human Decision Boundary

LLM review output is supplemental review material. It must not become final acceptance. Keep `final_human_decision.status` pending until a person decides.
