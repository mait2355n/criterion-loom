from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable, Mapping

from semantic_guard.models import AuditResult, Finding
from semantic_guard.resources import resource_path

CONVENTIONS_DIR = resource_path("docs", "conventions")
BASE_CONTRACT_FILE = CONVENTIONS_DIR / "base-contract.json"

_EXPRESSION_NEGATIVE_EXAMPLE_TERMS = [
    "bad example",
    "bad examples",
    "negative example",
    "avoid",
    "do not write",
    "does not say",
    "should warn",
    "warns",
    "avoid softer",
    "avoid vague",
    "review checklist",
    "before committing",
    "backed by an operation",
    "悪い例",
    "悪例",
    "避ける",
    "警告する",
    "警告される",
    "警告対象",
]

_EXPRESSION_EXAMPLE_TABLE_TERMS = [
    "observed wording changes",
    "seed examples",
    "before pattern",
    "after pattern",
]

_DEMONSTRATIVE_REFERENCE_TERMS = [
    "この内容",
    "その内容",
    "あの内容",
    "この部分",
    "その部分",
    "あの部分",
    "この箇所",
    "その箇所",
    "あの箇所",
    "この場所",
    "その場所",
    "あの場所",
    "この材料",
    "その材料",
    "あの材料",
    "このもの",
    "そのもの",
    "あのもの",
    "この表現",
    "その表現",
    "あの表現",
    "この結果",
    "その結果",
    "あの結果",
    "この値",
    "その値",
    "あの値",
    "この一覧",
    "その一覧",
    "あの一覧",
    "この記録",
    "その記録",
    "あの記録",
    "この出力",
    "その出力",
    "あの出力",
    "この対象",
    "その対象",
    "あの対象",
    "この指摘",
    "その指摘",
    "あの指摘",
    "この判断",
    "その判断",
    "あの判断",
    "その文書",
    "あの文書",
    "これら",
    "それら",
    "これ",
    "それ",
    "あれ",
    "ここ",
    "そこ",
    "こちら",
    "そちら",
]

_REFERENT_SUPPORT_TERMS = [
    "不明点",
    "未決定",
    "要求",
    "計画",
    "差分",
    "指摘",
    "候補",
    "診断",
    "監査",
    "対象",
    "項目",
    "一覧",
    "記録",
    "文書",
    "証拠",
    "根拠",
    "条件",
    "規則",
    "契約",
    "出力",
    "入力",
    "台帳",
    "目録",
    "schema_version",
    "status",
    "findings",
    "diagnostics",
    "details",
    "field",
    "schema",
    "JSON",
    "manifest",
    "bundle",
    "record",
    "artifact",
    "consulted",
    "missing",
    "inferred",
    "stale_candidates",
    "debt",
]

_STRONG_REFERENT_TERMS = [
    "schema_version",
    "status",
    "findings",
    "diagnostics",
    "details",
    "field",
    "schema",
    "manifest",
    "record",
    "artifact",
    "consulted",
    "missing",
    "inferred",
    "stale_candidates",
    "debt",
]

_WEAK_REFERENT_NOUNS = {
    "内容",
    "もの",
    "物",
    "部分",
    "場所",
    "箇所",
    "材料",
    "対象",
    "結果",
    "値",
    "情報",
    "データ",
    "こと",
    "点",
}

_JAPANESE_NOUN_PHRASE_RE = re.compile(
    r"([一-龯ァ-ンA-Za-z0-9_`][一-龯ぁ-んァ-ンA-Za-z0-9_`・ー./-]{1,40})(?:を|は|が|に|へ|から|として|ごと|で)"
)

_ASCII_IDENTIFIER_RE = re.compile(r"(?<![A-Za-z0-9_])[$]?[A-Za-z][A-Za-z0-9_]*(?:[._-][A-Za-z0-9_]+)+(?![A-Za-z0-9_])")

_EXPRESSION_CHECKS = [
    {
        "rule_id": "doc.expression.target_blurred",
        "trigger_terms": [
            "怪しい場所",
            "怪しい箇所",
            "気になるところ",
            "弱いところ",
            "不確かな点",
            "不確かなところ",
            "場所",
            "箇所",
            "部分",
            "内容",
            "材料",
            "もの",
        ],
        "support_terms": [
            "不明点",
            "差分",
            "要求",
            "計画",
            "指摘",
            "候補",
            "診断",
            "監査",
            "対象",
            "判断が必要",
            "要確認",
            "field",
            "rule",
            "finding",
        ],
        "repair_target": "target",
    },
    {
        "rule_id": "doc.expression.demonstrative_reference_blurred",
        "trigger_terms": _DEMONSTRATIVE_REFERENCE_TERMS,
        "support_terms": _REFERENT_SUPPORT_TERMS,
        "repair_target": "referent",
        "reference_check": True,
    },
    {
        "rule_id": "doc.expression.operation_blurred",
        "trigger_terms": ["外に出す", "外へ出す", "共有する", "渡す", "活用する", "対応する", "見える化する", "見える化", "可視化する"],
        "support_terms": ["抽出", "返す", "記録", "分類", "列挙", "検出", "出力", "保存", "生成", "診断", "emit", "return"],
        "repair_target": "operation",
    },
    {
        "rule_id": "doc.expression.utility_blurred",
        "trigger_terms": [
            "試験できる",
            "判断できる",
            "改善できる",
            "使える",
            "活用できる",
            "確認できる",
            "レビューできる",
            "検討できる",
            "対応できる",
        ],
        "support_terms": [
            "抽出",
            "返す",
            "分類",
            "一覧",
            "JSON",
            "監査結果",
            "findings",
            "diagnostics",
            "人間",
            "外部",
            "最終判断",
        ],
        "repair_target": "utility",
    },
    {
        "rule_id": "doc.expression.output_form_missing",
        "trigger_terms": ["内容", "外に出す", "外へ出す", "できる形", "使える形", "検討できる形", "レビューできる形", "返す", "出力する"],
        "support_terms": ["JSON", "一覧", "表", "監査結果", "finding", "findings", "diagnostics", "fixture", "記録", "レポート"],
        "repair_target": "output_form",
    },
    {
        "rule_id": "doc.expression.decision_actor_missing",
        "trigger_terms": ["判断できる", "判断に使える", "試験できる", "評価できる"],
        "support_terms": ["人間", "外部", "外部判断", "保守者", "最終判断", "accept", "request_revision", "defer"],
        "repair_target": "decision_actor",
    },
    {
        "rule_id": "doc.expression.revision_target_missing",
        "trigger_terms": ["改善できる", "修正できる", "直せる", "精度を上げる", "よくできる"],
        "support_terms": ["rule", "detector", "fixture", "corpus", "文書", "規約", "指摘", "差分", "修正対象"],
        "repair_target": "revision_target",
    },
]

_EXPRESSION_SUPPORT_TERMS = sorted(
    {
        str(term)
        for check in _EXPRESSION_CHECKS
        for term in check["support_terms"]
    }
)


def conventions_dir_path() -> Path:
    return CONVENTIONS_DIR


def conventions_catalog_path() -> Path:
    return BASE_CONTRACT_FILE


def load_conventions_catalog() -> dict[str, Any]:
    return json.loads(BASE_CONTRACT_FILE.read_text(encoding="utf-8"))


def audit_conventions(
    text: str,
    *,
    context: str = "",
    strict: bool = True,
    input_kind: str = "document",
) -> dict[str, object]:
    catalog = load_conventions_catalog()
    combined = "\n".join(part for part in [context, text] if part)
    surface_hits = _detect_surfaces(combined, catalog)
    findings: list[Finding] = []
    missing: list[str] = []

    for rule in catalog.get("rules", []):
        if not isinstance(rule, Mapping):
            continue
        if rule.get("detector"):
            continue
        applies_to = [str(item) for item in rule.get("applies_to", [])]
        active_surfaces = [surface for surface in applies_to if surface_hits.get(surface)]
        if rule.get("requires_any_surface", False) and not active_surfaces:
            continue
        if applies_to and not active_surfaces:
            continue
        if rule.get("requires_failure_terms", False) and not _has_failure_terms(combined):
            continue

        missing_groups = _missing_required_groups(combined, rule.get("required_groups", []))
        if not missing_groups:
            continue

        rule_id = str(rule.get("id", ""))
        missing.append(rule_id)
        findings.append(
            Finding(
                severity=_rule_severity(rule, strict=strict, catalog=catalog),
                category=str(rule.get("category", "governance")),
                basis=[
                    f"convention:{catalog.get('id', 'base-contract')}",
                    f"rule:{rule_id}",
                    f"surfaces:{','.join(active_surfaces) if active_surfaces else 'none'}",
                ],
                evidence=_evidence_excerpt(combined, rule, active_surfaces),
                finding=str(rule.get("finding", "Convention requirement is incomplete.")),
                suggested_fix=str(rule.get("suggested_fix", "State the missing convention fields.")),
                warning_class="actionable",
                nearest_candidates=[", ".join(group) for group in missing_groups],
                semantic_boundaries=[
                    "This check audits public contract shape, not internal architecture quality.",
                    "The base contract is draft; promotion to blockers requires user confirmation.",
                ],
                rule_id=rule_id,
                match_status="partial",
                confidence="medium",
            )
        )

    expression_findings, expression_details = _expression_precision_findings(combined, catalog, strict=strict)
    findings.extend(expression_findings)
    missing.extend(finding.rule_id for finding in expression_findings if finding.rule_id)

    score = _score(findings)
    status = _status(findings)
    next_actions = [finding.suggested_fix for finding in findings[:5]]
    if not findings and not any(surface_hits.values()) and not expression_details["surface_detected"]:
        next_actions = ["No convention-relevant public surface was detected; use a repository profile when one exists."]

    return AuditResult(
        phase="audit_conventions",
        status=status,
        score=score,
        findings=findings,
        missing=missing,
        next_actions=next_actions,
        details={
            "schema_version": catalog.get("schema_version"),
            "convention_id": catalog.get("id"),
            "convention_status": catalog.get("status"),
            "source": catalog.get("source"),
            "input_kind": input_kind,
            "surfaces": surface_hits,
            "rule_count": len([rule for rule in catalog.get("rules", []) if isinstance(rule, Mapping)]),
            "expression_precision": expression_details,
            "score_semantics": "score is a local convention-contract completeness score, not general implementation quality.",
        },
    ).as_dict()


def _expression_precision_findings(text: str, catalog: Mapping[str, Any], *, strict: bool) -> tuple[list[Finding], dict[str, object]]:
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
    }
    matched_phrases: list[str] = []
    support_terms: list[str] = []
    suppressed_contexts: list[str] = []
    emitted_rule_ids: list[str] = []
    referent_resolutions: list[dict[str, object]] = []

    lines = text.splitlines()
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue

        window = "\n".join(lines[max(0, index - 1) : min(len(lines), index + 2)])
        line_triggers = _matched_terms(stripped, _expression_trigger_terms())
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
            trigger_terms = [str(term) for term in check["trigger_terms"]]
            required_support = [str(term) for term in check["support_terms"]]
            matched = _matched_terms(stripped, trigger_terms)
            if not matched:
                continue

            resolution: dict[str, object] | None = None
            if check.get("reference_check"):
                resolution = _demonstrative_reference_resolution(lines, index, stripped, matched)
                referent_resolutions.append(resolution)
                has_support = resolution["status"] == "supported"
            else:
                has_support = _has_any(window, required_support)
            if has_support:
                continue

            rule = rules_by_id.get(rule_id, {})
            nearest_candidates = _nearest_expression_candidates(required_support, resolution)
            findings.append(
                Finding(
                    severity=_rule_severity(rule, strict=strict, catalog=catalog),
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
                        "minimal_example": "対象、操作、出力形式、判断主体を一文内か近傍に明示する。",
                        "needs_human_decision": False,
                        "source": "expression_precision",
                    },
                    match_status="partial",
                    confidence="medium",
                    ambiguity_reasons=_expression_ambiguity_reasons(matched, resolution),
                    candidate_matches=[{"term": term, "rule_id": rule_id} for term in matched],
                )
            )
            emitted_rule_ids.append(rule_id)

    details["matched_phrases"] = _unique_preserve_order(matched_phrases)
    details["support_terms"] = _unique_preserve_order(support_terms)
    details["suppressed_contexts"] = _unique_preserve_order(suppressed_contexts)
    details["emitted_rule_ids"] = _unique_preserve_order(emitted_rule_ids)
    details["referent_resolutions"] = referent_resolutions
    return findings, details


def _expression_trigger_terms() -> list[str]:
    return _unique_preserve_order(str(term) for check in _EXPRESSION_CHECKS for term in check["trigger_terms"])


def _nearest_expression_candidates(required_support: list[str], resolution: Mapping[str, object] | None) -> list[str]:
    if not resolution:
        return required_support[:12]
    candidates = resolution.get("candidates", [])
    if isinstance(candidates, list) and candidates:
        names = [str(item.get("text", "")) for item in candidates if isinstance(item, Mapping) and item.get("text")]
        if names:
            return names[:12]
    return required_support[:12]


def _expression_ambiguity_reasons(matched: list[str], resolution: Mapping[str, object] | None) -> list[str]:
    reasons = [f"matched vague expression: {term}" for term in matched]
    if resolution:
        reasons.append(f"referent resolution: {resolution.get('status', 'unknown')}")
        reason = str(resolution.get("reason", ""))
        if reason:
            reasons.append(reason)
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


def _matched_terms(text: str, terms: Iterable[str]) -> list[str]:
    return [term for term in terms if _has_any(text, [term])]


def _unique_preserve_order(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        unique.append(item)
    return unique


def _detect_surfaces(text: str, catalog: Mapping[str, Any]) -> dict[str, bool]:
    surfaces: dict[str, bool] = {}
    for surface in catalog.get("surfaces", []):
        if not isinstance(surface, Mapping):
            continue
        surface_id = str(surface.get("id", ""))
        terms = [str(term) for term in surface.get("terms", [])]
        surfaces[surface_id] = _has_any(text, terms)
    return surfaces


def _missing_required_groups(text: str, groups: object) -> list[list[str]]:
    missing: list[list[str]] = []
    if not isinstance(groups, list):
        return missing
    for group in groups:
        if not isinstance(group, list):
            continue
        terms = [str(term) for term in group]
        if not _has_any(text, terms):
            missing.append(terms)
    return missing


def _has_any(text: str, terms: Iterable[str]) -> bool:
    lowered = text.lower()
    for term in terms:
        normalized = term.lower()
        if _is_ascii_word(normalized):
            if re.search(rf"(?<![a-z0-9_]){re.escape(normalized)}(?![a-z0-9_])", lowered):
                return True
        elif normalized in lowered:
            return True
    return False


def _has_failure_terms(text: str) -> bool:
    return _has_any(text, ["error", "failure", "failed", "invalid", "timeout", "stderr", "失敗", "エラー", "異常", "失敗時"])


def _is_ascii_word(term: str) -> bool:
    return bool(re.fullmatch(r"[a-z0-9_ -]+", term))


def _rule_severity(rule: Mapping[str, Any], *, strict: bool, catalog: Mapping[str, Any]) -> str:
    severity = str(rule.get("severity", "major"))
    if severity == "blocker" and not strict:
        return "major"
    if catalog.get("status") == "draft" and severity == "blocker":
        return "major"
    return severity if severity in {"blocker", "major", "minor", "info"} else "major"


def _evidence_excerpt(text: str, rule: Mapping[str, Any], active_surfaces: list[str]) -> str:
    terms: list[str] = []
    for surface in active_surfaces:
        terms.append(surface)
    terms.extend(str(term) for group in rule.get("required_groups", []) if isinstance(group, list) for term in group)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines:
        if _has_any(line, terms):
            return line[:240]
    return (text.strip() or "No text supplied.")[:240]


def _status(findings: list[Finding]) -> str:
    if any(finding.severity == "blocker" for finding in findings):
        return "block"
    if any(finding.severity in {"major", "minor"} for finding in findings):
        return "warn"
    return "pass"


def _score(findings: list[Finding]) -> float:
    score = 1.0
    for finding in findings:
        if finding.severity == "blocker":
            score -= 0.3
        elif finding.severity == "major":
            score -= 0.16
        elif finding.severity == "minor":
            score -= 0.06
    return max(0.0, round(score, 3))
