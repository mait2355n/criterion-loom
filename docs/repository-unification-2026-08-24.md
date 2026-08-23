# Repository unification record, 2026-08-24

This record separates the logical project, two GitHub repository objects, and
their mutable owner/name labels. The full machine-readable record is
[`migration/repository-unification-2026-08-24.json`](../migration/repository-unification-2026-08-24.json).

## Identity and destination

| Role | Stable entity | GitHub repository ID | Recorded label |
| --- | --- | ---: | --- |
| Logical project | `canonical current・11c55966-ff12-50b9-b069-7bec6ed37cc4` | n/a | Criterion Loom / `semantic-guard` technical package |
| Repository to preserve and transfer | `canonical repository object・51d473df-7d86-466d-a9f4-47a01ff70d44` | `1270877024` | `morie-lene/criterion-loom` before transfer; `mait2355n/criterion-loom` after transfer |
| Repository to retire | `legacy repository object・540faebe-44e4-4a86-9030-389e5c888eb7` | `1284490044` | `mait2355n/criterion-loom` before temporary rename |

The identical repository name did not make the two GitHub objects identical.
Their Git histories had no common ancestor and their final trees differed.
GitHub-native pull requests, releases, Actions history, permissions, and
settings also belong to a repository object rather than to a Git tree.

The repository with ID `1270877024` is therefore the transfer subject. It holds
the current implementation and the richer GitHub-native record. The object
with ID `1284490044` contributes its Git history only; its tree is not silently
promoted as current content.

## History bridge

`legacy history bridge・47d6800e-2b5a-460b-a992-a2effa49feac` is commit
`7c82228f16b02606644e6ba57e1df4986d225f86` with these parents, in order:

1. canonical source main
   `b3848e8691c1a805d42e178f37a2d4b2c2d54851`;
2. legacy main `f07209d380ae680c51d34eb6e491cc4b6bdde623`.

The bridge uses Git's `ours` merge strategy. Its tree is
`4ad14bcaf412c08cd669f221ad950bd70981b0f2`, byte-for-byte the canonical
source tree at the first parent. This gives the legacy commits an explicit
lineage path without treating their content as the implementation winner.

The annotated tag
`legacy-mait2355n-main-before-unification-2026-08-24` points to the recorded
legacy tip so the pre-unification boundary remains directly addressable.

These commits do not change runtime code, dependencies, the lockfile, CI
workflow, authentication or authorization policy, or secret values. The bridge
commit changes only reachability in the Git graph; its tree is identical to its
canonical first parent. The following content commit adds only this migration
record and its documentation-map links. Live owner permissions and security
settings remain external state and are checked again at the transfer gate.

## Backup and transfer gate

Before any GitHub rename or transfer, separate complete Git bundles, GitHub
REST snapshots, and all 11 unexpired source Actions artifacts were stored in
an operator-local archive and checked by SHA-256. The bundle digests are in the
machine-readable record; the binary archive is intentionally not committed.

The legacy GitHub repository must not be deleted until the transferred
`mait2355n/criterion-loom` resolves to repository ID `1270877024`, both
pre-unification main tips are ancestors of canonical main, local and hosted
checks pass, and the transferred GitHub-native surfaces are re-observed. The
deletion target must then be re-read as ID `1284490044` immediately before the
destructive operation.

“Re-observed” is not a box-ticking loophole. Each branch, tag, pull request,
release, Actions record, redirect, permission, and security setting must match
its recorded baseline and required behavior. A missing, degraded, or
owner-invisible surface keeps the gate closed unless it is repaired or a human
separately accepts that exact discrepancy and consequence. All available run
records, job records, logs, and artifacts must be in a verified backup copied
to a separate storage volume; bytes unavailable from their source are recorded
as unavailable, never described as backed up.

The user authorized deletion of repository ID `1284490044` only as the final
operation of this transfer-preserving route and only when every listed gate has
an acceptable result. That conditional destructive authorization is distinct
from final acceptance of the completed migration, which remains pending. An ID
mismatch, unresolved loss, failed check, absent independent-backup receipt, or
material scope change invalidates the deletion authorization.

## Historical names and technical identity

Dated evidence keeps its original `morie-lene/criterion-loom` URLs. Those URLs
record where a pull request or Actions run actually occurred, and GitHub's
transfer redirect is the appropriate compatibility layer. Rewriting them
would make the historical record prettier and less true.

The `semantic-guard` package, CLI, and MCP names also remain unchanged.
Likewise, the existing schema `$id` under `morie-lene.github.io` remains a
stable public identifier in this migration. Repository ownership and technical
contract identity are related, but they are not the same fact.

Status at this commit: `pre_transfer`. A later evidence update must record the
actual transferred repository ID, final main, hosted CI, redirect checks, and
legacy deletion outcome. Human acceptance remains separate from those checks.
