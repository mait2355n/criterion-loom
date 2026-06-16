# Logical Audit Design

## Purpose

This document defines the first logical-audit vocabulary for `semantic-guard`.

It is a design document, not implementation evidence. It does not claim that the logical-audit layer already exists.

The goal is to make selected deterministic findings explainable by facts, executable rule predicates, checked counterconditions, obligations, derivation records, unknowns, and conflicts.

The goal is not to prove natural-language truth, semantic satisfaction, safety, release readiness, or final acceptance.

## Audience And Use

This document is for maintainers and Codex work that will implement WP2-WP7 of `docs/logical-audit-integration-plan-2026-06-02.md`.

Use it before adding `src/semantic_guard/logic.py`, before adding `finding.derivation`, and before attaching `details.logical_trace` to public audit output.

Representative commands:

```sh
uv run --python 3.13 --project . semantic-guard audit-request --kind document --file docs/logical-audit-design.md
uv run --python 3.13 --project . python -m unittest discover -s tests -v
uv run --python 3.13 --project . semantic-guard evaluate-fixtures
```

Expected use:

- Treat this as the stable vocabulary for the first logical-audit slice.
- Keep code changes deferred until this document passes document audit.
- Treat every model below as JSON-compatible output design, not as a required Python class name unless the implementation plan later adopts it.

## Scope

In scope:

- `Fact`
- `FactSource`
- `EvidenceSpan`
- `Obligation`
- `Countercondition`
- `RuleEvaluation`
- `DerivationStep`
- `LogicalTrace`
- derivation-scope wording.
- logical `pass`, `warn`, and `block` semantics.
- first vertical slice for `req.verifiability.acceptance_missing`.
- fixture expectations for derivation-shape regression.

Out of scope:

- no code changes in this WP1 pass.
- no new formal proof engine.
- no external logic solver.
- no full migration of all 36 rule catalog entries.
- no LLM-created accepted facts.
- no change to top-level `score`.
- no change to final human decision handling.

## Legacy Boundaries

The design inherits these contracts from the current system:

- `semantic-guard` remains a local research prototype and meaning-first audit layer, not an authoritative requirements engine, release gate, security scanner, MCP competitor, AI safety engine, or autonomous acceptance system.
- Existing phase output remains `phase`, `status`, `score`, `findings`, `missing`, `next_actions`, and `details`.
- New logical output is optional and additive.
- Existing diagnostics remain valid, including `warning_class`, `match_status`, `confidence`, `candidate_matches`, `details.non_emitted_rules`, `details.diagnostics`, and `details.severity_profile`.
- `score` remains the base deterministic severity signal, not derivation strength.
- Fixture evaluation remains local calibration and regression detection, not statistical precision or recall.
- LLM reviewer output is supplement material only.
- `review-if-needed` remains dry-run by default and limited to undecidable residue.
- `acceptance_review_bundle` remains the final human-review package. `final_human_decision.status` remains `pending` until a person decides.

## Derivation Scope

Every derivation record must carry this scope or an equivalent narrower wording:

```text
This derivation is valid only under the extracted facts, accepted counterconditions, and current executable rule predicate. It does not prove that the original natural-language artifact is true, complete, safe, semantically satisfied, release-ready, or accepted.
```

Short output form:

```json
{
  "derivation_scope": "rule-and-fact derivation only; not natural-language truth or final acceptance"
}
```

## Logical Status Vocabulary

### FactStatus

`FactStatus` records what the deterministic audit layer may use.

| Status | Meaning | May satisfy an obligation |
| --- | --- | --- |
| `present` | Evidence was deterministically accepted inside the declared input and context scope. | Yes |
| `absent` | The extractor checked the declared scope and did not find acceptable evidence. This is scoped absence, not global nonexistence. | No |
| `candidate` | A tolerance layer, reviewer, or weak match proposed a possible fact. | No |
| `rejected` | A candidate was inspected and rejected for a recorded reason. | No |
| `unknown` | The system cannot decide deterministically. | No |
| `conflict` | Evidence points to incompatible facts or statuses. | No |

`candidate`, `rejected`, `unknown`, and `conflict` must not be silently treated as `present`.

### DerivationStatus

`DerivationStatus` records the result of evaluating a rule predicate.

| Status | Meaning |
| --- | --- |
| `derived` | A finding or missing obligation was derived from accepted facts and the rule predicate. |
| `not_derived` | The predicate was evaluated and did not derive the finding. |
| `blocked_by_unknown` | The predicate needs a fact that is `unknown`. |
| `conflict` | The predicate encountered conflicting facts. |
| `not_applicable` | A countercondition makes the rule not applicable. |
| `satisfied` | Required obligations were satisfied under the evaluated rule. |

`DerivationStatus` is categorical. It is not a numeric confidence score.

## Core Models

### Fact

`Fact` is an audit fact accepted, rejected, or held by the logical layer.

Minimum shape:

```json
{
  "id": "fact.text.has_verification_language",
  "name": "text.has_verification_language",
  "status": "absent",
  "value": false,
  "source": {
    "kind": "deterministic_extractor",
    "label": "verification_terms"
  },
  "evidence": [],
  "extraction_method": "known_terms_absence",
  "confidence": "high",
  "notes": "Scoped to supplied request text and context."
}
```

Required fields:

- `id`: stable local identifier inside one trace.
- `name`: stable semantic name.
- `status`: one `FactStatus`.
- `source`: one `FactSource`.
- `evidence`: zero or more `EvidenceSpan` entries.
- `extraction_method`: stable method label.

Rules:

- `present` facts should have at least one evidence span unless the source is structural, such as `input_kind`.
- `absent` facts should name the extractor and checked scope.
- LLM-generated facts must enter as `candidate`.
- Human decisions may mark a candidate as accepted only when the decision is explicit and local to the audit material. That does not fill final acceptance.
- A fact from `trace-report` vocabulary must not be created from `suggested_tags` alone.

### FactSource

`FactSource` records where the fact came from.

Allowed initial source kinds:

| Kind | Use |
| --- | --- |
| `input_kind` | The caller supplied kind, such as `requirement`, `document`, `plan`, `diff-summary`, or `finish`. |
| `deterministic_extractor` | Local lexical, heading, structure, or profile extraction. |
| `requirement_profile` | Existing `details.requirement_profile` style extraction. |
| `requirement_structure` | Existing `details.requirement_structure` style extraction. |
| `candidate_match` | Existing `candidate_matches` or `nearest_candidates`; default status is `candidate` or `rejected`. |
| `context` | Explicit context text supplied to the audit command. |
| `trace_vocabulary` | Explicit caller tags or accepted `vocabulary_profile` entries only. |
| `llm_reviewer` | Reviewer supplement material; default status is `candidate`. |
| `human_decision` | Explicit human decision on a local fact or countercondition, not final acceptance. |

No hidden project context is a fact source unless it is supplied as audit input or explicit context.

### EvidenceSpan

`EvidenceSpan` points to the text or structural input that supports a fact.

Minimum shape:

```json
{
  "source": "request",
  "field": "text",
  "excerpt": "Verification: run unit tests and inspect JSON output.",
  "start": 12,
  "end": 67
}
```

Rules:

- `excerpt` should be short.
- `start` and `end` are optional when the extractor does not track offsets.
- Absence facts may use an empty evidence list and a `checked_scope` note in the fact.
- Evidence spans are not proof of natural-language truth. They are only the inspected material for deterministic audit.

### Obligation

`Obligation` records what a rule requires.

Minimum shape:

```json
{
  "id": "obl.verification_or_acceptance",
  "rule_id": "req.verifiability.acceptance_missing",
  "description": "Requirement must state how achievement will be verified or accepted.",
  "required_facts": [
    "text.has_verification_language",
    "text.has_acceptance_criteria"
  ],
  "status": "missing",
  "missing_fact_names": [
    "text.has_verification_language",
    "text.has_acceptance_criteria"
  ]
}
```

Allowed obligation status values:

- `satisfied`
- `missing`
- `unknown`
- `conflict`
- `not_applicable`

An obligation can be `satisfied` only by accepted `present` facts or an explicit countercondition that makes the obligation not applicable.

### Countercondition

`Countercondition` records why a rule may not apply.

Minimum shape:

```json
{
  "id": "ctr.input_kind_not_requirement",
  "rule_id": "req.verifiability.acceptance_missing",
  "description": "Rule does not apply to document, plan, diff-summary, or finish input.",
  "checked_facts": [
    "input.kind"
  ],
  "status": "absent",
  "effect": "continue"
}
```

Allowed countercondition status values:

- `present`
- `absent`
- `unknown`
- `conflict`

Allowed effects:

- `not_applicable`
- `satisfied`
- `continue`
- `defer`

Counterconditions must be checked before deriving a finding. A present countercondition with `not_applicable` suppresses the finding and may appear in `details.non_emitted_rules`.

### RuleEvaluation

`RuleEvaluation` records one executable predicate evaluation.

Minimum shape:

```json
{
  "rule_id": "req.verifiability.acceptance_missing",
  "phase": "audit_request",
  "predicate_id": "req.verifiability.acceptance_missing/v1",
  "status": "derived",
  "facts_used": [
    "fact.input.kind",
    "fact.text.has_verification_language"
  ],
  "counterconditions_checked": [
    "ctr.input_kind_not_requirement",
    "ctr.external_acceptance_route"
  ],
  "obligations": [
    "obl.verification_or_acceptance"
  ],
  "finding_ids": [
    "finding.req.verifiability.acceptance_missing"
  ],
  "derivation_steps": [
    "step.001",
    "step.002"
  ]
}
```

Rules:

- Keep `predicate_id` versioned.
- Keep explanatory `Rule.applies_when` and `Rule.does_not_apply_when`; do not pretend those prose fields are executable logic.
- Map executable predicates to rule ids separately.
- One rule may have no public derivation output during WP3; public derivation output begins only when WP5 accepts it.

### DerivationStep

`DerivationStep` is a human-readable derivation item.

Minimum shape:

```json
{
  "id": "step.002",
  "statement": "No verification or acceptance fact was accepted in the checked request/context scope.",
  "from": [
    "fact.text.has_verification_language",
    "fact.text.has_acceptance_criteria"
  ],
  "to": "obl.verification_or_acceptance",
  "operator": "all_absent"
}
```

Rules:

- Steps should be short and deterministic.
- Steps must reference facts, obligations, counterconditions, or rule predicate clauses.
- Steps must not cite private model reasoning.
- Steps must not use LLM prose as an accepted fact or direct derivation input.

### LogicalTrace

`LogicalTrace` is the phase-level logical summary.

Minimum shape:

```json
{
  "schema_version": "logical-trace/v1",
  "scope": "extracted facts and executable predicates only",
  "derivation_scope": "rule-and-fact derivation only; not natural-language truth or final acceptance",
  "phase": "audit_request",
  "rules_evaluated": [],
  "facts": [],
  "unknowns": [],
  "conflicts": []
}
```

Rules:

- `details.logical_trace` is optional.
- Empty or absent trace means no logical output was emitted, not that the input was fully proven.
- `unknowns` and `conflicts` must stay visible when they affect an evaluated predicate.
- Trace output should align with `details.diagnostics`, not create a parallel acceptance decision.

## Output Contract

Existing top-level output remains unchanged:

```json
{
  "phase": "audit_request",
  "status": "warn",
  "score": 0.82,
  "findings": [],
  "missing": [],
  "next_actions": [],
  "details": {}
}
```

Optional finding derivation shape:

```json
{
  "severity": "blocker",
  "category": "verifiability",
  "rule_id": "req.verifiability.acceptance_missing",
  "derivation": {
    "schema_version": "logical-derivation/v1",
    "derivation_scope": "rule-and-fact derivation only; not natural-language truth or final acceptance",
    "rule_id": "req.verifiability.acceptance_missing",
    "status": "derived",
    "facts_used": [],
    "counterconditions_checked": [],
    "missing_obligations": [],
    "derivation_steps": [],
    "unresolved_unknowns": []
  }
}
```

Compatibility rules:

- `finding.derivation` is optional.
- `details.logical_trace` is optional.
- Existing fields keep their meaning.
- `status` and `score` are not redefined by derivation output.
- Derivation output does not replace `repair`, `warning_class`, `match_status`, `confidence`, or `candidate_matches`.
- Derivation output does not decide human acceptance.

## Logical Status Semantics

Top-level `status` keeps the current public meaning. Logical output narrows only the explanation behind selected findings.

When `details.logical_trace` is present:

- `pass` means no violation was derived by the evaluated executable predicates, and no evaluated predicate was blocked by unresolved critical unknowns or conflicts.
- `warn` means a non-blocking finding, missing obligation, unknown, or conflict should be reviewed.
- `block` means a strict-mode blocker was derived or a required critical fact is unknown or conflicting in a way that prevents a bounded predicate decision.

These semantics apply only to evaluated executable predicates. They do not prove that unevaluated rules, hidden project context, domain truth, security, or final acceptance are complete.

## First Vertical Slice

The first implementation slice is limited to:

```text
req.verifiability.acceptance_missing
```

Reason:

- It is already a central requirement-quality rule.
- Existing output already emits a finding and `missing` entry for this failure mode.
- It has clear reverse conditions: wrong input kind or explicit external acceptance route.
- It exercises facts, obligations, counterconditions, and derivation steps without touching every phase.

### Candidate Facts

Initial fact names:

| Fact name | Expected source | Notes |
| --- | --- | --- |
| `input.kind` | `input_kind` | Caller-supplied kind. |
| `input.kind.requirement` | `input_kind` | Present when kind is `requirement` or compatible requirement candidate. |
| `text.has_verification_language` | `deterministic_extractor` | Terms such as verification, check, test, evidence, acceptance, or Japanese equivalents. |
| `text.has_acceptance_criteria` | `requirement_profile` | Existing profile-like extraction. |
| `text.has_verification_method` | `requirement_profile` | Existing method extraction. |
| `text.has_evidence_artifact` | `requirement_profile` | Existing evidence artifact extraction. |
| `context.has_external_acceptance_route` | `context` | Explicit acceptance or verification route in supplied context. |

Do not use `candidate_matches` as accepted facts. They may produce `candidate` or `rejected` facts.

### Predicate Sketch

The first predicate should evaluate in this order:

1. Check input kind.
2. Check counterconditions.
3. Check accepted verification or acceptance facts.
4. Derive missing obligations when required accepted facts are absent.
5. Record unknowns and conflicts instead of silently passing.

Sketch:

```text
countercondition:
  if input.kind is document, plan, diff-summary, or finish:
    status = not_applicable

countercondition:
  if context.has_external_acceptance_route is present:
    status = not_applicable or satisfied

applies:
  if input.kind.requirement is present
  and no not_applicable countercondition is present

derive:
  if text.has_verification_language is absent
  and text.has_acceptance_criteria is absent
  and text.has_verification_method is absent:
    missing obligation = verification_or_acceptance
    derivation status = derived

defer:
  if a required fact is unknown:
    derivation status = blocked_by_unknown

conflict:
  if required facts conflict:
    derivation status = conflict
```

The implementation may refine the exact accepted-fact group, but it must keep the first slice bounded to this rule and preserve current fixture behavior unless a separate regression note explains the intended calibration change.

## LLM Reviewer Boundary

The LLM reviewer may propose:

- candidate facts.
- candidate counterconditions.
- questions.
- supplement proposals.
- human review points.

The LLM reviewer must not directly create:

- accepted facts.
- accepted counterconditions.
- derivation steps.
- final findings.
- top-level `status`.
- `score`.
- final human decisions.

If an LLM proposal is useful, it enters the logical model as `status: "candidate"` with `source.kind: "llm_reviewer"`. It becomes accepted only through deterministic evidence or explicit local human decision. That local fact decision still does not decide final acceptance.

## Trace Vocabulary Boundary

`trace-report` vocabulary output remains diagnostic.

Rules:

- `suggested_tags` must not become accepted facts.
- unresolved terms must not become facts.
- weak vocabulary links must not become facts.
- accepted `vocabulary_profile` terms may become trace tags.
- accepted trace tags may support a `trace_vocabulary` source only when a deterministic extractor separately records the fact relation.

This prevents the logical layer from treating a naming suggestion as evidence.

## Fixture And Evaluation Design

Proof-shape fixtures should avoid whole-output equality.

Possible fixture label additions:

- `derivation_status`
- `derivation_rule_id`
- `derivation_missing_obligation`
- `derivation_countercondition`
- `derivation_fact`
- `logical_trace_rule`
- `logical_trace_unknown`
- `logical_trace_conflict`

Evaluation output must keep:

- local fixture totals.
- expected and forbidden rule labels.
- `rule_catalog_coverage.unhit_rule_ids`.
- `local_calibration_only: true`.

New derivation metrics must not be described as statistical precision or recall for arbitrary documents.

## Implementation Sequence

1. WP2: Add compatibility-only logical data structures, likely in `src/semantic_guard/logic.py`.
2. WP3: Build internal facts for `req.verifiability.acceptance_missing` without public derivation output.
3. WP4: Add the executable predicate for the target rule while matching current fixture behavior.
4. WP5: Add optional `finding.derivation` and `details.logical_trace`.
5. WP6: Add fixture matchers for derivation-shape invariants.
6. WP7: Update README, LLM reviewer docs, acceptance bundle docs, and dogfood notes.
7. WP8: Decide whether to continue, pause, revise, or retire derivation output.

Dependencies:

- WP2 must happen before derivation output.
- WP3 must happen before WP4.
- WP4 must happen before WP5.
- WP5 must happen before WP6.
- WP6 and WP7 must both pass before WP8.

Resource basis:

- The first implementation should use the current local Python codebase.
- No external parser, NLP dependency, proof solver, or network service is assumed.
- The first implementation owner is the maintainer/Codex worker for this repository.
- The first estimate basis is a narrow one-rule vertical slice, not a whole-catalog migration.

Risks and responses:

| Risk | Response |
| --- | --- |
| Derivation wording overclaims truth or safety. | Keep derivation scope in every derivation record and audit README wording before public use. |
| Logical output changes `score` semantics. | Keep derivation statuses categorical and do not mix them into score calculation. |
| Candidate facts become accepted facts. | Require deterministic evidence or explicit local human decision before status can become `present`. |
| LLM reviewer output becomes judgment. | Keep reviewer source facts as `candidate`; never let reviewer output create findings or final decisions directly. |
| Trace vocabulary suggestions become facts. | Treat `suggested_tags` and unresolved terms as diagnostics only. |
| First slice changes legacy behavior. | Preserve current fixtures; any fixture change needs an explicit calibration note. |
| Whole catalog migration starts too early. | Stop expansion at `req.verifiability.acceptance_missing` until WP8. |

Change control:

- Any public output shape change outside optional `finding.derivation` and `details.logical_trace` requires a new plan audit.
- Any implementation request before this design passes document audit is deferred.
- Any additional rule family before WP8 is deferred.
- Any new source kind for accepted facts must be added to this document or a follow-up design note before implementation.

Rollback or recovery:

- If the logical model breaks serialization, remove or isolate `src/semantic_guard/logic.py` and keep public output unchanged.
- If predicate behavior changes fixture results unintentionally, stop at the last passing work package and replan.
- If derivation output confuses acceptance, disable `finding.derivation` emission and keep internal traces only.
- If LLM reviewer material starts acting like accepted facts, remove that source path until the boundary is redesigned.

## Acceptance Evidence

WP1 has enough evidence to proceed to compatibility-only implementation planning when:

- this document exists.
- this document says natural-language truth is not proven.
- this document preserves output compatibility.
- this document limits the first implementation to `req.verifiability.acceptance_missing`.
- this document defines `Fact`, `FactSource`, `EvidenceSpan`, `Obligation`, `Countercondition`, `RuleEvaluation`, `DerivationStep`, and `LogicalTrace`.
- this document defines logical `pass`, `warn`, and `block` semantics.
- this document preserves the LLM candidate-fact boundary.
- `semantic-guard audit-request --kind document --file docs/logical-audit-design.md` returns pass.
- existing unit tests and fixture evaluation still pass.

## Open Decisions

These are intentionally deferred:

- Whether derivation output should be enabled by default or behind a flag during WP5.
- Whether `context.has_external_acceptance_route` should mark the rule `not_applicable` or the obligation `satisfied` in all cases.
- Whether `Fact` should be implemented as dataclasses, typed dictionaries, or small serializable dictionaries.
- Whether accepted local human fact decisions need a separate schema before use.

None of these decisions block WP2 as long as WP2 remains compatibility-only and does not change public audit behavior.
