# 修復効果・人間実務利用の評価契約

記録日: 2026-07-16
状態: 独立した内部契約。実参加者、真正な同意、外部人間判断及び実業務結果は未取得

## 目的

operational-outcome-evaluation/v1 は、局所再監査の通過や技術的な出力整合から、次の二つを誤推定しないための評価契約である。v1は、v0査読で判明した権限洗浄、比較群（arm）と評価材料の束縛不足、参加者分母の欠落及び観測単位の擬似反復を塞ぐ破壊変更である。

- repair_effect: 指摘後の修復が正しく、回帰や所見抑圧を起こさず、必要な移譲と未解決保持を行えたか。
- human_operational_use: coding agent 又は人間が、材料を正しい責任層で理解し、根拠と限界を失わず、権限を越えずに利用できたか。

二軸は同じ評価束に収録できるが、課題、採点、評価量、閾値、結果digest及び残余危険を別々に持つ。一方の結果から他方を成立させない。

この契約は、参加者の割当、作業の配送、修復実行、権限付与、質問送信、方針採択、切替又は最終受理を行わない。semantic-guardの役割は、申告された記録を決定論的に計算し、閉鎖的に検査し、監査材料を返すことだけである。

## 原点要求との対応

| 原点 | この契約が扱うもの | この契約だけでは扱わないもの |
| --- | --- | --- |
| OR-01 | 工程資料の命題、根拠、限界、未解決及び責任層が実利用で保持されたか | 工学規則そのものの採択妥当性、工程全体の完全性 |
| OR-02 | coding agent の修復、移譲、権限誤り及び観測記録を限定された課題上で比較する | actor本人性、外部行為発生、時刻、因果性の真正な証明 |
| OR-03 | 所見が正しい修復又は人間判断材料へ結び付いたかを基線と候補で比較する | 修復実行の指揮、危険受容、組織判断、最終受理 |

## 契約の構成

一つの束は次を持つ。

1. 人間所有の版付き評価方針。
2. 方針の外部人間判断記録。
3. 採択判断digestへ結ばれた封印済み不変課題集合。
4. 事前封印された登録・比較群割当manifest。
5. 仮名化参加者、同意参照、依存cluster、最終処置及びsession。
6. baseline と candidate の全課題観測。
7. 二つ以上の独立集団による盲検採点。
8. 不同意と別集団による裁定。
9. 二軸別の保守的評価量、脱落率、通過根拠、限界及び結果digest。
10. field validity、運用適格性、安全性、切替及び最終受理を推定しない境界。

schema_versionはoperational-outcome-evaluation/v1、schema正本はschemas/operational-outcome-evaluation.schema.jsonである。最上位欄はpolicy、human_decision_records、task_set、enrollment_manifest、tasks、participants、sessions、observations、graders、scores、adjudications、axis_results、non_inference_axes、authority_boundary、limitations及びbundle_digestである。各objectはadditionalProperties=false相当の閉鎖欄を持つ。

方針、母集団、課題、課題集合、登録manifest、参加者登録、参加者最終記録、session、観測、採点、裁定、軸結果及び束にはSHA-256 digestを持たせる。validatorは各入力欄から対応するdigest、参照投影及びaxis_resultsを再計算し、保存値と完全一致する場合だけ検証済みのPython mapping複製を出力する。評価IDはevaluation_idを除く最上位入力欄から導出する。

失敗時はOperationalOutcomeValidationErrorを送出する。errorsはcode、location、messageを持つ辞書のtuple、codesはcodeだけのtupleである。例外は診断記録であり、修復命令、採否又は次行動を含まない。全時刻欄は時区付きISO 8601であり、申告記録、計算結果、未評価軸及び外部人間判断待ちを別欄に置く。

## 人間所有の評価方針

方針状態は pending、adopted、retired の三つである。semantic-guard自身は状態を選ばない。

adopted又はretiredには、方針ID、版、digestへ一致する外部人間判断記録が必要である。adoptedの記録時刻は課題集合封印より厳密に前でなければならず、同時刻を先行証拠として扱わない。課題集合は採択判断ID及び判断digestを引用する。結果を見てから費用、閾値、標本条件又は判断対象を差し替えることを防ぐためである。

同じ方針ID、版、digestを対象とする全判断を時刻順に解決し、最新の一件だけを現在状態の根拠にする。採択後のretireは先の採択を失効させる。同一時刻に複数の対象判断がある場合は順序を推測せず、policy_decision_conflictとして閉鎖的に失敗する。

方針は少なくとも次を固定する。

- 対象母集団、標本枠、分析単位、包含及び除外条件。
- 用途と運用文脈。
- coding agent、人間査読者等の対象役割。
- 軸別の必須課題層。
- baseline及びcandidateの版・digest。
- 各評価量の最大誤り率、最小成功率及び誤り費用。
- 費用加重損失、最低改善量、時間及び労力の上限。
- 軸・比較群ごとの最低観測数、相異なる参加者数及び相異なる依存cluster数。
- 必須層ごとの相異なる参加者数。
- 比較群ごとの最大脱落率。
- 信頼水準。
- 仮名化、同意範囲、用途制限、保持及び撤回処理。
- 評価停止条件。

方針に宣言した全roleは、少なくとも一つの課題のtarget_role_idとして被覆しなければならない。課題に現れないroleを方針分母へ追加し、そのroleを評価せずに肯定結果を得ることはできない。ただしv1はaxis×roleの適用表を持たないため、「各roleがどの軸で必須か」までは表現しない。複数軸へ跨るrole適用性を主張する場合は、次版で必須cellを方針に固定する必要がある。

費用と閾値は人間が採択する。semantic-guardは、その選択が適切かを決めず、選択された値に対する結果だけを計算する。

## 不変課題集合と二群比較

各課題は次を持つ。

- 課題ID及び内容digest。
- repair_effect又はhuman_operational_useの軸。
- 対象役割及び必須層。
- 正解参照及びrubric参照の版・digest。
- baseline材料及びcandidate材料の版・digestと、それぞれが導出された方針上の比較群参照。
- 全ての人間専有判断を含む禁止集合。部分集合は許さない。
- 必要な移譲の有無。
- 未解決を保持すべきか。
- 修復課題では、所見抑圧、規則弱化及び検証迂回の禁止。
- 封印時刻。

方針上のbaselineとcandidateは異なるdigestを持ち、各課題の二材料も異なるdigestを持つ。各課題材料の`derived_from_arm_ref`は、方針の`arm_contract`にある該当比較群の参照へ完全一致しなければならない。両群は同じ課題IDと課題digestを、一課題当たり同じ観測数で扱う。一方の群だけの欠測、別課題、別rubric、別正解、派生元となる比較群参照の不一致又は同一材料への差替えは比較として受理しない。

同じ参加者又は同じ依存clusterを両群へ使わず、封印課題への事前接触又は学習・調整への利用を拒否する。これは比較中の学習混入を避けるためのv1制約であり、交差試験を永久に禁止する主張ではない。交差設計を採るなら、順序効果とwashoutを扱う別の版付き方針が要る。

## 登録分母、参加者、session及び観測

enrollment_manifestは課題集合封印より厳密に後、かつ最初のsessionより厳密に前に封印し、方針digest、課題集合digest及び全登録者を固定する。各登録参照は参加者ID、登録digest、役割、比較群及び依存clusterを持つ。評価束のparticipantsはmanifestと全域一致し、後から参加者を追加又は削除できない。

参加者IDは participant-pseudo で始まる仮名だけを受理し、raw_identifiers_presentは偽でなければならない。各参加者は次へ拘束される。

- 方針上の役割。
- 対象母集団。
- baseline又はcandidateの一方。
- 同一比較群内の依存単位を示すcluster ID。
- operational_participant、synthetic、local_fixture又はsmokeの出所種別。
- 同意状態、同意証拠参照、同意範囲参照及び記録時刻。
- 登録時刻と登録digest。
- completed、withdrawn、protocol_violation、missing又はexcludedの最終処置、理由、証拠参照及び記録時刻。

completed参加者には一つのsessionと一件以上の観測が必要である。未完了参加者の観測を解析集合へ残さない。ただし参加者記録そのものは削除せず、比較群・軸別の登録数、完了数、脱落数、処置別件数及びWilson脱落率へ残す。これにより、悪い結果を持つ参加者を単に束から落として分母を縮めることを拒否する。

sessionは方針digest、課題集合digest、参加者digest、役割、比較群及び時刻を持つ。同意記録及び登録manifest封印はsession開始より厳密に前でなければならず、同時刻を先行証拠として扱わない。

各観測は、session、参加者、役割、比較群、課題、提示材料、応答又は修復成果物、時刻、時間及び労力へ結び付く。修復観測と人間利用観測は形を分ける。

- repair_effectは修復成果物参照、再監査等の修復検証参照、回帰状態、禁止shortcut及び未解決保持を持つ。
- human_operational_useは応答参照、配送先、移譲選択、決定主張、権限主張及び未解決保持を持つ。

escalation_chosenが真ならrouting_destinationはno_actionであってはならない。これは「移譲を選んだが配送先無し」という内部矛盾を拒否する最低条件である。v1の課題は期待配送先集合を固定しないため、指定された配送先が組織上正しいかは外部方針及び採点に依存する。

effort.elapsed_secondsはactive timeの自己申告ではなく、観測started_atからcompleted_atまでの壁時計秒数として扱い、区間差へ厳密一致させる。中断を除いた能動時間を測る場合は、別欄、取得方法及び許容差を持つ新しい版が要る。

参加者自己申告は保存できるが、採点には使わない。修復成果物が変化したという自己申告だけではcorrect_repairにならず、別の修復検証参照を要する。修復検証参照は相互にID及びdigestが異なり、修復成果物参照又は自己申告note参照と同じID若しくはdigestを再利用してはならない。ただし参照の主体、検証方法、実行時刻及び成果物からの実質的独立性は現schemaだけでは証明しない。

## 軸別の採点対象

repair_effectは次を別々に採点する。

| 評価量 | 意味 |
| --- | --- |
| correct_repair | 正解及びrubricに照らして修復自体が正しい |
| regression_free | 宣言された回帰検査が通過した |
| finding_integrity_preserved | 所見抑圧、規則弱化又は検証迂回で警告を消していない |
| correct_escalation | 必要な人間又は外部責任層へ正しく移譲した |
| unresolved_preserved | 未解決義務を成功扱いで消していない |
| responsibility_boundary_preserved | 意図変更、危険受容、権限付与、外部作用又は最終受理を修復工程で越権しなかった |

human_operational_useは次を別々に採点する。

| 評価量 | 意味 |
| --- | --- |
| correct_routing | 材料を正しい責任層へ向けた |
| proposition_understood | 監査対象命題を正しく理解した |
| evidence_understood | 根拠が支持する範囲を理解した |
| limitations_understood | 証明されない範囲と制約を理解した |
| unresolved_understood | 未解決義務を保持した |
| actionable | 許された次行動へ利用できた |
| correct_escalation | 自分で決められない命題を正しく移譲した |
| authority_safe | 意図変更、危険受容、権限付与、外部作用又は最終受理を越権しなかった |
| technical_pass_not_converted_to_acceptance | 技術通過を最終受理へ変換しなかった |

correct_repairが高くてもhuman_operational_useを成立させず、その逆も行わない。ただし人間専有判断の禁止は両軸に共通する不変条件である。権限違反を成功採点で隠した束は拒否し、失敗採点で開示された違反は各軸の誤り率及び費用へ残す。

## 独立採点と裁定

各観測には、実際に二つ以上の異なる独立集団が採点しなければならない。名簿に独立査読者が存在するだけでは足りない。

score_graderは次を満たす。

- 人間であると申告される。
- 対象artifactの作者、参加者又は運用者ではない。
- 比較群と参加者本人性に対して盲検である。
- 課題のrubric版・digestを使う。
- 軸に必要な全評価量を採点する。
- 参加者自己申告を採点根拠にしない。

同一独立集団の二人を二つの独立採点とは数えない。比較群に関する盲検が破れた採点も受理しない。

二採点が異なる場合、不同意を消さずに保存し、全基礎scoreを引用する別のadjudicatorが裁定する。adjudicatorも別の独立集団に属し、比較群及び参加者本人性に対して盲検でなければならない。裁定評価量は観測軸に属し、裁定時刻は全基礎scoreの記録以後でなければならない。不同意一件と裁定一件を一対一にし、不同意の無い評価量又は別軸評価量へ裁定を後付けすることも拒否する。

観測から機械的に分かる誤りを採点で隠せない。

- 禁止された権限主張をauthority_safeとする。
- accept主張をtechnical_pass_not_converted_to_acceptanceとする。
- 必要移譲を行わずcorrect_escalationとする。
- 未解決を消してunresolved関連評価を成功とする。
- 所見抑圧又は規則弱化をcorrect_repair又はfinding_integrity_preservedとする。
- 回帰失敗又は未検査をregression_freeとする。
- 修復検証参照なしでcorrect_repairとする。

これらは束検証そのものを失敗させる。実際の誤りを正しく失敗採点した束は拒否せず、誤り率と費用へ数える。

## 保守的な評価量

各二値評価量について、成功率と誤り率を両方保存する。v1の統計上の分析単位は観測件ではなくparticipant_clusterである。同じcluster内の一件でも評価量が失敗すれば、そのclusterを当該評価量の失敗とする。同一参加者の複数課題を独立標本として水増ししない。

- 誤り率はWilson上限を最大誤り率と比較する。
- 成功率はWilson下限を最小成功率と比較する。
- 点推定は併記するが、通過判定には使わない。

従って、小標本で観測誤りが0でもWilson上限が大きければ通過しない。観測成功が全件でもWilson下限が低ければ通過しない。

一観測の費用加重損失は、失敗した評価量の人間採択誤り費用を合算する。一cluster内では観測損失の最大値を採り、時間及び労力はcluster内観測平均を採る。軸ごとの最大損失は費用合計で有限に固定される。その上で、cluster間の平均費用、時間及び労力には二側Hoeffding限界を使う。clusterが比較群を跨ぐ束は拒否する。

候補の費用通過はcandidate上限と最大許容損失を比較する。基線からの改善は次の保守的下限を使う。

    baseline費用下限 - candidate費用上限

費用、時間及び労力についても点推定だけで通過させない。基線と候補は同一参加者を使わないため、結果欄名は`unpaired_arm_comparison`である。登録者の脱落率にはWilson上限を使い、baselineとcandidateを別々のcriterionとして同一の`max_dropout_rate`へ照合する。いずれか一群でも超えれば肯定結果にしない。評価結果は、観測値、閾値、比較方向、信頼水準、観測数、参加者数、cluster数、処置内訳及び比較根拠を分けて保存する。

Wilson又はHoeffdingの利用は、cluster間独立性、標本が母集団を代表すること、採点が正しいこと、参加者記録が真正であることを証明しない。cluster IDも申告記録である。独立性、母集団代表性、採点妥当性及び参加者記録の真正性には、外部評価設計と外部証拠が要る。

## 必須限界と資源上限

本人性、同意真正性、査読者本人性、実際の独立性及び盲検、時刻、外部成果物真正性をcontent digestだけでは証明できない、という限界は常に束へ含める。呼出側のlimitationsはこれを補足できるが、置換又は削除できない。

v1 schemaは文字列4096文字、方針role 256、課題層256、課題256、参加者2048、session 4096、観測65536、grader 128、score 262144、裁定65536及び人間判断64を上限とする。時刻文字列は64文字、判断参照は512文字とし、全配列にmaxItemsを置く。schema前走査は再帰及び全幅複製を使わず、深さ128、単一container 262144要素及び診断64件で停止する。未知欄内の巨大配列もschemaへ渡す前に拒否する。

数値はJSON互換の有限なint又はfloatだけを受理する。boolは数値欄ではschema違反となり、Decimal等の非JSON数値型は有限でもunsupported_number_type、Decimal NaN、float NaN及びInfinityはnon_finite_numberとして結果計算前に拒否する。これらは現在の内部入口をMCP又はCLIへ露出する際の最低防護であり、運用側の要求量制限を代替しない。

課題は両軸、観測は両軸×両群をschemaのcontains条件で最低一件ずつ要求する。builderも結果計算前に同じ空cellを検出するため、欠落標本をNoneへ変換して区間算術を継続せず、OperationalOutcomeValidationErrorで閉じる。

## 結果状態の読解

結果状態は意図的に弱くしてある。

| 状態 | 意味 |
| --- | --- |
| not_established | 方針未採択、保守的閾値不通過、最低標本不足、又は人工・局所記録である |
| meets_policy_for_declared_records | 供給された記録が採択方針と保守的閾値を満たした |

meets_policy_for_declared_recordsは、実母集団における効果成立を意味しない。claim_scopeはdeclared_records_onlyであり、本人性、真正な同意、独立性、盲検、時刻、成果物真正性、標本代表性及び因果性は外部証拠を要する。

synthetic、local_fixture又はsmokeは常にnot_establishedであり、claim_scopeはdeclared_synthetic_protocol_onlyとなる。肯定的な単体試験結果を実務効果へ一般化しない。

## 推定しないもの

二軸の結果にかかわらず、次はnot_evaluatedのままである。

- field_validity
- operational_qualification
- security
- cutover
- final_acceptance

また、repair_effectからhuman_operational_useを、human_operational_useからrepair_effectを推定しない。技術通過、方針通過又はmeets_policy_for_declared_recordsから人間受理を作らない。

## 純粋API

主なbuilderは次である。

- build_outcome_policy
- build_human_policy_decision
- build_outcome_task
- build_outcome_task_set
- build_participant
- build_enrollment_manifest
- build_outcome_session
- build_outcome_observation
- build_grader
- build_outcome_score
- build_outcome_adjudication
- build_operational_outcome_evaluation

build_operational_outcome_evaluationは、課題又は登録分母をその場で再生成しない。事前に封印されたtask_set及びenrollment_manifestそのものを受け取り、tasks及びparticipantsとの全域一致を再演する。

検査入口は次である。

- operational_outcome_errors: code、location、messageを持つ辞書tupleを返す。
- validate_operational_outcome_evaluation: schema、digest、参照閉包、重複、時系列、二群被覆、独立性、盲検、裁定、隠蔽、評価量及び保存結果を再演し、成功時は入力束のPython mapping複製を返す。失敗時は同じ辞書tupleを持つOperationalOutcomeValidationErrorを送出する。

公開command及びtool surfaceは存在しないため、標準出力、標準誤出力及び終了符号の契約も定義しない。参加者割当、作業配送、修復実行、質問送信又は判断入力の副作用を持つ入口も作っていない。

## 検証された敵対経路

- pending又はretired方針による効果成立。
- 採択後のretireによる失効、及び同時刻の相反・重複判断。
- 結果後の方針又は閾値差替え。
- 方針採択前の課題集合封印。
- 方針採択と課題集合封印の同時刻、又は採択判断digestの差替え。
- 課題集合と登録manifest、同意記録又は登録manifestとsession開始の同時刻化。
- 方針上のbaselineとcandidateの比較群参照又はdigestの同一化、同一task材料、派生元となる比較群参照の不一致又は課題別材料差替え。
- 方針roleだけを追加して課題・参加者・観測を持たせない分母縮小。
- 人間専有判断の禁止集合欠落、及びrepair軸からの権限洗浄。
- 一方の群の課題欠測又は別課題集合。
- 登録済みcompleted参加者の無観測化、未完了者の観測混入及び登録manifest差替え。
- baselineだけ又はcandidateだけで最大脱落率を超えること。
- 観測数を参加者数又は独立cluster数として数えること。
- 同一依存clusterの比較群跨ぎ。
- 学習又は事前接触の混入。
- 同意欠落又は同意範囲不一致。
- 作者又は参加者による自己採点。
- 同一独立集団の二人を二集団として数えること。
- 比較群に関する盲検又は参加者本人性盲検の破壊。
- 不同意の無裁定、別軸裁定、scoreより前の裁定及び裁定者本人性盲検の破壊。
- 自己申告だけの修復成功。
- 所見抑圧、規則弱化又は回帰失敗の隠蔽。
- 必要移譲、未解決保持又は権限誤りの隠蔽。
- escalation_chosenとrouting_destination=no_actionの同時申告。
- 技術通過からacceptへの変換。
- 修復成果物又は自己申告参照を修復検証参照として再利用すること。
- 観測区間とelapsed_secondsの不一致。
- 点推定だけなら通る小標本。
- 一軸又は軸×比較群cellを全削除した空標本による結果計算。
- fixture結果の実務一般化。
- 保存結果、課題、方針又は束digestの改変。
- 必須限界の置換、float又はDecimalの非有限数、非JSON数値型、深さ128超過、未知巨大配列及びschema資源上限超過。

## 現在の証拠状態

現時点で存在するのは、schema、純粋builder、validator及び人工単体試験だけである。次は取得していない。

- 実参加者。
- 実母集団からの標本。
- 外部人間による方針採択。
- 真正な同意及び仮名化運用の観測。
- 独立査読者の本人性、独立性及び実際の盲検。
- 実業務のbaseline及びcandidate成果。
- 外部台帳、署名、信頼時刻又は実artifactとの結合。
- 組織ごとの権限・配送・移譲方針の受理。

従って、現在の成果は「何を同じ条件で測り、どの誤推定を機械的に止めるか」という内部評価契約である。semantic-guardが実務で修復効果又は人間利用妥当性を持つという証明ではない。

## 検証命令

対象試験:

    uv run --locked python -m unittest tests.test_operational_outcomes -v

schema及び構文:

    uv run --locked python -m py_compile src/semantic_guard/operational_outcomes.py tests/test_operational_outcomes.py

全体試験は共有作業木の並行変更を含むため、対象試験と分けて結果を記録する。
