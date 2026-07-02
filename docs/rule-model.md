# Rule Model

`semantic-guard` の rule catalog は、監査規則を履歴ではなく工学上の関心事として育てるための構造である。

## Purpose

既存の `core.py` は、小さな試作として判定を手続き的に持っている。そのまま規則を増やすと、なぜ警告するのか、どこまで適用するのか、どこには適用しないのかが読みにくくなる。

rule catalog は、規則ごとに根拠、適用条件、反適用条件、必要証拠、重大度方針を明示する。事例は規則を疑う材料であり、規則そのものの代わりにはしない。

## Status

この模型は最小実装である。現時点では `src/semantic_guard/rules.py` に代表規則を置き、既存 `core.py` の監査挙動は大きく変えない。外部DSL、規格群の網羅、推論器化は対象外である。

## When To Use

この模型は、監査規則を追加、分割、特殊化、一般化、廃止する時に使う。利用者は `semantic-guard` の保守者、監査結果を読む Codex、規則の根拠と適用範囲を確認する人である。

新しい警告を足したい時は、先に rule catalog 上で次を確認する。

- どの工学領域の関心事か。
- どの標準、手引き、または設計原則に接地するか。
- どの入力に適用するか。
- どの入力には適用しないか。
- 何を証拠として要求するか。

## Rule Fields

各 rule は次の欄を持つ。

- `id`: 安定した規則識別子。例: `req.verifiability.acceptance_missing`。
- `discipline`: 根拠領域。例: `requirements_engineering`, `project_planning`, `software_engineering`, `secure_development`, `semantic_preservation`。
- `phase`: 監査段階。例: `audit_request`, `audit_plan`, `audit_diff`, `finish_check`。
- `engineering_basis`: 参照する工学上の根拠。
- `concern`: その規則が防ぎたい失敗。
- `applies_when`: 適用条件。
- `does_not_apply_when`: 反適用条件。
- `evidence_required`: 求める証拠。
- `severity_policy`: strict mode などに応じた重大度。
- `finding`: 利用者へ返す指摘。
- `remediation`: 修正または補足の方針。

最小形は次のようになる。

```python
Rule(
    id="req.verifiability.acceptance_missing",
    discipline="requirements_engineering",
    phase="audit_request",
    engineering_basis=(
        "ISO/IEC/IEEE 29148: requirement quality and verifiability",
        "BABOK: requirements acceptance criteria and traceability",
    ),
    concern="要求が達成確認不能なまま実装へ進むこと。",
    applies_when=("入力が要求または要求候補である。",),
    does_not_apply_when=("入力種別が説明文書、計画、差分、完了報告である。",),
    evidence_required=("受入条件", "検証方法"),
    severity_policy=(SeverityPolicy(mode="strict", severity="blocker"),),
    finding="要求の達成確認方法が見えない。",
    remediation="試験、解析、検査、実演、受入条件のいずれかを明示する。",
)
```

## Engineering Basis

現行の代表規則は、次の領域に分けている。

- Requirements engineering: ISO/IEC/IEEE 29148, BABOK, NASA SEH。
- Project planning: PMBOK, ISO 21502, NASA SEH。
- Software engineering: ISO/IEC/IEEE 12207, SWEBOK, ISO/IEC 25010。
- Secure-development guidance: NIST SSDF, OWASP, CWE。
- Semantic preservation: semantic-implementation と保守設計上の名前、識別子、保管、所属の区別。

ここでの参照は、規格や手引きの処理全体を実装するという意味ではない。`semantic-guard` の小さな監査規則が、どの考え方に支えられているかを示すための設計根拠である。

「実装工学」という独立した標準名は置かない。`semantic-guard` は、SWEBOK、ISO/IEC/IEEE 12207、ISO/IEC 25010、NIST SSDF から着想した観点を、実装時に見落としやすい失敗様式へ圧縮して扱う。この圧縮は規格適合性の主張ではなく、`src/semantic_guard/rules.py` の rule category の由来を説明するための保守用分類である。

## Reverse Conditions

`does_not_apply_when` は必須である。

理由は単純で、適用条件だけを持つ規則は過剰警告に寄りやすい。たとえば `security` や `sensitive surface` という語は、実装上の変更、文書上の説明、規格名、警告例のどれにも現れる。反適用条件がなければ、字面が似ているだけの入力まで警告してしまう。

反適用条件には、少なくとも次のどれかを書く。

- 入力種別が違う。
- 文脈側に必要証拠がある。
- 変更が挙動や構成を変えない。
- 完了確認側で対象外理由が記録されている。

## Growth Operations

規則は履歴を積むのではなく、次の操作で育てる。

- Add: 新しい失敗様式を防ぐ規則を足す。
- Specialize: 過剰警告した規則の適用範囲を狭める。
- Generalize: 似た規則をまとめ、語彙依存を減らす。
- Split: 一つの規則が複数の意味を背負っていたら分ける。
- Retire: 価値が薄い、または害が大きい規則を落とす。

変更時は、規則本文と fixture の両方を見る。fixture は規則の代わりではなく、規則が守る局所整合性の退行検出である。

## Detector Mapping

`rule-detector-map` は、catalog rule id と現在の検出経路を対応づける保守用の一覧である。

```sh
uv run --python 3.13 --project . semantic-guard rule-detector-map
```

`rule-detector-map` の各 JSON entry は次の field を返す。

- `rule_id`: catalog 上の規則 ID。
- `phase`: 監査段階。
- `detector_id`: 人間が読める検出器名。
- `predicate_id`: 論理監査や構造抽出など、より細かい判定単位。該当しない場合は `null`。
- `source`: 現時点の主な code path。
- `notes`: 対応上の注意。

`rule-detector-map` は意味理解の証明ではない。目的は、規則本文だけが育ち、検出器側の対応が人間の記憶へ落ちる状態を避けることにある。新しい規則を足した時に `rule-detector-map` が欠けるなら、その規則はまだ保守可能な公開 catalog とは言いにくい。

## Current Coverage

現行 catalog は次の代表規則を持つ。

- 要求の検証可能性と受入条件。
- 要求の非目標と対象外。
- 要求の達成条件、合格条件、完了条件。
- 要求の検証方法の具体性。
- 要求の達成確認に使う証拠成果物。
- 安全、権限、移行、公開、運用などの不合格/差し戻し条件。例: 権限変更は人間承認なしでは進めない。この例は acceptance rule の記述材料であり、外部組織の承認手続きまでは定義しない。
- 利用者操作や入力出力を含む要求の利用場面、入力条件、期待出力。
- 改善、対応、サポート止まりの要求に対する観測可能な振る舞い。
- 利用者操作や公開面を持つ要求の前提条件または発火条件。
- 操作や入力に対する期待結果、期待状態、エラー、拒否の扱い。
- API、CLI、JSON、設定などの入出力契約。
- 要求の利害関係者または出所。
- 品質要求の測定条件または受入基準。
- 複数要求の優先度または実施順序。
- 不確実表現の未確定、仮説、判断待ちへの分類。
- 解決策が観測症状ではなく、原因、発生機構、制約、責務構造へどう作用するか。
- 受入条件が症状の消失だけになり、目的達成、異常時挙動、反証条件を測れない状態。
- 計画の復旧経路。
- 計画の妥当性確認。
- 計画の受入判断主体。
- 計画の成果物分解、作業パッケージ、WBS 相当の分解。
- 複数作業の先行関係、依存順序、並行可否。
- 計画の見積、担当、資源、容量前提。
- 計画上のリスク対応、退避、代替、検知、責任主体。
- 解決策が危険、負荷、費用、責任、故障様式をどこへ移すかの確認。
- 複数段階計画の進捗確認点。
- 進捗や完了を測る基準線、指標、判定基準。
- 移行、公開、運用、設定変更などの変更統制。
- 高影響作業に対する判断ゲート、承認、停止条件。
- 新規依存、抽象、層、wrapper、schema などを足す計画の最小性根拠。
- 差分の試験義務。
- 差分の sensitive surface 変更。
- 差分の CLI/API/MCP/出力契約など公開面の変更。
- 差分の外部実行、入出力、解析など失敗しやすい処理。
- 差分の常駐、定期実行、通知、監視など運用観測性。
- 差分の依存、実行環境、構成、CI 変更。
- 差分の分岐、loop、例外処理、class、async などによる複雑性増加。
- 差分の名前、識別子、保管、所属の意味境界。
- 完了報告の検証証拠。
- 完了報告の公開挙動に対する代表実行証拠。
- 完了報告の受入証拠。

## Limits

この模型は、規則を管理するための構造である。監査判断の深い意味理解、標準適合性の判定、実装差分の網羅的解析をそれだけで行うものではない。既存 `core.py` の判定との対応は段階的に増やす。
