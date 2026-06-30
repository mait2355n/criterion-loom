from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable, Mapping

from semantic_guard.models import AuditResult, Finding
from semantic_guard.resources import resource_path

CONVENTIONS_DIR = resource_path("docs", "conventions")
BASE_CONTRACT_FILE = CONVENTIONS_DIR / "base-contract.json"


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

    score = _score(findings)
    status = _status(findings)
    next_actions = [finding.suggested_fix for finding in findings[:5]]
    if not findings and not any(surface_hits.values()):
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
            "score_semantics": "score is a local convention-contract completeness score, not general implementation quality.",
        },
    ).as_dict()


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
