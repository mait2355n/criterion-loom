# 日本語文書地図

このdirectoryは、Criterion Loomを日本語で説明・実演するための入口である。

技術名としてのpackage / CLI / MCP serverは`semantic-guard`のまま扱う。

## 対象読者と用途

対象読者は、Criterion Loomを初めて見る技術者、利用前に概要を掴みたい人、公開文書を確認する保守者である。この文書は、詳細設計を読む前に「どの日本語文書を読めばよいか」を判断するために使う。

## 読む順番

初見の人には次の順で見せる。

1. `../../README.ja.md`
2. `naming.md`
3. `quickstart.md`
4. `../calibration-report-2026-06-05.md`
5. `../public-comparison-2026-06-02.ja.md`

## 各文書の役割

- `../../README.ja.md`: 日本語の総合取説。目的、非目標、基本command、出力の読み方。
- `naming.md`: Criterion Loom、Loom Guide、Need Thread、Plan Warp、Change Weftと技術名の対応。
- `quickstart.md`: clone後またはsnapshot rootでの動かし方。
- `../calibration-report-2026-06-05.md`: fixture評価の現時点snapshot。
- `../public-comparison-2026-06-02.ja.md`: MCP server、security scanner、agent skillなどとの比較。

補助記録として`public-positioning-note.md`がある。これは公開説明のclaim boundaryを確認するためのメモであり、公開READMEや利用者向け取説の代わりではない。

## 実行例

公開snapshotのrootから、次のcommandで日本語入口文書を監査できる。

```sh
uv run --python 3.13 --project . semantic-guard audit-request --kind document --file README.ja.md
uv run --python 3.13 --project . semantic-guard llm-explore-request --text "割り勘アプリを作りたい" --dry-run
```

fixture評価と導入状態は次のcommandでJSONとして確認する。

```sh
uv run --python 3.13 --project . semantic-guard evaluate-fixtures
uv run --python 3.13 --project . semantic-guard doctor
```

## 公開契約の読み場所

この入口文書は契約そのものを再定義しない。CLI、MCP、schema、失敗形、標準出力と標準誤出力、終了符号、永続証拠の未確定表示は、rootの`README.ja.md`と`../conventions/README.md`、`../conventions/base-contract.md`、`../../skills/semantic-implementation/references/mcp-contract.md`で確認する。

通常の監査commandはstdoutへJSONを返し、中心fieldは`phase`、`status`、`score`、`findings`、`missing`、`next_actions`、`details`である。使用法の誤りはstderrへargparseのmessageを出し、exit code 2で終わる。監査対象の警告やblockerはstdoutのJSON `status`に残る。

## 出力項目

文書監査の主要な返却項目は、`status`、`score`、`findings`、`missing`、`next_actions`、`details`である。

- `status`: 現在の規則で止めるかどうか。
- `findings`: 監査で検出した不足や警告の一覧。
- `missing`: 文書から見えなかった構造項目。
- `next_actions`: 次に直すべきこと。
- `details`: claim/evidence/limitationや診断情報。

## 注意

この資料群は営業資料ではない。過大な断定を避け、実行可能な成果、検証済みの範囲、未検証の範囲を分けて読ませるための取説である。
