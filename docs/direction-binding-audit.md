# 方向拘束監査の公開限定機能

## 目的

この限定機能は、「A の次」のように、方向を指定しなければ結果が一意に決まらない
後続選択表現について、**同一の対象と同一の操作へ方向を限定する表現が直接結び付いて
いるか**を監査する。方向拘束が一意なら確定し、
明示拘束が無ければ欠落、相反する拘束があれば競合、解析能力又は原文根拠が足りなければ
判定不能として残す。

主規則は `req.precondition.order_direction_unspecified` である。尺度系の `scalar` と
非尺度系の `non-scalar` の検出器は同じ主規則を扱うが、主判定を出せる範囲は重ならず、
一つの監査対象から主判定を出す検出器は最大一つだけになる。

## 最小対照例

[README の最短実例](../README.ja.md#最短実例)にある `--text` を替えると、同じ
「横一列で A の次を問う」表現について、方向の明示あり・なしを対照できる。
ここで `binding` は
`direction_binding_summary.frames[0].direction_binding` を指す。

| 入力 | `binding.status / direction` | `primary_rule_evaluation.state` | `workflow_disposition.status` | `acceptance_owner.acceptance_status` |
| --- | --- | --- | --- | --- |
| `横一列を左から右へ辿るとき、Aの次の項目はどれですか？` | `bound`; `direction=left_to_right` | `satisfied` | `pass` | `pending` |
| `横一列で、Aの次の項目はどれですか？` | `missing` | `gap` | `warn` | `pending` |

二例とも「A の次の項目そのもの」は算出しない。監査対象は、方向が未指定の表現へ
必要な方向拘束が直接付着しているかである。候補結果や慣例から方向を補わず、
`pass` から人間受理も推定しない。この対照は登録済み横方向表現一組の契約再現で
あり、未登録表現や一般自然言語に対する精度証拠ではない。

- 同一性: `direction-binding public slice・245dad95-accf-581c-8b0a-ae1c1f557de4`
- 契約: `semantic-guard-direction-binding-audit/v1`
- 統合先: `canonical current・11c55966-ff12-50b9-b069-7bec6ed37cc4`

## 資料状態

| 項目 | 値 |
| --- | --- |
| `context` | 方向拘束監査を既存要求関係監査から独立した公開限定機能として選択移植する |
| `current_state` | 1.1.0 公開限定機能は GitHub の `main` にあるマージコミット `a77c3cbdc69295572e90333e2a6e9da690fbbb6d` へ統合済み。値や項目を限定したスキーマ、CLI、MCP、ソースコード試験、選択配布物の隔離検証及び実 Sudachi 222組が存在する |
| `schema_version` | `semantic-guard-direction-binding-audit/v1` |
| `repository_id` | `canonical current・11c55966-ff12-50b9-b069-7bec6ed37cc4` |
| `repository_profile` | 新しい全体プロファイルは導入しない。この契約を `repository_id` と本表の三公開面だけへ限定する |
| `public_surfaces` | CLI `audit-direction-binding`、MCP `audit_direction_binding_tool`、スキーマ `direction-binding-audit` |
| `output_shape` | `schema_version` を持つ直接 JSON オブジェクト。主要項目の要約は後述する |
| `next_action` | 実務母集団、人間受理、公開索引配布及び運用採択を別々に検証する |
| `detail_refs` | [ソース対応表](../migration/direction-binding-source-map-2026-08-23.json)、[方向拘束スキーマ](../schemas/direction-binding-audit.schema.json)、[GitHub統合証拠](audits/direction-binding-integration-2026-08-23.md) |
| `evidence_source` | ハッシュ値付きソース対応表、ローカル検証及びマージ SHA へ拘束した GitHub 上の CI 観測。実地妥当性又は人間受理の証拠ではない |
| `record_time_policy` | 本資料の `recorded_on=2026-08-23` は ISO 8601 日付で時区なし。実行記録の `recorded_at` は RFC 3339 の時差付き日時 |
| `inference_status` | ソースコード実装、選択した1.1.0配布物、実 Sudachi 222組、GitHub 統合及びマージ後の `main` CI は成立。実務妥当性、公開配布及び人間受理は未立証 |
| `pending_decision` | 公開契約の最終受理及び人間採択 |
| `exceptions` | 既存要求関係監査、0.1.0 の歴史アーカイブ、vnext 候補及び一般自然言語理解は対象外 |
| `non_goals` | 方向選択、暗黙方向の生成、実務性能主張及び人間受理。詳細は「非目的」節 |

## 公開インターフェース

1.1.0 のソースコードでは、既存の要求関係監査を変更せず、方向拘束監査を独立した
機能として追加している。

| 面 | 名称 | 意味 |
| --- | --- | --- |
| CLI | `audit-direction-binding` | `text` と任意の `context` を監査し、項目を限定した方向拘束監査結果を返す |
| MCP | `audit_direction_binding_tool` | CLI と同じ入力境界・状態・契約版を返す |
| スキーマ | `direction-binding-audit` | `semantic-guard-direction-binding-audit/v1` の取得・検証契約 |

スキーマの `$id` に残る `morie-lene.github.io` URI は版付き識別子であり、
HTTP 取得位置又は現在の所有者名を表す取得先ではない。現行スキーマは
`semantic-guard schema direction-binding-audit`、導入済みパッケージ資源、又は
リポジトリの `schemas/direction-binding-audit.schema.json` から取得する。

[実行例、入力上限及び `context` の扱い](operations.md#方向拘束入力契約)は運用手引へ一本化している。

この限定機能を `audit-requirement` の任意項目へ後付けせず、既存の `audit-result/v0` の
項目構造、要求関係規則及び監査識別子の生成規則を変更しない。ただし生成元パッケージ版は
1.1.0へ上がるため、版と結び付く既存監査の具体的な識別子値まで不変とはしない。
CLI、MCP、スキーマのソースコード実装と回帰試験に加え、選択した `wheel` 上の公開面同等性と
実 Sudachi 222組はローカルで成立した。実装は PR #3 で `main` へマージされ、マージコミット
`a77c3cbdc69295572e90333e2a6e9da690fbbb6d` の GitHub 上の CI 四ジョブも成功した。
公開索引上の配布物、GitHub 上の成果物とローカル `wheel` のバイト同一性、未登録表現、
実務母集団又は人間受理までは、この限定証拠から推論しない。

## 機械出力契約の要約

成功時のデータは入れ子の `ok` ラッパーを持たず、次の JSON オブジェクトを直接返す。
完全な型、必須項目、最大サイズ及び入れ子構造は
[`schemas/direction-binding-audit.schema.json`](../schemas/direction-binding-audit.schema.json)
を正式な基準とし、この節は初見読者向けの抜き出しに限る。

| 項目 | 型又は列挙 | 役割 |
| --- | --- | --- |
| `schema_version` | 定数文字列 | `semantic-guard-direction-binding-audit/v1` |
| `audit_id` | 文字列 | `audit_id` 自身を除く完全な公開データに拘束した識別子 |
| `recorded_at` | RFC 3339 文字列 | 観測時刻。再現時は呼出側が明示できる |
| `subject_ref`, `producer_ref` | 型付きオブジェクト | 入力対象と公開限定機能の異なる同一性を記録する |
| `source_digest` | SHA-256 オブジェクト | `text` と任意の `context` を結合した原文内容のハッシュ値 |
| `input_regions` | 型付き配列 | `text` と `context` の役割、開始、排他的終了位置 |
| `rule_id` | 定数文字列 | `req.precondition.order_direction_unspecified` |
| `execution` | 型付きオブジェクト | 解析提供者、能力、被覆、診断及び `signal_only` 権限 |
| `decision_frame_summary` | オブジェクト | 尺度系の `decision-frame-summary/v3` |
| `direction_binding_summary` | オブジェクト | 非尺度系の `direction-binding-summary/v1` |
| `primary_rule_evaluation.state` | 列挙値 | `satisfied / gap / conflict / indeterminate / not_applicable / invalid` |
| `primary_rule_evaluation.emitter` | 列挙値 | `scalar / non_scalar / none` |
| `workflow_disposition.status` | 列挙値 | `pass / warn / block`。`reason_codes`、意味境界、受理効果を同じオブジェクトに保持する |
| `limitations` | 文字列配列 | 適用範囲と未立証事項 |
| `acceptance_owner` | 型付きオブジェクト | `human_external_to_criterion_loom`、`acceptance_status=pending`、`accepted=false` を記録する |

入出力の契約は、正常時に有効な JSON を `stdout`（標準出力）へ一件出し、診断を
`stderr`（標準誤出力）へ分ける。CLI の終了コードは、JSON 出力と契約検証の成功 `0`、使い方の誤り又は無効な入力
`2`、明示した監査状態閾値 `3` を持つ。`shadow-compare` だけは必須旧版観測不成立に
`4` を使う。

内部失敗は監査状態ではない。1.1.0 は `error_code / message / details / next_action` を持つ
公開エラーオブジェクトを定義しておらず、公開 JSON を出力しない。CLI は非零で終了し、
MCP はツール例外を返す。利用者の次行動は、`stderr` 又はツール例外の診断を保存し、入力又は
依存を訂正して再実行することである。想定外失敗なら診断、版及び最小再現入力を問題報告へ
添える。内部失敗に対して `workflow_disposition.status=block` を生成してはならない。

| 失敗経路 | コード又は例外 | 診断内容 | `stdout` | 次行動の手掛かり |
| --- | --- | --- | --- | --- |
| 使い方の誤り又は無効な入力 | CLI `2` | `stderr` 診断 | 空。正常データなし | 入力又はオプションを訂正して再実行する |
| 監査状態閾値 | CLI `3` | 正常データ内の `reason_codes` | 完全な正常データ | 監査状態を人間判断へ渡す |
| 内部失敗 | CLI非零又はMCPツール例外 | `stderr` 又は例外診断。構造化された詳細契約なし | 空。正常データなし | 診断、版、最小再現入力を保存して問題報告する |

`execution.status` は少なくとも `executed / not_configured / partial / failed / invalid` を
分離する。入力の `execution.status` が `not_configured`、`partial` 又は `failed` なら、
出力の `primary_rule_evaluation.state` を `indeterminate`、
`workflow_disposition.status` を `warn` とする。解析提供者が返した未加工の診断情報は
`execution.diagnostics` へ保持し、`reason_codes` には公開状態へ対応付けた安定したコードを置く。
尺度系と非尺度系の両方に判断枠が生じる、解析提供者の能力・`role=document` の全範囲
被覆・分割モードが契約を満たさない、又は公開データの項目間拘束が壊れる場合は、
情報不足を推測で補わず警告又は拒否する。

主操作の判断枠は `input_regions.role=source_text` 内に全て収まらなければならない。
`context` は原文ハッシュ値へ拘束される補助範囲だが、それ自体に置いた別質問や例だけを
主判定の対象にしない。方向を限定する必須表現を後置した `context` に移しても、
直接付着条件の代用にはならない。

Python 検証関数で呼出時の役割境界まで再現する場合は、結合済み `source_text` だけでなく、
既知の `text` と `context` を別引数で渡す。結合文字列だけを渡す検証は、ハッシュ値、
範囲及び自己申告された領域の内部整合を検査できるが、同じ文字列を別の `text/context`
境界を別の役割として付け替えていないという外部来歴までは立証しない。解析提供者の識別子、字句の原形、
品詞及び未加工の診断情報は宣言された受領記録の材料であり、この検証関数は解析提供者を再実行せず、
それらの外部真正性を認証しない。別引数を渡しても署名、発行者真正性又は信頼時刻に
なるわけではない。

### CLI と MCP の誤り境界

- CLI は正常な監査データを標準出力へ JSON として一件出す。既定の終了コード `0` は JSON 出力と契約検証の成功を表し、`workflow_disposition=pass` の別名ではない。
- `--fail-on warn|block` が指定閾値へ達した場合、CLI は JSON を標準出力へ出した後に終了コード `3` を返す。監査状態を書き換えない。
- 不正なオプション、入力読取り、UTF-8 又はサイズの誤りは標準誤出力へ診断を出し、終了コード `2` で終わり、正常な監査データを出さない。
- MCP は正常時に同じデータオブジェクトを返す。不正な `morphology` 値は `ValueError` とし、正常監査へ置き換えない。
- 解析提供者の未構成、部分結果及び通常の解析失敗は入出力上のエラーではなく、`execution` と `primary_rule_evaluation` に記録して返す。
- 内部スキーマ検証失敗又は想定外の依存関係の失敗では、有効な公開 JSON を出力しない。CLI は非零で終了し、MCP はツール例外を返す。
- 共通の構造化エラー形式は 1.1.0 の契約に含めず、将来課題とする。この形式が無いこと自体は、1.1.0 方向拘束公開限定機能のソースコード統合を妨げない。
- 呼出側は、非零終了やツール例外を監査上の `block` と読み替えてはならない。

ソースコード試験には代表的な CLI/MCP 実行とスキーマ検査が含まれるが、手書きの監査データは
本資料へ固定しない。選択配布物と実 Sudachi の代表実行はローカルで成立した。永続的な
完了証拠に使う場合は、対象成果物又は SHA へ拘束した別の検証記録に保存する。

## 検査範囲

### 尺度系（Scalar）

`decision-frame-summary/v3` は、登録済みの日本語による尺度系の後続選択構文だけを扱う。
登録範囲は14尺度族、49順序軸、56尺度語及び13数値対応である。尺度族が似ていても
順序軸が異なれば拘束として結合しない。

高極・低極、尺度名付き昇順・降順、現在の候補表へ直接付く見出し等を、同一判断枠・同一順序軸・直接付着という条件で検査する。裸の昇順・降順、別尺度、別集合、引用、例示、旧版、仮定、否定又は後置された表現は拘束に昇格させない。

### 非尺度系（Non-scalar）

`direction-binding-summary/v1` は、水平、垂直、奥行、時間、円環及び経路の六方向軸を扱う。左右、上下、前後、過去と未来、時計回りと反時計回り、起点と終点という登録済み二方向だけを、同一方向領域・同一軸・同一基準・直接付着の条件で検査する。

慣習的な既定順、画面座標、行順、世界知識又は候補結果から方向を補わない。直接結び付く位置に未知の方向表現らしきものがある場合は、欠落と断定せず `indeterminate` に留め、修正行動につながる主指摘を出さない。

## 証拠権限

形態素解析の権限上限は `signal_only` である。形態素、品詞、字句の原形又は解析器の
一致だけから、方向領域、方向拘束、主規則の充足、保留解除を導出してはならない。
拘束を成立させるのは、登録表と固定された原文照合規則に適合した、原文範囲付きの直接関係である。

解析器が未構成、部分被覆、失敗、能力不足又は由来不整合なら、その状態を成功扱いへ
置き換えない。`execution.status` と `primary_rule_evaluation.reason_codes` へ原因を記録し、
監査全体を無条件の `pass` にしない。

## 数値の境界

数値は `impact_evidence` の補助証拠に限る。項目を限定した反実仮想の証拠例を同一単位で
再現できる場合だけ付加してよい。数値の有無、値、同値、範囲、概数、欠損又は混合単位は、
主規則の適用、判断枠の状態、適合状態、確信度又は判定を出す検出器を変更しない。

従って「数値で結果が変わるから方向を決める」のではない。方向が未指定の表現と明示拘束との関係が一次判定であり、数値はその判断が持ち得る影響を説明するだけである。

## 非目的

この限定機能は次を行わない。

- 利用者に代わって採用方向を選ぶ。
- 自由形式の形容詞、任意の尺度又は一般自然言語を理解したと主張する。
- 慣例、常識、候補結果又は数値を入力として、方向拘束項目を生成する。
- 既存の要求関係監査、保証グラフ又はライフサイクル処理経路を統合し直す。
- 実務母集団での適合率、再現率、便益又は安全性を立証する。
- 0.1.0 の歴史アーカイブを現在の正解基準として再導入する。
- ローカルの vnext 候補を暗黙に採択又は正式な基準へ昇格する。
- `pass` を人間受理、領域正解、配備許可又は運用適格性へ読み替える。

## 人間判断境界

監査結果は、欠落、競合、判定不能、受理済み原文証拠及び却下証拠を、人が判断できる材料へ分ける。最終的な受理、差戻し、保留、延期、棄却及び採用方向の決定は監査系の外部に残る。契約適合や試験通過も、その人間判断を代行しない。

## 系譜と資料境界

この公開限定機能は `local feature source snapshot・2b62dfa0-6d90-5c31-ae2d-34ec55c94895`
からの `derived_from` であり、同じ対象への参照ではない。選択した五つのソースだけを
ハッシュ値で拘束し、正式な基準へ移植する。完全な対応表は
[方向拘束のソース対応表](../migration/direction-binding-source-map-2026-08-23.json) に置く。

`local vnext candidate・32646741-8cec-5fe3-b9f3-2971a8a787f0` は `candidate_ref` に留め、
1.1.0 方向拘束公開限定機能の移植元にしない。
`frozen legacy archive・3fd59352-b0d9-58f6-8279-9309c8960631` は当該 1.1.0 統合時点の
ソース対象から除外し、移動、改稿又は透過的な代替経路にしなかった。2026-08-24 の後続する
公開用修復は、旧版アーカイブの文書、付属スキルの文面及びアーカイブ目録だけを変更し、
実行時コード、スキーマ、試験及びテストデータは変更していない。

内容ハッシュ値は選択ソースと移植対象の内容一致証拠であり、対象の同一性ではない。
表示名、役割、配置パス又は同一内容だけから対象の同一性を推定しない。

## 検証状態

局所で成立したもの:

1. 二つの要約と最上位状態が項目を限定したスキーマに適合し、主判定を出す検出器が最大一つである。
2. 同一テストデータに対する CLI と MCP の契約版、状態、処置及び誤り意味が一致する。
3. 一回の `ProviderRequest` が返した形態素解析結果を、同じ原文・`context` 範囲付きで
   尺度系と非尺度系の両検出器へ入力する。
4. 既存要求関係監査、敵対的回帰及び CLI 説明の回帰を含む単体試験608件が、
   CPython 3.13で `44.866s`、隔離した CPython 3.11で `46.528s` にて通過した。
   時間値は性能保証ではない。
5. 1.1.0の `wheel` / `sdist` を構築し、選択した `wheel` の配布契約検証20件、
   24スキーマ、CLIコマンド四件、MCPツール四件、方向CLI・スキーマ・`--fail-on`・MCP振分けを再現した。
6. 新規 `wheel` と `nlp-ja` で、SudachiPy 0.6.11、SudachiDict-core 20260428、
   分割モード C を記録した。全56尺度語の `gap` / 高極 `bound` / 低極 `bound` 168組と、
   全18方向基底語の `gap` / 二方向 `bound` 54組、合計222組を公開監査及び厳格な
   ソースコード検証で再現した。

GitHubで成立したもの:

7. [PR #3](https://github.com/morie-lene/criterion-loom/pull/3)は実装コミット
   `c10ba59f8ab16659b50e9cbf13da07c9889ed195` をマージコミット
   `a77c3cbdc69295572e90333e2a6e9da690fbbb6d` へ統合し、PR の CI 四ジョブが成功した。
8. マージ後の `main` に対する
   [実行 32646816407](https://github.com/morie-lene/criterion-loom/actions/runs/32646816407)は、
   対象 SHA `a77c3cbdc69295572e90333e2a6e9da690fbbb6d` に対して、Python 3.11、
   Python 3.13、凍結済み 0.1.0 の基本動作確認、`wheel` 及び導入済み公開面の四ジョブを成功させた。
   詳細は[統合証拠](audits/direction-binding-integration-2026-08-23.md)へ分離した。

なお未成立のもの:

1. 実務母集団での妥当性、運用適格性及び外部真正性。
2. 公開索引上の1.1.0配布、リリース・タグ及び GitHub 上の成果物とローカル `wheel` のバイト同一性。
3. `acceptance_owner.acceptance_status=pending` を変更する外部人間の受理記録。
