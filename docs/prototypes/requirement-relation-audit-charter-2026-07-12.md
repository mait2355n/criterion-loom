# Requirement Relation Audit Prototype Charter

> Historical prototype charter recorded before the 1.0.0 canonicalization.
> Its implementation-status wording is not current; use the root README and
> `docs/implementation-status.md` for the 1.1.0 surface. The charter remains a
> dated source for the prototype's intended boundaries, not a current work order.

Date: 2026-07-12

Status at record time: implementation in progress; human acceptance pending

Recorded at: `2026-07-12T23:56:26+09:00` (ISO 8601 with timezone)

## Purpose

This charter bounds the first implementation of requirement-semantic relation
audit so that a stronger parser does not become an unbounded correctness or
approval claim. It is the implementation gate for this prototype, not evidence
that the acceptance criteria below have already been met.

## Audience And Use

Maintainers use this charter to implement and test the prototype. Audit agents
use it to preserve extractor authority, uncertainty, and original-purpose
boundaries. Human reviewers use its acceptance, rejection, and residual-risk
sections when deciding whether to accept, revise, or defer the prototype.

## Prototype Identity

- `prototype_id`: `requirement-relation-audit/v0`.
- `repository_id`: `semantic-guard`.
- `implementation_scope`: bounded functional-requirement relation audit.
- `decision_owner`: human.

## Hypothesis

A requirement audit can expose defects that lexical field-presence checks miss
by projecting bounded, explicit statements into a typed semantic assertion IR,
then comparing asserted relations with a requirement-kind-specific relation
profile.

The prototype succeeds only if it distinguishes an asserted relation from a
quoted, historical, conditional, metalinguistic, parser-proposed, or
LLM-proposed candidate. More extraction routes are not permission to turn an
uncertain interpretation into a pass.

## Origin Trace

- `OR-01`: strengthen lifecycle audit by checking engineering relations rather
  than isolated field-name occurrence.
- `OR-02`: prepare a typed claim-and-evidence relation substrate without
  claiming that action occurrence, authority, provenance, or authenticity has
  been proved.
- `OR-03`: return traceable relation deltas that an agent can use to revise a
  requirement and that a human can inspect before acceptance.
- Invariants 1-4: audit output remains intermediate material; final acceptance
  remains human; `pass` is not operational acceptance.
- Invariants 9-13: lexical occurrence is not an affirmative proposition;
  description completeness is not action proof; absent or weak evidence cannot
  become implicit success; evidence sources keep distinct trust strengths.
- Invariant 14: `semantic-guard` audits; `resource-control-plane` owns
  management state and next-action control.

## Essential Realization

The goal is not to add a Japanese parser. The goal is to make the following
chain inspectable:

```text
source text
  -> source-bounded assertion candidates
  -> typed entities and relations
  -> requirement relation obligations
  -> satisfied, missing, mismatched, unknown, or conflicting relation state
  -> repair and human-review material
```

## Input And Output

Input is the existing `audit-request` requirement text and optional context.

The first slice keeps the existing CLI, MCP tool, Python function signatures,
common audit-result envelope, error shape, stdout/stderr roles, and exit-code
behavior. It adds a versioned, additive
`details.requirement_relation_summary` for requirement input only. The full IR
is internal and is not a stable public export in this slice.

Candidate internal versions:

- `semantic-assertion-ir/v0`.
- `requirement-relation-profile/v0`.
- `relation-delta/v0`.
- `requirement-relation-summary/v1`.

Any future full-IR export, user-defined relation profile, new CLI command, new
MCP tool, automatic LLM execution, or durable relation record requires a
separate public-contract decision and convention audit.

Repository profile for this charter:

| Field | Value |
| --- | --- |
| `schema_version` | `requirement-relation-prototype-charter/v0` |
| `repository_id` | `semantic-guard` |
| `public_surfaces` | existing `audit-request` CLI, MCP tool, Python API, and additive audit-result details |
| `commands` | existing `audit-request`; no new command in the first slice |
| `output_shapes` | existing audit-result envelope plus versioned additive relation summary |
| `records` | no new durable record |
| `exceptions` | full internal IR and provider adapters are not public contracts |
| `non_goals` | approval, execution control, arbitrary-prose proof, action authenticity |

In compact profile form: `schema_version` is
`requirement-relation-prototype-charter/v0`; `repository_id` is
`semantic-guard`; public surfaces, commands, output shapes, exceptions, and
non-goals are the fields in the table above. This prototype charter does not
create a global convention outside this repository.

No new failure envelope is introduced. CLI usage errors retain argparse output
on stderr and exit code `2`; audited requirement warnings and blockers remain
JSON status values on stdout. Optional-provider absence is represented inside
relation diagnostics, not as silent success and not as a new process failure.
For that diagnostic, `code` is the stable attempt `status` such as
`unavailable` or `failed`, `message` is the bounded `reason`, structured
`details` retain provider/version fields when observed, and `hint` states the
optional installation or alternate-review action. This is an additive audit
detail, not a replacement for the existing CLI or MCP failure behavior.

## Extractor Authority

The execution order is cost-aware, but authority is monotonic and does not rise
merely because a later extractor is more complex.

| Stage | Maximum authority | May satisfy an obligation |
| --- | --- | --- |
| typed caller structure | `asserted` | yes |
| current binding structured field | field presence `asserted` | field presence only |
| scope-guarded direct relation rule | relation `asserted` | yes |
| morphology | `signal_only` | no |
| dependency parser | `candidate` | no |
| LLM reviewer | `candidate` | no |
| unresolved or disagreeing candidates | `unknown` or `conflict` | no |

Parser and LLM agreement does not promote a candidate to `asserted`. LLM
output cannot delete an existing delta, approve a requirement, or replace a
human decision.

### Ordering Decision

The originating discussion proposed morphology, then direct expression
comparison, then LLM as a fallback sequence. This slice separates execution
cost from evidentiary authority. Scope-guarded structured/direct rules run
first because they are the only built-in assertion-capable route and need no
optional runtime. Morphology and dependency analysis run only for unresolved
material when an explicit provider is supplied; LLM candidates remain last.

Running morphology first would not remove the direct comparison: morphology is
`signal_only` and cannot satisfy a relation. A future provider may precompute
tokens before direct rules for performance, but that scheduling change cannot
raise its authority or change the common target-profile comparison stage.

## First Relation Profile

The first profile is `functional-requirement-record/v0`. It checks a bounded
subset of relations among:

- scenario actor, meaning the grammatical participant that performs the
  scenario action, not the authority or system component responsible for the
  requirement;
- scenario action or stimulus and observable response/result; this edge does
  not by itself assign implementation responsibility to the scenario actor;
- acceptance criterion and optional metric;
- verification method;
- evidence artifact.

It does not claim that every functional requirement must be written as one
sentence. A closed structured requirement record may distribute the meaning
across labeled fields as long as the relations remain explicit and traceable.

## Evidence Plan

- Unit tests for IR identity, source offsets, serialization, scope, authority,
  aggregation, relation obligations, and deltas.
- Adversarial cases for quotation, example, history, conditional adoption,
  metalinguistic mention, negative-outcome criteria, explicit absence,
  candidate agreement, and candidate conflict.
- A high-confidence verification-target mismatch fixture with two source
  excerpts.
- Python 3.11 and 3.13 regression tests.
- Fixture evaluation, doctor, compile, representative CLI/MCP runs, and fresh
  wheel installation.
- Optional Japanese NLP dependencies are assessed separately for compatibility,
  license, model/dictionary size, reproducibility, and measurable corpus value.

Local tests and fixtures are regression evidence only. They do not establish
arbitrary-document precision or recall.

## Target Acceptance Criteria

The following are target conditions for future human review. They are not
current completion claims.

- A complete structured functional requirement yields asserted core relations
  and no high-confidence mismatch delta.
- A request containing acceptance, verification, and evidence vocabulary
  without binding relations does not satisfy those relations by vocabulary
  alone.
- A verification method that explicitly targets a different concern from the
  acceptance criterion yields a traceable
  `req.relation.verification_target_mismatch` finding.
- A concrete negative-outcome criterion remains asserted with negative
  polarity; it is not confused with an absent criterion.
- Quoted, example, historical, conditional-adoption, and metalinguistic
  occurrences do not satisfy a current binding relation.
- Morphology produces signals only; dependency and LLM routes produce
  candidates only.
- Unknowns and conflicts remain visible and never become implicit success.
- Every public mismatch finding identifies the rule and at least two relevant
  source excerpts.
- Existing CLI/MCP arguments, defaults, common result envelope, and logical
  trace version remain compatible.

## Rejection Conditions

Request revision if any of the following occurs:

- lexical occurrence alone satisfies a relation;
- a parser or LLM candidate becomes asserted without an independently
  assertion-capable source;
- a mismatch finding lacks both criterion and verification evidence;
- historical or quoted content overrides an explicit current state;
- optional NLP absence changes a deterministic result into a silent pass;
- a new required dependency or public surface is introduced without a separate
  compatibility and contract basis;
- fixture passage is described as broad natural-language understanding.

## Hollow Success Conditions

- A graph-shaped artifact exists but edges are created from adjacent words
  without scope or source evidence.
- More extractors run, but their authority and disagreements are hidden.
- The prototype reports more findings while failing to distinguish mismatch
  from unknown extraction.
- Morphological analysis is presented as dependency or semantic proof.
- LLM review becomes an approval route.
- Relation audit remains an isolated report that cannot point an agent to the
  specific requirement relation needing repair.

## LLM Dependency

The deterministic audit does not require an LLM. The first slice may prepare a
schema-bounded candidate request or use the existing reviewer route for
unresolved material, but automatic execution is not part of deterministic
`audit-request`. LLM material remains a supplement with candidate-only
authority.

## Promotion Criteria

Promote the sidecar relation audit deeper into the core only after:

- adversarial and holdout evidence shows value beyond existing field checks;
- false-positive and false-satisfaction costs are reviewed separately;
- relation-profile applicability and counterconditions are explicit;
- optional analyzer absence and failure behavior are deterministic;
- output identities and versioning are stable enough for a public-contract
  audit;
- the human reviewer accepts the residual-risk statement.

## Rollback Or Disposal

Keep extraction and relation comparison in new internal modules. Integration
with `audit-request` must be additive and removable without changing existing
function signatures or `logical-trace/v1`. If the prototype is rejected, remove
the additive summary/finding integration and retain the dated evidence record
for design history.

## Open Decisions

- Holdout corpus size and domain balance.
- Which dependency provider, if any, earns promotion after compatibility and
  accuracy testing.
- Whether a future full IR becomes public or remains diagnostic-only.
- Whether LLM relation candidates need a dedicated asynchronous tool rather
  than the existing reviewer route.
- How relation profiles expand from functional requirements to quality,
  interface, safety, transition, planning, action, and completion claims.

These decisions do not block the bounded deterministic first slice. They block
claims of generality and later public-contract expansion.

## Record Applicability And Evidence State

This Markdown charter is a dated design and implementation-control document,
not an append-only operational record. Its evidence source is the local
`semantic-guard` worktree inspected on 2026-07-12. Statements about current
code and completed command results must be recorded as observed facts in the
later implementation record; architecture effects remain hypotheses until
tested; analyzer promotion, public full-IR exposure, and final acceptance remain
pending decisions owned by the human reviewer.

Evidence-state vocabulary is `observed fact`, `inference`, `hypothesis`,
`unknown`, and `pending decision`. This charter contains hypotheses and target
conditions; the later implementation record must name command sources for
observed facts. The recorded timestamp above supplies time and timezone; no
acceptance decision has yet been made.
