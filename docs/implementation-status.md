# semantic-guard 1.1.0 実装状態

更新日: 2026-08-24
判定: 要求関係監査に加え、独立した方向拘束監査の閉契約、CLI、MCP、Schema及び回帰試験を実装し、GitHub mainのmerge commit `a77c3cbdc69295572e90333e2a6e9da690fbbb6d`へ統合済みである。PR枝とmerge後mainのhosted CI四jobは成功した。1.1.0の選択したwheel/sdistの配布契約とfresh wheel上の実Sudachi 222組も局所検証済みである。人間受理、実務妥当性、公開索引配布及び外部配備は未成立である。

この文書の `1.1.0` は merge commit `a77c3cbdc69295572e90333e2a6e9da690fbbb6d` へ統合した源契約を指す。公開索引上の配布物、hosted artifactと局所wheelのbyte同一性又は運用既定化と同一視しない。policy、profile、各Schemaの `v1` / `v2` は各契約の意味版であり、package版へ一括置換しない。

## 歴史的 1.0.0 基線

1.0.0 の正本化判断では、要求関係監査の局所契約をrepository root、配布物、CLI及びMCPの正本へ昇格した。全工程の公開縦断統合、実地妥当性、外部真正性、人間採択、外部配備切替及び不可逆な旧版廃止は未完であった。

この正本化はリポジトリ、配布物、CLI、MCPの同一性判断である。後述する2026-07-16の試験値とwheel値は候補時点の歴史的観測であり、1.0.0へ束縛した新証拠ではない。

## 1.1.0 統合済み: 方向拘束監査の独立公開切片

`direction-binding public slice・245dad95-accf-581c-8b0a-ae1c1f557de4` は、`canonical current・11c55966-ff12-50b9-b069-7bec6ed37cc4` の現作業木へ選択統合した別 entity である。源には `semantic-guard-direction-binding-audit/v1`、CLI `audit-direction-binding`、MCP `audit_direction_binding_tool` 及び閉 Schema `direction-binding-audit` が存在する。既存 `audit-requirement`、`audit-result/v0` の欄構造、要求関係規則及び監査識別子の生成規則は変更しない。ただし producer package版は1.1.0へ上がるため、版を束縛する既存監査の具体的な識別子値まで不変とはしない。

監査の一次判断は、同一対象・同一操作について、方向を開く表現へ方向を限定する表現が直接付着しているかである。scalar の `decision-frame-summary/v3` と六軸 non-scalar の `direction-binding-summary/v1` は発行範囲を分け、形態素解析は `signal_only`、数値は任意の影響証拠に限る。方向選択、一般自然言語理解、実務妥当性及び人間受理はこの局所契約に含めない。

源泉は `local feature source snapshot・2b62dfa0-6d90-5c31-ae2d-34ec55c94895` から五ファイルだけを選択する `derived_from` とし、[source map](../migration/direction-binding-source-map-2026-08-23.json) に digest と移植先を固定した。`frozen legacy archive・3fd59352-b0d9-58f6-8279-9309c8960631` は当該 1.1.0 統合時点で変更せず、`candidate_ref: local vnext candidate・32646741-8cec-5fe3-b9f3-2971a8a787f0` は保留した。2026-08-24 の後続 publication repair は旧版 archive の文書、companion Skill 文面及び archive manifest だけを変更し、runtime code、schema、試験及び fixture は変更していない。源実装は[GitHub統合証拠](audits/direction-binding-integration-2026-08-23.md)のmerge commitへ統合済みであり、選択した1.1.0配布物及びfresh wheel上の実Sudachi 222組は局所で成立した。いずれも実務母集団の妥当性又は人間受理の証拠へは昇格させない。

## 原点要求との対応

| 原点 | 現在あるもの | まだ成立していないもの |
| --- | --- | --- |
| `OR-01` 工程横断の体系監査 | 構造化要求の実行経路、十工程の候補profile、工程間trace、体系知rule-pack候補、状態・対象拘束、未解決分母 | 十profileの人間採択、profileとtraceのresolver、各工程の公開縦断実装、体系知rule-packの独立査読・採択・runtime接続、実務発見性能 |
| `OR-02` AIエージェント行為の限定的立証 | proof obligation graph、v0/v1保証契約、行為の発生・主体・権限・手続・来歴・真正性・因果性を分けるaction-evidence契約 | 実行runtime観測、主体本人性、署名検証器、信頼時刻、外部台帳、実artifactとの照合、現場での限定立証証拠 |
| `OR-03` 修正と人間判断への接続 | 責任別材料、修復cycle、型付き変更後監査・回帰・効果遷移、人間利用と修復効果を分けた評価契約 | 実際のagent修復、実参加者、真正な同意、独立盲検評価、組織別routing、人間最終受理 |

原点は [origin-requirement.md](prototypes/origin-requirement.md) である。成果物数や試験数は原点達成の代用品ではない。

## 実装面

| 面 | 主な実体 | 現在の意味 |
| --- | --- | --- |
| 検証分母 | `validation/verification-source.json`, `verification-gap-register.json` | 17検証項目、17未解決群、52解消責務、19解消経路、65 gapを閉じた正本と台帳で保持する |
| 正本投影 | `verification_projection.py`, `verification-source.generated.md` | 全JSON nodeをJSON Pointer付きで決定論的に投影し、生成文字列の完全一致を検査する |
| route・未解決再評価 | `routing.py`, `provider_receipts.py`, `reassessment.py`, `engine.py` | 直接規則、未解決理由、解析能力、実行段階を版付きで記録し、限定された`performs` / `acts_on`だけを再評価する |
| 解析器境界 | `japanese_morphology.py`, `japanese_dependency.py`, `dependency_projection.py`, `llm_candidates.py` | 形態素は信号、係り受けとLLMは候補に限定する。能力欠落・部分被覆・未構成を成功へ洗浄しない |
| 保証契約 | `assurance_graph.py`, `assurance-claim-v1.schema.json`, `public_contract.py` | subject、命題、規則、証拠、状態をproof obligation graphへ結び、v0差替えとv1再演不一致を拒む |
| 状態・対象 | `subject-manifest.schema.json`, `evidence-validity-policy.schema.json`, `state-assessment.schema.json`, `state_assessment.py` | policy/assessment v2で非循環basis、人間判断の主体・外部記録拘束、証拠種別別claim ceiling、型付き効果を実装する。自由申告だけなら`asserted_input_unproved`として技術軸を上げない |
| 体系知統治 | `validation/engineering-rule-pack.candidate.json` | 11義務・11候補規則を5一次資料へ追跡する。全件candidate、runtime authorityは`none` |
| 十工程意味分母 | `lifecycle-profile-registry.candidate.json`, `lifecycle_profiles.py` | requestからcompletionまで十profileを候補契約化する。全件`pending_human_adoption` |
| 工程間意味保存 | `lifecycle-trace.schema.json`, `lifecycle_trace.py` | 主体、命題、義務、証拠、権限、未解決を十工程graphで保存し、差替え・欠落・越権を拒む |
| 行為証拠 | `action-assurance-profile.schema.json`, `action-evidence.schema.json`, `action_evidence.py` | action profile v1のbasisへ人間採択を結合し、七主張を別々に再演する。説明、tool request、自己申告だけから発生を導出しない |
| 修復循環 | `responsibility-policy.schema.json`, `repair-cycle.schema.json`, `repair_loop.py` | policy/cycle v2で責任方針basis、人間採択主体、型付き変更後監査・回帰結果、版付き効果遷移、対象拘束済み独立人間査読を閉じる |
| Field評価 | `field-evaluation.schema.json`, `field_evaluation.py` | 同一case集合でrouteを比較し、偽充足・偽反証・棄権はWilson限界、費用は明示された比較根拠で扱う。実holdoutは未実施 |
| 修復・人間利用効果 | `operational-outcome-evaluation.schema.json`, `operational_outcomes.py` | v1で権限不変条件、arm由来、封印task/enrollment分母、参加者・群単位、脱落、盲検裁定、Wilson/Hoeffdingを閉じる。肯定値も供給記録内に限定する |
| 安全運用 | `secure-operation.schema.json`, `secure_operation.py` | v1で最新採択/廃止、scope、流路、保持、削除、再起動、証拠種別、資源上限を検査する。外部安全性を表す正判定は設けず、内部整合状態と未立証claimを分ける |
| 運用資格・移行 | `operational-qualification.schema.json`, `transition-plan.schema.json` | 12運用場面、配備包絡、再資格、sidecarからretirementまでの門、中止・rollbackを契約化する。実運用試験や切替判断は未実施 |
| 方向拘束公開切片 | `direction_binding_audit.py`, `request_decision_frame.py`, `request_direction_binding.py`, `direction-binding-audit.schema.json` | 同一対象・同一操作への明示方向付着をscalar 14族・49軸・56尺度語とnon-scalar六軸で検査する。形態素は`signal_only`、数値は補助のみ、人間受理は外部に残す |
| 呼出面 | `cli.py`, `mcp_server.py`, `schema_access.py` | CLI四命令、MCP四工具、全24契約schema取得を源で実装する。1.1.0 wheel/sdistを構築し、選択wheelの隔離検証20件、方向CLI・Schema・`--fail-on`・MCP dispatchを再演済み。ライフサイクル、状態、行為、修復、評価及び運用のsidecar群を合成する実務workflowは未実装 |

## 層別準備度

| 層 | 現在地 | 判定 |
| --- | --- | --- |
| A. 局所構造・意味契約 | schema、digest再演、参照閉包、権限境界、敵対fixture | schema適合、digest再演、参照閉包及び敵対fixtureを局所規則の範囲で検査済み。ただし全て供給資料内の観測に限る |
| B. v1内部合成 | requirement route、proof graph、state、trace、action、repair、評価、運用契約を個別APIで利用可能 | 部分成立。共通workflowと失効伝播は未統合 |
| C. 公開CLI/MCP縦断 | requirement relation監査と独立direction-binding監査を統合済みGitHub源及び選択した1.1.0配布物から呼出可能 | 方向拘束切片のGitHub CI/mergeまで成立。十工程・action・repair・評価・運用sidecar接続は未成立 |
| D. 実務妥当性 | 評価protocolと閾値計算器が存在し、fresh wheel上の実Sudachi 222組を再演済み | 未成立。222組は登録語彙の接続と限定契約の証拠に過ぎず、実母集団、独立標識、実参加者及び実運用観測が無い |
| E. 外部真正性 | digestと型付き参照で内部差替えを検出 | 未成立。署名、本人性、信頼時刻、外部台帳、証拠保管庫を検証しない |
| F. 人間採択・既定切替 | 判断対象をbasis digestへ結ぶ契約が存在 | 人間判断記録の構造検査だけ成立。rule-pack、profile、評価方針、運用包絡、外部配備切替及びretirementは未採択 |

## 独立査読で見つけ、修正した誤通過

- 同じ人間判断を内容変更後のaction / validity / responsibility policyへ再利用できた。
- 同じ人間受理記録を相反するstate assessmentへ再利用できた。
- 局所試験を`validation=supported_in_context`へ申告だけで昇格できた。
- `before=unresolved / after=unresolved`でも`effect=resolved`と書けば修復全体を`improved`にできた。
- secure-operationで後発廃止、自己観測洗浄、public資料のsynthetic洗浄、再起動差替え、証拠種別差替え、保持証拠欠落を通せた。
- human-use評価で人間専有判断の禁止集合を削り、repair軸だけで受理権限を洗浄できた。
- 評価方針のbaseline/candidateとtask材料を無関係に差し替え、同一材料でも比較成立にできた。
- 同一参加者の反復を独立標本として数え、未観測参加者を分母から落とせた。
- 後発の方針廃止、baseline側の脱落超過、未評価role、移譲先`no_action`、修復成果物の自己検証及び観測時刻と経過秒の不一致を残したまま成果評価を肯定できた。
- 深過ぎる又は幅過大な入力、非JSON数値、一軸欠落から、閉鎖的な誤り記録ではなく生例外へ落とせた。
- wheel外の紛らわしい隣接`schemas/`又は`validation/`が、同梱契約を影差替えできた。

各反例はv1/v2契約又は敵対試験へ移し、局所通過から外した。配布物はpackage資源を先に解決し、source fallbackをsource layout identityへ拘束した。これらは、試験数より試験分母の完全性が重要であることを示す。

## 局所観測

### 1.1.0 局所統合観測

2026-08-23 の統合対象作業木では、敵対的査読で追加した引用範囲、未知尺度方向、入力役割、provider被覆、細粒度token分割及びCLI説明の回帰試験を含む unit test suite 608件が成立した。CPython 3.13 の局所環境では `Ran 608 tests in 44.866s`、隔離した CPython 3.11 環境では `Ran 608 tests in 46.528s` で、いずれも `OK` となった。時間値は当該実行の観測であり、性能保証ではない。

同日の局所buildでは、1.1.0 の wheel と sdist の構築に成功し、選択wheelの配布契約検証20件が全て通過した。検証器は `public_schemas=24`、`cli_commands=4`、`mcp_tools=4` を記録し、導入済み配布物からの方向CLI、Schema取得、`--fail-on`及びMCP dispatchも通過した。

fresh wheelへ`nlp-ja`を導入した隔離環境では、SudachiPy 0.6.11、SudachiDict-core 20260428、split mode Cを記録した。全56尺度語についてgap / high-pole bound / low-pole boundの168組、全18方向基底語についてgap / 二方向boundの54組、合計222組を公開監査と厳格source検証の双方へ通した。これは選択した局所artifactの登録語彙、配布契約及び解析器接続を示すが、公開索引上の配布物、hosted artifactとのbyte同一性、未登録表現、実務母集団又は人間受理の証拠ではない。

### 1.1.0 GitHub統合観測

[PR #3](https://github.com/morie-lene/criterion-loom/pull/3)は実装commit `c10ba59f8ab16659b50e9cbf13da07c9889ed195`をmainへmergeし、merge commitは`a77c3cbdc69295572e90333e2a6e9da690fbbb6d`となった。PR CI [run 32646627913](https://github.com/morie-lene/criterion-loom/actions/runs/32646627913)と、当該merge SHAをsubjectにしたmain push CI [run 32646816407](https://github.com/morie-lene/criterion-loom/actions/runs/32646816407)は、いずれもPython 3.11、Python 3.13、凍結0.1.0煙試験、wheel及び導入済み公開面の四jobを成功させた。これはGitHub源統合と定義済みhosted CIの証拠であり、実務妥当性又は人間受理ではない。時刻、job URL、局所補助証拠及び非推論境界は[日付付き統合証拠](audits/direction-binding-integration-2026-08-23.md)に分離した。

### 1.0.0 歴史観測

2026-07-16 16:08 JST時点の再実行では、単体・契約試験569件、JSON 35ファイルの重複鍵検査、Draft 2020-12 schema 27件の自己検査、`compileall`、Ruff、lock検査、検証正本の六検査、工学規則台帳の三検査が通過した。運用成果評価は対象54試験に加え、別agentによる正常2・既出反例25の再現行列で27件全て期待結果となった。

構築wheel `f4289463...cf938` は隔離仮想環境で、隣接する偽schema・候補台帳を無視し、公開schema 23件、MCP schema資源23件、CLI schema名23件、lifecycle profile 10件、工学候補規則11件及び実console入口を再演した。実Sudachiは三能力を`ok`、実GiNZAは照応候補欠落を`partial`、LLM未構成を`not_configured`とし、既定assuranceは`block`した。

詳細は [`local-contract-verification-2026-07-16.json`](../validation/local-contract-verification-2026-07-16.json) に固定した。ただし全作業木・runtime・依存・raw logを閉世界manifestへ拘束していないため、この観測自身の鮮度は`unbound`である。従って正本状態を`current`や人間受理へ自動昇格していない。

## 未成立の証拠・統合項目

1. **規範採択** — rule-packと十工程profileを領域専門家と人間所有者が査読・採択する。
2. **縦断統合** — lifecycle profile resolver、profile適合adapter、state/action/repair/assessmentの失効伝播、CLI/MCP入口を実装する。
3. **実務資料評価** — 対象母集団、重大誤満足費用、閾値、独立二重標識、holdout、ablationを人間方針へ結んで実行する。
4. **行為・真正性連携** — runtime event、主体・権限snapshot、署名検証、信頼時刻、外部台帳、artifact provenanceを取得する。
5. **人間利用評価** — 実参加者、真正な同意、独立盲検採点、脱落を含む実務studyを実行する。
6. **運用資格** — 実配備で長時間、並行、負荷、枯渇、provider障害、restart、recovery、互換、事故を測る。
7. **外部移行判断** — 外部配備は shadow、opt-in、rollback rehearsal、証拠移行を経て、人間がdefault化又はretirementを別々に判断する。

## 現段階で許される主張

- 版付き限定規則で構造化機能要求の関係義務を監査できる。
- 版付き限定規則で、登録済みscalar/non-scalar方向表現の直接拘束を独立契約として監査できる源実装がある。
- 選択した1.1.0のwheel/sdistを構築でき、そのwheelで24 Schema、四CLI命令、四MCP工具を含む配布契約検証20件が通過した。
- fresh wheel上の指定Sudachi版・辞書版・split modeで、登録済み56尺度語と18方向基底語のgap及び両方向bound、合計222組を再演できた。
- 方向拘束公開切片はGitHub mainのmerge commit `a77c3cbdc69295572e90333e2a6e9da690fbbb6d`へ統合され、PR枝とmerge後mainの定義済みCI四jobが成功した。
- 未解決理由、解析能力、候補由来、証拠効果、権限境界を再演可能な内部記録へ残せる。
- 行為、状態、修復、評価、運用について、過大な成功主張を拒む候補契約と敵対試験が存在する。
- 正本の全値投影driftを機械検出できる。

次はまだ主張してはならない。

- 自然言語要求を一般に正しく理解する。
- 任意の開発工程を体系知に照らして十分な精度で監査する。
- AIエージェントの行為発生、本人性、真正性又は因果性を実証した。
- 実務母集団で修復効果又は人間利用価値が成立した。
- 公開索引上の1.1.0配布物、release/tag、hosted artifactと局所wheelのbyte同一性又はmainと異なる任意buildが検証済みである。
- 実Sudachi 222組から、未登録表現、実務母集団の妥当性、一般自然言語理解又は運用資格が成立した。
- `pass`、局所試験、内部整合又はdigest一致が人間受理を意味する。
- 一つの運用環境の構成記録だけを根拠に、別の運用環境の既定CLI/MCP経路へ切替えてよい。

運用詳細は [operations.md](operations.md)、正本化判断は [canonical-promotion-decision.md](canonical-promotion-decision.md)、移行は [migration-v0.1.0-to-v1.0.0.md](migration-v0.1.0-to-v1.0.0.md)、検証状態の正本は [verification-source.json](../validation/verification-source.json) を参照する。日付付きの [影響度と実行順](impact-and-execution-order-2026-07-16.md) は候補時点の歴史資料として保持する。
