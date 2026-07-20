# Calibration Report 2026-06-05

## Purpose

This report records the current `semantic-guard` fixture calibration state after
the first public-maturity pass: CI matrix verification, audit-result schema,
rule-detector mapping, doctor command, and limited field-corpus fixture
promotion.

It is not a statistical accuracy report. The fixture set is small and local.
The numbers below only show that the current regression examples behave as
expected; they do not prove broad precision, recall, safety, or release
readiness.

## Audience And Use

Use this report when reviewing the current public snapshot, checking whether CI
and local fixture calibration still agree, or deciding the next detector-quality
work package. Do not use it as a release gate or as evidence of general natural
language accuracy.

## Command

Run from the repository checkout root:

```sh
uv run --python 3.13 --project . semantic-guard evaluate-fixtures --include-passed
```

## Snapshot

- Fixture total: 39
- Passed: 39
- Failed: 0
- Pass rate: 1.0

Phase counts:

| Phase | Count |
| --- | ---: |
| `audit_request` | 17 |
| `audit_plan` | 9 |
| `audit_diff` | 10 |
| `finish_check` | 3 |

Expected and actual status counts matched:

| Status | Count |
| --- | ---: |
| `block` | 5 |
| `warn` | 24 |
| `pass` | 10 |

## Local Label Metrics

These are fixture-label checks only.

| Metric | Value |
| --- | ---: |
| Expected finding labels | 34 |
| Expected finding matches | 34 |
| Forbidden finding labels | 13 |
| Forbidden finding clean | 13 |
| Expected rule labels | 37 |
| Expected rule matches | 37 |
| Forbidden rule labels | 14 |
| Forbidden rule clean | 14 |
| Local false positives | 0 |
| Local false negatives | 0 |

The zero false-positive and false-negative counts apply only to the current
fixture labels. They must not be presented as general detector accuracy.

## Rule Catalog Coverage

- Catalog rule count: 36
- Rule ids touched by fixture labels: 36
- Unhit rule ids: 0
- Unemitted rule ids in the current fixture run: 0

`rule-detector-map` also reports 36 mapped catalog rules. That is a maintenance
trace from catalog id to detector code path, not a semantic proof.

## Field-Corpus Promotion

This pass promoted three accepted field-corpus examples into deterministic
fixtures:

- `GW-REQ-PRIORITY-001`: bundled administrator work without priority remains a
  priority warning.
- `GW-PLAN-ROLLBACK-001`: public CLI behavior change without rollback remains a
  risk warning.
- `NW-TEST-COMMAND-001`: test-only command wording remains quiet and should not
  be treated as a public contract change.

The remaining field corpus stays outside the deterministic fixture count. It is
still a review backlog, not accuracy evidence.

## Interpretation

The current fixture set is useful as a regression harness, not as a benchmark.
It covers the local rule catalog and a small number of accepted false-positive
boundaries, but it is still vocabulary-driven and intentionally narrow.

The next detector-quality pass should add more real examples before widening
heuristics. The safer order remains corpus first, then vocabulary tolerance,
warning policy, and detector refactoring.
