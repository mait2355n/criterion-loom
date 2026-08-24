# Migration from semantic-guard 0.1.0 to 1.0.0

> This guide describes the 0.1.0-to-1.0.0 contract replacement. The current 1.1.0 line additionally exposes the independent direction-binding command and MCP tool documented in the root README.

## Summary

1.0.0 is a contract replacement, not an in-place extension of the 0.1.0 command set. Migrate callers by selecting the required behaviour explicitly.

## Public surface mapping

| 0.1.0 surface | 1.0.0 status | Migration route |
| --- | --- | --- |
| `audit-request` | Replaced for the structured functional-requirement slice | Use `audit-requirement`; update the consumer to the v1 closed result schema. |
| `audit-plan` | Not migrated | Run the publication-repaired legacy archive explicitly or defer until a v1 slice exists. Do not label the legacy result as v1. |
| `audit-diff` | Not migrated | Same explicit legacy or defer route. |
| `finish-check` | Not migrated | Same explicit legacy or defer route. |
| exploration, decision-state, convention, trace, reviewer and acceptance-bundle commands | Not migrated | Available only in the publication-repaired 0.1.0 archive; no transparent v1 alias exists. |
| old schema commands | Replaced | Use `semantic-guard schema NAME`. |
| old MCP tool set | Replaced | Use only the four documented 1.1.0 MCP tools; the fourth is the independent direction-binding surface. |

The `--output legacy-compat` projection on `audit-requirement` is a lossy output projection for a narrow requirement result. It does not restore the old command set or execute the old engine.

## Canonical v1 invocation

```sh
uv sync --locked
uv run --locked semantic-guard audit-requirement --file requirement.txt
uv run --locked semantic-guard schema audit-result
uv run --locked semantic-guard-mcp
```

Consumers must validate the selected v1 schema, retain provenance and source spans, and handle `undetermined`, `partial`, `failed`, `warn`, and `block` without coercing them to success.

## Publication-repaired repository archive

`legacy/semantic-guard-v0.1.0/` contains predecessor runtime source and publication-repaired historical documentation. Its manifest identifies the original Git anchor, previous public digest, repair scope, and current digest. It is deliberately outside the canonical package. Work from that directory only when a caller knowingly needs the old behaviour.

```sh
cd legacy/semantic-guard-v0.1.0
uv sync --locked
uv run --locked semantic-guard --help
```

The archive is not maintained as a second live product line. Do not import it from v1 code, modify dated records to resemble current evidence, or combine old and new output without an explicit adapter and version marker.

## Controlled shadow comparison

The repository archive is source preservation; it is not automatically a trusted execution root. A shadow run needs an operator-owned external legacy root containing the pinned interpreter, adapter, baseline manifest, and all digest-covered files at the expected relative paths.

CLI callers must select the external root explicitly:

```sh
uv run --locked semantic-guard shadow-compare \
  --file requirement.txt \
  --legacy-root /absolute/operator-owned/legacy-root \
  --require-legacy
```

MCP operators, not tool callers, control this route:

```sh
export SEMANTIC_GUARD_ENABLE_LEGACY_SHADOW=1
export SEMANTIC_GUARD_LEGACY_ROOT=/absolute/operator-owned/legacy-root
uv run --locked semantic-guard-mcp
```

The server requires its fixed relative baseline and adapter paths and the server-pinned baseline digest. A matching digest establishes identity with the captured legacy subject, not correctness. Baseline capture remains pending human acceptance unless a later decision record explicitly adopts it.

## Result interpretation

Classify a difference as one of:

- preserved contract;
- corrected legacy defect;
- intentional contract change;
- v1 regression;
- incomparable evidence;
- not implemented.

Do not average old and new scores or select the old result as an oracle. Preserve both observations, the comparison basis, the version identities, and unresolved adjudication.

## Rollback and coexistence

Exact source rollback is possible by checking out the predecessor tag. The publication-repaired archive supports explicit compatibility inspection and execution but is not the original byte snapshot. Operational rollback requires a separately controlled deployment decision. Canonicalizing the repository does not assert that a deployed environment has switched, nor that every predecessor deployment may be destroyed.
