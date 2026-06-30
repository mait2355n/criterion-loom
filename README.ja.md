# Criterion Loom 日本語取説

Criterion Loom は、Codex などの開発作業で曖昧になりやすい意味、目的、探索前の質問、要求、決定状態、計画、差分、完了証拠を外へ取り出して点検するための意味先行監査体系である。

package / CLI / MCP server 名は `semantic-guard`。

これは完成済みの要求工学製品ではない。研究試作であり、実務上の判断を代替するものでもない。価値は「賢そうな判断を自動化すること」ではなく、「どこで価値判断が発生しているか」「何を根拠に完了と言っているか」を見える場所へ出すことにある。

## 何をする道具か

Criterion Loom は次の四つを公開上の柱として扱う。

| 公開名 | 役割 | 技術名 |
| --- | --- | --- |
| **Loom Guide** | Codex に監査手順を辿らせる導線。 | `semantic-implementation` skill |
| **Need Thread** | 要求が目的、利害関係者、範囲、品質、優先順位、検証条件を持つかを見る。 | `audit-request` |
| **Plan Warp** | 計画が作業分解、順序、リスク、検証、撤回、最小性、完了証拠を持つかを見る。 | `audit-plan` |
| **Change Weft** | 差分と完了主張が、意味、契約、失敗処理、運用観測、最小性、試験義務、証拠を壊していないかを見る。 | `audit-diff` / `finish-check` |

`explore-request`、`llm-explore-request`、`understand-target`、`audit-decision-state`、`trace-report`、`audit-conventions`、`conventions-catalog`、`doctor`、`audit-result-schema`、`request-exploration-review-schema`、`rule-detector-map`、LLM reviewer、acceptance-review bundle は支援面であり、公開上の四本柱そのものではない。

## 向いている使い方

- 仕様や要求がまだ曖昧な開発作業の事前点検。
- まだ仕様化できない初期案から、対象利用者、重大な曖昧点、聞くべき質問だけを切り出す探索。
- LLM に、入力と文脈から取れる情報をすべて拾わせた上で、欠けている重要情報をすべて問いたださせる探索。
- 決定済み、未決定、仮説、推測、片側観測、時点依存、価値判断、根拠不足を同じ本文から分けて取り出す確認。
- 実装計画が、やることの列挙だけになっていないかの確認。
- 新規依存、抽象、層、schema を足す計画に、既存機能や最小案で足りない理由があるかの確認。
- 差分が公共契約、識別子、保存先、権限、失敗境界、実装複雑性を変えていないかの確認。
- 完了報告に、試験や代表実行の証拠があるかの確認。
- LLM の中途監査を、人間の最終判断と混ぜないための受入束作成。
- 長い作業や公開差分で、親文脈に染まっていない fresh-eyes 査読を補助材料として挟むかの確認。

## 向いていない使い方

- 形式手法や網羅的な要求検証は担当しない。
- 脆弱性走査、配布可否判定、法務確認、品質部門の判定は担当しない。
- 人間の `accept`、`request_revision`、`defer` 判断は自動化しない。
- 単純な typo 修正や一行 command のような軽微作業には使わない。

## 最短実行

公開 snapshot の root で実行する。

```sh
uv run --python 3.13 --project . semantic-guard --help
uv run --python 3.13 --project . semantic-guard explore-request --text "割り勘アプリを作りたい"
uv run --python 3.13 --project . semantic-guard llm-explore-request --text "割り勘アプリを作りたい" --execute
uv run --python 3.13 --project . semantic-guard audit-decision-state --text "未決定: 選定基準。owner: 人間。next_action: 判断条件を書く。"
uv run --python 3.13 --project . semantic-guard audit-request --text "利用者: 開発者。目的: 監査結果を JSON で確認する。受入基準: status と findings が出力される。"
uv run --python 3.13 --project . semantic-guard evaluate-fixtures
uv run --python 3.13 --project . semantic-guard audit-conventions --text "MCP tool が JSON output を返す。"
uv run --python 3.13 --project . semantic-guard doctor
uv run --python 3.13 --project . semantic-guard audit-result-schema
uv run --python 3.13 --project . semantic-guard request-exploration-review-schema
uv run --python 3.13 --project . semantic-guard rule-detector-map
uv run --python 3.13 --project . semantic-guard conventions-catalog
uv run --python 3.13 --project . python -m unittest discover -s tests -v
```

詳細な操作例は `docs/ja/quickstart.md` を読む。

## Loom Guide skill の扱い

Codex 用の companion skill は `skills/semantic-implementation/` に置いている。
wheel にも同じ directory を同封するので、package archive からも skill
本文を取り出せる。

ただし、wheel を install しても Codex の live skill として自動有効化はしない。
Codex に読ませる時は、`skills/semantic-implementation/` を
`$CODEX_HOME/skills/semantic-implementation/` へ同期する。

repository root から同期する場合:

```sh
export CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
mkdir -p "$CODEX_HOME/skills"
rsync -a --delete \
  skills/semantic-implementation/ \
  "$CODEX_HOME/skills/semantic-implementation/"
```

wheel を install 済みの Python 環境から同期する場合:

```sh
export CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
SKILL_SRC="$(
  python - <<'PY'
from pathlib import Path
import semantic_guard

print(Path(semantic_guard.__file__).resolve().parents[1] / "skills" / "semantic-implementation")
PY
)"
test -d "$SKILL_SRC"
mkdir -p "$CODEX_HOME/skills"
rsync -a --delete "$SKILL_SRC/" "$CODEX_HOME/skills/semantic-implementation/"
```

同期後、既に古い skill を読んでいる Codex session があるなら新しい session を開始する。

## 出力の読み方

各監査 command は JSON を返す。中心になる field は次の通り。

- `status`: `pass`、`warn`、`block` のいずれか。
- `score`: 決定論的な粗い評価値。統計的な正確性ではない。
- `findings`: 警告、根拠、修正案、人間判断要否。
- `missing`: 不足している構造要素。
- `next_actions`: 次に確認すべきこと。
- `details`: 規則 ID、非発火規則、論理 trace、fixture 評価などの補助情報。

共通の監査結果 schema は `schemas/audit-result.schema.json` に置く。規則 catalog と検出器の対応は `rule-detector-map` で確認できる。これは保守用の対応表であり、自然文理解の証明ではない。

`explore-request` は、まだ要求文として監査できない初期案に使う軽量な決定論 preflight である。共通の JSON 包みを stdout に返し、`details.schema_version` は `request-exploration/v1` になる。`details.audience_hypotheses`、`details.material_ambiguities`、`details.questions`、`details.spec_outline` を返すが、これは実装計画ではない。CLI usage error は既存通り argparse の message を stderr に出して exit code 2 で終わり、監査対象の警告や blocker は stdout の JSON `status` として返る。

`llm-explore-request` は、網羅的な仕様化前探索に使う LLM 版である。元の入力、任意の context、決定論 preflight 出力を隔離 `codex exec` reviewer へ渡し、取れる fact / inference / hypothesis / unknown / pending decision をすべて拾った上で、欠けている重要情報を質問として返す。既定は dry-run で、`--execute` を付けた時だけ Codex を実行し、`schemas/request-exploration-review.schema.json` で JSON を検証する。有効な出力は `schema_version: "request-exploration-review/v1"` を持ち、`extracted_information`、`audience_hypotheses`、`material_ambiguities`、`questions`、`spec_outline`、`non_decisions`、`limits` を含む。質問は、範囲、資料模型、秘匿性、外部権威、受入証拠、人間判断点を変えるものだけに絞る。これも承認、実装計画、最終受入ではない。

MCP で長くなりそうな LLM 探索を走らせる場合は、`llm_explore_request_start_tool` で開始し、`llm_exploration_status_tool` で `running` / `completed` / `failed` / `timed_out` を見る。`exploration_received=true` は schema-valid な探索 JSON があるという意味で、最終受入ではない。

`audit-decision-state` は、正否を決める command ではない。未決定、不明、仮説、推測、片側観測、時点依存、価値判断、根拠不足を露出させるだけの支援監査である。`details.schema_version` は `decision-state-audit/v1` になる。管制面へ渡すため、`details.decision_state_report.management_handoff_items` には `kind`、`uncertainty_kind`、`decision_state`、`source_excerpt`、`suggested_owner`、`needed_for`、`blocking_status`、`next_action`、`review_at` が入る。独自の失敗経路は増やさない。使用法の誤りは既存通り argparse の message を stderr へ出し、exit code 2 で終わる。監査対象の警告は stdout の JSON に `status`、`findings`、`next_actions` として返る。handoff item を永続記録へ写す時は、ISO 8601 の timezone 付き時刻、evidence source、fact / inference / hypothesis / unknown / pending decision の区別、分かる範囲の decision owner を添える。

監査結果や完了報告を永続証拠として保存する場合は、ISO 8601 の timestamp と timezone、source command または reviewer source、各項目が fact / inference / hypothesis / unknown / pending decision のどれかを記録する。pending decision には、分かる範囲で decision owner を添える。

全体の入出力規約は `docs/conventions/` に置く。`audit-conventions` は、公開 I/O、CLI、MCP、API、記録、repo profile の話が出た時に、出力包み、`schema_version`、欄名、型、失敗形、標準出力/標準誤出力/終了符号、時刻と未確定表示、代表実行証拠が足りているかを見る。初版は `draft` なので、基本は警告で返す。

この repository profile は `schema_version: "criterion-loom-repository-profile/v1"`、`repository_id: "semantic-guard"` として扱う。公開面は CLI、MCP tools、Python package API、README/docs、schema、fixture 評価出力である。主要 command は `audit-request`、`audit-plan`、`audit-diff`、`finish-check`、`audit-conventions`、`evaluate-fixtures`、`doctor`、`rule-detector-map` で、出力形は通常の監査結果 JSON、規約監査 JSON、fixture 評価 JSON、doctor JSON、schema JSON に分かれる。例外は内部設計メモ、局所 calibration label、作業中の acceptance bundle で、非目標は脆弱性走査器、release gate、法務判定器、品質部門判定器、人間の最終受入判断の代替である。

`pass` は「この道具の現在の規則では止めない」という意味であって、実務上の受入を意味しない。最終判断は人間が行う。

## LLM 中途査読

`review-if-needed` は、監査結果を LLM に丸投げして正誤判定させる command ではない。決定論監査の不確実性、影響度、反適用条件の可能性、文脈汚染の危険、独立査読の価値から「査読経路圧」を作り、必要な時だけ隔離された `candidate_gap_reviewer` の dry-run または実行 payload を返す。

`pressure.score` は正しさの確率ではない。`escalation.non_decisions` には、合否、承認、棄却、警告解除、最終人間判断を変更しないことを明示している。

fresh-eyes 査読を明示したい時は、入力 JSON に `review_context.independent_review_requested` または `review_context.fresh_eyes_requested` を入れる。長時間同じ Codex 文脈で計画、実装、確認を進めた場合は `review_context.self_reviewed` や `review_context.same_agent_planned_and_implemented` も使える。
