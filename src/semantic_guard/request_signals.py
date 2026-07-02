from __future__ import annotations

import re

from semantic_guard.text_utils import first_match as _first_match, has_any as _has_any

STAKEHOLDER_SOURCE_TERMS = [
    "stakeholder",
    "user",
    "customer",
    "owner",
    "operator",
    "maintainer",
    "reviewer",
    "requester",
    "利用者",
    "ユーザー",
    "顧客",
    "依頼元",
    "受入者",
    "判断主体",
    "運用者",
    "保守者",
    "読者",
    "作者",
    "誰が",
    "誰のため",
]


def _stakeholder_source_signal(text: str) -> str:
    return _first_match(text, STAKEHOLDER_SOURCE_TERMS)


def _quality_requirement_signal(text: str) -> str:
    terms = [
        "performance",
        "latency",
        "throughput",
        "availability",
        "reliability",
        "maintainability",
        "usability",
        "security",
        "secure",
        "safe",
        "fast",
        "品質",
        "性能",
        "速度",
        "速く",
        "高速",
        "安全",
        "可用",
        "信頼",
        "保守",
        "使いやす",
        "分かりやす",
        "安定",
    ]
    return _first_match(text, terms)


def _has_quality_constraint_evidence(text: str) -> bool:
    if re.search(r"(\d+(\.\d+)?\s*(ms|s|sec|秒|分|件|回|%|kb|mb|gb)|p9[059]|[<>]=?|以内|以上|以下|未満)", text, re.IGNORECASE):
        return True
    return _has_any(
        text,
        [
            "threshold",
            "metric",
            "measure",
            "measurement",
            "acceptance",
            "criteria",
            "benchmark",
            "slo",
            "sla",
            "閾値",
            "指標",
            "測定",
            "計測",
            "受入",
            "受入基準",
            "許容",
            "基準",
            "ベンチ",
        ],
    )


def _has_priority_evidence(text: str) -> bool:
    return _has_any(
        text,
        [
            "priority",
            "must",
            "should",
            "could",
            "p0",
            "p1",
            "p2",
            "critical",
            "optional",
            "優先",
            "必須",
            "任意",
            "重要度",
            "先に",
            "後で",
            "保留",
            "採用",
        ],
    )


def _unclassified_uncertainty_signal(text: str) -> str:
    uncertainty = _first_match(
        text,
        ["たぶん", "おそらく", "かもしれない", "っぽい", "と思う", "maybe", "probably", "likely", "seems"],
    )
    if not uncertainty:
        return ""
    if _has_any(
        text,
        [
            "未確定",
            "未決",
            "仮説",
            "判断待ち",
            "保留",
            "片側観測",
            "時点差",
            "unknown",
            "hypothesis",
            "pending",
            "tbd",
        ],
    ):
        return ""
    return uncertainty

def _acceptance_criteria_signal(text: str) -> str:
    terms = [
        "acceptance criteria",
        "success criteria",
        "definition of done",
        "done when",
        "pass if",
        "accepted when",
        "受入基準",
        "合格条件",
        "完了条件",
        "達成条件",
        "成功条件",
        "達成されたと言える",
        "完了とする",
        "合格とする",
        "ことを確認",
        "ことを検証",
    ]
    match = _first_match(text, terms)
    if match:
        return match
    if _has_quality_constraint_evidence(text):
        return _first_match(text, ["threshold", "metric", "受入", "閾値", "指標", "測定", "基準", "p95", "以内", "以下", "以上"])
    return ""


def _verification_method_signal(text: str) -> str:
    return _first_match(
        text,
        [
            "unittest",
            "pytest",
            "npm test",
            "swift test",
            "uv run",
            "benchmark",
            "inspection",
            "review",
            "demonstration",
            "analysis",
            "measurement",
            "schema validation",
            "smoke",
            "e2e",
            "cli",
            "command",
            "試験",
            "テスト",
            "検査",
            "実演",
            "解析",
            "測定",
            "計測",
            "レビュー",
            "ベンチ",
            "代表 CLI",
            "コマンド",
            "スモーク",
        ],
    )


def _evidence_artifact_signal(text: str) -> str:
    return _first_match(
        text,
        [
            "evidence",
            "test result",
            "command output",
            "log",
            "screenshot",
            "report",
            "record",
            "json output",
            "artifact",
            "証拠",
            "証跡",
            "根拠",
            "試験結果",
            "検証結果",
            "コマンド結果",
            "実行結果",
            "ログ",
            "スクリーンショット",
            "出力 JSON",
            "記録",
            "報告",
            "成果物",
        ],
    )


def _rejection_condition_signal(text: str) -> str:
    return _first_match(
        text,
        [
            "fail if",
            "reject",
            "rejection",
            "not accepted",
            "rollback if",
            "error if",
            "不合格",
            "棄却",
            "差し戻し",
            "未達",
            "失敗条件",
            "失敗時",
            "戻す",
            "保留",
            "rollback",
        ],
    )


def _scenario_context_signal(text: str) -> str:
    return _first_match(
        text,
        [
            "scenario",
            "use case",
            "given",
            "when",
            "then",
            "input",
            "output",
            "operation",
            "workflow",
            "context",
            "シナリオ",
            "利用場面",
            "ユースケース",
            "入力",
            "出力",
            "手順",
            "前提条件",
            "場合",
        ],
    )


def _has_verification_or_acceptance_language(text: str) -> bool:
    return _has_any(
        text,
        ["検証", "確認", "試験", "テスト", "受入", "受入基準", "acceptance", "verify", "test", "evidence"],
    )


def _requires_rejection_condition(text: str) -> bool:
    return _has_any(
        text,
        [
            "安全",
            "security",
            "secure",
            "権限",
            "permission",
            "認証",
            "認可",
            "削除",
            "delete",
            "移行",
            "migration",
            "公開",
            "release",
            "運用",
            "operation",
            "永続",
            "保存",
            "支払",
            "payment",
        ],
    )


def _requires_scenario_context(text: str) -> bool:
    return _has_any(
        text,
        [
            "画面",
            "UI",
            "ユーザー",
            "利用者",
            "操作",
            "入力",
            "表示",
            "検索",
            "通知",
            "workflow",
            "screen",
            "user",
            "input",
            "display",
            "search",
            "notification",
        ],
    )


def _observable_behavior_signal(text: str) -> str:
    return _first_match(
        text,
        [
            "return",
            "returns",
            "display",
            "show",
            "save",
            "create",
            "update",
            "delete",
            "reject",
            "allow",
            "deny",
            "notify",
            "record",
            "validate",
            "search",
            "filter",
            "返す",
            "返る",
            "表示",
            "保存",
            "作成",
            "更新",
            "削除",
            "拒否",
            "許可",
            "通知",
            "検索",
            "絞り込",
            "出力",
            "入力",
        ],
    )


def _vague_behavior_signal(text: str) -> str:
    return _first_match(
        text,
        [
            "改善",
            "対応",
            "サポート",
            "整える",
            "最適化",
            "いい感じ",
            "使いやす",
            "分かりやす",
            "強化",
            "improve",
            "support",
            "optimize",
            "enhance",
            "better",
        ],
    )


def _precondition_or_trigger_signal(text: str) -> str:
    return _first_match(
        text,
        [
            "given",
            "when",
            "if",
            "on ",
            "after",
            "before",
            "trigger",
            "precondition",
            "前提",
            "前提条件",
            "場合",
            "とき",
            "時",
            "入力した場合",
            "クリック",
            "操作した場合",
            "起動時",
            "保存時",
            "受信時",
            "発火",
            "条件",
        ],
    )


def _expected_result_signal(text: str) -> str:
    return _first_match(
        text,
        [
            "then",
            "expected",
            "result",
            "output",
            "returns",
            "status",
            "error",
            "state",
            "期待結果",
            "期待状態",
            "返る",
            "返す",
            "表示される",
            "出力される",
            "保存される",
            "更新される",
            "作成される",
            "記録される",
            "残る",
            "拒否される",
            "通知される",
            "エラー",
            "状態",
            "一覧",
        ],
    )


def _interface_surface_signal(text: str) -> str:
    return _first_match(
        text,
        [
            "api",
            "cli",
            "mcp",
            "json",
            "yaml",
            "csv",
            "webhook",
            "http",
            "endpoint",
            "schema",
            "config",
            "env",
            "file format",
            "API",
            "CLI",
            "MCP",
            "JSON",
            "YAML",
            "CSV",
            "Webhook",
            "エンドポイント",
            "スキーマ",
            "構成",
            "設定",
            "環境変数",
            "ファイル形式",
        ],
    )


def _interface_contract_signal(text: str) -> str:
    if not _interface_surface_signal(text):
        return ""
    return _first_match(
        text,
        [
            "schema",
            "field",
            "property",
            "status",
            "status code",
            "error",
            "format",
            "example",
            "default",
            "option",
            "flag",
            "argument",
            "request",
            "response",
            "スキーマ",
            "項目",
            "フィールド",
            "状態コード",
            "エラー",
            "形式",
            "例",
            "既定",
            "オプション",
            "フラグ",
            "引数",
            "リクエスト",
            "レスポンス",
        ],
    )


def _requires_precondition_or_trigger(text: str) -> bool:
    if _has_quality_constraint_evidence(text) and not _has_any(text, ["画面", "UI", "入力", "操作", "API", "CLI", "JSON"]):
        return False
    return _has_any(
        text,
        [
            "画面",
            "UI",
            "ユーザー",
            "利用者",
            "操作",
            "入力",
            "検索",
            "通知",
            "API",
            "CLI",
            "JSON",
            "workflow",
            "screen",
            "user",
            "input",
            "search",
            "notification",
        ],
    )


def _requires_expected_result(text: str) -> bool:
    if _has_quality_constraint_evidence(text) and not _has_any(text, ["画面", "UI", "入力", "操作", "API", "CLI", "JSON"]):
        return False
    return _has_any(
        text,
        [
            "入力",
            "操作",
            "検索",
            "通知",
            "画面",
            "UI",
            "API",
            "CLI",
            "JSON",
            "output",
            "return",
            "screen",
            "input",
            "search",
            "notification",
        ],
    )
