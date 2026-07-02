# Logical Audit Legacy Inheritance Audit 2026-06-02

## Purpose

This document audits whether `docs/logical-audit-integration-plan-2026-06-02.md` degrades the prior `semantic-guard` documentation contract.

The target risk is not only file overwrite. The larger risk is failed inheritance: a new logical-audit plan can preserve the old files while silently dropping old boundaries, diagnostic meanings, escalation limits, or human-decision constraints.

## Audience And Use

This document is for the maintainer and Codex work that will implement logical-audit features after the current planning pass.

Use it before creating `docs/logical-audit-design.md` and before changing logical-audit code. The expected use is to treat the inheritance requirements here as constraints on WP1-WP7 of the integration plan.

Representative commands:

```sh
diff -qr backup-snapshot/docs-2026-06-02T12-22-15+0900/docs docs
uv run --python 3.13 --project . semantic-guard audit-request --kind document --file docs/logical-audit-inheritance-audit-2026-06-02.md
uv run --python 3.13 --project . semantic-guard audit-plan --file docs/logical-audit-integration-plan-2026-06-02.md
uv run --python 3.13 --project . semantic-guard evaluate-fixtures
```

## Scope

Audited old baseline:

- `backup-snapshot/docs-2026-06-02T12-22-15+0900/README.md`
- `backup-snapshot/docs-2026-06-02T12-22-15+0900/docs/`
- `backup-snapshot/docs-2026-06-02T12-22-15+0900/schemas/`

Audited current material:

- `README.md`
- `docs/`
- `schemas/`
- `docs/logical-audit-integration-plan-2026-06-02.md`

Not in scope:

- claiming that logical audit is implemented.
- proving runtime correctness.
- proving natural-language truth.
- deciding human acceptance.

## Mechanical Baseline

Backup verification:

- `shasum -a 256 -c MANIFEST.sha256` passed for every backed-up README, docs, and schema file.

Directory comparison:

- `diff -qr backup-snapshot/docs-2026-06-02T12-22-15+0900/README.md README.md`: no difference.
- `diff -qr backup-snapshot/docs-2026-06-02T12-22-15+0900/schemas schemas`: no difference.
- At the start of this inheritance audit, `diff -qr backup-snapshot/docs-2026-06-02T12-22-15+0900/docs docs` showed only `docs/logical-audit-integration-plan-2026-06-02.md` as an added current doc.
- After this inheritance audit, `docs/logical-audit-inheritance-audit-2026-06-02.md` is also an intentional added current doc.

Mechanical conclusion:

- No old README, docs, or schema file was overwritten in this planning pass.
- The current added docs are the logical-audit integration plan and this inheritance audit document.

Limitation:

- This checks file-level preservation only. It does not prove that the new plan inherits every old boundary.

## Legacy Contract Matrix

| Legacy contract | Old source | Current inheritance result |
| --- | --- | --- |
| Local deterministic audit layer, not an authoritative requirements, safety, or release gate. | `README.md` Status and Limitations | Preserved by unchanged README and reinforced in the integration plan public-positioning boundary. |
| Use the tool only where meaning, intent, scope, or verification can be harmed. Avoid fake rigor for trivial edits. | `README.md` When To Use | Mechanically preserved by unchanged README. WP1 design should avoid making derivation output a default ritual for trivial work. |
| Stable phase output shape: `phase`, `status`, `score`, `findings`, `missing`, `next_actions`, `details`. | `README.md` Output Shape | Preserved by integration-plan Output Compatibility. |
| New diagnostic fields must be optional and must not change the meaning of `status` or `score`. | `README.md` Output Shape and `docs/ambiguity-confidence-design.md` | Preserved. The plan adds optional `finding.derivation` and `details.logical_trace` and keeps derivation out of score semantics. |
| `nearest_candidates`, `candidate_matches`, match diagnostics, non-emitted rules, and trace diagnostics are review material, not proof or acceptance. | `README.md` Output Shape, Limitations, and `docs/ambiguity-confidence-design.md` | Partly present before this audit. The plan now explicitly preserves trace and vocabulary suggestions as diagnostics, not accepted facts. |
| `trace-report` cannot prove semantic satisfaction. `suggested_tags` are not accepted tags. | `README.md` Limitations and trace-report contract | Preserved after this audit by the new Trace And Vocabulary Boundary. |
| Fixture evaluation is local calibration and regression detection, not statistical precision or recall. | `README.md` fixture description and `docs/fixture-record-design.md` | Preserved after this audit by explicit WP6 criteria, including continued `rule_catalog_coverage.unhit_rule_ids`. |
| Rule catalog records engineering rationale, applies-when, reverse conditions, evidence, severity, finding, and remediation. It is not a full reasoning engine by itself. | `docs/rule-model.md` | Preserved by WP1-WP4, which limit the first executable predicate to one rule and keep counterconditions visible. |
| LLM reviewer is an isolated intermediate reviewer. It cannot approve, reject, change implementation, add rules, or decide final acceptance. | `README.md`, `docs/llm-reviewer.md` | Preserved by LLM Boundary. |
| `review-if-needed` is an uncertainty router and dry-run by default. | `README.md` Escalation and `docs/llm-reviewer.md` | Under-specified before this audit. The plan now has an Escalation Boundary. |
| `acceptance_review_bundle` is final human-review material. `final_human_decision.status` stays `pending` until a person decides. | `README.md` and `docs/acceptance-review-bundle.md` | Preserved, and now extended with strict-validation inheritance for deterministic audit material, execution evidence, and human review points. |
| Public positioning excludes security scanner, release gate, MCP competitor, requirements-engineering replacement, AI safety engine, and autonomous acceptance system. | `docs/public-comparison-2026-06-02.md` | Under-specified before this audit. The plan now has a Public Positioning Boundary and WP7 required statements. |

## Findings

### F01: No Mechanical Degradation Found

Severity: pass.

Evidence:

- The backup manifest verified successfully.
- Current `README.md` and `schemas/` match the backup.
- Current `docs/` differs from the backup only by added logical-audit planning and inheritance-audit documents.

Meaning:

- The old documentation corpus is still present.
- No old schema was changed.

Residual risk:

- This does not guard against future code changes or future documentation edits.

### F02: Core Trust Model Is Preserved After Plan Patch

Severity: pass with implementation watch.

The old trust model is:

- deterministic checks are useful but limited.
- diagnostics are evidence for review, not acceptance.
- fixture results are local calibration, not statistics.
- LLM review is supplement material.
- human final acceptance remains outside the tool.

The integration plan now preserves this model in non-goals, output compatibility, derivation scope, LLM boundary, human-decision boundary, escalation boundary, trace boundary, and public-positioning boundary.

Residual risk:

- Implementation can still violate the plan if accepted facts, derivation records, or reviewer output are wired into `status`, `score`, or final acceptance without explicit review.

### G01: Escalation Boundary Was Too Implicit

Severity: gap patched.

Before this audit, the plan said LLM output must not create accepted facts or decisions, but it did not explicitly preserve the old `review-if-needed` behavior:

- dry-run by default.
- only undecidable residue is routed outward.
- reviewer result is supplement material.

Patch made:

- Added `Escalation Boundary`.
- Added WP7 statement requiring `review-if-needed` to remain dry-run by default and limited to undecidable residue.

### G02: Trace Vocabulary Could Have Been Mistaken For Logical Facts

Severity: gap patched.

The logical-audit plan introduces facts and derivations. The old trace model already had `suggested_tags`, unresolved terms, weak vocabulary links, and accepted vocabulary decisions. Without an explicit boundary, a future implementation could accidentally treat suggested vocabulary as accepted facts.

Patch made:

- Added `Trace And Vocabulary Boundary`.
- Added WP7 statement that trace vocabulary suggestions are diagnostics, not accepted facts.

### G03: Public Positioning Was Not Fully Inherited

Severity: gap patched.

The old public comparison says `semantic-guard` must not be sold as a security scanner, release gate, MCP competitor, requirements-engineering replacement, AI safety engine, or autonomous acceptance system.

The initial logical-audit plan excluded some of these by implication, but not all of them explicitly.

Patch made:

- Added `Public Positioning Boundary`.
- Added WP7 statement preserving the old excluded claims.

### G04: Fixture Coverage Reporting Needed Explicit Preservation

Severity: gap patched.

The old fixture design treats fixture results as local regression and calibration data. `rule_catalog_coverage.unhit_rule_ids` is important because it shows which rules are not yet exercised by labels.

The initial plan said evaluation must stay local and non-statistical, but it did not name the unhit-rule reporting.

Patch made:

- Added WP6 acceptance criterion requiring continued `rule_catalog_coverage.unhit_rule_ids`.

### G05: Acceptance Bundle Strictness Needed Explicit Preservation

Severity: gap patched.

The old acceptance bundle design requires final human review material to include deterministic audit material, execution evidence, and human review points. The initial plan preserved `final_human_decision.pending`, but not this strict evidence requirement.

Patch made:

- Added strict acceptance-bundle validation wording under Human Decision Boundary.

## Regression Watchpoints For WP1-WP7

Treat these as stop conditions during implementation:

- Any derivation output changes top-level `score` into derivation strength.
- Any derivation output appears for unrelated rules before the first target rule is stable.
- Any LLM reviewer output becomes an accepted fact without deterministic evidence or explicit human decision.
- Any `review-if-needed` path executes by default.
- Any trace suggested tag or unresolved term is promoted into a fact by implication.
- Any fixture metric is described as statistical precision, recall, or general performance.
- Any README wording presents logical audit as a formal proof system, release gate, security scanner, or autonomous acceptance system.
- Any acceptance bundle fills `final_human_decision.status` with `accept`, `request_revision`, or `defer` without a person deciding.

## Verdict

The current logical-audit plan is not a documented downgrade of the old system after the patches made during this audit.

The old files are mechanically preserved, and the new plan now explicitly carries the old trust boundaries forward. The remaining risk is implementation drift: the next design and code passes must keep derivation output scoped to extracted facts, executable predicates, explicit counterconditions, and unresolved unknowns.

This verdict is limited to documentation and planning inheritance. It does not claim that the logical-audit implementation exists or that future code changes are regression-free.
