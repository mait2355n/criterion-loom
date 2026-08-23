---
name: semantic-implementation
description: Route non-trivial development work through the semantic-guard 1.1.0 requirement-relation and independent direction-binding audits while preserving intent, engineering basis, uncertainty, provenance, authority ceilings, compatibility boundaries, and final human judgment. Use when Codex clarifies or audits a structured functional requirement, checks whether a bounded direction-open expression has a directly attached direction, compares canonical v1 with the frozen 0.1.0 behavior, retrieves semantic-guard schemas, or works on design, implementation, migration, documentation, public contracts, durable evidence, and completion claims whose meaning could drift. Do not claim that v1 directly audits plans, diffs, finish evidence, every lifecycle phase, or unrestricted natural language.
---

# Semantic Implementation

Keep the original purpose visible: expose whether development requirements, plans, actions, realization methods, and evidence are justified by explicit engineering knowledge. Use the current 1.1.0 runtime only for the requirement-relation slice and independent direction-binding slice it actually implements.

Do not approve, reject, certify, accept risk, adopt policy, or make the final human decision.

## Public v1 surface

Prefer the MCP server when available:

- `audit_requirement_relations_tool`: audit one structured functional requirement.
- `audit_direction_binding_tool`: audit one bounded scalar or non-scalar direction-open expression under its independent v1 contract.
- `shadow_compare_legacy_tool`: compare v1 with an operator-pinned external 0.1.0 execution root.
- `semantic_guard_schema_tool`: retrieve one closed v1 schema.

Use the CLI fallback from the repository root:

```sh
uv run --locked semantic-guard audit-requirement --file requirement.txt
uv run --locked semantic-guard audit-direction-binding \
  --text '体重が重い順に並べたとき、Cの次に体重が重い人は誰か。' \
  --context '候補集合は現在の表だけを使う。' \
  --morphology sudachi
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
3. Give the requirement auditor one bounded requirement record at a time. Do not feed an entire plan or release note and rename the output a plan audit.
4. Give the direction-binding auditor one bounded direction-open expression in `text` plus only its current auxiliary context. A context-only question cannot become the primary operation, and postposed context does not substitute for direct attachment. Do not merge its result into `audit-result/v0`.
5. Retrieve the current schema when producing or consuming durable JSON.
6. Preserve every `undetermined`, `indeterminate`, `partial`, `failed`, challenge, hold, and unresolved obligation. Never coerce absence into success.
7. Map audit material into a plan, implementation change, verification step, or human question outside the audit engine. Keep that mapping explicit.
8. Record commands, exact results, checks not run, residual risks, and pending human decisions before claiming completion.

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

## Audit direction binding independently

Use `audit-direction-binding` or `audit_direction_binding_tool` only for the closed Japanese scalar and explicit non-scalar direction registries. Its primary question is whether a direction-open expression has exactly one effective direction-limiting expression directly attached to the same target and operation.

- Keep morphology at `signal_only`; a token, lemma, or part of speech never asserts the direction.
- Treat numeric projections as auxiliary `impact_evidence` only. They cannot change the primary rule, emitter, state, confidence, or workflow disposition.
- Read `primary_rule_evaluation.state` as `satisfied`, `gap`, `conflict`, `indeterminate`, `not_applicable`, or `invalid`.
- Read `workflow_disposition.status` separately as `pass`, `warn`, or `block`.
- Treat an unconfigured, partial, failed, or invalid morphology execution as visible uncertainty, never as a direction finding or unconditional pass.
- Never choose the direction for the caller and never treat workflow pass as human acceptance.

The result validates against `semantic-guard-direction-binding-audit/v1`. It is an additive public contract, not a field or projection of the requirement-relation audit.

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
