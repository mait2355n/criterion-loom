# クイックスタート

この文書は、Criterion Loom の技術実装である `semantic-guard` を公開 snapshot から動かすための最短手順である。

## 前提

- Python 3.11 以上を使う。以下の例は公開 snapshot の検証用に Python 3.13 で統一する。
- `uv` command を実行できる。
- command は repository または snapshot の root で実行する。

動作確認だけなら、仮想環境を手で作る必要はない。`uv run --python 3.13 --project . ...` で実行する。

## Help を見る

```sh
uv run --python 3.13 --project . semantic-guard --help
```

## 導入状態を診断する

```sh
uv run --python 3.13 --project . semantic-guard doctor
```

`doctor` は Python 版、project file、schema、MCP 依存、任意の `codex` binary、rule-detector 対応、CI workflow、fixture 評価を確認する。`status` が `pass` なら、この snapshot 内の導入前提は揃っている。

## 初期案を探索する

```sh
uv run --python 3.13 --project . semantic-guard explore-request --text \
  "割り勘アプリを作りたい"
```

`explore-request` は、まだ要求文として監査できない案から、対象利用者の仮説、重大な曖昧点、聞くべき質問、仕様書の輪郭を JSON の `details` と `findings` に返す軽量 preflight である。実装計画ではない。

網羅的に問いただす必要がある場合は LLM 版を使う。

```sh
uv run --python 3.13 --project . semantic-guard llm-explore-request --text \
  "割り勘アプリを作りたい" --execute
```

`llm-explore-request` は、入力と context から取れる fact / inference / hypothesis / unknown / pending decision を拾い、そのうえで欠けている重要情報を質問にする。既定は dry-run なので、実行する時だけ `--execute` を付ける。範囲、資料模型、秘匿性、外部権威、受入証拠、人間判断点を変える質問だけを残す。

## 要求を監査する

```sh
uv run --python 3.13 --project . semantic-guard audit-request --text \
  "利用者: 開発者。目的: CLI の監査結果を JSON で確認する。受入基準: status と findings が出力される。検証: command を実行する。証拠: 実行結果を記録する。対象外: UI 実装。"
```

要求監査では、受入基準、検証方法、証拠、非目標、利害関係者、品質制約、優先順位、不確実性などの欠落を見る。

## 文書を監査する

```sh
uv run --python 3.13 --project . semantic-guard audit-request \
  --kind document --file README.ja.md
```

`--kind document` を付けると、要求文ではなく説明文書として見る。目的、読み手、使い方、出力契約、限界、根拠のある主張を検査する。

## 計画を監査する

```sh
uv run --python 3.13 --project . semantic-guard audit-plan --text \
  "目的: README の日本語取説を整える。作業分解: 入口、操作例、公開上の制限説明を追加する。検証: 文書監査と単体試験を実行する。撤回: 追加文書だけを戻す。"
```

計画監査では、作業分解、依存順序、資源見積、リスク対応、進捗制御、変更統制、検証責任、撤回手段、新規依存や抽象化に対する最小性根拠を見る。

## 差分を監査する

```sh
git diff | uv run --python 3.13 --project . semantic-guard audit-diff \
  --intent "日本語取説を追加する"
```

`audit-diff` は、公共契約、失敗処理、運用観測、依存関係、試験義務、意味境界、複雑性増加の変化を拾う。Git repository でない場合は、差分要約を `--text` や標準入力で渡してもよい。

## 完了を確認する

```sh
uv run --python 3.13 --project . semantic-guard finish-check \
  --text "日本語取説を追加した。" \
  --evidence "audit-request --kind document、evaluate-fixtures、unittest を実行した。"
```

`finish-check` は、完了と言ってよいだけの証拠があるかを確認する。単に「実装した」と書いただけでは弱い。

## fixture 評価を実行する

```sh
uv run --python 3.13 --project . semantic-guard evaluate-fixtures
```

fixture 評価は local calibration set の回帰確認である。一般文書に対する統計的な正確性ではない。

## 監査結果 schema と規則対応を見る

```sh
uv run --python 3.13 --project . semantic-guard audit-result-schema
uv run --python 3.13 --project . semantic-guard rule-detector-map
```

`audit-result-schema` は通常の監査結果 JSON 契約を出す。`rule-detector-map` は rule catalog と検出器、predicate、source path の対応を出す。これは保守用の対応表であり、自然文の意味充足を証明するものではない。

## 単体試験を実行する

```sh
uv run --python 3.13 --project . python -m unittest discover -s tests -v
```

公開前、文書追加後、規則変更後は、この command、`evaluate-fixtures`、`doctor` をまとめて実行する。

## MCP server を起動する

```sh
uv run --python 3.13 --project . semantic-guard-mcp
```

Codex から使う場合の設定例は、root の `README.md` にある。MCP は便利な経路だが、CLI と監査核は同じ責務を持つ。MCP が無くても CLI で検証できる状態を保つ。
