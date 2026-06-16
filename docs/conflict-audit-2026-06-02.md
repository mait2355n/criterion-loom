# Conflict Audit 2026-06-02

## Purpose

This document audits `semantic-guard` for internal rule and output conflicts after the requirements, planning, implementation, traceability, severity-profile, not-applicable, vocabulary-negotiation, and reviewer-boundary layers have accumulated.

The goal is not to fix the code in this pass. The goal is to expose collisions, classify them, and give a follow-up implementation plan.

## Current State

Observed code and artifact surface:

- `src/semantic_guard/core.py`: 3050 lines.
- Rule catalog: 36 rules.
- Rule phases: `audit_request` 15, `audit_plan` 11, `audit_diff` 7, `finish_check` 3.
- Rule disciplines from catalog labels only, not a secure-behavior claim: requirements engineering 15, project planning 11, software engineering 6, secure development 2, semantic preservation 2.
- Tests: 105 unit tests passed during this audit.
- Fixture evaluation: 12 fixtures passed.
- The repository directory itself is not a Git repository, so this audit used file inspection, commands, and document references rather than `git diff`.

Important existing boundaries:

- LLM reviewer output is intermediate material only.
- `final_human_decision.status` remains `pending` until a human decides.
- Severity profiles change warning pressure, not truth.
- Trace tags and vocabulary suggestions are diagnostic indices, not semantic proof.
- Domain-specific vocabulary is not promoted automatically unless a `vocabulary_profile` accepts it.

## Requirement Audit

### Input Intent

User intent:

- Inspect the main `semantic-guard` layers once.
- Find conflict points.
- Before doing that, perform requirement and plan audits in detail.
- Watch for excess, shortage, ambiguity, and responsibility-boundary drift.

### Initial Target Understanding

Initial `understand-target` result:

- Status: `warn`.
- Missing support fields: `current_state`, `domain_terms`, `assumptions`.

Correction:

- Added current state: accumulated audit phases, trace report, reviewer routing, severity profiles, acceptance bundle, not-applicable trace, vocabulary decisions.
- Added domain terms: `finding`, `missing`, `details`, `signals`, `suppressed_rules`, `match_status`, `confidence`, `warning_class`, `escalation`, `trace_tags`, `vocabulary_decisions`, `final_human_decision`, `rule catalog`, `phase`, `profile`.
- Added assumption: this pass documents conflicts and does not primarily change code.

Refined `understand-target` result:

- Status: `pass`.
- No missing fields.

### Initial Request Audit

Initial `audit-request` result:

- Status: `warn`.
- Finding: `atomicity`.
- Reason: the request bundles inspection, classification, prioritization, implementation planning, and verification.

Interpretation:

- This is a real structural warning, not a blocker.
- The user's request is naturally a work package, not a single atomic product requirement.
- The correct response is not to reject the request, but to decompose the deliverable.

Derived atomic requirements:

- R1: Produce `docs/conflict-audit-2026-06-02.md`.
- R2: Include requirement-audit and plan-audit results.
- R3: Inventory rules, core phases, helper layers, docs, and tests.
- R4: Identify conflict points with evidence and impact.
- R5: Classify each point as `fix now`, `fix later`, or `acceptable by specification`.
- R6: Include excess and shortage analysis.
- R7: Include follow-up implementation plan.
- R8: Preserve the human final decision boundary.
- R9: Verify the resulting document with document audit and finish-check.

Acceptance criteria:

- The document names the inspected surface.
- Each conflict has evidence, risk, and recommended disposition.
- It separates collisions from acceptable overlaps.
- It does not turn this pass into broad code modification.
- It records remaining risks and follow-up order.

## Plan Audit

Initial `audit-plan` result:

- Status: `warn`.
- Finding: scope over-expansion.
- Trigger: the Japanese term `全体`.

Interpretation:

- This revealed a real lexical fragility in `audit-plan`.
- The intended plan was bounded inspection of major layers, not a full rewrite.
- The plan was rephrased from `全体` to `主要層`.

Refined `audit-plan` result:

- Status: `pass`.
- No missing fields.

Final working plan:

- Inspect rule catalog.
- Inspect `core.py` phase responsibilities.
- Inspect matching, escalation, traceability, severity profiles, LLM review, and acceptance bundle.
- Inspect README, design docs, dogfood note, and tests.
- Run representative CLI commands.
- Write this document.
- Audit this document as `--kind document`.
- Run finish-check.

Non-goals:

- No broad implementation changes in this pass.
- No profile-specific escalation pressure implementation.
- No NLP dependency.
- No final human decision automation.
- No statistical precision or recall claim beyond local fixture labels.

## Inventory

### Rule Catalog

Rule count by phase:

- `audit_request`: 15.
- `audit_plan`: 11.
- `audit_diff`: 7.
- `finish_check`: 3.

Rule count by discipline:

- `requirements_engineering`: 15.
- `project_planning`: 11.
- `software_engineering`: 6.
- `secure_development`: 2.
- `semantic_preservation`: 2.

Observations:

- Request and plan phases are now dense enough that field-level, profile-level, and trace-level interactions matter.
- `audit_diff` has fewer rules, but it has broad lexical surfaces: security, implementation signals, semantic boundaries, and documentation obligation.
- Finish rules are compact, but they carry high responsibility because they mediate completion claims.

### Core Phase Responsibilities

Current phase boundaries:

- `understand_target`: problem framing and missing context.
- `audit_request`: requirement quality, achievement profile, statement structure, non-goals, unknowns.
- `audit_plan`: planning fields, WBS-like decomposition, validation owner, control, baseline, change control, decision gate.
- `audit_diff`: security signal, implementation signals, test obligation, semantic boundaries, complexity, documentation obligation.
- `finish_check`: evidence, acceptance mapping, security evidence, representative public behavior, residual risk.

Current cross-cutting details:

- `warning_class_counts`.
- `match_status_counts`.
- `confidence_counts`.
- `ambiguity_reason_counts`.
- `suppressed_rules`.
- `suppressed_rule_counts`.
- Optional `severity_profile`.

### Helper Layers

Observed helper layers:

- `matching.py`: deterministic field match diagnostics.
- `severity_profiles.py`: adjusts finding severities and recalculates status.
- `escalation.py`: routes undecidable or high-risk residue to `candidate_gap_reviewer`.
- `traceability.py`: runs segment audits and adds vocabulary links, normalized trace tags, and vocabulary decisions.
- `llm_review.py`: builds bounded reviewer prompts and validates reviewer schema.
- `acceptance_review.py`: builds and validates final human review bundles.
- `evaluation.py`: local fixture calibration metrics.

## Conflict Findings

### C01: Broad-Scope Lexical Trigger Is Too Crude

Evidence:

- `audit-plan` warned on a bounded document-inspection plan because the objective contained `全体`.

Conflict:

- The rule intends to catch unbounded rewrite/refactor scope.
- The implementation currently treats `全体` as enough evidence even when the plan has explicit non-goals, deliverables, rollback, and change control.

Impact:

- Legitimate audit or survey tasks can be marked as overbroad.
- This is especially likely when Japanese prose naturally says "全体を確認する".

Disposition:

- Fix later.

Recommended implementation:

- Change broad-scope warning from single-token detection to compound detection.
- Require broad token plus missing decomposition/control, or mark as `possible false positive` when bounded artifacts and non-goals are present.
- Add fixture for `全体を確認する` with bounded deliverables.

### C02: Composite Requirement Warning Is Useful But Needs Work-Package Escape Hatch

Evidence:

- The user's request produced an `atomicity` warning even though the task is naturally a multi-step conflict audit.

Conflict:

- Requirement atomicity is useful for product requirements.
- Work-package requests legitimately bundle audit, classification, documentation, and verification.

Impact:

- The tool may nag correctly but too bluntly when the input is a bounded work order.

Disposition:

- Fix later.

Recommended implementation:

- Keep the warning for bundled product requirements.
- Downgrade when the text includes explicit deliverable, work breakdown, non-goals, verification, and acceptance route.
- Consider category split: `atomicity` for product requirements, `work_package_bundle` for implementation work.

### C03: `not_applicable` Trace Currently Also Means "Rule Satisfied"

Evidence:

- `audit-request` records `req.scope.non_goals_missing` as `match_status: "not_applicable"` when `対象外` is present.
- `audit-plan` records `plan.control.change_control_missing` as `not_applicable` when change control is present.

Conflict:

- `not_applicable` is documented as "rule does not apply due to explicit scope, negation, or phase".
- A missing-field rule whose field is present is arguably "satisfied" rather than "not applicable".

Impact:

- Suppression traces can become semantically ambiguous.
- A reader may confuse "the rule was scoped out" with "the rule was satisfied".

Disposition:

- Fix now or next.

Recommended implementation:

- Replace or extend `suppressed_rules` with a clearer taxonomy:
  - `non_emitted_rules`.
  - `reason_kind`: `satisfied`, `not_applicable`, `deferred`, `document_only`, `context_supplied`.
  - Keep `match_status: "not_applicable"` only for true counter-conditions.
- Preserve compatibility by keeping `suppressed_rules` for one release cycle if needed.

### C04: Severity Profiles Change Severity And Status But Not Score

Evidence:

- `severity_profiles.py` adjusts finding severity and recalculates `status`.
- It does not recalculate `score`.

Conflict:

- `score` remains severity-derived from the base audit.
- Profiled output can contain higher severity while retaining the old score.

Impact:

- Users can see a release or safety profile upgrade without a corresponding score shift.
- This is not wrong if documented as "base score", but it is currently easy to misread.

Disposition:

- Fix later.

Recommended implementation:

- Either document `score` as base-audit score after profiles, or add `details.severity_profile.profiled_score`.
- Avoid silently changing score semantics without an output contract note.

### C05: Trace Report Mixes Segment Audit Status With Trace-Specific Status

Evidence:

- `trace-report` runs `audit_request`, `audit_plan`, `audit_diff`, and `finish_check` internally.
- A representative trace report had strong links and no trace gaps, but overall status was `warn` because the embedded request audit warned.

Conflict:

- Trace strength can be good while an embedded audit warns for requirement quality.
- The single top-level `status` merges audit readiness and trace linkage.

Impact:

- A user may think traceability is weak when the actual issue is request wording.
- The trace-specific finding can be obscured.

Disposition:

- Fix later.

Recommended implementation:

- Add separate fields:
  - `summary.audit_status`.
  - `summary.trace_status`.
  - `summary.vocabulary_status`.
- Keep top-level `status` as aggregate, but make the reason explicit.

### C06: Document Audit Can Pass While Listing Unsupported Weak Claims

Evidence:

- Document audit output can include `claim_triples` with `support: "unsupported"` while status remains `pass`.
- This appeared in the dogfood document audit for historical or early-finding statements.

Conflict:

- The tool exposes unsupported claims in details but does not necessarily turn them into findings.
- This is acceptable for weak historical notes, but the distinction is not obvious.

Impact:

- Users can overlook unsupported claims because `status` is `pass`.

Disposition:

- Acceptable by specification for now, but document more clearly.

Recommended implementation:

- Add `details.document_claim_summary` with counts by support level.
- Optionally warn only when unsupported claims are strong, current, and unscoped.

### C07: `audit-diff` Meaning Boundary Warnings Are Too Generic For Documentation-Only Evidence Text

Evidence:

- `audit-diff` warned on `Changed docs: documented evidence boundaries and acceptance mapping.`
- The warning was `meaning` boundary `evidence`.

Conflict:

- The semantic-boundary check correctly sees evidence/acceptance terms.
- In a documentation-only summary, this often means "we documented evidence" rather than "we changed evidence semantics".

Impact:

- Useful document updates can produce a generic meaning warning.

Disposition:

- Fix later.

Recommended implementation:

- If changed files are docs-only, or the diff text clearly says `Changed docs`, downgrade to `generic caution` with `possible false positive`, or add a `document_only_boundary` reason.
- Keep warning for source changes touching evidence, acceptance, identity, permission, persistence, or source-of-truth semantics.

### C08: Rule Catalog Coverage Is Broader Than Fixture Coverage

Evidence:

- Rule catalog has 36 rules.
- Fixture evaluation currently covers 12 fixtures and reports rule hits for a subset.

Conflict:

- The catalog looks systematic.
- Local fixture coverage is still sparse relative to the rule count and cross-phase interactions.

Impact:

- New rules can regress without fixture-level detection.
- False-positive fixes can overfit to unit tests rather than calibration cases.

Disposition:

- Fix now or next.

Recommended implementation:

- Add conflict-oriented fixtures:
  - bounded "全体確認" plan.
  - not-applicable versus satisfied suppression.
  - docs-only evidence boundary.
  - severity-profile score/status behavior.
  - trace report with strong links but embedded audit warn.
- Track rule IDs not exercised by fixtures.

### C09: `warning_class`, `match_status`, And `suppressed_rules` Are Parallel But Not Unified

Evidence:

- Findings can carry `warning_class`, `match_status`, `confidence`, and `ambiguity_reasons`.
- Suppression traces carry `match_status` and `confidence`, but are not findings.
- Counts are separated as finding counts and suppressed rule counts.

Conflict:

- The output model has three overlapping explanatory channels:
  - finding classification.
  - matching diagnostics.
  - rule non-emission traces.

Impact:

- The model is expressive but becoming hard to read.
- Future escalation logic may not know whether to inspect findings, details, or both.

Disposition:

- Fix later.

Recommended implementation:

- Define a public "diagnostic envelope" contract.
- Separate:
  - emitted findings.
  - non-emitted rule diagnostics.
  - candidate field diagnostics.
  - trace diagnostics.
- Then let escalation read from a normalized diagnostic summary.

### C10: Profile-Specific Escalation Pressure Remains Unimplemented

Evidence:

- Docs say profile-specific escalation pressure is not implemented.
- Severity profiles exist and can alter finding severity and status.
- Escalation reads deterministic audit findings and reasons, not a profile-policy table.

Conflict:

- Profiles already change warning pressure.
- Escalation still has mostly profile-agnostic routing.

Impact:

- Release and safety profiles may feel stricter in status but not always stricter in reviewer escalation.

Disposition:

- Accept for now because the user explicitly chose not to prioritize this yet.

Recommended implementation:

- Do not implement until the responsibility model is stable.
- When implemented, keep it as "review pressure", not final acceptance.

## Excess Analysis

Likely excess:

- Single-token broad-scope detection.
- Generic evidence-boundary warning on documentation summaries.
- Requirement atomicity warning for bounded work packages.
- Embedded audit warnings dominating trace-report status.
- Multiple details channels that all explain "why" but with different shapes.

## Shortage Analysis

Likely shortage:

- No formal conflict matrix across phases.
- No fixture coverage map for all 36 rules.
- No explicit taxonomy for non-emitted rules.
- No profiled score or explicit base-score statement.
- No document-claim summary counts.
- No trace-specific status separated from embedded audit status.

## Follow-Up Implementation Plan

### Fix Now Or Next

1. Add non-emitted rule taxonomy.
   - Target: `core.py`, README, ambiguity design doc, tests.
   - Acceptance: `satisfied` and `not_applicable` are distinguishable.

2. Add conflict fixtures.
   - Target: `tests/fixtures` and evaluation labels.
   - Acceptance: at least five conflict cases are fixture-calibrated.

3. Add fixture rule-coverage report.
   - Target: `evaluation.py`.
   - Acceptance: output lists catalog rules not hit by fixture labels.

### Fix Later

4. Refine broad-scope detection.
   - Require broad token plus missing control, or downgrade bounded cases.

5. Refine documentation-only evidence boundary.
   - Add doc-only false-positive guard.

6. Split trace report statuses.
   - Add audit, trace, and vocabulary status in summary.

7. Clarify severity profile score behavior.
   - Document score as base score or add profiled score.

### Accept For Now

8. Keep profile-specific escalation pressure unimplemented.
   - Reason: responsibility boundary is still more important than automatic escalation force.

9. Keep unsupported weak document claims as details-only.
   - Reason: not every historical or early-finding claim should warn.

## Verification Commands

Commands run during this audit:

```sh
uv run --python 3.13 --project . semantic-guard understand-target --text ...
uv run --python 3.13 --project . semantic-guard audit-request --text ...
uv run --python 3.13 --project . semantic-guard audit-plan --text ...
uv run --python 3.13 --project . semantic-guard trace-report
uv run --python 3.13 --project . semantic-guard audit-diff --text ...
uv run --python 3.13 --project . python -m unittest discover -s tests
uv run --python 3.13 --project . semantic-guard evaluate-fixtures
```

Observed results:

- Refined target understanding: `pass`.
- Refined plan audit: `pass`.
- Representative broad-scope plan with `全体`: `warn`.
- Representative trace report: `warn` because embedded request audit warned even though trace links were strong and gaps were empty.
- Representative docs evidence diff: `warn` on semantic boundary `evidence`.
- Unit tests: 105 tests OK.
- Fixture evaluation: 12/12 passed.

## Residual Risk

- This audit is deterministic and file-based. It does not prove the rule system is complete.
- It identifies likely conflict points but does not measure precision or recall.
- Some collisions are design tradeoffs rather than bugs.
- Human decision remains required before implementing high-impact changes.
