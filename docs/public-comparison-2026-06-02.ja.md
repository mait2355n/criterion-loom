# 公開比較2026-06-02

## 目的 / Purpose

この文書は、`semantic-guard`を公開済みのMCPサーバ、エージェント技能、保安走査系の道具と比較し、公開時の位置づけを定めるための文書である。

これは比較と公開計画のための資料であって、`semantic-guard`が保安走査器、release gate、人間の受入判断の代替、または汎用MCPサーバの上位互換であるとは主張しない。

## 読者と用途 / Audience And Use

この文書は、`semantic-guard`のREADME、公開説明、release note、repository description、比較説明を書く時に使う。

想定読者は、保守者、査読者、導入を検討する利用者である。読者が判断すべき問いは、`semantic-guard`がMCPサーバなのか、skillなのか、scannerなのか、それとも別種の監査層なのか、という点である。

監査用の実行例:

```sh
uv run --python 3.13 --project . semantic-guard audit-request --kind document --file docs/public-comparison-2026-06-02.ja.md
```

公開時は、まず分類比較を引用する。実用価値を主張する時だけ、dogfoodの証拠を併記する。

## 短い位置づけ / Short Positioning

`semantic-guard`は、agentic workのための意味先行監査層である。

道具の実行そのものではなく、道具を使う前後の意味、要求、計画、差分、完了証拠を監査する。

- 作業前: 対象理解と要求監査。
- 編集前: 計画監査。
- 編集後: 差分監査。
- 完了主張前: 完了確認。
- 要求、計画、差分、完了証拠を結ぶ作業束: trace reportと人間向け受入判断材料。

`semantic-guard`は、主として文脈提供器でも実行器でもない。目的、範囲、検証、証拠、追跡可能性、人間の最終判断境界を扱う構造化監査面である。

## 比較に実際の軌道は必要か / Does Comparison Need Actual Trajectory?

分類比較には不要である。

公平な公開比較は、公開されている機能、出力契約、公式文書から行える。filesystem MCP、GitHub MCP、Context7、Snyk MCP、Semgrep MCP、Skillsは、各公開実装の用途と境界を比較できるだけの公開情報を持っている。

実際の軌道が役に立つのは別の主張、つまり「`semantic-guard`が実地で役に立ったか」を示す時である。

軌道は比較の根拠ではなく、証拠としてだけ使う。

- 生の会話履歴ではなく、dogfood成果物を使う。
- 内部推論ではなく、実行命令、結果、fixture数、変更ファイルを使う。
- 証拠の範囲を絞る。「この事例ではこの道具の改善に効いた」と言えるに留め、「広範な正しさを証明した」とは言わない。
- 概念上の比較が明確になった後で、事例研究として軌道を使う。

推奨される公開構成:

- 本文: 静的な分類比較。
- 付録: dogfood軌道を、成果物と実行結果として要約する。
- 生の会話transcriptは、公開する明確な理由が別途ない限り使わない。

## 比較軸 / Comparison Axes

| 軸 | 意味 |
| --- | --- |
| 主対象 | 文脈、コード、保安、workflow、要求、計画、差分、完了のどれを扱うか。 |
| 出力契約 | prose、tool action、structured JSON、rule id、証拠束のどれを出すか。 |
| 検証面 | tests、fixtures、regression metricsがあるか、手順書だけか。 |
| 誤警告の扱い | 非発火規則、not-applicable、弱い一致、助言警告を説明できるか。 |
| 人間判断境界 | 最終受入判断を人間に残すか。 |
| 統合形態 | MCP server、CLI、skill、hosted service、local scanner、documentation providerのどれか。 |
| 失敗様式 | 誤用された時に何を危険または誤導にするか。 |

## 生態系比較 / Ecosystem Comparison

| 分類 | 公開例 | 主用途 | 強い点 | `semantic-guard`との差 |
| --- | --- | --- | --- | --- |
| 参照・utility MCPサーバ | Model Context ProtocolのFilesystem、Git、Memory、Sequential Thinking、Fetch、GitHubなど | 助手を道具、file、memory、repository、思考補助へ接続する | 広い道具接続、再利用可能なMCP pattern、具体操作 | `semantic-guard`は主として操作面ではない。道具利用の周辺にある意味と完了証拠を監査する。 |
| repository platform MCP | GitHub MCP Server | repository、issue、pull request、Actions、code securityなどGitHub APIへの接続 | 直接的な平台統合、toolset、権限範囲 | repository事実や操作を露出できるが、要求、計画、差分、完了主張が意味を保っているかはそれ自体では見ない。 |
| 文書grounding MCP | Context7 | 現行かつversion-specificな文書と例をcoding promptへ入れる | 古いAPI知識や幻覚文書の危険を減らす | 情報の新しさを補強する。`semantic-guard`は、作業が範囲づけられ、検証可能で、追跡可能で、完了主張が正直かを見る。 |
| 保安走査MCP | Snyk MCP、Semgrep MCP | code、dependency、container、IaC、SBOM、静的保安走査 | 保安規則と脆弱性文脈に強い | `semantic-guard`は脆弱性走査器として競うべきではない。保安は広い要求・計画・完了監査の一項目に留まる。 |
| agent skills | Claude Skillsなどの`SKILL.md` workflow package | 指示、script、reference、反復手順をまとめる | portableなworkflow専門化、progressive disclosure、実行補助 | `semantic-implementation`はskillに近いが、`semantic-guard`はCLI/MCP実行、JSON出力、rule id、fixture、trace report、finish checkを追加する。 |
| 思考補助 | Sequential Thinking MCPなど | 思考手順の構造化や外部化 | 複雑な検討や思考修正に有用 | 思考構造は、受入基準、非目標、差分危険、fixture較正、最終証拠とは別物である。 |
| MCP保安・供給網走査 | Snyk MCP関連、MCP security scanner、Semgrep関連 | MCP設定、脆弱code、tool poisoningなどの危険検出 | agentic security postureとsupply-chain riskに強い | `semantic-guard`は保安を一分類として扱えるが、中心価値は意味drift、範囲drift、完了証拠driftの検出である。 |

## Skillsとの位置づけ / Positioning Against Skills

Skillsは、反復可能なworkflowを定義する点で近い。

通常の公開skillは、次の問いに答える。

- いつこのworkflowを使うか。
- どの手順に従うか。
- どのscript、reference、assetを読むか。

`semantic-guard`が追加で答える問いは、次である。

- そのworkflowを、外部からdataとして監査できるか。

重要な差は、実行可能な監査証拠である。

| 機能 | 通常のskill | `semantic-guard` |
| --- | --- | --- |
| 起動指示 | あり | `semantic-implementation` skill経由 |
| 反復workflow | あり | あり |
| CLI command | 任意 | あり |
| MCP tool | 任意 | あり |
| structured JSON result | 本質的ではない | あり |
| rule idとrepair hint | 本質的ではない | あり |
| fixture regression | 本質的ではない | あり |
| rule catalog coverage | 本質的ではない | あり |
| 完了証拠check | 多くは手続き的 | 実行可能なphase |
| 最終人間判断境界 | 作者次第 | 明示的に保持 |

このため、`semantic-guard`は単なるskillというより、skill-backed audit engineと呼ぶ方が、現状の機能束を説明しやすい。

## MCPサーバとの位置づけ / Positioning Against MCP Servers

多くのMCPサーバは能力adapterである。助手が道具や資料源へ到達できるようにする。

`semantic-guard`はgovernance adapterに近い。

- GitHub、file、documentation、security scannerを利用可能にする道具ではない。
- それらの道具利用が、目的、範囲、検証、証拠、追跡可能性と結びついているかを見る。

きれいな主張はこうである。

> 既存のMCPサーバは、agentが触れられるものを増やす。`semantic-guard`は、agentの作業が意味を保ち、境界づけられ、証拠を持ち、査読可能であるかを監査する。

これで十分に強い。保安走査器、repository tool、documentation grounding、人間査読を置き換えるとは言わない。

## 差別化点 / Differentiators

`semantic-guard`は、次の束で差別化される。

- 五相の監査経路: target、request、plan、diff、finish。
- 文書専用監査を含むinput-kind routing。
- 要求工学・計画工学寄りの確認。
- request、plan、diff、finish、evidenceをまたぐtrace report。
- `emission_status`付きの非発火規則診断。
- finding、non-emitted rules、field-match evidenceをまとめるdiagnostic envelope。
- base scoreとprofiled scoreを分けるseverity profile。
- rule catalog coverage付きfixture evaluation。
- LLM reviewerを中途材料に留める設計。
- 決定論出力の外側に置かれた人間の最終受入。

上の公開MCP分類の中に、要求、計画、差分、完了証拠を結ぶ監査束を主対象にしているものは見えない。個別の要素はskills、保安走査、思考補助、文書MCPと重なるが、統合点が違う。

## 弱点と正直な境界 / Weaknesses And Honest Boundaries

隠してはいけない境界は次である。

- まだheuristicである。
- 形式的な要求工学engineではない。
- 保安走査器ではない。
- fixture metricsは局所較正であって、任意文書に対する統計的precision / recallではない。
- rule catalogは小さい。
- profileごとのescalation pressureはまだdeferredである。
- 領域固有語彙では過警告も過少警告も起こり得る。
- 人間の受入判断はなお必要である。

人間判断、非保安走査、非release gate、局所校正という四つの境界は飾りではない。`semantic-guard`の信頼模型の中核に含まれる。

## 公開時の呼び方 / Publication Recommendation

公開時の呼び方:

- `meaning-first audit workbench`
- `agentic workflow audit layer`
- `requirements/planning/completion guard for Codex-style work`
- `skill-backed CLI/MCP audit engine`

避ける呼び方:

- `AI safety engine`
- `requirements engineering replacement`
- `release gate`
- `security scanner`
- `MCP competitor`
- `autonomous acceptance system`

## 公開すべき証拠 / Evidence To Publish

生の軌道ではなく、小さな証拠付録を使う。

推奨される証拠:

- 現在のtest数とpass結果。
- `evaluate-fixtures`の件数とpass rate。
- `details.non_emitted_rules`の小例。
- `rule_catalog_coverage.unhit_rule_ids`の小例。
- `trace-report.summary.audit_status`と`trace_status`の差を示す小例。
- README監査や衝突修正passのdogfood note linkまたは要約。

推奨文:

> 比較は分類に基づく。dogfood証拠は、その分類が机上論だけではないことを示す。

## 出典snapshot / Source Snapshot

確認日: 2026-06-02。

- Model Context Protocol reference serversはFilesystem、Git、Memory、Sequential Thinking、Fetch、GitHubなどを挙げている: https://github.com/modelcontextprotocol/servers
- GitHub MCP ServerはGitHub APIに基づくrepository access、PAT、toolset configurationを記述している: https://github.com/github/github-mcp-server
- Context7は、現行かつversion-specificなdocumentationとcode exampleをassistant promptに入れると説明している: https://context7.com/docs
- Snykは、Snyk CLI経由のlocal MCP serverとprofile-based security-scanning tool setを記述している: https://docs.snyk.io/integrations/snyk-studio-agentic-integrations/getting-started-with-snyk-studio
- Semgrep MCP repositoryは、security vulnerability scanningを行うMCP serverと説明している: https://github.com/semgrep/mcp
- Claude Skills documentationは、skillsを`SKILL.md`、instructions、scripts、resourcesを持つdirectoryとして説明している: https://claude.com/docs/skills/overviewとhttps://claude.com/docs/skills/how-to
