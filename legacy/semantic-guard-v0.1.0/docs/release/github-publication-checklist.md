# GitHub Publication Checklist

Use this checklist before pushing the public snapshot to GitHub.

## Purpose

This checklist keeps repository publication separate from development work. It verifies that the public tree is runnable, documented, and free of local-only material.

## Audience And Use

Use this file when preparing a GitHub repository, reviewing a publication snapshot, or checking a release candidate before push. It is for maintainers; it is not a general release gate for downstream users.

## Checklist Result

The expected output is a reviewed publication tree plus recorded command results for compile, unit tests, fixture evaluation, and public document audit.

## Repository Shape

- [ ] `README.md` explains status, install, CLI, MCP, output shape, and limits.
- [ ] `README.ja.md` and `docs/ja/` are present for Japanese usage and company-facing evidence.
- [ ] `LICENSE` is present.
- [ ] `CONTRIBUTING.md` is present.
- [ ] `SECURITY.md` is present and does not promise security-scanner coverage.
- [ ] `CHANGELOG.md` is present.
- [ ] `.github/workflows/ci.yml` runs compile, unit tests, fixture evaluation, and `doctor` on Python 3.11 and 3.13.
- [ ] Issue and pull request templates are present.

## Hygiene

- [ ] No local absolute paths such as `/Users/...` or `/Volumes/...`.
- [ ] No `.venv/`, `.backups/`, `__pycache__/`, `*.pyc`, `.DS_Store`, or local generated output.
- [ ] Selected historical design, dogfood, audit, and acceptance records have
  been reviewed for sensitive or machine-specific material and are treated as
  historical evidence rather than current guidance. Private work records remain
  excluded.

## Verification

Run from the repository root:

```sh
uv run --python 3.13 --project . python -m compileall src/semantic_guard tests
uv run --python 3.13 --project . python -m unittest discover -s tests -v
uv run --python 3.13 --project . semantic-guard evaluate-fixtures --include-passed
uv run --python 3.13 --project . semantic-guard doctor
uv run --python 3.13 --project . semantic-guard audit-result-schema
uv run --python 3.13 --project . semantic-guard rule-detector-map
```

Run document audit for the public entry points:

```sh
uv run --python 3.13 --project . semantic-guard audit-request --kind document --file README.md
uv run --python 3.13 --project . semantic-guard audit-request --kind document --file README.ja.md
uv run --python 3.13 --project . semantic-guard audit-request --kind document --file docs/ja/company-evidence.md
```

## Publication Notes

- Do not describe fixture pass rate as general accuracy.
- Do not describe LLM reviewer output as final human acceptance.
- Do not describe this project as a production requirements-engineering engine.
- If repository URLs, badges, or package links are added later, verify that they point to the actual public repository.
