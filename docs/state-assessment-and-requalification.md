# 状態評価・対象の固定・再評価契約

記録日: 2026-07-16
状態: 明示的に有効化する独立契約。既定の監査経路には未統合であり、人間にも未受理である。

## 目的

この契約は、検証結果や保証状態が別の対象、古い対象、都合よく選んだ証拠範囲へ結び付くことを防ぎ、証拠の失効と再評価要求を同じ入力から再計算できるようにする。

原点目的への寄与は限定的である。監査対象、適用規則、証拠、有効性方針、状態の導出、未証明範囲を外から再検査できる形にする一方、対象範囲そのものの妥当性、時刻の真正性、証拠内容が現実と一致すること、人間による受理、再評価作業の実行は証明しない。

## 契約の流れ

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
  └─ 再評価に必要な証拠
```

三つの JSON Schema と Python による項目間検査を併用する。スキーマは、許される値や項目と条件付き必須項目を検査する。Python はハッシュ値の再計算、参照集合、時刻順序、対象同一性、状態の導出、再評価計画を再計算する。スキーマの通過だけで、項目間の整合が全て確認できたと主張してはならない。

## 対象範囲を固定する目録

`subject-manifest/v0` は次を必須とする。

- `manifest_id` と `manifest_version`。
- `primary_subject` を少なくとも一つ含む対象項目。
- 各項目のリポジトリ相対パス、役割、SHA-256 ハッシュ値。
- 環境とプロファイルの ID、版、SHA-256 ハッシュ値。
- 明示した包含規則、除外パスと理由、対象件数。
- 目録自体の正規化 JSON ハッシュ値。

絶対パス、`..`、空又は正規化されていないパス、重複パス、重複 ID、包含と除外の重複、証拠の役割しか持たない自己選択の対象範囲を拒否する。

ただし `primary_subject` という役割の申告自体が正しいか、指定したルートの外に本来含めるべき対象がないかは機械的に証明しない。ここで固定できるのは「宣言済みの対象範囲内に漏れがないこと」であって、未知の対象が存在しないことではない。

## 証拠観測

`state-evidence-observation/v1` は、証拠 ID、種別、内容ハッシュ値、観測記録のハッシュ値、対象目録の正確な ID・版・ハッシュ値、観測時刻、失効時刻、時刻の信頼申告、環境・ツール・プロファイル・規則の同一性、型付きの `claim_effects`、信頼区分、限界を保持する。各効果は軸、値、`supports_axis_value`、根拠規則 ID を持ち、`covered_claim_dimensions` は効果の軸集合と完全一致しなければならない。

観測記録のハッシュ値は記録内の改変を検出するが、元証拠のバイト列、署名者、時計又は観測行為の真正性を確立しない。元証拠内容のハッシュ値の検算は、証拠取得側が別途行う必要がある。

## 有効性方針

`evidence-validity-policy/v2` は次を版付きで固定する。v2 は採択判断を行う人間主体との厳密な結び付けを必須にした破壊的契約変更であり、v0 及び v1 を暗黙には受理しない。

- `pending / adopted / retired` の採択状態。
- `adopted` の時だけ必須となる外部人間判断参照。
- 証拠種別ごとの最大有効期間、許容する信頼区分、再評価に必要な証拠種別。
- 証拠種別ごとに主張できる軸と値の上限 `claim_ceiling`。
- 対象、環境、ツール、プロファイル、規則のハッシュ値変更に対する失効結果と再評価要求。
- 信頼できない時刻を `stale` 又は `unbound` へ落とす方針。

`pending` 又は `retired` の方針から `current` は生成しない。採択判断日時より前の評価にも、その採択済み方針を遡及適用しない。

方針の採択は semantic-guard が行わない。採択判断は `decision_kind=adopt_evidence_validity_policy`、方針 ID、版、`policy_basis_digest` を完全一致で指す。加えて `decided_by` は、版と内容ハッシュ値を持つ `decision_maker_identity` の `entity_id` と一致しなければならず、`decision_maker_kind=human`、`external_to_semantic_guard=true`、判断記録の所在及びハッシュ値を必須とする。コーディングエージェント種別の判断主体、又は `decided_by` が `decision_maker_identity.entity_id` と一致しない記録は拒絶する。基礎ハッシュ値は、採択状態・判断記録・最終ハッシュ値を除く意味内容から先に計算するため循環せず、証拠として認める最長経過時間や主張上限を変えた方針へ古い判断を使い回せない。外部判断参照の存在、人物との対応、署名、真正性は、この副作用のない計算器だけでは検証しない。

## 六つの独立状態軸

`state-assessment/v2` は次を別々に保持する。v2 は人間受理の判断主体との厳密な結び付けを必須にした破壊的変更であり、v0 及び v1 を暗黙に受理しない。`state-evidence-observation/v1` は変更しない。

| 軸 | 意味 |
| --- | --- |
| `implementation` | 実装の有無又は部分性 |
| `verification` | 指定手続の実行結果 |
| `validation` | 指定利用文脈での妥当性 |
| `assurance` | 限定命題に対する保証状態 |
| `freshness` | 対象との結び付きと方針に基づく、証拠の現在性 |
| `human_acceptance` | 外部人間判断記録の状態 |

前四軸の肯定的な値は、現在有効で、対象に結び付いた支持証拠の型付き効果からだけ導出する。一つの軸の値から別の軸を補完せず、複数の効果値が衝突すれば評価自体を拒絶する。例えば `test_execution` の上限を実装・検証に限定した方針では、その試験を `validation=supported_in_context` の根拠へ引き上げられない。反証項目へ分類した証拠を肯定的な軸の根拠へ再利用することも拒絶する。

呼出元の `axis_values` は証明済み状態ではなく主張である。型付き効果と一致すれば導出値の補足として残るが、効果が無い一般的主張は `asserted_input_unproved` として保存し、軸値は `not_assessed` に留める。これにより規則名と説明文だけで肯定的な値を作ることを防ぐ。

`freshness` だけは有効性方針から決定論的に導出する。`human_acceptance` は外部判断記録が無ければ常に `pending` であり、状態評価自身が `accept` を作ることはない。外部記録は `decision_kind=accept_state_assessment`、評価 ID、対象目録、`acceptance_basis_digest`、人間である判断主体の同一性を完全に固定する情報、外部記録の所在及びハッシュ値を正確に指し、評価後に作られていなければならない。受理基礎ハッシュ値は、人間判断記録・人間受理軸・最終ハッシュ値を除く技術評価から先に計算するため、軸、証拠、命題又は時刻を変えた評価への判断再利用を拒絶する。同一性の固定は記録内部の人間主体の構造を保証するが、実人物との対応及び外部真正性は保証しない。

## `current` の必要条件

次が全て成立する場合だけ `freshness=current` となる。

1. 対象目録がスキーマに適合し、宣言範囲内に漏れがなく、ハッシュ値も一致する。
2. 有効性方針のスキーマとハッシュ値が有効で、人間判断参照付きの `adopted` である。
3. 評価時点が方針採用時点以後である。
4. 全証拠が同じ目録 ID・版・ハッシュ値を参照する。
5. 目録、証拠、現在の文脈にある環境とプロファイルが一致する。
6. 証拠と現在の文脈にあるツールと規則の同一性が一致する。
7. 証拠種別が方針に存在し、信頼区分が許容される。
8. 評価時点が観測後で、証拠の明示失効時刻と方針上限の双方より前である。
9. 評価時刻及び証拠時刻が方針上 `trusted` と申告されている。

対象のすり替え又は対象目録のハッシュ値差は `unbound` とする。期限切れ、環境・ツール・プロファイル・規則の変更、信頼できない時刻は、方針指定の `stale` 又は `unbound` とし、再評価要求を出す。

## 再評価出力

再評価計画は、次だけを返す。

- 再評価が必要か。
- 無効又は古い証拠参照。
- 失効理由と同一性の変更種別。
- 方針が要求する証拠種別。
- 再評価を起動できる条件。

優先度、担当、実行順、外部作用又は完了判断は返さない。それらは作業管理側の責務であり、この監査契約へ混ぜない。

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

全入力を呼出元が明示するため、同じ入力から同じ記録とハッシュ値が得られる。現在時刻、ファイルシステム又は外部サービスの情報を構築処理の内部では取得しない。

## 現段階の残余危険

- 目録に含めるべき対象を人間又は上流工程が誤って除外する危険。
- パスとハッシュ値の申告元が対象バイト列を実際に読んだこと及び真正性を、この契約だけでは証明できない。
- `trusted` という時刻申告は時刻証明ではない。
- 方針採択記録及び人間受理記録の所在とハッシュ値は保持するが、その外部記録の存在、署名、権限、真正性は別機構を要する。
- 証拠が各状態軸を意味的に十分支持するかは、採択済みの工学規則集と独立査読を要する。
- 現実の証拠取得、再評価の実行、保存、失効通知、既定経路への統合は未実装である。
