# Documentation map

## Start here

- [Repository overview](../README.md)
- [Implementation status](implementation-status.md)
- [Direction-binding audit public slice](direction-binding-audit.md)
- [Operations](operations.md)
- [Canonical promotion decision](canonical-promotion-decision.md)
- [Migration from 0.1.0](migration-v0.1.0-to-v1.0.0.md)
- [Canonical migration classification map](../migration/migration-map.md)
- [v1.0.0 canonicalization audit](audits/canonicalization-audit-v1.0.0-2026-07-17.md)
- [v1.1.0 direction-binding GitHub integration evidence](audits/direction-binding-integration-2026-08-23.md)

## Status and lineage

The status below is a reading role for a placement, not entity identity. Labels
and paths may change; the UUID on the right of `・` is the identity authority.

| Status | Placement or lineage | Reading rule |
| --- | --- | --- |
| `current` | `canonical current・11c55966-ff12-50b9-b069-7bec6ed37cc4`; the repository overview and implementation status | Describes the current canonical repository boundary. A current document is not by itself field-validity or human-acceptance evidence. |
| `reference` | `direction-binding public slice・245dad95-accf-581c-8b0a-ae1c1f557de4`; `direction-binding-audit.md` and the undated contract/design guides | Explains intended meaning and constraints. Machine schemas and verified behavior outrank explanatory prose. |
| `evidence` | Date- and subject-bound records under `docs/audits/` and `validation/` | Supports only the recorded subject, source digest, environment, and observation time. It does not automatically describe the current tree. |
| `archive` | `frozen legacy archive・3fd59352-b0d9-58f6-8279-9309c8960631`; frozen predecessor and superseded historical material | Preserved for history or explicit comparison. It is never a transparent current fallback or truth oracle. |
| `experimental` | `candidate_ref: local vnext candidate・32646741-8cec-5fe3-b9f3-2971a8a787f0`; `docs/prototypes/` | Candidate material only. Do not infer adoption, migration, or canonical authority. |
| `local-only` | `derived_from: local feature source snapshot・2b62dfa0-6d90-5c31-ae2d-34ec55c94895`; see the direction-binding source map | Exists outside the canonical repository boundary. Only explicitly selected, digest-bound sources may be integrated; no whole-root copy is authorized. |

## Contract and assurance design

- [Direction-binding audit public slice](direction-binding-audit.md)
- [Action evidence and assurance profile](action-evidence-and-assurance-profile.md)
- [Lifecycle profiles](lifecycle-profile-registry.md)
- [Lifecycle trace and composition](lifecycle-trace-and-composition.md)
- [State assessment and requalification](state-assessment-and-requalification.md)
- [Repair loop and responsibility material](repair-loop-and-responsibility-material.md)
- [Field evaluation and ablation](field-evaluation-and-ablation.md)
- [Operational outcome evaluation](operational-outcome-evaluation.md)
- [Operational qualification and transition](operational-qualification-and-transition.md)
- [Secure-operation boundary](secure-operation-boundary.md)
- [Engineering rule-pack governance](engineering-rule-pack-governance.md)

## Historical and prototype material

Files whose names contain a date, and files under `docs/prototypes/`, record the state or design intent at their stated time. Canonical promotion does not rewrite them. They may contain former candidate names and paths; use current contracts and the migration guide for present commands.

The historical full evaluation under `docs/audits/semantic-guard-full-evaluation-2026-07-11.md` remains a digest-bound source referenced by the verification register. It is not the v1.0.0 canonicalization audit.

## Reading rule

Contract schemas and the verification source outrank explanatory prose for field names and machine constraints. A dated report is evidence about its recorded subject only. None of these documents makes the final human acceptance decision.
