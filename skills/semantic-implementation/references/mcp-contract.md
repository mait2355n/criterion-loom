# semantic-guard v1 MCP and CLI contract

## Scope

This reference describes the `semantic-guard 1.1.0` source execution surface used by the companion Skill. Machine-readable field and enum definitions remain authoritative in `schemas/`. Installed wheel and sdist behavior must still be verified against the packaged artifacts selected by the operator.

Public CLI commands:

- `audit-requirement`
- `audit-direction-binding`
- `shadow-compare`
- `schema`

Public MCP tools:

- `audit_requirement_relations_tool`
- `audit_direction_binding_tool`
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

## Direction-binding audit

CLI:

```sh
semantic-guard audit-direction-binding --text "..." --morphology sudachi
semantic-guard audit-direction-binding --file prompt.txt --context "..."
```

MCP: `audit_direction_binding_tool`

Inputs:

- one of text, UTF-8 file, or standard input for the CLI;
- optional current `context`, appended after one newline and included in the source digest;
- `morphology`: `none` or `sudachi`;
- optional RFC 3339 `recorded_at`.

The direct result validates against `semantic-guard-direction-binding-audit/v1`. It contains `decision-frame-summary/v3`, `direction-binding-summary/v1`, one `primary_rule_evaluation`, and a typed `workflow_disposition`. The two summaries have disjoint primary-emission scopes. Morphology remains `signal_only`, and numeric evidence is auxiliary and non-decisional.

The primary operation frame must be wholly inside the `text` input region. `context` is digest-bound auxiliary material; a context-only question or example cannot become the primary operation, and a postposed context phrase does not replace direct source attachment.

For strict replay in Python, pass the known `text` and `context` separately to `validate_direction_binding_audit`. Passing only their combined `source_text` checks source and self-declared region consistency, but cannot prove the original role boundary against relabeling.

`morphology=none`, partial coverage, provider failure, or an invalid provider contract remains visible in `execution` and cannot be converted into a direction finding. The machine result never chooses a direction and keeps `acceptance_owner.acceptance_status=pending`.

This is an independent additive contract. It does not add fields to `audit-result/v0`, change requirement-relation obligations, or make the direction result part of requirement assurance.

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
semantic-guard schema direction-binding-audit
semantic-guard schema llm-candidate-input
```

MCP: `semantic_guard_schema_tool(name)`

The name must be one of the 24 closed known schema names in the 1.1.0 source registry. Path selection and unknown names are rejected. `direction-binding-audit` has a matching CLI and MCP runtime; availability of any other sidecar schema still does not imply a public end-to-end workflow.

## Exit and transport behavior

- CLI usage errors use exit code 2.
- Contract or input failures must not emit a successful audit result.
- `--fail-on never|warn|block` controls disposition-sensitive nonzero exit after valid JSON emission; it does not change the audit result.
- `--require-legacy` makes an unavailable, unpinned, schema-invalid, or incomplete legacy execution fail the shadow command.
- MCP transport errors and tool exceptions are distinct from `pass`, `warn`, or `block` in an audit payload.
- Standard output belongs to machine-readable results; diagnostics belong on standard error.
- An unexpected internal exception that produces no schema-valid public JSON is a process/tool failure, not an audit `block`. A common structured internal-error envelope is outside the 1.1.0 contract and remains future work.

## Evidence and non-inference

Persist the tool and package version, input digest, schema version, provider/resource identity, command or MCP tool name, timestamp with timezone, and output digest when the result is durable evidence.

Do not infer field validity, external authenticity, security certification, policy adoption, operational qualification, or human acceptance from a valid payload, matching digest, passing test, or workflow `pass`.
