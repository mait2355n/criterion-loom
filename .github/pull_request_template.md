## Objective

- Purpose and desired state:
- Non-goals:
- Human decision still pending:

## Scope

- [ ] canonical runtime or Python API
- [ ] CLI or MCP public contract
- [ ] schema or durable evidence
- [ ] requirement rules, providers, or conformance corpus
- [ ] packaging or CI
- [ ] documentation or Skill
- [ ] migration or frozen legacy boundary

## Compatibility and claims

- Breaking change:
- Migration route:
- Frozen 0.1.0 effect:
- Claims supported by this change:
- Claims explicitly not supported:

## Verification

```sh
uv lock --check
uv run --locked python -m unittest discover -s tests -v
uv run --locked python scripts/validate_verification_source.py
uv run --locked python scripts/render_verification_projection.py --check
uv run --locked python scripts/validate_engineering_rule_pack.py
uv build
uv run --locked python scripts/verify_packaged_contracts.py \
  --wheel dist/semantic_guard-1.1.0-py3-none-any.whl \
  --sdist dist/semantic_guard-1.1.0.tar.gz
```

- Commands run and outcomes:
- Checks not run and reason:
- Evidence references:

## Boundary check

- [ ] Analyzer and LLM candidates do not acquire support or hold-mutation authority.
- [ ] `pass` is not represented as correctness, release approval, or human acceptance.
- [ ] Dated historical records were not rewritten as current evidence.
- [ ] Canonicalization is not represented as field validity, policy adoption, operational qualification, or default cutover.
- [ ] Final human acceptance remains explicit.

## Residual risks

-
