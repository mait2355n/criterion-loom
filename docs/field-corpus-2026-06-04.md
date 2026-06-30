# Field Corpus 2026-06-04

This corpus is a review backlog for semantic-guard's next calibration step. It is not counted as fixture accuracy, and it is not statistical evidence of general field robustness.

## Purpose

The deterministic fixtures prove that the current local expectation catalog still passes. The field corpus serves a different purpose: it keeps examples that should guide future detector design before they are promoted into hard pass/fail fixtures.

## Audience and Use

This file is for maintainers who decide whether a warning should be kept, weakened, suppressed, or promoted into a detector. Use it before editing `src/semantic_guard/core.py`, and use it again after fixture evaluation to check whether the change solved the intended example rather than only satisfying a narrow keyword case.

## Corpus shape

The current corpus is `tests/field-corpus/corpus-2026-06-04.json`.

- `good_warning`: warnings that should remain warnings.
- `noisy_warning`: examples that should stay quiet, or whose warning should be weakened.
- `miss`: likely blind spots where a future detector or stricter rule should be considered.

Current balance:

- 10 good-warning entries.
- 10 noisy-warning entries.
- 10 miss entries.

## Review status

The entries are intentionally mixed:

- `accepted` means the example is already suitable as a calibration reference.
- `candidate` means the example is plausible but should be checked against real work before becoming a hard fixture.
- `deferred` is reserved for examples that are valid but not worth acting on in the current priority band.

## Validation

Run the structure check with:

```sh
uv run --python 3.13 --project . python -m unittest tests.test_field_corpus -v
```

Run it with the normal regression suite before promoting any entry:

```sh
uv run --python 3.13 --project . python -m unittest discover -s tests -v
uv run --python 3.13 --project . semantic-guard evaluate-fixtures
```

## Promotion rule

Do not turn a `miss` entry into a detector only because it is easy to match by keywords. Promote it only when the expected review can be tied to a stable engineering obligation: public contract, rollback, evidence, identity boundary, failure handling, operation visibility, concurrency, data retention, destructive operation, time-dependent source, or human decision boundary.

When an entry is promoted, add a deterministic fixture under `tests/fixtures/` and keep this corpus entry as the field-example origin.

## 2026-06-05 Promotion Notes

Three accepted entries were promoted into deterministic fixtures without widening the detectors:

- `GW-REQ-PRIORITY-001` -> `tests/fixtures/requests/field-priority-unprioritized.expected.json`
- `GW-PLAN-ROLLBACK-001` -> `tests/fixtures/plans/field-rollback-missing.expected.json`
- `NW-TEST-COMMAND-001` -> `tests/fixtures/diffs/field-test-command-no-contract.expected.json`

The remaining corpus entries stay as review backlog. A corpus entry should not become a fixture unless its expected review is stable enough to survive wording changes and can be tied to a concrete engineering obligation or a known false-positive boundary.
