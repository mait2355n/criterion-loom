# semantic-guard 1.0.0 canonicalization audit

Audit date: 2026-07-17

Audit subject: the promoted repository tree and its intended `semantic-guard 1.0.0` package artifacts

Audit authority: technical audit material only; no automatic release approval or human acceptance

## Record surface

- `context`: determine whether the former contract-first candidate can become the canonical source without misrepresenting maturity or losing the predecessor lineage.
- `current_state`: source, names, documentation, Skill, CI, migration, and archive are aligned; local tests, validators, and distribution checks pass. Git commit binding, hosted CI, publication, and final human acceptance remain pending.
- `action`: bind the verified tree and distributions to the final Git commit, run hosted CI, then present the exact publication evidence and residual risks to the human decision owner.
- `detail_refs`: repository diff, CI run, wheel verification output, `PUBLIC-SNAPSHOT.md`, `docs/canonical-promotion-decision.md`, `docs/migration-v0.1.0-to-v1.0.0.md`.

## Audit criteria

1. Product, distribution, Python, CLI, MCP, schema, and documentation identities do not leave an accidental candidate/default split.
2. The public surface names exactly three CLI commands and three MCP tools.
3. The frozen 0.1.0 source remains identifiable but is not imported, packaged, or represented as the v1 oracle.
4. The four dated `validation/*2026-07-16.json` observations remain byte-preserved and are not promoted into fresh evidence. Public copies that remove terminal-specific paths are separately identified and rebound instead of being represented as byte-identical originals.
5. The verification source, generated projection, schemas, engineering rule pack, tests, wheel resources, installed CLI, and installed MCP surface are reproducible.
6. Claims distinguish local contract conformance from field validity, external authenticity, human adoption, operational qualification, and final acceptance.

## Pre-promotion findings carried forward

- The candidate local contract suite had broad unit and adversarial coverage, but its dated evidence was unbound to the promoted source.
- The predecessor and candidate exposed materially different command surfaces.
- Candidate paths and names appeared in documentation, validation locators, packaging checks, and legacy baseline references.
- The former CI validated only the predecessor implementation.
- The companion Skill described commands absent from the candidate kernel.
- The public copy of `semantic-guard-full-evaluation-2026-07-11.md` redacts two terminal-specific source paths as `<local-source-root>`; the private recovery archive retains the original. The public redaction has its own digest and must not be substituted for the private original without recording which subject was used.
- The public copy of `migration/legacy-baseline-2026-07-16.json` redacts one resolved local-runtime path. The separate 2026-07-17 trust-root capture matched its 155 covered files at capture time but remains `pending_human_acceptance` and is not a correctness oracle.

These findings require canonical name migration, explicit breaking-change documentation, regenerated evidence, CI replacement, and Skill narrowing. They are not cured by changing a package version alone.

## Required verification

```sh
uv lock --check
uv run --locked python -m unittest discover -s tests -v
uv run --locked python scripts/validate_verification_source.py
uv run --locked python scripts/render_verification_projection.py --check
uv run --locked python scripts/validate_engineering_rule_pack.py
uv build
uv run --locked python scripts/verify_packaged_contracts.py \
  --wheel dist/semantic_guard-1.0.0-py3-none-any.whl \
  --sdist dist/semantic_guard-1.0.0.tar.gz
```

CI additionally verifies the installed CLI schema command, the installed MCP tool inventory, and a frozen-legacy smoke path.

## Local verification result

The final local tree produced the following observations:

- `uv lock --check`: passed.
- canonical unit and contract suite: 575 tests passed in 41.775 seconds.
- verification source: all six checks passed; 17 verification items, 17 unresolved items, 52 resolution obligations, 19 resolution paths, and 65 gap records remained explicit.
- generated verification projection: exact match.
- engineering rule pack: schema, mapping, and governance checks passed for 11 candidate rules and 5 sources.
- canonical CLI: version `1.0.0` and exactly three commands observed.
- canonical MCP: exactly three public tools observed.
- frozen legacy suite: all 196 tests passed from an external temporary environment; this is compatibility evidence, not v1 conformance evidence.
- packaged-contract verifier: passed for the final wheel and sdist, including 23 public schemas, 23 MCP schema resources, 3 MCP tools, 10 lifecycle profiles, 11 candidate engineering rules, canonical producer version, installed CLI, and installed MCP entry point.

Final local distribution digests:

- wheel `semantic_guard-1.0.0-py3-none-any.whl`: `dfe0956493f18c8a938f0805ec3e280b33d3c7c800ae922ce654bfe09b2ae551`;
- sdist `semantic_guard-1.0.0.tar.gz`: `419f3dff372e99cfee0bc79b0c75f1797fce69278336f7569688589c49d4b41c`.

These digests bind the locally built artifacts, not a future GitHub-hosted artifact unless that artifact is compared byte-for-byte.

## Evidence table

| Claim | Required evidence | Current disposition |
| --- | --- | --- |
| Canonical source identity is v1.0.0 | final diff, package metadata, CLI/MCP smoke | locally observed; Git commit binding pending |
| Closed local contracts remain valid | full unit suite and validators | locally observed pass |
| Wheel and sdist carry only the intended distribution boundary | trusted local digests and packaged-contract verifier | locally observed pass |
| Installed public surface is callable | isolated installed CLI and MCP inventory checks | locally observed pass |
| Frozen predecessor remains observable | archive manifest and legacy suite | locally observed: tag content is byte-identical outside the two archive manifests, 196 tests passed, and the 155-file public archive manifest digest is `e904692a1170df7b67f4fb4d9fd6331e8ba1cddc3f69d8fdeff0747f402948c5`; external trust-root adoption remains pending |
| Field performance is acceptable | adjudicated practical-domain corpus | not established |
| Candidate policy/profile is adopted | explicit human decision record | not established |
| External AI action is authentic | trusted observer, identity, time, and provenance evidence | not established |
| Operational default cutover is safe | qualification, shadow, rollback, security, and human-use gates | not established |

## Release claim boundary

If all local checks pass, the allowed claim is:

> semantic-guard 1.0.0 is the canonical repository and package implementation of the locally executable, versioned audit contracts and the first requirement-relation vertical slice.

The audit does not permit claims of production readiness, general natural-language accuracy, all-lifecycle workflow coverage, real external-action proof, security certification, human policy adoption, operational default cutover, or irreversible predecessor retirement.

## Human decision

Final acceptance remains pending until the exact final diff, Git commit, CI result, wheel digest, verification output, and residual risks are reviewed by the repository owner.
