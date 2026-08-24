# 方向拘束監査の公開切片

- identity: `direction-binding public slice・245dad95-accf-581c-8b0a-ae1c1f557de4`
- contract: `semantic-guard-direction-binding-audit/v1`
- integration target: `canonical current・11c55966-ff12-50b9-b069-7bec6ed37cc4`

## 資料状態

| Field | Value |
| --- | --- |
| `context` | 方向拘束監査を既存要求関係監査から独立した公開切片として選択移植する |
| `current_state` | 1.1.0 公開切片はGitHub mainのmerge commit `a77c3cbdc69295572e90333e2a6e9da690fbbb6d`へ統合済み。閉Schema、CLI、MCP、源試験、選択配布物の隔離検証及び実Sudachi 222組が存在する |
| `schema_version` | `semantic-guard-direction-binding-audit/v1` |
| `repository_id` | `canonical current・11c55966-ff12-50b9-b069-7bec6ed37cc4` |
| `repository_profile` | 新しい global profile は導入しない。この契約を `repository_id` と本表の三公開面だけへ局限する |
| `public_surfaces` | CLI `audit-direction-binding`、MCP `audit_direction_binding_tool`、Schema `direction-binding-audit` |
| `output_shape` | `schema_version` を持つ直接 JSON object。主要欄の要約は後述する |
| `next_action` | 実務母集団、人間受理、公開索引配布及び運用採択を別々に検証する |
| `detail_refs` | [source map](../migration/direction-binding-source-map-2026-08-23.json)、[direction-binding Schema](../schemas/direction-binding-audit.schema.json)、[GitHub統合証拠](audits/direction-binding-integration-2026-08-23.md) |
| `evidence_source` | digest付きsource map、局所検証及びmerge SHAへ束縛したhosted CI観測。実地妥当性又は人間受理の証拠ではない |
| `record_time_policy` | 本資料の `recorded_on=2026-08-23` は ISO 8601 日付で時区なし。実行記録の `recorded_at` は RFC 3339 の時差付き日時 |
| `inference_status` | 源実装、選択した1.1.0配布物、実Sudachi 222組、GitHub統合及びmerge後main CIは成立。実務妥当性、公開配布及び人間受理は未立証 |
| `pending_decision` | 公開契約の最終受理及び人間採択 |
| `exceptions` | 既存要求関係監査、0.1.0 の歴史 archive、vnext 候補及び一般自然言語理解は対象外 |
| `non_goals` | 方向選択、暗黙方向の生成、実務性能主張及び人間受理。詳細は「非目的」節 |

## 目的

この切片は、方向を開いた後続選択表現について、**同一の対象と同一の操作へ方向を限定する表現が直接付着しているか**を監査する。方向拘束が一意なら閉じ、明示拘束が無ければ欠落、相反する拘束があれば競合、解析能力又は原文根拠が足りなければ判定不能として残す。

主規則は `req.precondition.order_direction_unspecified` である。scalar と non-scalar の検出器は同じ主規則を扱うが、発行範囲は交わらず、一つの監査対象から主発行器は高々一つだけになる。

## 公開候補面

1.1.0 源が実装する公開候補面は、既存の要求関係監査から独立した加法的な縦断面である。

| 面 | 名称 | 意味 |
| --- | --- | --- |
| CLI | `audit-direction-binding` | text と任意 context を監査し、閉じた方向拘束監査結果を返す |
| MCP | `audit_direction_binding_tool` | CLI と同じ入力境界・状態・契約版を返す |
| Schema | `direction-binding-audit` | `semantic-guard-direction-binding-audit/v1` の取得・検証契約 |

Schema の `$id` に残る `morie-lene.github.io` URI は版付き識別子であり、
HTTP 取得位置又は現在の owner 名を表す locator ではない。現行 schema は
`semantic-guard schema direction-binding-audit`、導入済み package 資源、又は
repository の `schemas/direction-binding-audit.schema.json` から取得する。

```sh
uv run --locked semantic-guard audit-direction-binding \
  --text '体重が重い順に並べたとき、Cの次に体重が重い人は誰か。' \
  --context '候補集合は現在の表だけを使う。' \
  --morphology sudachi
uv run --locked semantic-guard schema direction-binding-audit
```

この切片を `audit-requirement` の任意 field へ後付けせず、既存の `audit-result/v0` の欄構造、要求関係規則及び監査識別子の生成規則を変更しない。ただし producer package版は1.1.0へ上がるため、版を束縛する既存監査の具体的な識別子値まで不変とはしない。CLI、MCP、Schema の源実装と回帰試験に加え、選択wheel上の公開面同等性と実Sudachi 222組は局所で成立した。実装はPR #3でmainへmergeされ、merge commit `a77c3cbdc69295572e90333e2a6e9da690fbbb6d` のhosted CI四jobも成功した。公開索引上の配布物、hosted artifactと局所wheelのbyte同一性、未登録表現、実務母集団又は人間受理までは、この限定証拠から推論しない。

## 機械出力契約の要約

成功時の payload は入れ子の `ok` wrapper を持たず、次の直接 JSON object を返す。完全な型、必須性、最大寸法及び入れ子構造は [`schemas/direction-binding-audit.schema.json`](../schemas/direction-binding-audit.schema.json) を正本とし、この節は第一読用の射影に限る。

| Field | 型又は列挙 | 役割 |
| --- | --- | --- |
| `schema_version` | const string | `semantic-guard-direction-binding-audit/v1` |
| `audit_id` | string | `audit_id` 自身を除く完全な公開 payload に束縛した識別子 |
| `recorded_at` | RFC 3339 string | 観測時刻。再現時は呼出側が明示できる |
| `subject_ref`, `producer_ref` | typed object | 入力対象と公開切片の別 identity を記録する |
| `source_digest` | SHA-256 object | text と任意 context を結合した原文内容の一致証拠 |
| `input_regions` | typed array | `text` と `context` の役割、開始、排他的終了位置 |
| `rule_id` | const string | `req.precondition.order_direction_unspecified` |
| `execution` | typed object | provider、能力、被覆、診断及び `signal_only` 権限 |
| `decision_frame_summary` | object | scalar `decision-frame-summary/v3` |
| `direction_binding_summary` | object | non-scalar `direction-binding-summary/v1` |
| `primary_rule_evaluation.state` | enum | `satisfied / gap / conflict / indeterminate / not_applicable / invalid` |
| `primary_rule_evaluation.emitter` | enum | `scalar / non_scalar / none` |
| `workflow_disposition.status` | enum | `pass / warn / block`。`reason_codes`、意味境界、受理効果を同じobjectに保持する |
| `limitations` | string array | 適用範囲と未立証事項 |
| `acceptance_owner` | typed object | `human_external_to_criterion_loom`、`acceptance_status=pending`、`accepted=false` を記録する |

輸送契約は、正常時に有効なJSONを`stdout`（標準出力）へ一件出し、診断を`stderr`（標準誤出力）へ分ける。CLIの`exit code`は、正常輸送`0`、利用法又は入力不成立`2`、明示した監査状態閾値`3`を持つ。`shadow-compare`だけは必須旧版観測不成立に`4`を使う。

内部失敗は監査状態ではない。1.1.0は`error_code / message / details / next_action`を持つ公開error objectを定義しておらず、公開JSONを出力しない。CLIは非零で終了し、MCPは工具例外を返す。利用者の次行動は、`stderr`又は工具例外の診断を保存し、入力又は依存を訂正して再実行することである。想定外失敗なら診断、版及び最小再現入力を問題報告へ添える。内部失敗に対して`workflow_disposition.status=block`を生成してはならない。

| failure path | code / exception | message / details | `stdout` | next-action hint |
| --- | --- | --- | --- | --- |
| 利用法・入力不成立 | CLI `2` | `stderr`診断 | 空。正常payloadなし | 入力又はoptionを訂正して再実行する |
| 監査状態閾値 | CLI `3` | payload内の`reason_codes` | 完結した正常payload | 監査状態を人間判断へ渡す |
| 内部失敗 | CLI非零又はMCP工具例外 | `stderr`又は例外診断。構造化details契約なし | 空。正常payloadなし | 診断、版、最小再現入力を保存して問題報告する |

`execution.status` は少なくとも `executed / not_configured / partial / failed / invalid` を分離する。入力の `execution.status` が `not_configured`、`partial` 又は `failed` なら、出力の `primary_rule_evaluation.state` を `indeterminate`、`workflow_disposition.status` を `warn` とする。providerが返した生診断は`execution.diagnostics`へ保持し、`reason_codes`には公開状態へ投影した安定符号を置く。scalar と non-scalar の両方に frame が生じる、provider 能力・`role=document` の全範囲被覆・split mode が契約を満たさない、又は公開 payload の交差拘束が壊れる場合は失敗閉鎖する。

主操作のframeは`input_regions.role=source_text`内に全て収まらなければならない。`context`は原文要約値へ束縛される補助範囲だが、それ自体に置いた別質問や例だけを主発行器へ昇格させない。方向を限定する必須表現を後置contextへ逃がしても、直接付着条件の代用にはならない。

Python検証関数で呼出時の役割境界まで再演する場合は、結合済み`source_text`だけでなく、既知の`text`と`context`を別引数で渡す。結合文字列だけを渡す検証は、要約値、範囲及び自己申告された領域の内部整合を検査できるが、同じ文字列を別の`text/context`境界へ再標識していないという外部来歴までは立証しない。provider識別子、token lemma、品詞及び生診断は宣言されたreceipt材料であり、この検証関数はproviderを再実行せず、それらの外部真正性を認証しない。別引数を渡しても署名、発行者真正性又は信頼時刻になるわけではない。

### CLI と MCP の誤り境界

- CLI は正常な監査 payload を標準出力へ JSON として一件出す。既定終了値0は輸送・契約上の成功であり、`workflow_disposition=pass` の別名ではない。
- `--fail-on warn|block` が指定閾値へ達した場合、CLI は JSON を標準出力へ出した後に終了値3を返す。監査状態を書き換えない。
- 不正 option、入力読取、UTF-8 又は寸法の誤りは標準誤出力へ診断を出し、終了値2で終わり、正常 payload を出さない。
- MCP は正常時に同じ payload object を返す。不正な `morphology` 値は `ValueError` とし、正常監査へ洗浄しない。
- provider の未構成、部分結果及び通常の解析失敗は輸送誤りではなく、`execution` と `primary_rule_evaluation` に記録して返す。
- 内部 Schema 検証失敗又は想定外依存失敗は、有効な公開 JSON を出力せず、CLIは非零で終了し、MCPは工具例外を返す。共通の構造化 error envelope は1.1.0契約に含めず将来課題とする。この共通包絡を設けない境界自体は 1.1.0 方向拘束公開切片の源統合を阻止する条件ではないが、呼出側は非零終了や工具例外を監査上の `block` と読み替えてはならない。

源試験には代表CLI/MCP実行とSchema検査が含まれるが、手書きのpayloadは本資料へ固定しない。選択配布物と実Sudachiの代表実行は局所で成立した。永続的な完了証拠に使う場合は、対象artifact又はSHAへ束縛した別の検証記録に保存する。

## 検査範囲

### Scalar

`decision-frame-summary/v3` は、登録済みの日本語 scalar 後続選択構文だけを扱う。登録分母は14尺度族、49順序軸、56尺度語及び13数値投影である。尺度族が似ていても順序軸が異なれば拘束として結合しない。

高極・低極、尺度名付き昇順・降順、現在の候補表へ直接付く見出し等を、同一判断枠・同一順序軸・直接付着という条件で検査する。裸の昇順・降順、別尺度、別集合、引用、例示、旧版、仮定、否定又は後置された表現は拘束に昇格させない。

### Non-scalar

`direction-binding-summary/v1` は、水平、垂直、奥行、時間、円環及び経路の六方向軸を扱う。左右、上下、前後、過去未来、時計回り反時計回り、起点終点という登録済み二方向だけを、同一方向領域・同一軸・同一基準・直接付着の条件で検査する。

慣習的な既定順、画面座標、行順、世界知識又は候補結果から方向を補わない。直接位置に未知の方向らしい表現がある場合は、欠落と断定せず `indeterminate` に留め、行動可能な主指摘を発行しない。

## 証拠権限

形態素解析の権限上限は `signal_only` である。形態素、品詞、lemma 又は解析器の一致だけから、方向領域、方向拘束、主規則の充足、保留解除を導出してはならない。拘束を成立させるのは、登録表と固定原文文法に適合した、原文範囲付きの直接関係である。

解析器が未構成、部分被覆、失敗、能力不足又は由来不整合なら、その状態を成功へ洗浄しない。`execution.status` と `primary_rule_evaluation.reason_codes` へ原因を記録し、監査全体を無条件の `pass` にしない。

## 数値の境界

数値は `impact_evidence` の補助証拠に限る。閉じた反実仮想 witness を同一単位で再演できる場合だけ付加してよい。数値の有無、値、同値、範囲、概数、欠損又は混合単位は、主規則の発火、frame 状態、適合状態、確信度又は発行器を変更しない。

従って「数値で結果が変わるから方向を決める」のではない。方向を開いた表現と明示拘束との関係が一次判定であり、数値はその判断が持ち得る影響を説明するだけである。

## 非目的

この切片は次を行わない。

- 利用者に代わって採用方向を選ぶ。
- 自由形式の形容詞、任意の尺度又は一般自然言語を理解したと主張する。
- 慣例、常識、候補結果又は数値を入力として、方向拘束 field を生成する。
- 既存の要求関係監査、保証 graph 又はライフサイクル workflow を統合し直す。
- 実務母集団での適合率、再現率、便益又は安全性を立証する。
- 0.1.0 の歴史 archive を現在の truth oracle として再導入する。
- local vnext 候補を暗黙に採択又は正本化する。
- `pass` を人間受理、領域正解、配備許可又は運用資格へ読み替える。

## 人間判断境界

監査結果は、欠落、競合、判定不能、受理済み原文証拠及び却下証拠を、人が判断できる材料へ分ける。最終的な受理、差戻し、保留、延期、棄却及び採用方向の決定は監査系の外部に残る。契約適合や試験通過も、その人間判断を代行しない。

## 系譜と資料境界

この公開切片は `local feature source snapshot・2b62dfa0-6d90-5c31-ae2d-34ec55c94895` からの `derived_from` であり、同じ entity への参照ではない。選択した五つの源泉だけを digest で束縛し、正本へ移植する。完全な対応表は [direction-binding source map](../migration/direction-binding-source-map-2026-08-23.json) に置く。

`local vnext candidate・32646741-8cec-5fe3-b9f3-2971a8a787f0` は `candidate_ref` に留め、1.1.0 方向拘束公開切片の移植元にしない。`frozen legacy archive・3fd59352-b0d9-58f6-8279-9309c8960631` は当該 1.1.0 統合時点の源対象から除外し、移動、改稿又は透過 fallback 化しなかった。2026-08-24 の後続 publication repair は旧版 archive の文書、companion Skill 文面及び archive manifest だけを変更し、runtime code、schema、試験及び fixture は変更していない。

content hash は選択源泉と移植対象の内容一致証拠であり、entity identity ではない。label、役割、配置 path 又は同一内容だけから entity の同一性を推定しない。

## 検証状態

局所で成立したもの:

1. 二つの summary と最上位状態が閉 Schema に適合し、主発行器が高々一つである。
2. 同一 fixture に対する CLI と MCP の契約版、状態、処置及び誤り意味が一致する。
3. 一回の `ProviderRequest` が返した形態素解析結果を、同じ原文・context 範囲付きで scalar と non-scalar の両検出器へ入力する。
4. 既存要求関係監査、敵対的回帰及びCLI説明の回帰を含むunit test 608件が、CPython 3.13で`44.866s`、隔離したCPython 3.11で`46.528s`にて通過した。時間値は性能保証ではない。
5. 1.1.0のwheel/sdistを構築し、選択wheelの配布契約検証20件、24 Schema、四CLI命令、四MCP工具、方向CLI・Schema・`--fail-on`・MCP dispatchを再演した。
6. fresh wheelと`nlp-ja`で、SudachiPy 0.6.11、SudachiDict-core 20260428、split mode Cを記録した。全56尺度語のgap / high-pole bound / low-pole bound 168組と、全18方向基底語のgap / 二方向bound 54組、合計222組を公開監査及び厳格source検証で再演した。

GitHubで成立したもの:

7. [PR #3](https://github.com/morie-lene/criterion-loom/pull/3)は実装commit `c10ba59f8ab16659b50e9cbf13da07c9889ed195`をmerge commit `a77c3cbdc69295572e90333e2a6e9da690fbbb6d`へ統合し、PR CI四jobが成功した。
8. merge後mainの[run 32646816407](https://github.com/morie-lene/criterion-loom/actions/runs/32646816407)はsubject SHA `a77c3cbdc69295572e90333e2a6e9da690fbbb6d`に対して、Python 3.11、Python 3.13、凍結0.1.0煙試験、wheel及び導入済み公開面の四jobを成功させた。詳細は[統合証拠](audits/direction-binding-integration-2026-08-23.md)へ分離した。

なお未成立のもの:

1. 実務母集団での妥当性、運用資格及び外部真正性。
2. 公開索引上の1.1.0配布、release/tag及びhosted artifactと局所wheelのbyte同一性。
3. `acceptance_owner.acceptance_status=pending` を変更する外部人間の受理記録。
