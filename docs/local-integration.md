# 結合版の利用手引

開発版 `semantic-guard 1.2.0.dev0` は、基幹 v1、工程別監査、統治付き候補を
同じ配布物に収める。使う入口で入力・結果契約を選ぶ。結果を合算したり、
旧系の `pass` を基幹 v1 や正式保証の判定へ変換したりはしない。

## 入口を選ぶ

| 用途 | CLI | MCPサーバー | 結果の扱い |
| --- | --- | --- | --- |
| 構造化した要求の関係・方向表現 | `semantic-guard audit-requirement` / `audit-direction-binding` | `semantic-guard-mcp` | 基幹 v1 の既存契約 |
| 要求・計画・差分・完了・規約・成果物所属など | `semantic-guard workflow COMMAND` | `semantic-guard-workflow-mcp` | 旧系を拡張した workflow 固有契約 |
| 統治資料と未解決義務を伴う要求監査 | `semantic-guard candidate audit-requirement` | `semantic-guard-vnext-mcp` | `governed-requirement-audit/v1` 候補契約 |

`semantic-guard-workflow COMMAND` と `semantic-guard-vnext COMMAND` は、各々の
専用 CLI でもある。MCPは基幹4工具、workflow 27工具、候補3工具を別サーバーで
公開する。既存の `semantic-guard-mcp` に別契約の工具を混入させない。

```sh
uv sync --locked
uv run --locked semantic-guard --version
uv run --locked semantic-guard workflow --help
uv run --locked semantic-guard workflow audit-plan --file plan.txt
uv run --locked semantic-guard workflow audit-diff --file change-summary.txt
uv run --locked semantic-guard workflow finish-check --file completion-evidence.txt
uv run --locked semantic-guard candidate audit-requirement --file requirement.txt
```

`plan.txt`、`change-summary.txt`、`completion-evidence.txt` は、それぞれ監査する
計画・変更説明・完了証拠の UTF-8 本文である。候補の `requirement.txt` は基幹と同じ
七項目（Purpose、User、Scenario、Expected result、Acceptance criteria、
Verification method、Evidence）の要求本文を受け取るが、結果の意味と終了値は同一ではない。

候補は統治未成立を `block` とし、既定で JSON を出して終了値 `3` を返す。
これは起動失敗ではない。候補の `--fail-on never` は終了値だけを輸送成功として
扱う明示選択であり、未解決義務や正式権限なしの状態は変更しない。
基幹の終了値方針は[基幹の運用手引](operations.md#終了コードと監査状態)を参照する。
各CLIは監査結果のJSONを標準出力へ、引数・入力形式の診断を標準エラーへ出す。
引数不正の終了値は `2`。workflowの監査結果は `phase / status / findings` などの
旧系項目を持ち、基幹と候補の `schema_version` 付き結果へ自動変換しない。

## 資源と出所

基幹は `semantic_guard`、workflowは `semantic_guard_workflow`、候補は
`semantic_guard_vnext` の Python 名前空間を使う。スキーマ・規約・例題・候補資料は
各パッケージの専用領域から読む。同名の `audit-result.schema.json` を共有せず、
作業ディレクトリや隣接パッケージの資料を代用品として探索しない。

結合基線は、公開側コミット `0a38d9bb82c593ccdd794ec08fbaf514dea135a9` と
ローカル開発側コミット `eb34d0f9c81342ad4f0ed6bac42c3614d9424fd2` である。
移植元のパス・ハッシュ値・移植先・変換範囲は
[`workflow-migration.json`](../integration/workflow-migration.json) と
[`candidate-migration.json`](../integration/candidate-migration.json) に記録する。
これらは内部の移植記録であり、公開監査結果のスキーマではない。

workflowのコード分割や名前空間変更で入力・出力の版を基幹v1へ読み替えない。
共通の原型を持つ実装も、現段階では各契約の回帰試験を保つため個別に保持する。
古い `legacy/semantic-guard-v0.1.0/` 保存版は変更しない。

## 実行と採択の境界

工程別監査を選ぶと、その契約による監査が実行される。外部LLMの実行機能は
呼出元が別途選ぶ。MCPへの接続だけで審査ジョブや外部コマンドを開始しない。
非同期のLLM開始工具は、呼び出した時点で実行を開始するため、資料読取用の
工具として扱わない。

候補のH1/H2規則・工程資料を同梱しても、人間の採択や正式な判定権限は成立しない。
U10 brokerコードの同梱は特権導入、鍵生成、署名、環境採択又は運用開始ではない。
通常の要求監査はU10の特権処理を起動しない。既存 `shadow-compare` は、指定された旧版基線との
比較を続ける。基幹 v1 と候補を比較する工具へ暗黙に変わることはない。

## 検証と残る結合

基幹の既存試験に加え、`workflow_tests/`、`candidate_tests/` と
`tests/test_integrated_interfaces.py` でCLIを呼び、返されたJSONの契約名・監査工程・終了値と、
別系統を呼び出した前後の基幹結果の一致を検査する。
配布物は `scripts/verify_packaged_contracts.py` で別環境へ導入し、ソースの位置に
依存せず資源が読めることと、各結果契約が区別されることを確かめる。
試験の移植範囲と除外理由は上記の移植記録に残す。
結合後の試験結果、配布物のハッシュ値、MCP実接続の証拠と未検証項目は
[`verification.json`](../integration/verification.json) にまとめる。

この開発版が結合するのは呼出経路と配布である。各監査結果を横断して一つの判定へまとめる
意味変換、重複実装の共通化、実地妥当性、未採用規則の採択、稼働MCPの切替は
別の課題として残る。他の開発枝にある配布強化・実地標本・引渡し投影も、この基線の
結合範囲には含めない。過去の試験記録を結合版の試験証拠として流用しない。
