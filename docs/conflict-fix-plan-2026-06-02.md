# Conflict Fix Plan 2026-06-02

## Purpose

This document ranks the conflict findings from `docs/conflict-audit-2026-06-02.md` and turns them into an implementation order.

This is a planning artifact. It does not modify code, severity policy, escalation behavior, or final human decision boundaries.

## Requirement Audit Summary

Initial request audit:

- Status: `warn`.
- Findings: `atomicity`, `priority`.

Refinement:

- Mandatory: rank all C01-C10 conflicts, give reasons, define staged repair plan, dependencies, acceptance criteria, and verification.
- Optional: note any newly discovered helper conflicts.
- Deferred: code changes, profile-specific escalation pressure, statistical precision claims.

Refined request audit:

- Status: `warn`.
- Remaining finding: `atomicity`.

Interpretation:

- The remaining atomicity warning is acceptable for this work package.
- The plan explicitly decomposes the bundled request into ranked deliverables.

Plan audit:

- Status: `pass`.
- No missing fields.

## Ranking Criteria

The ranking uses five criteria. Scores are 0-5.

| Criterion | Meaning |
| --- | --- |
| Responsibility risk | Risk of confusing diagnostic output with acceptance, final judgment, or truth. |
| Unlock value | How much the fix enables later fixes. |
| Calibration value | How much the fix improves test/fixture safety and regression visibility. |
| User friction | How often or sharply the conflict can disturb normal use. |
| Implementation tractability | Higher means the fix can be delivered in a bounded, reviewable slice. |

Execution order is not pure severity. A lower-severity guardrail can come first if it makes later fixes safer.

## Ranked Order

| Rank | Conflict | Score | Disposition | Why This Position |
| ---: | --- | ---: | --- | --- |
| 1 | C08 Rule Catalog Coverage Is Broader Than Fixture Coverage | 22 | Fix first | Fixture and coverage guardrails reduce the risk of every later repair. |
| 2 | C03 `not_applicable` Trace Also Means "Rule Satisfied" | 23 | Fix next | Highest responsibility-boundary risk; needs guardrails from rank 1 before changing output semantics. |
| 3 | C09 Parallel Diagnostic Channels Are Not Unified | 21 | Fix after C03 | Depends on a clearer non-emitted-rule taxonomy; gives escalation and readers one diagnostic shape. |
| 4 | C05 Trace Report Mixes Segment Audit Status With Trace-Specific Status | 19 | Fix after diagnostic cleanup | High user-facing confusion; should reuse the diagnostic/status split from rank 3. |
| 5 | C04 Severity Profiles Change Severity And Status But Not Score | 18 | Fix after status split | Trust issue in public output; score semantics should be clarified before profile pressure grows. |
| 6 | C01 Broad-Scope Lexical Trigger Is Too Crude | 17 | Fix after fixtures | Common Japanese false positive, but bounded once fixtures exist. |
| 7 | C07 `audit-diff` Evidence Boundary Is Too Generic For Docs-Only Text | 16 | Fix after fixtures | Frequent document-work false positive; lower responsibility risk than C03-C05. |
| 8 | C02 Composite Requirement Warning Needs Work-Package Escape Hatch | 15 | Fix later | Useful warning, but too blunt for bounded work packages. |
| 9 | C06 Document Audit Can Pass While Listing Unsupported Weak Claims | 13 | Accept then clarify | Mostly acceptable by specification; improve summary once diagnostic shape is clearer. |
| 10 | C10 Profile-Specific Escalation Pressure Remains Unimplemented | 14 | Keep deferred | The raw score is not lowest, but prior human direction and authority-drift risk keep it last. |

## Score Detail

| Conflict | Responsibility | Unlock | Calibration | Friction | Tractability | Total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| C01 | 2 | 2 | 4 | 5 | 4 | 17 |
| C02 | 2 | 2 | 3 | 4 | 4 | 15 |
| C03 | 5 | 5 | 4 | 5 | 4 | 23 |
| C04 | 4 | 3 | 3 | 4 | 4 | 18 |
| C05 | 4 | 4 | 3 | 5 | 3 | 19 |
| C06 | 2 | 2 | 3 | 3 | 3 | 13 |
| C07 | 2 | 2 | 4 | 5 | 4 | 16 |
| C08 | 3 | 5 | 5 | 4 | 5 | 22 |
| C09 | 5 | 5 | 4 | 4 | 3 | 21 |
| C10 | 5 | 2 | 2 | 2 | 1 | 14 |

Note: C10's raw responsibility score is high, but it is intentionally held back. The user already chose not to prioritize profile-specific escalation pressure, and implementing it early would amplify unresolved diagnostic ambiguity.

## Implementation Stages

### Stage 1: Fixture And Coverage Guardrails

Target conflicts:

- C08 first.
- Fixture pieces for C01, C03, C04, C05, C07, and C02.

Files likely touched:

- `tests/fixtures/**`
- `tests/test_evaluation.py`
- `src/semantic_guard/evaluation.py`
- `docs/fixture-record-design.md`
- `docs/dogfood-readme-2026-06-01.md`

Implementation shape:

- Add conflict-oriented fixture cases:
  - bounded `全体を確認する` plan.
  - satisfied non-goal/change-control rule versus true not-applicable rule.
  - docs-only evidence-boundary diff.
  - profile severity/status/score behavior.
  - trace report with strong links but embedded audit warning.
  - bounded work-package request with multiple deliverables.
- Add a catalog coverage summary listing rule IDs not hit by fixture expectations.
- Keep metrics explicitly local-fixture calibration, not statistical precision.

Acceptance criteria:

- `evaluate-fixtures` reports fixture pass/fail plus unhit rule IDs.
- Existing 12 fixtures still pass.
- New conflict fixtures pass.
- README or fixture docs state the coverage map is local calibration only.

Verification:

```sh
uv run --python 3.13 --project . python -m unittest discover -s tests
uv run --python 3.13 --project . semantic-guard evaluate-fixtures
```

### Stage 2: Non-Emitted Rule Taxonomy

Target conflicts:

- C03 primarily.
- C09 partially.

Files likely touched:

- `src/semantic_guard/core.py`
- `src/semantic_guard/models.py` if a public typed shape is added.
- `tests/test_core.py`
- `README.md`
- `docs/ambiguity-confidence-design.md`
- `docs/dogfood-readme-2026-06-01.md`

Implementation shape:

- Keep `suppressed_rules` only as compatibility or rename only with a migration note.
- Add clearer diagnostic entries such as `details.non_emitted_rules`.
- Include:
  - `rule_id`
  - `phase`
  - `emission_status`: `satisfied`, `not_applicable`, `deferred`, `context_supplied`, `document_only`
  - `reason`
  - `source`
  - `evidence`
  - optional `confidence`
- Keep `match_status: "not_applicable"` only when a real counter-condition makes the rule inapplicable.
- Mark present non-goals/change-control as `satisfied`, not `not_applicable`.

Acceptance criteria:

- Request with `対象外` records `req.scope.non_goals_missing` as `satisfied`.
- A true out-of-phase or explicitly scoped-out rule can still record `not_applicable`.
- `status`, `score`, `missing`, and human decision boundaries remain unchanged.
- Old `suppressed_rules` behavior is either preserved compatibly or clearly migrated.

Verification:

```sh
uv run --python 3.13 --project . python -m unittest tests.test_core
uv run --python 3.13 --project . semantic-guard audit-request --text '...対象外...'
uv run --python 3.13 --project . semantic-guard audit-plan --text '...変更統制...'
```

### Stage 3: Diagnostic Envelope

Target conflicts:

- C09 primarily.
- Supports C05, C06, C10 later.

Files likely touched:

- `src/semantic_guard/core.py`
- `src/semantic_guard/escalation.py`
- `src/semantic_guard/traceability.py`
- `README.md`
- `docs/ambiguity-confidence-design.md`
- `tests/test_escalation.py`
- `tests/test_traceability.py`

Implementation shape:

- Add `details.diagnostics` as a normalized summary.
- Keep current finding fields for compatibility.
- Separate:
  - emitted findings.
  - non-emitted rule diagnostics.
  - field match diagnostics.
  - trace diagnostics.
  - document claim diagnostics.
- Let escalation read `details.diagnostics` where possible without removing old logic yet.

Acceptance criteria:

- Existing outputs still include current fields.
- `details.diagnostics` explains which diagnostic channels exist and their counts.
- Escalation still triggers for existing tested cases.

Verification:

```sh
uv run --python 3.13 --project . python -m unittest tests.test_escalation tests.test_traceability tests.test_core
```

### Stage 4: Trace Report Status Split

Target conflicts:

- C05.

Files likely touched:

- `src/semantic_guard/traceability.py`
- `tests/test_traceability.py`
- `README.md`
- `docs/dogfood-readme-2026-06-01.md`

Implementation shape:

- Add:
  - `summary.audit_status`
  - `summary.trace_status`
  - `summary.vocabulary_status`
  - `summary.aggregate_status_reason`
- Keep top-level `status` as aggregate.
- Explain when top-level `warn` comes from embedded audit rather than trace gaps.

Acceptance criteria:

- A trace with strong links and an embedded request warning shows `trace_status: "pass"` and `audit_status: "warn"`.
- Existing trace-report tests still pass after expected field additions.

Verification:

```sh
uv run --python 3.13 --project . python -m unittest tests.test_traceability
uv run --python 3.13 --project . semantic-guard trace-report < sample.json
```

### Stage 5: Score And Profile Semantics

Target conflicts:

- C04.

Files likely touched:

- `src/semantic_guard/severity_profiles.py`
- `tests/test_severity_profiles.py`
- `README.md`
- `docs/dogfood-readme-2026-06-01.md`

Implementation options:

- Option A: document `score` as base score and add no new numeric score.
- Option B: add `details.severity_profile.profiled_score`.

Preferred option:

- Option B, if implemented carefully.

Acceptance criteria:

- Profiled outputs clearly show base score versus profiled score, or explicitly state only base score exists.
- Release/safety profile examples are not misread as final approval or rejection.

Verification:

```sh
uv run --python 3.13 --project . python -m unittest tests.test_severity_profiles tests.test_mcp_tools
```

### Stage 6: Lexical False-Positive Refinements

Target conflicts:

- C01.
- C07.
- C02.

Files likely touched:

- `src/semantic_guard/core.py`
- `src/semantic_guard/matching.py` if shared candidate logic is useful.
- `tests/test_core.py`
- conflict fixtures from Stage 1.

Implementation shape:

- C01: require broad-scope term plus missing bounded controls, or downgrade to `possible false positive`.
- C07: detect docs-only evidence-boundary language and classify as `document_only_boundary`.
- C02: distinguish product requirement atomicity from bounded work-package bundling.

Acceptance criteria:

- Bounded `全体を確認する` plan does not receive a major scope warning.
- Docs-only evidence mapping does not look like semantic evidence mutation.
- Bounded work package can warn less aggressively than bundled product requirements.
- Existing true-positive tests still pass.

Verification:

```sh
uv run --python 3.13 --project . python -m unittest tests.test_core tests.test_fixtures
uv run --python 3.13 --project . semantic-guard evaluate-fixtures
```

### Stage 7: Document Claim Summary

Target conflicts:

- C06.

Files likely touched:

- `src/semantic_guard/core.py`
- `tests/test_core.py`
- `README.md`

Implementation shape:

- Add `details.document_claim_summary`.
- Count `supported`, `limited`, `unsupported`, and strong unsupported claims.
- Warn only for strong unscoped unsupported claims.

Acceptance criteria:

- Document audits can pass while still exposing weak historical unsupported claims in summary.
- Strong current unsupported claims still warn.

Verification:

```sh
uv run --python 3.13 --project . python -m unittest tests.test_core
```

### Stage 8: Profile-Specific Escalation Pressure

Target conflicts:

- C10.

Status:

- Deferred.

Entry condition:

- Stages 2-5 have been delivered and verified.
- Diagnostic envelope is stable.
- Human final decision boundary is still documented and tested.

Implementation constraint:

- This must increase reviewer-routing pressure only.
- It must not approve, reject, accept, or replace `final_human_decision`.

## Recommended Immediate Next Step

Start with Stage 1.

Reason:

- Stage 1 does not require public output semantics changes.
- It gives regression protection before touching C03/C09.
- It also turns the ranking itself into executable calibration material.

After Stage 1 passes, move to Stage 2.

## Residual Risk

- The scores are engineering prioritization, not statistical measurements.
- Implementation effort may change after code inspection.
- Some fixes may be easier to combine, but combining should only happen when tests and public output contracts remain clear.
- C10 remains intentionally deferred despite a high responsibility score.
