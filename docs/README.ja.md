# Criterion Loom 文書一覧

[英語](README.md) · [プロジェクト概要](../README.ja.md)

このページは、目的から文書を選ぶための案内である。現行の正式な基準、運用手引、設計候補、
日付付き証拠、履歴を意図的に分離する。リポジトリ内で近くに置かれていることは、
位置付けが同じであることを意味しない。英語本文の詳細資料には「英語」と表示し、この
日本語一覧には対応する役割と主張境界を残す。

## 目的から選ぶ

| したいこと | 最初に読む | 次に読む |
| --- | --- | --- |
| 数分でプロジェクトを把握する | [プロジェクト概要](../README.ja.md) | [現行公開面](../PUBLIC-SNAPSHOT.md)（英語） |
| CLI / MCP サーバーを動かす | [最短実例](../README.ja.md#最短実例) | [運用手引](operations.md) |
| 構造化機能要求一件を監査する | [要求監査の実例](operations.md#要求関係入力契約) | [解析の流れ](operations.md#解析の流れ)と[終了コード・監査状態](operations.md#終了コードと監査状態) |
| MCP または付属スキルからエージェントに利用させる | [実行面の選択](../README.ja.md#実行面を選ぶ) | [スキルの MCP 契約](../skills/semantic-implementation/references/mcp-contract.md)（英語） |
| 方向拘束結果を解釈する | [方向拘束監査](direction-binding-audit.md) | [実装状態](implementation-status.md) |
| 成熟度・証拠の主張を査読する | [実装状態](implementation-status.md) | [証拠・監査記録](#証拠監査記録) |
| 変更提案・問題報告をする | [変更提案](../CONTRIBUTING.md)（英語） | [利用支援](../SUPPORT.md)（英語）又は[セキュリティ方針](../SECURITY.md)（英語） |
| 0.1.0 との断絶を理解する | [移行手引](migration-v0.1.0-to-v1.0.0.md)（英語） | [正式採用判断](canonical-promotion-decision.md)（英語） |

## 現行の正式な基準と参照資料

次の文書は、現行ソースコード又はその読解規則を説明する。ただし、文書が現行であること
だけでは、実務妥当性や人間受理の証拠にならない。

- [現行公開面](../PUBLIC-SNAPSHOT.md)（英語） — パッケージの同一性、公開コマンド・ツール、
  許される主張、非主張。
- [実装状態](implementation-status.md) — 実装面、日付付き観測、未成立の証拠と
  運用適格性。
- [運用手引](operations.md) — 入力境界、解析器権限、終了コード、自動処理、
  配布物検証、旧版隔離。
- [方向拘束監査](direction-binding-audit.md) — 独立した 1.1.0 限定機能の意味、状態、
  情報不足を推測で補わない対照例、誤り、証拠、限界。
- [原点要求](prototypes/origin-requirement.md) — 歴史的に `prototypes/` 配下へ
  置かれているが、現在も目的上の正式な基準である例外文書。

項目制約については、[要求監査スキーマ](../schemas/audit-result.schema.json)、
[方向拘束スキーマ](../schemas/direction-binding-audit.schema.json)、
[検証基準](../validation/verification-source.json)を機械可読な正式基準とする。
[基幹憲法](../constitution/semantic-guard-constitution.yaml)はプロジェクト水準の
権限境界を定める。

## 契約・保証設計

次の文書は、実装済みの内部補助契約、候補プロファイル、又は設計上の拘束を扱う。
個別文書に明記がない限り、その存在から正式な公開 CLI / MCP 処理経路や人間採択を
推論してはならない。

| 領域 | 現在状態 | 文書 |
| --- | --- | --- |
| 行為証拠と限定保証 | 内部補助契約を実装済み。公開処理経路には未統合 | [行為証拠・保証プロファイル](action-evidence-and-assurance-profile.md) |
| 工程範囲 | 候補。人間採択待ち | [工程プロファイル台帳](lifecycle-profile-registry.md) |
| 追跡と合成 | 内部試作を実装済み。公開処理経路には未統合 | [工程追跡・合成](lifecycle-trace-and-composition.md) |
| 変更後の状態妥当性 | 明示的に有効化する内部契約を実装済み。公開処理経路には未統合 | [状態評価・再評価](state-assessment-and-requalification.md) |
| 修正と責任 | 明示的に有効化する内部契約を実装済み。実務効果は未評価 | [修正循環・責任材料](repair-loop-and-responsibility-material.md) |
| 実地評価設計 | 評価契約を実装済み。実地結果なし | [実地評価・除去比較](field-evaluation-and-ablation.md) |
| 成果評価 | 評価契約を実装済み。実参加者・実成果なし | [運用成果評価](operational-outcome-evaluation.md) |
| 運用適格性と移行 | 内部契約実装済み。運用適格性・切替なし | [運用適格性・移行](operational-qualification-and-transition.md) |
| 安全運用境界 | 内部整合性の監査を実装済み。安全性に関する結論なし | [安全運用境界](secure-operation-boundary.md)（英語） |
| 工学知の統治 | 候補。実行時権限は `none` | [工学規則集の統治](engineering-rule-pack-governance.md) |

## 証拠・監査記録

日付付き記録が支持するのは、記録名が示す対象、ソースコードのハッシュ値又はコミット、環境、
観測時点だけである。ソースツリーが変わっても、その記録が現行版を示す証拠へ
自動的に更新されるわけではない。

| 記録 | 読解上の役割 |
| --- | --- |
| [公開文書監査、2026-08-27](audits/public-document-audit-2026-08-27.md) | 価値を先に示す構成、日本語、リポジトリ内リンク、契約境界及び手元での検証に関する統合前記録 |
| [方向拘束統合、2026-08-23](audits/direction-binding-integration-2026-08-23.md) | 1.1.0 のソースコード、配布物、登録例、GitHub 統合に関する日付付き証拠 |
| [リポジトリ統一、2026-08-24](repository-unification-2026-08-24.md)（英語） | 移管前のリポジトリ同一性と転送境界 |
| [移管後観測、2026-08-24](audits/repository-transfer-observation-2026-08-24.md)（英語） | リポジトリ移管後に分離して採取した観測 |
| [v1.0.0 正式採用監査、2026-07-17](audits/canonicalization-audit-v1.0.0-2026-07-17.md)（英語） | 1.0.0 昇格対象の証拠。1.1.0 へ自動一般化しない |
| [v1.0.0 公開時点記録、2026-07-17](audits/public-snapshot-v1.0.0-2026-07-17.md)（英語） | 凍結された歴史的公開面 |
| [試作全体評価、2026-07-11](audits/semantic-guard-full-evaluation-2026-07-11.md) | 公開用に整えた歴史評価。現行実行時の証拠ではない |
| [影響度・実行順、2026-07-16](impact-and-execution-order-2026-07-16.md)（英語） | 候補段階の歴史的優先順位 |

検証基準が宣言する項目について、構造化状態の権威は日付付き報告の便利な要約では
なく [`validation/verification-source.json`](../validation/verification-source.json)
にある。ただし `active_draft` が対象とする範囲には、後から得た観測の全てが含まれる
わけではなく、日付付き 1.1.0
証拠の鮮度を自動回復しない。

## 試作・履歴

- [原点要求](prototypes/origin-requirement.md)だけは配置上の例外である。`OR-01` から
  `OR-03` は現行の目的上の正式な基準だが、隣接する全試作を昇格させるものではない。
- [正式採用判断、2026-07-17](canonical-promotion-decision.md)（英語）は、1.0.0 を正式な基準へ
  昇格した理由と、その歴史的判断が証明しなかったものを記録する。現行 1.1.0 の
  コマンド一覧ではない。
- [要求関係監査の設計文書、2026-07-12](prototypes/requirement-relation-audit-charter-2026-07-12.md)（英語）
  は正式な v1 限定機能に先行した候補段階の設計記録である。
- [立証義務保証グラフの設計文書、2026-07-16](prototypes/proof-obligation-assurance-graph-charter-2026-07-16.md)（英語）
  は候補資料であり、採択済み公開処理経路ではない。
- [検証台帳完全性の設計文書、2026-07-16](prototypes/verification-register-completeness-charter-2026-07-16.md)（英語）
  は候補資料であり、採択済み公開処理経路ではない。
- [0.1.0 から 1.0.0 への移行](migration-v0.1.0-to-v1.0.0.md)（英語）は、契約置換、
  明示的な旧版経路、別名ではないという境界を説明する。
- [`migration/migration-map.md`](../migration/migration-map.md)（英語）は、保持、置換、
  保管、延期の分類を示す。
- [`legacy/semantic-guard-v0.1.0/`](../legacy/semantic-guard-v0.1.0/) は公開用
  修復済みアーカイブであり、目録が Git 上の元バイト列を指す。

歴史的 GitHub URL を、後の所有者名の下で出来事が起きたかのように書き換えない。
リポジトリ ID の対応と転送境界は、リポジトリ統一記録を使う。

## 状態と同一性の記法

次の状態は、文書の配置を読むための区分であり、対象の同一性ではない。この表の短縮参照では
`・` の右にある UUID が同一性の権威である。他の契約が別形式の安定 `entity_id` を
定める場合も、その定義契約に従って右側識別子を比較し、表示名、配置経路、役割、
内容ハッシュ値の一致だけでは同一対象と断定しない。

| 状態 | 配置又は系譜 | 読解規則 |
| --- | --- | --- |
| `current` | `canonical current・11c55966-ff12-50b9-b069-7bec6ed37cc4`; リポジトリ概要と実装状態 | 現行の正式な基準となるリポジトリ境界を説明する。現行文書であるだけでは実務妥当性又は人間受理の証拠にならない。 |
| `reference` | `direction-binding public slice・245dad95-accf-581c-8b0a-ae1c1f557de4`; `direction-binding-audit.md` と日付なし契約・設計手引 | 意図した意味と拘束を説明する。機械可読スキーマと検証済み挙動が説明文より優先する。 |
| `evidence` | `docs/audits/` と `validation/` の日付・対象拘束済み記録 | 記録対象、ソースコードのハッシュ値、環境、観測時点だけを支持する。現在のソースツリーを自動的に説明しない。 |
| `archive` | `publication-repaired legacy archive・3fd59352-b0d9-58f6-8279-9309c8960631`; 旧版・廃止済み歴史資料 | 履歴又は明示比較のために保存する。歴史的な Git 参照点が元バイト列を持ち、可読なアーカイブには開示済みの公開修復がある。現行の代替経路又は正解基準ではない。 |
| `experimental` | `candidate_ref: local vnext candidate・32646741-8cec-5fe3-b9f3-2971a8a787f0`; `origin-requirement.md` 以外の `docs/prototypes/` 設計文書 | 候補資料だけ。採択、移行、正式な基準としての権限を推論しない。 |
| `local-only` | `derived_from: local feature source snapshot・2b62dfa0-6d90-5c31-ae2d-34ec55c94895`; 方向拘束のソース対応表を参照 | 正式な基準となるリポジトリ境界外に存在する。明示選択しハッシュ値へ拘束したソースだけを統合でき、ルート全体の複写は許可されない。 |

`canonical current・11c55966-ff12-50b9-b069-7bec6ed37cc4` は、この表における
論理上のプロジェクトが現在採用している正式な基準を指す。GitHub のリポジトリ実体である
`canonical repository object・51d473df-7d86-466d-a9f4-47a01ff70d44` とは別の対象
である。

## 参加・保守

- [変更提案](../CONTRIBUTING.md)（英語）
- [利用支援](../SUPPORT.md)（英語）
- [セキュリティ方針](../SECURITY.md)（英語）
- [行動規範](../CODE_OF_CONDUCT.md)（英語）
- [変更履歴](../CHANGELOG.md)（英語）
- [MIT License](../LICENSE)（英語）

最終的な受理、差戻し、保留、棄却、残余危険受容、方針採択、運用切替は監査器の
外に残る。
