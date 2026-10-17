# Change Log

All notable repository and public-contract changes are recorded here. Package versions follow semantic versioning; schema versions remain independent and change only when their own contract changes.

## [Unreleased]

### Integration development version: 1.2.0.dev0

- Added a prospective field-sample intake sidecar and schema with permission, privacy, duplicate-cluster and evaluation-binding checks. Its human-owned policy remains pending; no field collection or performance claim is made.
- Bound CI distributions to a clean Git commit and tree, pinned workflow Actions and uv, and added Python 3.12 plus macOS/Windows packaging checks while retaining all three regression suites.
- Added explicit workflow and governed-candidate CLI routes and separate MCP servers in one distribution. Existing canonical result schemas and four MCP tools remain distinct.
- Imported the local workflow implementation into `semantic_guard_workflow`, and preserved the candidate namespaces and package-local resources. Historical legacy archive bytes are retained.
- Recorded source mappings, added coexistence regression tests, and extended installed-package checks. Candidate governance adoption, privileged U10 deployment, field validity, and runtime cutover are outside this change.


### Workflow reviewer agents and mechanical rule checks

- Added reviewer backends to the workflow interface. `--backend codex` (default, command line unchanged), `--backend claude` (Claude Code `claude -p --json-schema`, no tools, no session, no settings/MCP/skills), and the operator-only `--backend command --agent-command TEMPLATE`. The MCP tools accept `backend` for `codex` and `claude` only; `command` is refused there because it would let a caller start an arbitrary process. Every backend is validated against the same schema.
- Review and exploration results gain a `backend` field (additive). `doctor` replaces the `codex_binary` check with `reviewer_agents`, which passes when any preset agent CLI is on `PATH`.
- Added `semantic-guard workflow evaluate-metamorphic`: replays every fixture under 14 semantics-preserving rewrites (full-width, decomposed kana, half-width katakana, zero-width characters, CRLF, Markdown markers, line order, ...) and deletes fields from known-good documents to check that the owning rule fires. Exceptions are listed with a reason and fail as stale once they stop occurring. It runs in CI.
- Normalized input at each workflow audit entry point (invisible format characters, NFKC, line terminators). Lexical findings quote the normalized text; logical derivation evidence maps back to original source coordinates and excerpts. Diff file identities remain unchanged. The requirement-relation and direction-binding audit still receives the caller's text because its spans and morphology binding refer to it, so it remains sensitive to full-width, decomposed-kana, and half-width-katakana spelling (registered as known drift).
- Added 24 catalog rules so that every fixture finding is attributable to a rule (31 of 179 were not): `req.necessity.purpose_trace_missing`, `req.atomicity.multiple_requirements_bundled`, `req.solution.implementation_fixed`, `req.uncertainty.unknowns_unstated`, `req.clarity.ambiguous_term`, seven `doc.*` rules, eight `plan.*` rules (including `plan.scope.broad_scope_unbounded`, which detectors already referenced), `diff.traceability.intent_missing`, `diff.documentation.update_missing`, `finish.security.evidence_missing`, and `finish.risk.residual_risk_missing`. The catalog now holds 73 rules, each with a positive and a negative fixture (negative controls: 18 of 49 before, 73 of 73 now).
- Aligned catalog `severity_policy` with detector output: the relaxed severity of 28 rules, and the strict severity of `plan.risk.rollback_missing` (the fixtures pinned `major`). Added a test that fails on any future divergence in either mode.
- `evaluate-fixtures` reports `unguarded_rule_ids`/`unguarded_rule_count` (rules without a negative control).
- The packaged-resource allowlist in `scripts/verify_packaged_contracts.py` lists the 23 new fixtures, including the missing quality-constraint positive control found during integration review. Positive and negative rule coverage are checked separately. `integration/workflow-migration.json` records import-time bytes and is not rewritten, so its destination digests no longer match the modified workflow files.
- Restricted line rotation and sentence splitting to structurally safe inputs, recording skipped transformations. Known drift must match the exact status and rule-set delta, so unrelated regressions cannot inherit an exception. These checks measure fixture stability and sensitivity, not accuracy on real documents.
- Documented POSIX argument quoting for command templates on every OS, and the inherited limitation that timeout supervision does not stop a wrapper's entire descendant process tree.

### Fixed

- Stopped a bare `<` or `>` (quote marker, arrow, HTML tag, generic) from satisfying the measurable-constraint obligation, and tightened unit matching so that `5 sources` is not `5 s`.
- Made the deliverable item count read only the deliverable sentence, so a plan written on one line no longer gains `plan.structure.work_package_decomposition_missing` that the same plan split across lines does not.
- Prefer an explicit deliverable field over deliverable words inside an objective, and reject deferred sequence placeholders such as `順序: 後で決める` while retaining concrete, unlabelled order statements.
- Prevented a Markdown quote followed by a bare count from becoming a measurable threshold, while retaining real comparisons and units.
- Stopped `成果物` (deliverables) from satisfying the plan objective through the substring `成果`.
- Recognised Markdown headings inside quotes and list items when checking document structure and splitting claim blocks.
- Prevented state-assessment freshness checks from overflowing for schema-valid large policy lifetimes or observations near the maximum representable year. Expiration still occurs at the earlier evidence or policy deadline, including exact microsecond boundaries and ties.

### Documentation and distribution metadata

- Rebuilt the public entry path around an evidence-backed value statement, a reproducible input-command-output example, explicit current limits, interface choice, and task-oriented English/Japanese documentation maps.
- Reframed the direction-binding quickstart around its general decision and fail-closed boundaries, consolidated the paired positive/negative comparison in the detailed reference, and documented the overview/reference/test layering rule for future changes.
- Added a runnable requirement-audit path, separated historical decisions from current reference, and exposed the distinct states of internal, candidate, and public-workflow material in both documentation maps.
- Reworked current Japanese explanatory prose into ordinary Japanese while preserving machine identifiers, evidence states, non-claims, and historical records; synchronized the affected documentation anchors.
- Closed integration-preflight evidence bindings by synchronizing the current origin and constitution observations, checking the constitution's embedded origin digests, and testing the human-readable matrix against its canonical source.
- Restored the Criterion Loom public-project name while retaining `semantic-guard` for the package, CLI, and MCP surfaces.
- Separated the current 1.1.0 public-surface summary from dated 1.0.0 and repository-transfer evidence.
- Removed operator-local instructions, private-dialogue provenance, and unbound destructive-authorization wording from the public documentation surface.
- Added a public, non-sensitive contact-request route for reports that require a private follow-up channel.
- Repaired public prose in the 0.1.0 archive while retaining the original byte content at annotated tag `v0.1.0` and commit `e0a3dd39f17385b66f6361ade25eb44bed6e1ab3`.
- Replaced the tautological package summary in `pyproject.toml`; this changes metadata in future wheel and sdist builds but does not change the runtime API or schema contracts. No package-index artifact or release evidence is updated by this documentation change.

## [1.1.0] - 2026-08-23

### Added

- Added the independent `audit-direction-binding` CLI command, `audit_direction_binding_tool` MCP tool, and closed `semantic-guard-direction-binding-audit/v1` contract.
- Added bounded scalar direction coverage for 14 scale families and 49 axes, plus six non-scalar direction axes and twelve directions.
- Added a digest-bound source map and documentation index without rewriting the frozen 0.1.0 archive or adopting the deferred `vnext` candidate tree.

### Boundaries

- Preserved `audit-requirement` and `semantic-guard-audit-result/v0` without semantic changes.
- Kept morphology at `signal_only`; numeric projection remains auxiliary and cannot change the primary finding.
- Kept field validity, unrestricted-language accuracy, operational qualification, and final human acceptance outside the release claim.

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
