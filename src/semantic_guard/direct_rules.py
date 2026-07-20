from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Literal

from .profiles import FUNCTIONAL_REQUIREMENT_PROFILE, NormativeProfile, RelationObligationSpec
from .records import ParsedField, ParsedRequirementRecord


DirectOutcome = Literal["supported", "refuted", "unresolved", "not_applicable", "invalid"]


@dataclass(frozen=True, slots=True)
class DirectRelationAssessment:
    obligation_id: str
    outcome: DirectOutcome
    rule_id: str
    from_field: str
    to_field: str
    evidence_spans: tuple[tuple[int, int], ...]
    basis: tuple[str, ...]
    unknown_reasons: tuple[str, ...] = ()


DIMENSION_PATTERNS: dict[str, re.Pattern[str]] = {
    "latency": re.compile(r"応答時間|レスポンス|latency|response\s*time|p\d{2}|\bms\b|ミリ秒", re.IGNORECASE),
    "throughput": re.compile(r"スループット|throughput|requests?\s*/|件/秒|rps\b|qps\b", re.IGNORECASE),
    "availability": re.compile(r"可用性|稼働率|availability|uptime", re.IGNORECASE),
    "error_rate": re.compile(r"エラー率|失敗率|error\s*rate|failure\s*rate", re.IGNORECASE),
    "accuracy": re.compile(r"精度|正解率|accuracy|precision|recall", re.IGNORECASE),
    "authentication": re.compile(r"認証|ログイン|authentication|login", re.IGNORECASE),
    "search": re.compile(r"検索|search|query", re.IGNORECASE),
}

METRIC_PATTERN = re.compile(
    r"(?:p\d{2}\s*)?(?:\d+(?:\.\d+)?\s*(?:ms|s|秒|ミリ秒|%|％|件|回))|(?:以上|以下|以内|未満)",
    re.IGNORECASE,
)
CONDITION_PATTERN = re.compile(
    r"(?:場合(?:は|に|だけ|のみ)?|とき|(?:[一-龥ぁ-んァ-ヶA-Za-z0-9_]+)?(?:時(?!間)|際)(?:だけ|のみ|は|に)?"
    r"|なら(?:ば)?|たら|れば|に限り|when\b|if\b|unless\b)",
    re.IGNORECASE,
)
OBJECT_PATTERN = re.compile(
    r"(?P<object>[A-Za-z0-9_一-龥ぁ-んァ-ヶー]{1,32})を(?:処理|検索|返|表示|保存|生成|更新|削除|送信|検証|測定)",
    re.IGNORECASE,
)
CONTENT_ANCHOR_PATTERN = re.compile(r"[一-龥ァ-ヶーA-Za-z0-9_]{3,}")
GENERIC_CONTENT_ANCHORS = frozenset(
    {
        "api",
        "feature",
        "function",
        "query",
        "request",
        "response",
        "result",
        "search",
        "system",
        "user",
    }
)
_SAHEN_PREDICATE = (
    r"(?:する|した|して|し(?:ない|ます|た|て)?|"
    r"され(?:る|た|て|ない)?|させ(?:る|た|て)?|でき(?:る|た|て)?)"
)
ACTION_FAMILY_PATTERNS: dict[str, re.Pattern[str]] = {
    "create": re.compile(
        rf"(?:生成|作成|追加|登録){_SAHEN_PREDICATE}|"
        r"\b(?:create|generate|add|register)(?:s|d|ed|ing)?\b",
        re.IGNORECASE,
    ),
    "preserve": re.compile(
        rf"(?:保存|記録|保持|格納){_SAHEN_PREDICATE}|"
        r"\b(?:save|store|record|retain)(?:s|d|ed|ing)?\b",
        re.IGNORECASE,
    ),
    "delete": re.compile(
        rf"(?:削除|破棄|消去|除去){_SAHEN_PREDICATE}|"
        r"\b(?:delete|discard|erase|remove)(?:s|d|ed|ing)?\b",
        re.IGNORECASE,
    ),
    "return": re.compile(
        rf"返(?:す|した|して|し(?:ない|ます|た|て)?|され(?:る|た|て|ない)?)|"
        rf"(?:応答|表示|送信){_SAHEN_PREDICATE}|"
        r"\b(?:return|respond|display|send)(?:s|d|ed|ing)?\b",
        re.IGNORECASE,
    ),
    "process": re.compile(
        rf"(?:処理|検索|検証|認証){_SAHEN_PREDICATE}|"
        r"\b(?:process|search|verify|authenticate)(?:es|s|d|ed|ing)?\b",
        re.IGNORECASE,
    ),
    "update": re.compile(
        rf"(?:更新|変更|修正){_SAHEN_PREDICATE}|"
        r"\b(?:update|change|modify)(?:s|d|ed|ing)?\b",
        re.IGNORECASE,
    ),
    "enable": re.compile(
        rf"(?:有効化|許可){_SAHEN_PREDICATE}|有効(?:にする|になる)|"
        r"\b(?:enable|allow)(?:s|d|ed|ing)?\b",
        re.IGNORECASE,
    ),
    "disable": re.compile(
        rf"(?:無効化|禁止){_SAHEN_PREDICATE}|無効(?:にする|になる)|"
        r"\b(?:disable|deny|forbid)(?:s|d|ed|ing|den|ding)?\b",
        re.IGNORECASE,
    ),
}
INCOMPATIBLE_ACTION_FAMILIES = frozenset(
    {
        frozenset({"create", "delete"}),
        frozenset({"preserve", "delete"}),
        frozenset({"enable", "disable"}),
    }
)
EXPLICIT_RESULT_MARKER = re.compile(
    r"その結果|これにより|結果として|従って|thereby|as\s+a\s+result",
    re.IGNORECASE,
)


def semantic_dimensions(text: str) -> frozenset[str]:
    return frozenset(name for name, pattern in DIMENSION_PATTERNS.items() if pattern.search(text))


def _span(field: ParsedField | None) -> tuple[tuple[int, int], ...]:
    return () if field is None else ((field.value_start, field.value_end),)


def _spans(*fields: ParsedField | None) -> tuple[tuple[int, int], ...]:
    return tuple(span for field in fields for span in _span(field))


def _object_value(match: re.Match[str] | None) -> str | None:
    if match is None:
        return None
    value = match.group("object")
    for separator in ("、", "が", "は"):
        if separator in value:
            value = value.rsplit(separator, 1)[-1]
    return value or None


_ACTIVE_SAHEN_PREDICATE = (
    r"(?:する|した|して|し(?:ない|ます|た|て)?|でき(?:る|た|て)?)"
)
_ACTIVE_JAPANESE_ACTION = re.compile(
    rf"(?:生成|作成|追加|登録|保存|記録|保持|格納|削除|破棄|消去|除去|"
    rf"応答|表示|送信|処理|検索|検証|認証|更新|変更|修正|有効化|許可|"
    rf"無効化|禁止){_ACTIVE_SAHEN_PREDICATE}"
    r"|返(?:す|した|して|します|さない|さなかった)",
    re.IGNORECASE,
)
_NON_AGENTIVE_VOICE = re.compile(
    r"(?:され(?:る|た|て|ない|ます)?|させ(?:る|た|て|ない|ます)?|"
    r"られ(?:る|た|て|ない|ます)?|[一-龥ぁ-んァ-ヶー]れる)",
    re.IGNORECASE,
)
_REPORTED_OR_QUOTED = re.compile(
    r"[「」『』\"“”]|と(?:記載|報告|説明|発言|主張|述べ|いう|言う)",
    re.IGNORECASE,
)


def _actor_assertion(actor: str, scenario: str) -> tuple[bool, str]:
    """Recognize only a bounded, explicit actor/action assertion.

    Mere occurrence is not enough: ``システムが管理者を検索する`` names
    管理者 but makes it the object.  Direct rules may support ``performs``
    only when an actor marker is followed by a narrow active action predicate.
    A grammatical subject/topic is not necessarily an agent: passive,
    causative, reported, quoted, and nominal-predicate clauses therefore stay
    unresolved for the dependency/reassessment path.
    """

    value = actor.strip()
    if not value:
        return False, "scenario_actor_missing"
    escaped = re.escape(value)
    japanese = re.compile(
        rf"(?:^|[。！？!?；;\n])\s*{escaped}\s*(?:が|は)(?![A-Za-z0-9_])"
        rf"(?P<clause>[^。！？!?；;\n]*)",
        re.IGNORECASE,
    )
    english = re.compile(
        rf"(?:^|[.!?;\n])\s*{escaped}\s+(?:shall|must|will|can|may)\s+"
        rf"(?P<verb>[A-Za-z][A-Za-z0-9_-]*)\b",
        re.IGNORECASE,
    )
    japanese_match = japanese.search(scenario)
    if japanese_match is not None:
        clause = japanese_match.group("clause")
        if _REPORTED_OR_QUOTED.search(clause):
            return False, "scenario_actor_assertion_reported_or_quoted"
        if _NON_AGENTIVE_VOICE.search(clause):
            return False, "scenario_actor_voice_not_agentive"
        if not _ACTIVE_JAPANESE_ACTION.search(clause):
            return False, "scenario_actor_active_predicate_not_established"
        return True, "explicit_scenario_actor_active_assertion"

    english_match = english.search(scenario)
    if english_match is not None:
        verb = english_match.group("verb").casefold()
        if verb in {"be", "make", "cause", "allow", "require", "ask"}:
            return False, "scenario_actor_voice_not_agentive"
        return True, "explicit_scenario_actor_active_assertion"
    return False, "scenario_actor_role_not_assertion_capable"


def _content_anchors(text: str) -> frozenset[str]:
    return frozenset(
        item.casefold()
        for item in CONTENT_ANCHOR_PATTERN.findall(text)
        if item.casefold() not in GENERIC_CONTENT_ANCHORS
    )


def _shared_specific_anchors(left: str, right: str) -> tuple[str, ...]:
    left_anchors = _content_anchors(left)
    right_anchors = _content_anchors(right)
    shared: set[str] = set()
    for left_anchor in left_anchors:
        for right_anchor in right_anchors:
            shorter, longer = sorted((left_anchor, right_anchor), key=len)
            if shorter == longer or (len(shorter) >= 4 and shorter in longer):
                shared.add(shorter)
    return tuple(sorted(shared))


def _action_families(text: str) -> frozenset[str]:
    return frozenset(
        family
        for family, pattern in ACTION_FAMILY_PATTERNS.items()
        if pattern.search(text)
    )


def _produces_alignment(
    scenario: ParsedField | None,
    expected: ParsedField | None,
) -> tuple[DirectOutcome, tuple[str, ...]]:
    outcome, reasons = _alignment(scenario, expected)
    if outcome != "supported" or scenario is None or expected is None:
        return outcome, reasons
    scenario_actions = _action_families(scenario.value)
    expected_actions = _action_families(expected.value)
    incompatible_pairs: list[tuple[str, str]] = []
    for left in scenario_actions:
        for right in expected_actions:
            if frozenset({left, right}) in INCOMPATIBLE_ACTION_FAMILIES:
                incompatible_pairs.append((left, right))
    if incompatible_pairs:
        conflict_basis = tuple(
            item
            for left, right in sorted(incompatible_pairs)
            for item in (
                f"incompatible_scenario_action:{left}",
                f"incompatible_expected_action:{right}",
            )
        )
        if len(scenario_actions) == 1 and len(expected_actions) == 1:
            return "refuted", conflict_basis
        return (
            "unresolved",
            ("compound_result_transition_requires_parser", *conflict_basis),
        )
    shared_actions = tuple(sorted(scenario_actions & expected_actions))
    if shared_actions:
        return (
            "supported",
            reasons + tuple(f"shared_result_action:{item}" for item in shared_actions),
        )
    if EXPLICIT_RESULT_MARKER.search(expected.value):
        return "supported", reasons + ("explicit_result_marker",)
    return (
        "unresolved",
        (
            "shared_endpoint_without_versioned_result_transition",
            *reasons,
        ),
    )


def _alignment(
    left: ParsedField | None,
    right: ParsedField | None,
    *,
    allow_dimension_only: bool = False,
) -> tuple[DirectOutcome, tuple[str, ...]]:
    if left is None or right is None:
        return "unresolved", ("required_endpoint_missing_or_ambiguous",)
    left_dimensions = semantic_dimensions(left.value)
    right_dimensions = semantic_dimensions(right.value)
    shared_dimensions = sorted(left_dimensions & right_dimensions)
    shared_anchors = _shared_specific_anchors(left.value, right.value)
    if shared_anchors:
        return (
            "supported",
            tuple(f"shared_specific_anchor:{item}" for item in shared_anchors)
            + tuple(f"shared_dimension:{item}" for item in shared_dimensions),
        )
    if shared_dimensions and allow_dimension_only:
        return "supported", tuple(
            f"shared_dimension:{item}" for item in shared_dimensions
        )
    if left_dimensions and right_dimensions:
        if shared_dimensions:
            return (
                "unresolved",
                (
                    "shared_dimension_is_candidate_not_relation_proof",
                    *tuple(f"shared_dimension:{item}" for item in shared_dimensions),
                ),
            )
        return (
            "refuted",
            (
                f"left_dimensions:{','.join(sorted(left_dimensions))}",
                f"right_dimensions:{','.join(sorted(right_dimensions))}",
            ),
        )
    return "unresolved", ("no_assertion_capable_target_alignment",)


def _structural(
    obligation: RelationObligationSpec,
    from_field: ParsedField | None,
    to_field: ParsedField | None,
    *,
    rule: str,
) -> DirectRelationAssessment:
    if from_field is None or to_field is None:
        return DirectRelationAssessment(
            obligation_id=obligation.obligation_id,
            outcome="unresolved",
            rule_id=rule,
            from_field=obligation.from_role,
            to_field=obligation.to_role,
            evidence_spans=_spans(from_field, to_field),
            basis=(),
            unknown_reasons=("required_endpoint_missing_or_ambiguous",),
        )
    return DirectRelationAssessment(
        obligation_id=obligation.obligation_id,
        outcome="supported",
        rule_id=rule,
        from_field=obligation.from_role,
        to_field=obligation.to_role,
        evidence_spans=_spans(from_field, to_field),
        basis=("same_closed_structured_record",),
    )


def _aligned_relation(
    obligation: RelationObligationSpec,
    from_field: ParsedField | None,
    to_field: ParsedField | None,
    *,
    rule: str,
    allow_dimension_only: bool = False,
) -> DirectRelationAssessment:
    """Require an assertion-capable semantic anchor, not field co-location.

    This intentionally remains a bounded lexical rule.  When it cannot name a
    shared engineering dimension it yields ``unresolved`` and routes the record
    onward; it never treats mere presence of both fields as relation support.
    """

    outcome, reasons = _alignment(
        from_field,
        to_field,
        allow_dimension_only=allow_dimension_only,
    )
    return DirectRelationAssessment(
        obligation_id=obligation.obligation_id,
        outcome=outcome,
        rule_id=rule,
        from_field=obligation.from_role,
        to_field=obligation.to_role,
        evidence_spans=_spans(from_field, to_field),
        basis=reasons if outcome != "unresolved" else (),
        unknown_reasons=reasons if outcome == "unresolved" else (),
    )


def evaluate_direct_relations(
    record: ParsedRequirementRecord,
    profile: NormativeProfile = FUNCTIONAL_REQUIREMENT_PROFILE,
) -> tuple[DirectRelationAssessment, ...]:
    purpose = record.one("purpose")
    user = record.one("user")
    scenario = record.one("scenario")
    expected = record.one("expected_result")
    criterion = record.one("acceptance_criteria")
    method = record.one("verification_method")
    evidence = record.one("evidence")
    by_id = {item.obligation_id: item for item in profile.obligations}
    results: list[DirectRelationAssessment] = []

    results.append(
        _aligned_relation(
            by_id["func.applies_to"],
            purpose,
            user,
            rule="direct.dimension.applies-to/v2",
            allow_dimension_only=True,
        )
    )

    performs = _structural(
        by_id["func.performs"], user, scenario, rule="direct.structured.actor-scenario/v2"
    )
    if performs.outcome == "supported" and user is not None and scenario is not None:
        actor_supported, actor_reason = _actor_assertion(user.value, scenario.value)
        if actor_supported:
            performs = DirectRelationAssessment(
                obligation_id=performs.obligation_id,
                outcome="supported",
                rule_id=performs.rule_id,
                from_field=performs.from_field,
                to_field=performs.to_field,
                evidence_spans=performs.evidence_spans,
                basis=(actor_reason,),
            )
        else:
            performs = DirectRelationAssessment(
                obligation_id=performs.obligation_id,
                outcome="unresolved",
                rule_id=performs.rule_id,
                from_field=performs.from_field,
                to_field=performs.to_field,
                evidence_spans=performs.evidence_spans,
                basis=(),
                unknown_reasons=(actor_reason,),
            )
    results.append(performs)

    object_match = OBJECT_PATTERN.search(scenario.value) if scenario else None
    object_value = _object_value(object_match)
    acts_on = by_id["func.acts_on"]
    results.append(
        DirectRelationAssessment(
            obligation_id=acts_on.obligation_id,
            outcome="supported" if object_value else "unresolved",
            rule_id="direct.structured.object-marker/v0",
            from_field=acts_on.from_role,
            to_field=acts_on.to_role,
            evidence_spans=_span(scenario),
            basis=(f"object_marker:{object_value}",) if object_value else (),
            unknown_reasons=() if object_value else ("object_applicability_not_established",),
        )
    )

    condition_match = CONDITION_PATTERN.search(scenario.value) if scenario else None
    triggered = by_id["func.triggered_by"]
    results.append(
        DirectRelationAssessment(
            obligation_id=triggered.obligation_id,
            outcome="supported" if condition_match else "not_applicable",
            rule_id="direct.structured.condition-marker/v0",
            from_field=triggered.from_role,
            to_field=triggered.to_role,
            evidence_spans=_span(scenario),
            basis=(f"condition_marker:{condition_match.group(0)}",) if condition_match else ("no_explicit_condition_marker",),
        )
    )

    produces_outcome, produces_basis = _produces_alignment(scenario, expected)
    produces = by_id["func.produces"]
    results.append(
        DirectRelationAssessment(
            obligation_id=produces.obligation_id,
            outcome=produces_outcome,
            rule_id="direct.structured.scenario-result-alignment/v2",
            from_field=produces.from_role,
            to_field=produces.to_role,
            evidence_spans=_spans(scenario, expected),
            basis=produces_basis if produces_outcome != "unresolved" else (),
            unknown_reasons=produces_basis if produces_outcome == "unresolved" else (),
        )
    )

    constrained_outcome, constrained_basis = _alignment(expected, criterion)
    constrained = by_id["func.constrained_by"]
    results.append(
        DirectRelationAssessment(
            obligation_id=constrained.obligation_id,
            outcome=constrained_outcome,
            rule_id="direct.structured.result-criterion-alignment/v1",
            from_field=constrained.from_role,
            to_field=constrained.to_role,
            evidence_spans=_spans(expected, criterion),
            basis=constrained_basis if constrained_outcome != "unresolved" else (),
            unknown_reasons=constrained_basis if constrained_outcome == "unresolved" else (),
        )
    )

    metric_present = bool(criterion and METRIC_PATTERN.search(criterion.value))
    uses_metric = by_id["func.uses_metric"]
    results.append(
        DirectRelationAssessment(
            obligation_id=uses_metric.obligation_id,
            outcome="supported" if metric_present else "not_applicable",
            rule_id="direct.structured.metric-marker/v0",
            from_field=uses_metric.from_role,
            to_field=uses_metric.to_role,
            evidence_spans=_span(criterion),
            basis=("metric_marker_present",) if metric_present else ("no_metric_marker",),
        )
    )

    results.append(
        _aligned_relation(
            by_id["func.verified_by"],
            purpose,
            method,
            rule="direct.dimension.verified-by/v2",
        )
    )

    verifies_outcome, verifies_basis = _alignment(method, criterion)
    verifies = by_id["func.verifies"]
    results.append(
        DirectRelationAssessment(
            obligation_id=verifies.obligation_id,
            outcome=verifies_outcome,
            rule_id="direct.structured.verification-target-alignment/v1",
            from_field=verifies.from_role,
            to_field=verifies.to_role,
            evidence_spans=_spans(method, criterion),
            basis=verifies_basis if verifies_outcome != "unresolved" else (),
            unknown_reasons=verifies_basis if verifies_outcome == "unresolved" else (),
        )
    )

    measures = by_id["func.measures"]
    if not metric_present:
        measures_outcome: DirectOutcome = "not_applicable"
        measures_basis = ("no_metric_marker",)
    else:
        measures_outcome, measures_basis = _alignment(method, criterion)
    results.append(
        DirectRelationAssessment(
            obligation_id=measures.obligation_id,
            outcome=measures_outcome,
            rule_id="direct.structured.metric-target-alignment/v1",
            from_field=measures.from_role,
            to_field=measures.to_role,
            evidence_spans=_spans(method, criterion),
            basis=measures_basis if measures_outcome != "unresolved" else (),
            unknown_reasons=measures_basis if measures_outcome == "unresolved" else (),
        )
    )

    evidence_outcome, evidence_basis = _alignment(method, evidence)
    if method is not None and evidence is not None and evidence_outcome == "unresolved":
        shared_ascii = {
            token.casefold()
            for token in re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", method.value)
        } & {
            token.casefold()
            for token in re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", evidence.value)
        }
        shared_ascii -= GENERIC_CONTENT_ANCHORS
        if shared_ascii:
            evidence_outcome = "supported"
            evidence_basis = tuple(f"shared_artifact_term:{item}" for item in sorted(shared_ascii))
    evidence_obligation = by_id["func.produces_evidence"]
    results.append(
        DirectRelationAssessment(
            obligation_id=evidence_obligation.obligation_id,
            outcome=evidence_outcome,
            rule_id="direct.structured.method-evidence-alignment/v1",
            from_field=evidence_obligation.from_role,
            to_field=evidence_obligation.to_role,
            evidence_spans=_spans(method, evidence),
            basis=evidence_basis if evidence_outcome != "unresolved" else (),
            unknown_reasons=evidence_basis if evidence_outcome == "unresolved" else (),
        )
    )

    if len(results) != len(profile.obligations):
        raise AssertionError("every profile obligation must have exactly one direct assessment")
    return tuple(results)
