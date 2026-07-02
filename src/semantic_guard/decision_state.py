from __future__ import annotations

import re
from collections.abc import Iterable

from semantic_guard.models import Finding
from semantic_guard.result_builder import (
    build_result,
    next_actions as _next_actions,
    score_from_findings as _score_from_findings,
)

DECISION_STATE_AUDIT_SCHEMA_VERSION = "decision-state-audit/v1"
DEFAULT_SNIPPET_LIMIT = 220
INPUT_KINDS = {"requirement", "plan", "document", "diff-summary"}

REQUIREMENTS_BASIS = ["ISO/IEC/IEEE 29148", "BABOK", "NASA SEH"]
PLANNING_BASIS = ["PMBOK", "PMI WBS", "ISO 21502", "ISO 21511", "NASA SEH", "NASA SEMP"]
MEANING_BASIS = ["semantic-implementation"]

DECISION_STATE_TERMS: dict[str, list[str]] = {
    "pending_decision": [
        "未決",
        "未決定",
        "未確定",
        "判断待ち",
        "決定待ち",
        "保留",
        "pending decision",
        "to be decided",
        "tbd",
        "tbr",
    ],
    "unknown": ["不明", "未確認", "わからない", "unknown", "unconfirmed", "not confirmed"],
    "hypothesis": ["仮説", "仮定", "assumption", "hypothesis"],
    "inference": ["推測", "推定", "推論", "おそらく", "たぶん", "inference", "inferred", "probably"],
    "one_sided_observation": ["片側観測", "片側", "一方だけ", "one-sided", "single-sided"],
    "time_dependent": ["現時点", "時点差", "最新", "current", "latest", "today", "as of"],
    "value_judgment": ["価値判断", "優先", "重視", "許容", "妥協", "tradeoff", "trade-off", "risk tolerance"],
    "evidence_gap": ["証拠なし", "根拠なし", "証跡なし", "未検証", "裏取りなし", "no evidence", "not verified", "evidence gap"],
}

DECISION_STATE_CONTROL_TERMS: dict[str, list[str]] = {
    "owner": ["owner", "担当", "判断者", "決定者", "decision_owner", "human", "人間"],
    "needed_for": ["needed_for", "必要理由", "何のため", "目的", "goal", "connects_to"],
    "blocking_status": ["blocking", "block", "塞ぐ", "止める", "遮断", "依存"],
    "next_action": ["next_action", "次行動", "次に", "確認", "調査", "検証"],
    "review_at": ["review_at", "再確認", "見直し", "期限", "by ", "until"],
    "evidence_reference": ["evidence", "source", "証拠", "証跡", "根拠", "出典", "ログ"],
}


def audit_decision_state(text: str, context: str = "", strict: bool = True, input_kind: str = "document") -> dict[str, object]:
    """Expose decided, undecided, inferred, hypothetical, and evidence-gap states without resolving them."""
    input_kind = _normalize_input_kind(input_kind)
    combined = _combine(text, context)
    findings: list[Finding] = []
    missing: list[str] = []
    report = _decision_state_report(combined)
    counts = report["counts"]
    control_fields = report["control_fields"]

    if not text.strip():
        findings.append(_blocker("clarity", "監査対象本文が空。", "決定状態を含む本文を渡す。", MEANING_BASIS))
        missing.append("text")

    if not report["has_explicit_decision_state"]:
        findings.append(
            Finding(
                severity="minor" if strict else "info",
                category="decision_state",
                basis=MEANING_BASIS + PLANNING_BASIS,
                finding="決定済み、未決定、仮説、推測、不明、根拠不足の区別が明示されていない。",
                suggested_fix="決定状態を decided / undecided / hypothesis / inferred / unknown / needs_evidence のいずれかで明示する。",
                needs_human_decision=True,
                warning_class="possible false positive",
            )
        )
        missing.append("decision_state_markers")

    unresolved_count = int(report["unresolved_item_count"])
    if unresolved_count:
        findings.append(
            Finding(
                severity="major" if strict else "minor",
                category="decision_state",
                basis=MEANING_BASIS + PLANNING_BASIS,
                finding="未決定または不確実な項目がある。監査は露出までで、解決管理は管制面へ渡す必要がある。",
                evidence=str(report["first_unresolved_evidence"]),
                suggested_fix="owner, needed_for, blocking_status, next_action, review_at を付けて管理対象へ移す。",
                needs_human_decision=True,
            )
        )
        missing.append("unresolved_decision_management")
        for field in ("owner", "needed_for", "blocking_status", "next_action", "review_at"):
            if not control_fields[field]:
                missing.append(f"unresolved_{field}")

    if int(counts["value_judgment"]):
        findings.append(
            Finding(
                severity="minor",
                category="value_judgment",
                basis=MEANING_BASIS + PLANNING_BASIS,
                finding="価値判断が含まれている。これは監査で自動決定せず、判断主体と判断基準を分ける必要がある。",
                evidence=str(report["first_value_judgment_evidence"]),
                suggested_fix="何を優先し、何を犠牲にする判断なのかを人間の判断点として記録する。",
                needs_human_decision=True,
            )
        )

    if int(counts["evidence_gap"]):
        findings.append(
            Finding(
                severity="major" if strict else "minor",
                category="evidence",
                basis=REQUIREMENTS_BASIS + MEANING_BASIS,
                finding="根拠不足または未検証の項目がある。",
                evidence=str(report["first_evidence_gap_evidence"]),
                suggested_fix="根拠、証跡、確認方法、または未検証のまま扱う範囲を明示する。",
            )
        )
        missing.append("decision_evidence")

    if int(counts["hypothesis"]) or int(counts["inference"]):
        findings.append(
            Finding(
                severity="minor",
                category="uncertainty",
                basis=MEANING_BASIS,
                finding="仮説または推測が含まれている。事実と同格に扱わないための境界が必要。",
                evidence=str(report["first_inferential_evidence"]),
                suggested_fix="仮説、推測、確認済み事実を分け、仮説が崩れた時の影響先を書く。",
            )
        )

    return build_result(
        phase="audit_decision_state",
        findings=findings,
        missing=sorted(set(missing)),
        score=_score_from_findings(findings),
        details={
            "schema_version": DECISION_STATE_AUDIT_SCHEMA_VERSION,
            "input_kind": input_kind,
            "decision_authority": {
                "audit_scope": "expose decision and uncertainty state",
                "does_not_decide": True,
                "final_decision_owner": "human_or_control_plane",
            },
            "decision_state_report": report,
        },
        next_actions=_next_actions(findings, "決定状態を明示し、未決定項目を管制面の管理対象へ渡す。"),
    )


def _decision_state_report(text: str) -> dict[str, object]:
    units = _decision_state_units(text)
    control_values = _decision_control_values(text)
    items: list[dict[str, object]] = []
    explicit_categories: list[str] = []
    none_categories: list[str] = []

    for category, terms in DECISION_STATE_TERMS.items():
        category_explicit = False
        for unit in units:
            if not _has_any(unit, terms):
                continue
            category_explicit = True
            if _decision_state_unit_declares_none(unit, terms):
                none_categories.append(category)
                continue
            items.append(_decision_state_item(category, unit, control_values))
        if category_explicit:
            explicit_categories.append(category)

    items = _unique_decision_state_items(items)
    counts = {category: sum(1 for item in items if item["uncertainty_kind"] == category) for category in DECISION_STATE_TERMS}
    unresolved_categories = {
        "pending_decision",
        "unknown",
        "hypothesis",
        "inference",
        "one_sided_observation",
        "time_dependent",
        "value_judgment",
        "evidence_gap",
    }
    unresolved_items = [item for item in items if str(item["uncertainty_kind"]) in unresolved_categories]
    first_by_category = {category: _first_item_evidence(items, category) for category in DECISION_STATE_TERMS}

    return {
        "has_explicit_decision_state": bool(explicit_categories),
        "explicit_categories": sorted(set(explicit_categories)),
        "none_categories": sorted(set(none_categories)),
        "counts": counts,
        "unresolved_item_count": len(unresolved_items),
        "first_unresolved_evidence": _first_item_evidence(unresolved_items, ""),
        "first_value_judgment_evidence": first_by_category["value_judgment"],
        "first_evidence_gap_evidence": first_by_category["evidence_gap"],
        "first_inferential_evidence": _first_item_evidence(
            [item for item in items if item["uncertainty_kind"] in {"hypothesis", "inference"}],
            "",
        ),
        "control_fields": _decision_control_coverage(text),
        "control_values": control_values,
        "management_handoff_items": items,
    }


def _decision_state_units(text: str) -> list[str]:
    units: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        fragments = [fragment.strip(" \t-・*") for fragment in re.split(r"[。！？!?]\s*", stripped)]
        units.extend(fragment for fragment in fragments if fragment)
    if not units and text.strip():
        return [_compact_snippet(text)]
    return units


def _decision_state_unit_declares_none(unit: str, terms: list[str]) -> bool:
    lower = unit.lower()
    none_terms = ("なし", "無し", "ない", "該当なし", "none", "n/a", "not applicable")
    for term in terms:
        pattern = rf"{re.escape(term.lower())}[^。\n]{{0,24}}[:：=\\-]\s*({'|'.join(re.escape(item) for item in none_terms)})"
        if re.search(pattern, lower):
            return True
    return False


def _decision_state_item(category: str, unit: str, control_values: dict[str, object] | None = None) -> dict[str, object]:
    kind, state = _decision_state_kind_and_state(category)
    excerpt = _compact_snippet(unit)
    controls = control_values or {}
    suggested_owner = _extract_labeled_value(unit, DECISION_STATE_CONTROL_TERMS["owner"]) or str(controls.get("owner", ""))
    needed_for = _extract_labeled_values(unit, DECISION_STATE_CONTROL_TERMS["needed_for"]) or list(controls.get("needed_for", []))
    blocking_status = _decision_blocking_status(unit)
    if blocking_status == "unknown":
        blocking_status = str(controls.get("blocking_status", "unknown"))
    review_at = _extract_labeled_value(unit, DECISION_STATE_CONTROL_TERMS["review_at"]) or str(controls.get("review_at", ""))
    return {
        "kind": kind,
        "uncertainty_kind": category,
        "decision_state": state,
        "source_excerpt": excerpt,
        "suggested_owner": suggested_owner,
        "needed_for": needed_for,
        "blocking_status": blocking_status,
        "next_action": _decision_next_action(category, unit, str(controls.get("next_action", ""))),
        "review_at": review_at,
    }


def _decision_state_kind_and_state(category: str) -> tuple[str, str]:
    mapping = {
        "pending_decision": ("unresolved_decision", "undecided"),
        "unknown": ("unknown", "unknown"),
        "hypothesis": ("hypothesis", "hypothesis"),
        "inference": ("inference", "inferred"),
        "one_sided_observation": ("one_sided_observation", "unknown"),
        "time_dependent": ("time_dependent_item", "pending"),
        "value_judgment": ("value_judgment", "pending"),
        "evidence_gap": ("evidence_gap", "needs_evidence"),
    }
    return mapping.get(category, ("uncertainty", "unknown"))


def _decision_blocking_status(unit: str) -> str:
    lower = unit.lower()
    if any(term in lower for term in ["not blocking", "non-blocking", "塞がない", "止めない", "遮断しない"]):
        return "not_blocking"
    if _has_any(unit, DECISION_STATE_CONTROL_TERMS["blocking_status"]):
        return "blocking"
    return "unknown"


def _decision_next_action(category: str, unit: str, fallback_explicit: str = "") -> str:
    explicit = _extract_labeled_value(unit, DECISION_STATE_CONTROL_TERMS["next_action"]) or fallback_explicit
    if explicit:
        return explicit
    defaults = {
        "pending_decision": "決定者、判断条件、期限を置く。",
        "unknown": "確認先と証拠取得方法を決める。",
        "hypothesis": "検証方法を定め、仮説のまま使う範囲を制限する。",
        "inference": "推測の根拠と反証条件を残す。",
        "one_sided_observation": "反対側または欠けた観測元を確認する。",
        "time_dependent": "再確認時点を置き、時点依存の根拠を更新する。",
        "value_judgment": "人間の判断点として判断基準を明示する。",
        "evidence_gap": "根拠となる一次証跡を取得する。",
    }
    return defaults.get(category, "管理対象として次行動を決める。")


def _extract_labeled_value(text: str, labels: Iterable[str]) -> str:
    for label in labels:
        match = re.search(rf"{re.escape(label)}\s*[:：=]\s*([^、。\n;；]+)", text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ""


def _extract_labeled_values(text: str, labels: Iterable[str]) -> list[str]:
    value = _extract_labeled_value(text, labels)
    if not value:
        return []
    return [item.strip() for item in re.split(r"[,，、/]+", value) if item.strip()]


def _decision_control_coverage(text: str) -> dict[str, bool]:
    return {field: _has_any(text, terms) for field, terms in DECISION_STATE_CONTROL_TERMS.items()}


def _decision_control_values(text: str) -> dict[str, object]:
    return {
        "owner": _extract_labeled_value(text, DECISION_STATE_CONTROL_TERMS["owner"]),
        "needed_for": _extract_labeled_values(text, DECISION_STATE_CONTROL_TERMS["needed_for"]),
        "blocking_status": _decision_blocking_status(text),
        "next_action": _extract_labeled_value(text, DECISION_STATE_CONTROL_TERMS["next_action"]),
        "review_at": _extract_labeled_value(text, DECISION_STATE_CONTROL_TERMS["review_at"]),
    }


def _unique_decision_state_items(items: list[dict[str, object]]) -> list[dict[str, object]]:
    unique: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()
    for item in items:
        key = (str(item["uncertainty_kind"]), str(item["source_excerpt"]))
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def _first_item_evidence(items: list[dict[str, object]], category: str) -> str:
    for item in items:
        if category and item.get("uncertainty_kind") != category:
            continue
        evidence = str(item.get("source_excerpt", ""))
        if evidence:
            return evidence
    return ""


def _combine(*parts: str) -> str:
    return "\n".join(part for part in parts if part)


def _normalize_input_kind(input_kind: str) -> str:
    normalized = (input_kind or "requirement").strip().lower().replace("_", "-")
    if normalized not in INPUT_KINDS:
        return "requirement"
    return normalized


def _has_any(text: str, needles: Iterable[str]) -> bool:
    lower = text.lower()
    return any(needle.lower() in lower for needle in needles)


def _compact_snippet(text: str, limit: int = DEFAULT_SNIPPET_LIMIT) -> str:
    cleaned = "\n".join(line.rstrip() for line in text.strip().splitlines())
    if len(cleaned) <= limit:
        return cleaned

    boundary_chars = ".!?。！？、，,;；:：)]}」』"
    cut = -1
    for index in range(limit - 1, max(0, limit // 2), -1):
        if cleaned[index] in boundary_chars or cleaned[index].isspace():
            cut = index + 1
            break
    if cut < 0:
        cut = limit

    return cleaned[:cut].rstrip() + "..."


def _blocker(category: str, finding: str, suggested_fix: str, basis: list[str]) -> Finding:
    return Finding(
        severity="blocker",
        category=category,
        basis=basis,
        finding=finding,
        suggested_fix=suggested_fix,
    )
