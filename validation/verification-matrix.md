# v1 検証体系の可読投影

投影時点: 2026-08-24T13:01:52+09:00
正本: [`verification-source.json`](verification-source.json)
正本 schema: [`verification-source.schema.json`](verification-source.schema.json)
正本 SHA-256: `cd36b827bfea34fe5136a6e0677be400dabf62583bc325466050aeb271a19736`

## 役割

この文書は、人間が現在地を走査するための**非正規な編纂投影**である。検証項目、状態、証拠参照、反証、未証明範囲、再検証条件の正本は `verification-source.json` とし、この文書の表と衝突した場合は正本を先に直す。全値の機械投影は `verification-source.generated.md` であり、内部検証器はそちらの生成文字列を完全一致で検査する。この編纂説明の意味同値までは検査しない。

2026-07-16 の実装作業で、状態・行為・修復・安全運用・評価・運用資格等の局所 sidecar 契約と敵対試験が追加された。ただし、それだけで下表の証拠拘束済み状態を更新しない。実装面の最新説明は `docs/implementation-status.md`、正本へ登録済みの観測と状態だけは本 JSON 正本、実地妥当性と人間採択は別の将来証拠として扱う。

役割を次のように分ける。

| 実体 | 役割 | それだけでは言えないこと |
| --- | --- | --- |
| `docs/prototypes/origin-requirement.md` | 目的正本 | 実装済み、検証済み |
| `constitution/semantic-guard-constitution.yaml` | 規範・意味・権限境界 | 実装適合、実務妥当性 |
| `verification-source.json` | 検証要求、状態、証拠関係の正本 | 実行が起きたこと、最終受理 |
| `verification-source.generated.md` | 全 container・scalar の決定論的完全投影 | 値の実世界での真偽、説明上の意味同値 |
| 本文書 | 判断用に編纂した可読説明 | 正本更新、全値同値、実行証拠 |
| 日付付き検証 JSON | 対象 snapshot 上の観測証拠 | 一般性能、真正性、人間受理 |

## 実装系譜と採用境界

| 位置付け | 実装 identity | 意味 |
| --- | --- | --- |
| 現正本 | `semantic-guard v1・implementation.semantic-guard.v1` | root 昇格後の正本配置と製品 identity |
| 派生元 | `semantic-guard vNext candidate・implementation.semantic-guard.vnext` | v1 正本の実装上の派生元。現正本ではない |
| 旧版 | `semantic-guard v0.1.0・implementation.semantic-guard.v0.1.0` | 比較・移行・再現のために保存する旧実装 |

repository canonicalization は locator と製品 identity の昇格に限る。これだけでは、`0.2.0-draft` の憲法候補、工学規則、実務妥当性、運用資格、人間の最終受理を採択したことにならない。`INV-VN-*` は内容同一の不変条件 identity として維持し、表示名や配置変更だけを根拠に別 identity として扱わない。

従来の `evidence / partial / missing` 一軸は廃止する。`evidence` は状態値ではなく、識別され、時点・対象・取得方法・信頼強度・限界を持つ観測実体である。

## 正本件数

| collection | 件数 |
| --- | ---: |
| state profiles | 10 |
| evidence observations | 6 |
| evidence effects | 27 |
| verification items | 17 |
| implementation conformance items | 27 |
| views | 5 |
| unresolved families | 17 |
| resolution obligations | 52 |
| resolution paths | 19 |

この件数は正本の登録実体数であり、実装済み数、解消済み数、受理済み数ではない。2026-07-16 の実装作業で追加した六検証項目はすべて `state.not-assessed`、対応する七未解決群（解析 route 群を含む）はすべて未解消である。

## 独立状態軸

| 軸 | 語彙 | 問い |
| --- | --- | --- |
| 実装 | `not_assessed / missing / partial / implemented / not_applicable` | 必要な機構又は契約が存在するか |
| 検証 | `not_run / passed / failed / inconclusive / invalid / not_applicable` | 宣言した要求に対して指定方法で検査したか |
| 妥当性確認 | `not_evaluated / supported_in_context / refuted_in_context / inconclusive / not_applicable` | 意図した利用状況と利用者目的に役立つか |
| 限定的保証 | `outcome / finality / challenge / coverage` | 証拠と前提の範囲で命題をどこまで支持できるか |
| 証拠鮮度 | `current / stale / unbound` | 現在の対象 snapshot と利用文脈へ証拠が結び付いているか |
| 人間受理 | `pending / accept / request_revision / defer` | 人間が残危険を見て何を決めたか |

一つの軸から別の軸を推測しない。`implemented + passed` でも、妥当性確認、真正性、現行性、人間受理は成立しない。

`terminal` は `current` な対象拘束、`satisfied` 又は `refuted`、`challenge=none`、`coverage=complete` が同時に成立する時だけ許す。`unbound` な状態は常に `provisional` かつ非完全被覆である。また `refuted` 又は `challenge=open/conflict` は、項目に位置付けた反証参照を必須とする。不確実であることだけを根拠に `challenge` を生成しない。

各行の人間受理は、再利用可能な技術状態 profile ではなく、正本頂上の `human_acceptance` を投影する。項目別の人間判断が将来必要になった場合は、人間所有の判断記録、時刻、対象参照を持つ別実体として追加する。

## 原点要求被覆

| 検証項目 ID | 原点 | 実装 | 検証 | 妥当性確認 | 限定的保証 `outcome / finality / challenge / coverage` | 鮮度 | 人間受理 | 主な未証明範囲 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `verification.or01.lifecycle-surface-coverage` | OR-01 | partial | failed | not_evaluated | refuted / provisional / open / partial | unbound | pending | request、exploration_question、decision_state、plan、action、realization_policy、diff、verification、completion_claim。現 v1 縦断は requirement のみ |
| `verification.or01.engineering-knowledge-governance` | OR-01 | partial | inconclusive | not_evaluated | undetermined / provisional / open / partial | unbound | pending | 規格版・条項又は概念、解釈、採用、例外、失効、再審査 |
| `verification.or01.discovery-effectiveness` | OR-01 | partial | inconclusive | not_evaluated | undetermined / provisional / open / partial | unbound | pending | 未知の未知の発見率、跨文・照応、実務母集団、全工程 profile |
| `verification.or02.bounded-claim-model` | OR-02 | partial | inconclusive | not_evaluated | undetermined / provisional / open / partial | unbound | pending | 公開高信頼級の根拠拘束、保証 profile、実行観測、真正性、因果性 |
| `verification.or02.action-occurrence-and-procedure` | OR-02 | missing | failed | not_evaluated | refuted / provisional / open / partial | unbound | pending | 行為発生、主体、権限、観測者関係・信頼級、時刻、環境、入出力、実通過工程 |
| `verification.or02.artifact-provenance-authenticity` | OR-02 | missing | failed | not_evaluated | refuted / provisional / open / partial | unbound | pending | 原証拠照合、成果物生成、真正性、信頼時刻、再生防御、因果性 |
| `verification.or03.repair-effect` | OR-03 | not_assessed | not_run | not_evaluated | undetermined / provisional / none / not_evaluated | unbound | pending | 再計画・再実装・完了報告の修正成功、回帰、正しい人間移譲。機能欠落の主張自体も閉じた対象 manifest に未拘束 |
| `verification.or03.human-decision-boundary` | OR-03 | implemented | passed | not_evaluated | satisfied / provisional / none / partial | unbound | pending | 将来の受理記録の理解容易性と完全性 |
| `verification.cross.field-validation` | OR-01/02/03 | partial | not_run | not_evaluated | undetermined / provisional / none / not_evaluated | unbound | pending | 母集団、標本、閾値、不確実性、独立判定、実務価値 |
| `verification.cross.secure-and-responsible-operation` | OR-01/02 | not_assessed | not_run | not_evaluated | undetermined / provisional / none / not_evaluated | unbound | pending | 保護情報、外部送信、秘密・個人情報、敵対入力、依存資源来歴、最小権限、保持・事故対応。機能欠落の主張自体も閉じた対象 manifest に未拘束 |
| `verification.cross.operational-reverification` | OR-01/02/03 | partial | inconclusive | not_evaluated | undetermined / provisional / open / partial | unbound | pending | 対象 manifest、証拠失効、長時間、並行、負荷、複数 OS、障害回復、incident feedback |
| `verification.or02.proof-obligation-and-assurance-graph-soundness` | OR-01/02/03 | not_assessed | not_run | not_evaluated | undetermined / provisional / none / not_evaluated | unbound | pending | v0 cross-field 閉包、v1 proof obligation graph、独立再集約、mutation 耐性、保証 profile・移行採用、独立敵対査読 |
| `verification.cross.register-completeness` | OR-01/02/03 | not_assessed | not_run | not_evaluated | undetermined / provisional / none / not_evaluated | unbound | pending | 分母・disposition 採用、omission 検出、位置付き解消／非適用、handoff 後の不確実性保持、独立査読 |
| `verification.cross.lifecycle-trace-and-composition` | OR-01/02/03 | not_assessed | not_run | not_evaluated | undetermined / provisional / none / not_evaluated | unbound | pending | 工程間の同一性・命題・義務・権限・証拠・未解決範囲、split/merge/revision/cancellation/supersession/repair の意味合成 |
| `verification.cross.operational-qualification` | OR-01/02/03 | not_assessed | not_run | not_evaluated | undetermined / provisional / none / not_evaluated | unbound | pending | 配備 envelope、長時間、並行、負荷、枯渇、provider 障害、restart/recovery、互換性、複数 platform、incident、独立資格査読 |
| `verification.cross.transition-and-cutover` | OR-01/02/03 | not_assessed | not_run | not_evaluated | undetermined / provisional / none / not_evaluated | unbound | pending | opt-in/default 移行、互換期間、shadow、証拠 migration、abort/rollback rehearsal、disposal、旧版 retirement、人間 cutover 判断 |
| `verification.cross.human-operational-use` | OR-01/02/03 | not_assessed | not_run | not_evaluated | undetermined / provisional / none / not_evaluated | unbound | pending | coding agent／人間の責任分離、routing、理解可能性、修正可能性、escalation、権限誤り、実務判断支援 |

結論は明瞭で、要求関係監査の局所実装は進んでいるが、原点要求全体は未達である。特に OR-02 の行為立証・proof graph 健全性、工程横断の意味合成、OR-03 の修正効果と責任適合利用は、単なる残作業ではなく別個の検証命題として扱う。register へ追加されたこと自体は、その機構の実装、妥当性、受理を意味しない。

### OR-01 工程面の閉じた分母

`verification.or01.lifecycle-surface-coverage.lifecycle_surface_assessments` は、原点要求の十面と一対一である。内部検証器は面集合の完全一致、重複、状態・証拠参照閉包を検査する。

| 工程面 | 実装 | 検証 | 鮮度 | 現在の意味 |
| --- | --- | --- | --- | --- |
| `request` | not_assessed | not_run | unbound | v1 profile・契約・縦断実装の有無を閉じた対象 manifest へ未拘束 |
| `exploration_question` | not_assessed | not_run | unbound | v1 profile・契約・縦断実装の有無を閉じた対象 manifest へ未拘束 |
| `requirement` | implemented | passed | unbound | 構造化機能要求の関係監査は実装済み。日付付き試験報告は現 source manifest へ未拘束、実務未妥当化 |
| `decision_state` | not_assessed | not_run | unbound | v1 profile・契約・縦断実装の有無を閉じた対象 manifest へ未拘束 |
| `plan` | not_assessed | not_run | unbound | v1 profile・契約・縦断実装の有無を閉じた対象 manifest へ未拘束 |
| `action` | not_assessed | not_run | unbound | 行為立証の検証要求模型はあるが、runtime 縦断実装の有無を閉じた対象 manifest へ未拘束 |
| `realization_policy` | not_assessed | not_run | unbound | v1 profile・契約・縦断実装の有無を閉じた対象 manifest へ未拘束 |
| `diff` | not_assessed | not_run | unbound | v1 profile・契約・縦断実装の有無を閉じた対象 manifest へ未拘束 |
| `verification` | not_assessed | not_run | unbound | 検証成果物・検証主張を監査する profile・縦断実装の有無を閉じた対象 manifest へ未拘束 |
| `completion_claim` | not_assessed | not_run | unbound | 完了主張・受理材料の profile・契約・縦断実装の有無を閉じた対象 manifest へ未拘束 |

## 発見性能

現在の最大の穴は、生成済みの `unknown / conflict / invalid / coverage gap` を保持する能力と、それらを最初に発見する能力を分けて測れていないことだった。正本では `verification.or01.discovery-effectiveness` として独立させた。

形態素解析 ablation、係り受け・照応精度、lifting 拡張、LLM の増分価値は `unresolved.analyzer-route-effectiveness-and-incremental-value` に統合登録した。四者を同じ工学基準、対象拘束、独立標識、holdout、authority ceiling の下で比較するための統合であり、各評価責務は別 ID のまま保つ。

| 対象 | 現在の実体 | 現状態 | 次に必要な証拠 |
| --- | --- | --- | --- |
| 目標義務・関係の分母 | 構造化機能要求一種と三関係 | partial | 工程・成果物種別ごとの工学根拠付き義務集合、適用条件、反適用条件 |
| 既知未解決の保持 | INV-VN-001〜014 と fail-closed 集約 | implemented / passed | 発見性能とは別であることを維持 |
| 否定・引用・条件等の疑義化 | 人工 fixture と残余危険門 | implemented / passed locally | 独立標本、言い換え変形、跨文、照応、holdout |
| 形態素解析の寄与 | Sudachi、`signal_only` | implemented / passed locally | 解析なしとの ablation、誤満足・過警告・棄権差分 |
| 依存構造候補の寄与 | GiNZA、`candidate_only` | partial / inconclusive | `coreference_candidate`、長文、跨文、係り受け誤り別の評価 |
| LLM 候補の寄与 | 呼出元提出束、`candidate_only` | partial / inconclusive | 同一 corpus 上の増分価値、再現性、模型版差、費用・遅延 |
| 実務母集団 | 未定義 | not_evaluated | 領域別層化標本、独立二重判定、裁定、費用行列、不確実性 |
| 修正効果 | 未実装 | not_evaluated | finding→修正対象→再監査の前後比較、回帰、正しい escalation |

性能指標は少なくとも次を別々に保つ。

- `catastrophic_false_satisfaction`
- `false_defect`
- `abstention_or_undetermined_rate`
- `silent_coverage_gap`
- `challenge_capture`
- `source_span_fidelity`
- `repair_effect`

単一 score へ畳まない。特に重大誤満足を、平均精度や棄権率で相殺してはならない。

また、field 評価の protocol と実行は独立した前提なしに開始できない。`obligation.field-policy.evaluation-protocol` と `obligation.field-policy.execute-evaluation` は、少なくとも `obligation.field-policy.human-risk-choice`、`obligation.rule-pack.human-adoption`、`obligation.state-derivation.implement-assessment-record`、`obligation.secure-operation.human-policy` を前提とし、後者はさらに protocol と `obligation.field-policy.independent-labels` を要する。これは工程優先度ではなく、「何を正解・対象・安全な評価経路と見なすか」が未決定のまま数値だけを生成しないための意味依存である。

## 行為立証

| 主張 | 現状態 | 現在あるもの | 欠けるもの |
| --- | --- | --- | --- |
| 主張模型の分離 | partial / inconclusive | 命題、範囲、規則、証拠、導出、信頼前提、反証条件、被覆、未証明範囲 | 保証 profile、公開 `independently_observed / signed / formally_verified` の根拠拘束、全 claim class の実例と実務妥当性確認 |
| 行為発生 | missing / failed | 文書中 fact と span | runtime event、observer、actor、time、environment、I/O digest |
| 主体同一性・権限 | missing / failed | schema 上の参照・境界 | 信頼根、主体認証、権限 snapshot、付与元 |
| 手続適合 | missing / failed | 計画文の局所監査 | 実通過工程、stop condition、許可範囲、逸脱記録 |
| 成果物生成・来歴 | missing / failed | local digest 整合 | 生成 event、対象 digest、原証拠、独立観測、来歴機構 |
| 真正性・因果性 | missing / failed | 非目標と過大主張防止 | 署名又は append-only 根、信頼時刻、再生防御、因果模型 |

構造が整っていること、行為が発生したこと、主体が誰か、権限があったこと、成果物を生成したこと、検証が成功したことは、別々の命題である。

## 安全・責任ある運用境界

`verification.cross.secure-and-responsible-operation` は候補基準であり、人間が採用していない。保安走査器を名乗るためではなく、監査器自身が実資料や外部解析器を扱う時に別種の害を隠さないための分母である。

| 境界 | 現状態 | 採用前に必要なもの |
| --- | --- | --- |
| 保護情報・外部送信 | not_assessed / not_run | 資料分類、同意又は権限、最小化、秘密・個人情報除去、送信先、保持・削除方針 |
| 外部 LLM・解析器 | not_assessed / not_run | provider 別送信門、模型・指示・資源来歴、prompt injection と情報流出の敵対試験 |
| 依存・模型・辞書・rule pack | not_assessed / not_run | 版・取得元・digest・信頼根・置換検知・失効条件 |
| 権限・資源枯渇・事故 | not_assessed / not_run | 最小権限、時間・容量制限、停止条件、事故証拠、rollback・通知境界 |

採用、許容する外部送信、保持、権限、危険水準は人間判断であり、実装と敵対検証はその後続義務である。非採用だけでは欠落は消えず、実資料・保護情報、外部 provider、特権作用、永続運用を除外する版付き非適用境界と再評価起動条件を人間が受理し、対象・構成・情報流・権限・保存経路の位置付き観測が実際の境界内状態を示した場合だけ、採用枝の後続義務を非活性にできる。意味監査の正しさから安全運用を推測してはならない。

## 局所実装適合

以下は `view.local-implementation-conformance` の投影である。`passed` は日付付き観測が命名した局所試験で不変条件を確認したとの記録だけを示す。統合試験と実解析器試験には、試験対象 source の閉じた manifest が無いため、これらを参照する項目の鮮度は `unbound` である。現実装への現行適合を、この表だけから主張しない。

| 正本項目 | 不変条件 | 実装 | 検証 | 妥当性確認 | 証拠観測 | 主な限界 |
| --- | --- | --- | --- | --- | --- | --- |
| `conformance.INV-VN-001` | unknown/conflict/invalid/被覆不足を pass が捨てない | implemented | passed | not_evaluated | integrated-2026-07-16 | 未解決の発見率は別命題 |
| `conformance.INV-VN-002` | 直接 satisfied は残余危険門まで provisional | implemented | passed | not_evaluated | integrated-2026-07-16 | conditional の実務見逃し未評価 |
| `conformance.INV-VN-003` | terminal satisfaction の閉包条件 | implemented | passed | not_evaluated | integrated-2026-07-16 | 真正性・独立観測なし |
| `conformance.INV-VN-004` | 必須解析器障害を silent success にしない | implemented | passed | not_evaluated | integrated-2026-07-16 | 負荷・資源枯渇・並行障害未評価 |
| `conformance.INV-VN-005` | 候補解析器は支持・解除不能 | implemented | passed | not_evaluated | integrated-2026-07-16 | 外部模型同一性なし |
| `conformance.INV-VN-006` | 引用等を肯定へ自動昇格しない | implemented | passed | not_evaluated | integrated-2026-07-16 | 実務言い換え・跨文未評価 |
| `conformance.INV-VN-007` | 開いた自由文から missing を断定しない | implemented | passed | not_evaluated | integrated-2026-07-16 | 複数要求分割未実装 |
| `conformance.INV-VN-008` | 人間の危険受容で監査事実を消さない | partial | inconclusive | not_evaluated | integrated-2026-07-16 | 外部 append-only 受理記録なし |
| `conformance.INV-VN-009` | score を正しさ確率にしない | implemented | passed | not_evaluated | integrated-2026-07-16 | 旧利用者の誤読監視なし |
| `conformance.INV-VN-010` | schema/digest/由来破損を pass にしない | implemented | passed | not_evaluated | integrated-2026-07-16 | 署名・信頼時刻なし |
| `conformance.INV-VN-011` | 分野語共有だけを関係証明にしない | implemented | passed | not_evaluated | integrated-2026-07-16 | 語彙・作用族・跨文因果の被覆不明 |
| `conformance.INV-VN-012` | 解析器 ok は span 被覆と能力閉包を要する | implemented | passed | not_evaluated | integrated + real-nlp-smoke | 能力会計は意味精度ではない |
| `conformance.INV-VN-013` | 公開集約欄の矛盾を受理しない | implemented | passed | not_evaluated | integrated-2026-07-16 | 異版移行・外部直列化器未評価 |
| `conformance.INV-VN-014` | 入力同一性と監査観測同一性を分ける | implemented | passed | not_evaluated | integrated-2026-07-16 | 時刻証明・再生防御・主体認証なし |

## 処理系列

| 正本項目 | 段階 | 実装 | 検証 | 妥当性確認 | 限界 |
| --- | --- | --- | --- | --- | --- |
| `conformance.stage.input-boundary` | 0 入力契約と記録境界 | implemented | passed | not_evaluated | 一つの構造化機能要求 profile のみ |
| `conformance.stage.provisional-direct-audit` | 1 義務別仮判定 | implemented | passed | not_evaluated | 根拠統治と実務被覆が不足 |
| `conformance.stage.residual-risk-gate` | 2 独立残余危険門 | implemented | passed | not_evaluated | 未知の未知の発見率なし |
| `conformance.stage.morphology` | 3 形態素解析 | implemented | passed | not_evaluated | signal_only、検出への増分未測定 |
| `conformance.stage.dependency-analysis-bundle` | 4 依存構造解析束 | partial | inconclusive | not_evaluated | coreference 欠落、長文・精度未評価 |
| `conformance.stage.versioned-lifting-rule` | 5 版付き決定論的導出 | partial | inconclusive | not_evaluated | 条件付着 v0 のみ |
| `conformance.stage.llm-candidate` | 6 LLM 候補 | partial | inconclusive | not_evaluated | 自動 API、模型同一性、増分価値未評価 |
| `conformance.stage.obligation-reaggregation` | 7 義務別再集約 | implemented | passed | not_evaluated | 上流の未発見を補えない |
| `conformance.stage.decision-request-materialization` | 8 判断要求生成 | implemented | passed | not_evaluated | 理解容易性、正しい routing、修正効果未評価 |

## 完全性・移行観測

| 正本項目 | 実装 | 検証 | 妥当性確認 | 現在の意味 | 主な限界 |
| --- | --- | --- | --- | --- | --- |
| `conformance.completeness.provider-accounting` | implemented | passed | not_evaluated | 能力、資源版、対象 span 被覆を会計 | 意味精度の証明ではない |
| `conformance.completeness.public-result` | implemented | passed | not_evaluated | 義務実体から公開集約を再検査 | 原文なし excerpt、真正性未確認 |
| `conformance.migration.legacy-baseline` | implemented | passed | not_evaluated | 旧版対象、実行器、adapter を固定 | OS、host、時刻、動的 library は対象外 |
| `conformance.migration.legacy-characterization` | partial | inconclusive | not_evaluated | 334 件中 332 件通過、既知 2 失敗を保持 | 旧版を正解 oracle としない |

## 証拠観測

| 証拠 ID | 種別・信頼 | 対象拘束 / 鮮度 | 支持する範囲 | 支持しない範囲 |
| --- | --- | --- | --- | --- |
| `evidence.origin-requirement.snapshot.2026-08-24` | source_snapshot / locally_observed | bound / current | digest 固定した原点要求の記録内容 | 実装、効果 |
| `evidence.constitution.snapshot.2026-08-24` | source_snapshot / locally_observed | bound / current | digest 固定した規範模型と状態語彙 | 実装、実務性能 |
| `evidence.public-trust-basis-inspection.2026-07-17` | source_snapshot / locally_observed | bound / current | 公開 provenance schema の高信頼級に、観測者独立性・署名・信頼根・形式模型・検証器の条件拘束が無いという局所反証 | 実際の悪用、将来の修正、外部証拠真正性 |
| `evidence.integrated-verification.2026-07-16` | test_execution / tool_reported | unbound / unbound | 日付付き記録が報告する局所試験、schema、配布、MCP、旧版比較 | 現 source snapshot への適用、実務性能、真正性、運用受理 |
| `evidence.real-nlp-smoke.2026-07-16` | test_execution / tool_reported | unbound / unbound | 日付付き記録が報告する五例の実解析器経路、能力欠落 | 現解析器 source・資源への適用、母集団精度、一般化 |
| `evidence.full-evaluation.2026-07-11` | historical_assessment / locally_observed | unbound / stale | 歴史的欠落と改良方向 | 現 snapshot の完成状態 |

証拠ファイル名や試験定義は、証拠観測そのものではない。実行対象、環境、時刻、結果、digest、限界へ結び付いた場合だけ観測証拠として参照する。

## 証拠の型付き作用

`evidence_refs / counterevidence_refs` は参照一覧に過ぎず、何をどの極性・状態軸で動かすかまでは表せない。正本の `evidence_effects` は対象項目、証拠観測、`supports / refutes / challenges / contextualizes`、状態軸、限定命題、宣言済み観測位置、限界を結ぶ。正側・反証側の参照集合、支持を要する正状態、反証・疑義状態を双方向に閉じる。`proposition` 次元だけの `contextualizes` は命題形成の文脈であり、実装・検証・保証の支持には使えない。また `lifecycle_surfaces` で限定した部分面の支持は、その面だけへ作用し、親の全工程被覆を支持しない。以下は可読投影であり、説明文の意味同値までは内部検証器が立証しない。

| 作用 ID | 対象項目 | 証拠 | 極性 | 限定命題と限界 |
| --- | --- | --- | --- | --- |
| `effect.origin-requirement.purpose-items.contextualizes` | lifecycle / human boundary / secure-operation | origin snapshot | contextualizes | 原点の分母・権限・危険文脈だけ。実装状態を支持しない |
| `effect.origin-requirement.rebased-verification-denominator.contextualizes` | proof graph / register / lifecycle composition / operational qualification / transition / human use | origin snapshot | contextualizes | 六追加命題が原点の限定立証・工程横断・修正／人間判断・sidecar 境界から導かれる文脈だけ。実装・検証・運用・移行・受理を支持しない |
| `effect.constitution.normative-items.contextualizes` | engineering / bounded claim / repair / human / secure | constitution snapshot | contextualizes | 規範語彙と不変条件だけ。適合・実行を支持しない |
| `effect.historical-review.governance-action-authenticity.contextualizes` | governance / action / authenticity | historical review | contextualizes | 現命題の動機。旧対象の現行性は無い |
| `effect.lifecycle.integrated-record.contextualizes` | lifecycle coverage | integrated record | contextualizes | 追加工程面の文脈。分母全体は列挙しない |
| `effect.lifecycle.requirement-slice.integrated-suite.supports` | lifecycle requirement surface | integrated suite | supports | requirement 面の局所実装・検証・保証だけを暫定支持 |
| `effect.discovery.integrated-record.contextualizes` | discovery effectiveness | integrated record | contextualizes | 五例の実解析器要約。母集団性能ではない |
| `effect.real-nlp.discovery-field.contextualizes` | discovery / field validation | real NLP smoke | contextualizes | 実 provider の限定文脈。実務妥当性を支持しない |
| `effect.bounded-claim.integrated-schema.contextualizes` | bounded claim | integrated schema record | contextualizes | schema 自己検証の文脈。行為・真正性を支持しない |
| `effect.action-artifact.integrated-omission.contextualizes` | action / artifact authenticity | integrated omissions | contextualizes | 未実装一覧の位置付き文脈。反証は別作用 |
| `effect.repair.integrated-acceptance.contextualizes` | repair effect | acceptance state | contextualizes | 状態分離の文脈。修正効果を支持しない |
| `effect.human-boundary.integrated-acceptance.supports` | human decision boundary | acceptance state | supports | 自動検証と人間受理の分離を暫定支持。理解容易性は未評価 |
| `effect.field.integrated-unverified.contextualizes` | field validation | unverified list | contextualizes | 実務評価欠落の位置付き記録 |
| `effect.operational.integrated-unverified.contextualizes` | operational requalification | unverified list | contextualizes | 運用試験欠落の文脈。再資格を支持しない |
| `effect.local-conformance.integrated-suite.supports` | 局所不変条件・段階・完全性二十項目 | integrated suite | supports | 零失敗集約を暫定支持。個別試験 locator と対象 manifest は無い |
| `effect.real-nlp.provider-paths.supports` | INV-VN-012 / morphology / provider accounting | real NLP cases | supports | 実解析器経路と能力会計を暫定支持。意味精度ではない |
| `effect.partial-conformance.integrated-record.contextualizes` | INV-VN-008 / lifting / LLM / legacy characterization | integrated suite | contextualizes | 部分状態の文脈だけ。満足保証を支持しない |
| `effect.dependency-analysis.real-nlp.contextualizes` | dependency bundle | provider contract | contextualizes | coreference 欠落を含む部分実装文脈 |
| `effect.legacy-baseline.integrated-record.supports` | legacy baseline | baseline record | supports | manifest 一致を暫定支持。旧挙動の正しさではない |
| `effect.lifecycle-surface.integrated-next-action.refutes` | `verification.or01.lifecycle-surface-coverage` | `evidence.integrated-verification.2026-07-16` | refutes | 追加の工程縦断が必要との記録は全十面実装済み命題を反証する。一つの反例には足るが、現分母全体の列挙証拠ではない |
| `effect.engineering-governance.historical-review.challenges` | `verification.or01.engineering-knowledge-governance` | `evidence.full-evaluation.2026-07-11` | challenges | 歴史的監査の統治欠落。旧対象であり現 snapshot の状態は確定しない |
| `effect.discovery.real-nlp-missing-coreference.challenges` | `verification.or01.discovery-effectiveness` | `evidence.real-nlp-smoke.2026-07-16` | challenges | `coreference_candidate` 欠落。一能力・五例の観測で、母集団発見率ではない |
| `effect.bounded-claim.public-trust-basis.challenges` | `verification.or02.bounded-claim-model` | `evidence.public-trust-basis-inspection.2026-07-17` | challenges | 公開高信頼級を根拠機構へ条件拘束しない契約。利用者の実際の誤用までは示さない |
| `effect.action-occurrence.historical-review.refutes` | `verification.or02.action-occurrence-and-procedure` | `evidence.full-evaluation.2026-07-11` | refutes | 当時の行為・主体・権限・独立観測能力を反証する。現対象には stale / unbound |
| `effect.artifact-authenticity.historical-review.refutes` | `verification.or02.artifact-provenance-authenticity` | `evidence.full-evaluation.2026-07-11` | refutes | 当時の原証拠照合・真正性・来歴能力を反証する。現対象には stale / unbound |
| `effect.operational-reverification.integrated-record.challenges` | `verification.cross.operational-reverification` | `evidence.integrated-verification.2026-07-16` | challenges | 長時間・並行・負荷・DoS・複数 OS 証拠を未検証と明記。全再資格欠落の列挙ではない |
| `effect.legacy-characterization.known-failures.challenges` | `conformance.migration.legacy-characterization` | `evidence.integrated-verification.2026-07-16` | challenges | 既知二失敗は完全成功解釈を崩すが、v1 適合失敗を意味しない |

## 未解決と判断境界

| 未解決 ID | 種別 | 監査命題への効果 | 分離した解消責務 |
| --- | --- | --- | --- |
| `unresolved.lifecycle-surface-vertical-slices` | known_gap | blocks_claim | human: 現 OR-01 九工程面 profile の意味・範囲受理、分母変更なら版付き原点改訂、agent: 現分母の契約・縦断・適合試験、external: 横断欠落・分母改訂来歴の独立査読 |
| `unresolved.repair-loop-implementation-and-effect` | known_gap | blocks_claim | human: 修正効果・回帰・移譲方針、agent: finding→修正→再監査、external: 独立前後比較・回帰・移譲評価 |
| `unresolved.engineering-rule-pack-governance` | pending_decision | partially_blocks_claim | agent: rule pack・対応表、external: 独立工学査読、human: 採用・例外・再審査判断 |
| `unresolved.field-population-and-thresholds` | value_judgment | blocks_claim | human: 用途・危険費用・閾値、agent: 標本・測定設計、external: 独立標識・裁定 |
| `unresolved.action-evidence-and-authenticity-mechanism` | pending_decision | blocks_claim | human: 信頼・脅威模型、agent: 観測・来歴機構、external: profile 別独立・敵対検証 |
| `unresolved.secure-information-handling-and-external-boundaries` | value_judgment | blocks_claim | human: 採用 profile 又は閉じた非適用境界・再評価条件、agent: 採用時の情報流・制御・敵対試験、非適用時の対象・構成・経路閉包観測、external: 採用時の独立安全査読 |
| `unresolved.assurance-profile-and-public-trust-basis` | pending_decision | blocks_claim | human: 保証強度・独立性・信頼根・降格方針、agent: profile registry と公開根拠契約、external: 独立・敵対査読 |
| `unresolved.evidence-expiry-and-requalification` | time_dependent | partially_blocks_claim | human: 配備・失効・rollback 方針、agent: 対象 manifest・変更影響・再資格手順 |
| `unresolved.state-evidence-derivation-and-subject-binding` | evidence_gap | partially_blocks_claim | agent: 既存の支持・反証・疑義・文脈作用を消費する軸別評価記録、命題別 raw locator、対象 manifest、型付き経路選択・完了評価記録。作用と locator 閉包、経路構造は実装済みだが、起動条件の到達可能性・排他性・網羅性・選択・完了は未機械化。external: profile が要する独立観測 |
| `unresolved.proof-obligation-and-assurance-graph-soundness` | known_gap | blocks_claim | agent: v0 cross-field 閉包と opt-in v1 proof graph、external: subject・authority・evidence・集約 bypass の独立敵対査読、human: 保証強度・v1 default・v0 support/retirement・downgrade 方針 |
| `unresolved.verification-register-completeness` | known_gap | blocks_claim | agent: 分母・disposition・負 omission 検査、external: 分母・非適用・handoff の独立査読、human: 有界完全性・分母・非適用方針の採用 |
| `unresolved.lifecycle-trace-and-composition` | known_gap | blocks_claim | human: 工程間意味・許容変換・権限境界、agent: typed trace・split/merge/revision/cancellation/supersession/repair 合成、external: 全工程 omission・意味置換査読 |
| `unresolved.operational-qualification` | known_gap | blocks_claim | human: 配備・負荷・障害・回復 envelope、agent: 対象拘束した長時間・並行・負荷・枯渇・障害・回復・互換・platform 資格実行、external: 独立運用境界査読 |
| `unresolved.transition-cutover-rollback-and-retirement` | known_gap | blocks_claim | agent: compatibility・migration・abort・rollback・disposal・retirement 計画、external: shadow/migration/rollback/recovery rehearsal、human: field・運用・利用・register 証拠に基づく cutover 判断 |
| `unresolved.human-operational-use` | known_gap | blocks_claim | human: coding agent／人間の責任・判断権・escalation 方針、agent: 責任適合 material・routing、external: routing・理解・修正・escalation・権限誤りの task 評価 |
| `unresolved.analyzer-route-effectiveness-and-incremental-value` | known_gap | partially_blocks_claim | agent: 共通 protocol、形態素 ablation、係り受け／照応精度、lifting 拡張、LLM 増分価値、external: 同一 holdout・独立標識・authority ceiling の route 横断査読 |
| `unresolved.projection-value-equivalence` | evidence_gap | does_not_block_claim | agent: 投影の全値自動生成又は値級完全一致。現検証器は digest・時点・受理標識・識別子被覆まで |

正本では、全 17 verification item と全 27 implementation conformance item が、少なくとも一つの実在 unresolved family の `affected_entity_refs` に直接含まれる。これは各 gap-bearing 欄を canonical unresolved へ登録するための coverage であり、項目の実装状態を引き下げたり、未解決を解消したりするものではない。

### 型付き解消経路

`resolution_paths` が経路構造の機械上の正本であり、`resolution_summary` は非規範の可読要約である。現版の `activation_condition` は人間可読文字列で、検証器は到達可能性、排他性、網羅性、選択又は完了を判定しない。従って、経路文字列を書いただけで未解決は閉じない。将来は人間判断又は位置付けた観測に拘束した型付き選択・完了評価記録を要する。選択後は経路に列挙した責務とその同一未解決内前提を全て満たす。

| 経路 ID | 起動条件 | 必要責務 ID | 完了の要点 |
| --- | --- | --- | --- |
| `resolution-path.lifecycle-surfaces.current-or-revised-denominator` | 現 OR-01 分母。変更時は版付き人間承認原点改訂後 | `obligation.lifecycle-surfaces.human-profile-acceptance`<br>`obligation.lifecycle-surfaces.implement-vertical-slices`<br>`obligation.lifecycle-surfaces.independent-review` | 残存全工程面の profile・契約・縦断・証拠・独立査読を閉じる |
| `resolution-path.repair-loop.full-cycle` | OR-03 修正効果を主張する時 | `obligation.repair-loop.human-outcome-policy`<br>`obligation.repair-loop.implement-and-reaudit`<br>`obligation.repair-loop.independent-effect-review` | 人間方針、修正・再監査実装、独立前後評価 |
| `resolution-path.engineering-rule-pack.governed-and-reviewed` | 工学基準を audit profile へ採用する時 | `obligation.rule-pack.construct-mappings`<br>`obligation.rule-pack.independent-review`<br>`obligation.rule-pack.human-adoption` | 対応表、独立解釈査読、人間採用を全て要求 |
| `resolution-path.field-validation.accepted-and-independently-labeled` | 実務妥当性又は実用準備を主張する時 | `obligation.field-policy.human-risk-choice`<br>`obligation.field-policy.evaluation-protocol`<br>`obligation.field-policy.independent-labels`<br>`obligation.field-policy.execute-evaluation` | 工学基準採用・対象拘束・安全運用適用性・危険方針を前提に、評価設計、独立標識、実評価観測を閉じる |
| `resolution-path.action-assurance.implemented-and-challenged` | 行為・権限・来歴・真正性を立証する時 | `obligation.action-assurance.human-trust-model`<br>`obligation.action-assurance.implement-evidence-envelope`<br>`obligation.action-assurance.adversarial-review` | 信頼模型、観測機構、独立敵対証拠 |
| `resolution-path.secure-operation.adopted-profile` | 実・保護資料、外部 provider、特権又は永続運用を人間が選ぶ時 | `obligation.secure-operation.human-policy`<br>`obligation.secure-operation.implement-controls`<br>`obligation.secure-operation.independent-review` | 採用 profile の閉塞的制御と独立敵対査読 |
| `resolution-path.secure-operation.verified-nonapplicability` | 人間が閉じた synthetic/local/nonprivileged/nondurable 境界を選ぶ時 | `obligation.secure-operation.human-policy`<br>`obligation.secure-operation.verify-nonapplicability-boundary` | 宣言だけでなく対象・構成・経路観測と再起動試験 |
| `resolution-path.assurance-profile.accepted-implemented-challenged` | 高信頼級又は保証 profile を使う前 | `obligation.assurance-profile.human-policy`<br>`obligation.assurance-profile.public-contract`<br>`obligation.assurance-profile.independent-challenge` | 人間方針、fail-closed 契約、独立査読 |
| `resolution-path.requalification.policy-and-runbook` | 証拠を歴史的一回観測より長く再利用する時 | `obligation.requalification.human-validity-policy`<br>`obligation.requalification.implement-runbook` | 有効期間方針と変更→失効・再資格手順 |
| `resolution-path.state-derivation.profile-without-independence` | 受理 profile が独立観測不要と明記する時 | `obligation.state-derivation.implement-assessment-record` | 型付き作用を消費する軸別導出記録と対象拘束 |
| `resolution-path.state-derivation.profile-with-independence` | 受理 profile が独立観測を要求する時 | `obligation.state-derivation.implement-assessment-record`<br>`obligation.state-derivation.independent-observation` | 軸別導出に独立性根拠付き観測を追加 |
| `resolution-path.proof-graph.implemented-reviewed-and-human-adopted` | 公開 claim を再生可能な導出として扱う前、又は v1 default / v0 retirement 前 | `obligation.proof-graph.implement-replayable-contract`<br>`obligation.proof-graph.independent-adversarial-review`<br>`obligation.proof-graph.human-migration-adoption` | 再集約・mutation/graph 閉包、独立 bypass 査読、人間の保証・移行採用を分離して全て閉じる |
| `resolution-path.register-completeness.implemented-reviewed-and-human-adopted` | 有界 register 完全性を進捗・完了・移行・受理材料へ使う前 | `obligation.register-completeness.implement-denominator-and-dispositions`<br>`obligation.register-completeness.independent-denominator-review`<br>`obligation.register-completeness.human-denominator-adoption` | exactly-one disposition と負 omission を実装し、分母を独立査読した後、人間が有界意味を採用する |
| `resolution-path.lifecycle-composition.accepted-implemented-and-reviewed` | 二工程以上の意味又は証拠を合成する全 claim | `obligation.lifecycle-composition.human-semantics`<br>`obligation.lifecycle-composition.implement-trace-and-rules`<br>`obligation.lifecycle-composition.independent-cross-stage-review` | 人間受理した工程間意味に対し typed 合成と敵対例を実装し、全工程 omission・過大強化を独立査読する |
| `resolution-path.operational-qualification.selected-profile` | 選択配備 profile の運用準備又は default-route 主張前 | `obligation.operational-qualification.human-envelope`<br>`obligation.operational-qualification.execute-bound-profile`<br>`obligation.operational-qualification.independent-review` | 人間が選んだ secure-use・配備 envelope を対象拘束して資格実行し、試験外へ一般化しない独立査読を得る |
| `resolution-path.transition.evidence-complete-human-decision` | default switch、旧版 retirement、不可逆 migration 又は disposal 前 | `obligation.transition.define-plan-and-prohibitions`<br>`obligation.transition.independent-rehearsal`<br>`obligation.transition.human-cutover-decision` | 移行禁止・rollback 計画、独立 rehearsal、field/運用/利用/register 証拠に基づく人間判断を閉じる。実行権限ではない |
| `resolution-path.human-use.policy-material-and-independent-evaluation` | coding-agent 修正、人間 escalation、accept/request_revision/defer に利用可能と主張する前 | `obligation.human-use.human-responsibility-policy`<br>`obligation.human-use.implement-responsibility-aware-material`<br>`obligation.human-use.independent-task-evaluation` | 人間の責任方針、role-aware material、routing・理解・修正・権限誤りの独立 task 証拠を閉じる |
| `resolution-path.analyzer-effectiveness.common-holdout-and-independent-review` | 解析 route の発見性能又は増分価値を認める前 | `obligation.analyzer-effectiveness.define-route-protocol`<br>`obligation.analyzer-effectiveness.measure-morphology-ablation`<br>`obligation.analyzer-effectiveness.measure-dependency-coreference`<br>`obligation.analyzer-effectiveness.measure-lifting-expansion`<br>`obligation.analyzer-effectiveness.measure-llm-incremental-value`<br>`obligation.analyzer-effectiveness.independent-route-review` | 同一の統治済み対象拘束 holdout 上で四 route gap を別々に測定し、重大誤満足・棄権・authority ceiling を保った独立査読を得る |
| `resolution-path.projection.generated-or-value-compared` | Markdown 投影を正本の可読表示として出す時 | `obligation.projection.generate-or-compare` | 決定論的生成又は全状態・証拠セル比較 |

`blocks_claim` は対象項目の `satisfied` を、`blocks_claim / partially_blocks_claim` は `terminal satisfied` を許さない。反証命題、被覆、対象拘束が閉じた `terminal refuted` まで妨げない。ビューを対象にした場合も構成項目へ展開して検査する。解消責務は安定した `obligation_id`、権限級の根拠、前提責務参照を持ち、型付き解消経路は分岐の起動条件、必要責務、完了証拠条件を持つ。循環、参照切れ、同一経路内の前提落ち、全経路から漏れた責務を内部検証器が拒む。これは優先順位や作業割当ではなく、意味上どの決定又は証拠が先に要るかの関係だけを表す。

`semantic-guard` はこれらを監査材料として露出できるが、優先度、委譲、実行、危険受容を決めない。管制は外部呼出側又は `resource-control-plane`、最終 `accept / request_revision / defer` は人間が所有する。

現時点の `human_acceptance` は `pending` である。
