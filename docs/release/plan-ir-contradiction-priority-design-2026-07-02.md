# Plan IR contradiction and priority audit design

Date: 2026-07-02
Status: design only
Scope: `audit-plan`

## Purpose

This document designs a stronger `audit-plan` layer for plan-internal
contradictions and impact/priority design gaps.

The goal is not to claim general natural-language logical reasoning. The goal
is to make plan audit stronger by projecting explicit plan statements into a
small typed intermediate representation, then checking deterministic
constraints over that representation.

## Audience and Use

This document is for maintainers implementing `audit-plan`, reviewers checking
whether the feature is realistically bounded, and future agents resuming the
work. It should be used as implementation design input, not as proof that the
feature already exists.

Use it to decide:

- which Plan IR facts may be extracted deterministically;
- which contradiction findings are strong enough to emit;
- which priority and impact findings are only design-gap warnings;
- which output details can remain internal in the first implementation slice;
- which fixture classes are required before implementation acceptance.

## Non-goals

- Do not make `semantic-guard` decide final work priority.
- Do not claim complete contradiction detection over arbitrary prose.
- Do not add an LLM dependency to deterministic `audit-plan`.
- Do not make `resource-control-plane` part of `semantic-guard`.
- Do not change public CLI/MCP output contracts in the first implementation
  slice without a separate conventions audit.

## Boundary

`semantic-guard` exposes:

- possible plan contradictions;
- missing priority basis;
- missing impact classification;
- missing gate, rollback, verification, or completion proof material needed to make a plan
  controllable.

`resource-control-plane` consumes those findings as management material and can
decide, persist management state, defer, delegate, or close work.
`semantic-guard` must not decide final priority or final acceptance.

## Public I/O Contract Stance

This design does not define a new CLI, MCP, API, or durable management-entry contract.

First-slice implementation should keep the existing `audit-plan` result
envelope. Machine-readable audit JSON continues to go to stdout, human-facing
diagnostics continue to go to stderr, and existing CLI exit-code policy remains
unchanged. No new public error shape is introduced here; any future failure
surface must use the established error fields: code, message, details, hint or
next action, and command metadata.

If a later slice exposes full `details.plan_ir`, that change becomes a public
structured-output surface and needs a separate conventions audit, schema/version
decision, fixture coverage, stdout/stderr/exit-code verification, and release
note.

If findings are imported into `resource-control-plane` records, the durable
record belongs to that repository's schema. It must preserve observed time,
evidence source, acquisition method, evidence kind, inference status,
confidence, pending-decision markers, and owner where applicable. The observed
time must be an ISO 8601 timestamp with timezone. This design does not create
those records itself.

## Feasibility Claim

The feature is feasible if it is defined as typed extraction plus deterministic
constraint checking.

It is not feasible as a general proof that the prose is logically consistent.

The proof obligation is therefore limited:

1. Extract only explicit facts from labeled plan text or local sentence
   patterns.
2. Assign confidence to each extracted fact.
3. Emit `matched_conflict` only when two high-confidence facts collide.
4. Emit `possible_conflict` when target aliases or class-level overlap are
   plausible but not exact.
5. Emit priority findings only when an impact surface is visible and the plan
   lacks the control material required for that surface.

This keeps the system honest. It can miss subtle contradictions, but every
strong contradiction finding must be traceable to two or more source excerpts.

## Plan IR

The internal representation should start as `plan-ir/v0`. It can live in
`details.plan_ir_summary` first; full `details.plan_ir` should remain a later
decision because it may become a public output surface.

Minimum shape:

```json
{
  "schema_version": "plan-ir/v0",
  "source_segments": [],
  "entities": [],
  "assertions": [],
  "edges": [],
  "impact_surfaces": [],
  "priority_claims": [],
  "diagnostics": []
}
```

### Source Segment

```json
{
  "id": "seg-001",
  "field": "non_goals",
  "text": "対象外: UIは作らない。",
  "line": 3,
  "match_confidence": "high"
}
```

`field` should be one of:

- `objective`
- `non_goals`
- `deliverables`
- `work_breakdown`
- `sequence`
- `dependencies`
- `constraints`
- `risks`
- `verification`
- `validation`
- `rollback`
- `decision_gate`
- `completion_evidence`
- `unknowns`
- `unclassified`

### Entity

```json
{
  "id": "ent-ui",
  "canonical": "ui",
  "aliases": ["UI", "画面", "フロントエンド"],
  "entity_class": "user_interface",
  "source_segment_ids": ["seg-001", "seg-004"],
  "confidence": "high"
}
```

Entity classes are deliberately finite. First slice:

- `user_interface`
- `dependency`
- `public_contract`
- `release_artifact`
- `persistent_record`
- `permission_or_secret`
- `destructive_operation`
- `runtime_operation`
- `test_or_fixture`
- `documentation`
- `configuration`
- `core_module`
- `unknown`

### Assertion

```json
{
  "id": "ast-001",
  "kind": "scope_boundary",
  "target_id": "ent-ui",
  "action": "create",
  "polarity": "negative",
  "modality": "prohibited",
  "source_segment_id": "seg-001",
  "evidence": "UIは作らない",
  "confidence": "high"
}
```

`kind` should be finite:

- `scope_boundary`
- `work_action`
- `constraint`
- `dependency_policy`
- `sequence_claim`
- `risk_claim`
- `risk_response`
- `verification_claim`
- `validation_claim`
- `decision_gate`
- `priority_basis`
- `impact_claim`

`polarity`:

- `positive`
- `negative`
- `neutral`
- `unknown`

`modality`:

- `planned`
- `prohibited`
- `excluded`
- `required`
- `conditional`
- `deferred`
- `unknown`

### Edge

```json
{
  "id": "edge-001",
  "kind": "sequence_after",
  "from_id": "work-implement",
  "to_id": "work-verify",
  "source_segment_id": "seg-010",
  "confidence": "high"
}
```

Edge kinds:

- `sequence_before`
- `sequence_after`
- `depends_on`
- `verifies`
- `mitigates`
- `gated_by`
- `produces`

## Extraction Rules

Extraction must be conservative. If a fact cannot be extracted with useful
confidence, leave it out and optionally add a diagnostic; do not invent it.

### Segment Extraction

Use labeled Japanese and English headings first:

- `目的`, `Objective`
- `対象外`, `Non-goals`, `Out of scope`
- `成果物`, `Deliverables`
- `作業分解`, `手順`, `工程`, `Steps`
- `順序`, `依存`, `Dependencies`
- `制約`, `Constraints`
- `リスク`, `Risks`
- `検証`, `Verification`
- `妥当性`, `Validation`
- `決定点`, `Decision Gate`
- `戻し方`, `Rollback`
- `証拠`, `Evidence`
- `未確定`, `Open Decisions`

Unlabeled prose can still be segmented by sentence, but unlabeled extraction
starts at medium confidence at best.

### Entity Canonicalization

Canonicalization should use small local alias tables, not open-ended semantic
matching.

Initial aliases:

| canonical | aliases |
| --- | --- |
| `ui` | `UI`, `画面`, `フロントエンド`, `frontend` |
| `dependency` | `依存`, `新規依存`, `package`, `pip install`, `npm install` |
| `public_contract` | `CLI`, `MCP`, `API`, `schema`, `JSON output`, `出力契約` |
| `release_artifact` | `公開物`, `配布物`, `release`, `wheel`, `sdist`, `PyPI`, `npm` |
| `persistent_record` | `DB`, `保存`, `台帳`, `ledger`, `record`, `永続` |
| `permission_or_secret` | `権限`, `認証`, `認可`, `token`, `secret`, `秘密` |
| `destructive_operation` | `削除`, `上書き`, `unlink`, `rm`, `drop`, `移行` |
| `runtime_operation` | `同期`, `queue`, `job`, `cron`, `再試行`, `retry` |

Ambiguous aliases must not produce `matched_conflict` by themselves. They can
produce `possible_conflict` only.

### Polarity Extraction

Negative polarity terms:

- `しない`
- `作らない`
- `含めない`
- `対象外`
- `非対象`
- `導入しない`
- `追加依存なし`
- `公開しない`
- `配布しない`
- `読み取り専用`
- `書き込みなし`
- `自動化しない`

Positive polarity terms:

- `作る`
- `実装する`
- `追加する`
- `導入する`
- `更新する`
- `削除する`
- `移行する`
- `公開する`
- `配布する`
- `自動実行する`
- `npm install`
- `pip install`

When a negative and positive term appear in the same short phrase, local syntax
must decide the polarity. If syntax is unclear, set `polarity: unknown`.

## Contradiction Rules

Every strong contradiction finding must include at least two evidence excerpts.

### `plan.consistency.non_goal_conflict`

Applies when:

- one high-confidence `scope_boundary` assertion has `polarity: negative`;
- one high-confidence `work_action` assertion has `polarity: positive`;
- both share the same `target_id`;
- neither assertion has `modality: conditional` or `deferred`.

Finding:

> 計画の対象外と作業内容が衝突している可能性がある。

Severity:

- `major` for exact target conflict;
- `minor` for alias-class possible conflict.

### `plan.consistency.constraint_action_conflict`

First-slice pairs:

| constraint | conflicting action |
| --- | --- |
| `追加依存なし` | `pip install`, `npm install`, `新規依存を導入` |
| `読み取り専用`, `書き込みなし` | `削除`, `更新`, `移行`, `保存` |
| `公開しない`, `非公開` | `公開する`, `配布する`, `release`, `publish` |
| `自動化しない` | `自動実行`, `cron`, `scheduled job` |

Finding:

> 計画の制約と実行行為が衝突している可能性がある。

### `plan.consistency.risk_claim_conflict`

Applies when:

- the plan has a high-confidence `risk_claim` equivalent to `リスクなし`;
- another segment contains risk terms such as `壊れる`, `失敗`, `副作用`,
  `影響`, `負荷`, `危険`, `懸念`;
- the second segment is not a negated example.

Finding:

> リスクなしという主張と、別箇所の危険記述が衝突している。

### `plan.consistency.sequence_cycle`

Build a directed graph from high-confidence sequence and dependency edges.

Examples:

- `Aの後にB` => `A -> B`
- `BはAに依存` => `A -> B`
- `Bの前にA` => `A -> B`

Emit when the graph has a cycle.

Finding:

> 作業順序または依存関係が循環している。

### `plan.consistency.dependency_order_inversion`

Applies when:

- dependency edge says `A -> B`;
- sequence edge says `B -> A`;
- both edges are high confidence.

Finding:

> 依存関係と実行順序が逆転している可能性がある。

## Impact Classification

Impact classification is a prerequisite for priority audit. It should expose
what kind of surface the plan touches, not compute a final priority.

Initial impact surfaces:

| surface | level | triggers |
| --- | --- | --- |
| `public_contract` | high | CLI, MCP, API, schema, JSON output, output contract |
| `persistence` | high | DB, ledger, record schema, migration, saved state |
| `permission_or_secret` | high | auth, token, secret, permission, role |
| `destructive_operation` | high | delete, overwrite, drop, migration, unlink |
| `release` | high | publish, release, PyPI, npm, wheel, sdist |
| `runtime_operation` | medium/high | retry, queue, job, cron, sync, monitor |
| `core_shared_module` | medium/high | core, common, shared, base, framework |
| `user_facing_text` | medium | README, visible label, UI copy |
| `docs_only` | low/medium | docs, README, comments |
| `test_only` | low | tests, fixture, mock |

`level` is a classification label, not an acceptance decision.

## Priority Design Rules

### `plan.impact.surface_unclassified`

Applies when:

- the plan has three or more work items; and
- none of them receives an impact surface; and
- the plan is not marked as a small single-surface change.

Finding:

> 複数作業の計画だが、影響面の分類が見えない。

### `plan.priority.impact_basis_missing`

Applies when:

- the plan has a high-impact surface; and
- it has multiple work items or multiple deliverables; and
- no priority basis is visible.

Priority basis terms:

- `依存順`
- `影響度順`
- `危険低減`
- `基準線`
- `先にschema`
- `先に契約`
- `rollbackしやすい順`
- `検証しやすい順`
- `人間判断前`
- `公開前`
- `because`
- `rationale`

Finding:

> 高影響作業を含む計画だが、優先順の根拠が見えない。

### `plan.priority.contract_baseline_order_missing`

Applies when:

- the plan touches public contract surfaces; and
- docs, examples, or downstream wrappers are planned before the contract source
  is checked or fixed; and
- no rationale explains the order.

Finding:

> 公開契約に従属する作業の前に、契約基準線を確認する順序が見えない。

### `plan.priority.high_impact_gate_missing`

This overlaps with existing `plan.governance.decision_gate_missing`.

The design should not duplicate the rule. Instead, the IR should provide better
evidence for the existing decision-gate rule by naming the high-impact surface.

### `plan.priority.reversibility_order_missing`

Applies when:

- destructive, persistence, release, or permission surfaces are present; and
- rollback exists in general; but
- the plan does not put reversible validation before irreversible action.

Finding:

> 不可逆または高復旧費用の作業があるが、可逆な確認を先に置く順序が見えない。

## Confidence and Emission Policy

Use three confidence levels:

`high`
: Labeled segment plus exact alias or direct action term.

`medium`
: Unlabeled sentence or class-level alias match.

`low`
: Broad topical hint only.

Emission policy:

- `matched_conflict`: requires high/high evidence.
- `possible_conflict`: allows high/medium or medium/medium evidence.
- `priority_design_gap`: requires high-impact surface and missing basis.
- `impact_surface_unclassified`: warning-class generic caution unless the plan
  explicitly claims impact-based ordering.
- low-confidence facts are diagnostics only in the first slice.

## Output Design

First implementation should add stable findings but keep the full IR internal.

Recommended details addition:

```json
{
  "plan_ir_summary": {
    "schema_version": "plan-ir-summary/v0",
    "source_segment_count": 8,
    "entity_count": 5,
    "assertion_count": 12,
    "impact_surfaces": ["public_contract"],
    "conflict_candidates": [
      {
        "rule_id": "plan.consistency.non_goal_conflict",
        "conflict_kind": "matched_conflict",
        "evidence_count": 2
      }
    ],
    "priority_basis_present": false
  }
}
```

Do not expose raw full IR by default until its shape is stable. If exposed later,
it should be versioned and documented as public output.

## Implementation Slices

### Slice 1: IR extraction without new findings

Files:

- `src/semantic_guard/plan_ir.py`
- `tests/test_plan_ir.py`

Scope:

- source segmentation;
- entity aliasing;
- assertion extraction;
- impact surface classification;
- `details.plan_ir_summary`.

Acceptance:

- no existing fixture status changes;
- implementation tests verify the summary is JSON-serializable;
- no unmapped rules because no new rules yet.

### Slice 2: High-confidence contradiction rules

Rules:

- `plan.consistency.non_goal_conflict`
- `plan.consistency.constraint_action_conflict`
- `plan.consistency.risk_claim_conflict`
- `plan.consistency.sequence_cycle`
- `plan.consistency.dependency_order_inversion`

Acceptance:

- exact conflict fixtures warn;
- exact non-conflict fixtures pass;
- ambiguous alias fixtures emit only possible conflict or no finding according
  to expected label.

### Slice 3: Impact and priority design rules

Rules:

- `plan.impact.surface_unclassified`
- `plan.priority.impact_basis_missing`
- `plan.priority.contract_baseline_order_missing`
- `plan.priority.reversibility_order_missing`

Acceptance:

- high-impact multi-work plans without priority basis warn;
- high-impact plans with dependency/risk/contract-order rationale pass;
- docs-only one-file plans do not warn.

### Slice 4: Public documentation and calibration

Scope:

- update rule catalog;
- update rule-detector map;
- add fixtures and field-corpus entries;
- update documentation map only if the feature becomes part of the public
  explanation.

Acceptance:

- `python -m unittest discover -s tests -v`
- `semantic-guard evaluate-fixtures`
- `semantic-guard doctor`
- representative `audit-plan` smoke tests for conflict and priority examples.

## Fixture Matrix

Required bad cases:

| id | expected rule |
| --- | --- |
| `PLAN-CONFLICT-NONGOAL-UI-001` | `plan.consistency.non_goal_conflict` |
| `PLAN-CONFLICT-NO-DEPENDENCY-001` | `plan.consistency.constraint_action_conflict` |
| `PLAN-CONFLICT-READONLY-DELETE-001` | `plan.consistency.constraint_action_conflict` |
| `PLAN-CONFLICT-RISK-NONE-001` | `plan.consistency.risk_claim_conflict` |
| `PLAN-CONFLICT-SEQUENCE-CYCLE-001` | `plan.consistency.sequence_cycle` |
| `PLAN-PRIORITY-HIGH-IMPACT-NO-BASIS-001` | `plan.priority.impact_basis_missing` |
| `PLAN-PRIORITY-CONTRACT-BASELINE-MISSING-001` | `plan.priority.contract_baseline_order_missing` |
| `PLAN-PRIORITY-IRREVERSIBLE-FIRST-001` | `plan.priority.reversibility_order_missing` |

Required good cases:

| id | protected behavior |
| --- | --- |
| `PLAN-CONFLICT-NONGOAL-DOCS-GOOD-001` | docs-only plan with non-goal UI does not conflict |
| `PLAN-CONFLICT-DEPENDENCY-GOOD-001` | `追加依存なし` plus stdlib reuse passes |
| `PLAN-CONFLICT-READONLY-GOOD-001` | read-only audit with no write actions passes |
| `PLAN-CONFLICT-SEQUENCE-GOOD-001` | acyclic dependency order passes |
| `PLAN-PRIORITY-HIGH-IMPACT-WITH-BASIS-001` | public contract plan with schema-first rationale passes |
| `PLAN-PRIORITY-DOCS-ONLY-GOOD-001` | small README-only plan does not need impact ordering |

Ambiguous cases:

| id | expected behavior |
| --- | --- |
| `PLAN-CONFLICT-ALIAS-POSSIBLE-001` | possible conflict, not major matched conflict |
| `PLAN-PRIORITY-UNLABELED-MEDIUM-001` | missing basis warning only if high-impact surface is explicit |

## Failure Modes

Over-claiming
: The implementation starts saying it detects contradictions generally. Mitigate
  by naming findings as plan-internal conflict candidates unless evidence is
  exact.

Alias drift
: The alias table grows until unrelated terms collide. Mitigate by keeping
  alias tables per entity class and adding good fixtures for every new alias.

Priority scoring creep
: The feature becomes a hidden priority engine. Mitigate by using findings such
  as missing basis, missing gate, missing order rationale, and leaving decisions
  to humans or `resource-control-plane`.

Output contract drift
: Full IR becomes de facto public without schema. Mitigate by exposing only a
  versioned summary first.

Context dilution
: Low-confidence unlabeled prose produces noisy conflicts. Mitigate by keeping
  low-confidence facts diagnostic-only in the first implementation.

## Implementation Feasibility Conclusion

The feature is feasible if implemented as an explicit-fact checker over a
bounded Plan IR.

It is not feasible, and should not be presented, as general logical analysis of
Japanese prose.

The practical strength comes from this division:

- extraction is conservative;
- conflict rules require multiple evidence excerpts;
- high-confidence conflicts are separated from possible conflicts;
- priority audit checks missing rationale and missing gates, not final priority;
- management decisions remain outside `semantic-guard`.

This would make `audit-plan` materially closer to the requirement and diff
audits in strength without pretending to solve full natural-language reasoning.
