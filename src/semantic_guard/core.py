"""Compatibility facade for semantic-guard's core audit entrypoints.

The audit implementations live in phase-specific modules. Keep this file as a
thin import surface for existing callers that still depend on semantic_guard.core.
"""

from __future__ import annotations

from semantic_guard.audit_common import apply_logical_trace_mode
from semantic_guard.decision_state import audit_decision_state
from semantic_guard.diff_audit import audit_diff
from semantic_guard.finish_audit import finish_check
from semantic_guard.plan_audit import audit_plan
from semantic_guard.problem_signals import (
    _problem_mechanism_evidence_signal,
    _problem_or_symptom_signal,
    _side_effect_transfer_evidence_signal,
    _solution_action_signal,
    _symptom_disappearance_success_signal,
)
from semantic_guard.request_audit import audit_request
from semantic_guard.target_understanding import understand_target

__all__ = [
    "apply_logical_trace_mode",
    "audit_decision_state",
    "audit_diff",
    "audit_plan",
    "audit_request",
    "finish_check",
    "understand_target",
]
