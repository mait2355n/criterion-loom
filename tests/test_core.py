import unittest

from semantic_guard.core import (
    apply_logical_trace_mode,
    audit_decision_state,
    audit_diff,
    audit_plan,
    audit_request,
    finish_check,
    understand_target,
)
from semantic_guard.exploration import explore_request


class CoreAuditTests(unittest.TestCase):
    def test_explore_request_surfaces_material_ambiguities_before_spec(self) -> None:
        result = explore_request("割り勘アプリを作りたい", strict=True)

        self.assertEqual(result["phase"], "explore_request")
        self.assertEqual(result["status"], "warn")
        self.assertIn("target_audience", result["missing"])
        self.assertIn("data_or_state_model", result["missing"])
        self.assertIn("identity_privacy_or_authority", result["missing"])
        self.assertGreaterEqual(len(result["details"]["audience_hypotheses"]), 3)
        self.assertTrue(any(question["id"] == "target_audience" for question in result["details"]["questions"]))
        self.assertIn("does not start implementation", result["details"]["non_decisions"])

    def test_explore_request_passes_when_material_boundaries_are_visible(self) -> None:
        result = explore_request(
            "対象利用者: リンクから参加する支払参加者。問題: 食事後の精算が遅い。"
            "導線: 幹事が会計を入力し、参加者がリンクで確認し、精算完了を記録する。"
            "資料模型: 会計、参加者、支払状態を保存し、カード番号は保存しない。"
            "秘匿: リンクを知る参加者だけが閲覧でき、幹事だけが編集できる。"
            "受入基準: 3人分の精算額が表示される。検証: CLI smoke。証拠: コマンド結果。"
            "対象外: 実決済。未確定: 通知方式は判断待ち。",
            strict=True,
        )

        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["missing"], [])
        self.assertEqual(result["details"]["questions"], [])

    def test_understand_target_blocks_missing_core_fields(self) -> None:
        result = understand_target("検索機能を作る", strict=True)
        self.assertEqual(result["status"], "block")
        self.assertIn("non_goals", result["missing"])

    def test_audit_request_flags_unverifiable_request(self) -> None:
        result = audit_request("画面をいい感じに速くする", strict=True)
        categories = {finding["category"] for finding in result["findings"]}
        self.assertIn("clarity", categories)
        self.assertIn("verifiability", categories)
        target = next(finding for finding in result["findings"] if finding.get("rule_id") == "req.verifiability.acceptance_missing")
        self.assertEqual(target["derivation"]["status"], "derived")
        self.assertEqual(result["details"]["logical_trace"]["rules_evaluated"][0]["status"], "derived")
        self.assertEqual(result["details"]["diagnostics"]["logical_trace"]["rule_count"], 7)

    def test_audit_decision_state_surfaces_unresolved_items_for_management_handoff(self) -> None:
        result = audit_decision_state(
            "未決定: サブエージェント分割規則。owner: 人間。needed_for: goal design。"
            "blocking: true。next_action: 判断基準を書く。review_at: 2026-06-13T09:00:00+09:00。"
            "仮説: 並列化が有効。価値判断: 速度より意味保存を優先。証拠なし: 工学的根拠は未検証。",
            strict=True,
        )

        self.assertEqual(result["phase"], "audit_decision_state")
        self.assertEqual(result["status"], "warn")
        self.assertIn("unresolved_decision_management", result["missing"])
        self.assertEqual(result["details"]["schema_version"], "decision-state-audit/v1")
        report = result["details"]["decision_state_report"]
        self.assertTrue(result["details"]["decision_authority"]["does_not_decide"])
        self.assertGreaterEqual(report["unresolved_item_count"], 4)
        kinds = {item["kind"] for item in report["management_handoff_items"]}
        self.assertIn("unresolved_decision", kinds)
        self.assertIn("hypothesis", kinds)
        self.assertIn("value_judgment", kinds)
        self.assertIn("evidence_gap", kinds)
        first_item = report["management_handoff_items"][0]
        self.assertEqual(first_item["suggested_owner"], "人間")
        self.assertEqual(first_item["needed_for"], ["goal design"])
        self.assertEqual(first_item["blocking_status"], "blocking")
        self.assertEqual(first_item["review_at"], "2026-06-13T09:00:00+09:00")

    def test_audit_decision_state_accepts_explicit_no_unresolved_state(self) -> None:
        result = audit_decision_state(
            "決定状態: decided。未決: なし。仮説: なし。根拠: pytest result。owner: 人間。",
            strict=True,
        )

        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["missing"], [])
        self.assertEqual(result["details"]["decision_state_report"]["unresolved_item_count"], 0)

    def test_findings_include_rule_id_and_structured_repair_when_rule_matches(self) -> None:
        result = audit_request("画面をいい感じにする", strict=True)
        finding = next(finding for finding in result["findings"] if finding.get("rule_id") == "req.verifiability.acceptance_missing")
        self.assertEqual(finding["repair"]["source"], "rule_catalog")
        self.assertEqual(finding["repair"]["rule_id"], "req.verifiability.acceptance_missing")
        self.assertIn("minimal_example", finding["repair"])

    def test_audit_request_flags_weak_achievement_detail(self) -> None:
        result = audit_request(
            "利用者: 保守者。目的: 検索機能を改善する。検証: 動作確認する。対象外: UI刷新。未確定: なし。",
            strict=True,
        )
        categories = {finding["category"] for finding in result["findings"]}
        self.assertIn("acceptance", categories)
        self.assertIn("verification", categories)
        self.assertIn("evidence", categories)
        self.assertIn("achievement_criteria", result["missing"])
        self.assertIn("verification_method_detail", result["missing"])
        self.assertIn("evidence_artifact", result["missing"])
        verification_finding = next(finding for finding in result["findings"] if finding["category"] == "verification")
        self.assertEqual(verification_finding["rule_id"], "req.verification.method_detail_missing")
        self.assertEqual(verification_finding["derivation"]["status"], "derived")
        acceptance_finding = next(finding for finding in result["findings"] if finding.get("rule_id") == "req.achievement.criteria_missing")
        evidence_finding = next(finding for finding in result["findings"] if finding.get("rule_id") == "req.evidence.artifact_missing")
        scenario_finding = next(finding for finding in result["findings"] if finding.get("rule_id") == "req.context.scenario_missing")
        self.assertEqual(acceptance_finding["derivation"]["status"], "derived")
        self.assertEqual(evidence_finding["derivation"]["status"], "derived")
        self.assertEqual(scenario_finding["derivation"]["status"], "derived")

    def test_audit_request_flags_vague_behavior_structure(self) -> None:
        result = audit_request(
            "利用者: 保守者。目的: レポート機能を改善する。"
            "受入基準: 改善されたことを確認。検証方法: レビュー。証拠: レビュー記録。"
            "対象外: UI刷新。未確定: なし。",
            strict=True,
        )
        categories = {finding["category"] for finding in result["findings"]}
        self.assertIn("behavior", categories)
        self.assertIn("observable_behavior", result["missing"])
        self.assertIn("observable_behavior", result["details"]["requirement_signals"])

    def test_audit_request_flags_missing_trigger_and_expected_result(self) -> None:
        result = audit_request(
            "利用者: オペレータ。目的: 画面で検索できる。"
            "受入基準: 検索できることを確認。検証方法: pytest。証拠: 試験結果。"
            "対象外: UI刷新。未確定: なし。",
            strict=True,
        )
        self.assertIn("precondition_or_trigger", result["missing"])
        self.assertIn("expected_result", result["missing"])

    def test_audit_request_flags_interface_contract_missing(self) -> None:
        result = audit_request(
            "利用者: 連携先。目的: API が JSON を返す。"
            "シナリオ: 連携先が API を呼ぶ場合、JSON が返る。"
            "受入基準: JSON が返ることを確認。検証方法: pytest。証拠: 試験結果。"
            "対象外: 認証。未確定: なし。",
            strict=True,
        )
        categories = {finding["category"] for finding in result["findings"]}
        self.assertIn("interface", categories)
        self.assertIn("interface_contract", result["missing"])

    def test_audit_request_accepts_interface_contract_detail(self) -> None:
        result = audit_request(
            "利用者: 連携先。目的: API が JSON を返す。"
            "シナリオ: 連携先が API を呼ぶ場合、status と findings を含む JSON が返る。"
            "入力条件: GET /audit に request_id を渡す。"
            "受入基準: HTTP 200 と status, findings 項目を返す。"
            "検証方法: pytest。証拠: 試験結果。"
            "不合格条件: status が無い場合は差し戻し。対象外: 認証。未確定: なし。",
            strict=True,
        )
        categories = {finding["category"] for finding in result["findings"]}
        self.assertNotIn("interface", categories)
        self.assertNotIn("precondition_or_trigger", result["missing"])
        self.assertNotIn("expected_result", result["missing"])

    def test_audit_request_accepts_detailed_achievement_profile(self) -> None:
        result = audit_request(
            "利用者: 運用者。目的: 検索を速くする。"
            "シナリオ: 運用者が検索語を入力した場合、結果一覧が返る。"
            "受入基準: p95 500ms 以下。検証方法: ベンチマーク測定。"
            "証拠: コマンド結果を保存する。不合格条件: p95 が 500ms を超えたら差し戻し。"
            "対象外: UI刷新。未確定: なし。",
            strict=True,
        )
        categories = {finding["category"] for finding in result["findings"]}
        self.assertEqual(result["status"], "pass")
        self.assertNotIn("acceptance", categories)
        self.assertNotIn("verification", categories)
        self.assertNotIn("evidence", categories)
        self.assertNotIn("scenario", categories)
        self.assertEqual(result["details"]["logical_trace"]["rules_evaluated"][0]["status"], "satisfied")
        self.assertEqual(result["score"], 1.0)

    def test_apply_logical_trace_mode_filters_full_trace_without_changing_status(self) -> None:
        result = audit_request("目的: 速度改善をしたい。", strict=True)

        summary = apply_logical_trace_mode(result, "summary")
        full = apply_logical_trace_mode(result, "full")
        none = apply_logical_trace_mode(result, "none")

        self.assertEqual(summary["status"], result["status"])
        self.assertNotIn("logical_trace", summary["details"])
        self.assertIn("logical_trace_summary", summary["details"])
        self.assertIn("logical_trace", full["details"])
        self.assertNotIn("logical_trace", none["details"])
        self.assertNotIn("logical_trace_summary", none["details"])
        self.assertNotIn("logical_trace", none["details"]["diagnostics"])

    def test_audit_request_records_satisfied_scope_non_emission(self) -> None:
        result = audit_request(
            "利用者: 運用者。目的: 検索を速くする。"
            "シナリオ: 運用者が検索語を入力した場合、結果一覧が返る。"
            "受入基準: p95 500ms 以下。検証方法: ベンチマーク測定。"
            "証拠: コマンド結果を保存する。不合格条件: p95 が 500ms を超えたら差し戻し。"
            "対象外: UI刷新。未確定: なし。",
            strict=True,
        )
        rule_ids = {finding.get("rule_id") for finding in result["findings"]}
        suppressed = result["details"]["suppressed_rules"]
        trace = next(item for item in suppressed if item["rule_id"] == "req.scope.non_goals_missing")
        self.assertEqual(result["status"], "pass")
        self.assertNotIn("req.scope.non_goals_missing", rule_ids)
        self.assertEqual(trace["emission_status"], "satisfied")
        self.assertEqual(trace["match_status"], "matched")
        self.assertEqual(trace["reason"], "explicit_scope_boundary_satisfies_rule")
        self.assertIn("対象外", trace["evidence"])
        self.assertEqual(result["details"]["suppressed_rule_counts"]["req.scope.non_goals_missing"], 1)
        non_emitted = result["details"]["non_emitted_rules"]
        self.assertEqual(non_emitted[0]["emission_status"], "satisfied")
        self.assertEqual(
            result["details"]["non_emitted_rule_counts"]["by_emission_status"]["satisfied"],
            1,
        )

    def test_audit_request_flags_missing_rejection_condition_for_sensitive_requirement(self) -> None:
        result = audit_request(
            "利用者: 管理者。目的: 権限設定を安全にする。"
            "受入基準: 管理者以外は設定変更できないことを確認。"
            "検証方法: pytest。証拠: 試験結果。対象外: UI。未確定: なし。",
            strict=True,
        )
        self.assertIn("rejection_condition", result["missing"])

    def test_audit_request_flags_problem_mechanism_fit_gap(self) -> None:
        result = audit_request(
            "利用者: 保守者。問題: import が失敗する。"
            "解決策: エラーを握り潰す。目的: import を止めずに通す。"
            "受入基準: エラーが出ない。検証方法: pytest。証拠: 試験結果。"
            "対象外: UI。未確定: なし。",
            strict=True,
        )
        rule_ids = {finding.get("rule_id") for finding in result["findings"]}
        self.assertIn("problem_mechanism_fit", result["missing"])
        self.assertIn("symptom_only_success_criteria", result["missing"])
        self.assertIn("req.solution.problem_mechanism_fit_missing", rule_ids)
        self.assertIn("req.acceptance.symptom_only_success_criteria", rule_ids)

    def test_audit_request_accepts_problem_solution_with_mechanism_evidence(self) -> None:
        result = audit_request(
            "利用者: 保守者。問題: 旧 JSON の import が失敗する。"
            "原因: required field の欠落を新 schema として扱っている。"
            "解決策: 欠落 field に migration default を補う。"
            "受入基準: 旧 JSON が migration され、欠落 field は default として記録される。"
            "検証方法: pytest。証拠: 試験結果。不合格条件: 未知 field を silent に捨てた場合は差し戻し。"
            "対象外: UI。未確定: なし。利害関係者: 保守者。優先度: 必須。",
            strict=True,
        )
        rule_ids = {finding.get("rule_id") for finding in result["findings"]}
        self.assertNotIn("req.solution.problem_mechanism_fit_missing", rule_ids)
        self.assertNotIn("req.acceptance.symptom_only_success_criteria", rule_ids)

    def test_audit_request_flags_missing_scenario_for_user_facing_requirement(self) -> None:
        result = audit_request(
            "利用者: オペレータ。目的: 画面で検索する。"
            "受入基準: 結果が表示されることを確認。検証方法: pytest。"
            "証拠: 試験結果。対象外: UI刷新。未確定: なし。",
            strict=True,
        )
        categories = {finding["category"] for finding in result["findings"]}
        self.assertIn("scenario", categories)
        self.assertIn("scenario_context", result["missing"])

    def test_audit_request_flags_missing_stakeholder_source(self) -> None:
        result = audit_request(
            "目的: 検索結果を絞り込めるようにする。検証: 条件指定で結果が減ることを確認する。対象外: UI刷新。",
            strict=True,
        )
        categories = {finding["category"] for finding in result["findings"]}
        self.assertIn("stakeholder", categories)
        self.assertIn("stakeholder_source", result["missing"])
        self.assertIn("stakeholder_source", result["details"]["requirement_signals"])

    def test_audit_request_flags_quality_without_measurement(self) -> None:
        result = audit_request(
            "利用者: 運用者。目的: 画面を高速で安定させる。検証: 動作確認する。対象外: UI刷新。未確定: なし。",
            strict=True,
        )
        categories = {finding["category"] for finding in result["findings"]}
        self.assertIn("quality", categories)
        self.assertIn("quality_constraint", result["missing"])

    def test_audit_request_accepts_quality_with_threshold(self) -> None:
        result = audit_request(
            "利用者: 運用者。目的: 検索を速くする。受入基準: p95 500ms 以下。検証: ベンチマークで測定する。対象外: UI刷新。未確定: なし。",
            strict=True,
        )
        categories = {finding["category"] for finding in result["findings"]}
        self.assertNotIn("quality", categories)
        self.assertNotIn("quality_constraint", result["missing"])

    def test_audit_request_flags_multi_requirement_without_priority(self) -> None:
        result = audit_request(
            "利用者: 保守者。目的: READMEを更新し、CLIを追加し、MCPも直す。検証: unittestで確認。対象外: UI。未確定: なし。",
            strict=True,
        )
        categories = {finding["category"] for finding in result["findings"]}
        self.assertIn("priority", categories)
        self.assertIn("priority", result["missing"])

    def test_audit_request_bounded_work_package_avoids_atomicity_and_priority_noise(self) -> None:
        result = audit_request(
            "利用者: 保守者。目的: conflict fixture と coverage summary を修正計画の Stage 1 作業パッケージとして実装する。"
            "成果物: evaluation.py、tests、docs。順序: coverage を先に実装し、fixture を後で追加する。"
            "受入基準: unittest と evaluate-fixtures が通る。検証方法: unittest と代表 CLI 実行。"
            "証拠: コマンド結果。対象外: C10。未確定: なし。",
            strict=True,
        )
        categories = {finding["category"] for finding in result["findings"]}
        self.assertNotIn("atomicity", categories)
        self.assertNotIn("priority", categories)
        self.assertNotIn("priority", result["missing"])

    def test_audit_request_flags_unclassified_uncertainty(self) -> None:
        result = audit_request(
            "利用者: 保守者。目的: たぶんCLIを追加する。検証: unittestで確認。対象外: UI。",
            strict=True,
        )
        categories = {finding["category"] for finding in result["findings"]}
        self.assertIn("unknowns", categories)
        self.assertIn("uncertainty_classification", result["missing"])

    def test_audit_request_document_kind_avoids_requirement_prose_warnings(self) -> None:
        document = """
        # Tool

        ## Overview
        This document explains what the tool does and why it exists.

        ## Status
        This is a local prototype, not a release gate.

        ## When To Use
        Use it when a reader needs enough context to run the CLI.

        ## CLI
        Run the CLI and inspect JSON output.

        ```sh
        tool inspect
        ```

        ## Output Shape
        The command returns status, score, findings, missing, and details.

        ## Limitations
        It is heuristic and does not replace secure development review.
        """
        result = audit_request(document, strict=True, input_kind="document")
        categories = {finding["category"] for finding in result["findings"]}
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["details"]["input_kind"], "document")
        self.assertNotIn("clarity", categories)
        self.assertNotIn("atomicity", categories)
        self.assertNotIn("solution_bias", categories)

    def test_audit_request_document_kind_flags_overclaim_without_evidence(self) -> None:
        document = """
        # Tool

        ## Overview
        This is a production-ready secure complete requirements engine.

        ## Status
        Stable.

        ## When To Use
        Use it for every project.

        ## CLI
        Run the tool.

        ## Output Shape
        It returns JSON with status, score, findings, missing, next_actions, and details.

        ## Limitations
        None.
        """
        result = audit_request(document, strict=True, input_kind="document")
        categories = {finding["category"] for finding in result["findings"]}
        self.assertEqual(result["status"], "warn")
        self.assertIn("evidence", categories)
        triples = result["details"]["claim_triples"]
        self.assertTrue(any(triple["strong"] for triple in triples))

    def test_audit_request_document_kind_flags_usage_without_example(self) -> None:
        document = """
        # Tool

        ## Overview
        This document explains the tool.

        ## Status
        Prototype.

        ## When To Use
        Use it when running the CLI.

        ## Output Shape
        It returns JSON with status, score, findings, missing, next_actions, and details.

        ## Limitations
        It is heuristic and does not replace review.
        """
        result = audit_request(document, strict=True, input_kind="document")
        categories = {finding["category"] for finding in result["findings"]}
        self.assertEqual(result["status"], "warn")
        self.assertIn("documentation", categories)
        self.assertIn("executable_example", result["missing"])

    def test_audit_request_document_kind_extracts_claim_evidence_limitation(self) -> None:
        document = """
        # Tool

        ## Overview
        This tool can audit local README files.

        ## When To Use
        Use it when a reader needs document audit context.

        ## CLI
        Run this example:

        ```sh
        tool audit --kind document README.md
        ```

        It is heuristic and does not replace human review.

        ## Output Shape
        It returns JSON with status, score, findings, missing, next_actions, and details.

        ## Limitations
        This is a prototype, not a release gate.
        """
        result = audit_request(document, strict=True, input_kind="document")
        triples = result["details"]["claim_triples"]
        self.assertEqual(result["status"], "pass")
        self.assertTrue(any(triple["claim"].startswith("This tool can audit") for triple in triples))
        self.assertTrue(any(triple["evidence"] for triple in triples))
        self.assertTrue(any(triple["limitations"] for triple in triples))

    def test_audit_request_document_kind_keeps_long_code_evidence_well_formed(self) -> None:
        document = """
        # Tool

        ## CLI
        This command returns audit JSON for changed files.

        Run this example:

        ```sh
        semantic-guard audit-diff --kind diff-summary --intent "契約変更の影響を見る" --text "Changed files: src/semantic_guard/core.py, tests/test_core.py"
        semantic-guard audit-request --kind document --file README.md
        semantic-guard evaluate-fixtures --include-passed
        semantic-guard finish-check --text "実装完了" --evidence "unittest passed"
        ```

        It is heuristic and does not replace human review.

        ## Output Shape
        It returns JSON with status, score, findings, missing, next_actions, and details.

        ## Limitations
        This is a prototype, not a release gate.
        """
        result = audit_request(document, strict=True, input_kind="document")
        triples = result["details"]["claim_triples"]
        code_evidence = [snippet for triple in triples for snippet in triple["evidence"] if snippet.startswith("```")]
        self.assertTrue(code_evidence)
        self.assertTrue(all(snippet.endswith("```") for snippet in code_evidence))

    def test_audit_request_document_kind_summarizes_weak_unsupported_claims(self) -> None:
        document = """
        # Tool

        ## Overview
        This tool can inspect local documents and report heuristic findings.

        ## When To Use
        Use it for document audit.

        ## CLI
        Run this example:

        ```sh
        tool audit --kind document README.md
        ```

        It is a prototype and does not replace human review.

        ## Output Shape
        It returns status, score, findings, missing, next_actions, and details.

        ## Limitations
        Historical claims may be unsupported unless evidence is in the same section.
        """
        result = audit_request(document, strict=True, input_kind="document")
        summary = result["details"]["document_claim_summary"]
        self.assertEqual(result["status"], "pass")
        self.assertGreater(summary["unsupported_count"], 0)
        self.assertEqual(summary["strong_unsupported_count"], 0)

    def test_audit_request_document_kind_skips_question_like_audit_prompts_as_claims(self) -> None:
        document = """
        # Tool

        ## Overview
        It is a local audit helper.

        ## Audit Phases
        whether the target is understood before requirements are refined

        ## CLI
        ```sh
        tool audit --kind document README.md
        ```

        ## Output Shape
        It returns JSON with status, score, findings, missing, next_actions, and details.

        ## Limitations
        It is a prototype, not a release gate.
        """
        result = audit_request(document, strict=True, input_kind="document")
        claims = [triple["claim"] for triple in result["details"]["claim_triples"]]
        self.assertNotIn("whether the target is understood before requirements are refined", claims)

    def test_audit_plan_passes_minimum_structured_plan(self) -> None:
        plan = """
        目的: 要求監査を実装する
        対象外: UI は作らない
        成果物: CLI と MCP
        作業分解: CLI、MCP、試験、文書を作業パッケージに分ける
        手順: 調査、実装、検証、文書更新
        順序: 調査後に実装し、実装後に検証と文書更新を行う
        依存: uv と mcp
        資源: Codex が一作業単位で実施し追加依存は置かない
        リスク: MCP 起動失敗。退避と再検証を行う
        検証: unittest と CLI 実行
        妥当性: 要求の目的に合うか確認する
        判断主体: 利用者が受け入れる
        確認点: 実装後と文書更新後に進捗を確認する
        基準線: 既存 CLI 挙動と unittest 通過を判定基準にする
        決定点: MCP 契約が変わる場合は利用者判断へ回す
        戻し方: config の backup を戻す
        証拠: コマンド結果を残す
        未確定: なし
        """
        result = audit_plan(plan, strict=True)
        self.assertEqual(result["status"], "pass")

    def test_audit_plan_flags_new_dependency_or_abstraction_without_minimality_basis(self) -> None:
        plan = """
        目的: 監査結果を見やすくする。
        対象外: UI は作らない。
        成果物: core.py、tests、README。
        作業分解: core.py、tests、README を作業パッケージに分ける。
        手順: 調査、実装、検証、文書化。
        順序: 調査後に実装し、検証後に文書化する。
        依存: 新規依存として rich package を導入する。
        資源: Codex が一作業単位で実施する。
        リスク: 出力互換が崩れる。対策: 代表 CLI を再検証する。
        検証: unittest と代表 CLI。
        妥当性: 利用者が受入判断する。
        判断主体: 利用者。
        確認点: 実装後に進捗確認。
        基準線: 既存 fixture 通過を判定基準にする。
        戻し方: 差分を戻す。
        証拠: コマンド結果。
        未確定: なし。
        """
        result = audit_plan(plan, strict=True)
        rule_ids = {finding.get("rule_id") for finding in result["findings"]}

        self.assertIn("plan.minimality.justification_missing", rule_ids)
        self.assertIn("minimality", {finding["category"] for finding in result["findings"]})
        self.assertIn("minimality_justification", result["missing"])
        self.assertIn("minimality_justification", result["details"]["planning_signals"])

    def test_audit_plan_accepts_new_structure_when_minimality_basis_is_explicit(self) -> None:
        plan = """
        目的: 監査結果を見やすくする。
        対象外: UI は作らない。
        成果物: core.py、tests、README。
        作業分解: core.py、tests、README を作業パッケージに分ける。
        手順: 調査、実装、検証、文書化。
        順序: 調査後に実装し、検証後に文書化する。
        依存: 既存 CLI と Python 標準 json を再利用し、追加依存なし。
        資源: Codex が一作業単位で実施する。
        リスク: 出力互換が崩れる。対策: 代表 CLI を再検証する。
        検証: unittest と代表 CLI。
        妥当性: 利用者が受入判断する。
        判断主体: 利用者。
        確認点: 実装後に進捗確認。
        基準線: 既存 fixture 通過を判定基準にする。
        戻し方: 差分を戻す。
        証拠: コマンド結果。
        未確定: なし。
        """
        result = audit_plan(plan, strict=True)
        rule_ids = {finding.get("rule_id") for finding in result["findings"]}

        self.assertEqual(result["status"], "pass")
        self.assertNotIn("plan.minimality.justification_missing", rule_ids)
        self.assertNotIn("minimality_justification", result["missing"])

    def test_audit_plan_recognizes_japanese_synonym_headings(self) -> None:
        plan = """
        狙い: 日本語の要望書を過剰警告せず監査する。
        やらないこと: 外部規格の完全実装はしない。
        納品物: core.py、試験、README。
        作業分解: core.py、試験、README をファイル別作業に分ける。
        工程: 読解、実装、検査、文書化。
        順序: 読解後に実装し、検査後に文書化する。
        前提条件: 既存 CLI と unittest を使う。
        資源: Codex が一作業単位で実施し、追加依存なし。
        懸念: 語彙を広げすぎると誤通過する。対策として代表例で再検証する。
        検査: unittest と代表 CLI を走らせる。
        受入基準: 要望書の改善点に対応している。
        判断主体: 人間が受入を判断する。
        進捗確認: 各工程後に状態を確認する。
        基準線: 既存の期待値と新規試験通過を判定基準にする。
        切戻し: 差分単位で戻す。
        証跡: コマンド結果を残す。
        未決: なし。
        """
        result = audit_plan(plan, strict=True)
        self.assertEqual(result["status"], "pass")
        self.assertNotIn("unknowns_or_decisions", result["missing"])

    def test_audit_plan_flags_missing_validation_owner(self) -> None:
        plan = """
        目的: 監査を改善する。
        対象外: UI は作らない。
        成果物: core.py と tests。
        手順: 調査、実装、検証。
        依存: 既存 CLI。
        リスク: 過剰警告。
        検証: unittest。
        妥当性: 要求に合うことを確認する。
        確認点: 実装後に進捗確認。
        戻し方: 差分を戻す。
        証拠: コマンド結果。
        未確定: なし。
        """
        result = audit_plan(plan, strict=True)
        categories = {finding["category"] for finding in result["findings"]}
        self.assertIn("validation", categories)
        self.assertIn("validation_owner", result["missing"])

    def test_audit_plan_flags_progress_control_for_multi_step_plan(self) -> None:
        plan = """
        目的: 監査を改善する。
        対象外: UI は作らない。
        成果物: core.py と tests。
        手順: 調査、実装、検証、文書化。
        依存: 既存 CLI。
        リスク: 過剰警告。
        検証: unittest。
        妥当性: 要求に合うことを利用者が確認する。
        判断主体: 利用者。
        戻し方: 差分を戻す。
        証拠: コマンド結果。
        未確定: なし。
        """
        result = audit_plan(plan, strict=True)
        categories = {finding["category"] for finding in result["findings"]}
        self.assertIn("control", categories)
        self.assertIn("progress_control", result["missing"])

    def test_audit_plan_flags_change_control_for_migration_plan(self) -> None:
        plan = """
        目的: 設定を移行する。
        対象外: UI は作らない。
        成果物: config と README。
        手順: 調査、実装、検証。
        依存: 既存 config。
        リスク: 既存運用が壊れる。
        検証: unittest。
        妥当性: 利用者が受入判断する。
        判断主体: 利用者。
        確認点: 実装後に進捗確認。
        戻し方: backup を戻す。
        証拠: コマンド結果。
        未確定: なし。
        """
        result = audit_plan(plan, strict=True)
        self.assertIn("change_control", result["missing"])
        self.assertIn("change_control", result["details"]["planning_signals"])

    def test_audit_plan_records_satisfied_change_control_non_emission(self) -> None:
        plan = """
        目的: 設定を移行する。
        対象外: UI は作らない。
        成果物: config と README。
        作業分解: config と README を作業パッケージに分ける。
        手順: 調査、実装、検証、文書化。
        順序: 調査後に実装し、検証後に文書化する。
        依存: 既存 config。
        資源: Codex が一作業単位で実施し追加依存なし。
        リスク: 既存運用が壊れる。対策として backup へ退避する。
        検証: unittest。
        妥当性: 利用者が受入判断する。
        判断主体: 利用者。
        確認点: 実装後に進捗確認。
        基準線: 既存 config と unittest 通過を判定基準にする。
        変更統制: 追加要求は後続化し、範囲変更は判断待ちへ送る。
        決定点: 公開判断は利用者へ回す。
        戻し方: backup を戻す。
        証拠: コマンド結果。
        未確定: なし。
        """
        result = audit_plan(plan, strict=True)
        rule_ids = {finding.get("rule_id") for finding in result["findings"]}
        suppressed = result["details"]["suppressed_rules"]
        trace = next(item for item in suppressed if item["rule_id"] == "plan.control.change_control_missing")
        self.assertEqual(result["status"], "pass")
        self.assertNotIn("change_control", result["missing"])
        self.assertNotIn("change_control", result["details"]["planning_signals"])
        self.assertNotIn("plan.control.change_control_missing", rule_ids)
        self.assertEqual(trace["emission_status"], "satisfied")
        self.assertEqual(trace["match_status"], "matched")
        self.assertEqual(trace["reason"], "explicit_change_control_boundary_satisfies_rule")
        self.assertIn("変更統制", trace["evidence"])
        self.assertEqual(result["details"]["suppressed_rule_counts"]["plan.control.change_control_missing"], 1)

    def test_audit_plan_flags_missing_work_package_decomposition(self) -> None:
        plan = """
        目的: 監査を拡張する。
        対象外: UI は作らない。
        成果物: core.py、rules.py、tests、README。
        手順: 調査、実装、検証、文書化。
        順序: 調査後に実装し、検証後に文書化する。
        依存: 既存 CLI。
        資源: Codex が一作業単位で実施する。
        リスク: 語彙過多。対策として代表例で再検証する。
        検証: unittest。
        妥当性: 利用者が要求に合うか確認する。
        判断主体: 利用者。
        確認点: 実装後に進捗確認。
        基準線: 既存試験通過を判定基準にする。
        戻し方: 差分を戻す。
        証拠: コマンド結果。
        未確定: なし。
        """
        result = audit_plan(plan, strict=True)
        self.assertIn("work_package_decomposition", result["missing"])
        self.assertIn("work_package_decomposition", result["details"]["planning_signals"])

    def test_audit_plan_all_scope_with_bounded_controls_does_not_warn_scope(self) -> None:
        result = audit_plan(
            "目的: 監査全体を確認する。対象外: 全面刷新はしない。成果物: core.py、tests、README。"
            "作業分解: core.py、tests、README を作業パッケージに分ける。手順: 調査、実装、検証。"
            "順序: 調査後に実装し、検証後に文書化する。依存: 既存 CLI。資源: Codex が一作業単位で実施する。"
            "リスク: 誤警告。対策: 代表 fixture で再検証する。検証: unittest。"
            "妥当性: 利用者が受入判断する。判断主体: 利用者。確認点: 実装後。基準線: 既存試験通過。"
            "変更統制: 追加要求は後続化する。決定点: 受入は利用者。戻し方: 差分を戻す。"
            "証拠: コマンド結果。未確定: なし。",
            strict=True,
        )
        categories = {finding["category"] for finding in result["findings"]}
        self.assertNotIn("scope", categories)
        non_emitted = result["details"]["non_emitted_rules"]
        self.assertTrue(any(item["rule_id"] == "plan.scope.broad_scope_unbounded" for item in non_emitted))

    def test_audit_plan_flags_missing_dependency_sequence_and_resource_basis(self) -> None:
        plan = """
        目的: 監査を拡張する。
        対象外: UI は作らない。
        成果物: core.py と tests。
        作業分解: core.py と tests を作業パッケージに分ける。
        手順: 調査、実装、検証。
        依存: 既存 CLI。
        リスク: 過剰警告。対策として代表例で再検証する。
        検証: unittest。
        妥当性: 利用者が要求に合うか確認する。
        判断主体: 利用者。
        確認点: 実装後に進捗確認。
        基準線: 既存試験通過を判定基準にする。
        戻し方: 差分を戻す。
        証拠: コマンド結果。
        未確定: なし。
        """
        result = audit_plan(plan, strict=True)
        self.assertIn("dependency_sequence", result["missing"])
        self.assertIn("estimation_or_resource_basis", result["missing"])

    def test_audit_plan_flags_risk_without_response_and_missing_control_baseline(self) -> None:
        plan = """
        目的: 監査を拡張する。
        対象外: UI は作らない。
        成果物: core.py と tests。
        作業分解: core.py と tests を作業パッケージに分ける。
        手順: 調査、実装、検証。
        順序: 調査後に実装し、実装後に検証する。
        依存: 既存 CLI。
        資源: Codex が一作業単位で実施する。
        リスク: 過剰警告。
        検証: unittest。
        妥当性: 利用者が要求に合うか確認する。
        判断主体: 利用者。
        確認点: 実装後に進捗確認。
        戻し方: 差分を戻す。
        証拠: コマンド結果。
        未確定: なし。
        """
        result = audit_plan(plan, strict=True)
        self.assertIn("risk_response", result["missing"])
        self.assertIn("control_baseline", result["missing"])

    def test_audit_plan_flags_missing_hazard_transfer_analysis(self) -> None:
        plan = """
        目的: API import が止まる問題を解決する。
        対象外: UI は作らない。
        成果物: import 設定と tests。
        作業分解: import 設定と tests を作業パッケージに分ける。
        手順: 調査、実装、検証。
        順序: 調査後に実装し、検証後に文書化する。
        依存: 既存 API。
        資源: Codex が一作業単位で実施する。
        リスク: なし。対策: 代表実行で確認する。
        解決策: retry 回数を増やす。
        検証: pytest。
        妥当性: 利用者が受入判断する。
        判断主体: 利用者。
        確認点: 実装後に進捗確認。
        基準線: import 成功を判定基準にする。
        決定点: 失敗時は利用者へ回す。
        戻し方: 設定を戻す。
        証拠: コマンド結果。
        未確定: なし。
        """
        result = audit_plan(plan, strict=True)
        self.assertIn("hazard_transfer_analysis", result["missing"])
        self.assertIn("hazard_transfer_analysis", result["details"]["planning_signals"])

    def test_audit_plan_accepts_hazard_transfer_analysis(self) -> None:
        plan = """
        目的: API import が止まる問題を解決する。
        対象外: UI は作らない。
        成果物: import 設定と tests。
        作業分解: import 設定と tests を作業パッケージに分ける。
        手順: 調査、実装、検証。
        順序: 調査後に実装し、検証後に文書化する。
        依存: 既存 API。
        資源: Codex が一作業単位で実施する。
        リスク: 下流 API 負荷と費用が増える。対策: 下流影響と費用を測定し、閾値超過時は保留する。
        解決策: retry 回数を増やす。
        副作用確認: 下流 API 負荷、費用、回帰影響を測定する。
        検証: pytest。
        妥当性: 利用者が受入判断する。
        判断主体: 利用者。
        確認点: 実装後に進捗確認。
        基準線: import 成功と下流 API 負荷を判定基準にする。
        決定点: 下流影響が許容外なら利用者へ回す。
        戻し方: 設定を戻す。
        証拠: コマンド結果。
        未確定: なし。
        """
        result = audit_plan(plan, strict=True)
        self.assertNotIn("hazard_transfer_analysis", result["missing"])
        self.assertNotIn("hazard_transfer_analysis", result["details"]["planning_signals"])

    def test_audit_plan_flags_missing_decision_gate_for_release_plan(self) -> None:
        plan = """
        目的: 設定を公開する。
        対象外: UI は作らない。
        成果物: config と README。
        作業分解: config と README を作業パッケージに分ける。
        手順: 調査、実装、検証。
        順序: 調査後に実装し、検証後に公開する。
        依存: 既存 config。
        資源: Codex が一作業単位で実施する。
        リスク: 既存運用が壊れる。対策として backup へ退避する。
        検証: unittest。
        妥当性: 利用者が受入判断する。
        判断主体: 利用者。
        確認点: 実装後に進捗確認。
        基準線: 既存 config と unittest 通過を判定基準にする。
        変更統制: 追加要求は後続化する。
        戻し方: backup を戻す。
        証拠: コマンド結果。
        未確定: なし。
        """
        result = audit_plan(plan, strict=True)
        self.assertIn("decision_gate", result["missing"])
        self.assertIn("decision_gate", result["details"]["planning_signals"])

    def test_missing_plan_field_reports_nearest_candidate_and_warning_class(self) -> None:
        plan = """
        目的: 欠落候補を表示する。
        対象外: 判定器の大改修はしない。
        成果物: core.py と README。
        手順: 実装、整理、文書化。
        依存: 既存 API。
        リスク: 誤警告。
        点検方針: 人間が画面を見る。
        妥当性: 要望に合う。
        戻し方: 差分を戻す。
        証拠: 結果を残す。
        未確定: なし。
        """
        result = audit_plan(plan, strict=True)
        verification_findings = [
            finding for finding in result["findings"] if "verification_plan" in finding["finding"]
        ]
        self.assertTrue(verification_findings)
        self.assertEqual(verification_findings[0]["warning_class"], "possible false positive")
        self.assertIn("点検方針", verification_findings[0]["nearest_candidates"][0])
        self.assertEqual(verification_findings[0]["match_status"], "partial")
        self.assertEqual(verification_findings[0]["confidence"], "medium")
        self.assertIn("weak_synonym", verification_findings[0]["ambiguity_reasons"])
        self.assertEqual(verification_findings[0]["candidate_matches"][0]["status"], "partial")

    def test_audit_plan_accepts_english_work_package_decomposition_heading(self) -> None:
        plan = """
        Objective: implement ambiguity diagnostics.
        Non-goals: no external NLP dependency or automatic exec execution.
        Deliverables: models.py, matching.py, core.py, evaluation.py, escalation.py, tests, README.

        ### Work Package Decomposition
        - model fields and serialization
        - candidate extraction
        - missing-field integration
        - escalation integration
        - documentation updates

        Dependency Sequence: model first, matching second, core third, evaluation and escalation after that.
        Resource Basis: Codex handles this as one bounded code change with no additional dependency.
        Risks And Responses: false acceptance is limited by keeping weak synonyms partial; output breakage is limited by optional fields.
        Verification: unittest, compileall, and evaluate-fixtures.
        Validation owner: maintainer accepts the JSON output shape.
        Decision Gate: do not change status or score calculation in this pass.
        Rollback: revert optional fields, matching.py, and escalation additions.
        Completion Evidence: command results are recorded.
        Open Decisions: numeric thresholds remain pending.
        """
        result = audit_plan(plan, strict=True)
        self.assertEqual(result["status"], "pass")
        self.assertNotIn("work_breakdown", result["missing"])

    def test_document_overclaim_marks_missing_runtime_evidence_as_document_only(self) -> None:
        document = """
        # Audit Engine

        ## Overview
        This is a production-ready secure complete requirements engine.

        ## Status
        Stable.

        ## When To Use
        Use it for every project.

        ## Output Shape
        It returns JSON with status, score, findings, missing, next_actions, and details.

        ## Limitations
        None.
        """
        result = audit_request(document, strict=True, input_kind="document")
        self.assertTrue(result["details"]["document_checks"]["no_implementation_evidence_available"])
        evidence_findings = [finding for finding in result["findings"] if finding["category"] == "evidence"]
        self.assertTrue(evidence_findings)
        self.assertTrue(any(finding["warning_class"] == "generic caution" for finding in evidence_findings))

    def test_audit_diff_names_likely_semantic_boundaries(self) -> None:
        result = audit_diff(
            "*** Update File: docs/model.md\n"
            "Changed canonical source of truth, storage path, and user identifier handling.",
            intent="正本と永続化先と識別子の意味境界を見直す。",
            strict=True,
        )
        meaning_findings = [finding for finding in result["findings"] if finding["category"] == "meaning"]
        self.assertTrue(meaning_findings)
        boundaries = set(meaning_findings[0]["semantic_boundaries"])
        self.assertIn("source_of_truth", boundaries)
        self.assertIn("persistence", boundaries)
        self.assertIn("identity", boundaries)

    def test_audit_diff_semantic_boundary_evidence_uses_complete_summary_line(self) -> None:
        summary = (
            "Changed docs/model.md: canonical source of truth now comes from docs/model.md, "
            "while the old storage path remains documented for migration review."
        )
        result = audit_diff(
            summary,
            intent="正本と保存先の意味境界を見直す。",
            strict=True,
        )
        source_boundary = next(
            boundary
            for boundary in result["details"]["semantic_boundaries"]
            if boundary["boundary"] == "source_of_truth"
        )
        meaning_finding = next(finding for finding in result["findings"] if finding["category"] == "meaning")
        self.assertEqual(source_boundary["evidence"], summary)
        self.assertEqual(meaning_finding["evidence"].count(summary), 1)

    def test_audit_diff_extracts_changed_files_from_diff_summary_text(self) -> None:
        result = audit_diff(
            "Changed files: src/semantic_guard/core.py, tests/test_core.py\n"
            "Updated diff-summary changed_files extraction.",
            intent="変更要約からファイル名を拾う。",
            strict=True,
        )
        self.assertEqual(
            result["details"]["changed_files"],
            ["src/semantic_guard/core.py", "tests/test_core.py"],
        )
        self.assertEqual(result["details"]["changed_file_count"], 2)
        self.assertNotIn("test_obligation", result["missing"])

    def test_audit_diff_extracts_file_names_from_summary_sentence(self) -> None:
        result = audit_diff(
            "Updated src/semantic_guard/core.py and tests/test_core.py to parse audit-diff summary file names.",
            intent="変更要約からファイル名を拾う。",
            strict=True,
        )
        self.assertEqual(
            result["details"]["changed_files"],
            ["src/semantic_guard/core.py", "tests/test_core.py"],
        )

    def test_audit_diff_does_not_treat_migration_review_as_failure_operation(self) -> None:
        result = audit_diff(
            "Changed files: src/semantic_guard/core.py, tests/test_core.py\n"
            "Changed docs/model.md: canonical source of truth now comes from docs/model.md, "
            "while the old storage path remains documented for migration review.",
            intent="変更要約からファイル名を拾い、意味境界の証拠表示を自然にする。",
            strict=True,
        )
        categories = {finding["category"] for finding in result["findings"]}
        self.assertNotIn("reliability", categories)
        self.assertNotIn("failure_handling", result["missing"])

    def test_audit_diff_docs_only_evidence_boundary_is_document_only(self) -> None:
        result = audit_diff(
            "*** Update File: docs/example.md\n"
            "+ 検証証拠: audit-request --kind document を実行し、status pass を確認。\n"
            "+ 受入基準: 文書の usage と limitations が読める。",
            intent="docs に検証証拠を追記する。",
            strict=True,
        )
        categories = {finding["category"] for finding in result["findings"]}
        self.assertEqual(result["status"], "pass")
        self.assertNotIn("meaning", categories)
        self.assertEqual(result["details"]["document_only_boundaries"][0]["emission_status"], "document_only")

    def test_audit_diff_flags_public_contract_change(self) -> None:
        result = audit_diff(
            "*** Update File: src/semantic_guard/cli.py\n"
            "+ Added --execute option and changed JSON output schema defaults.",
            intent="CLI の公開契約を拡張する。",
            strict=True,
        )
        categories = {finding["category"] for finding in result["findings"]}
        self.assertIn("compatibility", categories)
        self.assertIn("public_contract_evidence", result["missing"])
        self.assertIn("public_contract", result["details"]["implementation_signals"])

    def test_audit_diff_flags_failure_prone_operation_without_handling(self) -> None:
        result = audit_diff(
            "*** Update File: src/semantic_guard/runner.py\n"
            "+ result = subprocess.run(command)",
            intent="外部実行 runner を追加する。",
            strict=True,
        )
        categories = {finding["category"] for finding in result["findings"]}
        self.assertIn("reliability", categories)
        self.assertIn("failure_handling", result["missing"])

    def test_audit_diff_still_flags_executable_migration_without_handling(self) -> None:
        result = audit_diff(
            "*** Update File: src/semantic_guard/migration.py\n"
            "+ run_database_migration()",
            intent="DB 移行処理を追加する。",
            strict=True,
        )
        categories = {finding["category"] for finding in result["findings"]}
        self.assertIn("reliability", categories)
        self.assertIn("failure_handling", result["missing"])

    def test_audit_diff_accepts_failure_operation_with_timeout_and_exception_handling(self) -> None:
        result = audit_diff(
            "*** Update File: src/semantic_guard/runner.py\n"
            "+ try:\n"
            "+     result = subprocess.run(command, timeout=30)\n"
            "+ except TimeoutError:\n"
            "+     return {'status': 'timeout'}",
            intent="外部実行 runner を timeout 付きで追加する。",
            strict=True,
        )
        categories = {finding["category"] for finding in result["findings"]}
        self.assertNotIn("reliability", categories)
        self.assertNotIn("failure_handling", result["missing"])

    def test_audit_diff_flags_operational_observability_gap(self) -> None:
        result = audit_diff(
            "*** Add File: src/semantic_guard/daemon.py\n"
            "+ start_background_scheduler(webhook_url)\n"
            "+ send_notification(payload)",
            intent="定期実行と通知を追加する。",
            strict=True,
        )
        categories = {finding["category"] for finding in result["findings"]}
        self.assertIn("operations", categories)
        self.assertIn("observability_evidence", result["missing"])

    def test_audit_diff_flags_dependency_runtime_change(self) -> None:
        result = audit_diff(
            "*** Update File: pyproject.toml\n"
            "+ dependencies = ['mcp>=1.0']",
            intent="依存を追加する。",
            strict=True,
        )
        categories = {finding["category"] for finding in result["findings"]}
        self.assertIn("dependency", categories)
        self.assertIn("dependency_runtime_evidence", result["missing"])

    def test_audit_diff_flags_complexity_growth_as_minimality_rule(self) -> None:
        result = audit_diff(
            "*** Update File: src/semantic_guard/example.py\n"
            "+def collect_visible(rows):\n"
            "+    try:\n"
            "+        output = []\n"
            "+        for row in rows:\n"
            "+            if row.enabled:\n"
            "+                for item in row.items:\n"
            "+                    if item.visible:\n"
            "+                        output.append(item)\n"
            "+        while rows:\n"
            "+            if len(rows) > 1:\n"
            "+                for extra in rows[0].extras:\n"
            "+                    if extra.active:\n"
            "+                        output.append(extra)\n"
            "+        return output\n"
            "+    except Exception:\n"
            "+        return []",
            intent="既存処理を読みやすくする。",
            strict=True,
        )
        rule_ids = {finding.get("rule_id") for finding in result["findings"]}

        self.assertIn("diff.implementation.complexity_growth", rule_ids)
        self.assertIn("minimality", {finding["category"] for finding in result["findings"]})
        self.assertIn("complexity_growth", result["details"])

    def test_audit_diff_does_not_treat_decision_as_ci_runtime_change(self) -> None:
        result = audit_diff(
            "Changed docs: kept final human decision unchanged and documented evidence boundaries.",
            intent="人間判断境界と証拠説明を文書化する。依存や実行環境は変更しない。",
            strict=True,
        )
        categories = {finding["category"] for finding in result["findings"]}
        self.assertNotIn("dependency", categories)
        self.assertNotIn("dependency_runtime_evidence", result["missing"])
        self.assertNotIn("dependency_runtime", result["details"]["implementation_signals"])

    def test_audit_diff_still_flags_ci_runtime_change_when_ci_is_token(self) -> None:
        result = audit_diff(
            "Changed workflow configuration: CI/CD runtime now uses Python 3.13.",
            intent="CI 実行環境を変更する。",
            strict=True,
        )
        categories = {finding["category"] for finding in result["findings"]}
        self.assertIn("dependency", categories)
        self.assertIn("dependency_runtime_evidence", result["missing"])
        self.assertIn("dependency_runtime", result["details"]["implementation_signals"])

    def test_audit_diff_does_not_treat_command_word_as_security_signal(self) -> None:
        result = audit_diff(
            "*** Update File: cli.py\nAdded command defaults for --kind.",
            intent="入力種別 kind の CLI 既定値を追加する。",
            strict=True,
        )
        categories = {finding["category"] for finding in result["findings"]}
        self.assertNotIn("security", categories)

    def test_audit_diff_does_not_treat_avoid_as_identifier_signal(self) -> None:
        result = audit_diff(
            "*** Update File: core.py\nAvoid generic command-word false positives.",
            intent="過剰警告を減らす。",
            strict=True,
        )
        categories = {finding["category"] for finding in result["findings"]}
        self.assertNotIn("meaning", categories)

    def test_audit_diff_does_not_treat_audit_path_as_file_path_signal(self) -> None:
        result = audit_diff(
            "*** Update File: core.py\nAdded document audit path.",
            intent="文書監査分岐を追加する。",
            strict=True,
        )
        categories = {finding["category"] for finding in result["findings"]}
        self.assertNotIn("meaning", categories)

    def test_audit_diff_does_not_treat_reviewer_role_as_security_signal(self) -> None:
        result = audit_diff(
            "*** Add File: docs/llm-reviewer.md\nDocumented reviewer role boundary.",
            intent="LLM査読役の役割境界を文書化する。",
            strict=True,
        )
        categories = {finding["category"] for finding in result["findings"]}
        self.assertNotIn("security", categories)

    def test_finish_check_requires_evidence(self) -> None:
        result = finish_check("実装した", strict=True)
        self.assertEqual(result["status"], "block")

    def test_finish_check_flags_public_behavior_without_smoke_evidence(self) -> None:
        result = finish_check(
            summary="CLI command の JSON output を実装した。",
            evidence="unittest passed. 受入条件と証拠の対応あり。残リスクなし。",
            strict=True,
        )
        categories = {finding["category"] for finding in result["findings"]}
        self.assertIn("behavior", categories)
        self.assertIn("behavior_evidence", result["missing"])

    def test_finish_check_accepts_public_behavior_with_representative_execution(self) -> None:
        result = finish_check(
            summary="CLI command の JSON output を実装した。",
            evidence=(
                "unittest passed. representative semantic-guard audit-diff execution returned JSON output. "
                "受入条件と証拠の対応あり。残リスクなし。"
            ),
            strict=True,
        )
        categories = {finding["category"] for finding in result["findings"]}
        self.assertNotIn("behavior", categories)
        self.assertNotIn("behavior_evidence", result["missing"])


if __name__ == "__main__":
    unittest.main()
