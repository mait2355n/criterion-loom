from __future__ import annotations

from semantic_guard.audit_common import (
    BASIS,
    _blocker,
    _has_behavior_evidence,
    _has_implementation_evidence,
    _implemented_public_behavior,
    _result,
    _security_signal,
)
from semantic_guard.models import Finding
from semantic_guard.result_builder import next_actions as _next_actions, score_from_findings as _score_from_findings
from semantic_guard.text_utils import combine as _combine, has_any as _has_any

def finish_check(summary: str, evidence: str = "", context: str = "", strict: bool = True) -> dict[str, object]:
    combined = _combine(summary, evidence, context)
    findings: list[Finding] = []
    missing: list[str] = []

    if not summary.strip():
        findings.append(_blocker("evidence", "完了要約が空。", "変更内容と完了範囲を書く。", BASIS["implementation"]))
        missing.append("summary")

    if not _has_any(combined, ["test", "pytest", "swift test", "npm test", "uv run", "検証", "確認", "コマンド", "実行"]):
        findings.append(
            Finding(
                severity="blocker" if strict else "major",
                category="evidence",
                basis=BASIS["implementation"],
                finding="検証証拠が見えない。",
                suggested_fix="実行したコマンド、結果、または未実行理由を記録する。",
                rule_id="finish.evidence.tests_missing",
            )
        )
        missing.append("tests_ran_or_reason")

    if not _has_any(combined, ["受入", "acceptance", "完了条件", "criteria", "evidence", "証拠", "結果"]):
        findings.append(
            Finding(
                severity="major",
                category="validation",
                basis=BASIS["requirements"] + BASIS["planning"],
                finding="受入条件と証拠の対応が薄い。",
                suggested_fix="要求または目的に対して、何をもって完了としたかを明記する。",
            )
        )
        missing.append("acceptance_evidence")

    if _security_signal(combined) and not _has_any(combined, ["secret scan", "dependency", "owasp", "nist", "安全", "セキュリティ", "手動確認"]):
        findings.append(
            Finding(
                severity="major",
                category="security",
                basis=BASIS["security"],
                finding="安全性に関わる変更の証拠が不足している。",
                suggested_fix="秘密情報、依存、認証認可、入力出力、ログの確認結果を記録する。",
            )
        )
        missing.append("security_evidence")

    if _implemented_public_behavior(combined) and not _has_behavior_evidence(combined):
        findings.append(
            Finding(
                severity="major" if strict else "minor",
                category="behavior",
                basis=BASIS["implementation"],
                finding="実装した公開挙動に対する代表実行証拠が見えない。",
                suggested_fix="単体試験だけでなく、代表 CLI/API/MCP 実行、smoke test、出力契約確認、または未実行理由を記録する。",
                warning_class="generic caution",
                rule_id="finish.implementation.behavior_evidence_missing",
            )
        )
        missing.append("behavior_evidence")

    if not _has_any(combined, ["残リスク", "未実行", "未確認", "できなかった", "not run", "residual", "risk", "none"]):
        findings.append(
            Finding(
                severity="info",
                category="risk",
                basis=BASIS["planning"],
                finding="残リスクまたは未実行事項の有無が明示されていない。",
                suggested_fix="残リスクが無い場合も `残リスクなし` と書く。",
            )
        )

    return _result(
        phase="finish_check",
        findings=findings,
        missing=sorted(set(missing)),
        score=_score_from_findings(findings),
        details={},
        next_actions=_next_actions(findings, "証拠と残リスクを補完してから完了報告する。"),
    )
