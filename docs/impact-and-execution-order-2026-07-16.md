# vNext Impact Analysis And Execution Order

Recorded at: `2026-07-16T13:16:09+09:00`

Status: implementation order adopted by the working agent; human final
acceptance remains pending

## Decision Frame

The ordering was evaluated against six dimensions on a five-point scale:

- origin-purpose contribution;
- prevention of false satisfaction or silent omission;
- contribution to replayable bounded assurance;
- prerequisite value for later work;
- practical-deployment impact;
- human-decision dependency, where a high number means implementation cannot
  close the item without a human policy choice.

Scores guide ordering but do not replace dependency constraints or human
judgment.

## Impact Comparison

| Work item | Origin | False satisfaction | Assurance | Prerequisite | Practical use | Human dependency | Main consequence if delayed |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Verification-register completeness | 5 | 5 | 4 | 5 | 4 | 3 | Known gaps can remain outside the denominator and later completion claims |
| Proof-obligation and assurance-graph closure | 5 | 5 | 5 | 5 | 4 | A public claim can change subject, proposition, rules, evidence, or state and still validate |
| Unresolved routing contract and obligation reassessment | 5 | 5 | 4 | 5 | 5 | Direct-rule false satisfaction and unresolved results survive later analysis unchanged |
| Engineering rule-pack governance | 5 | 5 | 4 | 5 | 5 | The system can precisely compare against an ungoverned or wrong normative model |
| State derivation and subject-snapshot binding | 5 | 5 | 5 | 5 | 4 | Evidence and state may be internally consistent but belong to another or stale subject |
| Lifecycle trace and composition | 5 | 4 | 5 | 4 | 5 | Ten separate surfaces can exist while meaning changes silently between them |
| Action-evidence and assurance profile | 5 | 5 | 5 | 4 | 5 | Descriptions of actions can be mistaken for occurrence, authority, provenance, or authenticity |
| Human operational use | 4 | 3 | 3 | 3 | 5 | Correct audit material may not reach the responsible human or agent in usable form |
| Field population, costs, thresholds, and ablation | 5 | 5 | 4 | 4 | 5 | Local fixtures can be mistaken for practical accuracy; extractor value remains unknown |
| Repair-loop effect | 4 | 3 | 3 | 3 | 5 | Findings may produce wording churn without reducing defects or regressions |
| Operational qualification | 3 | 3 | 4 | 3 | 5 | A locally correct mechanism can fail under duration, concurrency, load, or recovery |
| Transition, cutover, rollback, and retirement | 3 | 2 | 3 | 2 | 5 | An unqualified sidecar can be made default or become difficult to withdraw |
| Projection value equivalence | 3 | 3 | 3 | 2 | 3 | Human-readable material can drift from the canonical source |

## Comparison With The Previous Order

The previous order was:

1. proof-obligation and assurance graph;
2. state derivation and subject binding;
3. action evidence;
4. lifecycle trace and vertical surfaces;
5. repair loop and human material;
6. field evaluation;
7. operational qualification and transition.

That sequence preserved the main dependency direction but omitted two facts
now demonstrated by current code and adversarial probes:

1. the new denominator itself is not yet registered completely;
2. the direct-rule path can terminally satisfy a reversed grammatical role,
   while later parser candidates cannot reassess the unresolved obligation.

Building only the assurance graph first would therefore risk producing a
stronger record of a semantically wrong direct decision. Conversely, changing
the detector first without recording its route and proof basis would leave the
new result difficult to audit. The two concerns must share the first priority
band.

## Adopted Execution Order

### P0-A — Fix the denominator before claiming progress

1. Add the six missing verification concerns and their unresolved families:
   proof-graph soundness, register completeness, lifecycle trace/composition,
   operational qualification, transition/cutover, and human operational use.
2. Add stable unresolved entries for morphology ablation, coreference and
   dependency accuracy, lifting expansion, and LLM incremental value; these
   currently appear only as free remaining-obligation text.
3. Correct dependency edges so field evaluation cannot run before an accepted
   engineering basis, subject binding, secure-use boundary, and evaluation
   policy.

### P0-B — Close current false-assurance paths

4. Add a versioned unresolved-route and stage-plan contract.
5. Strengthen v0 cross-field validation for claim subject, proposition, rule,
   evidence, aggregate state, and human-authority combinations.
6. Implement opt-in `assurance-claim/v1` with typed proof obligations and an
   acyclic derivation graph, leaving v0 available.
7. Add a narrow, versioned `performs` and `acts_on` reassessment path that
   consumes candidate evidence without granting providers assertion authority.

### P1 — Make derivation and normative meaning inspectable

8. Implement state-assessment records, closed subject manifests, route traces,
   and evidence expiry/requalification mechanics.
9. Construct engineering rule-pack mappings with source version, clause
   locator, interpretation, applicability, counterconditions, limitations,
   adoption state, and review triggers. Independent review and human adoption
   remain explicit gates.
10. Make the morphology/dependency relationship truthful: either verified
    token consumption or explicitly independent analyzers. Add reason-driven
    capability accounting and explicit LLM unavailable/skipped observations.

### P2 — Expand across lifecycle and action claims

11. Define and obtain human acceptance for each missing lifecycle profile.
12. Implement typed cross-stage trace and composition before treating separate
    surface implementations as OR-01 completion.
13. Implement action evidence only inside an accepted assurance and threat
    profile; do not infer occurrence from descriptions.
14. Implement repair/re-audit and responsibility-correct decision material for
    coding agents and humans.

### P3 — Establish practical validity and safe adoption

15. Fix intended population, catastrophic-error costs, abstention policy, and
    thresholds; then run independently labelled holdout and extractor ablation.
16. Evaluate repair effect and human comprehension.
17. Close secure-operation applicability, operational qualification,
    requalification, cutover, rollback, and retirement evidence.
18. Generate or fully value-compare the readable projection.

## Immediate Acceptance And Stop Rules

- No item is marked complete from file presence or local test passage alone.
- Human-required obligations remain pending until a located human decision is
  available.
- External-evidence obligations remain pending until independent evidence is
  available.
- A provider or LLM candidate never gains assertion or acceptance authority by
  agreement alone.
- Any discovered false satisfaction is promoted ahead of extractor expansion.
- The sidecar does not become the default path without an explicit transition
  decision and rollback evidence.

## Baseline Evidence

- vNext unit suite before edits: `198 tests`, all passed.
- Verification-source internal validator before edits: all five checks passed;
  `11` verification items, `27` conformance items, `10` unresolved items,
  `28` resolution obligations, and `12` resolution paths.
- Adversarial public-contract probes accepted subject, proposition, rule,
  evidence, and claim-state substitutions.
- A role-reversal requirement passed the direct conditional path even though
  real dependency analysis identified the declared actor as the grammatical
  object and raised a conflict.

These observations justify the order. They do not establish field accuracy,
action authenticity, operational readiness, or human acceptance.

## Execution Result

The adopted dependency order was retained, with one deliberate pre-emption:
every reproducible false satisfaction or fail-open condition discovered during
independent review was moved ahead of the next feature band. This was not a
change of purpose. It applied the stated stop rule that an apparently stronger
feature is harmful when its positive result can be manufactured from the wrong
subject, stale policy, self-report, omitted denominator, or unbounded input.

| Band | Implemented result | What remains outside the result |
| --- | --- | --- |
| P0-A | Canonical register expanded to 17 verification items, 17 unresolved families, 52 resolution obligations, 19 resolution paths, and a 65-gap append-only register; deterministic full-value projection added | Human acceptance and external observations do not arise from register closure |
| P0-B | Versioned route/stage records, reason-driven capability accounting, narrow `performs`/`acts_on` reassessment, v0 cross-field replay restrictions, and an opt-in v1 proof-obligation graph | General dependency understanding and assertion authority for parsers or LLMs remain excluded |
| P1 | Bound subject/state assessment, evidence expiry and requalification, candidate engineering rule pack, independent analyzer accounting, and lifecycle profile registry | Rule-pack and ten lifecycle profiles remain candidate-only; public resolver and workflow integration remain absent |
| P2 | Typed lifecycle trace, seven-class action assurance, responsibility-bound repair/re-audit, and human/agent decision material | Runtime occurrence, identity, signatures, trusted time, real repair execution, and human acceptance remain external |
| P3 local contract | Field evaluation, repair/human outcome evaluation, secure-operation boundary, 12-scenario operational qualification, transition/rollback/retirement gates, and exact readable projection | Real holdout, real participants, operational runs, external authenticity, cutover evidence, and retirement decisions remain unperformed |

Independent adversarial review materially changed several local contracts. It
closed reusable human-decision records after policy changes, arbitrary state
axis promotion, self-declared repair effects, stale secure-operation decisions,
self-observation laundering, omitted participant denominators, pseudo-
replication, arm/material substitution, and unbounded structural traversal.
The resulting positive states remain deliberately weak: they describe internal
consistency or conformance of supplied records, not real-world truth.

This implementation therefore completes the locally executable contract work
in the adopted order, but it does not complete practical validation, external
action proof, organizational adoption, or default-path transition. Those are
evidence-producing activities and human decisions, not missing Boolean flags.

## Final Local Verification

- `569` unit and contract tests passed.
- `35` JSON records passed duplicate-key parsing; `27` Draft 2020-12 schemas
  passed schema self-validation.
- Ruff, `compileall`, dependency-lock checking, the canonical verification
  validator, the exact projection check, and the engineering rule-pack
  validator passed.
- A built wheel passed the isolated packaged-contract verifier with `23`
  schema surfaces, `10` lifecycle profiles, `11` engineering rules, the real
  CLI entry point, and adjacent-resource decoys. Its SHA-256 was
  `f4289463fe7b25556778da797f01642440b828b6185d265f575bae60752cf938`.
- Real Sudachi/GiNZA execution preserved the missing coreference capability as
  `partial`, preserved the absent LLM bundle as `not_configured`, and produced
  `block` rather than silent success.

The durable observation is
`validation/local-contract-verification-2026-07-16.json`. It deliberately
declares its evidence freshness `unbound`: it is not a substitute for a closed
current subject manifest, field evidence, external authenticity, independent
operational observation, or human acceptance.
