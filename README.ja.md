# Criterion Loom

[英語](README.md) · [文書一覧](docs/README.ja.md)

[![CI](https://github.com/mait2355n/criterion-loom/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/mait2355n/criterion-loom/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> 工学上の主張と証拠の隔たりを、検査可能にする。

AI と進めた作業では、事実、仮説、証拠不足、人間受理の違いが会話に
閉じ込められがちだ。Criterion Loom が目指すのは、この四つの違いを、版付きで検査できる
監査成果物として会話の外へ記録できる状態である。流暢な要約を信じるしかない状態から、
修正や判断をやり直せる状態へ変えるためのプロジェクトだ。

`Criterion Loom` は公開プロジェクト名である。現行の配布物と CLI は
`semantic-guard` 版 `1.1.0`、Python で読み込むパッケージ名は `semantic_guard`、
MCP サーバーの入口は `semantic-guard-mcp` である。

> 現行 v1 で公開している監査対象は、一度に一件の構造化された機能要求と、
> それとは独立した限定的な日本語の方向指定（方向拘束）である。計画、差分、完了の主張、
> 開発工程全体の監査は、まだ v1 の CLI / MCP から一貫して利用できない。

## 何が違うのか

単一の点数や合否へ畳むと、本来は別々に答えるべき問いが混ざる。
`semantic-guard` は少なくとも次を分離する。

- 選択した規則が何を結論したか。
- その結論は暫定か終端か。
- 疑義や競合が未解決のままか。
- 宣言された対象をどこまで被覆したか。
- 処理経路を継続、警告、停止のどれに対応付けるか。
- 人間が何かを受理したか。

出力は判断材料であって、人間の判断ではない。解析器の出力だけで、その結論が
正しいと認められることはない。`pass` は正しさ、リリース承認、安全性の認証、
人間による受理のいずれも意味しない。

## 最短実例

必要なのは [Python 3.11 以上](https://www.python.org/)と
[`uv`](https://docs.astral.sh/uv/) である。現段階ではソースコードを取得した
作業ディレクトリから実行する。一般公開されたパッケージ配布先での提供は、ここでは主張しない。
下の結果抽出用コマンドは POSIX シェル記法である。他のシェルでは、パイプ記号 `|` より
前の監査コマンドだけを実行すれば、同じ JSON データを直接読める。

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

この例は二つの境界を示す。規則結果を人間受理へ昇格させないことと、必要な方向が
入力に無ければ慣例から補わないことだ。後者では、情報不足を推測で補わず `gap` とし、
監査 JSON の `workflow_disposition.status` を `warn` とする。
[方向拘束監査](docs/direction-binding-audit.md)には、
明示あり・なしの対照入力と正確な項目状態を示す。

## 現在の公開面

| 能力 | CLI | MCP | 現在の境界 |
| --- | --- | --- | --- |
| 要求関係監査 | `audit-requirement` | `audit_requirement_relations_tool` | 七項目からなる一件の構造化機能要求。形態素解析は `signal_only`、係り受け解析と呼出元提出 LLM 解析は `candidate_only` |
| 方向拘束監査 | `audit-direction-binding` | `audit_direction_binding_tool` | 登録済みの尺度・非尺度日本語表現で、方向指定が同じ対象と操作に直接結び付いているかを検査。制限のない言語理解ではない |
| 値や項目を限定したスキーマの取得 | `schema` | `semantic_guard_schema_tool` | 既知のスキーマ名25件。スキーマが有るだけでは公開処理経路への統合を意味しない |
| 明示的な旧版比較 | `shadow-compare` | `shadow_compare_legacy_tool` | 運用者が所有する外部 0.1.0 ルートを使い、信頼済み比較には基準ハッシュ値の一致を要する。MCP 経路は既定無効で運用者設定が必要。旧版は正解基準ではない |

現行ソースコードには、工程横断と保証に関する候補契約も存在する。設計や試験の材料では
あるが、公開 CLI / MCP から一貫して利用できる機能としては扱っていない。

## 実行面を選ぶ

| 実行面 | 向く用途 | 最初の一手 |
| --- | --- | --- |
| CLI | 人間、スクリプト、CI が実行と JSON 保存を担う | `uv run --locked semantic-guard --help` |
| MCP | エージェント用クライアントが標準入出力を通じて同じ限定監査機能を使う | `uv run --locked semantic-guard-mcp` |
| 付属スキル | Codex が監査境界を保って設計・実装作業を進める | [`skills/semantic-implementation/`](skills/semantic-implementation/) |

`command`、`args`、`cwd` を受ける MCP クライアントなら、ソースコードの
作業ディレクトリに対する構成は概ね次と等価になる。

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

項目名はクライアントごとに異なる。サーバーとの通信には標準入出力を使う。上記 JSON の
項目構成はクライアント固有で、サーバー契約には含まれない。付属スキルはリポジトリ
資料であり、`wheel` / `sdist` には含まれず、自動導入もされない。

## 形容より証拠

2026-08-23 付の 1.1.0 証拠記録には、次の観測がある。

- 記録された Python 3.11 / 3.13 環境でソースコード試験608件が通過。
- 選択したローカルの `wheel` / `sdist` に対する配布契約検証20件が通過。
- パッケージ内のスキーマ24件、CLIコマンド四件、MCPツール四件を観測。
- 記録された、新しく構築した `wheel` の Sudachi 環境で、登録済み方向の `gap` / `bound` 222組を再現。
- 方向拘束の限定機能を GitHub の `main` へ統合し、定義済み CI 四ジョブが通過。

これらは記録された対象に拘束され、現在の `HEAD` を自動的に再検証するものでは
ない。契約と登録例の観測であって、ベンチマーク、採用実績、実務精度、無制限の
日本語被覆、運用適格性、人間受理ではない。対象と限界は
[実装状態](docs/implementation-status.md)と日付付きの
[方向拘束統合証拠](docs/audits/direction-binding-integration-2026-08-23.md)に記録する。

## 文書

| 目的 | 文書 |
| --- | --- |
| 現行パッケージと非主張を把握する | [現行公開面](PUBLIC-SNAPSHOT.md)（英語） |
| CLI / MCP サーバーを運用・自動化する | [運用手引](docs/operations.md) |
| 明示済み・欠落の方向拘束結果を比較する | [方向拘束監査](docs/direction-binding-audit.md) |
| 実装と証拠状態を検査する | [実装状態](docs/implementation-status.md) |
| 現行の正式な基準、証拠、履歴、試作を辿る | [文書一覧](docs/README.ja.md) |
| 旧 0.1.0 系から移る | [移行手引](docs/migration-v0.1.0-to-v1.0.0.md)（英語） |

項目制約については機械可読スキーマと検証基準を説明文より優先する。日付付き報告は
記録対象と記録時点の証拠であり、現在のソースツリーを自動的に説明しない。

## 版と旧版の境界

公開用修復済みの旧 `semantic-guard 0.1.0` は
[`legacy/semantic-guard-v0.1.0/`](legacy/semantic-guard-v0.1.0/) に保存する。
元のバイト列は保管資料の目録が示すタグとコミットに残る。旧版の依頼、計画、
差分、完了、規約、査読、受理材料に関する各コマンドは、v1 でそのまま読み替えられる別名ではない。

現行ソースコードの同一性、実務妥当性、方針採択、運用既定、歴史保存は別の状態である。
歴史的な [1.0.0 正式採用判断](docs/canonical-promotion-decision.md)（英語）と
[変更履歴](CHANGELOG.md)（英語）を参照する。

## 参加と支援

- [変更提案](CONTRIBUTING.md)（英語）
- [利用支援](SUPPORT.md)（英語）
- [セキュリティ方針](SECURITY.md)（英語）
- [行動規範](CODE_OF_CONDUCT.md)（英語）
- [MIT License](LICENSE)（英語）

最終受理、残余危険の受容、方針採択、既定経路の切替、旧版廃止は人間の判断に
残る。
