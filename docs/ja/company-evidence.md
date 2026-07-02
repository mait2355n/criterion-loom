# 実績証明用説明

この文書は、Criterion Loom を会社や第三者へ「自分が作った技術成果」として説明するための補助資料である。目的は、成果を小さく見せることではなく、過大主張で信用を毀損しない範囲に主張を固定することにある。

package / CLI / MCP server 名は互換性のため `semantic-guard` のまま扱う。

## 読み手と使い方

対象読者は、採用・評価・社内共有などで、技術成果の範囲を短時間で確認したい人である。用途は、詳細設計を読む前に、成果として主張できる範囲、実演 command、未成熟な範囲を切り分けることである。

## 一文で言うなら

Criterion Loom は、LLM / Codex を使った開発で暗黙化しやすい初期探索、要求、決定状態、計画、差分、完了証拠を、CLI / MCP server / Codex skill から検査できる形にした意味先行の監査試作である。

## 公開名と四本柱

- **Criterion Loom**: 全体の公開名。
- **Loom Guide**: Codex skill 導線。技術名は `semantic-implementation`。
- **Need Thread**: 要求監査。技術 command は `audit-request`。
- **Plan Warp**: 計画監査。技術 command は `audit-plan`。
- **Change Weft**: 実装監査。技術 command は `audit-diff` と `finish-check`。

## 主張できる成果

- `semantic-guard` local CLI と MCP server として動く。
- `explore-request` で、初期案から対象利用者の仮説、重大な曖昧点、聞くべき質問、仕様書の輪郭を軽量に取り出せる。
- `llm-explore-request` で、入力と文脈から取れる情報を LLM が fact / inference / hypothesis / unknown / pending decision に分け、欠けている重要情報を質問として返せる。
- Need Thread、Plan Warp、Change Weft として、要求監査、計画監査、差分監査、完了確認を持つ。
- trace report、fixture 評価、LLM reviewer、acceptance review bundle という支援面を持つ。
- 規則 ID、欠落項目、修正方針、非発火規則、論理 trace summary などを JSON で返す。
- 共通の監査結果 schema と、rule catalog から検出器への対応表を公開できる。
- `doctor` で導入時の Python、schema、MCP 依存、CI、fixture 状態を確認できる。
- LLM reviewer は中途監査として扱い、最終受入判断を人間側へ残す設計にしている。
- acceptance review bundle の schema を持ち、`final_human_decision.status` を人間判断まで `pending` に保つ。
- fixture と単体試験で、既存の監査規則が壊れていないかを確認できる。
- Loom Guide、つまり Codex skill `semantic-implementation` から、要求、計画、差分、完了確認へ自然に辿れる。

## 主張してはいけないこと

- 任意の要求文を高精度に理解できる、とは言わない。
- 脆弱性走査、法務確認、品質部門の判定、配布可否判定の担当ではない。
- LLM の判断を人間の最終判断に置き換えられる、とは言わない。
- fixture 評価の pass を、一般文書に対する統計的な精度と混同しない。
- 形式手法や網羅的な仕様検証を実現したものではない。

## 実演で見せるとよい command

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

説明相手が技術者なら、`audit-request` の JSON 出力で `findings`、`missing`、`details.logical_trace_summary`、`details.non_emitted_rules` を見るとよい。説明相手が非技術者なら、`status` と `next_actions` だけでも目的は伝わる。

## 評価観点

会社に見せる時は、次の観点で説明する。

- 要求工学: 受入基準、検証方法、非目標、利害関係者、品質制約、不確実性を露出する。
- 計画工学: 作業分解、依存順序、進捗制御、撤回、決定門、証拠を点検する。
- ソフトウェアシステム工学: 公共契約、識別子、永続化、失敗処理、運用観測、依存関係、試験義務を見る。
- 人間判断境界: LLM は補助材料を作るだけで、最終受入は人間が行う。

## 成果物として見る場所

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

## 弱点も含めた正直な説明

現時点の Criterion Loom の `semantic-guard` 実装は、小さな決定論規則群と fixture による校正を持つ研究試作である。強みは、LLM の曖昧な自己点検を外部化し、足りない判断材料を JSON と文書で残せることにある。

一方で、自然言語理解の広さ、誤検出率の実地測定、多言語文体への耐性、大規模 codebase での運用評価は、まだ成熟した主張にできない。実績証明としては、「製品を納品した」ではなく、「監査思想、CLI / MCP 実装、試験、fixture、文書化、公開 snapshot まで一貫して組んだ」と言うのが妥当である。
