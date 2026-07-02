---
name: semantic-implementation
description: Meaning-first routing and audit guidance for Codex work using semantic-guard / Criterion Loom. Use when Codex works on non-trivial design, implementation, refactoring, migration, documentation, creative canon organization, requirement clarification, public contract or tool-interface changes, durable evidence, completion evidence, or document wording where meaning, intent, scope, non-goals, uncertainty, verification, validation, traceability, final human acceptance, or change impact may be misunderstood. Do not use for trivial typo fixes, simple one-line commands, current time checks, or already-obvious mechanical edits.
---

# Loom Guide

## Purpose

Use this skill to keep implementation from becoming shape-matching. Clarify what must be preserved, why it matters, what is not being done, and how the result can be verified before changing files.

This skill is the routing layer. The deterministic audit core stays in `semantic-guard`; the skill decides when and how Codex should call the MCP tools or CLI fallback. It does not approve, reject, certify, or make final human acceptance decisions.

Detailed CLI, MCP, schema, error, and durable-record contracts live in `references/mcp-contract.md`, whose repository profile is `semantic-guard-mcp-cli-contract/v1`. Do not restate that contract here except for routing rules.

## Operating Rule

Use the lightest audit that protects the task.

- For open-ended ideas that are not yet requirements, run exploration first: use deterministic exploration for fast preflight, and use LLM exploration when the task needs an isolated reviewer to extract visible facts from the supplied request/context, return schema-valid exploration JSON, and list material questions without claiming completeness.
- For ambiguous or high-impact work, run the full chain: exploration when needed, target understanding, request audit, plan audit, diff audit, finish check.
- For ordinary code changes, at least identify meaning, intent, non-goals, risk, and verification before editing.
- For small obvious edits, keep the audit implicit and do not perform ritual paperwork.
- If the `semantic-guard` MCP server is available, prefer it for structured audits.
- If the MCP server is unavailable but a `semantic-guard` checkout is available, run the CLI from the checkout root with `uv run --python 3.13 --project . semantic-guard ...`, or set `SG_PROJECT=/absolute/path/to/semantic-guard` and use `--project "$SG_PROJECT"`.
- Before relying on a fresh checkout or publication snapshot as the audit source, run `semantic-guard doctor`.
- Use `audit-decision-state` when the important question is what is decided, unknown, hypothetical, inferred, value-laden, or waiting on a human decision.
- When auditing prose rather than a requirement statement, pass `--kind document` or MCP `kind="document"` to avoid requirement-only warnings.
- When a task adds or changes public I/O, CLI behavior, MCP tools, API responses, durable records, error handling, output schemas, or repository-wide coding conventions, run `audit_conventions_tool` or CLI `audit-conventions` before closing the implementation.
- For README, release notes, handoff docs, public positioning, or explanation prose, run `audit-conventions --kind document` and inspect `doc.expression.*` findings. Rule-specific checks should look at `doc.expression.*` and `details.expression_precision.referent_resolutions`, not only the top-level `status`.
- Use `trace-report` when request, plan, diff, finish evidence, or domain vocabulary need one readable traceability view.
- When changing durable records, keep the top-level recovery surface shallow: context, current_state, action, and detail_refs should be named fields or a documented equivalent, with long rationale and raw logs kept behind references.
- Use severity profiles when context matters: `exploratory` for early sketches, `dogfood` for local iteration, `release` for publication or configuration-sensitive work, and `safety` for high-risk surfaces.
- Use LLM reviewer only as intermediate audit material. It may point out missing aspects and supplements; it must not approve, reject, or decide final acceptance.
- Use `llm_review_run_tool` or `llm-review-run` in dry-run mode first. Use `execute=true` or `--execute` only when the extra review value justifies the cost, latency, and risk.
- When an MCP reviewer call may take long enough that status matters, prefer `llm_review_start_tool` or `review_if_needed_start_tool`, then poll `llm_review_status_tool` until the job is no longer `running`.
- For final human acceptance, build an `acceptance_review_bundle`. Keep `final_human_decision.status` as `pending` unless the human has actually decided.

## Audit Chain

### 0. Explore Request

Use this before requirements exist, especially for product ideas, feature sketches, broad documentation requests, creative canon organization, or any task where asking the wrong questions would quietly fix the wrong scope.

- Generate plausible audience or stakeholder hypotheses and state how each would change scope.
- For deeper elicitation, use the LLM exploration path so the reviewer classifies visible facts, inferences, hypotheses, unknowns, and pending decisions from the supplied request/context before questioning gaps. Treat the result as schema-valid elicitation material, not complete extraction.
- Extract only material ambiguities: scope, data shape, identity, privacy, payment, permissions, external authority, acceptance evidence, unresolved human decisions.
- Ask only questions whose answers would change the artifact or audit path.
- Keep taste, wording, and implementation-preference questions out unless they affect scope, public contracts, evidence, or risk.
- Produce a spec outline with non-goals, acceptance criteria, unresolved decisions, and next design or planning phase.
- Do not start implementation from this phase.

Use MCP `explore_request_tool` or CLI `semantic-guard explore-request` for fast deterministic preflight. Use MCP `llm_explore_request_tool` or CLI `semantic-guard llm-explore-request --execute` when the point is to ask an isolated reviewer to extract visible information from the supplied request/context, return schema-valid exploration JSON, and list material questions. Treat both outputs as elicitation material, not approval, completeness proof, or a final requirement.

### 1. Understand Target

Confirm that the object of work is understood before refining requirements.

- What is the subject: entity, module, document, feature, setting, or story fact.
- Who or what the work serves: user, maintainer, operator, author, reader, character, system.
- What is the current state and desired state.
- What meaning, intent, and value must be preserved.
- What constraints, non-goals, assumptions, and unknowns exist.
- How the user or artifact will prove that the problem itself is the right one.

Block implementation when purpose, desired state, non-goals, unknowns, or validation route are absent or only guessed for high-impact work.

### 2. Audit Request

Separate need from solution.

- Classify requirements as purpose, stakeholder, solution, transition, quality, operation, or non-requirement.
- Check clarity, atomicity, feasibility, necessity, priority, verifiability, acceptance criteria, and traceability.
- Mark undecided points as unknown, hypothesis, pending decision, one-sided observation, or time-dependent fact.
- Do not turn examples, implementation ideas, or storage layout into requirements unless the user or artifact makes them binding.

Use `audit-decision-state` beside request audit when decisions, ownership, evidence gaps, or uncertainty state matter more than requirement wording. Treat its management handoff items as record material, not as the decision itself. When those items are carried forward, preserve known owner, needed-for context, blocking status, next action, review timing, and whether the source is fact, inference, hypothesis, unknown, or pending decision.

### 3. Audit Plan

Check that the plan can satisfy the requirement without expanding the scope.

- State objective, non-goals, deliverables, work breakdown, dependencies, assumptions, risks, decision points, verification, validation, rollback, and completion evidence.
- Include documentation, migration, tests, generated files, and configuration when affected.
- When adding dependencies, abstractions, layers, wrappers, schemas, or adapters, state why existing or standard capabilities are insufficient and what should stay unbuilt.
- Identify user decisions only when required for correctness or permission.

### 4. Audit Diff

After editing, inspect the change as a possible meaning break.

- Trace each material change to a requirement or intent.
- Check semantic preservation: name versus identity, display versus identifier, storage versus membership, hypothesis versus fact.
- Check quality impact: functional suitability, reliability, maintainability, security, compatibility, performance, portability.
- Check complexity growth, public API, persistence, permissions, configuration, dependencies, operations, and documentation impact.

### 5. Finish Check

Do not close on "implemented" alone.

- Record commands run, tests not run, and reasons.
- Map acceptance criteria to evidence.
- Note residual risk, blockers, breaking changes, migration needs, and follow-up work.
- Prefer concrete evidence: file path, line, command, result, screenshot, or rendered artifact.

Use `trace-report` when the final explanation needs to connect request, plan, diff, finish evidence, and vocabulary without re-reading every audit output.

## Document And Convention Audits

Use `audit-conventions` for public I/O and documentation-contract work:

- Use `--kind document` for explanatory prose, READMEs, release handoffs, public positioning, and skill instructions.
- Treat `conv.*` findings as output-contract and repository-profile guidance.
- Treat `doc.expression.*` findings as recall-oriented wording diagnostics for vague targets, operations, output forms, utility claims, decision actors, revision targets, mapping contracts, capability contracts, and unclear demonstrative references.
- For demonstratives such as `this`, `that`, `これ`, or `それ`, read `details.expression_precision.referent_resolutions`; `supported` usually means the nearby referent was recoverable, while `ambiguous` or `no_candidate` deserves review.
- Do not use document-expression findings as a style lint, prohibition on demonstratives, proof of natural-language correctness, or final publication approval.

## LLM Reviewer

Use the LLM reviewer when deterministic audit is not enough to inspect context, weak assumptions, counter-conditions, rule item coverage, or missing supplements.

Good triggers:

- Requirements are ambiguous, high-impact, or likely to hide non-goals or acceptance gaps.
- A plan is large enough that dependency order, risk, rollback, or validation may be incomplete.
- A diff touches meaning, identity, storage, permissions, security-sensitive configuration, persistence, or public behavior.
- Finish evidence exists, but residual risk or acceptance mapping is still thin.
- You need a second, isolated reviewer before producing final human-review material.
- You need a fresh-eyes pass because the same context planned, implemented, and checked the work.

Default flow:

1. Run the relevant deterministic audit first.
2. When routing should be inspected, use `review_if_needed_tool` or CLI `review-if-needed` with `candidate`, `phase`, `deterministic_audit`, and optional `review_context`.
3. Use `review_context.independent_review_requested` or `fresh_eyes_requested` when the value is an uncontaminated second pass rather than a deterministic warning.
4. Read `escalation.pressure.score_semantics`: it is review routing pressure, not correctness probability.
5. Dry-run the LLM reviewer first through `review_if_needed_tool`, `llm_review_command_tool`, `llm_review_run_tool` with `execute=false`, or CLI `llm-review-run --dry-run`.
6. If execution is justified and a blocking call is acceptable, run `review_if_needed_tool` with `execute=true`, `llm_review_run_tool` with `execute=true`, or CLI `llm-review-run --execute`.
7. If execution is justified and response state must be observable, run `review_if_needed_start_tool` or `llm_review_start_tool`, then poll `llm_review_status_tool`. Treat `running=true` as still waiting, `review_received=true` as valid reviewer JSON received, `state=failed` as an invalid or failed run, and `state=timed_out` as timeout.
8. Treat the result as supplement material. Decide which supplements to adopt, reject, or defer in the main Codex work.

Never use LLM reviewer output as final approval. Never auto-apply supplement proposals without checking their relation to the request, non-goals, and evidence.

## Acceptance Review Bundle

Build an `acceptance_review_bundle` when the final artifact is ready for human evaluation, especially after non-trivial implementation, migration, policy, public documentation, or creative-canon changes.

The bundle should include:

- original request.
- final artifact kind, reference, and summary.
- deterministic audits.
- LLM reviewer material when used.
- adopted, rejected, and deferred supplements.
- execution evidence.
- residual risks.
- human review points.
- `final_human_decision` with `status: pending`.

Use `acceptance_bundle_template_tool` or CLI `acceptance-bundle-template` to scaffold it. Use `validate_acceptance_bundle_tool` or CLI `validate-acceptance-bundle` before presenting it.

Human decision values are limited to `accept`, `request_revision`, and `defer`. Do not fill a final decision on the user's behalf.

## CLI Examples

When MCP tools are unavailable, use the local CLI.

```sh
uv run --python 3.13 --project . semantic-guard explore-request --text "..."
uv run --python 3.13 --project . semantic-guard llm-explore-request --text "..." --execute
uv run --python 3.13 --project . semantic-guard understand-target --text "..."
uv run --python 3.13 --project . semantic-guard audit-request --kind document --file README.md
uv run --python 3.13 --project . semantic-guard audit-decision-state --text "..."
uv run --python 3.13 --project . semantic-guard audit-plan --file plan.md
uv run --python 3.13 --project . semantic-guard audit-diff --intent "..." --file diff.txt
uv run --python 3.13 --project . semantic-guard finish-check --text "..." --evidence "..."
uv run --python 3.13 --project . semantic-guard audit-conventions --kind document --file README.md
uv run --python 3.13 --project . semantic-guard trace-report --file trace-input.json
uv run --python 3.13 --project . semantic-guard doctor
uv run --python 3.13 --project . semantic-guard audit-result-schema
uv run --python 3.13 --project . semantic-guard request-exploration-review-schema
uv run --python 3.13 --project . semantic-guard rule-detector-map
uv run --python 3.13 --project . semantic-guard conventions-catalog
uv run --python 3.13 --project . semantic-guard evaluate-fixtures
uv run --python 3.13 --project . semantic-guard llm-review-run --file review-input.json --dry-run
uv run --python 3.13 --project . semantic-guard acceptance-bundle-template --file bundle-input.json
uv run --python 3.13 --project . semantic-guard validate-acceptance-bundle --file acceptance-bundle.json
```

## References

- Read `README.md` when installing or syncing this skill into a live Codex environment.
- Read `references/audit-rubric.md` when designing or reviewing the audit model.
- Read `references/mcp-contract.md` when using or extending the `semantic-guard` MCP/CLI interface.
