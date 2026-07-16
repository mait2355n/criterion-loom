# 運用資格と段階移行の独立契約

## 位置づけ

この契約は、単体試験や schema 適合から「実運用可能」を飛躍させないための監査面である。

- `operational-qualification/v0` は、選択済み配備包絡に対する運用証拠を評価する。
- `transition-plan/v0` は、`sidecar -> opt_in -> shadow -> default -> predecessor_retired` の各段階へ入る材料を評価する。
- どちらも返すのは `eligible`、`not_eligible`、外部人間判断記録を伴う `human_authorized` の監査材料だけである。
- 実配備、予定登録、既定値変更、危険受容、廃棄、旧系停止は行わない。

`human_authorized` も実行命令ではない。外部の人間判断記録が、対象 ID、版、対象要約値、対象段階を正確に指している、という記録内の事実を示すだけである。署名、人間の実在、権限、時刻、外部記録の存在は、この決定論的検証器だけでは認証できない。

## 運用資格プロファイル

`operational-qualification-profile/v0` の状態は次の三つに閉じる。

| 状態 | 外部人間判断 |
| --- | --- |
| `pending` | 採用・廃止判断を持てない |
| `adopted` | `adopt_operational_profile` が必須 |
| `retired` | 採用判断に加え、別 ID の `retire_operational_profile` が必須 |

判断記録は `profile_basis_digest` を指す。後から採用された方針を、採用前の観測へ遡及適用して資格化することはできない。

プロファイルは五つの配置形態を版・要約値の下へ置く。

- `local`
- `ci`
- `sidecar`
- `service`
- `external_provider`

一つの `deployment-envelope/v0` がこの中から一形態と一つの platform manifest を選ぶ。`selected` には `select_deployment_envelope` の外部人間判断が要る。包絡選択より前の実行観測は、後から包絡を選んでも資格証拠にはならない。

## 閉じた対象範囲

資格対象は次の五参照を必須とする。

- `subject_manifest_ref`
- `environment_manifest_ref`
- `dependency_manifest_ref`
- `provider_manifest_ref`
- `configuration_manifest_ref`

各参照は ID、版、SHA-256 要約値を持つ。実行観測は五参照全体の `scope_digest`、選択済み配備包絡、platform manifest、閾値参照へ拘束される。対象、環境、依存、提供者、構成、プロファイル、配備包絡のいずれかが変われば、既存資格を失効対象として再資格を要求する。

再資格時に以前の `execution_id` または生証拠要約値を再使用すると拒否する。要約値を付け替えただけの「再演習」を、新しい演習として数えないためである。

## 必須運用場面と閾値

資格は次の十二場面を一度ずつ要求する。欠落、重複、範囲外は契約違反である。

| 場面 | 資格化可能な主な実行種別 |
| --- | --- |
| `duration` | soak、運用観測 |
| `concurrency` | 並行実行試験、運用観測 |
| `load` | 負荷試験、運用観測 |
| `resource_exhaustion` | 資源枯渇試験 |
| `provider_failure` | 障害注入 |
| `restart` | 再起動演習 |
| `recovery` | 回復演習 |
| `compatibility` | 互換試験 |
| `platform` | platform 試験、運用観測 |
| `observability` | 観測可能性試験、運用観測 |
| `incident` | 事故対応演習 |
| `rollback_trigger` | 巻戻し演習 |

各閾値は `threshold_id`、版、測定量、比較演算子、目標値、単位、観測窓、要約値を持つ。観測は閾値参照と測定結果を持ち、`passed` が閾値未達なら拒否する。

`resource_exhaustion`、`provider_failure`、`restart`、`recovery`、`incident`、`rollback_trigger` は前後状態を必須とする。同一の前後要約値は状態遷移の証拠にならない。

次は `eligible` へ昇格しない。

- `failed`
- `not_run`
- `out_of_scope`
- 期限切れまたは信頼不能時刻
- `synthetic_fixture`
- 選択外 platform または閉じた manifest 範囲外
- 単体試験、schema 試験、smoke 試験だけの実行
- 不採用または廃止済みプロファイル
- 未選択配備包絡
- 独立査読の欠落、棄却、判定不能

## 独立した未閉鎖軸

運用資格が `eligible` でも、次は常に別軸として `open` のまま残る。

- 意味・現場における欄妥当性
- 安全性
- 人間による最終受理

運用耐性の証拠は、要求が正しいこと、安全であること、利用者に適すること、人間が受理したことを代替しない。独立査読も同様で、査読者は実行観測の実行者と別 identity でなければならない。

## 段階移行

段階順は固定する。

1. `sidecar`
2. `opt_in`
3. `shadow`
4. `default`
5. `predecessor_retired`

対象段階より前の `stage_history` は、この順序の完全な接頭列でなければならない。段階の飛越し、同じ predecessor/successor、別範囲の完了記録、合成完了記録は受理しない。

移行計画は以下を版・要約値付きで持つ。

- predecessor と successor
- 選択済み配備包絡と現行運用資格
- 互換窓と互換証拠
- 構成、データ、界面、証拠の移行参照
- 登録簿更新参照
- 巻戻し・回復計画参照
- 廃棄・旧系停止計画参照
- 段階別 entry criterion
- 全段階に適用する abort criterion

`default` と `predecessor_retired` は、次の gate を一度ずつ要求する。

- `field_validity`
- `operational_qualification`
- `human_use_validation`
- `security_assessment`
- `register_readiness`
- `compatibility_migration`
- `shadow_observation`
- `rollback_recovery_rehearsal`
- `independent_observation`

安全性は運用資格が閉じないため、移行 gate でも独立参照として要求する。`register_readiness`、`compatibility_migration`、`rollback_recovery_rehearsal` は、計画本体の対応参照と正確に一致しなければならない。運用資格 gate は、供給された資格 ID、版、要約値、結果と一致し、移行評価時点でも期限内でなければならない。

## 中止と巻戻し

全 abort criterion は一度ずつ観測する。

- 未発火なら `not_triggered`
- 発火したなら `aborted_and_rollback_started`
- 発火後の `continued` は契約違反

中止条件が発火した場合、正しく停止・巻戻しを開始していても当該段階は `not_eligible` である。人間判断記録で失敗、古さ、合成証拠、範囲外、中止を上書きすることはできない。

## 人間判断門

計画自体の `adopted` には `adopt_transition_plan` が要る。対象段階の全 gate が満たされた後でも、結果はまず `eligible` である。`human_authorized` には、現在の `gate_set_digest` と対象段階を指す `authorize_cutover_stage` が要る。

`predecessor_retired` は更に二つの判断を分ける。

1. 当該段階へ進む cutover 判断
2. 巻戻し不能化と predecessor 回復不能化を明示的に認識した `authorize_irreversible_predecessor_retirement`

二つは別 `decision_id` でなければならない。後者が無ければ、cutover 判断があっても旧系廃止について `human_authorized` にはならない。

## 合成試験の意味

`tests/test_operational_qualification.py` と `tests/test_transition_control.py` は契約の拒否・導出挙動を確認する合成適合試験である。そこで `eligible` や `human_authorized` を生成できても、実環境、実 platform、実事故、実利用者、実判断者に対する準備完了の証拠ではない。

実務で用いるには、同じ schema に適合する実行観測、生証拠、独立査読、外部人間判断記録を、現用 manifest と時刻へ正確に拘束して別途取得しなければならない。
