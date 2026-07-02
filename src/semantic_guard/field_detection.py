from __future__ import annotations

import re

from semantic_guard.matching import FieldMatchDiagnostic, diagnose_field_match
from semantic_guard.models import Finding
from semantic_guard.text_utils import first_match, strip_code_blocks, unique_nonempty

FIELD_CANDIDATE_HINTS: dict[str, list[str]] = {
    "objective": ["背景", "狙い", "到達点", "期待結果", "何をする"],
    "purpose_trace": ["背景", "理由", "狙い", "課題", "困りごと"],
    "non_goals": ["除外", "非対象", "範囲外", "今回は", "やらないこと"],
    "non_requirements": ["除外", "範囲外", "今回は", "やらないこと"],
    "stakeholder_source": ["利用者", "受入者", "依頼元", "関係者", "誰のため"],
    "quality_constraint": ["指標", "閾値", "測定", "許容", "性能条件"],
    "priority": ["優先", "重要度", "順序", "先に", "後で"],
    "uncertainty_classification": ["未確定", "仮説", "判断待ち", "保留", "片側観測"],
    "deliverables": ["納品", "作るもの", "更新対象", "変更対象"],
    "work_breakdown": ["進め方", "工程", "作業列", "段階", "着手順", "work package decomposition", "work package"],
    "dependencies": ["必要条件", "先行条件", "前提条件", "依存先"],
    "risks": ["懸念", "注意", "怖い点", "失敗時"],
    "verification_plan": ["検査", "点検", "動作確認", "試す", "見る"],
    "verification_or_acceptance": ["検査", "点検", "動作確認", "試す", "見る"],
    "validation_plan": ["受入基準", "合格条件", "目的適合", "人間確認"],
    "rollback_or_recovery": ["切戻し", "戻し方", "退避先", "復元"],
    "completion_evidence": ["証跡", "根拠", "ログ", "実行結果", "確認結果"],
    "unknowns_or_decisions": ["未決", "判断点", "確認待ち", "決めること", "不明点"],
    "unknowns": ["未決", "判断点", "確認待ち", "決めること", "不明点"],
    "validation_owner": ["判断主体", "受入者", "承認者", "誰が", "人間確認"],
    "progress_control": ["進捗", "確認点", "中間", "節目", "状態報告"],
    "change_control": ["変更統制", "範囲変更", "追加要求", "逸脱", "判断点"],
    "work_package_decomposition": ["作業分解", "作業パッケージ", "成果物分解", "WBS", "担当別", "ファイル別"],
    "dependency_sequence": ["順序", "先行", "後続", "前後関係", "依存関係", "critical path"],
    "estimation_or_resource_basis": ["見積", "工数", "所要時間", "資源", "担当", "capacity", "duration"],
    "risk_response": ["対策", "緩和", "回避", "代替", "退避", "contingency", "fallback"],
    "control_baseline": ["基準線", "基準", "指標", "閾値", "milestone", "baseline", "判定基準"],
    "decision_gate": ["決定点", "判断ゲート", "承認", "停止条件", "go/no-go", "継続判断"],
}


def missing_field_finding(
    *,
    field: str,
    patterns: list[str],
    text: str,
    severity: str,
    category: str,
    basis: list[str],
    finding: str,
    suggested_fix: str,
    needs_human_decision: bool = False,
    diagnostic: FieldMatchDiagnostic | None = None,
) -> Finding:
    direct_evidence = excerpt_for_field(text, patterns)
    diagnostic = diagnostic or field_match_diagnostic(text, field, patterns)
    candidates = diagnostic.nearest_candidates
    ambiguity_reasons = diagnostic.ambiguity_reasons
    return Finding(
        severity=severity,  # type: ignore[arg-type]
        category=category,
        basis=basis,
        finding=finding,
        evidence=direct_evidence or (candidates[0] if candidates else ""),
        suggested_fix=suggested_fix,
        needs_human_decision=needs_human_decision,
        warning_class="possible false positive" if candidates else "actionable",
        nearest_candidates=candidates,
        match_status=diagnostic.match_status,
        confidence=diagnostic.confidence,
        ambiguity_reasons=ambiguity_reasons,
        candidate_matches=diagnostic.candidate_matches,
    )


def field_match_diagnostic(text: str, field: str, patterns: list[str]) -> FieldMatchDiagnostic:
    return diagnose_field_match(
        text,
        field,
        patterns,
        weak_hints=FIELD_CANDIDATE_HINTS.get(field, []),
    )


def nearest_candidates(text: str, field: str, patterns: list[str], limit: int = 2) -> list[str]:
    lines = candidate_lines(text)
    if not lines:
        return []

    field_tokens = _tokens(field.replace("_", " "))
    hints = FIELD_CANDIDATE_HINTS.get(field, []) + patterns
    scored: list[tuple[int, str]] = []
    for line in lines:
        lower = line.lower()
        tokens = _tokens(line)
        score = len((tokens & field_tokens) - {"or", "and"})
        for hint in hints:
            if hint.lower() in lower:
                score += 3
        if re.match(r"^\s*(#{1,4}|\d+[.)]|[-*])?\s*[^:：]{1,24}[:：]", line):
            score += 1
        if score > 0:
            scored.append((score, line.strip()[:220]))

    if scored:
        scored.sort(key=lambda item: (-item[0], len(item[1])))
        return unique_nonempty([line for _, line in scored[:limit]])

    heading_like = [
        line.strip()[:220]
        for line in lines
        if re.match(r"^\s*(#{1,4}\s+|[-*]\s+|\d+[.)]\s+)?[^:：]{1,28}[:：]", line)
    ]
    return unique_nonempty(heading_like[:limit])


def candidate_lines(text: str) -> list[str]:
    stripped = strip_code_blocks(text)
    raw_lines = [line.strip() for line in stripped.splitlines()]
    lines = [line for line in raw_lines if line and not line.startswith("|")]
    structured = [
        line
        for line in lines
        if re.match(r"^\s*(#{1,4}\s+|[-*]\s+|\d+[.)]\s+)?\S", line)
        and (":" in line or "：" in line or line.startswith(("#", "-", "*")) or len(line) <= 90)
    ]
    if structured:
        return structured[:80]
    return [sentence.strip() for sentence in re.split(r"(?<=[.!?。])\s+|\n+", stripped) if sentence.strip()][:80]


def score_field(text: str, patterns: list[str]) -> int:
    if not text.strip():
        return 0
    hits = sum(1 for pattern in patterns if pattern.lower() in text.lower())
    if hits == 0:
        return 0
    if has_heading_hit(text, patterns):
        return 4
    if hits == 1:
        return 2
    if re.search(r"(/Users/|[\w.-]+:\d+|`[^`]+`|https?://|実行|確認済み|verified)", text, re.I):
        return 4
    return 3


def has_heading_hit(text: str, patterns: list[str]) -> bool:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        heading_like = bool(re.match(r"^(#{1,4}\s+|[-*]\s+|\d+[.)]\s+)?[^:：]{1,32}[:：]", stripped))
        markdown_heading = stripped.startswith("#")
        if not (heading_like or markdown_heading):
            continue
        prefix = stripped.split(":", 1)[0].split("：", 1)[0]
        if any(pattern.lower() in prefix.lower() for pattern in patterns):
            return True
    return False


def excerpt_for_field(text: str, patterns: list[str]) -> str:
    return first_match(text, patterns)


def _tokens(text: str) -> set[str]:
    return {token.lower() for token in re.findall(r"[A-Za-z0-9_一-龯ぁ-んァ-ヶー]{2,}", text)}
