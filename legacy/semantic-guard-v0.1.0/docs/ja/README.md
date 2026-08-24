# 日本語文書地図

> **歴史境界（0.1.0 公開用修復済み archive）。** この文書は 0.1.0 系の記録時点に
> おける predecessor を説明するもので、現行 1.x の状態・運用手順ではない。原 byte
> の権威は tag `v0.1.0` / commit `e0a3dd39f17385b66f6361ade25eb44bed6e1ab3` にある。

この directory は、Criterion Loom の 0.1.0 記録、実演 command、公開成果物の証拠境界を日本語で読むための入口である。

技術名としての package / CLI / MCP server は `semantic-guard` のまま扱う。

## 対象読者と用途

対象読者は、Criterion Loom を初めて見る技術読者と保守者である。この文書は、詳細設計を読む前に「どの日本語文書を読めばよいか」を判断するために使う。

## 読む順番

初見の読者は次の順で参照する。

1. `../../README.ja.md`
2. `naming.md`
3. `company-evidence.md`
4. `quickstart.md`
5. `../calibration-report-2026-06-05.md`
6. `../public-comparison-2026-06-02.ja.md`

## 各文書の役割

- `../../README.ja.md`: 日本語の総合取説。目的、非目標、基本 command、出力の読み方。
- `naming.md`: Criterion Loom、Loom Guide、Need Thread、Plan Warp、Change Weft と技術名の対応。
- `quickstart.md`: clone 後または snapshot root での動かし方。
- `company-evidence.md`: archive で観測できる成果物・機構と、この記録からは主張できない範囲を分ける。
- `../calibration-report-2026-06-05.md`: 2026-06-05 時点の fixture 評価 snapshot。
- `../public-comparison-2026-06-02.ja.md`: MCP server、security scanner、agent skill などとの比較。

## 実行例

公開 snapshot の root から、次の command で日本語入口文書を監査できる。

```sh
uv run --python 3.13 --project . semantic-guard audit-request --kind document --file README.ja.md
uv run --python 3.13 --project . semantic-guard llm-explore-request --text "割り勘アプリを作りたい" --dry-run
```

fixture 評価は次で確認する。

```sh
uv run --python 3.13 --project . semantic-guard evaluate-fixtures
uv run --python 3.13 --project . semantic-guard doctor
```

## 出力項目

文書監査の主要な返却項目は、`status`、`score`、`findings`、`missing`、`next_actions`、`details` である。

- `status`: 現在の規則で止めるかどうか。
- `findings`: 不足や警告の内容。
- `missing`: 文書から見えなかった構造項目。
- `next_actions`: 次に直すべきこと。
- `details`: claim/evidence/limitation や診断情報。

## 注意

この資料群は営業資料ではない。過大な断定を避け、実行可能な成果、検証済みの範囲、未検証の範囲を分けて読ませるための取説である。
