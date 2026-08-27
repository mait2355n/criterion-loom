# Contributing

Changes to `semantic-guard` must preserve its audit-only authority boundary and keep claims proportional to evidence.

Start a bug report, documentation correction, or rule-gap proposal with the
[issue chooser](https://github.com/mait2355n/criterion-loom/issues/new/choose).
Use [SUPPORT.md](SUPPORT.md) for usage questions and [SECURITY.md](SECURITY.md)
for vulnerabilities or sensitive reports. Code changes should follow the
[pull request template](.github/pull_request_template.md).

## Before changing code or contracts

State:

- the requirement, affected public surface, and intended value;
- what remains unchanged and what is explicitly out of scope;
- schema, CLI, MCP, migration, archive, and evidence impact;
- verification commands and the evidence that would justify completion;
- unresolved human decisions.

Do not treat a detector warning, parser candidate, LLM output, test pass, or prior-version result as release approval.

## Canonical and legacy boundaries

- Canonical v1 code lives at the repository root.
- `legacy/semantic-guard-v0.1.0/` is a publication-repaired predecessor archive, not a second implementation tree for ordinary development. Its manifest identifies the historical Git anchor and repair boundary.
- Fixes intended for v1 belong in the canonical root.
- A necessary legacy publication, compatibility, or security correction requires a separate, explicit decision and must update the archive manifest. Do not silently rewrite historical records.
- Dated validation records are append-only historical observations. Add a new record instead of modifying an old one.

## Required checks

Run the smallest relevant set while iterating, then the full release set before proposing a public-contract or release change:

```sh
uv lock --check
uv run --locked python -m unittest discover -s tests -v
uv run --locked python scripts/validate_verification_source.py
uv run --locked python scripts/render_verification_projection.py --check
uv run --locked python scripts/validate_engineering_rule_pack.py
uv build
uv run --locked python scripts/verify_packaged_contracts.py \
  --wheel dist/semantic_guard-*.whl \
  --sdist dist/semantic_guard-1.1.0.tar.gz
```

For documentation changes, verify paths, examples, command names, contract versions, claim/evidence/limitation triples, and the distinction between canonicalization and adoption.

## Documentation changes

`README.md` is the English public entry point and `README.ja.md` is its Japanese
counterpart. `docs/README.md` and `docs/README.ja.md` provide the matching
task-oriented documentation maps. When a change affects value, current scope,
commands, result semantics, evidence, or non-claims, update both languages in
the same change or state the deliberate divergence in the pull request.

Detailed reference and dated evidence may remain in their source language. Do
not rewrite a historical observation merely to make the language surfaces
symmetrical. Keep links from both documentation maps accurate, and classify
each document as current reference, operating guidance, candidate design,
dated evidence, migration, or archive material.

Keep overview examples concrete enough to run, but explain their significance
as stable project behavior. Put exhaustive field paths, paired negative
controls, and dated execution detail in the relevant reference, test, or
evidence record, then link to them from the overview. Do not strip away the
proof, and do not let one fixture stand in for the project's purpose.

In Japanese documentation, use ordinary Japanese for explanatory prose. Keep
commands, schema names, field names, enum values, paths, versions, and other
machine contracts exact and set them in code spans. Explain a specialized
concept in Japanese at first use; do not replace it with an unexplained literal
translation. Japanese and English documents must preserve the same claim
boundaries, but they need not mirror each sentence word for word.

## Pull requests

A pull request should include:

- objective and non-goals;
- affected files and public contracts;
- migration and compatibility effects;
- commands run and exact outcomes;
- checks not run and why;
- residual risks and pending human decisions.

Human review remains the final acceptance gate.
