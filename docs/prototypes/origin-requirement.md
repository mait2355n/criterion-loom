# Prototype Origin Requirement

作成日: 2026-06-30

## Purpose

この文書は、Criterion Loom / `semantic-guard` の今後の試作で、原点となる要求を見失わないための正本である。

ここで固定するのは、見栄えのよい概念文ではない。複数 prototype を作る時に、何を守り、何を測り、何を捨てるかを判断するための要求である。

## Origin Requirements

### OR-01 — 工程横断の体系監査

Criterion Loom は、AI エージェントが関与する開発工程の依頼、探索前の問い、要求、決定状態、計画、行為、実現方針、差分、検証、完了主張を、要求工学、計画工学、ソフトウェア／システム工学その他の明示された体系知に照らして監査する。

監査は、正しさを主張する根拠とその限界を明らかにし、不足、未決定、仮説、推測、意味のずれ、矛盾、難点、危険、証拠不足を構造化された結果として外部化する。

### OR-02 — AI エージェント行為の限定的立証

Criterion Loom は、AI エージェントの各工程行為について、対象命題ごとに、記録された要求、前提、規則、権限、主体、観測者、実行、入出力、成果物、検証証拠、信頼条件の範囲内で、何が支持され、何が反証され、何が未証明または矛盾状態にあるかを示す限定的な立証を構成し、監査可能にする。

この責務は、記述が整っていることと、行為が実際に起きたことを別の命題として扱う。

### OR-03 — 修正と人間判断への接続

監査結果と限定的立証は、AI エージェントの再計画、再実装、変更説明、検証、完了報告の修正へ戻せる材料であり、同時に人間が最終的に `accept`、`request_revision`、`defer` を判断するための材料である。

最大要件は、判定 system が正しさを自動承認することではない。判断の根拠、未決定、証拠、反証条件、未証明範囲、限界を見える場所へ出し、後続の修正と人間判断へ接続できる状態を保つことである。

## Meaning Of Correctness And Bounded Proof

本書でいう「正しさを担保する」とは、対象の正しさを無条件に確定することではない。対象命題、適用範囲、信頼前提、規則、観測、証拠、反証条件、未観測範囲、残余危険を追跡可能にし、何がどこまで支持されるかを再検査可能にすることを指す。

「限定的な立証」とは、対象命題と必要証拠が明示され、使用した証拠と導出を再現でき、証拠不足、反証、矛盾、被覆不足がある場合は未証明として残る保証主張を指す。

形式的証明、暗号的真正性、実行主体の本人性、改竄不能性を主張できるのは、それぞれに必要な形式模型、検証器、信頼根、署名、透明性記録その他の機構が実装され、その機構自体の前提と限界が明示されている場合に限る。

## Current Implementation Status

`OR-01`、`OR-02`、`OR-03` は到達すべき要求であり、現実装がすでに全項目を実現したという完成主張ではない。

2026-07-17 の正本 v1.0.0 は、単一の構造化機能要求を義務へ分け、直接規則、未解決再集約、形態素信号、係り受け等の候補、呼出元提出 LLM 候補を権限分離したまま検査する要求関係監査を公開縦断として持つ。公開面は `audit-requirement`、制御された `shadow-compare`、閉契約を返す `schema` と、それぞれに対応する三つの MCP 工具である。形態素解析は `signal_only`、依存構造解析と LLM は `candidate_only` が上限で、生出力だけでは支持又は保留解除にならない。

要求工程以外の生活周期 profile、action evidence、状態評価、修復、実地評価、安全運用、運用資格、移行には版付き候補又は sidecar 契約があるが、共通公開 workflow、人間採択、実地証拠、外部真正性は未成立である。従って `OR-01`、`OR-02`、`OR-03` の全工程達成済みとはしない。

旧 0.1.0 が持っていた文書、要求、計画、差分、完了、規約、査読、受理材料の局所監査は `legacy/semantic-guard-v0.1.0/` に凍結保存する。これらは未移植工程の互換導線であって、v1 正本へ透過統合された機能でも、正しさの oracle でもない。

正本化の境界は `docs/canonical-promotion-decision.md`、移行は `docs/migration-v0.1.0-to-v1.0.0.md`、現時点の技術監査は `docs/audits/canonicalization-audit-v1.0.0-2026-07-17.md` に記録する。要求上の語義、局所契約適合、実務妥当性、人間採択を混同しない。

## Why This Matters

AI エージェントは、もっともらしい計画、もっともらしい完了報告、もっともらしい自己点検を作れる。だが、その中で何が事実で、何が仮説で、何が未決定で、何を証拠として確認したのかは、しばしば会話の内側へ沈む。

Criterion Loom の価値は、その沈んだ判断材料を外部化する点にある。高性能な自然言語判定器に見せることではない。実装、文書、試験、監査、受入判断を続けるために、作業の意味と証拠を扱える形へ戻すことにある。

## Essential Realization

本質的に実現したい状態は次である。

AI エージェントの作業について、要求、計画、行為、変更、検証、完了主張のどこに不足や不確実性があるかを、体系知へ追跡できる規則、証拠、反適用条件、信頼前提、限界、人間判断点つきで説明できる。さらに行為に関する対象命題を、支持、反証、未証明、矛盾へ分け、その結果を次の修正行動へ戻せる。

成果物名や command 数ではなく、この状態が実現されているかを見る。

## Audience And Use

- Codex などの AI エージェント: 監査結果を受け取り、依頼解釈、計画、差分説明、検証、完了報告を修正する。
- 人間の受入判断者: 監査結果、実行証拠、残危険を見て、受理、差戻し、保留を判断する。
- 保守者: 規則、fixture、corpus、schema、外部証拠連携が原点要求から逸れていないかを確認する。

使い方は次である。

1. prototype を作る前に、この文書を読む。
2. prototype charter に `origin_trace` を書く。
3. charter を監査し、原点要求へ trace できる場合だけ実装へ進む。
4. prototype の採用、差戻し、保留、棄却は、人間判断材料として扱う。

正本 v1 で一つの機能要求を監査する例:

```sh
uv run --locked semantic-guard audit-requirement \
  --text '監査結果は、未解決義務と根拠範囲を保持しなければならない。'
```

この原点文書全体に対する旧 `audit-request --kind document` が必要なら、凍結旧版を明示して実行する。これは v1 監査ではない。

```sh
cd legacy/semantic-guard-v0.1.0
uv run --locked semantic-guard audit-request \
  --kind document --file ../../docs/prototypes/origin-requirement.md
```

## Non-Goals

- 人間の最終判断を代替すること。
- LLM reviewer の出力を承認、棄却、警告解除の根拠として単独採用すること。
- fixture pass rate を、任意文書に対する一般精度として主張すること。
- 保安走査器、release gate、法務判定器、品質部門判定器を名乗ること。
- 要求工学、計画工学、ソフトウェア／システム工学等の全体系または全規格条項を実装したと主張し、規格適合審査や専門家判断を代替すること。
- 記録されていない行為、観測範囲外の事実、隠れた行為の不存在を証明したと扱うこと。
- 自己申告、字句一致、説明文の完全性だけを、行為発生、権限、成果物生成、検証成功の証拠として採用すること。
- 必要な信頼根や検証機構なしに、形式証明、真正性、本人性、因果性、改竄不能性を主張すること。
- `semantic-guard` が AI エージェントの実行管制、優先度、権限付与、永続台帳、最終受理を所有すること。
- すべての prototype を一つの巨大機能へ混ぜること。
- public CLI、MCP、schema の契約を、試作の都合で暗黙に変えること。

## Contract Boundary

この文書は、試作群の原点要求であり、新しい public CLI、MCP tool、API、schema、永続記録形式を定義しない。

正本 v1 の正式な field、type、enum、条件制約は `schemas/audit-result.schema.json` とそこから参照される schema を正とする。旧 0.1.0 の `phase`、`status`、`score`、`findings`、`missing`、`next_actions`、`details` という共通形は凍結旧版の契約であり、v1 の閉じた義務結果へ読み替えない。

この文書自身の repository profile boundary は次の通りである。

- `schema_version`: `prototype-origin-requirement/v3`。
- `repository_id`: `semantic-guard`。
- `public_surfaces`: documentation only。
- `commands`: 正本 v1 の個別要求監査は `uv run --locked semantic-guard audit-requirement --text ...`。原点文書全体の旧文書監査は `legacy/semantic-guard-v0.1.0/` 内の `audit-request --kind document` を明示的に使う。
- `output_shapes`: no new output shape。
- `exceptions`: prototype-specific schema、CLI、MCP、API、record 形式は個別 prototype charter または別 schema で定義する。
- `internal_scope`: prototype の内部実装、検出器設計、fixture 追加、corpus 採点は個別 prototype 側で扱う。
- `non_goals`: public contract definition、旧版契約の v1 への暗黙併合、release gate、人間判断の代替。

prototype が新しい構造化出力を持つ場合は、別文書または schema で次を定義する。

- `schema_version` または schema source。
- named fields と value type または enum。
- success shape: `status`、`payload` または `result`、`metadata` または `details`。
- failure shape: `error.code`、`error.message`、`error.details`、`next_actions`。
- CLI を増やす場合の `stdout`、`stderr`、exit code。
- 永続記録を作る場合の ISO 8601 timestamp with timezone、evidence source、fact / inference / hypothesis / pending decision の区別。
- 後から復帰するための shallow surface: `context`、`current_state`、`action`、`detail_refs`。

## Invariants

すべての prototype は、次の不変条件を守る。

1. 監査結果は中間材料であり、最終判断ではない。
2. 人間の最終判断境界を残す。
3. LLM は補助材料に限る。決定的規則、構造化証拠、実行証拠を優先する。
4. `pass` は「現行規則では止めない」であり、実務上の受入ではない。
5. 局所 fixture と field corpus を分ける。退行検出と一般性能評価を混同しない。
6. prototype は原則 sidecar として作る。本体 core へ入れるのは昇格条件を満たした後に限る。
7. 各 prototype は、この原点要求のどの部分を強めるかを明記する。
8. 複数 prototype は別案として保つ。共通核だけを上位で束ねる。
9. 字句の存在と、肯定命題の成立を同一視しない。
10. 記述物の完全性監査と、実行行為の立証を別の命題として扱う。
11. 支持される命題は、対象、範囲、証拠、信頼前提、反証条件、被覆、未証明範囲を持つ。
12. 証拠不足、観測不能、矛盾、digest 不一致を、暗黙の成功または `pass` へ昇格させない。
13. 自己申告、tool 出力、filesystem 観測、CI 結果、人間の証言、署名付き証明書は、同一の信頼強度として扱わない。
14. `semantic-guard` は監査と立証検査を担当し、実行管制、優先度、永続台帳、次行動の所有は `resource-control-plane` 側、人間の最終受理は人間側へ残す。

## Prototype Charter Requirement

prototype を作る前に、最低限次を記録する。

- `prototype_id`: 安定した識別子。
- `hypothesis`: 何を確かめる試作か。
- `origin_trace`: `OR-01`、`OR-02`、`OR-03`、不変条件、非目標のどれに接続するか。
- `input_output`: 入力、出力、保存形式、公開契約を変えるか。
- `llm_dependency`: LLM なしで成否を測れる部分と、LLM を使う場合の補助範囲。
- `evidence_plan`: 価値、判定品質、妥当性、限界を点検する証拠。
- `acceptance_criteria`: 何が見えれば成功か。
- `rejection_conditions`: 何が起きたら棄却または差戻しか。
- `hollow_success_conditions`: 物はできたが本質的には失敗している条件。
- `promotion_criteria`: sidecar から本体へ昇格してよい条件。
- `rollback_or_disposal`: 捨てる、止める、戻す方法。

## Acceptance Criteria

この原点要求に沿った prototype 群は、次を満たす。

- 各 prototype が `origin_trace` を持つ。
- 各 prototype が少なくとも一つ、LLM のモデル性能に依存しない評価証拠を持つ。
- 規則、schema、fixture、corpus、外部証拠、trace、acceptance bundle のどれを改善するかが分かる。
- 価値、判定品質、妥当性、限界を別々に述べる。
- 局所較正結果と任意文書への一般化を分ける。
- 人間判断境界を侵さない。
- 本体契約を変える場合は、別計画、規約監査、試験、移行説明を要求する。
- 各 prototype が `OR-01`、`OR-02`、`OR-03` のどれを強めるかを安定した識別子で追跡できる。
- 体系知を用いる規則は、根拠、適用条件、反適用条件、必要証拠、限界を持ち、規格適合そのものとは区別される。
- 行為に関する主張は、対象命題、必要証拠、信頼前提、反証条件、被覆、未証明範囲を明示する。
- 記述物の完全性、行為発生、手続適合、成果物との関係、検証結果を別々の命題として扱う。
- 否定、引用、例示、条件、歴史記述中の字句を、独立した肯定命題または行為証拠へ自動昇格させない。
- 証拠不足、反証、矛盾、観測不能、digest 不一致がある場合、支持または成功へ昇格せず未証明範囲を残す。
- 同じ入力証拠、規則版、tool 版から立証導出を再検査できる。

## Hollow Success Conditions

次の状態は、成果物が存在しても失敗である。

- prototype が増えたが、原点要求への接続が説明できない。
- fixture が通ったことを、一般性能の証明として扱っている場合。
- LLM reviewer の判断を、最終承認または警告解除として扱っている。
- 入出力契約、schema、CLI の変更が、試作という名目で暗黙に混ざっている。
- 監査結果が人間向け静的報告で止まり、AI エージェントの修正行動へ戻らない。
- 複数 prototype が混ざり、一つずつ採否判断できない。
- 体系知の名称を並べたが、規則根拠、適用条件、反適用条件、必要証拠を追跡できない。
- action log を増やしたが、主体、権限、観測者、時刻、入出力、成果物 digest、反証条件がない。
- 意味を誤抽出した fact へ署名し、暗号的に堅い誤証明を作る。
- claim taxonomy と信頼前提を定めず、「証明可能」という語だけを追加する。

## Candidate Prototype Families

この一覧は候補であり、要求ではない。

| Prototype | Strengthens | LLM-independent evidence |
| --- | --- | --- |
| rule-trace | 規則、根拠、適用条件、反適用条件、非発火理由 | rule detector mapping, derivation fixture |
| corpus-calibration | 実例に対する警告品質、過警告、警告漏れ | labeled field corpus metrics |
| external-evidence | 試験、走査、coverage、代表実行の証拠連携 | tool output schema and smoke runs |
| action-evidence-envelope | 行為命題、主体、権限、観測、入出力、成果物関係、信頼前提、反証条件 | deterministic envelope validation and adversarial fixtures |
| concept-drift-guard | 原点要求からの逸脱検出 | document audit fixtures and forbidden claims |
| revision-loop-repair | 監査結果から再計画、再実装、完了報告修正への接続 | rule_id to repair template coverage |

## Decision Rules

- `adopt`: 原点要求へ trace し、証拠があり、非目標を侵さず、保守可能である。
- `revise`: 価値はあるが、証拠、境界、反適用条件、評価方法が不足している。
- `defer`: 価値はあるが、今の prototype 群の中核ではない。
- `reject`: 人間判断代替、過大主張、巨大統合、LLM 依存承認、契約破壊に寄る。

## Open Decisions

- 最初に作る prototype は未決定。現時点では `corpus-calibration` と `rule-trace` が有力である。
- prototype 評価 corpus の規模と採点語彙は未決定。
- sidecar artifact の保存場所と命名規則は未決定。
- 行為 claim taxonomy、信頼・脅威模型、proof obligation、外部証拠の真正性確認方法は未決定。

これらは、実装前に必要なら `resource-control-plane` 側の未決定記録へ移す。

## First Next Action

次に prototype を作る時は、この文書を先に読み、prototype charter を一枚書く。その charter がこの文書へ trace できなければ、実装へ進まない。
