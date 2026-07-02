# Logical Audit Trace Summary 2026-06-02

## Purpose

This document defines the compact logical-trace summary view used by CLI and MCP `audit-request` output.

The goal is to reduce first-read cost and fixture brittleness while keeping the full logical trace available for detailed audit.

## Audience And Use

Use this document when reading `audit-request` output, adding fixture expectations, or deciding whether another logical-audit rule can be added without making output too noisy.

Read `details.logical_trace_summary` first. Open `details.logical_trace` only when the summary shows a rule status, finding, unknown, conflict, or count that needs detailed inspection.

## Output Contract

`details.logical_trace_summary` is an optional object derived from the full logical trace. CLI and MCP `audit-request` calls emit it by default and omit `details.logical_trace` unless full trace output is requested.

Minimum shape:

```json
{
  "schema_version": "logical-trace-summary/v1",
  "source_schema_version": "logical-trace/v1",
  "scope": "extracted facts and executable predicates only",
  "derivation_scope": "rule-and-fact derivation only; not natural-language truth or final acceptance",
  "rule_count": 7,
  "fact_count": 12,
  "unknown_count": 0,
  "conflict_count": 0,
  "rules": [
    {
      "rule_id": "req.verification.method_detail_missing",
      "status": "derived",
      "finding_ids": ["finding.req.verification.method_detail_missing"],
      "finding_count": 1,
      "missing_obligation_count": 1,
      "unknown_obligation_count": 0,
      "conflict_obligation_count": 0,
      "countercondition_count": 2,
      "derivation_step_count": 3
    }
  ]
}
```

## Summary Boundary

The summary is a projection of `details.logical_trace`.

It must not:

- include fact excerpts or evidence spans.
- include private reasoning.
- change `status`, `score`, finding emission, or human acceptance.
- replace `finding.derivation` for emitted findings.
- claim statistical precision, recall, proof, release readiness, or natural-language truth.

## Fixture Use

Prefer `logical_trace_summary_rule` for fixture expectations that only need rule-level status and counts.

Example:

```json
{
  "expect": {
    "logical_trace_summary_rule": {
      "rule_id": "req.verification.method_detail_missing",
      "status": "derived",
      "finding_count": 1,
      "missing_obligation_count": 1
    }
  }
}
```

Use full `logical_trace_rule` only for representative compatibility checks or when rule-level summary is insufficient.

## Current Limitation

The full `details.logical_trace` is still available through core `audit_request()` and through CLI/MCP `logical_trace=full`. This preserves compatibility, but full output size can still grow as more executable rules are added.

CLI and MCP support `summary`, `full`, and `none` output modes. The default is `summary`.

## Verification Evidence

Representative checks:

```sh
uv run --python 3.13 --project . semantic-guard audit-request --text '利用者: 読者。目的: 検索結果の表示を確認する。シナリオ: 読者が検索語を入力する場合、検索結果が表示される。受入基準: 検索結果が表示されることを確認。検証: 動作確認する。証拠: 確認記録。対象外: UI刷新。未確定: なし。'
uv run --python 3.13 --project . semantic-guard evaluate-fixtures --include-passed
uv run --python 3.13 --project . python -m unittest discover -s tests -v
```
