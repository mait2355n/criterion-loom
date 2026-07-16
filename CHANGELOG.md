# Change Log

All notable repository and public-contract changes are recorded here. Package versions follow semantic versioning; schema versions remain independent and change only when their own contract changes.

## [1.0.0] - 2026-07-17

### Canonicalized

- Promoted the contract-first audit kernel to the canonical `semantic-guard` package, Python module, CLI, and MCP server.
- Established `audit-requirement`, `shadow-compare`, and `schema` as the three public CLI commands.
- Established `audit_requirement_relations_tool`, `shadow_compare_legacy_tool`, and `semantic_guard_schema_tool` as the three public MCP tools.
- Made the fail-closed requirement-obligation result, analyzer authority ceilings, provenance, coverage, unresolved obligations, and versioned schemas the canonical public contract.

### Archived

- Froze the former `semantic-guard 0.1.0` source under `legacy/semantic-guard-v0.1.0/`.
- Kept the old request, plan, diff, finish, convention, reviewer, and acceptance-bundle commands in the frozen legacy source only. They are not transparently forwarded by 1.0.0.
- Preserved dated validation records as historical observations rather than rewriting them as 1.0.0 evidence.

### Breaking changes

- Replaced the former multi-command 0.1.0 CLI with the three-command v1 audit kernel.
- Replaced the former broad MCP tool surface with the three v1 MCP tools.
- Changed package and public implementation identity from the prerelease candidate identity to `semantic-guard 1.0.0`.
- Legacy comparison now requires an explicitly selected, operator-owned, hash-pinned external legacy execution root. The repository archive alone is not an executable trust root.

### Verification and governance

- Added v1 unit, verification-source, generated-projection, engineering-rule-pack, wheel, installed CLI/MCP, and legacy smoke checks to CI.
- Added a canonical-promotion decision, migration guide, and canonicalization audit.
- Kept lifecycle profiles and the engineering rule pack in candidate or pending-human-adoption state.

### Non-claims

1.0.0 does not claim field accuracy, production qualification, security certification, human adoption, external action authenticity, all-lifecycle workflow coverage, or operational default cutover.

## [0.1.0] - archived 2026-07-17

The former local research prototype is preserved under `legacy/semantic-guard-v0.1.0/`. Its own changelog and dated documents remain historical records of that line.
