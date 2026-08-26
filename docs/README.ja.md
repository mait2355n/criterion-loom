# Criterion Loom 文書一覧

[English](README.md) · [プロジェクト概要](../README.ja.md)

この頁は、目的から文書を選ぶための案内である。現行正本、運用手引、設計候補、
日付付き証拠、履歴を意図的に分離する。repository 内で近くに置かれていることは、
権威が等しいことを意味しない。

## 目的から選ぶ

| したいこと | 最初に読む | 次に読む |
| --- | --- | --- |
| 数分でプロジェクトを把握する | [プロジェクト概要](../README.ja.md) | [現行公開面](../PUBLIC-SNAPSHOT.md) |
| CLI / MCP server を動かす | [最短実例](../README.ja.md#最短実例) | [運用手引](operations.md) |
| MCP または Companion Skill から agent と接続する | [実行面の選択](../README.ja.md#実行面を選ぶ) | [Skill の MCP 契約](../skills/semantic-implementation/references/mcp-contract.md) |
| 方向拘束結果を解釈する | [方向拘束監査](direction-binding-audit.md) | [実装状態](implementation-status.md) |
| 成熟度・証拠の主張を査読する | [実装状態](implementation-status.md) | [証拠・監査記録](#証拠監査記録) |
| 変更提案・問題報告をする | [変更提案](../CONTRIBUTING.md) | [利用支援](../SUPPORT.md)又は[保安方針](../SECURITY.md) |
| 0.1.0 との断絶を理解する | [移行手引](migration-v0.1.0-to-v1.0.0.md) | [正本化判断](canonical-promotion-decision.md) |

## 現行正本と参照資料

次の文書は、現行源又はその読解規則を説明する。ただし、文書が現行であること
だけでは、実務妥当性や人間受理の証拠にならない。

- [現行公開面](../PUBLIC-SNAPSHOT.md) — package 同一性、公開命令・工具、
  許される主張、非主張。
- [実装状態](implementation-status.md) — 実装面、日付付き観測、未成立の証拠と
  運用資格。
- [運用手引](operations.md) — 入力境界、解析器権限、終了符号、自動処理、
  配布物検証、旧版隔離。
- [方向拘束監査](direction-binding-audit.md) — 独立した 1.1.0 切片の意味、状態、
  誤り、証拠、限界。
- [原点要求](prototypes/origin-requirement.md) — 歴史的に `prototypes/` 配下へ
  置かれているが、現在も目的正本である例外文書。
- [正本化判断](canonical-promotion-decision.md) — v1 を正本へ昇格した理由と、
  昇格が証明しなかったもの。

欄制約の機械可読な権威は、[要求監査 Schema](../schemas/audit-result.schema.json)、
[方向拘束 Schema](../schemas/direction-binding-audit.schema.json)、
[検証源](../validation/verification-source.json)にある。
[基幹憲法](../constitution/semantic-guard-constitution.yaml)はプロジェクト水準の
権限境界を定める。

## 契約・保証設計

次の文書は、実装済みの内部 sidecar、候補 profile、又は設計上の拘束を扱う。
個別文書に明記がない限り、その存在から正本公開 CLI / MCP workflow や人間採択を
推論してはならない。

| 領域 | 文書 |
| --- | --- |
| 行為証拠と限定保証 | [行為証拠・保証 profile](action-evidence-and-assurance-profile.md) |
| 工程範囲 | [工程 profile 台帳](lifecycle-profile-registry.md) |
| 追跡と合成 | [工程 trace・合成](lifecycle-trace-and-composition.md) |
| 変更後の状態妥当性 | [状態評価・再資格](state-assessment-and-requalification.md) |
| 修正と責任 | [修正 loop・責任材料](repair-loop-and-responsibility-material.md) |
| 実地評価設計 | [実地評価・ablation](field-evaluation-and-ablation.md) |
| 成果評価 | [運用成果評価](operational-outcome-evaluation.md) |
| 運用資格と移行 | [運用資格・移行](operational-qualification-and-transition.md) |
| 安全運用境界 | [安全運用境界](secure-operation-boundary.md) |
| 工学知の統治 | [工学規則 pack 統治](engineering-rule-pack-governance.md) |

## 証拠・監査記録

日付付き記録が支持するのは、記録名が示す対象、源要約値又は commit、環境、
観測時点だけである。現在の木が変わっても、自動的に鮮度を回復しない。

| 記録 | 読解上の役割 |
| --- | --- |
| [方向拘束統合、2026-08-23](audits/direction-binding-integration-2026-08-23.md) | 1.1.0 の源、配布物、登録例、GitHub 統合に関する日付付き証拠 |
| [repository 統一、2026-08-24](repository-unification-2026-08-24.md) | 移管前の repository 同一性と redirect 境界 |
| [移管後観測、2026-08-24](audits/repository-transfer-observation-2026-08-24.md) | repository 移管後に分離して採取した観測 |
| [v1.0.0 正本化監査、2026-07-17](audits/canonicalization-audit-v1.0.0-2026-07-17.md) | 1.0.0 昇格対象の証拠。1.1.0 へ自動一般化しない |
| [v1.0.0 公開 snapshot、2026-07-17](audits/public-snapshot-v1.0.0-2026-07-17.md) | 凍結された歴史的公開面 |
| [試作全体評価、2026-07-11](audits/semantic-guard-full-evaluation-2026-07-11.md) | 公開用に整えた歴史評価。現 runtime の証拠ではない |
| [影響度・実行順、2026-07-16](impact-and-execution-order-2026-07-16.md) | 候補段階の歴史的優先順位 |

検証源が宣言する項目について、構造化状態の権威は日付付き報告の便利な要約では
なく [`validation/verification-source.json`](../validation/verification-source.json)
にある。ただし `active_draft` の範囲は後発観測を全て包摂せず、日付付き 1.1.0
証拠の鮮度を自動回復しない。

## 試作・履歴

- [原点要求](prototypes/origin-requirement.md)だけは配置上の例外である。OR-01 から
  OR-03 は現行の目的正本だが、隣接する全試作を昇格させるものではない。
- [要求関係監査 charter、2026-07-12](prototypes/requirement-relation-audit-charter-2026-07-12.md)
  は正本 v1 切片に先行した候補段階の設計記録である。
- [立証義務保証 graph charter、2026-07-16](prototypes/proof-obligation-assurance-graph-charter-2026-07-16.md)
  は候補資料であり、採択済み公開 workflow ではない。
- [検証台帳完全性 charter、2026-07-16](prototypes/verification-register-completeness-charter-2026-07-16.md)
  は候補資料であり、採択済み公開 workflow ではない。
- [0.1.0 から 1.0.0 への移行](migration-v0.1.0-to-v1.0.0.md)は、契約置換、
  明示的な旧版経路、非 alias 境界を説明する。
- [`migration/migration-map.md`](../migration/migration-map.md)は、保持、置換、
  archive、延期の分類を示す。
- [`legacy/semantic-guard-v0.1.0/`](../legacy/semantic-guard-v0.1.0/) は公開用
  修復済み archive であり、manifest が原 Git byte 列を指す。

歴史的 GitHub URL を、後の所有者名の下で出来事が起きたかのように書き換えない。
repository ID の対応と redirect 境界は、repository 統一記録を使う。

## 状態と同一性の記法

次の状態は配置上の読解役割であり、entity の同一性ではない。label や path は
変わり得るが、`・` の右にある UUID が同一性の権威である。label、path、内容の
一致だけでは同一 entity と断定しない。

| 状態 | 配置又は系譜 | 読解規則 |
| --- | --- | --- |
| `current` | `canonical current・11c55966-ff12-50b9-b069-7bec6ed37cc4`; repository 概要と実装状態 | 現行正本 repository 境界を説明する。現行文書であるだけでは実務妥当性又は人間受理の証拠にならない。 |
| `reference` | `direction-binding public slice・245dad95-accf-581c-8b0a-ae1c1f557de4`; `direction-binding-audit.md` と日付なし契約・設計手引 | 意図した意味と拘束を説明する。機械 Schema と検証済み挙動が説明文より優先する。 |
| `evidence` | `docs/audits/` と `validation/` の日付・対象拘束済み記録 | 記録対象、源要約値、環境、観測時点だけを支持する。現在の木を自動的に説明しない。 |
| `archive` | `publication-repaired legacy archive・3fd59352-b0d9-58f6-8279-9309c8960631`; 旧版・廃止済み歴史資料 | 履歴又は明示比較のために保存する。歴史的 Git anchor が原 byte 列を持ち、可読 archive には開示済みの公開修復がある。現行 fallback 又は真理 oracle ではない。 |
| `experimental` | `candidate_ref: local vnext candidate・32646741-8cec-5fe3-b9f3-2971a8a787f0`; `origin-requirement.md` 以外の `docs/prototypes/` charter | 候補資料だけ。採択、移行、正本権限を推論しない。 |
| `local-only` | `derived_from: local feature source snapshot・2b62dfa0-6d90-5c31-ae2d-34ec55c94895`; 方向拘束 source map 参照 | 正本 repository 境界外に存在する。明示選択し要約値へ拘束した源だけを統合でき、root 全体の複写は許可されない。 |

## 参加・保守

- [変更提案](../CONTRIBUTING.md)
- [利用支援](../SUPPORT.md)
- [保安方針](../SECURITY.md)
- [行動規範](../CODE_OF_CONDUCT.md)
- [変更履歴](../CHANGELOG.md)
- [MIT License](../LICENSE)

最終的な受理、差戻し、保留、棄却、残余危険受容、方針採択、運用切替は監査器の
外に残る。
