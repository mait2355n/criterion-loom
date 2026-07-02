# LLM Reviewer

`candidate_gap_reviewer` は、決定的監査の上に置く隔離査読者である。役割は候補案の不足指摘と補填案生成に限る。

## Purpose

`core.py` と rule catalog は再現性のある監査を担う。一方で、文脈上の不足、反適用条件、薄い前提、補うべき証拠は語彙照合だけでは拾いにくい。

LLM reviewer はその弱点を補う。ただし、最終合否を決める裁判官ではない。候補案、元要求、決定的監査結果、関連ruleを読み、不足、疑わしい前提、反適用条件の可能性、補填案、人間判断点を返す。

また、LLM reviewer は中途監査として起動される。人が最終成果物を評価する前に、要求監査、計画監査、差分監査、完了確認の各段階で不足と補填候補を整理する。

## Status

現時点では OpenAI API を直接呼ばない。実装済みなのは次である。

- `schemas/candidate-gap-review.schema.json`: LLM reviewer の出力schema。
- `src/semantic_guard/llm_review.py`: prompt生成、schema読込、軽量検証。
- `src/semantic_guard/codex_exec_review.py`: `codex exec` 用の dry-run 既定adapter。
- CLI補助: `llm-review-prompt`, `llm-review-schema`, `validate-llm-review`。
- 実行補助: `llm-review-command`, `llm-review-run --dry-run`, `llm-review-run --execute`。

## Role Boundary

LLM reviewer がしてよいこと。

- 候補案に不足している観点を指摘する。
- 論理監査に使えそうな候補事実や候補反適用条件を提案する。
- 段階に応じた工学知識を使う。要求監査では要求工学、計画監査では計画管理、差分監査ではソフトウェア工学と secure-development guidance、完了確認では検証、妥当性確認、release readiness を使う。
- 曖昧な前提や危険な仮定を挙げる。
- deterministic監査の警告が反適用条件に当たる可能性を示す。
- 関連ruleの `concern`, `applies_when`, `does_not_apply_when`, `evidence_required`, `severity_policy`, `finding`, `remediation` を項目ごとに点検する。
- 補うべき受入条件、検証方法、対象外、証拠、計画項目を提案する。
- 人間判断が必要な点を分離する。

LLM reviewer がしてはいけないこと。

- 候補案を承認または却下する。
- 実装を変更する。
- 候補事実を `present` な監査事実として確定する。
- `finding.derivation`、`details.logical_trace`、最終 finding、または `final_human_decision` を直接作る。
- deterministic監査の警告を無視してよいと断定する。
- rule や fixture を勝手に追加する。
- 親Codexの判断を上書きする。

## Output Contract

出力は `candidate-gap-review/v2` のJSONである。

主要項目は次の通り。

- `review_status`: `no_supplement_needed`, `needs_supplement`, `blocked_by_missing_context`。
- `missing_aspects`: 不足観点の一覧。各 item は重大度、理由、補填 proposal を持つ。
- `questionable_assumptions`: 疑わしい前提と危険。
- `possible_counter_conditions`: 該当しうる `does_not_apply_when`。
- `supplement_proposals`: 候補、計画、文書、証拠へ足す提案。
- `rule_item_reviews`: 関連ruleの要点ごとの点検結果。
- `human_decision_needed`: 人間判断が必要な点。

schema は `schemas/candidate-gap-review.schema.json` に置く。

`codex exec --output-schema` は object 内の `properties` 全項目が `required` に含まれていることを要求する。そのため、該当なしの欄も省略せず、JSON field に空配列または `なし` 相当の文字列を入れる。

## Prompt Generation

review input bundle は JSON object として stdin または file input に置く。

```json
{
  "candidate": "候補案本文",
  "request": "元要求",
  "audit_result": {
    "status": "warn",
    "findings": []
  },
  "rule_ids": [
    "req.verifiability.acceptance_missing"
  ],
  "constraints": "外部API呼び出しはまだしない",
  "non_goals": "合否決定はしない",
  "unknowns": "codex exec方式とAPI方式の選択は未定",
  "phase": "audit_plan"
}
```

input JSON に `phase` field を入れると、prompt には段階別の `phase_guidance` が入る。`rule_ids` が無い場合は、同じ phase に登録された rule を関連 rule として展開する。

prompt は次で生成できる。

```sh
uv run --python 3.13 --project . \
  semantic-guard llm-review-prompt --file review-input.json > review-prompt.md
```

schema は次で出力できる。

```sh
uv run --python 3.13 --project . \
  semantic-guard llm-review-schema > candidate-gap-review.schema.json
```

LLM出力の形だけを確認する場合は次を使う。

```sh
uv run --python 3.13 --project . \
  semantic-guard validate-llm-review --file review-output.json
```

## Codex Exec Adapter

`llm-review-command` は、実行せずに prompt、schema path、`codex exec` command を JSON output に返す。

```sh
uv run --python 3.13 --project . \
  semantic-guard llm-review-command --file review-input.json
```

`llm-review-run` は既定で dry-run になる。`--execute` を付けた時だけ `codex exec` を起動し、stdout を `candidate-gap-review/v2` として検証する。

```sh
uv run --python 3.13 --project . \
  semantic-guard llm-review-run --file review-input.json --dry-run

uv run --python 3.13 --project . \
  semantic-guard llm-review-run --file review-input.json --execute
```

adapter の `codex exec` command は次の形になる。prompt は argv に直接埋め込まず、標準入力へ書く。

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

`candidate_gap_reviewer` は別室の査読者であって、親Codexの内部判断を直接呼ばない。

失敗は査読結果へ偽装しない。timeout、non-zero exit、invalid JSON、schema mismatch は `execution_status`、`failure_kind`、`errors`、`stdout`、`stderr` として返す。

設計記録は `docs/codex-exec-reviewer-plan.md` に置く。そこでは dry-run 既定、read-only 実行、schema検証、失敗時の扱い、最終人間評価用の `acceptance_review_bundle` を分けて扱う。

MCP server からは次で呼べる。

- `llm_review_command_tool`: 実行せずに command と prompt を JSON object に返す。
- `llm_review_run_tool`: 既定は dry-run。`execute=true` の時だけ `codex exec` を起動する。
- `review_if_needed_tool`: deterministic監査結果から判別不能性を検出し、必要な時だけ同じ隔離査読へ渡す。既定は dry-run。
- `llm_review_start_tool`: `codex exec` reviewer を背景ジョブとして開始し、`job_id` を返す。
- `review_if_needed_start_tool`: `review-if-needed` の経路判定を先に行い、必要な時だけ背景ジョブを開始する。
- `llm_review_status_tool`: `job_id` の状態を JSON object に返す。

背景ジョブの状態は `queued`、`running`、`completed`、`failed`、`timed_out`、`not_needed`、`input_error`、`not_found` のいずれかである。呼出し側が「まだ応答中か、失敗したか、応答済みか」を見る時は、次を読む。

- `running=true`: まだ応答待ちである。
- `process_finished=true`: 背景 command は終了している。
- `review_received=true`: stdout が JSON として読め、schema 検証まで通った。
- `response_state=invalid_review`: process は終わったが、有効な査読結果ではない。
- `state=timed_out`: timeout により終了した。

この job store は MCP process 内の状態であり、MCP server の再起動をまたいで永続化しない。長期保存したい場合は、呼出し側が `llm_review_status_tool` の結果を証拠として保存する。

MCP tool は `codex_binary` を受け取らない。実行binaryを外から差し替えられるようにすると、監査補助が任意実行器へ崩れるためである。

## Review If Needed

`review-if-needed` は、決定的監査の結果を直接 LLM に丸投げするものではない。先に review routing 判定を行い、決定論規則だけでは価値ある補助査読を捨てることになる場合だけ `candidate_gap_reviewer` へ回す。

`pressure.score` field は、候補案の正しさ確率でも、決定的監査の誤り確率でもない。`pressure.score` は査読経路圧である。隔離 reviewer を作る価値がどれだけあるかを、不確実性、影響度、反適用条件らしさ、文脈汚染危険、独立査読価値から集約する。

- `warning_class` が `possible false positive`。
- blocker または major の欠落警告に `nearest_candidates` がある。
- `match_status=unknown`。
- blocker または major の finding が `match_status=partial`。
- high-impact finding の `confidence=low`。
- `ambiguity_reasons` に `negated_context`、`quoted_or_historical`、`trace_vocabulary_gap`、`high_impact_low_specificity` がある。
- `generic caution` が evidence、security、meaning、または semantic boundary に触れている。
- document-only 監査で、実装証拠なしの強い実行時主張がある。
- `audit_diff` が identity、persistence、source_of_truth、permission に触れている。
- blocker ではないが score が低く、補填査読で不足か過剰警告かを分けたい。
- `review_context.independent_review_requested` または `fresh_eyes_requested` がある。
- `review_context.self_reviewed`、`same_agent_planned_and_implemented`、`long_running_work` など、親文脈への染まりを疑う signal がある。
- `review_context.public_release`、`external_publication`、`changed_files_count` など、独立した二周目の価値が高い signal がある。

CLI は次で使う。

```sh
uv run --python 3.13 --project . \
  semantic-guard review-if-needed --file escalation-input.json --dry-run
```

入力 JSON は、少なくとも `candidate` と `deterministic_audit` を持つ。

```json
{
  "candidate": "監査対象の要求、計画、差分、文書、完了報告",
  "phase": "audit_plan",
  "deterministic_audit": {
    "phase": "audit_plan",
    "status": "warn",
    "findings": []
  },
  "review_context": {
    "independent_review_requested": true,
    "self_reviewed": true,
    "public_release": true,
    "changed_files_count": 12
  },
  "non_goals": "合否決定はしない"
}
```

`review-if-needed` の JSON output は `escalation` と `review_result` を持つ。`escalation.needed` が `false` の時、`review_result` は `null` である。`needed` が `true` の時も、既定では dry-run の command と prompt を JSON output に入れるだけで、`--execute` または MCP の `execute=true` が明示されるまで `codex exec` は起動しない。

`escalation` JSON object は互換用の `needed`、`mode`、`target`、`reasons`、`rationale`、`payload` を保ちつつ、次の field を持つ。

- `pressure`: score、level、score_semantics。
- `dimensions`: uncertainty、impact、countercondition_plausibility、context_contamination_risk、independent_review_value などの圧力段階。
- `signals`: 圧力を作った inspectable な入力信号。
- `non_decisions`: この routing が決めていないこと。合否、承認、棄却、finding 解除、status / score 変更、最終人間判断はここでは変わらない。

`review_result.prompt` には `review_context` と `routing_assessment` が渡される。これにより、隔離 reviewer は「なぜ呼ばれたか」を見られるが、「自分が最終判定者である」とは扱えない。

この層の目的は、決定論規則の外側にある見落とし候補を補助材料として露出することである。LLM reviewer の返答は補填候補であり、採用、棄却、延期は親側の判断に残す。

## Logical Audit Boundary

論理監査の `finding.derivation` と `details.logical_trace` は、決定的抽出器が受け入れた fact と executable predicate の導出記録である。

LLM reviewer は、そこへ足せるかもしれない候補 fact、候補 countercondition、質問、補填案を返してよい。しかし、その出力は `candidate` 止まりである。決定的証拠または明示的な人間判断なしに、LLM 出力を `present` fact、derivation step、finding、受入判断へ昇格してはいけない。

## Limits

この仕組みは不足補填の補助であり、正しさの証明ではない。LLM出力は揺れる。最終判断は、決定的監査、rule catalog、fixture、実行証拠、そして必要な人間判断を合わせて行う。
