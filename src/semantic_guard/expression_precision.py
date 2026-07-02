from __future__ import annotations

import re
from typing import Any, Callable, Mapping

from semantic_guard.expression_terms import (
    _ASCII_IDENTIFIER_RE,
    _DEMONSTRATIVE_REFERENCE_TERMS,
    _EXPRESSION_CHECKS,
    _EXPRESSION_EXAMPLE_TABLE_TERMS,
    _EXPRESSION_NEGATIVE_EXAMPLE_TERMS,
    _EXPRESSION_SUPPORT_TERMS,
    _JAPANESE_NOUN_PHRASE_RE,
    _JAPANESE_TOKEN_CHARS,
    _REFERENT_SUPPORT_TERMS,
    _STRONG_REFERENT_TERMS,
    _WEAK_REFERENT_NOUNS,
)
from semantic_guard.models import Finding
from semantic_guard.text_matching import (
    has_any as _has_any,
    matched_terms as _matched_terms,
    unique_preserve_order as _unique_preserve_order,
)


def expression_precision_findings(
    text: str,
    catalog: Mapping[str, Any],
    *,
    rule_severity: Callable[[Mapping[str, Any]], str],
) -> tuple[list[Finding], dict[str, object]]:
    rules_by_id = {
        str(rule.get("id", "")): rule
        for rule in catalog.get("rules", [])
        if isinstance(rule, Mapping) and rule.get("detector") == "expression_precision"
    }
    findings: list[Finding] = []
    details: dict[str, object] = {
        "surface_detected": False,
        "matched_phrases": [],
        "support_terms": [],
        "suppressed_contexts": [],
        "emitted_rule_ids": [],
        "referent_resolutions": [],
        "operation_contracts": [],
    }
    matched_phrases: list[str] = []
    support_terms: list[str] = []
    suppressed_contexts: list[str] = []
    emitted_rule_ids: list[str] = []
    referent_resolutions: list[dict[str, object]] = []
    operation_contracts: list[dict[str, object]] = []

    lines = text.splitlines()
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue

        window = "\n".join(lines[max(0, index - 1) : min(len(lines), index + 2)])
        line_triggers = _matched_expression_triggers(stripped)
        if not line_triggers:
            continue

        details["surface_detected"] = True
        matched_phrases.extend(line_triggers)
        support_terms.extend(_matched_terms(window, _EXPRESSION_SUPPORT_TERMS))

        suppression_reason = _expression_suppression_reason(lines, index)
        if suppression_reason:
            suppressed_contexts.append(f"{suppression_reason}: {stripped[:160]}")
            continue

        for check in _EXPRESSION_CHECKS:
            rule_id = str(check["rule_id"])
            required_support = [str(term) for term in check["support_terms"]]
            matched = _matched_expression_check_terms(stripped, check)
            if not matched:
                continue

            resolution: dict[str, object] | None = None
            operation_contract: dict[str, object] | None = None
            if isinstance(check.get("operation_contract"), Mapping):
                operation_contract = _operation_contract_diagnostic(check, index, stripped, window, matched)
                operation_contracts.append(operation_contract)

            if check.get("reference_check"):
                resolution = _demonstrative_reference_resolution(lines, index, stripped, matched)
                referent_resolutions.append(resolution)
                has_support = resolution["status"] == "supported"
            elif check.get("support_policy") == "always_warn":
                has_support = False
            elif operation_contract:
                has_support = operation_contract["status"] == "supported"
            else:
                has_support = _has_any(window, required_support)
            if has_support:
                continue

            rule = rules_by_id.get(rule_id, {})
            nearest_candidates = _nearest_expression_candidates(required_support, resolution)
            findings.append(
                Finding(
                    severity=rule_severity(rule),
                    category=str(rule.get("category", "expression_precision")),
                    basis=[
                        f"convention:{catalog.get('id', 'base-contract')}",
                        f"rule:{rule_id}",
                        "detector:expression_precision",
                    ],
                    evidence=stripped[:240],
                    finding=str(rule.get("finding", "Document expression does not expose enough operational shape.")),
                    suggested_fix=str(
                        rule.get(
                            "suggested_fix",
                            "Name the target, operation, output form, decision actor, or revision target explicitly.",
                        )
                    ),
                    needs_human_decision=bool(check.get("needs_human_decision", False)),
                    warning_class="actionable",
                    nearest_candidates=nearest_candidates,
                    semantic_boundaries=[
                        "This check audits operational recoverability of prose, not literary quality.",
                        "It does not prove the statement true or decide final acceptance.",
                    ],
                    rule_id=rule_id,
                    repair={
                        "kind": "clarify_expression",
                        "target": str(check["repair_target"]),
                        "minimal_example": str(
                            check.get("minimal_example", "対象、操作、出力形式、判断主体を一文内か近傍に明示する。")
                        ),
                        "needs_human_decision": bool(check.get("needs_human_decision", False)),
                        "source": "expression_precision",
                        **({"rewrite_candidates": check["rewrite_candidates"]} if "rewrite_candidates" in check else {}),
                    },
                    match_status="partial",
                    confidence="medium",
                    ambiguity_reasons=_expression_ambiguity_reasons(matched, resolution, operation_contract),
                    candidate_matches=[{"term": term, "rule_id": rule_id} for term in matched],
                )
            )
            emitted_rule_ids.append(rule_id)

    details["matched_phrases"] = _unique_preserve_order(matched_phrases)
    details["support_terms"] = _unique_preserve_order(support_terms)
    details["suppressed_contexts"] = _unique_preserve_order(suppressed_contexts)
    details["emitted_rule_ids"] = _unique_preserve_order(emitted_rule_ids)
    details["referent_resolutions"] = referent_resolutions
    details["operation_contracts"] = operation_contracts
    return findings, details


def _matched_expression_triggers(text: str) -> list[str]:
    matched: list[str] = []
    for check in _EXPRESSION_CHECKS:
        matched.extend(_matched_expression_check_terms(text, check))
    return _unique_preserve_order(matched)


def _matched_expression_check_terms(text: str, check: Mapping[str, object]) -> list[str]:
    trigger_terms = [str(term) for term in check.get("trigger_terms", [])]
    strict_terms = {str(term) for term in check.get("strict_trigger_terms", [])}
    return [term for term in trigger_terms if _has_expression_trigger(text, term, strict_terms)]


def _has_expression_trigger(text: str, term: str, strict_terms: set[str]) -> bool:
    if term in strict_terms:
        return _has_standalone_japanese_term(text, term)
    return _has_any(text, [term])


def _has_standalone_japanese_term(text: str, term: str) -> bool:
    return bool(
        re.search(
            rf"(?<![{_JAPANESE_TOKEN_CHARS}]){re.escape(term)}(?=(?:を|は|が|に|へ|で|から|として|ごと|の|、|。|,|\.|$))",
            text,
        )
    )


def _nearest_expression_candidates(required_support: list[str], resolution: Mapping[str, object] | None) -> list[str]:
    if not resolution:
        return required_support[:12]
    candidates = resolution.get("candidates", [])
    if isinstance(candidates, list) and candidates:
        names = [str(item.get("text", "")) for item in candidates if isinstance(item, Mapping) and item.get("text")]
        if names:
            return names[:12]
    return required_support[:12]


def _operation_contract_diagnostic(
    check: Mapping[str, object],
    index: int,
    line: str,
    window: str,
    matched: list[str],
) -> dict[str, object]:
    contract = check.get("operation_contract")
    if not isinstance(contract, Mapping):
        return {
            "line": index + 1,
            "rule_id": str(check.get("rule_id", "")),
            "family": "unknown",
            "triggers": matched,
            "status": "unknown",
            "present_slots": [],
            "missing_slots": [],
            "slot_hits": {},
        }

    slots = contract.get("slots", {})
    slot_hits: dict[str, list[str]] = {}
    present_slots: list[str] = []
    missing_slots: list[str] = []
    if isinstance(slots, Mapping):
        for slot_name, slot_terms in slots.items():
            terms = [str(term) for term in slot_terms] if isinstance(slot_terms, list) else []
            hits = _matched_terms(window, terms)
            slot = str(slot_name)
            slot_hits[slot] = hits
            if hits:
                present_slots.append(slot)
            else:
                missing_slots.append(slot)

    policy = str(contract.get("policy", "any_support"))
    if policy == "always_warn":
        status = "under_specified"
    elif policy == "minimum_slots":
        minimum_slots = int(contract.get("minimum_slots", 1))
        status = "supported" if len(present_slots) >= minimum_slots else "under_specified"
    else:
        status = "supported" if present_slots else "under_specified"

    return {
        "line": index + 1,
        "rule_id": str(check.get("rule_id", "")),
        "family": str(contract.get("family", "")),
        "triggers": matched,
        "status": status,
        "present_slots": present_slots,
        "missing_slots": missing_slots,
        "slot_hits": slot_hits,
        "evidence": line[:240],
    }


def _expression_ambiguity_reasons(
    matched: list[str],
    resolution: Mapping[str, object] | None,
    operation_contract: Mapping[str, object] | None = None,
) -> list[str]:
    reasons = [f"matched vague expression: {term}" for term in matched]
    if resolution:
        reasons.append(f"referent resolution: {resolution.get('status', 'unknown')}")
        reason = str(resolution.get("reason", ""))
        if reason:
            reasons.append(reason)
    if operation_contract:
        missing_slots = operation_contract.get("missing_slots", [])
        if isinstance(missing_slots, list) and missing_slots:
            reasons.append(f"missing operation contract slots: {', '.join(str(slot) for slot in missing_slots)}")
    return reasons


def _demonstrative_reference_resolution(lines: list[str], index: int, line: str, matched: list[str]) -> dict[str, object]:
    earliest_match = min((line.find(term) for term in matched if term in line), default=-1)
    term = next((term for term in matched if term in line and line.find(term) == earliest_match), matched[0] if matched else "")
    if earliest_match < 0:
        return {"line": index + 1, "term": term, "status": "no_candidate", "reason": "trigger position was not found", "candidates": []}

    left_context = line[:earliest_match]
    right_context = line[earliest_match:]
    contexts = [
        ("previous_line", "\n".join(_previous_nonempty_lines(lines, index, limit=2))),
        ("structural_context", "\n".join(_nearest_structural_context(lines, index))),
        ("same_line_left", left_context),
    ]

    candidates: list[dict[str, object]] = []
    for source, context in contexts:
        candidates.extend(_extract_referent_candidates(context, source=source))
    candidates.extend(_definition_clause_candidates(right_context))
    candidates = _dedupe_candidates(candidates)

    strong = [candidate for candidate in candidates if candidate["strength"] == "strong"]
    medium = [candidate for candidate in candidates if candidate["strength"] == "medium"]
    weak = [candidate for candidate in candidates if candidate["strength"] == "weak"]
    if strong:
        status = "supported"
        reason = "strong named referent candidate found nearby"
    elif len(medium) == 1:
        status = "supported"
        reason = "single medium referent candidate found nearby"
    elif len(medium) > 1:
        status = "ambiguous"
        reason = "multiple medium referent candidates found nearby"
    elif weak:
        status = "weak_only"
        reason = "only broad carrier nouns were found nearby"
    else:
        status = "no_candidate"
        reason = "no named referent candidate found nearby"
    return {
        "line": index + 1,
        "term": term,
        "status": status,
        "reason": reason,
        "candidates": candidates[:12],
    }


def _definition_clause_candidates(text: str) -> list[dict[str, object]]:
    marker = re.search(r"(?:とは|は|:|：)", text)
    if not marker:
        return []
    return _extract_referent_candidates(text[marker.end() :], source="definition_clause")


def _previous_nonempty_lines(lines: list[str], index: int, *, limit: int) -> list[str]:
    previous: list[str] = []
    for line in reversed(lines[:index]):
        stripped = line.strip()
        if not stripped:
            continue
        previous.append(stripped)
        if len(previous) >= limit:
            break
    return list(reversed(previous))


def _nearest_structural_context(lines: list[str], index: int) -> list[str]:
    contexts: list[str] = []
    for line in reversed(lines[max(0, index - 12) : index]):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            contexts.append(stripped.lstrip("#").strip())
            break
        if re.match(r"^[-*]\s+\S+", stripped):
            contexts.append(re.sub(r"^[-*]\s+", "", stripped))
            break
    return list(reversed(contexts))


def _extract_referent_candidates(text: str, *, source: str) -> list[dict[str, object]]:
    candidates: list[dict[str, object]] = []
    if not text.strip():
        return candidates

    for match in re.finditer(r"`([^`]+)`", text):
        candidates.append(_referent_candidate(match.group(1), source=source, reason="code_span"))
    for match in _ASCII_IDENTIFIER_RE.finditer(text):
        candidates.append(_referent_candidate(match.group(0), source=source, reason="ascii_identifier"))
    for term in _REFERENT_SUPPORT_TERMS:
        if _has_any(text, [term]):
            candidates.append(_referent_candidate(term, source=source, reason="support_term"))
    for match in _JAPANESE_NOUN_PHRASE_RE.finditer(text):
        for candidate_text in _split_compound_candidate(match.group(1)):
            candidates.append(_referent_candidate(candidate_text, source=source, reason="noun_phrase"))

    return _dedupe_candidates(candidates)


def _split_compound_candidate(text: str) -> list[str]:
    parts = [part.strip() for part in re.split(r"(?:と|、|,|，|/)", text) if part.strip()]
    return parts or [text]


def _referent_candidate(text: str, *, source: str, reason: str) -> dict[str, object]:
    cleaned = _clean_candidate_text(text)
    return {
        "text": cleaned,
        "source": source,
        "strength": _referent_strength(cleaned, reason=reason),
        "reason": reason,
    }


def _clean_candidate_text(text: str) -> str:
    cleaned = text.strip("`*_[]（）()「」『』,，、。:：;； \t\n")
    cleaned = re.sub(r"^(?:この|その|あの)", "", cleaned)
    return cleaned


def _referent_strength(text: str, *, reason: str) -> str:
    if not text:
        return "weak"
    if reason in {"code_span", "ascii_identifier"}:
        return "strong"
    if _has_any(text, _STRONG_REFERENT_TERMS):
        return "strong"
    if text in _WEAK_REFERENT_NOUNS:
        return "weak"
    if len(text) <= 1:
        return "weak"
    return "medium"


def _dedupe_candidates(candidates: list[dict[str, object]]) -> list[dict[str, object]]:
    exact_unique: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()
    strength_rank = {"strong": 3, "medium": 2, "weak": 1}
    for candidate in candidates:
        text = str(candidate.get("text", ""))
        if not text:
            continue
        key = (text, str(candidate.get("source", "")))
        if key in seen:
            continue
        seen.add(key)
        exact_unique.append(candidate)

    unique: list[dict[str, object]] = []
    for candidate in exact_unique:
        text = str(candidate.get("text", ""))
        source = str(candidate.get("source", ""))
        rank = strength_rank.get(str(candidate.get("strength")), 0)
        shadowed = False
        for other in exact_unique:
            other_text = str(other.get("text", ""))
            other_source = str(other.get("source", ""))
            other_rank = strength_rank.get(str(other.get("strength")), 0)
            if candidate is other or source != other_source or text == other_text:
                continue
            if text in other_text and rank <= other_rank:
                shadowed = True
                break
        if not shadowed:
            unique.append(candidate)

    unique.sort(key=lambda candidate: strength_rank.get(str(candidate.get("strength")), 0), reverse=True)
    return unique


def _expression_suppression_reason(lines: list[str], index: int) -> str:
    line = lines[index].strip()
    if line.startswith((">", "-", "*")) and _has_any(line, _EXPRESSION_NEGATIVE_EXAMPLE_TERMS):
        return "negative_example_marker"
    context = "\n".join(lines[max(0, index - 8) : index + 1])
    if _has_any(context, _EXPRESSION_NEGATIVE_EXAMPLE_TERMS):
        return "negative_example_context"
    table_context = "\n".join(lines[max(0, index - 16) : index + 1])
    if line.startswith("|") and _has_any(table_context, _EXPRESSION_EXAMPLE_TABLE_TERMS):
        return "seed_example_table_context"
    if _inside_code_fence(lines, index):
        return "quoted_or_code_example"
    return ""


def _inside_code_fence(lines: list[str], index: int) -> bool:
    fence_count = 0
    for line in lines[: index + 1]:
        if line.strip().startswith("```"):
            fence_count += 1
    return fence_count % 2 == 1
