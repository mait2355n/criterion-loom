# Agent Revision Loop Positioning

作成日: 2026-06-30

## Purpose

この文書は、Criterion Loomの公開READMEで追加された「監査結果をAIエージェントの修正ループへ戻す」という位置付けを記録する。目的は、README、公開説明、今後の公開文書で、古い「人間の判断材料だけを作る監査ツール」という説明へ戻らないようにすることである。

## Audience And Use

利用者は、このリポジトリの公開説明、companion skill説明、または公開 repository の紹介文を整える人間とCodexである。

使い方は次の通り。

1. Criterion Loomを外向けに説明する前に、この文書の「変更の要点」と「更新後の短い説明案」を確認する。
2. 説明文に「AIエージェントの修正作業へ戻す」観点が入っているかを確認する。
3. 「自動承認」「人間判断の代替」「高精度な自然言語理解」のような過大主張が混ざっていないかを確認する。

## Status And Scope

この文書は 2026-06-30 時点の位置付け変更を記録する作業記録である。現在の公開面は README、docs/README.md、docs/ja/README.md、docs/ja/public-positioning-note.md を優先し、この文書は「AIエージェントの修正ループへ戻す」という説明を維持するための補助記録として読む。

## 対象

- 公開リポジトリ: `https://github.com/mait2355n/criterion-loom`
- 変更後HEAD: `f3b2d527a844817277ec88ed639a5e1bdfb74ce8`
- 直近の位置付け変更commit: `f3b2d52 Clarify agent revision loop`
- 比較元commit: `a8bf0c4 Clarify Criterion Loom positioning`

## 変更された主な文書

- `README.md`
- `README.ja.md`
- `docs/acceptance-review-bundle.md`
- `skills/semantic-implementation/README.md`
- `skills/semantic-implementation/SKILL.md`

## 変更の要点

今回の変更で、Criterion Loomの説明は「監査結果を人間の最終判断材料として見せる道具」だけではなく、「監査結果をCodexなどのAIエージェントの作業ループへ戻し、再計画、再実装、変更説明、完了主張の修正に使う道具」として明確化された。

従来の説明でも人間判断を代替しないことは明記されていたが、AIエージェント側の修正ループへの還元が弱かった。今回の変更により、次の流れが表に出た。

1. CodexなどのAIエージェントが依頼、計画、変更説明、完了主張を作る。
2. Criterion Loomが曖昧さ、不足、未決定、証拠不足をJSON監査結果として返す。
3. AIエージェントが監査結果を受け取り、依頼解釈、計画、差分説明、検証、完了報告を修正する。
4. 最後に人間が`accept`、`request_revision`、`defer`を判断する。

## 変更後の中心表現

日本語READMEでは、次の意味が追加された。

- AIの出力をそのまま正解や承認結果として扱うものではない。
- 監査結果は、AIエージェントが依頼解釈、計画、変更説明、完了主張を修正するための指摘として作業ループへ戻せる。
- 同じ出力は、人間が最終的に`accept`、`request_revision`、`defer`を判断するための材料にもなる。
- 価値は、価値判断や完了根拠を見える場所へ出し、その結果をAIエージェントの修正、追加検証、再提示にも戻すことにある。

英語READMEでは、次の意味が追加された。

- Audit output is meant to feed an agentic revision loop.
- Codex or another AI agent can use findings to revise request framing, plans, change explanations, and completion claims.
- Human final decision is still required.

## 影響する外向け説明

外向けにCriterion Loomを説明する時は、単なる「人間の判断材料を作る監査ツール」よりも、次の表現の方が現在の公開READMEに合う。

```text
Codex等のAIエージェントを用いた開発作業で、依頼、計画、変更説明、完了主張に含まれる曖昧さや不足をJSONの監査結果として外へ取り出し、AIエージェントの修正作業と人間の最終判断材料へ接続するツール。
```

避けた方がよい表現は次の通り。

- AIの出力を自動承認する。
- 人間判断を代替する。
- 一般文書を高精度に理解できる要求工学製品。
- 監査結果を人間が読むだけの静的レポートとして扱う。

## 公開説明へ反映すべき点

公開 README、companion skill 説明、repository 紹介文では、次の要素を入れると整合する。

- 「依頼、計画、変更説明、完了主張」という入力対象。
- 「JSONの監査結果」として不足や曖昧さを返すこと。
- 「AIエージェントの再計画、再実装、完了報告修正へ戻せる」こと。
- 「人間の最終判断を代替しない」こと。
- 「公開可能な v0.1 ツールだが、判定は語彙規則と軽量な構造検査に基づく」こと。
- 「fixture評価はローカルな回帰確認であり、一般文書に対する精度保証ではない」こと。

## 更新後の短い説明案

```text
Criterion Loomは、Codex等のAIエージェントを用いた開発作業で、依頼、計画、変更説明、完了主張に含まれる曖昧さや不足をJSONの監査結果として返し、AIエージェントの修正作業と人間の最終判断材料へ接続する意味先行監査ツールです。
```

## 注意

この変更は、Criterion Loomをより強く見せるための誇張ではない。むしろ、監査結果の使い道を正確に分けるための変更である。

- AIエージェント側: 監査結果を受け取り、作業内容を修正する。
- 人間側: 修正後の成果物と監査材料を見て、最終的に受理、差戻し、保留を判断する。

この二つを混同しないことが、今回の位置付け変更の中核である。
