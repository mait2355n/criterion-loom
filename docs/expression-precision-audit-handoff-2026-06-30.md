# Expression Precision Audit Handoff

Created: 2026-06-30 JST

## Purpose

この文書は、表現精度監査を`semantic-guard`本体へ組み込む前に、ここまで決めたことと停止条件を残すための再開用記録である。

作業再開時は、先に公開済みrepository、手元の`<local-semantic-guard-checkout>`、CORE上の公開候補を統合する。その後で、この文書を読み直して実装へ進む。

## Current State

まだ実装しない。

理由:

- 公開されているもの、手元にあるもの、CORE上の公開候補が一致しているとは限らない。
- CORE側の候補`<previous-shared-public-candidate>`は、現利用者から書き込めない状態だった。
- どのtreeに機能を入れたのか分からない状態を避ける必要がある。

再開時の最初の作業は、実装ではなくrepository統合である。

## Accepted Direction

この機能は、公開文言だけを対象にしない。

ただし、一般的な文章校正や文体改善でもない。対象は、文書中の表現から対象、操作、出力形式、判断主体、用途を読者が復元できるかである。

短く言えば、これは「表現精度監査」である。

悪い例:

```text
怪しい場所を試験できる内容として外に出す。
```

この文では、次が読めない。

- 何が「怪しい場所」なのか。
- 何を「試験できる」のか。
- 「内容」とは何の形式なのか。
- どこへ「外に出す」のか。
- 誰が判断または試験するのか。

より良い例:

```text
不明点を抽出し、外部での判断に使える一覧として返す。
```

この文では、少なくとも対象は「不明点」、操作は「抽出」、出力形式は「一覧」、用途は「外部での判断」と読める。

## Feature Boundary

この機能が見るもの:

- 対象語の曖昧さ。
- 操作語の曖昧さ。
- 効用語の曖昧さ。
- 出力形式の欠落。
- 判断主体の欠落。
- 修正先の欠落。

この機能が見ないもの:

- 文体の美しさ。
- 文法校正。
- 自動書き換え。
- 一般的な自然言語理解の正しさ。
- 法務、保安、公開可否、最終受入の判断。
- すべての曖昧さの排除。

許容する曖昧さはある。警告すべきなのは、作業、判断、検証、公開、引継ぎに必要な操作像が復元できない表現である。

## Candidate Placement

`semantic-guard`本体に組み込む。

初版では新しいCLI commandやMCP toolを増やさない。既存の`audit-conventions --kind document`と`audit_conventions_tool`に載せる。

理由:

- 既存の`audit-conventions`は文書、規約、公開面、出力契約を警告主体で扱う。
- 既存の`AuditResult`形を再利用できる。
- 初版から公開面を増やすと、統合と文書更新の負担が増える。
- 挙動が固まれば、後で`audit-expression`や`audit-document`として昇格できる。

出力診断は`details.expression_precision`に置く案が自然である。

## Candidate Rule IDs

候補rule id:

- `doc.expression.target_blurred`
- `doc.expression.operation_blurred`
- `doc.expression.utility_blurred`
- `doc.expression.output_form_missing`
- `doc.expression.decision_actor_missing`
- `doc.expression.revision_target_missing`

初版ではblockerにしない。`minor`または`major` warningとして返す。

## Detector Sketch

初版は決定論でよい。LLM解析や深い日本語構文解析へ入らない。

検出方針:

1. 文を行または短い窓に分ける。
2. 曖昧な対象語、操作語、効用語を検出する。
3. 近傍に支え語があるかを見る。
4. 支え語が無い場合だけ`doc.expression.*`を出す。
5. 明示的な悪い例、避ける例、引用例は抑制する。

例の曖昧語:

- 対象語: `怪しい場所`, `内容`, `材料`, `もの`, `それ`, `問題点`
- 操作語: `出す`, `外に出す`, `扱う`, `活用する`, `対応する`, `見える化する`
- 効用語: `試験できる`, `判断できる`, `改善できる`, `使える`

例の支え語:

- 対象支え語: `不明点`, `差分`, `要求`, `計画`, `指摘`, `候補`, `診断`
- 操作支え語: `抽出`, `返す`, `記録`, `分類`, `列挙`, `検出`
- 出力支え語: `JSON`, `一覧`, `監査結果`, `finding`, `diagnostics`, `fixture`
- 判断支え語: `人間`, `外部判断`, `保守者`, `最終判断`, `accept`, `request_revision`, `defer`

## Implementation Notes

実装時の最小差分:

1. `src/semantic_guard/conventions.py`に表現精度detector helperを追加する。
2. `audit_conventions`の中で既存規約findingsに加えて表現精度findingsを足す。
3. `details.expression_precision`に検出語、支え語、抑制文脈、発火rule idを入れる。
4. `docs/conventions/base-contract.json`か別catalogに`doc.expression.*`を露出する。
5. `rule-detector-map`が対応を返すようにする。
6. `tests/test_conventions.py`に悪例、良例、抑制例を追加する。

注意:

- `doc.expression.*`を既存の`required_groups`汎用処理へそのまま流すと誤検知しやすい。
- `detector: expression_precision`のような印をcatalogに置き、専用helperで処理する方がよい。
- 初版は修正文生成をしない。`suggested_fix`には「対象、操作、出力形式、判断主体を明示する」程度を書く。

## Test Cases

最低限ほしい試験:

- `怪しい場所を試験できる内容として外に出す。`は警告する。
- `不明点を抽出し、外部での判断に使える一覧として返す。`は通す、または`外部`の判断主体だけ軽く警告する。
- `不明点を抽出し、人間の最終判断に使えるJSONの一覧として返す。`は通す。
- `問題点を見える化する。`は警告する。
- `問題点を分類し、監査結果のfindingsとして返す。`は通す。
- `この文は悪い例: 怪しい場所を試験できる内容として外に出す。`は、悪い例として抑制する。

## Reconciliation Before Implementation

実装前に必ず行うこと:

1. 公開済みrepositoryの最新状態を確認する。
2. `<local-semantic-guard-checkout>`の状態を確認する。
3. CORE上の公開候補を確認する。
4. 差分を分類する。
   - 公開済みにある差分。
   - 手元にだけある差分。
   - CORE候補にだけある差分。
   - 生成物や捨ててよい差分。
   - 権限や環境由来の差分。
5. 統合先を一つ決める。
6. 統合後にdoctor、unit test、fixture evaluationを走らせる。

## Verification Commands

統合後、実装前:

```sh
uv run --python 3.13 --project . semantic-guard doctor
uv run --python 3.13 --project . semantic-guard evaluate-fixtures
uv run --python 3.13 --project . python -m unittest tests.test_conventions
```

実装後:

```sh
uv run --python 3.13 --project . python -m compileall src/semantic_guard tests
uv run --python 3.13 --project . python -m unittest discover -s tests
uv run --python 3.13 --project . semantic-guard evaluate-fixtures
uv run --python 3.13 --project . semantic-guard doctor
uv run --python 3.13 --project . semantic-guard audit-conventions --kind document --text "怪しい場所を試験できる内容として外に出す。"
uv run --python 3.13 --project . semantic-guard audit-conventions --kind document --text "不明点を抽出し、人間の最終判断に使えるJSONの一覧として返す。"
uv run --python 3.13 --project . semantic-guard rule-detector-map
uv run --python 3.13 --project . semantic-guard conventions-catalog
```

## Done When

この機能の初版は、次を満たした時に完了とする。

- 公開済み、手元、CORE候補の統合先が明確である。
- `doc.expression.*`が`audit-conventions --kind document`から返る。
- 悪例と良例のunit testがある。
- `details.expression_precision`で検出理由を追える。
- `rule-detector-map`または`conventions-catalog`から規則が見える。
- `doctor`と既存fixture evaluationが悪化しない。
- 公開文書では、この機能を文体校正、法務判断、保安判断、最終受入判断として説明していない。
