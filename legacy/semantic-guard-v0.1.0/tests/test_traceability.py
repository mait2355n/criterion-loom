from __future__ import annotations

import unittest

from semantic_guard.traceability import build_trace_report


class TraceabilityTests(unittest.TestCase):
    def test_trace_report_links_request_plan_diff_and_finish(self) -> None:
        report = build_trace_report(
            {
                "request": "利用者: 保守者。目的: evaluate-fixtures が JSON summary を返す。"
                "対象外: fixture 内容の変更。利用場面: 保守者が CLI で回帰評価を実行する。"
                "前提: tests/fixtures が存在する。入力項目: --include-passed。出力項目: total, passed, failed, metrics。"
                "品質: pass_rate は小数第三位まで。受入条件: unittest と CLI 実行で JSON summary を確認する。"
                "不合格条件: JSON が壊れる、または failed 件数が実際と異なる。未確定: なし。",
                "plan": "目的: evaluate-fixtures JSON summary を実装する。対象外: fixture 内容の変更。"
                "成果物: cli.py と評価試験。作業分解: 出力集計、CLI 表示、試験追加。"
                "依存順序: 集計を先に直し、次に CLI、最後に試験。担当: Codex。"
                "リスク: 既存出力互換が壊れる。対応: 既存キーを維持する。検証: unittest と CLI。"
                "妥当性: 保守者が JSON summary を読めること。判断主体: 保守者。"
                "確認点: 試験通過後。戻し方: 変更ファイルを退避前状態へ戻す。証拠: コマンド結果。未確定: なし。",
                "diff": "diff --git a/src/semantic_guard/cli.py b/src/semantic_guard/cli.py\n+ evaluate-fixtures JSON summary",
                "finish": "完了要約: evaluate-fixtures JSON summary を追加した。完了条件: CLI が JSON summary を返す。"
                "公開挙動: semantic-guard evaluate-fixtures が total と metrics を返す。残リスク: なし。",
                "evidence": "受入証拠: uv run semantic-guard evaluate-fixtures を実行し JSON summary を確認。代表 CLI 実行済み。",
            }
        )

        self.assertEqual(report["phase"], "trace_report")
        self.assertIn(report["status"], {"pass", "warn"})
        self.assertGreaterEqual(report["summary"]["link_count"], 3)
        self.assertIn("request", report["audits"])
        self.assertIn("finish", report["audits"])

    def test_trace_report_splits_embedded_audit_status_from_trace_status(self) -> None:
        report = build_trace_report(
            {
                "request": "利用者: 保守者。目的: JSON summary を返す。"
                "受入条件: JSON summary を確認。検証方法: 動作確認。証拠: 試験結果。"
                "対象外: UI。未確定: なし。",
                "plan": "目的: JSON summary を返す監査を実装する。対象外: UI。成果物: core.py と tests。"
                "作業分解: core.py と tests を作業パッケージに分ける。手順: 調査、実装、検証。"
                "順序: 調査後に実装し検証する。依存: 既存 CLI。資源: Codex。"
                "リスク: JSON summary が壊れる。対策: unittest。検証: unittest。"
                "妥当性: 利用者が JSON summary を確認する。判断主体: 利用者。確認点: 実装後。"
                "基準線: 既存試験。変更統制: 追加要求は後続化する。決定点: 利用者が受入判断。"
                "戻し方: 差分を戻す。証拠: コマンド結果。未確定: なし。",
                "finish": "完了要約: JSON summary を返す監査を実装した。"
                "完了条件: JSON summary を確認。公開挙動: command が JSON output を返す。残リスク: なし。",
                "evidence": "受入証拠: uv run semantic-guard audit-request を実行し JSON summary を確認。代表 CLI 実行済み。",
            }
        )

        self.assertEqual(report["status"], "warn")
        self.assertEqual(report["summary"]["audit_status"], "warn")
        self.assertEqual(report["summary"]["trace_status"], "pass")
        self.assertEqual(report["summary"]["aggregate_status_reason"], "embedded audit returned warn")

    def test_trace_report_flags_missing_finish_segment(self) -> None:
        report = build_trace_report(
            {
                "request": "利用者: 保守者。目的: 設定を公開する。対象外: UI。"
                "利用場面: 保守者が公開前に config を確認する。前提: 設定ファイルが存在する。"
                "入力項目: config。出力項目: 公開済み設定。品質: 既存キーを削除しない。"
                "受入条件: unittest と公開前確認で設定が読める。"
                "不合格条件: 既存キーが消える、または読み込みに失敗する。未確定: なし。",
                "plan": "目的: 設定を公開する。対象外: UI。成果物: config。手順: 調査、実装、検証。"
                "依存: config。リスク: 運用が壊れる。検証: unittest。妥当性: 利用者が判断する。"
                "判断主体: 利用者。確認点: 実装後。戻し方: backup。証拠: コマンド結果。未確定: なし。",
            }
        )

        gap_kinds = {gap["kind"] for gap in report["gaps"]}
        self.assertIn("missing_segment", gap_kinds)
        self.assertEqual(report["status"], "warn")

    def test_trace_report_normalizes_trace_tags_across_vocabulary_gap(self) -> None:
        report = build_trace_report(
            {
                "request": "利用者: 保守者。目的: 追跡を確認する。対象外: UI。"
                "入力項目: 監査対象。出力項目: 件数と指標。"
                "受入条件: 結果概要が読める。検証方法: 実行で確認する。未確定: なし。",
                "finish": "Done when the summary is readable. Verification: command run. "
                "Output fields: counts and metrics. Evidence: execution result captured. Residual risk: none.",
            }
        )

        request_finish = next(
            link for link in report["links"] if link["from"] == "request" and link["to"] == "finish"
        )
        self.assertEqual(request_finish["raw_strength"], "weak")
        self.assertIn("acceptance", request_finish["shared_tags"])
        self.assertIn("output_contract", request_finish["shared_tags"])
        self.assertIn("verification", request_finish["shared_tags"])
        self.assertEqual(request_finish["strength"], "medium")
        self.assertEqual(request_finish["match_status"], "partial")
        self.assertEqual(request_finish["confidence"], "medium")
        self.assertIn("trace_vocabulary_gap", request_finish["ambiguity_reasons"])
        self.assertEqual(report["summary"]["ambiguity_reason_counts"]["trace_vocabulary_gap"], 1)
        self.assertNotIn(
            ("weak_trace", "request", "finish"),
            {(gap["kind"], gap.get("from"), gap.get("to")) for gap in report["gaps"]},
        )

    def test_trace_report_accepts_payload_tags_as_event_like_trace_tags(self) -> None:
        report = build_trace_report(
            {
                "request": "利用者: 保守者。目的: 監査の対応関係を確認する。対象外: UI。"
                "受入条件: 実行結果を確認する。未確定: なし。",
                "finish": "Completion note: reviewer saw the result. Residual risk: none.",
                "tags": {
                    "request": ["traceability", "acceptance"],
                    "finish": [{"tag": "traceability", "source": "manual review tag"}],
                },
            }
        )

        request_tags = {entry["tag"] for entry in report["trace_tags"]["request"]}
        finish_tags = {entry["tag"] for entry in report["trace_tags"]["finish"]}
        self.assertIn("traceability", request_tags)
        self.assertIn("traceability", finish_tags)
        request_finish = next(
            link for link in report["links"] if link["from"] == "request" and link["to"] == "finish"
        )
        self.assertIn("traceability", request_finish["shared_tags"])

    def test_trace_report_suggests_domain_terms_without_auto_accepting_them(self) -> None:
        report = build_trace_report(
            {
                "request": "利用者: 保守者。目的: ビード と ストランド の追跡を確認する。"
                "受入条件: 対応関係が読める。未確定: なし。",
                "finish": "完了要約: ビード の表示確認を記録した。残リスク: なし。",
            }
        )

        unresolved_terms = {(entry["term"], entry["segment"]) for entry in report["unresolved_terms"]}
        self.assertIn(("ビード", "request"), unresolved_terms)
        self.assertIn(("ストランド", "request"), unresolved_terms)
        suggested_tags = {entry["tag"] for entry in report["suggested_tags"]}
        self.assertIn("rs.bead", suggested_tags)
        self.assertIn("rs.strand", suggested_tags)
        trace_tags = {
            tag["tag"]
            for entries in report["trace_tags"].values()
            for tag in entries
        }
        self.assertNotIn("rs.bead", trace_tags)
        self.assertNotIn("rs.strand", trace_tags)
        self.assertGreaterEqual(report["summary"]["unresolved_term_count"], 2)

    def test_trace_report_uses_only_accepted_vocabulary_profile_terms_as_trace_tags(self) -> None:
        report = build_trace_report(
            {
                "request": "利用者: 保守者。目的: ビード と ストランド と 主観時間 を追跡する。"
                "受入条件: 対応関係が読める。未確定: なし。",
                "finish": "完了要約: ビード と ストランド と 主観時間 の確認を記録した。残リスク: なし。",
                "vocabulary_profile": {
                    "accepted": {"ビード": "rs.bead"},
                    "rejected": ["ストランド"],
                    "deferred": ["主観時間"],
                },
            }
        )

        request_tags = {entry["tag"] for entry in report["trace_tags"]["request"]}
        finish_tags = {entry["tag"] for entry in report["trace_tags"]["finish"]}
        self.assertIn("rs.bead", request_tags)
        self.assertIn("rs.bead", finish_tags)
        self.assertNotIn("rs.strand", request_tags | finish_tags)
        self.assertNotIn("rs.subjective_time", request_tags | finish_tags)

        status_by_term = {
            (entry["term"], entry["segment"]): entry["status"]
            for entry in report["vocabulary_decisions"]["decisions"]
        }
        self.assertEqual(status_by_term[("ビード", "request")], "accepted")
        self.assertEqual(status_by_term[("ストランド", "request")], "rejected")
        self.assertEqual(status_by_term[("主観時間", "request")], "deferred")
        request_finish = next(
            link for link in report["links"] if link["from"] == "request" and link["to"] == "finish"
        )
        self.assertIn("rs.bead", request_finish["shared_tags"])


if __name__ == "__main__":
    unittest.main()
