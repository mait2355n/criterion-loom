from __future__ import annotations

import re
from typing import Any

from semantic_guard.core import audit_diff, audit_plan, audit_request, finish_check
from semantic_guard.severity_profiles import apply_severity_profile


def build_trace_report(payload: dict[str, Any]) -> dict[str, object]:
    request = str(payload.get("request", ""))
    plan = str(payload.get("plan", ""))
    diff = str(payload.get("diff", ""))
    finish = str(payload.get("finish", ""))
    evidence = str(payload.get("evidence", ""))
    context = str(payload.get("context", ""))
    strict = bool(payload.get("strict", True))
    profile = str(payload.get("profile", "default"))
    manual_tags = payload.get("tags", {})
    vocabulary_profile = payload.get("vocabulary_profile", {})

    audits: dict[str, dict[str, Any]] = {}
    if request:
        audits["request"] = apply_severity_profile(audit_request(request, context=context, strict=strict), profile)
    if plan:
        audits["plan"] = apply_severity_profile(audit_plan(plan, request=request, context=context, strict=strict), profile)
    if diff:
        audits["diff"] = apply_severity_profile(audit_diff(diff, intent=plan or request, context=context, strict=strict), profile)
    if finish:
        audits["finish"] = apply_severity_profile(finish_check(finish, evidence=evidence, context=context, strict=strict), profile)

    segments = {
        "request": request,
        "plan": plan,
        "diff": diff,
        "finish": finish,
        "evidence": evidence,
    }
    vocabulary_decisions = _vocabulary_decisions(
        segments,
        profile_decisions=_vocabulary_profile_decisions(vocabulary_profile),
    )
    trace_tags = _trace_tag_map(
        segments,
        manual_tags=manual_tags,
        vocabulary_decisions=vocabulary_decisions,
    )
    links = _trace_links(
        request=request,
        plan=plan,
        diff=diff,
        finish=finish,
        evidence=evidence,
        audits=audits,
        trace_tags=trace_tags,
    )
    gaps = _trace_gaps(audits, links, request, plan, diff, finish)
    audit_status = _audit_status(audits)
    trace_status = _trace_gap_status(gaps)
    vocabulary_status = _vocabulary_status(vocabulary_decisions)
    status = _trace_status(audits, gaps)
    return {
        "phase": "trace_report",
        "status": status,
        "profile": profile,
        "audits": audits,
        "links": links,
        "gaps": gaps,
        "trace_tags": {segment: tags for segment, tags in trace_tags.items() if tags},
        "unresolved_terms": vocabulary_decisions["unresolved_terms"],
        "suggested_tags": vocabulary_decisions["suggested_tags"],
        "vocabulary_decisions": {
            "decisions": vocabulary_decisions["decisions"],
            "status_counts": vocabulary_decisions["status_counts"],
        },
        "summary": {
            "segment_count": len(audits),
            "gap_count": len(gaps),
            "link_count": len(links),
            "audit_status": audit_status,
            "trace_status": trace_status,
            "vocabulary_status": vocabulary_status,
            "aggregate_status_reason": _aggregate_status_reason(
                status=status,
                audit_status=audit_status,
                trace_status=trace_status,
                vocabulary_status=vocabulary_status,
            ),
            "trace_tag_count": sum(len(tags) for tags in trace_tags.values()),
            "ambiguity_reason_counts": _link_ambiguity_reason_counts(links),
            "unresolved_term_count": len(vocabulary_decisions["unresolved_terms"]),
            "suggested_tag_count": len(vocabulary_decisions["suggested_tags"]),
            "vocabulary_decision_counts": vocabulary_decisions["status_counts"],
        },
    }


def _trace_links(
    *,
    request: str,
    plan: str,
    diff: str,
    finish: str,
    evidence: str,
    audits: dict[str, dict[str, Any]],
    trace_tags: dict[str, list[dict[str, object]]],
) -> list[dict[str, object]]:
    links: list[dict[str, object]] = []
    if request and plan:
        links.append(
            _overlap_link(
                "request",
                "plan",
                request,
                plan,
                trace_tags.get("request", []),
                trace_tags.get("plan", []),
            )
        )
    if plan and diff:
        diff_files = audits.get("diff", {}).get("details", {}).get("changed_files", [])
        links.append(
            {
                **_overlap_link(
                    "plan",
                    "diff",
                    plan,
                    diff,
                    trace_tags.get("plan", []),
                    trace_tags.get("diff", []),
                ),
                "changed_files": diff_files,
            }
        )
    if diff and finish:
        links.append(
            _overlap_link(
                "diff",
                "finish",
                diff,
                finish + "\n" + evidence,
                trace_tags.get("diff", []),
                _merge_trace_tags(trace_tags.get("finish", []), trace_tags.get("evidence", [])),
            )
        )
    if request and finish:
        links.append(
            _overlap_link(
                "request",
                "finish",
                request,
                finish + "\n" + evidence,
                trace_tags.get("request", []),
                _merge_trace_tags(trace_tags.get("finish", []), trace_tags.get("evidence", [])),
            )
        )
    return links


def _overlap_link(
    source: str,
    target: str,
    left: str,
    right: str,
    left_tags: list[dict[str, object]] | None = None,
    right_tags: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    left_tokens = _tokens(left)
    right_tokens = _tokens(right)
    shared = sorted((left_tokens & right_tokens) - _STOP_TOKENS)
    raw_strength = "strong" if len(shared) >= 6 else "medium" if len(shared) >= 3 else "weak"
    shared_tags = sorted(_tag_names(left_tags or []) & _tag_names(right_tags or []))
    tag_strength = _tag_strength(shared_tags)
    strength = _stronger_strength(raw_strength, tag_strength)
    ambiguity_reasons: list[str] = []
    if raw_strength == "weak" and tag_strength in {"medium", "strong"}:
        ambiguity_reasons.append("trace_vocabulary_gap")

    match_status = _link_match_status(
        strength=strength,
        raw_strength=raw_strength,
        tag_strength=tag_strength,
    )
    confidence = _link_confidence(
        strength=strength,
        raw_strength=raw_strength,
        tag_strength=tag_strength,
    )
    return {
        "from": source,
        "to": target,
        "kind": "vocabulary_overlap",
        "strength": strength,
        "raw_strength": raw_strength,
        "tag_strength": tag_strength,
        "shared_terms": shared[:20],
        "shared_tags": shared_tags[:20],
        "match_status": match_status,
        "confidence": confidence,
        "ambiguity_reasons": ambiguity_reasons,
    }


def _trace_gaps(
    audits: dict[str, dict[str, Any]],
    links: list[dict[str, object]],
    request: str,
    plan: str,
    diff: str,
    finish: str,
) -> list[dict[str, object]]:
    gaps: list[dict[str, object]] = []
    if request and "plan" not in audits:
        gaps.append({"kind": "missing_segment", "segment": "plan", "message": "要求に対する計画がない。"})
    if plan and "finish" not in audits:
        gaps.append({"kind": "missing_segment", "segment": "finish", "message": "計画に対する完了証拠がない。"})
    if diff and "finish" not in audits:
        gaps.append({"kind": "missing_segment", "segment": "finish", "message": "差分に対する完了確認がない。"})

    for name, audit in audits.items():
        if audit.get("status") == "block":
            gaps.append({"kind": "blocked_audit", "segment": name, "message": "監査が block を返している。"})

    for link in links:
        if link["strength"] == "weak":
            gaps.append(
                {
                    "kind": "weak_trace",
                    "from": link["from"],
                    "to": link["to"],
                    "message": "語彙接続が弱く、追跡関係が薄い。",
                }
            )
    return gaps


def _trace_status(audits: dict[str, dict[str, Any]], gaps: list[dict[str, object]]) -> str:
    if any(audit.get("status") == "block" for audit in audits.values()):
        return "block"
    if gaps or any(audit.get("status") == "warn" for audit in audits.values()):
        return "warn"
    return "pass"


def _audit_status(audits: dict[str, dict[str, Any]]) -> str:
    if any(audit.get("status") == "block" for audit in audits.values()):
        return "block"
    if any(audit.get("status") == "warn" for audit in audits.values()):
        return "warn"
    return "pass"


def _trace_gap_status(gaps: list[dict[str, object]]) -> str:
    trace_gaps = [gap for gap in gaps if gap.get("kind") in {"missing_segment", "weak_trace"}]
    return "warn" if trace_gaps else "pass"


def _vocabulary_status(vocabulary_decisions: dict[str, object]) -> str:
    unresolved = vocabulary_decisions.get("unresolved_terms", [])
    return "warn" if isinstance(unresolved, list) and unresolved else "pass"


def _aggregate_status_reason(*, status: str, audit_status: str, trace_status: str, vocabulary_status: str) -> str:
    if status == "block":
        return "embedded audit returned block"
    if audit_status == "warn":
        return "embedded audit returned warn"
    if trace_status == "warn":
        return "trace gaps are present"
    if vocabulary_status == "warn":
        return "embedded audits and trace links pass; vocabulary suggestions are advisory"
    return "all embedded audits and trace links pass"


def _tokens(text: str) -> set[str]:
    lowered = text.lower()
    ascii_tokens = re.findall(r"[a-z0-9_./:-]{2,}", lowered)
    japanese_tokens = re.findall(r"[一-龯ぁ-んァ-ヶー]{2,}", text)
    return set(ascii_tokens + japanese_tokens)


def _trace_tag_map(
    segments: dict[str, str],
    *,
    manual_tags: object,
    vocabulary_decisions: dict[str, object],
) -> dict[str, list[dict[str, object]]]:
    payload_tags = manual_tags if isinstance(manual_tags, dict) else {}
    return {
        segment: _merge_trace_tags(
            _extract_trace_tags(text),
            _manual_trace_tags(segment, payload_tags),
            _accepted_vocabulary_tags(segment, vocabulary_decisions),
        )
        for segment, text in segments.items()
    }


def _extract_trace_tags(text: str) -> list[dict[str, object]]:
    found: dict[str, dict[str, object]] = {}
    for raw_tag in _explicit_tags(text):
        _add_trace_tag(
            found,
            tag=_canonical_tag(raw_tag),
            source_term=raw_tag,
            matched_by="explicit_tag",
            confidence="high",
        )

    for canonical, aliases in _TRACE_TAG_ALIASES.items():
        for alias in aliases:
            if _contains_term(text, alias):
                _add_trace_tag(
                    found,
                    tag=canonical,
                    source_term=alias,
                    matched_by="alias",
                    confidence="high" if _looks_like_label(text, alias) else "medium",
                )

    return _sorted_trace_tags(found)


def _explicit_tags(text: str) -> list[str]:
    tags: list[str] = []
    tags.extend(match.group(1) for match in re.finditer(r"(?<![\w/])#([A-Za-z0-9_.:-]{2,})", text))
    tags.extend(match.group(1) for match in re.finditer(r"(?<!\S)/([^/\s]{2,})/(?!\S)", text))
    for match in re.finditer(r"\b(?:tags?|trace_tags?)\s*[:=]\s*([^\n;]+)", text, re.IGNORECASE):
        tags.extend(part.strip() for part in re.split(r"[, ]+", match.group(1)) if part.strip())
    return tags


def _manual_trace_tags(segment: str, payload_tags: dict[object, object]) -> list[dict[str, object]]:
    value = payload_tags.get(segment, [])
    if isinstance(value, dict):
        value = value.get("tags", [])
    if isinstance(value, str):
        items: list[object] = [part for part in re.split(r"[, ]+", value) if part]
    elif isinstance(value, list):
        items = value
    else:
        items = []

    found: dict[str, dict[str, object]] = {}
    for item in items:
        if isinstance(item, dict):
            raw_tag = str(item.get("tag", ""))
            source_term = str(item.get("source", raw_tag))
        else:
            raw_tag = str(item)
            source_term = raw_tag
        if raw_tag:
            _add_trace_tag(
                found,
                tag=_canonical_tag(raw_tag),
                source_term=source_term,
                matched_by="payload_tag",
                confidence="high",
            )
    return _sorted_trace_tags(found)


def _accepted_vocabulary_tags(segment: str, vocabulary_decisions: dict[str, object]) -> list[dict[str, object]]:
    found: dict[str, dict[str, object]] = {}
    for entry in vocabulary_decisions.get("decisions", []):
        if not isinstance(entry, dict):
            continue
        if entry.get("segment") != segment or entry.get("status") != "accepted":
            continue
        tag = str(entry.get("accepted_tag", ""))
        if not tag:
            continue
        _add_trace_tag(
            found,
            tag=tag,
            source_term=str(entry.get("term", "")),
            matched_by="vocabulary_profile",
            confidence="high",
        )
    return _sorted_trace_tags(found)


def _add_trace_tag(
    found: dict[str, dict[str, object]],
    *,
    tag: str,
    source_term: str,
    matched_by: str,
    confidence: str,
) -> None:
    if not tag:
        return
    current = found.setdefault(
        tag,
        {
            "tag": tag,
            "confidence": confidence,
            "matched_by": [],
            "source_terms": [],
        },
    )
    if _CONFIDENCE_RANK[confidence] > _CONFIDENCE_RANK[str(current["confidence"])]:
        current["confidence"] = confidence
    if matched_by not in current["matched_by"]:
        current["matched_by"].append(matched_by)
    if source_term and source_term not in current["source_terms"]:
        current["source_terms"].append(source_term)


def _sorted_trace_tags(found: dict[str, dict[str, object]]) -> list[dict[str, object]]:
    return [found[tag] for tag in sorted(found)]


def _merge_trace_tags(*groups: list[dict[str, object]]) -> list[dict[str, object]]:
    found: dict[str, dict[str, object]] = {}
    for group in groups:
        for entry in group:
            tag = str(entry.get("tag", ""))
            if not tag:
                continue
            merged = found.setdefault(
                tag,
                {
                    "tag": tag,
                    "confidence": str(entry.get("confidence", "medium")),
                    "matched_by": [],
                    "source_terms": [],
                },
            )
            confidence = str(entry.get("confidence", "medium"))
            if _CONFIDENCE_RANK.get(confidence, 1) > _CONFIDENCE_RANK.get(str(merged["confidence"]), 1):
                merged["confidence"] = confidence
            for key in ("matched_by", "source_terms"):
                for item in entry.get(key, []):
                    if item not in merged[key]:
                        merged[key].append(item)
    return _sorted_trace_tags(found)


def _vocabulary_profile_decisions(profile: object) -> dict[str, dict[str, str]]:
    if not isinstance(profile, dict):
        return {}

    decisions: dict[str, dict[str, str]] = {}
    for entry in _profile_entries(profile.get("terms", []), default_status="needs_decision"):
        _store_profile_decision(decisions, entry)

    for key, status in (
        ("accepted", "accepted"),
        ("accepted_terms", "accepted"),
        ("rejected", "rejected"),
        ("rejected_terms", "rejected"),
        ("deferred", "deferred"),
        ("deferred_terms", "deferred"),
    ):
        for entry in _profile_entries(profile.get(key, []), default_status=status):
            _store_profile_decision(decisions, entry)

    return decisions


def _profile_entries(value: object, *, default_status: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    if isinstance(value, dict):
        iterable: list[object] = [{"term": term, "tag": tag} for term, tag in value.items()]
    elif isinstance(value, list):
        iterable = value
    elif isinstance(value, str):
        iterable = [part for part in re.split(r"[,;]", value) if part.strip()]
    else:
        iterable = []

    for item in iterable:
        if isinstance(item, dict):
            term = str(item.get("term", "") or item.get("source", ""))
            tag = str(item.get("tag", "") or item.get("accepted_tag", ""))
            status = _normalize_vocabulary_status(str(item.get("status", default_status)))
        else:
            term = str(item)
            tag = ""
            status = _normalize_vocabulary_status(default_status)
        if term:
            entries.append({"term": term, "tag": tag, "status": status})
    return entries


def _store_profile_decision(decisions: dict[str, dict[str, str]], entry: dict[str, str]) -> None:
    term = entry["term"]
    decisions[_normalize_term_key(term)] = {
        "term": term,
        "tag": entry.get("tag", ""),
        "status": _normalize_vocabulary_status(entry.get("status", "")),
    }


def _normalize_vocabulary_status(status: str) -> str:
    normalized = status.strip().lower().replace("-", "_")
    if normalized in {"accept", "accepted"}:
        return "accepted"
    if normalized in {"reject", "rejected"}:
        return "rejected"
    if normalized in {"defer", "deferred", "pending"}:
        return "deferred"
    return "needs_decision"


def _vocabulary_decisions(
    segments: dict[str, str],
    *,
    profile_decisions: dict[str, dict[str, str]],
) -> dict[str, object]:
    decisions: list[dict[str, object]] = []
    for segment, text in segments.items():
        if not text:
            continue
        for term, suggestion in _DOMAIN_TERM_SUGGESTIONS.items():
            if not _contains_term(text, term):
                continue
            profile_entry = profile_decisions.get(_normalize_term_key(term), {})
            status = _normalize_vocabulary_status(profile_entry.get("status", "needs_decision"))
            suggested_tag = profile_entry.get("tag") or str(suggestion["tag"])
            entry: dict[str, object] = {
                "segment": segment,
                "term": term,
                "status": status,
                "reason": "domain_specific_term",
                "suggested_tags": [
                    {
                        "tag": suggested_tag,
                        "confidence": suggestion.get("confidence", "medium"),
                        "basis": "known_domain_term",
                        "domain": suggestion["domain"],
                    }
                ],
            }
            if status == "accepted":
                entry["accepted_tag"] = suggested_tag
            decisions.append(entry)

    decisions.sort(key=lambda entry: (str(entry["segment"]), str(entry["term"])))
    return {
        "decisions": decisions,
        "unresolved_terms": [
            entry for entry in decisions if entry.get("status") in {"needs_decision", "deferred"}
        ],
        "suggested_tags": _suggested_tag_summary(decisions),
        "status_counts": _vocabulary_status_counts(decisions),
    }


def _suggested_tag_summary(decisions: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str], dict[str, object]] = {}
    for entry in decisions:
        status = str(entry.get("status", "needs_decision"))
        if status == "accepted":
            continue
        for suggestion in entry.get("suggested_tags", []):
            if not isinstance(suggestion, dict):
                continue
            tag = str(suggestion.get("tag", ""))
            if not tag:
                continue
            key = (tag, status)
            summary = grouped.setdefault(
                key,
                {
                    "tag": tag,
                    "status": status,
                    "terms": [],
                    "segments": [],
                    "domain": suggestion.get("domain", ""),
                    "confidence": suggestion.get("confidence", "medium"),
                },
            )
            term = str(entry.get("term", ""))
            segment = str(entry.get("segment", ""))
            if term and term not in summary["terms"]:
                summary["terms"].append(term)
            if segment and segment not in summary["segments"]:
                summary["segments"].append(segment)
    return sorted(grouped.values(), key=lambda item: (str(item["tag"]), str(item["status"])))


def _vocabulary_status_counts(decisions: list[dict[str, object]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for entry in decisions:
        status = str(entry.get("status", "needs_decision"))
        counts[status] = counts.get(status, 0) + 1
    return dict(sorted(counts.items()))


def _canonical_tag(raw_tag: str) -> str:
    key = _normalize_tag_key(raw_tag)
    return _TAG_CANONICALS.get(key, key)


def _normalize_term_key(value: str) -> str:
    return _normalize_tag_key(value)


def _normalize_tag_key(value: str) -> str:
    key = value.strip().strip("#/[](){}").lower()
    key = key.replace("-", "_").replace(" ", "_")
    key = re.sub(r"[^\w.:-]+", "_", key, flags=re.UNICODE)
    key = re.sub(r"_+", "_", key)
    return key.strip("_")


def _contains_term(text: str, term: str) -> bool:
    if _ascii_like(term):
        pattern = rf"(?<![a-z0-9_]){re.escape(term.lower())}(?![a-z0-9_])"
        return re.search(pattern, text.lower()) is not None
    return term in text


def _looks_like_label(text: str, term: str) -> bool:
    if _ascii_like(term):
        return re.search(rf"{re.escape(term.lower())}\s*[:：]", text.lower()) is not None
    return re.search(rf"{re.escape(term)}\s*[:：]", text) is not None


def _ascii_like(term: str) -> bool:
    return re.fullmatch(r"[A-Za-z0-9_.:/ -]+", term) is not None


def _tag_names(tags: list[dict[str, object]]) -> set[str]:
    return {str(tag.get("tag")) for tag in tags if tag.get("tag")}


def _tag_strength(shared_tags: list[str]) -> str:
    if len(shared_tags) >= 4:
        return "strong"
    if len(shared_tags) >= 2:
        return "medium"
    if shared_tags:
        return "weak"
    return "none"


def _stronger_strength(raw_strength: str, tag_strength: str) -> str:
    if raw_strength == "weak" and tag_strength in {"medium", "strong"}:
        return "medium"
    return max((raw_strength, tag_strength), key=lambda value: _STRENGTH_RANK[value])


def _link_match_status(*, strength: str, raw_strength: str, tag_strength: str) -> str:
    if raw_strength == "strong" or (raw_strength == "medium" and tag_strength in {"medium", "strong"}):
        return "matched"
    if strength in {"medium", "strong"}:
        return "partial"
    return "unknown"


def _link_confidence(*, strength: str, raw_strength: str, tag_strength: str) -> str:
    if raw_strength == "strong" or (raw_strength == "medium" and tag_strength == "strong"):
        return "high"
    if strength in {"medium", "strong"}:
        return "medium"
    return "low"


def _link_ambiguity_reason_counts(links: list[dict[str, object]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for link in links:
        for reason in link.get("ambiguity_reasons", []):
            key = str(reason)
            counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


_STOP_TOKENS = {
    "する",
    "した",
    "こと",
    "ため",
    "なし",
    "あり",
    "the",
    "and",
    "for",
    "with",
    "from",
    "this",
    "that",
}


_STRENGTH_RANK = {
    "none": 0,
    "weak": 1,
    "medium": 2,
    "strong": 3,
}


_CONFIDENCE_RANK = {
    "low": 0,
    "medium": 1,
    "high": 2,
}


_DOMAIN_TERM_SUGGESTIONS: dict[str, dict[str, str]] = {
    "match_status": {"tag": "sg.match_status", "domain": "semantic-guard", "confidence": "high"},
    "candidate_matches": {"tag": "sg.candidate_matches", "domain": "semantic-guard", "confidence": "high"},
    "review-if-needed": {"tag": "sg.review_if_needed", "domain": "semantic-guard", "confidence": "high"},
    "trace_vocabulary_gap": {"tag": "sg.trace_vocabulary_gap", "domain": "semantic-guard", "confidence": "high"},
    "semantic_boundaries": {"tag": "sg.semantic_boundaries", "domain": "semantic-guard", "confidence": "high"},
    "ビード": {"tag": "rs.bead", "domain": "releasable-strand", "confidence": "medium"},
    "ストランド": {"tag": "rs.strand", "domain": "releasable-strand", "confidence": "medium"},
    "主観時間": {"tag": "rs.subjective_time", "domain": "releasable-strand", "confidence": "medium"},
    "世界時間": {"tag": "rs.world_time", "domain": "releasable-strand", "confidence": "medium"},
    "エッジ": {"tag": "rs.edge", "domain": "releasable-strand", "confidence": "medium"},
    "shared bead": {"tag": "rs.shared_bead", "domain": "releasable-strand", "confidence": "medium"},
    "collapsed strand": {"tag": "rs.collapsed_strand", "domain": "releasable-strand", "confidence": "medium"},
}


_TRACE_TAG_ALIASES = {
    "acceptance": [
        "受入条件",
        "受け入れ条件",
        "完了条件",
        "達成条件",
        "acceptance criteria",
        "acceptance condition",
        "achievement condition",
        "completion condition",
        "definition of done",
        "done when",
    ],
    "change_control": ["変更統制", "change control"],
    "configuration": ["設定", "config", "configuration"],
    "deliverable": ["成果物", "deliverable", "artifact"],
    "evidence": ["証拠", "根拠", "実行結果", "コマンド結果", "evidence", "proof"],
    "interface_contract": ["入力項目", "interface contract", "api", "cli", "mcp", "command"],
    "non_goal": ["対象外", "非対象", "non-goal", "non goal", "out of scope"],
    "objective": ["目的", "目標", "狙い", "goal", "objective", "intent"],
    "output_contract": [
        "出力項目",
        "出力契約",
        "公開契約",
        "output contract",
        "output fields",
        "return fields",
        "json summary",
        "metrics",
    ],
    "quality": ["品質", "quality", "performance", "compatibility"],
    "risk": ["リスク", "残リスク", "risk", "residual risk"],
    "rollback": ["戻し方", "rollback", "recovery", "backout"],
    "security": ["安全", "権限", "security", "credential", "secret"],
    "traceability": ["追跡", "追跡性", "trace", "traceability", "trace-report", "trace report"],
    "validation": ["妥当性", "妥当性確認", "判断主体", "validation", "validate"],
    "verification": ["検証", "検証方法", "確認方法", "試験", "テスト", "unittest", "compileall", "verification", "verify"],
    "vocabulary": ["語彙", "vocabulary", "alias", "synonym", "normalization"],
    "work_breakdown": ["作業分解", "work breakdown", "work package decomposition", "wbs"],
}


_TAG_CANONICALS = {
    _normalize_tag_key(alias): canonical
    for canonical, aliases in _TRACE_TAG_ALIASES.items()
    for alias in [canonical, *aliases]
}
