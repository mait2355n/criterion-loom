# Criterion Loom

[English](README.md) · [文書一覧](docs/README.ja.md)

[![CI](https://github.com/mait2355n/criterion-loom/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/mait2355n/criterion-loom/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> 工学上の主張と、その証拠の隙間を、検査可能にする。

AI と進めた作業では、事実、仮説、証拠不足、人間受理の違いが会話に
閉じ込められがちだ。Criterion Loom は、この四者の区別を版付きで検査可能な
監査成果物へ外在化する。流暢な要約を信じるしかない状態から、次の修正や判断へ
戻せる状態へ変えるためのプロジェクトである。

`Criterion Loom` は公開プロジェクト名である。現行の源実装、Python package、
CLI、MCP server の技術名は `semantic-guard 1.1.0` である。

> 現行 v1 の公開 workflow が監査するのは、一度に一件の構造化機能要求と、
> それとは独立した限定的な日本語方向拘束表現である。計画、差分、完了主張、
> 全工程の監査は、まだ正本 v1 の CLI / MCP へ公開統合していない。

## 何が違うのか

単一の点数や合否へ畳むと、本来は別々に答えるべき問いが混ざる。
`semantic-guard` は少なくとも次を分離する。

- 選択した規則が何を結論したか。
- その結論は暫定か終端か。
- 疑義や競合が未解決のままか。
- 宣言された対象をどこまで被覆したか。
- workflow を継続、警告、停止のどれに射影するか。
- 人間が何かを受理したか。

出力は判断材料であって、判断そのものではない。解析器の出力が自ら支持権限を
獲得することはなく、`pass` は正しさ、release 承認、保安認証、人間受理の
いずれも意味しない。

## 最短実例

必要なのは [Python 3.11 以上](https://www.python.org/)と
[`uv`](https://docs.astral.sh/uv/) である。現段階では源 checkout から実行する。
公開 package index 上の成果物は、ここでは主張しない。下の射影命令は POSIX shell
記法である。他の shell では pipe より前の監査命令だけを実行すれば、同じ JSON
payload を直接読める。

```sh
git clone https://github.com/mait2355n/criterion-loom.git
cd criterion-loom

uv run --locked --extra nlp-ja semantic-guard audit-direction-binding \
  --text '横一列を左から右へ辿るとき、Aの次の項目はどれですか？' \
  --morphology sudachi \
  | python3 -c 'import json,sys; r=json.load(sys.stdin); print(json.dumps({"state": r["primary_rule_evaluation"]["state"], "direction": r["direction_binding_summary"]["frames"][0]["direction_binding"]["direction"], "workflow": r["workflow_disposition"]["status"], "human_acceptance": r["acceptance_owner"]["acceptance_status"]}, indent=2))'
```

抜き出した結果は次の通りになる。

```json
{
  "state": "satisfied",
  "direction": "left_to_right",
  "workflow": "pass",
  "human_acceptance": "pending"
}
```

最後の一行は意図した結果である。規則は左から右への直接拘束を見付けたが、
人間の判断までは僭称しない。同じ命令の入力を
`横一列で、Aの次の項目はどれですか？` に替えると、限定監査の JSON は
`primary_rule_evaluation.state=gap` と `workflow_disposition.status=warn` を返す。

## 現在の公開面

| 能力 | CLI | MCP | 現在の境界 |
| --- | --- | --- | --- |
| 要求関係監査 | `audit-requirement` | `audit_requirement_relations_tool` | 七欄からなる一件の構造化機能要求。形態素解析は `signal_only`、係り受け解析と呼出元提出 LLM 解析は `candidate_only` |
| 方向拘束監査 | `audit-direction-binding` | `audit_direction_binding_tool` | 登録済みの尺度・非尺度日本語表現と直接付着。制限のない言語理解ではない |
| 閉 Schema 取得 | `schema` | `semantic_guard_schema_tool` | 既知の Schema 名24件。Schema が有るだけでは公開 workflow への統合を意味しない |
| 明示的な旧版比較 | `shadow-compare` | `shadow_compare_legacy_tool` | 運用者所有の外部 0.1.0 root を使い、信頼済み比較には基準要約値の一致を要する。MCP 経路は既定無効で運用者設定が必要。旧版は真理 oracle ではない |

現行源には、工程横断と保証に関する候補契約も存在する。設計や試験の材料では
あるが、暗黙に公開済みの一貫機能へ昇格させてはいない。

## 実行面を選ぶ

| 実行面 | 向く用途 | 最初の一手 |
| --- | --- | --- |
| CLI | 人間、script、CI が実行と JSON 保存を所有する | `uv run --locked semantic-guard --help` |
| MCP | agent client が標準入出力越しに同じ限定工具を使う | `uv run --locked semantic-guard-mcp` |
| Companion Skill | Codex が監査境界を保って設計・実装作業を進める | [`skills/semantic-implementation/`](skills/semantic-implementation/) |

`command`、`args`、`cwd` を受ける MCP client なら、源 checkout に対する構成は
概ね次と等価になる。

```json
{
  "mcpServers": {
    "semantic-guard": {
      "command": "uv",
      "args": ["run", "--locked", "semantic-guard-mcp"],
      "cwd": "/absolute/path/to/criterion-loom"
    }
  }
}
```

欄名は client ごとに異なる。server 契約は標準入出力輸送であり、上記 JSON の
欄構成は client 固有で server 契約に含まれない。Companion Skill は repository
資料であり、wheel / sdist には含まれず、自動導入もされない。

## 形容より証拠

日付付きの 2026-08-23 版 1.1.0 証拠記録には、次の観測がある。

- 記録された Python 3.11 / 3.13 環境で源試験608件が通過。
- 選択した局所 wheel / sdist に対する配布契約検証20件が通過。
- package 内の Schema 24件、CLI四命令、MCP四工具を観測。
- 記録された fresh-wheel Sudachi 環境で、登録済み方向の gap / bound 222組を再演。
- 方向拘束切片を GitHub main へ統合し、定義済み CI 四 job が通過。

これらは記録された対象に拘束され、現在の HEAD を自動的に再検証するものでは
ない。契約と登録例の観測であって、benchmark、採用実績、実務精度、無制限の
日本語被覆、運用資格、人間受理ではない。対象と限界は
[実装状態](docs/implementation-status.md)と日付付きの
[方向拘束統合証拠](docs/audits/direction-binding-integration-2026-08-23.md)に記録する。

## 文書

| 目的 | 文書 |
| --- | --- |
| 現行 package と非主張を把握する | [現行公開面](PUBLIC-SNAPSHOT.md) |
| CLI / MCP server を運用・自動化する | [運用手引](docs/operations.md) |
| 方向拘束結果を解釈する | [方向拘束監査](docs/direction-binding-audit.md) |
| 実装と証拠状態を検査する | [実装状態](docs/implementation-status.md) |
| 現行正本、証拠、履歴、試作を辿る | [文書一覧](docs/README.ja.md) |
| 旧 0.1.0 系から移る | [移行手引](docs/migration-v0.1.0-to-v1.0.0.md) |

欄制約については機械 Schema と検証源が説明文より優先する。日付付き報告は
記録対象と記録時点の証拠であり、現在の木を自動的に説明しない。

## 版と旧版の境界

公開用修復済みの旧 `semantic-guard 0.1.0` は
[`legacy/semantic-guard-v0.1.0/`](legacy/semantic-guard-v0.1.0/) に保存する。
原 byte 列は archive manifest が示す tag と commit に残る。旧版の依頼、計画、
差分、完了、規約、査読、受理材料の命令は、v1 の透過 alias ではない。

現行源の同一性、実務妥当性、方針採択、運用既定、歴史保存は別の状態である。
[正本化判断](docs/canonical-promotion-decision.md)と
[変更履歴](CHANGELOG.md)を参照する。

## 参加と支援

- [変更提案](CONTRIBUTING.md)
- [利用支援](SUPPORT.md)
- [保安方針](SECURITY.md)
- [行動規範](CODE_OF_CONDUCT.md)
- [MIT License](LICENSE)

最終受理、残余危険の受容、方針採択、既定経路の切替、旧版廃止は人間の判断に
残る。
