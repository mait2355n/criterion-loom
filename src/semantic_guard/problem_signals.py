from __future__ import annotations

from semantic_guard.request_signals import _rejection_condition_signal
from semantic_guard.text_utils import first_match as _first_match, has_any as _has_any

def _problem_mechanism_fit_signal(text: str) -> str:
    if not _problem_or_symptom_signal(text) or not _solution_action_signal(text):
        return ""
    if _problem_mechanism_evidence_signal(text) or _investigation_only_signal(text):
        return ""
    return _problem_or_symptom_signal(text) or _solution_action_signal(text)


def _symptom_only_success_signal(text: str) -> str:
    if not _problem_or_symptom_signal(text):
        return ""
    symptom_success = _symptom_disappearance_success_signal(text)
    if not symptom_success:
        return ""
    if _problem_mechanism_evidence_signal(text) or _side_effect_transfer_evidence_signal(text) or _rejection_condition_signal(text):
        return ""
    return symptom_success


def _problem_or_symptom_signal(text: str) -> str:
    return _first_match(
        text,
        [
            "problem",
            "issue",
            "failure",
            "error",
            "incident",
            "symptom",
            "does not work",
            "broken",
            "slow",
            "blocked",
            "stuck",
            "rejected",
            "warning",
            "問題",
            "課題",
            "症状",
            "障害",
            "不具合",
            "失敗",
            "エラー",
            "警告",
            "止まる",
            "落ちる",
            "切れる",
            "詰まる",
            "遅い",
            "重い",
            "拒否",
            "通らない",
            "できない",
            "うまくいかない",
        ],
    )


def _solution_action_signal(text: str) -> str:
    return _first_match(
        text,
        [
            "solution",
            "fix",
            "workaround",
            "mitigation",
            "対応",
            "解決策",
            "解決案",
            "修正",
            "改善",
            "変更",
            "置換",
            "交換",
            "導入",
            "追加",
            "削除",
            "緩和",
            "回避",
            "抑止",
            "無効化",
            "上げる",
            "下げる",
            "増やす",
            "減らす",
            "伸ばす",
            "短くする",
            "広げる",
            "狭める",
            "止める",
            "消す",
        ],
    )


def _intervention_action_signal(text: str) -> str:
    return _first_match(
        text,
        [
            "bypass",
            "disable",
            "ignore",
            "suppress",
            "mute",
            "increase",
            "decrease",
            "raise",
            "lower",
            "retry",
            "timeout",
            "limit",
            "threshold",
            "quota",
            "capacity",
            "fallback",
            "workaround",
            "無効化",
            "握り潰す",
            "握りつぶす",
            "抑止",
            "抑制",
            "回避",
            "緩和",
            "無視",
            "消す",
            "出さない",
            "上げる",
            "下げる",
            "増やす",
            "減らす",
            "伸ばす",
            "短くする",
            "広げる",
            "狭める",
            "リトライ",
            "タイムアウト",
            "上限",
            "下限",
            "閾値",
            "容量",
            "制限",
            "検証を外す",
            "認可を外す",
        ],
    )


def _problem_mechanism_evidence_signal(text: str) -> str:
    return _first_match(
        text,
        [
            "root cause",
            "cause",
            "mechanism",
            "reproduction",
            "precondition",
            "constraint",
            "rationale",
            "why",
            "because",
            "caused by",
            "原因",
            "根本原因",
            "発生原因",
            "発生機構",
            "機構",
            "仕組み",
            "再現条件",
            "発生条件",
            "前提条件",
            "制約",
            "根拠",
            "理由",
            "なぜ",
            "作用",
            "効く",
            "仮説",
            "切り分け",
            "調査で確かめる",
        ],
    )


def _side_effect_transfer_evidence_signal(text: str) -> str:
    return _first_match(
        text,
        [
            "side effect",
            "impact",
            "risk transfer",
            "tradeoff",
            "downstream",
            "upstream",
            "load",
            "capacity",
            "cost",
            "regression",
            "compatibility",
            "failure mode",
            "副作用",
            "影響",
            "危険移転",
            "負荷移転",
            "リスク移転",
            "トレードオフ",
            "上流",
            "下流",
            "隣接",
            "負荷",
            "容量",
            "定格",
            "費用",
            "責任",
            "故障様式",
            "失敗様式",
            "互換",
            "回帰",
            "波及",
        ],
    )


def _symptom_disappearance_success_signal(text: str) -> str:
    return _first_match(
        text,
        [
            "does not happen",
            "does not fail",
            "does not stop",
            "no error",
            "no warning",
            "not blocked",
            "not rejected",
            "起きない",
            "発生しない",
            "再発しない",
            "失敗しない",
            "エラーが出ない",
            "警告が出ない",
            "止まらない",
            "落ちない",
            "切れない",
            "詰まらない",
            "拒否されない",
            "通る",
            "消える",
            "出ない",
        ],
    )


def _investigation_only_signal(text: str) -> str:
    return _has_any(
        text,
        [
            "調査のみ",
            "原因調査",
            "切り分けのみ",
            "まだ実施しない",
            "解決策を決めない",
            "investigation only",
            "diagnosis only",
            "do not implement",
        ],
    )
