from __future__ import annotations

from semantic_guard.audit_common import _is_bounded_work_package_request, _looks_multi_requirement
from semantic_guard.problem_signals import _problem_mechanism_fit_signal, _symptom_only_success_signal
from semantic_guard.request_signals import (
    _acceptance_criteria_signal,
    _evidence_artifact_signal,
    _expected_result_signal,
    _has_priority_evidence,
    _has_quality_constraint_evidence,
    _has_verification_or_acceptance_language,
    _interface_contract_signal,
    _interface_surface_signal,
    _observable_behavior_signal,
    _precondition_or_trigger_signal,
    _quality_requirement_signal,
    _rejection_condition_signal,
    _requires_expected_result,
    _requires_precondition_or_trigger,
    _requires_rejection_condition,
    _requires_scenario_context,
    _scenario_context_signal,
    _stakeholder_source_signal,
    _unclassified_uncertainty_signal,
    _vague_behavior_signal,
    _verification_method_signal,
)
from semantic_guard.text_utils import first_match as _first_match

def _requirement_achievement_profile(text: str) -> dict[str, str]:
    if not text.strip():
        return {
            "acceptance_criteria": "",
            "verification_method": "",
            "evidence_artifact": "",
            "acceptance_owner": "",
            "rejection_condition": "",
            "scenario_context": "",
        }

    return {
        "acceptance_criteria": _acceptance_criteria_signal(text),
        "verification_method": _verification_method_signal(text),
        "evidence_artifact": _evidence_artifact_signal(text),
        "acceptance_owner": _stakeholder_source_signal(text),
        "rejection_condition": _rejection_condition_signal(text),
        "scenario_context": _scenario_context_signal(text),
    }


def _requirement_structure_profile(text: str) -> dict[str, str]:
    if not text.strip():
        return {
            "observable_behavior": "",
            "precondition_or_trigger": "",
            "expected_result": "",
            "interface_contract": "",
        }

    return {
        "observable_behavior": _observable_behavior_signal(text),
        "precondition_or_trigger": _precondition_or_trigger_signal(text),
        "expected_result": _expected_result_signal(text),
        "interface_contract": _interface_contract_signal(text),
    }


def _requirement_quality_signals(
    text: str,
    combined: str,
    profile: dict[str, str],
    structure: dict[str, str],
) -> dict[str, str]:
    if not text.strip():
        return {}

    signals: dict[str, str] = {}
    stakeholder_source = _stakeholder_source_signal(combined)
    if not stakeholder_source:
        signals["stakeholder_source"] = ""

    quality_claim = _quality_requirement_signal(combined)
    if quality_claim and not _has_quality_constraint_evidence(combined):
        signals["quality_constraint"] = quality_claim

    if _looks_multi_requirement(text) and not _has_priority_evidence(combined) and not _is_bounded_work_package_request(text, combined):
        signals["priority"] = _first_match(text, [" and ", " or ", "かつ", "または", "及び", "および", "、"])

    uncertainty = _unclassified_uncertainty_signal(combined)
    if uncertainty:
        signals["uncertainty_classification"] = uncertainty

    problem_mechanism_gap = _problem_mechanism_fit_signal(combined)
    if problem_mechanism_gap:
        signals["problem_mechanism_fit"] = problem_mechanism_gap

    symptom_only_success = _symptom_only_success_signal(combined)
    if symptom_only_success:
        signals["symptom_only_success"] = symptom_only_success

    if _has_verification_or_acceptance_language(combined) and not profile["acceptance_criteria"]:
        signals["achievement_criteria"] = _first_match(
            combined,
            ["検証", "確認", "受入", "acceptance", "verify", "test", "evidence"],
        )

    if _has_verification_or_acceptance_language(combined) and not profile["verification_method"]:
        signals["verification_method_detail"] = _first_match(
            combined,
            ["検証", "確認", "試験", "テスト", "acceptance", "verify", "test"],
        )

    if (
        profile["acceptance_criteria"]
        or profile["verification_method"]
        or _has_verification_or_acceptance_language(combined)
    ) and not profile["evidence_artifact"]:
        signals["evidence_artifact"] = profile["acceptance_criteria"] or profile["verification_method"]

    if _requires_rejection_condition(combined) and not profile["rejection_condition"]:
        signals["rejection_condition"] = _first_match(
            combined,
            ["安全", "権限", "削除", "移行", "公開", "運用", "認証", "認可", "security", "permission", "delete", "migration"],
        )

    if _requires_scenario_context(combined) and not profile["scenario_context"]:
        signals["scenario_context"] = _first_match(
            combined,
            ["画面", "ユーザー", "利用者", "入力", "操作", "通知", "表示", "検索", "UI", "user", "screen", "input"],
        )

    vague_behavior = _vague_behavior_signal(combined)
    if vague_behavior and not structure["observable_behavior"]:
        signals["observable_behavior"] = vague_behavior

    if _requires_precondition_or_trigger(combined) and not structure["precondition_or_trigger"]:
        signals["precondition_or_trigger"] = _first_match(
            combined,
            ["画面", "UI", "ユーザー", "利用者", "入力", "操作", "検索", "通知", "API", "CLI", "JSON", "user", "input"],
        )

    if _requires_expected_result(combined) and not structure["expected_result"]:
        signals["expected_result"] = _first_match(
            combined,
            ["入力", "操作", "検索", "表示", "通知", "API", "CLI", "JSON", "output", "return", "screen"],
        )

    interface_surface = _interface_surface_signal(combined)
    if interface_surface and not structure["interface_contract"]:
        signals["interface_contract"] = interface_surface

    return signals
