# Base Contract

Status: draft

This contract defines the baseline shape for coding conventions and I/O
contracts across the workspaces that `semantic-guard` audits.

The purpose is not uniformity for its own sake. The purpose is to make public
behavior inspectable: what succeeded, what failed, what evidence exists, which
facts are inferred, and where a human decision remains pending.

## Structure First

Prefer structure over prose wherever later tools, skills, tests, or humans must
act on the result.

Use prose for explanation, rationale, and human notes. Do not make prose carry
control semantics that a caller must parse. Public contracts should expose named
fields, stable versions, typed values, and explicit exception points.

Structure-first conventions:

- machine-readable public outputs declare a `schema_version`, `$schema`,
  documented version, or established equivalent.
- public records use named fields for facts, inferences, pending decisions,
  evidence, and residual risks.
- free-form text lives in `notes`, `message`, `summary`, `rationale`, or another
  clearly named human field.
- booleans, enums, identifiers, timestamps, status values, and error codes are
  fields, not sentences.
- repository profiles follow fixed sections so differences between repositories
  are visible without re-reading prose.

## Applies To

Use this contract for public or cross-tool surfaces:

- CLI commands.
- MCP tools.
- API or webhook responses.
- JSON, YAML, JSONL, or CSV outputs.
- audit records and completion evidence.
- durable project notes that will be read by later agents.
- repository-level convention profiles.

Do not use it to force one internal architecture onto every repository. Internal
module layout, domain model, persistence engine, visualizer structure, and
creative-document structure remain repository-specific.

Non-goals and exceptions must be written down rather than guessed. A repository
profile may override the base contract for a named surface, but it should state
the exception, the reason, and the verification command that proves the local
shape still composes with the surrounding tools.

## Output Envelope

Machine-readable results should expose the outcome before the payload.

Success shape:

```json
{
  "schema_version": "tool-result/v1",
  "ok": true,
  "data": {},
  "meta": {}
}
```

Failure shape:

```json
{
  "schema_version": "tool-result/v1",
  "ok": false,
  "error": {
    "code": "stable_error_code",
    "message": "short human-readable message",
    "detail": {},
    "hint": ""
  },
  "meta": {}
}
```

For existing `semantic-guard` audit results, the established `status`,
`findings`, `missing`, `next_actions`, and `details` shape remains valid. Do not
break it just to wrap it. New public outputs should still state success or
failure plainly, keep error shape stable, and declare their structural version
or documented schema source.

## CLI Contract

CLI commands should keep these roles separate:

- `stdout`: machine-readable result when the command is meant to be composed.
- `stderr`: human diagnostics, progress, and non-result messages.
- exit `0`: successful command.
- exit `1`: expected domain failure or invalid audited artifact.
- exit `2`: usage, argument, configuration, or input-shape error.
- exit `3`: external dependency, environment, or subprocess failure.

Commands may return a non-zero exit code for a valid audit result when the
audited material fails the gate. That is distinct from the command itself being
broken.

## Error Contract

Public failures should include:

- stable `code`.
- short `message`.
- structured `detail` when available.
- `hint` when the next action is known.

Do not make callers parse prose to understand a failure class.

## Record Contract

Durable records should make time, source, and uncertainty explicit:

- timestamps use ISO 8601 with timezone.
- identifiers are stable across reruns when they represent the same entity.
- facts, inferences, pending decisions, and unresolved observations are marked
  separately.
- evidence is linked or described concretely enough to rerun or inspect.

Durable records should also keep their recovery surface shallow. A later reader
or tool should not need to traverse deep prose before it can resume work.

Expose a short `record_surface` or equivalent named fields:

- `context`: what this record is about and why it exists.
- `current_state`: the state now, not the full history.
- `action`: the next action, stop condition, or explicit no-action state.
- `detail_refs`: links or identifiers for deeper evidence, rationale, logs, or
  prior discussion.

Keep long rationale, raw logs, transcripts, and historical explanation behind
`detail_refs`. The top-level record should recover context and action; it should
not become the archive itself.

## Repository Profile

Each repository may have a profile that specializes this base contract.

The profile should use fixed sections:

- `schema_version`: profile schema version.
- `repository`: stable repository or workspace identifier.
- `public_surfaces`: CLI, MCP, API, files, records, or UI surfaces.
- `commands`: formatter, linter, test, fixture, smoke, and release checks.
- `output_shapes`: accepted structured outputs and schema references.
- `records`: durable logs, audit records, diary records, or evidence records.
- `exceptions`: local exceptions with reason and verification command.
- `non_goals`: repository-specific things the base contract must not force.

The base contract wins only where a repository profile is absent or silent.

## Verification

Representative checks for this convention layer:

```sh
uv run --python 3.13 --project . semantic-guard conventions-catalog
uv run --python 3.13 --project . semantic-guard audit-conventions --file docs/conventions/base-contract.md
uv run --python 3.13 --project . python -m unittest tests.test_conventions tests.test_cli tests.test_mcp_tools
```

Use these tests and example outputs when changing the convention catalog, CLI
surface, MCP surface, or output schema.

## Confirmation Points

These points require user confirmation before promotion from `draft`:

- whether every new machine-readable output must use an explicit `ok` envelope,
  or whether established audit-result shapes remain first-class without
  wrapping.
- whether exit code `1` should always mean audited-material failure, or whether
  some tools may use it for generic command failure.
- whether top-level `schema_version` is required on all new structured outputs,
  or whether documented schema source plus `details.schema_version` is enough
  for some support outputs.
- which convention violations should become blockers in release profile.
