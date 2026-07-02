# Prototype Origin Requirement

作成日: 2026-06-30

## Purpose

この文書は、Criterion Loom / `semantic-guard`の今後の試作で、原点となる要求を見失わないための正本である。

ここで固定するのは、見栄えのよい概念文ではない。複数prototypeを作る時に、何を守り、何を測り、何を捨てるかを判断するための要求である。

## Origin Requirement

Criterion Loomは、CodexなどのAIエージェント作業において、依頼、探索前の問い、要求、決定状態、計画、差分、完了主張に含まれる不足、未決定、仮説、推測、証拠不足、意味のずれを、構造化された監査結果として外へ取り出す。

その監査結果は、AIエージェントの再計画、再実装、変更説明、完了報告の修正へ戻せる材料であり、同時に人間が最終的に`accept`、`request_revision`、`defer`を判断するための材料である。

最大要件は、判定systemが正しさを自動承認することではない。判断の根拠、未決定、証拠、限界を見える場所へ出し、後続の修正と人間判断へ接続できる状態を保つことである。

## Why This Matters

AIエージェントは、もっともらしい計画、もっともらしい完了報告、もっともらしい自己点検を作れる。だが、その中で何が事実で、何が仮説で、何が未決定で、何を証拠として確認したのかは、しばしば会話の内側へ沈む。

Criterion Loomの価値は、その沈んだ判断材料を外部化する点にある。高性能な自然言語判定器に見せることではない。実装、文書、試験、監査、受入判断を続けるために、作業の意味と証拠を扱える形へ戻すことにある。

## Essential Realization

本質的に実現したい状態は次である。

AIエージェントの作業について、要求、計画、変更、完了主張のどこに不足や不確実性があるかを、規則、証拠、反適用条件、限界、人間判断点つきで説明でき、その結果を次の修正行動へ戻せる。

成果物名やcommand数ではなく、この状態が実現されているかを見る。

## Audience And Use

- CodexなどのAIエージェント: 監査結果を受け取り、依頼解釈、計画、差分説明、検証、完了報告を修正する。
- 人間の受入判断者: 監査結果、実行証拠、残危険を見て、受理、差戻し、保留を判断する。
- 保守者: 規則、fixture、corpus、schema、外部証拠連携が原点要求から逸れていないかを確認する。

使い方は次である。

1. prototypeを作る前に、この文書を読む。
2. prototype charterに`origin_trace`を書く。
3. charterを監査し、原点要求へtraceできる場合だけ実装へ進む。
4. prototypeの採用、差戻し、保留、棄却は、人間判断材料として扱う。

文書監査の例:

```sh
uv run --python 3.13 --project . semantic-guard audit-request --kind document --file docs/prototypes/origin-requirement.md
```

## Non-Goals

- 人間の最終判断を代替すること。
- LLM reviewerの出力を承認、棄却、警告解除の根拠として単独採用すること。
- fixture pass rateを、任意文書に対する一般精度として主張すること。
- 保安走査器、要求工学製品、release gate、法務判定器、品質部門判定器を名乗ること。
- すべてのprototypeを一つの巨大機能へ混ぜること。
- public CLI、MCP、schemaの契約を、試作の都合で暗黙に変えること。

## Contract Boundary

この文書は、試作群の原点要求であり、新しいpublic CLI、MCP tool、API、schema、永続記録形式を定義しない。

既存の監査結果の共通形は、`phase`、`status`、`score`、`findings`、`missing`、`next_actions`、`details`を持つ。正式なfield、type、enum、error shapeは`schemas/audit-result.schema.json`、`README.md`、`skills/semantic-implementation/references/mcp-contract.md`を正とする。

この文書自身のrepository profile boundaryは次の通りである。

- `schema_version`: `prototype-origin-requirement/v1`。
- `repository_id`: `semantic-guard`。
- `public_surfaces`: documentation only。
- `commands`: `uv run --python 3.13 --project . semantic-guard audit-request --kind document --file docs/prototypes/origin-requirement.md`。
- `output_shapes`: no new output shape。
- `exceptions`: prototype-specific schema、CLI、MCP、API、record形式は個別prototype charterまたは別schemaで定義する。
- `internal_scope`: prototypeの内部実装、検出器設計、fixture追加、corpus採点は個別prototype側で扱う。
- `non_goals`: public contract definition、release gate、人間判断の代替。

prototypeが新しい構造化出力を持つ場合は、別文書またはschemaで次を定義する。

- `schema_version`またはschema source。
- named fieldsとvalue typeまたはenum。
- success shape: `status`、`payload`または`result`、`metadata`または`details`。
- failure shape: `error.code`、`error.message`、`error.details`、`next_actions`。
- CLIを増やす場合の`stdout`、`stderr`、exit code。
- 永続記録を作る場合のISO 8601 timestamp with timezone、evidence source、fact / inference / hypothesis / pending decisionの区別。
- 後から復帰するためのshallow surface: `context`、`current_state`、`action`、`detail_refs`。

## Invariants

すべてのprototypeは、次の不変条件を守る。

1. 監査結果は中間材料であり、最終判断ではない。
2. 人間の最終判断境界を残す。
3. LLMは補助材料に限る。決定的規則、構造化証拠、実行証拠を優先する。
4. `pass`は「現行規則では止めない」であり、実務上の受入ではない。
5. 局所fixtureとfield corpusを分ける。退行検出と一般性能評価を混同しない。
6. prototypeは原則sidecarとして作る。本体coreへ入れるのは昇格条件を満たした後に限る。
7. 各prototypeは、この原点要求のどの部分を強めるかを明記する。
8. 複数prototypeは別案として保つ。共通核だけを上位で束ねる。

## Prototype Charter Requirement

prototypeを作る前に、最低限次を記録する。

- `prototype_id`: 安定した識別子。
- `hypothesis`: 何を確かめる試作か。
- `origin_trace`: この文書のどの要求、不変条件、非目標に接続するか。
- `input_output`: 入力、出力、保存形式、公開契約を変えるか。
- `llm_dependency`: LLMなしで成否を測れる部分と、LLMを使う場合の補助範囲。
- `evidence_plan`: 価値、判定品質、妥当性、限界を点検する証拠。
- `acceptance_criteria`: 何が見えれば成功か。
- `rejection_conditions`: 何が起きたら棄却または差戻しか。
- `hollow_success_conditions`: 物はできたが本質的には失敗している条件。
- `promotion_criteria`: sidecarから本体へ昇格してよい条件。
- `rollback_or_disposal`: 捨てる、止める、戻す方法。

## Acceptance Criteria

この原点要求に沿ったprototype群は、次を満たす。

- 各prototypeが`origin_trace`を持つ。
- 各prototypeが少なくとも一つ、LLMのモデル性能に依存しない評価証拠を持つ。
- 規則、schema、fixture、corpus、外部証拠、trace、acceptance bundleのどれを改善するかが分かる。
- 価値、判定品質、妥当性、限界を別々に述べる。
- 局所較正結果と任意文書への一般化を分ける。
- 人間判断境界を侵さない。
- 本体契約を変える場合は、別計画、規約監査、試験、移行説明を要求する。

## Hollow Success Conditions

次の状態は、成果物が存在しても失敗である。

- prototypeが増えたが、原点要求への接続が説明できない。
- fixtureが通ったことを、一般性能の証明として扱っている場合。
- LLM reviewerの判断を、最終承認または警告解除として扱っている。
- 入出力契約、schema、CLIの変更が、試作という名目で暗黙に混ざっている。
- 監査結果が人間向け静的報告で止まり、AIエージェントの修正行動へ戻らない。
- 複数prototypeが混ざり、一つずつ採否判断できない。

## Candidate Prototype Families

この一覧は候補であり、要求ではない。

| Prototype | Strengthens | LLM-independent evidence |
| --- | --- | --- |
| rule-trace | 規則、根拠、適用条件、反適用条件、非発火理由 | rule detector mapping, derivation fixture |
| corpus-calibration | 実例に対する警告品質、過警告、警告漏れ | labeled field corpus metrics |
| external-evidence | 試験、走査、coverage、代表実行の証拠連携 | tool output schema and smoke runs |
| concept-drift-guard | 原点要求からの逸脱検出 | document audit fixtures and forbidden claims |
| revision-loop-repair | 監査結果から再計画、再実装、完了報告修正への接続 | rule_id to repair template coverage |

## Decision Rules

- `adopt`: 原点要求へtraceし、証拠があり、非目標を侵さず、保守可能である。
- `revise`: 価値はあるが、証拠、境界、反適用条件、評価方法が不足している。
- `defer`: 価値はあるが、今のprototype群の中核ではない。
- `reject`: 人間判断代替、過大主張、巨大統合、LLM依存承認、契約破壊に寄る。

## Open Decisions

- 最初に作るprototypeは未決定。現時点では`corpus-calibration`と`rule-trace`が有力である。
- prototype評価corpusの規模と採点語彙は未決定。
- sidecar artifactの保存場所と命名規則は未決定。

これらは、実装前に必要なら`resource-control-plane`側の未決定記録へ移す。

## First Next Action

次にprototypeを作る時は、この文書を先に読み、prototype charterを一枚書く。そのcharterがこの文書へtraceできなければ、実装へ進まない。
