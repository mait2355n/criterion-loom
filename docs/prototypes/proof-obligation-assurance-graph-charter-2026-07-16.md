# Proof Obligation And Assurance Graph Prototype Charter

Date: 2026-07-16

Status: candidate implementation gate; human acceptance pending

Recorded at: `2026-07-16T13:16:09+09:00`

## Purpose

This charter bounds a prototype that makes every public assurance claim
replayable from typed proof obligations, subject-bound evidence, versioned
rules, and an acyclic derivation graph. It addresses a reproducible defect in
which `assurance-claim/v0` can be changed to name another subject,
proposition, rule set, evidence set, or aggregate state while the current
public validator still accepts the enclosing payload.

The prototype is not evidence that an audited requirement is correct. It is a
mechanism for rejecting assurance claims whose declared derivation cannot be
reconstructed under the stated boundary.

## Prototype Identity

- `prototype_id`: `proof-obligation-assurance-graph/v0`
- `repository_id`: `semantic-guard`
- `decision_owner`: human
- `implementation_scope`: requirement-audit assurance claims and their public
  validation path

## Hypothesis

A versioned proof-obligation profile and closed derivation graph can prevent a
public claim from becoming stronger, changing subjects, changing
propositions, substituting evidence, or inheriting authority without a
detectable contract failure. The graph succeeds only when an independent
validator can reaggregate the claim from the embedded obligation results and
reject every unclosed reference, cycle, duplicate evidence use, subject
substitution, proposition substitution, and unfulfilled required obligation.

## Origin Trace

- `OR-01`: prevents an audit result from hiding missing or contradictory
  engineering obligations.
- `OR-02`: supplies the typed, replayable, bounded derivation required for
  limited assurance of AI-agent work.
- `OR-03`: gives agents and humans a located reason for revision instead of an
  opaque pass/fail label.
- Invariants 1-4 and 9-13: pass is not acceptance; lexical or structural
  completeness is not action proof; missing evidence remains unproved.
- Invariant 14: this graph audits claims; it does not execute work, grant
  authority, prioritize tasks, or accept results.

## Essential Realization

The goal is not to add a graph-shaped document. The goal is this closed chain:

```text
subject snapshot
  -> versioned claim profile
  -> required proof obligations
  -> versioned rules and located evidence
  -> typed derivation nodes and edges
  -> independently reaggregated bounded claim
  -> explicit unproved scope, challenge, or invalidity when closure fails
```

## Input And Output Boundary

The first implementation keeps `assurance-claim/v0` available and strengthens
its runtime cross-field validation without changing its shape. A separate
`assurance-claim/v1` is introduced as an opt-in sibling contract; `v0` is not
silently reinterpreted as `v1`.

The v1 claim must include:

- one subject snapshot and digest;
- one versioned claim-profile reference;
- the exact basis obligation results;
- required proof-obligation results;
- typed subject, proposition, rule, evidence, obligation-result, aggregation,
  and claim nodes;
- typed derivation edges and one root;
- explicit coverage, holds, counterevidence, unproved scope, trust
  assumptions, and residual risks.

Any default-output switch, v0 retirement date, assurance-level policy, trust
root, signature mechanism, or formal-proof claim requires a separate human
decision and migration record.

## Evidence Plan

- Preserve the current valid public payload as a positive compatibility case.
- Reject unrelated `subject_ref` substitution.
- Reject proposition substitution.
- Reject empty rule and trust-assumption sets for terminal derived claims.
- Reject unresolved or substituted evidence references.
- Reject aggregate state that disagrees with basis obligation results.
- Reject cycles, duplicate node identities, duplicate evidence accounting,
  missing graph endpoints, and authority effects without a valid basis.
- Keep provider and LLM candidates incapable of satisfying a proof obligation
  by themselves.
- Run the complete vNext test suite, schema validation, CLI/MCP schema smoke,
  and an isolated wheel smoke before claiming local integration.

Local passage is regression evidence only. It is not action authenticity,
field validity, operational qualification, or human acceptance.

## Target Acceptance Criteria

- A generated v1 claim validates and independently reaggregates to the same
  outcome, finality, challenge, coverage, holds, and evidence closure.
- Each required proof obligation has exactly one result.
- Every graph reference resolves to one typed node and the graph is acyclic.
- The claim subject, scope, proposition, rules, and evidence are bound to the
  same audit observation and source snapshot.
- A required unfulfilled proof obligation prevents terminal satisfaction.
- v0 default behavior remains available until a separate migration decision.
- Public output continues to state that audit disposition is not human
  acceptance.

## Rejection And Hollow-Success Conditions

Request revision if any of the following is possible:

- changing claim meaning while preserving schema validity;
- signing or hashing a graph whose semantic endpoints are unbound;
- deriving a terminal claim from empty rules or unresolved evidence;
- letting a candidate parser or LLM node inherit support authority;
- counting the same evidence multiple times as independent corroboration;
- presenting graph closure as proof that an action occurred;
- replacing v0 silently or declaring v1 accepted without migration evidence.

## LLM Dependency

None is required. LLM output may appear only as candidate evidence with its
existing authority ceiling and cannot close a proof obligation without an
independent versioned rule that is authorized to do so.

## Promotion Criteria

- All mutation and graph-closure tests pass.
- The v1 schema, builder, validator, CLI/MCP opt-in surface, and package data
  are versioned and migration-tested.
- A fresh, digest-bound execution record identifies the tested source set.
- Independent review finds no subject, authority, evidence, or aggregation
  bypass in the bounded requirement slice.
- The human reviewer accepts or revises the residual-risk and migration
  policy.

## Rollback Or Disposal

Keep v1 in separate schema and implementation modules. If rejected, remove
the opt-in v1 surface and retain the adversarial tests and defect record.
Strengthened v0 semantic checks may remain only if existing valid v0 payloads
continue to validate and the change is documented as a validator correction.

## Open Decisions

- Human adoption of the assurance-level and trust-basis profile.
- Whether and when v1 becomes the default public claim.
- v0 support and retirement period.
- Which profiles require independent observation, signatures, trusted time,
  or a formal verifier.

