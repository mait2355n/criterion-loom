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
- Added `semantic-guard workflow evaluate-metamorphic`: replays every fixture under 37 semantics-preserving rewrites (full-width, decomposed kana, half-width katakana, zero-width characters inside words, five line-terminator forms, Markdown markers, line order, and eighteen label synonyms) and applies the spelling-level ones to the fixture's context, intent, request and evidence as well and deletes fields from known-good documents to check that the owning rule fires. It currently makes 1,595 substantive comparisons over 101 fixtures, all stable; comparisons where the rewrite left the text unchanged (1,346) are counted apart and are not evidence. The sensitivity check asserts the reaction of 31 of the 77 catalog rules. Exceptions are listed with a reason and fail as stale once they stop occurring; there are none now. It runs in CI.
- Normalized input at each workflow audit entry point (invisible format characters, NFKC, line terminators). Lexical findings quote the normalized text; logical derivation evidence maps back to original source coordinates and excerpts. Diff file identities remain unchanged. The requirement-relation and direction-binding audit runs on the normalized text when no morphology provider is configured, and its spans are mapped back to the caller's coordinates. With a provider, whose analysis is bound to the exact input, the bound summaries keep the caller's text while the verdict still comes from the provider-less normalized run; the decision frame and the direction binding of a provider run are still read from the caller's text, so a BOM or an invisible character inside a word can change whether a direction is bound (reproduced with the real Sudachi provider; a known limit, because the provider's analysis and the published offsets are bound to the exact input and the tests pin one provider execution per audit).
- Added 24 catalog rules so that every fixture finding is attributable to a rule (31 of 179 were not): `req.necessity.purpose_trace_missing`, `req.atomicity.multiple_requirements_bundled`, `req.solution.implementation_fixed`, `req.uncertainty.unknowns_unstated`, `req.clarity.ambiguous_term`, seven `doc.*` rules, eight `plan.*` rules (including `plan.scope.broad_scope_unbounded`, which detectors already referenced), `diff.traceability.intent_missing`, `diff.documentation.update_missing`, `finish.security.evidence_missing`, and `finish.risk.residual_risk_missing`. The catalog now holds 77 rules, each with a positive and a negative fixture (negative controls: 18 of 49 before, 77 of 77 after integration).
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
- Made the metamorphic harness able to fail: a rewrite that leaves the text unchanged is reported as identity and not counted; a verdict is status, score, each finding's rule and severity, and the gaps; evidence spans are checked against the audited text; an exception that hides a finding behind a pass fails the run; skipped morphology fixtures are listed; and a minimum number of comparisons and asserted rules is enforced. The ablation check now also covers a finish report and a README and asserts 31 of the 77 rules (it was 18).
- Pinned the CI workflow's trust boundary in `tests/test_ci_contract.py`: the metamorphic step, exactly the reviewed trigger set, a single top-level `contents: read` permission, no `pull_request_target`, no `continue-on-error`, the package job's `needs`, and the packaged-contract verification before the upload.
- Bound the field-sample intake to the policy decision it cites: the evaluation's decision record must replay to the bound one and precede the collection opening. Strict schema validation (`strict_schema.py`, identical in the four namespaces) reads an unescaped `$` as end of string and parses `date-time` for real; the published schemas are not edited, and every module under `src/` that builds a validator uses it (the verification scripts' own validators are not covered). Intake schema errors no longer repeat the offending value, references that look like an e-mail address, URL or file path are rejected, one subject cannot sit in two duplicate clusters, and a model or agent reference cannot hold a human-attested role.
- Made the distribution binding describe the bytes it judges: `scripts/distribution_binding.py` runs git without inherited `GIT_*` variables, rejects `skip-worktree` and `assume-unchanged` entries, requires a well-formed archive whose own metadata names this project and version, and prints ASCII JSON; `scripts/verify_packaged_contracts.py` copies each input once into a private directory so that the scan, the install and the reported digest describe that copy, accepts `--binding-manifest` to require the digests to equal the bound ones, and admits only `.py`, `py.typed` and two data directories in the main namespace. The binding does not prove the bytes came from the commit.
- Reviewer agents run in their own process group, which is killed as a whole on timeout; once the direct child exits, a descendant still holding an output pipe is stopped instead of making the call wait out the timeout and report a timeout; each captured stream is limited to 4 MiB with an explicit truncation marker. The Windows path (`taskkill /T`) is untested. Reviewer output is decoded as UTF-8 and an encoding failure is an `execution_error`. A `claude` envelope is accepted only with `subtype == "success"`, `is_error is False` and no permission denials.
- Reviewer options are validated before anything is decided or started: `timeout_seconds` must be positive, finite and at most 3600; `model` may not contain NUL or control characters or start with `-`; `working_directory` must exist and is resolved once, so `--cd` and the process `cwd` cannot each apply a relative path. MCP callers may name only directories under the server's current directory or `SEMANTIC_GUARD_WORKDIR_ROOTS`. `review-if-needed` validates before deciding whether a review is needed, and a `not_needed` result is no longer reported as a valid review.
- Command-template placeholders are expanded in a single pass, an unset placeholder drops its argument, and `--agent-binary` together with the command backend is an input error instead of being ignored.
- Background jobs run at most four at a time and keep at most 64 results; a start beyond either limit is `rejected` with a reason, an unread result is never evicted, and job snapshots omit the escalation payload (the text under review) unless `include_prompt` is set.
- Re-ran the 108 reproductions recorded by an independent review against the current tree and fixed what still reproduced: deferred-order wording (`未決`, `後日決定`, `決まっていない`, `決まり次第…`, `…後で決める`), the plan's own statement outranking the request and the context, the last labelled statement of an order standing (a later `順序: 後で決める` retracts an earlier order), the five quality signals that one line of `未定` cleared, figures that are rejected, denied, dated, quoted or in a code block, one-line excerpts and caller-coordinate spans whatever ends the lines, normalized trace-report links, `source`/`source_line` for referent lines, `infer_rule_id` no longer attributing arbitrary short text to a rule, and a quadratic audit of requirements with many records (29,600 characters: 22 s, now under 1 s). `audit-plan` and `audit-diff` now refuse another input kind, and `evaluate-fixtures` fails on a tree with no fixtures.
- Natural label synonyms (`ねらい`, `ゴール`, `完了条件`, `アウトプット`, `責任者`, `実施順`, `Introduction`) are accepted as the field they name. Replaying them exposed three vocabulary collisions that are fixed: `条件` inside `完了条件` counted as a precondition, `責任者` counted as a risk response, and `責任` inside `責任者` counted as evidence of hazard transfer. The harness also rewrites a fixture's `context`, `intent`, `request` and `evidence`, keeps list markers outside emphasis, does not split a sentence inside a quotation, and the sensitivity check compares the gap name where several fields share one rule id.
- Field-sample intake: one content digest shared across the original, normalized and evaluated fields of candidates in different duplicate units is rejected, a candidate record made after the duplicate review completed is rejected, and a permission that lacks both calibration and holdout uses names both. The CI contract test also forbids conditional steps, non-fatal commands, expressions outside a reviewed set (no secrets, no event data), other runners, and requires the lock check, the verification-source check, `--expected-commit` and the upload's `if-no-files-found: error`.
- Corrected the documentation: the asynchronous MCP `*_start_tool` family has no `execute` switch and starts the reviewer when called; reviewer child processes inherit the caller's whole environment; the `claude` preset's isolation is described by the flags it actually passes.

### Direction-binding audit: outside the registries is not a pass

- A live successor selection that neither the direction-space registry nor the scalar-axis registry covers now returns `primary_rule_evaluation.state=indeterminate` and `workflow_disposition.status=warn` with reason code `successor_selection_outside_registry`. Before, `円卓で、Aの次の席は誰ですか？` or `Cの次に背が高い人は誰ですか？` produced no frame and returned `not_applicable` with `pass`, and `--fail-on warn` exited 0, which reads as "checked and fine".
- The boundary uses the detectors' own source grammar (reference, `の`, `次`, a registered selection ending) and their exclusions (fenced code, quotation, examples, retired wording). Text without such a selection stays `not_applicable`. Context cannot supply the primary operation. No frame is invented and both summaries are unchanged.
- The schema `semantic-guard-direction-binding-audit/v1` is unchanged: the shape (emitter `none`, state `indeterminate`, both summaries `not_applicable`) was already valid. Validation replays the boundary from the source text and rejects a relabelling in either direction. Payloads recorded by earlier `1.2.0.dev0` builds for such inputs no longer replay.
- This states that the registries cannot evaluate the expression. It is not a gap finding and adds no language coverage: a selection whose order is evident from context is also `indeterminate`.

### Workflow audits no longer pass on wording alone

These change workflow results for inputs that previously passed. Canonical v1 and candidate contracts are unchanged.

- `finish-check` reads a completion report for what it says happened. Added `finish.evidence.failure_reported` (strict `blocker`, relaxed `major`): a failure count above zero, a failed or failing verification activity, a runner `FAILED` verdict, or unmet acceptance criteria in the summary or evidence blocks the completion claim. A report stating `テストが3件失敗しました`, or a success claim with `pytest: 3 failed, 117 passed` as evidence, previously returned `pass` with score 1.0. Request context is not read for failures, zero counts are not failures, and a later recorded successful re-run closes an earlier failure.
- Added `finish.evidence.receipt_missing` (strict `major`, relaxed `minor`): a statement that verification was done (`検証済み`) with no named command, count, exit state, or output location is a declaration, not a receipt, and now yields `warn`. A recorded not-run reason is exempt.
- A negated predicate directly after the action noun (`テストは実行していません`, `検証はしていません`) and an unresolved value followed by a copula (`受入基準は未確認です`, `テストは未実行です`) no longer count as evidence; before, the copula alone turned `未確認` into present evidence. Skipped, omitted and not-yet-started forms are treated the same way. One denied check no longer hides an independent receipt in the same clause.
- A failed representative execution still counts as execution evidence for `finish.implementation.behavior_evidence_missing`, but the report no longer passes: the reported failure is a separate finding. The tests that pinned `pass` for `CLI実行は失敗した` and `MCP build failed` now pin `block`.
- `残余リスク` and `残存リスク` are recognized as residual-risk statements.
- `audit-diff` no longer treats a deleted test file as a test change. Before, a source change alone returned `warn` (`diff.test_obligation.source_without_tests`), while the same change plus a deleted test file, or plus an added `@unittest.skip`, returned `pass` with score 1.0: removing the tests silenced the finding. A deleted test path now leaves the obligation open.
- Added `diff.test_obligation.tests_removed_or_disabled` (strict `blocker`, relaxed `major`): a deleted test file without replacement, a net loss of test definitions, or an added unconditional skip/xfail/disabled marker that the intent does not declare. Moved, renamed and split tests keep the definition count and are not flagged; `skipIf`-style platform guards and removed skip markers are not flagged; a requested feature removal that deletes the source file accounts for its tests.
- Added `diff.traceability.intent_scope_conflict` (strict `blocker`, relaxed `major`, `needs_human_decision`): the intent or context states an explicit limit (documents only, tests only, no code change, or a named file that must stay) and the diff changes files outside it. The same diff previously produced the same result under `数量を反映する` and under `READMEの誤字を修正する。コードは変更しない。`. Only stated limits are read; whether the diff implements the intent is not decided.
- Added `--fail-on never|warn|block` to the workflow audit commands. The default stays `never` (a completed audit exits 0 whatever its status); with a threshold the JSON is written first and the exit code is 3, the same value as the canonical CLI. `python -m semantic_guard_workflow.cli` now propagates that code.
- The catalog now holds 77 rules; five finish fixtures and five diff fixtures were added to both fixture trees and to the packaged-resource allowlist (103 fixtures after integration). These are bounded lexical readings of result statements and file lists, not a contradiction parser and not evidence of authenticity.

### Integration regression repairs

- Preserved labelled decision precedence across completion receipts, accepted concrete verification plans after approval, and kept explicit order retractions, current-system change requests and replacement quality thresholds distinct from deferred or historical statements.
- Prevented negated or conditional rerun claims, negated removal declarations and unrelated security-check results from satisfying the corresponding evidence checks. These remain bounded lexical checks; they do not match a failed check to the subject of a later successful rerun.
- Kept strict string patterns across referenced draft-2020-12 schemas without changing global validator registration, rejected invalid timezone offsets, and retained independent namespace copies.
- Stopped POSIX reviewer descendants after successful parent exit even when their output pipes were closed, and checked the wheel expansion budget before CRC decompression. Windows process-tree cleanup remains unverified.
- Reconciled the combined fixture catalog and field-deletion expectations; the receipt deletion now asserts its own missing evidence instead of remaining a silent exception.

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
