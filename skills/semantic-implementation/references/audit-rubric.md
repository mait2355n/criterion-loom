# Semantic Implementation Audit Rubric

## Audience And Use

This rubric is for maintainers reviewing `semantic-guard` audit behavior and
for Codex runs that need a compact checklist behind the
`semantic-implementation` skill.

Use it to shape local heuristic checks, review prompts, fixture labels, and
human-readable audit explanations. It is not an external certification basis.

## Scope And Limits

The standards and bodies named below are conceptual references only. This file
does not claim conformance, compliance, safety certification, security
certification, or release readiness.

The rubric should keep audits inspectable and lightweight. When a task needs a
formal standard-specific review, legal review, safety review, or security
assessment, use the appropriate specialist process outside this tool.

## Quick Check

For ordinary work, keep the review to the smallest useful slice:

```sh
uv run --python 3.13 --project . semantic-guard audit-request --kind document --file README.md
uv run --python 3.13 --project . semantic-guard audit-plan --file plan.md
uv run --python 3.13 --project . semantic-guard finish-check --text "..." --evidence "..."
```

## Foundations

Use these sources as the conceptual basis without copying their full process burden:

- ISO/IEC/IEEE 29148: requirements engineering processes, information items, and requirement quality.
- IIBA/BABOK: business, stakeholder, solution, non-functional, and transition requirements; traceability and change impact.
- NASA Systems Engineering Handbook: stakeholder expectations, technical requirements, decomposition, verification, validation, technical planning, risk, and assessment.
- PMBOK and ISO 21502: value, governance, scope, schedule, resources, stakeholders, risk, quality, change, and tailoring.
- ISO/IEC 25010: product quality characteristics for specifying and evaluating quality.
- ISO/IEC/IEEE 12207 and SWEBOK: software life cycle, requirements, architecture, design, construction, testing, maintenance, configuration, quality, security, and operations.
- OWASP, NIST SSDF, CWE, and language secure-coding standards: security-review vocabulary, risk prompts, and vulnerability categories.

## Target Understanding

Score each item from 0 to 4:

- 0 absent: not addressed.
- 1 inferred: guessed from context.
- 2 partial: partly stated but incomplete.
- 3 explicit: clearly stated.
- 4 verified: backed by artifact, command, source, or user confirmation.

Block high-impact work when these are below 2:

- `purpose`
- `desired_state`
- `non_goals`
- `unknowns`
- `validation_route`

Items:

- `subject_identity`: what the target is; separate name, entity, display, identifier, and storage.
- `stakeholders`: who or what the work serves.
- `current_state`: observed starting condition.
- `desired_state`: fulfilled condition.
- `meaning`: structural, semantic, or canonical facts to preserve.
- `intent`: why the change is requested.
- `value`: what changes when fulfilled.
- `constraints`: technical, operational, creative, legal, ethical, time, or permission constraints.
- `non_goals`: excluded work and forbidden expansions.
- `assumptions`: checked versus inferred assumptions.
- `unknowns`: undecided, hypothesis, pending decision, one-sided observation, time-dependent fact.
- `conflicts`: competing goals, requirements, or constraints.
- `validation_route`: how to confirm the problem definition is fit for this task.

## Request Audit

Check individual requirements and requirement sets separately.

Individual requirement:

- `classification`: purpose, stakeholder, solution, transition, quality, operation, or non-requirement.
- `necessity`: linked to purpose, stakeholder need, constraint, risk, or value.
- `atomicity`: one requirement, one obligation.
- `clarity`: no undefined terms, ambiguous adjectives, or hidden comparatives.
- `modality`: required, optional, suggestion, constraint, example, or note.
- `solution_bias`: does not lock implementation unless the lock is meaningful.
- `feasibility`: possible within known technology, operations, time, and authority.
- `verifiability`: test, analysis, inspection, or demonstration can prove it.
- `acceptance`: fulfilled state and evidence are stated.
- `traceability`: upward to purpose and forward to design, implementation, and tests.
- `conflict`: no unresolved contradiction with other requirements.
- `priority`: importance and sequencing are justified.
- `change_state`: proposed, accepted, pending, rejected, deprecated, or conflict.

Requirement set:

- `coverage`: functional, quality, constraints, interface, operations, maintenance, exceptions, transition.
- `scope_boundary`: in-scope, out-of-scope, assumptions, and constraints separated.
- `conflict_detection`: contradictions and tradeoffs identified.
- `validation_readiness`: stakeholder or artifact can confirm the problem statement.
- `change_impact`: affected requirements, designs, tests, docs, and operations.

## Plan Audit

Check whether the plan can safely satisfy the request.

- `objective_fit`: plan serves the stated purpose and value.
- `scope_control`: target, exclusions, unchanged behavior, and forbidden edits are visible.
- `deliverables`: outputs are inspectable.
- `work_breakdown`: discovery, design, implementation, tests, documentation, migration, and cleanup are covered when relevant.
- `dependency_order`: sequencing and parallelizable work are sound.
- `assumption_checks`: risky assumptions are verified before dependent work.
- `risk_register`: risk, trigger, impact, mitigation, fallback, and owner or decision point.
- `verification_plan`: proof that the built thing meets requirements.
- `validation_plan`: proof that the result solves the right problem.
- `decision_points`: user decisions are requested only when necessary.
- `change_control`: replanning conditions and record trail are explicit.
- `rollback_recovery`: restore, fallback, or containment path exists.
- `completion_evidence`: concrete evidence is named.

## Diff Audit

Check what the change can break.

- `intent_trace`: each material change maps to a requirement or intent.
- `design_fit`: change respects existing structure, responsibility, and boundaries.
- `meaning_preservation`: avoids confusing names, identities, identifiers, displays, storage, membership, hypotheses, and facts.
- `quality_delta`: functional suitability, reliability, maintainability, security, compatibility, performance, portability.
- `complexity_delta`: branches, state, abstractions, concurrency, error paths, and speculative generality.
- `security_delta`: input, output, authentication, authorization, secrets, crypto, logs, dependencies, configuration, CI/CD.
- `data_api_compat`: public API, persistence, migration, and compatibility.
- `test_obligation`: tests that should be added, changed, or explained.
- `doc_obligation`: README, specification, operation, configuration, and migration docs.
- `operational_risk`: monitoring, failure behavior, recovery, default values, permissions.
- `reviewability`: diff size, generated artifacts, formatting churn, naming, and context.

## Finish Check

- `tests_ran`: commands and results.
- `tests_not_ran`: missing checks and reason.
- `acceptance_evidence`: acceptance criteria mapped to proof.
- `security_evidence`: secret scan, dependency check, SAST, manual review, or reason not relevant.
- `regression_scope`: impact-based regression coverage.
- `docs_synced`: docs updated or explicitly not needed.
- `breaking_change`: compatibility, migration, and notification.
- `residual_risk`: remaining uncertainty or deferred work.
- `release_blockers`: permission, security, test, migration, or spec mismatches that should stop completion.
- `evidence_minimum`: no claim without artifact, command, or line reference when the claim matters.
