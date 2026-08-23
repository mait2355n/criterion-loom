# semantic-guard 1.1.0 運用手引

## 要求関係入力契約

最初の縦断実装は、一件の構造化機能要求を対象にする。次の七欄を一行ずつ `label: value` で与える。

- `Purpose` / `目的`
- `User` / `利用者` / `主体`
- `Scenario` / `シナリオ` / `利用場面` / `場面`
- `Expected result` / `期待結果`
- `Acceptance criteria` / `受入基準`
- `Verification method` / `検証方法`
- `Evidence` / `証拠`

未標識行、重複欄、複数記録、空欄は閉じた記録として扱わない。これは融通の欠如ではなく、自由文から「欠落」や「満足」を断定しないための境界である。

CLI と MCP が一回に受け取る要求本文は UTF-8 で 262,144 bytes 以下とする。この縦断実装は一件の構造化要求を対象にしており、文書束を一要求に偽装して投入してはならない。上限超過は解析前に拒否する。

## 方向拘束入力契約

`audit-direction-binding` / `audit_direction_binding_tool` は要求関係監査から独立し、一件の方向を開く表現と、それへ直接付着する現在の方向限定条件だけを対象にする。CLI は `--text`、UTF-8 `--file` 又は標準入力を受け、任意の `--context` を一改行の後へ結合する。MCP は `text` と任意の `context` を受ける。結合後の入力は同じ 262,144 bytes 上限と SHA-256 拘束を持つ。ただし主操作のframeは`source_text`領域内に必要であり、`context`内だけの別質問や例を主発行器にしない。

```sh
uv run --locked semantic-guard audit-direction-binding \
  --text '体重が重い順に並べたとき、Cの次に体重が重い人は誰か。' \
  --context '候補集合は現在の表だけを使う。' \
  --morphology sudachi
uv run --locked semantic-guard schema direction-binding-audit
```

形態素解析は `signal_only` で、数値投影は補助証拠に限る。`morphology=none`、部分被覆、失敗又は契約不整合を方向拘束の成立へ洗浄しない。方向監査は `semantic-guard-direction-binding-audit/v1` を返し、既存 `audit-result/v0` へ字段を追加しない。

## Wheel 配布契約の隔離検証

正本repository rootを作業directoryとし、信頼済みの局所作業木から wheel を一個だけ構築して、隔離仮想環境へ導入した配布実体を検証する。検証器は隣接する偽 `schemas/` と `validation/` を置いた上で、包内24 schema、CLI四命令、MCP四工具、生活周期候補10件、工学規則候補11件とそのschema、空objectを拒む運用成果schemaを再演する。

```sh
uv build --out-dir dist .
uv run --locked python scripts/verify_packaged_contracts.py \
  --wheel dist/semantic_guard-1.1.0-*.whl \
  --sdist dist/semantic_guard-1.1.0.tar.gz \
  --timeout-seconds 180
```

`dist/` には対象 wheel 一個だけを置く。標準出力は機械可読 JSON 一個で、`status=pass` の時だけ終了符号 `0`、入力、導入、資源上限、経路又は契約検証の不成立は非零となる。検証器は外部の Python、監査program又は資源pathを引数で選ばせず、wheel量、展開量、全体時限、子過程CPU、出力量、生成file量及びfile descriptor数を制限する。Darwinでは有限 `RLIMIT_AS` を受理しないため、住所空間上限だけは適用せず結果の限界へ明記する。

これは未知の wheel を安全に実行する隔離器ではない。wheelのimport自体が符号実行なので、アナタが信頼する局所buildだけを対象にする。依存解決には二進配布物だけを許すが、索引、通信及びその時点の互換依存版には依存する。成功しても、同梱資源と局所契約の再演を示すだけで、実地妥当性、運用資格、外部真正性、保安認証又は人間受理にはならない。

2026-08-23 の局所統合観測では、1.1.0 の wheel と sdist を構築し、選択した wheel に対する隔離検証20件が全て通過した。検証結果は `public_schemas=24`、`cli_commands=4`、`mcp_tools=4` を記録し、導入済み配布物からの方向拘束 CLI、Schema 取得、`--fail-on` 及び MCP dispatchも通過した。これは当該局所buildの配布契約を再演した証拠であり、別build、公開索引上の配布物、GitHub上のcommit又は人間受理へ一般化しない。

同じ fresh wheel へ `nlp-ja` を導入した隔離環境では、SudachiPy 0.6.11、SudachiDict-core 20260428、split mode C を記録した。全56尺度語の gap / high-pole bound / low-pole bound 168組と、全18方向基底語の gap / 二方向bound 54組、合計222組を公開監査と厳格source検証の双方で再演した。この222組は package された登録語彙、方向拘束契約及び解析器接続の限定的な実行証拠であり、未登録表現、実務母集団の妥当性、運用資格又は外部真正性を示さない。

## 解析系列

```text
入力境界
  → 義務別直接仮判定
  → 独立残余危険門
  → 必要時のみ形態素解析
  → 依存構造候補
  → 版付き決定論的再検査
  → assurance/影経路で明示投入された LLM 候補（conditional は未解決時）
  → 義務別再集約
  → 判断要求材料
```

既定の `assurance` は直接規則が通っても形態素・依存構造解析を実効実行し、必須解析器が無い又は失敗した場合は `pass` にしない。`conditional` は独立残余危険門又は未解決義務がある場合だけ解析器を起動する最適化候補であり、実務資料による見逃し評価が終わるまでは明示選択の実験経路とする。

`shadow_all` では解析器を観測用に全件実行するが、その信号、競合、解釈を実効判定へ混入させない。影結果を採用するには、別の版付き規則と適合試験が要る。

## 終了符号と監査状態

CLI は、入力解釈と監査実行が完了した場合の機械可読 JSON だけを標準出力へ書く。利用法違反、UTF-8 復号、入力上限、候補束読込など監査開始前の診断は標準誤出力へ書き、終了符号 `2` とする。予期しない過程異常の非零終了を監査上の `block` と読み替えてはならず、有効な公開 JSON が無ければ監査観測自体が成立していない。

CLI の終了符号 `0` は JSON 生成と契約検証が成功したことを示す。監査結論は `workflow_disposition.status` を読む。`warn` や `block` を過程異常と混同してはならず、逆に終了符号 `0` を監査通過と見做してもならない。

自動処理で監査状態も終了符号へ写す場合は `--fail-on warn` 又は `--fail-on block` を明示する。閾値に達しても JSON は標準出力へ完結して出し、その後に終了符号 `3` を返す。旧版影比較を必須にする `--require-legacy` が失敗した場合は終了符号 `4` を優先する。既定 `--fail-on never` は従来どおり、終了符号と監査結論を分離する。従って `0 / 2 / 3 / 4` はそれぞれ、輸送・契約成功、利用法又は入力不成立、明示された監査状態閾値、必須旧版観測不成立を表す。

`pass` は「現行の版付き監査規則が止めていない」という射影でしかない。受理、差戻し、保留、延期、棄却は外部の人間判断に残る。

## 解析器障害

- `conditional` で必要になった解析器が未構成、失敗、部分被覆なら `pass` にはならない。
- `shadow_all` の未構成解析器は観測として残るが、実効判定を変えない。
- Sudachi と GiNZA は任意依存であり、導入していない環境では障害が明示される。
- 方向拘束監査では Sudachi だけを選択できる。未構成、部分被覆、失敗又は能力・split mode 不整合は `primary_rule_evaluation.state=indeterminate|invalid` として残り、形態素だけから方向を導出しない。
- `partial` な解析器出力は全てを成功扱いにも全てを廃棄にもせず、充足能力だけを候補専用経路で使う。係り受け投影は `dependency`、条件作用域の限定導出は `dependency` と `scope` の充足を要する。欠落能力がある実行は、候補を使えても完全被覆又は `pass` にはならない。
- GiNZA の生候補は `dependency:*` 名前空間に留める。そのうち主語、目的語、原文整列した条件作用域だけを、版付き規則で `performs`、`acts_on`、`triggered_by` の意味関係候補へ投影する。これは差分検知用候補であり支持ではない。

## LLM 候補束

主な起動元は符号化エージェントなので、特定の外部模型 API を監査器内部へ固定しない。呼出元は `semantic-guard-llm-candidates/v0` の閉じた JSON 束を生成し、CLI では `--llm-candidates FILE`、MCP では `llm_candidate_bundle` として渡す。

束には原文 SHA-256、模型識別子と版、指示規約識別子と版、候補ごとの関係種別、始終範囲、解釈識別子、根拠を必須とする。原文 digest 不一致、不正範囲、未知欄は失敗観測となる。模型名は呼出元の来歴主張であって認証済み同一性ではない。LLM 束は常に `candidate_only` であり、支持、保留適用、保留解除は出来ない。明示束を渡した `assurance` では先行段階が仮通過していても候補束を観測する。LLM が返した反条件・作用域候補は版付き残余危険方針が保留材料へ写し、黙って捨てない。

```sh
uv run --locked semantic-guard schema llm-candidate-input
```

## 安全・責任ある運用候補

実資料を外部 LLM 又は解析器へ送る権限は、この監査系列の実装から生じない。`verification.cross.secure-and-responsible-operation` は、資料分類、同意又は権限、最小化、秘密・個人情報、外部送信、保持・削除、敵対入力、依存・模型・辞書の来歴、最小権限、資源枯渇、事故証拠と復旧を閉じた分母へ入れる候補基準である。`secure-operation/v1` の局所 sidecar は、供給された流路・範囲・保持・削除・採択/廃止・再起動・証拠種別・資源上限記録の内部整合だけを検査する。実署名、外部本人性、信頼時刻、外部台帳、実配備観測及び独立運用資格は無く、人間採択も未了なので、正本の状態軸を実装済み又は検証済みへ推測しない。保安走査器や適合認証を名乗るものではない。

人間が用途、資料、送信先、保持、権限、事故・残危険方針を採用する前に、呼出元は非公開資料を外部 provider へ送ってはならない。採用後も、外部呼出、作業実行、危険受容は呼出側又は管制面の責務であり、`semantic-guard` は不足と証拠を監査するだけである。

候補基準を採用しないだけでは、この未解決を消せない。解消は、採用した配備 profile に閉塞的制御と独立敵対証拠を備える枝か、実資料・保護情報、外部 provider、特権作用、永続運用を除外した版付きの非適用境界と再評価起動条件を人間が受理し、対象 manifest、構成、情報流、provider、権限、保存経路の位置付き観測で実際の非適用を示す枝のどちらかである。紙上の宣言だけでは後者にならない。境界を越えた時点で、実装・独立査読義務は再び有効になる。

## 検証正本と証拠更新

`validation/verification-source.json` は検証要求、証拠関係、独立状態軸、再検証条件、未決定の正本である。`verification-matrix.md` は人間向け投影、日付付き検証 JSON は実行時点の観測であり、三者を同じ物として更新しない。

更新順は次で固定する。

1. 原点要求、憲法、公開契約又は証拠対象が変わった場合、正本中の upstream 版又は digest を先に更新する。
2. 過去の日付付き観測を現状に合わせて書き換えない。再実行したなら新しい観測を追加し、取得方法、証拠ファイル digest、試験対象 locator と閉じた manifest 又は全対象 digest、環境、command 又は raw log locator、結果、限界を記録する。
3. 証拠観測を `evidence_observations` へ正規化し、証拠が命題又は状態軸へ及ぼす作用を `evidence_effects` に記録する。各作用は対象項目、証拠、`supports / refutes / challenges / contextualizes`、`claim_dimensions`、限定命題、宣言済み観測 locator、限界を持つ。`supports / contextualizes` は項目の `evidence_refs`、`refutes / challenges` は `counterevidence_refs` と集合を一致させる。`contextualizes` は命題形成の文脈であって実装・検証・妥当性・保証の支持ではない。部分面を `lifecycle_surfaces` で限定した支持も、親の全工程被覆を満たさない。`missing / failed / invalid / refuted_in_context` は同じ状態軸の負作用を必須とし、同軸の支持作用と併存するなら `challenge=conflict` を要する。負証拠が無い時は欠落を断定せず `not_assessed` に留める。反証・疑義は保証次元を必ず含める。試験名や予定だけを実行証拠にせず、同じ証拠ファイル内の別位置を観測位置の代用品にしない。
4. 実装、検証、妥当性確認、限定的保証、鮮度、人間受理を各々更新する。一軸の成功から他軸を推測しない。
5. `terminal` は現対象へ拘束した `current` 証拠、閉じた被覆、未解決 challenge なしを要する。`refuted` 又は `challenge=open/conflict` は位置付けた型付き作用を必須とし、`refuted` には少なくとも一つの `refutes` を要する。`challenges` は `challenge=open/conflict` を要し、`refutes` は `outcome=refuted` を要するが、反証命題と被覆が閉じていれば `terminal refuted / challenge=none` は許される。単なる不確実を challenge と呼ばず、locator は参照証拠の宣言済み観測位置へ閉じる。
6. 証拠ファイル自体の digest だけを、試験対象 snapshot の拘束と見做さない。全 `subject_locators` が digest で覆われない証拠は `current` にせず、現対象へ結び付かない証拠を `stale` 又は `unbound` とする。`test_execution / bound` は、SHA-256 で拘束した `semantic-guard-evidence-subject-manifest/v0`、`closed_world=true`、manifest と一致する全対象 digest、証拠報告及び manifest 自身とは異なる少なくとも一つの試験対象、環境、command 又は raw log locator を必須とする。報告 JSON 自身だけを対象分母にして `bound` へ昇格してはならない。項目状態を `current` にするなら、その項目が参照する全証拠も `current / bound` でなければならない。失効・変更影響・再資格条件が未定なら、その欠落自体を未解決として残す。
7. `independently_observed / signed / formally_verified` を名乗る観測は、観測者と独立性根拠、署名・信頼根・証明、又は形式模型・検証器・検証結果の該当欄を満たし、根拠成果物 locator が実在しなければならない。なお公開 provenance 契約にはこの拘束がまだ無く、保証 profile の採用と共に未解決である。
8. 未解決事項の `blocks_claim` は対象項目の `satisfied`、`blocks_claim / partially_blocks_claim` は `terminal satisfied` を禁止する。反証命題と被覆が閉じた `terminal refuted` は妨げない。ビュー参照も構成項目へ展開する。各解消責務には安定 `obligation_id`、権限級の根拠、前提責務参照を付け、`resolution_paths` には分岐の起動条件、同じ未解決内で必要な責務、完了証拠条件を列挙する。全責務を少なくとも一経路で覆い、同一未解決内の前提は選択経路から落とさない。`resolution_summary` は非規範の要約であり、経路選択、優先順位、割当は人間又は外部管制が決める。現版の起動条件は自由文であり、検証器は到達可能性、排他性、網羅性、選択又は完了を証明しない。型付き選択・完了評価記録が実装されるまで、自由文条件だけを根拠に未解決事項を削除してはならない。
9. 正本を先に直し、`verification-source.generated.md` を決定論的に再生成する。生成物へ直接追記してはならない。`verification-matrix.md` は判断補助の編纂文書であり、正本の完全投影とは扱わない。
10. 生成投影の完全一致と、正本の schema、参照閉包、局所 path・digest、正本 digest を内部検証器で確認する。

```sh
uv run --locked python scripts/render_verification_projection.py
uv run --locked python scripts/render_verification_projection.py --check
uv run --locked python scripts/validate_verification_source.py
```

生成投影は、正本の全 container と scalar を JSON Pointer 付きで一度ずつ列挙する。内部検証器は生成文字列の完全一致まで検査するので、値の脱落又は手編集 drift は検出できる。ただし、編纂文書 `verification-matrix.md` の説明が正本と同じ意味か、又は生成投影の値が実世界で真かを証明するものではない。

この検証器の成功は局所整合の観測に限られる。実務性能、行為真正性、人間受理までは立証しない。結果 JSON は検証器 digest、実行時刻、Python・`jsonschema` 版、source・schema・共通 schema・生成投影 digest を含む。検査開始時と終了時にも追跡対象の digest を比較するが、信頼済み snapshot、時刻証明又は敵対的な変更後復元への耐性にはならない。永続証拠として用いるなら、この出力自体と対象環境を新しい日付付き観測へ固定し、現 source の自己申告へ循環させない。

内部検証器の結果契約は [`verification-validation-result.schema.json`](../validation/verification-validation-result.schema.json) である。引数解釈が成立した検証実行は、標準出力へ `schema_version / status / subject / execution / checks / counts / errors / limitations` を持つ JSON 一個を出す。`status=error` の `errors[]` は `code / location / message` を持つ。検証成功は終了符号 `0`、schema・参照・path・digest・投影のいずれかの不成立は `1`、未知引数等の argparse 利用法違反は標準誤出力と `2` である。schema 不適合 source の配列欄が誤型でも JSON failure envelope を失わない。入力 source、schema、projection は repository 内に解決されなければならず、外部 path は読まずに `path_outside_repository` とする。人間受理を `pending` 以外へ変える場合、判断時刻は登録済み証拠より後でなければならず、`decision_record_ref` は repository 内の実在記録を指さなければならない。

検証正本は欠落、競合、証拠不足、再検証条件を露出できるが、実装優先度、作業委譲、実行権限、切替、危険受容を決めない。管制は外部呼出側又は `resource-control-plane`、最終 `accept / request_revision / defer` は人間が所有する。

## 旧版比較

旧版は運用者所有の外部rootにある `vnext/migration/legacy-baseline-2026-07-17.json` の閉じた file digest 集合を照合してから別過程で実行する。現在の採取候補は155ファイルを照合するが、`capture_authority=pending_human_acceptance`であり、人間採択済みの正しさのoracleではない。repository内の `legacy/semantic-guard-v0.1.0/` は源保存であって、必要な実行体と同相対配置を備えた信頼rootではない。2026-07-15及び2026-07-16のmanifestは歴史的観測として残すが、正規実行時の信頼根には使わない。digestがずれた場合、既定では比較を行わない。

MCP の旧版影比較は既定無効である。工具呼出側から実行ファイル、adapter、manifest、source root を指定させない。server operator が必要性と対象を確認した場合だけ、MCP server process に次を設定する。

```sh
SEMANTIC_GUARD_ENABLE_LEGACY_SHADOW=1
SEMANTIC_GUARD_LEGACY_ROOT=/absolute/operator-owned/legacy-root
```

root は絶対 path で、`.venv/bin/python`、固定位置の `vnext/scripts/legacy_request_adapter.py`、`vnext/migration/legacy-baseline-2026-07-17.json` を含まなければならない。adapter と manifest が root 外へ解決される場合は拒否する。manifest 自体の digest も MCP server 側に固定する。空、構造不正、空 digest 一覧、非正規相対 path、不正 sha256、必須旧版源又は adapter の欠落、封印範囲と digest 一覧の不一致を持つ manifest は `allow_baseline_drift` の有無にかかわらず実行しない。新しい信頼根の採取には `capture_legacy_baseline.py` の明示確認旗が必要であり、生成物自体も人間の受理前は信頼済みとは扱わない。

旧版 adapter は選択 manifest に封印された root 内 path だけを実行する。Python 実行体の SHA-256 も照合し、環境変数は限定規約へ正規化する。実行後に基準線を再照合し、途中 drift は結果を無効化する。標準出力は旧版 `audit-result` schema と `phase=audit_request` に適合した場合だけ `completed` とし、入力・文脈 digest、profile、論理追跡方式、timeout、出力 digest を実行観測へ残す。`--require-legacy` は実行完了だけでなく、基準線一致、adapter 封印、出力 schema 適合を要する。CLI の manifest/adapter 明示差替えは局所診断用であり、MCP の正規基準線と同一視してはならない。

採取器は試験結果を捏造して manifest に書かない。試験・診断・標本評価の実観測は `validation/` の別記録に残す。実行体 digest と lockfile は通常の drift を検出するが、OS、動的 library、host、署名済み来歴又は悪意ある実行環境の真正性までは立証しない。

差分は少なくとも observation delta、direction、assessment、basis kind を分ける。新旧不一致だけで v1 の後退又は改善を断定しない。裁定根拠は憲法不変条件、適合例、変形不変条件、裁定済み実務例、運用証拠のいずれかでなければならない。

## 切替禁止条件

- GitHub CI の成功と対象枝の merge を確認していない。
- 重大誤満足率を実務資料で測っていない。
- 未解決差分が残る。
- 公開 schema と実体の適合試験が失敗する。
- 任意解析器の版又は資源版が記録されない。
- 人間受理と監査通過が混同される呼出側がある。
- 撤回可能な並行運転と旧版経路が用意されていない。
