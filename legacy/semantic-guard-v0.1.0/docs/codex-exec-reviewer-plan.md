# Codex Exec Reviewer Plan

`codex exec` reviewer は、`candidate_gap_reviewer` の prompt と schema を使い、別プロセスの Codex を隔離査読者として起動するための計画である。

## Purpose

決定的監査は再現性を持つが、文脈上の不足、薄い前提、反適用条件、補填案の生成には弱い。`llm-review-prompt` はそのための入力と出力契約を作り、`codex_exec_review.py` は `codex exec` を使う実行層を担う。

この計画は、`codex exec` を使って LLM 査読を実行する場合の責務、制約、失敗時の扱い、人間による最終評価点を定める。

## Status

adapter は実装済みである。`llm-review-command` と `llm-review-run` は dry-run を既定にし、`--execute` が指定された時だけ `codex exec` を起動する。MCP server からは `llm_review_command_tool` と `llm_review_run_tool` で呼べる。

この文書は実装後も契約記録として残す。`acceptance_review_bundle` は `docs/acceptance-review-bundle.md` と `schemas/acceptance-review-bundle.schema.json` に分離して実装済みであり、LLM reviewer adapter とは混ぜない。

## Non-Goals

- OpenAI API 直接呼び出しはしない。
- 親 Codex セッションの内部モデルへ直接問い合わせる設計にはしない。
- LLM reviewer に最終合否を決めさせない。
- deterministic audit を置き換えない。
- LLM 出力を自動適用しない。
- 中間工程ごとに人間承認を要求しない。

## Target Flow

実行時の流れは次にする。

1. deterministic audit を実行する。
2. 候補案、元要求、監査結果、関連rule、制約、対象外、未確定事項を review bundle にまとめる。
3. `phase` に応じた工学知識を review bundle へ入れる。要求監査では要求工学、計画監査では計画管理、差分監査ではソフトウェア工学と secure-development guidance、完了確認では検証、妥当性確認、release readiness を使う。
4. 関連ruleの `concern`, `applies_when`, `does_not_apply_when`, `evidence_required`, `severity_policy`, `finding`, `remediation` を LLM reviewer が項目別に点検できる形で渡す。
5. `llm-review-prompt` で prompt を生成する。
6. dry-run では prompt、schema path、組み立てた `codex exec` command だけを返す。
7. run mode では `codex exec` を read-only sandbox で起動する。
8. LLM 出力を `validate-llm-review` 相当の検証に通す。
9. 結果を `candidate_gap_review` として保存または返却する。
10. Codex は補填案を採用、保留、却下の候補に分ける。
11. 最終成果物ができた時点で `acceptance_review_bundle` を作り、人が評価できる形にする。

## Command Contract

`codex exec` は次の条件を既定にする。

```sh
codex exec \
  --ephemeral \
  --ignore-user-config \
  --ignore-rules \
  --skip-git-repo-check \
  --sandbox read-only \
  -c 'approval_policy="never"' \
  --output-schema ./schemas/candidate-gap-review.schema.json \
  -m gpt-5.4-mini \
  -
```

shell 文字列を直接連結せず、`subprocess.run([...])` の list argv で起動する。prompt は標準入力で渡し、長い文字列を shell 展開しない。

## CLI

最小CLIは次である。

```sh
semantic-guard llm-review-command --file review-input.json
semantic-guard llm-review-run --file review-input.json --dry-run
semantic-guard llm-review-run --file review-input.json --execute
```

既定は dry-run とする。`--execute` が無い限り、`codex exec` は起動しない。追加で `--model`、`--timeout-seconds`、`--working-directory`、`--codex-binary`、`--include-schema` を受け取る。

## Safety Conditions

実行層は次を満たす。

- workspace への書き込みを許さない。
- approval は要求しない。現行 `codex exec` には `--ask-for-approval` が無いため、`-c 'approval_policy="never"'` と read-only sandbox で固定する。
- session は ephemeral にする。
- user / project rules は読ませない。
- 出力は schema で縛る。
- `codex exec --output-schema` の制約に合わせ、schema内objectの `properties` は全項目 `required` に含める。該当なしは空配列または `なし` 相当の文字列で表す。
- timeout を持つ。
- stderr と exit code を結果に残す。
- schema 不一致は失敗として扱う。
- LLM 出力を合否判定へ変換しない。
- LLM 出力には `rule_item_reviews` を含め、各rule要点を見た痕跡を残す。

## Failure Handling

失敗は deterministic audit を壊さず、別枠で返す。

- command build failure: adapter の実装不備として扱う。
- timeout: `review_status` ではなく execution failure として扱う。
- non-zero exit: exit code、stdout、stderr を記録する。
- invalid JSON: schema validation failure として扱う。
- schema mismatch: LLM reviewer result として採用しない。
- empty output: missing reviewer output として扱う。

## Human Final Review

人間確認は中間工程ではなく、最終成果物評価時に置く。

`acceptance_review_bundle` は次を含む。

- 元要求。
- 最終成果物。
- deterministic audit の結果。
- LLM reviewer の不足指摘と補填案。
- Codex が採用した補填。
- Codex が採用しなかった補填と理由。
- 実行証拠。
- 残リスク。
- 人が見るべき判断点。

人が下す判断は次の三つに限る。

- accept: 現成果物を受け入れる。
- request_revision: 修正を求める。
- defer: 判断を保留する。

LLM reviewer の出力は、この判断の材料であり、判断そのものではない。

## Implementation Steps

1. `src/semantic_guard/codex_exec_review.py` を追加した。
2. `CodexExecReviewRequest` と `CodexExecReviewResult` を定義した。
3. `build_codex_exec_command()` を実装した。
4. `run_codex_exec_review(..., execute=False)` を dry-run 既定で実装した。
5. `execute=True` の時だけ `subprocess.run` を呼ぶ。
6. stdout を JSON として読み、`validate_candidate_gap_review` に通す。
7. CLI に `llm-review-command` と `llm-review-run` を足した。
8. `tests/test_codex_exec_review.py` を追加した。
9. README と `docs/llm-reviewer.md` を更新した。

## Verification Plan

実装時は次を確認する。

- `build_codex_exec_command()` が固定実行オプションを含む。
- dry-run が `codex exec` を起動しない。
- execute mode でも list argv で起動する。
- timeout と non-zero exit を構造化して返す。
- invalid JSON と schema mismatch を失敗として返す。
- valid output は `candidate_gap_review` として返す。
- `approved`, `rejected`, `final_decision` を含む出力は不正になる。
- `rule_item_reviews` が無い出力は不正になる。
- phase別の工学知識が prompt に含まれる。
- 既存 `python -m unittest discover -s tests -v` が通る。

## Acceptance Review Bundle

`acceptance_review_bundle` は別schemaとして定義した。

- schema: `schemas/acceptance-review-bundle.schema.json`
- implementation: `src/semantic_guard/acceptance_review.py`
- CLI: `acceptance-bundle-schema`, `acceptance-bundle-template`, `validate-acceptance-bundle`
- MCP: `acceptance_bundle_template_tool`, `validate_acceptance_bundle_tool`

このbundleは人間最終評価の材料であり、LLM reviewer の判断ではない。

## Risks

- `codex exec` は遅く、費用がかかる。
- 別プロセスの Codex は親会話の文脈を自動では持たない。
- prompt が大きくなりすぎると、不要情報や秘密を渡す危険がある。
- LLM 出力がもっともらしいが誤っている可能性がある。
- schema は形を縛るが、意味の正しさは保証しない。

## Rollback

adapter 実装で問題が出た場合は、`src/semantic_guard/codex_exec_review.py`、CLI追加、関連試験、文書追記を戻す。既存の deterministic audit、rule catalog、LLM prompt生成層は維持できる。

## Completion Evidence

計画完了の証拠は次にする。

- この文書が存在する。
- `semantic-guard audit-plan` が pass する。
- この文書の `--kind document` 監査が pass する。
- 必要なら README または `docs/llm-reviewer.md` から参照される。
