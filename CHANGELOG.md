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

- Added reviewer backends to the workflow interface. `--backend codex` (default, command line unchanged), `--backend claude` (Claude Code `claude -p --json-schema` with no tools, no persisted session, no setting sources, no MCP configuration and no skills; whether it also stops `CLAUDE.md` discovery and auto-memory in the working directory is not verified), and the operator-only `--backend command --agent-command TEMPLATE`. The MCP tools accept `backend` for `codex` and `claude` only; `command` is refused there because it would let a caller start an arbitrary process. Every backend is validated against the same schema.
- Review and exploration results gain a `backend` field (additive). `doctor` replaces the `codex_binary` check with `reviewer_agents`, which passes when any preset agent CLI is on `PATH`.
- Added `semantic-guard workflow evaluate-metamorphic`: replays every fixture under 31 semantics-preserving rewrites (full-width, decomposed kana, half-width katakana, zero-width characters inside words, five line-terminator forms, Markdown markers, line order, and twelve label synonyms) and deletes fields from known-good documents to check that the owning rule fires. It currently makes 1,317 substantive comparisons over 91 fixtures, all stable; comparisons where the rewrite left the text unchanged (984) are counted apart and are not evidence. The sensitivity check asserts the reaction of 30 of the 73 catalog rules. Exceptions are listed with a reason and fail as stale once they stop occurring; there are none now. It runs in CI.
- Normalized input at each workflow audit entry point (invisible format characters, NFKC, line terminators). Lexical findings quote the normalized text; logical derivation evidence maps back to original source coordinates and excerpts. Diff file identities remain unchanged. The requirement-relation and direction-binding audit runs on the normalized text when no morphology provider is configured, and its spans are mapped back to the caller's coordinates. With a provider, whose analysis is bound to the exact input, the bound summaries keep the caller's text while the verdict still comes from the provider-less normalized run; the provider path itself was not exercised in this environment.
- Added 24 catalog rules so that every fixture finding is attributable to a rule (31 of 179 were not): `req.necessity.purpose_trace_missing`, `req.atomicity.multiple_requirements_bundled`, `req.solution.implementation_fixed`, `req.uncertainty.unknowns_unstated`, `req.clarity.ambiguous_term`, seven `doc.*` rules, eight `plan.*` rules (including `plan.scope.broad_scope_unbounded`, which detectors already referenced), `diff.traceability.intent_missing`, `diff.documentation.update_missing`, `finish.security.evidence_missing`, and `finish.risk.residual_risk_missing`. The catalog now holds 73 rules, each with a positive and a negative fixture (negative controls: 18 of 49 before, 73 of 73 now).
- Aligned catalog `severity_policy` with detector output: the relaxed severity of 28 rules, and the strict severity of `plan.risk.rollback_missing` (the fixtures pinned `major`). Added a test that fails on any future divergence in either mode.
- `evaluate-fixtures` reports `unguarded_rule_ids`/`unguarded_rule_count` (rules without a negative control).
- The packaged-resource allowlist in `scripts/verify_packaged_contracts.py` lists the 23 new fixtures, including the missing quality-constraint positive control found during integration review. Positive and negative rule coverage are checked separately. `integration/workflow-migration.json` records import-time bytes and is not rewritten, so its destination digests no longer match the modified workflow files.
- Restricted line rotation and sentence splitting to structurally safe inputs, recording skipped transformations. Known drift must match the exact status and rule-set delta, so unrelated regressions cannot inherit an exception. These checks measure fixture stability and sensitivity, not accuracy on real documents.
- Documented POSIX argument quoting for command templates on every OS, including that a UNC path loses a leading backslash inside double quotes and must be single-quoted, written with forward slashes, or have its backslashes doubled.

### Workflow decision accuracy and reviewer runtime hardening

- Added one shared definition of a field's *decision state* (`decided`, `deferred`, `not_applicable`, `declared_none`, `negated`, `empty`) in `assertion_context.py`. A value counts as a decision whatever its spelling: list marker, bold label, table cell, heading, quote, trailing parenthesis or qualifier. A labelled value (exact label, table cell, heading, `Xは...`) outranks a passing mention elsewhere, and a compound label such as `検証結果` carries its own value. A deferral (`TBD`, `未定`, `後で決める`, `検討中`, `別途`, ...) raises the same rule at the same severity as an absent field and is named as deferred; "nothing" (`なし`, `該当なし`) is accepted only for non-goals, unknowns, risks and dependencies. `検証: 実施しない` and `戻し方: 戻さない` no longer satisfy the verification and rollback fields.
- Read the plan's required fields, its resource, risk-response, baseline, decision-gate and work-package signals, the request audit's purpose, non-requirement and unknowns checks, and the finish report's remaining-risk check through that definition. A broad rewrite is bounded only by controls that are stated as decisions. Order is recognised from constructs that relate two steps rather than from the words `後で` and `先に`.
- A security word counts as finish evidence only where a confirmation is stated, so `セキュリティ確認は未実施` and a bare `安全。` no longer silence `finish.security.evidence_missing`. Test files are classified by directory and file-name convention instead of substrings (`latest_release.py` is not a test), an intent of `未定` or `-` is no intent, and failure-handling evidence ignores comments and matches whole words.
- A measurable quality constraint needs a number with a unit, a number bound by `以内/以上/以下/未満/超`, a rate, or a comparator directly before a number and unit; a bare `以上`, the units `分/件/回` alone, and the substrings `slo`/`sla` no longer satisfy it, and a long digit run no longer takes quadratic time.
- Fixed small detector defects: `not` no longer matches `notification`, `CLI`/`API` no longer match `client`, case folding keeps text length so evidence spans do not shift, `excerpt_around` stops at every line terminator, and a plan that states a field itself is judged on its own statement.
- Removed every Unicode format character (category `Cf`, variation selectors, U+034F, U+180B-180F, tag characters) during input normalization instead of a hand-written list, unified U+2028, U+2029 and U+0085 with the other line terminators, and matched diff-summary signals on the normalized view of the diff while keeping diff file identities unchanged.
- Selected reviewer rules by input kind (a requirement review no longer carries the seven document rules), made an unknown rule id an input error, stated in the prompt that `does_not_apply_when` is advisory, and accepted one-word label synonyms (`対象外`/`スコープ外`/`範囲外`, `原因`/`要因`, `受入基準`/`合格基準`, `期待結果`/`期待される結果`, `証拠`/`証跡`, ...); thirteen fixtures now state their obligations in sentences rather than labelled fields.
- Made the metamorphic harness able to fail: a rewrite that leaves the text unchanged is reported as identity and not counted; a verdict is status, score, each finding's rule and severity, and the gaps; evidence spans are checked against the audited text; an exception that hides a finding behind a pass fails the run; skipped morphology fixtures are listed; and a minimum number of comparisons and asserted rules is enforced. The ablation check now also covers a finish report and a README and asserts 30 of the 73 rules (it was 18).
- Pinned the CI workflow's trust boundary in `tests/test_ci_contract.py`: the metamorphic step, exactly the reviewed trigger set, a single top-level `contents: read` permission, no `pull_request_target`, no `continue-on-error`, the package job's `needs`, and the packaged-contract verification before the upload.
- Bound the field-sample intake to the policy decision it cites: the evaluation's decision record must replay to the bound one and precede the collection opening. Strict schema validation (`strict_schema.py`, identical in the four namespaces) reads an unescaped `$` as end of string and parses `date-time` for real; the published schemas are not edited, and every module under `src/` that builds a validator uses it (the verification scripts' own validators are not covered). Intake schema errors no longer repeat the offending value, references that look like an e-mail address, URL or file path are rejected, one subject cannot sit in two duplicate clusters, and a model or agent reference cannot hold a human-attested role.
- Made the distribution binding describe the bytes it judges: `scripts/distribution_binding.py` runs git without inherited `GIT_*` variables, rejects `skip-worktree` and `assume-unchanged` entries, requires a well-formed archive whose own metadata names this project and version, and prints ASCII JSON; `scripts/verify_packaged_contracts.py` copies each input once into a private directory so that the scan, the install and the reported digest describe that copy, accepts `--binding-manifest` to require the digests to equal the bound ones, and admits only `.py`, `py.typed` and two data directories in the main namespace. The binding does not prove the bytes came from the commit.
- Reviewer agents run in their own process group, which is killed as a whole on timeout; once the direct child exits, a descendant still holding an output pipe is stopped instead of making the call wait out the timeout and report a timeout; each captured stream is limited to 4 MiB with an explicit truncation marker. The Windows path (`taskkill /T`) is untested. Reviewer output is decoded as UTF-8 and an encoding failure is an `execution_error`. A `claude` envelope is accepted only with `subtype == "success"`, `is_error is False` and no permission denials.
- Reviewer options are validated before anything is decided or started: `timeout_seconds` must be positive, finite and at most 3600; `model` may not contain NUL or control characters or start with `-`; `working_directory` must exist and is resolved once, so `--cd` and the process `cwd` cannot each apply a relative path. MCP callers may name only directories under the server's current directory or `SEMANTIC_GUARD_WORKDIR_ROOTS`. `review-if-needed` validates before deciding whether a review is needed, and a `not_needed` result is no longer reported as a valid review.
- Command-template placeholders are expanded in a single pass, an unset placeholder drops its argument, and `--agent-binary` together with the command backend is an input error instead of being ignored.
- Background jobs run at most four at a time and keep at most 64 results; a start beyond either limit is `rejected` with a reason, an unread result is never evicted, and job snapshots omit the escalation payload (the text under review) unless `include_prompt` is set.
- Corrected the documentation: the asynchronous MCP `*_start_tool` family has no `execute` switch and starts the reviewer when called; reviewer child processes inherit the caller's whole environment; the `claude` preset's isolation is described by the flags it actually passes.

### Fixed

- Stopped a bare `<` or `>` (quote marker, arrow, HTML tag, generic) from satisfying the measurable-constraint obligation, and tightened unit matching so that `5 sources` is not `5 s`.
- Made the deliverable item count read only the deliverable sentence, so a plan written on one line no longer gains `plan.structure.work_package_decomposition_missing` that the same plan split across lines does not.
- Prefer an explicit deliverable field over deliverable words inside an objective. Order is recognised from order constructs rather than from the words `後で` and `先に`, so `後で決める` no longer counts as a dependency sequence and a concrete order still does.
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
