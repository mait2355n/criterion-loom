from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from semantic_guard.resources import resource_path

SCHEMA_VERSION = "request-exploration-review/v1"
EXPLORATION_STATUSES = {"complete", "blocked_by_missing_context"}
INFORMATION_STATUSES = {"fact", "inference", "hypothesis", "unknown", "pending_decision"}
CONFIDENCE_LEVELS = {"low", "medium", "high"}
SEVERITIES = {"blocker", "major", "minor", "info"}
QUESTION_PRIORITIES = {"must_ask", "ask_if_time", "defer"}
SCHEMA_FILE = resource_path("schemas", "request-exploration-review.schema.json")


@dataclass(frozen=True)
class RequestExplorationInput:
    text: str
    context: str = ""
    deterministic_exploration: Mapping[str, Any] | None = None
    constraints: str = ""
    non_goals: str = ""
    known_sources: str = ""

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "RequestExplorationInput":
        return cls(
            text=_required_string(payload, "text"),
            context=_optional_string(payload, "context"),
            deterministic_exploration=_optional_mapping(payload, "deterministic_exploration"),
            constraints=_optional_string(payload, "constraints"),
            non_goals=_optional_string(payload, "non_goals"),
            known_sources=_optional_string(payload, "known_sources"),
        )

    def as_prompt_payload(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "context": self.context,
            "deterministic_exploration": dict(self.deterministic_exploration or {}),
            "constraints": self.constraints,
            "non_goals": self.non_goals,
            "known_sources": self.known_sources,
        }


def request_exploration_review_schema_path() -> Path:
    return SCHEMA_FILE


def load_request_exploration_review_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_FILE.read_text(encoding="utf-8"))


def build_request_exploration_prompt(exploration_input: RequestExplorationInput, *, include_schema: bool = False) -> str:
    payload = json.dumps(exploration_input.as_prompt_payload(), ensure_ascii=False, indent=2, sort_keys=True)
    sections = [
        "# request_exploration_interviewer",
        "",
        "アナタは仕様化前の探索査読者である。",
        "入力と文脈から取れる情報をすべて拾い、事実・推測・仮説・不明・人間判断待ちを分けた上で、欠けている重要情報をすべて問いただす。",
        "ただし、好み、言い回し、実装方式の嗜好だけを問う質問は出さない。範囲、資料模型、本人性、秘匿性、権限、支払、外部権威、受入証拠、失敗条件、人間判断点を変える質問だけを残す。",
        "",
        "## Role Boundary",
        "",
        "- 対象利用者、主要導線、資料模型、状態、識別子、秘匿性、権限、外部連携、受入基準、非目標、未確定事項を重点的に見る。",
        "- 明示されていることは `extracted_information` に `status: fact` として残す。",
        "- 文脈から読めるが確定ではないものは `status: inference` または `hypothesis` として残す。",
        "- 分からないこと、決める必要があることは `unknown` または `pending_decision` として残す。",
        "- 質問は漏らさず出す。ただし同じ判断点を聞く重複質問は統合する。",
        "- `must_ask` は答えが無いと仕様や実装計画が危険な質問に限る。",
        "- `ask_if_time` は仕様の品質や利用体験を改善するが、保守的仮定で一旦進められる質問に使う。",
        "- `defer` は後続設計や実装前でよい質問に使う。",
        "- 仕様、実装計画、承認、棄却、最終受入判断をしてはならない。",
        "- 判断材料が入力にも文脈にも無さすぎる場合は `exploration_status` を `blocked_by_missing_context` にする。",
        "",
        "## Required Output",
        "",
        "JSONだけを返す。Markdown、説明文、コードブロックを返してはならない。",
        f"`schema_version` は `{SCHEMA_VERSION}` にする。",
        "schema内のobject propertiesはすべて出力する。該当なしは空配列、空文字列、または最も近い enum を使う。",
        "",
        "## Exploration Input",
        "",
        "```json",
        payload,
        "```",
    ]
    if include_schema:
        schema = json.dumps(load_request_exploration_review_schema(), ensure_ascii=False, indent=2, sort_keys=True)
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


def validate_request_exploration_review(payload: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    allowed = {
        "schema_version",
        "exploration_status",
        "extracted_information",
        "audience_hypotheses",
        "material_ambiguities",
        "questions",
        "spec_outline",
        "non_decisions",
        "limits",
    }
    for key in sorted(allowed):
        if key not in payload:
            errors.append(f"missing required field: {key}")
    for key in sorted(set(payload) - allowed):
        errors.append(f"unexpected field: {key}")

    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION!r}")
    if payload.get("exploration_status") not in EXPLORATION_STATUSES:
        errors.append("exploration_status must be one of complete, blocked_by_missing_context")

    _validate_object_array(
        errors,
        payload,
        "extracted_information",
        required_fields=("kind", "content", "source", "status", "confidence"),
        enum_fields={"status": INFORMATION_STATUSES, "confidence": CONFIDENCE_LEVELS},
    )
    _validate_object_array(
        errors,
        payload,
        "audience_hypotheses",
        required_fields=("id", "label", "evidence", "scope_implications", "confidence"),
        enum_fields={"confidence": CONFIDENCE_LEVELS},
        list_fields=("scope_implications",),
    )
    _validate_object_array(
        errors,
        payload,
        "material_ambiguities",
        required_fields=(
            "id",
            "category",
            "severity",
            "known_information",
            "missing_information",
            "why_material",
            "affects",
            "evidence",
            "question",
            "answer_shape",
        ),
        enum_fields={"severity": SEVERITIES},
        list_fields=("known_information", "missing_information", "affects"),
    )
    _validate_object_array(
        errors,
        payload,
        "questions",
        required_fields=("id", "question", "why", "affects", "answer_shape", "priority"),
        enum_fields={"priority": QUESTION_PRIORITIES},
        list_fields=("affects",),
    )
    _validate_object_array(
        errors,
        payload,
        "spec_outline",
        required_fields=("id", "title", "known", "missing", "required"),
        list_fields=("known", "missing"),
        boolean_fields=("required",),
    )
    _validate_string_array(errors, payload, "non_decisions")
    _validate_string_array(errors, payload, "limits")
    return errors


def _validate_object_array(
    errors: list[str],
    payload: Mapping[str, Any],
    key: str,
    *,
    required_fields: tuple[str, ...],
    enum_fields: Mapping[str, set[str]] | None = None,
    list_fields: tuple[str, ...] = (),
    boolean_fields: tuple[str, ...] = (),
) -> None:
    value = payload.get(key)
    if not isinstance(value, list):
        errors.append(f"{key} must be an array")
        return
    enum_fields = enum_fields or {}
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            errors.append(f"{key}[{index}] must be an object")
            continue
        for field_name in required_fields:
            if field_name not in item:
                errors.append(f"{key}[{index}] missing required field: {field_name}")
        for field_name, allowed_values in enum_fields.items():
            if field_name in item and item.get(field_name) not in allowed_values:
                errors.append(f"{key}[{index}].{field_name} has invalid value")
        for field_name in list_fields:
            if field_name in item and not _is_string_array(item.get(field_name)):
                errors.append(f"{key}[{index}].{field_name} must be an array of strings")
        for field_name in boolean_fields:
            if field_name in item and not isinstance(item.get(field_name), bool):
                errors.append(f"{key}[{index}].{field_name} must be a boolean")


def _validate_string_array(errors: list[str], payload: Mapping[str, Any], key: str) -> None:
    if not _is_string_array(payload.get(key)):
        errors.append(f"{key} must be an array of strings")


def _is_string_array(value: object) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


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


def _optional_mapping(payload: Mapping[str, Any], key: str) -> Mapping[str, Any] | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise ValueError(f"`{key}` must be an object")
    return value
