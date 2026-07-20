# Verification Register Completeness Prototype Charter

Date: 2026-07-16

Status: candidate implementation gate; human acceptance pending

Recorded at: `2026-07-16T13:16:09+09:00`

## Purpose

This charter bounds a completeness check for the verification register. Its
job is to prevent known unproved scope, remaining obligations, measured
hazards, transition prohibitions, and independent-review findings from
disappearing outside the canonical verification denominator.

It does not claim that unknown unknowns can be completely enumerated.

## Prototype Identity

- `prototype_id`: `verification-register-completeness/v0`
- `repository_id`: `semantic-guard`
- `decision_owner`: human
- `implementation_scope`: the vNext verification source, its unresolved
  families, typed resolution obligations, and readable projections

## Hypothesis

Every declared gap-bearing item can be assigned a stable identity and exactly
one inspectable disposition: canonical unresolved, evidence-backed resolved,
human-adopted non-applicable, or handed off to an external control plane. A
validator can reject missing, duplicate, contradictory, or dangling
dispositions without deciding priority or risk acceptance.

## Origin Trace

- `OR-01`: preserves omissions, uncertainty, and evidence gaps across all
  declared lifecycle and engineering concerns.
- `OR-02`: prevents unproved ranges and unresolved proof obligations from
  vanishing from a bounded assurance claim.
- `OR-03`: keeps unresolved material connected to revision or human decision
  material.
- Invariants 4-6 and 11-14: pass is bounded, local fixtures are not field
  validity, unresolved evidence does not become success, control ownership
  remains external.

## Essential Realization

The goal is not a larger checklist. It is the invariant that every declared
gap remains recoverable and cannot be omitted from completion material without
typed evidence or an authorized disposition.

## Register Denominator

The first version covers:

- `verification_items[].unproven_scope`;
- `verification_items[].residual_risks`;
- `implementation_conformance_items[].remaining_obligations`;
- unresolved resolution obligations and independent-review findings;
- declared transition or cutover prohibitions;
- measured hazards and unresolved field-evaluation outcomes.

Each entry must have a stable ID, exact source locator, kind, disposition,
subject reference, and the corresponding unresolved, resolution evidence,
human decision, or external handoff reference.

## Evidence Plan

- Reject one removed registration for a still-declared gap.
- Reject a locator that resolves to no source value.
- Reject duplicate or contradictory dispositions.
- Reject `resolved` without located evidence and completion assessment.
- Reject `not_applicable` without a versioned human decision and reactivation
  conditions.
- Reject `control_plane_handoff` without a stable handoff identity while
  preserving the audit gap as unresolved inside semantic-guard.
- Demonstrate that local internal consistency does not imply field validity or
  human acceptance.

## Target Acceptance Criteria

- Every item in the declared denominator has exactly one valid disposition.
- Every canonical unresolved reference closes to an unresolved family and
  typed resolution path.
- Evidence-backed resolution names the subject, evidence, assessor, time, and
  completion rule.
- Human non-applicability records include scope and re-evaluation triggers.
- Handoff never deletes the audit-side uncertainty.
- Projection generation or comparison exposes every registered ID.

## Rejection And Hollow-Success Conditions

- Counting strings without stable identity and source location.
- Declaring completeness because the current register validates against its
  own incomplete denominator.
- Treating handoff, deferral, or lack of implementation as resolution.
- Making semantic-guard own priority, scheduling, risk acceptance, or final
  acceptance.
- Claiming complete discovery of unknown unknowns.

## Promotion Criteria

- Negative omission and contradiction tests pass.
- The register denominator and disposition vocabulary receive independent
  review.
- The human reviewer accepts the bounded completeness meaning.
- The readable projection is generated or value-compared from the canonical
  source.

## Rollback Or Disposal

Keep the completeness model additive and versioned. If the first denominator
is rejected, retain the defect inventory and remove only the rejected
disposition contract; do not rewrite known gaps out of history.

## Open Decisions

- Human acceptance of the exact denominator and non-applicability policy.
- Whether control-plane handoffs are linked by locator only or imported from
  an append-only ledger.
- Whether readable projections are generated or fully value-compared.

