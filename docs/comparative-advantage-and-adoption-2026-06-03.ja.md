# 比較優位と隣接実装候補2026-06-03

## 目的

この文書は、公開状態で確認できる同系統のMCPサーバ、agent skill、仕様監査・保安走査系の実装を`semantic-guard`と比較し、次を切り分ける。

- `semantic-guard`が相対的に優位な点。
- `semantic-guard`が相対的に不利な点。
- `semantic-guard`の監査機能とは統合せず、隣接実装する価値がある仕組み。
- 監査coreに取り込むべきでない仕組み。

これは宣伝文ではない。`semantic-guard`を保安走査器、仕様平台、workflow実行器、release gate、人間受入判断の代替として扱うための文書でもない。

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

- Snyk、Semgrep、Harnessには公開repositoryから見える範囲外の商用機能がある。ここでは確認できた実装と文書だけを比較する。
- Planuはnpm package展開物から見た比較であり、非公開の運用やhosted featureは評価していない。
- Spec Kitは2026-06-03時点でworkflow engineが追加されており、以前の「command template中心」という評価より強いworkflow面を持つ。

## 結論

`semantic-guard`の優位は、単独領域の専門性ではない。

優位は、要求、計画、差分、完了、受入材料をまたいで、agent作業の意味を外部化し、監査可能なJSONとして残す点にある。

逆に、個別領域では普通に負ける。

- 保安走査はSemgrep / Snykが強い。
- 仕様準備度、受入条件品質、coverage gapはPlanuが強い。
- workflow実行、再開、人間gateは現行Spec Kitが強い。
- 平台操作のaudit log、危険度、elicitationはHarness MCPが強い。

したがって採るべき戦略は、競争ではなく隣接実装である。ただしengineを丸ごと輸入したり、既存の監査相へ直接混ぜたりはしない。外部道具から得られる証拠、規則、境界情報をsidecar artifactとして生成し、必要な時だけ人間または上位workflowが参照する。

この方針では、既存の`audit-request`、`audit-plan`、`audit-diff`、`finish-check`、`trace-report`の出力契約を変えない。追加するのは、監査coreの外側にあるcompanion command、schema、report generatorである。

## `semantic-guard`の現在地

`semantic-guard`は次の相を持つ。

| 相 | 役割 |
| --- | --- |
| `understand-target` | 対象理解の明文化 |
| `audit-request` | 要求、文書、計画、差分要約の入口監査 |
| `audit-plan` | 計画の目的、非目標、成果物、検証、受入、復旧、未決点を見る |
| `audit-diff` | 差分と意図、保安信号、意味境界、公開契約、失敗しやすい操作を見る |
| `finish-check` | 完了要約、検証証拠、受入条件、保安確認、代表実行を見る |
| `trace-report` | request / plan / diff / finish / evidenceの対応とgapを出す |
| `acceptance-review-bundle` | 決定論監査、LLM補助、人間確認点、残留危険を束ねる |

現行実装上の特徴:

- `audit_request`はinput kindを分け、文書、計画、差分要約へ分岐する。
- `audit_plan`は日本語見出しや同義語を含む計画項目を診断する。
- `audit_diff`は保安信号、変更ファイル、意味境界、実装工学信号を出す。
- `finish_check`は検証証拠と受入証拠の欠落を扱う。
- `matching.py`は`match_status`、`confidence`、`nearest_candidates`を持つ。
- `logic.py`はfact、obligation、countercondition、derivationをJSON化する。
- `traceability.py`は複数相をまとめてtrace gapを出す。
- `escalation.py`は決定論監査で判別しにくい候補をdry-runのreviewer補助へ回せる。
- `acceptance_review.py`はLLM reviewにfinal verdictを持たせず、`final_human_decision`を人間境界に残す。

この形は「コンテキストの外部化」に近い。ただし、ただの記憶や思考ログではなく、作業相ごとの義務、証拠、反証条件、人間判断点を構造化する外部化である。

## 比較表

| 対象 | 内部の主機構 | 相手側の強み | `semantic-guard`の優位 | `semantic-guard`の不利 |
| --- | --- | --- | --- | --- |
| Spec Kit | command template、spec / plan / tasks手順、YAML workflow engine、state persistence、human gate | 仕様駆動開発の一連実行、再開、gate、shell/prompt/command step | 特定workflowに縛られず、要求、計画、差分、完了の意味監査を横断できる | workflow実行、resume、gateの運用面は弱い |
| Planu | spec format validator、readiness score、quality score、EARS / BDD、AC gap、coverage gap、drift、challenge-spec | 受入条件の粒度、準備度採点、仕様とtest/codeの対応 | 仕様平台に縛られず、外部成果物やdogfood文書も監査できる。誤警告診断と人間判断境界が濃い | 受入条件の品質採点、coverage gap、drift検出、対立質問が弱い |
| Semgrep | CLI/RPC静的走査、post-tool hook、finding elicitation、既定方針のprompt injection | code入力に対する静的規則照合、agent編集直後のblock、規則集合 | 意味、範囲、検証、完了証拠の監査であり、特定の規則照合に限らない | 実codeへの規則照合能力は持たない。hookによる即時阻止もない |
| Snyk Studio MCP | JSON tool registry、CLI実行、trust/auth確認、output mapper、scan tool profiles | SCA / SAST / IaC / container / SBOM / package healthなどの供給網・保安実行 | vendor非依存で、codeが無い段階の要求や計画も見られる | trust model、auth、scanner adapter、結果正規化は未整備 |
| Harness MCP | registry dispatch、operation policy、risk level、elicitation、structured audit event | 平台API操作の統制、危険度別確認、操作audit log | API操作履歴ではなく、作業成果物の意味と完了証拠を監査できる | `semantic-guard`自身のCLI/MCP呼び出し履歴や危険度記録は薄い |

## 優位性

### 1.相をまたぐ意味の外部化

多くの同系統道具は、どこか一相に強い。

- Spec Kitは仕様駆動workflow。
- Planuは仕様準備度と受入条件。
- Semgrep / Snykはcodeと依存関係の走査。
- HarnessはAPI操作統制。

`semantic-guard`は、要求、計画、差分、完了を別々に扱い、その間のtrace gapを出せる。ここが最も独自に近い。

実装上は、`trace-report`がrequest / plan / diff / finish / evidenceを束ね、監査状態とtrace状態を分ける。単に「その場の回答が妥当か」ではなく、「前に言った目的と後の完了主張がつながっているか」を見られる。

### 2.最終判断を奪わない構造

Semgrepのhookはfindingsが出るとblockできる。Harnessは危険度に応じてelicitationし、条件次第でAPI操作を止める。これは実行統制として正しい。

一方、意味監査で同じことをやると危ない。要求や設計の良否は、文脈、事業判断、受入者の価値判断を含むからだ。

`semantic-guard`は、LLM reviewを補助に留め、`acceptance-review-bundle`の`final_human_decision`を`pending / accept / request_revision / defer`として人間側に残す。この境界は強い。面倒だが健全だ。

### 3.誤警告を監査対象に含める

Planuや走査器はscoreやfindingsを出すが、`semantic-guard`は`nearest_candidates`、`match_status`、`confidence`、`warning_class`、`non_emitted_rules`、logical derivationで「なぜ出たか」「なぜ出なかったか」も出そうとしている。

これはheuristic systemとしては重要である。規則が荒い時、利用者が見るべきなのは警告そのものだけでなく、規則の弱さである。

### 4. codeが無い段階でも効く

Semgrep / Snykはcode、依存、container、IaCが無いと力を出しにくい。Planuは仕様形式があるほど強い。

`semantic-guard`は、まだcodeもテストも無い段階で、要求の達成条件、検証方法、証拠形式、非目標、未決点を要求できる。agent作業ではここが効く。実装前の意味driftは、あとからtestだけで戻せない。

## 不利性

### 1.専門engineが薄い

保安はSemgrep / Snykに勝てない。仕様準備度はPlanuに勝てない。workflow実行はSpec Kitに勝てない。操作監査はHarnessに勝てない。

これは恥ではないが、誤魔化すと破綻する。`semantic-guard`は横断監査層であって、各専門engineの代替ではない。

### 2. scoreが局所較正に留まる

fixtureは役に立つが、任意文書へのprecision / recallを証明しない。Planuのようなreadiness / quality scoreも、Semgrepのようなrule corpusも、Snykのような脆弱性知識基盤もない。

したがって公開時は、fixture pass rateを「任意文書でも同じ品質で判定できる」という主張へ飛躍させてはいけない。

### 3.外部証拠の隣接生成・参照口が未成熟

現在の`finish-check`は「検証したか」「証拠があるか」を見るが、Semgrep JSON、Snyk JSON、coverage report、test report、workflow gate resultなどを、監査coreから独立した証拠reportとして正規化するschemaがまだない。

このせいで、外部道具の強みを「監査の材料」として横に置きにくい。

### 4. workflowと操作監査が弱い

Spec KitはYAML workflowを実行し、gateで止め、stateを保存してresumeする。Harnessはregistry-mediated API callに対してaudit eventを発行する。

`semantic-guard`は監査結果そのもののJSONは持つが、監査実行の操作履歴、危険度、確認方法、再開可能な監査workflowはまだ薄い。

### 5.対立質問とadversarial reviewが弱い

Planuの`challenge-spec`系は、失敗、保安、scale、data consistency、out-of-scope、過去決定との矛盾を攻める。`semantic-guard`にも未決点や反証条件はあるが、体系的なadversarial scenario packとしてはまだ弱い。

## 隣接実装できるもの

### 最優先: external evidence contract

Semgrep / Snyk / coverage / test / workflow gate / Planu readinessなどを、監査coreとは別の証拠reportとして正規化する共通schemaを作る。

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

これにより、上位workflowや人間reviewerは「証拠がある」という語だけでなく、何の証拠か、どの対象か、どの制限かを読める。既存の`finish-check`や`trace-report`は、このschemaを自動解釈しない。必要なら利用者がevidence textとして要約を渡す。

隣接reportの入力元:

- Semgrep: scan resultとfinding elicitation。
- Snyk: scan tool profile、trust/auth状態、output mapper。
- Planu: readiness / quality / gap / coverage result。
- Spec Kit: workflow gate result。
- Harness: operation audit event。

### 高優先: acceptance criteria quality rules

Planuから、受入条件の品質規則をcompanion reportとして借りる。

候補:

- Given / When / Thenまたは同等の状況、操作、期待結果があるか。
- 数値、閾値、状態、出力、error codeなどの観測可能条件があるか。
- file path、function/type、test fileなど実装具体性が必要な難度で見えているか。
- 入力validation、error handling、security/auth、rollback、observability、performance、accessibility、edge caseのgapがあるか。

これは`audit-request`や`audit-plan`の内部規則へ直結しない。別commandが`criteria-quality-report.json`を出し、人間または上位workflowが必要に応じて監査入力へ要約する。Planuのspec storeを輸入する必要はない。

### 高優先: gate suggestion

Spec KitとHarnessから、人間gate / elicitationの形を借りる。

ただし、`semantic-guard`は自動でaccept / rejectしない。出すべきは監査結果ではなく、sidecarのgate suggestion reportである。

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

これなら人間判断境界を保ったまま、Spec Kitのgate運用を横に置ける。既存のacceptance bundleやfinish checkへ自動注入しない。

### 高優先: operation audit log

Harness MCPのaudit eventは、`semantic-guard`自身にも欲しい。

記録対象:

- CLI / MCP tool名。
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

目的は利用者監視ではなく、作業の再現性である。JSONL sinkでよい。失敗しても監査本体を落とさないfailure-isolated sinkにする。これは監査結果の採点には使わない。

### 中優先: scanner evidence readers

SemgrepやSnykのengineを内蔵しない。代わりにJSON出力を読むreaderを作る。

候補:

- `semantic-guard ingest-evidence --kind semgrep --file reports/semgrep.json`
- `semantic-guard ingest-evidence --kind snyk-code --file reports/snyk-code.json`
- `semantic-guard ingest-evidence --kind coverage --file coverage.json`
- `semantic-guard finish-check --evidence-file evidence.json`

これで保安走査器と競合せず、完了証拠の横に置ける。

### 中優先: adversarial scenario pack

Planuのchallenge系を`semantic-guard`風に圧縮する。

規則候補:

- mutable operationなのにactor / permissionが薄い。
- migration / persistenceなのにrollback / recoveryが薄い。
- list / search / exportなのにscale / performance条件が薄い。
- payment / billing / deployなのにobservability / audit trailが薄い。
- out-of-scopeとacceptance criteriaが矛盾している。
- 過去のdecision / non-goalと今回planが衝突している。

これは`audit-request`と`audit-plan`のwarningへ直結しない。別reportとして出し、LLM reviewerへ投げるか、人間が要求や計画を直す材料にする。

### 中優先: workflow status import

Spec Kitのworkflow engineを丸ごと持つ必要は薄い。だがworkflowのgate状態、run id、step status、pause reasonをsidecar reportとして読む価値はある。

`semantic-guard`側の責務は、「workflowを実行する」ではなく、「workflowがどのgateで止まり、何を人間判断に残したか」を別artifactとして記録すること。

### 低優先: workflow runner

`semantic-guard`自体にYAML workflow runnerを持たせるのは後でよい。実装するならshell stepは最初から入れない方がいい。入れるならtrust model、dry-run、allowlist、audit logが先に要る。

この順序を間違えると、意味監査層だったものが危ない実行器になる。

## 監査coreに取り込むべきでないもの

### vendor scanner engineの内蔵

Semgrep / Snykの中身を置き換える必要はない。`semantic-guard`は保安走査器を名乗らない方が強い。作るなら結果readerとevidence schemaまでで、監査関数には混ぜない。

### release gate化

自動blockは保安findingやdestructive API操作なら意味がある。しかし意味監査で自動release gateを名乗ると、過警告と過少警告の両方で壊れる。

`semantic-guard`は「止める権限」ではなく、「止まるべき理由を見える化する道具」でよい。

### 仕様平台化

Planuのようなspec store、interactive clarify session、drift managementを丸ごと入れると、`semantic-guard`の境界が太りすぎる。

仕様正本を所有するより、外部正本を監査できる方がよい。

### 早すぎるshell workflow

Spec Kitのshell stepは強いが、`semantic-guard`に入れるには危険が増える。まずはsidecar artifact、gate suggestion report、operation audit log、external evidence normalizerが先。

## 導入順

### Phase 1: 外部証拠sidecar

成果物:

- `schemas/external-evidence.schema.json`
- `src/semantic_guard/companions/external_evidence.py`
- `semantic-guard evidence normalize ...`のような独立command
- test fixture: Semgrep/Snyk/coverage/readiness風の最小JSON

完了条件:

- 外部証拠がtarget、kind、status、limitation、raw referenceとしてsidecar JSONに残る。
- 証拠なし、非適用、失敗、未実行理由を区別できる。
- 既存の`finish-check`と`trace-report`の出力schemaは変えない。

### Phase 2: 受入条件品質とgap規則

成果物:

- `criteria_quality.py`
- `gap_rules.py`
- `semantic-guard criteria report ...`のような独立command
- `criteria-quality-report.json`

完了条件:

- 測定不能な受入条件を警告できる。
- mutable / migration / search / critical operationで必要なgapを提案できる。
- 日本語要求でも最小限動く。
- 既存の`audit-request`と`audit-plan`は変えない。

### Phase 3: gate suggestionとoperation audit log

成果物:

- `gate_suggestions` output。
- `audit_events.py`。
- JSONL sink。
- CLI option: `--audit-log <path>`または環境変数。

完了条件:

- 最終判断はなお人間に残る。
- `semantic-guard`自身の監査実行が再現可能なeventとして残る。
- audit log sinkの失敗が監査本体を落とさない。
- gate suggestionは監査statusやscoreに影響しない。

### Phase 4: scanner evidence readers

成果物:

- `ingest-evidence` CLI。
- Semgrep JSON reader。
- Snyk JSON reader。
- coverage/test report reader。

完了条件:

- scanner結果をsidecar evidenceとして正規化できる。
- scanner未実行時は「非適用」「未実行」「実行不能」を分ける。
- `semantic-guard`はscannerではないという境界を保つ。

### Phase 5: adversarial scenario pack

成果物:

- `challenge_rules.py`
- `semantic-guard challenge report ...`のような独立command。
- `challenge-report.json`

完了条件:

- 決定論規則で拾えるgapを、監査結果とは別のreportとして出す。
- 判別不能なものをreviewer補助へ回すかは、人間または上位workflowが決める。

## 採用優先順位

| 優先 | 候補 | 理由 |
| --- | --- | --- |
| 1 | external evidence contract | 他道具の強みを競合せずsidecar化できる |
| 2 | acceptance criteria quality / gap rules | Planuの強みを監査core外のreportとして使える |
| 3 | gate suggestion | 人間判断境界を保ったままSpec Kit / Harnessの強みを横に置ける |
| 4 | operation audit log | 監査道具自身の再現性が上がるが、採点には混ぜない |
| 5 | scanner evidence readers | Semgrep / Snykをsidecar evidenceとして正規化できる |
| 6 | adversarial scenario pack | LLM reviewerに渡す前の材料を増やせる |
| 7 | workflow status import | Spec Kitとの連携に効くが、先に証拠schemaが要る |
| 8 | workflow runner | 価値はあるが危険も大きい。最後でいい |

## 実装に入るなら最初の切り口

最初に作るべきは、`companions/external_evidence.py`である。

理由:

- Semgrep / Snyk / Planu / Spec Kit / Harnessの全てからsidecar化できる。
- `semantic-guard`の正体を変えない。
- 既存の監査関数を変えずに、周辺証拠の品質が上がる。
- 将来のscanner reader、coverage reader、gate suggestion、audit logの受け皿にもなる。

最小API案:

```python
def normalize_external_evidence(payload: Mapping[str, object]) -> dict[str, object]:
    ...

def summarize_external_evidence(items: Sequence[Mapping[str, object]]) -> dict[str, object]:
    ...
```

最小CLI案:

```sh
semantic-guard ingest-evidence --kind generic --file evidence.json
semantic-guard evidence summarize --file evidence.normalized.json
```

この順序なら、`semantic-guard`は「他道具より何でもできる」などという鈍い主張をせずに済む。各道具の勝っている部分をsidecar artifactとして扱い、監査coreはそのまま保つ。そこが一番筋がいい。

## 最終評価

`semantic-guard`は、公開同系統の中で「個別実行能力が最強の道具」ではない。

だが、agent作業の要求、計画、差分、完了、受入判断材料を、外部化された監査対象として扱う点では、かなり明確な位置を持つ。

利点は、コンテキスト外部化を「ただの記録」ではなく「監査可能な義務と証拠の束」へ寄せているところにある。

不利は、各専門engineに比べて現場証拠の接続が弱いこと。

ならば次の強化は明白である。専門engineを真似るな。専門engineの結果を、監査機能とは別のsidecar artifactとして実装しろ。これが一番、道具の正体を壊さずに能力を底上げする。
