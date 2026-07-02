## Purpose And Use

Use this template to give maintainers enough context to review scope, changed
public contracts, verification evidence, and claim-boundary risks.

Audience: repository maintainers and reviewers checking a Criterion Loom change.
Fill only the sections that apply, and keep unrelated design discussion in
linked issues or docs.

## Summary

- 

## Scope

- [ ] CLI or MCP behavior
- [ ] audit rules or matching
- [ ] fixtures or field corpus
- [ ] documentation only
- [ ] tests or CI only

## Verification

Representative commands:

```sh
uv run --python 3.13 --project . python -m unittest discover -s tests -v
uv run --python 3.13 --project . semantic-guard evaluate-fixtures
uv run --python 3.13 --project . semantic-guard audit-request --kind document --file README.md
```

- [ ] `uv run --python 3.13 --project . python -m compileall src/semantic_guard tests`
- [ ] `uv run --python 3.13 --project . python -m unittest discover -s tests -v`
- [ ] `uv run --python 3.13 --project . semantic-guard evaluate-fixtures`
- [ ] document audit was run for changed public docs, if applicable

## Boundary Check

- [ ] This does not claim general natural-language accuracy from fixture results.
- [ ] This does not treat LLM review as final human acceptance.
- [ ] Public contract, JSON fields such as `status` / `findings` / `details`, or MCP changes are called out above.
