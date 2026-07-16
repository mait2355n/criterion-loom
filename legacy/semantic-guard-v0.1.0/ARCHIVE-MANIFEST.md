# semantic-guard 0.1.0 archive manifest

Archive id: `archive.semantic-guard.v0.1.0`

Archived on: 2026-07-17

Source version: `semantic-guard 0.1.0`

Historical Git anchor: annotated tag `v0.1.0`, commit `e0a3dd39f17385b66f6361ade25eb44bed6e1ab3`

Machine-readable manifest: `ARCHIVE-MANIFEST.json`

## Purpose

This directory preserves the predecessor source, tests, schemas, Skill, and documentation needed to understand and explicitly reproduce the 0.1.0 line. It is not part of the canonical v1 package and is not an actively maintained second implementation.

## Authority boundary

- The archive is read-only historical and compatibility material.
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

The repository archive is a readable source snapshot, not the execution trust root used by canonical `shadow-compare`. Controlled shadow comparison requires a separately operator-owned external legacy root whose interpreter, adapter, baseline manifest, expected relative paths, and digests satisfy the v1 runner.

A private pre-v1 recovery archive and checksum manifest exist outside this public tree. Their existence is recovery evidence only; private filesystem paths and bundle contents are deliberately not published here.

The machine-readable snapshot digest covers every regular file below this archive root except `ARCHIVE-MANIFEST.json`. For each path sorted by UTF-8 relative-path bytes, calculate the file SHA-256 and byte length, encode `sha256 <hex> <size> <relative-path>\n`, concatenate the records, then calculate the SHA-256 of that byte sequence. This digest identifies the public repository archive; it is independent from the historical Git tree and private recovery archive digests.

## Modification rule

Do not modify this directory during ordinary v1 development. If a necessary compatibility or security correction is authorized, record the decision, preserve the former digest or Git object, update this manifest, and state that the result is a repaired archive rather than the original 0.1.0 snapshot.
