# Logical Audit Second Slice Readability Review 2026-06-02

## Purpose

This document reviews whether the second logical-audit slice is readable in representative real-use output.

The review is about human readability and boundary clarity. It is not a statistical accuracy report, a final acceptance decision, or proof of natural-language correctness.

## Usage

Read this after `docs/logical-audit-second-slice-2026-06-02.md` when deciding whether to keep, revise, or extend the second request-verification slice.

Use it as implementation review material. Do not use it as a release gate by itself.

## Reviewed Cases

Four representative cases were inspected:

| Case | Input shape | Expected readability result |
| --- | --- | --- |
| Acceptance route absent | `目的: 速度改善をしたい。` | `req.verifiability.acceptance_missing` derives; method-detail rule is not applicable. |
| Generic confirmation only | Acceptance criteria and evidence exist, but verification says only `動作確認する` | `req.verification.method_detail_missing` derives; broad acceptance-route finding does not derive. |
| Concrete method present | Acceptance criteria, benchmark method, evidence, and rejection condition exist | Both request-verification rules are satisfied and no derivation finding is emitted. |
| Document kind | Text mentions verification, but input kind is document | Requirement logical trace does not appear. |

## Observations

`finding.derivation` is readable for the second rule:

- It states the checked scope through `derivation_scope`.
- It says verification or acceptance language was accepted in the checked request/context scope.
- It says no concrete verification method fact was accepted.
- It derives only `req.verification.method_detail_missing`, not the broader acceptance-route finding.

`details.logical_trace` is more verbose than `finding.derivation`, but still useful as review material:

- `rules_evaluated` shows both request-verification rules.
- The broad rule can be `not_derived` while the method-detail rule is `derived`.
- `finding_ids` stays empty for non-emitted rules.
- Non-requirement document input does not expose request logical trace.

## Readability Fix Applied

The initial second-slice output was mostly readable, but one trace sentence was too vague:

```text
The target finding is not derived, though related obligations may still be missing.
```

That sentence did not clearly explain why the broad acceptance-route finding could be clean while the method-detail rule still derived.

It was replaced with:

```text
The broad acceptance-route finding is not derived because its primary obligation is satisfied; narrower obligations may still be reviewed by other rules.
```

The satisfied-method sentence was also made more concrete:

```text
A concrete verification method fact is accepted in scope, so the target rule is satisfied.
```

## Conclusion

The second slice is readable enough to keep.

It should not yet trigger another rule-family migration. The next gate should review this two-rule trace in real use and decide whether the raw `details.logical_trace` verbosity is still acceptable.

## Verification Evidence

Commands run:

```sh
uv run --python 3.13 --project . semantic-guard audit-request --text '目的: 速度改善をしたい。'
uv run --python 3.13 --project . semantic-guard audit-request --text '利用者: 読者。目的: 検索結果の表示を確認する。シナリオ: 読者が検索語を入力する場合、検索結果が表示される。受入基準: 検索結果が表示されることを確認。検証: 動作確認する。証拠: 確認記録。対象外: UI刷新。未確定: なし。'
uv run --python 3.13 --project . semantic-guard audit-request --text '利用者: 運用者。目的: 検索を速くする。シナリオ: 運用者が検索語を入力した場合、結果一覧が返る。受入基準: p95 500ms 以下。検証方法: ベンチマーク測定。証拠: コマンド結果を保存する。不合格条件: p95 が 500ms を超えたら差し戻し。対象外: UI刷新。未確定: なし。'
uv run --python 3.13 --project . semantic-guard audit-request --kind document --text 'これは説明文書である。検証方法の話題を扱うが、要求ではない。'
uv run --python 3.13 --project . python -m unittest tests.test_logic tests.test_core -v
```

Observed results:

- Acceptance route absent: broad acceptance-route rule derives; method-detail rule is `not_applicable`.
- Generic confirmation only: broad acceptance-route rule is `not_derived`; method-detail rule derives.
- Concrete method present: both rules are `satisfied`; top-level status remains `pass`.
- Document kind: no requirement logical trace appears.
- Targeted unit tests: 68 tests OK.

## Residual Risk

The readability is acceptable for the current two-rule trace, but raw trace verbosity will grow quickly if more rules are added.

Before adding another rule family, review whether `details.logical_trace` needs a compact summary view or per-rule filtering.

Post-review update:

- `details.logical_trace_summary` now provides the compact first-read view.
- Full `details.logical_trace` remains available for detailed audit and compatibility.
- Per-rule filtering is still deferred.
