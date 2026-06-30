# Public Repository Readiness

## Purpose

This document records the publication shape used for this candidate and the
public examples behind it. It is a maintainer checklist, not a release record.

## Audience And Use

Use this document when preparing the first public GitHub push, reviewing whether
the repository has a coherent public surface, or deciding whether a private work
record should be promoted into maintained documentation.

This file should be read with `PUBLIC-SNAPSHOT.md` and
`docs/release/github-publication-checklist.md`.

## Reference Pattern

The candidate follows the same broad shape used by healthy public tooling
repositories:

- short README entry point before deep reference material;
- explicit install and quickstart commands;
- clear non-goals and status language;
- `LICENSE`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, and
  `SUPPORT.md`;
- issue and pull request templates;
- CI template and dependency update configuration;
- detailed docs under `docs/` rather than a README that tries to carry every
  decision.

Useful comparison points:

- GitHub Community Profile guidance for public repository health files:
  <https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/about-community-profiles-for-public-repositories>
- GitHub README guidance for project orientation:
  <https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes>
- Ruff: <https://github.com/astral-sh/ruff>
- Black: <https://github.com/psf/black>

The Python tooling examples keep the README as an entry point: positioning and
quick usage first, deeper behavior in documentation.

## Applied Shape

| Surface | Local File |
| --- | --- |
| Main entry | `README.md` |
| Japanese entry | `README.ja.md` |
| Documentation map | `docs/README.md` |
| Public scope and non-claims | `docs/public-comparison-2026-06-02.md` |
| Contribution contract | `CONTRIBUTING.md` |
| Conduct expectations | `CODE_OF_CONDUCT.md` |
| Support routing | `SUPPORT.md` |
| Sensitive reports | `SECURITY.md` |
| Change history | `CHANGELOG.md` |
| Publication contract | `PUBLIC-SNAPSHOT.md` |
| CI template | `docs/release/ci-workflow-template.yml` |
| Dependency update hints | `.github/dependabot.yml` |
| Issue templates | `.github/ISSUE_TEMPLATE/` |
| Pull request template | `.github/pull_request_template.md` |

## Final Pre-Push Review

- Replace placeholder repository URLs only after the real GitHub repository
  exists.
- Do not add badges until the actual target URLs are known.
- Restore `docs/release/ci-workflow-template.yml` as `.github/workflows/ci.yml`
  after the publishing credential has GitHub `workflow` scope.
- Confirm `uv.lock` matches `pyproject.toml`.
- Confirm no local paths, cache directories, private notes, generated wheels, or
  source distributions are present in the source repository.
- Keep `dist/` artifacts for release workflows or GitHub Releases, not the
  source tree.

Run these checks in the final publish environment:

```sh
uv run --python 3.13 --project . python -m compileall src/semantic_guard tests
uv run --python 3.13 --project . python -m unittest discover -s tests -v
uv run --python 3.13 --project . semantic-guard evaluate-fixtures --include-passed
uv run --python 3.13 --project . semantic-guard doctor
uv run --python 3.13 --project . semantic-guard audit-request --kind document --file README.md
uv run --python 3.13 --project . semantic-guard audit-request --kind document --file README.ja.md
```

## Claim Boundary

The public repository may claim a working v0.1 tool, CLI, MCP server, schemas,
fixtures, docs, and companion Codex skill. It should not claim broad
natural-language accuracy, formal requirements verification, security scanning,
legal review, release approval, or replacement of final human judgment.
