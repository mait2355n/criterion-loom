# semantic-guard 0.1.0 archive manifest

Archive id: `archive.semantic-guard.v0.1.0`

Archived on: 2026-07-17

Source version: `semantic-guard 0.1.0`

Historical Git anchor: annotated tag `v0.1.0`, commit `e0a3dd39f17385b66f6361ade25eb44bed6e1ab3`

Publication repair: 2026-08-24

Machine-readable manifest: `ARCHIVE-MANIFEST.json`

## Purpose

This directory is a publication-repaired historical archive of the predecessor source, tests, schemas, Skill, and documentation needed to understand and explicitly reproduce the 0.1.0 line. The annotated Git anchor above is the authority for the original 0.1.0 bytes. This directory is not the original byte-for-byte snapshot, is not part of the canonical v1 package, and is not an actively maintained second implementation.

## Authority boundary

- The archive is publication-repaired, frozen historical and compatibility material.
- Its output does not override the v1 constitution, schemas, or conformance tests.
- A matching old result does not prove that the v1 result is correct.
- Dated records retain their original subject and date.
- Human acceptance, practical-domain validity, and operational authority are not inherited from this archive.

## Included surfaces

- 0.1.0 package metadata and lockfile
- former `src/semantic_guard/` implementation
- former CLI and MCP implementation
- former schemas, tests, fixtures, and field corpus
- former companion Skill
- former README, contribution, security, publication, and design documents
- former GitHub templates and CI definition

Generated environments, caches, build outputs, credentials, local backups, and private recovery bundles are not part of this public archive.

## Integrity and recovery

The repository archive is a readable, publication-repaired source snapshot, not the original byte snapshot and not the execution trust root used by canonical `shadow-compare`. Controlled shadow comparison requires a separately operator-owned external legacy root whose interpreter, adapter, baseline manifest, expected relative paths, and digests satisfy the v1 runner.

A record dated 2026-07-17 reported a private pre-v1 recovery archive and checksum manifest outside this public tree. This public archive does not establish their current availability; the dated record is recovery evidence only, and private filesystem paths and bundle contents are deliberately not published here.

Digest provenance before the current expansion is:

- `e904692a1170df7b67f4fb4d9fd6331e8ba1cddc3f69d8fdeff0747f402948c5`: previously recorded public archive digest before the 2026-08-24 publication repair, fixed at `git+https://github.com/mait2355n/criterion-loom.git@83bdd6deb86aeaa3c99515c013a1d30984a719e1#path=legacy/semantic-guard-v0.1.0`.

The machine-readable manifest keeps the public digest lineage as `e904...` to the current `snapshot.digest`, with `e904...` in `previous_snapshot_digest`. Neither digest replaces the annotated Git anchor as original-byte authority.

The current machine-readable snapshot digest covers every repository-tracked regular file below this archive root except `ARCHIVE-MANIFEST.json`; ignored environments and caches are outside the population. For each included path sorted by UTF-8 relative-path bytes, calculate the file SHA-256 and byte length, encode `sha256 <hex> <size> <relative-path>\n`, concatenate the records, then calculate the SHA-256 of that byte sequence. The current digest is stored only in `ARCHIVE-MANIFEST.json` so editing this Markdown file does not create a self-reference cycle. These digests identify public repository snapshots; neither replaces the historical Git anchor or any private-recovery digests reported by the dated record.

## 2026-08-24 publication repair

The repair gives all 44 in-scope public Markdown documents a direct-landing historical boundary, weakens exhaustive elicitation wording to a bounded attempt-and-gap-listing claim, replaces insulting or private-conversation-dependent rationale with technical record-bound explanations, and separates dated local or private evidence from unverified current availability. Only documentation, companion-Skill prose, and these archive manifests changed. Runtime code, schemas, tests, fixtures, and the legacy pull-request template did not change. The machine-readable manifest records the exact changed-file set, reason, ordered digest history, current digest, and repair date.

## Modification rule

Do not modify this repaired directory during ordinary v1 development. If another necessary publication, compatibility, or security correction is authorized, record the decision, preserve the prior digest and Git anchor, update both manifests, and state that the result is a later repaired archive rather than the original 0.1.0 snapshot.
