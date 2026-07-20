# 公開比較 2026-06-02

## 目的 / Purpose

この文書は、`semantic-guard` を公開済みの MCP サーバ、エージェント技能、保安走査系の道具と比較し、公開時の位置づけを定めるための文書である。

これは比較と公開計画のための資料であって、`semantic-guard` が保安走査器、release gate、人間の受入判断の代替、または汎用 MCP サーバの上位互換であるとは主張しない。

## 読者と用途 / Audience And Use

この文書は、`semantic-guard` の README、公開説明、release note、repository description、比較説明を書く時に使う。

想定読者は、保守者、査読者、導入を検討する利用者である。読者が判断すべき問いは、`semantic-guard` が MCP サーバなのか、skill なのか、scanner なのか、それとも別種の監査層なのか、という点である。

監査用の実行例:

```sh
uv run --python 3.13 --project . semantic-guard audit-request --kind document --file docs/public-comparison-2026-06-02.ja.md
```

公開時は、まず分類比較を引用する。実用価値を主張する時だけ、dogfood の証拠を併記する。

## 短い位置づけ / Short Positioning

`semantic-guard` は、agentic work のための意味先行監査層である。

道具の実行そのものではなく、道具を使う前後の意味、要求、計画、差分、完了証拠を監査する。

- 作業前: 対象理解と要求監査。
- 編集前: 計画監査。
- 編集後: 差分監査。
- 完了主張前: 完了確認。
- 作業束全体: trace report と人間向け受入判断材料。

`semantic-guard` は、主として文脈提供器でも実行器でもない。目的、範囲、検証、証拠、追跡可能性、人間の最終判断境界を扱う構造化監査面である。

## 比較に実際の軌道は必要か / Does Comparison Need Actual Trajectory?

分類比較には不要である。

公平な公開比較は、公開されている機能、出力契約、公式文書から行える。たとえば filesystem MCP、GitHub MCP、Context7、Snyk MCP、Semgrep MCP、Skills は、それぞれの用途と境界を比較できるだけの公開情報を持っている。

実際の軌道が役に立つのは別の主張、つまり「`semantic-guard` が実地で役に立ったか」を示す時である。

軌道は比較の根拠ではなく、証拠としてだけ使う。

- 生の会話履歴ではなく、dogfood 成果物を使う。
- 内部推論ではなく、実行命令、結果、fixture 数、変更ファイルを使う。
- 証拠の範囲を絞る。「この事例ではこの道具の改善に効いた」と言えるに留め、「広範な正しさを証明した」とは言わない。
- 概念上の比較が明確になった後で、事例研究として軌道を使う。

推奨される公開構成:

- 本文: 静的な分類比較。
- 付録: dogfood 軌道を、成果物と実行結果として要約する。
- 生の会話 transcript は、公開する明確な理由が別途ない限り使わない。

## 比較軸 / Comparison Axes

| 軸 | 意味 |
| --- | --- |
| 主対象 | 文脈、コード、保安、workflow、要求、計画、差分、完了のどれを扱うか。 |
| 出力契約 | prose、tool action、structured JSON、rule id、証拠束のどれを出すか。 |
| 検証面 | tests、fixtures、regression metrics があるか、手順書だけか。 |
| 誤警告の扱い | 非発火規則、not-applicable、弱い一致、助言警告を説明できるか。 |
| 人間判断境界 | 最終受入判断を人間に残すか。 |
| 統合形態 | MCP server、CLI、skill、hosted service、local scanner、documentation provider のどれか。 |
| 失敗様式 | 誤用された時に何を危険または誤導にするか。 |

## 生態系比較 / Ecosystem Comparison

| 分類 | 公開例 | 主用途 | 強い点 | `semantic-guard` との差 |
| --- | --- | --- | --- | --- |
| 参照・utility MCP サーバ | Model Context Protocol の Filesystem、Git、Memory、Sequential Thinking、Fetch、GitHub など | 助手を道具、file、memory、repository、思考補助へ接続する | 広い道具接続、再利用可能な MCP pattern、具体操作 | `semantic-guard` は主として操作面ではない。道具利用の周辺にある意味と完了証拠を監査する。 |
| repository platform MCP | GitHub MCP Server | repository、issue、pull request、Actions、code security など GitHub API への接続 | 直接的な平台統合、toolset、権限範囲 | repository 事実や操作を露出できるが、要求、計画、差分、完了主張が意味を保っているかはそれ自体では見ない。 |
| 文書 grounding MCP | Context7 | 現行かつ version-specific な文書と例を coding prompt へ入れる | 古い API 知識や幻覚文書の危険を減らす | 情報の新しさを補強する。`semantic-guard` は、作業が範囲づけられ、検証可能で、追跡可能で、完了主張が正直かを見る。 |
| 保安走査 MCP | Snyk MCP、Semgrep MCP | code、dependency、container、IaC、SBOM、静的保安走査 | 保安規則と脆弱性文脈に強い | `semantic-guard` は脆弱性走査器として競うべきではない。保安は広い要求・計画・完了監査の一項目に留まる。 |
| agent skills | Claude Skills などの `SKILL.md` workflow package | 指示、script、reference、反復手順をまとめる | portable な workflow 専門化、progressive disclosure、実行補助 | `semantic-implementation` は skill に近いが、`semantic-guard` は CLI/MCP 実行、JSON 出力、rule id、fixture、trace report、finish check を追加する。 |
| 思考補助 | Sequential Thinking MCP など | 思考手順の構造化や外部化 | 複雑な検討や思考修正に有用 | 思考構造は、受入基準、非目標、差分危険、fixture 較正、最終証拠とは別物である。 |
| MCP 保安・供給網走査 | Snyk MCP 関連、MCP security scanner、Semgrep 関連 | MCP 設定、脆弱 code、tool poisoning などの危険検出 | agentic security posture と supply-chain risk に強い | `semantic-guard` は保安を一分類として扱えるが、中心価値は意味 drift、範囲 drift、完了証拠 drift の検出である。 |

## Skills との位置づけ / Positioning Against Skills

Skills は、反復可能な workflow を定義する点で近い。

通常の公開 skill は、次の問いに答える。

- いつこの workflow を使うか。
- どの手順に従うか。
- どの script、reference、asset を読むか。

`semantic-guard` が追加で答える問いは、次である。

- その workflow を、外部から data として監査できるか。

重要な差は、実行可能な監査証拠である。

| 機能 | 通常の skill | `semantic-guard` |
| --- | --- | --- |
| 起動指示 | あり | `semantic-implementation` skill 経由 |
| 反復 workflow | あり | あり |
| CLI command | 任意 | あり |
| MCP tool | 任意 | あり |
| structured JSON result | 本質的ではない | あり |
| rule id と repair hint | 本質的ではない | あり |
| fixture regression | 本質的ではない | あり |
| rule catalog coverage | 本質的ではない | あり |
| 完了証拠 check | 多くは手続き的 | 実行可能な phase |
| 最終人間判断境界 | 作者次第 | 明示的に保持 |

このため、`semantic-guard` は単なる skill というより、skill-backed audit engine と呼ぶ方が、現状の機能束を説明しやすい。

## MCP サーバとの位置づけ / Positioning Against MCP Servers

多くの MCP サーバは能力 adapter である。助手が道具や資料源へ到達できるようにする。

`semantic-guard` は governance adapter に近い。

- GitHub、file、documentation、security scanner を利用可能にする道具ではない。
- それらの道具利用が、目的、範囲、検証、証拠、追跡可能性と結びついているかを見る。

きれいな主張はこうである。

> 既存の MCP サーバは、agent が触れられるものを増やす。`semantic-guard` は、agent の作業が意味を保ち、境界づけられ、証拠を持ち、査読可能であるかを監査する。

これで十分に強い。保安走査器、repository tool、documentation grounding、人間査読を置き換えるとは言わない。

## 差別化点 / Differentiators

`semantic-guard` は、次の束で差別化される。

- 五相の監査経路: target、request、plan、diff、finish。
- 文書専用監査を含む input-kind routing。
- 要求工学・計画工学寄りの確認。
- request、plan、diff、finish、evidence をまたぐ trace report。
- `emission_status` 付きの非発火規則診断。
- finding、non-emitted rules、field-match evidence をまとめる diagnostic envelope。
- base score と profiled score を分ける severity profile。
- rule catalog coverage 付き fixture evaluation。
- LLM reviewer を中途材料に留める設計。
- 決定論出力の外側に置かれた人間の最終受入。

上の公開 MCP 分類の中に、この束そのものを主対象にしているものは見えない。個別の要素は skills、保安走査、思考補助、文書 MCP と重なるが、統合点が違う。

## 弱点と正直な境界 / Weaknesses And Honest Boundaries

隠してはいけない境界は次である。

- まだ heuristic である。
- 形式的な要求工学 engine ではない。
- 保安走査器ではない。
- fixture metrics は局所較正であって、任意文書に対する統計的 precision / recall ではない。
- rule catalog は小さい。
- profile ごとの escalation pressure はまだ deferred である。
- 領域固有語彙では過警告も過少警告も起こり得る。
- 人間の受入判断はなお必要である。

これらの境界は飾りではない。`semantic-guard` の信頼模型そのものに含まれる。

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

- 現在の test 数と pass 結果。
- `evaluate-fixtures` の件数と pass rate。
- `details.non_emitted_rules` の小例。
- `rule_catalog_coverage.unhit_rule_ids` の小例。
- `trace-report.summary.audit_status` と `trace_status` の差を示す小例。
- README 監査や衝突修正 pass の dogfood note link または要約。

推奨文:

> 比較は分類に基づく。dogfood 証拠は、その分類が机上論だけではないことを示す。

## 出典 snapshot / Source Snapshot

確認日: 2026-06-02。

- Model Context Protocol reference servers は Filesystem、Git、Memory、Sequential Thinking、Fetch、GitHub などを挙げている: https://github.com/modelcontextprotocol/servers
- GitHub MCP Server は GitHub API に基づく repository access、PAT、toolset configuration を記述している: https://github.com/github/github-mcp-server
- Context7 は、現行かつ version-specific な documentation と code example を assistant prompt に入れると説明している: https://context7.com/docs
- Snyk は、Snyk CLI 経由の local MCP server と profile-based security-scanning tool set を記述している: https://docs.snyk.io/integrations/snyk-studio-agentic-integrations/getting-started-with-snyk-studio
- Semgrep MCP repository は、security vulnerability scanning を行う MCP server と説明している: https://github.com/semgrep/mcp
- Claude Skills documentation は、skills を `SKILL.md`、instructions、scripts、resources を持つ directory として説明している: https://claude.com/docs/skills/overview と https://claude.com/docs/skills/how-to
