# Criterion Loom documentation

[日本語](README.ja.md) · [Project overview](../README.md)

This page routes readers by task. It deliberately separates current reference,
operating guidance, design candidates, dated evidence, and history: proximity in
the repository is not authority.

## Choose by task

| If you want to… | Start with | Then read |
| --- | --- | --- |
| Understand the project in a few minutes | [Project overview](../README.md) | [Current public surface](../PUBLIC-SNAPSHOT.md) |
| Run the CLI or MCP server | [Quickstart](../README.md#quickstart-one-bounded-proof) | [Operations guide](operations.md) |
| Integrate an agent through MCP or the companion Skill | [Choose an interface](../README.md#choose-an-interface) | [Skill contract](../skills/semantic-implementation/references/mcp-contract.md) |
| Interpret a direction-binding result | [Direction-binding audit](direction-binding-audit.md) | [Implementation status](implementation-status.md) |
| Audit claims about maturity or evidence | [Implementation status](implementation-status.md) | [Evidence and audit records](#evidence-and-audit-records) |
| Contribute or report a problem | [Contributing](../CONTRIBUTING.md) | [Support](../SUPPORT.md) or [Security](../SECURITY.md) |
| Understand the 0.1.0 break | [Migration guide](migration-v0.1.0-to-v1.0.0.md) | [Canonical promotion decision](canonical-promotion-decision.md) |

## Current reference

These documents describe the current source line or its current reading rules.
They do not, by themselves, establish field validity or human acceptance.

- [Current public surface](../PUBLIC-SNAPSHOT.md) — package identity, public
  commands and tools, supported claims, and explicit non-claims.
- [Implementation status](implementation-status.md) — implemented surfaces,
  dated observations, open evidence, and qualification gaps.
- [Operations guide](operations.md) — input boundaries, provider authority,
  exit codes, automation, package verification, and legacy isolation.
- [Direction-binding audit](direction-binding-audit.md) — meaning, state model,
  errors, evidence, and limits of the independent 1.1.0 slice.
- [Origin requirement](prototypes/origin-requirement.md) — current purpose
  authority despite its historically inherited `prototypes/` path.
- [Canonical promotion decision](canonical-promotion-decision.md) — why v1 is
  the canonical implementation and what promotion did not prove.

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

| Area | Document |
| --- | --- |
| Action evidence and bounded assurance | [Action evidence and assurance profile](action-evidence-and-assurance-profile.md) |
| Lifecycle scope | [Lifecycle profile registry](lifecycle-profile-registry.md) |
| Trace and composition | [Lifecycle trace and composition](lifecycle-trace-and-composition.md) |
| State validity over change | [State assessment and requalification](state-assessment-and-requalification.md) |
| Repair and responsibility | [Repair loop and responsibility material](repair-loop-and-responsibility-material.md) |
| Field evaluation design | [Field evaluation and ablation](field-evaluation-and-ablation.md) |
| Outcome evaluation | [Operational outcome evaluation](operational-outcome-evaluation.md) |
| Qualification and transition | [Operational qualification and transition](operational-qualification-and-transition.md) |
| Secure-operation boundary | [Secure-operation boundary](secure-operation-boundary.md) |
| Engineering-knowledge governance | [Engineering rule-pack governance](engineering-rule-pack-governance.md) |

## Evidence and audit records

Dated records support only their named subject, source digest or commit,
environment, and observation time. They are not silently refreshed when the
current tree changes.

| Record | Reading role |
| --- | --- |
| [Direction-binding integration, 2026-08-23](audits/direction-binding-integration-2026-08-23.md) | Dated 1.1.0 source, package, registered-case, and GitHub integration evidence |
| [Repository unification, 2026-08-24](repository-unification-2026-08-24.md) | Pre-transfer repository identity and redirect boundary |
| [Post-transfer observation, 2026-08-24](audits/repository-transfer-observation-2026-08-24.md) | Separate observation after the repository transfer |
| [v1.0.0 canonicalization audit, 2026-07-17](audits/canonicalization-audit-v1.0.0-2026-07-17.md) | Evidence for the 1.0.0 promotion subject, not an automatic 1.1.0 claim |
| [v1.0.0 public snapshot, 2026-07-17](audits/public-snapshot-v1.0.0-2026-07-17.md) | Frozen historical public-surface description |
| [Full prototype evaluation, 2026-07-11](audits/semantic-guard-full-evaluation-2026-07-11.md) | Publication-sanitized historical evaluation; not current runtime evidence |
| [Impact and execution order, 2026-07-16](impact-and-execution-order-2026-07-16.md) | Historical candidate-stage prioritization |

For the verification items it declares, the structured state authority is
[`validation/verification-source.json`](../validation/verification-source.json),
not a convenient summary of a dated report. Its `active_draft` scope does not
absorb every later observation or make dated 1.1.0 evidence current.

## Prototypes and history

- [Origin requirement](prototypes/origin-requirement.md) is the one path
  exception: its OR-01 through OR-03 statements remain the current purpose
  authority. That status does not promote every prototype beside it.
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

The status below is a reading role for a placement, not entity identity. Labels
and paths may change; the UUID on the right of `・` remains the identity
authority. A shared label, path, or content digest does not by itself establish
identity.

| Status | Placement or lineage | Reading rule |
| --- | --- | --- |
| `current` | `canonical current・11c55966-ff12-50b9-b069-7bec6ed37cc4`; the repository overview and implementation status | Describes the current canonical repository boundary. A current document is not by itself field-validity or human-acceptance evidence. |
| `reference` | `direction-binding public slice・245dad95-accf-581c-8b0a-ae1c1f557de4`; `direction-binding-audit.md` and the undated contract/design guides | Explains intended meaning and constraints. Machine schemas and verified behavior outrank explanatory prose. |
| `evidence` | Date- and subject-bound records under `docs/audits/` and `validation/` | Supports only the recorded subject, source digest, environment, and observation time. It does not automatically describe the current tree. |
| `archive` | `publication-repaired legacy archive・3fd59352-b0d9-58f6-8279-9309c8960631`; predecessor and superseded historical material | Preserved for history or explicit comparison. The historical Git anchor retains the original bytes; the readable archive includes disclosed publication repairs. It is never a transparent current fallback or truth oracle. |
| `experimental` | `candidate_ref: local vnext candidate・32646741-8cec-5fe3-b9f3-2971a8a787f0`; prototype charters under `docs/prototypes/` except `origin-requirement.md` | Candidate material only. Do not infer adoption, migration, or canonical authority. |
| `local-only` | `derived_from: local feature source snapshot・2b62dfa0-6d90-5c31-ae2d-34ec55c94895`; see the direction-binding source map | Exists outside the canonical repository boundary. Only explicitly selected, digest-bound sources may be integrated; no whole-root copy is authorized. |

## Community and maintenance

- [Contributing](../CONTRIBUTING.md)
- [Support](../SUPPORT.md)
- [Security policy](../SECURITY.md)
- [Code of Conduct](../CODE_OF_CONDUCT.md)
- [Change log](../CHANGELOG.md)
- [MIT License](../LICENSE)

Final acceptance, revision, deferral, rejection, risk acceptance, policy
adoption, and operational cutover remain outside the audit engine.
