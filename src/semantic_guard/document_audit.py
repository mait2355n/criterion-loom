from __future__ import annotations

import re

from semantic_guard.field_detection import (
    missing_field_finding as _missing_field_finding,
    score_field as _score_field,
)
from semantic_guard.models import Finding
from semantic_guard.result_builder import (
    build_result,
    next_actions as _next_actions,
    score_from_findings as _score_from_findings,
)
from semantic_guard.text_utils import (
    combine as _combine,
    compact_code_snippet as _compact_code_snippet,
    compact_snippet as _compact_snippet,
    has_any as _has_any,
    strip_code_blocks as _strip_code_blocks,
    unique_nonempty as _unique_nonempty,
)

REQUIREMENTS_BASIS = ["ISO/IEC/IEEE 29148", "BABOK", "NASA SEH"]
MEANING_BASIS = ["semantic-implementation"]


def audit_document(text: str, context: str = "", strict: bool = True, input_kind: str = "document") -> dict[str, object]:
    combined = _combine(text, context)
    findings: list[Finding] = []
    missing: list[str] = []
    fields = {
        "purpose_or_overview": ["purpose", "overview", "what", "目的", "概要", "要旨", "何", "狙い", "位置づけ"],
        "audience_or_use": ["when to use", "use when", "audience", "reader", "読者", "利用者", "使いどころ", "用途", "誰"],
        "status_or_scope": ["status", "scope", "prototype", "alpha", "状態", "範囲", "試作", "現状", "適用範囲"],
        "usage_or_examples": ["usage", "example", "cli", "mcp", "使い方", "使用法", "例", "実行例", "設定"],
        "output_or_contract": ["output", "json", "schema", "contract", "出力", "契約", "構造", "返却", "項目"],
        "limitations_or_non_goals": ["limitations", "do not", "not ", "non-goal", "out of scope", "制限", "限界", "対象外", "しない", "非目標"],
    }
    critical = {"purpose_or_overview", "usage_or_examples", "limitations_or_non_goals"}
    field_scores = {field: _score_field(combined, patterns) for field, patterns in fields.items()}

    if not text.strip():
        findings.append(_blocker("clarity", "文書本文が空。", "文書本文を渡す。", REQUIREMENTS_BASIS))
        missing.append("document_text")

    for field, score in field_scores.items():
        patterns = fields[field]
        if score == 0:
            missing.append(field)
            findings.append(
                _missing_field_finding(
                    field=field,
                    patterns=patterns,
                    text=combined,
                    severity="major" if strict and field in critical else "info",
                    category="documentation",
                    basis=REQUIREMENTS_BASIS + MEANING_BASIS,
                    finding=f"文書監査項目 `{field}` が見えない。",
                    suggested_fix=f"`{field}` に相当する節や説明を足す。",
                )
            )

    document_checks = _document_validity_checks(combined, findings, missing)
    claim_triples = _document_claim_triples(combined, findings)
    document_claim_summary = _document_claim_summary(claim_triples)
    coverage_score = sum(field_scores.values()) / (4 * len(field_scores)) if field_scores else 0.0
    return build_result(
        phase="audit_request",
        findings=findings,
        missing=sorted(set(missing)),
        score=min(coverage_score, _score_from_findings(findings)),
        details={
            "input_kind": input_kind,
            "document_field_scores": field_scores,
            "document_checks": document_checks,
            "claim_triples": claim_triples,
            "document_claim_summary": document_claim_summary,
        },
        next_actions=_next_actions(findings, "文書の目的、使い方、制限、出力契約を補う。"),
    )


def _document_validity_checks(text: str, findings: list[Finding], missing: list[str]) -> dict[str, object]:
    checks = {
        "has_headings": bool(re.search(r"(?m)^\s*#{1,3}\s+\S+", text)),
        "has_code_examples": "```" in text,
        "has_output_contract_terms": _has_any(text, ["status", "score", "findings", "missing", "next_actions", "details"]),
        "has_limitations": _has_any(text, ["limitations", "制限", "does not", "do not", "not ", "対象外", "しない"]),
        "has_implementation_evidence": _has_implementation_evidence(text),
        "no_implementation_evidence_available": False,
        "overclaim_count": 0,
    }
    checks["no_implementation_evidence_available"] = not checks["has_implementation_evidence"]

    if not checks["has_headings"]:
        findings.append(
            Finding(
                severity="minor",
                category="documentation",
                basis=REQUIREMENTS_BASIS + MEANING_BASIS,
                finding="文書に見出し構造が見えない。",
                suggested_fix="読み手が走査できるように、目的、使い方、制限などを見出しで分ける。",
            )
        )

    if _has_any(text, ["cli", "mcp", "command", "run", "usage", "使い方"]) and not checks["has_code_examples"]:
        findings.append(
            Finding(
                severity="minor",
                category="documentation",
                basis=REQUIREMENTS_BASIS,
                finding="使い方を述べているが、実行例やコードブロックが見えない。",
                suggested_fix="少なくとも一つ、再現可能なコマンド例または設定例を追加する。",
            )
        )
        missing.append("executable_example")

    if _has_any(text, ["json", "output", "schema", "contract", "出力", "契約"]) and not checks["has_output_contract_terms"]:
        findings.append(
            Finding(
                severity="minor",
                category="documentation",
                basis=REQUIREMENTS_BASIS,
                finding="出力契約に触れているが、返却項目の説明が薄い。",
                suggested_fix="`status`, `score`, `findings`, `missing`, `next_actions`, `details` などの主要項目を明示する。",
            )
        )
        missing.append("output_contract_terms")

    overclaims = _document_overclaim_sentences(text)
    checks["overclaim_count"] = len(overclaims)
    for sentence in overclaims[:3]:
        document_only = not checks["has_implementation_evidence"]
        findings.append(
            Finding(
                severity="major",
                category="evidence",
                basis=REQUIREMENTS_BASIS + MEANING_BASIS,
                finding=(
                    "文書が強い完成度・安全性・正確性を主張しているが、文書内の実装証拠では支えられていない可能性がある。"
                    if document_only
                    else "文書が強い完成度・安全性・正確性を主張しているが、制限や証拠で支えられていない可能性がある。"
                ),
                evidence=sentence,
                suggested_fix=(
                    "文書だけでは実行時正しさを証明できないため、検証範囲、未証明範囲、または実装証拠が無い状態を明示する。"
                    if document_only
                    else "試作、制限、検証範囲、残リスク、根拠を明示するか、主張を弱める。"
                ),
                warning_class="generic caution" if document_only else "actionable",
            )
        )

    return checks


def _document_claim_triples(text: str, findings: list[Finding]) -> list[dict[str, object]]:
    blocks = _document_blocks(text)
    triples: list[dict[str, object]] = []
    for heading, block_text in blocks:
        evidence = _evidence_snippets(block_text)
        limitations = _limitation_snippets(block_text)
        for claim in _claim_sentences(block_text):
            strong = _is_strong_claim(claim)
            triple = {
                "section": heading,
                "claim": claim,
                "evidence": evidence[:2],
                "limitations": limitations[:2],
                "support": "supported" if evidence else "limited" if limitations else "unsupported",
                "strong": strong,
            }
            triples.append(triple)
            if strong and not evidence and not limitations and not _is_negated_or_scoped_claim(claim):
                findings.append(
                    Finding(
                        severity="major",
                        category="evidence",
                        basis=REQUIREMENTS_BASIS + MEANING_BASIS,
                        finding="文書内の強い主張に対応する証拠または制限が見えない。文書だけでは実行時正しさまでは証明できない。",
                        evidence=claim,
                        suggested_fix="同じ節に、実行例、検証結果、制限、未証明範囲、または主張を弱める説明を足す。",
                        warning_class="generic caution",
                    )
                )
    return triples[:20]


def _document_claim_summary(claim_triples: list[dict[str, object]]) -> dict[str, object]:
    support_counts = {"supported": 0, "limited": 0, "unsupported": 0}
    strong_counts = {"supported": 0, "limited": 0, "unsupported": 0}
    for triple in claim_triples:
        support = str(triple.get("support", "unsupported"))
        if support not in support_counts:
            support = "unsupported"
        support_counts[support] += 1
        if triple.get("strong"):
            strong_counts[support] += 1
    return {
        "claim_count": len(claim_triples),
        "support_counts": support_counts,
        "strong_support_counts": strong_counts,
        "unsupported_count": support_counts["unsupported"],
        "strong_unsupported_count": strong_counts["unsupported"],
    }


def _document_blocks(text: str) -> list[tuple[str, str]]:
    blocks: list[tuple[str, list[str]]] = [("preamble", [])]
    for line in text.splitlines():
        heading = re.match(r"^\s*#{1,3}\s+(.+?)\s*$", line)
        if heading:
            blocks.append((heading.group(1), []))
        else:
            blocks[-1][1].append(line)
    return [(heading, "\n".join(lines).strip()) for heading, lines in blocks if "\n".join(lines).strip()]


def _claim_sentences(text: str) -> list[str]:
    stripped = _strip_code_blocks(text)
    sentences = [sentence.strip(" -\t") for sentence in re.split(r"(?<=[.!?。])\s+|\n+", stripped)]
    claims: list[str] = []
    for sentence in sentences:
        if len(sentence) < 24 or sentence.startswith("|"):
            continue
        if sentence.lower().startswith(("whether ", "does ", "is there ", "what ", "when ", "where ", "how ")):
            continue
        if _has_any(sentence, [" is ", " are ", " can ", " will ", " should ", " provides ", " exposes ", " returns ", " checks ", " detects ", "useful", "helps", "は", "できる", "する", "返す"]):
            claims.append(sentence[:260])
    return claims[:6]


def _evidence_snippets(text: str) -> list[str]:
    snippets: list[str] = []
    for block in re.findall(r"```.*?```", text, re.DOTALL):
        snippets.append(_compact_code_snippet(block))
    for sentence in re.split(r"(?<=[.!?。])\s+|\n+", _strip_code_blocks(text)):
        cleaned = sentence.strip(" -\t")
        if _has_any(cleaned, ["verified", "tested", "passed", "ok", "example", "run ", "command", "evidence", "result", "検証", "確認", "実行", "結果", "証拠", "例"]):
            snippets.append(_compact_snippet(cleaned))
    return _unique_nonempty(snippets)


def _limitation_snippets(text: str) -> list[str]:
    snippets: list[str] = []
    for sentence in re.split(r"(?<=[.!?。])\s+|\n+", _strip_code_blocks(text)):
        cleaned = sentence.strip(" -\t")
        if _is_negated_or_scoped_claim(cleaned) or _has_any(cleaned, ["limitation", "heuristic", "rough", "residual risk", "prototype", "制限", "試作", "残リスク"]):
            snippets.append(_compact_snippet(cleaned))
    return _unique_nonempty(snippets)


def _is_strong_claim(sentence: str) -> bool:
    return bool(
        re.search(
            r"\b(production[- ]ready|authoritative|guarantee(?:d|s)?|complete|fully|always|never fails?|correct|safe|secure)\b|完成品|完全|保証|安全|正確",
            sentence,
            re.IGNORECASE,
        )
    )


def _document_overclaim_sentences(text: str) -> list[str]:
    terms = [
        r"\bproduction[- ]ready\b",
        r"\bauthoritative\b",
        r"\bguarantee(?:d|s)?\b",
        r"\bcomplete\b",
        r"\bfully\b",
        r"\balways\b",
        r"\bnever fails?\b",
        r"\bcorrect\b",
        r"\bsafe\b",
        r"\bsecure\b",
        r"完成品",
        r"完全",
        r"保証",
        r"安全",
        r"正確",
    ]
    sentences = re.split(r"(?<=[.!?。])\s+|\n+", text)
    flagged: list[str] = []
    for sentence in sentences:
        cleaned = sentence.strip()
        if not cleaned or _is_negated_or_scoped_claim(cleaned):
            continue
        for term in terms:
            if re.search(term, cleaned, re.IGNORECASE):
                flagged.append(cleaned[:240])
                break
    return flagged


def _is_negated_or_scoped_claim(sentence: str) -> bool:
    lowered = sentence.lower()
    scoped_phrases = [
        "not ",
        "does not",
        "do not",
        "should not",
        "cannot",
        "can't",
        "prototype",
        "research",
        "limitation",
        "limited",
        "over-warn",
        "under-warn",
        "influenced by",
        "guidance",
        "review",
        "試作",
        "制限",
        "対象外",
        "ではない",
        "しない",
    ]
    return any(phrase in lowered for phrase in scoped_phrases)


def _has_implementation_evidence(text: str) -> bool:
    return _has_any(
        text,
        [
            "unittest",
            "pytest",
            "npm test",
            "swift test",
            "uv run",
            "passed",
            "ok",
            "実行済み",
            "確認済み",
            "試験済み",
            "テスト済み",
            "結果:",
            "結果：",
            "検証結果",
        ],
    )


def _blocker(category: str, finding: str, suggested_fix: str, basis: list[str]) -> Finding:
    return Finding(
        severity="blocker",
        category=category,
        basis=basis,
        finding=finding,
        suggested_fix=suggested_fix,
    )
