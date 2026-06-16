# Logical Audit Integration Plan 2026-06-02

## Purpose

This plan turns the logical-audit consistency check into a staged implementation path.

The goal is not to shift `semantic-guard` into a full formal proof system. The goal is to add selected logic-side capabilities that make deterministic findings more inspectable:

- first-class facts extracted from supplied text.
- executable rule predicates for selected rules.
- obligation and countercondition records.
- derivation records attached to emitted findings.
- an explicit scope statement for what those records can and cannot establish.

## Audience And Use

This document is for the maintainer and Codex work that will implement the first logical-audit slices.

Use it after `docs/logical-audit-consistency-check-2026-06-02.md` and before changing `src/semantic_guard/models.py`, `src/semantic_guard/rules.py`, or `src/semantic_guard/core.py`.

Representative commands:

```sh
uv run --python 3.13 --project . semantic-guard audit-plan --file docs/logical-audit-integration-plan-2026-06-02.md
uv run --python 3.13 --project . semantic-guard audit-request --kind document --file docs/logical-audit-integration-plan-2026-06-02.md
uv run --python 3.13 --project . python -m unittest discover -s tests -v
uv run --python 3.13 --project . semantic-guard evaluate-fixtures
```

## Initial Baseline

Baseline at the start of this plan:

- Documentation and schema backup exists at `backup-snapshot/docs-2026-06-02T12-22-15+0900/`.
- Logical-audit consistency check exists at `docs/logical-audit-consistency-check-2026-06-02.md`.
- Unit tests previously passed: 110 tests OK.
- Fixture evaluation at plan start passed: 15 total, 15 passed, pass rate 1.0.
- Current output contract already supports optional details and finding fields.
- Current `Rule` catalog is explanatory, not executable.
- Current LLM reviewer is a supplement generator only.
- Human final decision remains outside the tool.

## Objective

This is the intended implementation target, not evidence that the logical-audit layer already exists.

Add a narrow logical-audit layer that can explain selected deterministic findings by showing:

- what facts were accepted or rejected.
- why a rule applied.
- which counterconditions were checked.
- which obligations were satisfied or missing.
- why a finding was derived.
- which unknowns remain unresolved.

## Non-Goals

- Do not prove natural-language truth.
- Do not prove semantic satisfaction.
- Do not replace human acceptance, domain review, security review, or acceptance testing.
- Do not turn LLM reviewer output into accepted facts.
- Do not change the meaning of `score` into derivation strength.
- Do not migrate all 36 catalog rules at once.
- Do not break existing CLI, MCP, fixture, or JSON output consumers.

## Design Constraints

### Output Compatibility

Existing phase output must keep:

- `phase`
- `status`
- `score`
- `findings`
- `missing`
- `next_actions`
- `details`

New logical output must be optional:

- `finding.derivation`
- `details.logical_trace`

Existing diagnostics remain valid:

- `warning_class`
- `match_status`
- `confidence`
- `candidate_matches`
- `details.non_emitted_rules`
- `details.diagnostics`
- `details.severity_profile`

### Derivation Scope

Every derivation record must state its scope:

> This derivation is valid only under the extracted facts, accepted counterconditions, and current executable rule predicate. It does not prove that the original natural-language artifact is true, complete, safe, or accepted.

### LLM Boundary

LLM reviewer output may only provide:

- candidate facts.
- candidate counterconditions.
- questions.
- supplement proposals.

LLM reviewer output must not directly create accepted facts, derivation records, final findings, or final decisions.

### Human Decision Boundary

`acceptance_review_bundle` remains the final human-review package.

`final_human_decision.status` remains `pending` until a person decides.

Strict acceptance-bundle validation remains part of the boundary. A final bundle still needs deterministic audit material, execution evidence, and human review points before it can be presented as ready for human acceptance.

### Escalation Boundary

`review-if-needed` remains an uncertainty router, not a default reviewer call.

The default remains dry-run. Logical traces must not automatically execute the LLM reviewer, and reviewer output must not be promoted into accepted facts, derivation steps, findings, or acceptance decisions without deterministic evidence or an explicit human decision.

### Trace And Vocabulary Boundary

Existing `trace-report` vocabulary output remains diagnostic.

`suggested_tags`, unresolved terms, weak vocabulary links, and trace vocabulary gaps must not become logical facts by implication. A domain term or trace tag counts as accepted only when the caller supplies explicit `tags` or a `vocabulary_profile` entry with accepted status, or when a deterministic extractor records a separately evidenced fact.

### Public Positioning Boundary

The logical-audit layer must preserve the existing public positioning.

Do not present `semantic-guard` as a formal requirements engine, security scanner, release gate, MCP competitor, AI safety engine, or autonomous acceptance system. Logical derivation records are a narrower diagnostic surface inside the existing meaning-first audit layer.

## Work Packages

### WP0: Baseline And Backup

Status: done.

Deliverables:

- Documentation backup under `backup-snapshot/docs-2026-06-02T12-22-15+0900/`.
- `MANIFEST.sha256` for backup verification.
- Consistency check document.

Acceptance evidence:

- `shasum -a 256 -c MANIFEST.sha256`: all backed-up files OK.
- `docs/logical-audit-consistency-check-2026-06-02.md` document audit: pass.

### WP1: Logical Audit Design Document

Purpose:

Define the stable vocabulary before adding code.

Deliverables:

- `docs/logical-audit-design.md`

Required content:

- `Fact`
- `FactSource`
- `EvidenceSpan`
- `RuleEvaluation`
- `DerivationStep`
- `Obligation`
- `Countercondition`
- `LogicalTrace`
- derivation-scope wording.
- `pass`, `warn`, and `block` semantics under logical scope.
- LLM candidate-fact boundary.

Acceptance criteria:

- The document says natural-language truth is not proven.
- The document preserves output compatibility.
- The document limits first implementation to `req.verifiability.acceptance_missing`.
- `semantic-guard audit-request --kind document` returns pass.

Verification:

```sh
uv run --python 3.13 --project . semantic-guard audit-request --kind document --file docs/logical-audit-design.md
```

### WP2: Compatibility-Only Logical Model

Status: done.

Purpose:

Add serializable logical-audit data structures without changing audit behavior.

Likely files:

- `src/semantic_guard/logic.py`
- `tests/test_logic.py`

Model candidates:

- `FactStatus`: `present`, `absent`, `candidate`, `rejected`, `unknown`, `conflict`.
- `DerivationStatus`: `derived`, `not_derived`, `blocked_by_unknown`, `conflict`, `not_applicable`, `satisfied`.
- `Fact`
- `EvidenceSpan`
- `Obligation`
- `Countercondition`
- `RuleEvaluation`
- `DerivationStep`
- `LogicalTrace`

Acceptance criteria:

- Unit tests cover JSON-compatible dictionary serialization for model examples.
- No existing public output changes.
- No audit behavior changes.
- Unit tests cover default and empty states.

Verification:

```sh
uv run --python 3.13 --project . python -m unittest tests.test_logic tests.test_core
```

Acceptance evidence:

- `src/semantic_guard/logic.py` defines compatibility-only logical-audit data structures and JSON-compatible `as_dict()` methods.
- In the WP2-only state, `tests/test_logic.py` covered model serialization, default and empty states, nested `LogicalTrace` serialization, candidate fact boundaries, and the absence of `details.logical_trace` or `finding.derivation` before WP5 exposed optional derivation output.
- `python -m unittest tests.test_logic -v`: 8 tests OK.
- `python -m unittest tests.test_logic tests.test_core -v`: 62 tests OK.
- `python -m unittest discover -s tests -v`: 118 tests OK.
- `semantic-guard evaluate-fixtures`: 15 total, 15 passed, pass rate 1.0.
- `src/semantic_guard/core.py`, `src/semantic_guard/models.py`, `src/semantic_guard/rules.py`, CLI, MCP, README, and schemas were not changed for WP2.

### WP3: Fact Extraction For One Rule

Status: done.

Purpose:

Introduce first-class facts behind `audit_request` without emitting derivation output yet.

Target rule:

- `req.verifiability.acceptance_missing`

Candidate facts:

- `input.kind.requirement`
- `text.has_verification_language`
- `text.has_acceptance_criteria`
- `text.has_verification_method`
- `text.has_evidence_artifact`
- `context.has_external_acceptance_route`

Implementation constraints:

- Facts should cite short excerpts or stable source labels.
- Facts should include extraction method.
- Rejected or candidate facts must not count as facts used by derivation records.
- Existing findings must remain unchanged.

Likely files:

- `src/semantic_guard/logic.py`
- `src/semantic_guard/core.py`
- `tests/test_logic.py`
- `tests/test_core.py`

Acceptance criteria:

- `audit_request` can internally build a `LogicalTrace` for the target rule.
- The public output remains unchanged unless a debug or private helper test reads the trace.
- Existing tests and fixtures still pass.

Implementation note:

WP3 was completed as part of the WP3-WP5 vertical slice. The final public output now includes the WP5 optional trace surface, so the WP3-only "public output remains unchanged" condition is superseded by the WP5 additive-output condition.

Acceptance evidence:

- `src/semantic_guard/logic.py` builds facts for `input.kind.requirement`, verification language, acceptance criteria, verification method, evidence artifact, and external acceptance route context.
- Facts include source, extraction method, checked scope, and excerpt evidence when present.
- Candidate, rejected, unknown, and conflict statuses remain unable to satisfy obligations.
- `tests.test_logic` covers derived, not-derived, satisfied, and not-applicable target trace states.

Verification:

```sh
uv run --python 3.13 --project . python -m unittest tests.test_logic tests.test_core tests.test_fixtures
uv run --python 3.13 --project . semantic-guard evaluate-fixtures
```

### WP4: Executable Predicate For One Rule

Status: done.

Purpose:

Move one rule from prose-only applicability to deterministic predicate evaluation.

Target rule:

- `req.verifiability.acceptance_missing`

Predicate sketch:

```text
applies when:
  input.kind.requirement is present
  and text.has_verification_language is absent
  or text.has_acceptance_criteria is absent

does not apply when:
  input.kind is document, plan, diff-summary, or finish report
  or context.has_external_acceptance_route is present

missing obligations:
  acceptance criteria
  verification method
  evidence artifact when verification is claimed
```

Acceptance criteria:

- Predicate result matches current expected behavior for existing fixtures.
- Predicate records checked counterconditions.
- Unknown facts produce `blocked_by_unknown` or `warn`, not silent pass.
- No LLM path is involved.

Acceptance evidence:

- The executable predicate is limited to `req.verifiability.acceptance_missing`.
- The predicate derives the target finding only when the existing target rule finding is emitted.
- Secondary obligations can be visible as missing without creating new legacy findings.
- No LLM reviewer path is imported or called from the logical trace builder.

Verification:

```sh
uv run --python 3.13 --project . python -m unittest tests.test_logic tests.test_core tests.test_fixtures
```

### WP5: Optional Proof Output

Status: done.

Purpose:

Expose derivation records without changing the stable result contract.

Output additions:

- `finding.derivation`
- `details.logical_trace`

Minimum `finding.derivation` shape:

```json
{
  "schema_version": "logical-derivation/v1",
  "derivation_scope": "rule-and-fact derivation only",
  "rule_id": "req.verifiability.acceptance_missing",
  "status": "derived",
  "facts_used": [],
  "counterconditions_checked": [],
  "missing_obligations": [],
  "derivation_steps": [],
  "unresolved_unknowns": []
}
```

Minimum `details.logical_trace` shape:

```json
{
  "schema_version": "logical-trace/v1",
  "scope": "extracted facts and executable predicates only",
  "rules_evaluated": [],
  "facts": [],
  "unknowns": [],
  "conflicts": []
}
```

Acceptance criteria:

- Existing fields still appear and keep their meanings.
- Derivation output appears only for the target rule.
- No derivation output is emitted for unrelated findings.
- Derivation records do not alter `score`.
- `status` changes only if predicate behavior intentionally matches current warning behavior.

Acceptance evidence:

- `Finding` now has optional `derivation`.
- `audit_request` attaches `finding.derivation` only to emitted `req.verifiability.acceptance_missing` findings.
- `audit_request` adds `details.logical_trace` for requirement audits and a short `details.diagnostics.logical_trace` summary.
- Detailed requirement regression keeps `status=pass` and `score=1.0` while recording a satisfied trace.
- Representative CLI output shows `logical-derivation/v1` and `logical-trace/v1` with the derivation scope wording.

Verification:

```sh
uv run --python 3.13 --project . python -m unittest tests.test_logic tests.test_core tests.test_fixtures tests.test_mcp_tools
uv run --python 3.13 --project . semantic-guard evaluate-fixtures
```

### WP6: Fixture And Evaluation Support For Derivation

Status: done.

Purpose:

Make derivation records testable without whole-output equality.

Likely files:

- `src/semantic_guard/evaluation.py`
- `tests/test_evaluation.py`
- `tests/fixtures/**`
- `docs/fixture-record-design.md`

Fixture matcher additions:

- `derivation_status`
- `derivation_rule_id`
- `derivation_missing_obligation`
- `derivation_countercondition`
- `derivation_fact`
- `logical_trace_rule`
- `logical_trace_summary_rule`
- `logical_trace_unknown`
- `logical_trace_conflict`

Acceptance criteria:

- Fixtures can assert derivation-shape invariants.
- Existing fixture labels still work.
- Evaluation still reports local calibration only.
- New metrics do not pretend statistical precision.
- `rule_catalog_coverage.unhit_rule_ids` continues to report rules not yet touched by fixture rule labels.

Acceptance evidence:

- `evaluate-fixtures` supports `derivation_status`, `derivation_rule_id`, `derivation_missing_obligation`, `derivation_countercondition`, `derivation_fact`, `logical_trace_rule`, `logical_trace_summary_rule`, `logical_trace_unknown`, and `logical_trace_conflict` expectations.
- `tests/fixtures/requests/ambiguous.expected.json` asserts target derivation and logical trace invariants.
- Evaluation metrics include `derivation_rule_hits`, `derivation_status_hits`, `logical_trace_rule_hits`, and `logical_trace_summary_rule_hits` as hit counts only.
- `evaluate-fixtures --include-passed`: 21 total, 21 passed, pass rate 1.0.

Verification:

```sh
uv run --python 3.13 --project . python -m unittest tests.test_evaluation tests.test_fixtures
uv run --python 3.13 --project . semantic-guard evaluate-fixtures --include-passed
```

### WP7: Documentation And Reviewer Boundary Update

Status: done.

Purpose:

Keep public positioning honest after derivation output appears.

Likely files:

- `README.md`
- `docs/llm-reviewer.md`
- `docs/acceptance-review-bundle.md`
- `docs/dogfood-readme-2026-06-01.md`

Required statements:

- Derivation records are rule-and-fact derivations only.
- Derivation records do not prove semantic satisfaction.
- LLM reviewer may suggest candidate facts but cannot accept them.
- Human final decision remains outside the tool.
- `review-if-needed` remains dry-run by default and limited to undecidable residue.
- Trace vocabulary suggestions are diagnostics, not accepted facts.
- Public positioning still excludes security scanner, release gate, MCP competitor, requirements-engineering replacement, and autonomous acceptance claims.

Acceptance criteria:

- README describes `finding.derivation` and `details.logical_trace`.
- Limitations section remains explicit.
- Document audit passes.

Acceptance evidence:

- `README.md` describes `finding.derivation`, `details.logical_trace`, derivation scope, fixture derivation expectations, and the non-statistical nature of derivation hit counts.
- `docs/llm-reviewer.md` states that LLM output may suggest candidate facts and counterconditions but cannot create accepted facts, derivation records, findings, or final decisions.
- `docs/acceptance-review-bundle.md` treats derivation records as deterministic audit material, not final approval.
- `docs/fixture-record-design.md` documents derivation expectation keys.
- `docs/dogfood-readme-2026-06-01.md` records the logical-audit follow-up request and implemented regression coverage.

Verification:

```sh
uv run --python 3.13 --project . semantic-guard audit-request --kind document --file README.md
uv run --python 3.13 --project . semantic-guard audit-request --kind document --file docs/llm-reviewer.md
```

### WP8: Second Rule Family Decision Gate

Status: done.

Purpose:

Decide whether the first slice is worth extending.

Entry conditions:

- WP1-WP7 pass.
- Existing fixtures pass.
- Target rule derivation output is readable and useful.
- No public output compatibility break.
- No user-facing confusion between derivation and final acceptance.

Candidate next rules:

- `req.verification.method_detail_missing`
- `req.evidence.artifact_missing`
- `plan.validation.owner_missing`
- `diff.implementation.public_contract_change`
- `finish.implementation.behavior_evidence_missing`

Decision options:

- `continue`: add next rule family.
- `pause`: keep the first slice as diagnostic-only.
- `revise`: redesign facts or derivation shape.
- `retire`: remove derivation output if it adds noise.

Decision:

- `pause`

Post-WP8 continuation:

- The maintainer later confirmed that the first derivation surface was readable enough to continue.
- The second slice is limited to `req.verification.method_detail_missing`.
- Remaining candidate rules stay deferred.

Acceptance evidence:

- Decision record: `docs/logical-audit-wp8-decision-2026-06-02.md`.
- Human-review bundle: `docs/logical-audit-wp3-wp8-acceptance-bundle-2026-06-02.json`.
- The first slice is kept as diagnostic output.
- Second-rule migration is deferred until a maintainer reads the public derivation shape in real use.
- Recommended next candidate after review: `req.verification.method_detail_missing`.
- Post-WP8 continuation record: `docs/logical-audit-second-slice-2026-06-02.md`.
- `semantic-guard validate-acceptance-bundle --file docs/logical-audit-wp3-wp8-acceptance-bundle-2026-06-02.json`: valid true.

## Dependency Sequence

1. WP1 must happen before code.
2. WP2 must happen before derivation output.
3. WP3 must happen before WP4.
4. WP4 must happen before WP5.
5. WP5 must happen before WP6.
6. WP6 and WP7 must both pass before WP8.

## Change Control

Use explicit change control for this plan.

Scope changes and additional requirements:

- Any scope change that adds another rule before `req.verifiability.acceptance_missing` is treated as deferred follow-up.
- Any additional requirement that changes public output shape before WP5 is held as `judgment pending`.
- Any deviation from output compatibility is blocked until a new plan audit passes.

Decision points:

- After WP1, decide whether the design is narrow enough for code.
- After WP5, decide whether derivation output is readable enough for fixture support.
- At WP8, decide whether to continue, pause, revise, or retire derivation output.

Replanning:

- If tests or fixture evaluation fail after WP2-WP7, stop expansion and replan from the last passing work package.
- If LLM reviewer behavior starts acting like accepted facts or final judgment, hold the change and revise the LLM boundary.

## Risk Response Controls

| Risk | Response Type | Response |
| --- | --- | --- |
| Derivation wording overclaims truth | Mitigation | Add derivation scope to every derivation record and README limitation; re-run document audit after wording changes. |
| Accepted facts become hidden LLM judgment | Avoidance | Keep LLM suggestions as `candidate` until deterministic evidence or human decision accepts them. |
| Output compatibility breaks | Mitigation | Add optional fields only; keep old fields and old fixture expectations; run MCP and fixture tests before release. |
| Derivation layer becomes another score | Avoidance | Use categorical derivation status, never derivation score. |
| All rules migrate at once | Avoidance | Limit first implementation to `req.verifiability.acceptance_missing`; defer second rule family to WP8. |
| Unknowns become false negatives | Mitigation | Carry `unknown` and `conflict` as first-class statuses; block silent pass when required facts are undecidable. |
| Diagnostic channels multiply | Mitigation | Attach logical output to existing `details.diagnostics` and findings, not a separate unrelated report. |
| First slice adds noise rather than value | Fallback | Use WP8 decision options to pause, revise, or retire derivation output before expanding. |

## Plan Acceptance Evidence

This planning pass has enough evidence when:

- This document exists.
- `audit-plan` on this document returns pass or only acceptable work-package warnings.
- `audit-request --kind document` on this document returns pass.
- `finish-check` records the document path and remaining non-implementation risk.

## Immediate Next Step

Implement the second request-verification slice only: `req.verification.method_detail_missing`.

Do not migrate another rule family until the second slice has the same implementation, fixture, representative output, document-audit, and human-readability checks.
