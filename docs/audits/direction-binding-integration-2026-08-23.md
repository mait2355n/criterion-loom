# 方向拘束公開切片の GitHub 統合証拠

> 2026-08-23 時点の歴史的統合証拠である。owner/name、main、CI 及び配布状態の現況は、この文書から推定しない。

- identity: `direction-binding hosted integration evidence・b811c797-d73c-459e-b44d-6299705fc613`
- subject_ref: `direction-binding public slice・245dad95-accf-581c-8b0a-ae1c1f557de4`
- repository_ref: `canonical current・11c55966-ff12-50b9-b069-7bec6ed37cc4`
- recorded_at: `2026-08-23T15:04:18Z`
- evidence_status: `observed`
- human_acceptance: `pending`

## 状態要約

| Field | Value |
| --- | --- |
| `context` | 方向拘束公開切片1.1.0の実装commit、PR merge及びmerge後main CIを分離して記録する |
| `current_state` | 実装commit `c10ba59f8ab16659b50e9cbf13da07c9889ed195` はPR #3を通じてmainへmergeされ、merge commit `a77c3cbdc69295572e90333e2a6e9da690fbbb6d` に対するpush CIが成功した |
| `next_action` | 実務母集団の妥当性、人間受理、公開索引配布及び運用採択を各々別証拠で判断する |
| `detail_refs` | [PR #3](https://github.com/morie-lene/criterion-loom/pull/3)、[PR CI](https://github.com/morie-lene/criterion-loom/actions/runs/32646627913)、[merge後main CI](https://github.com/morie-lene/criterion-loom/actions/runs/32646816407)、[source map](../../migration/direction-binding-source-map-2026-08-23.json) |
| `inference_status` | GitHub source統合と当該merge SHAのhosted CI成功は観測済み。実務妥当性、外部真正性、公開配布及び人間受理は未立証 |
| `pending_decision` | 公開契約の最終人間受理、実務評価方針、公開release及び運用採択 |

## GitHub 観測

| 対象 | 観測 |
| --- | --- |
| 実装commit | `c10ba59f8ab16659b50e9cbf13da07c9889ed195`; `Add bounded direction-binding audit surface` |
| PR | [#3](https://github.com/morie-lene/criterion-loom/pull/3); `MERGED`; merge時刻 `2026-08-23T14:53:27Z` |
| merge commit | `a77c3cbdc69295572e90333e2a6e9da690fbbb6d`; `recorded_at` 時点のremote `main` とAPI参照が一致 |
| PR CI | [run 32646627913](https://github.com/morie-lene/criterion-loom/actions/runs/32646627913); Python 3.11、Python 3.13、凍結0.1.0煙試験、wheel及び導入済み公開面の四jobが成功 |
| merge後main CI | [run 32646816407](https://github.com/morie-lene/criterion-loom/actions/runs/32646816407); subject SHA `a77c3cbdc69295572e90333e2a6e9da690fbbb6d`; push event; `2026-08-23T14:56:56Z` 完了; 同じ四jobが成功 |

merge後main CIの包装jobは1.1.0 wheel/sdistを構築し、配布契約検証、導入済みCLI/MCP在庫検査及びartifact uploadを通過した。本記録はupload済みartifactを再取得してdigestを採取していないため、下記の局所wheel digestをhosted artifactのdigestへ読み替えない。

## 局所補助証拠

下記artifact digestは、実装commit `c10ba59f8ab16659b50e9cbf13da07c9889ed195` と同じ内容を持つ、統合証拠文書追加前の局所実装作業木で採取した。本証拠文書を加えた後続sdist又はhosted artifactのdigestではない。

| 観測 | 結果 |
| --- | --- |
| CPython 3.13 unit suite | 608件成功 |
| 隔離CPython 3.11 unit suite | 608件成功 |
| JSON Schema | Draft 2020-12の公開24件が自己検査成功 |
| 包装検証 | 20件成功; `cli_commands=4`、`public_schemas=24`、`mcp_tools=4` |
| 局所実装wheel | SHA-256 `67d789f0aa824dbed29fa1e829390fef8ba1f51956a94e940538553418b456ca` |
| 局所実装sdist | SHA-256 `ed4061171a5b044bbee33f345ce16bd23c21313d51182936a834fb79c552989f` |
| 実Sudachi行列 | SudachiPy 0.6.11、SudachiDict-core 20260428、split mode Cで登録済み222組成功 |
| 選択源泉 | source mapの五つのsource/target SHA-256が一致 |
| 凍結旧版 | `legacy/`差分0 |

## 許される推論

- 方向拘束公開切片の源、CLI、MCP、Schema、試験、資料及び包装検証器が、上記merge commitのGitHub mainへ統合された。
- PR枝とmerge後mainの双方で、定義済みGitHub CI四jobが成功した。
- 局所で選択した配布物は、記録した版と環境において配布契約20件及び実Sudachi 222組を通過した。

次は推論しない。

- hosted artifactと局所wheelがbyte同一である。
- 公開索引上に1.1.0配布物又はrelease/tagが存在する。
- 222組から未登録表現又は実務母集団の妥当性が成立した。
- CI成功、merge又はdigest一致が外部真正性、運用資格、保安認証又は人間受理を意味する。

## 受理境界

本記録は観測証拠であり、受理記録ではない。最終受理の主体は `external_human` のまま残し、機械監査、GitHub merge又はCIが `acceptance_status=pending` を変更してはならない。
