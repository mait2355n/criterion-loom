# Contributing

Changes to `semantic-guard` must preserve its audit-only authority boundary and keep claims proportional to evidence.

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

## Pull requests

A pull request should include:

- objective and non-goals;
- affected files and public contracts;
- migration and compatibility effects;
- commands run and exact outcomes;
- checks not run and why;
- residual risks and pending human decisions.

Human review remains the final acceptance gate.
