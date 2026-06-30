## Summary

- 

## Scope

- [ ] CLI or MCP behavior
- [ ] audit rules or matching
- [ ] fixtures or field corpus
- [ ] documentation only
- [ ] tests or CI only

## Verification

- [ ] `uv run --python 3.13 --project . python -m compileall src/semantic_guard tests`
- [ ] `uv run --python 3.13 --project . python -m unittest discover -s tests -v`
- [ ] `uv run --python 3.13 --project . semantic-guard evaluate-fixtures`
- [ ] document audit was run for changed public docs, if applicable

## Boundary Check

- [ ] This does not claim general natural-language accuracy from fixture results.
- [ ] This does not treat LLM review as final human acceptance.
- [ ] Public contract, output shape, or MCP changes are called out above.
