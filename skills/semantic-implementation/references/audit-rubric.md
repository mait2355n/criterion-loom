# v1 requirement-relation audit rubric

## Purpose

Use this rubric to prepare and interpret one structured functional requirement for the canonical v1 auditor. It is engineering guidance, not standards certification.

## Requirement preparation

Keep these elements explicit where applicable:

- actor or responsible system;
- normative modality;
- action or state predicate;
- object and affected artifact;
- trigger or condition;
- scope and exclusions;
- acceptance target;
- verification target and method;
- evidence artifact;
- failure or rejection condition;
- source identity and stable spans;
- unresolved terms or decisions.

Do not turn examples, quotations, rejected proposals, historical statements, negated clauses, or implementation suggestions into active obligations without explicit status and scope.

## Relation checks

Inspect at least:

- actor to action;
- action to object;
- condition to governed clause;
- constraint to constrained behavior;
- acceptance target to verification target;
- evidence artifact to verified claim;
- output or state change to its producing action;
- modality, polarity, quotation, reporting, and adoption status;
- conjunction and coordination boundaries;
- unresolved coreference or attachment alternatives.

The auditor may expose only the relation families its current version implements. Missing coverage must remain visible.

## Evidence quality

Prefer direct source spans, closed records, versioned rules, reproducible commands, artifacts, and independent observations. Distinguish:

- supplied statement;
- parser signal;
- dependency candidate;
- LLM candidate;
- deterministic derivation;
- tool execution observation;
- human testimony;
- external authenticated evidence.

Agreement among weak sources does not create a stronger evidence class by itself.

## Fail-closed interpretation

Reject or preserve as unresolved when:

- required capability is missing;
- source coverage is partial;
- spans or digests do not match;
- provider output exceeds declared capability;
- active obligations have no unique result;
- support and counterevidence conflict;
- a hold lacks a versioned application or release basis;
- a rule would infer an affirmative fact from absence alone.

## Broader lifecycle boundary

The original product purpose covers requirements, plans, actions, realization methods, changes, verification, completion, and bounded action assurance. Canonical v1 exposes only the requirement-relation vertical slice. Treat plan, diff, finish, operation, and other lifecycle assessments as manual or frozen-legacy work until a corresponding v1 workflow is implemented and adopted.

## Final review

Report:

- what the v1 audit established;
- what it refuted;
- what remains undetermined or uncovered;
- which analyzer and rule versions were used;
- what was manually inferred after the audit;
- what evidence was not run or unavailable;
- what decision remains with the human owner.
