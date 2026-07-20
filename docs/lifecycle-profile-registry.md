# Lifecycle profile registry candidate

## 結論

`lifecycle-profile-registry/v0` は、開発の十工程に必要な意味を候補契約として閉じる内部sidecarである。

```text
request → exploration → requirement → decision → plan
        → action → realization → diff → verification → completion
```

各工程に成果物がある、必須語が書かれている、局所試験が通る、監査が `pass` した、という事実だけでは工程成立にしない。各profileは入口・出口条件、必須意味欄、必須関係、原点要求別の義務template、証拠種別、妥当性確認材料、空洞成功、人間受理質問、未決定、上流・下流trace、再適格化条件、権限境界を持つ。

登録簿全体の状態は `candidate`、各profileは `pending_human_adoption` である。schema又は検証器がvalidと返しても、採択、runtime activation、実行許可、人間最終受理にはならない。

## 原点要求との接続

各profileは `OR-01`、`OR-02`、`OR-03` を全て保持する。

| 原点 | profile内の責務 |
| --- | --- |
| `OR-01` | 各工程の内容を採択済み要求工学、計画工学、ソフトウェア／システム工学規則へ追跡する義務 |
| `OR-02` | 対象命題、主体、規則、証拠、導出、信頼前提、反証、未証明を工程固有の限定立証材料として残す義務 |
| `OR-03` | 欠落、失敗、矛盾を修正へ戻し、受理・差戻し・保留を人間判断材料へ接続する義務 |

OR名の列挙だけでは足りない。検証器は、各profileの `upstream_trace.origin_requirements` が三件全てを含み、`obligation_templates` も三件を集合として被覆することを検査する。

## 十工程の意味分母

| 工程 | 中核となる必須関係 | 成果物存在だけでは足りない理由 |
| --- | --- | --- |
| request | stakeholder `requests` outcome、need `justifies` outcome、boundary `constrains` subject | 依頼票だけでは誰の何を変えるか分からない |
| exploration | question `targets` unknown、evidence `supports_or_refutes` hypothesis、owner `owns` question | 質問数だけでは未知、影響、判断先を被覆しない |
| requirement | actor `performs` behavior、behavior `acts_on` object、condition `constrains` behavior、measure `evaluates` outcome | 必須語の出現だけでは主体と対象の係り受け又は検証可能性が成立しない |
| decision | human decider `selects` disposition、disposition `resolves_or_defers` subject、rationale `cites` evidence | 監査結果又はagent提案は人間決定ではない |
| plan | work package `addresses` obligation、dependency `precedes_or_gates` package、verification `checks` output | 計画書だけでは要求対応、順序、停止、復旧、検証を閉じない |
| action | actor `executes` operation、authority `permits` scope、observer `observes` event、output `derived_from` input/event | 説明、命令、成果物又は自己申告から行動発生を推定できない |
| realization | artifact `realizes` requirement、artifact `derived_from` action、deviation `authorized_or_unresolved_by` decision | ファイル存在だけでは要求実現、由来又は逸脱処理を示さない |
| diff | change `transforms` baseline、change `traces_to` intent、impact `affects` surface | 文字差分だけでは意味、契約、運用又は移行影響を被覆しない |
| verification | procedure `tests` proposition、result `supports/refutes/leaves_unproven` proposition、evidence `observes` result | 試験通過だけでは対象、oracle、被覆、信頼、一般化限界を閉じない |
| completion | claim `aggregates` verification、residual `qualifies` claim、human `accepts/revises/defers` bundle | 完了報告、監査pass又は局所試験は人間最終受理ではない |

この表は説明用投影であり、正本は [候補登録簿](../validation/lifecycle-profile-registry.candidate.json) である。

## 権限境界

登録簿は次を機械的に拒否する。

- registry又はprofileが人間採択前に `adopted` を名乗る。
- semantic-guard又はagentがprofile採択権、runtime authority又は最終受理権を持つ。
- decisionをagent所有にする、又は監査結果から人間判断を推定する。
- actionの発生を説明から推定する、又は監査結果から実行権限を生成する。
- completion claimを人間最終受理と併合する、又は局所試験・監査passを `accept` へ昇格する。

decisionは `claim_owner=human` かつ `decision_authority=human_only` である。actionは `claim_owner=explicitly_authorized_actor` だが、外部権限記録と別個の発生観測を必須とする。completion claimは明示的に権限を持つactorが作成できる一方、`final_acceptance_authority=human_only` のままである。

これらは権限記録の構造を検査する境界であり、外部人間の本人性、組織権限、強迫不存在、判断品質を証明しない。

## Content addressとsummary再演

各profileの `profile_digest` は `profile_digest` 自身を除くcanonical JSONのSHA-256である。`registry_digest` は派生summaryとdigest自身を除く登録簿全体を束縛する。

保存済み `summary` は次を原資料から再演する。

- registry ID、版、digest。
- 十工程順とprofile count。
- stage別profile ID、版、digest。
- `OR-01`、`OR-02`、`OR-03` のprofile被覆。
- `pending_human_adoption` と `adopted` の件数。
- semantic-guardに採択、実行、最終受理権がないという権限文。

検証器はprofile、registry、summaryのいずれか一つでも再演結果が違えばfail-closedにする。digest整合は改竄不能性又は真正性ではない。同じ入力bytesから同じ値を再計算できるという内部整合に限られる。

## 現在できること

- JSON Schema Draft 2020-12で閉じた登録簿構造を検査する。
- 十工程が過不足なく正しい順序で存在するか検査する。
- profile ID、stage、既存 `lifecycle_trace` stage名の対応を検査する。
- 前工程・次工程の隣接trace、未知参照、逆向き参照を検査する。
- profile、入れ子欄、stageの重複を検査する。
- 必須意味分母、必須関係、義務、証拠、妥当性確認、人間質問、未決定、再適格化条件の空欄を拒否する。
- `OR-01` / `OR-02` / `OR-03` traceと、成果物存在だけの空洞成功条件を必須化する。
- decision/action/completionの権限洗浄を拒否する。
- profile、registry、保存済みsummaryを決定論的に再演する。

純粋APIは次である。

```python
from semantic_guard.lifecycle_profiles import (
    load_candidate_registry,
    seal_lifecycle_profile_registry,
    build_registry_summary,
    lifecycle_profile_registry_errors,
    validate_lifecycle_profile_registry,
)
```

`seal_lifecycle_profile_registry` はcontent addressとsummaryを再生成するだけで、状態を `adopted` に変えない。

## 外部人間採択が必要なこと

候補profileを実務の規範分母として使う前に、少なくとも次が外部で必要である。

- 各工程の目的、必須欄、必須関係、義務、空洞成功、受理質問を誰が採択するか決める。
- 対象業務、法令、組織、危険度ごとの適用条件、反適用条件、追加欄、閾値を決める。
- 工学rule-packの採択版とprofile義務を対応させ、領域専門家が妥当性を査読する。
- decision、action、completionで使う外部権限記録、観測者、信頼根、署名、時刻、保持、再適格化方針を決める。
- 人工肯定例でなく、独立に標注した現場資料と実運用で過検出、見逃し、空洞成功、理解可能性を評価する。
- 採択、差戻し、延期又は棄却の人間判断を所在付きで残す。

登録簿内の `human_acceptance_questions` は判断材料であって、回答、判断又は採択を自動生成しない。

## 既存 lifecycle trace との未統合境界

既存 `lifecycle-trace/v0` はnodeとedgeを用いて、主体、命題、義務、未解決、証拠、権限の工程間保存を検査する。本登録簿は各工程の内部意味を候補profileとして定義する。責務は補完関係にある。

しかし現段階では未統合である。

- `lifecycle_trace` nodeの `profile_refs` が本登録簿のprofile ID、版、digestを解決するresolverはない。
- node内容が該当profileの必須意味欄・関係・義務を充足するかを検査するadapterはない。
- profile再適格化が既存graph、state assessment、assurance claim又はcompletion claimを自動的に失効させる接続はない。
- CLI、MCP、既存public audit contractへの公開接続はない。
- registry採択記録、版移行、廃止、rollbackを扱う外部管制記録はない。

従って、`lifecycle_trace` がvalidで本登録簿もvalidであっても、「十工程の実資料が採択済み意味契約を満たした」とはまだ言えない。今あるのは、工程間の保存模型と工程内の候補意味模型が別々に検査できる状態である。

## 検証

```sh
uv run --locked python -m unittest tests.test_lifecycle_profiles -v
uv run --locked python -m py_compile src/semantic_guard/lifecycle_profiles.py
uv run --locked python - <<'PY'
from jsonschema import Draft202012Validator
from semantic_guard.lifecycle_profiles import lifecycle_profile_registry_schema
Draft202012Validator.check_schema(lifecycle_profile_registry_schema())
PY
```

敵対試験は工程欠落、順序改変、digest改変、未知・逆向き参照、空分母、採択詐称、OR trace欠落、成果物存在だけの空洞成功、decision/action/completion越権、重複identity、保存済みsummary改変を含む。

## 残る危険

- 十工程の候補内容は、原点要求と既存模型から構成した未採択案であり、体系知の独立査読と領域妥当性確認をまだ受けていない。
- 全profileが `OR-01` / `OR-02` / `OR-03` を被覆することはtrace完全性であり、各義務の実装又は有効性証明ではない。
- JSON Schema、digest、summary再演は内部整合だけを支え、証拠、権限、主体、時計、観測者の真正性を支えない。
- 必須関係を記録欄として持っても、その関係を自然言語や現場証拠から正しく抽出する性能は別評価である。
- 人間採択、既存traceへの統合、field evaluation、secure operation、運用再適格化が閉じるまでruntime既定経路へ昇格させてはならない。
