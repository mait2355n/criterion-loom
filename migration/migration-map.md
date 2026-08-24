# semantic-guard canonical v1 migration map

> Historical map for the 0.1.0-to-1.0.0 canonicalization. The current 1.1.0
> surface additionally includes the independent direction-binding audit; use
> the root README and `PUBLIC-SNAPSHOT.md` for the current public inventory.
> This map remains authoritative only for the difference classes and migration
> boundaries recorded here.

Status: the requirement-relation vertical slice is canonical in the 1.0.0
repository and package identity. Practical-domain shadow adjudication,
operational default cutover, policy adoption, and final human acceptance remain
pending. This map does not authorize those decisions.

## Boundary

The legacy implementation remains an explicitly selected compatibility target.
It is not the truth oracle for canonical v1. A difference is classified before
it is treated as a regression.

## Difference classes

| Class | Meaning | Default disposition |
| --- | --- | --- |
| `preserved_contract` | Public input or bounded output meaning intentionally remains compatible. | Require matching contract tests. |
| `corrected_legacy_defect` | Canonical v1 differs because the legacy result violated a v1 invariant. | Preserve evidence and accept only with an adversarial test. |
| `intentional_contract_change` | The public meaning or shape changes by design. | Require versioning, migration notes, and human review. |
| `vnext_regression` | Canonical v1 loses required behavior without an adopted reason. The token is retained as a stable historical wire value. | Block the affected transition. |
| `incomparable` | Inputs, profiles, coverage, or trust assumptions differ. | Report both results without ranking them. |
| `not_implemented` | The legacy capability has not yet been migrated. | Keep the legacy route and record the gap. |

## Migration order

1. Constitution, schemas, and conformance invariants.
2. Obligation-scoped state and fail-closed aggregation.
3. Functional requirement relation audit vertical slice.
4. Morphology and dependency-provider contracts with source alignment.
5. Legacy shadow comparison at the external boundary.
6. Request-audit compatibility adapter.
7. Plan, diff, convention, finish, and acceptance material in separate slices.
8. Agent-action assurance only after trusted observers and provenance inputs exist.

Repository and package canonicalization covers steps 1 through 6 for the
requirement-relation slice. Step 7 onward, and practical-domain adjudicated
shadow evidence for step 5, remain open. Canonicalization does not mark them
complete and does not turn the frozen predecessor into a transparent fallback.

## Remaining operational transition gates

- No critical unresolved obligation is projected as `pass`.
- Analyzer failure and partial coverage remain visible.
- Candidate evidence cannot create support or release a hold.
- Every active obligation has exactly one result.
- Source spans and provider provenance survive serialization.
- Adversarial tests cover negation, quotation, reporting, non-adoption,
  condition, modality, multiple records, and wrong attachment.
- Shadow differences are classified, not averaged into one score.
- Human acceptance remains outside the audit engine.

These gates govern an operational default-route change and predecessor
retirement. The repository/package canonical-promotion decision is recorded
separately in `docs/canonical-promotion-decision.md`.
