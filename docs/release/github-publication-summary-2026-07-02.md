# GitHub Publication Summary 2026-07-02

## Purpose

This note summarizes the current files and verification evidence that can be
prepared for a GitHub publication snapshot after the expression-precision audit
slice.

It is a publication handoff, not a release approval. Human final publication
decision remains pending.

## Audience And Use

Audience: maintainers preparing the cleaned GitHub source snapshot, and future
Codex sessions resuming publication work.

Use this file before copying or pushing a public tree. It tells the maintainer
which current files matter, which local artifacts must stay out, what evidence
has already been gathered, and what claims must remain out of the public
wording.

## Contract References

This file does not define new public contracts. Contract sources remain:

- audit-result schema source: `schemas/audit-result.schema.json`, with
  `schema_version`, fields, properties, string or enum types, status values,
  findings, and details documented in the README and schema documents;
- error shape source: `schemas/audit-result.schema.json`, with error code,
  message, details, and `next_actions` or remediation material documented by
  the schema and CLI behavior;
- CLI stream policy: command stdout carries machine-readable JSON output where
  applicable, stderr is for human diagnostics, and exit code roles are defined
  in `docs/conventions/base-contract.md`;
- repository profile boundary: `README.ja.md` documents `schema_version:
  "criterion-loom-repository-profile/v1"`, repository id, public surface,
  commands, test evidence, output shapes, exception handling, internal domain
  material, and non-goal boundaries; this summary does not replace that
  profile;
- durable evidence: timestamps use ISO 8601 with timezone, and evidence should
  separate fact, inference, and pending human decision status;
- representative verification: unit tests, fixture evaluation, schema command,
  rule-detector-map command, and doctor command provide the current public
  output-contract checks.

## Publication Stance

Use the same stance as the existing repository update handoff:

- Criterion Loom is ready as a publishable public v0.1.
- The implementation name, package name, CLI name, and MCP server name remain
  `semantic-guard`.
- The project is a small deterministic heuristic tool, not a finished
  requirements-engineering product.
- The tool returns audit material for agent revision and human review. It does
  not approve, reject, or replace human judgment.
- Fixture results and corpus sweeps are local regression and calibration
  evidence. They are not general natural-language accuracy guarantees.

## Current Completion Scope

The current local state includes the expression-precision slice as usable
repository functionality:

- `audit-conventions --kind document` can emit `doc.expression.*` findings.
- The public convention catalog includes document-expression rules for vague
  targets, operations, output forms, utility claims, decision actors, revision
  targets, and unclear demonstrative references.
- Demonstrative references such as bare `それ` or `これ` are checked with a
  standard-library local-context heuristic.
- `details.expression_precision.referent_resolutions` reports whether nearby
  referents were `supported`, `ambiguous`, `no_candidate`, or `weak_only`.
- Morphological analysis, external NLP packages, and LLM review are not
  required for the default path.
- Corpus sweep data has been collected to guide threshold design and fixture
  expansion.

## Files To Carry Forward

Core publication files:

- `README.md`
- `README.ja.md`
- `CHANGELOG.md`
- `CONTRIBUTING.md`
- `CODE_OF_CONDUCT.md`
- `LICENSE`
- `PUBLIC-SNAPSHOT.md`
- `SECURITY.md`
- `SUPPORT.md`
- `docs/release/ci-workflow-template.yml`
- `pyproject.toml`
- `uv.lock`
- `src/`
- `schemas/`
- `tests/`
- `skills/semantic-implementation/`

Expression-precision files:

- `docs/conventions/README.md`
- `docs/conventions/base-contract.md`
- `docs/conventions/base-contract.json`
- `docs/public-wording-audit-feature-brief.md`
- `docs/release/public-writing-guidelines.md`
- `docs/release/expression-precision-reference-heuristic-2026-07-01.md`
- `docs/release/expression-precision-corpus-sweep-2026-07-02.md`
- `docs/release/github-publication-summary-2026-07-02.md`

Optional local evidence:

- `docs/release/expression-precision-corpus-sweep-2026-07-02.raw.json`

The raw corpus JSON is useful for local calibration. For a public snapshot,
include it only if the repository maintainer accepts dated corpus evidence with
historical backup-path labels. Otherwise keep the summary Markdown and exclude
the raw JSON.

## Do Not Carry Forward

Do not publish the development checkout as-is.

Exclude local or generated material:

- `.venv/`
- `.pytest_cache/`
- `.backups/`
- `__pycache__/`
- `*.pyc`
- `.DS_Store`
- local build outputs
- local acceptance-bundle drafts
- private or machine-specific work records

## Current Publication Gaps

The current local tree is suitable as a source for a cleaned publication
snapshot, but it is not itself the final GitHub push tree.

Open publication gaps:

- Existing dated handoff documents, dogfood records, conflict-audit notes, and
  implementation plans are still present as secondary working records. Decide
  whether to archive, exclude, or rewrite them before the final GitHub push.
- The corpus raw JSON should be treated as optional evidence, not mandatory
  public documentation.
- Re-run the full `uv` verification commands in the final publish environment
  after deciding how to handle secondary working records and the raw corpus JSON.

## Verification Evidence

Latest local verification: `2026-07-02T08:18:53+09:00`.

Commands run from the repository root:

```sh
uv run --python 3.13 --project . python -m compileall src/semantic_guard tests
uv run --python 3.13 --project . python -m unittest discover -s tests -v
uv run --python 3.13 --project . semantic-guard evaluate-fixtures
uv run --python 3.13 --project . semantic-guard doctor
uv run --python 3.13 --project . semantic-guard audit-result-schema
uv run --python 3.13 --project . semantic-guard rule-detector-map
uv run --python 3.13 --project . python -m json.tool docs/release/expression-precision-corpus-sweep-2026-07-02.raw.json
```

Observed results:

- compileall completed.
- unit tests: 217 tests passed.
- fixture evaluation: 45/45 passed.
- doctor: 9 checks passed, 0 warnings, 0 blockers.
- audit-result schema command completed.
- rule-detector-map command completed.
- corpus sweep raw JSON parsed successfully.

Post-cleanup local checks after the public wording updates:

- Python AST parse over `src/` and `tests`: 44 files parsed.
- JSON parse completed for the convention catalog, audit-result schema,
  request-exploration-review schema, and raw expression-precision corpus JSON.
- `semantic-guard evaluate-fixtures`: 45/45 passed.
- `audit-request --kind document` passed for `README.md`, `README.ja.md`, and
  `docs/README.md`.
- `audit-conventions --kind document` passed for `README.md`, `README.ja.md`,
  and `docs/public-wording-audit-feature-brief.md`.
- `doctor --no-fixtures` could not pass in this local environment because
  `mcp.server.fastmcp` was not installed. Treat the earlier full verification as
  implementation evidence and rerun final verification in the dependency-backed
  publish environment.

## Suggested GitHub Summary

Suggested title:

```text
Publish Criterion Loom v0.1 with expression precision audit
```

Suggested body:

```text
This snapshot publishes Criterion Loom / semantic-guard as a usable public v0.1
tool and adds document expression-precision auditing.

Highlights:
- Adds doc.expression.* convention findings for vague document wording.
- Adds deterministic demonstrative-reference diagnostics under
  details.expression_precision.referent_resolutions.
- Keeps the default implementation free of required morphological-analysis,
  external NLP, or LLM dependencies.
- Records corpus-sweep evidence for threshold design and future fixture work.
- Preserves the non-approval boundary: audit output informs agent revision and
  human review, but does not decide final acceptance.

Verification:
- compileall completed.
- 217 unit tests passed.
- 45/45 fixtures passed.
- doctor passed 9 checks.

Limits:
- This is not a general natural-language understanding proof.
- Fixture and corpus results are local calibration evidence only.
- This is not a security scanner, legal gate, release gate, or replacement for
  human judgment.
```

## Recommended Next Action

Decide how to handle the remaining secondary working records, decide whether to
keep the raw corpus JSON in the public repository, then rerun the verification
commands inside the cleaned snapshot before pushing to GitHub.
