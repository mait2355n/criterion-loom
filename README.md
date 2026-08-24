# Criterion Loom

Criterion Loom は公開 project 名であり、配布 package、Python module、CLI 及び MCP server の技術名は `semantic-guard 1.1.0` である。

`semantic-guard` は、開発工程で作られた要求、計画、行動、実現方法、証拠の関係を、要求工学・計画工学・ソフトウェアシステム工学の知識に照らして監査可能な材料へ変えるための監査系である。AI エージェントの判断や行動についても、何が観測され、何が導出され、何が未立証かを分離し、版付き JSON 契約として後から検査できる形へ残すことを目指す。

1.0.0 は、この原点目的へ向けて再構成した局所契約と最初の要求監査縦断を、リポジトリ・配布物・CLI・MCP の正本へ昇格した版である。旧 `0.1.0` の振舞いを正解として写した版ではない。

1.1.0 はその契約を変えず、同一対象・同一操作の方向開放表現に方向限定表現が直接結合しているかを検査する、独立した方向拘束監査を追加する。ローカル研究木全体や後続候補木を正本化した版ではない。

## 1.1.0 が実装する範囲

公開実行面は四つに限る。

1. `audit-requirement` / `audit_requirement_relations_tool`
   : 一つの構造化機能要求を義務へ分解し、関係、被覆、競合、疑義、保留、未解決を閉じた監査結果として返す。
2. `shadow-compare` / `shadow_compare_legacy_tool`
   : 明示的に指定された、要約値で固定済みの旧版実行環境と同じ入力を比較し、差分を観測する。旧版を正解 oracle にはしない。
3. `schema` / `semantic_guard_schema_tool`
   : 要求監査及び sidecar の版付き JSON Schema を取得する。Schema を取得できることは、その sidecar が公開縦断へ統合済みという意味ではない。
4. `audit-direction-binding` / `audit_direction_binding_tool`
   : 登録済みの尺度方向と非尺度方向について、方向開放表現と直接結合した方向限定表現を監査する。形態素解析は `signal_only`、数値投影は補助証拠に限り、結果から方向を逆算しない。

現公開縦断が監査する工程面は `requirement` のみである。計画、設計、実装、試験、配備、運用、変更、廃止を含む十工程には候補 profile と sidecar 契約があるが、人間採択、工程内 adapter、共通 workflow、失効伝播、公開 CLI/MCP 統合は未完了である。

## 原点目的と現在の境界

原点目的は、各開発工程の計画・行動・実現方法を体系化された工学知識で監査し、誤り候補、根拠不足、未決定、残余危険を外から読める材料として示すことにある。AI エージェントについては、供給された行為記録から限定的な保証命題を検査することも含む。

ただし、1.1.0 の公開面から次を推論してはならない。

- 任意の実務文書に対する精度又は再現率が確認された。
- 全開発工程が公開 workflow で監査できる。
- AI エージェントが外部で実際に行為したこと又は行為主体の真正性が証明された。
- 候補規則束又はライフサイクル profile が人間に採択された。
- `pass` が人間受理、無条件の正しさ、保安認証又は運用資格を意味する。
- リポジトリ正本化によって運用環境の既定経路まで切り替わった。

正本化、局所契約適合、実務妥当性、人間採択、運用既定化、外部真正性は別の状態である。

## 要求監査の順序

要求監査は概ね次の順で進む。

```text
構造化欄・直接規則
        ↓
未解決義務の再集約
        ↓
形態素解析の信号
        ↓
係り受け・作用域・述語項候補
        ↓
呼出元が提出した LLM 候補
        ↓
版付き規則による再評価と公開結果
```

形態素解析は `signal_only`、依存構造解析と LLM は `candidate_only` が権限上限である。解析器や LLM の生出力だけで義務を満足させたり、保留を適用・解除したりしない。能力欠落、部分被覆、由来不整合、不正な原文範囲は明示して縮退させる。

## 導入と最短実行

Python 3.11 以上と `uv` を用いる。

```sh
uv sync --locked
uv run --locked semantic-guard --help
uv run --locked semantic-guard audit-requirement \
  --text 'システムは、監査結果を JSON として保存しなければならない。'
uv run --locked semantic-guard schema audit-result
```

日本語の形態素解析と依存構造解析を有効にする場合は任意依存を導入する。

```sh
uv sync --locked --extra nlp-ja --extra nlp-ja-dependency
uv run --locked semantic-guard audit-requirement \
  --file requirement.txt \
  --morphology sudachi \
  --dependency ginza
uv run --locked semantic-guard audit-direction-binding \
  --text '横一列を左から右へ辿るとき、Aの次の項目はどれですか？' \
  --morphology sudachi
uv run --locked semantic-guard schema direction-binding-audit
```

呼出元エージェントが LLM 候補を提出する場合は、先に閉契約を取得し、原文要約値と範囲を結び付ける。

```sh
uv run --locked semantic-guard schema llm-candidate-input > llm-candidate-input.schema.json
uv run --locked semantic-guard audit-requirement \
  --file requirement.txt \
  --llm-candidates llm-candidates.json
```

MCP は標準入出力輸送で起動する。

```sh
uv run --locked semantic-guard-mcp
```

公開 MCP 工具は `audit_requirement_relations_tool`、`audit_direction_binding_tool`、`shadow_compare_legacy_tool`、`semantic_guard_schema_tool` の四つである。

## 結果の読み方

監査結果は少なくとも次を分離する。

- 義務の結論: `satisfied / refuted / undetermined / not_applicable / invalid`
- 確定性: `provisional / terminal / invalid`
- 疑義: `none / open / conflict`
- 被覆: `complete / partial / not_evaluated / failed`
- 作業上の扱い: `pass / warn / block`

`pass` は、版を固定した現在の監査規則が作業を停止しないという射影にすぎない。人間の最終的な受理、差戻し、保留、延期、棄却を代行しない。

## 旧版

旧 `semantic-guard 0.1.0` は [archive manifest](legacy/semantic-guard-v0.1.0/ARCHIVE-MANIFEST.md) の境界で保存する。公開上の誤読を避けるため旧文書には限定的な表現修復を施しており、元の byte snapshot は manifest が指す Git anchor に残る。旧 CLI の要求・計画・差分・完了・規約・査読機能は 1.x へ透過統合されていない。利用する場合は旧版を明示的に選び、現行監査結果と混同しないこと。

リポジトリ内の公開用修復済み archive は、そのまま `shadow-compare` が信頼する実行根ではない。影比較には、運用者が所有する外部旧版 root、固定された相対配置、実行環境、基準 manifest と要約値が必要である。詳しくは [移行手引](docs/migration-v0.1.0-to-v1.0.0.md) を参照する。

## 正本と記録

- [基幹憲法](constitution/semantic-guard-constitution.yaml)
- [現行公開面の要約](PUBLIC-SNAPSHOT.md)
- [公開監査結果 schema](schemas/audit-result.schema.json)
- [方向拘束監査 schema](schemas/direction-binding-audit.schema.json)
- [方向拘束監査の意味と限界](docs/direction-binding-audit.md)
- [方向拘束移植の由来記録](migration/direction-binding-source-map-2026-08-23.json)
- [GitHub repository 統一の移管前記録](docs/repository-unification-2026-08-24.md)
- [repository 統一の移管前機械記録](migration/repository-unification-2026-08-24.json)
- [移管後の公開観測](docs/audits/repository-transfer-observation-2026-08-24.md)
- [検証要求・状態正本](validation/verification-source.json)
- [実装状態](docs/implementation-status.md)
- [運用手引](docs/operations.md)
- [正本化判断](docs/canonical-promotion-decision.md)
- [0.1.0 から 1.0.0 への移行](docs/migration-v0.1.0-to-v1.0.0.md)
- [正本化監査](docs/audits/canonicalization-audit-v1.0.0-2026-07-17.md)
- [変更履歴](CHANGELOG.md)

`validation/*-2026-07-16.json` などの日付付き記録は作成時点の歴史的観測である。現在の源、1.1.0 配布物、実務妥当性又は人間受理へ読み替えない。

## 開発時検証

```sh
uv lock --check
uv run --locked python -m unittest discover -s tests -v
uv run --locked python scripts/validate_verification_source.py
uv run --locked python scripts/render_verification_projection.py --check
uv run --locked python scripts/validate_engineering_rule_pack.py
uv build
uv run --locked python scripts/verify_packaged_contracts.py \
  --wheel dist/semantic_guard-1.1.0-py3-none-any.whl \
  --sdist dist/semantic_guard-1.1.0.tar.gz
```

これらの成功が立証するのは、対象版の局所契約、試験、検証源整合、配布資源の再演までである。実務資料での妥当性、人間採択、運用資格は別途評価する。

## 参加と報告

- 変更提案: [CONTRIBUTING.md](CONTRIBUTING.md)
- 保安問題: [SECURITY.md](SECURITY.md)
- 利用支援: [SUPPORT.md](SUPPORT.md)
- Companion Skill: [`skills/semantic-implementation/`](skills/semantic-implementation/)

ライセンスは [MIT](LICENSE)。
