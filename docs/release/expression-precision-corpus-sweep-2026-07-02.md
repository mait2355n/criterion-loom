# Expression Precision Corpus Sweep 2026-07-02

## Purpose

This file records one local expression-precision corpus sweep.

Evidence source: `docs/release/expression-precision-corpus-sweep-2026-07-02.raw.json`.

Limit: the tables below are not accuracy, precision, or recall claims. Use them
only as maintenance material for threshold design and fixture additions.

## Audience And Use

This note is for maintainers tuning expression-precision thresholds, adding
fixtures, or reviewing false positives and false negatives. The representative
finding tables quote audit findings as calibration evidence; those quoted rows
are not maintained prose that must pass the expression-precision detector.

## Scope

- Root: repository root at run time; absolute local path intentionally omitted for publication hygiene.
- Included suffixes: `.adoc, .md, .rst, .txt`
- Excluded parts: `.git, .hg, .mypy_cache, .pytest_cache, .ruff_cache, .svn, .tox, .venv, __pycache__, build, dist, node_modules, venv`
- Audited files: 77 total / 51 primary / 26 backup
- Errors: 0
- Raw data: `docs/release/expression-precision-corpus-sweep-2026-07-02.raw.json`
- Run timestamp: `2026-07-02T08:06:53+09:00`
- Decision basis: `primary`; `.backups` is supplemental only.

## Reproduction Command

Run the corpus sweep from the repository root after dependencies are available:

```sh
uv run --python 3.13 --project . semantic-guard audit-conventions --kind document --file README.ja.md
uv run --python 3.13 --project . semantic-guard evaluate-fixtures
uv run --python 3.13 --project . python -m json.tool docs/release/expression-precision-corpus-sweep-2026-07-02.raw.json
```

## Aggregate By Scope

| Metric | All | Primary | Backup |
| --- | ---: | ---: | ---: |
| Audited files | 77 | 51 | 26 |
| Files with expression surface | 28 | 21 | 7 |
| Files with `doc.expression.*` findings | 22 | 17 | 5 |
| Total `doc.expression.*` findings | 103 | 77 | 26 |
| Findings per audited file | 1.3377 | 1.5098 | 1.0 |
| File finding ratio | 28.57% | 33.33% | 19.23% |
| Total referent resolutions | 83 | 61 | 22 |
| Problem referent ratio | 18.07% | 18.03% | 18.18% |
| Suppressed contexts | 40 | 38 | 2 |

## Primary Rule Distribution

| Rule | Count |
| --- | ---: |
| `doc.expression.target_blurred` | 31 |
| `doc.expression.output_form_missing` | 20 |
| `doc.expression.demonstrative_reference_blurred` | 11 |
| `doc.expression.operation_blurred` | 8 |
| `doc.expression.utility_blurred` | 4 |
| `doc.expression.decision_actor_missing` | 3 |

## Primary Referent Resolution Distribution

| Status | Count |
| --- | ---: |
| `ambiguous` | 9 |
| `no_candidate` | 2 |
| `supported` | 50 |

## Primary Top Matched Phrases

| Phrase | Count |
| --- | ---: |
| `返す` | 15 |
| `これ` | 13 |
| `もの` | 12 |
| `材料` | 12 |
| `場所` | 8 |
| `内容` | 7 |
| `ここ` | 6 |
| `それ` | 6 |
| `そのもの` | 5 |
| `使える` | 5 |
| `部分` | 5 |
| `渡す` | 4 |
| `これら` | 4 |
| `確認できる` | 3 |
| `できる形` | 3 |

## Primary Representative Findings

### `doc.expression.demonstrative_reference_blurred`

| Path | Line | Rule | Evidence |
| --- | ---: | --- | --- |
| `docs/comparative-advantage-and-adoption-2026-06-03.ja.md` | 222 | `doc.expression.demonstrative_reference_blurred` | これなら人間判断境界を保ったまま、Spec Kitのgate運用を横に置ける。既存のacceptance bundleやfinish checkへ自動注入しない。 |
| `docs/conventions/README.md` | 61 | `doc.expression.demonstrative_reference_blurred` | They also warn when demonstratives such as "それを外部へ出す" do not expose a |
| `docs/conventions/README.md` | 62 | `doc.expression.demonstrative_reference_blurred` | nearby referent. "未決定事項を抽出し、その一覧をJSONのfindingsとして返す" |
| `docs/expression-precision-audit-handoff-2026-06-30.md` | 29 | `doc.expression.demonstrative_reference_blurred` | 短く言えば、これは「表現精度監査」である。 |
| `docs/fixture-record-design.md` | 13 | `doc.expression.demonstrative_reference_blurred` | この記録形式は、監査規則を変更する開発者、fixtureを追加する保守者、監査結果の変化を読む利用者のために使う。実地利用で見つけた誤警告、警告漏れ、過剰なblockingを、再発させたくない局所整合性として固定する時に使う。 |
| `docs/llm-reviewer.md` | 143 | `doc.expression.demonstrative_reference_blurred` | これは別室の査読者であって、親Codexの内部判断を直接呼ぶものではない。 |

### `doc.expression.target_blurred`

| Path | Line | Rule | Evidence |
| --- | ---: | --- | --- |
| `README.ja.md` | 140 | `doc.expression.target_blurred` | archived public-heading wording from an older README |
| `README.ja.md` | 153 | `doc.expression.target_blurred` | ## GitHub公開時に見る場所 |
| `docs/acceptance-review-bundle.md` | 19 | `doc.expression.target_blurred` | bundleに含めるもの。 |
| `docs/acceptance-review-bundle.md` | 34 | `doc.expression.target_blurred` | bundleに含めないもの。 |
| `docs/agent-revision-loop-positioning-2026-06-30.md` | 52 | `doc.expression.target_blurred` | - 価値は、価値判断や完了根拠を見える場所へ出し、その結果をAIエージェントの修正、追加検証、再提示にも戻すことにある。 |
| `docs/codex-exec-reviewer-plan.md` | 122 | `doc.expression.target_blurred` | LLM reviewerの出力は、この判断の材料であり、判断そのものではない。 |

### `doc.expression.operation_blurred`

| Path | Line | Rule | Evidence |
| --- | ---: | --- | --- |
| `docs/comparative-advantage-and-adoption-2026-06-03.ja.md` | 178 | `doc.expression.operation_blurred` | これにより、上位workflowや人間reviewerは「証拠がある」という語だけでなく、何の証拠か、どの対象か、どの制限かを読める。既存の`finish-check`や`trace-report`は、このschemaを自動解釈しない。必要なら利用者がev… |
| `docs/comparative-advantage-and-adoption-2026-06-03.ja.md` | 294 | `doc.expression.operation_blurred` | `semantic-guard`は「止める権限」ではなく、「止まるべき理由を見える化する道具」でよい。 |
| `docs/comparative-advantage-and-adoption-2026-06-03.ja.md` | 392 | `doc.expression.operation_blurred` | \| 6 \| adversarial scenario pack \| LLM reviewerに渡す前の材料を増やせる \| |
| `docs/conventions/README.md` | 58 | `doc.expression.operation_blurred` | when wording such as "怪しい場所を試験できる内容として外に出す" leaves the |
| `docs/expression-precision-audit-handoff-2026-06-30.md` | 42 | `doc.expression.operation_blurred` | - どこへ「外に出す」のか。 |
| `docs/llm-reviewer.md` | 66 | `doc.expression.operation_blurred` | 入力bundleはJSONで渡す。 |

### `doc.expression.output_form_missing`

| Path | Line | Rule | Evidence |
| --- | ---: | --- | --- |
| `docs/acceptance-review-bundle.md` | 93 | `doc.expression.output_form_missing` | - `llm_review_command_tool`: prompt、schema path、`codex exec` commandを返すだけで実行しない。 |
| `docs/codex-exec-reviewer-plan.md` | 35 | `doc.expression.output_form_missing` | 6. dry-runではprompt、schema path、組み立てた`codex exec` commandだけを返す。 |
| `docs/codex-exec-reviewer-plan.md` | 40 | `doc.expression.output_form_missing` | 11.最終成果物ができた時点で`acceptance_review_bundle`を作り、人が評価できる形にする。 |
| `docs/codex-exec-reviewer-plan.md` | 91 | `doc.expression.output_form_missing` | 失敗はdeterministic auditを壊さず、別枠で返す。 |
| `docs/conventions/README.md` | 58 | `doc.expression.output_form_missing` | when wording such as "怪しい場所を試験できる内容として外に出す" leaves the |
| `docs/expression-precision-audit-handoff-2026-06-30.md` | 41 | `doc.expression.output_form_missing` | - 「内容」とは何の形式なのか。 |

### `doc.expression.utility_blurred`

| Path | Line | Rule | Evidence |
| --- | ---: | --- | --- |
| `docs/comparative-advantage-and-adoption-2026-06-03.ja.md` | 5 | `doc.expression.utility_blurred` | この文書は、公開状態で確認できる同系統のMCPサーバ、agent skill、仕様監査・保安走査系の実装を`semantic-guard`と比較し、次を切り分ける。 |
| `docs/conventions/README.md` | 58 | `doc.expression.utility_blurred` | when wording such as "怪しい場所を試験できる内容として外に出す" leaves the |
| `docs/expression-precision-audit-handoff-2026-06-30.md` | 40 | `doc.expression.utility_blurred` | - 何を「試験できる」のか。 |
| `docs/ja/quickstart.md` | 8 | `doc.expression.utility_blurred` | - `uv`が使える。 |

### `doc.expression.decision_actor_missing`

| Path | Line | Rule | Evidence |
| --- | ---: | --- | --- |
| `docs/codex-exec-reviewer-plan.md` | 40 | `doc.expression.decision_actor_missing` | 11.最終成果物ができた時点で`acceptance_review_bundle`を作り、人が評価できる形にする。 |
| `docs/conventions/README.md` | 58 | `doc.expression.decision_actor_missing` | when wording such as "怪しい場所を試験できる内容として外に出す" leaves the |
| `docs/expression-precision-audit-handoff-2026-06-30.md` | 40 | `doc.expression.decision_actor_missing` | - 何を「試験できる」のか。 |

## Primary Referent Samples

### `no_candidate`

| Path | Line | Term | Reason | Candidates |
| --- | ---: | --- | --- | --- |
| `docs/comparative-advantage-and-adoption-2026-06-03.ja.md` | 222 | `これ` | no named referent candidate found nearby |  |
| `docs/release/expression-precision-reference-heuristic-2026-07-01.md` | 85 | `それ` | no named referent candidate found nearby |  |

### `ambiguous`

| Path | Line | Term | Reason | Candidates |
| --- | ---: | --- | --- | --- |
| `docs/conventions/README.md` | 61 | `それ` | multiple medium referent candidates found nearby | 怪しい場所を試験できる内容, して外 |
| `docs/conventions/README.md` | 62 | `その一覧` | multiple medium referent candidates found nearby | 外部, 未決定事項 |
| `docs/expression-precision-audit-handoff-2026-06-30.md` | 29 | `これ` | multiple medium referent candidates found nearby | 出力, 機能, 公開文言だけを対象, 一般的な文章校正や文体改善 |
| `docs/fixture-record-design.md` | 13 | `この記録` | multiple medium referent candidates found nearby | 出力全体ではなく意味上の不変条件だけ, 監査規則, 監査結果の変化を読む利用者のため, 実地利用 |
| `docs/llm-reviewer.md` | 143 | `これ` | multiple medium referent candidates found nearby | 別室の査読者, 親Codexの内部判断を直接呼ぶもので |
| `docs/prototypes/origin-requirement.md` | 29 | `その結果` | multiple medium referent candidates found nearby | 本質的に実現したい状態は次, 要求, 計画, 証拠 |

### `supported`

| Path | Line | Term | Reason | Candidates |
| --- | ---: | --- | --- | --- |
| `README.ja.md` | 7 | `これ` | strong named referent candidate found nearby | semantic-guard, 要求, 計画, 差分 |
| `README.ja.md` | 20 | `そのもの` | strong named referent candidate found nearby | audit-plan, audit-diff, finish-check, llm-explore-request |
| `README.ja.md` | 114 | `これ` | strong named referent candidate found nearby | next_actions, details, details, schemas/audit-result.schema.json |
| `README.ja.md` | 116 | `これ` | strong named referent candidate found nearby | details, schemas/audit-result.schema.json, rule-detector-map, details |
| `README.ja.md` | 118 | `これ` | strong named referent candidate found nearby | schemas/audit-result.schema.json, rule-detector-map, explore-request, details.schema_version |
| `README.ja.md` | 166 | `これ` | strong named referent candidate found nearby | schema, 診断, 文書, 公開用に整えた作業成果 |

## Backup Check

`.backups`だけで見ると、古い査読・比較文書が`target_blurred`と`output_form_missing`を多く出している。現行閾値の根拠には混ぜず、過去文書にも同じ傾向が出るかを見る補助材料に留める。

## Calibration Observations

- `docs/conventions/README.md`の行分割された引用例は、例示文脈として抑制しきれていない。引用符内の前後行結合か、直前行の`such as`を見た抑制が要る。
- 古い`README.ja.md`の一部見出しは、見出し単体では対象語が薄いが、文書構造上は読める。Markdown見出しでは重大度を下げる余地がある。
- `docs/ja/quickstart.md`の`uvが使える。`は要件・前提条件の箇条書きであり、効用語の曖昧さとして扱う価値は低い。前提条件sectionでは`utility_blurred`を弱めるべき。
- `no_candidate`は2件だけだが、どちらも読み手が戻って探す必要があるため、現状の警告維持は妥当である。
- `supported`は50件あり、指示語を全て警告する実装にしなかった判断は妥当である。ここを崩すと過警告が一気に増える。
- この要約文書自体を`audit_conventions(input_kind="document")`にかけると、表内の `返す`、`もの`、`材料` などから62件の`doc.expression.*`が出る。統計表、監査報告、引用evidenceは通常散文より弱く扱う抑制が必要である。

## Threshold Notes

- 閾値判断の主対象は`primary`。`.backups`は表現揺れと重複確認用の補助corpusとして扱う。
- 指示代名詞は`no_candidate`と`ambiguous`を警告維持、`supported`を抑制維持する。
- `weak_only`は今回観測されなかったため、次のcorpus追加まで閾値を動かさない。
- 非指示代名詞の`target_blurred`、`operation_blurred`、`utility_blurred`は単独blockingにせず、同一文で対象、操作、出力形式、判断主体が二つ以上欠ける場合に強警告へ寄せる。
- 文書内に「不明点」「未決定」「判断主体」「出力形式」などの支援語が明示される場合は、同じ語が近傍候補に出るかを優先して過警告を抑える。

## Survival Bias Check

- この結果は検出器が発火した箇所の分布であり、発火しなかった曖昧表現の不存在証明ではない。
- 次段階では、警告あり文だけでなく警告なし文を無作為抽出し、手動で「指示対象が読めるか」「書き換える価値があるか」を付ける必要がある。
- 特に「これ」「それ」「この」「その」を含むのに`supported`となった文、または指示語を含まないが対象・操作が薄い文を負例として見る。

## Morphological Analysis Decision

- 今回の実測だけなら形態素解析を必須依存にする根拠はまだ弱い。
- 現在の危険は、名詞境界の取り違えよりも「検出語に寄った表面一致」と「未検出文の生存バイアス」にある。
- 導入するなら、標準経路ではなく任意のcalibration補助として、曖昧候補が多い文だけに限定するのが妥当。

## Next Corpus Work

- 生データから`primary`の`doc.expression.*`発火文を20件程度、人手で`true_positive`、`false_positive`、`useful_but_low_priority`に分類する。
- 警告なし文から`matched_phrases`を含むものと含まないものをそれぞれ抽出し、見逃しを確認する。
- 追加fixtureはJSON全体ではなく、`rule_id`、`referent_resolutions.status`、代表evidenceを対象に固定する。
- 形態素解析は、この手動分類で「候補抽出の境界誤り」が主要因だと分かるまで既定依存へ入れない。
