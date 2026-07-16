---
name: semantic-implementation
description: Route non-trivial development work through semantic-guard v1 requirement-relation audits while preserving intent, engineering basis, uncertainty, provenance, authority ceilings, compatibility boundaries, and final human judgment. Use when Codex clarifies or audits a structured functional requirement, compares canonical v1 with the frozen 0.1.0 behavior, retrieves semantic-guard schemas, or works on design, implementation, migration, documentation, public contracts, durable evidence, and completion claims whose meaning could drift. Do not claim that v1 directly audits plans, diffs, finish evidence, or every lifecycle phase.
---

# Semantic Implementation

Keep the original purpose visible: expose whether development requirements, plans, actions, realization methods, and evidence are justified by explicit engineering knowledge. Use the current v1 runtime only for the requirement-relation slice it actually implements.

Do not approve, reject, certify, accept risk, adopt policy, or make the final human decision.

## Public v1 surface

Prefer the MCP server when available:

- `audit_requirement_relations_tool`: audit one structured functional requirement.
- `shadow_compare_legacy_tool`: compare v1 with an operator-pinned external 0.1.0 execution root.
- `semantic_guard_schema_tool`: retrieve one closed v1 schema.

Use the CLI fallback from the repository root:

```sh
uv run --locked semantic-guard audit-requirement --file requirement.txt
uv run --locked semantic-guard shadow-compare \
  --file requirement.txt \
  --legacy-root /absolute/operator-owned/legacy-root \
  --require-legacy
uv run --locked semantic-guard schema audit-result
```

Read [references/mcp-contract.md](references/mcp-contract.md) when invoking or changing the public surface. Read [references/audit-rubric.md](references/audit-rubric.md) when judging requirement quality, relation coverage, evidence, or claim boundaries.

## Route the work

1. State the target, purpose, stakeholder, desired state, non-goals, constraints, unknowns, and validation route before editing.
2. Separate a functional requirement from examples, notes, plans, implementation ideas, historical statements, and acceptance decisions.
3. Give the v1 auditor one bounded requirement record at a time. Do not feed an entire plan or release note and rename the output a plan audit.
4. Retrieve the current schema when producing or consuming durable JSON.
5. Preserve every `undetermined`, `partial`, `failed`, challenge, hold, and unresolved obligation. Never coerce absence into success.
6. Map audit material into a plan, implementation change, verification step, or human question outside the audit engine. Keep that mapping explicit.
7. Record commands, exact results, checks not run, residual risks, and pending human decisions before claiming completion.

## Use the analysis chain correctly

The requirement audit proceeds through structured fields and direct rules, unresolved-obligation reassessment, optional morphology signals, optional dependency candidates, and optional caller-supplied LLM candidates.

- Treat morphology as `signal_only`.
- Treat dependency and LLM results as `candidate_only`.
- Require source digest, spans, provider identity, resource version, requested and fulfilled capabilities, and coverage where the contract calls for them.
- Do not let analyzer agreement create support, apply a hold, release a hold, or decide acceptance.
- Use `analysis_mode="assurance"` by default.
- Use `conditional` only when deliberately evaluating the unresolved gate; it is not a proven safe shortcut for practical-domain recall.
- Use `shadow_all` for observation without granting analyzer decision authority.

When submitting LLM candidates, retrieve `llm-candidate-input`, bind the candidate bundle to the exact input digest and source spans, and treat it as untrusted candidate material. The audit core does not call a particular model API.

## Interpret the result

Keep these axes separate:

- outcome: `satisfied`, `refuted`, `undetermined`, `not_applicable`, `invalid`;
- finality: `provisional`, `terminal`, `invalid`;
- challenge: `none`, `open`, `conflict`;
- coverage: `complete`, `partial`, `not_evaluated`, `failed`;
- workflow disposition: `pass`, `warn`, `block`.

Treat `pass` only as “the selected versioned audit policy does not stop this workflow.” It is not correctness probability, field validation, security approval, human acceptance, policy adoption, or proof that an external AI action occurred.

## Handle unsupported lifecycle work

For plans, diffs, completion evidence, conventions, reviewer material, and other lifecycle phases:

1. Perform ordinary engineering analysis and identify the requirement relations that can be audited by v1.
2. Mark the rest as not integrated into the canonical v1 workflow.
3. Use the frozen 0.1.0 implementation only when its historical heuristic is explicitly requested or materially useful.
4. Label every old result with the legacy version and never present it as v1 output or current truth.

The frozen source lives at `legacy/semantic-guard-v0.1.0/` in the repository. Running it is an explicit compatibility action, not a transparent fallback. Repository source preservation alone does not satisfy the trust-root requirements of v1 `shadow-compare`.

## Preserve decision ownership

Keep these decisions outside the audit engine:

- accepting, revising, deferring, or rejecting the work;
- accepting residual risk;
- adopting an engineering rule pack or lifecycle profile;
- authorizing external or irreversible action;
- switching an operational default;
- retiring a predecessor deployment.

Record an unresolved item with an owner, needed-for target, blocking state, next action, evidence reference, and resolution condition when it affects correctness or authority.

## Close the task

Before reporting completion:

- trace each material change to the purpose or requirement;
- verify affected schemas, CLI, MCP, packaging, migration, documentation, and archive boundaries;
- run the relevant tests and validators;
- distinguish current observations from dated historical evidence;
- state field validity, external authenticity, human adoption, and operational qualification as unestablished unless separately evidenced;
- leave final human acceptance pending until the human decides.
