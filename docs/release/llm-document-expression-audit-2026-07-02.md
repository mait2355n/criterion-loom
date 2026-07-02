# LLM Document Expression Audit 2026-07-02

## Purpose

This record captures a problem-seeking LLM audit over selected local documents.
The goal is to find document expressions that may need rewriting or new
`doc.expression.*` detector support.

This is candidate-generation material. It is not a final acceptance decision and
does not rewrite the source documents.

## Method

- Reviewer source: current Codex session LLM.
- Fresh-eyes isolation: not used in this first batch.
- Premise: assume useful expression issues exist and search for them.
- Deterministic comparison: each target was also checked with
  `semantic-guard audit-conventions --kind document`.
- Raw data: excluded from the public tree; retained as local calibration output.
- Triage table: `docs/release/llm-document-expression-audit-triage-2026-07-02.md`.

## Scope

| Resource | Path | Lines | Deterministic status | Expression findings |
| --- | --- | ---: | --- | --- |
| `semantic-guard` | `README.md` | 574 | `pass` | none |
| `semantic-guard` | `README.ja.md` | 166 | `warn` | `as_view_operation_blurred`, `inspection_contract_missing` |
| `semantic-guard` | `docs/conventions/README.md` | 75 | `warn` | multiple example-context expression findings |
| `semantic-guard` | `docs/conventions/base-contract.md` | 279 | `pass` | none |
| `continuity-concentrator` | `README.md` | 126 | `warn` | `demonstrative_reference_blurred` |
| `resource-control-plane` | `README.md` | 167 | `warn` | `demonstrative_reference_blurred`, `as_view_operation_blurred` |
| `resource-control-plane` | `docs/audit-integration.md` | 238 | `warn` | `as_view_operation_blurred`, `operation_blurred` |
| `resource-control-plane` | `docs/unresolved-decision-management.md` | 96 | `warn` | `demonstrative_reference_blurred`, `output_form_missing`, `as_view_operation_blurred`, `inspection_contract_missing` |

## Summary

- Candidate count: 29.
- `semantic-guard`: 13 candidates.
- `continuity-concentrator`: 5 candidates.
- `resource-control-plane`: 11 candidates.
- Deterministic detector did not emit the relevant expression issue for 23
  candidates.
- Deterministic detector emitted a relevant finding for 4 candidates.
- Deterministic detector emitted likely false positives for 2 candidates.

## Main Findings

The current deterministic expression rules are too phrase-oriented. The LLM
audit found several recurring slot families that should become broader detector
inputs:

- `capability_contract_missing`: claims such as "all visible information" or
  "every material missing question" need visibility boundaries, limits, and
  non-guarantee language.
- `abstract_material_contract_missing`: phrases such as "visible place",
  "support material", "context material", and "concentration" need output shape,
  fields, consumer, and use.
- `evaluation_axis_missing`: phrases such as "too much noise" or "explicit
  incompleteness over confident reconstruction" need a metric, threshold, or
  acceptance example.
- `repair_routing_contract_missing`: phrases about returning to a rule, detector,
  fixture, corpus, document, or skill need a symptom-to-destination routing rule.
- `mapping_contract_missing`: phrases such as "map audit results to resource
  state, risk, and next action" need a field mapping, priority rule, and evidence
  preservation rule.
- `acceptance_contract_missing`: acceptance bullets such as "visible",
  "recordable", or "traceable" need representative commands, sample records,
  schema checks, or explicit unimplemented boundaries.
- `closure_contract_missing`: phrases about keeping valuable unresolved items
  and closing them later need retention thresholds, closure triggers, and
  append-only link evidence.
- `example_context_suppression`: convention documents intentionally contain bad
  examples and should not be treated as source prose that needs rewriting.

## High-Value Candidates

1. `README.md` lines 10 and 142 use "all/every" capability language for LLM
   exploration. These are strong detector-gap candidates because current
   `audit-conventions` passes the file.
2. An earlier `README.ja.md` draft used abstract output-surface wording for
   value judgments; the current README wording names audit results and revision
   loops instead.
3. `docs/conventions/base-contract.md` lines 181-185 say morphological analysis
   should wait until "too much" false-positive or false-negative noise appears,
   but no threshold is named.
4. `continuity-concentrator` `README.md` line 3 says context is prepared to a
   concentration usable by the next task; this is useful wording, but the
   readiness criteria are not recoverable from the sentence.
5. `continuity-concentrator` `README.md` line 9 says context material is
   collected, concentrated, bundled, and unresolved remainder is exposed; the
   bundle shape and exposure surface should be named.
6. `resource-control-plane` `README.md` line 3 says the system looks across all
   resources and decides what to handle next; the resource scope, observation
   source, priority rule, and decision actor should be named.
7. `resource-control-plane` `docs/audit-integration.md` lines 36-41 say audit
   results are mapped to resource state, risk, and next action; this needs a
   field-level mapping contract.
8. `resource-control-plane` `docs/unresolved-decision-management.md` line 47
   says unresolved decisions are acceptable but hidden unresolved decisions are
   not; the operational signal for "hidden" should be named.

## Non-Decisions

- Do not treat LLM candidates as accepted findings.
- Do not edit README files from this batch without a separate rewrite pass.
- Do not collapse `semantic-guard`, `continuity-concentrator`, and
  `resource-control-plane` into one system boundary.
- Do not claim the deterministic detector already catches these broad slot
  families.

## Next Actions

1. Review the triage table and mark each candidate as accepted, false positive,
   rewrite-only, needs context, or deferred.
2. Promote accepted detector gaps into `doc.expression.*` contract-family rules.
3. Add false-positive cases as suppression fixtures.
4. After this batch is judged, run the same LLM audit pattern over additional
   local project docs instead of assuming the current three-resource sample is
   complete.
