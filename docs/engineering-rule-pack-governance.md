# 工学規則集の統治

## 結論

`engineering-rule-pack.candidate.json` は、`functional-requirement-record/v1` の11義務と現行11直接規則について、工学的な命題候補、解釈、適用条件、適用しない条件（反適用条件）、必要証拠、限界、一次資料の位置、採択状態を外から検査できる形にした候補台帳である。

これは工学適合証明ではなく、人間採択済み規則集でもない。現状は全件 `candidate_pending_human_adoption`、`runtime_authority=none` であり、監査の通過・失敗判定を正当化する実行時権限を持たない。

## 保存する境界

- `semantic-guard` は、候補規則と証拠の不足・矛盾・適用不能を監査材料として示す。
- 規則の採択、組織向け調整、例外受理、最終受理は人間が行う。
- 一次資料の文章と、`semantic-guard` が行った解釈を別の項目に保存する。
- 規格名を付しただけで工学的正しさを推定しない。
- 候補台帳の存在を、規格適合、実務での妥当性確認、独立査読、又は実行時権限と呼ばない。

## 現在の一次資料状態

| 元資料 | 現在の用途 | 取得・版状態 | 現在の権限 |
|---|---|---|---|
| [ISO/IEC/IEEE 29148:2018](https://www.iso.org/standard/72089.html) | 要求工学過程・情報項目という上位文脈 | 第2版。2024年確認済みだが、2026-02-16から改訂予定（90.92）で後継DISあり。公開要旨と製品情報のみ確認し、許諾された条文本文は未取得・ハッシュ値未記録 | なし |
| [NASA 4.2 Technical Requirements Definition](https://www.nasa.gov/reference/4-2-technical-requirements-definition/) | システム境界、機能・振舞、入出力、性能という候補根拠 | NASA公式ウェブページの見出しを2026-07-16に確認。ページが基づくハンドブックの版をページ単独から断定せず、固定した時点記録も未取得 | なし |
| [NASA Appendix C](https://www.nasa.gov/reference/appendix-c-how-to-write-a-good-requirement/) | 主体・能動動作・明瞭性・完全性・性能・検証可能性の候補根拠 | NASA公式ウェブページの見出しを確認。固定した時点記録と版のハッシュ値は未取得 | なし |
| [NASA Appendix D](https://www.nasa.gov/reference/appendix-d-requirements-verification-matrix/) | 要求識別子と検証方法の追跡候補 | NASA公式ウェブページの導入部と表位置を確認。表を転記せず、固定した時点記録も未取得 | なし |
| [EARS primary DOI](https://doi.org/10.1109/RE.2009.9) / [Manchester record](https://research.manchester.ac.uk/en/publications/easy-approach-to-requirements-syntax-ears/) | 構造化自然言語という概念候補 | 書誌情報と公開要旨のみ確認。論文本文と厳密な様式定義は未取得で、ハッシュ値も未記録 | なし |

著作権のある本文を台帳へ複製していない。各対応付けは短い節位置と独自の要約だけを保持する。特にISOは公開要旨を条文の代用にしない。

## 11義務の候補対応

| プロファイル上の義務 | 候補工学規則 | 局所直接規則 | 主な候補根拠 |
|---|---|---|---|
| `func.applies_to` | `engineering.functional.applies-to@v0` | `direct.dimension.applies-to/v2` | NASA 4.2.1.2.1 |
| `func.performs` | `engineering.functional.performs@v0` | `direct.structured.actor-scenario/v2` | NASA Appendix C, C.2 |
| `func.acts_on` | `engineering.functional.acts-on@v0` | `direct.structured.object-marker/v0` | NASA Appendix C, C.2 |
| `func.triggered_by` | `engineering.functional.triggered-by@v0` | `direct.structured.condition-marker/v0` | NASA 4.2.1.2.1、EARS公開要旨 |
| `func.produces` | `engineering.functional.produces@v0` | `direct.structured.scenario-result-alignment/v2` | NASA 4.2 overview |
| `func.constrained_by` | `engineering.functional.constrained-by@v0` | `direct.structured.result-criterion-alignment/v1` | NASA Appendix C, C.4 Verifiability/Testability |
| `func.uses_metric` | `engineering.functional.uses-metric@v0` | `direct.structured.metric-marker/v0` | NASA Appendix C, C.4 Performance |
| `func.verified_by` | `engineering.functional.verified-by@v0` | `direct.dimension.verified-by/v2` | NASA Appendix D、ISO公開要旨は上位文脈のみ |
| `func.verifies` | `engineering.functional.verifies@v0` | `direct.structured.verification-target-alignment/v1` | NASA Appendix C/D |
| `func.measures` | `engineering.functional.measures@v0` | `direct.structured.metric-target-alignment/v1` | NASA Appendix C, C.4 Performance / Verifiability |
| `func.produces_evidence` | `engineering.functional.produces-evidence@v0` | `direct.structured.method-evidence-alignment/v1` | NASA Appendix D、ISO公開要旨は上位文脈のみ |

この対応は一対一の追跡を保つための候補である。NASA又はISOが、これら11の関係をそのまま要求しているという意味ではない。例えば `produces_evidence` は、外部資料における検証計画の追跡を踏まえつつ`semantic-guard`が監査再現用に追加した局所解釈であり、その差を `interpretation` と `limitations` に明記している。

## 採択条件

候補を `adopted` 又は `runtime_authority!=none` にするには、少なくとも次を全て満たす必要がある。

1. 参照する正確な資料版を適法に取得し、内容範囲を明記したSHA-256ハッシュ値を保存する。
2. 公開要旨ではなく、採用する節又は概念へ対応付けを更新する。
3. 要求工学又は対象領域の独立査読者が、命題、解釈、適用条件、反適用条件、必要証拠、限界を査読する。
4. 査読証拠、査読権限、人間の採択記録、採択権限を記録する。
5. 肯定例だけでなく、反適用例、境界例、反証例、言語別例、実務母集団で検証する。
6. 採択版の規則集と実行時実装を内容のハッシュ値で結合し、版差替え時に再検証する。

一項でも欠けるなら `runtime_authority=none` のままにする。`semantic-guard`自身が自己採択してはならない。

## 情報不足なら拒否する検証

検証器はJSON Schema検証に加え、現在の `profiles.py` と `direct_rules.py` を構文木から読んで次を検査する。

- 11個のプロファイル義務の欠落、余分、重複
- 11個の局所直接規則IDの欠落、余分、重複
- 元資料、節、義務、局所規則にある、参照先の存在しない参照
- 安定規則IDと版の重複
- `interpretation`、`applicability`、`counterconditions`、`required_evidence`、`limitations`、`review_triggers` の欠落
- 原文取得状態とハッシュ値状態の矛盾
- 独立査読・人間採択証拠のない偽 `adopted`
- 未採択規則又は規則集への実行時権限付与
- 改訂予定ISOを参照する元資料又は規則の置換時に必要な再査読条件の欠落
- 部分候補台帳による規格適合主張

実行:

```sh
uv run --locked python scripts/validate_engineering_rule_pack.py
uv run --locked python -m unittest tests.test_engineering_rule_pack -v
```

期待する現在値は、元資料（`sources`）5件、規則（`rules`）11件、プロファイル義務（`profile_obligations`）11件、局所直接規則（`local_direct_rules`）11件、対応付けた元資料参照（`mapped_source_refs`）16件である。これは台帳の内部整合であって、規則の工学的妥当性ではない。

## 再査読条件

- ISO/IEC/IEEE DIS 29148又は後継版の公表・置換
- NASA公式ページ又は基礎となるハンドブックの版の変更
- EARS本文取得、後続版、又は正誤表採用
- プロファイル義務、直接規則ID、対応言語、解析器、辞書、LLM、昇格方針の変更
- 工学命題、解釈、適用条件、反適用条件、必要証拠、限界の変更
- 組織向け調整、例外、又は採択状態の変更

変更時は既存版を書き換えて権限を継承せず、新版、新旧版の対応表、再検証、独立査読、人間判断を必要とする。

## 残危険

- 一次資料本文が未取得なので、節単位の正確な対応と文脈保持は未証明である。
- 現在の資料群は要求記述と検証計画へ偏り、計画工学、ソフトウェア設計、実装差分、実行証拠、完了承認には別の規則集が要る。
- 11義務で十分かどうかはまだ妥当性を確認しておらず、要求種別、領域、言語ごとの追加・削除があり得る。
- 局所正規表現の内部整合と、自然言語上の正しい係り受けは別問題である。
- 独立査読、人間採択、実務母集団評価が未実施である以上、現状を実務受入可能と評価してはならない。
