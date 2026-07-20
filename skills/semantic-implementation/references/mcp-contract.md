# semantic-guard v1 MCP and CLI contract

## Scope

This reference describes the canonical `semantic-guard 1.0.0` execution surface used by the companion Skill. Machine-readable field and enum definitions remain authoritative in `schemas/`.

Public CLI commands:

- `audit-requirement`
- `shadow-compare`
- `schema`

Public MCP tools:

- `audit_requirement_relations_tool`
- `shadow_compare_legacy_tool`
- `semantic_guard_schema_tool`

No former 0.1.0 command or MCP tool is an implicit alias.

## Requirement audit

CLI:

```sh
semantic-guard audit-requirement --text "..."
semantic-guard audit-requirement --file requirement.txt
```

MCP: `audit_requirement_relations_tool`

Inputs:

- one of text, UTF-8 file, or standard input for CLI;
- `analysis_mode`: `assurance`, `conditional`, or `shadow_all`;
- `morphology`: `none` or `sudachi`;
- `dependency`: `none` or `ginza`;
- optional closed LLM candidate bundle;
- output projection: `public`, `assurance-v1`, `legacy-compat`, or CLI-only `internal-debug`;
- optional RFC 3339 `recorded_at` on CLI public or assurance records.

The public result must validate against the selected closed schema. `legacy-compat` is lossy projection, not execution of the predecessor.

Analyzer authority ceilings are invariant: morphology is signal-only; dependency and LLM are candidate-only.

## Shadow comparison

CLI:

```sh
semantic-guard shadow-compare \
  --file requirement.txt \
  --legacy-root /absolute/operator-owned/legacy-root \
  --require-legacy
```

MCP: `shadow_compare_legacy_tool`

The CLI caller selects an external root explicitly. The MCP tool caller cannot select the executable, root, adapter, or manifest. The server operator must set:

```sh
SEMANTIC_GUARD_ENABLE_LEGACY_SHADOW=1
SEMANTIC_GUARD_LEGACY_ROOT=/absolute/operator-owned/legacy-root
```

The external root must contain the server-expected relative baseline manifest, adapter, pinned interpreter, and digest-covered files. The baseline digest is fixed by the server implementation. `allow_baseline_drift` is diagnostic CLI behavior and must not be represented as a trusted match.

Shadow output keeps canonical result, legacy observation, and comparison separate. A matching legacy result is not a correctness proof; a difference requires adjudication.

## Schema access

CLI:

```sh
semantic-guard schema audit-result
semantic-guard schema llm-candidate-input
```

MCP: `semantic_guard_schema_tool(name)`

The name must be one of the closed known schema names. Path selection and unknown names are rejected. Schema availability does not imply that a sidecar has a public end-to-end runtime workflow.

## Exit and transport behavior

- CLI usage errors use exit code 2.
- Contract or input failures must not emit a successful audit result.
- `--fail-on never|warn|block` controls disposition-sensitive nonzero exit after valid JSON emission; it does not change the audit result.
- `--require-legacy` makes an unavailable, unpinned, schema-invalid, or incomplete legacy execution fail the shadow command.
- MCP transport errors and tool exceptions are distinct from `pass`, `warn`, or `block` in an audit payload.
- Standard output belongs to machine-readable results; diagnostics belong on standard error.

## Evidence and non-inference

Persist the tool and package version, input digest, schema version, provider/resource identity, command or MCP tool name, timestamp with timezone, and output digest when the result is durable evidence.

Do not infer field validity, external authenticity, security certification, policy adoption, operational qualification, or human acceptance from a valid payload, matching digest, passing test, or workflow `pass`.
