# 状態評価・対象拘束・再資格契約

記録日: 2026-07-16
状態: 独立した opt-in 契約。既定監査経路への統合及び人間受理前。

## 目的

この契約は、検証結果や保証状態が別対象、旧対象、自己選択した証拠分母へ結び付くことを防ぎ、証拠の失効と再資格要求を再現可能にする。

原点目的への寄与は限定的である。すなわち、監査対象、適用規則、証拠、有効性方針、状態導出及び未証明範囲を外から再検査できる形にする。一方、対象分母そのものの妥当性、時刻真正性、証拠内容の外界真実、人間受理又は再資格作業の実行は証明しない。

## 契約列

```text
subject-manifest/v0
  ├─ 対象 path・role・digest
  ├─ environment identity・digest
  └─ profile identity・digest
          ↓ exact id/version/digest
state-evidence-observation/v1
  ├─ observed_at / expires_at / time_trust
  ├─ environment / tool / profile / rule identity
  └─ typed claim effects / trust / limitations
          ↓ evidence-validity-policy/v2
state-assessment/v2
  ├─ 六つの独立状態軸
  ├─ 根拠・反証・未証明範囲
  ├─ 証拠別有効性評価
  └─ 再資格に必要な証拠
```

三つの JSON Schema と Python の交差項検査を併用する。Schema は閉じた欄と条件必須を検査し、Python は digest 再計算、参照集合、時刻順序、対象同一性、状態導出及び再資格計画を再生する。Schema 通過だけで交差項閉包を主張してはならない。

## 閉世界 subject manifest

`subject-manifest/v0` は次を必須とする。

- `manifest_id` と `manifest_version`。
- `primary_subject` を少なくとも一つ含む対象 entry。
- 各 entry の repository 相対 path、role、SHA-256 digest。
- environment と profile の ID、版、SHA-256 digest。
- 明示した inclusion rule、除外 path と理由、対象件数。
- manifest 自体の canonical JSON digest。

絶対 path、`..`、空又は非正規 path、重複 path、重複 ID、包含と除外の重複、証拠 role しか持たない自己選択分母を拒否する。

ただし `primary_subject` という role の申告自体が正しいか、指定 root の外に本来含めるべき対象がないかは機械的に証明しない。閉世界は「宣言済み分母内の閉包」であって、未知対象の不存在ではない。

## 証拠観測

`state-evidence-observation/v1` は、証拠 ID、種別、内容 digest、観測記録 digest、対象 manifest の正確な ID・版・digest、観測時刻、失効時刻、時刻信頼申告、environment・tool・profile・rule identity、型付き `claim_effects`、信頼級及び限界を保持する。各効果は軸、値、`supports_axis_value`、根拠規則 ID を持ち、`covered_claim_dimensions` は効果の軸集合と完全一致しなければならない。

観測記録 digest は記録内の改変を検出するが、元証拠 bytes、署名者、時計又は観測行為の真正性を確立しない。元証拠内容の digest 検算は、証拠取得側が別途行う必要がある。

## 有効性方針

`evidence-validity-policy/v2` は次を版付きで固定する。v2 は採択判断の人間主体束縛を必須化した破壊的契約変更であり、v0 及び v1 を暗黙には受理しない。

- `pending / adopted / retired` の採用状態。
- `adopted` の時だけ必須となる外部人間判断参照。
- 証拠種別ごとの最大有効期間、許容信頼級、再資格証拠種別。
- 証拠種別ごとに主張できる軸と値の上限 `claim_ceiling`。
- subject、environment、tool、profile、rule の digest 変更に対する失効結果と再資格要求。
- 信頼不能時刻を `stale` 又は `unbound` へ落とす方針。

`pending` 又は `retired` の方針から `current` は生成しない。採用判断日時より前の評価にも、その採用済み方針を遡及適用しない。

方針の採用は semantic-guard が行わない。採択判断は `decision_kind=adopt_evidence_validity_policy`、方針 ID、版、`policy_basis_digest` を完全一致で指す。加えて `decided_by` は版・内容 digest 付き `decision_maker_identity` と同一 ID でなければならず、`decision_maker_kind=human`、`external_to_semantic_guard=true`、判断記録の locator 及び digest を必須とする。コーディングエージェント種別の判断主体、または `decided_by` と同一性束縛が異なる記録は拒絶する。基礎要約は採択状態・判断記録・最終要約を除く意味内容から先に計算するため循環せず、最大年齢や主張上限を変えた方針へ古い判断を使い回せない。外部判断参照の存在、人物対応、署名及び真正性は、この純粋計算器だけでは検証しない。

## 六つの独立状態軸

`state-assessment/v2` は次を別々に保持する。v2 は人間受理判断の主体束縛を必須化した破壊的変更であり、v0 及び v1 を暗黙に受理しない。`state-evidence-observation/v1` は変更しない。

| 軸 | 意味 |
| --- | --- |
| `implementation` | 実装の有無又は部分性 |
| `verification` | 指定手続の実行結果 |
| `validation` | 指定利用文脈での妥当性 |
| `assurance` | 限定命題に対する保証状態 |
| `freshness` | 対象拘束と方針に基づく証拠有効性 |
| `human_acceptance` | 外部人間判断記録の状態 |

前四軸の正値は、現在有効かつ対象拘束済みの支持証拠にある型付き効果からだけ導出する。一軸の値から別軸を補完せず、複数の効果値が衝突すれば評価自体を拒絶する。例えば `test_execution` の上限を実装・検証に限定した方針では、その試験を `validation=supported_in_context` の根拠に昇格できない。反証欄へ分類した証拠を正の軸根拠へ再利用することも拒絶する。

呼出元の `axis_values` は証明済み状態ではなく主張である。型付き効果と一致すれば導出値の補足として残るが、効果が無い一般的主張は `asserted_input_unproved` として保存し、軸値は `not_assessed` に留める。これにより規則名と説明文だけで正値を作ることを防ぐ。

`freshness` だけは有効性方針から決定論的に導出する。`human_acceptance` は外部判断記録が無ければ常に `pending` であり、状態評価自身が `accept` を作ることはない。外部記録は `decision_kind=accept_state_assessment`、評価 ID、対象 manifest、`acceptance_basis_digest`、人間種別の完全な判断主体束縛、外部記録 locator 及び digest を正確に指し、評価後に作られていなければならない。受理基礎要約は人間判断記録・人間受理軸・最終要約を除く技術評価から先に計算するため、軸、証拠、命題又は時刻を変えた評価への判断再利用を拒絶する。同一性束縛は記録内部の人間主体形状を保証するが、実人物との対応及び外部真正性は保証しない。

## `current` の必要条件

次が全て成立する場合だけ `freshness=current` となる。

1. subject manifest の schema、閉包及び digest が有効である。
2. 有効性方針の schema と digest が有効で、人間判断参照付きの `adopted` である。
3. 評価時点が方針採用時点以後である。
4. 全証拠が同じ manifest ID・版・digest を参照する。
5. manifest、証拠及び現在 context の environment・profile が一致する。
6. 証拠と現在 context の tool・rule identity が一致する。
7. 証拠種別が方針に存在し、信頼級が許容される。
8. 評価時点が観測後で、証拠の明示失効時刻と方針上限の双方より前である。
9. 評価時刻及び証拠時刻が方針上 `trusted` と申告されている。

対象差替え又は subject manifest digest 差は `unbound` とする。期限切れ、environment・tool・profile・rule 変更、信頼不能時刻は方針指定の `stale` 又は `unbound` とし、再資格要求を出す。

## 再資格出力

再資格計画は、次だけを返す。

- 再資格が必要か。
- 無効又は古い証拠参照。
- 失効理由と identity 変更種別。
- 方針が要求する証拠種別。
- 再評価を起動できる条件。

優先度、担当、実行順、外部作用又は完了判断は返さない。それらは管制面の責務であり、この監査契約へ混ぜない。

## 利用例

```python
from semantic_guard.state_assessment import build_state_assessment

assessment = build_state_assessment(
    assessment_id="assessment.example",
    proposition="The named subject satisfies the bounded claim.",
    subject_manifest=manifest,
    validity_policy=policy,
    assessed_at="2026-07-16T04:00:00Z",
    time_trust="trusted",
    evidence_observations=[evidence],
    current_environment_bindings=manifest["environment_bindings"],
    current_tool_identity=tool_identity,
    current_profile_bindings=manifest["profile_bindings"],
    applied_rules=[rule_identity],
    axis_values={"verification": "passed"},
    axis_basis={
        "verification": {
            "evidence_ids": [evidence["evidence_id"]],
            "rule_ids": [rule_identity["entity_id"]],
            "rationale": "The named procedure passed under the named rule.",
        }
    },
    supporting_evidence_ids=[evidence["evidence_id"]],
    unproven_scope=["Field validity remains open."],
)
```

全入力を呼出元が明示するため、同じ入力から同じ記録と digest が得られる。現在時刻、filesystem 又は外部サービスを builder 内で取得しない。

## 現段階の残余危険

- manifest に含めるべき対象を人間又は上流工程が誤って除外する危険。
- path と digest の申告元が対象 bytes を実際に読んだこと及び真正性を、この契約だけでは証明できない。
- `trusted` という時刻申告は時刻証明ではない。
- 方針採用記録及び人間受理記録の locator・digest は保持するが、その外部記録の存在、署名、権限及び真正性は別機構を要する。
- 証拠が各状態軸を意味的に十分支持するかは、採用済み工学 rule pack と独立査読を要する。
- 現実の evidence 取得、再資格実行、保存、失効通知及び既定経路統合は未実装である。
