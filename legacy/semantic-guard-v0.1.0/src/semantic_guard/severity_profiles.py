from __future__ import annotations

from typing import Any

SEVERITY_ORDER = {"info": 0, "minor": 1, "major": 2, "blocker": 3}
SEVERITY_BY_LEVEL = {level: severity for severity, level in SEVERITY_ORDER.items()}

PROFILE_NAMES = ("default", "dogfood", "exploratory", "release", "safety")

PROFILE_OVERRIDES: dict[str, dict[str, Any]] = {
    "default": {},
    "dogfood": {
        "category_minimums": {
            "security": "major",
            "risk": "minor",
            "validation": "major",
        }
    },
    "exploratory": {
        "max_severity": "major",
        "category_minimums": {},
    },
    "release": {
        "category_minimums": {
            "security": "blocker",
            "risk": "major",
            "validation": "major",
            "evidence": "major",
            "compatibility": "major",
            "control": "major",
            "governance": "major",
        }
    },
    "safety": {
        "category_minimums": {
            "security": "blocker",
            "risk": "blocker",
            "validation": "blocker",
            "acceptance": "major",
            "permission": "blocker",
            "evidence": "major",
        }
    },
}


def apply_severity_profile(result: dict[str, Any], profile: str = "default") -> dict[str, Any]:
    normalized = _normalize_profile(profile)
    if normalized == "default":
        payload = dict(result)
        details = dict(payload.get("details", {}))
        base_score = float(payload.get("score", 0.0))
        details["severity_profile"] = {
            "name": "default",
            "applied": False,
            "adjustments": [],
            "base_score": round(base_score, 3),
            "profiled_score": round(base_score, 3),
            "score_semantics": "score is the base deterministic score; profiled_score reflects severity-profile adjustments.",
        }
        payload["details"] = details
        return payload

    payload = dict(result)
    findings = [dict(finding) for finding in payload.get("findings", []) if isinstance(finding, dict)]
    adjustments: list[dict[str, object]] = []
    overrides = PROFILE_OVERRIDES[normalized]

    for index, finding in enumerate(findings):
        original = str(finding.get("severity", "info"))
        adjusted = _profiled_severity(original, str(finding.get("category", "")), overrides)
        if adjusted != original:
            finding["severity"] = adjusted
            adjustments.append(
                {
                    "finding_index": index,
                    "category": finding.get("category", ""),
                    "rule_id": finding.get("rule_id", ""),
                    "from": original,
                    "to": adjusted,
                }
            )

    payload["findings"] = findings
    base_score = float(payload.get("score", 0.0))
    profiled_score = _score_from_findings(findings)
    payload["status"] = _status_from_findings(findings, profiled_score)
    details = dict(payload.get("details", {}))
    details["severity_profile"] = {
        "name": normalized,
        "applied": True,
        "adjustments": adjustments,
        "base_score": round(base_score, 3),
        "profiled_score": round(profiled_score, 3),
        "score_semantics": "score is the base deterministic score; profiled_score reflects severity-profile adjustments.",
    }
    payload["details"] = details
    return payload


def _profiled_severity(original: str, category: str, overrides: dict[str, Any]) -> str:
    severity = original if original in SEVERITY_ORDER else "info"
    minimum = overrides.get("category_minimums", {}).get(category)
    if minimum and SEVERITY_ORDER[minimum] > SEVERITY_ORDER[severity]:
        severity = minimum

    max_severity = overrides.get("max_severity")
    if max_severity and SEVERITY_ORDER[severity] > SEVERITY_ORDER[max_severity]:
        severity = max_severity
    return severity


def _status_from_findings(findings: list[dict[str, Any]], score: float) -> str:
    if any(finding.get("severity") == "blocker" for finding in findings):
        return "block"
    if any(finding.get("severity") in {"major", "minor"} for finding in findings):
        return "warn"
    if findings and score < 0.75:
        return "warn"
    return "pass"


def _score_from_findings(findings: list[dict[str, Any]]) -> float:
    score = 1.0
    for finding in findings:
        severity = finding.get("severity")
        if severity == "blocker":
            score -= 0.35
        elif severity == "major":
            score -= 0.18
        elif severity == "minor":
            score -= 0.07
    return max(0.0, score)


def _normalize_profile(profile: str) -> str:
    normalized = (profile or "default").strip().lower().replace("_", "-")
    if normalized not in PROFILE_NAMES:
        return "default"
    return normalized
