# Criterion Loom documentation

[日本語](README.ja.md) · [Project overview](../README.md)

This page routes readers by task. It deliberately separates current reference,
operating guidance, design candidates, dated evidence, and history: proximity in
the repository is not authority. Links to Japanese-language detail are marked
`Japanese`; this English map retains the corresponding role and claim boundary.

## Choose by task

| If you want to… | Start with | Then read |
| --- | --- | --- |
| Understand the project in a few minutes | [Project overview](../README.md) | [Current public surface](../PUBLIC-SNAPSHOT.md) |
| Run the CLI or MCP server | [Quickstart](../README.md#quickstart-one-bounded-proof) | [Operations guide](operations.md) (Japanese) |
| Audit one structured functional requirement | [Requirement example](operations.md#要求関係入力契約) (Japanese) | [Analysis flow](operations.md#解析の流れ) (Japanese) and [CLI/result states](operations.md#終了コードと監査状態) (Japanese) |
| Integrate an agent through MCP or the companion Skill | [Choose an interface](../README.md#choose-an-interface) | [Skill contract](../skills/semantic-implementation/references/mcp-contract.md) |
| Interpret a direction-binding result | [Direction-binding audit](direction-binding-audit.md) (Japanese) | [Implementation status](implementation-status.md) (Japanese) |
| Audit claims about maturity or evidence | [Implementation status](implementation-status.md) (Japanese) | [Evidence and audit records](#evidence-and-audit-records) |
| Contribute or report a problem | [Contributing](../CONTRIBUTING.md) | [Support](../SUPPORT.md) or [Security](../SECURITY.md) |
| Understand the 0.1.0 break | [Migration guide](migration-v0.1.0-to-v1.0.0.md) | [Canonical promotion decision](canonical-promotion-decision.md) |

## Current reference

These documents describe the current source line or its current reading rules.
They do not, by themselves, establish field validity or human acceptance.

- [Current public surface](../PUBLIC-SNAPSHOT.md) — package identity, public
  commands and tools, supported claims, and explicit non-claims.
- [Implementation status](implementation-status.md) (Japanese) — implemented surfaces,
  dated observations, open evidence, and qualification gaps.
- [Operations guide](operations.md) (Japanese) — input boundaries, provider authority,
  exit codes, automation, package verification, and legacy isolation.
- [Direction-binding audit](direction-binding-audit.md) (Japanese) — meaning, state model,
  paired fail-closed example, errors, evidence, and limits of the independent
  1.1.0 slice.
- [Origin requirement](prototypes/origin-requirement.md) (Japanese) — current purpose
  authority despite its historically inherited `prototypes/` path.

Machine-readable authority for field constraints lives in the
[audit-result schema](../schemas/audit-result.schema.json),
[direction-binding schema](../schemas/direction-binding-audit.schema.json), and
[verification source](../validation/verification-source.json). The
[constitution](../constitution/semantic-guard-constitution.yaml) defines the
project-level authority boundary.

## Contract and assurance design

The following documents describe implemented internal sidecars, candidate
profiles, or design constraints. Unless a document explicitly says otherwise,
their presence does not create a canonical public CLI/MCP workflow or human
adoption.

| Area | Current status | Document |
| --- | --- | --- |
| Action evidence and bounded assurance | Implemented internal sidecar; no public workflow | [Action evidence and assurance profile](action-evidence-and-assurance-profile.md) (Japanese) |
| Lifecycle scope | Candidate; pending human adoption | [Lifecycle profile registry](lifecycle-profile-registry.md) (Japanese) |
| Trace and composition | Implemented internal prototype; no public workflow | [Lifecycle trace and composition](lifecycle-trace-and-composition.md) (Japanese) |
| State validity over change | Implemented internal opt-in contract; no public workflow | [State assessment and requalification](state-assessment-and-requalification.md) (Japanese) |
| Repair and responsibility | Implemented internal opt-in contract; practical effect untested | [Repair loop and responsibility material](repair-loop-and-responsibility-material.md) (Japanese) |
| Prospective field-sample intake | Implemented intake gate; no real corpus or field result | [Field-sample intake](field-sample-intake.md) (Japanese) |
| Field evaluation design | Implemented evaluation contract; no field result | [Field evaluation and ablation](field-evaluation-and-ablation.md) (Japanese) |
| Outcome evaluation | Implemented evaluation contract; no real participants or outcomes | [Operational outcome evaluation](operational-outcome-evaluation.md) (Japanese) |
| Qualification and transition | Implemented internal contract; no operational qualification or cutover | [Operational qualification and transition](operational-qualification-and-transition.md) (Japanese) |
| Secure-operation boundary | Implemented internal-consistency audit; no security conclusion | [Secure-operation boundary](secure-operation-boundary.md) |
| Engineering-knowledge governance | Candidate; runtime authority `none` | [Engineering rule-pack governance](engineering-rule-pack-governance.md) (Japanese) |

## Evidence and audit records

Dated records support only their named subject, source digest or commit,
environment, and observation time. They are not silently refreshed when the
current tree changes.

| Record | Reading role |
| --- | --- |
| [Public-document audit, 2026-08-27](audits/public-document-audit-2026-08-27.md) (Japanese) | Pre-integration record for value-first structure, Japanese wording, local links, contract boundaries, and local verification |
| [Direction-binding integration, 2026-08-23](audits/direction-binding-integration-2026-08-23.md) (Japanese) | Dated 1.1.0 source, package, registered-case, and GitHub integration evidence |
| [Repository unification, 2026-08-24](repository-unification-2026-08-24.md) | Pre-transfer repository identity and redirect boundary |
| [Post-transfer observation, 2026-08-24](audits/repository-transfer-observation-2026-08-24.md) | Separate observation after the repository transfer |
| [v1.0.0 canonicalization audit, 2026-07-17](audits/canonicalization-audit-v1.0.0-2026-07-17.md) | Evidence for the 1.0.0 promotion subject, not an automatic 1.1.0 claim |
| [v1.0.0 public snapshot, 2026-07-17](audits/public-snapshot-v1.0.0-2026-07-17.md) | Frozen historical public-surface description |
| [Full prototype evaluation, 2026-07-11](audits/semantic-guard-full-evaluation-2026-07-11.md) (Japanese) | Publication-sanitized historical evaluation; not current runtime evidence |
| [Impact and execution order, 2026-07-16](impact-and-execution-order-2026-07-16.md) | Historical candidate-stage prioritization |

For the verification items it declares, the structured state authority is
[`validation/verification-source.json`](../validation/verification-source.json),
not a convenient summary of a dated report. Its `active_draft` scope does not
absorb every later observation or make dated 1.1.0 evidence current.

## Prototypes and history

- [Origin requirement](prototypes/origin-requirement.md) (Japanese) is the one path
  exception: its OR-01 through OR-03 statements remain the current purpose
  authority. That status does not promote every prototype beside it.
- [Canonical promotion decision, 2026-07-17](canonical-promotion-decision.md)
  records why 1.0.0 became canonical and what that historical decision did not
  prove. It is not the current 1.1.0 command inventory.
- [Requirement-relation audit charter, 2026-07-12](prototypes/requirement-relation-audit-charter-2026-07-12.md)
  records the candidate-stage design that preceded the canonical v1 slice.
- [Proof-obligation assurance graph charter, 2026-07-16](prototypes/proof-obligation-assurance-graph-charter-2026-07-16.md)
  is candidate material, not an adopted public workflow.
- [Verification-register completeness charter, 2026-07-16](prototypes/verification-register-completeness-charter-2026-07-16.md)
  is candidate material, not an adopted public workflow.
- [Migration from 0.1.0 to 1.0.0](migration-v0.1.0-to-v1.0.0.md) explains the
  contract replacement, explicit legacy route, and non-alias boundary.
- [`migration/migration-map.md`](../migration/migration-map.md) classifies
  retained, replaced, archived, and deferred material.
- [`legacy/semantic-guard-v0.1.0/`](../legacy/semantic-guard-v0.1.0/) is a
  publication-repaired archive. Its manifest points to the original Git bytes.

Historical GitHub URLs are not rewritten as though an earlier event occurred
under a later owner label. Use the repository-unification records for the
repository-ID mapping and redirect boundary.

## Status and identity notation

The status below is a reading role for a placement, not entity identity. For
the compact references in this table, the UUID on the right of `・` is the
identity authority. Other contracts may use another stable `entity_id`; compare
that right-hand identifier under its defining contract, never the label, path,
role, or content digest alone.

| Status | Placement or lineage | Reading rule |
| --- | --- | --- |
| `current` | `canonical current・11c55966-ff12-50b9-b069-7bec6ed37cc4`; the repository overview and implementation status | Describes the current canonical repository boundary. A current document is not by itself field-validity or human-acceptance evidence. |
| `reference` | `direction-binding public slice・245dad95-accf-581c-8b0a-ae1c1f557de4`; `direction-binding-audit.md` and the undated contract/design guides | Explains intended meaning and constraints. Machine schemas and verified behavior outrank explanatory prose. |
| `evidence` | Date- and subject-bound records under `docs/audits/` and `validation/` | Supports only the recorded subject, source digest, environment, and observation time. It does not automatically describe the current tree. |
| `archive` | `publication-repaired legacy archive・3fd59352-b0d9-58f6-8279-9309c8960631`; predecessor and superseded historical material | Preserved for history or explicit comparison. The historical Git anchor retains the original bytes; the readable archive includes disclosed publication repairs. It is never a transparent current fallback or truth oracle. |
| `experimental` | `candidate_ref: local vnext candidate・32646741-8cec-5fe3-b9f3-2971a8a787f0`; prototype charters under `docs/prototypes/` except `origin-requirement.md` | Candidate material only. Do not infer adoption, migration, or canonical authority. |
| `local-only` | `derived_from: local feature source snapshot・2b62dfa0-6d90-5c31-ae2d-34ec55c94895`; see the direction-binding source map | Exists outside the canonical repository boundary. Only explicitly selected, digest-bound sources may be integrated; no whole-root copy is authorized. |

`canonical current・11c55966-ff12-50b9-b069-7bec6ed37cc4` identifies the logical
project's current canonical state in this map. It is not the GitHub repository
object `canonical repository object・51d473df-7d86-466d-a9f4-47a01ff70d44`.

## Community and maintenance

- [Contributing](../CONTRIBUTING.md)
- [Support](../SUPPORT.md)
- [Security policy](../SECURITY.md)
- [Code of Conduct](../CODE_OF_CONDUCT.md)
- [Change log](../CHANGELOG.md)
- [MIT License](../LICENSE)

Final acceptance, revision, deferral, rejection, risk acceptance, policy
adoption, and operational cutover remain outside the audit engine.
