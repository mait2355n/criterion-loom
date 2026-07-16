# Lifecycle trace and composition

## 結論

`lifecycle-trace/v0` は、10工程の成果物が存在するかではなく、工程間で主体、命題、義務、未解決、証拠、権限が保全されたか、又はどの人間権限記録によって変更されたかを検証する内部試作契約である。

```text
request → exploration_question → requirement → decision → plan
        → action → realization → diff → verification → completion_claim
```

この列を並べただけではcomposition成功にならない。各nodeを結ぶtyped edgeが全入力材料の行方を示し、全nodeがrequestから到達可能でcompletion claimへ接続され、必須義務と未解決の消失や意味・信頼・権限の無断昇格がない場合だけ、内部compositionをvalidとする。

validは外部事実の正しさ、行為発生、証拠真正性、実務妥当性、又は人間受理を意味しない。

## 原点要求との接続

| origin | この試作が強めるもの | 強めないもの |
|---|---|---|
| `OR-01` | 依頼から完了主張までの10工程を同一の型付き関係graphへ載せ、工程間の意味保全と許可変更を検査する | 各工程固有の工学rule-packの正しさ・完全性 |
| `OR-02` | 主体snapshot、命題digest、義務状態、証拠trust/freshness、actor/observer、権限を限定的立証材料として結合する | 行為発生、本人性、署名、改竄不能性、因果性の外部証明 |
| `OR-03` | 未解決と残未証明範囲をcompletionまで保ち、人間の `accept` / `request_revision` / `defer` 記録を別権限として接続する | semantic-guard自身による採択、差戻し、延期、最終受理 |

## 正本となる構造

### Node

全nodeは次を持つ。

- 10種の `stage`
- `node_id` と決定論的 `node_digest`
- 対象snapshot refとSHA-256
- proposition IDとSHA-256
- requirednessを含むobligation states
- unresolved refs
- locator、digest、trust level、freshness、限界を持つevidence refs
- effective authority rights
- versioned profile refsとrule refs
- actorとobserver、その関係とtrust class
- timezone付き `recorded_at`

同じ文字列が別工程に現れることを同一主体又は同一命題の証拠にしない。refとdigestの双方をedgeで比較する。

### Edge

edge kindは次の9種である。

`refines`、`transforms`、`derives`、`verifies`、`supersedes`、`branches`、`merges`、`cancels`、`completes`

各edgeはversioned composition rule、入力node、出力node、許可変更、decision refs、evidence refsに加え、次の対応表を持つ。

- subject preservation
- proposition preservation
- obligation transition
- unresolved disposition
- evidence trust/freshness preservation
- authority right preservation/grant/revocation

一入力一出力だけでなく、branchの各出力、mergeの各入力と出力の組ごとに全対応が必要である。branch出力は後続merge又は明示的cancellationへ到達しなければならない。

### Resolution record

`resolved`、`refuted`、`not_applicable` は説明文だけでは成立しない。resolution recordは次を結合する。

- 対象obligationと関連unresolved refs
- 入出力node
- 出力nodeに位置づけられ、edgeから引用されたevidence
- 出力nodeが使用するversioned rule
- rationaleとrecorded time
- `not_applicable` の場合は対応するhuman authority record

従って、未解決配列から値を削除しただけではresolvedにならない。

### Human authority record

変更種別と必要record typeは次の通りである。

| change | human authority record |
|---|---|
| subject snapshot置換 | `subject_change` |
| proposition / intent変更 | `intent_change` |
| obligation又はunresolvedのscope除外 | `scope_change` |
| `not_applicable` | `not_applicable` 又は `scope_change` |
| evidence trust昇格 | `evidence_trust_override` |
| evidence freshness昇格 | `evidence_freshness_override` |
| authority right追加 | `authority_grant` |
| completionの受理・差戻し・延期 | `final_acceptance` |

recordは `issuer_kind=human`、人間actor、対象node、対象subject/proposition/obligation/right、判断、根拠、証拠、時刻を持つ。recordが台帳に存在するだけでは足りず、変更edgeの `decision_refs` から引用され、対象scopeが一致しなければならない。

semantic-guardはrecordの構造と対応を検証するだけであり、recordを発行せず、人間判断の正当性を自動承認しない。

## 閉鎖的検証規則

検証器は少なくとも次を拒否する。

- schema、node、edge、graph digestの不一致
- duplicate ID又はdangling endpoint/record/evidence
- 10工程の欠落、逆向きstage遷移、無型の同工程遷移
- cycle、requestから到達不能、completionへ到達不能
- branchの未回収、merge入力の不完全なcomposition
- authority recordのないsubject又はproposition置換
- obligationの無断消失、requiredness変更、terminal state洗浄
- located evidenceとversioned ruleのないresolution
- resolution又はscope authorityのないunresolved消去
- 同一evidence IDのdigest/locator置換
- human overrideのないtrust/freshness昇格
- human grantのないauthority right追加
- verification nodeを経ないcompletion claim
- completionにおけるactive required obligationの未被覆
- completion unresolved refsと残未証明範囲traceの不一致
- human authority recordのない `accepted` / `request_revision` / `deferred`

nodeが10個存在してもedgeが欠ければ、`node_not_composed_from_request` 又は `node_not_composed_to_completion` になる。

## Completion claim境界

completion claim nodeは次を明示する。

- 接続済みverification node refs
- 全active required obligationの `carried` / `resolved` / `refuted` trace
- 各義務を担うsource nodeとverification node
- completion時点の全unresolved refに対応する残未証明範囲
- `human_acceptance`

builderの既定思想は `human_acceptance.status=pending` である。非pending状態は、対応する `final_acceptance` human authority recordとcompletion edgeからの引用がある場合にだけ構造上成立する。それでもvalidityは「人間記録が正しく結合されている」という限定命題であって、semantic-guard自身が受理したことを意味しない。

## 使用する純粋API

```python
from semantic_guard.lifecycle_trace import (
    build_lifecycle_node,
    build_pair_preservation,
    build_composition_edge,
    build_lifecycle_trace,
    validate_lifecycle_trace,
)
```

- `build_lifecycle_node`: node contentから決定論的ID/digestを作る。
- `build_pair_preservation`: 入力nodeの全項目について保守的なcarry対応を作る。
- `build_composition_edge`: versioned composition ruleと対応表からedge ID/digestを作る。
- `build_lifecycle_trace`: node、edge、authority、resolutionを整列しgraph digestを作る。
- `validate_lifecycle_trace`: schema、digest、DAG、対応完全性、権限境界、completion closureを検証する。外部書込みを行わない。
- `lifecycle_trace_errors`: 失敗をtyped error codeとして返す。

## 検証

```sh
uv run --locked python -m unittest tests.test_lifecycle_trace -v
```

試験はvalidな10工程traceの決定論的再生に加え、subject/proposition substitution、obligation/unresolved drop、fake resolution、trust/freshness promotion、authority escalation、incomplete merge、cycle、verificationなしcompletion、acceptance laundering、node存在だけの空洞成功を反証する。

## 現在の限界

- 内部schema・builder・validatorであり、CLI、MCP、既存public audit contractへ未接続である。
- 実在の10工程artifactを生成・収集するadapterと永続台帳は未実装である。
- nodeの入力digestが正しい対象を表すか、evidenceが真正か、actor/observerが本人かは外部trust mechanismを要する。
- composition rule自体の工学的採択、独立査読、field corpus妥当化は別途必要である。
- initial authority rightsとinitial evidence trustの正当な発行元は、このgraphだけでは証明しない。
- branch/mergeの構造完全性は検証するが、代替案の探索十分性や採択価値は証明しない。
- `final_acceptance` recordの存在とscopeは検証できるが、人間判断の質、権限組織の適切性、強迫や誤認の不存在までは証明しない。

従って本試作は工程横断の「意味保全を検査できる型」を提供する段階であり、実務領域での有効性又は全工程完成を主張する段階ではない。
