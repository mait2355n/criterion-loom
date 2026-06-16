from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable

MATCH_STATUSES = {"matched", "partial", "rejected", "missing", "not_applicable", "unknown"}
CONFIDENCES = {"high", "medium", "low"}


@dataclass(frozen=True)
class FieldMatchDiagnostic:
    field: str
    match_status: str
    confidence: str
    ambiguity_reasons: list[str] = field(default_factory=list)
    candidate_matches: list[dict[str, object]] = field(default_factory=list)

    @property
    def nearest_candidates(self) -> list[str]:
        return [str(candidate["text"]) for candidate in self.candidate_matches if candidate.get("text")]


STRONG_FIELD_ALIASES: dict[str, list[str]] = {
    "objective": ["objective", "goal", "purpose", "desired outcome"],
    "purpose_trace": ["purpose", "value", "reason", "why"],
    "non_goals": ["non-goals", "non goals", "non-requirements", "out of scope"],
    "non_requirements": ["non-goals", "non goals", "non-requirements", "out of scope"],
    "deliverables": ["deliverables", "artifacts", "outputs"],
    "work_breakdown": [
        "work breakdown",
        "work-package decomposition",
        "work package decomposition",
        "work packages",
        "work package",
        "implementation plan",
        "implementation steps",
    ],
    "work_package_decomposition": [
        "work breakdown",
        "work-package decomposition",
        "work package decomposition",
        "work packages",
        "work package",
    ],
    "dependencies": ["dependencies", "dependency sequence", "dependency order", "prerequisites"],
    "dependency_sequence": ["dependency sequence", "dependency order", "predecessor", "successor", "critical path"],
    "risks": ["risks", "risk response", "risk and response", "risks and responses"],
    "risk_response": ["risk response", "risks and responses", "mitigation", "contingency"],
    "verification_plan": ["verification", "verification plan", "test plan", "tests"],
    "verification_or_acceptance": ["verification", "acceptance", "test evidence"],
    "validation_plan": ["validation", "acceptance criteria", "acceptance"],
    "rollback_or_recovery": ["rollback", "recovery", "rollback or recovery", "revert"],
    "completion_evidence": ["completion evidence", "evidence", "proof"],
    "unknowns_or_decisions": ["open decisions", "unknowns", "pending decisions"],
    "unknowns": ["open decisions", "unknowns", "pending decisions"],
    "validation_owner": ["validation owner", "acceptance owner", "approver", "reviewer"],
    "progress_control": ["progress control", "milestone", "status report"],
    "change_control": ["change control", "scope change", "change request"],
    "control_baseline": ["control baseline", "baseline", "metric", "milestone"],
    "decision_gate": ["decision gate", "go/no-go", "approval", "stop condition"],
}


def diagnose_field_match(
    text: str,
    field: str,
    patterns: Iterable[str],
    weak_hints: Iterable[str] = (),
    *,
    limit: int = 3,
) -> FieldMatchDiagnostic:
    lines = _candidate_lines(text)
    if not lines:
        return FieldMatchDiagnostic(field=field, match_status="missing", confidence="low")

    candidates: list[dict[str, object]] = []
    strong_aliases = STRONG_FIELD_ALIASES.get(field, [])
    pattern_list = list(patterns)
    weak_hint_list = [hint for hint in weak_hints if hint not in pattern_list and hint not in strong_aliases]
    field_tokens = _tokens(field.replace("_", " "))

    for line in lines:
        candidate = _score_candidate(
            line=line,
            field=field,
            field_tokens=field_tokens,
            patterns=pattern_list,
            strong_aliases=strong_aliases,
            weak_hints=weak_hint_list,
        )
        if candidate:
            candidates.append(candidate)

    if not candidates:
        return FieldMatchDiagnostic(field=field, match_status="missing", confidence="high")

    candidates.sort(key=lambda item: (-float(item["score"]), len(str(item["text"]))))
    selected = candidates[:limit]
    best = selected[0]
    status = str(best["status"])
    confidence = str(best["confidence"])
    reasons = _unique(
        reason
        for candidate in selected
        for reason in candidate.get("ambiguity_reasons", [])
        if isinstance(reason, str)
    )
    return FieldMatchDiagnostic(
        field=field,
        match_status=status,
        confidence=confidence,
        ambiguity_reasons=reasons,
        candidate_matches=selected,
    )


def _score_candidate(
    *,
    line: str,
    field: str,
    field_tokens: set[str],
    patterns: list[str],
    strong_aliases: list[str],
    weak_hints: list[str],
) -> dict[str, object] | None:
    lowered = line.lower()
    matched_by: list[str] = []
    rejected_by: list[str] = []
    ambiguity_reasons: list[str] = []
    score = 0.0

    if any(pattern and pattern.lower() in lowered for pattern in patterns):
        score += 0.7
        matched_by.append("direct_pattern")

    if any(alias and alias.lower() in lowered for alias in strong_aliases):
        score += 0.75
        matched_by.append("strong_alias")

    if any(hint and hint.lower() in lowered for hint in weak_hints):
        score += 0.45
        matched_by.append("field_hint")
        ambiguity_reasons.append("weak_synonym")

    token_overlap = len((_tokens(line) & field_tokens) - {"or", "and"})
    if token_overlap:
        score += min(0.3, 0.15 * token_overlap)
        matched_by.append("field_token")

    heading = _is_heading_like(line)
    if heading:
        score += 0.1
        matched_by.append("heading_shape")

    if _has_label_content(line):
        score += 0.1
        matched_by.append("label_content")
    elif heading and "strong_alias" not in matched_by:
        rejected_by.append("heading_only")
        ambiguity_reasons.append("heading_only")

    if _is_negated_context(line):
        rejected_by.append("negated_context")
        ambiguity_reasons.append("negated_context")
        score -= 0.35

    if _looks_like_history_or_example(line):
        rejected_by.append("quoted_or_historical")
        ambiguity_reasons.append("quoted_or_historical")
        score -= 0.15

    if score < 0.35:
        return None

    if "negated_context" in rejected_by:
        status = "unknown"
        confidence = "low"
    elif "strong_alias" in matched_by or "direct_pattern" in matched_by:
        status = "matched" if score >= 0.75 else "partial"
        confidence = "high" if score >= 0.75 else "medium"
    elif "field_hint" in matched_by:
        status = "partial" if score >= 0.5 else "rejected"
        confidence = "medium" if score >= 0.5 else "low"
    else:
        status = "rejected"
        confidence = "low"

    return {
        "text": line.strip()[:220],
        "field": field,
        "score": round(max(0.0, min(score, 1.0)), 3),
        "status": status,
        "confidence": confidence,
        "matched_by": _unique(matched_by),
        "rejected_by": _unique(rejected_by),
        "ambiguity_reasons": _unique(ambiguity_reasons),
    }


def _candidate_lines(text: str) -> list[str]:
    stripped = _strip_code_blocks(text)
    raw_lines = [line.strip() for line in stripped.splitlines()]
    lines = [line for line in raw_lines if line and not line.startswith("|")]
    structured = [
        line
        for line in lines
        if re.match(r"^\s*(#{1,6}\s+|[-*]\s+|\d+[.)]\s+)?\S", line)
        and (":" in line or "：" in line or line.startswith(("#", "-", "*")) or len(line) <= 90)
    ]
    if structured:
        return structured[:300]
    return [sentence.strip() for sentence in re.split(r"(?<=[.!?。])\s+|\n+", stripped) if sentence.strip()][:300]


def _strip_code_blocks(text: str) -> str:
    return re.sub(r"```.*?```", " ", text, flags=re.DOTALL)


def _tokens(text: str) -> set[str]:
    return {token.lower() for token in re.findall(r"[A-Za-z0-9_一-龯ぁ-んァ-ヶー]{2,}", text)}


def _is_heading_like(line: str) -> bool:
    return bool(re.match(r"^\s*(#{1,6}\s+|[-*]\s+|\d+[.)]\s+)?[^:：]{1,80}(:|：)?\s*", line))


def _has_label_content(line: str) -> bool:
    if ":" in line:
        return bool(line.split(":", 1)[1].strip())
    if "：" in line:
        return bool(line.split("：", 1)[1].strip())
    return False


def _is_negated_context(line: str) -> bool:
    lowered = line.lower()
    return any(
        marker in lowered
        for marker in [
            "not ",
            "do not",
            "does not",
            "no ",
            "non-goal",
            "out of scope",
            "対象外",
            "しない",
            "不要",
            "除外",
        ]
    )


def _looks_like_history_or_example(line: str) -> bool:
    lowered = line.lower()
    return any(marker in lowered for marker in ["example", "for example", "observed", "previous", "過去", "例:", "例："])


def _unique(items: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result
