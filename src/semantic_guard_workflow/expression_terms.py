from __future__ import annotations

import re
from typing import Iterable

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

_JAPANESE_TOKEN_CHARS = "一-龯ぁ-んァ-ンA-Za-z0-9_"

_AS_VIEW_OPERATION_REWRITE_CANDIDATES = [
    {"when": "one-time verification", "example": "〜のため確認する。"},
    {"when": "inspection against criteria", "example": "〜を基準に照らして検査する。"},
    {"when": "continuous observation", "example": "〜を監視する。"},
    {"when": "classification", "example": "〜として分類する。"},
    {"when": "human decision support", "example": "〜を判断材料として提示する。"},
]

_INSPECTION_CONTRACT_REWRITE_CANDIDATES = [
    {"when": "criteria available", "example": "〜を基準 X に照らして確認する。"},
    {"when": "rule-based inspection", "example": "〜を走査し、違反箇所を findings として返す。"},
    {"when": "human review", "example": "〜を人間の判断材料として提示する。"},
]

_CAPABILITY_CONTRACT_REWRITE_CANDIDATES = [
    {"when": "bounded input", "example": "指定された入力から抽出できる範囲を JSON として返す。"},
    {"when": "non-guaranteed completeness", "example": "現在の規則で検出できた候補を返し、網羅性は保証しない。"},
    {"when": "record-backed scope", "example": "指定された record 群を読み、根拠付きの候補一覧として記録する。"},
]

_MAPPING_CONTRACT_REWRITE_CANDIDATES = [
    {"when": "field mapping", "example": "findings と evidence を audit_record.fields に写す。"},
    {"when": "condition-based routing", "example": "blocking_status と needed_for に基づいて next_action を記録する。"},
    {"when": "append-only closure", "example": "resolution_condition を満たした時だけ closure record を追記する。"},
]


def _expression_terms_union(*term_groups: Iterable[str]) -> list[str]:
    terms: list[str] = []
    seen: set[str] = set()
    for term_group in term_groups:
        for term in term_group:
            if term in seen:
                continue
            seen.add(term)
            terms.append(term)
    return terms


_AS_VIEW_OPERATION_TERMS = [
    "確認",
    "検査",
    "監視",
    "観測",
    "分類",
    "提示",
    "返す",
    "記録",
    "照合",
    "比較",
    "抽出",
    "列挙",
    "保存",
    "生成",
    "出力",
    "emit",
    "return",
]

_INSPECTION_CRITERION_TERMS = ["基準", "条件", "規則", "契約", "観点", "項目", "差分", "照らして"]
_INSPECTION_METHOD_TERMS = ["検査", "確認", "チェック", "レビュー", "評価", "判断", "判定", "走査", "照合", "比較", "査読"]
_INSPECTION_OUTPUT_TERMS = ["一覧", "JSON", "findings", "diagnostics", "記録", "返す", "出力", "レポート", "指摘", "違反箇所", "結果"]
_INSPECTION_DECISION_ACTOR_TERMS = ["人間", "外部", "保守者", "reviewer", "最終判断", "判断材料"]

_CAPABILITY_SCOPE_BOUNDARY_TERMS = [
    "指定された",
    "対象",
    "範囲",
    "可視",
    "visible",
    "scope",
    "boundary",
    "resource_record",
    "audit_record",
]
_CAPABILITY_INPUT_BOUNDARY_TERMS = [
    "入力",
    "文脈",
    "context",
    "file",
    "文書",
    "record",
    "resource_record",
    "audit_record",
    "supplied",
    "provided",
]
_CAPABILITY_LIMIT_TERMS = [
    "限界",
    "制限",
    "非保証",
    "保証しない",
    "完全ではない",
    "現在の規則",
    "現在の detector",
    "limits",
    "within",
    "subject to",
]
_CAPABILITY_EVIDENCE_OUTPUT_TERMS = [
    "JSON",
    "findings",
    "details",
    "limits",
    "evidence",
    "記録",
    "schema",
    "出力",
    "返す",
    "report",
    "bundle",
]

_MAPPING_SOURCE_FIELD_TERMS = [
    "監査結果",
    "findings",
    "missing",
    "next_actions",
    "evidence",
    "handoff item",
    "handoff_items",
    "management_handoff_items",
    "audit_record",
    "source",
    "source_audit_id",
    "resource_record",
    "unresolved_decision_record",
]
_MAPPING_DESTINATION_FIELD_TERMS = [
    "資源状態",
    "危険",
    "次行動",
    "owner",
    "needed_for",
    "blocking_status",
    "next_action",
    "review_at",
    "audit_record",
    "fields",
    "record",
    "管理対象",
    "unresolved_decision_record",
    "decision_record",
    "resource_state",
    "risk",
]
_MAPPING_RULE_OR_CONDITION_TERMS = [
    "基づいて",
    "に基づき",
    "条件",
    "規則",
    "rule",
    "condition",
    "基準",
    "照らして",
    "満たした",
    "resolution_condition",
    "blocking_status",
    "needed_for",
    "review_at",
    "優先度",
]
_MAPPING_EVIDENCE_PRESERVATION_TERMS = [
    "evidence",
    "source_audit_id",
    "保持",
    "保存",
    "根拠",
    "証拠",
    "source_excerpt",
    "acquired_at",
    "記録",
    "preserve",
    "append-only",
]

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
        "strict_trigger_terms": ["場所", "箇所", "部分", "内容", "材料", "もの"],
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
        "rule_id": "doc.expression.as_view_operation_blurred",
        "trigger_terms": [
            "として見る",
            "として見て",
            "として見せる",
            "として扱う",
            "として扱い",
            "として使う",
            "として利用する",
            "として用いる",
        ],
        "support_terms": _AS_VIEW_OPERATION_TERMS,
        "repair_target": "operation",
        "support_policy": "always_warn",
        "operation_contract": {
            "family": "as_view_operation",
            "policy": "always_warn",
            "slots": {
                "operation": _AS_VIEW_OPERATION_TERMS
            },
        },
        "needs_human_decision": True,
        "minimal_example": "視点ではなく、確認、検査、監視、分類、提示などの具体操作を明示する。",
        "rewrite_candidates": _AS_VIEW_OPERATION_REWRITE_CANDIDATES,
    },
    {
        "rule_id": "doc.expression.inspection_contract_missing",
        "trigger_terms": [
            "検査する",
            "検査し",
            "確認する",
            "確認し",
            "チェックする",
            "チェックし",
            "レビューする",
            "レビューし",
            "評価する",
            "評価し",
            "判断する",
            "判断し",
            "判定する",
            "判定し",
        ],
        "support_terms": _expression_terms_union(
            _INSPECTION_CRITERION_TERMS,
            _INSPECTION_METHOD_TERMS,
            _INSPECTION_OUTPUT_TERMS,
            _INSPECTION_DECISION_ACTOR_TERMS,
        ),
        "repair_target": "operation_contract",
        "operation_contract": {
            "family": "inspection_contract",
            "policy": "minimum_slots",
            "minimum_slots": 2,
            "slots": {
                "criterion": _INSPECTION_CRITERION_TERMS,
                "method": _INSPECTION_METHOD_TERMS,
                "output": _INSPECTION_OUTPUT_TERMS,
                "decision_actor": _INSPECTION_DECISION_ACTOR_TERMS,
            },
        },
        "needs_human_decision": True,
        "minimal_example": "検査、確認、評価、判断の基準、方法、出力、または判断主体を明示する。",
        "rewrite_candidates": _INSPECTION_CONTRACT_REWRITE_CANDIDATES,
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
        "strict_trigger_terms": ["内容"],
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
    {
        "rule_id": "doc.expression.capability_contract_missing",
        "trigger_terms": [
            "すべて",
            "全て",
            "全情報",
            "資源全体",
            "全体",
            "網羅",
            "網羅性",
            "完全",
            "漏れなく",
            "あらゆる",
            "取れる情報",
            "all visible",
            "all information",
            "all facts",
            "all/every",
            "every material",
            "every missing",
        ],
        "strict_trigger_terms": ["すべて", "全て", "全情報", "全体", "網羅", "完全", "あらゆる"],
        "support_terms": _expression_terms_union(
            _CAPABILITY_SCOPE_BOUNDARY_TERMS,
            _CAPABILITY_INPUT_BOUNDARY_TERMS,
            _CAPABILITY_LIMIT_TERMS,
            _CAPABILITY_EVIDENCE_OUTPUT_TERMS,
        ),
        "repair_target": "capability_contract",
        "operation_contract": {
            "family": "capability_contract",
            "policy": "minimum_slots",
            "minimum_slots": 3,
            "slots": {
                "scope_boundary": _CAPABILITY_SCOPE_BOUNDARY_TERMS,
                "input_boundary": _CAPABILITY_INPUT_BOUNDARY_TERMS,
                "limit_or_non_guarantee": _CAPABILITY_LIMIT_TERMS,
                "evidence_or_output_shape": _CAPABILITY_EVIDENCE_OUTPUT_TERMS,
            },
        },
        "needs_human_decision": True,
        "minimal_example": "広い能力主張には、範囲、入力境界、限界または非保証、根拠または出力形を明示する。",
        "rewrite_candidates": _CAPABILITY_CONTRACT_REWRITE_CANDIDATES,
    },
    {
        "rule_id": "doc.expression.mapping_contract_missing",
        "trigger_terms": [
            "写像する",
            "写像し",
            "写す",
            "写し",
            "補う",
            "補って",
            "昇格させる",
            "昇格し",
            "戻す",
            "戻して",
            "接続する",
            "接続し",
            "閉じる",
            "追記する",
            "追記し",
        ],
        "support_terms": _expression_terms_union(
            _MAPPING_SOURCE_FIELD_TERMS,
            _MAPPING_DESTINATION_FIELD_TERMS,
            _MAPPING_RULE_OR_CONDITION_TERMS,
            _MAPPING_EVIDENCE_PRESERVATION_TERMS,
        ),
        "repair_target": "mapping_contract",
        "operation_contract": {
            "family": "mapping_contract",
            "policy": "minimum_slots",
            "minimum_slots": 3,
            "slots": {
                "source_field": _MAPPING_SOURCE_FIELD_TERMS,
                "destination_field": _MAPPING_DESTINATION_FIELD_TERMS,
                "rule_or_condition": _MAPPING_RULE_OR_CONDITION_TERMS,
                "evidence_preservation": _MAPPING_EVIDENCE_PRESERVATION_TERMS,
            },
        },
        "needs_human_decision": True,
        "minimal_example": "写像、補填、昇格、接続、閉鎖には、入力欄、出力欄、適用条件、根拠保持を明示する。",
        "rewrite_candidates": _MAPPING_CONTRACT_REWRITE_CANDIDATES,
    },
]

_EXPRESSION_SUPPORT_TERMS = sorted(
    {
        str(term)
        for check in _EXPRESSION_CHECKS
        for term in check["support_terms"]
    }
)


