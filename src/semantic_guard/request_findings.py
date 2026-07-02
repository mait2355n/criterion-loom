from __future__ import annotations

from semantic_guard.audit_common import BASIS
from semantic_guard.field_detection import missing_field_finding as _missing_field_finding
from semantic_guard.logic import (
    ACHIEVEMENT_CRITERIA_RULE_ID,
    EVIDENCE_ARTIFACT_RULE_ID,
    METHOD_DETAIL_RULE_ID,
    OBSERVABLE_BEHAVIOR_RULE_ID,
    REJECTION_CONDITION_RULE_ID,
    SCENARIO_CONTEXT_RULE_ID,
)
from semantic_guard.models import Finding
from semantic_guard.request_signals import STAKEHOLDER_SOURCE_TERMS

def _add_requirement_quality_findings(
    signals: dict[str, str],
    findings: list[Finding],
    missing: list[str],
    strict: bool,
    *,
    achievement_criteria_derivation: dict[str, object],
    method_detail_derivation: dict[str, object],
    evidence_artifact_derivation: dict[str, object],
    rejection_condition_derivation: dict[str, object],
    scenario_context_derivation: dict[str, object],
    observable_behavior_derivation: dict[str, object],
) -> None:
    if "stakeholder_source" in signals:
        findings.append(
            _missing_field_finding(
                field="stakeholder_source",
                patterns=STAKEHOLDER_SOURCE_TERMS,
                text="",
                severity="major" if strict else "minor",
                category="stakeholder",
                basis=BASIS["requirements"],
                finding="要求の利害関係者または出所が見えない。",
                suggested_fix="誰の要求か、誰が使うか、誰が受け入れるか、または出所が不要な理由を明示する。",
            )
        )
        missing.append("stakeholder_source")

    if "quality_constraint" in signals:
        findings.append(
            Finding(
                severity="major" if strict else "minor",
                category="quality",
                basis=BASIS["requirements"] + BASIS["implementation"],
                finding="品質要求らしき記述があるが、測定条件や受入基準が薄い。",
                evidence=signals["quality_constraint"],
                suggested_fix="性能、信頼性、安全性、使いやすさなどを、閾値、測定方法、受入基準、判断主体へ落とす。",
                warning_class="generic caution",
            )
        )
        missing.append("quality_constraint")

    if "priority" in signals:
        findings.append(
            Finding(
                severity="minor",
                category="priority",
                basis=BASIS["requirements"] + BASIS["planning"],
                finding="複数要求らしき入力に優先度または実施順序が見えない。",
                evidence=signals["priority"],
                suggested_fix="必須/任意、先にやる/後でやる、採用/保留などの優先度を分ける。",
            )
        )
        missing.append("priority")

    if "uncertainty_classification" in signals:
        findings.append(
            Finding(
                severity="minor",
                category="unknowns",
                basis=BASIS["requirements"] + BASIS["meaning"],
                finding="不確実な表現があるが、未確定、仮説、判断待ちなどの扱いが分かれていない。",
                evidence=signals["uncertainty_classification"],
                suggested_fix="推測を要求に混ぜず、未確定、仮説、判断待ち、片側観測、時点差のいずれかへ分類する。",
            )
        )
        missing.append("uncertainty_classification")

    if "problem_mechanism_fit" in signals:
        finding = Finding(
            severity="major" if strict else "minor",
            category="solution_fit",
            basis=BASIS["requirements"] + BASIS["meaning"],
            finding="解決策が問題の原因構造または発生機構へどう作用するかが見えない。",
            evidence=signals["problem_mechanism_fit"],
            suggested_fix="観測症状、原因仮説、発生条件、制約、解決策が効く理由、または調査で確かめる項目を分けて明示する。",
            warning_class="generic caution",
            needs_human_decision=True,
        )
        finding.rule_id = "req.solution.problem_mechanism_fit_missing"
        findings.append(finding)
        missing.append("problem_mechanism_fit")

    if "symptom_only_success" in signals:
        finding = Finding(
            severity="major" if strict else "minor",
            category="acceptance",
            basis=BASIS["requirements"] + BASIS["meaning"],
            finding="受入条件が観測症状の消失だけに寄っている。",
            evidence=signals["symptom_only_success"],
            suggested_fix="症状が出ないことだけでなく、原因または制約が解けた証拠、目的達成、異常時挙動、差し戻し条件を足す。",
            warning_class="generic caution",
            needs_human_decision=True,
        )
        finding.rule_id = "req.acceptance.symptom_only_success_criteria"
        findings.append(finding)
        missing.append("symptom_only_success_criteria")

    if "achievement_criteria" in signals:
        finding = Finding(
            severity="major" if strict else "minor",
            category="acceptance",
            basis=BASIS["requirements"],
            finding="要求が何を以て達成されたと言えるかが薄い。",
            evidence=signals["achievement_criteria"],
            suggested_fix="受入基準、合格条件、完了条件、成功状態、または Definition of Done を明示する。",
        )
        finding.rule_id = ACHIEVEMENT_CRITERIA_RULE_ID
        finding.derivation = achievement_criteria_derivation
        findings.append(finding)
        missing.append("achievement_criteria")

    if "verification_method_detail" in signals:
        finding = Finding(
            severity="major" if strict else "minor",
            category="verification",
            basis=BASIS["requirements"],
            finding="検証または確認の方法が具体化されていない。",
            evidence=signals["verification_method_detail"],
            suggested_fix="試験、解析、検査、実演、測定、レビュー、代表 CLI 実行など、どの方法で確かめるかを明示する。",
        )
        finding.rule_id = METHOD_DETAIL_RULE_ID
        finding.derivation = method_detail_derivation
        findings.append(finding)
        missing.append("verification_method_detail")

    if "evidence_artifact" in signals:
        finding = Finding(
            severity="minor",
            category="evidence",
            basis=BASIS["requirements"],
            finding="達成確認に使う証拠成果物が見えない。",
            evidence=signals["evidence_artifact"],
            suggested_fix="コマンド結果、試験結果、ログ、スクリーンショット、出力 JSON、レビュー記録など、残す証拠を明示する。",
        )
        finding.rule_id = EVIDENCE_ARTIFACT_RULE_ID
        finding.derivation = evidence_artifact_derivation
        findings.append(finding)
        missing.append("evidence_artifact")

    if "rejection_condition" in signals:
        finding = Finding(
            severity="minor",
            category="acceptance",
            basis=BASIS["requirements"] + BASIS["planning"],
            finding="不合格、棄却、戻しが必要になる条件が見えない。",
            evidence=signals["rejection_condition"],
            suggested_fix="どの結果なら未達、差し戻し、保留、または rollback とするかを明示する。",
            warning_class="generic caution",
        )
        finding.rule_id = REJECTION_CONDITION_RULE_ID
        finding.derivation = rejection_condition_derivation
        findings.append(finding)
        missing.append("rejection_condition")

    if "scenario_context" in signals:
        finding = Finding(
            severity="minor",
            category="scenario",
            basis=BASIS["requirements"] + BASIS["meaning"],
            finding="利用場面、入力条件、操作文脈が見えない。",
            evidence=signals["scenario_context"],
            suggested_fix="誰が、どの状態で、何を入力または操作し、何が返ればよいかを短いシナリオで明示する。",
        )
        finding.rule_id = SCENARIO_CONTEXT_RULE_ID
        finding.derivation = scenario_context_derivation
        findings.append(finding)
        missing.append("scenario_context")

    if "observable_behavior" in signals:
        finding = Finding(
            severity="major" if strict else "minor",
            category="behavior",
            basis=BASIS["requirements"],
            finding="要求が観測可能な振る舞いへ落ちていない。",
            evidence=signals["observable_behavior"],
            suggested_fix="誰または何が、どの操作や入力に対して、何を返す、保存する、表示する、拒否する、通知するのかを明示する。",
        )
        finding.rule_id = OBSERVABLE_BEHAVIOR_RULE_ID
        finding.derivation = observable_behavior_derivation
        findings.append(finding)
        missing.append("observable_behavior")

    if "precondition_or_trigger" in signals:
        findings.append(
            Finding(
                severity="minor",
                category="scenario",
                basis=BASIS["requirements"] + BASIS["meaning"],
                finding="要求が満たされる前提条件または発火条件が見えない。",
                evidence=signals["precondition_or_trigger"],
                suggested_fix="Given/When、前提状態、入力条件、操作、発火条件、対象データを明示する。",
            )
        )
        missing.append("precondition_or_trigger")

    if "expected_result" in signals:
        findings.append(
            Finding(
                severity="minor",
                category="acceptance",
                basis=BASIS["requirements"],
                finding="操作や入力に対する期待結果が見えない。",
                evidence=signals["expected_result"],
                suggested_fix="期待する出力、表示、状態変化、エラー、拒否、通知、保存結果を明示する。",
            )
        )
        missing.append("expected_result")

    if "interface_contract" in signals:
        findings.append(
            Finding(
                severity="minor",
                category="interface",
                basis=BASIS["requirements"] + BASIS["implementation"],
                finding="入出力または公開面に触れているが、契約の項目が薄い。",
                evidence=signals["interface_contract"],
                suggested_fix="入力項目、出力項目、形式、状態コード、エラー、既定値、例、schema のいずれかを明示する。",
                warning_class="generic caution",
            )
        )
        missing.append("interface_contract")
