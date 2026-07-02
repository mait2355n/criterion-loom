# Logical Audit WP8 Decision 2026-06-02

## Purpose

This document records the WP8 decision gate for the first logical-audit slice.

The decision is about whether to extend the logical-audit layer beyond `req.verifiability.acceptance_missing`. It is not a final human acceptance decision for the whole project.

## Audience And Use

This document is for the maintainer and Codex work that may extend the logical-audit layer after WP8.

Use it after reading `docs/logical-audit-integration-plan-2026-06-02.md` and after inspecting real `finding.derivation` / `details.logical_trace` output. It is a change-control record for the next implementation slice, not a user-facing release note.

Representative checks:

```sh
uv run --python 3.13 --project . python -m unittest discover -s tests -v
uv run --python 3.13 --project . semantic-guard evaluate-fixtures --include-passed
uv run --python 3.13 --project . semantic-guard audit-request --text "目的: 速度改善をしたい。"
```

## Entry Conditions

Required entry conditions:

- WP1-WP7 have implementation or documentation artifacts.
- Existing unit tests and fixture evaluation pass.
- Target rule derivation output is readable and scoped.
- Existing `status`, `score`, `missing`, CLI, MCP, and fixture behavior do not regress.
- Derivation wording does not imply natural-language truth, semantic satisfaction, release readiness, safety, or final acceptance.

## Implemented First Slice

The first slice covers only:

- `req.verifiability.acceptance_missing`

It adds:

- extracted facts for input kind, verification language, acceptance criteria, verification method, evidence artifact, and external acceptance route context.
- an executable predicate for the target rule.
- `finding.derivation` on emitted target-rule findings.
- `details.logical_trace` for requirement audits.
- fixture expectation keys for derivation and logical-trace invariants.
- documentation that keeps LLM reviewer output and human final decision outside derivation records.

## Decision

Decision option: `pause`.

Rationale:

- The first slice is useful enough to keep as diagnostic output.
- It is too early to migrate a second rule family before a maintainer reads the public derivation shape in real use.
- The derivation surface is new public output, even though it is additive. Expanding it immediately would make any wording or shape mistake harder to isolate.
- The existing non-goals remain binding: this must not become a formal requirements engine, release gate, security scanner, AI safety engine, or autonomous acceptance system.

## Deferred Candidate Rules

Do not implement these in this WP8 pass:

- `req.verification.method_detail_missing`
- `req.evidence.artifact_missing`
- `plan.validation.owner_missing`
- `diff.implementation.public_contract_change`
- `finish.implementation.behavior_evidence_missing`

Recommended next candidate after review:

- `req.verification.method_detail_missing`

Reason:

- It shares the same request-profile facts as the first slice.
- It can reuse `text.has_verification_method`.
- It is less likely than diff or finish rules to confuse derivation output with release readiness.

## Replanning Outcome

No downstream replan was required for WP3-WP7.

The only plan adjustment is the WP8 expansion decision:

- Keep the first slice.
- Pause second-rule migration.
- Use the first slice in real audits.
- Revisit extension only after the maintainer confirms that `finding.derivation` and `details.logical_trace` are readable and not misleading.

Post-WP8 continuation:

- The maintainer confirmed the derivation surface was readable enough to continue.
- The next implementation slice may use the recommended candidate `req.verification.method_detail_missing`.
- This continuation does not change the WP8 record itself; it records that the pause condition has been satisfied after review.

## Verification Evidence

Representative evidence from the WP3-WP8 pass:

- `python -m unittest discover -s tests -v`: 124 tests OK.
- `semantic-guard evaluate-fixtures --include-passed`: 15 total, 15 passed, pass rate 1.0.
- `python -m compileall src/semantic_guard tests`: OK.
- Representative `audit-request` output for `目的: 速度改善をしたい。` includes `logical-derivation/v1`, `logical-trace/v1`, target rule `req.verifiability.acceptance_missing`, `status=derived`, and derivation scope `rule-and-fact derivation only; not natural-language truth or final acceptance`.
- Detailed requirement regressions keep `status=pass` and `score=1.0` while recording a satisfied logical trace.
- MCP tool tests passed inside the full test suite.

## Human Boundary

`final_human_decision.status` remains outside this document and outside `semantic-guard`.

This WP8 decision does not mean the user has accepted the project. It only records the technical gate result for whether to expand the logical-audit implementation.
