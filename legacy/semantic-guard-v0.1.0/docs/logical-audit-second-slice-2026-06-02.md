# Logical Audit Second Slice 2026-06-02

## Purpose

This document records the post-WP8 continuation slice for the logical-audit layer.

The slice extends executable derivation output from one request-verification rule to two request-verification rules. It does not expand the whole catalog.

## Usage

Read this document after `docs/logical-audit-wp8-decision-2026-06-02.md` when deciding whether the logical-audit layer should expand beyond the second request-verification rule.

Use it as a change-control note, not as a user-facing release note or final acceptance record.

## Trigger

WP8 paused second-rule migration until the maintainer confirmed that `finding.derivation` and `details.logical_trace` were readable and not misleading.

The maintainer confirmed the naming and scope after `proof` was renamed to `derivation` and overclaiming wording was removed. That satisfies the pause condition for one narrow continuation slice.

## Implemented Scope

Implemented rule:

- `req.verification.method_detail_missing`

Existing retained rule:

- `req.verifiability.acceptance_missing`

Deferred rules:

- `req.evidence.artifact_missing`
- `plan.validation.owner_missing`
- `diff.implementation.public_contract_change`
- `finish.implementation.behavior_evidence_missing`

## Boundary

The second slice remains a rule-and-fact derivation only.

It must not:

- prove natural-language truth.
- prove semantic satisfaction.
- alter top-level `status` or `score` semantics.
- treat LLM reviewer output as accepted facts.
- create a final human acceptance decision.
- migrate additional rule families by implication.

## Implementation Summary

The request logical trace now evaluates:

- `req.verifiability.acceptance_missing`
- `req.verification.method_detail_missing`

`req.verification.method_detail_missing` derives only when:

- the input kind is a requirement.
- verification or acceptance language is accepted in the checked request/context scope.
- no concrete verification method fact is accepted.

The rule is `not_applicable` when verification or acceptance is not in scope, so it does not duplicate the broader acceptance-route finding.

## Fixture Coverage

Added fixture:

- `tests/fixtures/requests/verification-method-weak.expected.json`

This fixture checks that generic confirmation wording derives `req.verification.method_detail_missing` while `req.verifiability.acceptance_missing` remains clean.

## Verification Evidence

Commands run:

```sh
uv run --python 3.13 --project . python -m unittest discover -s tests -v
uv run --python 3.13 --project . python -m compileall src/semantic_guard tests
uv run --python 3.13 --project . semantic-guard evaluate-fixtures --include-passed
uv run --python 3.13 --project . semantic-guard audit-request --text '利用者: 読者。目的: 検索結果の表示を確認する。シナリオ: 読者が検索語を入力する場合、検索結果が表示される。受入基準: 検索結果が表示されることを確認。検証: 動作確認する。証拠: 確認記録。対象外: UI刷新。未確定: なし。'
```

Observed result:

- Unit tests: 125 tests OK.
- Compile check: OK.
- Fixture evaluation: 16 total, 16 passed, pass rate 1.0.
- Fixture derivation hits include both `req.verifiability.acceptance_missing` and `req.verification.method_detail_missing`.
- Representative output includes `logical-derivation/v1`, `logical-trace/v1`, `req.verification.method_detail_missing`, `status=derived`, and derivation scope `rule-and-fact derivation only; not natural-language truth or final acceptance`.

## Next Gate

Do not migrate another rule family until this second slice is reviewed in real use.

Recommended review focus:

- whether two evaluated rules make `details.logical_trace` too noisy.
- whether the second derivation statement is readable.
- whether method-detail findings feel separated from broader acceptance-route findings.
- whether fixture metrics remain clearly local calibration, not statistical claims.

Readability review:

- `docs/logical-audit-second-slice-readability-2026-06-02.md`
- `docs/logical-audit-trace-summary-2026-06-02.md`

Post-review continuation:

- `docs/logical-audit-third-rule-bundle-2026-06-02.md`
- The next-gate condition was addressed by adding compact summary/default output before expanding beyond the second rule.
