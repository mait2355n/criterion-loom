# Public Wording Audit Feature Brief

## Purpose

This document summarizes a proposed Criterion Loom audit feature for public
wording precision. It turns the current public-writing guideline into
deterministic audit requirements, candidate rule ids, output expectations, and
an implementation plan.

The target is not general copy editing. The target is claim-boundary auditing:
public prose should say what the tool returns, what an AI agent can revise from
it, what humans still decide, what evidence exists, and what remains outside the
tool.

## Audience And Use

This brief is for maintainers deciding whether to implement the feature in
Criterion Loom. Use it when discussing scope, detector placement, first rule
ids, expected output shape, fixtures, and acceptance criteria.

It is a feature brief, not an implementation record. It does not claim that the
public-wording audit already exists in the CLI or MCP server.

## Background

`docs/release/public-writing-guidelines.md` defines wording rules for Criterion
Loom public documents. Those rules are useful, but they currently rely on human
review. Because Criterion Loom already audits ambiguity, evidence, conventions,
and completion claims, the same discipline can be applied to public prose.

The useful feature is therefore not "make wording nicer". It is "warn when a
public claim uses vague ability language or overstates authority without naming
the operation, evidence, limitation, or revision path."

## Recommended Placement

Implement the first version inside `audit-conventions`.

Reasons:

- The concern is public contract shape and claim boundary, not ordinary
  requirement completeness.
- `audit-conventions` already owns public I/O, record, profile, and convention
  checks.
- The output can reuse normal `AuditResult` fields: `findings`, `missing`,
  `rule_id`, `evidence`, `suggested_fix`, `repair`, `match_status`, and
  `confidence`.
- If the rule group grows large, it can later be promoted to a dedicated
  command such as `audit-public-wording` without losing the rule ids or
  fixtures.

## Requirements

### Functional Requirements

- **REQ-PWA-001 Public wording surface detection**: The audit must run when the
  input appears to be public-facing documentation, such as README text, release
  notes, comparison material, publication notes, or companion-skill
  descriptions. It must also run when `input_kind=document` and public-claim
  terms are present.
- **REQ-PWA-002 Operation-backed ability claims**: Vague ability,
  visibility, repair, and improvement phrases must be backed by a nearby
  concrete operation, such as JSON output, structured findings, diagnostics,
  repair hints, schema, fixtures, corpus records, or explicit human decision
  boundaries. The initial watched phrase list should come from
  `docs/release/public-writing-guidelines.md`.
- **REQ-PWA-003 Improvement mechanism requirement**: Claims about improvement
  must name the feedback path. Valid paths include rule wording, detector code,
  fixture expectations, corpus records, output contracts, README wording,
  companion-skill routing, diagnostics, or the Codex work loop.
- **REQ-PWA-004 Finished-state scope requirement**: Claims that say the product
  is finished must be scoped to a publishable v0.1 surface, for example CLI,
  MCP server, companion skill, schema, fixtures, doctor, tests, and public docs.
  They must not imply a completed requirements engineering product or
  production approval gate.
- **REQ-PWA-005 Authority overclaim detection**: Claims using formal-evidence,
  approval, accuracy, safety, certification, or similar authority words must
  include a limitation or must be flagged when they imply general
  natural-language accuracy, release readiness, security certification, or
  final acceptance.
- **REQ-PWA-006 Agent and human boundary separation**: The audit must flag prose
  that treats the tool, LLM reviewer, or AI agent as the final accept/reject
  authority. It should accept prose that separates agent-side revision from
  human `accept`, `request_revision`, or `defer` decisions.
- **REQ-PWA-007 Evidence boundary requirement**: Claims about tests, fixtures,
  doctor, trace, or calibration must say whether they are local regression
  evidence, heuristic traces, or diagnostic records. They must not present local
  fixture success as general precision or recall.
- **REQ-PWA-008 Bilingual baseline**: The first version must cover the Japanese
  and English phrases already present in
  `docs/release/public-writing-guidelines.md`. It does not need broad
  multilingual coverage.
- **REQ-PWA-009 Example-context suppression**: The detector must avoid warning
  on forbidden phrases that appear inside explicit negative examples, such as
  `Avoid`, `Do not write`, `避ける`, `悪い例`, or guideline tables.
- **REQ-PWA-010 Structured findings**: Each warning must include a stable
  `rule_id`, compact evidence excerpt, missing operation or boundary,
  suggested fix, and repair target.

## Applied README.ja.md Review Indicators

The current `README.ja.md` rewrite used these practical indicators. They are
the first candidate examples for the proposed detector.

| Indicator | What Was Checked | README.ja.md Direction |
| --- | --- | --- |
| Product identity is concrete | The opening claim names the actual surface rather than a broad research theme. | `Codex作業向けの意味先行監査CLI / MCP server / companion skill` |
| Input and output are explicit | The text names the audited inputs and the machine-readable result. | requests, plans, change explanations, completion claims, and JSON audit results |
| Agent loop and human decision are separated | The text does not say the tool approves AI output. It separates agent-side revision from human final decision. | AI agents use findings to revise work; humans choose `accept`, `request_revision`, or `defer`. |
| Finished-state claim is scoped | `完成済み` is limited to the public v0.1 repository surface. | CLI, MCP server, companion skill, schemas, fixtures, doctor, tests, and public docs are present; broader performance continues to improve. |
| Authority claims are limited | The text does not imply general natural-language understanding, requirements proof, safety certification, or release approval. | vocabulary rules, lightweight structural checks, and local fixture regression are named as limits. |
| Improvement has a mechanism | Improvement claims name the artifact or loop that changes next. | rules, detectors, fixtures, corpus, output contracts, documents, and companion-skill routing. |
| Findings are revision targets | The text explains why Codex can act on output instead of receiving a vague critique. | `category`, `evidence`, `missing`, `rule_id`, `next_actions`, and `repair` are named. |
| Diagnostics explain uncertainty | The text names why a warning was emitted, suppressed, or treated as uncertain. | `non_emitted_rules`, `nearest_candidates`, `logical_trace_summary`, and claim/evidence/limitation diagnostics. |
| Public pillars stay stable | Support commands are not presented as separate public pillars. | Loom Guide, Need Thread, Plan Warp, and Change Weft remain the primary public shape. |
| Local evidence is not generalized | Fixture and corpus results are presented as local regression evidence. | They do not claim general precision, recall, semantic proof, or final acceptance. |

Observed wording changes used as seed examples:

| Before Pattern | After Pattern | Reason |
| --- | --- | --- |
| `JSONの監査結果として外へ取り出す` | `曖昧さや不足を抽出し、JSONの監査結果として返す` | Names extraction and JSON return rather than vague externalization. |
| `監査結果は ... 戻せる` | `AIエージェントは、監査結果を ... 作業ループへ戻す` | Names the actor and revision loop. |
| `人間が ... 判断するための材料にもなる` | `人間は同じ出力を ... 判断材料として使う` | Names the human use without making the tool the decision authority. |
| `見える場所へ出し` | `監査結果として分離し` | Names the output boundary. |
| `試験できる材料として外へ出す` | `退行検査できる材料として抽出する` | Ties the claim to regression checking. |
| `分けて直せる` | `どこが弱いかを切り分けられる` | Names diagnosis before repair. |
| `修正できる` | `指定された弱点に基づいて修正する` | Names the revision basis. |
| `追える` | `確認できる` / `対応づけられる` | Uses inspectable relation language. |
| `賢そうな判断を自動化すること` | `判断を自動承認すること` | Avoids rhetorical phrasing and names the forbidden authority claim. |

These indicators were checked with:

- `semantic-guard audit-request --kind document --file README.ja.md`
- public wording search for vague externalization, proof, finished-state, and
  improvement phrases
- review against `docs/release/public-writing-guidelines.md`

### Quality Requirements

- **REQ-PWA-011 Deterministic first**: The initial feature must use deterministic
  lexical and structural checks. LLM review can remain supplemental.
- **REQ-PWA-012 Low disruption default**: In the first release, findings should
  be `minor` or `major` warnings, not blockers. A release profile may later
  raise severity for public release material.
- **REQ-PWA-013 Local regression coverage**: Each rule must have at least one
  positive fixture and one negative fixture before promotion beyond draft.
- **REQ-PWA-014 Inspectable diagnostics**: `details.public_wording` should show
  detected public surface, matched phrases, satisfied support terms, suppressed
  example contexts, and emitted rule ids.
- **REQ-PWA-015 No general style linting**: The audit must not warn merely
  because a sentence is awkward, long, or stylistically plain. It only audits
  claim precision and boundary integrity.

## Non-Requirements

- It does not rewrite prose automatically.
- It does not judge marketing quality, tone, grammar, or beauty.
- It does not prove that public claims are true.
- It does not replace release review, legal review, security review, or final
  human acceptance.
- It does not require every use of `できる` or `can` to be removed. It requires
  strong ability claims to carry an operation, evidence, or boundary.

## Candidate Rule IDs

| Rule ID | Trigger | Expected Finding |
| --- | --- | --- |
| `conv.public_wording.operation_missing` | Vague ability phrase without operation support | Public wording uses ability language without naming what the tool returns, extracts, diagnoses, or leaves to human judgment. |
| `conv.public_wording.improvement_mechanism_missing` | Improvement claim without feedback path | Improvement is claimed without naming the artifact or work-loop path that changes next. |
| `conv.public_wording.finished_scope_unbounded` | Finished-state claim without v0.1 surface scope | Completion language is not bounded to CLI, MCP, skill, schemas, fixtures, doctor, tests, or public docs. |
| `conv.public_wording.authority_overclaim` | Accuracy, safety, approval, certification, or formal-evidence words without limitation | The prose may imply general correctness, security, release approval, or final acceptance. |
| `conv.public_wording.final_decision_boundary_blurred` | Tool, reviewer, or AI appears to accept/reject final output | The agent revision loop and final human decision boundary are mixed. |
| `conv.public_wording.fixture_generalization` | Fixture, corpus, doctor, or trace evidence presented as general accuracy | Local regression evidence is overstated as broad precision, recall, semantic proof, or readiness. |

## Detection Sketch

Use a small rule layer in `src/semantic_guard/conventions.py`:

1. Normalize text into lines and short windows.
2. Detect public-document surface terms such as README, release, public,
   publishable, documentation, skill, GitHub, comparison, `公開`, `文書`, and
   `README`.
3. Detect watched phrases from a catalog.
4. For each phrase, inspect the same line and neighboring lines for support
   terms.
5. Suppress hits inside explicit negative-example contexts.
6. Emit normal `Finding` objects with `rule_id`, `nearest_candidates`,
   `semantic_boundaries`, `match_status`, and `confidence`.

The first implementation can keep the phrase catalog in Python. If the rule
set grows, move it into `docs/conventions/base-contract.json` or a dedicated
`public-wording.json` catalog.

## Output Requirements

This proposal does not define a new active CLI, MCP, API, or durable-record
surface by itself. If implemented inside `audit-conventions`, it should reuse
the existing `AuditResult` envelope.

Expected public output contract:

- `stdout`: JSON `AuditResult` for normal CLI execution.
- `stderr`: argparse usage errors or dependency/runtime failure messages.
- exit code: existing command behavior; audited-material warnings stay in JSON
  `status`, while usage or runtime failures use non-zero exit codes.
- schema/version: reuse the current audit-result schema and include
  `details.schema_version`.
- fields and types: `status` string enum, `findings` array, `missing` array,
  `next_actions` array, and `details.public_wording` object.
- result metadata: keep diagnostic metadata under `details`.
- failure shape: do not introduce a second error envelope in this feature;
  existing errors carry code, message, details, and next_actions or remediation.

This proposal also does not introduce a new durable record schema. If a caller
persists the audit output, it should use the existing record guidance: ISO 8601
timestamp with timezone, evidence source, fact / inference / pending-decision
markers, and a shallow recovery surface with context, current_state,
next_action, and detail_refs.

No new repository profile is required. If the feature later needs profile
control, use the existing convention shape: schema_version, repository id,
public_surfaces, commands, tests, exceptions, non-goals, and internal-domain
boundaries. The default exception and non-goal remain: this feature audits
public wording, not internal domain design.

Example finding shape:

```json
{
  "severity": "major",
  "category": "governance",
  "rule_id": "conv.public_wording.improvement_mechanism_missing",
  "evidence": "Criterion Loom can improve incrementally because ...",
  "finding": "Public wording claims improvement without a concrete feedback path.",
  "suggested_fix": "Name the artifact or loop that changes next: rule wording, detector code, fixture expectation, corpus item, output contract, documentation, or companion-skill routing.",
  "missing": "improvement_feedback_path",
  "match_status": "partial",
  "confidence": "medium"
}
```

Expected details shape:

```json
{
  "public_wording": {
    "surface_detected": true,
    "matched_phrases": ["can improve"],
    "support_terms": [],
    "suppressed_contexts": [],
    "emitted_rule_ids": ["conv.public_wording.improvement_mechanism_missing"]
  }
}
```

## Fixture Plan

Add fixtures or unit tests for these cases:

- Japanese vague wording warns:
  `監査の挙動を構造化され、試験できる材料として外へ出す。`
- Japanese concrete wording passes:
  `監査の挙動を構造化され、退行検査できる材料として抽出する。`
- Improvement without feedback path warns.
- Improvement with rule, detector, fixture, corpus, documentation, and Codex
  work-loop feedback passes.
- Finished-state language without v0.1 scope warns.
- `公開可能な初版としては完成済み` with listed public surfaces passes.
- General-accuracy claims based only on fixture pass rate warn.
- `fixture evaluation is local regression coverage` passes.
- `The reviewer decides final acceptance` warns.
- `Human final decision remains pending until accept, request_revision, or defer`
  passes.
- `docs/release/public-writing-guidelines.md` passes despite containing avoid
  examples.

## Acceptance Criteria

- `semantic-guard audit-conventions --kind document --file README.md` passes.
- `semantic-guard audit-conventions --kind document --file README.ja.md` passes.
- `semantic-guard audit-conventions --kind document --file docs/release/public-writing-guidelines.md` passes.
- Bad examples emit the expected `conv.public_wording.*` rule ids.
- `conventions-catalog` or `rule-detector-map` exposes the new public-wording
  rules or detector mapping, depending on final placement.
- `evaluate-fixtures` passes after adding public-wording fixtures.
- Unit tests cover suppression of explicit negative examples.
- `doctor` continues to report no new block; the existing CI workflow warning is
  unrelated.

## Implementation Steps

1. Add a public-wording detector helper to `src/semantic_guard/conventions.py`.
2. Add the candidate rules to the conventions catalog or a dedicated public
   wording catalog.
3. Add unit tests in `tests/test_conventions.py`.
4. Add fixture cases if the team wants this tracked through
   `evaluate-fixtures`; otherwise keep the first version in unit tests and add
   fixtures after the rule wording stabilizes.
5. Add rule detector mappings if the rules are promoted into the main rule
   catalog.
6. Update `docs/conventions/README.md`,
   `docs/release/public-writing-guidelines.md`, and the companion skill docs so
   Codex can call the audit when preparing public prose.
7. Re-run README audits, convention audits, unit tests, fixture evaluation, and
   `doctor`.

## Open Decisions

- Should this remain inside `audit-conventions`, or should it become
  `audit-public-wording` after the first rule group proves useful?
- Should the phrase catalog live in `docs/conventions/base-contract.json`,
  `docs/release/public-writing-guidelines.md`, or a new machine-readable
  catalog?
- Should `release` severity profile raise public wording overclaims from
  `major` to `blocker`?
- How wide should the support window be: same line only, neighboring paragraph,
  or section-local?
- Should English and Japanese rules share one rule id per concern, or separate
  language-specific rule ids?

## Recommendation

Build the first version as an `audit-conventions` rule group with stable
`conv.public_wording.*` rule ids, deterministic pattern checks, and conservative
warning severity. Treat it as claim-boundary auditing, not style linting.

That keeps the feature aligned with Criterion Loom's core idea: do not accept
vague authority claims as final truth; turn them into structured revision
targets for Codex and review material for humans.
