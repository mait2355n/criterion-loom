from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from semantic_guard.resources import resource_path
from semantic_guard.rules import get_rule, rules_for_phase

SCHEMA_VERSION = "candidate-gap-review/v2"
REVIEW_STATUSES = {"no_supplement_needed", "needs_supplement", "blocked_by_missing_context"}
SEVERITIES = {"blocker", "major", "minor", "info"}
CONFIDENCE_LEVELS = {"low", "medium", "high"}
SCHEMA_FILE = resource_path("schemas", "candidate-gap-review.schema.json")

PHASE_REVIEW_GUIDANCE: dict[str, dict[str, object]] = {
    "understand_target": {
        "knowledge_area": "requirements engineering and problem framing",
        "engineering_basis": ["ISO/IEC/IEEE 29148", "BABOK", "NASA SEH", "semantic-implementation"],
        "inspect": [
            "subject identity: name, entity, display, identifier, and storage are separated",
            "stakeholders: user, maintainer, operator, author, reader, or affected system",
            "current state and desired state",
            "purpose, intent, value, and validation route",
            "constraints, non-goals, assumptions, unknowns, and conflicts",
        ],
    },
    "audit_request": {
        "knowledge_area": "requirements engineering",
        "engineering_basis": ["ISO/IEC/IEEE 29148", "BABOK", "NASA SEH"],
        "inspect": [
            "classification: purpose, stakeholder, solution, transition, quality, operation, or non-requirement",
            "necessity, atomicity, clarity, modality, and solution bias",
            "problem-solution fit: whether the candidate explains the cause, mechanism, constraint, or responsibility structure it changes rather than only suppressing an observed symptom",
            "feasibility, verifiability, acceptance criteria, and traceability",
            "acceptance depth: whether success criteria measure purpose and mechanism fit, not only that an error, warning, stop, refusal, or delay disappeared",
            "scope boundary: in-scope, out-of-scope, assumptions, and constraints",
            "conflict, priority, change state, and validation readiness",
        ],
    },
    "audit_plan": {
        "knowledge_area": "project planning and technical planning",
        "engineering_basis": ["PMBOK", "ISO 21502", "NASA SEH"],
        "inspect": [
            "objective fit and value delivery",
            "scope control, non-goals, deliverables, and work breakdown",
            "dependency order, assumption checks, decision points, and change control",
            "solution-risk transfer: whether the plan checks where load, hazard, cost, responsibility, or failure modes move after the solution",
            "risk register, mitigation, fallback, rollback, and recovery",
            "verification plan, validation plan, and completion evidence",
        ],
    },
    "audit_diff": {
        "knowledge_area": "software engineering, secure development, and semantic preservation",
        "engineering_basis": ["ISO/IEC/IEEE 12207", "SWEBOK", "ISO/IEC 25010", "NIST SSDF", "OWASP", "CWE"],
        "inspect": [
            "intent trace from material changes to request or plan",
            "design fit, responsibility boundaries, API/data compatibility, and operation risk",
            "meaning preservation: name, identity, display, identifier, storage, membership, hypothesis, and fact",
            "quality delta: reliability, maintainability, compatibility, performance, portability, and complexity",
            "security delta, test obligation, doc obligation, and reviewability",
        ],
    },
    "finish_check": {
        "knowledge_area": "verification, validation, release readiness, and evidence review",
        "engineering_basis": ["ISO/IEC/IEEE 29148", "ISO/IEC/IEEE 12207", "SWEBOK", "PMBOK"],
        "inspect": [
            "tests ran, tests not ran, and reasons",
            "acceptance evidence mapped to requirements or purpose",
            "security evidence, regression scope, and documentation sync",
            "breaking changes, migration needs, release blockers, and residual risk",
            "no meaningful completion claim without artifact, command, line reference, result, or stated non-applicability",
        ],
    },
}

GENERIC_REVIEW_GUIDANCE = {
    "knowledge_area": "meaning-oriented engineering review",
    "engineering_basis": ["semantic-implementation"],
    "inspect": [
        "purpose, scope, non-goals, assumptions, unknowns, evidence, and residual risk",
        "whether candidate gaps should be supplemented before final human review",
    ],
}


@dataclass(frozen=True)
class CandidateGapReviewInput:
    candidate: str
    request: str = ""
    deterministic_audit: Mapping[str, Any] | None = None
    related_rules: tuple[Mapping[str, Any], ...] = field(default_factory=tuple)
    constraints: str = ""
    non_goals: str = ""
    unknowns: str = ""
    context: str = ""
    review_context: Mapping[str, Any] | None = None
    routing_assessment: Mapping[str, Any] | None = None
    phase: str = ""

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "CandidateGapReviewInput":
        candidate = _required_string(payload, "candidate")
        related_rules = payload.get("related_rules")
        if related_rules is None:
            related_rules = _rules_from_ids_or_phase(payload.get("rule_ids", ()), payload.get("phase", ""))
        return cls(
            candidate=candidate,
            request=_optional_string(payload, "request"),
            deterministic_audit=_optional_mapping(payload, "deterministic_audit", "audit_result"),
            related_rules=_tuple_of_mappings(related_rules, "related_rules"),
            constraints=_optional_string(payload, "constraints"),
            non_goals=_optional_string(payload, "non_goals"),
            unknowns=_optional_string(payload, "unknowns"),
            context=_optional_string(payload, "context"),
            review_context=_optional_mapping(payload, "review_context", "routing_context"),
            routing_assessment=_optional_mapping(payload, "routing_assessment"),
            phase=_optional_string(payload, "phase"),
        )

    def as_prompt_payload(self) -> dict[str, Any]:
        return {
            "candidate": self.candidate,
            "request": self.request,
            "deterministic_audit": dict(self.deterministic_audit or {}),
            "related_rules": [dict(rule) for rule in self.related_rules],
            "phase_guidance": review_guidance_for_phase(self.phase),
            "constraints": self.constraints,
            "non_goals": self.non_goals,
            "unknowns": self.unknowns,
            "context": self.context,
            "review_context": dict(self.review_context or {}),
            "routing_assessment": dict(self.routing_assessment or {}),
            "phase": self.phase,
        }


def candidate_gap_review_schema_path() -> Path:
    return SCHEMA_FILE


def load_candidate_gap_review_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_FILE.read_text(encoding="utf-8"))


def review_guidance_for_phase(phase: str) -> dict[str, object]:
    normalized = (phase or "").strip().replace("-", "_")
    return dict(PHASE_REVIEW_GUIDANCE.get(normalized, GENERIC_REVIEW_GUIDANCE))


def build_candidate_gap_review_prompt(review_input: CandidateGapReviewInput, *, include_schema: bool = False) -> str:
    payload = json.dumps(review_input.as_prompt_payload(), ensure_ascii=False, indent=2, sort_keys=True)
    sections = [
        "# candidate_gap_reviewer",
        "",
        "アナタは候補案の不足を指摘し、補填案を出す隔離査読者である。",
        "合否判定、承認、却下、実装変更、警告の無視判断をしてはならない。",
        "",
        "## Role Boundary",
        "",
        "- deterministic監査結果の警告が過剰かもしれない場合は、`possible_counter_conditions` に書く。",
        "- 見逃し、薄い前提、検証不足、受入不足、対象外不足、証拠不足は `missing_aspects` に書く。",
        "- phase_guidance の `knowledge_area`, `engineering_basis`, `inspect` を使い、段階に応じた工学知識で候補を見る。",
        "- related_rules がある場合は、各ruleの concern, applies_when, does_not_apply_when, evidence_required, severity_policy, finding, remediation を項目ごとに見て `rule_item_reviews` に書く。",
        "- 補うべき文、条件、証拠、計画項目は `supplement_proposals` に書く。",
        "- 人間判断が必要な点だけ `human_decision_needed` に書く。",
        "- これは最終人間監査へ至る途中監査であり、人の最終評価用に不足と補填候補を整える。",
        "- 判断材料が足りない場合は `review_status` を `blocked_by_missing_context` にする。",
        "- 問題が見つからない場合も、承認ではなく `no_supplement_needed` として出力する。",
        "- routing_assessment.pressure.score は査読経路圧であり、候補案の正しさ確率ではない。",
        "- review_context が fresh-eyes / independent review を求めている場合は、親文脈に染まっていない別視点で見落とし候補を探す。",
        "",
        "## Required Output",
        "",
        "JSONだけを返す。Markdown、説明文、コードブロックを返してはならない。",
        f"`schema_version` は `{SCHEMA_VERSION}` にする。",
        "出力項目は schema にあるものだけを使う。",
        "schema内のobject propertiesはすべて出力する。該当なしは空配列または `なし` と書く。",
        "",
        "## Review Input",
        "",
        "```json",
        payload,
        "```",
    ]
    if include_schema:
        schema = json.dumps(load_candidate_gap_review_schema(), ensure_ascii=False, indent=2, sort_keys=True)
        sections.extend(
            [
                "",
                "## Output Schema",
                "",
                "```json",
                schema,
                "```",
            ]
        )
    return "\n".join(sections)


def validate_candidate_gap_review(payload: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    allowed = {
        "schema_version",
        "review_status",
        "missing_aspects",
        "questionable_assumptions",
        "possible_counter_conditions",
        "supplement_proposals",
        "human_decision_needed",
        "rule_item_reviews",
    }
    required = allowed

    for key in sorted(required):
        if key not in payload:
            errors.append(f"missing required field: {key}")
    for key in sorted(set(payload) - allowed):
        errors.append(f"unexpected field: {key}")

    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION!r}")
    if payload.get("review_status") not in REVIEW_STATUSES:
        errors.append("review_status must be one of no_supplement_needed, needs_supplement, blocked_by_missing_context")

    _validate_object_array(
        errors,
        payload,
        "missing_aspects",
        required_fields=("kind", "severity", "why_it_matters", "supplement"),
        enum_fields={"severity": SEVERITIES},
    )
    _validate_object_array(
        errors,
        payload,
        "questionable_assumptions",
        required_fields=("assumption", "risk", "supplement"),
    )
    _validate_object_array(
        errors,
        payload,
        "possible_counter_conditions",
        required_fields=("rule_id", "does_not_apply_when", "confidence", "reason"),
        enum_fields={"confidence": CONFIDENCE_LEVELS},
    )
    _validate_object_array(
        errors,
        payload,
        "supplement_proposals",
        required_fields=("target", "proposal", "reason"),
    )
    _validate_object_array(
        errors,
        payload,
        "rule_item_reviews",
        required_fields=("rule_id", "inspected_items", "missing_items", "supplement", "notes"),
        list_fields=("inspected_items", "missing_items", "counter_condition_candidates"),
    )
    _validate_string_array(errors, payload, "human_decision_needed")
    return errors


def _required_string(payload: Mapping[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"`{key}` must be a non-empty string")
    return value


def _optional_string(payload: Mapping[str, Any], key: str) -> str:
    value = payload.get(key, "")
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError(f"`{key}` must be a string")
    return value


def _optional_mapping(payload: Mapping[str, Any], *keys: str) -> Mapping[str, Any] | None:
    for key in keys:
        if key in payload and payload[key] is not None:
            value = payload[key]
            if not isinstance(value, Mapping):
                raise ValueError(f"`{key}` must be an object")
            return value
    return None


def _tuple_of_mappings(value: Any, key: str) -> tuple[Mapping[str, Any], ...]:
    if value is None:
        return ()
    if not isinstance(value, list | tuple):
        raise ValueError(f"`{key}` must be an array")
    result: list[Mapping[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            raise ValueError(f"`{key}[{index}]` must be an object")
        result.append(item)
    return tuple(result)


def _rules_from_ids_or_phase(rule_ids: Any, phase: Any) -> tuple[Mapping[str, Any], ...]:
    if not rule_ids:
        normalized_phase = str(phase or "").strip().replace("-", "_")
        if not normalized_phase:
            return ()
        return tuple(rule.as_dict() for rule in rules_for_phase(normalized_phase))  # type: ignore[arg-type]
    if not isinstance(rule_ids, list | tuple):
        raise ValueError("`rule_ids` must be an array")
    return tuple(get_rule(str(rule_id)).as_dict() for rule_id in rule_ids)


def _validate_object_array(
    errors: list[str],
    payload: Mapping[str, Any],
    key: str,
    *,
    required_fields: tuple[str, ...],
    optional_fields: tuple[str, ...] = (),
    list_fields: tuple[str, ...] = (),
    optional_list_fields: tuple[str, ...] = (),
    enum_fields: Mapping[str, set[str]] | None = None,
) -> None:
    value = payload.get(key)
    if not isinstance(value, list):
        errors.append(f"{key} must be an array")
        return
    allowed = set(required_fields) | set(optional_fields) | set(list_fields) | set(optional_list_fields)
    enum_fields = enum_fields or {}
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            errors.append(f"{key}[{index}] must be an object")
            continue
        for field_name in required_fields:
            if field_name in list_fields:
                continue
            field_value = item.get(field_name)
            if not isinstance(field_value, str) or not field_value.strip():
                errors.append(f"{key}[{index}].{field_name} must be a non-empty string")
        for field_name in list_fields:
            field_value = item.get(field_name)
            if not isinstance(field_value, list):
                errors.append(f"{key}[{index}].{field_name} must be an array")
                continue
            if any(not isinstance(entry, str) or not entry.strip() for entry in field_value):
                errors.append(f"{key}[{index}].{field_name} must contain only non-empty strings")
        for field_name in optional_list_fields:
            if field_name not in item:
                continue
            field_value = item.get(field_name)
            if not isinstance(field_value, list):
                errors.append(f"{key}[{index}].{field_name} must be an array")
                continue
            if any(not isinstance(entry, str) or not entry.strip() for entry in field_value):
                errors.append(f"{key}[{index}].{field_name} must contain only non-empty strings")
        for field_name in sorted(set(item) - allowed):
            errors.append(f"{key}[{index}] has unexpected field: {field_name}")
        for field_name, allowed_values in enum_fields.items():
            if item.get(field_name) not in allowed_values:
                errors.append(f"{key}[{index}].{field_name} must be one of {sorted(allowed_values)}")


def _validate_string_array(errors: list[str], payload: Mapping[str, Any], key: str) -> None:
    value = payload.get(key)
    if not isinstance(value, list):
        errors.append(f"{key} must be an array")
        return
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            errors.append(f"{key}[{index}] must be a non-empty string")
