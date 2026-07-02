# Acceptance Review Bundle

`acceptance_review_bundle` は、最終成果物を人が評価するための束である。LLM reviewer の出力、決定的監査、採用した補填、採用しなかった補填、実行証拠、残リスク、人が見るべき判断点を一つに集める。

## Purpose

中途監査は不足を見つけるためにある。最終判断は人が行う。そのため、最後に必要なのは「LLMの承認」ではなく、人が `accept`、`request_revision`、`defer` を選べるだけの材料である。

`acceptance_review_bundle` はこの最終評価点を作る。Codex は bundle を生成し、証拠と残リスクを埋め、人が見るべき判断点を分離する。人が判断するまでは `final_human_decision.status` は `pending` のままにする。

## Audience And Use

この文書の利用者は、Codex 作業の最終成果物を受け取る人間と、bundle を作る Codex 側である。

使う時点は、要求監査、計画監査、差分監査、完了確認、LLM中途査読が終わり、最終成果物を人が受け入れるかどうかを判断する直前である。中間工程の承認には使わない。

## Scope

acceptance review bundle に含める項目。

- 元要求。
- 最終成果物の種類、参照、要約。
- deterministic audit の結果。
- 必要に応じて `finding.derivation` や `details.logical_trace` の要約。
- LLM reviewer の不足指摘、補填案、rule点検、人間判断点。
- Codex が採用した補填。
- Codex が採用しなかった補填と理由。
- Codex が保留した補填と必要な判断。
- 実行証拠。
- 残リスク。
- 人が見るべき最終判断点。
- 人の最終判断欄。

acceptance review bundle に含めない項目。

- LLM による最終承認。
- LLM 出力の自動採用。
- derivation record だけに基づく最終承認。
- 人間判断の代行。
- 実行証拠のない完成主張。

## Schema

schema は `schemas/acceptance-review-bundle.schema.json` に置く。

`schema_version` は `acceptance-review-bundle/v1` である。

`final_human_decision.status` は次のいずれか。

- `pending`: まだ人が判断していない。
- `accept`: 現成果物を受け入れる。
- `request_revision`: 修正を求める。
- `defer`: 判断を保留する。

`accept`、`request_revision`、`defer` を入れる場合は、`decided_by`、`decided_at`、`rationale` を空にしない。`pending` の間は空文字でよい。

`finding.derivation` と `details.logical_trace` は deterministic audit material として扱う。これらは、抽出 fact と規則述語から finding がどう導かれたかを説明するだけである。自然言語本文の真偽、成果物の危険有無、受入済み状態、人間が `accept` すべきかどうかは示さない。

## CLI

schema を出す。

```sh
uv run --python 3.13 --project . \
  semantic-guard acceptance-bundle-schema
```

bundle scaffold を作る。

```sh
uv run --python 3.13 --project . \
  semantic-guard acceptance-bundle-template --file bundle-input.json
```

strict 検証をする。

```sh
uv run --python 3.13 --project . \
  semantic-guard validate-acceptance-bundle --file acceptance-bundle.json
```

scaffold の形だけを見る時は `--no-strict` を使う。strict では、少なくとも一つの deterministic audit、execution evidence、human review point が必要になる。

## MCP Tools

MCP server には次を追加する。

- `acceptance_bundle_template_tool`
- `validate_acceptance_bundle_tool`

LLM reviewer 側も MCP から呼べる。

- `llm_review_command_tool`: prompt、schema path、`codex exec` command を JSON object に返すだけで実行しない。
- `llm_review_run_tool`: 既定は dry-run。`execute=true` の時だけ `codex exec` を起動する。

MCP tool では任意の `codex_binary` は受け取らない。実行入口を増やす以上、ここを開けると監査機構が雑な実行器になる。馬鹿げているのでやらない。

## Example

```json
{
  "original_request": "exec reviewer と最終人間監査bundleを実装する。",
  "final_artifact": {
    "kind": "code",
    "reference": "src/semantic_guard/acceptance_review.py",
    "summary": "acceptance review bundle の生成と検証を追加した。"
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

この入力は `acceptance-bundle-template` でschema上のbundle形に展開できる。strict 検証に通すには、監査結果、実行証拠、人間判断点を実際の作業に合わせて埋める。
