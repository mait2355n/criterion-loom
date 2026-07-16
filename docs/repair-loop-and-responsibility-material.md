# 修復循環と責任適合材料

記録日: 2026-07-16
状態: 独立した opt-in 契約。実務効果、人間理解及び受理は未評価

## 目的

この契約は、監査所見を「直すべき対象」へ結び、外部で行われた変更を再監査し、所見解消・回帰・未解決・移譲を別々に記録する。また、コーディングエージェントが処理できる技術作業と、人間しか決められない意図、危険受容、権限及び最終受理を同じ出力へ潰さない。

実装対象は次の三契約である。

```text
responsibility-policy/v2       人間所有の役割・判断権・効果判定方針
          ↓
responsibility-material/v0     agent修復材料又は人間判断材料
          ↓
repair-cycle/v2                所見→外部変更→再監査→局所効果比較
```

機械契約の正本は `schemas/responsibility-policy.schema.json`、`schemas/responsibility-material.schema.json` 及び `schemas/repair-cycle.schema.json` であり、本文書は意味境界と交差項検査を説明する。

これは修復の実行器でも作業管制でもない。優先度、委譲、実行、質問送信、危険受容及び最終受理は外部に残る。

## 責任方針

`responsibility-policy/v2` は、役割、actor class、判断権、issue class ごとの責任役、許容役、必要判断権、先に行える技術作業、移譲条件及び修復効果方針を版と digest へ拘束する。v2 は採択判断の人間主体束縛を必須化した破壊的契約変更であり、v0 及び v1 の方針を暗黙には受理しない。

`adopted` には外部人間判断記録が必須である。判断記録は `decision_kind=adopt_responsibility_policy`、方針 ID、版、`policy_basis_digest` を完全一致で指す。`decided_by` は版・内容 digest 付き `decision_maker_identity` と同一 ID で、`decision_maker_kind=human`、`external_to_semantic_guard=true`、`status=accepted`、外部記録 locator 及び digest を必須とする。エージェント種別や主体 ID 不一致の判断は拒絶する。基礎要約は採択状態・判断記録・最終要約を除く意味内容から先に計算するため循環せず、役割、判断権又は効果方針を変えた記録へ古い採択判断を使い回せない。`pending` 又は `retired` から利用材料は作らない。コーディングエージェント、automation 又は管制面には、次の人間専有判断権を与えられない。

- 意図又は範囲の変更
- 残余危険の受容
- 権限の付与又は拡張
- 外部作用の許可
- 最終受理

この制約は、成功した実行や技術的通過から権限が逆流することを防ぐ。方針記録の存在、署名者本人性及び組織上の妥当性は別途検証を要する。

## 役割別材料

`responsibility-material/v0` は、同じ監査内容を一つの万能文章へ潰さず、次のどちらかとして出す。

### コーディングエージェント向け

- 観測事実、根拠、限界及び未解決範囲
- digest 付き修復対象と所在
- 欠陥仮説と意図する効果
- 成功条件、回帰防護及び停止条件
- 現在の役割で候補にできる作用
- 人間専有判断の禁止と移譲条件

修復対象には `finding_suppression_is_not_repair` と `changed_output_without_reaudit_is_not_success` を必須とする。警告文を消す、規則を弱める、出力が変わっただけで成功とする、といった空洞化を修復へ数えないためである。

### 人間向け

- 観測事実、根拠、限界及び未解決範囲
- 決めるべき一つの命題
- 必要判断権
- 二つ以上の選択肢と相違する便益・危険
- 停止及び再検討条件

材料内に決定値は持たせない。監査器が `accept`、`request_revision` 又は `defer` を先回りして埋めれば、人間判断境界を破るからである。材料の宛先も監査器は送信せず、外部呼出元又は管制面が扱う。

## 修復循環

`repair-cycle/v2` は次の監査入力を同名の cycle 欄へ束縛する。v2 は修復効果の査読対象要約と型付き独立査読記録を必須化した破壊的変更であり、v0 及び v1 は暗黙受理せず再作成を要する。

1. 対象と変更前監査の ID・digest。
2. 各所見の義務、変更前結果、根拠、限界、修復対象及び責任材料。
3. 外部で行われた変更の actor、identity evidence、authority evidence、時刻、前後対象 digest、変更証拠、停止条件結果。
4. 別個の変更後監査、全所見の前後比較、全回帰防護、移譲結果、独立査読参照及び残未解決。

各所見結果は、変更後監査、変更後対象 digest、義務 ID、結果値、結果所在及び結果 digest を持つ型付き `after_audit_result_ref` に束縛する。各回帰結果も同様に、変更後監査、変更後対象、guard ID、結果値及び原結果を `execution_result_ref` に束縛する。型付き結果の ID・digest は各証拠参照集合にも存在しなければならない。

`repair_attempt` の存在は成功を意味しない。変更後監査が無い間は `not_assessed` のままであり、自己申告しかない解消、変更前監査の再利用、所見又は回帰防護の欠落、変更前結果の置換を拒否する。

個別 `effect` は呼出元の自由値ではない。`repair-effect-transition/v1` が前後結果から導出し、矛盾する申告を拒絶する。変更後が `supported` なら `resolved`、前後同値なら `unchanged`、変更後が `refuted` 又は `invalid` へ悪化した場合は `worsened`、比較不能又は未知は `unknown` とする。局所総合結果は導出済み個別効果から次の保守的規則で導出する。

| 条件 | 局所結果 |
| --- | --- |
| 全所見解消、全回帰通過、移譲漏れなし、対象 digest 変更 | `improved` |
| 解消と未解決・未知・悪化が混在 | `mixed` |
| 悪化、回帰失敗、停止違反又は必要移譲漏れのみ | `regressed` |
| 全所見不変かつ全回帰通過 | `no_change` |
| 証拠未知又は対象不変のまま解消を主張 | `indeterminate` |

いずれも `claim_scope=declared_local_reaudit_only` であり、`field_repair_effect=not_evaluated` は固定される。実務でエージェントの修復成功率が上がるか、所要時間、回帰率、移譲精度、人間理解が改善するかは、独立した現場評価命題である。

責任方針の `independent_review_required=true` では、評価済み循環に一件以上の `repair-independent-review/v1` 記録を必須とする。記録は人間査読者の ID・版・digest、`relationship_to_subject=independent`、`external_to_semantic_guard=true`、循環 ID と修復試行を含む非循環の `cycle_basis_digest`、変更後監査参照、査読対象の `effect_basis_digest`、`status=accepted`、RFC 3339 時差付き査読時刻、一件以上の証拠参照、外部記録 locator・digest 及び記録全体 digest を束縛する。単な `{entity_id, entity_digest}`、空配列、全零 digest、別循環、別 after-audit、別効果要約、非人間又は非独立査読者は要件を満たさない。

`effect_basis_digest` は査読記録自体を除いた所見比較、回帰結果、移譲結果、局所総合結果、残未解決及び限界を対象に先に計算する。その後に外部査読記録を束縛するため循環しない。査読記録の `authenticity_status` は `unverified` 固定であり、記録内部の構造・参照・digest 一致を超える査読者の実在、組織上の独立性、署名及び内容真正性は依然として外部証明を要する。

## 検証済みの失敗経路

- 未採用方針からの材料生成
- 人間判断権を持つコーディングエージェント
- 必要判断権を持たない責任役
- 人間判断を禁止しない agent 材料
- 外部又は不可逆作用を「利用可能な作用」とする監査出力
- 方針と異なる人間質問
- anti-gaming 条件の消失
- 責任材料の差替え
- 変更だけを修復成功とする評価
- 変更前監査の after audit 化
- 自己申告だけの所見解消
- 所見又は回帰防護の欠落
- 変更前結果及び総合結果の洗替え
- `unresolved` のまま `resolved` とする個別効果洗浄
- 変更後監査・対象・義務・guard・結果値の参照差替え
- 方針が要求する独立査読の欠落
- 単な参照又は全零 digest による独立査読の空洞化
- 非人間・非独立査読者、別循環・別 after-audit・別効果要約への査読差替え
- 変更済み責任方針への採択判断再利用

## 残余危険

- 人間所有方針の主体同一性は記録内部で束縛するが、実人物対応、組織妥当性、権限記録、署名及び本人性は未立証。
- 修復 actor、authority evidence、時刻、変更証拠及び再監査証拠の真正性は、各 repair-cycle 記録の content digest だけでは立証できない。
- 対象 locator と実際の編集範囲が一致するかは、実在 artifact adapter を要する。
- 局所再監査が通っても、実務母集団での修復効果、理解可能性及び組織適合性は未評価。
- semantic-guard は修復を実行せず、管制面の優先度・配員・順序を決めず、人間へ質問を送らない。
