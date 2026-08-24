# 公開成果物と証拠境界

> **歴史境界（0.1.0 公開用修復済み archive）。** この文書は 0.1.0 系の記録時点に
> おける predecessor を説明するもので、現行 1.x の状態・運用手順ではない。原 byte
> の権威は tag `v0.1.0` / commit `e0a3dd39f17385b66f6361ade25eb44bed6e1ab3` にある。

この文書は、Criterion Loom の 0.1.0 公開成果物から観測できる実装範囲と、そこからは主張できない範囲を分ける補助資料である。比較順位や実地価値の根拠ではない。

package / CLI / MCP server 名は互換性のため `semantic-guard` のまま扱う。

## 読み手と使い方

対象読者は、公開成果物の技術範囲を短時間で確認したい読者と保守者である。用途は、詳細設計を読む前に、archive から観測できる実装、記録された command、未実装または未検証の範囲を切り分けることである。

## 一文で言うなら

0.1.0 記録上の Criterion Loom は、LLM / Codex を使った開発で暗黙化しやすい初期探索、要求、決定状態、計画、差分、完了証拠を、CLI / MCP server / Codex skill の監査対象として外部化する試作である。

## 公開名と四本柱

- **Criterion Loom**: 全体の公開名。
- **Loom Guide**: Codex skill 導線。技術名は `semantic-implementation`。
- **Need Thread**: 要求監査。技術 command は `audit-request`。
- **Plan Warp**: 計画監査。技術 command は `audit-plan`。
- **Change Weft**: 実装監査。技術 command は `audit-diff` と `finish-check`。

## Archive で観測できる成果物と機構

- Archive には `semantic-guard` の CLI / MCP server 実装が含まれる。現在環境での作動はこの文書だけでは確立しない。
- `explore-request` には、対象利用者の仮説、重大な曖昧点、質問、仕様書輪郭を返す command surface が記録されている。
- `llm-explore-request` には、入力と文脈を fact / inference / hypothesis / unknown / pending decision に分け、検出した不足を質問として返す schema と実行経路が記録されている。抽出や質問の網羅性は保証しない。
- Need Thread、Plan Warp、Change Weft という表示名に対応する要求監査、計画監査、差分監査、完了確認の command が記録されている。
- Trace report、fixture 評価、LLM reviewer、acceptance review bundle の実装・文書・schema が archive に含まれる。
- 監査結果には、規則 ID、欠落項目、修正方針、非発火規則、論理 trace summary などの JSON 欄が記録されている。
- 共通の監査結果 schema と、rule catalog から検出器への対応表が archive に含まれる。
- `doctor` command は Python、schema、MCP 依存、CI、fixture 状態を点検するものとして記録されている。
- LLM reviewer を中途監査に留め、最終受入判断を人間側へ残す設計と、`final_human_decision.status` を持つ acceptance bundle schema が記録されている。
- Fixture と単体試験は archive に含まれるが、その存在や過去の pass は現在環境または一般入力での妥当性を証明しない。
- Codex skill `semantic-implementation` には、要求、計画、差分、完了確認への 0.1.0 導線が記録されている。

## この文書からは主張できないこと

- 任意の要求文を高精度に理解できる、とは言わない。
- 脆弱性走査、法務確認、品質部門の判定、配布可否判定の担当ではない。
- LLM の判断を人間の最終判断に置き換えられる、とは言わない。
- fixture 評価の pass を、一般文書に対する統計的な精度と混同しない。
- 形式手法や網羅的な仕様検証を実現したものではない。

## 0.1.0 記録上の実演 command

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

技術読者は、記録上の `audit-request` JSON で `findings`、`missing`、`details.logical_trace_summary`、`details.non_emitted_rules` を確認できる。`status` と `next_actions` だけから監査の妥当性や実地価値を判断してはならない。

## 評価観点

公開成果物を評価する時の観測軸は次のとおり。

- 要求工学: 受入基準、検証方法、非目標、利害関係者、品質制約、不確実性を露出する。
- 計画工学: 作業分解、依存順序、進捗制御、撤回、決定門、証拠を点検する。
- ソフトウェアシステム工学: 公共契約、識別子、永続化、失敗処理、運用観測、依存関係、試験義務を見る。
- 人間判断境界: LLM は補助材料を作るだけで、最終受入は人間が行う。

## 公開成果物として参照する場所

- `README.md`: 英語の全体説明。
- `README.ja.md`: 日本語の全体説明。
- `docs/ja/naming.md`: 公開名と技術名の対応。
- `docs/ja/quickstart.md`: 動かし方。
- `docs/calibration-report-2026-06-05.md`: fixture 評価 snapshot。
- `docs/rule-model.md`: 規則 model。
- `docs/acceptance-review-bundle.md`: 人間最終判断束。
- `schemas/`: 監査結果、request exploration review、acceptance bundle、reviewer output の schema。
- `skills/semantic-implementation/`: Codex skill としての利用導線。
- `tests/`: 単体試験と fixture。

## 証拠境界を含む説明

この文書の記録時点における Criterion Loom の `semantic-guard` 実装は、小さな決定論規則群と fixture による校正を持つ研究試作である。実装上観測できる特徴は、LLM の自己点検から監査項目を外部化し、検出した判断材料の不足を JSON と文書へ記録する出力面にある。同種道具に対する優位性や実地での改善効果は、この説明だけでは立証されない。

一方で、自然言語理解の広さ、誤検出率の実地測定、多言語文体への耐性、大規模 codebase での運用評価は、この記録時点の証拠からは主張できない。公開成果物から確認できる範囲は、監査模型、CLI / MCP 実装、試験、fixture、文書、公開 snapshot が一つの archive に収録されていることまでである。
