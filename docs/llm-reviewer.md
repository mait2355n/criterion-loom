# LLM Reviewer

`candidate_gap_reviewer`は、決定的監査の上に置く隔離査読者である。役割は候補案の不足指摘と補填案生成に限る。

## Purpose

`core.py`とrule catalogは再現性のある監査を担う。一方で、文脈上の不足、反適用条件、薄い前提、追加証拠の候補は語彙照合だけでは拾いにくい。

LLM reviewerは、候補案、元要求、決定的監査結果、関連ruleを入力として読み、不足を`missing_aspects`、疑わしい前提を`questionable_assumptions`、反適用条件候補を`possible_counter_conditions`、補填案を`supplement_proposals`、人間判断点を`human_decision_needed`へ返す。ただし、最終合否を決める裁判官ではない。

また、LLM reviewerは中途監査として起動される。人が最終成果物を評価する前に、要求監査、計画監査、差分監査、完了確認の各段階で不足と補填候補を整理する。

## Status

現時点ではOpenAI APIを直接呼ばない。実装済みなのは次である。

- `schemas/candidate-gap-review.schema.json`: LLM reviewerの出力schema。
- `src/semantic_guard/llm_review.py`: prompt生成、schema読込、軽量検証。
- `src/semantic_guard/codex_exec_review.py`: `codex exec`用のdry-run既定adapter。
- CLI補助: `llm-review-prompt`, `llm-review-schema`, `validate-llm-review`。
- 実行補助: `llm-review-command`, `llm-review-run --dry-run`, `llm-review-run --execute`。

## Role Boundary

LLM reviewerがしてよいこと。

- 候補案に不足している観点を指摘する。
- 論理監査に使えそうな候補事実や候補反適用条件を提案する。
- 段階に応じた工学知識を使う。要求監査では要求工学、計画監査では計画管理、差分監査ではソフトウェア工学とsecure-development guidance、完了確認では検証、妥当性確認、release readinessを使う。
- 曖昧な前提や危険な仮定を挙げる。
- deterministic監査の警告が反適用条件に当たる可能性を示す。
- 関連ruleの`concern`, `applies_when`, `does_not_apply_when`, `evidence_required`, `severity_policy`, `finding`, `remediation`を項目ごとに点検する。
- 受入条件、検証方法、対象外、証拠、計画項目の追加候補を`supplement_proposals`へ返す。
- 人間判断が必要な点を分離する。

LLM reviewerがしてはいけないこと。

- 候補案を承認または却下する。
- 実装を変更する。
- 候補事実を`present`な監査事実として確定する。
- `finding.derivation`、`details.logical_trace`、最終finding、または`final_human_decision`を直接作る。
- deterministic監査の警告を無視してよいと断定する。
- ruleやfixtureを勝手に追加する。
- 親Codexの判断を上書きする。

## Output Contract

出力は`candidate-gap-review/v2`のJSONである。

主要項目は次の通り。

- `review_status`: `no_supplement_needed`, `needs_supplement`, `blocked_by_missing_context`。
- `missing_aspects`: 不足観点の一覧。各itemは重大度、理由、補填proposalを持つ。
- `questionable_assumptions`: 疑わしい前提と危険。
- `possible_counter_conditions`: 該当しうる`does_not_apply_when`。
- `supplement_proposals`: 候補、計画、文書、証拠へ足す提案。
- `rule_item_reviews`: 関連ruleの要点ごとの点検結果。
- `human_decision_needed`: 人間判断が必要な点。

schemaは`schemas/candidate-gap-review.schema.json`に置く。

`codex exec --output-schema`はobject内の`properties`全項目が`required`に含まれていることを要求する。そのため、該当なしの欄も省略せず、JSON fieldに空配列または`なし`相当の文字列を入れる。

## Prompt Generation

review input bundleはJSON objectとしてstdinまたはfile inputに置く。

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

input JSONに`phase` fieldを入れると、promptには段階別の`phase_guidance`が入る。`rule_ids`が無い場合は、同じphaseに登録されたruleを関連ruleとして展開する。

promptは次で生成できる。

```sh
uv run --python 3.13 --project . \
  semantic-guard llm-review-prompt --file review-input.json > review-prompt.md
```

schemaは次で出力できる。

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

`llm-review-command`は、実行せずにprompt、schema path、`codex exec` commandをJSON outputに返す。

```sh
uv run --python 3.13 --project . \
  semantic-guard llm-review-command --file review-input.json
```

`llm-review-run`は既定でdry-runになる。`--execute`を付けた時だけ`codex exec`を起動し、stdoutを`candidate-gap-review/v2`として検証する。

```sh
uv run --python 3.13 --project . \
  semantic-guard llm-review-run --file review-input.json --dry-run

uv run --python 3.13 --project . \
  semantic-guard llm-review-run --file review-input.json --execute
```

adapterの`codex exec` commandは次の形になる。promptはargvに直接埋め込まず、標準入力へ書く。

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

`candidate_gap_reviewer`は別室の査読者であって、親Codexの内部判断を直接呼ばない。

失敗は査読結果へ偽装しない。timeout、non-zero exit、invalid JSON、schema mismatchは`execution_status`、`failure_kind`、`errors`、`stdout`、`stderr`として返す。

設計記録は`docs/codex-exec-reviewer-plan.md`に置く。そこではdry-run既定、read-only実行、schema検証、失敗時の扱い、最終人間評価用の`acceptance_review_bundle`を分けて扱う。

MCP serverからは次で呼べる。

- `llm_review_command_tool`: 実行せずにcommandとpromptをJSON objectに返す。
- `llm_review_run_tool`: 既定はdry-run。`execute=true`の時だけ`codex exec`を起動する。
- `review_if_needed_tool`: deterministic監査結果から判別不能性を検出し、必要な時だけ同じ隔離査読へ渡す。既定はdry-run。
- `llm_review_start_tool`: `codex exec` reviewerを背景ジョブとして開始し、`job_id`を返す。
- `review_if_needed_start_tool`: `review-if-needed`の経路判定を先に行い、必要な時だけ背景ジョブを開始する。
- `llm_review_status_tool`: `job_id`の状態をJSON objectに返す。

背景ジョブの状態は`queued`、`running`、`completed`、`failed`、`timed_out`、`not_needed`、`input_error`、`not_found`のいずれかである。呼出し側が「まだ応答中か、失敗したか、応答済みか」を見る時は、次を読む。

- `running=true`: まだ応答待ちである。
- `process_finished=true`: 背景commandは終了している。
- `review_received=true`: stdoutがJSONとして読め、schema検証まで通った。
- `response_state=invalid_review`: processは終わったが、有効な査読結果ではない。
- `state=timed_out`: timeoutにより終了した。

このjob storeはMCP process内の状態であり、MCP serverの再起動をまたいで永続化しない。長期保存したい場合は、呼出し側が`llm_review_status_tool`の結果を証拠として保存する。

MCP toolは`codex_binary`を受け取らない。実行binaryを外から差し替えられるようにすると、監査補助が任意実行器へ崩れるためである。

## Review If Needed

`review-if-needed`は、決定的監査の結果を直接LLMに丸投げするものではない。先にreview routing判定を行い、決定論規則だけでは価値ある補助査読を捨てることになる場合だけ`candidate_gap_reviewer`へ回す。

`pressure.score` fieldは、候補案の正しさ確率でも、決定的監査の誤り確率でもない。`pressure.score`は査読経路圧である。隔離reviewerを作る価値がどれだけあるかを、不確実性、影響度、反適用条件らしさ、文脈汚染危険、独立査読価値から集約する。

- `warning_class`が`possible false positive`。
- blockerまたはmajorの欠落警告に`nearest_candidates`がある。
- `match_status=unknown`。
- blockerまたはmajorのfindingが`match_status=partial`。
- high-impact findingの`confidence=low`。
- `ambiguity_reasons`に`negated_context`、`quoted_or_historical`、`trace_vocabulary_gap`、`high_impact_low_specificity`がある。
- `generic caution`がevidence、security、meaning、またはsemantic boundaryに触れている。
- document-only監査で、実装証拠なしの強い実行時主張がある。
- `audit_diff`がidentity、persistence、source_of_truth、permissionに触れている。
- blockerではないがscoreが低く、補填査読で不足か過剰警告かを分けたい。
- `review_context.independent_review_requested`または`fresh_eyes_requested`がある。
- `review_context.self_reviewed`、`same_agent_planned_and_implemented`、`long_running_work`など、親文脈への染まりを疑うsignalがある。
- `review_context.public_release`、`external_publication`、`changed_files_count`など、独立した二周目の価値が高いsignalがある。

CLIは次で使う。

```sh
uv run --python 3.13 --project . \
  semantic-guard review-if-needed --file escalation-input.json --dry-run
```

入力JSONは、少なくとも`candidate`と`deterministic_audit`を持つ。

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

`review-if-needed`のJSON outputは`escalation`と`review_result`を持つ。`escalation.needed`が`false`の時、`review_result`は`null`である。`needed`が`true`の時も、既定ではdry-runのcommandとpromptをJSON outputに入れるだけで、`--execute`またはMCPの`execute=true`が明示されるまで`codex exec`は起動しない。

`escalation` JSON objectは互換用の`needed`、`mode`、`target`、`reasons`、`rationale`、`payload`を保ちつつ、次のfieldを持つ。

- `pressure`: score、level、score_semantics。
- `dimensions`: uncertainty、impact、countercondition_plausibility、context_contamination_risk、independent_review_valueなどの圧力段階。
- `signals`: 圧力を作ったinspectableな入力信号。
- `non_decisions`: このroutingが決めていないこと。合否、承認、棄却、finding解除、status / score変更、最終人間判断はここでは変わらない。

`review_result.prompt`には`review_context`と`routing_assessment`が渡される。これにより、隔離reviewerは「なぜ呼ばれたか」を見られるが、「自分が最終判定者である」とは扱えない。

この層の目的は、決定論規則の外側にある見落とし候補を補助材料として露出することである。LLM reviewerの返答は補填候補であり、採用、棄却、延期は親側の判断に残す。

## Logical Audit Boundary

論理監査の`finding.derivation`と`details.logical_trace`は、決定的抽出器が受け入れたfactとexecutable predicateの導出記録である。

LLM reviewerは、論理監査へ追加できるかもしれない候補fact、候補countercondition、質問、補填案を、`missing_aspects`、`possible_counter_conditions`、`supplement_proposals`などの候補fieldへ返してよい。親側が採用する場合だけ、source field、採用理由、対応する要求またはrule、保持する証拠を記録してから、計画、文書、証拠、fixture候補へ移す。しかし、その出力は`candidate`止まりである。決定的証拠または明示的な人間判断なしに、LLM出力を`present` fact、derivation step、finding、受入判断へ昇格してはいけない。

## Limits

この仕組みは不足補填の補助であり、正しさの証明ではない。LLM出力は揺れる。最終判断は、決定的監査、rule catalog、fixture、実行証拠、そして必要な人間判断を合わせて行う。
