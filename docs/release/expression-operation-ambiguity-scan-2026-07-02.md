# Expression Operation Ambiguity Scan 2026-07-02

## Purpose

This report searches for document wording that looks more concrete than bare vague phrasing but may still hide the actual operation, criterion, output, monitoring condition, or decision use.

It is an exploratory corpus scan, not a formal detector result and not an accuracy measurement.

## Scope

- Root: repository root at run time; absolute local path intentionally omitted for publication hygiene.
- Candidate files: 79
- Records: 254 total / 187 primary / 67 backup
- Primary actionable candidates: 113
- Errors: 0
- Raw data: excluded from the public tree; retained as local calibration output.

## Category Counts

| Category | Count |
| --- | ---: |
| `inspection_contract_missing` | 114 |
| `handling_or_use_contract_missing` | 103 |
| `as_view_operation_blurred` | 29 |
| `comparison_contract_missing` | 7 |
| `observation_contract_missing` | 1 |

## Status Counts

| Status | Count |
| --- | ---: |
| `partially_supported` | 93 |
| `under_specified_candidate` | 72 |
| `supported_context` | 47 |
| `example_context` | 28 |
| `structural_context_without_support` | 14 |

## Candidate Rule Families

### `doc.expression.as_view_operation_blurred`

Role/view wording such as 'として見る' names a viewpoint but not the concrete operation.

Rewrite candidates:

- `one-time verification`: 〜のため確認する。
- `inspection against criteria`: 〜を基準に照らして検査する。
- `continuous observation`: 〜を監視する。
- `classification`: 〜として分類する。
- `human decision support`: 〜を判断材料として提示する。

Primary actionable samples:

| Path | Line | Status | Match | Evidence | Support |
| --- | ---: | --- | --- | --- | --- |
| `README.ja.md` | 11 | `under_specified_candidate` | `として扱う` | Criterion Loomは次の四つを公開上の柱として扱う。 |  |
| `README.ja.md` | 142 | `under_specified_candidate` | `として見せる` | deleted company-facing section heading from an older README draft |  |
| `docs/agent-revision-loop-positioning-2026-06-30.md` | 73 | `under_specified_candidate` | `として扱う` | - 監査結果を人間が読むだけの静的レポートとして扱う。 |  |
| `docs/codex-exec-reviewer-plan.md` | 93 | `under_specified_candidate` | `として扱う` | - command build failure: adapterの実装不備として扱う。 |  |
| `docs/codex-exec-reviewer-plan.md` | 98 | `under_specified_candidate` | `として扱う` | - empty output: missing reviewer outputとして扱う。 |  |
| `docs/comparative-advantage-and-adoption-2026-06-03.ja.md` | 12 | `under_specified_candidate` | `として扱う` | これは宣伝文ではない。`semantic-guard`を保安走査器、仕様平台、workflow実行器、release gate、人間受入判断の代替として扱うための文書でもない。 |  |
| `README.ja.md` | 155 | `partially_supported` | `として見せる` | deleted GitHub-viewing section wording from an older README draft | 確認 |
| `docs/acceptance-review-bundle.md` | 57 | `partially_supported` | `として扱う` | `finding.derivation`と`details.logical_trace`はdeterministic audit materialとして扱う。これらは、抽出factと規則述語からfindingがどう導かれたかを説明するだけである。自然言語本文の真偽、成果物の危険有… | 抽出 |

### `doc.expression.inspection_contract_missing`

Inspection/review verbs name an operation but may omit criteria, method, output, or decision actor.

Rewrite candidates:

- `criteria available`: 〜を基準Xに照らして確認する。
- `rule-based inspection`: 〜を走査し、違反箇所をfindingsとして返す。
- `human review`: 〜を人間の判断材料として提示する。

Primary actionable samples:

| Path | Line | Status | Match | Evidence | Support |
| --- | ---: | --- | --- | --- | --- |
| `README.ja.md` | 155 | `under_specified_candidate` | `確認する` | deleted GitHub-viewing section wording from an older README draft |  |
| `docs/acceptance-review-bundle.md` | 15 | `under_specified_candidate` | `判断する` | 使う時点は、要求監査、計画監査、差分監査、完了確認、LLM中途査読が終わり、最終成果物を人が受け入れるかどうかを判断する直前である。中間工程の承認には使わない。 |  |
| `docs/acceptance-review-bundle.md` | 50 | `under_specified_candidate` | `判断して` | - `pending`: まだ人が判断していない。 |  |
| `docs/agent-revision-loop-positioning-2026-06-30.md` | 15 | `under_specified_candidate` | `確認する` | 1. Criterion Loomを外向けに説明する前に、この文書の「変更の要点」と「更新後の短い説明案」を確認する。 |  |
| `docs/codex-exec-reviewer-plan.md` | 138 | `under_specified_candidate` | `確認する` | 実装時は次を確認する。 |  |
| `docs/comparative-advantage-and-adoption-2026-06-03.ja.md` | 5 | `under_specified_candidate` | `確認できる` | この文書は、公開状態で確認できる同系統のMCPサーバ、agent skill、仕様監査・保安走査系の実装を`semantic-guard`と比較し、次を切り分ける。 |  |
| `docs/comparative-advantage-and-adoption-2026-06-03.ja.md` | 30 | `under_specified_candidate` | `評価して` | - Planuはnpm package展開物から見た比較であり、非公開の運用やhosted featureは評価していない。 |  |
| `docs/comparative-advantage-and-adoption-2026-06-03.ja.md` | 135 | `under_specified_candidate` | `判定できる` | したがって公開時は、fixture pass rateを「任意文書でも同じ品質で判定できる」という主張へ飛躍させてはいけない。 |  |

### `doc.expression.observation_contract_missing`

Observation/monitoring verbs may omit the signal, interval, threshold, or response action.

Rewrite candidates:

- `ongoing monitoring`: 〜の変化を指標Xで監視し、閾値Yを超えたら記録する。
- `periodic observation`: 〜を周期Zで観測し、差分を一覧へ記録する。

Primary actionable samples:

| Path | Line | Status | Match | Evidence | Support |
| --- | ---: | --- | --- | --- | --- |
| `tests/fixtures/plans/good.md` | 11 | `under_specified_candidate` | `追跡できる` | 妥当性: 各fixtureのrationaleが固定したい監査意味へ追跡できるか確認する。 |  |

### `doc.expression.comparison_contract_missing`

Comparison/alignment verbs may omit the counterpart, comparison field, mismatch output, or acceptance boundary.

Rewrite candidates:

- `diff check`: AとBの項目Xを比較し、不一致を一覧として返す。
- `contract alignment`: Aを契約Bに照合し、違反箇所をfindingsに記録する。

Primary actionable samples:

| Path | Line | Status | Match | Evidence | Support |
| --- | ---: | --- | --- | --- | --- |
| `docs/comparative-advantage-and-adoption-2026-06-03.ja.md` | 5 | `under_specified_candidate` | `比較し、` | この文書は、公開状態で確認できる同系統のMCPサーバ、agent skill、仕様監査・保安走査系の実装を`semantic-guard`と比較し、次を切り分ける。 |  |
| `docs/comparative-advantage-and-adoption-2026-06-03.ja.md` | 29 | `under_specified_candidate` | `比較する` | - Snyk、Semgrep、Harnessには公開repositoryから見える範囲外の商用機能がある。ここでは確認できた実装と文書だけを比較する。 |  |
| `docs/public-comparison-2026-06-02.ja.md` | 5 | `under_specified_candidate` | `比較し、` | この文書は、`semantic-guard`を公開済みのMCPサーバ、エージェント技能、保安走査系の道具と比較し、公開時の位置づけを定めるための文書である。 |  |
| `docs/public-comparison-2026-06-02.ja.md` | 41 | `partially_supported` | `比較できる` | 公平な公開比較は、公開されている機能、出力契約、公式文書から行える。たとえばfilesystem MCP、GitHub MCP、Context7、Snyk MCP、Semgrep MCP、Skillsは、それぞれの用途と境界を比較できるだけの公開情報を持っている。 | 契約, 出力 |

### `doc.expression.handling_or_use_contract_missing`

Handling/use wording such as '扱う' or '活用する' may omit the action, purpose, owner, or output.

Rewrite candidates:

- `tool use`: 〜を入力として使い、結果をJSONとして返す。
- `handling policy`: 〜をcategory Xとして扱い、保存先Yに記録する。
- `response action`: 〜に対してaction Xを実行し、結果を記録する。

Primary actionable samples:

| Path | Line | Status | Match | Evidence | Support |
| --- | ---: | --- | --- | --- | --- |
| `README.ja.md` | 11 | `under_specified_candidate` | `扱う` | Criterion Loomは次の四つを公開上の柱として扱う。 |  |
| `docs/acceptance-review-bundle.md` | 82 | `under_specified_candidate` | `使う` | scaffoldの形だけを見る時は`--no-strict`を使う。strictでは、少なくとも一つのdeterministic audit、execution evidence、human review pointが必要になる。 |  |
| `docs/codex-exec-reviewer-plan.md` | 93 | `under_specified_candidate` | `扱う` | - command build failure: adapterの実装不備として扱う。 |  |
| `docs/codex-exec-reviewer-plan.md` | 98 | `under_specified_candidate` | `扱う` | - empty output: missing reviewer outputとして扱う。 |  |
| `docs/fixture-record-design.md` | 89 | `under_specified_candidate` | `使う` | 6. derivation形状を固定したい場合は`derivation_status`, `derivation_rule_id`, `derivation_missing_obligation`, `derivation_countercondition`, `derivation_fact… |  |
| `docs/fixture-record-design.md` | 89 | `under_specified_candidate` | `使う` | 6. derivation形状を固定したい場合は`derivation_status`, `derivation_rule_id`, `derivation_missing_obligation`, `derivation_countercondition`, `derivation_fact… |  |
| `docs/ja/README.md` | 5 | `under_specified_candidate` | `扱う` | 技術名としてのpackage / CLI / MCP serverは`semantic-guard`のまま扱う。 |  |
| `docs/ja/quickstart.md` | 36 | `under_specified_candidate` | `使う` | 網羅的に問いただす必要がある場合はLLM版を使う。 |  |

## Assessment

- The scan confirms the same family exists beyond `〜として見る`: `扱う`, `使う`, `確認する`, `判断する`, `比較する`, and monitoring verbs can all hide missing operational contracts.
- The high count for inspection verbs shows this family is noisy. It should not be promoted as a broad warning until samples are labeled and support-term suppression is stronger.
- `as_view_operation_blurred` is the most direct and narrow first promotion target. It can include `検査する` as a rewrite candidate without making every `検査する` phrase a warning.
- `inspection_contract_missing` should be second, and only for verb forms where criteria or output are absent. Bare nouns such as `監査` or `判断` are intentionally no longer counted by this refined scan.

## Implementation Notes

- `doc.expression.as_view_operation_blurred` should be the first rule to promote because it directly covers the user-reported `〜として見る` family.
- `検査する` belongs in the rewrite candidates for `as_view_operation_blurred`, but text that already says `検査する` should be checked separately by `doc.expression.inspection_contract_missing` when the criterion, method, output, or decision actor is absent.
- Do not auto-rewrite these phrases by default. Return candidate rewrites with `needs_human_decision=true` unless a single operation is recoverable from nearby terms.
- Treat headings, tables, code examples, and explicit examples as lower-priority candidates. They are useful for fixture design but should not become high-severity prose warnings without context.

## Suggested Promotion Order

1. Add `doc.expression.as_view_operation_blurred` with rewrite candidates for confirmation, inspection, monitoring, classification, and decision support.
2. Add `doc.expression.inspection_contract_missing` for `検査する`, `確認する`, `チェックする`, `レビューする`, `評価する`, `判断する` when criteria or output are absent.
3. Add observation/comparison/handling rules only after labeled samples show they are not too noisy.
