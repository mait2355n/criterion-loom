# semantic-guard / Criterion Loom 全体評価 2026-07-11

> 2026-07-11 の局所研究試作を対象にした歴史的評価であり、現行 1.1.0 の実装状態ではない。公開版では端末固有 path、私的対話の逐語的来歴、公開 tree に存在しない成果物の実行指示を除いている。

本文中の bare path と行番号は評価時の対象を指す。公開用修復済みの旧版 archive に残る同名資料は `legacy/semantic-guard-v0.1.0/` 配下で参照できるが、原 byte の内容は annotated tag `v0.1.0` 又は commit `e0a3dd39f17385b66f6361ade25eb44bed6e1ab3` で確認する。

## 1. 評価目的

本書は、2026-07-11 時点の `semantic-guard` / Criterion Loom が次の二つをどこまで実現していたかを、当時の実装、公開契約、試験、配布、運用の観測結果から評価した記録である。

1. 開発各工程の要求、判断、計画、行動、実現方針、差分、検証、完了主張を、要求工学、計画工学、ソフトウェア／システム工学等の体系知に照らして監査し、正しさを主張する根拠と限界を明らかにするとともに、難点、欠落、矛盾、未決定、危険を露出する。
2. AI エージェントの各工程行為について、記録された前提、要求、規則、権限、実行、成果物、検証証拠の範囲内で、限定的な証明を構成可能にする。

後者は、本評価が追加前提として採用した中核要件である。2026-07-11 時点の原要求には収載されていなかったため、本書では評価前提と当時の正本との差分として扱う。後続版の原点要求における採否は [`../prototypes/origin-requirement.md`](../prototypes/origin-requirement.md) を参照する。

## 2. 評価範囲と非目的

評価対象:

- repository 内の `semantic-implementation` skill 文面。
- `semantic-guard` MCP server、CLI、Python package。
- 要求、計画、差分、完了、規約、判断状態、探索、追跡、LLM 補助査読、受理束。
- 規則 catalog、論理導出、JSON Schema、fixture、field corpus、単体試験、CI、doctor。
- wheel 生成と隔離環境への package 導入。
- 実務運用、組織統治、情報統治、証拠来歴、改竄検出、再現性。

非目的:

- コード、設定、schema、skill、MCP 契約、公開挙動の改修。
- 外部配備、正式認証、release 承認。
- 監査結果による人間の最終受理の代替。
- ISO、NIST、SLSA 等への適合宣言。

公開 tree に含まれる本評価の成果物は本書である。作成時に参照した構造化所見台帳は公開 tree に存在しないため、それだけに依存する所見はこの repository から独立再検証できない。

### 2.1 成果物契約と使い方

- 公開された人間向け記録: `docs/audits/semantic-guard-full-evaluation-2026-07-11.md`。
- 非公開成果物への参照は、本書の公開読者向け検証手順として扱わない。
- 公開CLI、MCP、package、既存schemaは変更しない。したがって本成果物独自の実行時error shape、stdout、stderr、exit codeは非適用である。
- 本書から最終人間受理を推定しない。公開された受理記録は確認できない。

## 3. 評価基準と証拠境界

### 3.1 工学的な比較基準

次の資料を概念的な比較基準として用いた。採用義務や適合認証を意味しない。

- [ISO/IEC/IEEE 29148:2018](https://www.iso.org/standard/72089.html): 要求工学工程、要求情報項目、ライフサイクル上の要求管理。
- [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework) と [AI RMF Playbook](https://www.nist.gov/itl/ai-risk-management-framework/nist-ai-rmf-playbook): AI 危険の `Govern / Map / Measure / Manage` とライフサイクル統治。
- [W3C PROV-O](https://www.w3.org/TR/prov-o/): entity、activity、agent を用いた来歴表現と交換。
- [in-toto](https://in-toto.io/docs/getting-started/) と [in-toto Attestation Framework](https://github.com/in-toto/attestation/blob/main/spec/README.md): 許可主体、工程、materials、products、署名された link metadata、attestation。
- [SLSA v1.2 Provenance](https://slsa.dev/spec/v1.2/provenance): 成果物がどこで、いつ、どのように作られたかを追跡する検証可能な来歴。
- [Sigstore verification](https://docs.sigstore.dev/cosign/verifying/verify/): digest、署名、証明書、bundle、透明性記録による真正性と完全性の検査。
- [OpenTelemetry context propagation](https://opentelemetry.io/docs/concepts/context-propagation/): 分散した実行単位を trace/span context で相関させる観測模型。これは証明そのものではなく、因果追跡の参考である。

### 3.2 証拠の優先順位

1. 評価時に実行した command と反証試験。
2. 評価時点の code / schema / fixture / test の file-line evidence。
3. 評価時点の文書が明示していた非目標と限界。
4. 外部基準との比較から得た推論。

文書の自己申告だけでは実装証拠としない。fixture 通過は局所退行証拠であり、実地精度ではない。暗号署名のない JSON は、内容の真正性を証明しない。

### 3.3 評価基準線

- 観測時刻: `2026-07-11T21:43:06+09:00`。
- 評価 root: `<local-source-root>`（公開写しでは端末固有 path を除去）。
- Git 状態: Git repository ではないため commit / branch / diff を基準線にできない。
- 評価前対象ファイル数: 189。`.venv`、cache、backup、`.DS_Store`、本監査文書を除外。
- 評価前 manifest SHA-256: `f091bb0f371f38097a9f59c66086abffb587d3daa47a9e3a36122cf37cff0cc2`。
- package version: `0.1.0`。

### 3.4 所見尺度

所見の重大度は、`critical`（中核命題又は権限境界を反転させ得る）、
`high`（主要な技術結論又は利用判断を変え得る）、`medium`（限定範囲の契約、
運用又は再現性を損なう）、`low`（結論を変えない明瞭性又は保守性の問題）の
四区分で記録した。確信度 `high` は、評価時点の対象ファイル又は再現 command
へ直接追跡できたという意味に限り、実地妥当性、現在性又は外部真正性を表さない。

## 4. 結論

2026-07-11 の評価対象は、**体系知を圧縮した決定論的な意味・構造監査を行い、そのJSON所見をAI エージェントの再計画・再実装・完了報告修正へ入力できる局所研究試作**としては成立していた。当時の局所環境では、CLI、MCP、47規則、構造化出力、限定論理導出、LLM 補助査読、人間受理束の動作を観測し、244件の単体試験と51件の局所fixtureの通過結果を得た。wheel の生成と隔離環境への導入も確認した。これらは、現在の導入状態又は利用可能性を示す証拠ではない。

しかし、2026-07-11 時点では、**実務領域の監査製品**および**AI エージェント工程行為の限定証明基盤**として未達であった。

評価時点の最大の断層は、監査対象が主として「要求文、計画文、差分説明、完了報告」であったのに対し、証明したい対象が「実際に行われた行為、その主体・権限・入出力・成果物・検証・来歴」であった点にある。当時の論理導出は監査判断の由来を説明できたが、行為事実を立証するものではなかった。

しかも、否定文中の `受入基準` や `証拠` という字句を `present / confidence=high` として受理し、対応義務を `satisfied` にできる反例を再現した。誤った前提から整然とした導出記録を作れる状態で証明機能を強化すると、単なる誤警告より危険な「説明可能な誤証明」になる。

したがって次の投資中心は規則数の追加ではない。**証明主張の契約、抽出事実の意味完全性、行為証拠束、因果識別子、証拠真正性、独立校正**である。

## 5. 成熟度評価

単一の完成度点又は未定義の成熟度語には還元せず、観測と未確認範囲を分ける。

| 評価面 | 評価時点で観測したこと | 未確認又は非立証の範囲 |
| --- | --- | --- |
| 原要求・責務境界 | 自動承認、正式認証及び人間判断代替を非目的とし、監査を修正材料へ戻す境界を文書が記述していた。 | 限定的行為証明は原要求に未収載。境界が全経路で強制されたこと。 |
| 局所決定論監査 | 47規則、各工程入口、構造化所見、244試験及び51 fixture の動作を局所観測した。 | 任意実務文書での精度と有効性。 |
| skill 文面 | repository 内の skill が作業経路と人間判断境界を記述していた。 | 外部環境への導入、同期、再読込又は運用状態。 |
| MCP 実行面 | package の MCP import と tool 呼出しが局所評価で成功した。 | 外部環境への登録、多人数・長時間・高負荷運用。 |
| package 配布 | wheel build、隔離したPython 3.13環境への導入及びCLI/MCP importが成功した。Python 3.11/3.13で244試験が成功した。 | 公開release、由来署名、SBOM、互換保証又は現在の導入可能性。 |
| 工学知識基盤 | 規則に工学領域、根拠、適用条件、反適用条件及び証拠要求があった。 | 規格版・条項・翻案責任・承認・失効管理を持つ統制知識基盤。 |
| 判断導出 | 要求7規則に fact / obligation / countercondition / derivation があった。 | 計画、差分、完了及び実行行為を同水準で導出すること。 |
| 工程追跡 | request / plan / diff / finish の欠落と語彙接続を出力した。 | 安定IDによる因果的な充足・生成・検証関係。 |
| 実地較正 | 51 fixture の局所退行実行を記録した。 | 外部holdout、領域別precision/recall、重大見逃し率及び評定者間一致。 |
| 限定的行為証明 | 監査判断の限定的導出と、自己申告の実行証拠欄があった。 | 行為事実、主体、権限、成果物、真正性、改竄耐性及び因果鎖の立証。 |
| 組織運用 | dry-run既定、read-only LLM査読、timeout及びschema検査があった。 | 資料分類、送信許可、伏字、永続job、同時数制御、監査log及び組織profile。 |
| 最終人間受理 | LLM出力と決定論監査を最終受理から分離する文面があった。 | 本評価書について人間受理を示す公開記録。 |

## 6. 観測された実装特性

### O-01 — 非目標と人間判断境界を明示していた

原要求は、監査出力を修正と人間判断へ接続し、`pass` を実務受理と同一視しないと記述していた。`docs/prototypes/origin-requirement.md:13-17, 52-59, 88-98`。これは記録された設計境界であり、全実行経路での強制を証明しない。

### O-02 — 複数工程の入口を実装していた

探索、対象理解、要求、判断状態、計画、差分、完了、規約、追跡、査読、受理束がCLI/MCPから利用できた。`src/semantic_guard/cli.py:54-82`、`src/semantic_guard/mcp_server.py:43-392`。当時の実装が複数工程の入口を公開していたことを示す。

### O-03 — 規則模型に保守用の欄があった

規則は識別子、工学領域、根拠、適用条件、反適用条件、必要証拠、重大度、指摘、修正方針を持つ。`src/semantic_guard/rules.py:17-53`。47規則と47 mappingが存在する。

### O-04 — 不確実性と確定事実を分ける状態欄があった

`candidate`、`rejected`、`unknown`、`conflict` と `present` を分け、反適用条件と不足義務を構造化する。`src/semantic_guard/logic.py:239-419`。利用者へ出すべき「何が未証明か」の基礎になる。

### O-05 — LLM補助査読に改変権限の制限があった

隔離査読は `--ephemeral`、利用者設定・規則無視、read-only sandbox、approval never、schema付き出力、timeoutを用いる。`src/semantic_guard/codex_exec_review.py:94-219`。LLM出力を最終承認へ直結しない。

### O-06 — 局所退行検査の記録があった

244単体試験、51 fixture、47規則のlabel被覆、doctor 9/9 passを確認した。Python 3.11と3.13の双方で244試験が通った。これは実地精度ではなく、記録対象の局所契約に対する退行検査である。

### O-07 — wheel 生成と隔離導入を評価用局所環境で観測した

2026-07-11 の評価では、256 KiB、117 entryのwheelを生成し、隔離した局所環境へ30依存を導入してCLIとMCP importを確認した。この一回の局所観測は、現在の導入可能性又は公開読者の環境での再現性を示さない。

### O-08 — 非主張範囲を文書化していた

当時の README は字句依存、過警告・見逃し、score非形式性、論理導出の限定、traceの語彙重複、文書監査の浅さを明記していた。`README.md:552-576`。これは当時の主張範囲を限定する記録である。

## 7. 主要問題

### F-001 — 限定的行為証明が原要求の正本にない

- 重大度: `critical`
- 確信度: `high`
- 証拠: `docs/prototypes/origin-requirement.md:11-31` は不足、不確実性、証拠、限界の外部化までを定めるが、行為事実、主体、権限、入出力、成果物の限定証明を定めない。
- 影響: 新しい規則や機能が増えても、行為証明に必要な責務が受入条件へ上がらない。
- 改良方向: 証明対象命題、信頼する観測者、前提、非証明範囲、反証条件、必要証拠を原要求へ追加する。

### F-002 — 否定・引用等を意味解釈せず、高確信の事実へ昇格できる

- 重大度: `critical`
- 確信度: `high`
- 証拠: `受入基準は定めない。検証方法はない。証拠は残さない。` に対し、`text.has_acceptance_criteria` と `text.has_evidence_artifact` が `present / confidence=high`、対応規則が `satisfied` になった。抽出は部分文字列中心である。`src/semantic_guard/logic.py:1193-1241`。
- 影響: 誤った前提から、見栄えのよい導出記録を作れる。限定証明の中核を直接壊す。
- 改良方向: `lexical_hit`、`candidate_assertion`、`semantically_asserted` を分け、否定、引用、例示、条件、歴史記述を扱う。高確信への昇格には意味上の肯定と独立証拠を要求する。

### F-003 — 監査対象と証明対象がずれている

- 重大度: `critical`
- 確信度: `high`
- 証拠: 通常監査結果の必須欄は `phase/status/score/findings/missing/next_actions/details` のみ。`schemas/audit-result.schema.json:7-51`。
- 欠落: `action_id`、actor、authority、start/end time、tool/model/rule version、input/output/artifact digest、environment、parent action、observer、signature、coverage manifest。
- 影響: 「その説明文が十分に見える」ことを監査できても、「その行為が実際に行われた」ことを立証できない。
- 改良方向: 証拠携行型の行為記録を第一級構造にし、semantic-guardはそれを監査・検証する側に留める。

### F-004 — 工程追跡が因果鎖ではなく語彙重複である

- 重大度: `high`
- 確信度: `high`
- 証拠: `trace-report` は token集合と受理済みtagの重複で `strong/medium/weak` を決め、`kind: vocabulary_overlap` を返す。`src/semantic_guard/traceability.py:98-201`。
- 影響: 同じ語を反復すれば強く見え、別語なら弱く見える。要求充足、成果物生成、検証因果を証明しない。
- 改良方向: `requirement_satisfied_by`、`plan_realized_by`、`action_produced`、`artifact_verified_by`、`evidence_observed_by` の型付き辺と安定IDへ移る。

### F-005 — 実行証拠と人間判断は自己申告だけでstrict validationを通る

- 重大度: `critical`
- 確信度: `high`
- 証拠: `execution_evidence` は自由文字列三つとbooleanだけ。`schemas/acceptance-review-bundle.schema.json:280-305`。`decided_at`も形式制約のない文字列。`src/semantic_guard/acceptance_review.py:186-230`。
- 反証: 存在しない成果物、未実行命令、`result: OK`、`passed: true`、`decided_at: not-a-date`、`decided_by: human` の受理束が `valid: true` になった。
- 影響: 受理束は構造的な確認表にはなるが、証明資料としての真正性はない。
- 改良方向: evidence ID、subject digest、command、exit code、raw output reference/digest、observer、acquisition method、tool/environment version、timestamp、signatureまたは信頼主体を必須化する。

### F-006 — 実地精度と価値効果が未測定

- 重大度: `high`
- 確信度: `high`
- 証拠: 較正報告自身が統計精度でないと明記する。`docs/calibration-report-2026-06-05.md:10-13`。field corpus 30件は local theme / dogfood中心で、試験は形と件数を検査するだけ。`tests/test_field_corpus.py:31-69`。
- 補足: field corpusが参照していた24規則IDのうち11個は評価時点のcatalog外で、将来候補と当時の規則の機械的境界も薄かった。
- 影響: 51/51を実務入力でのprecision/recallへ外挿できない。監査が手戻りを減らすか、警告疲労を増やすかも不明。
- 改良方向: 匿名化実案件、複数領域・文体、holdout、敵対例、独立複数人ラベル、評定者間一致、規則別precision/recall、重大見逃し率、修正後効果を測る。

### F-007 — 規則―検出器追跡表が実装記号へ到達しない

- 重大度: `high`
- 確信度: `high`
- 証拠: 全47 mappingが `source_module: semantic_guard.core` を指すが、記載された `source_functions` は同moduleに存在しない。実測 `mappings_with_missing_symbols=47`。`src/semantic_guard/rule_mapping.py:93-108`、`src/semantic_guard/core.py:1-22`。
- 影響: 「全規則mapping済み」というdoctor passは、実装への正しい追跡を保証しない。
- 改良方向: 実module/path/symbol、predicate version、rule version、source digestを返し、importとsymbol存在をdoctor/CIで検査する。

### F-008 — MCPの重要列挙値がfail-openで既定値へ落ちる

- 重大度: `high`
- 確信度: `high`
- 証拠: `kind=docment` は `requirement`、`profile=safty` は `default`、不正 `logical_trace` は `summary` へ黙って変換された。`src/semantic_guard/audit_common.py:64-94`、`src/semantic_guard/severity_profiles.py:136-140`。
- 影響: 呼出側は安全profileや文書監査を選んだつもりでも、別の監査が成功したように見える。
- 改良方向: MCP input schemaをenum化し、不正値は安定したinput errorへfail-closedする。

### F-009 — 公開schema、validator、error、versionの契約が分裂している

- 重大度: `high`
- 確信度: `high`
- 証拠:
  - audit-resultにtop-level `schema_version`がなく、`details`とfindingは開放形。`schemas/audit-result.schema.json:1-56`。
  - request explorationの手動validatorは、schemaが拒否するnested余分欄と非文字列を受理した。`src/semantic_guard/request_exploration_review.py:186-217`。
  - 存在しない`--file`は構造化誤りでなくPython traceback、exit 1、stdout空になった。`src/semantic_guard/cli.py:366-397`。
  - `status=block`でも通常監査CLIはexit 0。これは助言用途には妥当だが、CI gate用途には別policyが必要。
- 影響: 上位workflowが版、入力不良、監査block、依存障害を安全に区別しにくい。
- 改良方向: schemaをvalidator正本に統一し、全公開出力にversion識別、安定error envelope、`--fail-on warn|block`または外部policy adapterを設ける。

### F-010 — LLM経路の資料・個人情報統治がない

- 重大度: `high`
- 適用範囲: 組織利用時
- 確信度: `high`
- 証拠: candidate、request、audit、context等をpromptへ含め、同期結果はprompt/stdout/stderrも保持・返却する。`src/semantic_guard/llm_review.py:122-185`、`src/semantic_guard/codex_exec_review.py:60-91`。
- 影響: 要求、差分、秘密、契約資料、個人情報が外部model入力や二次logへ流れる可能性がある。read-only sandboxは送信統制ではない。
- 改良方向: data classification、redaction、送信許可、provider/model allowlist、path allowlist、保持期間、prompt非再掲、実行前preview、出力量制限を設ける。

### F-011 — 背景jobと観測面は局所試作用である

- 重大度: `medium`
- 確信度: `high`
- 証拠: job storeはprocess内dictionaryとdaemon threadで、再起動を越えない。完了済みjobの刈込はあるが、実行中同時数の拒否、queue、cancel、backpressure、durable stateがない。`src/semantic_guard/review_jobs.py:38-106`、`docs/llm-reviewer.md:158-168`。
- 影響: 長時間・多数利用で資源枯渇、状態喪失、操作来歴欠落が起きる。
- 改良方向: 同時数制限、queue/TTL/cancel、永続status、metrics/log/trace、client timeoutとの整合を運用隣接面に置く。

### F-012 — 公開文書、snapshot、release記録が現物とずれる

- 重大度: `medium`
- 確信度: `high`
- 証拠:
  - READMEは存在しない `docs/naming.md`、`docs/ja/naming.md`、`SECURITY.md` を参照する。`README.md:39-45`。
  - `docs/audits/public-snapshot-v1.0.0-2026-07-17.md` の snapshot contents はそれらを含むと記録する。
  - `CHANGELOG.md:33-45` はsecurity policyや36/39規則時点を記すが、現物は47規則、51fixtureである。
  - `docs/release/github-publication-summary-2026-07-02.md:26-31` はaudit-resultに`schema_version`とerror shapeがあるように書いていたが、評価時点のschemaにはなかった。
- 影響: 利用者が存在しない契約、古い較正値、未実装の誤り形を信じる。
- 改良方向: 現物生成のmanifest、リンク検査、schema由来の文書生成、release checklistをdoctor profileへ組み込む。

### F-013 — 規則知識と組織方針の統治がない

- 重大度: `high`
- 適用範囲: 組織利用時
- 確信度: `high`
- 証拠: 工学根拠は自由記述で、source edition、clause、interpretation owner、approved_at、review_at、validation casesを持たない。severity profileはコード固定5種。`src/semantic_guard/rules.py:27-38`、`src/semantic_guard/severity_profiles.py:8-140`。
- 影響: 組織別必須規則、例外、免責、期限、再審査、規格更新を統制できない。
- 改良方向: versioned rule pack、organization/repository profile、例外owner・理由・期限・evidence、規則採用記録を導入する。ただし監査と管制の境界は維持する。

### F-014 — doctor、CI、wheelは局所健全性に留まる

- 重大度: `medium`
- 確信度: `high`
- 証拠:
  - doctorは必須ファイル、JSON parse、import、mapping ID、CI文字列、fixtureを主に見る。`src/semantic_guard/doctor.py:35-185`。
  - CIはcompile、unittest、fixture、doctorのみ。`.github/workflows/ci.yml:29-39`。
  - wheelは `schemas/`、`docs/`、`skills/`、`tests/` をsite-packages直下へ置き、top-level namespace衝突の余地がある。`pyproject.toml:16-23`。
  - runtime依存は `mcp>=1.12.0` で上限なし。lockは1.27.2、fresh wheel導入では1.28.1が選ばれた。
- 影響: `doctor pass`がfresh install、MCP protocol、互換、保安、文書、複数OS、性能を保証すると誤読される。
- 改良方向: `doctor --release/--enterprise`、wheel/sdist fresh install、実MCP smoke、schema conformance、静的型/lint/coverage、依存・secret検査、namespace内resource配置、版互換試験を追加する。

## 8. 限定的行為証明の能力写像

| 証明対象 | 評価時点で観測した機構 | 未確認又は不足していた責務 |
| --- | --- | --- |
| 行為事実 | 本文から抽出したfactとevidence spanを記録した。実tool callや外部操作の観測ではなかった。 | action event、observer、actor、time、input/output digest、environment。 |
| 手続適合 | 申告された計画が検証、rollback、判断主体等を含むか監査した。 | 実行時権限、許可範囲、stop condition、通過工程の証拠。 |
| 判断導出 | 要求7規則がfact、obligation、countercondition、derivationを持っていた。 | 全工程へのpredicate coverage、抽出意味の健全化。 |
| 工程追跡 | 工程欠落と語彙接続を出力した。 | 安定IDと型付き因果辺。 |
| 結果充足 | 完了報告中の試験・受入証拠欠落を検出し、受理束を形検査した。 | 原証拠照合、再実行、対象digest、独立観測者、真正性検査。 |
| 未証明範囲 | unknown、conflict、未決定、証拠不足及び残危険を保持する欄があった。 | 規則・行為・証拠のcoverage manifestと、未観測領域の明示。 |

ここから導ける正確な表現は次である。

> 2026-07-11 時点の semantic-guard は、抽出器が受理した事実と局所規則を前提に、特定の監査判断がどう導かれたかを説明できた。AIエージェントの実行行為、その主体、権限、成果物、真正性、因果性を証明するものではなかった。

## 9. 改良計画の優先順

本評価の範囲に実装は含めない。以下は記録時点で依存順に並べた改良候補であり、後続作業への指示ではない。

### P0-A — 証明主張と信頼模型を固定する

- 証明する命題と証明しない命題を列挙する。
- self-report、tool output、filesystem observation、CI、human statement、signed attestationの信頼差を定義する。
- proof obligation、countercondition、coverage、失敗時の扱いを定める。
- semantic-guardは監査側、resource-control-planeは管理・保存・次行動側という境界を守る。

受入証拠: 原要求、threat/trust model、claim taxonomy、非目標、例示した正例・反例が人間に承認される。

### P0-B — 抽出事実の意味健全性を先に直す

- 否定、引用、例示、条件、歴史記述をfixtureとholdoutへ追加する。
- lexical hitを候補に留め、肯定命題と独立証拠が揃うまで`present/high`へ上げない。
- falsification fixtureを通常回帰fixtureと分ける。

受入証拠: F-002の反例が誤って`satisfied`にならず、既存fixtureの退行と新しい過警告率が報告される。

### P0-C — 証拠携行型行為記録を定義する

最低限次を持つ。

- `action_id`, `parent_action_id`, `trace_id`。
- actor / agent / authority / observer。
- start/end timestamp with timezone。
- tool / model / package / rule / schema version。
- commandまたは操作型、working directory、environment。
- input / output / artifact digest。
- raw evidence reference/digest、acquisition method。
- verification result、validation claim、limitations、unproven claims。
- signature、hash chain、または外部append-only recordへの参照。

受入証拠: 自己申告だけの偽証拠が拒否され、原証拠と成果物digestの不一致を検出できる。

### P0-D — 公開契約をfail-closedかつ版付きにする

- enum化、schema-validator統一、error envelope、top-level version識別。
- rule-detector mappingを実module/symbolへ修復する。
- CI用のexit policyを助言用途と分離する。

受入証拠: 不正kind/profile/trace modeがinput errorになり、全代表出力がschema検証を通り、全mapping symbolが解決する。

### P1-A — 語彙追跡から型付き因果追跡へ移る

要求、判断、計画step、行為、変更、試験、証拠、成果物に安定IDを与え、明示辺を構成する。W3C PROV、in-toto、SLSAは語彙と信頼境界の参考にするが、適用範囲を定めず一体実装へ取り込まない。

### P1-B — 外部証拠readerと結果充足行列を作る

test、coverage、CI、SAST、dependency scan等を、原結果digestと対象digest付きで正規化する。受入条件ごとに、検証方法、観測者、証拠、結果、不合格条件、残不確実性を辿れるようにする。

### P1-C — 独立較正と実務pilotを行う

複数領域の匿名化実例、独立ラベル、holdout、重大見逃し率、警告疲労、修正率、手戻り削減、判断時間を測る。局所fixtureと外的妥当性を混ぜない。

### P1-D — 情報統治と運用面を整える

資料分類、送信許可、伏字、保持、job永続化、同時実行制御、監査log、metrics、組織profile、例外台帳を隣接面へ置く。semantic-guard自身を万能管制系へ膨らませない。

### P2 — 公開製品面を整備する

版管理、互換方針、公開package、source provenance、checksum/signature、SBOM、SECURITY/SUPPORT、複数OS、fresh install、MCP end-to-end、文書生成とリンク検査を整える。

## 10. 空虚な成功条件

次の状態は、改良が進んだように見えても本質的には失敗である。

- 規則数とfixture数だけ増え、外部holdoutで精度を測らない。
- 誤抽出したfactへ署名し、暗号的に堅い誤証明を作る。
- action logを増やすが、主体、権限、digest、観測者、反証条件がない。
- semantic-guardが実行管制・優先度・台帳を飲み込み、resource-control-planeとの境界を壊す。
- `doctor pass`やCI greenを実務妥当性・安全性・受理と呼ぶ。
- 文書上のschemaと実際の出力が再びずれる。
- LLM reviewerのfresh-eyesを独立事実証拠と誤認する。

## 11. 未決定事項

| ID | 未決定 | owner | blocking | 解決条件 |
| --- | --- | --- | --- | --- |
| D-01 | 限定証明の目標強度を、監査説明、改竄検出可能なattestation、形式証明のどこまでとするか。 | human | `blocking P0-C` | claim taxonomyと非目標を受理する。 |
| D-02 | 行為証拠の永続面をどこに置き、semantic-guardとresource-control-planeの責務をどう分けるか。 | human | `partially blocking` | 監査、保存、管制、最終判断のownerを決める。 |
| D-03 | 外部corpusへ利用できる実案件、匿名化条件、秘匿性、利用許諾。 | human | `blocking P1-C` | data governanceとlabeling protocolを承認する。 |
| D-04 | 最初に実務pilotする領域と許容危険。 | human | `blocking production claim` | 対象工程、利用者、損失上限、fallback、受入指標を決める。 |

## 12. 実行証拠

以下は2026-07-11 の評価用局所環境で記録した結果である。現在の環境状態、外部からの再実行可能性又は公開読者の環境での再現性は示さない。

| 検査 | 結果 |
| --- | --- |
| `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests -q` | Python 3.13.12、244 tests、OK。 |
| `UV_PROJECT_ENVIRONMENT=/tmp/semantic-guard-audit-py311 uv run --python 3.11 --project . python -m unittest discover -s tests -q` | Python 3.11.15、244 tests、OK。 |
| `.venv/bin/semantic-guard evaluate-fixtures --path tests/fixtures` | 51/51、47 catalog rulesの局所label被覆。 |
| `.venv/bin/semantic-guard doctor --project-root <local-source-root>` | 9 pass、0 warn、0 block。 |
| `uv build --wheel --out-dir /tmp/...` | wheel生成成功、117 entries、256 KiB。 |
| fresh venv install + installed CLI/MCP import | 成功。source checkoutなしdoctorは6 pass、2 warn。 |
| invalid file CLI smoke | exit 1、stdout 0 byte、stderrにPython traceback。 |
| empty request CLI smoke | JSON `status=block`、exit 0。 |
| fake acceptance bundle strict validation | `valid=true`を再現。 |
| negation logical trace smoke | acceptance/evidence factの誤`present/high`とrule `satisfied`を再現。 |
| invalid MCP enum smoke | kind/profile/logical trace modeの既定値落ちを再現。 |
| rule-detector symbol resolution | 47/47 mappingでsource function不在を再現。 |

## 13. 文書再監査と所見採否

作成文書を監査結果のstatusだけで機械的に直さず、各findingのevidenceを読んで採否を決めた。

| 検査 | 結果 | 採否 |
| --- | --- | --- |
| YAML構文検査（当時の記録） | 当時の作業記録ではparse成功、`findings=14`、`improvement_program=9`。対象YAMLは公開treeに存在しない。 | `unavailable historical input`。公開treeから再検証できず、現在利用可能な機械走査用正本としては扱わない。 |
| 既存対象manifest再計算 | 評価前と同じ `f091...cc2`。 | 採用。既存資産が不変である証拠。 |
| `audit-diff` | `pass`。文書二点以外の変更主張なし。 | 採用。ただしnon-gitのため実差分証明ではなく、hashを主証拠とする。 |
| 報告書 `audit-request --kind document` | `warn`、3件。Sigstore公式資料の説明、欠落能力の否定、`safety` profile誤指定の危険説明を過大主張として拾った。 | 3件とも棄却。リンク、非保証、反証証拠が本文にあり、能力を主張していない。 |
| 報告書 `audit-conventions --kind document` | `warn`、11件。MCP、証拠、profile等の局所語に反応。 | runtime contractは非適用で2.1節に明記済み。表現findingは証拠参照を個別確認し、結論を変える曖昧さなし。検出器較正候補として保留。 |
| YAMLの文書監査（当時の記録） | 当時の作業記録では`warn`。見出し・実行例欠落とscope語への規約警告。対象YAMLは公開treeに存在しない。 | 当時の採否記録としてのみ保持する。公開treeから再検証できないため、現在の検証正本としては扱わない。 |
| `finish-check` | 明示的な残リスク、未実行事項、secret scan、dependency/auth/input-output/log非変更を与えた再監査で`pass`。 | 採用。最初の散文入力が残リスク・保安証拠を拾えなかった事実は字句感度の追加証拠。 |
| `trace-report` | `warn`だが`gap_count=0`、4 linksすべて`strong/high`、trace/vocabulary statusは`pass`。 | 接続証拠として採用。overall warnは埋込み監査の警告であり、意味充足証明には用いない。 |

このtriage自体も、評価時点のsemantic-guardの長所と弱点を示していた。所見を外へ出して個別に読める点は有用であったが、`status`や`score`だけで自動修正・受理すると誤るという限界も観測した。

## 14. 最終受理境界

この評価は、2026-07-11 時点で収集した証拠から作った歴史的監査材料である。当時想定した最終判断は、次のいずれかとして人間が行うものであった。

- `accept`: 評価内容と優先順を今後の改良基準として受理する。
- `request_revision`: 所見、重大度、範囲、優先順を差し戻す。
- `defer`: 追加証拠または目標強度の決定まで保留する。

評価記録の終了時点では `final_human_decision.status` は `pending` であった。後続する人間判断の有無又は内容は本書から推定しない。
