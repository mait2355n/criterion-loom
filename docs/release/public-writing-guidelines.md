# Public Writing Guidelines

## Purpose

This file defines wording rules for public Criterion Loom documents. Use it
when editing `README.md`, `README.ja.md`, release notes, comparison material,
or companion-skill documentation.

The goal is not decorative style. The goal is to keep public claims concrete:
what the tool returns, what an agent can revise from it, what is verified, and
what is still outside the tool.

## Audience And Use

Maintainers use this file before committing public prose. It is meant for
README copy, release notes, comparison documents, and companion-skill
descriptions that explain what Criterion Loom does.

Use it as a wording check after the technical content is already true. This
file does not replace feature verification, schema validation, fixture runs, or
human release review.

## Scope

These rules cover public wording and claim boundaries only. They do not define
runtime behavior, detector semantics, security posture, package distribution, or
release approval.

## Core Rules

- Prefer operation verbs over ability verbs. Write what the tool returns,
  extracts, separates, records, fixes as a regression check, or leaves to human
  judgment.
- Tie improvement claims to a mechanism: phase separation, structured findings,
  rule catalog, detector mapping, fixture / corpus records, diagnostics, or
  human review boundaries.
- Use `publishable v0.1` or `公開可能な初版` only for the repository surface:
  CLI, MCP server, companion skill, schemas, fixtures, doctor, and public docs.
- Do not imply broad natural-language accuracy, formal requirements proof,
  production approval, security certification, or replacement of human
  judgment.
- When a claim says something can improve, say what artifact changes next:
  rule wording, detector code, fixture expectation, corpus item, output
  contract, README wording, or companion-skill routing.

## Japanese Wording

Avoid vague helper phrases when a concrete operation is available.

| Avoid | Prefer |
| --- | --- |
| 外へ出す | JSON として返す / 監査結果として抽出する / 診断として露出する |
| 試験できる材料 | 退行検査できる材料 / 検証可能な材料 |
| 直せる | 修正対象を切り分ける / 指摘に基づいて修正する |
| 見つけやすい | 特定しやすい / 検出できる |
| 追える | 確認できる / 辿れる / 対応づけられる |
| 改善できる | 規則、検出器、fixture、corpus、文書へ戻して改善する |
| 材料になる | 判断材料として使う / 補填候補として扱う |

Prefer direct public-document sentences:

```text
Criterion Loom は、監査の挙動を曖昧な総評ではなく、構造化され、退行検査できる材料として抽出する。
```

Avoid softer process prose when it hides the operation:

```text
監査の挙動を曖昧な総評ではなく、構造化され、試験できる材料として外へ出す。
```

## English Wording

Use concrete verbs in the same way.

| Avoid | Prefer |
| --- | --- |
| can improve | has a feedback path through rules, detectors, fixtures, corpus, and diagnostics |
| makes things visible | returns JSON diagnostics / exposes structured findings |
| testable material | regression-checkable material |
| helps fix it | identifies the revision target / supplies repair hints |
| broad finished-state claims | publishable v0.1 surface is in place |
| proof | local regression evidence / heuristic trace / diagnostic record |

## Claim Boundary

Allowed:

- `Criterion Loom has its publishable v0.1 initial-release surface in place.`
- `公開可能な初版としては完成済みである。`
- `The output gives Codex revision targets and also supports human final review.`
- `fixture / corpus records improve local regression coverage.`

Do not write:

- `Criterion Loom proves request correctness.`
- `Criterion Loom approves AI output.`
- `Fixture pass rate proves general accuracy.`
- `The reviewer decides final acceptance.`
- `trace-report proves causal traceability.`

## Review Checklist

Before committing public prose, check:

- Does each strong claim name the concrete evidence or boundary?
- Are `できる`, `外へ出す`, `材料`, and `改善` backed by an operation?
- Does `完成済み` refer only to the public v0.1 surface?
- Does the text preserve the human final-decision boundary?
- Does the text say how feedback returns to rules, detectors, fixtures, corpus,
  documents, or the Codex work loop?
