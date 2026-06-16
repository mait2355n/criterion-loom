from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Mapping

FactStatus = Literal["present", "absent", "candidate", "rejected", "unknown", "conflict"]
DerivationStatus = Literal[
    "derived",
    "not_derived",
    "blocked_by_unknown",
    "conflict",
    "not_applicable",
    "satisfied",
]
FactSourceKind = Literal[
    "input_kind",
    "deterministic_extractor",
    "requirement_profile",
    "requirement_structure",
    "candidate_match",
    "context",
    "trace_vocabulary",
    "llm_reviewer",
    "human_decision",
]
ObligationStatus = Literal["satisfied", "missing", "unknown", "conflict", "not_applicable"]
CounterconditionStatus = Literal["present", "absent", "unknown", "conflict"]
CounterconditionEffect = Literal["not_applicable", "satisfied", "continue", "defer"]

LOGICAL_TRACE_SCHEMA_VERSION = "logical-trace/v1"
LOGICAL_DERIVATION_SCHEMA_VERSION = "logical-derivation/v1"
DERIVATION_SCOPE = "rule-and-fact derivation only; not natural-language truth or final acceptance"
LOGICAL_TRACE_SCOPE = "extracted facts and executable predicates only"
FACT_STATUSES_THAT_SATISFY_OBLIGATION = frozenset({"present"})
ACCEPTANCE_MISSING_RULE_ID = "req.verifiability.acceptance_missing"
ACCEPTANCE_MISSING_PREDICATE_ID = "req.verifiability.acceptance_missing/v1"
ACCEPTANCE_MISSING_FINDING_ID = "finding.req.verifiability.acceptance_missing"
ACHIEVEMENT_CRITERIA_RULE_ID = "req.achievement.criteria_missing"
ACHIEVEMENT_CRITERIA_PREDICATE_ID = "req.achievement.criteria_missing/v1"
ACHIEVEMENT_CRITERIA_FINDING_ID = "finding.req.achievement.criteria_missing"
METHOD_DETAIL_RULE_ID = "req.verification.method_detail_missing"
METHOD_DETAIL_PREDICATE_ID = "req.verification.method_detail_missing/v1"
METHOD_DETAIL_FINDING_ID = "finding.req.verification.method_detail_missing"
EVIDENCE_ARTIFACT_RULE_ID = "req.evidence.artifact_missing"
EVIDENCE_ARTIFACT_PREDICATE_ID = "req.evidence.artifact_missing/v1"
EVIDENCE_ARTIFACT_FINDING_ID = "finding.req.evidence.artifact_missing"
REJECTION_CONDITION_RULE_ID = "req.acceptance.rejection_condition_missing"
REJECTION_CONDITION_PREDICATE_ID = "req.acceptance.rejection_condition_missing/v1"
REJECTION_CONDITION_FINDING_ID = "finding.req.acceptance.rejection_condition_missing"
SCENARIO_CONTEXT_RULE_ID = "req.context.scenario_missing"
SCENARIO_CONTEXT_PREDICATE_ID = "req.context.scenario_missing/v1"
SCENARIO_CONTEXT_FINDING_ID = "finding.req.context.scenario_missing"
OBSERVABLE_BEHAVIOR_RULE_ID = "req.structure.observable_behavior_missing"
OBSERVABLE_BEHAVIOR_PREDICATE_ID = "req.structure.observable_behavior_missing/v1"
OBSERVABLE_BEHAVIOR_FINDING_ID = "finding.req.structure.observable_behavior_missing"
ACCEPTANCE_MISSING_VERIFICATION_TERMS = (
    "検証",
    "確認",
    "試験",
    "テスト",
    "検査",
    "受入",
    "受入基準",
    "acceptance",
    "verify",
    "test",
    "evidence",
)
ACCEPTANCE_CRITERIA_TERMS = (
    "受入基準",
    "受入条件",
    "合格条件",
    "完了条件",
    "成功状態",
    "Definition of Done",
    "acceptance criteria",
    "pass condition",
)
VERIFICATION_METHOD_TERMS = (
    "pytest",
    "unittest",
    "ベンチマーク",
    "測定",
    "解析",
    "検査",
    "実演",
    "レビュー",
    "代表 CLI",
    "コマンド",
)
EVIDENCE_ARTIFACT_TERMS = (
    "証拠",
    "証跡",
    "試験結果",
    "コマンド結果",
    "ログ",
    "スクリーンショット",
    "出力 JSON",
    "レビュー記録",
    "report",
    "artifact",
)
REJECTION_CONDITION_SCOPE_TERMS = (
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
)
REJECTION_CONDITION_TERMS = (
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
)
SCENARIO_CONTEXT_SCOPE_TERMS = (
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
)
SCENARIO_CONTEXT_TERMS = (
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
)
VAGUE_BEHAVIOR_TERMS = (
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
)
OBSERVABLE_BEHAVIOR_TERMS = (
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
)
EXTERNAL_ACCEPTANCE_ROUTE_TERMS = (
    "外部受入",
    "別途受入",
    "受入判断は人間",
    "人間が受入",
    "ユーザーが受入",
    "acceptance_review_bundle",
    "external acceptance",
    "human acceptance",
)


@dataclass
class FactSource:
    kind: FactSourceKind
    label: str = ""
    detail: str = ""

    def as_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {"kind": self.kind}
        if self.label:
            payload["label"] = self.label
        if self.detail:
            payload["detail"] = self.detail
        return payload


@dataclass
class EvidenceSpan:
    source: str
    field: str = ""
    excerpt: str = ""
    start: int | None = None
    end: int | None = None

    def as_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {"source": self.source}
        if self.field:
            payload["field"] = self.field
        if self.excerpt:
            payload["excerpt"] = self.excerpt
        if self.start is not None:
            payload["start"] = self.start
        if self.end is not None:
            payload["end"] = self.end
        return payload


@dataclass
class Fact:
    id: str
    name: str
    status: FactStatus = "unknown"
    source: FactSource = field(default_factory=lambda: FactSource(kind="deterministic_extractor"))
    value: Any | None = None
    evidence: list[EvidenceSpan] = field(default_factory=list)
    extraction_method: str = ""
    confidence: str = ""
    notes: str = ""
    checked_scope: str = ""

    def as_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "source": self.source.as_dict(),
            "evidence": [span.as_dict() for span in self.evidence],
            "extraction_method": self.extraction_method,
        }
        if self.value is not None:
            payload["value"] = self.value
        if self.confidence:
            payload["confidence"] = self.confidence
        if self.notes:
            payload["notes"] = self.notes
        if self.checked_scope:
            payload["checked_scope"] = self.checked_scope
        return payload


@dataclass
class Obligation:
    id: str
    rule_id: str
    description: str
    required_facts: list[str] = field(default_factory=list)
    status: ObligationStatus = "unknown"
    missing_fact_names: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "rule_id": self.rule_id,
            "description": self.description,
            "required_facts": self.required_facts,
            "status": self.status,
            "missing_fact_names": self.missing_fact_names,
        }


@dataclass
class Countercondition:
    id: str
    rule_id: str
    description: str
    checked_facts: list[str] = field(default_factory=list)
    status: CounterconditionStatus = "unknown"
    effect: CounterconditionEffect = "defer"

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "rule_id": self.rule_id,
            "description": self.description,
            "checked_facts": self.checked_facts,
            "status": self.status,
            "effect": self.effect,
        }


@dataclass
class RuleEvaluation:
    rule_id: str
    phase: str
    predicate_id: str
    status: DerivationStatus = "not_derived"
    facts_used: list[str] = field(default_factory=list)
    counterconditions_checked: list[str] = field(default_factory=list)
    obligations: list[str] = field(default_factory=list)
    finding_ids: list[str] = field(default_factory=list)
    derivation_steps: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return {
            "rule_id": self.rule_id,
            "phase": self.phase,
            "predicate_id": self.predicate_id,
            "status": self.status,
            "facts_used": self.facts_used,
            "counterconditions_checked": self.counterconditions_checked,
            "obligations": self.obligations,
            "finding_ids": self.finding_ids,
            "derivation_steps": self.derivation_steps,
        }


@dataclass
class DerivationStep:
    id: str
    statement: str
    from_ids: list[str] = field(default_factory=list)
    to: str = ""
    operator: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "statement": self.statement,
            "from": self.from_ids,
            "to": self.to,
            "operator": self.operator,
        }


@dataclass
class LogicalTrace:
    phase: str
    schema_version: str = LOGICAL_TRACE_SCHEMA_VERSION
    scope: str = LOGICAL_TRACE_SCOPE
    derivation_scope: str = DERIVATION_SCOPE
    rules_evaluated: list[RuleEvaluation] = field(default_factory=list)
    facts: list[Fact] = field(default_factory=list)
    obligations: list[Obligation] = field(default_factory=list)
    counterconditions: list[Countercondition] = field(default_factory=list)
    derivation_steps: list[DerivationStep] = field(default_factory=list)
    unknowns: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "scope": self.scope,
            "derivation_scope": self.derivation_scope,
            "phase": self.phase,
            "rules_evaluated": [rule.as_dict() for rule in self.rules_evaluated],
            "facts": [fact.as_dict() for fact in self.facts],
            "obligations": [obligation.as_dict() for obligation in self.obligations],
            "counterconditions": [countercondition.as_dict() for countercondition in self.counterconditions],
            "derivation_steps": [step.as_dict() for step in self.derivation_steps],
            "unknowns": self.unknowns,
            "conflicts": self.conflicts,
        }


def build_request_verification_trace(
    *,
    text: str,
    context: str = "",
    input_kind: str = "requirement",
    requirement_profile: Mapping[str, str] | None = None,
    requirement_structure: Mapping[str, str] | None = None,
) -> LogicalTrace:
    profile = requirement_profile or {}
    structure = requirement_structure or {}
    combined = _combine_text(text, context)
    facts = [
        _input_kind_requirement_fact(input_kind),
        _text_fact(
            name="text.has_verification_language",
            terms=ACCEPTANCE_MISSING_VERIFICATION_TERMS,
            text=text,
            context=context,
            extraction_method="known_verification_or_acceptance_terms",
        ),
        _text_fact(
            name="text.has_acceptance_criteria",
            terms=ACCEPTANCE_CRITERIA_TERMS,
            text=text,
            context=context,
            profile_value=profile.get("acceptance_criteria", ""),
            profile_key="acceptance_criteria",
            extraction_method="requirement_profile_or_acceptance_terms",
        ),
        _text_fact(
            name="text.has_verification_method",
            terms=VERIFICATION_METHOD_TERMS,
            text=text,
            context=context,
            profile_value=profile.get("verification_method", ""),
            profile_key="verification_method",
            extraction_method="requirement_profile_or_method_terms",
        ),
        _text_fact(
            name="text.has_evidence_artifact",
            terms=EVIDENCE_ARTIFACT_TERMS,
            text=text,
            context=context,
            profile_value=profile.get("evidence_artifact", ""),
            profile_key="evidence_artifact",
            extraction_method="requirement_profile_or_evidence_terms",
        ),
        _text_fact(
            name="text.has_rejection_condition",
            terms=REJECTION_CONDITION_TERMS,
            text=text,
            context=context,
            profile_value=profile.get("rejection_condition", ""),
            profile_key="rejection_condition",
            extraction_method="requirement_profile_or_rejection_terms",
        ),
        _text_fact(
            name="text.requires_rejection_condition",
            terms=REJECTION_CONDITION_SCOPE_TERMS,
            text=text,
            context=context,
            extraction_method="deterministic_rejection_scope_terms",
        ),
        _text_fact(
            name="text.has_scenario_context",
            terms=SCENARIO_CONTEXT_TERMS,
            text=text,
            context=context,
            profile_value=profile.get("scenario_context", ""),
            profile_key="scenario_context",
            extraction_method="requirement_profile_or_scenario_terms",
        ),
        _text_fact(
            name="text.requires_scenario_context",
            terms=SCENARIO_CONTEXT_SCOPE_TERMS,
            text=text,
            context=context,
            extraction_method="deterministic_scenario_scope_terms",
        ),
        _text_fact(
            name="text.has_vague_behavior_request",
            terms=VAGUE_BEHAVIOR_TERMS,
            text=text,
            context=context,
            extraction_method="deterministic_vague_behavior_terms",
        ),
        _text_fact(
            name="text.has_observable_behavior",
            terms=OBSERVABLE_BEHAVIOR_TERMS,
            text=text,
            context=context,
            profile_value=structure.get("observable_behavior", ""),
            profile_key="observable_behavior",
            profile_source_kind="requirement_structure",
            extraction_method="requirement_structure_or_observable_terms",
        ),
        _text_fact(
            name="context.has_external_acceptance_route",
            terms=EXTERNAL_ACCEPTANCE_ROUTE_TERMS,
            text="",
            context=context,
            extraction_method="context_external_acceptance_terms",
        ),
    ]
    fact_by_name = {fact.name: fact for fact in facts}
    acceptance_counterconditions = _acceptance_missing_counterconditions(fact_by_name)
    acceptance_obligations = _acceptance_missing_obligations(fact_by_name)
    acceptance_status = _acceptance_missing_rule_status(acceptance_counterconditions, acceptance_obligations)
    acceptance_steps = _acceptance_missing_derivation_steps(
        acceptance_status,
        facts,
        acceptance_counterconditions,
        acceptance_obligations,
        bool(combined.strip()),
    )
    achievement_rule, achievement_counterconditions, achievement_obligations, achievement_steps = _build_scoped_missing_rule(
        facts=fact_by_name,
        has_text=bool(combined.strip()),
        rule_id=ACHIEVEMENT_CRITERIA_RULE_ID,
        predicate_id=ACHIEVEMENT_CRITERIA_PREDICATE_ID,
        finding_id=ACHIEVEMENT_CRITERIA_FINDING_ID,
        step_prefix="req.achievement",
        required_fact_name="text.has_acceptance_criteria",
        scope_fact_names=["text.has_verification_language", "text.has_acceptance_criteria", "text.has_verification_method"],
        obligation_id="obl.req.achievement.criteria",
        obligation_description="Requirement must state acceptance criteria, a pass condition, a success state, or equivalent achievement criteria when verification is in scope.",
        scope_countercondition_id="ctr.req.achievement.criteria_not_in_scope",
        scope_countercondition_description="Rule does not apply when verification or acceptance is not in scope.",
        extract_statement="Caller-supplied input kind and deterministic achievement-criteria facts were extracted.",
        countercondition_statement="Counterconditions were checked before deriving the achievement-criteria rule.",
        derived_statement="Verification or acceptance is in scope, but no acceptance-criteria fact was accepted, so the target finding is derived.",
        satisfied_statement="An acceptance-criteria fact is accepted in scope, so the target rule is satisfied.",
        not_applicable_statement="The input is not a requirement or achievement criteria are not in scope, so the target rule is not applicable.",
    )
    method_counterconditions = _method_detail_counterconditions(fact_by_name)
    method_obligations = _method_detail_obligations(fact_by_name)
    method_status = _method_detail_rule_status(method_counterconditions, method_obligations)
    method_steps = _method_detail_derivation_steps(
        method_status,
        facts,
        method_counterconditions,
        method_obligations,
        bool(combined.strip()),
    )
    evidence_rule, evidence_counterconditions, evidence_obligations, evidence_steps = _build_scoped_missing_rule(
        facts=fact_by_name,
        has_text=bool(combined.strip()),
        rule_id=EVIDENCE_ARTIFACT_RULE_ID,
        predicate_id=EVIDENCE_ARTIFACT_PREDICATE_ID,
        finding_id=EVIDENCE_ARTIFACT_FINDING_ID,
        step_prefix="req.evidence",
        required_fact_name="text.has_evidence_artifact",
        scope_fact_names=["text.has_verification_language", "text.has_acceptance_criteria", "text.has_verification_method"],
        obligation_id="obl.req.evidence.artifact",
        obligation_description="Requirement must name the retained evidence artifact when verification or acceptance is in scope.",
        scope_countercondition_id="ctr.req.evidence.verification_not_in_scope",
        scope_countercondition_description="Rule does not apply when verification or acceptance is not in scope.",
        extract_statement="Caller-supplied input kind and deterministic evidence-artifact facts were extracted.",
        countercondition_statement="Counterconditions were checked before deriving the evidence-artifact rule.",
        derived_statement="Verification or acceptance is in scope, but no retained evidence-artifact fact was accepted, so the target finding is derived.",
        satisfied_statement="A retained evidence-artifact fact is accepted in scope, so the target rule is satisfied.",
        not_applicable_statement="The input is not a requirement or evidence is not in scope, so the target rule is not applicable.",
    )
    rejection_rule, rejection_counterconditions, rejection_obligations, rejection_steps = _build_scoped_missing_rule(
        facts=fact_by_name,
        has_text=bool(combined.strip()),
        rule_id=REJECTION_CONDITION_RULE_ID,
        predicate_id=REJECTION_CONDITION_PREDICATE_ID,
        finding_id=REJECTION_CONDITION_FINDING_ID,
        step_prefix="req.rejection",
        required_fact_name="text.has_rejection_condition",
        scope_fact_names=["text.requires_rejection_condition"],
        obligation_id="obl.req.acceptance.rejection_condition",
        obligation_description="Requirement must state a rejection, fail, rollback, or defer condition when the requirement touches high-impact scope.",
        scope_countercondition_id="ctr.req.acceptance.rejection_not_in_scope",
        scope_countercondition_description="Rule does not apply when high-impact rejection-condition scope is not present.",
        extract_statement="Caller-supplied input kind and deterministic rejection-condition facts were extracted.",
        countercondition_statement="Counterconditions were checked before deriving the rejection-condition rule.",
        derived_statement="High-impact requirement scope is present, but no rejection-condition fact was accepted, so the target finding is derived.",
        satisfied_statement="A rejection-condition fact is accepted in scope, so the target rule is satisfied.",
        not_applicable_statement="The input is not a requirement or rejection-condition scope is not present, so the target rule is not applicable.",
    )
    scenario_rule, scenario_counterconditions, scenario_obligations, scenario_steps = _build_scoped_missing_rule(
        facts=fact_by_name,
        has_text=bool(combined.strip()),
        rule_id=SCENARIO_CONTEXT_RULE_ID,
        predicate_id=SCENARIO_CONTEXT_PREDICATE_ID,
        finding_id=SCENARIO_CONTEXT_FINDING_ID,
        step_prefix="req.scenario",
        required_fact_name="text.has_scenario_context",
        scope_fact_names=["text.requires_scenario_context"],
        obligation_id="obl.req.context.scenario",
        obligation_description="Requirement must state scenario context when user-facing or input/output scope is present.",
        scope_countercondition_id="ctr.req.context.scenario_not_in_scope",
        scope_countercondition_description="Rule does not apply when scenario context does not affect the requirement scope.",
        extract_statement="Caller-supplied input kind and deterministic scenario-context facts were extracted.",
        countercondition_statement="Counterconditions were checked before deriving the scenario-context rule.",
        derived_statement="User-facing or input/output scope is present, but no scenario-context fact was accepted, so the target finding is derived.",
        satisfied_statement="A scenario-context fact is accepted in scope, so the target rule is satisfied.",
        not_applicable_statement="The input is not a requirement or scenario context is not in scope, so the target rule is not applicable.",
    )
    observable_rule, observable_counterconditions, observable_obligations, observable_steps = _build_scoped_missing_rule(
        facts=fact_by_name,
        has_text=bool(combined.strip()),
        rule_id=OBSERVABLE_BEHAVIOR_RULE_ID,
        predicate_id=OBSERVABLE_BEHAVIOR_PREDICATE_ID,
        finding_id=OBSERVABLE_BEHAVIOR_FINDING_ID,
        step_prefix="req.observable",
        required_fact_name="text.has_observable_behavior",
        scope_fact_names=["text.has_vague_behavior_request"],
        obligation_id="obl.req.structure.observable_behavior",
        obligation_description="Requirement must state observable behavior when it is phrased as a vague improvement or support request.",
        scope_countercondition_id="ctr.req.structure.observable_behavior_not_in_scope",
        scope_countercondition_description="Rule does not apply when the request is not phrased as a vague behavior request.",
        extract_statement="Caller-supplied input kind and deterministic observable-behavior facts were extracted.",
        countercondition_statement="Counterconditions were checked before deriving the observable-behavior rule.",
        derived_statement="A vague behavior request is present, but no observable-behavior fact was accepted, so the target finding is derived.",
        satisfied_statement="An observable-behavior fact is accepted in scope, so the target rule is satisfied.",
        not_applicable_statement="The input is not a requirement or observable behavior is not in scope, so the target rule is not applicable.",
    )
    acceptance_rule = RuleEvaluation(
        rule_id=ACCEPTANCE_MISSING_RULE_ID,
        phase="audit_request",
        predicate_id=ACCEPTANCE_MISSING_PREDICATE_ID,
        status=acceptance_status,
        facts_used=[fact.id for fact in facts],
        counterconditions_checked=[countercondition.id for countercondition in acceptance_counterconditions],
        obligations=[obligation.id for obligation in acceptance_obligations],
        finding_ids=[ACCEPTANCE_MISSING_FINDING_ID] if acceptance_status == "derived" else [],
        derivation_steps=[step.id for step in acceptance_steps],
    )
    method_rule = RuleEvaluation(
        rule_id=METHOD_DETAIL_RULE_ID,
        phase="audit_request",
        predicate_id=METHOD_DETAIL_PREDICATE_ID,
        status=method_status,
        facts_used=[fact.id for fact in facts],
        counterconditions_checked=[countercondition.id for countercondition in method_counterconditions],
        obligations=[obligation.id for obligation in method_obligations],
        finding_ids=[METHOD_DETAIL_FINDING_ID] if method_status == "derived" else [],
        derivation_steps=[step.id for step in method_steps],
    )
    return LogicalTrace(
        phase="audit_request",
        rules_evaluated=[
            acceptance_rule,
            achievement_rule,
            method_rule,
            evidence_rule,
            rejection_rule,
            scenario_rule,
            observable_rule,
        ],
        facts=facts,
        obligations=(
            acceptance_obligations
            + achievement_obligations
            + method_obligations
            + evidence_obligations
            + rejection_obligations
            + scenario_obligations
            + observable_obligations
        ),
        counterconditions=(
            acceptance_counterconditions
            + achievement_counterconditions
            + method_counterconditions
            + evidence_counterconditions
            + rejection_counterconditions
            + scenario_counterconditions
            + observable_counterconditions
        ),
        derivation_steps=(
            acceptance_steps
            + achievement_steps
            + method_steps
            + evidence_steps
            + rejection_steps
            + scenario_steps
            + observable_steps
        ),
        unknowns=[fact.name for fact in facts if fact.status == "unknown"],
        conflicts=[fact.name for fact in facts if fact.status == "conflict"],
    )


def build_acceptance_missing_trace(
    *,
    text: str,
    context: str = "",
    input_kind: str = "requirement",
    requirement_profile: Mapping[str, str] | None = None,
    requirement_structure: Mapping[str, str] | None = None,
) -> LogicalTrace:
    return build_request_verification_trace(
        text=text,
        context=context,
        input_kind=input_kind,
        requirement_profile=requirement_profile,
        requirement_structure=requirement_structure,
    )


def derivation_for_rule(trace: LogicalTrace, rule_id: str = ACCEPTANCE_MISSING_RULE_ID) -> dict[str, object]:
    rule = next((item for item in trace.rules_evaluated if item.rule_id == rule_id), None)
    if rule is None:
        return {}

    fact_by_id = {fact.id: fact for fact in trace.facts}
    countercondition_by_id = {countercondition.id: countercondition for countercondition in trace.counterconditions}
    step_by_id = {step.id: step for step in trace.derivation_steps}
    return {
        "schema_version": LOGICAL_DERIVATION_SCHEMA_VERSION,
        "derivation_scope": trace.derivation_scope,
        "rule_id": rule.rule_id,
        "status": rule.status,
        "facts_used": [fact_by_id[fact_id].as_dict() for fact_id in rule.facts_used if fact_id in fact_by_id],
        "counterconditions_checked": [
            countercondition_by_id[countercondition_id].as_dict()
            for countercondition_id in rule.counterconditions_checked
            if countercondition_id in countercondition_by_id
        ],
        "missing_obligations": [
            obligation.as_dict()
            for obligation in trace.obligations
            if obligation.rule_id == rule.rule_id and obligation.status in {"missing", "unknown", "conflict"}
        ],
        "derivation_steps": [step_by_id[step_id].as_dict() for step_id in rule.derivation_steps if step_id in step_by_id],
        "unresolved_unknowns": trace.unknowns,
    }


def _acceptance_missing_counterconditions(facts: Mapping[str, Fact]) -> list[Countercondition]:
    input_kind_fact = facts["input.kind.requirement"]
    external_route_fact = facts["context.has_external_acceptance_route"]
    return [
        Countercondition(
            id="ctr.req.verifiability.input_kind_not_requirement",
            rule_id=ACCEPTANCE_MISSING_RULE_ID,
            description="Rule does not apply when the input kind is not requirement.",
            checked_facts=[input_kind_fact.id],
            status="absent" if input_kind_fact.status == "present" else "present",
            effect="continue" if input_kind_fact.status == "present" else "not_applicable",
        ),
        Countercondition(
            id="ctr.req.verifiability.external_acceptance_route",
            rule_id=ACCEPTANCE_MISSING_RULE_ID,
            description="Rule does not apply when context supplies an explicit external acceptance route.",
            checked_facts=[external_route_fact.id],
            status="present" if external_route_fact.status == "present" else "absent",
            effect="not_applicable" if external_route_fact.status == "present" else "continue",
        ),
    ]


def _acceptance_missing_obligations(facts: Mapping[str, Fact]) -> list[Obligation]:
    verification_language = facts["text.has_verification_language"]
    acceptance_criteria = facts["text.has_acceptance_criteria"]
    verification_method = facts["text.has_verification_method"]
    evidence_artifact = facts["text.has_evidence_artifact"]
    has_any_acceptance_route = _fact_is_present(verification_language) or _fact_is_present(acceptance_criteria)
    verification_claimed = _fact_is_present(verification_language) or _fact_is_present(verification_method)
    return [
        Obligation(
            id="obl.req.verifiability.verification_or_acceptance",
            rule_id=ACCEPTANCE_MISSING_RULE_ID,
            description="Requirement must state a verification, confirmation, evidence, or acceptance route.",
            required_facts=[verification_language.id, acceptance_criteria.id],
            status="satisfied" if has_any_acceptance_route else "missing",
            missing_fact_names=[] if has_any_acceptance_route else [verification_language.name, acceptance_criteria.name],
        ),
        Obligation(
            id="obl.req.verifiability.acceptance_criteria",
            rule_id=ACCEPTANCE_MISSING_RULE_ID,
            description="Requirement should name an acceptance criterion or success condition.",
            required_facts=[acceptance_criteria.id],
            status="satisfied" if _fact_is_present(acceptance_criteria) else "missing",
            missing_fact_names=[] if _fact_is_present(acceptance_criteria) else [acceptance_criteria.name],
        ),
        Obligation(
            id="obl.req.verifiability.verification_method",
            rule_id=ACCEPTANCE_MISSING_RULE_ID,
            description="Requirement should name a concrete verification method when verification is in scope.",
            required_facts=[verification_method.id],
            status="satisfied" if _fact_is_present(verification_method) else "missing",
            missing_fact_names=[] if _fact_is_present(verification_method) else [verification_method.name],
        ),
        Obligation(
            id="obl.req.verifiability.evidence_artifact",
            rule_id=ACCEPTANCE_MISSING_RULE_ID,
            description="Requirement should name a retained evidence artifact when verification is claimed.",
            required_facts=[evidence_artifact.id],
            status=(
                "satisfied"
                if _fact_is_present(evidence_artifact)
                else "missing"
                if verification_claimed
                else "not_applicable"
            ),
            missing_fact_names=[] if _fact_is_present(evidence_artifact) or not verification_claimed else [evidence_artifact.name],
        ),
    ]


def _acceptance_missing_rule_status(
    counterconditions: list[Countercondition],
    obligations: list[Obligation],
) -> DerivationStatus:
    if any(countercondition.effect == "not_applicable" and countercondition.status == "present" for countercondition in counterconditions):
        return "not_applicable"
    if any(obligation.status == "conflict" for obligation in obligations):
        return "conflict"
    if any(obligation.status == "unknown" for obligation in obligations):
        return "blocked_by_unknown"
    primary = next(obligation for obligation in obligations if obligation.id == "obl.req.verifiability.verification_or_acceptance")
    if primary.status == "missing":
        return "derived"
    if any(obligation.status == "missing" for obligation in obligations):
        return "not_derived"
    return "satisfied"


def _acceptance_missing_derivation_steps(
    status: DerivationStatus,
    facts: list[Fact],
    counterconditions: list[Countercondition],
    obligations: list[Obligation],
    has_text: bool,
) -> list[DerivationStep]:
    input_step = DerivationStep(
        id="step.req.verifiability.001",
        statement="Caller-supplied input kind and deterministic text facts were extracted.",
        from_ids=[fact.id for fact in facts],
        to="facts",
        operator="extract",
    )
    countercondition_step = DerivationStep(
        id="step.req.verifiability.002",
        statement="Counterconditions were checked before deriving the target rule.",
        from_ids=[countercondition.id for countercondition in counterconditions],
        to=ACCEPTANCE_MISSING_RULE_ID,
        operator="check_counterconditions",
    )
    derivation_statement = {
        "derived": (
            "No verification or acceptance fact was accepted by the deterministic extractor "
            "in the checked request/context scope, so the target finding is derived."
        ),
        "not_derived": (
            "The broad acceptance-route finding is not derived because its primary obligation is satisfied; "
            "narrower obligations may still be reviewed by other rules."
        ),
        "satisfied": "All obligations for the target rule are satisfied under the extracted facts.",
        "not_applicable": "An input-kind or external-acceptance-route countercondition makes the target rule not applicable.",
        "blocked_by_unknown": "A required fact is unknown, so derivation is blocked.",
        "conflict": "Conflicting facts prevent derivation.",
    }[status]
    if not has_text:
        derivation_statement += " The request text is empty, so absence facts are scoped to the supplied empty text."
    derivation_step = DerivationStep(
        id="step.req.verifiability.003",
        statement=derivation_statement,
        from_ids=[obligation.id for obligation in obligations] + [countercondition.id for countercondition in counterconditions],
        to=ACCEPTANCE_MISSING_RULE_ID,
        operator=status,
    )
    return [input_step, countercondition_step, derivation_step]


def _method_detail_counterconditions(facts: Mapping[str, Fact]) -> list[Countercondition]:
    input_kind_fact = facts["input.kind.requirement"]
    verification_language = facts["text.has_verification_language"]
    acceptance_criteria = facts["text.has_acceptance_criteria"]
    verification_in_scope = _fact_is_present(verification_language) or _fact_is_present(acceptance_criteria)
    return [
        Countercondition(
            id="ctr.req.verification.input_kind_not_requirement",
            rule_id=METHOD_DETAIL_RULE_ID,
            description="Rule does not apply when the input kind is not requirement.",
            checked_facts=[input_kind_fact.id],
            status="absent" if input_kind_fact.status == "present" else "present",
            effect="continue" if input_kind_fact.status == "present" else "not_applicable",
        ),
        Countercondition(
            id="ctr.req.verification.verification_not_in_scope",
            rule_id=METHOD_DETAIL_RULE_ID,
            description="Rule does not apply when verification or acceptance is not in scope.",
            checked_facts=[verification_language.id, acceptance_criteria.id],
            status="absent" if verification_in_scope else "present",
            effect="continue" if verification_in_scope else "not_applicable",
        ),
    ]


def _method_detail_obligations(facts: Mapping[str, Fact]) -> list[Obligation]:
    verification_language = facts["text.has_verification_language"]
    acceptance_criteria = facts["text.has_acceptance_criteria"]
    verification_method = facts["text.has_verification_method"]
    verification_in_scope = _fact_is_present(verification_language) or _fact_is_present(acceptance_criteria)
    return [
        Obligation(
            id="obl.req.verification.method_detail",
            rule_id=METHOD_DETAIL_RULE_ID,
            description="Requirement must name a concrete verification method when verification or acceptance is in scope.",
            required_facts=[verification_method.id],
            status=(
                "satisfied"
                if _fact_is_present(verification_method)
                else "missing"
                if verification_in_scope
                else "not_applicable"
            ),
            missing_fact_names=[] if _fact_is_present(verification_method) or not verification_in_scope else [verification_method.name],
        )
    ]


def _method_detail_rule_status(
    counterconditions: list[Countercondition],
    obligations: list[Obligation],
) -> DerivationStatus:
    if any(countercondition.effect == "not_applicable" and countercondition.status == "present" for countercondition in counterconditions):
        return "not_applicable"
    if any(obligation.status == "conflict" for obligation in obligations):
        return "conflict"
    if any(obligation.status == "unknown" for obligation in obligations):
        return "blocked_by_unknown"
    primary = next(obligation for obligation in obligations if obligation.id == "obl.req.verification.method_detail")
    if primary.status == "missing":
        return "derived"
    return "satisfied"


def _method_detail_derivation_steps(
    status: DerivationStatus,
    facts: list[Fact],
    counterconditions: list[Countercondition],
    obligations: list[Obligation],
    has_text: bool,
) -> list[DerivationStep]:
    input_step = DerivationStep(
        id="step.req.verification.001",
        statement="Caller-supplied input kind and deterministic verification facts were extracted.",
        from_ids=[fact.id for fact in facts],
        to="facts",
        operator="extract",
    )
    countercondition_step = DerivationStep(
        id="step.req.verification.002",
        statement="Counterconditions were checked before deriving the verification-method rule.",
        from_ids=[countercondition.id for countercondition in counterconditions],
        to=METHOD_DETAIL_RULE_ID,
        operator="check_counterconditions",
    )
    derivation_statement = {
        "derived": (
            "Verification or acceptance language was accepted in the checked request/context scope, "
            "but no concrete verification method fact was accepted, so the target finding is derived."
        ),
        "not_derived": "The method-detail finding is not derived under the extracted facts.",
        "satisfied": "A concrete verification method fact is accepted in scope, so the target rule is satisfied.",
        "not_applicable": (
            "The input is not a requirement or verification/acceptance is not in scope, "
            "so the target rule is not applicable."
        ),
        "blocked_by_unknown": "A required fact is unknown, so derivation is blocked.",
        "conflict": "Conflicting facts prevent derivation.",
    }[status]
    if not has_text:
        derivation_statement += " The request text is empty, so absence facts are scoped to the supplied empty text."
    derivation_step = DerivationStep(
        id="step.req.verification.003",
        statement=derivation_statement,
        from_ids=[obligation.id for obligation in obligations] + [countercondition.id for countercondition in counterconditions],
        to=METHOD_DETAIL_RULE_ID,
        operator=status,
    )
    return [input_step, countercondition_step, derivation_step]


def _build_scoped_missing_rule(
    *,
    facts: Mapping[str, Fact],
    has_text: bool,
    rule_id: str,
    predicate_id: str,
    finding_id: str,
    step_prefix: str,
    required_fact_name: str,
    scope_fact_names: list[str],
    obligation_id: str,
    obligation_description: str,
    scope_countercondition_id: str,
    scope_countercondition_description: str,
    extract_statement: str,
    countercondition_statement: str,
    derived_statement: str,
    satisfied_statement: str,
    not_applicable_statement: str,
) -> tuple[RuleEvaluation, list[Countercondition], list[Obligation], list[DerivationStep]]:
    relevant_fact_names = _unique_fact_names(["input.kind.requirement", *scope_fact_names, required_fact_name])
    relevant_facts = [facts[name] for name in relevant_fact_names]
    scope_facts = [facts[name] for name in scope_fact_names]
    required_fact = facts[required_fact_name]
    in_scope = any(_fact_is_present(fact) for fact in scope_facts)
    counterconditions = [
        _input_kind_not_requirement_countercondition(
            facts,
            rule_id=rule_id,
            countercondition_id=f"ctr.{rule_id}.input_kind_not_requirement",
        ),
        Countercondition(
            id=scope_countercondition_id,
            rule_id=rule_id,
            description=scope_countercondition_description,
            checked_facts=[fact.id for fact in scope_facts],
            status="absent" if in_scope else "present",
            effect="continue" if in_scope else "not_applicable",
        ),
    ]
    obligations = [
        Obligation(
            id=obligation_id,
            rule_id=rule_id,
            description=obligation_description,
            required_facts=[required_fact.id],
            status=(
                "satisfied"
                if _fact_is_present(required_fact)
                else "missing"
                if in_scope
                else "not_applicable"
            ),
            missing_fact_names=[] if _fact_is_present(required_fact) or not in_scope else [required_fact.name],
        )
    ]
    status = _single_missing_rule_status(counterconditions, obligations, obligation_id)
    steps = _single_missing_derivation_steps(
        status=status,
        facts=relevant_facts,
        counterconditions=counterconditions,
        obligations=obligations,
        has_text=has_text,
        rule_id=rule_id,
        step_prefix=step_prefix,
        extract_statement=extract_statement,
        countercondition_statement=countercondition_statement,
        derived_statement=derived_statement,
        satisfied_statement=satisfied_statement,
        not_applicable_statement=not_applicable_statement,
    )
    rule = RuleEvaluation(
        rule_id=rule_id,
        phase="audit_request",
        predicate_id=predicate_id,
        status=status,
        facts_used=[fact.id for fact in relevant_facts],
        counterconditions_checked=[countercondition.id for countercondition in counterconditions],
        obligations=[obligation.id for obligation in obligations],
        finding_ids=[finding_id] if status == "derived" else [],
        derivation_steps=[step.id for step in steps],
    )
    return rule, counterconditions, obligations, steps


def _input_kind_not_requirement_countercondition(
    facts: Mapping[str, Fact],
    *,
    rule_id: str,
    countercondition_id: str,
) -> Countercondition:
    input_kind_fact = facts["input.kind.requirement"]
    return Countercondition(
        id=countercondition_id,
        rule_id=rule_id,
        description="Rule does not apply when the input kind is not requirement.",
        checked_facts=[input_kind_fact.id],
        status="absent" if input_kind_fact.status == "present" else "present",
        effect="continue" if input_kind_fact.status == "present" else "not_applicable",
    )


def _single_missing_rule_status(
    counterconditions: list[Countercondition],
    obligations: list[Obligation],
    primary_obligation_id: str,
) -> DerivationStatus:
    if any(countercondition.effect == "not_applicable" and countercondition.status == "present" for countercondition in counterconditions):
        return "not_applicable"
    if any(obligation.status == "conflict" for obligation in obligations):
        return "conflict"
    if any(obligation.status == "unknown" for obligation in obligations):
        return "blocked_by_unknown"
    primary = next(obligation for obligation in obligations if obligation.id == primary_obligation_id)
    if primary.status == "missing":
        return "derived"
    return "satisfied"


def _single_missing_derivation_steps(
    *,
    status: DerivationStatus,
    facts: list[Fact],
    counterconditions: list[Countercondition],
    obligations: list[Obligation],
    has_text: bool,
    rule_id: str,
    step_prefix: str,
    extract_statement: str,
    countercondition_statement: str,
    derived_statement: str,
    satisfied_statement: str,
    not_applicable_statement: str,
) -> list[DerivationStep]:
    input_step = DerivationStep(
        id=f"step.{step_prefix}.001",
        statement=extract_statement,
        from_ids=[fact.id for fact in facts],
        to="facts",
        operator="extract",
    )
    countercondition_step = DerivationStep(
        id=f"step.{step_prefix}.002",
        statement=countercondition_statement,
        from_ids=[countercondition.id for countercondition in counterconditions],
        to=rule_id,
        operator="check_counterconditions",
    )
    derivation_statement = {
        "derived": derived_statement,
        "not_derived": "The target finding is not derived under the extracted facts.",
        "satisfied": satisfied_statement,
        "not_applicable": not_applicable_statement,
        "blocked_by_unknown": "A required fact is unknown, so derivation is blocked.",
        "conflict": "Conflicting facts prevent derivation.",
    }[status]
    if not has_text:
        derivation_statement += " The request text is empty, so absence facts are scoped to the supplied empty text."
    derivation_step = DerivationStep(
        id=f"step.{step_prefix}.003",
        statement=derivation_statement,
        from_ids=[obligation.id for obligation in obligations] + [countercondition.id for countercondition in counterconditions],
        to=rule_id,
        operator=status,
    )
    return [input_step, countercondition_step, derivation_step]


def _unique_fact_names(names: list[str]) -> list[str]:
    result: list[str] = []
    for name in names:
        if name not in result:
            result.append(name)
    return result


def _input_kind_requirement_fact(input_kind: str) -> Fact:
    is_requirement = input_kind == "requirement"
    return Fact(
        id="fact.input.kind.requirement",
        name="input.kind.requirement",
        status="present" if is_requirement else "absent",
        value=is_requirement,
        source=FactSource(kind="input_kind", label=input_kind),
        evidence=[EvidenceSpan(source="input_kind", field="kind", excerpt=input_kind)],
        extraction_method="caller_supplied_kind",
        confidence="high",
        checked_scope="input_kind",
    )


def _text_fact(
    *,
    name: str,
    terms: tuple[str, ...],
    text: str,
    context: str,
    extraction_method: str,
    profile_value: str = "",
    profile_key: str = "",
    profile_source_kind: FactSourceKind = "requirement_profile",
) -> Fact:
    if profile_value:
        return Fact(
            id=f"fact.{name}",
            name=name,
            status="present",
            value=True,
            source=FactSource(kind=profile_source_kind, label=profile_key),
            evidence=[EvidenceSpan(source="requirement_profile", field=profile_key, excerpt=profile_value[:160])],
            extraction_method=extraction_method,
            confidence="high",
            checked_scope="request+context",
        )

    span = _first_evidence_span(text=text, context=context, terms=terms)
    status: FactStatus = "present" if span else "absent"
    return Fact(
        id=f"fact.{name}",
        name=name,
        status=status,
        value=status == "present",
        source=FactSource(kind="deterministic_extractor", label="lexical_terms"),
        evidence=[span] if span else [],
        extraction_method=extraction_method,
        confidence="high",
        checked_scope="request+context",
    )


def _first_evidence_span(*, text: str, context: str, terms: tuple[str, ...]) -> EvidenceSpan | None:
    for source, body in (("request", text), ("context", context)):
        lower = body.lower()
        for term in terms:
            index = lower.find(term.lower())
            if index < 0:
                continue
            end = index + len(term)
            excerpt = body[max(0, index - 50): min(len(body), end + 50)].strip()
            return EvidenceSpan(source=source, field="text", excerpt=excerpt, start=index, end=end)
    return None


def _fact_is_present(fact: Fact) -> bool:
    return fact.status in FACT_STATUSES_THAT_SATISFY_OBLIGATION


def _combine_text(*parts: str) -> str:
    return "\n".join(part for part in parts if part)


__all__ = [
    "Countercondition",
    "CounterconditionEffect",
    "CounterconditionStatus",
    "EvidenceSpan",
    "FACT_STATUSES_THAT_SATISFY_OBLIGATION",
    "ACCEPTANCE_MISSING_FINDING_ID",
    "ACCEPTANCE_MISSING_PREDICATE_ID",
    "ACCEPTANCE_MISSING_RULE_ID",
    "ACCEPTANCE_MISSING_VERIFICATION_TERMS",
    "ACHIEVEMENT_CRITERIA_FINDING_ID",
    "ACHIEVEMENT_CRITERIA_PREDICATE_ID",
    "ACHIEVEMENT_CRITERIA_RULE_ID",
    "EVIDENCE_ARTIFACT_FINDING_ID",
    "EVIDENCE_ARTIFACT_PREDICATE_ID",
    "EVIDENCE_ARTIFACT_RULE_ID",
    "METHOD_DETAIL_FINDING_ID",
    "METHOD_DETAIL_PREDICATE_ID",
    "METHOD_DETAIL_RULE_ID",
    "OBSERVABLE_BEHAVIOR_FINDING_ID",
    "OBSERVABLE_BEHAVIOR_PREDICATE_ID",
    "OBSERVABLE_BEHAVIOR_RULE_ID",
    "REJECTION_CONDITION_FINDING_ID",
    "REJECTION_CONDITION_PREDICATE_ID",
    "REJECTION_CONDITION_RULE_ID",
    "SCENARIO_CONTEXT_FINDING_ID",
    "SCENARIO_CONTEXT_PREDICATE_ID",
    "SCENARIO_CONTEXT_RULE_ID",
    "Fact",
    "FactSource",
    "FactSourceKind",
    "FactStatus",
    "LOGICAL_DERIVATION_SCHEMA_VERSION",
    "LOGICAL_TRACE_SCHEMA_VERSION",
    "LOGICAL_TRACE_SCOPE",
    "LogicalTrace",
    "Obligation",
    "ObligationStatus",
    "DERIVATION_SCOPE",
    "DerivationStatus",
    "DerivationStep",
    "RuleEvaluation",
    "build_acceptance_missing_trace",
    "build_request_verification_trace",
    "derivation_for_rule",
]
