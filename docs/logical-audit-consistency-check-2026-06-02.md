# Logical Audit Consistency Check 2026-06-02

## Purpose

This document checks whether the proposed shift from heuristic audit output to logic-backed audit output is consistent with the current `semantic-guard` system.

The target direction is not to prove natural-language meaning. The target is to make the deterministic audit path explainable as:

- accepted or candidate facts.
- executable rule conditions.
- checked counterconditions.
- missing obligations.
- derivation records for emitted findings.
- explicit unresolved unknowns.

## Audience And Use

This document is for the maintainer and Codex work that will design or implement the logical-audit layer.

Use it before writing `docs/logical-audit-design.md` or adding `src/semantic_guard/logic.py`. It gives the current compatibility boundary, the tensions that must be preserved in the design, and the first implementation slice that should stay small.

## Usage Or Examples

Representative follow-up commands:

```sh
uv run --python 3.13 --project . semantic-guard audit-request --kind document --file docs/logical-audit-consistency-check-2026-06-02.md
uv run --python 3.13 --project . python -m unittest discover -s tests -v
uv run --python 3.13 --project . semantic-guard evaluate-fixtures
```

Expected use:

- Treat this as a consistency baseline, not as an implementation design.
- Use the compatibility findings as constraints for the design document.
- Use the tension findings as risks to avoid during implementation.
- Re-run the commands above after changing this document or starting the logical-audit design.

## Scope

Inspected surface:

- `README.md`
- `docs/rule-model.md`
- `docs/ambiguity-confidence-design.md`
- `docs/conflict-audit-2026-06-02.md`
- `docs/conflict-fix-plan-2026-06-02.md`
- `docs/llm-reviewer.md`
- `docs/acceptance-review-bundle.md`
- `src/semantic_guard/models.py`
- `src/semantic_guard/rules.py`
- `src/semantic_guard/core.py`
- `src/semantic_guard/traceability.py`
- `src/semantic_guard/severity_profiles.py`
- `tests/fixtures/**`

Non-goals:

- No code changes in this pass.
- No new formal proof engine yet.
- No LLM final decision path.
- No claim that `pass` proves semantic correctness.
- No statistical precision or recall claim beyond the existing local fixture labels.

## Current Baseline

Commands run:

```sh
uv run --python 3.13 --project . python -m unittest discover -s tests -v
uv run --python 3.13 --project . semantic-guard evaluate-fixtures --include-passed
```

Results:

- Unit tests: 110 tests, OK.
- Fixture evaluation: 15 total, 15 passed, pass rate 1.0.
- Rule catalog count reported by fixture evaluation: 36.
- Fixture coverage is explicitly local calibration only.
- The directory is not a Git repository, so this check uses file inspection and command evidence rather than `git diff`.

## Compatibility Findings

### F01: The existing output contract already has extension points

Status: compatible.

The public phase output already preserves the stable shape:

- `phase`
- `status`
- `score`
- `findings`
- `missing`
- `next_actions`
- `details`

This is compatible with adding optional logic fields without breaking current callers. The most natural placement is:

- `finding.derivation` for the derivation of one emitted finding.
- `details.logical_trace` for phase-level facts, obligations, and rule-evaluation summaries.

Constraint:

- These fields must be optional.
- Existing `status`, `score`, `missing`, and current diagnostic fields must remain readable.

### F02: Current rule catalog is conceptually close but not executable enough

Status: compatible but incomplete.

`Rule` already contains:

- `id`
- `discipline`
- `phase`
- `engineering_basis`
- `concern`
- `applies_when`
- `does_not_apply_when`
- `evidence_required`
- `severity_policy`
- `finding`
- `remediation`

This matches the logical-audit direction at the documentation level. The gap is that `applies_when` and `does_not_apply_when` are explanatory strings, not executable predicates.

Required next move:

- Keep the explanatory fields.
- Add a separate executable layer that maps rule ids to deterministic predicate functions or predicate descriptors.
- Do not pretend that the prose fields themselves are machine-checkable logic.

### F03: Diagnostics already separate several responsibility layers

Status: compatible.

Current output already distinguishes:

- emitted findings.
- non-emitted rules.
- field match diagnostics.
- severity-profile details.
- trace report audit, trace, and vocabulary statuses.

This is a good base for logical derivation records because derivation output can attach to existing diagnostic channels instead of inventing a parallel reporting system.

Constraint:

- Do not create a fourth unrelated "why" channel.
- Logical derivation data should reuse or normalize existing `diagnostics`, `non_emitted_rules`, `match_status`, `confidence`, and `candidate_matches`.

### F04: Human final decision boundary is aligned

Status: compatible and mandatory.

The current LLM reviewer and acceptance review bundle both preserve the boundary:

- LLM reviewer is supplement material only.
- `final_human_decision.status` remains `pending` until a person decides.

Logical audit output must keep this unchanged. A derivation object may justify why a deterministic finding was emitted, but it must not become a final accept/reject decision.

### F05: The current README already forbids overclaiming

Status: compatible.

The README says document claim triples are heuristic and not a proof system. It also says trace report cannot prove semantic satisfaction.

This means logical-audit work must be positioned narrowly:

- It may establish derivability inside a rule-and-fact model.
- It must not prove that the original natural-language artifact is true, complete, safe, or accepted.

## Tension Findings

### T01: `pass` still sounds stronger than the logical target allows

Risk: medium.

Current `pass` means the current checks emitted no blocking or meaningful warning. For logical audit, `pass` should be sharpened to:

> Under the accepted facts and current executable rules, no unresolved violation was derived.

This is not a behavior change, but it is an output-semantics clarification.

Required handling:

- Add a design note before changing code.
- If logic fields are added, include `derivation_scope` or `logic_scope` language in `details.logical_trace`.

### T02: Facts do not exist as first-class records

Risk: high.

Current code extracts signals, profiles, candidates, and matches, but it does not expose a shared fact model. Without facts, a derivation object would have to cite ad hoc strings from each phase, which would make the logical layer brittle.

Required handling:

- Add a small `Fact` model before adding derivation output.
- Each fact needs `id`, `name`, `value/status`, `source`, `span or excerpt`, `confidence`, and `extraction_method`.
- Distinguish `present`, `absent`, `candidate`, `rejected`, `unknown`, and `conflict`.

### T03: Rule predicates need a migration path

Risk: high.

Moving all 36 rules to executable predicates at once would be noisy and dangerous. The existing catalog is broad, and the fixture set is local calibration, not a full coverage proof.

Required handling:

- Start with one vertical slice: `req.verifiability.acceptance_missing`.
- Add fixtures for expected facts, expected derivation steps, and expected missing obligations.
- Keep legacy emission behavior until the vertical slice has enough evidence.

### T04: `score` is not a logical measure

Risk: medium.

`score` is currently severity-derived. Severity profiles also keep base score and profiled score separate. This is good, but a logical audit layer must not reuse score as derivation strength.

Required handling:

- Do not add derivation confidence as another score.
- Use categorical derivation status instead: `derived`, `not_derived`, `blocked_by_unknown`, `conflict`, `not_applicable`, `satisfied`.

### T05: LLM reviewer must be pushed further away from judgment

Risk: medium.

The current role boundary is already good. For logical audit, it needs one extra tightening:

- LLM reviewer may propose candidate facts or questions.
- Deterministic logic must decide whether facts are accepted, rejected, unknown, or conflicting.

Required handling:

- Do not let LLM output directly populate accepted facts.
- If LLM-suggested facts are introduced, mark them as `candidate` until deterministic evidence or human decision accepts them.

### T06: Existing conflict-plan documents are partially stale

Risk: low to medium.

The previous conflict fix plan lists several stages as future work, but current tests and README show some are already implemented or partly implemented:

- conflict fixtures exist.
- `non_emitted_rules` exists.
- `diagnostics` exists.
- trace report has split statuses.
- severity profile exposes `profiled_score`.
- document claim summary exists.
- bounded Japanese whole-plan and bounded work-package cases have tests.

Required handling:

- Treat `docs/conflict-fix-plan-2026-06-02.md` as historical planning evidence, not current next-step truth.
- Either add a short status addendum later or make the new logical-audit plan cite current baseline instead of the old stage labels.

## Sequencing Recommendation

Recommended order:

1. Write `docs/logical-audit-design.md`.
   - Define `Fact`, `FactSource`, `EvidenceSpan`, `RuleEvaluation`, `DerivationStep`, `Obligation`, `Countercondition`, and `LogicalTrace`.
   - Define exact `pass/warn/block` semantics under logical scope.
   - Define what derivation records can and cannot establish.

2. Add a compatibility-only model slice.
   - Add optional data classes or typed dictionaries in a new `src/semantic_guard/logic.py`.
   - Do not attach them to public output yet.
   - Add unit tests for serialization.

3. Implement facts for one requirement rule.
   - Target: `req.verifiability.acceptance_missing`.
   - Extract facts such as `input_kind=requirement`, `has_verification_language`, `has_acceptance_criteria`, `has_verification_method`, and `has_evidence_artifact`.
   - Preserve current `audit_request` findings.

4. Add derivation output for that one rule.
   - Add optional `finding.derivation`.
   - Add phase-level `details.logical_trace`.
   - Derivation must cite facts and checked counterconditions.

5. Add fixture expectations for derivation shape.
   - Check expected facts.
   - Check expected missing obligations.
   - Check expected counterconditions.
   - Check no derivation is emitted for unrelated findings.

6. Audit documentation and output compatibility.
   - README must describe derivation scope as rule-and-fact derivation only.
   - LLM reviewer docs must say candidate facts are not accepted facts.
   - Acceptance bundle remains human-final.

7. Only then expand to other rule families.
   - Next candidates: verification method detail, evidence artifact, validation owner, public contract diff, behavior evidence finish check.

## Acceptance Criteria For Starting Implementation

The next implementation step is acceptable when all of the following are true:

- `docs/logical-audit-design.md` exists and passes `audit-request --kind document`.
- The design explicitly says natural-language truth is not proven.
- The design preserves existing output compatibility.
- The first vertical slice is limited to `req.verifiability.acceptance_missing`.
- Existing tests and fixtures still pass before code changes.

## Current Decision

Logical audit is consistent with the current direction if it is added as a scoped derivation layer.

It is not consistent if it is presented as:

- proof of semantic satisfaction.
- a replacement for human acceptance.
- a replacement for domain review, security review, or acceptance testing.
- a new score or statistical confidence layer.
- an LLM judgment layer.

The recommended next step is design-first, then one-rule vertical implementation. This recommendation is bounded by the inspected files and command results listed in this document.
