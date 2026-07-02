# Acceptance Review Bundle

`acceptance_review_bundle`は、最終成果物を人が評価するための束である。LLM reviewerの出力、決定的監査、採用した補填、採用しなかった補填、実行証拠、残リスク、人が見るべき判断点を一つに集める。

## Purpose

中途監査は不足を見つけるためにある。最終判断は人が行う。そのため、最後に必要なのは「LLMの承認」ではなく、人が`accept`、`request_revision`、`defer`を選べるだけの材料である。

`acceptance_review_bundle`はこの最終評価点に使うJSON束を作る。Codexはbundleを生成し、証拠、残リスク、人間判断点を別fieldへ入れる。人が判断するまでは`final_human_decision.status`は`pending`のままにする。

## Audience And Use

この文書の利用者は、Codex作業の最終成果物を受け取る人間と、bundleを作るCodex側である。

使う時点は、要求監査、計画監査、差分監査、完了確認、LLM中途査読が終わり、最終成果物を人が受け入れるかどうかを判断する直前である。中間工程の承認には使わない。

## Scope

acceptance review bundleに含める項目。

- 元要求。
- 最終成果物の種類、参照、要約。
- deterministic auditの結果。
- 必要に応じて`finding.derivation`や`details.logical_trace`の要約。
- LLM reviewerの不足指摘、補填案、rule点検、人間判断点。
- Codexが採用した補填。
- Codexが採用しなかった補填と理由。
- Codexが保留した補填と必要な判断。
- 実行証拠。
- 残リスク。
- 人が見るべき最終判断点。
- 人の最終判断欄。

acceptance review bundleに含めない項目。

- LLMによる最終承認。
- LLM出力の自動採用。
- derivation recordだけに基づく最終承認。
- 人間判断の代行。
- 実行証拠のない完成主張。

## Schema

schemaは`schemas/acceptance-review-bundle.schema.json`に置く。

`schema_version`は`acceptance-review-bundle/v1`である。

`final_human_decision.status`は次のいずれか。

- `pending`: `decided_by`、`decided_at`、`rationale`がまだ空で、人が最終判断を記録していない状態。
- `accept`: 現成果物を受け入れる。
- `request_revision`: 修正を求める。
- `defer`: 判断を保留する。

`accept`、`request_revision`、`defer`を入れる場合は、`decided_by`、`decided_at`、`rationale`を空にしない。`pending`の間は空文字でよい。

`finding.derivation`と`details.logical_trace`はdeterministic audit materialとしてbundleへ入れる。これらは、抽出factと規則述語からfindingがどう導かれたかを説明するだけである。自然言語本文の真偽、成果物の危険有無、受入済み状態、人間が`accept`すべきかどうかは示さない。

## CLI

schemaを出す。

```sh
uv run --python 3.13 --project . \
  semantic-guard acceptance-bundle-schema
```

bundle scaffoldを作る。

```sh
uv run --python 3.13 --project . \
  semantic-guard acceptance-bundle-template --file bundle-input.json
```

strict検証をする。

```sh
uv run --python 3.13 --project . \
  semantic-guard validate-acceptance-bundle --file acceptance-bundle.json
```

scaffoldの形だけを見る時は`--no-strict`を使う。strictでは、少なくとも一つのdeterministic audit、execution evidence、human review pointが必要になる。

## MCP Tools

MCP serverには次を追加する。

- `acceptance_bundle_template_tool`
- `validate_acceptance_bundle_tool`

LLM reviewer側もMCPから呼べる。

- `llm_review_command_tool`: prompt、schema path、`codex exec` commandをJSON objectに返すだけで実行しない。
- `llm_review_run_tool`: 既定はdry-run。`execute=true`の時だけ`codex exec`を起動する。

MCP toolでは任意の`codex_binary`は受け取らない。実行入口を増やす以上、ここを開けると監査機構が雑な実行器になる。馬鹿げているのでやらない。

## Example

```json
{
  "original_request": "exec reviewerと最終人間監査bundleを実装する。",
  "final_artifact": {
    "kind": "code",
    "reference": "src/semantic_guard/acceptance_review.py",
    "summary": "acceptance review bundleの生成と検証を追加した。"
  },
  "deterministic_audits": [
    {
      "phase": "finish_check",
      "status": "pass",
      "summary": "試験と証拠が揃っている。",
      "findings": []
    }
  ],
  "execution_evidence": [
    {
      "kind": "test",
      "command_or_reference": "python -m unittest discover -s tests -v",
      "result": "OK",
      "passed": true
    }
  ],
  "human_review_points": [
    {
      "question": "この成果物を受け入れるか。",
      "why_it_matters": "最終合否は人が決めるため。",
      "options": ["accept", "request_revision", "defer"]
    }
  ]
}
```

この入力は`acceptance-bundle-template`でschema上のbundle形に展開できる。strict検証に通すには、監査結果、実行証拠、人間判断点を実際の作業に合わせて埋める。
