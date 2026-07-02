# Fixture Record Design

`semantic-guard`のfixtureは、単なる入力例ではなく「壊してはいけない局所整合性」を記録するための実行可能な文書である。

## Purpose

監査規則は経験的に育つ。だから全文の丸ごと一致でgolden JSONを固定すると、改善のたびに壊れる。一方で固定が無いと、過剰警告、警告漏れ、文書種別の取り違え、完了証拠の見逃しが再発する。

このfixture層は、出力全体ではなく意味上の不変条件だけを検査する。

## When To Use

fixture recordは、監査規則を変更する開発者、fixtureを追加する保守者、監査結果の変化を読む利用者のために使う。実地利用で見つけた誤警告、警告漏れ、過剰なblockingを、再発させたくない局所整合性として固定する時に使う。

## Record Pair

各fixtureは二つのファイルで構成する。

- 入力本文: 監査対象の要求、計画、文書、差分要約、完了要約。
- `*.expected.json`: その入力で守るべき期待値と、なぜ固定するかを記録する文書。

期待値ファイルは標準`json`だけで読める形にする。外部依存を増やさないため、YAMLは使わない。

## Expected JSON Fields

- `id`: 安定したfixture識別子。
- `title`: 人が読める短い題名。
- `phase`: `understand_target`, `audit_request`, `audit_plan`, `audit_diff`, `finish_check`のいずれか。
- `kind`: 必要な場合の入力種別。例: `document`, `requirement`, `plan`, `diff-summary`。
- `input`: 同じディレクトリにある入力本文ファイル。
- `intent`, `request`, `context`, `evidence`: phaseに応じた補助入力。
- `strict`: strict modeの有無。省略時は`true`。
- `rationale`: このfixtureが固定する監査上の意味。
- `expect`: 実行結果に対する部分一致の期待値。

## Assertion Policy

検査器は次を確認する。

- `status`と`phase`の一致。
- `findings[].category`のinclude / exclude。
- `missing`のinclude / exclude。
- `details`の必要項目。
- `details.claim_triples`配列の各recordに含まれるclaim / evidence / limitationのsubstring match。
- `score`の上下限。
- `labels.expected_findings` / `labels.forbidden_findings`による局所true positive / false positive検査。
- `labels.expected_rules` / `labels.forbidden_rules`によるrule id単位の局所検査。
- `derivation_status`, `derivation_rule_id`, `derivation_missing_obligation`, `derivation_countercondition`, `derivation_fact`, `logical_trace_rule`, `logical_trace_summary_rule`, `logical_trace_unknown`, `logical_trace_conflict`による論理監査sliceの部分一致。

検査器はfinding数、全文、scoreの丸ごと一致を既定では見ない。これらは監査規則の改善で自然に変わるため、退行検出の軸として弱い。
`warning_class`、`nearest_candidates`、`semantic_boundaries`は通常の単体試験側で固定する。fixtureでは、複数の局所整合性を一つの期待値へ詰めすぎない。

`evaluate-fixtures`は`rule_catalog_coverage`も返す。`rule_catalog_coverage`はrule catalogとfixture labelの局所対応表であり、`unhit_rule_ids`はfixture rule labelがまだ触れていない規則を示す。`rule_catalog_coverage`は統計的な網羅率ではなく、fixture追加の作業台である。

derivation系の期待値も同じく局所退行検査である。`derivation_rule_hits`, `derivation_status_hits`, `logical_trace_rule_hits`, `logical_trace_summary_rule_hits`はfixture行で見えた値の件数であり、任意の入力に対する統計的な精度、再現率、証明能力を表さない。

`logical_trace_summary_rule`はfull traceより優先して使う退行検査の軸である。規則ごとの`rule_id`、`status`、`finding_count`、`missing_obligation_count`などの小さい投影だけを見る。full `logical_trace_rule`は代表例や互換性確認に留め、fact excerptやderivation step全体のような肥大しやすい細部をfixtureの主軸にしない。

## Current Coverage

現行fixtureは次を固定している。

- 文書監査で、良いREADME形の文書が要求監査用の警告を受けないこと。
- 強い完成度、安全性、完全性主張が証拠や制限なしに通らないこと。
- 曖昧な速度改善要求が、目的と検証経路なしに通らないこと。
- 曖昧な速度改善要求に対して、`req.verifiability.acceptance_missing`のderivationとlogical traceが付くこと。
- 一般的な確認文言だけの要求に対して、`req.verification.method_detail_missing`のderivationが付き、`req.verifiability.acceptance_missing`のfindingは出ないこと。
- 第三規則以降の第一束として、`req.achievement.criteria_missing`, `req.evidence.artifact_missing`, `req.acceptance.rejection_condition_missing`, `req.context.scenario_missing`, `req.structure.observable_behavior_missing`のsummary-rule期待値が代表fixtureで固定されていること。
- 十分に構造化された計画が通ること。
- `command`という語だけで`security` categoryへ落ちないこと。
- `diff-summary`の自然文要約から、変更文脈にある代表的なファイルパスを`details.changed_files`へ拾えること。
- `audit-diff`の意味境界evidenceが、単語や文の途中で不自然に始まる断片へ退化しないこと。
- 長い文書evidence snippetが、壊れたコード柵や不自然な固定長断片へ退化しないこと。
- 完了主張だけでは完了扱いにしないこと。
- boundedな `監査全体を確認する` 計画が、作業分解、対象外、順序、検証、変更統制を持つ場合にbroad-scope警告へ落ちないこと。
- bounded work-package requestがatomicity / priorityの過剰警告へ落ちないこと。
- docs-onlyの証拠追記diffがsemantic evidence mutationとして扱われないこと。
- 日本語の同義見出し、欠落候補、警告分類、意味境界名は単体試験で固定している。

## Adding A Fixture

新しいfixtureは、規則の細部ではなく守るべき意味を先に書く。

1. 入力本文を最小化する。
2. `rationale`に固定したい局所整合性を書く。
3. `expect.categories`と`expect.missing`で、必要な警告と出してはいけない警告を指定する。
4. 文書監査では必要に応じて`claim_triples`を指定する。
5. 特定の規則を固定したい場合は`labels.expected_rules`または`labels.forbidden_rules`を使う。
6. derivation形状を固定したい場合は`derivation_status`, `derivation_rule_id`, `derivation_missing_obligation`, `derivation_countercondition`, `derivation_fact`, `logical_trace_summary_rule`を最小限だけ使う。full traceの互換性を見る場合だけ`logical_trace_rule`を使う。
7. finding数や全文一致で縛らない。

最小の期待値は次の形にする。

```json
{
  "id": "REQ-EXAMPLE-001",
  "phase": "audit_request",
  "kind": "requirement",
  "input": "example.md",
  "rationale": "曖昧な要求を、検証経路なしに通さない。",
  "expect": {
    "status": "block",
    "categories": {
      "includes": ["verifiability"]
    },
    "missing": {
      "includes": ["verification_or_acceptance"]
    }
  }
}
```

rule idまで固定したい場合は次のように書く。

```json
{
  "labels": {
    "expected_rules": ["req.verifiability.acceptance_missing"],
    "forbidden_rules": ["diff.security.sensitive_surface_change"]
  }
}
```

derivation形状まで固定したい場合は次のように書く。

```json
{
  "expect": {
    "status": "block",
    "derivation_status": "derived",
    "derivation_rule_id": "req.verifiability.acceptance_missing",
    "derivation_missing_obligation": "obl.req.verifiability.verification_or_acceptance",
    "derivation_countercondition": "ctr.req.verifiability.input_kind_not_requirement",
    "derivation_fact": "text.has_verification_language",
    "logical_trace_summary_rule": {
      "rule_id": "req.verifiability.acceptance_missing",
      "status": "derived",
      "finding_count": 1
    }
  }
}
```

## Limits

この方式は退行検出であり、正しさの証明ではない。derivation期待値も「その局所fixtureで導出形が崩れていない」ことを示すだけで、自然言語要求が真であること、意味的に満たされたこと、人間が受け入れるべきことは示さない。未知の失敗様式はfixture化されるまで検出できない。実地利用で見つけた誤警告、警告漏れ、過剰なblockingをfixtureに落とすことで精度を上げる。
