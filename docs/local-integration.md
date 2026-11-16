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

workflow の監査コマンドは、`status` が `warn` や `block` でも、結果の JSON を出力できれば
既定で終了値 `0` を返す。スクリプトや CI で監査状態を終了値へ対応付ける場合は、
`--fail-on warn` 又は `--fail-on block` を明示する。閾値に達すると、JSON を完全な形で
標準出力へ出した後に、基幹と同じ終了値 `3` を返す。

```sh
uv run --locked semantic-guard workflow finish-check \
  --file completion-evidence.txt --fail-on block
```

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
| `claude` | `claude -p --output-format json --json-schema`（道具なし、会話を保存しない、設定源を空にし、MCP 設定を読まず、スラッシュコマンドとスキルを無効にする） | 封筒の `structured_output`。無ければ `result` の JSON | 可 |
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

`--text` 又は `--file` の入力は JSON オブジェクトで、査読対象の `candidate`（空でない文字列。必須）の
ほかに、`request`、`context`、`constraints`、`non_goals`、`unknowns`、`deterministic_audit`（決定的な
監査の結果）、`review_context`、`phase`、`rule_ids` を受ける。

`--model` を省くと各エージェント既定のモデルを使う（`codex` は `gpt-5.4-mini`、
`claude` は `sonnet`）。`gpt-5.4-mini` は `codex` の既定値と区別できないため、`claude` や `command` へ
明示して渡しても、そのエージェントの既定値に置き換わる。別のモデルを使うときは別の値を指定する。
`command` で既定のモデルが無いとき、`{model}` を含む引数は省かれる。`claude` の `--json-schema` は `$schema` と `$id` を解決できないため、
インライン渡しの前にこの二つを除く。`--agent-binary` で実行ファイルの場所を替えられる。

`claude` は、封筒の `subtype` が `success`、`is_error` が真偽値の `false`、`permission_denials` が
空又は無いときだけ成功として読む。それ以外は、`result` に妥当な JSON があっても `valid_review` にしない。
`claude` の隔離は、上記の引数が実際に止めるものに限る。作業ディレクトリ配下の `CLAUDE.md` の
自動探索と自動メモリを止めるかは実機で確認していないため、機密を含む作業ディレクトリでは
`--working-directory` で空のディレクトリを指す。

確認の範囲: 移植元の作成者は、Claude Code 2.1.302 とモデル `haiku` で
`valid_review` を得たと報告している（2026-10-17）。統合先のMacでは2.1.284へ合成入力を
一度渡したが、未ログインで終了した。統合先で実際の査読成功を再現した証拠はまだない。
他の版・モデルでの動作や査読内容の質も未確認で、`codex` の引数は既存の試験で固定している。

MCP の `llm_review_*`、`llm_explore_request_*`、`review_if_needed_*` 工具の `backend`
引数は、`codex` と `claude` だけを受ける。`command` は呼出元が指定した引数の雛形で任意の
プロセスを起動するため、操作者が直接指定する CLI に限り、MCP からは拒否して何も起動しない。

CLI と同期の MCP 工具は、`--execute` 又は `execute=true` のときだけ実行する。非同期の
`*_start_tool`（`llm_review_start_tool`、`llm_explore_request_start_tool`、
`review_if_needed_start_tool`）には `execute` 引数が無く、呼び出した時点で査読者を起動する。
対象の資料はそのエージェントの提供元へ送られるため、送ってよいかは呼出元が判断する。
特に `*_start_tool` の呼出しは、その同意を含む。査読の結果は不足の候補であり、
採択も却下も代行しない。

査読の実行前に、次を検査する。通らなければ何も起動せず `input_error` を返す（CLI は終了値 2。
`llm-explore-request` だけは構造化 JSON と終了値 1）。`review-if-needed` では、査読が必要かの
判定より先に検査するため、実行できない呼出しが「不要」に見えることはない。

- `timeout_seconds`（`--timeout-seconds`）は、0 より大きく 3600 以下の有限の数。
- `model` は NUL と制御文字を含まず、`-` で始まらない。`--agent-binary` は `command` では
  使えない（実行ファイルは雛形の先頭の引数）。
- `working_directory`（`--working-directory`）は存在するディレクトリ。相対パスは入口で実体の
  絶対パスへ解決し、codex の `--cd` と過程の `cwd` に二重に効かせない。CLI は操作者が指定する
  ため存在だけを確かめる。MCP からは、サーバーの現在のディレクトリと環境変数
  `SEMANTIC_GUARD_WORKDIR_ROOTS`（OS のパス区切りで複数）の配下だけを指定でき、
  シンボリックリンクで外へ出る指定は実体で判定して拒否する。`codex` は `read-only` でも指定した
  ディレクトリ配下を読めるため、査読対象の文書に紛れた指示がそこのファイルを読ませる経路になりうる。
  機密を含むディレクトリを、サーバーの現在のディレクトリや `SEMANTIC_GUARD_WORKDIR_ROOTS` に
  入れない。

`--agent-command` は全OSでPOSIXの引用規則により引数へ分割し、シェル自体は起動しない。
二重引用符の中で逆斜線が効くのは `\\` と `\"` の前だけなので、`"C:\tools\agent.exe"` の逆斜線は
保たれる。UNC パス `\\server\share\agent.exe` は、二重引用符の中でも先頭の `\\` が `\` 一つに縮む。
UNC パスは単一引用符で囲むか、逆斜線を二重にするか、スラッシュで書く。置換は雛形の
プレースホルダを1回だけ走査し、置換した値の中の `{model}` などは再置換しない。値が空の
プレースホルダだけの引数は、直前の単独のオプションと共に省く。Python API へ引数配列を渡す
場合は、この文字列分割を経由しない。

制限時間を超えると、査読エージェントを独立したセッション（Windows では新しい過程群）で
起動したうえで、その過程群全体を終了する（POSIX は `SIGKILL`、Windows は `taskkill /T`）。
直接の子が終了済みで、子孫だけが出力の管を握っている場合は、制限時間の満了を待たずに子孫を
止め、読めた出力を結果とする。ただし、子孫が自分で新しいセッションや過程群を作ると、この停止は
届かない。Windows の動作は試験環境で実機検証していない。標準出力と標準エラーは、それぞれ
4 MiB で打ち切り、結果にその旨を残す。

子過程には、呼出元過程の環境変数をすべて渡す。API キーなどを含め、絞り込みはしない。
機密を渡したくない場合は、環境変数を絞った状態でサーバー又は CLI を起動する。

非同期の `*_start_tool` が同時に実行する査読者は4つまでで、保持する結果は64件までである。
超える開始は `rejected` として理由付きで断る。読み取り済みの完了結果は、古いものから押し出す
が、未読の結果は黙って捨てない。ジョブの状態に返す `metadata` には、`include_prompt` を付けない限り、査読対象の本文を含めない。
背景処理の取消APIや常駐MCP設定の自動変更は、この追加には含まれない。

## 規則適用の機械検査

工程別規則の判定は、語彙の一致を中心にした決定的な検出器である。同じ内容の別表記で
判定が変わらないか、必須項目を欠いたとき対応する規則が反応するかは、人手の正解なしで
機械的に確かめられる。

```sh
uv run --locked semantic-guard workflow evaluate-fixtures      # 固定の期待値との照合
uv run --locked semantic-guard workflow evaluate-metamorphic   # 不変性と感度
```

`evaluate-metamorphic` は二つを確かめ、どちらかが崩れると終了値 `1` を返す。

- **不変性**: 既存の各フィクスチャを、意味を変えない書き換えで再実行し、判定と規則が
  動かないことを見る。書き換えは37種で、表記（全角英数字、濁点の分離、半角カタカナ、全角空白、
  語中を含む不可視文字）、改行（CRLF、CR、U+2028、U+2029、U+0085）、体裁（行末空白、Markdown の
  強調・見出し・箇条書き・番号・引用の記号、行の入れ替え、文ごとの改行）、ラベルの同義語
  （`対象外`→`範囲外`、`目的`→`ねらい`、`受入基準`→`完了条件` など18種）に分かれる。書き換えが原文を変えなかった組合せは「恒等」として
  別に数え、安定の根拠にしない。現在は91件のフィクスチャで1,515件の実質的な比較（恒等は1,236件）が
  全て安定している。フィクスチャの `context`、`intent`、`request`、`evidence` にも、文書の構造を
  変えない書き換えを同時に適用する。動いた組合せは、理由付きの既知の例外として登録されたものを除き失敗になる。
  既知の例外は現在ない。例外の登録は、動かなくなると「古い登録」として失敗するため、
  検出器が改善するたびに縮む。
- **感度**: 良い計画と良い要求から項目を一つずつ削り、その項目を担当する規則が出るか見る。
  何も出ない削除は、他の項目の語が同じ義務を満たしている旨の理由と共に表に残す。
  その削除が指摘を生むようになったら表の更新を求められる。この検査が反応を確かめる規則は、
  カタログ73件のうち30件である。残りの規則は、削除による反応をこの検査では確かめていない。
  複数の欄が同じ規則 ID を共有するときは、その欄に当たる欠落名も照合する。

検出器は監査の入口で、全角・半角、Unicode の合成形、不可視文字、改行を正規化してから語彙を
照合する。指摘が引用する本文は、この正規化後の形になる。要求関係と方向束縛の監査も、
形態素解析の提供元が無いときは正規化した文で判定し、公開する文字位置と抜粋は原文の座標へ
戻す。提供元を使う場合は、解析結果が原文そのものに結び付くため、結び付いた要約は原文のまま
作る。判定は、正規化した文での提供元なしの実行から得る。ただし判断枠と方向束縛の判定
は、提供元の解析結果（原文そのものに結び付く）から得るため、BOM や語中の不可視文字、全角・半角の違い
でも方向の束縛が変わりうる（実際の Sudachi で、文頭の BOM により「方向が未指定」の指摘が現れることを
確認した）。これは既知の限界で、記録済みの解析を持つフィクスチャは `invariance.skipped` に理由付きで
残し、不変性の検査から外している。

工程監査の論理導出も正規化した文字列で判定するが、公開する根拠範囲とその抜粋は、文字の
合成・展開・除去を対応付けて原文へ戻す。差分のファイル名も原文を保ち、全角文字や不可視文字を
別の識別子へ置き換えない。

同義語の書き換えは、別の欄の語と衝突する語（`完了条件` の `条件` が前提条件に、`責任者` の
`責任` が危険移転の証拠に数えられる、など）を見つけるために使い、見つかった衝突は語彙側で直した。

`audit-plan` と `audit-diff` は、入力種別がそれぞれ `plan`、`diff-summary` 以外のとき、
別の監査の規則を当てずに使用法の誤りとして拒否する（終了値 2。要求と文書は `audit-request`）。
順序を複数回書いたときは最後の記述が有効で、`順序: Aの後にB` の後に `順序: 後で決める` があれば
順序は未決になる。矛盾する具体的な順序同士（`AはBの前` と `BはAの前`）は比較しない。
`audit-conventions` の参照解決は、行番号 `line` が文脈と本文を連結した正規化後の文の行であることを、
`source`（`context` 又は `text`）と、その中の行番号 `source_line` で示す。

行回転と文改行は、符号囲みや順序付き手順などを壊さない範囲へ適用を絞り、除外理由を
`invariance.skipped` に残す。既知の変動も状態と増減する規則の組を照合し、同じ資料での
別の悪化を既知例外として通さない。

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
2026-10-01 の結合候補に対する試験結果、配布物のハッシュ値、MCP実接続の証拠と未検証項目は
[`verification.json`](../integration/verification.json) にまとめてある。これはその時点の観測で、
その後に加えた変更（規則の機械検査、取込み、実行層の検査など）の結果を含まない。現在の木に
ついては、CI と同じ `python -m unittest discover` で `tests`、`workflow_tests`、
`candidate_tests` を再実行して得る。

この開発版が結合するのは呼出経路と配布である。各監査結果を横断して一つの判定へまとめる
意味変換、重複実装の共通化、実地妥当性、未採用規則の採択、稼働MCPの切替は
別の課題として残る。今回の統合候補には、配布物とソースの結び付け、および許諾・重複・
評価対象を検査する実地標本の受入口を含む。受入口の方針は人間の判断待ちで、標本収集や
運用開始はしていない。引渡し投影の追加統合は範囲外である。過去の試験記録を今回の
統合候補の試験証拠として流用しない。
