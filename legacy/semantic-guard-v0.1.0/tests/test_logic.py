from __future__ import annotations

import json
import unittest

from semantic_guard.core import audit_request
from semantic_guard.logic import (
    ACCEPTANCE_MISSING_RULE_ID,
    ACHIEVEMENT_CRITERIA_RULE_ID,
    EVIDENCE_ARTIFACT_RULE_ID,
    FACT_STATUSES_THAT_SATISFY_OBLIGATION,
    DERIVATION_SCOPE,
    METHOD_DETAIL_RULE_ID,
    OBSERVABLE_BEHAVIOR_RULE_ID,
    REJECTION_CONDITION_RULE_ID,
    SCENARIO_CONTEXT_RULE_ID,
    Countercondition,
    EvidenceSpan,
    Fact,
    FactSource,
    LogicalTrace,
    Obligation,
    DerivationStep,
    RuleEvaluation,
    build_acceptance_missing_trace,
    build_request_verification_trace,
    derivation_for_rule,
)

REQUEST_LOGICAL_RULE_IDS = {
    ACCEPTANCE_MISSING_RULE_ID,
    ACHIEVEMENT_CRITERIA_RULE_ID,
    METHOD_DETAIL_RULE_ID,
    EVIDENCE_ARTIFACT_RULE_ID,
    REJECTION_CONDITION_RULE_ID,
    SCENARIO_CONTEXT_RULE_ID,
    OBSERVABLE_BEHAVIOR_RULE_ID,
}


class LogicalAuditModelTests(unittest.TestCase):
    def test_fact_serialization_matches_design_shape(self) -> None:
        fact = Fact(
            id="fact.text.has_verification_language",
            name="text.has_verification_language",
            status="absent",
            value=False,
            source=FactSource(kind="deterministic_extractor", label="verification_terms"),
            evidence=[],
            extraction_method="known_terms_absence",
            confidence="high",
            notes="Scoped to supplied request text and context.",
            checked_scope="request+context",
        )

        payload = fact.as_dict()

        self.assertEqual(
            payload,
            {
                "id": "fact.text.has_verification_language",
                "name": "text.has_verification_language",
                "status": "absent",
                "source": {"kind": "deterministic_extractor", "label": "verification_terms"},
                "evidence": [],
                "extraction_method": "known_terms_absence",
                "value": False,
                "confidence": "high",
                "notes": "Scoped to supplied request text and context.",
                "checked_scope": "request+context",
            },
        )
        self.assertIn('"value": false', json.dumps(payload, ensure_ascii=False, sort_keys=True))

    def test_evidence_span_serialization_omits_unknown_offsets(self) -> None:
        span = EvidenceSpan(
            source="request",
            field="text",
            excerpt="Verification: run unit tests and inspect JSON output.",
        )

        self.assertEqual(
            span.as_dict(),
            {
                "source": "request",
                "field": "text",
                "excerpt": "Verification: run unit tests and inspect JSON output.",
            },
        )

    def test_rule_evaluation_and_derivation_step_are_json_safe(self) -> None:
        rule = RuleEvaluation(
            rule_id="req.verifiability.acceptance_missing",
            phase="audit_request",
            predicate_id="req.verifiability.acceptance_missing/v1",
            status="derived",
            facts_used=["fact.input.kind", "fact.text.has_verification_language"],
            counterconditions_checked=["ctr.input_kind_not_requirement"],
            obligations=["obl.verification_or_acceptance"],
            finding_ids=["finding.req.verifiability.acceptance_missing"],
            derivation_steps=["step.001"],
        )
        step = DerivationStep(
            id="step.001",
            statement="No verification or acceptance fact was accepted in the checked request/context scope.",
            from_ids=["fact.text.has_verification_language", "fact.text.has_acceptance_criteria"],
            to="obl.verification_or_acceptance",
            operator="all_absent",
        )

        encoded = json.dumps({"rule": rule.as_dict(), "step": step.as_dict()}, ensure_ascii=False, sort_keys=True)

        self.assertIn('"predicate_id": "req.verifiability.acceptance_missing/v1"', encoded)
        self.assertIn('"from": ["fact.text.has_verification_language", "fact.text.has_acceptance_criteria"]', encoded)

    def test_obligation_and_countercondition_defaults_are_explicit(self) -> None:
        obligation = Obligation(
            id="obl.verification_or_acceptance",
            rule_id="req.verifiability.acceptance_missing",
            description="Requirement must state how achievement will be verified or accepted.",
        )
        countercondition = Countercondition(
            id="ctr.input_kind_not_requirement",
            rule_id="req.verifiability.acceptance_missing",
            description="Rule does not apply to document, plan, diff-summary, or finish input.",
        )

        self.assertEqual(obligation.as_dict()["status"], "unknown")
        self.assertEqual(obligation.as_dict()["required_facts"], [])
        self.assertEqual(countercondition.as_dict()["status"], "unknown")
        self.assertEqual(countercondition.as_dict()["effect"], "defer")

    def test_logical_trace_empty_state_is_json_safe(self) -> None:
        trace = LogicalTrace(phase="audit_request")

        payload = trace.as_dict()

        self.assertEqual(payload["schema_version"], "logical-trace/v1")
        self.assertEqual(payload["scope"], "extracted facts and executable predicates only")
        self.assertEqual(payload["derivation_scope"], DERIVATION_SCOPE)
        self.assertEqual(payload["rules_evaluated"], [])
        self.assertEqual(payload["facts"], [])
        self.assertEqual(payload["obligations"], [])
        self.assertEqual(payload["counterconditions"], [])
        self.assertEqual(payload["derivation_steps"], [])
        self.assertEqual(payload["unknowns"], [])
        self.assertEqual(payload["conflicts"], [])
        self.assertIn("logical-trace/v1", json.dumps(payload, ensure_ascii=False, sort_keys=True))

    def test_logical_trace_with_nested_models_serializes(self) -> None:
        trace = LogicalTrace(
            phase="audit_request",
            facts=[
                Fact(
                    id="fact.input.kind",
                    name="input.kind",
                    status="present",
                    value="requirement",
                    source=FactSource(kind="input_kind", label="requirement"),
                    extraction_method="caller_supplied_kind",
                    evidence=[],
                )
            ],
            rules_evaluated=[
                RuleEvaluation(
                    rule_id="req.verifiability.acceptance_missing",
                    phase="audit_request",
                    predicate_id="req.verifiability.acceptance_missing/v1",
                    status="derived",
                )
            ],
            unknowns=["fact.text.has_acceptance_criteria"],
            conflicts=[],
        )

        payload = trace.as_dict()

        self.assertEqual(payload["facts"][0]["source"], {"kind": "input_kind", "label": "requirement"})
        self.assertEqual(payload["rules_evaluated"][0]["status"], "derived")
        json.dumps(payload, ensure_ascii=False, sort_keys=True)

    def test_only_present_fact_status_satisfies_obligation(self) -> None:
        self.assertEqual(FACT_STATUSES_THAT_SATISFY_OBLIGATION, frozenset({"present"}))
        for status in ["absent", "candidate", "rejected", "unknown", "conflict"]:
            with self.subTest(status=status):
                self.assertNotIn(status, FACT_STATUSES_THAT_SATISFY_OBLIGATION)

    def test_acceptance_missing_trace_derives_target_rule_from_absent_verification(self) -> None:
        trace = build_acceptance_missing_trace(text="目的: 速度改善をしたい。", input_kind="requirement")
        payload = trace.as_dict()
        rule_statuses = {rule["rule_id"]: rule["status"] for rule in payload["rules_evaluated"]}

        self.assertEqual(payload["rules_evaluated"][0]["rule_id"], ACCEPTANCE_MISSING_RULE_ID)
        self.assertEqual(rule_statuses[ACCEPTANCE_MISSING_RULE_ID], "derived")
        self.assertEqual(rule_statuses[METHOD_DETAIL_RULE_ID], "not_applicable")
        self.assertEqual(rule_statuses[OBSERVABLE_BEHAVIOR_RULE_ID], "derived")
        fact_statuses = {fact["name"]: fact["status"] for fact in payload["facts"]}
        self.assertEqual(fact_statuses["input.kind.requirement"], "present")
        self.assertEqual(fact_statuses["text.has_verification_language"], "absent")
        self.assertEqual(payload["obligations"][0]["status"], "missing")
        self.assertEqual(payload["counterconditions"][0]["effect"], "continue")

    def test_method_detail_trace_derives_from_generic_verification_language(self) -> None:
        trace = build_request_verification_trace(
            text="利用者: 保守者。目的: 検索機能を改善する。検証: 動作確認する。対象外: UI刷新。未確定: なし。",
            input_kind="requirement",
        )
        payload = trace.as_dict()
        rule_statuses = {rule["rule_id"]: rule["status"] for rule in payload["rules_evaluated"]}
        method_derivation = derivation_for_rule(trace, METHOD_DETAIL_RULE_ID)

        self.assertEqual(rule_statuses[ACCEPTANCE_MISSING_RULE_ID], "not_derived")
        self.assertEqual(rule_statuses[METHOD_DETAIL_RULE_ID], "derived")
        self.assertEqual(method_derivation["rule_id"], METHOD_DETAIL_RULE_ID)
        self.assertEqual(method_derivation["status"], "derived")
        self.assertIn("obl.req.verification.method_detail", {item["id"] for item in method_derivation["missing_obligations"]})

    def test_additional_request_rules_derive_from_existing_requirement_signals(self) -> None:
        trace = build_request_verification_trace(
            text="利用者: 保守者。目的: 検索機能を改善する。検証: 動作確認する。対象外: UI刷新。未確定: なし。",
            input_kind="requirement",
        )
        payload = trace.as_dict()
        rule_statuses = {rule["rule_id"]: rule["status"] for rule in payload["rules_evaluated"]}

        self.assertEqual(rule_statuses[ACHIEVEMENT_CRITERIA_RULE_ID], "derived")
        self.assertEqual(rule_statuses[EVIDENCE_ARTIFACT_RULE_ID], "derived")
        self.assertEqual(rule_statuses[SCENARIO_CONTEXT_RULE_ID], "derived")
        self.assertEqual(rule_statuses[OBSERVABLE_BEHAVIOR_RULE_ID], "satisfied")
        achievement_derivation = derivation_for_rule(trace, ACHIEVEMENT_CRITERIA_RULE_ID)
        evidence_derivation = derivation_for_rule(trace, EVIDENCE_ARTIFACT_RULE_ID)
        scenario_derivation = derivation_for_rule(trace, SCENARIO_CONTEXT_RULE_ID)

        self.assertIn("obl.req.achievement.criteria", {item["id"] for item in achievement_derivation["missing_obligations"]})
        self.assertIn("obl.req.evidence.artifact", {item["id"] for item in evidence_derivation["missing_obligations"]})
        self.assertIn("obl.req.context.scenario", {item["id"] for item in scenario_derivation["missing_obligations"]})

    def test_rejection_and_observable_rules_derive_when_their_scope_is_present(self) -> None:
        trace = build_request_verification_trace(
            text=(
                "利用者: 管理者。目的: 権限設定を安全に改善する。"
                "受入基準: 管理者以外は設定変更できないことを確認。"
                "検証方法: pytest。証拠: 試験結果。対象外: UI。未確定: なし。"
            ),
            input_kind="requirement",
        )
        payload = trace.as_dict()
        rule_statuses = {rule["rule_id"]: rule["status"] for rule in payload["rules_evaluated"]}

        self.assertEqual(rule_statuses[REJECTION_CONDITION_RULE_ID], "derived")
        self.assertEqual(rule_statuses[OBSERVABLE_BEHAVIOR_RULE_ID], "derived")
        rejection_derivation = derivation_for_rule(trace, REJECTION_CONDITION_RULE_ID)
        observable_derivation = derivation_for_rule(trace, OBSERVABLE_BEHAVIOR_RULE_ID)

        self.assertIn(
            "obl.req.acceptance.rejection_condition",
            {item["id"] for item in rejection_derivation["missing_obligations"]},
        )
        self.assertIn(
            "obl.req.structure.observable_behavior",
            {item["id"] for item in observable_derivation["missing_obligations"]},
        )

    def test_acceptance_missing_trace_keeps_secondary_obligations_without_deriving_target(self) -> None:
        trace = build_acceptance_missing_trace(
            text="目的: 検索を速くする。検証: 動作確認する。対象外: UI。",
            input_kind="requirement",
        )
        payload = trace.as_dict()

        self.assertEqual(payload["rules_evaluated"][0]["status"], "not_derived")
        missing_obligations = {
            obligation["id"] for obligation in payload["obligations"] if obligation["status"] == "missing"
        }
        self.assertIn("obl.req.verifiability.acceptance_criteria", missing_obligations)
        self.assertNotIn("obl.req.verifiability.verification_or_acceptance", missing_obligations)

    def test_acceptance_missing_trace_respects_input_kind_countercondition(self) -> None:
        trace = build_acceptance_missing_trace(text="説明文書です。", input_kind="document")
        payload = trace.as_dict()

        self.assertEqual(payload["rules_evaluated"][0]["status"], "not_applicable")
        self.assertEqual(payload["counterconditions"][0]["status"], "present")
        self.assertEqual(payload["counterconditions"][0]["effect"], "not_applicable")

    def test_derivation_for_rule_is_scoped_and_json_safe(self) -> None:
        trace = build_acceptance_missing_trace(text="目的: 速度改善をしたい。", input_kind="requirement")
        derivation = derivation_for_rule(trace)

        self.assertEqual(derivation["schema_version"], "logical-derivation/v1")
        self.assertEqual(derivation["derivation_scope"], DERIVATION_SCOPE)
        self.assertEqual(derivation["rule_id"], ACCEPTANCE_MISSING_RULE_ID)
        self.assertEqual(derivation["status"], "derived")
        self.assertTrue(derivation["facts_used"])
        self.assertTrue(derivation["counterconditions_checked"])
        self.assertTrue(derivation["missing_obligations"])
        self.assertTrue(derivation["derivation_steps"])
        json.dumps(derivation, ensure_ascii=False, sort_keys=True)

    def test_public_audit_output_emits_scoped_logic_for_migrated_rules_only(self) -> None:
        result = audit_request("目的: 速度改善をしたい。", strict=True)
        target = next(finding for finding in result["findings"] if finding.get("rule_id") == ACCEPTANCE_MISSING_RULE_ID)
        rule_statuses = {rule["rule_id"]: rule["status"] for rule in result["details"]["logical_trace"]["rules_evaluated"]}

        self.assertIn("logical_trace", result["details"])
        self.assertIn("logical_trace_summary", result["details"])
        self.assertEqual(target["derivation"]["rule_id"], ACCEPTANCE_MISSING_RULE_ID)
        self.assertEqual(target["derivation"]["status"], "derived")
        self.assertEqual(result["details"]["logical_trace"]["rules_evaluated"][0]["rule_id"], ACCEPTANCE_MISSING_RULE_ID)
        self.assertEqual(set(rule_statuses), REQUEST_LOGICAL_RULE_IDS)
        self.assertEqual(rule_statuses[METHOD_DETAIL_RULE_ID], "not_applicable")
        self.assertEqual(rule_statuses[OBSERVABLE_BEHAVIOR_RULE_ID], "derived")
        summary = result["details"]["logical_trace_summary"]
        self.assertEqual(summary["schema_version"], "logical-trace-summary/v1")
        self.assertEqual(summary["rule_count"], 7)
        self.assertNotIn("facts", summary)
        summary_by_rule = {rule["rule_id"]: rule for rule in summary["rules"]}
        self.assertEqual(summary_by_rule[ACCEPTANCE_MISSING_RULE_ID]["status"], "derived")
        self.assertEqual(summary_by_rule[ACCEPTANCE_MISSING_RULE_ID]["finding_count"], 1)
        self.assertEqual(summary_by_rule[METHOD_DETAIL_RULE_ID]["status"], "not_applicable")
        self.assertEqual(summary_by_rule[METHOD_DETAIL_RULE_ID]["finding_count"], 0)
        self.assertEqual(summary_by_rule[OBSERVABLE_BEHAVIOR_RULE_ID]["status"], "derived")
        self.assertEqual(summary_by_rule[OBSERVABLE_BEHAVIOR_RULE_ID]["finding_count"], 1)
        for finding in result["findings"]:
            if finding.get("rule_id") not in REQUEST_LOGICAL_RULE_IDS:
                self.assertNotIn("derivation", finding)

    def test_logical_trace_does_not_change_status_or_score(self) -> None:
        result = audit_request(
            "利用者: 運用者。目的: 検索を速くする。"
            "シナリオ: 運用者が検索語を入力した場合、結果一覧が返る。"
            "受入基準: p95 500ms 以下。検証方法: ベンチマーク測定。"
            "証拠: コマンド結果を保存する。不合格条件: p95 が 500ms を超えたら差し戻し。"
            "対象外: UI刷新。未確定: なし。",
            strict=True,
        )

        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["score"], 1.0)
        self.assertIn("logical_trace", result["details"])
        self.assertIn("logical_trace_summary", result["details"])
        trace_statuses = {rule["rule_id"]: rule["status"] for rule in result["details"]["logical_trace"]["rules_evaluated"]}
        summary_statuses = {rule["rule_id"]: rule["status"] for rule in result["details"]["logical_trace_summary"]["rules"]}
        self.assertEqual(trace_statuses[ACCEPTANCE_MISSING_RULE_ID], "satisfied")
        self.assertEqual(trace_statuses[ACHIEVEMENT_CRITERIA_RULE_ID], "satisfied")
        self.assertEqual(trace_statuses[METHOD_DETAIL_RULE_ID], "satisfied")
        self.assertEqual(trace_statuses[EVIDENCE_ARTIFACT_RULE_ID], "satisfied")
        self.assertEqual(trace_statuses[REJECTION_CONDITION_RULE_ID], "satisfied")
        self.assertEqual(trace_statuses[SCENARIO_CONTEXT_RULE_ID], "satisfied")
        self.assertEqual(trace_statuses[OBSERVABLE_BEHAVIOR_RULE_ID], "not_applicable")
        self.assertEqual(summary_statuses, trace_statuses)
        for finding in result["findings"]:
            self.assertNotIn("derivation", finding)


if __name__ == "__main__":
    unittest.main()
