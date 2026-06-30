from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from semantic_guard.resources import resource_path

Severity = Literal["blocker", "major", "minor", "info"]
Status = Literal["pass", "warn", "block"]
WarningClass = Literal["actionable", "generic caution", "possible false positive"]
MatchStatus = Literal["matched", "partial", "rejected", "missing", "not_applicable", "unknown"]
Confidence = Literal["high", "medium", "low"]
AUDIT_RESULT_SCHEMA_FILE = resource_path("schemas", "audit-result.schema.json")


def audit_result_schema_path() -> Path:
    return AUDIT_RESULT_SCHEMA_FILE


def load_audit_result_schema() -> dict[str, object]:
    return json.loads(AUDIT_RESULT_SCHEMA_FILE.read_text(encoding="utf-8"))


@dataclass
class Finding:
    severity: Severity
    category: str
    basis: list[str]
    finding: str
    evidence: str = ""
    suggested_fix: str = ""
    needs_human_decision: bool = False
    warning_class: WarningClass = "actionable"
    nearest_candidates: list[str] = field(default_factory=list)
    semantic_boundaries: list[str] = field(default_factory=list)
    rule_id: str = ""
    repair: dict[str, object] = field(default_factory=dict)
    match_status: MatchStatus | str = ""
    confidence: Confidence | str = ""
    ambiguity_reasons: list[str] = field(default_factory=list)
    candidate_matches: list[dict[str, object]] = field(default_factory=list)
    derivation: dict[str, object] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "severity": self.severity,
            "category": self.category,
            "basis": self.basis,
            "evidence": self.evidence,
            "finding": self.finding,
            "suggested_fix": self.suggested_fix,
            "needs_human_decision": self.needs_human_decision,
            "warning_class": self.warning_class,
        }
        if self.nearest_candidates:
            payload["nearest_candidates"] = self.nearest_candidates
        if self.semantic_boundaries:
            payload["semantic_boundaries"] = self.semantic_boundaries
        if self.rule_id:
            payload["rule_id"] = self.rule_id
        if self.repair:
            payload["repair"] = self.repair
        if self.match_status:
            payload["match_status"] = self.match_status
        if self.confidence:
            payload["confidence"] = self.confidence
        if self.ambiguity_reasons:
            payload["ambiguity_reasons"] = self.ambiguity_reasons
        if self.candidate_matches:
            payload["candidate_matches"] = self.candidate_matches
        if self.derivation:
            payload["derivation"] = self.derivation
        return payload


@dataclass
class AuditResult:
    phase: str
    status: Status
    score: float
    findings: list[Finding] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    details: dict[str, object] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        return {
            "phase": self.phase,
            "status": self.status,
            "score": round(self.score, 3),
            "findings": [finding.as_dict() for finding in self.findings],
            "missing": self.missing,
            "next_actions": self.next_actions,
            "details": self.details,
        }
