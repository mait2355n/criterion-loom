# 公開位置付けメモ

この文書は、Criterion Loomを公開repositoryの読者へ説明する時の
主張範囲を固定する補助記録である。目的は、成果を小さく見せることでは
なく、過大主張で信頼を損なわない範囲に説明を揃えることにある。

package / CLI / MCP server名は互換性のため`semantic-guard`のまま扱う。

## 読み手と使い方

対象読者は、READMEを読んだ後にCriterion Loomの位置付け、主張できる
範囲、未検証の範囲を短時間で確認したい技術者と保守者である。この文書は
利用者向け取説ではなく、公開説明のclaim boundaryを確認するために使う。

## 一文で言うなら

Criterion Loomは、CodexなどのAIエージェントを用いた開発作業で、
初期探索、要求、決定状態、計画、差分、完了証拠をCLI / MCP server /
Codex skillから監査できる形にした意味先行監査ツールである。

## 公開名と四本柱

- **Criterion Loom**: 全体の公開名。
- **Loom Guide**: Codex skill導線。技術名は`semantic-implementation`。
- **Need Thread**: 要求監査。技術commandは`audit-request`。
- **Plan Warp**: 計画監査。技術commandは`audit-plan`。
- **Change Weft**: 実装監査。技術commandは`audit-diff`と`finish-check`。

## 主張できること

- `semantic-guard`はlocal CLIとMCP serverとして動く。
- `explore-request`は、初期案から対象利用者の仮説、重大な曖昧点、聞くべき質問、仕様書の輪郭を軽量に取り出す。
- `llm-explore-request`は、入力と文脈から取れる情報をLLMがfact / inference / hypothesis / unknown / pending decisionに分け、欠けている重要情報を質問として返す。
- Need Thread、Plan Warp、Change Weftとして、要求監査、計画監査、差分監査、完了確認を持つ。
- trace report、fixture評価、LLM reviewer、acceptance review bundleという支援面を持つ。
- 規則ID、欠落項目、修正方針、非発火規則、論理trace summaryなどをJSONで返す。
- 共通の監査結果schemaと、rule catalogから検出器への対応表を公開できる。
- `doctor`で導入時のPython、schema、MCP依存、CI、fixture状態を確認できる。
- LLM reviewerは中途監査として扱い、最終受入判断を人間側へ残す。
- acceptance review bundleのschemaを持ち、`final_human_decision.status`を人間判断まで`pending`に保つ。
- fixtureと単体試験で、既存の監査規則が壊れていないかを確認できる。
- Loom Guide、つまりCodex skill `semantic-implementation`から、要求、計画、差分、完了確認へ自然に辿れる。

## 主張しないこと

- 任意の要求文を高精度に理解できる、とは言わない。
- 脆弱性走査、法務確認、品質部門の判定、配布可否判定は担当しない。
- LLMの判断を人間の最終判断に置き換えられる、とは言わない。
- fixture評価のpassを、一般文書に対する統計的な精度と混同しない。
- 形式手法や網羅的な仕様検証を実現したものではない。

## 実演command

```sh
uv run --python 3.13 --project . semantic-guard --help
uv run --python 3.13 --project . semantic-guard explore-request --text "割り勘アプリを作りたい"
uv run --python 3.13 --project . semantic-guard llm-explore-request --text "割り勘アプリを作りたい" --execute
uv run --python 3.13 --project . semantic-guard audit-request --kind document --file README.ja.md
uv run --python 3.13 --project . semantic-guard evaluate-fixtures
uv run --python 3.13 --project . semantic-guard doctor
uv run --python 3.13 --project . semantic-guard audit-result-schema
uv run --python 3.13 --project . semantic-guard rule-detector-map
uv run --python 3.13 --project . python -m unittest discover -s tests -v
```

技術者に説明する時は、`audit-request`のJSON outputで`findings`、
`missing`、`details.logical_trace_summary`、`details.non_emitted_rules`
を見る。概要だけで足りる時は、`status`と`next_actions`から読む。

## 評価観点

公開説明では、次の観点で読む。

- 要求工学: 受入基準、検証方法、非目標、利害関係者、品質制約、不確実性を露出する。
- 計画工学: 作業分解、依存順序、進捗制御、撤回、決定門、証拠を点検する。
- software systems engineering: 公共契約、識別子、永続化、失敗処理、運用観測、依存関係、試験義務を見る。
- 人間判断境界: LLMは補助材料を作るだけで、最終受入は人間が行う。

## 公開repositoryで見る場所

- `README.md`: 英語の全体説明。
- `README.ja.md`: 日本語の全体説明。
- `docs/ja/naming.md`: 公開名と技術名の対応。
- `docs/ja/quickstart.md`: 動かし方。
- `docs/calibration-report-2026-06-05.md`: fixture評価snapshot。
- `docs/rule-model.md`: 規則model。
- `docs/acceptance-review-bundle.md`: 人間最終判断束。
- `schemas/`: 監査結果、request exploration review、acceptance bundle、reviewer outputのschema。
- `skills/semantic-implementation/`: Codex skillとしての利用導線。
- `tests/`: 単体試験とfixture。

## 現在の限界

Criterion Loomの`semantic-guard`実装は、公開可能なv0.1ツールとして
CLI、MCP server、Codex skill、schema、fixture、単体試験、導入確認command
を備えている。強みは、LLMの曖昧な自己点検を外部化し、足りない判断材料を
JSONと文書で残せることにある。

一方で、自然言語理解の広さ、誤検出率の実地測定、多言語文体への耐性、
大規模codebaseでの運用評価は、成熟した一般性能としてはまだ主張しない。
公開説明では、「監査思想、CLI / MCP実装、試験、fixture、文書化、公開
snapshotまで一貫して組んだv0.1ツールであり、監査性能と適用範囲を継続的に
改善している」と説明する。
