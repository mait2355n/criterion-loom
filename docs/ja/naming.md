# Criterion Loom命名整理

## 目的

Criterion Loom命名表は、公開名と、既存のpackage / CLI / MCP / skill名の対応を固定する文書だ。

## 対象読者と用途

README、repository description、release note、貢献案内を書く時に使う。公開名と技術名を混同しないための文書である。

## 名前対応

| 公開名 | 意味 | 技術上の実体 |
| --- | --- | --- |
| **Criterion Loom** | 全体の公開project名、監査体系の包括名。 | repository: `criterion-loom`; packageは`semantic-guard`のまま |
| **Loom Guide** | Codexに監査手順を辿らせるskill導線。 | `skills/semantic-implementation/` |
| **Need Thread** | 必要、利害関係者、範囲、検証、品質、優先順位、不確実性を見る要求監査。 | `semantic-guard audit-request` |
| **Plan Warp** | 作業分解、順序、リスク、妥当性確認、進捗、撤回、証拠を見る計画監査。 | `semantic-guard audit-plan` |
| **Change Weft** | 差分と完了主張について、意味、公共契約、失敗処理、試験、文書、運用、証拠を見る実装監査。 | `semantic-guard audit-diff` / `semantic-guard finish-check` |

## 残す技術名

Python package、CLI command、MCP serverは互換性のため`semantic-guard`名を残す。

```sh
uv run --python 3.13 --project . semantic-guard --help
uv run --python 3.13 --project . semantic-guard-mcp
```

skill directoryはCodexの読み込み名として`semantic-implementation`を残す。

## 契約と範囲

Criterion Loom命名表は命名契約を示す文書であり、CLIのJSON形状を変えない。

Criterion Loomの各commandは、引き続き`semantic-guard`の監査欄である
`phase`、`status`、`score`、`findings`、`missing`、`next_actions`、
`details`を返す。名前対応は、それぞれのcommand群を公開説明でどう呼ぶかを示すだけである。

技術上の根拠はrepository layoutに置く。packageとcommand名は
`pyproject.toml`、公開概要は`README.md`、Loom Guideのskill本文は
`skills/semantic-implementation/`に置く。

## 支援面

次のcommandは四本柱を支えるが、公開上の別柱ではない。

- `understand-target`: 変更対象の理解確認。
- `trace-report`: 要求、計画、差分、完了証拠の追跡報告。
- `llm-review-*`と`review-if-needed`: LLM中途監査材料。
- `acceptance-bundle-*`: 人間最終判断のための受入束。
- `evaluate-fixtures`: local calibration評価。

## 命名規則

公開projectを語る時は **Criterion Loom** を使う。package、CLI、MCP設定、schema、code pathを語る時だけ`semantic-guard`を使う。

Loom Guide、Need Thread、Plan Warp、Change Weftは別製品ではなく、Criterion Loomの構成要素である。
