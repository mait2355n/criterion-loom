# Calibration Report 2026-06-04

## Purpose

This report records the current `semantic-guard` fixture calibration state after
the first requirements/planning/software-systems fixture expansion pass.

It is not a statistical accuracy report. The fixture set is small and local.
The numbers below only show that the current regression examples behave as
expected; they do not prove broad precision, recall, safety, or release
readiness.

## Audience And Use

Use this report when deciding whether the current fixture set is strong enough
to support a public README, a small release note, or the next detector-quality
work package.

The intended readers are maintainers and reviewers. Read it before widening
heuristics, adding Japanese synonym handling, or claiming that the detector has
improved. Do not use it as a release gate or as a claim of general accuracy.

## Command

Run from the repository checkout root:

```sh
uv run --python 3.13 --project . semantic-guard evaluate-fixtures --include-passed
```

## Snapshot

- Fixture total: 36
- Passed: 36
- Failed: 0
- Pass rate: 1.0

Phase counts:

| Phase | Count |
| --- | ---: |
| `audit_request` | 16 |
| `audit_plan` | 8 |
| `audit_diff` | 9 |
| `finish_check` | 3 |

Expected and actual status counts matched:

| Status | Count |
| --- | ---: |
| `block` | 3 |
| `warn` | 24 |
| `pass` | 9 |

## Local Label Metrics

These are fixture-label checks only.

| Metric | Value |
| --- | ---: |
| Expected finding labels | 32 |
| Expected finding matches | 32 |
| Forbidden finding labels | 12 |
| Forbidden finding clean | 12 |
| Expected rule labels | 35 |
| Expected rule matches | 35 |
| Forbidden rule labels | 13 |
| Forbidden rule clean | 13 |
| Local false positives | 0 |
| Local false negatives | 0 |

The zero false-positive and false-negative counts apply only to the current
fixture labels. They must not be presented as general detector accuracy.

## Rule Catalog Coverage

- Catalog rule count: 36
- Rule ids touched by fixture labels: 36
- Unhit rule ids: 0
- Unemitted rule ids in the current fixture run: 0

The expansion added or labeled examples for:

- implementation diff concerns such as runtime dependency changes, failure
  handling, public contract changes, observability gaps, identity-boundary
  changes, and source-without-test obligations.
- finish-check behavior evidence where unit tests exist but representative
  public CLI/API/MCP execution is absent.
- planning concerns such as progress control, rollback, validation owner, and
  problem-fit validation.
- request concerns such as prioritization, classified versus unclassified
  uncertainty, stakeholder source, and explicit rule labels for existing
  logical-audit cases.

## Interpretation

The current fixture set is useful as a regression harness, not as a benchmark.
It catches several important local conflicts:

- broad Japanese scope wording that should not over-warn when bounded.
- bounded work-package requests that should not trigger atomicity or priority
  noise.
- docs-only evidence wording that should not become a semantic evidence mutation
  warning.
- command wording in tests and CLI documents that should not become a generic
  security signal.
- weak verification wording, missing evidence artifacts, missing rejection
  conditions, missing scenario context, and missing observable behavior in
  request audits.
- public contract changes, dependency/runtime changes, source changes without
  tests, failure-prone file/JSON paths without handling, operational background
  paths without observability, and identity/display/storage boundary changes in
  diff audits.
- completion claims where tests exist but representative public behavior
  evidence is still missing.
- plan gaps around rollback, validation owner, progress control, and
  problem-fit validation.

The next detection-quality pass should collect 30 to 50 real examples divided
into:

- good warnings that should remain warnings.
- noisy warnings that should be suppressed, weakened, or marked as possible
  false positives.
- misses where `semantic-guard` should have warned but did not.

Do not widen heuristics before those examples exist. The safer order is corpus
first, then vocabulary tolerance and warning policy changes.

The zero unhit-rule count is local catalog coverage only. It means each current
rule has at least one labeled fixture path; it does not mean the detector is
broadly accurate across real projects.
