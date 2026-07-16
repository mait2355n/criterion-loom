# 比較優位と隣接実装候補 2026-06-03

## 目的

この文書は、公開状態で確認できる同系統の MCP サーバ、agent skill、仕様監査・保安走査系の実装を `semantic-guard` と比較し、次を切り分ける。

- `semantic-guard` が相対的に優位な点。
- `semantic-guard` が相対的に不利な点。
- `semantic-guard` の監査機能とは統合せず、隣接実装する価値がある仕組み。
- 監査 core に取り込むべきでない仕組み。

これは宣伝文ではない。`semantic-guard` を保安走査器、仕様平台、workflow 実行器、release gate、人間受入判断の代替として扱うための文書でもない。

## 調査範囲

確認日: 2026-06-03 JST。

調査対象:

- `semantic-guard`: local checkout of this repository
- Spec Kit: `github.com/github/spec-kit`, snapshot `7bab0568c5612ae50310fa341b0161d2e4babd26`
- Harness MCP: `github.com/harness/harness-mcp`, snapshot `3a37d886f2434d9c6ca97930eca799dd18999ee8`
- Semgrep agent / MCP sources: `github.com/semgrep/semgrep`, snapshot `15f510ede866353d84f0193769e854c47e4a0fe9`
- Snyk Studio MCP sources: `github.com/snyk/snyk-ls`, snapshot `6fea01ae4e6c41c42015d395bf5e2f0670d3feb8`
- Planu CLI package: `@planu/cli@4.3.20`

注意:

- Snyk、Semgrep、Harness には公開 repository から見える範囲外の商用機能がある。ここでは確認できた実装と文書だけを比較する。
- Planu は npm package 展開物から見た比較であり、非公開の運用や hosted feature は評価していない。
- Spec Kit は 2026-06-03 時点で workflow engine が追加されており、以前の「command template 中心」という評価より強い workflow 面を持つ。

## 結論

`semantic-guard` の優位は、単独領域の専門性ではない。

優位は、要求、計画、差分、完了、受入材料をまたいで、agent 作業の意味を外部化し、監査可能な JSON として残す点にある。

逆に、個別領域では普通に負ける。

- 保安走査は Semgrep / Snyk が強い。
- 仕様準備度、受入条件品質、coverage gap は Planu が強い。
- workflow 実行、再開、人間 gate は現行 Spec Kit が強い。
- 平台操作の audit log、危険度、elicitation は Harness MCP が強い。

したがって採るべき戦略は、競争ではなく隣接実装である。ただし engine を丸ごと輸入したり、既存の監査相へ直接混ぜたりはしない。外部道具から得られる証拠、規則、境界情報を sidecar artifact として生成し、必要な時だけ人間または上位 workflow が参照する。

この方針では、既存の `audit-request`、`audit-plan`、`audit-diff`、`finish-check`、`trace-report` の出力契約を変えない。追加するのは、監査 core の外側にある companion command、schema、report generator である。

## `semantic-guard` の現在地

`semantic-guard` は次の相を持つ。

| 相 | 役割 |
| --- | --- |
| `understand-target` | 対象理解の明文化 |
| `audit-request` | 要求、文書、計画、差分要約の入口監査 |
| `audit-plan` | 計画の目的、非目標、成果物、検証、受入、復旧、未決点を見る |
| `audit-diff` | 差分と意図、保安信号、意味境界、公開契約、失敗しやすい操作を見る |
| `finish-check` | 完了要約、検証証拠、受入条件、保安確認、代表実行を見る |
| `trace-report` | request / plan / diff / finish / evidence の対応と gap を出す |
| `acceptance-review-bundle` | 決定論監査、LLM 補助、人間確認点、残留危険を束ねる |

現行実装上の特徴:

- `audit_request` は input kind を分け、文書、計画、差分要約へ分岐する。
- `audit_plan` は日本語見出しや同義語を含む計画項目を診断する。
- `audit_diff` は保安信号、変更ファイル、意味境界、実装工学信号を出す。
- `finish_check` は検証証拠と受入証拠の欠落を扱う。
- `matching.py` は `match_status`、`confidence`、`nearest_candidates` を持つ。
- `logic.py` は fact、obligation、countercondition、derivation を JSON 化する。
- `traceability.py` は複数相をまとめて trace gap を出す。
- `escalation.py` は決定論監査で判別しにくい候補を dry-run の reviewer 補助へ回せる。
- `acceptance_review.py` は LLM review に final verdict を持たせず、`final_human_decision` を人間境界に残す。

この形は「コンテキストの外部化」に近い。ただし、ただの記憶や思考ログではなく、作業相ごとの義務、証拠、反証条件、人間判断点を構造化する外部化である。

## 比較表

| 対象 | 内部の主機構 | 相手側の強み | `semantic-guard` の優位 | `semantic-guard` の不利 |
| --- | --- | --- | --- | --- |
| Spec Kit | command template、spec / plan / tasks 手順、YAML workflow engine、state persistence、human gate | 仕様駆動開発の一連実行、再開、gate、shell/prompt/command step | 特定 workflow に縛られず、要求、計画、差分、完了の意味監査を横断できる | workflow 実行、resume、gate の運用面は弱い |
| Planu | spec format validator、readiness score、quality score、EARS / BDD、AC gap、coverage gap、drift、challenge-spec | 受入条件の粒度、準備度採点、仕様と test/code の対応 | 仕様平台に縛られず、外部成果物や dogfood 文書も監査できる。誤警告診断と人間判断境界が濃い | 受入条件の品質採点、coverage gap、drift 検出、対立質問が弱い |
| Semgrep | CLI/RPC 静的走査、post-tool hook、finding elicitation、既定方針の prompt injection | code 入力に対する静的規則照合、agent 編集直後の block、規則集合 | 意味、範囲、検証、完了証拠の監査であり、特定の規則照合に限らない | 実 code への規則照合能力は持たない。hook による即時阻止もない |
| Snyk Studio MCP | JSON tool registry、CLI 実行、trust/auth 確認、output mapper、scan tool profiles | SCA / SAST / IaC / container / SBOM / package health などの供給網・保安実行 | vendor 非依存で、code が無い段階の要求や計画も見られる | trust model、auth、scanner adapter、結果正規化は未整備 |
| Harness MCP | registry dispatch、operation policy、risk level、elicitation、structured audit event | 平台 API 操作の統制、危険度別確認、操作 audit log | API 操作履歴ではなく、作業成果物の意味と完了証拠を監査できる | `semantic-guard` 自身の CLI/MCP 呼び出し履歴や危険度記録は薄い |

## 優位性

### 1. 相をまたぐ意味の外部化

多くの同系統道具は、どこか一相に強い。

- Spec Kit は仕様駆動 workflow。
- Planu は仕様準備度と受入条件。
- Semgrep / Snyk は code と依存関係の走査。
- Harness は API 操作統制。

`semantic-guard` は、要求、計画、差分、完了を別々に扱い、その間の trace gap を出せる。ここが最も独自に近い。

実装上は、`trace-report` が request / plan / diff / finish / evidence を束ね、監査状態と trace 状態を分ける。単に「その場の回答が妥当か」ではなく、「前に言った目的と後の完了主張がつながっているか」を見られる。

### 2. 最終判断を奪わない構造

Semgrep の hook は findings が出ると block できる。Harness は危険度に応じて elicitation し、条件次第で API 操作を止める。これは実行統制として正しい。

一方、意味監査で同じことをやると危ない。要求や設計の良否は、文脈、事業判断、受入者の価値判断を含むからだ。

`semantic-guard` は、LLM review を補助に留め、`acceptance-review-bundle` の `final_human_decision` を `pending / accept / request_revision / defer` として人間側に残す。この境界は強い。面倒だが健全だ。

### 3. 誤警告を監査対象に含める

Planu や走査器は score や findings を出すが、`semantic-guard` は `nearest_candidates`、`match_status`、`confidence`、`warning_class`、`non_emitted_rules`、logical derivation で「なぜ出たか」「なぜ出なかったか」も出そうとしている。

これは heuristic system としては重要である。規則が荒い時、利用者が見るべきなのは警告そのものだけでなく、規則の弱さである。

### 4. code が無い段階でも効く

Semgrep / Snyk は code、依存、container、IaC が無いと力を出しにくい。Planu は仕様形式があるほど強い。

`semantic-guard` は、まだ code もテストも無い段階で、要求の達成条件、検証方法、証拠形式、非目標、未決点を要求できる。agent 作業ではここが効く。実装前の意味 drift は、あとから test だけで戻せない。

## 不利性

### 1. 専門 engine が薄い

保安は Semgrep / Snyk に勝てない。仕様準備度は Planu に勝てない。workflow 実行は Spec Kit に勝てない。操作監査は Harness に勝てない。

これは恥ではないが、誤魔化すと破綻する。`semantic-guard` は横断監査層であって、各専門 engine の代替ではない。

### 2. score が局所較正に留まる

fixture は役に立つが、任意文書への precision / recall を証明しない。Planu のような readiness / quality score も、Semgrep のような rule corpus も、Snyk のような脆弱性知識基盤もない。

したがって公開時は、fixture pass rate を「任意文書でも同じ品質で判定できる」という主張へ飛躍させてはいけない。

### 3. 外部証拠の隣接生成・参照口が未成熟

現在の `finish-check` は「検証したか」「証拠があるか」を見るが、Semgrep JSON、Snyk JSON、coverage report、test report、workflow gate result などを、監査 core から独立した証拠 report として正規化する schema がまだない。

このせいで、外部道具の強みを「監査の材料」として横に置きにくい。

### 4. workflow と操作監査が弱い

Spec Kit は YAML workflow を実行し、gate で止め、state を保存して resume する。Harness は registry-mediated API call に対して audit event を発行する。

`semantic-guard` は監査結果そのものの JSON は持つが、監査実行の操作履歴、危険度、確認方法、再開可能な監査 workflow はまだ薄い。

### 5. 対立質問と adversarial review が弱い

Planu の `challenge-spec` 系は、失敗、保安、scale、data consistency、out-of-scope、過去決定との矛盾を攻める。`semantic-guard` にも未決点や反証条件はあるが、体系的な adversarial scenario pack としてはまだ弱い。

## 隣接実装できるもの

### 最優先: external evidence contract

Semgrep / Snyk / coverage / test / workflow gate / Planu readiness などを、監査 core とは別の証拠 report として正規化する共通 schema を作る。

案:

```json
{
  "schema_version": "semantic-guard-external-evidence/v1",
  "source": "semgrep",
  "kind": "security_scan",
  "command_or_reference": "semgrep scan --json",
  "target": "src/...",
  "timestamp": "2026-06-03T00:00:00+09:00",
  "applicability": "applicable",
  "status": "pass",
  "summary": "0 blocking findings",
  "raw_result_reference": "reports/semgrep.json",
  "confidence": "tool_reported",
  "limitations": "Only local ruleset was run"
}
```

これにより、上位 workflow や人間 reviewer は「証拠がある」という語だけでなく、何の証拠か、どの対象か、どの制限かを読める。既存の `finish-check` や `trace-report` は、この schema を自動解釈しない。必要なら利用者が evidence text として要約を渡す。

隣接 report の入力元:

- Semgrep: scan result と finding elicitation。
- Snyk: scan tool profile、trust/auth 状態、output mapper。
- Planu: readiness / quality / gap / coverage result。
- Spec Kit: workflow gate result。
- Harness: operation audit event。

### 高優先: acceptance criteria quality rules

Planu から、受入条件の品質規則を companion report として借りる。

候補:

- Given / When / Then または同等の状況、操作、期待結果があるか。
- 数値、閾値、状態、出力、error code などの観測可能条件があるか。
- file path、function/type、test file など実装具体性が必要な難度で見えているか。
- 入力 validation、error handling、security/auth、rollback、observability、performance、accessibility、edge case の gap があるか。

これは `audit-request` や `audit-plan` の内部規則へ直結しない。別 command が `criteria-quality-report.json` を出し、人間または上位 workflow が必要に応じて監査入力へ要約する。Planu の spec store を輸入する必要はない。

### 高優先: gate suggestion

Spec Kit と Harness から、人間 gate / elicitation の形を借りる。

ただし、`semantic-guard` は自動で accept / reject しない。出すべきは監査結果ではなく、sidecar の gate suggestion report である。

案:

```json
{
  "gate_suggestions": [
    {
      "gate": "before_implementation",
      "reason": "acceptance criteria are missing measurable success conditions",
      "options": ["revise_request", "proceed_with_risk", "defer"],
      "default_recommendation": "revise_request"
    }
  ]
}
```

これなら人間判断境界を保ったまま、Spec Kit の gate 運用を横に置ける。既存の acceptance bundle や finish check へ自動注入しない。

### 高優先: operation audit log

Harness MCP の audit event は、`semantic-guard` 自身にも欲しい。

記録対象:

- CLI / MCP tool 名。
- phase。
- target file。
- input kind。
- strict / profile。
- status。
- finding count。
- duration。
- exit code。
- escalation needed。
- companion artifact references。

目的は利用者監視ではなく、作業の再現性である。JSONL sink でよい。失敗しても監査本体を落とさない failure-isolated sink にする。これは監査結果の採点には使わない。

### 中優先: scanner evidence readers

Semgrep や Snyk の engine を内蔵しない。代わりに JSON 出力を読む reader を作る。

候補:

- `semantic-guard ingest-evidence --kind semgrep --file reports/semgrep.json`
- `semantic-guard ingest-evidence --kind snyk-code --file reports/snyk-code.json`
- `semantic-guard ingest-evidence --kind coverage --file coverage.json`
- `semantic-guard finish-check --evidence-file evidence.json`

これで保安走査器と競合せず、完了証拠の横に置ける。

### 中優先: adversarial scenario pack

Planu の challenge 系を `semantic-guard` 風に圧縮する。

規則候補:

- mutable operation なのに actor / permission が薄い。
- migration / persistence なのに rollback / recovery が薄い。
- list / search / export なのに scale / performance 条件が薄い。
- payment / billing / deploy なのに observability / audit trail が薄い。
- out-of-scope と acceptance criteria が矛盾している。
- 過去の decision / non-goal と今回 plan が衝突している。

これは `audit-request` と `audit-plan` の warning へ直結しない。別 report として出し、LLM reviewer へ投げるか、人間が要求や計画を直す材料にする。

### 中優先: workflow status import

Spec Kit の workflow engine を丸ごと持つ必要は薄い。だが workflow の gate 状態、run id、step status、pause reason を sidecar report として読む価値はある。

`semantic-guard` 側の責務は、「workflow を実行する」ではなく、「workflow がどの gate で止まり、何を人間判断に残したか」を別 artifact として記録すること。

### 低優先: workflow runner

`semantic-guard` 自体に YAML workflow runner を持たせるのは後でよい。実装するなら shell step は最初から入れない方がいい。入れるなら trust model、dry-run、allowlist、audit log が先に要る。

この順序を間違えると、意味監査層だったものが危ない実行器になる。

## 監査 core に取り込むべきでないもの

### vendor scanner engine の内蔵

Semgrep / Snyk の中身を置き換える必要はない。`semantic-guard` は保安走査器を名乗らない方が強い。作るなら結果 reader と evidence schema までで、監査関数には混ぜない。

### release gate 化

自動 block は保安 finding や destructive API 操作なら意味がある。しかし意味監査で自動 release gate を名乗ると、過警告と過少警告の両方で壊れる。

`semantic-guard` は「止める権限」ではなく、「止まるべき理由を見える化する道具」でよい。

### 仕様平台化

Planu のような spec store、interactive clarify session、drift management を丸ごと入れると、`semantic-guard` の境界が太りすぎる。

仕様正本を所有するより、外部正本を監査できる方がよい。

### 早すぎる shell workflow

Spec Kit の shell step は強いが、`semantic-guard` に入れるには危険が増える。まずは sidecar artifact、gate suggestion report、operation audit log、external evidence normalizer が先。

## 導入順

### Phase 1: 外部証拠 sidecar

成果物:

- `schemas/external-evidence.schema.json`
- `src/semantic_guard/companions/external_evidence.py`
- `semantic-guard evidence normalize ...` のような独立 command
- test fixture: Semgrep/Snyk/coverage/readiness 風の最小 JSON

完了条件:

- 外部証拠が target、kind、status、limitation、raw reference として sidecar JSON に残る。
- 証拠なし、非適用、失敗、未実行理由を区別できる。
- 既存の `finish-check` と `trace-report` の出力 schema は変えない。

### Phase 2: 受入条件品質と gap 規則

成果物:

- `criteria_quality.py`
- `gap_rules.py`
- `semantic-guard criteria report ...` のような独立 command
- `criteria-quality-report.json`

完了条件:

- 測定不能な受入条件を警告できる。
- mutable / migration / search / critical operation で必要な gap を提案できる。
- 日本語要求でも最小限動く。
- 既存の `audit-request` と `audit-plan` は変えない。

### Phase 3: gate suggestion と operation audit log

成果物:

- `gate_suggestions` output。
- `audit_events.py`。
- JSONL sink。
- CLI option: `--audit-log <path>` または環境変数。

完了条件:

- 最終判断はなお人間に残る。
- `semantic-guard` 自身の監査実行が再現可能な event として残る。
- audit log sink の失敗が監査本体を落とさない。
- gate suggestion は監査 status や score に影響しない。

### Phase 4: scanner evidence readers

成果物:

- `ingest-evidence` CLI。
- Semgrep JSON reader。
- Snyk JSON reader。
- coverage/test report reader。

完了条件:

- scanner 結果を sidecar evidence として正規化できる。
- scanner 未実行時は「非適用」「未実行」「実行不能」を分ける。
- `semantic-guard` は scanner ではないという境界を保つ。

### Phase 5: adversarial scenario pack

成果物:

- `challenge_rules.py`
- `semantic-guard challenge report ...` のような独立 command。
- `challenge-report.json`

完了条件:

- 決定論規則で拾える gap を、監査結果とは別の report として出す。
- 判別不能なものを reviewer 補助へ回すかは、人間または上位 workflow が決める。

## 採用優先順位

| 優先 | 候補 | 理由 |
| --- | --- | --- |
| 1 | external evidence contract | 他道具の強みを競合せず sidecar 化できる |
| 2 | acceptance criteria quality / gap rules | Planu の強みを監査 core 外の report として使える |
| 3 | gate suggestion | 人間判断境界を保ったまま Spec Kit / Harness の強みを横に置ける |
| 4 | operation audit log | 監査道具自身の再現性が上がるが、採点には混ぜない |
| 5 | scanner evidence readers | Semgrep / Snyk を sidecar evidence として正規化できる |
| 6 | adversarial scenario pack | LLM reviewer に渡す前の材料を増やせる |
| 7 | workflow status import | Spec Kit との連携に効くが、先に証拠 schema が要る |
| 8 | workflow runner | 価値はあるが危険も大きい。最後でいい |

## 実装に入るなら最初の切り口

最初に作るべきは、`companions/external_evidence.py` である。

理由:

- Semgrep / Snyk / Planu / Spec Kit / Harness の全てから sidecar 化できる。
- `semantic-guard` の正体を変えない。
- 既存の監査関数を変えずに、周辺証拠の品質が上がる。
- 将来の scanner reader、coverage reader、gate suggestion、audit log の受け皿にもなる。

最小 API 案:

```python
def normalize_external_evidence(payload: Mapping[str, object]) -> dict[str, object]:
    ...

def summarize_external_evidence(items: Sequence[Mapping[str, object]]) -> dict[str, object]:
    ...
```

最小 CLI 案:

```sh
semantic-guard ingest-evidence --kind generic --file evidence.json
semantic-guard evidence summarize --file evidence.normalized.json
```

この順序なら、`semantic-guard` は「他道具より何でもできる」などという鈍い主張をせずに済む。各道具の勝っている部分を sidecar artifact として扱い、監査 core はそのまま保つ。そこが一番筋がいい。

## 最終評価

`semantic-guard` は、公開同系統の中で「個別実行能力が最強の道具」ではない。

だが、agent 作業の要求、計画、差分、完了、受入判断材料を、外部化された監査対象として扱う点では、かなり明確な位置を持つ。

利点は、コンテキスト外部化を「ただの記録」ではなく「監査可能な義務と証拠の束」へ寄せているところにある。

不利は、各専門 engine に比べて現場証拠の接続が弱いこと。

ならば次の強化は明白である。専門 engine を真似るな。専門 engine の結果を、監査機能とは別の sidecar artifact として実装しろ。これが一番、道具の正体を壊さずに能力を底上げする。
