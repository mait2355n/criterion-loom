# semantic-guard 1.0.0 局所運用既定切替記録

記録日時: 2026-07-21T01:55:07+09:00

判断識別子: `operational-default-cutover.semantic-guard.v1.0.0.local-codex`

判断所有者: repository 所有者兼 Codex 局所運用者

判断出典: 2026-07-21 の Codex 対話における「では全面切り替えまで宜しくたのむ」という明示指示。対話外の署名、本人性、信頼時刻及び外部権限台帳は未検証である。

## 判断

この repository を含む Codex 局所作業領域では、対応済みの要求関係監査について `semantic-guard 1.0.0` を唯一の既定実行系とする。

- MCP は正本 checkout の `.venv/bin/semantic-guard-mcp` を使う。
- companion skill は正本 v1 と一致する一件だけを探索対象に置く。
- 旧 `0.1.0` は暗黙の代替経路にしない。明示的な互換確認又は回復のための凍結資料としてだけ保持する。
- `pass`、終了符号 `0` 又は局所試験成功を、人間受理、実地妥当性、保安認証又は全工程対応へ読み替えない。

この判断は撤回可能な局所既定値切替である。凍結旧版の不可逆削除、外部配備の停止、`predecessor_retired` 段階、候補工学規則群若しくは生活周期 profile の採択を許可しない。それらには対象と不可逆性を明示した別判断及び各移行門の実証が要る。

## 要求監査

対象要求は [`../migration/operational-default-cutover-requirement-2026-07-21.txt`](../migration/operational-default-cutover-requirement-2026-07-21.txt) とする。

- 入力 SHA-256: `c2df4cebb755c104aaa28bdbc0ada2608fd1ecc68fdd406ac999bf319ad74402`
- schema: `semantic-guard-audit-result/v0`
- 解析方式: `assurance`
- 記録時刻: `2026-07-21T01:55:07+09:00`
- 公開 JSON SHA-256: `8758dea930b57ebbb7fc78eb0ca17387f962eced3513b0a03273f4bd171881cc`
- workflow disposition: `warn`
- 未解決義務: `func.applies_to`, `func.performs`, `func.produces`, `func.constrained_by`, `func.verified_by`, `func.verifies`, `func.produces_evidence`
- 解析器: morphology `unavailable/signal_only`、dependency `unavailable/candidate_only`、LLM `unavailable/candidate_only`

`warn` は複合命題及び未構成解析器を残した結果であり、局所切替の外部人間判断を代替しない。逆に、この判断も未観測の意味関係を監査上の充足へ改竄しない。

## 切替観測

- 切替前正本 commit: `dd331e609c6809e3e610a7cd5987e2bab997e562`
- live skill SHA-256: `ac30c4240dc848f4dda1b395c24c290c70f9e1a415da87ab9526b6587212674f`
- CLI launcher SHA-256: `2ac447d4bad1034fb2b7bbf5c375320bf9bb8a0e2ccf432b2cc219bc2b7550de`
- MCP launcher SHA-256: `999be6b24e9da8e0b02d71b595cc4284e630b48fb4e16f83d872912687f8e98b`
- CLI 観測版: `semantic-guard 1.0.0`
- MCP 設定先: `<repository-root>/.venv/bin/semantic-guard-mcp`
- 探索可能な同名技能: v1 の一件
- 旧技能退避先: Codex 技能探索外の局所証拠保管庫。公開 repository には含めない。

## 切替後検証

- `uv lock --check`: 成功、81 package を解決。
- `python -m unittest discover -s tests -q`: 575件成功、失敗なし。
- `validate_verification_source.py`: 六検査成功、17未解決群と65 gapを維持。
- `render_verification_projection.py --check`: 完全一致。
- `validate_engineering_rule_pack.py`: schema、mapping、governance の三検査成功。候補状態は変更していない。
- wheel: `semantic_guard-1.0.0-py3-none-any.whl`, SHA-256 `9e1eb2c546610fd828e345724e740f3a98dab5362e02d5f837918812242c6210`, 324347 bytes。
- sdist: `semantic_guard-1.0.0.tar.gz`, SHA-256 `bebb14e96d0d7ef3d5bafc3743812d2d82a25d245f19e019090b2c9061bb6af1`, 284271 bytes。
- 隔離配布物検査: 成功。公開schema 23件、MCP schema資源23件、MCP tool 3件、生活周期profile 10件、工学候補規則11件、導入CLI版及びMCP console入口を確認。

配布物検査は依存取得のため外部package索引を使った。成功は包内資源と局所契約の再演を示すだけで、外部package索引、実運用又は保安の資格を与えない。

## 成立範囲

成立するのは、当該 Codex 局所環境における対応済み要求関係監査の既定経路切替と、旧版の暗黙選択排除である。

次は未成立のまま残す。

- 実務母集団による欄妥当性と重大誤満足率
- 十二の実運用場面を満たす運用資格
- 独立した保安評価、実利用者評価及び外部真正性
- 十工程 profile と工学規則群の人間採択及び公開縦断統合
- 外部配備の全面切替
- 凍結旧版の不可逆廃止

従って本記録は `transition-plan/v0` が要求する `default` 又は `predecessor_retired` の全門達成記録ではなく、より狭い局所構成判断及び実行観測である。
