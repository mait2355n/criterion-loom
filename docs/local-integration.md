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

## エージェント別の接続

MCP サーバーも付属スキルも、特定のエージェントに依存しない。標準入出力で話せる
クライアントなら同じサーバーを使え、`SKILL.md` の先頭の `name` と `description` を
読むエージェントなら同じスキルを使える。`skills/semantic-implementation/agents/openai.yaml`
は Codex の表示用メタデータであり、他のエージェントは読まない。

| エージェント | MCP サーバーの登録 | スキルの置き場所 |
| --- | --- | --- |
| Claude Code | `claude mcp add semantic-guard -- uv --directory /absolute/path/to/criterion-loom run --locked semantic-guard-mcp` | `skills/semantic-implementation/` を `~/.claude/skills/` 又は作業ディレクトリの `.claude/skills/` へ複写又は連結する |
| Codex | `~/.codex/config.toml` の `[mcp_servers.semantic-guard]` に `command = "uv"`、`args = ["--directory", "/absolute/path/to/criterion-loom", "run", "--locked", "semantic-guard-mcp"]` を書く（Codex の設定書式であり、本リポジトリの試験では実行していない） | `skills/semantic-implementation/` を Codex のスキル置き場へ複写する |
| その他 | `command`、`args`、`cwd` を受ける設定へ、README の JSON 例を写す | `SKILL.md` を読み込める置き場所へ複写する |

workflow の工程別監査を使うときは、登録名と最後の実行名を `semantic-guard-workflow` と
`semantic-guard-workflow-mcp` に替える。接続しただけでは、審査ジョブも外部コマンドも
始まらない。

## 外部LLM査読の実行エージェント

workflow の `llm-review-run`、`llm-explore-request`、`review-if-needed` は、決定的な監査の
後に、隔離した別の査読者へ不足の指摘と補填案を求められる。査読者として動かすエージェントは
`--backend` で選ぶ。どれを選んでも、プロンプトは標準入力へ渡され、返答は同じ JSON
スキーマで検証される。検証に通らない返答は `invalid_review` 又は `invalid_exploration` と
して残り、成功へは変換されない。結果には、どのエージェントが返したかを示す `backend`
が付く。

| `--backend` | 実行されるもの | 返答の読み方 | MCP |
| --- | --- | --- | --- |
| `codex`（既定） | `codex exec --output-schema`（読み取り専用、設定と規則を読まない） | 標準出力の JSON | 可 |
| `claude` | `claude -p --output-format json --json-schema`（道具なし、会話を保存しない、設定・MCP・スキルを読まない） | 封筒の `structured_output`。無ければ `result` の JSON | 可 |
| `command` | `--agent-command` で渡した引数の雛形 | 標準出力の JSON。Markdown のコードフェンスは外す | 不可（CLI 専用） |

```sh
# 既定は codex。外部へ送らず、実行されるコマンドとプロンプトだけを見る。
uv run --locked semantic-guard workflow llm-review-run --file review-input.json

# Claude Code を査読者にする。--execute を付けたときだけ実行する。
uv run --locked semantic-guard workflow llm-review-run --file review-input.json \
  --backend claude --model sonnet --execute

# 任意のエージェント。{model} {schema_path} {schema_json} {working_directory} を置換する。
uv run --locked semantic-guard workflow llm-review-run --file review-input.json \
  --backend command --agent-command "my-agent --model {model} --schema {schema_path}" --execute
```

`--model` を省くと各エージェント既定のモデルを使う（`codex` は `gpt-5.4-mini`、
`claude` は `sonnet`）。`claude` の `--json-schema` は `$schema` と `$id` を解決できないため、
インライン渡しの前にこの二つを除く。`--agent-binary` で実行ファイルの場所を替えられる。

確認の範囲: `claude` は Claude Code 2.1.302 に対し、実際の査読スキーマとプロンプトで
一度実行し、`valid_review` を得た（2026-10-17、モデル `haiku`）。他の版・モデルでの動作や、
査読内容の質は確認していない。`codex` の引数は既存の試験で固定している。

MCP の `llm_review_*`、`llm_explore_request_*`、`review_if_needed_*` 工具の `backend`
引数は、`codex` と `claude` だけを受ける。`command` は呼出元が指定した引数の雛形で任意の
プロセスを起動するため、操作者が直接指定する CLI に限り、MCP からは拒否して何も起動しない。

実行は `--execute` 又は `execute=true` のときだけ起きる。対象の資料はそのエージェントの
提供元へ送られるため、送ってよいかは呼出元が判断する。査読の結果は不足の候補であり、
採択も却下も代行しない。

## 規則適用の機械検査

工程別規則の判定は、語彙の一致を中心にした決定的な検出器である。同じ内容の別表記で
判定が変わらないか、必須項目を欠いたとき対応する規則が反応するかは、人手の正解なしで
機械的に確かめられる。

```sh
uv run --locked semantic-guard workflow evaluate-fixtures      # 固定の期待値との照合
uv run --locked semantic-guard workflow evaluate-metamorphic   # 不変性と感度
```

`evaluate-metamorphic` は二つを確かめ、どちらかが崩れると終了値 `1` を返す。

- **不変性**: 既存の各フィクスチャを、意味を変えない書き換え（全角英数字、濁点の分離、
  半角カタカナ、全角空白、不可視文字、CRLF、行末空白、Markdown の強調・見出し・箇条書き・
  引用の記号、行の入れ替え、文ごとの改行）で再実行し、判定と規則が動かないことを見る。
  動いた組合せは、理由付きの既知の例外として登録されたものを除き失敗になる。例外の
  登録は、動かなくなると「古い登録」として失敗するため、検出器が改善するたびに縮む。
- **感度**: 良い計画と良い要求から項目を一つずつ削り、その項目を担当する規則が出るか見る。
  何も出ない削除は、他の項目の語が同じ義務を満たしている旨の理由と共に表に残す。
  その削除が指摘を生むようになったら表の更新を求められる。

検出器は監査の入口で、全角・半角、Unicode の合成形、不可視文字、改行を正規化してから語彙を
照合する。指摘が引用する本文は、この正規化後の形になる。ただし、要求関係と方向束縛の監査は
結果に原文の文字位置と形態素解析の対象文字列を持つため、呼出元の原文のまま渡す。この経路は
全角・半角、濁点の分離、半角カタカナの違いにまだ影響される（`verification-target-mismatch`
で確認できる）。登録済みの既知の例外である。

規則カタログ自体も機械的に検査する。固定の期待値の全指摘が、カタログのどれかの規則に紐づくこと。
各規則の重大度（厳格・緩和）が検出器の出力と一致すること。各規則に、出るべき例と、
出てはならない例の両方のフィクスチャがあること。これらは `workflow_tests/test_rule_catalog_consistency.py`
が固定する。

これらはリポジトリ内のフィクスチャに対する較正であり、実務文書での精度、網羅性、
人間による受理を示すものではない。

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
